"""Reps opens on the map with the proposed districts drawn over the incumbent rep layout,
then staffs one district or the whole map, contests a district, and shows before-and-after.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, mapfig, repdata, staffdiff, steps, store
from app.common import (FILLERS, _figure, _geom, _json, _rows, _stamp, instance_of, launch_child,
                        open_on_map, pick_map, show_failure)


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


def render_reps() -> None:
    run = pick_map("Instance", "reps-run")
    if run is None:
        return
    rows = _rows(*_stamp(store.table_path(run)))
    instance = instance_of(run)
    reps = repdata.ensure(instance)

    if reps is not None:
        render_rep_map(run, reps)

    kind = store.read_step(run).get("kind")
    if kind == "staff":
        staff_run = run
    else:
        staff_children = [c for c in store.children(run, config.APP_RESULTS)
                          if store.read_step(c).get("kind") == "staff"]
        staff_run = (st.selectbox(
            "Staffing", staff_children, index=0,
            format_func=lambda c: f"{store.label(c, config.APP_RESULTS)} · {_scope_label(c)}",
            key=f"staff-pick-{run.name}") if staff_children else None)
    staffing = _json(store.metrics_path(staff_run)) if staff_run else None
    if staff_run is not None and staffing is None:
        st.caption(f"Staffing `{staff_run.name}` is {store.status(staff_run)}.")

    released, has_universe = render_keep_release(run, rows, staffing)
    render_scope(run, rows, released, has_universe)

    if staffing:
        st.divider()
        render_contest(run, staff_run, rows, staffing, reps)
        st.divider()
        render_assignment(staffing, staff_run)

    if reps is not None and staffing:
        st.divider()
        render_global_before_after(run, reps, staff_run, staffing)


def _scope_label(run: Path) -> str:
    districts = store.read_step(run).get("params", {}).get("districts") or []
    return "whole map" if not districts else ", ".join(districts)


def render_rep_map(run: Path, reps: dict) -> None:
    st.subheader("Proposed districts over the rep layout")
    reps_stamp = _stamp(repdata.reps_path(instance_of(run)))
    if reps_stamp is None:
        return
    cols = st.columns([2, 2, 1])
    colour_by = cols[0].radio(
        "Colour by", ["rep", "n"], horizontal=True,
        format_func=lambda v: "reps with book" if v == "n" else "rep",
        key=f"reps-colourby-{run.name}")
    focus = cols[1].selectbox("Focus rep", [""] + reps.get("reps", []),
                              key=f"reps-focus-{run.name}")
    hatch = cols[2].toggle("Hatch contested", value=True, key=f"reps-hatch-{run.name}")
    fig = _rep_fig(reps_stamp, _stamp(store.table_path(run)), _stamp(store.geom_path(run)),
                  colour_by, focus, hatch, True, None)
    st.plotly_chart(fig, width="stretch", key=f"reps-map-top-{run.name}")


def render_keep_release(run: Path, rows: list[dict], staffing: dict | None) -> tuple[list[str], bool]:
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
    return released, bool(universe)


def render_scope(run: Path, rows: list[dict], released: list[str], has_universe: bool) -> None:
    st.subheader("Scope")
    districts = sorted({row["district"] for row in rows if row.get("district")})
    picked = st.session_state.get("selected_zip")
    home = next((r["district"] for r in rows if r["zip"] == picked), None)
    mode = st.radio("Staff", ["the whole map", "these districts"], horizontal=True,
                    key=f"scope-mode-{run.name}")
    scope_districts: list[str] = []
    if mode == "these districts":
        scope_districts = st.multiselect(
            "Districts", districts, default=[home] if home in districts else [],
            key=f"scope-districts-{run.name}")

    cols = st.columns(3)
    theta = cols[0].number_input("theta", 0.0, 1.0, config.THETA, step=0.05, key="staff-theta")
    lam = cols[1].number_input("lambda", 0.0, 1.0, config.LAM, step=0.05, key="staff-lam")
    filler = cols[2].selectbox("Filler capture", FILLERS, index=FILLERS.index(config.FILLER),
                               key="staff-filler")
    label = "Staff" if has_universe else "Staff with everyone"
    if st.button(label, type="primary", key="staff-go"):
        instance = instance_of(run)
        table = store.table_path(run)
        scope = scope_districts or None
        # An empty `--release` is what "nobody leaves" looks like to `tools/staff.py`: it splits
        # on the names it is given, so the empty list keeps the whole roster. Likewise an empty
        # `--districts` (no scope flag at all) staffs every district.
        child = launch_child(
            run, "staff",
            dict(released=released, theta=float(theta), lam=float(lam), filler_capture=filler,
                instance=str(instance), districts=scope_districts),
            lambda child: steps.staff_argv(
                config.SOLVER_PYTHON, config.CODE, instance, child, table=table, keep=None,
                release=released, theta=float(theta), lam=float(lam), filler_capture=filler,
                districts=scope),
            {"table": "draw.csv", "metrics": "staffing.json"})
        st.success(f"`{child.name}` in flight. It shows up here when it is done.")


def render_contest(run: Path, staff_run: Path, rows: list[dict], staffing: dict,
                   reps: dict | None) -> None:
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

    if reps is not None:
        render_district_before_after(run, rows, reps, staff_run, staffing, district)

    render_footprint(run, rows, district, cands, reps)
    render_split(staff_run, district, cands)


def _district_bbox(rows: list[dict], district: str) -> tuple[float, float, float, float] | None:
    pts = [(r["x"], r["y"]) for r in rows
          if r.get("district") == district and r.get("x") is not None]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    px, py = (x1 - x0) * 0.05 or 1.0, (y1 - y0) * 0.05 or 1.0
    return (x0 - px, y0 - py, x1 + px, y1 + py)


def _rows_after_for_district(staff_run: Path, district: str) -> tuple[tuple[str, float] | None, bool]:
    """The newest split child's table for this district when one has a table (`True`), else the
    staffing run's own table (`False`)."""
    for child in store.children(staff_run, config.APP_RESULTS):
        step = store.read_step(child)
        if step.get("kind") == "split" and step.get("params", {}).get("district") == district:
            table = store.table_path(child)
            if table is not None:
                return _stamp(table), True
            break
    return _stamp(store.table_path(staff_run)), False


def _diff_table(view: dict) -> pd.DataFrame:
    reps_here = (set(view["before"]) - {"contested", "untapped"}) | set(view["after"])
    rows_ = []
    for rep in sorted(reps_here):
        b, a = view["before"].get(rep, 0.0), view["after"].get(rep, 0.0)
        rows_.append({"rep": rep, "before": b, "after": a, "change": a - b})
    for extra in ("contested", "untapped"):
        b = view["before"].get(extra, 0.0)
        rows_.append({"rep": extra, "before": b, "after": 0.0, "change": -b})
    return pd.DataFrame(rows_)


_PCT_COLUMNS = {name: st.column_config.NumberColumn(format="percent")
               for name in ("before", "after", "change")}


def render_district_before_after(run: Path, rows: list[dict], reps: dict, staff_run: Path,
                                 staffing: dict, district: str) -> None:
    bbox = _district_bbox(rows, district)
    if bbox is None:
        return
    reps_stamp = _stamp(repdata.reps_path(instance_of(run)))
    geom_stamp = _stamp(store.geom_path(run))
    rows_after_stamp, is_split = _rows_after_for_district(staff_run, district)
    staffing_stamp = _stamp(store.metrics_path(staff_run))
    if reps_stamp is None or rows_after_stamp is None or staffing_stamp is None:
        return

    left, right = st.columns(2)
    with left:
        fig = _rep_fig(reps_stamp, _stamp(store.table_path(run)), geom_stamp,
                       "rep", "", True, True, bbox)
        st.plotly_chart(fig, width="stretch", key=f"reps-dist-before-{staff_run.name}-{district}")
        st.caption("As sold today.")
    with right:
        fig2 = _staffed_fig(rows_after_stamp, geom_stamp, reps_stamp, staffing_stamp, bbox)
        st.plotly_chart(fig2, width="stretch", key=f"reps-dist-after-{staff_run.name}-{district}")
        st.caption("After split." if is_split else "After staffing.")

    view = staffdiff.district_view(reps, _rows(*rows_after_stamp), staffing, district)
    st.dataframe(_diff_table(view), width="stretch", hide_index=True, column_config=_PCT_COLUMNS)


def render_footprint(run: Path, rows: list[dict], district: str, cands: list[str],
                     reps: dict | None) -> None:
    here = [r for r in rows if r["district"] == district]
    reps_here = sorted({r["rep"] for r in here if r["rep"]})
    choices = ["the district"] + [r for r in cands if r in reps_here]
    # The key carries the run and the district: a stale selection under a fresh option list is
    # an error in streamlit, and both of those change the list.
    pick = st.selectbox("Show footprint", choices, key=f"reps-foot-{run.name}-{district}")
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
        instance = instance_of(staff_run)
        table = store.table_path(staff_run)
        child = launch_child(
            staff_run, "split",
            dict(district=district, reps=reps, exact=bool(exact), time_limit=int(limit),
                instance=str(instance), theta=theta, lam=lam, filler_capture=filler),
            lambda child: steps.split_argv(
                config.SOLVER_PYTHON, config.CODE, instance, child, table=table,
                district=district, reps=reps, theta=theta, lam=lam, filler_capture=filler,
                exact=bool(exact), time_limit=int(limit)),
            {"table": "draw.csv", "metrics": "split.json"})
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


def render_assignment(staffing: dict, staff_run: Path) -> None:
    st.subheader("Assignment")
    st.caption(f"Scope: {_scope_label(staff_run)}.")
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


def render_global_before_after(run: Path, reps: dict, staff_run: Path, staffing: dict) -> None:
    st.subheader("Before and after the staffing")
    reps_stamp = _stamp(repdata.reps_path(instance_of(run)))
    staff_table = store.table_path(staff_run)
    staffing_stamp = _stamp(store.metrics_path(staff_run))
    if reps_stamp is None or staff_table is None or staffing_stamp is None:
        return
    geom_stamp = _stamp(store.geom_path(run))

    left, right = st.columns(2)
    with left:
        fig = _rep_fig(reps_stamp, _stamp(store.table_path(run)), geom_stamp,
                       "rep", "", True, True, None)
        st.plotly_chart(fig, width="stretch", key=f"reps-global-before-{staff_run.name}")
    with right:
        fig2 = _staffed_fig(_stamp(staff_table), geom_stamp, reps_stamp, staffing_stamp, None)
        st.plotly_chart(fig2, width="stretch", key=f"reps-global-after-{staff_run.name}")

    rows_after = _rows(*_stamp(staff_table))
    summary = staffdiff.summary(reps, rows_after, staffing)
    cols = st.columns(3)
    cols[0].metric("Reps with territory", summary["reps_with_territory_after"],
                   delta=(summary["reps_with_territory_after"]
                         - summary["reps_with_territory_before"]))
    # Less contested book is the good direction, so the delta colour is inverted.
    cols[1].metric("Contested book", f"{summary['contested_weight_after']:.1%}",
                   delta=f"{summary['contested_weight_after'] - summary['contested_weight_before']:+.1%}",
                   delta_color="inverse")
    cols[2].metric("Free (before) / unstaffed (after) book",
                   f"{summary['unstaffed_weight_after']:.1%}",
                   delta=f"{summary['unstaffed_weight_after'] - summary['free_weight_before']:+.1%}")

    per_rep_rows = sorted(staffdiff.per_rep(reps, rows_after, staffing), key=lambda r: r["change"])
    only_changed = st.toggle("Only reps whose territory changed by more than 1 pt", value=True,
                             key=f"reps-changed-{staff_run.name}")
    if only_changed:
        per_rep_rows = [r for r in per_rep_rows if abs(r["change"]) > 0.01]
    frame = pd.DataFrame([{"rep": r["rep"], "before": r["before"], "after": r["after"],
                           "change": r["change"], "districts": ", ".join(r["districts"])}
                          for r in per_rep_rows])
    st.dataframe(frame, width="stretch", hide_index=True, column_config=_PCT_COLUMNS)
