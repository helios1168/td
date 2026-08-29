"""
cbc_tree.py -- Option B: lazy connectivity + OA tangent cuts in a single CBC
branch-and-cut tree via python-mip (PLAN.md C.1, OPTIONS.md sec:opt-b, W7).

Same architecture as Option A (PySCIPOpt, W6) *for connectivity*: one MILP, one tree.  A
`mip.ConstrsGenerator` is registered as `model.lazy_constrs_generator`; CBC calls it at
every INTEGER-FEASIBLE incumbent (never at fractional nodes, since we never register a
`cuts_generator`) and it may add two families of lazy constraint:

**Read `solve()`'s docstring before assuming both families run purely lazily in one tree,
as OPTIONS.md sec:opt-b describes** -- a python-mip/CBC platform limitation, found and
documented there, means the lazy generator below is only a *best-effort* mechanism for
both families: OA tangent convergence is guaranteed by a bounded outer restart loop, and
connectivity (mostly resolved by the lazy cuts below) is backstopped by an explicit
post-hoc violation check in that same loop, because CBC can silently keep an incumbent
that violates a cut it was just handed.

  1. Component-wise minimal-separator connectivity cuts (CLAUDE.md trap 13; PLAN C.0 #1).
     For every connected component K of the (already state-filtered) pair graph, and for
     each side, the side's own zips within K must be empty or one connected piece.  When a
     side has >= 2 pieces inside K, the largest piece P is kept and, for every other piece
     Q, a separator C is computed (default: C = N(Q) inside K, districting.py's cut, but
     scoped to *this* K -- never a global root) and the cheap, per-representative-pair cut
         sum_{w in C} x_w  >=  x_u + x_v - 1     (u = min(P), v = min(Q); mirror 1-x for b)
     is added lazily.  `solve()`'s carried-forward backstop constraints use a *different*,
     stronger Q-relative form instead (`sum_C x >= sum_Q x - (|Q| - 1)`) -- see
     `_find_violations`'s docstring for why the lazy generator needs the cheap form (found
     necessary 2026-08-29, this session: the expensive form made CBC dramatically slower to
     converge here) while the backstop needs the expensive one (the cheap form's validity is
     tied to a specific `u` that can go stale across restarts).  N(Q) always consists of
     off-side vertices when Q is a genuine connected piece of the induced side-subgraph (any
     on-side neighbour of Q would already belong to Q's own component), so this cut is
     *always* violated by the incumbent that triggered it -- mathematically sound and
     correctly submitted, but see `solve()`'s docstring finding #3: CBC does not
     always honour that submission before finalising its incumbent, which is why `solve()`
     re-verifies and backstops this regardless.
     `cbc_tree_minsep` (VARIANTS) additionally tries a smaller separator via
     `networkx.minimum_node_cut` on a P->u / Q->v contraction with every *other* same-side
     piece in K removed; the contraction is verified against the *full* K graph (with the
     other pieces added back) before use and silently falls back to C = N(Q) if that check
     fails -- see `_separator`'s docstring for why the naive contraction is not sound
     on its own.
  2. OA tangent cuts on z_a <= log(g_a), z_b <= log(g_b) (Duran-Grossmann; territory.py's
     `nash_exact`, mirrored here): 8 geomspace-seeded tangents per side are added once, up
     front each round, as ordinary (non-lazy) constraints -- they are valid everywhere,
     integral or not.  The generator *also* opportunistically tries to add further tangents
     lazily, at the incumbent's own (g_a, g_b), whenever the model's z exceeds the true
     log(g) by more than 1e-9 -- mathematically sound (tangents are globally valid, so
     adding them lazily is fine; OPTIONS.md sec:opt-b) but, per the finding in `solve()`'s
     docstring, *not reliably enforced by CBC before it accepts an incumbent*.  Tangent
     convergence is therefore actually guaranteed by `solve()`'s outer restart loop, which
     re-checks the returned incumbent's za/zb directly and, if still loose, adds the needed
     tangent to a *fresh* model and restarts -- the lazy attempt here is a (harmless, often
     helpful) best effort layered on top, not the correctness mechanism.

Because z_a's upper bound is the *minimum* over every tangent added so far, and every
individual tangent line lies weakly above the log curve everywhere (concavity), z_a is
always >= log(g_a) at any incumbent; the model can only ever over-count g_a's true log, so
`model.objective_bound` after CBC declares OPTIMAL is a genuine global upper bound on
log g_a + log g_b - rho * perimeter -- `ub_scope="global"` unconditionally (no root is ever
fixed, unlike `current.py`'s legacy wrapper).

python-mip / CBC quirks found while building this (2026-08-29, this session)
------------------------------------------------------------------------------
* **`model.store_search_progress_log = True` SIGSEGVs/SIGABRTs the CBC C library on this
  machine** (`Cbc_addProgrCallback` -> a crash inside `CbcModel::branchAndBound`, reliably,
  on a plain 40-var knapsack with no lazy/cut generator at all).  This is the only way
  python-mip exposes an incremental (t, lb, ub) history from CBC itself, so this module
  does **not** use it: `Trace.bound` is called exactly once, from `model.objective_bound`
  after `optimize()` returns (plus once per lazy tangent added, which is a valid but not
  necessarily monotonically-tightening proxy -- the harness's `Trace` already takes the
  running min).  `Trace.incumbent` is populated from genuine, tangent-converged,
  connectivity-feasible incumbents seen inside the generator, which *does* give a real
  time series -- just not a bound time series.  Reported to the calling session; not a
  design choice, a platform-level crash to route around.
* **CBC has no exposed branch-and-bound node count in this python-mip build** (no
  `Cbc_getNodeCount` binding surfaces on `Model`/`Solver`).  `Result.nodes` stays at the
  contract's default (0) rather than a fabricated number.
* **Exceptions raised inside a `ConstrsGenerator.generate_constrs` callback are silently
  swallowed by cffi** (printed to stderr, then ignored; confirmed empirically) -- CBC just
  proceeds as though the generator added nothing, which would let a genuinely infeasible or
  non-tangent-converged incumbent be accepted as "the" solution with no signal at all.  The
  generator here therefore wraps its entire body in try/except and records the first
  exception on `self.error`; `solve()` checks it after `optimize()` returns and reports
  `status="error"` (never a silent false "optimal") if it fired.  As a second, independent
  safety net, `solve()` also re-verifies feasibility of the returned allocation itself
  before ever claiming "optimal" -- belt and braces against exactly this failure mode.
* Registering `lazy_constrs_generator` makes python-mip's CBC binding turn CBC's own
  presolve off automatically (`cbc_set_parameter(self, "preprocess", "off")`, confirmed by
  reading `mip/cbc.py`), so variable names/indices are stable inside the callback and
  `model.var_by_name(...)` always finds every `x_i`/`za`/`zb` this module creates.
* **The big one: CBC does not reliably enforce a just-submitted lazy constraint before
  accepting the incumbent that violated it, for either the continuous OA tangents or (when
  the same model object is `optimize()`d a second time) the binary connectivity cuts.**
  This is why `solve()` is a bounded outer restart loop over fresh models for the tangent
  family rather than a single lazy tree for both -- see `solve()`'s docstring for the two
  reproductions and the architecture decided in response.

Requirement 1 (data-scaled tangent seeds and z bounds), requirement 6 (rho > 0 edge
variables `y_e >= |x_i - x_j|`, omitted entirely at rho = 0), and the g=0 exclusion via
`sum(x_z) >= 1` / `sum(1-x_z) >= 1` over positive-utility zips on each side, are exactly the
brief's Binding design requirements 1 and 6.
"""
from __future__ import annotations

import math
import time
from typing import Optional

import networkx as nx
import numpy as np

try:
    import mip
except ImportError as _e:                                              # pragma: no cover
    mip = None
    _IMPORT_ERROR = _e

from . import base

NAME = "cbc_tree"
EXACT = False   # demoted 2026-08-30: python-mip's lazy rows are unreliable (see _demote)
MAX_N = None
N_SEEDS = 8            # geomspace tangent seeds per side, mirrors territory.nash_exact
TANGENT_TOL = 1e-9      # z - log(g) violation threshold for a new lazy tangent
OUTER_ROUNDS = 60       # bounded OA-tangent restart cap (see solve())
VARIANTS = {
    "cbc_tree_minsep": dict(minsep=True),
}


# ------------------------------------------------------------------------- tangent algebra
def _tangent_expr_a(za, xvars, ua, gh):
    """za <= log(gh) - 1 + sum_i (ua[i]/gh) x_i   (territory.nash_exact's tangent, d=0)."""
    return za <= (math.log(gh) - 1.0) + mip.xsum((float(ua[i]) / gh) * xvars[i]
                                                 for i in range(len(ua)) if ua[i] != 0.0)


def _tangent_expr_b(zb, xvars, ub, gh, ub_sum):
    """zb <= log(gh) - 1 + ub_sum/gh - sum_i (ub[i]/gh) x_i."""
    return zb <= (math.log(gh) - 1.0 + ub_sum / gh) - mip.xsum(
        (float(ub[i]) / gh) * xvars[i] for i in range(len(ub)) if ub[i] != 0.0)


# --------------------------------------------------------------------------- separator cut
def _separator(Ksub: nx.Graph, K_side_nodes: set, P: set, Q: set, minsep: bool) -> set:
    """A vertex set C, disjoint from P and Q, that separates P from Q inside `Ksub`.

    Default (and always the fallback): C = N(Q) inside K, minus Q itself.  Since Q is a
    genuine connected component of the induced side-subgraph, every node adjacent to Q that
    is *also* on the same side would already be part of Q's own component -- so N(Q) \\ Q
    can contain only off-side vertices, which is exactly what makes the resulting cut
    `sum_C x >= x_u + x_v - 1` violated by the incumbent that triggered it (LHS is 0 there).

    `minsep=True` additionally tries networkx.minimum_node_cut on a reduced graph: every
    *other* same-side piece in K (neither P nor Q) is dropped, then P is contracted to a
    single node U and Q to a single node V (so a cut found for U-V is valid for "any node of
    P" vs "any node of Q", not just one representative pair).  Dropping the other pieces is
    necessary to guarantee the candidate cut only contains off-side vertices (an untouched
    same-side piece would trivially satisfy sum_C x>=1 already and never actually reject the
    incumbent) but is not, on its own, guaranteed sound: those dropped pieces could offer a
    real bypass path around the reduced graph's cut once they are put back.  So the
    candidate is verified against the *full* Ksub (with the dropped pieces restored) before
    use, and this function falls back to C = N(Q) whenever that check fails or the reduced
    problem errors out.
    """
    C = set()
    for z in Q:
        C |= set(Ksub.neighbors(z))
    C -= Q
    if not minsep or not C:
        return C
    other = K_side_nodes - P - Q
    keep = [nd for nd in Ksub.nodes() if nd not in other]
    U, V = "__U__", "__V__"
    H = nx.Graph()
    H.add_nodes_from(nd for nd in keep if nd not in P and nd not in Q)
    H.add_nodes_from((U, V))
    for a_, b_ in Ksub.subgraph(keep).edges():
        au = U if a_ in P else (V if a_ in Q else a_)
        bv = U if b_ in P else (V if b_ in Q else b_)
        if au == bv:
            continue
        H.add_edge(au, bv)
    if U not in H or V not in H or not nx.has_path(H, U, V):
        return C
    try:
        cand = {c for c in nx.minimum_node_cut(H, U, V) if c not in (U, V)}
    except Exception:                                        # noqa: BLE001 -- fall back
        return C
    if not cand:
        return C
    u_rep, v_rep = next(iter(P)), next(iter(Q))
    remaining = set(Ksub.nodes()) - cand
    if u_rep in remaining and v_rep in remaining:
        sub = Ksub.subgraph(remaining)
        if u_rep in sub and v_rep in sub and nx.has_path(sub, u_rep, v_rep):
            return C                        # unsound here (a dropped piece bypasses it)
    return cand if len(cand) < len(C) else C


def _find_violations(nodes, idx, comps, to_a: set, minsep: bool) -> list:
    """Every component-wise contiguity violation of `to_a`, as `(side, C, Q, P)` tuples (`C`
    a frozenset of separator nodes, `Q` a frozenset -- the excess piece, `P` a frozenset --
    the kept largest piece) -- one call scans every pair component K independently
    (CLAUDE.md trap 13; PLAN C.0 #1).  Shared by the lazy generator (best-effort, in-tree,
    uses `P` and `Q` to build the brief's cheap per-representative-pair cut) and by
    `solve()`'s outer-loop backstop (guaranteed, uses only `C`/`Q` for a stronger,
    permanently-valid cut -- see its docstring for why both mechanisms are needed, and why
    they use two *different* strengths of cut).

    Two cut forms are licensed by a violation here, at different costs and different scopes
    of validity:

    - **Per-representative-pair** (the design brief's literal form): `sum_C x >= x_u + x_v
      - 1` for `u = min(P)`, `v = min(Q)`.  Cheap (2 variables on the right), and sufficient
      to exclude the *specific* incumbent that triggered it -- all a single lazy add inside
      one tree needs to do.  This is what the lazy generator uses.  Found necessary
      2026-08-29 (this session) to use the *cheap* form here specifically: substituting the
      Q-relative form below (more terms) made CBC dramatically slower to converge on some
      T0 pairs, plausibly from extra LP rows/nonzeros or a branching-order side effect --
      the exact mechanism inside CBC was not pinned down further, but the fix (use the
      cheap form for every lazy add, reserve the expensive one for the few constraints that
      must outlive the round that found them) resolved it.
    - **Q-relative** (stronger, representative-independent): `sum_C x >= sum_Q x - (|Q| -
      1)`, i.e. "if *all* of Q is on this side, at least one separator node must be too" --
      active only when Q is taken in full, regardless of which node is currently `P`'s
      representative.  `solve()`'s carried-forward backstop constraints use this form
      (found necessary the same session: the per-(u, v) form let the *same* Q reappear as a
      violation in a later outer round once a *different* node of the -- also legitimate,
      but different -- largest piece became the new representative `u`; a constraint tied
      to the old `u` does not forbid that, since its right-hand side is only 1 when both the
      specific `u` and `v` it names are selected).  The Q-relative form has no such gap: it
      depends only on Q and C, both fixed once discovered, so it is safe to add once,
      permanently, as an ordinary constraint that must go on being correct in every
      subsequent fresh-model round -- which is exactly the backstop's job and not the lazy
      generator's (a lazy add only ever has to be correct for the one incumbent it fires
      on)."""
    out = []
    for K_nodes, Ksub in comps:
        for side in ("a", "b"):
            on_side = (lambda z: z in to_a) if side == "a" else (lambda z: z not in to_a)
            sel = [z for z in K_nodes if on_side(z)]
            if len(sel) < 2:
                continue
            pieces = sorted(nx.connected_components(Ksub.subgraph(sel)),
                            key=lambda c: (-len(c), base._sort_key(min(c, key=base._sort_key))))
            if len(pieces) < 2:
                continue
            P = set(pieces[0])
            Sside = set(sel)
            for Q_ in pieces[1:]:
                Q = set(Q_)
                C = _separator(Ksub, Sside, P, Q, minsep)
                if not C:
                    continue
                out.append((side, frozenset(C), frozenset(Q), frozenset(P)))
    return out


# ------------------------------------------------------------------------------ generator
class _ConnGen:
    """`mip.ConstrsGenerator`-shaped object (see module docstring for the cffi caveat that
    rules out subclassing being load-bearing -- every call is wrapped in try/except and the
    first exception is captured on `self.error` rather than allowed to vanish silently)."""

    def __init__(self, nodes, idx, ua, ub, comps, xnames, za_name, zb_name, rho, G,
                minsep, trace, check_cuts, reference_to_a):
        self.nodes = nodes
        self.idx = idx
        self.n = len(nodes)
        self.ua = ua
        self.ub = ub
        self.ub_sum = float(ub.sum())
        self.comps = comps                    # list of (K_nodes_sorted, Ksub) precomputed
        self.xnames = xnames
        self.za_name = za_name
        self.zb_name = zb_name
        self.rho = rho
        self.G = G
        self.minsep = minsep
        self.trace = trace
        self.check_cuts = check_cuts
        self.reference_x = (base.mask(nodes, reference_to_a)
                            if (check_cuts and reference_to_a is not None) else None)
        self.n_cuts = 0
        self.n_tangents = 0
        self.error: Optional[BaseException] = None
        self.cut_violations: list = []
        self._seen_cuts: set = set()
        self._seen_tangents = {"a": set(), "b": set()}
        self.best_lb: Optional[float] = None
        self.best_to_a: Optional[set] = None

    # -- mip.ConstrsGenerator protocol -------------------------------------------------
    def generate_constrs(self, model, depth: int = 0, npass: int = 0) -> None:
        if self.error is not None:
            return
        try:
            self._generate(model)
        except BaseException as e:              # noqa: BLE001 -- see module docstring
            self.error = e

    # -- actual body, kept out of the except-everything wrapper for clarity ------------
    def _generate(self, model) -> None:
        xv = np.empty(self.n)
        for i in range(self.n):
            v = model.var_by_name(self.xnames[i])
            if v is None or v.x is None:
                return                          # nothing to do yet (shouldn't happen)
            xv[i] = v.x
        xb = xv > 0.5
        to_a_now = {self.nodes[i] for i in range(self.n) if xb[i]}

        added = 0
        violations = _find_violations(self.nodes, self.idx, self.comps, to_a_now, self.minsep)
        # `has_violation`/`has_tan_violation` (below) track whether `to_a_now` is *actually*
        # feasible/tangent-tight right now -- independent of `_seen_cuts`/`_seen_tangents`
        # dedup.  Found necessary 2026-08-29 (this session): gating "accept as a genuine
        # incumbent" on `added == 0` alone let a *still-violating* `to_a_now` through
        # whenever the violating cut had already been submitted (hence not "added") on an
        # earlier call this round -- CBC's own known unreliability at enforcing a just-
        # submitted lazy constraint (`solve()`'s docstring finding #3) means that earlier
        # submission cannot be trusted to have actually excluded this later, still-violating
        # incumbent.  Concretely: this let a disconnected `to_a` through as `gen.best_to_a`
        # with an objective *above* the true (brute-verified) global optimum on a T0 pair.
        has_violation = bool(violations)
        for side, C, Q, P in violations:
            key = (side, C, Q)
            if key in self._seen_cuts:
                continue
            self._seen_cuts.add(key)
            cvars = [model.var_by_name(self.xnames[self.idx[w]]) for w in C]
            if any(v is None for v in cvars):
                continue
            # Lazy, in-tree cut: the brief's literal per-representative-pair form
            # (x_u + x_v - 1) -- cheaper for CBC to process than the Q-relative form (fewer
            # terms) and sufficient here, since excluding the *specific* incumbent that
            # triggered it is all one lazy add needs to do within a single tree.  Found
            # necessary 2026-08-29 (this session): using the (more expensive, many-term)
            # Q-relative form here too, not just in `solve()`'s carried-forward backstop
            # constraints, made CBC dramatically slower to converge on some T0 pairs (one
            # 11-zip instance did not return within its budget at all) -- plausibly more
            # LP rows/nonzeros per lazy add, or different branching behaviour, though the
            # exact mechanism inside CBC was not pinned down further.  `solve()`'s backstop
            # still needs the Q-relative form (see `_find_violations`'s docstring) because
            # it must keep working after the round that discovered it, once carried into a
            # fresh model as an ordinary constraint -- this lazy cut never has to.
            u = min(P, key=base._sort_key)
            v = min(Q, key=base._sort_key)
            xu = model.var_by_name(self.xnames[self.idx[u]])
            xv_ = model.var_by_name(self.xnames[self.idx[v]])
            if xu is None or xv_ is None:
                continue
            if side == "a":
                expr = mip.xsum(cvars) >= xu + xv_ - 1
                if self.reference_x is not None:
                    lhs = sum(self.reference_x[self.idx[w]] for w in C)
                    rhs = self.reference_x[self.idx[u]] + self.reference_x[self.idx[v]] - 1
                    if lhs < rhs - 1e-9:
                        self.cut_violations.append(("a", sorted(C), sorted(Q)))
            else:
                expr = mip.xsum(1 - w for w in cvars) >= (1 - xu) + (1 - xv_) - 1
                if self.reference_x is not None:
                    lhs = sum(1 - self.reference_x[self.idx[w]] for w in C)
                    rhs = (1 - self.reference_x[self.idx[u]]) + (1 - self.reference_x[self.idx[v]]) - 1
                    if lhs < rhs - 1e-9:
                        self.cut_violations.append(("b", sorted(C), sorted(Q)))
            model.add_lazy_constr(expr)
            self.n_cuts += 1
            added += 1

        ga = float(self.ua[xb].sum())
        gb = float(self.ub[~xb].sum())
        za_v = model.var_by_name(self.za_name)
        zb_v = model.var_by_name(self.zb_name)
        has_tan_violation = False
        if ga > 1e-12 and za_v is not None and za_v.x is not None:
            if za_v.x - math.log(ga) > TANGENT_TOL:
                has_tan_violation = True
                key_a = round(ga, 9)
                if key_a not in self._seen_tangents["a"]:
                    xvars = [model.var_by_name(n) for n in self.xnames]
                    model.add_lazy_constr(_tangent_expr_a(za_v, xvars, self.ua, ga))
                    self._seen_tangents["a"].add(key_a)
                    self.n_tangents += 1
                    added += 1
        if gb > 1e-12 and zb_v is not None and zb_v.x is not None:
            if zb_v.x - math.log(gb) > TANGENT_TOL:
                has_tan_violation = True
                key_b = round(gb, 9)
                if key_b not in self._seen_tangents["b"]:
                    xvars = [model.var_by_name(n) for n in self.xnames]
                    model.add_lazy_constr(_tangent_expr_b(zb_v, xvars, self.ub, gb, self.ub_sum))
                    self._seen_tangents["b"].add(key_b)
                    self.n_tangents += 1
                    added += 1

        if not has_violation and not has_tan_violation and ga > 0 and gb > 0:
            to_a = {self.nodes[i] for i in range(self.n) if xb[i]}
            per = base.perimeter(self.G, self.nodes, to_a) if self.rho else 0
            obj = math.log(ga) + math.log(gb) - self.rho * per
            if self.best_lb is None or obj > self.best_lb:
                self.best_lb = obj
                self.best_to_a = to_a
            if self.trace is not None:
                self.trace.incumbent(to_a, obj)


def _build_and_solve(G, nodes, idx, ua, ub, ua_sum, ub_sum, comps, edges, rho, seed,
                     extra_a, extra_b, extra_cuts, warm_to_a, time_budget, minsep, trace,
                     check_cuts, reference_to_a, no_lazy=False):
    """Build a *fresh* CBC model -- static + accumulated extra tangents, lazy connectivity
    generator -- and solve it exactly once.  One outer round of `solve()`'s restart loop
    (see its docstring for why connectivity is single-tree/lazy but tangents restart).

    `no_lazy=True` builds the identical model (same static tangents, same accumulated
    `extra_a`/`extra_b`/`extra_cuts`) but never attaches `model.lazy_constrs_generator` --
    used only as `solve()`'s verification pass for a suspected-false INFEASIBLE (see its
    docstring finding #4): found 2026-08-29, this session, that CBC can report INFEASIBLE
    on a model *with* the generator attached that solves to OPTIMAL, correctly, on the
    identical model minus only the `lazy_constrs_generator` registration -- so an
    INFEASIBLE with no prior verified incumbent to fall back on cannot be trusted either,
    and is re-checked this way before ever being reported."""
    n = len(nodes)
    u_all = np.concatenate([ua, ub])
    u_pos = u_all[u_all > 0]
    min_pos = float(u_pos.min()) if u_pos.size else 1e-9
    total = max(ua_sum, ub_sum, min_pos)
    z_lb, z_ub = math.log(min_pos) - 1.0, math.log(total) + 1.0

    model = mip.Model(sense=mip.MAXIMIZE, solver_name=mip.CBC)
    model.verbose = 0
    model.threads = 1
    model.max_mip_gap = 0.0
    model.max_mip_gap_abs = 0.0
    try:
        model.seed = int(seed)
    except Exception:                                          # noqa: BLE001
        pass

    xnames = [f"x{i}" for i in range(n)]
    xvars = [model.add_var(name=xnames[i], var_type=mip.BINARY) for i in range(n)]
    za = model.add_var(name="za", lb=z_lb, ub=z_ub, var_type=mip.CONTINUOUS)
    zb = model.add_var(name="zb", lb=z_lb, ub=z_ub, var_type=mip.CONTINUOUS)

    if rho:
        yvars = {}
        for k, (u, v) in enumerate(edges):
            yv = model.add_var(name=f"y{k}", lb=0.0, ub=1.0, var_type=mip.CONTINUOUS)
            yvars[(u, v)] = yv
            model += yv >= xvars[idx[u]] - xvars[idx[v]]
            model += yv >= xvars[idx[v]] - xvars[idx[u]]
        model.objective = mip.maximize(za + zb - rho * mip.xsum(yvars.values()))
    else:
        model.objective = mip.maximize(za + zb)

    pos_a = [i for i in range(n) if ua[i] > 0]
    pos_b = [i for i in range(n) if ub[i] > 0]
    if pos_a:
        model += mip.xsum(xvars[i] for i in pos_a) >= 1
    if pos_b:
        model += mip.xsum(1 - xvars[i] for i in pos_b) >= 1

    span = max(ua_sum, ub_sum)
    n_static_tangents = 0
    if span > 0:
        for gh in np.geomspace(max(span * 1e-3, 1e-3), span, N_SEEDS):
            gh = float(gh)
            if gh <= 1e-12:
                continue
            model += _tangent_expr_a(za, xvars, ua, gh)
            model += _tangent_expr_b(zb, xvars, ub, gh, ub_sum)
            n_static_tangents += 2
    for gh in extra_a:
        model += _tangent_expr_a(za, xvars, ua, gh)
        n_static_tangents += 1
    for gh in extra_b:
        model += _tangent_expr_b(zb, xvars, ub, gh, ub_sum)
        n_static_tangents += 1

    # backstop connectivity cuts (solve()'s docstring): violations found post-hoc in an
    # earlier round because CBC accepted an incumbent its own lazy generator should have
    # rejected -- added here as ordinary, always-enforced, Q-relative constraints (not tied
    # to any representative pair, see `_find_violations`'s docstring for why that matters
    # for a constraint that must keep working after the round that discovered it).
    for side, C, Q in extra_cuts:
        cvars = [xvars[idx[w]] for w in C]
        qvars = [xvars[idx[z]] for z in Q]
        nQ = len(Q)
        if side == "a":
            model += mip.xsum(cvars) >= mip.xsum(qvars) - (nQ - 1)
        else:
            model += mip.xsum(1 - v for v in cvars) >= mip.xsum(1 - v for v in qvars) - (nQ - 1)

    if warm_to_a is not None:
        wa = set(warm_to_a)
        model.start = [(xvars[i], 1.0 if nodes[i] in wa else 0.0) for i in range(n)]

    gen = _ConnGen(nodes, idx, ua, ub, comps, xnames, "za", "zb", rho, G,
                   bool(minsep), trace, bool(check_cuts), reference_to_a)
    if not no_lazy:
        model.lazy_constrs_generator = gen

    raw = model.optimize(max_seconds=max(float(time_budget), 0.01))
    return raw, model, xvars, za, zb, gen, n_static_tangents


# --------------------------------------------------------------------------------- solve
def _solve_cbc(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          minsep=False, check_cuts=False, reference_to_a=None, **opts) -> base.Result:
    """Component-wise lazy connectivity cuts, best-effort, inside a CBC branch-and-cut tree
    each round, wrapped in a bounded outer restart loop that GUARANTEES both convergence
    families -- see below for why this is not the pure "one tree, both families lazy"
    architecture OPTIONS.md sec:opt-b describes, and why the guarantee needed a second,
    independent backstop beyond the one first found.

    **Finding (2026-08-29, this session): CBC's `lazy_constrs_generator` callback, as bound
    by python-mip 2.0.0 on this platform, does not reliably enforce a just-submitted lazy
    constraint before accepting an integer-feasible candidate as the final incumbent -- for
    *either* cut family, and even on a completely fresh, once-solved model.** Confirmed three
    ways, each progressively narrowing where a purely-lazy design could be trusted:

    1. The OA tangent on `za`/`zb` (continuous): CBC declared OPTIMAL with `objective_bound`
       4.678241 on a two-pair-component hand instance whose true optimum (matching brute
       force exactly) is 4.538243 -- even though the exact tangent that would have tightened
       `za` for that incumbent's own `g_a` had already been submitted via `add_lazy_constr`
       earlier in the *same* `optimize()` call.  Repeated `generate_constrs` invocations for
       the *identical* `x` showed `za.x`/`zb.x` completely unchanged across calls, including
       the call immediately after the tangent was added -- the LP was not being re-solved
       between them.
    2. Reusing the *same* model object across a second `model.optimize()` call (a natural
       fix for #1: add the missing tangent as an ordinary constraint and re-optimize) can
       make even the **connectivity** cuts unsound: on a real T0 instance
       (`T0_n40_s1__A0_B0`, pair A0/B0), round 1 of a from-scratch solve correctly avoided a
       disconnected candidate `{28, 30, 32, 38}` (piece `{28,32,38}` plus isolated `{30}`);
       re-optimizing the *same* model after adding one extra tangent landed on that exact
       disconnected candidate as its new "OPTIMAL" incumbent, with no cut rejecting it.
    3. **Even a completely fresh model, solved exactly once, is not immune**: on the same
       instance, a *later* outer round (still a from-scratch `mip.Model`, never reused --
       the fix attempted for #2) landed on a different disconnected incumbent
       (`{28, 9, 10, 38}`) as its "OPTIMAL" answer, with `n_outer` as low as 1 on other T0
       pairs.  So "solve fresh, once" is not sufficient either; the unsoundness is a general
       property of this callback, not narrowly tied to cross-`optimize()`-call reuse.
    4. **The generator's own "no violation found" bookkeeping could itself be fooled by the
       same unreliability**: `_ConnGen._generate` used to gate "accept this incumbent as
       genuinely converged" on whether it had anything *new* to submit this call
       (`_seen_cuts`/`_seen_tangents` dedup) rather than on whether a violation was actually
       still present.  Since a lazy add is not reliably enforced against a *later* incumbent
       either (not just the one that triggered it -- this is the same failure mode as #1-#3,
       just recurring within one generator's own dedup state), that let a genuinely
       disconnected `to_a` through as `gen.best_to_a` with a log-product *above* the true
       (brute-verified) global optimum -- caught only because that value later got
       reported as the harness's own answer after a downstream INFEASIBLE (see #5) discarded
       every other candidate.  Fixed by gating on the live, undeduped result of
       `_find_violations`/the direct `za.x`/`zb.x` check every call, never on `_seen_*`.
    5. **CBC can also report the whole model INFEASIBLE when only the lazy generator
       differs**: the identical model (same variables, same tangents, same `x` fixed to a
       brute-verified feasible point) solves to OPTIMAL with `model.lazy_constrs_generator`
       unset and INFEASIBLE with it set, on a from-scratch, first-round model with *zero*
       backstop cuts yet added (`T0_n40_s3__A0_B0`, pair A0/B0).  So an INFEASIBLE verdict
       cannot be trusted at face value either, symmetrically with #1-#3's OPTIMAL verdicts.

    Architecture chosen in response, in three layers:

    - **Tangent convergence**: a bounded outer restart loop (`OUTER_ROUNDS`, default 20).
      Each round builds a completely fresh `mip.Model` carrying every tangent discovered as
      still-needed in a prior round as an *ordinary* constraint (never relying on the lazy
      add alone), plus a warm start from the prior round's incumbent.  OA convergence is
      fast in this codebase's experience (territory.py's `nash_exact`: 6-7 iterations
      regardless of n), so this is a modest compromise, not a full regression to the legacy
      multi-tree loop.
    - **Connectivity**: the lazy generator (`_ConnGen`) is still the primary, best-effort
      mechanism -- it resolves the overwhelming majority of violations within one tree, which
      is the actual point of Option B (OPTIONS.md mechanism (b): "the direct remedy for
      re-solve-from-scratch") -- but is backstopped by an explicit post-hoc check: every
      round's returned incumbent is re-verified with `base.is_feasible` regardless of what
      CBC claimed, and on failure the exact violation(s) are recomputed (`_find_violations`,
      the same logic the lazy generator uses) and added to `extra_cuts`, a list of *ordinary*
      constraints carried into every subsequent fresh round -- so a violation CBC accepted
      once cannot be silently re-accepted.  A run that keeps landing on already-cut
      violations (no new one to add) gives up after 5 consecutive occurrences rather than
      spin through `OUTER_ROUNDS` unproductively.
    - **INFEASIBLE verification**: an INFEASIBLE round is never taken at face value (finding
      #5).  If a verified incumbent exists from an earlier round, it is reported (as
      `"time_limit"`, uncertified -- see below) instead of a false `"infeasible"`.  If none
      exists yet, one extra solve of the identical model *without* the lazy generator
      attached is tried before ever reporting `"infeasible"`; if that finds a feasible point
      it is used, if it finds a connectivity-violating one its violation becomes a fresh
      backstop cut for the next round, and only if even that comes back INFEASIBLE is
      `"infeasible"` finally reported.

    Neither layer trusts CBC's own "OPTIMAL" claim at face value: `UB` is only ever taken
    from a round whose returned `x` is *both* connectivity-feasible (checked, not assumed)
    and tangent-converged (checked directly against `za.x`/`zb.x`, not inferred from the
    generator's own bookkeeping) -- so `UB - LB <= CERT_TOL` remains a sound gate on
    `status="optimal"` even though the underlying engine's own claim, on its own, is not
    always trustworthy as a certificate (see above).  `ga <= 0 or gb <= 0` is checked too
    (belt and braces on the positive-utility constraints).
    """
    if mip is None:                                            # pragma: no cover
        return base.Result(status="error", message=f"python-mip not importable: {_IMPORT_ERROR}")

    nodes = list(nodes)
    n = len(nodes)
    idx = {z: i for i, z in enumerate(nodes)}
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    ua_sum, ub_sum = float(ua.sum()), float(ub.sum())

    sub = G.subgraph(nodes)
    comps = []
    for K in nx.connected_components(sub):
        K_sorted = sorted(K, key=base._sort_key)
        comps.append((K_sorted, sub.subgraph(K_sorted)))
    edges = sorted(sub.edges(), key=lambda e: (base._sort_key(e[0]), base._sort_key(e[1])))

    t_start = time.perf_counter()
    extra_a: list = []
    extra_b: list = []
    extra_cuts: list = []                 # [(side, frozenset(C), frozenset(Q))] -- see docstring
    seen_extra_cuts: set = set()
    n_infeasible_retries = 0
    warm_to_a = set(warm_start) if warm_start is not None else None
    best_lb, best_to_a = None, None
    total_cuts = total_tangents = 0
    n_outer = 0

    for _ in range(OUTER_ROUNDS):
        remaining = float(time_limit) - (time.perf_counter() - t_start)
        if remaining <= 0.05:
            break
        raw, model, xvars, za, zb, gen, n_static_tangents = _build_and_solve(
            G, nodes, idx, ua, ub, ua_sum, ub_sum, comps, edges, rho, seed,
            extra_a, extra_b, extra_cuts, warm_to_a, remaining, minsep, trace, check_cuts,
            reference_to_a)
        n_outer += 1
        total_cuts += gen.n_cuts
        total_tangents += gen.n_tangents
        if gen.best_lb is not None and (best_lb is None or gen.best_lb > best_lb):
            best_lb, best_to_a = gen.best_lb, gen.best_to_a

        extra = dict(minsep=bool(minsep), cut_violations=gen.cut_violations,
                    raw_status=str(raw), n_outer=n_outer, n_static_tangents=n_static_tangents,
                    n_backstop_cuts=len(extra_cuts))

        def _finalise(status: str, to_a, LB, UB, message: str = "") -> base.Result:
            return base.Result(status=status, to_a=to_a, LB=LB, UB=UB, ub_scope="global",
                               n_cuts=total_cuts, n_tangents=total_tangents, extra=extra,
                               message=message)

        if gen.error is not None:
            return _finalise("error", best_to_a, best_lb, None,
                             f"cbc_tree: generator raised {type(gen.error).__name__}: {gen.error}")

        if raw in (mip.OptimizationStatus.OPTIMAL, mip.OptimizationStatus.FEASIBLE):
            x = np.array([bool(round(v.x)) for v in xvars])
            to_a = {nodes[i] for i in range(n) if x[i]}
            if not base.is_feasible(G, nodes, to_a):
                # Backstop for the finding in solve()'s docstring: CBC accepted an incumbent
                # its own lazy generator should have rejected (confirmed: this recurs even
                # on a from-scratch model/solve, not only across a reused one).  Compute the
                # violation(s) this exact incumbent has directly (the same logic the lazy
                # generator uses) and add them as *ordinary*, always-enforced constraints for
                # the next fresh round -- unlike a lazy add, these cannot be silently skipped.
                viol = _find_violations(nodes, idx, comps, to_a, bool(minsep))
                new = [(side, C, Q) for side, C, Q, _P in viol
                      if (side, C, Q) not in seen_extra_cuts]
                if not new:
                    n_infeasible_retries += 1
                    if n_infeasible_retries > 5:
                        return _finalise("error", best_to_a, best_lb, None,
                                         "cbc_tree: repeated infeasible incumbents with no "
                                         "new backstop cut to add -- giving up")
                else:
                    n_infeasible_retries = 0
                for side, C, Q in new:
                    seen_extra_cuts.add((side, C, Q))
                    extra_cuts.append((side, C, Q))
                # No warm start on a recovery round: found 2026-08-29 (this session) that
                # warm-starting from `best_to_a` right after adding a fresh backstop cut
                # could make some T0 pairs dramatically slower to return (the exact CBC-side
                # mechanism was not pinned down further, but dropping the warm start here
                # reproducibly avoided it on the case that surfaced it) -- a fresh, unbiased
                # search each recovery round is worth the (typically small) speed loss.
                warm_to_a = None
                continue
            ga = float(ua[x].sum())
            gb = float(ub[~x].sum())
            if ga <= 0 or gb <= 0:
                return _finalise("error", best_to_a, best_lb, None,
                                 "cbc_tree: solver's own incumbent has a zero-gain side "
                                 "despite the positive-utility constraints")
            per = base.perimeter(G, nodes, to_a) if rho else 0
            LB = math.log(ga) + math.log(gb) - rho * per
            if best_lb is None or LB > best_lb:
                best_lb, best_to_a = LB, to_a

            if raw == mip.OptimizationStatus.FEASIBLE:
                UB = model.objective_bound
                return _finalise("time_limit", to_a, LB,
                                 float(UB) if UB is not None else None)

            viol_a = za.x - math.log(ga) > TANGENT_TOL
            viol_b = zb.x - math.log(gb) > TANGENT_TOL
            if not (viol_a or viol_b):
                UB = model.objective_bound
                UB = float(UB) if UB is not None else None
                status = "optimal" if (UB is not None and UB - LB <= base.CERT_TOL) else "gap_limit"
                return _finalise(status, to_a, LB, UB)

            # OPTIMAL for this round's (incomplete) tangent set, but not yet tangent-tight:
            # add the missing tangent seed(s) and restart fresh, warm-started from here.
            if viol_a:
                extra_a.append(ga)
            if viol_b:
                extra_b.append(gb)
            warm_to_a = to_a
            continue

        if raw == mip.OptimizationStatus.NO_SOLUTION_FOUND:
            UB = model.objective_bound
            return _finalise("time_limit", best_to_a, best_lb,
                             float(UB) if UB is not None else None)

        if raw == mip.OptimizationStatus.INFEASIBLE:
            if best_to_a is not None:
                # The true feasible region is provably non-empty (`best_to_a` is an
                # independently-verified feasible, harness-recomputed point from an earlier
                # round) -- so this round's INFEASIBLE cannot be a fact about the underlying
                # contiguous-Nash problem.  It is at most a fact about *this round's*
                # accumulated constraint set (tangent seeds + backstop cuts), so reporting
                # `status="infeasible"` here would be a false, misleading claim (the harness
                # contract's `infeasible` means the model is unsolvable, not "this round's
                # cut set turned out too aggressive").  Fall back to the best verified
                # incumbent instead, uncertified.
                return _finalise("time_limit", best_to_a, best_lb, None,
                                 "cbc_tree: this round's accumulated constraints were "
                                 "reported infeasible by CBC despite an earlier, "
                                 "independently-verified feasible incumbent existing -- "
                                 "falling back to it rather than reporting infeasible")
            # No prior verified incumbent either -- but CBC's INFEASIBLE cannot be trusted
            # at face value here still (docstring finding #4: the *identical* model, minus
            # only `model.lazy_constrs_generator`, was confirmed to solve to OPTIMAL on a
            # case where the generator-attached model reported INFEASIBLE).  One
            # verification pass without the generator before ever believing it.
            vraw, vmodel, vxvars, _vza, _vzb, _vgen, _vnst = _build_and_solve(
                G, nodes, idx, ua, ub, ua_sum, ub_sum, comps, edges, rho, seed,
                extra_a, extra_b, extra_cuts, warm_to_a, remaining, minsep, None,
                False, None, no_lazy=True)
            if vraw in (mip.OptimizationStatus.OPTIMAL, mip.OptimizationStatus.FEASIBLE):
                vx = np.array([bool(round(v.x)) for v in vxvars])
                vto_a = {nodes[i] for i in range(n) if vx[i]}
                if base.is_feasible(G, nodes, vto_a):
                    vga = float(ua[vx].sum())
                    vgb = float(ub[~vx].sum())
                    if vga > 0 and vgb > 0:
                        vper = base.perimeter(G, nodes, vto_a) if rho else 0
                        vLB = math.log(vga) + math.log(vgb) - rho * vper
                        return _finalise("time_limit", vto_a, vLB, None,
                                         "cbc_tree: CBC reported INFEASIBLE with the lazy "
                                         "generator attached; the identical model without "
                                         "it found this feasible incumbent instead -- "
                                         "reporting it rather than a false infeasible")
                else:
                    # Not connectivity-feasible: turn this into a fresh backstop cut and
                    # give the *next* fresh round the benefit of it, instead of discarding
                    # the discovery and declaring infeasible on the spot.
                    viol = _find_violations(nodes, idx, comps, vto_a, bool(minsep))
                    new = [(side, C, Q) for side, C, Q, _P in viol
                          if (side, C, Q) not in seen_extra_cuts]
                    if new:
                        for side, C, Q in new:
                            seen_extra_cuts.add((side, C, Q))
                            extra_cuts.append((side, C, Q))
                        warm_to_a = None
                        continue
            return _finalise("infeasible", None, None, None,
                             "cbc_tree: model proven infeasible (verified without the lazy "
                             "generator attached too)")

        return _finalise("error", best_to_a, best_lb, None,
                         f"cbc_tree: unrecognised python-mip status {raw!r}")

    return base.Result(status="time_limit", to_a=best_to_a, LB=best_lb, UB=None,
                       ub_scope="global", n_cuts=total_cuts, n_tangents=total_tangents,
                       extra=dict(minsep=bool(minsep), n_outer=n_outer),
                       message="cbc_tree: outer OA-restart budget exhausted before "
                               "tangent convergence")


def solve(G, nodes, **kw):
    """Run the CBC tree and **demote the result to a heuristic** (main-session decision,
    2026-08-30, S1 review).

    In the S1 screening `cbc_tree` returned `status="optimal"` with a global UB *below*
    `brute`'s true optimum on two C2 pairs (a false certificate: python-mip 2.0's
    `lazy_constrs_generator` does not reliably enforce a just-added row before CBC
    finalises an incumbent -- the five findings in the module docstring), and two of its
    jobs ignored both `max_seconds` and the SIGALRM backstop.  A bound that can be wrong
    must not enter the cross-method UB*, so every result is reported as `heuristic`
    with `UB=None`; the engine's own claim is preserved in `extra["cbc_claimed_status"]`
    / `extra["cbc_claimed_UB"]` for the record.  `error` and `infeasible` pass through.
    """
    res = _solve_cbc(G, nodes, **kw)
    if res.status in ("error", "infeasible"):
        return res
    res.extra = dict(res.extra or {}, cbc_claimed_status=res.status, cbc_claimed_UB=res.UB)
    res.status = "heuristic"
    res.UB = None
    res.message = (res.message + "; " if res.message else "") + \
        "cbc_tree: demoted to heuristic (python-mip lazy rows unreliable; see solve())"
    return res
