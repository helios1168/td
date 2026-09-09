"""Reps staffs a map and contests its districts."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, steps, store
from app.common import (FILLERS, _figure, _json, _rows, _stamp, instance_of, k_for, launch_child,
                        newest_child, open_on_map, pick_map, show_failure)


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
        parent_params = store.read_step(staff_run).get("params", {})
        theta = parent_params.get("theta", config.THETA)
        lam = parent_params.get("lam", config.LAM)
        filler = parent_params.get("filler_capture", config.FILLER)
        child = store.new_run_dir(config.APP_RESULTS, "split", k_for(staff_run))
        argv = steps.split_argv(config.SOLVER_PYTHON, config.CODE, instance_of(staff_run), child,
                                table=store.table_path(staff_run), district=district, reps=reps,
                                theta=theta, lam=lam, filler_capture=filler,
                                exact=bool(exact), time_limit=int(limit))
        launch_child(child, kind="split", parent=staff_run,
                     params=dict(district=district, reps=reps, exact=bool(exact),
                                 time_limit=int(limit), instance=str(instance_of(staff_run)),
                                 theta=theta, lam=lam, filler_capture=filler),
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
