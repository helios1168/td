"""Reps opens on the map with the proposed districts drawn over the incumbent rep layout,
then staffs one district or the whole map, contests a district, and shows before-and-after.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, mapfig, repdata, runner, staffdiff, steps, store
from app.common import (FILLERS, _figure, _geom, _json, _rows, _stamp, instance_of, label_run,
                        launch_child, show_failure)


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

    render_staffing_form(view_run, rows, staffing)

    if staffing:
        st.divider()
        render_contest_detail(view_run, staffing_run, rows, staffing, reps)
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


def render_staffing_form(view_run: Path, rows: list[dict], staffing: dict | None) -> None:
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
    has_universe = bool(universe)

    cols = st.columns(5)
    theta = cols[0].number_input("theta", 0.0, 1.0, config.THETA, step=0.05, key="staff-theta")
    lam = cols[1].number_input("lambda", 0.0, 1.0, config.LAM, step=0.05, key="staff-lam")
    filler = cols[2].selectbox("Filler capture", FILLERS, index=FILLERS.index(config.FILLER),
                               key="staff-filler")
    exact = cols[3].toggle("Exact", value=False, key="staff-exact",
                           help="SCIP on the Nash objective for every multi-rep district's "
                                "split, warm started from the greedy incumbent. Applied "
                                "uniformly to every district this action resolves to 2+ reps.")
    limit = cols[4].number_input("Time limit (s)", 5, 3600, 60, step=5, key="staff-limit")

    st.subheader("Scope")
    districts = sorted({row["district"] for row in rows if row.get("district")})
    picked = st.session_state.get("selected_zip")
    home = next((r["district"] for r in rows if r["zip"] == picked), None)
    mode = st.radio("Staff", ["the whole map", "these districts"], horizontal=True,
                    key=f"scope-mode-{view_run.name}")
    scope_districts: list[str] = districts
    if mode == "these districts":
        scope_districts = st.multiselect(
            "Districts", districts, default=[home] if home in districts else [],
            key=f"scope-districts-{view_run.name}")
    # What `store.write_step`'s params carry for `_scope_label` to read back: the whole-map
    # case is `[]`, same as the old radio-only form, so it still prints "whole map" rather than
    # naming every district (the argv/data_editor still see the resolved `scope_districts` list
    # either way).
    params_districts = [] if mode == "the whole map" else scope_districts

    today = {d: sorted({r["rep"] for r in rows if r["district"] == d and r["rep"]})
            for d in scope_districts}
    editor_table = pd.DataFrame([{"district": d, "today": ", ".join(today.get(d, [])), "reps": 1}
                                 for d in scope_districts])
    # `st.data_editor` persists `edited_rows` under its key as `{row position: {col: value}}`
    # and reapplies it by position to whatever frame is passed next, with no identity or bounds
    # check: a scope change that shrinks or reorders the district list would otherwise replay a
    # stale edit onto the wrong district, or raise an IndexError outright. Folding a hash of the
    # resolved scope into the key forces a fresh editor -- and a fresh `edited_rows` -- on every
    # scope change.
    scope_hash = hashlib.sha1(",".join(scope_districts).encode()).hexdigest()[:8]
    edited = st.data_editor(
        editor_table, hide_index=True, width="stretch",
        key=f"reps-n-{view_run.name}-{scope_hash}",
        disabled=["district", "today"],
        column_config={"reps": st.column_config.NumberColumn(min_value=1, step=1)})

    multi = {}
    for _, row in edited.iterrows():
        n = row["reps"]
        n = 1 if pd.isna(n) else int(n)          # a cleared cell writes None/NaN, not 1
        if n > 1 and row["district"] in scope_districts:   # belt-and-braces scope guard
            multi[row["district"]] = n

    geom_path = store.geom_path(view_run)
    geom_dict = _geom(*_stamp(geom_path)) if geom_path else None
    has_cells = bool(geom_dict and geom_dict.get("cells"))
    submit_disabled = bool(multi) and not has_cells
    if submit_disabled:
        if geom_path is None:
            st.caption("A multi-rep split needs this run's cell geometry, and none has been "
                       "exported yet (no `geom.json` on this run).")
        else:
            st.caption("A multi-rep split needs cell geometry; this run's `geom.json` predates "
                       "cell export (no `\"cells\"` key). Rebuild it (\"Build polygons\" on the "
                       "Map tab) first.")

    label = "Staff" if has_universe else "Staff with everyone"
    if st.button(label, type="primary", key="staff-go", disabled=submit_disabled):
        instance = instance_of(view_run)
        table = store.table_path(view_run)
        child = launch_child(
            view_run, "staff",
            dict(released=released, theta=float(theta), lam=float(lam), filler_capture=filler,
                instance=str(instance), districts=params_districts, multi=multi,
                exact=bool(exact), time_limit=int(limit)),
            lambda child: steps.staff_and_split_argv(
                config.SOLVER_PYTHON, config.CODE, instance, child, table=table,
                release=released, theta=float(theta), lam=float(lam), filler_capture=filler,
                districts=scope_districts or None, multi=multi or None,
                exact=bool(exact), time_limit=int(limit), geom=geom_path),
            {"table": "draw.csv", "metrics": "staffing.json"})
        st.success(f"`{child.name}` in flight. It shows up here when it is done.")
        st.session_state["reps-preview"] = child
        st.rerun()


def render_contest_detail(view_run: Path, staffing_run: Path, rows: list[dict], staffing: dict,
                          reps: dict | None) -> None:
    st.subheader("Contest detail")
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

    split = (staffing.get("split_districts") or {}).get(district)
    if split:
        st.markdown("**Split**")
        shares = split.get("shares") or {}
        pieces = split.get("pieces") or {}
        frame = pd.DataFrame([{"rep": r, "share of the district's gain": shares.get(r, 0.0),
                               "pieces": pieces.get(r, "") if pieces else ""}
                              for r in sorted(split.get("reps") or [])])
        st.dataframe(frame, width="stretch", hide_index=True,
                     column_config={"share of the district's gain":
                                    st.column_config.NumberColumn(format="%.3f")})
        gap = split.get("gap")
        contiguous = split.get("contiguous")
        contig_note = {True: ", contiguous", False: ", not contiguous"}.get(contiguous, "")
        st.caption(f"{split.get('method', '')} / {split.get('status', '')}"
                   + (f", gap {gap:.2%}" if gap is not None else "")
                   + f", {split.get('n_zips', 0)} zips" + contig_note + ".")
        if contiguous is False:
            st.warning("Not contiguous on the cell graph: "
                       + ", ".join(f"{r} in {n} pieces" for r, n in sorted(pieces.items())
                                  if n > 1))

    requested = (staffing.get("requested_multi") or {}).get(district)
    if requested:
        req_n, res_n = requested["requested_n"], requested["resolved_n"]
        error = requested.get("error")
        if error:
            # The split runs before the Hungarian match: a raised error never strands this
            # district unstaffed on its own -- it falls through and is staffed above like any
            # other single-rep district, the error recorded here rather than hidden behind a
            # roster that (by count alone) came back full.
            st.warning(f"The {req_n}-rep split for this district failed and it was staffed as "
                       f"an ordinary single-rep district instead: {error}")
        elif res_n < req_n:
            n_zips_here = sum(1 for r in rows if r["district"] == district)
            if res_n == 0:
                st.caption(f"Requested {req_n} reps; no positive-gain candidate remained, so "
                           "this district is unstaffed.")
            elif n_zips_here < req_n and res_n >= n_zips_here:
                st.caption(f"Requested {req_n} reps, capped to {res_n}: this district has only "
                           f"{n_zips_here} zip(s)."
                           + (" Staffed by the ordinary match, not split." if res_n == 1 else ""))
            elif res_n == 1:
                st.caption(f"Requested {req_n} reps; only 1 positive-gain candidate remained, "
                           "so this district was staffed by the ordinary match instead of "
                           "split.")
            else:
                st.caption(f"Requested {req_n} reps, resolved to {res_n}: not enough "
                           "positive-gain candidates.")

    render_footprint(view_run, rows, district, cands, reps)


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


def render_assignment(staffing: dict, staffing_run: Path) -> None:
    st.subheader("Assignment")
    st.caption(f"Scope: {_scope_label(staffing_run)}.")
    assignment = staffing.get("assignment") or {}
    gains = staffing.get("gains") or {}
    split_districts = staffing.get("split_districts") or {}
    total = sum(gains.values()) + sum(sum((entry.get("gains") or {}).values())
                                      for entry in split_districts.values())
    frame_rows = [{"district": d, "rep": assignment.get(d, ""),
                  "gain share": gains.get(d, 0.0) / total if total else 0.0}
                 for d in sorted(set(assignment) | set(gains))]
    frame_rows += [{"district": d, "rep": ", ".join(sorted(entry.get("reps") or [])),
                    "gain share": (sum((entry.get("gains") or {}).values()) / total
                                   if total else 0.0)}
                   for d, entry in sorted(split_districts.items())]
    frame = pd.DataFrame(frame_rows)
    if not frame.empty:
        st.dataframe(frame, width="stretch", hide_index=True,
                     column_config={"gain share": st.column_config.NumberColumn(format="%.3f")})

    unstaffed = staffing.get("unstaffed_districts") or []
    unmatched = staffing.get("unmatched_reps") or []
    cols = st.columns(3)
    cols[0].metric("Districts staffed", len(assignment) + len(split_districts))
    cols[1].metric("Unstaffed", len(unstaffed))
    cols[2].metric("Reps with no district", len(unmatched))
    if unstaffed:
        st.warning("Unstaffed: " + ", ".join(unstaffed) + ". No kept rep sells there.")
    with st.expander(f"The {len(unmatched)} reps with no district"):
        st.write(", ".join(unmatched) or "none")


