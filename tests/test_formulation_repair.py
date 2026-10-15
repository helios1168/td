"""F4.W/F142.c conformance after #142 repair-engine and growth changes.
Agent: modeler (openai-codex/gpt-6-astra).
"""
from __future__ import annotations

from unittest.mock import patch

import networkx as nx

from td.formulation import f4w
from tests.test_formulation import _call, _solve, _production, _bad_point
from tests.test_contig_realize import _repair_module


def _scip(call, centres, assignment=None):
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

    with engine.installed(draw), patch.object(engine, "instance_of", instance), \
            patch.object(draw.tdrealize, "centres", center_input), \
            patch.object(draw, "construct", lambda *a, **k: (None, "spec point test")):
        result = draw._solve_group(**call)
    assert result.status in ("optimal", "infeasible"), result.report()
    return result


def _window(width, cap=True, opened=False, current=("A", "B")):
    grid = nx.grid_2d_graph(10, 6)
    labels = {(x, y): f"z{x:02d}_{y:02d}" for x, y in grid}
    pos = {labels[x, y]: (float(x), float(y)) for x, y in grid}
    G = nx.relabel_nodes(grid, labels)
    owner = {z: "A" if x < 5 else "B" for z, (x, _) in pos.items()}
    W = {z for z, (x, _) in pos.items() if 5 - width <= x < 5 + width}
    fixture = _call(G, pos, dict.fromkeys(G, 1.0),
                    fixed={z: j for z, j in owner.items() if z not in W}, known=owner)
    call, centres, good = fixture
    call["count"] = {"cap": cap, "current": {"U": set(current)},
                     "opened": {"U"} if opened else set()}
    return call, centres, good


def test_formulation_repair_three_nested_windows_both_engines():
    previous = None
    for width in (1, 2, 3):
        call, centres, good = _window(width)
        d = f4w.prepare(call, centres=centres)
        spec_status, optimum = _solve(f4w.build_model(d))
        assert spec_status == "optimal"
        for run in (_production, _scip):
            actual = run(call, centres)
            assert actual.status == spec_status
            assert abs(actual.objective - optimum) < 2e-6
            bad = dict.fromkeys(good, "A") if width == 1 else _bad_point(call, good)
            for point, verdict in ((good, "optimal"), (bad, "infeasible")):
                expected, value = _solve(f4w.build_model(d), point)
                got = run(call, centres, point)
                assert expected == got.status == verdict
                if value is not None:
                    assert abs(got.objective - value) < 2e-6
        owner = {**call["fixed"], **good}
        domain = f4w.assignment_domain(owner, ("A", "B"), owner, call["zs"])
        if previous is not None:
            assert previous < domain
        previous = domain
        print(f"  FORMULATION F4.W: 60 vertices, |W|={len(call['zs'])}, spec=HiGHS=SCIP {optimum:.9f}")


def test_formulation_repair_cap_and_opened_unit_verdicts():
    # The band requires two holders of this unit. A cap allowing no original
    # split is infeasible; opening the unit or removing the cap permits it.
    for cap, opened, expected in ((True, False, "infeasible"),
                                  (True, True, "optimal"), (False, False, "optimal")):
        call, centres, good = _window(5, cap, opened, current=("A",))
        verdict, value = _solve(f4w.build_model(f4w.prepare(call, centres=centres)), good)
        assert verdict == expected
        for run in (_production, _scip):
            actual = run(call, centres, good)
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
