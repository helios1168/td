"""Map opens any run the store discovered and draws its zip table. It defaults to clipped maps
because the clip is the result: a draw table is an intermediate and never stands in for the
map its clip would have produced.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from app import config, mapfig, repdata, runner, steps, store
from app.common import MAP_KINDS, _geom, _rows, _stamp, instance_of, label_run, show_failure


def render_map() -> None:
    discovered = store.discover(config.APP_RESULTS)
    if not discovered:
        st.info(f"No runs under {config.APP_RESULTS} yet. Launch a grid first.")
        return

    scenario = st.session_state.get("scenario")
    scoped = [run for run in discovered
             if store.scenario_of(run, config.APP_RESULTS) == scenario]

    intermediates = st.toggle(
        "Show intermediates", value=False,
        help="Adds the draw tables. A draw is what the clip starts from, not the map.")
    kinds = (*MAP_KINDS, "draw") if intermediates else MAP_KINDS
    shown = [run for run in scoped if store.read_step(run).get("kind") in kinds]
    if not shown:
        st.info("No clipped map yet. Turn on intermediates to see the draws.")
        return

    run = st.selectbox("Instance", shown, format_func=lambda p: f"{label_run(p)} · {store.status(p)}",
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

    st.subheader("Rep territories, as sold today")
    reps = repdata.ensure(instance_of(run))
    if reps is None:
        return
    render_rep_section(run, reps, rows, geom_stamp)


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
        stage2_value = data.get("stage2_value")
        if stage2_value is not None:
            st.metric("Stage-2 value", f"{stage2_value:.4g}")
            st.caption(f"theta {data.get('stage2_theta')}, lambda {data.get('stage2_lam')}, "
                       f"filler capture {data.get('stage2_filler')}")
    else:
        winner = json.loads(metrics.read_text()).get("winner") or {}
        report = winner.get("balance_report")
        if report:
            st.write("Balance")
            st.json(report, expanded=False)
        else:
            st.caption("This step's metrics carry no balance report.")
        stage2_value = winner.get("stage2_value")
        if stage2_value is not None:
            params = store.read_step(run).get("params", {})
            st.metric("Stage-2 value", f"{stage2_value:.4g}")
            st.caption(f"theta {params.get('theta')}, lambda {params.get('lam')}, "
                       f"filler capture {params.get('filler_capture')}")
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


def render_rep_section(run: Path, reps: dict, rows: list[dict], geom_stamp) -> None:
    c1, c2, c3, c4 = st.columns(4)
    colour_label = c1.radio("Colour by", ["rep", "reps with book"], key=f"rep-colour-{run.name}")
    colour_by = "rep" if colour_label == "rep" else "n"
    focus_rep = c2.selectbox("Focus rep", [""] + reps["reps"],
                             format_func=lambda r: r or "none", key=f"rep-focus-{run.name}")
    show_contested = c3.toggle("Hatch contested", value=True, key=f"rep-contested-{run.name}")
    overlay = c4.toggle("Overlay this instance's districts", value=False,
                        key=f"rep-overlay-{run.name}")

    reps_stamp = _stamp(repdata.reps_path(instance_of(run)))
    fig = _rep_fig(reps_stamp, geom_stamp if overlay else None, colour_by, focus_rep,
                  show_contested, rows)
    st.plotly_chart(fig, width="stretch", key=f"rep-map-{run.name}")

    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for info in reps.get("zips", {}).values():
        counts[min(info.get("n", 0), 3)] += 1
    st.caption(f"Zips by rep count: 0 → {counts[0]}, 1 → {counts[1]}, 2 → {counts[2]}, "
               f"3+ → {counts[3]}.")
    st.caption("Hatch marks a cell where two or more reps hold book there. Colour separates "
               "neighbouring territories only; a rep's identity is in the hover and the focus "
               "selector, not the colour.")


@st.cache_data(show_spinner=False, max_entries=8)
def _rep_fig(reps_stamp, geom_stamp, colour_by: str, focus_rep: str, show_contested: bool,
            _rows_data: list[dict]):
    reps = repdata.load(*reps_stamp)
    geom = _geom(*geom_stamp) if geom_stamp else None
    return mapfig.rep_figure(reps, _rows_data, geom, colour_by=colour_by, focus_rep=focus_rep,
                             show_contested=show_contested, district_lines=geom is not None)
