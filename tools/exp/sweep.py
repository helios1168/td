"""sweep.py -- run an experiment grid into flat, tracked run folders (#92).

    "$TD_PY" -u tools/exp/sweep.py <grid.toml> [--jobs N] [--root DIR] [--retry-failed]

A grid file names its lane, its formulation (a table of `tools/exp/formulations.toml`) and the
instance, `extract = "<path>"` or `fixture = <seed>`, with `public` for the 2025 downloads.  Its
`[params]` table holds the settings every job shares and its `[grid]` table one list per swept
setting; both are flattened to dotted keys, and the jobs are the product of the `[grid]` lists
over `[params]`.  `threads` (default 1) is the job's HiGHS thread count; the support formulation
reads `scenario`, `time_limit`, `maps` and the `spec.*` overrides into the scenario TOML.  A
`scenario` parameter names a file under the td root, or an absolute path: the sweep reads it once,
and each job runs from that snapshot, `scenario.toml` in its run folder.

    lane = "smoke"
    formulation = "support"
    extract = "/Users/Shared/sv-ntlee/td/instance_descaled.json.gz"
    [params]
    scenario = "scenarios/51_total_13n_11wh_24fi_3wifi.toml"
    time_limit = 120
    [grid]
    "spec.channels.WH.k" = [10, 11]

**Identity.**  A job's run id is `<lane>-<formulation>-<hash8>`, the hash over its flattened
parameters, the scenario file's sha256, the code's commit (with the hash of the uncommitted diff
when the tree is dirty, so uncommitted code never reuses a committed run) and the instance's
sha256.  A run id whose manifest says `done` or `failed` is skipped (`--retry-failed` reruns the
failed).  One left `queued` or `running` is cleared and run again only when it is abandoned: every
owner the manifest records (the sweep that queued it, the job process that ran it) was on this
host and is no longer running.  Any other unfinished run id refuses the whole sweep before a
folder is touched.

**The run folder** is `<root>/<lane>/<run_id>/`, `<root>` by default `$TD_REPO/runs/exp`.  It holds
`manifest.json`, `log.txt` (the job's output) and every file the formulation writes, flat.  The
manifest carries the identity, the provenance (commit, dirty flag and diff hash, host, instance
sha256, times), the flattened parameters, the status (queued, running, done or failed) with the
engine's stop reason, each channel's solver status and gap from `solver.json`, the audit verdict
from `run.json`, and the metrics: `worst_dev` and `mean_dev` from `districts.csv`, overlaid by the
looks scorer's `score(folder)` when `tools/looks/score.py` is present.

**Processes.**  Each job runs in its own process (`--job <folder>`), at most `--jobs` at once,
with every HiGHS solve of the process at the job's one thread count (trap 18).  The sweep ends,
however it ends, with `/Users/Shared/sv-ntlee/agent/notify` (`--notify`), which wakes the
launching session.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime
import hashlib
import importlib.util
import itertools
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FORMULATIONS = os.path.join(ROOT, "tools", "exp", "formulations.toml")
LOOKS_SCORER = os.path.join(ROOT, "tools", "looks", "score.py")
NOTIFY = "/Users/Shared/sv-ntlee/agent/notify"
MANIFEST = "manifest.json"
LOG = "log.txt"
SCENARIO = "scenario.toml"
NAME = re.compile(r"[A-Za-z0-9_.]{1,64}")      # a lane or formulation: no "-", which joins run ids
FINISHED = ("done", "failed")


class SweepError(RuntimeError):
    """The grid cannot be run: the sweep stops with the reason before any job starts."""


def default_root() -> str:
    return os.path.join(os.environ.get("TD_REPO") or ROOT, "runs", "exp")


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------------------ the grid
def flatten(table: dict, prefix: str = "") -> dict:
    """{dotted key: leaf}, recursing into tables only."""
    out = {}
    for k, v in table.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def expand(grid: dict) -> list:
    """The flattened parameters of each job: `[params]` with each product of the `[grid]` lists."""
    fixed = flatten(grid.get("params", {}))
    swept = flatten(grid.get("grid", {}))
    bad = sorted(k for k, v in swept.items() if not isinstance(v, list) or not v)
    if bad:
        raise SweepError(f"[grid] {', '.join(bad)} must each be a non-empty list")
    both = sorted(set(fixed) & set(swept))
    if both:
        raise SweepError(f"[params] and [grid] both set {', '.join(both)}")
    keys = sorted(swept)
    jobs = []
    for values in itertools.product(*(swept[k] for k in keys)):
        p = {"threads": 1, **fixed, **dict(zip(keys, values))}
        if not isinstance(p["threads"], int) or isinstance(p["threads"], bool) or p["threads"] < 1:
            raise SweepError(f"threads must be a positive integer, not {p['threads']!r}")
        jobs.append(dict(sorted(p.items())))
    return jobs


def formulations() -> dict:
    with open(FORMULATIONS, "rb") as fh:
        return tomllib.load(fh)


def load_grid(path: str) -> dict:
    with open(path, "rb") as fh:
        g = tomllib.load(fh)
    known = {"lane", "formulation", "extract", "fixture", "public", "params", "grid"}
    if set(g) - known:
        raise SweepError(f"{path}: unknown keys {', '.join(sorted(set(g) - known))}")
    for key in ("lane", "formulation"):
        if not isinstance(g.get(key), str) or not NAME.fullmatch(g[key]) or g[key] in (".", ".."):
            raise SweepError(f"{path}: {key} must be 1 to 64 of A-Z a-z 0-9 _ ., not {g.get(key)!r}")
    if g["formulation"] not in formulations():
        raise SweepError(f"{path}: formulation {g['formulation']!r} is not in {FORMULATIONS}")
    if ("extract" in g) == ("fixture" in g):
        raise SweepError(f"{path}: give exactly one of extract or fixture")
    if "extract" in g:
        g["extract"] = os.path.abspath(os.path.join(ROOT, g["extract"]))
    return g


# ------------------------------------------------------------------------------ provenance
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def instance(g: dict) -> dict:
    """The instance a grid runs on and its sha256: the extract file's, or the fixture seed's text."""
    if "extract" in g:
        return {"instance": g["extract"], "instance_sha256": sha256_file(g["extract"])}
    text = f"fixture seed {g['fixture']}"
    return {"instance": text, "instance_sha256": hashlib.sha256(text.encode()).hexdigest()}


def git(*args) -> bytes:
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, check=True).stdout


def code_state() -> dict:
    """The commit, whether the tree differs from it, and the sha256 of the difference: the diff
    against HEAD and each untracked file's path and bytes (None when clean)."""
    commit = git("rev-parse", "HEAD").decode().strip()
    diff = git("diff", "HEAD", "--binary")
    untracked = sorted(git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0"))
    h = hashlib.sha256(diff)
    for path in filter(None, untracked):
        h.update(path.encode() + b"\0")
        with open(os.path.join(ROOT, path), "rb") as fh:
            h.update(fh.read())
    dirty = bool(diff) or any(untracked)
    return {"commit": commit, "dirty": dirty, "diff_sha256": h.hexdigest() if dirty else None}


def run_id(lane: str, formulation: str, params: dict, code: dict, inst: dict,
           scenario_sha256: str | None = None) -> str:
    commit = code["commit"] + (f"+{code['diff_sha256'][:8]}" if code["dirty"] else "")
    key = json.dumps({"params": params, "commit": commit, "instance": inst["instance_sha256"],
                      "scenario": scenario_sha256}, sort_keys=True, separators=(",", ":"))
    return f"{lane}-{formulation}-{hashlib.sha256(key.encode()).hexdigest()[:8]}"


def process_start(pid: int):
    """When process `pid` started, as `ps` prints it, or None when no such process runs."""
    got = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True)
    return got.stdout.strip() or None


def owner() -> dict:
    """This process as a run's owner: its host, pid and start time (a reused pid starts later)."""
    return {"host": platform.node(), "pid": os.getpid(), "started": process_start(os.getpid())}


def abandoned(m: dict) -> bool:
    """True when every owner of an unfinished run was on this host and is no longer running.  An
    owner on another host, or a manifest without owners, cannot be checked: not abandoned."""
    owners = m.get("owners") or []
    return bool(owners) and all(o.get("host") == platform.node() and o.get("started")
                                and process_start(o["pid"]) != o["started"] for o in owners)


# ------------------------------------------------------------------------------ the manifest
def read_manifest(folder: str) -> dict:
    with open(os.path.join(folder, MANIFEST), encoding="utf-8") as fh:
        return json.load(fh)


def write_manifest(folder: str, m: dict) -> None:
    path = os.path.join(folder, MANIFEST)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(path + ".tmp", path)


def solver_summary(folder: str) -> dict:
    """{channel: {status, gap, time_s[, smallest_delta]}} from the run's `solver.json`."""
    path = os.path.join(folder, "solver.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = {}
    for c, rep in doc.items():
        s = rep.get("solver", {})
        out[c] = {k: s.get(k) for k in ("status", "gap", "time_s")}
        if "smallest_delta" in rep:
            out[c]["smallest_delta"] = {k: rep["smallest_delta"].get(k)
                                        for k in ("method", "status", "delta")}
    return out


def audit_verdict(folder: str):
    path = os.path.join(folder, "run.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("verdict")


def drawn_deviation(folder: str) -> dict:
    """`worst_dev` and `mean_dev`: |drawn mass / channel mean − 1| over the districts of
    `districts.csv`, as fractions; {} without the file."""
    path = os.path.join(folder, "districts.csv")
    if not os.path.exists(path):
        return {}
    by = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            by.setdefault(r["channel"], []).append(float(r["drawn_mass"]))
    devs = [abs(m / (sum(ms) / len(ms)) - 1) for ms in by.values() if sum(ms) > 0 for m in ms]
    return {"worst_dev": max(devs), "mean_dev": sum(devs) / len(devs)} if devs else {}


def looks_score(folder: str):
    """The looks scorer's `score(folder)` dict, or None when `tools/looks/score.py` is absent."""
    if not os.path.exists(LOOKS_SCORER):
        return None
    spec = importlib.util.spec_from_file_location("looks_score", LOOKS_SCORER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.score(folder))


def metrics(folder: str) -> tuple:
    """(metrics, scorer error): `drawn_deviation` overlaid by `looks_score` when present."""
    out = drawn_deviation(folder)
    try:
        scored = looks_score(folder)
    except Exception as e:                      # a scorer failure never fails the run
        return out, f"{type(e).__name__}: {e}"
    return {**out, **(scored or {})}, None


# ------------------------------------------------------------------------------ one job
def pin_threads(n: int) -> None:
    """Every HiGHS solve this process makes runs on `n` threads (trap 18): each `highspy.Highs`,
    and the realizer's SciPy `linprog`, whose bundled HiGHS takes `threads` from its options
    verbatim with an OptimizeWarning that calls it unrecognized."""
    import warnings

    import highspy
    from scipy.optimize import OptimizeWarning

    from td import realize
    base = highspy.Highs

    class Highs(base):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.setOptionValue("threads", n)
    highspy.Highs = Highs
    realize.LP_OPTIONS["threads"] = n           # copied by td/realize.py at each call
    warnings.filterwarnings("ignore", r"Unrecognized options detected: \{'threads': \d+\}\. ",
                            OptimizeWarning)


def entry(name: str):
    """The callable `<file>:<function>` that formulation `name` names, loaded from its file."""
    path, func = formulations()[name]["entry"].rsplit(":", 1)
    spec = importlib.util.spec_from_file_location(f"formulation_{name}", os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func)


def run_job(folder: str) -> int:
    """The job process: run the manifest's formulation into `folder` and record the outcome."""
    m = read_manifest(folder)
    m.update(status="running", started_at=now(), owners=m.get("owners", []) + [owner()])
    write_manifest(folder, m)
    pin_threads(m["params"]["threads"])
    t0 = time.time()
    try:
        entry(m["formulation"])(m, folder)
        m["status"], m["stop_reason"] = "done", None
    except Exception as e:
        m["status"], m["stop_reason"] = "failed", f"{type(e).__name__}: {e}"
        print(f"run stopped: {m['stop_reason']}", file=sys.stderr)
    m["solver"] = solver_summary(folder)
    if m["status"] == "done":
        m["stop_reason"] = "; ".join(f"{c} {s['status']}" for c, s in sorted(m["solver"].items()))
    m["audit"] = audit_verdict(folder)
    m["metrics"], m["scorer_error"] = metrics(folder) if m["status"] == "done" else ({}, None)
    m.update(finished_at=now(), seconds=round(time.time() - t0, 1))
    write_manifest(folder, m)
    return 0 if m["status"] == "done" else 1


def run_support(m: dict, folder: str) -> None:
    """The `support` formulation: `td.output.run` on the run's snapshot of `params.scenario` with
    the `spec.*` overrides, written to `spec.toml` in the run folder first."""
    from td import data, geo, output
    from td import spec as tdspec
    p = m["params"]
    with open(os.path.join(folder, SCENARIO), "rb") as fh:
        raw = tomllib.load(fh)
    for key, value in p.items():
        if key.startswith("spec."):
            *path, last = key.removeprefix("spec.").split(".")
            node = raw
            for part in path:
                node = node.setdefault(part, {})
            node[last] = value
    spec_path = os.path.join(folder, "spec.toml")
    with open(spec_path, "w", encoding="utf-8") as fh:
        fh.write(dump_toml(raw))
    s = tdspec.load(spec_path)
    ref = geo.read_reference()
    public = m["public"]
    if m.get("fixture") is not None:
        fx = data.fixture(m["fixture"], channels=s.fine_channels, reference=ref, public=public)
        extract, graph = fx.extract, fx.graph
    else:
        extract, graph = data.load(m["extract"]), None
    res = output.run(s, extract, folder, graph, ref, public, p.get("time_limit"),
                     p.get("maps", True), m["provenance"]["instance"],
                     keep=tuple(os.listdir(folder)))
    if res.verdict != "pass":
        print(f"audit: {res.verdict}", file=sys.stderr)


def _toml_key(k: str) -> str:
    return k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else json.dumps(k, ensure_ascii=False)


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{_toml_key(k)} = {_toml_value(x)}" for k, x in v.items()) + " }"
    raise SweepError(f"cannot write {v!r} to TOML")


def dump_toml(raw: dict) -> str:
    """`raw` as TOML that `tomllib` reads back equal; tables as sections, the rest inline."""
    lines = []

    def table(t: dict, path: tuple):
        if path:
            lines.append(f"\n[{'.'.join(map(_toml_key, path))}]")
        for k, v in t.items():
            if not isinstance(v, dict):
                lines.append(f"{_toml_key(k)} = {_toml_value(v)}")
        for k, v in t.items():
            if isinstance(v, dict):
                table(v, path + (k,))
    table(raw, ())
    text = "\n".join(lines).lstrip("\n") + "\n"
    if tomllib.loads(text) != raw:
        raise SweepError("the scenario does not survive a TOML round trip")
    return text


# ------------------------------------------------------------------------------ the sweep
def read_scenario(params: dict, cache: dict):
    """(resolved path, bytes) of the job's `scenario` parameter, each file read once per sweep, or
    (None, None) without one."""
    if "scenario" not in params:
        return None, None
    path = os.path.abspath(os.path.join(ROOT, params["scenario"]))
    if path not in cache:
        try:
            with open(path, "rb") as fh:
                cache[path] = fh.read()
        except OSError as e:
            raise SweepError(f"scenario {params['scenario']}: {e.strerror}") from None
    return path, cache[path]


def prepare(g: dict, root: str, retry_failed: bool = False) -> tuple:
    """([folders to run], [run ids skipped]): a queued manifest and the scenario snapshot in each
    new or cleared folder.  An unfinished run not verified abandoned refuses the sweep first."""
    code, inst = code_state(), instance(g)
    public = g.get("public")
    if public is None:
        from td import geo
        public = geo.PUBLIC_DIR
        if not os.path.exists(os.path.join(public, "tl_2025_us_state.zip")) and os.environ.get("TD_REPO"):
            public = os.path.join(os.environ["TD_REPO"], "data", "public")
    lane_dir = os.path.join(root, g["lane"])
    jobs, skipped, refused, seen, scenarios = [], [], [], set(), {}
    for params in expand(g):
        path, text = read_scenario(params, scenarios)
        sha = hashlib.sha256(text).hexdigest() if text is not None else None
        rid = run_id(g["lane"], g["formulation"], params, code, inst, sha)
        if rid in seen:
            continue
        seen.add(rid)
        folder = os.path.join(lane_dir, rid)
        if os.path.exists(folder):
            if not os.path.exists(os.path.join(folder, MANIFEST)):
                raise SweepError(f"{folder} exists without a {MANIFEST}; remove it by hand")
            m = read_manifest(folder)
            if m.get("status") == "done" or (m.get("status") == "failed" and not retry_failed):
                skipped.append(rid)
                continue
            if m.get("status") not in FINISHED and not abandoned(m):
                refused.append(f"{rid} ({m.get('status')}, owners "
                               + (", ".join(f"{o.get('host')}:{o.get('pid')}"
                                            for o in m.get("owners") or []) or "unrecorded") + ")")
                continue
        jobs.append((folder, rid, params, path, text, sha))
    if refused:
        raise SweepError(f"runs still owned or not verified abandoned: {'; '.join(refused)}; "
                         "wait for them, or remove a dead one by hand")
    todo = []
    for folder, rid, params, path, text, sha in jobs:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
        if text is not None:
            with open(os.path.join(folder, SCENARIO), "wb") as fh:
                fh.write(text)
        write_manifest(folder, {
            "run_id": rid, "lane": g["lane"], "formulation": g["formulation"], "folder": folder,
            "status": "queued", "stop_reason": None, "params": params,
            "scenario": {"path": path, "sha256": sha, "snapshot": SCENARIO} if text is not None else None,
            "extract": g.get("extract"), "fixture": g.get("fixture"), "public": public,
            "provenance": {**code, **inst, "host": platform.node(), "queued_at": now()},
            "owners": [owner()], "solver": {}, "audit": None, "metrics": {}})
        todo.append(folder)
    return todo, skipped


def launch(folder: str) -> str:
    """Run one job process; a process that dies without recording its end fails the run."""
    with open(os.path.join(folder, LOG), "ab") as log:
        rc = subprocess.run([sys.executable, "-u", os.path.abspath(__file__), "--job", folder],
                            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
    m = read_manifest(folder)
    if m["status"] not in FINISHED:
        with open(os.path.join(folder, LOG), encoding="utf-8", errors="replace") as fh:
            tail = (fh.read().strip().splitlines() or [""])[-1]
        m.update(status="failed", stop_reason=f"job process exited {rc}: {tail}",
                 finished_at=now())
        write_manifest(folder, m)
    return m["status"]


def notify(command: str, line: str) -> None:
    try:
        if subprocess.run([command, line]).returncode != 0:
            print(f"notify failed: {command}", file=sys.stderr)
    except OSError as e:
        print(f"notify failed: {e}", file=sys.stderr)


def sweep(a) -> tuple:
    """(exit code, one-line result) of the sweep `a` asks for; SweepError and the other preflight
    errors stop it before any job starts."""
    if not a.grid or a.jobs < 1:
        raise SweepError("give a grid file and --jobs of at least 1")
    g = load_grid(a.grid)
    root = os.path.abspath(a.root or default_root())
    todo, skipped = prepare(g, root, a.retry_failed)
    for rid in skipped:
        print(f"skip  {rid}")
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        futures = {pool.submit(launch, f): f for f in todo}
        for fut in concurrent.futures.as_completed(futures):
            print(f"{fut.result():7s}{os.path.basename(futures[fut])}", flush=True)
    status = [read_manifest(f)["status"] for f in todo]
    line = (f"sweep {g['lane']}/{g['formulation']}: {status.count('done')} done, "
            f"{status.count('failed')} failed, {len(skipped)} skipped; {os.path.join(root, g['lane'])}")
    print(line)
    return (0 if "failed" not in status else 1), line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools/exp/sweep.py", description=__doc__.splitlines()[0])
    ap.add_argument("grid", nargs="?", help="a grid TOML file")
    ap.add_argument("--jobs", type=int, default=1, help="job processes at once (default 1)")
    ap.add_argument("--root", default=None, help="runs root (default $TD_REPO/runs/exp)")
    ap.add_argument("--retry-failed", action="store_true", help="rerun failed run ids")
    ap.add_argument("--notify", default=NOTIFY, help="the command the sweep ends with")
    ap.add_argument("--job", metavar="FOLDER", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.job:
        return run_job(a.job)
    rc, line = 1, f"sweep {a.grid}: stopped by an error before its end"
    try:
        rc, line = sweep(a)
    except (SweepError, OSError, subprocess.CalledProcessError, tomllib.TOMLDecodeError) as e:
        rc, line = 2, f"sweep {a.grid}: stopped: {e}"
        print(line, file=sys.stderr)
    finally:
        notify(a.notify, line)
    return rc


if __name__ == "__main__":
    sys.exit(main())
