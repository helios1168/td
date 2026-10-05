"""repair.py -- #109's exact window repair (large-neighbourhood search) of a drawn contig run
folder that fails M1.

    "$TD_PY" -u tools/exp/contig/repair.py <run_dir> --out <dir> [--extract PATH] [--plans PATH]
        [--h0 3] [--max-zctas 1500] [--time-limit 600] [--channels c ...] [--maps]

Per planning channel with a detached piece on the drawn map (the ledger of `<run_dir>`, read
back to each ZCTA's plan copy):

- **The window** W at h hops (`ball`): every ZCTA within h hops of a detached piece on the
  instance's graph (M1's polygon graph with the approved connectors), kept when it is free
  (`draw.split_fixed`: a ZCTA of a split unit, an exclave or a dropped unit), plus the pieces
  themselves (of a piece over half `--max-zctas`, its ZCTAs within h hops of its border).  Past the h
  windows, the `corridor` windows: the free ZCTAs on a path from a piece to the rest of its
  district at most `slack` hops longer than the shortest (the piece stays fixed, a body).  Every ZCTA outside W
  keeps its owner.
- **The model** is `draw._solve_group` on W: x_{z,j} for z in W and every district owning a ZCTA
  in or next to W (a unit may change holders, an arm-2 move the audit lists; with
  `--keep-support`, arm 1, only the districts whose plan holds z's unit), each district's ZCTAs outside W its bodies (each component one vertex, the
  largest the root), every district connected by the separator solve-check-cut loop, each
  district's total drawn mass in the channel's final band (the band the audit judged the run
  at; a district whose mass outside W is already above it makes W infeasible, and a district
  with no ZCTA in or next to W is not in the model, so a window's status says nothing about its
  band: each attempt lists the districts outside the band before and after), split units first in the objective, then holders (cuts), then the border shape term (#121, `draw`'s docstring); with the cap
  (the default) the window units' split units and cuts may not rise above the drawn map's.  The
  geodesic-DAG restriction runs first and seeds the complete model (`draw._attempt`).  Every
  detached component gets a separator row per BFS layer towards its district's main component;
  with `--flow`, each district is also held connected by a single-commodity flow from its root
  body (exact either way; the flow proves infeasibility without enumerating separators).
- **Growth**: h doubles while W at h is proved infeasible, up to `--max-zctas` (the last step
  takes the largest h whose W fits), then the corridor's slack grows; the last window, when
  infeasible with the cap, is tried once more without it, and the rise in splits or cuts is
  reported.

- **Necks** (#121): once no detached piece is left, each neck M1 lists is repaired like a piece
  (`_repair_neck`): the windows of `steps` around the side it cuts off, each re-solved with the
  border term, the first kept that leaves no more detached pieces and fewer necks among its
  districts.

The source run is checked first (`check_source`): its districts.csv must list, per channel, the
plan's copies under the ids, names and supports the ledger was written with, or nothing is
repaired.

Statuses stay apart: "optimal" is a connected optimum of W's complete model at
`mip_rel_gap = 0` (W only, everything outside fixed; never an optimum of the map), "connected"
is connected and feasible, "infeasible" proves only that W at that h, the rest fixed, has no
drawing (never a certificate for the map: no no-good cut), "unknown" is the time limit.

The output is a full run folder (ledger, scorecard, districts.csv, run.json; `run.write_folder`)
and a manifest.json (mandate T1, `run.write_manifest`; its parent is the source run), and a
contig.json that copies the source run's channels and adds each window attempt under
`repair` (a neck's marked `kind: neck`), the map's border between districts before and after
(`cut_border_km_before_repair`, `cut_border_km`) and the necks left: pieces before and after, the shape, |W|, h or slack, status, seconds, worst deviation, split states and cuts
on the drawn map.  A repaired channel's band is the repair's, not the source drawing's: its
`group_delta_needed` moves to `source_group_delta_needed`, and `repair_band` holds the final band's
δ the windows held and the worst |mass/τ − 1| reached.  `tools/mandates/check.py` audits it like any run folder.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import math
import os
import pickle
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo, output  # noqa: E402
from td import spec as tdspec  # noqa: E402


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


draw = _load("contig_draw", "draw.py")
run = _load("contig_run", "run.py")


def check_source(districts_path: str, plans: dict) -> list:
    """The mismatches between a run's districts.csv and `plans`: per channel of the file, the
    (district id, copy name, support) rows must be the plan's copies numbered as
    `output.district_ids` numbers them, so the ledger's ids read back to the copies that drew it."""
    import csv
    have = collections.defaultdict(set)
    with open(districts_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            have[r["channel"]].add((r["district"], r["copy"], r["support"]))
    out = []
    for c in sorted(have):
        if c not in plans:
            out.append(f"{c}: in districts.csv, not in the plans")
            continue
        want = {(f"{c}_{i:02d}", j, "+".join(sorted(s)))
                for i, (j, s) in enumerate(sorted((cp.name, cp.support)
                                                  for cp in plans[c].copies), 1)}
        out += [f"{c}: districts.csv {d} {j} ({s}), not in the plan" for d, j, s in sorted(have[c] - want)]
        out += [f"{c}: plan {d} {j} ({s}), not in districts.csv" for d, j, s in sorted(want - have[c])]
    return out


def owners_from_ledger(rows: list, plans: dict) -> dict:
    """{channel: {zip: copy name}} from the ledger's district ids (`output.district_ids`)."""
    back = {(c, f"{c}_{i:02d}"): j for c, p in plans.items()
            for i, j in enumerate(sorted(cp.name for cp in p.copies), 1)}
    out = collections.defaultdict(dict)
    for r in rows:
        if not r["district"]:
            continue
        c, z = r["model_channel"], r["zip_code"]
        j = back[c, r["district"]]
        if out[c].setdefault(z, j) != j:
            raise RuntimeError(f"{c} {z}: two owners in the ledger")
    return dict(out)


def detached(owner: dict, adj: dict, m: dict) -> list:
    """[(district, frozenset of ZCTAs)] of every detached piece (all but the heaviest component,
    as `td.audit.district_pieces` orders them)."""
    return [(j, frozenset(cc)) for j, comps in audit.district_pieces(owner, adj, m).items()
            for cc in comps[1:]]


def window(seeds: set, free: set, adj: dict, h: int) -> set:
    """The ZCTAs within `h` hops of `seeds` that are free, and the seeds."""
    seen, layer = set(seeds), set(seeds)
    for _ in range(h):
        layer = {y for z in layer for y in adj[z]} - seen
        if not layer:
            break
        seen |= layer
    return (seen & free) | set(seeds)


def holders_on(owner: dict, units, vs) -> dict:
    return {v: {owner[z] for z in units.zips[v] if z in owner} for v in vs}


def map_figures(inst, c: str, owner: dict, state: dict) -> dict:
    """Worst |mass/τ − 1|, split states and cuts (by polygon ownership, as `report.py` counts on
    the ledger) of a channel's drawn map."""
    ch = inst.channels[c]
    mass = collections.Counter()
    by = collections.defaultdict(set)
    for z, j in owner.items():
        mass[j] += ch.m.get(z, 0.0)
        by[state[z]].add(j)
    split = sorted(s for s, js in by.items() if len(js) > 1)
    lo, hi = ch.final_band
    return {"worst_dev": max(abs(x / ch.tau - 1) for x in mass.values()),
            "split_states": len(split), "cuts": sum(len(by[s]) - 1 for s in split),
            "outside_band": sorted(j for j, x in mass.items() if not lo <= x <= hi)}


def solve_window(inst, plan, owner: dict, W: set, p: dict, time_limit: float, cap: bool,
                 log=print, flow: bool = False, keep_support: bool = False,
                 repairing: set = frozenset(), border: dict | None = None):
    """`draw.Group` of the window `W` (module docstring), everything outside fixed.  With
    `keep_support` (arm 1) a ZCTA may go only to a district whose plan holds its unit (an exclave
    or dropped ZCTA to any); else to any district of the window (a unit may change holders: an
    arm-2 move, reported by the audit's planned-against-drawn check)."""
    c = plan.channel
    ch, units = inst.channels[c], inst.units
    adj, m, unit_of = units.zip_adj, ch.m, units.unit_of
    outside = {z: j for z, j in owner.items() if z not in W}
    js = sorted({owner[z] for z in W} | {outside[y] for z in W for y in adj[z] if y in outside})
    allowed = {z: list(js) for z in W}
    if keep_support:
        hold = draw.holders(plan)
        _, _, exclave = draw.split_fixed(inst, plan)
        for z in W:
            if z not in exclave and unit_of[z] not in ch.dropped_units:
                allowed[z] = [j for j in js if j in hold.get(unit_of[z], ())]
    by_j = collections.defaultdict(set)
    for z, j in outside.items():
        if j in js:
            by_j[j].add(z)
    # a district's bodies are its components outside W that touch W, and for a district being
    # repaired its main one; another component (a piece of a district repaired elsewhere) is left
    # as it is, its mass counted in the band row
    near = {y for z in W for y in adj[z]}
    bodies, extra = {}, {}
    for j, zs_j in by_j.items():
        comps = sorted(draw.components(zs_j, adj),
                       key=lambda cc: (-math.fsum(m.get(z, 0.0) for z in cc), -len(cc), min(cc)))
        keep = [cc for i, cc in enumerate(comps) if cc & near or (i == 0 and j in repairing)]
        bodies[j] = keep
        extra[j] = math.fsum(m.get(z, 0.0) for cc in comps if cc not in keep for z in cc)
    body_of = {z: (j, i) for j, bs in bodies.items() for i, b in enumerate(bs) for z in b}
    hold = draw.holders(plan)
    planned = {(v, cp.name): cp.mass[v] for cp in plan.copies for v in cp.support}
    support = {cp.name: cp.support for cp in plan.copies}
    lo, hi = ch.final_band
    count = {"current": holders_on(owner, units, {unit_of[z] for z in W}), "cap": cap}
    zs = sorted(W)
    t_end = time.time() + time_limit

    def solve(_d, dag, seed):
        left = t_end - time.time()
        if left <= 1.0:
            return None
        g = draw._solve_group(c, zs, allowed, bodies, body_of, outside, adj, m, p, unit_of,
                              hold, plan, planned, support, inst, lo, hi, "arm1", False,
                              min(left, time_limit / 4) if dag else left, log, extra, dag=dag,
                              start=seed, count=count, layers=True, flow=flow, border=border)
        log(f"  {c} window of {len(zs)} ZCTAs{' (dag)' if dag else ''}"
            f"{'' if cap else ' (no cap)'}: {len(g.districts)} districts, {g.columns} columns"
            f" -> {g.status} in {g.seconds:.1f}s, {g.iterations} solves, {g.cuts} cuts"
            f"{(' (' + g.note + ')') if g.note else ''}")
        return g
    tried = []
    g = draw._attempt(solve, None, tried)
    if g is None:
        g = draw.Group(js, sorted({unit_of[z] for z in zs}), len(zs), 0, 0,
                       note="not tried: no time left")
    g.tried = tried
    g.seconds = sum(t["seconds"] for t in tried)
    return g


def ball(pieces: list, free: set, adj: dict, h: int, whole: int = 750) -> set:
    """W at h hops: the free ZCTAs within h hops of a piece, and the piece itself when it has at
    most `whole` ZCTAs; of a larger piece, its ZCTAs within h hops of its border (its core stays
    fixed, a body of its district outside W)."""
    inside = set().union(*(cc for _, cc in pieces))
    small = set().union(*(cc for _, cc in pieces if len(cc) <= whole))
    border = {z for z in inside if any(y not in inside for y in adj[z])}
    return window(border, free | inside, adj, h) | small


def _hops(src: set, through: set, adj: dict) -> dict:
    dist, layer, d = dict.fromkeys(src, 0), set(src), 0
    while layer:
        d += 1
        layer = {y for z in layer for y in adj[z] if y in through and y not in dist}
        dist.update(dict.fromkeys(layer, d))
    return dist


def corridor(pieces: list, owner: dict, free: set, adj: dict, slack: int) -> set:
    """The free ZCTAs on a path of at most (the shortest + `slack`) hops from a piece to the rest
    of its district through free ZCTAs: d(piece, z) + d(z, district) <= D + slack."""
    inside = set().union(*(cc for _, cc in pieces))
    out = set()
    for j, cc in pieces:
        main = {z for z, k in owner.items() if k == j} - inside
        dp = _hops(set(cc), free | main, adj)
        dm = _hops(main, free | set(cc), adj)
        both = [dp[z] + dm[z] for z in free if z in dp and z in dm]
        if both:
            top = min(both) + slack
            out |= {z for z in free if z in dp and z in dm and dp[z] + dm[z] <= top}
    return out


def steps(pieces: list, owner: dict, free: set, adj: dict, h0: int, max_zctas: int) -> list:
    """[(shape, size, W)]: the ball at h0, 2 h0, 4 h0, ... while it grows and fits in `max_zctas`
    (past it, the largest h that fits); then the corridor at slack 0, 1, 2, 4, ... while it fits."""
    out, h, prev = [], h0, None
    while True:
        W = ball(pieces, free, adj, h, max_zctas // 2)
        if len(W) > max_zctas:
            k, floor = h - 1, (out[-1][1] if out else -1)
            while k > floor and len(ball(pieces, free, adj, k, max_zctas // 2)) > max_zctas:
                k -= 1
            if k > floor:
                out.append(("ball", k, ball(pieces, free, adj, k, max_zctas // 2)))
            break
        if len(W) == prev:          # the free area around the pieces is used up
            break
        out.append(("ball", h, W))
        prev, h = len(W), 2 * h
    prev = None
    for s in (0, 1, 2, 4, 8, 16, 32):
        W = corridor(pieces, owner, free, adj, s)
        if len(W) > max_zctas or len(W) == prev:
            break
        if not any(W == x[2] for x in out):
            out.append(("corridor", s, W))
        prev = len(W)
    return out


def clusters(pieces: list) -> list:
    """The pieces in groups repaired one at a time, smallest first: a district's pieces go
    together (a piece left outside the window would be a body its district cannot reach)."""
    out = collections.defaultdict(list)
    for pc in pieces:
        out[pc[0]].append(pc)
    return sorted(out.values(), key=lambda g: (sum(len(cc) for _, cc in g), g[0][0]))


def _repair_cluster(inst, plan, owner, pieces, free, p, state, h0, max_zctas, time_limit,
                    attempts, log, flow=False, keep_support=False, border=None, ng=None):
    c = plan.channel
    ch = inst.channels[c]
    adj, m = inst.units.zip_adj, ch.m
    todo = steps(pieces, owner, free, adj, h0, max_zctas)
    todo = [(sh, k, W, True) for sh, k, W in todo] + [(sh, k, W, False) for sh, k, W in todo[-1:]]
    skip = None
    for shape, k, W, cap in todo:
        if shape == skip and cap:
            continue
        before = map_figures(inst, c, owner, state)
        t0 = time.time()
        g = solve_window(inst, plan, owner, W, p, time_limit, cap, log, flow, keep_support,
                         {j for j, _ in pieces}, border)
        rec = {"channel": c, "shape": shape, "h" if shape == "ball" else "slack": k,
               "window_zctas": len(W), "districts": g.districts,
               "cap": cap, "flow": flow, "keep_support": keep_support, "pieces_before": len(detached(owner, adj, m)),
               "cluster": [f"{j} {min(cc)} ({len(cc)} ZCTAs)" for j, cc in pieces],
               "piece_tau_before": [round(math.fsum(m.get(z, 0.0) for z in cc) / ch.tau, 4)
                                    for _, cc in pieces],
               "status": g.status, "seconds": round(time.time() - t0, 1),
               "objective": g.objective, "bound": g.bound, "gap": g.gap, "note": g.note,
               "tried": g.tried, "before": before}
        if g.status in ("optimal", "connected"):
            owner = {**owner, **g.owner}
            rec["after"] = map_figures(inst, c, owner, state)
        rec["pieces_after"] = len(detached(owner, adj, m))
        rec["group"] = g.report()
        attempts.append(rec)
        log(f"{c}: {shape} {'h' if shape == 'ball' else 'slack'} = {k}, |W| = {len(W)}"
            f"{'' if cap else ' (no cap)'}: {g.status}, pieces {rec['pieces_before']} -> "
            f"{rec['pieces_after']}, {rec['seconds']}s")
        if g.status in ("optimal", "connected"):
            break
        if g.status != "infeasible":
            skip = shape
    return owner


def necks(owner: dict, m: dict, ng, districts=None) -> list:
    """[(district, frozenset of the side cut off, `td.audit.Neck`)] of M1's necks on the map
    `owner` (#121), of `districts` only when given."""
    by = collections.defaultdict(set)
    for z, j in owner.items():
        by[j].add(z)
    return [(j, frozenset(nk.zips), nk) for j in sorted(districts if districts is not None else by)
            for nk in audit.district_necks(by[j], m, ng)]


def _repair_neck(inst, plan, owner, j, side, free, p, state, h0, max_zctas, time_limit,
                 attempts, log, flow, keep_support, border, ng):
    """Window repair of one neck, as of a detached piece (#121): the windows of `steps` around the
    side cut off, each re-solved with the border term, the first kept that leaves no more
    detached pieces and fewer necks among its districts."""
    c = plan.channel
    ch = inst.channels[c]
    adj, m = inst.units.zip_adj, ch.m
    for shape, k, W in steps([(j, side)], owner, free, adj, h0, max_zctas):
        before = map_figures(inst, c, owner, state)
        t0 = time.time()
        g = solve_window(inst, plan, owner, W, p, time_limit, True, log, flow, keep_support,
                         {j}, border)
        n_before = len(necks(owner, m, ng, g.districts))
        rec = {"channel": c, "kind": "neck", "shape": shape, "h" if shape == "ball" else "slack": k,
               "window_zctas": len(W), "districts": g.districts, "cap": True, "flow": flow,
               "keep_support": keep_support, "pieces_before": len(detached(owner, adj, m)),
               "cluster": [f"{j} {min(side)} ({len(side)} ZCTAs)"], "necks_before": n_before,
               "status": g.status, "seconds": None, "objective": g.objective, "bound": g.bound,
               "gap": g.gap, "note": g.note, "tried": g.tried, "before": before, "kept": False}
        new = {**owner, **g.owner} if g.status in ("optimal", "connected") else owner
        rec["pieces_after"] = len(detached(new, adj, m))
        rec["necks_after"] = len(necks(new, m, ng, g.districts))
        if g.status in ("optimal", "connected") and rec["pieces_after"] <= rec["pieces_before"] \
                and rec["necks_after"] < n_before:
            owner, rec["kept"] = new, True
            rec["after"] = map_figures(inst, c, owner, state)
        rec["seconds"] = round(time.time() - t0, 1)
        rec["group"] = g.report()
        attempts.append(rec)
        log(f"{c}: neck of {j} ({len(side)} ZCTAs), {shape} {'h' if shape == 'ball' else 'slack'} "
            f"= {k}, |W| = {len(W)}: {g.status}, necks {n_before} -> {rec['necks_after']} in its "
            f"districts, {'kept' if rec['kept'] else 'not kept'}, {rec['seconds']}s")
        if rec["kept"]:
            break
    return owner


def repair_channel(inst, plan, owner: dict, p: dict, state: dict, h0: int, max_zctas: int,
                   time_limit: float, log=print, flow: bool = False,
                   keep_support: bool = False, border: dict | None = None, ng=None,
                   neck_time_limit: float | None = None) -> tuple:
    """(the repaired owner, [attempt records]); the owner changes only by a connected window.
    Per cluster of pieces (`clusters`), the windows of `steps` in turn while each is proved
    infeasible (an unknown one skips the rest of its shape), then the last one without the cap;
    rounds repeat while they remove pieces, at most three.  Then, given `ng`
    (`td.audit.NeckGraph`), each neck M1 lists (#121), smallest side first, by `_repair_neck`;
    rounds repeat while they remove necks, at most three, each neck window with `neck_time_limit` seconds (default
    `time_limit`).  Every window solves with the border term over `border`."""
    c = plan.channel
    ch, units = inst.channels[c], inst.units
    adj, m = units.zip_adj, ch.m
    _, free, _ = draw.split_fixed(inst, plan)
    free &= set(owner)
    owner = dict(owner)
    attempts = []
    pieces = detached(owner, adj, m)
    for _ in range(3):
        if not pieces:
            break
        for group in clusters(pieces):
            live = set(detached(owner, adj, m))
            group = [pc for pc in group if pc in live]
            if group:
                owner = _repair_cluster(inst, plan, owner, group, free, p, state, h0, max_zctas,
                                        time_limit, attempts, log, flow, keep_support, border)
        left = detached(owner, adj, m)
        if len(left) >= len(pieces):
            break
        pieces = left
    if ng is None:
        return owner, attempts
    found = necks(owner, m, ng)
    for _ in range(3):
        if not found:
            break
        for j in [n[0] for n in sorted(found, key=lambda n: (len(n[1]), n[0]))]:
            cur = necks(owner, m, ng, [j])
            if not cur:
                continue            # gone with an earlier window
            owner = _repair_neck(inst, plan, owner, j, cur[0][1], free, p, state, h0, max_zctas,
                                 neck_time_limit or time_limit, attempts, log, flow, keep_support,
                                 border, ng)
        left = necks(owner, m, ng)
        if len(left) >= len(found):
            break
        found = left
    return owner, attempts


def _commit() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "-C", HERE, "rev-parse", "--short", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def load(run_dir: str, extract_path: str, plans_cache: str | None, plans_file: str | None = None):
    """The run's scenario on the current graph, the plans that drew it (`plans_file`, a pickle of
    `run.plans_for`'s pair, when the run was drawn on another connector list; else the cache) and
    its owners read back from the ledger."""
    with open(os.path.join(run_dir, "run.json")) as fh:
        src = json.load(fh)
    spec_path = src["spec"]
    s = tdspec.load(spec_path)
    ref = geo.read_reference()
    extract = data.load(extract_path)
    ext = tdspec.scope(s, data.conus(extract, ref))
    polygon = geo.polygon_graph()
    inst = tdspec.build(s, ext, ref)
    if plans_file:
        with open(plans_file, "rb") as fh:
            plans, reports = pickle.load(fh)
    else:
        plans, reports = run.plans_for(inst, spec_path, extract_path, plans_cache)
    bad = check_source(os.path.join(run_dir, "districts.csv"), plans)
    if bad:
        raise RuntimeError(f"{run_dir} was not drawn by these plans: " + "; ".join(bad[:5])
                           + (f" (+{len(bad) - 5} more)" if len(bad) > 5 else ""))
    owners = owners_from_ledger(output.read_ledger(os.path.join(run_dir, "ledger.csv")), plans)
    return s, ref, ext, polygon, inst, plans, reports, owners, src


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--plans", default=None, help="the plan cache of `run.py`")
    ap.add_argument("--plans-file", default=None,
                    help="the plans that drew the run, when its connector list was another")
    ap.add_argument("--label", default="", help="added to the scorecard title, e.g. its provenance")
    ap.add_argument("--h0", type=int, default=3)
    ap.add_argument("--max-zctas", type=int, default=1500)
    ap.add_argument("--time-limit", type=float, default=600.0, help="seconds per window")
    ap.add_argument("--neck-time-limit", type=float, default=None,
                    help="seconds per neck window (default --time-limit)")
    ap.add_argument("--channels", nargs="*", default=None)
    ap.add_argument("--flow", action="store_true",
                    help="hold each window district connected by a flow as well as the cuts")
    ap.add_argument("--keep-support", action="store_true",
                    help="arm 1: a ZCTA only to a district whose plan holds its unit")
    ap.add_argument("--maps", action="store_true")
    a = ap.parse_args(argv)
    output.check_out(a.out)
    commit = _commit()
    params = {k: v for k, v in vars(a).items() if k not in ("run_dir", "out")}
    with open(os.path.join(a.run_dir, "run.json")) as fh:
        spec_path = json.load(fh)["spec"]
    run.write_manifest(a.out, "contig_repair", spec_path, a.extract, params, a.plans_file, a.run_dir)
    s, ref, ext, polygon, inst, plans, reports, owners, src = load(a.run_dir, a.extract, a.plans,
                                                                       a.plans_file)
    border, ng = draw.border_km(polygon), audit.NeckGraph(polygon)
    os.makedirs(a.out, exist_ok=True)
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    p = {z: (float(x) / 1000.0, float(y) / 1000.0) for z, x, y in zip(rows.index, rows["x"], rows["y"])}
    state = dict(zip(rows.index, rows["state"]))
    with open(os.path.join(a.run_dir, "contig.json")) as fh:
        doc = json.load(fh)
    connectors = set(geo.approved_connectors(geo.read_connectors()))
    drawings = {}
    for c, plan in plans.items():
        owner = owners[c]
        attempts = []
        before_km = draw.cut_border(owner, inst.units.zip_adj, border)
        if a.channels is None or c in a.channels:
            owner, attempts = repair_channel(inst, plan, owner, p, state, a.h0, a.max_zctas,
                                             a.time_limit, flow=a.flow,
                                             keep_support=a.keep_support, border=border, ng=ng,
                                             neck_time_limit=a.neck_time_limit)
        res = draw.Result(c, owner, [], set(), [], [], plan.delta, "repair", False)
        d = draw.drawing(inst, plan, res)
        drawings[c] = d
        left = detached(owner, inst.units.zip_adj, inst.channels[c].m)
        entry = doc["channels"][c]
        entry["repair"] = attempts
        entry["groups"] = entry["groups"] + [r["group"] for r in attempts]
        if attempts:
            entry["connected"] = not left
            entry["status"] = "connected" if not left else entry["status"]
            entry["source_group_delta_needed"] = entry.pop("group_delta_needed", None)
            entry["repair_band"] = {"delta": inst.channels[c].spec.final_delta,
                                   "worst_dev": map_figures(inst, c, owner, state)["worst_dev"]}
        entry.update(run.drawn_stats(inst, plan, d, connectors, not left, border))
        entry["cut_border_km_before_repair"] = before_km
        entry["necks_left"] = [f"{j} {min(side)} ({len(side)} ZCTAs, {nk.width_km:.2f} km)"
                               for j, side, nk in necks(owner, inst.channels[c].m, ng)]
    report, m1 = run.write_folder(a.out, s, inst, ext, ref, polygon, plans, reports, drawings,
                                  f"{s.name} (contig {doc['arm']} + window repair{', ' + a.label if a.label else ''})",
                                  f"tools/exp/contig ({doc['arm']} + repair)", src.get("source", ""),
                                  a.maps)
    doc.update({"arm": doc["arm"] + "+repair", "repair_of": os.path.abspath(a.run_dir),
                "repair": {"h0": a.h0, "max_zctas": a.max_zctas, "time_limit": a.time_limit,
                           "neck_time_limit": a.neck_time_limit,
                           "plans_file": a.plans_file, "label": a.label,
                           "flow": a.flow, "keep_support": a.keep_support,
                           "commit": commit},
                "m1": report["m1"]})
    with open(os.path.join(a.out, "contig.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    run.write_manifest(a.out, "contig_repair", spec_path, a.extract, params, status="done",
                       stop_reason="repaired", audit=report["verdict"], m1=m1.status)
    print(f"{s.name} (repair of {a.run_dir}): M1 {m1.status} ({m1.summary}); audit "
          f"{report['verdict']}")
    return 0 if m1.status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
