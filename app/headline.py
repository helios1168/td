"""The Headline tab's data layer: one hard-wired case, capped per state and diffed.

The tab drives `tools/state_splits.py` for one cell only, the Track 2 anchored delta=5% map
already shipped (`docs/HEADLINE.md`), so a user can cap a state's district count, rerun, and
see what changed. Everything here reads JSON and CSV that the driver already writes; nothing
here touches `td` or a raw opportunity mass, only the M_s/tau ratios `--dump-state-shares` puts
on disk (the two absolute constraints on `app/`).

Two lower bounds hold a state above 1 district, and only one of them is a fact about the data:
the mass floor (`floor`, `problems`) cannot be argued with, while an anchor (`consequences`) is
a modelling choice about a district's committed home state and can be released. `problems`
blocks the run; `consequences` only warns.

A run that clears both can still come back with no map, in two ways that are not one claim, and
`failure` / `FAILURE_TEXT` keep them apart: HiGHS proving the overrides infeasible, and HiGHS
reaching its time limit without a feasible point. Refused by the floor, refuted by the solver,
and searched without success are three different answers.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

from app import config


def shares() -> dict:
    """`config.STATE_SHARES`'s content, or `{}` when it has not been computed yet."""
    if not config.STATE_SHARES.exists():
        return {}
    return json.loads(config.STATE_SHARES.read_text())


def compute_shares() -> Path:
    """Build `config.STATE_SHARES` once, in the foreground, and return its path.

    The driver loads the instance, joins the gazetteer and builds the moments matrix for this,
    tens of seconds, so it runs boxed in a spinner rather than on every rerun, and the result is
    cached to disk so it only has to run once.
    """
    config.STATE_SHARES.parent.mkdir(parents=True, exist_ok=True)
    argv = [str(config.SOLVER_PYTHON), str(config.REPO / "tools/state_splits.py"),
            str(config.INSTANCE), "--draw", str(config.COMMITTED_DRAW),
            "--geo-cache", str(config.GEO_CACHE), "--out", str(config.STATE_SHARES.parent),
            "--dump-state-shares", str(config.STATE_SHARES)]
    with st.spinner("Computing state shares (one-time, tens of seconds)..."):
        subprocess.run(argv, cwd=config.REPO, check=True, capture_output=True, text=True)
    return config.STATE_SHARES


def floor(ratio: float, delta: float) -> int:
    """The mass floor: a state carrying `ratio` * tau needs at least this many districts to fit
    each one under the `1 + delta` cap. The `1e-9` stops a ratio landing exactly on an integer
    from being pushed up a step by floating error."""
    return math.ceil(ratio / (1 + delta) - 1e-9)


def problems(caps: dict[str, int], delta: float, shares: dict) -> list[str]:
    """The refusal path. Fires only on the mass floor, never on an anchor, since the floor is
    a fact about the data and an anchor is not; an anchor is `consequences`' job."""
    states = shares.get("states", {})
    out = []
    for st, cap in sorted(caps.items()):
        info = states.get(st)
        if info is None:
            continue
        need = floor(info["ratio"], delta)
        if cap < need:
            admits = info["ratio"] / cap - 1
            out.append(
                f"{st} needs at least {need} districts at delta={delta:.0%}; "
                f"capping it at {cap} would need delta of about {admits:.1%}.")
    return out


def consequences(caps: dict[str, int], shares: dict) -> list[str]:
    """Warnings that do not block: a cap below a state's anchored count releases that many
    anchors, which is actionable (the tab reruns with `--unanchor`) rather than a refusal."""
    states = shares.get("states", {})
    out = []
    for st, cap in sorted(caps.items()):
        info = states.get(st)
        if info is None:
            continue
        anchored = info.get("anchored", 0)
        if cap < anchored:
            released = anchored - cap
            noun = "anchor" if released == 1 else "anchors"
            out.append(f"{st} holds {anchored} district homes; "
                       f"capping it at {cap} releases {released} {noun}.")
    return out


def failure(run: Path) -> dict | None:
    """The driver's `failure.json` for a run that produced no map, or `None` when it wrote none.

    Absent means the run died before or after the solve (a bad argument, a killed process), not
    that the MILP answered; the caller must keep a fallback for that case.
    """
    path = run / "failure.json"
    return json.loads(path.read_text()) if path.exists() else None


FAILURE_TEXT = {
    "infeasible": (
        "**No map satisfies these overrides.** HiGHS proved it: the constraints admit no "
        "assignment at all, so widening the search would change nothing. Only a wider band or a "
        "different override can help."),
    "no_incumbent": (
        "**The search ended without a map, which is not the same as proving there is none.** "
        "HiGHS reached the time limit having never found a feasible point. A longer limit, or a "
        "wider band, may still find one. California capped at 4 at delta = 5% answered this way "
        "after a full hour of search (`docs/HEADLINE.md` section 7)."),
    "other": (
        "**The solver stopped without a map and without a reason of either kind.** The log "
        "below has its own message."),
}


def reference() -> dict:
    """The headline cell: its `splits.json`, its `grid.csv` row one level up, and its draw."""
    return {
        "splits": json.loads((config.HEADLINE_CELL / "splits.json").read_text()),
        "grid": pd.read_csv(config.HEADLINE_CELL.parent / "grid.csv").iloc[0].to_dict(),
        "draw": config.HEADLINE_CELL / "draw.csv",
    }


def cell(run: Path) -> Path:
    """The single `d*/` directory inside a run: one delta per headline run."""
    dirs = sorted(run.glob("d*/"))
    if len(dirs) != 1:
        raise RuntimeError(f"expected exactly one d*/ cell under {run}, found {len(dirs)}")
    return dirs[0]


def district_ratios(splits: dict, shares: dict) -> list[float]:
    """Per-district ratio to tau, `sum_s (M_s/tau) y_sj`, from the balance-pass `y` in `splits`
    and the state ratios in `shares`: band position without the app ever touching a mass."""
    states = shares.get("states", {})
    state_list = splits["state_list"]
    y = splits["y"]
    k = len(y[0]) if y else 0
    ratios = [0.0] * k
    for s, code in enumerate(state_list):
        ratio = states.get(code, {}).get("ratio")
        if ratio is None:
            continue
        for j in range(k):
            ratios[j] += ratio * y[s][j]
    return ratios


def diff(ref: dict, new: dict, shares: dict) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Compare a rerun (`new`) against the headline (`ref`), both in `reference()`'s shape:
    `{"splits": ..., "grid": ..., "draw": ...}`, built from `cell(run)`'s `splits.json` and
    `draw.csv` and the run's own `grid.csv`.

    Returns a state table (headline count, new count, moved) restricted to states split in
    either side; a district table of each side's *target* share from the balance pass (labelled
    that way, not as a measurement: the module docstring's floor/anchor distinction has a
    twin here: `y` in `splits.json` is what the balance pass aimed for, `grid.csv`'s own
    `spread_rel` is what `realise` actually produced, and the two must not be shown as one
    number); and the count of zips relabelled, from joining the two `draw.csv` files on zip.
    Mass moved is deliberately absent: it needs per-zip mass, which the app must not hold.
    """
    ref_splits, new_splits = ref["splits"], new["splits"]

    def counts(splits: dict) -> dict[str, int]:
        state_list = splits["state_list"]
        z = splits["z"]
        return {state_list[s]: sum(z[s]) for s in range(len(state_list))}

    ref_counts, new_counts = counts(ref_splits), counts(new_splits)
    split_states = sorted(
        st for st in set(ref_counts) | set(new_counts)
        if ref_counts.get(st, 1) >= 2 or new_counts.get(st, 1) >= 2)
    state_table = pd.DataFrame([
        {"state": st, "headline": ref_counts.get(st, 1), "new": new_counts.get(st, 1),
         "moved": ref_counts.get(st, 1) != new_counts.get(st, 1)}
        for st in split_states])

    ref_ratios = district_ratios(ref_splits, shares)
    new_ratios = district_ratios(new_splits, shares)
    ref_delta, new_delta = ref_splits["delta"], new_splits["delta"]
    k = max(len(ref_ratios), len(new_ratios))
    district_table = pd.DataFrame([
        {"district": f"D{j + 1:02d}",
         "headline target share (balance pass)":
             ref_ratios[j] if j < len(ref_ratios) else float("nan"),
         "new target share (balance pass)":
             new_ratios[j] if j < len(new_ratios) else float("nan"),
         "headline band": f"{1 - ref_delta:.3f}-{1 + ref_delta:.3f}",
         "new band": f"{1 - new_delta:.3f}-{1 + new_delta:.3f}"}
        for j in range(k)])

    # only the two columns the join needs: a draw.csv is a zip table now and carries state,
    # coordinates and opportunity as well, and the app must hold no per-zip mass.
    cols = ["zip", "district"]
    ref_draw = pd.read_csv(ref["draw"])[cols].rename(columns={"district": "headline_district"})
    new_draw = pd.read_csv(new["draw"])[cols].rename(columns={"district": "new_district"})
    joined = ref_draw.merge(new_draw, on="zip", how="outer")
    zips_relabelled = int((joined["headline_district"] != joined["new_district"]).sum())

    return state_table, district_table, zips_relabelled
