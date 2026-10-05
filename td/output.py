"""output.py -- a run from spec to ledger, names, maps and exports (#71; `docs/MODEL.md` §8).

`python -m td run <spec>` (`run`): the extract (or the seeded fixture) less its non-CONUS ZIPs and
scoped to the scenario's fine channels (`spec.scope`, #79), the instance on the declared ZIP
graph, each channel's master (`td.master`) and map (`td.realize`), then the ledger, its audit
(`td.audit`), the district names and the maps, all in one run directory.  A spec the loader
refuses, a channel with no plan and a realizer stop each end the run with the reason (S28); a
channel whose declared band is proven infeasible first has its smallest master δ searched and
written to `solver.json`, and never adopted (OD1, S10).  A failed audit still writes everything
and exits 1.  A run writes only into a new or empty directory, so no
output of an earlier run can outlive a stop.

**The ledger** (`ledger.csv`, S25, S26) has one row per (ZIP, fine channel) cell of the scoped
CONUS extract; the cells of fine channels the scenario leaves to other scenarios have no row, and
`run.json` counts them per channel under `planned_elsewhere`.  It keeps the tagged
`scenarios.csv` columns (`LEGACY_COLUMNS`, in order) and adds the ZIP's 2025 county, CBSA and
place GEOIDs and the district's name, then the cell's opportunity `m_rel`, from which reported
masses and bands are read (§8), and the `reason` for a blank district:
- `dropped: zero opportunity`, a cell of a unit or channel dropped before solving (§1, #65 F1);
- `NOT_PLACED`, a ZIP that is not a vertex of the declared graph: it has no unit, so it is outside
  the audit's retained domain and counted in `run.json` (#67).  A ZIP with no opportunity in any
  channel is never a vertex of the graph the run declares (OD2, `declared_graph`).
`current_channel` is the fine channel, `model_channel` the planning channel holding the cell,
`district` the district id `<channel>_<nn>`, `district_channels` its channel (blank with the
district), and `rep` is blank: outputs are district-only plans (OD3, #58).  The audit reads the
ledger back from the file, so it checks what was written.

**Names.**  A district is its channel and the 2025 CBSA title holding most of its opportunity in
the ledger; a district with none takes `rural <state>` for its heaviest state.  Districts of a
channel that share a name add their next CBSA, and any still alike an ordinal by drawn mass.

**Pieces** (`ledger_pieces`) are the components of the ZIPs each district holds in the ledger, on
the declared graph and in the audit's order, so the scorecard, `run.json` and `districts.csv`
count the same pieces.  A piece inside a realizer piece keeps its cause; one inside the
realizer's main component was joined only through ZIPs the ledger has no cell for in the channel
(`CONNECTOR`).

**Maps** (`maps/<channel>.png`) read only the ledger file: each ZCTA the ledger gives a district is
its TIGER/Line 2025 ZCTA520 polygon (#52 §5.2), simplified by `SIMPLIFY_M` for the figure and
filled in its district's color, over TIGER/Line 2025 state outlines when the file is at hand, with
labels at the principal cities of the channel's `TOP_METROS` largest metros by 2025 population.
The principal cities are the ones the 2025 CBSA title names, placed at their 2025 gazetteer place.
Only the run's ZCTAs are read from the national file.  Without the file no map is drawn and
`run.json` says `MAPS_SKIPPED`; a ledger ZCTA the file lacks is listed there, never dropped silently.

**Paths.**  A planning channel names its map file, and the scenario names the default run
directory, so each must be a plain file name (`FILE_NAME`, not `.` or `..`, and channels distinct
without regard to case): the run and the maps command refuse any other before writing, and every
map path must resolve inside the run directory.  District ids (`<channel>_<nn>`) name no file.
"""
from __future__ import annotations

import collections
import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field

from td import audit, data, geo, master, realize
from td import spec as tdspec

LEGACY_COLUMNS = ("scenario", "zip_code", "current_channel", "state", "model_channel", "district",
                  "district_channels", "rep")          # the tag's scenarios.csv header
COLUMNS = LEGACY_COLUMNS + ("county", "cbsa", "place", "district_name", "m_rel", "reason")
DROPPED = audit.DROPPED
NOT_PLACED = "not placed: not a vertex of the declared ZIP graph"
CONNECTOR = "connector ZIP not in ledger"
TOP_METROS = 10
ZCTA_FILE = os.path.basename(geo.SOURCES["zcta"][0])   # tl_2025_us_zcta520.zip
SIMPLIFY_M = 250.0          # the figures' simplification, as the 2026-09-09 menu chose
MAPS_SKIPPED = "maps skipped: ZCTA polygons missing"
FILE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,250}")    # a key that may name a file: one component


class RunError(RuntimeError):
    """The run cannot go on: it stops with the reason."""


@dataclass
class Result:
    out: str
    verdict: str
    checks: list
    paths: dict
    report: dict = field(default_factory=dict)


# ------------------------------------------------------------------------------ the run
def positive_zips(extract) -> set:
    """The extract's ZIPs with opportunity in some fine channel.  A ZIP with none in every channel
    is for display only and is no optimization vertex (OD2); a ZIP at zero in one channel but not
    in all keeps its vertex."""
    return {z for z, m in extract.masses().items() if m > 0}


def declared_graph(extract, reference, public: str = geo.PUBLIC_DIR) -> dict:
    """The OD2 graph a real extract is drawn on, over its `positive_zips` only: the committed
    all-CONUS graph when each of its vertices has opportunity in the extract, else `geo.zip_graph`
    rebuilt over the positive placed points, since inducing the committed graph on fewer points
    would invent disconnections (trap 21).  A wholly-zero ZIP keeps its ledger rows, as
    `NOT_PLACED`."""
    import pandas as pd
    ref = reference.set_index("zcta")
    positive = positive_zips(extract)
    vertices = set(ref.index[ref["graph_vertex"].astype(int) == 1])
    if vertices <= positive:
        e = pd.read_csv(os.path.join(geo.REFERENCE_DIR, "zcta_graph_edges.csv.gz"), dtype=str)
        return {"vertices": sorted(vertices), "edges": list(zip(e["a"], e["b"]))}
    placed = [z for z in sorted(positive) if z in ref.index and ref.at[z, "state"]]
    if not placed:
        raise RunError("no ZIP of the extract has opportunity and a 2025 point: there is no graph")
    rows = ref.loc[placed]
    points = dict(zip(placed, zip(rows["x"].astype(float), rows["y"].astype(float))))
    return geo.zip_graph(points, dict(zip(placed, rows["state"])), data.state_polygons(public))


def run(s, extract, out: str, graph: dict | None = None, reference=None,
        public: str = geo.PUBLIC_DIR, time_limit: float | None = None, maps: bool = True,
        source: str = "") -> Result:
    """Spec `s` on `extract` into the run directory `out`, new or empty (module docstring)."""
    check_file_names("planning channel", s.channels)
    check_out(out)
    for c in s.channels:
        if tdspec.hook(s, c) is not None:
            raise RunError(f"channel {c} names a hook, and the run has no place to call one yet")
    ref = geo.read_reference() if reference is None else reference
    conus = data.conus(extract, ref)
    ext = tdspec.scope(s, conus)        # the scenario's fine channels only, before the graph (#79)
    graph = declared_graph(ext, ref, public) if graph is None else graph
    inst = tdspec.build(s, ext, ref, graph)
    os.makedirs(out, exist_ok=True)
    plans, reports = master.plan_all(inst, time_limit=time_limit)
    none = sorted(c for c, p in plans.items() if p is None)
    # a declared band proven infeasible: report the smallest master δ, never adopt it (OD1, S10)
    deltas = {c: master.smallest_delta(inst, c, time_limit=time_limit)
              for c in none if reports[c]["status"] == "infeasible"}
    paths = {"solver": write_solver(os.path.join(out, "solver.json"), reports, deltas)}
    if none:
        raise RunError("no plan for " + "; ".join(
            no_plan(c, inst.channels[c].spec.delta, reports[c], deltas.get(c)) for c in none)
            + "; the declared bands are kept (OD1): a run at another δ must declare it")
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    xy = dict(zip(rows.index, zip(rows["x"].astype(float), rows["y"].astype(float))))
    drawings = {c: realize.realize(inst, p, xy) for c, p in plans.items()}

    areas = read_areas()
    led = ledger(inst, drawings, ext, ref)
    names = name_districts(led, cbsa_titles(areas))
    for r in led:
        r["district_name"] = names.get(r["district"], "")
    paths["ledger"] = write_ledger(os.path.join(out, "ledger.csv"), led)
    led = read_ledger(paths["ledger"])
    with open(os.path.join(geo.REFERENCE_DIR, "MANIFEST.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    split = ledger_pieces(led, graph, drawings)
    checks = audit.audit(audit_run(inst, led, drawings, ext, reports, graph, names, manifest, ref,
                                   split))
    paths["scorecard"] = audit.write_scorecard(out, checks, f"{s.name} ({source or 'extract'})")
    paths["districts"] = write_districts(os.path.join(out, "districts.csv"), inst, plans,
                                         drawings, names, split)
    report = {
        "scenario": s.name, "spec": s.path, "source": source, "verdict": audit.verdict(checks),
        "cells": len(led), "zips": len({r["zip_code"] for r in led}),
        "not_placed_zips": len({r["zip_code"] for r in led if r["reason"] == NOT_PLACED}),
        "zero_opportunity_zips": len(set(ext.zips) - positive_zips(ext)),
        "conus_dropped": ext.dropped,
        "planned_elsewhere": {f: sum(1 for c in conus.channel if c == f)
                              for f in s.planned_elsewhere},
        "dropped_units": {c: list(u) for c, u in inst.report.get("dropped_units", {}).items()},
        "dropped_channels": list(inst.dropped_channels),
        "national_moved_units": sorted(inst.report.get("national_moved", {})),
        "disconnected_units": sorted(inst.report.get("disconnected", {})),
        "channels": {c: {"k": inst.channels[c].k, "delta": plans[c].delta,
                         "margin": inst.channels[c].spec.margin,
                         "tier": audit.tier(reports[c]), "status": reports[c]["status"],
                         "moved": len(d.moved), "vanished": len(d.vanished),
                         **piece_counts(split, c)}
                     for c, d in drawings.items()}}
    if not maps:
        report["maps"] = "not drawn (--no-maps)"
    elif zcta_file(public) is None:
        report["maps"] = MAPS_SKIPPED
    else:
        drawn = draw_maps(paths["ledger"], os.path.join(out, "maps"), ref, areas, public, root=out)
        paths["maps"] = {c: m["path"] for c, m in drawn.items()}
        report["maps"] = "drawn"
        report["maps_missing_polygons"] = sorted({z for m in drawn.values() for z in m["missing"]})
    paths["run"] = os.path.join(out, "run.json")
    with open(paths["run"], "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return Result(out, report["verdict"], checks, paths, report)


def delta_reading(found) -> dict:
    """What the smallest-δ search `found` (`master.Delta`) proves, by method (MODEL §5 Claim 2, C4).

    A bisection's `lower` is a δ a step proved infeasible; an exact solve's `lower` is the
    solver's bound when it stopped without a verdict, never a tested δ, and equals `delta` when
    it is optimal.  `proved` is true only for a definite answer: an exact optimum, or no δ at
    all.  Unknown stays unknown."""
    exact = found.method == "exact"
    return {
        "proved": found.status in ("exact", "infeasible"),
        "feasible_at": found.delta,
        "infeasible_at": None if exact else found.lower,
        "solver_bound": found.lower if exact and found.status == "unknown" else None}


def write_solver(path: str, reports: dict, deltas: dict) -> str:
    """`solver.json` as `master.write_report` writes it, each smallest δ with its reading."""
    master.write_report(path, reports, deltas)
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    for c, found in deltas.items():
        doc[c]["smallest_delta"]["reading"] = delta_reading(found)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def no_plan(channel: str, delta: float, report: dict, found) -> str:
    """Why `channel` has no plan at its declared δ, with the smallest master δ `found` when the
    band was proven infeasible, worded from `delta_reading` so a bound never reads as a verdict."""
    head = f"{channel} at δ = {delta} ({report['status']})"
    if found is None:
        return f"{head}, no verdict, so no smallest δ was searched"
    if found.status == "infeasible":
        return f"{head}, and no δ is feasible ({found.method})"
    r = delta_reading(found)
    tag = f"({found.method}, {found.status})"
    if found.status == "exact":
        return f"{head}; smallest master δ {found.delta:.6g} {tag}"
    known = [f"feasible at {r['feasible_at']:.6g}"] if r["feasible_at"] is not None else []
    if r["infeasible_at"] is not None:
        known.append(f"infeasible at {r['infeasible_at']:.6g}")
    if r["solver_bound"] is not None:
        known.append(f"solver bound {r['solver_bound']:.6g}")
    facts = ": " + ", ".join(known) if known else ", nothing proven"
    if found.status == "converged":
        where = f"{found.delta:.6g}" if r["infeasible_at"] is None else \
            f"in ({r['infeasible_at']:.6g}, {found.delta:.6g}]"
        return f"{head}; smallest master δ {where} {tag}{facts}"
    return f"{head}; smallest master δ unknown {tag}{facts}"


def check_out(out: str) -> None:
    """Stop unless the run directory `out` is new or empty, so no earlier output survives a stop."""
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        raise RunError(f"{out} exists and is not an empty directory; pass a fresh --out or remove it")


def check_file_names(kind: str, names) -> None:
    """Stop unless each of `names` is a plain file name (`FILE_NAME`, not `.` or `..`) and no two
    differ only in case, so a file named after one stays in its directory and overwrites no other."""
    bad = [n for n in names if not isinstance(n, str) or not FILE_NAME.fullmatch(n) or n in (".", "..")]
    if bad:
        raise RunError(f"{kind} {', '.join(map(repr, bad))} cannot name an output file: use "
                       "1 to 250 of A-Z a-z 0-9 _ . -, not . or ..")
    folded = collections.Counter(n.casefold() for n in names)
    alike = sorted(n for n in names if folded[n.casefold()] > 1)
    if alike:
        raise RunError(f"{kind} names {', '.join(map(repr, alike))} differ only in case and would "
                       "name the same file")


def inside(root: str, path: str) -> str:
    """`path`, after checking that it resolves, symlinks followed, inside the directory `root`."""
    r, p = os.path.realpath(root), os.path.realpath(path)
    if os.path.commonpath([r, p]) != r:
        raise RunError(f"{path} resolves to {p}, outside {root}")
    return path


# ------------------------------------------------------------------------------ the ledger
def district_ids(drawings: dict) -> dict:
    """{(channel, copy name): `<channel>_<nn>`}, numbered in copy-name order."""
    return {(c, j): f"{c}_{i:02d}" for c, d in drawings.items()
            for i, j in enumerate(sorted(d.mass), 1)}


def ledger(inst, drawings: dict, extract, reference) -> list:
    """The ledger rows, dicts over COLUMNS, one per (ZIP, fine channel) cell of `extract` (a ZIP's
    duplicate cells summed), sorted by ZIP and fine channel; `district_name` is left blank."""
    s, units = inst.spec, inst.units
    cells: dict = collections.defaultdict(float)
    for z, f, m in zip(extract.z, extract.channel, extract.m_rel):
        cells[z, f] += m
    zips = sorted({z for z, _ in cells})
    ref = reference.set_index("zcta")
    unknown = sum(1 for z in zips if z not in ref.index)
    if unknown:
        raise RunError(f"{unknown} ZIPs of the extract are not in the 2025 reference table; "
                       "apply the CONUS rule (td.data.conus) first")
    rows = ref.loc[zips]
    state, county, cbsa, place = (dict(zip(zips, rows[k])) for k in ("state", "county", "cbsa", "place"))
    unit_of = dict(units.unit_of)
    off = [z for z in zips if z not in unit_of]
    unit_of.update(tdspec.carve(s, {z: state[z] for z in off}, {z: county[z] for z in off},
                                {z: cbsa[z] for z in off}))
    chan = {(u, f): c.name for c in s.channels.values() for u, fs in c.domain.items() for f in fs}
    ids = district_ids(drawings)
    out, ownerless = [], collections.Counter()
    for z, f in sorted(cells):
        v = unit_of[z]
        c = chan[v, f]
        district, reason = "", ""
        if z not in units.unit_of:
            reason = NOT_PLACED
        elif c not in inst.channels or v not in inst.channels[c].M:
            reason = DROPPED
        elif z not in drawings[c].owner:
            ownerless[c] += 1
        else:
            district = ids[c, drawings[c].owner[z]]
        out.append({"scenario": s.name, "zip_code": z, "current_channel": f, "state": state[z],
                    "model_channel": c, "district": district,
                    "district_channels": c if district else "", "rep": "", "county": county[z],
                    "cbsa": cbsa[z], "place": place[z], "district_name": "", "m_rel": cells[z, f],
                    "reason": reason})
    if ownerless:
        raise RunError("cells of a solved unit with no owner in the map: "
                       + ", ".join(f"{c} {n}" for c, n in sorted(ownerless.items())))
    return out


def write_ledger(path: str, rows: list) -> str:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path


def read_ledger(path: str) -> list:
    """The ledger's rows as written, `m_rel` as a float."""
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["m_rel"] = float(r["m_rel"])
    return rows


def audit_run(inst, rows: list, drawings: dict, extract, reports: dict, graph: dict, names: dict,
              manifest: dict | None = None, reference=None, split: dict | None = None) -> audit.Run:
    """`td.audit.Run` over the ledger `rows`: the cells of placed ZIPs, the expected cells from
    `extract` (the input, not the ledger), the maps' planned and drawn shares as diagnostics, and
    the causes of the ledger's pieces (`split`, `ledger_pieces` of `rows` when None)."""
    ids = district_ids(drawings)
    placed = inst.units.unit_of
    cells = [audit.Cell(r["zip_code"], r["current_channel"], r["model_channel"], r["district"],
                        float(r["m_rel"]), r["rep"], r["reason"])
             for r in rows if r["reason"] != NOT_PLACED]
    expected = {(z, f) for z, f in zip(extract.z, extract.channel) if z in placed}
    chans = {c: audit.Channel(ch.k, *ch.final_band) for c, ch in inst.channels.items()}
    mode = {(c, v): ch.mode[v] for c, ch in inst.channels.items() for v in ch.units}
    planned, reported = {}, {}
    for c, d in drawings.items():
        M = inst.channels[c].M
        planned.update({(c, v, ids[c, j]): a / M[v] for (v, j), a in d.planned.items()})
        reported.update({(c, v, ids[c, j]): x / M[v] for (v, j), x in d.drawn.items()})
    split = ledger_pieces(rows, graph, drawings) if split is None else split
    causes = {(j, z): pc.cause for (_, j), pcs in split.items() for pc in pcs for z in pc.zips}
    return audit.Run(cells, chans, expected, dict(placed), mode, planned, reported, graph, causes,
                     metro_exceptions(inst, reference), manifest, reports, names)


def ledger_pieces(rows: list, graph: dict, drawings: dict) -> dict:
    """{(channel, district id): [realize.Piece]}, every district's pieces in the ledger `rows`: the
    components of the ZIPs it holds there on the declared graph's explicit vertices (trap 21),
    ordered as `td.audit.check_contiguity` orders them, less the first.  A piece inside a piece
    of the realizer's map takes its cause; one inside the map's main component takes `CONNECTOR`."""
    import networkx as nx
    g = nx.Graph()
    vertices = set(graph["vertices"])
    g.add_nodes_from(vertices)
    g.add_edges_from((a, b) for a, b, *_ in graph["edges"] if a in vertices and b in vertices)
    held: dict = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["district"]:
            held[r["model_channel"], r["district"]][r["zip_code"]] += float(r["m_rel"])
    ids = district_ids(drawings)
    cause_of = {(c, ids[c, pc.district], z): pc.cause
                for c, d in drawings.items() for pc in d.pieces for z in pc.zips}
    out = {}
    for (c, j), zips in sorted(held.items()):
        comps = sorted(nx.connected_components(g.subgraph(z for z in zips if z in g)),
                       key=lambda s: (-sum(zips[z] for z in s), min(s)))
        out[c, j] = [realize.Piece(j, tuple(sorted(comp)), math.fsum(zips[z] for z in comp),
                                   cause_of.get((c, j, min(comp)), CONNECTOR))
                     for comp in comps[1:]]
    return out


def piece_counts(split: dict, channel: str) -> dict:
    """U34 for one channel from `ledger_pieces`, in the shape of `realize.Drawing.counts`."""
    pcs = [pc for (c, _), ps in split.items() if c == channel for pc in ps]
    causes = sorted({pc.cause for pc in pcs})
    return {"pieces": len(pcs), "districts": len({pc.district for pc in pcs}),
            "pieces_by_cause": dict(collections.Counter(pc.cause for pc in pcs)),
            "districts_by_cause": {k: len({pc.district for pc in pcs if pc.cause == k})
                                   for k in causes}}


def metro_exceptions(inst, reference=None) -> list:
    """S14: every metro unit whose ZIPs cross a state line."""
    if not inst.spec.metros:
        return []
    ref = (geo.read_reference() if reference is None else reference).set_index("zcta")
    out = []
    for m in inst.spec.metros:
        zs = inst.units.zips.get(m.name, ())
        states = sorted(set(ref.loc[list(zs), "state"])) if zs else []
        if len(states) > 1:
            out.append(f"{m.name} (CBSA {m.cbsa}) crosses {'/'.join(states)}")
    return out


def write_districts(path: str, inst, plans: dict, drawings: dict, names: dict, split: dict) -> str:
    """One row per district: its id, name, copy, support, planned and drawn mass, and its pieces
    in the ledger (`ledger_pieces`)."""
    ids = district_ids(drawings)
    cols = ("channel", "district", "district_name", "copy", "support", "planned_mass",
            "drawn_mass", "pieces")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for c, d in drawings.items():
            for cp in sorted(plans[c].copies, key=lambda cp: ids[c, cp.name]):
                j = ids[c, cp.name]
                w.writerow((c, j, names.get(j, ""), cp.name, "+".join(sorted(cp.support)), cp.total,
                            d.mass[cp.name], len(split.get((c, j), ()))))
    return path


# ------------------------------------------------------------------------------ names
def read_areas():
    import pandas as pd
    return pd.read_csv(os.path.join(geo.REFERENCE_DIR, "areas.csv.gz"), dtype=str,
                       keep_default_na=False)


def cbsa_titles(areas) -> dict:
    """{CBSA code: its 2025 title less " Metro Area" or " Micro Area"}."""
    rows = areas[areas["layer"] == "cbsa"]
    return {g: n.removesuffix(" Metro Area").removesuffix(" Micro Area")
            for g, n in zip(rows["geoid"], rows["name"])}


def name_districts(rows: list, titles: dict) -> dict:
    """{district: name} from the ledger rows (module docstring); the names are unique."""
    by_cbsa: dict = collections.defaultdict(collections.Counter)
    by_state: dict = collections.defaultdict(collections.Counter)
    mass, chan = collections.Counter(), {}
    for r in rows:
        j = r["district"]
        if not j:
            continue
        chan[j] = r["model_channel"]
        mass[j] += r["m_rel"]
        by_state[j][r["state"]] += r["m_rel"]
        if r["cbsa"]:
            by_cbsa[j][r["cbsa"]] += r["m_rel"]

    def ranked(counter):
        return [k for k, m in sorted(counter.items(), key=lambda km: (-km[1], km[0])) if m > 0]

    first, second = {}, {}
    for j in chan:
        cs = ranked(by_cbsa[j])
        if cs:
            first[j] = titles.get(cs[0], f"CBSA {cs[0]}")
            second[j] = titles.get(cs[1], f"CBSA {cs[1]}") if len(cs) > 1 else ""
        else:
            st = ranked(by_state[j]) or sorted(by_state[j])
            first[j], second[j] = f"rural {st[0]}", ""
    names = {j: f"{chan[j]} {first[j]}" for j in chan}

    def alike():
        groups = collections.defaultdict(list)
        for j, n in names.items():
            groups[n].append(j)
        return [sorted(js, key=lambda j: (-mass[j], j)) for js in groups.values() if len(js) > 1]

    for js in alike():
        for j in js:
            if second[j]:
                names[j] = f"{names[j]} / {second[j]}"
    for js in alike():
        for i, j in enumerate(js, 1):
            names[j] = f"{names[j]} ({i})"
    if len(set(names.values())) != len(names):
        raise RunError("district names are not unique after disambiguation")
    return names


# ------------------------------------------------------------------------------ maps
def cbsa_population(reference) -> dict:
    """{CBSA code: its 2025 population}, the ZCTAs' co-est2025 shares summed."""
    pop = collections.Counter()
    for c, p in zip(reference["cbsa"], reference["pop2025"]):
        if c and p:
            pop[c] += float(p)
    return dict(pop)


def principal_cities(title: str, places: dict) -> list:
    """[(city, x, y)] for the principal cities a 2025 CBSA title names ("A-B-C, ST-ST Metro Area"),
    each at its 2025 gazetteer place: in one of the title's states, named the city plus a legal
    suffix ("city", "CDP", "metro government (balance)"), the most populous such place.
    `places` is {state: [(name, pop, x, y)]}.  A hyphen joins cities unless the title uses "--",
    as it does when a city's own name holds one; a hyphenated city is matched first."""
    head, _, tail = title.rpartition(", ")
    states = tail.split(" ")[0].split("-")

    def find(city):
        best = None
        for st in states:
            for name, pop, x, y in places.get(st, ()):
                rest = name[len(city):] if name.startswith(city) else None
                if rest is None or (rest and not rest.startswith(" ")):
                    continue
                if not all(w[0].islower() or w[0] == "(" or w == "CDP" for w in rest.split()):
                    continue
                if best is None or pop > best[1]:
                    best = (city, pop, x, y)
        return None if best is None else (best[0], best[2], best[3])

    if "--" in head:
        return [p for p in map(find, head.split("--")) if p]
    parts, out, i = head.split("-"), [], 0
    while i < len(parts):
        for k in range(len(parts), i, -1):
            got = find("-".join(parts[i:k]))
            if got:
                out.append(got)
                i = k
                break
        else:
            i += 1
    return out


def _places(areas, reference) -> dict:
    """{state: [(place name, 2025 population, x, y)]} with points in `geo.CRS`."""
    from pyproj import Transformer
    fips = {}
    for st, co in zip(reference["state"], reference["county"]):
        if st and co:
            fips[co[:2]] = st
    rows = areas[(areas["layer"] == "place") & (areas["lon"] != "") & (areas["lat"] != "")]
    to = Transformer.from_crs("EPSG:4269", geo.CRS, always_xy=True)
    xs, ys = to.transform(rows["lon"].astype(float).to_numpy(), rows["lat"].astype(float).to_numpy())
    out: dict = collections.defaultdict(list)
    for g, n, p, x, y in zip(rows["geoid"], rows["name"], rows["pop2025"], xs, ys):
        if g[:2] in fips:
            out[fips[g[:2]]].append((n, float(p) if p else -1.0, float(x), float(y)))
    return out


def zcta_file(public: str = geo.PUBLIC_DIR) -> str | None:
    """The TIGER/Line 2025 ZCTA520 file under `public`, or None when it is missing or not a zip."""
    path = os.path.join(public, ZCTA_FILE)
    return path if os.path.exists(path) and geo._valid_download(path) else None


def zcta_polygons(zips, public: str = geo.PUBLIC_DIR) -> dict:
    """{ZCTA: polygon} in `geo.CRS`, simplified by `SIMPLIFY_M`, for the `zips` the ZCTA520 file
    holds.  Only those are read: the file is 529 MB, and a `where` filter keeps it out of memory."""
    path = zcta_file(public)
    if path is None:
        raise RunError(f"{MAPS_SKIPPED}: no {ZCTA_FILE} in {public}")
    zs = sorted(z for z in set(zips) if re.fullmatch(r"\d{5}", z))
    if not zs:
        return {}
    df = geo._read(path, ["ZCTA5CE20"], where=f"ZCTA5CE20 IN ({','.join(repr(z) for z in zs)})")
    return {z: poly.simplify(SIMPLIFY_M, preserve_topology=True)
            for z, poly in zip(df["ZCTA5CE20"], df.geometry)}


def _polygon_path(geom):
    """A matplotlib compound path of `geom`'s rings, oriented so the nonzero rule leaves holes."""
    import numpy as np
    from matplotlib.path import Path
    from shapely.geometry.polygon import orient
    rings = [ring for part in getattr(geom, "geoms", [geom]) if not part.is_empty
             for ring in (orient(part, 1.0).exterior, *orient(part, 1.0).interiors)]
    return Path.make_compound_path(*(Path(np.asarray(r.coords)[:, :2], closed=True) for r in rings))


def draw_maps(ledger_path: str, out_dir: str, reference=None, areas=None,
              public: str = geo.PUBLIC_DIR, top: int = TOP_METROS, root: str | None = None) -> dict:
    """{channel: {"path", "districts", "labels", "zctas", "missing"}}: one map per planning channel,
    drawn only from the ledger file at `ledger_path` (module docstring).  `zctas` counts the
    polygons drawn and `missing` lists the ledger's ZCTAs the ZCTA520 file lacks.  Without that
    file it draws nothing and returns {} (`MAPS_SKIPPED`).  It stops before writing when a
    channel cannot name a file, and every map must resolve inside `root` (default `out_dir`)."""
    if zcta_file(public) is None:
        return {}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patheffects as pe
    import matplotlib.pyplot as plt
    import pandas as pd
    import shapely
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Patch, PathPatch
    ref = geo.read_reference() if reference is None else reference
    areas = read_areas() if areas is None else areas
    led = pd.read_csv(ledger_path, dtype=str, keep_default_na=False)
    check_file_names("planning channel", sorted(set(led["model_channel"])))
    root = out_dir if root is None else root
    inside(root, out_dir)
    led = led[led["district"] != ""].drop_duplicates(["model_channel", "zip_code"])
    polys = zcta_polygons(led["zip_code"], public)
    titles, pop, places = cbsa_titles(areas), cbsa_population(ref), _places(areas, ref)
    outlines = []
    path = os.path.join(public, "tl_2025_us_state.zip")
    if os.path.exists(path) and geo._valid_download(path):
        outlines = list(data.state_polygons(public).values())
    colors = [c for m in ("tab20", "tab20b", "tab20c") for c in plt.get_cmap(m).colors]
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for c, g in led.groupby("model_channel", sort=True):
        fig, ax = plt.subplots(figsize=(12, 8))
        for poly in outlines:
            for part in getattr(poly, "geoms", [poly]):
                ax.plot(*part.exterior.xy, color="0.75", linewidth=0.4, zorder=1)
        districts = sorted(g["district"].unique())
        drawn, handles = [], []
        for i, j in enumerate(districts):
            sel = g[g["district"] == j]
            shapes = [polys[z] for z in sel["zip_code"] if z in polys]
            color = colors[i % len(colors)]
            ax.add_collection(PatchCollection([PathPatch(_polygon_path(p)) for p in shapes],
                                              facecolor=color, edgecolor=color, linewidth=0.2,
                                              zorder=2))
            handles.append(Patch(facecolor=color, label=f"{j} {sel['district_name'].iloc[0]}"))
            drawn += shapes
        metros = sorted((code for code in set(g["cbsa"]) - {""}),
                        key=lambda code: (-pop.get(code, 0.0), code))[:top]
        labels = []
        for code in metros:
            for city, px, py in principal_cities(titles.get(code, ""), places):
                ax.plot(px, py, "k.", markersize=3, zorder=3)
                ax.annotate(city, (px, py), xytext=(3, 3), textcoords="offset points", fontsize=7,
                            zorder=4, path_effects=[pe.withStroke(linewidth=2, foreground="white")])
                labels.append(city)
        if drawn:
            x0, y0, x1, y1 = shapely.total_bounds(drawn)
            pad = 0.03 * max(x1 - x0, y1 - y0, 1.0)
            ax.set_xlim(x0 - pad, x1 + pad)
            ax.set_ylim(y0 - pad, y1 + pad)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(f"{g['scenario'].iloc[0]}: {c}, {len(districts)} districts")
        ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=6,
                  frameon=False)
        out[c] = {"path": inside(root, os.path.join(out_dir, f"{c}.png")), "districts": districts,
                  "labels": labels, "zctas": len(drawn),
                  "missing": sorted(set(g["zip_code"]) - set(polys))}
        fig.savefig(out[c]["path"], dpi=120, bbox_inches="tight")
        plt.close(fig)
    return out


# ------------------------------------------------------------------------------ the commands
def main_run(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m td run", description=__doc__.splitlines()[0])
    ap.add_argument("spec", help="a scenario TOML file")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--extract", help="a td_instance_descaled/3 extract")
    src.add_argument("--fixture", type=int, metavar="SEED", help="the seeded sparse fixture")
    ap.add_argument("--out", help="the run directory, new or empty (default runs/<scenario>)")
    ap.add_argument("--public", default=geo.PUBLIC_DIR, help="where the 2025 downloads are cached")
    ap.add_argument("--time-limit", type=float, help="seconds for each channel's master")
    ap.add_argument("--no-maps", action="store_true", help="skip the maps")
    a = ap.parse_args(argv)
    try:
        s = tdspec.load(a.spec)
        check_file_names("planning channel", s.channels)
        if not a.out:
            check_file_names("scenario", [s.name])
        out = a.out or os.path.join(geo.ROOT, "runs", s.name)
        check_out(out)
        ref = geo.read_reference()
        if a.fixture is not None:
            fx = data.fixture(a.fixture, channels=s.fine_channels, reference=ref, public=a.public)
            extract, graph, source = fx.extract, fx.graph, f"fixture seed {a.fixture}"
        else:
            extract, graph, source = data.load(a.extract), None, os.path.basename(a.extract)
        res = run(s, extract, out, graph, ref, a.public, a.time_limit, not a.no_maps, source)
    except (tdspec.SpecError, master.MasterError, realize.RealizeError, RunError) as e:
        print(f"run stopped: {e}", file=sys.stderr)
        return 1
    for c, r in res.report["channels"].items():
        print(f"{c}: K = {r['k']}, δ = {r['delta']}, {r['status']}, tier {r['tier']}, "
              f"{r['pieces']} pieces, {r['moved']} moved")
    if res.report["maps"] == MAPS_SKIPPED:
        print(f"{MAPS_SKIPPED}: no {ZCTA_FILE} in {a.public}")
    elif res.report.get("maps_missing_polygons"):
        print(f"maps: {len(res.report['maps_missing_polygons'])} ledger ZCTAs have no polygon "
              "(run.json lists them)")
    print(f"audit: {res.verdict}; {res.out}")
    return 0 if res.verdict == "pass" else 1


def main_maps(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m td maps", description="redraw a run's maps "
                                 "from its ledger.csv")
    ap.add_argument("run", help="a run directory")
    ap.add_argument("--public", default=geo.PUBLIC_DIR,
                    help=f"where {ZCTA_FILE} and tl_2025_us_state.zip are")
    a = ap.parse_args(argv)
    if zcta_file(a.public) is None:
        print(f"{MAPS_SKIPPED}: no {ZCTA_FILE} in {a.public}", file=sys.stderr)
        return 1
    try:
        drawn = draw_maps(os.path.join(a.run, "ledger.csv"), os.path.join(a.run, "maps"),
                          public=a.public, root=a.run)
    except RunError as e:
        print(f"maps stopped: {e}", file=sys.stderr)
        return 1
    for c, m in drawn.items():
        print(f"{c}: {m['path']}, {len(m['districts'])} districts, {m['zctas']} ZCTAs, "
              f"{len(m['missing'])} without a polygon, {len(m['labels'])} labels")
    return 0


if __name__ == "__main__":
    sys.exit(main_run())
