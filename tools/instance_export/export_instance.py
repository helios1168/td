#!/usr/bin/env python3
"""export_instance.py -- descaled real-instance export, run on the work machine.

Supersedes the synthetic-twin route for the N-way problem (see NWAY.md and the CLAUDE.md
"Real data route" decision, revised 2026-08-31).  The justification is algebraic rather than
statistical: with s_i(z) = S_i(z)/M_z and t_z = T_z/M_z,

    u_i(z) = c1*S_i + c2*(T_z - S_i) + lam*M_z  =  M_z * [ c1*s_i + c2*(t_z - s_i) + lam ]

so M_z factors out, and because the objective is sum_i log g_i, scaling every M_z by a
constant only adds n*log(kappa) -- an additive constant that cannot move the argmax.  At
rho = 0 (the model) the solution is *exactly* invariant to the dollar level.  The absolute
scale is therefore not information the solver ever uses, and stripping it costs nothing.

What this writes carries shares and a relative opportunity, never a currency amount.  It
deliberately does NOT write the two together in recoverable form: `share * M` would be the
book, so M leaves only as M/median(M).

When both extracts carry a `current_channel` column the node table goes long by (zip, channel)
and the format string becomes td_instance_descaled/2.  A cell (z, c) is priced against its own
M, the divisor stays pinned to the median of the `national` rows, and the surrogate rep ids of
the national reps are the ones the single-channel export already gave them.  With no channel
column nothing changes: the same format 1 file, byte for byte.

Single file on purpose -- read it end to end before running it on confidential data.

    python3 export_instance.py validate --sales s.csv --opportunity o.csv --graph e.parquet
    python3 export_instance.py export   --sales s.csv --opportunity o.csv --graph e.parquet \
                                        --states st.csv --out ./out

Exit codes:  0 ok | 2 a guard fired, nothing written | 3 validation failed | 4 unreadable input
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict

__version__ = "0.1.0"

THETA_DEFAULT = 0.40
JOIN_FLOOR = 0.99                 # hard-fail below this share of sales rows joining to M
SIG = 6                           # significant figures on every emitted float
FORMAT_V1 = "td_instance_descaled/1"      # nodes long by zip
FORMAT_V2 = "td_instance_descaled/2"      # nodes long by (zip, channel)
KAPPA_CHANNEL = "national"        # the channel the descaling divisor is pinned to
CHANNEL_NAMES = ("current_channel", "channel")   # header spellings, see `pick`


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


def _read_delimited(path):
    import csv
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel
        return [dict(r) for r in csv.DictReader(fh, dialect=dialect)]


def _read_arrow(path):
    try:
        import pyarrow.parquet as pq
        import pyarrow.feather as feather
    except ImportError as e:                                     # pragma: no cover
        raise InputError(f"{path}: reading parquet/feather needs pyarrow") from e
    tbl = feather.read_table(path) if path.endswith(".feather") else pq.read_table(path)
    cols = tbl.column_names
    return [dict(zip(cols, row)) for row in zip(*[c.to_pylist() for c in tbl.columns])]


def read_rows(path):
    if not os.path.exists(path):
        raise InputError(f"{path}: no such file")
    if path.endswith((".parquet", ".pq", ".feather")):
        return _read_arrow(path)
    return _read_delimited(path)


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


def read_edges(path, u_col=None, v_col=None):
    rows = read_rows(path)
    if not rows:
        raise InputError(f"{path}: empty edge table")
    r0 = rows[0]
    if u_col is None or v_col is None:
        for a, b in (("u", "v"), ("src", "dst"), ("zcta_a", "zcta_b"), ("source", "target")):
            if pick(r0, a, required=False) and pick(r0, b, required=False):
                u_col, v_col = pick(r0, a), pick(r0, b)
                break
        else:
            cols = list(r0)
            if len(cols) < 2:
                raise InputError(f"{path}: need two id columns, found {cols}")
            u_col, v_col = cols[0], cols[1]
    out = set()
    for r in rows:
        u, v = norm_id(r[u_col]), norm_id(r[v_col])
        if u != v:
            out.add((u, v) if u < v else (v, u))
    return sorted(out)


def graph_hash(zips, edges) -> str:
    h = hashlib.sha256()
    for z in sorted(zips):
        h.update(z.encode())
    for u, v in sorted(edges):
        h.update(u.encode()); h.update(v.encode())
    return h.hexdigest()


def rsig(x, sig=SIG):
    if x is None or not isinstance(x, (int, float)) or not math.isfinite(x) or x == 0:
        return x
    return round(float(x), -int(math.floor(math.log10(abs(float(x))))) + (sig - 1))


# ------------------------------------------------------------------------ build
class Instance(object):
    """Descaled instance, keyed by cell.

    A cell is a (zip, channel) pair; with no channel column in the extract the channel is ""
    and a cell is a zip, which is exactly the single-channel case.  `share[cell][rep]` is in
    [0,1]; `m_rel[cell]` = M_cell / median(positive M over the kappa channel).
    """

    def __init__(self):
        self.share = defaultdict(dict)     # cell -> {rep -> s}, real reps only
        self.free = {}                     # cell -> share booked under a vacancy filler key
        self.m_rel = {}                    # cell -> relative opportunity
        self.firm = {}                     # rep -> firm label
        self.state = {}                    # zip -> state (optional)
        self.channels = ()                 # () when the extract carries no channel column
        self.kappa_channel = ""            # the channel the divisor was taken from
        self.edges = []
        self.report = {}


def cell_of(z, c):
    """The key of a cell.  A zip when there is one channel, a (zip, channel) pair when more.

    Degrading to the zip itself is not cosmetic: with no channel column every structure in
    this module is keyed exactly as it was before channels existed, so the single-channel
    path cannot drift from the one that has been run on real data.
    """
    return (z, c) if c else z


def cell_zip(cell):
    return cell[0] if isinstance(cell, tuple) else cell


def cell_chan(cell):
    return cell[1] if isinstance(cell, tuple) else ""


def cell_label(cell):
    return f"{cell[0]}:{cell[1]}" if isinstance(cell, tuple) else cell


def zip_mass(inst):
    """Relative opportunity per zip, summed over the channels present.

    The graph, the components and the footprint report live on zips, not cells: a district is
    contiguous in the zip graph whatever channels it carries.
    """
    out = defaultdict(float)
    for cell, m in inst.m_rel.items():
        out[cell_zip(cell)] += m
    return out


def build(sales_path, opp_path, graph_path, states_path=None,
          theta=THETA_DEFAULT, u_col=None, v_col=None, keep_scale=False,
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

    def chan(row, col, label):
        v = row.get(col)
        v = "" if v is None else str(v).strip().lower()
        if not v:
            raise InputError(f"{label}: a row has an empty {col!r}. Every row must name its "
                             f"channel; a blank one would silently join to the wrong cell.")
        return v

    # --- opportunity -----------------------------------------------------------
    M, channels, seen = {}, [], set()
    for r in opp:
        z = norm_id(r[o_zip])
        c = chan(r, o_chan, "opportunity") if channelled else ""
        if c not in seen:
            seen.add(c)
            channels.append(c)
        try:
            v = float(r[o_val])
        except (TypeError, ValueError):
            continue                        # blank/absent M: the cell stays out of M here
        cell = cell_of(z, c)
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

    # kappa is pinned to one channel so that channel's m_rel, and every number derived from
    # it, is unchanged by the arrival of the others.
    kappa_channel = KAPPA_CHANNEL if channelled else ""
    if channelled and kappa_channel not in seen:
        raise InputError(
            f"no {kappa_channel!r} rows in the opportunity table. The descaling divisor is "
            f"pinned to that channel so the existing single-channel instance's m_rel, tau "
            f"and k carry over unchanged; channels are {sorted(seen)}.")
    pos = sorted(v for cell, v in M.items() if v > 0 and cell_chan(cell) == kappa_channel)
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
    # the graph instead of punching a hole in contiguity.  kappa above is computed from
    # real M values only, so imputation never moves the descaling constant.
    n_imputed = 0
    if impute_missing_m:
        book = defaultdict(float)
        for r in sales:
            cell = cell_of(norm_id(r[c_zip]), chan(r, c_chan, "sales") if channelled else "")
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

    n_rows = n_joined = n_nonpositive = n_unparsed = n_filler = 0
    unjoined_value, total_value = defaultdict(float), 0.0
    for r in sales:
        n_rows += 1
        z, rep = norm_id(r[c_zip]), str(r[c_rep]).strip()
        cell = cell_of(z, chan(r, c_chan, "sales") if channelled else "")
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

    # cells with opportunity but no sales at all: untapped glue, carried for adjacency only
    for cell, v in M.items():
        if cell not in inst.m_rel and v > 0:
            inst.m_rel[cell] = v / kappa

    inst.channels = tuple(channels) if channelled else ()
    inst.kappa_channel = kappa_channel

    # --- states ----------------------------------------------------------------
    if states_path:
        rows = read_rows(states_path)
        if rows:
            sz = pick(rows[0], "zip_code", "zcta", "zip", label="states")
            st = pick(rows[0], "state", "st", "state_code", label="states")
            for r in rows:
                inst.state[norm_id(r[sz])] = str(r[st]).strip().upper()

    # --- graph -----------------------------------------------------------------
    edges = read_edges(graph_path, u_col, v_col)
    keep = {cell_zip(cell) for cell in inst.m_rel}
    inst.edges = [(u, v) for u, v in edges if u in keep and v in keep]

    # --- candidate structure ---------------------------------------------------
    # counted per cell: with channels present a zip is contested in one channel and
    # untapped in another, and the decision the histogram describes is per cell.
    ncand = Counter(len(inst.share.get(cell, {})) for cell in inst.m_rel)
    n_vacant = sum(1 for cell in inst.m_rel
                   if not inst.share.get(cell) and inst.free.get(cell, 0.0) > 0)
    n_untapped = sum(1 for cell in inst.m_rel
                     if not inst.share.get(cell) and not inst.free.get(cell, 0.0))
    inst.report = dict(
        n_zips=len(keep),
        n_edges=len(inst.edges),
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
    if channelled:
        inst.report["channels"] = list(inst.channels)
        inst.report["kappa_channel"] = kappa_channel
        inst.report["n_cells"] = len(inst.m_rel)
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

    if not inst.edges:
        problems.append("no edges survived the join to the zip set")
    return problems


def mask_reps(inst):
    """Surrogate integer ids, assigned in descending total share.  The map stays local.

    Defence in depth: the upstream extract is already masked, so this is a second pass whose
    only job is to guarantee no upstream label -- however innocuous it looks -- rides along.

    With channels present the ranking runs over the kappa channel's cells first and the
    remaining reps follow.  The kappa channel's rows are the same data the single-channel
    export was built from, so its reps rank among themselves exactly as they did there and
    keep the ids they already have; reps seen only in the other channels are numbered after
    the last of them.  Without that, one new rep with a large book would shift every id and
    silently break every comparison against the existing instance.  Firm labels are numbered
    the same way, for the same reason.
    """
    total, ref = defaultdict(float), defaultdict(float)
    for cell, d in inst.share.items():  # noqa: PLC0206
        for rep, s in d.items():
            total[rep] += s * inst.m_rel[cell]
            if cell_chan(cell) == inst.kappa_channel:
                ref[rep] += s * inst.m_rel[cell]

    def key(r):
        # (-ref, str) inside the kappa channel: exactly the single-channel rule, including
        # its tie-break, so nothing about the other channels can perturb that order.
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


def check_rep_ids(inst, path):
    """Cross-check the surrogate ids against an earlier export, after `mask_reps`.

    The exported file carries surrogate ids only, so there is nothing in it to map a raw rep
    id back to one; the ids line up because `mask_reps` ranks the kappa channel first, and
    nothing is carried over from the file.  What the file does carry is each surrogate's
    share vector, and the kappa channel is meant to be the same data it was built from, so
    those vectors must match zip for zip.  A mismatch means an id now stands for a different
    rep, or that the channel's data moved.  Every comparison against that file would then be
    silently wrong, so it stops the export.

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
    for cell, d in inst.share.items():
        z = cell_zip(cell)
        if cell_chan(cell) != inst.kappa_channel or z not in zips:
            continue
        for rep, s in d.items():
            new_vec[rep][z] = rsig(s)

    bad = [rep for rep, vec in sorted(old_vec.items()) if new_vec.get(rep) != vec]
    if bad:
        raise GuardError(
            f"{len(bad)} of {len(old_vec)} rep id(s) in {os.path.basename(path)} no longer "
            f"carry the same book in the {inst.kappa_channel or 'single'} channel "
            f"(e.g. {bad[:8]}). Either that channel's rows are not the same data the file "
            f"was built from, or a filler key differs from the earlier run. Settle it "
            f"before exporting: the ids are how every result maps back.")
    fresh = [r for r in inst.firm if r not in old.get("firm", {})]
    retired = sorted(set(old.get("firm", {})) - set(old_vec))
    return dict(checked=len(old_vec), fresh=len(fresh), retired=len(retired))


# -------------------------------------------------------------- footprint report
CRUMB_SHARE = 0.01                # components below this share of M are reported, not sized


def components(inst):
    """Connected components of the footprint graph, as lists of zips (largest M first)."""
    mass = zip_mass(inst)
    parent = {z: z for z in mass}

    def find(z):
        while parent[z] != z:
            parent[z] = parent[parent[z]]
            z = parent[z]
        return z

    for u, v in inst.edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    groups = defaultdict(list)
    for z in mass:
        groups[find(z)].append(z)
    return sorted(groups.values(), key=lambda zs: -sum(mass[z] for z in zs))


def alloc_ceiling(shares, k):
    """Best integer split of k districts over disconnected components, on shares alone.

    Mirrors `td/channel.py::allocate_districts` (cross-checked by the repo's tests): each
    component c gets k_c >= 1 districts, and within c the best conceivable outcome is k_c
    equal districts of M_c/k_c -- an upper bound on any real partition.  Maximises
    sum_c k_c*log(M_c/k_c); also returns the spread-minimising allocation, which is
    generally a different budget.  Shares suffice: the objective is scale-invariant.
    """
    n = len(shares)
    if k < n:
        return None
    best = tight = None

    def spread(acc):
        sizes = [m / kc for m, kc in zip(shares, acc) for _ in range(kc)]
        return (max(sizes) - min(sizes)) / (sum(sizes) / len(sizes))

    def walk(i, left, acc):
        nonlocal best, tight
        if i == n - 1:
            acc = acc + [left]
            val = sum(kc * math.log(m / kc) for m, kc in zip(shares, acc))
            if best is None or val > best[0]:
                best = (val, acc)
            sp = spread(acc)
            if tight is None or sp < tight[0]:
                tight = (sp, acc)
            return
        for kc in range(1, left - (n - i - 1) + 1):
            walk(i + 1, left - kc, acc + [kc])

    walk(0, k, [])
    return dict(alloc=best[1], spread=spread(best[1]),
                min_spread=tight[0], min_spread_alloc=tight[1])


def footprint_text(inst):
    """Components of the footprint and the balance ceiling, in shares -- no currency amount.

    These are the four numbers stage 1 is blocked on: a contiguous district cannot span two
    components, so the per-component opportunity shares bound the reachable balance before
    any solver runs.  Read the share column off this report; nothing here needs to leave as
    a file.
    """
    comps = components(inst)
    mass = zip_mass(inst)
    total = sum(mass.values())
    if not comps or total <= 0:
        return "\nfootprint: no zips with positive opportunity\n"

    rows, crumb_zs, crumb_share = [], 0, 0.0
    sized = []                                  # shares entering the ceiling
    for zs in comps:
        share = sum(mass[z] for z in zs) / total
        if share < CRUMB_SHARE:
            crumb_zs += len(zs)
            crumb_share += share
            continue
        st = Counter(inst.state.get(z, "") for z in zs
                     if inst.state.get(z))
        label = " ".join(s for s, _ in st.most_common(3)) or "?"
        rows.append((share, len(zs), label))
        sized.append(share)

    L = ["", "footprint components (a contiguous district cannot span two)", "-" * 46,
         "  share of M      zips   states"]
    for share, nz, label in rows:
        L.append(f"  {share:>9.1%} {nz:>9,}   {label}")
    if crumb_zs:
        n_crumbs = len(comps) - len(rows)
        L += [f"  {crumb_share:>9.1%} {crumb_zs:>9,}   in {n_crumbs} crumb component(s) "
              f"below {CRUMB_SHARE:.0%} each",
              "  NOTE every component must host a whole district, so each crumb would be",
              "  one on its own -- decide upstream whether crumbs join the channel at all."]

    n = len(sized)
    L += ["", "balance ceiling (k_c equal districts per component; crumbs excluded)",
          "-" * 46,
          "  k   districts/component     ceiling spread   best possible spread"]
    for k in range(n, n + 6):
        c = alloc_ceiling(sized, k)
        agree = "  (same split)" if c["alloc"] == c["min_spread_alloc"] else ""
        L.append(f"  {k}   {'/'.join(map(str, c['alloc'])):<22}    {c['spread']:>8.1%}"
                 f"       {c['min_spread']:>8.1%}{agree}")
    L += ["", "  spread = (max - min)/mean district size.  A real contiguous partition can",
          "  only be worse than the ceiling; if every k misses the band, move k or the band.",
          ""]
    return "\n".join(L)


# ------------------------------------------------------------------------ write
def guard(payload):
    """Refuse to emit anything that looks like a currency amount, or an upstream label.

    Shares are in [0,1] by construction and m_rel is a ratio to the median, so a value in the
    thousands means the descaling did not happen.  This is the last line before the file is
    written, not a diagnostic.

    The median is taken over the kappa channel's rows only, the ones whose median is 1.0 by
    construction.  Over every row it would be a different statistic: a channel that is a
    third of national has m_rel around a third, and a file that is mostly such rows would
    fail a test it was never meant to be judged by.
    """
    ms = payload["nodes"]["m_rel"]
    if not ms:
        raise GuardError("no nodes to write")
    chans = payload["nodes"].get("channel")
    ref = payload.get("meta", {}).get("kappa_channel", "")
    ref_ms = [m for m, c in zip(ms, chans) if c == ref] if chans else ms
    if not ref_ms:
        raise GuardError(f"no {ref!r} rows to check the descaling against")
    med = sorted(ref_ms)[len(ref_ms) // 2]
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
    for key in guard.filler_keys:
        if key and key in json.dumps(payload):
            raise GuardError(f"filler key {key!r} appears in the payload; the sentinel's "
                             f"own name must not leave -- only the count does")
    # kappa_channel is a channel name, not the divisor; everything else named kappa is.
    meta = {k: v for k, v in payload.get("meta", {}).items() if k != "kappa_channel"}
    if "kappa" in json.dumps(meta):
        raise GuardError("meta carries kappa; the divisor must not leave")


guard.filler_keys = ()          # set by `write`; checked above against the whole payload


def write(inst, out_dir, theta, lam, verbose=True, filler_keys=()):
    """Write the instance.  Format 2 when the extract carried channels, format 1 when not.

    Format 2 is format 1 with the node table long by (zip, channel) and a `channel` column
    beside it, plus `channels` and `kappa_channel` in meta.  Every other field, the rounding
    and the graph hash are the same, and a channel-less run writes exactly what it always
    wrote.
    """
    os.makedirs(out_dir, exist_ok=True)
    rank = {c: i for i, c in enumerate(inst.channels)}
    cells = sorted(inst.m_rel,
                   key=lambda cell: (cell_zip(cell), rank.get(cell_chan(cell), len(rank))))
    zips = sorted({cell_zip(cell) for cell in cells})
    nodes = dict(
        z=[cell_zip(cell) for cell in cells],
        m_rel=[rsig(inst.m_rel[cell]) for cell in cells],
        share=[{r: rsig(s) for r, s in sorted(inst.share.get(cell, {}).items())}
               for cell in cells],
        share_free=[rsig(inst.free.get(cell, 0.0)) for cell in cells],
        state=[inst.state.get(cell_zip(cell), "") for cell in cells],
    )
    if inst.channels:
        nodes["channel"] = [cell_chan(cell) for cell in cells]
    scale = "descaled: M/median(positive M); shares dimensionless"
    if inst.channels:
        scale = (f"descaled: M/median(positive M over {inst.kappa_channel} rows); "
                 f"shares dimensionless")
    payload = dict(
        format=FORMAT_V2 if inst.channels else FORMAT_V1,
        nodes=nodes,
        edges=dict(u=[u for u, _ in inst.edges], v=[v for _, v in inst.edges]),
        firm=inst.firm,
        meta=dict(
            exporter="export_instance", version=__version__,
            theta=theta, lam=lam, scale=scale,
            graph_hash=graph_hash(zips, inst.edges),
            **{k: v for k, v in inst.report.items() if k != "kappa"},
        ),
    )
    guard.filler_keys = tuple(filler_keys)
    guard(payload)
    path = os.path.join(out_dir, "instance_descaled.json.gz")
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"), sort_keys=True)
    if verbose:
        print(f"wrote {path}  ({os.path.getsize(path)/1e6:.2f} MB)")
    return path


def report_text(inst):
    r = inst.report
    L = ["", "what this export contains", "-" * 46,
         f"  zips                 {r['n_zips']:>10,}",
         f"  edges                {r['n_edges']:>10,}",
         f"  reps                 {r['n_reps']:>10,}",
         f"  sales rows joined    {r['join_rate']:>10.4f}"]
    if inst.channels:
        L += [f"  cells (zip, channel) {r['n_cells']:>10,}",
              f"  channels             {' '.join(inst.channels):>10}   "
              f"kappa from {inst.kappa_channel}",
              "",
              "  every count below is per CELL, not per zip: a zip is contested in one",
              "  channel and untapped in another, and the decision is per cell."]
    L += ["",
         "candidate structure (cand(z) = real reps with positive sales)", "-" * 46,
         f"  untapped   (0 reps)  {r['zips_untapped']:>10,}   no sales at all; adjacency only",
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
         "surrogate rep ids, public ZCTA ids and edges. No currency amount.", ""]
    return "\n".join(L)


# -------------------------------------------------------------------------- cli
def main(argv=None):
    p = argparse.ArgumentParser(prog="export_instance", description=__doc__.split("\n")[0])
    p.add_argument("cmd", choices=["validate", "export"])
    p.add_argument("--sales", required=True,
                   help="zip_code, rep_id, firm, sales (long), optionally current_channel")
    p.add_argument("--opportunity", required=True,
                   help="zip_code, M, optionally current_channel")
    p.add_argument("--graph", required=True, help="edge table (parquet/feather/csv)")
    p.add_argument("--states", default=None, help="zip_code, state (optional)")
    p.add_argument("--out", default="./out")
    p.add_argument("--theta", type=float, default=THETA_DEFAULT)
    p.add_argument("--lam", type=float, default=0.30)
    p.add_argument("--u-col", default=None)
    p.add_argument("--v-col", default=None)
    p.add_argument("--impute-missing-m", action="store_true",
                   help="a zip with book but no (or nonpositive) opportunity value gets "
                        "M = its total book -- the conservative floor: no upside, zip "
                        "stays in the graph. Off by default; the count is reported.")
    p.add_argument("--repair-headroom", action="store_true",
                   help="where M is smaller than the book it must contain, lift it to "
                        "exactly the pointwise-headroom floor max_i(S_i + theta*(T-S_i)). "
                        "The minimal repair for messy opportunity data; off by default, "
                        "count and added share are reported.")
    p.add_argument("--join-floor", type=float, default=JOIN_FLOOR,
                   help=f"minimum share of positive sales rows that must join to an "
                        f"opportunity zip (default {JOIN_FLOOR}). Lower it only after "
                        f"reading the failure report: unjoined rows are dropped.")
    p.add_argument("--filler-key", action="append", default=[], metavar="KEY",
                   help="a rep_id that marks a VACANCY rather than a person. Repeatable. "
                        "Its sales stay in the instance as unowned book but it never "
                        "becomes a candidate owner.")
    p.add_argument("--rep-ids", default=None, metavar="PATH",
                   help="an earlier single-channel export (instance_descaled*.json.gz) to "
                        "cross-check the surrogate ids against. Nothing is carried into the "
                        "export from it: the ids line up because the kappa channel is "
                        "ranked first. This "
                        "asserts they did, and stops the export if that channel's book "
                        "moved. Compares only the zips that file kept.")
    p.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    a = p.parse_args(argv)

    try:
        inst = build(a.sales, a.opportunity, a.graph, a.states, theta=a.theta,
                     u_col=a.u_col, v_col=a.v_col, filler_keys=a.filler_key,
                     join_floor=a.join_floor, impute_missing_m=a.impute_missing_m,
                     repair_headroom=a.repair_headroom)
    except InputError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 4

    print(report_text(inst))
    print(footprint_text(inst))
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

    mask_reps(inst)
    if a.rep_ids:
        try:
            c = check_rep_ids(inst, a.rep_ids)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
