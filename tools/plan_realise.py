"""plan_realise.py: a finished `tools/full_plan.py` run -> zip and wholesaler assignments.

    .venv/bin/python3 tools/plan_realise.py battery/results/full_problem/seq_regression \\
        --geo-cache data/geo

Level 0 decides a channel plan at state x channel grain and hands level 2 one projected
instance per bundle (`projections/<bundle>/instance_descaled.json.gz` and `state_shares.csv`,
`docs/FULL_PROBLEM.md` section 6).  This driver runs that last step and joins the answer to the
plan's staffing:

    1. per used bundle, `td.solvers.state_splits.realise` over the projection's zips, with the
       bundle's used slots as the districts and one extra pseudo-district `other` carrying the
       share the plan left uncovered, so a state whose shares sum to less than 1 keeps its
       uncovered mass out of the real slots and a state touching no slot at all does not make
       `realise` raise (`td/solvers/state_splits.py:945-946`);
    2. slot -> wholesaler from `staffing.json` (`assignment` is keyed by the slot's index into
       `plan.json`'s `slots`);
    3. four files under the run directory (or `--out`): `assignment.csv` (one row per
       (zip, fine channel) cell), `districts.csv`, `wholesalers.csv` and `realise.json`.

Masses and books in the tables are read off the run's own per-cell instance
(`instance_v2.json.gz`, else the file `params.json` names), so `assignment.csv` sums to
`districts.csv` exactly; the projection files drive level 2 itself, as they do in the real
hand-off.

Contiguity is measured and repaired here, not by level 2: `realise` cuts a state by a power
diagram of the centres and never reads an edge, so a district comes back shattered.  The graph
is the one the project's contiguity model uses, the rook graph of the Voronoi cells of the zip
points (CLAUDE.md traps 21 and 23), built by the same calls `tools/geom_export.py` makes and
cached per bundle as `projections/<bundle>/cell_graph.json`.  The instance file's own edges are
never used: the v3 CONUS file carries 1,108 components over its 6,459 zips, so every district
would read disconnected on it however it was cut.

After the cut, `repair` frees every non-largest piece of every district and grows it back onto a
neighbouring district that is admissible in the freed zip's own state -- which leaves an unsplit
state's boundary alone, since only one district is admissible there -- never worsening either
district's distance outside the plan's mass band `[L, U]`.  What it cannot fix it names:
`realise.json` carries `pieces_before`, `pieces_after`, `moved` and an `unrepaired` list with a
reason per district, the commonest being that level 0 gave the district states that are not
adjacent, which no zip-level move can mend.

Level 0's cover row is per (state, channel) over all slots, so two bundles sharing a channel can
each take a share of one state; the projections then overlap at zip level.  Such cells are
counted in `realise.json` as `overlaps` and awarded to the first bundle in sorted order.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channel, channels, geo                                       # noqa: E402
from td import instance as descaled                                         # noqa: E402
from td.solvers import state_splits as ss                                   # noqa: E402
import run_draw                                                             # noqa: E402

# a state whose shares fall short of 1 by less than this is rounding (plan.json keeps 6 dp),
# not uncovered mass.  Opening the pseudo-column for it would cost the state a whole zip:
# `centers.assign` repairs every district with a positive target into non-emptiness.
RESIDUAL_TOL = 1e-4

OTHER = "other"

# a mass move is refused if it raises either district's distance outside [L, U] by more than
# this; the level-2 cut already leaves districts a little outside the band, so the guard is
# "never worse", not "inside"
BAND_TOL = 1e-9

# the fine label -> the channel the file carries it under
FILE_OF = {"N_WH": "national", "N_FI": "national", "WH": "wh", "FI": "fi"}

GRAPH = "cell_rook"

# {tuple(keys): (zips, edges)} -- the three bundles of a plan run usually project the same zip
# set, and one Voronoi diagram over 6,459 points is the expensive part of this driver
_PROX_CACHE: dict = {}


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="a finished tools/full_plan.py output directory")
    ap.add_argument("--rounds", type=int, default=5,
                    help="max Lloyd rounds per split state at level 2")
    ap.add_argument("--repair-rounds", type=int, default=10,
                    help="max contiguity repair rounds per bundle; 0 measures and does not move")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--out", default=None, help="where to write (default: RUN_DIR)")
    return ap


def district_name(bundle: str, j: int) -> str:
    """Bundle plus the 1-based slot position inside it: `WH_03`.  `run_draw.district_id`'s
    `D01` names a level-2 column, which is per bundle and would collide across bundles."""
    return f"{bundle}_{j + 1:02d}"


def _load_run(run_dir: str) -> tuple[dict, dict, dict]:
    def read(name):
        with open(os.path.join(run_dir, name), encoding="utf-8") as fh:
            return json.load(fh)
    params_path = os.path.join(run_dir, "params.json")
    params = read("params.json") if os.path.exists(params_path) else {}
    return read("plan.json"), read("staffing.json"), params


def cell_instance(run_dir: str, params: dict):
    """The run's per-cell instance, carrying the fine labels."""
    path = os.path.join(run_dir, "instance_v2.json.gz")
    if not os.path.exists(path):
        path = params.get("instance")
        if not path or not os.path.exists(path):
            raise FileNotFoundError(
                f"{run_dir} has no instance_v2.json.gz and params.json names no readable "
                f"instance; the run's cell masses cannot be read")
    d = descaled.load_descaled(path)
    if not d.channels:
        raise ValueError(f"{path} carries one channel; a plan run needs a format-2 instance")
    if tuple(d.channels) != tuple(channels.CHANNELS):
        d = channels.fine_split(d)
    return d


def used_by_bundle(plan: dict) -> dict:
    """`{bundle: [(slot index, record), ...]}` in plan order, which is the order
    `tools/full_plan.py::_write_projections` numbered the `state_shares.csv` districts in."""
    out: dict[str, list] = {}
    for i, rec in enumerate(plan["slots"]):
        if rec["used"] and rec["y"]:
            out.setdefault(rec["bundle"], []).append((i, rec))
    return out


def wholesaler_of(staffing: dict) -> dict:
    """`{slot index: rep}`.  `td.stage2_state.state_stage2` keys `assignment` by the slot's
    index into the plan's slot list, which JSON has turned into a string."""
    return {int(j): rep for j, rep in (staffing.get("assignment") or {}).items()}


def read_shares(path: str) -> dict:
    """`state_shares.csv` -> `{state: {district id: share}}`."""
    out: dict[str, dict[str, float]] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out.setdefault(row["state"], {})[row["district"]] = float(row["share"])
    return out


def _state_centroids(xy: np.ndarray, M: np.ndarray, state_idx: np.ndarray,
                     n_state: int) -> np.ndarray:
    C = np.zeros((n_state, xy.shape[1]), float)
    for s in range(n_state):
        sel = state_idx == s
        w = float(M[sel].sum())
        if w > 0:
            C[s] = (M[sel, None] * xy[sel]).sum(axis=0) / w
        elif sel.any():
            C[s] = xy[sel].mean(axis=0)
    return C


def initial_centers(state_C: np.ndarray, z: np.ndarray, y: np.ndarray,
                    M_s: np.ndarray) -> np.ndarray:
    """One centre per column, the target-weighted mean of the state centroids it touches.

    Level 2's Lloyd rounds only accept a round that does not raise the state's compactness, so
    this is a starting point, not a decision.
    """
    n_state, k = z.shape
    C = np.zeros((k, state_C.shape[1]), float)
    for j in range(k):
        w = np.where(z[:, j], y[:, j] * M_s, 0.0)
        if w.sum() > 0:
            C[j] = (w[:, None] * state_C).sum(axis=0) / w.sum()
        else:
            touch = np.flatnonzero(z[:, j])
            C[j] = state_C[touch].mean(axis=0) if touch.size else state_C.mean(axis=0)
    return C


def realise_bundle(bundle: str, recs: list, proj, shares: dict, geo_cache: str,
                   rounds: int) -> dict:
    """Level 2 for one bundle: `{zip: district name}` plus what the run should record."""
    zips_all = sorted(proj.G)
    xy_dict, missing = run_draw.coordinates(zips_all, geo_cache)
    placed = [z for z in zips_all if z in xy_dict]
    states_by_zip = {z: proj.G.nodes[z].get("state", "") for z in zips_all}
    M_by_zip = {z: float(proj.G.nodes[z]["M"]) for z in zips_all}
    if not placed:
        raise ValueError(f"bundle {bundle}: no zip of the projection has a gazetteer point")

    state_list = sorted({states_by_zip[z] for z in placed})
    s_of = {s: i for i, s in enumerate(state_list)}
    xy = np.array([xy_dict[z] for z in placed], float)
    M = np.array([M_by_zip[z] for z in placed], float)
    state_idx = np.array([s_of[states_by_zip[z]] for z in placed], int)
    M_s = np.bincount(state_idx, weights=M, minlength=len(state_list)).astype(float)

    k = len(recs)
    col = {run_draw.district_id(j): j for j in range(k)}
    resid = np.zeros(len(state_list), float)
    y = np.zeros((len(state_list), k + 1), float)
    for s, code in enumerate(state_list):
        for did, share in (shares.get(code) or {}).items():
            if did not in col:
                raise ValueError(f"bundle {bundle}: state_shares.csv names district {did!r}, "
                                 f"which is not one of this bundle's {k} used slot(s)")
            y[s, col[did]] = share
        resid[s] = max(0.0, 1.0 - float(y[s, :k].sum()))
    folded = {state_list[s]: float(resid[s]) for s in range(len(state_list))
              if 0.0 < resid[s] <= RESIDUAL_TOL}
    y[:, k] = np.where(resid > RESIDUAL_TOL, resid, 0.0)
    z = y > 0.0
    keep = k + 1 if z[:, k].any() else k              # no residual anywhere, no pseudo-column
    y, z = y[:, :keep], z[:, :keep]

    state_C = _state_centroids(xy, M, state_idx, len(state_list))
    C = initial_centers(state_C, z, y, M_s)
    out = ss.realise(xy, M, state_idx, z, y, C, rounds=rounds)

    names = [district_name(bundle, j) for j in range(k)] + [OTHER]
    to_district = {z_: names[int(lab)] for z_, lab in zip(placed, out["labels"])}
    to_district = channel.place_by_state(states_by_zip, to_district, missing, M_by_zip)

    # which real districts the plan lets a zip of each state belong to.  `z` is the level-1
    # decision after the residual fold, so an unsplit state names exactly one district and the
    # repair cannot move a zip out of it -- level 0 decided that state, not this driver.
    admissible = {code: {names[j] for j in range(k) if z[s, j]}
                  for s, code in enumerate(state_list)}

    rounds_used = out["rounds_used"]
    return dict(
        to_district=to_district,
        split_states=[state_list[s] for s in out["split_states"]],
        rounds_used=max(rounds_used.values()) if rounds_used else 0,
        n_fractional=int(out["n_fractional"]),
        folded_states=folded,
        pseudo_column=bool(keep > k),
        n_missing=len(missing),
        placed=placed,
        xy=xy_dict,
        states_by_zip=states_by_zip,
        M_by_zip=M_by_zip,
        admissible=admissible,
    )


def _state_borders(state_polys: dict, codes: list) -> list:
    """`[[s1, s2], ...]` -- the state pairs sharing a border of positive length.

    The yardstick for the cell graph: a state pair that shares a border but no cell edge is a
    gap the tessellation opened, and a district straddling it reads disconnected for a reason
    that is the geometry's, not the plan's.
    """
    import shapely
    geoms = [state_polys[c] for c in codes]
    ia, ib = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    keep = ia < ib
    ia, ib = ia[keep], ib[keep]
    lengths = shapely.length(shapely.intersection(np.asarray(geoms)[ia], np.asarray(geoms)[ib]))
    return sorted([codes[i], codes[j]] for i, j, L in zip(ia, ib, lengths) if L > 0)


def _proximity(keys: list, xy: dict, states_by_zip: dict, geo_cache: str) -> tuple:
    """`(zips, edges, state_borders)` -- `geom_export`'s proximity tessellation over `keys`.

    The same three calls `geom_export.export` makes, so the graph checked here is the graph the
    map is drawn against: one Voronoi diagram per state over that state's zips, clipped to the
    landmass, then the rook adjacency of those cells.  The vertex set is the cell dict's own
    keys, never `keys`: a zip whose cell clips away to nothing on the coastline has no cell, and
    admitting it as an isolated vertex would invent a district piece (CLAUDE.md trap 21).
    """
    import geom_export
    um = geom_export._us_maps()
    states_gdf = geo.states_outline(geo_cache)
    state_polys = dict(zip(states_gdf["STUSPS"].astype(str), states_gdf.geometry))
    clip = um.clip_region([xy[z] for z in keys], states_gdf)
    prox = um.voronoi_cells(keys, xy, clip, zip_state=states_by_zip, state_polys=state_polys)
    codes = sorted({states_by_zip.get(z, "") for z in keys} & set(state_polys))
    return sorted(prox), geom_export._proximity_edges(prox), _state_borders(state_polys, codes)


def cell_graph(run_dir: str, bundle: str, keys: list, xy: dict, states_by_zip: dict,
               geo_cache: str) -> tuple:
    """`(graph, state_borders, path)` -- the cell rook graph over `keys`, cached beside the
    projection.

    The cache records the key set it was built from, so a rerun over a different projection
    rebuilds rather than silently reusing another run's tessellation.
    """
    path = os.path.join(run_dir, "projections", bundle, "cell_graph.json")
    keys = list(keys)
    rec = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            got = json.load(fh)
        if got.get("keys") == keys and got.get("state_borders") is not None:
            rec = (got["zips"], got["edges"], got["state_borders"])
    if rec is None:
        cached = _PROX_CACHE.get(tuple(keys))
        rec = cached if cached is not None else _proximity(keys, xy, states_by_zip, geo_cache)
        _PROX_CACHE[tuple(keys)] = rec
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(dict(graph=GRAPH, keys=keys, zips=rec[0], edges=rec[1],
                           state_borders=rec[2]), fh)
            fh.write("\n")
    G = nx.Graph()
    G.add_nodes_from(rec[0])
    G.add_edges_from((a, b) for a, b in rec[1])
    return G, [list(b) for b in rec[2]], path


def district_pieces(G, to_district: dict) -> dict:
    """`{district: [component, ...]}` on `G`, largest piece by zip count first.

    A zip `G` has no vertex for -- unplaced, or its cell clipped away -- is in no piece, so a
    district holding only such zips comes back with none.
    """
    members: dict[str, set] = {}
    for z, d in to_district.items():
        if z in G:
            members.setdefault(d, set()).add(z)
    return {d: sorted(nx.connected_components(G.subgraph(part)),
                      key=lambda p: (-len(p), min(p)))
            for d, part in sorted(members.items())}


def state_adjacency(G, states_by_zip: dict) -> dict:
    """`{state: set(state)}` -- the cell graph contracted to states."""
    adj: dict[str, set] = {}
    for a, b in G.edges():
        sa, sb = states_by_zip.get(a, ""), states_by_zip.get(b, "")
        adj.setdefault(sa, set())
        adj.setdefault(sb, set())
        if sa != sb:
            adj[sa].add(sb)
            adj[sb].add(sa)
    return adj


def _excess(m: float, band) -> float:
    """How far a district mass falls outside `[L, U]`.  No band, no excess."""
    if band is None:
        return 0.0
    return max(0.0, band[0] - m) + max(0.0, m - band[1])


def off_plan(G, labels: dict, states_by_zip: dict, admissible: dict) -> dict:
    """`{zip: district}` for zips a district holds in a state the plan gives it no share of.

    TODO(2026-09-10): the fix belongs in `td/solvers/centers.py::assign`, not here.  A zip with
    `M = 0` has a zero objective coefficient and zero weight in every mass row, so the
    transportation LP is indifferent to where it goes and HiGHS parks it in column 0; in an
    unsplit state `realise` overwrites that, in a split state it stands.  On `v3_seq_warm` it is
    533 (FI), 460 (N) and 719 (WH) zips, all of zero mass, all on the bundle's first district,
    and it is the single largest source of shattering there.  Until `assign` constrains a
    zero-mass zip (a tiny distance term, or a `penalty` shutting the zero-target columns), the
    repair frees them and grows them back onto a district the plan does admit.

    A district all of whose graph zips are off-plan keeps them: freeing every zip a district
    holds would leave the plan with an empty district, which is worse than an off-plan one.
    """
    off: dict[str, list] = {}
    held: dict[str, int] = {}
    for z, d in labels.items():
        if d == OTHER or z not in G:
            continue
        if d in admissible.get(states_by_zip.get(z, ""), set()):
            held[d] = held.get(d, 0) + 1
        else:
            off.setdefault(d, []).append(z)
    return {z: d for d, zs in off.items() if held.get(d, 0) for z in zs}


def repair(G, to_district: dict, M_by_zip: dict, states_by_zip: dict, admissible: dict,
           band, rounds: int = 10) -> dict:
    """Free what must move and grow it back onto a neighbour the plan admits.

    `td.solvers.district_split._reconnect`'s pattern, with the plan's constraints on top.  Per
    round, two sets are freed: every zip a district holds off-plan (`off_plan`), and, on the
    graph with those removed, every piece but the heaviest of a district that has more than
    one.  Then, repeatedly, the freed zip `j` and settled neighbour `k` with the most edges from
    `j` into `k`'s district (ties to the lighter district, then to the lower zip and name) is
    reassigned to it.  A move is offered only when

      * `k`'s district is real, is not the one `j` came from, and the plan gives it a positive
        share of `j`'s own state -- so a zip in an unsplit state has nowhere to go and level 0's
        state decision stands;
      * neither district's distance outside `[L, U]` rises.  The band is already breached by the
        level-2 cut on the live run, so the guard is "no worse", not "inside".

    Grown-back zips join the district's largest piece by construction, so no move disconnects
    the district that receives it.  A freed zip with no such neighbour keeps the label it had
    and is reported, never dropped.  Returns the new labels and what happened.
    """
    labels = dict(to_district)
    mass: dict[str, float] = {}
    for z, d in labels.items():
        mass[d] = mass.get(d, 0.0) + float(M_by_zip.get(z, 0.0))
    moved, used = 0, 0
    stuck: dict[str, dict] = {}       # {district: {zips, reasons}}, the last round's
    started_off = off_plan(G, labels, states_by_zip, admissible)

    for _ in range(max(int(rounds), 0)):
        stuck = {}                    # the last round's leftovers are the ones that stand
        freed: dict[str, str] = dict(off_plan(G, labels, states_by_zip, admissible))
        rest = G.subgraph([z for z in G if z not in freed])
        for d, parts in district_pieces(rest, labels).items():
            if d == OTHER or len(parts) <= 1:
                continue
            # `parts` is sorted by descending zip count, so `max` breaks a mass tie by size
            heaviest = max(parts, key=lambda p: sum(float(M_by_zip.get(z, 0.0)) for z in p))
            for p in parts:
                if p is not heaviest:
                    freed.update({z: d for z in p})
        if not freed:
            break
        used += 1
        n_before = moved
        while freed:
            cand = None                      # ((edges, -mass), (zip, district))
            for j in sorted(freed):
                src = freed[j]
                mj = float(M_by_zip.get(j, 0.0))
                allowed = admissible.get(states_by_zip.get(j, ""), set())
                deg: dict[str, int] = {}
                for k in G[j]:
                    t = labels.get(k)
                    if k in freed or t is None or t == OTHER or t == src or t not in allowed:
                        continue
                    deg[t] = deg.get(t, 0) + 1
                for t, n in deg.items():
                    if (_excess(mass[src] - mj, band) > _excess(mass[src], band) + BAND_TOL
                            or _excess(mass[t] + mj, band) > _excess(mass[t], band) + BAND_TOL):
                        continue
                    key = (n, -mass[t])
                    if cand is None or key > cand[0] or (key == cand[0] and (j, t) < cand[1]):
                        cand = (key, (j, t))
            if cand is None:
                break
            j, t = cand[1]
            mj = float(M_by_zip.get(j, 0.0))
            mass[freed[j]] -= mj
            mass[t] += mj
            labels[j] = t
            del freed[j]
            moved += 1
        for j, src in freed.items():
            stuck.setdefault(src, dict(zips=0, reasons=set()))
            stuck[src]["zips"] += 1
            stuck[src]["reasons"].add(_why_stuck(G, labels, freed, j, src, states_by_zip,
                                                 admissible, M_by_zip, mass, band))
        if moved == n_before:
            break

    by_district: dict[str, int] = {}
    for d in started_off.values():
        by_district[d] = by_district.get(d, 0) + 1
    return dict(labels=labels, moved=moved, rounds_used=used, mass=mass,
                off_plan=dict(zips=len(started_off),
                              mass=sum(float(M_by_zip.get(z, 0.0)) for z in started_off),
                              by_district=dict(sorted(by_district.items()))),
                stuck={d: dict(zips=v["zips"], reasons=sorted(v["reasons"]))
                       for d, v in sorted(stuck.items())})


def _why_stuck(G, labels: dict, freed: dict, j: str, src: str, states_by_zip: dict,
               admissible: dict, M_by_zip: dict, mass: dict, band) -> str:
    """The reason one freed zip could not move, for the report.

    Read off the same neighbours the grow loop could offer, which are the *settled* ones: a zip
    whose admissible neighbours were themselves detached had no move to refuse, and calling that
    a band refusal would blame the plan for a deadlock between two pieces.
    """
    allowed = admissible.get(states_by_zip.get(j, ""), set())
    seen = {labels.get(k) for k in G[j]} - {None, OTHER, src}
    settled = {labels.get(k) for k in G[j] if k not in freed} - {None, OTHER, src}
    if not seen:
        return "no neighbouring district"
    if not (seen & allowed):
        return f"neighbours hold no share of {states_by_zip.get(j, '')!r}"
    if not (settled & allowed):
        return "its admissible neighbours were all detached too"
    mj = float(M_by_zip.get(j, 0.0))
    if _excess(mass[src] - mj, band) > _excess(mass[src], band) + BAND_TOL:
        return "the band: the piece's district would drop below L"
    return "the band: every admissible neighbour would rise above U"


def _state_groups(sadj: dict, states: set) -> list:
    """The district's states, grouped by the cell edges that cross between them."""
    H = nx.Graph()
    H.add_nodes_from(states)
    H.add_edges_from((a, b) for a in states for b in sadj.get(a, ()) if b in states)
    return sorted((sorted(c) for c in nx.connected_components(H)), key=lambda c: c[0])


def plan_states(admissible: dict) -> dict:
    """`{district: set(state)}` -- the plan's own view, inverted from `admissible`.

    The reason a district is split has to be read off the states the *plan* gave it, not off
    the states its zips happen to sit in: an off-plan zip the repair could not move would
    otherwise blame level 0 for a state level 0 never assigned.
    """
    out: dict[str, set] = {}
    for state, names in admissible.items():
        for name in names:
            out.setdefault(name, set()).add(state)
    return out


def unrepaired(after: dict, states_of: dict, sadj: dict, stuck: dict, gaps: list) -> list:
    """One row per district still in several pieces, with why it is.

    The commonest reason is level 0's, not level 2's: a district the plan gave states no cell
    edge joins cannot be made contiguous by moving zips, because there is no zip between them.
    `gaps` separates that from the tessellation's own fault -- a state pair with a real border
    and no cell edge -- which reads the same on the graph and is not the plan's doing.
    """
    healed = {k: set(v) for k, v in sadj.items()}
    for a, b in gaps:
        healed.setdefault(a, set()).add(b)
        healed.setdefault(b, set()).add(a)
    rows = []
    for name, parts in after.items():
        if name == OTHER or len(parts) <= 1:
            continue
        states = states_of.get(name, set())
        groups = _state_groups(sadj, states)
        if len(groups) > 1 and len(_state_groups(healed, states)) == 1:
            shown = "; ".join(f"{a}-{b}" for a, b in gaps)
            listed = "; ".join(",".join(g) for g in groups)
            why = (f"the cell tessellation left no edge on a real state border ({shown}), which "
                   f"is the only thing joining its states: {listed}")
        elif len(groups) > 1:
            why = (f"level 0 gave it {len(groups)} state group(s) with no cell edge between "
                   f"them: {'; '.join(','.join(g) for g in groups)}")
        elif name in stuck:
            why = "; ".join(stuck[name]["reasons"])
        else:
            why = "the repair round cap was reached with pieces still detached"
        rows.append(dict(district=name, pieces=len(parts),
                         detached_zips=sum(len(p) for p in parts[1:]), reason=why))
    return rows


def _write_assignment(path: str, d, cell_of: dict) -> tuple[dict, dict]:
    """`assignment.csv`, one row per (zip, fine channel).  Returns the per-channel zip counts
    and the residual mass per channel, which is what the summary prints."""
    assigned = {c: 0 for c in channels.CHANNELS}
    residual = {c: 0.0 for c in channels.CHANNELS}
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zip", "state", "channel", "file_channel", "district", "bundle",
                    "wholesaler", "M_cell"])
        for zp in sorted(d.G):
            a = d.G.nodes[zp]
            M_c = dict(a.get("M_c") or {})
            for c in channels.CHANNELS:
                district, bundle, rep = cell_of.get((zp, c), (OTHER, "", ""))
                m = float(M_c.get(c, 0.0))
                if district == OTHER:
                    residual[c] += m
                else:
                    assigned[c] += 1
                w.writerow([zp, a.get("state", ""), c, FILE_OF[c], district, bundle, rep, m])
    return assigned, residual


def _write_districts(path: str, rows: list) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["district", "bundle", "channels", "states", "n_zips", "mass",
                    "wholesaler", "staffed", "pieces", "contiguous"])
        for r in rows:
            w.writerow([r["district"], r["bundle"], " ".join(r["channels"]), r["states"],
                        r["n_zips"], r["mass"], r["wholesaler"],
                        int(r["staffed"]), r["pieces"], int(r["contiguous"])])


def _write_wholesalers(path: str, rows: list) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["wholesaler", "district", "bundle", "n_zips", "book_in_district",
                    "book_total", "share_of_book_kept"])
        for r in rows:
            w.writerow([r["wholesaler"], r["district"], r["bundle"], r["n_zips"],
                        r["book_in_district"], r["book_total"], r["share_of_book_kept"]])


def bundle_channels(proj, bundle: str) -> tuple:
    """The channels a projection sums, from the `meta["bundle"]` `channels.project` wrote.

    A named bundle leaves its name there and a catch-all bundle its channel list, so this is
    the one reader that covers both without importing the driver that made them.
    """
    named = proj.meta.get("bundle")
    if isinstance(named, str):
        named = channels.BUNDLES.get(named)
    chans = tuple(named or ())
    unknown = [c for c in chans if c not in channels.CHANNELS]
    if not chans or unknown:
        raise ValueError(f"bundle {bundle!r}: the projection's meta['bundle'] is "
                         f"{proj.meta.get('bundle')!r}, not a channel list this run can key "
                         f"a cell table by")
    return chans


def _overlaps(by_bundle: dict, chans_of: dict) -> list:
    """(state, channel) pairs two used bundles both take a share of.  Level 0's cover row is
    `<= 1` per cell summed over slots, so this is a plan the projections cannot express."""
    seen: dict[tuple, set] = {}
    for bundle, recs in by_bundle.items():
        for c in chans_of.get(bundle, ()):
            for _, rec in recs:
                for st in rec["y"]:
                    seen.setdefault((st, c), set()).add(bundle)
    return [dict(state=st, channel=c, bundles=sorted(bs))
            for (st, c), bs in sorted(seen.items()) if len(bs) > 1]


def _main(args) -> int:
    run_dir = os.path.abspath(args.run_dir)
    out = os.path.abspath(args.out or run_dir)
    os.makedirs(out, exist_ok=True)

    plan, staffing, params = _load_run(run_dir)
    d = cell_instance(run_dir, params)
    by_bundle = used_by_bundle(plan)
    rep_of = wholesaler_of(staffing)
    # the plan's own mass band, in the projection's units.  A run whose params.json predates it
    # gets no band guard, and `realise.json` says so.
    band = ((float(params["L"]), float(params["U"]))
            if params.get("L") is not None and params.get("U") is not None else None)
    print(f"plan: {sum(len(v) for v in by_bundle.values())} used slot(s) over "
          f"{len(by_bundle)} bundle(s) {sorted(by_bundle)}, {len(rep_of)} staffed, "
          f"band {'[%g, %g]' % band if band else 'unset'}", flush=True)

    record: dict[str, dict] = {}
    chans_of: dict[str, tuple] = {}
    cell_of: dict[tuple, tuple] = {}
    district_rows: list[dict] = []
    book: dict[str, float] = {}

    for bundle in sorted(by_bundle):
        t0 = time.time()
        recs = by_bundle[bundle]
        cell = os.path.join(run_dir, "projections", bundle)
        proj = descaled.load_descaled(os.path.join(cell, "instance_descaled.json.gz"))
        shares = read_shares(os.path.join(cell, "state_shares.csv"))
        res = realise_bundle(bundle, recs, proj, shares, args.geo_cache, args.rounds)
        to_district = res["to_district"]

        G, borders, gpath = cell_graph(run_dir, bundle, res["placed"], res["xy"],
                                       res["states_by_zip"], args.geo_cache)
        before = district_pieces(G, to_district)
        fix = repair(G, to_district, res["M_by_zip"], res["states_by_zip"],
                     res["admissible"], band, rounds=args.repair_rounds)
        to_district = fix["labels"]
        after = district_pieces(G, to_district)
        sadj = state_adjacency(G, res["states_by_zip"])
        # a state pair that shares a real border but no cell edge: the tessellation opened a
        # gap, and a district straddling it cannot be repaired to contiguity here
        on_graph = {tuple(sorted((a, b))) for a in sadj for b in sadj[a]}
        gaps = [b for b in borders if tuple(sorted(b)) not in on_graph]
        still = unrepaired(after, plan_states(res["admissible"]), sadj, fix["stuck"], gaps)
        pieces_of = {name: len(parts) for name, parts in after.items()}

        chans = chans_of[bundle] = bundle_channels(proj, bundle)
        members: dict[str, list] = {}
        for zp, name in to_district.items():
            members.setdefault(name, []).append(zp)

        for j, (idx, rec) in enumerate(recs):
            name = district_name(bundle, j)
            zips_j = sorted(members.get(name, ()))
            rep = rep_of.get(idx, "")
            mass = 0.0
            for zp in zips_j:
                a = d.G.nodes[zp]
                M_c = dict(a.get("M_c") or {})
                S_c = dict(a.get("S_c") or {})
                for c in chans:
                    mass += float(M_c.get(c, 0.0))
                    cell_of.setdefault((zp, c), (name, bundle, rep))   # first bundle wins
                if rep:
                    per = dict(S_c.get(rep) or {})
                    book[name] = book.get(name, 0.0) + sum(float(per.get(c, 0.0))
                                                           for c in chans)
            district_rows.append(dict(
                district=name, slot=rec["id"], bundle=bundle, channels=chans,
                states=",".join(f"{st}:{sh:g}" for st, sh in sorted(rec["y"].items())),
                n_zips=len(zips_j), mass=mass, wholesaler=rep, staffed=bool(rep),
                pieces=pieces_of.get(name, 0),
                contiguous=pieces_of.get(name, 0) == 1))

        resid_mass = 0.0
        for zp in members.get(OTHER, ()):
            M_c = dict(d.G.nodes[zp].get("M_c") or {})
            resid_mass += sum(float(M_c.get(c, 0.0)) for c in chans)
        names = [district_name(bundle, j) for j in range(len(recs))]
        record[bundle] = dict(
            status="ok", k=len(recs), n_zips=len(to_district),
            split_states=res["split_states"], rounds_used=res["rounds_used"],
            n_fractional=res["n_fractional"], pseudo_column=res["pseudo_column"],
            folded_states=res["folded_states"], n_missing=res["n_missing"],
            residual_zips=len(members.get(OTHER, ())), residual_mass=resid_mass,
            graph=GRAPH, graph_path=os.path.relpath(gpath, run_dir),
            graph_zips=G.number_of_nodes(), graph_edges=G.number_of_edges(),
            components=nx.number_connected_components(G),
            cross_state_edges=sum(1 for a, b in G.edges()
                                  if res["states_by_zip"].get(a) != res["states_by_zip"].get(b)),
            no_cell_zips=len([z for z in res["placed"] if z not in G]),
            state_borders=len(borders), state_borders_on_graph=len(on_graph),
            state_borders_missing=gaps,
            band=list(band) if band else None,
            pieces_before={n: len(before.get(n, ())) for n in names},
            pieces_after={n: len(after.get(n, ())) for n in names},
            moved=fix["moved"], repair_rounds=fix["rounds_used"],
            off_plan=fix["off_plan"],
            band_violations=[dict(district=n, mass=fix["mass"].get(n, 0.0))
                             for n in names if _excess(fix["mass"].get(n, 0.0), band) > 0],
            unrepaired=still,
            seconds=time.time() - t0)
        rec_b = record[bundle]
        print(f"{bundle}: {len(recs)} district(s), {len(res['split_states'])} split state(s), "
              f"{rec_b['residual_zips']} zip(s) other; graph {GRAPH} "
              f"{rec_b['graph_zips']} zip(s) {rec_b['graph_edges']} edge(s) "
              f"{rec_b['components']} component(s), {rec_b['cross_state_edges']} cross-state; "
              f"pieces {sum(rec_b['pieces_before'].values())} -> "
              f"{sum(rec_b['pieces_after'].values())}, {fix['moved']} zip(s) moved, "
              f"{fix['off_plan']['zips']} off-plan (mass {fix['off_plan']['mass']:g}), "
              f"{len(still)} district(s) still split "
              f"({rec_b['seconds']:.1f}s)", flush=True)

    overlaps = _overlaps(by_bundle, chans_of)
    if overlaps:
        print(f"warning: {len(overlaps)} (state, channel) cell(s) served by two bundles; the "
              f"first bundle in sorted order wins", flush=True)

    assigned, residual = _write_assignment(os.path.join(out, "assignment.csv"), d, cell_of)
    _write_districts(os.path.join(out, "districts.csv"), district_rows)

    total = {}
    for zp in d.G:
        for rep, v in (d.G.nodes[zp].get("S") or {}).items():
            total[rep] = total.get(rep, 0.0) + float(v)
    held = {r["wholesaler"]: r for r in district_rows if r["wholesaler"]}
    wrows = []
    for rep in sorted(set(total) | set(staffing.get("reps") or ()) | set(held)):
        r = held.get(rep)
        b_in = book.get(r["district"], 0.0) if r else 0.0
        b_all = total.get(rep, 0.0)
        wrows.append(dict(wholesaler=rep, district=r["district"] if r else "",
                          bundle=r["bundle"] if r else "", n_zips=r["n_zips"] if r else 0,
                          book_in_district=b_in, book_total=b_all,
                          share_of_book_kept=(b_in / b_all) if b_all > 0 else 0.0))
    _write_wholesalers(os.path.join(out, "wholesalers.csv"), wrows)

    with open(os.path.join(out, "realise.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(run_dir=run_dir, rounds=args.rounds,
                       repair_rounds=args.repair_rounds, graph=GRAPH,
                       band=list(band) if band else None, bundles=record,
                       overlaps=overlaps,
                       districts=[dict(district=r["district"], slot=r["slot"],
                                       bundle=r["bundle"], wholesaler=r["wholesaler"])
                                  for r in district_rows]),
                  fh, indent=2, default=float)
        fh.write("\n")

    staffed = sum(1 for r in district_rows if r["staffed"])
    print(f"districts={len(district_rows)} staffed={staffed} "
          f"unstaffed={len(district_rows) - staffed} "
          f"disconnected={sum(1 for r in district_rows if not r['contiguous'])} "
          f"moved={sum(v['moved'] for v in record.values())} "
          f"band_violations={sum(len(v['band_violations']) for v in record.values())}",
          flush=True)
    for bundle in sorted(record):
        for row in record[bundle]["unrepaired"]:
            print(f"  {row['district']}: {row['pieces']} pieces, "
                  f"{row['detached_zips']} zip(s) detached -- {row['reason']}", flush=True)
    for c in channels.CHANNELS:
        print(f"{c}: {assigned[c]} zip(s) assigned, residual mass {residual[c]:.6g}",
              flush=True)
    print(f"wrote {out}", flush=True)
    return 0


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    return _main(args)


if __name__ == "__main__":
    raise SystemExit(main())
