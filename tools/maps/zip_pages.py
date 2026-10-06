"""zip_pages.py -- the ZIP-level pages of a run folder in the required look: one page per planning
channel (#120; ported from `runs/autonomous_2026-10-05/batch_border/zip_pages.py`, m5, gitignored).

    "$TD_PY" tools/maps/zip_pages.py <run_dir> <label> <out_dir> [--corridor] [--fac PATH]
        [--cache DIR]

`tools/maps/render.py` calls `main`; this CLI is the same.  The page title is
`<label>  ·  <channel>: K districts`; files are `zip_<channel>.png` and `zip_pages.pdf` in
`out_dir`.

Every ZCTA a district owns in the ledger (zero-m_rel territory included) is filled in its
district's colour, drawn with td/output.py's helpers (`zcta_polygons`, `_polygon_path`).  CONUS
land in no ZCTA is drawn light grey as unassigned land and joins no district (owner ruling).  The
land is the 2025 cartographic-boundary states (cb_2025_us_state_500k) less the union of every
CONUS ZCTA, opened by `OPEN_M` so the slivers of a 250 m simplification and a generalised
shoreline do not read as land.  Insets: the NYC metro, and with --corridor BOS-WAS.

The inputs that are not tracked are read from `$TD_REPO` or flags, never copied into the repo:
`--cache` holds `cb_2025_us_state_500k.zip` and the pickled ZCTA polygons, state shapes and
no-ZCTA land (built from `$TD_REPO/data/public` on a miss); `--fac` the $ per m_rel of each
current channel (`tables.json`'s `fac`, from the owner's channel totals).  The run path in the
footer is relative to `$TD_REPO`.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
TD_REPO = os.environ.get("TD_REPO", ROOT)

import matplotlib                                   # noqa: E402
matplotlib.use("Agg")
import matplotlib.patheffects as pe                 # noqa: E402
import matplotlib.pyplot as plt                     # noqa: E402
import numpy as np                                  # noqa: E402
import shapely                                      # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Patch, PathPatch, Rectangle  # noqa: E402
from pyproj import Transformer                      # noqa: E402

from td import geo                                  # noqa: E402
from td.output import _polygon_path, zcta_polygons  # noqa: E402

CACHE = os.path.join(TD_REPO, "runs", "autonomous_2026-10-05", "batch", "geo")
FAC_JSON = os.path.join(TD_REPO, "runs", "sweep", "grid_2026-10-01", "tables.json")
OPEN_M = 1000.0             # opening radius of the no-ZCTA land: drops slivers under 2 km wide
UNASSIGNED = "#dcdcdc"
UNASSIGNED_TEXT = "Land in no ZCTA: unassigned, part of no district"
OTHER_FILL, OTHER_EDGE = "#f6f6f6", "#b8b8b8"   # ZCTAs another planning channel of the map plans
# lon/lat boxes (west, south, east, north)
NYC = ("NYC metro (NY / NJ / CT)", (-74.4, 40.4, -73.0, 41.4))
CORRIDOR = ("BOS–WAS corridor", (-77.6, 38.6, -70.0, 42.9))
PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6",
           "#bfef45", "#9a6324", "#469990", "#dcbeff", "#800000", "#aaffc3", "#808000",
           "#ffd8b1", "#000075", "#fabed4", "#ffe119"]
SCORE = os.path.join(ROOT, "tools", "looks", "score.py")


def score_constant(name):
    import ast
    for node in ast.parse(open(SCORE).read()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


TARGET, DOLLAR_BAND, DOLLARS = (score_constant(n) for n in ("TARGET", "DOLLAR_BAND", "DOLLARS"))


def read_fac(path: str = FAC_JSON) -> dict:
    """$M per m_rel of each current channel."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["fac"]


def cached(name, build, cache: str = CACHE):
    path = os.path.join(cache, name)
    if os.path.exists(path):
        with open(path, "rb") as fh:
            return pickle.load(fh)
    out = build()
    with open(path, "wb") as fh:
        pickle.dump(out, fh, protocol=4)
    return out


def all_zctas() -> list:
    import gzip
    with gzip.open(os.path.join(geo.REFERENCE_DIR, "zcta_reference.csv.gz"), "rt") as fh:
        return sorted({r["zcta"] for r in csv.DictReader(fh) if r["graph_vertex"] == "1"})


def states(cache: str = CACHE) -> dict:
    st = geo._read(os.path.join(cache, "cb_2025_us_state_500k.zip"), ["STATEFP", "STUSPS"])
    st = st[st["STATEFP"].isin(geo.CONUS_STATEFP)]
    return dict(zip(st["STUSPS"], st.geometry))


def no_zcta_land(polys: dict, st: dict):
    land = shapely.union_all(list(st.values()))
    covered = shapely.union_all(list(polys.values()))
    gap = shapely.difference(land, covered)
    return gap.buffer(-OPEN_M).buffer(OPEN_M)


def bbox(lonlat):
    tr = Transformer.from_crs("EPSG:4326", geo.CRS, always_xy=True)
    w, s, e, n = lonlat
    lon = np.linspace(w, e, 25)
    lat = np.linspace(s, n, 25)
    xs, ys = tr.transform(np.r_[lon, lon, np.full(25, w), np.full(25, e)],
                          np.r_[np.full(25, s), np.full(25, n), lat, lat])
    return min(xs), min(ys), max(xs), max(ys)


def neighbours(unions: dict) -> dict:
    """{district: districts within 5 km of it}."""
    ids = sorted(unions)
    near = {d: set() for d in ids}
    geoms = [unions[d].buffer(5000) for d in ids]
    a, b = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    for i, j in zip(a, b):
        if i != j:
            near[ids[i]].add(ids[j])
    return near


def colouring(unions: dict, near: dict) -> dict:
    """Greedy: no two districts within 5 km share a colour; among the free colours, the least used."""
    out, used = {}, collections.Counter()
    for d in sorted(unions, key=lambda d: (-len(near[d]), d)):
        taken = {out[x] for x in near[d] if x in out}
        out[d] = min((c for c in PALETTE if c not in taken), key=lambda c: (used[c], PALETTE.index(c)))
        used[out[d]] += 1
    return out


def borders(unions: dict, near: dict) -> list:
    """The lines where two districts meet: each district's boundary within 300 m of a neighbour.
    The edge of a district against land in no ZCTA or water is not drawn, so unassigned land reads
    as grey land, not as a hole cut out of a district."""
    out = []
    for d, u in unions.items():
        if not near[d]:
            continue
        other = shapely.union_all([unions[x].buffer(300) for x in near[d]])
        out.append(u.boundary.intersection(other))
    return out


def draw(ax, ch_rows, polys, unions, colour, lines, st, gap, other, box=None, labels=True, fs=7):
    if other is not None and not other.is_empty:
        ax.add_patch(PathPatch(_polygon_path(other), facecolor=OTHER_FILL, edgecolor=OTHER_EDGE,
                               hatch="////", linewidth=0, zorder=1))
    if gap is not None and not gap.is_empty:
        ax.add_patch(PathPatch(_polygon_path(gap), facecolor=UNASSIGNED, edgecolor="none", zorder=1))
    for d, zs in ch_rows.items():
        shapes = [polys[z] for z in zs if z in polys]
        ax.add_collection(PatchCollection([PathPatch(_polygon_path(p)) for p in shapes],
                                          facecolor=colour[d], edgecolor=colour[d], linewidth=0.25,
                                          alpha=0.75, zorder=2))
    segs = [np.asarray(ln.coords)[:, :2] for g in lines for ln in shapely.get_parts(g)
            if ln.geom_type == "LineString" and not ln.is_empty]
    from matplotlib.collections import LineCollection
    ax.add_collection(LineCollection(segs, colors="#202020", linewidths=0.8, zorder=4))
    for poly in st.values():
        ax.add_patch(PathPatch(_polygon_path(poly), facecolor="none", edgecolor="#606060",
                               linewidth=0.5, linestyle=(0, (4, 2)), zorder=3))
    if labels:
        view = shapely.box(*box) if box else None
        for d, u in unions.items():
            g = u if view is None else u.intersection(view)
            if g.is_empty:
                continue
            part = max(getattr(g, "geoms", [g]), key=lambda p: p.area)
            p = part.representative_point()
            ax.text(p.x, p.y, d.rsplit("_", 1)[1], ha="center", va="center", fontsize=fs,
                    fontweight="bold", zorder=6,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    if box:
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[1], box[3])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def page(run_dir, label, ch, ch_rows, polys, st, gap, other, other_names, names, dollars, insets, out_dir, extra):
    unions = {d: shapely.union_all([polys[z] for z in zs if z in polys]).buffer(150).buffer(-150)
              for d, zs in ch_rows.items()}
    near = neighbours(unions)
    colour = colouring(unions, near)
    lines = [shapely.line_merge(g) if g.geom_type == "MultiLineString" else g for g in borders(unions, near)]
    k = len(ch_rows)
    fig = plt.figure(figsize=(20, 11.5), dpi=130, facecolor="white")
    n_in = len(insets)
    ax = fig.add_axes([0.005, 0.12, 0.66, 0.80])
    x0, y0, x1, y1 = shapely.total_bounds(list(st.values()))
    pad = 0.01 * (x1 - x0)
    main_box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    draw(ax, ch_rows, polys, unions, colour, lines, st, gap, other, main_box, fs=7 if k < 30 else 6)
    for spine in ax.spines.values():
        spine.set_visible(False)
    hgt = 0.80 / max(n_in, 1)
    for i, (title, lonlat) in enumerate(insets):
        b = bbox(lonlat)
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False,
                               edgecolor="black", linewidth=1.0, zorder=7))
        ax.text(b[0], b[3], f" {chr(65 + i)}", ha="left", va="bottom", fontsize=9, fontweight="bold", zorder=7)
        iax = fig.add_axes([0.665, 0.12 + 0.80 - (i + 1) * hgt + 0.01, 0.20, hgt - 0.02])
        draw(iax, ch_rows, polys, unions, colour, lines, st, gap, other, b, fs=8)
        iax.set_title(f"{chr(65 + i)}: {title}", fontsize=10)
    handles = [Patch(facecolor=colour[d], alpha=0.75, edgecolor="#202020",
                     label=f"{d.rsplit('_', 1)[1]} {names.get(d, d).split(' ', 1)[-1][:30]}")
               for d in sorted(ch_rows)]
    handles.append(Patch(facecolor=UNASSIGNED, edgecolor="none", label=UNASSIGNED_TEXT))
    if other_names:
        handles.append(Patch(facecolor=OTHER_FILL, edgecolor=OTHER_EDGE, hatch="////",
                             label=f"Planned in {', '.join(other_names)} (its own page)"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.868, 0.93), fontsize=6.3 if k < 30 else 5.6,
               frameon=False, ncol=1, handlelength=1.2, borderaxespad=0)
    t = TARGET.get(ch)
    m = list(dollars.values())
    mean = sum(m) / len(m)
    vs = f"target \\${t / 1e6:,.0f}M ±{100 * DOLLAR_BAND:.0f}%" if t else "no \\$ target"
    fig.suptitle(f"{label}  ·  {ch}: {k} districts", fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.01, 0.075, f"\\${min(m):,.0f}M to \\${max(m):,.0f}M per district, drawn mean \\${mean:,.0f}M ({vs})  ·  "
             f"{extra['splits']}", fontsize=10.5)
    fig.text(0.01, 0.045, f"Every ZCTA a district owns is filled, zero-opportunity territory included.  "
             f"Grey: land in no ZCTA, unassigned (owner ruling), not a hole in a district.  "
             f"Black: borders between districts; dashed: state lines.  Run: {os.path.relpath(run_dir, TD_REPO)}", fontsize=8.5, color="#404040")
    fig.text(0.01, 0.022, "Opportunity \\$ = m_rel × the owner's channel totals; no sales data.  "
             f"No-ZCTA land: cb_2025_us_state_500k less every CONUS ZCTA (250 m simplified), opened by "
             f"{OPEN_M / 1000:g} km.", fontsize=8.5, color="#404040")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"zip_{ch}.png")
    fig.savefig(path, dpi=130, facecolor="white")
    return fig, path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("label")
    ap.add_argument("out_dir")
    ap.add_argument("--corridor", action="store_true")
    ap.add_argument("--fac", default=FAC_JSON, help="tables.json with `fac`, $M per m_rel")
    ap.add_argument("--cache", default=CACHE, help="the state shapes and the pickled geometry")
    a = ap.parse_args(argv)
    FAC = read_fac(a.fac)
    public = os.path.join(TD_REPO, "data", "public")
    zall = all_zctas()
    polys = cached("zcta_polys.pkl", lambda: zcta_polygons(zall, public), a.cache)
    st = cached("states.pkl", lambda: states(a.cache), a.cache)
    gap = cached("no_zcta_land.pkl", lambda: no_zcta_land(polys, st), a.cache)
    with open(os.path.join(a.run_dir, "districts.csv"), newline="") as fh:
        names = {r["district"]: r["district_name"] for r in csv.DictReader(fh)}
    owned = collections.defaultdict(lambda: collections.defaultdict(set))
    usd = collections.defaultdict(collections.Counter)
    with open(os.path.join(a.run_dir, "ledger.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if not r["district"]:
                continue
            owned[r["model_channel"]][r["district"]].add(r["zip_code"])
            m = float(r["m_rel"])
            if m > 0:
                usd[r["model_channel"]][r["district"]] += m * FAC[r["current_channel"]]
    zst = {}
    with open(os.path.join(a.run_dir, "ledger.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            zst[r["zip_code"]] = r["state"]
    insets = [NYC] + ([CORRIDOR] if a.corridor else [])
    written = []
    for ch in sorted(owned, key=lambda c: ["national", "WH", "FI", "WIFI", "IFA"].index(c)):
        rows = owned[ch]
        held = collections.defaultdict(set)
        for d, zs in rows.items():
            for z in zs:
                held[zst[z]].add(d)
        split = sorted(s for s, ds in held.items() if len(ds) > 1)
        missing = sorted({z for zs in rows.values() for z in zs} - set(polys))
        extra = {"splits": f"{len(split)} split states: {' '.join(split) or 'none'}"
                 + (f"  ·  {len(missing)} owned ZCTAs with no polygon" if missing else "")}
        mine = {z for zs in rows.values() for z in zs}
        other_names = [c for c in owned if c != ch
                       and any(z not in mine for zs in owned[c].values() for z in zs)]
        elsewhere = {z for c in other_names for zs in owned[c].values() for z in zs} - mine
        other = (shapely.union_all([polys[z] for z in elsewhere if z in polys]).buffer(150).buffer(-150)
                 if elsewhere else None)
        fig, path = page(a.run_dir, a.label, ch, rows, polys, st, gap, other, other_names, names,
                         {d: usd[ch][d] for d in rows}, insets, a.out_dir, extra)
        plt.close(fig)
        written.append(path)
        print(f"{ch}: {len(rows)} districts, {sum(map(len, rows.values()))} ZCTAs, "
              f"{len(missing)} without polygon, splits {len(split)} -> {path}", flush=True)
    from PIL import Image                          # a raster PDF: the vector one runs to 100+ MB
    pages = [Image.open(p).convert("RGB") for p in written]
    written.append(os.path.join(a.out_dir, "zip_pages.pdf"))
    pages[0].save(written[-1], save_all=True, append_images=pages[1:], resolution=130)
    return written


if __name__ == "__main__":
    main()
