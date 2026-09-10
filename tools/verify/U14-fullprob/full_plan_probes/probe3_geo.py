"""Item 3: --n-max and --dist-max reach build_level0, and --dist-max measures km.

The rook graph is monkeypatched with real shapely boxes whose centroids sit at known LAEA
metre offsets: AA at x = 0, BB at x = 500 km, CC at x = 2,000 km, chained AA-BB-CC.  A single
national slot has to hold all three states to reach the floor, so a cap that forbids one pair
drops the covered mass to zero.  That is the discriminator.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                                    # noqa: E402
import shapely                                                        # noqa: E402
import toy                                                            # noqa: E402
import full_plan as cli                                               # noqa: E402
from td.solvers import level0                                         # noqa: E402

ADJ = {"AA": ("BB",), "BB": ("AA", "CC"), "CC": ("BB",)}
KM = 1000.0
POLYS = {
    "AA": shapely.box(-10 * KM, -10 * KM, 10 * KM, 10 * KM),
    "BB": shapely.box(500 * KM - 10 * KM, -10 * KM, 500 * KM + 10 * KM, 10 * KM),
    "CC": shapely.box(2000 * KM - 10 * KM, -10 * KM, 2000 * KM + 10 * KM, 10 * KM),
}
SPEC = {s: dict(national=0.4, wh=0.0, fi=0.0) for s in ADJ}


def run(tmp, args, tag):
    inst = os.path.join(tmp, "inst.json.gz")
    toy.write_v2_toy(inst, SPEC)
    out = os.path.join(tmp, f"out_{tag}")
    seen = {}
    real_build = level0.build_level0

    def build(cells, bundles, **kw):
        p = real_build(cells, bundles, **kw)
        seen.setdefault("kw", {k: kw.get(k) for k in ("n_max", "dist_max", "state_xy")})
        seen.setdefault("rows", dict(p.rows))
        return p

    level0.build_level0 = build
    orig, td_geo = toy.patch_rook(ADJ, POLYS)
    try:
        rc = cli.main([inst, "--route", "sequential", "--engine", "scipy", "--strategy",
                       "direct", "--k", "1", "--bundles", "N", "--priority", "N",
                       "--time-limit", "60", "--out", out] + args)
    finally:
        toy.unpatch(orig, td_geo)
        level0.build_level0 = real_build
    with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    cover = [p for p in plan["passes"] if p["name"].startswith("cover")]
    used = [(r["bundle"], round(r["mass"], 4), r["y"]) for r in plan["slots"] if r["used"]]
    print(f"--- {tag}: rc={rc} cover={cover[0]['value'] if cover else None} used={used}")
    print("   build kwargs:", {k: (np.round(v, 3).tolist() if isinstance(v, np.ndarray) else v)
                               for k, v in seen["kw"].items()})
    print("   cap rows:", {k: v for k, v in seen["rows"].items() if k.startswith("cap")})
    return plan


def main():
    with tempfile.TemporaryDirectory() as tmp:
        print("centroid km:", {c: (POLYS[c].centroid.x / 1000.0) for c in POLYS})
        run(tmp, [], "no_cap")
        run(tmp, ["--dist-max", "3000"], "dist3000")
        run(tmp, ["--dist-max", "1000"], "dist1000")
        run(tmp, ["--n-max", "2"], "nmax2")
        # the caps are dropped under --driver reps
        run(tmp, ["--dist-max", "1000", "--driver", "reps"], "dist1000_reps")


if __name__ == "__main__":
    main()
