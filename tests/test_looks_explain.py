"""tools/looks/explain.py on a toy ledger (the study's own toy), and on one real district when the hub inputs exist."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

import shapely

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("looks_explain", os.path.join(HERE, "..", "tools", "looks", "explain.py"))
explain = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(explain)
study = explain.study

# the toy of test_looks_study.py: each ZIP 1 km2; A the corners of a 2 km square, B the centre, C a triangle far east
ZIPS = {"a1": (0, 0, "A"), "a2": (2, 0, "A"), "a3": (0, 2, "A"), "a4": (2, 2, "A"), "b1": (1, 1, "B"),
        "c1": (10, 0, "C"), "c2": (10, 1, "C"), "c3": (11, 0, "C")}
MASS = {"a1": 1, "a2": 1, "a3": 1, "a4": 1, "b1": 8, "c1": 1, "c2": 1, "c3": 1}
CBSA = {"a1": "k", "a2": "k", "a3": "k", "b1": "k"}


def _toy_ctx():
    names = list(ZIPS)
    edges = [("b1", a) for a in ("a1", "a2", "a3", "a4")] + [("c1", "c2"), ("c1", "c3")]
    ref = study.Ref(names, [ZIPS[z][0] for z in names], [ZIPS[z][1] for z in names], [1.0] * len(names), edges,
                    {"k": "Kay Metro Area"})
    rows = [{"zip_code": z, "state": "S" if d != "C" else "T", "model_channel": "X", "district": d,
             "county": "c1" if d != "C" else "c9", "cbsa": CBSA.get(z, ""), "m_rel": str(MASS[z]),
             "current_channel": "x"} for z, (_, _, d) in ZIPS.items()]
    drows, mrows = [], []
    for name, group in (("census/divisions", "reference"), ("toy", "main")):
        d, _ = study.measure_map(name, rows, ref)
        drows += d
        mrows.append(study.aggregate(name, group, d, {"necks": "", "pieces": "", "splits": ""}))
    for r in drows:
        for c in explain.NUMERIC:
            r[c] = float(r[c])
    polys = {z: shapely.box((x - 0.5) * 1000, (y - 0.5) * 1000, (x + 0.5) * 1000, (y + 0.5) * 1000)
             for z, (x, y, _) in ZIPS.items()}
    states = {"S": shapely.box(-3000, -3000, 4000, 4000), "T": shapely.box(8000, -3000, 14000, 4000)}
    cells, _ = study.channel_cells(rows)
    for r in mrows:
        for c in ("necks", "pieces", "splits"):
            r[c] = float("nan")
    return explain.Ctx(drows, mrows, ref, polys, states, cells_of={"toy": cells, "census/divisions": cells})


def test_toy_pages_build_and_check_the_rows():
    import matplotlib.pyplot as plt
    explain.MIN_ZIPS = 1
    ctx = _toy_ctx()
    a = next(r for r in ctx.drows if r["map"] == "toy" and r["district"] == "A")
    v = ctx.hull_view(a)       # redraws A from the ledger and raises unless it reproduces the row
    assert v["hull_km2"] == 4.0 and v["bite_zips"] == ["b1"] and v["bite_km2"] == 1.0
    bad = dict(a, bite=0.5)
    try:
        ctx.check(bad, v)
    except AssertionError:
        pass
    else:
        raise AssertionError("a row that disagrees with the redrawn district must raise")
    for fn in (explain.page_hull_fill, explain.page_bite, explain.page_axis, explain.page_effort, explain.page_cut,
               explain.page_doughnuts, explain.page_hub, explain.page_glossary, explain.page_limits):
        fig = fn(ctx)
        assert fig.axes or fn in (explain.page_glossary, explain.page_limits), fn.__name__
        plt.close(fig)
    with tempfile.TemporaryDirectory() as d:
        out = explain.build(ctx, os.path.join(d, "x", "t.pdf"), pages=(explain.page_hull_fill, explain.page_limits),
                            log=lambda *_: None)
        assert os.path.getsize(out) > 1000


def test_limits_table_and_helpers():
    ctx = _toy_ctx()
    got = {m: (n, c, anyf) for m, n, c, anyf in explain.limits_table(ctx.drows, ctx.mrows)}
    # bite > 0.30: none (A is 0.25); hull_fill < 0.45: none; > 4 states: none; hard doughnut: A and B
    assert got["toy"] == (3, [0, 0, 0, 2], 2)
    assert explain.fill_holes(shapely.Polygon([(0, 0), (9, 0), (9, 9), (0, 9)],
                                              [[(1, 1), (2, 1), (2, 2), (1, 2)]])).interiors[:] == []
    assert explain.farthest(__import__("numpy").array([[0.0, 0], [3, 4], [1, 1]]))[2] == 5.0


def test_real_district_reproduces_its_row():
    miss = explain.missing_inputs()
    if miss:
        print(f"SKIP  test_looks_explain.py: {miss[0]} missing; the real-district check did not run", file=sys.stderr)
        return
    ctx = explain.Ctx.load()
    row = next(r for r in ctx.real if r["hull_km2"] > 0 and r["n_zips"] < 400)
    assert ctx.hull_view(row)["hull_km2"] > 0         # raises when the drawn district disagrees with districts.csv
