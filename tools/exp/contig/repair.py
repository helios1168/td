"""repair.py -- #109's exact window repair (large-neighbourhood search) of a drawn contig run
folder that fails M1.

    "$TD_PY" -u tools/exp/contig/repair.py <run_dir> --out <dir> [--extract PATH] [--plans PATH]
        [--h0 3] [--max-zctas 1500] [--time-limit 600] [--budget s] [--channels c ...] [--maps]
        [--jobs N]

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
- **Neck-aware windows** (#121, given the neck graph, as `main` always is): every window, of a
  piece or a neck, runs M1's exact neck check (`td.audit.district_necks`) on each drawing its
  loop would keep, and each neck meeting W in a district of the window adds a `draw.NeckCut`
  (`neck_cuts`): the border across the neck's side, counted where both ends stay the district's,
  at least 10 km while its anchor sets stay the district's and its land stays small enough for
  them to hold the 5% share; valid for every drawing without a neck.  Districts with a neck on
  the map that the window is not repairing are exempt (listed).  A window's drawing then has no
  neck meeting W in a district it is held to; its "optimal" is over the cut-augmented model and
  its "infeasible" proves that no drawing of W, the rest fixed, is connected, in the band and
  leaves every district it cut without a neck.

- **Opened units** (#122, `--open-units`): the ZCTAs of the units named join the free ZCTAs, and
  any district of a window may take them even with `--keep-support`; the cap lets each such unit
  of W gain one split.  An arm-2 split of a unit held whole, for a neck no arm-1 window reaches.

- **In parallel** (#123, `--jobs N` above 1; 1 is the sequential loop): each channel is repaired
  in its own process (`repair_parallel`), and each escalation, of a piece or a neck, is a race
  (`_race`): up to N windows of its sequence solve at once in worker processes (`WindowPool`,
  HiGHS pinned to one thread in every worker, trap 18), at most N solves across the channels, a
  channel's own neck counts among them (`WindowPool.hold`).  A window gets the channel's deadline
  and takes its time limit from it as its worker begins (`_window_task`).  When a channel fails
  the others are stopped, each closing its windows, and every process is joined (`run.stop`).
  Attempts settle in sequence order, never by finish time: the first success in sequence order is
  kept, an earlier window is waited for to its own time limit, a later one is killed once an
  earlier one succeeds, and an unknown window still skips the later capped ones of its shape.
  With no window stopped by a time limit (or `--budget`) the folder is the sequential run's but
  for seconds.

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
`--diag-final-delta` holds the windows and the audit at another band instead: a diagnostic, never a
deliverable, marked `"diagnostic": true` in run.json and the manifest (as is any repair of a
diagnostic folder, #121, `audit.diagnostic`), named so in its title and stop reason; its scorecard's
bands row gives the scenario's bands' result beside the diagnostic one.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
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


_NECKS = {}     # (id(m), id(ng), frozenset of a district's ZCTAs) -> (m, ng, [audit.Neck])
ANCHOR_MARGIN = 1.2     # an anchor set holds this many times the share of its district's land


def district_necks(zips, m: dict, ng) -> list:
    """`audit.district_necks` of one district, cached by its ZCTAs (the entry holds `m` and `ng`,
    so their ids stay theirs)."""
    key = (id(m), id(ng), frozenset(zips))
    if key not in _NECKS:
        if len(_NECKS) >= 20000:
            _NECKS.clear()
        _NECKS[key] = (m, ng, audit.district_necks(set(zips), m, ng))
    return _NECKS[key][2]


def _nbrs(ng, z) -> set:
    return set(ng.border.get(z, ())) | ng.connector.get(z, set())


# M1's check: a cut of floored whole cm (`audit.border_cm`) is a neck at NECK_W_CM - 1 or less and
# none at NECK_W_CM or more; half a cm between keeps the row's float sums off either side
NECK_KM = (audit.NECK_W_CM - 0.5) / 1e5


def _edge_km(ng, u: str, v: str, states: frozenset) -> float:
    """The edge's width in a neck cut (`draw.NeckCut`), as M1's check counts it: its border in
    floored whole cm, plus for an approved connector 0 where land would do within `states` and the
    limit otherwise; in km, capped at the limit."""
    km = ng.border_cm.get(u, {}).get(v, 0) / 1e5
    if v in ng.connector.get(u, ()):
        km += 0.0 if ng.land_would_do(u, v, states) else NECK_KM
    return min(km, NECK_KM)


def _anchors(X: set, W: set, ng, target: float) -> set:
    """A connected subset of the connected set `X` holding `target` km² of land, or all of `X`:
    its largest component outside `W` (anchors outside the window cost the cut nothing), grown
    by every neighbour outside `W`, else by the neighbour in `W` with the most land."""
    area = {z: ng.aland.get(z, 0.0) / 1e6 for z in X}
    out = {z: {y for y in _nbrs(ng, z) if y in X} for z in X}
    fixed = draw.components(X - W, out)        # ties: the first, as `components` orders them
    S = set(max(fixed, key=lambda cc: math.fsum(area[z] for z in cc))) if fixed \
        else {max(sorted(X), key=lambda z: area[z])}
    have = math.fsum(area[z] for z in S)
    front = {y for z in S for y in out[z]} - S
    while have < target and front:
        take = (front - W) or {max(front & W, key=lambda z: (area[z], z))}
        S |= take
        have += math.fsum(area[z] for z in take)
        front = (front | {y for z in take for y in out[z]}) - S
    return S


def neck_cuts(c: str, owner: dict, W: set, m: dict, ng, own: dict, check) -> tuple:
    """([draw.NeckCut], [labels]) of the necks the window drawing `own` {ZCTA of W: district}
    must lose (#121): each neck M1 finds on the map `owner` with `own` in it, of a district in
    `check`, whose side meets W or has an edge into W (a neck wholly outside W is the rest's).
    Each gets one cut, its anchors (`_anchors`) holding `ANCHOR_MARGIN` times the share of the
    district's land on that map (the cut binds while the district's land stays below
    a_min / share)."""
    new = {**owner, **own}
    by = collections.defaultdict(set)
    for z, j in new.items():
        if j in check:
            by[j].add(z)
    cuts, labels = [], []
    for j in sorted(by):
        D = by[j]
        for nk in district_necks(D, m, ng):
            A = set(nk.zips)
            delta = [(u, v) for u in sorted(A) for v in sorted(_nbrs(ng, u)) if v not in A]
            if not (A & W or any(v in W for _, v in delta)) and nk.status == "proved":
                continue
            label = audit.neck_item(c, j, nk)
            labels.append(label)
            if nk.status != "proved":
                continue
            seen, stack = set(A), list(A)       # the rest: A's component of D, less A
            while stack:
                for y in _nbrs(ng, stack.pop()):
                    if y in D and y not in seen:
                        seen.add(y)
                        stack.append(y)
            R = seen - A
            fixed_j = {z for z, k in owner.items() if k == j and z not in W}
            states = frozenset(ng.state.get(z, "") for z in fixed_j)
            const, single, pair = 0.0, [], []
            for u, v in delta:
                if not all(z in W or owner.get(z) == j for z in (u, v)):
                    continue                    # an end fixed in another district
                km = _edge_km(ng, u, v, states)
                if km <= 0:
                    continue
                if u in W and v in W:
                    pair.append((u, v, km))
                elif u in W or v in W:
                    single.append((u if u in W else v, km))
                else:
                    const += km
            area_fixed = math.fsum(ng.aland.get(z, 0.0) for z in fixed_j) / 1e6
            area = tuple((z, ng.aland.get(z, 0.0) / 1e6) for z in sorted(W))
            tot = math.fsum(ng.aland.get(z, 0.0) for z in D) / 1e6
            target = ANCHOR_MARGIN * audit.NECK_SHARE * tot
            sa, sr = _anchors(A, W, ng, target), _anchors(R, W, ng, target)
            a_min = min(math.fsum(ng.aland.get(z, 0.0) for z in s) for s in (sa, sr)) / 1e6
            cuts.append(draw.NeckCut(j, const, tuple(single), tuple(pair),
                                     tuple(sorted((sa | sr) & W)), area_fixed, area, a_min,
                                     NECK_KM, audit.NECK_SHARE,
                                     label))
    return cuts, labels


def solve_window(inst, plan, owner: dict, W: set, p: dict, time_limit: float, cap: bool,
                 log=print, flow: bool = False, keep_support: bool = False,
                 repairing: set = frozenset(), border: dict | None = None, ng=None,
                 opened: frozenset = frozenset()):
    """`draw.Group` of the window `W` (module docstring), everything outside fixed.  With
    `keep_support` (arm 1) a ZCTA may go only to a district whose plan holds its unit (an exclave
    or dropped ZCTA to any); else to any district of the window (a unit may change holders: an
    arm-2 move, reported by the audit's planned-against-drawn check).  Given `ng`
    (`audit.NeckGraph`) the window is neck-aware (#121): its drawing must leave no neck meeting W
    in its districts but the exempt ones, those with a neck on the map that are not `repairing`
    (`neck_cuts`, `draw._solve_group`); the group lists them under `neck_exempt`.  A ZCTA of
    `opened` (`--open-units`, #122) may go to any district of the window even with
    `keep_support`, and the cap lets each opened unit of W gain one split (an arm-2 split)."""
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
            if z not in exclave and unit_of[z] not in ch.dropped_units and z not in opened:
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
    count = {"current": holders_on(owner, units, {unit_of[z] for z in W}), "cap": cap,
             "opened": frozenset(unit_of[z] for z in W & opened)}
    zs = sorted(W)
    cutter, exempt = None, []
    if ng is not None:
        on_map = collections.defaultdict(set)
        for z, j in owner.items():
            if j in js:
                on_map[j].add(z)
        exempt = sorted(j for j in js
                        if j not in repairing and district_necks(on_map[j], m, ng))
        check = set(js) - set(exempt)

        def cutter(own):
            return neck_cuts(c, owner, W, m, ng, own, check)
    t_end = time.time() + time_limit

    def solve(_d, dag, seed):
        left = t_end - time.time()
        if left <= 1.0:
            return None
        g = draw._solve_group(c, zs, allowed, bodies, body_of, outside, adj, m, p, unit_of,
                              hold, plan, planned, support, inst, lo, hi, "arm1", False,
                              min(left, time_limit / 4) if dag else left, log, extra, dag=dag,
                              start=seed, count=count, layers=True, flow=flow, border=border,
                              necks=cutter, neck_seed={z: owner[z] for z in zs})
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
    g.neck_exempt = exempt
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


def _time_left(time_limit: float, deadline: float | None, log, what: str) -> float:
    """A window's seconds under the channel's `deadline` (`--budget`); 0 once it has passed."""
    if deadline is None:
        return time_limit
    left = deadline - time.time()
    if left < 30.0:
        log(f"budget spent: {what} not tried")
        return 0.0
    return min(time_limit, left)


def _repair_cluster(inst, plan, owner, pieces, free, p, state, h0, max_zctas, time_limit,
                    attempts, log, flow=False, keep_support=False, border=None, ng=None,
                    deadline=None, opened=frozenset(), pool=None):
    c = plan.channel
    adj = inst.units.zip_adj
    todo = steps(pieces, owner, free, adj, h0, max_zctas)
    todo = [(sh, k, W, True) for sh, k, W in todo] + [(sh, k, W, False) for sh, k, W in todo[-1:]]
    repairing = {j for j, _ in pieces}
    if pool is not None:
        return _race_cluster(inst, plan, owner, pieces, todo, repairing, state, time_limit,
                             attempts, log, flow, keep_support, ng, deadline, opened, pool)
    skip = None
    for shape, k, W, cap in todo:
        if shape == skip and cap:
            continue
        tl = _time_left(time_limit, deadline, log, f"{c} {shape} {k} of {pieces[0][0]}")
        if not tl:
            break
        before = map_figures(inst, c, owner, state)
        t0 = time.time()
        g = solve_window(inst, plan, owner, W, p, tl, cap, log, flow, keep_support,
                         repairing, border, ng, opened)
        owner = _settle_cluster(inst, c, owner, pieces, (shape, k, W, cap), g, before,
                                round(time.time() - t0, 1), state, attempts, log, flow,
                                keep_support, ng)
        if g.status in ("optimal", "connected"):
            break
        if g.status != "infeasible":
            skip = shape
    return owner


def _settle_cluster(inst, c, owner, pieces, step, g, before, seconds, state, attempts, log, flow,
                    keep_support, ng):
    """Record a piece window's solve `g` (`_repair_cluster`); the owner, the window's drawing in
    it when connected."""
    shape, k, W, cap = step
    ch = inst.channels[c]
    adj, m = inst.units.zip_adj, ch.m
    rec = {"channel": c, "shape": shape, "h" if shape == "ball" else "slack": k,
           "window_zctas": len(W), "districts": g.districts,
           "cap": cap, "flow": flow, "keep_support": keep_support, "pieces_before": len(detached(owner, adj, m)),
           "cluster": [f"{j} {min(cc)} ({len(cc)} ZCTAs)" for j, cc in pieces],
           "piece_tau_before": [round(math.fsum(m.get(z, 0.0) for z in cc) / ch.tau, 4)
                                for _, cc in pieces],
           "status": g.status, "seconds": seconds,
           "objective": g.objective, "bound": g.bound, "gap": g.gap, "note": g.note,
           "tried": g.tried, "before": before, "neck_aware": ng is not None,
           "neck_cuts": g.neck_cuts}
    if g.status in ("optimal", "connected"):
        owner = {**owner, **g.owner}
        rec["after"] = map_figures(inst, c, owner, state)
    rec["pieces_after"] = len(detached(owner, adj, m))
    rec["group"] = g.report()
    attempts.append(rec)
    log(f"{c}: {shape} {'h' if shape == 'ball' else 'slack'} = {k}, |W| = {len(W)}"
        f"{'' if cap else ' (no cap)'}: {g.status}, pieces {rec['pieces_before']} -> "
        f"{rec['pieces_after']}, {rec['seconds']}s")
    return owner


def _race_cluster(inst, plan, owner, pieces, todo, repairing, state, time_limit, attempts, log,
                  flow, keep_support, ng, deadline, opened, pool):
    """`_repair_cluster`'s windows as a race on `pool` (`_race`): an unknown window still skips
    the later capped ones of its shape, as in the loop."""
    c = plan.channel
    before = map_figures(inst, c, owner, state)
    skip = []

    def launch(i):
        shape, k, W, cap = todo[i]
        what = f"{c} {shape} {k} of {pieces[0][0]}"
        if not _time_left(time_limit, deadline, log, what):
            return None
        return c, owner, W, time_limit, deadline, what, cap, flow, keep_support, repairing, opened

    def settle(i, res):
        nonlocal owner
        g, seconds = res
        owner = _settle_cluster(inst, c, owner, pieces, todo[i], g, before, round(seconds, 1),
                                state, attempts, log, flow, keep_support, ng)
        if g.status not in ("optimal", "connected", "infeasible"):
            skip.append(todo[i][0])
        return g.status in ("optimal", "connected")

    _race(pool, len(todo), launch, settle, lambda i: not (todo[i][3] and todo[i][0] in skip))
    return owner


def necks(owner: dict, m: dict, ng, districts=None) -> list:
    """[(district, frozenset of the side cut off, `td.audit.Neck`)] of M1's necks on the map
    `owner` (#121), of `districts` only when given."""
    by = collections.defaultdict(set)
    for z, j in owner.items():
        by[j].add(z)
    return [(j, frozenset(nk.zips), nk) for j in sorted(districts if districts is not None else by)
            for nk in district_necks(by[j], m, ng)]


STEP_KEY = {"ball": "h", "corridor": "slack", "own": "zctas"}   # a window step's size, by shape


def own_window(owner: dict, j: str, side, opened: frozenset, unit_of: dict) -> set:
    """The ZCTAs `j` holds in the opened units (`--open-units`) its neck's `side` lies in (#122):
    a window of the district's own ZCTAs, through which a neighbour may take the side."""
    units = {unit_of[z] for z in side if z in opened}
    return {z for z in opened if owner.get(z) == j and unit_of[z] in units}


def _repair_neck(inst, plan, owner, j, side, free, p, state, h0, max_zctas, time_limit,
                 attempts, log, flow, keep_support, border, ng, deadline=None,
                 opened=frozenset(), pool=None):
    """Window repair of one neck, as of a detached piece (#121): the windows of `steps` around the
    side cut off, after `own_window` when the side lies in an opened unit (#122), each re-solved
    with the border term, the first kept that leaves no more detached pieces and fewer necks among
    its districts."""
    c = plan.channel
    adj = inst.units.zip_adj
    todo = steps([(j, side)], owner, free, adj, h0, max_zctas)
    own = own_window(owner, j, side, opened, inst.units.unit_of)
    if own and len(own) <= max_zctas:
        todo = [("own", len(own), own)] + [st for st in todo if st[2] != own]
    if pool is not None:
        return _race_neck(inst, plan, owner, j, side, todo, state, time_limit, attempts, log,
                          flow, keep_support, ng, deadline, opened, pool)
    for shape, k, W in todo:
        tl = _time_left(time_limit, deadline, log, f"{c} neck of {j}, {shape} {k}")
        if not tl:
            break
        before = map_figures(inst, c, owner, state)
        t0 = time.time()
        g = solve_window(inst, plan, owner, W, p, tl, True, log, flow, keep_support,
                         {j}, border, ng, opened)
        owner, kept = _settle_neck(inst, c, owner, j, side, (shape, k, W), g, before, t0, state,
                                   attempts, log, flow, keep_support, ng)
        if kept:
            break
    return owner


def _settle_neck(inst, c, owner, j, side, step, g, before, t0, state, attempts, log, flow,
                 keep_support, ng) -> tuple:
    """Record a neck window's solve `g` (`_repair_neck`), its seconds counted from `t0`; (the
    owner, whether the window's drawing was kept in it)."""
    shape, k, W = step
    adj, m = inst.units.zip_adj, inst.channels[c].m
    n_before = len(necks(owner, m, ng, g.districts))
    rec = {"channel": c, "kind": "neck", "shape": shape, STEP_KEY[shape]: k,
           "window_zctas": len(W), "districts": g.districts, "cap": True, "flow": flow,
           "keep_support": keep_support, "pieces_before": len(detached(owner, adj, m)),
           "cluster": [f"{j} {min(side)} ({len(side)} ZCTAs)"], "necks_before": n_before,
           "status": g.status, "seconds": None, "objective": g.objective, "bound": g.bound,
           "gap": g.gap, "note": g.note, "tried": g.tried, "before": before, "kept": False,
           "neck_aware": True, "neck_cuts": g.neck_cuts, "neck_exempt": g.neck_exempt}
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
    log(f"{c}: neck of {j} ({len(side)} ZCTAs), {shape} {STEP_KEY[shape]} "
        f"= {k}, |W| = {len(W)}: {g.status}, necks {n_before} -> {rec['necks_after']} in its "
        f"districts, {g.neck_cuts} neck cuts, {'kept' if rec['kept'] else 'not kept'}, "
        f"{rec['seconds']}s")
    return owner, rec["kept"]


def _race_neck(inst, plan, owner, j, side, todo, state, time_limit, attempts, log, flow,
               keep_support, ng, deadline, opened, pool):
    """`_repair_neck`'s windows as a race on `pool` (`_race`); a window's seconds are its solve's
    and then the neck counts that judge it."""
    c = plan.channel
    before = map_figures(inst, c, owner, state)

    def launch(i):
        shape, k, W = todo[i]
        what = f"{c} neck of {j}, {shape} {k}"
        if not _time_left(time_limit, deadline, log, what):
            return None
        return c, owner, W, time_limit, deadline, what, True, flow, keep_support, {j}, opened

    def settle(i, res):
        nonlocal owner
        g, seconds = res
        with pool.hold():                       # its neck counts are MILPs here
            owner, kept = _settle_neck(inst, c, owner, j, side, todo[i], g, before,
                                       time.time() - seconds, state, attempts, log, flow,
                                       keep_support, ng)
        return kept

    _race(pool, len(todo), launch, settle, lambda i: True)
    return owner


def repair_channel(inst, plan, owner: dict, p: dict, state: dict, h0: int, max_zctas: int,
                   time_limit: float, log=print, flow: bool = False,
                   keep_support: bool = False, border: dict | None = None, ng=None,
                   neck_time_limit: float | None = None, budget: float | None = None,
                   open_units=(), pool=None) -> tuple:
    """(the repaired owner, [attempt records]); the owner changes only by a connected window.
    Per cluster of pieces (`clusters`), the windows of `steps` in turn while each is proved
    infeasible (an unknown one skips the rest of its shape), then the last one without the cap;
    rounds repeat while they remove pieces, at most three.  Then, given `ng`
    (`td.audit.NeckGraph`), each neck M1 lists (#121), those with a side in an opened unit first
    (#122), then smallest side first, by `_repair_neck`;
    rounds repeat while they remove necks, at most three, each neck window with `neck_time_limit` seconds (default
    `time_limit`).  Every window solves with the border term over `border`.  With `budget`
    (seconds), no window starts once the channel has spent it, and the last gets what is left.
    With `pool` (`WindowPool`, #123) each escalation is a race (`_race`), its result the loop's."""
    deadline = None if budget is None else time.time() + budget
    c = plan.channel
    ch, units = inst.channels[c], inst.units
    adj, m = units.zip_adj, ch.m
    _, free, _ = draw.split_fixed(inst, plan)
    opened = frozenset(z for v in open_units if v in ch.units for z in units.zips[v]) & set(owner)
    free = (free | opened) & set(owner)     # `--open-units`: their ZCTAs join the windows (#122)
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
                                        time_limit, attempts, log, flow, keep_support, border, ng,
                                        deadline, opened, pool)
        left = detached(owner, adj, m)
        if len(left) >= len(pieces):
            break
        pieces = left
    if ng is None:
        return owner, attempts
    def first(n):               # the order necks are repaired in, within a district too
        return not n[1] & opened, len(n[1]), n[0]
    found = necks(owner, m, ng)
    for _ in range(3):
        if not found:
            break
        for j in [n[0] for n in sorted(found, key=first)]:
            cur = necks(owner, m, ng, [j])
            if not cur:
                continue            # gone with an earlier window
            owner = _repair_neck(inst, plan, owner, j, min(cur, key=first)[1], free, p, state,
                                 h0, max_zctas, neck_time_limit or time_limit, attempts, log,
                                 flow, keep_support, border, ng, deadline, opened, pool)
        left = necks(owner, m, ng)
        if len(left) >= len(found):
            break
        found = left
    return owner, attempts


# ------------------------------------------------------------------------------ in parallel (#123)
WORKER = "contig_repair_worker"     # the name a worker process runs this file under


def _race(pool, n, launch, settle, wanted) -> None:
    """Attempts 0..n-1 of one escalation, as many at a time as `pool` has room for (#123).
    `launch(i)` gives attempt i's task, or None when the budget lets no window start (then no later
    one starts either); `settle(i, result)` records attempt i and says whether the escalation
    stops there; `wanted(i)` says whether attempt i still runs after those settled (a skip rule).
    Attempts settle in sequence order, never by finish time: an earlier one is waited for to its
    own time limit, and a later one is killed once an earlier one stops the escalation or a skip
    rule drops it, so the attempts settled are the sequential loop's.  A result None is a window
    its worker found the budget spent for as it began (`_window_task`): it and every later one go
    unsettled, as the loop never starts them."""
    running, done = {}, {}
    head = nxt = 0
    end = n
    try:
        while head < end:
            if not wanted(head):
                if head in running:
                    pool.kill(running.pop(head))
                done.pop(head, None)
                head += 1
                continue
            nxt = max(nxt, head)
            while nxt < end and (not wanted(nxt) or pool.reserve()):
                if wanted(nxt):
                    task = launch(nxt)
                    if task is None:
                        pool.unreserve()
                        end = nxt
                        break
                    running[nxt] = pool.start(task)
                nxt += 1
            if head >= end:
                break
            if head not in done:
                back = {h: i for i, h in running.items()}
                for h, res in pool.wait(list(back), 1.0):
                    done[back[h]] = res
                    del running[back[h]]
            if head in done:
                res = done.pop(head)
                if res is None:
                    break
                stop = settle(head, res)
                head += 1
                if stop:
                    break
                for i in [i for i in running if not wanted(i)]:
                    pool.kill(running.pop(i))
    finally:
        for h in running.values():
            pool.kill(h)


def _spawn(role: str, shared: str, slots=None, daemon: bool = True, log: bool = True) -> tuple:
    """(process, connection) of a worker process (`_serve`) running this file (`run.spawn`; a
    channel leads its process group)."""
    return run.spawn(os.path.abspath(__file__), WORKER, (role, shared, slots, log), daemon,
                     lead=role == "channel")


class WindowPool:
    """Up to `jobs` worker processes solving one channel's windows (#123), each with HiGHS pinned
    to one thread (`run.pin_threads`).  Every running solve passes one gate: the windows started
    and not yet done, and a solve in the channel's own process (`hold`).  With `slots`, a count of
    free solver processes shared by the channels, a channel's first running solve is its own and
    each further one takes a slot.  With `log` false the workers print nothing."""

    def __init__(self, jobs: int, shared: str, slots=None, log: bool = True):
        self.jobs, self.shared, self.slots, self.log = jobs, shared, slots, log
        self.idle, self.busy = [], {}           # [(process, connection)], {connection: process}
        self.done = {}                          # {connection: (process, result)}, not yet waited for
        self.solving = 0                        # running solves, a reserved one counted
        self.reserved = False
        self.started = 0                        # tasks started

    def _take(self) -> bool:
        """Count one more running solve, when the gate lets it start."""
        if self.solving >= self.jobs:
            return False
        if self.solving and self.slots is not None:
            with self.slots.get_lock():
                if self.slots.value <= 0:
                    return False
                self.slots.value -= 1
        self.solving += 1
        return True

    def _give(self) -> None:
        self.solving -= 1
        if self.solving and self.slots is not None:
            with self.slots.get_lock():
                self.slots.value += 1

    def reserve(self) -> bool:
        """Whether one more window may start now (taking a slot for it when one is needed)."""
        if len(self.busy) + len(self.done) >= self.jobs or not self._take():
            return False
        self.reserved = True
        return True

    def unreserve(self) -> None:
        if self.reserved:
            self._give()
        self.reserved = False

    @contextlib.contextmanager
    def hold(self):
        """A solve in the channel's own process (`_settle_neck`'s neck counts) through the gate:
        it waits for room, the windows that finish meanwhile moving to `done`."""
        while not self._take():
            self._collect(0.05)
        try:
            yield
        finally:
            self._give()

    def start(self, task):
        proc, conn = self.idle.pop() if self.idle else self._spawn()
        conn.send(task)
        self.busy[conn] = proc
        self.reserved = False
        self.started += 1
        return conn

    def _collect(self, timeout: float) -> None:
        """Move the windows done within `timeout` from `busy` to `done`."""
        from multiprocessing.connection import wait
        for conn in wait(list(self.busy), timeout):
            res = run.receive(conn, "window")
            self.done[conn] = (self.busy.pop(conn), res)
            self._give()

    def wait(self, conns: list, timeout: float) -> list:
        """[(connection, (Group, seconds) or None)] of the windows of `conns` done within `timeout`
        (None: not started, `_window_task`)."""
        if not any(conn in self.done for conn in conns):
            self._collect(timeout)
        out = []
        for conn in conns:
            if conn in self.done:
                proc, res = self.done.pop(conn)
                self.idle.append((proc, conn))
                out.append((conn, res))
        return out

    def kill(self, conn) -> None:
        """Stop a window; a fresh worker starts loading in its place."""
        if conn in self.done:                   # done already: its worker is idle
            self.idle.append((self.done.pop(conn)[0], conn))
            return
        proc = self.busy.pop(conn)
        self._give()
        self._stop(proc, conn)
        self.idle.append(self._spawn())

    def _spawn(self):
        return _spawn("window", self.shared, log=self.log)

    def _stop(self, proc, conn) -> None:
        proc.kill()
        proc.join()
        conn.close()

    def close(self) -> None:
        """Kill and join every worker."""
        workers = [(proc, conn) for conn, proc in self.busy.items()] + self.idle \
            + [(proc, conn) for conn, (proc, _) in self.done.items()]
        self.busy, self.idle, self.done, self.solving = {}, [], {}, 0
        for proc, conn in workers:
            self._stop(proc, conn)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def write_shared(path: str, inst, plans: dict, p: dict, state: dict, border, ng) -> str:
    """Pickle what every worker process reads once to `path`."""
    with open(path, "wb") as fh:
        pickle.dump({"inst": inst, "plans": plans, "p": p, "state": state, "border": border,
                     "ng": ng}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return path


def _print(line: str) -> None:
    print(line, flush=True)


def _window_task(sh: dict, task: tuple, log):
    """A window task's (Group, seconds) (`_race_cluster`, `_race_neck`), its time limit taken
    from the channel's deadline as the task begins; None, the window not tried, when the budget
    is spent by then (`_time_left`)."""
    c, owner, W, time_limit, deadline, what, cap, flow, keep_support, repairing, opened = task
    tl = _time_left(time_limit, deadline, log, what)
    if not tl:
        return None
    t0 = time.time()
    g = solve_window(sh["inst"], sh["plans"][c], owner, W, sh["p"], tl, cap, log, flow,
                     keep_support, repairing, sh["border"], sh["ng"], opened)
    return g, time.time() - t0


def _stopped(*_) -> None:
    import signal
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise SystemExit(128 + signal.SIGTERM)


def _serve(conn, role: str, shared: str, slots, log: bool) -> None:
    """A worker process, HiGHS pinned to one thread before anything else: `window` solves window
    tasks (`_window_task`) until its connection closes; `channel` repairs one channel
    (`repair_channel`) with a `WindowPool` and sends (owner, attempts).  A channel leads its own
    process group, its windows in it, and on SIGTERM (`run.stop`) closes its pool and exits."""
    import signal
    import traceback
    run.pin_threads()
    if role == "channel":
        os.setpgrp()
        signal.signal(signal.SIGTERM, _stopped)
    _log = _print if log else (lambda *_: None)
    with open(shared, "rb") as fh:
        sh = pickle.load(fh)
    while True:
        try:
            task = conn.recv()
        except EOFError:
            return
        try:
            if role == "window":
                conn.send(("done", _window_task(sh, task, _log)))
            else:
                c, owner, jobs, kw = task
                with WindowPool(jobs, shared, slots, log) as pool:
                    res = repair_channel(sh["inst"], sh["plans"][c], owner, sh["p"], sh["state"],
                                         log=_log, border=sh["border"], ng=sh["ng"], pool=pool,
                                         **kw)
                conn.send(("done", res))
                return
        except BaseException:
            conn.send(("error", traceback.format_exc()))
            raise


def repair_parallel(inst, plans: dict, owners: dict, p: dict, state: dict, channels: list,
                    jobs: int, border=None, ng=None, log: bool = True, **kw) -> dict:
    """{channel: (the repaired owner, [attempt records])} of `channels` (#123): each repaired in
    its own process, at most `jobs` at once, by `repair_channel` with `kw` and a `WindowPool` of
    `jobs` racing its windows, the processes together running at most `jobs` solves (a shared
    count of slots: each running channel's first solve is its own).  The channels' ledger
    cells are disjoint, so the dict is the one the sequential loop builds whenever no window stops
    on a time limit.  When one fails, every other is stopped (`run.stop`) before the error is
    raised.  With `log` false the processes print nothing."""
    import multiprocessing
    import shutil
    import tempfile
    from multiprocessing.connection import wait
    tmp = tempfile.mkdtemp(prefix="td-repair-")
    out, todo, running = {}, list(channels), {}
    try:
        shared = write_shared(os.path.join(tmp, "shared.pkl"), inst, plans, p, state, border, ng)
        slots = multiprocessing.get_context("spawn").Value("i", jobs - min(jobs, len(todo)))
        while todo or running:
            while todo and len(running) < jobs:
                c = todo.pop(0)
                proc, conn = _spawn("channel", shared, slots, daemon=False, log=log)
                conn.send((c, owners[c], jobs, kw))
                running[conn] = (c, proc)
            for conn in wait(list(running)):
                c, proc = running[conn]
                out[c] = run.receive(conn, f"{c} channel")
                del running[conn]               # a failed one stays, for `run.stop`
                proc.join()
                if not todo:                    # its first-solve slot passes to the others
                    with slots.get_lock():
                        slots.value += 1
    finally:
        run.stop([proc for _, proc in running.values()])
        shutil.rmtree(tmp, ignore_errors=True)
    return out


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
    ap.add_argument("--budget", type=float, default=None,
                    help="seconds per channel; no window starts past it")
    ap.add_argument("--neck-time-limit", type=float, default=None,
                    help="seconds per neck window (default --time-limit)")
    ap.add_argument("--channels", nargs="*", default=None)
    ap.add_argument("--flow", action="store_true",
                    help="hold each window district connected by a flow as well as the cuts")
    ap.add_argument("--keep-support", action="store_true",
                    help="arm 1: a ZCTA only to a district whose plan holds its unit")
    ap.add_argument("--open-units", nargs="*", default=(),
                    help="units whose ZCTAs any window district may take, even with "
                         "--keep-support: an arm-2 split, one more allowed per unit; a neck "
                         "inside one first tries the district's own ZCTAs there (#122)")
    ap.add_argument("--jobs", type=int, default=1,
                    help="processes (#123): each channel in its own, its windows raced, at most "
                         "this many solves at once; 1 is the sequential loop")
    ap.add_argument("--maps", action="store_true")
    ap.add_argument("--diag-final-delta", type=float, default=None,
                    help="diagnostic only: windows and audit at this final band, not the "
                         "scenario's; the folder is never a deliverable")
    a = ap.parse_args(argv)
    output.check_out(a.out)
    commit = _commit()
    params = {k: v for k, v in vars(a).items() if k not in ("run_dir", "out")}
    with open(os.path.join(a.run_dir, "run.json")) as fh:
        spec_path = json.load(fh)["spec"]
    params["plan"] = run.spec_plan(spec_path)
    diag = audit.diagnostic(a.run_dir)      # a child of a diagnostic folder is diagnostic (#121)
    if diag is not None:
        diag = {"band": diag["band"], "label": f"child of the diagnostic folder {os.path.abspath(a.run_dir)}"}
    if a.diag_final_delta is not None:
        diag = {"band": a.diag_final_delta, "label": f"diagnostic band ±{100 * a.diag_final_delta:g}%"}
    flag = {} if diag is None else {"diagnostic": True, "diagnostic_band": diag["band"],
                                    "diagnostic_label": diag["label"]}
    run.write_manifest(a.out, "contig_repair", spec_path, a.extract, params, a.plans_file, a.run_dir,
                       **flag)
    s, ref, ext, polygon, inst, plans, reports, owners, src = load(a.run_dir, a.extract, a.plans,
                                                                       a.plans_file)
    scenario_bands = {c: (*ch.final_band, ch.spec.final_delta) for c, ch in inst.channels.items()}
    if a.diag_final_delta is not None:      # a diagnostic band (#121, OD1): never the scenario's
        for ch in inst.channels.values():
            ch.final_band = (ch.tau * (1 - a.diag_final_delta), ch.tau * (1 + a.diag_final_delta))
        a.label = f"DIAGNOSTIC final band ±{a.diag_final_delta:g}" + (f", {a.label}" if a.label else "")
    elif diag is not None:
        a.label = "DIAGNOSTIC (" + diag["label"] + ")" + (f", {a.label}" if a.label else "")
    border, ng = draw.border_km(polygon), audit.NeckGraph(polygon)
    os.makedirs(a.out, exist_ok=True)
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    p = {z: (float(x) / 1000.0, float(y) / 1000.0) for z, x, y in zip(rows.index, rows["x"], rows["y"])}
    state = dict(zip(rows.index, rows["state"]))
    with open(os.path.join(a.run_dir, "contig.json")) as fh:
        doc = json.load(fh)
    connectors = set(geo.approved_connectors(geo.read_connectors()))
    repaired = {}
    if a.jobs > 1:
        repaired = repair_parallel(inst, plans, owners, p, state,
                                   [c for c in plans if a.channels is None or c in a.channels],
                                   a.jobs, border, ng, h0=a.h0, max_zctas=a.max_zctas,
                                   time_limit=a.time_limit, flow=a.flow,
                                   keep_support=a.keep_support, neck_time_limit=a.neck_time_limit,
                                   budget=a.budget, open_units=a.open_units)
    drawings = {}
    for c, plan in plans.items():
        owner = owners[c]
        attempts = []
        before_km = draw.cut_border(owner, inst.units.zip_adj, border)
        if c in repaired:
            owner, attempts = repaired[c]
        elif a.channels is None or c in a.channels:
            owner, attempts = repair_channel(inst, plan, owner, p, state, a.h0, a.max_zctas,
                                             a.time_limit, flow=a.flow,
                                             keep_support=a.keep_support, border=border, ng=ng,
                                             neck_time_limit=a.neck_time_limit, budget=a.budget,
                                             open_units=a.open_units)
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
            entry["repair_band"] = {"delta": a.diag_final_delta or inst.channels[c].spec.final_delta,
                                   "worst_dev": map_figures(inst, c, owner, state)["worst_dev"]}
        entry.update(run.drawn_stats(inst, plan, d, connectors, not left, border))
        entry["cut_border_km_before_repair"] = before_km
        entry["necks_left"] = [f"{j} {min(side)} ({len(side)} ZCTAs, {nk.width_km:.2f} km)"
                               for j, side, nk in necks(owner, inst.channels[c].m, ng)]
    report, m1 = run.write_folder(a.out, s, inst, ext, ref, polygon, plans, reports, drawings,
                                  f"{s.name} (contig {doc['arm']} + window repair{', ' + a.label if a.label else ''})",
                                  f"tools/exp/contig ({doc['arm']} + repair)", src.get("source", ""),
                                  a.maps, diag, scenario_bands if a.diag_final_delta is not None else None)
    doc.update({"arm": doc["arm"] + "+repair", "repair_of": os.path.abspath(a.run_dir),
                "repair": {"h0": a.h0, "max_zctas": a.max_zctas, "time_limit": a.time_limit,
                           "neck_time_limit": a.neck_time_limit, "budget": a.budget,
                           "plans_file": a.plans_file, "label": a.label,
                           "flow": a.flow, "keep_support": a.keep_support,
                           "open_units": list(a.open_units),
                           "commit": commit},
                "m1": report["m1"]})
    with open(os.path.join(a.out, "contig.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    run.write_manifest(a.out, "contig_repair", spec_path, a.extract, params, status="done",
                       stop_reason="diagnostic" if diag is not None else "repaired",
                       audit=report["verdict"], m1=m1.status)
    print(f"{s.name} (repair of {a.run_dir}): M1 {m1.status} ({m1.summary}); audit "
          f"{report['verdict']}")
    return 0 if m1.status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
elif __name__ == WORKER:
    _serve(*WORKER_ARGS)     # noqa: F821 (set by `run.spawn`)
