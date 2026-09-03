"""run_draw.py -- the reproducible stage-1 draw: instance in, a staffed map out.

    .venv/bin/python3 tools/run_draw.py instance_descaled.json.gz --k 13 \\
        --seeds 0 1 2 3 4 --out battery/results/draw_k13_20260901/

    .venv/bin/python3 tools/run_draw.py instance_descaled.json.gz --k 8-16 \\
        --fix SOUTHWEST=TX,OK --anchor FLORIDA=FL --workers 8 --out battery/results/sweep/

One command for the whole pipeline, so a map is always reproducible from a run id::

    load instance          td.instance.load_descaled
    coordinates             td.geo.zcta_points  (cached under data/geo/, no network if present)
    hand-drawn districts    a --fix (closed) or --anchor (open) district, given by state
    stage 1                 td.solvers.centers.draw           one balanced draw per (k, seed)
    complete each draw      td.channel.place_by_state         the zips with no coordinates
    stage 2                 td.channel.score_draws            rank the draws by how they staff

`--k` takes a range (`8-16`) or a list (`8 10 13`); every k in it gets its own run, in its own
`k<kk>/` subdirectory of `--out`.  `--fix NAME=ST,ST` pins a **closed** district to exactly
those states (it never reaches the solver: its zips are removed and `k` is reduced by one for
the solver's purposes); `--anchor NAME=ST,ST` pins an **open** district -- those states are
locked in, and the solver adds zips to it until it reaches the run's common target, or fewer if
the locked states already carry more than that.  This is a *partial* hand-drawn pin: see
`docs/FRAME.md` §3 for the fully manual baseline, a different thing.

The ranking within one k is the point of running several seeds.  Stage 1 cannot see rep
relationships, so a draw that is beautifully balanced may staff badly; stage 2 is
milliseconds, so the portfolio is scored and the *best-staffing* draw wins, not the
best-balanced one (CLAUDE.md's mitigation for the two-stage split).  Both numbers are recorded
per draw in `metrics.json` so the cost of that choice is visible rather than assumed.

Written into `--out`:

    k<kk>/draw.csv       zip,district for k's winning draw -- every instance zip, including
                         the ones placed by state or pinned by a hand-drawn district.  This is
                         what tools/us_maps.py --districts reads (per k; `--regions`, the power
                         diagram, is only meaningful for solver/anchor districts, not fixed ones).
    k<kk>/metrics.json   k's per-draw stage-1 metrics, the stage-2 value and assignment, the
                         winner's balance report, the resolved scenario and its per-district
                         hand-drawn statistics, and the realised stage-1 targets.
    sweep.csv/.json      one row per k: balance statistics, Nash and stage-2 value, the
                         winning seed, and whether every district staffed.

District ids are the strings `D01`..`Dkk` for solver/anchor districts (anchors keep their own
name), not the raw 0-based labels, so the CSV, the JSON, the summary table and the figure's
direct labels all say the same word.  Exit status is nonzero if any k had an unstaffed
district -- that would mean fewer reps than districts, which is a data problem and must not
pass silently.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Literal

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..")))

from td import channel, geo                                                # noqa: E402
from td import instance as descaled                                        # noqa: E402
from td.solvers import centers                                             # noqa: E402


def district_id(label) -> str:
    """0-based stage-1 label -> `D01`.  One name for a district everywhere downstream."""
    return f"D{int(label) + 1:02d}"


def default_run_id(k, when=None) -> str:
    when = when or _dt.date.today()
    return f"draw_k{int(k)}_{when:%Y%m%d}"


# ------------------------------------------------------------------ the pipeline
def coordinates(zips, cache=geo.DEFAULT_DEST):
    """`(xy, missing)` -- projected LAEA points for the zips the gazetteer carries.

    `missing` is returned rather than raised: on the real instance it is 6 zips out of 1,229
    (retired or non-ZCTA codes), and they are placed afterwards by `channel.place_by_state`,
    not dropped.  Dropping them would quietly shrink the total opportunity the balance is
    measured against.
    """
    points = geo.zcta_points(cache)
    have = [z for z in zips if z in points]
    missing = [z for z in zips if z not in points]
    x, y = geo.project([points[z][0] for z in have], [points[z][1] for z in have])
    return {z: (float(a), float(b)) for z, a, b in zip(have, x, y)}, missing


# ------------------------------------------------------------------ hand-drawn scenarios
Mode = Literal["fix", "anchor", "solver"]


@dataclass(frozen=True)
class Scenario:
    """The resolved hand-drawn spec: district name -> the states pinned to it.

    `fix` districts are closed (exactly those states, never touched by the solver); `anchor`
    districts are open (those states locked in, the solver fills the rest to the common
    target).  A name and a state each appear in at most one of the two dicts combined --
    `load_scenario` enforces that before a `Scenario` is built.
    """
    fix: dict[str, tuple[str, ...]]
    anchor: dict[str, tuple[str, ...]]


_STATE_RE = re.compile(r"^[A-Z]{2}$")
_SOLVER_NAME_RE = re.compile(r"^D\d{2,}$")


def _check_states(name: str, states) -> tuple[str, tuple[str, ...]]:
    """Validate one `name: [states]` entry; shared by `parse_pin` and `load_scenario`'s JSON
    path so both take the same rules -- a stripped, non-empty, whitespace/comma-free name, and
    a non-empty list of 2-letter upper-cased state codes, de-duplicated in the order given."""
    name = name.strip()
    if not name or re.search(r"[\s,]", name):
        raise ValueError(f"invalid district name {name!r}")
    seen: list[str] = []
    for s in states:
        s = str(s).strip().upper()
        if not s:
            continue
        if not _STATE_RE.match(s):
            raise ValueError(f"invalid state code {s!r} for district {name!r}")
        if s not in seen:
            seen.append(s)
    if not seen:
        raise ValueError(f"no states given for district {name!r}")
    return name, tuple(seen)


def parse_pin(text: str) -> tuple[str, tuple[str, ...]]:
    """`"SOUTHWEST=TX,OK"` -> `("SOUTHWEST", ("TX", "OK"))`, as used by `--fix`/`--anchor`."""
    if "=" not in text:
        raise ValueError(f"missing '=' in pin {text!r}")
    lhs, _, rhs = text.partition("=")
    return _check_states(lhs, rhs.split(","))


def _parse_int_ranges(tokens: list[str], minimum: int) -> list[int]:
    """Each token is an `int` or an `a-b` range (`a <= b`); collect, de-duplicate, sort.

    Used by `parse_k` (`minimum=1`, since a k of 0 is meaningless) and `parse_seeds`
    (`minimum=0`).  Raises on an empty result, a malformed token, or a value below `minimum`.
    """
    out: set[int] = set()
    for tok in tokens:
        if "-" in tok:
            a_s, _, b_s = tok.partition("-")
            try:
                a, b = int(a_s), int(b_s)
            except ValueError:
                raise ValueError(f"malformed range {tok!r}") from None
            if a > b:
                raise ValueError(f"malformed range {tok!r}: {a} > {b}")
            vals = range(a, b + 1)
        else:
            try:
                vals = [int(tok)]
            except ValueError:
                raise ValueError(f"malformed value {tok!r}") from None
        for v in vals:
            if v < minimum:
                raise ValueError(f"value {v} is below the minimum {minimum}")
            out.add(v)
    if not out:
        raise ValueError("no values given")
    return sorted(out)


def parse_k(tokens: list[str]) -> list[int]:
    """`["8-16"]` -> `8..16`; `["8", "10"]` -> `[8, 10]`; sorted, unique, each `>= 1`."""
    return _parse_int_ranges(tokens, 1)


def parse_seeds(tokens: list[str]) -> list[int]:
    """`["0-4"]` -> `0..4`; sorted, unique, each `>= 0`."""
    return _parse_int_ranges(tokens, 0)


def load_scenario(path: str | None, fix: list[str], anchor: list[str]) -> Scenario:
    """Merge a `--scenario` JSON file with `--fix`/`--anchor` flags into one `Scenario`.

    The file, if given, has only the top-level keys `fix` and `anchor`, each `{name: [states]}`
    validated by `_check_states`; the flags are parsed by `parse_pin` and merged in after.  A
    district name defined twice (file vs. flags, or `fix` vs. `anchor`), a state pinned to two
    districts, or a name colliding with a solver id (`D07`, `D123`, ...) is a `ValueError`
    naming the offending name or state.
    """
    fix_d: dict[str, tuple[str, ...]] = {}
    anchor_d: dict[str, tuple[str, ...]] = {}
    seen_names: set[str] = set()
    state_owner: dict[str, str] = {}

    def _add(name: str, states, mode: str) -> None:
        name, states = _check_states(name, states)
        if _SOLVER_NAME_RE.match(name):
            raise ValueError(f"district name {name!r} collides with a solver id")
        if name in seen_names:
            raise ValueError(f"district {name!r} defined twice")
        for s in states:
            if s in state_owner:
                raise ValueError(f"state {s!r} assigned to both "
                                 f"{state_owner[s]!r} and {name!r}")
            state_owner[s] = name
        seen_names.add(name)
        (fix_d if mode == "fix" else anchor_d)[name] = states

    if path:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        extra = set(data) - {"fix", "anchor"}
        if extra:
            raise ValueError(f"unknown scenario key(s): {sorted(extra)}")
        for name, states in data.get("fix", {}).items():
            _add(name, states, "fix")
        for name, states in data.get("anchor", {}).items():
            _add(name, states, "anchor")

    for text in fix:
        name, states = parse_pin(text)
        _add(name, states, "fix")
    for text in anchor:
        name, states = parse_pin(text)
        _add(name, states, "anchor")

    return Scenario(fix=fix_d, anchor=anchor_d)


def expand_states(sc: Scenario, states: dict[str, str]) -> dict[str, str]:
    """`{zip: district name}` for every instance zip whose state is pinned by `sc`.

    Runs over **all** instance zips, coordinate-less ones included, so a hand-drawn state's
    zips are placed directly rather than falling through to `place_by_state`.  Warns to stderr
    for a pinned state with no zip in the instance at all -- a likely typo, not an error.
    """
    by_state = {st: name for name, sts in {**sc.fix, **sc.anchor}.items() for st in sts}
    out = {z: by_state[st] for z, st in states.items() if st in by_state}
    covered = {states[z] for z in out}
    for st, name in by_state.items():
        if st not in covered:
            print(f"warning: state {st} ({name}) has no zips in the instance", file=sys.stderr)
    return out


def solver_k(k: int, sc: Scenario) -> int:
    """`k` minus the fixed districts; raises if what is left cannot even fit the anchors."""
    ks = k - len(sc.fix)
    if ks < max(1, len(sc.anchor)):
        raise ValueError(f"k={k}: {len(sc.fix)} fixed districts leave {ks} for the solver, "
                         f"but {len(sc.anchor)} anchored districts need at least that many")
    return ks


# ------------------------------------------------------------------ the (k, seed) sweep
def draw_job(XY: np.ndarray, M: np.ndarray, k: int, seed: int,
            locked: np.ndarray | None) -> dict:
    """One `centers.draw` call -- the process-pool target, so it must stay module-level (macOS
    `spawn` pickles a target by its qualified name; the `__main__` guard below keeps a spawned
    child from re-running `main`)."""
    return centers.draw(XY, M, k, seed=seed, locked=locked)


def run_sweep(ks: list[int], seeds: list[int], XY, M, locked,
             workers: int) -> dict[int, list[dict]]:
    """Every `(k, seed)` draw, grouped by k and ranked best-Nash-first within each k.

    `ks` are **solver** k's (post `solver_k`). `workers <= 1` runs in-process, useful for
    debugging and for tests that must not fork; otherwise a `ProcessPoolExecutor` of that size.
    """
    jobs = [(k, s) for k in ks for s in seeds]
    if workers <= 1:
        results = [draw_job(XY, M, k, s, locked) for k, s in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(draw_job, XY, M, k, s, locked) for k, s in jobs]
            results = [f.result() for f in futures]
    by_k: dict[int, list[dict]] = {k: [] for k in ks}
    for (k, _s), res in zip(jobs, results):
        by_k[k].append(res)
    for rs in by_k.values():
        rs.sort(key=lambda r: -r["nash"])
    return by_k


def relabel(labels: np.ndarray, zips: list[str], anchor_names: list[str]) -> dict[str, str]:
    """A stage-1 labelling -> `{zip: district name}`; anchors keep their name, the rest become
    `D01..` counting from the first non-anchor label (anchors occupy labels `0..a-1`)."""
    a = len(anchor_names)
    return {z: (anchor_names[int(lab)] if int(lab) < a else district_id(int(lab) - a))
            for z, lab in zip(zips, labels)}


def complete(labels, placed_zips, states, missing, M, *, pinned=None, anchor_names=None) -> dict:
    """A stage-1 labelling -> the completed `{zip: district name}` mapping stage 2 consumes.

    `pinned` is `{zip: name}` for every hand-drawn zip absent from `placed_zips` (a fixed
    district's zips, plus a hand-drawn state's coordinate-less zips); it is applied last, so it
    always wins. `missing` should already exclude hand-drawn coordinate-less zips (the caller's
    `missing_free`) -- a fixed district is never a `place_by_state` candidate because it is
    absent from `placed_zips`/`relabel`'s output in the first place.
    """
    to_d = relabel(labels, placed_zips, anchor_names or [])
    out = channel.place_by_state(states, to_d, missing, M)
    out.update(pinned or {})
    return out


def _stage1_metrics(res, M_by_zip, placed_zips, completed) -> dict:
    """Stage-1 metrics as drawn, and again after the coordinate-less/hand-drawn zips are placed."""
    before = {k: v for k, v in res.items() if k not in ("labels", "centers")}
    per = {}
    for z, d in completed.items():
        per[d] = per.get(d, 0.0) + float(M_by_zip[z])
    vals = np.array([per[d] for d in sorted(per)], float)
    mean = float(vals.mean())
    return dict(
        seed=int(res["seed"]),
        before=before,
        after=dict(k=int(vals.size), total=float(vals.sum()), mean=mean,
                   min=float(vals.min()), max=float(vals.max()),
                   masses={d: float(per[d]) for d in sorted(per)},
                   nash=float(np.log(vals).sum()),
                   spread_rel=float((vals.max() - vals.min()) / mean),
                   max_dev_rel=float(np.abs(vals - mean).max() / mean)),
        n_placed_by_state=len(completed) - len(placed_zips),
    )


# ------------------------------------------------------------------ reporting
def summary_rows(completed, M_by_zip, states, assignment=None, *,
                 modes=None, gains=None, target=None) -> list:
    """Per district: id, mode, zips, M, share, balance vs. target, states, per-zip spread,
    staffing rep and gain.

    `modes` is `{district: "fix"|"anchor"}`; a district absent from it is `"solver"`.
    `target` defaults to the equal split `total / (number of districts)`; `vs_target` is
    `M / target - 1`. `max_zip_share`/`max_zip_M` and `median_zip_M` describe the district's
    own zip-size distribution, not its share of the total.
    """
    per, cnt, st, zip_M = {}, {}, {}, {}
    for z, d in completed.items():
        m = float(M_by_zip[z])
        per[d] = per.get(d, 0.0) + m
        cnt[d] = cnt.get(d, 0) + 1
        s = states.get(z) or "??"
        st.setdefault(d, {})[s] = st.setdefault(d, {}).get(s, 0) + 1
        zip_M.setdefault(d, []).append(m)
    total = sum(per.values()) or 1.0
    tgt = target if target is not None else total / (len(per) or 1)
    rows = []
    for d in sorted(per):
        top = max(sorted(st.get(d, {"??": 0})), key=lambda s: (st[d][s], s)) if st.get(d) \
            else "??"
        share = st.get(d, {}).get(top, 0) / cnt[d] if cnt.get(d) else 0.0
        ms = zip_M.get(d, [])
        max_m = max(ms) if ms else 0.0
        rows.append(dict(
            district=d, zips=cnt[d], M=per[d], share=per[d] / total,
            top_state=top, top_state_share=share,
            rep=(assignment or {}).get(d, ""),
            mode=(modes or {}).get(d, "solver"),
            vs_target=(per[d] / tgt - 1) if tgt else 0.0,
            n_states=len(st.get(d, {})),
            max_zip_M=max_m,
            max_zip_share=(max_m / per[d]) if per[d] else 0.0,
            median_zip_M=statistics.median(ms) if ms else 0.0,
            gain=(gains or {}).get(d),
        ))
    return rows


def print_summary(rows) -> None:
    staffed = any(r["rep"] for r in rows)
    wd = max([9] + [len(str(r["district"])) + 1 for r in rows])   # hand-drawn names are free-form
    head = (f"{'district':<{wd}}{'mode':<7}{'zips':>5}{'M':>12}{'share':>8}{'vs_tgt':>8}  "
            f"{'top state':<12}{'n_st':>5}  {'maxzip':>7}  ")
    print(head + ("rep" if staffed else ""))
    print("-" * (len(head) + (3 if staffed else 0)))
    for r in rows:
        top = "{} ({:.0%})".format(r["top_state"], r["top_state_share"])
        vs = f"{r['vs_target']:+.1%}"
        line = (f"{r['district']:<{wd}}{r['mode']:<7}{r['zips']:>5}{r['M']:>12,.1f}"
                f"{r['share']:>7.2%}{vs:>8}  {top:<12}{r['n_states']:>5}  "
                f"{r['max_zip_share']:>6.1%}  ")
        print(line + (str(r["rep"]) if staffed else ""))
    tot = sum(r["M"] for r in rows)
    n = len(rows) or 1
    lo, hi = min(r["M"] for r in rows), max(r["M"] for r in rows)
    print("-" * (len(head) + (3 if staffed else 0)))
    print(f"{'total':<{wd}}{'':<7}{sum(r['zips'] for r in rows):>5}{tot:>12,.1f}{1.0:>7.2%}  "
          f"spread {(hi - lo) / (tot / n):.3%}")


_SWEEP_COLS = ["k", "target", "min", "max", "mean", "median", "std", "cv", "spread_rel",
              "max_dev_rel", "n_within_5pct", "n_within_10pct", "nash", "stage2_value",
              "winner_seed", "n_unstaffed", "n_fixed", "n_anchor",
              "worst_hand_drawn_vs_target"]


def sweep_row(k: int, rows: list[dict], per_draw: list[dict], best: dict, sc: Scenario) -> dict:
    """One `sweep.csv` row for k: balance statistics over the winning draw's district masses,
    plus the stage-2 value, the winning seed, and the worst hand-drawn district's imbalance
    (`None` when there is none)."""
    vals = np.array([r["M"] for r in rows], float)
    total = float(vals.sum())
    target = total / k if k else 0.0
    mean = float(vals.mean())
    std = float(vals.std())
    vs_target = np.abs(vals / target - 1) if target else np.zeros_like(vals)
    hand_rows = [r for r in rows if r["mode"] != "solver"]
    return dict(
        k=k, target=target,
        min=float(vals.min()), max=float(vals.max()), mean=mean,
        median=float(np.median(vals)), std=std,
        cv=(std / mean) if mean else 0.0,
        spread_rel=((vals.max() - vals.min()) / mean) if mean else 0.0,
        max_dev_rel=(float(np.abs(vals - target).max()) / target) if target else 0.0,
        n_within_5pct=int((vs_target <= 0.05).sum()),
        n_within_10pct=int((vs_target <= 0.10).sum()),
        nash=float(np.log(vals).sum()),
        stage2_value=float(best["value"]),
        winner_seed=int(per_draw[best["draw"]]["seed"]),
        n_unstaffed=len(best["unstaffed_districts"]),
        n_fixed=len(sc.fix),
        n_anchor=len(sc.anchor),
        worst_hand_drawn_vs_target=(max(abs(r["vs_target"]) for r in hand_rows)
                                    if hand_rows else None),
    )


def write_sweep(out_dir: str, rows: list[dict], sc: Scenario, meta: dict) -> None:
    """`sweep.csv` (the `sweep_row` columns) and `sweep.json` (`meta` + the scenario + `rows`)."""
    with open(os.path.join(out_dir, "sweep.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_SWEEP_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    payload = {**meta,
              "scenario": {"fix": {n: list(s) for n, s in sc.fix.items()},
                           "anchor": {n: list(s) for n, s in sc.anchor.items()}},
              "rows": rows}
    with open(os.path.join(out_dir, "sweep.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=float)
        fh.write("\n")


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", nargs="?", default="instance_descaled.json.gz")
    ap.add_argument("--k", nargs="+", default=["13"],
                    help="district counts: a value, a list, or a range a-b (default 13)")
    ap.add_argument("--seeds", nargs="+", default=["0-4"],
                    help="stage-1 seeds: a value, a list, or a range a-b (default 0-4)")
    ap.add_argument("--fix", action="append", default=[],
                    help="NAME=ST,ST -- a closed hand-drawn district (repeatable)")
    ap.add_argument("--anchor", action="append", default=[],
                    help="NAME=ST,ST -- an open hand-drawn district (repeatable)")
    ap.add_argument("--scenario", default=None,
                    help="JSON file with top-level fix/anchor keys, merged with the flags")
    ap.add_argument("--workers", type=int, default=8,
                    help="process pool size for the (k, seed) sweep (default 8; 1 = serial)")
    ap.add_argument("--out", default=None,
                    help="output directory (default battery/results/sweep_<YYYYMMDD>/, or "
                         "draw_k<k>_<YYYYMMDD>/ for a single k)")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--theta", type=float, default=0.40, help="stage-2 theta")
    ap.add_argument("--lam", type=float, default=0.30, help="stage-2 lambda")
    ap.add_argument("--filler-capture", default="theta", help="stage-2 filler-capture mode")
    args = ap.parse_args(argv)

    ks = parse_k(args.k)
    seeds = parse_seeds(args.seeds)
    sc = load_scenario(args.scenario, args.fix, args.anchor)
    for k in ks:
        solver_k(k, sc)                      # validate every k before any work

    out_dir = args.out or os.path.join(
        "battery", "results",
        default_run_id(ks[0]) if len(ks) == 1 else f"sweep_{_dt.date.today():%Y%m%d}")
    os.makedirs(out_dir, exist_ok=True)

    d = descaled.load_descaled(args.instance)
    print(f"instance: {d.summary()}")
    zips = sorted(d.G)
    M_by_zip = {z: float(d.G.nodes[z]["M"]) for z in zips}
    states = {z: d.G.nodes[z].get("state") or "" for z in zips}

    xy, missing = coordinates(zips, args.geo_cache)
    print(f"geometry: {len(xy):,} of {len(zips):,} zips have gazetteer coordinates; "
          f"{len(missing)} placed by state" + (f" {missing}" if missing else ""))

    hand = expand_states(sc, states)
    anchor_names = list(sc.anchor)
    open_zips = [z for z in zips if z in xy and hand.get(z) not in sc.fix]
    XY = np.array([xy[z] for z in open_zips], float)
    M = np.array([M_by_zip[z] for z in open_zips], float)

    if anchor_names:
        locked = np.array([anchor_names.index(hand[z]) if z in hand else -1
                           for z in open_zips], int)
        present = set(locked.tolist())
        absent = [name for i, name in enumerate(anchor_names) if i not in present]
        if absent:
            raise ValueError(f"anchor district(s) {absent} have no zip with coordinates")
    else:
        locked = None

    pinned = {z: hand[z] for z in zips if z in hand and z not in open_zips}
    missing_free = [z for z in missing if z not in hand]

    n_fixed_zips = sum(1 for z in zips if hand.get(z) in sc.fix)
    n_anchor_zips = int((locked >= 0).sum()) if locked is not None else 0
    n_pinned_coordless = sum(1 for z in pinned if z not in xy)
    print(f"scenario: {len(sc.fix)} fixed district(s) ({n_fixed_zips} zips), "
          f"{len(sc.anchor)} anchored district(s) ({n_anchor_zips} zips), "
          f"{len(open_zips)} solver zips, {n_pinned_coordless} pinned coordinate-less")

    modes: dict[str, str] = {n: "fix" for n in sc.fix} | {n: "anchor" for n in sc.anchor}

    t0 = _dt.datetime.now()
    by_k = run_sweep([solver_k(k, sc) for k in ks], seeds, XY, M, locked, args.workers)
    elapsed = (_dt.datetime.now() - t0).total_seconds()
    print(f"stage 1: {len(ks)} k value(s) x {len(seeds)} seed(s) in {elapsed:.1f}s")

    sweep_rows = []
    any_unstaffed = False
    for k in ks:
        ks_solver = solver_k(k, sc)
        ranked1 = by_k[ks_solver]
        draws, per_draw = [], []
        for res in ranked1:
            completed = complete(res["labels"], open_zips, states, missing_free, M_by_zip,
                                 pinned=pinned, anchor_names=anchor_names)
            draws.append(completed)
            per_draw.append(_stage1_metrics(res, M_by_zip, open_zips, completed))
            m = per_draw[-1]
            print(f"  k={k} seed {m['seed']}: spread {m['before']['spread_rel']:.3%} drawn -> "
                  f"{m['after']['spread_rel']:.3%} completed, nash {m['after']['nash']:.6f}")

        print(f"stage 2 (k={k}): Hungarian on log gains")
        ranked2 = channel.score_draws(d.G, draws, theta=args.theta, lam=args.lam,
                                      filler_capture=args.filler_capture)
        for r in ranked2:
            per_draw[r["draw"]]["stage2_value"] = float(r["value"])
            per_draw[r["draw"]]["stage2_unstaffed"] = list(r["unstaffed_districts"])
        best = ranked2[0]
        winner, wm = draws[best["draw"]], per_draw[best["draw"]]
        print(f"  best: seed {wm['seed']} (draw {best['draw']}), value {best['value']:.6f}; "
              f"stage-1-best seed was {per_draw[0]['seed']}")

        target = sum(M_by_zip.values()) / k
        rows = summary_rows(winner, M_by_zip, states, best["assignment"],
                            modes=modes, gains=best["gains"], target=target)
        print(f"\n== k={k} ==")
        print_summary(rows)

        k_dir = os.path.join(out_dir, f"k{k:02d}")
        os.makedirs(k_dir, exist_ok=True)
        draw_csv = os.path.join(k_dir, "draw.csv")
        with open(draw_csv, "w", encoding="utf-8") as fh:
            fh.write("zip,district\n")
            for z in sorted(winner):
                fh.write(f"{z},{winner[z]}\n")

        stage1_targets_list = wm["before"]["targets"]
        name_order = anchor_names + [district_id(j)
                                     for j in range(len(stage1_targets_list) - len(anchor_names))]
        stage1_targets = {name: float(t) for name, t in zip(name_order, stage1_targets_list)}

        metrics_out = dict(
            run_id=os.path.basename(os.path.normpath(k_dir)),
            written=_dt.datetime.now().isoformat(timespec="seconds"),
            instance=os.path.abspath(args.instance),
            k=k, seeds=list(seeds),
            theta=args.theta, lam=args.lam, filler_capture=args.filler_capture,
            n_zips=len(zips), n_with_coordinates=len(xy), n_solver_zips=len(open_zips),
            placed_by_state={z: winner[z] for z in missing_free},
            winner=dict(draw=int(best["draw"]), seed=int(wm["seed"]),
                       stage2_value=float(best["value"]),
                       assignment={n: str(v) for n, v in best["assignment"].items()},
                       unmatched_reps=[str(r) for r in best["unmatched_reps"]],
                       unstaffed_districts=list(best["unstaffed_districts"]),
                       balance_report=best["balance"],
                       gains=best["gains"]),
            draws=per_draw,
            summary=rows,
            scenario={"fix": {n: list(s) for n, s in sc.fix.items()},
                     "anchor": {n: list(s) for n, s in sc.anchor.items()}},
            k_solver=ks_solver,
            hand_drawn=[r for r in rows if r["mode"] != "solver"],
            stage1_targets=stage1_targets,
        )
        with open(os.path.join(k_dir, "metrics.json"), "w", encoding="utf-8") as fh:
            json.dump(metrics_out, fh, indent=2, sort_keys=False, default=float)
            fh.write("\n")
        print(f"wrote {draw_csv} and {os.path.join(k_dir, 'metrics.json')}")

        sweep_rows.append(sweep_row(k, rows, ranked1, best, sc))
        if best["unstaffed_districts"]:
            any_unstaffed = True
            print(f"ERROR: k={k}: {len(best['unstaffed_districts'])} district(s) unstaffed: "
                  f"{best['unstaffed_districts']}", file=sys.stderr)

    print()
    print(f"{'k':>4}{'target':>14}{'min':>12}{'max':>12}{'spread':>9}{'cv':>8}"
          f"{'within10':>10}{'nash':>12}{'stage2':>10}{'unstaffed':>11}")
    for r in sweep_rows:
        print(f"{r['k']:>4}{r['target']:>14,.1f}{r['min']:>12,.1f}{r['max']:>12,.1f}"
              f"{r['spread_rel']:>9.2%}{r['cv']:>8.3f}{r['n_within_10pct']:>10}"
              f"{r['nash']:>12.4f}{r['stage2_value']:>10.4f}{r['n_unstaffed']:>11}")

    write_sweep(out_dir, sweep_rows, sc,
               meta=dict(run_id=os.path.basename(os.path.normpath(out_dir)),
                         written=_dt.datetime.now().isoformat(timespec="seconds"),
                         instance=os.path.abspath(args.instance), ks=ks, seeds=seeds,
                         theta=args.theta, lam=args.lam, filler_capture=args.filler_capture,
                         workers=args.workers, elapsed_s=elapsed))
    print(f"\nwrote {out_dir}")

    return 1 if any_unstaffed else 0


if __name__ == "__main__":
    sys.exit(main())
