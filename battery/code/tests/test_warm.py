"""
test_warm.py -- contig_methods/warm.py: Option F warm starts, F1 spanning-tree
bisection + boundary-swap local search and F3 OT-threshold construction (PLAN.md
OPTIONS.md sec:7, W5).

Acceptance (TEST_PLAN sec:7): F1 feasible on 100% of instances, < 5s at n=800,
cross-method gap reported (here: LB vs brute's OPT on T0/hand, and vs the S0
`current_tu` UB where available on the named failures).  F3 at k in {1, 2, 4}
feasible on 100%; a comparison table against F1 decides whether F3 is worth keeping
as a MIP start (kept only if it beats F1 on median gap or time-to-certificate).
Both are `status="heuristic"`, `UB=None`: no bound is claimed anywhere in this file.
"""
from __future__ import annotations

import math
import os
import statistics
import sys
import time
import uuid

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import instances                                    # noqa: E402
import synth, territory as T                         # noqa: E402
from contig_methods import REGISTRY, base, brute      # noqa: E402

THETA, LAM = instances.THETA, instances.LAM


# ------------------------------------------------------------------- hand instances
def path_instance(n=8):
    """Same construction as test_base.py / test_brute.py: monotone ratio along a
    path, so a prefix is optimal and F1 should find it exactly."""
    G = nx.path_graph(n)
    for i in range(n):
        A = 1.0 + 0.9 * (n - 1 - i) / (n - 1)
        B = 1.0 + 0.9 * i / (n - 1)
        G.nodes[i].update(A=A, B=B, M=4.0 + 0.1 * i, pos=(i / n, 0.5))
    return G


def two_component_instance():
    """P4 + P3, disjoint: the pair graph itself has two components (C.0 #1)."""
    G = path_instance(4)
    H = nx.relabel_nodes(path_instance(3), {0: 10, 1: 11, 2: 12})
    return nx.union(G, H)


def glue_instance():
    """P6 with two zero-value (A=B=M=0) zips in the middle (regime (d))."""
    G = path_instance(6)
    for z in (2, 3):
        G.nodes[z].update(A=0.0, B=0.0, M=0.0)
    return G


# ---------------------------------------------------------------------- T0 helpers
def _run(name, H, nodes, time_limit=20.0, seed=0):
    spec = REGISTRY[name]
    res = base.run_method(spec.solve, H, nodes, theta=THETA, lam=LAM, rho=0.0,
                          time_limit=time_limit, seed=seed, **spec.kwargs)
    row = base.evaluate(H, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    return res, row


# --------------------------------------------------------------------------- registry
def test_registry_variants():
    expect = {
        "warm": {},
        "warm_f1": dict(method="f1"),
        "warm_f1_n200": dict(method="f1", n_trees=200),
        "warm_f3_k1": dict(method="f3", k=1),
        "warm_f3_k2": dict(method="f3", k=2),
        "warm_f3_k4": dict(method="f3", k=4),
    }
    for name, kwargs in expect.items():
        assert name in REGISTRY, name
        assert REGISTRY[name].base_name == "warm"
        assert REGISTRY[name].kwargs == kwargs, (name, REGISTRY[name].kwargs)
        assert not REGISTRY[name].exact


# ---------------------------------------------------------------------------- T0
def test_warm_f1_feasible_and_le_brute_on_t0():
    """Acceptance per the brief: feasible on all, LB <= brute.LB + 1e-9 on all, and
    report (not gate on) how many hit the exact optimum.  F1 carries no optimality
    guarantee on a general (non-monotone-ratio) graph -- CLAUDE.md trap 1 measures
    the analogous ratio-prefix heuristic at ~45% exact-match at this n range, with
    a mean shortfall of a few tenths of a percent; F1 (spanning-tree cuts + boundary
    local search) lands in the same regime empirically (see the printed table),
    which is why the acceptance bar here is soundness (LB <= OPT) and a bounded
    shortfall, not exact match."""
    specs = instances.build_T0()
    assert len(specs) >= 10
    n_optimal = 0
    shortfalls = []
    print("\n[warm_f1 vs brute on T0]")
    for sp in specs:
        pi = instances.build_pair(sp, with_bounds=False)
        bres = brute.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0,
                           respect_state=False, time_limit=30, seed=0)
        OPT = bres.LB
        res, row = _run("warm_f1", pi.G, pi.nodes)
        assert row["valid"], (sp.name, row["violations"])
        assert res.status == "heuristic" and res.UB is None
        assert row["excess_pieces"] == 0
        assert row["LB"] is not None and row["LB"] <= OPT + 1e-9, (sp.name, row["LB"], OPT)
        shortfall = OPT - row["LB"]
        shortfalls.append(shortfall)
        matched = shortfall < 1e-6
        n_optimal += matched
        print(f"  {sp.name:<20} n={sp.n_expected:<3} OPT={OPT:.6f}  F1={row['LB']:.6f}"
             f"  shortfall={shortfall:.6f}  match={matched}")
    mean_shortfall = sum(shortfalls) / len(shortfalls)
    print(f"[warm_f1 vs brute] {n_optimal}/{len(specs)} exact matches, "
         f"mean shortfall {mean_shortfall:.6f} nats, max {max(shortfalls):.6f} nats")
    assert mean_shortfall < 0.02, f"mean shortfall {mean_shortfall:.6f} nats looks too large"


# ------------------------------------------------------------------------- hand
def test_hand_instances_feasible():
    for name, G in (("path8", path_instance(8)),
                    ("two_component", two_component_instance()),
                    ("glue", glue_instance())):
        nodes = sorted(G)
        for method in ("warm_f1", "warm_f3_k2"):
            res, row = _run(method, G, nodes)
            assert row["valid"], (name, method, row["violations"])
            assert row["excess_pieces"] == 0, (name, method)


def test_path_monotone_ratio_f1_finds_optimum():
    G = path_instance(10)
    nodes = sorted(G)
    bres = brute.solve(G, nodes, theta=THETA, lam=LAM, rho=0.0,
                       respect_state=False, time_limit=30, seed=0)
    res, row = _run("warm_f1", G, nodes)
    assert row["valid"]
    assert abs(row["LB"] - bres.LB) < 1e-9, (row["LB"], bres.LB)


def test_disconnected_pair_feasible_pieces_a_can_exceed_one():
    """Disconnected pair graph: feasible with excess_pieces == 0, and pieces_a may
    legitimately be > 1 (one piece per pair-graph component that lands on A)."""
    G = two_component_instance()
    nodes = sorted(G)
    for method in ("warm_f1", "warm_f3_k1"):
        res, row = _run(method, G, nodes)
        assert row["valid"], (method, row["violations"])
        assert row["excess_pieces"] == 0
        assert row["pair_components"] == 2


# --------------------------------------------------------------- named failures
def test_named_failures_feasible():
    rows = []
    for sp in instances.named_failures():
        pi = instances.build_pair(sp, with_bounds=False)
        for method in ("warm_f1", "warm_f3_k2"):
            t0 = time.perf_counter()
            res, row = _run(method, pi.G, pi.nodes, time_limit=30.0)
            dt = time.perf_counter() - t0
            assert row["valid"], (sp.name, method, row["violations"])
            assert row["excess_pieces"] == 0, (sp.name, method)
            rows.append((sp.name, method, sp.n_expected, dt, row["LB"]))

    # compare next to S0's current_tu UB when that run exists on disk (soft: skip
    # the comparison, never the feasibility check above, if it doesn't)
    s0_path = os.path.join(ROOT, "battery", "results", "contiguity", "s0_2026-08-29",
                           "rows.jsonl")
    ub_by_name = {}
    if os.path.exists(s0_path):
        import json
        with open(s0_path) as f:
            for line in f:
                r = json.loads(line)
                if r.get("method") == "current_tu" and r.get("UB") is not None:
                    ub_by_name[r.get("instance")] = r["UB"]
    print("\n[warm named-failure timings]")
    for name, method, n, dt, lb in rows:
        ub = ub_by_name.get(name)
        print(f"  {name:<32} n={n:<4} {method:<12} {dt:6.2f}s  LB={lb!r}  current_tu UB={ub!r}")


# ------------------------------------------------------------------------ T2 scale
def test_warm_f1_t2_c7b_under_5s():
    specs = [s for s in instances.build_T2() if s.case.startswith("C7b")]
    assert len(specs) >= 6, "expected the eight C7b n=800 pairs"
    for sp in specs:
        pi = instances.build_pair(sp, with_bounds=False)
        t0 = time.perf_counter()
        res, row = _run("warm_f1", pi.G, pi.nodes, time_limit=15.0)
        dt = time.perf_counter() - t0
        assert row["valid"], (sp.name, row["violations"])
        assert row["excess_pieces"] == 0
        assert dt < 5.0, f"{sp.name} (n={sp.n_expected}) took {dt:.2f}s, budget is 5s"
        print(f"[warm_f1 n={sp.n_expected}] {dt:.3f}s")


# ------------------------------------------------------------------- F3 vs F1 table
def test_f3_variants_feasible_and_comparison_table():
    rows = []   # (instance, n, f1_lb, f1_dt, k, f3_lb, f3_dt)

    def _cases():
        for sp in instances.build_T0():
            pi = instances.build_pair(sp, with_bounds=False)
            yield sp.name, pi.G, pi.nodes
        for sp in instances.named_failures():
            pi = instances.build_pair(sp, with_bounds=False)
            yield sp.name, pi.G, pi.nodes

    for name, G, nodes in _cases():
        t0 = time.perf_counter()
        f1_res, f1_row = _run("warm_f1", G, nodes, time_limit=30.0)
        f1_dt = time.perf_counter() - t0
        assert f1_row["valid"], (name, "warm_f1", f1_row["violations"])
        for k, method in ((1, "warm_f3_k1"), (2, "warm_f3_k2"), (4, "warm_f3_k4")):
            t0 = time.perf_counter()
            f3_res, f3_row = _run(method, G, nodes, time_limit=30.0)
            f3_dt = time.perf_counter() - t0
            assert f3_row["valid"], (name, method, f3_row["violations"])
            assert f3_row["excess_pieces"] == 0
            rows.append((name, len(nodes), f1_row["LB"], f1_dt, k, f3_row["LB"], f3_dt))

    print("\n[F1 vs F3 table: instance, n, F1 LB, F1 s, k, F3 LB, F3 s, F3-F1]")
    n_f3_better = 0
    diffs = []
    for name, n, f1_lb, f1_dt, k, f3_lb, f3_dt in rows:
        d = (f3_lb - f1_lb) if (f1_lb is not None and f3_lb is not None) else None
        if d is not None:
            diffs.append(d)
            if d > 1e-9:
                n_f3_better += 1
        print(f"  {name:<32} n={n:<4} F1={f1_lb!r:<20} {f1_dt:5.2f}s  "
             f"k={k}  F3={f3_lb!r:<20} {f3_dt:5.2f}s  diff={d}")
    if diffs:
        print(f"[F3 vs F1] median diff (F3-F1) = {statistics.median(diffs):.6g}, "
             f"F3 strictly better on {n_f3_better}/{len(diffs)} rows")


# --------------------------------------------------------------------- determinism
def test_determinism():
    G = glue_instance()
    nodes = sorted(G)
    for method in ("warm_f1", "warm_f3_k2"):
        r1, _ = _run(method, G, nodes, seed=13)
        r2, _ = _run(method, G, nodes, seed=13)
        assert r1.to_a == r2.to_a, method
        assert r1.status == r2.status
        if r1.LB is not None and r2.LB is not None:
            assert abs(r1.LB - r2.LB) < 1e-12


# -------------------------------------------------------------------------- harness
def test_harness_smoke():
    import contiguity_bench as cb
    run_id = f"_test_w5_{os.getpid()}_{uuid.uuid4().hex[:6]}"
    out_dir = os.path.join(ROOT, "battery", "results", "contiguity", run_id)
    try:
        rc = cb.main(["--tiers", "T0", "--methods", "warm_f1,warm_f3_k2", "--cap", "30",
                     "--workers", "2", "--quiet", "--run-id", run_id])
        assert rc == 0
        import json
        rows_path = os.path.join(out_dir, "rows_scored.jsonl")
        assert os.path.exists(rows_path)
        with open(rows_path) as f:
            rows = [json.loads(line) for line in f]
        assert len(rows) > 0
        for r in rows:
            assert r["valid"], r.get("violations")
            assert r["status"] == "heuristic"
            assert r["UB"] is None
            if r.get("gap_star_nats") is not None:
                assert r["gap_star_nats"] >= -1e-9
    finally:
        import shutil
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
