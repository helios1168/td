"""app.mapfig's rep and staffed figures: trace names and order.

Gated on plotly, which the solver venv does not have: every test returns immediately when it
is absent, so `.venv/bin/python3 tests/run_all.py` still passes here (as an early return, not
a skip the runner counts). Run for real under the app venv:
    PYTHONPATH=$PWD .venv-app/bin/python3 tests/run_all.py -k mapfig
"""
from __future__ import annotations

try:
    import plotly
    from app import mapfig
except ImportError:
    plotly = None
    mapfig = None


def _reps() -> dict:
    return dict(
        crs="laea",
        instance="instance_descaled_v2_conus.json.gz",
        reps=["R1", "R2", "R3"],
        book_share={"R1": 0.4, "R2": 0.4},
        free_share=0.2,
        zips={
            "z1": {"top": "R1", "shares": {"R1": 1.0}, "free": 0.0, "n": 1, "weight": 0.4},
            "z2": {"top": "R2", "shares": {"R2": 0.6, "R1": 0.4}, "free": 0.0, "n": 2,
                  "weight": 0.4},
            "z3": {"top": "", "shares": {}, "free": 1.0, "n": 0, "weight": 0.2},
        },
        territories={
            "R1": {"rings": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]], "color": "#4269d0"},
            "R2": {"rings": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]], "color": "#efb118"},
        },
        footprints={
            "R1": {"rings": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "R2": {"rings": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]]},
        },
        contested={"rings": [[[1, 0], [1.2, 0], [1.2, 1], [1, 1], [1, 0]]]},
        states={"S1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]], "label": [1.0, 0.5]}},
    )


def _rows() -> list[dict]:
    return [
        dict(zip="z1", state="S1", x=0.5, y=0.5, opportunity=1.0, district="D1", rep="R1"),
        dict(zip="z2", state="S1", x=1.5, y=0.5, opportunity=1.0, district="D1", rep="R2"),
    ]


def _geom() -> dict:
    return dict(
        states={"S1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]], "label": [1.0, 0.5]}},
        districts={"D1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]],
                         "color": "#4269d0"}})


def test_rep_colours_shared_across_figures():
    if plotly is None:
        return
    colours = mapfig.rep_colours(_reps())
    assert colours["R1"] == "#4269d0"
    assert colours["R2"] == "#efb118"
    assert colours["R3"] not in ("#4269d0", "#efb118")


def test_rep_figure_trace_order_without_geom():
    if plotly is None:
        return
    fig = mapfig.rep_figure(_reps(), _rows(), None)
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, "R1", "R2", mapfig.CONTESTED, mapfig.REP_ZIPS,
                     mapfig.HANDLES]


def test_rep_figure_trace_order_with_geom_and_focus():
    if plotly is None:
        return
    fig = mapfig.rep_figure(_reps(), _rows(), _geom(), focus_rep="R1")
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, "R1", "R2", mapfig.CONTESTED, mapfig.FOCUS,
                     mapfig.DISTRICT_LINES, mapfig.REP_ZIPS, mapfig.HANDLES]


def test_rep_figure_colour_by_n_adds_legend():
    if plotly is None:
        return
    fig = mapfig.rep_figure(_reps(), _rows(), None, colour_by="n")
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, "R1", "R2", mapfig.CONTESTED, mapfig.REP_ZIPS,
                     *mapfig.N_LABELS, mapfig.HANDLES]


def test_staffed_figure_unstaffed_district():
    if plotly is None:
        return
    colours = mapfig.rep_colours(_reps())
    staffing = dict(assignment={}, unstaffed_districts=["D1"])
    fig = mapfig.staffed_figure(_rows(), _geom(), colours, staffing=staffing)
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, mapfig.UNSTAFFED, mapfig.REP_ZIPS, mapfig.HANDLES]


def test_staffed_figure_split_zips_present():
    if plotly is None:
        return
    colours = mapfig.rep_colours(_reps())
    staffing = dict(assignment={"D1": "R1"}, unstaffed_districts=[])
    fig = mapfig.staffed_figure(_rows(), _geom(), colours, staffing=staffing)
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, "D1", mapfig.SPLIT_ZIPS, mapfig.REP_ZIPS, mapfig.HANDLES]


def test_staffed_figure_bbox_sets_axis_ranges():
    if plotly is None:
        return
    colours = mapfig.rep_colours(_reps())
    staffing = dict(assignment={"D1": "R1"}, unstaffed_districts=[])
    bbox = (0.0, 0.0, 2.0, 1.0)
    fig = mapfig.staffed_figure(_rows(), _geom(), colours, staffing=staffing, bbox=bbox)
    assert list(fig.layout.xaxis.range) == [bbox[0], bbox[2]]
    assert list(fig.layout.yaxis.range) == [bbox[1], bbox[3]]
    assert fig.layout.uirevision == bbox
