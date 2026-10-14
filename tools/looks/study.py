"""study.py -- the looks-and-effort study: per-district "looks" and "effort" measures on drawn maps.

    "$TD_PY" tools/looks/study.py [--out DIR] [--only SUBSTRING]

Measurement only, no solver.  For each map (the Census divisions and regions as whole-state
"districts", the main-map overnight grid's finals, the regional merge, the IFA CONUS maps) and each
planning channel, one row per district goes to `<out>/districts.csv`, one row per map to
`maps.csv`, with `SUMMARY.md` and the figures beside them.  Measures (all on ZCTA data, in the
2025 reference's equal-area EPSG:5070 metres, so km and km² need no further projection):

- L3a `hull_fill`: the district's land (the gazetteer's, km²) over the area of the convex hull of
  its ZIP centroids, capped at 1 (`hull_fill_raw` is uncapped: a centroid hull can be smaller than
  the land of a district of a few large ZCTAs).
- L3b `bite`: the land of other districts' ZIPs of the same channel whose centroid lies in the
  hull, over the hull area; `bite_states` names the states of the largest intruders.
- L4 `longest_axis_km` (`score.extent_km` over the ZIP centroids) and `aspect` = axis / (land /
  axis).
- L2 cut proxy: in every state the district shares with another district of its channel,
  `cut_edges` counts the polygon-graph edges between the two inside the state, `cut_counties`
  the counties holding ZIPs of both; `cut_detail` lists them per state.
- effort: `land_km2`, `land_per_usd` (km² per $M), `wmean_dist_km` (m_rel-weighted mean distance
  to the m_rel-weighted centroid) and `r90_km` (radius around it holding 90% of m_rel).
- doughnuts, per CBSA of at least `MIN_CBSA_TAU` of the channel's mean district mass:
  `core_without_ring` when the district holds >= 50% of the CBSA's m_rel and < 30% of its land,
  `ring_without_core` the reverse; the CBSA names are listed.  A CBSA cut among many districts has
  no 50% holder, so a soft test (`doughnut_soft`) flags a district holding >= 15% of a CBSA's
  m_rel at >= 4 times its land share (`core_dense`) or >= 15% of its land at >= 4 times its m_rel
  share (`ring_sparse`).
- `hub`: the CBSA giving the district most m_rel, and its share of the district's.

A ledger carries one row per (ZIP, fine channel); a district's m_rel and $ are summed over them,
the land once per (ZIP, planning channel).  $ is m_rel times the fine channel's `fac_usd.json`
rate when the grid has one (1.0 on the dollar extract: m_rel is already $M).
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import math
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import geo                                             # noqa: E402

HUB = os.environ.get("TD_REPO", ROOT)
OUT_DEFAULT = os.path.join(HUB, "runs", "exp", "looks_study_2026-10-13")
GRID = os.path.join(HUB, "runs", "exp", "main_overnight_2026-10-13")
CORE_SHARE, RING_LAND = 0.5, 0.3     # a district's hold of a CBSA: >= 50% of one, < 30% of the other
SOFT_SHARE, SOFT_RATIO = 0.15, 4.0   # the soft test: >= 15% of one and SOFT_RATIO times its share of the other
MIN_CBSA_TAU = 0.05                  # a CBSA counts when its m_rel is this share of the channel's mean district's
MAIN_CHANNELS = ("FI", "WH", "WIFI", "national")

_spec = importlib.util.spec_from_file_location(
    "looks_score", os.path.join(os.path.dirname(os.path.abspath(__file__)), "score.py"))
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)

DIVISIONS = {       # CONUS only, DC with South Atlantic
    "New England": "CT ME MA NH RI VT",
    "Middle Atlantic": "NJ NY PA",
    "East North Central": "IL IN MI OH WI",
    "West North Central": "IA KS MN MO NE ND SD",
    "South Atlantic": "DE DC FL GA MD NC SC VA WV",
    "East South Central": "AL KY MS TN",
    "West South Central": "AR LA OK TX",
    "Mountain": "AZ CO ID MT NV NM UT WY",
    "Pacific": "CA OR WA",
}
REGIONS = {
    "Northeast": ("New England", "Middle Atlantic"),
    "Midwest": ("East North Central", "West North Central"),
    "South": ("South Atlantic", "East South Central", "West South Central"),
    "West": ("Mountain", "Pacific"),
}
DIVISION_OF = {s: d for d, ss in DIVISIONS.items() for s in ss.split()}
REGION_OF = {s: r for r, ds in REGIONS.items() for d in ds for s in DIVISIONS[d].split()}

DISTRICT_COLUMNS = [
    "map", "channel", "district", "states", "n_states", "usd_m", "m_rel", "n_zips", "land_km2",
    "hull_km2", "hull_fill", "hull_fill_raw", "bite", "bite_states", "longest_axis_km", "aspect",
    "cut_edges", "cut_counties", "cut_detail", "land_per_usd", "wmean_dist_km", "r90_km",
    "core_without_ring", "ring_without_core", "doughnut", "core_dense", "ring_sparse",
    "doughnut_soft", "hub", "hub_share"]


class Ref:
    """The ZIP reference: `zips`, `idx` {zip: row}, `x`, `y` (km), `land` (km²), `ea`, `eb` (edge
    ends as rows) and `cbsa_name` {cbsa id: name}."""

    def __init__(self, zips, x, y, land, edges, cbsa_name=None):
        self.zips = list(zips)
        self.idx = {z: i for i, z in enumerate(self.zips)}
        self.x, self.y, self.land = (np.asarray(v, dtype=float) for v in (x, y, land))
        pairs = [(self.idx[a], self.idx[b]) for a, b, *_ in edges if a in self.idx and b in self.idx]
        self.ea = np.array([p[0] for p in pairs], dtype=int)
        self.eb = np.array([p[1] for p in pairs], dtype=int)
        self.cbsa_name = cbsa_name or {}

    @classmethod
    def load(cls, ref_dir: str = geo.REFERENCE_DIR) -> "Ref":
        ref = geo.read_reference(ref_dir)
        ref = ref[ref["graph_vertex"] == "1"]
        graph = geo.polygon_graph(ref_dir)
        names = geo.read_reference(ref_dir, "areas.csv.gz")
        cbsa = names[names["layer"] == "cbsa"]
        return cls(ref["zcta"], [float(v) / 1000.0 for v in ref["x"]],
                   [float(v) / 1000.0 for v in ref["y"]],
                   [graph["aland"][z] / 1e6 for z in ref["zcta"]], graph["edges"],
                   dict(zip(cbsa["geoid"], cbsa["name"])))


def _hull(pts: np.ndarray):
    """(area km², facet equations or None) of the convex hull of `pts`; 0 and None when it has none."""
    pts = np.unique(pts, axis=0)
    if len(pts) < 3:
        return 0.0, None
    from scipy.spatial import ConvexHull, QhullError
    try:
        h = ConvexHull(pts)
    except QhullError:
        return 0.0, None
    return float(h.volume), h.equations


def _wquantile(dist: np.ndarray, w: np.ndarray, q: float) -> float:
    """The smallest distance by which the weights up to it reach `q` of their total."""
    order = np.argsort(dist, kind="stable")
    cum = np.cumsum(w[order])
    return float(dist[order][min(int(np.searchsorted(cum, q * cum[-1] - 1e-12)), len(cum) - 1)])


def channel_cells(rows: list, fac: dict | None = None) -> tuple:
    """({channel: {zip: cell}}, n): `cell` = {d, s, county, cbsa, m, usd} summed over the fine channels
    of a ledger's rows; n counts the extra rows naming a second district for a (channel, zip) cell."""
    fac = fac or {}
    cells = collections.defaultdict(dict)
    conflicts = 0
    for r in rows:
        d = r["district"]
        if not d:
            continue
        m = float(r["m_rel"] or 0.0)
        c = cells[r["model_channel"]].get(r["zip_code"])
        if c is None:
            c = cells[r["model_channel"]][r["zip_code"]] = {
                "d": d, "s": r["state"], "county": r.get("county", ""), "cbsa": r.get("cbsa", ""),
                "m": 0.0, "usd": 0.0}
        elif c["d"] != d:
            conflicts += 1
            continue
        c["m"] += m
        c["usd"] += m * fac.get(r.get("current_channel", ""), 1.0)
    return dict(cells), conflicts


def measure_channel(map_name: str, ch: str, cells: dict, ref: Ref, min_tau: float = MIN_CBSA_TAU) -> list:
    """One `DISTRICT_COLUMNS` row per district of channel `ch`; `cells` is {zip: cell}."""
    zs = [z for z in cells if z in ref.idx]
    ii = np.array([ref.idx[z] for z in zs], dtype=int)
    x, y, land = ref.x[ii], ref.y[ii], ref.land[ii]
    cs = [cells[z] for z in zs]
    names = sorted({c["d"] for c in cs})
    k_of = {d: k for k, d in enumerate(names)}
    di = np.array([k_of[c["d"]] for c in cs], dtype=int)
    m = np.array([c["m"] for c in cs])
    usd = np.array([c["usd"] for c in cs])
    st = [c["s"] for c in cs]
    pts = np.c_[x, y]
    tau = m.sum() / len(names)

    loc = -np.ones(len(ref.zips), dtype=int)           # cut proxy inputs
    loc[ii] = np.arange(len(ii))
    la, lb = loc[ref.ea], loc[ref.eb]
    ok = (la >= 0) & (lb >= 0)
    cut_edge = collections.defaultdict(collections.Counter)      # district -> state -> edges
    for a, b in zip(la[ok], lb[ok]):
        if st[a] == st[b] and di[a] != di[b]:
            cut_edge[names[di[a]]][st[a]] += 1
            cut_edge[names[di[b]]][st[a]] += 1
    county_ds = collections.defaultdict(set)
    for c in cs:
        if c["county"]:
            county_ds[c["s"], c["county"]].add(c["d"])
    cut_county = collections.defaultdict(collections.Counter)
    for (s, _), ds in county_ds.items():
        if len(ds) > 1:
            for d in ds:
                cut_county[d][s] += 1

    cb_m, cb_land = collections.Counter(), collections.Counter()     # CBSA aggregates
    cb_dm, cb_dland = collections.Counter(), collections.Counter()
    for c, a in zip(cs, land):
        if c["cbsa"]:
            cb_m[c["cbsa"]] += c["m"]
            cb_land[c["cbsa"]] += a
            cb_dm[c["d"], c["cbsa"]] += c["m"]
            cb_dland[c["d"], c["cbsa"]] += a
    label = lambda b: ref.cbsa_name.get(b, b)                         # noqa: E731
    core, ring, hub_of = collections.defaultdict(list), collections.defaultdict(list), {}
    dense, sparse = collections.defaultdict(list), collections.defaultdict(list)
    for (d, b), mm in cb_dm.items():
        if cb_m[b] >= min_tau * tau and cb_m[b] > 0 and cb_land[b] > 0:
            sm, sl = mm / cb_m[b], cb_dland[d, b] / cb_land[b]
            if sm >= CORE_SHARE and sl < RING_LAND:
                core[d].append(f"{label(b)} (m {sm:.0%}, land {sl:.0%})")
            if sl >= CORE_SHARE and sm < RING_LAND:
                ring[d].append(f"{label(b)} (land {sl:.0%}, m {sm:.0%})")
            if sm >= SOFT_SHARE and sm >= SOFT_RATIO * sl:
                dense[d].append(f"{label(b)} (m {sm:.0%}, land {sl:.0%})")
            if sl >= SOFT_SHARE and sl >= SOFT_RATIO * sm:
                sparse[d].append(f"{label(b)} (land {sl:.0%}, m {sm:.0%})")
        if mm > hub_of.get(d, ("", -1.0))[1]:
            hub_of[d] = (b, mm)

    out = []
    for k, d in enumerate(names):
        sel = np.where(di == k)[0]
        area, eq = _hull(pts[sel])
        dland = float(land[sel].sum())
        raw = dland / area if area > 0 else 1.0
        bite, bite_states = 0.0, ""
        if eq is not None:
            inside = ((pts @ eq[:, :2].T + eq[:, 2]) <= 1e-6).all(axis=1) & (di != k)
            bite = float(land[inside].sum()) / area
            by = collections.Counter()
            for j in np.where(inside)[0]:
                by[st[j]] += land[j]
            bite_states = " ".join(f"{s}:{a / area:.3f}" for s, a in by.most_common(3))
        axis = score.extent_km([tuple(p) for p in pts[sel]])
        dm, du = float(m[sel].sum()), float(usd[sel].sum())
        if dm > 0:
            cx, cy = (m[sel] * x[sel]).sum() / dm, (m[sel] * y[sel]).sum() / dm
            dist = np.hypot(x[sel] - cx, y[sel] - cy)
            wmean, r90 = float((m[sel] * dist).sum() / dm), _wquantile(dist, m[sel], 0.9)
        else:
            wmean = r90 = float("nan")
        states = sorted({st[j] for j in sel})
        split = sorted(set(cut_edge[d]) | set(cut_county[d]))
        hub, hub_m = hub_of.get(d, ("", 0.0))
        out.append({
            "map": map_name, "channel": ch, "district": d, "states": ";".join(states),
            "n_states": len(states), "usd_m": round(du, 3), "m_rel": round(dm, 4),
            "n_zips": len(sel), "land_km2": round(dland, 1), "hull_km2": round(area, 1),
            "hull_fill": round(min(1.0, raw), 4), "hull_fill_raw": round(raw, 4),
            "bite": round(bite, 4), "bite_states": bite_states, "longest_axis_km": round(axis, 1),
            "aspect": round(axis * axis / dland, 3) if dland > 0 else float("nan"),
            "cut_edges": sum(cut_edge[d].values()), "cut_counties": sum(cut_county[d].values()),
            "cut_detail": " ".join(f"{s}:e{cut_edge[d][s]}/c{cut_county[d][s]}" for s in split),
            "land_per_usd": round(dland / du, 3) if du > 0 else float("nan"),
            "wmean_dist_km": round(wmean, 1), "r90_km": round(r90, 1),
            "core_without_ring": "; ".join(core[d]), "ring_without_core": "; ".join(ring[d]),
            "doughnut": int(bool(core[d] or ring[d])), "core_dense": "; ".join(dense[d]),
            "ring_sparse": "; ".join(sparse[d]),
            "doughnut_soft": int(bool(core[d] or ring[d] or dense[d] or sparse[d])), "hub": label(hub) if hub else "",
            "hub_share": round(hub_m / dm, 3) if dm > 0 else float("nan")})
    return out


def measure_map(map_name: str, rows: list, ref: Ref, fac: dict | None = None) -> tuple:
    """(district rows, number of cells naming two districts) of a ledger, every channel."""
    cells, conflicts = channel_cells(rows, fac)
    out = []
    for ch in sorted(cells):
        out += measure_channel(map_name, ch, cells[ch], ref)
    return out, conflicts


def census_rows(rows: list, level: str) -> list:
    """`rows` with each district replaced by the state's Census division or region; a state
    outside CONUS has no row."""
    of = DIVISION_OF if level == "division" else REGION_OF
    return [dict(r, district=f"{r['model_channel']}:{of[r['state']]}") for r in rows if r["state"] in of]


def score_fields(path: str) -> dict:
    """M1, pieces, necks and splits from a run's score.txt, blank when there is none."""
    out = {"eligible": "", "m1": "", "pieces": "", "necks": "", "splits": ""}
    if not os.path.exists(path):
        return out
    text = open(path, encoding="utf-8").read()
    if m := re.search(r"^eligible: (\S+)", text, re.M):
        out["eligible"] = m.group(1)
    if m := re.search(r"^M1: (\w+)", text, re.M):
        out["m1"] = m.group(1)
    if m := re.search(r"^M1: .*?(\d+) districts in pieces", text, re.M):
        out["pieces"] = int(m.group(1))
    if m := re.search(r"^M1: .*?(\d+) necks", text, re.M):
        out["necks"] = int(m.group(1))
    if m := re.search(r"^channel-state splits: (\d+)", text, re.M):
        out["splits"] = int(m.group(1))
    else:
        found = re.findall(r"^\w+: K \d+, .*?splits (\d+)", text, re.M)
        out["splits"] = sum(map(int, found)) if found else ""
    return out


def aggregate(map_name: str, group: str, drows: list, extra: dict) -> dict:
    """The maps.csv row of a map's district rows."""
    def col(name, rows=drows):
        return [r[name] for r in rows if not (isinstance(r[name], float) and math.isnan(r[name]))]
    ratios = {}
    for ch in sorted({r["channel"] for r in drows}):
        v = [r["land_per_usd"] for r in drows if r["channel"] == ch and r["land_per_usd"] == r["land_per_usd"]
             and r["land_per_usd"] > 0]
        if v:
            ratios[ch] = max(v) / min(v)
    worst = max(ratios, key=ratios.get) if ratios else ""
    fills = col("hull_fill")
    return {"map": map_name, "group": group, "districts": len(drows),
            "hull_fill_min": round(min(fills), 4), "hull_fill_mean": round(sum(fills) / len(fills), 4),
            "hull_fill_max": round(max(fills), 4), "bite_max": round(max(col("bite")), 4),
            "bite_mean": round(sum(col("bite")) / len(drows), 4),
            "axis_max_km": max(col("longest_axis_km")), "doughnuts": sum(r["doughnut"] for r in drows),
            "doughnuts_soft": sum(r["doughnut_soft"] for r in drows),
            "land_per_usd_ratio_worst": round(ratios[worst], 2) if worst else "",
            "land_per_usd_ratio_channel": worst, "r90_max_km": max(col("r90_km")), **extra}


def discover(hub: str = HUB) -> list:
    """[(name, group, run dir)] of the real maps: the grid's finals, the regional merge and the IFA CONUS maps."""
    out = []
    grid = os.path.join(hub, "runs", "exp", "main_overnight_2026-10-13")
    points = json.load(open(os.path.join(grid, "GRID.json")))["points"]
    for pid, p in sorted(points.items()):
        final = p.get("final")
        if final and os.path.exists(os.path.join(grid, final, "ledger.csv")):
            out.append((f"main/{final}", "main", os.path.join(grid, final)))
    exp = os.path.join(hub, "runs", "exp")
    out.append(("regional/merged", "regional", os.path.join(exp, "regional_2026-10-13", "merged")))
    contig = os.path.join(exp, "contig")
    # no folder carries "ifa_kgrid": the CONUS maps, then two full 49-district maps of the arm1 line
    for name, rel in (("ifa_conus_v2", "ifa/conus/ifa_conus_v2"), ("ifa_conus_v1", "ifa/conus/ifa_conus_v1"),
                      ("ifa_conus_nony", "ifa/conus/ifa_conus_nony"),
                      ("ifa49-arm1-seq-repair-fast", "ifa49-arm1-seq-repair-fast"),
                      ("ifa49-arm1-seq", "ifa49-arm1-seq")):
        if os.path.exists(os.path.join(contig, rel, "ledger.csv")):
            out.append((f"ifa/{name}", "ifa", os.path.join(contig, rel)))
    return out


def read_ledger(run_dir: str) -> list:
    with open(os.path.join(run_dir, "ledger.csv"), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def rank_key(r: dict) -> tuple:
    """Fewest doughnuts, then smallest worst bite, then largest worst hull fill."""
    return (r["doughnuts"], r["bite_max"], -r["hull_fill_min"])


def write_csv(path: str, cols: list, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def figures(out: str, drows: list, mrows: list) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    paths = []
    ref_div = [r for r in drows if r["map"] == "census/divisions"]
    ref_reg = [r for r in drows if r["map"] == "census/regions"]
    real = [r for r in drows if not r["map"].startswith("census/")]

    fig, ax = plt.subplots(figsize=(8, 6))
    for grp, color in (("main", "tab:blue"), ("regional", "tab:green"), ("ifa", "tab:orange")):
        sub = [r for r in real if r["map"].split("/")[0] == grp]
        ax.scatter([r["hull_fill"] for r in sub], [r["bite"] for r in sub], s=10, alpha=0.4, c=color, label=grp)
    for rows, color, label in ((ref_reg, "tab:purple", "Census regions"), (ref_div, "tab:red", "Census divisions")):
        ax.scatter([r["hull_fill"] for r in rows], [r["bite"] for r in rows], s=60, c=color, marker="D",
                   edgecolor="k", label=label)
    for r in ref_div:
        ax.annotate(r["district"].split(":")[-1], (r["hull_fill"], r["bite"]), fontsize=6, xytext=(3, 3),
                    textcoords="offset points")
    ax.set_xlabel("hull_fill (district land / convex hull of ZIP centroids)")
    ax.set_ylabel("bite (other districts' land inside the hull / hull)")
    ax.set_title("Looks: hull fill vs bite, one point per district")
    ax.legend(fontsize=8)
    paths.append(os.path.join(out, "fig_hull_vs_bite.png"))
    fig.savefig(paths[-1], dpi=150, bbox_inches="tight")
    plt.close(fig)

    ms = sorted(mrows, key=lambda r: (r["group"] != "reference", rank_key(r)))
    fig, ax = plt.subplots(figsize=(8, 0.28 * len(ms) + 1.5))
    colors = {"reference": "tab:red", "main": "tab:blue", "regional": "tab:green", "ifa": "tab:orange"}
    ax.barh([r["map"] for r in ms][::-1], [r["doughnuts"] for r in ms][::-1],
            color=[colors[r["group"]] for r in ms][::-1])
    ax.set_xlabel("districts failing the doughnut test (all channels)")
    ax.set_title("Doughnut districts per map")
    ax.tick_params(axis="y", labelsize=7)
    paths.append(os.path.join(out, "fig_doughnuts.png"))
    fig.savefig(paths[-1], dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axs = plt.subplots(1, 3, figsize=(14, 0.28 * len(ms) + 1.5), sharey=True)
    ys = [r["map"] for r in ms][::-1]
    for ax, key, title in ((axs[0], "bite_max", "max bite"), (axs[1], "hull_fill_min", "min hull_fill"),
                           (axs[2], "r90_max_km", "worst r90 (km)")):
        ax.barh(ys, [r[key] for r in ms][::-1], color=[colors[r["group"]] for r in ms][::-1])
        ax.set_title(title)
        ax.tick_params(axis="y", labelsize=7)
    paths.append(os.path.join(out, "fig_map_extremes.png"))
    fig.savefig(paths[-1], dpi=150, bbox_inches="tight")
    plt.close(fig)
    return paths


def summary_md(mrows: list, drows: list, notes: list) -> str:
    ms = sorted(mrows, key=lambda r: (r["group"] != "reference", rank_key(r)))
    lines = ["# Looks study (2026-10-13)", "",
             "Measurement only, no solver.  Maps ranked by (doughnut districts, max bite, min hull_fill): "
             "fewer doughnuts first, then the smaller worst bite, then the larger worst hull fill. "
             "The Census reference maps come first.  Columns are defined in `tools/looks/study.py`.", "",
             "| # | map | districts | doughnuts (soft) | bite max | hull_fill min | hull_fill mean | axis max km "
             "| land/$ ratio (ch) | r90 max km | M1 | pieces | necks | splits |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    n = 0
    for r in ms:
        n += r["group"] != "reference"
        rk = "ref" if r["group"] == "reference" else str(n)
        lines.append(f"| {rk} | {r['map']} | {r['districts']} | {r['doughnuts']} ({r['doughnuts_soft']}) | {r['bite_max']:.3f} | "
                     f"{r['hull_fill_min']:.3f} | {r['hull_fill_mean']:.3f} | {r['axis_max_km']:.0f} | "
                     f"{r['land_per_usd_ratio_worst']} ({r['land_per_usd_ratio_channel']}) | {r['r90_max_km']:.0f} | "
                     f"{r['m1']} | {r['pieces']} | {r['necks']} | {r['splits']} |")
    lines += ["", "## Worst districts by bite (real maps)", "",
              "| map | channel | district | states | bite | bite states | hull_fill |", "|---|---|---|---|---|---|---|"]
    real = [r for r in drows if not r["map"].startswith("census/")]
    for r in sorted(real, key=lambda r: -r["bite"])[:12]:
        lines.append(f"| {r['map']} | {r['channel']} | {r['district']} | {r['states']} | {r['bite']:.3f} | "
                     f"{r['bite_states']} | {r['hull_fill']:.3f} |")
    lines += ["", "## Doughnut districts (real maps, first 25)", "",
              "| map | district | core without ring | ring without core |", "|---|---|---|---|"]
    for r in [r for r in real if r["doughnut"]][:25]:
        lines.append(f"| {r['map']} | {r['district']} | {r['core_without_ring']} | {r['ring_without_core']} |")
    lines += ["", "## Soft doughnut districts missing the hard test (real maps, first 25)", "",
              "| map | district | core dense | ring sparse |", "|---|---|---|---|"]
    for r in [r for r in real if r["doughnut_soft"] and not r["doughnut"]][:25]:
        lines.append(f"| {r['map']} | {r['district']} | {r['core_dense']} | {r['ring_sparse']} |")
    if notes:
        lines += ["", "## Sanity checks and notes", ""] + [f"- {t}" for t in notes]
    return "\n".join(lines) + "\n"


def sanity(drows: list) -> list:
    """The three owner sanity checks as note lines."""
    notes = []
    div = [r for r in drows if r["map"] == "census/divisions" and r["channel"] == "national"]
    if div:
        notes.append("Census divisions: hull_fill " + ", ".join(
            f"{r['district'].split(':')[-1]} {r['hull_fill']:.2f}/bite {r['bite']:.3f}" for r in div))
    nat = [r for r in drows if r["map"].endswith("ne-52-filight-wide/r2") and r["district"] == "national_11"]
    for r in nat:
        notes.append(f"{r['map']} national_11 ({r['states']}): bite {r['bite']:.3f} ({r['bite_states']}), "
                     f"hull_fill {r['hull_fill']:.3f}")
    ny = [r for r in drows if r["map"].endswith("w1-50-wide/r2") and "NY" in r["states"].split(";")]
    for r in ny:
        notes.append(f"w1-50-wide/r2 {r['district']} ({r['states']}): doughnut {r['doughnut']}"
                     f", soft {r['doughnut_soft']}: dense [{r['core_dense']}] sparse [{r['ring_sparse']}]")
    return notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--only", default="", help="measure only maps whose name contains this")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    ref = Ref.load()
    fac = json.load(open(os.path.join(GRID, "fac_usd.json")))["fac"]
    maps = discover()
    drows, mrows = [], []

    def run(name, group, rows, extra):
        if args.only and args.only not in name:
            return
        d, conflicts = measure_map(name, rows, ref, fac)
        drows.extend(d)
        mrows.append(aggregate(name, group, d, dict(extra, conflicts=conflicts)))
        print(f"{name}: {len(d)} districts, {mrows[-1]['doughnuts']} doughnuts, bite max {mrows[-1]['bite_max']}",
              flush=True)

    blank = {"eligible": "", "m1": "", "pieces": "", "necks": "", "splits": ""}
    main_t = next(p for n, g, p in maps if n == "main/ne-52-filight-wide/r2")
    ifa_t = next(p for n, g, p in maps if n == "ifa/ifa_conus_v2")
    for label, path in (("main", main_t), ("ifa", ifa_t)):
        rows = read_ledger(path)
        for level, plural in (("division", "divisions"), ("region", "regions")):
            run(f"census/{plural}" if label == "main" else f"census/{plural}_ifa", "reference",
                census_rows(rows, level), blank)
    for name, group, path in maps:
        run(name, group, read_ledger(path), score_fields(os.path.join(path, "score.txt")))
    write_csv(os.path.join(args.out, "districts.csv"), DISTRICT_COLUMNS, drows)
    cols = list(mrows[0]) if mrows else []
    write_csv(os.path.join(args.out, "maps.csv"), cols, mrows)
    notes = sanity(drows) + [
        "no folder under runs/exp/contig carries `ifa_kgrid`; the IFA set is the three `ifa_conus_*` folders "
        "and two full 49-district `ifa49-arm1-seq*` maps.",
        "hull_fill is capped at 1; `hull_fill_raw` in districts.csv is not.",
        f"doughnut tests use CBSAs of at least {MIN_CBSA_TAU:.0%} of the channel's mean district m_rel."]
    with open(os.path.join(args.out, "SUMMARY.md"), "w", encoding="utf-8") as fh:
        fh.write(summary_md(mrows, drows, notes))
    for p in figures(args.out, drows, mrows):
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
