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
relaxed) and a **retry ladder** -- after a numerical abort the solve is repeated at 1e-7, then
1e-6, then once more in the OA formulation, each time within the remaining budget and
restarting from the best allocation proved so far.  Every attempt bounds the same optimum, so
the merged answer keeps the smallest UB and the largest LB of all of them, and a rung that
adds nothing is simply discarded.

**The ladder has to be driven off `extra["retryable"]`, not off the status** (W6b,
2026-08-30).  An LP abort reaches `_finish` as a raised `Exception: SCIP: error in LP solver!`
with `getStatus() == "unknown"`, and `_finish` deliberately rewrites that to `time_limit` when
valid bounds survive, so that `errors` in the harness summary counts crashes only.  `solve`
used to continue only on status `error`, so it never continued at all: every S2 pair of 124
zips or more returned after 1-58 s of a **1200 s** budget with the 1e-7, 1e-6 and OA rungs
unrun.  `_retryable` now answers the real question -- did SCIP consume the budget or certify?
-- and `_short_stop` adds the other half of it: a SCIP `timelimit` fired well inside the wall
time the rung was actually given (seen at 57 s of 106 s under harness load) is SCIP's clock
talking, not ours, and is retried like an abort.  When the ladder runs out with budget left,
further OA rungs are appended at a shifted seed up to `max_rungs`.

Effect on the seven S2 stragglers, same 1200 s cap, ρ=0 (`w6b_2026-08-30`; S2 -> W6b):
124 zips 4.3e-3 -> 1.1e-07 (219 s), 135 8.8e-4 -> 3.0e-08 (281 s), 169 4.9e-3 -> 4.2e-3,
197 5.8e-3 -> 4.2e-3, 205 3.4e-3 -> 3.4e-4, 320 1.4e-3 -> 1.3e-4, 464 1.2e-2 -> 2.3e-3.
Four of the seven now beat `flow_pwl`'s 1200 s bound, and the two smallest are at their
tolerance floor rather than at a search limit.  The two certified controls in the same run
(77 and 114 zips) still certify in 0.8 s and 0.08 s on the first rung.

*LP settings swept and rejected* (five pairs, 120 s, 2026-08-30; every number below within
+-30 % of the default, i.e. inside the run-to-run spread): `lp/scaling = 2`,
`lp/checkstability = False`, `lp/refactorinterval = 10` (the 10..100 sweep already recorded
below), `constraints/nonlinear/tightenlpfeastol = False` (the setting that asks for the
1e-12 LP tolerance -- turning it off changed nothing measurable), and two that turned out to
be no-ops on this model: `lp/fastmip = 0` and `numerics/lpfeastolfactor = 1000`.  None of
them stopped the native rung aborting.  The one setting that did anything is primal simplex
(`lp/initalgorithm = lp/resolvealgorithm = "p"`), which keeps the 1e-6 native rung alive to
the cap on the 464-zip pair (gap 1.7e-3 twice, against 3.3-3.6e-3 for the default) while
costing 10-20 % of the gap on three of the other four large pairs; it is kept as the
`scip_tree_psimplex` variant rather than promoted, because the sign of the effect is
instance-dependent.  `lp_params` is the escape hatch that made the sweep possible and stays
for the next one.

`misc/allowstrongdualreds` and `misc/allowweakdualreds` are **off**.  Dual reductions count
locks over the constraints SCIP can see, and the connectivity cuts (and, in the OA build, the
tangents) are not there yet: with them on, the OA build had presolve fix `za` to its upper
bound and then "certify" the warm start (6.4539 against brute's 6.4545 on the first T0 pair).
This is a correctness requirement for any lazily separated model, not a tuning knob.

Contiguity: root-free lazy minimal-separator cuts
-------------------------------------------------
A constraint handler with `needscons=False` and `chckpriority = enfopriority = -10` sits
*below* the integrality handler, so `consenfolp` only ever sees integral LP solutions and
`conscheck` guards every solution SCIP wants to accept.

Fractional separation (`conssepalp` / `conssepasol`, added in W6b; skipped at the W6 review)
runs **at the root only** by default and is bounded by `max_sepa_rounds` and
`max_sepa_cuts`.  For side y and a threshold t, `S = {z : y_z >= t}` is the part of the graph
the LP has committed to y; if S splits inside a pair component K, each non-largest piece P
gives the same cut with `C` a minimal separator seeded at `N_K(P)`, and it is added only when
the LP point violates it by more than 1e-6.  Validity is untouched -- the cut family, the
component-wise scope and the absence of roots are the same, and `_check_opt` audits every
fractional cut against the reference optimum on all 13 T0 pairs -- because *any* u,v-separator
gives a valid cut, however u, v and C were chosen.  Measured effect is small and mixed: at a
120 s cap it improves the gap on three of five large pairs (124, 320, 464) and is neutral to
slightly worse on the other two, and its clearest win is on the OA rung's dual bound at 464
zips (6.4789 with, 6.5468 without).  Off with `sepa_frac=False`.

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

1. `warm_start` -- or, absent one and with `mip_start="f1"` (the default), W5's
   `warm.solve(method="f1")` run for at most 5 % of the budget (cap 30 s) -- turned into a
   *full* variable assignment and handed to `model.addSol` before `optimize()`.  An x-only
   partial solution is accepted but not exploited by SCIP.  `mip_start="internal"` falls back
   to this module's own construction (the better of a repaired ratio-order prefix and the best
   spanning-tree subtree split, PLAN.md F1) and reproduces the S2 behaviour; `mip_start=None`
   is the same thing.  The incumbent matters twice over: it is the LB, and through
   `_gain_floor` it is what keeps the native log's LPs stable.
2. Every integral point `consenfolp` rejects is also *repaired* (flip whole stray pieces until
   each side is one piece, then a bounded boundary-swap local search) and offered back with
   `trySol` whenever it beats SCIP's own incumbent.
3. Cuts are de-duplicated on `(side, C, u, v)`.  From an LP solution a duplicate cannot
   happen; from a *pseudo* solution it is the norm, which is why `consenfops` returns
   SCIP_SOLVELP rather than spinning (it did: 120,234 calls in 25 s before the fix).

`formulation="oa"` (registry key `scip_tree_oa`) swaps SCIP's native log for tangent cuts
`z <= log(ghat) + (sum u x - ghat)/ghat`, added by the same handler at integral points.  It is
a cross-check on the convexity handling, not the S1 default: it is slower on every pair that
`native` certifies, but it has no nonlinear relaxation to destabilise, which is why it is also
the ladder's last rung.

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
    # Primal simplex instead of SCIP's automatic choice.  The one LP setting in the W6b
    # sweep that changed anything: on the 464-zip C7b A0/B0 pair it is what keeps the 1e-6
    # native rung alive to the cap (gap 1.7e-3 against 3.3e-3 for the default, which falls
    # through to the OA rung), while costing 10-20 % of the gap on three of the other four
    # large pairs.  Kept as a variant, not promoted, because the sign of the effect is
    # instance-dependent.
    "scip_tree_psimplex": dict(lp_params={"lp/initalgorithm": "p",
                                          "lp/resolvealgorithm": "p"}),
}

_LOG_FLOOR = 1e-9                # lower bound on g_a, g_b (keeps log defined)
_MAX_LS_MOVES = 50               # boundary-swap moves per repair
_REPAIR_TIME_SHARE = 0.25        # at most this share of the budget goes to in-callback repair
# ------------------------------------------------------------------------------- W6d
# The 2026-08-30 primal/dual diagnostic (RESULTS.md section "Primal/dual") found the
# 1200 s incumbents on the 169/197/464-zip pairs were not even 1-swap locally optimal:
# `_repair`'s descent is truncated by `ls_moves` and the 25% repair budget share, and
# SCIP's own accepted solutions are never descended at all.  W6d wires the existing
# first-improvement descent to *convergence* on every new incumbent (`_polish`, its own
# absolute per-call cap, outside the repair budget share) and takes the F1 MIP start
# through a short kick-and-descend loop (`_ils_start`, the ils_diag.py pattern).
_POLISH_MOVES = 10 ** 9          # "to convergence": descent stops only at a local optimum
_POLISH_TIME = 5.0               # absolute per-call cap so a callback cannot starve the tree
_ILS_START_TIME = 5.0            # kick-and-descend budget for the MIP start
_ILS_MIN_N = 100                 # below this the first rung certifies in well under a second,
                                 # so an ILS start would only delay it (S0 t->cert 0.029 s)
_ILS_STALE_KICKS = 40            # stop the loop after this many non-improving kicks


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


def _minimal_separator(ctx, K_set, piece, big, side, pick=None):
    """A minimal u,v-separator inside K, seeded at N_K(piece).

    `u` is the highest-weight zip of the violating piece, `v` the highest of the largest
    piece; the weight is `u_side` by default and the LP value `pick` when the caller is
    separating a *fractional* point (there the cut's right-hand side is `x_u + x_v - 1`, so
    the largest x is what makes it bite).  `N_K(piece)` separates them by construction --
    `piece` is a *maximal* connected block inside K, so all its K-neighbours are outside it
    and every u,v-path in K meets them.  Candidates are then dropped in descending weight
    order whenever u and v stay disconnected without them: one BFS pair per successful drop,
    O(|C| * |K|) overall.  Validity does not depend on how u, v or C were chosen -- any
    u,v-separator gives a valid cut -- so the fractional caller reuses this unchanged.
    """
    us = ctx.u_side[side] if pick is None else pick
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


def _polish(ctx, st, to_a, *, cap=_POLISH_TIME):
    """W6d: first-improvement descent run to convergence on an incumbent.

    Unlike the in-repair descent this is not truncated by `ls_moves` or charged to the
    repair budget share -- the diagnostic showed the truncation left +1e-3-nat improvements
    one swap away after 1200 s.  A per-call absolute cap (and the global deadline) is the
    only limit, and it is only ever called on a *new best* allocation, so the number of
    calls is bounded by the number of incumbent improvements.
    """
    if to_a is None:
        return None
    now = time.perf_counter()
    deadline = now + cap
    if st["deadline"] is not None:
        deadline = min(deadline, st["deadline"])
    out = _local_search(ctx, to_a, ls_moves=_POLISH_MOVES, deadline=deadline)
    st["n_polish"] += 1
    st["polish_spent"] += time.perf_counter() - now
    return out


def _ils_start(ctx, start, seed, budget):
    """W6d: kick-and-descend on the MIP start (the ils_diag.py loop on ctx primitives).

    kick = up to k in [2, 12] random feasibility-preserving boundary flips (worse accepted);
    descend = `_local_search` to convergence; accept if better, else keep with prob 0.05.
    Returns the best allocation seen (never worse than the descended start).
    """
    rng = np.random.default_rng(seed)
    deadline = time.perf_counter() + float(budget)
    cur = _local_search(ctx, set(start), ls_moves=_POLISH_MOVES, deadline=deadline)
    best, best_obj = set(cur), ctx.objective(cur)
    cur_obj = best_obj
    stale = 0
    while time.perf_counter() < deadline and stale < _ILS_STALE_KICKS:
        k = int(rng.integers(2, 13))
        cand = set(cur)
        for _ in range(20 * k):
            if k <= 0:
                break
            z = ctx.nodes[int(rng.integers(ctx.n))]
            if not any(((w in cand) != (z in cand)) for w in ctx.nbrs[z]):
                continue                                          # interior: no boundary move
            trial = (cand - {z}) if z in cand else (cand | {z})
            if trial and (ctx.node_set - trial) and ctx.is_feasible(trial) \
                    and math.isfinite(ctx.objective(trial)):
                cand = trial
                k -= 1
        cand = _local_search(ctx, cand, ls_moves=_POLISH_MOVES, deadline=deadline)
        if not ctx.is_feasible(cand):
            continue
        o = ctx.objective(cand)
        if o > cur_obj + 1e-12 or rng.random() < 0.05:
            cur, cur_obj = set(cand), o
        if o > best_obj + 1e-12:
            best, best_obj = set(cand), o
            stale = 0
        else:
            stale += 1
    return best, best_obj


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

    # -- fractional separation (W6b deliverable 3) ---------------------------------
    def _frac_values(self, sol, side):
        get = self.model.getSolVal
        if side == "a":
            return {z: float(get(sol, self.x[z])) for z in self.ctx.nodes}
        return {z: 1.0 - float(get(sol, self.x[z])) for z in self.ctx.nodes}

    def _frac_candidates(self, sol):
        """Violated separator cuts read off the *support* of a fractional point.

        For side y and a threshold t, `S = {z : y_z >= t}` is the part of the graph the LP
        has already committed to y.  If S splits into several pieces inside a pair component
        K, the LP is paying for a y-territory that is not connected, and each non-largest
        piece P yields the cut `sum_{w in C} y_w >= y_u + y_v - 1` with `C` a minimal
        separator seeded at `N_K(P)` (Validi, Buchanan & Lykhovyd 2022 sec.4 in the vertex-cut
        form this module already uses at integral points).  The cut is kept only when the LP
        point actually violates it by more than 1e-6, so a round that finds nothing costs one
        pass over the graph and returns DIDNOTFIND.

        Nothing here touches the validity argument: the cut is the same family, still
        root-free and still component-wise (trap 13), and `_check_opt` audits every one of
        them against the reference optimum in the tests.
        """
        st, ctx = self.st, self.ctx
        out = []
        for side in ("a", "b"):
            f = self._frac_values(sol, side)
            for t in st["sepa_thresholds"]:
                for K in ctx.comps:
                    K_set = set(K)
                    S = [z for z in K if f[z] >= t]
                    if len(S) < 2:
                        continue
                    ps = _components(S, ctx.nbrs)
                    if len(ps) <= 1:
                        continue
                    ps.sort(key=lambda P: (-sum(f[z] for z in P), -len(P),
                                           base._sort_key(min(P, key=base._sort_key))))
                    big = ps[0]
                    for piece in ps[1:]:
                        got = _minimal_separator(ctx, K_set, piece, big, side, pick=f)
                        if got is None:
                            continue
                        u, v, C = got
                        key = (side, C, u, v)
                        if key in st["cut_keys"]:
                            continue           # already a global constraint; the LP obeys it
                        viol = (f[u] + f[v] - 1.0) - sum(f[w] for w in C)
                        if viol > 1e-6:
                            out.append((viol, key, side, u, v, C))
        out.sort(key=lambda c: (-c[0], c[2], base._sort_key(c[3]), base._sort_key(c[4]),
                                tuple(sorted((base._sort_key(w) for w in c[5])))))
        return out

    def _separate_frac(self, sol):
        st = self.st
        if not st["sepa_frac"] or st["sepa_rounds"] >= st["max_sepa_rounds"]:
            return {"result": SCIP_RESULT.DIDNOTRUN}
        try:
            depth = int(self.model.getDepth())
        except Exception:                                        # noqa: BLE001
            depth = 0
        if depth > st["max_sepa_depth"]:
            return {"result": SCIP_RESULT.DIDNOTRUN}
        if st["deadline"] is not None and time.perf_counter() > st["deadline"]:
            st["interrupted"] = True
            self.model.interruptSolve()
            return {"result": SCIP_RESULT.DIDNOTRUN}
        st["sepa_rounds"] += 1
        try:
            cands = self._frac_candidates(sol)
        except Exception:                                        # noqa: BLE001
            return {"result": SCIP_RESULT.DIDNOTRUN}
        if not cands:
            return {"result": SCIP_RESULT.DIDNOTFIND}
        for _viol, key, side, u, v, C in cands[:st["max_sepa_cuts"]]:
            if key in st["cut_keys"]:
                continue
            self._check_opt(side, u, v, C)
            self.model.addCons(self._cut_expr(side, u, v, C),
                               name=f"fsep{st['n_cuts_total']}",
                               local=False, modifiable=False, removable=False)
            st["cut_keys"].add(key)
            st["n_cuts_total"] += 1
            st["n_sepa_cuts"] += 1
        return {"result": SCIP_RESULT.CONSADDED}

    def conssepalp(self, constraints, nusefulconss):
        return self._separate_frac(None)

    def conssepasol(self, constraints, nusefulconss, solution):
        return self._separate_frac(solution)

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
        if not _record(self.ctx, self.st, to_a) or self.st["in_polish"]:
            return
        # W6d: SCIP's own accepted solutions were never descended at all (the diagnostic
        # found them not 1-swap optimal after 1200 s).  Descend to convergence, and hand an
        # improvement back so the tree prunes with it.  `in_polish` stops the recursion a
        # successful `trySol` (-> BESTSOLFOUND -> here) would otherwise start.
        self.st["in_polish"] = True
        try:
            polished = _polish(self.ctx, self.st, to_a)
            if polished is not None and _record(self.ctx, self.st, polished):
                _inject(self.model, self.ctx, self.st, polished)
        except Exception:                                        # noqa: BLE001
            pass                                  # a polish failure must never kill the solve
        finally:
            self.st["in_polish"] = False


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
    if _record(ctx, st, fixed):
        # W6d: a repaired point good enough to become the incumbent gets the full descent
        # (outside the repair budget share -- see `_polish`).
        polished = _polish(ctx, st, fixed)
        if polished is not None and _record(ctx, st, polished):
            fixed = polished
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
                 gain_floor=(_LOG_FLOOR, _LOG_FLOOR), refactor_interval=100,
                 lp_params=None):
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
    for key, val in (lp_params or {}).items():
        # escape hatch for the LP-stability sweep (W6b deliverable 4); an unknown or
        # out-of-range parameter must not take the whole method down
        try:
            with _quiet_c_stdout():
                m.setParam(key, val)
        except Exception:                                        # noqa: BLE001
            pass

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
_MAX_RUNGS = 8                      # hard cap on ladder attempts (incl. the extension rungs)
_MIN_RUNG = 1.0                     # do not start another rung for less than this many seconds
_MIP_START_SHARE = 0.05             # share of the budget the F1 warm start may spend
_MIP_START_CAP = 30.0               # ... and its absolute cap, in seconds


_SHORT_STOP_SHARE = 0.75            # a "timelimit" below this share of the rung's budget
                                    # is SCIP's clock talking, not ours


def _short_stop(scip_status, used: float, allotted: float) -> bool:
    """A SCIP `timelimit` that our own wall clock does not agree with.

    SCIP's `limits/time` runs on SCIP's clock, and under load (four to eleven harness
    workers) it has been seen to fire after 57 s of a 106 s budget -- measured 2026-08-30 on
    the 197-zip C7b pair, which then returned after 65 s of a 120 s cap with a rung still
    unspent.  The point of the ladder is that the budget gets used, so a stop this early is
    treated exactly like an abort: another rung, from the best allocation so far.  Genuine
    time limits (SCIP and our own clock agreeing) still end it.
    """
    if scip_status != "timelimit":
        return False
    return allotted > _MIN_RUNG and used < _SHORT_STOP_SHARE * allotted


def _f1_warm_start(G, nodes, *, theta, lam, rho, respect_state, seed, budget):
    """`warm.solve(method="f1")` as a MIP start.  Returns (allocation | None, source tag).

    W5's F1 (ReCom-style spanning-tree bisection + boundary local search) is a much better
    primal than this module's internal fallback -- the repaired ratio prefix / best subtree
    split -- and mechanism (b) is *primal* on the large pairs: SCIP's own heuristics are
    contiguity-blind, so nearly everything they produce fails `conscheck`, and a poor
    incumbent also loosens `_gain_floor`, which is what keeps the native log's LPs stable.
    Imported lazily: `warm` pulls in `bounds`, which imports `territory`, and `scip_tree`
    must stay importable for registry discovery without the repo's `code/` on the path.
    """
    if budget < _MIN_RUNG:
        return None, "skipped_no_budget"
    try:
        from . import warm as _warm
        res = _warm.solve(G, nodes, theta=theta, lam=lam, rho=rho,
                          respect_state=respect_state, time_limit=budget, seed=seed,
                          method="f1")
    except Exception as e:                                       # noqa: BLE001
        return None, f"failed:{type(e).__name__}"
    if res.to_a is None or res.LB is None or not math.isfinite(res.LB):
        return None, "empty"
    return set(res.to_a), "warm_f1"


_TIGHTEN_WINDOW = 1e-5              # a certified-but-uncertifiable gap this small is the
                                    # loosened rung's tolerance floor, nothing else


def _near_certified(merged) -> bool:
    """Is the merged answer inside `_TIGHTEN_WINDOW` of a certificate?

    A rung at feastol f stores a solution that satisfies `za <= log(ga)` to about f, so its
    recomputed certificate gap bottoms out near `2f` -- above `base.CERT_TOL` for every rung
    but the first.  On the 124- and 135-zip C7b pairs that is exactly where the 1200 s re-run
    landed: SCIP status `optimal`, recomputed gap 1.1e-7 and 3.0e-8, with ~1000 s unspent.

    A gap this small is a *tolerance* result, not a search result, so it puts the ladder into
    a terminal mode: try the rungs at the tolerance originally asked for (native, then OA,
    warm-started at the allocation just proved -- which also tightens `_gain_floor`), and if
    neither survives, stop.  Continuing the ordinary ladder from here is measurably wasted
    budget: on the 124-zip pair it spent 1027 s in an OA rung whose dual bound came back at
    6.4592 against the 6.45885 already in hand.
    """
    return (merged.LB is not None and merged.UB is not None
            and base.CERT_TOL < merged.UB - merged.LB <= _TIGHTEN_WINDOW)


def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          formulation="native", repair=True, feastol=1e-9, check_opt=None,
          verbose=False, ls_moves=_MAX_LS_MOVES, refactor_interval=100,
          fallback_warm_start=True, mip_start="f1", max_rungs=_MAX_RUNGS,
          tighten_back=True,
          sepa_frac=True, max_sepa_rounds=30, max_sepa_depth=0,
          sepa_thresholds=(0.5,), max_sepa_cuts=40, lp_params=None,
          **opts) -> base.Result:
    """One branch-and-cut solve, retried down a ladder after a numerical abort.

    SCIP can stop with "unresolved numerical troubles in LP -- aborting" -- an engine
    failure, not a model one, and the tighter the feasibility tolerance the likelier it is.
    The ladder answers it: 1e-7, then 1e-6, then the tangent (OA) build, which has no
    nonlinear relaxation to destabilise; each rung re-solves the same problem from the best
    allocation proved so far and gets **all** the remaining budget.  Every attempt bounds
    the same optimum, so the merged answer keeps the smallest UB and the largest LB, and a
    rung that adds nothing is discarded (`_merge`).

    Continuation is decided by `extra["retryable"]` (`_retryable`), never by the status: the
    status the harness sees is deliberately `time_limit` for an abort that still holds valid
    bounds, and reading *that* is what silently disabled the whole ladder in S2.

    If the ladder runs out while budget remains and the last rung was still aborting, extra
    OA rungs are appended (up to `max_rungs`) with a shifted random seed, so the budget is
    actually spent rather than returned unused.

    The mirror case is `tighten_back`: a merged gap just above `base.CERT_TOL` is a
    *tolerance* result, not a search result, so it ends the ordinary ladder and tries only
    the rungs at the tolerance originally asked for -- native, then OA -- before stopping.
    (`_near_certified`.)
    """
    t0 = time.perf_counter()
    deadline0 = t0 + float(time_limit)

    # ------------------------------------------------------------- F1 MIP start (W6b)
    mip_start_src = "given" if warm_start is not None else "off"
    ws = warm_start
    if warm_start is None and mip_start == "f1":
        budget = min(_MIP_START_SHARE * float(time_limit), _MIP_START_CAP)
        budget = min(budget, max(deadline0 - time.perf_counter() - _MIN_RUNG, 0.0))
        cand, mip_start_src = _f1_warm_start(G, nodes, theta=theta, lam=lam, rho=rho,
                                             respect_state=respect_state, seed=seed,
                                             budget=budget)
        if cand is not None:
            ws = cand
            # W6d: take the F1 start through a short kick-and-descend loop.  The diagnostic
            # measured +1e-3 nats over the F1 plateau in ~1 s on three of the five large
            # pairs; a start this much better also tightens `_gain_floor` from t = 0.
            ils_budget = min(_ILS_START_TIME,
                             max(deadline0 - time.perf_counter() - _MIN_RUNG, 0.0))
            if ils_budget >= 0.5 and len(list(nodes)) >= _ILS_MIN_N:
                try:
                    nlist = list(nodes)
                    ua0, ub0 = base.utilities(G, nlist, theta, lam, kappa)
                    ctx0 = _Ctx(G, nlist, ua0, ub0, rho)
                    if ctx0.is_feasible(ws) and math.isfinite(ctx0.objective(ws)):
                        better, obj_b = _ils_start(ctx0, ws, int(seed) + 17, ils_budget)
                        if better is not None and obj_b > ctx0.objective(ws) + 1e-12:
                            ws = better
                            mip_start_src = "warm_f1+ils"
                except Exception:                                # noqa: BLE001
                    pass                          # the plain F1 start is still a valid start

    rungs = [(float(feastol), formulation, 0)]
    rungs += [(f, formulation, 0) for f in _FEASTOL_LADDER if f > float(feastol) * 1.001]
    if formulation == "native":
        # Last resort: the same tree with tangents instead of SCIP's `log`.  A pure MILP has
        # no nonlinear relaxation to destabilise, so it survives where the native build
        # aborts at every tolerance (the 464-zip C7b A0/B0 pair does exactly that, at every
        # feastol in the ladder and every `lp/refactorinterval` from 10 to 100).  The bound
        # merge means this rung can only help: it either tightens something or is discarded.
        rungs.append((_FEASTOL_LADDER[-1], "oa", 0))

    merged = None
    attempts = []
    tried = set()                             # (feastol, formulation) rungs already run
    k = 0
    while k < len(rungs) and len(attempts) < int(max_rungs):
        ft, form, seed_shift = rungs[k]
        k += 1
        remaining = deadline0 - time.perf_counter()
        if remaining <= (_MIN_RUNG if merged is not None else 0.05):
            break
        t_rung = time.perf_counter()
        res = _solve_once(G, nodes, theta=theta, lam=lam, rho=rho,
                          time_limit=max(remaining, 0.05),
                          seed=int(seed) + seed_shift, warm_start=ws, trace=trace,
                          kappa=kappa, formulation=form, repair=repair, feastol=ft,
                          check_opt=check_opt, verbose=verbose, ls_moves=ls_moves,
                          refactor_interval=refactor_interval,
                          fallback_warm_start=fallback_warm_start,
                          sepa_frac=sepa_frac, max_sepa_rounds=max_sepa_rounds,
                          max_sepa_depth=max_sepa_depth, sepa_thresholds=sepa_thresholds,
                          max_sepa_cuts=max_sepa_cuts, lp_params=lp_params)
        used = time.perf_counter() - t_rung
        retryable = bool(res.extra.get("retryable"))
        short = _short_stop(res.extra.get("scip_status"), used, remaining)
        retryable = retryable or short
        attempts.append(dict(feastol=ft, formulation=form, seed_shift=seed_shift,
                             status=res.status, scip_status=res.extra.get("scip_status"),
                             retryable=retryable, short_stop=short, t=round(used, 3),
                             asked=round(remaining, 3), LB=res.LB, UB=res.UB,
                             nodes=res.nodes,
                             n_sepa_cuts=res.extra.get("n_sepa_cuts", 0)))
        merged = _merge(merged, res)
        tried.add((ft, form))
        if res.to_a is not None and res.LB is not None:
            ws = res.to_a                     # restart from the best allocation we did prove
        if merged.status == "optimal":
            break
        if tighten_back and _near_certified(merged):
            nxt = next((c for c in ((float(feastol), formulation), (float(feastol), "oa"))
                        if c not in tried), None)
            if nxt is None or (deadline0 - time.perf_counter()) <= _MIN_RUNG:
                break                         # nothing tighter left to try: this is the answer
            attempts[-1]["tighten_back"] = True
            rungs.insert(k, (nxt[0], nxt[1], seed_shift))
            continue
        if not retryable:
            break
        if k >= len(rungs) and (deadline0 - time.perf_counter()) > _MIN_RUNG:
            # the ladder is exhausted but the engine is still aborting and the budget is not
            # spent: keep going on the most robust rung with a shifted seed
            rungs.append((_FEASTOL_LADDER[-1], "oa" if formulation == "native" else formulation,
                          seed_shift + 1))
    if merged is None:                        # ladder never ran (no budget at all)
        return base.Result(status="time_limit", message="scip_tree: no time budget")
    merged.extra["attempts"] = attempts
    merged.extra["formulation"] = formulation
    merged.extra["mip_start"] = mip_start_src
    merged.extra["n_rungs"] = len(attempts)
    return merged


def _merge(a: "base.Result", b: "base.Result") -> "base.Result":
    """Keep the better allocation and the tightest valid bound across two attempts."""
    if a is None:
        return b
    ubs = [u for u in (a.UB, b.UB) if u is not None and math.isfinite(u)]
    keep = a if (a.LB is not None and (b.LB is None or a.LB >= b.LB)) else b
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
                ls_moves=_MAX_LS_MOVES, refactor_interval=100,
                fallback_warm_start=True, sepa_frac=True, max_sepa_rounds=30,
                max_sepa_depth=0, sepa_thresholds=(0.5,), max_sepa_cuts=40,
                lp_params=None) -> base.Result:
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
              n_polish=0, polish_spent=0.0, in_polish=False,
              lin_a=None, lin_b=None, gvals=(0.0, 0.0), feastol=float(feastol),
              sepa_frac=bool(sepa_frac), sepa_rounds=0, n_sepa_cuts=0,
              max_sepa_rounds=int(max_sepa_rounds), max_sepa_depth=int(max_sepa_depth),
              sepa_thresholds=tuple(float(t) for t in sepa_thresholds),
              max_sepa_cuts=int(max_sepa_cuts))

    # ------------------------------------------------------------------ warm start
    # Computed *before* the model: its objective is a valid floor on both gains, which is
    # what keeps the log's gradient tame (see `_gain_floor`).
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
    if ws is None and fallback_warm_start:
        ws, warm_source = _fallback_warm_start(ctx, deadline=deadline)
    if ws is not None:
        _record(ctx, st, ws)
        # W6d: descend the start to convergence before `_gain_floor` reads `best_obj` -- a
        # better start is a tighter floor, and the floor is what keeps the log's LPs stable.
        polished = _polish(ctx, st, ws)
        if polished is not None and _record(ctx, st, polished):
            ws = polished

    m, V = _build_model(ctx, rho=rho, time_limit=max(deadline - time.perf_counter(), 0.01),
                        seed=seed, formulation=formulation, feastol=feastol, verbose=verbose,
                        gain_floor=_gain_floor(ctx, st["best_obj"]),
                        refactor_interval=refactor_interval, lp_params=lp_params)
    st["V"] = V
    st["lin_a"], st["lin_b"] = V["lin_a"], V["lin_b"]

    hdlr = (_OAContig if formulation == "oa" else _Contig)(ctx, V["x"], st)
    # `sepafreq = 1` turns on `conssepalp` (W6b deliverable 3); the handler itself refuses to
    # run below `max_sepa_depth` or after `max_sepa_rounds`, so this is cheap when it is off.
    m.includeConshdlr(hdlr, "contig", "component-wise contiguity (lazy separator cuts)",
                      chckpriority=-10, enfopriority=-10, needscons=False,
                      sepapriority=0, sepafreq=(1 if st["sepa_frac"] else -1))
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


def _retryable(scip_status, st, *, aborted: bool) -> bool:
    """Did this attempt stop for a reason another rung of the ladder could survive?

    The ladder exists for exactly one failure: SCIP giving up on its own LPs ("unresolved
    numerical troubles in LP -- aborting"), which surfaces as a raised `Exception: SCIP:
    error in LP solver!` *and* `getStatus() == "unknown"`.  Everything else -- a genuine
    time limit, our own deadline interrupt, an optimality or gap certificate, infeasibility
    -- means either the budget really is gone or the answer really is in, and a retry would
    only repeat it.

    Found 2026-08-30 (W6b): `_finish` used to rewrite that abort to `time_limit` (so the
    harness counts crashes, not capped runs, in `errors`) *before* `solve` looked at it, and
    `solve` continued only `if res.status == "error"`.  So every large pair in S2 burned
    1-58 s of a 1200 s budget on the first rung and stopped: the 1e-7 / 1e-6 / OA rungs the
    docstring promises never ran once.  The verdict is now carried in `extra["retryable"]`,
    independent of the status the harness sees.
    """
    if aborted:
        return True
    if scip_status is None:
        return True
    if scip_status == "userinterrupt":
        # ours (deadline hit inside a callback) => the budget is gone; SCIP's own => retry
        return not st["interrupted"]
    return scip_status in ("unknown", "unbounded", "inforunbd")


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
                 repair_spent=round(st["repair_spent"], 4),
                 n_polish=st["n_polish"], polish_spent=round(st["polish_spent"], 4),
                 n_sepa_rounds=st["sepa_rounds"], n_sepa_cuts=st["n_sepa_cuts"],
                 retryable=_retryable(scip_status, st, aborted=forced_status == "error"))
    if status == "heuristic":
        UB = None
    if status == "error" and LB is not None and UB is not None:
        # main-session decision (W6 star-2): an exhausted retry ladder that still holds a
        # feasible incumbent and a valid dual bound is a capped run, not a crash --
        # `errors` in summary.csv should count crashes only.  The message keeps the cause.
        status = "time_limit"
        extra_note = "scip_tree: reported as time_limit (ladder exhausted with valid bounds)"
        message = (message + "; " if message else "") + extra_note
    return base.Result(status=status, to_a=to_a, LB=LB, UB=UB, ub_scope="global",
                       iters=st["n_enfolp"], n_cuts=len(st["cut_keys"]),
                       n_tangents=st["n_tangents"], nodes=nodes_used,
                       extra=extra, message=message)
