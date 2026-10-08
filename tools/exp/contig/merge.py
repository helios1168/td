"""merge.py -- several single-state run folders (`run.py --states <S>`, `repair.py --states <S>`)
merged into one regional run folder and audited as one map, so a single-state run's out-of-state
ZCTAs stop counting as cells with no row and the regional M1 verdict is the real one.

    "$TD_PY" tools/exp/contig/merge.py <spec.toml> --out <dir> --extract-out <path.json.gz>
        STATE=<run folder> [STATE=<run folder> ...]

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
    olds = sorted({(c, tag, r["district"]) for tag, rows in sources for r in rows
                   for c in [r["model_channel"]] if r["district"]})
    ids, count = {}, collections.Counter()
    for c, tag, j in olds:
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


def write_extract(sources: list, path: str) -> str:
    """The sources' extracts (their manifests' `extract`) merged and written to `path`."""
    ext = [data.load(json.load(open(os.path.join(f, "manifest.json"), encoding="utf-8"))["extract"])
           for _, f in sources]
    data.write(merge_extracts(ext), path)
    return path


def merge(spec_path: str, out: str, extract_out: str, sources: list) -> dict:
    """Write the merged run folder `out` from `sources`, [(state, run folder)] and their merged
    extract `extract_out` (`write_extract`); run.json's dict."""
    run = _run()
    s = tdspec.load(spec_path)
    output.check_out(out, ("manifest.json",))
    folders = dict(sources)
    states = tuple(tag for tag, _ in sources)
    src_rows = [(tag, output.read_ledger(os.path.join(f, "ledger.csv"))) for tag, f in sources]
    src_manifest = {tag: json.load(open(os.path.join(f, "manifest.json"), encoding="utf-8"))
                    for tag, f in sources}
    led, ids = merge_ledgers(src_rows, s.name)

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
    copy = {v: f"{tag}/{j}" for v, (tag, c, j) in back.items()}   # sorts as the merged ids do
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
    audit.write_scorecard(out, checks, f"{s.name} (merged from {', '.join(states)})")

    src_district = {}
    for tag, f in sources:
        with open(os.path.join(f, "districts.csv"), encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                src_district[tag, r["channel"], r["district"]] = r
    cols = ("channel", "district", "district_name", "copy", "support", "planned_mass",
            "drawn_mass", "pieces", "source_run", "source_district")
    with open(os.path.join(out, "districts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for v in sorted(back):
            tag, c, j = back[v]
            sd = src_district[tag, c, j]
            w.writerow((c, v, names.get(v, ""), sd["copy"], sd["support"], sd["planned_mass"],
                        mass[c][copy[v]], len(split.get((c, v), ())),
                        os.path.basename(os.path.normpath(folders[tag])), j))

    m1 = next(ch for ch in checks if ch.name == audit.M1_CHECK)
    src_run = {tag: json.load(open(os.path.join(f, "run.json"), encoding="utf-8"))
               for tag, f in sources}
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
                             f"{tag} {src_run[tag]['channels'][c]['status']}" for tag in states
                             if c in src_run[tag]["channels"]),
                         "vanished": 0, **output.piece_counts(split, c)}
                     for c in drawings},
        "m1": {"status": m1.status, "summary": m1.summary,
               "coverage": "footprint coverage (D3)"},
        "merged_from": {tag: {"run": os.path.relpath(folders[tag], ROOT),
                              "m1": src_run[tag]["m1"]["status"],
                              "commit": src_manifest[tag]["provenance"]["commit"]}
                        for tag in states},
        "maps": "not drawn (tools/maps/render.py <dir> draws them)"}
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return report


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
    ap.add_argument("sources", nargs="+", help="STATE=<run folder>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract-out", required=True,
                    help="where the merged extract is written (confidential, never committed)")
    a = ap.parse_args(argv)
    sources = [tuple(x.split("=", 1)) for x in a.sources]
    run = _run()
    params = {"sources": dict(sources), "extract_out": a.extract_out}
    output.check_out(a.out)
    os.makedirs(a.out, exist_ok=True)
    src = [{"state": tag, "run": os.path.abspath(f),
            "commit": json.load(open(os.path.join(f, "manifest.json"),
                                     encoding="utf-8"))["provenance"]["commit"]}
           for tag, f in sources]
    write_extract(sources, a.extract_out)
    run.write_manifest(a.out, "contig_merge", a.spec, a.extract_out, params, source_runs=src)
    try:
        report = merge(a.spec, a.out, a.extract_out, sources)
    except Exception as e:
        run.write_manifest(a.out, "contig_merge", a.spec, a.extract_out, params, status="failed",
                           stop_reason=f"{type(e).__name__}: {e}")
        raise
    run.write_manifest(a.out, "contig_merge", a.spec, a.extract_out, params, status="done",
                       stop_reason="merged", audit=report["verdict"], m1=report["m1"]["status"])
    print(f"{report['scenario']}: M1 {report['m1']['status']} ({report['m1']['summary']}); "
          f"audit {report['verdict']}")
    for j, s_, m, usd, ok, pcs in summary(a.out):
        print(f"  {j} {s_:28s} m_rel {m:9.3f}  ${usd:8.1f}M  {'in' if ok else 'OUT of'} band"
              f" [{BAND_M[0]:g}, {BAND_M[1]:g}]  pieces {pcs}")
    return 0 if report["m1"]["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
