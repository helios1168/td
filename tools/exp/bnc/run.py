"""run.py -- one arm on one instance per process, then the gate on the merged map (#142, A1/A2).

    "$TD_PY" -u tools/exp/bnc/run.py one <instance> <arm> --time-limit 7200 --threads 4
    "$TD_PY" -u tools/exp/bnc/run.py all --time-limit 7200 --threads 4 [--insts ...] [--arms a b c d] [--jobs 1]

`one` writes `<out>/<instance>/<arm>/{result.json, ledger.csv, log}`, `out` being
`$TD_REPO/runs/exp/bnc_2026-10-15` by default:

- `result.json`: the arm's result (`arms.py`: status, objective, bound, gap, nodes, seconds, rounds,
  cuts, note), the settings (time limit, threads, instance sha256) and, when the arm returned a
  drawing, `objective_check` (the drawing's cost on the instance's own MILP, `Inst.evaluate`) and
  `gate`;
- `ledger.csv`: the drawing as the ledger rows of the group's ZCTAs (every fine-channel row of the
  channel), in the full ledger's columns, `district` the district id of the source map;
- `merged/`: that drawing merged into the source map's full ledger (`districts.csv` and `run.json`
  beside it), the folder the gate reads;
- `log`: the arm's log.

The gate is `tools/mandates/check.py`'s `m1` on `merged/` (the full 2025 polygon graph with the
connectors, relays and neck rule as the gate has them) and `tools/looks/score.py`'s `dollar_gate`
(the whole-dollar windows).  M1 is district-local, so the verdict that belongs to the arm is that
of the districts of the group: `gate.m1` is `pass` when none of them has a detached piece or a
neck, `fail` otherwise (a failure is reported as one, never as a timing); `gate.map_m1` is the
whole merged map's status, which also carries the source map's other districts and is context
only.  `gate.in_window` says whether every district of the group is inside its dollar window.

`all` runs each (instance, arm) as its own process (`one`), `--jobs` at a time (default 1, so that
the times are comparable), and then writes `REPORT.md` (`report.py`).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import capture  # noqa: E402
import inst_io  # noqa: E402

export = capture.sibling("bnc_export", "export.py")

ROOT = export.ROOT
TD_REPO = export.TD_REPO
OUT = os.path.join(TD_REPO, "runs", "exp", "bnc_2026-10-15")
INSTANCES = ("FI_PA", "FI_FL", "FI_NY", "WIFI_MD")


def _module(name: str, rel: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def mandates():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    return _module("mandates_check", os.path.join("tools", "mandates", "check.py"))


# ------------------------------------------------------------------------------ ledger and merge
def write_rows(path: str, fields: list, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def merge(inst, owner: dict, base: str, cfg: dict, folder: str) -> dict:
    """Write `ledger.csv` (the group's rows) and `merged/` in `folder`; {"districts": {copy: id}, ...}
    with what the merge found in the source map (`consistency`)."""
    channel = cfg["channel"]
    districts = export.read_csv(os.path.join(base, "districts.csv"))
    ident = {r["copy"]: r["district"] for r in districts if r["channel"] == channel}
    name = {r["district"]: r["district_name"] for r in districts if r["channel"] == channel}
    missing = [j for j in inst.js if j not in ident]
    if missing:
        raise RuntimeError(f"districts of the group not in {base}/districts.csv: {missing}")
    by_id = {v: k for k, v in ident.items()}
    zs = set(inst.zs)
    with open(os.path.join(base, "ledger.csv"), newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)
    # does the source map agree with the instance outside the group?  bodies are fixed in the model
    body = {z: j for j, bs in inst.doc["draw"]["bodies"].items() for b in bs for z in b}
    have = {r["zip_code"]: by_id.get(r["district"]) for r in rows if r["model_channel"] == channel and r["district"]}
    bad = sorted(z for z, j in body.items() if have.get(z) != j)
    replaced, group_rows = 0, []
    for r in rows:
        if r["model_channel"] == channel and r["zip_code"] in zs:
            r["district"] = ident[owner[r["zip_code"]]]
            r["district_name"] = name[r["district"]]
            group_rows.append(r)
            replaced += 1
    merged = os.path.join(folder, "merged")
    os.makedirs(merged, exist_ok=True)
    write_rows(os.path.join(folder, "ledger.csv"), fields, group_rows)
    write_rows(os.path.join(merged, "ledger.csv"), fields, rows)
    shutil.copy(os.path.join(base, "districts.csv"), merged)
    shutil.copy(os.path.join(base, "run.json"), merged)
    return {"ident": ident, "replaced_rows": replaced, "group_zctas": len(zs),
            "consistency": {"body_zctas": len(body), "body_zctas_not_owned_as_modelled": len(bad),
                            "examples": bad[:5]}}


def gate(inst, owner: dict, cfg: dict, folder: str, log=print) -> dict:
    """M1 and the dollar window of the merged map (module docstring)."""
    check = mandates()
    info = merge(inst, owner, cfg["gate_base"], cfg, folder)
    merged = os.path.join(folder, "merged")
    t0 = time.time()
    g = check.m1(merged)
    log(f"  gate: M1 of the merged map {g['status']} in {time.time() - t0:.0f}s ({g['summary']})")
    mine = {f"{cfg['channel']}/{d}" for d in (info["ident"][j] for j in inst.js)}
    items = [i for i in g["check"].items if i.split(":", 1)[0] in mine
             and "mass neck" not in i and (check.score.NECK.search(i) or check.score.PIECE.search(i))]
    sc = check.score
    ledger = export.read_csv(os.path.join(merged, "ledger.csv"))
    districts = export.read_csv(os.path.join(merged, "districts.csv"))
    rows = sc.dollar_gate(ledger, districts, sc.rates_of(cfg["extract"]))
    ours = [r for r in rows if r["channel"] == cfg["channel"] and f"{r['channel']}/{r['district']}" in mine]
    others = [r for r in rows if r["channel"] == cfg["channel"] and f"{r['channel']}/{r['district']}" not in mine
              and not r["ok"]]
    return {
        "m1": "fail" if items else "pass", "m1_items": items,
        "map_m1": g["status"], "map_summary": g["summary"],
        "in_window": all(r["ok"] for r in ours),
        "districts": [{"copy": j, "id": info["ident"][j],
                       "usd_m": round(next(r["usd"] for r in ours if r["district"] == info["ident"][j]) / 1e6, 3),
                       "lo_m": next(r["lo"] for r in ours if r["district"] == info["ident"][j]) / 1e6,
                       "hi_m": next(r["hi"] for r in ours if r["district"] == info["ident"][j]) / 1e6,
                       "ok": next(r["ok"] for r in ours if r["district"] == info["ident"][j])}
                      for j in inst.js],
        "other_districts_outside_window": [r["district"] for r in others],
        "merge": {k: v for k, v in info.items() if k != "ident"}, "seconds": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------ one process
def one(name: str, arm: str, a) -> int:
    arms = capture.sibling("bnc_arms", "arms.py")
    cfg = export.instances(a.m2_dir)[name]
    folder = os.path.join(a.out, name, arm)
    os.makedirs(folder, exist_ok=True)
    logf = open(os.path.join(folder, "log"), "w", encoding="utf-8")

    def log(*msg):
        line = " ".join(str(x) for x in msg)
        print(line, flush=True)
        logf.write(f"{time.strftime('%H:%M:%S')} {line}\n")
        logf.flush()
    path = os.path.join(a.instances, f"{name}.json.gz")
    inst = inst_io.load(path)
    kw = {"frac_root": a.frac_root} if arm == "c" else ({"flow": not a.no_flow} if arm == "a" else {})
    log(f"{name} arm {arm}: time limit {a.time_limit:g}s, threads {a.threads}, "
        f"{inst.n} columns, {inst.n_rows} rows, {len(inst.zs)} ZCTAs, {len(inst.js)} districts {kw}")
    result = arms.solve(arm, inst, a.time_limit, a.threads, log, **kw)
    owner = result.pop("owner")
    result.update(instance=name, instance_sha256=export.sha256(path), time_limit=a.time_limit,
                  threads=a.threads, settings=kw, finished=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  code_commit=export.commit())
    log(f"{name} arm {arm}: {result['status']} objective {result['objective']} bound {result['bound']} "
        f"gap {result['gap']} nodes {result['nodes']} in {result['seconds']:.1f}s; {result['note']}")
    if owner is not None:
        obj, why = inst.evaluate(owner)
        result["objective_check"] = {"objective": obj, "problem": why}
        log(f"  the drawing on the instance's MILP: objective {obj} {why}")
        if not a.no_gate:
            result["gate"] = gate(inst, owner, cfg, folder, log)
            g = result["gate"]
            log(f"  gate: M1 of the group's districts {g['m1']} {g['m1_items'][:2]}, "
                f"in window {g['in_window']}")
    with open(os.path.join(folder, "result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    logf.close()
    return 0


def all_runs(a) -> int:
    report = capture.sibling("bnc_report", "report.py")
    jobs, running, todo = max(1, a.jobs), [], [(i, r) for i in a.insts for r in a.arms]
    py = sys.executable
    while todo or running:
        while todo and len(running) < jobs:
            i, r = todo.pop(0)
            cmd = [py, "-u", os.path.abspath(__file__), "one", i, r, "--time-limit", str(a.time_limit),
                   "--threads", str(a.threads), "--out", a.out, "--instances", a.instances,
                   "--m2-dir", a.m2_dir] + (["--frac-root"] if a.frac_root else []) \
                + (["--no-flow"] if a.no_flow else []) + (["--no-gate"] if a.no_gate else [])
            os.makedirs(os.path.join(a.out, i, r), exist_ok=True)
            print("start", " ".join(cmd), flush=True)
            running.append((i, r, subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=open(
                os.path.join(a.out, i, r, "stderr"), "w"))))
        time.sleep(2)
        for item in list(running):
            if item[2].poll() is not None:
                print(f"done {item[0]} {item[1]} rc {item[2].returncode}", flush=True)
                running.remove(item)
    report.write(a.out, a.instances)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("one", "all"):
        p = sub.add_parser(cmd)
        if cmd == "one":
            p.add_argument("instance", choices=INSTANCES)
            p.add_argument("arm", choices=("a", "b", "c", "d"))
        else:
            p.add_argument("--insts", nargs="*", default=list(INSTANCES))
            p.add_argument("--arms", nargs="*", default=["a", "b", "c", "d"])
            p.add_argument("--jobs", type=int, default=1)
        p.add_argument("--time-limit", type=float, default=7200.0)
        p.add_argument("--threads", type=int, default=1)
        p.add_argument("--out", default=OUT)
        p.add_argument("--instances", default=None, help="default <out>/instances")
        p.add_argument("--m2-dir", default=export.M2_DIR)
        p.add_argument("--frac-root", action="store_true", help="arm c: fractional separation at the root")
        p.add_argument("--no-flow", action="store_true", help="arm a without the flow rows")
        p.add_argument("--no-gate", action="store_true")
    a = ap.parse_args(argv)
    a.instances = a.instances or os.path.join(a.out, "instances")
    return one(a.instance, a.arm, a) if a.cmd == "one" else all_runs(a)


if __name__ == "__main__":
    sys.exit(main())
