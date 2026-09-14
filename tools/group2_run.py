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
from typing import Any

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import full_plan
from td import channels
from td.solvers import level0

GROUP2 = "TX NY FL NJ IL AZ NC PA MI OH VA GA CO MD WA UT IN LA MN CT".split()
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
    rows["conditional_purity"] = (problem.A.shape[0], problem.A.shape[0] + n_rows)
    extra = sparse.coo_matrix((vv, (rr, cc)), shape=(n_rows, problem.n_var)).tocsc()
    return dataclasses.replace(
        problem, A=sparse.vstack([problem.A, extra]).tocsc(),
        lb=np.concatenate([problem.lb, np.zeros(n_rows)]),
        ub=np.concatenate([problem.ub, np.full(n_rows, np.inf)]),
        var_lb=lower, var_ub=upper, rows=rows)


def plan_audit(plan: dict[str, Any], case: str, count_mode: str = "fixed") -> dict[str, Any]:
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
                outside_group2=sorted(set(national) - set(GROUP2)),
                missing_required_states=sorted(set(GROUP2) - set(national)) if case == "all" else [],
                residual_share_sum=sum(float(v) for per in plan["per_state"].values()
                                       for v in per["residual_by_channel"].values()))


def realized_audit(path: Path, case: str, count_mode: str = "fixed") -> dict[str, Any]:
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
            if row["district"]:
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
                national_states=national, outside_group2=sorted(set(national)-set(GROUP2)),
                missing_required_states=sorted(set(GROUP2)-set(national)) if case == "all" else [])


def valid(audit: dict[str, Any]) -> bool:
    return (audit["counts_satisfied"] and not audit["purity_violations"]
            and not audit["outside_group2"] and not audit["missing_required_states"])


def planner_args(hub: Path, out: Path, case: str, seconds: float,
                 count_mode: str = "fixed") -> list[str]:
    argv = [str(hub / "instance_descaled_v4_conus.json.gz"), "--out", str(out),
            "--geo-cache", str(hub / "data/geo"), "--route", "sequential", "--driver", "geo",
            "--priority", "N,WH,FI", "--k-fixed", "N=14,WH=11,FI=21", "--k-mode", count_mode,
            "--band-mode", "per-bundle", "--delta", "0.1", "--eta", "0.05",
            "--national-states", ",".join(GROUP2), "--dist-max", "900", "--dist-max-state", "WA=1200",
            "--n-max", "6", "--max-splits", "CA=3,TX=2,NY=2,FL=2",
            "--band-break", "CA,TX,NY,FL", "--catch-all", "--catch-all-bundle", "all",
            "--other-floor", "0.5", "--plus-pair", "--warm", "none", "--anchor", "none",
            "--engine", "highs", "--strategy", "direct", "--threads", "2",
            "--time-limit", str(seconds), "--stage2-reservation", "none"]
    if case == "all":
        argv += ["--force-national", ",".join(GROUP2)]
    return argv


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["choose", "all"], required=True)
    parser.add_argument("--count-mode", choices=["fixed", "cap"], default="fixed")
    parser.add_argument("--hub", type=Path, default=Path(os.environ["TD_REPO"]))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--time-limit", type=float, default=180.0)
    args = parser.parse_args(argv)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    args.hub = args.hub.resolve()
    os.environ["TD_GAZ_VINTAGE"] = "2025"
    os.environ["TD_ZCTA_SHP"] = str(args.hub / "data/tiger/2025/tl_2025_us_zcta520.shp")
    command = planner_args(args.hub, out, args.case, args.time_limit, args.count_mode)
    sources = [Path(__file__), ROOT / "tools/full_plan.py", ROOT / "tools/plan_realise.py",
               ROOT / "td/solvers/level0.py", ROOT / "td/stage2_state.py"]
    write_json(out / "run_request.json", dict(
        case=args.case, count_mode=args.count_mode, requested_counts=COUNTS,
        national_pool=GROUP2, planner_argv=command,
        input_sha256=hashlib.sha256((args.hub / "instance_descaled_v4_conus.json.gz").read_bytes()).hexdigest(),
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        additions=["conditional purity rows for N, WH and FI",
                   "count lower and upper bounds" if args.count_mode == "fixed" else "count upper bounds"],
        state_sweep=False, other_first=[], greedy_anchors=False,
        terminal_rematch=True, stage2_reservation="none", gazetteer_vintage="2025"))
    started = time.monotonic()
    report: dict[str, Any] = dict(case=args.case, count_mode=args.count_mode,
                                status="running", phase="planning")
    write_json(out / "run_status.json", report)
    original = full_plan._build

    def build(*a: Any, **kw: Any) -> level0.Level0Problem:
        return constrain_problem(original(*a, **kw), COUNTS, args.count_mode)

    try:
        with (out / "step_full_plan.log").open("w") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                full_plan._build = build
                try:
                    full_plan.main(command)
                finally:
                    full_plan._build = original
        audit = plan_audit(json.loads((out / "plan.json").read_text()), args.case, args.count_mode)
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
        audit = realized_audit(out / "assignment.csv", args.case, args.count_mode)
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
