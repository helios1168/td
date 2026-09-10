"""Item 1: route S stage order, the `prior` fold, a zero-slot stage, and the clip at 1.

Toy: A - B rook-adjacent, C isolated (no rook neighbour).  A and B carry national mass that
two slots can band; C's national mass is below L, so stage N covers it only in part and the
fold has something to say.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                                    # noqa: E402
import toy                                                            # noqa: E402

import full_plan as cli                                               # noqa: E402
from td.solvers import level0                                         # noqa: E402

SPEC = {
    "AA": dict(national=1.0, wh=0.6, fi=0.4),
    "BB": dict(national=1.0, wh=0.6, fi=0.4),
    "CC": dict(national=0.3, wh=0.1, fi=0.1),      # isolated, below L
}
ADJ = {"AA": ("BB",), "BB": ("AA",), "CC": ()}


def run(tmp, extra=None):
    inst = os.path.join(tmp, "inst.json.gz")
    toy.write_v2_toy(inst, SPEC)
    out = os.path.join(tmp, "out")
    priors, results = [], []

    real_build = level0.build_level0
    real_solve = level0.solve_passes

    def build(cells, bundles, **kw):
        priors.append(np.array(kw.get("prior"), float) if kw.get("prior") is not None else None)
        return real_build(cells, bundles, **kw)

    def solve(problem, passes, **kw):
        res = real_solve(problem, passes, **kw)
        results.append(res)
        return res

    level0.build_level0, level0.solve_passes = build, solve
    orig, td_geo = toy.patch_rook(ADJ)
    try:
        rc = cli.main([inst, "--route", "sequential", "--driver", "geo", "--engine", "scipy",
                       "--strategy", "direct", "--k", "2", "--time-limit", "60",
                       "--out", out] + list(extra or []))
    finally:
        toy.unpatch(orig, td_geo)
        level0.build_level0, level0.solve_passes = real_build, real_solve
    return rc, out, priors, results


def main():
    with tempfile.TemporaryDirectory() as tmp:
        rc, out, priors, results = run(tmp)
        print("rc:", rc)
        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)
        print("stages in pass log:", [p["stage"] for p in plan["passes"]])
        print("pass names:", [p["name"] for p in plan["passes"]])
        print("slot bundles:", [(r["id"], r["bundle"], r["used"], round(r["mass"], 4), r["y"])
                                for r in plan["slots"] if r["used"]])

        cov = [np.asarray(r["covered"], float) for r in results]
        print("n build calls:", len(priors), "n solves:", len(results))
        for i, p in enumerate(priors):
            print(f"prior[{i}] =\n{np.round(p, 6)}")
        for i, c in enumerate(cov):
            print(f"covered[{i}] =\n{np.round(c, 6)}")

        # the claim: prior for stage n is exactly the sum of the earlier stages' `covered`
        ok = True
        acc = np.zeros_like(cov[0])
        for i in range(len(priors)):
            want = np.clip(acc.copy(), 0.0, 1.0)
            got = priors[i]
            same = np.allclose(got, want, atol=0.0, rtol=0.0)
            print(f"stage {i}: prior == sum of earlier covered exactly? {same} "
                  f"(max abs diff {np.abs(got - want).max():.3e})")
            ok &= bool(same)
            if i < len(cov):
                acc = acc + cov[i]
        print("PRIOR FOLD EXACT:", ok)
        print("prior <= 1 everywhere:", bool((acc <= 1.0 + 0.0).all()),
              "max acc", float(acc.max()))

        # residual reported per state
        for st, row in plan["per_state"].items():
            print(st, "residual", row["residual_by_channel"])

    # zero-slot stage: FI mass zero and only the pure bundles enabled
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        toy.write_v2_toy(inst, {"AA": dict(national=1.0, wh=1.0, fi=0.0),
                                "BB": dict(national=1.0, wh=1.0, fi=0.0)})
        out = os.path.join(tmp, "out0")
        orig, td_geo = toy.patch_rook({"AA": ("BB",), "BB": ("AA",)})
        try:
            rc = cli.main([inst, "--route", "sequential", "--engine", "scipy",
                           "--strategy", "direct", "--k", "2", "--bundles", "N,WH,FI",
                           "--time-limit", "60", "--out", out])
        finally:
            toy.unpatch(orig, td_geo)
        print("zero-slot stage rc:", rc)
        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)
        print("passes:", [(p["stage"], p["name"], p["value"], p["certified"])
                          for p in plan["passes"]])


if __name__ == "__main__":
    main()
