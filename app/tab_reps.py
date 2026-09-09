"""Reps opens on the map with the proposed districts drawn over the incumbent rep layout,
then staffs one district or the whole map, contests a district, and shows before-and-after.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, mapfig, repdata, runner, staffdiff, steps, store
from app.common import (FILLERS, _figure, _geom, _json, _rows, _stamp, instance_of, label_run,
                        launch_child, open_on_map, show_failure)


# ------------------------------------------------------------------ cached figures
@st.cache_data(show_spinner=False, max_entries=8)
def _rep_fig(reps_stamp, rows_stamp, geom_stamp, colour_by, focus_rep, show_contested,
            district_lines, bbox):
    reps = repdata.load(*reps_stamp)
    rows = _rows(*rows_stamp) if rows_stamp else None
    geom = _geom(*geom_stamp) if geom_stamp else None
    return mapfig.rep_figure(reps, rows, geom, colour_by=colour_by, focus_rep=focus_rep,
                             show_contested=show_contested, district_lines=district_lines,
                             bbox=bbox)


@st.cache_data(show_spinner=False, max_entries=8)
def _staffed_fig(rows_stamp, geom_stamp, reps_stamp, staffing_stamp, bbox):
    reps = repdata.load(*reps_stamp)
    colours = mapfig.rep_colours(reps)
    geom = _geom(*geom_stamp) if geom_stamp else None
    staffing = _json(Path(staffing_stamp[0]))
    return mapfig.staffed_figure(_rows(*rows_stamp), geom, colours, staffing=staffing, bbox=bbox)


def render_reps(base_run: Path | None, named: list[Path], default_run: Path | None) -> None:
    if base_run is None:
        st.info("No runs for this instance yet.")
        return
    member = st.session_state.get("instance")

    pending = st.session_state.pop("reps-view-pending", None)
    if pending is not None:
        st.session_state["reps-view"] = pending

    preview = st.session_state.get("reps-preview")
    if preview is not None and not (Path(preview) / store.STEP).exists():
        st.session_state.pop("reps-preview", None)   # its directory is gone; self-heal
        preview = None

    options = [None] + named                          # None sentinel = "Clip (base)"
    current = st.session_state.get("reps-view")
    index = options.index(current) if current in options else 0

    def _label(r: Path | None) -> str:
        if r is None:
            return "Clip (base)"
        text = store.read_view(r).get("name", label_run(r))
        return text + ("  (default)" if r == default_run else "")

    picked = st.selectbox("View", options, index=index, format_func=_label, key="reps-view",
                          on_change=lambda: st.session_state.pop("reps-preview", None))
    view_run = preview if preview is not None else (base_run if picked is None else picked)
    is_base = picked is None and preview is None

    if store.table_path(view_run) is None:
        st.write(f"**{view_run.name}** · {store.status(view_run)}")
        show_failure(view_run)
        st.code(runner.log_tail(view_run) or "(no output yet)")
        return

    reps = repdata.ensure(instance_of(view_run))
    rows = _rows(*_stamp(store.table_path(view_run)))

    render_pane(view_run, is_base, reps, rows)

    if preview is not None and view_run == preview and not store.read_view(preview):
        st.divider()
        render_save(preview, member, default_run)

    staffing_run = store.staffing_run(view_run, config.APP_RESULTS)
    staffing = _json(store.metrics_path(staffing_run)) if staffing_run else None

    released, has_universe = render_keep_release(view_run, rows, staffing)
    render_scope(view_run, rows, released, has_universe)

    if staffing:
        st.divider()
        render_contest(view_run, staffing_run, rows, staffing, reps)
        st.divider()
        render_assignment(staffing, staffing_run)


def render_pane(view_run: Path, is_base: bool, reps: dict | None, rows: list[dict]) -> None:
    if reps is None:
        st.caption("Build rep territories (button above) to see the map and numbers here.")
        return
    reps_stamp = _stamp(repdata.reps_path(instance_of(view_run)))
    geom_stamp = _stamp(store.geom_path(view_run))
    rows_stamp = _stamp(store.table_path(view_run))
    if reps_stamp is None or rows_stamp is None:
        return

    if is_base:
        st.subheader("Proposed districts over the rep layout")
        cols = st.columns([2, 2, 1])
        colour_by = cols[0].radio("Colour by", ["rep", "n"], horizontal=True,
                                  format_func=lambda v: "reps with book" if v == "n" else "rep",
                                  key=f"reps-colourby-{view_run.name}")
        focus = cols[1].selectbox("Focus rep", [""] + reps.get("reps", []),
                                  key=f"reps-focus-{view_run.name}")
        hatch = cols[2].toggle("Hatch contested", value=True, key=f"reps-hatch-{view_run.name}")
        fig = _rep_fig(reps_stamp, rows_stamp, geom_stamp, colour_by, focus, hatch, True, None)
        st.plotly_chart(fig, width="stretch", key=f"reps-map-{view_run.name}")
        return

    st.subheader("The staffed map")
    staffing_run = store.staffing_run(view_run, config.APP_RESULTS)
    staffing_stamp = _stamp(store.metrics_path(staffing_run)) if staffing_run else None
    if staffing_stamp is None:
        st.caption(f"`{view_run.name}` carries no finished staffing in its own lineage.")
        return
    fig = _staffed_fig(rows_stamp, geom_stamp, reps_stamp, staffing_stamp, None)
    st.plotly_chart(fig, width="stretch", key=f"reps-map-{view_run.name}")

    staffing = _json(store.metrics_path(staffing_run))
    per_rep_rows = sorted(staffdiff.per_rep(reps, rows, staffing), key=lambda r: r["change"])
    only_changed = st.toggle("Only reps whose territory changed by more than 1 pt", value=True,
                             key=f"reps-changed-{view_run.name}")
    if only_changed:
        per_rep_rows = [r for r in per_rep_rows if abs(r["change"]) > 0.01]
    frame = pd.DataFrame([{"rep": r["rep"], "after": r["after"], "change": r["change"],
                           "districts": ", ".join(r["districts"])} for r in per_rep_rows])
    st.dataframe(frame, width="stretch", hide_index=True, column_config=_PCT_COLUMNS)


def render_save(run: Path, member: str, default_run: Path | None) -> None:
    st.markdown(f"**Preview: `{run.name}`** — unsaved; name it to keep it in the View list.")
    with st.form(f"view-save-{run.name}"):
        name = st.text_input("Name this view",
                             placeholder=f"{store.read_step(run).get('kind')} v1")
        make_default = st.checkbox(f"Make this the default for {store.member_label(member)}")
        submitted = st.form_submit_button("Save")
    if submitted:
        if not name.strip():
            st.warning("Name it first.")
            return
        store.write_view(run, config.APP_RESULTS, name=name.strip(),
                         default_for=(member if make_default else None))
        st.session_state.pop("reps-preview", None)
        st.session_state["reps-view-pending"] = run
        st.success(f"Saved as “{name.strip()}”.")
        st.rerun()


def _scope_label(run: Path) -> str:
    districts = store.read_step(run).get("params", {}).get("districts") or []
    return "whole map" if not districts else ", ".join(districts)


def render_keep_release(view_run: Path, rows: list[dict],
                        staffing: dict | None) -> tuple[list[str], bool]:
    st.subheader("Kept and released")
    known = staffing or {}
    universe = sorted(set(known.get("kept", [])) | set(known.get("released", [])))
    if not universe:
        universe = sorted({row["rep"] for row in rows if row["rep"]})

    if universe:
        released = st.multiselect(
            "Release", universe, default=[r for r in known.get("released", []) if r in universe],
            key=f"staff-released-{view_run.name}")
        st.caption(f"{len(universe) - len(released)} of {len(universe)} reps kept. A released "
                   "rep's book folds into the free book, which the reps who stay then value at "
                   "the filler rate.")
    else:
        st.caption("No staffing beside this map and no `rep` column in its table, so the app "
                   "cannot name the reps: opening the instance is the solver's job, not ours. "
                   "Staff everyone once and the roster comes back in `staffing.json`.")
        typed = st.text_area("Release these reps by hand", "", key=f"staff-typed-{view_run.name}",
                             help="Comma separated ids. Leave it empty to keep everyone.")
        released = [t.strip() for t in typed.replace("\n", ",").split(",") if t.strip()]
    return released, bool(universe)


def render_scope(view_run: Path, rows: list[dict], released: list[str],
                 has_universe: bool) -> None:
    st.subheader("Scope")
    districts = sorted({row["district"] for row in rows if row.get("district")})
    picked = st.session_state.get("selected_zip")
    home = next((r["district"] for r in rows if r["zip"] == picked), None)
    mode = st.radio("Staff", ["the whole map", "these districts"], horizontal=True,
                    key=f"scope-mode-{view_run.name}")
    scope_districts: list[str] = []
    if mode == "these districts":
        scope_districts = st.multiselect(
            "Districts", districts, default=[home] if home in districts else [],
            key=f"scope-districts-{view_run.name}")

    cols = st.columns(3)
    theta = cols[0].number_input("theta", 0.0, 1.0, config.THETA, step=0.05, key="staff-theta")
    lam = cols[1].number_input("lambda", 0.0, 1.0, config.LAM, step=0.05, key="staff-lam")
    filler = cols[2].selectbox("Filler capture", FILLERS, index=FILLERS.index(config.FILLER),
                               key="staff-filler")
    label = "Staff" if has_universe else "Staff with everyone"
    if st.button(label, type="primary", key="staff-go"):
        instance = instance_of(view_run)
        table = store.table_path(view_run)
        scope = scope_districts or None
        # An empty `--release` is what "nobody leaves" looks like to `tools/staff.py`: it splits
        # on the names it is given, so the empty list keeps the whole roster. Likewise an empty
        # `--districts` (no scope flag at all) staffs every district.
        child = launch_child(
            view_run, "staff",
            dict(released=released, theta=float(theta), lam=float(lam), filler_capture=filler,
                instance=str(instance), districts=scope_districts),
            lambda child: steps.staff_argv(
                config.SOLVER_PYTHON, config.CODE, instance, child, table=table, keep=None,
                release=released, theta=float(theta), lam=float(lam), filler_capture=filler,
                districts=scope),
            {"table": "draw.csv", "metrics": "staffing.json"})
        st.success(f"`{child.name}` in flight. It shows up here when it is done.")
        st.session_state["reps-preview"] = child
        st.rerun()


def render_contest(view_run: Path, staffing_run: Path, rows: list[dict], staffing: dict,
                   reps: dict | None) -> None:
    st.subheader("Contestability")
    contest = staffing.get("contest") or {}
    districts = sorted(contest)
    if not districts:
        st.caption("This staffing reports no contest.")
        return
    picked = st.session_state.get("selected_zip")
    home = next((r["district"] for r in rows if r["zip"] == picked), None)
    district = st.selectbox("District", districts, key=f"reps-district-{view_run.name}",
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

    render_footprint(view_run, rows, district, cands, reps)
    render_split(view_run, district, cands)


_PCT_COLUMNS = {name: st.column_config.NumberColumn(format="percent")
               for name in ("after", "change")}


def render_footprint(view_run: Path, rows: list[dict], district: str, cands: list[str],
                     reps: dict | None) -> None:
    here = [r for r in rows if r["district"] == district]
    reps_here = sorted({r["rep"] for r in here if r["rep"]})
    choices = ["the district"] + [r for r in cands if r in reps_here]
    # The key carries the run and the district: a stale selection under a fresh option list is
    # an error in streamlit, and both of those change the list.
    pick = st.selectbox("Show footprint", choices, key=f"reps-foot-{view_run.name}-{district}")
    if pick == "the district":
        marked = {r["zip"] for r in here}
        note = f"Highlighted: every zip of {district}."
    elif reps is not None:
        zips = reps.get("zips", {})
        marked = {r["zip"] for r in here
                 if zips.get(r["zip"], {}).get("shares", {}).get(pick, 0) > 0}
        note = f"Highlighted: {pick}'s sales footprint from the instance, inside {district}."
    else:
        marked = {r["zip"] for r in here if r["rep"] == pick}
        note = (f"Highlighted: the zips of {district} this table already labels {pick}. That is "
                "the table's own labelling, not a sales footprint; per-zip rep sales live in "
                "the instance, which the app never opens.")
    fig = _figure(_stamp(store.table_path(view_run)), _stamp(store.geom_path(view_run)),
                  tuple(sorted(marked)), pick)
    st.plotly_chart(fig, width="stretch", key=f"reps-foot-map-{view_run.name}-{district}")
    st.caption(note)


def render_split(view_run: Path, district: str, cands: list[str]) -> None:
    st.markdown("**Split this district among its candidates**")
    if len(cands) < 2:
        st.caption("A split needs two candidates or more.")
        return
    reps = st.multiselect("Reps", cands, default=cands[:2],
                          key=f"split-reps-{view_run.name}-{district}")
    cols = st.columns([2, 1, 1])
    exact = cols[1].toggle("Exact", value=False, key=f"split-exact-{view_run.name}-{district}",
                           help="SCIP on the Nash objective, warm started from the greedy "
                                "incumbent. Exact only when it closes the gap.")
    limit = cols[0].number_input("Time limit (s)", 5, 3600, 60, step=5,
                                 key=f"split-limit-{view_run.name}-{district}")
    geom = store.geom_path(view_run)
    if geom is None:
        st.caption("Geometry for this staffing is still being built; the split waits for it.")
    if cols[2].button("Split", key=f"split-go-{view_run.name}-{district}",
                      disabled=len(reps) < 2 or geom is None):
        parent_params = store.read_step(view_run).get("params", {})
        theta = parent_params.get("theta", config.THETA)
        lam = parent_params.get("lam", config.LAM)
        filler = parent_params.get("filler_capture", config.FILLER)
        instance = instance_of(view_run)
        table = store.table_path(view_run)
        child = launch_child(
            view_run, "split",
            dict(district=district, reps=reps, exact=bool(exact), time_limit=int(limit),
                instance=str(instance), theta=theta, lam=lam, filler_capture=filler,
                geom=str(geom)),
            lambda child: steps.split_argv(
                config.SOLVER_PYTHON, config.CODE, instance, child, table=table,
                district=district, reps=reps, theta=theta, lam=lam, filler_capture=filler,
                exact=bool(exact), time_limit=int(limit), geom=geom),
            {"table": "draw.csv", "metrics": "split.json"})
        st.success(f"`{child.name}` in flight.")
        st.session_state["reps-preview"] = child
        st.rerun()

    for child in store.children(view_run, config.APP_RESULTS):
        step = store.read_step(child)
        if step.get("kind") != "split" or step.get("params", {}).get("district") != district:
            continue
        report = _json(store.metrics_path(child))
        if report is None:
            st.caption(f"`{child.name}` is {store.status(child)}.")
            show_failure(child)
            return
        gap = report.get("gap")
        contiguous = report.get("contiguous")
        contig_note = {True: ", contiguous", False: ", not contiguous"}.get(contiguous, "")
        st.caption(f"`{child.name}`: {report.get('method', '')} / {report.get('status', '')}"
                   + (f", gap {gap:.2%}" if gap is not None else "")
                   + f", {report.get('n_zips', 0)} zips" + contig_note + ".")
        pieces = report.get("pieces") or {}
        if contiguous is False:
            st.warning("Not contiguous on the cell graph: "
                       + ", ".join(f"{r} in {n} pieces" for r, n in sorted(pieces.items())
                                  if n > 1))
        st.dataframe(pd.DataFrame([{"rep": rep, "share of the district's gain": share,
                                    "pieces": pieces.get(rep, "")}
                                   for rep, share in sorted((report.get("shares") or {}).items())]),
                     width="stretch", hide_index=True,
                     column_config={"share of the district's gain":
                                    st.column_config.NumberColumn(format="%.3f")})
        st.button("Open this split on the Map tab", on_click=open_on_map, args=(child,),
                  key=f"split-open-{child.name}")
        return


def render_assignment(staffing: dict, staffing_run: Path) -> None:
    st.subheader("Assignment")
    st.caption(f"Scope: {_scope_label(staffing_run)}.")
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


