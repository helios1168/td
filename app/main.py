"""The scenario app: launch a grid of maps, then read one on the map.

Five tabs.  Scenarios launches one chain per k (draw, then clip, then polygons) and watches
them; Map opens any run the store discovered and draws its zip table.  Reps, Overrides and
Compare arrive in wave 2.

Nothing here imports `td`.  Every step is a driver in the solver virtualenv, launched detached
by `runner` and read back off disk by `store`, so a solve that takes ten minutes never blocks a
script rerun.  The Map tab defaults to clipped maps because the clip is the result: a draw
table is an intermediate and never stands in for the map its clip would have produced.

Each tab's body is a function called inside its `with` block.  `st.stop()` would end the whole
script, so a tab with nothing to show returns instead and leaves the other four standing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, mapfig, runner, steps, store

st.set_page_config(page_title="Territory scenarios", layout="wide")
st.title("Territory scenarios")

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


def runs_frame(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for run in paths:
        step = store.read_step(run)
        rows.append({"run": run.name, "kind": step.get("kind", ""),
                     "parent": step.get("parent") or "", "status": store.status(run),
                     "failure": (store.failure(run) or {}).get("reason", "")})
    return pd.DataFrame(rows)


def show_failure(run: Path) -> None:
    fail = store.failure(run)
    if fail:
        st.error(FAILURE_TEXT.get(fail.get("reason", ""), OTHER_FAILURE))


# ------------------------------------------------------------------ scenarios
def render_scenarios() -> None:
    if not config.INSTANCES:
        st.error(f"No CONUS instance under {config.REPO}. Nothing can be launched.")
        return

    left, right = st.columns([2, 1])
    with left:
        instance = st.selectbox("Instance", config.INSTANCES, format_func=lambda p: p.name)
        name = st.text_input("Grid name", "grid", help="Goes into every run directory name.")
        ks_text = st.text_input("Districts (k)", ",".join(str(k) for k in config.KS))
        ks, ks_problems = parse_ks(ks_text)
        seeds = st.text_input("Seeds", config.SEEDS,
                              help="A value, a list, or a range a-b. More seeds, better draw.")
    with right:
        delta = st.number_input("delta (band half-width)", 0.0, 0.5, config.DELTA, step=0.01,
                                format="%.3f")
        workers = st.number_input("Workers per draw", 1, 12, config.WORKERS)
        time_limit = st.number_input("Clip time limit (s)", 30, 7200, config.TIME_LIMIT, step=30)
        theta = st.number_input("theta", 0.0, 1.0, config.THETA, step=0.05)
        lam = st.number_input("lambda", 0.0, 1.0, config.LAM, step=0.05)
        filler = st.selectbox("Filler capture", FILLERS, index=FILLERS.index(config.FILLER))

    st.subheader("Hand-drawn districts")
    st.caption("`fix` is closed, exactly those states. `anchor` is open, those states plus "
               "whatever the solver adds. States as codes, comma separated.")
    edited = st.data_editor(
        pd.DataFrame([{"district": "", "mode": "anchor", "states": ""}]),
        num_rows="dynamic", width="stretch", hide_index=True,
        column_config={"mode": st.column_config.SelectboxColumn(options=["fix", "anchor"])},
        key="pins")
    fix, anchor, pin_problems = pins_from_table(edited)

    problems = ks_problems + pin_problems
    for problem in problems:
        st.warning(problem)

    if st.button("Launch grid", type="primary", disabled=bool(problems)):
        chains = steps.grid(
            config.APP_RESULTS, name=name or "grid", ks=ks, delta=float(delta), seeds=seeds,
            workers=int(workers), theta=float(theta), lam=float(lam), filler_capture=filler,
            time_limit=int(time_limit),
            pins={"fix": fix, "anchor": anchor} if (fix or anchor) else None,
            python=config.SOLVER_PYTHON, repo=config.CODE, instance=instance,
            geo_cache=config.GEO_CACHE)
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        launched: list[str] = []
        for chain in chains:
            runner.launch_chain(chain, cwd=config.CODE, env=env)
            # A chain names its clip directory twice, once for the clip and once for the
            # geometry export that follows it in the same directory.
            launched += [run.name for run, _ in chain if run.name not in launched]
        st.success(f"{len(chains)} chains in flight:\n\n"
                   + "\n".join(f"- `{n}`" for n in launched))

    in_flight()

    st.subheader("Runs")
    discovered = store.discover(config.APP_RESULTS)
    if discovered:
        st.dataframe(runs_frame(discovered[:30]), width="stretch", hide_index=True)
    else:
        st.caption(f"No runs under {config.APP_RESULTS} yet.")


@st.fragment(run_every=5)
def in_flight() -> None:
    """Polled on its own, so a five-second refresh does not rerun the whole script."""
    live = [run for run in store.discover(config.APP_RESULTS)
            if store.status(run) in ("queued", "running")]
    st.subheader("In flight")
    if not live:
        st.caption("Nothing queued or running.")
        return
    for run in live:
        step = store.read_step(run)
        state = store.status(run)
        row, stop = st.columns([5, 1])
        row.write(f"**{run.name}** · {step.get('kind', '')} · {state} · "
                  f"started {step.get('started', '')}")
        pid = step.get("pid")
        if pid and state == "running" and stop.button("Cancel", key=f"cancel-{run.name}"):
            runner.cancel(int(pid))
            st.rerun(scope="fragment")
        with st.expander(f"Log · {run.name}"):
            st.code(runner.log_tail(run) or "(no output yet)")


# ------------------------------------------------------------------ map
def render_map() -> None:
    discovered = store.discover(config.APP_RESULTS)
    if not discovered:
        st.info(f"No runs under {config.APP_RESULTS} yet. Launch a grid first.")
        return

    intermediates = st.toggle(
        "Show intermediates", value=False,
        help="Adds the draw tables. A draw is what the clip starts from, not the map.")
    kinds = (*MAP_KINDS, "draw") if intermediates else MAP_KINDS
    shown = [run for run in discovered if store.read_step(run).get("kind") in kinds]
    if not shown:
        st.info("No clipped map yet. Turn on intermediates to see the draws.")
        return

    run = st.selectbox("Run", shown, format_func=lambda p: f"{p.name} · {store.status(p)}",
                       key="map-run")
    st.caption(" > ".join(p.name for p in store.lineage(run, config.APP_RESULTS)))

    table = store.table_path(run)
    if table is None or not table.exists():
        st.warning(f"This run is **{store.status(run)}** and has written no table yet.")
        show_failure(run)
        st.code(runner.log_tail(run) or "(no output yet)")
        return

    rows = _rows(*_stamp(table))
    geom_stamp = _stamp(store.geom_path(run))
    geom = _geom(*geom_stamp) if geom_stamp else None

    board, side = st.columns([3, 1])
    with side:
        render_side(run, geom)
    with board:
        render_board(run, rows, geom)


def render_side(run: Path, geom: dict | None) -> None:
    if geom is None:
        st.info("No polygons for this map yet, so it is drawn as points.")
        if st.button("Build polygons", key=f"geom-{run.name}"):
            argv = steps.geom_argv(config.SOLVER_PYTHON, config.CODE, store.table_path(run), run,
                                   geo_cache=config.GEO_CACHE)
            # A run whose driver never promised polygons (a draw) has no `geom` output to read
            # back, so register one before launching the export that fills it.
            step = store.read_step(run)
            store.update_step(run, outputs={**step["outputs"], "geom": "geom.json"})
            runner.launch(run, argv, cwd=config.CODE)
            st.success("Building. Reopen this tab when it is done.")

    metrics = store.metrics_path(run)
    if metrics is None or not metrics.exists():
        st.caption("No metrics beside this table.")
    elif store.read_step(run).get("kind") == "clip":
        data = json.loads(metrics.read_text())
        st.metric("States split", data.get("splits", 0))
        st.write(f"status `{data.get('status', 'unknown')}`")
        gap = data.get("mip_gap")
        if gap is not None:
            st.write(f"MIP gap {float(gap):.3%}")
        split_states = data.get("split_states") or []
        st.write("split: " + (", ".join(split_states) if split_states else "no state"))
    else:
        report = (json.loads(metrics.read_text()).get("winner") or {}).get("balance_report")
        if report:
            st.write("Balance")
            st.json(report, expanded=False)
        else:
            st.caption("This step's metrics carry no balance report.")
    show_failure(run)


def render_board(run: Path, rows: list[dict], geom: dict | None) -> None:
    fig = mapfig.figure(rows, geom)
    event = st.plotly_chart(fig, width="stretch", on_select="rerun",
                            selection_mode=("points",), key=f"map-{run.name}")
    for point in (event.get("selection") or {}).get("points", []):
        trace = fig.data[point.get("curve_number", 0)].name
        custom = point.get("customdata") or []
        if trace == mapfig.ZIPS and len(custom) >= 2:
            st.session_state["selected_zip"] = custom[0]
            st.session_state["selected_state"] = custom[1]
        elif trace == mapfig.HANDLES and custom:
            st.session_state["selected_state"] = custom[0]

    picked_zip = st.session_state.get("selected_zip")
    picked_state = st.session_state.get("selected_state")
    if picked_zip or picked_state:
        st.caption(f"Selected: zip {picked_zip or 'none'}, state {picked_state or 'none'}. "
                   "The Reps and Overrides tabs read this.")
    else:
        st.caption("Click a zip or a state handle to select it.")


scenarios, map_tab, reps, overrides, compare = st.tabs(
    ["Scenarios", "Map", "Reps", "Overrides", "Compare"])

with scenarios:
    render_scenarios()

with map_tab:
    render_map()

with reps:
    st.info("Reps arrives in wave 2: kept and released editor, staffing, contestability, split.")

with overrides:
    st.info("Overrides arrives in wave 2: an edit list, Mode A relabel and the Mode B reruns.")

with compare:
    st.info("Compare arrives in wave 2: two maps side by side and their diff.")
