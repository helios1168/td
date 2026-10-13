"""#133's land balance (the main-map overnight grid, 2026-10-13): `land.py`'s split-group rows
by hand, `land.csv`, and `draw.py`'s land term on a toy MILP, a drawing the border term alone
leaves unbalanced held to R, every seed meeting the new rows, never infeasible."""
from __future__ import annotations

import csv
import importlib.util
import os
import sys
import tempfile

from tests import test_realize as tr

HERE = os.path.dirname(os.path.abspath(__file__))


def _module(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(HERE, "..", "tools", "exp", "contig", file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


land = _module("contig_land", "land.py")
draw = _module("contig_draw", "draw.py")


def _ledger(cells) -> list:
    """Ledger rows from (ZIP, fine channel, state, planning channel, district, mass)."""
    return [{"zip_code": z, "current_channel": f, "state": s, "model_channel": ch, "district": d,
             "m_rel": repr(float(m))} for z, f, s, ch, d, m in cells]


def test_land_rows_by_hand():
    """A: X_01 (land 100) against X_02 (5 + 3, two fine channels on one ZIP counted once): 12.5,
    beyond R = 10; X_03's sliver (0.5 km², 10% of its mass) is no piece but counts in `ratio_all`.
    B: one piece of 20% or more, no ratio.  C is whole, no row; Y's unowned cell is skipped."""
    aland = {"a1": 100.0, "a2": 5.0, "a3": 3.0, "a4": 0.5, "b1": 40.0, "b2": 2.0, "c1": 7.0}
    led = _ledger([("a1", "wh", "A", "X", "X_01", 6.0), ("a2", "wh", "A", "X", "X_02", 2.0),
                   ("a2", "fi", "A", "X", "X_02", 1.0), ("a3", "wh", "A", "X", "X_02", 1.0),
                   ("a4", "wh", "A", "X", "X_03", 1.0), ("b1", "wh", "B", "X", "X_03", 9.0),
                   ("b2", "wh", "B", "X", "X_01", 0.5), ("c1", "wh", "C", "X", "X_01", 3.5),
                   ("c1", "fi", "C", "Y", "", 1.0)])
    a, b = land.land_rows(led, aland)
    assert (a["channel"], a["state"], a["districts"], a["pieces"]) == ("X", "A", 3, 2)
    assert (a["largest"], a["largest_km2"], a["smallest"], a["smallest_km2"]) == ("X_01", 100.0, "X_02", 8.0)
    assert a["ratio"] == 12.5 and a["ratio_all"] == 200.0 and a["over"]
    assert a["detail"] == [("X_01", 100.0, 0.6), ("X_02", 8.0, 1.0), ("X_03", 0.5, 0.1)]
    assert (b["state"], b["pieces"], b["ratio"], b["over"]) == ("B", 1, None, False)
    assert (b["largest"], b["smallest"], b["ratio_all"]) == ("X_03", "X_01", 20.0)
    assert land.land_rows(led, aland, ratio=12.5)[0]["over"] is False
    assert land.summary("run", [a, b]) == ("run: 2 split groups, 1 with two pieces of 20% or more, "
                                           "1 beyond R = 10; X A 12.5")


def test_write_land():
    aland = {"a1": 100.0, "a2": 8.0}
    rows = land.land_rows(_ledger([("a1", "wh", "A", "X", "X_01", 1.0),
                                   ("a2", "wh", "A", "X", "X_02", 1.0)]), aland)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "land.csv")
        land.write_land(path, rows)
        with open(path, newline="") as fh:
            got = list(csv.reader(fh))
    assert got == [land.COLUMNS, ["X", "A", "2", "2", "12.50", "12.50", "X_01", "100.0", "X_02", "8.0",
                                  "1", "X_01:100.0:100%;X_02:8.0:100%"]]


def _grid_toy():
    """NY is a 4 × 3 grid of free ZCTAs of mass 1, CT's a0 (mass 2) on the left column and NJ's b0
    (4.6) on the right (`_finger_toy`'s), every edge 1 km; the left column holds 10 km² a ZCTA,
    the rest 1.  CT plans 7/12 of NY, NJ 5/12, both past `LAND_MIN_SHARE` of τ."""
    pts = [(x, y) for x in range(4) for y in range(3)]
    name = {q: f"v{q[0]}{q[1]}" for q in pts}
    edges = [(name[a], name[b]) for a in pts for b in pts
             if a < b and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
    edges += [("a0", name[0, y]) for y in range(3)] + [("b0", name[3, y]) for y in range(3)]
    xy = {name[q]: (float(q[0]), float(q[1])) for q in pts}
    xy.update({"a0": (-1.0, 1.0), "b0": (4.0, 1.0)})
    mass = dict.fromkeys(xy, 1.0)
    mass.update({"a0": 2.0, "b0": 4.6})
    inst, xym = tr._toy({"NY": [name[q] for q in pts], "CT": ["a0"], "NJ": ["b0"]}, edges, mass,
                        xy, {"NY": "free"}, k=2, delta=0.15, final_delta=0.15)
    plan = tr._plan(inst, [({"CT", "NY"}, {"CT": 1.0, "NY": 7 / 12}),
                           ({"NJ", "NY"}, {"NJ": 1.0, "NY": 5 / 12})])
    aland = {z: 10.0 if z.startswith("v0") else 1.0 for z in xy}
    return inst, xym, plan, aland


def _ny_land(inst, owner: dict, aland: dict) -> dict:
    out = {}
    for z in inst.units.zips["NY"]:
        out[owner[z]] = out.get(owner[z], 0.0) + aland[z]
    return out


def _brute(inst, plan, aland, ratio) -> tuple:
    """(least border, least |CT − NJ| land) over every connected drawing of NY in the band, the
    border among those within `ratio` both ways."""
    units, ch = inst.units, inst.channels["X"]
    adj, m = units.zip_adj, ch.m
    ny = sorted(units.zips["NY"])
    names = {next(iter(cp.support - {"NY"})): cp.name for cp in plan.copies}
    lo, hi = ch.tau * (1 - plan.delta), ch.tau * (1 + plan.delta)
    best, diff = float("inf"), float("inf")
    for mask in range(2 ** len(ny)):
        owner = {"a0": names["CT"], "b0": names["NJ"]}
        owner.update({z: names["CT"] if mask >> i & 1 else names["NJ"] for i, z in enumerate(ny)})
        mass = {}
        for z, j in owner.items():
            mass[j] = mass.get(j, 0.0) + m.get(z, 0.0)
        if not all(lo - 1e-9 <= x <= hi + 1e-9 for x in mass.values()) or len(mass) < 2:
            continue
        if any(len(draw.components({z for z in owner if owner[z] == j}, adj)) > 1 for j in mass):
            continue
        got = _ny_land(inst, owner, aland)
        a, b = got.get(names["CT"], 0.0), got.get(names["NJ"], 0.0)
        diff = min(diff, abs(a - b))
        if a <= ratio * b and b <= ratio * a:
            best = min(best, sum(1 for x in owner for y in adj[x] if x < y and owner[x] != owner[y]))
    return best, diff


def test_the_land_term_holds_the_in_state_ratio():
    """Without the term the least border gives CT both heavy columns (33 km² against 6, 5.5); at
    R = 2 the drawing is within R, its border the least of those within R and its excess 0; every
    seed drawing meets the land rows (none "breaks a row")."""
    inst, xy, plan, aland = _grid_toy()
    ct, nj = sorted(cp.name for cp in plan.copies)
    [g0] = draw.draw(inst, plan, xy, log=lambda *_: None).groups
    assert g0.status == "optimal" and g0.land_excess is None and g0.report()["land_excess"] is None
    assert _ny_land(inst, g0.owner, aland) == {ct: 33.0, nj: 6.0}
    lines = []
    res = draw.draw(inst, plan, xy, log=lines.append,
                    land={"aland": aland, "ratio": 2.0, "min_share": draw.LAND_MIN_SHARE})
    [g] = res.groups
    assert g.status == "optimal" and res.connected, (g.status, g.note)
    got = _ny_land(inst, g.owner, aland)
    assert got[ct] <= 2.0 * got[nj] and got[nj] <= 2.0 * got[ct], got
    assert abs(g.land_excess) < 1e-9 and g.report()["land_excess"] == g.land_excess
    assert g.border_km == _brute(inst, plan, aland, 2.0)[0] > g0.border_km
    assert not any("breaks a row" in line for line in lines), [l for l in lines if "breaks" in l]
    seq = draw.draw(inst, plan, xy, sequential=True, log=lambda *_: None,
                    land={"aland": aland, "ratio": 2.0, "min_share": draw.LAND_MIN_SHARE})
    [gs] = seq.groups                   # set125's `--sequential`: one unit, the same rows
    got = _ny_land(inst, seq.owner, aland)
    assert gs.status == "connected" and abs(gs.land_excess) < 1e-9 and got[ct] <= 2.0 * got[nj], got


def test_the_land_term_never_makes_a_group_infeasible():
    """R = 1 asks for equal land, which no drawing has: the group is still drawn, optimal, its
    excess that of its drawing (|CT − NJ| over NY's 39 km²); with `min_share` above both plans no
    pair counts and the excess is 0."""
    inst, xy, plan, aland = _grid_toy()
    ct, nj = sorted(cp.name for cp in plan.copies)
    [g0] = draw.draw(inst, plan, xy, log=lambda *_: None).groups
    [g] = draw.draw(inst, plan, xy, log=lambda *_: None,
                    land={"aland": aland, "ratio": 1.0, "min_share": 0.2}).groups
    assert g.status == "optimal"
    got = _ny_land(inst, g.owner, aland)
    assert abs(g.land_excess - abs(got[ct] - got[nj]) / 39.0) < 1e-9 and g.land_excess > 0
    assert _brute(inst, plan, aland, 1.0)[1] > 0
    [g2] = draw.draw(inst, plan, xy, log=lambda *_: None,
                     land={"aland": aland, "ratio": 1.0, "min_share": 0.9}).groups
    assert g2.status == "optimal" and g2.land_excess == 0.0 and g2.owner == g0.owner


def test_channels_drawn_in_parallel_carry_the_land_term():
    """`run.draw_parallel` passes `land` to each worker in the shared pickle (#123): the drawing
    is the in-process one, within R."""
    run = _module("contig_run", "run.py")
    inst, xy, plan, aland = _grid_toy()
    term = {"aland": aland, "ratio": 2.0, "min_share": draw.LAND_MIN_SHARE}
    seq = draw.draw(inst, plan, xy, log=lambda *_: None, land=term)
    par = run.draw_parallel(inst, {"X": plan}, xy, 2, log=False, land=term)
    assert par["X"].owner == seq.owner and abs(par["X"].groups[0].land_excess) < 1e-9


def test_land_term_reads_the_polygon_graph_in_km2():
    poly = {"aland": {"a": 2.5e6, "b": 0.0}}
    assert draw.land_term(poly, 10) == {"aland": {"a": 2.5, "b": 0.0}, "ratio": 10.0,
                                        "min_share": draw.LAND_MIN_SHARE}
