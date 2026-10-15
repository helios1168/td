"""F4, MODEL.md §4.1: complete group model (no DAG, neck or repair-count rows).

Parameter preparation is independent of draw.py: NetworkX supplies shortest paths;
centres are supplied F7 inputs. Rows/objective are named mathematical components.
Connectivity uses an extended flow formulation, including rootless/empty districts.
Agent: modeler (openai-codex/gpt-6-astra).
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import networkx as nx
import pyomo.environ as pyo


def prepare(call, *, centres):
    """Translate the inputs of draw._solve_group, not its matrix or solution.

    `centres[(v,j)]` are fixed geometric inputs. Pruning precedes objective
    normalization, as in F4. Unsupported variants fail rather than lose rows.
    """
    if call.get("dag") or call.get("count") is not None or call.get("necks") is not None:
        raise ValueError("F4 spec excludes DAG, repair counts and neck callbacks")
    zs = tuple(call["zs"])
    bodies, fixed, adj = call["bodies"], call["fixed"], call["adj"]
    unit, mass, pos = call["unit_of"], call["m"], call["p"]
    unit_zips = call["inst"].units.zips
    ch = call["inst"].channels[call["c"]]
    js = sorted({j for z in zs for j in call["allowed"][z]})
    total_zips = set(zs) | {z for j in js for b in bodies.get(j, ()) for z in b}
    if not 1 <= len(total_zips) <= 300:
        raise ValueError("F4 specification requires 1..300 ZCTAs, including bodies")
    bnodes = {j: tuple(f"@{j}#{i}" for i in range(len(bodies.get(j, ())))) for j in js}
    body_of = {z: bnodes[j][i] for j in js for i, b in enumerate(bodies.get(j, ())) for z in b}
    body_owner = {b: j for j in js for b in bnodes[j]}
    G = nx.Graph()
    G.add_nodes_from(zs)
    G.add_nodes_from(body_owner)
    for z in zs:
        for w in adj[z]:
            if w in zs:
                G.add_edge(z, w)
            elif w in body_of:
                G.add_edge(z, body_of[w])
    F_j = {j: math.fsum(mass.get(z, 0) for b in bodies.get(j, ()) for z in b)
           + (call.get("extra") or {}).get(j, 0) for j in js}
    lo, hi = call["lo"], call["hi"]
    A = {z: set(call["allowed"][z]) for z in zs}
    # Valid path/component pruning; do not normalize the moment over removed pairs.
    for j in js:
        mine = {z for z in zs if j in A[z]}
        gj = G.subgraph(mine | set(bnodes[j]))
        if bnodes[j]:
            lengths = nx.single_source_dijkstra_path_length(
                gj, bnodes[j][0], weight=lambda a, b, _: mass.get(b, 0) if b in mine else 0)
            budget = hi - F_j[j] + 1e-9 * max(1, hi)
            remove = {z for z in mine if lengths.get(z, math.inf) > budget}
        else:
            remove = set().union(*(cc for cc in nx.connected_components(gj)
                if math.fsum(mass.get(z, 0) for z in cc) < lo - F_j[j] - 1e-9 * max(1, lo)))
        for z in remove:
            A[z].remove(j)
    A = {z: sorted(v) for z, v in A.items()}
    Gamma = {j: G.subgraph({z for z in zs if j in A[z]} | set(bnodes[j])).copy() for j in js}
    geo = {}
    for j in js:
        mine = {z for z in zs if j in A[z]}
        src = {z for z in mine if set(G[z]) & set(bnodes[j])}
        if not src:
            for v in sorted({unit[z] for z in mine}):
                if (v, j) in centres:
                    src.add(min((z for z in mine if unit[z] == v),
                                key=lambda z: (math.dist(pos[z], centres[v, j]) ** 2, z)))
        free_graph = Gamma[j].subgraph(mine)
        geo[j] = (nx.multi_source_dijkstra_path_length(
            free_graph, src, weight=lambda a, b, _: math.dist(pos[a], pos[b])) if src else {})
    mbar = math.fsum(mass.get(z, 0) for z in zs) / max(1, sum(mass.get(z, 0) > 0 for z in zs)) or 1
    g = {(z, j): (mass.get(z, 0) / mbar + 0.1) * geo[j].get(z, math.inf) ** 2 for z in zs for j in A[z]}
    far = max((v for v in g.values() if math.isfinite(v)), default=1)
    g = {key: v if math.isfinite(v) else 4 * far for key, v in g.items()}
    gamma = 9 / max(1e-12, math.fsum(max((g[z, j] for j in A[z]), default=0) for z in zs))
    border = call.get("border")

    def km(a, b):
        return 1 if border is None else border.get(tuple(sorted((a, b))), 0)

    k = {(z, w): km(z, w) for z in zs for w in adj[z] if w in zs and z < w and km(z, w) > 0}
    kB = {}
    for z in zs:
        for w in adj[z]:
            if w in body_of:
                key = (z, body_owner[body_of[w]])
                kB[key] = kB.get(key, 0) + km(z, w)
    beta = 900 / max(1e-12, math.fsum(k.values()) + math.fsum(kB.values()))
    Y = sorted({(unit[z], j) for z in zs for j in A[z]})
    Yplus = [(v, j) for v, j in Y if not any(fixed.get(z) == j for z in unit_zips.get(v, ()))]
    land = call.get("land")
    H, area, held = {}, {}, {}
    if land is not None:
        aland = land["aland"]
        floor = land.get("min_share", .20) * ch.tau - 1e-9 * max(1, ch.tau)
        for v in sorted({unit[z] for z in zs}):
            a = math.fsum(aland.get(z, 0) for z in unit_zips[v])
            hs = [j for j in js if (v, j) in Y and call["planned"].get((v, j), 0) >= floor]
            if a > 0 and len(hs) > 1:
                H[v], area[v] = hs, a
                held.update({(v, j): math.fsum(aland.get(z, 0) for z in unit_zips[v]
                             if fixed.get(z) == j and z not in zs) for j in hs})
    return SimpleNamespace(Z_g=zs, J_g=js, A_z=A, B=bnodes, Gamma=Gamma, F=F_j,
        v=unit, m=mass, ell=lo, u=hi, g=g, gamma=gamma, k=k, kB=kB, beta=beta,
        Y=Y, Yplus=Yplus, H=H, area=area, held=held, call=call, unit_zips=unit_zips)


def build_model(data, *, connectivity=True):
    """Build complete F4; connectivity=False is the shared F142 *base relaxation*."""
    d = data
    M = pyo.ConcreteModel(name="F4")
    M._data = d
    M.Z_g = pyo.Set(initialize=d.Z_g, ordered=True)
    M.J_g = pyo.Set(initialize=d.J_g, ordered=True)
    M.A_z = pyo.Set(M.Z_g, initialize=d.A_z)
    M.B = pyo.Set(M.J_g, initialize=d.B)
    M.Gamma = pyo.Set(M.J_g, initialize={j: sorted(d.Gamma[j]) for j in d.J_g})
    M.X = pyo.Set(dimen=2, initialize=[(z, j) for z in d.Z_g for j in d.A_z[z]])
    M.Y = pyo.Set(dimen=2, initialize=d.Y)
    M.Yplus = pyo.Set(dimen=2, initialize=d.Yplus)
    M.E = pyo.Set(dimen=2, initialize=sorted(d.k))
    M.v = pyo.Param(M.Z_g, initialize={z: d.v[z] for z in d.Z_g}, within=pyo.Any)
    M.m = pyo.Param(M.Z_g, initialize={z: d.m.get(z, 0) for z in d.Z_g}, within=pyo.NonNegativeReals)
    M.F = pyo.Param(M.J_g, initialize=d.F)
    M.ell = pyo.Param(initialize=d.ell)
    M.u = pyo.Param(initialize=d.u)
    M.g = pyo.Param(M.X, initialize=d.g)
    M.k = pyo.Param(M.E, initialize=d.k)
    M.kB = pyo.Param(M.X, initialize={key: d.kB.get(key, 0) for key in M.X})
    M.beta = pyo.Param(initialize=d.beta)
    M.gamma = pyo.Param(initialize=d.gamma)
    M.zero = pyo.Param(initialize=0, mutable=True)  # symbolic empty sums, including infeasible rows
    M.x = pyo.Var(M.X, domain=pyo.Binary)
    M.y = pyo.Var(M.Y, domain=pyo.Binary)
    M.c = pyo.Var(M.E, bounds=(0, 1))
    M.coverage = pyo.Constraint(M.Z_g, rule=lambda t, z: sum((t.x[z, j] for j in t.A_z[z]), t.zero) == 1)
    M.holder = pyo.Constraint(M.X, rule=lambda t, z, j: t.x[z, j] <= t.y[d.v[z], j])
    M.cut = pyo.ConstraintList()
    for z, w in M.E:
        for j in d.A_z[z]:
            M.cut.add(M.c[z, w] >= M.x[z, j] - (M.x[w, j] if (w, j) in M.X else 0))
    sequential = d.call.get("sequential", False)
    M.band = pyo.Constraint(M.J_g, rule=lambda t, j: pyo.inequality(
        max(0, d.ell - d.F[j]) if sequential else d.ell - d.F[j],
        sum((t.m[z] * t.x[z, j] for z in t.Z_g if (z, j) in t.X), t.zero),
        max(0, d.u - d.F[j]) if sequential else d.u - d.F[j]))
    M.neighbor = pyo.ConstraintList()
    for z, j in M.X:
        if set(d.Gamma[j][z]) & set(d.B[j]):
            continue
        if not d.B[j] and max((d.m.get(w, 0) for w in d.Z_g if j in d.A_z[w]), default=0) >= d.ell - d.F[j]:
            continue
        M.neighbor.add(M.x[z, j] <= sum((M.x[w, j] for w in d.Gamma[j][z] if (w, j) in M.X), M.zero))
    M.move = pyo.ConstraintList()
    if d.call["arm"] == "move":
        for v in sorted({d.v[z] for z in d.Z_g}):
            if len(d.call["hold"].get(v, ())) > 1:
                M.move.add(sum((M.y[u, j] for u, j in M.Y if u == v), M.zero) <= len(d.call["hold"][v]))
    M.targets = pyo.ConstraintList()
    if d.call["fixed_targets"]:
        for v in sorted({d.v[z] for z in d.Z_g}):
            if v not in d.call["inst"].channels[d.call["c"]].M:
                continue
            top = max(d.m[z] for z in d.unit_zips[v])
            for j in d.J_g:
                residual = d.call["planned"].get((v, j), 0) - math.fsum(d.m[z] for z in d.unit_zips[v]
                    if d.call["fixed"].get(z) == j and z not in d.Z_g)
                M.targets.add(pyo.inequality(residual - top,
                    sum((M.m[z] * M.x[z, j] for z in d.Z_g if d.v[z] == v and (z, j) in M.X), M.zero), residual + top))
    M.V_land = pyo.Set(initialize=sorted(d.H))
    M.H = pyo.Set(M.V_land, initialize=d.H)
    M.T = pyo.Set(dimen=3, initialize=[(v, j, k) for v, hs in d.H.items() for j in hs for k in hs if j != k])
    M.e = pyo.Var(M.T, bounds=(0, 1))
    M.A = pyo.Param(M.V_land, initialize=d.area)
    land = d.call.get("land") or {"ratio": 1, "aland": {}}
    M.R = pyo.Param(initialize=land["ratio"], within=pyo.NonNegativeReals)
    M.a = pyo.Param(M.Z_g, initialize={z: land["aland"].get(z, 0) for z in d.Z_g})
    M.A_vj = pyo.Expression(M.Y, rule=lambda t, v, j: d.held.get((v, j), 0)
        + sum(t.a[z] * t.x[z, j] for z in d.Z_g if d.v[z] == v and (z, j) in t.X))
    M.land_excess = pyo.Constraint(M.T, rule=lambda t, v, j, k:
        t.e[v, j, k] >= (t.A_vj[v, j] - t.R * t.A_vj[v, k]) / t.A[v] - (1 - t.y[v, k]))
    M.omega = pyo.Param(M.V_land, initialize={v: 900 / ((len(hs) - 1) * len(d.H)) for v, hs in d.H.items()})
    M.objective = pyo.Objective(expr=1000 * sum(M.y[v, j] for v, j in M.Yplus)
        + M.beta * (sum(M.k[z, w] * M.c[z, w] for z, w in M.E) - sum(M.kB[z, j] * M.x[z, j] for z, j in M.X))
        + M.gamma * sum(M.g[z, j] * M.x[z, j] for z, j in M.X)
        + sum(M.omega[v] * M.e[v, j, k] for v, j, k in M.T))
    if connectivity:
        add_flow(M)
    return M


def selected(M, j, v):
    """The F4/F142 x^j_v convention: bodies are identically one."""
    return 1 if v in M.B[j] else M.x[v, j]


def add_flow(M):
    """Exact connectivity extension, allowing the empty set when base rows allow it.

    For a body district the root is fixed. Rootless selected sets use one root,
    but rootless empty sets use none; production's separator loop permits both.
    """
    d = M._data
    M.JV = pyo.Set(dimen=2, initialize=[(j, v) for j in M.J_g for v in M.Gamma[j]])
    M.JA = pyo.Set(dimen=3, initialize=[(j, a, b) for j in M.J_g for a in M.Gamma[j] for b in d.Gamma[j][a]])
    M.n = pyo.Param(M.J_g, initialize={j: len(M.Gamma[j]) for j in M.J_g})
    M.t = pyo.Var(M.J_g, domain=pyo.Binary)
    M.r = pyo.Var(M.JV, domain=pyo.Binary)
    M.f = pyo.Var(M.JA, domain=pyo.NonNegativeReals)
    for j in M.J_g:
        if d.B[j]:
            M.t[j].fix(1)
            for v in M.Gamma[j]:
                M.r[j, v].fix(int(v == d.B[j][0]))
    M.nonempty = pyo.Constraint(M.J_g, rule=lambda t, j:
                                t.t[j] <= sum((selected(t, j, v) for v in t.Gamma[j]), t.zero))
    M.owns_active = pyo.Constraint(M.JV, rule=lambda t, j, v: selected(t, j, v) <= t.t[j])
    M.root_count = pyo.Constraint(M.J_g, rule=lambda t, j:
                                 sum((t.r[j, v] for v in t.Gamma[j]), t.zero) == t.t[j])
    M.root_owned = pyo.Constraint(M.JV, rule=lambda t, j, v: t.r[j, v] <= selected(t, j, v))
    M.flow_tail = pyo.Constraint(M.JA, rule=lambda t, j, a, b: t.f[j, a, b] <= t.n[j] * selected(t, j, a))
    M.flow_head = pyo.Constraint(M.JA, rule=lambda t, j, a, b: t.f[j, a, b] <= t.n[j] * selected(t, j, b))
    M.flow_balance = pyo.Constraint(M.JV, rule=lambda t, j, v:
        sum((t.f[j, u, v] - t.f[j, v, u] for u in d.Gamma[j][v]), t.zero)
        >= selected(t, j, v) - t.n[j] * t.r[j, v])
