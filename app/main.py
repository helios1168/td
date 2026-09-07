"""The scenario app: define a scenario, run it, see the map, save it."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app import config, engines, runner, runs, scenario as sc_mod
from app.scenario import Scenario

st.set_page_config(page_title="Territory scenarios", layout="wide")

MAPS = {
    "districts.png": "Districts — bubble area is opportunity",
    "district_regions.png": "Territory — power diagram",
    "district_regions_fixed_committed.png":
        "One held diagram, before — the committed labelling on the power diagram it implies; "
        "every mismatched dot was assigned against compactness",
    "district_regions_fixed_snapped.png":
        "One held diagram, after — the same centres and weights, dots recoloured by the "
        "labelling those weights produce. Zero outside, relative to this diagram; rebuilding "
        "it from these labels moves the centres and some fall outside again",
    "district_regions_voronoi.png": "Territory — zip catchments",
}

# The review pair, in the order a sponsor reads them. Both panels carry their own numbers in the
# rendered subtitle, so nothing here restates a count that could drift away from the figure.
FIXED = ("district_regions_fixed_committed.png", "district_regions_fixed_snapped.png")


def pins_table(sc: Scenario) -> pd.DataFrame:
    rows = [{"district": d, "mode": mode, "states": ",".join(states)}
            for mode, group in (("fix", sc.fix), ("anchor", sc.anchor))
            for d, states in group.items()]
    return pd.DataFrame(rows or [{"district": "", "mode": "anchor", "states": ""}])


def pins_from_table(table: pd.DataFrame) -> tuple[dict, dict]:
    fix: dict[str, list[str]] = {}
    anchor: dict[str, list[str]] = {}
    for row in table.to_dict("records"):
        name = str(row.get("district") or "").strip().upper()
        if not name:
            continue
        states = [s.strip().upper() for s in str(row.get("states") or "").split(",") if s.strip()]
        (fix if row.get("mode") == "fix" else anchor)[name] = states
    return fix, anchor


def cuts_from_text(text: str) -> dict[str, int]:
    cuts: dict[str, int] = {}
    for token in text.split():
        group, _, pieces = token.rpartition(":")
        if group and pieces.isdigit():
            cuts[group.upper()] = int(pieces)
    return cuts


# ------------------------------------------------------------------ sidebar: saved scenarios
saved = sc_mod.saved_scenarios()
with st.sidebar:
    st.header("Saved scenarios")
    if saved:
        picked = st.selectbox("Open", saved, format_func=lambda s: f"{s.name} · {s.saved[:10]}")
        if st.button("Load", width="stretch"):
            st.session_state["editing"] = picked
    else:
        st.caption(f"None yet. They are saved to {config.SCENARIOS}.")

current: Scenario = st.session_state.get("editing", Scenario(name=""))

define, results, review = st.tabs(["Define and run", "Results", "Review"])

# ------------------------------------------------------------------ define and run
with define:
    left, right = st.columns([2, 1])
    with left:
        name = st.text_input("Scenario name", current.name, placeholder="California anchored")
        notes = st.text_area("Notes", current.notes, height=80,
                             placeholder="Why this scenario exists, and what to compare it to.")
    with right:
        keys = list(engines.REGISTRY)
        engine_key = st.selectbox(
            "Engine", keys,
            index=keys.index(current.engine) if current.engine in keys else keys.index(engines.DEFAULT),
            format_func=lambda k: engines.REGISTRY[k].label)
        engine = engines.REGISTRY[engine_key]
        k = st.number_input("Districts (k)", min_value=2, max_value=40, value=current.k)
        seeds = st.text_input("Seeds", current.seeds, disabled="seeds" not in engine.fields,
                              help="A value, a list, or a range a-b. More seeds, better draw, longer run.")
    st.caption(engine.note)

    pins_honoured = bool({"fix", "anchor"} & engine.fields)
    st.subheader("Hand-drawn districts")
    if pins_honoured:
        st.caption("`fix` is closed — exactly those states. `anchor` is open — those states plus "
                   "whatever the solver adds. States as codes, comma separated.")
        table = st.data_editor(
            pins_table(current), num_rows="dynamic", width="stretch", hide_index=True,
            column_config={"mode": st.column_config.SelectboxColumn(options=["fix", "anchor"])},
            key="pins")
        fix, anchor = pins_from_table(table)
        cuts = current.cuts
    else:
        st.info(f"{engine.label} does not take hand-drawn districts. It takes a cut plan.")
        fix, anchor = {}, {}
        cuts_text = st.text_input("Cut plan", " ".join(f"{g}:{n}" for g, n in
                                                       (current.cuts or {"CA": 5, "TX": 2, "NY,NJ": 3, "FL": 2}).items()),
                                  help="ST[,ST]:N — a state group cut into N pieces.")
        cuts = cuts_from_text(cuts_text)

    draft = Scenario(name=name, engine=engine_key, k=int(k), seeds=seeds,
                     fix=fix, anchor=anchor, cuts=cuts, notes=notes)
    problems = sc_mod.validate(draft)
    for problem in problems:
        st.warning(problem)

    save_col, run_col, _ = st.columns([1, 1, 4])
    if save_col.button("Save", disabled=bool(problems), width="stretch"):
        st.success(f"Saved to {sc_mod.save(draft)}")
    if run_col.button("Run", type="primary", disabled=bool(problems), width="stretch"):
        sc_mod.save(draft)
        out = runner.launch(draft)
        st.session_state["watching"] = str(out)
        st.success(f"Running in {out}. Follow it under Results.")

# ------------------------------------------------------------------ results
with results:
    active = [p for p in runner.launched_runs() if runner.status(p) != "done"]
    if active:
        st.subheader("In flight")
        if st.button("Refresh"):
            st.rerun()
        for path in active:
            state = runner.status(path)
            row, stop = st.columns([5, 1])
            row.write(f"**{path.name}** — {state}")
            if state == "running" and stop.button("Cancel", key=f"cancel-{path.name}"):
                runner.cancel(path)
                st.rerun()
            with st.expander(f"Log — {path.name}", expanded=state == "failed"):
                st.code(runner.log_tail(path) or "(no output yet)")

    finished = runs.discover()
    if not finished:
        st.info(f"No finished runs under {config.RESULTS}.")
        st.stop()

    watching = st.session_state.get("watching")
    default = next((i for i, r in enumerate(finished) if str(r.path) == watching), 0)
    pick, k_pick = st.columns([3, 1])
    run = pick.selectbox("Run", finished, index=default, format_func=lambda r: r.label)
    k = k_pick.selectbox("k", run.ks, index=len(run.ks) - 1)

    m = runs.metrics(run, k)
    winner = m.get("winner", {})
    after = next((d["after"] for d in m.get("draws", []) if d["seed"] == winner.get("seed")), {})
    nan = float("nan")

    cols = st.columns(4)
    cols[0].metric("Stage-2 value", f"{winner.get('stage2_value', nan):.4f}")
    cols[1].metric("Nash (stage 1)", f"{after.get('nash', nan):.4f}")
    cols[2].metric("Mass spread", f"{after.get('spread_rel', nan):.2%}")
    cols[3].metric("Unstaffed districts", len(winner.get("unstaffed_districts", [])))

    pinned = m.get("scenario", {})
    if pinned.get("fix") or pinned.get("anchor"):
        st.subheader("Hand-drawn districts")
        st.json(pinned)

    st.subheader("Districts")
    st.dataframe(pd.DataFrame(m["summary"]), width="stretch", hide_index=True)

    st.subheader("Maps")
    launch_file = run.path / runner.LAUNCH
    engine_key = (json.loads(launch_file.read_text())["engine"]
                  if launch_file.exists() else engines.DEFAULT)
    figures = runner.figure_dir(run.path, k)
    drawn = [(n, figures / n) for n in MAPS if (figures / n).exists()]
    if st.button("Render maps", help="Runs tools/us_maps.py. Seconds for a catchment map; "
                                     "minutes for a power-cell run, which solves a "
                                     "transportation LP per diagram."):
        with st.spinner("Drawing"):
            runner.render_maps(run.path, k, engine_key)
        st.rerun()
    for name, path in drawn:
        st.image(str(path), caption=MAPS[name])
    if not drawn:
        st.caption("No figures for this run and k yet.")

# ------------------------------------------------------------------ review
# The sponsor-facing view: one held power diagram, the committed labelling and the snapped one
# drawn on it. Every other rendering recomputes the centroids from whatever labels it is handed,
# so it scores the *next* iterate and cannot show the zero
# (`docs/OPTIONS_power-cell-contiguity.md` §4a). This tab exists because that figure is the one
# a review needs and no other panel can stand in for it.
with review:
    st.subheader("Does the shipped map agree with its own geometry?")
    st.write(
        "A district is defined by a centre and a weight, and a zip belongs to whichever cell is "
        "nearest once the weights correct for how much opportunity each district has to cover. "
        "A dot in the wrong colour is a zip the draw assigned against that geometry. Both panels "
        "below hold the **same** centres and weights, so the only thing that changes between "
        "them is which district each zip is labelled with.")

    # `finished` is non-empty here: the Results tab above stops the script when it is not.
    # Open on a run whose pair is already drawn, so the tab shows the figure rather than the
    # render button. Newest-first order is preserved among those, and falls back to newest.
    default = next((i for i, r in enumerate(finished)
                    if all((runner.figure_dir(r.path, r.ks[-1]) / n).exists() for n in FIXED)), 0)
    pick, k_pick = st.columns([3, 1])
    run = pick.selectbox("Run", finished, index=default, format_func=lambda r: r.label,
                         key="review-run")
    k = k_pick.selectbox("k", run.ks, index=len(run.ks) - 1, key="review-k")

    figures = runner.figure_dir(run.path, k)
    missing = [n for n in FIXED if not (figures / n).exists()]
    if missing:
        st.warning("This pair has not been rendered for this run and k yet.")
        st.caption("Rendering solves a transportation LP per diagram and takes minutes, not "
                   "seconds. It runs in the foreground, so leave the tab open.")
        launch_file = run.path / runner.LAUNCH
        engine_key = (json.loads(launch_file.read_text())["engine"]
                      if launch_file.exists() else engines.DEFAULT)
        if st.button("Render the pair", type="primary"):
            with st.spinner("Drawing"):
                runner.render_maps(run.path, k, engine_key)
            st.rerun()
    else:
        for name in FIXED:
            st.image(str(figures / name), caption=MAPS[name])
        st.caption(
            "The zero on the second panel is relative to the diagram drawn there. Rebuild a "
            "diagram from those labels and the centres move, so a handful of zips fall outside "
            "again — the panel's own subtitle carries the measured count. Ringed zips are the "
            "ones the LP splits between two cells, where the assignment is a rounding rather "
            "than a decision.")
