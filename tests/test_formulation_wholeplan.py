"""F2.W whole-unit window reduction and certificate on 30 ZCTAs.
Agent: modeler (openai-codex/gpt-6-astra).
"""
import math

import pyomo.environ as pyo

from td import master, supports
from td.formulation import f2w
from tests.test_master import _toy
from tests.test_wholeplan import _wholeplan


def _instance(lo, hi):
    units = {v: [f'{v}{i:02d}' for i in range(10)] for v in ('PA', 'NY', 'NJ')}
    zs = sum(units.values(), [])
    edges = list(zip(zs, zs[1:]))
    # NY is much lighter than either neighbour; neither singleton alone fits the narrow window.
    mass = {z: (1 / 320 if v == 'NY' else 1 / 10) for v, vv in units.items() for z in vv}
    xy = {z: (base + i, 0.0) for v, base in [('PA', 0), ('NY', 20), ('NJ', 100)]
          for i, z in enumerate(units[v])}
    inst = _toy(units, edges, mass, xy, k=2, mode='whole', band_lo=lo, band_hi=hi)
    polygon = dict(vertices=zs, edges=edges, border=dict.fromkeys(edges, 30000.0), connectors=[],
                   state=dict(inst.units.unit_of), aland=dict.fromkeys(zs, 1e8))
    return inst, polygon


def _symbolic(inst, family, banned=()):
    ch = inst.channels['X']
    # Independently computed diameters, not production objective coefficients.
    centers = {'PA': (4.5, 0.0), 'NY': (24.5, 0.0), 'NJ': (104.5, 0.0)}
    weights = {s: max(math.dist(centers[u], centers[v]) for u in s for v in s)
               for s in family.supports}
    return f2w.build_model(unit_zips=inst.units.zips, mass=ch.m, family=family.supports,
                          weights=weights, k=2, lo=ch.tau * ch.spec.band_lo,
                          hi=ch.tau * ch.spec.band_hi, banned=banned)


def _solve(model):
    solver = pyo.SolverFactory('highs')
    solver.options.update({'mip_rel_gap': 0.0, 'mip_abs_gap': 0.0})
    result = solver.solve(model, load_solutions=False)
    term = result.solver.termination_condition
    if term == pyo.TerminationCondition.infeasible:
        return 'infeasible', None
    assert term == pyo.TerminationCondition.optimal, term
    model.solutions.load_from(result)
    return 'optimal', pyo.value(model.objective)


def test_formulation_whole_unit_window_optimum_and_points_30():
    # tau = 65/64: the middle window puts masses 1 and 33/32 exactly on its endpoints.
    for lo, hi in ((0.9, 1.123456), (64 / 65, 66 / 65), (0.999, 1.001)):
        inst, polygon = _instance(lo, hi)
        fam = supports.family(inst, 'X')
        for banned in ((), (frozenset({'PA', 'NY'}),)):
            production = master.build(inst, 'X', fam=fam, banned=banned)
            actual = master.solve(production, mip_rel_gap=0.0)
            symbolic = _symbolic(inst, fam, banned)
            status, objective = _solve(symbolic)
            assert actual.status == status
            if status == 'optimal':
                assert math.isclose(actual.objective, objective, abs_tol=1e-8)
            # Two partitions and one under-covering point; test both actual matrices at each point.
            for selected in (({'PA', 'NY'}, {'NJ'}), ({'PA'}, {'NY', 'NJ'}), ({'PA'}, {'NJ'})):
                selected = set(map(frozenset, selected))
                point = _symbolic(inst, fam, banned)
                for i, s in enumerate(fam.supports):
                    point.n[i].fix(int(s in selected))
                symbolic_feasible = _solve(point)[0] == 'optimal'
                x = [0.0] * len(production.cost)
                for s, col in production.n_col.items():
                    x[col] = int(s in selected)
                for (v, s), col in production.t_col.items():
                    x[col] = int(s in selected)
                assert symbolic_feasible == (not master.violations(production, x))
        # The real wholeplan loop uses the same fixed window and raw-gate geometry.
        result = _wholeplan().loop(inst, 'X', polygon, log=lambda *_: None)
        feasible = lo != 0.999
        assert result['status'] == ('passed' if feasible else 'no plan'), result
        reference = _symbolic(inst, fam)
        assert pyo.value(reference.minimum_delta_certificate) == 0
        for rec in result['rounds']:
            assert rec['delta_method'] == 'window' and rec['exact_delta'] is None
            assert rec['delta_status'] == ('converged' if feasible else 'infeasible')
        if feasible:
            expected_delta = max(1 - lo, hi - 1)
            assert result['delta'] == expected_delta
            assert math.isclose(result['delta'], pyo.value(reference.delta_w), abs_tol=1e-12)
            assert result['rounds'][0]['window_feasible'] is True
            assert result['report']['mip_rel_gap'] == 0.0
            _, optimum = _solve(_symbolic(inst, fam))
            assert math.isclose(result['plan'].objective, optimum, abs_tol=1e-8)
        else:
            assert result['plan'] is None
