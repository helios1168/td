"""score.py -- the looks scorer (td#93): eligibility and the four rank keys of drawn runs.

    "$TD_PY" tools/looks/score.py <run_dir> [<run_dir> ...] [--extract <instance.json.gz>]

`score(run_dir)` returns the dict without printing (the interface #92's tools load by path):
`eligible`, `splits`, `thin_links`, `small_pieces`, `crowded_states`, `contiguity_pieces`,
`contiguity_weight`, `defects`, `largest_piece_tau`, `multipart_pieces`, `largest_extent_km`, `states_per_district`,
`worst_dev`, `mean_dev` (fractions), and details.  `rank(scores)` orders runs by the keys and sets
`review`.

A run directory has the layout `python -m td run` writes: `ledger.csv`, `districts.csv`,
`run.json`, `scorecard.md`.  Every measure comes from the drawn ledger, which since #116 owns
every ZCTA of each channel's footprint, zero-opportunity ones included.  The small-piece, crowded
and thin-link rules are those of `runs/sweep/comb_2026-10-02/summarize5.py` (m5, gitignored),
with the display fill made deterministic; the display fill sizes no piece.

A map is **eligible** when (PROBLEM.md row 2026-10-04, `runs/plan_2026-10-04/EXPERIMENTS.md` §1):
- the audit passes at a plain ±`BAND` band: no check of `scorecard.md` other than the band check
  fails, and `td.audit.check_bands` passes on the ledger with every channel's band τ_c(1 ± BAND),
  τ_c = the channel's ledger total / K_c.  A run scored with a dollar gate (main map or IFA)
  is exempt: the gate below replaces it, and the band stays information;
- a main-map run (any run but an IFA-only one) passes the dollar gate (`dollar_gate`, main-map
  overnight grid, 2026-10-13): every district's $ lies in its channel's `WINDOWS`, edges
  included, compared in unrounded dollars, and a channel without a window fails.  A district of a
  channel in `WHOLE_STATE_CAP` (WIFI) that owns alone, in its channel, every state it owns a
  ZCTA in may reach the cap, and its row says it took the allowance.  The IFA district owning
  alone every state it holds and holding exactly MD, DE and WV is the one waiver (PROBLEM.md,
  #130): above its window, not below it, its row says `waiver`, and `report` names it.
  `--dollars-csv` writes the rows to each run's `dollars.csv`.  $ is m_rel times the owner's dollar total over the
  extract's m_rel total, per fine channel (`DOLLARS`), summed over the district's drawn cells; on
  a dollar extract (`tools/exp/contig/dollarize.py`, $M) that rate is 1e6 for every fine
  channel;
- an IFA-only run passes the same district gate against `IFA_WINDOW` ($1,000M-$1,437.5M, edges
  included, unrounded dollars; #105, owner, 2026-10-15), $ being the ledger's unrounded m_rel times
  `td.spec.IFA_USD_PER_M_REL` (an IFA ledger keeps the original m_rel units, whatever the extract's
  rate), and also averages a $ per district within ±`DOLLAR_BAND` of its `TARGET`, edges
  included, compared in whole dollars, $ being the owner's whole-extract IFA total over K (owner,
  2026-10-04), the `dollars` it reports.  A run scored by `eligibility` without a gate is held
  to the same average rule on every channel with a target, a channel without one, such as a
  combined channel (D11), printed but not checked;
- the main map's total K is in `MAIN_K`; an IFA-only run is exempt;
- M1 holds (#108): `td.audit.check_m1` passes on the ledger with the committed polygon graph and
  its owner-approved connectors (`td.geo.polygon_graph`): every district one piece, every CONUS
  ZCTA owned in every channel.  Without a polygon graph M1 is unverified, and the run is not
  eligible.  The run's own scorecard M1, which also checks each cell's planning channel against
  the scenario, must not fail either (#116).  Necks follow the owner's 2026-10-14 rule
  (`td.audit.check_m1`): connectors unlimited, land in no ZCTA (G1, #131) and zero-opportunity
  ZCTAs of the channel count towards a passage; `td.audit.GAP_WIDTH_ENV` = "0" opts out of the
  gap land and `td.audit.LAND_RULE_ENV` = "1" back into the pre-2026-10-14 land rule.
  `m1_both` gives the verdict with gap land off (`strict`) and on (`gap_width`) and the districts
  they disagree on (by a neck or a detached piece, R5), and `--m1-json` writes them to each run's `m1.json`;
- the folder is not diagnostic (#121, `td.audit.diagnostic`): a run held to a diagnostic band,
  or derived from one, is INELIGIBLE with the reason "diagnostic band".

Rank keys, compared in order, fewest or smallest first:
1. **splits**: channel-state splits, Σ_c the states where two or more of c's districts own a ZCTA,
   zero-opportunity ones included, on the drawn map (owner, 2026-10-05, council decision 1; PA
   split in WH and in FI counts 2); `distinct` is the set of split states;
2. **defects** = thin_links + small_pieces + crowded_states + contiguity_weight, each printed:
   - thin: a district's piece in one state whose ZIP border with its pieces in its other states
     is under `THIN_KM`, measured on the display fill (every ZIP with no cell in the channel joins
     the nearest district of its state, by breadth-first search on the ZIP graph);
   - small: a district's piece of a split state under `SMALL_TAU` τ;
   - crowded: a split state with more than ceil(M_s / τ) + 1 districts;
   - pieces: components of each district's ledger ZCTAs on the M1 polygon graph beyond the
     heaviest (`td.audit.district_pieces`), the pieces `td.audit.check_m1` lists, each weighing
     1 + its ledger mass / τ (owner, 2026-10-05, #108), so a 0.45τ island weighs 1.45 and a 2-ZIP
     zero-mass piece 1; `contiguity_pieces` counts them and `largest_piece_tau` is the heaviest.
     No display fill sizes them (#116): the ledger owns every ZCTA, so the audit's piece list is
     the one count, and `audit_pieces`, M1's count read from `scorecard.md`, is printed beside it;
   - necks, listed from M1 (#121) and not in the sum: M1 fails a map with one, so an eligible
     map has none; the necks by mass M1 lists beside it, for the owner, are printed too;
   - multipart pieces, listed and counted (`multipart_pieces`) but not in the sum: a separate
     piece of a district's drawn union that only a multipart ZCTA makes is a visual defect, not
     an M1 failure (owner, 2026-10-05, #108).  Most are islets of coastal ZCTAs, drawn apart
     whatever the plan, so the count barely tells two maps apart;
3. **shape**: largest_extent_km (the longest distance between two ZIP points one district holds,
   km, as #81's `measure.extent_km`), then states_per_district, the most states one district
   owns a ZCTA in, zero-opportunity ones included (council decision 1);
4. **balance**: worst_dev, then mean_dev, of |drawn mass / channel mean − 1| over all districts.

**REVIEW** (owner D2): across the eligible runs scored together, a run with one split more than
the fewest and strictly fewer defects than every run at the fewest stays, flagged
`REVIEW: +1 split for -n defects`, n against the fewest defects at the fewest splits.
"""
from __future__ import annotations

import argparse
import collections
import csv
import functools
import gzip
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo           # noqa: E402
from td import spec as tdspec              # noqa: E402

HUB = os.environ.get("TD_REPO", ROOT)
BAND = 0.15
DOLLAR_BAND = 0.10
MAIN_K = (48, 54)
THIN_KM = 25.0
SMALL_TAU = 0.20
TARGET = {"national": 1.25e9, "WH": 1.0e9, "FI": 0.9e9, "IFA": 1.25e9}          # $ per district
DOLLARS = {"wh": 11.36e9, "fi": 20.69e9, "wells_wh": 4.44e9, "wells_fi": 4.63e9,  # owner's totals,
           "national_chase": 8.55e9, "ifa": 62.14e9}                              # 2026-10-01
WINDOWS = {"national": (1.0e9, 1.4375e9), "WH": (0.85e9, 1.15e9),      # $ per district, the main
           "FI": (0.765e9, 1.035e9), "WIFI": (0.85e9, 1.15e9)}           # map's gate (2026-10-13)
WHOLE_STATE_CAP = {"WIFI": 1.6e9}       # a district of whole states only (owner, 2026-10-13)
WAIVER = {"IFA": frozenset({"MD", "DE", "WV"})}    # the one IFA waiver district: exactly these states
DOLLAR_COLUMNS = ["channel", "district", "usd_m", "lo_m", "hi_m", "whole_state_cap_m", "states",
                  "whole_states", "allowance", "waiver", "ok"]       # (owner, 2026-10-08, #130)
IFA_ONLY = {"IFA"}
IFA_WINDOW = {"IFA": tuple(m * 1e6 for m in tdspec.IFA_WINDOW_M)}      # $ per district, IFA-only runs
IFA_RATES = {"ifa": tdspec.IFA_USD_PER_M_REL * 1e6}     # $ per m_rel; IFA ledgers keep original units
BAND_CHECK = "final bands on drawn mass"
NECK = re.compile(r"^[^:]+: neck ")       # M1's neck items (`td.audit.neck_item`)
PIECE = re.compile(r"^[^:]+: detached piece ")   # M1's detached-piece items (`td.audit.check_m1`)


class Geography:
    """The 2025 reference: `state` {zip: state}, `xy` {zip: (x, y) km}, `edge` {zip: {zip: border
    km}} over the ZIP graph's edges, `polygon`, M1's graph (`td.geo.polygon_graph`), or None, and
    `parts`, the polygon parts: `{"area": {zip: [m2 per part]}, "edges": [(a, a_part, b, b_part,
    kind)]}` (`td.geo.part_edges`), or None."""

    def __init__(self, state: dict, xy: dict, edge: dict, polygon: dict | None = None,
                 parts: dict | None = None):
        self.state, self.xy, self.edge, self.polygon = state, xy, edge, polygon
        # the pieces M1 lists: land-only gap edges join them unless G1 is off (R5, owner, 2026-10-14)
        self.polygon_adj = audit.adjacency(polygon, gaps=audit.gap_width_on()) if polygon is not None else None
        self.parts = parts
        self.part_adj = part_adjacency(polygon, parts) if polygon and parts else None

    @classmethod
    def load(cls, ref_dir: str = geo.REFERENCE_DIR) -> "Geography":
        ref = geo.read_reference(ref_dir)
        state = dict(zip(ref["zcta"], ref["state"]))
        xy = {z: (float(x) / 1000.0, float(y) / 1000.0)
              for z, x, y in zip(ref["zcta"], ref["x"], ref["y"]) if x and y}
        edge = collections.defaultdict(dict)
        with gzip.open(os.path.join(ref_dir, "zcta_graph_edges.csv.gz"), "rt") as fh:
            for r in csv.DictReader(fh):
                b = float(r["border_m"] or 0) / 1000.0
                edge[r["a"]][r["b"]] = b
                edge[r["b"]][r["a"]] = b
        parts = None
        if os.path.exists(os.path.join(ref_dir, geo.ZCTA_PARTS)):
            area = collections.defaultdict(list)
            for z, a in zip(*geo.read_reference(ref_dir, geo.ZCTA_PARTS)[["zcta", "area_m2"]].T.values):
                area[z].append(float(a))
            pe = geo.read_reference(ref_dir, geo.PART_EDGES)
            parts = {"area": dict(area), "edges": [(a, int(i), b, int(j), k) for a, i, b, j, k in
                                                   pe[["a", "a_part", "b", "b_part", "kind"]].values]}
        return cls(state, xy, edge, geo.polygon_graph(ref_dir), parts)


def part_adjacency(polygon: dict, parts: dict) -> dict:
    """{(zip, part): set of (zip, part)}: the polygon graph at part level.  An edge between two
    single-part ZCTAs joins their part 0; one with a multipart end joins the part pairs `parts`
    lists for it, its `connector` rows only when the pair is an edge of `polygon` (approved)."""
    n = {z: len(a) for z, a in parts["area"].items()}
    adj = {(z, k): set() for z in polygon["vertices"] for k in range(n.get(z, 1))}
    pairs = {tuple(sorted(e[:2])) for e in polygon["edges"]}
    listed = set()
    for a, i, b, j, kind in parts["edges"]:
        if (a, b) in pairs and (a, i) in adj and (b, j) in adj:
            adj[a, i].add((b, j))
            adj[b, j].add((a, i))
            listed.add((a, b))
    for a, b in pairs - listed:
        if n.get(a, 1) == 1 and n.get(b, 1) == 1 and (a, 0) in adj and (b, 0) in adj:
            adj[a, 0].add((b, 0))
            adj[b, 0].add((a, 0))
    return adj


def multipart_pieces(owner: dict, g: Geography) -> list:
    """[(district, ZIPs, km2)]: each separate piece of a district's drawn union that only a
    multipart ZCTA makes (owner, 2026-10-05): within each component of the district's ZIPs on the
    polygon graph, the components of their parts on `g.part_adj` beyond the largest by area."""
    out = []
    for d, comps in audit.district_pieces(owner, g.polygon_adj, {}).items():
        for comp in comps:
            if all(len(g.parts["area"].get(z, (0,))) == 1 for z in comp):
                continue
            nodes = {(z, k) for z in comp for k in range(len(g.parts["area"].get(z, (0,))))}
            got = audit._components(nodes, g.part_adj)
            area = [(math.fsum(g.parts["area"][z][k] for z, k in c), c) for c in got]
            area.sort(key=lambda ac: (-ac[0], min(ac[1])))
            out += [(d, "+".join(sorted({z for z, _ in c})), round(a / 1e6, 3)) for a, c in area[1:]]
    return out



def extent_km(points: list) -> float:
    """The largest distance between two of `points` (km), over their convex hull."""
    if len(points) < 2:
        return 0.0
    import numpy as np
    pts = np.unique(np.asarray(points, dtype=float), axis=0)
    if len(pts) > 3:
        from scipy.spatial import ConvexHull, QhullError
        try:
            pts = pts[ConvexHull(pts).vertices]
        except QhullError:          # collinear points: the brute force below is exact
            pass
    d = pts[:, None, :] - pts[None, :, :]
    return float(np.sqrt((d ** 2).sum(-1)).max())


def display_fill(own: dict, g: Geography) -> dict:
    """{zip: district}: `own` spread to every ZIP of the same state reachable on the ZIP graph,
    breadth first.  A tie goes to the ZIP earlier in `own`'s order, then in the edge file's, as
    in summarize5."""
    fill, frontier = dict(own), list(own)
    while frontier:
        nxt = []
        for z in frontier:
            for w in g.edge.get(z, ()):
                if w not in fill and g.state.get(w) == g.state.get(z):
                    fill[w] = fill[z]
                    nxt.append(w)
        frontier = nxt
    return fill


def channel_looks(ch: str, ledger: list, districts: list, g: Geography) -> dict:
    """Balance and looks of channel `ch` from its ledger rows and its `districts.csv` rows."""
    rows = [r for r in districts if r["channel"] == ch]
    tau = sum(float(r["drawn_mass"]) for r in rows) / len(rows)
    dev = {r["district"]: float(r["drawn_mass"]) / tau - 1 for r in rows}
    mass = collections.defaultdict(collections.Counter)          # district -> state -> mass
    held = collections.defaultdict(lambda: collections.defaultdict(set))
    smass = collections.Counter()
    for r in ledger:
        if r["model_channel"] == ch and r["district"]:
            m = float(r["m_rel"])
            mass[r["district"]][r["state"]] += m
            smass[r["state"]] += m
            held[r["district"]][r["state"]].add(r["zip_code"])
    owners = collections.defaultdict(set)          # a ZCTA owned splits its state (#116)
    for d, bys in held.items():
        for s in bys:
            owners[s].add(d)
    split = sorted(s for s, ds in owners.items() if len(ds) > 1)
    small = sorted((d, s, round(mass[d][s] / tau, 3)) for s in split for d in owners[s]
                   if mass[d][s] / tau < SMALL_TAU)
    crowded = [s for s in split if len(owners[s]) > math.ceil(smass[s] / tau) + 1]
    own = {z: d for d, bys in held.items() for zs in bys.values() for z in sorted(zs)}
    filled = collections.defaultdict(lambda: collections.defaultdict(set))
    for z, d in display_fill(own, g).items():
        filled[d][g.state[z]].add(z)
    thin, pieces, multipart = [], [], None
    if g.polygon_adj is not None:
        zip_mass = collections.Counter()
        for r in ledger:
            if r["model_channel"] == ch and r["district"]:
                zip_mass[r["zip_code"]] += float(r["m_rel"])
        owner = {z: d for d, bys in held.items() for zs in bys.values() for z in zs}
        for d, comps in audit.district_pieces(owner, g.polygon_adj, zip_mass).items():
            pieces += [(d, len(c), round(math.fsum(zip_mass[z] for z in c) / tau, 4),
                        "+".join(sorted({g.state.get(z, "?") for z in c}))) for c in comps[1:]]
        if g.part_adj is not None:
            multipart = multipart_pieces(owner, g)
    for d in sorted(filled):
        bys = filled[d]
        states = [s for s in sorted(bys) if mass[d][s] > 0]
        if len(states) < 2:
            continue
        for s in states:
            other = set().union(*(bys[t] for t in states if t != s))
            km = sum(g.edge[z].get(w, 0) for z in bys[s] for w in g.edge.get(z, ()) if w in other)
            if km < THIN_KM:
                thin.append((d, s, round(km, 1)))
    extent = max(extent_km([g.xy[z] for zs in bys.values() for z in zs if z in g.xy])
                 for bys in held.values())
    return {"k": len(rows), "tau": tau, "deviation": dev, "split": split, "small": small,
            "crowded": crowded, "thin": thin, "multipart": multipart,
            "pieces": None if g.polygon_adj is None else sorted(pieces, key=lambda p: (-p[2], p)),
            "extent_km": extent,
            "max_states": max(len(bys) for bys in held.values())}     # owned ZCTAs (#116)


def dollar_rates(extract: data.Extract) -> dict:
    """{fine channel: $ per m_rel}: the owner's total over the extract's m_rel total."""
    total = collections.Counter()
    for c, m in zip(extract.channel, extract.m_rel):
        total[c] += m
    return {f: DOLLARS[f] / total[f] for f in DOLLARS if total[f] > 0}


def _need_rates(ch: str, ledger: list, rates: dict) -> None:
    fine = {r["current_channel"] for r in ledger if r["model_channel"] == ch and r["district"]}
    missing = sorted(fine - set(rates))
    if missing:
        raise ValueError(f"channel {ch}: no dollar total for fine channel(s) {', '.join(missing)}")


def dollars_per_district(ch: str, k: int, ledger: list, rates: dict) -> float:
    _need_rates(ch, ledger, rates)
    return sum(float(r["m_rel"]) * rates[r["current_channel"]] for r in ledger
               if r["model_channel"] == ch and r["district"]) / k


def district_dollars(ch: str, ledger: list, rates: dict) -> dict:
    """{district: $} of channel `ch`: m_rel times its fine channel's rate over the district's
    drawn cells."""
    _need_rates(ch, ledger, rates)
    out = collections.Counter()
    for r in ledger:
        if r["model_channel"] == ch and r["district"]:
            out[r["district"]] += float(r["m_rel"]) * rates[r["current_channel"]]
    return out


def dollar_gate(ledger: list, districts: list, rates: dict, windows: dict = WINDOWS) -> list:
    """The dollar gate, one row per `districts.csv` row: `usd`, its channel's window in `windows`
    `lo`, `hi` (None without one), `states` it owns a ZCTA in, `whole_states` when it owns each
    alone in its channel, `cap`, the channel's `WHOLE_STATE_CAP` for such a district (else None),
    `allowance` when its $ is above `hi` and within the cap, `waiver` when it is the channel's
    `WAIVER` district (whole, exactly those states) at or above `lo`, and `ok`.  Unrounded dollars,
    edges included; a channel without a window is never ok."""
    owners = collections.defaultdict(set)          # (channel, state) -> districts owning a ZCTA
    states = collections.defaultdict(set)          # (channel, district) -> states
    for r in ledger:
        if r["district"]:
            owners[r["model_channel"], r["state"]].add(r["district"])
            states[r["model_channel"], r["district"]].add(r["state"])
    usd, out = {}, []
    for row in sorted(districts, key=lambda r: (r["channel"], r["district"])):
        ch, d = row["channel"], row["district"]
        if ch not in usd:
            usd[ch] = district_dollars(ch, ledger, rates)
        x, st = usd[ch].get(d, 0.0), sorted(states[ch, d])
        whole = bool(st) and all(owners[ch, s] == {d} for s in st)
        lo, hi = windows.get(ch, (None, None))
        cap = WHOLE_STATE_CAP.get(ch) if whole else None
        inside = lo is not None and lo <= x <= hi
        allowance = not inside and lo is not None and cap is not None and lo <= x <= cap
        waiver = (not inside and lo is not None and whole and x >= lo
                  and frozenset(st) == WAIVER.get(ch))
        out.append({"channel": ch, "district": d, "usd": x, "lo": lo, "hi": hi, "states": st,
                    "whole_states": whole, "cap": cap, "allowance": allowance, "waiver": waiver,
                    "ok": inside or allowance or waiver})
    return out


def gate_reason(r: dict) -> str:
    """Why a `dollar_gate` row fails."""
    if r["lo"] is None:
        return f"$ {r['district']}: no dollar window for {r['channel']}"
    cap = f" (whole states: up to {r['cap'] / 1e6:,.1f}M)" if r["cap"] is not None else ""
    return (f"$ {r['district']} {r['usd'] / 1e6:,.1f}M outside {r['lo'] / 1e6:,.1f}-"
            f"{r['hi'] / 1e6:,.1f}M{cap}")


def write_dollars(path: str, gate: list) -> None:
    """`dollars.csv`: the `dollar_gate` rows, $ in $M at round-trip precision."""
    def m(v):
        return "" if v is None else repr(v / 1e6)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(DOLLAR_COLUMNS)
        for r in gate:
            w.writerow([r["channel"], r["district"], m(r["usd"]), m(r["lo"]), m(r["hi"]), m(r["cap"]),
                        ";".join(r["states"]), int(r["whole_states"]), int(r["allowance"]), int(r["waiver"]),
                        int(r["ok"])])


def scorecard_checks(text: str) -> dict:
    """{check name: status} from the table of a `scorecard.md`."""
    out = {}
    for line in text.splitlines():
        m = re.fullmatch(r"\| (.+?) \| (pass|fail|listed|unverified) \| .* \|", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def audit_pieces(text: str) -> int | None:
    """M1's detached pieces in a `scorecard.md`, None without an M1 row."""
    m = re.search(rf"\| {audit.M1_CHECK} \| \w+ \| \d+ districts in pieces, (\d+) detached pieces", text)
    return int(m.group(1)) if m else None


def bands_at(ledger: list, ks: dict, band: float) -> audit.Check:
    """`td.audit.check_bands` on the ledger with every channel's band τ_c(1 ± band)."""
    cells = [audit.Cell(r["zip_code"], r["current_channel"], r["model_channel"], r["district"],
                        float(r["m_rel"])) for r in ledger]
    total = collections.Counter()
    for c in cells:
        total[c.channel] += c.m
    chans = {ch: audit.Channel(k, total[ch] / k * (1 - band), total[ch] / k * (1 + band))
             for ch, k in ks.items()}
    return audit.check_bands(audit.Run(cells, chans))


def m1_check(ledger: list, ks: dict, g: Geography, fine=None, gap_width: bool | None = None,
             land_rule: bool | None = None) -> audit.Check:
    """`td.audit.check_m1` on the drawn ledger with `g`'s polygon graph (strict: no display fill),
    on the scenario's fine channels `fine` (`fine_channels`); None, for a run from before #116,
    takes the ledger's, and the summary says so.  A run folder has no units, so the routing of a
    cell to its planning channel is the run's own scorecard M1's to check.  `gap_width` goes to
    `check_m1`: None reads `td.audit.GAP_WIDTH_ENV` (on unless "0", owner, 2026-10-14); so does
    `land_rule`, the opt-in pre-2026-10-14 land rule (`td.audit.LAND_RULE_ENV`)."""
    cells = [audit.Cell(r["zip_code"], r["current_channel"], r["model_channel"], r["district"],
                        float(r["m_rel"]), reason=r.get("reason", "")) for r in ledger]
    return audit.check_m1(audit.Run(cells, {ch: audit.Channel(k) for ch, k in ks.items()},
                                    polygon=g.polygon, fine=None if fine is None else tuple(fine)),
                          gap_width=gap_width, land_rule=land_rule)


def m1_both(ledger: list, ks: dict, g: Geography, fine=None) -> dict:
    """M1 both ways (G3, the main-map overnight grid, 2026-10-13): `strict`, necks on polygon
    borders (gap land off), and `gap_width`, necks across coverage gaps too (`td.audit.NeckGraph`,
    the default since 2026-10-14; both read connectors and zero-opportunity ZCTAs the new way), each a
    `m1_check`, and `flips`, one row per district that fails one way and not the other, by a neck
    or by a detached piece (R5's land-only gap edges join pieces with the switch on):
    {"district": "channel/district", "strict": its neck and detached-piece items, "gap_width": the
    same}."""
    got = {k: m1_check(ledger, ks, g, fine, gap_width=k == "gap_width") for k in ("strict", "gap_width")}
    bad = {k: collections.defaultdict(list) for k in got}
    for k, c in got.items():
        for i in c.items:
            if NECK.search(i) or PIECE.search(i):
                bad[k][i.split(":", 1)[0]].append(i)
    flips = [{"district": d, "strict": bad["strict"].get(d, []), "gap_width": bad["gap_width"].get(d, [])}
             for d in sorted(set(bad["strict"]) ^ set(bad["gap_width"]))]
    return {**got, "flips": flips}


def write_m1(path: str, both: dict) -> None:
    """`m1.json`: `m1_both`'s verdicts (status, summary, counts, neck and detached-piece items) and
    flips."""
    doc = {k: {"status": c.status, "summary": c.summary, **c.counts,
               "necks": [i for i in c.items if NECK.search(i)],
               "pieces": [i for i in c.items if PIECE.search(i)]}
           for k, c in both.items() if k != "flips"}
    doc["flips"] = both["flips"]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")


def fine_channels(run_dir: str):
    """The scenario's fine channels from the run's `run.json` (#116), or None without them."""
    path = os.path.join(run_dir, "run.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("fine_channels")


def eligibility(checks: dict, bands: audit.Check, ks: dict, dollars: dict,
                m1: audit.Check | None = None, gate: list | None = None) -> list:
    """Why a run is not eligible, one reason per failed rule; empty when it is.  `m1` is the M1
    check; a run without one is not eligible.  `gate`, the `dollar_gate` rows, adds one reason per
    failing district; with a gate the ±`BAND` band is information only, and on a main-map run the
    gate also replaces the per-channel average, which an IFA-only run keeps."""
    gated = gate is not None and set(ks) != IFA_ONLY
    why = [f"audit: {name} fails" for name, s in checks.items() if s == "fail" and name != BAND_CHECK]
    if m1 is None or m1.status != "pass":
        why.append(f"M1: {m1.status}, {m1.summary}" if m1 else "M1: not checked")
    if not checks:
        why.append("audit: no scorecard")
    if bands.status != "pass" and gate is None:
        why.append(f"audit at ±{100 * BAND:.0f}%: {bands.summary}")
    why += [gate_reason(r) for r in gate or () if not r["ok"]]
    for ch, d in sorted(dollars.items()) if not gated else ():
        t = TARGET.get(ch)
        if t is None:
            continue
        lo, hi = round(t * (1 - DOLLAR_BAND)), round(t * (1 + DOLLAR_BAND))   # whole dollars, inclusive
        if round(d) < lo or round(d) > hi:
            why.append(f"$ {ch} {d / 1e6:,.0f}M is {100 * (d / t - 1):+.1f}% of {t / 1e6:,.0f}M")
    total = sum(ks.values())
    if set(ks) != IFA_ONLY and not MAIN_K[0] <= total <= MAIN_K[1]:
        why.append(f"main K {total} outside {MAIN_K[0]}-{MAIN_K[1]}")
    return why


def extract_path(run_dir: str) -> str:
    """The extract a run was solved on: `run.json`'s source under `HUB`."""
    with open(os.path.join(run_dir, "run.json")) as fh:
        return os.path.join(HUB, json.load(fh)["source"])


@functools.lru_cache(maxsize=None)
def geography() -> Geography:
    return Geography.load()


@functools.lru_cache(maxsize=None)
def rates_of(path: str) -> dict:
    return dollar_rates(data.load(path))


def score(run_dir: str, g: Geography | None = None, rates: dict | None = None) -> dict:
    """Eligibility, the rank keys and the per-channel details of one run directory.  `g` and
    `rates` default to the 2025 reference and the run's own extract's rates, each loaded once."""
    g = g or geography()
    with open(os.path.join(run_dir, "ledger.csv"), newline="") as fh:
        ledger = list(csv.DictReader(fh))
    with open(os.path.join(run_dir, "districts.csv"), newline="") as fh:
        districts = list(csv.DictReader(fh))
    sc_path = os.path.join(run_dir, "scorecard.md")
    sc = open(sc_path, encoding="utf-8").read() if os.path.exists(sc_path) else ""
    chans = {ch: channel_looks(ch, ledger, districts, g) for ch in sorted({r["channel"] for r in districts})}
    ks = {ch: c["k"] for ch, c in chans.items()}
    gate = None
    if set(ks) == IFA_ONLY:              # owner, 2026-10-04: the whole-extract IFA total over K
        dollars = {ch: DOLLARS["ifa"] / k for ch, k in ks.items()}
        gate = dollar_gate(ledger, districts, IFA_RATES, IFA_WINDOW)     # #105, owner, 2026-10-15
    else:
        rates = rates if rates is not None else rates_of(extract_path(run_dir))
        dollars = {ch: dollars_per_district(ch, k, ledger, rates) for ch, k in ks.items()}
        gate = dollar_gate(ledger, districts, rates)
    bands = bands_at(ledger, ks, BAND)
    m1 = m1_check(ledger, ks, g, fine_channels(run_dir))
    why = eligibility(scorecard_checks(sc), bands, ks, dollars, m1, gate)
    diag = audit.diagnostic(run_dir)
    if diag is not None:                 # never a deliverable (#121)
        why.insert(0, "diagnostic band" + (f" ({diag['label']})" if diag["label"] else ""))
    devs = [abs(x) for c in chans.values() for x in c["deviation"].values()]
    pieces = [p for c in chans.values() for p in c["pieces"] or ()]
    defects = {"thin_links": sum(len(c["thin"]) for c in chans.values()),
               "small_pieces": sum(len(c["small"]) for c in chans.values()),
               "crowded_states": sum(len(c["crowded"]) for c in chans.values()),
               "contiguity_weight": round(math.fsum(1 + p[2] for p in pieces), 4)}
    return {
        "run": os.path.basename(os.path.normpath(run_dir)), "dir": run_dir,
        "eligible": not why, "why": why, "diagnostic": diag is not None, "k": ks, "dollars": dollars,
        "dollar_gate": gate,
        "m1": {"status": m1.status, "summary": m1.summary, **m1.counts},
        "necks": [i for i in m1.items if NECK.search(i)],
        "mass_necks": [i for i in m1.items if audit.MASS_NECK in i],
        "splits": sum(len(c["split"]) for c in chans.values()),
        "split_list": [f"{ch}:{s}" for ch, c in chans.items() for s in c["split"]],
        "distinct": sorted({s for c in chans.values() for s in c["split"]}),
        "defects": round(math.fsum(defects.values()), 4), **defects,
        "contiguity_pieces": len(pieces),
        "multipart_pieces": None if any(c["multipart"] is None for c in chans.values())
        else sum(len(c["multipart"]) for c in chans.values()),
        "largest_piece_tau": max((p[2] for p in pieces), default=0.0),
        "audit_pieces": audit_pieces(sc),
        "largest_extent_km": max(c["extent_km"] for c in chans.values()),
        "states_per_district": max(c["max_states"] for c in chans.values()),
        "worst_dev": max(devs), "mean_dev": sum(devs) / len(devs),
        "channels": chans, "review": None,
    }


def rank_key(s: dict) -> tuple:
    return (s["splits"], s["defects"], s["largest_extent_km"], s["states_per_district"], s["worst_dev"],
            s["mean_dev"])


def rank(scores: list) -> list:
    """Eligible runs in rank-key order, then the rest; sets `review` on the D2 runs among
    `scores` and clears it on every other run."""
    for s in scores:
        s["review"] = None
    ok = sorted((s for s in scores if s["eligible"]), key=rank_key)
    if ok:
        best = ok[0]["splits"]
        floor = min(s["defects"] for s in ok if s["splits"] == best)
        for s in ok:
            if s["splits"] == best + 1 and s["defects"] < floor:
                s["review"] = f"REVIEW: +1 split for -{floor - s['defects']} defects"
    return ok + sorted((s for s in scores if not s["eligible"]), key=rank_key)


def verdict(s: dict) -> str:
    head = "ELIGIBLE" if s["eligible"] else "INELIGIBLE (" + "; ".join(s["why"]) + ")"
    review = f" | {s['review']}" if s["review"] else ""
    return (f"{s['run']}: {head}{review} | {s['splits']} splits ({len(s['distinct'])} states) | "
            f"{s['defects']:g} defects (thin {s['thin_links']}, small {s['small_pieces']}, crowded "
            f"{s['crowded_states']}, pieces {s['contiguity_pieces']} weighing {s['contiguity_weight']:g}, "
            f"largest {s['largest_piece_tau']:.3g} τ; multipart pieces "
            f"{s['multipart_pieces']}, listed only) | extent {s['largest_extent_km']:,.0f} km, "
            f"{s['states_per_district']} states | worst {100 * s['worst_dev']:.1f}%, mean {100 * s['mean_dev']:.1f}%")


def report(s: dict) -> str:
    lines = [f"# {s['run']}", f"dir: {s['dir']}",
             f"eligible: {'yes' if s['eligible'] else 'no'}"] + [f"  - {w}" for w in s["why"]]
    lines.append(f"K: {' '.join(f'{ch} {k}' for ch, k in s['k'].items())} = {sum(s['k'].values())}")
    for ch, c in s["channels"].items():
        t = TARGET.get(ch)
        dol = f"${s['dollars'][ch] / 1e6:,.0f}M" + (f" ({100 * (s['dollars'][ch] / t - 1):+.1f}% of target)"
                                                    if t else " (no target)")
        worst = max(map(abs, c["deviation"].values()))
        lines.append(f"{ch}: K {c['k']}, {dol}, worst {100 * worst:.1f}%, splits {len(c['split'])} "
                     f"{' '.join(c['split'])}, thin {len(c['thin'])}, small {len(c['small'])}, "
                     f"crowded {len(c['crowded'])}, pieces {len(c['pieces'] or ())}, extent "
                     f"{c['extent_km']:,.0f} km, max states {c['max_states']}")
        lines += [f"    thin {d} {st} {km} km" for d, st, km in c["thin"]]
        lines += [f"    small {d} {st} {f:.3f} tau" for d, st, f in c["small"]]
        lines += [f"    crowded {st}" for st in c["crowded"]]
        largest = {}
        for d, n, f, st in c["pieces"] or ():
            largest.setdefault(d, (d, n, f, st))
        lines += [f"    largest detached piece {d}: {n} ZIPs in {st}, {f:.3f} tau"
                  for d, n, f, st in sorted(largest.values(), key=lambda p: (-p[2], p[0]))]
        lines += [f"    multipart piece {d}: part of {zs}, {km2:,.3f} km2 (visual defect, not M1)"
                  for d, zs, km2 in c["multipart"] or ()]
    gate = s.get("dollar_gate")
    if gate is not None:
        lines.append(f"$ gate: {len(gate)} districts, {sum(not r['ok'] for r in gate)} outside their window, "
                     f"{sum(r['allowance'] for r in gate)} on the whole-state allowance")
        lines += [f"    {gate_reason(r)}" for r in gate if not r["ok"]]
        lines += [f"    {r['district']} {r['usd'] / 1e6:,.1f}M on the whole-state allowance "
                  f"({'+'.join(r['states'])}, up to {r['cap'] / 1e6:,.1f}M)" for r in gate if r["allowance"]]
        lines += [f"    {r['district']} {r['usd'] / 1e6:,.1f}M is the waiver district "
                  f"({'+'.join(r['states'])})" for r in gate if r["waiver"]]
    lines += [f"channel-state splits: {s['splits']}: {' '.join(s['split_list'])}",
              f"distinct split states: {len(s['distinct'])}: {' '.join(s['distinct'])}",
              f"defects: {s['defects']:g} = thin {s['thin_links']} + small {s['small_pieces']} + crowded "
              f"{s['crowded_states']} + pieces {s['contiguity_weight']:g} ({s['contiguity_pieces']} pieces "
              f"weighing 1 + mass/tau each, on the ledger; M1's piece count {s['audit_pieces']})",
              f"multipart pieces: {s['multipart_pieces']} (listed, not in the defects sum)",
              f"M1: {s['m1']['status']}: {s['m1']['summary']} (strict, on the ledger, necks "
              f"{'across coverage gaps' if s['m1'].get('gap_width') else 'on polygon borders'})"]
    lines += [f"    {n}" for n in s["necks"] + s["mass_necks"]]
    lines += [f"shape: extent {s['largest_extent_km']:,.1f} km, {s['states_per_district']} states per district",
              f"balance: worst {100 * s['worst_dev']:.2f}%, mean {100 * s['mean_dev']:.2f}%",
              f"review: {s['review'] or 'none'} (rule: among eligible runs scored together, one split "
              f"more than the fewest and fewer defects than every run at the fewest)",
              f"verdict: {verdict(s)}"]
    return "\n".join(lines)


def main(argv=None) -> list:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--extract", help="the extract (default: run.json's source under $TD_REPO)")
    ap.add_argument("--dollars-csv", action="store_true",
                    help="write each run's dollar gate (main map or IFA) to its dollars.csv")
    ap.add_argument("--m1-json", action="store_true",
                    help="write each run's M1, strict and across coverage gaps, to its m1.json")
    a = ap.parse_args(argv)
    rates = rates_of(a.extract) if a.extract else None
    scores = rank([score(d, rates=rates) for d in a.run_dirs])
    if a.dollars_csv:
        for s in scores:
            if s["dollar_gate"] is not None:
                write_dollars(os.path.join(s["dir"], "dollars.csv"), s["dollar_gate"])
    if a.m1_json:
        for s in scores:
            with open(os.path.join(s["dir"], "ledger.csv"), newline="") as fh:
                ledger = list(csv.DictReader(fh))
            write_m1(os.path.join(s["dir"], "m1.json"),
                     m1_both(ledger, s["k"], geography(), fine_channels(s["dir"])))
    for s in scores:
        print(report(s), end="\n\n")
    if len(scores) > 1:
        print("# ranking")
        for i, s in enumerate(scores, 1):
            print(f"{i}. {verdict(s)}")
    return scores


if __name__ == "__main__":
    main()
