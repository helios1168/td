"""Reading what an engine wrote.

Both stage-1 drivers (`tools/run_draw.py`, `tools/run_atoms.py`) write the same two files per k:
`<run>/k<kk>/draw.csv` (`zip,district`) and `<run>/k<kk>/metrics.json`.  That shared shape is the
seam the app depends on, so a new solver becomes readable here for free as long as it writes it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app import config


@dataclass(frozen=True)
class Run:
    """One engine output directory, plus the ks it holds."""
    path: Path
    ks: tuple[int, ...]

    @property
    def label(self) -> str:
        return str(self.path.relative_to(config.RESULTS))


def discover(root: Path | None = None, max_depth: int = 3) -> list[Run]:
    """Every directory under `root` holding at least one `k<kk>/metrics.json`, newest first."""
    root = root or config.RESULTS
    if not root.is_dir():
        return []
    found: dict[Path, list[int]] = {}
    for depth in range(1, max_depth + 1):
        for metrics in root.glob("/".join(["*"] * depth) + "/k*/metrics.json"):
            k_dir = metrics.parent
            if not k_dir.name[1:].isdigit():
                continue
            found.setdefault(k_dir.parent, []).append(int(k_dir.name[1:]))
    runs = [Run(path, tuple(sorted(ks))) for path, ks in found.items()]
    return sorted(runs, key=lambda r: r.path.stat().st_mtime, reverse=True)


def metrics(run: Run, k: int) -> dict:
    return json.loads((run.path / f"k{k}" / "metrics.json").read_text())


def draw_csv(run: Run, k: int) -> Path:
    return run.path / f"k{k}" / "draw.csv"
