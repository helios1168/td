"""merge.py -- several run folders (`run.py --states <S>`, `repair.py --states <S>`, or merged
region folders written by this tool) merged into one run folder and audited as one map, so a
source's out-of-state ZCTAs stop counting as cells with no row and the merged M1 verdict is the
real one.

    "$TD_PY" tools/exp/contig/merge.py <spec.toml> --out <dir> --extract-out <path.json.gz>
        [--base-extract <instance_descaled.json.gz>] [--window LO,HI] [--export]
        <source> [<source> ...]

A source is `STATES=<run folder>`, STATES one state or several joined by "," or "+" (`CT,RI=...`,
`AR+LA+OK=...`), or a bare `<run folder>`, whose states are its ledger's `state` column.  The
channel's k is the number of merged districts and every state split between two merged districts
is `free`, whatever the spec says (`run.json` "spec_overrides"): no master is solved, so k and the
modes only set τ and the instance's units.  `--window LO,HI` (m_rel) writes each district's
window check (in, under or over), the band verdict (owner, 2026-10-08, E2); the audit's final-band
check on τ[1 ± final_delta] stays as the spec sets it and is information only.  `--export` writes
the stakeholder dataset to `<out>/export/`.

The merge invariant: every district keeps its exact ZCTA set; every (ZCTA, fine channel) cell has
exactly one owner; the merge never adds, removes or re-routes a cell; the sources' ZCTA sets are
disjoint (`merge_ledgers` refuses an overlap).  District ids are renumbered per channel in
(source state, source id) order, so NJ's IFA_01 and PA's IFA_01 cannot collide, and
`districts.csv` keeps each district's `source_run` and `source_district`.  Names are recomputed
from the merged ledger (`output.name_districts`), since two states' names can coincide.

The merged extract is the sources' extracts concatenated (states are disjoint).  The instance is
`td.spec.build` of the merged spec on the polygon graph induced on the sources' states (`run.
induced_graph`); the ledger is re-gated with `output.audit_run` and `audit.audit` on the full
`geo.polygon_graph()`, as `run.write_folder` gates a run, whatever the sources' verdicts.  No
regional master is solved, so the solver checks are unverified; the drawings carry no planned or
drawn shares, so the share checks see none.
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import dataclasses
import re

from td import audit, data, geo, output, realize  # noqa: E402
from td import spec as tdspec  # noqa: E402

DOLLARS_PER_M_REL = 1.2519681558        # $M per unit of m_rel (IFA, 2026-10-01 maps)
BAND_M = (1000.0, 1437.5)               # the IFA $ band of the stakeholder maps, $M


def _run():
    if "contig_run" not in sys.modules:
        spec = importlib.util.spec_from_file_location("contig_run", os.path.join(HERE, "run.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_run"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_run"]


class MergeError(ValueError):
    pass


def merge_ledgers(sources: list, scenario: str) -> tuple:
    """(merged rows, {(tag, channel, source id): merged id}) of `sources`, [(tag, ledger rows)].
    Raises MergeError when two sources share a ZCTA or a source owns a cell twice."""
    seen: dict = {}
    for tag, rows in sources:
        for z in {r["zip_code"] for r in rows}:
            if z in seen:
                raise MergeError(f"ZCTA {z} is in both {seen[z]} and {tag}")
            seen[z] = tag
        cells = collections.Counter((r["zip_code"], r["current_channel"]) for r in rows)
        twice = sorted(k for k, n in cells.items() if n > 1)
        if twice:
            raise MergeError(f"{tag}: {len(twice)} cells with two rows, first {twice[0]}")
    order = {tag: i for i, (tag, _) in enumerate(sources)}     # (source order, source id)
    olds = sorted({(c, order[tag], tag, r["district"]) for tag, rows in sources for r in rows
                   for c in [r["model_channel"]] if r["district"]})
    ids, count = {}, collections.Counter()
    for c, _, tag, j in olds:
        count[c] += 1
        ids[tag, c, j] = f"{c}_{count[c]:02d}"
    out = []
    for tag, rows in sources:
        for r in rows:
            m = dict(r, scenario=scenario, district_name="")
            if r["district"]:
                m["district"] = ids[tag, r["model_channel"], r["district"]]
            out.append(m)
    out.sort(key=lambda r: (r["zip_code"], r["current_channel"]))
    before = sorted((r["zip_code"], r["current_channel"], r["model_channel"], r["m_rel"],
                     (tag, r["district"]) if r["district"] else None)
                    for tag, rows in sources for r in rows)
    back = {v: (tag, j) for (tag, c, j), v in ids.items()}
    after = sorted((r["zip_code"], r["current_channel"], r["model_channel"], r["m_rel"],
                    back[r["district"]] if r["district"] else None) for r in out)
    if before != after:
        raise MergeError("the merge changed a cell")
    return out, ids


def parse_source(arg: str) -> tuple:
    """(tag, states, folder) of a source argument: `STATES=<folder>`, STATES joined by "," or
    "+", or a bare `<folder>`, whose states are its ledger's `state` column (tag "A,B,...")."""
    if "=" in arg:
        tag, folder = arg.split("=", 1)
        states = tuple(x for x in re.split(r"[,+]", tag) if x)
    else:
        folder = arg
        led = output.read_ledger(os.path.join(folder, "ledger.csv"))
        states = tuple(sorted({r["state"] for r in led if r["state"]}))
        tag = ",".join(states)
    if not states or any(not re.fullmatch(r"[A-Z]{2}", x) for x in states):
        raise MergeError(f"source {arg!r}: no list of two-letter states")
    return tag, states, folder


def source_run(folder: str) -> str:
    """A source's name in districts.csv: its folder's name, `<region>/merged` for a region."""
    f = os.path.normpath(folder)
    name = os.path.basename(f)
    return f"{os.path.basename(os.path.dirname(f))}/{name}" if name == "merged" else name


def window_status(m: float, window: tuple) -> str:
    return "under" if m < window[0] else "over" if m > window[1] else "in"


def merge_extracts(extracts: list) -> data.Extract:
    """The extracts' rows concatenated; their ZIP sets must be disjoint."""
    seen = set()
    for e in extracts:
        zs = set(e.z)
        if zs & seen:
            raise MergeError(f"extracts share {len(zs & seen)} ZIPs")
        seen |= zs
    first = extracts[0]
    if any(e.channels != first.channels for e in extracts):
        raise MergeError("extracts declare different channels")
    firm = {}
    for e in extracts:
        firm.update(e.firm)
    cat = lambda f: [x for e in extracts for x in getattr(e, f)]
    return data.Extract(first.channels, cat("z"), cat("channel"), cat("m_rel"), cat("share"),
                        cat("share_free"), firm, dict(first.meta), {})


def write_extract(sources: list, path: str, base: str | None = None) -> str:
    """The sources' extracts (their manifests' `extract`) merged and written to `path`; with
    `base`, `base`'s rows in the sources' states (`Extract.subset`) instead."""
    if base is None:
        ext = merge_extracts([data.load(json.load(open(os.path.join(f, "manifest.json"),
                                                       encoding="utf-8"))["extract"])
                              for _, _, f in sources])
    else:
        ref = geo.read_reference()
        state = dict(zip(ref["zcta"], ref["state"]))
        keep = {st for _, sts, _ in sources for st in sts}
        full = data.load(base)
        ext = full.subset({z for z in set(full.z) if state.get(z) in keep})
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data.write(ext, path)
    return path


def merge_spec(s, led: list) -> tuple:
    """(`s` with each channel's k the merged district count and its states split between two
    merged districts free; the overrides)."""
    chans, over = dict(s.channels), {}
    for c, cs in s.channels.items():
        rows = [r for r in led if r["model_channel"] == c]
        js = {r["district"] for r in rows if r["district"]}
        if not js:
            continue
        held = collections.defaultdict(set)
        for r in rows:
            if r["district"]:
                held[r["state"]].add(r["district"])
        modes = dict(cs.modes)
        free = sorted(u for u, d in held.items() if len(d) > 1 and u in modes)
        modes.update(dict.fromkeys(free, "free"))
        new = dataclasses.replace(cs, k=len(js), modes=modes)
        chans[c], over[c] = new, {"k": len(js), "free": free}
    return dataclasses.replace(s, channels=chans), over


def merge(spec_path: str, out: str, extract_out: str, sources: list,
          window: tuple | None = None) -> dict:
    """Write the merged run folder `out` from `sources`, [(tag, states, run folder)] and their
    merged extract `extract_out` (`write_extract`); run.json's dict."""
    run = _run()
    output.check_out(out, ("manifest.json",))
    folders = {tag: f for tag, _, f in sources}
    if len(folders) != len(sources):
        raise MergeError("two sources have the same tag")
    tags = tuple(folders)
    states = tuple(st for _, sts, _ in sources for st in sts)
    if len(set(states)) != len(states):
        raise MergeError(f"a state is in two sources: {sorted(x for x in set(states) if states.count(x) > 1)}")
    src_rows = [(tag, output.read_ledger(os.path.join(f, "ledger.csv"))) for tag, _, f in sources]
    src_manifest = {tag: json.load(open(os.path.join(f, "manifest.json"), encoding="utf-8"))
                    for tag, _, f in sources}
    s0 = tdspec.load(spec_path)
    led, ids = merge_ledgers(src_rows, s0.name)
    s, overrides = merge_spec(s0, led)

    ref = geo.read_reference()
    ext = tdspec.scope(s, data.conus(data.load(extract_out), ref))
    polygon = geo.polygon_graph()       # M1's audit on the full graph (#52)
    inst = tdspec.build(s, ext, ref, graph=run.induced_graph(polygon, states))
    placed = set(inst.units.unit_of)
    held = {r["zip_code"] for r in led if r["district"]}
    if placed != held:
        raise MergeError(f"the instance places {len(placed - held)} ZCTAs no source owns and "
                         f"leaves {len(held - placed)} owned ZCTAs unplaced")

    back = {v: (tag, c, j) for (tag, c, j), v in ids.items()}
    order = {tag: i for i, tag in enumerate(tags)}
    copy = {v: f"{order[tag]:02d} {tag}/{j}" for v, (tag, c, j) in back.items()}  # sorts as the merged ids do
    owner, mass = collections.defaultdict(dict), collections.defaultdict(dict)
    for r in led:
        if r["district"]:
            c, j = r["model_channel"], copy[r["district"]]
            owner[c][r["zip_code"]] = j
            mass[c][j] = mass[c].get(j, 0.0) + r["m_rel"]
    drawings = {c: realize.Drawing(c, owner[c], mass[c], {}, {}, []) for c in sorted(owner)}
    if output.district_ids(drawings) != {(c, copy[v]): v for v, (_, c, _) in back.items()}:
        raise MergeError("the drawings' district ids are not the merged ids")

    areas = output.read_areas()
    names = output.name_districts(led, output.cbsa_titles(areas))
    for r in led:
        r["district_name"] = names.get(r["district"], "")
    lpath = output.write_ledger(os.path.join(out, "ledger.csv"), led)
    led = output.read_ledger(lpath)
    with open(os.path.join(geo.REFERENCE_DIR, "MANIFEST.json"), encoding="utf-8") as fh:
        ref_manifest = json.load(fh)
    split = output.ledger_pieces(led, polygon, drawings)
    arun = output.audit_run(inst, led, drawings, ext, None, polygon, names, ref_manifest, ref,
                            split, polygon)
    checks = audit.audit(arun)
    audit.write_scorecard(out, checks, f"{s.name} (merged from {'; '.join(tags)})")
    m1 = next(ch for ch in checks if ch.name == audit.M1_CHECK)
    necks = collections.Counter(re.match(r"(\S+/\S+): neck", x).group(1)
                                for x in m1.items if re.match(r"\S+/\S+: neck", x))
    flagged = {re.match(r"(\S+/\S+): ", x).group(1) for x in m1.items
               if re.match(r"\S+/\S+: ", x) and audit.MASS_NECK not in x}

    src_district = {}
    for tag, _, f in sources:
        with open(os.path.join(f, "districts.csv"), encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                src_district[tag, r["channel"], r["district"]] = r
    cols = ("channel", "district", "district_name", "copy", "support", "planned_mass",
            "drawn_mass", "pieces", "source_run", "source_district") + (("window",) if window else ())
    per = {}
    with open(os.path.join(out, "districts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for v in sorted(back):
            tag, c, j = back[v]
            sd = src_district[tag, c, j]
            m = mass[c][copy[v]]
            per[v] = {"m_rel": m, "usd_m": round(m * DOLLARS_PER_M_REL, 1),
                      "pieces": len(split.get((c, v), ())), "necks": necks[f"{c}/{v}"],
                      "m1": "fail" if f"{c}/{v}" in flagged else "pass"}
            if window:
                per[v]["window"] = window_status(m, window)
            w.writerow((c, v, names.get(v, ""), sd["copy"], sd["support"], sd["planned_mass"],
                        m, per[v]["pieces"], source_run(folders[tag]), j)
                       + ((per[v]["window"],) if window else ()))

    src_run = {tag: json.load(open(os.path.join(f, "run.json"), encoding="utf-8"))
               for tag, _, f in sources}
    report = {
        "scenario": s.name, "spec": os.path.relpath(spec_path, ROOT), "source": os.path.basename(extract_out),
        "verdict": audit.verdict(checks), "realizer": "tools/exp/contig/merge.py",
        "fine_channels": list(s.fine_channels), "cells": len(led),
        "zips": len({r["zip_code"] for r in led}),
        "dropped_units": {c: list(u) for c, u in inst.report.get("dropped_units", {}).items()},
        "dropped_channels": list(inst.dropped_channels),
        "channels": {c: {"k": inst.channels[c].k,
                         "delta": inst.channels[c].spec.delta,
                         "final_delta": inst.channels[c].spec.final_delta,
                         "margin": inst.channels[c].spec.margin,
                         "tier": "none (merged; no regional master)",
                         "status": "merged: " + ", ".join(
                             f"{tag} {src_run[tag]['channels'][c]['status']}" for tag in tags
                             if c in src_run[tag]["channels"]),
                         "vanished": 0, **output.piece_counts(split, c)}
                     for c in drawings},
        "m1": {"status": m1.status, "summary": m1.summary,
               "coverage": "footprint coverage (D3)"},
        "merged_from": {tag: {"run": os.path.relpath(folders[tag], ROOT),
                              "m1": src_run[tag]["m1"]["status"],
                              "commit": src_manifest[tag]["provenance"]["commit"]}
                        for tag in tags},
        "spec_overrides": overrides,
        "neck_gap_width": os.environ.get("TD_NECK_GAP_WIDTH") == "1",
        "districts": per,
        "maps": "not drawn (tools/maps/render.py <dir> draws them)"}
    if window:
        bad = sorted(v for v, d in per.items() if d["window"] != "in")
        report["window"] = {"m_rel": list(window),
                            "usd_m": [round(x * DOLLARS_PER_M_REL, 1) for x in window],
                            "verdict": "fail" if bad else "pass", "outside": bad,
                            "in": len(per) - len(bad), "districts": len(per)}
    fb = next(ch for ch in checks if ch.name == "final bands on drawn mass")
    report["tau_band"] = {"status": fb.status, "summary": fb.summary,
                          "final_delta": {c: inst.channels[c].spec.final_delta for c in drawings},
                          "role": "information only (owner, 2026-10-08)" if window else "check"}
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return report


EXPORT_README = """# IFA CONUS territory export

Run folder: `{run}` ({scenario}), written by `tools/exp/contig/merge.py` at commit `{commit}`.

- `ifa_zip_districts.csv`: one row per ZCTA: zip_code, state, county, cbsa, district,
  district_name, m_rel, usd.
- `ifa_districts.csv`: one row per district: district, district_name, states, n_zips, m_rel,
  usd, window, pieces, necks, m1 (the full-graph M1 audit, per district).

Rate: usd = m_rel x {rate} $M per m_rel, rounded to 0.1 ($M).

Band rule (owner, 2026-10-08, E2): each district passes when its m_rel lies in the window
[{lo:.2f}, {hi:.2f}] m_rel = [${lo_usd:,.1f}M, ${hi_usd:,.1f}M]; {window}.  The audit's
τ ± final_delta line ({tau}) is information only and is not tuned to agree with the window.

Decisions:
- F1: MD is kept whole, under a band waiver.
- G1 (#131): a neck's width may count the coverage gaps beside it; the gate default measures
  the shared border only. {g1}
- G2: as recorded in the owner's decision record (not restated here).

Sources (merged in this order):
{sources}

CONUS verdict: M1 {m1} ({m1_summary}); band (window) {window_verdict}; audit {verdict}
(its τ line information only).
"""


def export(out: str, report: dict, window: tuple | None) -> str:
    """`<out>/export/`: the ZIP and district tables and README.md of the merged run."""
    d = os.path.join(out, "export")
    os.makedirs(d, exist_ok=True)
    led = output.read_ledger(os.path.join(out, "ledger.csv"))
    usd = lambda m: round(m * DOLLARS_PER_M_REL, 1)
    with open(os.path.join(d, "ifa_zip_districts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(("zip_code", "state", "county", "cbsa", "district", "district_name", "m_rel", "usd"))
        for r in sorted(led, key=lambda r: (r["zip_code"], r["current_channel"])):
            w.writerow((r["zip_code"], r["state"], r["county"], r["cbsa"], r["district"],
                        r["district_name"], r["m_rel"], usd(r["m_rel"])))
    zips, sts, name = collections.defaultdict(set), collections.defaultdict(set), {}
    for r in led:
        if r["district"]:
            zips[r["district"]].add(r["zip_code"])
            sts[r["district"]].add(r["state"])
            name[r["district"]] = r["district_name"]
    per = report["districts"]
    with open(os.path.join(d, "ifa_districts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(("district", "district_name", "states", "n_zips", "m_rel", "usd", "window",
                    "pieces", "necks", "m1"))
        for v in sorted(per):
            p = per[v]
            w.writerow((v, name.get(v, ""), "+".join(sorted(sts[v])), len(zips[v]), p["m_rel"],
                        usd(p["m_rel"]), p.get("window", ""), p["pieces"], p["necks"], p["m1"]))
    win = report.get("window")
    lo, hi = window if window else (float("nan"), float("nan"))
    man = json.load(open(os.path.join(out, "manifest.json"), encoding="utf-8"))
    text = EXPORT_README.format(
        run=os.path.relpath(out, ROOT), scenario=report["scenario"],
        commit=man["provenance"]["commit"], rate=DOLLARS_PER_M_REL, lo=lo, hi=hi,
        lo_usd=lo * DOLLARS_PER_M_REL, hi_usd=hi * DOLLARS_PER_M_REL,
        window=(f"{sum(p.get('window') == 'in' for p in per.values())} of {len(per)} districts in "
                f"it" if win else "not checked (no --window)"),
        g1=("This run was audited with TD_NECK_GAP_WIDTH=1 (gap width counted)."
            if report["neck_gap_width"] else "This run was audited with the gate default."),
        sources="\n".join(f"- `{tag}`: `{m['run']}` at commit `{m['commit']}`, source M1 {m['m1']}"
                          for tag, m in report["merged_from"].items()),
        tau=f"final_delta {report['tau_band']['final_delta']}: {report['tau_band']['status']}, "
            f"{report['tau_band']['summary']}",
        m1=report["m1"]["status"], m1_summary=report["m1"]["summary"], verdict=report["verdict"],
        window_verdict=win["verdict"] if win else "not checked")
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return d


def summary(out: str) -> list:
    """Per district: (id, source, drawn m_rel, $M, inside BAND_M)."""
    with open(os.path.join(out, "districts.csv"), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    res = []
    for r in rows:
        usd = float(r["drawn_mass"]) * DOLLARS_PER_M_REL
        res.append((r["district"], f"{r['source_run']}:{r['source_district']}",
                    float(r["drawn_mass"]), usd, BAND_M[0] <= usd <= BAND_M[1], int(r["pieces"])))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec")
    ap.add_argument("sources", nargs="+",
                    help="STATES=<run folder> (STATES joined by ',' or '+') or <run folder>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract-out", required=True,
                    help="where the merged extract is written (confidential, never committed)")
    ap.add_argument("--base-extract",
                    help="build the merged extract from this extract's rows in the sources' "
                         "states, not from the sources' own extracts")
    ap.add_argument("--window", help="LO,HI in m_rel: the per-district window check")
    ap.add_argument("--export", action="store_true", help="write <out>/export/")
    a = ap.parse_args(argv)
    sources = [parse_source(x) for x in a.sources]
    window = tuple(float(x) for x in a.window.split(",")) if a.window else None
    if window is not None and (len(window) != 2 or not 0 < window[0] <= window[1]):
        raise SystemExit(f"--window {a.window}: need LO,HI with 0 < LO <= HI")
    run = _run()
    params = {"sources": {tag: f for tag, _, f in sources}, "extract_out": a.extract_out,
              "base_extract": a.base_extract, "window": list(window) if window else None,
              "export": a.export}
    output.check_out(a.out)
    os.makedirs(a.out, exist_ok=True)
    src = [{"state": tag, "states": list(sts), "run": os.path.abspath(f),
            "commit": json.load(open(os.path.join(f, "manifest.json"),
                                     encoding="utf-8"))["provenance"]["commit"]}
           for tag, sts, f in sources]
    write_extract(sources, a.extract_out, a.base_extract)
    run.write_manifest(a.out, "contig_merge", a.spec, a.extract_out, params, source_runs=src)
    try:
        report = merge(a.spec, a.out, a.extract_out, sources, window)
        if a.export:
            export(a.out, report, window)
    except Exception as e:
        run.write_manifest(a.out, "contig_merge", a.spec, a.extract_out, params, status="failed",
                           stop_reason=f"{type(e).__name__}: {e}")
        raise
    run.write_manifest(a.out, "contig_merge", a.spec, a.extract_out, params, status="done",
                       stop_reason="merged", audit=report["verdict"], m1=report["m1"]["status"])
    win = report.get("window")
    print(f"{report['scenario']}: M1 {report['m1']['status']} ({report['m1']['summary']}); "
          f"audit {report['verdict']}"
          + (f"; window: {win['in']} of {win['districts']} in [{window[0]:g}, {window[1]:g}] m_rel"
             f" (band {win['verdict']}); τ band (information only): {report['tau_band']['status']}"
             f", {report['tau_band']['summary']}" if win else ""))
    for j, s_, m, usd, ok, pcs in summary(a.out):
        w_ = f"  window {report['districts'][j]['window']}" if win else ""
        print(f"  {j} {s_:28s} m_rel {m:9.3f}  ${usd:8.1f}M  {'in' if ok else 'OUT of'} band"
              f" [{BAND_M[0]:g}, {BAND_M[1]:g}]  pieces {pcs}{w_}")
    return 0 if report["m1"]["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
