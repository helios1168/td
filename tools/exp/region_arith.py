"""region_arith.py -- regional sealing arithmetic for the main-map and IFA grids (arithmetic only,
no feasibility certificate: no MILP over ZIPs, no run).

    "$TD_PY" tools/exp/region_arith.py [--out DIR] [--extract PATH] [--search]

Sealing draws each region on its own and merges them (`tools/exp/contig/merge.py`).  Every
district then lies in one region, so each region needs its own K_r with $_r / K_r inside the
channel's dollar window, and the grid's K_c is a sum of K_r.  This tool is the regional analogue
of `notes/2026-10-12_main-map-joint-wifi-grid-research.md` §10 (P0, one region, reproduces it) and
of `tools/exp/split_floor.py`, whose `components`, `forced_splits` and `parts_floor` it reuses.

Inputs: the dollar extract's (state, fine channel) cells over M1's vertex set
(`overnight.state_cells`), each structure's channel footprints from its base spec
(`overnight.unit_mass`), the state graph from `geo.polygon_graph` (polygon edges plus the
approved connectors, an edge when two ZCTAs of two states touch), the dollar windows from
`tools/looks/score.py`, the final δ from `overnight.fit_delta`, the grid from `overnight.POINTS`.
IFA is one channel over all 49 units, $ from the extract's ifa cells, window `merge.BAND_M`.

Partitions: P0 unsealed (one region), P1 IFA's six regions (the sources of the K48-K54 merges,
`runs/exp/contig/ifa/kgrid/K*/run.json` "merged_from"), P2 the nine Census divisions, P3 the four
Census regions (`tools/looks/study.py` DIVISIONS and REGIONS).

Per (partition, channel, region), with the channel's footprint states in the region:
- feasible K: k with τ = $_r / k strictly inside the window (`fit_delta` is not None; the WIFI
  window is $850-1,150M, up to the $1.6B whole-state cap for a channel with no split list, as
  `overnight.plan_point` has it);
- forced splits, two ways: against the final-δ band τ(1 + δ) the chain enforces (`forced_band`),
  and against the window top alone (`forced_top`, a bound for any method); cuts = pieces - 1;
- parts floor: `split_floor.parts_floor` over the region's connected components against δ
  (`ok_band`), and the $-only allocation of districts to components (`ok_win`).

Three tracks: `band` (window-feasible K that pass `ok_band`, forced against the band), `win`
(window-feasible K that pass `ok_win`, forced against the window top: the same for every partition,
so sealing never adds to it), and `allow` (only where a WIFI channel has a split list, so its plan
window tops at $1,150M: `win` with that channel's top at the $1.6B cap, a relaxation that holds only
for districts of whole states, `score.dollar_gate`).

Per (partition, structure, total): the channel K sums reachable from regional passing K, the
minimum forced splits over reachable combos, the best headroom (§10's 2 min(avg - L, U - avg) /
(U - L), minimum over channels with a free K).  The combos are the P0 window-feasible K per channel
(WH >= 8), because a sealed channel's K lies in the same window.  A grid point passes when every
channel's K is a sum of passing regional K.

Whole-state groups: connected sets of whole states in the window, by size cap 4, 6 and none; the
small states (alone under the window floor) must be covered by disjoint groups (exact cover);
carving jobs for the states that must (over the window top) or may (at twice its floor or more)
split; the attach sets (connected whole neighbour states, at most `ATTACH_MAX`, adjacent to the
state) and the states no group and no attach set can take (rule C orphans: `orphans` and
`orphans_usable` attach to the must/may states only, `orphans_any` lets every neighbour state
split).

`--search` (only that, no grouping): per structure and channel footprint (a fixed WIFI channel is
not searched), A, every coarsening of the Census divisions into connected regions whose regional
window-feasible K sum to a grid point's K, ranked by regions, headroom, largest region; B, the
Northeast corridor sealed (`CORRIDOR_VARIANTS`) with the rest one unsealed region; C, IFA under P1
at K48-K54 with the per-region K combos.  Writes `7_partition_search.md`, `7b_ifa_combos.md`.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import itertools
import json
import math
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import geo                                              # noqa: E402
from td import spec as tdspec                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


split_floor = _load("exp_split_floor", os.path.join(HERE, "split_floor.py"))
overnight = _load("contig_overnight", os.path.join(HERE, "contig", "overnight.py"))
study = _load("looks_study", os.path.join(ROOT, "tools", "looks", "study.py"))
merge = _load("contig_merge", os.path.join(HERE, "contig", "merge.py"))
score = overnight.score

OUT_DEFAULT = "/tmp/td-region-arith"
MAIN_TOTALS = range(48, 53)
IFA_TOTALS = range(48, 55)
WH_MIN_K = 8                    # the locked grid's setting: WH K >= 8 where WH is a channel
ATTACH_MAX = 3                  # whole neighbour states attached to a split state's piece
CAPS = (4, 6, None)             # whole-state group size caps; None is no cap
EPS = 1e-9

# IFA's six regions: the "merged_from" keys of runs/exp/contig/ifa/kgrid/K48..K54/run.json (and
# ifa_conus_v2); scenarios/regions/ifa/*_merge.toml name only each region's split list.
IFA_REGIONS = {
    "NewEngland": "CT MA ME NH RI VT",
    "MidAtlantic": "NJ NY PA",
    "SouthAtlantic": "DC DE FL GA MD NC SC VA WV",
    "SouthCentral": "AL AR KY LA MS OK TN TX",
    "Midwest": "CO IA IL IN KS MI MN MO ND NE OH SD WI",
    "West": "AZ CA ID MT NM NV OR UT WA WY",
}
# §10 of the research note, for the P0 check: feasible K per channel and the locked grid's headroom
SECTION10_K = {
    "ne_plains": {"national": (12, 16), "WH": (9, 11), "FI": (18, 24), "WIFI": (3, 3)},
    "west8": {"national": (12, 16), "WH": (10, 12), "FI": (19, 25), "WIFI": (1, 1)},
    "nw49": {"national": (13, 17), "WIFI": (28, 36)},
    "nw34": {"national": (12, 16), "WIFI": (28, 37)},
    "w1": {"WIFI": (43, 57)},
}
SECTION10_HEAD = {
    "ne-48-bal": 0.86, "ne-50-bal": 0.56, "ne-50-filight": 0.26, "ne-52-bal": 0.29,
    "ne-52-filight": 0.26, "w8-48-bal": 0.85, "w8-50-bal": 0.60, "w8-50-filight": 0.28,
    "w8-52-bal": 0.31, "w8-52-filight": 0.28, "nw49-48": 0.67, "nw49-50": 0.44,
    "nw49-52": 0.14, "nw34-48": 0.61, "nw34-50": 0.43, "nw34-52": 0.26, "w1-48": 0.87,
    "w1-50": 0.85, "w1-52": 0.60}


# ------------------------------------------------------------------------------ inputs
def state_graph() -> dict:
    """{state: set of states} from the polygon graph's cross-state edges (connectors included)."""
    g = geo.polygon_graph()
    st = g["state"]
    adj = collections.defaultdict(set)
    for a, b in g["edges"]:
        if st[a] != st[b]:
            adj[st[a]].add(st[b])
            adj[st[b]].add(st[a])
    return {s: set(v) for s, v in adj.items()}


def partitions() -> dict:
    """{partition: {region: [states]}}: P0 one region, P1 IFA, P2 divisions, P3 Census regions."""
    p1 = {r: s.split() for r, s in IFA_REGIONS.items()}
    p2 = {d: s.split() for d, s in study.DIVISIONS.items()}
    p3 = {r: [s for d in ds for s in study.DIVISIONS[d].split()] for r, ds in study.REGIONS.items()}
    allstates = sorted(s for ss in p1.values() for s in ss)
    for name, p in (("P1", p1), ("P2", p2), ("P3", p3)):
        got = sorted(s for ss in p.values() for s in ss)
        if got != allstates:
            raise ValueError(f"{name} does not partition the 49 units: {set(got) ^ set(allstates)}")
    return {"P0": {"ALL": allstates}, "P1": p1, "P2": p2, "P3": p3}


def structures(cells: dict) -> dict:
    """{structure: {"channels": {channel: {state: $M}}, "whole": {channel: bool}, "fixed":
    {channel}, "rule": base|rule}} for the five main structures and IFA.  `whole`: a WIFI channel
    with no split list (overnight.plan_point), so its window tops at the whole-state cap."""
    out = {}
    for name, (path, rule) in overnight.STRUCTURES.items():
        sp = tdspec.parse(tomllib.load(open(os.path.join(ROOT, path), "rb")))
        mass = overnight.unit_mass(sp, cells)
        whole = {}
        for c in mass:
            free = [u for u, m in sp.channels[c].modes.items() if m == "free"]
            whole[c] = rule == "base" and not free and c in score.WHOLE_STATE_CAP
        fixed = {c for c in mass if c == "WIFI" and rule == "base"}
        out[name] = {"channels": mass, "whole": whole, "fixed": fixed, "rule": rule}
    ifa = {s: cells.get((s, "ifa"), 0.0) for s in sorted({s for s, _ in cells})}
    out["ifa"] = {"channels": {"IFA": ifa}, "whole": {"IFA": False}, "fixed": set(), "rule": "ifa"}
    return out


def window_of(channel: str, whole: bool) -> tuple:
    """($M lo, hi) of a channel: score.WINDOWS, WIFI up to the whole-state cap when `whole`; IFA's
    is merge.BAND_M."""
    if channel == "IFA":
        return tuple(merge.BAND_M)
    lo, hi = score.WINDOWS[channel]
    if whole and channel in score.WHOLE_STATE_CAP:
        hi = score.WHOLE_STATE_CAP[channel]
    return lo / 1e6, hi / 1e6


# ------------------------------------------------------------------------------ one region
def region_analysis(M: dict, adj: dict, lo: float, hi: float) -> dict:
    """Per k the window fit, forced splits and parts floor of one region's channel footprint
    `M` {state: $M}: {"usd", "n_states", "components", "k": {k: row}}.  A row: tau, delta (the
    final δ of `fit_delta`), forced_band {state: cuts}, forced_top {state: cuts}, parts_floor,
    ok_band, ok_win."""
    total = math.fsum(M.values())
    local = {s: adj.get(s, set()) & set(M) for s in M}
    comps = sorted(split_floor.components(M, local), key=lambda c: -sum(M[u] for u in c))
    masses = [math.fsum(M[u] for u in c) for c in comps]
    top = {v: math.ceil(m / hi) - 1 for v, m in M.items() if m > hi + EPS}
    rows = {}
    for k in range(1, int(total / lo) + 2):
        tau = total / k
        d = overnight.fit_delta(tau, k, lo, hi)
        if d is None:
            continue
        band = split_floor.forced_splits(M, tau, d)
        pf, alloc = split_floor.parts_floor(masses, k)
        rows[k] = {"tau": tau, "delta": d, "forced_band": band, "forced_top": top,
                   "parts_floor": pf, "allocation": alloc, "ok_band": pf <= d + 1e-12,
                   "ok_win": parts_in_window(masses, k, lo, hi)}
    return {"usd": total, "n_states": len(M), "components": [sorted(c) for c in comps],
            "k": rows}


def parts_in_window(masses: list, k: int, lo: float, hi: float) -> bool:
    """Whether the components take k_i >= 1 districts, sum k, each $_i / k_i inside [lo, hi]."""
    reach = {0}
    for m in masses:
        ks = [j for j in range(1, k + 1) if lo - EPS <= m / j <= hi + EPS]
        reach = {s + j for s in reach for j in ks if s + j <= k}
    return k in reach


TRACKS = ("band", "win")
# band: the chain's rule, forced splits against the final-δ band τ(1 + δ) and the parts floor
# against δ; win: the dollar window alone (forced = $ over the window top, parts by dollars only),
# the bound any method meets.  allow (only where a WIFI channel has a split list, so its plan window
# tops at $1,150M): win with that channel's top raised to the $1.6B whole-state cap, a relaxation
# that holds only for districts of whole states (score.dollar_gate).


def pass_k(row: dict, track: str = "band") -> dict:
    """{k: row} of the region's window-feasible K that pass the track's parts check."""
    return {k: r for k, r in row["k"].items() if r["ok_band" if track == "band" else "ok_win"]}


def forced_of(r: dict, track: str) -> dict:
    return r["forced_band" if track == "band" else "forced_top"]


# ------------------------------------------------------------------------------ K sums
def sumset(regions: list, track: str = "band") -> dict:
    """{K: (forced states, cuts, allocation)} minimising (forced states, cuts), K a sum of the
    regions' passing k; {} when a region has none.  `regions` is a list of `pass_k` dicts."""
    best = {0: (0, 0, ())}
    for rk in regions:
        nxt = {}
        for s, (n, c, alloc) in best.items():
            for k, r in rk.items():
                f = forced_of(r, track)
                cand = (n + len(f), c + sum(f.values()), alloc + (k,))
                if s + k not in nxt or cand[:2] < nxt[s + k][:2]:
                    nxt[s + k] = cand
        best = nxt
    return {} if not regions else {k: v for k, v in best.items() if k > 0}


def headroom(avg: float, lo: float, hi: float) -> float:
    """§10's headroom: 2 min(avg - L, U - avg) / (U - L)."""
    return 2 * min(avg - lo, hi - avg) / (hi - lo)


def channel_regions(M: dict, region_states: dict, adj: dict, lo: float, hi: float) -> dict:
    """{region: region_analysis} for the regions that hold a state of the footprint `M`."""
    out = {}
    for r, ss in region_states.items():
        sub = {s: M[s] for s in ss if s in M}
        if sub:
            out[r] = region_analysis(sub, adj, lo, hi)
    return out


def reach_of(regions: dict, track: str = "band") -> dict:
    """{K: (forced, cuts, allocation)} a channel's reachable K under a partition, {} when a region
    has no passing k."""
    return sumset([pass_k(v, track) for v in regions.values()], track)


def combos(structure: dict, f0: dict, total: int) -> list:
    """The K per channel (dict) whose sum is `total`, from each channel's P0 window-feasible K
    (WH >= WH_MIN_K; a fixed channel keeps its feasible K)."""
    names = sorted(f0)
    out = []
    for combo in itertools.product(*[f0[c] for c in names]):
        if sum(combo) == total:
            out.append(dict(zip(names, combo)))
    return out


def total_rows(name: str, st: dict, parts: dict, adj: dict, totals) -> dict:
    """The §10 and sealing tables of one structure: P0's window-feasible K, and for each
    partition and track the channel reach, per total the combos, reachable combos, minimum
    forced splits and best headroom."""
    wins = {c: window_of(c, st["whole"][c]) for c in st["channels"]}
    allow = [c for c in st["channels"] if c in score.WHOLE_STATE_CAP and not st["whole"][c]]
    tracks = TRACKS + (("allow",) if allow else ())
    usd = {c: math.fsum(M.values()) for c, M in st["channels"].items()}
    f0 = {}
    for c, M in st["channels"].items():
        ks = sorted(region_analysis(M, adj, *wins[c])["k"])
        f0[c] = [k for k in ks if k >= WH_MIN_K] if c == "WH" else ks
    out = {"f0": f0, "windows": wins, "tracks": tracks, "allow": allow, "partitions": {}}

    def head(x):
        hs = [headroom(usd[c] / k, *wins[c]) for c, k in x.items() if c not in st["fixed"]]
        return min(hs) if hs else 1.0
    for pn, region_states in parts.items():
        regs = {c: channel_regions(M, region_states, adj, *wins[c]) for c, M in st["channels"].items()}
        regs_allow = {c: channel_regions(st["channels"][c], region_states, adj, *window_of(c, True))
                      if c in allow else regs[c] for c in regs}
        p = {"regions": regs, "regions_allow": regs_allow, "tracks": {}}
        for tk in tracks:
            rg = regs_allow if tk == "allow" else regs
            reach = {c: reach_of(rg[c], tk) for c in rg}
            blockers = {c: [r for r, v in rg[c].items() if not pass_k(v, tk)] for c in rg}
            t = {"reach": reach, "blockers": blockers, "totals": {}}
            for tot in totals:
                cs = combos(st, f0, tot)
                ok = [x for x in cs if all(x[c] in reach[c] for c in x)]
                rec = {"combos": len(cs), "reachable": len(ok)}
                if ok:
                    def forced(x):
                        return (sum(reach[c][x[c]][0] for c in x), sum(reach[c][x[c]][1] for c in x))
                    rec["min_forced"] = min(ok, key=lambda x: (forced(x), -head(x)))
                    rec["min_forced_n"] = forced(rec["min_forced"])
                    rec["best_head"] = max(ok, key=lambda x: (head(x), -forced(x)[0]))
                    rec["best_head_value"] = head(rec["best_head"])
                    rec["best_head_forced"] = forced(rec["best_head"])
                t["totals"][tot] = rec
            p["tracks"][tk] = t
        out["partitions"][pn] = p
    return out


def point_rows(name: str, st: dict, tr: dict, points: list) -> list:
    """For each grid point of the structure: per partition and track whether every channel's K
    is reachable, the forced splits at that K, and the headroom."""
    rows = []
    for pt in points:
        k = {("IFA" if name == "ifa" else c): v for c, v in pt["k"].items()}
        rec = {"id": pt["id"], "k": k, "partitions": {}}
        hs = [headroom(math.fsum(st["channels"][c].values()) / v, *tr["windows"][c])
              for c, v in k.items() if c not in st["fixed"]]
        rec["headroom"] = min(hs) if hs else None
        for pn, p in tr["partitions"].items():
            rec["partitions"][pn] = {}
            for tk, t in p["tracks"].items():
                miss = {c: v for c, v in k.items() if v not in t["reach"][c]}
                rec["partitions"][pn][tk] = {
                    "pass": not miss, "missing": miss,
                    "forced": None if miss else (sum(t["reach"][c][v][0] for c, v in k.items()),
                                                 sum(t["reach"][c][v][1] for c, v in k.items()))}
        rows.append(rec)
    return rows


# ------------------------------------------------------------------------------ whole-state groups
class Region:
    """One channel's footprint inside one region: states, $M, adjacency, bit indices."""

    def __init__(self, M: dict, adj: dict, lo: float, hi: float):
        self.names = sorted(M)
        self.idx = {s: i for i, s in enumerate(self.names)}
        self.w = [M[s] for s in self.names]
        self.lo, self.hi = lo, hi
        self.nbr = [0] * len(self.names)
        for s in self.names:
            for t in adj.get(s, ()):
                if t in self.idx:
                    self.nbr[self.idx[s]] |= 1 << self.idx[t]

    def connected_sets(self, hi: float, max_size: int | None = None, skip: int = 0) -> list:
        """[(mask, $, size)] of the connected state sets with $ <= hi (and size <= max_size)
        that avoid the states in bitmask `skip` (ESU enumeration; $ only grows, so it prunes)."""
        out = []
        w, nbr = self.w, self.nbr

        def extend(mask, tot, size, closed, ext, v):
            out.append((mask, tot, size))
            if max_size and size >= max_size:
                return
            while ext:
                low = ext & -ext
                x = low.bit_length() - 1
                ext ^= low
                t2 = tot + w[x]
                if t2 > hi + EPS:
                    continue
                new = ext | (nbr[x] & ~closed & ~((1 << (v + 1)) - 1) & ~skip)
                extend(mask | low, t2, size + 1, closed | nbr[x] | low, new, v)
        for v in range(len(self.names)):
            if (skip >> v) & 1 or w[v] > hi + EPS:
                continue
            extend(1 << v, w[v], 1, nbr[v] | (1 << v), nbr[v] & ~((1 << (v + 1)) - 1) & ~skip, v)
        return out

    def groups(self) -> list:
        """The window groups: connected sets with $ in [lo, hi]."""
        return [g for g in self.connected_sets(self.hi) if g[1] >= self.lo - EPS]

    def states(self, mask: int) -> list:
        return [s for i, s in enumerate(self.names) if (mask >> i) & 1]


def cover(groups: list, need: int) -> list | None:
    """Disjoint groups covering every state of bitmask `need` (exact cover of those states; other
    states may be in a group or out), or None.  Fail-first search with failures memoised on the
    used mask."""
    by_state = collections.defaultdict(list)
    for g in groups:
        m = g[0] & need
        while m:
            low = m & -m
            by_state[low].append(g)
            m ^= low
    dead = set()

    def go(used):
        todo = need & ~used
        if not todo:
            return []
        if used in dead:
            return None
        best, best_opts = None, None
        m = todo
        while m:
            low = m & -m
            m ^= low
            opts = [g for g in by_state.get(low, ()) if not g[0] & used]
            if best_opts is None or len(opts) < len(best_opts):
                best, best_opts = low, opts
                if not opts:
                    break
        for g in best_opts:
            rest = go(used | g[0])
            if rest is not None:
                return [g] + rest
        dead.add(used)
        return None
    return go(0)


def conflict_core(groups: list, need: int) -> int:
    """A minimal (deletion filter) subset of the `need` states that no disjoint groups cover."""
    core = need
    m = need
    while m:
        low = m & -m
        m ^= low
        if cover(groups, core & ~low) is None:
            core &= ~low
    return core


def grouping(reg: Region) -> dict:
    """Library counts, per-state membership, the small-state cover under each cap, carving jobs,
    attach sets and rule C orphans of one region."""
    n = len(reg.names)
    allg = reg.groups()
    small = sum(1 << i for i in range(n) if reg.w[i] < reg.lo - EPS)
    counts, member, cov = {}, {}, {}
    for cap in CAPS:
        gs = [g for g in allg if cap is None or g[2] <= cap]
        key = "none" if cap is None else str(cap)
        counts[key] = len(gs)
        mem = collections.Counter()
        for g in gs:
            for s in reg.states(g[0]):
                mem[s] += 1
        member[key] = {s: mem.get(s, 0) for s in reg.names}
        sol = cover(gs, small)
        entry = {"ok": sol is not None, "groups": [reg.states(g[0]) for g in sol or []]}
        if sol is None:
            entry["zero_group"] = [s for s in reg.states(small) if not mem.get(s)]
            entry["core"] = reg.states(conflict_core(gs, small))
        cov[key] = entry
    attach_sets = reg.connected_sets(reg.hi, ATTACH_MAX)
    jobs, orphan_loose, orphan_use, orphan_any = [], [], [], []
    taken_loose, taken_use, taken_any = set(), set(), set()
    for i, s in enumerate(reg.names):
        usd = reg.w[i]
        kmin, kmax = math.ceil(usd / reg.hi - EPS), math.floor(usd / reg.lo + EPS)
        must, may = usd > reg.hi + EPS, kmax >= 2
        sets = [a for a in attach_sets if not (a[0] >> i) & 1 and
                any(reg.nbr[i] >> j & 1 for j in range(n) if (a[0] >> j) & 1)]
        loose = [a for a in sets if a[1] <= reg.hi + EPS]
        use = [a for a in loose if a[1] < reg.hi - EPS and a[1] + usd >= reg.lo - EPS]
        for a in use:               # any state may give a piece, however small its $
            taken_any.update(reg.states(a[0]))
        if not (must or may):
            continue
        for a in loose:
            taken_loose.update(reg.states(a[0]))
        for a in use:
            taken_use.update(reg.states(a[0]))
        jobs.append({"state": s, "usd": usd, "kind": "must" if must else "may",
                     "k": [k for k in range(max(kmin, 2), kmax + 1)],
                     "alone_ok": kmin <= kmax, "attach": len(loose), "attach_usable": len(use),
                     "attach_max_size": ATTACH_MAX})
    zero6 = [s for s in reg.names if not member["6"][s]]
    by_job = {j["state"]: j for j in jobs}
    for s in zero6:
        j = by_job.get(s)
        own = j is not None and (j["alone_ok"] or j["attach"] > 0)
        own_use = j is not None and (j["alone_ok"] or j["attach_usable"] > 0)
        if s not in taken_loose and not own:
            orphan_loose.append(s)
        if s not in taken_use and not own_use:
            orphan_use.append(s)
        if s not in taken_any and not own_use:
            orphan_any.append(s)
    return {"states": reg.names, "usd": {s: reg.w[i] for i, s in enumerate(reg.names)},
            "small": reg.states(small), "counts": counts, "member": member, "cover": cov,
            "jobs": jobs, "orphans": orphan_loose, "orphans_usable": orphan_use,
            "orphans_any": orphan_any}


def grouping_rows(st: dict, parts: dict, adj: dict) -> list:
    """One record per (partition, channel, region) of a structure."""
    out = []
    for c, M in st["channels"].items():
        lo, hi = window_of(c, st["whole"][c])
        for pn, region_states in parts.items():
            for r, ss in region_states.items():
                sub = {s: M[s] for s in ss if s in M}
                if sub:
                    g = grouping(Region(sub, adj, lo, hi))
                    g.update({"partition": pn, "channel": c, "region": r, "window": [lo, hi]})
                    out.append(g)
    return out


# ------------------------------------------------------------------------------ markdown
def fmt_ks(ks) -> str:
    """A K set as ranges: 12-16, 18, 20-21."""
    ks = sorted(ks)
    if not ks:
        return "none"
    out, a = [], ks[0]
    for x, y in zip(ks, ks[1:] + [None]):
        if y != x + 1:
            out.append(str(a) if a == x else f"{a}-{x}")
            a = y
    return ", ".join(out)


def md_regions(name: str, st: dict, tr: dict) -> list:
    lines = []
    for c in st["channels"]:
        lo, hi = tr["windows"][c]
        lines += [f"### {name} / {c} (window ${lo:,.1f}-{hi:,.1f}M)", "",
                  "| partition | region | $M | states | comps | feasible K (window) | K passing, band "
                  "| K passing, win | K passing, allow | forced (band) n/cuts per passing K | forced "
                  "(window top) states (pieces - 1) | parts floor δ at band-passing K |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for pn, p in tr["partitions"].items():
            for r, v in p["regions"][c].items():
                ks, ok, okw = sorted(v["k"]), sorted(pass_k(v)), sorted(pass_k(v, "win"))
                oka = (fmt_ks(pass_k(p["regions_allow"][c][r], "allow"))
                       if c in tr["allow"] else "—")
                fb = " ".join(f"{k}:{len(v['k'][k]['forced_band'])}/{sum(v['k'][k]['forced_band'].values())}"
                              for k in ok) or "—"
                top = " ".join(f"{s}({n})" for s, n in sorted(
                    next(iter(v["k"].values()))["forced_top"].items())) if v["k"] else "—"
                pf = " ".join(f"{k}:{v['k'][k]['parts_floor'] * 100:.1f}%" for k in ok
                              if v["k"][k]["parts_floor"] > 0) or "—"
                lines.append(f"| {pn} | {r} | {v['usd']:,.0f} | {v['n_states']} | {len(v['components'])} "
                             f"| {fmt_ks(ks)} | {fmt_ks(ok)} | {fmt_ks(okw)} | {oka} | {fb} | {top or '—'} | {pf} |")
        lines.append("")
    return lines


def md_totals(name: str, st: dict, tr: dict, totals) -> list:
    lines = [f"### {name}: P0 window-feasible K " +
             ", ".join(f"{c} {fmt_ks(k)}" for c, k in tr["f0"].items()), ""]
    for tk in tr["tracks"]:
        lines += [f"**{name}, track {tk}**", "",
                  "| partition | channel reach (sum of regional passing K) | blocked by (region without a "
                  "passing K) |", "|---|---|---|"]
        for pn, p in tr["partitions"].items():
            t = p["tracks"][tk]
            reach = "; ".join(f"{c} {fmt_ks(t['reach'][c])}" for c in t["reach"])
            blk = "; ".join(f"{c}: {', '.join(b)}" for c, b in t["blockers"].items() if b) or "—"
            lines.append(f"| {pn} | {reach} | {blk} |")
        lines += ["", "| partition | total | combos | reachable | min forced (n/cuts) at | best headroom "
                  "(forced n/cuts) | extra forced vs P0 (min) |", "|---|---|---|---|---|---|---|"]
        for pn, p in tr["partitions"].items():
            for t_ in totals:
                r = p["tracks"][tk]["totals"][t_]
                base = tr["partitions"]["P0"]["tracks"][tk]["totals"][t_]
                if not r["reachable"]:
                    lines.append(f"| {pn} | {t_} | {r['combos']} | 0 | — | — | — |")
                    continue
                mf = " ".join(f"{c}{k}" for c, k in r["min_forced"].items())
                bh = " ".join(f"{c}{k}" for c, k in r["best_head"].items())
                extra = ("n/a (P0 unreachable)" if not base["reachable"]
                         else f"{r['min_forced_n'][0] - base['min_forced_n'][0]:+d} / "
                              f"{r['min_forced_n'][1] - base['min_forced_n'][1]:+d} cuts")
                lines.append(f"| {pn} | {t_} | {r['combos']} | {r['reachable']} | {r['min_forced_n'][0]}/"
                             f"{r['min_forced_n'][1]} ({mf}) | {r['best_head_value']:.2f} ({bh}; "
                             f"{r['best_head_forced'][0]}/{r['best_head_forced'][1]}) | {extra} |")
        lines.append("")
    return lines


def md_points(name: str, rows: list, parts) -> list:
    lines = []
    for tk in rows[0]["partitions"]["P0"]:
        lines += [f"### {name} grid points, track {tk}", "",
                  "| point | K | headroom | " + " | ".join(f"{p} (forced n/cuts; extra vs P0)" for p in parts)
                  + " |", "|---|---|---|" + "---|" * len(parts)]
        for r in rows:
            base = r["partitions"]["P0"][tk]["forced"]
            cells = []
            for p in parts:
                v = r["partitions"][p][tk]
                if v["pass"]:
                    extra = "" if base is None else f"; {v['forced'][0] - base[0]:+d}"
                    cells.append(f"pass ({v['forced'][0]}/{v['forced'][1]}{extra})")
                else:
                    cells.append("FAIL " + ",".join(f"{c}{k}" for c, k in v["missing"].items()))
            h = "—" if r["headroom"] is None else f"{r['headroom']:.2f}"
            lines.append(f"| {r['id']} | {' '.join(f'{c}{k}' for c, k in r['k'].items())} | {h} | "
                         + " | ".join(cells) + " |")
        lines.append("")
    return lines


def md_grouping(name: str, recs: list) -> list:
    lines = [f"### {name}: whole-state groups, small-state cover, carving", "",
             "| partition | channel | region | window | small states | groups cap4 / cap6 / none "
             "| cover cap4 | cover cap6 | cap-4 conflict (core) | cap-6 conflict (core) | "
             "zero-group states (cap 6) | orphans (loose / usable / any state may split) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in recs:
        c4, c6 = g["cover"]["4"], g["cover"]["6"]
        core = ", ".join(c4.get("core", [])) if not c4["ok"] else "—"
        if not c4["ok"] and c6["ok"]:
            core += " (cap 6 ok)"
        core6 = ", ".join(c6.get("core", [])) if not c6["ok"] else "—"
        zero = ", ".join(s for s in g["states"] if not g["member"]["6"][s]) or "—"
        lines.append(
            f"| {g['partition']} | {g['channel']} | {g['region']} | {g['window'][0]:,.0f}-{g['window'][1]:,.1f} "
            f"| {len(g['small'])} | {g['counts']['4']} / {g['counts']['6']} / {g['counts']['none']} "
            f"| {'ok' if c4['ok'] else 'NO'} | {'ok' if c6['ok'] else 'NO'} | {core} | {core6} | {zero} "
            f"| {','.join(g['orphans']) or '—'} / {','.join(g['orphans_usable']) or '—'} / "
            f"{','.join(g['orphans_any']) or '—'} |")
    return lines + [""]


def md_jobs(name: str, recs: list) -> list:
    lines = [f"### {name}: carving jobs (K does not enter: the window is fixed)", "",
             "| partition | channel | region | state σ | $M | kind | k (pieces) | alone-ok | "
             "attach sets (|A|≤3, $A≤U, adjacent) | usable |", "|---|---|---|---|---|---|---|---|---|---|"]
    for g in recs:
        for j in g["jobs"]:
            lines.append(f"| {g['partition']} | {g['channel']} | {g['region']} | {j['state']} | "
                         f"{j['usd']:,.0f} | {j['kind']} | {fmt_ks(j['k'])} | "
                         f"{'yes' if j['alone_ok'] else 'NO'} | {j['attach']} | {j['attach_usable']} |")
    return lines + [""]


def md_membership(name: str, recs: list) -> list:
    lines = [f"### {name}: groups containing each state (cap 4 / cap 6 / none)", ""]
    for g in recs:
        m = g["member"]
        lines.append(f"- {g['partition']} {g['channel']} {g['region']}: " + " ".join(
            f"{s}={m['4'][s]}/{m['6'][s]}/{m['none'][s]}" for s in g["states"]))
    return lines + [""]


def md_summary(results: dict, parts: dict) -> list:
    """Task 4: per partition and track, the grid points that pass, the extra forced splits against
    P0, and the cap-4 conflicts."""
    lines = []
    for pn in parts:
        lines += [f"## {pn}: " + ", ".join(f"{r} ({len(s)})" for r, s in parts[pn].items()), ""]
        for tk in TRACKS + ("allow",):
            lines += [f"**{pn}, track {tk}**", "",
                      "| structure | points that pass | points that fail (channel K not a sum of passing "
                      "regional K) | extra forced vs P0, passing points (n) |", "|---|---|---|---|"]
            for name, res in results.items():
                if tk not in res["tr"]["tracks"]:
                    continue
                ok, bad, extra = [], [], []
                for r in res["points"]:
                    v, b = r["partitions"][pn][tk], r["partitions"]["P0"][tk]
                    if v["pass"]:
                        ok.append(r["id"])
                        if b["pass"]:
                            extra.append(v["forced"][0] - b["forced"][0])
                    else:
                        bad.append(r["id"] + " " + ",".join(f"{c}{k}" for c, k in v["missing"].items()))
                ex = "—" if not extra else f"{min(extra):+d} to {max(extra):+d}" + (
                    "" if len(extra) == len(ok) else f" ({len(ok) - len(extra)} not passing at P0)")
                lines.append(f"| {name} | {', '.join(ok) or 'none'} | {'; '.join(bad) or '—'} | {ex} |")
            lines.append("")
        lines += [f"**{pn}, small-state cover (whole states only)**", "",
                  "| structure | channel | region | cap 4 | cap 6 | states that cause it |", "|---|---|---|---|---|---|"]
        for name, res in results.items():
            for g in res["grouping"]:
                if g["partition"] != pn:
                    continue
                c4, c6 = g["cover"]["4"], g["cover"]["6"]
                if c4["ok"] and c6["ok"]:
                    continue
                cause = ", ".join(c4.get("core", [])) if not c4["ok"] else ", ".join(c6.get("core", []))
                zero = [s for s in c4.get("zero_group", [])]
                lines.append(f"| {name} | {g['channel']} | {g['region']} | {'ok' if c4['ok'] else 'NO'} | "
                             f"{'ok' if c6['ok'] else 'NO'} | {cause}"
                             + (f" (no group at cap 4: {', '.join(zero)})" if zero else "") + " |")
        lines.append("")
    return lines


def md_matrix(results: dict, parts: dict) -> list:
    """Per partition a region by footprint matrix: $M and the window-feasible K, the band-passing K
    in brackets when they differ; footprints that several structures share are one column."""
    cols = {}
    for name, res in results.items():
        for c, M in res["st"]["channels"].items():
            key = (c, res["tr"]["windows"][c], tuple(sorted((s, round(v, 3)) for s, v in M.items())))
            cols.setdefault(key, []).append((name, c))
    lines = []
    for pn, region_states in parts.items():
        heads = [f"{k[0]} [{','.join(n for n, _ in v)}]" for k, v in cols.items()]
        lines += [f"### {pn}: $M and feasible K (band-passing K in brackets when fewer)", "",
                  "| region | " + " | ".join(heads) + " |", "|---|" + "---|" * len(heads)]
        for r in region_states:
            cells = []
            for k, v in cols.items():
                name, c = v[0]
                reg = results[name]["tr"]["partitions"][pn]["regions"][c].get(r)
                if reg is None:
                    cells.append("·")
                    continue
                ks, ok = sorted(reg["k"]), sorted(pass_k(reg))
                cells.append(f"{reg['usd']:,.0f}: {fmt_ks(ks)}" + ("" if ks == ok else f" [{fmt_ks(ok)}]"))
            lines.append(f"| {r} | " + " | ".join(cells) + " |")
        lines.append("")
    return lines


# ------------------------------------------------------------------------------ partition search
# A: coarsenings of the Census divisions; B: a sealed Northeast corridor and one unsealed rest.
# Channels are independent footprints: a region is a set of footprint states, and a region whose
# footprint states are not one connected piece of the state graph is not a region.
CORRIDOR = {"NE": "CT ME MA NH RI VT", "NY": "NY", "NJ": "NJ", "PA": "PA",
            "DE": "DE", "MD": "MD", "DC": "DC", "VA": "VA"}     # atoms; "NE" is New England
CORRIDOR_VARIANTS = {                                          # name: blocks of atoms (rest: unsealed)
    "B1 corridor": [["NE", "NY", "NJ", "PA", "DE", "MD", "DC", "VA"]],
    "B2 NY,NJ,PA,NE / DE,MD,DC,VA": [["NE", "NY", "NJ", "PA"], ["DE", "MD", "DC", "VA"]],
    "B3 NY,NJ,NE / PA,DE,MD,DC,VA": [["NE", "NY", "NJ"], ["PA", "DE", "MD", "DC", "VA"]],
    "B4 NY,NJ,PA,NE / DE,MD,DC (VA to rest)": [["NE", "NY", "NJ", "PA"], ["DE", "MD", "DC"]],
    "B5 NY,NJ,NE / PA,DE,MD,DC (VA to rest)": [["NE", "NY", "NJ"], ["PA", "DE", "MD", "DC"]],
    "B6 NE / NY,NJ,PA / DE,MD,DC,VA": [["NE"], ["NY", "NJ", "PA"], ["DE", "MD", "DC", "VA"]],
    "B7 corridor without VA (VA to rest)": [["NE", "NY", "NJ", "PA", "DE", "MD", "DC"]],
}
DIV_CODE = {"New England": "NE", "Middle Atlantic": "MA", "East North Central": "ENC",
            "West North Central": "WNC", "South Atlantic": "SA", "East South Central": "ESC",
            "West South Central": "WSC", "Mountain": "MTN", "Pacific": "PAC"}
SEARCH_TOP = 3
SEARCH_TRACKS = ("win", "band")


def is_connected(states, adj: dict) -> bool:
    """Whether `states` is one connected piece of the state graph `adj` (edges among them only)."""
    states = set(states)
    if not states:
        return False
    seen, todo = set(), [next(iter(states))]
    while todo:
        s = todo.pop()
        if s not in seen:
            seen.add(s)
            todo.extend((adj.get(s, set()) & states) - seen)
    return seen == states


def set_partitions(items: list):
    """Every partition of `items` into blocks (lists), Bell(len) of them."""
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for part in set_partitions(rest):
        yield [[first]] + part
        for i in range(len(part)):
            yield part[:i] + [[first] + part[i]] + part[i + 1:]


def coarsenings(divs: dict, adj: dict) -> list:
    """The unions of divisions that cover the footprint, each union connected.  `divs` is
    {division: footprint states in it}; a division with no footprint state is dropped.  Returns
    [[(division, ...), ...]]: the regions as tuples of division names, one list per coarsening."""
    names = sorted(d for d, ss in divs.items() if ss)
    ok = {}

    def connected(block):
        key = frozenset(block)
        if key not in ok:
            ok[key] = is_connected([s for d in block for s in divs[d]], adj)
        return ok[key]
    out = []
    for part in set_partitions(names):
        if all(connected(b) for b in part):
            out.append([tuple(sorted(b)) for b in sorted(part, key=lambda b: sorted(b))])
    return out


def k_splits(infos: list, track: str, lo: float, hi: float) -> dict:
    """{K: (min regional headroom, (k per region))} over the ways to give each region one of its
    `track`-passing k, maximising the minimum headroom; `infos` is a list of region_analysis dicts,
    {} when a region has no passing k."""
    best = {0: (math.inf, ())}
    for info in infos:
        nxt = {}
        for s, (h, ks) in best.items():
            for k in pass_k(info, track):
                cand = (min(h, headroom(info["usd"] / k, lo, hi)), ks + (k,))
                if s + k not in nxt or cand[0] > nxt[s + k][0]:
                    nxt[s + k] = cand
        best = nxt
    return {} if not infos else {k: v for k, v in best.items() if k > 0}


def search_blocks(M: dict, blocks: list, adj: dict, lo: float, hi: float, cache: dict) -> list:
    """region_analysis of each block (a list of footprint states of `M`), cached by the state set."""
    out = []
    for b in blocks:
        key = frozenset(b)
        if key not in cache:
            cache[key] = region_analysis({s: M[s] for s in b}, adj, lo, hi)
        out.append(cache[key])
    return out


def rank_key(rec: dict) -> tuple:
    """Most regions, then the largest minimum headroom, then the fewest states in the largest region."""
    return (-len(rec["regions"]), -rec["head"], max(len(r) for r in rec["regions"]),
            [sorted(r) for r in rec["regions"]])


def search_channel(M: dict, divisions: dict, adj: dict, lo: float, hi: float) -> dict:
    """A, for one channel footprint `M` {state: $M}: every connected coarsening of the divisions,
    each with its states per region and, per track, {K: (min headroom, k per region)}.  `n` counts
    the connected coarsenings, `cache` the region analyses."""
    divs = {d: [s for s in ss if s in M] for d, ss in divisions.items()}
    cache = {}
    recs = []
    for co in coarsenings(divs, adj):
        regions = [sorted(s for d in blk for s in divs[d]) for blk in co]
        infos = search_blocks(M, regions, adj, lo, hi, cache)
        recs.append({"divisions": co, "labels": [" + ".join(b) for b in co], "regions": regions, "infos": infos,
                     "splits": {tk: k_splits(infos, tk, lo, hi) for tk in SEARCH_TRACKS}})
    return {"n": len(recs), "recs": recs}


def feasible_at(found: dict, k: int, track: str) -> list:
    """The coarsenings of `search_channel` whose regions reach K = k on the track, ranked, each a
    dict with its regions, k per region and minimum headroom."""
    out = []
    for r in found["recs"]:
        hit = r["splits"][track].get(k)
        if hit:
            out.append({**r, "head": hit[0], "ks": hit[1], "track": track})
    return sorted(out, key=rank_key)


def corridor_blocks(variant: list, footprint: set) -> list:
    """The variant's blocks as footprint-state lists (empty blocks dropped)."""
    blocks = [sorted(s for a in blk for s in CORRIDOR[a].split() if s in footprint) for blk in variant]
    return [b for b in blocks if b]


def search_corridor(M: dict, adj: dict, lo: float, hi: float, cache: dict) -> dict:
    """B, for one channel footprint: per variant the blocks, the unsealed rest, connectedness of
    each block and, per track, {K: (min headroom, k per region)}.  Duplicate restrictions of two
    variants to the footprint stay separate rows (the name tells what was meant)."""
    out = {}
    for name, variant in CORRIDOR_VARIANTS.items():
        blocks = corridor_blocks(variant, set(M))
        used = {s for b in blocks for s in b}
        rest = sorted(set(M) - used)
        regions = blocks + ([rest] if rest else [])
        labels = [" + ".join(a for a in blk if any(s in set(M) for s in CORRIDOR[a].split()))
                  for blk in variant if any(s in set(M) for a in blk for s in CORRIDOR[a].split())]
        rec = {"regions": regions, "labels": labels + (["REST"] if rest else []),
               "n_sealed": len(blocks), "rest": rest,
               "connected": [is_connected(b, adj) for b in blocks],
               "rest_components": len(split_floor.components({s: M[s] for s in rest},
                                                              {s: adj.get(s, set()) & set(rest) for s in rest}))
               if rest else 0}
        if not all(rec["connected"]):
            rec["splits"] = {tk: {} for tk in SEARCH_TRACKS}
            rec["infos"] = []
        else:
            rec["infos"] = search_blocks(M, regions, adj, lo, hi, cache)
            rec["splits"] = {tk: k_splits(rec["infos"], tk, lo, hi) for tk in SEARCH_TRACKS}
        out[name] = rec
    return out


def search_structure(st: dict, adj: dict, divisions: dict) -> dict:
    """Search results for one structure: per channel (not a fixed one) the A search and the B
    variants, memoised by footprint and window."""
    out = {}
    done = {}
    for c, M in st["channels"].items():
        if c in st["fixed"]:
            continue
        lo, hi = window_of(c, st["whole"][c])
        key = (round(lo, 6), round(hi, 6), tuple(sorted((s, round(v, 3)) for s, v in M.items())))
        if key not in done:
            done[key] = {"A": search_channel(M, divisions, adj, lo, hi),
                         "B": search_corridor(M, adj, lo, hi, {}), "window": (lo, hi)}
        out[c] = done[key]
    return out


def code_of(rec: dict) -> str:
    """A coarsening's regions as division codes: [NE+MA][ENC+ESC]..."""
    return "".join("[" + "+".join(DIV_CODE[d] for d in blk) + "]" for blk in rec["divisions"])


def md_region_table(rec: dict, ks: tuple, lo: float, hi: float) -> list:
    lines = ["| region | states | $M | feasible K (win) | feasible K (band) | chosen K | headroom |",
             "|---|---|---|---|---|---|---|"]
    for label, states, info, k in zip(rec["labels"], rec["regions"], rec["infos"], ks):
        lines.append(f"| {label} | {', '.join(states)} ({len(states)}) | {info['usd']:,.0f} | "
                     f"{fmt_ks(pass_k(info, 'win'))} | {fmt_ks(pass_k(info, 'band'))} | {k} | "
                     f"{headroom(info['usd'] / k, lo, hi):.2f} |")
    return lines


def md_point_search(pt: dict, st: dict, res: dict) -> tuple:
    """The section of one grid point (lines, A feasible per track, the B variants that pass every channel)."""
    chans = {c: k for c, k in pt["k"].items()}
    lines = [f"### {pt['id']}  ({', '.join(f'{c} {k}' for c, k in chans.items())})", ""]
    a_ok = {"win": True, "band": True}
    for c, k in chans.items():
        if c in st["fixed"]:
            lines += [f"**{c} K{k}: fixed**, not searched (whole-state districts, not sealed: "
                      "New England 2 + plains 1).", ""]
            continue
        lo, hi = res[c]["window"]
        found = res[c]["A"]
        win, band = feasible_at(found, k, "win"), feasible_at(found, k, "band")
        for tk, lst in (("win", win), ("band", band)):
            a_ok[tk] = a_ok[tk] and bool(lst)
        lines += [f"**A, {c} K{k}** (window ${lo:,.0f}-{hi:,.0f}M, τ = {math.fsum(st['channels'][c].values()) / k:,.0f}M): "
                  f"{found['n']} connected coarsenings; feasible {len(win)} (win), {len(band)} (band).", ""]
        if not win:
            lines += ["No coarsening has window-feasible K per region summing to K.", ""]
            continue
        sealed = [r for r in win if len(r["regions"]) > 1]
        top_h = max(sealed, key=lambda r: (r["head"], len(r["regions"]))) if sealed else None
        if top_h is not None and top_h is not win[0]:
            lines += [f"Highest headroom among the sealed ones (2+ regions): {code_of(top_h)}, "
                      f"{len(top_h['regions'])} regions, min headroom {top_h['head']:.2f}.", ""]
        for i, r in enumerate(win[:SEARCH_TOP]):
            b = r["splits"]["band"].get(k)
            lines += [f"- A{i + 1}: {len(r['regions'])} regions, min headroom {r['head']:.2f} (win)"
                      + (f", band-feasible (headroom {b[0]:.2f}, K {'+'.join(map(str, b[1]))})" if b
                         else ", not band-feasible"),
                      f"  largest region {max(len(x) for x in r['regions'])} states"]
            lines += [""] + md_region_table(r, r["ks"], lo, hi) + [""]
        if band and not any(r["splits"]["band"].get(k) for r in win[:SEARCH_TOP]):
            r = band[0]
            lines += [f"- best band-feasible: {len(r['regions'])} regions, headroom {r['head']:.2f}", ""]
            lines += md_region_table(r, r["ks"], lo, hi) + [""]
    lines += [f"**A verdict, {pt['id']}**: win {'YES' if a_ok['win'] else 'NO'}, "
              f"band {'YES' if a_ok['band'] else 'NO'}.", ""]
    lines += ["**B (Northeast corridor sealed, the rest one unsealed region)**", "",
              "| variant | " + " | ".join(f"{c} K{k}" for c, k in chans.items() if c not in st["fixed"]) + " |",
              "|---|" + "---|" * sum(c not in st["fixed"] for c in chans)]
    b_pass = {}
    for v in CORRIDOR_VARIANTS:
        cells = []
        for c, k in chans.items():
            if c in st["fixed"]:
                continue
            lo, hi = res[c]["window"]
            rec = res[c]["B"][v]
            w, b = rec["splits"]["win"].get(k), rec["splits"]["band"].get(k)
            if not all(rec["connected"]):
                cells.append("block disconnected")
            elif not w:
                cells.append("no")
            else:
                cells.append(f"yes{' (band)' if b else ' (win only)'} h {w[0]:.2f} "
                             f"K {'+'.join(map(str, w[1]))}")
            if w and all(rec["connected"]):
                b_pass.setdefault(v, []).append((c, rec, w, b))
        lines.append(f"| {v} | " + " | ".join(cells) + " |")
    n_ch = sum(c not in st["fixed"] for c in chans)
    common = {v: x for v, x in b_pass.items() if len(x) == n_ch}
    lines += [""]
    if common:
        def bkey(v):
            x = common[v]
            return (-len(x[0][1]["regions"]), -min(w[0] for _, _, w, _ in x))
        best = min(common, key=bkey)
        lines += [f"**B verdict, {pt['id']}**: YES with {', '.join(common)}; best {best}.", ""]
        for c, rec, w, b in common[best]:
            lo, hi = res[c]["window"]
            lines += [f"{c} K{chans[c]} under {best}:", ""] + md_region_table(rec, w[1], lo, hi)
            if rec["rest_components"] > 1:
                lines += ["", f"REST is {rec['rest_components']} components on this footprint "
                          "(judged by the parts check)."]
            lines += [""]
    else:
        per = {c: [v for v, x in b_pass.items() if any(cc == c for cc, *_ in x)]
               for c in chans if c not in st["fixed"]}
        lines += [f"**B verdict, {pt['id']}**: NO variant passes every channel. Passing variants "
                  "per channel: " + "; ".join(f"{c}: {', '.join(v) or 'none'}" for c, v in per.items()), ""]
    return lines, a_ok, common


def md_ifa_confirm(sts: dict, adj: dict, parts: dict) -> tuple:
    """C: P1 at K48-54 and the per-region K combos that hit each total."""
    st = sts["ifa"]
    M = st["channels"]["IFA"]
    lo, hi = window_of("IFA", False)
    regs = channel_regions(M, parts["P1"], adj, lo, hi)
    names = list(regs)
    lines = [f"IFA window ${lo:,.0f}-{hi:,.0f}M (merge.BAND_M); P1 regions and their feasible K:", "",
             "| region | states | $M | feasible K (win) | feasible K (band) |", "|---|---|---|---|---|"]
    for r in names:
        v = regs[r]
        lines.append(f"| {r} | {', '.join(s for s in parts['P1'][r] if s in M)} | {v['usd']:,.0f} | "
                     f"{fmt_ks(pass_k(v, 'win'))} | {fmt_ks(pass_k(v, 'band'))} |")
    lines += ["", "| total | combos (win) | combos (band) | best headroom (win), K by region in the order "
              + " ".join(names) + " | forced states/cuts (band, minimum) |", "|---|---|---|---|---|"]
    full = []
    for tot in IFA_TOTALS:
        combos_ = {}
        for tk in SEARCH_TRACKS:
            ks = [sorted(pass_k(regs[r], tk)) for r in names]
            combos_[tk] = [c for c in itertools.product(*ks) if sum(c) == tot]

        def h(c):
            return min(headroom(regs[r]["usd"] / k, lo, hi) for r, k in zip(names, c))
        best = max(combos_["win"], key=h) if combos_["win"] else None
        reach = reach_of(regs, "band")
        lines.append(f"| {tot} | {len(combos_['win'])} | {len(combos_['band'])} | "
                     + (f"{h(best):.2f}: {' '.join(map(str, best))}" if best else "none") + " | "
                     + (f"{reach[tot][0]}/{reach[tot][1]}" if tot in reach else "—") + " |")
        full += [f"### IFA K{tot}: {len(combos_['win'])} combos (win), {len(combos_['band'])} (band)", "",
                 "K by region " + " ".join(names) + "; headroom = min over regions; band = also band-feasible", "",
                 "| " + " | ".join(names) + " | headroom | band |", "|" + "---|" * (len(names) + 2)]
        bandset = set(combos_["band"])
        for c in sorted(combos_["win"], key=lambda c: (-h(c), c)):
            full.append("| " + " | ".join(map(str, c)) + f" | {h(c):.2f} | {'yes' if c in bandset else 'no'} |")
        full.append("")
    return lines + [""], full


ARITH_NOTICE = ("> **Arithmetic only; no feasibility certificate.** Every pass, feasible-K and band/win "
                "entry below is a necessary check on dollar sums, not a statement that a connected, "
                "balanced district map exists.")


def write_report(path: str, lines: list) -> None:
    """One generated markdown report, the arithmetic-only notice first (every table is standalone)."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join([ARITH_NOTICE, ""] + list(lines)) + "\n")


def run_search(extract: str, out: str) -> dict:
    """--search: 7_partition_search.md and 7b_ifa_combos.md under `out`."""
    cells = overnight.state_cells(extract)
    adj = state_graph()
    parts = partitions()
    sts = structures(cells)
    divisions = parts["P2"]
    os.makedirs(out, exist_ok=True)
    head_rows, sections, results = [], [], {}
    for name in ("ne_plains", "nw49", "nw34", "w1"):
        st = sts[name]
        res = search_structure(st, adj, divisions)
        results[name] = res
        for pt in [p for p in overnight.POINTS if p["structure"] == name]:
            sec, a_ok, common = md_point_search(pt, st, res)
            sections += sec
            ch = [c for c in pt["k"] if c not in st["fixed"]]
            best_a = []
            for c in ch:
                w = feasible_at(res[c]["A"], pt["k"][c], "win")
                best_a.append(f"{c} {code_of(w[0])} h{w[0]['head']:.2f} ({len(w)})" if w
                              else f"{c} none")
            if common:
                bkey = min(common, key=lambda v: (-len(common[v][0][1]["regions"]),
                                                  -min(w[0] for _, _, w, _ in common[v])))
                best_b = bkey.split()[0]
            else:
                best_b = "none"
            head_rows.append(f"| {pt['id']} | {'; '.join(best_a)} | {'YES' if a_ok['win'] else 'NO'}"
                             f"/{'YES' if a_ok['band'] else 'NO'} | {best_b} | "
                             f"{'YES' if common else 'NO'} |")
    ifa_lines, ifa_full = md_ifa_confirm(sts, adj, parts)
    doc = ["# Partition search (arithmetic only: window fit and K sums, no feasibility certificate)", "",
           "Generated by `tools/exp/region_arith.py --search`. Channels are independent footprints; "
           "ne_plains WIFI stays NE 2 + plains 1 whole-state districts, not sealed (not searched). "
           "west8 is skipped (WH has no band-passing K even unsealed).", "",
           "**Rules.** A region is a set of footprint states, connected in the state graph "
           "(`state_graph`, polygon edges plus connectors). *Feasible* means every region has a "
           "window-feasible K that passes the `win` parts check (`ok_win`) and the regional K sum to "
           "the point's K; *band* also needs `ok_band` (parts floor against the final δ). Headroom per "
           "region is 2 min(τ_r - L, U - τ_r) / (U - L) at the chosen K; a split maximises the minimum "
           "over regions. Ranking: most regions, then the largest minimum headroom, then the fewest "
           "states in the largest region. A = unions of adjacent Census divisions (all connected "
           "coarsenings, by set partition of the divisions that hold a footprint state). B = the corridor "
           "(CT ME MA NH RI VT NY NJ PA DE MD DC VA, footprint only) sealed as the named variant, the "
           "rest of the footprint one unsealed region (its components are judged by the parts check, "
           "as in P0). `win` is the bound any method meets; `band` is the chain's rule.", "",
           "## Headline", "",
           "A: best coarsening per channel as division codes (NE New England, MA Middle Atlantic, ENC/WNC East/"
           "West North Central, SA South Atlantic, ESC/WSC East/West South Central, MTN Mountain, PAC Pacific), "
           "its minimum headroom h and the number of feasible coarsenings; feasible = win/band.", "",
           "| point | A best per channel (coarsening, h, count) | A feasible win/band "
           "| B best variant (every channel) | B feasible (win) |", "|---|---|---|---|---|"]
    doc += head_rows + ["", "## C. IFA under P1 (IFA regions)", ""] + ifa_lines
    doc += ["## Per grid point", ""] + sections
    write_report(os.path.join(out, "7_partition_search.md"), doc)
    write_report(os.path.join(out, "7b_ifa_combos.md"), ["# IFA P1: per-region K combos by total", ""] + ifa_full)
    return results


# ------------------------------------------------------------------------------ checks and main
def check_section10(results: dict) -> list:
    """P0 against §10: the feasible K per channel and the locked grid's headroom."""
    lines = ["| structure | channel | §10 K | here (WH ≥ 8 shown; raw window in brackets) | match |",
             "|---|---|---|---|---|"]
    for name, chans in SECTION10_K.items():
        f0 = results[name]["tr"]["f0"]
        for c, (a, b) in chans.items():
            ks = f0[c]
            raw = region_analysis(results[name]["st"]["channels"][c], results[name]["adj"],
                                  *results[name]["tr"]["windows"][c])["k"]
            ok = (ks and (min(ks), max(ks)) == (a, b)) or (c == "WH" and min(raw) == a and max(raw) == b)
            lines.append(f"| {name} | {c} | {a}-{b} | {fmt_ks(ks)} [{fmt_ks(raw)}] | {'yes' if ok else 'NO'} |")
    lines += ["", "| point | §10 headroom | here | match |", "|---|---|---|---|"]
    for name, res in results.items():
        for r in res["points"]:
            if r["id"] in SECTION10_HEAD and r["headroom"] is not None:
                ok = abs(r["headroom"] - SECTION10_HEAD[r["id"]]) < 0.006
                lines.append(f"| {r['id']} | {SECTION10_HEAD[r['id']]:.2f} | {r['headroom']:.2f} | "
                             f"{'yes' if ok else 'NO'} |")
    return lines + [""]


def ifa_points() -> list:
    return [{"id": f"ifa-{t}", "structure": "ifa", "k": {"IFA": t}} for t in IFA_TOTALS]


def run(extract: str, out: str) -> dict:
    cells = overnight.state_cells(extract)
    adj = state_graph()
    parts = partitions()
    sts = structures(cells)
    os.makedirs(out, exist_ok=True)
    results = {}
    for name, st in sts.items():
        totals = IFA_TOTALS if name == "ifa" else MAIN_TOTALS
        tr = total_rows(name, st, parts, adj, totals)
        pts = ifa_points() if name == "ifa" else [p for p in overnight.POINTS if p["structure"] == name]
        results[name] = {"st": st, "tr": tr, "adj": adj, "totals": totals,
                         "points": point_rows(name, st, tr, pts),
                         "grouping": grouping_rows(st, parts, adj)}
    files = {"1_regions.md": [], "2_totals.md": [], "2b_points.md": [], "3_grouping.md": [],
             "5_membership.md": [], "6_jobs.md": []}   # 7: the orphans, in 3_grouping.md
    for name, res in results.items():
        files["1_regions.md"] += md_regions(name, res["st"], res["tr"])
        files["2_totals.md"] += md_totals(name, res["st"], res["tr"], res["totals"])
        files["2b_points.md"] += md_points(name, res["points"], list(parts))
        files["3_grouping.md"] += md_grouping(name, res["grouping"])
        files["5_membership.md"] += md_membership(name, res["grouping"])
        files["6_jobs.md"] += md_jobs(name, res["grouping"])
    files["0_section10_check.md"] = check_section10(results)
    files["4_summary.md"] = md_summary(results, parts)
    files["1b_matrix.md"] = md_matrix(results, parts)
    for fn, lines in files.items():
        write_report(os.path.join(out, fn), lines)
    with open(os.path.join(out, "region_arith.json"), "w", encoding="utf-8") as fh:
        json.dump({n: {"f0": r["tr"]["f0"], "points": r["points"], "grouping": r["grouping"],
                       "reach": {p: {tk: {c: {str(k): v[:2] for k, v in rc.items()}
                                         for c, rc in t["reach"].items()}
                                     for tk, t in pv["tracks"].items()}
                                 for p, pv in r["tr"]["partitions"].items()}}
                   for n, r in results.items()}, fh, indent=1, default=str)
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT_DEFAULT, help="where the tables go (default /tmp)")
    ap.add_argument("--extract", default=overnight.EXTRACT, help="the dollar extract")
    ap.add_argument("--search", action="store_true",
                    help="only the partition search: 7_partition_search.md, 7b_ifa_combos.md")
    a = ap.parse_args(argv)
    if not os.path.exists(a.extract):
        print(f"missing {a.extract}", file=sys.stderr)
        return 2
    if a.search:
        run_search(a.extract, a.out)
        print(f"wrote {os.path.join(a.out, '7_partition_search.md')}")
        return 0
    results = run(a.extract, a.out)
    print(f"wrote {a.out}: " + ", ".join(sorted(os.listdir(a.out))))
    print("\n".join(check_section10(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
