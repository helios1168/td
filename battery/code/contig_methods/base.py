"""
base.py -- the contiguity-harness contract (PLAN.md Part C.1; frozen at the U1a merge).

Every contiguity method is a module in this package exposing

    NAME: str                      registry key
    EXACT: bool                    True if the method can certify (produces a global UB)
    MAX_N: int | None              optional size cap (brute force)
    VARIANTS: dict[str, dict]      optional {variant_name: extra kwargs for solve}
    solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0, **opts) -> Result

What a method receives
----------------------
`G`      a *copy* of the pair subgraph, node attrs `A, B, M` (+ `state`, `pos`, and
         `d_a, d_b` when kappa > 0), already state-filtered and rescaled by the harness
         (`filter_pair`, `rescale_pair`).  Methods never mutate it.
`nodes`  `sorted(G)`.
`theta, lam, rho, kappa`   model parameters; **rho defaults to 0 everywhere** (decision
         2026-08-28: contiguity is a hard constraint; the perimeter penalty is only a
         secondary axis for the `current` control).
`respect_state`   always False when a method sees it: the harness has already deleted the
         cross-state edges (C.0 #5).  Methods must not delete edges themselves.
`time_limit`   seconds; methods self-enforce it, run one solver thread, and are
         deterministic in `seed`.
`trace`  harness-owned `Trace`; methods call `trace.incumbent(to_a, obj)` whenever they
         find a better feasible allocation and `trace.bound(ub)` whenever their global
         bound tightens.  The harness fills `Result.trace` and `t_first_feasible` from it.

Utilities are **always** taken from `utilities(G, nodes, theta, lam, kappa)`; a method must
never recompute u_a, u_b itself (W11 changes them).

Objective and feasibility
-------------------------
    obj(S) = log g_a(S) + log g_b(S) - rho * perimeter(S)        (nats; rho = 0 -> log product)
    g_a(S) = sum_{z in S} u_a(z),   g_b(S) = sum_{z not in S} u_b(z)      (d = (0, 0))

Feasible  <=>  for every connected component K of the (filtered) pair graph, S∩K and K∖S are
each connected or empty (C.0 #1).  `pieces()` reports pair_components, pieces_a, pieces_b,
excess_pieces; `optimal` requires excess_pieces == 0.

Bounds: `gap_nats = UB - LB` is the primary gap (scale-invariant; acceptance <= 1e-8 + eps),
`gap_rel = 1 - exp(-gap_nats)` secondary.  `Result.ub_scope` is "global" or "rooted"
(a root-fixed formulation bounds a *restriction*); the harness downgrades a rooted `optimal`
to `status_eff = "optimal_rooted"` with `valid_certificate = False`.

Statuses.  `optimal` may be claimed only when the method's own UB - LB <= CERT_TOL + eps
on a feasible allocation (the validator rejects anything looser).  A loop that converged
but whose engine stopped on a relative-gap tolerance (HiGHS' default mip_rel_gap = 1e-4
inside the legacy `districting` loop, found 2026-08-29) reports `gap_limit` with its valid
UB.  `time_limit` / `iteration_limit` carry the last iterate (feasible or not, LB=None if
not); `heuristic` has UB=None; `infeasible` / `error` may carry no allocation.

What the harness recomputes (never trusts): g_a, g_b, product, perimeter, LB, pieces_*,
excess_pieces, the fairness audit, cost_of_contiguity, gaps, t_total.  What it trusts:
status, UB, ub_scope, eps, iters, n_cuts, n_tangents, nodes, t_first_feasible, extra.
"""
from __future__ import annotations

import math
import signal
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Iterable, Optional

import networkx as nx
import numpy as np

STATUSES = ("optimal", "gap_limit", "time_limit", "iteration_limit", "heuristic",
            "infeasible", "error")
UB_SCOPES = ("global", "rooted")
CERT_TOL = 1e-8          # certificate tolerance in nats (CLAUDE.md acceptance)
# Second acceptance tier (decided 2026-08-30, PLAN.md "Decisions taken"): a row whose gap
# is <= EPS_CERT nats counts as eps-certified at the *programme* level (production sizes,
# T2+), because 5e-3 sits below the measured data-noise floor of the objective itself --
# bootstrap of the 197-zip C7b_s1 A2/B2 pair under the contestability noise model
# (cv_sales=0.10, cv_opp=0.06, theta/lam fixed) moves the optimal log-product by
# std 8.4e-3 / IQR 1.3e-2 nats and flips ~24/197 zips per draw (RESULTS.md
# "Two-tier acceptance"). Method-level semantics are UNCHANGED: `optimal` still requires
# CERT_TOL; this constant is read only by the harness scoring (contiguity_bench phase 3).
EPS_CERT = 5e-3          # eps-certificate tolerance in nats (~0.5% of the Nash product)
LB_TOL = 1e-9            # |LB_claimed - LB_recomputed|
PRODUCT_TOL = 1e-9       # product <= product_free * (1 + PRODUCT_TOL)
RESCALE_TARGET = 100.0   # sum(u_a + u_b) after rescale_pair


# ----------------------------------------------------------------------------- results
@dataclass
class Result:
    """What a method returns.  Only `status` is required; everything else defaults."""
    status: str
    to_a: Optional[set] = None            # zips assigned to a; None if no iterate at all
    LB: Optional[float] = None            # method's claim for obj(to_a); None if to_a infeasible
    UB: Optional[float] = None            # tightest valid bound (None for heuristics)
    ub_scope: str = "global"              # "global" | "rooted"
    eps: float = 0.0                      # a-priori bound for eps-methods (Option C), else 0
    iters: int = 0                        # outer iterations (OA rounds, cut rounds)
    n_cuts: int = 0                       # connectivity cuts added
    n_tangents: int = 0                   # tangent (OA) cuts added
    nodes: int = 0                        # branch-and-bound nodes, if the engine reports them
    t_first_feasible: Optional[float] = None   # filled by the harness from trace if None
    t_total: Optional[float] = None       # filled by the harness
    trace: list = field(default_factory=list)  # [(t, LB, UB)] filled by the harness
    extra: dict = field(default_factory=dict)  # method-specific (root_a, root_b, ...)
    message: str = ""

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"status {self.status!r} not in {STATUSES}")
        if self.ub_scope not in UB_SCOPES:
            raise ValueError(f"ub_scope {self.ub_scope!r} not in {UB_SCOPES}")
        if self.to_a is not None and not isinstance(self.to_a, (set, frozenset)):
            self.to_a = set(self.to_a)

    def to_json(self) -> dict:
        d = asdict(self)
        d["to_a"] = None if self.to_a is None else sorted(self.to_a, key=_sort_key)
        d["trace"] = [list(t) for t in self.trace]
        return d


def _sort_key(z):
    return (0, z) if isinstance(z, (int, np.integer)) else (1, str(z))


class Trace:
    """Harness-owned incumbent/bound log.  Methods call `incumbent` and `bound`."""

    def __init__(self, t0: Optional[float] = None):
        self.t0 = time.perf_counter() if t0 is None else t0
        self.events: list[tuple[float, Optional[float], Optional[float]]] = []
        self.best_lb: Optional[float] = None
        self.best_to_a: Optional[set] = None
        self.best_ub: Optional[float] = None
        self.t_first_feasible: Optional[float] = None

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0

    def incumbent(self, to_a: Iterable, obj: float) -> None:
        t = self.elapsed()
        if self.t_first_feasible is None:
            self.t_first_feasible = t
        if self.best_lb is None or obj > self.best_lb:
            self.best_lb = float(obj)
            self.best_to_a = set(to_a)
        self.events.append((t, self.best_lb, self.best_ub))

    def bound(self, ub: float) -> None:
        t = self.elapsed()
        ub = float(ub)
        if self.best_ub is None or ub < self.best_ub:
            self.best_ub = ub
        self.events.append((t, self.best_lb, self.best_ub))

    def rows(self) -> list:
        return [(round(t, 6), lb, ub) for t, lb, ub in self.events]


# ------------------------------------------------------------------------- utilities
def utilities(G, nodes, theta: float = 0.40, lam: float = 0.30, kappa: float = 0.0):
    """u_a, u_b per zip (aligned with `nodes`).  The only sanctioned way to get them.

        u_a = c1*A + c2*B + lam*M - kappa*d_a,   u_b = c2*A + c1*B + lam*M - kappa*d_b
        c1 = 1 - lam,  c2 = theta*(1 - lam)          (territory._fields at kappa = 0)

    kappa > 0 (W11 travel cost) requires node attrs `d_a`, `d_b` (distance to each rep's base).
    """
    A = np.array([G.nodes[z]["A"] for z in nodes], float)
    B = np.array([G.nodes[z]["B"] for z in nodes], float)
    M = np.array([G.nodes[z]["M"] for z in nodes], float)
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    ua = c1 * A + c2 * B + lam * M
    ub = c2 * A + c1 * B + lam * M
    if kappa:
        try:
            da = np.array([G.nodes[z]["d_a"] for z in nodes], float)
            db = np.array([G.nodes[z]["d_b"] for z in nodes], float)
        except KeyError as e:
            raise KeyError("kappa > 0 needs node attrs d_a, d_b on every zip") from e
        ua = ua - kappa * da
        ub = ub - kappa * db
    return ua, ub


def ratio(ua, ub):
    """u_a/u_b with the zero-value guard (C.0 #9): ub == 0 < ua -> +inf, ua == ub == 0 -> 1."""
    ua = np.asarray(ua, float); ub = np.asarray(ub, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ub > 0, ua / ub, np.where(ua > 0, np.inf, 1.0))


def mask(nodes, to_a) -> np.ndarray:
    to_a = set(to_a)
    return np.fromiter((z in to_a for z in nodes), dtype=bool, count=len(nodes))


def gains(ua, ub, x: np.ndarray):
    return float(ua[x].sum()), float(ub[~x].sum())


def objective(ua, ub, x: np.ndarray, rho: float = 0.0, perimeter: int = 0) -> float:
    """log g_a + log g_b - rho*perimeter; -inf if either gain is <= 0."""
    ga, gb = gains(ua, ub, x)
    if ga <= 0 or gb <= 0:
        return -math.inf
    return math.log(ga) + math.log(gb) - rho * perimeter


# ----------------------------------------------------------------- pair graph handling
def filter_pair(G, nodes, respect_state: bool = False):
    """Pair subgraph copy with attrs A, B, M, state, pos, d_a, d_b only.

    With respect_state=True the cross-state edges are deleted here (never inside a
    method); raises if any zip lacks `state`.  Returns (H, edge_share_deleted).
    """
    keep = ("A", "B", "M", "state", "pos", "d_a", "d_b")
    H = nx.Graph()
    for z in nodes:
        H.add_node(z, **{k: v for k, v in G.nodes[z].items() if k in keep})
    sub = G.subgraph(nodes)
    H.add_edges_from(sub.edges())
    m0 = H.number_of_edges()
    deleted = 0
    if respect_state:
        for z in nodes:
            if "state" not in H.nodes[z]:
                raise ValueError(f"respect_state=True but zip {z!r} has no 'state' attribute")
        cross = [(u, v) for u, v in H.edges() if H.nodes[u]["state"] != H.nodes[v]["state"]]
        H.remove_edges_from(cross)
        deleted = len(cross)
    return H, (deleted / m0 if m0 else 0.0)


def check_state_filter(G, respect_state: bool) -> list:
    """Violations if respect_state and a cross-state edge survives (or state is missing)."""
    if not respect_state:
        return []
    out = []
    for u, v in G.edges():
        su, sv = G.nodes[u].get("state"), G.nodes[v].get("state")
        if su is None or sv is None:
            out.append(f"state missing on edge ({u!r},{v!r})")
        elif su != sv:
            out.append(f"cross-state edge survives ({u!r},{v!r})")
    return out


def rescale_pair(G, nodes, theta: float = 0.40, lam: float = 0.30,
                 target: float = RESCALE_TARGET, kappa: float = 0.0):
    """Copy of G with A, B, M (and d_a, d_b) multiplied so that sum(u_a + u_b) == target.

    Utilities are homogeneous of degree 1 in (A, B, M, d), so the argmax is unchanged and
    obj shifts by exactly 2*log(scale).  Returns (H, scale); scale == 1 if sum(u) == 0.
    """
    ua, ub = utilities(G, nodes, theta, lam, kappa)
    tot = float(ua.sum() + ub.sum())
    scale = target / tot if tot > 0 else 1.0
    H = G.copy()
    for z in nodes:
        for k in ("A", "B", "M", "d_a", "d_b"):
            if k in H.nodes[z]:
                H.nodes[z][k] = float(H.nodes[z][k]) * scale
    H.graph["scale"] = scale
    return H, scale


def perimeter(G, nodes, to_a) -> int:
    """Boundary edges of the partition (to_a vs the rest) in the pair graph."""
    to_a = set(to_a)
    return sum(1 for u, v in G.subgraph(nodes).edges() if (u in to_a) != (v in to_a))


def pieces(G, nodes, to_a) -> dict:
    """Component-wise contiguity report (C.0 #1).

    pair_components : components of the pair graph itself
    pieces_a/b      : connected components of S / of the complement, over the whole graph
    excess_pieces   : sum over pair components K of (cc(S∩K) - 1)^+ + (cc(K\\S) - 1)^+
                      == 0  <=>  feasible
    """
    to_a = set(to_a)
    sub = G.subgraph(nodes)
    comps = list(nx.connected_components(sub))
    pa = pb = excess = 0
    for K in comps:
        Sa_ = [z for z in K if z in to_a]
        Sb_ = [z for z in K if z not in to_a]
        ca = nx.number_connected_components(sub.subgraph(Sa_)) if Sa_ else 0
        cb = nx.number_connected_components(sub.subgraph(Sb_)) if Sb_ else 0
        pa += ca; pb += cb
        excess += max(ca - 1, 0) + max(cb - 1, 0)
    return dict(pair_components=len(comps), pieces_a=pa, pieces_b=pb, excess_pieces=excess)


def is_feasible(G, nodes, to_a) -> bool:
    return pieces(G, nodes, to_a)["excess_pieces"] == 0


# ------------------------------------------------------------------ fairness audit (d=0)
def fairness(ua, ub, x: np.ndarray) -> dict:
    """EF1, envy over u_max, proportionality shortfall for the allocation x (a-side mask).

    ef1_ab : a does not envy b up to one good:  v_a(T) - max_{z in T} u_a(z) <= g_a
    ef1_ba : mirror.
    envy_over_umax : max over sides of envy^+ / u_max of the envied bundle (0 if no envy).
    prop_shortfall_a : max(0, 0.5*sum(u_a) - g_a) / max_z u_a(z); same for b.
    """
    ga, gb = gains(ua, ub, x)
    T, S = ~x, x
    va_T = float(ua[T].sum()); vb_S = float(ub[S].sum())
    ua_T_max = float(ua[T].max()) if T.any() else 0.0
    ub_S_max = float(ub[S].max()) if S.any() else 0.0
    ef1_ab = (va_T - ua_T_max) <= ga + 1e-12
    ef1_ba = (vb_S - ub_S_max) <= gb + 1e-12
    envy_a = max(0.0, va_T - ga); envy_b = max(0.0, vb_S - gb)
    e = 0.0
    if envy_a > 0: e = max(e, envy_a / ua_T_max if ua_T_max > 0 else math.inf)
    if envy_b > 0: e = max(e, envy_b / ub_S_max if ub_S_max > 0 else math.inf)
    ua_max = float(ua.max()) if len(ua) else 0.0
    ub_max = float(ub.max()) if len(ub) else 0.0
    psa = max(0.0, 0.5 * float(ua.sum()) - ga); psb = max(0.0, 0.5 * float(ub.sum()) - gb)
    return dict(ef1_ab=bool(ef1_ab), ef1_ba=bool(ef1_ba), ef1=bool(ef1_ab and ef1_ba),
                envy_over_umax=float(e),
                prop_shortfall_a=float(psa / ua_max) if ua_max > 0 else 0.0,
                prop_shortfall_b=float(psb / ub_max) if ub_max > 0 else 0.0)


# ------------------------------------------------------------------------ covariates
def _gini(v: np.ndarray) -> float:
    v = np.sort(np.asarray(v, float)); n = len(v); s = v.sum()
    if n == 0 or s <= 0: return 0.0
    return float((2.0 * np.arange(1, n + 1) - n - 1).dot(v) / (n * s))


def block_tree_is_path(G) -> bool:
    """True iff every component's block-cut tree is a path (Bilo et al. 2022, Thm 3.10)."""
    for K in nx.connected_components(G):
        sub = G.subgraph(K)
        blocks = [frozenset(b) for b in nx.biconnected_components(sub)]
        if len(blocks) <= 1:
            continue
        cuts = set(nx.articulation_points(sub))
        T = nx.Graph()
        T.add_nodes_from(("B", i) for i in range(len(blocks)))
        T.add_nodes_from(("C", c) for c in cuts)
        for i, b in enumerate(blocks):
            for c in cuts & b:
                T.add_edge(("B", i), ("C", c))
        if any(d > 2 for _, d in T.degree()):
            return False
    return True


def covariates(G, nodes, ua, ub, free_to_a=None) -> dict:
    """Per-pair structure covariates (C.1).  `free_to_a` = free-Nash allocation if known."""
    sub = G.subgraph(nodes)
    u = np.asarray(ua) + np.asarray(ub)
    tot = float(u.sum())
    top5 = float(np.sort(u)[-5:].sum() / tot) if tot > 0 else 0.0
    states = {G.nodes[z].get("state") for z in nodes} - {None}
    out = dict(n=len(nodes), n_edges=sub.number_of_edges(),
               pair_components=nx.number_connected_components(sub),
               articulation_points=sum(1 for _ in nx.articulation_points(sub)),
               block_tree_is_path=block_tree_is_path(sub),
               gini_u=_gini(u), top5_share_u=top5,
               active_frac=float((u > 0).mean()) if len(u) else 0.0,
               n_states=len(states))
    if free_to_a is not None:
        p = pieces(G, nodes, free_to_a)
        out.update(free_pieces_a=p["pieces_a"], free_pieces_b=p["pieces_b"],
                   free_excess_pieces=p["excess_pieces"],
                   free_perimeter=perimeter(G, nodes, free_to_a))
    return out


# ------------------------------------------------------------------------- validation
def evaluate(G, nodes, res: Result, *, theta: float = 0.40, lam: float = 0.30,
             rho: float = 0.0, kappa: float = 0.0, respect_state: bool = False,
             product_free: Optional[float] = None, UB_star_global: Optional[float] = None,
             ua=None, ub=None) -> dict:
    """Recompute everything from `res.to_a`, validate, and return the row fields.

    Always returns `valid` (bool) and `violations` (list of str).  Recomputed quantities are
    None when there is no iterate.  `status_eff` is `res.status` except that a rooted
    `optimal` becomes "optimal_rooted"; `valid_certificate` is True only for a global,
    tolerance-tight certificate on a feasible allocation.
    """
    if ua is None or ub is None:
        ua, ub = utilities(G, nodes, theta, lam, kappa)
    v: list[str] = []
    row: dict = dict(status=res.status, status_eff=res.status, ub_scope=res.ub_scope,
                     UB=res.UB, LB_claimed=res.LB, eps=res.eps, iters=res.iters,
                     n_cuts=res.n_cuts, n_tangents=res.n_tangents, nodes=res.nodes,
                     t_first_feasible=res.t_first_feasible, t_total=res.t_total,
                     message=res.message, extra=res.extra,
                     g_a=None, g_b=None, product=None, perimeter=None, LB=None,
                     obj_iterate=None, feasible=None, pair_components=None, pieces_a=None,
                     pieces_b=None, excess_pieces=None, k=None,
                     cost_of_contiguity=None, gap_nats=None, gap_rel=None,
                     gap_star_nats=None, valid_certificate=False)
    v += check_state_filter(G, respect_state)
    if res.status not in STATUSES:
        v.append(f"unknown status {res.status!r}")
    if res.UB is not None and not np.isfinite(res.UB):
        v.append("UB is not finite")
    if res.UB is not None and res.LB is not None and res.LB > res.UB + CERT_TOL:
        v.append(f"claimed LB {res.LB:.12g} exceeds claimed UB {res.UB:.12g}")
    if res.status == "heuristic" and res.UB is not None:
        v.append("heuristic must report UB=None")

    if res.to_a is not None:
        node_set = set(nodes)
        if not set(res.to_a) <= node_set:
            v.append("to_a contains zips outside the pair")
        to_a = set(res.to_a) & node_set
        x = mask(nodes, to_a)
        ga, gb = gains(ua, ub, x)
        per = perimeter(G, nodes, to_a)
        p = pieces(G, nodes, to_a)
        feas = p["excess_pieces"] == 0
        obj = objective(ua, ub, x, rho, per)
        row.update(g_a=ga, g_b=gb, product=ga * gb, perimeter=per, k=int(x.sum()),
                   obj_iterate=obj if np.isfinite(obj) else None, feasible=feas, **p)
        row.update(fairness(ua, ub, x))
        if feas and np.isfinite(obj):
            row["LB"] = obj
        if res.status == "optimal" and not feas:
            v.append(f"optimal but excess_pieces={p['excess_pieces']}")
        if res.LB is not None:
            if not feas:
                v.append("LB claimed for an infeasible iterate (must be None)")
            elif not np.isfinite(obj) or abs(res.LB - obj) > LB_TOL:
                v.append(f"LB claimed {res.LB!r} != recomputed {obj!r}")
        if product_free is not None and ga * gb > product_free * (1 + PRODUCT_TOL):
            v.append(f"product {ga*gb:.12g} exceeds free product {product_free:.12g}")
        if product_free is not None and product_free > 0:
            row["cost_of_contiguity"] = 1.0 - (ga * gb) / product_free
    else:
        if res.status == "optimal":
            v.append("optimal without an allocation")
        if res.LB is not None:
            v.append("LB claimed without an allocation")

    LB = row["LB"]
    if res.UB is not None and LB is not None:
        row["gap_nats"] = res.UB - LB
        row["gap_rel"] = 1.0 - math.exp(-max(row["gap_nats"], 0.0))
    if UB_star_global is not None and LB is not None:
        row["gap_star_nats"] = UB_star_global - LB
        if LB > UB_star_global + CERT_TOL:
            v.append(f"LB {LB:.12g} exceeds the cross-method global UB* {UB_star_global:.12g} (bug)")

    if res.status == "optimal":
        if res.UB is None:
            v.append("optimal without a UB")
        elif LB is None:
            pass  # already flagged (infeasible / missing allocation)
        elif res.UB - LB > CERT_TOL + res.eps:
            v.append(f"optimal but gap_nats {res.UB - LB:.3e} > {CERT_TOL + res.eps:.1e}")
        if res.ub_scope == "rooted":
            row["status_eff"] = "optimal_rooted"
        elif not v:
            row["valid_certificate"] = True
    row["valid"] = not v
    row["violations"] = v
    return row


# ------------------------------------------------------------- harness-side execution
class Backstop(Exception):
    """Raised inside a method by the SIGALRM backstop."""


def default_backstop(time_limit: float) -> float:
    return 1.25 * time_limit + 30.0


def run_method(solve: Callable, G, nodes, *, theta: float = 0.40, lam: float = 0.30,
               rho: float = 0.0, respect_state: bool = False, time_limit: float = 60.0,
               seed: int = 0, kappa: float = 0.0, warm_start=None, reductions=None,
               backstop: Optional[Callable[[float], float]] = default_backstop,
               **opts) -> Result:
    """Call a method under the contract: harness-owned Trace, wall clock, SIGALRM backstop.

    Fills `t_total`, `trace`, `t_first_feasible` (if the method left it None).  A method that
    raises returns status "error" (or "time_limit" for the backstop) carrying the trace's
    best incumbent, so the row is still written.  SIGALRM needs the main thread of the
    process -- true for Pool workers; pass backstop=None to disable.
    """
    tr = Trace()
    old = None
    use_alarm = backstop is not None and hasattr(signal, "SIGALRM")
    if use_alarm:
        def _alarm(signum, frame):
            raise Backstop(f"backstop after {tr.elapsed():.1f}s (cap {time_limit}s)")
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, max(backstop(time_limit), 0.01))
    try:
        res = solve(G, nodes, theta=theta, lam=lam, rho=rho, respect_state=respect_state,
                    time_limit=time_limit, seed=seed, warm_start=warm_start,
                    reductions=reductions, trace=tr, kappa=kappa, **opts)
        if not isinstance(res, Result):
            raise TypeError(f"method returned {type(res).__name__}, not Result")
    except Backstop as e:
        res = _from_trace(tr, "time_limit", str(e))
    except Exception as e:  # noqa: BLE001 -- every failure becomes a row
        res = _from_trace(tr, "error", f"{type(e).__name__}: {e}")
    finally:
        if use_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
    res.t_total = tr.elapsed()
    res.trace = tr.rows()
    if res.t_first_feasible is None:
        res.t_first_feasible = tr.t_first_feasible
    return res


def _from_trace(tr: Trace, status: str, message: str) -> Result:
    return Result(status=status, to_a=tr.best_to_a, LB=tr.best_lb, UB=tr.best_ub,
                  message=message)


# ------------------------------------------------------------------- lexi post-pass
_LEXI_ENGINE_OPTS = frozenset(("lambda_inout", "cut_family", "minimal", "max_iter"))


def lexi_perimeter(G, nodes, to_a, opt_value: float, method: Callable, *,
                   theta: float = 0.40, lam: float = 0.30, kappa: float = 0.0,
                   time_limit: float = 60.0, seed: int = 0, **opts):
    """Lexicographic perimeter tie-break (W9a): among contiguous allocations with
    log g_a + log g_b >= opt_value - 1e-9, minimise the perimeter.  An exact post-pass that
    reuses the chosen engine; reported as `perimeter_lexi`, never changes LB/UB.

    Signature frozen here; the body is W9a's (the one sanctioned edit to this file).

    Implementation (W9a).  The engine is always `contig_methods.loop_v2.solve_lexi` (the
    only wired engine to date; other engines can be plugged in later without touching this
    signature).  `method` names the engine the caller wants reused -- the harness passes
    `mspec.solve`, i.e. whichever method's own `solve` produced `to_a` (see
    `contiguity_bench.py::_lexi`).  If `method` is (or belongs to) `loop_v2` -- checked by
    name, by `__module__`, or by identity with `loop_v2.solve` -- it is used silently;
    otherwise a warning is issued (`method` is "not wired for the perimeter post-pass") and
    `loop_v2`'s engine is used anyway, since it is the only one available -- this keeps
    `--lexi` usable for every method in `rows.jsonl`, at the cost of the post-pass not
    literally being method-specific except for `loop_v2` itself (the one case this unit's
    acceptance test exercises: `--lexi --methods loop_v2`).  Recognised engine options
    (`lambda_inout`, `cut_family`, `minimal`, `max_iter`) are passed through from `**opts`
    when present (so a row produced by e.g. `loop_v2_nbr` gets its perimeter tie-break run
    with `cut_family="nbr"` too); anything else in `**opts` (variant kwargs belonging to a
    different method, such as `current`'s `milp_options`) is dropped, not forwarded.

    Never trusts the engine: independently recomputes g_a, g_b, the value floor and
    contiguity on whatever `to_a` the engine returns, and never returns a perimeter larger
    than the input allocation's -- any failure (engine exception, no feasible iterate, value
    floor violated, infeasible, or no improvement) falls back to the *original* `to_a` and
    its own perimeter, status "fallback".
    """
    import warnings
    from . import loop_v2 as _loop_v2   # deferred: avoids a base<->loop_v2 import cycle

    nodes = list(nodes)
    to_a_in = set(to_a) & set(nodes)
    per_in = perimeter(G, nodes, to_a_in)

    def _fallback(msg: str) -> dict:
        return dict(perimeter=int(per_in), to_a=set(to_a_in), obj=None, status="fallback",
                   iters=0, message=msg)

    engine_name = method if isinstance(method, str) else getattr(method, "__name__", "")
    engine_module = getattr(method, "__module__", "")
    is_loop_v2 = (engine_name == "loop_v2" or engine_module.endswith(".loop_v2")
                 or engine_module == "loop_v2" or method is getattr(_loop_v2, "solve", None))
    if not is_loop_v2:
        warnings.warn(
            f"lexi_perimeter: engine {method!r} is not wired for the perimeter post-pass; "
            "falling back to loop_v2's own engine", stacklevel=2)

    engine_kwargs = {k: v for k, v in opts.items() if k in _LEXI_ENGINE_OPTS}
    t0 = time.perf_counter()
    try:
        out = _loop_v2.solve_lexi(G, nodes, opt_value, theta=theta, lam=lam, kappa=kappa,
                                  time_limit=max(time_limit - (time.perf_counter() - t0), 0.1),
                                  seed=seed, **engine_kwargs)
    except Exception as e:                                   # noqa: BLE001
        return _fallback(f"lexi_perimeter: engine error {type(e).__name__}: {e}")

    cand_to_a = out.get("to_a")
    if cand_to_a is None:
        return _fallback("lexi_perimeter: no feasible iterate from the engine")
    cand_to_a = set(cand_to_a) & set(nodes)

    ua, ub = utilities(G, nodes, theta, lam, kappa)
    x = mask(nodes, cand_to_a)
    ga, gb = gains(ua, ub, x)
    if ga <= 0 or gb <= 0 or (math.log(ga) + math.log(gb)) < opt_value - 1e-9:
        return _fallback("lexi_perimeter: candidate violates the value floor")
    if not is_feasible(G, nodes, cand_to_a):
        return _fallback("lexi_perimeter: candidate is not contiguous")

    per = perimeter(G, nodes, cand_to_a)
    if per > per_in:
        return _fallback("lexi_perimeter: candidate did not improve on the input perimeter")

    status = "optimal" if out.get("status") == "optimal" else "capped"
    return dict(perimeter=int(per), to_a=cand_to_a, obj=float(math.log(ga) + math.log(gb)),
               status=status, iters=int(out.get("iters", 0)))
