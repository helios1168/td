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

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Lowercase, `[a-z0-9-]` only, collapsed: the run-directory-safe form of a scenario name."""
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "run"


def new_run_dir(root: Path, kind: str, slug: str) -> Path:
    """Create and return `<root>/<kind>_<slug>_<timestamp>`, made unique with a `-2`, `-3`,
    ... suffix when two runs land in the same second."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    base = f"{kind}_{_slugify(slug)}_{datetime.now():%Y%m%d_%H%M%S}"
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
