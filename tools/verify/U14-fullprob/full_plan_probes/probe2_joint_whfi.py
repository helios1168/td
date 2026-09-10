"""Item 2: route J's coverage passes never name WHFI, and what the catch-all does about it.

Toy AA-BB.  BB carries only national.  AA's WH and FI each sit below L but sum into the band,
so the only district that can serve AA's WH and FI is a merged one.

Variant "with_N": AA also carries a little national, so once cover_N takes it AA's N residual
is 0 and the four-channel catch-all bundle is blocked at AA by the cover rows.
Variant "no_N":  AA carries no national at all, so its N cover_ub stays 1 and the catch-all
can take it.

Also: the zero-residual catch-all (everything covered) as a separate run.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toy                                                            # noqa: E402
import full_plan as cli                                               # noqa: E402

ADJ = {"AA": ("BB",), "BB": ("AA",)}


def run(tmp, spec, args, tag):
    inst = os.path.join(tmp, f"inst_{tag}.json.gz")
    toy.write_v2_toy(inst, spec)
    out = os.path.join(tmp, f"out_{tag}")
    orig, td_geo = toy.patch_rook(ADJ)
    try:
        rc = cli.main([inst, "--engine", "scipy", "--strategy", "direct", "--k", "2",
                       "--time-limit", "60", "--out", out] + args)
    finally:
        toy.unpatch(orig, td_geo)
    with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    print(f"--- {tag}: rc={rc}")
    print("  bundles field:", plan["bundles"])
    print("  used slots:", [(r["id"], r["bundle"], round(r["mass"], 4), r["y"])
                            for r in plan["slots"] if r["used"]])
    print("  passes:", [(p["stage"], p["name"], round(float(p["value"]), 6), p["certified"])
                        for p in plan["passes"]])
    for st, row in plan["per_state"].items():
        print("  residual", st, row["residual_by_channel"])
    return plan


def main():
    with_n = {"AA": dict(national=0.1, wh=0.5, fi=0.5),
              "BB": dict(national=2.0, wh=0.0, fi=0.0)}
    no_n = {"AA": dict(national=0.0, wh=0.5, fi=0.5),
            "BB": dict(national=2.0, wh=0.0, fi=0.0)}

    with tempfile.TemporaryDirectory() as tmp:
        run(tmp, with_n, ["--route", "joint", "--driver", "geo", "--catch-all"], "joint_withN")
        run(tmp, no_n, ["--route", "joint", "--driver", "geo", "--catch-all"], "joint_noN")
        run(tmp, with_n, ["--route", "sequential", "--driver", "geo", "--catch-all"],
            "seq_withN")

    # everything covered -> the catch-all bundle has zero slots
    with tempfile.TemporaryDirectory() as tmp:
        full = {"AA": dict(national=1.0, wh=0.6, fi=0.4),
                "BB": dict(national=1.0, wh=0.6, fi=0.4)}
        try:
            run(tmp, full, ["--route", "sequential", "--driver", "geo", "--catch-all"],
                "catchall_zero")
            print("catch-all with no residual: no crash")
        except Exception:
            print("catch-all with no residual: RAISED")
            traceback.print_exc(limit=4)
            out = os.path.join(tmp, "out_catchall_zero")
            print("  timings.json present:", os.path.exists(os.path.join(out, "timings.json")))
            print("  plan.json present:", os.path.exists(os.path.join(out, "plan.json")))
            print("  failure.json present:", os.path.exists(os.path.join(out, "failure.json")))


if __name__ == "__main__":
    main()
