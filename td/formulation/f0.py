"""F0, docs/F0.tex: one fixed routing structure, exact supplied neck family.

The caller supplies the *complete* nonexempt forbidden ownership-set family and
symbolic shape/balance evaluators. No geometry oracle or owner policy is invented.
The three objectives are ordered, not scalarized; activate one at a time and fix
previous objective values for lexicographic optimization. GDP is left untransformed.
Agent: modeler (openai-codex/gpt-6-astra).
"""
from __future__ import annotations

import pyomo.environ as pyo
from pyomo.gdp import Disjunct, Disjunction

WINDOWS = {"national": (1000, 1437.5), "WH": (850, 1150),
           "FI": (765, 1035), "WIFI": (850, 1150)}


def build_model(*, Z, F, rho, m, rates, state, E_P, manhattan, forbidden, shape, balance):
    """Build F0 for |H|=1; dollars in millions, J=1..54 and total K=48..54.

    rho[(z,f)] is a channel in WINDOWS; m[(z,f)] is descaled opportunity.
    manhattan explicitly identifies Manhattan ZCTAs in Z (empty on a toy with none).
    forbidden[c] must explicitly list all nonexempt neck-failing sets for that
    channel footprint (an empty list asserts none). shape(model), balance(model)
    return symbolic expressions: they are instance inputs, not settled policies.
    """
    Z, F, manhattan = tuple(Z), tuple(F), frozenset(manhattan)
    if not manhattan <= set(Z):
        raise ValueError("Manhattan ZCTAs must belong to the explicit vertex set")
    if not 1 <= len(Z) <= 300:
        raise ValueError("F0 specification requires 1..300 explicit ZCTAs")
    if set(rho) != {(z, f) for z in Z for f in F}:
        raise ValueError("routing must cover exactly Z x F")
    channels = sorted(set(rho.values()))
    if set(channels) - WINDOWS.keys() or set(forbidden) != set(channels):
        raise ValueError("unknown channel or missing complete forbidden-set family")
    footprints = {c: [z for z in Z if any(rho[z, f] == c for f in F)] for c in channels}
    B = {c: [frozenset(b) for b in forbidden[c]] for c in channels}
    if any(not b or not b <= set(footprints[c]) for c in channels for b in B[c]):
        raise ValueError("forbidden ownership sets must be nonempty footprint subsets")
    M = pyo.ConcreteModel(name="F0")
    M.H = pyo.Set(initialize=["fixed"])
    M.Z = pyo.Set(initialize=Z, ordered=True)
    M.Manhattan = pyo.Set(within=M.Z, initialize=sorted(manhattan))
    M.F = pyo.Set(initialize=F)
    M.C = pyo.Set(initialize=channels)
    M.J = pyo.RangeSet(1, 54)
    M.Z_hc = pyo.Set(M.H, M.C, initialize=lambda _, h, c: footprints[c])
    M.S = pyo.Set(initialize=sorted({state[z] for z in Z}))
    M.s = pyo.Param(M.Z, initialize=state, within=pyo.Any)
    M.rho = pyo.Param(M.Z, M.F, initialize=rho, within=pyo.Any)
    M.m = pyo.Param(M.Z, M.F, initialize=m, within=pyo.NonNegativeReals)
    M.r_rate = pyo.Param(M.F, initialize=rates, within=pyo.NonNegativeReals)
    M.HCZ = pyo.Set(dimen=3, initialize=[("fixed", c, z) for c in channels for z in footprints[c]])
    M.d = pyo.Param(M.HCZ, initialize=lambda _, h, c, z:
                    sum(rates[f] * m[z, f] for f in F if rho[z, f] == c))
    M.L = pyo.Param(M.C, initialize={c: WINDOWS[c][0] for c in channels})
    M.U = pyo.Param(M.C, initialize={c: WINDOWS[c][1] for c in channels})
    M.HCJZ = pyo.Set(dimen=4, initialize=[(h, c, j, z) for h, c, z in M.HCZ for j in M.J])
    M.q = pyo.Var(M.H, domain=pyo.Binary)
    M.y = pyo.Var(M.H, M.C, M.J, domain=pyo.Binary)
    M.x = pyo.Var(M.HCJZ, domain=pyo.Binary)
    M.b = pyo.Var(M.H, M.C, M.J, M.S, domain=pyo.Binary)
    M.w = pyo.Var(M.H, M.C, M.J, domain=pyo.Binary)
    M.r = pyo.Var(M.HCJZ, domain=pyo.Binary)
    M.t = pyo.Var(M.HCJZ, domain=pyo.Binary)
    M.p = pyo.Var(M.H, M.C, M.S, domain=pyo.Binary)
    M.structure = pyo.Constraint(expr=sum(M.q.values()) == 1)
    M.activation = pyo.Constraint(M.H, M.C, M.J, rule=lambda t, h, c, j: t.y[h, c, j] <= t.q[h])
    M.coverage = pyo.Constraint(M.HCZ, rule=lambda t, h, c, z:
                                sum(t.x[h, c, j, z] for j in t.J) == t.q[h])
    M.owns_active = pyo.Constraint(M.HCJZ, rule=lambda t, h, c, j, z: t.x[h, c, j, z] <= t.y[h, c, j])
    M.nonempty = pyo.Constraint(M.H, M.C, M.J, rule=lambda t, h, c, j:
                                sum(t.x[h, c, j, z] for z in t.Z_hc[h, c]) >= t.y[h, c, j])
    M.K = pyo.Expression(M.H, M.C, rule=lambda t, h, c: sum(t.y[h, c, j] for j in t.J))
    M.channel_count = pyo.Constraint(M.H, M.C, rule=lambda t, h, c: t.K[h, c] >= t.q[h])
    M.total_count = pyo.Constraint(expr=pyo.inequality(48, sum(M.K.values()), 54))
    M.D = pyo.Expression(M.H, M.C, M.J, rule=lambda t, h, c, j:
                         sum(t.d[h, c, z] * t.x[h, c, j, z] for z in t.Z_hc[h, c]))
    M.window_lo = pyo.Constraint(M.H, M.C, M.J, rule=lambda t, h, c, j:
                                 t.D[h, c, j] >= t.L[c] * t.y[h, c, j])
    M.window_hi = pyo.Constraint(M.H, M.C, M.J, rule=lambda t, h, c, j:
                                 t.D[h, c, j] <= t.U[c] * t.y[h, c, j] + (450 * t.w[h, c, j] if c == "WIFI" else 0))
    M.touch = pyo.Constraint(M.HCJZ, rule=lambda t, h, c, j, z: t.x[h, c, j, z] <= t.b[h, c, j, state[z]])
    M.incidence = pyo.Constraint(M.H, M.C, M.J, M.S, rule=lambda t, h, c, j, s:
                                 t.b[h, c, j, s] <= sum(t.x[h, c, j, z] for z in t.Z_hc[h, c] if state[z] == s))
    M.cap_active = pyo.Constraint(M.H, M.C, M.J, rule=lambda t, h, c, j: t.w[h, c, j] <= t.y[h, c, j])
    for h in M.H:
        for c in M.C:
            if c != "WIFI":
                for j in M.J:
                    M.w[h, c, j].fix(0)
    M.WIFI = pyo.Set(dimen=3, initialize=[(h, c, j) for h in M.H for c in M.C if c == "WIFI" for j in M.J])

    def ordinary(d, h, c, j):
        d.no_allowance = pyo.Constraint(expr=M.w[h, c, j] == 0)

    def whole(d, h, c, j):
        d.allowance = pyo.Constraint(expr=M.w[h, c, j] == 1)
        d.owns_touched_state = pyo.Constraint(M.Z_hc[h, c], rule=lambda _, z:
                                             M.x[h, c, j, z] >= M.b[h, c, j, state[z]])

    M.ordinary = Disjunct(M.WIFI, rule=ordinary)
    M.whole = Disjunct(M.WIFI, rule=whole)
    M.wifi_cap = Disjunction(M.WIFI, rule=lambda t, h, c, j: [t.ordinary[h, c, j], t.whole[h, c, j]])
    arcs = sorted({(u, v) for a, b in E_P for u, v in ((a, b), (b, a))})
    M.E_P = pyo.Set(dimen=2, initialize=arcs)
    M.HCJA = pyo.Set(dimen=5, initialize=[(h, c, j, u, v) for h in M.H for c in M.C
                     for j in M.J for u, v in arcs if u in footprints[c] and v in footprints[c]])
    M.f = pyo.Var(M.HCJA, domain=pyo.NonNegativeReals)
    M.root_count = pyo.Constraint(M.H, M.C, M.J, rule=lambda t, h, c, j:
                                 sum(t.r[h, c, j, z] for z in t.Z_hc[h, c]) == t.y[h, c, j])
    M.root_owned = pyo.Constraint(M.HCJZ, rule=lambda t, h, c, j, z: t.r[h, c, j, z] <= t.x[h, c, j, z])
    M.manhattan_root_count = pyo.Constraint(M.H, M.C, M.J, rule=lambda t, h, c, j:
        sum(t.t[h, c, j, z] for z in t.Z_hc[h, c]) <= t.y[h, c, j])
    M.manhattan_root_owned = pyo.Constraint(M.HCJZ, rule=lambda t, h, c, j, z:
        t.t[h, c, j, z] <= t.x[h, c, j, z])
    for h, c, j, z in M.HCJZ:
        if z not in M.Manhattan:
            M.t[h, c, j, z].fix(0)
    M.flow_tail = pyo.Constraint(M.HCJA, rule=lambda t, h, c, j, u, v:
                                t.f[h, c, j, u, v] <= (len(t.Z_hc[h, c]) - 1) * t.x[h, c, j, u])
    M.flow_head = pyo.Constraint(M.HCJA, rule=lambda t, h, c, j, u, v:
                                t.f[h, c, j, u, v] <= (len(t.Z_hc[h, c]) - 1) * t.x[h, c, j, v])
    M.flow_balance = pyo.Constraint(M.HCJZ, rule=lambda t, h, c, j, z:
        sum(t.f[h, c, j, u, z] for u, v in arcs if v == z and (h, c, j, u, z) in t.HCJA)
        - sum(t.f[h, c, j, z, v] for u, v in arcs if u == z and (h, c, j, z, v) in t.HCJA)
        >= t.x[h, c, j, z] - len(t.Z_hc[h, c]) * (t.r[h, c, j, z] + t.t[h, c, j, z]))
    M.B = pyo.Set(dimen=3, initialize=[(h, c, i) for h in M.H for c in M.C for i in range(len(B[c]))])
    M.neck = pyo.Constraint(M.B, M.J, rule=lambda t, h, c, i, j:
        sum(1 - t.x[h, c, j, z] for z in B[c][i])
        + sum(t.x[h, c, j, z] for z in t.Z_hc[h, c] if z not in B[c][i]) >= t.y[h, c, j])
    M.R = pyo.Expression(M.H, M.C, M.S, rule=lambda t, h, c, s: sum(t.b[h, c, j, s] for j in t.J))
    M.split_lo = pyo.Constraint(M.H, M.C, M.S, rule=lambda t, h, c, s: 2 * t.p[h, c, s] <= t.R[h, c, s])
    M.split_hi = pyo.Constraint(M.H, M.C, M.S, rule=lambda t, h, c, s: t.R[h, c, s] <= t.q[h] + 53 * t.p[h, c, s])
    M.Phi_shape = pyo.Expression(expr=shape(M))
    M.Phi_balance = pyo.Expression(expr=balance(M))
    M.shape_objective = pyo.Objective(expr=M.Phi_shape)
    M.balance_objective = pyo.Objective(expr=M.Phi_balance)
    M.splits_objective = pyo.Objective(expr=sum(M.p.values()))
    M.balance_objective.deactivate()
    M.splits_objective.deactivate()
    return M
