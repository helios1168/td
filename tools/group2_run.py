"""Run one Group 2 case with exact counts and conditional state-channel purity.

This experiment adapter decorates full_plan's model builder only during this process.
It preserves the working tree's staffing implementation and records its additional
constraints separately. The legacy state sweep is disabled because it can introduce
partial pure-channel coverage outside the MILP. Residual mass remains an explicit result.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Callable

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import full_plan
from td import channels
from td.solvers import level0
from td.solvers import milp_engines
from tools import group2_checkpoint, group2_initializer, group2_symmetry

# Colorado remains eligible as supporting territory, not a priority or required state.
GROUP2: list[str] = [str(state) for state in
                     "TX NY FL NJ IL AZ NC PA MI OH VA GA MD WA UT IN LA MN CT".split()]
COUNTS = {"N": 14, "WH": 11, "FI": 21}
PURE = {"N": ("N_WH", "N_FI"), "WH": ("WH",), "FI": ("FI",)}
SHARE_TOL = 1e-6


def constrain_problem(problem: level0.Level0Problem,
                      counts: dict[str, int], count_mode: str = "fixed") -> level0.Level0Problem:
    """Require full pure share whenever any pure slot contacts a state.

    For each pure slot j, sum_h y[s,h] >= z[s,j], with h ranging over
    that pure bundle. Existing channel coverage bounds give sum_h y[s,h] <= 1.
    Multiple districts may split that full share. Prior mixed coverage makes
    a new pure contact infeasible. Existing slot lower bounds are paired with
    upper bounds here: full_plan's fixed_used alone is only a count floor.
    """
    if count_mode not in ("fixed", "cap"):
        raise ValueError(f"Unknown count mode {count_mode}")
    lower, upper = problem.var_lb.copy(), problem.var_ub.copy()
    for bundle, count in counts.items():
        if bundle not in problem.slots:
            continue
        start, stop = problem.slots[bundle]
        if count < 0 or (count_mode == "fixed" and count > stop - start):
            raise ValueError(f"{bundle}: requested {count} slots, available {stop-start}")
        count = min(count, stop - start)
        if count_mode == "fixed":
            lower[problem.off_u + start:problem.off_u + start + count] = 1.0
        upper[problem.off_u + start + count:problem.off_u + stop] = 0.0

    rr: list[int] = []
    cc: list[int] = []
    vv: list[float] = []
    n_rows = 0
    for bundle in PURE:
        start, stop = problem.slots.get(bundle, (0, 0))
        for s in range(problem.n_state):
            for j in range(start, stop):
                yy = [problem.off_y + s * problem.k + h for h in range(start, stop)]
                rr.extend([n_rows] * (len(yy) + 1))
                cc.extend(yy + [problem.off_z + s * problem.k + j])
                vv.extend([1.0] * len(yy) + [-1.0])
                n_rows += 1
    rows = dict(problem.rows)
    matrix_shape = problem.A.shape
    assert matrix_shape is not None
    rows["conditional_purity"] = (matrix_shape[0], matrix_shape[0] + n_rows)
    extra = sparse.coo_matrix((vv, (rr, cc)), shape=(n_rows, problem.n_var)).tocsc()
    return dataclasses.replace(
        problem, A=sparse.vstack([problem.A, extra]).tocsc(),
        lb=np.concatenate([problem.lb, np.zeros(n_rows)]),
        ub=np.concatenate([problem.ub, np.full(n_rows, np.inf)]),
        var_lb=lower, var_ub=upper, rows=rows)


def drop_connectivity_for_diagnostic(problem: level0.Level0Problem) -> level0.Level0Problem:
    """Project out only SCF connectivity for a labeled feasibility diagnostic."""
    removed = {"root", "rz", "flow_tail", "flow_head", "net"}
    keep = np.ones(len(problem.lb), dtype=bool)
    for name in removed:
        if name not in problem.rows:
            raise ValueError(f"connectivity diagnostic needs row block {name!r}")
        lo, hi = problem.rows[name]
        keep[lo:hi] = False
    rows: dict[str, tuple[int, int]] = {}
    next_row = 0
    for name, (lo, hi) in problem.rows.items():
        if name in removed:
            continue
        size = int(keep[lo:hi].sum())
        rows[name] = (next_row, next_row + size)
        next_row += size
    upper = problem.var_ub.copy()
    upper[problem.off_r:problem.off_u] = 0.0
    return dataclasses.replace(problem, A=problem.A[keep].tocsc(), lb=problem.lb[keep],
                               ub=problem.ub[keep], var_ub=upper, rows=rows)


def drop_geography_for_diagnostic(problem: level0.Level0Problem) -> level0.Level0Problem:
    """Remove pair-distance rows while retaining all opportunity and purity rules."""
    if "cap_dist" not in problem.rows:
        return problem
    lo_drop, hi_drop = problem.rows["cap_dist"]
    keep = np.ones(len(problem.lb), dtype=bool)
    keep[lo_drop:hi_drop] = False
    rows: dict[str, tuple[int, int]] = {}
    next_row = 0
    for name, (lo, hi) in problem.rows.items():
        if name == "cap_dist":
            continue
        size = int(keep[lo:hi].sum())
        rows[name] = (next_row, next_row + size)
        next_row += size
    return dataclasses.replace(problem, A=problem.A[keep].tocsc(), lb=problem.lb[keep],
                               ub=problem.ub[keep], rows=rows)


def plan_audit(plan: dict[str, Any], case: str, count_mode: str = "fixed",
               supporting_states: bool = False) -> dict[str, Any]:
    shares: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: Counter[str] = Counter()
    for slot in plan["slots"]:
        if slot["used"]:
            counts[slot["bundle"]] += 1
            for state, share in slot["y"].items():
                shares[state][slot["bundle"]] += float(share)
    issues: list[dict[str, Any]] = []
    for state, per in shares.items():
        for pure, fine in PURE.items():
            own = per.get(pure, 0.0)
            mixed = sum(v for b, v in per.items()
                        if b != pure and set(fine).intersection(full_plan._bundle_channels(b)))
            if own > SHARE_TOL and (abs(own - 1.0) > SHARE_TOL or mixed > SHARE_TOL):
                issues.append(dict(state=state, channel=pure, pure_share=own,
                                   mixed_share=mixed))
    national = sorted(s for s, per in shares.items() if per.get("N", 0) > SHARE_TOL)
    return dict(counts=dict(counts), exact_counts=all(counts[b] == n for b, n in COUNTS.items()),
                counts_satisfied=all(counts[b] == n if count_mode == "fixed" else counts[b] <= n
                                     for b, n in COUNTS.items()),
                purity_violations=issues, national_states=national,
                outside_group2=[] if supporting_states else sorted(set(national) - set(GROUP2)),
                supporting_national_states=sorted(set(national) - set(GROUP2)),
                missing_required_states=sorted(set(GROUP2) - set(national)) if case == "all" else [],
                residual_share_sum=sum(float(v) for per in plan["per_state"].values()
                                       for v in per["residual_by_channel"].values()))


def realized_audit(path: Path, case: str, count_mode: str = "fixed",
                   supporting_states: bool = False) -> dict[str, Any]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    pure_mass: dict[tuple[str, str], float] = defaultdict(float)
    districts: dict[str, str] = {}
    residual = 0.0
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            mass = float(row["M_cell"] or 0.0)
            channel = "N" if row["channel"] in PURE["N"] else row["channel"]
            key = (row["state"], channel)
            totals[key] += mass
            if row["district"] not in ("", "other"):
                districts[row["district"]] = row["bundle"]
                if row["bundle"] == channel:
                    pure_mass[key] += mass
            else:
                residual += mass
    violations = []
    for (state, channel), total in totals.items():
        own = pure_mass[state, channel]
        if own > 1e-9 and total - own > max(1e-8, total * 1e-8):
            violations.append(dict(state=state, channel=channel, mass_outside_pure=total-own))
    national = sorted(s for (s, c), mass in pure_mass.items() if c == "N" and mass > 1e-9)
    counts = Counter(districts.values())
    return dict(counts=dict(counts), exact_counts=all(counts[b] == n for b, n in COUNTS.items()),
                counts_satisfied=all(counts[b] == n if count_mode == "fixed" else counts[b] <= n
                                     for b, n in COUNTS.items()),
                purity_violations=violations, residual_mass=residual,
                coverage_complete=residual <= 1e-8,
                national_states=national,
                supporting_national_states=sorted(set(national)-set(GROUP2)),
                outside_group2=[] if supporting_states else sorted(set(national)-set(GROUP2)),
                missing_required_states=sorted(set(GROUP2)-set(national)) if case == "all" else [])


def valid(audit: dict[str, Any]) -> bool:
    return (audit["counts_satisfied"] and not audit["purity_violations"]
            and not audit["outside_group2"] and not audit["missing_required_states"])


def planner_args(hub: Path, out: Path, case: str, seconds: float,
                 count_mode: str = "fixed", supporting_states: bool = False) -> list[str]:
    argv = [str(hub / "instance_descaled_v4_conus.json.gz"), "--out", str(out),
            "--geo-cache", str(hub / "data/geo"), "--route", "sequential", "--driver", "geo",
            "--priority", "N,WH,FI", "--k-fixed", "N=14,WH=11,FI=21", "--k-mode", count_mode,
            "--band-mode", "per-bundle", "--delta", "0.1", "--eta", "0.05",
            "--dist-max", "900", "--dist-max-state", "WA=1200",
            "--n-max", "6", "--max-splits", "CA=3,TX=2,NY=2,FL=2",
            "--band-break", "CA,TX,NY,FL", "--catch-all", "--catch-all-bundle", "all",
            "--other-floor", "0.5", "--plus-pair", "--warm", "none", "--anchor", "none",
            "--engine", "highs", "--strategy", "direct", "--threads", "2",
            "--time-limit", str(seconds), "--stage2-reservation", "none"]
    if not supporting_states:
        argv += ["--national-states", ",".join(GROUP2)]
    if case == "all":
        argv += ["--force-national", ",".join(GROUP2)]
    return argv


def group2_priority(problem: level0.Level0Problem) -> level0.Pass:
    """Maximize Group 2 national opportunity before nationwide N coverage."""
    priority = level0.cover_pass(problem, ["N"], name="cover_group2")
    for s, state in enumerate(problem.state_list):
        if state not in GROUP2:
            priority.c[problem.off_y + s * problem.k:problem.off_y + (s+1) * problem.k] = 0.0
    return priority


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def make_accelerated_runner(
    original_run: Callable[..., dict[str, Any]], *, checkpoint_dir: Path,
    resume_dir: Path | None, provenance: dict[str, Any], seed_seconds: float,
    heuristic_effort: float = 1.0,
) -> Callable[..., dict[str, Any]]:
    """Seed unchanged stage models and retain live incumbents without skipping solves."""
    store = group2_checkpoint.CheckpointStore(checkpoint_dir, provenance)
    resume = (group2_checkpoint.CheckpointStore(resume_dir, provenance)
              if resume_dir is not None else None)
    progress: list[dict[str, Any]] = []

    def flush() -> None:
        checkpoint_dir.parent.mkdir(parents=True, exist_ok=True)
        write_json(checkpoint_dir.parent / "stage_progress.json", progress)

    def run(problem: level0.Level0Problem, passes: list[level0.Pass],
            args: Any, stage: str, timings: Any, **kwargs: Any) -> dict[str, Any]:
        started = time.monotonic()
        record: dict[str, Any] = dict(stage=stage, status="starting", passes=[], seed={})
        progress.append(record)
        flush()
        candidate: np.ndarray | None = None
        if resume is not None:
            loaded = resume.latest(stage, problem)
            if loaded is not None:
                candidate = np.asarray(loaded["x"], dtype=float)
                record["seed"] = dict(source="checkpoint", status="loaded")
        if candidate is None and kwargs.get("warm") is None and seed_seconds > 0:
            seed = group2_initializer.build_group2_feasibility_start(
                problem, passes, time_limit=seed_seconds, threads=args.threads or 2)
            candidate = seed.vector
            record["seed"] = dict(source="purity_initializer", **seed.metadata)
        if candidate is not None:
            try:
                if not np.isfinite(candidate).all():
                    raise ValueError("seed contains non-finite values")
                level0.check_point(problem, candidate)
            except ValueError as exc:
                record["seed"].update(status="rejected", message=str(exc))
            else:
                kwargs["warm"] = candidate
                kwargs["warm_seconds"] = time.monotonic() - started
                record["seed"] = dict(record["seed"], validated=True)
                try:
                    path = store.save(stage, "seed", {"x": candidate}, problem)
                    record["seed"]["checkpoint"] = str(path)
                except (ValueError, OSError) as exc:
                    record["seed"]["checkpoint_error"] = str(exc)
        record["status"] = "solving"
        flush()
        original_solve = milp_engines.solve_problem
        pass_index = 0

        def solve(current: level0.Level0Problem, *a: Any, **kw: Any) -> dict[str, Any]:
            nonlocal pass_index
            pass_index += 1
            item: dict[str, Any] = dict(index=pass_index, status="running",
                                        live_incumbents=0)
            record["passes"].append(item)
            flush()
            pass_started = time.monotonic()
            prior_callback = kw.get("on_incumbent")

            def retain_incumbent(incumbent: dict[str, Any]) -> None:
                """Atomically retain each improving feasible point from the native solver."""
                if prior_callback is not None:
                    prior_callback(incumbent)
                try:
                    path = store.save(stage, f"pass_{pass_index:03d}_live", incumbent, problem)
                except (ValueError, OSError) as exc:
                    item["live_checkpoint_error"] = str(exc)
                else:
                    item["live_incumbents"] = int(item["live_incumbents"]) + 1
                    item["live_checkpoint"] = str(path)
                    for field in ("objective", "seconds", "splits"):
                        value = incumbent.get(field)
                        if (isinstance(value, (int, float, np.integer, np.floating))
                                and np.isfinite(float(value))):
                            item[f"live_{field}"] = float(value)
                flush()

            kw["on_incumbent"] = retain_incumbent
            kw.setdefault("heuristic_effort", heuristic_effort)
            try:
                result = original_solve(current, *a, **kw)
                item["status"] = str(result.get("status", "returned"))
                for field in ("objective", "dual_bound", "nodes", "mip_gap"):
                    value = result.get(field)
                    if isinstance(value, (int, float, np.integer, np.floating)) and np.isfinite(float(value)):
                        item[field] = float(value)
                try:
                    path = store.save(stage, f"pass_{pass_index:03d}", result, problem)
                    item["checkpoint"] = str(path)
                except (ValueError, OSError) as exc:
                    # An unusable checkpoint must not replace or invalidate a solver result.
                    item["checkpoint_error"] = str(exc)
                return result
            except Exception as exc:
                item.update(status="failed", reason=getattr(exc, "reason", type(exc).__name__))
                raise
            finally:
                item["seconds"] = round(time.monotonic() - pass_started, 3)
                flush()

        milp_engines.solve_problem = solve
        try:
            result = original_run(problem, passes, args, stage, timings, **kwargs)
            record["status"] = "completed"
            return result
        except Exception as exc:
            record.update(status="failed", reason=getattr(exc, "reason", type(exc).__name__))
            raise
        finally:
            milp_engines.solve_problem = original_solve
            record["seconds"] = round(time.monotonic() - started, 3)
            flush()

    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["choose", "all"], required=True)
    parser.add_argument("--count-mode", choices=["fixed", "cap"], default="fixed")
    parser.add_argument("--supporting-states", action="store_true")
    parser.add_argument("--audit-only", action="store_true",
                        help="Refresh the ZIP audit of an existing completed realization")
    parser.add_argument("--hub", type=Path, default=Path(os.environ["TD_REPO"]))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--time-limit", type=float, default=180.0)
    parser.add_argument("--seed-time-limit", type=float, default=15.0,
                        help="Auxiliary purity-aware seed budget per stage; 0 disables seeding")
    parser.add_argument("--heuristic-effort", type=float, default=1.0,
                        help="HiGHS primal heuristic effort in [0,1] for production passes")
    parser.add_argument("--diagnostic-drop-connectivity", action="store_true",
                        help="Diagnostic only: remove SCF contiguity, retaining business bounds")
    parser.add_argument("--diagnostic-drop-geography", action="store_true",
                        help="Diagnostic only: remove state-distance rows")
    parser.add_argument("--resume-checkpoints", type=Path,
                        help="Prior checkpoints directory; compatible points seed fresh solves")
    args = parser.parse_args(argv)
    if not np.isfinite(args.seed_time_limit) or args.seed_time_limit < 0:
        parser.error("--seed-time-limit must be finite and nonnegative")
    if not np.isfinite(args.heuristic_effort) or not 0.0 <= args.heuristic_effort <= 1.0:
        parser.error("--heuristic-effort must be finite and in [0,1]")
    out = args.out.resolve()
    if args.audit_only:
        audit = realized_audit(out / "assignment.csv", args.case, args.count_mode,
                               args.supporting_states)
        report = json.loads((out / "run_status.json").read_text())
        report.update(status="completed" if valid(audit) else "rejected_realized_purity",
                      realized_audit=audit,
                      audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        write_json(out / "realized_purity.json", audit)
        write_json(out / "run_status.json", report)
        print(json.dumps(report, allow_nan=False))
        return 0 if valid(audit) else 1
    out.mkdir(parents=True, exist_ok=False)
    args.hub = args.hub.resolve()
    os.environ["TD_GAZ_VINTAGE"] = "2025"
    os.environ["TD_ZCTA_SHP"] = str(args.hub / "data/tiger/2025/tl_2025_us_zcta520.shp")
    command = planner_args(args.hub, out, args.case, args.time_limit, args.count_mode,
                           args.supporting_states)
    sources = [Path(__file__), ROOT / "tools/full_plan.py", ROOT / "tools/plan_realise.py",
               ROOT / "td/solvers/level0.py", ROOT / "td/stage2_state.py",
               ROOT / "tools/group2_checkpoint.py", ROOT / "tools/group2_initializer.py",
               ROOT / "tools/group2_symmetry.py",
               ROOT / "td/solvers/milp_engines.py"]
    provenance = dict(
        input_sha256=hashlib.sha256((args.hub / "instance_descaled_v4_conus.json.gz").read_bytes()).hexdigest(),
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    write_json(out / "run_request.json", dict(
        case=args.case, count_mode=args.count_mode, requested_counts=COUNTS,
        group2_states=GROUP2, supporting_states_allowed=args.supporting_states,
        national_pool="CONUS" if args.supporting_states else GROUP2, planner_argv=command,
        **provenance,
        seed_time_limit=args.seed_time_limit,
        heuristic_effort=args.heuristic_effort,
        diagnostic_drop_connectivity=args.diagnostic_drop_connectivity,
        diagnostic_drop_geography=args.diagnostic_drop_geography,
        resume_checkpoints=str(args.resume_checkpoints.resolve()) if args.resume_checkpoints else None,
        additions=["conditional purity rows for N, WH and FI",
                   "count lower and upper bounds" if args.count_mode == "fixed" else "count upper bounds"],
        state_sweep=False, other_first=[], greedy_anchors=False,
        terminal_rematch=True, stage2_reservation="none", gazetteer_vintage="2025"))
    started = time.monotonic()
    report: dict[str, Any] = dict(case=args.case, count_mode=args.count_mode,
                                status="running", phase="planning",
                                checkpoint_directory=str(out / "checkpoints"),
                                progress_file=str(out / "stage_progress.json"))
    write_json(out / "run_status.json", report)
    original = full_plan._build
    original_passes = full_plan._pass_list
    original_run = full_plan._run_passes

    def build(*a: Any, **kw: Any) -> level0.Level0Problem:
        problem = constrain_problem(original(*a, **kw), COUNTS, args.count_mode)
        if args.diagnostic_drop_connectivity:
            problem = drop_connectivity_for_diagnostic(problem)
        if args.diagnostic_drop_geography:
            problem = drop_geography_for_diagnostic(problem)
        if args.diagnostic_drop_connectivity or args.diagnostic_drop_geography:
            return problem
        return (group2_symmetry.canonicalize_slot_symmetry(problem, "N")
                if "N" in problem.slots else problem)

    def passes(problem: level0.Level0Problem, *a: Any, **kw: Any) -> list[level0.Pass]:
        result = original_passes(problem, *a, **kw)
        if args.supporting_states and "N" in problem.slots:
            result.insert(0, group2_priority(problem))
        return result

    try:
        with (out / "step_full_plan.log").open("w") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                try:
                    full_plan._build = build
                    full_plan._pass_list = passes
                    full_plan._run_passes = make_accelerated_runner(
                        original_run, checkpoint_dir=out / "checkpoints",
                        resume_dir=args.resume_checkpoints, provenance=provenance,
                        seed_seconds=args.seed_time_limit,
                        heuristic_effort=args.heuristic_effort)
                    full_plan.main(command)
                finally:
                    full_plan._build = original
                    full_plan._pass_list = original_passes
                    full_plan._run_passes = original_run
        audit = plan_audit(json.loads((out / "plan.json").read_text()), args.case, args.count_mode,
                           args.supporting_states)
        write_json(out / "plan_purity.json", audit)
        if not valid(audit):
            raise ValueError("Plan failed exact-count or purity audit")
        report["phase"] = "realization"
        write_json(out / "run_status.json", report)
        cmd = [sys.executable, "-u", str(ROOT / "tools/plan_realise.py"), str(out),
               "--geo-cache", str(args.hub / "data/geo"), "--sweep-zips",
               "--split-cut", "contiguous", "--split-cut-bundles", ",".join(channels.BUNDLES),
               "--stage2-rematch"]
        with (out / "step_plan_realise.log").open("w") as log:
            subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        audit = realized_audit(out / "assignment.csv", args.case, args.count_mode,
                               args.supporting_states)
        write_json(out / "realized_purity.json", audit)
        report.update(status="completed" if valid(audit) else "rejected_realized_purity",
                      realized_audit=audit)
    except Exception as exc:
        failure = out / "failure.json"
        report.update(status="failed", exception=type(exc).__name__, message=str(exc))
        if failure.exists():
            report["solver_failure"] = json.loads(failure.read_text())
    finally:
        report["seconds"] = round(time.monotonic() - started, 3)
        write_json(out / "run_status.json", report)
    print(json.dumps(report, allow_nan=False), flush=True)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
