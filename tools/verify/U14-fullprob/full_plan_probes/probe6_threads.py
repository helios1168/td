"""Item 6: trap 18 on the route-R path.

`solve_passes(strategy="portfolio")` forces `threads=2` for every pass of a stage; `_rep_moves`
then calls `solve_passes(..., strategy="direct", threads=args.threads)`, and `args.threads` is
documented to be left unset under `--strategy portfolio`.  So one process asks HiGHS for 2
threads and then for whatever the default is.  This runs that exact sequence on a small
Level0Problem and reports the second solve's status.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                                    # noqa: E402
import toy                                                            # noqa: E402
import full_plan as cli                                               # noqa: E402
from td import channels, instance as descaled                         # noqa: E402
from td.solvers import level0, milp_engines as me                     # noqa: E402

STATES = ["AA", "BB", "CC", "DD"]
SPEC = {s: dict(national=0.5, wh=0.5, fi=0.5) for s in STATES}


def build():
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        toy.write_v2_toy(inst, SPEC)
        d = channels.fine_split(descaled.load_descaled(inst))
    cells = channels.aggregate(d, STATES)
    M = np.asarray(cells.M, float)
    tau = float(M[:, :2].sum()) / 2.0
    return level0.build_level0(cells, {"N": channels.BUNDLES["N"]},
                               edges=[(0, 1), (1, 2), (2, 3)],
                               L=0.8 * tau, U=1.2 * tau, eta=0.01, order_mass=False)


def main():
    print("solve_passes threads guard:")
    p = build()
    for th in (None, 2, 4):
        try:
            level0.solve_passes(p, [], engine="highs", strategy="portfolio", threads=th)
            print(f"  portfolio threads={th}: accepted")
        except ValueError as exc:
            print(f"  portfolio threads={th}: refused ({exc})")

    try:
        import highspy                                                # noqa: F401
    except Exception as exc:
        print("highspy unavailable, skipping the live thread-pool sequence:", exc)
        return
    q = level0.contacts_pass(p)
    import dataclasses
    prob = dataclasses.replace(p, c=q.c)
    for th in (2, None, 2, 4):
        res = me.solve_problem(prob, "highs", time_limit=30, threads=th)
        print(f"  highs solve threads={th}: status={res['status']!r} "
              f"objective={res['objective']}")


if __name__ == "__main__":
    main()
