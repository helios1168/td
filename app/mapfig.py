"""The interactive map: one plotly figure from a zip table plus polygons.

Coordinates are LAEA metres straight out of the zip table, drawn on cartesian axes with
`scaleanchor`, so nothing here projects or unprojects anything.  There are no map tiles: a
tiled basemap would need geographic coordinates, and the inverse projection does not exist in
this repo.  Equal aspect on the two axes is what makes the shapes read as a US map.

The trace order is a contract with `main.py`, which reads a selection event back by matching
`curve_number` against the trace names below.  Outlines and polygons skip hover so a click
always lands on a zip or a state handle, never on the fill under them.

The figure is not cached here.  Caching is `st.cache_data` in `main.py`, keyed on path and
mtime, because this module knows nothing about streamlit and stays importable from a plain
python.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import plotly.graph_objects as go

OUTLINES = "state outlines"
ZIPS = "zips"
HANDLES = "state handles"

# Fallback only, for a table whose polygons have not been built yet.  Once `geom.json` exists
# its own colours win, because they are the ones assigned so that neighbours differ.
PALETTE = [
    "#4269d0", "#efb118", "#ff725c", "#6cc5b0", "#3ca951", "#ff8ab7", "#a463f2", "#97bbf5",
    "#9c6b4e", "#9498a0", "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#8c564b", "#e377c2",
    "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8",
]

MIN_PX, MAX_PX = 3.0, 14.0


def load_rows(path: Path) -> list[dict]:
    """The zip table as plain dicts. x, y and opportunity are floats, or None when blank."""
    with open(path, newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in ("x", "y", "opportunity"):
            value = (row.get(field) or "").strip()
            row[field] = float(value) if value else None
        row["rep"] = (row.get("rep") or "").strip()
    return rows


def load_geom(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _colours(rows: list[dict], geom: dict | None) -> dict[str, str]:
    districts = sorted({row["district"] for row in rows if row.get("district")})
    if geom:
        from_geom = {d: info.get("color") for d, info in geom.get("districts", {}).items()}
        if all(from_geom.get(d) for d in districts):
            return {d: from_geom[d] for d in districts}
    return {d: PALETTE[i % len(PALETTE)] for i, d in enumerate(districts)}


def _sizes(rows: list[dict]) -> list[float]:
    """Marker area proportional to opportunity, so radius goes as its square root."""
    roots = [math.sqrt(row["opportunity"]) for row in rows if row["opportunity"]]
    if not roots:
        return [MIN_PX] * len(rows)
    lo, hi = min(roots), max(roots)
    span = hi - lo
    out = []
    for row in rows:
        if not row["opportunity"]:
            out.append(MIN_PX)
        elif span <= 0:
            out.append((MIN_PX + MAX_PX) / 2)
        else:
            out.append(MIN_PX + (MAX_PX - MIN_PX) * (math.sqrt(row["opportunity"]) - lo) / span)
    return out


def _joined(rings: list[list[list[float]]]) -> tuple[list, list]:
    """Several rings as one trace: a None between them breaks the line."""
    xs: list = []
    ys: list = []
    for ring in rings:
        for x, y in ring:
            xs.append(x)
            ys.append(y)
        xs.append(None)
        ys.append(None)
    return xs, ys


def _sig3(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3g}"


def _contest_line(staffing: dict | None, district: str) -> str:
    """The three candidates with the largest share of this district's book, as a hover line."""
    if not staffing:
        return ""
    contest = (staffing.get("contest") or {}).get(district)
    if not contest:
        return ""
    share = contest.get("share") or {}
    top = sorted(share.items(), key=lambda kv: kv[1], reverse=True)[:3]
    if not top:
        return ""
    return "top reps " + ", ".join(f"{rep} {frac:.0%}" for rep, frac in top)


def figure(
    rows: list[dict],
    geom: dict | None,
    *,
    highlight_zips: set[str] = frozenset(),
    highlight_label: str = "",
    outline: dict | None = None,
    staffing: dict | None = None,
) -> go.Figure:
    """The map for one zip table.

    `outline` is a ring bundle from another map's `geom.json`, drawn dashed on top so a child
    map can be read against its parent: `{"rings": [...], "label": str, "color": str}`.
    """
    colours = _colours(rows, geom)
    fig = go.Figure()

    if geom:
        xs: list = []
        ys: list = []
        for info in geom.get("states", {}).values():
            sx, sy = _joined(info.get("rings", []))
            xs += sx
            ys += sy
        if xs:
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines", name=OUTLINES, hoverinfo="skip", showlegend=False,
                line=dict(color="#b0b0b0", width=0.8)))

        for district, info in sorted(geom.get("districts", {}).items()):
            dx, dy = _joined(info.get("rings", []))
            if not dx:
                continue
            fig.add_trace(go.Scatter(
                x=dx, y=dy, mode="lines", fill="toself", name=district, hoverinfo="skip",
                opacity=0.35, fillcolor=colours.get(district, info.get("color", "#cccccc")),
                line=dict(color=info.get("color", "#888888"), width=0.5)))

    drawn = [row for row in rows if row["x"] is not None and row["y"] is not None]
    staff_lines = {d: _contest_line(staffing, d) for d in {r["district"] for r in drawn}}
    fig.add_trace(go.Scattergl(
        x=[row["x"] for row in drawn],
        y=[row["y"] for row in drawn],
        mode="markers", name=ZIPS, showlegend=False,
        marker=dict(size=_sizes(drawn),
                    color=[colours.get(row["district"], "#888888") for row in drawn],
                    line=dict(width=0)),
        customdata=[[row["zip"], row["state"], row["district"], row["rep"] or "unassigned",
                     _sig3(row["opportunity"]), staff_lines.get(row["district"], "")]
                    for row in drawn],
        hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                       "district %{customdata[2]} · rep %{customdata[3]}<br>"
                       "opportunity %{customdata[4]}<br>"
                       "%{customdata[5]}<extra></extra>")))

    if geom:
        labelled = [(code, info["label"]) for code, info in sorted(geom.get("states", {}).items())
                    if info.get("label")]
        if labelled:
            fig.add_trace(go.Scatter(
                x=[point[0] for _, point in labelled], y=[point[1] for _, point in labelled],
                mode="text", name=HANDLES, showlegend=False,
                text=[code for code, _ in labelled],
                textfont=dict(size=11, color="#333333"),
                customdata=[[code] for code, _ in labelled],
                hovertemplate="state %{customdata[0]}<extra></extra>"))

    if highlight_zips:
        marked = [row for row in drawn if row["zip"] in highlight_zips]
        if marked:
            fig.add_trace(go.Scattergl(
                x=[row["x"] for row in marked], y=[row["y"] for row in marked],
                mode="markers", name=highlight_label or "highlight", hoverinfo="skip",
                marker=dict(symbol="circle-open", size=16, color="#111111",
                            line=dict(width=2, color="#111111"))))

    if outline and outline.get("rings"):
        ox, oy = _joined(outline["rings"])
        fig.add_trace(go.Scatter(
            x=ox, y=oy, mode="lines", name=outline.get("label", "outline"), hoverinfo="skip",
            line=dict(color=outline.get("color", "#111111"), width=1.6, dash="dash")))

    axis = dict(showgrid=False, zeroline=False, showticklabels=False, visible=False)
    fig.update_layout(
        height=700, margin=dict(l=0, r=0, t=10, b=0), dragmode="pan",
        xaxis=axis, yaxis=dict(**axis, scaleanchor="x", scaleratio=1),
        legend=dict(yanchor="top", y=1.0, xanchor="left", x=1.01),
        plot_bgcolor="white", uirevision="map", clickmode="event+select")
    return fig
