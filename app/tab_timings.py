"""Timings tab: a scenario's Gantt across its draw/clip/geom/staff/... chains, read off each
run's `timings.json` (`td/telemetry.py`), plus one run's phase breakdown underneath.

A run written before telemetry existed, or one whose driver has not finished, carries no
`timings.json`; it still gets a row, drawn hollow while running or as a zero-width "no
timings" marker once it is not. `gantt_figure` and `phases_figure` are plain functions of
already-loaded data so they can be built and checked outside Streamlit.
"""
from __future__ import annotations

import io
import json
import pstats
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import config, store

# Fixed step-kind palette, in legend order (dataviz, validated by the main session: CVD 7.9 on
# green/orange, legal only because every solid bar also carries its kind as a direct label).
KIND_COLOR = {"draw": "#2563eb", "clip": "#d97706", "geom": "#059669", "staff": "#7c3aed"}
OTHER_COLOR = "#dc2626"  # split, override, reps, and anything else
KIND_ORDER = ["draw", "clip", "geom", "staff", "other"]


def _kind_bucket(kind: str) -> str:
    return kind if kind in KIND_COLOR else "other"


def _kind_color(kind: str) -> str:
    return KIND_COLOR.get(kind, OTHER_COLOR)


# ------------------------------------------------------------------ reading timings.json
@st.cache_data(show_spinner=False)
def _timings(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _timings_path(run: Path) -> Path | None:
    rel = store.read_step(run).get("outputs", {}).get("timings")
    if not rel:
        return None
    path = (Path(run) / rel).resolve()
    return path if path.exists() else None


def _load(run: Path) -> dict | None:
    path = _timings_path(run)
    return _timings(str(path), path.stat().st_mtime) if path is not None else None


def _parse_started(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ------------------------------------------------------------------ pure figure builders
def _hover_text(row: dict) -> str:
    lines = [f"{row['kind']} · {row['label']}"]
    lines.append(f"wall {row['wall']:.1f} s" if row.get("wall") is not None else "no timings yet")
    for name, wall in row.get("phases", []):
        lines.append(f"{name} {wall:.1f} s")
    return "<br>".join(lines)


def gantt_figure(rows: list[dict]) -> go.Figure:
    """`rows`: one dict per bar -- `member`, `kind` (bucket: draw/clip/geom/staff/other),
    `label` (run label for hover), `start`/`end` (seconds relative to the scenario's earliest
    start), `state` (`"done"`, `"running"` or `"no_timings"`), `phases` (depth-0 `(name, wall)`
    pairs), `wall` (seconds, or `None`). One trace per kind, in the fixed legend order, so hue
    always means the same kind."""
    starts: dict[str, float] = {}
    for row in rows:
        starts[row["member"]] = min(starts.get(row["member"], row["start"]), row["start"])
    members = sorted(starts, key=lambda m: starts[m])

    fig = go.Figure()
    for kind in KIND_ORDER:
        bucket = [r for r in rows if r["kind"] == kind]
        if not bucket:
            continue
        color = _kind_color(kind)
        fig.add_trace(go.Bar(
            name=kind, orientation="h",
            base=[r["start"] for r in bucket],
            x=[max(r["end"] - r["start"], 0.0) for r in bucket],
            y=[r["member"] for r in bucket],
            marker=dict(
                color=["rgba(0,0,0,0)" if r["state"] == "running" else color for r in bucket],
                line=dict(color=color, width=[1.5 if r["state"] == "running" else 0 for r in bucket])),
            text=[kind if r["state"] == "done" else
                  ("running" if r["state"] == "running" else "no timings") for r in bucket],
            textposition="auto",
            hovertext=[_hover_text(r) for r in bucket], hoverinfo="text"))

    fig.update_layout(
        barmode="overlay",
        xaxis=dict(title="seconds", gridcolor="#e5e7eb", zeroline=False),
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(members))),
        height=max(220, 40 * len(members) + 120),
        margin=dict(l=160, r=20, t=30, b=40),
        uirevision="timings")
    return fig


def phases_figure(timings: dict) -> go.Figure:
    """One horizontal bar per depth-0/1 phase, in the order the driver entered them. Depth 1 is
    indented in its label and drawn in the lighter shade of the same hue."""
    phases = [p for p in timings.get("phases", []) if p.get("depth", 0) in (0, 1)]
    labels = [("    " if p.get("depth") == 1 else "") + p["name"] for p in phases]
    walls = [p.get("wall", 0.0) for p in phases]
    colors = ["#93c5fd" if p.get("depth") == 1 else "#2563eb" for p in phases]
    fig = go.Figure(go.Bar(
        orientation="h", x=walls, y=labels, marker=dict(color=colors),
        text=[f"{w:.2f} s" for w in walls], textposition="auto"))
    fig.update_layout(
        xaxis=dict(title="seconds", gridcolor="#e5e7eb", zeroline=False),
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(labels))),
        height=max(160, 32 * len(labels) + 80),
        margin=dict(l=180, r=20, t=20, b=40),
        showlegend=False)
    return fig


# ------------------------------------------------------------------ scenario summary
def _scenario_summary(entries: list[dict], root: Path) -> dict | None:
    if not entries:
        return None
    epoch = min(e["started"] for e in entries)
    now = datetime.now()
    total_cpu = 0.0
    latest_end = epoch
    span_by_member: dict[str, tuple[datetime, datetime, str, float]] = {}
    for e in entries:
        member = store.member_of(e["run"], root) or store.label(e["run"], root)
        timings = e["timings"]
        if timings is not None:
            end = e["started"] + timedelta(seconds=timings["wall"])
            total_cpu += timings.get("cpu", 0.0)
        elif store.status(e["run"]) == "running":
            end = now
        else:
            end = e["started"]
        latest_end = max(latest_end, end)
        dur = (end - e["started"]).total_seconds()
        lo, hi, culprit, culprit_dur = span_by_member.get(member, (e["started"], end, e["kind"], dur))
        lo, hi = min(lo, e["started"]), max(hi, end)
        if dur > culprit_dur:
            culprit, culprit_dur = e["kind"], dur
        span_by_member[member] = (lo, hi, culprit, culprit_dur)

    slowest, (lo, hi, culprit, _dur) = max(
        span_by_member.items(), key=lambda kv: (kv[1][1] - kv[1][0]).total_seconds())
    span = (latest_end - epoch).total_seconds()
    return dict(member=slowest, wall=(hi - lo).total_seconds(), kind=culprit,
               parallelism=(total_cpu / span) if span > 0 else 0.0)


# ------------------------------------------------------------------ render
def render_timings() -> None:
    root = config.APP_RESULTS
    slug = st.session_state.get("scenario")
    runs = [r for r in store.discover(root) if store.scenario_of(r, root) == slug]
    if not runs:
        st.info("No runs in this scenario yet.")
        return

    entries = []
    for run in runs:
        step = store.read_step(run)
        started = _parse_started(step.get("started"))
        if started is None:
            continue
        entries.append(dict(run=run, step=step, started=started,
                            kind=step.get("kind", "other"), timings=_load(run)))
    if not entries:
        st.info("No runs in this scenario have started yet.")
        return

    epoch = min(e["started"] for e in entries)
    now = datetime.now()
    rows = []
    for e in entries:
        member = store.member_of(e["run"], root) or store.label(e["run"], root)
        start = (e["started"] - epoch).total_seconds()
        timings = e["timings"]
        if timings is not None:
            rows.append(dict(member=member, kind=_kind_bucket(e["kind"]),
                             label=store.label(e["run"], root), start=start,
                             end=start + timings["wall"], state="done",
                             phases=[(p["name"], p["wall"]) for p in timings.get("phases", [])
                                    if p.get("depth") == 0],
                             wall=timings["wall"]))
        elif store.status(e["run"]) == "running":
            rows.append(dict(member=member, kind=_kind_bucket(e["kind"]),
                             label=store.label(e["run"], root), start=start,
                             end=(now - epoch).total_seconds(), state="running",
                             phases=[], wall=None))
        else:
            rows.append(dict(member=member, kind=_kind_bucket(e["kind"]),
                             label=store.label(e["run"], root), start=start, end=start,
                             state="no_timings", phases=[], wall=None))

    summary = _scenario_summary(entries, root)
    if summary:
        st.write(f"Slowest chain: **{summary['member']}**, {summary['wall']:.0f} s total, "
                f"set by **{summary['kind']}**. Parallelism (cpu / wall) over the scenario: "
                f"{summary['parallelism']:.2f}x.")
    if not any(e["timings"] for e in entries):
        st.caption("No timings yet. The drivers write timings.json when they finish.")

    st.plotly_chart(gantt_figure(rows), width="stretch", key=f"timings-gantt-{slug}")

    render_detail(entries, root)


def render_detail(entries: list[dict], root: Path) -> None:
    with_timings = [e for e in entries if e["timings"] is not None]
    if not with_timings:
        st.caption("No run in this scenario has written timings.json yet.")
        return

    with_timings.sort(key=lambda e: e["timings"]["wall"], reverse=True)
    options = [e["run"] for e in with_timings]
    run = st.selectbox("Run", options, index=0, format_func=lambda r: store.label(r, root),
                       key="timings-detail-run")
    timings = next(e["timings"] for e in with_timings if e["run"] == run)

    if timings.get("phases"):
        st.plotly_chart(phases_figure(timings), width="stretch", key=f"timings-phases-{run.name}")
    else:
        st.caption("This run's timings.json carries no phases.")

    solve = next((p for p in timings.get("phases", []) if p.get("name") == "solve"), None)
    note = (solve or {}).get("note") or {}
    if note:
        fields = [("status", "status", "{}"), ("gap", "gap", "{:.2%}"),
                 ("nodes", "nodes", "{:,}"), ("dual_bound", "dual bound", "{:.4g}"),
                 ("objective", "objective", "{:.4g}"), ("engine", "engine", "{}")]
        present = [(label, fmt.format(note[key])) for key, label, fmt in fields
                  if note.get(key) is not None]
        if present:
            for col, (label, value) in zip(st.columns(len(present)), present):
                col.metric(label, value)

    ticks = timings.get("ticks") or {}
    if ticks:
        st.write("Ticks")
        st.dataframe(pd.DataFrame([
            {"name": name, "n": t["n"], "wall (s)": round(t["wall"], 3),
             "mean (s)": round(t["wall"] / t["n"], 4) if t["n"] else 0.0}
            for name, t in sorted(ticks.items())]), hide_index=True, width="stretch")

    path = _timings_path(run)
    profile = path.parent / "profile.prof" if path is not None else None
    if profile is not None and profile.exists():
        with st.expander("Profile: top 25 by cumulative time"):
            buf = io.StringIO()
            pstats.Stats(str(profile), stream=buf).sort_stats("cumulative").print_stats(25)
            st.code(buf.getvalue())
