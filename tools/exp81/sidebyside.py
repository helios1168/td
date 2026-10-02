"""sidebyside.py -- two run directories' maps side by side, one PNG per channel (experimental, td#81).

    "$TD_PY" tools/exp81/sidebyside.py <run_dir_left> <run_dir_right> --out <dir>
        [--labels "support diameter" "Hess"]

Each panel is drawn as `td.output.draw_maps` draws a channel's map, from the ledger file only:
TIGER/Line 2025 ZCTA520 polygons in EPSG:5070 simplified by `output.SIMPLIFY_M`, filled by
district with the same palette rule (tab20, tab20b, tab20c in sorted district order), over the
2025 state outlines, with the principal cities of the channel's `output.TOP_METROS` largest
metros.  Two changes fit two panels on one figure: both panels share the extent of the union of
their ZCTAs, and each legend sits below its panel.  The ZCTA file is read in batches of 500,
because GDAL rejects one 6,623-item IN list (`runs/sweep/looks_2026-10-01/run3.py`).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data, geo, output                # noqa: E402

HUB = os.environ.get("TD_REPO", ROOT)
BATCH = 500


def zcta_polygons(zips, public: str) -> dict:
    """`output.zcta_polygons`, read `BATCH` ZCTAs at a time."""
    path = output.zcta_file(public)
    if path is None:
        raise output.RunError(f"{output.MAPS_SKIPPED}: no {output.ZCTA_FILE} in {public}")
    zs = sorted(z for z in set(zips) if re.fullmatch(r"\d{5}", z))
    out = {}
    for i in range(0, len(zs), BATCH):
        df = geo._read(path, ["ZCTA5CE20"],
                       where=f"ZCTA5CE20 IN ({','.join(repr(z) for z in zs[i:i + BATCH])})")
        out.update({z: poly.simplify(output.SIMPLIFY_M, preserve_topology=True)
                    for z, poly in zip(df["ZCTA5CE20"], df.geometry)})
    return out


def read_drawn(run_dir: str):
    import pandas as pd
    led = pd.read_csv(os.path.join(run_dir, "ledger.csv"), dtype=str, keep_default_na=False)
    return led[led["district"] != ""].drop_duplicates(["model_channel", "zip_code"])


def draw_panel(ax, g, label: str, polys: dict, outlines: list, context: dict, top: int) -> list:
    """One channel of one run on `ax`, as `output.draw_maps` draws it; the polygons drawn."""
    import matplotlib.patheffects as pe
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Patch, PathPatch
    for poly in outlines:
        for part in getattr(poly, "geoms", [poly]):
            ax.plot(*part.exterior.xy, color="0.75", linewidth=0.4, zorder=1)
    colors = [c for m in ("tab20", "tab20b", "tab20c") for c in plt.get_cmap(m).colors]
    districts = sorted(g["district"].unique())
    drawn, handles = [], []
    for i, j in enumerate(districts):
        sel = g[g["district"] == j]
        shapes = [polys[z] for z in sel["zip_code"] if z in polys]
        color = colors[i % len(colors)]
        ax.add_collection(PatchCollection([PathPatch(output._polygon_path(p)) for p in shapes],
                                          facecolor=color, edgecolor=color, linewidth=0.2, zorder=2))
        handles.append(Patch(facecolor=color, label=f"{j} {sel['district_name'].iloc[0]}"))
        drawn += shapes
    pop, titles, places = context["pop"], context["titles"], context["places"]
    metros = sorted((code for code in set(g["cbsa"]) - {""}),
                    key=lambda code: (-pop.get(code, 0.0), code))[:top]
    for code in metros:
        for city, px, py in output.principal_cities(titles.get(code, ""), places):
            ax.plot(px, py, "k.", markersize=3, zorder=3)
            ax.annotate(city, (px, py), xytext=(3, 3), textcoords="offset points", fontsize=7,
                        zorder=4, path_effects=[pe.withStroke(linewidth=2, foreground="white")])
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{label}\n{g['scenario'].iloc[0]}: {g['model_channel'].iloc[0]}, "
                 f"{len(districts)} districts")
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=6,
              frameon=False)
    return drawn


def sidebyside(left: str, right: str, out_dir: str, labels=None, public: str | None = None,
               top: int = output.TOP_METROS) -> dict:
    """{channel: png path} for every channel either run draws."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    public = public or os.path.join(HUB, "data", "public")
    labels = labels or [os.path.basename(os.path.normpath(left)),
                        os.path.basename(os.path.normpath(right))]
    runs = [read_drawn(left), read_drawn(right)]
    polys = zcta_polygons(set(runs[0]["zip_code"]) | set(runs[1]["zip_code"]), public)
    ref, areas = geo.read_reference(), output.read_areas()
    context = {"titles": output.cbsa_titles(areas), "pop": output.cbsa_population(ref),
               "places": output._places(areas, ref)}
    outlines = []
    path = os.path.join(public, "tl_2025_us_state.zip")
    if os.path.exists(path) and geo._valid_download(path):
        outlines = list(data.state_polygons(public).values())
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    channels = sorted(set(runs[0]["model_channel"]) | set(runs[1]["model_channel"]))
    output.check_file_names("planning channel", channels)
    for c in channels:
        fig, axes = plt.subplots(1, 2, figsize=(22, 9))
        drawn = []
        for ax, led, label in zip(axes, runs, labels):
            g = led[led["model_channel"] == c]
            if len(g):
                drawn += draw_panel(ax, g, label, polys, outlines, context, top)
            else:
                ax.set_axis_off()
                ax.set_title(f"{label}\nno {c} districts")
        if drawn:
            x0, y0, x1, y1 = shapely.total_bounds(drawn)
            pad = 0.03 * max(x1 - x0, y1 - y0, 1.0)
            for ax in axes:
                ax.set_xlim(x0 - pad, x1 + pad)
                ax.set_ylim(y0 - pad, y1 + pad)
        out[c] = output.inside(out_dir, os.path.join(out_dir, f"{c}.png"))
        fig.savefig(out[c], dpi=120, bbox_inches="tight")
        plt.close(fig)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--out", required=True, help="the directory for <channel>.png")
    ap.add_argument("--labels", nargs=2, metavar=("LEFT", "RIGHT"),
                    help="panel labels (default: the run directories' names)")
    ap.add_argument("--public", help="the 2025 downloads (default: $TD_REPO/data/public)")
    a = ap.parse_args(argv)
    for c, p in sidebyside(a.left, a.right, a.out, a.labels, a.public).items():
        print(f"{c}: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
