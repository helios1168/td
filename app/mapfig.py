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

# Rep-territory and staffed-map trace names.
REP_FILLS = "rep territories"
CONTESTED = "contested"
FOCUS = "focus"
DISTRICT_LINES = "district lines"
REP_ZIPS = "reps"
STAFFED_FILLS = "staffed districts"
UNSTAFFED = "unstaffed"
SPLIT_ZIPS = "split"

# Four-step sequential ramp for "reps with book" (0, 1, 2, 3+), one hue light to dark, plus the
# outline that keeps a class-0 marker visible against the white surface. Validated with the
# `dataviz` skill's palette checker.
N_RAMP = ["#f1f5f9", "#a5b4fc", "#6366f1", "#312e81"]
N_LABELS = ["0 reps", "1 rep", "2 reps", "3+ reps"]
N_OUTLINE = "#94a3b8"

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


def _joined_many(infos) -> tuple[list, list]:
    """Several features' rings as one trace: each feature is `_joined` in turn, and the `None`
    it already ends on breaks the line before the next feature starts."""
    xs: list = []
    ys: list = []
    for info in infos:
        sx, sy = _joined(info.get("rings", []))
        xs += sx
        ys += sy
    return xs, ys


def rep_colours(reps: dict) -> dict[str, str]:
    """`{rep: hex}` shared by the rep map and the staffed map, so a rep keeps one hue on both.

    A rep with a territory keeps `reps.json`'s own colour (assigned so neighbours differ); a
    rep with none takes the next `PALETTE` entry not already spoken for.
    """
    territories = reps.get("territories", {})
    used = {info["color"] for info in territories.values() if info.get("color")}
    colours: dict[str, str] = {}
    i = 0
    for rep in reps.get("reps", []):
        colour = territories.get(rep, {}).get("color")
        if not colour:
            tries = 0
            while PALETTE[i % len(PALETTE)] in used and tries < len(PALETTE):
                i += 1
                tries += 1
            colour = PALETTE[i % len(PALETTE)]
            used.add(colour)
            i += 1
        colours[rep] = colour
    return colours


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
    bbox: tuple[float, float, float, float] | None = None,
) -> go.Figure:
    """The map for one zip table.

    `outline` is a ring bundle from another map's `geom.json`, drawn dashed on top so a child
    map can be read against its parent: `{"rings": [...], "label": str, "color": str}`.

    `bbox` is `(x0, y0, x1, y1)`, LAEA metres: it sets the axis ranges, for zooming to one
    district, and `uirevision` becomes the bbox itself so pan and zoom persist across reruns
    with the same bbox and reset when it changes.
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
    xaxis = dict(axis, range=[bbox[0], bbox[2]]) if bbox else dict(axis)
    yaxis = dict(axis, scaleanchor="x", scaleratio=1, range=[bbox[1], bbox[3]]) if bbox \
        else dict(axis, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=700, margin=dict(l=0, r=0, t=10, b=0), dragmode="pan",
        xaxis=xaxis, yaxis=yaxis,
        legend=dict(yanchor="top", y=1.0, xanchor="left", x=1.01),
        plot_bgcolor="white", uirevision=(bbox if bbox else "map"), clickmode="event+select")
    return fig


def rep_figure(
    reps: dict,
    rows: list[dict] | None,
    geom: dict | None,
    *,
    colour_by: str = "rep",
    focus_rep: str = "",
    show_contested: bool = True,
    district_lines: bool = True,
    bbox: tuple[float, float, float, float] | None = None,
) -> go.Figure:
    """The rep-territory map: whose book covers which zips, as sold today.

    `reps` is a loaded `reps.json`. `rows` (`load_rows`'s output, or `None`) supplies the zip
    coordinates for the hover layer; `reps.json` alone carries no `x, y`, so without `rows`
    `REP_ZIPS` is skipped. `geom` is another run's district geometry, drawn as an overlay when
    `district_lines` is set. `colour_by="n"` drops the territory fills to outlines and instead
    colours every zip by how many reps hold book there, off the four-step `N_RAMP`.
    """
    colours = rep_colours(reps)
    fig = go.Figure()

    xs, ys = _joined_many(reps.get("states", {}).values())
    if xs:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=OUTLINES, hoverinfo="skip", showlegend=False,
            line=dict(color="#b0b0b0", width=0.8)))

    for rep, info in sorted(reps.get("territories", {}).items()):
        tx, ty = _joined(info.get("rings", []))
        if not tx:
            continue
        colour = colours.get(rep, "#cccccc")
        if colour_by == "n":
            fig.add_trace(go.Scatter(
                x=tx, y=ty, mode="lines", name=rep, legendgroup=REP_FILLS, showlegend=False,
                hoverinfo="skip", line=dict(color="#cbd5e1", width=0.6)))
        else:
            fig.add_trace(go.Scatter(
                x=tx, y=ty, mode="lines", fill="toself", name=rep, legendgroup=REP_FILLS,
                showlegend=False, hoverinfo="skip", opacity=0.45,
                fillcolor=colour, line=dict(color=colour, width=0.5)))

    if show_contested:
        cx, cy = _joined((reps.get("contested") or {}).get("rings", []))
        if cx:
            fig.add_trace(go.Scatter(
                x=cx, y=cy, mode="lines", fill="toself", name=CONTESTED, hoverinfo="skip",
                opacity=0.5, fillcolor="rgba(0,0,0,0)",
                fillpattern=dict(shape="/", fgcolor="#444444", solidity=0.35),
                line=dict(color="#444444", width=0.5)))

    if focus_rep:
        info = (reps.get("territories") or {}).get(focus_rep) \
            or (reps.get("footprints") or {}).get(focus_rep)
        if info:
            fx, fy = _joined(info.get("rings", []))
            if fx:
                fig.add_trace(go.Scatter(
                    x=fx, y=fy, mode="lines", fill="toself", name=FOCUS, hoverinfo="skip",
                    opacity=0.7, fillcolor=colours.get(focus_rep, "#111111"),
                    line=dict(color="#111111", width=1.5)))

    if district_lines and geom:
        dx, dy = _joined_many(geom.get("districts", {}).values())
        if dx:
            fig.add_trace(go.Scatter(
                x=dx, y=dy, mode="lines", name=DISTRICT_LINES, hoverinfo="skip",
                showlegend=False, line=dict(color="#111111", width=1.8)))

    if rows:
        zips = reps.get("zips", {})
        drawn = [row for row in rows if row.get("x") is not None and row.get("y") is not None
                and row.get("zip") in zips]
        if drawn:
            if colour_by == "n":
                classes = [min(zips[row["zip"]].get("n", 0), 3) for row in drawn]
                marker = dict(
                    size=6, color=[N_RAMP[c] for c in classes],
                    line=dict(width=[1 if c == 0 else 0 for c in classes], color=N_OUTLINE))
            else:
                marker = dict(size=4, color="#333333", line=dict(width=0))
            fig.add_trace(go.Scattergl(
                x=[row["x"] for row in drawn], y=[row["y"] for row in drawn],
                mode="markers", name=REP_ZIPS, showlegend=False, opacity=0.6, marker=marker,
                customdata=[_rep_hover(row, zips[row["zip"]]) for row in drawn],
                hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                               "district %{customdata[2]}<br>"
                               "%{customdata[3]} · free %{customdata[4]}<extra></extra>")))

    if colour_by == "n":
        for label, colour in zip(N_LABELS, N_RAMP):
            outline = dict(width=1, color=N_OUTLINE) if colour == N_RAMP[0] else None
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers", name=label,
                marker=dict(size=9, color=colour, line=outline)))

    labelled = [(code, info["label"]) for code, info in sorted(reps.get("states", {}).items())
               if info.get("label")]
    if labelled:
        fig.add_trace(go.Scatter(
            x=[point[0] for _, point in labelled], y=[point[1] for _, point in labelled],
            mode="text", name=HANDLES, showlegend=False,
            text=[code for code, _ in labelled],
            textfont=dict(size=11, color="#333333"),
            customdata=[[code] for code, _ in labelled],
            hovertemplate="state %{customdata[0]}<extra></extra>"))

    axis = dict(showgrid=False, zeroline=False, showticklabels=False, visible=False)
    xaxis = dict(axis, range=[bbox[0], bbox[2]]) if bbox else dict(axis)
    yaxis = dict(axis, scaleanchor="x", scaleratio=1, range=[bbox[1], bbox[3]]) if bbox \
        else dict(axis, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=700, margin=dict(l=0, r=0, t=10, b=0), dragmode="pan",
        xaxis=xaxis, yaxis=yaxis,
        legend=dict(yanchor="top", y=1.0, xanchor="left", x=1.01),
        plot_bgcolor="white", uirevision=(bbox if bbox else "rep-map"),
        clickmode="event+select")
    return fig


def _rep_hover(row: dict, zip_info: dict) -> list:
    shares = sorted((zip_info.get("shares") or {}).items(), key=lambda kv: kv[1], reverse=True)
    line = ", ".join(f"{rep} {frac:.0%}" for rep, frac in shares) if shares else "none"
    free = zip_info.get("free") or 0.0
    return [row["zip"], row["state"], row.get("district") or "?", line, f"{free:.0%}"]


def staffed_figure(
    rows: list[dict],
    geom: dict | None,
    rep_colours: dict[str, str],
    *,
    staffing: dict,
    bbox: tuple[float, float, float, float] | None = None,
) -> go.Figure:
    """The staffed ("after") map: one fill per district in its assigned rep's colour.

    `rep_colours` is the shared `{rep: hex}` map from `mapfig.rep_colours`, so a rep keeps the
    same hue here as on the incumbent map. `staffing` is a loaded `staffing.json`:
    `assignment` gives each district's rep, `unstaffed_districts` the ones with none. `rows`
    carries the table's own `rep` column, which a split can set differently per zip inside one
    district; a zip whose `rep` disagrees with its district's assignment draws in `SPLIT_ZIPS`.
    """
    geom = geom or {}
    assignment = staffing.get("assignment", {})
    unstaffed = set(staffing.get("unstaffed_districts", []))
    districts = geom.get("districts", {})
    fig = go.Figure()

    xs, ys = _joined_many(geom.get("states", {}).values())
    if xs:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=OUTLINES, hoverinfo="skip", showlegend=False,
            line=dict(color="#b0b0b0", width=0.8)))

    for district, info in sorted(districts.items()):
        if district in unstaffed:
            continue
        dx, dy = _joined(info.get("rings", []))
        if not dx:
            continue
        colour = rep_colours.get(assignment.get(district, ""), "#cccccc")
        fig.add_trace(go.Scatter(
            x=dx, y=dy, mode="lines", fill="toself", name=district, legendgroup=STAFFED_FILLS,
            showlegend=False, hoverinfo="skip", opacity=0.55,
            fillcolor=colour, line=dict(color=colour, width=0.5)))

    ux, uy = _joined_many(info for d, info in sorted(districts.items()) if d in unstaffed)
    if ux:
        fig.add_trace(go.Scatter(
            x=ux, y=uy, mode="lines", fill="toself", name=UNSTAFFED, hoverinfo="skip",
            opacity=0.5, fillcolor="rgba(0,0,0,0)",
            fillpattern=dict(shape="/", fgcolor="#444444", solidity=0.35),
            line=dict(color="#cccccc", width=0.5)))

    drawn = [row for row in rows if row.get("x") is not None and row.get("y") is not None]
    split = [row for row in drawn if row.get("district") and row.get("rep")
            and row["district"] not in unstaffed
            and row["rep"] != assignment.get(row["district"], "")]
    if split:
        fig.add_trace(go.Scattergl(
            x=[row["x"] for row in split], y=[row["y"] for row in split],
            mode="markers", name=SPLIT_ZIPS, showlegend=False,
            marker=dict(size=6, color=[rep_colours.get(row["rep"], "#333333") for row in split],
                       line=dict(width=0)),
            customdata=[[row["zip"], row["state"], row["district"], row["rep"]]
                       for row in split],
            hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                           "district %{customdata[2]} · rep %{customdata[3]}<extra></extra>")))

    if drawn:
        fig.add_trace(go.Scattergl(
            x=[row["x"] for row in drawn], y=[row["y"] for row in drawn],
            mode="markers", name=REP_ZIPS, showlegend=False,
            marker=dict(size=4, color="#333333", line=dict(width=0)), opacity=0.6,
            customdata=[[row["zip"], row["state"], row.get("district") or "?",
                        row.get("rep") or "unassigned"] for row in drawn],
            hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                           "district %{customdata[2]} · rep %{customdata[3]}<extra></extra>")))

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

    axis = dict(showgrid=False, zeroline=False, showticklabels=False, visible=False)
    xaxis = dict(axis, range=[bbox[0], bbox[2]]) if bbox else dict(axis)
    yaxis = dict(axis, scaleanchor="x", scaleratio=1, range=[bbox[1], bbox[3]]) if bbox \
        else dict(axis, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=700, margin=dict(l=0, r=0, t=10, b=0), dragmode="pan",
        xaxis=xaxis, yaxis=yaxis,
        plot_bgcolor="white", uirevision=(bbox if bbox else "staffed-map"),
        clickmode="event+select")
    return fig
