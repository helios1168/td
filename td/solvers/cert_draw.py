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
  solution, which is exactly what branch-and-bound cannot prune.  Two cheap breaks are applied
  **on an un-anchored instance only**: the heaviest zip is fixed into district 0, and districts
  `1..k-1` are constrained to non-increasing mass (valid, since after fixing that one zip those
  labels are still freely interchangeable).  Both assume that symmetry, and a pin destroys it --
  see "Anchored draws" below.  At tiny `k` this closes instantly; at `k = 13` over 1,223 zips the
  *dual* side still crawls -- the LP relaxation is `t = 0` (split the zips fractionally and
  every district is exactly on target), so the root bound is vacuous and the tree has to work
  for every nat of it.  That is reported honestly as a bound pair, and the primal side is the
  useful half regardless: a feasible `t` is a **constructive proof that balance that good is
  reachable**, which is what bounds the heuristic's loss.

Anchored draws
--------------
`centers.draw(locked=)` pins some zips to districts, and the pin-cost catalogue in
`docs/RUNS.md` is built on such draws.  Every certificate here takes the same optional `locked`
(`-1` for a free zip, else its district); `None`, or an array with no entry `>= 0`, reproduces
the un-anchored answer bit-for-bit.  Passing it is not cosmetic -- each certificate is wrong,
vacuous, or answering a different question without it, and each failure was exhibited before it
was fixed (`tests/test_cert_draw.py`, the ANCHORED section):

1. `cert_balance_ceiling` stays **true** but stops being reachable.  The honest ceiling is the
   constrained Jensen problem over the free mass, whose exact maximiser is `residual_targets`'
   water-fill -- proved in the docstring, not assumed.  Un-told, it billed an anchored-*optimal*
   draw 0.288 nats.
2. `cert_integer_balance_floor` searched over partitions that move pinned zips: it reported a
   floor of 0.5 where nothing lock-respecting beats 3.5, and offered a partition violating the
   pins as its constructive proof.  Both inherited symmetry breaks are unsound once pins exist;
   one is dropped and one is restricted (its docstring gives the measured counterexamples).
3. `cert_assignment_at_centers` "improved" a pinned draw by undoing the pin.  Now the pins are
   variable bounds, the analogue of `centers.improve(movable=)`.
4. `cert_power_diagram` condemned an anchored-optimal draw at a 16.5% gap, because a pinned zip
   cannot be expected to lie in its own cell.  The duals are now taken on the **free**
   subproblem and the pinned cost added back as the constant it is.

Certificates 3 and 4 also refuse labels that contradict `locked`: a certificate about an
anchored draw is only about it if the draw honours the pins.

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


def _anchor_state(M, k: int, locked) -> dict:
    """Locked mass per district, and the per-district targets that are left over.

    `locked` uses `centers.draw(locked=)`'s encoding: `-1` for a free zip, else the district it
    is pinned to.  `None`, or an array with no entry `>= 0`, is the un-anchored case and every
    field below collapses to it -- `locked_mass` all zero and `targets` the equal split -- so
    each certificate can be written once and take the old path bit-for-bit.

    `targets` is `locked_mass + residual_targets(...)`, the **water-fill**: see
    `cert_balance_ceiling` for the proof that this is not a convention but the solution of the
    anchored Jensen problem.
    """
    from .centers import residual_targets                  # a pure-numpy sibling; no cycle

    M = np.asarray(M, float)
    n = M.size
    if locked is None:
        lock = np.full(n, -1, int)
    else:
        lock = np.asarray(locked, int)
        if lock.shape != (n,):
            raise ValueError(f"locked must have shape ({n},); got {lock.shape}")
        if lock.size and int(lock.max()) >= k:
            raise ValueError(f"locked references district {int(lock.max())} but k={k}")
    is_locked = lock >= 0
    total = float(M.sum())
    locked_mass = np.bincount(lock[is_locked], weights=M[is_locked], minlength=k).astype(float)
    residual = residual_targets(total, locked_mass, k)
    return dict(locked=lock, is_locked=is_locked, free=~is_locked, total=total,
                locked_mass=locked_mass, residual=residual, targets=locked_mass + residual,
                anchored=bool(is_locked.any()), supplied=locked is not None)


def _check_labels_match_locks(labels, st: dict) -> None:
    """A certificate about an anchored draw is only about it if the draw honours the pins."""
    m = st["is_locked"]
    if not m.any():
        return
    lab = np.asarray(labels, int)
    bad = int((lab[m] != st["locked"][m]).sum())
    if bad:
        raise ValueError(f"{bad} labelled zip(s) contradict `locked`; these labels are not the "
                         f"anchored draw those pins describe")


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


def _lpt(M: np.ndarray, k: int, targets=None):
    """Longest-processing-time greedy: heaviest zip first, always into the lightest district.

    The classical multiway-number-partitioning heuristic, here purely as a **constructive
    primal**: whatever it returns is a real partition, so its max-deviation is an upper bound on
    `t*` that needs no solver and no proof beyond arithmetic.

    `targets` (one per district) generalises "lightest" to "furthest below its own target",
    which is what an anchored instance needs: a saturated anchor has a target of 0 and must be
    passed over.  `None` keeps the equal-target arithmetic literally unchanged.
    """
    order = np.argsort(-M)
    lab = np.empty(M.size, int)
    mass = np.zeros(k)
    if targets is None:
        for z in order:
            j = int(np.argmin(mass))
            lab[z] = j
            mass[j] += M[z]
        return lab, mass
    t = np.asarray(targets, float)
    for z in order:
        j = int(np.argmin(mass - t))
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
    tg = np.broadcast_to(np.asarray(target, float), (k,))   # scalar or one target per district
    for _ in range(int(iters)):
        cur = float(np.abs(mass - tg).max())
        h, l = int(np.argmax(mass - tg)), int(np.argmin(mass - tg))
        if h == l:
            break
        best = None
        hi, lo = np.flatnonzero(lab == h), np.flatnonzero(lab == l)
        for z in hi:                                    # move z: h -> l
            v = float(max(abs(mass[h] - M[z] - tg[h]), abs(mass[l] + M[z] - tg[l]),
                          *(abs(mass[j] - tg[j]) for j in range(k) if j not in (h, l))))
            if v < cur - 1e-15 and (best is None or v < best[0]):
                best = (v, int(z), None)
        for z in hi:                                    # swap z (in h) with y (in l)
            for y in lo:
                dm = M[z] - M[y]
                if dm <= 0:
                    continue
                v = float(max(abs(mass[h] - dm - tg[h]), abs(mass[l] + dm - tg[l]),
                              *(abs(mass[j] - tg[j]) for j in range(k) if j not in (h, l))))
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
def cert_balance_ceiling(M, labels, k: int = None, locked=None) -> dict:
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

    Anchored draws: why `residual_targets` IS the ceiling
    -----------------------------------------------------
    `locked` (`centers.draw`'s encoding: `-1` free, else the pinned district) changes the
    question.  The Jensen ceiling stays **true** under a pin -- it bounds every partition, so a
    fortiori every pinned one -- but it stops being *reachable*, and quoting it charges the draw
    for a gap no lock-respecting partition could ever have closed.  Measured on the fixture in
    `tests/test_cert_draw.py`: an anchored-optimal draw is billed `log(4/3) = 0.288` nats.

    With `A_j` the mass pinned into district `j` and `S` the free mass, the honest ceiling is

        max  sum_j log(A_j + f_j)   s.t.  f_j >= 0,  sum_j f_j = S

    -- the free mass, distributed as well as it can be, on top of what the pins already fixed.
    That objective is strictly concave and the feasible set is a compact simplex, so the
    maximiser is unique and characterised by KKT: with multiplier `lambda` on the sum and
    `mu_j >= 0` on `f_j >= 0`, `1/(A_j + f_j) = lambda - mu_j` and `mu_j f_j = 0`.  Writing
    `u = 1/lambda`, that says

        f_j > 0  ==>  A_j + f_j = u          (every unsaturated district sits at a common level)
        f_j = 0  ==>  A_j >= u               (a district already past the level takes nothing)

    which is exactly a **water-fill at level `u`** -- and exactly what `centers.residual_targets`
    computes.  Its loop stops at a level `t` with `sum_{j free}(t - A_j) = S`, `A_j < t` on the
    unsaturated districts and `A_j >= t` on the saturated ones (the level is non-increasing as
    districts saturate, so a district saturated at an earlier, higher level is still saturated at
    `t`).  Those are the KKT conditions verbatim, so `residual_targets` returns the unique
    maximiser and `ceiling_nash = sum_j log(A_j + residual_j)`.  Established, not assumed: the
    argument above is a proof, and it was checked numerically against a general-purpose optimiser
    over 4,000 random anchored instances (max excess 8e-14).

    Two consequences worth stating.  The anchored ceiling is never above the free one, and equals
    it exactly when no anchor exceeds its equal share (then `u = T/k` and nothing saturates) --
    so a pin only costs Nash headroom once it is *over-weight*.  And `max_dev` is reported
    against these targets rather than against `T/k`, which is what makes it commensurable with
    `cert_integer_balance_floor`'s `t`.

    Without `locked` the certificate cannot know a pin exists, so `locked_supplied` says whether
    it was told.
    """
    M = np.asarray(M, float)
    labels = np.asarray(labels, int)
    if k is None:
        k = int(labels.max()) + 1 if labels.size else 0
    k = int(k)
    if k <= 0:
        return dict(certificate="balance_ceiling", k=0, feasible=False,
                    reason="no districts")
    st = _anchor_state(M, k, locked)
    _check_labels_match_locks(labels, st)
    anchored = st["anchored"]
    tg = st["targets"]                                   # the equal split when nothing is pinned
    mass = _masses(M, labels, k)
    total = float(mass.sum())
    target = total / k
    empty = [int(j) for j in np.flatnonzero(mass <= 0)]
    achieved = float(np.log(mass).sum()) if not empty else -math.inf
    jensen = k * math.log(target) if target > 0 else -math.inf
    if anchored:
        ceiling = float(np.log(tg).sum()) if (tg > 0).all() else -math.inf
        dev = float(np.abs(mass - tg).max())
    else:
        # bit-for-bit the pre-anchor numbers: `tg` is the same equal split, but it is derived
        # from `M.sum()` where these two are derived from `mass.sum()`, and the two totals can
        # differ in the last bit
        ceiling = jensen
        dev = float(np.abs(mass - target).max())
    gap = (ceiling - achieved) if math.isfinite(achieved) else math.inf
    if anchored:
        not_proved = ("nothing about compactness or contiguity, and not that the ceiling is "
                      "reachable in whole zips (see cert_integer_balance_floor)")
    else:
        not_proved = ("nothing about compactness, contiguity, or whether the ceiling is "
                      "reachable at all -- zips are indivisible (see "
                      "cert_integer_balance_floor)")
        if not st["supplied"]:
            not_proved += (".  No `locked` was supplied, so this is the FREE ceiling: on a "
                           "pinned draw it stays true but becomes unreachable, and the gap it "
                           "reports is then an overstatement")
    return dict(
        certificate="balance_ceiling",
        method=("analytic (constrained Jensen at the water-fill; no solver)" if anchored
                else "analytic (Jensen; no solver)"),
        k=k, n=int(labels.size), total=total, target=target,
        masses=[float(v) for v in mass],
        sizes=[int(v) for v in np.bincount(labels, minlength=k)],
        empty_districts=empty,
        achieved_nash=achieved,
        ceiling_nash=ceiling,
        jensen_ceiling_nash=jensen,
        anchored=anchored,
        locked_supplied=bool(st["supplied"]),
        n_locked=int(st["is_locked"].sum()),
        locked_mass=[float(v) for v in st["locked_mass"]],
        targets=[float(v) for v in tg],
        residual_targets=[float(v) for v in st["residual"]],
        saturated_districts=[int(j) for j in np.flatnonzero((st["residual"] <= 0)
                                                            & (st["locked_mass"] > 0))],
        gap_nats=gap,
        gap_rel=(1.0 - math.exp(-gap)) if math.isfinite(gap) else 1.0,
        min=float(mass.min()), max=float(mass.max()),
        spread_rel=float((mass.max() - mass.min()) / target) if target else 0.0,
        max_dev=dev,
        max_dev_rel=float(dev / target) if target else 0.0,
        proved=True,
        proves=(("sum_j log M_j <= sum_j log(locked_j + residual_j) for every partition of the "
                 "FREE zips that honours these pins -- the water-fill is the exact maximiser of "
                 "the anchored problem, so this ceiling is reachable up to indivisibility")
                if anchored else
                ("sum_j log M_j <= k log(sum M / k) for EVERY partition of these zips into k "
                 "parts; the gap is this draw's distance from perfect balance")),
        does_not_prove=not_proved,
    )


# ------------------------------------------- 2. the indivisible-zip floor on max-deviation
def cert_integer_balance_floor(M, k: int, time_limit: float = DEFAULT_TIME_LIMIT,
                               warm_labels=None, locked=None) -> dict:
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

    Anchored draws, and the symmetry breaking that does NOT survive them
    --------------------------------------------------------------------
    `locked` restricts the search to partitions that honour the pins: only the free zips are
    variables, and district `j` is asked for `residual_j` of free mass, the water-fill share
    `cert_balance_ceiling` proves is the anchored optimum.  Deviation is measured against
    `targets = locked_mass + residual`, which is what makes `t` commensurable with the ceiling's
    gap.  Without `locked` the certificate answers a *different question* -- and not a
    conservative one.  Measured on the seven-zip fixture in the tests: it reports `t = 0.5` where
    no lock-respecting partition beats `3.5` on the same yardstick, and the partition it offers
    as constructive proof moves pinned zips, so it is not a proof of anything about the anchored
    instance.

    Both inherited symmetry breaks assume **full label symmetry**, and a pin destroys it:
    district `j` now has an identity (its locked mass, hence its own target).  Following
    "solve on free zips against residual_targets" while keeping them is unsound, and measurably
    so -- each of these was run:

    * **heaviest zip into district 0** is dropped outright.  There is no valid restriction of
      it: the heaviest free zip may belong in an anchor district, and no relabelling of the
      other districts can put it there.  On `A = (10, 0)` with free zips `(4, 1, 1)` it turns
      `t* = 0` into `t = 4`.
    * **non-increasing mass on districts `1..k-1`** is restricted to the districts with **no
      locked mass**.  Those are the only ones still interchangeable: they share a locked mass of
      0 *and* a residual target (the common water level `u`), so permuting them maps any
      solution to an equally good one.  Left unrestricted it is unsound under either reading --
      ordering by free mass doubles the floor on `A = (0, 8, 1)` with four unit zips
      (`t* = 0.5` becomes `t = 1`), and ordering by total mass makes the model **infeasible** on
      `A = (0, 0, 8)`, where the true `t*` is 0.

    The cost of dropping break 1 is a bigger tree on anchored instances.  That is the correct
    trade: a fast wrong bound is worse than a slow honest one, and the primal side -- which is
    the operative half at production size -- does not go through the MILP at all.

    `labels` is always returned at full length with the pins in place, and `masses` is
    recomputed from it, so the returned partition can be checked against `locked` directly.
    `t_vs_equal_split` reports the same partition's deviation from `T/k`, because mixing the two
    yardsticks silently is exactly the trap this certificate exists to avoid.
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
    st = _anchor_state(M, k, locked)
    anchored = st["anchored"]
    lock, free = st["locked"], st["free"]
    tg, resid = st["targets"], st["residual"]            # equal split / equal split when free
    out.update(total=total, target=target, anchored=anchored,
               targets=[float(v) for v in tg],
               residual_targets=[float(v) for v in resid],
               locked_mass=[float(v) for v in st["locked_mass"]],
               n_locked=int(st["is_locked"].sum()), n_free=int(free.sum()))
    if warm_labels is not None:
        _check_labels_match_locks(warm_labels, st)
        ref = _masses(M, warm_labels, k)
        out["reference_max_dev"] = float(np.abs(ref - tg).max())
        out["reference_max_dev_rel"] = float(np.abs(ref - tg).max() / target)

    if k == 1:
        out.update(proved=True, status="proved_optimal", t=0.0, t_rel=0.0,
                   t_lower=0.0, t_rel_lower=0.0, t_source="trivial", solver_status=0,
                   solver_status_name="trivial", solver_message="k == 1: one district",
                   labels=[0] * n, masses=[total], t_seconds=0.0, t_vs_equal_split=0.0)
        out["proves"] = "with one district the deviation is 0 by definition"
        return out

    # only the FREE zips are decisions; the pinned ones enter as constant mass per district
    Mf = M[free]
    nf = int(Mf.size)
    if nf == 0:                                      # everything is pinned: nothing to choose
        mass = _masses(M, lock, k)
        t = float(np.abs(mass - tg).max())
        out.update(proved=True, status="proved_optimal", t=t, t_rel=t / target,
                   t_lower=t, t_rel_lower=t / target, t_source="forced (every zip is locked)",
                   solver_status=0, solver_status_name="trivial",
                   solver_message="every zip is locked: the partition is forced",
                   labels=lock.tolist(), masses=[float(v) for v in mass], t_seconds=0.0,
                   t_vs_equal_split=float(np.abs(mass - target).max()))
        out["proves"] = "the partition is forced by the pins, so t is its deviation, exactly"
        out["does_not_prove"] = "nothing geometric"
        return out

    # the constructive primal: a real partition, so a rigorous upper bound on t* with no solver
    t_g0 = time.perf_counter()
    if anchored:
        g_lab_f, g_mass_f = _lpt(Mf, k, targets=resid)
        out["t_lpt"] = float(np.abs(g_mass_f - resid).max())
        g_lab_f, _ = _polish_partition(Mf, k, g_lab_f, g_mass_f, resid)
    else:
        g_lab_f, g_mass_f = _lpt(Mf, k)
        out["t_lpt"] = float(np.abs(g_mass_f - target).max())
        g_lab_f, _ = _polish_partition(Mf, k, g_lab_f, g_mass_f, target)
    g_lab = lock.copy()
    g_lab[free] = g_lab_f                            # the pins are put back before anything else
    g_mass = _masses(M, g_lab, k)                    # recomputed, never carried incrementally
    t_greedy = float(np.abs(g_mass - tg).max())
    out.update(t_greedy=t_greedy, t_greedy_rel=t_greedy / target,
               t_lpt_rel=out["t_lpt"] / target,
               t_greedy_seconds=float(time.perf_counter() - t_g0))

    if time_limit is not None and time_limit <= 0:
        out.update(proved=False, status="not_attempted (time_limit <= 0)",
                   solver_status=None, solver_status_name="not_run", solver_message="",
                   t=t_greedy, t_rel=t_greedy / target, t_source="greedy_lpt_polish",
                   labels=g_lab.tolist(), masses=[float(v) for v in g_mass],
                   t_lower=0.0, t_rel_lower=0.0,
                   t_vs_equal_split=float(np.abs(g_mass - target).max()))
        out["proves"] = ("only the constructed partition: t* <= t.  The MILP was not run, so "
                         "nothing bounds t* from below beyond the trivial t* >= 0")
        return out

    # conditioning: masses descaled by their mean, exactly as centers.assign descales its LP.
    # Scaling a row and its right-hand side together leaves the feasible set identical.
    scale = float(Mf.mean())
    w = Mf / scale
    # the free mass district j is asked for.  Unanchored this is the equal split, computed the
    # way it always was so the un-anchored solve is arithmetically untouched.
    tw = np.full(k, float(w.sum()) / k) if not anchored else resid / scale

    nv = nf * k + 1                                  # ... + the max-deviation variable t
    A_place = _placement_matrix(nf, k, extra_cols=1)
    A_mass = _mass_matrix(w, k, extra_cols=1)
    # |free mass_j - residual_j| <= t, as two one-sided families.  Since M_j = locked_j + f_j and
    # target_j = locked_j + residual_j, this is |M_j - target_j| <= t with the locks folded in.
    e = sparse.coo_matrix((np.ones(k), (np.arange(k), np.full(k, nf * k))), shape=(k, nv))
    A_up = (A_mass - e).tocsc()                      # sum_z w x_zj - t <= tw
    A_lo = (A_mass + e).tocsc()                      # sum_z w x_zj + t >= tw

    cons = [LinearConstraint(A_place.tocsc(), 1.0, 1.0),
            LinearConstraint(A_up, -np.inf, tw),
            LinearConstraint(A_lo, tw, np.inf)]

    lb = np.zeros(nv)
    ub = np.ones(nv)
    # t is continuous, and capped at the constructed primal: a partition that good exists, so
    # the cap removes no solution that could be optimal, and it shrinks the tree
    ub[nf * k] = (t_greedy / scale) * (1.0 + 1e-9) + 1e-12

    # Symmetry breaking.  Both breaks are valid only under full label symmetry, which a pin
    # destroys (see the docstring, and the measured counterexamples there).
    if not anchored:
        z0 = int(np.argmax(Mf))                      # break 1: heaviest zip -> district 0
        lb[z0 * k] = 1.0
        ub[z0 * k + 1:z0 * k + k] = 0.0
        sym = list(range(1, k))                      # break 2: districts 1..k-1
    else:
        # break 1 has no sound restriction and is dropped.  Break 2 survives exactly on the
        # districts with no locked mass: they share a locked mass of 0 and a residual target
        # (the common water level), so permuting them maps a solution to an equally good one.
        sym = [j for j in range(k) if st["locked_mass"][j] <= 0.0]
        if len(sym) >= 2:
            lvl = resid[sym]
            if float(lvl.max() - lvl.min()) > 1e-9 * max(float(np.abs(lvl).max()), 1.0):
                sym = []                             # not interchangeable after all; take none
    out["symmetry_break_heaviest_zip"] = bool(not anchored)
    out["symmetry_break_ordered_districts"] = [int(j) for j in sym] if len(sym) >= 2 else []
    if len(sym) >= 2:
        base = np.arange(nf) * k
        rows, cols, vals = [], [], []
        for r, (ja, jb) in enumerate(zip(sym[:-1], sym[1:])):
            rows.append(np.full(2 * nf, r))
            cols.append(np.concatenate([base + ja, base + jb]))
            vals.append(np.concatenate([w, -w]))
        A_ord = sparse.coo_matrix((np.concatenate(vals),
                                   (np.concatenate(rows), np.concatenate(cols))),
                                  shape=(len(sym) - 1, nv)).tocsc()
        cons.append(LinearConstraint(A_ord, 0.0, np.inf))

    integrality = np.ones(nv)
    integrality[nf * k] = 0                          # t is continuous

    c = np.zeros(nv)
    c[nf * k] = 1.0

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
        lab_f = np.asarray(x[:nf * k], float).reshape(nf, k).argmax(axis=1).astype(int)
        lab = lock.copy()
        lab[free] = lab_f
        mass = _masses(M, lab, k)
        t_milp = float(np.abs(mass - tg).max())
        out.update(t_milp=t_milp, t_milp_rel=t_milp / target,
                   solver_t=float(x[nf * k]) * scale)  # what the engine thinks, for comparison
        if t_milp < best_t:
            best_t, best_lab, best_mass, src = t_milp, lab, mass, "milp"
    else:
        out["t_milp"] = out["t_milp_rel"] = None
    out.update(t=best_t, t_rel=best_t / target, t_source=src,
               labels=np.asarray(best_lab, int).tolist(),
               masses=[float(v) for v in best_mass],
               t_vs_equal_split=float(np.abs(best_mass - target).max()))

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
    scope = ("of the FREE zips that honours the pins (deviation measured against "
             "targets = locked_mass + residual)" if anchored else "of these zips")
    if out["proved"]:
        out["t_lower"] = out["t"]
        out["t_rel_lower"] = out["t_rel"]
        out["proves"] = (f"t* is exactly the smallest max-deviation ANY partition {scope} "
                         f"into k districts can achieve, geometry ignored")
    else:
        out["proves"] = (f"bound pair only: a partition {scope} achieving t was constructed (so "
                         f"balance that good is reachable), and no such partition beats t_lower; "
                         f"the true t* lies in [t_lower, t]")
    out["does_not_prove"] = ("nothing geometric -- the optimal partition here is generally "
                             "scattered and would make a nonsensical territory map")
    if anchored:
        out["does_not_prove"] += ("; and nothing about partitions that move a pinned zip, which "
                                  "is a different and strictly easier problem")
    return out


# ----------------------------------------- 3. optimal assignment with the centers PINNED
def cert_assignment_at_centers(xy, M, labels, centers, slack=None,
                               time_limit: float = DEFAULT_TIME_LIMIT, locked=None) -> dict:
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

    Anchored draws
    --------------
    `locked` pins `x_{z,l(z)} = 1` through the variable bounds -- the direct analogue of
    `centers.improve(movable=)`, which is what produced the draw in the first place.  Without it
    the certificate happily "improves" a pinned draw by undoing the pin, and reports the result
    as a finding: on the fixture in the tests it moves the one anchored zip back to the centroid
    beside it and claims a 99% cut in the moment of inertia, which is not an improvement anyone
    can take.  The balance band is centred on the water-fill `targets` rather than on `T/k` for
    the same reason as `cert_balance_ceiling` -- with an over-weight anchor, `T/k` is a target no
    lock-respecting assignment can reach, so a band around it is either vacuous or empty.

    `locked_respected` is checked on the returned labels rather than assumed from the bounds.
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

    st = _anchor_state(M, k, locked)
    _check_labels_match_locks(labels, st)
    anchored = st["anchored"]
    tg = st["targets"]                                # the equal split when nothing is pinned

    d2 = ((xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)      # (n, k)
    cost = M[:, None] * d2                                        # raw units
    draw_cost = float(cost[np.arange(n), labels].sum())
    total = float(M.sum())
    target = total / k
    mass_draw = _masses(M, labels, k)
    draw_dev = float(np.abs(mass_draw - tg).max())
    delta = draw_dev if slack is None else float(slack)
    out.update(total=total, target=target, draw_cost=draw_cost,
               draw_max_dev=draw_dev,
               draw_max_dev_rel=float(draw_dev / target),
               draw_nash=(float(np.log(mass_draw).sum()) if (mass_draw > 0).all()
                          else -math.inf),
               slack=delta, slack_rel=delta / target if target else 0.0,
               slack_is_default=slack is None,
               anchored=anchored, n_locked=int(st["is_locked"].sum()),
               targets=[float(v) for v in tg])

    if time_limit is not None and time_limit <= 0:
        out.update(proved=False, status="not_attempted (time_limit <= 0)",
                   solver_status=None, solver_status_name="not_run", solver_message="",
                   opt_cost=None, rel_gap=None, improving_labels=None)
        out["proves"] = "nothing -- the solve was not attempted"
        return out

    # conditioning (see the module docstring): mass column by its mean, objective by its mean
    mscale = float(M.mean())
    w = M / mscale
    # unanchored this is the equal split, computed as it always was; anchored it is the
    # water-fill, the only per-district target a pinned assignment can actually meet
    tw = np.full(k, float(w.sum()) / k) if not anchored else tg / mscale
    dw = delta / mscale
    cscale = float(cost.mean())
    c = (cost / (cscale if cscale > 0 else 1.0)).ravel()

    tol = FEAS_TOL * max(float(tw.max()), 1.0)
    cons = [LinearConstraint(_placement_matrix(n, k).tocsc(), 1.0, 1.0),
            LinearConstraint(_mass_matrix(w, k).tocsc(), tw - dw - tol, tw + dw + tol)]

    # the pins, as variable bounds: the analogue of centers.improve(movable=)
    if anchored:
        lb = np.zeros(n * k)
        ub = np.ones(n * k)
        for z in np.flatnonzero(st["is_locked"]):
            j = int(st["locked"][z])
            ub[z * k:(z + 1) * k] = 0.0
            lb[z * k + j] = 1.0
            ub[z * k + j] = 1.0
        bounds = Bounds(lb, ub)
    else:
        bounds = Bounds(0.0, 1.0)

    t0 = time.perf_counter()
    res = milp(c, integrality=np.ones(n * k), bounds=bounds, constraints=cons,
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
    # checked on the returned labels, not assumed from the bounds we handed the solver
    m = st["is_locked"]
    respected = bool((not m.any()) or (lab[m] == st["locked"][m]).all())
    out["locked_respected"] = respected
    feasible = bool(np.abs(mass_opt - tg).max() <= delta + 1e-6 * max(target, 1.0)) and respected
    out.update(opt_cost=opt_cost,
               opt_max_dev=float(np.abs(mass_opt - tg).max()),
               opt_max_dev_rel=float(np.abs(mass_opt - tg).max() / target),
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
    pins = " (among assignments that honour the pins)" if anchored else ""
    if improved:
        out["proves"] = ("the draw is NOT assignment-optimal at its own centers: a strictly "
                         f"cheaper assignment{pins} exists at balance no worse than the draw's")
    elif out["proved"]:
        out["proves"] = (f"no integer assignment{pins} to THESE centers, at max-deviation <= "
                         "slack, is more compact than the draw -- the assignment step is "
                         "optimal given the centers")
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
def cert_power_diagram(xy, M, labels, centers, targets=None, locked=None) -> dict:
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

    Anchored draws: the bound has to be taken on the FREE subproblem
    ----------------------------------------------------------------
    A pinned zip need not lie in its own power cell -- it is there because it was pinned, not
    because it is close -- so on an anchored draw the free-cell check condemns a draw that is
    optimal given the pins.  Measured on the fixture in the tests: one pinned zip, and the
    certificate reports a 16.5% gap and `is_power_diagram = False` for a draw no lock-respecting
    assignment beats.

    What `locked` does here is more than excluding those zips from the count, because that alone
    would leave the *bound* wrong in the direction that matters.  Run over all `n` zips, the LP
    may reassign the pinned ones, so `lp_bound` stays a valid lower bound (it is a relaxation)
    but `is_power_diagram = True` would no longer mean the draw is optimal -- the claim, not the
    number, is what breaks.  So the certificate is taken on the free subproblem instead.  Write

        cost(draw) = sum_{z pinned} M_z d^2(z, c_{l(z)})  +  cost_F(draw)

    -- the first term is a constant of the anchored instance.  `power_weights` is solved on the
    free zips alone at the draw's own realised **free** mass per district, and its dual bound
    bounds `cost_F` over every assignment of the free zips meeting those free masses.  Adding
    the constant gives `lp_bound`, a genuine lower bound on every lock-respecting assignment,
    and `n_outside_cell = 0` then means exactly what it means unanchored: the draw is the most
    compact assignment available to it.  `locked_cost` and `lp_bound_free` are returned
    separately so the split is checkable.

    Not proved, same scope as certificate 3: nothing about the centers.  The bound is
    conditional on `centers` exactly as a k-means assignment step is.
    """
    from . import centers as _centers                       # a pure-numpy sibling; no cycle

    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    labels = np.asarray(labels, int)
    C = np.asarray(centers, float)
    n, k = xy.shape[0], C.shape[0]

    st = _anchor_state(M, k, locked)
    _check_labels_match_locks(labels, st)
    anchored = st["anchored"]
    free, is_locked = st["free"], st["is_locked"]
    nf = int(free.sum())

    d2 = ((xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    cost = M[:, None] * d2
    draw_cost = float(cost[np.arange(n), labels].sum())
    mass_draw = _masses(M, labels, k)
    target = float(M.sum()) / k

    own = targets is None
    if not anchored:
        locked_cost = 0.0
        res = _centers.power_weights(xy, M, C, targets=mass_draw if own else targets)
        cell = np.asarray(res["labels"], int)
        outside = cell != labels
        mass_cell = _masses(M, cell, k)
        # the incumbent has to be inside the bound's own feasible set for the gap to mean anything
        t = np.asarray(res["targets"], float)
        dev = float(np.abs(mass_draw - t).max())
        meets = bool(own or dev <= FEAS_TOL * max(float(M.sum()), 1.0))
        bound = float(res["lp_bound"])
        cell_cost = float(cost[np.arange(n), cell].sum())
        full_targets = [float(v) for v in res["targets"]]
    else:
        if nf < k:
            return dict(certificate="power_diagram_duals", n=int(n), k=int(k), anchored=True,
                        n_locked=int(is_locked.sum()), n_free=nf, proved=False,
                        status="not_attempted (fewer free zips than districts)",
                        proves="nothing -- the free subproblem is degenerate")
        locked_cost = float(cost[is_locked, labels[is_locked]].sum())
        mass_free = np.bincount(labels[free], weights=M[free], minlength=k).astype(float)
        res = _centers.power_weights(xy[free], M[free], C,
                                     targets=mass_free if own else targets)
        cell_f = np.asarray(res["labels"], int)
        cell = labels.copy()                       # the pins stay where they are on the map
        cell[free] = cell_f
        outside = np.zeros(n, bool)
        outside[free] = cell_f != labels[free]
        mass_cell = _masses(M, cell, k)
        t = np.asarray(res["targets"], float)
        dev = float(np.abs(mass_free - t).max())
        meets = bool(own or dev <= FEAS_TOL * max(float(M.sum()), 1.0))
        bound = locked_cost + float(res["lp_bound"])
        cell_cost = float(cost[np.arange(n), cell].sum())
        full_targets = [float(a + b) for a, b in zip(st["locked_mass"], res["targets"])]

    out = dict(certificate="power_diagram_duals",
               method=("transportation LP duals on the FREE zips (HiGHS), verified by O(nk) "
                       "arithmetic" if anchored else
                       "transportation LP duals (HiGHS), verified by O(nk) arithmetic"),
               n=int(n), k=int(k), centers_pinned=True,
               anchored=anchored, n_locked=int(is_locked.sum()), n_free=nf,
               locked_cost=locked_cost,
               lp_bound_free=float(res["lp_bound"]),
               free_targets=[float(v) for v in res["targets"]],
               targets_are_draw_masses=bool(own),
               draw_meets_targets=meets,
               draw_target_max_dev=dev,
               weights=[float(v) for v in res["weights"]],
               targets=full_targets,
               alpha_sum=float(np.sum(res["alpha"])),
               beta=[float(v) for v in res["beta"]],
               n_fractional=int(res["n_fractional"]),
               max_dual_violation=float(res["max_dual_violation"]),
               max_dual_violation_rel=float(res["max_dual_violation_rel"]),
               max_cs_residual_rel=float(res["max_cs_residual_rel"]),
               lp_bound=bound,
               draw_cost=draw_cost,
               rel_gap=((float((draw_cost - bound) / draw_cost) if draw_cost > 0
                         else 0.0) if meets else None),
               cell_cost=cell_cost,
               n_outside_cell=int(outside.sum()),
               outside_cell_share=float(outside.mean()) if n else 0.0,
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
        out["proves"] = (("every FREE zip lies in its own cell of the power diagram of these "
                          "centers, so the draw is the most compact assignment available to it "
                          "at these masses WITHOUT moving a pinned zip")
                         if anchored else
                         ("the draw IS the power diagram of its centers with these weights, and "
                          "therefore the most compact assignment meeting the mass targets"))
    else:
        out["proves"] = (("no assignment of the FREE zips to these centers meeting the free mass "
                          "targets costs less than lp_bound - locked_cost, so no lock-respecting "
                          "assignment costs less than lp_bound -- a bound checkable in O(nk) "
                          "arithmetic from alpha and beta, with no solver in the trusted path")
                         if anchored else
                         ("no assignment of these zips to these centers meeting the mass targets "
                          "costs less than lp_bound -- a bound checkable in O(nk) arithmetic "
                          "from alpha and beta, with no solver in the trusted path"))
    out["does_not_prove"] = ("nothing about the centers, which are the heuristic's; and nothing "
                             "about the stage-1 Nash objective, which this LP does not see -- "
                             "the zips outside their cell are where the draw bought balance "
                             "with compactness")
    if anchored:
        out["does_not_prove"] += ("; and nothing about assignments that move a pinned zip, which "
                                  "is a strictly larger and cheaper feasible set")
    return out


# --------------------------------------------------------------------------- the report
def certify(xy, M, labels, centers, k: int = None, *,
            time_limit: float = DEFAULT_TIME_LIMIT,
            floor_time_limit: float = None, slack=None, locked=None) -> dict:
    """Run all three certificates on one draw and merge them into a single report.

    `summary` is a list of plain sentences, each stating what IS and what IS NOT proved, in the
    order the certificates strengthen: the analytic ceiling bounds every partition; the integer
    floor says how much of the gap to that ceiling was ever available; the pinned-center
    assignment says whether the geometry of *this* draw was solved optimally given its centers.

    Nothing here certifies the centers.  That is stated in the summary every time, because it is
    the one thing a reader is most likely to assume and the one thing least true.

    `locked` (`centers.draw`'s encoding) is passed to all four.  It changes what each of them
    means -- see their docstrings -- so when it is given the summary says so in its first line,
    rather than leaving a reader to notice that the numbers are about a pinned instance.
    """
    labels = np.asarray(labels, int)
    if k is None:
        k = int(np.asarray(centers).shape[0])
    k = int(k)
    if floor_time_limit is None:
        floor_time_limit = time_limit

    ceil_ = cert_balance_ceiling(M, labels, k, locked=locked)
    floor = cert_integer_balance_floor(M, k, time_limit=floor_time_limit, warm_labels=labels,
                                       locked=locked)
    assign = cert_assignment_at_centers(xy, M, labels, centers, slack=slack,
                                        time_limit=time_limit, locked=locked)
    power = cert_power_diagram(xy, M, labels, centers, locked=locked)
    anchored = bool(ceil_.get("anchored"))

    s = []
    if anchored:
        s.append(
            f"ANCHORED DRAW: {ceil_['n_locked']} of {int(labels.size)} zips are pinned, so every "
            f"certificate below is about the partitions that HONOUR those pins and no others. "
            f"The per-district targets are the water-fill "
            f"{['%.4g' % v for v in ceil_['targets']]} rather than the equal split "
            f"{ceil_['target']:.4g}; districts {ceil_['saturated_districts']} are saturated "
            f"(pinned at or past their share, so they take nothing more). Balance deviations "
            f"below are measured against those targets.")
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
        anchored=anchored,
        balance_ceiling=ceil_,
        integer_balance_floor=floor,
        assignment_at_centers=assign,
        power_diagram=power,
        proved_all=bool(ceil_.get("proved") and floor.get("proved") and assign.get("proved")
                        and power.get("proved")),
        summary=s,
    )
