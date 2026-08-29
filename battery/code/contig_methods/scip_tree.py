"""
scip_tree.py -- Option A: single-tree branch-and-cut on SCIP (PySCIPOpt), with SCIP's
native `log` and root-free minimal-separator connectivity cuts (PLAN.md W6,
research/contiguity/OPTIONS.md section 2).

Why this exists
---------------
The legacy loop (`contig_methods/current`) restarts a *fresh* MILP for every round of
separator + tangent cuts, so the two cut families' finite-convergence arguments multiply
(CLAUDE.md trap 11 / OPTIONS.md section 12).  HiGHS has no cut-injection callback, so that
multi-tree structure is not fixable inside scipy.  SCIP does have one, and it also detects
the convexity of `z <= log(g)` itself, so the whole problem goes into **one** branch-and-bound
tree with a globally valid dual bound at every moment.

Formulation (A', `formulation="native"`)
----------------------------------------
    maximise   za + zb - rho * sum_e y_e
    s.t.       ga <= sum_z u_a(z) x_z                  ga in [ga_min, sum u_a]
               gb <= sum_z u_b(z) (1 - x_z)            gb in [gb_min, sum u_b]
               za <= log(ga)                           za in [log ga_min, log sum u_a]
               zb <= log(gb)                           zb in [log gb_min, log sum u_b]
               sum_{z : u_a(z) > 0} x_z       >= 1     (g_a > 0; only cuts obj = -inf)
               sum_{z : u_b(z) > 0} (1 - x_z) >= 1     (g_b > 0)
               y_e >= |x_i - x_j|                      (only when rho > 0)
               x contiguous, component-wise            (lazy; see below)

`za <= log(ga)` is convex and SCIP recognises it, so `getDualbound()` is a valid *global*
upper bound on `log g_a + log g_b - rho*perimeter` throughout -- checked at the W6 smoke test
against `territory.nash_exact` to <= 9e-16 with contiguity switched off.

Two details of that model are load-bearing and were both found while porting (2026-08-29):

* **`<=`, not `==`, on the gains.**  The objective increases in ga and gb through the logs, so
  the inequality is tight at every optimum -- but an equality lets presolve *multi-aggregate*
  ga and gb out of the transformed problem, after which `setSolVal` on them raises and every
  in-callback `trySol` dies.  `_set` additionally skips a variable presolve aggregated anyway.
* **`ga_min`, `gb_min` come from the warm start, not from 1e-9** (`_gain_floor`).  Any
  allocation at least as good as an incumbent worth `lb0` has `ga >= exp(lb0)/sum(u_b)`, so
  tightening the bound this way keeps both the argmax and the dual bound valid -- and it takes
  the log's gradient at the lower bound from 1e9 down to about 0.08 on a rescaled instance.
  With the bare floor SCIP's LPs go unstable ("unresolved numerical troubles in LP") on the
  larger pairs at every feasibility tolerance tried.

Numerics
--------
`numerics/feastol` has to be small: SCIP stops when its own primal and dual bounds meet, and
its stored solution may satisfy `za <= log(ga)` only to `feastol`, so the *recomputed*
certificate gap is about `2*feastol` (measured: 1.04e-8 at feastol 1e-8, 1.72e-8 at 1e-7 --
both above `base.CERT_TOL`).  Hence the 1e-9 default.  Small tolerances also make the LP
harder, so two things guard it: `lp/refactorinterval = 100` (accuracy only, no tolerance is
relaxed) and a **retry ladder** -- after a numerical abort the solve is repeated at 1e-7 and
then 1e-6 within the remaining budget, restarting from the best allocation proved so far, and
the merged answer keeps the tightest valid bound of all attempts.

`misc/allowstrongdualreds` and `misc/allowweakdualreds` are **off**.  Dual reductions count
locks over the constraints SCIP can see, and the connectivity cuts (and, in the OA build, the
tangents) are not there yet: with them on, the OA build had presolve fix `za` to its upper
bound and then "certify" the warm start (6.4539 against brute's 6.4545 on the first T0 pair).
This is a correctness requirement for any lazily separated model, not a tuning knob.

Contiguity: root-free lazy minimal-separator cuts
-------------------------------------------------
A constraint handler with `needscons=False` and `chckpriority = enfopriority = -10` sits
*below* the integrality handler, so `consenfolp` only ever sees integral LP solutions and
`conscheck` guards every solution SCIP wants to accept.  Fractional separation
(`conssepalp`) is deliberately **not** implemented (decision at the W6 review): integral-only
separation keeps every cut a genuine combinatorial Benders cut and avoids paying Python
callback cost at every LP.

Feasibility is component-wise (`base.pieces`, PLAN.md C.0 #1): inside each connected
component K of the pair graph, both sides must be connected *or empty*.  For a violating
piece P of side y within K (any piece that is not the largest), with

    u = argmax_{z in P} u_y(z),   v = argmax_{z in largest piece} u_y(z),
    C = a minimal u,v-vertex-separator inside K, seeded at N_K(P) and greedily minimalised,

the cut is

    sum_{w in C} y_w  >=  y_u + y_v - 1          (y_z = x_z on side a, 1 - x_z on side b)

*Validity.*  Any feasible allocation that puts both u and v on side y needs a y-path from u
to v inside K; every u,v-path in K meets C, so some w in C is on side y and the left-hand side
is >= 1 = the right-hand side.  If either endpoint is on the other side the right-hand side is
<= 0 and the cut is slack.  Cuts are global (`local=False`), never removed, and root-free: no
zip is fixed to a side anywhere, so the bound is `ub_scope = "global"` -- unlike `current`,
whose fixed roots make its bound certify only a restriction, and are outright unsound on a
disconnected pair graph (CLAUDE.md trap 13, PLAN.md C.0 #3).

`check_opt=<set|dict>` asserts every cut against a known-optimal allocation before it is
added; the fast test suite runs all of T0 with brute's optimum in that slot, because an
invalid cut is the one failure mode that is silent -- it would just look like a good bound.

The primal side (mechanism (b))
-------------------------------
At the W6 smoke test 5 of the 6 named failures certified in <= 2.1 s, but C7 A3/B3 (205 zips)
stopped at a *tight* dual bound with a worthless incumbent (LB 1.55): SCIP's own heuristics
are contiguity-blind, so almost nothing they produce survives `conscheck`.  Mechanism (b) is a
**primal** problem here, and this module attacks it three ways:

1. `warm_start` -- or, absent one, an internal fallback: the better of a repaired ratio-order
   prefix and the best spanning-tree subtree split (PLAN.md F1) -- turned into a *full*
   variable assignment and handed to `model.addSol` before `optimize()`.  An x-only partial
   solution is accepted but not exploited by SCIP.
2. Every integral point `consenfolp` rejects is also *repaired* (flip whole stray pieces until
   each side is one piece, then a bounded boundary-swap local search) and offered back with
   `trySol` whenever it beats SCIP's own incumbent.
3. Cuts are de-duplicated on `(side, C, u, v)`.  From an LP solution a duplicate cannot
   happen; from a *pseudo* solution it is the norm, which is why `consenfops` returns
   SCIP_SOLVELP rather than spinning (it did: 120,234 calls in 25 s before the fix).

`formulation="oa"` (registry key `scip_tree_oa`) swaps SCIP's native log for tangent cuts
`z <= log(ghat) + (sum u x - ghat)/ghat`, added by the same handler at integral points.  It is
a cross-check on the convexity handling, not the S1 default; it is slower on every pair
measured but has no nonlinear relaxation to destabilise.

Not used: `respect_state` (the harness has already deleted cross-state edges) and
`reductions` (Option E's business).  Utilities come only from `base.utilities`; `G` is never
mutated.
"""
from __future__ import annotations

import contextlib
import math
import os
import time

import numpy as np

from . import base

try:                                            # registry discovery must not explode
    from pyscipopt import (Conshdlr, Eventhdlr, Model, SCIP_EVENTTYPE, SCIP_RESULT,
                           log as _scip_log, quicksum)
    _SCIP_ERROR = None
except Exception as _e:                         # noqa: BLE001
    Conshdlr = Eventhdlr = object                # type: ignore
    Model = SCIP_EVENTTYPE = SCIP_RESULT = None  # type: ignore
    _scip_log = quicksum = None                  # type: ignore
    _SCIP_ERROR = f"{type(_e).__name__}: {_e}"

NAME = "scip_tree"
EXACT = True
MAX_N = None
VARIANTS = {
    # Outer approximation instead of SCIP's native log: the same single tree, but the two
    # `z <= log(g)` constraints are replaced by tangents added at integral points.  A
    # cross-check on the convexity handling, not an S1 default.
    "scip_tree_oa": dict(formulation="oa"),
}

_LOG_FLOOR = 1e-9                # lower bound on g_a, g_b (keeps log defined)
_MAX_LS_MOVES = 50               # boundary-swap moves per repair
_REPAIR_TIME_SHARE = 0.25        # at most this share of the budget goes to in-callback repair


@contextlib.contextmanager
def _quiet_c_stdout():
    """Silence SCIP's C-level stdout for the duration of the block.

    `numerics/feastol = 1e-9` makes SCIP derive an LP tolerance of 1e-12, which it cannot
    honour without GMP; it says so ("Cannot set feasibility tolerance to small value 1e-12
    without GMP - using 1e-10") on file descriptor 1, before -- and regardless of --
    `display/verblevel`.  The message is harmless but it would land in every worker's stdout,
    which the harness keeps clean by design (contiguity_bench: "stdout is not a data channel").
    """
    try:
        saved = os.dup(1)
    except OSError:                                              # no fd 1 to save
        yield
        return
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        yield
    finally:
        os.dup2(saved, 1)
        os.close(devnull)
        os.close(saved)


# ============================================================================ context
class _Ctx:
    """Everything the separator, the repair heuristic and the objective need, precomputed.

    Node order, neighbour lists and component lists are all sorted, so every traversal is
    deterministic (set iteration order is not part of the contract).
    """

    __slots__ = ("nodes", "n", "idx", "ua", "ub", "u_side", "nbrs", "comps", "comp_of",
                 "edges", "rho", "node_set")

    def __init__(self, G, nodes, ua, ub, rho):
        self.nodes = list(nodes)
        self.n = len(self.nodes)
        self.node_set = set(self.nodes)
        self.idx = {z: i for i, z in enumerate(self.nodes)}
        self.ua = np.asarray(ua, float)
        self.ub = np.asarray(ub, float)
        self.u_side = {"a": {z: float(self.ua[i]) for i, z in enumerate(self.nodes)},
                       "b": {z: float(self.ub[i]) for i, z in enumerate(self.nodes)}}
        sub = G.subgraph(self.nodes)
        self.nbrs = {z: tuple(sorted((w for w in sub.neighbors(z)), key=base._sort_key))
                     for z in self.nodes}
        self.edges = [(u, v) for u, v in sorted(
            ((min(e, key=base._sort_key), max(e, key=base._sort_key)) for e in sub.edges()),
            key=lambda e: (base._sort_key(e[0]), base._sort_key(e[1])))]
        self.comps = [sorted(c, key=base._sort_key)
                      for c in sorted(_components(self.nodes, self.nbrs),
                                      key=lambda c: base._sort_key(min(c, key=base._sort_key)))]
        self.comp_of = {}
        for k, K in enumerate(self.comps):
            for z in K:
                self.comp_of[z] = k
        self.rho = float(rho)

    # -- objective -----------------------------------------------------------------
    def mask(self, to_a) -> np.ndarray:
        return np.fromiter((z in to_a for z in self.nodes), dtype=bool, count=self.n)

    def gains(self, to_a):
        x = self.mask(to_a)
        return float(self.ua[x].sum()), float(self.ub[~x].sum())

    def perimeter(self, to_a) -> int:
        return sum(1 for u, v in self.edges if (u in to_a) != (v in to_a))

    def objective(self, to_a) -> float:
        ga, gb = self.gains(to_a)
        if ga <= 0.0 or gb <= 0.0:
            return -math.inf
        val = math.log(ga) + math.log(gb)
        if self.rho:
            val -= self.rho * self.perimeter(to_a)
        return val

    # -- feasibility ---------------------------------------------------------------
    def pieces(self, K, S):
        """Connected pieces of `S` inside the component `K` (a sorted list)."""
        return _components([z for z in K if z in S], self.nbrs)

    def is_feasible(self, to_a) -> bool:
        for K in self.comps:
            if len(self.pieces(K, to_a)) > 1:
                return False
            if len(self.pieces(K, self.node_set - set(to_a))) > 1:
                return False
        return True


def _components(verts, nbrs):
    """Connected components of `verts` (an ordered iterable) under `nbrs`, deterministically.

    Seeds are taken in the given order and each BFS walks sorted neighbour lists, so the
    component list -- and the order inside every component -- is a function of the input
    order alone.
    """
    verts = list(verts)
    remaining = set(verts)
    out = []
    for seed in verts:
        if seed not in remaining:
            continue
        remaining.discard(seed)
        comp = {seed}
        stack = [seed]
        while stack:
            v = stack.pop()
            for w in nbrs[v]:
                if w in remaining:
                    remaining.discard(w)
                    comp.add(w)
                    stack.append(w)
        out.append(comp)
    return out


# ========================================================================== separator
def _reachable(src, K_set, blocked, nbrs):
    seen = {src}
    stack = [src]
    while stack:
        v = stack.pop()
        for w in nbrs[v]:
            if w in K_set and w not in blocked and w not in seen:
                seen.add(w)
                stack.append(w)
    return seen


def _minimal_separator(ctx, K_set, piece, big, side):
    """A minimal u,v-separator inside K, seeded at N_K(piece).

    `u` is the highest-`u_side` zip of the violating piece, `v` the highest of the largest
    piece.  `N_K(piece)` separates them by construction (piece is a *maximal* connected block
    of side `side` inside K, so all its K-neighbours are on the other side).  Candidates are
    then dropped in descending `u_side` order whenever u and v stay disconnected without
    them: one BFS pair per successful drop, O(|C| * |K|) overall.
    """
    us = ctx.u_side[side]
    u = max(sorted(piece, key=base._sort_key), key=lambda z: us[z])
    v = max(sorted(big, key=base._sort_key), key=lambda z: us[z])
    C = set()
    for z in piece:
        for w in ctx.nbrs[z]:
            if w in K_set and w not in piece:
                C.add(w)
    if not C:                                   # piece is a whole component: not a violation
        return None
    Ru = _reachable(u, K_set, C, ctx.nbrs)
    Rv = _reachable(v, K_set, C, ctx.nbrs)
    for w in sorted(sorted(C, key=base._sort_key), key=lambda z: -us[z]):
        if w not in C:
            continue
        nb = ctx.nbrs[w]
        touches_u = any(y in Ru for y in nb)
        touches_v = any(y in Rv for y in nb)
        if touches_u and touches_v:
            continue                            # essential: keep it
        C.discard(w)
        if touches_u or touches_v:              # regions grew; recompute
            Ru = _reachable(u, K_set, C, ctx.nbrs)
            Rv = _reachable(v, K_set, C, ctx.nbrs)
    return u, v, frozenset(C)


def _violations(ctx, to_a):
    """(side, piece, largest_piece, K_set) for every non-largest piece of either side."""
    out = []
    others = ctx.node_set - to_a
    for K in ctx.comps:
        K_set = set(K)
        for side, S in (("a", to_a), ("b", others)):
            ps = ctx.pieces(K, S)
            if len(ps) <= 1:
                continue
            ps.sort(key=lambda P: (-len(P), base._sort_key(min(P, key=base._sort_key))))
            big = ps[0]
            for piece in ps[1:]:
                out.append((side, piece, big, K_set))
    return out


# ====================================================================== repair (primal)
def _repair(ctx, to_a, *, ls_moves=_MAX_LS_MOVES, deadline=None):
    """A feasible allocation near `to_a`, or None.

    Phase 1 (always terminates): while some component has more than one piece on a side, flip
    a whole non-largest piece to the other side, choosing the flip with the best objective.
    Flipping a *maximal* piece P of side y inside K removes one y-piece and, since every
    K-neighbour of P is on the other side, merges >= 1 of the other side's pieces into one --
    so the total piece count strictly drops and the loop ends in <= |K| rounds.

    Phase 2: bounded first-improvement boundary swaps that preserve feasibility.
    """
    cur = set(to_a) & ctx.node_set
    for K in ctx.comps:
        K_set = set(K)
        for _ in range(len(K) + 2):
            if deadline is not None and time.perf_counter() > deadline:
                return None
            pa = ctx.pieces(K, cur)
            pb = ctx.pieces(K, ctx.node_set - cur)
            if len(pa) <= 1 and len(pb) <= 1:
                break
            cands = []
            for side, ps in (("a", pa), ("b", pb)):
                if len(ps) <= 1:
                    continue
                ps = sorted(ps, key=lambda P: (-len(P),
                                               base._sort_key(min(P, key=base._sort_key))))
                for piece in ps[1:]:
                    cands.append((cur - piece) if side == "a" else (cur | piece))
            if not cands:
                break
            cur = max(cands, key=lambda s: (ctx.objective(s),
                                            -len(s)))          # deterministic tie-break
        else:
            return None
        if len(ctx.pieces(K, cur)) > 1 or len(ctx.pieces(K, ctx.node_set - cur)) > 1:
            return None
    if not ctx.is_feasible(cur):
        return None
    if math.isinf(ctx.objective(cur)):
        # phase 1 emptied a side (objective -inf): fall back to a guaranteed-feasible split
        cur, obj = _subtree_splits(ctx, deadline=deadline)
        if cur is None or not math.isfinite(obj):
            return None
    return _local_search(ctx, cur, ls_moves=ls_moves, deadline=deadline)


def _local_search(ctx, cur, *, ls_moves=_MAX_LS_MOVES, deadline=None):
    """First-improvement boundary swaps that keep the allocation feasible."""
    cur = set(cur)
    best_obj = ctx.objective(cur)
    for _ in range(max(int(ls_moves), 0)):
        if deadline is not None and time.perf_counter() > deadline:
            break
        boundary = [z for z in ctx.nodes
                    if any(((w in cur) != (z in cur)) for w in ctx.nbrs[z])]
        moved = False
        for z in boundary:
            cand = (cur - {z}) if z in cur else (cur | {z})
            obj = ctx.objective(cand)
            if obj > best_obj + 1e-12 and ctx.is_feasible(cand):
                cur, best_obj, moved = cand, obj, True
                break
        if not moved:
            break
    return cur


def _ratio_prefix(ctx):
    """Best free (contiguity-blind) prefix in descending u_a/u_b order -- the Appendix B rule."""
    r = base.ratio(ctx.ua, ctx.ub)
    order = sorted(range(ctx.n), key=lambda i: (-r[i], base._sort_key(ctx.nodes[i])))
    ca = np.cumsum(np.concatenate([[0.0], ctx.ua[order]]))
    cb = ctx.ub.sum() - np.cumsum(np.concatenate([[0.0], ctx.ub[order]]))
    with np.errstate(divide="ignore", invalid="ignore"):
        val = np.where((ca > 0) & (cb > 0), np.log(np.maximum(ca, 1e-300)) +
                       np.log(np.maximum(cb, 1e-300)), -np.inf)
    k = int(np.argmax(val))
    return {ctx.nodes[i] for i in order[:k]}


def _subtree_splits(ctx, *, deadline=None):
    """The best allocation among the spanning-tree subtree splits (PLAN.md F1).

    Root a BFS tree at each of the two extreme-ratio zips of each pair component.  For any
    vertex v, `subtree(v)` and its complement inside the component are *both* connected, so
    each of the 2|K| splits is feasible by construction -- no articulation-point test, one
    BFS per root.  Other components go to b, which keeps them feasible too.  This is the
    guaranteed-feasible fallback: it needs no incumbent to repair and cannot fail on a
    connected component of size >= 2.
    """
    best, best_obj = None, -math.inf
    r = base.ratio(ctx.ua, ctx.ub)
    rank = {z: float(r[i]) for i, z in enumerate(ctx.nodes)}
    for K in ctx.comps:
        if len(K) < 2:
            continue
        roots = {max(K, key=lambda z: (rank[z], base._sort_key(z))),
                 min(K, key=lambda z: (rank[z], base._sort_key(z)))}
        for root in sorted(roots, key=base._sort_key):
            if deadline is not None and time.perf_counter() > deadline:
                return (best, best_obj) if best is not None else (None, -math.inf)
            order, parent = [root], {root: None}
            for v in order:                                   # BFS, growing `order` in place
                for w in ctx.nbrs[v]:
                    if w not in parent:
                        parent[w] = v
                        order.append(w)
            subtree = {v: {v} for v in order}
            for v in reversed(order[1:]):                     # children before parents
                subtree[parent[v]] |= subtree[v]
            for v in order[1:]:                               # v == root is the whole component
                cand = set(subtree[v])
                obj = ctx.objective(cand)
                if obj > best_obj:
                    best, best_obj = cand, obj
    return best, best_obj


def _fallback_warm_start(ctx, *, deadline=None):
    """A feasible allocation with no outside help: the better of a repaired ratio prefix and
    the best spanning-tree subtree split."""
    cands = []
    fixed = _repair(ctx, _ratio_prefix(ctx), deadline=deadline)
    if fixed is not None:
        cands.append((ctx.objective(fixed), fixed, "ratio_prefix_repaired"))
    sub, sub_obj = _subtree_splits(ctx, deadline=deadline)
    if sub is not None and math.isfinite(sub_obj):
        cands.append((sub_obj, sub, "subtree_split"))
    if cands:
        obj, cand, src = max(cands, key=lambda c: c[0])
        if math.isfinite(obj):
            return cand, src
    for K in ctx.comps:                       # last resort: one whole component to a
        cand = set(K)
        if ctx.is_feasible(cand) and math.isfinite(ctx.objective(cand)):
            return cand, "single_component"
    return None, "none"


# ================================================================ constraint handler
class _Contig(Conshdlr):
    """Root-free lazy separator cuts; enforcement only, no fractional separation."""

    def __init__(self, ctx, xvars, state):
        super().__init__()
        self.ctx = ctx
        self.x = xvars
        self.st = state                      # the shared mutable solve state (dict)

    # -- helpers -------------------------------------------------------------------
    def _to_a(self, sol):
        get = self.model.getSolVal
        return {z for z in self.ctx.nodes if get(sol, self.x[z]) > 0.5}

    def _cut_expr(self, side, u, v, C):
        if side == "a":
            return quicksum(self.x[w] for w in sorted(C, key=base._sort_key)) >= \
                self.x[u] + self.x[v] - 1
        return quicksum(1 - self.x[w] for w in sorted(C, key=base._sort_key)) >= \
            (1 - self.x[u]) + (1 - self.x[v]) - 1

    def _check_opt(self, side, u, v, C):
        opt = self.st["check_opt"]
        if opt is None:
            return
        val = (lambda z: 1.0 if z in opt else 0.0) if side == "a" else \
              (lambda z: 0.0 if z in opt else 1.0)
        lhs = sum(val(w) for w in C)
        rhs = val(u) + val(v) - 1
        if lhs < rhs - 1e-9:
            msg = (f"scip_tree: invalid separator cut (side={side}, u={u!r}, v={v!r}, "
                   f"|C|={len(C)}) -- it cuts off the reference optimum")
            self.st["invalid_cut"] = msg      # a callback exception may be swallowed by SCIP
            self.model.interruptSolve()
            raise AssertionError(msg)

    def _add_cuts(self, to_a, *, fresh_only=False):
        """One cut per violating piece, both sides, de-duplicated on (side, C, u, v).

        From an *LP* solution a duplicate should be impossible: the earlier copy is a global
        constraint the LP already satisfies, and a cut derived from a violated point is
        violated by it.  Re-adding one is still sound and still cuts the point off, so
        `fresh_only=False` never returns 0 on an infeasible point.  From a *pseudo* solution
        (`consenfops`) duplicates are the norm -- adding a constraint does not move a
        bound-derived point -- so that path passes `fresh_only=True` and asks for an LP
        instead of spinning.  Returns (n_added, n_duplicates_seen).
        """
        st = self.st
        fresh, dup = [], []
        for side, piece, big, K_set in _violations(self.ctx, to_a):
            found = _minimal_separator(self.ctx, K_set, piece, big, side)
            if found is None:
                continue
            u, v, C = found
            key = (side, C, u, v)
            (dup if key in st["cut_keys"] else fresh).append((key, side, u, v, C))
        chosen = fresh if (fresh or fresh_only) else dup
        st["n_dup_cuts"] += len(dup)
        for key, side, u, v, C in chosen:
            self._check_opt(side, u, v, C)
            self.model.addCons(self._cut_expr(side, u, v, C),
                               name=f"sep{st['n_cuts_total']}",
                               local=False, modifiable=False, removable=False)
            st["cut_keys"].add(key)
            st["n_cuts_total"] += 1
        return len(chosen), len(dup)

    # -- callbacks -----------------------------------------------------------------
    def conscheck(self, constraints, solution, checkintegrality, checklprows, printreason,
                  completely):
        self.st["n_check"] += 1
        to_a = self._to_a(solution)
        ok = not _violations(self.ctx, to_a)
        return {"result": SCIP_RESULT.FEASIBLE if ok else SCIP_RESULT.INFEASIBLE}

    def _enforce(self, key):
        st = self.st
        st[key] += 1
        if st["deadline"] is not None and time.perf_counter() > st["deadline"]:
            st["interrupted"] = True
            self.model.interruptSolve()
        if st["trace"] is not None:
            try:
                st["trace"].bound(self.model.getDualbound())
            except Exception:                                    # noqa: BLE001
                pass
        to_a = self._to_a(None)
        st["last_integral"] = to_a
        n, _ = self._add_cuts(to_a)
        if n == 0:
            return {"result": SCIP_RESULT.FEASIBLE}
        _maybe_repair(self.model, self.ctx, st, to_a)
        return {"result": SCIP_RESULT.CONSADDED}

    def consenfolp(self, constraints, nusefulconss, solinfeasible):
        return self._enforce("n_enfolp")

    def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):
        """Pseudo solutions: ask for an LP rather than cut.

        SCIP falls back to pseudo enforcement when the node LP is unresolved ("numerical
        troubles in LP", which the 1e-9 feastol provokes on the larger pairs).  A separator
        cut does not move a *pseudo* solution -- it is built from variable bounds, not from a
        relaxation that the new constraint enters -- so returning CONSADDED here spins
        forever on the same point (120,234 calls in 25 s on C7 A0/B0, found 2026-08-29).
        SCIP_SOLVELP is the documented answer for a handler that cannot enforce a pseudo
        solution: SCIP solves the LP, or branches if it cannot.  The point is still worth a
        repair, so the primal side keeps running.
        """
        st = self.st
        st["n_enfops"] += 1
        if st["deadline"] is not None and time.perf_counter() > st["deadline"]:
            st["interrupted"] = True
            self.model.interruptSolve()
        to_a = self._to_a(None)
        if not _violations(self.ctx, to_a):
            return {"result": SCIP_RESULT.FEASIBLE}
        st["last_integral"] = to_a
        _maybe_repair(self.model, self.ctx, st, to_a)
        n, _ = self._add_cuts(to_a, fresh_only=True)
        return {"result": SCIP_RESULT.CONSADDED if n else SCIP_RESULT.SOLVELP}

    def conslock(self, constraint, locktype, nlockspos, nlocksneg):
        for var in self.x.values():
            self.model.addVarLocks(var, nlockspos + nlocksneg, nlockspos + nlocksneg)


class _OAContig(_Contig):
    """`formulation="oa"`: the same separator, plus log tangents at integral points."""

    def _gvals(self, sol):
        """(g_a, g_b) of a solution, evaluated on x -- not on the `ga`/`gb` variables.

        In the OA formulation nothing ties `ga` to the objective, so the LP parks it at its
        lower bound and a tangent taken there is vacuous (the first OA build added zero
        tangents for exactly this reason).  The tangent must be taken at the *implied* gain.
        """
        get = self.model.getSolVal
        ga = gb = 0.0
        for i, z in enumerate(self.ctx.nodes):
            xv = get(sol, self.x[z])
            ga += float(self.ctx.ua[i]) * xv
            gb += float(self.ctx.ub[i]) * (1.0 - xv)
        return ga, gb

    def _add_tangents(self, sol):
        """`z <= log(ghat) + (sum u x - ghat)/ghat` at the current implied gains."""
        st = self.st
        m = self.model
        added = 0
        for name, lin, var_z in (("a", st["lin_a"], st["V"]["za"]),
                                 ("b", st["lin_b"], st["V"]["zb"])):
            g = st["gvals"][0] if name == "a" else st["gvals"][1]
            z = m.getSolVal(sol, var_z)
            if g <= _LOG_FLOOR or z <= math.log(g) + 1e-11:
                continue
            key = (name, round(float(g), 12))
            if key in st["tangent_keys"]:
                continue
            st["tangent_keys"].add(key)
            m.addCons(var_z <= math.log(g) + (lin() - g) / g,
                      name=f"tan{st['n_tangents']}", local=False, modifiable=False,
                      removable=False)
            st["n_tangents"] += 1
            added += 1
        return added

    def _enforce(self, key):
        st = self.st
        st[key] += 1
        if st["deadline"] is not None and time.perf_counter() > st["deadline"]:
            st["interrupted"] = True
            self.model.interruptSolve()
        if st["trace"] is not None:
            try:
                st["trace"].bound(self.model.getDualbound())
            except Exception:                                    # noqa: BLE001
                pass
        to_a = self._to_a(None)
        st["last_integral"] = to_a
        st["gvals"] = self._gvals(None)
        n_cuts, _ = self._add_cuts(to_a)
        n = n_cuts + self._add_tangents(None)
        if n == 0:
            return {"result": SCIP_RESULT.FEASIBLE}
        _maybe_repair(self.model, self.ctx, st, to_a)
        return {"result": SCIP_RESULT.CONSADDED}

    def conscheck(self, constraints, solution, checkintegrality, checklprows, printreason,
                  completely):
        self.st["n_check"] += 1
        to_a = self._to_a(solution)
        if _violations(self.ctx, to_a):
            return {"result": SCIP_RESULT.INFEASIBLE}
        ga, gb = self._gvals(solution)
        for g, var_z in ((ga, self.st["V"]["za"]), (gb, self.st["V"]["zb"])):
            z = self.model.getSolVal(solution, var_z)
            if g <= _LOG_FLOOR or z > math.log(g) + 1e-9:
                return {"result": SCIP_RESULT.INFEASIBLE}
        return {"result": SCIP_RESULT.FEASIBLE}


# ==================================================================== event handler
class _Events(Eventhdlr):
    """BESTSOLFOUND -> trace.incumbent (every accepted solution has passed conscheck)."""

    def __init__(self, ctx, state):
        super().__init__()
        self.ctx = ctx
        self.st = state

    def eventinit(self):
        self.model.catchEvent(SCIP_EVENTTYPE.BESTSOLFOUND, self)

    def eventexit(self):
        self.model.dropEvent(SCIP_EVENTTYPE.BESTSOLFOUND, self)

    def eventexec(self, event):
        sol = self.model.getBestSol()
        if sol is None:
            return
        get = self.model.getSolVal
        to_a = {z for z in self.ctx.nodes if get(sol, self.st["V"]["x"][z]) > 0.5}
        _record(self.ctx, self.st, to_a)


# ======================================================================== primal glue
def _record(ctx, st, to_a):
    """Register a candidate incumbent (recomputed objective, never SCIP's)."""
    if to_a is None or not ctx.is_feasible(to_a):
        return False
    obj = ctx.objective(to_a)
    if not math.isfinite(obj):
        return False
    if st["best_obj"] is None or obj > st["best_obj"] + 1e-15:
        st["best_obj"] = obj
        st["best_to_a"] = set(to_a)
        if st["trace"] is not None:
            st["trace"].incumbent(to_a, obj)
        return True
    return False


def _set(model, sol, var, val) -> bool:
    """setSolVal that tolerates a variable presolve has aggregated away.

    A multi-aggregated variable's value is *derived* from the active ones, so skipping it is
    correct -- but SCIP raises (and prints from C) rather than ignoring the write, and an
    exception escaping a constraint handler kills the solve (it surfaces only as "Exception
    ignored in PyConsEnfolp").  SCIP multi-aggregates `ga`/`gb` on some instances even from
    the `<=` form, having proved the constraint tight, so the status is checked first.
    """
    try:
        if model.getStage() > 2:                                 # TRANSFORMED or later
            tv = model.getTransformedVar(var)
            if tv is not None and tv.getStatus() == "MULTAGGR":
                return False
    except Exception:                                            # noqa: BLE001
        pass
    try:
        model.setSolVal(sol, var, val)
        return True
    except Exception:                                            # noqa: BLE001
        return False


def _full_solution(model, ctx, V, to_a):
    """A complete variable assignment (x, y, ga, gb, za, zb) -- SCIP ignores partial ones."""
    ga, gb = ctx.gains(to_a)
    if ga <= 0.0 or gb <= 0.0:
        return None
    sol = model.createSol()
    for z in ctx.nodes:
        if not _set(model, sol, V["x"][z], 1.0 if z in to_a else 0.0):
            return None                       # x aggregated away: nothing sensible to hand over
    for (i, j), var in V["y"].items():
        _set(model, sol, var, 1.0 if ((i in to_a) != (j in to_a)) else 0.0)
    _set(model, sol, V["ga"], ga)
    _set(model, sol, V["gb"], gb)
    _set(model, sol, V["za"], math.log(ga))
    _set(model, sol, V["zb"], math.log(gb))
    return sol


def _inject(model, ctx, st, to_a):
    """Offer a feasible allocation to SCIP from inside a callback."""
    sol = _full_solution(model, ctx, st["V"], to_a)
    if sol is None:
        return False
    try:
        accepted = model.trySol(sol, printreason=False, completely=True)
    except Exception:                                            # noqa: BLE001
        return False
    st["n_injected"] += 1 if accepted else 0
    return bool(accepted)


def _maybe_repair(model, ctx, st, to_a):
    """Repair the rejected integral point and hand the result back to SCIP."""
    if not st["repair"]:
        return
    now = time.perf_counter()
    if st["repair_spent"] > st["repair_budget"]:
        return
    if st["deadline"] is not None and now > st["deadline"]:
        return
    cap = min(st["deadline"] if st["deadline"] is not None else now + 1.0,
              now + max(st["repair_budget"] - st["repair_spent"], 0.0))
    try:
        fixed = _repair(ctx, to_a, ls_moves=st["ls_moves"], deadline=cap)
    except Exception:                                            # noqa: BLE001
        fixed = None
    st["repair_spent"] += time.perf_counter() - now
    st["n_repairs"] += 1
    if fixed is None:
        return
    _record(ctx, st, fixed)
    obj = ctx.objective(fixed)
    try:
        incumbent = float(model.getPrimalbound())
    except Exception:                                            # noqa: BLE001
        incumbent = -math.inf
    if math.isfinite(obj) and (not math.isfinite(incumbent) or obj > incumbent + 1e-9):
        _inject(model, ctx, st, fixed)


# =========================================================================== the model
def _gain_floor(ctx, lb0):
    """Valid lower bounds (ga_min, gb_min) implied by a known achievable objective `lb0`.

    Every allocation at least as good as the incumbent has `log ga + log gb >= lb0 + rho*per
    >= lb0`, so `ga >= exp(lb0) / sum(u_b)` and symmetrically -- and the optimum is one of
    those allocations, so tightening the variable bounds this way keeps both the argmax and
    the dual bound valid.

    This is what makes the native (SCIP `log`) build numerically usable.  With the bare
    `1e-9` floor the log's gradient at the lower bound is 1e9, and SCIP's LPs go unstable:
    on the 205-zip C7 A3/B3 pair every feastol from 1e-9 to 1e-8 aborted with "unresolved
    numerical troubles in LP" inside 0.3 s (2026-08-29).  On a rescaled instance the derived
    floor is ~12.6 against a 50 upper bound, i.e. a gradient of 0.08.
    """
    ua_sum, ub_sum = float(ctx.ua.sum()), float(ctx.ub.sum())
    if lb0 is None or not math.isfinite(lb0):
        return _LOG_FLOOR, _LOG_FLOOR
    try:
        ga_min = math.exp(lb0 - math.log(ub_sum)) if ub_sum > 0 else _LOG_FLOOR
        gb_min = math.exp(lb0 - math.log(ua_sum)) if ua_sum > 0 else _LOG_FLOOR
    except (ValueError, OverflowError):
        return _LOG_FLOOR, _LOG_FLOOR
    eps = 1e-12                                   # never cut off the incumbent itself
    ga_min = min(max(ga_min * (1 - eps), _LOG_FLOOR), max(ua_sum, _LOG_FLOOR))
    gb_min = min(max(gb_min * (1 - eps), _LOG_FLOOR), max(ub_sum, _LOG_FLOOR))
    return ga_min, gb_min


def _build_model(ctx, *, rho, time_limit, seed, formulation, feastol, verbose,
                 gain_floor=(_LOG_FLOOR, _LOG_FLOOR), refactor_interval=100):
    m = Model("scip_tree")
    if not verbose:
        m.hideOutput()
        m.setParam("display/verblevel", 0)
    m.setParam("limits/time", float(max(time_limit, 0.01)))
    m.setParam("limits/gap", 0.0)
    m.setParam("limits/absgap", 0.0)
    with _quiet_c_stdout():
        m.setParam("numerics/feastol", float(feastol))
    # Lazy constraints and dual reductions do not mix: SCIP's presolve/propagation may fix a
    # variable on locks counted over the constraints it can *see*, and the separator cuts (and,
    # in the OA formulation, the tangents) are not there yet.  Observed 2026-08-29 on the OA
    # build: with no tangent in the model za has a single up-lock from the objective, so
    # presolve fixed za to its upper bound log(sum u_a) and ga to its lower bound 1e-9 -- and
    # tangents added afterwards could no longer move them, so the method "certified" the warm
    # start (6.4539 against brute's 6.4545 on the first T0 pair).  Both flags off is the
    # documented requirement for lazily separated models.
    m.setParam("misc/allowstrongdualreds", False)
    m.setParam("misc/allowweakdualreds", False)
    m.setParam("parallel/maxnthreads", 1)
    try:
        m.setParam("lp/threads", 1)
    except Exception:                                            # noqa: BLE001
        pass
    m.setParam("randomization/randomseedshift", int(seed))
    if refactor_interval:
        # Refactorise the simplex basis every `refactor_interval` iterations instead of
        # SCIP's automatic choice.  Pure accuracy, no tolerance is relaxed -- and it is what
        # keeps the larger pairs alive: on the 320-zip C7b A1/B1 pair the default setting
        # aborts with "unresolved numerical troubles in LP" at every rung of the feastol
        # ladder (13 s in), while at 100 the same run uses its whole 60 s budget and closes
        # the gap further (7.60e-4 -> 6.93e-4).  Measured 2026-08-29.
        m.setParam("lp/refactorinterval", int(refactor_interval))

    x = {z: m.addVar(vtype="B", name=f"x{i}") for i, z in enumerate(ctx.nodes)}
    ua_sum = float(ctx.ua.sum())
    ub_sum = float(ctx.ub.sum())
    ga_min, gb_min = gain_floor
    ga = m.addVar(lb=ga_min, ub=max(ua_sum, ga_min), name="ga")
    gb = m.addVar(lb=gb_min, ub=max(ub_sum, gb_min), name="gb")
    # `<=`, not `==`: the objective is increasing in ga and gb (through za <= log ga), so the
    # inequality is tight at every optimum, while an *equality* lets SCIP multi-aggregate ga
    # and gb out of the transformed problem -- after which `setSolVal` on them raises
    # "cannot set solution value for multiple aggregated variable" and every in-callback
    # `trySol` dies (found while porting the W6 prototype, 2026-08-29).
    m.addCons(ga <= quicksum(float(ctx.ua[i]) * x[z] for i, z in enumerate(ctx.nodes)))
    m.addCons(gb <= quicksum(float(ctx.ub[i]) * (1 - x[z]) for i, z in enumerate(ctx.nodes)))
    za = m.addVar(lb=math.log(ga_min), ub=math.log(max(ua_sum, ga_min)), name="za")
    zb = m.addVar(lb=math.log(gb_min), ub=math.log(max(ub_sum, gb_min)), name="zb")
    if formulation == "native":
        m.addCons(za <= _scip_log(ga))
        m.addCons(zb <= _scip_log(gb))

    # g_a, g_b > 0: excludes only allocations whose objective is -inf, so the bound stands
    pos_a = [z for i, z in enumerate(ctx.nodes) if ctx.ua[i] > 0]
    pos_b = [z for i, z in enumerate(ctx.nodes) if ctx.ub[i] > 0]
    if pos_a:
        m.addCons(quicksum(x[z] for z in pos_a) >= 1)
    if pos_b:
        m.addCons(quicksum(1 - x[z] for z in pos_b) >= 1)

    y = {}
    obj = za + zb
    if rho > 0 and ctx.edges:
        for k, (i, j) in enumerate(ctx.edges):
            e = m.addVar(vtype="C", lb=0.0, ub=1.0, name=f"y{k}")
            m.addCons(e >= x[i] - x[j])
            m.addCons(e >= x[j] - x[i])
            y[(i, j)] = e
        obj = obj - float(rho) * quicksum(y.values())
    m.setObjective(obj, "maximize")
    V = dict(x=x, ga=ga, gb=gb, za=za, zb=zb, y=y)
    # rebuilt per call: a pyscipopt Expr is consumed by addCons, so it cannot be cached
    V["lin_a"] = lambda: quicksum(float(ctx.ua[i]) * x[z] for i, z in enumerate(ctx.nodes))
    V["lin_b"] = lambda: quicksum(float(ctx.ub[i]) * (1 - x[z]) for i, z in enumerate(ctx.nodes))
    return m, V


# ================================================================================ solve
_FEASTOL_LADDER = (1e-7, 1e-6)      # retried, in order, after a numerical abort


def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          formulation="native", repair=True, feastol=1e-9, check_opt=None,
          verbose=False, ls_moves=_MAX_LS_MOVES, refactor_interval=100,
          **opts) -> base.Result:
    """One branch-and-cut solve, retried at a looser feastol after a numerical abort.

    SCIP can stop with "unresolved numerical troubles in LP -- aborting" -- an engine
    failure, not a model one, and the tighter the feasibility tolerance the likelier it is.
    The retry re-solves the same problem from the best allocation found so far, and the
    merged answer keeps the tightest *valid* bound of all attempts (every attempt's dual
    bound bounds the same optimum, so the minimum of them does too, and the maximum LB is
    still achieved by an allocation this method has exhibited).
    """
    t0 = time.perf_counter()
    deadline0 = t0 + float(time_limit)
    ladder = [float(feastol)] + [f for f in _FEASTOL_LADDER if f > float(feastol) * 1.001]
    merged = None
    attempts = []
    ws = warm_start
    for ft in ladder:
        remaining = deadline0 - time.perf_counter()
        if remaining <= 0.05 and merged is not None:
            break
        res = _solve_once(G, nodes, theta=theta, lam=lam, rho=rho, time_limit=max(remaining, 0.05),
                          seed=seed, warm_start=ws, trace=trace, kappa=kappa,
                          formulation=formulation, repair=repair, feastol=ft,
                          check_opt=check_opt, verbose=verbose, ls_moves=ls_moves,
                          refactor_interval=refactor_interval)
        attempts.append(dict(feastol=ft, status=res.status,
                             scip_status=res.extra.get("scip_status")))
        merged = _merge(merged, res)
        if res.status != "error":
            break
        if res.to_a is not None and res.LB is not None:
            ws = res.to_a                     # restart from the best allocation we did prove
    if merged is None:                        # ladder never ran (no budget at all)
        return base.Result(status="time_limit", message="scip_tree: no time budget")
    merged.extra["attempts"] = attempts
    return merged


def _merge(a: "base.Result", b: "base.Result") -> "base.Result":
    """Keep the better allocation and the tightest valid bound across two attempts."""
    if a is None:
        return b
    ubs = [u for u in (a.UB, b.UB) if u is not None and math.isfinite(u)]
    keep, other = (a, b) if (a.LB is not None and (b.LB is None or a.LB >= b.LB)) else (b, a)
    out = b                                   # the later attempt carries the engine's verdict
    out.to_a = keep.to_a if keep.LB is not None else (b.to_a if b.to_a is not None else a.to_a)
    out.LB = keep.LB
    out.UB = min(ubs) if ubs else None
    out.nodes = a.nodes + b.nodes
    out.iters = a.iters + b.iters
    out.n_cuts = a.n_cuts + b.n_cuts
    out.n_tangents = a.n_tangents + b.n_tangents
    if out.t_first_feasible is None:
        out.t_first_feasible = a.t_first_feasible
    if out.status != "optimal" and out.UB is not None and out.LB is not None \
            and out.UB - out.LB <= base.CERT_TOL:
        out.status = "optimal"
    if out.status == "optimal" and (out.UB is None or out.LB is None
                                    or out.UB - out.LB > base.CERT_TOL):
        out.status = "gap_limit" if out.LB is not None else "time_limit"
    return out


def _solve_once(G, nodes, *, theta, lam, rho, time_limit, seed,
                warm_start=None, trace=None, kappa=0.0, formulation="native", repair=True,
                feastol=1e-9, check_opt=None, verbose=False,
                ls_moves=_MAX_LS_MOVES, refactor_interval=100) -> base.Result:
    t0 = time.perf_counter()
    if _SCIP_ERROR is not None:
        return base.Result(status="error", message=f"scip_tree: pyscipopt unavailable "
                                                   f"({_SCIP_ERROR})")
    if formulation not in ("native", "oa"):
        return base.Result(status="error",
                           message=f"scip_tree: unknown formulation {formulation!r}")
    nodes = list(nodes)
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    ctx = _Ctx(G, nodes, ua, ub, rho)
    deadline = t0 + float(time_limit)

    if check_opt is not None and not isinstance(check_opt, (set, frozenset)):
        check_opt = {z for z in nodes if check_opt[z]}          # accept a 0/1 mapping

    st = dict(V=None, trace=trace, deadline=deadline, check_opt=check_opt,
              cut_keys=set(), tangent_keys=set(), n_cuts_total=0, n_dup_cuts=0,
              n_tangents=0, n_enfolp=0, n_enfops=0, n_check=0, n_repairs=0, n_injected=0,
              best_obj=None, best_to_a=None, last_integral=None, interrupted=False,
              invalid_cut=None,
              repair=bool(repair), ls_moves=int(ls_moves), repair_spent=0.0,
              repair_budget=_REPAIR_TIME_SHARE * float(time_limit),
              lin_a=None, lin_b=None, gvals=(0.0, 0.0), feastol=float(feastol))

    # ------------------------------------------------------------------ warm start
    # Computed *before* the model: its objective is a valid floor on both gains, which is
    # what keeps the log's gradient tame (see `_gain_floor`).
    warm_source = "none"
    ws = None
    if warm_start is not None and not isinstance(warm_start, str):
        cand = set(warm_start) & ctx.node_set
        if ctx.is_feasible(cand) and math.isfinite(ctx.objective(cand)):
            ws, warm_source = cand, "given"
        else:
            fixed = _repair(ctx, cand, ls_moves=ls_moves, deadline=deadline)
            if fixed is not None:
                ws, warm_source = fixed, "given_repaired"
    if ws is None and warm_start != "__none__":                 # "__none__": tests, cold start
        ws, warm_source = _fallback_warm_start(ctx, deadline=deadline)
    if ws is not None:
        _record(ctx, st, ws)

    m, V = _build_model(ctx, rho=rho, time_limit=max(deadline - time.perf_counter(), 0.01),
                        seed=seed, formulation=formulation, feastol=feastol, verbose=verbose,
                        gain_floor=_gain_floor(ctx, st["best_obj"]),
                        refactor_interval=refactor_interval)
    st["V"] = V
    st["lin_a"], st["lin_b"] = V["lin_a"], V["lin_b"]

    hdlr = (_OAContig if formulation == "oa" else _Contig)(ctx, V["x"], st)
    m.includeConshdlr(hdlr, "contig", "component-wise contiguity (lazy separator cuts)",
                      chckpriority=-10, enfopriority=-10, needscons=False)
    m.includeEventhdlr(_Events(ctx, st), "scip_tree_events", "incumbent trace")

    if ws is not None:
        sol = _full_solution(m, ctx, V, ws)
        if sol is not None:
            try:
                m.addSol(sol)
            except Exception:                                    # noqa: BLE001
                warm_source += "_rejected"

    # ------------------------------------------------------------------------ solve
    remaining = deadline - time.perf_counter()
    if remaining <= 0.01:
        return _finish(ctx, st, m, None, t0, formulation, warm_source,
                       forced_status="time_limit",
                       message="scip_tree: budget exhausted before optimize()")
    m.setParam("limits/time", float(remaining))
    err = None
    try:
        m.optimize()
    except Exception as e:                                       # noqa: BLE001
        err = f"{type(e).__name__}: {e}"

    scip_status = None
    try:
        scip_status = m.getStatus()
    except Exception:                                            # noqa: BLE001
        pass
    if st["invalid_cut"] is not None:
        raise AssertionError(st["invalid_cut"])
    if err is not None and "invalid separator cut" in err:
        raise AssertionError(err)
    return _finish(ctx, st, m, scip_status, t0, formulation, warm_source,
                   message="" if err is None else f"scip_tree: {err}",
                   forced_status="error" if err is not None else None)


def _finish(ctx, st, m, scip_status, t0, formulation, warm_source, *,
            forced_status=None, message=""):
    dual = primal = None
    nodes_used = 0
    if m is not None:
        try:
            dual = float(m.getDualbound())
            primal = float(m.getPrimalbound())
            nodes_used = int(m.getNNodes())
        except Exception:                                        # noqa: BLE001
            pass
        # SCIP's own best solution, re-checked and re-scored on our side
        try:
            if m.getNSols() > 0:
                sol = m.getBestSol()
                to_a = {z for z in ctx.nodes if m.getSolVal(sol, st["V"]["x"][z]) > 0.5}
                _record(ctx, st, to_a)
        except Exception:                                        # noqa: BLE001
            pass

    UB = dual if (dual is not None and math.isfinite(dual)) else None
    to_a = st["best_to_a"]
    LB = st["best_obj"]
    if to_a is None:
        to_a = st["last_integral"]
        LB = None

    if forced_status is not None:
        status = forced_status
    elif scip_status == "optimal":
        status = "optimal" if (UB is not None and LB is not None
                               and UB - LB <= base.CERT_TOL) else "gap_limit"
    elif scip_status in ("timelimit", "userinterrupt"):
        status = "time_limit"
    elif scip_status in ("gaplimit", "bestsollimit", "sollimit", "nodelimit",
                         "totalnodelimit", "stallnodelimit", "restartlimit"):
        status = "gap_limit"
    elif scip_status == "infeasible":
        status = "infeasible"
        to_a, LB, UB = None, None, None
    else:
        status = "error"
        message = (message + "; " if message else "") + \
            f"scip_tree: unhandled SCIP status {scip_status!r}"

    if status == "optimal" and (LB is None or UB is None):
        status = "time_limit" if LB is None else "gap_limit"
    if UB is not None and LB is not None and LB > UB:
        UB = None if (LB - UB) > base.CERT_TOL else UB
        if UB is None:
            status = "heuristic" if status == "optimal" else status
            message = (message + "; " if message else "") + \
                "scip_tree: dual bound below a recomputed feasible incumbent -- UB dropped"

    extra = dict(scip_status=scip_status, dual_at_stop=dual, primal_at_stop=primal,
                 n_enfolp=st["n_enfolp"], n_enfops=st["n_enfops"], n_check=st["n_check"],
                 n_repairs=st["n_repairs"], n_injected=st["n_injected"],
                 n_dup_cuts=st["n_dup_cuts"], warm_source=warm_source,
                 formulation=formulation, interrupted=st["interrupted"],
                 repair_spent=round(st["repair_spent"], 4))
    if status == "heuristic":
        UB = None
    return base.Result(status=status, to_a=to_a, LB=LB, UB=UB, ub_scope="global",
                       iters=st["n_enfolp"], n_cuts=len(st["cut_keys"]),
                       n_tangents=st["n_tangents"], nodes=nodes_used,
                       extra=extra, message=message)
