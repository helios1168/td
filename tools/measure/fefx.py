"""fefx.py -- A1: the typed FEFx / EF1 / proportionality audit core.

Read-only over `td/`.  This is the scoped, delivered-map fairness audit settled by
`agy-job/contract.md` sections 1, 2 and 9: for every ordered pair (rep i, district j) it
emits three verdicts -- plain EF1 (existential removal), FEFx w.r.t. the capacity band
(universal removal), and proportionality -- plus the legacy `td/model.py::fairness`
regression anchor.

The two valuation conventions are explicit and never mixed:

    "gain_matrix"   every rep prices every district, u_i(z) = common_z + (c1 - c2)*S_i(z),
                    the same formula `td/channel.py::gain_matrix` uses (non-holders still
                    value the ambient `common_z = c2*T_z + c_free*S_free(z) + lam*M_z`).
    "masked"        `td/model.py::utilities`, which zeroes non-candidates.  This is the
                    legacy anchor convention and reproduces `td/model.py::fairness`.

EF1 removes the single *most* valuable zip (`TOP`, existential); FEFx removes the single
*least* valuable zip (`BOT`, universal).  By additivity that is exact: `u_i(A_j) - TOP <= g_i`
iff some one-good removal kills the envy, and `u_i(A_j) - BOT <= g_i` iff every removal does.
`TOP >= BOT`, so FEFx pass implies EF1 pass; a wide EF1 failure that is *not* an FEFx failure
is the meaningful diagnostic (`DOMAIN_economic-theory.md` N1).

Feasibility is the whole-district capacity band, supplied by the caller as `feasible`
(`(n_rep, n_district) bool`); the audit tests it once, before removal, and never re-runs it.
The band-only and band-plus-book-overlap audits are two *separate* calls with two different
masks; this module never combines them.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..")))

from td import channel, model                                             # noqa: E402

Rep = str
District = str

# Not-applicable reason enum (contract section 2).  A pair with a reason is not applicable
# and contributes to no pass or fail total.  `None` is the applicable case; "ok" is never a
# reason value.
REASON_SELF = "self"
REASON_EMPTY_BUNDLE = "empty_bundle"
REASON_EMPTY_OWN_BUNDLE = "empty_own_bundle"
REASON_INFEASIBLE = "infeasible_for_agent"
REASON_UNMATCHED = "unmatched_rep"
NOT_APPLICABLE_REASONS = (
    REASON_SELF, REASON_EMPTY_BUNDLE, REASON_EMPTY_OWN_BUNDLE,
    REASON_INFEASIBLE, REASON_UNMATCHED,
)

VALUATIONS = ("gain_matrix", "masked")
QUANTIFIERS = ("ef1", "efx")


@dataclass(frozen=True)
class PairVerdict:
    """One ordered pair: rep `i` envies district `j`.

    `reason` is `None` iff the pair is applicable (a verdict was computed); otherwise it is
    one of `NOT_APPLICABLE_REASONS`.  `ef1` (existential removal, `TOP`) and `fefx`
    (universal removal, `BOT`) are `None` on a non-applicable pair.  `mass` and `band` are
    filled only for `infeasible_for_agent`, from the caller-supplied district mass and band.
    """
    i: Rep
    j: District
    reason: str | None
    ef1: bool | None
    fefx: bool | None
    applicable: bool
    mass: float | None = None
    band: tuple | None = None


# --------------------------------------------------------------------------- valuation
def _utility_matrix(G, nodes, reps_order, *, theta, lam, filler_capture, valuation):
    """Per-zip utilities `U[i, z]` over `nodes` under the named convention.

    `masked` is exactly `model.utilities` (non-candidates zeroed).  `gain_matrix` prices
    every rep on every zip with the `channel.gain_matrix` formula
    `common_z + (c1 - c2)*S_i(z)`, reusing `model.coefficients` / `model.books` /
    `model.free_book`; its row sums over a district equal `channel.gain_matrix`'s `g`.
    """
    R = list(reps_order)
    if valuation == "masked":
        U, _ = model.utilities(G, list(nodes), R, theta=theta, lam=lam,
                               filler_capture=filler_capture)
        return U
    c1, c2, c_free = model.coefficients(theta, lam, filler_capture)
    ir = {r: i for i, r in enumerate(R)}
    U = np.zeros((len(R), len(nodes)), float)
    for j, z in enumerate(nodes):
        S = model.books(G, z)
        T = float(sum(S.values()))
        free = model.free_book(G, z)
        M = float(G.nodes[z]["M"])
        common = c2 * T + c_free * free + lam * M
        for r, i in ir.items():
            U[i, j] = common + (c1 - c2) * float(S.get(r, 0.0))
    return U


def _extrema(U, nodes, to_district, districts):
    """`(G, TOP, BOT)` over districts: sum, max and min of `U` per district column.

    An empty district column yields `G = TOP = BOT = 0` (contract section 1).
    """
    nR, nD = U.shape[0], len(districts)
    jd = {d: j for j, d in enumerate(districts)}
    zc = {z: k for k, z in enumerate(nodes)}
    G = np.zeros((nR, nD), float)
    TOP = np.full((nR, nD), -np.inf, float)
    BOT = np.full((nR, nD), np.inf, float)
    has = np.zeros(nD, bool)
    for z in nodes:
        d = to_district[z]
        if d not in jd:
            raise ValueError(f"zip {z!r} maps to district {d!r}, absent from the district list")
        j = jd[d]
        has[j] = True
        u = U[:, zc[z]]
        G[:, j] += u
        np.maximum(TOP[:, j], u, out=TOP[:, j])
        np.minimum(BOT[:, j], u, out=BOT[:, j])
    TOP[:, ~has] = 0.0
    BOT[:, ~has] = 0.0
    return G, TOP, BOT


def district_extrema(G, to_district, reps_order=None, districts=None, *,
                     theta: float = 0.40, lam: float = 0.30,
                     filler_capture: str = "theta"):
    """`(G, TOP, BOT)` under the `gain_matrix` valuation convention (contract section 9).

    `G[i, j] = u_i(A_j)`, `TOP[i, j] = max_{z in A_j} u_i(z)`, `BOT[i, j] = min_{z in A_j}
    u_i(z)`, with `u_i` priced on every zip exactly as `channel.gain_matrix` does.  `G`
    equals `channel.gain_matrix`'s `g`; `TOP`/`BOT` are the per-district extrema needed for
    the EF1 (remove max) and FEFx (remove min) closed forms.
    """
    nodes = sorted(to_district)
    R = list(reps_order) if reps_order is not None else model.reps(G, nodes)
    D = list(districts) if districts is not None else channel.districts_from(to_district)
    U = _utility_matrix(G, nodes, R, theta=theta, lam=lam,
                        filler_capture=filler_capture, valuation="gain_matrix")
    if not np.isfinite(U).all():
        raise ValueError("non-finite utility values (reject)")
    return _extrema(U, nodes, to_district, D)


# --------------------------------------------------------------------------- the audit
def compute_envy_matrix(G, to_district, reps_order=None, districts=None, *,
                        feasible: np.ndarray | None = None,
                        quantifier: str = "efx",
                        valuation: str = "gain_matrix",
                        slack: float = 0.0,
                        theta: float = 0.40, lam: float = 0.30,
                        filler_capture: str = "theta",
                        assignment: dict | None = None,
                        district_mass: dict | None = None,
                        bands: dict | None = None) -> dict:
    """The FEFx / EF1 / proportionality audit on a delivered assignment.

    `feasible` is the whole-district mask `(n_rep, n_district)`; `None` means plain
    (unfiltered).  `quantifier` names the removal rule, `"ef1"` (existential, `TOP`) or
    `"efx"` (universal, `BOT`); both verdicts are computed and returned either way.  The
    legacy anchor is `valuation="masked"`, `quantifier="ef1"`, `slack=1e-12`, with the
    total-roster proportionality divisor.

    `assignment` maps `district -> rep` (the delivered roster); `None` is the identity
    `districts[i] -> reps_order[i]`, the square-case convention under which `self` is the
    diagonal.  `district_mass` and `bands` enrich `infeasible_for_agent` records only.
    """
    if valuation not in VALUATIONS:
        raise ValueError(f"valuation {valuation!r} not in {VALUATIONS}")
    if quantifier not in QUANTIFIERS:
        raise ValueError(f"quantifier {quantifier!r} not in {QUANTIFIERS}")
    if not np.isfinite(slack) or slack < 0.0:
        raise ValueError(f"slack must be finite and >= 0, got {slack!r}")

    nodes = sorted(to_district)
    R = list(reps_order) if reps_order is not None else model.reps(G, nodes)
    D = list(districts) if districts is not None else channel.districts_from(to_district)
    nR, nD = len(R), len(D)

    U = _utility_matrix(G, nodes, R, theta=theta, lam=lam,
                        filler_capture=filler_capture, valuation=valuation)
    if not np.isfinite(U).all():
        raise ValueError("non-finite utility values (reject)")
    Gmat, TOP, BOT = _extrema(U, nodes, to_district, D)

    if feasible is None:
        feas = np.ones((nR, nD), bool)
    else:
        feas = np.asarray(feasible, dtype=bool)
        if feas.shape != (nR, nD):
            raise ValueError(f"feasible must be ({nR}, {nD}), got {feas.shape}")

    # --- the delivered roster and ownership
    if assignment is None:
        assignment = {D[i]: R[i] for i in range(min(nR, nD))}
    else:
        assignment = dict(assignment)
        bad_d = [d for d in assignment if d not in set(D)]
        if bad_d:
            raise ValueError(f"assignment keys not in the district list: {bad_d}")
        bad_r = [r for r in assignment.values() if r not in set(R)]
        if bad_r:
            raise ValueError(f"assignment values not in the rep list: {bad_r}")
        if len(set(assignment.values())) != len(assignment):
            raise ValueError("assignment is not injective (one rep, two districts)")

    owner = {r: d for d, r in assignment.items()}          # rep -> its own district
    didx = {d: j for j, d in enumerate(D)}
    ridx = {r: i for i, r in enumerate(R)}
    retained = set(assignment.values())

    zip_count = np.zeros(nD, int)
    for z in nodes:
        zip_count[didx[to_district[z]]] += 1

    own_idx = {r: (didx[owner[r]] if r in owner else None) for r in R}
    g_own = np.zeros(nR, float)
    for r in R:
        j = own_idx[r]
        if j is not None and zip_count[j] > 0:
            g_own[ridx[r]] = Gmat[ridx[r], j]

    # proportionality divisor: masked -> every roster row (fairness); gain_matrix -> retained
    n = nR if valuation == "masked" else len(assignment)
    uZ = U.sum(axis=1)                                     # u_i(Z), the delivered footprint

    legacy = valuation == "masked"
    pairs: list[PairVerdict] = []
    ef1_all = True
    fefx_all = True
    n_ef1_fail = 0
    n_fefx_fail = 0
    n_applicable = 0
    n_zero_bundle = 0
    worst_envy = 0.0
    reason_counts = {k: 0 for k in NOT_APPLICABLE_REASONS}

    for i, r in enumerate(R):
        j_own = own_idx[r]
        # unmatched / empty-own exclusions are the new-audit (gain_matrix) semantics; the
        # masked anchor evaluates every envier exactly as fairness does (g_i = 0 when empty)
        unmatched_i = (not legacy) and j_own is None
        empty_own = (not legacy) and j_own is not None and zip_count[j_own] == 0
        gi = g_own[i]
        for j, d in enumerate(D):
            reason = None
            if unmatched_i:
                reason = REASON_UNMATCHED
                p = PairVerdict(r, d, reason, None, None, False)
            elif empty_own:
                reason = REASON_EMPTY_OWN_BUNDLE
                p = PairVerdict(r, d, reason, None, None, False)
            elif j_own == j:
                reason = REASON_SELF
                p = PairVerdict(r, d, reason, None, None, False)
            elif zip_count[j] == 0:
                reason = REASON_EMPTY_BUNDLE
                p = PairVerdict(r, d, reason, None, None, False)
            elif not feas[i, j]:
                reason = REASON_INFEASIBLE
                mass = district_mass.get(d) if district_mass is not None else None
                band = bands.get(d) if bands is not None else None
                p = PairVerdict(r, d, reason, None, None, False, mass=mass, band=band)
            else:
                v = Gmat[i, j]
                top = TOP[i, j]
                bot = BOT[i, j]
                ef1_ok = not (v - top > gi + slack)
                fefx_ok = not (v - bot > gi + slack)
                p = PairVerdict(r, d, None, bool(ef1_ok), bool(fefx_ok), True)
                n_applicable += 1
                if not ef1_ok:
                    ef1_all = False
                    n_ef1_fail += 1
                if not fefx_ok:
                    fefx_all = False
                    n_fefx_fail += 1
                if bot == 0.0:
                    n_zero_bundle += 1
                envy = v - gi
                if envy > 0.0 and top > 0.0:
                    worst_envy = max(worst_envy, envy / top)
            if reason is not None:
                reason_counts[reason] += 1
            pairs.append(p)

    # legacy normalized proportionality shortfall (fairness semantics)
    shortfall = 0.0
    for i in range(nR):
        if not legacy and ridx.get(R[i]) is not None and R[i] not in retained:
            continue
        if n == 0:
            continue
        share = uZ[i] / n
        umax = float(U[i].max()) if U.shape[1] else 0.0
        if umax > 0.0:
            shortfall = max(shortfall, max(0.0, share - g_own[i]) / umax)

    # signed raw proportional gap: g_i - u_i(Z)/n
    prop_gap = np.full(nR, np.nan, float)
    if legacy:
        prop_gap = g_own - uZ / n if n > 0 else prop_gap
    else:
        for r in retained:
            i = ridx[r]
            prop_gap[i] = g_own[i] - uZ[i] / n
    finite_gap = prop_gap[np.isfinite(prop_gap)]
    prop_gap_min = float(finite_gap.min()) if finite_gap.size else float("nan")

    return dict(
        valuation=valuation,
        quantifier=quantifier,
        slack=float(slack),
        theta=float(theta),
        lam=float(lam),
        filler_capture=str(filler_capture),
        n=int(n),
        n_reps=nR,
        n_districts=nD,
        n_retained=len(retained),
        n_unmatched_reps=nR - len(retained),
        n_unstaffed_districts=nD - len(assignment),
        n_applicable=n_applicable,
        n_infeasible=int(reason_counts[REASON_INFEASIBLE]),
        n_infeasible_districts=int((~feas).any(axis=0).sum()),
        n_zero_valued_bundle_pairs=n_zero_bundle,
        n_self=int(reason_counts[REASON_SELF]),
        n_empty_bundle=int(reason_counts[REASON_EMPTY_BUNDLE]),
        n_empty_own_bundle=int(reason_counts[REASON_EMPTY_OWN_BUNDLE]),
        n_unmatched=int(reason_counts[REASON_UNMATCHED]),
        ef1=bool(ef1_all),
        n_ef1_failures=n_ef1_fail,
        fefx=bool(fefx_all),
        n_fefx_failures=n_fefx_fail,
        envy_over_umax=float(worst_envy),
        prop_shortfall=float(shortfall),
        prop_gap=prop_gap,
        prop_gap_min=prop_gap_min,
        pairs=pairs,
    )
