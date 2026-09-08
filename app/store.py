"""The step.json ledger for one run directory: how the app tells `draw`, `clip`, `staff`,
`override`, `split` and `import` runs apart, finds their parents and children, and reads back
what a driver has written so far.

A run directory holds one `step.json` (kind, parent, params, argv, pid, started, outputs) and
whatever a driver writes under it; the outputs never carry an absolute path, only one relative
to the run directory, so a run directory can be moved or copied along with its tree. This
module never runs a driver itself (`app.runner` does that) and never imports streamlit or
pandas, so the whole thing is testable from the solver venv.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import runner

STEP = "step.json"
FAILURE = "failure.json"

STAMP = "%Y%m%d_%H%M%S"


def new_run_dir(root: Path, kind: str, k: int) -> Path:
    """Create and return `<root>/<kind>_k<kk>_<YYYYmmdd_HHMMSS>`, made unique with a `-2`,
    `-3`, ... suffix when two runs of the same kind and k land in the same second. The name
    carries only what tells runs apart at a glance: the kind, the district count and when."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    base = f"{kind}_k{int(k):02d}_{datetime.now():{STAMP}}"
    name, n = base, 2
    while (root / name).exists():
        name = f"{base}-{n}"
        n += 1
    run = root / name
    run.mkdir()
    return run


def write_step(run: Path, *, kind: str, parent: str | None, params: dict, argv: list[str],
               outputs: dict) -> dict:
    """Write `step.json` for a run just created: no process has been launched yet, so `pid`
    and `started` are both `None` until `app.runner.launch`/`launch_chain` fills them in."""
    step = dict(kind=kind, parent=parent, params=params, argv=argv, pid=None, started=None,
               outputs=outputs)
    _write(run, step)
    return step


def read_step(run: Path) -> dict:
    return json.loads((Path(run) / STEP).read_text(encoding="utf-8"))


def update_step(run: Path, **fields) -> dict:
    """Merge `fields` into the existing `step.json` and rewrite it."""
    step = read_step(run)
    step.update(fields)
    _write(run, step)
    return step


def _write(run: Path, step: dict) -> None:
    (Path(run) / STEP).write_text(json.dumps(step, indent=2) + "\n", encoding="utf-8")


def discover(root: Path) -> list[Path]:
    """Every run directory under `root` that carries a `step.json`, newest first by the
    timestamp the name ends in (`<kind>_<slug>_<YYYYmmdd_HHMMSS>[-n]`), then by name, so a
    `clip_*` and a `draw_*` made in the same second stay together rather than grouping by kind."""
    root = Path(root)
    if not root.is_dir():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir() and (p / STEP).exists()]
    return sorted(dirs, key=lambda p: (_stamp(p.name), p.name), reverse=True)


def _stamp(name: str) -> str:
    """The `YYYYmmdd_HHMMSS` a run directory name ends in, uniqueness suffix dropped."""
    parts = name.split("_")
    return "_".join(parts[-2:]).split("-")[0] if len(parts) >= 3 else name


def k_of(run: Path, root: Path) -> int | None:
    """The district count a run was made for: its own `params.k`, else the nearest ancestor's,
    else the `k<kk>` in its name. `None` for a hand-imported table that says nothing."""
    for step_run in reversed(lineage(run, root)):
        k = read_step(step_run).get("params", {}).get("k")
        if k is not None:
            return int(k)
    match = re.search(r"_k(\d+)_", Path(run).name)
    return int(match.group(1)) if match else None


def label(run: Path, root: Path) -> str:
    """What a picker shows for a run: `k18 · clip · 2026-09-08 14:42:39`. Read from the ledger
    rather than the directory name, so runs made under an older naming read the same way."""
    step = read_step(run)
    k = k_of(run, root)
    when = step.get("started") or _stamp(Path(run).name)
    try:
        when = datetime.strptime(when, STAMP).isoformat(sep=" ", timespec="seconds")
    except ValueError:
        when = when.replace("T", " ")
    return f"{'k' + str(k) if k is not None else 'k?'} · {step.get('kind', '?')} · {when}"


def _output_path(run: Path, key: str) -> Path | None:
    rel = read_step(run).get("outputs", {}).get(key)
    if not rel:
        return None
    path = (Path(run) / rel).resolve()
    return path if path.exists() else None


def table_path(run: Path) -> Path | None:
    return _output_path(run, "table")


def metrics_path(run: Path) -> Path | None:
    return _output_path(run, "metrics")


def geom_path(run: Path) -> Path | None:
    return _output_path(run, "geom")


def failure(run: Path) -> dict | None:
    path = Path(run) / FAILURE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def status(run: Path) -> str:
    """`queued`, `running`, `done` or `failed`. A table on disk wins outright, since a driver
    that already wrote its output is done regardless of what its pid is doing; short of that, a
    live pid means running, and a dead one (or a failure.json with no table) means failed. A
    chain member started by `app.runner.launch_chain` shares its predecessor's pid, so it reads
    running for as long as the chain is still working its way to that member's own step."""
    if table_path(run) is not None:
        return "done"
    step = read_step(run)
    pid = step.get("pid")
    if pid is not None and runner._alive(pid):
        return "running"
    if (Path(run) / FAILURE).exists() or pid is not None:
        return "failed"
    return "queued"


def lineage(run: Path, root: Path) -> list[Path]:
    """The chain of runs from the root ancestor to `run` itself, root first."""
    root = Path(root)
    chain = [Path(run)]
    parent = read_step(chain[-1]).get("parent")
    while parent:
        chain.append(root / parent)
        parent = read_step(chain[-1]).get("parent")
    return list(reversed(chain))


def children(run: Path, root: Path) -> list[Path]:
    """Every run directly parented on `run`, newest first."""
    name = Path(run).name
    return [d for d in discover(root) if read_step(d).get("parent") == name]
