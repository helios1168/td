"""plan_to_app.py: a finished `tools/full_plan.py` + `tools/plan_realise.py` run -> app runs.

    .venv/bin/python3 tools/plan_to_app.py battery/results/full_problem/v3_seq_warm \\
        --name v3-seq-warm --geo-cache /Users/ntlee/projects/td/data/geo

One run directory per business channel in the app's store (`battery/results/app`), so the
plan's maps open in the Streamlit app beside every other map.  A channel is what the file
carries -- national, wh, fi -- and each becomes one scenario member (`store.member_name`'s
channel token).  A bundle is a way of serving one or more channels, so a bundle appears on
every channel map it carries: `district` is the slot id, which already names its bundle
(`N_03`, `FI_PLUS_01`, `WHFI_02`), and the map draws a plus or merged bundle with a hatch.

A channel's zip table is read off `assignment.csv` alone: `opportunity` is the zip's cells of
that channel summed (`M_cell`), `district` and `rep` the first row of that channel that places
the zip, and a zip no slot serves reads with an empty district, the way an unplaced zip does
everywhere else.  A zip with no district and no mass in the channel is not part of that
channel's map at all.  `params.instance` is the channel's own pure projection, for the Reps tab.

The step is written as `clip`, the kind the Map tab treats as the result; nothing is re-solved
here.  `splits.json` carries what the Map tab reads, aggregated over the bundles drawn on that
channel's map, with `certified_splits` false: the labels come from level 2's power-diagram cut,
which proves nothing about the split count.  Polygons are built by `tools/geom_export.py` as a
subprocess per channel, all launched at once.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app import config, store                                               # noqa: E402
from td import geo, ziptable                                                # noqa: E402
import plan_realise                                                         # noqa: E402
import run_draw                                                             # noqa: E402

# the file's own channels, and the bundle whose projection is that channel alone
CHANNELS = ("national", "wh", "fi")
PURE_BUNDLE = {"national": "N", "wh": "WH", "fi": "FI"}


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="a finished plan run, already realised")
    ap.add_argument("--name", required=True, help="scenario name, slugified for the store")
    ap.add_argument("--app-results", default=str(config.APP_RESULTS),
                    help="the app's run store (default: the hub's)")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--channels", default=None,
                    help=f"comma-separated subset of {', '.join(CHANNELS)}")
    return ap


def channel_cells(path: str) -> tuple[dict, int]:
    """`{channel: {zip: {state, M, district, rep, bundle}}}` from `assignment.csv`, and the
    number of zips whose cells of one channel landed in two different districts.

    A channel's cells of one zip (national is carried by `N_WH` and `N_FI` together) normally
    agree, or one of them is unserved; the first row that places the zip wins, and a genuine
    disagreement is counted and reported rather than silently halved.  The `other`
    pseudo-district is not a district: it reads as an empty label, which is what `ziptable`
    writes for a zip no district holds and what `render` and the app both skip.
    """
    out: dict[str, dict] = {c: {} for c in CHANNELS}
    clashes = 0
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            cells = out.setdefault(row["file_channel"], {})
            cell = cells.setdefault(row["zip"], dict(state=row["state"], M=0.0, district="",
                                                     rep="", bundle=""))
            cell["M"] += float(row["M_cell"] or 0.0)
            name = "" if row["district"] == plan_realise.OTHER else row["district"]
            if not name:
                continue
            if not cell["district"]:
                cell["district"], cell["rep"], cell["bundle"] = name, row["wholesaler"], row["bundle"]
            elif cell["district"] != name:
                clashes += 1
    return out, clashes


def channel_rows(cells: dict, xy: dict) -> list[dict]:
    """The channel's zip table: every zip it places or carries mass for, sorted by zip. A zip
    absent from `xy` keeps its row with an empty `x`/`y`, exactly as `ziptable.build` does."""
    rows = []
    for z in channel_zips(cells):
        cell = cells[z]
        p = xy.get(z)
        rows.append(dict(zip=z, state=cell["state"],
                         x=None if p is None else float(p[0]),
                         y=None if p is None else float(p[1]),
                         opportunity=cell["M"], district=cell["district"], rep=cell["rep"]))
    rows.sort(key=lambda r: r["zip"])
    return rows


def channel_zips(cells: dict) -> list[str]:
    """The zips that belong to a channel's map: placed, or carrying mass in that channel."""
    return [z for z, cell in cells.items() if cell["district"] or cell["M"] > 0.0]


def stage2_value(plan: dict, staffing: dict, bundle: str) -> float:
    """The bundle's share of the plan's stage-2 value: its used slots' gains, summed."""
    gains = staffing.get("gains") or {}
    idx = [i for i, _ in plan_realise.used_by_bundle(plan).get(bundle, ())]
    return float(sum(float(gains.get(str(i), 0.0)) for i in idx))


def launch_geom(python: str, table: str, run: str, geo_cache: str) -> subprocess.Popen:
    """`tools/geom_export.py` on one table, detached enough to run three at once."""
    argv = [python, os.path.join(HERE, "geom_export.py"), "--table", table, "--out", run,
            "--geo-cache", geo_cache]
    return subprocess.Popen(argv, cwd=ROOT)


def _main(args) -> int:
    run_dir = os.path.abspath(args.run_dir)
    root = os.path.abspath(args.app_results)
    plan, staffing, params = plan_realise._load_run(run_dir)
    with open(os.path.join(run_dir, "realise.json"), encoding="utf-8") as fh:
        realise = json.load(fh)
    by_channel, clashes = channel_cells(os.path.join(run_dir, "assignment.csv"))
    if clashes:
        print(f"warning: {clashes} zips place two channels' cells in different districts; "
              f"the first row wins", flush=True)

    channels = list(CHANNELS)
    if args.channels:
        want = [c.strip() for c in args.channels.split(",") if c.strip()]
        unknown = [c for c in want if c not in CHANNELS]
        if unknown:
            raise SystemExit(f"--channels names {unknown}, not among {list(CHANNELS)}")
        channels = want

    slug = store.slugify(args.name)
    delta = float(params.get("band_hi", 1.0)) - 1.0
    theta, lam = params.get("theta"), params.get("lam")
    filler = params.get("filler_capture")

    pending = []
    for channel in channels:
        cells = by_channel.get(channel, {})
        xy, missing = run_draw.coordinates(channel_zips(cells), args.geo_cache)
        rows = channel_rows(cells, xy)

        districts = {r["district"] for r in rows if r["district"]}
        bundles = sorted({c["bundle"] for c in cells.values() if c["district"] and c["bundle"]})
        recs = [realise["bundles"][b] for b in bundles if b in realise["bundles"]]
        k = len(districts)
        proj = os.path.join(run_dir, "projections", PURE_BUNDLE[channel],
                            "instance_descaled.json.gz")

        member = store.member_name(slug, k, delta, channel)
        run = store.new_run_dir(root, "clip", member)
        table = ziptable.write(os.path.join(run, "draw.csv"), rows)
        split_states = sorted({s for rec in recs for s in rec["split_states"]})
        statuses = sorted({rec["status"] for rec in recs})
        with open(os.path.join(run, "splits.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(delta=delta, status=", ".join(statuses) or "no district",
                           splits=len(split_states), split_states=split_states,
                           certified_splits=False,
                           n_fractional=sum(rec["n_fractional"] for rec in recs),
                           residual_zips=sum(rec["residual_zips"] for rec in recs),
                           channel=channel, bundles=bundles,
                           stage2_value=sum(stage2_value(plan, staffing, b) for b in bundles),
                           stage2_theta=theta, stage2_lam=lam, stage2_filler=filler),
                      fh, indent=2)
            fh.write("\n")
        # before geom_export runs: `Timings.write` only steps aside to `timings.geom.json` when a
        # `timings.json` is already there, so a copy made afterwards would overwrite geom's own
        shutil.copyfile(os.path.join(run_dir, "timings.json"), os.path.join(run, "timings.json"))

        store.write_step(
            run, kind="clip", parent=None,
            params=dict(k=k, delta=delta, instance=proj, channel=channel, bundles=bundles,
                        plan_run=run_dir, theta=theta, lam=lam, filler_capture=filler,
                        scenario_name=args.name, geo_cache=str(args.geo_cache)),
            argv=list(sys.argv),
            outputs={"table": "draw.csv", "metrics": "splits.json", "geom": "geom.json",
                     "timings": "timings.json"},
            scenario=slug, member=member)
        store.write_view(run, root, name=f"{store.channel_label(channel)} ({k} districts)",
                         default_for=member)

        n_labelled = sum(1 for r in rows if r["district"])
        print(f"{channel}: k={k} bundles={bundles} member={member} zips={len(rows)} "
              f"labelled={n_labelled} no gazetteer point={len(missing)} -> {run}", flush=True)
        pending.append((channel, run, launch_geom(sys.executable, table, str(run),
                                                  str(args.geo_cache))))

    for channel, run, proc in pending:
        if proc.wait() != 0:
            print(f"warning: {channel}: geom_export failed; the map draws as points", flush=True)

    print(f"scenario {slug}", flush=True)
    for member, _ in store.members(root, slug):
        print(f"  member {member}", flush=True)
    return 0


def main(argv=None) -> int:
    return _main(build_argparser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
