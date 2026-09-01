"""nway.py -- N-way division primitives: 3+ candidate owners per zip.

The two-player contract in `base.py` encodes an allocation as `to_a: set` -- membership is
the whole answer, because there are exactly two sides.  When a zip can be claimed by three or
more reps that representation runs out, and so do `gains`, `objective`, `pieces` and
`fairness`, all of which are written against an `a` side and its complement.

This module is the N-way replacement for those primitives.  It is deliberately *standalone*:
`base.py` is the frozen harness contract and a serial-only file (CLAUDE.md), so the N-way
maths gets proved out here first and the contract extension lands once, later, with the
reduction test already passing.  See `research/contiguity/NWAY.md` for the design and phasing.

The model
---------
Per-rep booked production `S[i][z]`, total booked `T_z = sum_j S[j][z]`, opportunity `M_z`::

    u_i(z) = c1*S_i(z) + c2*(T_z - S_i(z)) + lam*M_z
    c1 = 1 - lam,   c2 = theta*(1 - lam)

The inheriting rep keeps `c1` of their own book and captures `c2` of everyone else's.  At two
reps with S = {a: A_z, b: B_z} this is identically `base.utilities` -- asserted by
`tests/test_nway.py::test_two_rep_reduction`, which is what lets the existing corpus of
two-player results stay interpretable.

An allocation is a `to_owner: dict[node -> rep]`, total over the nodes considered.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional

import networkx as nx
import numpy as np

# Attribute names.  Native N-way nodes carry `cand` + `S`; two-rep nodes carry the legacy
# rep_a/rep_b/A/B and are read through `candidates` / `books` below.
CAND = "cand"
BOOK = "S"


# ------------------------------------------------------------------ schema shim
def candidates(G, z) -> tuple:
    """Candidate owners of zip `z`, as a tuple, for native and legacy two-rep nodes."""
    d = G.nodes[z]
    if CAND in d:
        c = tuple(d[CAND])
        if len(c) < 2:
            raise ValueError(f"zip {z!r} has {len(c)} candidate(s); need >= 2")
        if len(set(c)) != len(c):
            raise ValueError(f"zip {z!r} has duplicate candidates {c!r}")
        return c
    return (d["rep_a"], d["rep_b"])


def books(G, z) -> dict:
    """Per-rep booked production at `z`: {rep -> S}, for native and legacy nodes."""
    d = G.nodes[z]
    if BOOK in d:
        return dict(d[BOOK])
    return {d["rep_a"]: float(d["A"]), d["rep_b"]: float(d["B"])}


def reps(G, nodes) -> list:
    """Every rep appearing as a candidate on `nodes`, in first-appearance order.

    Deterministic ordering matters: it fixes the row order of the utility matrix and hence
    every downstream index, so runs stay reproducible.
    """
    seen, out = set(), []
    for z in nodes:
        for i in candidates(G, z):
            if i not in seen:
                seen.add(i)
                out.append(i)
    return out


# ------------------------------------------------------------------- utilities
def utilities(G, nodes, reps_order=None, theta: float = 0.40, lam: float = 0.30):
    """(U, reps) with `U[k, j]` = u of rep `reps[k]` for `nodes[j]`, 0 where not a candidate.

    Non-candidates are held at 0 rather than at their notional utility: a rep cannot own a zip
    it is not a candidate for, so the entry is never read by a feasible allocation, and 0
    keeps `gains` a plain masked sum.  Use `candidate_matrix` for the feasibility mask itself.
    """
    nodes = list(nodes)
    R = list(reps_order) if reps_order is not None else reps(G, nodes)
    idx = {i: k for k, i in enumerate(R)}
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    U = np.zeros((len(R), len(nodes)), float)
    for j, z in enumerate(nodes):
        S = books(G, z)
        T = float(sum(S.values()))
        M = float(G.nodes[z]["M"])
        for i in candidates(G, z):
            k = idx.get(i)
            if k is None:                      # rep filtered out of this subproblem
                continue
            s = float(S.get(i, 0.0))
            U[k, j] = c1 * s + c2 * (T - s) + lam * M
    return U, R


def candidate_matrix(G, nodes, reps_order) -> np.ndarray:
    """Boolean `C[k, j]`: may rep `reps_order[k]` own `nodes[j]`?"""
    nodes = list(nodes)
    idx = {i: k for k, i in enumerate(reps_order)}
    C = np.zeros((len(reps_order), len(nodes)), bool)
    for j, z in enumerate(nodes):
        for i in candidates(G, z):
            k = idx.get(i)
            if k is not None:
                C[k, j] = True
    return C


def headroom_violations(G, nodes=None, theta: float = 0.40) -> list:
    """Zips violating `M_z >= max_i (S_i + theta*(T - S_i))`; the N-way headroom condition.

    Reduces to `M >= max(A + theta*B, B + theta*A)` at two reps (`territory.validate`).
    """
    bad = []
    for z in (G.nodes() if nodes is None else nodes):
        S = books(G, z)
        T = float(sum(S.values()))
        need = max((s + theta * (T - s)) for s in S.values()) if S else 0.0
        M = float(G.nodes[z]["M"])
        if M < need - 1e-12:
            bad.append((z, M, need))
    return bad


# ----------------------------------------------------------------- allocations
def owner_index(nodes, to_owner, reps_order) -> np.ndarray:
    """Per-node index into `reps_order`; -1 where unassigned."""
    idx = {i: k for k, i in enumerate(reps_order)}
    return np.fromiter((idx.get(to_owner.get(z, None), -1) for z in nodes),
                       dtype=int, count=len(nodes))


def gains(U: np.ndarray, oi: np.ndarray) -> np.ndarray:
    """g_k = sum of U[k, j] over nodes j owned by rep k."""
    g = np.zeros(U.shape[0], float)
    for k in range(U.shape[0]):
        sel = oi == k
        if sel.any():
            g[k] = float(U[k, sel].sum())
    return g


def objective(U: np.ndarray, oi: np.ndarray, rho: float = 0.0, perimeter: int = 0) -> float:
    """sum_k log g_k - rho*perimeter; -inf if any rep's gain is <= 0.

    The `-inf` is the honest reading of maximum Nash welfare, not a guard: one rep at zero
    utility makes the product zero.  Whether an allocation that starves a rep should instead
    be handled lexicographically is open -- NWAY.md §6.1.
    """
    g = gains(U, oi)
    if (g <= 0).any():
        return -math.inf
    return float(np.log(g).sum()) - rho * perimeter


def perimeter(G, nodes, to_owner) -> int:
    """Boundary edges: endpoints with different owners.  At two reps this is `base.perimeter`."""
    return sum(1 for u, v in G.subgraph(nodes).edges()
               if to_owner.get(u, None) != to_owner.get(v, None))


def pieces(G, nodes, to_owner) -> dict:
    """Per-rep contiguity report, component-wise (the trap-13 rule at N reps).

    `excess_pieces` sums, over each component K of the node-induced subgraph and each rep i,
    `(cc(K_i) - 1)^+` where `K_i` is i's share of K.  Zero iff every rep holds one connected
    piece inside every component it appears in -- the N-way form of `base.pieces`.
    """
    sub = G.subgraph(nodes)
    comps = list(nx.connected_components(sub))
    per_rep: dict = {}
    excess = 0
    for K in comps:
        by_rep: dict = {}
        for z in K:
            by_rep.setdefault(to_owner.get(z, None), []).append(z)
        for rep, zs in by_rep.items():
            cc = nx.number_connected_components(sub.subgraph(zs))
            per_rep[rep] = per_rep.get(rep, 0) + cc
            if rep is not None:
                excess += max(cc - 1, 0)
    return dict(pair_components=len(comps), pieces_per_rep=per_rep,
                excess_pieces=excess,
                unassigned=sum(1 for z in nodes if z not in to_owner))


def is_feasible(G, nodes, to_owner) -> bool:
    """Every node assigned to one of its own candidates, and every rep in one piece."""
    for z in nodes:
        if z not in to_owner:
            return False
        if to_owner[z] not in candidates(G, z):
            return False
    return pieces(G, nodes, to_owner)["excess_pieces"] == 0


def violations(G, nodes, to_owner, reps_order=None) -> list:
    """Human-readable reasons `to_owner` is not a valid N-way allocation (empty == valid)."""
    out = []
    nodes = list(nodes)
    node_set = set(nodes)
    stray = [z for z in to_owner if z not in node_set]
    if stray:
        out.append(f"to_owner covers {len(stray)} node(s) outside the subproblem "
                   f"(e.g. {stray[:3]})")
    missing = [z for z in nodes if z not in to_owner]
    if missing:
        out.append(f"{len(missing)} node(s) unassigned (e.g. {missing[:3]})")
    off = [z for z in nodes if z in to_owner and to_owner[z] not in candidates(G, z)]
    if off:
        out.append(f"{len(off)} node(s) assigned to a non-candidate (e.g. {off[:3]})")
    p = pieces(G, nodes, to_owner)
    if p["excess_pieces"]:
        out.append(f"excess_pieces={p['excess_pieces']} (a rep holds a disconnected bundle)")
    if reps_order is not None:
        U, _ = utilities(G, nodes, reps_order)
        g = gains(U, owner_index(nodes, to_owner, reps_order))
        zero = [reps_order[k] for k in range(len(g)) if g[k] <= 0]
        if zero:
            out.append(f"{len(zero)} rep(s) receive zero utility (e.g. {zero[:3]}) "
                       f"-- objective is -inf; see NWAY.md 6.1")
    return out


# -------------------------------------------------------------- fairness audit
def fairness(U: np.ndarray, oi: np.ndarray) -> dict:
    """EF1 over all ordered rep pairs, at d=0 (Caragiannis et al. 2019, stated for n agents).

    i does not envy j up to one good:  v_i(A_j) - max_{z in A_j} u_i(z) <= g_i.
    Returns the conjunction plus the worst normalised envy and the worst proportionality
    shortfall (`1/n` share, the n-agent form of the two-player `1/2`).
    """
    n = U.shape[0]
    g = gains(U, oi)
    worst_envy = 0.0
    ef1 = True
    pairs_failed = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            sel = oi == j
            if not sel.any():
                continue
            v_ij = float(U[i, sel].sum())
            top = float(U[i, sel].max())
            if v_ij - top > g[i] + 1e-12:
                ef1 = False
                pairs_failed.append((i, j))
            envy = v_ij - g[i]
            if envy > 0 and top > 0:
                worst_envy = max(worst_envy, envy / top)
    shortfall = 0.0
    for i in range(n):
        share = float(U[i].sum()) / n
        umax = float(U[i].max()) if U.shape[1] else 0.0
        if umax > 0:
            shortfall = max(shortfall, max(0.0, share - g[i]) / umax)
    return dict(ef1=bool(ef1), n_ef1_failures=len(pairs_failed),
                envy_over_umax=float(worst_envy),
                prop_shortfall=float(shortfall))


# ------------------------------------------------------- two-player interop
def to_owner_from_to_a(nodes, to_a, rep_a, rep_b) -> dict:
    """Lift a two-player `to_a` set into an N-way `to_owner` map."""
    to_a = set(to_a)
    return {z: (rep_a if z in to_a else rep_b) for z in nodes}


def to_a_from_to_owner(nodes, to_owner, rep_a) -> set:
    """Project an N-way allocation back onto a two-player `to_a` set (2-rep graphs only)."""
    return {z for z in nodes if to_owner.get(z, None) == rep_a}
