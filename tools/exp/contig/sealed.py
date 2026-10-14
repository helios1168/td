"""sealed.py -- the sealed-region driver (2026-10-14): a map drawn region by region and merged,
each district inside one region (owner, 2026-10-13: regional sealing for the main map).

    "$TD_PY" -u tools/exp/contig/sealed.py run --partition P.json --root DIR --host m5|m2
        [--slots N] [--hours H] [--only ID ...] [--extract PATH] [--max-size N] [--forbid A-B ...]
        [--shape-limits L.json] [--dry-run]
    "$TD_PY" tools/exp/contig/sealed.py index --root DIR      (`collect` is the same command)

**The partition** (`P.json`): `{"points": [{"id", "structure", "channels": {<channel>: {"regions":
[{"name", "states": [...], "k", "k_alt"?, "forbid"?: ["DE-VA"]}], "rest": bool, "k_total"?}}]}}`.
`structure` is one of `overnight.STRUCTURES` (its base spec and split rule).  Every channel of the
structure is listed.  A region's `states` are disjoint from the channel's other regions' and hold
at least one of its footprint states; `rest: true` adds the region of the channel's footprint states
in no region, with `k_total` (the channel's K over the whole map, default the K of the
`overnight.POINTS` entry of the same id) less the regions' K; `rest: false` needs every footprint
state in a region.  `merge.py` takes one partition per point, so the state sets of the point's
regions, over all channels, are equal or disjoint, and a channel with footprint states in a state
set lists a region of exactly that set: channels sharing a state set are drawn together in one run.
`validate_partition` refuses anything else, naming it.

**A run** (one state set of a point; the unit of work and of the scheduler) is, in
`<root>/<point>/<run>/`, each stage a child process killed at its wall cap (`CAPS`, `--cap`), logging
to `<stage>.log` (trap 15; a hung HiGHS, as NY+NJ at K 7 on 2026-10-13, is killed, not waited for):

1. the spec copy `spec-base.toml`: the structure's base spec with each present channel's k the
   region's, `margin = false`, the final δ `overnight.fit_delta` gives the region's τ (region $ over
   k, from the dollar extract as `overnight.plan_point` computes it) in the channel's dollar window
   (`score.WINDOWS`), the declared δ `overnight.DECLARED_DELTA` or the final δ when smaller, the
   split list the rule's or the base's on the region's states, `--max-size` and the forbid pairs
   (`--forbid` and the region's) with both states in the run.  A channel with no cell in the run is
   dropped by the spec build; its lines stay as the base has them.
2. `plan` (this file, on the polygon graph induced on the run's states; `replan.py` plans on the
   full graph, which a region's K does not fit): the master per channel at the declared δ, else the
   smallest feasible δ up to the final δ (never wider, the band is the owner's), the plans cached
   for `run.py --plans`.
3. `run.py --states` into `draw/` (arm 1, sequential, `overnight.LAND_RATIO`).  A channel's drawing
   ends "infeasible" or "unknown" (`overnight.needs_retry`: the realizer's own stop reasons): when
   the region lists `k_alt` for it, K moves to `k_alt` and the run is drawn once more in `alt/`,
   only if `k_alt` has a final δ in the window (the region's feasible set, `fit_delta`); the drawing
   with fewer failing channels goes on.  The band never widens.
4. `repair.py --states` pass 1 into `r1/`, pass 2 into `r2/` when a channel of `r1/` is still in
   pieces or necked (`contig.json`).  `--window` is `score.WINDOWS` in $M for a run of one channel
   only (the repair intersects every channel's band with one window); the final δ already fits each
   channel's window.
5. glue repair (`glue.py`) into `glue/`: detached pieces joined through zero-opportunity ZCTAs of
   other districts, applied only when no donor gains a piece or a neck; what it leaves is in
   `glue.json` for the owner.

**A point** is finished when its runs are: `merge.py` over every run's last folder into `merged/`
(`--rate 1`, `--gap-width`, `--window` for one channel), the gate (`tools/mandates/check.py`),
`score.py` (`score.txt`, `dollars.csv`, `m1.json`), `land.py`, and the per-district shape measures
of `tools/looks/study.py` (`shape.json`).  **Labels**: `fails M1` (the gap-width verdict of
`m1.json`), else `outside band` (a district outside its channel's dollar window, `dollars.csv`),
else `passes`; `fails shape` instead when the shape limits file says `"hard": true` and a district
breaches one; `infeasible` (a run with no plan inside its window or a drawing left infeasible with
no alternative that planned), `stopped` (a stage's cap or the `--hours` stop), `error` otherwise.
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

from td import data, geo  # noqa: E402
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
CAPS = {"replan": 600.0, "draw": 2700.0, "repair": 1800.0, "glue": 600.0, "merge": 3600.0}
DRAW_FRAC = 0.85                # run.py's per-channel time limit, of the draw's wall cap
LABELS = ("passes", "fails M1", "outside band", "fails shape", "infeasible", "stopped", "error")
RUN_BAD = ("error", "stopped", "infeasible")        # a run's failing statuses, worst first
STRUCTURES = {k: (os.path.join(ROOT, p), rule) for k, (p, rule) in overnight.STRUCTURES.items()}
GAP_ENV = overnight.GAP_ENV


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
    [{name, states, ks, k_alt, forbid}]}`.  `structures` {name: (base spec path, split rule)}
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
        if not isinstance(pid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", pid):
            errs.append(f"point {pid!r}: the id must be a file-name word")
            continue
        if pid in seen_ids:
            errs.append(f"point {pid}: listed twice")
        seen_ids.add(pid)
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
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name == "alt":
                    errs.append(f"{rw}: the name must be a file-name word other than 'alt'")
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
        runs = _group_runs(pid, entries, foot, errs)
        out.append({"id": pid, "structure": structure, "base": base, "rule": rule, "channels": norm, "runs": runs})
    if errs:
        raise PartitionError("\n".join(errs))
    return out


def _group_runs(pid: str, entries: list, foot: dict, errs: list) -> list:
    """The runs of one point from its (channel, name, states, k, k_alt, forbid, rest) entries: one per
    distinct state set, the sets pairwise disjoint, every channel with footprint states in a set
    listed there."""
    by = collections.OrderedDict()
    for c, name, sts, k, k_alt, forbid, rest in entries:
        r = by.setdefault(frozenset(sts), {"states": sts, "names": [], "ks": {}, "k_alt": {}, "forbid": set(),
                                            "rest": []})
        if not rest:
            r["names"].append(name)
        else:
            r["rest"].append(c)
        r["ks"][c] = k
        if k_alt:
            r["k_alt"][c] = k_alt
        r["forbid"] |= set(forbid)
    rest_sets = [r for r in by.values() if not r["names"]]
    runs = []
    for r in by.values():
        names = sorted(set(r["names"]))
        if len(names) > 1:
            errs.append(f"point {pid}: regions {names} have the same states ({', '.join(r['states'])}) in different channels "
                        "and must share one name")
        name = names[0] if names else ("rest" if len(rest_sets) == 1 else "rest-" + "-".join(sorted(r["rest"])))
        runs.append({"name": name, "states": r["states"], "ks": r["ks"], "k_alt": r["k_alt"],
                     "forbid": sorted(r["forbid"])})
    names = [r["name"] for r in runs]
    errs += [f"point {pid}: two runs are named {n!r}" for n in sorted({n for n in names if names.count(n) > 1})]
    for i, a in enumerate(runs):
        for b in runs[i + 1:]:
            both = sorted(set(a["states"]) & set(b["states"]))
            if both:
                errs.append(f"point {pid}: runs {a['name']!r} and {b['name']!r} overlap in {', '.join(both)} "
                            "without being the same set (merge.py takes one partition per point)")
        for c, fs in foot.items():
            if fs & set(a["states"]) and c not in a["ks"]:
                errs.append(f"point {pid}: {c} has footprint states in run {a['name']!r} "
                            f"({', '.join(sorted(fs & set(a['states'])))}) but lists no region of exactly "
                            f"{', '.join(a['states'])}")
    return runs


def load_partition(path: str, **kw) -> list:
    with open(path, encoding="utf-8") as fh:
        return validate_partition(json.load(fh), **kw)


# ------------------------------------------------------------------------------ a run's spec copy
def region_plan(sp, states, ks: dict, cells: dict, rule: str) -> dict:
    """`overnight.plan_point` on the run's states: per present channel (one with mass in the states)
    K, the region's $M, τ, the split list (the rule's, or the base's, on the states) and the final δ;
    `infeasible` {channel: why}; `absent` the channels with no cell there."""
    S = set(states)
    cs = {k: m for k, m in cells.items() if k[0] in S}
    mass = overnight.unit_mass(sp, cs)
    present = sorted(c for c in sp.channels if math.fsum(mass[c].values()) > 0)
    missing = [c for c in present if c not in ks]
    if missing:
        raise PartitionError(f"{', '.join(missing)} have cells in {', '.join(states)} but no K")
    sub = dataclasses.replace(sp, channels={c: sp.channels[c] for c in present})
    plan = overnight.plan_point({c: ks[c] for c in present}, sub, cs, rule)
    for v in plan["channels"].values():
        v["free"] = [u for u in v["free"] if u in S]
    plan["absent"] = sorted(set(sp.channels) - set(present))
    return plan


def run_spec_text(base_text: str, pid: str, run_name: str, states, plan: dict, forbid=(),
                  max_size: int | None = None) -> str:
    """The run's spec copy: the base TOML with each present channel's K, declared δ
    (`overnight.DECLARED_DELTA`, or the final δ when smaller), final δ, split list, `margin = false`,
    `max_size` when given and the forbid pairs with both states in the run; named `<point>-<run>`."""
    ch, S = plan["channels"], set(states)
    pairs = sorted({tuple(sorted(p)) for p in forbid if set(p) <= S})
    keys = {c: {"k": str(v["k"]), "margin": "false", **({"max_size": str(max_size)} if max_size else {})}
            for c, v in ch.items()}
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
             nch: int) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "sealed.py"), "plan", base, "--out-spec", out_spec,
            "--plans", plans, "--report", report, "--extract", extract, "--states", ",".join(states),
            "--time-limit", f"{max(30.0, cap / (2 * nch + 2)):g}"]


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


def nominal_chain(pid: str, run: dict, rdir: str, plans: str, extract: str, plan: dict, caps: dict) -> list:
    """[(stage, command, cap, env)] of a run's chain as it runs when nothing fails and nothing is
    retried: plan, draw, repair pass 1, glue (pass 2 and the `k_alt` re-run depend on the results)."""
    st, jobs, label = run["states"], jobs_of(run), f"sealed {pid}/{run['name']}"
    nch = len(plan["channels"])
    win = window_of(plan)
    return [("plan", plan_cmd(os.path.join(rdir, "spec-base.toml"), os.path.join(rdir, "spec.toml"), plans,
                              os.path.join(rdir, "replan.json"), extract, st, caps["replan"], nch),
             caps["replan"], None),
            ("draw", draw_cmd(os.path.join(rdir, "spec.toml"), os.path.join(rdir, "draw"), plans, extract, jobs, st,
                              caps["draw"]), caps["draw"], None),
            ("r1", repair_cmd(os.path.join(rdir, "draw"), os.path.join(rdir, "r1"), plans, extract, jobs, 1, label,
                              st, caps["repair"], win), caps["repair"], None),
            ("glue", glue_cmd(os.path.join(rdir, "r1"), os.path.join(rdir, "glue"), plans, extract, label, st),
             caps["glue"], GAP_ENV)]


def point_chain(pid: str, pdir: str, finals: list, base_spec: str, extract: str, window: str | None,
                caps: dict) -> list:
    """[(stage, command, cap, env)] of a point's merge, gate, score and land."""
    merged = os.path.join(pdir, "merged")
    sources = [f"{'+'.join(states)}={final}" for states, final in finals]
    return [("merge", merge_cmd(base_spec, merged, os.path.join(pdir, "merged_extract.json.gz"), extract, sources,
                                window), caps["merge"], GAP_ENV),
            ("gate", overnight.gate_cmd(merged), overnight.CAP_S["gate"], GAP_ENV),
            ("score", overnight.score_cmd(merged), overnight.CAP_S["post"], GAP_ENV),
            ("land", overnight.land_cmd(merged), overnight.CAP_S["post"], None)]


# ------------------------------------------------------------------------------ the plan stage
def cmd_plan(a) -> int:
    """`sealed.py plan`: `replan.py` on the polygon graph induced on `--states`."""
    from td import master
    replan = overnight._replan()
    run = replan.run
    states = tuple(x for x in a.states.split(",") if x)
    with open(a.spec, encoding="utf-8") as fh:
        src = fh.read()
    if replan.same_file(a.out_spec, a.spec):
        raise SystemExit("the copy must not overwrite the base spec")
    head = (f"# sealed-region master (tools/exp/contig/sealed.py plan): a copy of {os.path.abspath(a.spec)}\n"
            f"# planned on the polygon graph induced on {', '.join(states)}\n")
    deltas, plans, reports, doc = {}, {}, {}, {"source_spec": os.path.abspath(a.spec), "states": list(states),
                                                "channels": {}}

    def write():
        os.makedirs(os.path.dirname(os.path.abspath(a.out_spec)), exist_ok=True)
        with open(a.out_spec, "w", encoding="utf-8") as fh:
            fh.write(head + replan.banned_text(src, [], deltas=deltas))

    def build():
        s = tdspec.load(a.out_spec)
        ref = geo.read_reference()
        ext = tdspec.scope(s, data.conus(data.load(a.extract), ref))
        return tdspec.build(s, ext, ref, graph=run.induced_graph(geo.polygon_graph(), states))
    write()
    inst = build()
    for c, ch in inst.channels.items():
        p, rep = master.plan(inst, c, time_limit=a.time_limit)
        plans[c], reports[c] = p, rep
        entry = {"declared_delta": ch.spec.delta, "final_delta": ch.spec.final_delta,
                 "status_at_declared": rep.get("status")}
        if p is None:
            d = master.smallest_delta(inst, c, time_limit=a.time_limit)
            entry["smallest_delta"] = {"status": d.status, "delta": d.delta, "lower": d.lower}
            if d.delta is None or d.delta > ch.spec.final_delta:
                doc["channels"][c] = entry
                print(f"{c}: no plan up to final_delta {ch.spec.final_delta:g} ({d.status})", flush=True)
                _dump(a.report, doc)
                return 1
            deltas[c] = math.ceil(d.delta * 1e4) / 1e4
        entry["delta"] = deltas.get(c, ch.spec.delta)
        doc["channels"][c] = entry
        print(f"{c}: δ {entry['delta']:g} (declared {ch.spec.delta:g})", flush=True)
    if deltas:
        write()
        inst = build()
        for c in deltas:
            plans[c], reports[c] = master.plan(inst, c, time_limit=a.time_limit)
    for c, p in plans.items():
        if p is None:
            print(f"{c}: no plan at δ {doc['channels'][c]['delta']:g} on re-solve", flush=True)
            _dump(a.report, doc)
            return 1
    key = run.plans_key(a.out_spec, a.extract, a.plans)
    os.makedirs(a.plans, exist_ok=True)
    with open(key, "wb") as fh:
        pickle.dump((plans, reports), fh)
    doc["plans_file"] = key
    _dump(a.report, doc)
    return 0


def _dump(path, doc) -> None:
    if path:
        overnight._write_json(path, doc)


# ------------------------------------------------------------------------------ shape
_SHAPE = {}
_SHAPE_LOCK = threading.Lock()
SUM_COLUMNS = ("hull_fill", "bite", "aspect", "longest_axis_km", "doughnut", "doughnut_soft")


def _study():
    return overnight._load("looks_study", os.path.join(ROOT, "tools", "looks", "study.py"))


def load_limits(path: str | None) -> dict:
    """{"hard": bool, "limits": {column: {"min"?: x, "max"?: y}}} from L.json (columns of
    `tools/looks/study.py`'s per-district measures); the default is no limits, report only."""
    if path is None:
        return {"hard": False, "limits": {}}
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    lim = doc.get("limits")
    if not isinstance(lim, dict) or not isinstance(doc.get("hard", False), bool) or set(doc) - {"hard", "limits"}:
        raise PartitionError(f"{path}: expected {{\"hard\": bool, \"limits\": {{column: {{min, max}}}}}}")
    cols = set(_study().DISTRICT_COLUMNS)
    errs = [f"{path}: {k!r} is not a district measure of tools/looks/study.py" for k in lim if k not in cols]
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


# ------------------------------------------------------------------------------ labels
def label_point(m1: dict, rows: list, breaches: list, hard: bool) -> tuple:
    """(label, reason): `fails M1` on the gap-width verdict of `m1.json`, else `outside band` when a
    district of `dollars.csv` is outside its window, else `fails shape` for a breach under a hard
    limits file, else `passes`."""
    if m1["status"] != "pass":
        return "fails M1", f"M1 across coverage gaps: {m1['status']}, {m1['summary']}"
    bad = [r for r in rows if not r["ok"]]
    if bad:
        return "outside band", "; ".join(
            f"{r['district']} {r['usd']:,.1f}M outside "
            + ("no window" if r["lo"] is None else f"{r['lo']:,.1f}-{(r['cap'] or r['hi']):,.1f}M") for r in bad)
    if hard and breaches:
        return "fails shape", f"{len(breaches)} breaches of the hard shape limits, first {breaches[0]}"
    return "passes", ""


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

    def __init__(self, grid, root, host, extract, cells, points: dict, caps: dict, forbid, max_size, limits):
        super().__init__(grid, root, host, extract, cells)
        self.points, self.caps, self.forbid, self.max_size, self.limits = points, caps, forbid, max_size, limits
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
        """Spec copy, plan and draw of one K choice in `adir`; the drawn folder, its contig.json and
        the channels whose drawing ended on a stop reason of the realizer's own."""
        pid, rn = pt["id"], run["name"]
        sp, text = self.spec_of(pt)
        os.makedirs(adir, exist_ok=True)
        plan = region_plan(sp, run["states"], ks, self.cells, pt["rule"])
        if plan["infeasible"]:
            raise Stop("infeasible", "; ".join(plan["infeasible"].values()))
        base, spec, out = (os.path.join(adir, x) for x in ("spec-base.toml", "spec.toml", "draw"))
        with open(base, "w", encoding="utf-8") as fh:
            fh.write(run_spec_text(text, pid, rn, run["states"], plan, self.forbid | set(map(tuple, run["forbid"])),
                                   self.max_size))
        chain = dict((s, (cmd, cap, env)) for s, cmd, cap, env in
                     nominal_chain(pid, run, adir, self.plans, self.extract, plan, self.caps))
        if not (os.path.exists(spec) and finished(out)):
            cmd, cap, _ = chain["plan"]
            log = os.path.join(adir, "replan.log")
            info = self.stage(pid, f"{rn}{tag}.plan", cmd, log, cap)
            if info["stop"] == "cap":
                raise Stop("stopped", f"plan killed at its cap ({cap / 60:g} min)")
            if info["rc"] == 1 and "no plan" in overnight._text(log):
                raise Stop("infeasible", overnight._tail(log))
            if info["rc"] != 0:
                raise Stop("error", f"plan exited {info['rc']}: {overnight._tail(log)}")
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
        return {"dir": adir, "draw": out, "contig": contig, "failing": overnight.needs_retry(contig), "ks": ks,
                "plan": plan}

    def _chain(self, pt: dict, run: dict, rdir: str) -> None:
        pid, rn = pt["id"], run["name"]
        first = self._attempt(pt, run, rdir, dict(run["ks"]), "")
        got, retry = first, None
        alt = {c: run["k_alt"][c] for c in first["failing"] if c in run["k_alt"]}
        if alt:
            ks2 = {**run["ks"], **alt}
            sp, _ = self.spec_of(pt)
            bad = region_plan(sp, run["states"], ks2, self.cells, pt["rule"])["infeasible"]
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
                  draw_failing=got["failing"])
        adir, src = got["dir"], got["draw"]
        plan, jobs, label = got["plan"], jobs_of(run), f"sealed {pid}/{rn}"
        win = window_of(plan)
        for npass in (1, 2):
            if npass == 2 and clean(src):
                break
            out = os.path.join(adir, f"r{npass}")
            if not finished(out):
                overnight.set_aside(out)
                cap = self.caps["repair"]
                info = self.stage(pid, f"{rn}.r{npass}",
                                  repair_cmd(src, out, self.plans, self.extract, jobs, npass, label, run["states"], cap,
                                             win), os.path.join(adir, f"r{npass}.log"), cap)
                if info["stop"] == "cap":
                    self.note(pid, rn, **{f"r{npass}": f"killed at its cap ({cap / 60:g} min)"})
            if os.path.exists(os.path.join(out, "ledger.csv")):
                src = out
        gout = os.path.join(adir, "glue")
        if not os.path.exists(os.path.join(gout, "glue.json")):
            overnight.set_aside(gout)
            cap = self.caps["glue"]
            info = self.stage(pid, f"{rn}.glue", glue_cmd(src, gout, self.plans, self.extract, label, run["states"]),
                              os.path.join(adir, "glue.log"), cap, GAP_ENV)
            if info["stop"] == "cap":
                self.note(pid, rn, glue=f"killed at its cap ({cap / 60:g} min)")
            elif info["rc"] != 0:
                raise Stop("error", f"glue.py exited {info['rc']}: {overnight._tail(os.path.join(adir, 'glue.log'))}")
        if os.path.exists(os.path.join(gout, "glue.json")):
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
        finals = [(run["states"], os.path.join(self.root, rec["runs"][run["name"]]["final"])) for run in pt["runs"]]
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
        shape = {"error": None, "summary": {}, "breaches": [], "limits": self.limits}
        try:
            drows = measure_shape(merged, pid)
            shape["summary"] = shape_summary(drows)
            shape["breaches"] = shape_breaches(drows, self.limits["limits"])
        except Exception as e:      # reported, loudly: it decides the label only under hard limits
            shape["error"] = f"{type(e).__name__}: {e}"
            if self.limits["hard"]:
                raise Stop("error", f"shape measures failed under hard limits: {shape['error']}")
        overnight._write_json(os.path.join(merged, "shape.json"), shape)
        label, reason = label_point(m1["gap_width"], rows, shape["breaches"], self.limits["hard"])
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
    for pt in points:
        sp = tdspec.load(pt["base"])
        with open(pt["base"], encoding="utf-8") as fh:
            text = fh.read()
        print(f"\n######## point {pt['id']} ({pt['structure']}, rule {pt['rule']}): {len(pt['runs'])} runs")
        finals = []
        for run in pt["runs"]:
            rdir = os.path.join(a.root, pt["id"], run["name"])
            plan = region_plan(sp, run["states"], run["ks"], cells, pt["rule"])
            print(f"\n==== run {run['name']} ({','.join(run['states'])}), K {run['ks']}, slots {jobs_of(run)}")
            for c, v in sorted(plan["channels"].items()):
                print(f"  {c}: K {v['k']}, ${v['usd_m']:,.1f}M, τ {v['tau_m']:,.1f}M, final δ {v['final_delta']}, "
                      f"split list {','.join(v['free']) or 'none'}")
            if plan["absent"]:
                print(f"  no cell in the run (dropped by the spec build): {', '.join(plan['absent'])}")
            for c, why in plan["infeasible"].items():
                print(f"  INFEASIBLE {why}")
            for c, k in sorted(run["k_alt"].items()):
                alt = region_plan(sp, run["states"], {**run["ks"], c: k}, cells, pt["rule"])
                print(f"  k_alt {c} {k}: " + (alt["infeasible"].get(c) or f"final δ {alt['channels'][c]['final_delta']}"))
            if plan["infeasible"]:
                continue
            print(f"--- spec copy {os.path.join(rdir, 'spec-base.toml')}")
            print(run_spec_text(text, pt["id"], run["name"], run["states"], plan, forbid | set(map(tuple, run["forbid"])),
                                a.max_size), end="")
            print("---")
            for stage, cmd, cap, env in nominal_chain(pt["id"], run, rdir, plans, a.extract, plan, caps):
                print(f"[{stage}, cap {cap:g} s{', env ' + str(env) if env else ''}] " + " ".join(map(q, cmd)))
            finals.append((run["states"], os.path.join(rdir, "glue")))
        if len(finals) == len(pt["runs"]):
            pdir = os.path.join(a.root, pt["id"])
            win = merge_window(sp)
            print(f"\n==== point {pt['id']}: merge, gate, score, land")
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
    drv = Driver(grid, a.root, a.host, a.extract, cells, {p["id"]: p for p in todo}, caps, forbid, a.max_size, limits)
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
    r.add_argument("--dry-run", action="store_true", help="print the spec copies and commands; solve nothing")
    r.set_defaults(func=cmd_run)
    for name in ("index", "collect"):
        i = sub.add_parser(name, help="write <root>/SEALED.md from SEALED.json")
        i.add_argument("--root", required=True)
        i.set_defaults(func=cmd_index)
    p = sub.add_parser("plan", help="(a run's plan stage) the master per channel on the polygon graph induced on --states")
    p.add_argument("spec")
    p.add_argument("--out-spec", required=True)
    p.add_argument("--plans", required=True)
    p.add_argument("--report", default=None)
    p.add_argument("--extract", required=True)
    p.add_argument("--states", required=True)
    p.add_argument("--time-limit", type=float, default=150.0, help="seconds per master solve")
    p.set_defaults(func=cmd_plan)
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
