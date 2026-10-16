"""F4.W/F142.c conformance after #142 repair-engine and growth changes.
Agent: modeler (openai-codex/gpt-6-astra).

The windows go through the real `repair.solve_window` (both engines): it builds the group from the
instance, plan and map, and the test compares what it hands `draw._solve_group` (the ZCTAs, the fixed
owners, the bodies, the band, the holders it counts) with an expected group written here from the grid
and the plan alone, then solves that group with the F4.W specification.
"""
from __future__ import annotations

import math
from types import SimpleNamespace as NS
from unittest.mock import patch

import networkx as nx

from td.formulation import f4w
from tests import test_realize as tr
from tests.test_formulation import _solve, _production, _bad_point
from tests.test_contig_realize import _repair_module

quiet = lambda *_: None     # noqa: E731
WIDTH, HEIGHT = 10, 6
LO, HI = 27.0, 33.0         # tau = 60 / 2 = 30, final delta 0.1


def _scip(run, call, centres, assignment=None):
    """The same solve with SCIP in HiGHS's place: `run` is `solve_window` with engine "scip", which installs it."""
    repair = _repair_module()
    draw, engine = repair.draw, repair.scip_engine()
    original = engine.instance_of

    def instance(h, loc):
        assert h.getOptionValue("mip_rel_gap")[1] == 0.0
        if assignment is not None:
            for (z, j), i in loc["col"].items():
                value = float(assignment[z] == j)
                h.changeColBounds(i, value, value)
        return original(h, loc)

    def center_input(inst, c, v, support, p):
        return {j: centres[v, j] for j in support}

    with patch.object(engine, "instance_of", instance), \
            patch.object(draw.tdrealize, "centres", center_input), \
            patch.object(draw, "construct", lambda *a, **k: (None, "spec point test")):
        result = run()
    assert result.status in ("optimal", "infeasible"), result.report()
    return result


def _name(x, y):
    return f"z{x:02d}_{y:02d}"


def _world(units, owner, W, copies, cap, opened=(), target=None):
    """A 10 x 6 grid of mass 1 (K 2, tau 30, final band 27-33) cut into `units` {unit: [ZCTAs]}, drawn as `owner`,
    with the window `W` (`opened`: the ZCTAs `repair.py --open-units` opens): the real instance, plan and
    map for `repair.solve_window`, and the group expected of it, written from the grid, the owner map and the plan alone (`call`, F4.W's input), its geometric `centres`
    (each district's nearest-to-`target` ZCTA of the unit) and a `good` assignment of the window (`target`)."""
    pos = {_name(x, y): (float(x), float(y)) for x in range(WIDTH) for y in range(HEIGHT)}
    G = nx.Graph()
    G.add_nodes_from(pos)
    G.add_edges_from((a, b) for a in pos for b in pos if a < b and
                     abs(pos[a][0] - pos[b][0]) + abs(pos[a][1] - pos[b][1]) == 1)
    mass = dict.fromkeys(pos, 1.0)
    inst, _ = tr._toy(units, sorted(G.edges()), mass, pos, k=2, delta=0.1, final_delta=0.1)
    plan = tr._plan(inst, copies)
    names = [c.name for c in plan.copies]
    unit_of = {z: v for v, zs in units.items() for z in zs}
    # the expected group
    fixed = {z: owner[z] for z in pos if z not in W}
    bodies = {j: sorted((frozenset(cc) for cc in nx.connected_components(
        G.subgraph([z for z in fixed if fixed[z] == j]))), key=lambda cc: (-len(cc), min(cc))) for j in names}
    held = {v: {owner[z] for z in zs} for v, zs in units.items()}
    target = target or owner
    centres = {(v, j): pos[min(z for z in zs if target[z] == j)] for v, zs in units.items()
               for j in names if any(target[z] == j for z in zs)}
    zs = sorted(W)
    call = dict(c="X", zs=zs, allowed={z: list(names) for z in zs}, bodies=bodies,
                body_of={z: (j, i) for j, bs in bodies.items() for i, b in enumerate(bs) for z in b},
                fixed=fixed, adj={z: set(G[z]) for z in G}, m=mass, p=pos, unit_of=unit_of,
                hold={v: sorted(j for j in names if (v, j) in centres or j in held[v]) for v in units},
                plan=NS(copies=[NS(name=n, total=0.0) for n in names]), planned={}, support={},
                inst=NS(channels={"X": NS(tau=30.0, M={}, m=mass)}, units=NS(zips=units, unit_of=unit_of)),
                lo=LO, hi=HI, arm="arm1", fixed_targets=False, time_limit=90.0, log=quiet, dag=False,
                flow=False, border=None, land=None,
                count={"cap": cap, "current": {v: set(js) for v, js in held.items() if v in {unit_of[z] for z in W}},
                       "opened": {unit_of[z] for z in W & set(opened)}})
    good = {z: target[z] for z in zs}
    return NS(inst=inst, plan=plan, owner=owner, W=set(W), p=pos, cap=cap, opened=frozenset(opened), names=names,
              call=call, centres=centres, good=good)


def _expect_group(world, run):
    """Run `run` while recording the group `solve_window` hands `draw._solve_group`; assert it is the expected one."""
    repair = _repair_module()
    draw, seen, original = repair.draw, [], repair.draw._solve_group

    def spy(*a, **k):
        seen.append((a, k))
        return original(*a, **k)

    with patch.object(draw, "_solve_group", spy):
        result = run()
    assert seen, "solve_window never reached draw._solve_group"
    c = world.call
    for a, k in seen:
        (name, zs, allowed, bodies, body_of, outside, adj, m, p, unit_of, hold, plan, planned, support, inst, lo, hi,
         arm, fixed_targets, limit, log, extra) = a[:22]
        assert name == "X" and list(zs) == c["zs"] and outside == c["fixed"]
        assert {z: sorted(js) for z, js in allowed.items()} == {z: sorted(js) for z, js in c["allowed"].items()}
        assert {j: sorted(sorted(b) for b in bs) for j, bs in bodies.items()} == \
            {j: sorted(sorted(b) for b in bs) for j, bs in c["bodies"].items()}
        assert body_of == c["body_of"] and unit_of == c["unit_of"]
        assert (lo, hi) == (LO, HI) and math.isclose(lo, 30 * 0.9) and math.isclose(hi, 30 * 1.1)
        assert {j: sorted(js) for j, js in hold.items()} == {v: sorted(js) for v, js in c["hold"].items()}
        assert not any(extra.get(j) for j in world.names)
        assert k["count"] == c["count"], (k["count"], c["count"])
    return result


def _via_repair(world, engine, assignment=None):
    repair = _repair_module()

    def run():
        return repair.solve_window(world.inst, world.plan, world.owner, world.W, world.p, 60.0, world.cap,
                                   log=quiet, opened=world.opened, engine=engine)
    checked = lambda: _expect_group(world, run)     # noqa: E731
    if engine == "scip":
        return _scip(checked, world.call, world.centres, assignment)
    return _production(world.call, world.centres, assignment, run=checked)


def _window(width):
    """The whole grid is unit NY, drawn A = left five columns, B = the right five; the window is the
    2 * width columns around the middle."""
    U = [_name(x, y) for x in range(WIDTH) for y in range(HEIGHT)]
    names = ("NY#1", "NY#2")
    owner = {z: names[0] if int(z[1:3]) < 5 else names[1] for z in U}
    W = {z for z in U if 5 - width <= int(z[1:3]) < 5 + width}
    return _world({"NY": U}, owner, W, [({"NY"}, {"NY": 0.5}), ({"NY"}, {"NY": 0.5})], cap=True)


def _cap_world(cap, opened):
    """NY (columns 0-7, 48 ZCTAs) is A's alone, CT (columns 8-9) is B's: the band (27-33) forces B into U,
    a second holder of NY; the window is NY's columns 3-7."""
    U = [_name(x, y) for x in range(8) for y in range(HEIGHT)]
    PB = [_name(x, y) for x in (8, 9) for y in range(HEIGHT)]
    a, b = "NY#1", "CT+NY#1"
    owner = {**dict.fromkeys(U, a), **dict.fromkeys(PB, b)}
    W = {z for z in U if int(z[1:3]) >= 3}
    target = {**{z: a if int(z[1:3]) < 5 else b for z in U}, **dict.fromkeys(PB, b)}
    return _world({"NY": U, "CT": PB}, owner, W,
                  [({"NY"}, {"NY": 0.5}), ({"CT", "NY"}, {"CT": 1.0, "NY": 0.5})], cap,
                  opened=W if opened else (), target=target)


def test_formulation_repair_three_nested_windows_both_engines():
    previous = None
    for width in (1, 2, 3):
        world = _window(width)
        call, centres, good, names = world.call, world.centres, world.good, world.names
        d = f4w.prepare(call, centres=centres)
        spec_status, optimum = _solve(f4w.build_model(d))
        assert spec_status == "optimal"
        for engine in ("highs", "scip"):
            actual = _via_repair(world, engine)
            assert actual.status == spec_status
            assert abs(actual.objective - optimum) < 2e-6
            bad = dict.fromkeys(good, names[0]) if width == 1 else _bad_point(call, good)
            for point, verdict in ((good, "optimal"), (bad, "infeasible")):
                expected, value = _solve(f4w.build_model(d), point)
                got = _via_repair(world, engine, point)
                assert expected == got.status == verdict
                if value is not None:
                    assert abs(got.objective - value) < 2e-6
        owner = {**call["fixed"], **good}
        domain = f4w.assignment_domain(owner, names, owner, call["zs"])
        if previous is not None:
            assert previous < domain
        previous = domain
        print(f"  FORMULATION F4.W: 60 vertices, |W|={len(call['zs'])}, spec=HiGHS=SCIP {optimum:.9f}")


def test_formulation_repair_cap_and_opened_unit_verdicts():
    # The band requires two holders of this unit (NY is A's alone on the map). A cap allowing no original
    # split is infeasible; opening the unit or removing the cap permits it.
    for cap, opened, expected in ((True, False, "infeasible"),
                                  (True, True, "optimal"), (False, False, "optimal")):
        world = _cap_world(cap, opened)
        assert world.call["count"]["current"] == {"NY": {"NY#1"}}
        verdict, value = _solve(f4w.build_model(f4w.prepare(world.call, centres=world.centres)), world.good)
        assert verdict == expected
        for engine in ("highs", "scip"):
            actual = _via_repair(world, engine, world.good)
            assert actual.status == expected
            if value is not None:
                assert abs(actual.objective - value) < 2e-6


def test_formulation_growth_domain_and_proof_gate():
    # This 60-vertex path has an independently specified adjacent-district ring.
    from tests.test_repair_scip import _line, _run, _race_run
    repair = _repair_module()
    inst, plan, owner, free, state, pieces = _line()
    adj = inst.units.zip_adj
    W = {f"z{i:02d}" for i in range(11)}
    expected_ring = {f"z{i:02d}" for i in range(20, 30)}  # C adjacent to A/B
    steps = repair.grow_windows(pieces, owner, W, free, adj, 3, 3, 60)
    assert steps[0][0] == "grow-adjacent" and steps[0][2] == W | expected_ring
    assert any(shape == "grow-wider" for shape, _, _ in steps)
    for _, _, enlarged in steps:
        assert W < enlarged and len(enlarged) <= 60
        assert f4w.assignment_domain(owner, set(owner.values()), owner, W) < \
            f4w.assignment_domain(owner, set(owner.values()), owner, enlarged)
        W = enlarged
    for cap in (11, 14, 25, 60):
        for limit in (0, 1, 2, 3):
            initial = {f"z{i:02d}" for i in range(11)}
            got = repair.grow_windows(pieces, owner, initial, free, adj, 3, limit, cap)
            # On this path nearest-first C vertices are z20,z21,...; no production
            # neighborhood or hop routine supplies this expected adjacent ring.
            ring = sorted(expected_ring)[:max(0, cap - len(initial))]
            candidates = [ring] + [V for _, _, V in repair.steps(pieces, owner, free, adj, 3, cap)]
            expected = f4w.growth_sequence(initial, candidates, limit=limit, cap=cap)
            assert [frozenset(s[2]) for s in got] == expected
            assert len(got) <= limit and all(len(s[2]) <= cap for s in got)
    for status in ("infeasible", "unknown", "connected", "optimal"):
        expected = f4w.growth_permitted(status, uncapped=True)
        for runner in (lambda: _run(repair, lambda W: status, (3, 60))[0],
                       lambda: _race_run(repair, lambda W: status, (3, 60))):
            attempts = runner()
            assert any(a["shape"].startswith("grow") for a in attempts) == expected
        for cap in (False, True):
            last = ("ball", 3, {"z00"}, cap)
            record = dict(status=status, cap=cap, shape="ball", window_zctas=1)
            assert repair.proved_infeasible([record], last) == \
                f4w.growth_permitted(status, uncapped=not cap)


def test_formulation_growth_unions_skip_over_cap_without_spending_steps():
    """60 vertices: an over-cap proposal must not hide later smaller fitting unions."""
    from tests.test_repair_scip import _line
    repair = _repair_module()
    inst, plan, owner, free, state, pieces = _line()
    W = {f"z{i:02d}" for i in range(11)}
    ring = {f"z{i:02d}" for i in range(20, 30)}
    proposals = [W | {f"z{i:02d}" for i in range(11, 16)},  # union 26: over cap
                 {"z11"},                                # union 22, candidate only 1
                 W,                                      # no growth: no step spent
                 {"z12", "z13"},                         # union 24
                 {"z14"}]                                # union 25, if budget remains
    explicit = [W | ring, W | ring | {"z11"},
                W | ring | {"z11", "z12", "z13"},
                W | ring | {"z11", "z12", "z13", "z14"}]
    for limit in (0, 1, 2, 3, 4):
        expected = f4w.growth_sequence(W, [ring, *proposals], limit=limit, cap=25)
        assert expected == explicit[:limit]
        with patch.object(repair, "steps", return_value=[("ball", i, V) for i, V in enumerate(proposals)]):
            got = repair.grow_windows(pieces, owner, W, free, inst.units.zip_adj, 3, limit, 25)
        assert [frozenset(V) for _, _, V in got] == expected
        assert [k for _, k, _ in got] == list(range(1, len(expected) + 1))
        previous = W
        for enlarged in expected:
            assert f4w.assignment_domain(owner, set(owner.values()), owner, previous) < \
                f4w.assignment_domain(owner, set(owner.values()), owner, enlarged)
            previous = enlarged
