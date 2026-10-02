"""hess.py -- #81's Hess-style ZIP planner (experimental; not a production planner).

The comparison arm of #81: a channel's districts chosen at ZIP grain by the Hess objective

    min Σ_z Σ_j M_z ‖p_z − c_j‖² x_zj

with balance constrained, never traded.  It is a separate planner, not a support-master
objective: the support master decides (n_S, t_{v,S}) at unit grain and never sees a ZIP, so a
ZIP-grain objective cannot sit in it without changing its decision grain (#81 "Be explicit
about architecture").  The output is a ZIP map, so the realizer's centres, transport LP and
tree rounding have no job here; its zero-mass placement, its repair pass (S23), its piece causes,
and the ledger and audit of `td.output` are reused unchanged by `run_hess.py`.

**Items.**  A whole unit is one item: all its ZIPs go together, and its cost at a centre c is
M_v ‖p̄_v − c‖² + I_v, with p̄_v its opportunity-weighted centroid and I_v = Σ_{z∈v} M_z ‖p_z − p̄_v‖²
its inertia, so the item's cost is exactly the sum of its ZIPs' costs.  Each ZIP with m_z > 0 of a
free unit is its own item.  Zero-mass ZIPs carry no cost; a whole unit's go with it, and a free
unit's are placed afterwards by `td.realize.place_zero`.  No clipped units or metros occur in the
#81 scenario; `items` refuses them rather than guess their policy.

**The assignment MILP at fixed centres** (`build`).  Binaries x_{ij} (item i to district j) and,
per free unit v, y_{vj} (district j touches v).  u_{vj} is x_{ij} for a whole unit's item and
y_{vj} for a free unit:

    assign     Σ_j x_ij = 1                                        every item
    band       L ≤ Σ_i m_i x_ij ≤ U                                every district
    link       x_ij ≤ y_vj                                         i a ZIP of free v
    eta        Σ_{i∈v} m_i x_ij ≥ η_c M_v y_vj                     free v
    size       Σ_v u_vj ≤ s̄_c                                       every district
    dist       u_aj + u_bj ≤ 1                                     d(a, b) > R_c(a, b)
    eta_cap    Σ_j y_vj ≤ ⌊1/η_c⌋                                   free v
    contact    Σ_j u_vj ≤ cap_v                                    the spec's contact caps
    connect    u_aj + u_bj − 1 ≤ Σ_{w∈N(C)} u_wj                     separator cuts

The rows hold the support family's rules on each district's unit set S = {v : u_vj = 1}: |S| ≤
s̄_c, the pairwise distance cap, and G[S] connected (`td.supports`, MODEL §2), plus the master's
η, ⌊1/η⌋ and contact rows (§3).  Connectivity is enforced by separator cuts: N(C), the
neighbours of a set C in G[V_c], separates C from every unit outside C ∪ N(C).  `build` adds the
cuts with C = {a} for every pair (a, b) inside the distance cap and not adjacent; a solution whose
S_j is still disconnected gets, for each component C and a unit b of S_j outside it, the cut with
a ∈ C, for every district, and the solve is repeated (`connected_solve`).  A single-commodity
flow formulation of the same rule was tried and found no incumbent on FI in 300 s.  The master's
corridor floor, border cap, count cap and rounding margin (§4) are drawability devices for a plan
that is drawn later; this plan is drawn already, and they are not built.  ZIP contiguity is not a
row, in this arm or the support arm.

**Centres** (location–allocation, the archived MODEL §8 Lloyd loop).  The seed is
`td.realize.kmeans` on the channel's positive ZIPs, deterministic.  It ignores the band, and the
MILP at it finds no incumbent on FI in 300 s, so the loop first runs on the MILP's LP relaxation
(`relaxed_centres`), which moves the centres in seconds.  A first assignment at those centres
(`start_assignment`, iteration −1) moves them to its centroids.  Each iteration then solves the
assignment MILP at the current centres to `mip_rel_gap` 0, warm-started from the previous
assignment (the rows do not depend on the centres, so it stays feasible and the objective never
rises), then moves each centre to its district's opportunity-weighted centroid.  The loop stops
when the assignment repeats, or at the iteration or time cap.  The result is a local optimum of
the Hess objective: each iteration is certified at its own centres when its MILP ends optimal,
and nothing bounds the objective over all centres.  The first assignment comes from the same
MILP with each item restricted to its few cheapest districts, widened until one is found; every
later MILP is unrestricted.

Costs are in m_rel · km², the masses in m_rel; the MILP runs on costs over their mean and masses
over τ_c.  HiGHS runs with `threads` fixed per process (trap 18), `mip_rel_gap` and `mip_abs_gap`
0 (trap 12), and its own model status keys every report (trap 15).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import highspy
import numpy as np

from td import realize, supports
from td.master import FEAS_TOL, INT_TOL, eta_cap

TIME_LIMIT = 900.0          # seconds for one assignment MILP
MAX_ITERS = 30              # location–allocation iterations
TOTAL_LIMIT = 3 * 3600.0    # seconds for the whole loop of one channel
THREADS = 4                 # HiGHS threads, one value per process (trap 18); None: HiGHS default
NEAREST = (3, 5, 8, 12, 24) # the first warm start's candidate districts per item, widened in turn
START_LIMIT = 120.0         # seconds for one restricted MILP of the first warm start
RELAXED_ITERS = 50          # LP-relaxed location–allocation rounds before the first MILP
RELAXED_MOVE_KM = 1.0       # ... until no centre moves farther


class HessError(RuntimeError):
    """The planner cannot go on."""


@dataclass
class Item:
    unit: str
    zips: tuple                 # the ZIPs it places: a whole unit's all, a free ZIP itself
    mass: float
    centre: tuple               # opportunity-weighted centroid, km
    inertia: float              # Σ m_z ‖p_z − centre‖² over its ZIPs


@dataclass
class Model:
    channel: str
    items: list
    k: int
    x_col: dict                 # (i, j) -> column
    y_col: dict                 # (v, j) -> column, free v
    lower: list
    upper: list
    integer: list               # bool per column
    rows: list                  # (coef {col: a}, lo, hi, kind)
    cuts: list = field(default_factory=list)    # (a, b, separator) units
    upfront: int = 0                            # how many of `cuts` `build` added

    @property
    def ncols(self) -> int:
        return len(self.lower)

    def touch(self, v: str, j: int, unit_items: dict) -> int:
        """The column of u_vj."""
        return self.y_col[v, j] if (v, j) in self.y_col else self.x_col[unit_items[v][0], j]


def positions(inst) -> dict:
    """{zip: (x_km, y_km)} for the instance's placed ZIPs, as `td.realize.realize` reads them."""
    from td import geo
    ref = geo.read_reference().set_index("zcta").loc[sorted(inst.units.unit_of)]
    return {z: (float(x) / 1000.0, float(y) / 1000.0) for z, x, y in zip(ref.index, ref["x"], ref["y"])}


def items(inst, channel: str, p: dict) -> list:
    """The channel's items, whole units first (by name), then free ZIPs (by unit, ZIP)."""
    ch, units = inst.channels[channel], inst.units
    other = sorted(v for v in ch.units if ch.mode[v] not in ("whole", "free"))
    if other:
        raise HessError(f"channel {channel}: units {other} are neither whole nor free; "
                        "the Hess arm has no rule for their mode")
    out = []
    for v in sorted(ch.units):
        if ch.mode[v] == "whole":
            zs = units.zips[v]
            c = realize.centroid([z for z in zs if ch.m[z] > 0], ch.m, p)
            out.append(Item(v, zs, ch.M[v], c,
                            math.fsum(ch.m[z] * realize._d2(p[z], c) for z in zs)))
    for v in sorted(ch.units):
        if ch.mode[v] == "free":
            out += [Item(v, (z,), ch.m[z], p[z], 0.0) for z in units.zips[v] if ch.m[z] > 0]
    return out


def cost(item: Item, c: tuple) -> float:
    """Σ_{z∈item} m_z ‖p_z − c‖², exact by the parallel-axis rule."""
    return item.mass * realize._d2(item.centre, c) + item.inertia


def incompatible(inst, channel: str) -> list:
    """Unit pairs (a, b), a < b, beyond the channel's distance cap R_c(a, b)."""
    ch = inst.channels[channel]
    us = sorted(ch.units)
    return [(a, b) for i, a in enumerate(us) for b in us[i + 1:]
            if inst.units.distance_km(a, b) > ch.spec.dist_cap(a, b)]


def unit_items(its: list) -> dict:
    out: dict = {}
    for i, it in enumerate(its):
        out.setdefault(it.unit, []).append(i)
    return out


def build(inst, channel: str, its: list, band: tuple) -> Model:
    """The assignment MILP's columns and rows, without the objective (it depends on the centres).
    `band` is (L, U) in m_rel."""
    ch, cs = inst.channels[channel], inst.channels[channel].spec
    k, tau = ch.k, ch.tau
    ui = unit_items(its)
    free = sorted(v for v in ch.units if ch.mode[v] == "free")
    m = Model(channel, its, k, {}, {}, [], [], [], [])

    def col(hi=1.0, integer=True):
        m.lower.append(0.0)
        m.upper.append(hi)
        m.integer.append(integer)
        return len(m.lower) - 1

    for i in range(len(its)):
        for j in range(k):
            m.x_col[i, j] = col()
    for v in free:
        for j in range(k):
            m.y_col[v, j] = col()
    rows = m.rows
    for i in range(len(its)):
        rows.append(({m.x_col[i, j]: 1.0 for j in range(k)}, 1.0, 1.0, "assign"))
    lo, hi = band[0] / tau, band[1] / tau
    for j in range(k):
        rows.append(({m.x_col[i, j]: it.mass / tau for i, it in enumerate(its)}, lo, hi, "band"))
    for v in free:
        for j in range(k):
            y = m.y_col[v, j]
            for i in ui[v]:
                rows.append(({m.x_col[i, j]: 1.0, y: -1.0}, -math.inf, 0.0, "link"))
            coef = {m.x_col[i, j]: its[i].mass / tau for i in ui[v]}
            coef[y] = -cs.eta * ch.M[v] / tau
            rows.append((coef, 0.0, math.inf, "eta"))
    for j in range(k):
        rows.append(({m.touch(v, j, ui): 1.0 for v in ch.units}, -math.inf, float(cs.max_size), "size"))
    for a, b in incompatible(inst, channel):
        for j in range(k):
            rows.append(({m.touch(a, j, ui): 1.0, m.touch(b, j, ui): 1.0}, -math.inf, 1.0, "dist"))
    for v in free:
        rows.append(({m.y_col[v, j]: 1.0 for j in range(k)}, -math.inf, float(eta_cap(cs.eta)), "eta_cap"))
    for v, cap in sorted(cs.contact_caps.items()):
        if v in ch.M:
            rows.append(({m.touch(v, j, ui): 1.0 for j in range(k)}, -math.inf, float(cap), "contact"))
    adj = supports.unit_graph(inst, channel)
    far = set(incompatible(inst, channel))
    for a in sorted(ch.units):
        for b in sorted(ch.units):
            if a != b and b not in adj[a] and (min(a, b), max(a, b)) not in far:
                add_cut(m, inst, a, b, frozenset(adj[a]), ui)
    m.upfront = len(m.cuts)
    return m


def add_cut(m: Model, inst, a: str, b: str, sep: frozenset, ui: dict | None = None) -> None:
    """u_aj + u_bj − Σ_{w∈sep} u_wj ≤ 1 for every district j."""
    ui = unit_items(m.items) if ui is None else ui
    m.cuts.append((a, b, tuple(sorted(sep))))
    for j in range(m.k):
        coef = {m.touch(a, j, ui): 1.0}
        coef[m.touch(b, j, ui)] = coef.get(m.touch(b, j, ui), 0.0) + 1.0
        for w in sep:
            coef[m.touch(w, j, ui)] = coef.get(m.touch(w, j, ui), 0.0) - 1.0
        m.rows.append((coef, -math.inf, 1.0, "connect"))


def unit_sets(m: Model, assign: list) -> list:
    """The unit set S_j of each district under `assign` (item -> district)."""
    out = [set() for _ in range(m.k)]
    for i, j in enumerate(assign):
        out[j].add(m.items[i].unit)
    return out


def separators(inst, channel: str, sets: list) -> list:
    """(a, b, N(C)) for each component C of a disconnected G[S_j] and one unit b of S_j − C."""
    adj = supports.unit_graph(inst, channel)
    out = []
    for s in sets:
        comps = _components(s, adj)
        if len(comps) < 2:
            continue
        for c in comps:
            nb = frozenset(set().union(*(adj[u] for u in c)) - c)
            b = min(min(d) for d in comps if d is not c)
            out.append((min(c), b, nb))
    return out


def _components(s, adj) -> list:
    left, comps = set(s), []
    while left:
        start = min(left)
        comp, stack = {start}, [start]
        while stack:
            for w in adj[stack.pop()]:
                if w in left and w not in comp:
                    comp.add(w)
                    stack.append(w)
        left -= comp
        comps.append(frozenset(comp))
    return sorted(comps, key=lambda c: min(c))


# ------------------------------------------------------------------------------ solving
@dataclass
class Step:
    """One assignment MILP at fixed centres."""
    status: str
    objective: float | None
    bound: float | None
    gap: float | None
    time_s: float
    nodes: int
    lp_iterations: int
    rows: int
    cols: int
    nonzeros: int
    integers: int
    cuts: int


def _lp(m: Model, cost: np.ndarray) -> highspy.HighsLp:
    lp = highspy.HighsLp()
    lp.num_col_, lp.num_row_ = m.ncols, len(m.rows)
    lp.col_cost_ = cost
    lp.col_lower_ = np.array(m.lower, dtype=float)
    lp.col_upper_ = np.array(m.upper, dtype=float)
    inf = highspy.kHighsInf
    lp.row_lower_ = np.array([max(lo, -inf) for _, lo, _, _ in m.rows], dtype=float)
    lp.row_upper_ = np.array([min(hi, inf) for _, _, hi, _ in m.rows], dtype=float)
    cols: list = [[] for _ in range(m.ncols)]
    for r, (coef, _, _, _) in enumerate(m.rows):
        for c, a in coef.items():
            if a != 0.0:
                cols[c].append((r, a))
    start, index, value = [0], [], []
    for entries in cols:
        for r, a in entries:
            index.append(r)
            value.append(a)
        start.append(len(index))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.array(start, dtype=np.int32)
    lp.a_matrix_.index_ = np.array(index, dtype=np.int32)
    lp.a_matrix_.value_ = np.array(value, dtype=float)
    lp.integrality_ = [highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous
                       for i in m.integer]
    return lp


def costs(m: Model, centres: list) -> np.ndarray:
    """The objective at fixed centres, in m_rel · km², per column (0 on y)."""
    out = np.zeros(m.ncols)
    for (i, j), c in m.x_col.items():
        out[c] = cost(m.items[i], centres[j])
    return out


def violations(m: Model, x) -> list:
    bad = []
    for c, v in enumerate(x):
        if (v < m.lower[c] - FEAS_TOL or v > m.upper[c] + FEAS_TOL
                or (m.integer[c] and abs(v - round(v)) > INT_TOL)):
            bad.append(("bound/integer", c, v))
    for coef, lo, hi, kind in m.rows:
        a = math.fsum(k * x[c] for c, k in coef.items())
        if max(lo - a, a - hi) > FEAS_TOL:
            bad.append((kind, lo, a, hi))
    return bad


def solve(m: Model, centres: list, start: list | None, time_limit: float,
          nearest: int | None = None) -> tuple:
    """(assignment item -> district or None, Step) at fixed `centres`, warm-started from the
    assignment `start` when given.  `nearest` restricts each item to its `nearest` cheapest
    districts (`start_assignment` only)."""
    w = costs(m, centres)
    upper = list(m.upper)
    if nearest is not None:
        for i in range(len(m.items)):
            keep = set(sorted(range(m.k), key=lambda j: (w[m.x_col[i, j]], j))[:nearest])
            for j in set(range(m.k)) - keep:
                upper[m.x_col[i, j]] = 0.0
    scale = float(w[w > 0].mean()) if (w > 0).any() else 1.0
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    if THREADS is not None:
        h.setOptionValue("threads", THREADS)
    h.setOptionValue("mip_rel_gap", 0.0)
    h.setOptionValue("mip_abs_gap", 0.0)
    h.setOptionValue("time_limit", float(time_limit))
    lp = _lp(m, w / scale)
    lp.col_upper_ = np.array(upper, dtype=float)
    h.passModel(lp)
    if start is not None:
        h.setSolution(_solution(m, start))
    t0 = time.time()
    h.run()
    elapsed = time.time() - t0
    ms = h.getModelStatus()
    info = h.getInfo()
    status = h.modelStatusToString(ms).lower()
    nnz = sum(len(coef) for coef, _, _, _ in m.rows)
    obj = bound = gap = None
    assign = None
    if info.primal_solution_status == highspy.kSolutionStatusFeasible:
        x = list(h.getSolution().col_value)
        bad = violations(m, x)
        if bad:
            raise HessError(f"channel {m.channel}: HiGHS ({status}) returned an incumbent that "
                            f"breaks {len(bad)} rows, e.g. {bad[:3]}")
        assign = []
        for i in range(len(m.items)):
            js = [j for j in range(m.k) if x[m.x_col[i, j]] > 0.5]
            assign.append(js[0])
        obj = math.fsum(cost(m.items[i], centres[j]) for i, j in enumerate(assign))
        b = float(info.mip_dual_bound) * scale
        bound = min(b, obj) if math.isfinite(b) else None
        if bound is not None:
            gap = 0.0 if obj - bound <= 1e-9 * max(1.0, abs(obj)) else (obj - bound) / abs(obj)
    return assign, Step(status, obj, bound, gap, round(elapsed, 3), int(info.mip_node_count),
                        int(info.simplex_iteration_count), len(m.rows), m.ncols, nnz, sum(m.integer),
                        len(m.cuts))


def _solution(m: Model, assign: list) -> highspy.HighsSolution:
    """The column vector of `assign`: its x and its touches y."""
    x = [0.0] * m.ncols
    ui = unit_items(m.items)
    for i, j in enumerate(assign):
        x[m.x_col[i, j]] = 1.0
    for (v, j), c in m.y_col.items():
        x[c] = 1.0 if any(assign[i] == j for i in ui[v]) else 0.0
    sol = highspy.HighsSolution()
    sol.col_value = x
    sol.value_valid = True
    return sol


def recentre(m: Model, assign: list, old: list) -> list:
    """Each district's opportunity-weighted centroid; a district with no mass keeps its centre."""
    sx, sy, sm = [0.0] * m.k, [0.0] * m.k, [0.0] * m.k
    for it, j in zip(m.items, assign):
        sx[j] += it.mass * it.centre[0]
        sy[j] += it.mass * it.centre[1]
        sm[j] += it.mass
    return [(sx[j] / sm[j], sy[j] / sm[j]) if sm[j] > 0 else old[j] for j in range(m.k)]


def hess_objective(m: Model, assign: list, centres: list) -> float:
    return math.fsum(cost(m.items[i], centres[j]) for i, j in enumerate(assign))


def connected_solve(m: Model, inst, centres: list, start: list | None, time_limit: float,
                    deadline: float, nearest: int | None = None, log=print) -> tuple:
    """(assignment or None, steps): `solve` with lazy separator cuts until every G[S_j] is
    connected.  A round with no incumbent, or the deadline, returns `start`, which is connected."""
    steps = []
    while True:
        left = deadline - time.time()
        if left <= 0:
            return start, steps
        new, step = solve(m, centres, start, min(time_limit, left), nearest)
        seps = separators(inst, m.channel, unit_sets(m, new)) if new is not None else []
        steps.append({**step.__dict__, "nearest": nearest, "cuts_added": len(seps)})
        log(f"{m.channel}: {'nearest ' + str(nearest) if nearest else 'full'} MILP {step.status}, "
            f"obj {step.objective}, gap {step.gap}, {step.time_s}s, {len(seps)} new cuts")
        if new is None:
            return start, steps
        if not seps:
            return new, steps
        for a, b, sep in seps:
            add_cut(m, inst, a, b, sep)


def relaxed_centres(m: Model, centres: list, log=print) -> tuple:
    """(centres, rounds): the location–allocation loop on the MILP's LP relaxation, from
    `centres`, until no centre moves by `RELAXED_MOVE_KM`, at most `RELAXED_ITERS` rounds.  A
    district's centre is the opportunity-weighted centroid of its fractional assignment."""
    rounds = []
    for r in range(RELAXED_ITERS):
        w = costs(m, centres)
        scale = float(w[w > 0].mean())
        lp = _lp(m, w / scale)
        lp.integrality_ = [highspy.HighsVarType.kContinuous] * m.ncols
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        if THREADS is not None:
            h.setOptionValue("threads", THREADS)
        h.setOptionValue("time_limit", START_LIMIT)
        h.passModel(lp)
        t0 = time.time()
        h.run()
        status = h.modelStatusToString(h.getModelStatus()).lower()
        if status != "optimal":
            raise HessError(f"channel {m.channel}: the relaxed assignment ended {status}")
        x = h.getSolution().col_value
        sx, sy, sm = [0.0] * m.k, [0.0] * m.k, [0.0] * m.k
        for (i, j), c in m.x_col.items():
            f = x[c] * m.items[i].mass
            if f > 0:
                sx[j] += f * m.items[i].centre[0]
                sy[j] += f * m.items[i].centre[1]
                sm[j] += f
        new = [(sx[j] / sm[j], sy[j] / sm[j]) if sm[j] > 0 else centres[j] for j in range(m.k)]
        move = max(math.dist(a, b) for a, b in zip(centres, new))
        rounds.append({"round": r, "status": status, "objective": h.getInfo().objective_function_value
                       * scale, "move_km": move, "time_s": round(time.time() - t0, 3)})
        centres = new
        if move < RELAXED_MOVE_KM:
            break
    log(f"{m.channel}: relaxed location-allocation, {len(rounds)} rounds, LP objective "
        f"{rounds[-1]['objective']:.6g}, last move {rounds[-1]['move_km']:.2f} km")
    return centres, rounds


def start_assignment(m: Model, inst, centres: list, deadline: float, log=print) -> tuple:
    """(a connected assignment or None, steps): the first warm start, from the same MILP with
    each item restricted to its `NEAREST` cheapest districts, widened until one is found.  It
    only starts the full MILP, which then runs unrestricted."""
    steps = []
    for n in NEAREST:
        a, st = connected_solve(m, inst, centres, None, START_LIMIT, deadline, min(n, m.k), log)
        steps += st
        if a is not None:
            return a, steps
    return None, steps


def _iteration(m: Model, it: int, steps: list, assign: list, centres: list, log) -> dict:
    out = {"iteration": it, "steps": steps,
           "objective_at_centres": hess_objective(m, assign, centres),
           "objective_recentred": hess_objective(m, assign, recentre(m, assign, centres))}
    log(f"{m.channel} it {it}: {out['objective_at_centres']:.6g} at its centres, "
        f"{out['objective_recentred']:.6g} recentred")
    return out


@dataclass
class Result:
    channel: str
    assign: list
    centres: list               # the final centres, each its district's weighted centroid
    objective: float            # Σ_z M_z ‖p_z − c_j‖² at those centres
    stop: str                   # why the loop ended
    iterations: list            # per iteration: centres' objective, the MILP's Step, cuts
    time_s: float
    seed_centres: list
    relaxed: list               # the LP-relaxed rounds before the first MILP


def plan(inst, channel: str, p: dict, band: tuple, max_iters: int = MAX_ITERS,
         time_limit: float = TIME_LIMIT, total_limit: float = TOTAL_LIMIT, log=print) -> tuple:
    """(Result, Model): the location–allocation loop (module docstring)."""
    t0 = time.time()
    ch = inst.channels[channel]
    its = items(inst, channel, p)
    m = build(inst, channel, its, band)
    pos = sorted(z for z in ch.m if ch.m[z] > 0)
    seed = realize.kmeans(pos, ch.m, p, ch.k)
    log(f"{channel}: {len(its)} items, {m.ncols} columns, {len(m.rows)} rows; seed in "
        f"{time.time() - t0:.1f}s")
    centres, relaxed = relaxed_centres(m, list(seed), log)
    assign, steps = start_assignment(m, inst, centres, t0 + total_limit, log)
    if assign is None:
        raise HessError(f"channel {channel}: no connected assignment found to start from")
    iters, stop = [], "iteration cap"
    iters.append(_iteration(m, -1, steps, assign, centres, log))  # the start, then its centroids
    centres = recentre(m, assign, centres)
    deadline = t0 + total_limit
    for it in range(max_iters):
        if time.time() >= deadline:
            stop = "time cap"
            break
        new, steps = connected_solve(m, inst, centres, assign, time_limit, deadline, None, log)
        repeats = new == assign
        assign = new
        iters.append(_iteration(m, it, steps, assign, centres, log))
        centres = recentre(m, assign, centres)
        if repeats:
            stop = "assignment repeats"
            break
    return Result(channel, assign, centres, hess_objective(m, assign, centres), stop, iters,
                  round(time.time() - t0, 3), seed, relaxed), m
