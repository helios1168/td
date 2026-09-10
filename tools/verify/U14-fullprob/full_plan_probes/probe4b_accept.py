"""Item 4, second half: can any move ever be accepted?

A move is accepted only when its trial re-solve is feasible under every pin the stage left and
scores strictly above the incumbent.  This toy makes the forbid a no-op (the moved state has no
WH or FI mass at all) and leaves the N split degenerate (many contact-optimal splits), which is
the only shape in which an acceptance can occur.  Whether the trial's `z` differs from the
incumbent's is printed, since an acceptance at identical `z` is a solver tie, not the move.
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

ADJ = {"AA": ("BB",), "BB": ("AA",)}
SPEC = {"AA": dict(national=0.5, wh=0.0, fi=0.0),
        "BB": dict(national=1.5, wh=0.0, fi=0.0)}


def main():
    for route in ("joint", "sequential"):
        with tempfile.TemporaryDirectory() as tmp:
            inst = os.path.join(tmp, "inst.json.gz")
            toy.write_v2_toy(inst, SPEC)
            out = os.path.join(tmp, "out")
            orig, td_geo = toy.patch_rook(ADJ)
            try:
                rc = cli.main([inst, "--route", route, "--driver", "reps", "--engine",
                               "scipy", "--strategy", "direct", "--k", "2",
                               "--time-limit", "60", "--out", out])
            finally:
                toy.unpatch(orig, td_geo)
            with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
                plan = json.load(fh)
            print(f"--- route {route}: rc={rc}")
            print("   used:", [(r["id"], r["bundle"], round(r["mass"], 4), r["y"])
                               for r in plan["slots"] if r["used"]])
            for m in plan["moves"]:
                print("   ", m)


if __name__ == "__main__":
    main()
