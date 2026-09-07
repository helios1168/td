"""Launching an engine, and rendering its maps.

A sweep takes about a minute, so the driver is started detached and the UI polls for its output
rather than waiting on it: a Streamlit script rerun must never be blocked by a solver, and the
run must survive the browser tab closing.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app import config, engines
from app.scenario import Scenario

LOG = "run.log"
LAUNCH = "launch.json"
PINS = "scenario.json"


def launch(sc: Scenario) -> Path:
    """Start the engine detached. Returns the run directory it will write into."""
    engine = engines.REGISTRY[sc.engine]
    out = config.APP_RESULTS / f"{sc.slug}_{datetime.now():%Y%m%d_%H%M%S}"
    out.mkdir(parents=True, exist_ok=True)

    pins: Path | None = None
    if {"fix", "anchor"} & engine.fields and (sc.fix or sc.anchor):
        pins = out / PINS
        pins.write_text(json.dumps(sc.pins(), indent=2) + "\n")

    argv = engine.command(sc, out, pins)
    log = (out / LOG).open("w")
    proc = subprocess.Popen(
        argv, cwd=config.REPO, stdout=log, stderr=subprocess.STDOUT,
        env={**os.environ, **engine.env}, start_new_session=True,
    )
    (out / LAUNCH).write_text(json.dumps({
        "scenario": asdict(sc), "engine": engine.key, "argv": argv,
        "pid": proc.pid, "started": datetime.now().isoformat(timespec="seconds"),
    }, indent=2) + "\n")
    return out


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def status(out: Path) -> str:
    """`running`, `done`, or `failed`, from the launch record and what is on disk."""
    if not (out / LAUNCH).exists():
        return "unknown"
    done = any(out.glob("k*/metrics.json"))
    if _alive(json.loads((out / LAUNCH).read_text())["pid"]):
        return "running"
    return "done" if done else "failed"


def cancel(out: Path) -> None:
    """Stop a running engine. The driver's process group goes with it (`start_new_session`)."""
    pid = json.loads((out / LAUNCH).read_text())["pid"]
    if _alive(pid):
        os.killpg(os.getpgid(pid), signal.SIGTERM)


def log_tail(out: Path, lines: int = 30) -> str:
    path = out / LOG
    return "\n".join(path.read_text().splitlines()[-lines:]) if path.exists() else ""


def launched_runs() -> list[Path]:
    """Every run this app started, newest first."""
    if not config.APP_RESULTS.is_dir():
        return []
    runs = [p for p in config.APP_RESULTS.iterdir() if (p / LAUNCH).exists()]
    return sorted(runs, key=lambda p: p.name, reverse=True)


def figure_dir(run: Path, k: int) -> Path:
    """One directory per run and k. Named from the path under `battery/results/`, so a historic
    `runs_20260904/baseline` cannot collide with an app run called `baseline`."""
    label = run.relative_to(config.RESULTS) if run.is_relative_to(config.RESULTS) else run
    return config.FIGURES / str(label).replace("/", "_") / f"k{k}"


def render_maps(run: Path, k: int, engine_key: str) -> Path:
    """Draw the maps for one k with `tools/us_maps.py`, the same renderer the notes use.

    `--regions` (the power diagram) is only meaningful for a center-based draw, so it is asked
    for only when the engine produced one; `--regions-voronoi` applies to any draw.

    `--regions-fixed` rides along with `--regions` for the same reason, and it is the only
    rendering that can show the zero-mismatch guarantee: it holds one diagram's centres and
    weights and draws the committed labelling and the snapped one on it, rather than
    recentroiding from whatever draw it is handed
    (`docs/OPTIONS_power-cell-contiguity.md` §4). It costs a further transportation LP or two,
    which is most of why rendering a power-cell run takes minutes rather than seconds.
    """
    draw = run / f"k{k}" / "draw.csv"
    out = figure_dir(run, k)
    out.mkdir(parents=True, exist_ok=True)
    argv = [str(config.SOLVER_PYTHON), str(config.REPO / "tools/us_maps.py"),
            str(config.INSTANCE), "--out", str(out),
            "--districts", str(draw), "--regions-voronoi", str(draw)]
    if engine_key == "power-cells":
        argv += ["--regions", str(draw), "--regions-fixed", str(draw)]
    subprocess.run(argv, cwd=config.REPO, check=True, capture_output=True, text=True)
    return out
