"""plan_render_app.py: one map exactly as the Streamlit app draws it, written to a PNG.

    .venv-app/bin/python3 tools/plan_render_app.py --rows draw.csv --geom geom.json \\
        --out map.png [--labels labels.json] [--title "WH only"]

Runs under the app's own virtualenv (`.venv-app`, which carries plotly and kaleido), never the
solver's: it imports `app/mapfig.py` and calls the same `figure` the app calls, so the PNG is
the app's map and not a reproduction of it.  `tools/plan_summary.py` runs it by subprocess for
each bundle of a plan and tiles the PNGs.

Inputs are the app's own: a zip table with the columns `mapfig.load_rows` reads (zip, state,
district, rep, x, y, opportunity) and a `geom.json` from `tools/geom_export.py`.  `--labels` is
a JSON `{district: {"x": ..., "y": ..., "text": ...}}` of label anchors in the table's
coordinates; the app itself labels nothing but the states (a district's name is its hover), so
a static map takes the labels from the caller, which has the geometry to place them with.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import mapfig                                                    # noqa: E402

WIDTH, HEIGHT, SCALE = 1600, 1000, 2
LABEL_FONT = 13


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", required=True, help="the zip table (draw.csv shape)")
    ap.add_argument("--geom", required=True, help="geom.json for that table")
    ap.add_argument("--out", required=True, help="the PNG to write")
    ap.add_argument("--labels", default=None, help="JSON of {district: {x, y, text}}")
    ap.add_argument("--title", default="")
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--height", type=int, default=HEIGHT)
    ap.add_argument("--scale", type=float, default=SCALE)
    return ap


def render(rows: list, geom: dict, labels: dict | None, title: str, *, width: int = WIDTH,
           height: int = HEIGHT):
    """The app's figure for `rows` and `geom`, with the caller's labels on top and the
    interactive furniture (legend, hover margins) taken off."""
    fig = mapfig.figure(rows, geom)
    for district, spot in sorted((labels or {}).items()):
        fig.add_annotation(x=spot["x"], y=spot["y"], text=spot["text"].replace("\n", "<br>"),
                           showarrow=False, align="center",
                           font=dict(size=LABEL_FONT, color="#1f1f1f", family="Arial"),
                           bgcolor="rgba(255,255,255,0.85)", bordercolor="#9a9a9a",
                           borderwidth=0.6, borderpad=3)
    fig.update_layout(width=width, height=height, showlegend=False,
                      margin=dict(l=4, r=4, t=44 if title else 4, b=4),
                      paper_bgcolor="white",
                      title=dict(text=title, x=0.5, xanchor="center", y=0.985,
                                 font=dict(size=22, color="#222222")) if title else None)
    return fig


def _main(args) -> int:
    rows = mapfig.load_rows(Path(args.rows))
    geom = mapfig.load_geom(Path(args.geom))
    labels = None
    if args.labels:
        with open(args.labels, encoding="utf-8") as fh:
            labels = json.load(fh)
    fig = render(rows, geom, labels, args.title, width=args.width, height=args.height)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    fig.write_image(args.out, scale=args.scale)
    print(f"wrote {args.out}", flush=True)
    return 0


def main(argv=None) -> int:
    return _main(build_argparser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
