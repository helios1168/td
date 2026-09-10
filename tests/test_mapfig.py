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
                         "color": "#4269d0"}},
        cells={
            "z1": {"rings": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "z2": {"rings": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]]},
        })


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
    assert names == [mapfig.OUTLINES, "R1", "R2", mapfig.CONTESTED, mapfig.HANDLES]


def test_rep_figure_trace_order_with_geom_and_focus():
    if plotly is None:
        return
    fig = mapfig.rep_figure(_reps(), _rows(), _geom(), focus_rep="R1")
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, "R1", "R2", mapfig.CONTESTED, mapfig.FOCUS,
                     mapfig.DISTRICT_LINES, mapfig.HANDLES]
    assert fig.data[1].hoveron == "points"
    assert "z1" in fig.data[1].text[0]


def test_rep_figure_colour_by_n_adds_legend():
    if plotly is None:
        return
    fig = mapfig.rep_figure(_reps(), _rows(), _geom(), colour_by="n")
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, *mapfig.N_LABELS, mapfig.CONTESTED,
                     mapfig.DISTRICT_LINES, mapfig.HANDLES]
    assert fig.data[1].x == (None,)  # "0 reps": z3 has no cell, so nothing qualifies


def test_staffed_figure_unstaffed_district():
    if plotly is None:
        return
    colours = mapfig.rep_colours(_reps())
    staffing = dict(assignment={}, unstaffed_districts=["D1"])
    fig = mapfig.staffed_figure(_rows(), _geom(), colours, staffing=staffing)
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, mapfig.UNSTAFFED, mapfig.HANDLES]


def test_staffed_figure_fills_cells_by_the_table_rep():
    if plotly is None:
        return
    colours = mapfig.rep_colours(_reps())
    staffing = dict(assignment={"D1": "R1"}, unstaffed_districts=[])
    fig = mapfig.staffed_figure(_rows(), _geom(), colours, staffing=staffing)
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, "R1", "R2", mapfig.HANDLES]
    assert fig.data[2].fillcolor == colours["R2"]


def test_staffed_figure_without_cells_falls_back_to_district_fills():
    if plotly is None:
        return
    colours = mapfig.rep_colours(_reps())
    staffing = dict(assignment={"D1": "R1"}, unstaffed_districts=[])
    geom = dict(
        states={"S1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]], "label": [1.0, 0.5]}},
        districts={"D1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]],
                         "color": "#4269d0"}})
    fig = mapfig.staffed_figure(_rows(), geom, colours, staffing=staffing)
    names = [t.name for t in fig.data]
    assert names == [mapfig.OUTLINES, "D1", mapfig.HANDLES]


def test_figure_geom_branch_names_every_cell_trace_zips_with_customdata():
    if plotly is None:
        return
    fig = mapfig.figure(_rows(), _geom())
    fill_traces = [t for t in fig.data if t.name == mapfig.ZIPS]
    assert fill_traces
    for t in fill_traces:
        assert t.customdata
        for entry in t.customdata:
            if entry is not None:
                assert len(entry) == 6


def test_reach_boundary_is_drawn_after_the_cell_fills():
    """The fills are 0.85 opacity, so a boundary drawn before them is invisible -- which is
    exactly what happened when the district outline sat above the cells in the trace order."""
    if plotly is None:
        return
    geom = _geom()
    geom["district_reach"] = {"D1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]],
                                     "color": "#4269d0"}}
    fig = mapfig.figure(_rows(), geom)
    names = [t.name for t in fig.data]
    last_fill = max(i for i, n in enumerate(names) if n == mapfig.ZIPS)
    assert names.index(mapfig.REACH) > last_fill, names
    assert names.index("D1") > last_fill, names          # the honest outline too

    reach = fig.data[names.index(mapfig.REACH)]
    assert reach.mode == "lines"
    assert reach.fill is None                 # stroked, never filled: it is not held ground
    assert reach.line.width > fig.data[names.index("D1")].line.width


def test_figure_without_a_reach_layer_draws_only_the_real_outline():
    """A geom.json exported before the layer existed keeps the honest ZCTA outline and simply
    gets no reach boundary."""
    if plotly is None:
        return
    fig = mapfig.figure(_rows(), _geom())     # `_geom()` carries no `district_reach`
    names = [t.name for t in fig.data]
    assert mapfig.REACH not in names
    assert "D1" in names


def test_figure_falls_back_to_dots_without_geom():
    if plotly is None:
        return
    fig = mapfig.figure(_rows(), None)
    zip_traces = [t for t in fig.data if t.name == mapfig.ZIPS]
    assert len(zip_traces) == 1
    trace = zip_traces[0]
    assert trace.mode == "markers"
    assert trace.marker.line.width == 0
    assert len(trace.customdata) == 2
    assert len(trace.customdata[0]) == 6


def test_figure_falls_back_to_dots_without_cells():
    if plotly is None:
        return
    geom = dict(
        states={"S1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]], "label": [1.0, 0.5]}},
        districts={"D1": {"rings": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]],
                         "color": "#4269d0"}})
    fig = mapfig.figure(_rows(), geom)
    zip_traces = [t for t in fig.data if t.name == mapfig.ZIPS]
    assert len(zip_traces) == 1
    trace = zip_traces[0]
    assert trace.mode == "markers"
    assert trace.marker.line.width == 0


def test_quantile_bins_even_split():
    if plotly is None:
        return
    rows = [dict(opportunity=float(i)) for i in range(8)]
    bins = mapfig._quantile_bins(rows, 4)
    assert len(bins) == 4
    assert all(len(b) == 2 for b in bins)
    assert [r["opportunity"] for r in bins[0]] == [0.0, 1.0]


def test_quantile_bins_tie_heavy_collapses_to_fewer_bins():
    if plotly is None:
        return
    # 24 rows, all tied at the same opportunity, into 8 bins: a straight count-based split
    # (3 per bin) would still produce 8 bins here since 24 >= 8, so this only passes if ties
    # are actually merged across the count boundaries.
    rows = [dict(opportunity=1.0)] * 24
    bins = mapfig._quantile_bins(rows, 8)
    assert len(bins) == 1
    assert sum(len(b) for b in bins) == 24


def test_quantile_bins_empty_input():
    if plotly is None:
        return
    assert mapfig._quantile_bins([], 8) == []


def test_cell_trace_border_defaults_to_visible_not_same_as_fill():
    if plotly is None:
        return
    trace = mapfig._cell_trace(_geom()["cells"], ["z1"], {}, name="t", colour="#123456",
                               opacity=0.5)
    assert trace.line.color != "#123456"
    assert trace.line.color == mapfig.N_OUTLINE


def test_figure_residual_dot_trace_for_zips_without_cells():
    if plotly is None:
        return
    # z3 has no cell in _geom() -- geom_export only emits one for a row with a district, or an
    # older/parent geom may not cover this table's zips at all. It must still render, clickable,
    # in a trace named ZIPS with well-formed customdata.
    rows = _rows() + [dict(zip="z3", state="S1", x=1.8, y=0.2, opportunity=0.5,
                           district="D1", rep="")]
    fig = mapfig.figure(rows, _geom())
    found = False
    for t in fig.data:
        if t.name != mapfig.ZIPS or not t.customdata:
            continue
        for entry in t.customdata:
            if entry and entry[0] == "z3":
                found = True
                assert len(entry) == 6
    assert found


def test_bin_colour_last_bin_always_darkest():
    if plotly is None:
        return
    for n_bins in (2, 3, 8):
        assert mapfig._bin_colour(n_bins - 1, n_bins) == mapfig.OPPORTUNITY_RAMP[-1]


def test_legend_swatch_omitted_for_bin_with_no_drawable_trace():
    if plotly is None:
        return
    rows = [dict(zip="z1", state="S1", x=0.5, y=0.5, opportunity=1.0, district="D1", rep="R1")]
    geom = dict(states={}, districts={}, cells={"z1": {"rings": []}})
    fig = mapfig.figure(rows, geom)
    legend_traces = [t for t in fig.data
                     if isinstance(t.name, str) and t.name.startswith("opportunity ")]
    assert legend_traces == []


def test_district_trace_is_outline_only_no_fill():
    if plotly is None:
        return
    fig = mapfig.figure(_rows(), _geom())
    district_trace = next(t for t in fig.data if t.name == "D1")
    assert district_trace.fill is None
    assert district_trace.fillcolor is None
    assert district_trace.showlegend is False


def test_figure_strokes_a_districts_hole_ring():
    """A district's real gap (`geom["districts"]["D1"]["holes"]`, decision 1) must be drawn --
    stroked in a second "D1" trace, never folded into the outline trace's own rings -- and that
    trace must never become a click target (`app/tab_map.py` matches selections by trace name
    against `mapfig.ZIPS`) or gain a fill (`staffed_figure`'s two fill sites are a different
    function and untouched, but the hole trace itself must not fill either)."""
    if plotly is None:
        return
    geom = _geom()
    geom["districts"]["D1"] = dict(geom["districts"]["D1"],
                                   holes=[[[0.5, 0.3], [1.0, 0.3], [1.0, 0.7], [0.5, 0.7],
                                          [0.5, 0.3]]])
    fig = mapfig.figure(_rows(), geom)
    d1_traces = [t for t in fig.data if t.name == "D1"]
    assert len(d1_traces) == 2, "expected one outline trace and one hole trace, both named D1"
    hole_trace = d1_traces[1]

    assert hole_trace.name != mapfig.ZIPS
    assert hole_trace.mode == "lines"
    assert hole_trace.fill is None
    assert hole_trace.fillcolor is None
    assert hole_trace.hoverinfo == "skip"
    assert hole_trace.showlegend is False
    assert 0.5 in hole_trace.x and 1.0 in hole_trace.x


def test_figure_district_with_no_holes_gets_a_single_trace():
    if plotly is None:
        return
    fig = mapfig.figure(_rows(), _geom())          # D1 has no "holes" key
    d1_traces = [t for t in fig.data if t.name == "D1"]
    assert len(d1_traces) == 1


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
    assert fig.layout.hoverdistance == 40
