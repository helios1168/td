"""
test_loop_v2.py -- contig_methods/loop_v2.py (W9a): the engineered multi-tree
outer-approximation + root-free G2 connectivity-cut loop, and the `base.lexi_perimeter`
post-pass it implements.

Fast tier only (< 120 s): T0 exactness for all three variants with the check_cuts debug
assertion against `brute`, hand instances (two-component / glue), determinism, the rho=2e-3
path, the lexi post-pass on T0, and a small (8-pair) slice of B.17.  The full 63-pair T1
sweep, the named-failure / C9 iteration-count table, and the full-harness `--lexi` smoke are
in `test_loop_v2_slow.py` (SLOW = True; `TD_SLOW=1`).
"""
from __future__ import annotations

import math
import os
import sys
import warnings

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import instances                                    # noqa: E402
from contig_methods import REGISTRY, base, brute, loop_v2   # noqa: E402

THETA, LAM = 0.40, 0.30


# ------------------------------------------------------------------------ hand instances
def path_instance(n=8, offset=0):
    """P_n with monotone utility ratio along the path (prefixes are contiguous)."""
    G = nx.path_graph(n)
    G = nx.relabel_nodes(G, {i: i + offset for i in range(n)})
    for i in range(n):
        A = 1.0 + 0.9 * (n - 1 - i) / (n - 1)
        B = 1.0 + 0.9 * i / (n - 1)
        G.nodes[i + offset].update(A=A, B=B, M=4.0 + 0.1 * i, pos=(i / n, 0.5))
    return G


def two_component_instance():
    """Two disjoint paths P4 + P3 -- the pair graph itself is disconnected (C.0 #1); this
    is exactly the shape the legacy solver's fixed-root cuts get WRONG (CLAUDE.md trap 13)."""
    G = path_instance(4)
    H = path_instance(3, offset=10)
    return nx.union(G, H)


def glue_instance():
    """P6 with two zero-value zips in the middle (regime (d))."""
    G = path_instance(6)
    for z in (2, 3):
        G.nodes[z].update(A=0.0, B=0.0, M=0.0)
    return G


# --------------------------------------------------------------------------------- T0
def _t0_pairs():
    """The 13 curated T0 pairs (`instances.build_T0()`), filtered + rescaled."""
    out = []
    for spec in instances.build_T0():
        pi = instances.build_pair(spec, theta=THETA, lam=LAM, rescale=True, with_bounds=False)
        out.append((pi.G, pi.nodes, spec.name))
    return out


_T0 = None
def t0_pairs():
    global _T0
    if _T0 is None:
        _T0 = _t0_pairs()
    return _T0


def _run(name, H, nodes, time_limit=20.0, rho=0.0, **kw):
    spec = REGISTRY[name]
    opts = dict(spec.kwargs); opts.update(kw)
    res = base.run_method(spec.solve, H, nodes, theta=THETA, lam=LAM, rho=rho,
                          time_limit=time_limit, **opts)
    row = base.evaluate(H, nodes, res, theta=THETA, lam=LAM, rho=rho)
    return res, row


def _cut_satisfied(cut, to_a, tol=1e-6):
    lhs = sum(coef * (1.0 if node in to_a else 0.0) for node, coef in cut["coeffs"].items())
    return (lhs >= cut["lo"] - tol) and (lhs <= cut["hi"] + tol)


# --------------------------------------------------------------------------- registry
def test_registry_variants():
    for name, kwargs in (("loop_v2", {}), ("loop_v2_noinout", dict(lambda_inout=1.0)),
                         ("loop_v2_nbr", dict(cut_family="nbr"))):
        assert name in REGISTRY, name
        assert REGISTRY[name].base_name == "loop_v2"
        assert REGISTRY[name].kwargs == kwargs, (name, REGISTRY[name].kwargs)
        assert REGISTRY[name].exact


# -------------------------------------------------------------------------------- T0
def _check_variant_on_t0(name, check_cuts=False):
    n_checked_cuts = 0
    for H, nodes, iname in t0_pairs():
        bres = brute.solve(H, nodes, theta=THETA, lam=LAM, rho=0.0,
                           respect_state=False, time_limit=30, seed=0)
        res, row = _run(name, H, nodes, time_limit=30.0,
                        **(dict(check_cuts=True) if check_cuts else {}))
        assert row["valid"], (name, iname, row["violations"])
        assert res.status == "optimal", (name, iname, res.status, res.message)
        assert row["excess_pieces"] == 0, (name, iname)
        assert row["LB"] is not None and abs(row["LB"] - bres.LB) < 1e-6, \
            (name, iname, row["LB"], bres.LB)
        assert row["valid_certificate"], (name, iname, row["violations"])
        if check_cuts:
            cuts = res.extra.get("cuts_debug", [])
            for c in cuts:
                assert _cut_satisfied(c, bres.to_a), (iname, c)
                n_checked_cuts += 1
    return n_checked_cuts


def test_loop_v2_matches_brute_on_t0_with_cut_validity():
    n_checked = _check_variant_on_t0("loop_v2", check_cuts=True)
    assert n_checked > 0, "expected at least one G2 cut across the T0 sweep"


def test_loop_v2_nbr_matches_brute_on_t0():
    _check_variant_on_t0("loop_v2_nbr", check_cuts=True)


def test_loop_v2_noinout_matches_brute_on_t0():
    _check_variant_on_t0("loop_v2_noinout")


# ------------------------------------------------------------------- hand instances
def test_hand_instances_two_component_and_glue():
    for G in (two_component_instance(), glue_instance()):
        nodes = sorted(G)
        bres = brute.solve(G, nodes, theta=THETA, lam=LAM, rho=0.0,
                           respect_state=False, time_limit=30, seed=0)
        for name in ("loop_v2", "loop_v2_nbr", "loop_v2_noinout"):
            res, row = _run(name, G, nodes, time_limit=20.0)
            assert row["valid"], (name, row["violations"])
            assert res.status == "optimal", (name, res.status, res.message)
            assert abs(row["LB"] - bres.LB) < 1e-6, (name, row["LB"], bres.LB)


def test_two_component_instance_needs_no_root():
    """The disconnected hand fixture is exactly CLAUDE.md trap 13's shape: the legacy
    solver's fixed-root cuts are invalid here.  loop_v2 has no roots at all and must still
    certify -- this is the smallest reproduction of the C1-seed2 A0/B0 named failure."""
    G = two_component_instance()
    nodes = sorted(G)
    assert nx.number_connected_components(G.subgraph(nodes)) == 2
    res, row = _run("loop_v2", G, nodes, time_limit=20.0, check_cuts=True)
    assert res.status == "optimal" and row["valid"]
    assert res.ub_scope == "global"


# --------------------------------------------------------------------- determinism
def test_determinism():
    H, nodes, _ = t0_pairs()[-1]
    res1, _ = _run("loop_v2", H, nodes, time_limit=20.0)
    res2, _ = _run("loop_v2", H, nodes, time_limit=20.0)
    assert res1.to_a == res2.to_a
    assert res1.status == res2.status
    assert res1.LB is not None and res2.LB is not None
    assert abs(res1.LB - res2.LB) < 1e-12


# ------------------------------------------------------------------------- rho > 0
def test_rho_2e3_consistency():
    for H, nodes, name in t0_pairs()[:6]:
        bres = brute.solve(H, nodes, theta=THETA, lam=LAM, rho=2e-3,
                           respect_state=False, time_limit=30, seed=0)
        res, row = _run("loop_v2", H, nodes, time_limit=20.0, rho=2e-3)
        assert row["valid"], (name, row["violations"])
        assert res.status == "optimal", (name, res.status)
        assert row["perimeter"] is not None and isinstance(row["perimeter"], int)
        assert abs(row["LB"] - bres.LB) < 1e-6, (name, row["LB"], bres.LB)


# -------------------------------------------------------------------- lexi post-pass
def test_lexi_perimeter_on_t0():
    for H, nodes, name in t0_pairs():
        res, row = _run("loop_v2", H, nodes, time_limit=30.0)
        assert res.status == "optimal"
        per_before = base.perimeter(H, nodes, res.to_a)
        out = base.lexi_perimeter(H, nodes, res.to_a, row["LB"], loop_v2.solve,
                                  theta=THETA, lam=LAM, time_limit=20.0, seed=0)
        assert out["perimeter"] <= per_before, (name, out["perimeter"], per_before)
        assert out["obj"] is None or out["obj"] >= row["LB"] - 1e-9, (name, out)
        assert base.is_feasible(H, nodes, out["to_a"]), name
        ua, ub = base.utilities(H, nodes, THETA, LAM)
        ga, gb = base.gains(ua, ub, base.mask(nodes, out["to_a"]))
        assert ga > 0 and gb > 0
        assert math.log(ga) + math.log(gb) >= row["LB"] - 1e-9, name


def test_lexi_perimeter_engine_mismatch_warns_and_still_works():
    H, nodes, _ = t0_pairs()[3]
    res, row = _run("loop_v2", H, nodes, time_limit=20.0)

    def _not_loop_v2(*a, **k):
        raise AssertionError("should never be called")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = base.lexi_perimeter(H, nodes, res.to_a, row["LB"], _not_loop_v2,
                                  theta=THETA, lam=LAM, time_limit=15.0, seed=0)
    assert any("not wired" in str(w.message) for w in caught)
    assert out["status"] in ("optimal", "capped")
    per_before = base.perimeter(H, nodes, res.to_a)
    assert out["perimeter"] <= per_before


def test_lexi_perimeter_falls_back_on_engine_error():
    """An exception inside the engine (`loop_v2.solve_lexi`, monkey-patched here to raise --
    `method` itself, per the docstring, is only used to decide which engine to reuse and is
    never called directly) must fall back to the untouched input allocation, status
    "fallback", never crash the caller."""
    H, nodes, _ = t0_pairs()[0]
    res, row = _run("loop_v2", H, nodes, time_limit=20.0)
    per_in = base.perimeter(H, nodes, res.to_a)

    def _boom(*a, **k):
        raise RuntimeError("engine exploded")

    original = loop_v2.solve_lexi
    loop_v2.solve_lexi = _boom
    try:
        out = base.lexi_perimeter(H, nodes, res.to_a, row["LB"], loop_v2.solve,
                                  theta=THETA, lam=LAM, time_limit=5.0, seed=0)
    finally:
        loop_v2.solve_lexi = original
    assert out["status"] == "fallback"
    assert out["to_a"] == set(res.to_a)
    assert out["perimeter"] == per_in


def test_lexi_perimeter_falls_back_when_value_floor_is_unreachable():
    """An `opt_value` above the true attainable maximum can never be met; the post-pass must
    fall back rather than report a candidate that violates the floor."""
    H, nodes, _ = t0_pairs()[0]
    res, row = _run("loop_v2", H, nodes, time_limit=20.0)
    per_in = base.perimeter(H, nodes, res.to_a)
    impossible = row["LB"] + 50.0     # far above the free (uncontiguous) maximum too
    out = base.lexi_perimeter(H, nodes, res.to_a, impossible, loop_v2.solve,
                              theta=THETA, lam=LAM, time_limit=5.0, seed=0)
    assert out["status"] == "fallback"
    assert out["to_a"] == set(res.to_a)
    assert out["perimeter"] == per_in


# -------------------------------------------------------------------------- B.17 (fast slice)
def _b17_subset(n=8):
    specs = instances.specs_for_tiers(["T1"])
    return sorted(specs, key=lambda s: s.n_expected)[:n]


def test_b17_fast_subset():
    """Fast, small-n slice of B.17: on every T1 pair where `current` certifies at rho=2e-3
    (short cap), `loop_v2` at rho=0 also certifies (short cap).  The full 63-pair sweep at
    the caps prescribed by PLAN.md (rho=2e-3/20s for `current`, rho=0/60s for `loop_v2`) is
    `test_loop_v2_slow.py::test_b17_full_t1_sweep`."""
    # "current certifies" is judged in ITS OWN (rooted) sense -- status == "optimal" with a
    # tight gap -- exactly test_current.py's own convention; `valid_certificate` is *always*
    # False for `current` (ub_scope="rooted"), so it cannot be the criterion here.
    n_current_certified = 0
    n_loop_v2_certified = 0
    for spec in _b17_subset():
        pi = instances.build_pair(spec, theta=THETA, lam=LAM, rescale=True, with_bounds=False)
        H, nodes = pi.G, pi.nodes
        cres, crow = _run("current", H, nodes, time_limit=5.0, rho=2e-3)
        if not (cres.status == "optimal" and crow.get("gap_nats") is not None
               and crow["gap_nats"] <= base.CERT_TOL):
            continue
        n_current_certified += 1
        lres, lrow = _run("loop_v2", H, nodes, time_limit=10.0, rho=0.0)
        assert lrow["valid"], (spec.name, lrow["violations"])
        assert lrow["valid_certificate"], \
            (spec.name, "current certified at rho=2e-3 but loop_v2 did not at rho=0",
             lres.status, lrow.get("gap_nats"))
        n_loop_v2_certified += 1
    assert n_current_certified >= 3, "too few current-certified rows in the fast B.17 slice"
    assert n_loop_v2_certified == n_current_certified
