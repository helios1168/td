"""
flow.py -- Option D: Shirabe single-commodity flow contiguity, one-shot, with an outer
approximation (OA) tangent loop for the log welfare (PLAN.md W4, OPTIONS.md §4).

Why this exists
---------------
The legacy `current` loop generates connectivity cuts *lazily* by restarting the master
MILP once per violated component (a "multi-tree" scheme), and the OA tangent loop restarts
it again.  The two cut families have different finite-convergence arguments and their
iteration bounds multiply (CLAUDE.md trap 11 / OPTIONS.md §12), which is the structural
reason the loop thrashes.  This module removes one of the two loops entirely: contiguity is
written *once*, as a compact flow formulation, so the only remaining loop is the OA one --
and OA on a concave objective converges in a handful of rounds (Duran-Grossmann).

The formulation (per side, per connected component K of the pair graph)
----------------------------------------------------------------------
`x_z in {0,1}` is "z goes to a".  For the a-side, S = {z : x_z = 1}; for the b-side,
K \\ S.  Contiguity of S∩K is enforced by a single-commodity flow that must reach every
selected node from a *root* selected inside S∩K:

    (c)  sum_in f^a(.,z) - sum_out f^a(z,.) + U_K * r^a_z  >=  x_z        for z in K
    (d)  f^a_(u,v) <= cap_(u,v) * x_u      and      f^a_(u,v) <= cap_(u,v) * x_v

with `U_K = |K|` and `r^a` the root indicator (D1 below).  The b-side is the mirror image
with `x -> 1 - x`.  Components with |K| <= 2 need no rows at all: every subset of a
1- or 2-node component is connected.

*Correctness (both directions).*  Sum (c) over a connected component C of S∩K: internal
arcs cancel, and every arc leaving C has its other endpoint outside S (C is a *maximal*
connected piece), so (d) pins those flows to 0.  What survives is
`U_K * sum_{z in C} r^a_z >= |C| > 0`, i.e. C contains a root.  There is at most one root
per component (D1), so S∩K has at most one piece: it is connected.  Conversely, if S∩K is
connected, route one unit to every node of S∩K along a spanning arborescence out of the
root; arc (u,v) then carries at most the size of v's subtree, which is at most
`cap_(u,v)` (D5), and the root absorbs the slack because (c) is an inequality.

D1 -- root selection by "lowest index in the component" (no extra binaries)
--------------------------------------------------------------------------
`r` is never materialised.  Per side and per component, continuous prefix indicators
`h_z in [0,1]` over the component's node order satisfy

    h_0 = x_0,        h_j - h_{j-1} >= 0,   h_j - x_j >= 0,   h_j - h_{j-1} - x_j <= 0

which for integral x force `h_j = max_{i<=j} x_i`, hence `r_j := h_j - h_{j-1}` is exactly
`1{j = min ord_K(S∩K)}` -- and `h == 0`, no root, when S∩K is empty, with no special case.
`r_j` is substituted into (c), never added as a column.  The bound stays **global**
(`ub_scope="global"`): no allocation is excluded, unlike a formulation that pins a
particular zip to a particular side.

Variants (registry keys):
  `flow`            the above; chain roots, tight caps, global bound.
  `flow_selroot`    PLAN.md's literal `sum_K r <= 1, r <= x` with **binary** r.  Continuous
                    r is unsound here -- a stray piece carrying `sum_C r = 0.5` satisfies
                    (c) with room to spare -- so this variant pays 2n extra binaries.
  `flow_rooted`     roots *fixed* per component at the argmax / argmin utility ratio, the
                    way `current` does it.  This bounds a restriction of the problem, so it
                    reports `ub_scope="rooted"` and the harness downgrades its `optimal` to
                    `optimal_rooted`.  Diagnostic control for "how much does root fixing
                    cost?", not a production method.
  `flow_loosecaps`  `cap == |K| - 1` everywhere (D5 off): the LP-strength control.

D2/D3 (the a-priori chord under-estimator that removes the OA loop) live in `flow_pwl.py`,
which imports `build_core`, `tree_cut_incumbent` and the bound machinery from here.

D4 -- hard valid bounds on the gains
------------------------------------
`g_a in [g_lo_a, g_hi_a]`, `g_b in [g_lo_b, g_hi_b]`, as *variable bounds* on two aggregate
columns `g_a`, `g_b` linked to x by one equality each.  `g_hi` is the sum of the positive
utilities (trivially valid).  `g_lo` combines two valid floors:

  * `min{u_a(z) : u_a(z) > 0}` -- any allocation with `g_a > 0` attains at least this
    (only used when no utility is negative, i.e. kappa = 0).  Always on: it is what keeps
    `log g_a` off its singularity.
  * `exp(LB_incumbent) / g_hi_b` -- the optimum's objective is at least the incumbent's, and
    `g_b <= g_hi_b`, so `g_a >= exp(obj_inc + rho*per_inc)/g_hi_b >= exp(LB_inc)/g_hi_b`.
    Switched by `bound_g` (default True).

The aggregate columns also make every tangent (and, in `flow_pwl`, every chord) a two-nonzero
row instead of an (n+1)-nonzero row -- the difference between 8k and 800k nonzeros at
n = 200, k = 1000.

D5 -- arc capacities from articulation points
---------------------------------------------
`cap_(u,v) = |R_K(v, K \\ {u})|`, the number of nodes reachable from v inside K without
passing through u.  Default `|K| - 1`; for every cut vertex u and every component C of
K - u, the arcs from u into C get `cap = |C|`.  Tightening capacities is the cheapest
available strengthening of a notoriously weak flow LP.

D6 -- rho
---------
`rho = 0` is the model, and then there are no `y_e` columns at all.  At `rho > 0`,
`y_e >= x_u - x_v`, `y_e >= x_v - x_u`, cost `rho` in the minimisation.

Traps this addresses
--------------------
trap 11 mechanism (b) "pure scale": one MILP instead of a restart per cut round -- but the
flow LP is weak, and the expected finding is that it *measures* the scale wall rather than
removing it (OPTIONS.md §4 risk).
trap 11 mechanism (a) "pre-existing graph disconnection": handled by construction -- the
formulation is per component of the pair graph, matching `base.pieces`' component-wise
feasibility rule, so a disconnected pair is not a special case (contrast `current.py`,
whose single global root per side is *wrong* on such pairs).
trap 12 "converged to HiGHS' relative gap": `mip_rel_gap = 0.0` and `mip_abs_gap = 0.0` are
forced on every master, and `optimal` is claimed only when this module's own
`UB - LB <= base.CERT_TOL`.
CLAUDE.md's `g0 in {1..11}` tangent-seed trap: seeds are eight geomspace points on the
instance's own `[g_lo, g_hi]`, never absolute constants.

Known environment issue (2026-08-29): HiGHS 1.15.1 can return "Status 4: Solve error" after
proving optimality, because its own post-check finds the returned solution 1e-6 primal
infeasible.  `run_milp`'s docstring has the diagnosis and the six-rung deterministic escape
ladder; `extra["retried_without_tol"]`, `extra["retried_random_seed"]` and
`extra["milp_rung"]` record when it fired.
"""
from __future__ import annotations

import math
import time
import warnings
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csc_array

from . import base

NAME = "flow"
EXACT = True
MAX_N = None
VARIANTS = {
    "flow_selroot": dict(root_mode="binary"),
    "flow_rooted": dict(root_mode="fixed"),
    "flow_loosecaps": dict(caps="loose"),
}

MIN_COMPONENT = 3          # components of 1 or 2 nodes need no connectivity rows
Z_FLOOR = -60.0            # z_a / z_b lower bound when g_lo is 0 (feasibility probes only)
_TOL_OPTS = dict(mip_feasibility_tolerance=1e-9, primal_feasibility_tolerance=1e-9)
# Deterministic escape ladder for the HiGHS "Solve error" post-check (see run_milp).  Rung 0
# is the intended configuration; each later rung perturbs the search enough to land on a
# numerically cleaner optimal vertex.  Both `presolve=False` and `random_seed` are needed:
# each rescues a model the other does not.
_LADDER = (
    dict(),
    dict(drop_tol=True),
    dict(presolve=False),
    dict(drop_tol=True, presolve=False),
    dict(random_seed=1),
    dict(drop_tol=True, presolve=False, random_seed=7),
)


# ============================================================================ row buffer
class Rows:
    """COO triplet accumulator.  Built once for the static block, then extended per OA
    round with the tangent rows only -- never a `lil_matrix` inside the loop."""

    __slots__ = ("i", "j", "v", "bl", "bu", "n")

    def __init__(self):
        self.i: list[int] = []
        self.j: list[int] = []
        self.v: list[float] = []
        self.bl: list[float] = []
        self.bu: list[float] = []
        self.n = 0

    def add(self, pairs, lo, hi) -> int:
        r = self.n
        for cj, val in pairs:
            if val == 0.0:
                continue
            self.i.append(r)
            self.j.append(int(cj))
            self.v.append(float(val))
        self.bl.append(float(lo))
        self.bu.append(float(hi))
        self.n += 1
        return r

    def arrays(self):
        return (np.asarray(self.i, dtype=np.int64), np.asarray(self.j, dtype=np.int64),
                np.asarray(self.v, dtype=float), np.asarray(self.bl, dtype=float),
                np.asarray(self.bu, dtype=float))


# ============================================================================ components
def components_sorted(H, nodes) -> list:
    """Connected components of the pair graph, deterministically ordered.

    Nodes inside a component follow `nodes` order (that order *is* D1's `ord_K`), and the
    components themselves follow their first node.
    """
    idx = {z: i for i, z in enumerate(nodes)}
    comps = [sorted(c, key=lambda z: idx[z]) for c in nx.connected_components(H.subgraph(nodes))]
    comps.sort(key=lambda K: idx[K[0]])
    return comps


def arc_caps(H, K, tight: bool = True) -> dict:
    """D5: `cap[(u, v)] = |R_K(v, K\\{u})|` for every ordered arc inside component K.

    `|K| - 1` is always valid (a unit is routed to at most every other node).  When u is a
    cut vertex, everything the arc u->v can ever serve lies in v's own component of K - u,
    so the cap drops to that component's size.
    """
    sub = H.subgraph(K)
    m = len(K)
    caps = {}
    for u, v in sub.edges():
        caps[(u, v)] = float(m - 1)
        caps[(v, u)] = float(m - 1)
    if not tight:
        return caps
    for u in set(nx.articulation_points(sub)):
        rest = sub.subgraph([z for z in K if z != u])
        nbrs = set(sub.neighbors(u))
        for C in nx.connected_components(rest):
            sz = float(len(C))
            for v in nbrs & C:
                if sz < caps[(u, v)]:
                    caps[(u, v)] = sz
    return caps


# ================================================================================= core
@dataclass
class Core:
    """The static MILP block: columns, bounds, objective, and the frozen constraint COO."""
    nodes: list
    n: int
    ua: np.ndarray
    ub: np.ndarray
    rho: float
    root_mode: str
    comps: list
    IGA: int
    IGB: int
    IZA: int
    IZB: int
    n_col: int
    lo: np.ndarray
    hi: np.ndarray
    integrality: np.ndarray
    c: np.ndarray
    si: np.ndarray
    sj: np.ndarray
    sv: np.ndarray
    sbl: np.ndarray
    sbu: np.ndarray
    n_static_rows: int
    g_lo_a: float
    g_hi_a: float
    g_lo_b: float
    g_hi_b: float
    n_arcs: int
    roots: dict = field(default_factory=dict)

    # ---- constraint assembly -------------------------------------------------------
    def constraint(self, ext: Optional[Rows] = None) -> LinearConstraint:
        """`LinearConstraint` for the static block plus `ext` (the tangent / chord rows)."""
        if ext is None or ext.n == 0:
            i, j, v = self.si, self.sj, self.sv
            bl, bu = self.sbl, self.sbu
            nrow = self.n_static_rows
        else:
            ei, ej, ev, ebl, ebu = ext.arrays()
            i = np.concatenate([self.si, ei + self.n_static_rows])
            j = np.concatenate([self.sj, ej])
            v = np.concatenate([self.sv, ev])
            bl = np.concatenate([self.sbl, ebl])
            bu = np.concatenate([self.sbu, ebu])
            nrow = self.n_static_rows + ext.n
        A = csc_array((v, (i, j)), shape=(nrow, self.n_col))
        return LinearConstraint(A, bl, bu)

    # ---- cut generators ------------------------------------------------------------
    def tangent(self, side: str, ghat: float, ext: Rows) -> bool:
        """`z_s <= log ghat + (g_s - ghat)/ghat`, i.e. `z_s - g_s/ghat <= log ghat - 1`.

        A supporting hyperplane of the concave `log`, hence valid at every feasible point:
        this is what makes the master's dual bound a genuine upper bound on the true
        objective (Duran-Grossmann outer approximation).
        """
        if not (ghat > 0) or not math.isfinite(ghat):
            return False
        col = self.IZA if side == "a" else self.IZB
        gcol = self.IGA if side == "a" else self.IGB
        ext.add([(col, 1.0), (gcol, -1.0 / ghat)], -np.inf, math.log(ghat) - 1.0)
        return True

    def chord(self, side: str, p0: float, p1: float, ext: Rows) -> None:
        """`z_s <= log p0 + s*(g_s - p0)` with `s` the chord slope over [p0, p1] (D2).

        `log` is concave, so the chord lies *below* it on [p0, p1] and above it outside;
        the min over a grid's chords is therefore exactly the piecewise-linear interpolant
        on [p_0, p_k] -- k plain rows, no SOS2, no lambda variables, no binaries.
        """
        col = self.IZA if side == "a" else self.IZB
        gcol = self.IGA if side == "a" else self.IGB
        s = (math.log(p1) - math.log(p0)) / (p1 - p0)
        ext.add([(col, 1.0), (gcol, -s)], -np.inf, math.log(p0) - s * p0)


def fixed_roots(H, nodes, ua, ub, ratio=None) -> dict:
    """`flow_rooted`'s per-component roots: argmax / argmin utility ratio, `current`-style.

    Keyed by the component's first node.  Only components with `|K| >= MIN_COMPONENT` get
    roots -- smaller ones carry no connectivity rows, so fixing anything there would be a
    gratuitous restriction.
    """
    nodes = list(nodes)
    idx = {z: i for i, z in enumerate(nodes)}
    if ratio is None:
        ratio = base.ratio(ua, ub)
    out = {}
    for K in components_sorted(H, nodes):
        if len(K) < MIN_COMPONENT:
            continue
        ii = np.array([idx[z] for z in K])
        order = np.argsort(ratio[ii], kind="stable")
        out[K[0]] = (nodes[int(ii[order[-1]])], nodes[int(ii[order[0]])])
    return out


def build_core(H, nodes, ua, ub, rho, *, root_mode: str = "chain", caps: str = "tight",
               g_lo_a: float, g_hi_a: float, g_lo_b: float, g_hi_b: float,
               ratio=None) -> Core:
    """Assemble the static block once, as COO triplets (never a dense or lil matrix).

    Column layout
        0 .. n-1      x_z                          binary
        n             g_a  (= sum ua_z x_z)        [g_lo_a, g_hi_a]
        n+1           g_b  (= sum ub_z (1-x_z))    [g_lo_b, g_hi_b]
        n+2           z_a  (<= log g_a)            [log g_lo_a - 1, log g_hi_a + 1]
        n+3           z_b
        then          f^a per arc, f^b per arc     [0, cap]
        then          h^a_z, h^b_z                 [0, 1]
        then          y_e                          [0, 1]      only when rho > 0
        then          r^a_z, r^b_z                 binary      only when root_mode="binary"
    """
    nodes = list(nodes)
    n = len(nodes)
    idx = {z: i for i, z in enumerate(nodes)}
    comps = components_sorted(H, nodes)
    active = [K for K in comps if len(K) >= MIN_COMPONENT]

    # ---- arcs (both directions) over the active components -------------------------
    arcs: list[tuple[int, int]] = []
    arc_cap: list[float] = []
    arc_of: dict[tuple[int, int], int] = {}
    comp_caps = {}
    for K in active:
        cp = arc_caps(H, K, tight=(caps != "loose"))
        comp_caps[id(K)] = cp
        for (u, v), cval in sorted(cp.items(), key=lambda kv: (idx[kv[0][0]], idx[kv[0][1]])):
            arc_of[(idx[u], idx[v])] = len(arcs)
            arcs.append((idx[u], idx[v]))
            arc_cap.append(float(cval))
    n_arc = len(arcs)

    edges = sorted(((idx[u], idx[v]) if idx[u] < idx[v] else (idx[v], idx[u]))
                   for u, v in H.subgraph(nodes).edges())
    n_edge = len(edges)

    IGA, IGB, IZA, IZB = n, n + 1, n + 2, n + 3
    base_f = n + 4
    FA = base_f
    FB = base_f + n_arc
    HA = base_f + 2 * n_arc
    HB = HA + n
    n_col = HB + n
    YE = -1
    if rho > 0:
        YE = n_col
        n_col += n_edge
    RA = RB = -1
    if root_mode == "binary":
        RA = n_col
        RB = n_col + n
        n_col += 2 * n

    lo = np.zeros(n_col)
    hi = np.ones(n_col)
    integrality = np.zeros(n_col)
    integrality[:n] = 1
    lo[IGA], hi[IGA] = g_lo_a, max(g_hi_a, g_lo_a)
    lo[IGB], hi[IGB] = g_lo_b, max(g_hi_b, g_lo_b)
    lo[IZA] = math.log(g_lo_a) - 1.0 if g_lo_a > 0 else Z_FLOOR
    hi[IZA] = math.log(g_hi_a) + 1.0 if g_hi_a > 0 else 1.0
    lo[IZB] = math.log(g_lo_b) - 1.0 if g_lo_b > 0 else Z_FLOOR
    hi[IZB] = math.log(g_hi_b) + 1.0 if g_hi_b > 0 else 1.0
    for k in range(n_arc):
        hi[FA + k] = arc_cap[k]
        hi[FB + k] = arc_cap[k]
    if root_mode == "binary":
        integrality[RA:RA + 2 * n] = 1

    # ---- fixed roots (the `flow_rooted` control) ------------------------------------
    roots: dict = {}
    if root_mode == "fixed":
        roots = fixed_roots(H, nodes, ua, ub, ratio=ratio)
        for ra_node, rb_node in roots.values():
            ra, rb = idx[ra_node], idx[rb_node]
            lo[ra] = hi[ra] = 1.0
            lo[rb] = hi[rb] = 0.0

    c = np.zeros(n_col)
    c[IZA] = c[IZB] = -1.0            # milp minimises: -(z_a + z_b) + rho * sum y
    if rho > 0:
        c[YE:YE + n_edge] = rho

    R = Rows()
    # (a) aggregate gain links -------------------------------------------------------
    R.add([(IGA, 1.0)] + [(i, -float(ua[i])) for i in range(n)], 0.0, 0.0)
    R.add([(IGB, 1.0)] + [(i, float(ub[i])) for i in range(n)],
          float(ub.sum()), float(ub.sum()))

    # (b) root chain / root binaries -------------------------------------------------
    if root_mode == "chain":
        for K in active:
            for j, z in enumerate(K):
                zi = idx[z]
                ha, hb = HA + zi, HB + zi
                if j == 0:
                    R.add([(ha, 1.0), (zi, -1.0)], 0.0, 0.0)            # h^a_0 = x_0
                    R.add([(hb, 1.0), (zi, 1.0)], 1.0, 1.0)             # h^b_0 = 1 - x_0
                else:
                    pi = idx[K[j - 1]]
                    hpa, hpb = HA + pi, HB + pi
                    R.add([(ha, 1.0), (hpa, -1.0)], 0.0, np.inf)        # monotone
                    R.add([(ha, 1.0), (zi, -1.0)], 0.0, np.inf)         # h >= x
                    R.add([(ha, 1.0), (hpa, -1.0), (zi, -1.0)], -np.inf, 0.0)   # r <= x
                    R.add([(hb, 1.0), (hpb, -1.0)], 0.0, np.inf)
                    R.add([(hb, 1.0), (zi, 1.0)], 1.0, np.inf)          # h^b >= 1 - x
                    R.add([(hb, 1.0), (hpb, -1.0), (zi, 1.0)], -np.inf, 1.0)
    elif root_mode == "binary":
        for K in active:
            R.add([(RA + idx[z], 1.0) for z in K], -np.inf, 1.0)
            R.add([(RB + idx[z], 1.0) for z in K], -np.inf, 1.0)
            for z in K:
                zi = idx[z]
                R.add([(RA + zi, 1.0), (zi, -1.0)], -np.inf, 0.0)       # r^a <= x
                R.add([(RB + zi, 1.0), (zi, 1.0)], -np.inf, 1.0)        # r^b <= 1 - x

    # (c) flow conservation ----------------------------------------------------------
    for K in active:
        U = float(len(K))
        for j, z in enumerate(K):
            zi = idx[z]
            inc, out = [], []
            for w in H.neighbors(z):
                if w not in idx:
                    continue
                wi = idx[w]
                k_in = arc_of.get((wi, zi))
                k_out = arc_of.get((zi, wi))
                if k_in is not None:
                    inc.append(k_in)
                if k_out is not None:
                    out.append(k_out)
            pa = [(FA + k, 1.0) for k in inc] + [(FA + k, -1.0) for k in out] + [(zi, -1.0)]
            pb = [(FB + k, 1.0) for k in inc] + [(FB + k, -1.0) for k in out] + [(zi, 1.0)]
            la, lb = 0.0, 1.0
            if root_mode == "chain":
                pa.append((HA + zi, U))
                pb.append((HB + zi, U))
                if j > 0:
                    pi = idx[K[j - 1]]
                    pa.append((HA + pi, -U))
                    pb.append((HB + pi, -U))
            elif root_mode == "binary":
                pa.append((RA + zi, U))
                pb.append((RB + zi, U))
            else:                                   # fixed roots: r is a constant
                ra_node, rb_node = roots[K[0]]
                if z == ra_node:
                    la -= U
                if z == rb_node:
                    lb -= U
            R.add(pa, la, np.inf)
            R.add(pb, lb, np.inf)

    # (d) capacity links at BOTH endpoints -------------------------------------------
    for k, (ui, vi) in enumerate(arcs):
        cap = arc_cap[k]
        R.add([(FA + k, 1.0), (ui, -cap)], -np.inf, 0.0)
        R.add([(FA + k, 1.0), (vi, -cap)], -np.inf, 0.0)
        R.add([(FB + k, 1.0), (ui, cap)], -np.inf, cap)
        R.add([(FB + k, 1.0), (vi, cap)], -np.inf, cap)

    # (e) perimeter ------------------------------------------------------------------
    if rho > 0:
        for e, (ui, vi) in enumerate(edges):
            R.add([(YE + e, 1.0), (ui, -1.0), (vi, 1.0)], 0.0, np.inf)
            R.add([(YE + e, 1.0), (ui, 1.0), (vi, -1.0)], 0.0, np.inf)

    si, sj, sv, sbl, sbu = R.arrays()
    return Core(nodes=nodes, n=n, ua=np.asarray(ua, float), ub=np.asarray(ub, float),
                rho=float(rho), root_mode=root_mode, comps=comps,
                IGA=IGA, IGB=IGB, IZA=IZA, IZB=IZB, n_col=n_col, lo=lo, hi=hi,
                integrality=integrality, c=c, si=si, sj=sj, sv=sv, sbl=sbl, sbu=sbu,
                n_static_rows=R.n, g_lo_a=g_lo_a, g_hi_a=g_hi_a, g_lo_b=g_lo_b,
                g_hi_b=g_hi_b, n_arcs=n_arc, roots=roots)


# ================================================================= spanning-tree incumbent
def _subtree_masks(T, K, root):
    """Boolean (|K|, |K|) matrix: row j is the node set of the subtree under K[j]."""
    m = len(K)
    pos = {z: i for i, z in enumerate(K)}
    order = list(nx.dfs_preorder_nodes(T, root))
    parent = nx.dfs_predecessors(T, root)
    sub = np.zeros((m, m), dtype=bool)
    for z in reversed(order):
        i = pos[z]
        sub[i, i] = True
        p = parent.get(z)
        if p is not None:
            sub[pos[p]] |= sub[i]
    return sub


def _component_candidates(H, K, ua_K, ub_K, rho, rng, n_trees, extra_masks=()):
    """Candidate (contiguous both sides) splits of one component.

    Every cut of a spanning tree splits K into two *connected* pieces, so both orientations
    are feasible by construction -- no repair, no rejection sampling.  `n_trees` random
    spanning trees give a diverse pool in O(n_trees * |K| * |E_K|).
    """
    m = len(K)
    pos = {z: i for i, z in enumerate(K)}
    sub = H.subgraph(K)
    eK = np.array([[pos[u], pos[v]] for u, v in sub.edges()], dtype=np.int64) \
        if sub.number_of_edges() else np.zeros((0, 2), dtype=np.int64)

    masks = [np.ones(m, dtype=bool)]                      # all-a (and, mirrored, all-b)
    if m > 1 and eK.shape[0]:
        ew = list(sub.edges())
        for _ in range(max(1, n_trees)):
            w = rng.random(len(ew))
            Gw = nx.Graph()
            Gw.add_nodes_from(K)
            for (u, v), ww in zip(ew, w):
                Gw.add_edge(u, v, weight=float(ww))
            T = nx.minimum_spanning_tree(Gw)
            sm = _subtree_masks(T, K, K[0])
            masks.append(sm[1:] if m > 1 else sm)         # drop the whole-tree row (dup)
    for em in extra_masks:
        masks.append(np.asarray(em, dtype=bool).reshape(1, m))
    M = np.vstack([mm.reshape(-1, m) for mm in masks])
    # de-duplicate splits (identical subtrees recur across trees)
    _, uniq = np.unique(np.packbits(M, axis=1), axis=0, return_index=True)
    M = M[np.sort(uniq)]

    if eK.shape[0]:
        per = (M[:, eK[:, 0]] != M[:, eK[:, 1]]).sum(axis=1).astype(float)
    else:
        per = np.zeros(M.shape[0])
    ga = M @ ua_K
    gb = (~M) @ ub_K
    # both orientations: the mirror of a split is also a valid split
    ga2 = (~M) @ ua_K
    gb2 = M @ ub_K
    cand_mask = np.vstack([M, ~M])
    cand_ga = np.concatenate([ga, ga2])
    cand_gb = np.concatenate([gb, gb2])
    cand_per = np.concatenate([per, per])
    return cand_mask, cand_ga, cand_gb, cand_per


def tree_cut_incumbent(H, nodes, ua, ub, rho=0.0, seed=0, n_trees=8, warm_start=None,
                       max_sweeps=20):
    """A contiguous incumbent from random spanning-tree cuts + coordinate ascent.

    Returns `(to_a, obj)` or `(None, -inf)`.  Feasible by construction; the ascent is over
    components (fairness does not decompose, but the *feasible set* does), so a multi-
    component pair is handled without any repair heuristic (CLAUDE.md trap 6: greedy island
    repair is catastrophic -- this never repairs anything, it only ever picks whole
    contiguous pieces).
    """
    nodes = list(nodes)
    n = len(nodes)
    if n == 0:
        return None, -math.inf
    idx = {z: i for i, z in enumerate(nodes)}
    ua = np.asarray(ua, float)
    ub = np.asarray(ub, float)
    rng = np.random.default_rng(seed)
    comps = components_sorted(H, nodes)

    ws_ok = warm_start is not None and base.is_feasible(H, nodes, set(warm_start))
    ws = set(warm_start) if ws_ok else None

    C = []
    for K in comps:
        ii = np.array([idx[z] for z in K])
        extra = ()
        if ws is not None:
            extra = (np.array([z in ws for z in K], dtype=bool),)
        cm, cga, cgb, cper = _component_candidates(H, K, ua[ii], ub[ii], rho, rng,
                                                   n_trees, extra_masks=extra)
        C.append((ii, cm, cga, cgb, cper))

    tiny = 1e-300

    def _score(ga, gb, per):
        with np.errstate(divide="ignore", invalid="ignore"):
            v = np.where((ga > 0) & (gb > 0),
                         np.log(np.where(ga > 0, ga, tiny)) +
                         np.log(np.where(gb > 0, gb, tiny)) - rho * per, -np.inf)
        return v

    best = (-math.inf, None)
    inits = ("balanced", "a_first", "b_first")
    for init in inits:
        sel = []
        for (_ii, _cm, cga, cgb, cper) in C:
            if init == "balanced":
                s = np.log(cga + 1e-12) + np.log(cgb + 1e-12) - rho * cper
            elif init == "a_first":
                s = cga - rho * cper
            else:
                s = cgb - rho * cper
            sel.append(int(np.argmax(s)))
        GA = sum(C[k][2][sel[k]] for k in range(len(C)))
        GB = sum(C[k][3][sel[k]] for k in range(len(C)))
        PER = sum(C[k][4][sel[k]] for k in range(len(C)))
        for _ in range(max_sweeps):
            changed = False
            for k in range(len(C)):
                _ii, _cm, cga, cgb, cper = C[k]
                ra = GA - cga[sel[k]]
                rb = GB - cgb[sel[k]]
                rp = PER - cper[sel[k]]
                v = _score(ra + cga, rb + cgb, rp + cper)
                j = int(np.argmax(v))
                if not np.isfinite(v[j]):
                    continue
                if j != sel[k]:
                    changed = True
                    sel[k] = j
                GA, GB, PER = ra + cga[j], rb + cgb[j], rp + cper[j]
            if not changed:
                break
        if GA > 0 and GB > 0:
            obj = math.log(GA) + math.log(GB) - rho * float(PER)
            if obj > best[0]:
                to_a = set()
                for k in range(len(C)):
                    ii, cm = C[k][0], C[k][1]
                    m = cm[sel[k]]
                    to_a |= {nodes[int(ii[t])] for t in range(len(ii)) if m[t]}
                best = (obj, to_a)
    if best[1] is None:
        return None, -math.inf
    return best[1], best[0]


# ================================================================= bounds on the gains
def gain_bounds(ua, ub, *, product_floor: Optional[float] = None, bound_g: bool = True):
    """D4: valid `[g_lo, g_hi]` boxes for both gains.

    `product_floor` is `exp(LB_incumbent)`, a valid lower bound on `g_a * g_b` at any
    allocation at least as good as the incumbent (rho * perimeter >= 0 only helps).
    """
    ua = np.asarray(ua, float)
    ub = np.asarray(ub, float)
    g_hi_a = float(np.maximum(ua, 0.0).sum())
    g_hi_b = float(np.maximum(ub, 0.0).sum())
    g_lo_a = g_lo_b = 0.0
    if (ua >= 0).all():
        pos = ua[ua > 0]
        if pos.size:
            g_lo_a = float(pos.min())
    if (ub >= 0).all():
        pos = ub[ub > 0]
        if pos.size:
            g_lo_b = float(pos.min())
    if bound_g and product_floor is not None and product_floor > 0:
        if g_hi_b > 0:
            g_lo_a = max(g_lo_a, product_floor / g_hi_b)
        if g_hi_a > 0:
            g_lo_b = max(g_lo_b, product_floor / g_hi_a)
    # a hair of slack so the incumbent itself can never be cut off by floating point
    g_lo_a = min(g_lo_a * (1.0 - 1e-9), g_hi_a)
    g_lo_b = min(g_lo_b * (1.0 - 1e-9), g_hi_b)
    return g_lo_a, g_hi_a, g_lo_b, g_hi_b


# ======================================================================= solver plumbing
def run_milp(core: Core, ext: Optional[Rows], time_limit: float, *, integral: bool = True,
             use_tol: bool = True, extra_opts: Optional[dict] = None):
    """One `scipy.optimize.milp` call under the harness' conventions.

    Forces `mip_rel_gap = mip_abs_gap = 0` (CLAUDE.md trap 12: HiGHS' default 1e-4 relative
    gap silently turns "optimal" into "gap_limit") and walks a deterministic retry ladder
    when HiGHS returns "Status 4: Solve error".  Returns `(res, flags)` with
    `flags = {"retried_without_tol", "retried_random_seed", "milp_rung", "milp_retries"}`
    (`milp_rung` is the `_LADDER` index that succeeded, or -1 if none did).

    The 2026-08-29 environment issue, diagnosed here (scipy 1.18.1 / HiGHS 1.15.1) on
    `T0_n40_s8__A0_B0` under `flow_selroot` with `disp=True`:

        Solving report ... Status Optimal ... Gap 0%
        ERROR: MIP solver claims optimality, but with num/max/sum
               primal(1/1e-06/1e-06) infeasibilities
        ERROR: Setting model status to Solve error

    So it is *not* an option-parsing failure.  HiGHS proves optimality, then its own
    post-check finds one row violated by 1e-6 in the solution it is about to return and
    downgrades the whole run.  Consequences, all verified on that model:

      * `primal_feasibility_tolerance = 1e-9` makes that post-check strictly harsher, so it
        does contribute -- with `mip_rel_gap = 0` and both 1e-9 tolerances the first master
        already errors, and dropping the tolerances recovers it.  (Loosening the tolerance
        instead does *not* help: 1e-4 and 1e-3 still error, so the check is not simply
        reading the option back.)
      * Once enough tangents are in, *every* option set errors -- default tolerances
        included.  What recovers it is a different search path onto an equally optimal but
        numerically cleaner vertex, and no single perturbation is enough for every model:
        on `T0_n40_s8__A0_B0` `random_seed in {1, 7, 17}` all work while `presolve=False`
        does not, and on `hand_p8` (second OA round) it is exactly the other way round.
        Hence the six-rung `_LADDER`, which crosses the two.  Also useless on both:
        `mip_detect_symmetry`, `mip_heuristic_effort`, `simplex_strategy`, `solver=ipm/pdlp`,
        and any value of `primal_feasibility_tolerance`.  Loosening
        `mip_feasibility_tolerance` to 1e-7/1e-8 does help on `hand_p8` -- consistent with
        the violation being big-M slop `cap * x` on a near-integral x -- but tightening it
        to 1e-10 does not, so it is not a monotone knob and is not used as a rung.
      * Forwarding **`threads`** is unsafe on its own: `threads=1` with nothing else set
        returns "HiGHS Status 0: Not Set" on the same model, so it is never passed.
        Single-threading is the harness' job anyway (the bench pins OMP/OPENBLAS/MKL to 1
        before numpy is imported).

    Both failures are model-dependent, not universal -- the identical option sets solve a
    random dense MILP fine -- which is why this is a retry ladder and not a global setting.
    The ladder is deterministic (fixed seeds, fixed order), so the method stays reproducible
    as the contract requires, and rung 0 is what runs on a healthy model -- the perturbed
    rungs cost nothing unless something has already gone wrong.
    """
    opts = dict(time_limit=max(float(time_limit), 1e-3), mip_rel_gap=0.0, mip_abs_gap=0.0)
    if extra_opts:
        opts.update(extra_opts)
    if use_tol:
        opts.update(_TOL_OPTS)
    con = core.constraint(ext)
    integ = core.integrality if integral else np.zeros(core.n_col)
    bnds = Bounds(core.lo, core.hi)

    def _call(o):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return milp(c=core.c, constraints=con, integrality=integ, bounds=bnds, options=o)

    def _broken(r):
        return (getattr(r, "status", None) == 4
                or "solve error" in str(getattr(r, "message", "")).lower())

    rungs = []
    for delta in _LADDER:
        o = dict(opts)
        if delta.get("drop_tol"):
            for k in _TOL_OPTS:
                o.pop(k, None)
        o.update({k: v for k, v in delta.items() if k != "drop_tol"})
        rungs.append((delta, o))

    flags = dict(retried_without_tol=False, retried_random_seed=False, milp_rung=0,
                 milp_retries=0)
    res = None
    for i, (delta, o) in enumerate(rungs):
        res = _call(o)
        flags["milp_rung"] = i
        flags["milp_retries"] = i
        if not _broken(res):
            flags["retried_without_tol"] = bool(delta.get("drop_tol"))
            flags["retried_random_seed"] = "random_seed" in delta
            return res, flags
    flags["milp_rung"] = -1
    return res, flags
    if use_tol:
        flags["retried_without_tol"] = True
        res = _call({k: v for k, v in opts.items() if k not in _TOL_OPTS})
        if not _broken(res):
            return res, flags
    for sd in _RETRY_SEEDS:
        flags["retried_random_seed"] = True
        res = _call(dict(opts, random_seed=int(sd)))
        if not _broken(res):
            break
    return res, flags


def _dual_bound(res) -> Optional[float]:
    """Valid UB on the true objective from the master's dual bound (`c` is the negated
    objective, so `UB = -mip_dual_bound`)."""
    db = getattr(res, "mip_dual_bound", None)
    if db is None or not np.isfinite(db):
        return None
    return float(-db)


def _round_x(res, n) -> Optional[np.ndarray]:
    x = getattr(res, "x", None)
    if x is None:
        return None
    return np.round(np.asarray(x[:n], float)).astype(bool)


def root_compatible(core: Core, to_a) -> bool:
    """True if `to_a` respects `flow_rooted`'s per-component fixed roots."""
    if core.root_mode != "fixed":
        return True
    to_a = set(to_a)
    for ra, rb in core.roots.values():
        if ra not in to_a or rb in to_a:
            return False
    return True


# ================================================================================ solve
def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          max_iter=60, root_mode="chain", caps="tight", bound_g=True, n_trees=8,
          n_seeds=8, reserve=0.05, **opts) -> base.Result:
    t0 = time.perf_counter()

    def left():
        return time_limit - (time.perf_counter() - t0) - reserve

    nodes = list(nodes)
    n = len(nodes)
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    H = G.subgraph(nodes)
    extra = dict(root_mode=root_mode, caps=caps, bound_g=bool(bound_g),
                 retried_without_tol=False, retried_random_seed=False, stall=False)

    if n == 0:
        return base.Result(status="infeasible", message="flow: empty pair", extra=extra)
    if float(np.maximum(ua, 0).sum()) <= 0 or float(np.maximum(ub, 0).sum()) <= 0:
        return base.Result(status="infeasible", extra=extra,
                           message="flow: one side has no positive utility anywhere "
                                   "-- no allocation gives both gains > 0")

    # ---- incumbent (also the D4 product floor and the OA warm start) ----------------
    inc_to_a, inc_obj = tree_cut_incumbent(H, nodes, ua, ub, rho, seed=seed,
                                           n_trees=n_trees, warm_start=warm_start)
    ratio_v = base.ratio(ua, ub)

    # A rooted restriction may exclude the incumbent.  Then the incumbent is *not* a lower
    # bound on what this formulation bounds from above, and reporting it against a rooted UB
    # would produce the LB > UB contradiction `current.py` documents.  Drop it instead.
    if root_mode == "fixed" and inc_to_a is not None:
        rr = fixed_roots(H, nodes, ua, ub, ratio=ratio_v)
        if any(ra not in inc_to_a or rb in inc_to_a for ra, rb in rr.values()):
            inc_to_a, inc_obj = None, -math.inf

    g_lo_a, g_hi_a, g_lo_b, g_hi_b = gain_bounds(
        ua, ub, product_floor=(math.exp(inc_obj) if inc_to_a is not None
                               and math.isfinite(inc_obj) else None),
        bound_g=bound_g)

    core = build_core(H, nodes, ua, ub, rho, root_mode=root_mode, caps=caps,
                      g_lo_a=g_lo_a, g_hi_a=g_hi_a, g_lo_b=g_lo_b, g_hi_b=g_hi_b,
                      ratio=ratio_v)

    ub_scope = "rooted" if root_mode == "fixed" else "global"
    best_lb, best_to_a = -math.inf, None
    if inc_to_a is not None and math.isfinite(inc_obj):
        best_lb, best_to_a = inc_obj, set(inc_to_a)
        if trace is not None:
            trace.incumbent(best_to_a, best_lb)

    extra.update(g_lo_a=core.g_lo_a, g_hi_a=core.g_hi_a, g_lo_b=core.g_lo_b,
                 g_hi_b=core.g_hi_b, warm_product=(math.exp(inc_obj)
                                                   if math.isfinite(inc_obj) else None),
                 n_cols=core.n_col, n_rows_static=core.n_static_rows, n_arcs=core.n_arcs,
                 n_components=len(core.comps))

    # ---- OA seeds: eight geomspace points on the instance's own range, never constants
    ext = Rows()
    n_tan = 0
    for gh in np.geomspace(max(core.g_lo_a, core.g_hi_a * 1e-6), max(core.g_hi_a, 1e-12),
                           max(2, int(n_seeds))):
        n_tan += int(core.tangent("a", float(gh), ext))
    for gh in np.geomspace(max(core.g_lo_b, core.g_hi_b * 1e-6), max(core.g_hi_b, 1e-12),
                           max(2, int(n_seeds))):
        n_tan += int(core.tangent("b", float(gh), ext))

    UB = math.inf
    iters = 0
    nodes_bb = 0
    placed: set = set()
    status = "iteration_limit"
    message = ""

    for it in range(int(max_iter)):
        rem = left()
        if rem <= 0:
            status = "time_limit"
            message = "flow: wall clock exhausted before the next master solve"
            break
        res, flags = run_milp(core, ext, rem)
        for k, v in flags.items():
            extra[k] = extra.get(k, False) or v
        iters += 1
        nc = getattr(res, "mip_node_count", None)
        if nc:
            nodes_bb += int(nc)
        st = getattr(res, "status", 4)

        if st == 2:
            if it == 0:
                return base.Result(status="infeasible", ub_scope=ub_scope, iters=iters,
                                   n_tangents=n_tan, nodes=nodes_bb, extra=extra,
                                   message="flow: master infeasible on the first solve")
            status = "error"
            message = "flow: master became infeasible after tangents (bug)"
            break
        if st not in (0, 1) or getattr(res, "x", None) is None:
            status = "time_limit" if st == 1 else "error"
            message = f"flow: milp status {st} -- {getattr(res, 'message', '')}"
            break

        db = _dual_bound(res)
        if db is not None and db < UB:
            UB = db
            if trace is not None:
                trace.bound(UB)

        x = _round_x(res, n)
        to_a = {nodes[i] for i in range(n) if x[i]}
        if base.is_feasible(G, nodes, to_a):
            per = base.perimeter(G, nodes, to_a)
            obj = base.objective(ua, ub, base.mask(nodes, to_a), rho, per)
            if math.isfinite(obj) and obj > best_lb:
                best_lb, best_to_a = obj, to_a
                if trace is not None:
                    trace.incumbent(to_a, obj)

        if math.isfinite(UB) and best_to_a is not None and UB - best_lb <= base.CERT_TOL:
            status = "optimal"
            break

        if st == 1:                       # HiGHS stopped on the time limit: bound is valid
            status = "time_limit"
            message = "flow: master hit the time limit"
            break

        ga, gb = base.gains(ua, ub, x)
        added = 0
        for side, gv in (("a", ga), ("b", gb)):
            if not (gv > 0):
                continue
            key = (side, round(float(gv), 12))
            if key in placed:
                continue
            placed.add(key)
            added += int(core.tangent(side, float(gv), ext))
        n_tan += added
        if added == 0:
            extra["stall"] = True
            status = "gap_limit" if best_to_a is not None else "iteration_limit"
            message = ("flow: OA stalled -- the master's rounded point repeats a tangent "
                       "already placed; the reported UB is still valid")
            break
        if it == int(max_iter) - 1:
            status = "gap_limit" if best_to_a is not None else "iteration_limit"
            message = f"flow: max_iter={max_iter} reached"

    if status == "optimal" and (best_to_a is None or not math.isfinite(UB)):
        status = "heuristic" if best_to_a is not None else "error"

    UB_out = UB if math.isfinite(UB) else None
    LB_out = best_lb if best_to_a is not None and math.isfinite(best_lb) else None
    if status == "gap_limit" and UB_out is None:
        status = "heuristic" if best_to_a is not None else "error"
    if status == "heuristic":
        UB_out = None
    return base.Result(status=status, to_a=best_to_a, LB=LB_out, UB=UB_out,
                       ub_scope=ub_scope, iters=iters, n_cuts=0, n_tangents=n_tan,
                       nodes=nodes_bb, extra=extra, message=message)
