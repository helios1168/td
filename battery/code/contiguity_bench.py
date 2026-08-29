#!/usr/bin/env python3
"""
contiguity_bench.py -- the benchmark driver for the contiguity options (PLAN.md C.1, C.5).

    .venv/bin/python3 battery/code/contiguity_bench.py --stage S0 --dry-run
    .venv/bin/python3 battery/code/contiguity_bench.py --stage S1 --workers 11

Three phases, each runnable alone with `--phase`:

  1  instances : build every spec (filter -> rescale -> covariates -> method-independent
                 bounds) in the pool, write `instances.csv` and `instances/<name>.json`
  2  jobs      : instances x methods x rho x kappa through the pool, one row per job appended
                 to `rows.jsonl` by the *parent* (flush + fsync, so a killed run loses nothing)
  3  post      : cross-method UB*, `rows_scored.jsonl`, `summary.csv`, `bugs.json`

Everything lands in `battery/results/contiguity/<run_id>/`.  `_assert_safe_out` refuses any
path outside that root, and in particular anything under `battery/figures/` (primary artifacts).

Notes on the machinery
----------------------
*Threads.*  Every BLAS/OpenMP thread-count variable is pinned to 1 *before* numpy is imported;
11 single-threaded workers beat 11 oversubscribed ones on a 12-core machine.

*stdout is not a data channel.*  HiGHS writes to file descriptor 1 from C, so rows never go to
stdout; progress goes to `run.log` and stderr.

*Two schedulers.*  `--scheduler pool` (default) is `multiprocessing.Pool(maxtasksperchild=1)`
and relies on `base.run_method`'s SIGALRM backstop.  A C-extension solver that blocks signals
would defeat that, so `--scheduler proc` runs each job in its own `Process` and the parent
`terminate()`s any that outlives `1.5*cap + 60 s` (risk R3).
"""
from __future__ import annotations

import os

# ---- one thread per worker; must precede the numpy import (risk: 11x oversubscription) ----
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import argparse                              # noqa: E402
import csv                                   # noqa: E402
import json                                  # noqa: E402
import multiprocessing as mp                 # noqa: E402
import queue as _queue                       # noqa: E402
import re                                    # noqa: E402
import signal                                # noqa: E402
import statistics                            # noqa: E402
import sys                                   # noqa: E402
import threading                             # noqa: E402
import time                                  # noqa: E402
from dataclasses import dataclass, replace         # noqa: E402
from pathlib import Path                     # noqa: E402
from typing import Optional                  # noqa: E402

import numpy as np                           # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT / "code"), str(ROOT / "battery" / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import instances                             # noqa: E402
from instances import (THETA, LAM, InstanceSpec, _jsonable,  # noqa: E402
                       build_pair, named_failures, specs_for_tiers)
from contig_methods import REGISTRY, base    # noqa: E402

RESULTS_ROOT = ROOT / "battery" / "results" / "contiguity"
FORBIDDEN = ROOT / "battery" / "figures"
GAP_TIMES = (5, 20, 60, 300, 1200)


def _assert_safe_out(p) -> Path:
    """Refuse to write anywhere but under `battery/results/contiguity/` (never figures/)."""
    p = Path(p).resolve()
    fig = FORBIDDEN.resolve()
    if p == fig or fig in p.parents or "battery/figures" in p.as_posix():
        raise RuntimeError(f"refusing to write under battery/figures/: {p}")
    root = RESULTS_ROOT.resolve()
    if p != root and root not in p.parents:
        raise RuntimeError(f"refusing to write outside {root}: {p}")
    return p


# ================================================================================ presets
@dataclass(frozen=True)
class Preset:
    tiers: tuple
    methods: Optional[tuple]        # None = every registered method except the fakes
    rho: tuple
    cap: float
    include_named: bool = False
    rho_current_extra: tuple = ()   # extra rho values, `current*` only (battery continuity)
    methods_required: bool = False  # the user must name the finalists
    respect_state: bool = False


PRESETS: dict[str, Preset] = {
    # rho = 0 is the model everywhere (PLAN.md "Decisions taken"); 2e-3 survives only as a
    # secondary column for the legacy `current` control.
    "S0": Preset(("T0",), ("current", "current_tight", "current_tu", "current_inout", "brute", "flow", "warm"), (0.0,), 60.0,
                 include_named=True),
    "S1": Preset(("T0", "T1", "T2"), None, (0.0,), 60.0, rho_current_extra=(2e-3,)),
    "S2": Preset(("T1", "T2", "T3"), None, (0.0, 2e-3), 1200.0, methods_required=True),
    "S3": Preset(("T3",), None, (0.0,), 3600.0, methods_required=True),
    "S4": Preset(("T4",), None, (0.0,), 1200.0, methods_required=True, respect_state=True),
}


def registered_methods() -> list:
    return sorted(REGISTRY)


def default_methods() -> list:
    return [m for m in registered_methods() if not m.startswith("fake")]


# ==================================================================================== jobs
@dataclass(frozen=True)
class Job:
    spec: InstanceSpec
    method: str
    base_method: str
    rho: float
    kappa: float
    cap: float
    seed: int
    rescale: bool
    lexi: bool
    save_assignments: bool
    product_free: Optional[float]
    run_id: str
    run_dir: str
    max_iter: Optional[int] = None

    def key(self) -> str:
        return (f"{self.spec.name}__{self.method}__rho{self.rho:g}"
                f"__k{self.kappa:g}__s{self.seed}")


def _fmt(x):
    return "" if x is None else x


# ------------------------------------------------------------------------- phase 1 worker
def build_instance(args) -> dict:
    """Pool worker: realise one spec, write its JSON, return the `instances.csv` row."""
    spec, run_dir, rescale, bounds_cap = args
    t0 = time.perf_counter()
    ident = dict(instance=spec.name, tier=spec.tier, case=spec.case, scenario=spec.scenario,
                 seed=spec.seed, rep_a=spec.rep_a, rep_b=spec.rep_b,
                 min_share=spec.min_share, dense=spec.dense,
                 respect_state=spec.respect_state, named_failure=spec.named_failure,
                 n_expected=spec.n_expected)
    try:
        pi = build_pair(spec, theta=THETA, lam=LAM, rescale=rescale, with_bounds=True,
                        bounds_cap=bounds_cap)
    except ValueError as e:                 # e.g. respect_state on a stateless instance
        return dict(ident, ok=False, skip_reason=f"{type(e).__name__}: {e}",
                    build_s=time.perf_counter() - t0)
    except Exception as e:                  # noqa: BLE001 -- generator drift, etc.
        return dict(ident, ok=False, skip_reason=f"{type(e).__name__}: {e}",
                    build_s=time.perf_counter() - t0)
    out = Path(_assert_safe_out(Path(run_dir) / "instances" / f"{spec.name}.json"))
    instances.write_instance_json(pi, out)
    row = dict(ident, ok=True, skip_reason="")
    row.update(pi.covariates)
    row.update({k: v for k, v in pi.bounds.items() if k != "free_to_a"})
    row["build_s"] = time.perf_counter() - t0
    return row


# ------------------------------------------------------------------------- phase 2 worker
def _worker_init():
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[v] = "1"
    signal.signal(signal.SIGINT, signal.SIG_IGN)   # the parent owns Ctrl-C


def _lexi(pi, job, mspec, res, lb):
    """Lexicographic perimeter post-pass (W9a).  Absent until `loop_v2` lands."""
    if not job.lexi or lb is None or res.to_a is None:
        return None, "off" if not job.lexi else "no_feasible_iterate"
    try:
        out = base.lexi_perimeter(pi.G, pi.nodes, res.to_a, lb, mspec.solve,
                                  theta=THETA, lam=LAM, kappa=job.kappa,
                                  time_limit=job.cap, seed=job.seed, **mspec.kwargs)
    except NotImplementedError:
        return None, "not_implemented"
    except Exception as e:                          # noqa: BLE001
        return None, f"error: {type(e).__name__}: {e}"
    per = getattr(out, "perimeter", None)
    if per is None and isinstance(out, dict):
        per = out.get("perimeter")
    if per is None and isinstance(out, (int, float, np.integer, np.floating)):
        per = out
    return (None if per is None else int(per)), "ok"


def run_job(job: Job) -> dict:
    """Pool/Process worker: rebuild the instance, run one method, return the validated row."""
    harness = dict(job_key=job.key(), run_id=job.run_id, instance=job.spec.name,
                   tier=job.spec.tier, case=job.spec.case, method=job.method,
                   base_method=job.base_method, rho=job.rho, kappa=job.kappa,
                   seed=job.seed, cap=job.cap, rescaled=job.rescale,
                   respect_state=job.spec.respect_state, n=job.spec.n_expected,
                   n_expected=job.spec.n_expected, dense=job.spec.dense,
                   named_failure=job.spec.named_failure)
    try:
        pi = build_pair(job.spec, theta=THETA, lam=LAM, rescale=job.rescale,
                        kappa=job.kappa, with_bounds=False)
        mspec = REGISTRY[job.method]
        opts = dict(mspec.kwargs)
        if job.max_iter is not None:
            opts["max_iter"] = job.max_iter
        res = base.run_method(mspec.solve, pi.G, pi.nodes, theta=THETA, lam=LAM, rho=job.rho,
                              respect_state=False, time_limit=job.cap, seed=job.seed,
                              kappa=job.kappa, **opts)
        row = base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM, rho=job.rho,
                            kappa=job.kappa, respect_state=job.spec.respect_state,
                            product_free=job.product_free)
        per_lexi, lexi_status = _lexi(pi, job, mspec, res, row.get("LB"))
        row.update(harness)
        row.update(scale=pi.scale, n=pi.n,
                   to_a=None if res.to_a is None else sorted(res.to_a, key=base._sort_key),
                   trace=res.trace, perimeter_lexi=per_lexi, lexi_status=lexi_status,
                   product_free=job.product_free)
        if job.save_assignments and res.to_a is not None:
            p = _assert_safe_out(Path(job.run_dir) / "assign" / f"{job.key()}.npz")
            p.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(p, nodes=np.array(pi.nodes, dtype=object),
                                x=base.mask(pi.nodes, res.to_a), scale=np.array([pi.scale]))
        return row
    except Exception as e:                          # noqa: BLE001 -- every failure is a row
        return dict(harness, status="error", status_eff="error", valid=False,
                    violations=[f"harness: {type(e).__name__}: {e}"], to_a=None, trace=[],
                    perimeter_lexi=None, lexi_status="off", message=f"{type(e).__name__}: {e}")


# ================================================================================ logging
class Log:
    def __init__(self, path: Optional[Path] = None, quiet: bool = False):
        self.f = None
        self.quiet = quiet
        if path is not None:
            self.f = open(_assert_safe_out(path), "a")

    def __call__(self, msg: str):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        if not self.quiet:
            print(line, file=sys.stderr, flush=True)
        if self.f:
            self.f.write(line + "\n")
            self.f.flush()

    def close(self):
        if self.f:
            self.f.close()


class Watchdog(threading.Thread):
    """Parent-side progress log: how many jobs are outstanding, and for how long."""

    def __init__(self, total: int, log: Log, every: float = 30.0):
        super().__init__(daemon=True)
        self.total, self.log, self.every = total, log, every
        self.done = 0
        self.t0 = time.perf_counter()
        self._stop = threading.Event()

    def run(self):
        while not self._stop.wait(self.every):
            el = time.perf_counter() - self.t0
            self.log(f"  ... {self.done}/{self.total} jobs done, {el:.0f}s elapsed, "
                     f"{self.total - self.done} outstanding")

    def stop(self):
        self._stop.set()


# ================================================================================ schedulers
def _run_pool(jobs, workers, start_method, log, on_row):
    ctx = mp.get_context(start_method)
    wd = Watchdog(len(jobs), log)
    wd.start()
    try:
        with ctx.Pool(max(1, workers), maxtasksperchild=1, initializer=_worker_init) as pool:
            for row in pool.imap_unordered(run_job, jobs):
                wd.done += 1
                on_row(row)
    finally:
        wd.stop()


def _proc_target(job, q):
    _worker_init()
    try:
        q.put(run_job(job))
    except Exception as e:                          # noqa: BLE001
        q.put(dict(job_key=job.key(), instance=job.spec.name, method=job.method,
                   status="error", status_eff="error", valid=False,
                   violations=[f"worker: {type(e).__name__}: {e}"]))


def _run_proc(jobs, workers, start_method, log, on_row):
    """Slot scheduler: one Process per job, parent `terminate()`s anything past the watchdog.

    The escape hatch for risk R3 -- a C-extension solver that swallows SIGALRM cannot be
    stopped from inside the worker, only killed from outside.
    """
    ctx = mp.get_context(start_method)
    q = ctx.Queue()
    pending = list(jobs)
    live: dict = {}
    done = 0
    total = len(jobs)
    t_last = time.perf_counter()
    while pending or live:
        while pending and len(live) < max(1, workers):
            job = pending.pop(0)
            p = ctx.Process(target=_proc_target, args=(job, q), daemon=True)
            p.start()
            live[p.pid] = (p, job, time.perf_counter())
        try:
            row = q.get(timeout=0.25)
            on_row(row)
            done += 1
        except _queue.Empty:
            pass
        now = time.perf_counter()
        for pid, (p, job, t0) in list(live.items()):
            limit = 1.5 * job.cap + 60.0
            if p.is_alive() and now - t0 > limit:
                log(f"  watchdog: terminating {job.key()} after {now - t0:.0f}s (cap {job.cap}s)")
                p.terminate()
                p.join(5)
                on_row(dict(job_key=job.key(), run_id=job.run_id, instance=job.spec.name,
                            tier=job.spec.tier, case=job.spec.case, method=job.method,
                            base_method=job.base_method, rho=job.rho, kappa=job.kappa,
                            seed=job.seed, cap=job.cap, status="error", status_eff="error",
                            valid=False, to_a=None, trace=[],
                            violations=[f"scheduler watchdog terminated after {now - t0:.0f}s"],
                            named_failure=job.spec.named_failure, n=job.spec.n_expected))
                done += 1
                del live[pid]
            elif not p.is_alive():
                p.join(1)
                del live[pid]
        if now - t_last > 30:
            t_last = now
            log(f"  ... {done}/{total} jobs done, {len(live)} live")
    # drain anything that arrived between the last get and the exit check
    while True:
        try:
            on_row(q.get_nowait())
        except _queue.Empty:
            break


# ================================================================================= phase 1
IDENT_COLS = ("instance", "tier", "case", "scenario", "seed", "rep_a", "rep_b", "min_share",
              "dense", "respect_state", "named_failure", "n", "n_expected", "ok",
              "skip_reason", "build_s")


def phase1(specs, run_dir: Path, *, workers: int, rescale: bool, bounds_cap: float,
           start_method: str, log: Log) -> dict:
    """Realise every spec, write `instances/<name>.json` + `instances.csv`.

    Returns {instance name: row}; rows with ok=False are excluded from phase 2 and land in
    `jobs.json["skipped"]`.
    """
    instances.warn_bounds_missing(log)
    log(f"phase 1: building {len(specs)} instances on {workers} workers")
    args = [(sp, str(run_dir), rescale, bounds_cap) for sp in specs]
    t0 = time.perf_counter()
    rows = []
    if workers <= 1:
        rows = [build_instance(a) for a in args]
    else:
        ctx = mp.get_context(start_method)
        with ctx.Pool(workers, maxtasksperchild=1, initializer=_worker_init) as pool:
            for r in pool.imap_unordered(build_instance, args):
                rows.append(r)
                if len(rows) % 25 == 0:
                    log(f"  ... {len(rows)}/{len(args)} built")
    by_name = {r["instance"]: r for r in rows}
    ordered = [by_name[sp.name] for sp in specs if sp.name in by_name]
    cols = list(IDENT_COLS) + [c for r in ordered for c in r if c not in IDENT_COLS]
    seen, columns = set(), []
    for c in cols:
        if c not in seen:
            seen.add(c)
            columns.append(c)
    p = _assert_safe_out(run_dir / "instances.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, restval="", extrasaction="ignore")
        w.writeheader()
        for r in ordered:
            w.writerow({k: _fmt(r.get(k)) for k in columns})
    bad = [r for r in ordered if not r["ok"]]
    log(f"phase 1: {len(ordered) - len(bad)} ok, {len(bad)} skipped, "
        f"{time.perf_counter() - t0:.1f}s -> instances.csv")
    return by_name


# ================================================================================= phase 2
def make_jobs(specs, inst_rows: dict, *, methods, rho_list, kappas, cap, seed, rescale, lexi,
              save_assignments, run_id, run_dir, max_iter, rho_current_extra=(),
              distances=None, done_keys=frozenset()) -> tuple:
    """Cross specs x methods x rho x kappa, applying every skip rule.  Returns (jobs, skipped)."""
    jobs, skipped = [], []

    def skip(sp, method, reason, **kw):
        skipped.append(dict(instance=sp.name, method=method, reason=reason, **kw))

    for sp in specs:
        info = inst_rows.get(sp.name)
        if info is not None and not info.get("ok", True):
            skip(sp, "*", f"instance build failed: {info.get('skip_reason')}")
            continue
        n = (info or {}).get("n") or sp.n_expected
        if sp.respect_state and info is not None and (info.get("n_states") or 0) < 1:
            skip(sp, "*", "respect_state requested but the instance has no `state` attribute")
            continue
        pf = (info or {}).get("product_free")
        pf = None if pf in ("", None) else float(pf)
        for method in methods:
            mspec = REGISTRY.get(method)
            if mspec is None:
                skip(sp, method, "method not in REGISTRY")
                continue
            if mspec.max_n is not None and n is not None and int(n) > mspec.max_n:
                skip(sp, method, f"n={n} exceeds {method}.MAX_N={mspec.max_n}")
                continue
            rl = list(rho_list)
            if rho_current_extra and mspec.base_name.startswith("current"):
                rl += [r for r in rho_current_extra if r not in rl]
            for rho in rl:
                for kappa in kappas:
                    if kappa and distances is None:
                        skip(sp, method, "kappa > 0 without a `distances` provider (W11)")
                        continue
                    job = Job(spec=sp, method=method, base_method=mspec.base_name, rho=float(rho),
                              kappa=float(kappa), cap=float(cap), seed=int(seed),
                              rescale=rescale, lexi=lexi, save_assignments=save_assignments,
                              product_free=pf, run_id=run_id, run_dir=str(run_dir),
                              max_iter=max_iter)
                    if job.key() in done_keys:
                        skip(sp, method, "already in rows.jsonl (--resume)")
                        continue
                    jobs.append(job)
    return jobs, skipped


def phase2(jobs, run_dir: Path, *, workers: int, scheduler: str, start_method: str,
           log: Log) -> int:
    """Run the jobs; the *parent* is the only writer of `rows.jsonl` (append + flush + fsync)."""
    if not jobs:
        log("phase 2: no jobs")
        return 0
    p = _assert_safe_out(run_dir / "rows.jsonl")
    log(f"phase 2: {len(jobs)} jobs on {workers} workers ({scheduler}/{start_method})")
    t0 = time.perf_counter()
    n = 0
    with open(p, "a") as f:
        def on_row(row):
            nonlocal n
            n += 1
            f.write(json.dumps(row, default=_jsonable) + "\n")
            f.flush()
            os.fsync(f.fileno())
            bad = "" if row.get("valid", True) else f"  !! {row.get('violations')}"
            log(f"  [{n}/{len(jobs)}] {row.get('instance')} {row.get('method')} "
                f"-> {row.get('status_eff', row.get('status'))} "
                f"({(row.get('t_total') or 0):.1f}s){bad}")
        runner = _run_proc if scheduler == "proc" else _run_pool
        runner(jobs, workers, start_method, log, on_row)
    log(f"phase 2: {n} rows in {time.perf_counter() - t0:.1f}s -> rows.jsonl")
    return n


# ================================================================================= phase 3
def _gap_at(trace, t):
    """Running (max LB, min UB) over the trace up to time t; None if either side is empty."""
    lb = ub = None
    for ev in trace or ():
        if not ev or ev[0] > t:
            break
        _, l, u = ev[0], ev[1], ev[2]
        if l is not None:
            lb = l if lb is None else max(lb, l)
        if u is not None:
            ub = u if ub is None else min(ub, u)
    if lb is None or ub is None:
        return None
    return ub - lb


def _median(vals):
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def _frac(rows, pred):
    return (sum(1 for r in rows if pred(r)) / len(rows)) if rows else None


SUMMARY_COLS = ["method", "base_method", "rho", "tier", "n_rows", "certified_frac",
                "rooted_optimal_frac", "gap_limit_frac", "feasible_frac", "median_t_to_cert",
                "median_gap_nats_at_cap", "worst_gap", "mean_cost_of_contiguity", "ef1_frac",
                "named_failures_certified", "errors"] + [f"gap_at_{t}" for t in GAP_TIMES]


def phase3(run_dir: Path, log: Log) -> dict:
    """Cross-method UB*, per-row `gap_vs_UB_star`, `summary.csv`, `bugs.json`."""
    rp = run_dir / "rows.jsonl"
    if not rp.exists():
        log("phase 3: no rows.jsonl")
        return {}
    rows = []
    with open(rp) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    # -- cross-method global upper bound, per (instance, rho, kappa) ----------------------
    ub_star: dict = {}
    for r in rows:
        if r.get("ub_scope") == "global" and r.get("UB") is not None and r.get("valid"):
            k = (r.get("instance"), r.get("rho"), r.get("kappa"))
            ub_star[k] = min(ub_star.get(k, np.inf), float(r["UB"]))
    bugs = []
    for r in rows:
        k = (r.get("instance"), r.get("rho"), r.get("kappa"))
        u = ub_star.get(k)
        r["UB_star_global"] = u
        lb = r.get("LB")
        r["gap_vs_UB_star"] = None if (u is None or lb is None) else u - lb
        if u is not None and lb is not None and lb > u + base.CERT_TOL:
            bugs.append(dict(instance=r.get("instance"), method=r.get("method"),
                             rho=r.get("rho"), LB=lb, UB_star_global=u,
                             excess=lb - u))
    with open(_assert_safe_out(run_dir / "rows_scored.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=_jsonable) + "\n")
    with open(_assert_safe_out(run_dir / "bugs.json"), "w") as f:
        json.dump(bugs, f, indent=1, default=_jsonable)

    # -- summary per (method, rho, tier) ---------------------------------------------------
    named = {s.name for s in named_failures()}
    groups: dict = {}
    for r in rows:
        groups.setdefault((r.get("method"), r.get("rho"), r.get("tier")), []).append(r)
    out = []
    for (method, rho, tier), rs in sorted(groups.items(), key=lambda kv: tuple(map(str, kv[0]))):
        cert = [r for r in rs if r.get("valid_certificate")]
        certified_named = {r["instance"] for r in cert if r.get("instance") in named}
        gaps = [r.get("gap_vs_UB_star") if r.get("gap_vs_UB_star") is not None
                else r.get("gap_nats") for r in rs]
        row = dict(method=method, base_method=(rs[0].get("base_method") if rs else ""),
                   rho=rho, tier=tier, n_rows=len(rs),
                   certified_frac=_frac(rs, lambda r: bool(r.get("valid_certificate"))),
                   rooted_optimal_frac=_frac(rs, lambda r: r.get("status_eff") == "optimal_rooted"),
                   gap_limit_frac=_frac(rs, lambda r: r.get("status") == "gap_limit"),
                   feasible_frac=_frac(rs, lambda r: r.get("feasible") is True),
                   median_t_to_cert=_median([r.get("t_total") for r in cert]),
                   median_gap_nats_at_cap=_median([r.get("gap_nats") for r in rs
                                                   if not r.get("valid_certificate")]),
                   worst_gap=max([g for g in gaps if g is not None], default=None),
                   mean_cost_of_contiguity=_mean([r.get("cost_of_contiguity") for r in rs]),
                   ef1_frac=_frac([r for r in rs if r.get("ef1") is not None],
                                  lambda r: bool(r.get("ef1"))),
                   named_failures_certified=f"{len(certified_named)}/{len(named)}",
                   errors=sum(1 for r in rs if r.get("status") == "error"))
        for t in GAP_TIMES:
            row[f"gap_at_{t}"] = _median([_gap_at(r.get("trace"), t) for r in rs])
        out.append(row)
    with open(_assert_safe_out(run_dir / "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLS, restval="", extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow({k: _fmt(r.get(k)) for k in SUMMARY_COLS})

    # -- instances.csv gains UB_star_global (at rho = 0, the headline objective) ----------
    ip = run_dir / "instances.csv"
    if ip.exists():
        with open(ip) as f:
            rd = list(csv.DictReader(f))
            cols = list(rd[0].keys()) if rd else []
        if "UB_star_global" not in cols:
            cols.append("UB_star_global")
        best = {}
        for (inst, rho, kappa), u in ub_star.items():
            if rho in (0, 0.0) and kappa in (0, 0.0):
                best[inst] = u
        for r in rd:
            r["UB_star_global"] = _fmt(best.get(r.get("instance")))
        with open(_assert_safe_out(ip), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, restval="", extrasaction="ignore")
            w.writeheader()
            w.writerows(rd)
    log(f"phase 3: {len(rows)} rows, {len(out)} summary groups, {len(bugs)} bugs "
        "-> summary.csv, rows_scored.jsonl, bugs.json")
    return dict(rows=len(rows), groups=len(out), bugs=len(bugs))


# ==================================================================================== CLI
def _floats(s: str) -> tuple:
    return tuple(float(x) for x in str(s).split(",") if str(x).strip() != "")


def _strs(s: str) -> tuple:
    return tuple(x.strip() for x in str(s).split(",") if x.strip())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="contiguity_bench",
                                description="contiguity-option benchmark driver (PLAN.md C.1)")
    p.add_argument("--stage", choices=sorted(PRESETS), default=None,
                   help="preset: instance tiers, methods, rho, cap")
    p.add_argument("--methods", type=_strs, default=None,
                   help="comma-separated registry keys (overrides the preset)")
    p.add_argument("--tiers", type=_strs, default=None,
                   help=f"comma-separated tiers; known: {','.join(sorted(instances.TIERS))}")
    p.add_argument("--instances", dest="regex", default=None,
                   help="regex filter on the instance name")
    p.add_argument("--cap", type=float, default=None, help="per-job time limit, seconds")
    p.add_argument("--rho", type=_floats, default=None, help="compactness weights (default 0)")
    p.add_argument("--kappa", type=_floats, default=(0.0,), help="travel-cost weights (W11)")
    p.add_argument("--respect-state", action="store_true",
                   help="delete cross-state edges; instances without `state` are skipped")
    p.add_argument("--workers", type=int, default=11)
    p.add_argument("--run-id", default=None)
    p.add_argument("--dry-run", action="store_true", help="count jobs; write nothing")
    p.add_argument("--max-iter", type=int, default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-rescale", action="store_true",
                   help="skip the sum(u_a+u_b)=100 rescale (the G4 invariance run)")
    p.add_argument("--lexi", action="store_true", help="lexicographic perimeter post-pass (W9a)")
    p.add_argument("--save-assignments", action="store_true")
    p.add_argument("--resume", action="store_true",
                   help="skip jobs already present in the run's rows.jsonl")
    p.add_argument("--bounds-cap", type=float, default=120.0,
                   help="cap on the free-Nash bound solve per instance (phase 1)")
    p.add_argument("--start-method", choices=("spawn", "fork"), default="spawn")
    p.add_argument("--phase", choices=("1", "2", "3", "all"), default="all")
    p.add_argument("--scheduler", choices=("pool", "proc"), default="pool",
                   help="'proc' kills jobs from outside; use when a solver ignores SIGALRM")
    p.add_argument("--list-methods", action="store_true")
    p.add_argument("--quiet", action="store_true", help="log to run.log only, not to stderr")
    return p


def resolve_plan(args) -> dict:
    """Preset + overrides -> the concrete run plan (tiers, methods, rho, cap, ...)."""
    preset = PRESETS.get(args.stage) if args.stage else None
    tiers = list(args.tiers) if args.tiers else (list(preset.tiers) if preset else ["T0"])
    if args.methods:
        methods, requested = list(args.methods), list(args.methods)
    elif preset is not None:
        requested = list(preset.methods) if preset.methods else default_methods()
        if preset.methods_required:
            raise SystemExit(f"--stage {args.stage} requires an explicit --methods list")
        methods = requested
    else:
        methods = requested = default_methods()
    missing = [m for m in requested if m not in REGISTRY]
    methods = [m for m in methods if m in REGISTRY]
    rho = tuple(args.rho) if args.rho is not None else (tuple(preset.rho) if preset else (0.0,))
    cap = args.cap if args.cap is not None else (preset.cap if preset else 60.0)
    return dict(tiers=tiers, methods=methods, missing_methods=missing, rho=rho, cap=float(cap),
                include_named=bool(preset.include_named) if preset else False,
                rho_current_extra=tuple(preset.rho_current_extra) if preset else (),
                respect_state=bool(args.respect_state or (preset.respect_state if preset else False)))


def collect_specs(plan, regex=None) -> list:
    specs = specs_for_tiers(plan["tiers"])
    if plan["include_named"]:
        have = {s.name for s in specs}
        specs += [s for s in named_failures() if s.name not in have]
    if plan["respect_state"]:
        specs = [replace(s, respect_state=True) for s in specs]
    if regex:
        rx = re.compile(regex)
        specs = [s for s in specs if rx.search(s.name)]
    seen, out = set(), []
    for s in specs:
        if s.name not in seen:
            seen.add(s.name)
            out.append(s)
    return out


def dry_run_report(specs, plan, kappas, log) -> dict:
    """Counts per tier x method, honouring the skip rules that need no instance build."""
    jobs, skipped = make_jobs(specs, {}, methods=plan["methods"], rho_list=plan["rho"],
                              kappas=kappas, cap=plan["cap"], seed=0, rescale=True, lexi=False,
                              save_assignments=False, run_id="dry", run_dir="/dev/null",
                              max_iter=None, rho_current_extra=plan["rho_current_extra"])
    counts: dict = {}
    for j in jobs:
        counts[(j.spec.tier, j.method)] = counts.get((j.spec.tier, j.method), 0) + 1
    methods = plan["methods"]
    w = max([12] + [len(m) for m in methods])
    tiers = [t for t in plan["tiers"] if any(s.tier == t for s in specs)]
    tiers += sorted({s.tier for s in specs} - set(tiers))     # named failures live in T1/T2/T4
    log("dry run -- nothing written")
    log(f"  tiers   : {', '.join(f'{t}({sum(1 for s in specs if s.tier == t)})' for t in tiers)}"
        f"   [{len(specs)} instances]")
    log(f"  methods : {', '.join(methods) or '(none registered)'}")
    if plan["missing_methods"]:
        log(f"  missing : {', '.join(plan['missing_methods'])} (not in REGISTRY)")
    log(f"  rho     : {', '.join(f'{r:g}' for r in plan['rho'])}"
        + (f"   (+{plan['rho_current_extra']} for current*)" if plan["rho_current_extra"] else ""))
    log(f"  kappa   : {', '.join(f'{k:g}' for k in kappas)}   cap {plan['cap']:g}s")
    hdr = "tier".ljust(10) + "".join(m.rjust(w + 2) for m in methods) + "total".rjust(9)
    log("  " + hdr)
    log("  " + "-" * len(hdr))
    seen_tiers = tiers
    for t in seen_tiers:
        cells = [counts.get((t, m), 0) for m in methods]
        log("  " + t.ljust(10) + "".join(str(c).rjust(w + 2) for c in cells)
            + str(sum(cells)).rjust(9))
    tot = [sum(counts.get((t, m), 0) for t in seen_tiers) for m in methods]
    log("  " + "TOTAL".ljust(10) + "".join(str(c).rjust(w + 2) for c in tot)
        + str(sum(tot)).rjust(9))
    if skipped:
        by = {}
        for s in skipped:
            by[s["reason"]] = by.get(s["reason"], 0) + 1
        for reason, k in sorted(by.items()):
            log(f"  skipped {k}: {reason}")
    return dict(jobs=len(jobs), skipped=len(skipped), counts=counts, specs=len(specs))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_methods:
        for m in registered_methods():
            s = REGISTRY[m]
            print(f"{m:<24} base={s.base_name:<12} exact={s.exact} max_n={s.max_n} {s.kwargs}")
        return 0
    plan = resolve_plan(args)
    kappas = tuple(args.kappa) or (0.0,)
    specs = collect_specs(plan, args.regex)

    if args.dry_run:
        dry_run_report(specs, plan, kappas, Log(None, quiet=args.quiet))
        return 0

    run_id = args.run_id or f"{args.stage or 'run'}_{time.strftime('%Y%m%d_%H%M%S')}"
    run_dir = Path(_assert_safe_out(RESULTS_ROOT / run_id))
    run_dir.mkdir(parents=True, exist_ok=True)
    log = Log(run_dir / "run.log", quiet=args.quiet)
    try:
        log(f"run_id={run_id}  stage={args.stage}  tiers={plan['tiers']}  "
            f"methods={plan['methods']}  rho={plan['rho']}  cap={plan['cap']:g}s  "
            f"workers={args.workers}  scheduler={args.scheduler}/{args.start_method}")
        if plan["missing_methods"]:
            log(f"NOT REGISTERED (skipped): {plan['missing_methods']}")

        inst_rows: dict = {}
        if args.phase in ("1", "all"):
            inst_rows = phase1(specs, run_dir, workers=args.workers,
                               rescale=not args.no_rescale, bounds_cap=args.bounds_cap,
                               start_method=args.start_method, log=log)
        elif (run_dir / "instances.csv").exists():
            with open(run_dir / "instances.csv") as f:
                for r in csv.DictReader(f):
                    r["ok"] = str(r.get("ok")).lower() in ("true", "1")
                    inst_rows[r["instance"]] = r

        if args.phase in ("2", "all"):
            done = set()
            if args.resume and (run_dir / "rows.jsonl").exists():
                with open(run_dir / "rows.jsonl") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            done.add(json.loads(line).get("job_key"))
            jobs, skipped = make_jobs(
                specs, inst_rows, methods=plan["methods"], rho_list=plan["rho"], kappas=kappas,
                cap=plan["cap"], seed=args.seed, rescale=not args.no_rescale, lexi=args.lexi,
                save_assignments=args.save_assignments, run_id=run_id, run_dir=run_dir,
                max_iter=args.max_iter, rho_current_extra=plan["rho_current_extra"],
                done_keys=frozenset(done))
            skipped += [dict(instance="*", method=m, reason="method not in REGISTRY")
                        for m in plan["missing_methods"]]
            with open(_assert_safe_out(run_dir / "jobs.json"), "w") as f:
                json.dump(dict(run_id=run_id, stage=args.stage, plan=dict(
                    tiers=plan["tiers"], methods=plan["methods"], rho=list(plan["rho"]),
                    kappa=list(kappas), cap=plan["cap"], respect_state=plan["respect_state"],
                    rescale=not args.no_rescale, seed=args.seed, workers=args.workers,
                    scheduler=args.scheduler, start_method=args.start_method),
                    n_instances=len(specs), n_jobs=len(jobs),
                    jobs=[j.key() for j in jobs], skipped=skipped), f, indent=1,
                    default=_jsonable)
            phase2(jobs, run_dir, workers=args.workers, scheduler=args.scheduler,
                   start_method=args.start_method, log=log)

        if args.phase in ("3", "all"):
            phase3(run_dir, log)
        log(f"done -> {run_dir}")
    finally:
        log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
