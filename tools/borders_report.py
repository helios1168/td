"""borders_report.py -- Unit F of the borders build (docs/BORDERS_PLAN.md): the per-cell
reporting helper shared by the borders CLI drivers written next (`tools/state_borders.py` and
whatever companion needs the same numbers).

A "cell" is one labelling of the committed k=18 draw -- the committed map itself, a pure
state-border snap, or a penalised-and-banded refinement (`td.solvers.state_borders.refine`) --
and this module turns one such labelling into the row `docs/BORDERS_PLAN.md`'s grid wants:
stage-1/stage-2 metrics on the *completed* instance (coordinate-less zips placed back in), how
much mass sits outside its state's owner set, a `draw.csv` zip table (`td/ziptable.py`) whose
first and last columns are the `zip,district` `tools/us_maps.py` and the app already read, and
the maps themselves::

    ctx = load_committed(instance_path, draw_path, geo_cache)     # once per run
    row = cell_row(ctx, ctx.labels0, "committed", {"n_fractional": 0})
    completed = run_draw.complete(ctx.labels0, ctx.zips, ctx.states_by_zip, ctx.missing,
                                  ctx.M_by_zip)
    write_cell(out_dir, "committed", ctx, ctx.labels0, completed)
    write_grid(out_dir, [row, ...])                                # committed row first
    render_cell_maps(os.path.join(out_dir, "committed"), geo_cache)

`load_committed` reads the instance and the committed draw once and owns everything downstream
needs: the geometric arrays `centers.py`/`state_borders.py` take (`xy`, `M`, `state_idx`,
`labels0`, `zips`, `k`), the full-instance dicts `run_draw.complete`/`channel.place_by_state`
need to complete any other labelling on the same zips, and the committed map's own owner sets
(`home`/`owners`), computed once from the committed labels and reused for every cell -- a
district's identity as "whose home state" must not move just because a later cell relabels a
handful of its zips.
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channel, geo, ziptable                                      # noqa: E402
from td import instance as descaled                                        # noqa: E402
from td.solvers import centers                                             # noqa: E402
import run_draw                                                            # noqa: E402
import us_maps                                                             # noqa: E402

# run_draw.py's --theta/--lam/--filler-capture defaults -- the weights the committed map's own
# stage-2 value was computed under (battery/results/draw_k18_v2_20260904/k18/metrics.json), and
# `cell_row`'s own defaults.  A caller may override them (e.g. `tools/state_splits.py`'s
# --theta/--lam/--filler-capture), in which case the resulting stage-2 value is scored under
# different weights and is not comparable to the committed map's own number.
THETA = 0.40
LAM = 0.30
FILLER_CAPTURE = "theta"

# lower 48 + DC (td.geo.NON_CONUS's complement, DC added back): a zip in AK, HI, or with an
# unknown/"??" state gets state_idx -1 -- no owner set, never snapped, still placed at
# completion by `channel.place_by_state`.
_STATE_LIST = sorted({
    "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "ID", "IL", "IN", "IA", "KS", "KY",
    "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "DC",
})

_D_RE = re.compile(r"^D(\d+)$")


def _label_of(name: str) -> int:
    """`"D07"` -> `6` -- the inverse of `run_draw.district_id`."""
    m = _D_RE.match(name)
    if not m:
        raise ValueError(f"district name {name!r} is not a solver id D01..Dkk")
    return int(m.group(1)) - 1


# ------------------------------------------------------------------ owner sets (committed only)
def _home_and_owners(labels: np.ndarray, state_idx: np.ndarray, M: np.ndarray, k: int,
                     n_states: int) -> tuple:
    """Inline fallback for `td.solvers.state_borders.owner_sets`, same rule: `home(j)` is the
    state with the plurality of district `j`'s mass; `O(s)` is the districts with home `s`,
    or -- when that is empty -- the single district holding the most of `s`'s mass."""
    mass = np.zeros((k, n_states), float)
    valid = state_idx >= 0
    np.add.at(mass, (labels[valid], state_idx[valid]), M[valid])
    home = np.array([int(row.argmax()) if row.sum() > 0 else -1 for row in mass], int)
    owners = np.zeros((n_states, k), bool)
    for s in range(n_states):
        ds = np.flatnonzero(home == s)
        if ds.size:
            owners[s, ds] = True
        elif mass[:, s].sum() > 0:
            owners[s, int(mass[:, s].argmax())] = True
    return home, owners


def _owner_sets(labels: np.ndarray, state_idx: np.ndarray, M: np.ndarray, k: int,
               n_states: int) -> tuple:
    """`td.solvers.state_borders.owner_sets` when it is implemented, else `_home_and_owners`.

    That module is being written concurrently (docs/BORDERS_PLAN.md); its `owner_sets` exists
    as a stub that raises `NotImplementedError` until then.
    """
    try:
        from td.solvers.state_borders import owner_sets
        return owner_sets(labels, state_idx, M, k, n_states)
    except (ImportError, NotImplementedError):
        return _home_and_owners(labels, state_idx, M, k, n_states)


# ------------------------------------------------------------------------------------- context
@dataclass
class Ctx:
    """Everything a cell needs, loaded once from the instance and the committed draw.

    `xy`, `M`, `state_idx`, `labels0`, `zips` are parallel arrays over the `k`-district
    committed draw's *geometric* zips only (those with a gazetteer coordinate) -- the shape
    `centers.py`/`state_borders.py` take.  Completing a labelling to every instance zip needs
    the full-instance dicts (`states_by_zip`, `M_by_zip`, `missing`) alongside it.
    """
    d: object                        # td.instance.Descaled
    zips: list                       # n geometric zips, sorted; xy/M/state_idx/labels0's order
    xy: np.ndarray                   # (n, 2)
    M: np.ndarray                    # (n,)
    state_idx: np.ndarray            # (n,) int, -1 for AK/HI/unknown
    labels0: np.ndarray              # (n,) int, the committed labelling, 0-based
    k: int
    state_list: list                 # state codes, index matches state_idx's values
    states_by_zip: dict              # {zip: state code, or "" if unknown} -- every instance zip
    M_by_zip: dict                   # {zip: M} -- every instance zip
    missing: list                    # instance zips with no gazetteer coordinate
    committed_full: dict             # {zip: "D0X"} -- the committed draw, every instance zip
    home: np.ndarray                 # (k,) int, home state index per district (-1 if none)
    owners: np.ndarray               # (n_states, k) bool, owner districts per state
    committed_rep_of: dict | None    # {"D0X": rep} from the committed metrics.json, if found


def load_committed(instance_path: str, draw_path: str,
                   geo_cache: str = geo.DEFAULT_DEST) -> Ctx:
    """The committed draw and everything a cell needs, loaded once.

    Reuses `run_draw.coordinates` for the gazetteer join, `us_maps.read_draw` for the committed
    `draw.csv`, and computes the committed draw's own owner sets (`_owner_sets`) so every later
    cell scores against the same reference districts.
    """
    d = descaled.load_descaled(instance_path)
    zips_all = sorted(d.G)
    M_by_zip = {z: float(d.G.nodes[z]["M"]) for z in zips_all}
    states_by_zip = {z: d.G.nodes[z].get("state") or "" for z in zips_all}

    xy_dict, missing = run_draw.coordinates(zips_all, geo_cache)
    committed_full = us_maps.read_draw(draw_path)

    have = [z for z in zips_all if z in xy_dict]
    xy = np.array([xy_dict[z] for z in have], float)
    M = np.array([M_by_zip[z] for z in have], float)
    labels0 = np.array([_label_of(committed_full[z]) for z in have], int)
    k = int(labels0.max()) + 1 if labels0.size else 0

    state_idx_of = {s: i for i, s in enumerate(_STATE_LIST)}
    state_idx = np.array([state_idx_of.get(states_by_zip[z], -1) for z in have], int)

    home, owners = _owner_sets(labels0, state_idx, M, k, len(_STATE_LIST))

    metrics_path = os.path.join(os.path.dirname(draw_path), "metrics.json")
    committed_rep_of = None
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as fh:
            committed_rep_of = json.load(fh).get("winner", {}).get("assignment") or None

    return Ctx(d=d, zips=have, xy=xy, M=M, state_idx=state_idx, labels0=labels0, k=k,
              state_list=list(_STATE_LIST), states_by_zip=states_by_zip, M_by_zip=M_by_zip,
              missing=missing, committed_full=committed_full, home=home, owners=owners,
              committed_rep_of=committed_rep_of)


# ---------------------------------------------------------------------- owner-set measurements
def _owner_metrics(ctx: Ctx, completed: dict) -> tuple:
    """`(outside_share, n_districts_outside_home_1pct, n_states_split, states_split)` for the
    labelling in `completed`, scored against the committed draw's `ctx.home`/`ctx.owners`.

    `outside_share` is the share of the *whole instance's* mass sitting in a district outside
    its own zip's state's owner set (an unknown-state zip pays no penalty and is never
    "outside", per `td.solvers.state_borders`'s contract).  `n_districts_outside_home_1pct`
    counts districts with more than 1% of their own mass from a state other than their home.
    `n_states_split` counts states with >=2 districts each holding >=1% of that state's mass,
    excluding a state whose own owner set already spans >=2 districts (a split there is not a
    border artifact -- that state is intentionally shared, e.g. CA/TX/NY/FL/NJ at k=18).
    """
    state_idx_of = {s: i for i, s in enumerate(ctx.state_list)}
    total_M = sum(ctx.M_by_zip.values()) or 1.0

    mass_outside = 0.0
    district_mass = np.zeros(ctx.k, float)
    district_mass_outside_home = np.zeros(ctx.k, float)
    state_mass: dict = {}
    state_district_mass: dict = {}

    for z, dist_name in completed.items():
        lab = _label_of(dist_name)
        m = ctx.M_by_zip[z]
        district_mass[lab] += m
        s = state_idx_of.get(ctx.states_by_zip.get(z, ""), -1)
        if s < 0:
            continue
        if not ctx.owners[s, lab]:
            mass_outside += m
        if ctx.home[lab] != s:
            district_mass_outside_home[lab] += m
        state_mass[s] = state_mass.get(s, 0.0) + m
        per = state_district_mass.setdefault(s, {})
        per[lab] = per.get(lab, 0.0) + m

    outside_share = mass_outside / total_M

    # The same share against the labelling's OWN owner sets (plurality home per district,
    # else the single top holder), since `refine` drifts its owner sets each round and the
    # two readings differ at large delta (`docs/CODEVERIFY_state_borders.md` F2).
    dist_state = np.zeros((ctx.k, len(ctx.state_list)), float)
    for s, per in state_district_mass.items():
        for lab, m in per.items():
            dist_state[lab, s] = m
    home_own = np.where(dist_state.sum(axis=1) > 0, dist_state.argmax(axis=1), -1)
    owners_own = np.zeros((len(ctx.state_list), ctx.k), bool)
    for s in state_district_mass:
        js = np.flatnonzero(home_own == s)
        owners_own[s, js if js.size else [int(dist_state[:, s].argmax())]] = True
    outside_share_own = float((dist_state.T * ~owners_own).sum()) / total_M

    n_home_1pct = int(np.sum((district_mass > 0)
                             & (district_mass_outside_home / np.maximum(district_mass, 1e-12)
                                > 0.01)))

    n_states_split, split_codes = 0, []
    for s, per in state_district_mass.items():
        tot = state_mass[s]
        if tot <= 0:
            continue
        n_big = sum(1 for m in per.values() if m / tot >= 0.01)
        if n_big >= 2 and int(ctx.owners[s].sum()) < 2:
            n_states_split += 1
            split_codes.append(ctx.state_list[s])

    return (outside_share, outside_share_own, n_home_1pct, n_states_split,
            ",".join(sorted(split_codes)))


# --------------------------------------------------------------------------------- the row
def cell_row(ctx: Ctx, labels: np.ndarray, name: str, params: dict, *,
            theta: float = THETA, lam: float = LAM,
            filler_capture: str = FILLER_CAPTURE) -> dict:
    """One grid row: complete `labels`, then measure it on the completed instance.

    Returns a flat dict: `name`, `spread_rel`, `max_dev_rel`, `nash` (`sum_j log M_j`), `gap`
    (`k*log(M/k) - nash`, the whole-instance Nash ceiling), `outside_owner_share`,
    `n_districts_outside_home_1pct`, `n_states_split`, `states_split` (comma-joined codes),
    `zips_changed` (vs the committed draw), `compactness` (`sum M*d^2` to `labels`'s own
    centroids, geometric zips only), `n_fractional` (from `params`), `stage2_value`,
    `n_unmatched_reps`, `stage2_theta`, `stage2_lam`, `stage2_filler` (the weights `stage2_value`
    was actually computed under), then every key of `params` (the cell's own settings and loop
    outcome, e.g. `delta`, `lam_rel`, `rounds_used`, `converged`), so the grid carries them.
    """
    completed = run_draw.complete(labels, ctx.zips, ctx.states_by_zip, ctx.missing,
                                  ctx.M_by_zip)

    report = channel.balance_report(ctx.d.G, completed)
    ideal = report["k"] * math.log(report["mean"]) if report["mean"] > 0 else math.inf
    gap = ideal - report["log_sum"]

    compactness = centers.metrics(ctx.M, labels, ctx.xy)["compactness"]
    zips_changed = sum(1 for z, dist in completed.items() if dist != ctx.committed_full.get(z))
    (outside_share, outside_share_own, n_home_1pct, n_states_split,
     states_split) = _owner_metrics(ctx, completed)

    stage2 = channel.stage2(ctx.d.G, completed, theta=theta, lam=lam,
                            filler_capture=filler_capture)

    row = dict(
        name=name,
        spread_rel=report["spread_rel"],
        max_dev_rel=report["max_dev_rel"],
        nash=report["log_sum"],
        gap=gap,
        outside_owner_share=outside_share,
        outside_owner_share_own=outside_share_own,
        n_districts_outside_home_1pct=n_home_1pct,
        n_states_split=n_states_split,
        states_split=states_split,
        zips_changed=zips_changed,
        compactness=compactness,
        n_fractional=int(params.get("n_fractional", 0)),
        stage2_value=stage2["value"],
        n_unmatched_reps=len(stage2["unmatched_reps"]),
        stage2_theta=theta,
        stage2_lam=lam,
        stage2_filler=filler_capture,
    )
    row.update({k: v for k, v in params.items() if k not in row})
    return row


# ------------------------------------------------------------------------------------ writing
def zip_rows(ctx: Ctx, completed: dict) -> list[dict]:
    """The cell's zip table (`td.ziptable`), from the context's instance and its geometry."""
    xy = {z: (float(p[0]), float(p[1])) for z, p in zip(ctx.zips, ctx.xy)}
    return ziptable.build(ctx.d, xy, completed)


def _write_draw_csv(path: str, ctx: Ctx, completed: dict) -> None:
    """`draw.csv`, the zip table for `completed` -- `zip,state,x,y,opportunity,district` sorted
    by zip.  `tools/us_maps.py` and the app read the two columns they always read; the four in
    between are what a map used to need the instance and the gazetteer for."""
    ziptable.write(path, zip_rows(ctx, completed))


def write_cell(out_dir: str, name: str, ctx: Ctx, labels: np.ndarray, completed: dict,
              iterates: list | None = None, steps: list | None = None) -> str:
    """`<out_dir>/<name>/draw.csv`, plus the per-round files `iterates` or `steps` asks for.

    Both take raw geometric label arrays in `ctx`'s own zip order and complete each the same way
    as `labels`, so every file written here is a zip table drawable on its own.  They differ
    only in naming: `iterates` is a bare list, written as `iterates/NN.csv` (Track 1's Lloyd
    rounds, `state_borders.refine`); `steps` is a list of `(step name, labels)` pairs, written
    as `steps/NN_<step name>.csv` with a final `NN_completed.csv` for `labels` itself.
    """
    cell_dir = os.path.join(out_dir, name)
    _write_draw_csv(os.path.join(cell_dir, "draw.csv"), ctx, completed)
    if iterates:
        for i, lab in enumerate(iterates):
            comp_i = run_draw.complete(lab, ctx.zips, ctx.states_by_zip, ctx.missing,
                                       ctx.M_by_zip)
            _write_draw_csv(os.path.join(cell_dir, "iterates", f"{i:02d}.csv"), ctx, comp_i)
    if steps:
        for i, (step_name, lab) in enumerate(list(steps) + [("completed", labels)], start=1):
            comp_i = run_draw.complete(lab, ctx.zips, ctx.states_by_zip, ctx.missing,
                                       ctx.M_by_zip)
            _write_draw_csv(os.path.join(cell_dir, "steps", f"{i:02d}_{step_name}.csv"),
                            ctx, comp_i)
    return cell_dir


def _fmt_grid_cell(v) -> str:
    return f"{v:.6g}" if isinstance(v, float) else str(v)


def write_grid(out_dir: str, rows: list) -> None:
    """`grid.csv` and `grid.md`, one row per cell in the order given (the committed map first,
    by convention -- `docs/BORDERS_PLAN.md`'s "Rows 0 and 1"). Columns are the union of the
    rows' keys in first-seen order, since the committed and snap rows carry no `delta`."""
    if not rows:
        raise ValueError("write_grid: no rows given")
    os.makedirs(out_dir, exist_ok=True)
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(out_dir, "grid.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(os.path.join(out_dir, "grid.md"), "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(cols) + " |\n")
        fh.write("|" + "|".join("---" for _ in cols) + "|\n")
        for r in rows:
            fh.write("| " + " | ".join(_fmt_grid_cell(r.get(c)) for c in cols) + " |\n")


# -------------------------------------------------------------------------------------- maps
def render_cell_maps(cell_dir: str, geo_cache: str = geo.DEFAULT_DEST, *,
                     states=None, steps: bool = False, report=None) -> Path:
    """`districts.png` and `district_regions_voronoi.png` from `cell_dir/draw.csv`, in-process.

    The cell's `draw.csv` is a zip table, so the maps come from `td.ziptable.render` with no
    instance, no gazetteer join and no subprocess.  Never the power diagram: the unpenalised one
    no longer matches a penalised labelling (`docs/BORDERS_PLAN.md`).  Per-state clipping and
    heavy state lines are `ziptable.render`'s own defaults, so a cell map always shows where the
    borders sit against state lines.  `steps=True` draws every `cell_dir/steps/*.csv` too, one
    directory per step.  `states` is the basemap; it is loaded here only if the caller has none
    to hand, since reading the shapefile per cell is the slowest thing in the loop.
    """
    if states is None:
        states = geo.states_outline(geo_cache)
    fig_dir = Path(cell_dir) / "figures"
    ziptable.render(ziptable.read(os.path.join(cell_dir, "draw.csv")), str(fig_dir), states,
                    report=report)
    if steps:
        for path in sorted(glob.glob(os.path.join(cell_dir, "steps", "*.csv"))):
            out = Path(cell_dir) / "steps" / "figures" / Path(path).stem
            ziptable.render(ziptable.read(path), str(out), states)
    return fig_dir
