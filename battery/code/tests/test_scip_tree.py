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
    assert REGISTRY["scip_tree_psimplex"].base_name == "scip_tree"
    assert REGISTRY["scip_tree_psimplex"].kwargs["lp_params"]["lp/initalgorithm"] == "p" 


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


# ------------------------------------------------- W6b: the ladder and the MIP start
def test_retryable_classifies_a_numerical_abort_but_not_a_spent_budget():
    """`_retryable` is what continues the ladder; the reported status is not.

    The S2 regression this guards: an LP abort reaches `_finish` as `scip_status ==
    "unknown"` plus a raised exception, and `_finish` deliberately rewrites it to
    `time_limit` (so `errors` in summary.csv counts crashes only).  Reading the *status* to
    decide whether to retry therefore stopped the ladder on its first rung.
    """
    ours = dict(interrupted=True)
    theirs = dict(interrupted=False)
    # continue: the engine gave up on its own LPs
    assert ST._retryable("unknown", theirs, aborted=True)
    assert ST._retryable("unknown", theirs, aborted=False)
    assert ST._retryable(None, theirs, aborted=False)
    assert ST._retryable("userinterrupt", theirs, aborted=False)   # SCIP's own interrupt
    # stop: the budget really is gone, or the answer really is in
    assert not ST._retryable("timelimit", theirs, aborted=False)
    assert not ST._retryable("optimal", theirs, aborted=False)
    assert not ST._retryable("infeasible", theirs, aborted=False)
    assert not ST._retryable("gaplimit", theirs, aborted=False)
    assert not ST._retryable("userinterrupt", ours, aborted=False)  # our deadline


def test_ladder_runs_every_rung_after_repeated_aborts():
    """A mocked `_solve_once` that always aborts must be called on all four rungs.

    Each rung sees the remaining budget, restarts from the previous rung's allocation, and
    the merged answer keeps the tightest UB and the best LB; `extra["attempts"]` records
    all of them with wall times.  With budget left over the ladder is *extended* with
    further OA rungs at a shifted seed, up to `max_rungs`.
    """
    pi = _t0()[0]

    def make_fake(calls):
        def fake(G, nodes, **kw):
            calls.append((kw["feastol"], kw["formulation"], kw["seed"], kw["time_limit"],
                          kw["warm_start"]))
            k = len(calls)
            return base.Result(status="time_limit", to_a=set(nodes[:1]),
                               LB=1.0 + 0.01 * k, UB=9.0 - 0.01 * k, ub_scope="global",
                               extra=dict(scip_status="unknown", retryable=True))
        return fake

    calls = []
    real = ST._solve_once
    ST._solve_once = make_fake(calls)
    try:
        res = ST.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                       time_limit=20.0, seed=0, mip_start=None, max_rungs=4)
    finally:
        ST._solve_once = real

    assert len(calls) == 4, calls                      # 1e-9, 1e-7, 1e-6 native, then oa
    assert [c[0] for c in calls] == [1e-9, 1e-7, 1e-6, 1e-6]
    assert [c[1] for c in calls] == ["native", "native", "native", "oa"]
    assert calls[1][4] is not None, "a rung must restart from the previous allocation"
    assert all(c[3] > 0 for c in calls)
    attempts = res.extra["attempts"]
    assert len(attempts) == 4 and res.extra["n_rungs"] == 4
    assert all(a["retryable"] and "t" in a for a in attempts)
    assert abs(res.LB - 1.04) < 1e-12 and abs(res.UB - 8.96) < 1e-12   # best LB, tightest UB

    # budget left over -> extension rungs, on the robust formulation, at a shifted seed
    calls2 = []
    ST._solve_once = make_fake(calls2)
    try:
        ST.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                 time_limit=20.0, seed=0, mip_start=None, max_rungs=7)
    finally:
        ST._solve_once = real
    assert len(calls2) == 7, calls2
    assert [c[1] for c in calls2[3:]] == ["oa"] * 4
    assert [c[2] for c in calls2[3:]] == [0, 1, 2, 3], "extension rungs must shift the seed"


def test_ladder_stops_when_the_budget_is_spent_or_the_answer_is_certified():
    """A genuine `timelimit`, and a certificate, both end the ladder on the first rung."""
    import time as _time
    pi = _t0()[0]
    for scip_status, lb, ub, burn in (("timelimit", 1.0, 9.0, 1.8), ("optimal", 5.0, 5.0, 0.0)):
        calls = []

        def fake(G, nodes, _s=scip_status, _lb=lb, _ub=ub, _burn=burn, **kw):
            calls.append(kw["feastol"])
            _time.sleep(_burn)                 # a genuine time limit costs the whole budget
            return base.Result(status="time_limit" if _s == "timelimit" else "optimal",
                               to_a=set(nodes[:1]), LB=_lb, UB=_ub, ub_scope="global",
                               extra=dict(scip_status=_s,
                                          retryable=ST._retryable(_s, dict(interrupted=False),
                                                                  aborted=False)))

        real = ST._solve_once
        ST._solve_once = fake
        try:
            ST.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                     time_limit=2.0, seed=0, mip_start=None)
        finally:
            ST._solve_once = real
        assert calls == [1e-9], (scip_status, calls)


def test_short_stop_treats_scips_own_clock_as_a_failure_not_a_spent_budget():
    """SCIP has been seen to report `timelimit` after 57 s of a 106 s rung under load.

    Our wall clock is the authority on whether the budget is gone, so a `timelimit` well
    inside the rung's allocation continues the ladder instead of ending the solve early.
    """
    assert ST._short_stop("timelimit", 57.0, 106.0)
    assert not ST._short_stop("timelimit", 100.0, 106.0)
    assert not ST._short_stop("unknown", 1.0, 106.0)     # already retryable for other reasons
    assert not ST._short_stop("optimal", 1.0, 106.0)
    assert not ST._short_stop("timelimit", 0.1, 0.5)     # sub-_MIN_RUNG rungs never retry

    # end to end: an instant "timelimit" is retried, and the attempt says why
    pi = _t0()[0]
    calls = []

    def fake(G, nodes, **kw):
        calls.append(kw["feastol"])
        return base.Result(status="time_limit", to_a=set(nodes[:1]), LB=1.0, UB=9.0,
                           ub_scope="global",
                           extra=dict(scip_status="timelimit", retryable=False))

    real = ST._solve_once
    ST._solve_once = fake
    try:
        res = ST.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                       time_limit=20.0, seed=0, mip_start=None, max_rungs=3)
    finally:
        ST._solve_once = real
    assert len(calls) == 3, calls
    assert all(a["short_stop"] for a in res.extra["attempts"])


def test_a_loosened_rung_that_certifies_is_retried_at_the_tight_tolerance():
    """`tighten_back`: SCIP `optimal` at 1e-6 leaves a ~1e-7 gap; re-solve at 1e-9.

    The S2 re-run landed exactly there on the 124- and 135-zip C7b pairs -- certified by
    SCIP, gap 1.1e-7 / 3.0e-8, and ~1000 s of the 1200 s budget unspent.
    """
    pi = _t0()[0]
    calls = []

    def fake(G, nodes, **kw):
        calls.append((kw["feastol"], kw["formulation"]))
        if len(calls) == 3:                    # the loosened rung certifies to its tolerance
            return base.Result(status="gap_limit", to_a=set(nodes[:1]), LB=5.0, UB=5.0 + 1e-7,
                               ub_scope="global",
                               extra=dict(scip_status="optimal", retryable=False))
        if len(calls) == 4:                    # ... and the tight retry closes it
            return base.Result(status="optimal", to_a=set(nodes[:1]), LB=5.0, UB=5.0,
                               ub_scope="global",
                               extra=dict(scip_status="optimal", retryable=False))
        return base.Result(status="time_limit", to_a=set(nodes[:1]), LB=1.0, UB=9.0,
                           ub_scope="global",
                           extra=dict(scip_status="unknown", retryable=True))

    real = ST._solve_once
    ST._solve_once = fake
    try:
        res = ST.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                       time_limit=60.0, seed=0, mip_start=None)
    finally:
        ST._solve_once = real
    # the tight native rung already ran as rung 1, so the retry is the tight OA one
    assert calls == [(1e-9, "native"), (1e-7, "native"), (1e-6, "native"),
                     (1e-9, "oa")], calls
    assert res.extra["attempts"][2]["tighten_back"] is True
    assert res.status == "optimal" and res.UB == 5.0 and res.LB == 5.0

    # a near-certified gap is terminal: when the tight rungs are used up, stop -- do not
    # spend the rest of the budget on the ordinary ladder (measured waste: 1027 s)
    calls3 = []

    def fake3(G, nodes, **kw):
        calls3.append((kw["feastol"], kw["formulation"]))
        if len(calls3) >= 3:
            return base.Result(status="gap_limit", to_a=set(nodes[:1]), LB=5.0, UB=5.0 + 1e-7,
                               ub_scope="global",
                               extra=dict(scip_status="optimal", retryable=False))
        return base.Result(status="time_limit", to_a=set(nodes[:1]), LB=1.0, UB=9.0,
                           ub_scope="global",
                           extra=dict(scip_status="unknown", retryable=True))

    ST._solve_once = fake3
    try:
        res3 = ST.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                        time_limit=60.0, seed=0, mip_start=None)
    finally:
        ST._solve_once = real
    assert calls3 == [(1e-9, "native"), (1e-7, "native"), (1e-6, "native"),
                      (1e-9, "oa")], calls3
    assert res3.status == "gap_limit"

    # switched off, the ladder stops on the certified-but-coarse rung
    calls2 = []

    def fake2(G, nodes, **kw):
        calls2.append(kw["feastol"])
        if len(calls2) == 3:
            return base.Result(status="gap_limit", to_a=set(nodes[:1]), LB=5.0, UB=5.0 + 1e-7,
                               ub_scope="global",
                               extra=dict(scip_status="optimal", retryable=False))
        return base.Result(status="time_limit", to_a=set(nodes[:1]), LB=1.0, UB=9.0,
                           ub_scope="global",
                           extra=dict(scip_status="unknown", retryable=True))

    ST._solve_once = fake2
    try:
        ST.solve(pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                 time_limit=60.0, seed=0, mip_start=None, tighten_back=False)
    finally:
        ST._solve_once = real
    assert calls2 == [1e-9, 1e-7, 1e-6], calls2


def test_mip_start_f1_feeds_the_solver_and_is_switchable():
    """`mip_start="f1"` hands `warm.solve(method="f1")`'s allocation to SCIP as a MIP start."""
    pi = _t0()[-1]
    res_f1, row_f1 = _run(pi.G, pi.nodes, mip_start="f1")
    assert res_f1.extra["mip_start"] == "warm_f1"
    assert res_f1.extra["warm_source"] == "given"          # F1's allocation is feasible
    assert row_f1["valid_certificate"]

    res_int, row_int = _run(pi.G, pi.nodes, mip_start="internal")
    assert res_int.extra["mip_start"] == "off"
    assert res_int.extra["warm_source"] in ("ratio_prefix_repaired", "subtree_split",
                                            "single_component")
    assert row_int["valid_certificate"]
    assert abs(res_f1.LB - res_int.LB) < 1e-9

    # an explicit warm start still wins over the F1 call
    b = _brute(pi)
    res_given, _ = _run(pi.G, pi.nodes, warm_start=b.to_a, mip_start="f1")
    assert res_given.extra["mip_start"] == "given"
    assert res_given.extra["warm_source"] == "given"


def test_fractional_separation_runs_and_keeps_the_certificate():
    """`conssepalp` fires at the root, its cuts pass `check_opt`, and T0 still certifies."""
    n_with_cuts = 0
    for pi in _t0():
        b = _brute(pi)
        res, row = _run(pi.G, pi.nodes, check_opt=b.to_a, sepa_frac=True)
        assert row["valid_certificate"], (pi.spec.name, res.status, row["gap_nats"])
        assert abs(res.LB - b.LB) < 1e-9, (pi.spec.name, res.LB, b.LB)
        assert res.extra["n_sepa_rounds"] >= 1, pi.spec.name
        n_with_cuts += res.extra["n_sepa_cuts"] > 0
    assert n_with_cuts >= 1, "no fractional cut was ever separated on T0"


def test_fractional_separation_can_be_switched_off():
    pi = _t0()[-1]
    b = _brute(pi)
    res, row = _run(pi.G, pi.nodes, check_opt=b.to_a, sepa_frac=False)
    assert res.extra["n_sepa_rounds"] == 0 and res.extra["n_sepa_cuts"] == 0
    assert row["valid_certificate"]
    assert abs(res.LB - b.LB) < 1e-9


# ------------------------------------------------------------------------- W6d polish
def test_polish_descends_to_a_local_optimum():
    """`_polish` runs the descent to convergence: a deliberately kicked (worse, feasible)
    allocation comes back at least as good as before the kick, feasible, and 1-swap
    locally optimal -- the exact property the 2026-08-30 diagnostic found missing."""
    pi = _t0()[-1]
    ua, ub = base.utilities(pi.G, pi.nodes, THETA, LAM)
    ctx = ST._Ctx(pi.G, pi.nodes, ua, ub, 0.0)
    st = dict(deadline=None, n_polish=0, polish_spent=0.0)
    start, _src = ST._fallback_warm_start(ctx)
    start = ST._local_search(ctx, start, ls_moves=ST._POLISH_MOVES)
    obj0 = ctx.objective(start)
    kicked = None                                # one feasibility-preserving worsening flip
    for z in sorted(ctx.nodes, key=base._sort_key):
        cand = (start - {z}) if z in start else (start | {z})
        if cand and (ctx.node_set - cand) and ctx.is_feasible(cand) \
                and ctx.objective(cand) < obj0 - 1e-12:
            kicked = cand
            break
    assert kicked is not None
    out = ST._polish(ctx, st, kicked)
    assert st["n_polish"] == 1 and ctx.is_feasible(out)
    assert ctx.objective(out) >= ctx.objective(kicked) - 1e-15
    for z in ctx.nodes:                          # 1-swap local optimality
        cand = (out - {z}) if z in out else (out | {z})
        if cand and (ctx.node_set - cand) and ctx.is_feasible(cand):
            assert ctx.objective(cand) <= ctx.objective(out) + 1e-12


def test_ils_start_is_gated_by_size_and_never_worse():
    """T0 solves keep the plain `warm_f1` start (no 5 s ILS below `_ILS_MIN_N`); called
    directly, `_ils_start` returns a feasible allocation at least as good as the descended
    start, deterministically for a fixed seed."""
    pi = _t0()[-1]
    res, _ = _run(pi.G, pi.nodes, mip_start="f1")
    assert res.extra["mip_start"] == "warm_f1"           # not "+ils": n < _ILS_MIN_N
    ua, ub = base.utilities(pi.G, pi.nodes, THETA, LAM)
    ctx = ST._Ctx(pi.G, pi.nodes, ua, ub, 0.0)
    start, _src = ST._fallback_warm_start(ctx)
    ref = ctx.objective(ST._local_search(ctx, set(start), ls_moves=ST._POLISH_MOVES))
    b1, o1 = ST._ils_start(ctx, start, 17, 2.0)
    b2, o2 = ST._ils_start(ctx, start, 17, 2.0)
    assert ctx.is_feasible(b1) and o1 >= ref - 1e-15
    assert b1 == b2 and abs(o1 - o2) < 1e-15
