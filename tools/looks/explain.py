"""explain.py -- a plain-English PDF of the "nice shape" metrics, each with real drawn examples.

    "$TD_PY" tools/looks/explain.py [--out PDF] [--study DIR]

Reads the last looks study's `districts.csv` and `maps.csv` (`tools/looks/study.py`, default
`$TD_REPO/runs/exp/looks_study_2026-10-13/`), the ledgers of the maps it scored (`study.discover`),
and the pickled 2025 ZCTA polygons and state shapes of the ZIP pages (`tools/maps/zip_pages.CACHE`).
Writes `results/looks_explainer_2026-10-14/LOOKS_METRICS.pdf`, landscape, one metric family a page:

1. glossary: metric, meaning, formula, direction, Census-division range, real-map range;
2. `hull_fill`, 3. `bite`: six districts each (two Census divisions, two middling real ones, the two
   worst real ones), drawn with the land the metric counts shaded;
4-8. longest axis and aspect, effort (land per $M, mean distance, r90), the state-split cut proxy,
   the CBSA doughnuts (hard and soft), the hub;
9-10. the scorer's (`tools/looks/score.py`) channel-state splits, crowded states, small pieces, thin
   links, detached pieces and necks;
11. the provisional limits of 2026-10-14, as how many districts of each scored map fail each.

No metric is computed here.  Values come from `districts.csv`; the shading is re-derived from the
ledger with the study's own `_hull` and its inside-the-hull rule, and every drawn district is
checked against its `districts.csv` row (`Ctx.hull_view`, `Ctx.check`), a mismatch raising.
Nothing masked is read: no rep, firm or sales column of a ledger reaches a page.
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import math
import os
import pickle
import re
import statistics
import sys
import textwrap

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import matplotlib                                          # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
import shapely                                             # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages       # noqa: E402
from matplotlib.patches import Circle, PathPatch           # noqa: E402

from td.output import _polygon_path                        # noqa: E402

_spec = importlib.util.spec_from_file_location("looks_study", os.path.join(HERE, "study.py"))
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)
score = study.score

HUB = study.HUB
STUDY_DIR = study.OUT_DEFAULT
GEO_CACHE = os.path.join(HUB, "runs", "autonomous_2026-10-05", "batch", "geo")   # `zip_pages.CACHE`
SHORTLIST = os.path.join(ROOT, "tools", "shortlist", "shortlist.json")
OUT_DEFAULT = os.path.join(ROOT, "results", "looks_explainer_2026-10-14", "LOOKS_METRICS.pdf")
PAGE = (11.0, 8.5)
KM = 0.001
BLUE, RED, ORANGE, GREEN = "#2f6eab", "#c0392b", "#f0a63c", "#4c9a6a"
LAND, LINE = "#f2f1ec", "#9c9c9c"
TINTS = ["#f0b27a", "#82c0cc", "#b5d99c", "#d7a6d0", "#e8d27a", "#9fb4e0"]
# the limits proposed 2026-10-14, provisional and not decided: (column, test, label)
LIMITS = (("bite", lambda r: r["bite"] > 0.30, "bite > 0.30"),
          ("hull_fill", lambda r: r["hull_fill"] < 0.45, "hull_fill < 0.45"),
          ("n_states", lambda r: r["n_states"] > 4, "more than 4 states"),
          ("doughnut", lambda r: r["doughnut"] == 1, "hard doughnut"))
MIN_ZIPS = 5            # a district of fewer ZIPs is no example of an effort or hub measure
NUMERIC = ("n_states", "usd_m", "m_rel", "n_zips", "land_km2", "hull_km2", "hull_fill", "hull_fill_raw", "bite",
           "longest_axis_km", "aspect", "cut_edges", "cut_counties", "land_per_usd", "wmean_dist_km", "r90_km",
           "doughnut", "doughnut_soft", "hub_share")


def missing_inputs(study_dir: str = STUDY_DIR, geo_cache: str = GEO_CACHE) -> list:
    """The inputs the PDF needs that are not there (none for a full build)."""
    need = [os.path.join(study_dir, f) for f in ("districts.csv", "maps.csv")]
    need += [os.path.join(geo_cache, f) for f in ("zcta_polys.pkl", "states.pkl")]
    need += [os.path.join(HUB, "reference", "2025", "zcta_reference.csv.gz")] if not os.path.isdir(
        study.geo.REFERENCE_DIR) else []
    return [p for p in need if not os.path.exists(p)]


def read_rows(path: str, numeric=NUMERIC) -> list:
    """A study CSV as dicts, the `numeric` columns as floats (blank = nan) and the count columns whole."""
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for c in numeric:
            if c in r:
                r[c] = float(r[c]) if r[c] not in ("", None) else float("nan")
    return rows


def short(name: str) -> str:
    return name.replace("main/", "").replace("ifa/", "ifa ").replace("regional/", "regional ")


class Ctx:
    """What the pages draw from: study rows, the ZIP reference and polygons, and each map's cells.

    `cells_of` {map: {channel: {zip: cell}}} (`study.channel_cells`) may be given whole (tests) or
    left to `ledger_cells`, which reads the hub's ledgers; `polys` {zip: polygon in EPSG:5070 m},
    `states` {abbr: shape in m}; `runs` {map: run dir}; `shortlist` {run dir: id}."""

    def __init__(self, drows, mrows, ref, polys, states, cells_of=None, runs=None, shortlist=None):
        self.drows, self.mrows, self.ref, self.polys = drows, mrows, ref, polys
        self.states = {s: shapely.transform(g, lambda a: a * KM) for s, g in states.items()}
        self.cells_of = dict(cells_of or {})
        self.runs, self.shortlist = runs or {}, shortlist or {}
        self.real = [r for r in drows if not r["map"].startswith("census/")]
        self.census = [r for r in drows if r["map"] in ("census/divisions", "census/divisions_ifa")]
        self._views, self._unions, self._geo, self.score_counts = {}, {}, None, {}

    # ---- inputs
    @classmethod
    def load(cls, study_dir: str = STUDY_DIR, geo_cache: str = GEO_CACHE) -> "Ctx":
        miss = missing_inputs(study_dir, geo_cache)
        if miss:
            raise FileNotFoundError("explain.py inputs missing: " + ", ".join(miss))
        with open(os.path.join(geo_cache, "zcta_polys.pkl"), "rb") as fh:
            polys = pickle.load(fh)
        with open(os.path.join(geo_cache, "states.pkl"), "rb") as fh:
            states = pickle.load(fh)
        runs = {n: p for n, _, p in study.discover()}
        short_ids = {}
        if os.path.exists(SHORTLIST):
            with open(SHORTLIST, encoding="utf-8") as fh:
                for m in json.load(fh)["maps"]:
                    short_ids[os.path.normpath(os.path.join(HUB, m["run"]))] = m["id"]
        return cls(read_rows(os.path.join(study_dir, "districts.csv")),
                   read_rows(os.path.join(study_dir, "maps.csv"), ("districts", "necks", "pieces", "splits")),
                   study.Ref.load(), polys, states, runs=runs, shortlist=short_ids)

    def label(self, name: str) -> str:
        """A map's shortlist id when it has one, else its run name."""
        sid = self.shortlist.get(os.path.normpath(self.runs.get(name, "")))
        return sid or short(name)

    def run_rows(self, name: str) -> list:
        if name.startswith("census/"):
            base = "main/ne-52-filight-wide/r2" if name in ("census/divisions", "census/regions") \
                else "ifa/ifa_conus_v2"
            level = "division" if "divisions" in name else "region"
            return study.census_rows(study.read_ledger(self.runs[base]), level)
        return study.read_ledger(self.runs[name])

    def cells(self, name: str, ch: str) -> dict:
        if name not in self.cells_of:
            fac = {}
            if not name.startswith(("ifa/", "census/divisions_ifa", "census/regions_ifa")):
                fac = json.load(open(os.path.join(study.GRID, "fac_usd.json")))["fac"]
            self.cells_of[name] = study.channel_cells(self.run_rows(name), fac)[0]
        return self.cells_of[name][ch]

    def geography(self):
        if self._geo is None:
            self._geo = score.Geography.load()
        return self._geo

    # ---- geometry (km)
    def union(self, zs) -> "shapely.Geometry":
        key = tuple(sorted(zs))
        if key not in self._unions:
            g = shapely.transform(shapely.union_all([self.polys[z] for z in key if z in self.polys]), lambda a: a * KM)
            self._unions[key] = fill_holes(g)
        return self._unions[key]

    def hull_view(self, row: dict) -> dict:
        """The district `row`'s land, hull and bitten-in ZIPs, drawn from the ledger with the study's rules,
        checked against the row."""
        key = (row["map"], row["channel"], row["district"])
        if key in self._views:
            return self._views[key]
        cells = self.cells(row["map"], row["channel"])
        zs = [z for z in cells if z in self.ref.idx]
        ii = np.array([self.ref.idx[z] for z in zs], dtype=int)
        pts, land = np.c_[self.ref.x[ii], self.ref.y[ii]], self.ref.land[ii]
        mine = np.array([cells[z]["d"] == row["district"] for z in zs])
        area, eq = study._hull(pts[mine])
        hull, inside = None, np.zeros(len(zs), dtype=bool)
        if eq is not None:
            from scipy.spatial import ConvexHull
            u = np.unique(pts[mine], axis=0)
            hull = shapely.Polygon(u[ConvexHull(u).vertices])
            inside = ((pts @ eq[:, :2].T + eq[:, 2]) <= 1e-6).all(axis=1) & ~mine
        view = {"zips": [z for z, m in zip(zs, mine) if m], "pts": pts[mine], "hull": hull, "hull_km2": area,
                "land_km2": float(land[mine].sum()),
                "bite_zips": [z for z, i in zip(zs, inside) if i], "bite_km2": float(land[inside].sum())}
        view["land"] = self.union(view["zips"])
        view["bite_geom"] = self.union(view["bite_zips"]) if view["bite_zips"] else None
        self.check(row, view)
        self._views[key] = view
        return view

    @staticmethod
    def check(row: dict, view: dict) -> None:
        """The drawn district must reproduce its `districts.csv` row: land, hull, fill and bite."""
        raw = view["land_km2"] / view["hull_km2"] if view["hull_km2"] > 0 else 1.0
        bite = view["bite_km2"] / view["hull_km2"] if view["hull_km2"] > 0 else 0.0
        if (abs(min(1.0, raw) - row["hull_fill"]) > 6e-4 or abs(bite - row["bite"]) > 6e-4
                or abs(view["land_km2"] - row["land_km2"]) > 0.2):
            raise AssertionError(f"explain.py: {row['map']} {row['district']} redrawn as fill {raw:.4f}, bite "
                                 f"{bite:.4f}, land {view['land_km2']:.1f}; districts.csv says "
                                 f"{row['hull_fill']}, {row['bite']}, {row['land_km2']}")


# ------------------------------------------------------------------------------ drawing
HOLE_KM2 = 150.0        # drawn unions fill interior gaps (lakes, ZIP-less land) under this area


def fill_holes(g, limit: float = HOLE_KM2):
    """`g` (km) without interior rings under `limit` km²: a drawing aid, never used by a value."""
    parts = []
    for p in getattr(g, "geoms", [g]):
        if p.geom_type == "Polygon":
            keep = [r for r in p.interiors if shapely.Polygon(r).area >= limit]
            p = shapely.Polygon(p.exterior, keep)
        parts.append(p)
    return shapely.MultiPolygon(parts) if len(parts) > 1 else parts[0]


def draw_geom(ax, g, **kw) -> None:
    """Add `g` (km) as a patch, simplified to well under a pixel of the panel (`base` sets the tolerance)."""
    if g is not None and not g.is_empty:
        tol = getattr(ax, "simplify_km", 0.0)
        g = g.simplify(tol, preserve_topology=True) if tol else g
        if not g.is_empty:
            ax.add_patch(PathPatch(_polygon_path(g), **kw))


def box_of(*geoms, extra=()) -> tuple:
    xs, ys = [], []
    for g in geoms:
        if g is not None and not g.is_empty:
            b = g.bounds
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
    for x, y in extra:
        xs.append(x)
        ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def base(ax, box, ctx: Ctx, pad: float = 0.08) -> None:
    """Square view of `box` (km) over grey land with thin state lines, and a scale bar."""
    x0, y0, x1, y1 = box
    cx, cy, half = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0, 20.0) / 2 * (1 + 2 * pad)
    win = (cx - half, cy - half, cx + half, cy + half)
    ax.simplify_km = half * 2 / 500
    for g in ctx.states.values():
        if g.intersects(shapely.box(*win)):
            draw_geom(ax, shapely.clip_by_rect(g, *win), facecolor=LAND, edgecolor=LINE, lw=0.35, zorder=0)
    ax.set_xlim(win[0], win[2])
    ax.set_ylim(win[1], win[3])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#cccccc")
        sp.set_linewidth(0.6)
    bar = next(b for b in (10, 25, 50, 100, 200, 500, 1000, 2000) if b >= half * 2 * 0.18)
    bx, by = win[0] + half * 0.1, win[1] + half * 0.1
    ax.plot([bx, bx + bar], [by, by], color="k", lw=1.6, zorder=9, solid_capstyle="butt")
    ax.text(bx, by + half * 0.035, f"{bar:,} km", fontsize=6, zorder=9)


def title(ax, tag: str, ctx: Ctx, row: dict, color: str = "k") -> None:
    st = row["states"].replace(";", " ")
    st = st if row["n_states"] <= 7 else f"{int(row['n_states'])} states: " + st[:24] + "…"
    who = (f"{row['district'].split(':')[-1]} ({row['channel']} channel)" if row["map"].startswith("census/")
           else f"{ctx.label(row['map'])} · {row['district']} · ${row['usd_m']:,.0f}M")
    ax.set_title(f"{tag}\n{who}\n{st}",
                 fontsize=6.8, loc="left", color=color, linespacing=1.25)


def value(ax, text: str) -> None:
    ax.text(0.5, -0.025, text, transform=ax.transAxes, ha="center", va="top", fontsize=7.4, fontweight="bold",
            linespacing=1.3)


def page(title_text: str, lead: str, n_rows: int, n_cols: int, top: float = 0.775, bottom: float = 0.125):
    """(figure, axes list) with a heading and a plain-English lead paragraph."""
    fig = plt.figure(figsize=PAGE)
    fig.text(0.04, 0.955, title_text, fontsize=17, fontweight="bold", va="top")
    fig.text(0.04, 0.905, textwrap.fill(lead, 152), fontsize=9.2, va="top", linespacing=1.4, color="#222222")
    gs = fig.add_gridspec(n_rows, n_cols, left=0.04, right=0.97, top=top, bottom=bottom, hspace=0.55, wspace=0.12)
    return fig, [fig.add_subplot(gs[i, j]) for i in range(n_rows) for j in range(n_cols)]


def blank(axs, used: int) -> None:
    for ax in axs[used:]:
        ax.axis("off")


def distinct(rows, n: int) -> list:
    """The first `n` of `rows` with different state sets."""
    out, seen = [], set()
    for r in rows:
        if r["states"] not in seen:
            seen.add(r["states"])
            out.append(r)
        if len(out) == n:
            break
    return out


def census_pair(ctx: Ctx, key: str, best_first: bool) -> list:
    """The best and the worst Census division (national channel, else all) by `key`."""
    rows = [r for r in ctx.census if r["map"] == "census/divisions" and r["hull_km2"] > 0]
    rows = [r for r in rows if r["channel"] == "national"] or rows
    rows = sorted(rows, key=lambda r: r[key], reverse=not best_first)
    return [rows[0], rows[-1]] if len(rows) > 1 else rows


def middling(rows, key: str, n: int = 2) -> list:
    """`n` of `rows` nearest the median of `key`, from different maps when it can."""
    vals = [r[key] for r in rows]
    if not vals:
        return []
    med = statistics.median(vals)
    near = sorted(rows, key=lambda r: abs(r[key] - med))
    out, maps = [], set()
    for r in near:
        if r["map"] not in maps and all(r["states"] != o["states"] for o in out):
            out.append(r)
            maps.add(r["map"])
        if len(out) == n:
            return out
    return out + [r for r in near if r not in out][: n - len(out)]


# ------------------------------------------------------------------------------ hull_fill and bite
def hull_panel(ax, ctx: Ctx, row: dict, tag: str, mode: str) -> None:
    v = ctx.hull_view(row)
    base(ax, box_of(v["land"], v["hull"]), ctx)
    if v["hull"] is not None:
        if mode == "fill":
            draw_geom(ax, v["hull"], facecolor=ORANGE, alpha=0.55, edgecolor="none", zorder=2)
        else:
            draw_geom(ax, v["hull"], facecolor="#fbf3df", alpha=0.7, edgecolor="none", zorder=2)
    draw_geom(ax, v["land"], facecolor=BLUE, edgecolor="white", lw=0.15, zorder=3)
    if mode == "bite":
        draw_geom(ax, v["bite_geom"], facecolor=RED, edgecolor="white", lw=0.15, zorder=4)
    if v["hull"] is not None:
        x, y = v["hull"].exterior.xy
        ax.plot(x, y, color="#222222", lw=1.0, ls=(0, (4, 2)), zorder=5)
    title(ax, tag, ctx, row)
    if mode == "fill":
        value(ax, f"hull_fill {row['hull_fill']:.2f}\n{v['land_km2']:,.0f} km² land ÷ {v['hull_km2']:,.0f} km² hull")
    else:
        who = ", ".join(f"{p.split(':')[0]} {float(p.split(':')[1]):.2f}" for p in row["bite_states"].split())
        value(ax, f"bite {row['bite']:.2f}\n{v['bite_km2']:,.0f} km² of others' land ÷ {v['hull_km2']:,.0f} km² hull"
              + (f"\nmost of it in {who}" if who else ""))


def page_hull_fill(ctx: Ctx):
    fig, axs = page(
        "hull_fill: how much of the outline is the district's own",
        "Stretch a rubber band around the centres of a district's ZIPs: that is its convex hull (dashed). hull_fill is the "
        "share of the hull that is the district's own land (blue). The orange left over is room inside the outline that "
        "is not the district's: sea, another country, or another district's land. A round, solid district scores near "
        "1; a ragged, sprawling or wrapped-around district scores low. Higher is better.", 2, 3)
    rows = [r for r in ctx.real if r["hull_km2"] > 0]
    panels = ([(f"Census division, {w}", r) for r, w in zip(census_pair(ctx, "hull_fill", False), ("most solid", "least solid"))]
              + [("real district, middling", r) for r in middling(rows, "hull_fill")]
              + [("real district, worst", r) for r in distinct(sorted(rows, key=lambda r: r["hull_fill"]), 2)])
    for ax, (tag, r) in zip(axs, panels):
        hull_panel(ax, ctx, r, tag, "fill")
    blank(axs, len(panels))
    return fig


def page_bite(ctx: Ctx):
    fig, axs = page(
        "bite: a neighbour's land inside this district's outline",
        "Same dashed hull. bite counts, in red, the land of other districts' ZIPs (same channel) whose centre falls "
        "inside this district's hull, as a share of the hull. It is high when a district wraps around, or is notched by, "
        "somebody else's territory: the 'bite' taken out of its outline. Lower is better; 0 means no neighbour sits "
        "inside the outline.", 2, 3)
    rows = [r for r in ctx.real if r["hull_km2"] > 0]
    panels = ([(f"Census division, {w}", r) for r, w in zip(census_pair(ctx, "bite", True), ("least bitten", "most bitten"))]
              + [("real district, middling", r) for r in middling(rows, "bite")]
              + [("real district, worst", r) for r in distinct(sorted(rows, key=lambda r: -r["bite"]), 2)])
    for ax, (tag, r) in zip(axs, panels):
        hull_panel(ax, ctx, r, tag, "bite")
    blank(axs, len(panels))
    return fig


# ------------------------------------------------------------------------------ axis and aspect
def farthest(pts: np.ndarray) -> tuple:
    """The two points of `pts` farthest apart (the longest axis `score.extent_km` measures)."""
    u = np.unique(pts, axis=0)
    if len(u) > 3:
        from scipy.spatial import ConvexHull, QhullError
        try:
            u = u[ConvexHull(u).vertices]
        except QhullError:
            pass
    d = np.hypot(*(u[:, None, :] - u[None, :, :]).transpose(2, 0, 1))
    i, j = np.unravel_index(d.argmax(), d.shape)
    return u[i], u[j], float(d[i, j])


def page_axis(ctx: Ctx):
    fig, axs = page(
        "longest_axis_km and aspect: how long and how stretched",
        "longest_axis_km is the longest straight line between two ZIP centres in the district (red): the worst-case "
        "span. aspect is that axis squared over the district's land, so it tells long and thin from round: a disc "
        "scores about 1.3, a long strip scores far higher. Both lower is better. The scorer's 'largest extent' is the same "
        "longest axis.", 2, 2)
    rows = [r for r in ctx.real if r["land_km2"] > 0 and r["aspect"] == r["aspect"]]
    cen = [r for r in ctx.census if r["map"] == "census/divisions"]
    panels = [("real district, most compact (lowest aspect)", min(rows, key=lambda r: r["aspect"])),
              ("real district, most stretched (highest aspect)", max(rows, key=lambda r: r["aspect"])),
              ("real district, longest axis", max(rows, key=lambda r: r["longest_axis_km"]))] if rows else []
    if cen:
        panels.append(("Census division, longest axis", max(cen, key=lambda r: r["longest_axis_km"])))
    for ax, (tag, r) in zip(axs, panels):
        v = ctx.hull_view(r)
        a, b, d = farthest(v["pts"])
        base(ax, box_of(v["land"], v["hull"]), ctx)
        draw_geom(ax, v["land"], facecolor=BLUE, edgecolor="white", lw=0.15, zorder=3)
        ax.plot([a[0], b[0]], [a[1], b[1]], color=RED, lw=1.6, marker="o", ms=3.5, zorder=6)
        assert abs(d - r["longest_axis_km"]) < 0.2, (r["district"], d, r["longest_axis_km"])
        title(ax, tag, ctx, r)
        value(ax, f"longest axis {r['longest_axis_km']:,.0f} km   ·   aspect {r['aspect']:.1f}\n"
              f"{r['longest_axis_km']:,.0f}² ÷ {r['land_km2']:,.0f} km² of land")
    blank(axs, len(panels))
    return fig


# ------------------------------------------------------------------------------ effort
def effort_geometry(ctx: Ctx, row: dict) -> tuple:
    """(land, ZIP centre array, m_rel weights, weighted centroid) of a district; wmean and r90 are checked."""
    cells = ctx.cells(row["map"], row["channel"])
    zs = [z for z, c in cells.items() if c["d"] == row["district"] and z in ctx.ref.idx]
    ii = np.array([ctx.ref.idx[z] for z in zs], dtype=int)
    pts, m = np.c_[ctx.ref.x[ii], ctx.ref.y[ii]], np.array([cells[z]["m"] for z in zs])
    c = (m[:, None] * pts).sum(0) / m.sum() if m.sum() > 0 else pts.mean(0)
    dist = np.hypot(*(pts - c).T)
    if m.sum() > 0 and abs((m * dist).sum() / m.sum() - row["wmean_dist_km"]) > 0.2:
        raise AssertionError(f"explain.py: wmean_dist_km redrawn off for {row['map']} {row['district']}")
    return ctx.union(zs), pts, m, c


def page_effort(ctx: Ctx):
    fig, axs = page(
        "land_per_usd, wmean_dist_km, r90_km: effort to cover the money",
        "These are about where the opportunity sits, not about the outline. The star is the district's money-centre "
        "(opportunity-weighted centroid) and the dots are its ZIPs sized by opportunity (m_rel). wmean_dist_km is the "
        "average distance from the star, weighted by m_rel (solid circle); r90_km is the radius that holds 90% of "
        "m_rel (dashed). land_per_usd is km² of land per $M. Lower means less ground per dollar and shorter trips.", 2, 2)
    rows = [r for r in ctx.real if r["m_rel"] > 0 and r["usd_m"] > 0 and r["n_zips"] >= MIN_ZIPS]
    cen = [r for r in ctx.census if r["map"] == "census/divisions" and r["m_rel"] > 0]
    panels = [("real district, tightest (lowest r90)", min(rows, key=lambda r: r["r90_km"])),
              ("real district, middling r90", middling(rows, "r90_km", 1)[0]),
              ("real district, widest (highest r90)", max(rows, key=lambda r: r["r90_km"]))] if rows else []
    if cen:
        panels.append(("Census division, widest r90", max(cen, key=lambda r: r["r90_km"])))
    for ax, (tag, r) in zip(axs, panels):
        land, pts, m, c = effort_geometry(ctx, r)
        base(ax, box_of(land, extra=[(c[0] + r["r90_km"], c[1] + r["r90_km"]), (c[0] - r["r90_km"], c[1] - r["r90_km"])]), ctx)
        draw_geom(ax, land, facecolor="#cfdcec", edgecolor="white", lw=0.2, zorder=3)
        ax.scatter(pts[:, 0], pts[:, 1], s=2 + 140 * m / max(m.max(), 1e-9), color=BLUE, alpha=0.65, lw=0, zorder=5)
        ax.add_patch(Circle(c, r["wmean_dist_km"], fill=False, ec=RED, lw=1.2, zorder=6))
        ax.add_patch(Circle(c, r["r90_km"], fill=False, ec=RED, lw=1.2, ls=(0, (4, 2)), zorder=6))
        ax.plot(*c, marker="*", color="k", ms=9, mec="white", zorder=7)
        title(ax, tag, ctx, r)
        value(ax, f"land/$M {r['land_per_usd']:,.1f} km²   ·   wmean {r['wmean_dist_km']:,.0f} km   ·   r90 {r['r90_km']:,.0f} km\n"
              f"{r['land_km2']:,.0f} km² of land holding ${r['usd_m']:,.0f}M")
    blank(axs, len(panels))
    return fig


# ------------------------------------------------------------------------------ cut proxy
def cut_edges_of(ctx: Ctx, row: dict, state: str) -> list:
    """[(x0, y0, x1, y1)] ZIP-centre segments of the polygon-graph edges the district's boundary cuts in `state`."""
    cells = ctx.cells(row["map"], row["channel"])
    out = []
    zs = ctx.ref.zips
    for a, b in zip(ctx.ref.ea, ctx.ref.eb):
        ca, cb = cells.get(zs[a]), cells.get(zs[b])
        if ca and cb and ca["s"] == cb["s"] == state and ca["d"] != cb["d"] and row["district"] in (ca["d"], cb["d"]):
            out.append((ctx.ref.x[a], ctx.ref.y[a], ctx.ref.x[b], ctx.ref.y[b]))
    return out


def top_cut_state(row: dict) -> tuple:
    """(state, edges, counties) of the state with the most cut edges in `cut_detail` ('S:e4/c1 ...')."""
    best = max(((s, int(e), int(c)) for s, e, c in re.findall(r"(\w+):e(\d+)/c(\d+)", row["cut_detail"])),
               key=lambda t: (t[1], t[2]), default=None)
    return best


def draw_state_districts(ax, ctx: Ctx, cells: dict, state: str, focus: str) -> dict:
    """The ZIPs of `state` in `cells` unioned per district: `focus` blue, the others in tints; {district: union}."""
    by = collections.defaultdict(list)
    for z, c in cells.items():
        if c["s"] == state:
            by[c["d"]].append(z)
    unions, k = {}, 0
    for d, zs in sorted(by.items()):
        unions[d] = ctx.union(zs)
        col = BLUE if d == focus else TINTS[k % len(TINTS)]
        k += d != focus
        draw_geom(ax, unions[d], facecolor=col, edgecolor="white", lw=0.2, zorder=3)
    return unions


def page_cut(ctx: Ctx):
    fig, axs = page(
        "cut_edges and cut_counties: how roughly a state is carved up",
        "Where two districts share a state, how ragged is the line between them? In every such state, cut_edges counts the "
        "neighbouring-ZIP pairs the boundary separates (red links between ZIP centres) and cut_counties the counties that hold "
        "ZIPs of both districts. A district that owns whole states has 0 of both. Lower is better; a state split along "
        "county lines scores lower than one split ZIP by ZIP.", 2, 2)
    rows = [r for r in ctx.real if r["cut_edges"] > 0]
    cen = [r for r in ctx.census if r["map"] == "census/divisions" and r["channel"] == "national"][:1]
    hi = distinct(sorted(rows, key=lambda r: -r["cut_edges"]), 1)
    low = distinct([r for r in sorted(rows, key=lambda r: (r["cut_edges"], r["cut_counties"]))
                    if r["cut_counties"] > 0 and not (hi and r["states"] == hi[0]["states"])], 1)
    mid = middling([r for r in rows if r["states"] not in {h["states"] for h in hi + low}], "cut_edges", 1)
    panels = [("Census division: whole states, nothing cut", r) for r in cen] + \
             [("real district, fewest cut edges (above 0)", r) for r in low] + \
             [("real district, middling cut", r) for r in mid] + \
             [("real district, most cut edges", r) for r in hi]
    for ax, (tag, r) in zip(axs, panels):
        cells = ctx.cells(r["map"], r["channel"])
        top = top_cut_state(r)
        if top is None:
            land = ctx.union([z for z, c in cells.items() if c["d"] == r["district"]])
            base(ax, box_of(land), ctx)
            draw_geom(ax, land, facecolor=BLUE, edgecolor="white", lw=0.15, zorder=3)
            value(ax, "cut_edges 0   ·   cut_counties 0")
        else:
            st, e, c = top
            unions = draw_state_districts(ax, ctx, {z: v for z, v in cells.items() if v["s"] == st}, st, r["district"])
            base(ax, box_of(*unions.values()), ctx)
            segs = cut_edges_of(ctx, r, st)
            assert len(segs) == e, (r["district"], st, len(segs), e)
            for x0, y0, x1, y1 in segs:
                ax.plot([x0, x1], [y0, y1], color=RED, lw=0.7, zorder=6)
            for d, g in unions.items():
                if d != r["district"]:
                    p = g.representative_point()
                    ax.text(p.x, p.y, d.split("_")[-1], fontsize=7, ha="center", color="#333", zorder=7)
            value(ax, f"{st} shown: {e} cut edges, {c} counties\nwhole district: cut_edges {int(r['cut_edges'])}"
                  f"   ·   cut_counties {int(r['cut_counties'])}")
        title(ax, tag, ctx, r)
    blank(axs, len(panels))
    return fig


# ------------------------------------------------------------------------------ doughnuts
def cbsa_id(ctx: Ctx, label: str):
    for b, n in ctx.ref.cbsa_name.items():
        if n == label:
            return b
    return None


def doughnut_item(row: dict, col: str, needle: str) -> str | None:
    for it in row[col].split("; "):
        if needle in it:
            return it
    return None


def doughnut_example(ctx: Ctx, col: str, needle: str, rows=None, share=None) -> tuple:
    """(row, item) of the first row of `rows` whose `col` names a CBSA containing `needle`."""
    out = []
    for r in (ctx.real if rows is None else rows):
        it = doughnut_item(r, col, needle) if r[col] else None
        if it:
            out.append((r, it))
    return out[0] if out else (None, None)


def page_doughnuts(ctx: Ctx):
    fig, axs = page(
        "doughnuts: a metro split into its money and its land",
        "A doughnut is a metro area (CBSA) cut so that one district gets its money-rich core and another its land-rich "
        "ring. Hard test: a district holds at least half the metro's opportunity on under 30% of its land "
        "(core_without_ring), or at least half the land on under 30% of the opportunity (ring_without_core). Soft test, for metros "
        "cut among many: a share of 15% or more at 4 or more times its share of the other (core_dense, ring_sparse). "
        "In the maps, blue is the district, the other tints other districts; dots are ZIP opportunity. Fewer is better.", 2, 2, top=0.745)
    cen = [r for r in ctx.census if r["doughnut"] == 1]
    cen = sorted(cen, key=lambda r: (r["channel"] != "national", r["map"] != "census/divisions", r["district"]))
    picks = [("hard, core without ring: New York", *doughnut_example(ctx, "core_without_ring", "New York")),
             ("hard, ring without core: St. Louis", *doughnut_example(ctx, "ring_without_core", "St. Louis"))]
    if cen:
        col = "core_without_ring" if cen[0]["core_without_ring"] else "ring_without_core"
        picks.append(("hard, Census division (also St. Louis)", cen[0], cen[0][col].split("; ")[0], col))
    soft = [(r, it) for r in ctx.real if not r["doughnut"] and r["core_dense"] for it in [r["core_dense"].split("; ")[0]]]
    if soft:
        soft.sort(key=lambda t: ("New York" not in t[1], t[0]["map"]))
        picks.append(("soft, core dense", soft[0][0], soft[0][1], "core_dense"))
    cols = {0: "core_without_ring", 1: "ring_without_core"}
    for k, ax in enumerate(axs):
        if k >= len(picks):
            ax.axis("off")
            continue
        tag, r, item = picks[k][:3]
        if r is None:
            ax.axis("off")
            continue
        name = item.rsplit(" (", 1)[0]
        b = cbsa_id(ctx, name)
        cells = ctx.cells(r["map"], r["channel"])
        zs = [z for z, c in cells.items() if c["cbsa"] == b and z in ctx.polys]
        by = collections.defaultdict(list)
        for z in zs:
            by[cells[z]["d"]].append(z)
        unions, kk = {}, 0
        for d, dz in sorted(by.items()):
            unions[d] = ctx.union(dz)
        base(ax, box_of(*unions.values()), ctx)
        for d, g in unions.items():
            col = BLUE if d == r["district"] else TINTS[kk % len(TINTS)]
            kk += d != r["district"]
            draw_geom(ax, g, facecolor=col, edgecolor="white", lw=0.2, zorder=3, alpha=0.9)
        ii = [ctx.ref.idx[z] for z in zs if z in ctx.ref.idx]
        mm = np.array([cells[ctx.ref.zips[i]]["m"] for i in ii])
        ax.scatter(ctx.ref.x[ii], ctx.ref.y[ii], s=1 + 90 * mm / max(mm.max(), 1e-9), color="#222222", alpha=0.55, lw=0, zorder=5)
        title(ax, tag, ctx, r)
        value(ax, "\n".join(textwrap.wrap(item, 70)))
    return fig


# ------------------------------------------------------------------------------ hub
def page_hub(ctx: Ctx):
    fig, axs = page(
        "hub and hub_share: the one metro a district leans on",
        "hub is the metro area (CBSA) that gives the district the most opportunity (m_rel), shown in orange; hub_share is "
        "that metro's share of the district's m_rel. A high share means the district is essentially one city; a low share "
        "means the money is spread over several. It is context for reading the other measures, not a quality score, so "
        "no direction is proposed.", 2, 2)
    real = [r for r in ctx.real if r["hub"] and r["hub_share"] == r["hub_share"] and r["n_zips"] >= MIN_ZIPS]
    cen = [r for r in ctx.census if r["map"] == "census/divisions" and r["hub"]]
    panels = [("real district, most single-metro", max(real, key=lambda r: r["hub_share"])),
              ("real district, most spread out", min(real, key=lambda r: r["hub_share"]))] if real else []
    if cen:
        panels += [("Census division, highest hub_share", max(cen, key=lambda r: r["hub_share"])),
                   ("Census division, lowest hub_share", min(cen, key=lambda r: r["hub_share"]))]
    for ax, (tag, r) in zip(axs, panels):
        cells = ctx.cells(r["map"], r["channel"])
        b = cbsa_id(ctx, r["hub"])
        mine = [z for z, c in cells.items() if c["d"] == r["district"]]
        land = ctx.union(mine)
        hubz = [z for z in mine if cells[z]["cbsa"] == b]
        base(ax, box_of(land), ctx)
        draw_geom(ax, land, facecolor="#cfdcec", edgecolor="white", lw=0.15, zorder=3)
        if hubz:
            draw_geom(ax, ctx.union(hubz), facecolor=ORANGE, edgecolor="white", lw=0.2, zorder=4)
        title(ax, tag, ctx, r)
        value(ax, f"hub_share {r['hub_share']:.2f}\n{r['hub']}")
    blank(axs, len(panels))
    return fig


# ------------------------------------------------------------------------------ the scorer's defects
def run_looks(ctx: Ctx, name: str, ch: str) -> dict:
    g = ctx.geography()
    rows = ctx.run_rows(name)
    if name.startswith("census/"):
        mass = collections.Counter()
        for r in rows:
            mass[r["model_channel"], r["district"]] += float(r["m_rel"] or 0.0)
        drows = [{"channel": c, "district": d, "drawn_mass": m} for (c, d), m in mass.items()]
    else:
        with open(os.path.join(ctx.runs[name], "districts.csv"), encoding="utf-8", newline="") as fh:
            drows = list(csv.DictReader(fh))
    return score.channel_looks(ch, rows, drows, g)


def state_pieces(ax, ctx: Ctx, cells: dict, d: str, hi_state: str | None, pieces: list | None = None) -> None:
    """District `d` by state (the `hi_state` piece red, the rest blue tints); or, with `pieces`, by connected piece."""
    mine = {z: c for z, c in cells.items() if c["d"] == d}
    if pieces:
        groups = {f"piece {i}": set(p) for i, p in enumerate(pieces)}
        cols = {k: (BLUE if k == "piece 0" else RED) for k in groups}
    else:
        by = collections.defaultdict(set)
        for z, c in mine.items():
            by[c["s"]].add(z)
        groups = {s: zs for s, zs in by.items()}
        cols = {s: (RED if s == hi_state else TINTS[i % len(TINTS)]) for i, s in enumerate(sorted(groups))}
    unions = {k: ctx.union(zs) for k, zs in groups.items()}
    base(ax, box_of(*unions.values()), ctx)
    for k, g in unions.items():
        draw_geom(ax, g, facecolor=cols[k], edgecolor="white", lw=0.2, zorder=3)
        if not pieces:
            p = g.representative_point()
            ax.text(p.x, p.y, k, fontsize=7, ha="center", va="center", zorder=7, fontweight="bold")


def first_with(ctx: Ctx, name: str, what: str):
    """(channel, looks) of the first channel of map `name` whose scorer lists `what`."""
    for ch in sorted({r["channel"] for r in ctx.drows if r["map"] == name}):
        looks = run_looks(ctx, name, ch)
        if looks[what]:
            return ch, looks
    return None, None


def page_scorer_a(ctx: Ctx):
    fig, axs = page(
        "scorer: splits, crowded states, small pieces",
        "The looks scorer (tools/looks/score.py) counts state-level untidiness on the drawn map. A channel-state split is a "
        "state where two or more of a channel's districts own a ZIP (cutting a state is sometimes unavoidable). "
        "Crowded: a split state shared by more districts than ceil(its opportunity ÷ τ) + 1, where τ is one district's target "
        "opportunity. Small piece: a district's slice of a split state holds under 0.20 τ, a sliver. Lower is better for all three.", 1, 3,
        top=0.68, bottom=0.24)
    name = "main/ne-48-bal/r2"
    if name not in ctx.runs:
        blank(axs, 0)
        return fig
    done = 0
    ch, looks = first_with(ctx, name, "crowded")
    if ch:
        st = looks["crowded"][0]
        cells = ctx.cells(name, ch)
        unions = draw_state_districts(axs[0], ctx, {z: c for z, c in cells.items() if c["s"] == st}, st, "")
        base(axs[0], box_of(*unions.values()), ctx)
        n = len(unions)
        mass = sum(c["m"] for c in cells.values() if c["s"] == st)
        ax = axs[0]
        for d, g in unions.items():
            p = g.representative_point()
            ax.text(p.x, p.y, d.split("_")[-1], fontsize=7, ha="center", color="#333", zorder=7)
        ax.set_title(f"crowded state\n{ctx.label(name)} · {ch} · {st}", fontsize=6.8, loc="left")
        value(ax, f"{st}: {n} {ch} districts own ZIPs here\nlimit ceil({mass / looks['tau']:.1f}) + 1 = {math.ceil(mass / looks['tau']) + 1}")
        done += 1
    ch, looks = first_with(ctx, name, "small")
    if ch:
        d, st, tau = looks["small"][0]
        cells = ctx.cells(name, ch)
        state_pieces(axs[1], ctx, cells, d, st)
        axs[1].set_title(f"small piece\n{ctx.label(name)} · {d}", fontsize=6.8, loc="left")
        value(axs[1], f"{d}'s slice of {st} (red) holds {tau:.2f} τ\nunder the 0.20 τ floor")
        done += 1
    ch, looks = first_with(ctx, name, "split")
    if ch:
        st = [s for s in looks["split"] if s not in looks["crowded"]][:1] or looks["split"][:1]
        cells = ctx.cells(name, ch)
        unions = draw_state_districts(axs[2], ctx, {z: c for z, c in cells.items() if c["s"] == st[0]}, st[0], "")
        base(axs[2], box_of(*unions.values()), ctx)
        for d, g in unions.items():
            p = g.representative_point()
            axs[2].text(p.x, p.y, d.split("_")[-1], fontsize=7, ha="center", color="#333", zorder=7)
        axs[2].set_title(f"channel-state split\n{ctx.label(name)} · {ch} · {st[0]}", fontsize=6.8, loc="left")
        value(axs[2], f"{st[0]} is split among {len(unions)} {ch} districts\nmap total: {sum(len(looks['split']) for looks in [looks])} splits in {ch}")
        done += 1
    blank(axs, done)
    return fig


def neck_example(ctx: Ctx):
    """(map, channel, district, text, [zips]) of the first neck line in a discovered run's score.txt."""
    for name, path in ctx.runs.items():
        sp = os.path.join(path, "score.txt")
        if not os.path.exists(sp):
            continue
        for line in open(sp, encoding="utf-8"):
            m = re.match(r"\s+(\w+)/(\w+): (neck [\d.]+ km wide cuts off .*?); cut (.*)$", line.rstrip())
            if m:
                zips = sorted(set(re.findall(r"\b(\d{5})\b", m.group(4))))
                return name, m.group(1), m.group(2), m.group(3), zips
    return None


def page_scorer_b(ctx: Ctx):
    fig, axs = page(
        "scorer: thin links, detached pieces, necks",
        "Thin link: a district's piece in one state touches its pieces in its other states along under 25 km of ZIP border, "
        "so two states are joined by a thread. Detached piece: part of a district is not connected to the rest on the drawn "
        "ZIP map; each counts 1 + its opportunity ÷ τ, and M1 (the contiguity mandate) fails the map. Neck: a part holding "
        "5% or more of a district's land is joined to the rest by a passage under 10 km. Multipart islets (coastal ZIPs "
        "drawn in separate land parts) are listed by the scorer too, but are not in these counts. Lower is better; M1 wants zero.",
        1, 3, top=0.67, bottom=0.24)
    done = 0
    name = "main/w1-50-wide/r2"
    if name in ctx.runs:
        ch, looks = first_with(ctx, name, "thin")
        if ch:
            d, st, km = looks["thin"][0]
            state_pieces(axs[0], ctx, ctx.cells(name, ch), d, st)
            axs[0].set_title(f"thin link\n{ctx.label(name)} · {d}", fontsize=6.8, loc="left")
            value(axs[0], f"{d}'s {st} piece (red) borders its other\nstates along {km:g} km (limit 25 km)")
            done += 1
    name = "main/nw34-48-wide/r2"
    if name in ctx.runs:
        ch, looks = first_with(ctx, name, "pieces")
        if ch:
            d, nzip, tau, sts = looks["pieces"][0]
            cells = ctx.cells(name, ch)
            g = ctx.geography()
            owner = {z: c["d"] for z, c in cells.items()}
            mass = {z: c["m"] for z, c in cells.items()}
            comps = score.audit.district_pieces(owner, g.polygon_adj, mass)[d]
            state_pieces(axs[1], ctx, cells, d, None, pieces=comps)
            axs[1].set_title(f"detached piece\n{ctx.label(name)} · {d}", fontsize=6.8, loc="left")
            value(axs[1], f"{d}: {nzip} ZIPs in {sts} (red) are cut off\nfrom the main piece (blue), {tau:.2f} τ")
            done += 1
    ex = neck_example(ctx)
    if ex:
        name, ch, d, text, zips = ex
        cells = ctx.cells(name, ch)
        mine = [z for z, c in cells.items() if c["d"] == d and z in ctx.polys]
        land, cut = ctx.union(mine), ctx.union([z for z in zips if z in ctx.polys])
        ax = axs[2]
        base(ax, (cut.bounds[0] - 40, cut.bounds[1] - 40, cut.bounds[2] + 40, cut.bounds[3] + 40), ctx, pad=0.0)
        draw_geom(ax, land, facecolor=BLUE, edgecolor="white", lw=0.15, zorder=3)
        draw_geom(ax, cut, facecolor=RED, edgecolor="white", lw=0.2, zorder=4)
        ax.set_title(f"neck (M1)\n{ctx.label(name)} · {d}", fontsize=6.8, loc="left")
        value(ax, "\n".join(textwrap.wrap(f"{d}: {text.replace('cuts off', 'cut off')} (red = the cut ZIPs)", 62)))
        done += 1
    blank(axs, done)
    return fig


# ------------------------------------------------------------------------------ glossary
def span(vals, fmt: str = "{:.2f}", med: bool = True) -> str:
    vals = [v for v in vals if v == v]
    if not vals:
        return "n/a"
    lo, hi = fmt.format(min(vals)), fmt.format(max(vals))
    return f"{lo} to {hi}" + (f" (med {fmt.format(statistics.median(vals))})" if med else "")


def score_counts(ctx: Ctx) -> dict:
    """{'real'|'census': {key: [per-map totals]}} of the scorer's counts, from `score.channel_looks`."""
    out = {g: collections.defaultdict(list) for g in ("real", "census")}
    names = [(r["map"], "census" if r["group"] == "reference" else "real") for r in ctx.mrows]
    for name, grp in names:
        if name in ("census/regions", "census/regions_ifa"):
            continue
        chans = sorted({r["channel"] for r in ctx.drows if r["map"] == name})
        ls = [run_looks(ctx, name, ch) for ch in chans]
        out[grp]["splits"].append(sum(len(c["split"]) for c in ls))
        out[grp]["thin"].append(sum(len(c["thin"]) for c in ls))
        out[grp]["small"].append(sum(len(c["small"]) for c in ls))
        out[grp]["crowded"].append(sum(len(c["crowded"]) for c in ls))
        out[grp]["pieces"].append(sum(len(c["pieces"] or ()) for c in ls))
        if all(c["multipart"] is not None for c in ls):
            out[grp]["multipart"].append(sum(len(c["multipart"]) for c in ls))
        out[grp]["states"].append(max(c["max_states"] for c in ls))
        out[grp]["necks"] = []
    out["real"]["necks"] = [r["necks"] for r in ctx.mrows if r["group"] != "reference" and r["necks"] == r["necks"]]
    return out


def glossary_rows(ctx: Ctx) -> list:
    """[(metric, meaning, formula, direction, census range, real range)]."""
    cen = ctx.census
    sc = ctx.score_counts

    def per(col, fmt="{:.2f}", med=True):
        return span([r[col] for r in cen], fmt, med=False), span([r[col] for r in ctx.real], fmt, med)

    def count(key):
        c, r = sc.get("census", {}).get(key, []), sc.get("real", {}).get(key, [])
        return (span(c, "{:.0f}", False) if c else "n/a (whole states)"), (span(r, "{:.0f}", True) + " per map" if r else "n/a")

    def share(col):
        return (f"{int(sum(r[col] for r in cen))} of {len(cen)}", f"{int(sum(r[col] for r in ctx.real))} of {len(ctx.real)}")

    rows = [
        ("hull_fill", "How much of the outline around the district's ZIP centres is its own land. 1 = solid.",
         "district land ÷ convex-hull area (capped at 1)", "higher", *per("hull_fill")),
        ("bite", "Other districts' land sitting inside this district's outline: how much it wraps a neighbour.",
         "land of other districts' ZIPs with centre in the hull ÷ hull area", "lower", *per("bite")),
        ("longest_axis_km", "Longest straight line between two ZIP centres in the district.",
         "max pairwise distance of ZIP centres, km", "lower", *per("longest_axis_km", "{:,.0f}")),
        ("aspect", "How stretched: about 1.3 for a disc, much more for a strip.",
         "longest_axis² ÷ district land", "lower", *per("aspect", "{:.1f}")),
        ("cut_edges", "How ragged the line is where it shares a state with another district.",
         "ZIP neighbour pairs, same state, split between two districts", "lower", *per("cut_edges", "{:.0f}")),
        ("cut_counties", "Counties holding ZIPs of this district and another.",
         "counties in shared states with both", "lower", *per("cut_counties", "{:.0f}")),
        ("land_per_usd", "Ground to cover per dollar of opportunity.",
         "district land km² ÷ $M", "lower*", *per("land_per_usd", "{:,.0f}")),
        ("wmean_dist_km", "Typical distance from the money-centre, weighted by opportunity.",
         "Σ m_rel·dist ÷ Σ m_rel, from the m_rel centroid", "lower*", *per("wmean_dist_km", "{:,.0f}")),
        ("r90_km", "Radius around the money-centre holding 90% of the opportunity.",
         "smallest radius with 90% of m_rel", "lower*", *per("r90_km", "{:,.0f}")),
        ("doughnut (hard)", "A metro cut so one district has its core money, another its outer land.",
         "core: ≥50% m_rel on <30% land; ring: ≥50% land on <30% m_rel", "none", *share("doughnut")),
        ("doughnut (soft)", "Same idea for metros cut among many districts.",
         "≥15% of one at ≥4× the share of the other", "none", *share("doughnut_soft")),
        ("hub_share", "Share of the district's money from its single biggest metro.",
         "m_rel of top CBSA ÷ district m_rel", "context", *per("hub_share")),
        ("splits (scorer)", "States where two or more districts of a channel own ZIPs.",
         "Σ channels of states with ≥2 owners", "lower", *count("splits")),
        ("crowded (scorer)", "A split state shared by too many districts.",
         "owners > ceil(state m_rel ÷ τ) + 1", "lower", *count("crowded")),
        ("small piece (scorer)", "A district's sliver of a split state.",
         "piece m_rel < 0.20 τ", "lower", *count("small")),
        ("thin link (scorer)", "A district's state pieces joined by under 25 km of border.",
         "ZIP border to its other-state pieces < 25 km", "lower", *count("thin")),
        ("detached piece", "Part of a district cut off from the rest on the ZIP map (M1).",
         "components beyond the heaviest, weight 1 + m_rel/τ", "zero", *count("pieces")),
        ("neck (M1)", "A big part reached only through a narrow passage.",
         "part ≥5% of land, passage < 10 km", "zero", "n/a", span(sc.get("real", {}).get("necks", []), "{:.0f}", True) + " per map"
         if sc.get("real", {}).get("necks") else "n/a"),
        ("states per district", "Most states one district owns ZIPs in.",
         "max n_states over districts", "lower", span([r["n_states"] for r in cen], "{:.0f}", False),
         span([r["n_states"] for r in ctx.real], "{:.0f}")),
    ]
    return rows


def page_glossary(ctx: Ctx):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.03, 0.965, "What the 'nice shape' numbers mean", fontsize=17, fontweight="bold", va="top")
    fig.text(0.03, 0.925, textwrap.fill(
        "Per-district measures from the looks study of 2026-10-13 (tools/looks/study.py) and the looks scorer (tools/looks/score.py). "
        "Pages 2 to 10 show each one on real districts. Ranges: min to max, median in brackets.", 150),
        fontsize=8.6, va="top", color="#333333")
    cols = [("Metric", 0.03, 0.105), ("Plain English", 0.135, 0.245), ("Formula", 0.38, 0.205),
            ("Better", 0.585, 0.045), ("Census divisions", 0.63, 0.16), ("Real maps", 0.79, 0.19)]
    y = 0.865
    for name, x, _ in cols:
        fig.text(x, y, name, fontsize=8, fontweight="bold", va="top")
    fig.add_artist(plt.Line2D([0.03, 0.98], [y - 0.014, y - 0.014], color="k", lw=0.8))
    y -= 0.022
    fs = 6.9
    for i, row in enumerate(glossary_rows(ctx)):
        wrapped = [textwrap.wrap(str(t), max(8, int(w * 11 * 15.5 * 7.0 / fs))) or [""] for t, (_, _, w) in zip(row, cols)]
        n = max(len(w) for w in wrapped)
        h = n * 0.0148 + 0.0075
        if i % 2 == 0:
            fig.add_artist(plt.Rectangle((0.03, y - h + 0.003), 0.95, h, color="#f1f4f8", zorder=0, transform=fig.transFigure))
        for (_, x, _), lines in zip(cols, wrapped):
            fig.text(x, y - 0.002, "\n".join(lines), fontsize=fs, va="top", linespacing=1.3,
                     fontweight="bold" if x == 0.03 else "normal")
        y -= h
    fig.text(0.03, 0.062, textwrap.fill(
        "* Effort measures, read within a channel; no limit is proposed for them.  Census divisions: the 9 divisions as whole-state "
        "districts, per channel.  'Better': the direction a reader would call nicer; only the four limits on page 11 are proposed, "
        "and they are provisional.", 200), fontsize=7, va="top", color="#333333")
    return fig


# ------------------------------------------------------------------------------ the provisional limits
def limits_table(drows: list, mrows: list) -> list:
    """[(map, districts, [fail count per LIMITS], any)] for each scored map."""
    out = []
    for m in mrows:
        rs = [r for r in drows if r["map"] == m["map"]]
        counts = [sum(1 for r in rs if test(r)) for _, test, _ in LIMITS]
        out.append((m["map"], len(rs), counts, sum(1 for r in rs if any(t(r) for _, t, _ in LIMITS))))
    return out


def page_limits(ctx: Ctx):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.03, 0.965, "PROVISIONAL, NOT DECIDED: what the proposed limits would fail", fontsize=16, fontweight="bold",
             va="top", color=RED)
    fig.text(0.03, 0.925, textwrap.fill(
        "Limits proposed on 2026-10-14: bite ≤ 0.30, hull_fill ≥ 0.45, at most 4 states per district, no hard doughnut. Each cell "
        "is the number of districts in that map failing the limit; 'any limit' counts a district once.", 150),
        fontsize=8.6, va="top", color="#333333")
    heads = ["map (shortlist id or run)", "districts"] + [lab for _, _, lab in LIMITS] + ["any limit"]
    xs = [0.03, 0.37, 0.46, 0.57, 0.68, 0.80, 0.90]
    y = 0.865
    for h, x in zip(heads, xs):
        fig.text(x, y, h, fontsize=8, fontweight="bold", va="top")
    fig.add_artist(plt.Line2D([0.03, 0.98], [y - 0.014, y - 0.014], color="k", lw=0.8))
    y -= 0.024
    rows = limits_table(ctx.drows, ctx.mrows)
    step = min(0.0295, (y - 0.09) / max(len(rows), 1))
    for i, (name, n, counts, anyf) in enumerate(rows):
        if i % 2 == 0:
            fig.add_artist(plt.Rectangle((0.03, y - step + 0.005), 0.95, step, color="#f1f4f8", zorder=0, transform=fig.transFigure))
        ref = name.startswith("census/")
        lab = ctx.label(name) + ("  (reference)" if ref else "")
        fig.text(xs[0], y, lab, fontsize=7.4, va="top", fontweight="bold" if ref else "normal")
        if not ref and short(name).split()[-1] != lab and short(name) != lab:
            fig.text(xs[0] + 0.012 + 0.0052 * len(lab), y, f"= {short(name)}", fontsize=6.4, va="top", color="#666666")
        for v, x in zip([n] + counts + [anyf], xs[1:]):
            fig.text(x, y, f"{v}", fontsize=7.4, va="top", color=RED if v and x != xs[1] else "k")
        y -= step
    fig.text(0.03, 0.065, textwrap.fill(
        "Counts are over all planning channels of a map, from districts.csv of the 2026-10-13 study (bite > 0.30, hull_fill < 0.45 and "
        "more than 4 states fail; a hard doughnut is the study's doughnut flag). Census rows are reference pseudo-maps of whole "
        "states. Nothing here is a decision.", 210), fontsize=7, va="top", color="#333333")
    return fig


# ------------------------------------------------------------------------------ build
PAGES = (page_glossary, page_hull_fill, page_bite, page_axis, page_effort, page_cut, page_doughnuts, page_hub,
         page_scorer_a, page_scorer_b, page_limits)


def build(ctx: Ctx, out: str, pages=PAGES, log=print) -> str:
    """Write the PDF of `pages` for `ctx` to `out`; the glossary needs `ctx.score_counts`."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with PdfPages(out, metadata={"Title": "Looks metrics explained", "Author": "Agent: worker (claude-bridge/claude-sonnet-5-5)"}) as pdf:
        for n, fn in enumerate(pages, 1):
            fig = fn(ctx)
            fig.text(0.97, 0.018, f"{n} / {len(pages)}", fontsize=7, ha="right", color="#666666")
            fig.text(0.03, 0.018, "looks metrics explained · 2026-10-14 · tools/looks/explain.py · data: looks study 2026-10-13",
                     fontsize=7, color="#666666")
            pdf.savefig(fig)
            plt.close(fig)
            log(f"page {n}: {fn.__name__}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--study", default=STUDY_DIR)
    args = ap.parse_args(argv)
    ctx = Ctx.load(args.study)
    ctx.score_counts = score_counts(ctx)
    print("wrote", build(ctx, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
