"""master.py -- the support master (`docs/MODEL.md` §3–§5): per channel, the MILP, its decoding
into districts, the smallest δ and the solver report.

**The model** (`build`) is §3 row for row, in masses divided by τ_c so that the band is
[1 − δ, 1 + δ] whatever the extract's scale.  Variables are n_S ∈ ℤ≥0 per support of the closed
family 𝒮_c (`td.supports`) and t_{v,S} ∈ [0, 1] per unit of S.  Each row is kept by kind and key
(`Row`), so a test can find it, and the incumbent check reads the same rows:

    count        Σ_S n_S = K_c
    cover        Σ_{S∋v} t_{v,S} = 1                                   v ∈ V_c
    eta, share   η_c n_S ≤ t_{v,S} ≤ n_S                               v ∈ S
    band_lo/hi   (L + μ_S) n_S ≤ Σ_v M_v t_{v,S} ≤ (U − μ_S) n_S       §4.6
    hold         t_{v,S} = n_S, n_S ≤ 1: v whole, or clipped with |S| > 1
    contact      Σ_{S∋v} n_S ≤ cap_v                                   the spec's contact caps
    corridor     M_v t_{v,S} ≥ c_v(S) n_S, v a cut vertex of G[S]      §4.2, C6; n_S = 0 if c = ∞
    border       Σ_{S∋v, N(v)∩S={u}} n_S ≤ b_{uv}, free v, u ∈ N(v)    §4.3, C7
    count_cap    Σ_{S∋v} n_S ≤ |Z_v|                                   §4.4, C8

The Menger row (§4.5, C9) is optional and off by default in MODEL.md; it is not built here.  The
objective is Σ_S w_S n_S with w_S the support's diameter in km (§3.5).

**Solving** uses HiGHS directly (`highspy`), so the report carries the engine's own model status
(trap 15).  A certificate solve sets `mip_rel_gap` and `mip_abs_gap` to 0 (trap 12).  Tolerances
stay at HiGHS's defaults (trap 14), and `threads` is never set, so one process uses one thread
count (trap 18).  Every incumbent, whatever the status, is checked against the rows
(`violations`) before anything reads it: a validated incumbent is the only evidence of
feasibility.

**Decoding** (§3.1) expands each support with n_S ≥ 1 into copies with ȳ_{v,j} = t_{v,S} / n_S.
A unit's shares must sum to 1; a sum off by more than `FEAS_TOL` stops the run, and the solver's
float residual (≤ `FEAS_TOL`) goes onto the unit's largest t_{v,S}, never spread by rescaling
(S26).  There is no `other` district.

**The smallest δ** (§5 Claim 2, S10) is a property of the master, not of the ZIP map (C4):
- with whole and clipped units only, `exact_delta` minimises δ in one MILP: multi-unit supports
  and whole singletons are binary, and a clipped singleton picks k copies from
  {1, …, min(K_c, |Z_v|, ⌊1/η_c⌋, cap_v)} by binaries;
- with free units, `bisect_delta` bisects.  Each step solves the normal model with its objective
  kept (trap 19), and stops at its first incumbent (`mip_rel_gap` 1, the objective being ≥ 0),
  since a step asks only whether one exists.  A step is feasible with a validated incumbent,
  infeasible only when HiGHS proves it, and otherwise unknown; an unknown step stops the search
  and is reported, never read as infeasible (C4).
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field

import highspy
import numpy as np

from td import audit, supports

FEAS_TOL = 1e-6         # an incumbent's rows, in shares and τ-normalised masses; HiGHS's own is 1e-7
INT_TOL = 1e-6          # how far an integer variable may sit from an integer
DELTA_TOL = 1e-4        # bisection stops when the bracket is this narrow
SCOPE = "a property of the master (C4): it says nothing about drawing the plan on ZIPs"


class MasterError(RuntimeError):
    """A solve or a decode that must stop the run."""


# ------------------------------------------------------------------------------ the model
@dataclass
class Row:
    kind: str
    key: tuple
    coef: dict                  # column -> coefficient
    lo: float
    hi: float


@dataclass
class Model:
    channel: str
    delta: float
    supports: tuple             # 𝒮_c, in the family's order
    n_col: dict                 # S -> column of n_S
    t_col: dict                 # (v, S) -> column of t_{v,S}
    cost: list
    lower: list
    upper: list
    integer: list               # bool per column
    rows: list = field(default_factory=list)

    def rows_of(self, kind: str) -> dict:
        return {r.key: r for r in self.rows if r.kind == kind}


def _add_col(model: Model, cost: float, lo: float, hi: float, integer: bool) -> int:
    model.cost.append(cost)
    model.lower.append(lo)
    model.upper.append(hi)
    model.integer.append(integer)
    return len(model.cost) - 1


def build(inst, channel: str, delta: float | None = None, fam=None) -> Model:
    """The §3 master of `channel` at δ (the channel's planning δ when None)."""
    ch = inst.channels[channel]
    cs = ch.spec
    fam = supports.family(inst, channel) if fam is None else fam
    delta = cs.delta if delta is None else float(delta)
    tau = ch.tau
    lo_band, hi_band = 1.0 - delta, 1.0 + delta
    model = Model(channel, delta, fam.supports, {}, {}, [], [], [], [])
    held = {}                   # S -> True when some unit of S is held whole in it
    for s in fam.supports:
        held[s] = any(ch.mode[v] == "whole" or (ch.mode[v] == "clipped" and len(s) > 1)
                      for v in s)
        model.n_col[s] = _add_col(model, supports.diameter(inst, s), 0.0,
                                  1.0 if held[s] else float(cs.k), True)
        for v in sorted(s):
            model.t_col[v, s] = _add_col(model, 0.0, 0.0, 1.0, False)
    rows = model.rows
    rows.append(Row("count", (), {model.n_col[s]: 1.0 for s in fam.supports}, cs.k, cs.k))
    for v in ch.units:
        rows.append(Row("cover", (v,), {c: 1.0 for (u, s), c in model.t_col.items() if u == v},
                        1.0, 1.0))
    for s in fam.supports:
        n = model.n_col[s]
        mu = supports.margin(inst, channel, s) / tau
        for v in sorted(s):
            t = model.t_col[v, s]
            rows.append(Row("eta", (v, s), {t: 1.0, n: -cs.eta}, 0.0, math.inf))
            rows.append(Row("share", (v, s), {t: 1.0, n: -1.0}, -math.inf, 0.0))
            if ch.mode[v] == "whole" or (ch.mode[v] == "clipped" and len(s) > 1):
                rows.append(Row("hold", (v, s), {t: 1.0, n: -1.0}, 0.0, 0.0))
        mass = {model.t_col[v, s]: ch.M[v] / tau for v in sorted(s)}
        rows.append(Row("band_lo", (s,), {**mass, n: -(lo_band + mu)}, 0.0, math.inf))
        rows.append(Row("band_hi", (s,), {**mass, n: -(hi_band - mu)}, -math.inf, 0.0))
    for v, cap in sorted(cs.contact_caps.items()):
        if v in ch.M:
            rows.append(Row("contact", (v,), {model.n_col[s]: 1.0 for s in fam.supports if v in s},
                            -math.inf, float(cap)))
    for (s, v), c in supports.corridor_floors(inst, fam).items():
        n = model.n_col[s]
        if math.isinf(c):
            rows.append(Row("corridor", (s, v), {n: 1.0}, -math.inf, 0.0))
        else:
            rows.append(Row("corridor", (s, v), {model.t_col[v, s]: ch.M[v] / tau, n: -c / tau},
                            0.0, math.inf))
    for (u, v), (b, over) in supports.border_rows(inst, fam).items():
        if over:
            rows.append(Row("border", (u, v), {model.n_col[s]: 1.0 for s in over},
                            -math.inf, float(b)))
    for v in ch.units:
        rows.append(Row("count_cap", (v,), {model.n_col[s]: 1.0 for s in fam.supports if v in s},
                        -math.inf, float(len(inst.units.zips[v]))))
    return model


# ------------------------------------------------------------------------------ solving
@dataclass
class Solution:
    status: str                 # HiGHS's model status: optimal, infeasible, time limit, ...
    x: list | None              # the incumbent, None without one
    objective: float | None
    bound: float | None
    mip_rel_gap: float
    time_s: float

    def report(self) -> dict:
        """The per-channel solver report `td.audit` reads (OD3): status, objective, bound, gap,
        mip_rel_gap.  The gap is HiGHS's relative gap (objective − bound) / |objective|, written 0
        when the bound is within `audit.allowance` of the objective."""
        obj, bound = self.objective, self.bound
        gap = None
        if obj is not None and bound is not None:
            gap = 0.0 if obj - bound <= audit.allowance(obj) else audit.actual_gap(obj, bound)
        return {"status": self.status, "objective": obj, "bound": bound, "gap": gap,
                "mip_rel_gap": self.mip_rel_gap, "time_s": round(self.time_s, 3)}


_STATUS = {highspy.HighsModelStatus.kOptimal: "optimal",
           highspy.HighsModelStatus.kInfeasible: "infeasible",
           highspy.HighsModelStatus.kTimeLimit: "time limit"}


def _highs_lp(cost, lower, upper, integer, rows) -> highspy.HighsLp:
    lp = highspy.HighsLp()
    lp.num_col_, lp.num_row_ = len(cost), len(rows)
    lp.col_cost_ = np.array(cost, dtype=float)
    lp.col_lower_ = np.array(lower, dtype=float)
    lp.col_upper_ = np.array(upper, dtype=float)
    inf = highspy.kHighsInf
    lp.row_lower_ = np.array([max(r.lo, -inf) for r in rows], dtype=float)
    lp.row_upper_ = np.array([min(r.hi, inf) for r in rows], dtype=float)
    cols: list = [[] for _ in cost]
    for i, r in enumerate(rows):
        for c, a in r.coef.items():
            if a != 0.0:
                cols[c].append((i, a))
    start, index, value = [0], [], []
    for entries in cols:
        for i, a in entries:
            index.append(i)
            value.append(a)
        start.append(len(index))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.array(start, dtype=np.int32)
    lp.a_matrix_.index_ = np.array(index, dtype=np.int32)
    lp.a_matrix_.value_ = np.array(value, dtype=float)
    lp.integrality_ = [highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous
                       for i in integer]
    return lp


def _run(cost, lower, upper, integer, rows, mip_rel_gap: float, time_limit: float | None) -> Solution:
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("mip_rel_gap", float(mip_rel_gap))
    if mip_rel_gap == 0:
        h.setOptionValue("mip_abs_gap", 0.0)
    if time_limit is not None:
        h.setOptionValue("time_limit", float(time_limit))
    h.passModel(_highs_lp(cost, lower, upper, integer, rows))
    t0 = time.time()
    h.run()
    elapsed = time.time() - t0
    ms = h.getModelStatus()
    status = _STATUS.get(ms) or h.modelStatusToString(ms).lower()
    info = h.getInfo()
    x = obj = bound = None
    if info.primal_solution_status == highspy.kSolutionStatusFeasible:
        x = list(h.getSolution().col_value)
        obj = float(info.objective_function_value)
        bound = float(info.mip_dual_bound)
        bound = min(bound, obj) if math.isfinite(bound) else None
    return Solution(status, x, obj, bound, float(mip_rel_gap), elapsed)


def violations(model_or_rows, x, lower=None, upper=None, integer=None, tol: float = FEAS_TOL) -> list:
    """(kind, key, excess) for every row, bound or integrality `x` breaks by more than `tol`."""
    if isinstance(model_or_rows, Model):
        m = model_or_rows
        rows, lower, upper, integer = m.rows, m.lower, m.upper, m.integer
    else:
        rows = model_or_rows
    out = []
    for c, v in enumerate(x):
        if v < lower[c] - tol or v > upper[c] + tol:
            out.append(("bound", (c,), v))
        if integer[c] and abs(v - round(v)) > INT_TOL:
            out.append(("integer", (c,), v))
    for r in rows:
        a = math.fsum(k * x[c] for c, k in r.coef.items())
        excess = max(r.lo - a, a - r.hi)
        if excess > tol:
            out.append((r.kind, r.key, excess))
    return out


def solve(model: Model, mip_rel_gap: float = 0.0, time_limit: float | None = None) -> Solution:
    """Solve the model.  An incumbent that breaks a row stops the run: a status never vouches for
    a point the rows reject."""
    sol = _run(model.cost, model.lower, model.upper, model.integer, model.rows,
               mip_rel_gap, time_limit)
    if sol.x is not None:
        bad = violations(model, sol.x)
        if bad:
            raise MasterError(f"channel {model.channel}: HiGHS ({sol.status}) returned an incumbent "
                              f"that breaks {len(bad)} rows, e.g. {bad[:3]}")
    return sol


# ------------------------------------------------------------------------------ decoding
@dataclass
class Copy:
    """One district: copy r of support S, with planned shares ȳ_{v,j} and masses a_{v,j}."""
    support: frozenset
    r: int
    share: dict                 # v -> ȳ_{v,j}
    mass: dict                  # v -> a_{v,j} = M_v ȳ_{v,j}

    @property
    def name(self) -> str:
        return f"{'+'.join(sorted(self.support))}#{self.r}"

    @property
    def total(self) -> float:
        return math.fsum(self.mass.values())


@dataclass
class Plan:
    channel: str
    delta: float
    n: dict                     # S -> n_S, the supports in use
    t: dict                     # (v, S) -> t_{v,S}, for the supports in use
    copies: list
    objective: float
    report: dict


def decode(inst, model: Model, x) -> tuple:
    """(n, t, copies) from a validated incumbent (§3.1).  A unit whose shares do not sum to 1
    within FEAS_TOL stops the run; the float residual within it goes onto the unit's largest
    t_{v,S}.  Held units get t = n exactly."""
    ch = inst.channels[model.channel]
    n = {}
    for s, c in model.n_col.items():
        k = round(x[c])
        if abs(x[c] - k) > INT_TOL:
            raise MasterError(f"channel {model.channel}: n_S = {x[c]} for {sorted(s)} is not an integer")
        if k >= 1:
            n[s] = int(k)
    t = {}
    for (v, s), c in model.t_col.items():
        if s in n:
            held = ch.mode[v] == "whole" or (ch.mode[v] == "clipped" and len(s) > 1)
            t[v, s] = float(n[s]) if held else min(max(x[c], 0.0), float(n[s]))
    for v in ch.units:
        mine = sorted(((val, sorted(s)) for (u, s), val in t.items() if u == v), reverse=True)
        total = math.fsum(val for val, _ in mine)
        if not mine or abs(total - 1.0) > FEAS_TOL:
            raise MasterError(f"channel {model.channel}: unit {v}'s shares sum to {total}, not 1")
        top = frozenset(mine[0][1])
        t[v, top] = 1.0 - math.fsum(val for (u, s), val in t.items() if u == v and s != top)
    copies = []
    for s in model.supports:
        for r in range(1, n.get(s, 0) + 1):
            share = {v: t[v, s] / n[s] for v in sorted(s)}
            copies.append(Copy(s, r, share, {v: ch.M[v] * y for v, y in share.items()}))
    if len(copies) != ch.k:
        raise MasterError(f"channel {model.channel}: {len(copies)} copies, K = {ch.k}")
    return n, t, copies


def plan(inst, channel: str, delta: float | None = None, fam=None, mip_rel_gap: float = 0.0,
         time_limit: float | None = None) -> tuple:
    """(Plan or None, solver report): the channel's master solved at δ and decoded.  The plan is
    None when HiGHS ends without an incumbent; the report says why."""
    model = build(inst, channel, delta, fam)
    sol = solve(model, mip_rel_gap, time_limit)
    if sol.x is None:
        return None, sol.report()
    n, t, copies = decode(inst, model, sol.x)
    return Plan(channel, model.delta, n, t, copies, sol.objective, sol.report()), sol.report()


def plan_all(inst, mip_rel_gap: float = 0.0, time_limit: float | None = None) -> tuple:
    """({channel: Plan or None}, {channel: solver report}) for every channel solved."""
    plans, reports = {}, {}
    for c in inst.channels:
        plans[c], reports[c] = plan(inst, c, mip_rel_gap=mip_rel_gap, time_limit=time_limit)
    return plans, reports


# ------------------------------------------------------------------------------ smallest δ
@dataclass
class Delta:
    """The smallest δ at which the master is feasible (§5 Claim 2), `SCOPE`.

    `delta` is the smallest δ shown feasible, `lower` the largest shown infeasible (exact: equal
    to `delta`).  `status` is exact, converged (the bracket is within `tol`), unknown (a step or
    the exact solve ended without a verdict; the bracket stands) or infeasible (no δ works)."""
    channel: str
    method: str                 # exact | bisection
    status: str
    delta: float | None
    lower: float | None
    tol: float
    steps: list = field(default_factory=list)      # (δ, verdict, solver report)
    report: dict | None = None
    scope: str = SCOPE


def _k_range(inst, ch, v) -> range:
    cs = ch.spec
    top = min(cs.k, len(inst.units.zips[v]), math.floor(1.0 / cs.eta + 1e-12),
              cs.contact_caps.get(v, cs.k))
    return range(1, top + 1)


def exact_delta(inst, channel: str, fam=None, time_limit: float | None = None) -> Delta:
    """The exact δ-MILP of Claim 2 for a channel with whole and clipped units only."""
    ch = inst.channels[channel]
    if any(ch.mode[v] == "free" for v in ch.units):
        raise MasterError(f"channel {channel}: free units need bisection (Claim 2)")
    fam = supports.family(inst, channel) if fam is None else fam
    tau, cs = ch.tau, ch.spec
    floors = supports.corridor_floors(inst, fam)
    cost, lower, upper, integer, rows = [1.0], [0.0], [math.inf], [False], []   # column 0 is δ
    cols, coef, units_of, copies_of = {}, {}, {}, {}

    def binary(key, s, k, c, blocked=False):
        cols[key], coef[key], units_of[key], copies_of[key] = len(cost), c, s, k
        cost.append(0.0)
        lower.append(0.0)
        upper.append(0.0 if blocked else 1.0)
        integer.append(True)

    for s in fam.supports:
        mu = supports.margin(inst, channel, s)
        if len(s) == 1 and ch.mode[next(iter(s))] == "clipped":
            v = next(iter(s))
            for k in _k_range(inst, ch, v):         # k copies of {v}, M_v / k each
                binary((s, k), s, k, (abs(ch.M[v] / k - tau) + mu) / tau)
        else:                                       # every unit held: t = n ∈ {0, 1}
            mass = math.fsum(ch.M[v] for v in s)
            blocked = any(ch.M[v] < floors[s, v] for v in s if (s, v) in floors)
            binary((s, 1), s, 1, (abs(mass - tau) + mu) / tau, blocked)
    rows.append(Row("count", (), {c: float(copies_of[key]) for key, c in cols.items()}, cs.k, cs.k))
    for v in ch.units:
        rows.append(Row("cover", (v,), {c: 1.0 for key, c in cols.items() if v in units_of[key]},
                        1.0, 1.0))
        touch = {c: float(copies_of[key]) for key, c in cols.items() if v in units_of[key]}
        if v in cs.contact_caps:
            rows.append(Row("contact", (v,), touch, -math.inf, float(cs.contact_caps[v])))
        rows.append(Row("count_cap", (v,), touch, -math.inf, float(len(inst.units.zips[v]))))
    for key, c in cols.items():
        rows.append(Row("delta", key, {0: 1.0, c: -coef[key]}, 0.0, math.inf))
    sol = _run(cost, lower, upper, integer, rows, 0.0, time_limit)
    if sol.x is not None:
        bad = violations(rows, sol.x, lower, upper, integer)
        if bad:
            raise MasterError(f"channel {channel}: the δ-MILP incumbent breaks {bad[:3]}")
    rep = sol.report()
    if sol.status == "infeasible":
        return Delta(channel, "exact", "infeasible", None, None, 0.0, report=rep)
    if sol.x is None:
        return Delta(channel, "exact", "unknown", None, None, 0.0, report=rep)
    chosen = [key for key, c in cols.items() if round(sol.x[c]) == 1]
    delta = max(coef[key] for key in chosen)      # δ from the chosen binaries, not the float
    if sol.status == "optimal":
        return Delta(channel, "exact", "exact", delta, delta, 0.0, report=rep)
    return Delta(channel, "exact", "unknown", delta, sol.bound, 0.0, report=rep)


def step(inst, channel: str, delta: float, fam=None, mip_rel_gap: float = 1.0,
         time_limit: float | None = None) -> tuple:
    """(verdict, report) for the master at δ, objective kept (trap 19): feasible with a validated
    incumbent, infeasible when HiGHS proves it, else unknown (C4).  The step asks only for an
    incumbent, so its default gap stops at the first one."""
    sol = solve(build(inst, channel, delta, fam), mip_rel_gap, time_limit)
    if sol.x is not None:
        return "feasible", sol.report()
    return ("infeasible" if sol.status == "infeasible" else "unknown"), sol.report()


def delta_top(inst, channel: str, fam) -> float:
    """A δ at which the band rows bind no plan: U − μ_S reaches the channel's whole mass and
    L + μ_S falls to 0 for every support."""
    ch = inst.channels[channel]
    mu = max(supports.margin(inst, channel, s) for s in fam.supports) / ch.tau
    return max(ch.k - 1.0, 1.0) + mu + 1e-9


def bisect_delta(inst, channel: str, fam=None, tol: float = DELTA_TOL,
                 time_limit: float | None = None, mip_rel_gap: float = 1.0) -> Delta:
    """Bisect on δ with the normal model (Claim 2).  δ is probed at the channel's planning δ, then
    at 0 or at `delta_top`, then halved until the bracket is within `tol`.  An unknown step stops
    the search: the bracket so far is the answer, and the status says unknown."""
    ch = inst.channels[channel]
    fam = supports.family(inst, channel) if fam is None else fam
    steps = []

    def probe(d):
        verdict, rep = step(inst, channel, d, fam, mip_rel_gap, time_limit)
        steps.append((d, verdict, rep))
        return verdict

    def result(status, hi, lo):
        return Delta(channel, "bisection", status, hi, lo, tol, steps)

    lo, hi = None, None
    first = ch.spec.delta
    v = probe(first)
    if v == "unknown":
        return result("unknown", None, None)
    if v == "feasible":
        hi = first
        v0 = probe(0.0)
        if v0 == "feasible":
            return result("converged", 0.0, None)
        if v0 == "unknown":
            return result("unknown", hi, None)
        lo = 0.0
    else:
        lo = first
        top = delta_top(inst, channel, fam)
        vt = probe(top)
        if vt == "infeasible":
            return result("infeasible", None, top)
        if vt == "unknown":
            return result("unknown", None, lo)
        hi = top
    while hi - lo > tol:
        mid = (lo + hi) / 2
        v = probe(mid)
        if v == "unknown":
            return result("unknown", hi, lo)
        if v == "feasible":
            hi = mid
        else:
            lo = mid
    return result("converged", hi, lo)


def smallest_delta(inst, channel: str, fam=None, tol: float = DELTA_TOL,
                   time_limit: float | None = None) -> Delta:
    """Exact when the channel has no free unit, else bisection (Claim 2)."""
    ch = inst.channels[channel]
    if any(ch.mode[v] == "free" for v in ch.units):
        return bisect_delta(inst, channel, fam, tol, time_limit)
    return exact_delta(inst, channel, fam, time_limit)


# ------------------------------------------------------------------------------ the report
def write_report(path: str, reports: dict, deltas: dict | None = None) -> str:
    """`solver.json`: per channel, the solver report `td.audit` reads, and the smallest δ with
    its method, bracket, steps and scope (C4)."""
    out = {}
    for c, rep in reports.items():
        out[c] = {"solver": rep}
        d = (deltas or {}).get(c)
        if d is not None:
            out[c]["smallest_delta"] = {
                "method": d.method, "status": d.status, "delta": d.delta, "lower": d.lower,
                "tol": d.tol, "scope": d.scope,
                "steps": [{"delta": x, "verdict": v, "solver": r} for x, v, r in d.steps],
                **({"solver": d.report} if d.report else {})}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path
