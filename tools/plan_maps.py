"""plan_maps.py: a realised `tools/full_plan.py` run -> one map per channel and a metrics row.

    .venv/bin/python3 tools/plan_maps.py battery/results/full_problem/v3_seq_warm \\
        --geo-cache /Users/ntlee/projects/td/data/geo

The step a reviewer needs after `tools/plan_realise.py`: the labels are already on disk in
`assignment.csv`, and what nobody can rank from a CSV is whether a district is a territory or a
scatter.

**One panel per business channel**, never per bundle: `maps/national.png`, `maps/wh.png`,
`maps/fi.png`, and `maps/all.png` with the three side by side.  A channel is what the business
sells and a bundle is how the plan chose to carry it, so the panel answers "who covers this
channel here" and the bundle shows up as a fill style on it:

    solid        a pure bundle (N, WH, FI): this channel and nothing else
    diagonal     a plus bundle (WH_PLUS, FI_PLUS): it carries a national channel too
    cross        a merged bundle (WHFI, WHFI_PLUS): one district on both WH and FI

A merged district is therefore drawn on the WH panel and on the FI panel, in the same colour
and under the same id.  Zips of the channel in no district are light grey.

The fill is each zip's Voronoi catchment, dissolved by district and clipped to its own state
(`tools/us_maps.py`'s own machinery).  Trap 23 applies to how it is read: that tessellation is
the contiguity model's graph, not the ZCTA polygons the app draws.

`maps/metrics.csv` stays one row per district, carrying its bundle, the fine channels it
carries, and the shape numbers the picture shows.  `extent_km` is measured between *state*
centroids, the same coordinates `tools/full_plan.py::_state_xy` caps with `--dist-max`, so a
plan run under a cap can be checked against it directly; the hull columns are measured over the
district's zip points instead, so a district that fills its states and one that holds a corner
of each are not scored alike.

Nothing here reads a projection instance: `assignment.csv` already carries `M_cell`, the mass
of one (zip, channel) cell, and it sums per district to exactly what `districts.csv` reports.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channels, geo, ziptable                                    # noqa: E402
import run_draw                                                           # noqa: E402
import us_maps                                                            # noqa: E402

OTHER = "other"                 # `tools/plan_realise.py::OTHER`, the no-district pseudo-label
NONE = "(none)"                 # the grey region: zips of the channel no district holds
PANELS = channels.FILE_CHANNELS                              # national, wh, fi
PANEL_TITLE = {"national": "national", "wh": "WH", "fi": "FI"}

GREY = "#dcdcdc"
HATCH = {"pure": "", "plus": "///", "merged": "xxx"}
HATCH_TEXT = {"pure": "pure bundle", "plus": "plus a national channel",
              "merged": "merged WH + FI"}

COLUMNS = ("bundle", "channels", "district", "n_states", "n_zips", "mass", "extent_km",
           "hull_area_km2", "hull_perimeter_km", "mass_per_hull_area", "pieces", "wholesaler")


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="a finished plan run, already realised")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--bundles", default=None,
                    help="comma-separated subset of the run's bundles; the districts of every "
                         "other bundle are left off the panels")
    ap.add_argument("--dpi", type=int, default=110,
                    help="dpi of maps/all.png (default 110); the per-channel figures are drawn "
                         "at tools/us_maps.py's own DPI, which no caller may set")
    return ap


# ------------------------------------------------------------------------------- reading a run
def read_assignment(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def district_meta(path: str) -> dict:
    """`{district: row}` from `districts.csv`, or `{}` when the run has no such file."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {row["district"]: row for row in csv.DictReader(fh)}


def fill_class(bundle: str) -> str:
    """`pure` / `plus` / `merged`: the fill style the bundle earns on a channel panel."""
    chans = set(channels.BUNDLES.get(bundle, ()))
    if {"WH", "FI"} <= chans:
        return "merged"
    if chans & {"N_WH", "N_FI"} and chans & {"WH", "FI"}:
        return "plus"
    return "pure"


def by_panel(rows: list[dict]) -> dict:
    """`{file_channel: {zip: district}}`; `other` reads as unplaced, which draws grey.

    One district per (channel, zip) is the invariant `tools/plan_realise.py` writes, so the
    first row per pair speaks for it and a later one is ignored rather than silently winning.
    """
    out: dict[str, dict] = {c: {} for c in PANELS}
    for row in rows:
        panel = out.setdefault(row["file_channel"], {})
        if row["zip"] in panel:
            continue
        panel[row["zip"]] = "" if row["district"] == OTHER else row["district"]
    return out


def district_table(rows: list[dict]) -> dict:
    """`{district: {bundle, channels, panels, zips, states, mass}}` from `assignment.csv`."""
    out: dict[str, dict] = {}
    for row in rows:
        if row["district"] == OTHER:
            continue
        rec = out.setdefault(row["district"], dict(
            bundle=row["bundle"], channels=set(), panels=set(), zips=set(), states=set(),
            mass=0.0))
        rec["channels"].add(row["channel"])
        rec["panels"].add(row["file_channel"])
        rec["zips"].add(row["zip"])
        if row.get("state"):
            rec["states"].add(row["state"])
        rec["mass"] += float(row["M_cell"] or 0.0)
    return out


# ------------------------------------------------------------------------------------- metrics
def extent_km(states: set, polys: dict) -> float:
    """Max pairwise distance between the district's state centroids, in km.

    `--dist-max` is a cap on exactly this quantity, so a plan drawn under one is checked
    against its own number rather than a differently measured proxy.
    """
    pts = [(polys[s].centroid.x / 1000.0, polys[s].centroid.y / 1000.0)
           for s in sorted(states) if s in polys]
    worst = 0.0
    for i, (ax, ay) in enumerate(pts):
        for bx, by in pts[i + 1:]:
            worst = max(worst, ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5)
    return worst


def hull(points: list) -> tuple[float, float]:
    """`(area km2, perimeter km)` of the convex hull of LAEA points; `(0, 0)` under 3 points."""
    import shapely

    if len(points) < 3:
        return 0.0, 0.0
    h = shapely.MultiPoint(points).convex_hull
    return float(h.area) / 1e6, float(h.length) / 1000.0


def metrics(table: dict, meta: dict, xy: dict, state_polys: dict) -> list[dict]:
    """One record per district, in district order."""
    out = []
    for district in sorted(table):
        rec = table[district]
        row = meta.get(district) or {}
        pts = [xy[z] for z in sorted(rec["zips"]) if z in xy]
        area, perim = hull(pts)
        mass = rec["mass"]
        fine = [c for c in channels.CHANNELS if c in rec["channels"]]
        out.append(dict(
            bundle=rec["bundle"], channels=",".join(fine), district=district,
            n_states=len(rec["states"]), n_zips=len(rec["zips"]), mass=round(mass, 6),
            extent_km=round(extent_km(rec["states"], state_polys), 1),
            hull_area_km2=round(area, 1), hull_perimeter_km=round(perim, 1),
            mass_per_hull_area=(round(mass / area, 8) if area > 0 else ""),
            pieces=row.get("pieces", ""), wholesaler=row.get("wholesaler", "")))
    return out


def write_metrics(path: str, records: list[dict]) -> str:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(COLUMNS))
        w.writeheader()
        w.writerows(records)
    return path


# ------------------------------------------------------------------------------------- drawing
def label_of(district: str, meta: dict) -> str:
    """The drawn label: the district id, the wholesaler under it when one is known."""
    wh = (meta.get(district) or {}).get("wholesaler") or ""
    return f"{district}\n{wh}" if wh else district


def geometry(region_of: dict, xy: dict, states, zip_state: dict) -> dict:
    """The panel's Voronoi tessellation, dissolved by district (unplaced zips into `NONE`)."""
    keys = [z for z in sorted(region_of) if z in xy]
    if len(keys) < 2:
        return dict(keys=keys, clip=None, cells={}, polys={})
    clip = us_maps.clip_region([xy[z] for z in keys], states)
    state_polys = None if states is None else dict(zip(states["STUSPS"], states.geometry))
    cells = us_maps.voronoi_cells(keys, xy, clip, zip_state=zip_state,
                                  state_polys=state_polys)
    polys = us_maps.dissolve(cells, {z: (region_of[z] or NONE) for z in cells})
    return dict(keys=keys, clip=clip, cells=cells, polys=polys)


def hatch_legend(ax, fontsize: int = 7) -> None:
    """The one convention a reader cannot guess: what a hatched district means."""
    from matplotlib.patches import Patch

    handles = [Patch(facecolor="#bbbbbb", edgecolor=us_maps.BORDER, hatch=HATCH[k],
                     label=HATCH_TEXT[k]) for k in ("pure", "plus", "merged")]
    handles.append(Patch(facecolor=GREY, edgecolor=us_maps.BORDER, label="no district"))
    ax.legend(handles=handles, loc="lower left", fontsize=fontsize, frameon=False,
              handlelength=2.2, borderaxespad=0.0)


def draw_panel(fig, ax, geom: dict, region_of: dict, colors: dict, table: dict, meta: dict,
               states, *, fontsize: int = 8, state_w: float = ziptable.STATE_W,
               label: bool = True) -> None:
    """One channel's panel onto `ax`: fills, hatches, the zip lattice, borders, labels."""
    from matplotlib.collections import LineCollection
    from matplotlib.patches import PathPatch

    ax.set_facecolor(us_maps.BG)
    ax.set_aspect("equal")
    ax.set_axis_off()
    polys = geom["polys"]
    if not polys:
        return

    for district in sorted(polys, key=str):
        g = polys[district]
        grey = district == NONE
        face = GREY if grey else colors.get(district, GREY)
        klass = "pure" if grey else fill_class((table.get(district) or {}).get("bundle", ""))
        for path in us_maps._poly_paths(g):
            ax.add_patch(PathPatch(path, facecolor=face, edgecolor="none",
                                   alpha=0.35 if grey else us_maps.REGION_ALPHA, zorder=1))
            if HATCH[klass]:
                ax.add_patch(PathPatch(path, facecolor="none", edgecolor=us_maps.BORDER,
                                       hatch=HATCH[klass], linewidth=0.0, alpha=0.55,
                                       zorder=1.5))

    lattice = [seg for g in geom["cells"].values() for seg in us_maps._lines_of(g.boundary)]
    ax.add_collection(LineCollection(lattice, colors=us_maps.CELL_EDGE,
                                     linewidths=us_maps.CELL_EDGE_W,
                                     alpha=us_maps.CELL_EDGE_ALPHA, zorder=2))
    x0, y0, x1, y1 = geom["clip"].bounds
    eps = 1e-4 * float((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    real = {d: g for d, g in polys.items() if d != NONE}
    ax.add_collection(LineCollection(us_maps.district_borders(real, eps),
                                     colors=us_maps.BORDER, linewidths=us_maps.BORDER_W,
                                     capstyle="round", joinstyle="round", zorder=3))
    if states is not None:
        # heavy and dark, `td.ziptable`'s own settings: every cell is clipped to its state, so
        # the state line is where a reader checks the fill against the border
        states.boundary.plot(ax=ax, color=ziptable.STATE_COLOR, linewidth=state_w, zorder=4)

    mx, my = 0.02 * (x1 - x0), 0.02 * (y1 - y0)
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y0 - my, y1 + my)

    if label and real:
        order = sorted(real, key=str)
        # a point inside the district's own largest part, which `label_points` then refines
        centroids = {d: us_maps._largest_part(g).representative_point().coords[0]
                     for d, g in real.items()}
        anchors = us_maps.label_points(order, real, centroids, us_maps.LABEL_SEP * (x1 - x0))
        footprint = {d: us_maps._largest_part(g).area for d, g in real.items()}
        # the wholesaler rides under the district id, so the drawn name is the label itself
        names = {d: label_of(d, meta) for d in order}
        us_maps._place_labels(fig, ax, [names[d] for d in order],
                              {names[d]: anchors[d] for d in order if d in anchors},
                              {names[d]: footprint[d] for d in order}, fontsize=fontsize,
                              avoid_polys={names[d]: real[d] for d in order},
                              land=geom["clip"])


def panel_figure(geom: dict, region_of: dict, values: dict, colors: dict, table: dict,
                 meta: dict, states, out_png: str) -> str:
    """One channel's own figure, with the share-of-M legend `tools/us_maps.py` draws."""
    drawn = {z: d for z, d in region_of.items() if d}
    channel = geom["channel"]
    order = sorted(set(drawn.values()), key=str)
    title = f"{PANEL_TITLE.get(channel, channel)} channel — {len(order)} districts"
    subtitle = ("fill = the Voronoi catchment of each ZIP, clipped to its own state  ·  "
                "hatch = the bundle the district carries\ncolours and ids are shared across "
                "the three panels  ·  grey = this channel served by no district")
    fig, ax = us_maps._canvas(None, title, subtitle)
    draw_panel(fig, ax, geom, region_of, colors, table, meta, states)
    hatch_legend(ax)
    us_maps._district_legend(fig, drawn, values, colors, order)
    return us_maps._save(fig, out_png)


def overview(geoms: list, panels: dict, colors: dict, table: dict, meta: dict, states,
             out_png: str, dpi: int) -> str:
    """`all.png`: the channel panels side by side, one hatch legend on the first."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = max(len(geoms), 1)
    fig, axes = plt.subplots(1, n, figsize=(7.0 * n, 5.2), dpi=dpi, facecolor=us_maps.BG)
    axes = list(axes) if n > 1 else [axes]
    for ax, geom in zip(axes, geoms):
        channel = geom["channel"]
        region_of = panels[channel]
        draw_panel(fig, ax, geom, region_of, colors, table, meta, states, fontsize=6,
                   state_w=0.8)
        ax.set_title(f"{PANEL_TITLE.get(channel, channel)} — "
                     f"{len({d for d in region_of.values() if d})} districts",
                     color=us_maps.TEXT, fontsize=12)
    hatch_legend(axes[0], fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=dpi, facecolor=us_maps.BG)
    plt.close(fig)
    return out_png


# ---------------------------------------------------------------------------------- the driver
def _main(args) -> int:
    run_dir = os.path.abspath(args.run_dir)
    rows = read_assignment(os.path.join(run_dir, "assignment.csv"))
    meta = district_meta(os.path.join(run_dir, "districts.csv"))
    table = district_table(rows)

    if args.bundles:
        want = [b.strip() for b in args.bundles.split(",") if b.strip()]
        have = sorted({r["bundle"] for r in table.values()})
        unknown = [b for b in want if b not in have]
        if unknown:
            raise SystemExit(f"--bundles names {unknown}, not among the run's {have}")
        table = {d: r for d, r in table.items() if r["bundle"] in want}

    panels = {c: {z: (d if d in table else "") for z, d in p.items()}
              for c, p in by_panel(rows).items() if p}
    order = [c for c in PANELS if c in panels] + [c for c in panels if c not in PANELS]
    if not order:
        raise SystemExit(f"{run_dir}: assignment.csv carries no channel rows")

    zips = sorted({r["zip"] for r in rows})
    xy, missing = run_draw.coordinates(zips, args.geo_cache)
    zip_state = {r["zip"]: r["state"] for r in rows if r.get("state")}
    states = geo.states_outline(args.geo_cache)
    _, state_polys = geo.state_rook(args.geo_cache)

    # the mass of one (channel, zip) cell: what the share-of-M legend reports and what the
    # colouring weights a district's centroid by
    values: dict[str, dict] = {c: {} for c in order}
    for row in rows:
        cell = values.setdefault(row["file_channel"], {})
        cell[row["zip"]] = cell.get(row["zip"], 0.0) + float(row["M_cell"] or 0.0)

    # one colouring over every district of every panel, so a merged district keeps its hue on
    # both of its panels and two different districts drawn at the same place never share one
    keyed = {(c, z): d for c in order for z, d in panels[c].items() if d}
    keyed_xy = {k: xy[k[1]] for k in keyed if k[1] in xy}
    keyed_values = {k: values[k[0]].get(k[1], 0.0) for k in keyed}
    _, _, colors = us_maps.draw_palette(keyed, keyed_values, keyed_xy)

    out_dir = os.path.join(run_dir, "maps")
    os.makedirs(out_dir, exist_ok=True)
    geoms = []
    for channel in order:
        geom = geometry(panels[channel], xy, states, zip_state)
        geom["channel"] = channel
        geoms.append(geom)
        png = panel_figure(geom, panels[channel], values[channel], colors, table, meta,
                           states, os.path.join(out_dir, f"{channel}.png"))
        held = {d for d in panels[channel].values() if d}
        print(f"{channel}: {len(held)} districts, {len(panels[channel])} zips, "
              f"{sum(1 for d in panels[channel].values() if not d)} unplaced -> {png}",
              flush=True)
    if missing:
        print(f"{len(missing)} zip(s) have no gazetteer point and are not drawn", flush=True)

    overview(geoms, panels, colors, table, meta, states,
             os.path.join(out_dir, "all.png"), args.dpi)
    records = metrics(table, meta, xy, state_polys)
    path = write_metrics(os.path.join(out_dir, "metrics.csv"), records)
    print(f"wrote {path} ({len(records)} districts) and {os.path.join(out_dir, 'all.png')}",
          flush=True)
    return 0


def main(argv=None) -> int:
    return _main(build_argparser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
