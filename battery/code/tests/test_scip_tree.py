"""
test_scip_tree.py -- contig_methods/scip_tree.py: SCIP single-tree branch-and-cut with
native `log` and root-free minimal-separator connectivity cuts (PLAN.md W6, Option A).

Acceptance (the W6 brief): the 13 curated T0 pairs match `brute` exactly and certify with
`gap_nats <= base.CERT_TOL`; the hand instances (a disconnected pair graph, zero-value glue,
a trident) match `brute`; every cut is checked against the reference optimum via
`check_opt`; the solve is deterministic; a warm start at the optimum costs no more nodes
than a cold one and is feasible at t = 0; `_repair` turns random infeasible masks into
feasible allocations; rho = 2e-3 on the C8 pair agrees with the legacy `current_tight`; and
the benchmark driver produces 13 certified rows and no bugs.

Cut validity is the one silent failure mode -- an invalid separator cut just looks like a
good bound -- so `check_opt` runs on *every* T0 pair here, not on a sample.

The slow tier (the six named failures at a 60 s cap, and the 320/464-zip C7b pairs) lives in
`test_scip_tree_slow.py`.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import instances as I                                  # noqa: E402
import synth                                           # noqa: E402
import territory as T                                  # noqa: E402
from contig_methods import REGISTRY, base, brute       # noqa: E402
from contig_methods import scip_tree as ST             # noqa: E402
import test_base as TB                                 # noqa: E402  (shared hand instances)

THETA, LAM = 0.40, 0.30
CAP = 30.0

_T0_CACHE: list = []
_BRUTE_CACHE: dict = {}


# --------------------------------------------------------------------------- helpers
def _t0():
    """The 13 curated T0 pairs, built once."""
    if not _T0_CACHE:
        _T0_CACHE.extend(I.build_pair(sp) for sp in I.build_T0())
    return _T0_CACHE


def _brute(pi):
    key = pi.spec.name
    if key not in _BRUTE_CACHE:
        _BRUTE_CACHE[key] = brute.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0,
                                        respect_state=False, time_limit=CAP, seed=0)
    return _BRUTE_CACHE[key]


def _run(G, nodes, *, rho=0.0, time_limit=CAP, **kw):
    res = base.run_method(ST.solve, G, nodes, theta=THETA, lam=LAM, rho=rho,
                          time_limit=time_limit, seed=0, **kw)
    row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=rho)
    return res, row


def _hand_pairs():
    """(name, G, nodes) for the hand instances small enough for `brute`."""
    out = [("two_component", TB.two_component_instance()),
           ("glue", TB.glue_instance()),
           ("trident", I.HAND_GRAPHS["hand_trident"]()),
           ("cycle10", I.HAND_GRAPHS["hand_cycle10"]())]
    return [(name, G, sorted(G)) for name, G in out]


# ------------------------------------------------------------------------- registry
def test_registry_exposes_scip_tree_and_the_oa_variant():
    assert "scip_tree" in REGISTRY and REGISTRY["scip_tree"].exact
    assert REGISTRY["scip_tree"].max_n is None
    assert REGISTRY["scip_tree_oa"].base_name == "scip_tree"
    assert REGISTRY["scip_tree_oa"].kwargs == dict(formulation="oa")


# ------------------------------------------------------------- T0 ground truth + cuts
def test_t0_matches_brute_and_certifies_with_checked_cuts():
    """13/13 against exhaustive enumeration, every cut validated against that optimum.

    `check_opt` asserts, before each separator cut is added, that the reference optimum
    satisfies it -- so a cut family that quietly excluded the optimum would raise here
    rather than surface as a suspiciously good bound.
    """
    pairs = _t0()
    assert len(pairs) == 13, f"T0 should be 13 curated pairs, got {len(pairs)}"
    for pi in pairs:
        b = _brute(pi)
        res, row = _run(pi.G, pi.nodes, check_opt=b.to_a)
        assert row["valid"], (pi.spec.name, row["violations"])
        assert row["valid_certificate"], (pi.spec.name, res.status, row["gap_nats"])
        assert res.ub_scope == "global"
        assert row["excess_pieces"] == 0, pi.spec.name
        assert row["gap_nats"] <= base.CERT_TOL, (pi.spec.name, row["gap_nats"])
        assert abs(res.LB - b.LB) < 1e-9, (pi.spec.name, res.LB, b.LB)
        if res.to_a != b.to_a:                        # a tie is allowed, a worse value is not
            assert abs(res.LB - b.LB) < 1e-9, (pi.spec.name, "different set, different value")


def test_oa_variant_matches_brute_on_t0():
    """The cross-check formulation (tangents instead of SCIP's native log) agrees."""
    for pi in _t0():
        b = _brute(pi)
        res, row = _run(pi.G, pi.nodes, formulation="oa", check_opt=b.to_a)
        assert row["valid"], (pi.spec.name, row["violations"])
        assert row["valid_certificate"], (pi.spec.name, res.status, row["gap_nats"])
        assert abs(res.LB - b.LB) < 1e-9, (pi.spec.name, res.LB, b.LB)
        assert res.n_tangents > 0, "the OA build must actually add tangents"


def test_hand_instances_match_brute():
    """Disconnected pair graph, zero-value glue, a degree-3 block tree, a cycle."""
    for name, G, nodes in _hand_pairs():
        b = brute.solve(G, nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                        time_limit=CAP, seed=0)
        res, row = _run(G, nodes, check_opt=b.to_a)
        assert row["valid"], (name, row["violations"])
        assert row["valid_certificate"], (name, res.status, row["gap_nats"])
        assert abs(res.LB - b.LB) < 1e-9, (name, res.LB, b.LB)
        assert row["excess_pieces"] == 0, name


def test_disconnected_pair_bound_is_global_not_rooted():
    """The mechanism-(a) regression: the pair graph of `current`'s counterexample.

    `current` reports `heuristic` here because its root-fixed separator cuts are unsound on a
    disconnected pair graph (CLAUDE.md trap 13).  scip_tree fixes no root, so it must return
    a genuine global certificate at the true optimum.
    """
    G = synth.scenario("S1_aligned", n=50, seed=2)
    zips = sorted(T.zips_for_pair(G, 1, 1))
    H0, _ = base.filter_pair(G, zips, respect_state=False)
    assert nx.number_connected_components(H0) == 2
    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
    nodes = sorted(H)
    b = brute.solve(H, nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                    time_limit=CAP, seed=0)
    res, row = _run(H, nodes, check_opt=b.to_a)
    assert res.ub_scope == "global"
    assert row["valid_certificate"], (res.status, row["gap_nats"])
    assert abs(res.LB - b.LB) < 1e-9, (res.LB, b.LB)


# --------------------------------------------------------------------- determinism
def test_deterministic():
    pi = _t0()[-1]
    r1, _ = _run(pi.G, pi.nodes)
    r2, _ = _run(pi.G, pi.nodes)
    assert r1.to_a == r2.to_a
    assert r1.nodes == r2.nodes
    assert r1.n_cuts == r2.n_cuts
    assert r1.status == r2.status
    assert abs(r1.LB - r2.LB) < 1e-15


# --------------------------------------------------------------------- warm starting
def test_warm_start_at_the_optimum_costs_no_more_nodes():
    pi = _t0()[-1]
    b = _brute(pi)
    cold, _ = _run(pi.G, pi.nodes)
    warm, wrow = _run(pi.G, pi.nodes, warm_start=b.to_a)
    assert warm.extra["warm_source"] == "given"
    assert wrow["valid_certificate"]
    assert abs(warm.LB - b.LB) < 1e-9
    assert warm.t_first_feasible is not None and warm.t_first_feasible < 0.5
    assert warm.nodes <= cold.nodes, (warm.nodes, cold.nodes)


def test_infeasible_warm_start_is_repaired_not_rejected():
    pi = _t0()[-1]
    nodes = pi.nodes
    bad = set(nodes[::2])                                  # almost certainly fragmented
    res, row = _run(pi.G, nodes, warm_start=bad)
    assert res.extra["warm_source"] in ("given", "given_repaired")
    assert row["valid_certificate"]


def test_fallback_warm_start_is_feasible_without_help():
    for pi in _t0()[:4]:
        ua, ub = base.utilities(pi.G, pi.nodes, THETA, LAM)
        ctx = ST._Ctx(pi.G, pi.nodes, ua, ub, 0.0)
        ws, src = ST._fallback_warm_start(ctx)
        assert ws is not None and src != "none"
        assert ctx.is_feasible(ws)
        assert math.isfinite(ctx.objective(ws))


# -------------------------------------------------------------------------- repair
def test_repair_makes_random_masks_feasible():
    """20 random (mostly infeasible) masks on a mid-size pair -> feasible allocations."""
    pi = _t0()[-1]
    ua, ub = base.utilities(pi.G, pi.nodes, THETA, LAM)
    ctx = ST._Ctx(pi.G, pi.nodes, ua, ub, 0.0)
    rng = np.random.default_rng(17)
    n_infeasible_seen = 0
    for _ in range(20):
        mask = rng.random(len(pi.nodes)) < 0.5
        to_a = {z for z, m in zip(pi.nodes, mask) if m}
        n_infeasible_seen += not ctx.is_feasible(to_a)
        fixed = ST._repair(ctx, to_a)
        assert fixed is not None, to_a
        assert ctx.is_feasible(fixed), (to_a, fixed)
        assert base.is_feasible(pi.G, pi.nodes, fixed)      # the contract's own definition
        assert math.isfinite(ctx.objective(fixed))
    assert n_infeasible_seen >= 10, "the random masks were not challenging enough"


def test_subtree_splits_are_feasible_by_construction():
    pi = _t0()[-1]
    ua, ub = base.utilities(pi.G, pi.nodes, THETA, LAM)
    ctx = ST._Ctx(pi.G, pi.nodes, ua, ub, 0.0)
    best, obj = ST._subtree_splits(ctx)
    assert best is not None and math.isfinite(obj)
    assert base.is_feasible(pi.G, pi.nodes, best)


# ------------------------------------------------------------------------- rho > 0
def test_rho_positive_on_the_c8_pair_agrees_with_current_tight():
    """rho = 2e-3 on the 62-zip C8 pair: the edge variables and the perimeter penalty.

    `current_tight` is rooted, so its optimum is over a *restriction* -- scip_tree's global
    optimum can only be at least as good.  On this pair the legacy roots happen to be the
    optimal ones, so the two objectives agree exactly.
    """
    G = synth.scenario("S1_aligned", n=200, seed=1)
    zips = sorted(T.zips_for_pair(G, 3, 3))
    assert len(zips) == 62
    H0, _ = base.filter_pair(G, zips, respect_state=False)
    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
    nodes = sorted(H)

    res, row = _run(H, nodes, rho=2e-3, time_limit=60.0)
    assert row["valid"], row["violations"]
    assert row["valid_certificate"], (res.status, row["gap_nats"])
    assert row["excess_pieces"] == 0

    spec = REGISTRY["current_tight"]
    cres = base.run_method(spec.solve, H, nodes, theta=THETA, lam=LAM, rho=2e-3,
                           time_limit=60.0, **spec.kwargs)
    crow = base.evaluate(H, nodes, cres, theta=THETA, lam=LAM, rho=2e-3)
    assert crow["LB"] is not None
    assert row["LB"] >= crow["LB"] - 1e-9, (row["LB"], crow["LB"])
    assert abs(row["LB"] - crow["LB"]) < 1e-6, (row["LB"], crow["LB"])


# ------------------------------------------------------------------- harness smoke
def test_harness_run_certifies_every_t0_row():
    import contiguity_bench as CB

    run_id = f"_test_w6_{os.getpid()}"
    run_dir = CB.RESULTS_ROOT / run_id
    try:
        rc = CB.main(["--tiers", "T0", "--methods", "scip_tree", "--cap", "20",
                      "--workers", "2", "--quiet", "--run-id", run_id])
        assert rc == 0
        rows = [json.loads(line) for line in open(run_dir / "rows.jsonl") if line.strip()]
        assert len(rows) == 13, len(rows)
        assert all(r["valid"] for r in rows), [r["violations"] for r in rows if not r["valid"]]
        assert all(r["valid_certificate"] for r in rows), \
            [(r["instance"], r["status"], r["gap_nats"]) for r in rows
             if not r["valid_certificate"]]
        assert all(r["excess_pieces"] == 0 for r in rows)
        assert json.load(open(run_dir / "bugs.json")) == []
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
