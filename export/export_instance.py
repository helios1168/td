#!/usr/bin/env python3
"""export_instance.py -- descaled real-instance export, run on the work machine.

The justification is algebraic rather than statistical: with s_i(z) = S_i(z)/M_z and
t_z = T_z/M_z,

    u_i(z) = c1*S_i + c2*(T_z - S_i) + lam*M_z  =  M_z * [ c1*s_i + c2*(t_z - s_i) + lam ]

so M_z factors out, and because the objective is sum_i log g_i, scaling every M_z by a
constant only adds n*log(kappa) -- an additive constant that cannot move the argmax.  At
rho = 0 (the model) the solution is *exactly* invariant to the dollar level.  The absolute
scale is therefore not information the solver ever uses, and stripping it costs nothing.

What this writes carries shares and a relative opportunity, never a currency amount.  It
deliberately does NOT write the two together in recoverable form: `share * M` would be the
book, so M leaves only as M/median(M).

Format 3 (td#61).  The node table is long by (zip, channel) cell, and the channel list is
whatever the extract's `current_channel` column holds: any value, normalised, none of them
special.  One divisor serves every channel: kappa is the median positive cell M over all
channels, so masses are comparable across channels.  `channels.json`, written next to the
instance, lists each channel with its raw spellings and counts for the owner to review.  An
extract with no channel column is one channel, `national`.  No graph and no states: the ZIP
graph and each ZIP's state are built in the repo from public 2025 data (td#62).

Single file, standard library only, on purpose -- read it end to end before running it on
confidential data.

    python3 export_instance.py validate --sales s.csv --opportunity o.csv
    python3 export_instance.py export   --sales s.csv --opportunity o.csv --out ./out

Exit codes:  0 ok | 2 a guard fired, nothing written | 3 validation failed | 4 unreadable input
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

__version__ = "0.3.0"

THETA_DEFAULT = 0.40
JOIN_FLOOR = 0.99                 # hard-fail below this share of sales rows joining to M
SIG = 6                           # significant figures on every emitted float
FORMAT = "td_instance_descaled/3"         # nodes long by (zip, channel)
DEFAULT_CHANNEL = "national"      # the one channel of an extract with no channel column
CHANNEL_NAMES = ("current_channel", "channel")   # header spellings, see `pick`
_CHANNEL_SEP = re.compile(r"[ \-/().]+")


def channel_name(value):
    """Normalise a channel value: strip, lower-case, then any run of spaces, hyphens,
    slashes, parentheses or dots becomes one underscore, and leading/trailing underscores
    are stripped.  So "Wells (WH)", "WELLS-WH" and "wells wh" are one channel, wells_wh.
    Any value is accepted; `channels.json` shows the owner what each name was spelled as.
    """
    return _CHANNEL_SEP.sub("_", str(value).strip().lower()).strip("_")


class InputError(Exception):
    pass


class GuardError(Exception):
    pass


# --------------------------------------------------------------------------- io
def norm_id(x) -> str:
    """ZCTA ids to 5-character strings; survives the classic integer cast (501 -> 00501)."""
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(5)


def read_rows(path):
    """A delimited text table (comma, tab, semicolon or pipe), as a list of dicts."""
    if not os.path.exists(path):
        raise InputError(f"{path}: no such file")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel
        return [dict(r) for r in csv.DictReader(fh, dialect=dialect)]


def pick(row, *names, required=True, label=""):
    """First matching column name, case/underscore-insensitively."""
    keys = {str(k).lower().replace(" ", "_"): k for k in row}
    for n in names:
        k = keys.get(n.lower())
        if k is not None:
            return k
    if required:
        raise InputError(f"{label}: none of {names} found; columns are {sorted(row)}")
    return None


def rsig(x, sig=SIG):
    if x is None or not isinstance(x, (int, float)) or not math.isfinite(x) or x == 0:
        return x
    return round(float(x), -int(math.floor(math.log10(abs(float(x))))) + (sig - 1))


# ------------------------------------------------------------------------ build
class Instance(object):
    """Descaled instance, keyed by cell.

    A cell is a (zip, channel) pair.  `share[cell][rep]` is in [0,1]; `m_rel[cell]` =
    M_cell / median(positive cell M over every channel).
    """

    def __init__(self):
        self.share = defaultdict(dict)     # cell -> {rep -> s}, real reps only
        self.free = {}                     # cell -> share booked under a vacancy filler key
        self.m_rel = {}                    # cell -> relative opportunity
        self.firm = {}                     # rep -> firm label
        self.channels = ()                 # in the order the opportunity table names them
        self.spellings = {}                # channel -> the raw values that normalised to it
        self.sales_rows = {}               # channel -> sales rows read
        self.report = {}


def cell_label(cell):
    return f"{cell[0]}:{cell[1]}"


def build(sales_path, opp_path, theta=THETA_DEFAULT, keep_scale=False,
          filler_keys=(), join_floor=JOIN_FLOOR, impute_missing_m=False,
          repair_headroom=False):
    sales = read_rows(sales_path)
    opp = read_rows(opp_path)
    if not sales or not opp:
        raise InputError("sales or opportunity table is empty")

    s0, o0 = sales[0], opp[0]
    c_zip = pick(s0, "zip_code", "zcta", "zip", "postal_code", label="sales")
    c_rep = pick(s0, "rep_id", "rep", "wholesaler_id", "wholesaler", label="sales")
    c_val = pick(s0, "sales", "amount", "production", "premium", label="sales")
    c_firm = pick(s0, "firm", "company", "carrier", required=False)
    c_chan = pick(s0, *CHANNEL_NAMES, required=False)
    o_zip = pick(o0, "zip_code", "zcta", "zip", "postal_code", label="opportunity")
    o_val = pick(o0, "M", "opportunity", "potential", "market", label="opportunity")
    o_chan = pick(o0, *CHANNEL_NAMES, required=False)
    if (c_chan is None) != (o_chan is None):
        raise InputError(
            "exactly one of the two tables carries a channel column. Both must be long by "
            "(zip, channel), or neither -- a channelled sales table joined to a per-zip "
            "opportunity table would price every channel against the whole zip's M.")
    channelled = c_chan is not None
    spellings = defaultdict(set)

    def chan(row, col, label):
        if not channelled:
            return DEFAULT_CHANNEL
        raw = row.get(col)
        raw = "" if raw is None else str(raw).strip()
        c = channel_name(raw)
        if not c:
            raise InputError(f"{label}: a row has an empty {col!r}. Every row must name its "
                             f"channel; a blank one would silently join to the wrong cell.")
        spellings[c].add(raw)
        return c

    # --- opportunity -----------------------------------------------------------
    M, channels, nonfinite = {}, [], set()
    for r in opp:
        z = norm_id(r[o_zip])
        c = chan(r, o_chan, "opportunity")
        if c not in channels:
            channels.append(c)
        try:
            v = float(r[o_val])
        except (TypeError, ValueError):
            continue                        # blank/absent M: the cell stays out of M here
        cell = (z, c)
        if not math.isfinite(v):
            nonfinite.add(cell)             # NaN or infinity parses, but is no opportunity
            continue
        if channelled:
            # The channelled extract carries a cell's opportunity once across its rows (one
            # row holds it and the duplicate rows hold 0, or several rows hold parts of it),
            # so a cell's M is the sum of its rows. Only the channel-less extract repeats
            # the same M on every row of a zip, which is the rule below.
            M[cell] = M.get(cell, 0.0) + v
            continue
        if cell in M and M[cell] > 0 and v > 0 and abs(v - M[cell]) > 1e-6 * max(v, M[cell]):
            raise InputError(
                f"cell {cell_label(cell)} carries two different opportunity values "
                f"({M[cell]:g} vs {v:g}). With a combined sales+opportunity file, M must be "
                f"identical on every row of a cell -- this looks like a bad merge.")
        M[cell] = max(v, M.get(cell, v))     # a positive value wins over a stray 0
    if nonfinite:
        bad = sorted(nonfinite)
        raise InputError(
            f"{len(bad)} opportunity cell(s) hold a value that is not a finite number (NaN or "
            f"infinity), e.g. {[cell_label(c) for c in bad[:3]]}. A blank M reads as no "
            f"value; a NaN or infinity is bad data. Fix it upstream before exporting.")

    # One divisor for every channel: the median positive cell M, so masses are comparable
    # across channels and no channel is special (td#61).
    pos = sorted(v for v in M.values() if v > 0)
    if not pos:
        raise InputError("no positive opportunity values")
    kappa = pos[len(pos) // 2] if len(pos) % 2 else 0.5 * (pos[len(pos) // 2 - 1] +
                                                           pos[len(pos) // 2])
    if kappa <= 0:
        raise InputError("median positive opportunity is not positive")

    # --- sales -> shares -------------------------------------------------------
    inst = Instance()
    raw, raw_free = defaultdict(dict), defaultdict(float)
    fillers = {str(k).strip() for k in filler_keys}

    # opt-in: a cell with book but no (or nonpositive) M gets M = its total book.  The
    # conservative floor -- it values the cell at exactly what is already sold there (no
    # upside, satisfies pointwise headroom with equality at theta<=1) and keeps the zip in
    # the instance.  kappa above is computed from real M values only, so imputation never
    # moves the descaling constant.
    n_imputed = 0
    if impute_missing_m:
        book = defaultdict(float)
        for r in sales:
            cell = (norm_id(r[c_zip]), chan(r, c_chan, "sales"))
            if cell in M and M[cell] > 0:
                continue
            try:
                v = float(r[c_val])
            except (TypeError, ValueError):
                continue
            if v > 0:
                book[cell] += v
        for cell, t in book.items():
            M[cell] = t
            n_imputed += 1

    # A negative cell total is bad data, never a cell to drop quietly: checked here, after
    # --impute-missing-m has replaced the nonpositive M of every cell with book, so the
    # declared repair still applies and any negative total left over stops the export.
    negative = sorted(cell for cell, v in M.items() if v < 0)
    if negative:
        raise InputError(
            f"{len(negative)} cell(s) carry negative opportunity, e.g. "
            f"{[cell_label(c) for c in negative[:3]]}. A cell cannot hold negative "
            f"opportunity; fix it upstream (--impute-missing-m replaces it only in a cell "
            f"with book).")

    n_rows = n_joined = n_nonpositive = n_unparsed = n_filler = 0
    rows_by_chan = Counter()
    unjoined_value, total_value = defaultdict(float), 0.0
    for r in sales:
        n_rows += 1
        z, rep = norm_id(r[c_zip]), str(r[c_rep]).strip()
        cell = (z, chan(r, c_chan, "sales"))
        rows_by_chan[cell[1]] += 1
        try:
            v = float(r[c_val])
        except (TypeError, ValueError):
            n_unparsed += 1                 # blank/non-numeric: not a sales row at all
            continue                        # (a combined file's opportunity-only rows land here)
        if v <= 0:                          # cand(z) = {i : S_i > 0}, per the 2026-08-31 rule
            n_nonpositive += 1
            continue
        total_value += v
        if cell not in M or M[cell] <= 0:
            unjoined_value[cell] += v
            continue
        n_joined += 1
        if rep in fillers:
            # a vacancy placeholder: real book, real firm, but no incumbent person.  It must
            # never become a candidate owner (the objective would try to be fair to a
            # vacancy) while its production still counts as book at the cell.
            n_filler += 1
            raw_free[cell] += v
            continue
        raw[cell][rep] = raw[cell].get(rep, 0.0) + v
        if c_firm is not None and rep not in inst.firm:
            inst.firm[rep] = str(r[c_firm]).strip()

    join_rate = n_joined / max(n_rows - n_nonpositive - n_unparsed, 1)
    if join_rate < join_floor:
        lost_share = sum(unjoined_value.values()) / total_value if total_value else 0.0
        top = sorted(unjoined_value.items(), key=lambda kv: -kv[1])[:8]
        top_txt = ", ".join(f"{cell_label(c)} ({v / total_value:.2%})" for c, v in top)
        raise InputError(
            f"only {join_rate:.4f} of positive sales rows joined to an opportunity cell "
            f"(floor {join_floor}); the unjoined rows carry {lost_share:.2%} of sales value.\n"
            f"  worst cells by lost value: {top_txt}\n"
            f"  Check those ids before overriding: 4-digit ids mean dropped leading zeros; "
            f"ids missing from any ZCTA table are usually PO-box/unique USPS zips, which "
            f"never exist as ZCTAs (fix: a zip->ZCTA crosswalk upstream). A cell missing "
            f"only in one channel means the opportunity extract does not carry that "
            f"(zip, channel) row at all. If the loss is understood and acceptable, rerun "
            f"with --join-floor {join_rate:.2f} -- the unjoined rows are then dropped from "
            f"the instance.")

    # opt-in: where the opportunity figure is smaller than the book it must contain, lift
    # M to exactly the pointwise-headroom floor max_i(S_i + theta*(T - S_i)) -- the least
    # repair that makes the model well-posed.  Anything larger (e.g. M += T everywhere it
    # violates) overshoots where M is only slightly understated and distorts the balance
    # measure more than the data requires.  Count and added share are reported and ride
    # into the export meta: this is a recorded data repair, not a silent fix.
    n_repaired, repair_added = 0, 0.0
    if repair_headroom:
        for cell in set(raw) | set(raw_free):
            vals = list(raw.get(cell, {}).values())
            f = raw_free.get(cell, 0.0)
            if f > 0:
                vals.append(f)
            T = sum(vals)
            need = max(v + theta * (T - v) for v in vals)
            # the export rounds to SIG significant figures and a cell's t sums up to ~100
            # rounded shares, so landing exactly on the floor lets that accumulated
            # rounding tip headroom past 1 downstream; this margin dominates the rounding
            # error (a few 1e-5 relative) while staying far below any data noise
            need *= 1 + 5e-5
            if M.get(cell, 0.0) < need:
                repair_added += need - M.get(cell, 0.0)
                M[cell] = need
                n_repaired += 1

    for cell, per_rep in raw.items():
        inst.m_rel[cell] = M[cell] / kappa
        for rep, v in per_rep.items():
            inst.share[cell][rep] = v / M[cell]
    for cell, v in raw_free.items():
        inst.m_rel[cell] = M[cell] / kappa
        inst.free[cell] = v / M[cell]

    # cells with opportunity but no sales at all: untapped, carried so the map stays whole
    for cell, v in M.items():
        if cell not in inst.m_rel and v > 0:
            inst.m_rel[cell] = v / kappa

    # A cell --impute-missing-m made from sales alone can be in a channel the opportunity
    # table never names. It joins the list after those, in sales-table order, so the list
    # covers every cell: td/data.py refuses a cell whose channel is not listed.
    emitted = {c for _, c in inst.m_rel}
    channels += [c for c in rows_by_chan if c in emitted and c not in channels]
    inst.channels = tuple(channels)
    inst.spellings = {c: sorted(spellings.get(c, ())) for c in channels}
    inst.sales_rows = dict(rows_by_chan)

    # --- candidate structure ---------------------------------------------------
    # counted per cell: a zip is contested in one channel and untapped in another, and the
    # decision the histogram describes is per cell.
    ncand = Counter(len(inst.share.get(cell, {})) for cell in inst.m_rel)
    n_vacant = sum(1 for cell in inst.m_rel
                   if not inst.share.get(cell) and inst.free.get(cell, 0.0) > 0)
    n_untapped = sum(1 for cell in inst.m_rel
                     if not inst.share.get(cell) and not inst.free.get(cell, 0.0))
    inst.report = dict(
        n_zips=len({z for z, _ in inst.m_rel}),
        n_cells=len(inst.m_rel),
        channels=list(inst.channels),
        n_reps=len({r for d in inst.share.values() for r in d}),
        n_sales_rows=n_rows,
        n_sales_rows_nonpositive=n_nonpositive,
        join_rate=round(join_rate, 6),
        cand_histogram={str(k): v for k, v in sorted(ncand.items())},
        zips_uncontested=ncand.get(1, 0),
        zips_vacant=n_vacant,
        zips_untapped=n_untapped,
        zips_with_filler=sum(1 for v in inst.free.values() if v > 0),
        n_filler_rows=n_filler,
        n_filler_keys=len(fillers),
        zips_m_imputed=n_imputed,
        zips_headroom_repaired=n_repaired,
        repair_added_share=round(repair_added / max(sum(M.values()), 1e-300), 6),
        zips_contested=sum(v for k, v in ncand.items() if k >= 2),
        max_candidates=max(ncand) if ncand else 0,
        scale_stripped=not keep_scale,
    )
    if keep_scale:                          # never used by the runbook; here so the flag is honest
        inst.report["kappa"] = kappa
    return inst


# ------------------------------------------------------------------- validation
def validate(inst, theta=THETA_DEFAULT):
    """Model validity in share space, per cell.  Returns a list of problems (empty == valid)."""
    problems = []
    bad_share = [c for c, d in inst.share.items() if any(s < 0 or s > 1 for s in d.values())]
    bad_share += [c for c, f in inst.free.items() if f < 0 or f > 1]
    if bad_share:
        problems.append(f"{len(bad_share)} cell(s) with a share outside [0,1] "
                        f"(e.g. {[cell_label(c) for c in bad_share[:3]]}) -- sales exceed "
                        f"opportunity there")

    # headroom, share form:  1 >= max_i ( s_i + theta*(t - s_i) )
    viol = []
    for cell in inst.m_rel:
        d = inst.share.get(cell, {})
        f = inst.free.get(cell, 0.0)
        vals = list(d.values()) + ([f] if f > 0 else [])
        if not vals:
            continue
        t = sum(d.values()) + f
        need = max((s + theta * (t - s)) for s in vals)
        if need > 1.0 + 1e-9:
            viol.append((cell, need))
    if viol:
        worst = max(v for _, v in viol)
        problems.append(
            f"{len(viol)} cell(s) violate pointwise headroom at theta={theta} "
            f"(need <= 1, worst {worst:.4f}). The opportunity figure is smaller than the "
            f"book it is supposed to contain -- a modelling question, settle it first.")
    return problems


def mask_reps(inst, ref_channel=""):
    """Surrogate integer ids, assigned in descending total book.  The map stays local.

    Defence in depth: the upstream extract is already masked, so this is a second pass whose
    only job is to guarantee no upstream label -- however innocuous it looks -- rides along.

    With `ref_channel` set (`--rep-ids-channel`), the reps with book in that channel are
    ranked among themselves first, on that channel's book alone, and the rest follow.  So
    reps keep the ids an earlier single-channel export of that channel gave them, and
    `--rep-ids` can check it.  Firm labels are numbered the same way, for the same reason.
    """
    total, ref = defaultdict(float), defaultdict(float)
    for cell, d in inst.share.items():  # noqa: PLC0206
        for rep, s in d.items():
            total[rep] += s * inst.m_rel[cell]
            if cell[1] == ref_channel:
                ref[rep] += s * inst.m_rel[cell]

    def key(r):
        # (-ref, str) inside the reference channel: exactly the single-channel rule,
        # including its tie-break, so nothing about the other channels can perturb it.
        return (0, -ref[r], str(r)) if ref[r] > 0 else (1, -total[r], str(r))

    order = sorted(total, key=key)
    rep_map = {rep: f"R{i:04d}" for i, rep in enumerate(order)}
    ref_firms = sorted({inst.firm.get(r, "") for r in order if ref[r] > 0})
    rest = sorted({inst.firm.get(r, "") for r in order} - set(ref_firms))
    firm_map = {f: f"F{i}" for i, f in enumerate(ref_firms + rest)}
    new_share = defaultdict(dict)
    for cell, d in inst.share.items():
        for rep, s in d.items():
            new_share[cell][rep_map[rep]] = s
    inst.share = new_share
    inst.firm = {rep_map[r]: firm_map.get(inst.firm.get(r, ""), "F0") for r in order}
    return rep_map, firm_map


def check_rep_ids(inst, path, channel):
    """Cross-check the surrogate ids against an earlier export, after `mask_reps`.

    The exported file carries surrogate ids only, so there is nothing in it to map a raw rep
    id back to one; the ids line up because `mask_reps` ranks `channel` first, and nothing is
    carried over from the file.  What the file does carry is each surrogate's share vector,
    and `channel` is meant to be the same data it was built from, so those vectors must match
    zip for zip.  A mismatch means an id now stands for a different rep, or that the
    channel's data moved.  Every comparison against that file would then be silently wrong,
    so it stops the export.

    Only the zips the earlier file kept are compared: it may be a filtered derivative (the
    CONUS instance is), and a zip it dropped is not evidence of anything.
    """
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            old = json.load(fh)
    except OSError as e:
        raise InputError(f"{path}: cannot read the earlier export ({e})") from e
    nodes = old.get("nodes", {})
    if "channel" in nodes:
        raise InputError(f"{path}: --rep-ids wants the existing single-channel export, "
                         f"the one whose ids the rest of the work pins to")
    old_vec = defaultdict(dict)
    for z, row in zip(nodes.get("z", []), nodes.get("share", [])):
        for rep, s in row.items():
            old_vec[rep][z] = s
    zips = set(nodes.get("z", []))
    new_vec = defaultdict(dict)
    for (z, c), d in inst.share.items():
        if c != channel or z not in zips:
            continue
        for rep, s in d.items():
            new_vec[rep][z] = rsig(s)

    bad = [rep for rep, vec in sorted(old_vec.items()) if new_vec.get(rep) != vec]
    if bad:
        raise GuardError(
            f"{len(bad)} of {len(old_vec)} rep id(s) in {os.path.basename(path)} no longer "
            f"carry the same book in the {channel} channel "
            f"(e.g. {bad[:8]}). Either that channel's rows are not the same data the file "
            f"was built from, or a filler key differs from the earlier run. Settle it "
            f"before exporting: the ids are how every result maps back.")
    fresh = [r for r in inst.firm if r not in old.get("firm", {})]
    retired = sorted(set(old.get("firm", {})) - set(old_vec))
    return dict(checked=len(old_vec), fresh=len(fresh), retired=len(retired))


# ------------------------------------------------------------------------ write
def channels_doc(inst):
    """What `channels.json` holds, for the owner to review before anything is modelled.

    Per channel, in the order the opportunity table names them: the raw values that
    normalised to its name, its sales rows, cells and zips, and its share of the total
    opportunity.  Counts and one ratio only -- no currency amount and no divisor.
    """
    cells, zips, mass = Counter(), defaultdict(set), defaultdict(float)
    for (z, c), m in inst.m_rel.items():
        cells[c] += 1
        zips[c].add(z)
        mass[c] += m
    total = sum(mass.values())
    return dict(channels=[
        dict(channel=c, spellings=inst.spellings.get(c, []),
             sales_rows=inst.sales_rows.get(c, 0), cells=cells[c], zips=len(zips[c]),
             opportunity_share=rsig(mass[c] / total) if total else 0.0)
        for c in inst.channels])


def _keys(obj):
    """Every dict key at any depth of a JSON-shaped object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _keys(v)


def guard(payload, channels=None):
    """Refuse to emit anything that looks like a currency amount, or an upstream label.

    Shares are in [0,1] by construction and m_rel is a ratio to the median, so a value in the
    thousands means the descaling did not happen.  This is the last line before either file is
    written, not a diagnostic: `channels` is the `channels.json` document, and the filler
    sentinel and the divisor are refused in it as in the payload.

    The median is taken over the positive m_rel of every cell, the set kappa was the median
    of, so it is 1.0 by construction up to imputed and repaired cells.
    """
    ms = payload["nodes"]["m_rel"]
    if not ms:
        raise GuardError("no nodes to write")
    pos = sorted(m for m in ms if m > 0)
    if not pos:
        raise GuardError("no positive m_rel to check the descaling against")
    med = pos[len(pos) // 2]
    if not (0.5 <= med <= 2.0):
        raise GuardError(f"median m_rel is {med:.6g}, expected ~1.0 -- scale was not stripped")
    big = [m for m in ms if m > 1e4]
    if big:
        raise GuardError(f"{len(big)} m_rel value(s) above 1e4 (max {max(big):.6g}) -- "
                         f"this looks like a currency amount, not a ratio")
    neg = [m for m in ms if m < 0]
    if neg:
        raise GuardError(f"{len(neg)} negative m_rel value(s) (min {min(neg):.6g}) -- "
                         f"a cell cannot hold negative opportunity")
    for row in payload["nodes"]["share"]:
        for s in row.values():
            if not (0.0 <= s <= 1.0):
                raise GuardError(f"share {s!r} outside [0,1] -- not a share")
    for s in payload["nodes"]["share_free"]:
        if not (0.0 <= s <= 1.0):
            raise GuardError(f"free share {s!r} outside [0,1] -- not a share")
    docs = {"the payload": json.dumps(payload)}
    if channels is not None:
        docs["channels.json"] = json.dumps(channels)
    for key in guard.filler_keys:
        for name, text in docs.items():
            if key and key in text:
                raise GuardError(f"filler key {key!r} appears in {name}; the sentinel's "
                                 f"own name must not leave -- only the count does")
    # a field named for the divisor, not the word in a value: a channel may be called kappa
    for name, doc in (("meta", payload.get("meta", {})), ("channels.json", channels)):
        if any("kappa" in k.lower() for k in _keys(doc)):
            raise GuardError(f"{name} carries a kappa field; the divisor must not leave")


guard.filler_keys = ()          # set by `write`; checked above against both documents


def write(inst, out_dir, theta, lam, verbose=True, filler_keys=()):
    """Write the format-3 instance and `channels.json` beside it, both or neither."""
    rank = {c: i for i, c in enumerate(inst.channels)}
    cells = sorted(inst.m_rel, key=lambda cell: (cell[0], rank.get(cell[1], len(rank))))
    nodes = dict(
        z=[z for z, _ in cells],
        channel=[c for _, c in cells],
        m_rel=[rsig(inst.m_rel[cell]) for cell in cells],
        share=[{r: rsig(s) for r, s in sorted(inst.share.get(cell, {}).items())}
               for cell in cells],
        share_free=[rsig(inst.free.get(cell, 0.0)) for cell in cells],
    )
    payload = dict(
        format=FORMAT,
        nodes=nodes,
        firm=inst.firm,
        meta=dict(
            exporter="export_instance", version=__version__,
            theta=theta, lam=lam,
            scale="descaled: M/median(positive cell M over all channels); "
                  "shares dimensionless",
            **{k: v for k, v in inst.report.items() if k != "kappa"},
        ),
    )
    chans = channels_doc(inst)
    guard.filler_keys = tuple(filler_keys)
    guard(payload, chans)               # both documents, before either file is opened
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "instance_descaled.json.gz")
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"), sort_keys=True)
    chan_path = os.path.join(out_dir, "channels.json")
    with open(chan_path, "w", encoding="utf-8") as fh:
        json.dump(chans, fh, indent=2, sort_keys=True)
        fh.write("\n")
    if verbose:
        print(f"wrote {path}  ({os.path.getsize(path)/1e6:.2f} MB)")
        print(f"wrote {chan_path}  -- review the channel list before modelling")
    return path


def report_text(inst):
    r = inst.report
    L = ["", "what this export contains", "-" * 46,
         f"  zips                 {r['n_zips']:>10,}",
         f"  cells (zip, channel) {r['n_cells']:>10,}",
         f"  reps                 {r['n_reps']:>10,}",
         f"  sales rows joined    {r['join_rate']:>10.4f}",
         "", "channels (written to channels.json on export)", "-" * 46,
         "  channel                  cells     zips   share of M   spelled"]
    for c in channels_doc(inst)["channels"]:
        L.append(f"  {c['channel']:<22} {c['cells']:>7,} {c['zips']:>8,}   "
                 f"{c['opportunity_share']:>9.1%}   {', '.join(c['spellings'])}")
    L += ["",
          "  every count below is per CELL, not per zip: a zip is contested in one",
          "  channel and untapped in another, and the decision is per cell.",
          "",
          "candidate structure (cand(z) = real reps with positive sales)", "-" * 46,
          f"  untapped   (0 reps)  {r['zips_untapped']:>10,}   no sales at all",
          f"  vacant     (0 reps)  {r['zips_vacant']:>10,}   sales, but only under a filler key",
          f"  uncontested(1 rep )  {r['zips_uncontested']:>10,}   owner forced, no decision",
          f"  contested  (2+ reps) {r['zips_contested']:>10,}   the actual problem",
          f"  max candidates       {r['max_candidates']:>10,}",
          f"  zips with filler book{r['zips_with_filler']:>10,}   ({r['n_filler_rows']:,} rows)",
          f"  zips with M imputed  {r['zips_m_imputed']:>10,}   book but no M; M = total book",
          f"  zips headroom-repaired{r['zips_headroom_repaired']:>9,}   M lifted to the floor; "
          f"added {r['repair_added_share']:.2%} of total M",
          "", "  |cand| histogram: " + ", ".join(f"{k}:{v}" for k, v in
                                                  r["cand_histogram"].items()),
          "",
          "leaving this machine: shares in [0,1], opportunity as M/median(M),",
          "surrogate rep ids, public ZCTA ids, channel names. No currency amount.", ""]
    return "\n".join(L)


# -------------------------------------------------------------------------- cli
def main(argv=None):
    p = argparse.ArgumentParser(prog="export_instance", description=__doc__.split("\n")[0])
    p.add_argument("cmd", choices=["validate", "export"])
    p.add_argument("--sales", required=True,
                   help="zip_code, rep_id, firm, current_channel, sales (long); with no "
                        "channel column the whole extract is one channel, national")
    p.add_argument("--opportunity", required=True,
                   help="zip_code, current_channel, M; the channel column on both tables "
                        "or neither")
    p.add_argument("--out", default="./out")
    p.add_argument("--theta", type=float, default=THETA_DEFAULT)
    p.add_argument("--lam", type=float, default=0.30)
    p.add_argument("--impute-missing-m", action="store_true",
                   help="a cell with book but no (or nonpositive) opportunity value gets "
                        "M = its total book -- the conservative floor: no upside, the cell "
                        "stays in. Off by default; the count is reported.")
    p.add_argument("--repair-headroom", action="store_true",
                   help="where M is smaller than the book it must contain, lift it to "
                        "exactly the pointwise-headroom floor max_i(S_i + theta*(T-S_i)). "
                        "The minimal repair for messy opportunity data; off by default, "
                        "count and added share are reported.")
    p.add_argument("--join-floor", type=float, default=JOIN_FLOOR,
                   help=f"minimum share of positive sales rows that must join to an "
                        f"opportunity cell (default {JOIN_FLOOR}). Lower it only after "
                        f"reading the failure report: unjoined rows are dropped.")
    p.add_argument("--filler-key", action="append", default=[], metavar="KEY",
                   help="a rep_id that marks a VACANCY rather than a person. Repeatable. "
                        "Its sales stay in the instance as unowned book but it never "
                        "becomes a candidate owner.")
    p.add_argument("--rep-ids-channel", default=None, metavar="NAME",
                   help="rank the reps with book in this channel first, on that channel's "
                        "book alone, so they keep the ids an earlier single-channel export "
                        "of it gave them. Required by --rep-ids.")
    p.add_argument("--rep-ids", default=None, metavar="PATH",
                   help="an earlier single-channel export (instance_descaled*.json.gz) to "
                        "cross-check the surrogate ids against, over --rep-ids-channel. "
                        "Nothing is carried into the export from it. Stops the export if "
                        "that channel's book moved. Compares only the zips that file kept.")
    p.add_argument("--rep-map", default=None, metavar="PATH",
                   help="write the raw rep id to surrogate id map here (rep_surrogate, rep_id, "
                        "firm_surrogate, firm); confidential, it stays on this machine")
    p.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    a = p.parse_args(argv)

    try:
        if a.rep_ids and not a.rep_ids_channel:
            raise InputError("--rep-ids needs --rep-ids-channel: the channel whose book the "
                             "earlier single-channel export was built from")
        inst = build(a.sales, a.opportunity, theta=a.theta, filler_keys=a.filler_key,
                     join_floor=a.join_floor, impute_missing_m=a.impute_missing_m,
                     repair_headroom=a.repair_headroom)
        ref_channel = channel_name(a.rep_ids_channel) if a.rep_ids_channel else ""
        if ref_channel and ref_channel not in inst.channels:
            raise InputError(f"--rep-ids-channel {a.rep_ids_channel!r} is not a channel of "
                             f"this extract; channels are {list(inst.channels)}")
    except InputError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 4

    print(report_text(inst))
    problems = validate(inst, a.theta)
    if problems:
        print("VALIDATION PROBLEMS")
        for s in problems:
            print(f"  - {s}")
    else:
        print("validation: clean")

    if a.cmd == "validate":
        return 3 if problems else 0
    if problems:
        print("\nrefusing to export while validation fails.", file=sys.stderr)
        return 3

    raw_firm = dict(inst.firm)
    rep_map, firm_map = mask_reps(inst, ref_channel)
    if a.rep_ids:
        try:
            c = check_rep_ids(inst, a.rep_ids, ref_channel)
        except InputError as e:
            print(f"input error: {e}", file=sys.stderr)
            return 4
        except GuardError as e:
            print(f"GUARD: {e}\nnothing written.", file=sys.stderr)
            return 2
        print(f"rep ids: {c['checked']} checked against {os.path.basename(a.rep_ids)}, all "
              f"unchanged; {c['fresh']} new rep(s) numbered after them"
              + (f"; {c['retired']} id(s) in that file have no book on its zips and were "
                 f"not checked" if c["retired"] else ""))

    if not a.yes:
        try:
            ans = input("\nwrite the descaled instance? [y/N] ").strip().lower()
        except EOFError:
            ans = "n"
        if ans not in ("y", "yes"):
            print("nothing written.")
            return 0
    try:
        write(inst, a.out, a.theta, a.lam, filler_keys=a.filler_key)
    except GuardError as e:
        print(f"GUARD: {e}\nnothing written.", file=sys.stderr)
        return 2
    if a.rep_map:
        # the map `mask_reps` keeps local, written only on request and only next to a
        # successful export: the one file that ties a surrogate back to a person
        with open(a.rep_map, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["rep_surrogate", "rep_id", "firm_surrogate", "firm"])
            for rep, sur in sorted(rep_map.items(), key=lambda kv: kv[1]):
                firm = raw_firm.get(rep, "")
                w.writerow([sur, rep, firm_map.get(firm, "F0"), firm])
        print(f"rep map: {len(rep_map)} rep(s) -> {a.rep_map} (confidential)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
