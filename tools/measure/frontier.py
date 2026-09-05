"""frontier.py -- U8-band: the band-constrained frontier `delta -> EG^bal_{S13}(delta)`.

    .venv/bin/python3 tools/measure/frontier.py instance_descaled.json.gz \\
        battery/results/draw_k13_20260901 --out battery/results/u8_band_20260904

`docs/MODEL_U8-band.md` is the spec; `td/solvers/eg_band.py` is the solver.  Read-only over
`td/`.  What this produces, in the order the unit brief asks for it:

* **the hard gate** -- the unconstrained `EG_S` checked against `V` before any frontier point is
  computed.  `EG_S` is an upper bound on every band-feasible map's value and the delivered map is
  one such map, so `EG_S >= V` holds on *any* instance and fails exactly when the utility matrix
  is wrong.  It must be `channel.gain_matrix`'s **unmasked** convention (a rep is valued on every
  zip, not only where it holds book); `model.utilities` is the masked form and lands at
  `EG = 55.98` on v1 (the masked delivered map at `51.93`), *below* `V = 59.9375`, which would
  mimic a refutation of P1-band rather than a units error (measured, `CODEVERIFY_U8-band.md`
  row 2).  `--gate-reference VALUE` additionally pins `EG_S` to a published number to `1e-6`;
  v1 at `k = 13` reproduces with `--gate-reference 60.6974156139`;
* **`delta_0`** = `max_j |m_j - T/k| / (T/k)` on the committed draw -- a **max deviation**, not
  the published 0.78% spread (`MODEL_U8-band.md` §6 records the N7 discrepancy);
* **D1'** -- the one-solve concavity certificate `EG^bal(d0) + s(d0)(d - d0) - V <= 5e-3` at
  `d in {0.02, 0.05, 0.10}`, with a soft / not-soft verdict;
* **the frontier** on `{d0, 0.02, 0.05, 0.10, 0.33}` with monotonicity and concavity checked and
  reported, `delta*` by bisection, the band duals `nu_i` (N8), the proportionality gap (N9), the
  first-mover zips and their `M`-mass, and two SCIP cross-checks;
* **the plot**, always carrying the delivered MNW draw at `(d0, 59.9375)` and the unconstrained
  endpoint at `(0.33, 60.6974)` -- trap 2, every time the curve is rendered.

Every reported bound is verified by `eg_band.check_dual`, which is `O(nk)` arithmetic with no
solver in the trusted path.  A SCIP `timelimit` is reported as no bound, never as a bound.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import importlib.metadata as _md
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..")))

from td import channel, model                                              # noqa: E402
from td import instance as descaled                                        # noqa: E402
from td.solvers import eg_band                                             # noqa: E402

Rep = str
District = str
Zip = str
Roster = dict[District, Rep]

SMALL_NATS = 5e-3                    # base.EPS_CERT, the tier-2 floor
GATE_TOL = 1e-6                      # the utility-convention gate, in nats
EG_S13_REFERENCE = 60.6974156139     # v1 at k=13 only; docs/MODEL_U1-cert.md §4.1
V_DELIVERED_REFERENCE = 59.9374697984  # v1 at k=13 only
CROSS_TOL = 1e-6                     # OA vs SCIP agreement
GRID = (0.02, 0.05, 0.10, 0.33)      # delta_0 is prepended once measured (MODEL_U8-band.md §6)
SPONSOR_DELTAS = (0.02, 0.05, 0.10)  # D1': FRAME §3's +-10% is the widest on record
SCIP_DELTAS = (0.02, 0.33)           # "two or three delta only"
BIND_TOL = 1e-9                      # a band multiplier above this counts as binding (N8)
SHAPE_TOL = 1e-7                     # the LP tolerance floor; below it, no shape violation
TANGENT_TOL = 1e-7                   # the same floor, for U9 §10.A's supergradient guard
_K_DIR = re.compile(r"^k\d+$")


# --------------------------------------------------------------------------- the setting
@dataclass(frozen=True)
class Setting:
    """The instance, the committed draw and the roster every number below is conditional on."""

    nodes: tuple[Zip, ...]
    districts: tuple[District, ...]
    staff: tuple[Rep, ...]           # staff[j] runs districts[j]; the roster S13
    U: np.ndarray                    # (n, k) unmasked utilities, column j = staff[j]
    M: np.ndarray                    # (n,)
    V: float                         # sum_j log g at the delivered coverage
    g_delivered: np.ndarray          # (k,)
    m_delivered: np.ndarray          # (k,) district opportunity masses
    delta0: float                    # max_j |m_j - T/k| / (T/k)
    spread0: float                   # (max - min)/mean -- the published 0.0078, for the finding

    @property
    def T(self) -> float:
        return float(self.M.sum())

    @property
    def k(self) -> int:
        return len(self.staff)

    @property
    def u_total(self) -> np.ndarray:
        """`u_i(Z)` per selected rep -- the numerator of N9's proportionality share."""
        return self.U.sum(axis=0)


@dataclass(frozen=True)
class Point:
    """One grid point of the frontier, with everything N7/N8/N9 read off it."""

    delta: float
    upper: float
    primal: float
    bracket: float
    slope: float                     # (T/k) sum_i |nu_i| -- U9 P4.3's canonical supergradient
    slope_raw: float                 # (T/k) sum_i (mu+ + mu-) -- solver-dependent, for contrast
    converged: bool
    n_cuts: int
    status: str
    m: np.ndarray                    # (k,) masses at the optimum
    nu: np.ndarray                   # (k,) net band multipliers
    n_binding_upper: int             # N8
    n_binding_lower: int
    prop_gap: np.ndarray             # N9: g_i - u_i(Z)/k
    p: np.ndarray                    # (n,) supply duals -- dumped so the O(nk) check is redoable
    q_min: float                     # min_zi q_zi = p_z + nu_i M_z, the gauge-invariant price
    q_max: float
    integral_witness_in_band: bool   # the delivered draw is band-feasible here (U9 §10.D)
    dual_check: eg_band.DualCheck
    vertex: eg_band.VertexReport
    scip: eg_band.ScipBound | None

    @property
    def certified_upper(self) -> float:
        """The tighter of the two valid upper bounds: the master's, and the `O(nk)` dual's."""
        if self.dual_check.feasible and math.isfinite(self.dual_check.bound):
            return float(min(self.upper, self.dual_check.bound))
        return float(self.upper)


@dataclass(frozen=True)
class Softness:
    """D1': the one-solve concavity bound at a sponsor's `delta`, against the tier-2 floor.

    `direct` is `EG^bal(delta)` actually solved at that `delta`, and `slack = bound - direct` is
    `VERIFY_U9-bandthm` §10.A's mandatory guard: the tangent bound must dominate the curve, or
    `s_min` was under-minimised and the certificate is invalid.  Because every sponsor `delta`
    is also a grid point, the softness *verdict* here does not rest on `s_min` at all -- it is
    read off `direct` -- and the one-solve bound is reported as the certificate it is meant to
    be, with its validity witnessed rather than assumed.
    """

    delta: float
    bound: float                     # EG^bal(d0) + s_min(d0)(delta - d0)
    gap: float                       # bound - V(delivered)
    soft: bool
    direct: float | None             # EG^bal(delta) solved outright, when delta is on the grid
    slack: float | None              # bound - direct; must be >= 0 or s_min is not a supergradient
    tangent_valid: bool | None


@dataclass(frozen=True)
class DeltaStar:
    """`delta* = min{delta : EG^bal(delta) - V > 5e-3}` by bisection on monotonicity."""

    value: float | None
    verdict: str
    lo: float
    hi: float
    n_solves: int


@dataclass(frozen=True)
class Shape:
    """Monotone and concave on the grid?  Violations are reported as findings, not repaired."""

    monotone: bool
    concave: bool
    max_monotonicity_violation: float
    max_concavity_violation: float


# --------------------------------------------------------------------------- construction
def utility_matrix(G: Any, nodes: Sequence[Zip], staff: Sequence[Rep], *,
                   theta: float, lam: float, filler_capture: str) -> np.ndarray:
    """`U[z, i]` in `td/channel.py::gain_matrix`'s **unmasked** convention (candidacy ignored).

    Verbatim in behaviour with `docs/artifacts/U1-cert/instance_numbers.py::utility_matrix`.
    `td/model.py::utilities` is the *masked* form (`0` where not a candidate) and is wrong here.
    """
    if filler_capture not in model.FILLER_CAPTURE:
        raise ValueError(f"filler_capture {filler_capture!r} not in {model.FILLER_CAPTURE}")
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    c_free = {"theta": c2, "full": c1, "opportunity": lam}[filler_capture]
    idx = {r: i for i, r in enumerate(staff)}
    U = np.zeros((len(nodes), len(staff)))
    for j, z in enumerate(nodes):
        S = model.books(G, z)
        T = float(sum(S.values()))
        U[j, :] = c2 * T + c_free * model.free_book(G, z) + lam * float(G.nodes[z]["M"])
        for r, s in S.items():
            i = idx.get(r)
            if i is not None:
                U[j, i] += (c1 - c2) * float(s)
    return U


def build_setting(G: Any, to_district: dict[Zip, District], sigma: Roster, *,
                  theta: float, lam: float, filler_capture: str) -> Setting:
    """Assemble `U`, `M`, the delivered gains and masses, and `delta_0`, from the committed map."""
    nodes = tuple(sorted(to_district))
    if set(nodes) != set(G):
        raise ValueError(f"the draw covers {len(nodes)} zips, the instance has {G.number_of_nodes()}")
    districts = tuple(channel.districts_from(to_district))
    missing = [d for d in districts if d not in sigma]
    if missing:
        raise ValueError(f"the roster does not staff districts {missing}")
    staff = tuple(sigma[d] for d in districts)

    U = utility_matrix(G, nodes, staff, theta=theta, lam=lam, filler_capture=filler_capture)
    M = np.array([float(G.nodes[z]["M"]) for z in nodes])
    jd = {d: j for j, d in enumerate(districts)}
    lab = np.array([jd[to_district[z]] for z in nodes], int)

    k = len(staff)
    g = np.array([U[lab == j, j].sum() for j in range(k)])
    m = np.array([M[lab == j].sum() for j in range(k)])
    target = float(M.sum()) / k
    return Setting(nodes=nodes, districts=districts, staff=staff, U=U, M=M,
                   V=float(math.fsum(math.log(v) for v in g)),
                   g_delivered=g, m_delivered=m,
                   delta0=float(np.abs(m - target).max() / target),
                   spread0=float((m.max() - m.min()) / m.mean()))


# --------------------------------------------------------------------------- the numbers
def gate(setting: Setting, *, reference: float | None = None,
         tol: float = GATE_TOL) -> dict[str, Any]:
    """Check the unconstrained `EG_S` against `V` before any frontier point.  Raises if it misses.

    `EG_S` is an upper bound on every band-feasible map's value and the delivered map is one such
    map, so `EG_S >= V` on any instance; the masked utility convention breaks it.  A `reference`
    additionally pins `EG_S` to a published number (v1 at k=13: `EG_S13_REFERENCE`).
    """
    sol = eg_band.solve_band(setting.U, setting.M, None)
    check = eg_band.check_dual(setting.U, setting.M, None, sol.X, sol.g, sol.duals)
    target = float(setting.M.sum()) / setting.k
    above_V = bool(sol.upper >= setting.V - tol)
    matches = reference is None or bool(abs(sol.upper - reference) <= tol
                                        and abs(sol.primal - reference) <= tol)
    out = dict(EG_S_upper=sol.upper, EG_S_primal=sol.primal, bracket=sol.bracket,
               reference=reference, gap_to_V=sol.upper - setting.V,
               delta_upper=None if reference is None else sol.upper - reference,
               n_cuts=sol.n_cuts, converged=sol.converged, status=sol.status,
               lp_tol=sol.lp_tol, dual_bound=check.bound,
               dual_feasible=check.feasible,
               dual_violation_rel=check.dual_violation_rel,
               cs_residual_rel=check.cs_residual_rel,
               M_max_dev_rel=float(np.abs(sol.m - target).max() / target),
               M_spread_rel=float((sol.m.max() - sol.m.min()) / sol.m.mean()),
               above_V=above_V, matches_reference=matches,
               passed=bool(above_V and matches))
    if not above_V:
        raise ValueError(
            f"utility-convention gate FAILED: unconstrained EG_S = [{sol.primal!r}, "
            f"{sol.upper!r}] is below the delivered V = {setting.V!r} "
            f"(gap {sol.upper - setting.V:.3e} nats, tolerance {tol:g}). EG_S bounds every "
            f"band-feasible map from above and the delivered map is one, so this cannot happen "
            f"with the right utilities: the masked convention lands at EG = 55.98 against "
            f"V = 59.9375 on v1, and so mimics a refutation of P1-band. Do not compute a "
            f"frontier point until this passes")
    if not matches and reference is not None:
        raise ValueError(
            f"gate reference MISSED: unconstrained EG_S = [{sol.primal!r}, {sol.upper!r}] "
            f"against --gate-reference {reference!r} (delta {sol.upper - reference:.3e} nats, "
            f"tolerance {tol:g}). The instance, the draw or the roster is not the one that "
            f"produced the reference")
    return out


def evaluate(setting: Setting, delta: float, *, cuts: np.ndarray | None,
             scip: bool, scip_time_limit: float = eg_band.SCIP_TIME_LIMIT
             ) -> tuple[Point, eg_band.BandSolution]:
    """One grid point; the solution carries the cut pool to carry to the next `delta`."""
    sol = eg_band.solve_band(setting.U, setting.M, delta, cuts=cuts)
    lo, hi = eg_band.band_rhs(setting.M, setting.k, delta)
    check = eg_band.check_dual(setting.U, setting.M, delta, sol.X, sol.g, sol.duals)
    vertex = eg_band.vertex_report(sol.X, setting.U, setting.M, sol.g, lo, hi)
    band = eg_band.solve_scip(setting.U, setting.M, delta, g_lower=sol.g * 0.5,
                              time_limit=scip_time_limit) if scip else None
    q = sol.duals.prices(setting.M)
    # U9 §10.D: a bound over an empty feasible set is true and useless.  No MILP is needed to
    # rule that out here -- the delivered draw is itself an integral coverage, and delta_0 is
    # defined as its own max deviation, so it witnesses non-emptiness at every delta >= delta_0.
    span = max(abs(hi), abs(lo), 1.0)
    witness = bool(setting.m_delivered.min() >= lo - 1e-9 * span
                   and setting.m_delivered.max() <= hi + 1e-9 * span)
    point = Point(
        delta=float(delta), upper=sol.upper, primal=sol.primal, bracket=sol.bracket,
        slope=sol.slope, slope_raw=sol.slope_raw,
        converged=sol.converged, n_cuts=sol.n_cuts, status=sol.status,
        m=sol.m, nu=sol.duals.nu,
        n_binding_upper=int((sol.duals.mu_plus > BIND_TOL).sum()),
        n_binding_lower=int((sol.duals.mu_minus > BIND_TOL).sum()),
        prop_gap=sol.g - setting.u_total / setting.k,
        p=sol.duals.p, q_min=float(q.min()), q_max=float(q.max()),
        integral_witness_in_band=witness,
        dual_check=check, vertex=vertex, scip=band)
    return point, sol


def softness(sol_at_delta0: eg_band.BandSolution, V: float,
             deltas: Sequence[float] = SPONSOR_DELTAS,
             solved: dict[float, float] | None = None) -> list[Softness]:
    """D1': `EG^bal(d0) + s_min(d0)(d - d0) - V <= 5e-3`?  A certificate, not a judgement call."""
    out = []
    for d in deltas:
        bound = sol_at_delta0.curve_bound(d)
        direct = None if solved is None else solved.get(float(d))
        out.append(Softness(
            delta=float(d), bound=bound, gap=bound - V,
            soft=bool(bound - V <= SMALL_NATS), direct=direct,
            slack=None if direct is None else bound - direct,
            tangent_valid=None if direct is None else bool(bound >= direct - TANGENT_TOL)))
    return out


def bisect_delta_star(setting: Setting, lo: float, hi: float, *,
                      lo_gap: float, hi_gap: float, cuts: np.ndarray | None,
                      digits: int = 3) -> DeltaStar:
    """Bisection is licensed by monotonicity of `EG^bal(delta) - V`, not by concavity."""
    if lo_gap > SMALL_NATS:
        return DeltaStar(value=float(lo), verdict=(
            f"delta* <= delta_0 = {lo:.4f}: the gap is already {lo_gap:.6f} nats at the left "
            f"endpoint, so no band on [delta_0, {hi:g}] makes the premium soft"),
            lo=float(lo), hi=float(lo), n_solves=0)
    if hi_gap <= SMALL_NATS:
        return DeltaStar(value=None,
                         verdict=f"none in [{lo:.4f}, {hi:g}]: the gap is still "
                                 f"{hi_gap:.6f} nats at the right endpoint",
                         lo=float(lo), hi=float(hi), n_solves=0)
    a, b, solves = float(lo), float(hi), 0
    width = 0.5 * 10.0 ** (-digits)
    while b - a > width:
        mid = 0.5 * (a + b)
        sol = eg_band.solve_band(setting.U, setting.M, mid, cuts=cuts)
        cuts = sol.cuts
        solves += 1
        if sol.upper - setting.V > SMALL_NATS:
            b = mid
        else:
            a = mid
    return DeltaStar(value=round(b, digits),
                     verdict=f"bracketed to [{a:.6f}, {b:.6f}] in {solves} solves",
                     lo=a, hi=b, n_solves=solves)


def shape(points: Sequence[Point]) -> Shape:
    """Check monotone and concave on the grid; report violations rather than fixing them."""
    d = np.array([p.delta for p in points], float)
    v = np.array([p.upper for p in points], float)
    order = np.argsort(d)
    d, v = d[order], v[order]
    mono = float(np.min(np.diff(v), initial=0.0))
    slopes = np.diff(v) / np.diff(d)
    conc = float(np.max(np.diff(slopes), initial=0.0)) if slopes.size > 1 else 0.0
    return Shape(monotone=bool(mono >= -SHAPE_TOL), concave=bool(conc <= SHAPE_TOL),
                 max_monotonicity_violation=float(min(mono, 0.0)),
                 max_concavity_violation=float(max(conc, 0.0)))


def movers(setting: Setting, sol: eg_band.BandSolution, *,
           top: int = 25) -> list[dict[str, Any]]:
    """The first-mover zips and their `M`-mass -- void if the support says the dual is degenerate.

    Ranked by `MODEL_U9-bandthm` P2.5's margin on `u_i(z)/g_i - nu_i M_z`, **not** by
    `DOMAIN_optimization` §2.12's published ratio `u_i(z)/q_zi`, which drops the `1/g_i` and is
    false already at `nu = 0`.
    """
    fm = eg_band.first_movers(setting.U, setting.M, sol.g, sol.duals)
    pick = fm.order[:top]
    return [dict(zip=setting.nodes[int(z)], margin=float(fm.margin[z]),
                 margin_abs=float(fm.margin_abs[z]), p=float(fm.best[z]),
                 M=float(setting.M[z]), M_share=float(setting.M[z] / setting.T),
                 owner=setting.staff[int(fm.owner[z])],
                 runner_up=setting.staff[int(fm.runner_up[z])])
            for z in pick]


# --------------------------------------------------------------------------- io
def sha256(path: str) -> str:
    """Hex digest of a file, for provenance."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_draw_dir(path: str) -> tuple[str, str]:
    """`(dir, label)` for either layout: `<dir>/draw.csv` or a single `<dir>/k<kk>/draw.csv`."""
    d = os.path.normpath(path)
    if not os.path.isfile(os.path.join(d, "draw.csv")):
        subs = sorted(s for s in os.listdir(d) if _K_DIR.match(s)
                      and os.path.isfile(os.path.join(d, s, "draw.csv")))
        if len(subs) != 1:
            raise ValueError(f"{path}: expected draw.csv, or exactly one k*/draw.csv "
                             f"subdirectory; found {subs}")
        d = os.path.join(d, subs[0])
    base = os.path.basename(d)
    label = (os.path.basename(os.path.dirname(os.path.abspath(d)))
             if _K_DIR.match(base) else base)
    return d, label


def read_draw(path: str) -> dict[Zip, District]:
    """`zip,district` -- the CSV `tools/run_draw.py` writes."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = csv.DictReader(fh)
        if rows.fieldnames != ["zip", "district"]:
            raise ValueError(f"{path}: header {rows.fieldnames}, expected ['zip', 'district']")
        return {r["zip"]: r["district"] for r in rows}


def read_metrics(path: str) -> dict[str, Any]:
    """The draw's `metrics.json`; `winner.gains` is absent on the seed-3 draw."""
    with open(path, encoding="utf-8") as fh:
        return dict(json.load(fh))


def solver_versions() -> dict[str, str]:
    """scipy / numpy / highspy / pyscipopt, for acceptance 5.  highspy has no `__version__`."""
    out = {}
    for name in ("scipy", "numpy", "highspy", "pyscipopt", "matplotlib"):
        try:
            out[name] = _md.version(name)
        except _md.PackageNotFoundError:
            out[name] = "absent"
    return out


def _jsonable(obj: Any) -> Any:
    """numpy and dataclass -> plain JSON, so `sort_keys=True` gives a byte-identical re-run.

    `ScipBound.seconds` is dropped: a wall time is a measurement of this machine, not of the
    instance, and it would make every re-run differ.  Timings go to `wall_seconds` beside
    `written`, and those two keys are the whole of the "modulo timestamp" in acceptance 5.
    """
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if hasattr(obj, "__dataclass_fields__"):
        return {f: _jsonable(getattr(obj, f)) for f in obj.__dataclass_fields__
                if not (isinstance(obj, eg_band.ScipBound) and f == "seconds")}
    return obj


def plot_frontier(setting: Setting, points: Sequence[Point], star: DeltaStar,
                  path: str) -> None:
    """The curve, always with the delivered MNW point and the unconstrained endpoint (trap 2)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = np.array([p.delta for p in points], float)
    v = np.array([p.certified_upper for p in points], float)
    order = np.argsort(d)
    d, v = d[order], v[order]
    target = setting.T / setting.k
    end = points[int(np.argmax([p.delta for p in points]))]
    end_spread = float((end.m.max() - end.m.min()) / end.m.mean())

    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=150)
    ax.plot(d, v, "-o", color="#31688e", lw=1.8, ms=4.5,
            label=(rf"$EG^{{bal}}_{{S_{{{setting.k}}}}}(\delta)$  "
                   r"(upper bound on every band-feasible map)"))
    ax.axhline(setting.V, color="#999999", lw=0.8, ls=":")
    ax.plot([setting.delta0], [setting.V], marker="*", ms=15, color="#d62728", ls="none",
            label=(f"delivered MNW draw  "
                   rf"$(\delta_0 = {setting.delta0:.4f},\ V = {setting.V:.4f})$"))
    ax.plot([end.delta], [end.certified_upper], marker="s", ms=7, color="#2ca02c", ls="none",
            label=(rf"unconstrained endpoint  $(\delta = {end.delta:g}$, "
                   rf"$EG_{{S_{{{setting.k}}}}} = {end.certified_upper:.4f})$"))
    ax.annotate(f"$M$-spread {end_spread:.0%}\nat the optimum",
                xy=(end.delta, end.certified_upper), xytext=(-8, -34),
                textcoords="offset points", ha="right", fontsize=8, color="#2ca02c")
    if star.value is not None:
        at_left = star.value <= setting.delta0 + 1e-12
        ax.axvline(star.value, color="#ff7f0e", lw=1.0, ls="--",
                   label=((rf"$\delta^* \leq \delta_0 = {star.value:.4f}$: the gap is already "
                           rf"{points[0].certified_upper - setting.V:.3f} nats here")
                          if at_left else
                          rf"$\delta^* = {star.value:.3f}$  (gap $> 5\times10^{{-3}}$ nats)"))
    ax.set_xlabel(r"band half-width $\delta$   (max deviation of $M(A_j)$ from $T/k$"
                  f" = {target:,.1f})")
    ax.set_ylabel(r"$\sum_i \log g_i$   (nats)")
    ax.set_title(rf"A1 U8-band: the band-constrained frontier at the roster $S_{{{setting.k}}}$")
    ax.legend(loc="lower right", fontsize=7.5, framealpha=0.95)
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("instance", help="instance_descaled.json.gz")
    ap.add_argument("draw", help="draw directory: <dir>/draw.csv or <dir>/k<kk>/draw.csv")
    ap.add_argument("--out", default=os.path.join(
        "battery", "results", f"u8_band_{_dt.date.today():%Y%m%d}"))
    ap.add_argument("--figure", default=os.path.join("figures", "u8_band", "frontier.png"))
    ap.add_argument("--theta", type=float, default=0.40)
    ap.add_argument("--lam", type=float, default=0.30)
    ap.add_argument("--filler-capture", default="theta")
    ap.add_argument("--no-scip", dest="scip", action="store_false", default=True)
    ap.add_argument("--scip-time-limit", type=float, default=eg_band.SCIP_TIME_LIMIT)
    ap.add_argument("--top-movers", type=int, default=25)
    ap.add_argument("--gate-reference", type=float, default=None,
                    help="pin the unconstrained EG_S to a published value to 1e-6 (v1 at k=13: "
                         f"{EG_S13_REFERENCE!r}); omitted, the gate checks only EG_S >= V")
    args = ap.parse_args(argv)

    draw_dir, label = resolve_draw_dir(args.draw)
    draw_csv = os.path.join(draw_dir, "draw.csv")
    to_district = read_draw(draw_csv)
    metrics = read_metrics(os.path.join(draw_dir, "metrics.json"))
    winner = dict(metrics.get("winner") or {})

    d = descaled.load_descaled(args.instance)
    print(f"instance: {d.summary()}")

    res = channel.stage2(d.G, to_district, reps_order=d.reps, theta=args.theta,
                         lam=args.lam, filler_capture=args.filler_capture)
    sigma: Roster = {str(k): str(v) for k, v in res["assignment"].items()}
    recorded = {str(k): str(v) for k, v in (winner.get("assignment") or {}).items()}
    if recorded and sorted(recorded.values()) != sorted(sigma.values()):
        raise ValueError(f"the re-run stage-2 roster {sorted(sigma.values())} is not the "
                         f"draw's recorded one {sorted(recorded.values())}")

    setting = build_setting(d.G, to_district, sigma, theta=args.theta, lam=args.lam,
                            filler_capture=args.filler_capture)
    if "stage2_value" in winner and abs(setting.V - float(winner["stage2_value"])) > 1e-9:
        raise ValueError(
            f"recomputed V {setting.V!r} != recorded winner.stage2_value "
            f"{winner['stage2_value']!r} (delta {setting.V - float(winner['stage2_value']):.3e}); "
            f"the roster, the map or the parameters are not the ones that produced the draw")

    print(f"draw: {label} ({draw_dir}), {len(setting.nodes):,} zips, k={setting.k}")
    print(f"V(delivered) = {setting.V:.12f}   (v1/k=13 reference {V_DELIVERED_REFERENCE})")
    print(f"delta_0 = {setting.delta0:.6f} (max deviation)   "
          f"spread = {setting.spread0:.6f}  -- the N7 grid uses the spread; this unit does not")

    print(f"\ngate: unconstrained EG_{{S{setting.k}}} in the unmasked utility convention")
    g_out = gate(setting, reference=args.gate_reference)
    ref = ("" if args.gate_reference is None else
           f"  vs reference {args.gate_reference!r}  delta {g_out['delta_upper']:.3e}")
    print(f"  [{g_out['EG_S_primal']:.12f}, {g_out['EG_S_upper']:.12f}]  "
          f"bracket {g_out['bracket']:.3e}  gap to V {g_out['gap_to_V']:+.6f}{ref}  PASS")
    print(f"  M max-dev at that optimum {g_out['M_max_dev_rel']:.4f}, "
          f"spread {g_out['M_spread_rel']:.4f}")

    grid = tuple(sorted({round(setting.delta0, 10), *GRID}))
    points: list[Point] = []
    sols: dict[float, eg_band.BandSolution] = {}
    cuts: np.ndarray | None = None
    print(f"\nfrontier on delta in {grid}")
    for delta in grid:
        want_scip = args.scip and any(abs(delta - s) < 1e-12 for s in SCIP_DELTAS)
        pt, sol = evaluate(setting, delta, cuts=cuts, scip=want_scip,
                           scip_time_limit=args.scip_time_limit)
        cuts = sol.cuts
        points.append(pt)
        sols[delta] = sol
        line = (f"  d={delta:<7.4f} EG^bal in [{pt.primal:.10f}, {pt.upper:.10f}] "
                f"br={pt.bracket:.2e} cuts={pt.n_cuts:>3d} s_min={pt.slope:>9.4f} "
                f"(raw {pt.slope_raw:.4f}) "
                f"gap-V={pt.certified_upper - setting.V:.6f} "
                f"bind +{pt.n_binding_upper}/-{pt.n_binding_lower} "
                f"dual{'OK' if pt.dual_check.feasible else 'BAD'} "
                f"viol={pt.dual_check.dual_violation_rel:.1e} "
                f"cs={pt.dual_check.cs_residual_rel:.1e}")
        if not pt.converged:
            line += f"  [{pt.status}]"
        print(line)
        v = pt.vertex
        print(f"      vertex: splits {v.n_split} (raw {v.n_split_raw}) vs cap k-1+t = "
              f"{v.split_cap}; t = {v.n_tight_bands} tight, {v.n_agents_band_slack} agents "
              f"slack, gauge {'pinned' if v.gauge_pinned else 'FREE'}; "
              f"rank {v.rank}/{v.n_support} {'vertex' if v.is_vertex else 'NOT a vertex'}; "
              f"clean cost g {v.clean_max_g_rel:.1e}, band {v.clean_max_band_violation:.1e}; "
              f"integral witness in band: {pt.integral_witness_in_band}")
        if pt.scip is not None:
            db = pt.scip.dual_bound
            agree = None if db is None else abs(db - pt.upper)
            print(f"      SCIP status={pt.scip.status} "
                  f"dual_bound={'NO BOUND' if db is None else f'{db:.10f}'} "
                  f"{'' if agree is None else f'|OA-SCIP|={agree:.2e} '}"
                  f"({pt.scip.seconds:.1f}s)")

    d0_sol = sols[grid[0]]
    solved = {p.delta: p.certified_upper for p in points}
    soft = softness(d0_sol, setting.V, solved=solved)
    print("\nD1' -- the one-solve concavity certificate from delta_0 "
          f"(EG^bal({grid[0]:.4f}) = {d0_sol.upper:.10f}, s_min = {d0_sol.slope:.6f})")
    for s in soft:
        print(f"  delta={s.delta:<5.2f} bound={s.bound:.8f}  bound - V = {s.gap:.8f} nats  "
              f"{'SOFT' if s.soft else 'NOT SOFT'} (floor {SMALL_NATS:g})"
              + ("" if s.direct is None else
                 f"  | direct {s.direct:.8f}, tangent slack {s.slack:+.2e} "
                 f"{'OK' if s.tangent_valid else 'INVALID SUPERGRADIENT'}"))
    if any(s.tangent_valid is False for s in soft):
        raise ValueError("s_min is not a supergradient: the tangent bound is violated at a "
                         "grid point, so it was under-minimised (VERIFY_U9-bandthm §10.A). "
                         "Reported, not tuned")
    verdict = ("soft across the whole plausible band: A1 collapses-on-softness"
               if all(s.soft for s in soft) else
               "not soft: the premium survives the band and A1 continues")
    print(f"  verdict: {verdict}")

    lo_pt, hi_pt = points[0], points[-1]
    star = bisect_delta_star(setting, lo_pt.delta, hi_pt.delta,
                             lo_gap=lo_pt.certified_upper - setting.V,
                             hi_gap=hi_pt.certified_upper - setting.V, cuts=cuts)
    print(f"\ndelta*: {star.verdict}")

    sh = shape(points)
    print(f"shape: monotone={sh.monotone} concave={sh.concave} "
          f"(worst violations {sh.max_monotonicity_violation:.2e} / "
          f"{sh.max_concavity_violation:.2e} nats)")

    star_delta = star.value if star.value is not None else hi_pt.delta
    star_sol = sols.get(star_delta) or eg_band.solve_band(setting.U, setting.M, star_delta,
                                                          cuts=cuts)
    star_support = eg_band.vertex_report(
        star_sol.X, setting.U, setting.M, star_sol.g,
        *eg_band.band_rhs(setting.M, setting.k, star_delta))
    first = movers(setting, star_sol, top=args.top_movers)
    fm = eg_band.first_movers(setting.U, setting.M, star_sol.g, star_sol.duals)
    n_tied = int((fm.margin <= 1e-12).sum())
    print(f"\nfirst movers at delta = {star_delta:g} "
          f"(support {star_support.n_support} vs expected {star_support.expected}, "
          f"{'DEGENERATE -- one dual optimum only' if star_support.degenerate else 'vertex'}; "
          f"{n_tied} zips are exact MBB ties, carrying "
          f"{setting.M[fm.margin <= 1e-12].sum() / setting.T:.2%} of T)")
    for row in first[:10]:
        print(f"  {row['zip']:>8}  margin {row['margin']:.3e} (abs {row['margin_abs']:.3e}, "
              f"p_z {row['p']:.5f})  M {row['M']:>8.3f} "
              f"({row['M_share']:.3%})  {row['owner']} -> {row['runner_up']}")
    print(f"  total M-mass of the top {len(first)}: "
          f"{sum(r['M'] for r in first):,.2f} ({sum(r['M_share'] for r in first):.2%} of T)")

    payload = dict(
        run_id=label,
        instance=os.path.abspath(args.instance),
        instance_sha256=sha256(args.instance),
        draw_dir=os.path.abspath(draw_dir),
        draw_sha256=sha256(draw_csv),
        theta=float(args.theta), lam=float(args.lam),
        filler_capture=str(args.filler_capture),
        solver_versions=solver_versions(),
        n_zips=len(setting.nodes), k=setting.k,
        T=setting.T, target=setting.T / setting.k,
        staff=list(setting.staff), districts=list(setting.districts),
        V_delivered=setting.V, gate_reference=args.gate_reference,
        V_reference_v1_k13=V_DELIVERED_REFERENCE,
        g_delivered=_jsonable(setting.g_delivered),
        m_delivered=_jsonable(setting.m_delivered),
        delta0=setting.delta0, spread0=setting.spread0,
        prop_gap_delivered=_jsonable(setting.g_delivered - setting.u_total / setting.k),
        u_total=_jsonable(setting.u_total),
        gate=_jsonable(g_out),
        grid=list(grid),
        points=[_jsonable(p) for p in points],
        certified_upper=[p.certified_upper for p in points],
        softness=[_jsonable(s) for s in soft],
        softness_verdict=verdict,
        delta_star=_jsonable(star),
        shape=_jsonable(sh),
        first_movers=dict(delta=float(star_delta), vertex=_jsonable(star_support),
                          n_exact_ties=n_tied,
                          tied_M_share=float(setting.M[fm.margin <= 1e-12].sum() / setting.T),
                          zips=_jsonable(first)),
        tier1=eg_band.CERT_TOL, tier2=SMALL_NATS,
        cross_check_tol=CROSS_TOL, clean_tol=eg_band.CLEAN_TOL,
        split_cap_2k_minus_1=2 * setting.k - 1,   # U9 P3-split, the -1 unconditional
        # the two non-reproducible keys; everything else is byte-identical on a re-run
        wall_seconds={f"scip@{p.delta:g}": p.scip.seconds for p in points
                      if p.scip is not None},
        written=_dt.datetime.now().isoformat(timespec="seconds"),
    )
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{label}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=float)
        fh.write("\n")
    print(f"\nwrote {path}")

    plot_frontier(setting, points, star, args.figure)
    print(f"wrote {args.figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
