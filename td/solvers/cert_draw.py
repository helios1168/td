"""cert_draw.py -- post-hoc certificates for a stage-1 center-based draw.

`solvers.centers` produces a draw by a heuristic (k-means++ seeding, Lloyd rounds around a
transportation LP, then a greedy Nash polish).  Nothing in that pipeline proves anything: the
seeding is random, the rounding of the LP's `k-1` split zips is arbitrary, and `improve` is a
local search.  This module says, after the fact and with a solver where a solver is needed,
**how far from optimal the draw actually is** -- and, just as importantly, which questions the
certificates do *not* answer.

Four certificates, four different things proved
-----------------------------------------------
``cert_balance_ceiling``          analytic, no solver.  `sum_j log M_j <= k log(sum M / k)` by
                                  concavity of `log` (Jensen), with equality iff every district
                                  is exactly `sum M / k`.  So the ceiling bounds **every**
                                  partition of these zips into k parts -- geometry, contiguity,
                                  indivisibility and all.  The gap in nats is the draw's total
                                  distance from a perfectly balanced map.  This is the same
                                  object `channel.allocate_districts` computes across
                                  components; here it is computed for one component set at the
                                  realised labels.

``cert_integer_balance_floor``    the honest version of the ceiling.  The ceiling is generally
                                  unreachable, because zips are indivisible: no assignment of
                                  1,223 lumps into 13 bins hits the target exactly.  This
                                  certificate solves, geometry-free,

                                      min t  s.t.  sum_z M_z x_zj = target + e_j,
                                                   |e_j| <= t,  sum_j x_zj = 1,  x binary

                                  whose optimum `t*` is the **best max-deviation any partition
                                  can achieve**, ignoring geometry entirely.  A draw whose
                                  `max_dev` sits at `t*` is perfectly balanced in the only sense
                                  available; the remaining distance to the ceiling is the price
                                  of indivisibility, not of the heuristic.

``cert_assignment_at_centers``    the geometric question, with the draw's centers **pinned**:
                                  holding the centers fixed and the balance no worse than the
                                  draw's own, is there a strictly more compact integer
                                  assignment?  Pinning removes the k! label symmetry entirely,
                                  and the resulting model is a transportation problem with two
                                  side bounds per district -- nearly integral, so HiGHS closes
                                  it fast.

``cert_power_diagram``            the same geometric question asked of the LP's **duals**
                                  instead of a MILP.  Dual feasibility of the transportation
                                  problem reads `alpha_z + M_z beta_j <= M_z d^2(z, c_j)`, so
                                  an optimal assignment puts each zip in the district
                                  minimising `d^2(z, c_j) - beta_j`: the **power (Laguerre)
                                  diagram** of the centers, weights `beta`.  That yields a
                                  lower bound whose verification is `O(nk)` arithmetic with no
                                  solver in the trusted path -- and the territory map, exactly,
                                  as `k` convex cells.  It is the cheaper and stronger half of
                                  certificate 3 for the equal-mass question; certificate 3
                                  stays because its max-deviation *band* is a different and
                                  looser feasible set that the equality rows cannot express.

What is NOT proved
------------------
The centers themselves are heuristic.  Certificate 3 is conditional on them exactly as a
k-means "certificate" would be: it proves the assignment step is optimal *given* the centers,
never that the centers are the best k points.  The joint problem (choose centers **and**
assignment) is not touched by anything here, and no bound in this module should be read as a
claim about it.  Certificate 1 does bound every partition, but only in balance -- it says
nothing about compactness; certificate 2 likewise ignores geometry by construction, which is
what makes it a valid floor: a *geometric* optimum can only be worse.

Traps observed
--------------
* **Trap 12.** `scipy.optimize.milp` inherits HiGHS' default `mip_rel_gap = 1e-4`.  A "solved"
  MILP at that tolerance is not a certificate, it is a 0.01% promise.  Every solve here passes
  `mip_rel_gap=0.0` explicitly.
* **Trap 15.** The solver's own stop reason is reported verbatim (`solver_status`,
  `solver_message`) and separately from this module's interpretation (`status`, `proved`).
  Nothing in the code keys off the interpretation: `proved` is set from the engine's status
  code alone, and a time-limited solve reports a (primal, dual) bound pair rather than a claim.
* **Symmetry** (the reason certificate 2 is the hard one).  The balance model has full
  district-label symmetry -- every one of the `k!` relabellings of a solution is another
  solution, which is exactly what branch-and-bound cannot prune.  Two cheap breaks are applied:
  the heaviest zip is fixed into district 0, and districts `1..k-1` are constrained to
  non-increasing mass (valid, since after fixing that one zip those labels are still freely
  interchangeable).  At tiny `k` this closes instantly; at `k = 13` over 1,223 zips the
  *dual* side still crawls -- the LP relaxation is `t = 0` (split the zips fractionally and
  every district is exactly on target), so the root bound is vacuous and the tree has to work
  for every nat of it.  That is reported honestly as a bound pair, and the primal side is the
  useful half regardless: a feasible `t` is a **constructive proof that balance that good is
  reachable**, which is what bounds the heuristic's loss.

Conditioning
------------
Both MILPs are descaled the way `centers.assign` descales its LP: masses by their mean, the
compactness coefficients by theirs.  HiGHS' feasibility tolerances are absolute, and the real
instance's `M` is descaled dollars, so an undescaled solve would set mass rows at ~1e3 and
distance-squared costs at ~1e12 in the same model.  Scaling a whole constraint row and its
right-hand side together leaves the feasible set identical, and scaling the objective by a
positive constant leaves the argmin identical, so nothing but the arithmetic changes.  Every
number *returned* is converted back to the caller's units, and the compactness costs are
recomputed from the integer labels rather than read off `res.fun`.

Pure functions on arrays (`xy`, `M`, `labels`, `centers`, `k`), like `centers` itself; each
returns a plain dict, and `certify` merges all three into one report.
"""
from __future__ import annotations

import math
import time

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

# a relative gap below this is treated as "no improvement" rather than a finding: the MILP and
# the direct recomputation of the draw's cost differ in the last bits of floating point
COST_TOL = 1e-9
# feasibility slack added to the mass window so the draw itself is never rejected by rounding
FEAS_TOL = 1e-9
# a dual vector is accepted as feasible when no constraint is violated by more than this
# *relative to the bound it certifies* -- the raw units are M times squared metres, so on the
# real instance an absolute residual of 1e-3 against a bound of 1e14 is exact arithmetic
DUAL_TOL = 1e-9
DEFAULT_TIME_LIMIT = 180.0


# --------------------------------------------------------------------------- helpers
def _masses(M: np.ndarray, labels: np.ndarray, k: int) -> np.ndarray:
    return np.bincount(np.asarray(labels, int), weights=np.asarray(M, float),
                       minlength=k).astype(float)


def _milp_options(time_limit: float) -> dict:
    """HiGHS options for a *certificate*: `mip_rel_gap=0.0` (trap 12), never the 1e-4 default."""
    opts = dict(mip_rel_gap=0.0, presolve=True, disp=False)
    if time_limit is not None and time_limit > 0:
        opts["time_limit"] = float(time_limit)
    return opts


def _interpret(res) -> dict:
    """The engine's raw stop reason, kept apart from our reading of it (trap 15).

    `proved` is set from `res.status` alone -- the code never consults the human-facing
    `status` string, so a mis-worded interpretation cannot turn into a false certificate.
    """
    raw = int(getattr(res, "status", -1))
    name = {0: "optimal", 1: "iteration_or_time_limit", 2: "infeasible",
            3: "unbounded", 4: "other"}.get(raw, "unknown")
    return dict(solver_status=raw, solver_status_name=name,
                solver_message=str(getattr(res, "message", "")),
                proved=(raw == 0),
                status="proved_optimal" if raw == 0 else f"not_proved ({name})")


def _lpt(M: np.ndarray, k: int):
    """Longest-processing-time greedy: heaviest zip first, always into the lightest district.

    The classical multiway-number-partitioning heuristic, here purely as a **constructive
    primal**: whatever it returns is a real partition, so its max-deviation is an upper bound on
    `t*` that needs no solver and no proof beyond arithmetic.
    """
    order = np.argsort(-M)
    lab = np.empty(M.size, int)
    mass = np.zeros(k)
    for z in order:
        j = int(np.argmin(mass))
        lab[z] = j
        mass[j] += M[z]
    return lab, mass


def _polish_partition(M: np.ndarray, k: int, lab: np.ndarray, mass: np.ndarray,
                      target: float, iters: int = 200):
    """Steepest single-move / single-swap descent on the max-deviation.  Still constructive.

    Each round takes the heaviest and lightest districts and tries every move of one zip from
    the former to the latter, plus every swap between them, keeping the change that lowers the
    max-deviation most; it stops when nothing helps.  On the real instance this takes LPT's
    ~7e-5 relative deviation to ~2e-6 in a fraction of a second -- far below anything a
    geometric draw can reach, which is the point: it shows indivisibility is not what costs the
    draw its balance.
    """
    lab, mass = lab.copy(), mass.copy()
    for _ in range(int(iters)):
        cur = float(np.abs(mass - target).max())
        h, l = int(np.argmax(mass - target)), int(np.argmin(mass - target))
        if h == l:
            break
        best = None
        hi, lo = np.flatnonzero(lab == h), np.flatnonzero(lab == l)
        for z in hi:                                    # move z: h -> l
            v = float(max(abs(mass[h] - M[z] - target), abs(mass[l] + M[z] - target),
                          *(abs(mass[j] - target) for j in range(k) if j not in (h, l))))
            if v < cur - 1e-15 and (best is None or v < best[0]):
                best = (v, int(z), None)
        for z in hi:                                    # swap z (in h) with y (in l)
            for y in lo:
                dm = M[z] - M[y]
                if dm <= 0:
                    continue
                v = float(max(abs(mass[h] - dm - target), abs(mass[l] + dm - target),
                              *(abs(mass[j] - target) for j in range(k) if j not in (h, l))))
                if v < cur - 1e-15 and (best is None or v < best[0]):
                    best = (v, int(z), int(y))
        if best is None:
            break
        _, z, y = best
        if y is None:
            mass[h] -= M[z]; mass[l] += M[z]; lab[z] = l
        else:
            dm = M[z] - M[y]
            mass[h] -= dm; mass[l] += dm
            lab[z], lab[y] = l, h
    return lab, mass


def _placement_matrix(n: int, k: int, extra_cols: int = 0) -> sparse.coo_matrix:
    """`sum_j x_zj = 1` rows.  Variable (z, j) lives at `z*k + j`, matching `centers.assign`."""
    cols = np.arange(n * k)
    rows = np.repeat(np.arange(n), k)
    return sparse.coo_matrix((np.ones(n * k), (rows, cols)), shape=(n, n * k + extra_cols))


def _mass_matrix(w: np.ndarray, k: int, extra_cols: int = 0) -> sparse.coo_matrix:
    """`sum_z w_z x_zj` rows, one per district."""
    n = w.size
    cols = np.arange(n * k)
    rows = np.tile(np.arange(k), n)
    return sparse.coo_matrix((np.repeat(w, k), (rows, cols)), shape=(k, n * k + extra_cols))


# ------------------------------------------------------- 1. the analytic balance ceiling
def cert_balance_ceiling(M, labels, k: int = None) -> dict:
    """Jensen's bound on `sum_j log M_j`, and the draw's distance from it.  No solver.

    `log` is strictly concave, so for any k positive district masses summing to `T`

        sum_j log M_j  <=  k * log(T / k)

    with equality exactly when every `M_j = T/k`.  The sum `T` is partition-invariant (every
    zip lands in exactly one district), so the right-hand side depends on nothing but `T` and
    `k`: it bounds **every** partition of these zips into k parts, whatever geometry,
    contiguity or indivisibility would allow.  It is therefore a free dual bound on stage 1 --
    the same object `channel.allocate_districts` maximises across components, evaluated here at
    one draw.

    `gap_nats = ceiling - achieved` is in nats and scale-free: rescaling every `M_z` by a
    constant shifts both terms by `k log kappa` and leaves the gap alone.  `gap_rel` converts it
    to the equivalent proportional loss in the Nash *product*, `1 - exp(-gap_nats)`.

    An empty district makes `achieved` `-inf` and the gap infinite, which is the honest reading
    (`centers.metrics` and `model.objective` agree): a district with no opportunity is not a
    near-miss, it is a different, worse problem.
    """
    M = np.asarray(M, float)
    labels = np.asarray(labels, int)
    if k is None:
        k = int(labels.max()) + 1 if labels.size else 0
    k = int(k)
    if k <= 0:
        return dict(certificate="balance_ceiling", k=0, feasible=False,
                    reason="no districts")
    mass = _masses(M, labels, k)
    total = float(mass.sum())
    target = total / k
    empty = [int(j) for j in np.flatnonzero(mass <= 0)]
    achieved = float(np.log(mass).sum()) if not empty else -math.inf
    ceiling = k * math.log(target) if target > 0 else -math.inf
    gap = (ceiling - achieved) if math.isfinite(achieved) else math.inf
    return dict(
        certificate="balance_ceiling",
        method="analytic (Jensen; no solver)",
        k=k, n=int(labels.size), total=total, target=target,
        masses=[float(v) for v in mass],
        sizes=[int(v) for v in np.bincount(labels, minlength=k)],
        empty_districts=empty,
        achieved_nash=achieved,
        ceiling_nash=ceiling,
        gap_nats=gap,
        gap_rel=(1.0 - math.exp(-gap)) if math.isfinite(gap) else 1.0,
        min=float(mass.min()), max=float(mass.max()),
        spread_rel=float((mass.max() - mass.min()) / target) if target else 0.0,
        max_dev=float(np.abs(mass - target).max()),
        max_dev_rel=float(np.abs(mass - target).max() / target) if target else 0.0,
        proved=True,
        proves=("sum_j log M_j <= k log(sum M / k) for EVERY partition of these zips into k "
                "parts; the gap is this draw's distance from perfect balance"),
        does_not_prove=("nothing about compactness, contiguity, or whether the ceiling is "
                        "reachable at all -- zips are indivisible (see "
                        "cert_integer_balance_floor)"),
    )


# ------------------------------------------- 2. the indivisible-zip floor on max-deviation
def cert_integer_balance_floor(M, k: int, time_limit: float = DEFAULT_TIME_LIMIT,
                               warm_labels=None) -> dict:
    """`min over partitions of max_j |M_j - target|`, by MILP.  Geometry-free.

    The model, on `x_zj in {0,1}` and one continuous `t >= 0`::

        min  t
        s.t. sum_j x_zj = 1                       every zip in exactly one district
             sum_z M_z x_zj - t <= target         \\  |M_j - target| <= t
             sum_z M_z x_zj + t >= target         /

    Its optimum `t*` is the **best balance indivisible zips permit**, with no geometry, no
    contiguity and no centers: every real draw's `max_dev` is `>= t*`, so `t*` separates the
    heuristic's loss from the arithmetic's.  The ceiling of `cert_balance_ceiling` says how far
    the draw is from `t = 0`; this says how much of that distance was ever available.

    Symmetry, and why the dual side is hard
    ---------------------------------------
    The k district labels are interchangeable, so every solution has `k!` twins and
    branch-and-bound loses its pruning.  Two valid breaks are applied:

    * the **heaviest zip is fixed into district 0** (`x[z0,0] = 1`), a relabelling that costs
      nothing;
    * districts `1..k-1` are forced to **non-increasing mass**.  Valid because after fixing
      only `z0`, those `k-1` labels remain freely permutable, so every solution has a twin
      obeying the order.  `k-2` extra rows, which is as cheap as symmetry breaking gets.

    Even so the LP relaxation is worthless: split every zip fractionally and each district sits
    exactly on target, so the root bound is `t = 0` and the dual side must be earned node by
    node.  At `k = 2` over a handful of zips HiGHS closes it in milliseconds; at production size
    it does not close at all, and its own incumbents are poor -- measured at n = 1,223, k = 13:
    HiGHS' best after 300 s was a max-deviation of 1.69% of target, worse than the geometric
    draw it was meant to bound.

    The primal side therefore does not go through the MILP
    ------------------------------------------------------
    A primal bound needs no proof beyond arithmetic: **any** partition someone constructs is an
    upper bound on `t*`.  So the certificate constructs one directly -- LPT (heaviest zip first,
    into the lightest district) followed by a steepest move/swap descent, `_lpt` and
    `_polish_partition`, both a fraction of a second -- and reports the better of that and
    whatever HiGHS found.  On the real instance this lands at ~2e-6 of target against HiGHS'
    1.7e-2, and it is exactly as rigorous: the partition is returned in `labels` and its masses
    are recomputed from it.  The greedy value is also imposed as an upper bound on the MILP's
    `t` variable, which cuts nothing off (a solution that good exists) and shrinks the tree.

    Measured, so that nobody has to re-discover it: at n = 1,223 and k = 13 the capped MILP
    explored **0 nodes and returned no incumbent in 300 s** -- with `t` capped at 2e-6 of target
    the model is a near-exact number-partitioning feasibility problem, and HiGHS never got out
    of the root.  At that size the certificate's entire content is therefore the constructive
    primal plus the trivial `t* >= 0`, and it is reported as such (`t_source`,
    `solver_status_name`, `nodes`).  That is not a disappointment: `t* <= 2.03e-6` against a
    draw at 4.00e-3 already settles the question the certificate exists to answer -- the draw's
    imbalance is ~2,000x the indivisibility floor, so it is the price of *geometry*, and closing
    the dual side to the last digit would change nothing about that reading.

    What comes back is a **bound pair**: `t_rel` (primal -- balance this good is provably
    *reachable*, geometry ignored) and `t_rel_lower` (dual -- no partition beats it).  `proved`
    is True only when the engine returned status 0 *and* did not disagree with the constructed
    primal.  For judging a draw the primal half is the operative one: it is what says whether
    the draw's imbalance is arithmetic or geometry.

    `time_limit <= 0` skips the MILP and reports the constructed primal alone -- still a valid
    upper bound on `t*`, and labelled as such rather than as a certificate of `t*`.
    `warm_labels` is used only to report the reference draw's own `max_dev` alongside; HiGHS
    through `scipy.optimize.milp` takes no warm start.
    """
    M = np.asarray(M, float)
    n, k = M.size, int(k)
    out = dict(certificate="integer_balance_floor",
               method="MILP (min max-deviation, geometry-free), HiGHS via scipy.optimize.milp",
               n=int(n), k=k, mip_rel_gap=0.0, time_limit=float(time_limit))
    if k < 1 or n < k:
        out.update(proved=False, status="not_attempted (k out of range)",
                   reason=f"need 1 <= k <= n; got k={k}, n={n}")
        return out

    total = float(M.sum())
    target = total / k
    out.update(total=total, target=target)
    if warm_labels is not None:
        ref = _masses(M, warm_labels, k)
        out["reference_max_dev"] = float(np.abs(ref - target).max())
        out["reference_max_dev_rel"] = float(np.abs(ref - target).max() / target)

    if k == 1:
        out.update(proved=True, status="proved_optimal", t=0.0, t_rel=0.0,
                   t_lower=0.0, t_rel_lower=0.0, t_source="trivial", solver_status=0,
                   solver_status_name="trivial", solver_message="k == 1: one district",
                   labels=[0] * n, masses=[total], t_seconds=0.0)
        out["proves"] = "with one district the deviation is 0 by definition"
        return out

    # the constructive primal: a real partition, so a rigorous upper bound on t* with no solver
    t_g0 = time.perf_counter()
    g_lab, g_mass = _lpt(M, k)
    out["t_lpt"] = float(np.abs(g_mass - target).max())
    g_lab, g_mass = _polish_partition(M, k, g_lab, g_mass, target)
    g_mass = _masses(M, g_lab, k)                    # recomputed, never carried incrementally
    t_greedy = float(np.abs(g_mass - target).max())
    out.update(t_greedy=t_greedy, t_greedy_rel=t_greedy / target,
               t_lpt_rel=out["t_lpt"] / target,
               t_greedy_seconds=float(time.perf_counter() - t_g0))

    if time_limit is not None and time_limit <= 0:
        out.update(proved=False, status="not_attempted (time_limit <= 0)",
                   solver_status=None, solver_status_name="not_run", solver_message="",
                   t=t_greedy, t_rel=t_greedy / target, t_source="greedy_lpt_polish",
                   labels=g_lab.tolist(), masses=[float(v) for v in g_mass],
                   t_lower=0.0, t_rel_lower=0.0)
        out["proves"] = ("only the constructed partition: t* <= t.  The MILP was not run, so "
                         "nothing bounds t* from below beyond the trivial t* >= 0")
        return out

    # conditioning: masses descaled by their mean, exactly as centers.assign descales its LP.
    # Scaling a row and its right-hand side together leaves the feasible set identical.
    scale = float(M.mean())
    w = M / scale
    tw = float(w.sum()) / k

    nv = n * k + 1                                   # ... + the max-deviation variable t
    A_place = _placement_matrix(n, k, extra_cols=1)
    A_mass = _mass_matrix(w, k, extra_cols=1)
    # |M_j - target| <= t, as two one-sided families
    e = sparse.coo_matrix((np.ones(k), (np.arange(k), np.full(k, n * k))), shape=(k, nv))
    A_up = (A_mass - e).tocsc()                      # sum_z w x_zj - t <= tw
    A_lo = (A_mass + e).tocsc()                      # sum_z w x_zj + t >= tw

    cons = [LinearConstraint(A_place.tocsc(), 1.0, 1.0),
            LinearConstraint(A_up, -np.inf, tw),
            LinearConstraint(A_lo, tw, np.inf)]

    # symmetry break 2: districts 1..k-1 in non-increasing mass
    if k >= 3:
        base = np.arange(n) * k
        rows, cols, vals = [], [], []
        for r, j in enumerate(range(1, k - 1)):
            rows.append(np.full(2 * n, r))
            cols.append(np.concatenate([base + j, base + j + 1]))
            vals.append(np.concatenate([w, -w]))
        A_ord = sparse.coo_matrix((np.concatenate(vals),
                                   (np.concatenate(rows), np.concatenate(cols))),
                                  shape=(k - 2, nv)).tocsc()
        cons.append(LinearConstraint(A_ord, 0.0, np.inf))

    lb = np.zeros(nv)
    ub = np.ones(nv)
    # t is continuous, and capped at the constructed primal: a partition that good exists, so
    # the cap removes no solution that could be optimal, and it shrinks the tree
    ub[n * k] = (t_greedy / scale) * (1.0 + 1e-9) + 1e-12
    z0 = int(np.argmax(M))                           # symmetry break 1: heaviest zip -> 0
    lb[z0 * k] = 1.0
    ub[z0 * k + 1:z0 * k + k] = 0.0
    integrality = np.ones(nv)
    integrality[n * k] = 0                           # t is continuous

    c = np.zeros(nv)
    c[n * k] = 1.0

    t0 = time.perf_counter()
    res = milp(c, integrality=integrality, bounds=Bounds(lb, ub), constraints=cons,
               options=_milp_options(time_limit))
    elapsed = time.perf_counter() - t0
    out.update(_interpret(res))
    out["t_seconds"] = float(elapsed)

    # the primal is whichever real partition is better -- the engine's incumbent or the
    # constructed one.  Both are recomputed from their integer labels; res.fun is never trusted.
    best_t, best_lab, best_mass, src = t_greedy, g_lab, g_mass, "greedy_lpt_polish"
    x = getattr(res, "x", None)
    if x is not None:
        lab = np.asarray(x[:n * k], float).reshape(n, k).argmax(axis=1).astype(int)
        mass = _masses(M, lab, k)
        t_milp = float(np.abs(mass - target).max())
        out.update(t_milp=t_milp, t_milp_rel=t_milp / target,
                   solver_t=float(x[n * k]) * scale)   # what the engine thinks, for comparison
        if t_milp < best_t:
            best_t, best_lab, best_mass, src = t_milp, lab, mass, "milp"
    else:
        out["t_milp"] = out["t_milp_rel"] = None
    out.update(t=best_t, t_rel=best_t / target, t_source=src,
               labels=np.asarray(best_lab, int).tolist(),
               masses=[float(v) for v in best_mass])

    dual = getattr(res, "mip_dual_bound", None)
    if dual is not None and np.isfinite(dual):
        out["t_lower"] = float(max(dual, 0.0)) * scale
        out["t_rel_lower"] = out["t_lower"] / target
    else:
        out["t_lower"] = 0.0
        out["t_rel_lower"] = 0.0
    out["mip_gap_reported"] = (float(res.mip_gap)
                               if getattr(res, "mip_gap", None) is not None else None)
    out["nodes"] = int(getattr(res, "mip_node_count", 0) or 0)

    # a "proved optimal" that the constructed partition beats is a tolerance artefact, not a
    # certificate: downgrade rather than publish the contradiction (traps 12 and 15)
    if out["proved"] and out.get("t_milp") is not None and best_t < out["t_milp"] - 1e-12:
        out["proved"] = False
        out["status"] = ("not_proved (engine claimed optimal at t_milp but the constructed "
                         "partition is strictly better -- treated as a tolerance artefact)")
    if out["proved"]:
        out["t_lower"] = out["t"]
        out["t_rel_lower"] = out["t_rel"]
        out["proves"] = ("t* is exactly the smallest max-deviation ANY partition of these zips "
                         "into k districts can achieve, geometry ignored")
    else:
        out["proves"] = ("bound pair only: a partition achieving t was constructed (so balance "
                         "that good is reachable), and no partition beats t_lower; the true t* "
                         "lies in [t_lower, t]")
    out["does_not_prove"] = ("nothing geometric -- the optimal partition here is generally "
                             "scattered and would make a nonsensical territory map")
    return out


# ----------------------------------------- 3. optimal assignment with the centers PINNED
def cert_assignment_at_centers(xy, M, labels, centers, slack=None,
                               time_limit: float = DEFAULT_TIME_LIMIT) -> dict:
    """With the draw's centers fixed, is a strictly more compact integer assignment available?

    The model, on `x_zj in {0,1}` and the draw's own centers `c_j`::

        min  sum_z sum_j M_z d^2(z, c_j) x_zj
        s.t. sum_j x_zj = 1
             |sum_z M_z x_zj - target| <= delta

    with `delta` defaulting to the draw's **own** max deviation, so the draw is feasible for
    its own test and `opt_cost <= draw_cost` always holds.  Pass `slack` (absolute, in the units
    of `M`) to ask the question at a different balance.

    Why this one is cheap where certificate 2 is not: the centers are given, so there is no
    label symmetry at all -- district `j` is the one at `c_j`.  What is left is a transportation
    problem with two side bounds per district, whose LP relaxation is nearly integral (a basic
    solution splits at most a handful of zips), so the root bound is tight and HiGHS closes it
    in seconds.

    Returned: `draw_cost`, `opt_cost`, `rel_gap = (draw_cost - opt_cost)/draw_cost`, and
    `improving_labels` **only when the MILP strictly beat the draw** -- in which case the draw
    was demonstrably not optimal even at its own centers.  Costs are recomputed from the integer
    labels in the caller's units, not read off `res.fun`.

    What the improvement optimises, and what it does not
    ----------------------------------------------------
    The constraint is a **max-deviation band**, not the stage-1 Nash objective, so a "cheaper"
    assignment is cheaper in compactness only: it may sit anywhere inside the band, and
    `sum_j log M_j` can come out slightly *lower* than the draw's even though `max_dev` does
    not.  Measured on the real draw: `-8.53%` moment of inertia for `-4.7e-5` nats of Nash and a
    spread of 0.64% -> 0.80% at an unchanged max-deviation of 0.400%.  Both `draw_nash` and
    `opt_nash` are returned so the trade is visible rather than implied; if the Nash objective
    is what must not regress, re-run with a tighter `slack`.

    Conditional, and only conditionally: this proves optimality of the *assignment given the
    centers*.  The centers came out of a heuristic (`centers.draw`'s Lloyd loop) and are not
    certified by anything here -- exactly the limitation a k-means "optimal assignment step"
    has.  A zero gap means the draw cannot be improved by moving zips between the districts it
    has; it does not mean the districts are the right ones.
    """
    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    labels = np.asarray(labels, int)
    C = np.asarray(centers, float)
    n, k = xy.shape[0], C.shape[0]
    out = dict(certificate="assignment_at_centers",
               method="MILP (min weighted moment of inertia at pinned centers), HiGHS",
               n=int(n), k=int(k), mip_rel_gap=0.0, time_limit=float(time_limit),
               centers_pinned=True)

    d2 = ((xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)      # (n, k)
    cost = M[:, None] * d2                                        # raw units
    draw_cost = float(cost[np.arange(n), labels].sum())
    total = float(M.sum())
    target = total / k
    mass_draw = _masses(M, labels, k)
    delta = float(np.abs(mass_draw - target).max()) if slack is None else float(slack)
    out.update(total=total, target=target, draw_cost=draw_cost,
               draw_max_dev=float(np.abs(mass_draw - target).max()),
               draw_max_dev_rel=float(np.abs(mass_draw - target).max() / target),
               draw_nash=(float(np.log(mass_draw).sum()) if (mass_draw > 0).all()
                          else -math.inf),
               slack=delta, slack_rel=delta / target if target else 0.0,
               slack_is_default=slack is None)

    if time_limit is not None and time_limit <= 0:
        out.update(proved=False, status="not_attempted (time_limit <= 0)",
                   solver_status=None, solver_status_name="not_run", solver_message="",
                   opt_cost=None, rel_gap=None, improving_labels=None)
        out["proves"] = "nothing -- the solve was not attempted"
        return out

    # conditioning (see the module docstring): mass column by its mean, objective by its mean
    mscale = float(M.mean())
    w = M / mscale
    tw = float(w.sum()) / k
    dw = delta / mscale
    cscale = float(cost.mean())
    c = (cost / (cscale if cscale > 0 else 1.0)).ravel()

    tol = FEAS_TOL * max(tw, 1.0)
    cons = [LinearConstraint(_placement_matrix(n, k).tocsc(), 1.0, 1.0),
            LinearConstraint(_mass_matrix(w, k).tocsc(), tw - dw - tol, tw + dw + tol)]

    t0 = time.perf_counter()
    res = milp(c, integrality=np.ones(n * k), bounds=Bounds(0.0, 1.0), constraints=cons,
               options=_milp_options(time_limit))
    elapsed = time.perf_counter() - t0
    out.update(_interpret(res))
    out["t_seconds"] = float(elapsed)
    out["nodes"] = int(getattr(res, "mip_node_count", 0) or 0)

    x = getattr(res, "x", None)
    if x is None:
        out.update(opt_cost=None, rel_gap=None, improving_labels=None)
        out["proves"] = "nothing -- the solver returned no assignment"
        return out

    lab = np.asarray(x, float).reshape(n, k).argmax(axis=1).astype(int)
    opt_cost = float(cost[np.arange(n), lab].sum())   # recomputed in raw units
    mass_opt = _masses(M, lab, k)
    feasible = bool(np.abs(mass_opt - target).max() <= delta + 1e-6 * max(target, 1.0))
    out.update(opt_cost=opt_cost,
               opt_max_dev=float(np.abs(mass_opt - target).max()),
               opt_max_dev_rel=float(np.abs(mass_opt - target).max() / target),
               opt_masses=[float(v) for v in mass_opt],
               opt_nash=(float(np.log(mass_opt).sum()) if (mass_opt > 0).all() else -math.inf),
               opt_labels_respect_slack=feasible,
               solver_obj=float(res.fun) * (cscale if cscale > 0 else 1.0),
               rel_gap=float((draw_cost - opt_cost) / draw_cost) if draw_cost > 0 else 0.0)
    out["nash_delta"] = out["opt_nash"] - out["draw_nash"]

    dual = getattr(res, "mip_dual_bound", None)
    if dual is not None and np.isfinite(dual):
        out["cost_lower_bound"] = float(dual) * (cscale if cscale > 0 else 1.0)
        out["rel_gap_upper"] = (float((draw_cost - out["cost_lower_bound"]) / draw_cost)
                                if draw_cost > 0 else 0.0)

    improved = opt_cost < draw_cost * (1.0 - COST_TOL) and feasible
    out["improved"] = bool(improved)
    out["n_relabelled"] = int((lab != labels).sum())
    out["improving_labels"] = lab.tolist() if improved else None
    if improved:
        out["proves"] = ("the draw is NOT assignment-optimal at its own centers: a strictly "
                         "cheaper assignment exists at balance no worse than the draw's")
    elif out["proved"]:
        out["proves"] = ("no integer assignment to THESE centers, at max-deviation <= slack, "
                         "is more compact than the draw -- the assignment step is optimal "
                         "given the centers")
    else:
        out["proves"] = ("bound pair only: no assignment at these centers costs less than "
                         "cost_lower_bound, and the draw was not beaten within the time limit")
    out["does_not_prove"] = ("nothing about the centers themselves -- they came from a "
                             "heuristic (k-means-style Lloyd rounds) and joint optimality over "
                             "centers AND assignment is NOT claimed; and the objective here is "
                             "compactness inside a max-deviation band, so an 'improvement' can "
                             "carry a small loss in sum_j log M_j (see nash_delta)")
    return out


# --------------------------------- 4. the power-diagram dual bound at the SAME pinned centers
def cert_power_diagram(xy, M, labels, centers, targets=None) -> dict:
    """The transportation duals as a solver-free lower bound, and the territory they draw.

    Certificate 3 asks the compactness question with a MILP.  This one asks it with **one LP
    and a page of arithmetic**, and answers more.  The balanced assignment at fixed centers is
    a transportation problem; its dual feasibility `alpha_z + M_z beta_j <= M_z d^2(z, c_j)`
    says an optimal assignment sends each zip to a district minimising `d^2(z, c_j) - beta_j`.
    So two things fall out of the same solve:

    * `lp_bound = sum_z alpha_z + sum_j m_j beta_j` is a valid lower bound on the compactness
      cost of **every** assignment meeting `targets` -- fractional and integer alike, since an
      integer assignment is LP-feasible.  Checking it needs no solver and no trust in one: the
      returned `alpha`, `beta` are verified against all `n*k` dual constraints here
      (`max_dual_violation`), and a reader can redo that in `O(nk)` arithmetic.
    * `weights = beta` (rescaled to squared distance) are the weights of the **power diagram**
      of the centers, which is the optimal territory as a partition of the plane: `k` convex
      cells with straight borders.  That is the map, and it is exact rather than a rendering
      choice.

    Which masses to ask about, and the trap in the other choice
    -----------------------------------------------------------
    `targets` defaults to the **draw's own realised masses**, not to the equal split, and that
    default is load-bearing.  A bound is only comparable to an incumbent the bound's own
    feasible set contains: at exactly-equal targets a draw whose max-deviation is 0.4% of
    target is *infeasible*, `lp_bound` can legitimately exceed `draw_cost`, and `rel_gap` comes
    out **negative** -- not a certificate of anything.  (Measured on the six-point fixture:
    `rel_gap = -76.9` for a 4-2 draw asked about at 3-3.)  At the draw's own masses the draw is
    feasible by construction, so `lp_bound <= draw_cost` always holds and the gap is a true
    suboptimality gap: it isolates *where the zips are* from *how big the districts are*, which
    is exactly the question a territory map asks.  `draw_meets_targets` reports which case a
    caller-supplied `targets` landed in, and `rel_gap` is `None` when it is False.

    This is also where certificate 3 differs, and legitimately: it constrains balance by a
    **max-deviation band**, a strictly larger feasible set than any equality rows, so its
    optimum can sit below the bound here without either being wrong.

    `n_outside_cell` is the sharpest single number: how many of the draw's zips sit in another
    district's power cell.  Zero would mean the draw *is* a power diagram and is therefore
    compactness-optimal at its centers.  A large count means the draw traded compactness for
    something -- here, for balance, in `centers.improve`'s Nash polish -- and that trade is the
    open lexicographic decision, not a bug.

    Not proved, same scope as certificate 3: nothing about the centers.  The bound is
    conditional on `centers` exactly as a k-means assignment step is.
    """
    from . import centers as _centers                       # a pure-numpy sibling; no cycle

    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    labels = np.asarray(labels, int)
    C = np.asarray(centers, float)
    n, k = xy.shape[0], C.shape[0]

    d2 = ((xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    cost = M[:, None] * d2
    draw_cost = float(cost[np.arange(n), labels].sum())
    mass_draw = _masses(M, labels, k)
    target = float(M.sum()) / k

    own = targets is None
    res = _centers.power_weights(xy, M, C, targets=mass_draw if own else targets)
    cell = np.asarray(res["labels"], int)
    mass_cell = _masses(M, cell, k)
    # the incumbent has to be inside the bound's own feasible set for the gap to mean anything
    t = np.asarray(res["targets"], float)
    dev = float(np.abs(mass_draw - t).max())
    meets = bool(own or dev <= FEAS_TOL * max(float(M.sum()), 1.0))

    out = dict(certificate="power_diagram_duals",
               method="transportation LP duals (HiGHS), verified by O(nk) arithmetic",
               n=int(n), k=int(k), centers_pinned=True,
               targets_are_draw_masses=bool(own),
               draw_meets_targets=meets,
               draw_target_max_dev=dev,
               weights=[float(v) for v in res["weights"]],
               targets=[float(v) for v in res["targets"]],
               alpha_sum=float(np.sum(res["alpha"])),
               beta=[float(v) for v in res["beta"]],
               n_fractional=int(res["n_fractional"]),
               max_dual_violation=float(res["max_dual_violation"]),
               max_dual_violation_rel=float(res["max_dual_violation_rel"]),
               max_cs_residual_rel=float(res["max_cs_residual_rel"]),
               lp_bound=float(res["lp_bound"]),
               draw_cost=draw_cost,
               rel_gap=((float((draw_cost - res["lp_bound"]) / draw_cost) if draw_cost > 0
                         else 0.0) if meets else None),
               cell_cost=float(cost[np.arange(n), cell].sum()),
               n_outside_cell=int((cell != labels).sum()),
               outside_cell_share=float((cell != labels).mean()) if n else 0.0,
               cell_masses=[float(v) for v in mass_cell],
               cell_max_dev_rel=float(np.abs(mass_cell - target).max() / target) if target else 0.0,
               draw_max_dev_rel=float(np.abs(mass_draw - target).max() / target) if target else 0.0,
               )
    # the dual vector is only a bound if it is dual-feasible; say so from the residual, not
    # from the solver's word for it
    out["proved"] = bool(abs(res["max_dual_violation_rel"]) <= DUAL_TOL)
    out["status"] = "optimal" if out["proved"] else "dual vector failed its own feasibility check"
    out["is_power_diagram"] = bool(out["n_outside_cell"] == 0)
    if not out["proved"]:
        out["proves"] = "nothing -- the returned duals are not feasible to the stated tolerance"
    elif not meets:
        out["proves"] = ("the lower bound only, and NOT a gap: the draw's own masses miss the "
                         "supplied targets by " + f"{dev:.6g}" + ", so it is not in the feasible "
                         "set the bound covers and lp_bound may exceed draw_cost. Re-run with "
                         "targets=None to ask the question at the draw's own masses")
    elif out["is_power_diagram"]:
        out["proves"] = ("the draw IS the power diagram of its centers with these weights, and "
                         "therefore the most compact assignment meeting the mass targets")
    else:
        out["proves"] = ("no assignment of these zips to these centers meeting the mass targets "
                         "costs less than lp_bound -- a bound checkable in O(nk) arithmetic from "
                         "alpha and beta, with no solver in the trusted path")
    out["does_not_prove"] = ("nothing about the centers, which are the heuristic's; and nothing "
                             "about the stage-1 Nash objective, which this LP does not see -- "
                             "the zips outside their cell are where the draw bought balance "
                             "with compactness")
    return out


# --------------------------------------------------------------------------- the report
def certify(xy, M, labels, centers, k: int = None, *,
            time_limit: float = DEFAULT_TIME_LIMIT,
            floor_time_limit: float = None, slack=None) -> dict:
    """Run all three certificates on one draw and merge them into a single report.

    `summary` is a list of plain sentences, each stating what IS and what IS NOT proved, in the
    order the certificates strengthen: the analytic ceiling bounds every partition; the integer
    floor says how much of the gap to that ceiling was ever available; the pinned-center
    assignment says whether the geometry of *this* draw was solved optimally given its centers.

    Nothing here certifies the centers.  That is stated in the summary every time, because it is
    the one thing a reader is most likely to assume and the one thing least true.
    """
    labels = np.asarray(labels, int)
    if k is None:
        k = int(np.asarray(centers).shape[0])
    k = int(k)
    if floor_time_limit is None:
        floor_time_limit = time_limit

    ceil_ = cert_balance_ceiling(M, labels, k)
    floor = cert_integer_balance_floor(M, k, time_limit=floor_time_limit, warm_labels=labels)
    assign = cert_assignment_at_centers(xy, M, labels, centers, slack=slack,
                                        time_limit=time_limit)
    power = cert_power_diagram(xy, M, labels, centers)

    s = []
    s.append(
        f"BALANCE CEILING (analytic, always valid): the draw scores {ceil_['achieved_nash']:.6f} "
        f"nats against a ceiling of {ceil_['ceiling_nash']:.6f}, a gap of {ceil_['gap_nats']:.3e} "
        f"nats ({ceil_['gap_rel']:.3%} of the Nash product). PROVED: no partition of these zips "
        f"into {k} districts scores above the ceiling. NOT PROVED: that the ceiling is reachable "
        f"-- zips are indivisible.")
    if floor.get("proved"):
        s.append(
            f"INTEGER BALANCE FLOOR (exact): the best max-deviation ANY partition can reach is "
            f"t* = {floor['t_rel']:.3%} of target, against the draw's "
            f"{ceil_['max_dev_rel']:.3%}. PROVED: t* is optimal for the indivisible-zip problem "
            f"with geometry ignored. NOT PROVED: that a territory map can reach t* -- the "
            f"optimal partition here is geometrically arbitrary.")
    elif floor.get("t_rel") is not None:
        s.append(
            f"INTEGER BALANCE FLOOR (bound pair, {floor['status']}): a partition with "
            f"max-deviation {floor['t_rel']:.4%} of target was constructed "
            f"(source: {floor['t_source']}) and no partition beats {floor['t_rel_lower']:.4%}; "
            f"the draw sits at {ceil_['max_dev_rel']:.4%}, i.e. "
            f"{ceil_['max_dev_rel'] / floor['t_rel']:.0f}x the constructed primal, so the "
            f"draw's imbalance is the price of geometry and not of indivisibility. PROVED: "
            f"balance of {floor['t_rel']:.4%} is reachable, and t* >= "
            f"{floor['t_rel_lower']:.4%}. NOT PROVED: the exact value of t* -- the k! label "
            f"symmetry leaves the dual side open."
            if floor["t_rel"] > 0 else
            f"INTEGER BALANCE FLOOR (bound pair, {floor['status']}): an exactly balanced "
            f"partition was constructed (source: {floor['t_source']}), so t* = 0; the draw "
            f"sits at {ceil_['max_dev_rel']:.4%}. PROVED: perfect balance is reachable with "
            f"geometry ignored. NOT PROVED: anything geometric.")
    else:
        s.append(
            f"INTEGER BALANCE FLOOR: {floor['status']}. PROVED: nothing. The draw's own "
            f"max-deviation is {ceil_['max_dev_rel']:.3%} of target and stands unchallenged.")
    if assign.get("improved"):
        s.append(
            f"ASSIGNMENT AT PINNED CENTERS: the draw is NOT optimal -- a reassignment of "
            f"{assign['n_relabelled']} zip(s) cuts the weighted moment of inertia by "
            f"{assign['rel_gap']:.3%} at balance no worse than the draw's "
            f"({assign['slack_rel']:.3%} of target), for {assign['nash_delta']:+.2e} nats of "
            f"Nash. PROVED: an improvement in compactness exists (it is returned as "
            f"improving_labels). NOT PROVED: that the improved map is jointly optimal -- the "
            f"centers are still the heuristic's -- nor that it is better on the stage-1 "
            f"objective, which a max-deviation band does not control.")
    elif assign.get("proved"):
        s.append(
            f"ASSIGNMENT AT PINNED CENTERS: optimal. PROVED: no integer assignment to these "
            f"centers with max-deviation <= {assign['slack_rel']:.3%} of target is more compact "
            f"than the draw (gap {assign['rel_gap']:.3e}). NOT PROVED: that the centers are the "
            f"right ones -- center choice is heuristic, exactly as in k-means, and global joint "
            f"optimality over centers AND assignment is NOT claimed.")
    else:
        s.append(
            f"ASSIGNMENT AT PINNED CENTERS: {assign['status']}. PROVED: at most a bound pair; "
            f"read cost_lower_bound, not a claim of optimality.")
    if not power.get("proved"):
        s.append(
            f"POWER-DIAGRAM DUALS: {power['status']}. PROVED: nothing -- the dual vector did "
            f"not pass its own feasibility check, so the bound is not claimed.")
    elif power.get("is_power_diagram"):
        s.append(
            f"POWER-DIAGRAM DUALS (exact, solver-free to check): every zip lies in its own "
            f"district's power cell, so the draw IS the power diagram of its centers with "
            f"weights {['%.3g' % w for w in power['weights']]}. PROVED: no assignment to these "
            f"centers at these masses is more compact. NOT PROVED: anything about the centers.")
    else:
        s.append(
            f"POWER-DIAGRAM DUALS (exact, solver-free to check): at the draw's own district "
            f"masses -- so the draw is feasible for its own test and the gap is a real one -- "
            f"the transportation duals bound the compactness cost of every assignment to these "
            f"centers from below by {power['lp_bound']:.6g}; the draw sits "
            f"{power['rel_gap']:.3%} above it, and {power['n_outside_cell']} of {power['n']} "
            f"zips ({power['outside_cell_share']:.1%}) lie outside their own district's power "
            f"cell -- so the draw is NOT a power diagram, which is exactly where it bought "
            f"balance with compactness. PROVED: the lower bound, verifiable in O(nk) arithmetic "
            f"from alpha and beta with no solver in the trusted path (max dual violation "
            f"{power['max_dual_violation_rel']:.1e} relative). NOT PROVED: that a *better* map "
            f"exists on the stage-1 objective -- this LP does not see sum_j log M_j, and the "
            f"cells' own spread is {power['cell_max_dev_rel']:.2%} of target against the "
            f"draw's {power['draw_max_dev_rel']:.2%}.")
    s.append(
        "SCOPE: all four certificates are conditional on the zip set and weights handed in. "
        "Center placement is heuristic and is NOT certified; contiguity is not modelled at all "
        "(the sold-zip adjacency of the real instance is shattered, so compactness stands in "
        "for it); and stage 2 (staffing) is a separate exact problem, untouched here.")

    return dict(
        k=k, n=int(labels.size),
        balance_ceiling=ceil_,
        integer_balance_floor=floor,
        assignment_at_centers=assign,
        power_diagram=power,
        proved_all=bool(ceil_.get("proved") and floor.get("proved") and assign.get("proved")
                        and power.get("proved")),
        summary=s,
    )
