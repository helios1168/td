"""The scenario app: define a scenario, run it, see the map, save it."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app import config, engines, runner, runs, scenario as sc_mod
from app import headline as hl
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

define, results, review, headline = st.tabs(["Define and run", "Results", "Review", "Headline"])

# ------------------------------------------------------------------ define and run
with define:
    left, right = st.columns([2, 1])
    with left:
        name = st.text_input("Scenario name", current.name, placeholder="California anchored")
        notes = st.text_area("Notes", current.notes, height=80,
                             placeholder="Why this scenario exists, and what to compare it to.")
    with right:
        keys = [k for k, e in engines.REGISTRY.items() if e.listed]
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

# ------------------------------------------------------------------ headline
# One hard-wired case, the shipped Track 2 anchored delta=5% cut: cap a state's district count,
# rerun the same MILP (free rerun plus diff, no warm start, no penalty term), and see what moved
# against the shipped map. `runs.discover()` never finds these runs (they write `d*/splits.json`,
# not `k*/metrics.json`), so they are filtered here by the engine key in their own `launch.json`.


def _headline_runs() -> list[Path]:
    out = []
    for p in runner.launched_runs():
        lf = p / runner.LAUNCH
        if lf.exists() and json.loads(lf.read_text()).get("engine") == "borders-headline":
            out.append(p)
    return out


with headline:
    ref = hl.reference()
    ref_splits, ref_grid = ref["splits"], ref["grid"]

    st.subheader("The shipped map")
    st.write(
        f"Track 2 anchored delta=5%: **{ref_splits['splits']} splits** "
        f"({ref_splits['split_states']}), spread {ref_grid['spread_rel']:.2%}, "
        f"max deviation {ref_grid['max_dev_rel']:.2%}. This is the map in `docs/HEADLINE.md`.")

    st.subheader("Override")
    st_shares = hl.shares()
    if not st_shares:
        st.warning(f"State shares have not been computed yet ({config.STATE_SHARES}).")
        if st.button("Compute state shares"):
            hl.compute_shares()
            st.rerun()
        st.stop()

    delta = st.number_input("delta (band half-width)", min_value=0.0, max_value=0.5,
                            value=0.05, step=0.01, format="%.3f")

    ref_counts = {code: sum(z) for code, z in zip(ref_splits["state_list"], ref_splits["z"])}
    override_rows = pd.DataFrame([
        {"state": code, "headline": ref_counts.get(code, 1),
         "floor": hl.floor(info["ratio"], delta), "cap": float("nan")}
        for code, info in sorted(st_shares["states"].items())
    ])
    edited = st.data_editor(
        override_rows, hide_index=True, width="stretch",
        disabled=["state", "headline", "floor"],
        column_config={"cap": st.column_config.NumberColumn(min_value=1, max_value=18, step=1)},
        key=f"hl-override-{delta:g}")
    caps = {row["state"]: int(row["cap"]) for row in edited.to_dict("records")
           if pd.notna(row.get("cap"))}

    st.subheader("Pre-flight")
    probs = hl.problems(caps, delta, st_shares)
    warns = hl.consequences(caps, st_shares)
    for p in probs:
        st.error(p)
    for w in warns:
        st.warning(w)
    if not probs and not warns:
        st.caption("No problems or consequences for this override.")

    name = "headline " + " ".join(f"{s}={n}" for s, n in sorted(caps.items())) + f" d{delta:g}"
    if st.button("Run", type="primary", disabled=bool(probs)):
        draft = Scenario(name=name, engine="borders-headline", caps=caps, delta=delta)
        draft_problems = sc_mod.validate(draft)
        for p in draft_problems:
            st.error(p)
        if not draft_problems:
            out = runner.launch(draft)
            st.session_state["hl-watching"] = str(out)
            st.success(f"Running in {out}. The MILP takes a few minutes; the rest of the "
                      f"pipeline takes seconds.")

    hl_runs = _headline_runs()
    st.subheader("In flight")
    active = [p for p in hl_runs if runner.status(p) != "done"]
    if not active:
        st.caption("No headline run in flight.")
    for path in active:
        state = runner.status(path)
        row, stop = st.columns([5, 1])
        row.write(f"**{path.name}** — {state}")
        if state == "running" and stop.button("Cancel", key=f"hl-cancel-{path.name}"):
            runner.cancel(path)
            st.rerun()
        with st.expander(f"Log — {path.name}", expanded=state == "failed"):
            if state == "failed":
                # TODO: this collapses two different outcomes into one sentence that reads as a
                # claim about the map. HiGHS Status 8 (Infeasible) is a proof that no map
                # satisfies the overrides; Status 13 (Time limit reached) with no primal
                # solution says only that the search did not reach a feasible point -- CA at 4,
                # delta = 5% returns the latter after an hour. Read the driver's log, tell the
                # two apart, and say how long the search ran.
                st.error("No map satisfies these overrides, or the run failed before writing "
                        "a result. The log below has the driver's own message.")
            st.code(runner.log_tail(path) or "(no output yet)")

    st.subheader("Result")
    finished = [p for p in hl_runs if runner.status(p) == "done"]
    if not finished:
        st.caption("No finished headline run yet.")
        st.stop()

    watching = st.session_state.get("hl-watching")
    default = next((i for i, p in enumerate(finished) if str(p) == watching), 0)
    run_path = st.selectbox("Run", finished, index=default, format_func=lambda p: p.name,
                            key="hl-run-pick")

    new_cell = hl.cell(run_path)
    new = {
        "splits": json.loads((new_cell / "splits.json").read_text()),
        "grid": pd.read_csv(run_path / "grid.csv").iloc[0].to_dict(),
        "draw": new_cell / "draw.csv",
    }

    if new["splits"]["status"] == "time_limit":
        st.warning(
            "This run hit the 600s solve limit. It returns an **incumbent**, a feasible map, "
            "not a certified minimum-splits map.")

    state_table, district_table, zips_relabelled = hl.diff(ref, new, st_shares)
    st.write(f"Zips relabelled against the headline: **{zips_relabelled}**")
    st.write("States split, headline vs. new district count:")
    st.dataframe(state_table, width="stretch", hide_index=True)
    st.write("Districts, target share from the balance pass, not a measurement:")
    st.dataframe(district_table, width="stretch", hide_index=True)
    st.caption(
        f"Headline: target spread {ref_grid['pass_spread']:.2%}, realised spread "
        f"{ref_grid['spread_rel']:.2%}. New: target spread {new['grid']['pass_spread']:.2%}, "
        f"realised spread {new['grid']['spread_rel']:.2%}. The two are not the same number.")

    if st.button("Render maps", key="hl-render"):
        ref_out = config.FIGURES / "headline_reference"
        new_out = config.FIGURES / "headline" / run_path.name
        with st.spinner("Drawing"):
            runner.render_draw(ref["draw"], ref_out)
            runner.render_draw(new["draw"], new_out)
        st.session_state["hl-rendered"] = str(run_path)
        st.rerun()

    if st.session_state.get("hl-rendered") == str(run_path):
        ref_png = config.FIGURES / "headline_reference" / "districts.png"
        new_png = config.FIGURES / "headline" / run_path.name / "districts.png"
        left, right = st.columns(2)
        if ref_png.exists():
            left.image(str(ref_png), caption="Headline")
        if new_png.exists():
            right.image(str(new_png), caption="New")
