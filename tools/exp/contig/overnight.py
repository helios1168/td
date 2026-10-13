"""overnight.py -- the main-map overnight grid (2026-10-13): 21 points, five WIFI structures by K
totals 48-52, each planned, drawn and repaired by #125's chain (`set125.sh`) on the dollar extract
(`dollarize.py`, $M), unsealed on the full polygon graph, and labelled.

    "$TD_PY" -u tools/exp/contig/overnight.py run --host m5|m2 [--hours 8] [--slots N]
        [--only ID ...] [--root DIR] [--extract PATH] [--notify CMD]

**Points** (`POINTS`, the research's settled grid): each names a structure, the base spec under
`scenarios/` (`STRUCTURES`), and a K per channel; west8's six run on m2, the other fifteen on m5
(`HOST_OF`).  Per channel c at K_c (`plan_point`): τ_c is the channel's $M over K_c, summed from
the dollar extract over the spec's domain on M1's vertex set; the split list is the base spec's
(ne_plains, west8) or the #76 rule's, the units whose $ in c exceeds τ_c/2 (nw49, nw34, w1); the
final δ is the largest, to 1e-4 below, whose band τ_c(1 ± δ) lies in the channel's dollar window
(`score.WINDOWS`), up to the whole-state cap (`score.WHOLE_STATE_CAP`) for a channel with no split
unit, `K1_FINAL_DELTA` for one district.  A channel whose τ is outside its window makes the point
**infeasible** unrun.

**The chain** per point, in `<root>/<id>/`, each stage a child process logging to `<stage>.log`:
the spec copy (`spec-base.toml`: K, δ declared at `DECLARED_DELTA` or the final δ when smaller,
the final δ), `replan.py` (the split lists restated, `PLAN_S` per master solve, the plans cached
in `<root>/_plans`); `run.py` into `draw/` (arm 1, sequential, the #133 land term at
`LAND_RATIO`, `DRAW_S` per channel); one retry into `draw_retry/` at the failing channels' largest
plan δ plus `RETRY_WIDEN` when a channel's drawing ends "infeasible" or "unknown" (`needs_retry`:
the realizer's own stop reasons, trap 15), kept when fewer channels fail there (run.py's
`--delta` starts every channel at it); repair pass 1 into `r1/`; pass 2 into `r2/` only when M1
still fails on `r1/`; then `score.py --dollars-csv --m1-json` (`score.txt`, `dollars.csv`, `m1.json`)
and `land.py` (`land.csv`) on every stage folder.  Every M1 here, the gate and the score's,
measures necks across coverage gaps (`td.audit.GAP_WIDTH_ENV` = "1", G3); `m1.json` keeps the strict
verdict beside it.  A point holds `slots_of` slots, its channels and at least two: `run.py` and
`repair.py` pin HiGHS to one thread per worker only with `--jobs` above 1 (trap 18).

**Labels** (`label_of`, on the last folder with a ledger): **fails M1** when M1 fails after pass
2; **ineligible ($)** when a district is outside its dollar window, after the one re-run a
point earns (`rerun_k`: a channel whose failing districts are all under its window at K_c − 1,
all over at K_c + 1, as its own point `<id>-<channel><K>`); **eligible** when the scorer finds no
reason; **ineligible** with the scorer's reasons otherwise; **infeasible** for no plan within the
final δ (replan.py's own "no plan" stop, a master time limit included); **stopped** when the
`--hours` stop or a stage's wall cap (`CAP_S`) kills a stage; **error** for a stage that fails
without a folder or a launcher fault (`launcher_error.txt`).  The label and its reason are appended
to the last folder's `scorecard.md`.

**GRID.json** (`<root>/GRID.json`, written atomically) lists all 21 points at launch, the other
host's as "elsewhere", with the assumptions the run takes (`ASSUMPTIONS`, #111, #112, #119 and
#133 open), the limits, the extract and its sha256 and the code state; each point gains its
plan, stages, label and reason as it ends.  A second `run` resumes: a labelled point is kept, an
unlabelled one restarts at its first stage without a finished folder (manifest "done" and a
ledger), an unfinished folder moved aside, never deleted.  The `--hours` stop (from the first
launch, kept on a resume) starts no stage after it and kills the stages it finds running (SIGINT
to the stage's process group, then SIGKILL after `STOP_GRACE`).  Nothing here prints a cell's
value; maps are rendered on m5 after the run.

"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime
import importlib.util
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo  # noqa: E402
from td import spec as tdspec  # noqa: E402

HUB = os.environ.get("TD_REPO", ROOT)
GRID_NAME = "main_overnight_2026-10-13"
GRID_ROOT = os.path.join(HUB, "runs", "exp", GRID_NAME)
GRID_JSON = "GRID.json"
EXTRACT = os.path.join(HUB, "instance_descaled_usd.json.gz")
GAP_ENV = {audit.GAP_WIDTH_ENV: "1"}        # G3: the grid's M1 measures necks across coverage gaps

STRUCTURES = {                  # structure -> (base spec, split lists: the base's or the #76 rule)
    "ne_plains": ("scenarios/main_ne_plains.toml", "base"),
    "west8": ("scenarios/main_west8.toml", "base"),
    "nw49": ("scenarios/main_nw49.toml", "rule"),
    "nw34": ("scenarios/main_nw34.toml", "rule"),
    "w1": ("scenarios/main_w1.toml", "rule"),
}
HOST_OF = {"west8": "m2"}       # every other structure on m5 (D12)
SLOTS = {"m5": 12, "m2": 8}     # one thread per process; m2 lower after the smoke if memory is tight


def _point(pid: str, structure: str, **k) -> dict:
    return {"id": pid, "structure": structure, "k": k}


POINTS = [                      # the research's locked grid (2026-10-12)
    _point("ne-48-bal", "ne_plains", national=14, WH=10, FI=21, WIFI=3),
    _point("ne-50-bal", "ne_plains", national=15, WH=10, FI=22, WIFI=3),
    _point("ne-50-filight", "ne_plains", national=16, WH=11, FI=20, WIFI=3),
    _point("ne-52-bal", "ne_plains", national=15, WH=11, FI=23, WIFI=3),
    _point("ne-52-filight", "ne_plains", national=16, WH=11, FI=22, WIFI=3),
    _point("ne-cmp-tierP", "ne_plains", national=15, WH=11, FI=20, WIFI=3),
    _point("w8-48-bal", "west8", national=14, WH=11, FI=22, WIFI=1),
    _point("w8-50-bal", "west8", national=15, WH=11, FI=23, WIFI=1),
    _point("w8-50-filight", "west8", national=16, WH=12, FI=21, WIFI=1),
    _point("w8-52-bal", "west8", national=15, WH=12, FI=24, WIFI=1),
    _point("w8-52-filight", "west8", national=16, WH=12, FI=23, WIFI=1),
    _point("w8-cmp-seed", "west8", national=13, WH=11, FI=24, WIFI=1),
    _point("nw49-48", "nw49", national=15, WIFI=33),
    _point("nw49-50", "nw49", national=16, WIFI=34),
    _point("nw49-52", "nw49", national=17, WIFI=35),
    _point("nw34-48", "nw34", national=14, WIFI=34),
    _point("nw34-50", "nw34", national=15, WIFI=35),
    _point("nw34-52", "nw34", national=16, WIFI=36),
    _point("w1-48", "w1", WIFI=48),
    _point("w1-50", "w1", WIFI=50),
    _point("w1-52", "w1", WIFI=52),
]

HOURS = 8.0                     # the hard stop
LAND_RATIO = 10.0               # #133's R (owner decision open)
DECLARED_DELTA = 0.02           # set125's declared δ: replan.py takes the smallest up to the final δ
K1_FINAL_DELTA = 0.10           # one district holds τ whatever its band (D9)
PLAN_S = 600.0                  # replan.py --time-limit: 10 min per master solve
DRAW_S = 4500.0                 # run.py --time-limit: 75 min per channel
RETRY_WIDEN = 0.05              # the draw's one retry starts this much wider
RETRY_ON = ("infeasible", "unknown")    # a channel drawing's own stop reasons (`draw.Result.status`)
REPAIR_S = 1800.0               # repair.py --budget: 30 min per channel per pass
REPAIR = {1: ["--h0", "3", "--max-zctas", "1500", "--time-limit", "600", "--neck-time-limit", "120"],
          2: ["--h0", "8", "--max-zctas", "2000", "--time-limit", "300", "--neck-time-limit", "240"]}
CAP_S = {"replan": 300.0, "draw": 1800.0, "repair": 1500.0, "gate": 900.0, "post": 1800.0}
STOP_GRACE = 60.0               # a killed stage's grace after SIGINT (run.STOP_GRACE is 30 s)
LABELS = ("eligible", "fails M1", "ineligible ($)", "ineligible", "infeasible", "stopped", "error")
ASSUMPTIONS = [
    "#111, #112 (what gives way): open; no remedy arm beyond the stop/retry policy",
    "#119 (all-M1 bound): not used; no point is claimed minimal",
    "#133: R = 10 on in-state land, pieces of 20% of district mass or more, for this run only",
    "WIFI window $850-1,150M with the $1.6B whole-state allowance, national floor $1,000M: "
    "owner decisions (2026-10-12) still to be filed in PROBLEM.md",
    "M1 gated with necks across coverage gaps (scouts G1, TD_NECK_GAP_WIDTH=1); strict beside it",
]
LIVE = set()                    # the stage processes running, for the stop
LIVE_LOCK = threading.Lock()


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


score = _load("looks_score", os.path.join(ROOT, "tools", "looks", "score.py"))


def _replan():
    return _load("contig_replan", os.path.join(HERE, "replan.py"))


def _dollarize():
    return _load("contig_dollarize", os.path.join(HERE, "dollarize.py"))


def _sweep():
    return _load("exp_sweep", os.path.join(ROOT, "tools", "exp", "sweep.py"))


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------------------ a point's plan
def state_cells(extract_path: str, ref=None) -> dict:
    """{(state, fine channel): mass} of the extract over M1's vertex set, the ZCTAs
    `td.spec.build` places: $M on the dollar extract."""
    ref = geo.read_reference() if ref is None else ref
    ref = ref[ref["graph_vertex"] == "1"]
    state = dict(zip(ref["zcta"], ref["state"]))
    ext = data.load(extract_path)
    out = collections.Counter()
    for z, f, m in zip(ext.z, ext.channel, ext.m_rel):
        if state.get(z):
            out[state[z], f] += m
    return dict(out)


def unit_mass(sp, cells: dict) -> dict:
    """{channel: {unit: mass}} of a scenario whose units are states, as every grid structure's
    are: each unit's cells of the fine channels its domain gives the channel."""
    if sp.pieces or sp.metros:
        raise ValueError(f"{sp.name}: the grid's units are states, not pieces or metros")
    return {c: {u: math.fsum(cells.get((u, f), 0.0) for f in sorted(fs)) for u, fs in cs.domain.items()}
            for c, cs in sp.channels.items()}


def fit_delta(tau: float, k: int, lo: float, hi: float) -> float | None:
    """D9: the largest final δ, to 1e-4 below, whose band τ(1 ± δ) lies in the dollar window
    [lo, hi]; `K1_FINAL_DELTA` for one district (it holds τ whatever its band) with τ in the
    window; None when τ is not strictly inside it."""
    if k == 1:
        return K1_FINAL_DELTA if lo <= tau <= hi else None
    d = math.floor(min(tau - lo, hi - tau) / tau * 1e4 + 1e-9) / 1e4
    return d if d > 0 else None


def plan_point(ks: dict, sp, cells: dict, rule: str) -> dict:
    """The point's channels on its base spec `sp` (D9, D10): per channel K, its $M and τ, its
    split list (`rule` "base": the spec's own; "rule": #76's, the units above τ/2), its window in
    $M (`hi` the whole-state cap for a channel with no split unit and a cap) and its final δ;
    `infeasible` {channel: why} for each channel whose τ is outside its window."""
    if set(ks) != set(sp.channels):
        raise ValueError(f"{sp.name}: K for {sorted(ks)}, channels {sorted(sp.channels)}")
    mass = unit_mass(sp, cells)
    out = {"channels": {}, "infeasible": {}}
    for c, k in sorted(ks.items()):
        total = math.fsum(mass[c].values())
        tau = total / k
        if rule == "rule":
            free = sorted(u for u, m in mass[c].items() if m > tau / 2)
        else:
            free = sorted(u for u, m in sp.channels[c].modes.items() if m == "free")
        window = score.WINDOWS.get(c)
        lo = hi = d = None
        whole = not free and c in score.WHOLE_STATE_CAP
        if window is not None:
            lo, hi = window[0] / 1e6, (score.WHOLE_STATE_CAP[c] if whole else window[1]) / 1e6
            d = fit_delta(tau, k, lo, hi)
        out["channels"][c] = {"k": k, "usd_m": total, "tau_m": tau, "free": free, "lo_m": lo,
                              "hi_m": hi, "whole_state_cap": whole, "final_delta": d}
        if window is None:
            out["infeasible"][c] = f"{c}: no dollar window"
        elif d is None:
            out["infeasible"][c] = (f"{c}: τ outside the dollar window ({tau:,.1f}M at K {k}, "
                                    f"window {lo:,.1f}-{hi:,.1f}M)")
    return out


def point_spec_text(base_text: str, pid: str, plan: dict) -> str:
    """The point's spec copy: the base TOML with each channel's K, its declared δ
    (`DECLARED_DELTA`, or the final δ when smaller) and its final δ (`replan.banned_text`), and
    the scenario named after the point."""
    ch = plan["channels"]
    body = _replan().banned_text(
        base_text, [], deltas={c: min(DECLARED_DELTA, v["final_delta"]) for c, v in ch.items()},
        final_deltas={c: v["final_delta"] for c, v in ch.items()},
        keys={c: {"k": str(v["k"])} for c, v in ch.items()})
    body, n = re.subn(r'(?m)^name = ".*"$', f'name = "{pid}"', body, count=1)
    if n != 1:
        raise ValueError("the base spec has no [scenario] name line")
    return (f"# main-map overnight grid point {pid} ({GRID_NAME}, tools/exp/contig/overnight.py): "
            "the base spec with K, declared δ and final δ set per channel\n" + body)


# ------------------------------------------------------------------------------ commands
def slots_of(pt: dict) -> int:
    return max(2, len(pt["k"]))


def replan_cmd(base: str, pdir: str, plans: str, extract: str, plan: dict) -> list:
    free = [x for c, v in sorted(plan["channels"].items()) if v["free"]
            for x in ("--free", f"{c}={','.join(v['free'])}")]
    return [sys.executable, "-u", os.path.join(HERE, "replan.py"), base, "--out-spec",
            os.path.join(pdir, "spec.toml"), "--plans", plans, "--report",
            os.path.join(pdir, "replan.json"), "--extract", extract, "--time-limit", f"{PLAN_S:g}",
            *(free or ["--keep"])]


def draw_cmd(spec: str, out: str, plans: str, extract: str, jobs: int, delta: float | None = None) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "run.py"), spec, "--plans", plans, "--extract",
            extract, "--out", out, "--arm", "arm1", "--sequential", "--land-ratio", f"{LAND_RATIO:g}",
            "--time-limit", f"{DRAW_S:g}", "--jobs", str(jobs),
            *(["--delta", f"{delta:g}"] if delta is not None else [])]


def repair_cmd(src: str, out: str, plans: str, extract: str, jobs: int, npass: int, label: str) -> list:
    return [sys.executable, "-u", os.path.join(HERE, "repair.py"), src, "--out", out, "--plans", plans,
            "--extract", extract, "--keep-support", "--flow", *REPAIR[npass], "--budget",
            f"{REPAIR_S:g}", "--jobs", str(jobs), "--label", f"{label}, repair pass {npass}"]


def gate_cmd(folder: str) -> list:
    return [sys.executable, os.path.join(ROOT, "tools", "mandates", "check.py"), folder]


def score_cmd(folder: str) -> list:
    return [sys.executable, os.path.join(ROOT, "tools", "looks", "score.py"), folder, "--dollars-csv",
            "--m1-json"]


def land_cmd(folder: str) -> list:
    return [sys.executable, os.path.join(HERE, "land.py"), folder, "--ratio", f"{LAND_RATIO:g}"]


# ------------------------------------------------------------------------------ verdicts
def needs_retry(contig: dict) -> list:
    """The channels whose drawing ended on a stop reason of the realizer's own (`RETRY_ON`)."""
    return sorted(c for c, ch in contig.get("channels", {}).items() if ch.get("status") in RETRY_ON)


def retry_delta(contig: dict, failing: list) -> float:
    """The retry's internal δ: the failing channels' largest plan δ plus `RETRY_WIDEN`."""
    return round(max(contig["channels"][c]["plan_delta"] for c in failing) + RETRY_WIDEN, 4)


def read_dollars(path: str) -> list:
    """`score.write_dollars`'s rows with $M as floats (None where blank) and flags as bools."""
    def num(x):
        return None if x == "" else float(x)
    with open(path, newline="") as fh:
        return [{"channel": r["channel"], "district": r["district"], "usd": num(r["usd_m"]),
                 "lo": num(r["lo_m"]), "hi": num(r["hi_m"]), "cap": num(r["whole_state_cap_m"]),
                 "allowance": r["allowance"] == "1", "ok": r["ok"] == "1"} for r in csv.DictReader(fh)]


def read_score(path: str) -> tuple:
    """(eligible, reasons) from a `score.py` report: its `eligible:` line and the `  - ` lines
    under it."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("eligible: "):
            why = []
            for x in lines[i + 1:]:
                if not x.startswith("  - "):
                    break
                why.append(x[4:])
            return line == "eligible: yes", why
    raise ValueError(f"{path}: no eligible line")


def label_of(m1: dict, rows: list, eligible: bool, why: list) -> tuple:
    """(label, reason) of a point's last folder: M1 first (its gated verdict, `m1` as `m1.json`
    holds it), then the dollar gate's rows, then the scorer."""
    if m1["status"] != "pass":
        return "fails M1", f"M1 across coverage gaps: {m1['status']}, {m1['summary']}"
    bad = [r for r in rows if not r["ok"]]
    if bad:
        return "ineligible ($)", "; ".join(
            f"{r['district']} {r['usd']:,.1f}M outside "
            + ("no window" if r["lo"] is None else f"{r['lo']:,.1f}-{(r['cap'] or r['hi']):,.1f}M")
            for r in bad)
    if eligible:
        return "eligible", ""
    return "ineligible", "; ".join(why)


def rerun_k(rows: list, ks: dict) -> dict | None:
    """D13: the K per channel of the one re-run a dollar-gate failure earns, or None: a channel
    whose failing districts are all under its window goes to K − 1 (never 0), all over its
    window (its whole-state cap for a district taking it) to K + 1; a mixed channel, or one with
    no window, earns none."""
    bad = collections.defaultdict(list)
    for r in rows:
        if not r["ok"]:
            bad[r["channel"]].append(r)
    if not bad:
        return None
    out = dict(ks)
    for c, rs in bad.items():
        if any(r["lo"] is None for r in rs):
            return None
        if all(r["usd"] < r["lo"] for r in rs) and ks[c] > 1:
            out[c] = ks[c] - 1
        elif all(r["usd"] > (r["cap"] if r["cap"] is not None else r["hi"]) for r in rs):
            out[c] = ks[c] + 1
        else:
            return None
    return out


def rerun_id(pid: str, ks: dict, new: dict) -> str:
    return pid + "".join(f"-{c}{new[c]}" for c in sorted(new) if new[c] != ks[c])


# ------------------------------------------------------------------------------ GRID.json
def _write_json(path: str, doc: dict) -> None:
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(path + ".tmp", path)


def record(pt: dict, host: str, parent: str | None = None) -> dict:
    """A point's GRID.json entry before it runs; another host's point is "elsewhere"."""
    mine = HOST_OF.get(pt["structure"], "m5")
    return {"id": pt["id"], "structure": pt["structure"], "k": dict(pt["k"]), "total": sum(pt["k"].values()),
            "host": mine, "parent": parent, "status": "queued" if mine == host else "elsewhere",
            "label": None, "reason": None, "plan": None, "stages": {}, "final": None, "rerun": None,
            "started_at": None, "finished_at": None}


def grid_doc(host: str, extract: str, extract_sha256: str, deadline: float, code: dict) -> dict:
    return {"grid": GRID_NAME, "host": host, "created_at": now(),
            "deadline": datetime.datetime.fromtimestamp(deadline, datetime.timezone.utc).isoformat(
                timespec="seconds"),
            "extract": extract, "extract_sha256": extract_sha256, "code": code,
            "assumptions": ASSUMPTIONS, "land_ratio": LAND_RATIO, "gap_width_gate": True,
            "limits": {"plan_s_per_solve": PLAN_S, "draw_s_per_channel": DRAW_S,
                       "retry_widen": RETRY_WIDEN, "repair_s_per_pass": REPAIR_S, "hours": HOURS,
                       "caps_s": CAP_S},
            "points": {pt["id"]: record(pt, host) for pt in POINTS}}


class Grid:
    """GRID.json under a lock: every change written at once, atomically."""

    def __init__(self, path: str, doc: dict):
        self.path, self.doc, self.lock = path, doc, threading.Lock()
        _write_json(path, doc)

    def deadline(self) -> float:
        return datetime.datetime.fromisoformat(self.doc["deadline"]).timestamp()

    def get(self, pid: str) -> dict:
        with self.lock:
            return json.loads(json.dumps(self.doc["points"][pid]))

    def update(self, pid: str, **fields) -> None:
        with self.lock:
            self.doc["points"][pid].update(fields)
            _write_json(self.path, self.doc)

    def stage(self, pid: str, name: str, info: dict) -> None:
        with self.lock:
            self.doc["points"][pid]["stages"][name] = info
            _write_json(self.path, self.doc)

    def add(self, rec: dict) -> None:
        with self.lock:
            self.doc["points"][rec["id"]] = rec
            _write_json(self.path, self.doc)


# ------------------------------------------------------------------------------ stages
def _end(p) -> int:
    """SIGINT to a stage's process group (its collectors stop their workers, `run.stop`), then
    SIGKILL after `STOP_GRACE`; its exit code."""
    for sig in (signal.SIGINT, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            return p.wait(timeout=STOP_GRACE)
        except subprocess.TimeoutExpired:
            continue
    return p.wait()


def child(cmd: list, log_path: str, cap: float, deadline: float, env: dict | None = None) -> dict:
    """One stage: `cmd` in its own process group, stdout and stderr to `log_path`, killed at
    `cap` seconds or at `deadline`; {rc, seconds, stop: None, "cap" or "deadline"}."""
    left = deadline - time.time()
    if left <= 0:
        return {"rc": None, "seconds": 0.0, "stop": "deadline"}
    timeout, stop, t0 = min(cap, left), None, time.time()
    with open(log_path, "w") as lg:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=lg, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             env={**os.environ, **(env or {})}, start_new_session=True)
        with LIVE_LOCK:
            LIVE.add(p)
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop = "deadline" if left <= cap else "cap"
            rc = _end(p)
        finally:
            with LIVE_LOCK:
                LIVE.discard(p)
    return {"rc": rc, "seconds": round(time.time() - t0, 1), "stop": stop}


def stop_all() -> None:
    """End every stage still running (the launcher stopped or interrupted)."""
    with LIVE_LOCK:
        procs = list(LIVE)
    for p in procs:
        _end(p)


def finished(folder: str) -> bool:
    """A stage folder a resumed run keeps: its manifest says done and its ledger is written."""
    try:
        with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as fh:
            done = json.load(fh).get("status") == "done"
    except (OSError, ValueError):
        return False
    return done and os.path.exists(os.path.join(folder, "ledger.csv"))


def set_aside(folder: str) -> str | None:
    """Move an unfinished stage folder to `<folder>.stale<N>` (run.py and repair.py refuse a
    folder holding files); never deletes.  The new path, or None when there was none."""
    if not os.path.exists(folder):
        return None
    n = 1
    while os.path.exists(f"{folder}.stale{n}"):
        n += 1
    os.rename(folder, f"{folder}.stale{n}")
    return f"{folder}.stale{n}"


def _text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _tail(path: str) -> str:
    return (_text(path).strip().splitlines() or [""])[-1][:300]


def label_scorecard(folder: str, label: str, reason: str) -> None:
    with open(os.path.join(folder, "scorecard.md"), "a", encoding="utf-8") as fh:
        fh.write(f"\n**Overnight grid label ({GRID_NAME}):** {label}" + (f" ({reason})" if reason else "") + "\n")


class Stop(Exception):
    """A stage killed or failed: the point ends with `label` and `reason`."""

    def __init__(self, label: str, reason: str):
        super().__init__(reason)
        self.label, self.reason = label, reason


class Runner:
    """One host's points of the grid: `point` runs one through the chain and labels it."""

    def __init__(self, grid: Grid, root: str, host: str, extract: str, cells: dict):
        self.grid, self.root, self.host, self.extract, self.cells = grid, root, host, extract, cells
        self.plans = os.path.join(root, "_plans")
        self.deadline = grid.deadline()

    def stage(self, pid: str, name: str, cmd: list, log: str, cap: float, env=None) -> dict:
        info = child(cmd, log, cap, self.deadline, env)
        self.grid.stage(pid, name, {**info, "log": os.path.relpath(log, self.root)})
        if info["stop"] == "deadline":
            raise Stop("stopped", f"the {self.grid.doc['limits']['hours']:g} h stop during {name}")
        return info

    def point(self, pt: dict) -> list:
        """Run `pt` and label it; the re-run it earns, as a list of new points to queue."""
        pid = pt["id"]
        self.grid.update(pid, status="running", started_at=now())
        try:
            label, reason, final, new = self._chain(pt)
        except Stop as e:
            label, reason, final, new = e.label, e.reason, None, []
        except Exception as e:      # a launcher fault: the point is labelled, the grid goes on
            label, reason, final, new = "error", f"{type(e).__name__}: {e}", None, []
            os.makedirs(os.path.join(self.root, pid), exist_ok=True)
            with open(os.path.join(self.root, pid, "launcher_error.txt"), "w") as fh:
                fh.write(traceback.format_exc())
        if final is not None:
            label_scorecard(final, label, reason)
        self.grid.update(pid, status="done", label=label, reason=reason, finished_at=now(),
                         final=final and os.path.relpath(final, self.root))
        return new

    def _chain(self, pt: dict) -> tuple:
        pid, ks = pt["id"], pt["k"]
        pdir = os.path.join(self.root, pid)
        os.makedirs(pdir, exist_ok=True)
        jobs = slots_of(pt)
        base_path, rule = STRUCTURES[pt["structure"]]
        base_path = os.path.join(ROOT, base_path)
        plan = plan_point(ks, tdspec.load(base_path), self.cells, rule)
        self.grid.update(pid, plan=plan)
        if plan["infeasible"]:
            return "infeasible", "; ".join(plan["infeasible"].values()), None, []
        spec = os.path.join(pdir, "spec.toml")
        if not (os.path.exists(spec) and finished(os.path.join(pdir, "draw"))):
            with open(base_path, encoding="utf-8") as fh:
                text = point_spec_text(fh.read(), pid, plan)
            base = os.path.join(pdir, "spec-base.toml")
            with open(base, "w", encoding="utf-8") as fh:
                fh.write(text)
            log = os.path.join(pdir, "replan.log")
            info = self.stage(pid, "replan", replan_cmd(base, pdir, self.plans, self.extract, plan), log,
                              PLAN_S * len(ks) + CAP_S["replan"])
            if info["stop"] == "cap":
                raise Stop("stopped", f"replan.py killed at its cap ({(PLAN_S * len(ks) + CAP_S['replan']) / 60:g} min)")
            if info["rc"] == 1 and "no plan" in _text(log):
                return "infeasible", _tail(log), None, []
            if info["rc"] != 0:
                raise Stop("error", f"replan.py exited {info['rc']}: {_tail(log)}")
        src = self._draw(pid, pdir, spec, jobs)
        final = self._repair(pid, pdir, src, jobs, 1)
        if self.stage(pid, "gate_r1", gate_cmd(final), os.path.join(pdir, "gate_r1.log"),
                      CAP_S["gate"], GAP_ENV)["rc"] != 0:
            final = self._repair(pid, pdir, final, jobs, 2)
        for name in ("draw", "draw_retry", "r1", "r2"):
            folder = os.path.join(pdir, name)
            if os.path.exists(os.path.join(folder, "ledger.csv")):
                self.stage(pid, f"score_{name}", score_cmd(folder), os.path.join(folder, "score.txt"),
                           CAP_S["post"], GAP_ENV)
                self.stage(pid, f"land_{name}", land_cmd(folder), os.path.join(pdir, f"land_{name}.log"),
                           CAP_S["post"])
        with open(os.path.join(final, "m1.json"), encoding="utf-8") as fh:
            m1 = json.load(fh)["gap_width"]
        rows = read_dollars(os.path.join(final, "dollars.csv"))
        label, reason = label_of(m1, rows, *read_score(os.path.join(final, "score.txt")))
        new = []
        if label == "ineligible ($)" and pt.get("parent") is None:
            ks2 = rerun_k(rows, ks)
            if ks2 is not None:
                kid = {"id": rerun_id(pid, ks, ks2), "structure": pt["structure"], "k": ks2, "parent": pid}
                self.grid.add(record(kid, self.host, parent=pid))
                self.grid.update(pid, rerun=kid["id"])
                reason += f"; re-run {kid['id']}"
                new.append(kid)
        return label, reason, final, new

    def _draw(self, pid: str, pdir: str, spec: str, jobs: int) -> str:
        """The drawn folder repair starts from: `draw/`, or `draw_retry/` when the first drawing
        ended on `RETRY_ON` and fewer channels do in the retry's ledger."""
        out = os.path.join(pdir, "draw")
        if not finished(out):
            set_aside(out)
            info = self.stage(pid, "draw", draw_cmd(spec, out, self.plans, self.extract, jobs),
                              os.path.join(pdir, "draw.log"), DRAW_S + CAP_S["draw"])
            if info["stop"] == "cap":
                raise Stop("stopped", f"draw killed at its cap ({(DRAW_S + CAP_S['draw']) / 60:g} min)")
        if not os.path.exists(os.path.join(out, "ledger.csv")):
            raise Stop("error", f"run.py wrote no ledger: {_tail(os.path.join(pdir, 'draw.log'))}")
        with open(os.path.join(out, "contig.json"), encoding="utf-8") as fh:
            contig = json.load(fh)
        failing = needs_retry(contig)
        if not failing:
            return out
        retry = os.path.join(pdir, "draw_retry")
        if not finished(retry):
            set_aside(retry)
            self.stage(pid, "draw_retry",
                       draw_cmd(spec, retry, self.plans, self.extract, jobs, retry_delta(contig, failing)),
                       os.path.join(pdir, "draw_retry.log"), DRAW_S + CAP_S["draw"])
        if not os.path.exists(os.path.join(retry, "contig.json")):
            return out
        with open(os.path.join(retry, "contig.json"), encoding="utf-8") as fh:
            better = len(needs_retry(json.load(fh))) < len(failing)
        return retry if better and os.path.exists(os.path.join(retry, "ledger.csv")) else out

    def _repair(self, pid: str, pdir: str, src: str, jobs: int, npass: int) -> str:
        """Repair pass `npass` of `src` into `r<npass>/`; the folder the chain goes on from (`src`
        when the pass wrote no ledger)."""
        out = os.path.join(pdir, f"r{npass}")
        if not finished(out):
            set_aside(out)
            self.stage(pid, f"r{npass}", repair_cmd(src, out, self.plans, self.extract, jobs, npass, pid),
                       os.path.join(pdir, f"r{npass}.log"),
                       REPAIR_S + float(REPAIR[npass][5]) + CAP_S["repair"])
        return out if os.path.exists(os.path.join(out, "ledger.csv")) else src


# ------------------------------------------------------------------------------ the scheduler
def order(points: list) -> list:
    """Largest single channel first (single WIFI, then national + WIFI: the longest draws)."""
    return sorted(points, key=lambda p: (-max(p["k"].values()), p["id"]))


def schedule(todo: list, slots: int, deadline: float, work, need=slots_of, clock=time.time,
             poll: float = 5.0) -> list:
    """Run `work(point)` for the points of `todo`, in order, on `slots` slots, a point holding
    `need(point)` while it runs, first fit (a smaller point fills slots a larger one cannot);
    the points `work` returns (re-runs) go to the front of the queue.  No point starts at or after
    `deadline`; returns those never started."""
    big = [p["id"] for p in todo if need(p) > slots]
    if big:
        raise ValueError(f"points needing more than {slots} slots: {big}")
    queue, running, free = list(todo), {}, slots
    with concurrent.futures.ThreadPoolExecutor(max_workers=slots) as pool:
        while queue or running:
            if clock() < deadline:
                for p in list(queue):
                    if need(p) <= free:
                        queue.remove(p)
                        free -= need(p)
                        running[pool.submit(work, p)] = p
            if not running:
                break
            done, _ = concurrent.futures.wait(running, timeout=poll,
                                              return_when=concurrent.futures.FIRST_COMPLETED)
            for f in done:
                p = running.pop(f)
                free += need(p)
                queue[:0] = f.result() or []
    return queue


# ------------------------------------------------------------------------------ the CLI
def open_grid(root: str, host: str, extract: str, hours: float) -> Grid:
    """GRID.json at `root`: the one there (a resume, its stop kept), or a new one listing every
    point."""
    path = os.path.join(root, GRID_JSON)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("host") != host:
            raise SystemExit(f"{path} is {doc.get('host')}'s grid, not {host}'s")
        return Grid(path, doc)
    doc = grid_doc(host, extract, _dollarize().sha256(extract), time.time() + 3600.0 * hours,
                   _sweep().code_state())
    doc["limits"]["hours"] = hours
    return Grid(path, doc)


def cmd_run(a) -> int:
    if _dollarize().rates_of(a.extract) is None:
        raise SystemExit(f"{a.extract} is not a dollar extract (tools/exp/contig/dollarize.py)")
    os.makedirs(a.root, exist_ok=True)
    grid = open_grid(a.root, a.host, a.extract, a.hours)
    pts = [grid.get(pid) for pid in grid.doc["points"]]
    todo = order([p for p in pts if p["host"] == a.host and p["label"] is None
                  and (not a.only or p["id"] in a.only)])
    runner = Runner(grid, a.root, a.host, a.extract, state_cells(a.extract) if todo else {})
    print(f"{GRID_NAME} on {a.host}: {len(todo)} points, {a.slots} slots, stop at {grid.doc['deadline']}",
          flush=True)
    try:
        left = schedule(todo, a.slots, grid.deadline(), runner.point)
    except BaseException:
        stop_all()
        raise
    for p in left:
        grid.update(p["id"], status="done", label="stopped",
                    reason=f"not started before the {grid.doc['limits']['hours']:g} h stop", finished_at=now())
    mine = [grid.get(pid) for pid in grid.doc["points"] if grid.doc["points"][pid]["host"] == a.host]
    counts = collections.Counter(p["label"] for p in mine)
    line = f"{GRID_NAME} {a.host}: " + ", ".join(f"{counts[x]} {x}" for x in LABELS if counts[x])
    print(line, flush=True)
    if a.notify:
        _sweep().notify(a.notify, line)
    return 0 if all(p["label"] in LABELS for p in mine if not a.only or p["id"] in a.only) else 1


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="tools/exp/contig/overnight.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run this host's points")
    r.add_argument("--host", required=True, choices=sorted(SLOTS))
    r.add_argument("--hours", type=float, default=HOURS, help="the hard stop, from the first launch")
    r.add_argument("--slots", type=int, default=None, help="processes at once (default SLOTS[host])")
    r.add_argument("--only", nargs="*", default=None, help="these point ids only")
    r.add_argument("--root", default=GRID_ROOT)
    r.add_argument("--extract", default=EXTRACT)
    r.add_argument("--notify", default=None, help="a command the run ends with (sweep.py's NOTIFY)")
    r.set_defaults(func=cmd_run)
    return ap


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    if getattr(a, "slots", 0) is None:
        a.slots = SLOTS[a.host]
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
