"""Scenario browser — the walking skeleton of the business-user app.

Today it only reads what the engines already wrote: pick a run and a k, see the district table,
the balance numbers and the map.  Defining and saving a scenario, and launching an engine from
the browser, are the next steps (`docs/APP.md`).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app import config, runs

st.set_page_config(page_title="Territory scenarios", layout="wide")

MAPS = {
    "districts.png": "Bubbles, area proportional to opportunity",
    "district_regions.png": "Filled territory (power diagram; center-based draws only)",
    "district_regions_voronoi.png": "Filled territory (zip catchments; any draw)",
}


@st.cache_data(show_spinner=False)
def load_summary(path: str, k: int) -> pd.DataFrame:
    run = runs.Run(config.RESULTS / path, (k,))
    return pd.DataFrame(runs.metrics(run, k)["summary"])


all_runs = runs.discover()
if not all_runs:
    st.error(f"No engine output under {config.RESULTS}. Set TD_REPO if the hub is elsewhere.")
    st.stop()

with st.sidebar:
    st.header("Scenario")
    run = st.selectbox("Run", all_runs, format_func=lambda r: r.label)
    k = st.selectbox("Districts (k)", run.ks, index=len(run.ks) - 1)

m = runs.metrics(run, k)
scenario = m.get("scenario", {})
winner = m.get("winner", {})
after = next((d["after"] for d in m.get("draws", []) if d["seed"] == winner.get("seed")), {})

st.title(run.label)
st.caption(f"k = {k} · written {m.get('written', '?')} · seeds {m.get('seeds')}")

cols = st.columns(4)
cols[0].metric("Stage-2 value", f"{winner.get('stage2_value', float('nan')):.4f}")
cols[1].metric("Nash (stage 1)", f"{after.get('nash', float('nan')):.4f}")
cols[2].metric("Mass spread", f"{after.get('spread_rel', float('nan')):.2%}")
cols[3].metric("Unstaffed districts", len(winner.get("unstaffed_districts", [])))

if scenario.get("fix") or scenario.get("anchor"):
    st.subheader("Hand-drawn districts")
    st.json(scenario)

st.subheader("Districts")
st.dataframe(load_summary(run.label, k), width="stretch", hide_index=True)

st.subheader("Map")
figures = config.FIGURES / run.label.replace("/", "_") / f"k{k}"
shown = [(name, figures / name) for name in MAPS if (figures / name).exists()]
if shown:
    for name, path in shown:
        st.image(str(path), caption=MAPS[name])
else:
    st.info(
        f"No figures at {figures}. Generate them with:\n\n"
        f"```\n{config.SOLVER_PYTHON} tools/us_maps.py {config.INSTANCE} \\\n"
        f"  --out {figures} --districts {runs.draw_csv(run, k)} \\\n"
        f"  --regions-voronoi {runs.draw_csv(run, k)}\n```"
    )
