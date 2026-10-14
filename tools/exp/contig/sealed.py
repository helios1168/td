"""sealed.py -- the sealed-region driver (2026-10-14): a map drawn region by region and merged,
each district inside one region (owner, 2026-10-13: regional sealing for the main map).

    "$TD_PY" -u tools/exp/contig/sealed.py run --partition P.json --root DIR --host m5|m2
        [--slots N] [--hours H] [--only ID ...] [--extract PATH] [--max-size N] [--forbid A-B ...]
        [--shape-limits L.json] [--no-window-band] [--dry-run]
    "$TD_PY" tools/exp/contig/sealed.py index --root DIR      (`collect` is the same command)

**The partition** (`P.json`): `{"points": [{"id", "structure", "channels": {<channel>: {"regions":
[{"name", "states": [...], "k", "k_alt"?, "forbid"?: ["DE-VA"]}], "rest": bool, "k_total"?}}]}}`.
`structure` is one of `overnight.STRUCTURES` (its base spec and split rule).  Every channel of the
structure is listed.  A region's `states` are disjoint from the channel's other regions' and hold
at least one of its footprint states; `rest: true` adds the region of the channel's footprint states
in no region, with `k_total` (the channel's K over the whole map, default the K of the
`overnight.POINTS` entry of the same id) less the regions' K; `rest: false` needs every footprint
state in a region.  The channels are partitioned independently: a channel's regions need not
match another channel's state sets or names.  Channels whose regions have one state set are drawn
together in one run (named for the region, or the regions' names joined by `-`); any other run holds
only the channels of its regions, on `extract.json.gz`, a copy of the extract cut to their fine
channels, so a channel outside the run is not drawn there.  When the runs' state sets are pairwise
disjoint and each holds every channel with footprint states in it, `merge.py` takes the runs' last
folders as its sources; otherwise `combined/` is written first (stage `combine`, `sealed.py combine`, a capped child): one ledger with each (ZCTA, fine
channel) cell from the run that owns its planning channel in the ZCTA's state (district ids
prefixed by the run), which `merge.py` takes as its one source.  Point ids and region names may
not be a name the driver writes itself (`merged`, `combined`, `spec-merge.toml`, `SEALED.json`,
...).  `validate_partition` refuses anything else, naming it.

**A run** (one state set of a point; the unit of work and of the scheduler) is, in
`<root>/<point>/<run>/`, each stage a child process killed at its wall cap (`CAPS`, `--cap`), logging
to `<stage>.log` (trap 15; a hung HiGHS, as NY+NJ at K 7 on 2026-10-13, is killed, not waited for):

1. the spec copy `spec-base.toml`: the structure's base spec with each present channel's k the
   region's, `margin = false`, the final δ `overnight.fit_delta` gives the region's τ (region $ over
   k, from the dollar extract as `overnight.plan_point` computes it) in the channel's dollar window
   (`score.WINDOWS`), and, by default (`--window-band`, owner's approval, #112 comment, 2026-10-14;
   `--no-window-band` turns it off), `band_lo` = L/τ and `band_hi` = U/τ: the band of the master, the
   draw, the repair and the audit is the dollar window itself, never ±δ or wider (the δ keys are then
   for reporting), the declared δ `overnight.DECLARED_DELTA` or the final δ when smaller, the
   split list the rule's or the base's on the region's states, `--max-size` and the forbid pairs
   (`--forbid` and the region's) with both states in the run.  A channel with no cell in the run is
   dropped by the spec build; its lines stay as the base has them.
2. `replan` (`sealed.py replan`: `replan.py` itself with its instance built on the polygon graph
   induced on the run's states, since `replan.py` alone plans the full graph, which a region's K does
   not fit): the master per channel at the declared δ, else the smallest feasible δ up to the final δ
   (never wider, the band is the owner's), the plans cached for `run.py --plans`.  `--drawable-alone`
   (#124 B) is on by default (`--no-drawable-alone` turns it off): the master plans only supports that
   `plancheck.drawable` shows can be drawn alone, connected and without a neck; its bans and
   unknowns per channel are in the run's `plan` record (and `replan.json`).
3. `run.py --states` into `draw/` (arm 1, sequential, `overnight.LAND_RATIO`).  The drawing is strict
   (owner, 2026-10-14: contiguity at the solver level): `draw.py` gives the ZCTAs of a group with no
   connected drawing to a non-contiguous fallback, so after every draw `contig.json` is read
   (`drawing_failures`): a channel with `undrawn_zctas` or a status other than optimal/connected is a
   failure, and a failed drawing is never repaired or merged; a drawing that succeeded but leaves
   detached pieces (`connected` false, `fixed_split` districts) goes on to the repair and the glue.  When the region lists `k_alt` for a failing channel, K moves to `k_alt` and the run is
   drawn once more in `alt/`, only if `k_alt` has a final δ in the window (the region's feasible set,
   `fit_delta`); the drawing with fewer failing channels goes on.  If it still fails the run, and the
   point, end `no connected drawing` with the groups' details.  The band never widens.
4. `repair.py --states` pass 1 into `r1/`, pass 2 into `r2/` when a channel of `r1/` is still in
   pieces or necked (`contig.json`).  `--window` is `score.WINDOWS` in $M for a run of one channel
   only (the repair intersects every channel's band with one window); the final δ already fits each
   channel's window.
5. glue repair (`glue.py`) into `glue/`: detached pieces joined through zero-opportunity ZCTAs of
   other districts, applied only when no donor gains or enlarges a piece or a neck; what it leaves is in
   `glue.json` for the owner.  A `glue/` folder is reused on a resume only when its manifest says
   done and, if it moved a ZCTA, its ledger is written; an interrupted one is moved aside.

**A point** is finished when its runs are: `merge.py` over every run's last folder into `merged/`
(`--rate 1`, `--gap-width`, `--window` for one channel), the gate (`tools/mandates/check.py`),
`score.py` (`score.txt`, `dollars.csv`, `m1.json`), `land.py`, and the per-district shape measures
of `tools/looks/study.py` (stage `shape`, `sealed.py shape`: a child killed at its cap or the
`--hours` stop; every district's row in `shape-districts.json` and `.csv` beside the merged ledger,
the channel summary and the limit breaches in `shape.json`).  **Labels**: `fails M1` (the gap-width
verdict of `m1.json`), else `outside band` (a district outside its channel's dollar window,
`dollars.csv`), else `ineligible` (`score.txt`'s `eligible: no` with its reasons, such as a main
map K outside the allowed range), else `passes`; `fails shape` instead when the shape limits file
says `"hard": true` and a district breaches one (a missing or non-finite value of a hard-limited measure is an `error`); `no connected drawing` (a run whose drawing failed as above, with no `k_alt` that drew),
`infeasible` (a run with no plan inside its window), `stopped` (a stage's cap or the `--hours` stop), `error` otherwise.
Shape limits (`L.json`: `{"hard": false, "limits": {<study column>: {"min": x, "max": y}}}`) are
parameters, not decisions: with no file, or `"hard": false`, the shape is reported and decides
nothing.

`SEALED.json` (atomic, `overnight.Grid`) holds every point's runs, stages and label; a second `run`
resumes: a labelled point is kept, a finished stage folder is not redone, an unfinished one is moved
aside (`overnight.set_aside`).  `--dry-run` prints each run's spec copy and every command, writes
nothing and solves nothing.  `index` writes `<root>/SEALED.md`: per point and channel the regions,
K, M1 verdict, band, splits, shape and label.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import csv
import datetime
import hashlib
import importlib.util
import json
import math
import os
import pickle
import re
import shlex
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data, geo, output  # noqa: E402
from td import spec as tdspec  # noqa: E402


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


overnight = _load("contig_overnight", os.path.join(HERE, "overnight.py"))
score = overnight.score
child, Grid, schedule, fit_delta, Stop = (overnight.child, overnight.Grid, overnight.schedule,
                                          overnight.fit_delta, overnight.Stop)

HUB = overnight.HUB
NAME = "sealed"
SEALED_ROOT = os.path.join(HUB, "runs", "exp", NAME)
STATE_JSON = "SEALED.json"
INDEX_MD = "SEALED.md"
CAPS = {"replan": 600.0, "draw": 2700.0, "repair": 1800.0, "glue": 600.0, "combine": 600.0, "merge": 3600.0,
        "shape": 1800.0}
DRAW_FRAC = 0.85                # run.py's per-channel time limit, of the draw's wall cap
NO_DRAWING = "no connected drawing"
LABELS = ("passes", "fails M1", "outside band", "ineligible", "fails shape", NO_DRAWING, "infeasible", "stopped",
          "error")
RUN_BAD = ("error", "stopped", NO_DRAWING, "infeasible")   # a run's failing statuses, worst first
DRAWN_OK = ("optimal", "connected")        # a group or channel drawing the owner accepts (2026-10-14: contiguity at the solver)
STRUCTURES = {k: (os.path.join(ROOT, p), rule) for k, (p, rule) in overnight.STRUCTURES.items()}
GAP_ENV = overnight.GAP_ENV
SHAPE_ROWS = "shape-districts.json"     # every district's study measures, beside the merged ledger (+ .csv)
POINT_NAMES = ("SEALED.json", "SEALED.json.tmp", "SEALED.md", "_plans")     # written in the root
RUN_NAMES = ("alt", "merged", "combined", "spec-merge.toml", "merged_extract.json.gz", "merge.log", "gate.log",
             "land.log", "shape.log", "launcher_error.txt")                # written in a point's folder


class PartitionError(ValueError):
    """P.json (or a region's numbers) the driver refuses; the message lists every problem."""


# ------------------------------------------------------------------------------ the partition
def _states_of(x, where: str, errs: list) -> tuple:
    if not isinstance(x, list) or not x or not all(isinstance(s, str) for s in x):
        errs.append(f"{where}: states must be a non-empty list of state codes")
        return ()
    bad = sorted(s for s in x if s not in tdspec.CONUS_STATES)
    if bad:
        errs.append(f"{where}: not CONUS states: {', '.join(bad)}")
    twice = sorted({s for s in x if x.count(s) > 1})
    if twice:
        errs.append(f"{where}: lists {', '.join(twice)} twice")
    return tuple(sorted(set(x)))


def _count(x, where: str, errs: list) -> int | None:
    if isinstance(x, bool) or not isinstance(x, int) or x < 1:
        errs.append(f"{where}: must be an integer of 1 or more, not {x!r}")
        return None
    return x


def _taken(name: str, owned) -> bool:
    """True when `name` is one of the `owned` names, ignoring case (a Mac volume is case-insensitive)
    and the `.stale<N>` suffix `overnight.set_aside` adds."""
    return re.sub(r"\.stale\d+$", "", name).casefold() in {x.casefold() for x in owned}


def parse_pair(text: str) -> tuple:
    """("DE", "VA") from "DE-VA" or "VA-DE"."""
    a, sep, b = text.partition("-")
    if not sep or not a or not b or a == b or not (a in tdspec.CONUS_STATES and b in tdspec.CONUS_STATES):
        raise PartitionError(f"a forbid pair is two CONUS states joined by '-', not {text!r}")
    return tuple(sorted((a, b)))


def validate_partition(doc: dict, structures: dict | None = None, totals: dict | None = None,
                       load=tdspec.load) -> list:
    """The points of `doc` (P.json) normalised, or `PartitionError` naming every problem: per point
    `{id, structure, base, rule, channels: {c: {regions, rest_states, rest_k, k_total}}, runs:
    [{name, states, ks, k_alt, forbid}], aligned}` (`_group_runs`).  `structures` {name: (base spec path, split rule)}
    (default `STRUCTURES`), `totals` {point id: {channel: K over the whole map}} (default
    `overnight.POINTS`), `load` the spec loader."""
    structures = STRUCTURES if structures is None else structures
    if totals is None:
        totals = {p["id"]: p["k"] for p in overnight.POINTS}
    errs, out, seen_ids = [], [], set()
    if not isinstance(doc, dict) or not isinstance(doc.get("points"), list) or not doc["points"]:
        raise PartitionError("P.json needs a non-empty list under 'points'")
    for p in doc["points"]:
        pid, structure = p.get("id"), p.get("structure")
        if not isinstance(pid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", pid) or _taken(pid, POINT_NAMES):
            errs.append(f"point {pid!r}: the id must be a file-name word other than the driver's own "
                        f"({', '.join(POINT_NAMES)})")
            continue
        if pid.casefold() in seen_ids:     # a Mac volume is case-insensitive: Pt and pt are one folder
            errs.append(f"point {pid}: listed twice (ids are compared ignoring case)")
        seen_ids.add(pid.casefold())
        if structure not in structures:
            errs.append(f"point {pid}: structure {structure!r} is not one of {sorted(structures)}")
            continue
        base, rule = structures[structure]
        sp = load(base)
        foot = {c: frozenset(cs.domain) for c, cs in sp.channels.items()}
        chans = p.get("channels")
        if not isinstance(chans, dict):
            errs.append(f"point {pid}: 'channels' must be an object")
            continue
        errs += [f"point {pid}: channel {c} of {structure} is not listed" for c in sorted(set(foot) - set(chans))]
        errs += [f"point {pid}: {c} is not a channel of {structure}" for c in sorted(set(chans) - set(foot))]
        entries, norm = [], {}                  # (channel, name or None, states, k, k_alt, forbid, rest)
        for c in sorted(set(chans) & set(foot)):
            ch = chans[c]
            where = f"point {pid} {c}"
            regions, taken, ksum = [], {}, 0
            if not isinstance(ch, dict) or not isinstance(ch.get("regions", []), list):
                errs.append(f"{where}: needs an object with a list 'regions'")
                continue
            names = [r.get("name") for r in ch.get("regions", [])]
            for r in ch.get("regions", []):
                name = r.get("name")
                rw = f"{where} region {name!r}"
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or _taken(name, RUN_NAMES):
                    errs.append(f"{rw}: the name must be a file-name word other than the driver's own "
                                f"({', '.join(RUN_NAMES)})")
                    continue
                if names.count(name) > 1:
                    errs.append(f"{rw}: name used twice in {c}")
                sts = _states_of(r.get("states"), rw, errs)
                if sts and not set(sts) & foot[c]:
                    errs.append(f"{rw}: none of its states is in {c}'s footprint")
                for s in sts:
                    if s in taken:
                        errs.append(f"{rw}: {s} is also in region {taken[s]!r}")
                    taken[s] = name
                k = _count(r.get("k"), f"{rw} k", errs)
                k_alt = r.get("k_alt")
                if k_alt is not None:
                    k_alt = _count(k_alt, f"{rw} k_alt", errs)
                    if k_alt is not None and k_alt == k:
                        errs.append(f"{rw}: k_alt equals k")
                forbid = []
                for x in r.get("forbid", []):
                    try:
                        forbid.append(parse_pair(x))
                    except PartitionError as e:
                        errs.append(f"{rw}: {e}")
                if sts and k:
                    ksum += k
                    regions.append({"name": name, "states": sts, "k": k, "k_alt": k_alt, "forbid": forbid})
                    entries.append((c, name, sts, k, k_alt, forbid, False))
            rest = ch.get("rest")
            if not isinstance(rest, bool):
                errs.append(f"{where}: 'rest' must be true or false")
                continue
            rest_states = tuple(sorted(foot[c] - set(taken)))
            k_total = ch.get("k_total", totals.get(pid, {}).get(c))
            rest_k = None
            if rest:
                if not rest_states:
                    errs.append(f"{where}: rest is true but every footprint state is in a region")
                elif k_total is None:
                    errs.append(f"{where}: rest needs k_total (the point is not in overnight.POINTS)")
                else:
                    kt = _count(k_total, f"{where} k_total", errs)
                    if kt is not None and kt - ksum < 1:
                        errs.append(f"{where}: k_total {kt} less the regions' {ksum} leaves no district for the rest")
                    elif kt is not None:
                        rest_k = kt - ksum
                        entries.append((c, None, rest_states, rest_k, None, [], True))
            else:
                if rest_states:
                    errs.append(f"{where}: rest is false and {', '.join(rest_states)} are in no region")
                if "k_total" in ch and ch["k_total"] != ksum:
                    errs.append(f"{where}: k_total {ch['k_total']} is not the regions' {ksum}")
            norm[c] = {"regions": regions, "rest": rest, "rest_states": rest_states if rest else (),
                       "rest_k": rest_k, "k_total": k_total}
        runs, aligned = _group_runs(pid, entries, foot, errs)
        out.append({"id": pid, "structure": structure, "base": base, "rule": rule, "channels": norm, "runs": runs,
                    "aligned": aligned})
    if errs:
        raise PartitionError("\n".join(errs))
    return out


def _group_runs(pid: str, entries: list, foot: dict, errs: list) -> tuple:
    """(runs, aligned) of one point from its (channel, name, states, k, k_alt, forbid, rest) entries.
    The channels are partitioned independently; a run is one state set, holding the channels whose
    regions have it.  `aligned`: the runs' state sets are pairwise disjoint and each run holds every
    channel with footprint states in it, so `merge.py` can take the runs' folders as its sources."""
    by = collections.OrderedDict()
    for c, name, sts, k, k_alt, forbid, rest in entries:
        r = by.setdefault(frozenset(sts), {"states": sts, "names": set(), "ks": {}, "k_alt": {}, "forbid": set(),
                                            "rest": []})
        if not rest:
            r["names"].add(name)
        else:
            r["rest"].append(c)
        r["ks"][c] = k
        if k_alt:
            r["k_alt"][c] = k_alt
        r["forbid"] |= set(forbid)
    rest_sets = [r for r in by.values() if not r["names"]]
    runs = []
    for r in by.values():
        name = ("-".join(sorted(r["names"])) if r["names"] else
                "rest" if len(rest_sets) == 1 else "rest-" + "-".join(sorted(r["rest"])))
        runs.append({"name": name, "states": r["states"], "ks": r["ks"], "k_alt": r["k_alt"],
                     "forbid": sorted(r["forbid"])})
    same = [sum(x["name"].casefold() == r["name"].casefold() for x in runs) > 1 for r in runs]
    for r, dup in zip(runs, same):      # one name for different state sets (the channels' regions are independent)
        if dup:
            r["name"] += "-" + "-".join(sorted(r["ks"]))
    names = [r["name"].casefold() for r in runs]
    errs += [f"point {pid}: two runs are named {n!r}" for n in sorted({n for n in names if names.count(n) > 1})]
    errs += [f"point {pid}: the run name {r['name']!r} is one the driver writes itself ({', '.join(RUN_NAMES)})"
             for r in runs if _taken(r["name"], RUN_NAMES)]
    aligned = True
    for i, a in enumerate(runs):
        aligned &= all(not set(a["states"]) & set(b["states"]) for b in runs[i + 1:])
        aligned &= all(c in a["ks"] for c, fs in foot.items() if fs & set(a["states"]))
    return runs, aligned


def load_partition(path: str, **kw) -> list:
    with open(path, encoding="utf-8") as fh:
        return validate_partition(json.load(fh), **kw)


# ------------------------------------------------------------------------------ a run's spec copy
def region_plan(sp, states, ks: dict, cells: dict, rule: str, window_band: bool = False) -> dict:
    """`overnight.plan_point` on the run's states: per present channel (one of `ks` with mass in the
    states) K, the region's $M, τ, the split list (the rule's, or the base's, on the states) and the
    final δ; `infeasible` {channel: why}; `absent` the channels of `ks` with no cell there; `outside`
    the channels not in `ks` that have cells there (another region's, cut from the run's extract).
    With `window_band` each channel also has `band_lo`, `band_hi` (`overnight.plan_point`)."""
    S = set(states)
    cs = {k: m for k, m in cells.items() if k[0] in S}
    mass = overnight.unit_mass(sp, cs)
    has = sorted(c for c in sp.channels if math.fsum(mass[c].values()) > 0)
    present = [c for c in has if c in ks]
    sub = dataclasses.replace(sp, channels={c: sp.channels[c] for c in present})
    plan = overnight.plan_point({c: ks[c] for c in present}, sub, cs, rule, window_band=window_band)
    for v in plan["channels"].values():
        v["free"] = [u for u in v["free"] if u in S]
    plan["absent"] = sorted(set(ks) & (set(sp.channels) - set(present)))
    plan["outside"] = sorted(set(has) - set(ks))
    return plan


def run_fine(sp, channels) -> set:
    """The fine channels in the domains of `channels` of the spec `sp`."""
    return {f for c in channels for fs in sp.channels[c].domain.values() for f in fs}


def run_cells(sp, channels) -> set:
    """{(state, fine channel)} the domains of `channels` of the spec `sp` give them: a fine channel
    can belong to one planning channel in a state and another in the next (`main_ne_plains`'
    national_chase: national in CA, WIFI in CT)."""
    return {(u, f) for c in channels for u, fs in sp.channels[c].domain.items() for f in fs}


def zip_states() -> dict:
    """{ZCTA: state} over M1's vertex set, as `overnight.state_cells` places the extract's cells."""
    ref = geo.read_reference()
    ref = ref[ref["graph_vertex"] == "1"]
    return dict(zip(ref["zcta"], ref["state"]))


def cut_extract(src: str, dst: str, cells, state_of: dict) -> str:
    """`dst`: the extract `src` less the cells whose (state of the ZCTA, fine channel) is not in
    `cells` (`run_cells`: the planning channel that owns a cell is the state's, not the fine
    channel's), written atomically; a ZCTA with no state in `state_of` is judged by its fine channel
    alone (`td.spec.build` places only the vertex set).  A channel whose cells are all gone is
    dropped by the spec build."""
    ext = data.load(src)
    fine = {f for _, f in cells}
    rows = [i for i, (z, f) in enumerate(zip(ext.z, ext.channel))
            if ((state_of[z], f) in cells if z in state_of else f in fine)]
    kept = {ext.channel[i] for i in rows}
    cut = dataclasses.replace(
        ext, channels=tuple(f for f in ext.channels if f in kept), z=[ext.z[i] for i in rows],
        channel=[ext.channel[i] for i in rows], m_rel=[ext.m_rel[i] for i in rows],
        share=[ext.share[i] for i in rows], share_free=[ext.share_free[i] for i in rows])
    data.write(cut, dst + ".tmp")
    os.replace(dst + ".tmp", dst)
    return dst


def run_spec_text(base_text: str, pid: str, run_name: str, states, plan: dict, forbid=(),
                  max_size: int | None = None) -> str:
    """The run's spec copy: the base TOML with each present channel's K, declared δ
    (`overnight.DECLARED_DELTA`, or the final δ when smaller), final δ, split list, `margin = false`,
    `max_size` when given and the forbid pairs with both states in the run; named `<point>-<run>`.
    A channel of `plan` with `band_lo`, `band_hi` (`region_plan(window_band=True)`) gets them as its
    band, the dollar window [L, U] (owner, #112 comment, 2026-10-14); its δ keys are then for
    reporting."""
    ch, S = plan["channels"], set(states)
    if plan["infeasible"]:
        raise PartitionError("no spec copy for a region outside the window: " + "; ".join(plan["infeasible"].values()))
    pairs = sorted({tuple(sorted(p)) for p in forbid if set(p) <= S})
    keys = {c: {"k": str(v["k"]), "margin": "false", **({"max_size": str(max_size)} if max_size else {}),
                **overnight.window_keys(v)} for c, v in ch.items()}
    body = overnight._replan().banned_text(
        base_text, [], deltas={c: min(overnight.DECLARED_DELTA, v["final_delta"]) for c, v in ch.items()},
        extra={c: pairs for c in ch} if pairs else None, free={c: v["free"] for c, v in ch.items()},
        final_deltas={c: v["final_delta"] for c, v in ch.items()}, keys=keys)
    body, n = re.subn(r'(?m)^name = ".*"$', f'name = "{pid}-{run_name}"', body, count=1)
    if n != 1:
        raise ValueError("the base spec has no [scenario] name line")
    return (f"# sealed-region run {pid}/{run_name} (tools/exp/contig/sealed.py): the base spec with the region's "
            f"K, declared δ, final δ and split list per channel, margin = false\n"
            f"# states: {', '.join(states)}\n" + body)


# ------------------------------------------------------------------------------ commands
def _patched(cmd: list, flag: str, value: str) -> list:
    i = cmd.index(flag)
    return cmd[:i + 1] + [value] + cmd[i + 2:]


def plan_cmd(base: str, out_spec: str, plans: str, report: str, extract: str, states, cap: float,
             nch: int, drawable_alone: bool = True) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "sealed.py"), "replan", base, "--out-spec", out_spec,
            "--plans", plans, "--report", report, "--extract", extract, "--states", ",".join(states),
            "--time-limit", f"{max(30.0, cap / (2 * nch + 2)):g}"] + (["--drawable-alone"] if drawable_alone else [])


def draw_cmd(spec: str, out: str, plans: str, extract: str, jobs: int, states, cap: float) -> list:
    cmd = overnight.draw_cmd(spec, out, plans, extract, jobs)
    return _patched(cmd, "--time-limit", f"{DRAW_FRAC * cap:g}") + ["--states", ",".join(states)]


def repair_cmd(src: str, out: str, plans: str, extract: str, jobs: int, npass: int, label: str, states,
               cap: float, window: str | None = None) -> list:
    cmd = overnight.repair_cmd(src, out, plans, extract, jobs, npass, label)
    p = overnight.REPAIR[npass]
    window_s = max(float(p[p.index("--time-limit") + 1]), float(p[p.index("--neck-time-limit") + 1]))
    return (_patched(cmd, "--budget", f"{max(60.0, cap - window_s - 30.0):g}")
            + ["--states", ",".join(states)] + (["--window", window] if window else []))


def glue_cmd(src: str, out: str, plans: str, extract: str, label: str, states) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "glue.py"), src, "--out", out, "--extract", extract,
            "--plans", plans, "--states", ",".join(states), "--label", label]


def merge_cmd(spec: str, out: str, extract_out: str, extract: str, sources: list,
              window: str | None = None) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "merge.py"), spec, *sources, "--out", out,
            "--extract-out", extract_out, "--base-extract", extract, "--rate", "1", "--gap-width",
            *(["--window", window] if window else [])]


def window_of(plan: dict) -> str | None:
    """"LO,HI" in $M for a run of one channel (`repair.py --window`, `merge.py --window` take one
    window for every channel), else None."""
    if len(plan["channels"]) != 1:
        return None
    v = next(iter(plan["channels"].values()))
    return f"{v['lo_m']:g},{v['hi_m']:g}"


def merge_window(sp) -> str | None:
    """"LO,HI" in $M for a spec with one channel (`merge.py --window` takes one window for the
    map), else None; the per-channel judge is `score.py`'s `dollars.csv`."""
    if len(sp.channels) != 1:
        return None
    lo, hi = score.WINDOWS.get(next(iter(sp.channels)), (None, None))
    return f"{lo / 1e6:g},{hi / 1e6:g}" if lo else None


def jobs_of(run: dict) -> int:
    return max(2, len(run["ks"]))


def nominal_chain(pid: str, run: dict, rdir: str, plans: str, extract: str, plan: dict, caps: dict,
                  drawable_alone: bool = True) -> list:
    """[(stage, command, cap, env)] of a run's chain as it runs when nothing fails and nothing is
    retried: replan, draw, repair pass 1, glue (pass 2 and the `k_alt` re-run depend on the
    results)."""
    st, jobs, label = run["states"], jobs_of(run), f"sealed {pid}/{run['name']}"
    nch = len(plan["channels"])
    win = window_of(plan)
    return [("replan", plan_cmd(os.path.join(rdir, "spec-base.toml"), os.path.join(rdir, "spec.toml"), plans,
                                os.path.join(rdir, "replan.json"), extract, st, caps["replan"], nch, drawable_alone),
             caps["replan"], None),
            ("draw", draw_cmd(os.path.join(rdir, "spec.toml"), os.path.join(rdir, "draw"), plans, extract, jobs, st,
                              caps["draw"]), caps["draw"], None),
            ("r1", repair_cmd(os.path.join(rdir, "draw"), os.path.join(rdir, "r1"), plans, extract, jobs, 1, label,
                              st, caps["repair"], win), caps["repair"], None),
            ("glue", glue_cmd(os.path.join(rdir, "r1"), os.path.join(rdir, "glue"), plans, extract, label, st),
             caps["glue"], GAP_ENV)]


def shape_cmd(folder: str, name: str, out_dir: str) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "sealed.py"), "shape", "--folder", folder, "--name", name,
            "--out-dir", out_dir]


def combine_cmd(args_json: str, out: str, spec: str, extract: str) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "sealed.py"), "combine", "--runs", args_json, "--out", out,
            "--spec", spec, "--extract", extract]


def point_chain(pid: str, pdir: str, finals: list, base_spec: str, extract: str, window: str | None,
                caps: dict) -> list:
    """[(stage, command, cap, env)] of a point's merge, gate, score, land and shape."""
    merged = os.path.join(pdir, "merged")
    sources = [f"{'+'.join(states)}={final}" for states, final in finals]
    return [("merge", merge_cmd(base_spec, merged, os.path.join(pdir, "merged_extract.json.gz"), extract, sources,
                                window), caps["merge"], GAP_ENV),
            ("gate", overnight.gate_cmd(merged), overnight.CAP_S["gate"], GAP_ENV),
            ("score", overnight.score_cmd(merged), overnight.CAP_S["post"], GAP_ENV),
            ("land", overnight.land_cmd(merged), overnight.CAP_S["post"], None),
            ("shape", shape_cmd(merged, pid, merged), caps["shape"], None)]


def all_states(runs: list) -> tuple:
    return tuple(sorted({st for r in runs for st in r["states"]}))


def combine_args(runs: list, folders: dict) -> dict:
    """What `sealed.py combine` reads: the normalised runs (name, states, channels' K) and their last folders."""
    return {"runs": [{"name": r["name"], "states": list(r["states"]), "ks": dict(r["ks"])} for r in runs],
            "folders": {r["name"]: folders[r["name"]] for r in runs}}


def cmd_combine(a) -> int:
    """`sealed.py combine` (a point's combine stage, a child of the driver so its cap and the `--hours`
    stop can end it): `combine_point` over the runs of `--runs`."""
    with open(a.runs, encoding="utf-8") as fh:
        doc = json.load(fh)
    got = combine_point(doc["runs"], doc["folders"], a.out, a.spec, a.extract)
    print(f"combined: {got['cells']} cells, {got['districts']} districts", flush=True)
    return 0


def _run():
    return overnight._load("contig_run", os.path.join(HERE, "run.py"))


def combine_point(runs: list, folders: dict, out: str, spec_path: str, extract_path: str) -> dict:
    """`out`: one run folder (`ledger.csv`, `districts.csv`, `manifest.json`, `run.json`: what
    `merge.py` reads of a source) holding every cell of a point whose channels were drawn by
    independent regions.  A cell (ZCTA, fine channel) comes from the run that has its planning channel
    (`model_channel`) for the ZCTA's state, else, for a cell of no run's channel, from the first run
    holding the state; a run's rows outside its states, and its other channels' rows, are left to
    their own runs.  Districts are renamed `<run>/<id>`, so no two runs' districts collide.
    `runs` the normalised runs, `folders` {run name: its last folder}.  The folder's manifest is its
    own (mandate T1, `run.write_manifest`: identity, command, `spec_path` and `extract_path` with
    their sha256, this code's commit), with every source run in `source_runs` and `combined_from`,
    so the tracker index lists it as a run of its own."""
    srcs = []
    for run in runs:
        with open(os.path.join(folders[run["name"]], "manifest.json"), encoding="utf-8") as fh:
            commit = json.load(fh)["provenance"]["commit"]
        srcs.append({"run": run["name"], "states": list(run["states"]), "folder": os.path.abspath(folders[run["name"]]),
                     "commit": commit})
    params = {"runs": {r["name"]: {"states": list(r["states"]), "channels": sorted(r["ks"])} for r in runs}}
    os.makedirs(out, exist_ok=True)
    stale = os.path.join(out, "manifest.json")
    if os.path.exists(stale):
        os.remove(stale)        # a retry is a new run: its own start time and code state
    mrun = _run()
    mrun.write_manifest(out, "sealed_combine", spec_path, extract_path, params, source_runs=srcs,
                        combined_from={r["run"]: r["folder"] for r in srcs})
    try:
        got = _combine_cells(runs, folders, out)
    except Exception as e:
        mrun.write_manifest(out, "sealed_combine", spec_path, extract_path, params, status="failed",
                            stop_reason=f"{type(e).__name__}: {e}")
        raise
    mrun.write_manifest(out, "sealed_combine", spec_path, extract_path, params, status="done",
                        stop_reason="combined", **got)
    return got


def _combine_cells(runs: list, folders: dict, out: str) -> dict:
    """The ledger, districts and run.json of `combine_point`'s folder; {cells, districts}."""
    owner, first = collections.defaultdict(dict), {}
    for run in runs:
        for st in run["states"]:
            first.setdefault(st, run["name"])
            for c in run["ks"]:
                owner[c].setdefault(st, run["name"])
    ledger, used, seen = [], collections.defaultdict(set), {}
    for run in runs:
        name, held = run["name"], set(run["states"])
        for r in output.read_ledger(os.path.join(folders[name], "ledger.csv")):
            st, c = r["state"], r["model_channel"]
            if st not in held or owner[c].get(st, first[st]) != name:
                continue
            cell = (r["zip_code"], r["current_channel"])
            if cell in seen:
                raise ValueError(f"cell {cell} is in both {seen[cell]} and {name}")
            seen[cell] = name
            if r["district"]:
                used[name].add((c, r["district"]))
                r["district"] = f"{name}/{r['district']}"
            ledger.append(r)
    os.makedirs(out, exist_ok=True)
    output.write_ledger(os.path.join(out, "ledger.csv"), ledger)
    rows, header = [], None
    for run in runs:
        name = run["name"]
        with open(os.path.join(folders[name], "districts.csv"), encoding="utf-8", newline="") as fh:
            rd = csv.DictReader(fh)
            header = header or rd.fieldnames
            for r in rd:
                if (r["channel"], r["district"]) in used[name]:
                    used[name].discard((r["channel"], r["district"]))
                    rows.append(dict(r, district=f"{name}/{r['district']}"))
        if used[name]:
            raise ValueError(f"{name}: districts {sorted(used[name])[:3]} are in the ledger but not in districts.csv")
    with open(os.path.join(out, "districts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    status, m1 = collections.defaultdict(list), []
    for run in runs:
        with open(os.path.join(folders[run["name"]], "run.json"), encoding="utf-8") as fh:
            rj = json.load(fh)
        m1.append(f"{run['name']} {rj['m1']['status']}")
        for c, v in rj["channels"].items():
            if any(owner[c].get(st) == run["name"] for st in run["states"]):
                status[c].append(f"{run['name']} {v['status']}")
    overnight._write_json(os.path.join(out, "run.json"), {
        "channels": {c: {"status": "; ".join(v)} for c, v in sorted(status.items())},
        "m1": {"status": "unverified here (the runs': " + ", ".join(m1) + ")"}})
    return {"cells": len(ledger), "districts": len(rows)}


# ------------------------------------------------------------------------------ the replan stage
def cmd_replan(a) -> int:
    """`sealed.py replan`: `replan.py` itself, its instance built on the polygon graph induced on
    `--states` (`replan.build` swapped; `replan.py` plans the full graph, which a region's K does not
    fit).  Everything else is `replan.main`'s: the master at the declared δ else the smallest feasible
    one up to the final δ, the plans cached for `run.py --plans`, `replan.json`; with
    `--drawable-alone` (#124 B) every channel plans only supports `plancheck.drawable` shows can be
    drawn alone without a neck, its tests and bans in the report's `plan_check`."""
    replan = overnight._replan()
    states = tuple(x for x in a.states.split(",") if x)

    def build(spec_path: str, extract_path: str):
        s = tdspec.load(spec_path)
        ref = geo.read_reference()
        ext = tdspec.scope(s, data.conus(data.load(extract_path), ref))
        return s, tdspec.build(s, ext, ref, graph=replan.run.induced_graph(geo.polygon_graph(), states))
    replan.build = build
    argv = [a.spec, "--out-spec", a.out_spec, "--plans", a.plans, "--extract", a.extract,
            "--time-limit", f"{a.time_limit:g}", "--check-time", f"{min(120.0, a.time_limit):g}",
            "--drawable-alone" if a.drawable_alone else "--keep"]
    if a.report:
        argv += ["--report", a.report]
    return replan.main(argv)


def plan_report(path: str) -> dict:
    """What a region's `replan.json` says per channel: the δ planned at, the supports `plancheck`
    banned (B's bans: not drawable alone), those it could not decide, and the tests run."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = {}
    for c, e in sorted(doc.get("channels", {}).items()):
        pc = e.get("plan_check") or e.get("plan_check_at_declared") or {}
        out[c] = {"delta": e.get("delta"), "status": e.get("status"),
                  "bans": [b["support"] for b in pc.get("bans", [])],
                  "unknown": [u["support"] for u in pc.get("unknown", [])], "tested": len(pc.get("tested", []))}
    return out


# ------------------------------------------------------------------------------ shape
_SHAPE = {}
_SHAPE_LOCK = threading.Lock()
SUM_COLUMNS = ("hull_fill", "bite", "aspect", "longest_axis_km", "doughnut", "doughnut_soft")
LIMIT_COLUMNS = ("n_states", "usd_m", "m_rel", "n_zips", "land_km2", "hull_km2", "hull_fill", "hull_fill_raw", "bite",
                 "longest_axis_km", "aspect", "cut_edges", "cut_counties", "land_per_usd", "wmean_dist_km",
                 "r90_km", "doughnut", "doughnut_soft", "hub_share")      # the numeric columns of study.DISTRICT_COLUMNS


def _study():
    return overnight._load("looks_study", os.path.join(ROOT, "tools", "looks", "study.py"))


def load_limits(path: str | None) -> dict:
    """{"hard": bool, "limits": {column: {"min"?: x, "max"?: y}}} from L.json (numeric columns of
    `tools/looks/study.py`'s per-district measures, `LIMIT_COLUMNS`); the default is no limits, report only."""
    if path is None:
        return {"hard": False, "limits": {}}
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    lim = doc.get("limits")
    if not isinstance(lim, dict) or not isinstance(doc.get("hard", False), bool) or set(doc) - {"hard", "limits"}:
        raise PartitionError(f"{path}: expected {{\"hard\": bool, \"limits\": {{column: {{min, max}}}}}}")
    cols = set(_study().DISTRICT_COLUMNS) & set(LIMIT_COLUMNS)
    errs = [f"{path}: {k!r} is not a numeric district measure of tools/looks/study.py ({', '.join(LIMIT_COLUMNS)})"
            for k in lim if k not in cols]
    errs += [f"{path}: {k}: a limit is {{\"min\": x}} and/or {{\"max\": y}} with numbers"
             for k, v in lim.items() if not isinstance(v, dict) or not v or set(v) - {"min", "max"}
             or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v.values())]
    if errs:
        raise PartitionError("\n".join(errs))
    return {"hard": bool(doc.get("hard", False)), "limits": lim}


def shape_breaches(rows: list, limits: dict) -> list:
    """[{channel, district, measure, value, limit}] for each district row beyond a limit."""
    out = []
    for r in rows:
        for col, lim in sorted(limits.items()):
            v = r.get(col)
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            for kind, x in sorted(lim.items()):
                if (kind == "min" and v < x) or (kind == "max" and v > x):
                    out.append({"channel": r["channel"], "district": r["district"], "measure": col,
                                "value": float(v), "limit": f"{kind} {x:g}"})
    return out


def shape_unmeasured(rows: list, limits: dict) -> list:
    """[{channel, district, measure, value}] for each district row whose value of a configured limit
    column is missing or not a finite number; `shape_breaches` skips them, which a hard limit may not."""
    return [{"channel": r.get("channel"), "district": r.get("district"), "measure": col, "value": r.get(col)}
            for r in rows for col in sorted(limits)
            if isinstance(r.get(col), bool) or not isinstance(r.get(col), (int, float)) or not math.isfinite(r[col])]


def shape_summary(rows: list) -> dict:
    """{channel: {districts, hull_fill_min, bite_max, aspect_max, longest_axis_km_max, doughnuts,
    doughnuts_soft}} of the district rows."""
    out = {}
    for ch in sorted({r["channel"] for r in rows}):
        rs = [r for r in rows if r["channel"] == ch]

        def col(name):
            return [float(r[name]) for r in rs if r.get(name) is not None and r[name] == r[name]]
        out[ch] = {"districts": len(rs), "hull_fill_min": min(col("hull_fill"), default=None),
                   "bite_max": max(col("bite"), default=None), "aspect_max": max(col("aspect"), default=None),
                   "longest_axis_km_max": max(col("longest_axis_km"), default=None),
                   "doughnuts": int(sum(col("doughnut"))), "doughnuts_soft": int(sum(col("doughnut_soft")))}
    return out


def measure_shape(folder: str, name: str) -> list:
    """`tools/looks/study.py`'s district rows of one run folder (its CLI measures a fixed list of
    maps, so its functions are called): `Ref.load` once per process."""
    study = _study()
    with _SHAPE_LOCK:
        if "ref" not in _SHAPE:
            _SHAPE["ref"] = study.Ref.load()
    rows = study.read_ledger(folder)
    drows, conflicts = study.measure_map(name, rows, _SHAPE["ref"], {f: 1.0 for f in score.DOLLARS})
    if conflicts:
        raise RuntimeError(f"{folder}: {conflicts} cells name two districts")
    return drows


def cmd_shape(a) -> int:
    """`sealed.py shape` (a point's shape stage, a child of the driver so its cap and the `--hours`
    stop can end it): every district's measures of `--folder` to `<out-dir>/shape-districts.json` and
    `.csv`."""
    rows = measure_shape(a.folder, a.name)
    plain = lambda x: x.item() if hasattr(x, "item") else str(x)
    path = os.path.join(a.out_dir, SHAPE_ROWS)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1, default=plain)
        fh.write("\n")
    os.replace(path + ".tmp", path)
    _study().write_csv(os.path.join(a.out_dir, os.path.splitext(SHAPE_ROWS)[0] + ".csv"),
                       _study().DISTRICT_COLUMNS, rows)
    print(f"{a.name}: {len(rows)} districts", flush=True)
    return 0


# ------------------------------------------------------------------------------ labels
def label_point(m1: dict, rows: list, breaches: list, hard: bool, eligible: bool = True, why=()) -> tuple:
    """(label, reason): `fails M1` on the gap-width verdict of `m1.json`, else `outside band` when a
    district of `dollars.csv` is outside its window, else `ineligible` with the scorer's reasons
    (`eligible`, `why` of `overnight.read_score`: the main K outside its range, a failed audit check),
    else `fails shape` for a breach under a hard limits file, else `passes`."""
    if m1["status"] != "pass":
        return "fails M1", f"M1 across coverage gaps: {m1['status']}, {m1['summary']}"
    bad = [r for r in rows if not r["ok"]]
    if bad:
        return "outside band", "; ".join(
            f"{r['district']} {r['usd']:,.1f}M outside "
            + ("no window" if r["lo"] is None else f"{r['lo']:,.1f}-{(r['cap'] or r['hi']):,.1f}M") for r in bad)
    if not eligible:
        return "ineligible", "; ".join(why) or "score.txt says eligible: no"
    if hard and breaches:
        return "fails shape", f"{len(breaches)} breaches of the hard shape limits, first {breaches[0]}"
    return "passes", ""


def drawing_failures(contig: dict) -> dict:
    """{channel: {reasons, groups}} for each channel of a run's `contig.json` that has no drawing to
    repair (owner, 2026-10-14: contiguity at the solver level): ZCTAs handed to the non-contiguous
    fallback (`undrawn_zctas`), or a status other than `DRAWN_OK`; `groups` are the coupled groups
    whose solve ended otherwise.  A drawing that succeeded and leaves detached pieces (`connected`
    false, `fixed_split` districts) is not a failure here: the repair and the glue take it."""
    out = {}
    for c, ch in sorted(contig.get("channels", {}).items()):
        why = []
        if ch.get("undrawn_zctas"):
            why.append(f"{ch['undrawn_zctas']} undrawn ZCTAs left to the non-contiguous fallback")
        if ch.get("status") not in DRAWN_OK:
            why.append(f"drawing status {ch.get('status')}")
        if why:
            out[c] = {"reasons": why, "groups": [
                {"districts": g.get("districts"), "units": g.get("units"), "free_zctas": g.get("free_zctas"),
                 "status": g.get("status"), "seconds": g.get("seconds"), "gap": g.get("gap")}
                for g in ch.get("groups", []) if g.get("status") not in DRAWN_OK]}
    return out


def failure_text(failures: dict) -> str:
    return "; ".join(
        f"{c}: {', '.join(f['reasons'])}" + ("; groups " + ", ".join(
            f"{'+'.join(map(str, g['districts'] or []))} [{','.join(map(str, g['units'] or []))}] {g['status']}"
            for g in f["groups"][:4]) + (f" (+{len(f['groups']) - 4} more)" if len(f["groups"]) > 4 else "")
            if f["groups"] else "") for c, f in sorted(failures.items()))


def worst_run(runs: dict) -> tuple | None:
    """(status, reason) of the worst failing run (`RUN_BAD`), or None when every run is done."""
    bad = {s: [(n, v) for n, v in sorted(runs.items()) if v.get("status") == s] for s in RUN_BAD}
    other = [(n, v) for n, v in sorted(runs.items()) if v.get("status") != "done" and v.get("status") not in RUN_BAD]
    for s in RUN_BAD:
        if bad[s]:
            return s, "; ".join(f"{n}: {v.get('reason', s)}" for n, v in bad[s])
    if other:
        return "error", "; ".join(f"{n}: never finished (status {v.get('status')})" for n, v in other)
    return None


# ------------------------------------------------------------------------------ the driver
class Driver(overnight.Runner):
    """One host's sealed points: `region` runs one run's chain, `finish` merges a point whose runs
    are all done and labels it."""

    def __init__(self, grid, root, host, extract, cells, points: dict, caps: dict, forbid, max_size, limits,
                 drawable_alone: bool = True, window_band: bool = False):
        super().__init__(grid, root, host, extract, cells, window_band)
        self.points, self.caps, self.forbid, self.max_size, self.limits = points, caps, forbid, max_size, limits
        self.drawable_alone = drawable_alone
        self.state_of = None            # {ZCTA: state}, read when a run needs a cut extract
        self.lock = threading.Lock()
        self.pending = collections.Counter()
        self.specs = {}

    # -- bookkeeping
    def spec_of(self, pt: dict):
        with self.lock:
            if pt["base"] not in self.specs:
                with open(pt["base"], encoding="utf-8") as fh:
                    self.specs[pt["base"]] = (tdspec.load(pt["base"]), fh.read())
            return self.specs[pt["base"]]

    def note(self, pid: str, run: str, **fields) -> None:
        with self.lock:
            runs = self.grid.get(pid)["runs"]
            runs.setdefault(run, {}).update(fields)
            self.grid.update(pid, runs=runs)

    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.root)

    def run_extract(self, sp, run: dict, plan: dict, rdir: str) -> str:
        """The extract a run's stages read: the driver's own, or, when channels outside the run have
        cells in its states, `<run>/extract.json.gz` less their fine channels (made once)."""
        if not plan["outside"]:
            return self.extract
        path = os.path.join(rdir, "extract.json.gz")
        if not os.path.exists(path):
            if self.state_of is None:
                self.state_of = zip_states()
            cut_extract(self.extract, path, run_cells(sp, [c for c in run["ks"] if c in sp.channels]),
                        self.state_of)
        return path

    # -- one run
    def region(self, task: dict) -> list:
        pt, run = self.points[task["point"]], task["run"]
        pid, rn = pt["id"], run["name"]
        rdir = os.path.join(self.root, pid, rn)
        os.makedirs(rdir, exist_ok=True)
        if self.grid.get(pid)["started_at"] is None:
            self.grid.update(pid, status="running", started_at=overnight.now())
        self.note(pid, rn, status="running", states=list(run["states"]), ks=run["ks"])
        try:
            self._chain(pt, run, rdir)
        except Stop as e:
            self.note(pid, rn, status=e.label, reason=e.reason)
        except Exception as e:      # a launcher fault: the run is labelled, the rest goes on
            self.note(pid, rn, status="error", reason=f"{type(e).__name__}: {e}")
            with open(os.path.join(rdir, "launcher_error.txt"), "w") as fh:
                fh.write(traceback.format_exc())
        with self.lock:
            self.pending[pid] -= 1
            last = self.pending[pid] == 0
        if last:
            self.finish(pt)
        return []

    def _attempt(self, pt: dict, run: dict, adir: str, ks: dict, tag: str) -> dict:
        """Spec copy, replan and draw of one K choice in `adir`; the drawn folder, its contig.json and
        `failures`, `drawing_failures` of it: a channel whose drawing is not a connected one."""
        pid, rn = pt["id"], run["name"]
        sp, text = self.spec_of(pt)
        os.makedirs(adir, exist_ok=True)
        plan = region_plan(sp, run["states"], ks, self.cells, pt["rule"], self.window_band)
        if plan["infeasible"]:
            raise Stop("infeasible", "; ".join(plan["infeasible"].values()))
        extract = self.run_extract(sp, run, plan, os.path.join(self.root, pid, rn))
        base, spec, out = (os.path.join(adir, x) for x in ("spec-base.toml", "spec.toml", "draw"))
        with open(base, "w", encoding="utf-8") as fh:
            fh.write(run_spec_text(text, pid, rn, run["states"], plan, self.forbid | set(map(tuple, run["forbid"])),
                                   self.max_size))
        chain = dict((s, (cmd, cap, env)) for s, cmd, cap, env in
                     nominal_chain(pid, run, adir, self.plans, extract, plan, self.caps, self.drawable_alone))
        if not (os.path.exists(spec) and finished(out)):
            cmd, cap, _ = chain["replan"]
            log = os.path.join(adir, "replan.log")
            info = self.stage(pid, f"{rn}{tag}.replan", cmd, log, cap)
            if info["stop"] == "cap":
                raise Stop("stopped", f"replan killed at its cap ({cap / 60:g} min)")
            if info["rc"] == 1 and "no plan" in overnight._text(log):
                raise Stop("infeasible", overnight._tail(log))
            if info["rc"] != 0:
                raise Stop("error", f"replan exited {info['rc']}: {overnight._tail(log)}")
        if os.path.exists(os.path.join(adir, "replan.json")):
            self.note(pid, rn, **{f"plan{tag.replace('.', '_')}": plan_report(os.path.join(adir, "replan.json"))})
        if not finished(out):
            overnight.set_aside(out)
            cmd, cap, _ = chain["draw"]
            info = self.stage(pid, f"{rn}{tag}.draw", cmd, os.path.join(adir, "draw.log"), cap)
            if info["stop"] == "cap":
                raise Stop("stopped", f"draw killed at its cap ({cap / 60:g} min)")
        if not os.path.exists(os.path.join(out, "ledger.csv")):
            raise Stop("error", f"run.py wrote no ledger: {overnight._tail(os.path.join(adir, 'draw.log'))}")
        with open(os.path.join(out, "contig.json"), encoding="utf-8") as fh:
            contig = json.load(fh)
        failures = drawing_failures(contig)
        return {"dir": adir, "draw": out, "contig": contig, "failures": failures, "failing": sorted(failures),
                "ks": ks, "plan": plan, "extract": extract}

    def _chain(self, pt: dict, run: dict, rdir: str) -> None:
        pid, rn = pt["id"], run["name"]
        first = self._attempt(pt, run, rdir, dict(run["ks"]), "")
        got, retry = first, None
        alt = {c: run["k_alt"][c] for c in first["failing"] if c in run["k_alt"]}
        if alt:
            ks2 = {**run["ks"], **alt}
            sp, _ = self.spec_of(pt)
            bad = region_plan(sp, run["states"], ks2, self.cells, pt["rule"], self.window_band)["infeasible"]
            retry = {"k_alt": alt, "failing": first["failing"]}
            if bad:
                retry["result"] = "k_alt has no final δ in the window: " + "; ".join(bad.values())
            else:
                try:
                    second = self._attempt(pt, run, os.path.join(rdir, "alt"), ks2, ".alt")
                except Stop as e:
                    if e.label == "stopped":
                        raise
                    retry["result"] = f"the re-run at k_alt ended {e.label}: {e.reason}"
                else:
                    retry["result"] = f"{len(second['failing'])} channels failing at k_alt, {len(first['failing'])} at k"
                    if len(second["failing"]) < len(first["failing"]):
                        got = second
        self.note(pid, rn, ks_used=got["ks"], retry=retry,
                  draw={c: ch.get("status") for c, ch in sorted(got["contig"]["channels"].items())},
                  draw_failing=got["failing"], draw_failures=got["failures"])
        if got["failures"]:     # never a deliverable: not repaired, not merged (owner, 2026-10-14)
            raise Stop(NO_DRAWING, failure_text(got["failures"]))
        adir, src, extract = got["dir"], got["draw"], got.get("extract") or self.extract
        plan, jobs, label = got["plan"], jobs_of(run), f"sealed {pid}/{rn}"
        win = window_of(plan)
        for npass in (1, 2):
            if npass == 2 and clean(src):
                break
            out = os.path.join(adir, f"r{npass}")
            if not repair_done(out):
                overnight.set_aside(out)
                cap = self.caps["repair"]
                info = self.stage(pid, f"{rn}.r{npass}",
                                  repair_cmd(src, out, self.plans, extract, jobs, npass, label, run["states"], cap,
                                             win), os.path.join(adir, f"r{npass}.log"), cap)
                if info["stop"] == "cap":
                    self.note(pid, rn, **{f"r{npass}": f"killed at its cap ({cap / 60:g} min)"})
            if repair_done(out):        # an interrupted pass leaves the last completed source in place
                src = out
        gout = os.path.join(adir, "glue")
        if not glue_done(gout):
            overnight.set_aside(gout)
            cap = self.caps["glue"]
            info = self.stage(pid, f"{rn}.glue", glue_cmd(src, gout, self.plans, extract, label, run["states"]),
                              os.path.join(adir, "glue.log"), cap, GAP_ENV)
            if info["stop"] == "cap":
                self.note(pid, rn, glue=f"killed at its cap ({cap / 60:g} min)")
            elif info["rc"] != 0:
                raise Stop("error", f"glue.py exited {info['rc']}: {overnight._tail(os.path.join(adir, 'glue.log'))}")
        if glue_done(gout):
            with open(os.path.join(gout, "glue.json"), encoding="utf-8") as fh:
                g = json.load(fh)["channels"]
            self.note(pid, rn, glue={c: {"glued": len(v["glued"]), "left": v["left"], "moved": len(v["moved"])}
                                     for c, v in sorted(g.items())})
            if os.path.exists(os.path.join(gout, "ledger.csv")):
                src = gout
        self.note(pid, rn, status="done", final=self.rel(src))

    # -- a point
    def finish(self, pt: dict) -> None:
        pid = pt["id"]
        try:
            label, reason, final, extra = self._merge(pt)
        except Stop as e:
            label, reason, final, extra = e.label, e.reason, None, {}
        except Exception as e:
            label, reason, final, extra = "error", f"{type(e).__name__}: {e}", None, {}
            os.makedirs(os.path.join(self.root, pid), exist_ok=True)
            with open(os.path.join(self.root, pid, "launcher_error.txt"), "w") as fh:
                fh.write(traceback.format_exc())
        if final is not None:
            with open(os.path.join(final, "scorecard.md"), "a", encoding="utf-8") as fh:
                fh.write(f"\n**Sealed-region driver label ({pid}):** {label}" + (f" ({reason})" if reason else "") + "\n")
        self.grid.update(pid, status="done", label=label, reason=reason, finished_at=overnight.now(),
                         final=final and self.rel(final), **extra)

    def _merge(self, pt: dict) -> tuple:
        pid = pt["id"]
        pdir = os.path.join(self.root, pid)
        rec = self.grid.get(pid)
        worst = worst_run(rec["runs"])
        if worst:
            return worst[0], worst[1], None, {}
        folders = {run["name"]: os.path.join(self.root, rec["runs"][run["name"]]["final"]) for run in pt["runs"]}
        combined = os.path.join(pdir, "combined")
        finals = ([(run["states"], folders[run["name"]]) for run in pt["runs"]] if pt["aligned"]
                  else [(all_states(pt["runs"]), combined)])
        sp, text = self.spec_of(pt)
        mspec = os.path.join(pdir, "spec-merge.toml")
        with open(mspec, "w", encoding="utf-8") as fh:
            fh.write(re.sub(r'(?m)^name = ".*"$', f'name = "{pid}"', text, count=1))
        window = merge_window(sp)
        chain = dict((s, (cmd, cap, env)) for s, cmd, cap, env in
                     point_chain(pid, pdir, finals, mspec, self.extract, window, self.caps))
        merged = os.path.join(pdir, "merged")
        if not finished(merged):
            overnight.set_aside(merged)
            if not pt["aligned"]:       # independent regions per channel: one source holding each cell once
                cargs, log = os.path.join(pdir, "combine-args.json"), os.path.join(pdir, "combine.log")
                overnight._write_json(cargs, combine_args(pt["runs"], folders))
                cap = self.caps["combine"]
                info = self.stage(pid, "combine", combine_cmd(cargs, combined, mspec, self.extract), log, cap)
                if info["stop"] == "cap":
                    raise Stop("stopped", f"combine killed at its cap ({cap / 60:g} min)")
                if info["rc"] != 0:
                    raise Stop("error", f"combine exited {info['rc']}: {overnight._tail(log)}")
            cmd, cap, env = chain["merge"]
            info = self.stage(pid, "merge", cmd, os.path.join(pdir, "merge.log"), cap, env)
            if info["stop"] == "cap":
                raise Stop("stopped", f"merge killed at its cap ({cap / 60:g} min)")
            if not finished(merged):
                raise Stop("error", f"merge.py exited {info['rc']}: {overnight._tail(os.path.join(pdir, 'merge.log'))}")
        for name in ("gate", "score", "land"):
            cmd, cap, env = chain[name]
            log = {"gate": os.path.join(pdir, "gate.log"), "score": os.path.join(merged, "score.txt"),
                   "land": os.path.join(pdir, "land.log")}[name]
            info = self.stage(pid, name, cmd, log, cap, env)
            if info["stop"] == "cap":
                raise Stop("stopped", f"{name} killed at its cap ({cap / 60:g} min)")
        for f in ("m1.json", "dollars.csv", "score.txt"):
            if not os.path.exists(os.path.join(merged, f)):
                raise Stop("error", f"score.py wrote no {f}: {overnight._tail(os.path.join(merged, 'score.txt'))}")
        with open(os.path.join(merged, "m1.json"), encoding="utf-8") as fh:
            m1 = json.load(fh)
        rows = overnight.read_dollars(os.path.join(merged, "dollars.csv"))
        try:
            eligible, why = overnight.read_score(os.path.join(merged, "score.txt"))
        except ValueError as e:
            raise Stop("error", f"score.py: {e}")
        shape = {"error": None, "summary": {}, "breaches": [], "limits": self.limits, "districts": None}
        cmd, cap, env = chain["shape"]
        log = os.path.join(pdir, "shape.log")
        info = self.stage(pid, "shape", cmd, log, cap, env)      # a Stop at the --hours stop, a kill at its cap
        if info["stop"] == "cap":
            shape["error"] = f"shape killed at its cap ({cap / 60:g} min)"
        elif info["rc"] != 0:
            shape["error"] = f"shape exited {info['rc']}: {overnight._tail(log)}"
        else:
            try:
                with open(os.path.join(merged, SHAPE_ROWS), encoding="utf-8") as fh:
                    drows = json.load(fh)
                shape["summary"] = shape_summary(drows)
                shape["breaches"] = shape_breaches(drows, self.limits["limits"])
                gaps = shape_unmeasured(drows, self.limits["limits"]) if self.limits["hard"] else []
                if gaps:      # a hard limit on a value that was not measured is not a pass
                    shape["error"] = f"{len(gaps)} missing or non-finite values under hard shape limits, first {gaps[0]}"
                shape["districts"] = SHAPE_ROWS
            except (OSError, ValueError, KeyError) as e:
                shape["error"] = f"{type(e).__name__}: {e}"
        if shape["error"] and self.limits["hard"]:     # reported, loudly; it decides the label only under hard limits
            raise Stop("stopped" if info["stop"] == "cap" else "error",
                       f"shape measures failed under hard limits: {shape['error']}")
        overnight._write_json(os.path.join(merged, "shape.json"), shape)
        label, reason = label_point(m1["gap_width"], rows, shape["breaches"], self.limits["hard"], eligible, why)
        looks = overnight.read_looks(os.path.join(merged, "score.txt"))
        bands = {}
        for c in sorted({r["channel"] for r in rows}):
            us = [r["usd"] for r in rows if r["channel"] == c and r["usd"] is not None]
            bands[c] = {"districts": len(us), "out": sum(1 for r in rows if r["channel"] == c and not r["ok"]),
                        "min_m": min(us, default=None), "max_m": max(us, default=None),
                        "avg_m": math.fsum(us) / len(us) if us else None}
        summary = {"m1_gap_width": m1["gap_width"]["status"], "m1_strict": m1["strict"]["status"],
                   "bands": bands, "splits": looks and looks["splits"], "shape": shape["summary"],
                   "shape_error": shape["error"], "shape_breaches": len(shape["breaches"]),
                   "shape_hard": self.limits["hard"]}
        return label, reason, merged, {"summary": summary}


def finished(folder: str) -> bool:
    return overnight.finished(folder)


def repair_done(folder: str) -> bool:
    """True when a repair pass folder is a completed one the next stage can read: `finished` (manifest
    done, ledger written) with its `contig.json` and `run.json`."""
    return finished(folder) and all(os.path.exists(os.path.join(folder, f)) for f in ("contig.json", "run.json"))


def glue_done(folder: str) -> bool:
    """True when a `glue/` folder is one a resumed run keeps: its manifest says done and `glue.json`
    reads; if it moved a ZCTA, the folder `glue.py` writes then (ledger, `contig.json`, `run.json`) is
    all there, else (a done run with nothing to glue) only `glue.json` is."""
    try:
        with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as fh:
            if json.load(fh).get("status") != "done":
                return False
        with open(os.path.join(folder, "glue.json"), encoding="utf-8") as fh:
            moved = sum(len(v["moved"]) for v in json.load(fh)["channels"].values())
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return not moved or (finished(folder) and all(os.path.exists(os.path.join(folder, f))
                                                  for f in ("contig.json", "run.json")))


def clean(folder: str) -> bool:
    """True when every channel of a repaired folder's contig.json is connected with no neck left."""
    try:
        with open(os.path.join(folder, "contig.json"), encoding="utf-8") as fh:
            ch = json.load(fh)["channels"]
    except (OSError, ValueError, KeyError):
        return False
    return all(v.get("connected") and not v.get("necks_left") for v in ch.values())


# ------------------------------------------------------------------------------ the index
def k_of(rec: dict, c: str) -> str:
    """"4 + 10 = 14": a channel's K per run, summed over the runs that hold it (the K each run used)."""
    ks = [(n, (v.get("ks_used") or v.get("ks") or {}).get(c)) for n, v in sorted(rec.get("runs", {}).items())]
    ks = [(n, k) for n, k in ks if k]
    return " + ".join(str(k) for _, k in ks) + (f" = {sum(k for _, k in ks)}" if len(ks) > 1 else "")


def index_rows(doc: dict) -> list:
    """One row per (point, channel) of SEALED.json: regions with their states and K, the M1 verdict,
    the band (districts out of window / districts), splits, shape and the point's label."""
    out = []
    for pid, rec in sorted(doc["points"].items()):
        summ = rec.get("summary") or {}
        chans = sorted({c for v in rec.get("runs", {}).values() for c in (v.get("ks_used") or v.get("ks") or {})})
        for c in chans or [""]:
            regs = [f"{n} ({','.join(v.get('states', []))}) K{(v.get('ks_used') or v.get('ks') or {}).get(c)}"
                    for n, v in sorted(rec.get("runs", {}).items())
                    if c in (v.get("ks_used") or v.get("ks") or {})]
            b = (summ.get("bands") or {}).get(c)
            sh = (summ.get("shape") or {}).get(c)
            out.append({"id": pid, "structure": rec.get("structure"), "channel": c, "regions": "; ".join(regs),
                        "k": k_of(rec, c),
                        "m1": "—" if not summ else f"{summ['m1_gap_width']} / {summ['m1_strict']} (strict)",
                        "band": "—" if not b else f"{b['out']} of {b['districts']} out"
                        + (f", {b['min_m']:,.0f}-{b['max_m']:,.0f}M" if b["min_m"] is not None else ""),
                        "splits": "—" if summ.get("splits") is None else str(summ["splits"]),
                        "shape": _shape_text(sh, summ), "label": rec.get("label") or rec.get("status") or "queued",
                        "reason": rec.get("reason") or ""})
    return out


def _shape_text(sh: dict | None, summ: dict) -> str:
    if summ.get("shape_error"):
        return f"ERROR {summ['shape_error']}"
    if not sh:
        return "—"
    f = lambda x, fmt: "—" if x is None else format(x, fmt)
    text = (f"hull fill min {f(sh['hull_fill_min'], '.2f')}, bite max {f(sh['bite_max'], '.2f')}, aspect max "
            f"{f(sh['aspect_max'], '.1f')}, axis max {f(sh['longest_axis_km_max'], ',.0f')} km, doughnuts {sh['doughnuts']}")
    if summ.get("shape_breaches"):
        text += f"; {summ['shape_breaches']} breaches" + (" (hard)" if summ.get("shape_hard") else " (report only)")
    return text


def index_md(doc: dict, at: str) -> str:
    rows = index_rows(doc)
    counts = collections.Counter((r.get("label") or r.get("status") or "queued") for r in doc["points"].values())
    md = [f"# SEALED: {os.path.basename(doc.get('root', '')) or NAME}", "",
          f"Built by `tools/exp/contig/sealed.py index` from `SEALED.json` at {at}.  Extract "
          f"`{os.path.basename(doc.get('extract', ''))}`; partition `{doc.get('partition', {}).get('path', '')}` "
          f"(sha256 `{str(doc.get('partition', {}).get('sha256', ''))[:12]}`).", "",
          f"{len(doc['points'])} points: " + (", ".join(f"{n} {x}" for x, n in sorted(counts.items())) or "none") + ".", "",
          "M1: across coverage gaps (the gate) / strict.  Band: districts outside their channel's dollar window.  "
          "Shape: `tools/looks/study.py`'s measures over the merged map, reported against the limits file when "
          "given.", "",
          "| point | structure | channel | regions (states, K) | K | M1 | band | splits | shape | label |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['id']} | {r['structure']} | {r['channel']} | {r['regions']} | {r['k']} | {r['m1']} | {r['band']} | "
           f"{r['splits']} | {r['shape']} | **{r['label']}** |" for r in rows]
    md += ["", "## Reasons", ""] + ([f"- **{pid}** ({rec.get('label')}): {rec['reason']}"
                                     for pid, rec in sorted(doc["points"].items()) if rec.get("reason")] or ["- none"])
    md += ["", "## Runs", ""]
    for pid, rec in sorted(doc["points"].items()):
        for n, v in sorted(rec.get("runs", {}).items()):
            glue = v.get("glue")
            left = sum(len(g["left"]) for g in glue.values()) if isinstance(glue, dict) else 0
            md.append(f"- {pid}/{n} ({','.join(v.get('states', []))}): {v.get('status')}"
                      + (f", {v['reason']}" if v.get("reason") else "")
                      + (f"; draw {v['draw']}" if v.get("draw") else "")
                      + (f"; retry: {v['retry']['result']}" if v.get("retry") and v["retry"].get("result") else "")
                      + (f"; glue left {left} pieces for the owner" if left else ""))
    return "\n".join(md) + "\n"


def cmd_index(a) -> int:
    path = os.path.join(a.root, STATE_JSON)
    if not os.path.exists(path):
        raise SystemExit(f"no {path}: `run` writes it")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["root"] = a.root
    out = os.path.join(a.root, INDEX_MD)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(index_md(doc, overnight.now()))
    print(out, flush=True)
    return 0


# ------------------------------------------------------------------------------ run
def tasks_of(points: list) -> list:
    """The scheduler's tasks: one per run of the points, the largest state sets first."""
    t = [{"id": f"{p['id']}/{r['name']}", "point": p["id"], "run": r, "need": jobs_of(r)}
         for p in points for r in p["runs"]]
    return sorted(t, key=lambda x: (-len(x["run"]["states"]), x["id"]))


def cmd_dry_run(a, points: list, cells: dict, caps: dict, forbid: set) -> int:
    """Print every run's plan, spec copy and commands, and each point's merge chain; nothing is
    written or solved."""
    q = shlex.quote
    plans = os.path.join(a.root, "_plans")
    wb = getattr(a, "window_band", False)
    for pt in points:
        sp = tdspec.load(pt["base"])
        with open(pt["base"], encoding="utf-8") as fh:
            text = fh.read()
        print(f"\n######## point {pt['id']} ({pt['structure']}, rule {pt['rule']}): {len(pt['runs'])} runs")
        finals = []
        for run in pt["runs"]:
            rdir = os.path.join(a.root, pt["id"], run["name"])
            plan = region_plan(sp, run["states"], run["ks"], cells, pt["rule"], wb)
            print(f"\n==== run {run['name']} ({','.join(run['states'])}), K {run['ks']}, slots {jobs_of(run)}")
            for c, v in sorted(plan["channels"].items()):
                print(f"  {c}: K {v['k']}, ${v['usd_m']:,.1f}M, τ {v['tau_m']:,.1f}M, final δ {v['final_delta']}, "
                      f"split list {','.join(v['free']) or 'none'}"
                      + (f", window band [{v['band_lo']:.6g}, {v['band_hi']:.6g}] τ" if "band_lo" in v else ""))
            if plan["absent"]:
                print(f"  no cell in the run (dropped by the spec build): {', '.join(plan['absent'])}")
            if plan["outside"]:
                print(f"  channels of other regions with cells here ({', '.join(plan['outside'])}): the stages read "
                      f"{os.path.join(rdir, 'extract.json.gz')}, the extract less their fine channels")
            for c, why in plan["infeasible"].items():
                print(f"  INFEASIBLE {why}")
            for c, k in sorted(run["k_alt"].items()):
                alt = region_plan(sp, run["states"], {**run["ks"], c: k}, cells, pt["rule"], wb)
                print(f"  k_alt {c} {k}: " + (alt["infeasible"].get(c) or f"final δ {alt['channels'][c]['final_delta']}"))
            if plan["infeasible"]:
                continue
            print(f"--- spec copy {os.path.join(rdir, 'spec-base.toml')}")
            print(run_spec_text(text, pt["id"], run["name"], run["states"], plan, forbid | set(map(tuple, run["forbid"])),
                                a.max_size), end="")
            print("---")
            rx = os.path.join(rdir, "extract.json.gz") if plan["outside"] else a.extract
            for stage, cmd, cap, env in nominal_chain(pt["id"], run, rdir, plans, rx, plan, caps, a.drawable_alone):
                print(f"[{stage}, cap {cap:g} s{', env ' + str(env) if env else ''}] " + " ".join(map(q, cmd)))
            finals.append((run["states"], os.path.join(rdir, "glue")))
        if len(finals) == len(pt["runs"]):
            pdir = os.path.join(a.root, pt["id"])
            win = merge_window(sp)
            if not pt["aligned"]:
                print(f"\n==== point {pt['id']}: the regions are independent per channel; {os.path.join(pdir, 'combined')} "
                      f"gets each cell from the run owning its channel, and is merge.py's one source")
                cargs = os.path.join(pdir, "combine-args.json")
                print(f"[combine, cap {caps['combine']:g} s] "
                      + " ".join(map(q, combine_cmd(cargs, os.path.join(pdir, "combined"),
                                                    os.path.join(pdir, "spec-merge.toml"), a.extract))))
                finals = [(all_states(pt["runs"]), os.path.join(pdir, "combined"))]
            print(f"\n==== point {pt['id']}: merge, gate, score, land, shape")
            for stage, cmd, cap, env in point_chain(pt["id"], pdir, finals, os.path.join(pdir, "spec-merge.toml"),
                                                    a.extract, win, caps):
                print(f"[{stage}, cap {cap:g} s{', env ' + str(env) if env else ''}] " + " ".join(map(q, cmd)))
    return 0


def parse_caps(items: list) -> dict:
    caps = dict(CAPS)
    for x in items or []:
        k, sep, v = x.partition("=")
        if not sep or k not in CAPS:
            raise SystemExit(f"--cap STAGE=SECONDS with STAGE one of {', '.join(CAPS)}, not {x!r}")
        caps[k] = float(v)
    return caps


def open_state(root: str, host: str, extract: str, hours: float, part_path: str, part_sha: str, points: list) -> Grid:
    path = os.path.join(root, STATE_JSON)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("host") != host:
            raise SystemExit(f"{path} is {doc.get('host')}'s, not {host}'s")
        if doc["partition"]["sha256"] != part_sha:
            raise SystemExit(f"{path} was written for another partition file ({doc['partition']['sha256'][:12]}, "
                             f"this one {part_sha[:12]}); use a new --root")
        saved, now_sha = doc.get("extract_sha256"), overnight._dollarize().sha256(extract)
        if saved != now_sha:
            raise SystemExit(f"{path} was written for another extract ({(saved or 'no hash')[:12]}, {extract} is "
                             f"{now_sha[:12]}); use a new --root")
        grid = Grid(path, doc)
    else:
        doc = {"grid": NAME, "host": host, "created_at": overnight.now(),
               "deadline": datetime.datetime.fromtimestamp(time.time() + 3600.0 * hours,
                                                           datetime.timezone.utc).isoformat(timespec="seconds"),
               "extract": extract, "extract_sha256": overnight._dollarize().sha256(extract),
               "partition": {"path": part_path, "sha256": part_sha},
               "code": overnight._sweep().code_state(), "limits": {"hours": hours, "caps_s": CAPS}, "points": {}}
        grid = Grid(path, doc)
    for p in points:
        if p["id"] not in grid.doc["points"]:
            grid.add({"id": p["id"], "structure": p["structure"], "host": host, "status": "queued", "label": None,
                      "reason": None, "runs": {}, "stages": {}, "final": None, "summary": None,
                      "started_at": None, "finished_at": None,
                      "regions": {r["name"]: {"states": list(r["states"]), "ks": r["ks"]} for r in p["runs"]}})
    return grid


def cmd_run(a) -> int:
    if overnight._dollarize().rates_of(a.extract) is None:
        raise SystemExit(f"{a.extract} is not a dollar extract (tools/exp/contig/dollarize.py)")
    a.root, a.partition = os.path.abspath(a.root), os.path.abspath(a.partition)     # the stages run from the repo root
    a.extract = os.path.abspath(a.extract)
    caps = parse_caps(a.cap)
    forbid = {parse_pair(x) for x in a.forbid or []}
    limits = load_limits(a.shape_limits)
    with open(a.partition, "rb") as fh:
        part_sha = hashlib.sha256(fh.read()).hexdigest()
    points = load_partition(a.partition)
    if a.only:
        unknown = sorted(set(a.only) - {p["id"] for p in points})
        if unknown:
            raise SystemExit(f"--only: no point {', '.join(unknown)} in {a.partition}")
        points = [p for p in points if p["id"] in a.only]
    cells = overnight.state_cells(a.extract)
    if a.dry_run:
        return cmd_dry_run(a, points, cells, caps, forbid)
    os.makedirs(a.root, exist_ok=True)
    grid = open_state(a.root, a.host, a.extract, a.hours, os.path.abspath(a.partition), part_sha, points)
    todo = [p for p in points if grid.get(p["id"])["label"] is None]
    drv = Driver(grid, a.root, a.host, a.extract, cells, {p["id"]: p for p in todo}, caps, forbid, a.max_size, limits,
                 a.drawable_alone, a.window_band)
    tasks = tasks_of(todo)
    for p in todo:
        drv.pending[p["id"]] = len(p["runs"])
    print(f"{NAME} on {a.host}: {len(todo)} points, {len(tasks)} runs, {a.slots} slots, stop at "
          f"{grid.doc['deadline']}", flush=True)
    try:
        left = schedule(tasks, a.slots, grid.deadline(), drv.region, need=lambda t: t["need"])
    except BaseException:
        overnight.stop_all()
        raise
    for t in left:
        drv.note(t["point"], t["run"]["name"], status="stopped",
                 reason=f"not started before the {grid.doc['limits']['hours']:g} h stop")
        with drv.lock:
            drv.pending[t["point"]] -= 1
            last = drv.pending[t["point"]] == 0
        if last:
            drv.finish(drv.points[t["point"]])
    mine = [grid.get(p["id"]) for p in todo]
    counts = collections.Counter(p["label"] for p in mine)
    print(f"{NAME} {a.host}: " + ", ".join(f"{counts[x]} {x}" for x in LABELS if counts[x]), flush=True)
    doc = grid.doc
    doc["root"] = a.root
    with open(os.path.join(a.root, INDEX_MD), "w", encoding="utf-8") as fh:
        fh.write(index_md(doc, overnight.now()))
    return 0 if all(p["label"] in LABELS for p in mine) else 1


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="tools/exp/contig/sealed.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="plan, draw, repair, glue and merge the partition's points")
    r.add_argument("--partition", required=True)
    r.add_argument("--root", required=True)
    r.add_argument("--host", required=True, choices=sorted(overnight.SLOTS))
    r.add_argument("--slots", type=int, default=None, help="processes at once (default SLOTS[host])")
    r.add_argument("--hours", type=float, default=overnight.HOURS, help="the hard stop, from the first launch")
    r.add_argument("--only", nargs="*", default=None, help="these point ids only")
    r.add_argument("--extract", default=overnight.EXTRACT)
    r.add_argument("--max-size", type=int, default=None, help="max_size written into every present channel")
    r.add_argument("--forbid", nargs="*", default=None, metavar="A-B",
                   help="state pairs no district may hold together (in a run holding both)")
    r.add_argument("--shape-limits", default=None, help="L.json; report only unless it says \"hard\": true")
    r.add_argument("--cap", action="append", default=None, metavar="STAGE=S",
                   help=f"a stage's wall cap in seconds ({', '.join(f'{k} {v:g}' for k, v in CAPS.items())})")
    r.add_argument("--no-drawable-alone", dest="drawable_alone", action="store_false",
                   help="plan without replan.py's --drawable-alone (default: on, the owner's contiguity at the solver, 2026-10-14)")
    r.add_argument("--window-band", dest="window_band", action=argparse.BooleanOptionalAction, default=True,
                   help="each channel's band is its dollar window [L, U] (band_lo, band_hi), not ±δ "
                        "(default: on; owner, #112 comment, 2026-10-14); --no-window-band is the ±δ band")
    r.add_argument("--dry-run", action="store_true", help="print the spec copies and commands; solve nothing")
    r.set_defaults(func=cmd_run)
    for name in ("index", "collect"):
        i = sub.add_parser(name, help="write <root>/SEALED.md from SEALED.json")
        i.add_argument("--root", required=True)
        i.set_defaults(func=cmd_index)
    cb = sub.add_parser("combine", help="(a point's combine stage) one folder holding each cell of independent regions once")
    cb.add_argument("--runs", required=True, help="the JSON the driver wrote: {runs, folders}")
    cb.add_argument("--out", required=True)
    cb.add_argument("--spec", required=True)
    cb.add_argument("--extract", required=True)
    cb.set_defaults(func=cmd_combine)
    sh = sub.add_parser("shape", help="(a point's shape stage) every district's study measures of a folder")
    sh.add_argument("--folder", required=True)
    sh.add_argument("--name", required=True)
    sh.add_argument("--out-dir", required=True)
    sh.set_defaults(func=cmd_shape)
    p = sub.add_parser("replan", help="(a run's replan stage) replan.py on the polygon graph induced on --states")
    p.add_argument("spec")
    p.add_argument("--out-spec", required=True)
    p.add_argument("--plans", required=True)
    p.add_argument("--report", default=None)
    p.add_argument("--extract", required=True)
    p.add_argument("--states", required=True)
    p.add_argument("--time-limit", type=float, default=150.0, help="seconds per master solve")
    p.add_argument("--drawable-alone", action="store_true",
                   help="replan.py --drawable-alone: only supports that draw alone without a neck")
    p.set_defaults(func=cmd_replan)
    return ap


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    if a.cmd == "run" and a.slots is None:
        a.slots = overnight.SLOTS[a.host]
    try:
        return a.func(a)
    except PartitionError as e:
        raise SystemExit(f"{e}")


if __name__ == "__main__":
    sys.exit(main())
