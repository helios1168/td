---
date: 2026-10-13T04:04:35-0500
author: Nicolas Lee
commit: 5939e04
branch: m5-studio/national-overnight
repository: td-national-overnight
topic: "Main-map overnight grid: dollar-scaled extract, per-district dollar gate, gap-width audit, #133 land term and the 21-point launcher"
tags: [plan, main-map, WIFI, K-grid, dollars, gap-width, land-balance, launcher, overnight, score, audit, draw]
status: ready
parent: ".rpiv/artifacts/designs/2026-10-13_01-09-34_main-map-overnight-grid.md"
phase_count: 7
phases:
  - { n: 1, title: "Dollar-scaled extract + export_long reversal", files: [tools/exp/contig/dollarize.py, tools/exp/contig/export_long.py, tests/test_dollarize.py, docs/CODE_MAP.md], depends_on: [] }
  - { n: 2, title: "Per-district dollar gate", files: [tools/looks/score.py, tests/test_looks_score.py], depends_on: [1] }
  - { n: 3, title: "Gap-width audit", files: [td/audit.py, tests/test_neck_gapwidth.py, tools/looks/score.py], depends_on: [2] }
  - { n: 4, title: "#133 land term + land.csv", files: [tools/exp/contig/draw.py, tools/exp/contig/run.py, tools/exp/contig/land.py, tests/test_land.py], depends_on: [1] }
  - { n: 5, title: "Grid launcher core", files: [tools/exp/contig/overnight.py, tests/test_overnight.py], depends_on: [1, 2, 3, 4] }
  - { n: 6, title: "Collect + morning + smoke", files: [tools/exp/contig/overnight.py, tests/test_overnight.py, docs/CODE_MAP.md], depends_on: [5] }
  - { n: 7, title: "Pre-launch gates", files: [scenarios/main_ne_plains.toml, scenarios/main_west8.toml, scenarios/main_nw49.toml, scenarios/main_nw34.toml, scenarios/main_w1.toml, tests/test_overnight.py], depends_on: [6] }
last_updated: 2026-10-13T04:04:35-0500
last_updated_by: Nicolas Lee
---

# Main-Map Overnight Grid Implementation Plan

## Overview

Implements the design `.rpiv/artifacts/designs/2026-10-13_01-09-34_main-map-overnight-grid.md`. Overnight, the support master → draw → repair chain of `set125.sh` runs over 21 main-map points (five WIFI structures × K totals 48–52), unsealed on the full polygon graph. Masses are in $M via a derived extract, so every stage balances dollars with no band-row change (G5/B1). The scorer gates every main-map district against its channel's dollar window. The scouts' gap-width prototype (`d312834`) lands with both M1 verdicts reported. The draw gains a soft #133 land-balance penalty at R = 10. A Python launcher (`tools/exp/contig/overnight.py`) runs the grid on m5 + m2 and writes `GRID.json`, `MORNING.md` and `MORNING.pdf`.

The seven phases are the design's seven slices, one to one. Code comes from the design's `## Architecture`. Success Criteria are copied verbatim from its `## Slices`. Two Architecture fences cover more than one slice: `tools/looks/score.py` covers Slices 2 and 3, and `tools/exp/contig/overnight.py` / `tests/test_overnight.py` cover Slices 5–7. They are split along the boundaries the design names (see Developer Context), so each phase carries only its own code and applies on top of the phases before it.

## Desired End State

```bash
# once per Studio, before launch (the extract stays gitignored at the hub root)
"$TD_PY" tools/exp/contig/dollarize.py "$TD_REPO/instance_descaled.json.gz" "$TD_REPO/instance_descaled_usd.json.gz"
git -C "$TD_REPO" check-ignore -q instance_descaled_usd.json.gz && echo ignored

# pre-launch smoke on each Studio (same spec, same commit), then compare
"$TD_PY" -u tools/exp/contig/overnight.py smoke --point ne-48-bal --out /tmp/td-smoke-$(hostname -s)

# launch: m5 runs its 15 points, m2 its 6 (west8), 8 h hard stop
"$TD_PY" -u tools/exp/contig/overnight.py run --host m5 &        # on m5
ssh m2 '... "$TD_PY" -u tools/exp/contig/overnight.py run --host m2' &

# morning, on m5
"$TD_PY" tools/exp/contig/overnight.py collect --from m2          # rsync + sha256 check
"$TD_PY" tools/exp/contig/overnight.py morning                    # MORNING.md + MORNING.pdf
```
```python
# a run folder's gate in one call
score = load("tools/looks/score.py")
s = score.score(run_dir)                       # eligible only if every district is in its $ window
rows = score.dollar_gate(ledger, districts, rates)  # one row per districts.csv row: usd, lo, hi, cap, allowance, ok
score.write_dollars(os.path.join(run_dir, "dollars.csv"), rows)   # or: score.py <run_dir> --dollars-csv
both = score.m1_both(ledger, ks, g, fine)      # {"strict": Check, "gap_width": Check, "flips": [...]}
```

## What We're NOT Doing

- Main-map merge or state sealing (`merge.py`, `--states`, `--window`): the overnight run is unsealed like #125.
- A dollar repair arm (owner chose B1: gate and re-run, no repair arm).
- The #131 dry-land gap builder, `zcta_gap_land.csv.gz`, its test rewrite or rebase (before stakeholders, not overnight).
- The thin-unit floor (G2/#132) and any Manhattan rule (owner C1: none on the main map).
- A land term in `repair.py` windows (repair keeps its objective; `land.csv` reports drift).
- PROBLEM.md / WATCHDOG.md / MANDATES.md edits: the WIFI window, $1.6B allowance, $1,000M national floor and #133 definition are owner decisions for the lander to file.
- Any merge to `main` (owner only), shortlist registration of grid points (morning step, after review), any change to IFA scoring.
- Resolving #111, #112, #119 or the #133 ladder.

## Phase 1: Dollar-scaled extract + export_long reversal

### Overview
Build the $M extract writer (`dollarize.py`: `scale`, `rates_of`, `to_m_rel`, a name guard that only accepts gitignored extract names). Land `export_long.py` from `m5-studio/ifa-conus` with the main-map CANON spellings and the $M → `m_rel` reversal (`rows_long`). Add tests and CODE_MAP rows. Every later phase reads the $M extract or its helpers.

### Changes Required:

#### 1. Dollar extract
**File**: `tools/exp/contig/dollarize.py` (NEW)
**Changes**: The whole module.

```python
"""dollarize.py -- the dollar-scaled extract (G5/B1, the main-map overnight grid, 2026-10-13): every
cell's mass in $M, so the master, the draw, the repair and the audit balance dollars with their band
rows unchanged (one mass vector feeds every stage).

    "$TD_PY" tools/exp/contig/dollarize.py <instance_descaled.json.gz> <instance_descaled_usd.json.gz>

A cell's $M is its `m_rel` times its fine channel's rate, E1 as coded: the owner's dollar total over
the extract's `m_rel` total (`tools/looks/score.py`'s `dollar_rates`), in $M.  The output keeps
the format `td_instance_descaled/3`, so `td.data.load` reads it, and records `meta["dollar_scale"]`:
the unit, the rates, the source's file name and sha256, and the fine channels dropped, those with no
owner total (career, edj, imo, priafs, which every main-map scenario plans elsewhere), never mixed
into a file of another unit.  A run's `manifest.json` records the output's path and sha256
(`run.write_manifest`), so a run traces back through `dollar_scale` to its descaled source.

The output keeps the source's per-rep shares and firm map, so it is as confidential as the source:
`main` refuses a name `.gitignore`'s `instance_descaled*.json.gz` does not cover, the source
itself, and a source already in dollars.  `to_m_rel` is the reversal (`export_long.py`).  Nothing
here prints a row's values.
"""
from __future__ import annotations

import argparse
import fnmatch
import functools
import hashlib
import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data  # noqa: E402

UNIT = "$M"
KEY = "dollar_scale"
IGNORED = "instance_descaled*.json.gz"      # .gitignore:18, the confidential extracts


def _score():
    """`tools/looks/score.py`, loaded by path once (`tools/mandates/check.py`'s module name)."""
    if "looks_score" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "looks_score", os.path.join(ROOT, "tools", "looks", "score.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["looks_score"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["looks_score"]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rates(extract: data.Extract) -> dict:
    """{fine channel: $M per m_rel}, E1 as coded, for the fine channels with an owner total."""
    return {f: r / 1e6 for f, r in _score().dollar_rates(extract).items()}


def scale(extract: data.Extract, source: str = "", source_sha256: str = "") -> data.Extract:
    """`extract` with every cell's mass in $M (module doc).  Raises ValueError on an extract
    already in dollars."""
    if KEY in extract.meta:
        raise ValueError(f"the extract is already in dollars ({extract.meta[KEY].get('unit')})")
    r = rates(extract)
    keep = [i for i, c in enumerate(extract.channel) if c in r]
    channels = tuple(c for c in extract.channels if c in r)
    meta = {**extract.meta, "channels": list(channels),
            KEY: {"unit": UNIT, "rates": dict(sorted(r.items())), "source": source,
                  "source_sha256": source_sha256,
                  "dropped_channels": sorted(set(extract.channels) - set(r))}}
    return data.Extract(channels, [extract.z[i] for i in keep], [extract.channel[i] for i in keep],
                        [extract.m_rel[i] * r[extract.channel[i]] for i in keep],
                        [dict(extract.share[i]) for i in keep], [extract.share_free[i] for i in keep],
                        dict(extract.firm), meta, dict(extract.dropped))


@functools.lru_cache(maxsize=None)
def rates_of(path: str) -> dict | None:
    """The {fine channel: $M per m_rel} a dollar extract at `path` was scaled by, or None for an
    extract in `m_rel`."""
    got = data.load(path).meta.get(KEY)
    return None if got is None else dict(got["rates"])


def to_m_rel(value: float, fine: str, rates_: dict | None) -> float:
    """A cell's mass back in `m_rel`: `value` over its fine channel's rate, or `value` itself
    when `rates_` is None (an extract in `m_rel`).  Raises KeyError on a fine channel with no
    rate."""
    return value if rates_ is None else value / rates_[fine]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="the descaled extract (td_instance_descaled/3, m_rel)")
    ap.add_argument("out", help=f"the dollar extract; its name must match {IGNORED}")
    a = ap.parse_args(argv)
    if not fnmatch.fnmatch(os.path.basename(a.out), IGNORED):
        sys.exit(f"{a.out}: the name must match {IGNORED} (.gitignore), the file carries rep shares")
    if os.path.exists(a.out) and os.path.samefile(a.source, a.out):
        sys.exit(f"{a.out} is the source")
    ext = data.load(a.source)
    try:
        usd = scale(ext, os.path.basename(a.source), sha256(a.source))
    except ValueError as e:
        sys.exit(f"{a.source}: {e}")
    data.write(usd, a.out)
    info = usd.meta[KEY]
    print(f"{a.out}: {len(usd.z)} cells in {UNIT}, channels {', '.join(usd.channels)}; dropped "
          f"{', '.join(info['dropped_channels']) or 'none'}; rates "
          + ", ".join(f"{f} {x:.6g}" for f, x in info["rates"].items()) + f"; sha256 {sha256(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

#### 2. Long-schema export with the reversal
**File**: `tools/exp/contig/export_long.py` (NEW)
**Changes**: The base is `git show m5-studio/ifa-conus:tools/exp/contig/export_long.py` (D4). This adds the main-map CANON rows, the `_dollarize` loader, the row loop moved into `rows_long` with the reversal, the refusal when the extract is missing, and the final print's "$M reversed" note.

```python
"""Export a run folder's ledger in the nationwide long schema the owner's database already holds
(archive `tools/export_all_scenarios_nationwide_long.py`, 2026-09-14): one row per (scenario, ZCTA,
source channel), columns exactly `scenario, zip_code, current_channel, canonical_channel, state,
model_channel, bundle, district, district_channels, rep, m_rel, has_commercial_opportunity`.

The scenario id is `<K>_<channels>_<commit>` (owner, 2026-10-08: "just use 52_ifa_ and the relevant
commit hash at the end"), the commit being the one that first committed the run folder's ledger.csv
on its branch; `scenarios.csv` beside the file ties it to the branch, the code commit, the spec and
extract hashes and the source runs, so a row can be traced to the exact solver run.  No dollars, no shares, no reps, no firms.

A run drawn on a dollar extract (`dollarize.py`, the main-map overnight grid) holds $M in its
ledger's `m_rel` column; the export divides each row by its fine channel's rate from the extract's
`dollar_scale` (`rows_long`), so the database always receives `m_rel`.  The extract is the one
`manifest.json` names; a run whose extract is gone is refused (without it $M cannot be told from
`m_rel`), so a dollar run is never exported in $M.

    "$TD_PY" tools/exp/contig/export_long.py <run_dir> [--branch NAME] [--rank N]
"""
import argparse, csv, datetime, gzip, importlib.util, json, os, subprocess, sys

COLUMNS = ["scenario", "zip_code", "current_channel", "canonical_channel", "state", "model_channel",
           "bundle", "district", "district_channels", "rep", "m_rel", "has_commercial_opportunity"]
SCENARIO_COLUMNS = ["scenario", "legacy_id", "k_total", "channels", "run_id", "run_folder", "branch", "commit", "ledger_commit",
                    "code_commit", "code_dirty", "spec_sha256", "instance_sha256", "source_runs",
                    "m1", "m1_gate", "shortlist_rank", "exported_at"]
# the extract's channel spellings -> the database's canonical names and bundles (archive exporter's
# SUBCHANNELS table, IFA added as its own bundle; the v3 extract's main-map spellings added for the
# overnight grid)
CANON = {"ifa": ("ifa", "IFA"), "National (Chase)": ("national_chase", "N"), "Wells WH": ("national_wells_wh", "N"),
         "Wells FI": ("national_wells_fi", "N"), "WH": ("wh", "WH"), "FI": ("fi", "FI"),
         "national_chase": ("national_chase", "N"), "wells_wh": ("national_wells_wh", "N"),
         "wells_fi": ("national_wells_fi", "N"), "wh": ("wh", "WH"), "fi": ("fi", "FI")}
HERE = os.path.dirname(os.path.abspath(__file__))


def _dollarize():
    if "contig_dollarize" not in sys.modules:
        spec = importlib.util.spec_from_file_location("contig_dollarize", os.path.join(HERE, "dollarize.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_dollarize"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_dollarize"]


def rows_long(rows, scenario, rates):
    """The long rows of ledger `rows` for `scenario`; `m_rel` is the ledger's value over its fine
    channel's rate when `rates` ({fine: $M per m_rel}, `dollarize.rates_of`) is given, else as is."""
    to_m_rel = _dollarize().to_m_rel
    for r in rows:
        canon, bundle = CANON.get(r["current_channel"], (r["current_channel"].lower(), r["model_channel"]))
        m = to_m_rel(float(r["m_rel"] or 0.0), r["current_channel"], rates)
        yield {"scenario": scenario, "zip_code": r["zip_code"], "current_channel": r["current_channel"],
               "canonical_channel": canon, "state": r["state"], "model_channel": r["model_channel"],
               "bundle": bundle, "district": r["district"], "district_channels": r["district_channels"],
               "rep": "", "m_rel": f"{m:.6f}", "has_commercial_opportunity": m > 0}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--branch", default=None, help="the branch the run folder is published on")
    ap.add_argument("--rank", default="", help="the shortlist rank, once registered")
    a = ap.parse_args(argv)
    run_dir = os.path.abspath(a.run_dir)
    man = json.load(open(os.path.join(run_dir, "manifest.json")))
    run_id = man["run_id"]
    extract = man.get("extract", "")
    if not os.path.exists(extract):
        sys.exit(f"{extract or 'no extract in manifest.json'}: the run's extract is needed to tell $M from m_rel")
    rates = _dollarize().rates_of(extract)
    rows = list(csv.DictReader(open(os.path.join(run_dir, "ledger.csv"))))
    counts = {}
    for r in rows:
        counts.setdefault(r["model_channel"], set()).add(r["district"])
    counts = {ch: len(d) for ch, d in sorted(counts.items())}
    ledger_commit = subprocess.run(["git", "log", "--diff-filter=A", "--format=%h", "--", "ledger.csv"],
                                   capture_output=True, text=True, cwd=run_dir).stdout.split()
    if not ledger_commit:
        sys.exit("ledger.csv is not committed yet: commit the run folder first, the scenario id carries that commit")
    scenario = f"{sum(counts.values())}_{'_'.join(ch.lower() for ch in counts)}_{ledger_commit[-1]}"
    out_dir = os.path.join(run_dir, "export")
    os.makedirs(out_dir, exist_ok=True)
    name = f"{scenario}_nationwide_zcta_long.csv"
    with open(os.path.join(out_dir, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows_long(rows, scenario, rates))
    with open(os.path.join(out_dir, name), "rb") as src, gzip.open(os.path.join(out_dir, name + ".gz"), "wb") as dst:
        dst.writelines(src)
    legacy = f"{sum(counts.values())}_total_" + "_".join(f"{n}{ch.lower()}" for ch, n in counts.items())
    branch = a.branch or subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True,
                                        cwd=run_dir).stdout.strip()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=run_dir).stdout.strip()
    prov = man.get("provenance", {})
    scen = {"scenario": scenario, "legacy_id": legacy, "k_total": sum(counts.values()),
            "channels": ";".join(f"{ch}={n}" for ch, n in counts.items()), "run_id": run_id,
            "run_folder": os.path.relpath(run_dir, subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                                                  capture_output=True, text=True, cwd=run_dir).stdout.strip()),
            "branch": branch, "commit": commit, "ledger_commit": ledger_commit[-1], "code_commit": prov.get("commit", ""), "code_dirty": prov.get("dirty", ""),
            "spec_sha256": man.get("scenario", {}).get("sha256", ""), "instance_sha256": prov.get("instance_sha256", ""),
            "source_runs": ";".join(f"{os.path.basename(os.path.dirname(s['run']))}/{os.path.basename(s['run'])}@{s['commit'][:7]}"
                                    for s in man.get("source_runs", [])),
            "m1": man.get("m1", ""), "m1_gate": man.get("m1_gate", ""), "shortlist_rank": a.rank,
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    with open(os.path.join(out_dir, "scenarios.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SCENARIO_COLUMNS)
        w.writeheader()
        w.writerow(scen)
    print(f"{name}: {len(rows)} rows, scenario {scenario} (run {run_id}, legacy id {legacy}"
          f"{', $M reversed to m_rel' if rates else ''}); scenarios.csv written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

#### 3. Tests
**File**: `tests/test_dollarize.py` (NEW)
**Changes**: Six tests on a hand-made extract: the E1 scale, refusing a second scale, the file round trip and reversal, the scorer's rates of 1e6 per $M, the export's reversal, and the name guard.

```python
"""tools/exp/contig/dollarize.py and export_long.py's reversal (main-map overnight grid, G5/B1) on
a hand-made extract: the $M scale is E1 as coded, the file round-trips through `td.data`, the
scorer's rates on it are 1e6 per $M, and the export gives back the `m_rel` the scale started
from.  Every value is made up; no real row enters a test."""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile

from td import data

HERE = os.path.dirname(os.path.abspath(__file__))
CONTIG = os.path.join(HERE, "..", "tools", "exp", "contig")


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


dollarize = _load("contig_dollarize", os.path.join(CONTIG, "dollarize.py"))
export_long = _load("contig_export_long", os.path.join(CONTIG, "export_long.py"))
score = dollarize._score()

CELLS = [("10001", "national_chase", 2.0), ("10001", "wh", 1.0), ("10001", "fi", 0.5),
         ("10002", "national_chase", 3.0), ("10002", "fi", 1.5), ("10002", "edj", 4.0),
         ("10003", "wh", 0.25)]


def _toy() -> data.Extract:
    chans = ("national_chase", "wh", "fi", "edj")
    return data.Extract(chans, [z for z, _, _ in CELLS], [c for _, c, _ in CELLS],
                        [m for _, _, m in CELLS], [{"R0000": 0.5} if i == 0 else {} for i in range(len(CELLS))],
                        [0.25 if i == 1 else 0.0 for i in range(len(CELLS))], {"R0000": "F0"},
                        {"channels": list(chans)})


def test_scale_is_e1_in_millions_and_drops_channels_without_a_total():
    ext = _toy()
    usd = dollarize.scale(ext, "instance_descaled.json.gz", "ab" * 32)
    total = {"national_chase": 5.0, "wh": 1.25, "fi": 2.0}
    want = {f: score.DOLLARS[f] / total[f] / 1e6 for f in total}
    info = usd.meta["dollar_scale"]
    assert info["unit"] == "$M" and info["dropped_channels"] == ["edj"]
    assert info["source"] == "instance_descaled.json.gz" and info["source_sha256"] == "ab" * 32
    assert set(info["rates"]) == set(want)
    assert all(math.isclose(info["rates"][f], want[f], rel_tol=1e-12) for f in want)
    assert usd.channels == ("national_chase", "wh", "fi") and usd.meta["channels"] == list(usd.channels)
    assert "edj" not in usd.channel and len(usd.z) == len(CELLS) - 1
    for z, c, m, x in zip(usd.z, usd.channel, usd.m_rel, (r for r in CELLS if r[1] != "edj")):
        assert (z, c) == x[:2] and math.isclose(m, x[2] * want[c], rel_tol=1e-12)
    assert usd.share[0] == {"R0000": 0.5} and usd.share_free[1] == 0.25 and usd.firm == {"R0000": "F0"}


def test_scale_refuses_an_extract_already_in_dollars():
    usd = dollarize.scale(_toy())
    try:
        dollarize.scale(usd)
    except ValueError as e:
        assert "already in dollars" in str(e)
    else:
        raise AssertionError("a dollar extract was scaled twice")


def test_file_round_trip_and_reversal():
    ext = _toy()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "instance_descaled_usd.json.gz")
        usd = dollarize.scale(ext)
        data.write(usd, path)
        back = data.load(path)
        rates = dollarize.rates_of(path)
    assert back == usd
    assert rates == usd.meta["dollar_scale"]["rates"]
    kept = [r for r in CELLS if r[1] != "edj"]
    for (z, c, m), x in zip(kept, back.m_rel):
        assert math.isclose(dollarize.to_m_rel(x, c, rates), m, rel_tol=1e-12)
    assert dollarize.to_m_rel(1.5, "wh", None) == 1.5


def test_scorer_rates_on_a_dollar_extract_are_a_million_per_unit():
    usd = dollarize.scale(_toy())
    got = score.dollar_rates(usd)
    assert set(got) == {"national_chase", "wh", "fi"}
    assert all(math.isclose(r, 1e6, rel_tol=1e-12) for r in got.values())


def test_export_rows_reverse_dollars_and_keep_m_rel_runs():
    usd = dollarize.scale(_toy())
    rates = usd.meta["dollar_scale"]["rates"]
    rows = [{"zip_code": z, "current_channel": c, "state": "NY", "model_channel": "national" if c == "national_chase" else c.upper(),
             "district": "d1", "district_channels": "", "m_rel": repr(m)} for z, c, m in zip(usd.z, usd.channel, usd.m_rel)]
    rows.append({"zip_code": "10004", "current_channel": "wh", "state": "NY", "model_channel": "WH",
                 "district": "d1", "district_channels": "", "m_rel": ""})
    got = list(export_long.rows_long(rows, "s", rates))
    kept = [m for _, c, m in CELLS if c != "edj"] + [0.0]
    assert [r["m_rel"] for r in got] == [f"{m:.6f}" for m in kept]
    assert [r["has_commercial_opportunity"] for r in got] == [m > 0 for m in kept]
    assert got[0]["canonical_channel"] == "national_chase" and got[0]["bundle"] == "N"
    assert got[1]["canonical_channel"] == "wh" and got[1]["bundle"] == "WH"
    assert all(r["rep"] == "" for r in got)
    plain = list(export_long.rows_long(rows[:1], "s", None))
    assert plain[0]["m_rel"] == f"{usd.m_rel[0]:.6f}"


def test_main_refuses_a_name_gitignore_misses():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "instance_descaled.json.gz")
        data.write(_toy(), src)
        for name in ("usd.json.gz", "instance_usd.json.gz"):
            try:
                dollarize.main([src, os.path.join(tmp, name)])
            except SystemExit as e:
                assert "must match" in str(e.code)
            else:
                raise AssertionError(f"{name} was written")
        assert dollarize.main([src, os.path.join(tmp, "instance_descaled_usd.json.gz")]) == 0
        assert dollarize.rates_of(os.path.join(tmp, "instance_descaled_usd.json.gz")) is not None
```

#### 4. CODE_MAP rows
**File**: `docs/CODE_MAP.md` (MODIFY)
**Changes**: Insert these two rows immediately after the `tools/exp/contig/replan.py` row of `## Files`. Phase 6 adds four more rows after them.

```markdown
| `tools/exp/contig/dollarize.py`, `tools/exp/contig/export_long.py` | the main-map overnight grid's dollars (G5/B1, 2026-10-13): `dollarize.py` writes the $M extract (`instance_descaled_usd.json.gz` at the hub root, gitignored with the other extracts), every cell's `m_rel` times its fine channel's E1 rate (`score.dollar_rates` / 1e6), the fine channels with no owner total dropped, `meta.dollar_scale` recording the rates and the source's name and sha256 (`rates_of`, `to_m_rel`); `export_long.py` (from `m5-studio/ifa-conus`, `21d9cb4`) writes a run's ledger in the owner's nationwide long schema with `scenarios.csv`, a dollar run's $M turned back into `m_rel` (`rows_long`) |
| `tests/test_dollarize.py` | the $M scale against E1 by hand, the file round trip and the reversal, the scorer's rates on a dollar extract (1e6 per $M), the export's reversal and channel names, the name guard |
```

### Success Criteria:

#### Automated Verification:
- [ ] Slice tests pass: `"$TD_PY" tests/run_all.py -k test_dollarize.py 2>&1 | tail -3` shows `6 passed, 0 failed`
- [ ] The name guard covers only gitignored extracts: `rg -c 'IGNORED = "instance_descaled\*\.json\.gz"' tools/exp/contig/dollarize.py` prints 1, and `git check-ignore -q instance_descaled_usd.json.gz` exits 0
- [ ] export_long carries the main-map channel names and the reversal: `rg -c 'def rows_long|"wells_fi": \("national_wells_fi", "N"\)' tools/exp/contig/export_long.py` prints 2
- [ ] export_long's other lines are the branch's: `git show m5-studio/ifa-conus:tools/exp/contig/export_long.py | diff - tools/exp/contig/export_long.py | rg -c '^< '` prints at most 12 (docstring tail, imports, CANON, the row loop moved into `rows_long`, the final print)
- [ ] CODE_MAP rows present: `rg -c 'tools/exp/contig/dollarize.py|tests/test_dollarize.py' docs/CODE_MAP.md` prints 2
- [ ] The export writes no shares, reps or firms (masking): `rg -c 'share|firm' tools/exp/contig/export_long.py` prints 1 (the docstring's "No dollars, no shares, no reps, no firms.")
- [ ] The scenario-id convention is the branch's (`21d9cb4`, `ef5d761`): `diff <(git show m5-studio/ifa-conus:tools/exp/contig/export_long.py | rg '^    scenario = ') <(rg '^    scenario = ' tools/exp/contig/export_long.py)` exits 0
- [ ] No extract staged or tracked: `git status --porcelain | rg 'instance_descaled'` prints nothing

#### Manual Verification:
- [ ] On m5: `"$TD_PY" tools/exp/contig/dollarize.py "$TD_REPO/instance_descaled.json.gz" "$TD_REPO/instance_descaled_usd.json.gz"` prints rates equal to `runs/sweep/grid_2026-10-01/tables.json`'s `fac` to 5 significant figures (wh 1.2501, fi 1.2426, wells_wh 1.2400, wells_fi 1.1776, national_chase 1.2340, ifa 1.2520) and drops career, edj, imo, priafs; `git -C "$TD_REPO" check-ignore -q instance_descaled_usd.json.gz` exits 0
- [ ] The $M per-channel totals of the new file equal the owner's totals (`score.DOLLARS` / 1e6: wh 11,360, fi 20,690, wells_wh 4,440, wells_fi 4,630, national_chase 8,550, ifa 62,140) to 1e-6 relative, printed as aggregates only, never rows
- [ ] The output's sha256 is recorded in the m5 setup notes for the m2 comparison in Slice 7

---

## Phase 2: Per-district dollar gate

### Overview
In `tools/looks/score.py`, gate every district of a main-map run against its channel's dollar window: `WINDOWS`, `WHOLE_STATE_CAP` (WIFI $1.6B for a district made only of whole states), `district_dollars`, `dollar_gate`, `gate_reason`, `write_dollars` / `--dollars-csv`, and `eligibility(..., gate=)` replacing the ±15% band and the channel-average checks. IFA-only runs score as before. This phase applies only the Slice 2 hunks of the design's merged `score.py` fence. The Slice 3 hunks are Phase 3's.

### Changes Required:

#### 1. The gate
**File**: `tools/looks/score.py` (MODIFY)
**Changes**: A unified diff against HEAD `e82d6a4` (`git apply`). It is the design's merged fence minus the Slice 3 parts: the docstring's M1-necks sentence, `m1_check(gap_width=)`, `m1_both`, `write_m1`, the report's M1 suffix and `--m1-json`. Those stay in Phase 3. Without them this phase never calls `check_m1(gap_width=)`, which does not exist until Phase 3.

```diff
--- a/tools/looks/score.py
+++ b/tools/looks/score.py
@@ -17,13 +17,22 @@
 A map is **eligible** when (PROBLEM.md row 2026-10-04, `runs/plan_2026-10-04/EXPERIMENTS.md` §1):
 - the audit passes at a plain ±`BAND` band: no check of `scorecard.md` other than the band check
   fails, and `td.audit.check_bands` passes on the ledger with every channel's band τ_c(1 ± BAND),
-  τ_c = the channel's ledger total / K_c;
-- every channel with a `TARGET` averages a $ per district within ±`DOLLAR_BAND` of it, edges
-  included, compared in whole dollars.  $ is
-  m_rel times the owner's dollar total over the extract's m_rel total, per fine channel
-  (`DOLLARS`), summed over the channel's drawn cells; an IFA-only run uses the owner's
-  whole-extract IFA total over K instead (owner, 2026-10-04).  A channel without a target, such
-  as a combined channel (D11), is printed but not checked;
+  τ_c = the channel's ledger total / K_c.  A main-map run is exempt: the dollar gate below
+  replaces it;
+- a main-map run (any run but an IFA-only one) passes the dollar gate (`dollar_gate`, main-map
+  overnight grid, 2026-10-13): every district's $ lies in its channel's `WINDOWS`, edges
+  included, compared in whole dollars, and a channel without a window fails.  A district of a
+  channel in `WHOLE_STATE_CAP` (WIFI) that owns alone, in its channel, every state it owns a
+  ZCTA in may reach the cap, and its row says it took the allowance.  `--dollars-csv` writes the
+  rows to each run's `dollars.csv`.  $ is m_rel times the owner's dollar total over the
+  extract's m_rel total, per fine channel (`DOLLARS`), summed over the district's drawn cells; on
+  a dollar extract (`tools/exp/contig/dollarize.py`, $M) that rate is 1e6 for every fine
+  channel;
+- an IFA-only run averages a $ per district within ±`DOLLAR_BAND` of its `TARGET`, edges
+  included, compared in whole dollars, $ being the owner's whole-extract IFA total over K (owner,
+  2026-10-04).  A run scored by `eligibility` without a gate is held to the same average rule on
+  every channel with a target, a channel without one, such as a combined channel (D11), printed
+  but not checked;
 - the main map's total K is in `MAIN_K`; an IFA-only run is exempt;
 - M1 holds (#108): `td.audit.check_m1` passes on the ledger with the committed polygon graph and
   its owner-approved connectors (`td.geo.polygon_graph`): every district one piece, every CONUS
@@ -92,6 +101,11 @@
 TARGET = {"national": 1.25e9, "WH": 1.0e9, "FI": 0.9e9, "IFA": 1.25e9}          # $ per district
 DOLLARS = {"wh": 11.36e9, "fi": 20.69e9, "wells_wh": 4.44e9, "wells_fi": 4.63e9,  # owner's totals,
            "national_chase": 8.55e9, "ifa": 62.14e9}                              # 2026-10-01
+WINDOWS = {"national": (1.0e9, 1.4375e9), "WH": (0.85e9, 1.15e9),      # $ per district, the main
+           "FI": (0.765e9, 1.035e9), "WIFI": (0.85e9, 1.15e9)}           # map's gate (2026-10-13)
+WHOLE_STATE_CAP = {"WIFI": 1.6e9}       # a district of whole states only (owner, 2026-10-13)
+DOLLAR_COLUMNS = ["channel", "district", "usd_m", "lo_m", "hi_m", "whole_state_cap_m", "states",
+                  "whole_states", "allowance", "ok"]
 IFA_ONLY = {"IFA"}
 BAND_CHECK = "final bands on drawn mass"
 NECK = re.compile(r"^[^:]+: neck ")       # M1's neck items (`td.audit.neck_item`)
@@ -268,15 +282,81 @@
     return {f: DOLLARS[f] / total[f] for f in DOLLARS if total[f] > 0}
 
 
-def dollars_per_district(ch: str, k: int, ledger: list, rates: dict) -> float:
+def _need_rates(ch: str, ledger: list, rates: dict) -> None:
     fine = {r["current_channel"] for r in ledger if r["model_channel"] == ch and r["district"]}
     missing = sorted(fine - set(rates))
     if missing:
         raise ValueError(f"channel {ch}: no dollar total for fine channel(s) {', '.join(missing)}")
+
+
+def dollars_per_district(ch: str, k: int, ledger: list, rates: dict) -> float:
+    _need_rates(ch, ledger, rates)
     return sum(float(r["m_rel"]) * rates[r["current_channel"]] for r in ledger
                if r["model_channel"] == ch and r["district"]) / k
+
+
+def district_dollars(ch: str, ledger: list, rates: dict) -> dict:
+    """{district: $} of channel `ch`: m_rel times its fine channel's rate over the district's
+    drawn cells."""
+    _need_rates(ch, ledger, rates)
+    out = collections.Counter()
+    for r in ledger:
+        if r["model_channel"] == ch and r["district"]:
+            out[r["district"]] += float(r["m_rel"]) * rates[r["current_channel"]]
+    return out
+
+
+def dollar_gate(ledger: list, districts: list, rates: dict) -> list:
+    """The main map's dollar gate, one row per `districts.csv` row: `usd`, its channel's window
+    `lo`, `hi` (None without one), `states` it owns a ZCTA in, `whole_states` when it owns each
+    alone in its channel, `cap`, the channel's `WHOLE_STATE_CAP` for such a district (else None),
+    `allowance` when its $ is above `hi` and within the cap, and `ok`.  Whole dollars, edges
+    included; a channel without a window is never ok."""
+    owners = collections.defaultdict(set)          # (channel, state) -> districts owning a ZCTA
+    states = collections.defaultdict(set)          # (channel, district) -> states
+    for r in ledger:
+        if r["district"]:
+            owners[r["model_channel"], r["state"]].add(r["district"])
+            states[r["model_channel"], r["district"]].add(r["state"])
+    usd, out = {}, []
+    for row in sorted(districts, key=lambda r: (r["channel"], r["district"])):
+        ch, d = row["channel"], row["district"]
+        if ch not in usd:
+            usd[ch] = district_dollars(ch, ledger, rates)
+        x, st = usd[ch].get(d, 0.0), sorted(states[ch, d])
+        whole = bool(st) and all(owners[ch, s] == {d} for s in st)
+        lo, hi = WINDOWS.get(ch, (None, None))
+        cap = WHOLE_STATE_CAP.get(ch) if whole else None
+        inside = lo is not None and round(lo) <= round(x) <= round(hi)
+        allowance = (not inside and lo is not None and cap is not None
+                     and round(lo) <= round(x) <= round(cap))
+        out.append({"channel": ch, "district": d, "usd": x, "lo": lo, "hi": hi, "states": st,
+                    "whole_states": whole, "cap": cap, "allowance": allowance,
+                    "ok": inside or allowance})
+    return out
 
 
+def gate_reason(r: dict) -> str:
+    """Why a `dollar_gate` row fails."""
+    if r["lo"] is None:
+        return f"$ {r['district']}: no dollar window for {r['channel']}"
+    cap = f" (whole states: up to {r['cap'] / 1e6:,.1f}M)" if r["cap"] is not None else ""
+    return (f"$ {r['district']} {r['usd'] / 1e6:,.1f}M outside {r['lo'] / 1e6:,.1f}-"
+            f"{r['hi'] / 1e6:,.1f}M{cap}")
+
+
+def write_dollars(path: str, gate: list) -> None:
+    """`dollars.csv`: the `dollar_gate` rows, $ in $M."""
+    def m(v):
+        return "" if v is None else f"{v / 1e6:.3f}"
+    with open(path, "w", newline="") as fh:
+        w = csv.writer(fh)
+        w.writerow(DOLLAR_COLUMNS)
+        for r in gate:
+            w.writerow([r["channel"], r["district"], m(r["usd"]), m(r["lo"]), m(r["hi"]), m(r["cap"]),
+                        ";".join(r["states"]), int(r["whole_states"]), int(r["allowance"]), int(r["ok"])])
+
+
 def scorecard_checks(text: str) -> dict:
     """{check name: status} from the table of a `scorecard.md`."""
     out = {}
@@ -326,17 +406,21 @@
 
 
 def eligibility(checks: dict, bands: audit.Check, ks: dict, dollars: dict,
-                m1: audit.Check | None = None) -> list:
+                m1: audit.Check | None = None, gate: list | None = None) -> list:
     """Why a run is not eligible, one reason per failed rule; empty when it is.  `m1` is the M1
-    check; a run without one is not eligible."""
+    check; a run without one is not eligible.  `gate`, the `dollar_gate` rows of a main-map run,
+    replaces the ±`BAND` band and the per-channel average with one reason per failing district;
+    an IFA-only run ignores it."""
+    gated = gate is not None and set(ks) != IFA_ONLY
     why = [f"audit: {name} fails" for name, s in checks.items() if s == "fail" and name != BAND_CHECK]
     if m1 is None or m1.status != "pass":
         why.append(f"M1: {m1.status}, {m1.summary}" if m1 else "M1: not checked")
     if not checks:
         why.append("audit: no scorecard")
-    if bands.status != "pass":
+    if bands.status != "pass" and not gated:
         why.append(f"audit at ±{100 * BAND:.0f}%: {bands.summary}")
-    for ch, d in sorted(dollars.items()):
+    why += [gate_reason(r) for r in gate or () if gated and not r["ok"]]
+    for ch, d in sorted(dollars.items()) if not gated else ():
         t = TARGET.get(ch)
         if t is None:
             continue
@@ -377,14 +461,16 @@
     sc = open(sc_path, encoding="utf-8").read() if os.path.exists(sc_path) else ""
     chans = {ch: channel_looks(ch, ledger, districts, g) for ch in sorted({r["channel"] for r in districts})}
     ks = {ch: c["k"] for ch, c in chans.items()}
+    gate = None
     if set(ks) == IFA_ONLY:              # owner, 2026-10-04: the whole-extract IFA total over K
         dollars = {ch: DOLLARS["ifa"] / k for ch, k in ks.items()}
     else:
         rates = rates if rates is not None else rates_of(extract_path(run_dir))
         dollars = {ch: dollars_per_district(ch, k, ledger, rates) for ch, k in ks.items()}
+        gate = dollar_gate(ledger, districts, rates)
     bands = bands_at(ledger, ks, BAND)
     m1 = m1_check(ledger, ks, g, fine_channels(run_dir))
-    why = eligibility(scorecard_checks(sc), bands, ks, dollars, m1)
+    why = eligibility(scorecard_checks(sc), bands, ks, dollars, m1, gate)
     diag = audit.diagnostic(run_dir)
     if diag is not None:                 # never a deliverable (#121)
         why.insert(0, "diagnostic band" + (f" ({diag['label']})" if diag["label"] else ""))
@@ -397,6 +483,7 @@
     return {
         "run": os.path.basename(os.path.normpath(run_dir)), "dir": run_dir,
         "eligible": not why, "why": why, "diagnostic": diag is not None, "k": ks, "dollars": dollars,
+        "dollar_gate": gate,
         "m1": {"status": m1.status, "summary": m1.summary, **m1.counts},
         "necks": [i for i in m1.items if NECK.search(i)],
         "mass_necks": [i for i in m1.items if audit.MASS_NECK in i],
@@ -470,6 +557,13 @@
                   for d, n, f, st in sorted(largest.values(), key=lambda p: (-p[2], p[0]))]
         lines += [f"    multipart piece {d}: part of {zs}, {km2:,.3f} km2 (visual defect, not M1)"
                   for d, zs, km2 in c["multipart"] or ()]
+    gate = s.get("dollar_gate")
+    if gate is not None:
+        lines.append(f"$ gate: {len(gate)} districts, {sum(not r['ok'] for r in gate)} outside their window, "
+                     f"{sum(r['allowance'] for r in gate)} on the whole-state allowance")
+        lines += [f"    {gate_reason(r)}" for r in gate if not r["ok"]]
+        lines += [f"    {r['district']} {r['usd'] / 1e6:,.1f}M on the whole-state allowance "
+                  f"({'+'.join(r['states'])}, up to {r['cap'] / 1e6:,.1f}M)" for r in gate if r["allowance"]]
     lines += [f"channel-state splits: {s['splits']}: {' '.join(s['split_list'])}",
               f"distinct split states: {len(s['distinct'])}: {' '.join(s['distinct'])}",
               f"defects: {s['defects']:g} = thin {s['thin_links']} + small {s['small_pieces']} + crowded "
@@ -490,9 +584,15 @@
     ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
     ap.add_argument("run_dirs", nargs="+")
     ap.add_argument("--extract", help="the extract (default: run.json's source under $TD_REPO)")
+    ap.add_argument("--dollars-csv", action="store_true",
+                    help="write each main-map run's dollar gate to its dollars.csv")
     a = ap.parse_args(argv)
     rates = rates_of(a.extract) if a.extract else None
     scores = rank([score(d, rates=rates) for d in a.run_dirs])
+    if a.dollars_csv:
+        for s in scores:
+            if s["dollar_gate"] is not None:
+                write_dollars(os.path.join(s["dir"], "dollars.csv"), s["dollar_gate"])
     for s in scores:
         print(report(s), end="\n\n")
     if len(scores) > 1:
```

#### 2. Scorer tests
**File**: `tests/test_looks_score.py` (MODIFY)
**Changes**: A unified diff against HEAD `e82d6a4` (`git apply`; the design's fence unchanged). It tests window edges inclusive in whole dollars, the whole-state allowance (WIFI only, whole states only), eligibility with a gate, `write_dollars`, and the toy run's gate rows. The IFA-only run's `dollar_gate` is None.

```diff
--- a/tests/test_looks_score.py
+++ b/tests/test_looks_score.py
@@ -203,8 +203,89 @@
         for d in (t * 1.1 + 1, t * 0.9 - 1):             # a dollar past either edge: not
             why = score.eligibility({}, ok, {"IFA": 1}, {ch: d}, M1_PASS)
             assert len(why) == 2 and why[1].startswith(f"$ {ch} "), (ch, d, why)
+
+
+def _gate_rows(ch: str, cells) -> list:
+    """Ledger rows of channel `ch` from (ZIP, district, $) cells at a rate of 1 per $; the state is
+    the ZIP's first letter."""
+    return [{"zip_code": z, "current_channel": "x", "state": z[0].upper(), "model_channel": ch,
+             "district": d, "m_rel": repr(float(m))} for z, d, m in cells]
+
+
+def _gate(ch: str, cells, names) -> list:
+    return score.dollar_gate(_gate_rows(ch, cells), [{"channel": ch, "district": d} for d in names],
+                             {"x": 1.0})
+
+
+def test_dollar_gate_window_edges_inclusive():
+    """Every main-map window in whole dollars, edges included (precedent 2d189e9); a district
+    sharing its state with another takes no allowance."""
+    for ch, (lo, hi) in score.WINDOWS.items():
+        for x, ok in ((lo, True), (hi, True), (lo - 1, False), (hi + 1, False)):
+            rows = _gate(ch, (("a1", "D_01", x), ("a2", "D_02", lo)), ("D_02", "D_01"))
+            assert [r["district"] for r in rows] == ["D_01", "D_02"]
+            r = rows[0]
+            assert (r["ok"], r["allowance"], r["whole_states"], r["cap"]) == (ok, False, False, None), (ch, x, r)
+            assert (r["usd"], r["lo"], r["hi"], r["states"]) == (x, lo, hi, ["A"])
+
+
+def test_whole_state_allowance_is_wifi_only_and_whole_states_only():
+    """Owner, 2026-10-13: a WIFI district owning alone, in WIFI, every state it owns a ZCTA in may
+    reach $1.6B; a zero-mass ZCTA of a shared state ends that, and no other channel has it."""
+    names = ("W_01", "W_02", "W_03")
+    cells = (("a1", "W_01", 1.0e9), ("a2", "W_01", 0.6e9), ("c1", "W_01", 0.0),   # A and C whole
+             ("b1", "W_02", 1.2e9), ("b2", "W_03", 1.0e9))                          # B shared
+    w1, w2, w3 = _gate("WIFI", cells, names)
+    assert (w1["ok"], w1["allowance"], w1["whole_states"], w1["cap"], w1["states"]) == (
+        True, True, True, 1.6e9, ["A", "C"])
+    assert (w2["ok"], w2["allowance"], w2["whole_states"], w2["cap"]) == (False, False, False, None)
+    assert (w3["ok"], w3["allowance"]) == (True, False)
+    assert score.gate_reason(w2) == "$ W_02 1,200.0M outside 850.0-1,150.0M"
+    edge = _gate("WIFI", (("a1", "W_01", 1.6e9),), names[:1])[0]
+    over = _gate("WIFI", (("a1", "W_01", 1.6e9 + 1),), names[:1])[0]
+    assert (edge["ok"], edge["allowance"]) == (True, True) and (over["ok"], over["allowance"]) == (False, False)
+    assert score.gate_reason(over) == "$ W_01 1,600.0M outside 850.0-1,150.0M (whole states: up to 1,600.0M)"
+    w1 = _gate("WIFI", cells + (("b3", "W_01", 0.0),), names)[0]
+    assert (w1["ok"], w1["whole_states"], w1["states"]) == (False, False, ["A", "B", "C"])
+    nat = _gate("national", (("a1", "N_01", 1.5e9),), ("N_01",))[0]
+    assert (nat["ok"], nat["whole_states"], nat["cap"]) == (False, True, None)
+    ne = _gate("NE", (("a1", "NE_01", 1.0e9),), ("NE_01",))[0]
+    assert ne["lo"] is None and not ne["ok"]
+    assert score.gate_reason(ne) == "$ NE_01: no dollar window for NE"
 
 
+def test_eligibility_with_a_gate():
+    """A main-map run: the gate's failing districts replace the ±15% band and the channel
+    averages; an IFA-only run ignores a gate, and a call without one keeps the old rules."""
+    checks = {**score.scorecard_checks(SCORECARD), audit.M1_CHECK: "pass"}
+    off = audit.Check(score.BAND_CHECK, "fail", "1 outside")
+    main = {"national": 15, "WH": 12, "FI": 20, "WIFI": 3}
+    far = {"national": 2.0e9, "WH": 0.5e9, "FI": 0.9e9, "WIFI": 1.0e9}      # averages the gate never reads
+    good = {"channel": "WH", "district": "WH_01", "usd": 1.0e9, "lo": 0.85e9, "hi": 1.15e9,
+            "states": ["A"], "whole_states": False, "cap": None, "allowance": False, "ok": True}
+    bad = dict(good, district="WH_02", usd=1.2e9, ok=False)
+    assert score.eligibility(checks, off, main, far, M1_PASS, [good]) == []
+    assert score.eligibility(checks, off, main, far, M1_PASS, [good, bad]) == [
+        "$ WH_02 1,200.0M outside 850.0-1,150.0M"]
+    assert score.eligibility({}, off, {"IFA": 49}, {"IFA": 1.227e9}, M1_PASS, [bad]) == [
+        "audit: no scorecard", "audit at ±15%: 1 outside"]
+    assert score.eligibility(checks, off, main, far, M1_PASS) == [
+        "audit at ±15%: 1 outside", "$ WH 500M is -50.0% of 1,000M", "$ national 2,000M is +60.0% of 1,250M"]
+
+
+def test_write_dollars():
+    rows = _gate("WIFI", (("a1", "W_01", 1.5e9), ("b1", "W_02", 0.9e9), ("b2", "W_03", 0.9e9)),
+                 ("W_01", "W_02", "W_03"))
+    with tempfile.TemporaryDirectory() as d:
+        path = os.path.join(d, "dollars.csv")
+        score.write_dollars(path, rows)
+        with open(path, newline="") as fh:
+            got = list(csv.reader(fh))
+    assert got[0] == score.DOLLAR_COLUMNS and len(got) == 4
+    assert got[1] == ["WIFI", "W_01", "1500.000", "850.000", "1150.000", "1600.000", "A", "1", "1", "1"]
+    assert got[2] == ["WIFI", "W_02", "900.000", "850.000", "1150.000", "", "B", "0", "0", "1"]
+
+
 def _score_toy(ch: str, rates: dict, fine=None, run_json=None) -> dict:
     """`score.score` on a run folder holding channel `ch` laid out as X; with `fine`, its
     `run.json` names the scenario's fine channels; `run_json` adds to that file."""
@@ -246,9 +327,16 @@
     assert s["worst_dev"] == 0.0 and s["mean_dev"] == 0.0
     assert f"INELIGIBLE ({sc}; {m1}; main K 2 outside 48-54) | 1 splits (1 states) | 5.4 defects" in score.verdict(s)
     assert "largest detached piece WH_02: 1 ZIPs in B, 0.250 tau" in score.report(s)
+    # the main map's dollar gate checks every district (2026-10-13): $1,000M each, in WH's window
+    assert [(r["district"], round(r["usd"]), r["ok"]) for r in s["dollar_gate"]] == [
+        ("WH_01", 1000000000, True), ("WH_02", 1000000000, True)]
+    hot = _score_toy("WH", {"wh": 1.2e9})
+    assert hot["why"] == [sc, m1, "$ WH_01 1,200.0M outside 850.0-1,150.0M",
+                          "$ WH_02 1,200.0M outside 850.0-1,150.0M", "main K 2 outside 48-54"]
+    assert "$ gate: 2 districts, 2 outside their window, 0 on the whole-state allowance" in score.report(hot)
     # An IFA-only run: no main K rule, and $ is the owner's whole-extract IFA total over K.
     ifa = _score_toy("IFA", {})
-    assert ifa["dollars"] == {"IFA": 62.14e9 / 2}
+    assert ifa["dollars"] == {"IFA": 62.14e9 / 2} and ifa["dollar_gate"] is None
     assert ifa["why"] == [sc, m1, "$ IFA 31,070M is +2385.6% of 1,250M"]
     # the scenario's fine channels come from run.json (#116): fi has no row at all
     both = _score_toy("WH", {"wh": 1.0e9}, fine=["wh", "fi"])
```

### Success Criteria:

#### Automated Verification:
- [ ] Slice tests pass: `"$TD_PY" tests/run_all.py -k test_looks_score.py 2>&1 | tail -1` shows `15 passed, 0 failed`
- [ ] Slice 1's scorer check still holds on a $M extract: `"$TD_PY" tests/run_all.py -k test_dollarize.py 2>&1 | tail -1` shows `6 passed, 0 failed`
- [ ] The gate's surface is present: `rg -c '^WINDOWS = |^WHOLE_STATE_CAP = |^def dollar_gate|^def gate_reason|^def write_dollars' tools/looks/score.py` prints 5
- [ ] The map captions' constants are untouched: `git diff HEAD -- tools/looks/score.py | rg -c '^[-+](TARGET|DOLLAR_BAND|BAND|DOLLARS) ='` prints 0
- [ ] Other scorer consumers still pass: `"$TD_PY" tests/run_all.py -k test_mandates 2>&1 | tail -1` shows `0 failed`

#### Manual Verification:
- [ ] On m5, re-gate one existing main-map run folder (precedents `1293d41`, `20cfe36`: no cached ELIGIBLE): `"$TD_PY" tools/looks/score.py <tier-P run dir> --dollars-csv` writes `dollars.csv` with one row per `districts.csv` row, and the report's `$ gate:` line counts them; the failing districts are consistent with the scouts' D3 audit under the new windows (national_01 −$48.4M and national_09 −$39.7M against the old $1,062.5M floor now inside $1,000M; WH_09 −$9.2M under $850M still fails)
- [ ] An IFA-only run folder scores exactly as before (same `why`, no `$ gate:` line, no `dollars.csv` written)

---

## Phase 3: Gap-width audit

### Overview
Land `d312834`'s `NeckGraph(gap_width)` verbatim in `td/audit.py`, plus `GAP_WIDTH_ENV`, `check_m1(run, gap_width=None)` (None reads the environment; True/False override it) and `counts["gap_width"]`. In `score.py`, add `m1_check(gap_width=)`, `m1_both` (both verdicts plus the districts that flip), `write_m1` / `--m1-json`, and the report's M1 suffix. After this phase `tools/looks/score.py` is byte-identical to the design's merged fence applied to HEAD.

### Changes Required:

#### 1. The switch in the audit
**File**: `td/audit.py` (MODIFY)
**Changes**: A unified diff against HEAD `e82d6a4` (`git apply`): `d312834`'s hunks verbatim, plus `GAP_WIDTH_ENV`, the `check_m1` parameter and `counts["gap_width"]`. Never `46d2d89`.

```diff
--- a/td/audit.py
+++ b/td/audit.py
@@ -447,6 +447,7 @@ NECK_TIME = 60.0        # seconds per district component; past it the district i
 NECK_TOL = 1e-9         # relative slack of the share comparisons, against float noise; it only
                         # enlarges what fails
 NECK_W_CM = round(NECK_W_KM * 1e5)  # widths are whole centimetres (`border_cm`): a neck is <= this - 1
+GAP_WIDTH_ENV = "TD_NECK_GAP_WIDTH"  # "1": `check_m1` measures necks across coverage gaps (G1, #131)
 
 
 def border_cm(metres: float) -> int:
@@ -477,9 +478,18 @@ class NeckGraph:
     `state`, and `border_cm` the borders in whole centimetres, floored (`border_cm`).  `polygon` is
     `geo.polygon_graph`'s dict, which carries "border", "connectors" and
     "aland" since #121.  An edge of the graph that is neither a bordered polygon edge nor a
-    connector counts as a polygon edge 0 km wide."""
-
-    def __init__(self, polygon: dict):
+    connector counts as a polygon edge 0 km wide.
+
+    `gap_width` is the G1 prototype (owner, 2026-10-08, "Measure width across coverage gaps"), off
+    by default until its owner-decision issue lands: when True, every pair of ZCTAs of one state
+    adjacent in the Voronoi ZIP graph but neither a polygon edge nor a connector (`geo`'s
+    `zcta_polygon_vs_voronoi.csv.gz` rows `dropped`, or `polygon["voronoi_gaps"]` {(a, b): m})
+    is a neck edge as wide as its shared Voronoi border, so land in no ZCTA counts towards a
+    passage.  No land test: `geo` separates land from water only per county at build time, so a
+    gap across water (a lake, a sound) counts too.  The gap edges enter `border_cm`, the necks'
+    widths, and not `border`, so `land_would_do` and the pieces still read the polygon edges."""
+
+    def __init__(self, polygon: dict, gap_width: bool = False):
         self.state = polygon.get("state", {})
         self.aland = polygon["aland"]
         border = {tuple(sorted(e)): m for e, m in polygon["border"].items()}
@@ -495,6 +505,16 @@ class NeckGraph:
             if e in border or e not in joins:
                 self.border[a][b] = self.border[b][a] = border.get(e, 0.0) / 1000.0
                 self.border_cm[a][b] = self.border_cm[b][a] = border_cm(border.get(e, 0.0))
+        if gap_width:
+            gaps = polygon.get("voronoi_gaps")
+            if gaps is None:
+                vs = geo.read_reference(name="zcta_polygon_vs_voronoi.csv.gz")
+                vs = vs[vs["change"] == "dropped"]
+                gaps = {(a, b): float(m) for a, b, m in zip(vs["a"], vs["b"], vs["border_m"])}
+            for (a, b), m in gaps.items():
+                if (a in self.aland and b in self.aland and b not in self.border_cm.get(a, {})
+                        and b not in self.connector.get(a, ()) and self.state.get(a) == self.state.get(b)):
+                    self.border_cm[a][b] = self.border_cm[b][a] = border_cm(m)
         self.by_state = collections.defaultdict(set)
         for z in polygon["vertices"]:
             self.by_state[self.state.get(z, "")].add(z)
@@ -797,12 +817,16 @@ def neck_item(ch: str, j: str, nk: Neck, kind: str = "neck") -> str:
             f"{nk.area:.1%} of its land area and {nk.mass:.1%} of its mass; cut {cut}")
 
 
-def check_m1(run: Run) -> Check:
+def check_m1(run: Run, gap_width: bool | None = None) -> Check:
     """M1 (module doc): one connected piece per district on the polygon graph, no neck
     (`district_necks`), and every (ZCTA, fine channel) cell of the scenario owned exactly once, in
     the planning channel holding it.  A polygon graph without border lengths leaves the necks, and
-    so M1, unverified."""
+    so M1, unverified.  `gap_width` is `NeckGraph`'s G1 switch: None reads `GAP_WIDTH_ENV` ("1"
+    turns it on), True or False overrides it (the main-map overnight grid gates with it on and
+    reports M1 both ways, 2026-10-13); `counts["gap_width"]` records which."""
     name = M1_CHECK
+    if gap_width is None:
+        gap_width = os.environ.get(GAP_WIDTH_ENV) == "1"
     if run.polygon is None:
         return Check(name, "unverified", "no polygon graph: M1 is not checked")
     adj = adjacency(run.polygon)
@@ -866,7 +890,8 @@ def check_m1(run: Run) -> Check:
     for i, comp in enumerate(_components(set(adj), adj)):
         whole.update(dict.fromkeys(comp, i))
     uncovered, n_pieces, split, largest, n_free = [], 0, 0, 0.0, 0
-    ng = NeckGraph(run.polygon) if {"border", "connectors", "aland"} <= set(run.polygon) else None
+    ng = (NeckGraph(run.polygon, gap_width=gap_width)
+          if {"border", "connectors", "aland"} <= set(run.polygon) else None)
     neck_items, mass_items, vertices = [], [], set(adj)
     for ch in sorted(set(run.channels) | set(owner)):
         spec = run.channels.get(ch)
@@ -919,7 +944,7 @@ def check_m1(run: Run) -> Check:
                  {"split": split, "pieces": n_pieces, "largest_tau": largest, "no_owner": n_free,
                   "no_row": n_norow, "double": n_double,
                   "necks": len(neck_items) if ng is not None else None,
-                  "mass_necks": len(mass_items) if ng is not None else None})
+                  "mass_necks": len(mass_items) if ng is not None else None, "gap_width": gap_width})
 
 
 def check_geography(run: Run) -> Check:
```

#### 2. Gap-width tests
**File**: `tests/test_neck_gapwidth.py` (NEW)
**Changes**: `d312834`'s test, plus the `check_m1` argument/environment override and `score.m1_both` / `write_m1` on the same toy.

```python
"""NeckGraph's gap_width flag (G1 prototype, owner 2026-10-08): a Voronoi-adjacent pair across land
in no ZCTA widens a passage, so a coverage gap no longer reads as a neck."""
from td import audit


def test_gap_width_turns_coverage_gap_neck_into_none():
    # A chain a-b-c of ZCTAs, 50 km borders, plus s reaching b through a 1 km polygon edge; s and c
    # are Voronoi neighbours across a 30 km land gap that no polygon edge spans.
    vs = ["a", "b", "c", "s"]
    edges = [("a", "b"), ("b", "c"), ("b", "s")]
    poly = {"vertices": vs, "edges": edges, "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8),
            "voronoi_gaps": {("c", "s"): 30000.0}}
    [nk] = audit.district_necks(set(vs), {}, audit.NeckGraph(poly))
    assert nk.zips == ("s",) and nk.width_km == 1.0
    assert audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True)) == []
    # A gap pair across a state line adds nothing.
    poly["state"] = dict(poly["state"], s="NM")
    assert len(audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True))) == 1

# ----------------------------------------------- check_m1's switch and score.m1_both (G3, 2026-10-13)
import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "looks_score", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "looks", "score.py"))
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)


def _gap_world() -> tuple:
    """(ledger, Geography): the toy above as one district X_01 of channel X, one fine channel f."""
    vs = ["a", "b", "c", "s"]
    poly = {"vertices": vs, "edges": [("a", "b"), ("b", "c"), ("b", "s")], "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8), "voronoi_gaps": {("c", "s"): 30000.0}}
    ledger = [{"zip_code": z, "current_channel": "f", "state": "TX", "model_channel": "X",
               "district": "X_01", "m_rel": "1.0"} for z in vs]
    return ledger, score.Geography(poly["state"], {}, {}, poly)


def test_check_m1_gap_width_argument_overrides_the_environment():
    ledger, g = _gap_world()
    old = os.environ.pop(audit.GAP_WIDTH_ENV, None)
    try:
        for env, arg, want in ((None, None, "fail"), ("1", None, "pass"), ("0", None, "fail"),
                               ("1", False, "fail"), (None, True, "pass")):
            if env is None:
                os.environ.pop(audit.GAP_WIDTH_ENV, None)
            else:
                os.environ[audit.GAP_WIDTH_ENV] = env
            m1 = score.m1_check(ledger, {"X": 1}, g, ["f"], gap_width=arg)
            assert (m1.status, m1.counts["gap_width"]) == (want, want == "pass"), (env, arg, m1.items)
            assert m1.counts["necks"] == (want == "fail")
    finally:
        os.environ.pop(audit.GAP_WIDTH_ENV, None)
        if old is not None:
            os.environ[audit.GAP_WIDTH_ENV] = old


def test_m1_both_lists_the_flip_and_writes_m1_json():
    ledger, g = _gap_world()
    both = score.m1_both(ledger, {"X": 1}, g, ["f"])
    assert (both["strict"].status, both["gap_width"].status) == ("fail", "pass")
    [flip] = both["flips"]
    assert flip["district"] == "X/X_01" and flip["gap_width"] == []
    [item] = flip["strict"]
    assert item.startswith("X/X_01: neck 1.00 km wide cuts off 1 ZIPs (s...)"), item
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m1.json")
        score.write_m1(path, both)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    assert (doc["strict"]["status"], doc["strict"]["gap_width"], doc["strict"]["necks"]) == ("fail", False, [item])
    assert (doc["gap_width"]["status"], doc["gap_width"]["gap_width"], doc["gap_width"]["necks"]) == ("pass", True, [])
    assert doc["flips"] == [flip]
    # no flip when both ways agree: s joined to b by a 20 km polygon edge is no neck either way
    _, g2 = _gap_world()
    g2.polygon["border"][("b", "s")] = 20000.0
    assert score.m1_both(ledger, {"X": 1}, g2, ["f"])["flips"] == []
```

#### 3. Both verdicts in the scorer
**File**: `tools/looks/score.py` (MODIFY)
**Changes**: A unified diff against the file as Phase 2 leaves it (`git apply`). These are the Slice 3 hunks of the design's merged fence.

```diff
--- a/tools/looks/score.py
+++ b/tools/looks/score.py
@@ -38,7 +38,10 @@
   its owner-approved connectors (`td.geo.polygon_graph`): every district one piece, every CONUS
   ZCTA owned in every channel.  Without a polygon graph M1 is unverified, and the run is not
   eligible.  The run's own scorecard M1, which also checks each cell's planning channel against
-  the scenario, must not fail either (#116);
+  the scenario, must not fail either (#116).  Necks are measured on polygon borders unless
+  `td.audit.GAP_WIDTH_ENV` is "1" (G1, #131), as the main-map overnight grid gates (G3,
+  2026-10-13); `m1_both` gives both verdicts and the districts they disagree on, and
+  `--m1-json` writes them to each run's `m1.json`;
 - the folder is not diagnostic (#121, `td.audit.diagnostic`): a run held to a diagnostic band,
   or derived from one, is INELIGIBLE with the reason "diagnostic band".
 
@@ -385,17 +388,46 @@
     return audit.check_bands(audit.Run(cells, chans))
 
 
-def m1_check(ledger: list, ks: dict, g: Geography, fine=None) -> audit.Check:
+def m1_check(ledger: list, ks: dict, g: Geography, fine=None, gap_width: bool | None = None) -> audit.Check:
     """`td.audit.check_m1` on the drawn ledger with `g`'s polygon graph (strict: no display fill),
     on the scenario's fine channels `fine` (`fine_channels`); None, for a run from before #116,
     takes the ledger's, and the summary says so.  A run folder has no units, so the routing of a
-    cell to its planning channel is the run's own scorecard M1's to check."""
+    cell to its planning channel is the run's own scorecard M1's to check.  `gap_width` goes to
+    `check_m1`: None reads `td.audit.GAP_WIDTH_ENV`."""
     cells = [audit.Cell(r["zip_code"], r["current_channel"], r["model_channel"], r["district"],
                         float(r["m_rel"]), reason=r.get("reason", "")) for r in ledger]
     return audit.check_m1(audit.Run(cells, {ch: audit.Channel(k) for ch, k in ks.items()},
-                                    polygon=g.polygon, fine=None if fine is None else tuple(fine)))
+                                    polygon=g.polygon, fine=None if fine is None else tuple(fine)),
+                          gap_width=gap_width)
 
 
+def m1_both(ledger: list, ks: dict, g: Geography, fine=None) -> dict:
+    """M1 both ways (G3, the main-map overnight grid, 2026-10-13): `strict`, necks on polygon
+    borders, and `gap_width`, necks across coverage gaps too (`td.audit.NeckGraph`), each a
+    `m1_check`, and `flips`, one row per district with a neck one way and none the other:
+    {"district": "channel/district", "strict": its neck items, "gap_width": its neck items}."""
+    got = {k: m1_check(ledger, ks, g, fine, gap_width=k == "gap_width") for k in ("strict", "gap_width")}
+    necks = {k: collections.defaultdict(list) for k in got}
+    for k, c in got.items():
+        for i in c.items:
+            if NECK.search(i):
+                necks[k][i.split(":", 1)[0]].append(i)
+    flips = [{"district": d, "strict": necks["strict"].get(d, []), "gap_width": necks["gap_width"].get(d, [])}
+             for d in sorted(set(necks["strict"]) ^ set(necks["gap_width"]))]
+    return {**got, "flips": flips}
+
+
+def write_m1(path: str, both: dict) -> None:
+    """`m1.json`: `m1_both`'s verdicts (status, summary, counts, neck items) and flips."""
+    doc = {k: {"status": c.status, "summary": c.summary, **c.counts,
+               "necks": [i for i in c.items if NECK.search(i)]}
+           for k, c in both.items() if k != "flips"}
+    doc["flips"] = both["flips"]
+    with open(path, "w", encoding="utf-8") as fh:
+        json.dump(doc, fh, indent=1)
+        fh.write("\n")
+
+
 def fine_channels(run_dir: str):
     """The scenario's fine channels from the run's `run.json` (#116), or None without them."""
     path = os.path.join(run_dir, "run.json")
@@ -570,7 +602,8 @@
               f"{s['crowded_states']} + pieces {s['contiguity_weight']:g} ({s['contiguity_pieces']} pieces "
               f"weighing 1 + mass/tau each, on the ledger; M1's piece count {s['audit_pieces']})",
               f"multipart pieces: {s['multipart_pieces']} (listed, not in the defects sum)",
-              f"M1: {s['m1']['status']}: {s['m1']['summary']} (strict, on the ledger)"]
+              f"M1: {s['m1']['status']}: {s['m1']['summary']} (strict, on the ledger, necks "
+              f"{'across coverage gaps' if s['m1'].get('gap_width') else 'on polygon borders'})"]
     lines += [f"    {n}" for n in s["necks"] + s["mass_necks"]]
     lines += [f"shape: extent {s['largest_extent_km']:,.1f} km, {s['states_per_district']} states per district",
               f"balance: worst {100 * s['worst_dev']:.2f}%, mean {100 * s['mean_dev']:.2f}%",
@@ -586,6 +619,8 @@
     ap.add_argument("--extract", help="the extract (default: run.json's source under $TD_REPO)")
     ap.add_argument("--dollars-csv", action="store_true",
                     help="write each main-map run's dollar gate to its dollars.csv")
+    ap.add_argument("--m1-json", action="store_true",
+                    help="write each run's M1, strict and across coverage gaps, to its m1.json")
     a = ap.parse_args(argv)
     rates = rates_of(a.extract) if a.extract else None
     scores = rank([score(d, rates=rates) for d in a.run_dirs])
@@ -593,6 +628,12 @@
         for s in scores:
             if s["dollar_gate"] is not None:
                 write_dollars(os.path.join(s["dir"], "dollars.csv"), s["dollar_gate"])
+    if a.m1_json:
+        for s in scores:
+            with open(os.path.join(s["dir"], "ledger.csv"), newline="") as fh:
+                ledger = list(csv.DictReader(fh))
+            write_m1(os.path.join(s["dir"], "m1.json"),
+                     m1_both(ledger, s["k"], geography(), fine_channels(s["dir"])))
     for s in scores:
         print(report(s), end="\n\n")
     if len(scores) > 1:
```

### Success Criteria:

#### Automated Verification:
- [ ] Slice tests pass: `"$TD_PY" tests/run_all.py -k test_neck_gapwidth.py 2>&1 | tail -1` shows `3 passed, 0 failed`
- [ ] Slice 2's scorer tests still pass with the merged `score.py`: `"$TD_PY" tests/run_all.py -k test_looks_score.py 2>&1 | tail -1` shows `15 passed, 0 failed`
- [ ] M1's other tests are unchanged by the switch: `"$TD_PY" tests/run_all.py -k test_audit.py 2>&1 | tail -1` shows `0 failed`
- [ ] The switch's surface is present: `rg -c '^GAP_WIDTH_ENV = "TD_NECK_GAP_WIDTH"|def __init__\(self, polygon: dict, gap_width: bool = False\)|^def check_m1\(run: Run, gap_width: bool \| None = None\)' td/audit.py` prints 3
- [ ] The scorer's surface is present: `rg -c '^def m1_both|^def write_m1|"--m1-json"' tools/looks/score.py` prints 3
- [ ] Only `d312834` is taken, never `46d2d89` (gap-land builder): `git diff e82d6a4 -- td/geo.py | wc -l` prints 0
- [ ] The default stays off: `rg -n 'GAP_WIDTH_ENV\) == "1"' td/audit.py` prints exactly one line

#### Manual Verification:
- [ ] On m5, `"$TD_PY" tools/looks/score.py <a tier-P main-map run dir> --m1-json` writes `m1.json` with `strict` and `gap_width` verdicts (each with `status`, `summary`, counts, `necks`, `gap_width` false/true) and a `flips` list; the report's M1 line ends "necks on polygon borders", and ends "necks across coverage gaps" when rerun with `TD_NECK_GAP_WIDTH=1`
- [ ] On m5, the same on the TX K3 IFA run of `d312834`'s audit (`runs/exp/contig/nj/_gapwidth_audit.md`): one flip, `IFA/IFA_02`, its strict neck cutting 79718-79734 (6.14 km), none across coverage gaps
- [ ] Every flip on the tier-P folder other than TX El Paso (79718–79734) is noted for MORNING's "Needs your eye" (G3)

---

## Phase 4: #133 land term + land.csv

### Overview
Add a soft in-state land-balance penalty to `draw._solve_group` (`LAND_WEIGHT`, `LAND_MIN_SHARE`, `land_term`, the e-columns and rows with the −(1 − y_{v,k}) relief, `accept` seeding via `land_e`, `Group.land_excess`). Plumb it through `draw` / `_sequential` and `run.py --land-ratio` (including `draw_parallel`'s pickle and contig.json's `land_ratio` / `land_excess`). Add `land.py`, which writes `land.csv`. Repair is untouched. Phase 4 depends only on Phase 1 and can run in parallel with Phases 2–3.

### Changes Required:

#### 1. The land term
**File**: `tools/exp/contig/draw.py` (MODIFY)
**Changes**: A unified diff against HEAD `e82d6a4` (`git apply`). `mip_rel_gap` stays 0.0 (trap 12).

```diff
--- a/tools/exp/contig/draw.py
+++ b/tools/exp/contig/draw.py
@@ -48,6 +48,16 @@
   tie-break at `MOMENT_SHARE` of the shape tier's scale.  `border` is {(a, b) with a < b: km}
   (`border_km`); without it every edge counts 1 km (toys).  Each group reports both terms of its
   drawing (`border_km`, `moment`).  Balance is held by the band, not optimised.
+- **Land balance** (#133, `land`, the main-map overnight grid, 2026-10-13): for each unit of the
+  group with two holders or more planned at `LAND_MIN_SHARE` of τ or more (a unit is a state in
+  every main-map scenario), and each ordered pair (j, k) of them, a continuous excess
+  e ≥ (L_j − R·L_k) / A − (1 − y_{v,k}), L_j being j's land in the unit (its ZCTAs there outside
+  the group plus Σ aland_z · x_{z,j}), A the unit's land and R the ratio: k's land need not reach
+  1/R of j's once k holds none of the unit.  Each e costs `LAND_WEIGHT` over (holders − 1) and
+  over the group's units with the term, so the group's whole land term stays at or below
+  `LAND_WEIGHT`, under one split; a whole unit's excess in a group of one such unit and two
+  holders costs the shape tier's whole scale.  It never makes a group infeasible; each group
+  reports its drawing's Σ e (`land_excess`).
 - **Status per group**: `optimal` (a connected optimum of the complete model at
   `mip_rel_gap = 0`, trap 12), `connected` (connected and feasible, not proved optimal),
   `infeasible` (proved), or `unknown` (a time limit or a restricted model; never infeasible).
@@ -72,6 +82,8 @@
 SHAPE_SCALE = 0.9 * SPLIT_WEIGHT
 AREA_FLOOR = 0.1            # a zero-opportunity ZCTA's weight in the moment term, in m̄
 MOMENT_SHARE = 0.01         # the moment tie-break's scale against the border term's (#121)
+LAND_WEIGHT = SHAPE_SCALE   # the land term's (#133) most per group, below one split
+LAND_MIN_SHARE = 0.20       # #133: a holder counts when it plans this share of τ in the unit
 MASS_TOL = 1e-9
 PHASE1_GAP = 0.05           # the cut loop's absolute gap until a connected drawing exists
 FINAL_ABS_GAP = 1e-6        # then mip_rel_gap = 0 and this absolute gap (trap 12)
@@ -104,6 +116,7 @@
     neck_cuts: int = 0                  # neck cuts added (`NeckCut`, #121)
     necks_cut: list = field(default_factory=list)   # the necks they were cut for
     neck_exempt: list = field(default_factory=list)     # districts whose necks it may keep
+    land_excess: float | None = None    # the drawing's Σ e of the land term (#133); None without it
 
     def report(self) -> dict:
         return {"districts": self.districts, "units": self.units, "free_zctas": self.free,
@@ -113,7 +126,7 @@
                 "bound": self.bound, "gap": self.gap, "note": self.note, "delta": self.delta,
                 "tried": self.tried, "dag": self.dag, "border_km": self.border_km,
                 "moment": self.moment, "neck_cuts": self.neck_cuts, "necks_cut": self.necks_cut,
-                "neck_exempt": self.neck_exempt}
+                "neck_exempt": self.neck_exempt, "land_excess": self.land_excess}
 
 
 @dataclass(frozen=True)
@@ -201,6 +214,13 @@
                      if z < y and y in owner and owner[y] != j)
 
 
+def land_term(polygon: dict, ratio: float, min_share: float = LAND_MIN_SHARE) -> dict:
+    """`draw`'s `land` (#133): {"aland": {zip: km²}, from `geo.polygon_graph`'s m², "ratio": R,
+    "min_share": the share of τ a holder plans in the unit to count}."""
+    return {"aland": {z: a / 1e6 for z, a in polygon["aland"].items()}, "ratio": float(ratio),
+            "min_share": float(min_share)}
+
+
 def components(zs, adj) -> list:
     """Components of `zs` on `adj`, largest first, ties by smallest id."""
     inside, seen, out = set(zs), set(), []
@@ -258,11 +278,12 @@
 def draw(inst, plan, xy: dict, arm: str = "arm1", delta: float | None = None,
          fixed_targets: bool = False, time_limit: float = 600.0, wider=(),
          group_limit: float | None = None, sequential: bool = False, log=print,
-         border: dict | None = None) -> Result:
+         border: dict | None = None, land: dict | None = None) -> Result:
     """The channel's contiguity-aware map (module docstring); `xy` is {zip: (x, y)} in metres.
     A group with no connected drawing in the band of `delta` (the plan's by default) is tried
     again at each wider δ of `wider` in turn (the remedy "a wider internal band", reported per
-    group); each attempt has `group_limit` seconds, all of them `time_limit` together."""
+    group); each attempt has `group_limit` seconds, all of them `time_limit` together.  `land`
+    (`land_term`) adds the land term (#133, module docstring)."""
     if arm not in ARMS:
         raise ValueError(f"arm {arm!r} not in {ARMS}")
     c = plan.channel
@@ -345,7 +366,7 @@
     if sequential:
         return _sequential(inst, plan, c, owner, free, exclave, allowed, hold, planned, support,
                            p, delta, wider, arm, fixed_targets, t_end, group_limit,
-                           fixed_split, share_only, log, border)
+                           fixed_split, share_only, log, border, land)
     for gi, qis in enumerate(sorted(groups.values(), key=lambda g: -sum(len(fcomps[q]) for q in g))):
         zs = sorted(z for q in qis for z in fcomps[q])
         tried, g = [], None
@@ -357,7 +378,7 @@
             r = _solve_group(c, zs, allowed, bodies, body_of, fixed, adj, m, p, unit_of, hold,
                              plan, planned, support, inst, ch.tau * (1 - d), ch.tau * (1 + d),
                              arm, fixed_targets, min(left, group_limit or left), log, dag=dag,
-                             start=seed, border=border)
+                             start=seed, border=border, land=land)
             log(f"  {c} group {gi} at δ = {d:g}{' (dag)' if dag else ''}: {len(r.districts)} "
                 f"districts, {r.free} free ZCTAs, {r.columns} columns -> {r.status} in "
                 f"{r.seconds:.1f}s, {r.iterations} solves, {r.cuts} cuts"
@@ -403,7 +424,7 @@
 
 def _sequential(inst, plan, c, owner, free, exclave, allowed, hold, planned, support, p, delta,
                 wider, arm, fixed_targets, t_end, group_limit, fixed_split, share_only, log,
-                border=None):
+                border=None, land=None):
     """The sequential restriction (`draw(sequential=True)`): one split unit at a time (adjacent
     split units together when one district enters the second only through the first), each
     district's ZCTAs in the unit attached to what it already owns next to the unit (its whole
@@ -466,7 +487,7 @@
             r = _solve_group(c, zs, allowed, bodies, body_of, owner, adj, m, p, unit_of, hold,
                              plan, planned, support, inst, ch.tau * (1 - d), ch.tau * (1 + d),
                              arm, fixed_targets, min(left, group_limit or left), log, extra,
-                             dag=dag, start=seed, sequential=True, border=border)
+                             dag=dag, start=seed, sequential=True, border=border, land=land)
             log(f"  {c} unit {v} at δ = {d:g}{' (dag)' if dag else ''}: {len(r.districts)} "
                 f"districts, {r.free} ZCTAs -> {r.status} in {r.seconds:.1f}s, "
                 f"{r.iterations} solves, {r.cuts} cuts{(' (' + r.note + ')') if r.note else ''}")
@@ -748,7 +769,7 @@
                  extra: dict | None = None, dag: bool = False, start: dict | None = None,
                  count: dict | None = None, layers: bool = False, flow: bool = False,
                  sequential: bool = False, border: dict | None = None, necks=None,
-                 neck_seed: dict | None = None) -> Group:
+                 neck_seed: dict | None = None, land: dict | None = None) -> Group:
     """One group's MILP and cut loop (module docstring).  `count` is the window repair's
     (`repair.py`): {"current": {unit: its holders on the drawn map}, "cap": bool}; then split
     units come first in the objective, holders (cuts) second, shape third, and with "cap" neither
@@ -760,7 +781,8 @@
     only checks).  With `sequential` (`_sequential`) a district whose fixed mass and `extra` are
     already past the band takes nothing more instead of being forced back; otherwise such a
     district makes the group infeasible, since its mass outside the group cannot change.  `border`
-    is the shape term's {(a, b) with a < b: km} (module docstring).
+    is the shape term's {(a, b) with a < b: km} and `land` the land term's (`land_term`; both in
+    the module docstring).
 
     With `necks` (#121, the window repair's neck-aware solve), a callable taking a drawing {group
     ZCTA: district} to ([NeckCut], [the necks it must lose]), the loop also cuts necks: a connected
@@ -861,6 +883,24 @@
             held_by[v] = {fixed[y] for y in units.zips.get(v, ()) if y in fixed}
             scol[v] = len(cost)
             cost.append(big)
+    lcol, lunit = {}, {}        # the land term (#133): (unit, j, k) -> e; unit -> (A, {j: fixed km²})
+    if land is not None:
+        aland, ratio = land["aland"], float(land["ratio"])
+        floor_ = float(land.get("min_share", LAND_MIN_SHARE)) * ch.tau - MASS_TOL * max(1.0, ch.tau)
+        terms = []
+        for v in sorted({unit_of[z] for z in zs}):
+            area = math.fsum(aland.get(z, 0.0) for z in units.zips[v])
+            hs = [j for j in js if (v, j) in ycol and planned.get((v, j), 0.0) >= floor_]
+            if area > 0 and len(hs) > 1:
+                terms.append((v, area, hs))
+        for v, area, hs in terms:
+            lunit[v] = (area, {j: math.fsum(aland.get(z, 0.0) for z in units.zips[v]
+                                            if fixed.get(z) == j and z not in zset) for j in hs})
+            for j in hs:
+                for k in hs:
+                    if j != k:
+                        lcol[v, j, k] = len(cost)
+                        cost.append(LAND_WEIGHT / ((len(hs) - 1) * len(terms)))
     fcol = {}                   # (district, a, b) -> flow on the arc a -> b
     if flow:
         for j in sorted(root):
@@ -877,7 +917,7 @@
     if THREADS is not None:
         h.setOptionValue("threads", THREADS)
     inf = highspy.kHighsInf
-    fset = set(fcol.values()) | set(ccol.values())
+    fset = set(fcol.values()) | set(ccol.values()) | set(lcol.values())
     cap_of = {j: 1 + sum(1 for z in zs if j in allowed[z]) + sum(1 for k in vert_of.values() if k == j)
               for j in root} if flow else {}
     ub = np.ones(n)
@@ -914,6 +954,16 @@
         if sequential:          # a district already past the band is not forced back
             a, b = max(0.0, a), max(0.0, b)
         row(a, b, idx, [m[z] for z in zs if (z, j) in col and m.get(z, 0.0) > 0])
+    for (v, j, k), e in lcol.items():   # e ≥ (L_j − R·L_k) / A − (1 − y_{v,k})
+        area, held = lunit[v]
+        idx, val = [e, ycol[v, k]], [1.0, -1.0]
+        for z in zs:
+            if unit_of[z] == v and aland.get(z, 0.0) > 0:
+                for d, w in ((j, -1.0), (k, ratio)):
+                    if (z, d) in col:
+                        idx.append(col[z, d])
+                        val.append(w * aland[z] / area)
+        row((held[j] - ratio * held[k]) / area - 1.0, inf, idx, val)
     if flow:                    # into a vertex only when j owns it; each consumes one unit
         into, out_ = collections.defaultdict(list), collections.defaultdict(list)
         for (j, a, b), k in fcol.items():
@@ -1067,6 +1117,18 @@
     found = None                # the best connected drawing: (owner, objective, bound)
     target = {cp.name: cp.total for cp in plan.copies}
     tol = 1e-7 * max(1.0, hi)
+    lzs = {v: [z for z in zs if unit_of[z] == v] for v in lunit}
+
+    def land_e(own: dict) -> dict:
+        """{(unit, j, k): e} of a drawing `own` {group ZCTA: district}, each e at its least."""
+        out = {}
+        for v, j, k in lcol:
+            area, held = lunit[v]
+            got = {d: held[d] + math.fsum(aland.get(z, 0.0) for z in lzs[v] if own.get(z) == d)
+                   for d in (j, k)}
+            has_k = any(own.get(z) == k for z in lzs[v])
+            out[v, j, k] = max(0.0, (got[j] - ratio * got[k]) / area - (0.0 if has_k else 1.0))
+        return out
 
     def accept(start, how):
         """Keep `start` (a connected drawing) when it meets every row and beats `found`."""
@@ -1088,6 +1150,8 @@
                                             if u == v and x0[i] > 0.5}) > 1)
         for (z, y), k in ccol.items():
             x0[k] = float(start[z] != start[y])
+        for key, e in land_e(start).items():
+            x0[lcol[key]] = e
         for j in sorted(root) if fcol else ():     # a BFS tree's subtree sizes from the root
             mine = {z for z, k in start.items() if k == j} | {b for b, k in vert_of.items() if k == j}
             up, order = {root[j]: None}, [root[j]]
@@ -1250,6 +1314,8 @@
         g.border_km = math.fsum(km(z, y) for z in zs for y in adj[z]
                                 if y in own and own[y] != own[z] and (y not in zset or z < y))
         g.moment = math.fsum(moment[col[z, j]] for z, j in g.owner.items())
+        if land is not None:
+            g.land_excess = math.fsum(land_e(g.owner).values())
     g.dag = dag
     g.rows = nrows
     g.seconds = time.time() - t0
```

#### 2. The flag
**File**: `tools/exp/contig/run.py` (MODIFY)
**Changes**: A unified diff against HEAD `e82d6a4` (`git apply`): `--land-ratio`, the `land` dict passed to `draw` and `draw_parallel`, and the contig.json fields.

```diff
--- a/tools/exp/contig/run.py
+++ b/tools/exp/contig/run.py
@@ -5,6 +5,7 @@
     "$TD_PY" -u tools/exp/contig/run.py <spec.toml> --out <dir> [--extract PATH]
         [--arm arm1|band|split|move] [--fixed-targets] [--sequential] [--time-limit S]
         [--group-limit S] [--plans PATH] [--plans-file PKL] [--parent RUN] [--maps] [--jobs N]
+        [--land-ratio R]
 
 Or as the `contig` formulation of `tools/exp/sweep.py` (#92's tracker): params `scenario`,
 `arm`, `time_limit` (seconds per channel), `group_limit`, `fixed_targets`, `sequential`, `plans`.
@@ -32,6 +33,10 @@
 (`draw._sequential`, adjacent units together when one district enters the second only through
 the first), for coupled groups too large to solve jointly: neither a restriction nor a relaxation
 of the joint model, so only the audit's M1 judges its maps, and its failures prove nothing.
+`--land-ratio R` adds the draw's land term (#133, `draw.land_term` on the polygon graph's land,
+the main-map overnight grid at R = 10): in each split state the land of a holder planned at
+`draw.LAND_MIN_SHARE` of τ or more is held within R of every other's, a soft penalty below one
+split; `contig.json` records R (`land_ratio`) and each channel's Σ excess (`land_excess`).
 
 `contig.json` holds what #109 reports per channel: each group's size, solve status ("optimal"
 is proved, "connected" is connected and feasible, "infeasible" is proved, "unknown" is the time
@@ -151,7 +156,7 @@
                group_limit: float | None = None, plans_cache: str | None = None,
                source: str = "", keep=(), maps: bool = False, sequential: bool = False,
                delta: float | None = None, log=print, plans_file: str | None = None,
-               jobs: int = 1) -> dict:
+               jobs: int = 1, land_ratio: float | None = None) -> dict:
     if arm not in ARMS:
         raise ValueError(f"arm {arm!r} not in {ARMS}")
     s = tdspec.load(spec_path)
@@ -181,10 +186,12 @@
     state = dict(zip(rows.index, rows["state"]))
     connectors = set(geo.approved_connectors(geo.read_connectors()))
     border = draw.border_km(polygon)
+    land = None if land_ratio is None else draw.land_term(polygon, land_ratio)
     contig, drawings = {}, {}
     drawn = {}
     if jobs > 1:
-        drawn = draw_parallel(inst, plans, xy, jobs, border, arm="arm1" if arm == "band" else arm,
+        drawn = draw_parallel(inst, plans, xy, jobs, border, land=land,
+                              arm="arm1" if arm == "band" else arm,
                               fixed_targets=fixed_targets, time_limit=time_limit,
                               wider=WIDER if arm == "band" else (), group_limit=group_limit,
                               sequential=sequential, delta=delta)
@@ -194,7 +201,7 @@
         res = drawn[c] if c in drawn else draw.draw(
             inst, p, xy, arm="arm1" if arm == "band" else arm, fixed_targets=fixed_targets,
             time_limit=time_limit, wider=WIDER if arm == "band" else (), group_limit=group_limit,
-            sequential=sequential, delta=delta, log=log, border=border)
+            sequential=sequential, delta=delta, log=log, border=border, land=land)
         fallback = None
         if res.undrawn:
             fallback = realize.realize(inst, p, xy)
@@ -209,12 +216,14 @@
                                       default=p.delta),
             "fixed_split": res.fixed_split, "share_only": res.share_only,
             "shape": shape_terms(res.groups),
+            "land_excess": None if land is None else math.fsum(g.land_excess or 0.0 for g in res.groups),
             **drawn_stats(inst, p, d, connectors, res.connected, border)}
     report, m1 = write_folder(out, s, inst, ext, ref, polygon, plans, reports, drawings,
                               f"{s.name} (contig {arm}, {source or 'extract'})",
                               f"tools/exp/contig ({arm})", source, maps)
     doc = {"scenario": s.name, "arm": arm, "fixed_targets": fixed_targets,
            "sequential": sequential, "internal_delta": delta, "plans_file": plans_file,
+           "land_ratio": land_ratio,
            "plan_seconds": round(plan_seconds, 1), "m1": report["m1"], "channels": contig}
     with open(os.path.join(out, "contig.json"), "w", encoding="utf-8") as fh:
         json.dump(doc, fh, indent=2, sort_keys=True)
@@ -342,6 +351,7 @@
         pin_threads()
         c, kw = conn.recv()
         conn.send(("done", draw.draw(sh["inst"], sh["plans"][c], sh["xy"], border=sh["border"],
+                                     land=sh.get("land"),
                                      log=lambda line: log and print(line, flush=True), **kw)))
     except BaseException:
         conn.send(("error", traceback.format_exc()))
@@ -349,11 +359,11 @@
 
 
 def draw_parallel(inst, plans: dict, xy: dict, jobs: int, border=None, log: bool = True,
-                  **kw) -> dict:
+                  land: dict | None = None, **kw) -> dict:
     """{channel: `draw.Result`} of `draw.draw` with `kw`, each channel in its own process, at
     most `jobs` at once (#123): a channel's drawing reads only its own plan, so the dict is the
     sequential loop's whenever no solve stops on a time limit.  With `log` false the processes
-    print nothing."""
+    print nothing.  `border` and `land` (`draw.land_term`) travel in the shared pickle."""
     import shutil
     import tempfile
     from multiprocessing.connection import wait
@@ -362,7 +372,7 @@
     try:
         shared = os.path.join(tmp, "shared.pkl")
         with open(shared, "wb") as fh:
-            pickle.dump({"inst": inst, "plans": plans, "xy": xy, "border": border}, fh,
+            pickle.dump({"inst": inst, "plans": plans, "xy": xy, "border": border, "land": land}, fh,
                         protocol=pickle.HIGHEST_PROTOCOL)
         while todo or running:
             while todo and len(running) < jobs:
@@ -528,7 +538,7 @@
                bool(p.get("fixed_targets", False)), float(p.get("time_limit", 900)),
                p.get("group_limit"), p.get("plans"), m["provenance"]["instance"],
                keep=tuple(os.listdir(folder)), maps=bool(p.get("maps", False)),
-               sequential=bool(p.get("sequential", False)))
+               sequential=bool(p.get("sequential", False)), land_ratio=p.get("land_ratio"))
 
 
 def main(argv=None) -> int:
@@ -552,6 +562,9 @@
                     help="processes (#123): each channel drawn in its own, at most this many at "
                          "once; 1 is the sequential loop")
     ap.add_argument("--maps", action="store_true")
+    ap.add_argument("--land-ratio", type=float, default=None,
+                    help="#133's R: hold each split state's in-state land ratio within R (soft, "
+                         "draw.land_term); off by default")
     a = ap.parse_args(argv)
     params = {k: v for k, v in vars(a).items() if k not in ("spec", "out")}
     params["plan"] = spec_plan(a.spec)
@@ -561,7 +574,7 @@
         doc = contig_run(a.spec, a.extract, a.out, a.arm, a.fixed_targets, a.time_limit,
                          a.group_limit, a.plans, os.path.basename(a.extract), maps=a.maps,
                          sequential=a.sequential, delta=a.delta, plans_file=a.plans_file,
-                         keep=("manifest.json",), jobs=a.jobs)
+                         keep=("manifest.json",), jobs=a.jobs, land_ratio=a.land_ratio)
     except Exception as e:
         write_manifest(a.out, "contig", a.spec, a.extract, params, status="failed",
                        stop_reason=f"{type(e).__name__}: {e}")
```

#### 3. land.csv
**File**: `tools/exp/contig/land.py` (NEW)
**Changes**: `land_rows`, `write_land`, `summary`, and a CLI over run folders.

```python
"""land.py -- #133's land balance on run folders (the main-map overnight grid, 2026-10-13):
each folder's `land.csv`, one row per split group, a planning channel's districts owning ZCTAs in
one state when there are two or more, with the in-state land ratio, largest over smallest, over
the pieces holding at least `MIN_SHARE` of their district's mass, against R.

    "$TD_PY" tools/exp/contig/land.py <run_dir>... [--ratio R]

The ratio over every piece (`ratio_all`) is listed beside it: a sliver holding little of its
district's mass is no territory to balance (#133 step 1: NY national 870 over all pieces, 31 over
those of 20% or more).  Land is the gazetteer's (`geo.polygon_graph`'s `aland`, in km²), each
ZCTA counted once per channel however many fine channels it carries; mass is the ledger's, `m_rel`
or $M on a dollar run (a share is a ratio either way).  The draw holds the ratio softly
(`draw.py`'s land term, `run.py --land-ratio`); the repair keeps its own objective, so a
repaired folder's `land.csv` reports what it moved.
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import geo  # noqa: E402

RATIO = 10.0            # #133's R for the overnight grid (owner decision open, 2026-10-13)
MIN_SHARE = 0.20        # a piece counts when it holds this share of its district's mass
COLUMNS = ["channel", "state", "districts", "pieces", "ratio", "ratio_all", "largest", "largest_km2",
           "smallest", "smallest_km2", "over", "detail"]


def land_rows(ledger: list, aland: dict, ratio: float = RATIO, min_share: float = MIN_SHARE) -> list:
    """One row per split group of the ledger, sorted by (channel, state): `districts` and
    `pieces` (those of `min_share` or more) counted, `ratio` the largest piece's land over the
    smallest's among `pieces` (None below two), `ratio_all` over every piece, `largest` and
    `smallest` the two districts of `ratio` (else of `ratio_all`) with their km², `over` when
    `ratio` exceeds R, and `detail` [(district, km², share)] by land, largest first.  `aland` is
    {zip: km²}."""
    owned = set()                                   # (channel, district, state, zip)
    mass, total = collections.Counter(), collections.Counter()
    for r in ledger:
        d = r["district"]
        if not d:
            continue
        ch, s = r["model_channel"], r["state"]
        owned.add((ch, d, s, r["zip_code"]))
        m = float(r["m_rel"] or 0.0)
        mass[ch, d, s] += m
        total[ch, d] += m
    land = collections.Counter()
    groups = collections.defaultdict(set)
    for ch, d, s, z in owned:
        land[ch, d, s] += aland.get(z, 0.0)
        groups[ch, s].add(d)
    out = []
    for (ch, s), ds in sorted(groups.items()):
        if len(ds) < 2:
            continue
        detail = sorted(((d, land[ch, d, s], mass[ch, d, s] / total[ch, d] if total[ch, d] else 0.0)
                         for d in ds), key=lambda p: (-p[1], p[0]))
        big = [p for p in detail if p[2] >= min_share]
        use = big if len(big) > 1 else detail
        r_big = big[0][1] / max(big[-1][1], 1e-9) if len(big) > 1 else None
        out.append({"channel": ch, "state": s, "districts": len(ds), "pieces": len(big),
                    "ratio": r_big, "ratio_all": detail[0][1] / max(detail[-1][1], 1e-9),
                    "largest": use[0][0], "largest_km2": use[0][1],
                    "smallest": use[-1][0], "smallest_km2": use[-1][1],
                    "over": r_big is not None and r_big > ratio, "detail": detail})
    return out


def write_land(path: str, rows: list) -> None:
    """`land.csv`: the `land_rows`, km² to 0.1, ratios to 0.01, `detail` as district:km²:share%."""
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([r["channel"], r["state"], r["districts"], r["pieces"],
                        "" if r["ratio"] is None else f"{r['ratio']:.2f}", f"{r['ratio_all']:.2f}",
                        r["largest"], f"{r['largest_km2']:.1f}", r["smallest"], f"{r['smallest_km2']:.1f}",
                        int(r["over"]),
                        ";".join(f"{d}:{a:.1f}:{100 * x:.0f}%" for d, a, x in r["detail"])])


def summary(name: str, rows: list, ratio: float = RATIO) -> str:
    """One line per folder: split groups, those with two pieces or more, and those beyond R."""
    over = [r for r in rows if r["over"]]
    head = (f"{name}: {len(rows)} split groups, {sum(r['ratio'] is not None for r in rows)} with two "
            f"pieces of {100 * MIN_SHARE:.0f}% or more, {len(over)} beyond R = {ratio:g}")
    return head + "".join(f"; {r['channel']} {r['state']} {r['ratio']:.1f}" for r in over)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--ratio", type=float, default=RATIO, help="#133's R")
    a = ap.parse_args(argv)
    aland = {z: x / 1e6 for z, x in geo.polygon_graph()["aland"].items()}
    for d in a.run_dirs:
        with open(os.path.join(d, "ledger.csv"), newline="") as fh:
            rows = land_rows(list(csv.DictReader(fh)), aland, a.ratio)
        write_land(os.path.join(d, "land.csv"), rows)
        print(summary(os.path.basename(os.path.normpath(d)), rows, a.ratio))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

#### 4. Tests
**File**: `tests/test_land.py` (NEW)
**Changes**: `land_rows` and `write_land` by hand. On the toy MILP, the term holds the ratio (also `--sequential` and `draw_parallel`), never makes a group infeasible, and `land_term` converts to km².

```python
"""#133's land balance (the main-map overnight grid, 2026-10-13): `land.py`'s split-group rows
by hand, `land.csv`, and `draw.py`'s land term on a toy MILP, a drawing the border term alone
leaves unbalanced held to R, every seed meeting the new rows, never infeasible."""
from __future__ import annotations

import csv
import importlib.util
import os
import sys
import tempfile

from tests import test_realize as tr

HERE = os.path.dirname(os.path.abspath(__file__))


def _module(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(HERE, "..", "tools", "exp", "contig", file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


land = _module("contig_land", "land.py")
draw = _module("contig_draw", "draw.py")


def _ledger(cells) -> list:
    """Ledger rows from (ZIP, fine channel, state, planning channel, district, mass)."""
    return [{"zip_code": z, "current_channel": f, "state": s, "model_channel": ch, "district": d,
             "m_rel": repr(float(m))} for z, f, s, ch, d, m in cells]


def test_land_rows_by_hand():
    """A: X_01 (land 100) against X_02 (5 + 3, two fine channels on one ZIP counted once): 12.5,
    beyond R = 10; X_03's sliver (0.5 km², 10% of its mass) is no piece but counts in `ratio_all`.
    B: one piece of 20% or more, no ratio.  C is whole, no row; Y's unowned cell is skipped."""
    aland = {"a1": 100.0, "a2": 5.0, "a3": 3.0, "a4": 0.5, "b1": 40.0, "b2": 2.0, "c1": 7.0}
    led = _ledger([("a1", "wh", "A", "X", "X_01", 6.0), ("a2", "wh", "A", "X", "X_02", 2.0),
                   ("a2", "fi", "A", "X", "X_02", 1.0), ("a3", "wh", "A", "X", "X_02", 1.0),
                   ("a4", "wh", "A", "X", "X_03", 1.0), ("b1", "wh", "B", "X", "X_03", 9.0),
                   ("b2", "wh", "B", "X", "X_01", 0.5), ("c1", "wh", "C", "X", "X_01", 3.5),
                   ("c1", "fi", "C", "Y", "", 1.0)])
    a, b = land.land_rows(led, aland)
    assert (a["channel"], a["state"], a["districts"], a["pieces"]) == ("X", "A", 3, 2)
    assert (a["largest"], a["largest_km2"], a["smallest"], a["smallest_km2"]) == ("X_01", 100.0, "X_02", 8.0)
    assert a["ratio"] == 12.5 and a["ratio_all"] == 200.0 and a["over"]
    assert a["detail"] == [("X_01", 100.0, 0.6), ("X_02", 8.0, 1.0), ("X_03", 0.5, 0.1)]
    assert (b["state"], b["pieces"], b["ratio"], b["over"]) == ("B", 1, None, False)
    assert (b["largest"], b["smallest"], b["ratio_all"]) == ("X_03", "X_01", 20.0)
    assert land.land_rows(led, aland, ratio=12.5)[0]["over"] is False
    assert land.summary("run", [a, b]) == ("run: 2 split groups, 1 with two pieces of 20% or more, "
                                           "1 beyond R = 10; X A 12.5")


def test_write_land():
    aland = {"a1": 100.0, "a2": 8.0}
    rows = land.land_rows(_ledger([("a1", "wh", "A", "X", "X_01", 1.0),
                                   ("a2", "wh", "A", "X", "X_02", 1.0)]), aland)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "land.csv")
        land.write_land(path, rows)
        with open(path, newline="") as fh:
            got = list(csv.reader(fh))
    assert got == [land.COLUMNS, ["X", "A", "2", "2", "12.50", "12.50", "X_01", "100.0", "X_02", "8.0",
                                  "1", "X_01:100.0:100%;X_02:8.0:100%"]]


def _grid_toy():
    """NY is a 4 × 3 grid of free ZCTAs of mass 1, CT's a0 (mass 2) on the left column and NJ's b0
    (4.6) on the right (`_finger_toy`'s), every edge 1 km; the left column holds 10 km² a ZCTA,
    the rest 1.  CT plans 7/12 of NY, NJ 5/12, both past `LAND_MIN_SHARE` of τ."""
    pts = [(x, y) for x in range(4) for y in range(3)]
    name = {q: f"v{q[0]}{q[1]}" for q in pts}
    edges = [(name[a], name[b]) for a in pts for b in pts
             if a < b and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
    edges += [("a0", name[0, y]) for y in range(3)] + [("b0", name[3, y]) for y in range(3)]
    xy = {name[q]: (float(q[0]), float(q[1])) for q in pts}
    xy.update({"a0": (-1.0, 1.0), "b0": (4.0, 1.0)})
    mass = dict.fromkeys(xy, 1.0)
    mass.update({"a0": 2.0, "b0": 4.6})
    inst, xym = tr._toy({"NY": [name[q] for q in pts], "CT": ["a0"], "NJ": ["b0"]}, edges, mass,
                        xy, {"NY": "free"}, k=2, delta=0.15, final_delta=0.15)
    plan = tr._plan(inst, [({"CT", "NY"}, {"CT": 1.0, "NY": 7 / 12}),
                           ({"NJ", "NY"}, {"NJ": 1.0, "NY": 5 / 12})])
    aland = {z: 10.0 if z.startswith("v0") else 1.0 for z in xy}
    return inst, xym, plan, aland


def _ny_land(inst, owner: dict, aland: dict) -> dict:
    out = {}
    for z in inst.units.zips["NY"]:
        out[owner[z]] = out.get(owner[z], 0.0) + aland[z]
    return out


def _brute(inst, plan, aland, ratio) -> tuple:
    """(least border, least |CT − NJ| land) over every connected drawing of NY in the band, the
    border among those within `ratio` both ways."""
    units, ch = inst.units, inst.channels["X"]
    adj, m = units.zip_adj, ch.m
    ny = sorted(units.zips["NY"])
    names = {next(iter(cp.support - {"NY"})): cp.name for cp in plan.copies}
    lo, hi = ch.tau * (1 - plan.delta), ch.tau * (1 + plan.delta)
    best, diff = float("inf"), float("inf")
    for mask in range(2 ** len(ny)):
        owner = {"a0": names["CT"], "b0": names["NJ"]}
        owner.update({z: names["CT"] if mask >> i & 1 else names["NJ"] for i, z in enumerate(ny)})
        mass = {}
        for z, j in owner.items():
            mass[j] = mass.get(j, 0.0) + m.get(z, 0.0)
        if not all(lo - 1e-9 <= x <= hi + 1e-9 for x in mass.values()) or len(mass) < 2:
            continue
        if any(len(draw.components({z for z in owner if owner[z] == j}, adj)) > 1 for j in mass):
            continue
        got = _ny_land(inst, owner, aland)
        a, b = got.get(names["CT"], 0.0), got.get(names["NJ"], 0.0)
        diff = min(diff, abs(a - b))
        if a <= ratio * b and b <= ratio * a:
            best = min(best, sum(1 for x in owner for y in adj[x] if x < y and owner[x] != owner[y]))
    return best, diff


def test_the_land_term_holds_the_in_state_ratio():
    """Without the term the least border gives CT both heavy columns (33 km² against 6, 5.5); at
    R = 2 the drawing is within R, its border the least of those within R and its excess 0; every
    seed drawing meets the land rows (none "breaks a row")."""
    inst, xy, plan, aland = _grid_toy()
    ct, nj = sorted(cp.name for cp in plan.copies)
    [g0] = draw.draw(inst, plan, xy, log=lambda *_: None).groups
    assert g0.status == "optimal" and g0.land_excess is None and g0.report()["land_excess"] is None
    assert _ny_land(inst, g0.owner, aland) == {ct: 33.0, nj: 6.0}
    lines = []
    res = draw.draw(inst, plan, xy, log=lines.append,
                    land={"aland": aland, "ratio": 2.0, "min_share": draw.LAND_MIN_SHARE})
    [g] = res.groups
    assert g.status == "optimal" and res.connected, (g.status, g.note)
    got = _ny_land(inst, g.owner, aland)
    assert got[ct] <= 2.0 * got[nj] and got[nj] <= 2.0 * got[ct], got
    assert abs(g.land_excess) < 1e-9 and g.report()["land_excess"] == g.land_excess
    assert g.border_km == _brute(inst, plan, aland, 2.0)[0] > g0.border_km
    assert not any("breaks a row" in line for line in lines), [l for l in lines if "breaks" in l]
    seq = draw.draw(inst, plan, xy, sequential=True, log=lambda *_: None,
                    land={"aland": aland, "ratio": 2.0, "min_share": draw.LAND_MIN_SHARE})
    [gs] = seq.groups                   # set125's `--sequential`: one unit, the same rows
    got = _ny_land(inst, seq.owner, aland)
    assert gs.status == "connected" and abs(gs.land_excess) < 1e-9 and got[ct] <= 2.0 * got[nj], got


def test_the_land_term_never_makes_a_group_infeasible():
    """R = 1 asks for equal land, which no drawing has: the group is still drawn, optimal, its
    excess that of its drawing (|CT − NJ| over NY's 39 km²); with `min_share` above both plans no
    pair counts and the excess is 0."""
    inst, xy, plan, aland = _grid_toy()
    ct, nj = sorted(cp.name for cp in plan.copies)
    [g0] = draw.draw(inst, plan, xy, log=lambda *_: None).groups
    [g] = draw.draw(inst, plan, xy, log=lambda *_: None,
                    land={"aland": aland, "ratio": 1.0, "min_share": 0.2}).groups
    assert g.status == "optimal"
    got = _ny_land(inst, g.owner, aland)
    assert abs(g.land_excess - abs(got[ct] - got[nj]) / 39.0) < 1e-9 and g.land_excess > 0
    assert _brute(inst, plan, aland, 1.0)[1] > 0
    [g2] = draw.draw(inst, plan, xy, log=lambda *_: None,
                     land={"aland": aland, "ratio": 1.0, "min_share": 0.9}).groups
    assert g2.status == "optimal" and g2.land_excess == 0.0 and g2.owner == g0.owner


def test_channels_drawn_in_parallel_carry_the_land_term():
    """`run.draw_parallel` passes `land` to each worker in the shared pickle (#123): the drawing
    is the in-process one, within R."""
    run = _module("contig_run", "run.py")
    inst, xy, plan, aland = _grid_toy()
    term = {"aland": aland, "ratio": 2.0, "min_share": draw.LAND_MIN_SHARE}
    seq = draw.draw(inst, plan, xy, log=lambda *_: None, land=term)
    par = run.draw_parallel(inst, {"X": plan}, xy, 2, log=False, land=term)
    assert par["X"].owner == seq.owner and abs(par["X"].groups[0].land_excess) < 1e-9


def test_land_term_reads_the_polygon_graph_in_km2():
    poly = {"aland": {"a": 2.5e6, "b": 0.0}}
    assert draw.land_term(poly, 10) == {"aland": {"a": 2.5, "b": 0.0}, "ratio": 10.0,
                                        "min_share": draw.LAND_MIN_SHARE}
```

### Success Criteria:

#### Automated Verification:
- [ ] Slice tests pass: `"$TD_PY" tests/run_all.py -k test_land.py 2>&1 | tail -1` shows `6 passed, 0 failed`
- [ ] The realizer's other tests still pass: `"$TD_PY" tests/run_all.py -k test_contig_realize.py 2>&1 | tail -1` shows `0 failed`
- [ ] Trap 12 holds: `rg -n 'mip_rel_gap' tools/exp/contig/draw.py` shows only `0.0`
- [ ] The term's surface is present: `rg -c '^LAND_WEIGHT = |^LAND_MIN_SHARE = |^def land_term' tools/exp/contig/draw.py` prints 3, and `rg -c '"--land-ratio"' tools/exp/contig/run.py` prints 1
- [ ] Repair keeps its objective: `git diff e82d6a4 -- tools/exp/contig/repair.py | wc -l` prints 0

#### Manual Verification:
- [ ] On m5, `"$TD_PY" tools/exp/contig/land.py $TD_REPO/runs/exp/contig/border/ne_plains_wh11` writes land.csv and prints 14 split groups, 13 with two pieces of 20% or more, 5 beyond R = 10 (national CA 32.1, national NY 31.2, FI NY 30.7, FI PA 20.5, WH PA 12.1), research §8's figures
- [ ] A smoke draw of one main-map spec with `--land-ratio 10` records `land_ratio` 10 and each channel's `land_excess` in contig.json, and draws no more split units than the same draw without it
- [ ] The same smoke draw's `run.json` `source` is `instance_descaled_usd.json.gz` and its `manifest.json` `provenance.instance_sha256` equals `shasum -a 256 "$TD_REPO/instance_descaled_usd.json.gz"` (a $M ledger traces back to its extract)

---

## Phase 5: Grid launcher core

### Overview
The `run` subcommand of `tools/exp/contig/overnight.py`. It covers `POINTS` (21), `STRUCTURES`, `fit_delta` / `plan_point` (D9, D10), `point_spec_text`, the set125 chain run as child processes in their own process groups, the trap-15 draw retry (`RETRY_ON`), repair pass 2 only when the G3 gate fails, labels (`label_of`), the dollar re-run (`rerun_k`, D13), the first-fit `schedule`, and an atomic, resumable `GRID.json`. Phase 6 extends the same file with `collect`, `morning` and `smoke`. Here the file holds only the `run` parts, so its parser offers `{run}` alone.

### Changes Required:

#### 1. The launcher (run)
**File**: `tools/exp/contig/overnight.py` (NEW)
**Changes**: The design's fence minus Slice 6's parts:
- the docstring's usage lines and paragraphs for `collect`, `morning` and `smoke`;
- the `resource`, `shlex`, `socket` and `textwrap` imports;
- the `CHANNELS`, `STAGES`, `RENDER_S`, `EL_PASO`, `MEM_GIB` and `PDF_PAGE` constants;
- `_render`;
- the `collect`, `morning` and `smoke` sections;
- their subparsers.

```python
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
```

#### 2. Tests
**File**: `tests/test_overnight.py` (NEW)
**Changes**: The design's twelve Slice 5 tests: the δ fit, the plan rule, the spec copy, the retry, labels, the re-run direction, the dollar and score readers, the scheduler, a stage's kill, resume, GRID.json, and the commands' flags.

```python
"""tools/exp/contig/overnight.py (the main-map overnight grid, 2026-10-13) on toy specs and
hand-computed values: the δ fit, the split rule, the spec copy, the retry, labels, the re-run
direction, the scheduler, a stage's kill, the resume helpers and GRID.json."""
from __future__ import annotations

import collections
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import tomllib

from td import spec as tdspec

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "contig_overnight", os.path.join(HERE, "..", "tools", "exp", "contig", "overnight.py"))
overnight = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(overnight)
score = overnight.score

TOY = """[scenario]
name = "toy"
fine_channels = ["national_chase", "wh"]
planned_elsewhere = ["career", "edj", "fi", "ifa", "imo", "priafs", "wells_fi", "wells_wh"]

[channels.national]
k = 2
domain = [{ units = "all", fine = ["national_chase"] }]
mode = "whole"
free = ["CA"]
eta = 0.05
delta = 0.1

[channels.WIFI]
k = 2
domain = [{ units = "all", fine = ["wh"] }]
mode = "whole"
eta = 0.05
"""
CELLS = {("CA", "national_chase"): 1500.0, ("TX", "national_chase"): 700.0,
         ("NY", "national_chase"): 300.0, ("CA", "wh"): 1000.0, ("TX", "wh"): 900.0}


def _toy():
    return tdspec.parse(tomllib.loads(TOY))


def test_fit_delta_by_hand():
    assert overnight.fit_delta(1207.0, 14, 1000.0, 1437.5) == 0.1714      # 207 / 1207 = 0.17150
    assert overnight.fit_delta(950.0, 2, 850.0, 1150.0) == 0.1052         # 100 / 950 = 0.10526
    assert overnight.fit_delta(1543.0, 1, 850.0, 1600.0) == overnight.K1_FINAL_DELTA
    assert overnight.fit_delta(1700.0, 1, 850.0, 1600.0) is None
    assert overnight.fit_delta(850.0, 3, 850.0, 1150.0) is None           # on the edge: no band
    assert overnight.fit_delta(800.0, 3, 850.0, 1150.0) is None


def test_plan_point_rule_window_and_whole_state_cap():
    p = overnight.plan_point({"national": 2, "WIFI": 2}, _toy(), CELLS, "rule")
    n, w = p["channels"]["national"], p["channels"]["WIFI"]
    assert p["infeasible"] == {}
    assert (n["usd_m"], n["tau_m"], n["free"]) == (2500.0, 1250.0, ["CA", "TX"])      # > 625
    assert (n["lo_m"], n["hi_m"], n["final_delta"]) == (1000.0, 1437.5, 0.15)          # 187.5 / 1250
    assert (w["tau_m"], w["free"], w["whole_state_cap"], w["hi_m"]) == (950.0, ["CA", "TX"], False, 1150.0)
    assert w["final_delta"] == 0.1052
    bad = overnight.plan_point({"national": 2, "WIFI": 4}, _toy(), CELLS, "rule")
    assert list(bad["infeasible"]) == ["WIFI"] and "τ outside the dollar window" in bad["infeasible"]["WIFI"]
    cells = {**CELLS, ("CA", "wh"): 900.0, ("TX", "wh"): 643.0}
    base = overnight.plan_point({"national": 2, "WIFI": 1}, _toy(), cells, "base")
    assert base["channels"]["national"]["free"] == ["CA"]                # the spec's own list
    w = base["channels"]["WIFI"]
    assert (w["free"], w["whole_state_cap"], w["hi_m"], w["final_delta"]) == ([], True, 1600.0, 0.10)
    try:
        overnight.plan_point({"national": 2}, _toy(), CELLS, "rule")
    except ValueError:
        pass
    else:
        raise AssertionError("a K for some channels only was planned")


def test_point_spec_text_sets_k_and_both_deltas():
    plan = {"channels": {"national": {"k": 3, "final_delta": 0.15}, "WIFI": {"k": 1, "final_delta": 0.01}}}
    text = overnight.point_spec_text(TOY, "pt-1", plan)
    assert text.startswith("# main-map overnight grid point pt-1")
    sp = tdspec.parse(tomllib.loads(text))
    assert sp.name == "pt-1"
    n, w = sp.channels["national"], sp.channels["WIFI"]
    assert (n.k, n.delta, n.final_delta) == (3, 0.02, 0.15)
    assert (w.k, w.delta, w.final_delta) == (1, 0.01, 0.01)               # declared at most the final


def test_retry_keys_on_the_drawings_own_status():
    contig = {"channels": {"national": {"status": "connected", "plan_delta": 0.05},
                           "WH": {"status": "unknown", "plan_delta": 0.07},
                           "FI": {"status": "infeasible", "plan_delta": 0.09},
                           "WIFI": {"status": "optimal", "plan_delta": 0.1}}}
    assert overnight.needs_retry(contig) == ["FI", "WH"]
    assert overnight.retry_delta(contig, ["FI", "WH"]) == 0.14
    assert overnight.needs_retry({"channels": {"WIFI": {"status": "connected"}}}) == []


def _row(ch, usd, lo=850.0, hi=1150.0, cap=None, ok=False, d=None):
    return {"channel": ch, "district": d or f"{ch}_01", "usd": usd, "lo": lo, "hi": hi, "cap": cap,
            "allowance": False, "ok": ok}


def test_label_order_m1_then_dollars_then_scorer():
    good, bad = {"status": "pass", "summary": "ok"}, {"status": "fail", "summary": "1 district in pieces"}
    ok, out = _row("WH", 900.0, ok=True), _row("WH", 840.8, d="WH_09")
    assert overnight.label_of(bad, [out], False, ["x"])[0] == "fails M1"
    assert overnight.label_of(good, [ok, out], False, ["x"]) == ("ineligible ($)", "WH_09 840.8M outside 850.0-1,150.0M")
    assert overnight.label_of(good, [ok], True, []) == ("eligible", "")
    assert overnight.label_of(good, [ok], False, ["audit: a fails", "main K 47 outside 48-54"]) == \
        ("ineligible", "audit: a fails; main K 47 outside 48-54")


def test_rerun_direction():
    ks = {"national": 15, "WH": 11, "FI": 20, "WIFI": 3}
    assert overnight.rerun_k([_row("WH", 840.0)], ks) == {**ks, "WH": 10}
    assert overnight.rerun_k([_row("FI", 1100.0, 765.0, 1035.0)], ks) == {**ks, "FI": 21}
    assert overnight.rerun_k([_row("WIFI", 1700.0, cap=1600.0)], ks) == {**ks, "WIFI": 4}
    assert overnight.rerun_k([_row("WH", 840.0), _row("WH", 1200.0, d="WH_02")], ks) is None
    assert overnight.rerun_k([_row("WIFI", 800.0)], {"WIFI": 1}) is None
    assert overnight.rerun_k([_row("X", 5.0, lo=None, hi=None)], {"X": 2}) is None
    assert overnight.rerun_k([_row("WH", 900.0, ok=True)], ks) is None
    assert overnight.rerun_id("ne-50-bal", ks, {**ks, "WH": 10}) == "ne-50-bal-WH10"


def test_dollars_and_score_files_read_back():
    gate = [{"channel": "WH", "district": "WH_01", "usd": 840.8e6, "lo": 0.85e9, "hi": 1.15e9,
             "states": ["NJ", "NY"], "whole_states": False, "cap": None, "allowance": False, "ok": False},
            {"channel": "WIFI", "district": "WIFI_01", "usd": 1.543e9, "lo": 0.85e9, "hi": 1.15e9,
             "states": ["CO", "ID"], "whole_states": True, "cap": 1.6e9, "allowance": True, "ok": True}]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "dollars.csv")
        score.write_dollars(path, gate)
        rows = overnight.read_dollars(path)
        sc = os.path.join(tmp, "score.txt")
        with open(sc, "w") as fh:
            fh.write("# r\ndir: d\neligible: no\n  - audit: a fails\n  - $ WH_01 840.8M outside\nK: WH 11\n")
        no = overnight.read_score(sc)
        with open(sc, "w") as fh:
            fh.write("# r\ndir: d\neligible: yes\nK: WH 11\n")
        yes = overnight.read_score(sc)
    assert rows[0] == {"channel": "WH", "district": "WH_01", "usd": 840.8, "lo": 850.0, "hi": 1150.0,
                       "cap": None, "allowance": False, "ok": False}
    assert (rows[1]["usd"], rows[1]["cap"], rows[1]["allowance"], rows[1]["ok"]) == (1543.0, 1600.0, True, True)
    assert no == (False, ["audit: a fails", "$ WH_01 840.8M outside"])
    assert yes == (True, [])


def test_schedule_first_fit_reruns_and_deadline():
    pts = [{"id": "a", "k": {"x": 1, "y": 1, "z": 1}}, {"id": "b", "k": {"x": 1, "y": 1, "z": 1}},
           {"id": "c", "k": {"x": 1}}]
    lock, ran, live, peak = threading.Lock(), [], [0], [0]

    def work(p):
        with lock:
            live[0] += overnight.slots_of(p)
            peak[0] = max(peak[0], live[0])
        time.sleep(0.05)
        with lock:
            live[0] -= overnight.slots_of(p)
            ran.append(p["id"])
        return [{"id": "a2", "k": {"x": 1}}] if p["id"] == "a" else []
    assert overnight.schedule(pts, 5, time.time() + 60, work, poll=0.01) == []
    assert sorted(ran) == ["a", "a2", "b", "c"] and peak[0] <= 5
    assert ran.index("c") < ran.index("b")                                 # c filled a's leftover slots
    ran.clear()
    assert overnight.schedule(pts, 5, time.time() - 1, work, poll=0.01) == pts and ran == []
    try:
        overnight.schedule([{"id": "w", "k": {"x": 1}}], 1, time.time() + 60, work)
    except ValueError:
        pass
    else:
        raise AssertionError("a point larger than the slots was scheduled")


def test_child_cap_deadline_and_exit():
    sleep = [sys.executable, "-c", "import time; time.sleep(30)"]
    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "s.log")
        cap = overnight.child(sleep, log, 0.5, time.time() + 60)
        late = overnight.child(sleep, log, 60, time.time() + 0.5)
        past = overnight.child(sleep, log, 5, time.time() - 1)
        ok = overnight.child([sys.executable, "-c", "print('hi')"], log, 30, time.time() + 60)
        text = open(log).read()
    assert cap["stop"] == "cap" and cap["rc"] != 0 and cap["seconds"] < 10
    assert late["stop"] == "deadline" and late["seconds"] < 10
    assert past == {"rc": None, "seconds": 0.0, "stop": "deadline"}
    assert ok["rc"] == 0 and ok["stop"] is None and "hi" in text
    assert not overnight.LIVE


def test_resume_keeps_finished_folders_and_sets_others_aside():
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "draw")
        assert not overnight.finished(d)
        os.makedirs(d)
        open(os.path.join(d, "ledger.csv"), "w").close()
        for status, want in (("running", False), ("done", True)):
            with open(os.path.join(d, "manifest.json"), "w") as fh:
                json.dump({"status": status}, fh)
            assert overnight.finished(d) is want
        r1 = os.path.join(tmp, "r1")
        assert overnight.set_aside(r1) is None
        for n in (1, 2):
            os.makedirs(r1)
            open(os.path.join(r1, "x"), "w").close()
            assert overnight.set_aside(r1) == f"{r1}.stale{n}"
            assert os.path.exists(os.path.join(f"{r1}.stale{n}", "x")) and not os.path.exists(r1)


def test_grid_lists_every_point_once():
    doc = overnight.grid_doc("m5", "/x/instance_descaled_usd.json.gz", "abc", time.time() + 3600,
                             {"commit": "c", "dirty": False, "diff_sha256": None})
    pts = doc["points"]
    assert len(pts) == len(overnight.POINTS) == 21
    assert collections.Counter(p["status"] for p in pts.values()) == {"queued": 15, "elsewhere": 6}
    assert all((p["host"] == "m2") == (p["structure"] == "west8") for p in pts.values())
    chans = {"ne_plains": {"national", "WH", "FI", "WIFI"}, "west8": {"national", "WH", "FI", "WIFI"},
             "nw49": {"national", "WIFI"}, "nw34": {"national", "WIFI"}, "w1": {"WIFI"}}
    for p in overnight.POINTS:
        assert set(p["k"]) == chans[p["structure"]] and 48 <= sum(p["k"].values()) <= 52
    assert overnight.order(overnight.POINTS)[0]["id"] == "w1-52"
    assert any("#133" in x for x in doc["assumptions"])
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "GRID.json")
        g = overnight.Grid(path, doc)
        g.update("w1-48", label="stopped")
        g.add(overnight.record({"id": "w1-48-WIFI47", "structure": "w1", "k": {"WIFI": 47}}, "m5", "w1-48"))
        back = json.load(open(path))
        assert back["points"]["w1-48"]["label"] == "stopped"
        assert back["points"]["w1-48-WIFI47"]["parent"] == "w1-48"
        assert not os.path.exists(path + ".tmp")
        assert abs(g.deadline() - (time.time() + 3600)) < 5


def test_commands_carry_the_settled_flags():
    plan = {"channels": {"national": {"free": ["CA", "TX"]}, "WIFI": {"free": []}}}
    rp = overnight.replan_cmd("b.toml", "/p", "/plans", "/x.json.gz", plan)
    assert rp[rp.index("--free") + 1] == "national=CA,TX" and "--keep" not in rp
    assert rp[rp.index("--time-limit") + 1] == "600"
    assert "--keep" in overnight.replan_cmd("b.toml", "/p", "/plans", "/x", {"channels": {"WIFI": {"free": []}}})
    d = overnight.draw_cmd("s.toml", "/o", "/plans", "/x", 4)
    assert d[d.index("--land-ratio") + 1] == "10" and "--sequential" in d and "--delta" not in d
    assert d[d.index("--jobs") + 1] == "4" and d[d.index("--time-limit") + 1] == "4500"
    d = overnight.draw_cmd("s.toml", "/o", "/plans", "/x", 4, 0.14)
    assert d[d.index("--delta") + 1] == "0.14"
    r = overnight.repair_cmd("/s", "/o", "/plans", "/x", 2, 2, "ne-48-bal")
    assert r[r.index("--h0") + 1] == "8" and r[r.index("--max-zctas") + 1] == "2000"
    assert r[r.index("--budget") + 1] == "1800" and "--keep-support" in r and "--flow" in r
    assert overnight.slots_of({"k": {"WIFI": 48}}) == 2
    assert overnight.slots_of({"k": dict.fromkeys(("national", "WH", "FI", "WIFI"), 1)}) == 4
```

### Success Criteria:

#### Automated Verification:
- [ ] Slice tests pass: `"$TD_PY" tests/run_all.py -k test_overnight.py 2>&1 | tail -1` shows `12 passed, 0 failed`
- [ ] Earlier slices still pass beside the launcher: `"$TD_PY" tests/run_all.py -k test_land.py 2>&1 | tail -1` shows `6 passed, 0 failed` and `"$TD_PY" tests/run_all.py -k test_looks_score.py 2>&1 | tail -1` shows `15 passed, 0 failed`
- [ ] The launcher's surface is present: `rg -c '^def (plan_point|fit_delta|point_spec_text|needs_retry|label_of|rerun_k|schedule|child)\(' tools/exp/contig/overnight.py` prints 8
- [ ] The grid holds the 21 settled points: `rg -c '^    _point\(' tools/exp/contig/overnight.py` prints 21
- [ ] Trap 15: the draw retry keys on the realizer's own stop reasons: `rg -n 'RETRY_ON = \("infeasible", "unknown"\)' tools/exp/contig/overnight.py` prints one line
- [ ] Trap 18: every point drawn and repaired with HiGHS pinned (run.py/repair.py pin only above one job): `rg -n 'return max\(2, len\(pt\["k"\]\)\)' tools/exp/contig/overnight.py` prints one line
- [ ] The #133 term and the G3 gate are wired: `rg -c '"--land-ratio"|GAP_ENV = \{audit.GAP_WIDTH_ENV: "1"\}' tools/exp/contig/overnight.py` prints 2
- [ ] The launcher never deletes a run folder: `rg -n 'rmtree|os\.remove|os\.unlink' tools/exp/contig/overnight.py` prints nothing
- [ ] No source file outside the slice changes: `git diff --stat e82d6a4 -- tools/exp/contig/run.py tools/exp/contig/repair.py tools/exp/contig/replan.py | tail -1` shows only Slice 4's run.py change (repair.py and replan.py untouched)

#### Manual Verification:
- [ ] On m5 with the dollar extract in place (Slice 1), `"$TD_PY" tools/exp/contig/overnight.py run --host m5 --hours 0 --root /tmp/td-grid-dry` exits 0 and writes `/tmp/td-grid-dry/GRID.json` listing all 21 points: the 15 m5 points labelled `stopped` ("not started before the 0 h stop"), the six west8 points `elsewhere` with no label, the extract's sha256 matching `shasum -a 256 "$TD_REPO/instance_descaled_usd.json.gz"`, and the assumptions naming #111, #112, #119 and #133
- [ ] Rerunning the same command resumes: it prints "0 points" and leaves every label in GRID.json as it was
- [ ] `"$TD_PY" tools/exp/contig/overnight.py run --host m5 --extract "$TD_REPO/instance_descaled.json.gz" --root /tmp/td-grid-dry2` refuses with "is not a dollar extract" and writes nothing

---

## Phase 6: Collect + morning + smoke

### Overview
Adds the remaining subcommands:
- `collect`: reads m2's GRID.json over ssh, hashes with `shasum -a 256`, copies with `rsync -a`, compares sha256 file by file, and runs `merge_remote`.
- `morning`: `fac_usd.json` (D14), `render.py --if-stale --fac` under the G3 gate, `title_of`, `morning_order`, `eye_items`, `MORNING.md` and `MORNING.pdf`.
- `smoke`: one point's replan and draw, `smoke.json` with the ledger sha256 and peak RSS, `suggest_slots`, and `--compare`.

Also adds the four remaining CODE_MAP rows. After this phase `tools/exp/contig/overnight.py` is byte-identical to the design's fence.

### Changes Required:

#### 1. collect, morning, smoke
**File**: `tools/exp/contig/overnight.py` (MODIFY)
**Changes**: A unified diff against the file as Phase 5 leaves it (`git apply`).

```diff
--- a/tools/exp/contig/overnight.py
+++ b/tools/exp/contig/overnight.py
@@ -4,6 +4,12 @@
 
     "$TD_PY" -u tools/exp/contig/overnight.py run --host m5|m2 [--hours 8] [--slots N]
         [--only ID ...] [--root DIR] [--extract PATH] [--notify CMD]
+    "$TD_PY" tools/exp/contig/overnight.py collect --from m2 [--ssh ALIAS] [--remote-root DIR]
+        [--root DIR] [--anyway]
+    "$TD_PY" tools/exp/contig/overnight.py morning [--root DIR] [--no-render] [--jobs N]
+    "$TD_PY" -u tools/exp/contig/overnight.py smoke --out DIR [--point ID] [--host m5|m2]
+        [--extract PATH] [--hours H]
+    "$TD_PY" tools/exp/contig/overnight.py smoke --compare A B
 
 **Points** (`POINTS`, the research's settled grid): each names a structure, the base spec under
 `scenarios/` (`STRUCTURES`), and a K per channel; west8's six run on m2, the other fifteen on m5
@@ -49,6 +55,31 @@
 to the stage's process group, then SIGKILL after `STOP_GRACE`).  Nothing here prints a cell's
 value; maps are rendered on m5 after the run.
 
+**collect** (on m5, after the run): the other host's GRID.json read over ssh, refused while one
+of its points has no label (`--anyway` copies them as they are) or when its extract is not this
+grid's; its points' folders hashed there (`shasum -a 256`), copied with `rsync -a`, hashed here
+and compared file by file.  On a match its records replace the "elsewhere" ones in this GRID.json
+with a `collected` note and its own GRID.json is kept as `GRID.<host>.json`; a mismatch merges
+nothing and exits 1.  `collect_<host>.json` lists every file's sha256 and the problems either way.
+
+**morning** (on m5, after collect): every stage folder rendered unless current
+(`tools/maps/render.py --if-stale`, under the G3 gate, its $M through `fac_usd.json`, a factor
+of 1 per fine channel, D14), the final folder titled with its point's label (`title_of`); then
+`MORNING.md`, one table in the settled order (`morning_order`: eligible first by the scorer's
+`rank_key`, then fails M1, ineligible ($), ineligible, infeasible, stopped and error, a balanced
+point beside its FI-light partner when both carry one label) with K, splits, defects, the worst
+district's $ against its channel's mean, M1 across gaps and strict, the largest in-state land
+ratio, the label and links, the assumptions above it and "Needs your eye" below (`eye_items`:
+every M1 flip but El Paso's, every whole-state allowance, every split group beyond R, every
+failed render and unlabelled point); and `MORNING.pdf`, one page per point in that order, the
+final folder's `summary.png` or a page naming the label and reason.
+
+**smoke** (before the launch, on each Studio): one point's replan and draw, as `run` would draw
+it, into an empty folder with its own plan cache; `smoke.json` records the code, the extract's
+and the ledger's sha256, each channel's drawing status, the seconds, the peak RSS of any one
+child process (`RUSAGE_CHILDREN`) and the slots it leaves room for (`suggest_slots`, D12).
+`--compare` reads two of them (`host:path` over ssh) and exits 0 only when they agree
+(`compare_smoke`).
 """
 from __future__ import annotations
 
@@ -62,9 +93,13 @@
 import math
 import os
 import re
+import resource
+import shlex
 import signal
+import socket
 import subprocess
 import sys
+import textwrap
 import threading
 import time
 import traceback
@@ -145,6 +180,12 @@
     "owner decisions (2026-10-12) still to be filed in PROBLEM.md",
     "M1 gated with necks across coverage gaps (scouts G1, TD_NECK_GAP_WIDTH=1); strict beside it",
 ]
+CHANNELS = ("national", "WH", "FI", "WIFI")    # the order K is written in
+STAGES = ("draw", "draw_retry", "r1", "r2")     # a point's stage folders, in chain order
+RENDER_S = 1800.0               # one folder's render cap
+EL_PASO = ("79718-79734", "79734-79718")        # the TX K3 flip of d312834's audit (G3)
+MEM_GIB = {"m2": 24}            # the memory the smoke's peak RSS divides (D12)
+PDF_PAGE = (2600, 1500)         # a page without a map, when no map sets the size
 LIVE = set()                    # the stage processes running, for the stop
 LIVE_LOCK = threading.Lock()
 
@@ -173,6 +214,10 @@
     return _load("exp_sweep", os.path.join(ROOT, "tools", "exp", "sweep.py"))
 
 
+def _render():
+    return _load("maps_render", os.path.join(ROOT, "tools", "maps", "render.py"))
+
+
 def now() -> str:
     return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
 
@@ -695,8 +740,442 @@
                 free += need(p)
                 queue[:0] = f.result() or []
     return queue
+
+
+# ------------------------------------------------------------------------------ collect
+def ssh_text(alias: str, command: str) -> str:
+    """`command`'s stdout on the host `alias` (`ssh m2` on the LAN, `m2-ts` over Tailscale)."""
+    got = subprocess.run(["ssh", "-o", "BatchMode=yes", alias, command], capture_output=True, text=True,
+                         stdin=subprocess.DEVNULL)
+    if got.returncode:
+        raise SystemExit(f"ssh {alias} {command!r} exited {got.returncode}: {got.stderr.strip()[-300:]}")
+    return got.stdout
+
+
+def read_json_at(where: str) -> dict:
+    """A JSON file here, or at `host:path` over ssh."""
+    if not os.path.exists(where) and ":" in where:
+        alias, path = where.split(":", 1)
+        return json.loads(ssh_text(alias, f"cat {shlex.quote(path)}"))
+    with open(where, encoding="utf-8") as fh:
+        return json.load(fh)
+
+
+def parse_shasum(text: str) -> dict:
+    """{path: sha256} from `shasum -a 256` lines, paths relative to the grid root."""
+    out = {}
+    for line in text.splitlines():
+        if line.strip():
+            sha, path = line.split("  ", 1)
+            out[path[2:] if path.startswith("./") else path] = sha
+    return out
+
+
+def hash_tree(root: str, ids: list) -> dict:
+    """{path: sha256} of every file under `root`/<id> for the `ids`, paths relative to `root`."""
+    out = {}
+    for pid in ids:
+        for d, _, fs in os.walk(os.path.join(root, pid)):
+            for name in fs:
+                path = os.path.join(d, name)
+                out[os.path.relpath(path, root).replace(os.sep, "/")] = _dollarize().sha256(path)
+    return out
+
+
+def compare_hashes(theirs: dict, ours: dict) -> list:
+    """Each file of `theirs` missing here or with another sha256; files only here are not compared
+    (a render made on m5 after an earlier collect)."""
+    return [f"missing {p}" if p not in ours else f"differs {p}" for p in sorted(theirs) if ours.get(p) != theirs[p]]
+
+
+def remote_unlabelled(remote: dict, host: str) -> list:
+    return sorted(pid for pid, r in remote["points"].items() if r["host"] == host and r["label"] is None)
+
+
+def check_remote(doc: dict, remote: dict, host: str) -> list:
+    """The ids of `host`'s points in its GRID.json `remote`, after checking it is `host`'s grid
+    of this one's name on this one's extract and that no point here is another host's."""
+    if remote.get("grid") != doc.get("grid") or remote.get("host") != host:
+        raise ValueError(f"the remote GRID.json is {remote.get('host')}'s {remote.get('grid')}, not {host}'s "
+                         f"{doc.get('grid')}")
+    if remote.get("extract_sha256") != doc.get("extract_sha256"):
+        raise ValueError(f"{host} ran on extract {str(remote.get('extract_sha256'))[:12]}, this grid on "
+                         f"{str(doc.get('extract_sha256'))[:12]}")
+    ids = sorted(pid for pid, r in remote["points"].items() if r["host"] == host)
+    clash = [pid for pid in ids if pid in doc["points"] and doc["points"][pid]["host"] != host]
+    if clash:
+        raise ValueError(f"points of another host here: {clash}")
+    return ids
+
+
+def merge_remote(doc: dict, remote: dict, host: str, note: dict) -> list:
+    """`host`'s records from `remote` into `doc` in place of its "elsewhere" ones (its re-runs
+    added), each with `collected` = `note`; the ids merged."""
+    ids = check_remote(doc, remote, host)
+    for pid in ids:
+        doc["points"][pid] = {**remote["points"][pid], "collected": dict(note)}
+    return ids
+
+
+def cmd_collect(a) -> int:
+    path = os.path.join(a.root, GRID_JSON)
+    if not os.path.exists(path):
+        raise SystemExit(f"no {path}: collect into the grid `run` wrote on this host")
+    with open(path, encoding="utf-8") as fh:
+        doc = json.load(fh)
+    alias, rroot = a.ssh or a.src, a.remote_root or a.root
+    remote = json.loads(ssh_text(alias, f"cat {shlex.quote(os.path.join(rroot, GRID_JSON))}"))
+    try:
+        ids = check_remote(doc, remote, a.src)
+    except ValueError as e:
+        raise SystemExit(f"{a.src}: {e}")
+    open_ = remote_unlabelled(remote, a.src)
+    if open_ and not a.anyway:
+        raise SystemExit(f"{a.src}'s points without a label: {', '.join(open_)} (still running? --anyway "
+                         "copies them as they are)")
+    listing = ssh_text(alias, f"cd {shlex.quote(rroot)} && find {' '.join(map(shlex.quote, ids))} -type f "
+                              "-print0 2>/dev/null | xargs -0 shasum -a 256")
+    theirs = parse_shasum(listing)
+    copied = sorted({p.split("/", 1)[0] for p in theirs})
+    for pid in copied:
+        rc = subprocess.run(["rsync", "-a", f"{alias}:{rroot}/{pid}/", os.path.join(a.root, pid) + "/"],
+                            stdin=subprocess.DEVNULL).returncode
+        if rc:
+            raise SystemExit(f"rsync of {pid} from {alias} exited {rc}; nothing merged")
+    bad = compare_hashes(theirs, hash_tree(a.root, copied))
+    at = now()
+    _write_json(os.path.join(a.root, f"collect_{a.src}.json"),
+                {"from": a.src, "ssh": alias, "remote_root": rroot, "at": at, "points": ids, "copied": copied,
+                 "files": len(theirs), "problems": bad, "sha256": theirs})
+    if bad:
+        print(f"{len(bad)} of {len(theirs)} files from {a.src} do not match; nothing merged:", *bad[:20], sep="\n  ")
+        return 1
+    _write_json(os.path.join(a.root, f"GRID.{a.src}.json"), remote)
+    merged = merge_remote(doc, remote, a.src, {"from": a.src, "at": at, "files": len(theirs),
+                                               "sha256_checked": True, "code": remote.get("code")})
+    Grid(path, doc)
+    print(f"collected {len(merged)} points of {a.src} ({len(copied)} folders, {len(theirs)} files, sha256 "
+          f"checked) into {path}", flush=True)
+    return 0
+
+
+# ------------------------------------------------------------------------------ morning
+def k_text(ks: dict) -> str:
+    return ", ".join(f"{c} {ks[c]}" for c in CHANNELS if c in ks) + f" = {sum(ks.values())}"
+
+
+def title_of(rec: dict, stage: str | None = None) -> str:
+    """A map's one-line title: the point, its structure and K, and its label (`render.FAILS` for
+    fails M1, so the renderer adds none); a stage folder other than the final one says so."""
+    head = f"{rec['id']}: {rec['structure']}, K {k_text(rec['k'])}"
+    if stage is not None:
+        return f"{head} ({stage}, not the final folder)"
+    label = _render().FAILS if rec["label"] == "fails M1" else rec["label"] or "no label"
+    return f"{head}; {label}" + (f" (re-run of {rec['parent']})" if rec.get("parent") else "")
+
+
+def fac_file(root: str) -> str:
+    """`<root>/fac_usd.json`: $M per $M, 1 for every fine channel with an owner total (D14)."""
+    path = os.path.join(root, "fac_usd.json")
+    _write_json(path, {"fac": {f: 1.0 for f in sorted(score.DOLLARS)},
+                       "note": "the overnight grid's ledgers hold $M (tools/exp/contig/dollarize.py)"})
+    return path
+
+
+def render_jobs(root: str, recs: list) -> list:
+    """(folder, title) for every stage folder with a ledger, the final one titled with the label."""
+    out = []
+    for rec in recs:
+        final = rec.get("final") and os.path.join(root, rec["final"])
+        for name in STAGES:
+            folder = os.path.join(root, rec["id"], name)
+            if os.path.exists(os.path.join(folder, "ledger.csv")):
+                out.append((folder, title_of(rec) if folder == final else title_of(rec, name)))
+    return out
+
+
+def render_one(folder: str, title: str, fac: str) -> tuple:
+    """(folder, exit code) of `render.py` on it, under the G3 gate, logged to its `render.log`."""
+    cmd = [sys.executable, "-u", os.path.join(ROOT, "tools", "maps", "render.py"), folder, "--label", title,
+           "--fac", fac, "--if-stale"]
+    return folder, child(cmd, os.path.join(folder, "render.log"), RENDER_S, time.time() + RENDER_S + 60, GAP_ENV)["rc"]
+
+
+LOOKS = {"splits": (r"^channel-state splits: (\d+):", int),           # score.report's lines
+         "defects": (r"^defects: (\S+) =", float),
+         "largest_extent_km": (r"^shape: extent ([\d,.]+) km", lambda x: float(x.replace(",", ""))),
+         "states_per_district": (r"^shape: extent [\d,.]+ km, (\d+) states per district", int),
+         "worst_dev": (r"^balance: worst ([\d.]+)%", lambda x: float(x) / 100),
+         "mean_dev": (r"^balance: worst [\d.]+%, mean ([\d.]+)%", lambda x: float(x) / 100)}
+
+
+def read_looks(path: str) -> dict | None:
+    """`score.rank_key`'s fields from a `score.py` report, or None without one."""
+    text, out = _text(path), {}
+    for k, (pat, conv) in LOOKS.items():
+        m = re.search(pat, text, re.M)
+        if m is None:
+            return None
+        out[k] = conv(m.group(1))
+    return out
+
+
+def worst_usd(rows: list) -> tuple | None:
+    """(district, $M, deviation) of the district farthest from its channel's mean $ per district."""
+    by, best = collections.defaultdict(list), None
+    for r in rows:
+        by[r["channel"]].append(r)
+    for _, rs in sorted(by.items()):
+        tau = math.fsum(r["usd"] for r in rs) / len(rs)
+        for r in rs:
+            dev = (r["usd"] - tau) / tau if tau else 0.0
+            if best is None or abs(dev) > abs(best[2]):
+                best = (r["district"], r["usd"], dev)
+    return best
+
+
+def folder_metrics(folder: str | None) -> dict:
+    """A final folder's score report fields, dollar rows, `m1.json` and `land.csv` rows (None where
+    absent)."""
+    def opt(name, read):
+        path = folder and os.path.join(folder, name)
+        return read(path) if path and os.path.exists(path) else None
+
+    def land(path):
+        with open(path, newline="") as fh:
+            return list(csv.DictReader(fh))
+
+    def m1(path):
+        with open(path, encoding="utf-8") as fh:
+            return json.load(fh)
+    return {"looks": opt("score.txt", read_looks), "dollars": opt("dollars.csv", read_dollars),
+            "m1": opt("m1.json", m1), "land": opt("land.csv", land)}
 
 
+def point_row(root: str, rec: dict) -> dict:
+    final = os.path.join(root, rec["final"]) if rec.get("final") else None
+    m = folder_metrics(final)
+    return {"id": rec["id"], "rec": rec, "label": rec["label"] or "error", "final": rec.get("final"),
+            "reason": rec["reason"] or ("" if rec["label"] else f"no label (status {rec['status']})"),
+            "m": m, "key": score.rank_key(m["looks"]) if m["looks"] else None}
+
+
+def pair_of(pid: str) -> str | None:
+    m = re.match(r"^(.*)-(bal|filight)$", pid)
+    return m and m.group(1)
+
+
+def morning_order(rows: list) -> list:
+    """The settled order: by label (`LABELS`, unknown last), within one by the scorer's
+    `rank_key` (rows without a report after), then id; a balanced point's FI-light partner
+    (`<x>-bal`, `<x>-filight`) moved beside the first of the two when both carry one label."""
+    at = {x: i for i, x in enumerate(LABELS)}
+    rows = sorted(rows, key=lambda r: (at.get(r["label"], len(LABELS)), r["key"] is None, r["key"] or (), r["id"]))
+    out, seen = [], set()
+    for r in rows:
+        if r["id"] in seen:
+            continue
+        out.append(r)
+        seen.add(r["id"])
+        p = pair_of(r["id"])
+        for s in rows:
+            if p and s["id"] not in seen and pair_of(s["id"]) == p and s["label"] == r["label"]:
+                out.append(s)
+                seen.add(s["id"])
+    return out
+
+
+def el_paso(flip: dict) -> bool:
+    items = flip["strict"] + flip["gap_width"]
+    return bool(items) and all(any(c in i for c in EL_PASO) for i in items)
+
+
+def eye_items(pid: str, m: dict) -> list:
+    """G3's flips but El Paso's, the whole-state allowances and the split groups beyond R of a
+    point's final folder."""
+    out = []
+    for f in (m["m1"] or {}).get("flips", []):
+        if not el_paso(f):
+            way = "strict only" if f["strict"] else "across coverage gaps only"
+            out.append(f"{pid}: M1 flip {f['district']}, a neck {way}: {(f['strict'] or f['gap_width'])[0]}")
+    out += [f"{pid}: {r['district']} {r['usd']:,.1f}M on the whole-state allowance (up to {r['cap']:,.1f}M)"
+            for r in m["dollars"] or () if r["allowance"]]
+    out += [f"{pid}: {r['channel']} {r['state']} in-state land ratio {r['ratio']} beyond R = {LAND_RATIO:g} "
+            f"({r['largest']} {r['largest_km2']} km², {r['smallest']} {r['smallest_km2']} km²)"
+            for r in m["land"] or () if r["over"] == "1"]
+    return out
+
+
+def _cells(r: dict) -> list:
+    m, final = r["m"], r["final"]
+    looks, w = m["looks"], worst_usd(m["dollars"] or [])
+    ratios = [float(x["ratio"]) for x in m["land"] or () if x["ratio"]]
+    over = sum(x["over"] == "1" for x in m["land"] or ())
+    m1 = m["m1"]
+    return [r["id"], r["rec"]["structure"], k_text(r["rec"]["k"]),
+            "—" if looks is None else str(looks["splits"]), "—" if looks is None else f"{looks['defects']:g}",
+            "—" if w is None else f"{w[0]} {100 * w[2]:+.1f}% ({w[1]:,.1f}M)",
+            "—" if m1 is None else f"{m1['gap_width']['status']} / {m1['strict']['status']}"
+            + (f", {len(m1['flips'])} flips" if m1["flips"] else ""),
+            "—" if not ratios else f"{max(ratios):.1f}" + (f" ({over} > R)" if over else ""),
+            f"**{r['label']}**",
+            "—" if not final else f"[folder]({final}/) · [map]({final}/summary.png) · [score]({final}/score.txt)"]
+
+
+def morning_md(doc: dict, rows: list, eye: list, at: str) -> str:
+    counts = collections.Counter(r["label"] for r in rows)
+    codes = sorted({json.dumps(c, sort_keys=True) for c in [doc.get("code")]
+                    + [r["rec"].get("collected", {}).get("code") for r in rows] if c})
+    md = [f"# MORNING: {GRID_NAME}", "",
+          f"Built by `tools/exp/contig/overnight.py morning` from `GRID.json` at {at}.  Extract "
+          f"`{os.path.basename(doc['extract'])}` (sha256 `{doc['extract_sha256'][:12]}`); code "
+          + ", ".join(f"`{json.loads(c)['commit'][:7]}`" + (" (dirty)" if json.loads(c)["dirty"] else "") for c in codes)
+          + f"; stop at {doc['deadline']}.", "",
+          f"{len(rows)} points: " + ", ".join(f"{counts[x]} {x}" for x in LABELS if counts[x]) + ".", "",
+          "## Assumptions (owner decisions open)", ""] + [f"- {x}" for x in doc["assumptions"]] + [
+          "", "## Points", "",
+          "Eligible first by the scorer's rank key (splits, defects, extent, states per district, worst and mean "
+          "deviation), then fails M1, ineligible ($), ineligible, infeasible, stopped and error; a balanced point "
+          "beside its FI-light partner when both carry one label.  Worst $: the district farthest from its "
+          "channel's mean $ per district.  M1: across coverage gaps (the gate) / strict.  Land: the largest "
+          f"in-state ratio, groups beyond R = {LAND_RATIO:g}.  `MORNING.pdf` has one page per point in this order.",
+          "", "| # | id | structure | K | splits | defects | worst $ | M1 gaps / strict | land | label | links |",
+          "|---|---|---|---|---|---|---|---|---|---|---|"]
+    md += [f"| {i} | " + " | ".join(_cells(r)) + " |" for i, r in enumerate(rows, 1)]
+    md += ["", "## Reasons", ""] + ([f"- **{r['id']}** ({r['label']}): {r['reason']}" for r in rows if r["reason"]]
+                                    or ["- none"])
+    md += ["", "## Needs your eye", ""] + ([f"- {x}" for x in eye] or ["- nothing"])
+    return "\n".join(md) + "\n"
+
+
+def morning_pdf(path: str, pages: list) -> None:
+    """A raster PDF (`tools/shortlist/build.py`'s `deck`): one page per (png or None, text), a
+    page without a map showing its text."""
+    from PIL import Image, ImageDraw, ImageFont
+    size = next((Image.open(p).size for p, _ in pages if p and os.path.exists(p)), PDF_PAGE)
+    font, imgs = ImageFont.load_default(size=40), []
+    for png, text in pages:
+        if png and os.path.exists(png):
+            imgs.append(Image.open(png).convert("RGB"))
+            continue
+        im = Image.new("RGB", size, "white")
+        body = "\n".join(textwrap.fill(x, 100) for x in text.splitlines())
+        ImageDraw.Draw(im).multiline_text((60, 60), body, fill="black", font=font, spacing=12)
+        imgs.append(im)
+    imgs[0].save(path, save_all=True, append_images=imgs[1:], resolution=100)
+
+
+def cmd_morning(a) -> int:
+    with open(os.path.join(a.root, GRID_JSON), encoding="utf-8") as fh:
+        doc = json.load(fh)
+    recs = [doc["points"][pid] for pid in sorted(doc["points"])]
+    eye = []
+    if not a.no_render:
+        fac = fac_file(a.root)
+        _render()
+        with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
+            done = list(pool.map(lambda j: render_one(*j, fac), render_jobs(a.root, recs)))
+        eye += [f"render failed (exit {rc}): {os.path.relpath(f, a.root)}/render.log" for f, rc in done if rc != 0]
+    rows = morning_order([point_row(a.root, rec) for rec in recs])
+    for r in rows:
+        eye += eye_items(r["id"], r["m"])
+        if r["rec"]["label"] is None:
+            eye.append(f"{r['id']}: {r['reason']}, counted as an error")
+    md = os.path.join(a.root, "MORNING.md")
+    with open(md, "w", encoding="utf-8") as fh:
+        fh.write(morning_md(doc, rows, eye, now()))
+    pdf = os.path.join(a.root, "MORNING.pdf")
+    morning_pdf(pdf, [(r["final"] and os.path.join(a.root, r["final"], "summary.png"),
+                       title_of(r["rec"]) + (f"\n{r['reason']}" if r["reason"] else "") + "\nno map")
+                      for r in rows])
+    print(f"{md}\n{pdf}\n{len(rows)} points, {len(eye)} items need your eye", flush=True)
+    return 0
+
+
+# ------------------------------------------------------------------------------ smoke
+def peak_rss(maxrss: int, platform: str = sys.platform) -> int:
+    """`ru_maxrss` in bytes: bytes on macOS, KiB on Linux."""
+    return maxrss if platform == "darwin" else maxrss * 1024
+
+
+def suggest_slots(host: str, peak: int) -> int:
+    """D12: `MEM_GIB`[host] over the smoke's peak RSS, at most `SLOTS`[host]; `SLOTS` where no
+    budget is set."""
+    if host not in MEM_GIB or peak <= 0:
+        return SLOTS[host]
+    return max(1, min(SLOTS[host], int(MEM_GIB[host] * 2 ** 30 // peak)))
+
+
+def this_host() -> str | None:
+    name = socket.gethostname().split(".")[0]
+    return next((h for h in sorted(SLOTS) if name.startswith(h)), None)
+
+
+SMOKE_SAME = ("point", "extract_sha256", "ledger_sha256", "statuses")
+
+
+def compare_smoke(a: dict, b: dict) -> list:
+    """What differs between two `smoke.json`: the point, extract, ledger, statuses or code."""
+    out = [f"{k}: {a.get(k)!r} vs {b.get(k)!r}" for k in SMOKE_SAME if a.get(k) != b.get(k)]
+    ca, cb = ((c["code"]["commit"], c["code"]["diff_sha256"]) for c in (a, b))
+    if ca != cb:
+        out.append(f"code: {ca} vs {cb}")
+    return out
+
+
+def cmd_smoke(a) -> int:
+    if a.compare:
+        x, y = map(read_json_at, a.compare)
+        diff = compare_smoke(x, y)
+        print(*(diff or [f"match: {x['point']} ledger {x['ledger_sha256'][:12]} on {x['host']} and {y['host']}; "
+                         f"peak RSS {x['peak_rss_bytes'] / 2 ** 30:.2f} / {y['peak_rss_bytes'] / 2 ** 30:.2f} GiB"]),
+              sep="\n")
+        return 1 if diff else 0
+    if not a.out:
+        raise SystemExit("smoke needs --out DIR (or --compare A B)")
+    host = a.host or this_host()
+    if host is None:
+        raise SystemExit("cannot tell the host from the hostname; pass --host")
+    pt = {p["id"]: p for p in POINTS}.get(a.point)
+    if pt is None:
+        raise SystemExit(f"no point {a.point}")
+    if _dollarize().rates_of(a.extract) is None:
+        raise SystemExit(f"{a.extract} is not a dollar extract (tools/exp/contig/dollarize.py)")
+    if os.path.exists(a.out) and os.listdir(a.out):
+        raise SystemExit(f"{a.out} is not empty")
+    os.makedirs(a.out, exist_ok=True)
+    base_path, rule = STRUCTURES[pt["structure"]]
+    base_path = os.path.join(ROOT, base_path)
+    plan = plan_point(pt["k"], tdspec.load(base_path), state_cells(a.extract), rule)
+    if plan["infeasible"]:
+        raise SystemExit("; ".join(plan["infeasible"].values()))
+    base, spec, plans = (os.path.join(a.out, x) for x in ("spec-base.toml", "spec.toml", "_plans"))
+    with open(base_path, encoding="utf-8") as fh:
+        text = point_spec_text(fh.read(), pt["id"], plan)
+    with open(base, "w", encoding="utf-8") as fh:
+        fh.write(text)
+    deadline = time.time() + 3600.0 * a.hours
+    rp = child(replan_cmd(base, a.out, plans, a.extract, plan), os.path.join(a.out, "replan.log"),
+               PLAN_S * len(pt["k"]) + CAP_S["replan"], deadline)
+    if rp["rc"] != 0:
+        raise SystemExit(f"replan.py: {rp}, {_tail(os.path.join(a.out, 'replan.log'))}")
+    out = os.path.join(a.out, "draw")
+    dr = child(draw_cmd(spec, out, plans, a.extract, slots_of(pt)), os.path.join(a.out, "draw.log"),
+               DRAW_S + CAP_S["draw"], deadline)
+    ledger = os.path.join(out, "ledger.csv")
+    contig = read_json_at(os.path.join(out, "contig.json")) if os.path.exists(os.path.join(out, "contig.json")) else {}
+    peak = peak_rss(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
+    doc = {"point": pt["id"], "host": host, "at": now(), "code": _sweep().code_state(), "extract": a.extract,
+           "extract_sha256": _dollarize().sha256(a.extract),
+           "ledger_sha256": _dollarize().sha256(ledger) if os.path.exists(ledger) else None,
+           "statuses": {c: ch.get("status") for c, ch in sorted(contig.get("channels", {}).items())},
+           "stages": {"replan": rp, "draw": dr}, "peak_rss_bytes": peak, "slots": suggest_slots(host, peak)}
+    _write_json(os.path.join(a.out, "smoke.json"), doc)
+    print(f"smoke {pt['id']} on {host}: ledger {str(doc['ledger_sha256'])[:12]}, {doc['statuses']}, "
+          f"{rp['seconds'] + dr['seconds']:,.0f} s, peak RSS {peak / 2 ** 30:.2f} GiB, slots {doc['slots']}", flush=True)
+    return 0 if doc["ledger_sha256"] and dr["rc"] == 0 else 1
+
+
 # ------------------------------------------------------------------------------ the CLI
 def open_grid(root: str, host: str, extract: str, hours: float) -> Grid:
     """GRID.json at `root`: the one there (a resume, its stop kept), or a new one listing every
@@ -754,6 +1233,27 @@
     r.add_argument("--extract", default=EXTRACT)
     r.add_argument("--notify", default=None, help="a command the run ends with (sweep.py's NOTIFY)")
     r.set_defaults(func=cmd_run)
+    c = sub.add_parser("collect", help="copy another host's points here, sha256 checked, and merge GRID.json")
+    c.add_argument("--from", dest="src", required=True, choices=sorted(SLOTS))
+    c.add_argument("--ssh", default=None, help="the ssh alias (default the host's name; m2-ts over Tailscale)")
+    c.add_argument("--remote-root", default=None, help="the grid there (default --root)")
+    c.add_argument("--root", default=GRID_ROOT)
+    c.add_argument("--anyway", action="store_true", help="copy points that have no label yet")
+    c.set_defaults(func=cmd_collect)
+    m = sub.add_parser("morning", help="render, then write MORNING.md and MORNING.pdf")
+    m.add_argument("--root", default=GRID_ROOT)
+    m.add_argument("--no-render", action="store_true", help="use the maps already there")
+    m.add_argument("--jobs", type=int, default=4, help="renders at once")
+    m.set_defaults(func=cmd_morning)
+    s = sub.add_parser("smoke", help="one point's replan and draw, its ledger sha256 and peak RSS")
+    s.add_argument("--point", default="ne-48-bal")
+    s.add_argument("--out", default=None, help="an empty folder")
+    s.add_argument("--host", default=None, choices=sorted(SLOTS), help="default from the hostname")
+    s.add_argument("--extract", default=EXTRACT)
+    s.add_argument("--hours", type=float, default=2.0, help="the smoke's own stop")
+    s.add_argument("--compare", nargs=2, default=None, metavar=("A", "B"),
+                   help="two smoke.json (host:path over ssh): exit 0 when they match")
+    s.set_defaults(func=cmd_smoke)
     return ap
 
 
```

#### 2. Tests
**File**: `tests/test_overnight.py` (MODIFY)
**Changes**: A unified diff against the file as Phase 5 leaves it (`git apply`). It adds `import re` and seven tests: collect's hashes and merge, the morning order, "Needs your eye", the morning files, titles and `fac`, smoke's slots and comparison, and the subcommands' parsing.

```diff
--- a/tests/test_overnight.py
+++ b/tests/test_overnight.py
@@ -7,6 +7,7 @@
 import importlib.util
 import json
 import os
+import re
 import sys
 import tempfile
 import threading
@@ -255,3 +256,171 @@
     assert r[r.index("--budget") + 1] == "1800" and "--keep-support" in r and "--flow" in r
     assert overnight.slots_of({"k": {"WIFI": 48}}) == 2
     assert overnight.slots_of({"k": dict.fromkeys(("national", "WH", "FI", "WIFI"), 1)}) == 4
+
+
+def test_collect_hashes_and_merge():
+    with tempfile.TemporaryDirectory() as tmp:
+        for rel, body in (("w8-48-bal/r1/ledger.csv", b"a"), ("w8-48-bal/r1/m1.json", b"b"),
+                          ("w8-50-bal/draw/ledger.csv", b"c")):
+            os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
+            with open(os.path.join(tmp, rel), "wb") as fh:
+                fh.write(body)
+        ours = overnight.hash_tree(tmp, ["w8-48-bal", "w8-50-bal"])
+    assert sorted(ours) == ["w8-48-bal/r1/ledger.csv", "w8-48-bal/r1/m1.json", "w8-50-bal/draw/ledger.csv"]
+    listing = "".join(f"{s}  ./{p}\n" for p, s in ours.items())
+    theirs = overnight.parse_shasum(listing)
+    assert theirs == ours and overnight.compare_hashes(theirs, {**ours, "w8-48-bal/r1/summary.png": "x"}) == []
+    bad = {**ours, "w8-48-bal/r1/m1.json": "0" * 64}
+    del bad["w8-50-bal/draw/ledger.csv"]
+    assert overnight.compare_hashes(theirs, bad) == ["differs w8-48-bal/r1/m1.json", "missing w8-50-bal/draw/ledger.csv"]
+    code = {"commit": "c", "dirty": False, "diff_sha256": None}
+    doc = overnight.grid_doc("m5", "/x", "abc", time.time() + 60, code)
+    remote = overnight.grid_doc("m2", "/x", "abc", time.time() + 60, code)
+    remote["points"]["w8-48-bal"].update(status="done", label="eligible", final="w8-48-bal/r1")
+    remote["points"]["w8-48-bal-WH10"] = overnight.record(
+        {"id": "w8-48-bal-WH10", "structure": "west8", "k": {"WH": 10}}, "m2", "w8-48-bal")
+    assert overnight.remote_unlabelled(remote, "m2") == [
+        "w8-48-bal-WH10", "w8-50-bal", "w8-50-filight", "w8-52-bal", "w8-52-filight", "w8-cmp-seed"]
+    got = overnight.merge_remote(doc, remote, "m2", {"from": "m2"})
+    assert len(got) == 7 and doc["points"]["w8-48-bal"]["label"] == "eligible"
+    assert doc["points"]["w8-48-bal-WH10"]["parent"] == "w8-48-bal"
+    assert doc["points"]["w8-48-bal"]["collected"] == {"from": "m2"} and doc["points"]["w1-48"]["status"] == "queued"
+    for bad_remote in ({**remote, "extract_sha256": "zzz"}, {**remote, "host": "m5"}):
+        try:
+            overnight.check_remote(doc, bad_remote, "m2")
+        except ValueError:
+            pass
+        else:
+            raise AssertionError("a GRID.json of another extract or host was merged")
+
+
+def _rec(pid, label, structure="ne_plains", final=None, reason=None, parent=None):
+    ks = {"national": 15, "WH": 11, "FI": 20, "WIFI": 3}
+    return {"id": pid, "structure": structure, "k": ks, "label": label, "reason": reason, "final": final,
+            "status": "done" if label else "running", "parent": parent}
+
+
+def _ordered(pid, label, key=None):
+    return {"id": pid, "label": label, "key": key}
+
+
+def test_morning_order_ranks_labels_and_pairs():
+    rows = [_ordered("ne-52-filight", "eligible", (3, 1.0)), _ordered("w1-48", "stopped"),
+            _ordered("ne-50-bal", "eligible", (2, 5.0)), _ordered("ne-52-bal", "eligible", (2, 0.5)),
+            _ordered("ne-50-filight", "fails M1", (1, 0.0)), _ordered("nw49-48", "infeasible"),
+            _ordered("w8-48-bal", "ineligible ($)", (4, 0.0)), _ordered("x", "error"), _ordered("y", "odd")]
+    got = [r["id"] for r in overnight.morning_order(rows)]
+    assert got == ["ne-52-bal", "ne-52-filight", "ne-50-bal", "ne-50-filight", "w8-48-bal", "nw49-48",
+                   "w1-48", "x", "y"]
+
+
+def test_needs_your_eye_skips_el_paso():
+    ep = ("IFA/IFA_02: neck 5.10 km wide cuts off 3 ZIPs (79734...), 1.0% of its land area and 0.5% of its "
+          "mass; cut 79718-79734 6.14 km")
+    other = ("WH/WH_03: neck 4.00 km wide cuts off 9 ZIPs (10001...), 2.0% of its land area and 1.0% of its "
+             "mass; cut 10001-10002 4.00 km")
+    m = {"m1": {"flips": [{"district": "IFA/IFA_02", "strict": [ep], "gap_width": []},
+                          {"district": "WH/WH_03", "strict": [], "gap_width": [other]}]},
+         "dollars": [{"channel": "WIFI", "district": "WIFI_01", "usd": 1543.0, "lo": 850.0, "hi": 1150.0,
+                      "cap": 1600.0, "allowance": True, "ok": True}],
+         "land": [{"channel": "national", "state": "CA", "ratio": "32.10", "largest": "national_01",
+                   "largest_km2": "90000.0", "smallest": "national_02", "smallest_km2": "2800.0", "over": "1"},
+                  {"channel": "FI", "state": "TX", "ratio": "3.00", "over": "0"}]}
+    got = overnight.eye_items("ne-48-bal", m)
+    assert len(got) == 3
+    assert "WH/WH_03, a neck across coverage gaps only" in got[0] and "79718" not in " ".join(got)
+    assert "WIFI_01 1,543.0M on the whole-state allowance (up to 1,600.0M)" in got[1]
+    assert "national CA in-state land ratio 32.10 beyond R = 10" in got[2]
+
+
+REPORT = ("# r1\ndir: d\neligible: yes\nK: national 15 WH 11 FI 20 WIFI 3 = 49\n"
+          "channel-state splits: 7: national:CA\ndefects: 2.5 = thin 1 + small 0 + crowded 0 + pieces 1.5\n"
+          "shape: extent 1,234.5 km, 4 states per district\nbalance: worst 9.50%, mean 3.25%\n")
+
+
+def test_morning_files_from_a_toy_grid():
+    from PIL import Image
+    doc = overnight.grid_doc("m5", "/hub/instance_descaled_usd.json.gz", "abcdef0123456789", time.time() + 60,
+                             {"commit": "e82d6a4aaaa", "dirty": False, "diff_sha256": None})
+    with tempfile.TemporaryDirectory() as tmp:
+        fin = os.path.join(tmp, "ne-cmp-tierP", "r1")
+        os.makedirs(fin)
+        with open(os.path.join(fin, "score.txt"), "w") as fh:
+            fh.write(REPORT)
+        score.write_dollars(os.path.join(fin, "dollars.csv"), [
+            {"channel": "WH", "district": f"WH_0{i}", "usd": u, "lo": 0.85e9, "hi": 1.15e9, "states": ["NY"],
+             "whole_states": False, "cap": None, "allowance": False, "ok": True}
+            for i, u in ((1, 0.9e9), (2, 1.1e9))])
+        with open(os.path.join(fin, "m1.json"), "w") as fh:
+            json.dump({"strict": {"status": "pass"}, "gap_width": {"status": "pass"}, "flips": []}, fh)
+        with open(os.path.join(fin, "land.csv"), "w") as fh:
+            fh.write("channel,state,ratio,over\nWH,NY,12.50,1\nFI,PA,,0\n")
+        Image.new("RGB", (300, 200), "red").save(os.path.join(fin, "summary.png"))
+        recs = [_rec("ne-cmp-tierP", "eligible", final="ne-cmp-tierP/r1"),
+                _rec("w1-48", "stopped", "w1", reason="not started before the 8 h stop"),
+                _rec("w8-48-bal", None, "west8")]
+        rows = overnight.morning_order([overnight.point_row(tmp, r) for r in recs])
+        assert [r["label"] for r in rows] == ["eligible", "stopped", "error"]
+        assert rows[0]["key"] == (7, 2.5, 1234.5, 4, 0.095, 0.0325)
+        md = overnight.morning_md(doc, rows, ["x"], "2026-10-13T12:00:00+00:00")
+        pdf = os.path.join(tmp, "MORNING.pdf")
+        overnight.morning_pdf(pdf, [(r["final"] and os.path.join(tmp, r["final"], "summary.png"),
+                                     overnight.title_of(r["rec"])) for r in rows])
+        with open(pdf, "rb") as fh:
+            raw = fh.read()
+    assert raw.startswith(b"%PDF") and len(re.findall(rb"/Type\s*/Page\b(?!s)", raw)) == 3
+    lines = md.splitlines()
+    table = [x for x in lines if re.match(r"^\| [123] \|", x)]
+    assert table[0].startswith("| 1 | ne-cmp-tierP | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | 7 | 2.5 | ")
+    assert "WH_01 -10.0% (900.0M)" in table[0] and "pass / pass" in table[0] and "12.5 (1 > R)" in table[0]
+    assert "[map](ne-cmp-tierP/r1/summary.png)" in table[0]
+    assert "| **stopped** | — |" in table[1] and "| **error** | — |" in table[2]
+    assert "- **w8-48-bal** (error): no label (status running)" in lines
+    assert any("#133" in x for x in lines) and "- x" in lines and "1 eligible, 1 stopped, 1 error." in md
+    assert "`e82d6a4`" in md and "sha256 `abcdef012345`" in md
+
+
+def test_titles_and_fac_for_renders():
+    rec = _rec("ne-50-bal", "fails M1")
+    assert overnight.title_of(rec) == "ne-50-bal: ne_plains, K national 15, WH 11, FI 20, WIFI 3 = 49; FAILS M1"
+    assert overnight.title_of(rec, "draw").endswith("(draw, not the final folder)")
+    kid = _rec("ne-50-bal-WH10", "eligible", parent="ne-50-bal")
+    assert overnight.title_of(kid).endswith("; eligible (re-run of ne-50-bal)")
+    with tempfile.TemporaryDirectory() as tmp:
+        fac = json.load(open(overnight.fac_file(tmp)))["fac"]
+        for name in ("draw", "r1", "r2"):
+            os.makedirs(os.path.join(tmp, "ne-50-bal", name))
+            if name != "r2":
+                open(os.path.join(tmp, "ne-50-bal", name, "ledger.csv"), "w").close()
+        jobs = overnight.render_jobs(tmp, [{**rec, "final": "ne-50-bal/r1"}])
+    assert fac == dict.fromkeys(sorted(score.DOLLARS), 1.0)
+    assert [(os.path.basename(f), t.endswith("FAILS M1")) for f, t in jobs] == [("draw", False), ("r1", True)]
+
+
+def test_smoke_slots_and_compare():
+    assert overnight.peak_rss(3 * 2 ** 30, "darwin") == 3 * 2 ** 30
+    assert overnight.peak_rss(1024, "linux") == 2 ** 20
+    assert overnight.suggest_slots("m2", 3 * 2 ** 30) == 8
+    assert overnight.suggest_slots("m2", 4 * 2 ** 30) == 6
+    assert overnight.suggest_slots("m2", 40 * 2 ** 30) == 1
+    assert overnight.suggest_slots("m5", 9 * 2 ** 30) == 12
+    a = {"point": "ne-48-bal", "host": "m5", "extract_sha256": "e", "ledger_sha256": "l",
+         "statuses": {"WH": "optimal"}, "code": {"commit": "c", "diff_sha256": None}, "peak_rss_bytes": 1}
+    assert overnight.compare_smoke(a, {**a, "host": "m2"}) == []
+    got = overnight.compare_smoke(a, {**a, "ledger_sha256": "m", "code": {"commit": "d", "diff_sha256": None}})
+    assert got == ["ledger_sha256: 'l' vs 'm'", "code: ('c', None) vs ('d', None)"]
+    with tempfile.TemporaryDirectory() as tmp:
+        path = os.path.join(tmp, "smoke.json")
+        with open(path, "w") as fh:
+            json.dump(a, fh)
+        assert overnight.read_json_at(path) == a
+
+
+def test_subcommands_parse():
+    p = overnight.parser()
+    c = p.parse_args(["collect", "--from", "m2"])
+    assert (c.src, c.ssh, c.remote_root, c.anyway, c.root) == ("m2", None, None, False, overnight.GRID_ROOT)
+    m = p.parse_args(["morning", "--no-render"])
+    assert m.no_render and m.jobs == 4 and m.func is overnight.cmd_morning
+    s = p.parse_args(["smoke", "--compare", "a.json", "m2:/tmp/b.json"])
+    assert s.compare == ["a.json", "m2:/tmp/b.json"] and s.point == "ne-48-bal" and s.func is overnight.cmd_smoke
```

#### 3. CODE_MAP rows
**File**: `docs/CODE_MAP.md` (MODIFY)
**Changes**: Insert these four rows immediately after the `tests/test_dollarize.py` row that Phase 1 added.

```markdown
| `tools/exp/contig/land.py` | #133's land balance on run folders (the main-map overnight grid, 2026-10-13): `land.csv`, one row per split group, the in-state land ratio (largest over smallest, over the pieces holding 20% or more of their district's mass, every piece's ratio beside it) against R; the draw holds it softly (`draw.py`'s land term, `run.py --land-ratio`), the repair reports what it moved |
| `tools/exp/contig/overnight.py` | the main-map overnight grid (2026-10-13): 21 points, five WIFI structures by K totals 48-52 on the dollar extract; `run` plans each point (τ, the base spec's or #76's split list, the final δ fitting the dollar window), runs #125's chain (`replan.py` → `run.py` arm 1 sequential with the land term → `repair.py` pass 1, pass 2 when M1 fails) as child processes under the settled stop/retry policy and labels it in `GRID.json` (resumable); `collect` copies m2's points to m5 sha256-checked and merges its GRID.json; `morning` renders ($M, `fac_usd.json`) and writes `MORNING.md` and `MORNING.pdf`; `smoke` draws one point before the launch and records its ledger sha256 and peak RSS |
| `tests/test_land.py`, `tests/test_neck_gapwidth.py` | the land term's toy MILP and `land_rows` by hand; `d312834`'s gap-width neck test and `check_m1`'s `gap_width` override |
| `tests/test_overnight.py` | the launcher on toys: the δ fit, the split rule, the spec copy, the retry, labels, the re-run direction, the scheduler, a stage's kill, resume, GRID.json; collect's hashes and merge, the morning order, table, "Needs your eye" and PDF, the render titles, smoke's slots and comparison |
```

### Success Criteria:

#### Automated Verification:
- [ ] Slice tests pass: `"$TD_PY" tests/run_all.py -k test_overnight.py 2>&1 | tail -1` shows `19 passed, 0 failed`
- [ ] Slice 5's surface is unchanged: `rg -c '^def (plan_point|fit_delta|point_spec_text|needs_retry|label_of|rerun_k|schedule|child)\(' tools/exp/contig/overnight.py` prints 8 and `rg -c '^    _point\(' tools/exp/contig/overnight.py` prints 21
- [ ] The new subcommands' surface is present: `rg -c '^def (cmd_collect|cmd_morning|cmd_smoke|merge_remote|compare_hashes|morning_order|morning_md|morning_pdf|eye_items|compare_smoke|suggest_slots)\(' tools/exp/contig/overnight.py` prints 11
- [ ] The CLI has all four subcommands: `"$TD_PY" tools/exp/contig/overnight.py --help | rg -q '\{run,collect,morning,smoke\}'` exits 0
- [ ] Renders run under the G3 gate: `rg -n 'RENDER_S, time.time\(\) \+ RENDER_S \+ 60, GAP_ENV' tools/exp/contig/overnight.py` prints one line
- [ ] The launcher still never deletes a run folder: `rg -n 'rmtree|os\.remove|os\.unlink' tools/exp/contig/overnight.py` prints nothing
- [ ] CODE_MAP rows present: `rg -c '^\| .(tools/exp/contig/overnight\.py|tools/exp/contig/land\.py|tests/test_overnight\.py|tests/test_land\.py).' docs/CODE_MAP.md` prints 4
- [ ] The doc checks still pass: `"$TD_PY" tests/run_all.py -k test_docs_owners.py 2>&1 | tail -1` shows `0 failed`

#### Manual Verification:
- [ ] On m5, after Slice 5's dry run (`/tmp/td-grid-dry`): `"$TD_PY" tools/exp/contig/overnight.py morning --root /tmp/td-grid-dry --no-render` writes `MORNING.md` with the five assumptions, one table row per point (15 **stopped**, the six west8 points **error** "no label (status elsewhere)"), each west8 point under "Needs your eye", and a 21-page `MORNING.pdf` whose pages name the point, its K and its label
- [ ] On m5, `morning` on a copy of one tier-P main-map folder laid out as `<root>/<id>/r1` (with a GRID.json record whose `final` is it) renders `r1` with `--fac <root>/fac_usd.json`: `render.json`'s `fac.path` is `fac_usd.json`, the page title ends with the record's label, and the $ in the summary's caption equals `dollars.csv`'s to 0.1M
- [ ] `"$TD_PY" tools/exp/contig/overnight.py smoke --out /tmp/td-smoke-x --extract "$TD_REPO/instance_descaled.json.gz"` refuses with "is not a dollar extract", and `smoke --compare` on one `smoke.json` given twice prints "match" and exits 0
- [ ] With m2 reachable and no grid there, `"$TD_PY" tools/exp/contig/overnight.py collect --from m2 --root /tmp/td-grid-dry` exits with `ssh m2 'cat /tmp/td-grid-dry/GRID.json' exited 1` and leaves `/tmp/td-grid-dry/GRID.json` unchanged (its sha256 before and after)

---

## Phase 7: Pre-launch gates

### Overview
The five tracked base specs the launcher reads (`STRUCTURES`) and three tests on them, then the pre-launch gates on both Studios: dollarize, tests, the plan check, smoke compare, the `w1-50` smoke, m2 quiet, masking. Code must be committed, pushed and pulled on m2 before the manual gates.

### Changes Required:

#### 1. ne_plains
**File**: `scenarios/main_ne_plains.toml` (NEW)
**Changes**: s13_WH11 verbatim with a header and the name `main_ne_plains` (D10).

```toml
# The main-map overnight grid's ne_plains structure (2026-10-13, tools/exp/contig/overnight.py):
# the lead-map layout of the six tier-P maps, ported from the hub's untracked
# runs/exp/contig/wh_dollar/s13_WH11.toml (set125.sh's seed) with its lists unchanged (D10).
# WIFI is 15 whole states, New England and the plains, holding all five fine channels; national,
# WH and FI plan the other 34 units apart under the #67 rule.  The launcher sets each channel's k,
# delta and final_delta per grid point on the dollar extract; the split lists are this file's.

[scenario]
name = "main_ne_plains"
fine_channels = ["national_chase", "wells_wh", "wells_fi", "wh", "fi"]
delta = 0.1
planned_elsewhere = ["career", "edj", "ifa", "imo", "priafs"]

[channels.national]
margin = false
k = 15
domain = [{ units = ["MS", "DE", "WV", "DC", "AR", "IA", "OR", "TN", "AL", "WI", "KY", "MO", "SC", "NV", "LA", "MN", "IN", "UT", "WA", "MD", "CO", "GA", "OH", "VA", "MI", "AZ", "PA", "NC", "IL", "NJ", "FL", "NY", "TX", "CA"], fine = ["national_chase", "wells_wh", "wells_fi"] }]
mode = "whole"
eta = 0.05
max_size = 5
max_dist_km = 900
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600, CO = 1600 }
contact_caps = { CA = 4 }
free = ["CA", "FL", "NY", "TX"]
delta = 0.0938
final_delta = 0.1

[channels.WH]
margin = false
k = 11
domain = [{ units = ["AL", "AR", "AZ", "CA", "CO", "DC", "DE", "FL", "GA", "IA", "IL", "IN", "KY", "LA", "MD", "MI", "MN", "MO", "MS", "NC", "NJ", "NV", "NY", "OH", "OR", "PA", "SC", "TN", "TX", "UT", "VA", "WA", "WI", "WV"], fine = ["wh"] }]
mode = "whole"
eta = 0.05
max_size = 4
max_dist_km = 900
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600, CO = 1600 }
contact_caps = { CA = 4 }
free = ["CA", "FL", "NJ", "NY", "PA", "TX"]
delta = 0.090
final_delta = 0.1

[channels.FI]
margin = false
k = 20
domain = [{ units = ["AL", "AR", "AZ", "CA", "CO", "DC", "DE", "FL", "GA", "IA", "IL", "IN", "KY", "LA", "MD", "MI", "MN", "MO", "MS", "NC", "NJ", "NV", "NY", "OH", "OR", "PA", "SC", "TN", "TX", "UT", "VA", "WA", "WI", "WV"], fine = ["fi"] }]
mode = "whole"
eta = 0.15
max_size = 6
max_dist_km = 900
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600, CO = 1600 }
contact_caps = { CA = 4 }
free = ["CA", "FL", "NC", "NY", "OH", "PA", "TN", "TX"]
delta = 0.08
final_delta = 0.1

[channels.WIFI]
margin = false
k = 3
domain = [{ units = ["ME", "NH", "VT", "MA", "RI", "CT", "ID", "MT", "ND", "NE", "SD", "WY", "NM", "OK", "KS"], fine = ["wh", "fi", "national_chase", "wells_wh", "wells_fi"] }]
mode = "whole"
eta = 0.05
delta = 0.1
max_size = 9
max_dist_km = 5000
final_delta = 0.1

[national]
channel = "national"
fine = ["national_chase", "wells_wh", "wells_fi"]
units = ["MS", "DE", "WV", "DC", "AR", "IA", "OR", "TN", "AL", "WI", "KY", "MO", "SC", "NV", "LA", "MN", "IN", "UT", "WA", "MD", "CO", "GA", "OH", "VA", "MI", "AZ", "PA", "NC", "IL", "NJ", "FL", "NY", "TX", "CA"]
fallback = { national_chase = "fi", wells_fi = "fi", wells_wh = "wh" }
```

#### 2. west8
**File**: `scenarios/main_west8.toml` (NEW)
**Changes**: Scenario 51's national, WH and FI with each `free` list on one line. WIFI is `west`, whole, max_size 8, max_dist_km 5000 (D11).

```toml
# The main-map overnight grid's west8 structure (2026-10-13, tools/exp/contig/overnight.py):
# scenario 51 (51_total_13n_11wh_24fi_3wifi.toml) with its national, WH and FI rules and split
# lists unchanged (D10, D11) and WIFI made one whole-state support over the eight western units
# (the listed blocks and their inert delta 1.0 dropped), so WIFI at K1 may use the $1.6B
# whole-state allowance.  Each split list sits on one line, as replan.py's --free rewrite needs.
# The launcher sets each channel's k, delta and final_delta per grid point on the dollar extract.

[scenario]
name = "main_west8"
fine_channels = ["national_chase", "wells_wh", "wells_fi", "wh", "fi"]
planned_elsewhere = ["career", "edj", "ifa", "imo", "priafs"]
delta = 0.10                    # OD1's default final band, per channel

[sets]
west = ["CO", "ID", "MT", "ND", "NE", "NM", "SD", "WY"]
new_england = ["CT", "MA", "ME", "NH", "RI", "VT"]
southeast = ["AL", "FL", "GA", "SC"]

# The owner's purity and fallback rule (#67): a unit with national keeps national chase, wells WH
# and wells FI in national; a unit without it sends national chase and wells FI with FI, and
# wells WH with WH.  In the west WH and FI are both WIFI, so all five go there.
[national]
channel = "national"
fine = ["national_chase", "wells_wh", "wells_fi"]
units = "all - west"
fallback = { national_chase = "fi", wells_fi = "fi", wells_wh = "wh" }

[channels.national]
k = 13
domain = [{ units = "all - west", fine = ["national_chase", "wells_wh", "wells_fi"] }]
mode = "whole"
free = ["CA", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "FL", "GA", "VA", "MI"]
eta = 0.05                      # legacy 51 value; policy
max_size = 6                    # legacy 51 value; policy
max_dist_km = 900               # legacy 51 value; policy
# legacy 51 values; policy (CA was CA1 1600 and CA2 1500 there)
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600 }
contact_caps = { CA = 4 }       # legacy 51 value; policy (CA1 and CA2 at 2 each)
# The legacy National filter, ported closed (C19): New England with NY as one extra support,
# New England units paired only with each other and NY, FL alone, MS apart from the southeast.
extra_supports = [["new_england", "NY"]]
confine = [
    { units = "new_england", partners = ["new_england", "NY"] },
    { units = ["FL"], partners = [] },
]
forbid_pairs = [["MS", "AL"], ["MS", "FL"], ["MS", "GA"], ["MS", "SC"]]

[channels.WH]
k = 11
domain = [{ units = "all - west", fine = ["wh"] }]
mode = "whole"
free = ["CA", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "MI", "GA", "FL", "MO", "KY", "TN", "VA", "IN"]
eta = 0.05                      # legacy 51 value; policy
max_size = 6                    # legacy 51 value; policy
max_dist_km = 900               # legacy 51 value; policy
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600 }
contact_caps = { CA = 4 }       # legacy 51 value; policy

[channels.FI]
k = 24
domain = [{ units = "all - west", fine = ["fi"] }]
mode = "whole"
free = ["CA", "TX", "NY", "NJ", "IL", "NC", "PA", "OH", "FL", "GA", "VA", "MI", "KY", "TN", "MO", "IN", "AR"]
eta = 0.05                      # legacy 51 value; policy
max_size = 6                    # legacy 51 value; policy
max_dist_km = 900               # legacy 51 value; policy
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600 }
contact_caps = { CA = 4 }       # legacy 51 value; policy

# WIFI: the eight western units whole, all five fine channels, one support of them all (owner,
# 2026-10-12): the K1 district holds every unit, so max_size is 8 and the distance cap is lifted.
[channels.WIFI]
k = 1
domain = [{ units = "west", fine = ["national_chase", "wells_wh", "wells_fi", "wh", "fi"] }]
mode = "whole"
eta = 0.05                      # legacy 51 value; policy
max_size = 8
max_dist_km = 5000
```

#### 3. nw49
**File**: `scenarios/main_nw49.toml` (NEW)
**Changes**: National plus WIFI over all 49 units, with no split lists (#76 per point).

```toml
# The main-map overnight grid's nw49 structure (2026-10-13, tools/exp/contig/overnight.py):
# national + WIFI over all 49 units.  Every unit has national, so national holds national chase,
# wells WH and wells FI everywhere and WIFI holds WH and FI everywhere; WIFI units may split.
# No split list here: the launcher computes one per grid point by the #76 rule (units whose
# channel $ exceeds half a district) and passes it to replan.py, and sets k, delta and
# final_delta.  Support values are scenario 50's (50_ifa.toml), the one channel planned over all
# 49 units at a comparable K (policy).

[scenario]
name = "main_nw49"
fine_channels = ["national_chase", "wells_wh", "wells_fi", "wh", "fi"]
planned_elsewhere = ["career", "edj", "ifa", "imo", "priafs"]
delta = 0.10                    # OD1's default final band; the launcher sets each channel's

[national]
channel = "national"
fine = ["national_chase", "wells_wh", "wells_fi"]
units = "all"

[channels.national]
k = 16
domain = [{ units = "all", fine = ["national_chase", "wells_wh", "wells_fi"] }]
mode = "whole"
eta = 0.05                      # legacy 51 value; policy
max_size = 6                    # legacy 51 value; policy
max_dist_km = 900               # legacy 51 value; policy
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600 }

[channels.WIFI]
k = 34
domain = [{ units = "all", fine = ["wh", "fi"] }]
mode = "whole"
eta = 0.05                      # legacy 51 value; policy
max_size = 6                    # legacy 51 value; policy
max_dist_km = 900               # legacy 51 value; policy
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600 }
```

#### 4. nw34
**File**: `scenarios/main_nw34.toml` (NEW)
**Changes**: National over the 34 non-ne_plains units with the #67 fallback. WIFI holds wh and fi everywhere, plus national fine channels on the 15.

```toml
# The main-map overnight grid's nw34 structure (2026-10-13, tools/exp/contig/overnight.py):
# national + WIFI, national over the 34 units ne_plains plans it in.  The 15 New England and
# plains units have no national, so the #67 fallback sends their national chase and wells FI
# with FI and their wells WH with WH, both in WIFI: WIFI holds WH and FI everywhere and all five
# fine channels there.  WIFI units may split.  No split list here: the launcher computes one per
# grid point by the #76 rule and sets k, delta and final_delta.  National's support values are
# ne_plains' (the same 34 units); WIFI's are scenario 50's (50_ifa.toml), the one channel planned
# over all 49 units at a comparable K (policy).

[scenario]
name = "main_nw34"
fine_channels = ["national_chase", "wells_wh", "wells_fi", "wh", "fi"]
planned_elsewhere = ["career", "edj", "ifa", "imo", "priafs"]
delta = 0.10                    # OD1's default final band; the launcher sets each channel's

[sets]
ne_plains = ["ME", "NH", "VT", "MA", "RI", "CT", "ID", "MT", "ND", "NE", "SD", "WY", "NM", "OK", "KS"]

[national]
channel = "national"
fine = ["national_chase", "wells_wh", "wells_fi"]
units = "all - ne_plains"
fallback = { national_chase = "fi", wells_fi = "fi", wells_wh = "wh" }

[channels.national]
margin = false
k = 15
domain = [{ units = "all - ne_plains", fine = ["national_chase", "wells_wh", "wells_fi"] }]
mode = "whole"
eta = 0.05
max_size = 5
max_dist_km = 900
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600, CO = 1600 }
contact_caps = { CA = 4 }

[channels.WIFI]
k = 35
domain = [{ units = "all", fine = ["wh", "fi"] },
          { units = "ne_plains", fine = ["national_chase", "wells_wh", "wells_fi"] }]
mode = "whole"
eta = 0.05                      # legacy 51 value; policy
max_size = 6                    # legacy 51 value; policy
max_dist_km = 900               # legacy 51 value; policy
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600 }
```

#### 5. w1
**File**: `scenarios/main_w1.toml` (NEW)
**Changes**: A single WIFI channel over all five fine channels and all 49 units.

```toml
# The main-map overnight grid's w1 structure (2026-10-13, tools/exp/contig/overnight.py): the
# original single WIFI channel, all five fine channels over all 49 units, no national (the
# baseline grid point).  No split list here: the launcher computes one per grid point by the #76
# rule and sets k, delta and final_delta.  Support values are scenario 50's (50_ifa.toml), the
# one channel planned over all 49 units at a comparable K (policy).

[scenario]
name = "main_w1"
fine_channels = ["national_chase", "wells_wh", "wells_fi", "wh", "fi"]
planned_elsewhere = ["career", "edj", "ifa", "imo", "priafs"]
delta = 0.10                    # OD1's default final band; the launcher sets each channel's

[channels.WIFI]
k = 50
domain = [{ units = "all", fine = ["national_chase", "wells_wh", "wells_fi", "wh", "fi"] }]
mode = "whole"
eta = 0.05                      # legacy 51 value; policy
max_size = 6                    # legacy 51 value; policy
max_dist_km = 900               # legacy 51 value; policy
dist_km = { WA = 1600, TX = 1200, OR = 1000, UT = 1100, AZ = 1100, LA = 1150, CA = 1600 }
```

#### 6. Base-spec tests
**File**: `tests/test_overnight.py` (MODIFY)
**Changes**: A unified diff against the file as Phase 6 leaves it (`git apply`). It adds `import math` and the three base-spec tests (load and fit, footprints, the launcher's rewrites). Afterwards the file is byte-identical to the design's fence.

```diff
--- a/tests/test_overnight.py
+++ b/tests/test_overnight.py
@@ -6,6 +6,7 @@
 import collections
 import importlib.util
 import json
+import math
 import os
 import re
 import sys
@@ -424,3 +425,100 @@
     assert m.no_render and m.jobs == 4 and m.func is overnight.cmd_morning
     s = p.parse_args(["smoke", "--compare", "a.json", "m2:/tmp/b.json"])
     assert s.compare == ["a.json", "m2:/tmp/b.json"] and s.point == "ne-48-bal" and s.func is overnight.cmd_smoke
+
+
+# ------------------------------------------------ the base specs (the pre-launch gates, Slice 7)
+NE_PLAINS = {"ME", "NH", "VT", "MA", "RI", "CT", "ID", "MT", "ND", "NE", "SD", "WY", "NM", "OK", "KS"}
+WEST = {"CO", "ID", "MT", "ND", "NE", "NM", "SD", "WY"}
+ALL = set(tdspec.CONUS_STATES)
+FIVE = {"national_chase", "wells_wh", "wells_fi", "wh", "fi"}
+NATIONAL_FINE = {"national_chase", "wells_wh", "wells_fi"}
+
+
+def _base(structure):
+    path = os.path.join(overnight.ROOT, overnight.STRUCTURES[structure][0])
+    with open(path, encoding="utf-8") as fh:
+        return tdspec.load(path), fh.read(), overnight.STRUCTURES[structure][1]
+
+
+def _free(cs):
+    return sorted(u for u, m in cs.modes.items() if m == "free")
+
+
+def test_base_specs_load_and_fit_every_point():
+    assert set(overnight.STRUCTURES) == {p["structure"] for p in overnight.POINTS}
+    cells = {(u, f): 1.0 for u in ALL for f in FIVE}
+    for structure in overnight.STRUCTURES:
+        sp, text, rule = _base(structure)
+        assert sp.name == f"main_{structure}" and re.search(r'(?m)^name = ".*"$', text)
+        assert set(sp.fine_channels) == FIVE
+        assert {"career", "edj", "imo", "priafs"} <= set(sp.planned_elsewhere)   # no owner total
+        mass = overnight.unit_mass(sp, cells)                                     # units are states
+        assert math.fsum(m for c in mass.values() for m in c.values()) == len(ALL) * len(FIVE)
+        for pt in overnight.POINTS:
+            if pt["structure"] == structure:
+                assert set(pt["k"]) == set(sp.channels), pt["id"]
+        free = {c: _free(cs) for c, cs in sp.channels.items()}
+        if rule == "rule":
+            assert not any(free.values()), structure                              # #76 per point
+        else:
+            assert free.pop("WIFI") == [] and all(free.values()), structure       # whole-state cap
+
+
+def test_base_footprints():
+    ne, _, _ = _base("ne_plains")
+    assert ne.channels["WIFI"].units == NE_PLAINS and set(ne.channels["WIFI"].domain.values()) == {frozenset(FIVE)}
+    assert all(ne.channels[c].units == ALL - NE_PLAINS for c in ("national", "WH", "FI"))
+    assert ne.national.units == ALL - NE_PLAINS
+    assert [_free(ne.channels[c]) for c in ("national", "WH", "FI")] == [            # s13_WH11's (D10)
+        ["CA", "FL", "NY", "TX"], ["CA", "FL", "NJ", "NY", "PA", "TX"],
+        ["CA", "FL", "NC", "NY", "OH", "PA", "TN", "TX"]]
+    assert ne.channels["WIFI"].max_size == 9 and not ne.channels["WIFI"].listed_only
+
+    w8, _, _ = _base("west8")
+    s51 = tdspec.load(os.path.join(overnight.ROOT, "scenarios", "51_total_13n_11wh_24fi_3wifi.toml"))
+    assert all(w8.channels[c] == s51.channels[c] for c in ("national", "WH", "FI"))  # D11
+    assert w8.national == s51.national
+    wifi = w8.channels["WIFI"]
+    assert wifi.units == WEST and set(wifi.domain.values()) == {frozenset(FIVE)}
+    assert (wifi.listed_only, wifi.extra_supports, wifi.max_size, wifi.max_dist_km) == (False, (), 8, 5000.0)
+    assert set(wifi.modes.values()) == {"whole"}
+
+    nw49, _, _ = _base("nw49")
+    assert nw49.channels["national"].units == ALL and nw49.national.units == ALL
+    assert set(nw49.channels["national"].domain.values()) == {frozenset(NATIONAL_FINE)}
+    assert nw49.channels["WIFI"].units == ALL
+    assert set(nw49.channels["WIFI"].domain.values()) == {frozenset({"wh", "fi"})}
+
+    nw34, _, _ = _base("nw34")
+    n34, n = nw34.channels["national"], ne.channels["national"]
+    assert n34.units == ALL - NE_PLAINS and nw34.national.units == ALL - NE_PLAINS
+    assert ((n34.eta, n34.max_size, n34.max_dist_km, n34.dist_km, n34.contact_caps, n34.margin)
+            == (n.eta, n.max_size, n.max_dist_km, n.dist_km, n.contact_caps, n.margin))
+    assert all(f == (FIVE if u in NE_PLAINS else {"wh", "fi"}) for u, f in nw34.channels["WIFI"].domain.items())
+    assert nw34.channels["WIFI"].units == ALL
+
+    w1, _, _ = _base("w1")
+    assert list(w1.channels) == ["WIFI"] and w1.national is None
+    assert w1.channels["WIFI"].units == ALL and set(w1.channels["WIFI"].domain.values()) == {frozenset(FIVE)}
+    for s in ("nw49", "nw34", "w1"):                     # scenario 50's support values (policy)
+        sp, _, _ = _base(s)
+        w = sp.channels["WIFI"]
+        assert (w.eta, w.max_size, w.max_dist_km, w.dist_km["CA"], w.margin) == (0.05, 6, 900.0, 1600.0, True)
+
+
+def test_base_specs_take_the_launchers_rewrites():
+    banned_text = overnight._replan().banned_text
+    for structure in overnight.STRUCTURES:
+        sp, text, rule = _base(structure)
+        pt = next(p for p in overnight.POINTS if p["structure"] == structure)
+        plan = {"channels": {c: {"k": k, "final_delta": 0.05} for c, k in pt["k"].items()}}
+        copy = overnight.point_spec_text(text, pt["id"], plan)
+        got = tdspec.parse(tomllib.loads(copy))
+        assert got.name == pt["id"]
+        assert {c: (cs.k, cs.delta, cs.final_delta) for c, cs in got.channels.items()} == \
+            {c: (k, 0.02, 0.05) for c, k in pt["k"].items()}
+        free = ({c: _free(cs) for c, cs in sp.channels.items() if _free(cs)} if rule == "base"
+                else {c: ["CA", "TX"] for c in sp.channels})               # replan.py --free's rewrite
+        out = tdspec.parse(tomllib.loads(banned_text(copy, [], free=free)))
+        assert {c: _free(cs) for c, cs in out.channels.items() if c in free} == free, structure
```

### Success Criteria:

#### Automated Verification:
- [ ] Slice tests pass: `"$TD_PY" tests/run_all.py -k test_overnight.py 2>&1 | tail -1` shows `22 passed, 0 failed`
- [ ] The five base specs are tracked: `git ls-files 'scenarios/main_*.toml' | wc -l` prints 5
- [ ] Each base spec loads (partition and #67 checks included): `"$TD_PY" -c 'from td import spec; [spec.load(f"scenarios/main_{s}.toml") for s in ("ne_plains", "west8", "nw49", "nw34", "w1")]'` exits 0
- [ ] Every split list sits on one line, as replan.py's `--free` rewrite needs: `rg -n '^free = \[[^\]]*$' scenarios/main_*.toml` prints nothing
- [ ] Every point's name line is rewritable: `rg -c '^name = "main_[a-z0-9_]+"$' scenarios/main_*.toml` prints 1 for each of the five files
- [ ] No extract staged or tracked: `git status --porcelain | rg 'instance_descaled'` and `git ls-files | rg 'instance_descaled'` print nothing
- [ ] The whole fast suite passes (project baseline): `"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '` ends with `0 failed` (429 passed in a scratch copy with Slices 1-7 applied)

#### Manual Verification:
- [ ] Code committed and pushed to `m5-studio/national-overnight`, and m2's checkout of that branch at the same commit: `git rev-parse HEAD` on m5 equals `ssh m2 'git -C <m2 checkout> rev-parse HEAD'`
- [ ] Dollar extract on both Studios (Slice 1's command on each): `shasum -a 256 "$TD_REPO/instance_descaled_usd.json.gz"` equal on m5 and m2, and `git -C "$TD_REPO" check-ignore -q instance_descaled_usd.json.gz` exits 0 on both
- [ ] Tests pass on both Studios: `"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '` ends with `0 failed` on m5 and on m2
- [ ] Every point plans inside its window on the real dollar extract (aggregates only): `"$TD_PY" -c 'import importlib.util as u; s = u.spec_from_file_location("o", "tools/exp/contig/overnight.py"); o = u.module_from_spec(s); s.loader.exec_module(o); from td import spec; c = o.state_cells(o.EXTRACT); [print(p["id"], {k: (round(v["usd_m"]), round(v["tau_m"]), v["final_delta"]) for k, v in pl["channels"].items()}, pl["infeasible"] or "") for p in o.POINTS for pl in [o.plan_point(p["k"], spec.load(o.STRUCTURES[p["structure"]][0]), c, o.STRUCTURES[p["structure"]][1])]]'` prints 21 lines with no infeasible channel, channel totals equal research §10 ($M: ne_plains N 16,896 / WH 10,139 / FI 18,504 / WIFI 3,370; west8 16,981 / 10,754 / 19,631 / 1,543; nw49 N 17,535 / WIFI 31,374; nw34 16,896 / 32,013; w1 48,909) and the tightest final δ nw49-52 national 0.0305 (draft-spec check on the m_rel extract × E1 rates, 2026-10-13)
- [ ] Smoke on both Studios from the same commit: `"$TD_PY" -u tools/exp/contig/overnight.py smoke --point ne-48-bal --out /tmp/td-smoke-$(hostname -s)` on m5 and on m2, then `smoke --compare /tmp/td-smoke-<m5>/smoke.json m2:/tmp/td-smoke-<m2>/smoke.json` prints "match" and exits 0; m2's `smoke.json` `slots` (6-8) is the `--slots` m2 launches with
- [ ] The new structures' support families plan: on m5, `"$TD_PY" -u tools/exp/contig/overnight.py smoke --point w1-50 --out /tmp/td-smoke-w1 --hours 1.5` gets past replan (`replan.log` gives a plan for WIFI, no "no plan"), its `smoke.json` peak RSS and seconds noted as the first main-map timing of a 50-district channel (research's timing risk); a "no plan" here is reported to the owner before launch, never patched by loosening the spec
- [ ] m2 is quiet: `ssh m2 'top -l 1 -o cpu -n 5'` shows no `photolibraryd` above 10% CPU
- [ ] Masking on both Studios: `git -C "$TD_REPO" status --porcelain | rg instance_descaled` prints nothing on m5 and m2

---

## Testing Strategy

### Automated:
- Each phase's slice tests: `"$TD_PY" tests/run_all.py -k <test file>`, with counts as in each phase's Success Criteria (dollarize 6, looks_score 15, neck_gapwidth 3, land 6, overnight 12 → 19 → 22).
- Whole plan (owned by validate): `"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '` ends with `0 failed`. In a scratch copy of HEAD with Phases 1–7 applied it gave 429 passed, 0 failed, 0 skipped (2026-10-13, m5).
- Masking: `git status --porcelain | rg 'instance_descaled'` and `git ls-files | rg 'instance_descaled'` print nothing.

### Manual Testing Steps:
Reference only: the design's Verification Notes. Each phase's Manual Verification already holds the checks that count.

- Trap 12: every certifying solve keeps `mip_rel_gap = 0`; the land columns must not change `draw.py:876`. `rg -n 'mip_rel_gap' tools/exp/contig/draw.py` still shows 0.0.
- Trap 15: retries key on the solver's own stop reason (run.py / repair.py exit code and contig.json group statuses, `unknown` notes), never on a harness status.
- Trap 18: one thread count per process; `run.py --jobs N` pins 1 thread per worker (`run.py:332-341`); the launcher never mixes thread counts in one process.
- Trap 19: the land term adds cost, never replaces the objective with zero.
- Masking: `git check-ignore -q instance_descaled_usd.json.gz` on both Studios; `git status --porcelain` shows no extract; export_long writes no shares, reps or firms.
- Re-gate everything (precedents `1293d41`, `20cfe36`): no cached ELIGIBLE; every point's verdict is recomputed by `score.py` under the new windows.
- G3: both M1 verdicts per folder; every flip other than TX El Paso (79718–79734) goes to MORNING's "Needs your eye".
- Draw-term precedent (`71517c8` → `9378ee4`, `b70299f`, `c26ed48`): exact rows and a toy MILP test on day one; a seed drawing must pass `accept` with the new columns set.
- Scorer precedent (`2d189e9`): whole-dollar inclusive window edges, tested at both edges.
- export_long precedent (`21d9cb4`, `ef5d761`): scenario-id convention unchanged; reversal tested.
- Gap-width precedent (`46d2d89`): cherry-pick `d312834` only; never `46d2d89`.
- Launcher precedent (`66bab5d`, `a2a3867`): resume per point from GRID.json on day one.
- The draw and the ledger mass column hold $M on dollar runs; the column keeps the name `m_rel` (schema unchanged); run.json `source` and manifest `instance_sha256` identify the extract.
- Timing risk: single WIFI and national + WIFI draws (33–52 districts in one channel) have no main-map timing; the smoke measures peak RSS, the 8 h stop bounds wall time.

Ordering on the night (design's Ordering Constraints): dollarize on both Studios → tests on both → smoke on both (compare ledger sha256, read peak RSS, set m2 slots) → launch.

## Performance Considerations

- The land term adds per split state ≤ h(h−1) continuous columns and rows (h = holders ≥ 0.2τ, typically 2–4), small next to x and border pairs.
- Dollar scaling keeps cell magnitudes at m_rel's scale (×1.18–1.25), so no tolerance retuning.
- `score.py` loads the dollar extract once per process (`rates_of` cache); `dollar_gate` is linear in the ledger.
- Slots = channels per point; m5 at 12 holds three four-channel points; m2's slots come from the smoke's peak RSS.
- `land.py` reads `polygon_graph()` once per call (aland, state).

## Migration Notes

No schema change: the dollar extract is `td_instance_descaled/3` with an extra `meta.dollar_scale`, the ledger keeps its columns, and old m_rel runs still score (rates from their own extract). The plan cache keys on the extract sha (`run.py:108`), so dollar plans never mix with m_rel plans. Rollback: drop the branch; nothing on main changes.

## Developer Context

**Parallelism** (design's Ordering Constraints): Phase 1 comes first. Phases 2 → 3 run in order because both edit `tools/looks/score.py`. Phase 4 is independent of Phases 2–3 and can run beside them after Phase 1. Phase 5 needs Phases 1–4: it reads the dollar extract (1), `score.write_dollars` (2), `audit.GAP_WIDTH_ENV` (3) and `run.py --land-ratio` (4). Phases 5 → 6 → 7 run in order because they share `overnight.py` / `tests/test_overnight.py`. Phases 1 and 6 both edit `docs/CODE_MAP.md` and are already ordered. Slice 7's manual gates run only after all code is committed, pushed and pulled on m2.

**Splitting the merged fences (plan, 2026-10-13):** Three Architecture fences cover more than one slice:
- `tools/looks/score.py`: Slices 2 and 3;
- `tools/exp/contig/overnight.py`: Slices 5 and 6;
- `tests/test_overnight.py`: Slices 5, 6 and 7.

The design's CODE_MAP fence also holds the rows for both Slice 1 and Slice 6.

Applying the merged `score.py` fence in Phase 2 would break Phase 2's own tests: `m1_check` would pass `gap_width=` to `check_m1`, which only exists after Phase 3. So each was split along the boundaries the design names:
- `score.py`: Slice 3 owns the docstring sentence on necks, `m1_check(gap_width=)`, `m1_both`, `write_m1`, the report's M1 suffix and `--m1-json`.
- `overnight.py`: Slice 6 owns `collect`, `morning` and `smoke`, their constants and imports, and the docstring's paragraphs on them.
- `tests/test_overnight.py`: Slice 6 appends seven tests and `import re`; Slice 7 adds the last three tests and `import math`.

The split was done by script, not rewritten by hand. In a scratch copy of HEAD (`git archive` → `/tmp/plan-work/scratch`), the phases were applied in order 1 → 7:
- Each phase's slice tests gave the design's counts (6; 15, with `test_dollarize` 6 and `test_mandates` 0 failed; 3, with `test_audit` 48 and 0 failed; 6, with `test_contig_realize` 52; 12; 19, with `test_docs_owners` 0 failed; 22).
- Every static Automated Verification line (rg counts, `git diff` checks, `--help` choices) held at its phase.
- An AST check found no undefined names and no unused imports in any intermediate file.
- After Phase 3 `score.py`, after Phase 6 `overnight.py` and after Phase 7 `tests/test_overnight.py` are byte-identical to the design's fences.
- The full fast suite after Phase 7 gave 429 passed, 0 failed.

## Plan Review (Step 4)

_Independent post-finalization review by artifact-code-reviewer and artifact-coverage-reviewer subagents. Findings triaged at Step 5 by the planner. The developer asked for the run to finish without waiting on their input (2026-10-13), so the planner made each call. Every applied change was checked in the scratch copy._

| source | plan-loc | codebase-loc | severity | dimension | finding | recommendation | resolution |
| --- | --- | --- | --- | --- | --- | --- | --- |
| coverage | Testing Strategy, Manual Testing Steps §4 | <n/a> | blocker | verification-coverage | Trap 19 ("the land term adds cost, never replaces the objective with zero") has no Success Criteria bullet and no test asserting a non-zero objective. | Add an rg check on draw.py's cost lines to Phase 4. | dismissed: Phase 4's `test_the_land_term_holds_the_in_state_ratio` asserts the drawing's `border_km` equals the brute-force least border among drawings within R (`_brute`). That would fail if the objective were dropped to zero, so the existing test covers trap 19. In the scratch copy, draw.py only appends the land cost (`cost.append(LAND_WEIGHT / ...)`, :903). The proposed rg would also match the existing rescaling lines `cost = [...]` (:846, :850). |
| coverage | Testing Strategy, Manual Testing Steps §5 | <n/a> | blocker | verification-coverage | "export_long writes no shares, reps or firms" is covered only for reps (`rep` is ""); nothing checks that shares and firms are absent. | Add an rg check on export_long.py to Phase 1. | applied: Phase 1 Automated Verification gained `rg -c 'share\|firm' tools/exp/contig/export_long.py` prints 1, the docstring line only (verified in scratch). |
| coverage | Testing Strategy, Manual Testing Steps §13 | <n/a> | blocker | verification-coverage | "run.json `source` and manifest `instance_sha256` identify the extract" is in no criterion. | Add it to Phase 4's smoke-draw manual check. | applied: Phase 4 Manual Verification gained a bullet: the smoke draw's run.json `source` is the dollar extract and manifest.json `provenance.instance_sha256` equals its sha256 (fields at run.py:453, :518). |
| code | Phase 1 §2 (export_long.py) | <n/a> | concern | code-quality | `main` refuses any run whose extract is missing, while the docstring says only a dollar run is refused. | Make the docstring say every run needs its extract. | applied (plan-local; design follow-up: .rpiv/artifacts/designs/2026-10-13_01-09-34_main-map-overnight-grid.md): docstring only, now "a run whose extract is gone is refused (without it $M cannot be told from `m_rel`), so a dollar run is never exported in $M". The refusal is intended. Only added (`>`) lines change, so Phase 1's branch-diff count is unaffected. |
| code | Phase 2 §1 (score.py) | tools/looks/score.py:343 | concern | code-quality | `write_dollars` writes $M to 3 decimals ($1k) while the gate compares whole dollars, so `read_dollars` can misjudge districts within $1k of an edge. | Write 6 decimals. | dismissed: `ok` and `allowance` are computed in whole dollars before writing, and `label_of` reads those flags, never `usd_m`. `usd_m` only sets `rerun_k`'s direction for a district already failing. The 3-decimal format is pinned by the design's `test_write_dollars` ("1500.000"). |
| code | Phase 3 §1 (audit.py) | td/audit.py:474 | concern | code-quality | `NeckGraph(gap_width=True)` reads `zcta_polygon_vs_voronoi.csv.gz` on every construction, uncached. | Cache it with lru_cache. | dismissed: the hunk is `d312834` verbatim (D6). It is read a few times per scored folder, in seconds-scale post stages against hour-scale draws and repairs. |
| code | Phase 4 §1 (draw.py) | tools/exp/contig/draw.py:71 | concern | code-quality | Each excess costs `LAND_WEIGHT/((h−1)·units)`. With h(h−1) ordered pairs a unit could reach h·LAND_WEIGHT, more than one split. | Divide by h(h−1)·units. | dismissed: the bound is too loose. Each `e_{j,k} ≤ L_j/A` and is positive only when `L_j > R·L_k`, so at most one of each pair is positive (R ≥ 1). Then Σ_k e_{j,k} ≤ (h−1)·L_j/A and Σ_{j,k} e ≤ (h−1)·Σ_j L_j/A ≤ h−1. A unit therefore costs ≤ LAND_WEIGHT/units and a group ≤ LAND_WEIGHT, as the docstring states. |
| code | Phase 5 §1 (overnight.py) | <n/a> | concern | code-quality | A score, land, repair or retry stage killed at its `CAP_S` cap is not labelled **stopped**: only replan and the first draw raise `Stop` on "cap". | Raise `Stop("stopped")` after every capped stage. | deferred (design follow-up: label policy): a capped repair falls back to its source folder, which matches the pass-1/pass-2 policy. A capped score or land stage leaves no m1.json, and the point gets **error** with a FileNotFoundError reason, never a false **eligible**. Changing which stages stop a point is a design decision on the settled stop/retry policy. |
| code | Phase 6 §1 (overnight.py) | requirements.txt:1 | concern | codebase-fit | `ImageFont.load_default(size=40)` needs Pillow ≥ 10.1, and Pillow is not pinned directly. | Call it without `size`. | dismissed: the hub venv has Pillow 12.3.0 (via matplotlib 3.11.1), and `test_morning_files_from_a_toy_grid` passed on it in scratch. Phase 7 runs the suite on both Studios, which catches a different Pillow on m2. |
| code | Phase 6 §1 (overnight.py) | <n/a> | concern | code-quality | `folder_metrics` does not catch a corrupt `m1.json` or `dollars.csv`, so `morning` crashes. | Wrap each read in try/except returning None. | deferred: the files are written by stages that finished. A crash in `morning` is visible and re-runnable (`morning --no-render`), whereas a silent None would hide a bad folder from the table. Revisit if a stage is ever killed mid-write. |
| coverage | Testing Strategy, Manual Testing Steps §10 | <n/a> | concern | verification-coverage | "Scenario-id convention unchanged" has no criterion; the branch-diff count would pass a one-line change. | Add a check on the scenario line. | applied: Phase 1 Automated Verification gained a diff of the `    scenario = ` line between `m5-studio/ifa-conus` and the landed file, which exits 0 (verified in scratch). |
| code | Phase 1 §1 (dollarize.py) | <n/a> | suggestion | code-quality | `os.path.samefile` raises FileNotFoundError when the source is missing. | Check the source exists first. | dismissed: a missing source fails with a clear FileNotFoundError naming it either way. |
| code | Phase 3 §2 (test_neck_gapwidth.py) | tests/test_looks_score.py:4 | suggestion | codebase-fit | Imports sit mid-file after the first test. | Move them to the top. | dismissed: the first block is `d312834`'s test verbatim (D6), and the G3 block is appended with `# noqa: E402` to keep it so. |
| code | Phase 5 §1 (overnight.py) | <n/a> | suggestion | codebase-fit | `overnight.LAND_RATIO` duplicates `land.RATIO`. | Import it. | dismissed: the launcher passes its R explicitly to both `run.py --land-ratio` and `land.py --ratio`, so one constant governs the run. |
| code | Phase 5 §1 (overnight.py) | <n/a> | suggestion | codebase-fit | `ASSUMPTIONS` hardcodes "R = 10". | Build it from `LAND_RATIO`. | dismissed: R is fixed for this run (D15). The assumption text is the record of the owner decision taken, not a derived value. |
| code | Phase 5 §1 (overnight.py) | <n/a> | suggestion | code-quality | On resume, `child` truncates the stage log while `set_aside` keeps only the folder. | Move the log aside too. | deferred: only a resumed point is affected, and the set-aside folder keeps its own manifest and partial output. |
| code | Phase 6 §1 (overnight.py) | <n/a> | suggestion | codebase-fit | `_chain` repeats the `STAGES` tuple as a literal. | Use `STAGES`. | dismissed: `STAGES` is Slice 6's constant (the split keeps Phase 5 self-contained), and both tuples are identical in the design's fence. |
| code | Phase 6 §1 (overnight.py) | <n/a> | suggestion | codebase-fit | `rerun_id` orders channels by `sorted`, `k_text` by `CHANNELS`. | Use `CHANNELS` order. | dismissed: re-run ids only need to be unique and stable, and `sorted` is both. |
| code | Phase 6 §1 (overnight.py) | <n/a> | suggestion | code-quality | `check_remote` returning [] would make `find` list the whole remote tree. | Raise on empty ids. | dismissed: `check_remote` first requires the remote grid to be `--from`'s host, and every m2 grid lists the six west8 points (`grid_doc`), so ids cannot be empty. |
| code | Phase 6 §2 (test_overnight.py) | <n/a> | suggestion | code-quality | The morning test writes a 4-column land.csv, so its `eye_items` land branch is unexercised. | Write the full 12 columns. | dismissed: `test_needs_your_eye_skips_el_paso` exercises that branch with full land rows. The morning test checks the table's land column. |
| coverage | Testing Strategy, Manual Testing Steps §15 | <n/a> | suggestion | verification-coverage | The night's order (dollarize → tests → smoke → launch) is stated in no criterion. | Add an ordered Phase 7 manual bullet. | dismissed: the order is in Testing Strategy and Desired End State, and Phase 7's manual bullets already run in that order (push, dollarize, tests, plan check, smoke compare, w1-50, m2 quiet, masking). |

## References

- Design: `.rpiv/artifacts/designs/2026-10-13_01-09-34_main-map-overnight-grid.md`
- Research: `.rpiv/artifacts/research/2026-10-12_23-32-43_main-map-joint-wifi-grid.md`
- FRD: `.rpiv/artifacts/discover/2026-10-12_23-21-17_main-map-joint-wifi-grid.md`
- Orientation: `.rpiv/artifacts/orientation/2026-10-13-ifa-to-national.md`, `.rpiv/artifacts/orientation/2026-10-13-overnight-decisions.md`
- Issues: #111, #112, #119 (open, untouched), #130 (scorer), #131 (gap width), #133 (land balance)
- Commits: `d312834` (G1 prototype), `21d9cb4`/`ef5d761` (export_long), `0d0f685` (set125.sh), `71517c8`/`ef03fc1` (draw terms)
