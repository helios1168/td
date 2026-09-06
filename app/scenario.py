"""The saved scenario record.

The engines already have a scenario format: `tools/run_draw.py --scenario file.json` takes
exactly `{"fix": {NAME: [ST, ...]}, "anchor": {...}}` and rejects any other top-level key, and
fourteen such files live in `docs/artifacts/runs/scenarios/`.  This module does not replace it.
A `Scenario` is that object plus the run parameters and the business metadata around it; the
stripped `{fix, anchor}` object is written into the run directory at launch (`app/runner.py`),
so the driver still sees the format it validates and there is no second format to keep in sync.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from app import config

STATES: tuple[str, ...] = (
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT",
    "VT", "VA", "WA", "WV", "WI", "WY",
)

SLUG = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass(frozen=True)
class Scenario:
    """One saved scenario: what to pin, and how to run it.

    `fix` is a closed hand-drawn district (exactly those states, never touched by the solver);
    `anchor` is an open one (those states, plus whatever the solver adds).  `cuts` is the
    state-atom cut plan, `{"CA": 5, "NY,NJ": 3}`, meaningless to the power-cell engine.  Which
    of these an engine honours is recorded in `app/engines.py`, not assumed here.
    """
    name: str
    engine: str = "power-cells"
    k: int = 18
    seeds: str = "0-9"
    fix: dict[str, list[str]] = field(default_factory=dict)
    anchor: dict[str, list[str]] = field(default_factory=dict)
    cuts: dict[str, int] = field(default_factory=dict)
    notes: str = ""
    saved: str = ""

    @property
    def slug(self) -> str:
        return SLUG.sub("-", self.name).strip("-").lower() or "unnamed"

    @property
    def path(self) -> Path:
        return config.SCENARIOS / f"{self.slug}.json"

    def pins(self) -> dict[str, dict[str, list[str]]]:
        """The `{fix, anchor}` object the drivers accept, and nothing else."""
        return {"fix": self.fix, "anchor": self.anchor}


def validate(sc: Scenario) -> list[str]:
    """Everything `run_draw.py::load_scenario` would reject, caught before a 60-second run.

    Returns the problems as sentences; an empty list means the scenario is launchable.
    """
    problems: list[str] = []
    if not sc.name.strip():
        problems.append("The scenario needs a name.")
    if sc.k < 2:
        problems.append("k must be at least 2.")

    seen: dict[str, str] = {}
    for mode, districts in (("fix", sc.fix), ("anchor", sc.anchor)):
        for district, states in districts.items():
            if not district.strip():
                problems.append(f"A {mode} district has no name.")
            if not states:
                problems.append(f"District {district} has no states.")
            for st in states:
                if st not in STATES:
                    problems.append(f"{st!r} is not a state code.")
                elif st in seen:
                    problems.append(f"{st} is pinned to both {seen[st]} and {district}.")
                else:
                    seen[st] = district

    both = set(sc.fix) & set(sc.anchor)
    if both:
        problems.append(f"District(s) {', '.join(sorted(both))} are both fixed and anchored.")
    if len(sc.fix) + len(sc.anchor) > sc.k:
        problems.append(f"{len(sc.fix) + len(sc.anchor)} hand-drawn districts do not fit in k = {sc.k}.")
    return problems


def save(sc: Scenario) -> Path:
    """Write the record, stamped with the save time. Returns the path written."""
    sc = replace(sc, saved=datetime.now().isoformat(timespec="seconds"))
    sc.path.parent.mkdir(parents=True, exist_ok=True)
    sc.path.write_text(json.dumps(sc.__dict__, indent=2) + "\n")
    return sc.path


def load(path: Path) -> Scenario:
    return Scenario(**json.loads(path.read_text()))


def saved_scenarios() -> list[Scenario]:
    """Every saved scenario, newest first."""
    if not config.SCENARIOS.is_dir():
        return []
    return sorted((load(p) for p in config.SCENARIOS.glob("*.json")),
                  key=lambda s: s.saved, reverse=True)
