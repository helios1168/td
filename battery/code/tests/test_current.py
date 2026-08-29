"""
test_current.py -- contig_methods/current.py: the legacy `districting.solve_contiguous_nash`
wrapped under the harness contract (PLAN.md C.1, C.5, U2).

Acceptance (PLAN.md C.5): the registry carries `current` + its three variants; every
row the wrapper produces validates under `base.evaluate`; `current.LB <= OPT` always,
with equality wherever the brute-force optimum already respects the legacy solver's
fixed roots (`opt_has_ratio_roots`); the named C1-seed2 / C9-seed2 failures reproduce
as `time_limit` / `iteration_limit` rows carrying a `UB` and the last iterate; the
C8-pair trap-12 numbers (`current` vs `current_tight`) reproduce through this wrapper.

Deviation from the brief, found while building this test (T0-pair sweep, 2026-08-29):
"current.LB <= OPT, equal iff opt_has_ratio_roots" does NOT hold, as an "optimal"
claim, when the pair graph has more than one connected component.  Concrete
counterexample kept as a regression case below (S1_aligned n=50 seed=2, pair (1,1),
8 zips splitting into components {8, 11} and {14, 15, 16, 39, 44, 46}): the raw
legacy loop reports status "optimal" (fully mip_rel_gap=0 converged, no violated cut)
with an own dual bound of 6.283133, yet an *earlier, discarded* iterate it itself
visited was truly feasible (per the harness's correct, per-component contiguity
definition) with objective 6.4359 -- ABOVE its own final "converged" bound.  Root
cause: the legacy separator-cut formulation (districting.py) fixes one root per side
*globally* and cuts any a-side component not containing root_a by forcing its
external neighbours onto side a too; on a component that can never reach root_a (a
different connected component of the pair graph entirely), that cut still fires,
incorrectly excludes truly-feasible points from its own relaxation, and its dual
bound stops being a *valid* upper bound at all -- not merely loose.  `current.py`
detects this (`LB > UB` after recomputation) and reports `status="heuristic"`,
`UB=None` rather than a self-contradicting certificate (see its module docstring).
This is a sharper form of the already-documented "mechanism 1" (CLAUDE.md trap 11 /
PLAN.md C.0 #1): mechanism 1 was known to make the loop fail to converge on
disconnected pairs (iteration_limit); this shows it can also *falsely claim*
convergence on a provably suboptimal point, with an unsound bound to match.  Not
fixed here -- districting.py is out of scope for U2 ("files you must not touch") --
so the equal-iff check below is scoped to single-component pairs, and the finding is
reported to the calling session.  The weaker, unconditional claim (current.LB <= OPT)
still holds in every case tested, including this one: current.py only ever accepts
harness-feasible incumbents (`base.is_feasible`), and OPT is the true max over
exactly that feasible set, so any feasible incumbent's objective is bounded by it
regardless of how the legacy solver got there.
"""
from __future__ import annotations

import math
import os
import sys

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import synth, territory as T                      # noqa: E402
from contig_methods import REGISTRY, base, brute   # noqa: E402

THETA, LAM = 0.40, 0.30


# ------------------------------------------------------------------ T0-like pairs
def _t0_pairs(ns=(40, 50, 60), seeds=range(1, 11), lo=8, hi=20, limit=25):
    """(H, nodes, n_components) triples: S1_aligned pairs, 8..20 zips, filtered +
    rescaled through the same pipeline the production harness will use."""
    out = []
    for n in ns:
        for seed in seeds:
            G = synth.scenario("S1_aligned", n=n, seed=seed)
            O = T.overlap_graph(G)
            for edge in O.edges():
                ra, rb = T.pair_endpoints(edge)
                zips = T.zips_for_pair(G, ra, rb)
                if lo <= len(zips) <= hi:
                    H0, _ = base.filter_pair(G, sorted(zips), respect_state=False)
                    ncomp = nx.number_connected_components(H0)
                    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
                    out.append((H, sorted(H), ncomp))
                    if len(out) >= limit:
                        return out
    return out


def _run(name, H, nodes, time_limit=20.0):
    spec = REGISTRY[name]
    res = base.run_method(spec.solve, H, nodes, theta=THETA, lam=LAM, rho=0.0,
                          time_limit=time_limit, **spec.kwargs)
    row = base.evaluate(H, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    return res, row


# ------------------------------------------------------------------------- registry
def test_registry_variants():
    for name, kwargs in (("current", {}), ("current_unbounded", dict(max_iter=10 ** 6)),
                         ("current_q", dict(g0_seeds="quantile")),
                         ("current_tight", dict(milp_options=dict(mip_rel_gap=0.0)))):
        assert name in REGISTRY, name
        assert REGISTRY[name].base_name == "current"
        assert REGISTRY[name].kwargs == kwargs, (name, REGISTRY[name].kwargs)
        assert REGISTRY[name].exact


# --------------------------------------------------------------------- T0 sweep
def test_current_rows_valid_on_t0_pairs():
    pairs = _t0_pairs(limit=15)
    assert len(pairs) >= 10, "not enough T0-like pairs generated"
    for H, nodes, _ in pairs:
        res, row = _run("current", H, nodes, time_limit=15.0)
        assert row["valid"], (nodes, row["violations"])
        assert res.ub_scope == "rooted"
        assert res.status in base.STATUSES
        assert set(res.extra) == {"root_a", "root_b"}


def test_current_LB_le_OPT_equal_iff_ratio_roots_single_component():
    """PLAN.md C.5 acceptance, scoped to single-component pairs -- see module
    docstring for why multi-component pairs are excluded (a genuine, reported
    limitation of the wrapped legacy solver, not of this wrapper)."""
    pairs = _t0_pairs(limit=20)
    n_checked_eq_branch = 0
    for H, nodes, ncomp in pairs:
        bres = brute.solve(H, nodes, theta=THETA, lam=LAM, rho=0.0,
                           respect_state=False, time_limit=30, seed=0)
        OPT = bres.LB
        ratio_roots = bres.extra["opt_has_ratio_roots"]
        cres, crow = _run("current_tight", H, nodes, time_limit=20.0)
        if crow["LB"] is not None:
            assert crow["LB"] <= OPT + 1e-6, (nodes, crow["LB"], OPT)
        if ncomp == 1 and cres.status == "optimal":
            eq = crow["LB"] is not None and abs(crow["LB"] - OPT) < 1e-6
            assert eq == ratio_roots, (nodes, crow["LB"], OPT, ratio_roots)
            n_checked_eq_branch += 1
    assert n_checked_eq_branch >= 5, "too few single-component, fully-converged rows"


def test_current_disconnected_pair_regression():
    """The counterexample from the module docstring, pinned as a regression case:
    districting's own dual bound is unsound here (an earlier discarded iterate beats
    its final "converged" claim), so current.py must report status="heuristic" with
    UB=None rather than a self-contradicting certificate -- and its LB stays a valid
    lower bound (<= OPT) regardless."""
    G = synth.scenario("S1_aligned", n=50, seed=2)
    zips = T.zips_for_pair(G, 1, 1)
    H0, _ = base.filter_pair(G, sorted(zips), respect_state=False)
    assert nx.number_connected_components(H0) == 2
    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
    nodes = sorted(H)
    bres = brute.solve(H, nodes, theta=THETA, lam=LAM, rho=0.0,
                       respect_state=False, time_limit=30, seed=0)
    assert bres.extra["opt_has_ratio_roots"]
    cres, crow = _run("current_tight", H, nodes, time_limit=20.0)
    assert crow["valid"], crow["violations"]
    assert cres.status == "heuristic" and cres.UB is None, \
        "expected the documented unsound-bound fallback on this disconnected pair; " \
        "if this now fails, districting.py's separator-cut handling of disconnected " \
        "pair graphs may have changed -- re-check current.py's module docstring"
    assert crow["LB"] is not None and crow["LB"] <= bres.LB + 1e-9
    assert crow["LB"] < bres.LB - 1e-3, "expected the documented sub-optimality here"


# -------------------------------------------------------------------- determinism
def test_current_deterministic():
    pairs = _t0_pairs(limit=1)
    H, nodes, _ = pairs[0]
    res1, _ = _run("current", H, nodes, time_limit=15.0)
    res2, _ = _run("current", H, nodes, time_limit=15.0)
    assert res1.to_a == res2.to_a
    assert res1.status == res2.status
    if res1.LB is not None and res2.LB is not None:
        assert abs(res1.LB - res2.LB) < 1e-12


# ---------------------------------------------------------------- named failures
def _named_failure_row(scenario, seed, ra, rb):
    G = synth.scenario(scenario, n=200, seed=seed)
    zips = T.zips_for_pair(G, ra, rb)
    H0, _ = base.filter_pair(G, sorted(zips), respect_state=False)
    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
    nodes = sorted(H)
    res, row = _run("current", H, nodes, time_limit=20.0)
    return res, row, nodes


def test_named_failures_reproduce():
    # C1-seed2 A0/B0 (CLAUDE.md: pre-existing 67+2-zip disconnection, iteration limit)
    res, row, nodes = _named_failure_row("S1_aligned", 2, 0, 0)
    assert len(nodes) == 69
    assert row["valid"], row["violations"]
    assert res.status in ("time_limit", "iteration_limit", "gap_limit")
    assert res.UB is not None
    assert res.to_a is not None            # the last iterate is always carried

    # C9-seed2 A2/B2 (CLAUDE.md: value concentration moves the point of failure --
    # a previously-trivial 31-zip single-component pair now hits the iteration limit)
    res, row, nodes = _named_failure_row("S7_heavytail", 2, 2, 2)
    assert len(nodes) == 31
    assert row["valid"], row["violations"]
    assert res.status in ("time_limit", "iteration_limit", "gap_limit")
    assert res.UB is not None
    assert res.to_a is not None


# --------------------------------------------------------------------- C8 pair
def test_c8_pair_current_vs_current_tight():
    """CLAUDE.md trap 12's numbers (log-product 6.47177 at 14 iters loose, 6.47234
    at 9 iters certified), reproduced through the harness wrapper: `current`'s
    mip_rel_gap=1e-4 default leaves a gap far above CERT_TOL; `current_tight`
    certifies to CERT_TOL and finds a (slightly) better incumbent along the way."""
    G = synth.scenario("S1_aligned", n=200, seed=1)
    zips = T.zips_for_pair(G, 3, 3)
    assert len(zips) == 62
    H0, _ = base.filter_pair(G, sorted(zips), respect_state=False)
    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
    nodes = sorted(H)

    res_loose, row_loose = _run("current", H, nodes, time_limit=60.0)
    res_tight, row_tight = _run("current_tight", H, nodes, time_limit=60.0)

    assert row_loose["valid"] and row_tight["valid"]
    assert res_loose.status == "gap_limit"
    assert row_loose["gap_nats"] is not None and 1e-5 < row_loose["gap_nats"] < 1e-2
    assert res_tight.status == "optimal"
    assert row_tight["gap_nats"] is not None and row_tight["gap_nats"] <= base.CERT_TOL
    # current_tight's certified log-product is >= current's loose incumbent's
    assert row_tight["LB"] >= row_loose["LB"] - 1e-9
