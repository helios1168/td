"""full_grid.py: many `tools/full_plan.py` cells overnight, each ending in maps and a row.

    nohup .venv/bin/python3 -u tools/full_grid.py battery/grid/cells.json \\
        --out battery/results/full_problem/grid1 --concurrency 5 \\
        --geo-cache /Users/ntlee/projects/td/data/geo > battery/results/full_problem/grid1.log &

`CELLS.json` is `{"defaults": {flag: value}, "cells": [{"tag": "...", "flags": {...}}]}`, the
flags being `full_plan.py`'s long options with the dashes dropped (`band_lo`, `dist_max`,
`k_fixed`, `catch_all`, ...).  A cell's flags override the defaults; `True` becomes a bare
flag, `None` omits the option, and `instance` is the positional argument.

One worker per cell runs three steps in order (`full_plan.py`, `plan_realise.py`,
`plan_maps.py`), each as a subprocess logged to `<tag>/step_<name>.log`.  A step that exits
nonzero fails the cell and the worker moves to the next one; an overnight grid must not stop on
its worst cell.  The pool is threads, not processes: every step is a child process, so the
worker only waits on it, and one thread of control keeps `grid.csv` consistent with no lock.
Trap 18 is respected the same way: each `full_plan.py` gets `--threads 2` unless the cell
names its own, and no solve runs in this process at all.

`grid.csv` and `grid.md` are rewritten in full every time a cell ends, so a reader who opens
either mid-run always sees a complete table; `status.json` is rewritten every 30 seconds with
what is running and what is left.  `--resume` skips a cell that already has both `plan.json`
and `maps/metrics.csv`, and still puts its row in the table.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

STEPS = ("full_plan", "plan_realise", "plan_maps")

# a state's share of a slot below this is not coverage: `tools/plan_realise.py::RESIDUAL_TOL`,
# the same threshold level 2 folds a share away at, so `states_three` counts what a run
# actually assigns rather than what its realisation rounds off
SHARE_EPS = 1e-4

COLUMNS = ("tag", "status", "wall_s", "route", "band", "dist_max", "n_max", "radius_max",
           "k_fixed", "bundles", "cover_N", "cover_WH", "cover_FI", "cover_merged",
           "certified_passes", "districts", "districts_N", "districts_WH", "districts_FI",
           "splits_N", "splits_WH", "splits_FI", "states_three", "states_merged",
           "states_dropped", "states_other", "residual_mass", "max_extent_km",
           "mean_extent_km", "max_hull_area_km2", "min_mass_per_hull_area", "pieces_total",
           "staffed", "reps_idle", "staffing_value")


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cells", help="the cell list (JSON); see the module docstring")
    ap.add_argument("--out", required=True, help="grid directory; one subdirectory per cell")
    ap.add_argument("--concurrency", type=int, default=5, help="cells in flight (default 5)")
    ap.add_argument("--geo-cache", default=None,
                    help="filled into a cell's flags when it names no geo_cache of its own")
    ap.add_argument("--resume", action="store_true", default=False,
                    help="skip a cell that already has plan.json and maps/metrics.csv")
    ap.add_argument("--dry-run", action="store_true", default=False,
                    help="write each cell's planned commands to its step logs and run none "
                         "of them; what the tests drive, since a toy instance needs a "
                         "monkeypatched state_rook that no subprocess can be given")
    return ap


# ------------------------------------------------------------------------------- the cell list
def load_cells(path: str) -> list[dict]:
    """`[{tag, flags}, ...]` with the defaults folded into every cell's flags."""
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    defaults = spec.get("defaults") or {}
    cells = []
    seen = set()
    for cell in spec["cells"]:
        tag = str(cell["tag"])
        if tag in seen:
            raise ValueError(f"duplicate cell tag {tag!r}")
        seen.add(tag)
        flags = dict(defaults)
        flags.update(cell.get("flags") or {})
        cells.append(dict(tag=tag, flags=flags))
    return cells


def plan_argv(python: str, flags: dict, out_dir: str) -> list[str]:
    """The `full_plan.py` command for one cell.  `--out` and `--threads` are this runner's."""
    flags = {k: v for k, v in flags.items() if k != "out"}
    instance = flags.pop("instance", None)
    if instance is None:
        raise ValueError("every cell needs an `instance`, in its flags or in the defaults")
    argv = [python, "-u", os.path.join(HERE, "full_plan.py"), str(instance)]
    for name, value in flags.items():
        if value is None or value is False:
            continue
        opt = "--" + name.replace("_", "-")
        argv.append(opt)
        if value is not True:
            argv.append(str(value))
    if "threads" not in flags:
        argv += ["--threads", "2"]
    return argv + ["--out", out_dir]


def step_argvs(python: str, flags: dict, out_dir: str) -> list[tuple[str, list[str]]]:
    """The three commands of a cell, in the order they run."""
    geo_cache = flags.get("geo_cache")
    tail = ["--geo-cache", str(geo_cache)] if geo_cache else []
    return [
        (STEPS[0], plan_argv(python, flags, out_dir)),
        (STEPS[1], [python, "-u", os.path.join(HERE, "plan_realise.py"), out_dir] + tail),
        (STEPS[2], [python, "-u", os.path.join(HERE, "plan_maps.py"), out_dir] + tail),
    ]


# ------------------------------------------------------------------------------ running a cell
def _reason(out_dir: str) -> str:
    """`failure.json`'s own reason (`infeasible` is a proof, `no_incumbent` ran out of time)."""
    rec = read_json(os.path.join(out_dir, "failure.json"))
    return str(rec.get("reason") or "")


def run_cell(cell: dict, grid_dir: str, *, dry_run: bool, state: dict) -> dict:
    """Run one cell's three steps; returns `{tag, status, seconds}` and never raises."""
    tag = cell["tag"]
    out_dir = os.path.join(grid_dir, tag)
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    state[tag] = dict(status="running", step=STEPS[0], started=time.time())

    status = "ok"
    for name, argv in step_argvs(sys.executable, cell["flags"], out_dir):
        state[tag] = dict(state[tag], step=name)
        log = os.path.join(out_dir, f"step_{name}.log")
        try:
            with open(log, "w", encoding="utf-8") as fh:
                if dry_run:
                    fh.write(" ".join(argv) + "\n")
                    rc = 0
                else:
                    rc = subprocess.run(argv, stdout=fh, stderr=subprocess.STDOUT,
                                        cwd=os.path.dirname(HERE)).returncode
        except OSError as exc:                      # a command that could not start at all
            rc, status = 1, f"failed:{name}:{exc.__class__.__name__}"
        if rc != 0:
            if status == "ok":
                reason = _reason(out_dir) if name == STEPS[0] else ""
                status = f"failed:{name}:{reason}" if reason else f"failed:{name}"
            break
    if dry_run and status == "ok":
        status = "dry_run"

    rec = dict(tag=tag, status=status, seconds=time.time() - t0)
    state[tag] = dict(rec, step=None, finished=time.time())
    print(f"{tag}: {status} ({rec['seconds']:.0f}s)", flush=True)
    return rec


# ------------------------------------------------------------------------------- the grid table
def read_json(path: str) -> dict:
    """The file, or `{}`: a missing or half-written artifact leaves blanks, never an exception."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def read_csv(path: str) -> list[dict]:
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _num(text) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _agg(rows: list[dict], column: str, how) -> str:
    """Four significant figures, not four decimals: `mass_per_hull_area` runs around 1e-4 and
    a fixed-decimal round would collapse the whole column onto one value."""
    vals = [v for v in (_num(r.get(column)) for r in rows) if v is not None]
    return "" if not vals else float(f"{how(vals):.4g}")


def slot_stats(plan: dict) -> dict:
    """Used slots and split states per bundle.

    A slot is used when it carries a state; a state is split when it sends a slot less than all
    of itself, which is the count `tools/plan_realise.py` reports as `split_states`.
    """
    used: dict[str, int] = {}
    splits: dict[str, set] = {}
    for rec in plan.get("slots") or []:
        if not (rec.get("used") and rec.get("y")):
            continue
        bundle = rec["bundle"]
        used[bundle] = used.get(bundle, 0) + 1
        for state, share in rec["y"].items():
            if float(share) < 1.0 - SHARE_EPS:
                splits.setdefault(bundle, set()).add(state)
    return dict(used=used, splits={b: len(s) for b, s in splits.items()})


def state_shape(plan: dict) -> dict:
    """How each state came out: three slots, fewer, a residual, or more.

    Three is the plan the priority order asks for: one N slot, one WH, one FI.  Fewer means a
    merged bundle serves two of its groups at once; more means the state was split across extra
    slots.  A residual above `SHARE_EPS` on any channel outranks both: that state is not served.
    """
    counts = dict(states_three=0, states_merged=0, states_dropped=0, states_other=0)
    for row in (plan.get("per_state") or {}).values():
        residual = max((abs(float(v)) for v in
                        (row.get("residual_by_channel") or {}).values()), default=0.0)
        n = sum(1 for k, v in row.items()
                if k != "residual_by_channel" and float(v) > SHARE_EPS)
        if residual > SHARE_EPS:
            counts["states_dropped"] += 1
        elif n == 3:
            counts["states_three"] += 1
        elif n < 3:
            counts["states_merged"] += 1
        else:
            counts["states_other"] += 1
    return counts


def cell_row(tag: str, status: str, out_dir: str) -> dict:
    """One `grid.csv` row from whatever the cell directory holds."""
    params = read_json(os.path.join(out_dir, "params.json"))
    plan = read_json(os.path.join(out_dir, "plan.json"))
    timings = read_json(os.path.join(out_dir, "timings.json"))
    staffing = read_json(os.path.join(out_dir, "staffing.json"))
    realise = read_json(os.path.join(out_dir, "realise.json"))
    shapes = read_csv(os.path.join(out_dir, "maps", "metrics.csv"))

    row = {c: "" for c in COLUMNS}
    row.update(tag=tag, status=status)
    wall = _num(timings.get("wall"))
    if wall is not None:
        row["wall_s"] = round(wall, 1)
    row["route"] = params.get("route", "")
    if params.get("band_lo") is not None:
        row["band"] = f"{params['band_lo']}-{params.get('band_hi')}"
    for key in ("dist_max", "n_max", "radius_max"):
        row[key] = "" if params.get(key) is None else params[key]
    if params.get("k_fixed"):
        row["k_fixed"] = ",".join(f"{b}={n}" for b, n in sorted(params["k_fixed"].items()))
    if params.get("bundles"):
        row["bundles"] = ",".join(params["bundles"])

    # the last pass of each name wins: route R re-solves a stage, and the plan on disk is the
    # one the last solve left
    passes = plan.get("passes") or []
    for name in ("cover_N", "cover_WH", "cover_FI", "cover_merged"):
        vals = [_num(p.get("value")) for p in passes if p.get("name") == name]
        vals = [v for v in vals if v is not None]
        if vals:
            row[name] = round(vals[-1], 4)
    scored = [p for p in passes if p.get("name") != "greedy" and p.get("status") != "skipped"]
    if scored:
        row["certified_passes"] = f"{sum(1 for p in scored if p.get('certified'))}/{len(scored)}"

    stats = slot_stats(plan)
    if plan.get("slots"):
        row["districts"] = sum(stats["used"].values())
        for bundle in ("N", "WH", "FI"):
            row[f"districts_{bundle}"] = stats["used"].get(bundle, 0)
            row[f"splits_{bundle}"] = stats["splits"].get(bundle, 0)
    if plan.get("per_state"):
        row.update(state_shape(plan))

    masses = [_num(b.get("residual_mass")) for b in (realise.get("bundles") or {}).values()]
    masses = [m for m in masses if m is not None]
    if masses:
        row["residual_mass"] = round(sum(masses), 4)

    if shapes:
        row["max_extent_km"] = _agg(shapes, "extent_km", max)
        row["mean_extent_km"] = _agg(shapes, "extent_km", lambda v: sum(v) / len(v))
        row["max_hull_area_km2"] = _agg(shapes, "hull_area_km2", max)
        row["min_mass_per_hull_area"] = _agg(shapes, "mass_per_hull_area", min)
        pieces = [_num(r.get("pieces")) for r in shapes]
        pieces = [p for p in pieces if p is not None]
        if pieces:
            row["pieces_total"] = int(sum(pieces))

    if staffing:
        row["staffed"] = len(staffing.get("assignment") or {})
        row["reps_idle"] = len(staffing.get("unmatched_reps") or [])
        value = _num(staffing.get("value"))
        if value is not None:
            row["staffing_value"] = round(value, 4)
    return row


def rank_key(row: dict) -> tuple:
    """(states_three desc, max_extent_km asc, splits total asc); a blank ranks last either way."""
    three = _num(row.get("states_three"))
    extent = _num(row.get("max_extent_km"))
    splits = [_num(row.get(f"splits_{b}")) for b in ("N", "WH", "FI")]
    splits = [s for s in splits if s is not None]
    return (-(three if three is not None else float("-inf")),
            extent if extent is not None else float("inf"),
            sum(splits) if splits else float("inf"),
            row.get("tag", ""))


def write_grid(grid_dir: str, rows: list[dict]) -> None:
    """`grid.csv` in cell order and `grid.md` in rank order, both rewritten whole."""
    with open(os.path.join(grid_dir, "grid.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(COLUMNS))
        w.writeheader()
        w.writerows(rows)

    ranked = sorted(rows, key=rank_key)
    lines = ["| " + " | ".join(COLUMNS) + " |",
             "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    lines += ["| " + " | ".join(str(r.get(c, "")) for c in COLUMNS) + " |" for r in ranked]
    with open(os.path.join(grid_dir, "grid.md"), "w", encoding="utf-8") as fh:
        fh.write("# grid\n\nranked by states_three desc, max_extent_km asc, splits asc\n\n")
        fh.write("\n".join(lines) + "\n")


def write_status(grid_dir: str, state: dict, started: float) -> None:
    """Progress for a reader who has only the directory.

    `state` is written by the worker threads and read here, which is safe only because every
    tag is in it before the pool starts: a worker replaces a value and never adds a key, so
    the dict is never resized under this iteration.
    """
    cells = {tag: dict(state[tag]) for tag in sorted(state)}
    done = [t for t, r in cells.items() if r["status"] not in ("pending", "running")]
    with open(os.path.join(grid_dir, "status.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(
            started=started, now=time.time(), elapsed_s=round(time.time() - started, 1),
            total=len(cells), finished=len(done),
            failed=sorted(t for t in done if str(cells[t]["status"]).startswith("failed")),
            running=sorted(t for t, r in cells.items() if r["status"] == "running"),
            pending=sorted(t for t, r in cells.items() if r["status"] == "pending"),
            cells=cells), fh, indent=2, default=str)
        fh.write("\n")


# ------------------------------------------------------------------------------------ the loop
def _main(args) -> int:
    grid_dir = os.path.abspath(args.out)
    os.makedirs(grid_dir, exist_ok=True)
    cells = load_cells(args.cells)
    for cell in cells:
        if args.geo_cache and not cell["flags"].get("geo_cache"):
            cell["flags"]["geo_cache"] = os.path.abspath(args.geo_cache)

    started = time.time()
    # every tag before the pool starts, so a worker only ever replaces a value: see write_status
    state = {cell["tag"]: dict(status="pending", step=None) for cell in cells}
    finished: list[tuple[str, str]] = []           # (tag, status), in completion order

    todo = []
    for cell in cells:
        out_dir = os.path.join(grid_dir, cell["tag"])
        done = (os.path.exists(os.path.join(out_dir, "plan.json"))
                and os.path.exists(os.path.join(out_dir, "maps", "metrics.csv")))
        if args.resume and done:
            state[cell["tag"]] = dict(status="cached", step=None, finished=time.time())
            finished.append((cell["tag"], "cached"))
            print(f"{cell['tag']}: cached", flush=True)
        else:
            todo.append(cell)

    print(f"{len(todo)} cell(s) to run, {len(finished)} cached, concurrency "
          f"{args.concurrency} -> {grid_dir}", flush=True)
    rows = [cell_row(tag, status, os.path.join(grid_dir, tag)) for tag, status in finished]
    write_grid(grid_dir, rows)
    write_status(grid_dir, state, started)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(args.concurrency, 1)) as pool:
        pending = {pool.submit(run_cell, cell, grid_dir, dry_run=args.dry_run, state=state)
                   for cell in todo}
        while pending:
            done, pending = concurrent.futures.wait(
                pending, timeout=30.0, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                rec = future.result()
                finished.append((rec["tag"], rec["status"]))
                rows = [cell_row(t, s, os.path.join(grid_dir, t)) for t, s in finished]
                write_grid(grid_dir, rows)
            write_status(grid_dir, state, started)

    write_status(grid_dir, state, started)
    ok = [t for t, s in finished if not str(s).startswith("failed")]
    print(f"{len(ok)}/{len(cells)} cell(s) ended without a failed step "
          f"({time.time() - started:.0f}s); wrote {os.path.join(grid_dir, 'grid.csv')}",
          flush=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    return _main(build_argparser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
