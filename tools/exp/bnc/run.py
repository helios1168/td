"""run.py -- one arm on one instance per process, then the gate on the merged map (#142, A1/A2).

    "$TD_PY" -u tools/exp/bnc/run.py one <instance> <arm> --time-limit 7200 --threads 1
    "$TD_PY" -u tools/exp/bnc/run.py all --time-limit 7200 --threads 1 [--insts ...] [--arms a b c d] [--jobs 1]

`one` writes `<out>/<instance>/<arm>/{result.json, ledger.csv, log}`, `out` being
`$TD_REPO/runs/exp/bnc_2026-10-15` by default:

- `result.json`: the arm's result (`arms.py`: status, objective, bound, gap, nodes, seconds, rounds,
  cuts, note), the settings (time limit, threads, the instance's path and sha256 and the code commit and dirty flag, all taken before the solve) and, when the arm returned a
  drawing, `objective_check` (the drawing's cost on the instance's own MILP, `Inst.evaluate`) and
  `gate`;
- `ledger.csv`: the drawing as the ledger rows of the group's ZCTAs (every fine-channel row of the
  channel), in the full ledger's columns, `district` the district id of the source map;
- `merged/`: that drawing merged into the source map's full ledger (`districts.csv` and `run.json`
  beside it), the folder the gate reads;
- `log`: the arm's log.

The gate is `tools/mandates/check.py`'s `m1` on `merged/` (the full 2025 polygon graph with the
connectors, relays and neck rule as the gate has them) and `tools/looks/score.py`'s `dollar_gate`
(the whole-dollar windows).  The M1 verdict of a drawing (`gate.m1`) is the real gate's verdict on the
merged map: `pass`, `fail`, or `ungated` when the gate could not verify the map.  Only a failure proven
to belong to a district outside the group that is already in the gate's items on the unmodified source
map (the same item text) is left out; it is listed in `gate.m1_excluded`.  Every other item counts:
the group's districts, changed or new items of other districts, and all coverage, ownership, routing
and fine-channel items.  `gate.map_m1` is the merged map's own status.  `gate.in_window` says whether
every district of the group is inside its dollar window.

The gate always runs on a returned drawing (no switch turns it off).  The arm folder and `merged/`
each get a `manifest.json` (mandate T1, `contig/run.py`'s `write_manifest`): `running` at the start,
`done` at the end, `failed` when the run raised.

`all` runs each (instance, arm) as its own process (`one`), `--jobs` at a time (default 1, so that
the times are comparable), and then writes `REPORT.md` (`report.py`).  A child that exits non-zero or
leaves no `result.json` makes `all` exit 1; a `result.json` of an earlier run is moved to
`result.previous.json` before its child starts (`one` does the same for a direct rerun), so a failed
rerun never reports old measurements.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
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
END_GRACE = 10.0        # seconds a campaign child's group gets to stop on SIGINT before SIGKILL (`end_group`)
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


def m1_verdict(check, mine: set, base_items=None) -> dict:
    """The M1 verdict of a drawing: the gate's own verdict on the merged map (`check`, an
    `audit.Check`), minus only the failures proven to lie outside the group.

    A failure is excluded when it is a detached-piece or neck item of a district not in `mine`
    ("channel/district" ids) AND the same item (identical text) is in `base_items`, the gate's items on the unmodified source map (a callable, called only when it is needed).  Every other failure
    stays: a district of the group, a changed or new item of another district, and every coverage,
    ownership, routing or fine-channel item.  A map the gate could not verify, or whose necks it
    could not measure, is `ungated`, never `pass`.  Mass necks are listed beside M1 by the gate and are not failures.
    {"m1": "pass" | "fail" | "ungated", "m1_items": the failures that count, "m1_excluded": the
    items left out and why they could be}.  An unresolved neck search (`td.audit.neck_item`) is never
    left out: the gate could not show that neck is not one."""
    if check.status == "pass":
        return {"m1": "pass", "m1_items": [], "m1_excluded": []}
    if check.status != "fail":
        return {"m1": "ungated", "m1_items": [f"gate status {check.status}: {check.summary}"],
                "m1_excluded": []}
    sc = mandates().score
    failing = [i for i in check.items if mandates().audit.MASS_NECK not in i]
    outside = [i for i in failing if (sc.NECK.search(i) or sc.PIECE.search(i))
               and i.split(":", 1)[0] not in mine]
    base = set(base_items()) if outside and base_items is not None else set()
    excluded = [i for i in outside if i in base and " unresolved (" not in i]   # an unverified neck never passes
    kept = [i for i in failing if i not in excluded]
    if not kept and not excluded:
        kept = [f"gate status fail without an item: {check.summary}"]
    if not kept and check.counts.get("necks") is None:      # necks never measured: no post-exclusion pass
        return {"m1": "ungated", "m1_excluded": excluded,
                "m1_items": [f"necks not verified (no border lengths): {check.summary}"]}
    return {"m1": "fail" if kept else "pass", "m1_items": kept, "m1_excluded": excluded}


def gate(inst, owner: dict, cfg: dict, folder: str, log=print) -> dict:
    """M1 and the dollar window of the merged map (module docstring)."""
    check = mandates()
    info = merge(inst, owner, cfg["gate_base"], cfg, folder)
    merged = os.path.join(folder, "merged")
    t0 = time.time()
    g = check.m1(merged)
    log(f"  gate: M1 of the merged map {g['status']} in {time.time() - t0:.0f}s ({g['summary']})")
    mine = {f"{cfg['channel']}/{d}" for d in (info["ident"][j] for j in inst.js)}

    def base_items():
        t1 = time.time()
        b = check.m1(cfg["gate_base"])
        log(f"  gate: M1 of the unmodified source map {b['status']} in {time.time() - t1:.0f}s ({b['summary']})")
        return b["check"].items
    verdict = m1_verdict(g["check"], mine, base_items)
    sc = check.score
    ledger = export.read_csv(os.path.join(merged, "ledger.csv"))
    districts = export.read_csv(os.path.join(merged, "districts.csv"))
    rows = sc.dollar_gate(ledger, districts, sc.rates_of(cfg["extract"]))
    ours = [r for r in rows if r["channel"] == cfg["channel"] and f"{r['channel']}/{r['district']}" in mine]
    others = [r for r in rows if r["channel"] == cfg["channel"] and f"{r['channel']}/{r['district']}" not in mine
              and not r["ok"]]
    return {
        **verdict,
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
def manifests(folder: str, name: str, arm: str, cfg: dict, a, status: str, **more) -> None:
    """Mandate T1's `manifest.json` in `folder` and, once the gate has made it, in `folder/merged`
    (every folder under runs/exp with a `ledger.csv` needs one); a manifest of an earlier run is
    replaced, not updated, at `running` (and in `merged/`)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    contig = capture._load("contig_run", os.path.join(capture.CONTIG, "run.py"))
    params = {"instance": name, "arm": arm, "time_limit": a.time_limit, "threads": a.threads,
              "frac_root": bool(a.frac_root), "no_flow": bool(a.no_flow)}
    merged = os.path.join(folder, "merged")
    for d in (folder, merged):
        if not os.path.isdir(d):
            continue
        path = os.path.join(d, "manifest.json")
        if os.path.exists(path) and (d == merged or status == "running"):
            os.remove(path)
        contig.write_manifest(d, "bnc", cfg["spec"], cfg["extract"], params, status=status, lane="bnc",
                              **more)


def one(name: str, arm: str, a) -> int:
    cfg = export.instances(a.m2_dir)[name]
    folder = os.path.join(a.out, name, arm)
    os.makedirs(folder, exist_ok=True)
    stale = os.path.join(folder, "result.json")      # a failed attempt must not leave an old result to be reported
    if os.path.exists(stale):
        os.replace(stale, os.path.join(folder, "result.previous.json"))
    manifests(folder, name, arm, cfg, a, "running")
    try:
        rc = _one(name, arm, a, cfg, folder)
    except BaseException as e:
        manifests(folder, name, arm, cfg, a, "failed", stop_reason=f"{type(e).__name__}: {e}")
        raise
    manifests(folder, name, arm, cfg, a, "done")
    return rc


def _one(name: str, arm: str, a, cfg: dict, folder: str) -> int:
    arms = capture.sibling("bnc_arms", "arms.py")
    logf = open(os.path.join(folder, "log"), "w", encoding="utf-8")

    def log(*msg):
        line = " ".join(str(x) for x in msg)
        print(line, flush=True)
        logf.write(f"{time.strftime('%H:%M:%S')} {line}\n")
        logf.flush()
    path = os.path.abspath(os.path.join(a.instances, f"{name}.json.gz"))
    data, digest = inst_io.read(path)        # the bytes solved are the bytes hashed, and the code is noted
    prov = export.provenance()               # before the solve: a file or checkout changed during it is not recorded as the input
    inst = inst_io.loads(data, path)
    kw = {"frac_root": a.frac_root} if arm == "c" else ({"flow": not a.no_flow} if arm == "a" else {})
    log(f"{name} arm {arm}: time limit {a.time_limit:g}s, threads {a.threads}, "
        f"{inst.n} columns, {inst.n_rows} rows, {len(inst.zs)} ZCTAs, {len(inst.js)} districts {kw}")
    result = arms.solve(arm, inst, a.time_limit, a.threads, log, **kw)
    owner = result.pop("owner")
    result.update(instance=name, instance_sha256=digest, instance_path=path, time_limit=a.time_limit,
                  threads=a.threads, settings=kw, finished=time.strftime("%Y-%m-%dT%H:%M:%S"), **prov)
    log(f"{name} arm {arm}: {result['status']} objective {result['objective']} bound {result['bound']} "
        f"gap {result['gap']} nodes {result['nodes']} in {result['seconds']:.1f}s; {result['note']}")
    if owner is not None:
        obj, why = inst.evaluate(owner, a.threads)
        result["objective_check"] = {"objective": obj, "problem": why}
        log(f"  the drawing on the instance's MILP: objective {obj} {why}")
        result["gate"] = gate(inst, owner, cfg, folder, log)
        g = result["gate"]
        log(f"  gate: M1 {g['m1']} {g['m1_items'][:2]} ({len(g['m1_excluded'])} excluded: outside the group "
            f"and already in the source map), in window {g['in_window']}")
    with open(os.path.join(folder, "result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    logf.close()
    return 0


class hold_sigint:
    """Defer SIGINT (Ctrl-C) over the block: the signal is noted, and with `raise_after` a KeyboardInterrupt is
    raised once the block has ended and the old handler is back, so an interrupt never lands between two steps
    that must go together (a Popen and its registration) or in the middle of a cleanup.  Only the main thread
    gets signals; elsewhere the block is not held."""

    def __init__(self, raise_after: bool = True):
        self.raise_after, self.hit, self.old = raise_after, False, None

    def __enter__(self):
        if threading.current_thread() is threading.main_thread():
            self.old = signal.signal(signal.SIGINT, self._note)
        return self

    def _note(self, signum, frame):
        self.hit = True

    def __exit__(self, *exc):
        if self.old is not None:
            signal.signal(signal.SIGINT, self.old)
        if self.hit and self.raise_after and exc[0] is None:
            raise KeyboardInterrupt
        return False


def reap_all(running: list) -> None:
    """End every group of `running` (items `(instance, arm, Popen)`), removing each once reaped.  An interrupt
    meanwhile is held until all are signalled and reaped (`hold_sigint`); one arriving before the hold is in
    place retries it, so the groups are all ended however often Ctrl-C is pressed."""
    while running:
        try:
            with hold_sigint(raise_after=False):
                while running:
                    end_group(running[0][2])
                    running.pop(0)
        except KeyboardInterrupt:
            continue


def end_group(proc) -> None:
    """End a campaign child's process group and reap its leader: SIGINT (the solver stops and writes), then SIGKILL
    to the group once `END_GRACE` seconds have passed with a member left, whether or not the leader exited (a solver
    descendant outlives it)."""
    def alive():
        try:
            os.killpg(proc.pid, 0)
        except (ProcessLookupError, PermissionError):
            return False
        return True
    grace = END_GRACE
    end = time.time() + grace
    try:
        os.killpg(proc.pid, signal.SIGINT)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    while alive() and time.time() < end:
        time.sleep(0.05)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait()


def all_runs(a) -> int:
    report = capture.sibling("bnc_report", "report.py")
    failed = []
    jobs, running, todo = max(1, a.jobs), [], [(i, r) for i in a.insts for r in a.arms]
    try:
        _drive(a, jobs, running, todo, failed)
    except BaseException:       # every child has its own session: an interrupt reaches none of them
        reap_all(running)
        raise
    report.write(a.out, a.instances)
    for i, r, rc in failed:
        print(f"FAILED {i} {r}: rc {rc} or no result.json (stderr in {os.path.join(a.out, i, r, 'stderr')})", flush=True)
    return 1 if failed else 0


def _drive(a, jobs: int, running: list, todo: list, failed: list) -> None:
    """Start the `todo` (instance, arm) children `jobs` at a time, each in its own process group, until all are done."""
    py = sys.executable
    while todo or running:
        while todo and len(running) < jobs:
            i, r = todo.pop(0)
            cmd = [py, "-u", os.path.abspath(__file__), "one", i, r, "--time-limit", str(a.time_limit),
                   "--threads", str(a.threads), "--out", a.out, "--instances", a.instances,
                   "--m2-dir", a.m2_dir] + (["--frac-root"] if a.frac_root else []) \
                + (["--no-flow"] if a.no_flow else [])
            os.makedirs(os.path.join(a.out, i, r), exist_ok=True)
            stale = os.path.join(a.out, i, r, "result.json")
            if os.path.exists(stale):
                os.replace(stale, os.path.join(a.out, i, r, "result.previous.json"))
            print("start", " ".join(cmd), flush=True)
            with hold_sigint():     # an interrupt after the Popen returns waits until the group is in `running`
                running.append((i, r, subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=open(
                    os.path.join(a.out, i, r, "stderr"), "w"), start_new_session=True)))
        time.sleep(2)
        for item in list(running):
            if item[2].poll() is not None:
                print(f"done {item[0]} {item[1]} rc {item[2].returncode}", flush=True)
                running.remove(item)
                made = os.path.exists(os.path.join(a.out, item[0], item[1], "result.json"))
                if item[2].returncode != 0 or not made:
                    failed.append((item[0], item[1], item[2].returncode))


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
    a = ap.parse_args(argv)
    a.instances = a.instances or os.path.join(a.out, "instances")
    return one(a.instance, a.arm, a) if a.cmd == "one" else all_runs(a)


if __name__ == "__main__":
    sys.exit(main())
