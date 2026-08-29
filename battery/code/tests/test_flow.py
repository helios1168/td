"""
test_flow.py -- contig_methods/flow.py and flow_pwl.py: Option D (Shirabe single-commodity
flow, one-shot contiguity + OA tangent loop) and Option D+C (one MILP with an a-priori chord
under-estimator of the log).  PLAN.md W4.

The first test is the load-bearing one: it checks the *formulation*, not the solver.  With x
fixed to every subset of four tiny graphs, the flow polytope is LP-feasible exactly when the
allocation is component-wise contiguous under `base.pieces` -- both directions, no sampling.
Everything after that is optimality (against `brute`), bound validity, and contract hygiene.

Runtime budget: well under 60 s.  The slow tier (T1 sweep, named failures, eps sensitivity)
is `test_flow_slow.py`.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import shutil
import subprocess
import sys
import time

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

from scipy.optimize import Bounds, linprog, milp            # noqa: E402

from contig_methods import REGISTRY, base, flow, flow_pwl   # noqa: E402
from instances import HAND_GRAPHS, build_T0, build_pair     # noqa: E402

THETA, LAM = 0.40, 0.30
FLOW_KEYS = ("flow", "flow_loosecaps", "flow_selroot", "flow_rooted")

# every (UB, LB, OPT) triple any test in this module produces, checked in one place (test 7)
_BOUND_LOG: list = []


def _record(tag, res, row, opt=None):
    _BOUND_LOG.append(dict(tag=tag, UB=res.UB, LB=row.get("LB"), opt=opt, eps=res.eps,
                           scope=res.ub_scope))
    return row


# ------------------------------------------------------------------- hand instances
def path_instance(n=8):
    G = nx.path_graph(n)
    for i in range(n):
        G.nodes[i].update(A=1.0 + 0.9 * (n - 1 - i) / (n - 1), B=1.0 + 0.9 * i / (n - 1),
                          M=4.0 + 0.1 * i, pos=(i / n, 0.5))
    return G


def two_component_instance():
    """P4 + P3, disjoint: `test_brute.py`'s instance, so the two modules see the same graph."""
    G = path_instance(4)
    H = nx.relabel_nodes(path_instance(3), {0: 10, 1: 11, 2: 12})
    return nx.union(G, H)


def glue_instance():
    """P6 with two zero-value (A=B=M=0) zips in the middle -- regime (d), sparse active zips
    with zero-value glue (OPTIONS.md).  The glue is free to go either way, so the optimum is
    massively degenerate and any root/tie-breaking bug shows up as a wrong objective."""
    G = path_instance(6)
    for z in (2, 3):
        G.nodes[z].update(A=0.0, B=0.0, M=0.0)
    return G


def three_component_instance():
    """`test_brute.py`'s three-component instance verbatim (one component carries glue)."""
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2)])
    for i, (A, B, M) in zip((0, 1, 2), [(1.9, 1.0, 4.0), (1.5, 1.4, 4.2), (1.0, 1.9, 4.4)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 0))
    G.add_edges_from([(10, 11), (11, 12)])
    for i, (A, B, M) in zip((10, 11, 12), [(0.6, 2.3, 3.6), (1.1, 1.7, 3.1), (2.0, 0.9, 3.9)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 1))
    G.add_edges_from([(20, 21), (21, 22), (22, 23)])
    for i, (A, B, M) in zip((20, 21, 22, 23),
                            [(1.7, 0.8, 3.3), (0.0, 0.0, 0.0), (1.2, 1.6, 3.5), (0.9, 1.4, 3.0)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 2))
    return G


def component_to_b_instance():
    """Two components; the optimum hands the *whole* second one to b.

    This is the concrete separation between a global and a rooted bound (PLAN.md C.0 #3,
    CLAUDE.md trap 13).  `flow` finds 6.7125 by giving {10,11,12} entirely to b; `flow_rooted`
    fixes the argmax-ratio zip of *every* component to a, so it cannot express that allocation
    and certifies a strictly worse restricted optimum instead.
    """
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2), (2, 3)])
    for i, (A, B, M) in zip((0, 1, 2, 3),
                            [(9.0, 1.0, 12.0), (8.0, 1.5, 12.0), (7.0, 2.0, 11.0),
                             (6.0, 2.5, 10.0)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 0))
    G.add_edges_from([(10, 11), (11, 12)])
    for i, (A, B, M) in zip((10, 11, 12), [(0.2, 6.0, 7.0), (0.3, 5.0, 6.0), (0.1, 7.0, 8.0)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 1))
    return G


def zero_value_instance(n=6):
    """Every zip worth nothing to anyone: no allocation gives two positive gains."""
    G = nx.path_graph(n)
    for i in range(n):
        G.nodes[i].update(A=0.0, B=0.0, M=0.0, pos=(i, 0))
    return G


def prep(G):
    """Filter + rescale, the way the harness hands a pair to a method."""
    nodes = sorted(G)
    H, _ = base.filter_pair(G, nodes, respect_state=False)
    H, _ = base.rescale_pair(H, nodes, THETA, LAM)
    return H, sorted(H)


def run(key, G, nodes, *, rho=0.0, time_limit=60, seed=0, **kw):
    spec = REGISTRY[key]
    opts = dict(spec.kwargs)
    opts.update(kw)
    return base.run_method(spec.solve, G, nodes, theta=THETA, lam=LAM, rho=rho,
                           respect_state=False, time_limit=time_limit, seed=seed, **opts)


def opt_of(G, nodes, rho=0.0):
    res = run("brute", G, nodes, rho=rho)
    assert res.status == "optimal", res.message
    return base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=rho)["LB"], res.to_a


# T0 is rebuilt a lot; regenerating a pair is ~0.01 s but brute is not, so cache it here.
_T0_CACHE: dict = {}


def t0_pairs():
    if "pairs" not in _T0_CACHE:
        _T0_CACHE["pairs"] = [(sp, build_pair(sp)) for sp in build_T0()]
    return _T0_CACHE["pairs"]


def t0_opt(name, pi):
    if name not in _T0_CACHE:
        _T0_CACHE[name] = opt_of(pi.G, pi.nodes)[0]
    return _T0_CACHE[name]


# =========================================================== 1. the formulation itself
def _lp_feasible(core, xvals):
    """Is the flow polytope non-empty with x pinned to `xvals`?  Pure LP: zero objective,
    every integrality dropped (the chain h variables are *supposed* to come out integral on
    their own -- that is the whole point of D1)."""
    con = core.constraint(None)
    A = np.asarray(con.A.todense())
    lb, ub = np.asarray(con.lb, float), np.asarray(con.ub, float)
    eq = np.isfinite(lb) & np.isfinite(ub) & (lb == ub)
    rows_ub = np.isfinite(ub) & ~eq
    rows_lb = np.isfinite(lb) & ~eq
    A_ub = np.vstack([A[rows_ub], -A[rows_lb]]) if (rows_ub.any() or rows_lb.any()) else None
    b_ub = np.concatenate([ub[rows_ub], -lb[rows_lb]]) if A_ub is not None else None
    lo, hi = core.lo.copy(), core.hi.copy()
    lo[:core.n] = xvals
    hi[:core.n] = xvals
    r = linprog(c=np.zeros(core.n_col), A_ub=A_ub, b_ub=b_ub,
                A_eq=(A[eq] if eq.any() else None), b_eq=(lb[eq] if eq.any() else None),
                bounds=list(zip(lo, hi)), method="highs")
    return bool(r.status == 0)


def _core_for(G, nodes, root_mode="chain", caps="tight"):
    """A core with the gain box wide open, so LP infeasibility can only mean 'not contiguous'."""
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    return flow.build_core(G.subgraph(nodes), nodes, ua, ub, 0.0, root_mode=root_mode,
                           caps=caps, g_lo_a=0.0, g_hi_a=float(np.maximum(ua, 0).sum()),
                           g_lo_b=0.0, g_hi_b=float(np.maximum(ub, 0).sum()))


def test_1_flow_polytope_is_exactly_component_contiguity():
    """The formulation, checked by exhaustion: for every subset of four tiny graphs (one of
    them disconnected), the flow LP is feasible IFF `base.pieces` says the allocation is
    component-wise contiguous.  Both directions -- a formulation that merely *implies*
    contiguity would still be wrong, because it would cut off feasible allocations and make
    the dual bound unsound (exactly CLAUDE.md trap 13's failure)."""
    graphs = {"p8": path_instance(8), "two_component": two_component_instance(),
              "cycle6": nx.cycle_graph(6), "star6": nx.star_graph(5)}
    for k in ("cycle6", "star6"):
        for i, z in enumerate(graphs[k].nodes()):
            graphs[k].nodes[z].update(A=1.0 + 0.1 * i, B=1.0 + 0.07 * i, M=3.0, pos=(i, 0))
    checked = 0
    for caps in ("tight", "loose"):
        for name, G in graphs.items():
            nodes = sorted(G)
            assert len(nodes) <= 8
            core = _core_for(G, nodes, caps=caps)
            for bits in itertools.product((0.0, 1.0), repeat=len(nodes)):
                to_a = {nodes[i] for i in range(len(nodes)) if bits[i]}
                want = base.pieces(G, nodes, to_a)["excess_pieces"] == 0
                got = _lp_feasible(core, np.array(bits))
                assert want == got, (caps, name, sorted(to_a), want, got)
                checked += 1
    print(f"[flow formulation] {checked} fixed-x LP feasibility checks, all agree with pieces()")


def test_1b_continuous_root_indicators_would_be_unsound():
    """Why D1 uses the *prefix chain* and `flow_selroot` pays for **binary** r.

    PLAN.md's literal `sum_K r <= 1, r <= x` is only valid with r integral: a stray piece can
    carry `sum_C r = 0.5` and satisfy the conservation row with room to spare.  This test
    pins that down -- with r relaxed the polytope admits disconnected allocations, and with r
    binary it does not.
    """
    G = path_instance(8)
    nodes = sorted(G)
    core = _core_for(G, nodes, root_mode="binary")
    integ = core.integrality.copy()
    integ[:core.n] = 0                      # x is pinned by bounds; keep r binary
    relaxed_wrong = strict_wrong = 0
    for bits in itertools.product((0.0, 1.0), repeat=len(nodes)):
        to_a = {nodes[i] for i in range(len(nodes)) if bits[i]}
        want = base.pieces(G, nodes, to_a)["excess_pieces"] == 0
        lo, hi = core.lo.copy(), core.hi.copy()
        lo[:core.n] = hi[:core.n] = np.array(bits)
        if _lp_feasible(core, np.array(bits)) != want:
            relaxed_wrong += 1
        res = milp(c=np.zeros(core.n_col), constraints=core.constraint(None),
                   integrality=integ, bounds=Bounds(lo, hi), options=dict(time_limit=20))
        if (res.status == 0) != want:
            strict_wrong += 1
    assert relaxed_wrong > 0, "expected the continuous relaxation of r to admit stray pieces"
    assert strict_wrong == 0, f"binary r must be exact, {strict_wrong} mismatches"
    print(f"[selroot] continuous r wrong on {relaxed_wrong}/256 subsets, binary r exact")


# ============================================================ 2-3. T0 against brute force
def test_2_flow_matches_brute_on_T0():
    for sp, pi in t0_pairs():
        opt = t0_opt(sp.name, pi)
        res = run("flow", pi.G, pi.nodes)
        row = _record(f"flow/{sp.name}", res, base.evaluate(pi.G, pi.nodes, res,
                                                            theta=THETA, lam=LAM), opt)
        assert row["valid"], (sp.name, row["violations"])
        assert res.status == "optimal", (sp.name, res.status, res.message)
        assert res.ub_scope == "global"
        assert row["valid_certificate"], sp.name
        assert abs(row["LB"] - opt) <= 1e-8, (sp.name, row["LB"], opt)
        assert res.UB >= opt - 1e-9, (sp.name, res.UB, opt)
        assert row["excess_pieces"] == 0


def test_3_flow_pwl_matches_brute_on_T0_within_eps():
    for sp, pi in t0_pairs():
        opt = t0_opt(sp.name, pi)
        for key in ("flow_pwl", "flow_pwl_e4"):
            res = run(key, pi.G, pi.nodes)
            row = _record(f"{key}/{sp.name}", res,
                          base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM), opt)
            assert row["valid"], (key, sp.name, row["violations"])
            assert res.status == "optimal", (key, sp.name, res.status, res.message)
            assert res.eps > 0, (key, sp.name, res.eps)
            assert opt - row["LB"] <= res.eps + 1e-9, (key, sp.name, opt - row["LB"], res.eps)
            assert res.UB >= opt - 1e-9, (key, sp.name, res.UB, opt)
            assert res.iters == 1 and res.n_tangents == 0


# ============================================================ 4-6. hand / structural cases
def test_4_hand_graphs_match_brute():
    for name in sorted(HAND_GRAPHS):
        G, nodes = prep(HAND_GRAPHS[name]())
        opt, _ = opt_of(G, nodes)
        for key in ("flow", "flow_pwl"):
            res = run(key, G, nodes)
            row = _record(f"{key}/{name}", res,
                          base.evaluate(G, nodes, res, theta=THETA, lam=LAM), opt)
            assert row["valid"], (key, name, row["violations"])
            assert res.status == "optimal", (key, name, res.status, res.message)
            assert opt - row["LB"] <= res.eps + 1e-8, (key, name, row["LB"], opt)


def test_5_glue_instance():
    """Zero-value glue zips: hugely degenerate optimum, and every variant must still find it
    and certify it (the degeneracy is trap 4's 'fairness alone ties' in miniature)."""
    G, nodes = prep(glue_instance())
    opt, _ = opt_of(G, nodes)
    for key in FLOW_KEYS + ("flow_pwl",):
        res = run(key, G, nodes)
        row = _record(f"{key}/glue", res, base.evaluate(G, nodes, res, theta=THETA, lam=LAM),
                      opt)
        assert row["valid"], (key, row["violations"])
        assert res.status == "optimal", (key, res.status, res.message)
        if key != "flow_rooted":
            assert opt - row["LB"] <= res.eps + 1e-8, (key, row["LB"], opt)
        assert row["excess_pieces"] == 0


def test_6_disconnected_pairs_and_the_rooted_restriction():
    """Multi-component pairs are handled component-wise (mechanism (a)), and the one place a
    global bound and a rooted bound genuinely differ is exercised on purpose."""
    for name, Graw in (("two_component", two_component_instance()),
                       ("three_component", three_component_instance())):
        G, nodes = prep(Graw)
        assert nx.number_connected_components(G.subgraph(nodes)) >= 2
        opt, to_a_star = opt_of(G, nodes)
        for key in ("flow", "flow_pwl"):
            res = run(key, G, nodes)
            row = _record(f"{key}/{name}", res,
                          base.evaluate(G, nodes, res, theta=THETA, lam=LAM), opt)
            assert row["valid"], (key, name, row["violations"])
            assert res.status == "optimal", (key, name, res.status, res.message)
            assert opt - row["LB"] <= res.eps + 1e-8, (key, name, row["LB"], opt)

    G, nodes = prep(component_to_b_instance())
    opt, to_a_star = opt_of(G, nodes)
    comp_b = {10, 11, 12}
    assert not (comp_b & to_a_star), "instance no longer hands a whole component to b"

    res = run("flow", G, nodes)
    row = _record("flow/component_to_b", res,
                  base.evaluate(G, nodes, res, theta=THETA, lam=LAM), opt)
    assert row["valid"] and res.status == "optimal" and res.ub_scope == "global"
    assert row["valid_certificate"]
    assert abs(row["LB"] - opt) <= 1e-8 and not (comp_b & res.to_a)

    rres = run("flow_rooted", G, nodes)
    rrow = _record("flow_rooted/component_to_b", rres,
                   base.evaluate(G, nodes, rres, theta=THETA, lam=LAM), opt)
    assert rrow["valid"], rrow["violations"]
    assert rres.status == "optimal" and rres.ub_scope == "rooted"
    assert rrow["status_eff"] == "optimal_rooted"
    assert rrow["valid_certificate"] is False
    assert rrow["LB"] < opt - 1e-6, (rrow["LB"], opt)
    assert comp_b & rres.to_a, "the rooted restriction must force a zip of comp b to a"
    print(f"[rooted cost] global {opt:.6f} vs rooted {rrow['LB']:.6f} "
          f"({opt - rrow['LB']:.4f} nats)")


# ================================================================ 7. every bound, one place
def test_7_all_bounds_are_valid():
    """`UB >= OPT` and `LB <= UB` on every result any test in this module produced.

    Depends on the earlier tests having run; `run_all.py` executes in definition order, and
    if it did not, the log would simply be shorter -- so the assert on its size is the guard.
    """
    assert len(_BOUND_LOG) >= 40, f"only {len(_BOUND_LOG)} bounds logged -- run the module"
    for e in _BOUND_LOG:
        if e["UB"] is not None:
            assert np.isfinite(e["UB"]), e
            if e["LB"] is not None:
                assert e["LB"] <= e["UB"] + base.CERT_TOL, e
            if e["opt"] is not None and e["scope"] == "global":
                assert e["UB"] >= e["opt"] - 1e-9, e
        if e["LB"] is not None and e["opt"] is not None:
            assert e["LB"] <= e["opt"] + 1e-9, e


# ================================================================ 8. variants agree on value
def test_8_variants_agree_on_the_optimal_value():
    """`flow`, `flow_loosecaps` and `flow_selroot` are three encodings of the *same* feasible
    set, so they must agree on the objective -- never on the allocation, which can tie."""
    for sp, pi in t0_pairs()[:5]:
        opt = t0_opt(sp.name, pi)
        for key in ("flow", "flow_loosecaps", "flow_selroot"):
            res = run(key, pi.G, pi.nodes)
            row = _record(f"{key}/{sp.name}", res,
                          base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM), opt)
            assert row["valid"], (key, sp.name, row["violations"])
            assert res.status == "optimal", (key, sp.name, res.status, res.message)
            assert res.ub_scope == "global"
            assert abs(row["LB"] - opt) <= 1e-8, (key, sp.name, row["LB"], opt)


# ======================================================================== 9. determinism
def test_9_deterministic_in_seed():
    G, nodes = prep(two_component_instance())
    for key in ("flow", "flow_pwl", "flow_selroot"):
        a = run(key, G, nodes, seed=3)
        b = run(key, G, nodes, seed=3)
        assert a.to_a == b.to_a and a.status == b.status, key
        assert a.LB == b.LB and a.UB == b.UB, key
    for sp, pi in t0_pairs()[:2]:
        a = run("flow", pi.G, pi.nodes, seed=11)
        b = run("flow", pi.G, pi.nodes, seed=11)
        assert a.to_a == b.to_a and a.LB == b.LB and a.UB == b.UB, sp.name


# ============================================================================== 10. rho > 0
def test_10_rho_positive_matches_brute():
    """rho = 0 is the model (PLAN.md), but the perimeter columns must still be correct: at
    rho = 2e-3 the y variables have to equal |x_u - x_v| at the optimum, or the objective the
    harness recomputes will not match the one the MILP maximised."""
    rho = 2e-3
    cases = [("hand_p8", prep(HAND_GRAPHS["hand_p8"]()))]
    sp, pi = t0_pairs()[3]
    cases.append((sp.name, (pi.G, pi.nodes)))
    for name, (G, nodes) in cases:
        opt, _ = opt_of(G, nodes, rho=rho)
        for key in ("flow", "flow_pwl"):
            res = run(key, G, nodes, rho=rho)
            row = _record(f"{key}/{name}/rho", res,
                          base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=rho), opt)
            assert row["valid"], (key, name, row["violations"])
            assert res.status == "optimal", (key, name, res.status, res.message)
            assert opt - row["LB"] <= res.eps + 1e-8, (key, name, row["LB"], opt)


# ========================================================================= 11. tiny cap
def test_11_tiny_time_limit_is_a_clean_row():
    """A 0.05 s cap must not raise, must not lie, and must still hand back whatever the
    spanning-tree incumbent found (a valid `time_limit` row with LB and no UB)."""
    sp, pi = t0_pairs()[-1]
    for key in ("flow", "flow_pwl"):
        res = run(key, pi.G, pi.nodes, time_limit=0.05)
        row = base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM)
        _record(f"{key}/tiny_cap", res, row, t0_opt(sp.name, pi))
        assert row["valid"], (key, row["violations"])
        assert res.status in base.STATUSES
        assert res.t_total is not None and res.t_total < 20.0
        if res.to_a is not None:
            assert row["excess_pieces"] == 0, (key, row)


# =================================================================== 12. degenerate values
def test_12_zero_value_pair_is_infeasible():
    """Every zip worth 0 to both sides: no allocation gives two positive gains, so there is
    nothing to certify.  Report `infeasible`, do not crash and do not invent a bound."""
    G, nodes = prep(zero_value_instance())
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    assert ua.sum() == 0 and ub.sum() == 0
    for key in FLOW_KEYS + ("flow_pwl", "flow_pwl_e4"):
        res = run(key, G, nodes)
        row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM)
        assert res.status == "infeasible", (key, res.status, res.message)
        assert res.to_a is None and res.LB is None and res.UB is None, key
        assert row["valid"], (key, row["violations"])


# ============================================================ 13. through the bench driver
def test_13_bench_end_to_end():
    """The methods have to survive the real driver: pool workers, spawn start method, the
    SIGALRM backstop, the validator, and the scoring pass.  Every row must be valid and
    optimal, and `bugs.json` must be empty."""
    run_id = f"_test_w4_{os.getpid()}"
    out = os.path.join(ROOT, "battery", "results", "contiguity", run_id)
    if os.path.isdir(out):
        shutil.rmtree(out)
    cmd = [sys.executable, os.path.join(ROOT, "battery", "code", "contiguity_bench.py"),
           "--methods", "flow,flow_pwl", "--tiers", "T0", "--instances", "^T0_n40",
           "--cap", "10", "--workers", "2", "--run-id", run_id, "--quiet"]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
        assert p.returncode == 0, p.stderr[-3000:]
        with open(os.path.join(out, "rows.jsonl")) as f:
            rows = [json.loads(line) for line in f if line.strip()]
        assert len(rows) >= 12, len(rows)
        for r in rows:
            assert r["valid"], (r["instance"], r["method"], r["violations"])
            assert r["status_eff"] == "optimal", (r["instance"], r["method"], r["status_eff"])
            assert r["excess_pieces"] == 0, (r["instance"], r["method"])
        with open(os.path.join(out, "bugs.json")) as f:
            bugs = json.load(f)
        assert not bugs, bugs
        print(f"[bench] {len(rows)} rows, all valid and optimal, no bugs")
    finally:
        shutil.rmtree(out, ignore_errors=True)


# =============================================== extra: the D3 arithmetic, checked directly
def test_14_chord_error_closed_form():
    """`E(t) = sigma - 1 - log sigma` against a brute-force maximum of `log g - chord(g)`.
    The whole eps guarantee rests on this one formula."""
    for t in (1.0005, 1.001, 1.01, 1.1, 1.5, 2.0, 5.0, 20.0):
        g = np.linspace(1.0, t, 400001)
        s = math.log(t) / (t - 1.0)
        numeric = float(np.max(np.log(g) - s * (g - 1.0)))
        closed = flow_pwl.chord_error(t)
        assert abs(closed - numeric) <= 1e-3 * max(numeric, 1e-12) + 1e-15, (t, closed, numeric)
    # the grid arithmetic: the k it picks really does meet the target, and k-1 would not
    for R in (1.5, 4.0, 50.0):
        for target in (1e-4, 1e-6):
            k, e = flow_pwl.segments_for(R, target)
            assert e <= target, (R, target, k, e)
            if k > 1:
                assert flow_pwl.chord_error(R ** (1.0 / (k - 1))) > target, (R, target, k)
    # k_max binds and the achieved eps is reported honestly rather than the target
    k, e = flow_pwl.segments_for(1e6, 1e-12, k_max=50)
    assert k == 50 and e > 1e-12


if __name__ == "__main__":
    t0 = time.time()
    for name, fn in sorted(((k, v) for k, v in list(globals().items())
                            if k.startswith("test_") and callable(v)),
                           key=lambda kv: kv[0]):
        t = time.time()
        fn()
        print(f"PASS {name} ({time.time() - t:.1f}s)")
    print(f"total {time.time() - t0:.1f}s")
