"""zip_pages.py -- the ZIP-level pages of a run folder in the required look: one page per planning
channel (#120; ported from `runs/autonomous_2026-10-05/batch_border/zip_pages.py`, m5, gitignored).

    "$TD_PY" tools/maps/zip_pages.py <run_dir> <label> <out_dir> [--corridor] [--fac PATH]
        [--cache DIR]

`tools/maps/render.py` calls `main`; this CLI is the same.  The pages are the primary view of a
rendered run (owner, 2026-10-13): `zip_summary.png`, then one `zip_<channel>.png` per planning
channel, and `zip_pages.pdf` holding them in that order, all in `out_dir`; `main` returns those
paths, the PDF last.  A channel page's title is `<label>  ·  <channel>: K districts`.

The summary page (`summary_page`, title `<label>  ·  territories per state`) is a CONUS state
map: each state filled by how many districts, across all planning channels, own a ZCTA filed
there (the ledger's `state`; `state_territories`), on a light ramp of 1 to `COUNT_BINS`+; its
label the state and each channel's count there (`N 2 · W 3`, `ABBR`), a count of 2 or more in
bold.  A state is split in a channel when 2+ of its districts own ZCTAs there (`split_states`);
a split state has a thick dark outline, and the caption lists each channel's split states.  The
Northeast inset (`NORTHEAST`) carries the small states; a state label that does not fit inside
its state gets a leader line, and on the main map is left to the inset when the state is in it.

Every page labels the major metros (`metros`): the `METROS` CBSA Metro Areas with the most
opportunity $ in the run's ledger (owned rows, through the ledger's `cbsa`), each at its CBSA's
gazetteer internal point and named by the first principal city of its title (two for `TWIN`),
from the tracked `reference/2025/areas.csv.gz`.  `place_labels` sets a dot and a label in rank
order, trying offsets around the dot, then further ones with a leader line, and drops a metro
whose label would overlap a placed label, dot or district number, so dense areas thin out; the
insets, at a larger scale, carry more.

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
import shapely.ops                                  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.lines import Line2D                 # noqa: E402
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
NORTHEAST = ("Northeast and Mid-Atlantic", (-80.6, 37.0, -66.8, 47.6))
CHANNELS = ["national", "WH", "FI", "WIFI", "IFA"]   # the page order
ABBR = {"national": "N", "WH": "WH", "FI": "FI", "WIFI": "W", "IFA": "IFA"}
COUNT_BINS = 6              # the summary's fill: 1, 2, ..., COUNT_BINS or more territories
SPLIT_EDGE = "#7a0000"
METROS = 30                 # metros labelled, before thinning
TWIN = ("Dallas", "Minneapolis")   # metros named by their first two principal cities
AREAS = os.path.join(geo.REFERENCE_DIR, "areas.csv.gz")
PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6",
           "#bfef45", "#9a6324", "#469990", "#dcbeff", "#800000", "#aaffc3", "#808000",
           "#ffd8b1", "#000075", "#fabed4", "#ffe119"]
SCORE = os.path.join(ROOT, "tools", "looks", "score.py")
METRO_HANDLE = Line2D([], [], marker="o", linestyle="none", markersize=4, markerfacecolor="#111111",
                      markeredgecolor="white", label="Major metro (CBSA)")


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


def state_territories(rows) -> dict:
    """{state: {channel: districts owning a ZCTA filed there}} from (channel, district, state)
    rows, one per owned (ZCTA, fine channel) row or fewer."""
    held = collections.defaultdict(lambda: collections.defaultdict(set))
    for ch, d, s in rows:
        held[s][ch].add(d)
    return {s: {ch: len(ds) for ch, ds in chs.items()} for s, chs in held.items()}


def split_states(counts: dict) -> dict:
    """{channel: sorted states where 2+ of its districts own ZCTAs} from `state_territories`."""
    out = collections.defaultdict(list)
    for s in sorted(counts):
        for ch, n in counts[s].items():
            if n > 1:
                out[ch].append(s)
    return dict(out)


def metro_name(title: str) -> str:
    """'Dallas-Fort Worth-Arlington, TX Metro Area' -> 'Dallas–Fort Worth'; else the first city."""
    cities = title.split(",")[0].split("-")
    return "–".join(cities[:2]) if cities[0] in TWIN and len(cities) > 1 else cities[0]


def top_metros(weight: dict, areas: dict, n: int = METROS) -> list:
    """[(name, lon, lat)] of the `n` Metro Areas with the most `weight` ({cbsa: $}), heaviest
    first; `areas` is {cbsa: (title, lon, lat)}.  Micro Areas, unknown CBSAs and no weight drop."""
    keep = [c for c in weight if weight[c] > 0 and c in areas and areas[c][0].endswith("Metro Area")]
    keep.sort(key=lambda c: (-weight[c], c))
    return [(metro_name(areas[c][0]), areas[c][1], areas[c][2]) for c in keep[:n]]


def read_areas(path: str = AREAS) -> dict:
    """{cbsa: (title, lon, lat)} from `reference/2025/areas.csv.gz` (the gazetteer's points)."""
    import gzip
    with gzip.open(path, "rt", newline="") as fh:
        return {r["geoid"]: (r["name"], float(r["lon"]), float(r["lat"])) for r in csv.DictReader(fh)
                if r["layer"] == "cbsa" and r["lon"] and r["lat"]}


def metros(weight: dict, n: int = METROS) -> list:
    """[(x, y, name)] in `geo.CRS`: `top_metros` on the tracked CBSA points."""
    top = top_metros(weight, read_areas(), n)
    if not top:
        return []
    tr = Transformer.from_crs("EPSG:4326", geo.CRS, always_xy=True)
    xs, ys = tr.transform([t[1] for t in top], [t[2] for t in top])
    return [(x, y, t[0]) for t, x, y in zip(top, xs, ys)]


NEAR = [(4, 2, "left", "bottom"), (-4, 2, "right", "bottom"), (4, -2, "left", "top"),
        (-4, -2, "right", "top"), (0, 5, "center", "bottom"), (0, -5, "center", "top")]
LEADER = [(dx * r, dy * r, "left" if dx > 0 else "right" if dx < 0 else "center",
           "bottom" if dy > 0 else "top" if dy < 0 else "center")
          for r in (1, 1.8, 2.6)
          for dx, dy in ((14, 9), (-14, 9), (14, -9), (-14, -9), (18, 0), (-18, 0), (0, 14), (0, -14))]


def place_labels(ax, items, fs=6.5, avoid=(), marker=True, near=NEAR, leader=LEADER, fits=None,
                 **text) -> list:
    """Set each (x, y, text) of `items` in order (module doc): a dot when `marker`, the label at
    the first offset (points) in `near`, then `leader` with a leader line, whose box overlaps no
    placed label or dot, nor `avoid`'s texts, and stays in the axes; for a `near` offset of
    (0, 0), `fits(i, box)` (the box in data coordinates) must hold too.  An item with no free
    offset is dropped.  The labels placed."""
    from matplotlib.text import Text
    ax.apply_aspect()
    r = ax.figure.canvas.get_renderer()
    frame = ax.get_window_extent(r)
    to_data = ax.transData.inverted()
    taken = [t.get_window_extent(r) for t in avoid]
    x0, x1 = sorted(ax.get_xlim())
    y0, y1 = sorted(ax.get_ylim())
    out = []
    style = dict(fontsize=fs, zorder=9, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")],
                 **text)
    for i, (x, y, s) in enumerate(items):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        dot = None
        if marker:
            px, py = ax.transData.transform((x, y))
            dot = matplotlib.transforms.Bbox.from_extents(px - 3, py - 3, px + 3, py + 3)
            if any(dot.overlaps(o) for o in taken):
                continue
        for k, (dx, dy, ha, va) in enumerate(list(near) + list(leader)):
            arrow = (dict(arrowstyle="-", linewidth=0.5, color="#303030", shrinkA=0, shrinkB=2)
                     if k >= len(near) else None)
            t = ax.annotate(s, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                            arrowprops=arrow, **style)
            t.update_positions(r)
            box = Text.get_window_extent(t, r).expanded(1.04, 1.08)
            ok = (frame.containsx(box.x0) and frame.containsx(box.x1) and frame.containsy(box.y0)
                  and frame.containsy(box.y1) and not any(box.overlaps(o) for o in taken)
                  and not (dot is not None and box.overlaps(dot) and k >= len(near)))
            if ok and fits is not None and (dx, dy) == (0, 0):
                ok = fits(i, matplotlib.transforms.Bbox(to_data.transform(box.get_points())))
            if ok:
                taken.append(box)
                if dot is not None:
                    taken.append(dot)
                    ax.plot([x], [y], "o", markersize=3.2, markerfacecolor="#111111",
                            markeredgecolor="white", markeredgewidth=0.6, zorder=8)
                out.append(t)
                break
            t.remove()
    return out


def label_metros(ax, metro, fs=6.5) -> list:
    """`place_labels` of the metros, around the axes' texts already drawn (district numbers)."""
    return place_labels(ax, metro, fs=fs, avoid=list(ax.texts), style="italic", color="#111111")


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


def page(run_dir, label, ch, ch_rows, polys, st, gap, other, other_names, names, dollars, insets, out_dir, extra,
         metro=()):
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
    label_metros(ax, metro)
    hgt = 0.80 / max(n_in, 1)
    for i, (title, lonlat) in enumerate(insets):
        b = bbox(lonlat)
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False,
                               edgecolor="black", linewidth=1.0, zorder=7))
        ax.text(b[0], b[3], f" {chr(65 + i)}", ha="left", va="bottom", fontsize=9, fontweight="bold", zorder=7)
        iax = fig.add_axes([0.665, 0.12 + 0.80 - (i + 1) * hgt + 0.01, 0.20, hgt - 0.02])
        draw(iax, ch_rows, polys, unions, colour, lines, st, gap, other, b, fs=8)
        iax.set_title(f"{chr(65 + i)}: {title}", fontsize=10)
        label_metros(iax, metro, fs=7.5)
    handles = [Patch(facecolor=colour[d], alpha=0.75, edgecolor="#202020",
                     label=f"{d.rsplit('_', 1)[1]} {names.get(d, d).split(' ', 1)[-1][:30]}")
               for d in sorted(ch_rows)]
    handles.append(Patch(facecolor=UNASSIGNED, edgecolor="none", label=UNASSIGNED_TEXT))
    if metro:
        handles.append(METRO_HANDLE)
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


def count_fill(n: int) -> str:
    """The summary's fill for `n` territories in a state: a light ramp, so labels stay legible."""
    if n <= 0:
        return "white"
    return matplotlib.colors.to_hex(plt.get_cmap("YlGnBu")(0.02 + 0.6 * (min(n, COUNT_BINS) - 1)
                                                         / (COUNT_BINS - 1)))


def state_text(s: str, chs: dict, order: list) -> str:
    """'TX\nN 2 · W 3': the state and each channel's district count there."""
    return s + "\n" + " · ".join(f"{ABBR.get(c, c)} {chs[c]}" for c in order if chs.get(c))


def draw_states(ax, st, counts, order, box, fs, metro, inset=None):
    """One summary map (module doc): fills, split outlines, state labels, metros.  With `inset`
    (a data box), a state in it whose label does not fit inside it is left to the inset."""
    split = {s for s, chs in counts.items() if any(n > 1 for n in chs.values())}
    for s, poly in st.items():
        n = sum(counts.get(s, {}).values())
        ax.add_patch(PathPatch(_polygon_path(poly), facecolor=count_fill(n), edgecolor="#606060",
                               linewidth=0.6, zorder=2))
    for s in sorted(split & set(st)):
        ax.add_patch(PathPatch(_polygon_path(st[s]), facecolor="none", edgecolor=SPLIT_EDGE,
                               linewidth=2.2, zorder=3))
    ax.set_xlim(box[0], box[2])
    ax.set_ylim(box[1], box[3])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    view = shapely.box(*box)
    names = sorted((s for s in st if s in counts and st[s].intersects(view)), key=lambda s: -st[s].area)
    shapes = [st[s].intersection(view) for s in names]
    pts = []
    for s, g in zip(names, shapes):
        part = max(getattr(g, "geoms", [g]), key=lambda p: p.area)
        p = shapely.ops.polylabel(part, tolerance=2000) if part.geom_type == "Polygon" else part.representative_point()
        pts.append((p.x, p.y, state_text(s, counts[s], order)))
    inner = shapely.box(*inset) if inset else None
    placed = place_labels(ax, pts, fs=fs, marker=False, near=[(0, 0, "center", "center")],
                          fits=lambda i, b: shapes[i].buffer(15000).contains(shapely.box(*b.extents)),
                          leader=[x for x in LEADER if x[0] >= 0] + [x for x in LEADER if x[0] < 0],
                          linespacing=1.05, color="#111111")
    for t in placed:                                # a small state inside the inset: the inset's
        s = t.get_text().split("\n")[0]
        if inner is not None and t.arrow_patch is not None and inner.contains(shapely.Point(t.xy)):
            t.remove()
        elif any(n > 1 for n in counts[s].values()):
            t.set_fontweight("bold")
    label_metros(ax, metro, fs=fs - 0.5)


def summary_page(run_dir, label, counts, k, st, metro, out_dir):
    """The summary page (module doc): `counts` from `state_territories`, `k` {channel: districts};
    the figure and `zip_summary.png`."""
    order = [c for c in CHANNELS if c in k] + sorted(c for c in k if c not in CHANNELS)
    fig = plt.figure(figsize=(20, 11.5), dpi=130, facecolor="white")
    ax = fig.add_axes([0.005, 0.12, 0.575, 0.80])
    x0, y0, x1, y1 = shapely.total_bounds(list(st.values()))
    pad = 0.01 * (x1 - x0)
    title, lonlat = NORTHEAST
    b = bbox(lonlat)
    main_box = (x0 - pad, y0 - pad, max(x1, b[2]) + pad, y1 + pad)     # the inset's frame in view
    draw_states(ax, st, counts, order, main_box, 7.5, metro, inset=b)
    ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, edgecolor="black",
                           linewidth=1.0, zorder=7))
    ax.text(b[0], b[3], " B", ha="left", va="bottom", fontsize=9, fontweight="bold", zorder=7)
    iax = fig.add_axes([0.595, 0.12, 0.28, 0.80])
    draw_states(iax, st, counts, order, b, 9, metro)
    iax.set_title(f"B: {title}", fontsize=11)
    for spine in iax.spines.values():
        spine.set_visible(True)
    handles = [Patch(facecolor=count_fill(n), edgecolor="#606060",
                     label=f"{n}{'+' if n == COUNT_BINS else ''} territor{'y' if n == 1 else 'ies'} in the state")
               for n in range(1, COUNT_BINS + 1)]
    handles.append(Patch(facecolor="white", edgecolor=SPLIT_EDGE, linewidth=2.2,
                         label="Split: 2+ districts of one channel"))
    handles += [Patch(facecolor="none", edgecolor="none",
                      label=f"{ABBR.get(c, c)} = {c}: {k[c]} districts") for c in order]
    handles.append(METRO_HANDLE)
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.882, 0.93), fontsize=7.5, frameon=False,
               handlelength=1.4, borderaxespad=0)
    split = split_states(counts)
    total = sum(k.values())
    fig.suptitle(f"{label}  ·  territories per state", fontsize=17, fontweight="bold", y=0.975)
    held = {c: sum(1 for s in counts if counts[s].get(c)) for c in order}
    fig.text(0.01, 0.083, "  ·  ".join(f"{c}: {k[c]} districts in {held[c]} states, {len(split.get(c, []))} split: "
                                        f"{' '.join(split.get(c, [])) or 'none'}" for c in order),
             fontsize=10.5)
    fig.text(0.01, 0.055, f"Fill: territories (districts, all {len(order)} channels, {total} in all) owning a ZCTA "
             "filed in the state; label: each channel's count there, bold where split; dark outline: split "
             "in some channel.  Small states: inset B.", fontsize=8.5, color="#404040")
    fig.text(0.01, 0.030, f"Metros: the top {METROS} CBSA Metro Areas by opportunity \\$ in this run, as room "
             "allows, at their internal points (2025 gazetteer).  Opportunity "
             f"\\$ = m_rel × the owner's channel totals; no sales data.  Run: {os.path.relpath(run_dir, TD_REPO)}",
             fontsize=8.5, color="#404040")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "zip_summary.png")
    fig.savefig(path, dpi=130, facecolor="white")
    return fig, path


def geometry(cache: str = CACHE) -> tuple:
    """(ZCTA polygons, state shapes, no-ZCTA land), each pickled in `cache` (`zcta_polys.pkl`,
    `states.pkl`, `no_zcta_land.pkl`) and built on a miss; the summary page reads the first two
    (`tools/maps/summary.py`)."""
    public = os.path.join(TD_REPO, "data", "public")
    polys = cached("zcta_polys.pkl", lambda: zcta_polygons(all_zctas(), public), cache)
    st = cached("states.pkl", lambda: states(cache), cache)
    gap = cached("no_zcta_land.pkl", lambda: no_zcta_land(polys, st), cache)
    return polys, st, gap


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
    polys, st, gap = geometry(a.cache)
    with open(os.path.join(a.run_dir, "districts.csv"), newline="") as fh:
        names = {r["district"]: r["district_name"] for r in csv.DictReader(fh)}
    owned = collections.defaultdict(lambda: collections.defaultdict(set))
    usd = collections.defaultdict(collections.Counter)
    by_cbsa = collections.Counter()
    filed = set()
    with open(os.path.join(a.run_dir, "ledger.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if not r["district"]:
                continue
            owned[r["model_channel"]][r["district"]].add(r["zip_code"])
            filed.add((r["model_channel"], r["district"], r["state"]))
            m = float(r["m_rel"])
            if m > 0:
                usd[r["model_channel"]][r["district"]] += m * FAC[r["current_channel"]]
                if r.get("cbsa"):
                    by_cbsa[r["cbsa"]] += m * FAC[r["current_channel"]]
    zst = {}
    with open(os.path.join(a.run_dir, "ledger.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            zst[r["zip_code"]] = r["state"]
    insets = [NYC] + ([CORRIDOR] if a.corridor else [])
    metro = metros(by_cbsa)
    counts = state_territories(filed)
    fig, path = summary_page(a.run_dir, a.label, counts, {c: len(owned[c]) for c in owned}, st, metro,
                             a.out_dir)
    plt.close(fig)
    written = [path]
    print(f"summary: {len(counts)} states, {sum(map(len, split_states(counts).values()))} (state, channel) "
          f"splits, {len(metro)} metros -> {path}", flush=True)
    for ch in sorted(owned, key=CHANNELS.index):
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
                         {d: usd[ch][d] for d in rows}, insets, a.out_dir, extra, metro)
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
