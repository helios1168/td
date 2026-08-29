"""
test_scip_tree_slow.py -- the W6 regression floor: the six named contiguity failures at a
60 s cap, and the two largest C7b pairs (320 and 464 zips) as a gap-at-cap record.

`SLOW = True`, so `run_all.py` skips this unless `TD_SLOW=1`.  Budget: ~10 minutes (five of
the six named pairs certify in under 2 s; C7 A3/B3 and both C7b pairs run to the cap -- since
W6b they really do run to it, where before the retry ladder stopped them after 1-4 s).

The printed tables are the numbers the W6 review asks for; the assertions are deliberately
weak floors, not the measurements -- they exist so a regression in the separator, the primal
heuristics or the bound handling is caught, not so that a solver-version change fails the
suite.  The floor is **5 of 6 named failures certified**; the sixth, C7 A3/B3 (205 zips), is
the open case and only has to produce a valid, non-trivial bound.
"""
from __future__ import annotations

import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import instances as I                                  # noqa: E402
from contig_methods import base                        # noqa: E402
from contig_methods import scip_tree as ST             # noqa: E402

SLOW = True
THETA, LAM = 0.40, 0.30
CAP = 60.0

_HDR = (f"{'instance':30s} {'n':>4s} {'status':11s} {'UB':>12s} {'LB':>12s} {'gap_nats':>10s} "
        f"{'nodes':>8s} {'cuts':>7s} {'dup':>5s} {'tan':>5s} {'enfolp':>7s} {'enfops':>7s} "
        f"{'inj':>4s} {'t':>6s} {'t_ff':>6s} cert")


def _row(name, n, res, row):
    g = row["gap_nats"]
    e = res.extra
    return (f"{name:30s} {n:4d} {res.status:11s} "
            f"{(res.UB if res.UB is not None else float('nan')):12.6f} "
            f"{(res.LB if res.LB is not None else float('nan')):12.6f} "
            f"{(g if g is not None else float('nan')):10.2e} {res.nodes:8d} {res.n_cuts:7d} "
            f"{e.get('n_dup_cuts', 0):5d} {res.n_tangents:5d} {e.get('n_enfolp', 0):7d} "
            f"{e.get('n_enfops', 0):7d} {e.get('n_injected', 0):4d} {res.t_total:6.1f} "
            f"{(res.t_first_feasible if res.t_first_feasible is not None else float('nan')):6.2f} "
            f"{row['valid_certificate']}")


def _solve(pi, **kw):
    res = base.run_method(ST.solve, pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0,
                          time_limit=CAP, seed=0, **kw)
    row = base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM, rho=0.0)
    return res, row


def test_named_failures_at_60s():
    """>= 5 of the 6 named failures certified; every row valid and contiguous."""
    print(f"\n-- scip_tree (native), the six named failures, cap {CAP:g}s --\n{_HDR}")
    certified, open_cases = [], []
    t0 = time.perf_counter()
    for sp in I.named_failures():
        pi = I.build_pair(sp)
        res, row = _solve(pi)
        print(_row(sp.name, pi.n, res, row), flush=True)
        assert row["valid"], (sp.name, row["violations"])
        assert res.ub_scope == "global"
        assert res.UB is not None and math.isfinite(res.UB), sp.name
        assert row["LB"] is not None, f"{sp.name}: no feasible incumbent inside the cap"
        assert row["excess_pieces"] == 0, sp.name
        assert res.UB >= row["LB"] - base.CERT_TOL, (sp.name, res.UB, row["LB"])
        (certified if row["valid_certificate"] else open_cases).append(sp.name)
    print(f"certified {len(certified)}/6 in {time.perf_counter() - t0:.0f}s; "
          f"open: {open_cases}")
    assert len(certified) >= 5, f"regression: only {certified} certified, open {open_cases}"
    # C7 A3/B3 is the known-open one; if something *else* stopped certifying, say so loudly
    assert set(open_cases) <= {"C7_scale_n400__A3_B3"}, open_cases


def test_the_open_case_spends_its_whole_budget():
    """The W6b regression: an uncertified pair must use the cap, not 3 s of it.

    Before W6b the retry ladder stopped on the first numerical abort, so C7 A3/B3 returned a
    3e-3 gap after 3 s of a 60 s budget (and after 3 s of a 1200 s budget in S2).  It now runs
    several rungs to the cap and lands near 1e-3.
    """
    sp = [s for s in I.named_failures() if s.name == "C7_scale_n400__A3_B3"]
    assert len(sp) == 1
    pi = I.build_pair(sp[0])
    res, row = _solve(pi)
    print(f"\n-- C7 A3/B3 budget use: t={res.t_total:.1f}s of {CAP:g}s, "
          f"gap={row['gap_nats']:.2e}, rungs={res.extra['n_rungs']}")
    for a in res.extra["attempts"]:
        print("   ", a)
    assert res.extra["n_rungs"] >= 2, res.extra["attempts"]
    assert res.t_total > 0.8 * CAP, (res.t_total, CAP)
    assert row["gap_nats"] < 3e-3, row["gap_nats"]
    assert row["excess_pieces"] == 0


def test_c7b_320_and_464_gap_at_cap():
    """The two largest T2 pairs: a gap-at-60 s record, not a certification requirement."""
    specs = [s for s in I.build_T2()
             if s.case.startswith("C7b") and s.n_expected in (320, 464)]
    assert len(specs) == 2, [s.name for s in specs]
    print(f"\n-- scip_tree (native), C7b 320/464, cap {CAP:g}s --\n{_HDR}")
    for sp in sorted(specs, key=lambda s: s.n_expected):
        pi = I.build_pair(sp)
        res, row = _solve(pi)
        print(_row(sp.name, pi.n, res, row), flush=True)
        assert row["valid"], (sp.name, row["violations"])
        assert res.UB is not None and math.isfinite(res.UB), sp.name
        assert row["LB"] is not None, f"{sp.name}: no feasible incumbent inside the cap"
        assert row["excess_pieces"] == 0, sp.name
        assert res.t_first_feasible is not None and res.t_first_feasible < 5.0, \
            f"{sp.name}: the warm start should be feasible almost immediately"
        assert row["gap_nats"] < 0.1, (sp.name, row["gap_nats"])


def test_oa_variant_on_the_named_failures():
    """The cross-check formulation must agree with `native` wherever both certify."""
    print(f"\n-- scip_tree_oa, the six named failures, cap {CAP:g}s --\n{_HDR}")
    n_cert = 0
    for sp in I.named_failures():
        pi = I.build_pair(sp)
        res, row = _solve(pi, formulation="oa")
        print(_row(sp.name, pi.n, res, row), flush=True)
        assert row["valid"], (sp.name, row["violations"])
        assert row["excess_pieces"] == 0, sp.name
        n_cert += bool(row["valid_certificate"])
        if row["valid_certificate"]:
            nat, nrow = _solve(pi)
            if nrow["valid_certificate"]:
                assert abs(row["LB"] - nrow["LB"]) < 1e-8, \
                    (sp.name, "native and oa certified different optima",
                     nrow["LB"], row["LB"])
    print(f"certified[oa] {n_cert}/6")
    assert n_cert >= 5, n_cert
