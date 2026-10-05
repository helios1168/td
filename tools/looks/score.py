"""score.py -- the looks scorer (td#93): eligibility and the four rank keys of drawn runs.

    "$TD_PY" tools/looks/score.py <run_dir> [<run_dir> ...] [--extract <instance.json.gz>]

`score(run_dir)` returns the dict without printing (the interface #92's tools load by path):
`eligible`, `splits`, `thin_links`, `small_pieces`, `crowded_states`, `contiguity_pieces`,
`defects` (their sum), `largest_extent_km`, `states_per_district`, `worst_dev`, `mean_dev`
(fractions), and details.  `rank(scores)` orders runs by the keys and sets `review`.

A run directory has the layout `python -m td run` writes: `ledger.csv`, `districts.csv`,
`run.json`, `scorecard.md`.  Every measure comes from the drawn ledger.  The split, small-piece,
crowded and thin-link rules are those of `runs/sweep/comb_2026-10-02/summarize5.py` (m5,
gitignored), with the display fill made deterministic.

A map is **eligible** when (PROBLEM.md row 2026-10-04, `runs/plan_2026-10-04/EXPERIMENTS.md` §1):
- the audit passes at a plain ±`BAND` band: no check of `scorecard.md` other than the band check
  fails, and `td.audit.check_bands` passes on the ledger with every channel's band τ_c(1 ± BAND),
  τ_c = the channel's ledger total / K_c;
- every channel with a `TARGET` averages a $ per district within ±`DOLLAR_BAND` of it.  $ is
  m_rel times the owner's dollar total over the extract's m_rel total, per fine channel
  (`DOLLARS`), summed over the channel's drawn cells; an IFA-only run uses the owner's
  whole-extract IFA total over K instead (owner, 2026-10-04).  A channel without a target, such
  as a combined channel (D11), is printed but not checked;
- the main map's total K is in `MAIN_K`; an IFA-only run is exempt.

Rank keys, compared in order, fewest or smallest first:
1. **splits**: channel-state splits, Σ_c the states where two or more of c's districts hold
   positive mass (PA split in WH and in FI counts 2); `distinct` is the set of split states;
2. **defects** = thin_links + small_pieces + crowded_states + contiguity_pieces, each printed:
   - thin: a district's piece in one state whose ZIP border with its pieces in its other states
     is under `THIN_KM`, measured on the display fill (every ZIP with no cell in the channel joins
     the nearest district of its state, by breadth-first search on the ZIP graph);
   - small: a district's piece of a split state under `SMALL_TAU` τ;
   - crowded: a split state with more than ceil(M_s / τ) + 1 districts;
   - pieces: components of each district's display-fill ZIPs on the ZIP graph beyond the first.
     The audit's own piece count (`audit_pieces`, from `scorecard.md`) is printed for reference;
     it counts the sparse channels' "connector ZIP not in ledger" pieces, which the fill joins;
3. **shape**: largest_extent_km (the longest distance between two ZIP points one district holds,
   km, as #81's `measure.extent_km`), then states_per_district, the most states one district
   holds positive mass in;
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

HUB = os.environ.get("TD_REPO", ROOT)
BAND = 0.15
DOLLAR_BAND = 0.10
MAIN_K = (48, 54)
THIN_KM = 25.0
SMALL_TAU = 0.20
TARGET = {"national": 1.25e9, "WH": 1.0e9, "FI": 0.9e9, "IFA": 1.25e9}          # $ per district
DOLLARS = {"wh": 11.36e9, "fi": 20.69e9, "wells_wh": 4.44e9, "wells_fi": 4.63e9,  # owner's totals,
           "national_chase": 8.55e9, "ifa": 62.14e9}                              # 2026-10-01
IFA_ONLY = {"IFA"}
BAND_CHECK = "final bands on drawn mass"


class Geography:
    """The 2025 reference: `state` {zip: state}, `xy` {zip: (x, y) km}, `edge` {zip: {zip: border
    km}} over the ZIP graph's edges."""

    def __init__(self, state: dict, xy: dict, edge: dict):
        self.state, self.xy, self.edge = state, xy, edge

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
        return cls(state, xy, edge)


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


def components(zips: set, edge: dict) -> int:
    """How many components the ZIP graph has on `zips`."""
    seen, n = set(), 0
    for z in sorted(zips):
        if z in seen:
            continue
        n += 1
        seen.add(z)
        stack = [z]
        while stack:
            for w in edge.get(stack.pop(), ()):
                if w in zips and w not in seen:
                    seen.add(w)
                    stack.append(w)
    return n


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
    owners = collections.defaultdict(set)
    for d, c in mass.items():
        for s, m in c.items():
            if m > 0:
                owners[s].add(d)
    split = sorted(s for s, ds in owners.items() if len(ds) > 1)
    small = sorted((d, s, round(mass[d][s] / tau, 3)) for s in split for d in owners[s]
                   if mass[d][s] / tau < SMALL_TAU)
    crowded = [s for s in split if len(owners[s]) > math.ceil(smass[s] / tau) + 1]
    own = {z: d for d, bys in held.items() for zs in bys.values() for z in sorted(zs)}
    filled = collections.defaultdict(lambda: collections.defaultdict(set))
    for z, d in display_fill(own, g).items():
        filled[d][g.state[z]].add(z)
    thin, pieces = [], 0
    for d in sorted(filled):
        bys = filled[d]
        pieces += components(set().union(*bys.values()), g.edge) - 1
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
            "crowded": crowded, "thin": thin, "pieces": pieces, "extent_km": extent,
            "max_states": max(len([s for s in c if c[s] > 0]) for c in mass.values())}


def dollar_rates(extract: data.Extract) -> dict:
    """{fine channel: $ per m_rel}: the owner's total over the extract's m_rel total."""
    total = collections.Counter()
    for c, m in zip(extract.channel, extract.m_rel):
        total[c] += m
    return {f: DOLLARS[f] / total[f] for f in DOLLARS if total[f] > 0}


def dollars_per_district(ch: str, k: int, ledger: list, rates: dict) -> float:
    fine = {r["current_channel"] for r in ledger if r["model_channel"] == ch and r["district"]}
    missing = sorted(fine - set(rates))
    if missing:
        raise ValueError(f"channel {ch}: no dollar total for fine channel(s) {', '.join(missing)}")
    return sum(float(r["m_rel"]) * rates[r["current_channel"]] for r in ledger
               if r["model_channel"] == ch and r["district"]) / k


def scorecard_checks(text: str) -> dict:
    """{check name: status} from the table of a `scorecard.md`."""
    out = {}
    for line in text.splitlines():
        m = re.fullmatch(r"\| (.+?) \| (pass|fail|listed|unverified) \| .* \|", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def audit_pieces(text: str) -> int | None:
    m = re.search(r"\| ZIP contiguity \| \w+ \| \d+ districts in pieces, (\d+) pieces", text)
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


def eligibility(checks: dict, bands: audit.Check, ks: dict, dollars: dict) -> list:
    """Why a run is not eligible, one reason per failed rule; empty when it is."""
    why = [f"audit: {name} fails" for name, s in checks.items() if s == "fail" and name != BAND_CHECK]
    if not checks:
        why.append("audit: no scorecard")
    if bands.status != "pass":
        why.append(f"audit at ±{100 * BAND:.0f}%: {bands.summary}")
    for ch, d in sorted(dollars.items()):
        t = TARGET.get(ch)
        if t is not None and abs(d / t - 1) > DOLLAR_BAND:
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
    if set(ks) == IFA_ONLY:              # owner, 2026-10-04: the whole-extract IFA total over K
        dollars = {ch: DOLLARS["ifa"] / k for ch, k in ks.items()}
    else:
        rates = rates if rates is not None else rates_of(extract_path(run_dir))
        dollars = {ch: dollars_per_district(ch, k, ledger, rates) for ch, k in ks.items()}
    bands = bands_at(ledger, ks, BAND)
    why = eligibility(scorecard_checks(sc), bands, ks, dollars)
    devs = [abs(x) for c in chans.values() for x in c["deviation"].values()]
    defects = {"thin_links": sum(len(c["thin"]) for c in chans.values()),
               "small_pieces": sum(len(c["small"]) for c in chans.values()),
               "crowded_states": sum(len(c["crowded"]) for c in chans.values()),
               "contiguity_pieces": sum(c["pieces"] for c in chans.values())}
    return {
        "run": os.path.basename(os.path.normpath(run_dir)), "dir": run_dir,
        "eligible": not why, "why": why, "k": ks, "dollars": dollars,
        "splits": sum(len(c["split"]) for c in chans.values()),
        "split_list": [f"{ch}:{s}" for ch, c in chans.items() for s in c["split"]],
        "distinct": sorted({s for c in chans.values() for s in c["split"]}),
        "defects": sum(defects.values()), **defects, "audit_pieces": audit_pieces(sc),
        "largest_extent_km": max(c["extent_km"] for c in chans.values()),
        "states_per_district": max(c["max_states"] for c in chans.values()),
        "worst_dev": max(devs), "mean_dev": sum(devs) / len(devs),
        "channels": chans, "review": None,
    }


def rank_key(s: dict) -> tuple:
    return (s["splits"], s["defects"], s["largest_extent_km"], s["states_per_district"], s["worst_dev"],
            s["mean_dev"])


def rank(scores: list) -> list:
    """Eligible runs in rank-key order, then the rest; sets `review` on the D2 runs."""
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
            f"{s['defects']} defects (thin {s['thin_links']}, small {s['small_pieces']}, crowded "
            f"{s['crowded_states']}, pieces {s['contiguity_pieces']}) | extent {s['largest_extent_km']:,.0f} km, "
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
                     f"crowded {len(c['crowded'])}, pieces {c['pieces']}, extent {c['extent_km']:,.0f} km, "
                     f"max states {c['max_states']}")
        lines += [f"    thin {d} {st} {km} km" for d, st, km in c["thin"]]
        lines += [f"    small {d} {st} {f:.3f} tau" for d, st, f in c["small"]]
        lines += [f"    crowded {st}" for st in c["crowded"]]
    lines += [f"channel-state splits: {s['splits']}: {' '.join(s['split_list'])}",
              f"distinct split states: {len(s['distinct'])}: {' '.join(s['distinct'])}",
              f"defects: {s['defects']} = thin {s['thin_links']} + small {s['small_pieces']} + crowded "
              f"{s['crowded_states']} + pieces {s['contiguity_pieces']} (audit's piece count {s['audit_pieces']})",
              f"shape: extent {s['largest_extent_km']:,.1f} km, {s['states_per_district']} states per district",
              f"balance: worst {100 * s['worst_dev']:.2f}%, mean {100 * s['mean_dev']:.2f}%",
              f"review: {s['review'] or 'none'} (rule: among eligible runs scored together, one split "
              f"more than the fewest and fewer defects than every run at the fewest)",
              f"verdict: {verdict(s)}"]
    return "\n".join(lines)


def main(argv=None) -> list:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--extract", help="the extract (default: run.json's source under $TD_REPO)")
    a = ap.parse_args(argv)
    rates = rates_of(a.extract) if a.extract else None
    scores = rank([score(d, rates=rates) for d in a.run_dirs])
    for s in scores:
        print(report(s), end="\n\n")
    if len(scores) > 1:
        print("# ranking")
        for i, s in enumerate(scores, 1):
            print(f"{i}. {verdict(s)}")
    return scores


if __name__ == "__main__":
    main()
