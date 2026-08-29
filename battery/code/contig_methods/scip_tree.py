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

Formulation (A', "native")
--------------------------
    maximise   za + zb - rho * sum_e y_e
    s.t.       ga == sum_z u_a(z) x_z                 ga in [1e-9, sum u_a]
               gb == sum_z u_b(z) (1 - x_z)           gb in [1e-9, sum u_b]
               za <= log(ga)                          za, zb in [log 1e-9, log sum u]
               zb <= log(gb)
               sum_{z : u_a(z) > 0} x_z       >= 1     (ga > 0; excludes only obj = -inf)
               sum_{z : u_b(z) > 0} (1 - x_z) >= 1     (gb > 0)
               y_e >= |x_i - x_j|                      (only when rho > 0)
               x contiguous, component-wise            (lazy, below)

`za <= log(ga)` is a convex constraint that SCIP recognises, so `getDualbound()` is a valid
*global* upper bound on `log g_a + log g_b - rho*perimeter` throughout -- verified at the W6
smoke test against `territory.nash_exact` to <= 9e-16 with contiguity switched off.

`numerics/feastol = 1e-9` is **required**: at SCIP's 1e-6 default the certificate carries
~1e-7 of slack, which is above `base.CERT_TOL`.  (SCIP prints "Cannot set feasibility
tolerance to 1e-12 without GMP -- using 1e-10" when it clamps its dependent tolerances; that
message is harmless and is suppressed at verblevel 0.)

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
to v inside K; every u,v-path in K meets C, so some w in C is on side y and the left side is
>= 1 = the right side.  If either endpoint is on the other side the right side is <= 0 and the
cut is slack.  The cut is global (`local=False`), never removed, and root-free: no zip is
fixed to a side anywhere, so the bound is `ub_scope = "global"` (unlike `current`, whose
fixed roots make its bound certify only a restriction -- PLAN.md C.0 #3).

`check_opt=<set|dict>` asserts every cut against a known-optimal allocation before it is
added; the fast test suite runs all of T0 with brute's optimum in that slot, because an
invalid cut is the one failure mode that is silent (it would just look like a good bound).

The primal side (mechanism (b))
-------------------------------
At the W6 smoke test 5 of the 6 named failures certified in <= 2.1 s, but C7 A3/B3 (205 zips)
stopped at a *tight* dual bound with a worthless incumbent: SCIP's own heuristics are
contiguity-blind, so almost nothing they produce survives `conscheck`.  Mechanism (b) is
therefore a **primal** problem here, and this module attacks it three ways:

1. `warm_start` (or, absent one, an internal ratio-prefix + repair fallback) is turned into a
   *full* variable assignment and handed to `model.addSol` before `optimize()` -- an x-only
   partial solution is accepted but not exploited by SCIP.
2. Every integral point that `consenfolp` rejects is also *repaired* into a feasible
   allocation (flip the cheapest stray piece until the piece count reaches 1 per side, then a
   bounded boundary-swap local search) and offered back with `trySol`.
3. Cuts are de-duplicated on `(side, C, u, v)` across the whole solve.

Not used: `respect_state` (the harness has already deleted cross-state edges) and
`reductions` (Option E's business).  Utilities come only from `base.utilities`; `G` is never
mutated.
"""
from __future__ import annotations

import math
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


def _fallback_warm_start(ctx, *, deadline=None):
    """A feasible allocation with no outside help: repaired ratio prefix, else all-but-one."""
    cand = _repair(ctx, _ratio_prefix(ctx), deadline=deadline)
    if cand is not None:
        return cand, "ratio_prefix_repaired"
    # last resort: one component entirely to a, the rest to b (always feasible when it scores)
    for K in ctx.comps:
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

    def _add_cuts(self, to_a):
        """One cut per violating piece, both sides, de-duplicated on (side, C, u, v)."""
        st = self.st
        fresh, dup = [], []
        for side, piece, big, K_set in _violations(self.ctx, to_a):
            found = _minimal_separator(self.ctx, K_set, piece, big, side)
            if found is None:
                continue
            u, v, C = found
            key = (side, C, u, v)
            (dup if key in st["cut_keys"] else fresh).append((key, side, u, v, C))
        # A cut derived from a violated integral point is itself violated by that point, so a
        # "duplicate" should be impossible (the earlier copy is a global constraint the LP
        # already satisfies).  If one turns up anyway, re-adding it is still sound and still
        # cuts the point off -- never silently return FEASIBLE on an infeasible point.
        chosen = fresh if fresh else dup
        st["n_dup_cuts"] += len(dup) if fresh else 0
        for key, side, u, v, C in chosen:
            self._check_opt(side, u, v, C)
            self.model.addCons(self._cut_expr(side, u, v, C),
                               name=f"sep{st['n_cuts_total']}",
                               local=False, modifiable=False, removable=False)
            st["cut_keys"].add(key)
            st["n_cuts_total"] += 1
        return len(chosen)

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
        n = self._add_cuts(to_a)
        if n == 0:
            return {"result": SCIP_RESULT.FEASIBLE}
        _maybe_repair(self.model, self.ctx, st, to_a)
        return {"result": SCIP_RESULT.CONSADDED}

    def consenfolp(self, constraints, nusefulconss, solinfeasible):
        return self._enforce("n_enfolp")

    def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):
        return self._enforce("n_enfops")

    def conslock(self, constraint, locktype, nlockspos, nlocksneg):
        for var in self.x.values():
            self.model.addVarLocks(var, nlockspos + nlocksneg, nlockspos + nlocksneg)


class _OAContig(_Contig):
    """`formulation="oa"`: the same separator, plus log tangents at integral points."""

    def _add_tangents(self, to_a):
        st = self.st
        m = self.model
        added = 0
        for name, var_g, var_z, gval in (
                ("a", st["V"]["ga"], st["V"]["za"], None),
                ("b", st["V"]["gb"], st["V"]["zb"], None)):
            g = m.getSolVal(None, var_g)
            z = m.getSolVal(None, var_z)
            if g <= _LOG_FLOOR:
                continue
            if z <= math.log(g) + 1e-9:
                continue
            key = (name, round(float(g), 12))
            if key in st["tangent_keys"]:
                continue
            st["tangent_keys"].add(key)
            m.addCons(var_z <= math.log(g) + (var_g - g) / g,
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
        n = self._add_cuts(to_a) + self._add_tangents(to_a)
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
        m = self.model
        for var_g, var_z in ((self.st["V"]["ga"], self.st["V"]["za"]),
                             (self.st["V"]["gb"], self.st["V"]["zb"])):
            g = m.getSolVal(solution, var_g)
            z = m.getSolVal(solution, var_z)
            if g <= _LOG_FLOOR or z > math.log(g) + 1e-7:
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
def _build_model(ctx, *, rho, time_limit, seed, formulation, feastol, verbose):
    m = Model("scip_tree")
    if not verbose:
        m.hideOutput()
        m.setParam("display/verblevel", 0)
    m.setParam("limits/time", float(max(time_limit, 0.01)))
    m.setParam("limits/gap", 0.0)
    m.setParam("limits/absgap", 0.0)
    m.setParam("numerics/feastol", float(feastol))
    m.setParam("parallel/maxnthreads", 1)
    try:
        m.setParam("lp/threads", 1)
    except Exception:                                            # noqa: BLE001
        pass
    m.setParam("randomization/randomseedshift", int(seed))

    x = {z: m.addVar(vtype="B", name=f"x{i}") for i, z in enumerate(ctx.nodes)}
    ua_sum = float(ctx.ua.sum())
    ub_sum = float(ctx.ub.sum())
    ga = m.addVar(lb=_LOG_FLOOR, ub=max(ua_sum, _LOG_FLOOR), name="ga")
    gb = m.addVar(lb=_LOG_FLOOR, ub=max(ub_sum, _LOG_FLOOR), name="gb")
    # `<=`, not `==`: the objective is increasing in ga and gb (through za <= log ga), so the
    # inequality is tight at every optimum, while an *equality* lets SCIP multi-aggregate ga
    # and gb out of the transformed problem -- after which `setSolVal` on them raises
    # "cannot set solution value for multiple aggregated variable" and every in-callback
    # `trySol` dies (found while porting the W6 prototype, 2026-08-29).
    m.addCons(ga <= quicksum(float(ctx.ua[i]) * x[z] for i, z in enumerate(ctx.nodes)))
    m.addCons(gb <= quicksum(float(ctx.ub[i]) * (1 - x[z]) for i, z in enumerate(ctx.nodes)))
    lo = math.log(_LOG_FLOOR)
    za = m.addVar(lb=lo, ub=math.log(max(ua_sum, _LOG_FLOOR)), name="za")
    zb = m.addVar(lb=lo, ub=math.log(max(ub_sum, _LOG_FLOOR)), name="zb")
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
    return m, dict(x=x, ga=ga, gb=gb, za=za, zb=zb, y=y)


# ================================================================================ solve
def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          formulation="native", repair=True, feastol=1e-9, check_opt=None,
          verbose=False, ls_moves=_MAX_LS_MOVES, **opts) -> base.Result:
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
              repair_budget=_REPAIR_TIME_SHARE * float(time_limit))

    m, V = _build_model(ctx, rho=rho, time_limit=max(deadline - time.perf_counter(), 0.01),
                        seed=seed, formulation=formulation, feastol=feastol, verbose=verbose)
    st["V"] = V

    hdlr = (_OAContig if formulation == "oa" else _Contig)(ctx, V["x"], st)
    m.includeConshdlr(hdlr, "contig", "component-wise contiguity (lazy separator cuts)",
                      chckpriority=-10, enfopriority=-10, needscons=False)
    m.includeEventhdlr(_Events(ctx, st), "scip_tree_events", "incumbent trace")

    # ------------------------------------------------------------------ warm start
    warm_source = "none"
    ws = None
    if warm_start is not None:
        cand = set(warm_start) & ctx.node_set
        if ctx.is_feasible(cand) and math.isfinite(ctx.objective(cand)):
            ws, warm_source = cand, "given"
        else:
            fixed = _repair(ctx, cand, ls_moves=ls_moves, deadline=deadline)
            if fixed is not None:
                ws, warm_source = fixed, "given_repaired"
    if ws is None:
        ws, warm_source = _fallback_warm_start(ctx, deadline=deadline)
    if ws is not None:
        _record(ctx, st, ws)
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
