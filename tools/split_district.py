"""split_district.py -- divide one district of a zip table among several reps.

    .venv/bin/python3 -u tools/split_district.py instance_descaled_v2_conus.json.gz \\
        --table battery/results/.../draw.csv --district D05 --reps R1,R2,R3 \\
        --exact --time-limit 60 --out battery/results/app/split_d05

Reads a zip table, takes the rows of one district, builds those reps' utilities on them from
the instance's books (`district_split.unrestricted_utilities`, candidacy ignored the way
staffing ignores it), and runs `td.solvers.district_split`.  Writes the same table back with
the `rep` column set on the district's rows and nothing else touched -- `district` in
particular is unchanged, because a split is a division *inside* a district, not a redraw --
plus `split.json` with the gains, the shares and how the answer was reached.

Mass comes from the table's `opportunity` column and books come from the instance: the table
is the unit, and the instance is opened only for `S`, `cand` and `S_free` (the plan's second
invariant).  `split.json` carries ratios and log-gains only, never a raw mass.

`--geom` gives the run's `geom.json`; its `cell_edges` build the Voronoi cell graph over the
district's zips, and the split is then contiguity-guarded on that graph
(`td.solvers.district_split`).  `split.json` gains `pieces` (one connected-piece count per rep)
and `contiguous` (true iff every rep holds one piece per component it appears in); without
`--geom` both are `null`.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                          # noqa: E402

from td import geo, instance, model, telemetry, ziptable                    # noqa: E402
from td.solvers import district_split                                       # noqa: E402


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--table", required=True, help="the zip table to split a district of")
    ap.add_argument("--district", required=True, help="the district to split")
    ap.add_argument("--reps", required=True, help="comma-separated reps to divide it among")
    ap.add_argument("--exact", action="store_true",
                    help="also run the SCIP MINLP, warm-started from the greedy answer")
    ap.add_argument("--time-limit", type=float, default=60.0, help="SCIP time limit, seconds")
    ap.add_argument("--theta", type=float, default=0.40)
    ap.add_argument("--lam", type=float, default=0.30)
    ap.add_argument("--filler-capture", default="full", choices=list(model.FILLER_CAPTURE))
    ap.add_argument("--n-near", type=int, default=3,
                    help="a zip may only move to one of its n nearest rep centres")
    ap.add_argument("--geom", help="the run's geom.json; its cell_edges make the split "
                    "contiguous on the Voronoi cell graph")
    ap.add_argument("--out", required=True, help="output directory")
    return ap


def build_adjacency(geom: dict, zips: list[str]) -> dict | None:
    """The Voronoi cell graph over `zips`, `{column index: {neighbour column index, ...}}`,
    built from `geom["cell_edges"]` restricted to pairs both present in `geom["cells"]` and both
    in `zips`.  `None` when `geom` carries no `"cells"` key (a geom.json from before cells were
    exported)."""
    if "cells" not in geom:
        return None
    col = {z: j for j, z in enumerate(zips)}
    adjacency = {col[z]: set() for z in zips if z in geom["cells"]}
    for a, b in geom["cell_edges"]:
        if a in col and b in col and col[a] in adjacency and col[b] in adjacency:
            adjacency[col[a]].add(col[b])
            adjacency[col[b]].add(col[a])
    return adjacency


def _fail(out: str, reason: str) -> int:
    """Driver convention: `failure.json` with a reason, and a nonzero exit."""
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "failure.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(step="split", reason=reason), fh, indent=2)
        fh.write("\n")
    print(f"split: FAILED -- {reason}", file=sys.stderr, flush=True)
    return 1


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    T = telemetry.Timings("split")
    try:
        with T.phase("load"):
            d = instance.load_descaled(args.instance)
            geo.assert_conus(d)

            rows = ziptable.read(args.table)
            inside = [r for r in rows if r["district"] == args.district]
            if not inside:
                return _fail(args.out,
                             f"no row of {args.table} carries district {args.district!r}")
            zips = [r["zip"] for r in inside]
            missing = [z for z in zips if z not in d.G]
            if missing:
                return _fail(args.out,
                             f"{len(missing)} zip(s) of {args.district} are absent from the "
                             f"instance (e.g. {missing[:3]})")

            reps = [r.strip() for r in args.reps.split(",") if r.strip()]
            if len(reps) < 2:
                return _fail(args.out, f"a split needs two or more reps; got {reps}")
            if len(zips) < len(reps):
                return _fail(args.out,
                             f"{len(zips)} zip(s) cannot be split among {len(reps)} reps")

            masses = {r["zip"]: float(r["opportunity"]) for r in inside}
            u = district_split.unrestricted_utilities(
                d.G, zips, reps, masses, theta=args.theta, lam=args.lam,
                filler_capture=args.filler_capture)
            book = district_split.book_matrix(d.G, zips, reps)
            M = np.array([masses[z] for z in zips], float)
            xy = np.array([[np.nan if r["x"] is None else r["x"],
                            np.nan if r["y"] is None else r["y"]] for r in inside], float)

            adjacency = None
            if args.geom:
                with open(args.geom, encoding="utf-8") as fh:
                    geom = json.load(fh)
                adjacency = build_adjacency(geom, zips)
                if adjacency is None:
                    return _fail(args.out,
                                 f"{args.geom} has no cells (a geom.json from before cells "
                                 f"were exported)")

        # `district_split.split` runs greedy always and, under --exact, escalates to a SCIP
        # MINLP warm-started from it; the two engines are opaque from here (td/solvers is not
        # ours to instrument this workstream), so the whole call is billed to whichever one
        # dominates the wall clock -- "scip" when --exact asked for it, "greedy" otherwise.
        t0 = time.time()
        try:
            with T.phase("scip" if args.exact else "greedy") as ph:
                res = district_split.split(u, M, xy, reps, book=book, n_near=args.n_near,
                                           use_exact=args.exact, time_limit=args.time_limit,
                                           adjacency=adjacency)
                ph.note(method=res["method"], status=res["status"], gap=res["gap"])
        except (ValueError, ImportError) as exc:
            return _fail(args.out, str(exc))
        seconds = time.time() - t0

        with T.phase("write"):
            by_zip = dict(zip(zips, res["labels"]))
            out_rows = [dict(r, rep=by_zip.get(r["zip"], r["rep"])) for r in rows]
            ziptable.write(os.path.join(args.out, "draw.csv"), out_rows)

            total = sum(res["gains"].values())
            report = dict(
                district=args.district,
                reps=res["reps"],
                objective=res["objective"],
                gains=res["gains"],
                shares={r: (g / total if total > 0 else 0.0) for r, g in res["gains"].items()},
                method=res["method"],
                gap=(None if res["gap"] is None or not math.isfinite(res["gap"])
                     else res["gap"]),
                status=res["status"],
                n_zips=len(zips),
                dropped_reps=res["dropped_reps"],
                pieces=res["pieces"],
                contiguous=res["contiguous"],
                seconds=seconds,
            )
            with open(os.path.join(args.out, "split.json"), "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, default=float)
                fh.write("\n")

        shares = " ".join(f"{r}={report['shares'][r]:.3f}" for r in res["reps"])
        pieces = ("-" if res["pieces"] is None
                  else " ".join(f"{r}={n}" for r, n in res["pieces"].items()))
        print(f"split {args.district}: {len(zips)} zips over {len(res['reps'])} reps, "
              f"method={res['method']} status={res['status']} "
              f"gap={'-' if report['gap'] is None else format(report['gap'], '.2e')} "
              f"objective={res['objective']:.6f} moves={res['moves']} shares[{shares}] "
              f"pieces[{pieces}] "
              f"dropped={res['dropped_reps'] or '-'} ({seconds:.1f}s) -> {args.out}", flush=True)
        return 0
    finally:
        T.write(args.out)


if __name__ == "__main__":
    sys.exit(telemetry.maybe_profile(main)())
