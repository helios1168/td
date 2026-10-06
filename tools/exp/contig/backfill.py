"""backfill.py -- manifests for map runs drawn before they were tracked (#120, mandate T1).

    "$TD_PY" tools/exp/contig/backfill.py [--lane-dir DIR] [--lane NAME] [--dry-run] [FOLDER ...]

Every folder under the lane directory (default `$TD_REPO/runs/exp/contig`, lane `contig`) that holds
a `ledger.csv` and no `manifest.json` gets one in `tools/exp/sweep.py`'s format, written after the
fact from what the folder and its neighbours give: `run.json` (scenario path, instance, audit
verdict, diagnostic flag), `contig.json` (the arm, the repair's settings, `parent_run` from
`repair_of`, the plan file), the sibling log `<folder>.log` and the launch scripts (`*.sh`) beside
the folder or at the lane's top.  The run id is the folder's path under the lane directory, since
names repeat across `old*/`.  Explicit FOLDERs (with `--lane-dir` their common root, e.g.
`runs/sweep` with `--lane sweep` for the 2026-10-01/02 sweep runs on the shortlist) are
backfilled the same way.  A folder that already has a manifest is never touched.

Provenance is marked `"backfilled": true`: the commit, dirty flag, command line and start time are
unknown (null), the host is this machine, and the scenario's and instance's sha256 are of the
files at backfill time (`backfilled_at`), not proven to be the bytes the run read.  `finished_at`
is `run.json`'s modification time.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import importlib.util
import json
import os
import platform
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
_spec = importlib.util.spec_from_file_location("exp_sweep", os.path.join(ROOT, "tools", "exp", "sweep.py"))
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)

CONTIG_PARAMS = ("arm", "fixed_targets", "sequential", "internal_delta", "plan_seconds")


def td_repo() -> str:
    return os.environ.get("TD_REPO", ROOT)


def _json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve(path: str | None) -> str | None:
    """`path` made absolute against `$TD_REPO` (a run records it relative to where it ran)."""
    if not path:
        return None
    return path if os.path.isabs(path) else os.path.join(td_repo(), path)


def _iso(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(timespec="seconds")


def pending(lane_dir: str) -> list:
    """Every folder under `lane_dir` with a `ledger.csv` and no `manifest.json`, sorted."""
    return sorted(d for d, _, fs in os.walk(lane_dir)
                  if "ledger.csv" in fs and sweep.MANIFEST not in fs)


def launch_scripts(folder: str, lane_dir: str) -> list:
    """The `*.sh` files beside `folder`, or at the lane's top when there are none beside it."""
    near = sorted(glob.glob(os.path.join(os.path.dirname(folder), "*.sh")))
    return near or sorted(glob.glob(os.path.join(lane_dir, "*.sh")))


def manifest(folder: str, lane_dir: str, lane: str, shas: dict) -> dict:
    """The backfilled manifest of `folder` (module doc); `shas` caches file sha256s by path."""
    def sha(path):
        if path is None or not os.path.exists(path):
            return None
        if path not in shas:
            shas[path] = sweep.sha256_file(path)
        return shas[path]
    folder = os.path.abspath(folder)
    run = _json(os.path.join(folder, "run.json"))
    contig = _json(os.path.join(folder, "contig.json"))
    repair = contig.get("repair") or {}
    formulation = "contig_repair" if repair else "contig" if contig else "support"
    params = {k: contig[k] for k in CONTIG_PARAMS if k in contig}
    params.update(sweep.flatten({"repair": repair}) if repair else {})
    spec = _resolve(run.get("spec"))
    inst = _resolve(run.get("source"))
    logs = sorted(glob.glob(folder + ".log") + glob.glob(folder + ".*.log"))
    m = {"run_id": os.path.relpath(folder, os.path.abspath(lane_dir)), "lane": lane,
         "formulation": formulation, "folder": folder, "status": "done", "stop_reason": None,
         "params": params, "command": None,
         "scenario": {"path": spec, "sha256": sha(spec)} if spec else None,
         "extract": inst, "plans_file": repair.get("plans_file") or contig.get("plans_file"),
         "parent_run": contig.get("repair_of"),
         "provenance": {"commit": None, "dirty": None, "diff_sha256": None,
                        "host": platform.node(), "instance": inst, "instance_sha256": sha(inst),
                        "queued_at": None, "backfilled": True, "backfilled_at": sweep.now(),
                        "logs": logs, "launch_scripts": launch_scripts(folder, lane_dir)},
         "started_at": None, "audit": run.get("verdict")}
    if os.path.exists(os.path.join(folder, "run.json")):
        m["finished_at"] = _iso(os.path.getmtime(os.path.join(folder, "run.json")))
    if run.get("diagnostic"):
        m.update(diagnostic=True, diagnostic_band=run.get("diagnostic_band"),
                 diagnostic_label=run.get("diagnostic_label", ""))
    return m


def backfill(lane_dir: str, lane: str, folders=None, dry_run: bool = False) -> list:
    """Write a manifest into each folder of `folders` (default `pending(lane_dir)`) that has a
    ledger and no manifest; the manifests written (or that would be, with `dry_run`)."""
    shas, out = {}, []
    for folder in folders if folders is not None else pending(lane_dir):
        if (not os.path.exists(os.path.join(folder, "ledger.csv"))
                or os.path.exists(os.path.join(folder, sweep.MANIFEST))):
            continue
        m = manifest(folder, lane_dir, lane, shas)
        if not dry_run:
            sweep.write_manifest(folder, m)
        out.append(m)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools/exp/contig/backfill.py", description=__doc__.splitlines()[0])
    ap.add_argument("folders", nargs="*", help="these folders only (default: every pending one)")
    ap.add_argument("--lane-dir", default=None, help="default $TD_REPO/runs/exp/contig")
    ap.add_argument("--lane", default="contig")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    lane_dir = os.path.abspath(a.lane_dir or os.path.join(sweep.default_root(), "contig"))
    done = backfill(lane_dir, a.lane, [os.path.abspath(f) for f in a.folders] or None, a.dry_run)
    for m in done:
        print(f"{'would write' if a.dry_run else 'wrote'} {m['run_id']} ({m['formulation']}, "
              f"parent {m['parent_run'] and os.path.relpath(m['parent_run'], lane_dir)})")
    print(f"{len(done)} manifests {'to write' if a.dry_run else 'written'} under {lane_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
