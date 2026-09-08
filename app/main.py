"""The scenario app: launch a grid of maps, then read one on the map.

Five tabs.  Scenarios launches one chain per k (draw, then clip, then polygons) and watches
them; Map opens any run the store discovered and draws its zip table; Reps staffs a map and
contests its districts; Overrides edits one by hand or reruns it under the edit as a
constraint; Compare diffs two maps on the zips they share.

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
        parent = step.get("parent")
        rows.append({"run": store.label(run, config.APP_RESULTS),
                     "parent": store.label(config.APP_RESULTS / parent, config.APP_RESULTS)
                     if parent and (config.APP_RESULTS / parent / store.STEP).exists() else "",
                     "status": store.status(run),
                     "failure": (store.failure(run) or {}).get("reason", ""),
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


def map_runs() -> list[Path]:
    """Every discovered run with a table on disk, newest first. A draw is included: staffing or
    an override on the intermediate is a fair thing to ask for, only never the default."""
    return [run for run in store.discover(config.APP_RESULTS)
            if store.table_path(run) is not None]


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
    """The picker every child tab opens with, defaulting to whatever the Map tab is showing."""
    runs = map_runs()
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


def launch_child(run: Path, *, kind: str, parent: Path, params: dict, argv: list[str],
                 outputs: dict) -> None:
    """Register a child run and launch its driver with the geometry export chained behind it,
    so the map it writes arrives with polygons rather than as bare points."""
    geom = steps.geom_argv(config.SOLVER_PYTHON, config.CODE, run / outputs["table"], run,
                           geo_cache=config.GEO_CACHE)
    store.write_step(run, kind=kind, parent=Path(parent).name, params=params, argv=argv,
                     outputs={**outputs, "geom": "geom.json"})
    runner.launch_chain([(run, argv), (run, geom)], cwd=config.CODE,
                        env={**os.environ, "PYTHONHASHSEED": "0"})


# ------------------------------------------------------------------ scenarios
def render_scenarios() -> None:
    if not config.INSTANCES:
        st.error(f"No CONUS instance under {config.REPO}. Nothing can be launched.")
        return

    left, right = st.columns([2, 1])
    with left:
        instance = st.selectbox("Instance", config.INSTANCES, format_func=lambda p: p.name)
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
            config.APP_RESULTS, ks=ks, delta=float(delta), seeds=seeds,
            workers=int(workers), theta=float(theta), lam=float(lam), filler_capture=filler,
            time_limit=int(time_limit),
            pins={"fix": fix, "anchor": anchor} if (fix or anchor) else None,
            python=config.SOLVER_PYTHON, repo=config.CODE, instance=instance,
            geo_cache=config.GEO_CACHE)
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        launched: list[Path] = []
        for chain in chains:
            runner.launch_chain(chain, cwd=config.CODE, env=env)
            # A chain names its clip directory twice, once for the clip and once for the
            # geometry export that follows it in the same directory.
            launched += [run for run, _ in chain if run not in launched]
        st.success(f"{len(chains)} chains in flight:\n\n"
                   + "\n".join(f"- {label_run(run)}" for run in launched))

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
        row.write(f"**{label_run(run)}** · {state}")
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

    run = st.selectbox("Run", shown, format_func=lambda p: f"{label_run(p)} · {store.status(p)}",
                       key="map-run")
    st.caption(" > ".join(label_run(p) for p in store.lineage(run, config.APP_RESULTS))
               + f"  (`{run.name}`)")

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


# ------------------------------------------------------------------ reps
def render_reps() -> None:
    run = pick_map("Map", "reps-run")
    if run is None:
        return
    rows = _rows(*_stamp(store.table_path(run)))
    kind = store.read_step(run).get("kind")
    staff_run = run if kind == "staff" else newest_child(run, "staff")
    staffing = _json(store.metrics_path(staff_run)) if staff_run else None
    if staff_run is not None and staffing is None:
        st.caption(f"Staffing `{staff_run.name}` is {store.status(staff_run)}.")

    render_keep_release(run, rows, staffing)
    if staffing:
        st.divider()
        render_contest(run, staff_run, rows, staffing)
        st.divider()
        render_assignment(staffing)


def render_keep_release(run: Path, rows: list[dict], staffing: dict | None) -> None:
    st.subheader("Kept and released")
    known = staffing or {}
    universe = sorted(set(known.get("kept", [])) | set(known.get("released", [])))
    if not universe:
        universe = sorted({row["rep"] for row in rows if row["rep"]})

    if universe:
        released = st.multiselect(
            "Release", universe, default=[r for r in known.get("released", []) if r in universe],
            key=f"staff-released-{run.name}")
        st.caption(f"{len(universe) - len(released)} of {len(universe)} reps kept. A released "
                   "rep's book folds into the free book, which the reps who stay then value at "
                   "the filler rate.")
    else:
        st.caption("No staffing beside this map and no `rep` column in its table, so the app "
                   "cannot name the reps: opening the instance is the solver's job, not ours. "
                   "Staff everyone once and the roster comes back in `staffing.json`.")
        typed = st.text_area("Release these reps by hand", "", key=f"staff-typed-{run.name}",
                             help="Comma separated ids. Leave it empty to keep everyone.")
        released = [t.strip() for t in typed.replace("\n", ",").split(",") if t.strip()]

    cols = st.columns(3)
    theta = cols[0].number_input("theta", 0.0, 1.0, config.THETA, step=0.05, key="staff-theta")
    lam = cols[1].number_input("lambda", 0.0, 1.0, config.LAM, step=0.05, key="staff-lam")
    filler = cols[2].selectbox("Filler capture", FILLERS, index=FILLERS.index(config.FILLER),
                               key="staff-filler")
    if st.button("Staff" if universe else "Staff with everyone", type="primary", key="staff-go"):
        child = store.new_run_dir(config.APP_RESULTS, "staff", k_for(run))
        # An empty `--release` is what "nobody leaves" looks like to `tools/staff.py`: it splits
        # on the names it is given, so the empty list keeps the whole roster.
        argv = steps.staff_argv(config.SOLVER_PYTHON, config.CODE, instance_of(run), child,
                                table=store.table_path(run), keep=None, release=released,
                                theta=float(theta), lam=float(lam), filler_capture=filler)
        launch_child(child, kind="staff", parent=run,
                     params=dict(released=released, theta=float(theta), lam=float(lam),
                                 filler_capture=filler, instance=str(instance_of(run))),
                     argv=argv, outputs={"table": "draw.csv", "metrics": "staffing.json"})
        st.success(f"`{child.name}` in flight. It shows up here when it is done.")


def render_contest(run: Path, staff_run: Path, rows: list[dict], staffing: dict) -> None:
    st.subheader("Contestability")
    contest = staffing.get("contest") or {}
    districts = sorted(contest)
    if not districts:
        st.caption("This staffing reports no contest.")
        return
    picked = st.session_state.get("selected_zip")
    home = next((r["district"] for r in rows if r["zip"] == picked), None)
    district = st.selectbox("District", districts, key=f"reps-district-{staff_run.name}",
                            index=districts.index(home) if home in districts else 0,
                            help="Defaults to the district of the zip picked on the Map tab.")

    entry = contest[district]
    assigned = (staffing.get("assignment") or {}).get(district, "")
    cands = entry.get("candidates") or []
    if not cands:
        st.warning("No kept rep sells in this district, so it is left unstaffed.")
    else:
        share, gain = entry.get("share") or {}, entry.get("g") or {}
        frame = pd.DataFrame([{"rep": rep, "share of the district book": share.get(rep, 0.0),
                               "g": gain.get(rep, 0.0), "assigned": rep == assigned}
                              for rep in cands]).sort_values("share of the district book",
                                                             ascending=False)
        st.dataframe(frame, width="stretch", hide_index=True,
                     column_config={"share of the district book":
                                    st.column_config.NumberColumn(format="%.3f"),
                                    "g": st.column_config.NumberColumn(format="%.4g")})
        st.caption(f"Free book {entry.get('free_share', 0.0):.1%} of this district's total.")
    render_footprint(run, rows, district, cands)
    render_split(staff_run, district, cands)


def render_footprint(run: Path, rows: list[dict], district: str, cands: list[str]) -> None:
    here = [r for r in rows if r["district"] == district]
    reps_here = sorted({r["rep"] for r in here if r["rep"]})
    choices = ["the district"] + [r for r in cands if r in reps_here]
    # The key carries the run and the district: a stale selection under a fresh option list is
    # an error in streamlit, and both of those change the list.
    pick = st.selectbox("Show footprint", choices, key=f"reps-foot-{run.name}-{district}")
    if pick == "the district":
        marked = {r["zip"] for r in here}
        note = f"Highlighted: every zip of {district}."
    else:
        marked = {r["zip"] for r in here if r["rep"] == pick}
        note = (f"Highlighted: the zips of {district} this table already labels {pick}. That is "
                "the table's own labelling, not a sales footprint; per-zip rep sales live in "
                "the instance, which the app never opens.")
    fig = _figure(_stamp(store.table_path(run)), _stamp(store.geom_path(run)),
                  tuple(sorted(marked)), pick)
    st.plotly_chart(fig, width="stretch", key=f"reps-map-{run.name}")
    st.caption(note)


def render_split(staff_run: Path, district: str, cands: list[str]) -> None:
    st.markdown("**Split this district among its candidates**")
    if len(cands) < 2:
        st.caption("A split needs two candidates or more.")
        return
    reps = st.multiselect("Reps", cands, default=cands[:2], key=f"split-reps-{district}")
    cols = st.columns([2, 1, 1])
    exact = cols[1].toggle("Exact", value=False, key=f"split-exact-{district}",
                           help="SCIP on the Nash objective, warm started from the greedy "
                                "incumbent. Exact only when it closes the gap.")
    limit = cols[0].number_input("Time limit (s)", 5, 3600, 60, step=5,
                                 key=f"split-limit-{district}")
    if cols[2].button("Split", key=f"split-go-{district}", disabled=len(reps) < 2):
        child = store.new_run_dir(config.APP_RESULTS, "split", k_for(staff_run))
        argv = steps.split_argv(config.SOLVER_PYTHON, config.CODE, instance_of(staff_run), child,
                                table=store.table_path(staff_run), district=district, reps=reps,
                                exact=bool(exact), time_limit=int(limit))
        launch_child(child, kind="split", parent=staff_run,
                     params=dict(district=district, reps=reps, exact=bool(exact),
                                 time_limit=int(limit), instance=str(instance_of(staff_run))),
                     argv=argv, outputs={"table": "draw.csv", "metrics": "split.json"})
        st.success(f"`{child.name}` in flight.")

    for child in store.children(staff_run, config.APP_RESULTS):
        step = store.read_step(child)
        if step.get("kind") != "split" or step.get("params", {}).get("district") != district:
            continue
        report = _json(store.metrics_path(child))
        if report is None:
            st.caption(f"`{child.name}` is {store.status(child)}.")
            show_failure(child)
            return
        gap = report.get("gap")
        st.caption(f"`{child.name}`: {report.get('method', '')} / {report.get('status', '')}"
                   + (f", gap {gap:.2%}" if gap is not None else "")
                   + f", {report.get('n_zips', 0)} zips.")
        st.dataframe(pd.DataFrame([{"rep": rep, "share of the district's gain": share}
                                   for rep, share in sorted((report.get("shares") or {}).items())]),
                     width="stretch", hide_index=True,
                     column_config={"share of the district's gain":
                                    st.column_config.NumberColumn(format="%.3f")})
        st.button("Open this split on the Map tab", on_click=open_on_map, args=(child,),
                  key=f"split-open-{child.name}")
        return


def render_assignment(staffing: dict) -> None:
    st.subheader("Assignment")
    assignment = staffing.get("assignment") or {}
    gains = staffing.get("gains") or {}
    total = sum(gains.values())
    frame = pd.DataFrame([{"district": d, "rep": assignment.get(d, ""),
                           "gain share": gains.get(d, 0.0) / total if total else 0.0}
                          for d in sorted(set(assignment) | set(gains))])
    if not frame.empty:
        st.dataframe(frame, width="stretch", hide_index=True,
                     column_config={"gain share": st.column_config.NumberColumn(format="%.3f")})

    unstaffed = staffing.get("unstaffed_districts") or []
    unmatched = staffing.get("unmatched_reps") or []
    cols = st.columns(3)
    cols[0].metric("Districts staffed", len(assignment))
    cols[1].metric("Unstaffed", len(unstaffed))
    cols[2].metric("Reps with no district", len(unmatched))
    if unstaffed:
        st.warning("Unstaffed: " + ", ".join(unstaffed) + ". No kept rep sells there.")
    with st.expander(f"The {len(unmatched)} reps with no district"):
        st.write(", ".join(unmatched) or "none")


# ------------------------------------------------------------------ overrides
# The rerun modes as the driver takes them: the label, the `--mode` flag, and whether the hold
# set travels. B (i) sends an empty hold, so only the moved units are locked.
MODES = {
    "A: relabel only": ("A", False),
    "B (i): rerun, moved units locked": ("B", False),
    "B (ii): rerun, moved units locked plus the hold set": ("B", True),
}


def render_overrides() -> None:
    run = pick_map("Map to override", "over-run")
    if run is None:
        return
    rows = _rows(*_stamp(store.table_path(run)))
    districts = sorted({r["district"] for r in rows if r["district"]})
    states = sorted({r["state"] for r in rows if r["state"]})
    edits: list[dict] = st.session_state.setdefault("edits", [])

    st.subheader("Moves")
    cols = st.columns([1, 1, 1, 1])
    unit = cols[0].radio("Unit", ["state", "zip"], horizontal=True, key="over-unit")
    prefill = st.session_state.get("selected_state" if unit == "state" else "selected_zip") or ""
    # The key carries the prefill, so a fresh click on the Map tab resets the box to it rather
    # than leaving whatever was typed the last time standing.
    mid = cols[1].text_input("Id", prefill, key=f"over-id-{unit}-{prefill}")
    to = cols[2].selectbox("To district", districts, key="over-to")
    if cols[3].button("Add move", key="over-add") and mid.strip():
        edits.append({"unit": unit, "id": mid.strip(), "to": to})
        st.rerun()

    if edits:
        st.dataframe(pd.DataFrame(edits), width="stretch", hide_index=True)
        undo, clear = st.columns(2)
        if undo.button("Remove the last move", key="over-pop"):
            edits.pop()
            st.rerun()
        if clear.button("Clear the list", key="over-clear"):
            st.session_state["edits"] = []
            st.rerun()
    else:
        st.caption("No move yet. Click a zip or a state handle on the Map tab, or type an id.")

    st.subheader("Mode")
    label = st.radio("Mode", list(MODES), key="over-mode")
    mode, uses_hold = MODES[label]
    hold_states: list[str] = []
    hold_zips: list[str] = []
    if uses_hold:
        hold_states = st.multiselect("Hold these states at their parent labels", states,
                                     key="over-hold-states")
        typed = st.text_input("Hold these zips", "", key="over-hold-zips")
        hold_zips = [t.strip() for t in typed.replace(",", " ").split() if t.strip()]
    elif mode == "B":
        st.caption("Only the moved units are locked. Every other district is re-solved, so "
                   "under a draw parent the free districts are re-seeded and renamed.")

    if st.button("Run override", type="primary", disabled=not edits, key="over-go"):
        child = store.new_run_dir(config.APP_RESULTS, "override", k_for(run))
        payload = {"moves": list(edits), "hold": {"states": hold_states, "zips": hold_zips}}
        (child / "edits.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        argv = steps.override_argv(config.SOLVER_PYTHON, config.CODE, instance_of(run), child,
                                   table=store.table_path(run), edits=child / "edits.json",
                                   mode=mode, parent=run)
        launch_child(child, kind="override", parent=run,
                     params=dict(mode=mode, label=label, instance=str(instance_of(run)), **payload),
                     argv=argv, outputs={"table": "draw.csv", "metrics": "metrics.json"})
        st.success(f"`{child.name}` in flight.")

    st.divider()
    st.subheader("Result")
    render_override_result(run)


def render_override_result(run: Path) -> None:
    child = newest_child(run, "override")
    if child is None:
        st.caption("No override on this map yet.")
        return
    st.write(f"**{child.name}** · {store.status(child)}")
    metrics = _json(store.metrics_path(child))
    if metrics is None:
        show_failure(child)
        st.code(runner.log_tail(child) or "(no output yet)")
        return

    before = metrics.get("balance_before") or {}
    after = metrics.get("balance") or {}
    cols = st.columns(4)
    for col, field, name in ((cols[0], "max_dev_rel", "Worst deviation"),
                             (cols[1], "spread_rel", "Spread")):
        now, was = float(after.get(field, 0.0)), float(before.get(field, 0.0))
        col.metric(name, f"{now:.1%}", delta=f"{now - was:+.1%}", delta_color="inverse")
    cols[2].metric("Zips relabelled", (metrics.get("diff") or {}).get("zips_relabelled", 0))
    cols[3].metric("States split", len(metrics.get("states_split") or []))

    broken = sorted(d for d, ok in (metrics.get("contiguity") or {}).items() if not ok)
    if broken:
        st.warning(f"{len(broken)} district(s) whose owner states are not connected: "
                   + ", ".join(broken))
    else:
        st.success("Every district's owner states are connected.")

    honoured = metrics.get("edits_honoured")
    if isinstance(honoured, dict):
        st.write("Edits honoured")
        st.json(honoured, expanded=False)
    elif honoured is False:
        st.warning("Not every edit held. Under a clip parent a zip edit is a preference the "
                   "solver can outvote, never a bound.")

    if metrics.get("mode") == "B":
        st.caption(f"Engine `{metrics.get('engine', 'unknown')}`"
                   + (f", run `{metrics['engine_run']}`" if metrics.get("engine_run") else "") + ".")
        bounds = metrics.get("bounds_honoured")
        if bounds is not None:
            st.write("Bounds honoured")
            st.json(bounds, expanded=False)

    if store.table_path(child) is not None:
        st.button("Open this map on the Map tab", on_click=open_on_map, args=(child,),
                  key=f"over-open-{child.name}")


# ------------------------------------------------------------------ compare
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


def render_compare() -> None:
    runs = map_runs()
    if len(runs) < 2:
        st.info("Two finished maps are needed for a comparison.")
        return
    left, right = st.columns(2)
    a = left.selectbox("A", runs, index=1, format_func=label_run, key="cmp-a")
    b = right.selectbox("B", runs, index=0, format_func=label_run, key="cmp-b")
    stamp_a, stamp_b = _stamp(store.table_path(a)), _stamp(store.table_path(b))
    diff = diff_frames(_rows(*stamp_a), _rows(*stamp_b))

    cols = st.columns(3)
    cols[0].metric("Zips relabelled", diff["relabelled"])
    cols[1].metric("Zips in both", diff["shared"])
    cols[2].metric("Zips in one only", diff["only_a"] + diff["only_b"])
    if diff["only_a"] or diff["only_b"]:
        st.caption(f"{diff['only_a']} zip(s) only in A and {diff['only_b']} only in B take no "
                   "part in the counts above.")

    st.subheader("By state")
    st.dataframe(diff["states"], width="stretch", hide_index=True,
                 column_config={"share relabelled": st.column_config.NumberColumn(format="%.3f")})
    st.subheader("By district")
    st.dataframe(diff["districts"], width="stretch", hide_index=True,
                 column_config={"share A": st.column_config.NumberColumn(format="%.4f"),
                                "share B": st.column_config.NumberColumn(format="%.4f")})

    st.subheader("Side by side")
    board_a, board_b = st.columns(2)
    for column, run, stamp in ((board_a, a, stamp_a), (board_b, b, stamp_b)):
        with column:
            st.caption(run.name)
            st.plotly_chart(_figure(stamp, _stamp(store.geom_path(run)), (), ""),
                            width="stretch", key=f"cmp-map-{run.name}")


scenarios, map_tab, reps, overrides, compare = st.tabs(
    ["Scenarios", "Map", "Reps", "Overrides", "Compare"])

with scenarios:
    render_scenarios()

with map_tab:
    render_map()

with reps:
    render_reps()

with overrides:
    render_overrides()

with compare:
    render_compare()
