"""The engine registry — the one place that knows how to invoke a solver.

Every engine is a driver script in the solver venv that writes `<out>/k<kk>/draw.csv` and
`<out>/k<kk>/metrics.json`.  An entry records the driver, how to build its argv from a
`Scenario`, the environment it needs, and which scenario fields it actually honours — the two
engines here disagree about that, which is why it is recorded rather than assumed.  Adding a
third workstream's solver is one entry, provided it writes those two files.
"""
from __future__ import annotations

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
    )
}

DEFAULT = "power-cells"
