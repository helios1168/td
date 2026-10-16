"""overnight.py -- the main-map overnight grid (2026-10-13): 21 points, five WIFI structures by K
totals 48-52, each planned, drawn and repaired by #125's chain (`set125.sh`) on the dollar extract
(`dollarize.py`, $M), unsealed on the full polygon graph, and labelled.

    "$TD_PY" -u tools/exp/contig/overnight.py run --host m5|m2 [--hours 8] [--slots N]
        [--only ID ...] [--root DIR] [--extract PATH] [--notify CMD] [--window-band]
    "$TD_PY" tools/exp/contig/overnight.py collect --from m2 [--ssh ALIAS] [--remote-root DIR]
        [--root DIR] [--anyway]
    "$TD_PY" tools/exp/contig/overnight.py morning [--root DIR] [--no-render] [--jobs N]
    "$TD_PY" -u tools/exp/contig/overnight.py smoke --out DIR [--point ID] [--host m5|m2]
        [--extract PATH] [--hours H]
    "$TD_PY" tools/exp/contig/overnight.py smoke --compare A B

**Points** (`POINTS`, the research's settled grid): each names a structure, the base spec under
`scenarios/` (`STRUCTURES`), and a K per channel; west8's six run on m2, the other fifteen on m5
(`HOST_OF`).  Per channel c at K_c (`plan_point`): τ_c is the channel's $M over K_c, summed from
the dollar extract over the spec's domain on M1's vertex set; the split list is the base spec's
(ne_plains, west8) or the #76 rule's, the units whose $ in c exceeds τ_c/2 (nw49, nw34, w1); the
final δ is the largest, to 1e-4 below, whose band τ_c(1 ± δ) lies in the channel's dollar window
(`score.WINDOWS`), up to the whole-state cap (`score.WHOLE_STATE_CAP`) for a channel with no split
unit, `K1_FINAL_DELTA` for one district.  A channel whose τ is outside its window makes the point
**infeasible** unrun.  With `--window-band` (off here, so the 10-13 grid reproduces; on in
`sealed.py`; owner's approval, #112 comment, 2026-10-14) the spec copy also writes `band_lo` = L/τ
and `band_hi` = U/τ per channel (`td.spec`): the band the master, the draw, the repair and the audit
hold is then the dollar window itself, never ±δ, and `final_delta` is written for reporting only.

**The chain** per point, in `<root>/<id>/`, each stage a child process logging to `<stage>.log`:
the spec copy (`spec-base.toml`: K, δ declared at `DECLARED_DELTA` or the final δ when smaller,
the final δ), `replan.py` (the split lists restated, `PLAN_S` per master solve, the plans cached
in `<root>/_plans`); `run.py` into `draw/` (arm 1, sequential, the #133 land term at
`LAND_RATIO`, `DRAW_S` per channel); one retry into `draw_retry/` at the failing channels' largest
plan δ plus `RETRY_WIDEN` when a channel's drawing ends "infeasible" or "unknown" (`needs_retry`:
the realizer's own stop reasons, trap 15), kept when fewer channels fail there (run.py's
`--delta` starts every channel at it; none under `--window-band`, where the band cannot widen); repair pass 1 into `r1/`; pass 2 into `r2/` only when M1
still fails on `r1/`; then `score.py --dollars-csv --m1-json` (`score.txt`, `dollars.csv`, `m1.json`)
and `land.py` (`land.csv`) on every stage folder.  Every M1 here, the gate and the score's,
measures necks across coverage gaps (`td.audit.GAP_WIDTH_ENV` = "1", G3); `m1.json` keeps the strict
verdict beside it.  A point holds `slots_of` slots, its channels and at least two: `run.py` and
`repair.py` pin HiGHS to one thread per worker only with `--jobs` above 1 (trap 18).

**Labels** (`label_of`, on the last folder with a ledger, after one more gate stage there, `gate`, run as
`ifa_index_night.py --gate` so the sides of the pieces and necks it judged are recorded next to the point): **fails M1**
when that final gate did not complete (killed at its cap: **stopped**) or exited other than 0 and the
Manhattan exception does not pass its evidence (`sealed.manhattan_verdict`: only a detached piece holding a
36061 ZCTA and a neck whose cut-off side holds one, owner, 2026-10-14, td#140, and necks measured), or `m1.json` fails; **ineligible ($)** when a district is outside its dollar window, judged exactly (`sealed.exact_rows`: the
ledger's cells at the full extract's masses and rates, unrounded dollars, the edges in; the ledger's districts must be
`districts.csv`'s), after the one re-run a
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

**collect** (on m5, after the run): the other host's GRID.json read over ssh, refused while one
of its points has no label (`--anyway` copies them as they are) or when its extract is not this
grid's; its points' folders hashed there (`shasum -a 256`), copied with `rsync -a`, hashed here
and compared file by file.  On a match its records replace the "elsewhere" ones in this GRID.json
with a `collected` note and its own GRID.json is kept as `GRID.<host>.json`; a mismatch merges
nothing and exits 1.  `collect_<host>.json` lists every file's sha256 and the problems either way.

**morning** (on m5, after collect): every stage folder rendered unless current
(`tools/maps/render.py --if-stale`, under the G3 gate, its $M through `fac_usd.json`, a factor
of 1 per fine channel, D14), the final folder titled with its point's label (`title_of`); then
`MORNING.md`, one table in the settled order (`morning_order`: eligible first by the scorer's
`rank_key`, then fails M1, ineligible ($), ineligible, infeasible, stopped and error, a balanced
point beside its FI-light partner when both carry one label) with K, splits, defects, the worst
district's $ against its channel's mean, M1 across gaps and strict, the largest in-state land
ratio, the label and links, the assumptions above it and "Needs your eye" below (`eye_items`:
every M1 flip but El Paso's, every whole-state allowance, every split group beyond R, every
failed render and unlabelled point); and `MORNING.pdf`, one page per point in that order, the
final folder's `zip_summary.png` (`summary.png` when it has none, `map_png`) or a page naming the
label and reason.  Both open with the index (`index_rows`; `index_md`, `index_pages`): per point,
in that order, K and its channel structure, and per channel the target $ per district (WIFI's
window midpoint), the window, and the final folder's average, min and max $ per district with
their deviation from the target and the districts outside the window, or the planned τ for a
point with no final folder.

**smoke** (before the launch, on each Studio): one point's replan and draw, as `run` would draw
it, into an empty folder with its own plan cache; `smoke.json` records the code, the extract's
and the ledger's sha256, each channel's drawing status, the seconds, the peak RSS of any one
child process (`RUSAGE_CHILDREN`) and the slots it leaves room for (`suggest_slots`, D12).
`--compare` reads two of them (`host:path` over ssh) and exits 0 only when they agree
(`compare_smoke`).
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
import resource
import shlex
import signal
import socket
import subprocess
import sys
import textwrap
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
CHANNELS = ("national", "WH", "FI", "WIFI")    # the order K is written in
STAGES = ("draw", "draw_retry", "r1", "r2")     # a point's stage folders, in chain order
RENDER_S = 1800.0               # one folder's render cap
EL_PASO = ("79718-79734", "79734-79718")        # the TX K3 flip of d312834's audit (G3)
MEM_GIB = {"m2": 24}            # the memory the smoke's peak RSS divides (D12)
PDF_PAGE = (2600, 1500)         # a page without a map, when no map sets the size
LIVE = set()                    # the stage processes running, for the stop
LIVE_LOCK = threading.Lock()
HALT = threading.Event()        # set by `schedule` while it unwinds: no stage starts, a started one is ended


class Halted(BaseException):
    """A stage refused because the scheduler is unwinding; not an `Exception`, so no point is labelled by it."""


_LOAD_LOCK = threading.RLock()     # points start on threads; a module is never seen half-loaded


def _load(name: str, path: str):
    with _LOAD_LOCK:
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
        return sys.modules[name]


score = _load("looks_score", os.path.join(ROOT, "tools", "looks", "score.py"))


def _sealed():
    """`sealed.py`, loaded by path on first use: it loads this module, so it cannot be loaded at the top."""
    return _load("contig_sealed", os.path.join(HERE, "sealed.py"))


def _replan():
    return _load("contig_replan", os.path.join(HERE, "replan.py"))


def _dollarize():
    return _load("contig_dollarize", os.path.join(HERE, "dollarize.py"))


def _sweep():
    return _load("exp_sweep", os.path.join(ROOT, "tools", "exp", "sweep.py"))


def _render():
    return _load("maps_render", os.path.join(ROOT, "tools", "maps", "render.py"))


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


def plan_point(ks: dict, sp, cells: dict, rule: str, floor: dict | None = None,
               window_band: bool = False) -> dict:
    """The point's channels on its base spec `sp` (D9, D10): per channel K, its $M and τ, its
    split list (`rule` "base": the spec's own; "rule": #76's, the units above τ/2), its window in
    $M (`hi` the whole-state cap for a channel with no split unit and a cap) and its final δ;
    `infeasible` {channel: why} for each channel whose τ is outside its window.  `floor`
    {channel: δ} raises a channel's final δ to at least that (a `-wide` point: the master's
    smallest feasible δ when the window's fit has no plan); the dollar gate is unchanged.  With
    `window_band` (`--window-band`, owner's approval, #112 comment, 2026-10-14) each channel with a
    window also gets `band_lo` = L/τ and `band_hi` = U/τ (U the whole-state cap where `hi_m` is),
    the spec's band in place of ±δ, and its `final_delta` becomes max(1 − band_lo, band_hi − 1),
    which is for reporting; a channel whose τ is not strictly inside the window gets neither.  Under
    `window_band` a channel is feasible exactly when τ is strictly inside [L, U], however small the
    headroom (`fit_delta`'s rounded symmetric δ may be None there)."""
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
            if d is not None and floor and c in floor:
                d = max(d, float(floor[c]))
        out["channels"][c] = {"k": k, "usd_m": total, "tau_m": tau, "free": free, "lo_m": lo,
                              "hi_m": hi, "whole_state_cap": whole, "final_delta": d}
        banded = window_band and window is not None and 0 < lo < tau < hi   # the unrounded bounds, not fit_delta's δ
        if banded:
            band_lo, band_hi = lo / tau, hi / tau
            out["channels"][c].update(band_lo=band_lo, band_hi=band_hi,
                                      final_delta=max(1.0 - band_lo, band_hi - 1.0))
        if window is None:
            out["infeasible"][c] = f"{c}: no dollar window"
        elif d is None and not banded:
            out["infeasible"][c] = (f"{c}: τ outside the dollar window ({tau:,.1f}M at K {k}, "
                                    f"window {lo:,.1f}-{hi:,.1f}M)")
    return out


WIDE_MAX = 0.35                 # a -wide point's floor stops here: a wider band is no territory


def wide_floor(replan_json: str, floor: dict) -> dict | None:
    """The δ floors a `-wide` point raises after a "no plan" replan: each channel whose master's
    smallest feasible δ (`replan.json`, rounded up to 1e-4) is above its final δ and its floor;
    None when there is none or one would pass `WIDE_MAX`."""
    try:
        with open(replan_json, encoding="utf-8") as fh:
            ch = json.load(fh)["channels"]
    except (OSError, ValueError, KeyError):
        return None
    out = {}
    for c, v in ch.items():
        sd = (v.get("smallest_delta") or {}).get("delta")
        if sd is not None and sd > v["final_delta"] + 1e-12 and sd > floor.get(c, 0.0):
            out[c] = math.ceil(sd * 1e4 - 1e-9) / 1e4
    if not out or any(x > WIDE_MAX for x in out.values()):
        return None
    return out


def window_keys(v: dict) -> dict:
    """{"band_lo": text, "band_hi": text} of a `plan_point` channel that has them, written with
    `repr` so the float is exact: the window is the owner's, a rounded key could move it."""
    return {k: repr(float(v[k])) for k in ("band_lo", "band_hi")} if "band_lo" in v else {}


def point_spec_text(base_text: str, pid: str, plan: dict) -> str:
    """The point's spec copy: the base TOML with each channel's K, its declared δ
    (`DECLARED_DELTA`, or the final δ when smaller) and its final δ (`replan.banned_text`), and
    the scenario named after the point.  A channel of `plan` with `band_lo`, `band_hi`
    (`plan_point(window_band=True)`) gets them written, exactly (`repr`), as its band."""
    ch = plan["channels"]
    body = _replan().banned_text(
        base_text, [], deltas={c: min(DECLARED_DELTA, v["final_delta"]) for c, v in ch.items()},
        final_deltas={c: v["final_delta"] for c, v in ch.items()},
        keys={c: {"k": str(v["k"]), **window_keys(v)} for c, v in ch.items()})
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


def label_of(m1: dict, rows: list, eligible: bool, why: list, gate_rc: int | None, verdict: dict | None = None,
             gate_tail: str = "") -> tuple:
    """(label, reason) of a point's last folder: M1 first (the final gate's exit code `gate_rc` and, for a gate
    that exited 1, the Manhattan adjudication `verdict` of its evidence, `sealed.manhattan_verdict`; else
    `m1` as `m1.json` holds it), then the exact dollar rows (`sealed.exact_rows`), then the scorer.  These are
    `sealed.label_point`'s, under this grid's names: `ineligible ($)` is its `outside band`, `eligible` its
    `passes`.  A gate that did not complete is `gate_rc` None: `fails M1`, never a pass."""
    label, reason = _sealed().label_point(m1, rows, [], False, eligible, why, gate_rc, gate_tail, verdict)
    return {"outside band": "ineligible ($)", "passes": "eligible"}.get(label, label), reason


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
def _group_alive(pgid: int) -> bool:
    """True while some process of the group `pgid` is left (the leader's exit does not end the group)."""
    try:
        os.killpg(pgid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


class hold_sigint:
    """Defer SIGINT (Ctrl-C) over the block: the signal is noted, and with `raise_after` a KeyboardInterrupt is
    raised once the block has ended and the old handler is back, so an interrupt never lands between a Popen and
    its registration or in the middle of ending a stage group.  Only the main thread gets signals; elsewhere the
    block is not held."""

    def __init__(self, raise_after: bool = True):
        self.raise_after, self.hit, self.old = raise_after, False, None

    def __enter__(self):
        if threading.current_thread() is threading.main_thread():
            self.old = signal.signal(signal.SIGINT, self._note)
        return self

    def _note(self, signum, frame):
        self.hit = True

    def __exit__(self, *exc):
        if self.old is not None:
            signal.signal(signal.SIGINT, self.old)
        if self.hit and self.raise_after and exc[0] is None:
            if callable(self.old):      # an enclosing `first_sigint` switches to holding later signals
                self.old(signal.SIGINT, None)
            raise KeyboardInterrupt
        return False


class first_sigint:
    """Over the block, the first SIGINT (Ctrl-C) raises KeyboardInterrupt as usual and later ones are only noted, so
    the cleanup that exception enters is not interrupted again before it holds SIGINT (`hold_sigint`) itself; a
    noted one is raised once the block ends without an exception.  A `hold_sigint` inside the block hands its
    deferred signal to this handler.  Only the main thread gets signals; elsewhere the block is not guarded."""

    def __init__(self):
        self.hit, self.old = False, None

    def __enter__(self):
        if threading.current_thread() is threading.main_thread():
            self.old = signal.signal(signal.SIGINT, self._first)
        return self

    def _first(self, signum, frame):
        signal.signal(signal.SIGINT, self._note)
        raise KeyboardInterrupt

    def _note(self, signum, frame):
        self.hit = True

    def __exit__(self, *exc):
        if self.old is not None:
            signal.signal(signal.SIGINT, self.old)
        if self.hit and exc[0] is None:
            raise KeyboardInterrupt
        return False


def _end(p) -> int:
    """`_end_now` with an interrupt held until the group is signalled and reaped, then raised; one arriving before
    the hold is in place retries it, so the group is ended however often Ctrl-C is pressed."""
    interrupt, rc = False, None
    while rc is None:
        try:
            with hold_sigint(raise_after=False) as held:
                rc = _end_now(p)
            interrupt = interrupt or held.hit
        except KeyboardInterrupt:
            interrupt = True
    if interrupt:
        raise KeyboardInterrupt
    return rc


def _end_now(p) -> int:
    """SIGINT to a stage's process group (its collectors stop their workers, `run.stop`), then SIGKILL to
    the group once `STOP_GRACE` has passed with a member left, whether or not the leader exited on the SIGINT
    (a member that ignores it, or a worker still stopping, outlives the leader); the leader's exit code."""
    end = time.time() + STOP_GRACE
    try:
        os.killpg(p.pid, signal.SIGINT)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        rc = p.wait(timeout=STOP_GRACE)
    except subprocess.TimeoutExpired:
        rc = None
    while _group_alive(p.pid) and time.time() < end:
        time.sleep(0.05)
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    return p.wait() if rc is None else rc


def child(cmd: list, log_path: str, cap: float, deadline: float, env: dict | None = None) -> dict:
    """One stage: `cmd` in its own process group, stdout and stderr to `log_path`, killed at
    `cap` seconds or at `deadline`; {rc, seconds, stop: None, "cap" or "deadline"}."""
    if HALT.is_set():
        raise Halted("the scheduler is unwinding")
    left = deadline - time.time()
    if left <= 0:
        return {"rc": None, "seconds": 0.0, "stop": "deadline"}
    timeout, stop, t0 = min(cap, left), None, time.time()
    with open(log_path, "w") as lg:
        p = None
        with first_sigint():    # a second Ctrl-C during the cleanup below is held until the stage is ended
            try:
                with hold_sigint():     # an interrupt after the Popen returns waits until the stage is in LIVE
                    p = subprocess.Popen(cmd, cwd=ROOT, stdout=lg, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                         env={**os.environ, **(env or {})}, start_new_session=True)
                    with LIVE_LOCK:
                        LIVE.add(p)
                if HALT.is_set():       # set after the check above: `stop_all` may have taken its snapshot before the add
                    raise Halted("the scheduler is unwinding")
                rc = p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                stop = "deadline" if left <= cap else "cap"
                rc = _end(p)
            except BaseException:       # an interrupt: the stage has its own session, so nothing else ends or reaps it
                if p is not None:
                    _end(p)
                raise
            finally:
                if p is not None:
                    with LIVE_LOCK:
                        LIVE.discard(p)
    return {"rc": rc, "seconds": round(time.time() - t0, 1), "stop": stop}


def stop_all() -> None:
    """End every stage still running (the launcher stopped or interrupted).  An interrupt meanwhile is held until
    every group is signalled and reaped (`hold_sigint`), then raised; one arriving before the hold is in place
    retries it."""
    done, interrupt = False, None
    while not done:
        try:
            with hold_sigint(raise_after=False) as held:
                with LIVE_LOCK:
                    procs = list(LIVE)
                for p in procs:
                    _end_now(p)
                done = True
            if held.hit:
                interrupt = KeyboardInterrupt()
        except KeyboardInterrupt as e:
            interrupt = e
    if interrupt is not None:
        raise interrupt


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

    def __init__(self, grid: Grid, root: str, host: str, extract: str, cells: dict,
                 window_band: bool = False):
        self.grid, self.root, self.host, self.extract, self.cells = grid, root, host, extract, cells
        self.window_band = window_band      # `--window-band`: each channel's band is its dollar window
        self.plans = os.path.join(root, "_plans")
        self.deadline = grid.deadline()
        self._masses = None             # (cell masses, rates) of the full dollar extract, `dollar_masses`
        self._masses_lock = threading.Lock()

    def dollar_masses(self) -> tuple:
        """(cell masses, dollar rates) of the full dollar extract, read once: the exact window of every point."""
        with self._masses_lock:
            if self._masses is None:
                sealed, ext = _sealed(), data.load(self.extract)
                self._masses = (sealed.ifa_index.extract_masses(ext), score.dollar_rates(ext))
            return self._masses

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
        floor = dict(pt.get("delta_floor") or {})
        spec = os.path.join(pdir, "spec.toml")
        for attempt in range(1 + (len(ks) if pt.get("wide_of") else 0)):
            plan = plan_point(ks, tdspec.load(base_path), self.cells, rule, floor, self.window_band)
            self.grid.update(pid, plan=plan)
            if plan["infeasible"]:
                return "infeasible", "; ".join(plan["infeasible"].values()), None, []
            if os.path.exists(spec) and finished(os.path.join(pdir, "draw")):
                break
            with open(base_path, encoding="utf-8") as fh:
                text = point_spec_text(fh.read(), pid, plan)
            base = os.path.join(pdir, "spec-base.toml")
            with open(base, "w", encoding="utf-8") as fh:
                fh.write(text)
            name = "replan" if attempt == 0 else f"replan{attempt + 1}"
            log = os.path.join(pdir, f"{name}.log")
            info = self.stage(pid, name, replan_cmd(base, pdir, self.plans, self.extract, plan), log,
                              PLAN_S * len(ks) + CAP_S["replan"])
            if info["stop"] == "cap":
                raise Stop("stopped", f"replan.py killed at its cap ({(PLAN_S * len(ks) + CAP_S['replan']) / 60:g} min)")
            if info["rc"] == 1 and "no plan" in _text(log):
                more = (wide_floor(os.path.join(pdir, "replan.json"), floor)
                        if pt.get("wide_of") and not self.window_band else None)   # a window is never widened
                if not more:
                    return "infeasible", _tail(log), None, []
                floor.update(more)
                self.grid.update(pid, delta_floor=floor)
                continue
            if info["rc"] != 0:
                raise Stop("error", f"replan.py exited {info['rc']}: {_tail(log)}")
            break
        else:
            return "infeasible", f"no plan after {len(ks) + 1} replans of a -wide point: {_tail(log)}", None, []
        src = self._draw(pid, pdir, spec, jobs)
        final = self._repair(pid, pdir, src, jobs, 1)
        if self.stage(pid, "gate_r1", gate_cmd(final), os.path.join(pdir, "gate_r1.log"),
                      CAP_S["gate"], GAP_ENV)["rc"] != 0:
            final = self._repair(pid, pdir, final, jobs, 2)
        for name in ("draw", "draw_retry", "r1", "r2"):
            folder = os.path.join(pdir, name)
            if os.path.exists(os.path.join(folder, "ledger.csv")):
                self.stage(pid, f"score_{name}", score_cmd(folder) + ["--extract", self.extract],
                           os.path.join(folder, "score.txt"),
                           CAP_S["post"], GAP_ENV)
                self.stage(pid, f"land_{name}", land_cmd(folder), os.path.join(pdir, f"land_{name}.log"),
                           CAP_S["post"])
        return self._label_final(pt, pdir, final)

    def _label_final(self, pt: dict, pdir: str, final: str) -> tuple:
        """(label, reason, final, new points) of the last folder `final`, after a gate stage there that is
        recorded (`gate-evidence.json` in the point's folder) and finished: killed at its cap it ends the point
        `stopped`, any exit other than 0 is judged by `label_of` (1 only with a Manhattan-only
        `sealed.manhattan_verdict`), and the dollars are the exact ones of the full extract."""
        pid, ks, sealed = pt["id"], pt["k"], _sealed()
        evidence = os.path.join(pdir, sealed.ifa_index.EVIDENCE)
        if os.path.exists(evidence):
            os.remove(evidence)         # a stale record is never the gate's of this folder
        log = os.path.join(pdir, "gate.log")
        info = self.stage(pid, "gate", sealed.gate_cmd(final, evidence), log, CAP_S["gate"], GAP_ENV)
        if info["stop"] == "cap":
            raise Stop("stopped", f"the final gate killed at its cap ({CAP_S['gate'] / 60:g} min)")
        gate_rc = info["rc"]
        for f in ("m1.json", "dollars.csv", "score.txt"):
            if not os.path.exists(os.path.join(final, f)):
                raise Stop("error", f"score.py wrote no {f} in {final}: {_tail(os.path.join(final, 'score.txt'))}")
        with open(os.path.join(final, "m1.json"), encoding="utf-8") as fh:
            m1 = json.load(fh)["gap_width"]
        try:
            rows = sealed.exact_rows(final, *self.dollar_masses())
        except (OSError, ValueError, KeyError) as e:
            raise Stop("error", f"exact dollar window of {final}: {type(e).__name__}: {e}")
        try:
            eligible, why = read_score(os.path.join(final, "score.txt"))
        except ValueError as e:
            raise Stop("error", f"score.py: {e}")
        label, reason = label_of(m1, rows, eligible, why, gate_rc, sealed.manhattan_verdict(final, gate_rc),
                                 _tail(log))
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
        if not failing or self.window_band:     # a window band is the owner's: a wider start is no remedy
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
    `deadline`; returns those never started.  An interrupt (or a `work` that raises) ends every live stage
    process group first (`HALT`, `stop_all`), then joins the workers; no stage starts meanwhile."""
    big = [p["id"] for p in todo if need(p) > slots]
    if big:
        raise ValueError(f"points needing more than {slots} slots: {big}")
    queue, running, free = list(todo), {}, slots
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=slots) as pool:
            try:
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
            except BaseException:   # before the pool's exit joins the workers: they wait on their stages
                HALT.set()
                for f in running:
                    f.cancel()
                stop_all()
                raise
    finally:
        HALT.clear()
    return queue


# ------------------------------------------------------------------------------ collect
def ssh_text(alias: str, command: str) -> str:
    """`command`'s stdout on the host `alias` (`ssh m2` on the LAN, `m2-ts` over Tailscale)."""
    got = subprocess.run(["ssh", "-o", "BatchMode=yes", alias, command], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL)
    if got.returncode:
        raise SystemExit(f"ssh {alias} {command!r} exited {got.returncode}: {got.stderr.strip()[-300:]}")
    return got.stdout


def read_json_at(where: str) -> dict:
    """A JSON file here, or at `host:path` over ssh."""
    if not os.path.exists(where) and ":" in where:
        alias, path = where.split(":", 1)
        return json.loads(ssh_text(alias, f"cat {shlex.quote(path)}"))
    with open(where, encoding="utf-8") as fh:
        return json.load(fh)


def parse_shasum(text: str) -> dict:
    """{path: sha256} from `shasum -a 256` lines, paths relative to the grid root."""
    out = {}
    for line in text.splitlines():
        if line.strip():
            sha, path = line.split("  ", 1)
            out[path[2:] if path.startswith("./") else path] = sha
    return out


def hash_tree(root: str, ids: list) -> dict:
    """{path: sha256} of every file under `root`/<id> for the `ids`, paths relative to `root`."""
    out = {}
    for pid in ids:
        for d, _, fs in os.walk(os.path.join(root, pid)):
            for name in fs:
                path = os.path.join(d, name)
                out[os.path.relpath(path, root).replace(os.sep, "/")] = _dollarize().sha256(path)
    return out


def compare_hashes(theirs: dict, ours: dict) -> list:
    """Each file of `theirs` missing here or with another sha256; files only here are not compared
    (a render made on m5 after an earlier collect)."""
    return [f"missing {p}" if p not in ours else f"differs {p}" for p in sorted(theirs) if ours.get(p) != theirs[p]]


def remote_unlabelled(remote: dict, host: str) -> list:
    return sorted(pid for pid, r in remote["points"].items() if r["host"] == host and r["label"] is None)


def check_remote(doc: dict, remote: dict, host: str) -> list:
    """The ids of `host`'s points in its GRID.json `remote`, after checking it is `host`'s grid
    of this one's name on this one's extract and that no point here is another host's."""
    if remote.get("grid") != doc.get("grid") or remote.get("host") != host:
        raise ValueError(f"the remote GRID.json is {remote.get('host')}'s {remote.get('grid')}, not {host}'s "
                         f"{doc.get('grid')}")
    if remote.get("extract_sha256") != doc.get("extract_sha256"):
        raise ValueError(f"{host} ran on extract {str(remote.get('extract_sha256'))[:12]}, this grid on "
                         f"{str(doc.get('extract_sha256'))[:12]}")
    ids = sorted(pid for pid, r in remote["points"].items() if r["host"] == host)
    clash = [pid for pid in ids if pid in doc["points"] and doc["points"][pid]["host"] != host]
    if clash:
        raise ValueError(f"points of another host here: {clash}")
    return ids


def merge_remote(doc: dict, remote: dict, host: str, note: dict) -> list:
    """`host`'s records from `remote` into `doc` in place of its "elsewhere" ones (its re-runs
    added), each with `collected` = `note`; the ids merged."""
    ids = check_remote(doc, remote, host)
    for pid in ids:
        doc["points"][pid] = {**remote["points"][pid], "collected": dict(note)}
    return ids


def cmd_collect(a) -> int:
    path = os.path.join(a.root, GRID_JSON)
    if not os.path.exists(path):
        raise SystemExit(f"no {path}: collect into the grid `run` wrote on this host")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    alias, rroot = a.ssh or a.src, a.remote_root or a.root
    remote = json.loads(ssh_text(alias, f"cat {shlex.quote(os.path.join(rroot, GRID_JSON))}"))
    try:
        ids = check_remote(doc, remote, a.src)
    except ValueError as e:
        raise SystemExit(f"{a.src}: {e}")
    open_ = remote_unlabelled(remote, a.src)
    if open_ and not a.anyway:
        raise SystemExit(f"{a.src}'s points without a label: {', '.join(open_)} (still running? --anyway "
                         "copies them as they are)")
    listing = ssh_text(alias, f"cd {shlex.quote(rroot)} && find {' '.join(map(shlex.quote, ids))} -type f "
                              "-print0 2>/dev/null | xargs -0 shasum -a 256")
    theirs = parse_shasum(listing)
    copied = sorted({p.split("/", 1)[0] for p in theirs})
    for pid in copied:
        rc = subprocess.run(["rsync", "-a", f"{alias}:{rroot}/{pid}/", os.path.join(a.root, pid) + "/"],
                            stdin=subprocess.DEVNULL).returncode
        if rc:
            raise SystemExit(f"rsync of {pid} from {alias} exited {rc}; nothing merged")
    bad = compare_hashes(theirs, hash_tree(a.root, copied))
    at = now()
    _write_json(os.path.join(a.root, f"collect_{a.src}.json"),
                {"from": a.src, "ssh": alias, "remote_root": rroot, "at": at, "points": ids, "copied": copied,
                 "files": len(theirs), "problems": bad, "sha256": theirs})
    if bad:
        print(f"{len(bad)} of {len(theirs)} files from {a.src} do not match; nothing merged:", *bad[:20], sep="\n  ")
        return 1
    _write_json(os.path.join(a.root, f"GRID.{a.src}.json"), remote)
    merged = merge_remote(doc, remote, a.src, {"from": a.src, "at": at, "files": len(theirs),
                                               "sha256_checked": True, "code": remote.get("code")})
    Grid(path, doc)
    print(f"collected {len(merged)} points of {a.src} ({len(copied)} folders, {len(theirs)} files, sha256 "
          f"checked) into {path}", flush=True)
    return 0


# ------------------------------------------------------------------------------ morning
def k_text(ks: dict) -> str:
    return ", ".join(f"{c} {ks[c]}" for c in CHANNELS if c in ks) + f" = {sum(ks.values())}"


def title_of(rec: dict, stage: str | None = None) -> str:
    """A map's one-line title: the point, its structure and K, and its label (`render.FAILS` for
    fails M1, so the renderer adds none); a stage folder other than the final one says so."""
    head = f"{rec['id']}: {rec['structure']}, K {k_text(rec['k'])}"
    if stage is not None:
        return f"{head} ({stage}, not the final folder)"
    label = _render().FAILS if rec["label"] == "fails M1" else rec["label"] or "no label"
    return f"{head}; {label}" + (f" (re-run of {rec['parent']})" if rec.get("parent") else "")


def fac_file(root: str) -> str:
    """`<root>/fac_usd.json`: $M per $M, 1 for every fine channel with an owner total (D14)."""
    path = os.path.join(root, "fac_usd.json")
    _write_json(path, {"fac": {f: 1.0 for f in sorted(score.DOLLARS)},
                       "note": "the overnight grid's ledgers hold $M (tools/exp/contig/dollarize.py)"})
    return path


def render_jobs(root: str, recs: list) -> list:
    """(folder, title) for every stage folder with a ledger, the final one titled with the label."""
    out = []
    for rec in recs:
        final = rec.get("final") and os.path.join(root, rec["final"])
        for name in STAGES:
            folder = os.path.join(root, rec["id"], name)
            if os.path.exists(os.path.join(folder, "ledger.csv")):
                out.append((folder, title_of(rec) if folder == final else title_of(rec, name)))
    return out


def render_one(folder: str, title: str, fac: str) -> tuple:
    """(folder, exit code) of `render.py` on it, under the G3 gate, logged to its `render.log`."""
    cmd = [sys.executable, "-u", os.path.join(ROOT, "tools", "maps", "render.py"), folder, "--label", title,
           "--fac", fac, "--if-stale"]
    return folder, child(cmd, os.path.join(folder, "render.log"), RENDER_S, time.time() + RENDER_S + 60, GAP_ENV)["rc"]


LOOKS = {"splits": (r"^channel-state splits: (\d+):", int),           # score.report's lines
         "defects": (r"^defects: (\S+) =", float),
         "largest_extent_km": (r"^shape: extent ([\d,.]+) km", lambda x: float(x.replace(",", ""))),
         "states_per_district": (r"^shape: extent [\d,.]+ km, (\d+) states per district", int),
         "worst_dev": (r"^balance: worst ([\d.]+)%", lambda x: float(x) / 100),
         "mean_dev": (r"^balance: worst [\d.]+%, mean ([\d.]+)%", lambda x: float(x) / 100)}


def read_looks(path: str) -> dict | None:
    """`score.rank_key`'s fields from a `score.py` report, or None without one."""
    text, out = _text(path), {}
    for k, (pat, conv) in LOOKS.items():
        m = re.search(pat, text, re.M)
        if m is None:
            return None
        out[k] = conv(m.group(1))
    return out


def worst_usd(rows: list) -> tuple | None:
    """(district, $M, deviation) of the district farthest from its channel's mean $ per district."""
    by, best = collections.defaultdict(list), None
    for r in rows:
        by[r["channel"]].append(r)
    for _, rs in sorted(by.items()):
        tau = math.fsum(r["usd"] for r in rs) / len(rs)
        for r in rs:
            dev = (r["usd"] - tau) / tau if tau else 0.0
            if best is None or abs(dev) > abs(best[2]):
                best = (r["district"], r["usd"], dev)
    return best


def folder_metrics(folder: str | None) -> dict:
    """A final folder's score report fields, dollar rows, `m1.json` and `land.csv` rows (None where
    absent)."""
    def opt(name, read):
        path = folder and os.path.join(folder, name)
        return read(path) if path and os.path.exists(path) else None

    def land(path):
        with open(path, newline="") as fh:
            return list(csv.DictReader(fh))

    def m1(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"looks": opt("score.txt", read_looks), "dollars": opt("dollars.csv", read_dollars),
            "m1": opt("m1.json", m1), "land": opt("land.csv", land)}


def point_row(root: str, rec: dict) -> dict:
    final = os.path.join(root, rec["final"]) if rec.get("final") else None
    m = folder_metrics(final)
    return {"id": rec["id"], "rec": rec, "label": rec["label"] or "error", "final": rec.get("final"),
            "reason": rec["reason"] or ("" if rec["label"] else f"no label (status {rec['status']})"),
            "m": m, "key": score.rank_key(m["looks"]) if m["looks"] else None}


def pair_of(pid: str) -> str | None:
    m = re.match(r"^(.*)-(bal|filight)$", pid)
    return m and m.group(1)


def morning_order(rows: list) -> list:
    """The settled order: by label (`LABELS`, unknown last), within one by the scorer's
    `rank_key` (rows without a report after), then id; a balanced point's FI-light partner
    (`<x>-bal`, `<x>-filight`) moved beside the first of the two when both carry one label."""
    at = {x: i for i, x in enumerate(LABELS)}
    rows = sorted(rows, key=lambda r: (at.get(r["label"], len(LABELS)), r["key"] is None, r["key"] or (), r["id"]))
    out, seen = [], set()
    for r in rows:
        if r["id"] in seen:
            continue
        out.append(r)
        seen.add(r["id"])
        p = pair_of(r["id"])
        for s in rows:
            if p and s["id"] not in seen and pair_of(s["id"]) == p and s["label"] == r["label"]:
                out.append(s)
                seen.add(s["id"])
    return out


def el_paso(flip: dict) -> bool:
    items = flip["strict"] + flip["gap_width"]
    return bool(items) and all(any(c in i for c in EL_PASO) for i in items)


def eye_items(pid: str, m: dict) -> list:
    """G3's flips but El Paso's, the whole-state allowances and the split groups beyond R of a
    point's final folder."""
    out = []
    for f in (m["m1"] or {}).get("flips", []):
        if not el_paso(f):
            way = "strict only" if f["strict"] else "across coverage gaps only"
            out.append(f"{pid}: M1 flip {f['district']}, a neck {way}: {(f['strict'] or f['gap_width'])[0]}")
    out += [f"{pid}: {r['district']} {r['usd']:,.1f}M on the whole-state allowance (up to {r['cap']:,.1f}M)"
            for r in m["dollars"] or () if r["allowance"]]
    out += [f"{pid}: {r['channel']} {r['state']} in-state land ratio {r['ratio']} beyond R = {LAND_RATIO:g} "
            f"({r['largest']} {r['largest_km2']} km², {r['smallest']} {r['smallest_km2']} km²)"
            for r in m["land"] or () if r["over"] == "1"]
    return out


def _cells(r: dict) -> list:
    m, final = r["m"], r["final"]
    looks, w = m["looks"], worst_usd(m["dollars"] or [])
    ratios = [float(x["ratio"]) for x in m["land"] or () if x["ratio"]]
    over = sum(x["over"] == "1" for x in m["land"] or ())
    m1 = m["m1"]
    return [r["id"], r["rec"]["structure"], k_text(r["rec"]["k"]),
            "—" if looks is None else str(looks["splits"]), "—" if looks is None else f"{looks['defects']:g}",
            "—" if w is None else f"{w[0]} {100 * w[2]:+.1f}% ({w[1]:,.1f}M)",
            "—" if m1 is None else f"{m1['gap_width']['status']} / {m1['strict']['status']}"
            + (f", {len(m1['flips'])} flips" if m1["flips"] else ""),
            "—" if not ratios else f"{max(ratios):.1f}" + (f" ({over} > R)" if over else ""),
            f"**{r['label']}**",
            "—" if not final else f"[folder]({final}/) · [map]({final}/summary.png) · [score]({final}/score.txt)"]


def morning_md(doc: dict, rows: list, eye: list, at: str) -> str:
    counts = collections.Counter(r["label"] for r in rows)
    codes = sorted({json.dumps(c, sort_keys=True) for c in [doc.get("code")]
                    + [r["rec"].get("collected", {}).get("code") for r in rows] if c})
    md = [f"# MORNING: {GRID_NAME}", "",
          f"Built by `tools/exp/contig/overnight.py morning` from `GRID.json` at {at}.  Extract "
          f"`{os.path.basename(doc['extract'])}` (sha256 `{doc['extract_sha256'][:12]}`); code "
          + ", ".join(f"`{json.loads(c)['commit'][:7]}`" + (" (dirty)" if json.loads(c)["dirty"] else "") for c in codes)
          + f"; stop at {doc['deadline']}.  `MORNING.pdf` opens with this index.", "",
          f"{len(rows)} points: " + ", ".join(f"{counts[x]} {x}" for x in LABELS if counts[x]) + ".", ""]
    md += index_md(index_rows(rows)) + ["", "## Assumptions (owner decisions open)", ""]
    md += [f"- {x}" for x in doc["assumptions"]] + [
          "", "## Points", "",
          "Eligible first by the scorer's rank key (splits, defects, extent, states per district, worst and mean "
          "deviation), then fails M1, ineligible ($), ineligible, infeasible, stopped and error; a balanced point "
          "beside its FI-light partner when both carry one label.  Worst $: the district farthest from its "
          "channel's mean $ per district.  M1: across coverage gaps (the gate) / strict.  Land: the largest "
          f"in-state ratio, groups beyond R = {LAND_RATIO:g}.  `MORNING.pdf` has one page per point in this order.",
          "", "| # | id | structure | K | splits | defects | worst $ | M1 gaps / strict | land | label | links |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {i} | " + " | ".join(_cells(r)) + " |" for i, r in enumerate(rows, 1)]
    md += ["", "## Reasons", ""] + ([f"- **{r['id']}** ({r['label']}): {r['reason']}" for r in rows if r["reason"]]
                                    or ["- none"])
    md += ["", "## Needs your eye", ""] + ([f"- {x}" for x in eye] or ["- nothing"])
    return "\n".join(md) + "\n"


MEANING = {                     # structure -> its channel footprint, for the index page
    "ne_plains": "WIFI = 15 NE+plains states whole; N/WH/FI rest",
    "west8": "WIFI = 8 western states whole; N/WH/FI elsewhere",
    "nw49": "N over all 49 units; WIFI (WH+FI) over all 49",
    "nw34": "N over 34 units; WIFI over 49 (all 5 in NE+plains)",
    "w1": "WIFI only: all 5 fine channels over 49 units; no N",
}
SHORT = {"national": "N", "WH": "WH", "FI": "FI", "WIFI": "WIFI"}


def target_m(c: str) -> float:
    """A channel's $M per district target: `score.TARGET`, else its window's midpoint (WIFI)."""
    if c in score.TARGET:
        return score.TARGET[c] / 1e6
    lo, hi = score.WINDOWS[c]
    return (lo + hi) / 2e6


def _dev(x: float | None, t: float) -> float | None:
    return None if x is None else (x - t) / t


def index_rows(rows: list) -> list:
    """The index page's rows, one per point in `rows`' order (numbered as MORNING.pdf's points):
    K, the channel structure and per channel the target, window, whole-state cap and, from the
    final folder's dollars, the average, min and max $M per district with their deviation from
    the target and the districts outside the window; a point without a final folder carries its
    planned τ (GRID plan's usd_m / k) instead, `planned` set."""
    out = []
    for n, r in enumerate(rows, 1):
        rec, dollars = r["rec"], r["m"]["dollars"] if r["final"] else None
        plan = ((rec.get("plan") or {}).get("channels") or {})
        chans = []
        for c in (c for c in CHANNELS if c in rec["k"]):
            t, (lo, hi), p = target_m(c), score.WINDOWS[c], plan.get(c) or {}
            ds = [d for d in dollars or () if d["channel"] == c and d["usd"] is not None]
            cap = p.get("whole_state_cap") or any(d["cap"] for d in ds)
            row = {"channel": c, "k": rec["k"][c], "target_m": t, "lo_m": lo / 1e6, "hi_m": hi / 1e6,
                   "cap_m": score.WHOLE_STATE_CAP[c] / 1e6 if cap and c in score.WHOLE_STATE_CAP else None,
                   "planned": dollars is None, "avg_m": None, "min_m": None, "max_m": None, "out": None}
            if ds:
                us = [d["usd"] for d in ds]
                row.update(avg_m=math.fsum(us) / len(us), min_m=min(us), max_m=max(us),
                           out=sum(not d["ok"] for d in ds))
            elif dollars is None and p.get("usd_m") is not None:
                row["avg_m"] = p["usd_m"] / p["k"]
            for x in ("avg", "min", "max"):
                row[f"{x}_dev"] = _dev(row[f"{x}_m"], t)
            chans.append(row)
        out.append({"n": n, "id": rec["id"], "structure": rec["structure"],
                    "meaning": MEANING.get(rec["structure"], ""), "label": r["label"],
                    "reason": r["reason"], "drawn": dollars is not None, "k_total": sum(rec["k"].values()),
                    "k_text": " · ".join(f"{SHORT[c['channel']]} {c['k']}" for c in chans), "channels": chans})
    return out


INDEX_LEGEND = ("N: national; target: $M per district (TARGET; WIFI has none, so its window's midpoint 1,000M); window: the "
                "dollar gate lo-hi (cap: WIFI's whole-state allowance); deviation: (x - target) / target; "
                "out: districts outside the window; avg/min/max from the final folder's dollars.csv, "
                "or the planned τ (usd_m / K) when nothing was drawn")


def _m(x: float | None, dev: float | None) -> str:
    return "—" if x is None else f"{x:,.0f} ({100 * dev:+.1f}%)"


def _window(c: dict) -> str:
    return f"{c['lo_m']:,.0f}-{c['hi_m']:,.0f}" + (f" cap {c['cap_m']:,.0f}" if c["cap_m"] else "")


def _status(x: dict) -> str:
    return x["label"] + ("" if x["drawn"] else "; planned τ, not drawn")


def index_md(index: list) -> list:
    """The index as MORNING.md lines: one table row per channel, the point's cells on its first."""
    md = ["## Index", "", INDEX_LEGEND[0].upper() + INDEX_LEGEND[1:] + ".", "",
          "| # | id | structure | label | K | channel | target $M | window $M | avg $M | min $M | max $M | out |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in index:
        head = [f"**{x['n']}**", x["id"], f"{x['structure']}: {x['meaning']}", _status(x),
                f"{x['k_total']} = {x['k_text']}"]
        for i, c in enumerate(x["channels"]):
            avg = ("τ " if c["planned"] else "") + _m(c["avg_m"], c["avg_dev"])
            md.append("| " + " | ".join((head if i == 0 else [""] * 5) + [
                f"{c['channel']} {c['k']}", f"{c['target_m']:,.0f}", _window(c), avg, _m(c["min_m"], c["min_dev"]),
                _m(c["max_m"], c["max_dev"]), "—" if c["out"] is None else str(c["out"])]) + " |")
    return md


INDEX_COLS = (("#  point · K · structure · label", 63), ("chan", 6), ("K", 4), ("target", 8), ("window", 21),
              ("avg (dev)", 18), ("min (dev)", 16), ("max (dev)", 16), ("out", 4))


def _index_lines(x: dict) -> list:
    """A point's block: the point's lines down the first column, one channel per line beside them."""
    w = INDEX_COLS[0][1] - 3
    left = [f"{x['n']:>2} {x['id']}", f"   K {x['k_total']} = {x['k_text']}", f"   {x['structure']}: {x['meaning']}",
            f"   {_status(x)}"] + ([f"   {x['reason']}"] if not x["drawn"] and x["reason"] else [])
    left = [s if len(s) <= w else s[:w - 1] + "…" for s in left]
    out = []
    for i in range(max(len(left), len(x["channels"]))):
        cells = [left[i] if i < len(left) else ""]
        if i < len(x["channels"]):
            c = x["channels"][i]
            cells += [SHORT[c["channel"]], str(c["k"]), f"{c['target_m']:,.0f}", _window(c),
                      ("τ " if c["planned"] else "") + _m(c["avg_m"], c["avg_dev"]), _m(c["min_m"], c["min_dev"]),
                      _m(c["max_m"], c["max_dev"]), "—" if c["out"] is None else str(c["out"])]
        out.append(cells)
    return out


def index_pages(index: list, size: tuple = PDF_PAGE, title: str = f"MORNING index: {GRID_NAME}") -> list:
    """The index as landscape PIL pages of `size`: the title, the legend and a monospace table,
    one shaded block per point, split between pages at block boundaries."""
    from matplotlib import font_manager
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    chars = sum(w for _, w in INDEX_COLS)
    mono = font_manager.findfont("DejaVu Sans Mono")
    px = max(12, int((W - 120) / chars / 0.602))     # DejaVu Sans Mono's advance is 0.602 em
    font, bold = ImageFont.truetype(mono, px), ImageFont.truetype(mono, int(px * 1.4))
    small = ImageFont.truetype(font_manager.findfont("DejaVu Sans"), int(px * 0.8))
    lh, cw = int(px * 1.25), px * 0.602
    xs = [60 + cw * sum(w for _, w in INDEX_COLS[:i]) for i in range(len(INDEX_COLS))]
    blocks = [_index_lines(x) for x in index]
    legend = textwrap.wrap(INDEX_LEGEND, int((W - 120) / (px * 0.8 * 0.5)))
    pages, i = [], 0
    while i < len(blocks) or not pages:
        im = Image.new("RGB", size, "white")
        d = ImageDraw.Draw(im)
        y = 40
        d.text((60, y), title + (f"  (page {len(pages) + 1})" if len(pages) else ""), fill="black", font=bold)
        y += int(px * 1.9)
        for s in legend:
            d.text((60, y), s, fill="#333333", font=small)
            y += int(px * 1.05)
        y += lh // 3
        for (name, _), x in zip(INDEX_COLS, xs):
            d.text((x, y), name, fill="black", font=font)
        y += lh
        d.line((60, y - 4, W - 60, y - 4), fill="black", width=2)
        while i < len(blocks) and (y + lh * len(blocks[i]) <= H - 40 or y < H // 3):
            if i % 2 == 0:
                d.rectangle((50, y, W - 50, y + lh * len(blocks[i])), fill="#eef2f7")
            for cells in blocks[i]:
                for j, (s, x) in enumerate(zip(cells, xs)):
                    d.text((x, y + 2), s, fill="black" if j else "#1a1a1a", font=font)
                y += lh
            i += 1
        pages.append(im)
    return pages


def map_png(final: str) -> str:
    """The final folder's page in MORNING.pdf: the ZIP pages' state summary, else `summary.png`."""
    zp = os.path.join(final, "zip_summary.png")
    return zp if os.path.exists(zp) else os.path.join(final, "summary.png")


def map_pages(final: str) -> list:
    """A final folder's pages in MORNING.pdf: the ZIP pages (state summary, then each planning
    channel's district map, `CHANNELS` order), else `map_png`'s one page."""
    chans = [os.path.join(final, f"zip_{c}.png") for c in CHANNELS + ("IFA",)]
    got = [p for p in [os.path.join(final, "zip_summary.png")] + chans if os.path.exists(p)]
    return got or [map_png(final)]


def page_size(pages: list) -> tuple:
    """The first map page's size, else `PDF_PAGE`."""
    from PIL import Image
    return next((Image.open(p).size for p, _ in pages if p and os.path.exists(p)), PDF_PAGE)


def morning_pdf(path: str, pages: list, front: tuple = ()) -> None:
    """A raster PDF (`tools/shortlist/build.py`'s `deck`): one page per (png or None, text), a
    page without a map showing its text; `front` (PIL images, the index) goes first."""
    from PIL import Image, ImageDraw, ImageFont
    size = page_size(pages)
    font, imgs = ImageFont.load_default(size=40), [im.convert("RGB") for im in front]
    for png, text in pages:
        if png and os.path.exists(png):
            imgs.append(Image.open(png).convert("RGB"))
            continue
        im = Image.new("RGB", size, "white")
        body = "\n".join(textwrap.fill(x, 100) for x in text.splitlines())
        ImageDraw.Draw(im).multiline_text((60, 60), body, fill="black", font=font, spacing=12)
        imgs.append(im)
    imgs[0].save(path, save_all=True, append_images=imgs[1:], resolution=100)


def cmd_morning(a) -> int:
    with open(os.path.join(a.root, GRID_JSON), encoding="utf-8") as fh:
        doc = json.load(fh)
    recs = [doc["points"][pid] for pid in sorted(doc["points"])]
    eye = []
    if not a.no_render:
        fac = fac_file(a.root)
        _render()
        with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
            done = list(pool.map(lambda j: render_one(*j, fac), render_jobs(a.root, recs)))
        eye += [f"render failed (exit {rc}): {os.path.relpath(f, a.root)}/render.log" for f, rc in done if rc != 0]
    rows = morning_order([point_row(a.root, rec) for rec in recs])
    for r in rows:
        eye += eye_items(r["id"], r["m"])
        if r["rec"]["label"] is None:
            eye.append(f"{r['id']}: {r['reason']}, counted as an error")
    md = os.path.join(a.root, "MORNING.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(morning_md(doc, rows, eye, now()))
    pdf = os.path.join(a.root, "MORNING.pdf")
    pages = [(png, title_of(r["rec"]) + (f"\n{r['reason']}" if r["reason"] else "") + "\nno map")
             for r in rows for png in (map_pages(os.path.join(a.root, r["final"])) if r["final"] else [None])]
    front = index_pages(index_rows(rows), page_size(pages))
    morning_pdf(pdf, pages, front)
    print(f"{md}\n{pdf}\n{len(rows)} points, {len(front)} index pages, {len(eye)} items need your eye", flush=True)
    return 0


# ------------------------------------------------------------------------------ smoke
def peak_rss(maxrss: int, platform: str = sys.platform) -> int:
    """`ru_maxrss` in bytes: bytes on macOS, KiB on Linux."""
    return maxrss if platform == "darwin" else maxrss * 1024


def suggest_slots(host: str, peak: int) -> int:
    """D12: `MEM_GIB`[host] over the smoke's peak RSS, at most `SLOTS`[host]; `SLOTS` where no
    budget is set."""
    if host not in MEM_GIB or peak <= 0:
        return SLOTS[host]
    return max(1, min(SLOTS[host], int(MEM_GIB[host] * 2 ** 30 // peak)))


def this_host() -> str | None:
    name = socket.gethostname().split(".")[0]
    return next((h for h in sorted(SLOTS) if name.startswith(h)), None)


SMOKE_SAME = ("point", "extract_sha256", "ledger_sha256", "statuses")


def compare_smoke(a: dict, b: dict) -> list:
    """What differs between two `smoke.json`: the point, extract, ledger, statuses or code."""
    out = [f"{k}: {a.get(k)!r} vs {b.get(k)!r}" for k in SMOKE_SAME if a.get(k) != b.get(k)]
    ca, cb = ((c["code"]["commit"], c["code"]["diff_sha256"]) for c in (a, b))
    if ca != cb:
        out.append(f"code: {ca} vs {cb}")
    return out


def cmd_smoke(a) -> int:
    if a.compare:
        x, y = map(read_json_at, a.compare)
        diff = compare_smoke(x, y)
        print(*(diff or [f"match: {x['point']} ledger {x['ledger_sha256'][:12]} on {x['host']} and {y['host']}; "
                         f"peak RSS {x['peak_rss_bytes'] / 2 ** 30:.2f} / {y['peak_rss_bytes'] / 2 ** 30:.2f} GiB"]),
              sep="\n")
        return 1 if diff else 0
    if not a.out:
        raise SystemExit("smoke needs --out DIR (or --compare A B)")
    host = a.host or this_host()
    if host is None:
        raise SystemExit("cannot tell the host from the hostname; pass --host")
    pt = {p["id"]: p for p in POINTS}.get(a.point)
    if pt is None:
        raise SystemExit(f"no point {a.point}")
    if _dollarize().rates_of(a.extract) is None:
        raise SystemExit(f"{a.extract} is not a dollar extract (tools/exp/contig/dollarize.py)")
    if os.path.exists(a.out) and os.listdir(a.out):
        raise SystemExit(f"{a.out} is not empty")
    os.makedirs(a.out, exist_ok=True)
    base_path, rule = STRUCTURES[pt["structure"]]
    base_path = os.path.join(ROOT, base_path)
    plan = plan_point(pt["k"], tdspec.load(base_path), state_cells(a.extract), rule, window_band=a.window_band)
    if plan["infeasible"]:
        raise SystemExit("; ".join(plan["infeasible"].values()))
    base, spec, plans = (os.path.join(a.out, x) for x in ("spec-base.toml", "spec.toml", "_plans"))
    with open(base_path, encoding="utf-8") as fh:
        text = point_spec_text(fh.read(), pt["id"], plan)
    with open(base, "w", encoding="utf-8") as fh:
        fh.write(text)
    deadline = time.time() + 3600.0 * a.hours
    rp = child(replan_cmd(base, a.out, plans, a.extract, plan), os.path.join(a.out, "replan.log"),
               PLAN_S * len(pt["k"]) + CAP_S["replan"], deadline)
    if rp["rc"] != 0:
        raise SystemExit(f"replan.py: {rp}, {_tail(os.path.join(a.out, 'replan.log'))}")
    out = os.path.join(a.out, "draw")
    dr = child(draw_cmd(spec, out, plans, a.extract, slots_of(pt)), os.path.join(a.out, "draw.log"),
               DRAW_S + CAP_S["draw"], deadline)
    ledger = os.path.join(out, "ledger.csv")
    contig = read_json_at(os.path.join(out, "contig.json")) if os.path.exists(os.path.join(out, "contig.json")) else {}
    peak = peak_rss(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    doc = {"point": pt["id"], "host": host, "at": now(), "code": _sweep().code_state(), "extract": a.extract,
           "extract_sha256": _dollarize().sha256(a.extract),
           "ledger_sha256": _dollarize().sha256(ledger) if os.path.exists(ledger) else None,
           "statuses": {c: ch.get("status") for c, ch in sorted(contig.get("channels", {}).items())},
           "stages": {"replan": rp, "draw": dr}, "peak_rss_bytes": peak, "slots": suggest_slots(host, peak)}
    _write_json(os.path.join(a.out, "smoke.json"), doc)
    print(f"smoke {pt['id']} on {host}: ledger {str(doc['ledger_sha256'])[:12]}, {doc['statuses']}, "
          f"{rp['seconds'] + dr['seconds']:,.0f} s, peak RSS {peak / 2 ** 30:.2f} GiB, slots {doc['slots']}", flush=True)
    return 0 if doc["ledger_sha256"] and dr["rc"] == 0 else 1


# ------------------------------------------------------------------------------ the CLI
def check_window_band(path: str, doc: dict, window_band: bool) -> None:
    """A resume keeps the band mode the grid was written in: `doc["window_band"]` (absent: off,
    a grid from before the flag); a run that asks for the other mode is refused, since its
    finished stage folders were built under the first."""
    saved = bool(doc.get("window_band", False))
    if saved != window_band:
        raise SystemExit(f"{path} was written {'with' if saved else 'without'} --window-band, this run is "
                         f"{'with' if window_band else 'without'}; use a new --root")


def open_grid(root: str, host: str, extract: str, hours: float, window_band: bool = False) -> Grid:
    """GRID.json at `root`: the one there (a resume, its stop and its band mode kept), or a new one
    listing every point."""
    path = os.path.join(root, GRID_JSON)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("host") != host:
            raise SystemExit(f"{path} is {doc.get('host')}'s grid, not {host}'s")
        check_window_band(path, doc, window_band)
        return Grid(path, doc)
    doc = grid_doc(host, extract, _dollarize().sha256(extract), time.time() + 3600.0 * hours,
                   _sweep().code_state())
    doc["limits"]["hours"] = hours
    doc["window_band"] = window_band
    return Grid(path, doc)


def cmd_run(a) -> int:
    if _dollarize().rates_of(a.extract) is None:
        raise SystemExit(f"{a.extract} is not a dollar extract (tools/exp/contig/dollarize.py)")
    os.makedirs(a.root, exist_ok=True)
    grid = open_grid(a.root, a.host, a.extract, a.hours, a.window_band)
    pts = [grid.get(pid) for pid in grid.doc["points"]]
    todo = order([p for p in pts if p["host"] == a.host and p["label"] is None
                  and (not a.only or p["id"] in a.only)])
    runner = Runner(grid, a.root, a.host, a.extract, state_cells(a.extract) if todo else {}, a.window_band)
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
    r.add_argument("--window-band", action="store_true",
                   help="each channel's band is its dollar window [L, U] (band_lo, band_hi), not ±δ "
                        "(owner, #112 comment, 2026-10-14); off keeps the 10-13 grid reproducible")
    r.set_defaults(func=cmd_run)
    c = sub.add_parser("collect", help="copy another host's points here, sha256 checked, and merge GRID.json")
    c.add_argument("--from", dest="src", required=True, choices=sorted(SLOTS))
    c.add_argument("--ssh", default=None, help="the ssh alias (default the host's name; m2-ts over Tailscale)")
    c.add_argument("--remote-root", default=None, help="the grid there (default --root)")
    c.add_argument("--root", default=GRID_ROOT)
    c.add_argument("--anyway", action="store_true", help="copy points that have no label yet")
    c.set_defaults(func=cmd_collect)
    m = sub.add_parser("morning", help="render, then write MORNING.md and MORNING.pdf")
    m.add_argument("--root", default=GRID_ROOT)
    m.add_argument("--no-render", action="store_true", help="use the maps already there")
    m.add_argument("--jobs", type=int, default=4, help="renders at once")
    m.set_defaults(func=cmd_morning)
    s = sub.add_parser("smoke", help="one point's replan and draw, its ledger sha256 and peak RSS")
    s.add_argument("--point", default="ne-48-bal")
    s.add_argument("--out", default=None, help="an empty folder")
    s.add_argument("--host", default=None, choices=sorted(SLOTS), help="default from the hostname")
    s.add_argument("--extract", default=EXTRACT)
    s.add_argument("--hours", type=float, default=2.0, help="the smoke's own stop")
    s.add_argument("--window-band", action="store_true", help="as `run --window-band`")
    s.add_argument("--compare", nargs=2, default=None, metavar=("A", "B"),
                   help="two smoke.json (host:path over ssh): exit 0 when they match")
    s.set_defaults(func=cmd_smoke)
    return ap


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    if getattr(a, "slots", 0) is None:
        a.slots = SLOTS[a.host]
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
