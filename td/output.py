"""output.py -- a run from spec to ledger, names, maps and exports (#71; `docs/MODEL.md` §8).

`python -m td run <spec>` (`run`): the extract (or the seeded fixture) less its non-CONUS ZIPs, the
instance on the declared ZIP graph, each channel's master (`td.master`) and map (`td.realize`),
then the ledger, its audit (`td.audit`), the district names and the maps, all in one run
directory.  A spec the loader refuses, a channel with no plan and a realizer stop each end the run
with the reason (S28); a failed audit still writes everything and exits 1.

**The ledger** (`ledger.csv`, S25, S26) has one row per (ZIP, fine channel) cell of the CONUS
extract.  It keeps the tagged `scenarios.csv` columns (`LEGACY_COLUMNS`, in order) and adds the
ZIP's 2025 county, CBSA and place GEOIDs and the district's name, then the cell's opportunity
`m_rel`, from which reported masses and bands are read (§8), and the `reason` for a blank district:
- `dropped: zero opportunity`, a cell of a unit or channel dropped before solving (§1, #65 F1);
- `NOT_PLACED`, a ZIP that is not a vertex of the declared graph: it has no unit, so it is outside
  the audit's retained domain and counted in `run.json` (#67).
`current_channel` is the fine channel, `model_channel` the planning channel holding the cell,
`district` the district id `<channel>_<nn>`, `district_channels` its channel (blank with the
district), and `rep` is blank: outputs are district-only plans (OD3, #58).  The audit reads the
ledger back from the file, so it checks what was written.

**Names.**  A district is its channel and the 2025 CBSA title holding most of its opportunity in
the ledger; a district with none takes `rural <state>` for its heaviest state.  Districts of a
channel that share a name add their next CBSA, and any still alike an ordinal by drawn mass.

**Maps** (`maps/<channel>.png`) read only the ledger file: each ZIP's 2025 gazetteer point, colored
by its district, over TIGER/Line 2025 state outlines when the file is at hand, with labels at the
principal cities of the channel's `TOP_METROS` largest metros by 2025 population.  The principal
cities are the ones the 2025 CBSA title names, placed at their 2025 gazetteer place.
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys
from dataclasses import dataclass, field

from td import audit, data, geo, master, realize
from td import spec as tdspec

LEGACY_COLUMNS = ("scenario", "zip_code", "current_channel", "state", "model_channel", "district",
                  "district_channels", "rep")          # the tag's scenarios.csv header
COLUMNS = LEGACY_COLUMNS + ("county", "cbsa", "place", "district_name", "m_rel", "reason")
DROPPED = audit.DROPPED
NOT_PLACED = "not placed: not a vertex of the declared ZIP graph"
TOP_METROS = 10


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
def declared_graph(extract, reference, public: str = geo.PUBLIC_DIR) -> dict:
    """The OD2 graph a real extract is drawn on: the committed all-CONUS graph when the extract
    holds all its vertices, else `geo.zip_graph` over the extract's placed points (trap 21)."""
    import pandas as pd
    ref = reference.set_index("zcta")
    vertices = set(ref.index[ref["graph_vertex"].astype(int) == 1])
    if vertices <= set(extract.zips):
        e = pd.read_csv(os.path.join(geo.REFERENCE_DIR, "zcta_graph_edges.csv.gz"), dtype=str)
        return {"vertices": sorted(vertices), "edges": list(zip(e["a"], e["b"]))}
    placed = [z for z in extract.zips if z in ref.index and ref.at[z, "state"]]
    rows = ref.loc[placed]
    points = dict(zip(placed, zip(rows["x"].astype(float), rows["y"].astype(float))))
    return geo.zip_graph(points, dict(zip(placed, rows["state"])), data.state_polygons(public))


def run(s, extract, out: str, graph: dict | None = None, reference=None,
        public: str = geo.PUBLIC_DIR, time_limit: float | None = None, maps: bool = True,
        source: str = "") -> Result:
    """Spec `s` on `extract` into the run directory `out` (module docstring)."""
    for c in s.channels:
        if tdspec.hook(s, c) is not None:
            raise RunError(f"channel {c} names a hook, and the run has no place to call one yet")
    ref = geo.read_reference() if reference is None else reference
    ext = data.conus(extract, ref)
    graph = declared_graph(ext, ref, public) if graph is None else graph
    inst = tdspec.build(s, ext, ref, graph)
    os.makedirs(out, exist_ok=True)
    plans, reports = master.plan_all(inst, time_limit=time_limit)
    paths = {"solver": master.write_report(os.path.join(out, "solver.json"), reports)}
    none = sorted(c for c, p in plans.items() if p is None)
    if none:
        raise RunError("no plan for " + "; ".join(
            f"{c} at δ = {inst.channels[c].spec.delta} ({reports[c]['status']})" for c in none)
            + "; td.master.smallest_delta finds the smallest δ a channel meets")
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
    checks = audit.audit(audit_run(inst, led, drawings, ext, reports, graph, names, manifest, ref))
    paths["scorecard"] = audit.write_scorecard(out, checks, f"{s.name} ({source or 'extract'})")
    paths["districts"] = write_districts(os.path.join(out, "districts.csv"), inst, plans,
                                         drawings, names)
    report = {
        "scenario": s.name, "spec": s.path, "source": source, "verdict": audit.verdict(checks),
        "cells": len(led), "zips": len({r["zip_code"] for r in led}),
        "not_placed_zips": len({r["zip_code"] for r in led if r["reason"] == NOT_PLACED}),
        "conus_dropped": ext.dropped,
        "dropped_units": {c: list(u) for c, u in inst.report.get("dropped_units", {}).items()},
        "dropped_channels": list(inst.dropped_channels),
        "national_moved_units": sorted(inst.report.get("national_moved", {})),
        "disconnected_units": sorted(inst.report.get("disconnected", {})),
        "channels": {c: {"k": inst.channels[c].k, "delta": plans[c].delta,
                         "tier": audit.tier(reports[c]), "status": reports[c]["status"],
                         "moved": len(d.moved), "vanished": len(d.vanished), **d.counts()}
                     for c, d in drawings.items()}}
    paths["run"] = os.path.join(out, "run.json")
    with open(paths["run"], "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    if maps:
        drawn = draw_maps(paths["ledger"], os.path.join(out, "maps"), ref, areas, public)
        paths["maps"] = {c: m["path"] for c, m in drawn.items()}
    return Result(out, report["verdict"], checks, paths, report)


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
              manifest: dict | None = None, reference=None) -> audit.Run:
    """`td.audit.Run` over the ledger `rows`: the cells of placed ZIPs, the expected cells from
    `extract` (the input, not the ledger), and the maps' planned and drawn shares as diagnostics."""
    ids = district_ids(drawings)
    placed = inst.units.unit_of
    cells = [audit.Cell(r["zip_code"], r["current_channel"], r["model_channel"], r["district"],
                        float(r["m_rel"]), r["rep"], r["reason"])
             for r in rows if r["reason"] != NOT_PLACED]
    expected = {(z, f) for z, f in zip(extract.z, extract.channel) if z in placed}
    chans = {c: audit.Channel(ch.k, *ch.final_band) for c, ch in inst.channels.items()}
    mode = {(c, v): ch.mode[v] for c, ch in inst.channels.items() for v in ch.units}
    planned, reported, causes = {}, {}, {}
    for c, d in drawings.items():
        M = inst.channels[c].M
        planned.update({(c, v, ids[c, j]): a / M[v] for (v, j), a in d.planned.items()})
        reported.update({(c, v, ids[c, j]): x / M[v] for (v, j), x in d.drawn.items()})
        for pc in d.pieces:
            causes.update({(ids[c, pc.district], z): pc.cause for z in pc.zips})
    return audit.Run(cells, chans, expected, dict(placed), mode, planned, reported, graph, causes,
                     metro_exceptions(inst, reference), manifest, reports, names)


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


def write_districts(path: str, inst, plans: dict, drawings: dict, names: dict) -> str:
    """One row per district: its id, name, copy, support, planned and drawn mass, and pieces."""
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
                            d.mass[cp.name], sum(1 for pc in d.pieces if pc.district == cp.name)))
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


def draw_maps(ledger_path: str, out_dir: str, reference=None, areas=None,
              public: str = geo.PUBLIC_DIR, top: int = TOP_METROS) -> dict:
    """{channel: {"path", "districts", "labels"}}: one map per planning channel, drawn only from
    the ledger file at `ledger_path` (module docstring)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patheffects as pe
    import matplotlib.pyplot as plt
    import pandas as pd
    ref = geo.read_reference() if reference is None else reference
    areas = read_areas() if areas is None else areas
    led = pd.read_csv(ledger_path, dtype=str, keep_default_na=False)
    led = led[led["district"] != ""].drop_duplicates(["model_channel", "zip_code"])
    at = ref.set_index("zcta")
    titles, pop, places = cbsa_titles(areas), cbsa_population(ref), _places(areas, ref)
    outlines = []
    path = os.path.join(public, "tl_2025_us_state.zip")
    if os.path.exists(path) and geo._valid_download(path):
        outlines = list(data.state_polygons(public).values())
    colors = [c for m in ("tab20", "tab20b", "tab20c") for c in plt.get_cmap(m).colors]
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for c, g in led.groupby("model_channel", sort=True):
        x = at.loc[g["zip_code"], "x"].astype(float).to_numpy()
        y = at.loc[g["zip_code"], "y"].astype(float).to_numpy()
        fig, ax = plt.subplots(figsize=(12, 8))
        for poly in outlines:
            for part in getattr(poly, "geoms", [poly]):
                ax.plot(*part.exterior.xy, color="0.75", linewidth=0.4, zorder=1)
        districts = sorted(g["district"].unique())
        for i, j in enumerate(districts):
            sel = (g["district"] == j).to_numpy()
            ax.scatter(x[sel], y[sel], s=4, color=colors[i % len(colors)], zorder=2,
                       label=f"{j} {g['district_name'][sel].iloc[0]}")
        metros = sorted((code for code in set(g["cbsa"]) - {""}),
                        key=lambda code: (-pop.get(code, 0.0), code))[:top]
        labels = []
        for code in metros:
            for city, px, py in principal_cities(titles.get(code, ""), places):
                ax.plot(px, py, "k.", markersize=3, zorder=3)
                ax.annotate(city, (px, py), xytext=(3, 3), textcoords="offset points", fontsize=7,
                            zorder=4, path_effects=[pe.withStroke(linewidth=2, foreground="white")])
                labels.append(city)
        pad = 0.03 * max(x.max() - x.min(), y.max() - y.min(), 1.0)
        ax.set_xlim(x.min() - pad, x.max() + pad)
        ax.set_ylim(y.min() - pad, y.max() + pad)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(f"{g['scenario'].iloc[0]}: {c}, {len(districts)} districts")
        ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=6, markerscale=2,
                  frameon=False)
        out[c] = {"path": os.path.join(out_dir, f"{c}.png"), "districts": districts, "labels": labels}
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
    ap.add_argument("--out", help="the run directory (default runs/<scenario>)")
    ap.add_argument("--public", default=geo.PUBLIC_DIR, help="where the 2025 downloads are cached")
    ap.add_argument("--time-limit", type=float, help="seconds for each channel's master")
    ap.add_argument("--no-maps", action="store_true", help="skip the maps")
    a = ap.parse_args(argv)
    try:
        s = tdspec.load(a.spec)
        ref = geo.read_reference()
        if a.fixture is not None:
            fx = data.fixture(a.fixture, channels=s.fine_channels, reference=ref, public=a.public)
            extract, graph, source = fx.extract, fx.graph, f"fixture seed {a.fixture}"
        else:
            extract, graph, source = data.load(a.extract), None, os.path.basename(a.extract)
        out = a.out or os.path.join(geo.ROOT, "runs", s.name)
        res = run(s, extract, out, graph, ref, a.public, a.time_limit, not a.no_maps, source)
    except (tdspec.SpecError, master.MasterError, realize.RealizeError, RunError) as e:
        print(f"run stopped: {e}", file=sys.stderr)
        return 1
    for c, r in res.report["channels"].items():
        print(f"{c}: K = {r['k']}, δ = {r['delta']}, {r['status']}, tier {r['tier']}, "
              f"{r['pieces']} pieces, {r['moved']} moved")
    print(f"audit: {res.verdict}; {res.out}")
    return 0 if res.verdict == "pass" else 1


def main_maps(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m td maps", description="redraw a run's maps "
                                 "from its ledger.csv")
    ap.add_argument("run", help="a run directory")
    ap.add_argument("--public", default=geo.PUBLIC_DIR, help="where tl_2025_us_state.zip is")
    a = ap.parse_args(argv)
    drawn = draw_maps(os.path.join(a.run, "ledger.csv"), os.path.join(a.run, "maps"),
                      public=a.public)
    for c, m in drawn.items():
        print(f"{c}: {m['path']}, {len(m['districts'])} districts, {len(m['labels'])} labels")
    return 0


if __name__ == "__main__":
    sys.exit(main_run())
