"""Overrides edits a map by hand or reruns it under the edit as a constraint."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, runner, steps, store
from app.common import (MODES, _json, _rows, _stamp, instance_of, launch_child,
                        newest_child, open_on_map, pick_map, show_failure)


def render_overrides() -> None:
    run = pick_map("Instance to override", "over-run")
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
        payload = {"moves": list(edits), "hold": {"states": hold_states, "zips": hold_zips}}

        def build_argv(child: Path) -> list[str]:
            (child / "edits.json").write_text(json.dumps(payload, indent=2) + "\n",
                                              encoding="utf-8")
            return steps.override_argv(config.SOLVER_PYTHON, config.CODE, instance_of(run), child,
                                       table=store.table_path(run), edits=child / "edits.json",
                                       mode=mode, parent=run)

        child = launch_child(
            run, kind="override",
            params=dict(mode=mode, label=label, instance=str(instance_of(run)), **payload),
            argv=build_argv, outputs={"table": "draw.csv", "metrics": "metrics.json"})
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
