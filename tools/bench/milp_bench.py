"""milp_bench.py -- bench the minimum-splits MILP across engines, on the real instance.

Builds the level-1 problem exactly as `tools/state_splits.py main` does with `--anchor-homes`
on (`M_s`, `D`, the rook graph, `tau`, `eps`, and the home-state `z` anchors, read via
`state_splits._state_masses_and_moments` and `ctx.home`), once per `k`, then runs each variant
below against that same problem, one process at a time, and writes one JSON with every
`(k, variant)` row to `battery/results/bench/milp_<stamp>.json` (`app.config.RESULTS / "bench"`,
the hub path whichever checkout this runs from).

    .venv/bin/python3 -u tools/bench/milp_bench.py instance_descaled_v2_conus.json.gz \\
        --draw battery/results/app/draw_grid-k20_20260908_144239/k20/draw.csv \\
        --ks 18,20 --cap 180

| variant              | engine            | exact? |
|----------------------|-------------------|--------|
| scipy                | scipy             | yes    |
| highs                | highs             | yes    |
| highs-root           | highs, roots fixed| yes    |
| scip                 | scip              | yes    |
| scip-root            | scip, roots fixed | yes    |
| lp-heur              | reweighted-L1 LP  | no (primal, upper bound) |
| cpsat                | OR-Tools CP-SAT   | no (primal, upper bound; `.venv-opt`) |
| highs-root-cutoff    | highs, roots fixed, `with_cutoff(best incumbent)` | yes |
| scip-root-cutoff     | scip,  roots fixed, `with_cutoff(best incumbent)` | yes |
| highs-root-warm      | highs, roots fixed, MIP-started from the best primal so far | yes |
| scip-root-warm       | scip,  roots fixed, MIP-started from the best primal so far | yes |

`*-cutoff` and `*-warm` need a prior incumbent from an earlier variant in the same cell (the
table's own order supplies one); asking for one with none run yet is a usage error, not a solve
failure.  A variant that raises `SolveFailure` still gets a row (status `"infeasible"` or
`"no_incumbent"`, every other field `None`) rather than stopping the whole bench.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
for _p in (ROOT, TOOLS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import geo                                              # noqa: E402
from td.solvers import milp_engines as me                       # noqa: E402
from td.solvers import state_splits as ss                       # noqa: E402
import borders_report                                            # noqa: E402
import state_splits as ts                                        # tools/state_splits.py  noqa: E402
from app import config                                            # noqa: E402  RESULTS only

DEFAULT_VARIANTS = ["scipy", "highs", "highs-root", "scip", "scip-root", "lp-heur", "cpsat",
                    "highs-root-cutoff", "scip-root-cutoff", "highs-root-warm", "scip-root-warm"]
THREADS = 12


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--draw", required=True, help="the committed draw.csv (its k sets --ks)")
    ap.add_argument("--ks", required=True, help="comma-separated k values, e.g. 18,20")
    ap.add_argument("--cap", type=float, required=True, help="time limit per variant, seconds")
    ap.add_argument("--variants", default=None,
                    help="comma-separated subset of the table (default: all, table order)")
    ap.add_argument("--out", default=None, help="output directory (default: config.RESULTS/bench)")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    return ap


def _variant_order(spec: str | None) -> list[str]:
    if spec is None:
        return list(DEFAULT_VARIANTS)
    wanted = [v.strip() for v in spec.split(",") if v.strip()]
    unknown = sorted(set(wanted) - set(DEFAULT_VARIANTS))
    if unknown:
        sys.exit(f"--variants: unknown {unknown}; expected a subset of {DEFAULT_VARIANTS}")
    return [v for v in DEFAULT_VARIANTS if v in wanted]


def _build_problem(instance: str, draw: str, geo_cache: str, k: int):
    """One level-1 `SplitProblem` plus its home-state anchors, exactly as `state_splits.py
    main --anchor-homes` builds it."""
    ctx = borders_report.load_committed(instance, draw, geo_cache)
    geo.assert_conus(ctx.d)
    if ctx.k != k:
        raise ValueError(f"--draw's k={ctx.k} does not match --ks value {k}")
    M_s, D, edges, tau, _C = ts._state_masses_and_moments(ctx, geo_cache)
    eps = ss.eps_lexicographic(M_s, D)
    anchors = [(int(ctx.home[j]), j) for j in range(ctx.k) if ctx.home[j] >= 0]
    problem = ss.build_milp(M_s, D, edges, tau, 0.10, eps, anchors=anchors)
    return problem, anchors


def _row(k: int, variant: str, *, status=None, objective=None, dual_bound=None, gap=None,
        splits=None, seconds=None, nodes=None, trajectory=None) -> dict:
    return dict(k=k, variant=variant, status=status, objective=objective, dual_bound=dual_bound,
               gap=gap, splits=splits, seconds=seconds, nodes=nodes,
               trajectory=trajectory if trajectory is not None else [])


def run_variant(variant: str, base, anchors, *, cap: float, best_s: int | None,
                best_warm: dict | None) -> tuple[dict, dict | None]:
    """One `(row, warm_payload)` pair; `warm_payload` is `{"z", "y"}` when the variant produced
    a solution (so a later `-warm` variant can start from whichever one is best so far), `None`
    on a `SolveFailure`."""
    t0 = time.time()
    root = variant.startswith(("highs-root", "scip-root"))
    engine = "highs" if variant.startswith("highs") else ("scip" if variant.startswith("scip")
                                                           else variant)
    problem = me.fix_roots(base, anchors) if root else base

    if variant == "lp-heur":
        out = me.lp_heuristic(base)
        row = _row(0, variant, status="heuristic", splits=out["splits"], seconds=out["seconds"])
        return row, dict(z=out["z"], y=out["y"])

    cutoff_variant = variant.endswith("-cutoff")
    warm_variant = variant.endswith("-warm")
    if (cutoff_variant or warm_variant) and best_s is None:
        sys.exit(f"--variants: {variant} needs a prior incumbent; run a primal or exact "
                 "variant before it")
    if cutoff_variant:
        problem = me.with_cutoff(problem, best_s)
    warm = best_warm if warm_variant else None

    try:
        res = me.solve_problem(problem, engine, time_limit=cap, warm=warm,
                              threads=(None if engine == "scipy" else THREADS))
    except ss.SolveFailure as exc:
        return _row(0, variant, status=exc.reason, seconds=time.time() - t0), None

    row = _row(0, variant, status=res["status"], objective=res["objective"],
              dual_bound=res["dual_bound"], gap=res["mip_gap"], splits=res["splits"],
              seconds=time.time() - t0, nodes=res["nodes"], trajectory=res["trajectory"])
    return row, dict(z=res["z"], y=res["y"])


def run_k(k: int, instance: str, draw: str, geo_cache: str, variants: list[str],
          cap: float) -> list[dict]:
    print(f"k={k}: building the level-1 problem...", flush=True)
    base, anchors = _build_problem(instance, draw, geo_cache, k)
    rows = []
    best_s, best_warm = None, None
    for variant in variants:
        row, payload = run_variant(variant, base, anchors, cap=cap, best_s=best_s,
                                   best_warm=best_warm)
        row["k"] = k
        rows.append(row)
        print(f"k={k} {variant}: status={row['status']} splits={row['splits']} "
              f"gap={row['gap']} ({row['seconds']:.1f}s)", flush=True)
        if row["splits"] is not None and (best_s is None or row["splits"] < best_s):
            best_s = row["splits"]
            best_warm = payload
    return rows


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    variants = _variant_order(args.variants)
    ks = [int(k) for k in args.ks.split(",") if k.strip()]

    rows = []
    for k in ks:
        rows.extend(run_k(k, args.instance, args.draw, args.geo_cache, variants, args.cap))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or str(config.RESULTS / "bench")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"milp_{stamp}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(dict(instance=os.path.abspath(args.instance), draw=os.path.abspath(args.draw),
                      cap=args.cap, ks=ks, variants=variants, rows=rows), fh, indent=2)
        fh.write("\n")
    print(f"wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
