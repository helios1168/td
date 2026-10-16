"""F2.W: whole-unit fixed-window master, not an F0 optimizer.

Reduction assumes connected nonempty units, positive unit mass, 0 < eta <= 1,
and no contact cap below one. Fixed family and bans are inputs, not M1 evidence.
Agent: modeler (openai-codex/gpt-6-astra).
"""
import pyomo.environ as pyo


def build_model(*, unit_zips, mass, family, weights, k, lo, hi, banned=()):
    """Small whole-unit set partition model; mass is per ZIP, weights per support."""
    zips = [z for zs in unit_zips.values() for z in zs]
    if not 1 <= len(zips) <= 300 or len(set(zips)) != len(zips):
        raise ValueError('F2.W requires disjoint nonempty units and at most 300 ZIPs')
    if any(not zs or sum(mass[z] for z in zs) <= 0 for zs in unit_zips.values()):
        raise ValueError('F2.W requires nonempty positive-mass units')
    family = tuple(frozenset(s) for s in family)
    banned = set(map(frozenset, banned))
    m = pyo.ConcreteModel(name='F2.W')
    m.Z = pyo.Set(initialize=zips)
    m.V = pyo.Set(initialize=sorted(unit_zips))
    m.S = pyo.Set(initialize=range(len(family)))
    m.a = pyo.Param(m.V, m.S, initialize=lambda m, v, s: int(v in family[s]))
    m.M = pyo.Param(m.V, initialize={v: sum(mass[z] for z in zs) for v, zs in unit_zips.items()})
    m.w = pyo.Param(m.S, initialize={s: weights[f] for s, f in enumerate(family)})
    m.b = pyo.Param(m.S, initialize={s: int(f in banned) for s, f in enumerate(family)})
    m.K = pyo.Param(initialize=k)
    m.L = pyo.Param(initialize=lo)
    m.U = pyo.Param(initialize=hi)
    tau = sum(mass[z] for z in zips) / k
    m.delta_w = pyo.Param(initialize=max(1 - lo / tau, hi / tau - 1))
    # Fixed-window feasibility never supplies a smallest-delta certificate.
    m.minimum_delta_certificate = pyo.Param(initialize=0, within=pyo.Binary)
    m.n = pyo.Var(m.S, domain=pyo.Binary)
    m.count = pyo.Constraint(expr=sum(m.n[s] for s in m.S) == m.K)
    m.cover = pyo.Constraint(m.V, rule=lambda m, v: sum(m.a[v, s] * m.n[s] for s in m.S) == 1)
    m.band_lo = pyo.Constraint(m.S, rule=lambda m, s: sum(m.M[v] * m.a[v, s] for v in m.V) * m.n[s] >= m.L * m.n[s])
    m.band_hi = pyo.Constraint(m.S, rule=lambda m, s: sum(m.M[v] * m.a[v, s] for v in m.V) * m.n[s] <= m.U * m.n[s])
    m.ban = pyo.Constraint(m.S, rule=lambda m, s: m.n[s] <= 1 - m.b[s])
    m.objective = pyo.Objective(expr=sum(m.w[s] * m.n[s] for s in m.S))
    return m
