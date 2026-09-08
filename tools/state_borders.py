"""state_borders.py -- Track 1 CLI: the penalised, banded transportation LP that snaps the
committed k=18 draw's district borders onto state lines (docs/BORDERS_PLAN.md).

    .venv/bin/python3 tools/state_borders.py instance_descaled_v2.json.gz \\
        --draw battery/results/draw_k18_v2_20260904/k18/draw.csv \\
        --geo-cache data/geo --out battery/results/borders_k18_v2_20260907 --maps

Loads the committed draw once (`borders_report.load_committed`), then writes one grid row per
cell: the committed map itself, a zero-parameter state-border snap (`state_borders.pure_snap`),
a `state_borders.refine` at each `--delta` (band) and `--lam` (penalty), and again at each
`--soft-lam` and `--soft-delta` to show the soft regime. Every cell is scored on the completed
instance (`borders_report.cell_row`), written as its own `draw.csv` plus one file per Lloyd
round (`borders_report.write_cell`), and optionally mapped (`borders_report.render_cell_maps`).
`grid.csv`/`grid.md` are rewritten after every cell, so a killed run keeps whatever finished.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import geo                                                          # noqa: E402
from td.solvers import centers                                              # noqa: E402
from td.solvers import state_borders as sb                                  # noqa: E402
import borders_report                                                       # noqa: E402
import run_draw                                                             # noqa: E402


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--draw", required=True, help="the committed draw.csv")
    ap.add_argument("--k", type=int, default=18, help="must match the committed draw's k")
    ap.add_argument("--delta", type=float, nargs="+", default=[0.0, 0.01, 0.02, 0.05, 0.10],
                    help="band(s) for the main delta grid, at --lam (default 0 .01 .02 .05 .10)")
    ap.add_argument("--lam", type=float, default=100.0,
                    help="penalty (multiple of committed mean d^2) for the delta grid")
    ap.add_argument("--soft-lam", type=float, nargs="+", default=[1.0, 10.0],
                    help="penalty(ies) for the soft-regime grid, at --soft-delta")
    ap.add_argument("--soft-delta", type=float, default=0.02,
                    help="band for the soft-regime grid")
    ap.add_argument("--rounds", type=int, default=10, help="max Lloyd rounds per refine cell")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--maps", dest="maps", action="store_true", default=True,
                    help="render districts/regions-voronoi maps per cell (default on)")
    ap.add_argument("--no-maps", dest="maps", action="store_false")
    return ap


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    print(f"loading instance and committed draw ({args.draw})...", flush=True)
    ctx = borders_report.load_committed(args.instance, args.draw, args.geo_cache)
    if ctx.k != args.k:
        raise ValueError(f"--k {args.k} does not match the committed draw's k={ctx.k}")
    print(f"loaded: {len(ctx.zips)} geometric zips, k={ctx.k}", flush=True)

    compactness0 = centers.metrics(ctx.M, ctx.labels0, ctx.xy)["compactness"]
    base = compactness0 / ctx.M.sum()                     # committed mean d^2 -- lam_abs / lam_rel
    lam_abs = {lam: lam * base for lam in sorted({args.lam, *args.soft_lam})}

    params = dict(
        instance=os.path.abspath(args.instance),
        draw=os.path.abspath(args.draw),
        k=args.k,
        delta=args.delta,
        lam=args.lam,
        soft_lam=args.soft_lam,
        soft_delta=args.soft_delta,
        rounds=args.rounds,
        out=os.path.abspath(args.out),
        geo_cache=os.path.abspath(args.geo_cache),
        maps=args.maps,
        lam_abs=lam_abs,
    )
    with open(os.path.join(args.out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2, default=float)
        fh.write("\n")

    rows: list[dict] = []

    def run_cell(name: str, labels, params_row: dict, iterates=None) -> dict:
        t0 = time.time()
        row = borders_report.cell_row(ctx, labels, name, params_row)
        completed = run_draw.complete(labels, ctx.zips, ctx.states_by_zip, ctx.missing,
                                      ctx.M_by_zip)
        cell_dir = borders_report.write_cell(args.out, name, ctx, labels, completed,
                                             iterates=iterates)
        rows.append(row)
        borders_report.write_grid(args.out, rows)
        solve_s = time.time() - t0
        if args.maps:
            borders_report.render_cell_maps(cell_dir, args.geo_cache, report=print)
        total_s = time.time() - t0
        print(f"{name}: spread_rel={row['spread_rel']:.5f} "
              f"outside_owner_share={row['outside_owner_share']:.4f} "
              f"n_states_split={row['n_states_split']} zips_changed={row['zips_changed']} "
              f"stage2={row['stage2_value']:.4f} "
              f"({solve_s:.1f}s solve, {total_s:.1f}s total)", flush=True)
        return row

    run_cell("committed", ctx.labels0, {"n_fractional": 0})

    snap_labels = sb.pure_snap(ctx.xy, ctx.M, ctx.labels0, ctx.state_idx, ctx.k)
    run_cell("snap", snap_labels, {"n_fractional": 0})

    for delta in args.delta:
        name = f"d{delta:g}_lam{args.lam:g}"
        result = sb.refine(ctx.xy, ctx.M, ctx.labels0, ctx.state_idx, ctx.k,
                           lam_rel=args.lam, delta=delta, rounds=args.rounds)
        params_row = dict(delta=delta, lam_rel=args.lam, rounds_used=result["rounds_used"],
                          converged=result["converged"], n_fractional=result["n_fractional"])
        run_cell(name, result["labels"], params_row, iterates=result["iterates"])

    for lam in args.soft_lam:
        name = f"d{args.soft_delta:g}_lam{lam:g}"
        result = sb.refine(ctx.xy, ctx.M, ctx.labels0, ctx.state_idx, ctx.k,
                           lam_rel=lam, delta=args.soft_delta, rounds=args.rounds)
        params_row = dict(delta=args.soft_delta, lam_rel=lam, rounds_used=result["rounds_used"],
                          converged=result["converged"], n_fractional=result["n_fractional"])
        run_cell(name, result["labels"], params_row, iterates=result["iterates"])

    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
