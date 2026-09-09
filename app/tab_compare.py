"""Compare diffs two maps on the zips they share."""
from __future__ import annotations

import streamlit as st

from app import store
from app.common import _figure, _rows, _stamp, diff_frames, label_run, map_runs


def render_compare() -> None:
    runs = map_runs()
    if len(runs) < 2:
        st.info("Two finished maps are needed for a comparison.")
        return
    left, right = st.columns(2)
    a = left.selectbox("A", runs, index=1, format_func=label_run, key="cmp-a")
    b = right.selectbox("B", runs, index=0, format_func=label_run, key="cmp-b")
    stamp_a, stamp_b = _stamp(store.table_path(a)), _stamp(store.table_path(b))
    diff = diff_frames(_rows(*stamp_a), _rows(*stamp_b))

    cols = st.columns(3)
    cols[0].metric("Zips relabelled", diff["relabelled"])
    cols[1].metric("Zips in both", diff["shared"])
    cols[2].metric("Zips in one only", diff["only_a"] + diff["only_b"])
    if diff["only_a"] or diff["only_b"]:
        st.caption(f"{diff['only_a']} zip(s) only in A and {diff['only_b']} only in B take no "
                   "part in the counts above.")

    st.subheader("By state")
    st.dataframe(diff["states"], width="stretch", hide_index=True,
                 column_config={"share relabelled": st.column_config.NumberColumn(format="%.3f")})
    st.subheader("By district")
    st.dataframe(diff["districts"], width="stretch", hide_index=True,
                 column_config={"share A": st.column_config.NumberColumn(format="%.4f"),
                                "share B": st.column_config.NumberColumn(format="%.4f")})

    st.subheader("Side by side")
    board_a, board_b = st.columns(2)
    for column, run, stamp in ((board_a, a, stamp_a), (board_b, b, stamp_b)):
        with column:
            st.caption(run.name)
            st.plotly_chart(_figure(stamp, _stamp(store.geom_path(run)), (), ""),
                            width="stretch", key=f"cmp-map-{run.name}")
