"""What survives when the catch-all stage has no residual left (K_WHFI_PLUS = 0)."""
from __future__ import annotations

import os
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toy                                                            # noqa: E402
import full_plan as cli                                               # noqa: E402

ADJ = {"AA": ("BB",), "BB": ("AA",)}
SPEC = {"AA": dict(national=0.1, wh=0.5, fi=0.5),
        "BB": dict(national=2.0, wh=0.0, fi=0.0)}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        toy.write_v2_toy(inst, SPEC)
        out = os.path.join(tmp, "out")
        orig, td_geo = toy.patch_rook(ADJ)
        try:
            cli.main([inst, "--route", "sequential", "--driver", "geo", "--catch-all",
                      "--engine", "scipy", "--strategy", "direct", "--k", "2",
                      "--time-limit", "60", "--out", out])
            print("no crash")
        except Exception as exc:
            print("RAISED:", type(exc).__name__, exc)
            traceback.print_exc(limit=2)
        finally:
            toy.unpatch(orig, td_geo)
        for name in ("params.json", "plan.json", "staffing.json", "timings.json",
                     "failure.json"):
            print(f"  {name}: {os.path.exists(os.path.join(out, name))}")
        print("  projections dir:", os.path.exists(os.path.join(out, "projections")))


if __name__ == "__main__":
    main()
