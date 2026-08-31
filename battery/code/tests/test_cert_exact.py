"""
test_cert_exact.py -- contig_methods/cert_exact.py: the exact post-hoc certificate (W6c).

What is being guarded, in order of how badly a regression would hurt:

1. **The relaxation is valid.**  `sqrt(ga*gb) <= (p*ga + q*gb)/2` has to hold for every
   (p, q) `tangent_pq` returns, at every (ga, gb) -- not just near the tangency point and
   not just for well-behaved magnitudes.  A p, q pair that fails this makes every
   certificate downstream worthless while still looking like a good bound, so the test is
   an exact-arithmetic check over a dense sample plus adversarial points (zero, tiny, huge,
   wildly asymmetric).
2. **The exact arithmetic is exact.**  `dyadic_bits` / `to_int_scaled` must reproduce the
   float data with no rounding at all.
3. **The certificate agrees with brute force.**  On all 13 T0 pairs the certifier must
   return `certified` with `UB_exact` equal, as a rational, to the brute-force optimum's
   product -- and `check_opt` audits every separator cut against that optimum on the way,
   because an invalid cut is the one failure mode that is silent.
4. **It refutes what it should refute.**  A deliberately suboptimal (but contiguous)
   incumbent must come back `improved`, with a strictly larger exact product.
5. **It is deterministic**, and it rejects a non-contiguous incumbent instead of
   certifying it.
"""
from __future__ import annotations

import math
import os
import random
import sys
from fractions import Fraction

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import instances as I                                        # noqa: E402
from contig_methods import base, brute, cert_exact as CE     # noqa: E402

THETA, LAM = 0.40, 0.30


def _path_instance(n=8):
    """A path with a monotone ratio -- the same shape test_base/test_brute use."""
    G = nx.path_graph(n)
    for i in range(n):
        G.nodes[i].update(A=1.0 + 0.9 * (n - 1 - i) / (n - 1),
                          B=1.0 + 0.9 * i / (n - 1),
                          M=4.0 + 0.1 * i, pos=(i / n, 0.5))
    return G


# ------------------------------------------------------------------ 1. relaxation validity
def test_tangent_pq_is_a_valid_over_estimator():
    """(p*ga + q*gb)/2 >= sqrt(ga*gb) for every (p, q) `tangent_pq` returns.

    Checked in exact rational arithmetic by squaring, so no floating-point comparison is
    load-bearing: ((p*ga + q*gb))**2 >= 4*ga*gb.
    """
    rng = random.Random(20260830)
    p_floats = [1e-6, 1e-3, 0.1, 0.5, 0.9999, 1.0, 1.0001, 2.0, 10.0, 1e3, 1e6]
    p_floats += [math.exp(rng.uniform(-8, 8)) for _ in range(60)]
    pts = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1e-12, 1e12), (1e12, 1e-12),
           (1.0, 1.0), (1e-300, 1.0), (25.9, 24.5)]
    pts += [(math.exp(rng.uniform(-10, 10)), math.exp(rng.uniform(-10, 10)))
            for _ in range(200)]
    for pf in p_floats:
        Pn, Qn = CE.tangent_pq(pf)
        assert Pn > 0 and Qn > 0
        assert Pn * Qn >= 1 << (2 * CE.KP), f"p*q < 1 for p={pf}"
        p = Fraction(Pn, 1 << CE.KP)
        q = Fraction(Qn, 1 << CE.KP)
        for ga_f, gb_f in pts:
            ga, gb = Fraction(ga_f), Fraction(gb_f)
            lhs = p * ga + q * gb
            assert lhs * lhs >= 4 * ga * gb, f"invalid at p={pf} g=({ga_f},{gb_f})"


def test_tangent_pq_is_tight_at_its_own_point():
    """Rounding p, q outward must cost at most a few ulps, or the bound is useless."""
    for ga, gb in [(25.9, 24.5), (1.0, 100.0), (3.25, 3.25)]:
        Pn, Qn = CE.tangent_pq(math.sqrt(gb / ga))
        p = Fraction(Pn, 1 << CE.KP)
        q = Fraction(Qn, 1 << CE.KP)
        over = float((p * Fraction(ga) + q * Fraction(gb)) / 2) / math.sqrt(ga * gb)
        assert 1.0 <= over <= 1.0 + 1e-8, over


# ------------------------------------------------------------------ 2. exact data helpers
def test_dyadic_scaling_is_exact():
    vals = [0.1, 0.25, 1.0 / 3.0, 1e-8, 123456.789, 2.0 ** -40, 7.0]
    bits = max(CE.dyadic_bits(v) for v in vals)
    ints = CE.to_int_scaled(vals, bits)
    for v, i in zip(vals, ints):
        assert Fraction(i, 1 << bits) == Fraction(v)
    try:
        CE.to_int_scaled([1.0 / 3.0], 4)
    except ValueError:
        pass
    else:                                                    # pragma: no cover
        raise AssertionError("to_int_scaled accepted an inexact scaling")


# ------------------------------------------------------- 3. agreement with brute force
def _exact_product(ua, ub, x):
    ga = sum((Fraction(float(v)) for v, xi in zip(ua, x) if xi), Fraction(0))
    gb = sum((Fraction(float(v)) for v, xi in zip(ub, x) if not xi), Fraction(0))
    return ga * gb


def test_t0_certificates_equal_brute_force_rationally():
    """All 13 T0 pairs: certified, and UB_exact == brute's optimum *as a rational*."""
    specs = I.specs_for_tiers(["T0"])
    assert len(specs) == 13, f"T0 has {len(specs)} pairs, expected 13"
    for sp in specs:
        pi = I.build_pair(sp)
        res = base.run_method(brute.solve, pi.G, pi.nodes, time_limit=120)
        assert res.status == "optimal", f"{sp.name}: brute returned {res.status}"
        ua, ub = base.utilities(pi.G, pi.nodes, THETA, LAM)
        P_brute = _exact_product(ua, ub, base.mask(pi.nodes, res.to_a))
        c = CE.certify(pi.G, pi.nodes, res.to_a, time_limit=300, check_opt=res.to_a)
        assert c.status == "certified", f"{sp.name}: {c.status} ({c.message})"
        assert c.incumbent_exact == P_brute, f"{sp.name}: incumbent product mismatch"
        assert c.UB_exact == P_brute, (
            f"{sp.name}: UB_exact {c.UB_exact} != brute {P_brute}")
        assert c.gap_exact == 0.0, f"{sp.name}: gap_exact {c.gap_exact!r} is not exactly 0"


def test_hand_path_instance_certifies():
    G = _path_instance(8)
    nodes = sorted(G)
    res = base.run_method(brute.solve, G, nodes, time_limit=60)
    c = CE.certify(G, nodes, res.to_a, time_limit=60, check_opt=res.to_a)
    assert c.status == "certified" and c.gap_exact == 0.0


# ------------------------------------------------------------------ 4. refutation
def test_suboptimal_incumbent_is_refuted():
    """A contiguous but suboptimal allocation must come back `improved`, not `certified`."""
    G = _path_instance(8)
    nodes = sorted(G)
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    res = base.run_method(brute.solve, G, nodes, time_limit=60)
    opt = set(res.to_a)
    P_opt = _exact_product(ua, ub, base.mask(nodes, opt))
    worse = None
    for k in range(1, len(nodes)):                           # every contiguous prefix
        cand = set(nodes[:k])
        if not base.is_feasible(G, nodes, cand):
            continue
        P = _exact_product(ua, ub, base.mask(nodes, cand))
        if P < P_opt:
            worse = cand
            break
    assert worse is not None, "no suboptimal contiguous prefix on the hand instance"
    c = CE.certify(G, nodes, worse, time_limit=60)
    assert c.status == "improved", c.status
    assert c.better_to_a is not None
    P_better = _exact_product(ua, ub, base.mask(nodes, set(c.better_to_a)))
    assert P_better > c.incumbent_exact
    assert base.is_feasible(G, nodes, set(c.better_to_a))


def test_non_contiguous_incumbent_is_rejected():
    G = _path_instance(8)
    nodes = sorted(G)
    bad = {nodes[0], nodes[3]}                               # two pieces on a path
    assert not base.is_feasible(G, nodes, bad)
    c = CE.certify(G, nodes, bad, time_limit=30)
    assert c.status == "error" and "contiguous" in c.message


# ------------------------------------------------------------------ 5. determinism, slack
def test_determinism():
    sp = [s for s in I.specs_for_tiers(["T0"]) if s.n_expected and s.n_expected >= 16][0]
    pi = I.build_pair(sp)
    res = base.run_method(brute.solve, pi.G, pi.nodes, time_limit=120)
    a = CE.certify(pi.G, pi.nodes, res.to_a, time_limit=300)
    b = CE.certify(pi.G, pi.nodes, res.to_a, time_limit=300)
    assert (a.status, a.UB_exact, a.incumbent_exact) == (b.status, b.UB_exact,
                                                         b.incumbent_exact)
    assert (a.n_nodes, a.n_cuts, a.n_tangents) == (b.n_nodes, b.n_cuts, b.n_tangents)


def test_slack_is_a_rigorous_bound_not_a_tolerance():
    """`slack_rel` must show up in `gap_exact` as exactly log1p(slack), never as 0."""
    G = _path_instance(8)
    nodes = sorted(G)
    res = base.run_method(brute.solve, G, nodes, time_limit=60)
    c = CE.certify(G, nodes, res.to_a, time_limit=60, slack_rel=1e-9)
    assert c.status == "certified"
    assert abs(c.gap_exact - math.log1p(1e-9)) < 1e-15, c.gap_exact
    assert c.UB_exact == c.incumbent_exact * (1 + Fraction(1e-9))
    c0 = CE.certify(G, nodes, res.to_a, time_limit=60, slack_rel=0.0)
    assert c0.gap_exact == 0.0 and c0.UB_exact == c0.incumbent_exact


def test_module_is_not_registered_as_a_method():
    from contig_methods import REGISTRY                      # noqa: PLC0415
    assert "cert_exact" not in REGISTRY
    assert not hasattr(CE, "solve")
