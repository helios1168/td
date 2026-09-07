"""state_splits.py -- Track 2 CLI: the state-level minimum-splits MILP driver
(docs/BORDERS_PLAN.md "Track 2 -- the state-level minimum-splits MILP").

    .venv/bin/python3 tools/state_splits.py instance_descaled_v2.json.gz \\
        --draw battery/results/draw_k18_v2_20260904/k18/draw.csv \\
        --geo-cache data/geo --out battery/results/splits_k18_v2_20260907 --maps

Loads the committed draw once (`borders_report.load_committed`), then builds the level-1 data
once: state masses `M_s` and moments `D_sj` about the committed centres over the lower 48 plus
DC (`ctx.state_idx`), and the rook graph over those same state indices (`td.geo.state_rook`).
Prints one sanity row -- is the committed map's own state composition band-feasible and
connected at delta = 1.3%, checked directly, not solved for -- then for every `--delta`:

    1. `td.solvers.state_splits.build_milp` / `solve` (time-limited, `strict=False`: an
       unclosed run reports its incumbent and gap instead of raising);
    2. `balance_pass`, fixing `z` and tightening `y`;
    3. `realise`, turning `(z, y)` into zip labels over the known-state zips, then
       `channel.place_by_state` for AK, HI and the unknown-state zips -- excluded from the MILP
       by design, placed the same way `run_draw.complete` places the gazetteer-missing ones;
    4. `borders_report.cell_row` / `write_cell` (and maps, if `--maps`), plus a per-delta
       `splits.json` with the full `z`/`y` and the MILP's own objective, status and gap.

`grid.csv` / `grid.md` are rewritten after every cell, so a killed run keeps whatever finished.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channel, geo, model                                          # noqa: E402
from td.solvers import centers                                              # noqa: E402
from td.solvers import state_splits as ss                                   # noqa: E402
import borders_report                                                       # noqa: E402
import run_draw                                                             # noqa: E402

# the sanity-row delta: the committed k=18 draw's own spread_rel (docs/BORDERS_PLAN.md)
COMMITTED_SPREAD = 0.013


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--draw", required=True, help="the committed draw.csv")
    ap.add_argument("--k", type=int, default=18, help="must match the committed draw's k")
    ap.add_argument("--delta", type=float, nargs="+", default=[0.0, 0.01, 0.02, 0.05, 0.10],
                    help="band(s) for the minimum-splits MILP (default 0 .01 .02 .05 .10)")
    ap.add_argument("--time-limit", type=float, default=300.0,
                    help="seconds per MILP; an unclosed run reports its incumbent and gap")
    ap.add_argument("--rounds", type=int, default=5,
                    help="max Lloyd rounds per split state at level 2")
    ap.add_argument("--eta", type=float, default=0.01,
                    help="minimum share a state flagged z_sj=1 must actually send")
    ap.add_argument("--incumbency-tiebreak", action="store_true", default=False,
                    help="level-2 bonus toward the committed map's rep(j) book (off by default)")
    ap.add_argument("--anchor-homes", action="store_true", default=False,
                    help="force z=1 for each district in its committed home state; names the "
                         "districts so HiGHS can close the MILP (off by default)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--maps", dest="maps", action="store_true", default=True,
                    help="render districts/regions-voronoi maps per cell (default on)")
    ap.add_argument("--no-maps", dest="maps", action="store_false")
    return ap


def _dlabel(name: str) -> int:
    """`"D07"` -> `6` -- the inverse of `run_draw.district_id`."""
    return int(name[1:]) - 1


# ------------------------------------------------------------------------------ level-1 data
def _state_masses_and_moments(ctx, geo_cache: str):
    """`(M_s, D, edges, tau, C)` for the lower-48-plus-DC states in `ctx.state_idx`.

    `M_s` is each state's mass; `C` the committed draw's `k` centroids; `D[s, j]` the exact
    moment of state `s` about centre `j`; `edges` the rook graph (`td.geo.state_rook`) mapped
    onto `ctx.state_list`'s indices; `tau` the equal-split target over this state population.
    """
    known = ctx.state_idx >= 0
    n_state = len(ctx.state_list)
    M_s = np.bincount(ctx.state_idx[known], weights=ctx.M[known], minlength=n_state).astype(float)

    C = centers._centroids(ctx.xy, ctx.M, ctx.labels0, ctx.k)
    d2 = ((ctx.xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    num = np.zeros((n_state, ctx.k), float)
    np.add.at(num, ctx.state_idx[known], ctx.M[known, None] * d2[known])
    D = np.divide(num, M_s[:, None], out=np.zeros_like(num), where=M_s[:, None] > 0)

    adj, _ = geo.state_rook(geo_cache)
    code_to_idx = {c: i for i, c in enumerate(ctx.state_list)}
    stray = sorted(set(adj) - set(code_to_idx))
    if stray:
        raise ValueError(f"state_rook codes not in the state list: {stray}")
    edges = sorted({(min(code_to_idx[a], code_to_idx[b]), max(code_to_idx[a], code_to_idx[b]))
                    for a, nbrs in adj.items() for b in nbrs})

    tau = float(M_s.sum()) / ctx.k
    return M_s, D, edges, tau, C


def _sanity_row(ctx, M_s: np.ndarray, edges: list, tau: float, delta: float) -> None:
    """Is the committed map's own state composition `y0` feasible at `delta`?  Band and
    connectivity are checked directly on `y0`/`z0`; nothing is solved for."""
    known = ctx.state_idx >= 0
    n_state = len(ctx.state_list)
    mass_sj = np.zeros((n_state, ctx.k), float)
    np.add.at(mass_sj, (ctx.state_idx[known], ctx.labels0[known]), ctx.M[known])
    y0 = np.divide(mass_sj, M_s[:, None], out=np.zeros_like(mass_sj), where=M_s[:, None] > 0)
    z0 = mass_sj > 0

    masses = M_s @ y0
    spread_rel = float((masses.max() - masses.min()) / masses.mean())
    max_dev_rel = float(np.abs(masses - tau).max() / tau)
    band_ok = max_dev_rel <= delta + 1e-9
    conn_ok = all(ss.connected(z0[:, j], edges) for j in range(ctx.k))
    below_eta = int(np.sum(z0 & (y0 < 0.01)))
    print(f"sanity @ delta={delta:g}: committed y0 feasible={band_ok and conn_ok} "
          f"(band_ok={band_ok} max_dev_rel={max_dev_rel:.4f} spread_rel={spread_rel:.4f} "
          f"connectivity_ok={conn_ok} state-district contacts below eta={below_eta})",
          flush=True)


# ------------------------------------------------------------------------- incumbency tiebreak
def _raw_tiebreak(ctx, zips_known: list) -> np.ndarray:
    """`(len(zips_known), k)` book of district `j`'s committed rep at each known-state zip,
    unscaled (mu = 1).  `--incumbency-tiebreak` needs `ctx.committed_rep_of` (the committed
    map's `metrics.json`, `{"D0X": rep}`) and `model.books(G, z)`; both are reachable off `ctx`,
    so this is the real tiebreak, not the fallback `NotImplementedError`."""
    if ctx.committed_rep_of is None:
        raise NotImplementedError(
            "--incumbency-tiebreak needs the committed draw's metrics.json (rep(j) "
            "assignment) next to --draw; none was found")
    rep_of = [ctx.committed_rep_of.get(run_draw.district_id(j)) for j in range(ctx.k)]
    tb = np.zeros((len(zips_known), ctx.k), float)
    for i, z in enumerate(zips_known):
        S = model.books(ctx.d.G, z)
        for j, rep in enumerate(rep_of):
            if rep is not None:
                tb[i, j] = S.get(rep, 0.0)
    return tb


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    print(f"loading instance and committed draw ({args.draw})...", flush=True)
    ctx = borders_report.load_committed(args.instance, args.draw, args.geo_cache)
    if ctx.k != args.k:
        raise ValueError(f"--k {args.k} does not match the committed draw's k={ctx.k}")
    print(f"loaded: {len(ctx.zips)} geometric zips, k={ctx.k}", flush=True)

    M_s, D, edges, tau, C = _state_masses_and_moments(ctx, args.geo_cache)
    n_state = M_s.shape[0]
    print(f"states: {n_state} (lower 48 + DC), edges={len(edges)}, "
          f"tau={tau:.6g}, total_state_mass={M_s.sum():.6g}", flush=True)
    _sanity_row(ctx, M_s, edges, tau, COMMITTED_SPREAD)

    eps = ss.eps_lexicographic(M_s, D)

    anchors = None
    if args.anchor_homes:
        anchors = [(int(ctx.home[j]), j) for j in range(ctx.k) if ctx.home[j] >= 0]
        print(f"anchors: {len(anchors)} districts held in their committed home states "
              f"({', '.join(run_draw.district_id(j) + '=' + ctx.state_list[s] for s, j in anchors)})",
              flush=True)

    known = ctx.state_idx >= 0
    zips_known = [z for z, kk in zip(ctx.zips, known) if kk]
    zips_unknown = [z for z, kk in zip(ctx.zips, known) if not kk]
    xy_k, M_k, state_idx_k = ctx.xy[known], ctx.M[known], ctx.state_idx[known]

    tiebreak = None
    if args.incumbency_tiebreak:
        tb_raw = _raw_tiebreak(ctx, zips_known)
        compactness0 = centers.metrics(ctx.M, ctx.labels0, ctx.xy)["compactness"]
        bound = float((M_k * tb_raw.max(axis=1)).sum())
        mu = 0.01 * compactness0 / bound if bound > 0 else 0.0
        tiebreak = tb_raw * mu
        print(f"incumbency tiebreak: mu={mu:.6g} (bound={bound:.6g}, "
              f"committed compactness={compactness0:.6g})", flush=True)

    params = dict(
        instance=os.path.abspath(args.instance), draw=os.path.abspath(args.draw), k=args.k,
        delta=args.delta, time_limit=args.time_limit, rounds=args.rounds, eta=args.eta,
        incumbency_tiebreak=args.incumbency_tiebreak, anchor_homes=args.anchor_homes,
        out=os.path.abspath(args.out),
        geo_cache=os.path.abspath(args.geo_cache), maps=args.maps, eps=eps, tau=tau,
        n_state=n_state, n_edges=len(edges),
    )
    with open(os.path.join(args.out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2, default=float)
        fh.write("\n")

    rows: list[dict] = []

    def run_cell(delta: float) -> dict:
        name = f"d{delta:g}"
        t0 = time.time()
        problem = ss.build_milp(M_s, D, edges, tau, delta, eps, eta=args.eta, anchors=anchors)
        result = ss.solve(problem, time_limit=args.time_limit, strict=False)
        solve_s = time.time() - t0
        split_codes = ",".join(sorted(ctx.state_list[s] for s in result["split_states"]))
        y_shares = {ctx.state_list[s]: {run_draw.district_id(j): round(float(result["y"][s, j]), 4)
                                        for j in np.flatnonzero(result["z"][s])}
                   for s in result["split_states"]}
        print(f"{name}: status={result['status']} splits={result['splits']} "
              f"split_states=[{split_codes}] milp_spread_rel={result['spread_rel']:.5f} "
              f"mip_gap={result['mip_gap']:.4g} ({solve_s:.1f}s solve)", flush=True)

        pas = ss.balance_pass(problem, result["z"])
        print(f"{name}: balance pass spread_rel={pas['spread_rel']:.5f} "
              f"max_dev_rel={pas['max_dev_rel']:.5f}", flush=True)

        realised = ss.realise(xy_k, M_k, state_idx_k, result["z"], pas["y"], C,
                              rounds=args.rounds, tiebreak=tiebreak)
        to_district_known = {z: run_draw.district_id(int(lab))
                             for z, lab in zip(zips_known, realised["labels"])}
        placed = channel.place_by_state(ctx.states_by_zip, to_district_known, zips_unknown,
                                        ctx.M_by_zip)
        labels_full = np.array([_dlabel(placed[z]) for z in ctx.zips], int)

        rounds_vals = list(realised["rounds_used"].values())
        params_row = dict(
            delta=delta, splits=result["splits"], status=result["status"],
            mip_gap=result["mip_gap"], milp_spread=result["spread_rel"],
            pass_spread=pas["spread_rel"], pass_max_dev=pas["max_dev_rel"],
            n_fractional=realised["n_fractional"],
            rounds_used=max(rounds_vals) if rounds_vals else 0,
        )
        row = borders_report.cell_row(ctx, labels_full, name, params_row)
        completed = run_draw.complete(labels_full, ctx.zips, ctx.states_by_zip, ctx.missing,
                                      ctx.M_by_zip)
        cell_dir = borders_report.write_cell(args.out, name, ctx, labels_full, completed)
        rows.append(row)
        borders_report.write_grid(args.out, rows)

        with open(os.path.join(cell_dir, "splits.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(
                delta=delta, status=result["status"], mip_gap=result["mip_gap"],
                objective=result["objective"], splits=result["splits"],
                split_states=split_codes, y_shares=y_shares,
                z=result["z"].astype(bool).tolist(), y=pas["y"].tolist(),
                state_list=ctx.state_list,
            ), fh, indent=2)
            fh.write("\n")

        if args.maps:
            borders_report.render_cell_maps(args.instance, cell_dir, args.geo_cache)
        total_s = time.time() - t0
        print(f"{name}: spread_rel={row['spread_rel']:.5f} "
              f"outside_owner_share={row['outside_owner_share']:.4f} "
              f"n_states_split={row['n_states_split']} zips_changed={row['zips_changed']} "
              f"stage2={row['stage2_value']:.4f} "
              f"({solve_s:.1f}s solve, {total_s:.1f}s total)", flush=True)
        return row

    for delta in args.delta:
        run_cell(delta)

    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
