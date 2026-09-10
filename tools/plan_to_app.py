"""plan_to_app.py: a finished `tools/full_plan.py` + `tools/plan_realise.py` run -> app runs.

    .venv/bin/python3 tools/plan_to_app.py battery/results/full_problem/v3_seq_warm \\
        --name v3-seq-warm --geo-cache /Users/ntlee/projects/td/data/geo

One run directory per used bundle in the app's store (`battery/results/app`), so the plan's
maps open in the Streamlit app beside every other map.  Each bundle becomes one scenario
member: the projection's zips, coordinates from the gazetteer, `opportunity` the projection's
own `M`, `district` and `rep` read off `assignment.csv`'s rows for that bundle (the bundle's
channels agree by product form, so the first row per zip speaks for all of them), and a zip no
slot serves reads with an empty district, the way an unplaced zip does everywhere else.

The step is written as `clip`, the kind the Map tab treats as the result; nothing is re-solved
here.  `splits.json` carries what the Map tab reads, with `certified_splits` false: the labels
come from level 2's power-diagram cut, which proves nothing about the split count.  Polygons are
built by `tools/geom_export.py` as a subprocess per bundle, all launched at once.
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
from td import instance as descaled                                         # noqa: E402
import plan_realise                                                         # noqa: E402
import run_draw                                                             # noqa: E402


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="a finished plan run, already realised")
    ap.add_argument("--name", required=True, help="scenario name, slugified for the store")
    ap.add_argument("--app-results", default=str(config.APP_RESULTS),
                    help="the app's run store (default: the hub's)")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--bundles", default=None, help="comma-separated subset of the used bundles")
    return ap


def cells_by_bundle(path: str) -> dict:
    """`{bundle: {zip: (district, rep)}}` from `assignment.csv`, first row per (bundle, zip).

    The `other` pseudo-district is not a district: it reads as an empty label, which is what
    `ziptable` writes for a zip no district holds and what `render` and the app both skip.
    """
    out: dict[str, dict] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            cells = out.setdefault(row["bundle"], {})
            if row["zip"] in cells:
                continue
            name = "" if row["district"] == plan_realise.OTHER else row["district"]
            cells[row["zip"]] = (name, row["wholesaler"])
    return out


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
    cells = cells_by_bundle(os.path.join(run_dir, "assignment.csv"))

    bundles = sorted(realise["bundles"])
    if args.bundles:
        want = [b.strip() for b in args.bundles.split(",") if b.strip()]
        unknown = [b for b in want if b not in bundles]
        if unknown:
            raise SystemExit(f"--bundles names {unknown}, not among the run's {bundles}")
        bundles = want

    slug = store.slugify(args.name)
    delta = float(params.get("band_hi", 1.0)) - 1.0
    theta, lam = params.get("theta"), params.get("lam")
    filler = params.get("filler_capture")

    pending = []
    for bundle in bundles:
        rec = realise["bundles"][bundle]
        proj = os.path.join(run_dir, "projections", bundle, "instance_descaled.json.gz")
        d = descaled.load_descaled(proj)
        zips = list(d.G)
        xy, missing = run_draw.coordinates(zips, args.geo_cache)
        labels = {z: cells.get(bundle, {}).get(z, ("", ""))[0] for z in zips}
        reps = {z: cells.get(bundle, {}).get(z, ("", ""))[1] for z in zips}
        rows = ziptable.build(d, xy, labels, reps)

        k = int(rec["k"])
        member = store.member_name(slug, k, delta)
        run = store.new_run_dir(root, "clip", member)
        table = ziptable.write(os.path.join(run, "draw.csv"), rows)
        with open(os.path.join(run, "splits.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(delta=delta, status=rec["status"],
                           splits=len(rec["split_states"]), split_states=rec["split_states"],
                           certified_splits=False, n_fractional=rec["n_fractional"],
                           residual_zips=rec["residual_zips"], bundle=bundle,
                           stage2_value=stage2_value(plan, staffing, bundle),
                           stage2_theta=theta, stage2_lam=lam, stage2_filler=filler),
                      fh, indent=2)
            fh.write("\n")
        # before geom_export runs: `Timings.write` only steps aside to `timings.geom.json` when a
        # `timings.json` is already there, so a copy made afterwards would overwrite geom's own
        shutil.copyfile(os.path.join(run_dir, "timings.json"), os.path.join(run, "timings.json"))

        store.write_step(
            run, kind="clip", parent=None,
            params=dict(k=k, delta=delta, instance=proj, bundle=bundle, plan_run=run_dir,
                        theta=theta, lam=lam, filler_capture=filler, scenario_name=args.name,
                        geo_cache=str(args.geo_cache)),
            argv=list(sys.argv),
            outputs={"table": "draw.csv", "metrics": "splits.json", "geom": "geom.json",
                     "timings": "timings.json"},
            scenario=slug, member=member)
        store.write_view(run, root, name=f"{bundle} ({k} districts)", default_for=member)

        n_labelled = sum(1 for r in rows if r["district"])
        print(f"{bundle}: k={k} member={member} zips={len(rows)} labelled={n_labelled} "
              f"no gazetteer point={len(missing)} -> {run}", flush=True)
        pending.append((bundle, run, launch_geom(sys.executable, table, str(run),
                                                 str(args.geo_cache))))

    for bundle, run, proc in pending:
        if proc.wait() != 0:
            print(f"warning: {bundle}: geom_export failed; the map draws as points", flush=True)

    print(f"scenario {slug}", flush=True)
    for member, _ in store.members(root, slug):
        print(f"  member {member}", flush=True)
    return 0


def main(argv=None) -> int:
    return _main(build_argparser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
