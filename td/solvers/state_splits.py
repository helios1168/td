"""state_splits.py -- Track 2: the state-level minimum-splits MILP.

Level 1 decides, per band width `delta`, **which states split** and how each split state's mass
is shared between districts; level 2 (`realise`) turns that decision into zip labels.  The
committed draw's `k` centres are fixed data here: a state's cost of joining district `j` is its
exact moment about that centre, `D_sj = sum_{z in s} M_z d^2(z, c_j) / M_s`, precomputed by the
caller.  States enter as an index over `0..S-1` and the rook graph as an edge list over those
indices; this module never touches `td.geo` -- the CLI fetches the graph and passes it in::

    min   sum_s (sum_j z_sj - 1)  +  eps * sum_s sum_j M_s D_sj y_sj
    s.t.  sum_j y_sj = 1                        for every s      (all of s placed)
          eta z_sj <= y_sj <= z_sj,  z_sj in {0,1}               (z marks *real* contact)
          tau(1-delta) <= sum_s M_s y_sj <= tau(1+delta)  per j  (the band)
          {s : z_sj = 1} connected in the rook graph      per j  (contiguity)

`eps` is lexicographic (`eps_lexicographic`): the whole compactness term is worth under half a
split at every feasible `y`, so it only ranks solutions of equal split count and never buys one.

`eta` (default 1%, the plan's own reporting threshold for "state s is in district j") is not
cosmetic.  Contiguity binds the **z**-set, and `y_sj <= z_sj` alone lets `z_sj = 1` with
`y_sj = 0`: a state can be bought as a bridge for one split while the district actually realised
at level 2 -- which owns only the states with `y_sj > 0` -- is disconnected (path A-B-C, masses
1, 2, 1, tau = 2, delta = 0; docs/VERIFY_state_splits.md section 1b).  `y_sj >= eta z_sj` makes
a z-flag imply real mass, so contiguity of `z` is contiguity of the district.

Contiguity is VBL's single-commodity flow (`scf`), compact and solved in one shot -- no lazy
separation, and so none of trap 14's SCIP configuration.  Per district there is a variable root
`r_sj <= z_sj` with `sum_s r_sj = 1`, a directed flow variable on each rook edge in each
direction bounded by `(N-1) z_uj` and `(N-1) z_vj`, and net inflow at `s` of at least
`z_sj - N r_sj` (N = S).  Districts are anonymous; the distinct fixed centres in the tie-break
break the k! symmetry in practice at this size.

Conditioning: the mass rows are divided by `tau`, so the band reads `[1-delta, 1+delta]` and
the coefficients are state shares of a district rather than dollars -- HiGHS' feasibility
tolerances are absolute and the real `M` is in dollars.  The optimum is unchanged (scaling a
row and its right-hand side together leaves the feasible set identical).

The MILP uses the whole band wherever that saves a split, so at a wide `delta` it returns an
imbalance the chosen splits did not require.  `balance_pass` fixes `z` and re-solves for `y`,
lexicographically: first the maximum deviation from `tau`, then the spread at that deviation.
`delta` becomes a cap and the shares become the tightest balance those splits allow.

Pure functions on arrays; the only dependency inside `td/` is `centers` (`realise` calls
`centers.assign` per split state, and its Lloyd rounds `centers._centroids`).
"""
from __future__ import annotations

import inspect
import multiprocessing as mp
import os
import time
from dataclasses import dataclass, field
from queue import Empty

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

from td.solvers import centers as _centers

COST_TOL = 1e-12         # a Lloyd round is accepted only if the state's cost rises by no more


def failure_reason(status: int) -> str:
    """Name what a failed `milp` call actually established, from scipy's status code.

    `2` is HiGHS Status 8, a proof that no assignment satisfies the constraints.  `1` is HiGHS
    Status 13, the time limit: the search did not find a feasible point, which is not the same
    claim and must never be reported as one (docs/HEADLINE.md section 7).  Anything else is
    neither, and says so.

    The `1` label is exact under `solve(..., strict=False)`, which is how every caller that
    passes a `time_limit` runs: `strict=False` returns a time-limited incumbent rather than
    raising, so a `1` that reaches here has none.  Under `strict=True` a time limit raises
    whether or not it holds an incumbent, and only the first of those is `no_incumbent`.
    """
    return {1: "no_incumbent", 2: "infeasible"}.get(int(status), "other")


class SolveFailure(RuntimeError):
    """A minimum-splits MILP that returned nothing usable, with `reason` kept beside the text.

    A `RuntimeError` subclass on purpose: `solve` raised a bare one before this existed, and
    every caller that catches `RuntimeError` still catches this.
    """

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"minimum-splits MILP did not solve to optimality: {message}")
        self.status = int(status)
        self.reason = failure_reason(status)
        self.solver_message = message


@dataclass
class SplitProblem:
    """The MILP in matrix form plus the index layout `solve` reads the solution back with.

    Variables are four contiguous blocks, each in row-major `(s, j)` / `(arc, j)` order::

        z at off_z + s*k + j     binary, state s touches district j
        y at off_y + s*k + j     continuous in [0, 1], s's share going to j
        r at off_r + s*k + j     binary, s is district j's flow root
        f at off_f + a*k + j     continuous in [0, N-1], flow on directed arc a for district j

    Directed arc `2*e` is `edges[e][0] -> edges[e][1]` and arc `2*e+1` is its reverse.  `rows`
    maps a constraint block name to its `(start, stop)` row range in `A`.
    """

    c: np.ndarray
    A: sparse.csc_matrix
    lb: np.ndarray
    ub: np.ndarray
    integrality: np.ndarray
    var_lb: np.ndarray
    var_ub: np.ndarray
    M_s: np.ndarray
    D: np.ndarray
    edges: list[tuple[int, int]]
    tau: float
    delta: float
    eps: float
    eta: float
    n_state: int
    k: int
    off_z: int
    off_y: int
    off_r: int
    off_f: int
    n_var: int
    rows: dict[str, tuple[int, int]] = field(default_factory=dict)


def _block(rows: np.ndarray, cols: np.ndarray, vals: np.ndarray,
           n_row: int, n_var: int) -> sparse.coo_matrix:
    """A constraint block as a COO matrix; duplicate `(row, col)` entries are summed."""
    return sparse.coo_matrix((vals, (rows, cols)), shape=(n_row, n_var))


def bound_z(problem: SplitProblem, s: int, j: int, lo: float, hi: float) -> None:
    """Bound `z_sj` in place: `lo <= z_sj <= hi` at `off_z + s*k + j`.

    `(1, 1)` forces state `s` to touch district `j` and `(0, 0)` forbids it; that pair is the
    whole of what an override can say at level 1, since `y` follows `z` through
    `eta z <= y <= z`.  Nothing else about the model moves, so a bound is safe to apply to an
    already-assembled `SplitProblem`.

    An anchor (`build_milp(anchors=...)`) sets the same lower bound, so a bound applied after
    the anchors silently overrides one; the CLI drops a contradicted anchor explicitly instead,
    so the release is visible in the log and in `params.json`.
    """
    if not (0 <= s < problem.n_state and 0 <= j < problem.k):
        raise ValueError(f"bound ({s}, {j}) out of range")
    if not (0.0 <= float(lo) <= float(hi) <= 1.0):
        raise ValueError(f"bound ({s}, {j}) needs 0 <= lo <= hi <= 1, got ({lo}, {hi})")
    at = problem.off_z + s * problem.k + j
    problem.var_lb[at] = float(lo)
    problem.var_ub[at] = float(hi)


def build_milp(M_s: np.ndarray, D: np.ndarray, edges: list[tuple[int, int]],
               tau: float, delta: float, eps: float, *, eta: float = 0.01,
               anchors: list[tuple[int, int]] | None = None,
               caps: dict[int, int] | None = None,
               bounds: list[tuple[int, int, float, float]] | None = None,
               fix_roots: bool = False) -> SplitProblem:
    """Assemble the minimum-splits MILP.  `M_s` is `(S,)`, `D` is `(S, k)`, `edges` the rook
    graph over state indices (undirected, given once per pair).  `eta` is the minimum share a
    state must send to a district it is flagged as touching (see the module docstring).

    `anchors` is a list of `(s, j)` pairs forced to `z_sj = 1`: district `j` keeps state `s`.
    Anchoring every district to its committed home state names the districts and so removes
    the `k!` relabelling symmetry, which the `eps` tie-break alone does not break at S = 49,
    k = 18 (HiGHS left a one-split gap open after 600 s without anchors).

    `caps` maps a state index to the maximum number of districts it may touch
    (`sum_j z_sj <= caps[s]`).  When falsy, no new row block is added and `rows` gains no new
    key, so an uncapped call reproduces bit for bit.  When given, a row is appended for each
    capped state, after `net`, in `sorted(caps)` order, under the name `"cap"`.

    `bounds` is a list of `(s, j, lo, hi)` applied through `bound_z` **after** the anchors and
    the caps, so an override wins over an anchor on the same `(s, j)`.  Bounds add no row, so
    the matrix is the same whether or not they are given.

    `fix_roots`, when true, roots every anchor that is still standing once `bounds` has been
    applied at its home state (`milp_engines.fix_roots`'s own tightening, run here on whatever
    anchors survive).  An anchor a `bounds` entry has forbidden or refused no longer has
    `z_sj`'s lower bound at 1, so it is left out; rooting a released anchor would make the MILP
    infeasible or worse (`tools/verify/milp_root_fix/REPORT.md`, "the gap the adoption step must
    guard")."""
    M_s = np.asarray(M_s, float)
    D = np.asarray(D, float)
    if M_s.ndim != 1 or D.ndim != 2 or D.shape[0] != M_s.shape[0]:
        raise ValueError(f"M_s {M_s.shape} and D {D.shape} disagree")
    S, k = D.shape
    N = S
    E = [(int(u), int(v)) for u, v in edges]
    if any(u == v or not (0 <= u < S) or not (0 <= v < S) for u, v in E):
        raise ValueError("edges must be distinct state indices in range")
    n_arc = 2 * len(E)
    tau = float(tau)
    if tau <= 0:
        raise ValueError("tau must be positive")
    for s, m in (caps or {}).items():
        if not (0 <= s < S):
            raise ValueError(f"cap state {s} out of range")
        if not (1 <= m <= k):
            raise ValueError(f"cap {m} for state {s} outside [1, {k}]")

    off_z, off_y, off_r = 0, S * k, 2 * S * k
    off_f = 3 * S * k
    n_var = off_f + n_arc * k

    c = np.zeros(n_var)
    c[off_z:off_z + S * k] = 1.0
    c[off_y:off_y + S * k] = float(eps) * (M_s[:, None] * D).ravel()

    sk = np.arange(S * k)
    j_of = np.tile(np.arange(k), S)                      # district of flat (s, j)
    s_of = np.repeat(np.arange(S), k)

    blocks, lb, ub, rows = [], [], [], {}

    def add(name, mat, lo, hi):
        start = sum(b.shape[0] for b in blocks)
        blocks.append(mat)
        lb.append(np.asarray(lo, float))
        ub.append(np.asarray(hi, float))
        rows[name] = (start, start + mat.shape[0])

    # sum_j y_sj = 1
    add("place", _block(s_of, off_y + sk, np.ones(S * k), S, n_var), np.ones(S), np.ones(S))
    # y_sj - z_sj <= 0
    add("yz", _block(np.concatenate([sk, sk]),
                     np.concatenate([off_y + sk, off_z + sk]),
                     np.concatenate([np.ones(S * k), -np.ones(S * k)]), S * k, n_var),
        np.full(S * k, -np.inf), np.zeros(S * k))
    # eta z_sj - y_sj <= 0
    add("yz_lo", _block(np.concatenate([sk, sk]),
                        np.concatenate([off_z + sk, off_y + sk]),
                        np.concatenate([np.full(S * k, float(eta)), -np.ones(S * k)]),
                        S * k, n_var),
        np.full(S * k, -np.inf), np.zeros(S * k))
    # (1-delta) <= sum_s (M_s/tau) y_sj <= (1+delta)
    add("band", _block(j_of, off_y + sk, np.repeat(M_s / tau, k), k, n_var),
        np.full(k, 1.0 - delta), np.full(k, 1.0 + delta))
    # sum_s r_sj = 1
    add("root", _block(j_of, off_r + sk, np.ones(S * k), k, n_var), np.ones(k), np.ones(k))
    # r_sj - z_sj <= 0
    add("rz", _block(np.concatenate([sk, sk]),
                     np.concatenate([off_r + sk, off_z + sk]),
                     np.concatenate([np.ones(S * k), -np.ones(S * k)]), S * k, n_var),
        np.full(S * k, -np.inf), np.zeros(S * k))

    tails = np.array([e[i] for e in E for i in (0, 1)], int) if E else np.zeros(0, int)
    heads = np.array([e[1 - i] for e in E for i in (0, 1)], int) if E else np.zeros(0, int)
    arc_flat = np.arange(n_arc * k)
    arc_of = np.repeat(np.arange(n_arc), k)
    j_arc = np.tile(np.arange(k), n_arc)
    for name, ends in (("flow_tail", tails), ("flow_head", heads)):
        # f_aj - (N-1) z_{end(a), j} <= 0
        add(name, _block(np.concatenate([arc_flat, arc_flat]),
                         np.concatenate([off_f + arc_flat, off_z + ends[arc_of] * k + j_arc]),
                         np.concatenate([np.ones(n_arc * k), np.full(n_arc * k, -(N - 1.0))]),
                         n_arc * k, n_var),
            np.full(n_arc * k, -np.inf), np.zeros(n_arc * k))
    # z_sj - N r_sj - (inflow - outflow)_sj <= 0
    add("net", _block(np.concatenate([sk, sk, heads[arc_of] * k + j_arc, tails[arc_of] * k + j_arc]),
                      np.concatenate([off_z + sk, off_r + sk,
                                      off_f + arc_flat, off_f + arc_flat]),
                      np.concatenate([np.ones(S * k), np.full(S * k, -float(N)),
                                      -np.ones(n_arc * k), np.ones(n_arc * k)]),
                      S * k, n_var),
        np.full(S * k, -np.inf), np.zeros(S * k))

    if caps:
        idx = np.array(sorted(caps), int)
        r_cap = np.repeat(np.arange(len(idx)), k)
        c_cap = (off_z + idx[:, None] * k + np.arange(k)).ravel()
        add("cap", _block(r_cap, c_cap, np.ones(len(idx) * k), len(idx), n_var),
            np.full(len(idx), -np.inf), np.array([caps[s] for s in idx], float))

    var_lb = np.zeros(n_var)
    var_ub = np.ones(n_var)
    var_ub[off_f:] = max(N - 1.0, 0.0)
    for s, j in anchors or ():
        if not (0 <= s < S and 0 <= j < k):
            raise ValueError(f"anchor ({s}, {j}) out of range")
        var_lb[off_z + s * k + j] = 1.0
    integrality = np.zeros(n_var)
    integrality[off_z:off_z + S * k] = 1
    integrality[off_r:off_r + S * k] = 1

    problem = SplitProblem(
        c=c, A=sparse.csc_matrix(sparse.vstack(blocks)),
        lb=np.concatenate(lb), ub=np.concatenate(ub),
        integrality=integrality, var_lb=var_lb, var_ub=var_ub,
        M_s=M_s, D=D, edges=E, tau=tau, delta=float(delta), eps=float(eps), eta=float(eta),
        n_state=S, k=k, off_z=off_z, off_y=off_y, off_r=off_r, off_f=off_f,
        n_var=n_var, rows=rows,
    )
    for bs, bj, lo, hi in bounds or ():
        bound_z(problem, int(bs), int(bj), float(lo), float(hi))

    if fix_roots:
        survivors = [(s, j) for s, j in (anchors or ())
                    if problem.var_lb[problem.off_z + s * k + j] >= 1.0 - 1e-9]
        if survivors:
            from td.solvers import milp_engines as _me      # lazy: that module imports this one
            problem = _me.fix_roots(problem, survivors)
    return problem


def solve(problem: SplitProblem, *, time_limit: float | None = None, strict: bool = True,
         engine: str = "scipy", strategy: str = "direct", primal_seconds: float = 30.0,
         threads: int | None = None, portfolio_quick_seconds: float = 5.0) -> dict:
    """Solve `problem` and read `z`, `y` back.  `engine="scipy", strategy="direct"` is this
    function's original body, unchanged: `scipy.optimize.milp`, no threads, no callbacks, the
    only path every caller used before `milp_engines` existed.

    `engine` picks the solver (`"scipy"`, `"highs"`, `"scip"`; anything else goes to
    `milp_engines.solve_problem`, imported lazily since that module imports this one).

    `strategy="direct"` is one solve to `time_limit`.  `strategy="descent"` (`_solve_descent`)
    is three phases instead: a quick incumbent, then repeated `milp_engines.with_cutoff` calls
    proving no smaller split count exists, then one more `with_cutoff` closing the compactness
    tie-break at that count, warm-started from the best incumbent.  It adds `certified_splits`
    (phase two's outcome) and `phases` (a log of `{phase, seconds, status, splits}`) to the
    return; `status` reports phase three's outcome (`0` closed, `"time_limit"` otherwise), so a
    map's split count can be certified even when its exact tie-break is not.

    `strategy="portfolio"` (`_solve_portfolio`) replaces phase A with rounds of `highs` and
    `scip` racing in their own processes.  Round 0 races them on the plain problem; every
    incumbent either one finds is checked in the parent by a fast `with_cutoff` feasibility
    solve (`portfolio_quick_seconds`, default 5 s).  An infeasible answer certifies the split
    count at once.  When that quick check only times out, the parent does not give up: it waits
    a further 5 s for a strictly better incumbent from the members, and only then stops them and
    starts the next round, where both members solve `with_cutoff(problem, s_star)` itself for
    the remaining time -- the cutoff row can turn a search that never converges into one that
    closes in seconds.  A member that proves a cutoff round's problem infeasible certifies
    `s_star` directly; one that instead solves it hands the smaller split count through the same
    quick-check-then-round cycle.  Phase C then closes the tie-break exactly as `_solve_descent`'s
    own phase C does.  `engine` is ignored (the members are fixed); `threads` is read as the
    machine's core count, used to size the members, not the parent's own solves.

    Raises `SolveFailure` when nothing usable comes back, same reasons either strategy: a
    `strict=True` (the default) time limit with no incumbent, or a proven infeasibility.
    """
    if strategy == "direct":
        result = _solve_direct(problem, time_limit=time_limit, strict=strict, engine=engine,
                               threads=threads)
    elif strategy == "descent":
        result = _solve_descent(problem, time_limit=time_limit, strict=strict, engine=engine,
                                primal_seconds=primal_seconds, threads=threads)
    elif strategy == "portfolio":
        result = _solve_portfolio(problem, time_limit=time_limit, strict=strict, threads=threads,
                                  quick_certify_seconds=portfolio_quick_seconds)
    else:
        raise ValueError(f"unknown strategy {strategy!r}; "
                         "expected 'direct', 'descent' or 'portfolio'")
    result.setdefault("engine", engine)
    result.setdefault("strategy", strategy)
    result.setdefault("certified_splits", result.get("status") == 0)
    result.setdefault("phases", [])
    return result


def _solve_direct(problem: SplitProblem, *, time_limit, strict, engine, threads) -> dict:
    """`strategy="direct"`: one solve to `time_limit`, on `engine`."""
    if engine == "scipy":
        return _solve_scipy(problem, time_limit=time_limit, strict=strict)
    from td.solvers import milp_engines as _me               # lazy: it imports this module
    return _me.solve_problem(problem, engine, time_limit=time_limit, threads=threads)


def _solve_descent(problem: SplitProblem, *, time_limit, strict, engine, primal_seconds,
                   threads) -> dict:
    """`strategy="descent"`, see `solve`'s docstring for the three phases.  `time_limit` bounds
    the whole call; each phase spends only what the previous ones left (`time_limit=None` still
    caps phase A at `primal_seconds`, but phases B and C then run until they resolve)."""
    from td.solvers import milp_engines as _me                # lazy: it imports this module

    t0 = time.time()

    def left():
        return None if time_limit is None else max(0.0, time_limit - (time.time() - t0))

    phases: list[dict] = []

    # Phase A: a quick incumbent, never more than primal_seconds.
    budget = primal_seconds if time_limit is None else min(primal_seconds, left())
    ta = time.time()
    best, a_status = None, None
    try:
        best = _me.solve_problem(problem, engine, time_limit=budget, threads=threads,
                                 heuristic_effort=0.5)
        a_status = best["status"]
    except SolveFailure as exc:
        if exc.reason == "infeasible":
            raise
        a_status = exc.reason                                 # "no_incumbent"
    phases.append(dict(phase="incumbent", seconds=time.time() - ta, status=a_status,
                       splits=(best["splits"] if best else None)))

    if best is None:
        tf = time.time()
        result = _solve_direct(problem, time_limit=left(), strict=strict, engine=engine,
                               threads=threads)
        phases.append(dict(phase="direct", seconds=time.time() - tf,
                           status=result.get("status"), splits=result.get("splits")))
        result.update(engine=engine, strategy="descent", certified_splits=False, phases=phases)
        return result

    # Phase B: does a map with fewer splits exist?  Infeasible certifies s_star; a better
    # incumbent lowers s_star and the question is asked again; a bare time limit gives up.
    s_star = best["splits"]
    certified = False
    while True:
        rem = left()
        if rem is not None and rem <= 0:
            break
        tb = time.time()
        try:
            res_b = _me.solve_problem(_me.with_cutoff(problem, s_star), engine, time_limit=rem,
                                      threads=threads, heuristic_effort=0.5)
        except SolveFailure as exc:
            phases.append(dict(phase="descent", seconds=time.time() - tb, status=exc.reason,
                               splits=None))
            certified = exc.reason == "infeasible"
            break
        phases.append(dict(phase="descent", seconds=time.time() - tb, status=res_b["status"],
                           splits=res_b["splits"]))
        s_star, best = res_b["splits"], res_b

    # Phase C: close the compactness tie-break at s_star, warm-started from the incumbent.
    # scipy has no warm-start hook (milp_engines.solve_problem raises on warm= for it), so it
    # gets none; every other engine gets the incumbent's own z, y.
    rem = left()
    result, closed = dict(best), False
    if rem is not None and rem <= 0:
        pass                                                   # no time left; keep the incumbent
    else:
        tc = time.time()
        warm = None if engine == "scipy" else dict(z=best["z"], y=best["y"])
        try:
            res_c = _me.solve_problem(_me.with_cutoff(problem, s_star + 1), engine,
                                      time_limit=rem, threads=threads, warm=warm,
                                      heuristic_effort=0.5)
            phases.append(dict(phase="tiebreak", seconds=time.time() - tc,
                               status=res_c["status"], splits=res_c["splits"]))
            result, closed = res_c, res_c["status"] == 0
        except SolveFailure as exc:
            # the incumbent itself satisfies this cutoff, so infeasible should not happen; any
            # failure here just means the clock ran out before an improvement was found.
            phases.append(dict(phase="tiebreak", seconds=time.time() - tc, status=exc.reason,
                               splits=None))

    result = dict(result)
    result.update(engine=engine, strategy="descent", certified_splits=certified, phases=phases,
                 status=(0 if closed else "time_limit"))
    return result


def _portfolio_member(name: str, kwargs: dict, problem: SplitProblem, time_limit,
                      queue: mp.Queue, stop) -> None:
    """One `strategy="portfolio"` member's whole run, in its own process: solve `problem` on
    engine `name`, streaming every incumbent through `queue` as `(member, splits, z, y,
    objective, seconds)`, then a final `(member, "done", status)`.  `milp_engines` is imported
    lazily, the same reason every other cross-module call in this file is."""
    from td.solvers import milp_engines as _me

    def on_incumbent(info: dict) -> None:
        queue.put((name, info["splits"], info["z"], info["y"], info["objective"],
                  info["seconds"]))

    try:
        res = _me.solve_problem(problem, name, time_limit=time_limit,
                                on_incumbent=on_incumbent, stop=stop, **kwargs)
        status = res["status"]
    except SolveFailure as exc:
        status = exc.reason
    queue.put((name, "done", status))


def _solve_portfolio(problem: SplitProblem, *, time_limit, strict, threads,
                     quick_certify_seconds: float = 5.0) -> dict:
    """`strategy="portfolio"`: rounds of `highs` and `scip` searching together, each in its own
    process.  Cores = `threads` or the machine's `os.cpu_count()`; the `highs` member gets
    `cores - 3` threads (never fewer than 1) and `mip_heuristic_effort=0.5`, `scip` gets one
    thread (its own search is single-threaded; `threads` only sizes its LP) -- at `threads=2`
    (a grid chain sharing the machine with others) that floor puts `highs` at exactly 1, the
    intended split against the parent's own `threads=2` certificate calls.

    Round 0 runs the members on the plain problem.  Every incumbent either one finds is checked
    in the parent by a fast `with_cutoff` feasibility solve, `quick_certify_seconds` long
    (default 5 s, plumbed through `solve(..., portfolio_quick_seconds=...)`): infeasible
    certifies the split count at once and ends the race, a better incumbent tightens the check
    and asks again, and a bare time limit on that one check is not itself a reason to give up --
    a real certificate is usually well under a second, but "one fewer split" can need branch and
    bound the members are still running in the background.  So when the quick check only times
    out, the parent waits `quiet_seconds` (5 s) on the same round for a strictly better
    incumbent; if none arrives, it stops the round's members, joins them, and starts the next
    round with both members solving `with_cutoff(problem, s_star)` itself for whatever time is
    left -- the same problem the quick check could not close, now searched with the members' own
    full time and threads instead of a 5 s stab.  Each round gets a fresh queue and stop event,
    so a message from a member the parent has already stopped can never be read as belonging to
    the next round.  A member that finishes a cutoff round with reason `infeasible` certifies
    `s_star` directly, no further quick check needed: the parent records a `certify` phase
    naming that member and stops the other one.  A member that instead finds a solution in a
    cutoff round reports it through the same incumbent channel -- it has fewer splits than
    `s_star` by construction -- and the parent runs the quick check on it exactly as in round 0,
    opening another cutoff round at the new `s_star` if that check cannot resolve it either.  A
    member that finishes a cutoff round with `time_limit` or `no_incumbent` is simply done; once
    both members in a round are done with no verdict, the loop ends uncertified, which by then
    means time is up.

    Phase C then closes the compactness tie-break at the certified (or best known) count exactly
    as `_solve_descent`'s own phase C does.  The parent's own HiGHS calls -- every quick check
    and phase C -- always use `threads=2`, one thread count for the whole process (the pool
    hazard in the module docstring).  No incumbent from anyone within `time_limit` falls back to
    `_solve_direct`, as `_solve_descent` does."""
    from td.solvers import milp_engines as _me

    cores = threads if threads else (os.cpu_count() or 1)
    t0 = time.time()
    quiet_seconds = 5.0

    def left():
        return None if time_limit is None else max(0.0, time_limit - (time.time() - t0))

    ctx = mp.get_context("spawn")
    member_specs = [
        ("highs", dict(threads=max(1, cores - 3), heuristic_effort=0.5)),
        ("scip", dict(threads=1)),
    ]

    phases: list[dict] = []
    best: dict | None = None
    certified = False

    def certify(s_star: int, current_best: dict) -> tuple[int, dict, bool, bool]:
        """Tighten `s_star` with fast cutoff solves as long as a strictly better map keeps
        turning up.  Returns `(s_star, best, certified, gave_up_on_time)`."""
        while True:
            rem = left()
            if rem is not None and rem <= 0:
                return s_star, current_best, False, True
            # A real certificate is an LP-infeasibility proof and returns in well under a
            # second on the k=20 instance; a cutoff that is not yet infeasible is as hard as
            # the whole problem, so spending more than a few seconds on it only delays the
            # queue (the members keep searching meanwhile).
            budget = quick_certify_seconds if rem is None else min(quick_certify_seconds, rem)
            tc = time.time()
            try:
                res_c = _me.solve_problem(_me.with_cutoff(problem, s_star), "highs",
                                          time_limit=budget, threads=2)
            except SolveFailure as exc:
                phases.append(dict(phase="certify", seconds=time.time() - tc,
                                   status=exc.reason))
                return s_star, current_best, exc.reason == "infeasible", False
            phases.append(dict(phase="certify", seconds=time.time() - tc,
                               status=res_c["status"]))
            s_star, current_best = res_c["splits"], res_c

    def start_round(round_problem: SplitProblem):
        q = ctx.Queue()
        stop = ctx.Event()
        procs = [ctx.Process(target=_portfolio_member,
                            args=(name, kwargs, round_problem, left(), q, stop))
                for name, kwargs in member_specs]
        for p in procs:
            p.start()
        return q, stop, procs

    def stop_round(stop, procs) -> None:
        stop.set()
        for p in procs:
            p.join(timeout=5.0)
        for p in procs:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5.0)

    round_num = 0
    s_star: int | None = None
    q, stop, procs = start_round(problem)
    phases.append(dict(phase="round", round=round_num, problem="plain",
                       seconds=time.time() - t0))
    done: set[str] = set()
    pending_deadline: float | None = None

    try:
        while True:
            rem = left()
            if rem is not None and rem <= 0:
                break
            if pending_deadline is not None and time.time() >= pending_deadline:
                stop_round(stop, procs)
                round_num += 1
                q, stop, procs = start_round(_me.with_cutoff(problem, s_star))
                done = set()
                pending_deadline = None
                phases.append(dict(phase="round", round=round_num,
                                   problem=f"cutoff<{s_star}>", seconds=time.time() - t0))
                continue
            heartbeat = 1.0 if rem is None else min(1.0, rem)
            wait = heartbeat if pending_deadline is None else min(
                heartbeat, max(0.0, pending_deadline - time.time()))
            try:
                msg = q.get(timeout=wait)
            except Empty:
                continue

            member = msg[0]
            if msg[1] == "done":
                done.add(member)
                status = msg[2]
                if round_num > 0 and status == "infeasible":
                    phases.append(dict(phase="certify", member=member,
                                       seconds=time.time() - t0, status="infeasible"))
                    certified = True
                    stop_round(stop, procs)
                    break
                if len(done) >= len(procs):
                    if pending_deadline is not None:
                        pending_deadline = time.time()      # nothing more will arrive; go now
                    else:
                        break                                # no verdict this round; time is up
                continue

            _, splits, z, y, objective, seconds = msg
            phases.append(dict(phase="incumbent", member=member, seconds=seconds,
                               splits=splits))
            if best is not None and splits >= best["splits"]:
                continue
            # a member's incumbent carries only {splits, z, y, objective}; fill it out to the
            # same shape every engine's own decode returns (split_states, spread_rel, ...) so a
            # caller sees the full result even if phase C below never gets to replace it.
            best = dict(_me._decode_zy(problem, z, y), objective=float(objective),
                       status="time_limit", mip_gap=float("nan"), nodes=0,
                       dual_bound=float("nan"), trajectory=[])
            s_star, best, cert_ok, gave_up = certify(splits, best)
            if cert_ok:
                certified = True
                stop_round(stop, procs)
                break
            if gave_up:
                stop_round(stop, procs)
                break
            rem2 = left()
            quiet = quiet_seconds if rem2 is None else min(quiet_seconds, rem2)
            pending_deadline = time.time() + quiet
    finally:
        stop.set()
        for p in procs:
            p.join(timeout=5.0)
        for p in procs:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5.0)

    if best is None:
        result = _solve_direct(problem, time_limit=left(), strict=strict, engine="highs",
                               threads=2)
        result.update(engine="highs", strategy="portfolio", certified_splits=False,
                     phases=phases)
        return result

    s_star = best["splits"]
    rem = left()
    result, closed = dict(best), False
    if rem is not None and rem <= 0:
        pass                                                   # no time left; keep the incumbent
    else:
        tc = time.time()
        warm = dict(z=best["z"], y=best["y"])
        try:
            res_c = _me.solve_problem(_me.with_cutoff(problem, s_star + 1), "highs",
                                      time_limit=rem, threads=2, warm=warm)
            phases.append(dict(phase="tiebreak", seconds=time.time() - tc,
                               status=res_c["status"], splits=res_c["splits"]))
            result, closed = res_c, res_c["status"] == 0
        except SolveFailure as exc:
            phases.append(dict(phase="tiebreak", seconds=time.time() - tc, status=exc.reason,
                               splits=None))

    result = dict(result)
    result.update(engine="highs", strategy="portfolio", certified_splits=certified,
                 phases=phases, status=(0 if closed else "time_limit"))
    return result


def _solve_scipy(problem: SplitProblem, *, time_limit: float | None = None,
                 strict: bool = True) -> dict:
    """Solve to proven optimality (`mip_rel_gap = 0.0`, trap 12) and read `z`, `y` back.

    Raises unless HiGHS reports optimality: a time-limited or infeasible run is not a split
    count.  `y` is zeroed where `z` is 0 (the LP can leave 1e-12 there) and each state's row is
    renormalised to sum to 1, so `realise`'s targets are exact.

    `strict=False` softens only the time-limit case: if HiGHS stops at `time_limit` with an
    incumbent in hand (`res.status == 1`, `res.x is not None`), that incumbent is returned with
    `status="time_limit"` and its own `mip_gap` instead of raising.  Infeasible, unbounded or
    incumbent-less runs still raise regardless of `strict`, as `SolveFailure`, whose `reason`
    separates a refutation from a search that ran out of time.
    """
    options = {"mip_rel_gap": 0.0}
    if time_limit is not None:
        options["time_limit"] = float(time_limit)
    res = milp(c=problem.c,
               constraints=LinearConstraint(problem.A, problem.lb, problem.ub),
               integrality=problem.integrality,
               bounds=Bounds(problem.var_lb, problem.var_ub),
               options=options)
    timed_out = (not strict) and res.status == 1 and res.x is not None
    if not timed_out and (res.status != 0 or res.x is None):
        raise SolveFailure(res.status, res.message)

    S, k = problem.n_state, problem.k
    x = np.asarray(res.x, float)
    z = x[problem.off_z:problem.off_z + S * k].reshape(S, k) > 0.5
    y = np.clip(x[problem.off_y:problem.off_y + S * k].reshape(S, k), 0.0, 1.0)
    y = np.where(z, y, 0.0)
    y = y / y.sum(axis=1, keepdims=True)
    masses = problem.M_s @ y
    return dict(
        z=z, y=y, masses=masses,
        splits=int(z.sum() - S),
        split_states=[s for s in range(S) if int(z[s].sum()) >= 2],
        spread_rel=float((masses.max() - masses.min()) / masses.mean()),
        max_dev_rel=float(np.abs(masses - problem.tau).max() / problem.tau),
        objective=float(res.fun),
        status="time_limit" if timed_out else int(res.status),
        mip_gap=float(res.mip_gap),
        nodes=int(res.mip_node_count),
        dual_bound=float(res.mip_dual_bound),
    )


def eps_lexicographic(M_s: np.ndarray, D: np.ndarray) -> float:
    """`0.5 / sum_s M_s max_j D_sj` -- the tie-break is worth under half a split at **every**
    feasible `y`, so it ranks equal-split solutions and can never buy one.

    The plan's `0.5 / sum_s sum_j M_s D_sj y0_sj` calibrates at the committed map's own
    composition only, and fails exactly when the MILP beats the committed map: on a 4-state path
    with `D = [[1,100],[100,1],[1,100],[100,1]]` it returns 2 splits where 0 is optimal
    (docs/VERIFY_state_splits.md section 2).  The bound here is over the polytope: the only
    per-state row is `sum_j y_sj = 1`, so the term is at most `sum_s M_s max_j D_sj`.
    """
    M_s = np.asarray(M_s, float)
    total = float((M_s * np.asarray(D, float).max(axis=1)).sum())
    if total <= 0:
        raise ValueError("the state moments must be positive")
    return 0.5 / total


def balance_pass(problem: SplitProblem, z: np.ndarray) -> dict:
    """Fix `z` and re-solve for `y`, lexicographically: minimise the maximum deviation
    `t >= |mass_j - tau|`, then minimise the spread `u - l` at that `t`.

    Two LPs (`y` is continuous, `z` only sets its bounds), so the splits are exactly those the
    MILP chose and the shares are the tightest balance they allow.  The second LP is not
    decoration: `sum_j (mass_j - tau) = 0` gives only `t <= spread <= 2t`, so minimising `t`
    pins the spread within a factor 2 and the simplex breaks the remaining ties arbitrarily --
    at delta = 10% that has been seen to *widen* the spread by 18% at an unchanged `t`
    (docs/VERIFY_state_splits.md section 3).

    No band rows are carried over: the MILP's own `y` is feasible here, so `t* <= delta*tau`
    automatically.  `eta z <= y <= z` is carried over, since dropping the lower bound would let
    the pass empty a district's bridge state and disconnect it again.  Deviations are relative
    (the mass rows are scaled by `tau` as in `build_milp`).
    """
    S, k = problem.n_state, problem.k
    z = np.asarray(z, bool)
    if z.shape != (S, k):
        raise ValueError(f"z must be {(S, k)}, got {z.shape}")
    n_y = S * k
    sk = np.arange(n_y)
    j_of = np.tile(np.arange(k), S)

    def eq_rows(n_var):
        return sparse.coo_matrix((np.ones(n_y), (np.repeat(np.arange(S), k), sk)),
                                 shape=(S, n_var)).tocsc()

    def mass_rows(n_var):
        return sparse.coo_matrix((np.repeat(problem.M_s / problem.tau, k), (j_of, sk)),
                                 shape=(k, n_var)).tocsc()

    def col(n_var, at, val):
        """`k` rows carrying `val` in variable `at` and nothing else."""
        return sparse.coo_matrix((np.full(k, val), (np.arange(k), np.full(k, at))),
                                 shape=(k, n_var)).tocsc()

    def bounds(extra):
        lo = np.concatenate([(problem.eta * z).ravel(), [b[0] for b in extra]])
        hi = np.concatenate([z.ravel().astype(float), [b[1] for b in extra]])
        return np.stack([lo, hi], axis=1)

    def run(c, A_ub, b_ub, extra):
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=eq_rows(c.shape[0]), b_eq=np.ones(S),
                      bounds=bounds(extra), method="highs-ds", options={"time_limit": 60.0})
        if not res.success:
            raise RuntimeError(f"balance LP failed: {res.message}")
        return res

    # LP 1: min t,  |mass_j/tau - 1| <= t
    n_var = n_y + 1
    mass, t_col = mass_rows(n_var), col(n_var, n_y, -1.0)
    c = np.zeros(n_var)
    c[n_y] = 1.0
    res1 = run(c, sparse.vstack([mass + t_col, -mass + t_col]).tocsc(),
               np.concatenate([np.ones(k), -np.ones(k)]), [(0.0, np.inf)])
    t_star = float(res1.x[n_y]) * (1.0 + 1e-9) + 1e-12

    # LP 2: min u - l,  l <= mass_j/tau <= u,  |mass_j/tau - 1| <= t*
    n_var = n_y + 2
    mass = mass_rows(n_var)
    c = np.zeros(n_var)
    c[n_y], c[n_y + 1] = 1.0, -1.0                       # u at n_y, l at n_y + 1
    A_ub = sparse.vstack([mass + col(n_var, n_y, -1.0),          # mass - u <= 0
                          -mass + col(n_var, n_y + 1, 1.0),      # l - mass <= 0
                          mass, -mass]).tocsc()
    b_ub = np.concatenate([np.zeros(2 * k),
                           np.full(k, 1.0 + t_star), np.full(k, -(1.0 - t_star))])
    res2 = run(c, A_ub, b_ub, [(0.0, np.inf), (0.0, np.inf)])

    y = np.clip(np.asarray(res2.x, float)[:n_y].reshape(S, k), 0.0, 1.0)
    y = np.where(z, y, 0.0)
    y = y / y.sum(axis=1, keepdims=True)
    masses = problem.M_s @ y
    return dict(
        y=y, masses=masses,
        spread_rel=float((masses.max() - masses.min()) / masses.mean()),
        max_dev_rel=float(np.abs(masses - problem.tau).max() / problem.tau),
    )


def connected(z_col: np.ndarray, edges: list[tuple[int, int]]) -> bool:
    """Is `{s : z_col[s]}` connected in the rook graph?  The empty set counts as connected."""
    sel = np.asarray(z_col, bool)
    nodes = set(int(s) for s in np.flatnonzero(sel))
    if not nodes:
        return True
    adj: dict[int, list[int]] = {s: [] for s in nodes}
    for u, v in edges:
        if u in nodes and v in nodes:
            adj[int(u)].append(int(v))
            adj[int(v)].append(int(u))
    seen = {next(iter(nodes))}
    stack = list(seen)
    while stack:
        s = stack.pop()
        for t in adj[s]:
            if t not in seen:
                seen.add(t)
                stack.append(t)
    return seen == nodes


def _state_cost(xy: np.ndarray, M: np.ndarray, labels: np.ndarray, C: np.ndarray) -> float:
    """`sum_z M_z d^2(z, c_label(z))` over the zips passed -- the state's compactness."""
    d2 = ((xy - C[labels]) ** 2).sum(axis=1)
    return float((M * d2).sum())


def realise(xy: np.ndarray, M: np.ndarray, state_idx: np.ndarray, z: np.ndarray,
            y: np.ndarray, centers: np.ndarray, *, rounds: int = 5,
            tiebreak: np.ndarray | None = None) -> dict:
    """Level 2: turn the level-1 decision into zip labels.

    Every unsplit state goes whole to its single district.  Each split state gets one
    `centers.assign` over its own zips against the full centre set with `targets = y_sj * M_s`
    (a district with `z_sj = 0` gets target 0, which `assign` honours), so the cut inside the
    state is a power diagram of the centres it touches.

    Then up to `rounds` Lloyd rounds per split state: recentroid every district touching the
    state from its **full** membership (whole states included), re-solve that state's LP, stop
    when the state's labels repeat.  The committed centres were placed for the old shares and
    can sit wrong for the piece a district now owns.  A round is accepted only if it does not
    raise the state's compactness, so `cost_rounds` is non-increasing by construction and
    `realise` can only improve on the plain assignment.  Per split state, `iterates` holds
    `(labels of that state's zips, centres of the districts touching it)` for the LP cut and
    every kept round, so the loop can be replayed.  `trajectory` says the same thing whole
    rather than per state: `(state, round, labels of every zip at that moment)`, with the other
    states as they stand, which is what a driver writes out as one zip table per step.

    `tiebreak` is an `(n, k)` bonus **subtracted** from `d^2` (it goes to `centers.assign` as
    `penalty=-tiebreak`), so a large entry attracts zip `z` to district `j`.  The CLI builds it
    from books; this module knows nothing about books.  It needs `centers.assign(...,
    penalty=...)`; where that keyword is absent, a non-None `tiebreak` raises
    `NotImplementedError`.
    """
    has_penalty = "penalty" in inspect.signature(_centers.assign).parameters
    if tiebreak is not None and not has_penalty:
        raise NotImplementedError(
            "tiebreak needs centers.assign(..., penalty=...), which this centers.py lacks")

    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    state_idx = np.asarray(state_idx, int)
    z = np.asarray(z, bool)
    y = np.asarray(y, float)
    C = np.array(centers, float)
    S, k = z.shape
    if state_idx.shape[0] != xy.shape[0] or M.shape[0] != xy.shape[0]:
        raise ValueError("xy, M and state_idx must agree on the zip count")
    if state_idx.size and (state_idx.min() < 0 or state_idx.max() >= S):
        raise ValueError(f"state_idx must index 0..{S - 1}")

    members = [np.flatnonzero(state_idx == s) for s in range(S)]
    labels = np.full(xy.shape[0], -1, int)
    split_states = [s for s in range(S) if int(z[s].sum()) >= 2]

    def assign_state(s: int, C_now: np.ndarray) -> tuple[np.ndarray, int]:
        idx = members[s]
        total = float(M[idx].sum())
        t = np.where(z[s], y[s], 0.0) * total
        t = t * (total / t.sum())
        if tiebreak is None:
            loc, n_frac = _centers.assign(xy[idx], M[idx], C_now, targets=t)
        else:
            loc, n_frac = _centers.assign(xy[idx], M[idx], C_now, targets=t,
                                          penalty=-np.asarray(tiebreak, float)[idx])
        return np.asarray(loc, int), int(n_frac)

    for s in range(S):
        idx = members[s]
        js = np.flatnonzero(z[s])
        if js.size == 0:
            raise ValueError(f"state {s} touches no district")
        if idx.size == 0:
            continue
        if js.size == 1:
            labels[idx] = int(js[0])
    for s in split_states:
        if members[s].size:
            labels[members[s]] = assign_state(s, C)[0]

    states: dict[int, dict] = {}
    trajectory: list[tuple[int, int, np.ndarray]] = []
    n_fractional = 0
    # TODO(2026-09-07): realise is order-dependent -- it moves the shared centre array `C`
    # as it cuts split states in turn. Deterministic, undocumented, unjudged. Fix is to
    # recentroid from a copy per state or process states in a fixed named order; judge on
    # the CA cut of the shipped cell. (STATE.md ## Next, dropped 2026-09-07 step 4)
    for s in split_states:
        idx = members[s]
        touching = np.flatnonzero(z[s])
        if idx.size == 0:
            states[s] = dict(districts=[int(j) for j in touching], n_fractional=0,
                             rounds_used=0, cost_rounds=[])
            continue
        cur, cur_frac = assign_state(s, C)
        labels[idx] = cur
        cost = _state_cost(xy[idx], M[idx], cur, C)
        cost_rounds, used = [cost], 0
        iterates = [(cur.copy(), C[touching].copy())]     # the LP cut, then each kept round
        trajectory.append((s, 0, labels.copy()))
        for _ in range(rounds):
            C_new = C.copy()
            C_new[touching] = _centers._centroids(xy, M, labels, k, prev=C)[touching]
            loc, frac = assign_state(s, C_new)
            new_cost = _state_cost(xy[idx], M[idx], loc, C_new)
            if new_cost > cost + COST_TOL:
                break                                    # a round never raises the cost
            repeat = np.array_equal(loc, cur)
            cur, cur_frac, C, cost = loc, frac, C_new, new_cost
            labels[idx] = cur
            cost_rounds.append(new_cost)
            iterates.append((cur.copy(), C[touching].copy()))
            used += 1
            trajectory.append((s, used, labels.copy()))
            if repeat:
                break
        n_fractional += cur_frac
        states[s] = dict(districts=[int(j) for j in touching], n_fractional=cur_frac,
                         rounds_used=used, cost_rounds=cost_rounds, iterates=iterates)

    return dict(labels=labels, centers=C, n_fractional=int(n_fractional),
                split_states=split_states,
                rounds_used={s: states[s]["rounds_used"] for s in split_states},
                states=states, trajectory=trajectory)
