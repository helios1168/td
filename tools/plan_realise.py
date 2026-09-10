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

Two things this driver reports rather than fixes.  Contiguity is checked here, not by level 2:
`realise` cuts a state by a power diagram of the centres, which owes the proximity graph
nothing, so a district can come back disconnected and that is recorded per district, not
raised.  Read it beside `graph_components`: the check runs on the graph the instance file
carries, and the v2 CONUS file as of 2026-09-10 carries 827 components over its 3,713 zips (the
contiguity model's own vertex set and edges ship in `geom.json`, CLAUDE.md traps 21 and 23), so
on that instance every district reads disconnected however it was cut.  And level 0's cover row
is per
(state, channel) over all slots, so two bundles sharing
a channel can each take a share of one state; the projections then overlap at zip level.  Such
cells are counted in `realise.json` as `overlaps` and awarded to the first bundle in sorted
order.
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

# the fine label -> the channel the file carries it under
FILE_OF = {"N_WH": "national", "N_FI": "national", "WH": "wh", "FI": "fi"}


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="a finished tools/full_plan.py output directory")
    ap.add_argument("--rounds", type=int, default=5,
                    help="max Lloyd rounds per split state at level 2")
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

    rounds_used = out["rounds_used"]
    return dict(
        to_district=to_district,
        split_states=[state_list[s] for s in out["split_states"]],
        rounds_used=max(rounds_used.values()) if rounds_used else 0,
        n_fractional=int(out["n_fractional"]),
        folded_states=folded,
        pseudo_column=bool(keep > k),
        n_missing=len(missing),
    )


def contiguity(proj, to_district: dict) -> dict:
    """`{district: bool}` on the projection's proximity graph, `other` excluded.

    Level 2 has no such check: `centers.assign` cuts a state by a power diagram of the centres
    and never reads an edge, so this is measured after the fact.
    """
    members: dict[str, set] = {}
    for z, d in to_district.items():
        members.setdefault(d, set()).add(z)
    return {d: bool(nx.is_connected(proj.G.subgraph(part)))
            for d, part in sorted(members.items()) if d != OTHER and part}


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
                    "wholesaler", "staffed", "contiguous"])
        for r in rows:
            w.writerow([r["district"], r["bundle"], " ".join(r["channels"]), r["states"],
                        r["n_zips"], r["mass"], r["wholesaler"],
                        int(r["staffed"]), int(r["contiguous"])])


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
    print(f"plan: {sum(len(v) for v in by_bundle.values())} used slot(s) over "
          f"{len(by_bundle)} bundle(s) {sorted(by_bundle)}, {len(rep_of)} staffed", flush=True)

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
        contig = contiguity(proj, to_district)

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
                contiguous=bool(contig.get(name, False))))

        resid_mass = 0.0
        for zp in members.get(OTHER, ()):
            M_c = dict(d.G.nodes[zp].get("M_c") or {})
            resid_mass += sum(float(M_c.get(c, 0.0)) for c in chans)
        record[bundle] = dict(
            status="ok", k=len(recs), n_zips=len(to_district),
            split_states=res["split_states"], rounds_used=res["rounds_used"],
            n_fractional=res["n_fractional"], pseudo_column=res["pseudo_column"],
            folded_states=res["folded_states"], n_missing=res["n_missing"],
            residual_zips=len(members.get(OTHER, ())), residual_mass=resid_mass,
            contiguous=contig,
            # what a `contiguous` of 0 is worth: the instance ships its own graph, and on the
            # v2 CONUS file as of 2026-09-10 that graph is 827 components over 3,713 zips (the
            # contiguity model's vertex set and edges live in geom.json, CLAUDE.md traps 21 and
            # 23), so a district cannot be connected on it however it was cut
            graph_components=nx.number_connected_components(proj.G),
            seconds=time.time() - t0)
        print(f"{bundle}: {len(recs)} district(s), {len(res['split_states'])} split state(s), "
              f"{record[bundle]['residual_zips']} zip(s) other, "
              f"{sum(1 for v in contig.values() if not v)} disconnected "
              f"({record[bundle]['seconds']:.1f}s)", flush=True)

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
        json.dump(dict(run_dir=run_dir, rounds=args.rounds, bundles=record,
                       overlaps=overlaps,
                       districts=[dict(district=r["district"], slot=r["slot"],
                                       bundle=r["bundle"], wholesaler=r["wholesaler"])
                                  for r in district_rows]),
                  fh, indent=2, default=float)
        fh.write("\n")

    staffed = sum(1 for r in district_rows if r["staffed"])
    print(f"districts={len(district_rows)} staffed={staffed} "
          f"unstaffed={len(district_rows) - staffed} "
          f"disconnected={sum(1 for r in district_rows if not r['contiguous'])}", flush=True)
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
