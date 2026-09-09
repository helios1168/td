"""Scenarios launches one chain per k (draw, then clip, then polygons) and watches them."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from app import config, runner, steps, store
from app.common import FILLERS, label_run, parse_ks, pins_from_table, runs_frame


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
