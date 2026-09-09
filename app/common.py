"""Shared state and helpers used by every tab: parsing, cached reads, and the run pickers and
launch helpers the tabs act on.

Nothing here imports `td`.  Every step is a driver in the solver virtualenv, launched detached
by `runner` and read back off disk by `store`, so a solve that takes ten minutes never blocks a
script rerun.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, mapfig, runner, steps, store

# The terminal maps and everything grown from one. A draw is an intermediate, shown on request.
MAP_KINDS = ("clip", "staff", "override", "split", "import")
FILLERS = ["theta", "full", "opportunity"]

# Refused by the floor, refuted by the solver, and searched without success are three different
# answers, and the UI has to keep them apart.
FAILURE_TEXT = {
    "infeasible": (
        "**No map satisfies these constraints.** The solver proved it: they admit no "
        "assignment at all, so widening the search would change nothing. Only a wider band or a "
        "different constraint can help."),
    "no_incumbent": (
        "**The search ended without a map, which is not the same as proving there is none.** "
        "The solver reached its time limit having never found a feasible point. A longer limit, "
        "or a wider band, may still find one."),
}
OTHER_FAILURE = ("**The step stopped without a map and without a reason of either kind.** The "
                 "log below has its own message.")

# The rerun modes as the driver takes them: the label, the `--mode` flag, and whether the hold
# set travels. B (i) sends an empty hold, so only the moved units are locked.
MODES = {
    "A: relabel only": ("A", False),
    "B (i): rerun, moved units locked": ("B", False),
    "B (ii): rerun, moved units locked plus the hold set": ("B", True),
}


# ------------------------------------------------------------------ parsing and validation
def parse_ks(text: str) -> tuple[list[int], list[str]]:
    ks: list[int] = []
    problems: list[str] = []
    for token in text.replace(",", " ").split():
        if not token.isdigit():
            problems.append(f"`{token}` is not a whole number.")
            continue
        k = int(token)
        if not 2 <= k <= 60:
            problems.append(f"k = {k} is outside 2 to 60.")
        elif k not in ks:
            ks.append(k)
    if not ks and not problems:
        problems.append("No k given.")
    return sorted(ks), problems


def pins_from_table(table: pd.DataFrame) -> tuple[dict, dict, list[str]]:
    """`fix` is closed, `anchor` is open. A state belongs to at most one pin either way."""
    fix: dict[str, list[str]] = {}
    anchor: dict[str, list[str]] = {}
    seen: dict[str, str] = {}
    problems: list[str] = []
    for row in table.to_dict("records"):
        name = str(row.get("district") or "").strip().upper()
        states = [s.strip().upper() for s in str(row.get("states") or "").split(",") if s.strip()]
        if not name and not states:
            continue
        if not name:
            problems.append(f"{', '.join(states)} pinned to no district.")
            continue
        for code in states:
            if len(code) != 2 or not code.isalpha():
                problems.append(f"`{code}` is not a two-letter state code.")
            elif code in seen:
                problems.append(f"{code} is pinned twice, to {seen[code]} and to {name}.")
            else:
                seen[code] = name
        (fix if row.get("mode") == "fix" else anchor)[name] = states
    return fix, anchor, problems


# ------------------------------------------------------------------ cached reads
@st.cache_data(show_spinner=False)
def _rows(path: str, mtime: float) -> list[dict]:
    return mapfig.load_rows(Path(path))


@st.cache_data(show_spinner=False)
def _geom(path: str, mtime: float) -> dict | None:
    return mapfig.load_geom(Path(path))


def _stamp(path: Path | None) -> tuple[str, float] | None:
    """Path and mtime, the cache key: a driver rewrites a file in place under the same name."""
    return (str(path), path.stat().st_mtime) if path and path.exists() else None


def _timings_path(run: Path) -> Path | None:
    """Where a run's `timings.json` sits, if the step recorded one and it was actually written."""
    rel = store.read_step(run).get("outputs", {}).get("timings")
    if not rel:
        return None
    path = (Path(run) / rel).resolve()
    return path if path.exists() else None


@st.cache_data(show_spinner=False)
def _wall(path: str, mtime: float) -> float | None:
    return json.loads(Path(path).read_text()).get("wall")


def runs_frame(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for run in paths:
        step = store.read_step(run)
        parent = step.get("parent")
        timings = _timings_path(run)
        rows.append({"run": store.label(run, config.APP_RESULTS),
                     "scenario": store.scenario_of(run, config.APP_RESULTS) or "",
                     "instance": store.member_of(run, config.APP_RESULTS) or "",
                     "parent": store.label(config.APP_RESULTS / parent, config.APP_RESULTS)
                     if parent and (config.APP_RESULTS / parent / store.STEP).exists() else "",
                     "status": store.status(run),
                     "failure": (store.failure(run) or {}).get("reason", ""),
                     "wall (s)": round(_wall(*_stamp(timings)), 1) if timings else None,
                     "directory": run.name})
    return pd.DataFrame(rows)


def show_failure(run: Path) -> None:
    fail = store.failure(run)
    if fail:
        st.error(FAILURE_TEXT.get(fail.get("reason", ""), OTHER_FAILURE))


# ------------------------------------------------------------------ runs the child tabs act on
def _json(path: Path | None) -> dict | None:
    return json.loads(path.read_text()) if path and path.exists() else None


@st.cache_data(show_spinner=False, max_entries=8)
def _figure(stamp, geom_stamp, marked: tuple[str, ...], label: str):
    """A figure with no click handling, cached on the same key its inputs are read under.

    The Map tab builds its own uncached, because it reads a selection back off the trace order.
    Reps and Compare draw two or three more figures on every script rerun and only look at them.
    """
    geom = _geom(*geom_stamp) if geom_stamp else None
    return mapfig.figure(_rows(*stamp), geom, highlight_zips=set(marked), highlight_label=label)


_UNSET = object()


def current_scenario() -> str | None:
    """The sidebar's scenario picker: newest scenario first, sticky in
    `st.session_state["scenario"]` across reruns. The Scenarios tab hands over a freshly
    launched scenario by setting `scenario-pending` and calling `st.rerun()`; that has to be
    read and written into the widget's own key before the widget is built, since a widget's key
    cannot be written once the widget exists. The legacy group (`None`) reads as "older runs".
    Renders nothing and returns `None` when the store holds no runs at all."""
    groups = store.scenarios(config.APP_RESULTS)
    if not groups:
        return None
    pending = st.session_state.pop("scenario-pending", None)
    if pending is not None:
        st.session_state["scenario"] = pending
    options = [slug for slug, _ in groups]
    return st.sidebar.selectbox(
        "Scenario", options, index=0, key="scenario",
        format_func=lambda slug: slug if slug is not None else "older runs")


def map_runs(scenario=_UNSET) -> list[Path]:
    """Every discovered run with a table on disk, newest first. A draw is included: staffing or
    an override on the intermediate is a fair thing to ask for, only never the default. With no
    argument, every run in the store; passing a scenario slug (or `None` for the legacy group)
    keeps only that scenario's runs."""
    runs = [run for run in store.discover(config.APP_RESULTS)
            if store.table_path(run) is not None]
    if scenario is _UNSET:
        return runs
    return [run for run in runs if store.scenario_of(run, config.APP_RESULTS) == scenario]


def label_run(run: Path) -> str:
    return store.label(run, config.APP_RESULTS)


def k_for(run: Path) -> int:
    """The district count a child run is filed under: the parent's k, or, for a table that
    carries none in its lineage, the number of districts the table has."""
    k = store.k_of(run, config.APP_RESULTS)
    if k is not None:
        return k
    table = store.table_path(run)
    rows = _rows(*_stamp(table)) if table else []
    return len({row["district"] for row in rows if row.get("district")})


def pick_map(label: str, key: str) -> Path | None:
    """The picker every child tab opens with, defaulting to whatever the Map tab is showing,
    filtered to the sidebar's current scenario (`current_scenario`'s widget, read back off its
    own key rather than built a second time)."""
    runs = map_runs(st.session_state.get("scenario"))
    if not runs:
        st.info(f"No finished run under {config.APP_RESULTS} yet. Launch a grid first.")
        return None
    current = st.session_state.get("map-run")
    index = runs.index(current) if current in runs else 0
    return st.selectbox(label, runs, index=index, format_func=label_run, key=key)


def open_on_map(run: Path) -> None:
    """`on_click` for the buttons that hand a child run to the Map tab.

    It has to be a callback: session state under a widget's key cannot be written once that
    widget exists, and the Map tab's selectbox is built earlier in the same script pass.
    """
    st.session_state["map-run"] = run


def instance_of(run: Path) -> Path:
    """The instance this map was drawn from, read off its lineage. A hand-imported table
    carries none, and then the configured default is the only answer available."""
    for step_run in reversed(store.lineage(run, config.APP_RESULTS)):
        name = store.read_step(step_run).get("params", {}).get("instance")
        if name:
            return Path(name)
    return config.INSTANCE


def newest_child(run: Path, kind: str) -> Path | None:
    for child in store.children(run, config.APP_RESULTS):
        if store.read_step(child).get("kind") == kind:
            return child
    return None


def launch_child(parent: Path, kind: str, params: dict, argv, outputs: dict) -> Path:
    """Create the child run directory, named from the parent's scenario member (or a bare `k`
    for a parent outside any scenario), register it and launch its driver with the geometry
    export chained behind it, so the map it writes arrives with polygons rather than as bare
    points. Returns the child directory.

    `argv` is a one-argument callable given the child directory once it exists and returning
    the driver's argv: every driver's argv embeds its own `--out` path, which does not exist
    until this function creates it, and a caller may need to write into the child directory
    (an edits file, say) before that path is final."""
    member = store.member_of(parent, config.APP_RESULTS) or f"k{k_for(parent)}"
    run = store.new_run_dir(config.APP_RESULTS, kind, member)
    built = argv(run)
    geom = steps.geom_argv(config.SOLVER_PYTHON, config.CODE, run / outputs["table"], run,
                           geo_cache=config.GEO_CACHE)
    store.write_step(run, kind=kind, parent=Path(parent).name, params=params, argv=built,
                     outputs={**outputs, "geom": "geom.json", "timings": "timings.json"},
                     scenario=store.scenario_of(parent, config.APP_RESULTS), member=member)
    runner.launch_chain([(run, built), (run, geom)], cwd=config.CODE,
                        env={**os.environ, "PYTHONHASHSEED": "0"})
    return run


# ------------------------------------------------------------------ compare helpers
def _mass(rows: list[dict]) -> dict[str, float]:
    per: dict[str, float] = {}
    for row in rows:
        if row["district"]:
            per[row["district"]] = per.get(row["district"], 0.0) + float(row["opportunity"] or 0.0)
    return per


def diff_frames(rows_a: list[dict], rows_b: list[dict]) -> dict:
    """The two tables joined on zip. A zip in only one of them takes no part in the diff and is
    reported apart, since a label it has on one side only cannot be said to have changed."""
    by_b = {r["zip"]: r for r in rows_b}
    pairs = [(ra, by_b[ra["zip"]]) for ra in rows_a if ra["zip"] in by_b]

    cells: dict[str, dict] = {}
    for ra, rb in pairs:
        cell = cells.setdefault(ra["state"], dict(a=set(), b=set(), mass=0.0, moved=0.0))
        cell["a"].add(ra["district"])
        cell["b"].add(rb["district"])
        mass = float(ra["opportunity"] or 0.0)
        cell["mass"] += mass
        if ra["district"] != rb["district"]:
            cell["moved"] += mass

    mass_a, mass_b = _mass(rows_a), _mass(rows_b)
    total_a, total_b = sum(mass_a.values()), sum(mass_b.values())
    return dict(
        relabelled=sum(1 for ra, rb in pairs if ra["district"] != rb["district"]),
        shared=len(pairs), only_a=len(rows_a) - len(pairs), only_b=len(rows_b) - len(pairs),
        states=pd.DataFrame([
            {"state": s, "districts in A": len(c["a"]), "districts in B": len(c["b"]),
             "share relabelled": c["moved"] / c["mass"] if c["mass"] else 0.0}
            for s, c in sorted(cells.items())]),
        districts=pd.DataFrame([
            {"district": d, "share A": mass_a.get(d, 0.0) / total_a if total_a else 0.0,
             "share B": mass_b.get(d, 0.0) / total_b if total_b else 0.0}
            for d in sorted(set(mass_a) | set(mass_b))]),
    )
