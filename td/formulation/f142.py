"""F142, MODEL.md §12.1: F4 base plus the finite vertex-separator family.

The family is exponential. build_model creates its base relaxation; separate adds
violated integer rows. An integer optimum is a certificate only after separate
returns zero. This small-spec interface is not a production solving backend.
No bnc branch code is imported; NetworkX components supply independent witnesses.
Agent: modeler (openai-codex/gpt-6-astra).
"""
from __future__ import annotations

import networkx as nx
import pyomo.environ as pyo

from .f4 import build_model as base_model, selected


def build_model(data):
    """Materialize F142's common base, with an initially empty separator family."""
    M = base_model(data, connectivity=False)
    M.name = "F142"
    M.SEP = pyo.Set(dimen=4, ordered=True)  # (j, a, b, row id)
    M.S = pyo.Set(M.SEP)
    M.separator = pyo.Constraint(M.SEP)
    M._separator_keys = set()
    return M


def separate(M, *, tolerance=1e-6):
    """Add valid x^j_a + x^j_b - sum_{s in S} x^j_s <= 1 rows.

    For a disconnected selected component C, S=N(C) in Gamma_j contains
    only unselected vertices. Choose b in another selected component. Every
    a-b path crosses S; both endpoints are selected, so the row is violated.
    Empty and singleton selected sets have no disconnected pair, as in F142.
    Returns the number added; rejects fractional points rather than certifying.
    """
    added = 0
    for j in M.J_g:
        G = M._data.Gamma[j]
        values = {v: pyo.value(selected(M, j, v)) for v in G}
        if any(abs(x - round(x)) > tolerance for x in values.values()):
            raise ValueError("integer separation requires an integral assignment")
        owned = {v for v, x in values.items() if x > .5}
        comps = sorted(nx.connected_components(G.subgraph(owned)), key=lambda cc: min(cc))
        if len(comps) < 2:
            continue
        b = min(comps[0])
        for C in comps[1:]:
            S = set().union(*(set(G[a]) for a in C)) - C
            assert not S & owned
            for a in sorted(C):
                key = (j, a, b, tuple(sorted(S)))
                if key in M._separator_keys:
                    raise RuntimeError("solver returned a point violating an existing separator")
                M._separator_keys.add(key)
                index = (j, a, b, len(M.SEP))
                M.SEP.add(index)
                M.S[index] = sorted(S)
                M.separator[index] = (selected(M, j, a) + selected(M, j, b)
                    - sum((selected(M, j, s) for s in S), M.zero) <= 1)
                added += 1
    return added
