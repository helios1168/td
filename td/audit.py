"""audit.py -- the #52 §4 audit (`docs/MODEL.md` §9): check a run's ledger, write `scorecard.md`.

A run hands the audit a `Run`: its ledger, one `Cell` per (ZIP, fine channel), and what it
planned.  Every mass and share the audit reports comes from the ledger (S26); the run's own
reports are only compared with it.  Each check ends in one status:

    pass        the check holds
    fail        a hard failure, so the run fails (S28, C16, OD1, OD3)
    listed      it holds, with items the scorecard lists for a reader
    unverified  the run lacks what the check needs, as the tagged catalog lacks opportunity

Two share defects are kept apart (#70):
- a *phantom share* is a share the run reports that the ledger does not back: a reported drawn
  share of a unit that differs from the ledger's, or a cell owned by a pseudo-district such as
  the legacy `other`.  It fails the run (S26: a share exists only as a set of ZIPs).
- a *vanished share* is a planned share drawn as no ZIPs.  It is listed, not failed (C8).

`python -m td.audit catalog` scores the tagged catalog (`archive/pre-support-2026-09`,
`scenarios.csv`) once, for `docs/RESULTS.md` (S22).  Its contiguity runs on the OD2 graph built
over the catalog's own ZIPs, since the tag does not ship the graph it was drawn on.
"""
from __future__ import annotations

import collections
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, replace
from typing import NamedTuple

from td import geo

MODES = ("whole", "clipped", "free")
PSEUDO = frozenset({"other", "unserved", "unassigned", "none"})   # owners that are not districts
SHARE_TOL = 1e-9
DROPPED = "dropped: zero opportunity"   # a ledger row's reason for a blank district (MODEL §1)
BAND_SLACK = 1e-9        # OD1: numerical slack at each band boundary, times τ_c
# How far a certificate's bound may sit from its objective and still count as equal, in objective
# units: EXACT_ALLOWANCE × max(1, |objective|), mixed absolute/relative as HiGHS, so float noise at
# a proved optimum still earns `exact`. Decided on #70:
# https://github.com/helios1168/td/issues/70#issuecomment-5908116656
EXACT_ALLOWANCE = 1e-9
TAG = "archive/pre-support-2026-09"
TAG_URL = f"https://github.com/helios1168/td/blob/{TAG}"


class Cell(NamedTuple):
    """One ledger row: `m` is the cell's opportunity, None when the ledger carries none."""
    zip: str
    fine: str
    channel: str
    district: str
    m: float | None = None
    rep: str = ""
    reason: str = ""                 # DROPPED for a cell of a unit or channel dropped before solving


@dataclass
class Channel:
    k: int
    lo: float | None = None      # the final tolerance on drawn mass (OD1)
    hi: float | None = None


@dataclass
class Run:
    """What the audit needs from a run.  Anything left None makes its checks `unverified`.

    `planned` and `reported` map (channel, unit, district) to a share of the unit: the master's
    planned share and the drawn share the run's diagnostics report.  `solver` maps a channel to
    {status, objective, bound, gap, mip_rel_gap}; `causes` maps (district, zip) to the realizer's
    cause for the piece holding that ZIP.
    """
    cells: list
    channels: dict
    expected: set | None = None          # every (zip, fine channel) cell of the extract
    unit_of: dict | None = None
    mode: dict | None = None             # (channel, unit) -> whole | clipped | free
    planned: dict | None = None
    reported: dict | None = None
    graph: dict | None = None            # geo.zip_graph's {"vertices", "edges"}
    causes: dict = field(default_factory=dict)
    metro_exceptions: list = field(default_factory=list)
    manifest: dict | None = None
    solver: dict | None = None
    names: dict | None = None            # district -> name


@dataclass
class Check:
    name: str
    status: str
    summary: str
    items: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)


def _real(district: str) -> bool:
    return bool(district) and district.lower() not in PSEUDO


def _masses(run: Run) -> bool:
    return all(c.m is not None for c in run.cells)


def _drawn(run: Run) -> dict:
    """{(channel, unit, district): drawn share}, from the ledger alone."""
    if run.unit_of is None or not _masses(run):
        return {}
    unit_mass, held = collections.Counter(), collections.Counter()
    for c in run.cells:
        v = run.unit_of[c.zip]
        unit_mass[c.channel, v] += c.m
        held[c.channel, v, c.district] += c.m
    return {(ch, v, j): m / unit_mass[ch, v] for (ch, v, j), m in held.items() if unit_mass[ch, v] > 0}


def _unsolved(run: Run) -> set:
    """Channels whose every cell was dropped for zero opportunity: not solved, so K_c and the
    solver report do not apply (MODEL §1, §9)."""
    return {c.channel for c in run.cells} - {c.channel for c in run.cells if c.reason != DROPPED}


def _owners(run: Run) -> dict:
    """{(channel, unit): {district: set of its ZIPs there}}."""
    out: dict = collections.defaultdict(lambda: collections.defaultdict(set))
    for c in run.cells:
        if _real(c.district):
            out[c.channel, run.unit_of[c.zip]][c.district].add(c.zip)
    return out


# ------------------------------------------------------------------------------ the checks
def check_cells(run: Run) -> Check:
    seen = collections.Counter((c.zip, c.fine) for c in run.cells)
    items = [f"cell {z}/{f}: {n} owners" for (z, f), n in sorted(seen.items()) if n > 1]
    items += [f"cell {c.zip}/{c.fine}: no owner" for c in run.cells
              if not c.district and c.reason != DROPPED]
    if run.unit_of is not None:
        items += [f"cell {c.zip}/{c.fine}: ZIP has no unit" for c in run.cells if c.zip not in run.unit_of]
    # the owner comes from the channel realizer's ZIP (§8), so a ZIP's cells in one channel share it
    held = collections.defaultdict(set)
    for c in run.cells:
        if _real(c.district):
            held[c.zip, c.channel].add(c.district)
    items += [f"ZIP {z} in {ch}: {len(js)} owners ({', '.join(sorted(js))})"
              for (z, ch), js in sorted(held.items()) if len(js) > 1]
    if run.expected is not None:
        items += [f"cell {z}/{f}: not in the ledger" for z, f in sorted(run.expected - set(seen))]
        items += [f"cell {z}/{f}: not expected" for z, f in sorted(set(seen) - run.expected)]
    return Check("one owner per cell", "fail" if items else "pass",
                 f"{len(seen)} cells, {len(items)} with other than one owner", items)


def check_count(run: Run) -> Check:
    got = collections.defaultdict(set)
    for c in run.cells:
        if _real(c.district):
            got[c.channel].add(c.district)
    unsolved = _unsolved(run)
    items = [f"{ch}: {len(got[ch])} districts, K = {spec.k}"
             for ch, spec in sorted(run.channels.items()) if ch not in unsolved and len(got[ch]) != spec.k]
    items += [f"{ch}: not a declared channel" for ch in sorted(set(got) - set(run.channels))]
    return Check("district count per channel", "fail" if items else "pass",
                 f"{len(run.channels)} channels, {len(items)} off K", items)


def check_dropped(run: Run) -> Check:
    """Cells dropped for zero opportunity (MODEL §1, §9) are listed and do not fail the run.  A drop
    fails only when it is not one: the cell has an owner, or its unit has opportunity there."""
    name = "dropped for zero opportunity"
    dropped = [c for c in run.cells if c.reason == DROPPED]
    if not dropped:
        return Check(name, "pass", "no cells dropped")
    mass = collections.Counter()
    if run.unit_of is not None and _masses(run):
        for c in run.cells:
            mass[c.channel, run.unit_of[c.zip]] += c.m
    bad = [f"cell {c.zip}/{c.fine}: dropped but owned by {c.district}" for c in dropped if c.district]
    bad += [f"cell {c.zip}/{c.fine}: dropped but {c.channel}/{run.unit_of[c.zip]} has opportunity "
            f"{mass[c.channel, run.unit_of[c.zip]]:.6g}"
            for c in dropped if mass[c.channel, (run.unit_of or {}).get(c.zip)] > 0]
    listed = [f"cell {c.zip}/{c.fine} ({c.channel}): {DROPPED}" for c in dropped]
    return Check(name, "fail" if bad else "listed", f"{len(dropped)} cells dropped, {len(bad)} not valid",
                 bad + listed)


def check_bands(run: Run) -> Check:
    name = "final bands on drawn mass"
    if not _masses(run):
        return Check(name, "unverified", "the ledger carries no opportunity")
    if any(s.lo is None or s.hi is None for s in run.channels.values()):
        return Check(name, "unverified", "no final tolerance declared (OD1)")
    mass, total = collections.Counter(), collections.Counter()
    for c in run.cells:
        total[c.channel] += c.m
        if _real(c.district):
            mass[c.channel, c.district] += c.m
    drawn = _drawn(run)
    items = []
    for (ch, j), m in sorted(mass.items()):
        spec = run.channels.get(ch)
        if spec is None:
            items.append(f"{ch}/{j}: drawn {m:.6g} in an undeclared channel, no band")
            continue
        slack = BAND_SLACK * total[ch] / spec.k     # τ_c from the ledger's own mass
        if spec.lo - slack <= m <= spec.hi + slack:
            continue
        short = sorted(v for (c2, v, j2), p in (run.planned or {}).items()
                       if c2 == ch and j2 == j and drawn.get((ch, v, j), 0.0) < p - SHARE_TOL)
        cause = f"; undrawn share of {', '.join(short)}" if short else ""
        items.append(f"{ch}/{j}: drawn {m:.6g} outside [{spec.lo:.6g}, {spec.hi:.6g}]{cause}")
    return Check(name, "fail" if items else "pass",
                 f"{len(mass)} districts, {len(items)} outside the final tolerance", items)


def check_phantom(run: Run) -> Check:
    items = [f"cell {c.zip}/{c.fine}: owned by pseudo-district {c.district!r}"
             for c in run.cells if c.district and not _real(c.district)]
    compared = 0
    if run.reported is not None and run.unit_of is not None:
        drawn, owners = _drawn(run), _owners(run)
        for (ch, v, j), share in sorted(run.reported.items()):
            compared += 1
            if share > SHARE_TOL and j not in owners.get((ch, v), {}):
                items.append(f"{ch}/{v}/{j}: reports share {share:.6g}, owns no ZIP there")
            elif drawn and abs(share - drawn.get((ch, v, j), 0.0)) > SHARE_TOL:
                items.append(f"{ch}/{v}/{j}: reports share {share:.6g}, "
                             f"ledger draws {drawn.get((ch, v, j), 0.0):.6g}")
    return Check("phantom shares", "fail" if items else "pass",
                 f"{compared} reported shares compared with the ledger, {len(items)} not backed", items)


def check_planned(run: Run) -> Check:
    name = "planned against drawn owners"
    if run.planned is None or run.unit_of is None or run.mode is None:
        return Check(name, "unverified", "the run reports no planned shares")
    owners = _owners(run)
    items = [f"{ch}/{v}/{j}: planned share {p:.6g} drawn as no ZIPs (C8)"
             for (ch, v, j), p in sorted(run.planned.items())
             if p > SHARE_TOL and j not in owners.get((ch, v), {})]
    planned = {(ch, v, j) for (ch, v, j), p in run.planned.items() if p > SHARE_TOL}
    items += [f"{ch}/{v}/{j}: extra owner from repair in a free unit"
              for (ch, v), held in sorted(owners.items()) if run.mode.get((ch, v)) == "free"
              for j in sorted(held) if (ch, v, j) not in planned]
    return Check(name, "listed" if items else "pass", f"{len(items)} listed", items)


def check_modes(run: Run) -> Check:
    name = "mode compliance"
    if run.unit_of is None or run.mode is None:
        return Check(name, "unverified", "the run declares no units or modes")
    owners = _owners(run)
    reach = collections.defaultdict(set)       # (channel, district) -> units it owns ZIPs in
    for (ch, v), held in owners.items():
        for j in held:
            reach[ch, j].add(v)
    items = []
    for (ch, v), held in sorted(owners.items()):
        mode = run.mode.get((ch, v))
        if mode not in MODES:
            items.append(f"{ch}/{v}: mode {mode!r} not in {MODES}")
        elif mode == "whole" and len(held) > 1:
            items.append(f"{ch}/{v}: whole unit with {len(held)} owners ({', '.join(sorted(held))})")
        elif mode == "clipped" and len(held) > 1:
            items += [f"{ch}/{v}/{j}: owner outside the clipped unit, also in "
                      f"{', '.join(sorted(reach[ch, j] - {v}))} (C16)"
                      for j in sorted(held) if reach[ch, j] != {v}]
    listed = [f"metro exception (S14): {m}" for m in run.metro_exceptions]
    status = "fail" if items else "listed" if listed else "pass"
    return Check(name, status, f"{len(items)} violations, {len(listed)} metro exceptions",
                 items + listed)


def check_contiguity(run: Run) -> Check:
    name = "ZIP contiguity"
    if run.graph is None:
        return Check(name, "unverified", "no declared graph")
    import networkx as nx
    g = nx.Graph()
    vertices = set(run.graph["vertices"])     # explicit (trap 21): an edge adds no vertex
    g.add_nodes_from(vertices)
    g.add_edges_from((a, b) for a, b, *_ in run.graph["edges"] if a in vertices and b in vertices)
    weigh = _masses(run)
    held = collections.defaultdict(lambda: collections.Counter())
    for c in run.cells:
        if _real(c.district):
            held[c.channel, c.district][c.zip] += c.m if weigh else 0.0
    items, split, pieces, gaps = [], 0, 0, 0
    for (ch, j), zips in sorted(held.items()):
        size = (lambda s: sum(zips[z] for z in s)) if weigh else len
        total = size(set(zips)) or 1
        outside = sorted(z for z in zips if z not in g)
        gaps += len(outside)
        items += [f"{ch}/{j}: ZIP {z} not in the graph (graph gap)" for z in outside]
        comps = sorted(nx.connected_components(g.subgraph(z for z in zips if z in g)),
                       key=lambda s: (-size(s), min(s)))
        if len(comps) > 1:
            split += 1
            pieces += len(comps) - 1
        for comp in comps[1:]:
            cause = next((run.causes[j, z] for z in sorted(comp) if (j, z) in run.causes), "unreported")
            items.append(f"{ch}/{j}: piece of {len(comp)} ZIPs, {size(comp) / total:.3g} of the "
                         f"district's {'mass' if weigh else 'ZIPs'}, cause {cause}")
    return Check(name, "listed" if items else "pass",
                 f"{split} districts in pieces, {pieces} pieces, {gaps} ZIPs not in the graph", items,
                 {"split": split, "pieces": pieces, "gaps": gaps})


def check_geography(run: Run) -> Check:
    name = "geography manifest is 2025"
    if run.manifest is None:
        return Check(name, "unverified", "no manifest")
    try:
        geo.check_manifest(run.manifest)
    except ValueError as e:
        return Check(name, "fail", "not all 2025 (S17)", [str(e)])
    return Check(name, "pass", f"{len(run.manifest['sources'])} sources, all 2025")


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def allowance(obj: float) -> float:
    """EXACT_ALLOWANCE × max(1, |objective|): the distance, in objective units, at which a bound
    still counts as equal to the objective (#70)."""
    return EXACT_ALLOWANCE * max(1.0, abs(obj))


def actual_gap(obj: float, bound: float) -> float:
    """The relative gap of a minimisation, (objective - bound) / |objective|, as HiGHS reports it."""
    if obj == bound:
        return 0.0
    return (obj - bound) / abs(obj) if obj != 0 else math.inf


def solver_problems(report: dict) -> list:
    """Why a report with an incumbent cannot back a tier: an objective or bound that is not a
    finite number, a bound above the incumbent, or a reported gap the objective and bound do not
    give.  A report with no bound claims no optimality, so it needs no gap."""
    obj, bound, gap = report.get("objective"), report.get("bound"), report.get("gap")
    if not _finite(obj):
        return [f"objective {obj!r} is not a finite number"]
    if bound is None:
        return [] if gap is None else [f"gap {gap!r} reported without a bound"]
    if not _finite(bound):
        return [f"bound {bound!r} is not a finite number"]
    if bound - obj > allowance(obj):
        return [f"bound {bound!r} above the incumbent {obj!r}"]
    if gap is not None and not _gap_agrees(gap, obj, min(bound, obj)):
        return [f"reported gap {gap!r}, objective and bound give {actual_gap(obj, min(bound, obj)):.6g}"]
    return []


def _gap_agrees(gap, obj: float, bound: float) -> bool:
    """A reported gap agrees when it is the actual gap, or when the bound it implies,
    objective − gap × |objective|, lies within the allowance of `bound`.  At a zero objective a
    gap implies no bound, so only the actual gap, or 0 with the bound within the allowance, agrees."""
    if not isinstance(gap, (int, float)) or isinstance(gap, bool):
        return False
    if gap == actual_gap(obj, bound):
        return True
    if not math.isfinite(gap):
        return False
    if obj == 0:
        return gap == 0 and obj - bound <= allowance(obj)
    return abs(obj - bound - gap * abs(obj)) <= allowance(obj)


def tier(report: dict) -> str:
    """OD3 (#58): exact, bounded or feasible only; `none` without an incumbent, and `invalid`
    when the report cannot back a tier (`solver_problems`).  Exact needs a proven optimum at
    `mip_rel_gap=0`, a reported gap of 0, and a bound within `allowance(objective)` =
    EXACT_ALLOWANCE × max(1, |objective|) of the objective."""
    obj, bound = report.get("objective"), report.get("bound")
    if obj is None:
        return "none"
    if solver_problems(report):
        return "invalid"
    if bound is None:
        return "feasible only"
    if (report.get("status") == "optimal" and report.get("mip_rel_gap") == 0
            and report.get("gap") == 0 and obj - min(bound, obj) <= allowance(obj)):
        return "exact"
    return "bounded"


def _shown_gap(report: dict) -> str:
    """The gap a solver row prints: the actual gap of a report that backs a tier, None without a
    bound, and the report's own value when it backs none."""
    obj, bound = report.get("objective"), report.get("bound")
    if tier(report) in ("invalid", "none"):
        return f"{report.get('gap')}"
    if bound is None:
        return "None"
    return f"{actual_gap(obj, min(bound, obj)):.6g}"


def check_solver(run: Run) -> list:
    if run.solver is None:
        return [Check("solver status, bound and gap", "unverified", "no solver report"),
                Check("certificate tier", "unverified", "no solver report")]
    rows = [f"{ch}: status {r.get('status')}, objective {r.get('objective')}, bound {r.get('bound')}, "
            f"gap {_shown_gap(r)}, tier {tier(r)}" for ch, r in sorted(run.solver.items())]
    tiers = {ch: tier(r) for ch, r in run.solver.items()}
    missing = sorted(set(run.channels) - set(run.solver) - _unsolved(run))
    bad = [f"{ch}: no incumbent" for ch, t in sorted(tiers.items()) if t == "none"]
    bad += [f"{ch}: invalid report, {why}" for ch, r in sorted(run.solver.items())
            if tiers[ch] == "invalid" for why in solver_problems(r)]
    bad += [f"{ch}: no solver report" for ch in missing]
    order = ["exact", "bounded", "feasible only", "invalid"]
    worst = max((t for t in tiers.values() if t in order), key=order.index, default="none")
    return [Check("solver status, bound and gap", "fail" if bad else "listed",
                  f"{len(rows)} channels", bad + rows),
            Check("certificate tier", "fail" if bad else "pass", f"weakest tier: {worst}",
                  [f"{ch}: {t}" for ch, t in sorted(tiers.items())])]


def check_names(run: Run) -> Check:
    name = "one name per district"
    if run.names is None:
        return Check(name, "unverified", "no district names")
    districts = sorted({c.district for c in run.cells if _real(c.district)})
    items = [f"{j}: no name" for j in districts if not run.names.get(j)]
    by_name = collections.defaultdict(list)
    for j in districts:
        if run.names.get(j):
            by_name[run.names[j]].append(j)
    items += [f"{n!r} names {', '.join(js)}" for n, js in sorted(by_name.items()) if len(js) > 1]
    return Check(name, "fail" if items else "pass", f"{len(districts)} districts", items)


def check_reps(run: Run) -> Check:
    labels = collections.defaultdict(set)
    for c in run.cells:
        if c.rep:
            labels[c.channel, c.district].add(c.rep)
    if not labels:
        return Check("rep labels", "pass", "blank, as OD3 (#58) decides")
    items = [f"{ch}/{j}: {len(r)} rep labels" for (ch, j), r in sorted(labels.items()) if len(r) > 1]
    return Check("rep labels", "fail" if items else "pass",
                 f"{len(items)} districts with conflicting rep labels", items)


def audit(run: Run) -> list:
    """Every §9 check on `run`, in the scorecard's order.  A ledger cell whose ZIP has no unit fails
    `check_cells`; the other checks run without it, so the scorecard still completes."""
    mapped = run
    if run.unit_of is not None and any(c.zip not in run.unit_of for c in run.cells):
        mapped = replace(run, cells=[c for c in run.cells if c.zip in run.unit_of])
    return [check_cells(run), check_count(mapped), check_dropped(mapped), check_bands(mapped),
            check_phantom(mapped), check_planned(mapped), check_modes(mapped), check_contiguity(mapped),
            check_geography(mapped), *check_solver(mapped), check_names(mapped), check_reps(mapped)]


def verdict(checks: list) -> str:
    return "fail" if any(c.status == "fail" for c in checks) else "pass"


def scorecard(checks: list, title: str) -> str:
    lines = [f"# Scorecard: {title}", "", f"**Verdict: {verdict(checks)}**", "",
             "| check | status | summary |", "|---|---|---|"]
    lines += [f"| {c.name} | {c.status} | {c.summary} |" for c in checks]
    for c in checks:
        if c.items:
            lines += ["", f"## {c.name}", ""] + [f"- {i}" for i in c.items]    # every item (§9)
    return "\n".join(lines) + "\n"


def write_scorecard(run_dir: str, checks: list, title: str) -> str:
    path = os.path.join(run_dir, "scorecard.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(scorecard(checks, title))
    return path


# ------------------------------------------------------------------------------ the tagged catalog
LAYERS = {"n": "N", "wh": "WH", "fi": "FI", "wifi": "WHFI"}


def catalog_k(scenario: str) -> dict:
    """{layer: K} from a catalog scenario name such as `51_total_13n_11wh_24fi_3wifi`."""
    got = {LAYERS[k]: int(n) for n, k in re.findall(r"_(\d+)(n|wh|fi|wifi)(?=_|$)", scenario)}
    if set(got) != set(LAYERS.values()):
        raise ValueError(f"not a catalog scenario name: {scenario!r}")
    return got


def read_catalog(path: str | None = None):
    """The tag's `scenarios.csv`, from `path` or from git."""
    import io
    import pandas as pd
    if path is None:
        raw = subprocess.run(["git", "show", f"{TAG}:scenarios.csv"], cwd=geo.ROOT,
                             capture_output=True, check=True).stdout
        path = io.BytesIO(raw)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def catalog_graph(frame, public: str = geo.PUBLIC_DIR, reference=None) -> dict:
    """The OD2 graph over the catalog's ZIPs; `excluded` lists those without a 2025 point."""
    from td import data
    ref = (geo.read_reference() if reference is None else reference).set_index("zcta")
    zips = sorted(set(frame["zip_code"]))
    placed = [z for z in zips if z in ref.index and ref.at[z, "state"]]
    points = {z: (float(ref.at[z, "x"]), float(ref.at[z, "y"])) for z in placed}
    g = geo.zip_graph(points, {z: ref.at[z, "state"] for z in placed}, data.state_polygons(public))
    g["excluded"] = sorted(set(zips) - set(placed))
    return g


def catalog_runs(frame, graph: dict | None = None):
    """(scenario, Run) for each tagged scenario.  A cell's channel is its district's layer; units
    are states.  The tag has no opportunity, plan, modes, solver report, names or manifest."""
    for scenario, rows in frame.groupby("scenario", sort=True):
        cells = [Cell(z, f, ch, j, None, r) for z, f, ch, j, r in
                 zip(rows["zip_code"], rows["current_channel"], rows["district_channels"],
                     rows["district"], rows["rep"])]
        yield scenario, Run(cells, {ch: Channel(k) for ch, k in catalog_k(scenario).items()},
                            unit_of=dict(zip(rows["zip_code"], rows["state"])), graph=graph)


def catalog_scorecard(frame, graph: dict) -> str:
    """The §9 audit of every tagged scenario, as markdown for `docs/RESULTS.md`."""
    rows, statuses = [], collections.defaultdict(collections.Counter)
    totals = collections.Counter()
    for scenario, run in catalog_runs(frame, graph):
        checks = {c.name: c for c in audit(run)}
        for c in checks.values():
            statuses[c.name][c.status] += 1
        reps = len(checks["rep labels"].items)
        split, pieces = (checks["ZIP contiguity"].counts.get(k, 0) for k in ("split", "pieces"))
        totals.update(reps=reps, split=split, pieces=pieces)
        rows.append(f"| {scenario} | {verdict(checks.values())} | {checks['one owner per cell'].status} "
                    f"| {checks['district count per channel'].status} | {reps} | {split} | {pieces} |")
    zips = frame["zip_code"].nunique()
    lines = [
        f"Scored with `td/audit.py` on the tag's [`scenarios.csv`]({TAG_URL}/scenarios.csv): "
        f"{frame['scenario'].nunique()} scenarios, {zips} ZIPs, {len(frame)} cells.",
        "",
        f"Contiguity is on the 2025 Voronoi rook graph over the catalog's ZIPs (OD2, built by "
        f"`geo.zip_graph`: {len(graph['vertices'])} vertices, {len(graph['edges'])} edges). "
        f"{len(graph['excluded'])} catalog ZIPs have no 2025 gazetteer point and are left out; "
        f"{len(graph['missing'])} lose their cell. The tag does not ship the graph it was drawn "
        "on, so these counts are not comparable with older ones.",
        "",
        "| check | " + " | ".join(("pass", "fail", "listed", "unverified")) + " |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {n} | " + " | ".join(str(s[k]) for k in ("pass", "fail", "listed", "unverified")) + " |"
              for n, s in statuses.items()]
    lines += ["", "| scenario | verdict | one owner per cell | district count | districts with "
              "conflicting rep labels | districts in pieces | pieces |", "|---|---|---|---|---|---|---|"]
    lines += rows
    lines.append(f"| **total** | | | | {totals['reps']} | {totals['split']} | {totals['pieces']} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m td.audit", description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["catalog"])
    ap.add_argument("--csv", help="the tag's scenarios.csv (default: read it from git)")
    ap.add_argument("--public", default=geo.PUBLIC_DIR, help="where tl_2025_us_state.zip is")
    a = ap.parse_args(argv)
    frame = read_catalog(a.csv)
    sys.stdout.write(catalog_scorecard(frame, catalog_graph(frame, a.public)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
