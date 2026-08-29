"""
test_cbc_tree_slow.py -- cbc_tree.py against the six named contiguity failures
(CLAUDE.md trap 11 / PLAN.md C.0 #1), at a 60 s cap (PLAN.md C.5, W7).

SLOW: run with `TD_SLOW=1`.  This is the number the calling session's stage-gate review
wants: which named failures does the CBC-tree method certify, at what gap, in what time --
not a pass/fail gate (`research/contiguity/TEST_PLAN.md` calls Option B's certification of
the 125-zip pair "aspirational for CBC"; report what it does).  The one thing this test does
assert is the contract: every row must be `valid` (never a false certificate, never a
disconnected "optimal" -- see cbc_tree.py's module docstring for the CBC quirks that make
this an actual, not theoretical, concern), and if `status == "optimal"` then `excess_pieces
== 0` and `product <= free product` (checked via brute/exhaustive infeasible at this size, so
via the harness's own `evaluate` machinery instead).
"""
from __future__ import annotations

import os
import sys
import time

SLOW = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import instances                                    # noqa: E402
from contig_methods import base, cbc_tree           # noqa: E402

THETA, LAM = instances.THETA, instances.LAM
CAP = 60.0


def test_named_failures_report():
    specs = instances.named_failures()
    assert len(specs) == 6
    print()
    print(f"{'instance':<28} {'n':>4} {'status':<12} {'UB':>10} {'LB':>10} "
          f"{'gap':>10} {'nodes':>6} {'t':>7}")
    for sp in specs:
        pi = instances.build_pair(sp, theta=THETA, lam=LAM)
        t0 = time.perf_counter()
        res = base.run_method(cbc_tree.solve, pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0,
                              time_limit=CAP, seed=0)
        row = base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM, rho=0.0)
        t = time.perf_counter() - t0
        assert row["valid"], (sp.name, row["violations"])
        if res.extra.get("cbc_claimed_status") == "optimal":
            assert row["excess_pieces"] == 0, (sp.name, row)
            assert row["valid"] and res.status == "heuristic", (sp.name, row)
        ub = f"{res.UB:.6f}" if res.UB is not None else "None"
        lb = f"{row['LB']:.6f}" if row.get("LB") is not None else "None"
        gap = row.get("gap_nats")
        gap_s = f"{gap:.2e}" if gap is not None else "None"
        print(f"{sp.name:<28} {pi.n:>4} {res.status:<12} {ub:>10} {lb:>10} "
              f"{gap_s:>10} {res.nodes:>6} {t:>6.1f}s")
