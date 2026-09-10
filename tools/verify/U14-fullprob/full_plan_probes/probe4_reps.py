"""Item 4: driver R -- the per-state moves, the pin collision, and what the log records.

Part 1 runs the driver with `--driver reps` on both routes and prints the move log.
Part 2 is the independent oracle for "the forbid collides with the cover pin": the same
`forbid_bundle` is solved twice, once on the pinned problem the driver hands the move (which
is what `_rep_moves` uses) and once on the unpinned problem, so a collision with the pin is
distinguishable from a genuinely infeasible forbid.
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
from td import channels                                               # noqa: E402
from td.solvers import level0, state_splits as ss                     # noqa: E402

STATES = ["AA", "BB", "CC", "DD"]
ADJ = {"AA": ("BB",), "BB": ("AA", "CC"), "CC": ("BB", "DD"), "DD": ("CC",)}
SPEC = {s: dict(national=0.5, wh=0.5, fi=0.5) for s in STATES}


def drive(tmp, route, tag, extra=()):
    inst = os.path.join(tmp, "inst.json.gz")
    toy.write_v2_toy(inst, SPEC)
    out = os.path.join(tmp, f"out_{tag}")
    orig, td_geo = toy.patch_rook(ADJ)
    try:
        rc = cli.main([inst, "--route", route, "--driver", "reps", "--engine", "scipy",
                       "--strategy", "direct", "--k", "2", "--time-limit", "60",
                       "--out", out] + list(extra))
    finally:
        toy.unpatch(orig, td_geo)
    with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    print(f"--- {tag}: rc={rc}")
    print("   used slots:", [(r["id"], r["bundle"], round(r["mass"], 4), r["y"])
                             for r in plan["slots"] if r["used"]])
    print("   moves logged:", sorted({m["move"] for m in plan["moves"]}))
    for m in plan["moves"]:
        print("   ", m)
    return plan


def oracle(tmp):
    """Rebuild the joint model by hand, run the same passes, then compare a forbid on the
    pinned problem with the same forbid on the unpinned one."""
    from td import instance as descaled
    inst = os.path.join(tmp, "inst.json.gz")
    toy.write_v2_toy(inst, SPEC)
    d = channels.fine_split(descaled.load_descaled(inst))
    cells = channels.aggregate(d, STATES)
    edges = [(0, 1), (1, 2), (2, 3)]
    M = np.asarray(cells.M, float)
    tau = float(M[:, :2].sum()) / 2.0
    L, U = 0.8 * tau, 1.2 * tau
    bundles = {b: channels.BUNDLES[b] for b in channels.DEFAULT_BUNDLES}

    base = level0.build_level0(cells, bundles, edges=edges, L=L, U=U, eta=0.01,
                               order_mass=False)
    passes = [level0.cover_pass(base, list(bs), name=n) for n, bs in cli.JOINT_COVER
              if all(b in base.slots for b in bs)]
    passes.append(level0.contacts_pass(base))
    res = level0.solve_passes(base, passes, engine="scipy", strategy="direct", time_limit=60)
    pinned = res["problem"]
    print("oracle: pass log", [(p["name"], round(float(p["value"]), 6)) for p in res["passes"]])
    print("oracle: pin rows on the handed-back problem:",
          [k for k in pinned.rows if k.startswith("pin_")])

    for move, forbidden in cli.MOVES.items():
        if not forbidden:
            continue
        for s, code in enumerate(STATES[:2]):
            trial_p, trial_u = pinned, base
            for b in forbidden:
                if b in pinned.slots:
                    trial_p = level0.forbid_bundle(trial_p, s, b)
                    trial_u = level0.forbid_bundle(trial_u, s, b)
            got = {}
            for name, prob in (("pinned", trial_p), ("unpinned", trial_u)):
                try:
                    out = level0.solve_passes(prob, [level0.contacts_pass(prob)],
                                              engine="scipy", strategy="direct", time_limit=60)
                    got[name] = ("ok", round(float(out["passes"][0]["value"]), 4))
                except ss.SolveFailure as exc:
                    got[name] = ("SolveFailure", getattr(exc, "reason", "?"))
            print(f"oracle: move={move} state={code} pinned={got['pinned']} "
                  f"unpinned={got['unpinned']}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        drive(tmp, "joint", "joint_reps")
        drive(tmp, "sequential", "seq_reps")
        oracle(tmp)


if __name__ == "__main__":
    main()
