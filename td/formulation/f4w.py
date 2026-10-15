"""F4.W: independent small-window specification, MODEL.md §4.3.

Outside ownership/lists/bodies are inputs; cap and split-first rows augment F4.
This is not a production solver. Neck callbacks and DAG remain unsupported here.
Agent: modeler (openai-codex/gpt-6-astra).
"""
from __future__ import annotations

import pyomo.environ as pyo

from . import f4


def prepare(call, *, centres):
    if call.get("count") is None:
        raise ValueError("F4.W requires repair count data")
    data = f4.prepare({**call, "count": None}, centres=centres)
    data.call = call
    return data


def build_model(data):
    """The complete fixed-window model with independent flow connectivity."""
    M = f4.build_model(data)
    M.name = "F4.W"
    d, count = data, data.call["count"]
    units = sorted({d.v[z] for z in d.Z_g})
    held = {v: {d.call["fixed"][z] for z in d.unit_zips[v] if z in d.call["fixed"]}
            for v in units}
    M.V_W = pyo.Set(initialize=units)
    M.O = pyo.Set(within=M.V_W, initialize=sorted(set(count.get("opened", ())) & set(units)))
    M.h = pyo.Param(M.V_W, initialize={v: len(held[v]) for v in units})
    M.Y_v_plus = pyo.Set(M.V_W, initialize={v: [j for u, j in d.Yplus if u == v] for v in units})
    M.s = pyo.Var(M.V_W, domain=pyo.Binary)
    M.split = pyo.ConstraintList()
    for v in units:
        if len(held[v]) >= 2:
            M.s[v].fix(1)
        elif len(M.Y_v_plus[v]):
            M.split.add(M.h[v] + sum(M.y[v, j] for j in M.Y_v_plus[v])
                        <= 1 + len(M.Y_v_plus[v]) * M.s[v])
    M.S_0 = pyo.Param(initialize=sum(len(count["current"][v]) > 1 for v in units))
    M.Q_0 = pyo.Param(initialize=sum(len(count["current"][v]) - len(held[v]) for v in units))
    M.cap_splits = pyo.ConstraintList()
    M.cap_holders = pyo.ConstraintList()
    M.cap_opened = pyo.ConstraintList()
    if count["cap"]:
        groups = [(units, len(M.O))]
        if len(M.O):
            groups.append(([v for v in units if v not in M.O], 0))
        for vs, allowance in groups:
            M.cap_splits.add(sum((M.s[v] for v in vs), M.zero) <= M.S_0 + allowance)
            M.cap_holders.add(sum((M.y[v, j] for v in vs for j in M.Y_v_plus[v]), M.zero)
                              <= M.Q_0 + allowance)
        for v in M.O:
            M.cap_opened.add(sum((M.y[v, j] for j in M.Y_v_plus[v]), M.zero)
                             <= len(count["current"][v]) + 1 - M.h[v])
    M.objective.set_value(M.objective.expr + 1000 * (len(M.Y) + 1) * sum(M.s.values()))
    return M


def assignment_domain(Z, districts, owner, W):
    """Pure assignment restriction R(W); rows/bodies/caps are additional conditions.

    W subset W' implies R(W) subset R(W'), not monotonic local objective values.
    """
    return {(z, j) for z in Z for j in districts if z in W or owner[z] == j}


def growth_permitted(status, *, uncapped):
    """A larger accepted search step requires a complete uncapped infeasibility proof."""
    return status == "infeasible" and uncapped
