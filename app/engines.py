"""The engine registry — the one place that knows how to invoke a solver.

Every engine is a driver script in the solver venv that writes `<out>/k<kk>/draw.csv` and
`<out>/k<kk>/metrics.json`.  An entry records the driver, how to build its argv from a
`Scenario`, the environment it needs, and which scenario fields it actually honours — the two
engines here disagree about that, which is why it is recorded rather than assumed.  Adding a
third workstream's solver is one entry, provided it writes those two files.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app import config
from app.scenario import Scenario


@dataclass(frozen=True)
class Engine:
    key: str
    label: str
    driver: str
    fields: frozenset[str]
    env: dict[str, str]
    argv: Callable[[Scenario, Path, Path | None], list[str]]
    note: str = ""
    done_glob: str = "k*/metrics.json"
    listed: bool = True

    def command(self, sc: Scenario, out: Path, pins: Path | None) -> list[str]:
        """The full argv, solver interpreter first. `pins` is the written `{fix, anchor}` file."""
        return [str(config.SOLVER_PYTHON), str(config.REPO / self.driver),
                str(config.INSTANCE), *self.argv(sc, out, pins)]


def _power_cells(sc: Scenario, out: Path, pins: Path | None) -> list[str]:
    argv = ["--k", str(sc.k), "--seeds", sc.seeds, "--workers", "8", "--out", str(out)]
    if pins is not None:
        argv += ["--scenario", str(pins)]
    return argv


def _state_atoms(sc: Scenario, out: Path, pins: Path | None) -> list[str]:
    argv = ["--k", str(sc.k), "--out", str(out)]
    for group, pieces in sc.cuts.items():
        argv += ["--cut", f"{group}:{pieces}"]
    return argv


def _anchored_count(st: str) -> int:
    """Districts anchored to `st`'s home in `config.STATE_SHARES`, or 0 when that file, or the
    state in it, is missing."""
    if not config.STATE_SHARES.exists():
        return 0
    data = json.loads(config.STATE_SHARES.read_text())
    return data.get("states", {}).get(st, {}).get("anchored", 0)


def _borders_headline(sc: Scenario, out: Path, pins: Path | None) -> list[str]:
    """The one hard-wired headline case: same run parameters as the shipped Track 2 anchored
    cell, so a diff against it is a diff against the headline and not a different experiment.
    Only `caps` and `delta` vary; a cap below a state's anchored count releases its anchors,
    since anchoring is what holds that state above its mass floor, not the floor itself."""
    argv = ["--draw", str(config.COMMITTED_DRAW), "--k", "18",
            "--delta", f"{sc.delta:g}", "--anchor-homes", "--eta", "0.01",
            "--rounds", "5", "--time-limit", "600",
            "--geo-cache", str(config.GEO_CACHE), "--no-maps", "--out", str(out)]
    for st, n in sorted(sc.caps.items()):
        argv += ["--cap", f"{st}={n}"]
        if n < _anchored_count(st):
            argv += ["--unanchor", st]
    return argv


REGISTRY: dict[str, Engine] = {
    e.key: e for e in (
        Engine(
            key="power-cells",
            label="Power cells (compact, not contiguous)",
            driver="tools/run_draw.py",
            fields=frozenset({"fix", "anchor", "seeds"}),
            env={},
            argv=_power_cells,
            note="Honours the hand-drawn districts. The territory is a power diagram, so all "
                 "three map renderings apply.",
        ),
        Engine(
            key="state-atoms",
            label="State atoms (contiguous, whole states cut only where oversized)",
            driver="tools/run_atoms.py",
            fields=frozenset({"cuts"}),
            env={"PYTHONHASHSEED": "0"},
            argv=_state_atoms,
            note="Takes a cut plan instead of hand-drawn districts, and refuses to start "
                 "without PYTHONHASHSEED=0 (its search tie-breaks on set iteration). Not a "
                 "power diagram, so only the zip-catchment map applies.",
        ),
        Engine(
            key="borders-headline",
            label="Borders headline (state-level minimum splits, one hard-wired case)",
            driver="tools/state_splits.py",
            fields=frozenset({"caps", "delta"}),
            env={},
            argv=_borders_headline,
            note="The Track 2 anchored delta=5% headline, capped per state and rerun. Not "
                 "listed in Define and run: it has its own tab.",
            done_glob="d*/splits.json",
            listed=False,
        ),
    )
}

DEFAULT = "power-cells"
