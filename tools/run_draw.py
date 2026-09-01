"""run_draw.py -- the reproducible stage-1 draw: instance in, a staffed map out.

    .venv/bin/python3 tools/run_draw.py instance_descaled.json.gz --k 13 \\
        --seeds 0 1 2 3 4 --out battery/results/draw_k13_20260901/

One command for the whole pipeline, so a map is always reproducible from a run id::

    load instance          td.instance.load_descaled
    coordinates            td.geo.zcta_points  (cached under data/geo/, no network if present)
    stage 1                td.solvers.centers.portfolio      one balanced draw per seed
    complete each draw     td.channel.place_by_state         the zips with no coordinates
    stage 2                td.channel.score_draws            rank the draws by how they staff

The ranking is the point of running several seeds.  Stage 1 cannot see rep relationships, so
a draw that is beautifully balanced may staff badly; stage 2 is milliseconds, so the portfolio
is scored and the *best-staffing* draw wins, not the best-balanced one (CLAUDE.md's mitigation
for the two-stage split).  Both numbers are recorded per draw in `metrics.json` so the cost of
that choice is visible rather than assumed.

Written into `--out`:

    draw.csv      zip,district for the winning draw -- every instance zip, including the ones
                  placed by state.  This is what tools/us_maps.py --districts reads.
    metrics.json  per-draw stage-1 metrics (before *and* after the state placements), the
                  stage-2 value and assignment, and the winner's balance report.

District ids are the strings `D01`..`Dk`, not the raw 0-based labels, so the CSV, the JSON,
the summary table and the figure's direct labels all say the same word.  Exit status is
nonzero if any district ends up unstaffed -- that would mean fewer reps than districts, which
is a data problem and must not pass silently.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..")))

from td import channel, geo                                                # noqa: E402
from td import instance as descaled                                        # noqa: E402
from td.solvers import centers                                             # noqa: E402


def district_id(label) -> str:
    """0-based stage-1 label -> `D01`.  One name for a district everywhere downstream."""
    return f"D{int(label) + 1:02d}"


def default_run_id(k, when=None) -> str:
    when = when or _dt.date.today()
    return f"draw_k{int(k)}_{when:%Y%m%d}"


# ------------------------------------------------------------------ the pipeline
def coordinates(zips, cache=geo.DEFAULT_DEST):
    """`(xy, missing)` -- projected LAEA points for the zips the gazetteer carries.

    `missing` is returned rather than raised: on the real instance it is 6 zips out of 1,229
    (retired or non-ZCTA codes), and they are placed afterwards by `channel.place_by_state`,
    not dropped.  Dropping them would quietly shrink the total opportunity the balance is
    measured against.
    """
    points = geo.zcta_points(cache)
    have = [z for z in zips if z in points]
    missing = [z for z in zips if z not in points]
    x, y = geo.project([points[z][0] for z in have], [points[z][1] for z in have])
    return {z: (float(a), float(b)) for z, a, b in zip(have, x, y)}, missing


def complete(labels, placed_zips, states, missing, M) -> dict:
    """A stage-1 labelling -> the completed `{zip: 'D01'}` mapping stage 2 consumes."""
    to_d = {z: district_id(d) for z, d in centers.to_district(placed_zips, labels).items()}
    return channel.place_by_state(states, to_d, missing, M)


def _stage1_metrics(res, M_by_zip, placed_zips, completed) -> dict:
    """Stage-1 metrics as drawn, and again after the coordinate-less zips are placed."""
    before = {k: v for k, v in res.items() if k not in ("labels", "centers")}
    per = {}
    for z, d in completed.items():
        per[d] = per.get(d, 0.0) + float(M_by_zip[z])
    vals = np.array([per[d] for d in sorted(per)], float)
    mean = float(vals.mean())
    return dict(
        seed=int(res["seed"]),
        before=before,
        after=dict(k=int(vals.size), total=float(vals.sum()), mean=mean,
                   min=float(vals.min()), max=float(vals.max()),
                   masses={d: float(per[d]) for d in sorted(per)},
                   nash=float(np.log(vals).sum()),
                   spread_rel=float((vals.max() - vals.min()) / mean),
                   max_dev_rel=float(np.abs(vals - mean).max() / mean)),
        n_placed_by_state=len(completed) - len(placed_zips),
    )


# ------------------------------------------------------------------ reporting
def summary_rows(completed, M_by_zip, states, assignment=None) -> list:
    """Per district: id, zips, M, share of total, top state (by zip count), staffing rep."""
    per, cnt, st = {}, {}, {}
    for z, d in completed.items():
        per[d] = per.get(d, 0.0) + float(M_by_zip[z])
        cnt[d] = cnt.get(d, 0) + 1
        s = states.get(z) or "??"
        st.setdefault(d, {})[s] = st.setdefault(d, {}).get(s, 0) + 1
    total = sum(per.values()) or 1.0
    rows = []
    for d in sorted(per):
        top = max(sorted(st.get(d, {"??": 0})), key=lambda s: (st[d][s], s)) if st.get(d) \
            else "??"
        share = st.get(d, {}).get(top, 0) / cnt[d] if cnt.get(d) else 0.0
        rows.append(dict(district=d, zips=cnt[d], M=per[d], share=per[d] / total,
                         top_state=top, top_state_share=share,
                         rep=(assignment or {}).get(d, "")))
    return rows


def print_summary(rows) -> None:
    staffed = any(r["rep"] for r in rows)
    head = f"{'district':<9}{'zips':>6}{'M':>12}{'share':>9}  {'top state':<12}"
    print(head + ("rep" if staffed else ""))
    print("-" * (len(head) + (3 if staffed else 0)))
    for r in rows:
        top = "{} ({:.0%})".format(r["top_state"], r["top_state_share"])
        line = (f"{r['district']:<9}{r['zips']:>6}{r['M']:>12,.1f}{r['share']:>8.2%}  "
                f"{top:<12}")
        print(line + (str(r["rep"]) if staffed else ""))
    tot = sum(r["M"] for r in rows)
    n = len(rows) or 1
    lo, hi = min(r["M"] for r in rows), max(r["M"] for r in rows)
    print("-" * (len(head) + (3 if staffed else 0)))
    print(f"{'total':<9}{sum(r['zips'] for r in rows):>6}{tot:>12,.1f}{1.0:>8.2%}  "
          f"spread {(hi - lo) / (tot / n):.3%}")


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", nargs="?", default="instance_descaled.json.gz")
    ap.add_argument("--k", type=int, default=13, help="number of districts (default 13)")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4],
                    help="stage-1 seeds; one draw per seed (default 0..4)")
    ap.add_argument("--out", default=None,
                    help="output directory (default battery/results/draw_k<k>_<YYYYMMDD>/)")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--theta", type=float, default=0.40, help="stage-2 theta")
    ap.add_argument("--lam", type=float, default=0.30, help="stage-2 lambda")
    ap.add_argument("--filler-capture", default="theta", help="stage-2 filler-capture mode")
    args = ap.parse_args(argv)

    out_dir = args.out or os.path.join("battery", "results", default_run_id(args.k))
    os.makedirs(out_dir, exist_ok=True)

    d = descaled.load_descaled(args.instance)
    print(f"instance: {d.summary()}")
    zips = sorted(d.G)
    M_by_zip = {z: float(d.G.nodes[z]["M"]) for z in zips}
    states = {z: d.G.nodes[z].get("state") or "" for z in zips}

    xy, missing = coordinates(zips, args.geo_cache)
    print(f"geometry: {len(xy):,} of {len(zips):,} zips have gazetteer coordinates; "
          f"{len(missing)} placed by state" + (f" {missing}" if missing else ""))

    placed = [z for z in zips if z in xy]
    XY = np.array([xy[z] for z in placed], float)
    M = np.array([M_by_zip[z] for z in placed], float)

    print(f"stage 1:  k={args.k}, seeds {args.seeds}")
    ranked1 = centers.portfolio(XY, M, args.k, args.seeds)
    draws, per_draw = [], []
    for res in ranked1:
        completed = complete(res["labels"], placed, states, missing, M_by_zip)
        draws.append(completed)
        per_draw.append(_stage1_metrics(res, M_by_zip, placed, completed))
        m = per_draw[-1]
        print(f"  seed {m['seed']}: spread {m['before']['spread_rel']:.3%} drawn -> "
              f"{m['after']['spread_rel']:.3%} completed, nash {m['after']['nash']:.6f}")

    print("stage 2:  Hungarian on log gains")
    ranked2 = channel.score_draws(d.G, draws, theta=args.theta, lam=args.lam,
                                  filler_capture=args.filler_capture)
    for r in ranked2:
        per_draw[r["draw"]]["stage2_value"] = float(r["value"])
        per_draw[r["draw"]]["stage2_unstaffed"] = list(r["unstaffed_districts"])
    best = ranked2[0]
    winner, wm = draws[best["draw"]], per_draw[best["draw"]]
    print(f"  best: seed {wm['seed']} (draw {best['draw']}), value {best['value']:.6f}; "
          f"stage-1-best seed was {per_draw[0]['seed']}")

    rows = summary_rows(winner, M_by_zip, states, best["assignment"])
    print()
    print_summary(rows)

    draw_csv = os.path.join(out_dir, "draw.csv")
    with open(draw_csv, "w", encoding="utf-8") as fh:
        fh.write("zip,district\n")
        for z in sorted(winner):
            fh.write(f"{z},{winner[z]}\n")

    metrics = dict(
        run_id=os.path.basename(os.path.normpath(out_dir)),
        written=_dt.datetime.now().isoformat(timespec="seconds"),
        instance=os.path.abspath(args.instance),
        k=args.k, seeds=list(args.seeds),
        theta=args.theta, lam=args.lam, filler_capture=args.filler_capture,
        n_zips=len(zips), n_with_coordinates=len(placed),
        placed_by_state={z: winner[z] for z in missing},
        winner=dict(draw=int(best["draw"]), seed=int(wm["seed"]),
                    stage2_value=float(best["value"]),
                    assignment={k: str(v) for k, v in best["assignment"].items()},
                    unmatched_reps=[str(r) for r in best["unmatched_reps"]],
                    unstaffed_districts=list(best["unstaffed_districts"]),
                    balance_report=best["balance"]),
        draws=per_draw,
        summary=rows,
    )
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, sort_keys=False, default=float)
        fh.write("\n")
    print(f"\nwrote {draw_csv} and {os.path.join(out_dir, 'metrics.json')}")

    if best["unstaffed_districts"]:
        print(f"ERROR: {len(best['unstaffed_districts'])} district(s) unstaffed: "
              f"{best['unstaffed_districts']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
