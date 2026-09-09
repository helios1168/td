"""The scenario app: launch a grid of maps, then read one on the map.

Six tabs.  Scenarios launches one chain per k (draw, then clip, then polygons) and watches
them; Map opens any run the store discovered and draws its zip table; Reps staffs a map and
contests its districts; Overrides edits one by hand or reruns it under the edit as a
constraint; Compare diffs two maps on the zips they share; Timings shows how long each step
took. A sidebar picker, common to every tab, scopes them all to one launched scenario.

Nothing here imports `td`.  Every step is a driver in the solver virtualenv, launched detached
by `runner` and read back off disk by `store`, so a solve that takes ten minutes never blocks a
script rerun.  The Map tab defaults to clipped maps because the clip is the result: a draw
table is an intermediate and never stands in for the map its clip would have produced.

Each tab's body is a function called inside its `with` block.  `st.stop()` would end the whole
script, so a tab with nothing to show returns instead and leaves the other four standing.
"""
from __future__ import annotations

import streamlit as st

from app import common, tab_compare, tab_map, tab_overrides, tab_reps, tab_scenarios, tab_timings

st.set_page_config(page_title="Territory scenarios", layout="wide")
st.title("Territory scenarios")

common.current_scenario()

scenarios, map_tab, reps, overrides, compare, timings = st.tabs(
    ["Scenarios", "Map", "Reps", "Overrides", "Compare", "Timings"])

with scenarios:
    tab_scenarios.render_scenarios()

with map_tab:
    tab_map.render_map()

with reps:
    tab_reps.render_reps()

with overrides:
    tab_overrides.render_overrides()

with compare:
    tab_compare.render_compare()

with timings:
    tab_timings.render_timings()
