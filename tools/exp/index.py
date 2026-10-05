"""index.py -- rebuild `runs/exp/index.jsonl` from the run manifests (#92).

    "$TD_PY" tools/exp/index.py [--root DIR]

One row per `<root>/<lane>/<run_id>/manifest.json` (`tools/exp/sweep.py`), in run-id order: the
identity, status and stop reason, provenance, flattened parameters, audit verdict, each channel's
solver status and the metrics.  A done run is rescored with the looks scorer when
`tools/looks/score.py` is present (`sweep.metrics`); the manifest itself is left as the run wrote it.
The file is replaced whole, so a reader never sees half of it.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("exp_sweep", os.path.join(HERE, "sweep.py"))
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)

INDEX = "index.jsonl"


def row(m: dict) -> dict:
    """The index row of manifest `m`, rescored when the looks scorer is present."""
    metrics, error = m.get("metrics") or {}, m.get("scorer_error")
    if m["status"] == "done" and os.path.exists(sweep.LOOKS_SCORER):
        metrics, error = sweep.metrics(m["folder"])
    prov = m.get("provenance", {})
    return {
        "run_id": m["run_id"], "lane": m["lane"], "formulation": m["formulation"],
        "folder": m["folder"], "status": m["status"], "stop_reason": m.get("stop_reason"),
        **{k: prov.get(k) for k in ("commit", "dirty", "diff_sha256", "host", "instance",
                                    "instance_sha256", "queued_at")},
        "started_at": m.get("started_at"), "finished_at": m.get("finished_at"),
        "seconds": m.get("seconds"), "params": m.get("params", {}), "audit": m.get("audit"),
        "solver": {c: s.get("status") for c, s in (m.get("solver") or {}).items()},
        "metrics": metrics, "scorer_error": error}


def rebuild(root: str) -> list:
    """Write `<root>/index.jsonl` from every manifest under `root`; its rows."""
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "*", "*", sweep.MANIFEST))):
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
        m["folder"] = os.path.dirname(path)         # where the run is now
        rows.append(row(m))
    rows.sort(key=lambda r: r["run_id"])
    out = os.path.join(root, INDEX)
    os.makedirs(root, exist_ok=True)
    with open(out + ".tmp", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(out + ".tmp", out)
    return rows


def read(root: str) -> list:
    with open(os.path.join(root, INDEX), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools/exp/index.py", description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="runs root (default $TD_REPO/runs/exp)")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root or sweep.default_root())
    rows = rebuild(root)
    lanes = sorted({r["lane"] for r in rows})
    print(f"{len(rows)} runs in {len(lanes)} lanes ({', '.join(lanes)}): {os.path.join(root, INDEX)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
