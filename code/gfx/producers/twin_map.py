"""
gfx/producers/twin_map.py -- the twin-instance map figure (PLAN.md Part D).

`twin_instance.json.gz` (PLAN.md C.2) carries `meta`, columnar `nodes{z, state, A, B, M,
rep_a, rep_b}` and `edges{u, v}` (node ids, not indices -- unlike the compact per-pair
`schemas.py` instance JSON). It does not itself carry positions or TIGER polygons; U4's
`battery/code/twin.py::load_twin` is what joins those in from `data/zcta_adjacency.npz`
and the TIGER shapefile. Until that lands, this producer accepts positions embedded at
`nodes.pos` (a stand-in the fixture supplies) and falls back to `geom.polys_from_pos`;
pass `--shapes <path>` (anything `geopandas.read_file` opens, indexed by zip id) once
real TIGER geometry is available to use `geom.polys_from_shapes` instead -- no code
change needed, just the flag.

Panels: national M heatmap · rep territories A and B · a zoomed pair with adjacency
(`--pair rep_a,rep_b`; auto-picks the largest 200-800-zip pair if omitted).

Usage:
    python -m gfx.producers.twin_map <twin_instance.json[.gz]> --out <png> [--shapes <path>]
    [--pair rep_a,rep_b]
"""
from __future__ import annotations

import sys
from collections import Counter

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .. import geom, maps, style
from . import _common


def _rep_choropleth(ax, zs, polys, bounds, rep_of, title):
    reps = sorted(set(rep_of.values()))
    idx = {r: i for i, r in enumerate(reps)}
    maps.choropleth(ax, polys, lambda z: style.rep_color(idx[rep_of[z]]), bounds=bounds,
                    title=title, legend=None)


def _pick_pair(rep_a, rep_b, target=(200, 800)):
    counts = Counter(zip(rep_a, rep_b))
    in_band = {k: v for k, v in counts.items() if target[0] <= v <= target[1]}
    if in_band:
        return max(in_band, key=in_band.get)
    return max(counts, key=counts.get)


def build(twin: dict, shapes=None, pair: tuple | None = None) -> plt.Figure:
    style.use_rc()
    nodes = twin["nodes"]
    zs = list(nodes["z"])
    M = dict(zip(zs, nodes["M"]))
    style.use_rc()
    fig, axes = plt.subplots(2, 2, figsize=style.FIGSIZE["card"])

    if shapes is not None:
        polys, bounds = geom.polys_from_shapes(shapes)
    else:
        pos = nodes.get("pos")
        if pos is None:
            raise ValueError("twin instance has no nodes.pos and no --shapes given; "
                             "load_twin (U4) or the stand-in fixture must supply one")
        polys, bounds = geom.polys_from_pos(zs, pos)

    maps.heatmap(axes[0, 0], polys, M, bounds=bounds, cmap=style.PALETTE["cmap_M"],
                title="national M", cbar_label="opportunity")

    rep_a, rep_b = nodes.get("rep_a"), nodes.get("rep_b")
    if rep_a and rep_b:
        _rep_choropleth(axes[0, 1], zs, polys, bounds, dict(zip(zs, rep_a)),
                        "firm-A territories")
        _rep_choropleth(axes[1, 0], zs, polys, bounds, dict(zip(zs, rep_b)),
                        "firm-B territories")
    else:
        for ax, lab in ((axes[0, 1], "A"), (axes[1, 0], "B")):
            ax.axis("off")
            ax.text(0.5, 0.5, f"no nodes.rep_{lab.lower()} in this instance",
                    ha="center", va="center", fontsize=8, transform=ax.transAxes)

    ax = axes[1, 1]
    if rep_a and rep_b:
        ra, rb = pair if pair else _pick_pair(rep_a, rep_b)
        sub = [z for z, a, b in zip(zs, rep_a, rep_b) if a == ra or b == rb]
        pos_map = dict(zip(zs, nodes.get("pos") or []))
        u, v = twin.get("edges", {}).get("u", []), twin.get("edges", {}).get("v", [])
        subset = set(sub)
        induced = [(a, b) for a, b in zip(u, v) if a in subset and b in subset]
        sub_polys, sub_bounds = geom.polys_from_pos(sub, [pos_map[z] for z in sub])
        side_of = dict(zip(zs, rep_a))
        maps.choropleth(ax, sub_polys,
                        lambda z: style.PALETTE["A"] if side_of[z] == ra else style.PALETTE["B"],
                        bounds=sub_bounds, title=f"pair {ra}/{rb} (n={len(sub)}), zoomed",
                        legend=[Line2D([], [], marker="s", ls="", color=style.PALETTE["A"], label=str(ra)),
                               Line2D([], [], marker="s", ls="", color=style.PALETTE["B"], label=str(rb))])
        maps.adjacency(ax, geom.edge_segments(induced, pos_map))
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "no rep_a/rep_b: cannot select a pair", ha="center", va="center",
                fontsize=8, transform=ax.transAxes)

    fig.suptitle((twin.get("meta") or {}).get("graph_hash", "twin instance"), fontsize=10)
    style.tight_layout(fig)
    return fig


def main(argv=None):
    p = _common.base_parser(__doc__)
    p.add_argument("twin_instance_json")
    p.add_argument("--shapes", default=None)
    p.add_argument("--pair", default=None, help="rep_a,rep_b")
    args = p.parse_args(argv)
    twin = _common.load_json(args.twin_instance_json)
    shapes = None
    if args.shapes:
        import geopandas as gpd
        shapes = gpd.read_file(args.shapes)
    pair = tuple(args.pair.split(",")) if args.pair else None
    fig = build(twin, shapes, pair)
    style.check_text_overlap(fig)
    style.save(fig, args.out, inputs=[args.twin_instance_json], producer="twin_map")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
