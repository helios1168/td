"""staff_and_split.py -- staff a drawn map, splitting multi-rep districts with the contiguous
Nash bargaining solution in the same run.

    .venv/bin/python3 -u tools/staff_and_split.py instance_descaled_v2_conus.json.gz \\
        --table battery/results/app/clip_.../draw.csv --release R12,R31 \\
        --filler-capture full --multi D02:3,D07:4 --geom battery/results/app/clip_.../geom.json \\
        --out battery/results/app/staff_...

One composed script, not a chain of `tools/staff.py` and `tools/split_district.py`.  A district
named in `--multi` gets its roster resolved (top-N by gain among the reps who already book
there, conflict-skipped top-to-bottom, `resolve_rosters` below) *before* the ordinary N=1
Hungarian match runs, and the reps a resolved 2+-rep roster actually uses are excluded from that
match's candidate pool -- `--release` folds a rep's book into the free pool at the same rate the
rep's own book is valued (`filler_capture="full"`), which would distort every neighbouring N=1
match if it were used to keep a multi-claimed rep out of a district they still book; exclusion
from candidacy does the same job without that distortion.  Every district in scope, N=1 or N>1,
is priced off one `channel.gain_matrix` call.

Writes `<out>/staffing.json`, the `tools/staff.py` schema plus `split_districts` (one entry per
2+-rep district, the `tools/split_district.py` per-district report) and `requested_multi` (every
`--multi` district's requested vs. resolved roster size); `assignment` / `split_districts` /
`unstaffed_districts` partition `districts` (the scope) three ways, mutually exclusive and
jointly exhaustive.  `<out>/draw.csv` is the input table with `rep` filled in: unconditionally
from `assignment` for an N=1-resolved district, per-zip from each split's own `labels` for a
2+-rep one, unchanged everywhere else.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channel, geo, model, telemetry, ziptable                      # noqa: E402
from td import instance as descaled                                          # noqa: E402
from td.solvers import district_split                                        # noqa: E402

import staff                                                                 # noqa: E402
from split_district import build_adjacency                                   # noqa: E402


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--table", required=True, help="the zip table to staff (draw.csv)")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--keep", default=None, metavar="R1,R2,...",
                     help="the reps who stay; everyone else is released")
    grp.add_argument("--release", default=None, metavar="R3,R4,...",
                     help="the reps who leave; everyone else is kept")
    ap.add_argument("--theta", type=float, default=0.40)
    ap.add_argument("--lam", type=float, default=0.30)
    ap.add_argument("--filler-capture", default="full", choices=list(model.FILLER_CAPTURE),
                    help="how a kept rep capitalises unowned book, released book included "
                         "(default full: a vacancy has nobody left to pull business away)")
    ap.add_argument("--districts", default=None, metavar="D01,D05,...",
                    help="restrict this action to these districts; the rest keep the rep they "
                         "arrived with (default: every district of the table)")
    ap.add_argument("--multi", default=None, metavar="D02:3,D07:4",
                    help="districts to divide among more than one rep, requested roster size "
                         "each; every other district in scope gets a single rep")
    ap.add_argument("--exact", action="store_true",
                    help="also run the SCIP MINLP for every multi-rep district's split, "
                         "warm-started from the greedy answer")
    ap.add_argument("--time-limit", type=float, default=60.0,
                    help="SCIP time limit, seconds, applied uniformly to every multi-rep "
                         "district's split")
    ap.add_argument("--geom", default=None,
                    help="the run's geom.json; required when --multi is non-empty, its "
                         "cell_edges make every split contiguous on the Voronoi cell graph")
    ap.add_argument("--out", required=True, help="output directory")
    return ap


def _fail(out: str, reason: str) -> int:
    """Driver convention: `failure.json` with a reason, and a nonzero exit."""
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "failure.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(step="staff", reason=reason), fh, indent=2)
        fh.write("\n")
    print(f"staff: FAILED -- {reason}", file=sys.stderr, flush=True)
    return 1


def _parse_multi(spec: str | None) -> dict[str, int]:
    """`"D02:3,D07:4"` -> `{"D02": 3, "D07": 4}`; an empty or absent spec is `{}`."""
    out: dict[str, int] = {}
    for tok in (spec or "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if ":" not in tok:
            sys.exit(f"--multi entry {tok!r} needs a district:count pair")
        dist, n = tok.split(":", 1)
        dist = dist.strip()
        try:
            n = int(n.strip())
        except ValueError:
            sys.exit(f"--multi entry {tok!r}: the count must be an integer")
        if dist in out:
            sys.exit(f"--multi names district {dist!r} twice")
        out[dist] = n
    return out


def resolve_rosters(order: list[str], multi: dict[str, int],
                    candidates: dict[str, list[str]],
                    gain: dict[str, dict[str, float]]) -> dict[str, dict]:
    """For each district in `order` that `multi` names (district -> requested rep count), take
    its own top-N candidates by `gain[district][rep]`, descending, skipping any rep already
    claimed by an earlier district in `order`. Positive-gain candidates only. Returns
    `{district: {"roster": [rep,...], "requested": N, "resolved": len(roster)}}`; a district
    short of candidates after earlier claims takes what's left, down to zero -- never blocked,
    only reported short (`requested` vs `resolved`).

    A roster claims its reps against later districts in `order` only when it has two or more --
    a district that resolves to 0 or 1 is not going to become a real split (it falls through to
    the ordinary Hungarian match instead), so reserving its lone pick would only starve a later
    district that is genuinely going to split."""
    claimed: set[str] = set()
    out: dict[str, dict] = {}
    for d in order:
        if d not in multi:
            continue
        n = multi[d]
        pool = [r for r in candidates.get(d, [])
               if r not in claimed and gain.get(d, {}).get(r, 0.0) > 0]
        pool.sort(key=lambda r: gain[d][r], reverse=True)
        roster = pool[:n]
        if len(roster) >= 2:
            claimed.update(roster)
        out[d] = dict(roster=roster, requested=n, resolved=len(roster))
    return out


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    T = telemetry.Timings("staff")
    try:
        with T.phase("load"):
            d = descaled.load_descaled(args.instance)
            geo.assert_conus(d)

            rows = ziptable.read(args.table)
            to_district = {r["zip"]: r["district"] for r in rows if r["district"]}
            if not to_district:
                sys.exit(f"{args.table}: no labelled row, so there is nothing to staff")
            missing = sorted(z for z in to_district if z not in d.G)
            if missing:
                sys.exit(f"{len(missing)} zip(s) of the table are not in the instance "
                         f"(e.g. {missing[:5]})")
            k = len({r["district"] for r in rows if r["district"]})

            scope = staff._names(args.districts)
            if scope:
                unknown = sorted(set(scope) - set(to_district.values()))
                if unknown:
                    sys.exit(f"unknown district(s) {unknown}; the table has "
                             f"{sorted(set(to_district.values()))}")
                to_district = {z: dist for z, dist in to_district.items() if dist in scope}
            else:
                scope = sorted(set(to_district.values()))

            multi = _parse_multi(args.multi)
            unknown_multi = sorted(set(multi) - set(scope))
            if unknown_multi:
                sys.exit(f"--multi names district(s) {unknown_multi} outside scope {scope}")
            bad = {dist: n for dist, n in multi.items() if n < 2}
            if bad:
                sys.exit(f"--multi counts must be 2 or more; got {bad}")
            if multi and not args.geom:
                sys.exit("--multi needs --geom to build the contiguity adjacency")
            geom = None
            if args.geom:
                with open(args.geom, encoding="utf-8") as fh:
                    geom = json.load(fh)
                if multi and build_adjacency(geom, []) is None:
                    return _fail(args.out,
                                f"{args.geom} has no cells (a geom.json from before cells "
                                f"were exported)")

            all_reps = sorted(model.reps(d.G, sorted(d.G)))
            kept, released = staff.split_reps(all_reps, staff._names(args.keep),
                                              staff._names(args.release))
            if not kept:
                sys.exit("every rep is released; there is nobody left to staff the map")

            G = model.release_reps(d.G, released)

        with T.phase("books"):
            book, free = staff.district_books(G, to_district, kept)

        with T.phase("gain_matrix"):
            g, R, D = channel.gain_matrix(G, to_district, reps_order=kept, theta=args.theta,
                                          lam=args.lam, filler_capture=args.filler_capture)

        with T.phase("rosters"):
            held = {r["rep"] for r in rows if r["district"] and r["district"] not in scope
                    and r["rep"]}
            cands = {dist: [r for r in kept if r not in held
                            and book.get(dist, {}).get(r, 0.0) > 0] for dist in D}
            jd = {dist: j for j, dist in enumerate(D)}
            ir = {r: i for i, r in enumerate(R)}

            multi_gain = {dist: {r: float(g[ir[r], jd[dist]]) for r in cands[dist]}
                         for dist in multi}
            rosters = resolve_rosters(sorted(D), multi, cands, multi_gain)

            # A roster can never hold more reps than its district has zips (`split()` refuses
            # that outright); cap it here, keeping the top-gain reps `resolve_rosters` already
            # sorted to the front, and report the capped size as `resolved` -- the same "never
            # blocked, only reported short" rule a candidate shortfall already gets.
            n_zips_by_district: dict[str, int] = {}
            for dist in to_district.values():
                n_zips_by_district[dist] = n_zips_by_district.get(dist, 0) + 1
            for dist, entry in rosters.items():
                cap = n_zips_by_district.get(dist, len(entry["roster"]))
                if len(entry["roster"]) > cap:
                    entry["roster"] = entry["roster"][:cap]
                    entry["resolved"] = len(entry["roster"])

            # A district resolved to a real (2+-rep) roster is *attempted* as a split below;
            # whether it actually claims its reps exclusively depends on that attempt
            # succeeding, decided in the split phase, which runs before the Hungarian match
            # for exactly that reason -- a district whose split raises must fall through to
            # the ordinary match like any other single-rep district, not lose its reps to a
            # split that never happened (product decision: a single-rep district uses the
            # existing staffing logic, unchanged).
            split_ds = {dist for dist, entry in rosters.items() if entry["resolved"] >= 2}

        split_districts_out: dict = {}
        split_labels: dict = {}
        split_ok: set[str] = set()                     # districts whose split actually landed
        claimed: set[str] = set()                       # their reps, minus each split's own
                                                          # dropped_reps
        with T.phase("split"):
            for dist in sorted(split_ds):
                roster = rosters[dist]["roster"]
                inside = [r for r in rows if r["district"] == dist]
                zips = [r["zip"] for r in inside]
                masses_d = {r["zip"]: float(r["opportunity"]) for r in inside}
                u = district_split.unrestricted_utilities(
                    G, zips, roster, masses_d, theta=args.theta, lam=args.lam,
                    filler_capture=args.filler_capture)
                book_mat = district_split.book_matrix(G, zips, roster)
                M = np.array([masses_d[z] for z in zips], float)
                xy = np.array([[np.nan if r["x"] is None else r["x"],
                                np.nan if r["y"] is None else r["y"]] for r in inside], float)
                adjacency = build_adjacency(geom, zips) if geom is not None else None
                try:
                    res = district_split.split(u, M, xy, roster, book=book_mat, n_near=3,
                                               use_exact=args.exact, time_limit=args.time_limit,
                                               adjacency=adjacency)
                except (ValueError, ImportError) as exc:
                    # One district's split failing must not cost the whole run its output, and
                    # must not strand its reps either: this district falls through to the
                    # ordinary Hungarian match below (still to run), and none of its roster is
                    # ever added to `claimed`, so those reps stay free to staff it -- or
                    # anything else -- like any other candidate.
                    rosters[dist]["error"] = str(exc)
                    continue
                total = sum(res["gains"].values())
                split_districts_out[dist] = dict(
                    reps=res["reps"],
                    gains=res["gains"],
                    shares={r: (v / total if total > 0 else 0.0)
                           for r, v in res["gains"].items()},
                    objective=res["objective"],
                    method=res["method"],
                    gap=(None if res["gap"] is None or not math.isfinite(res["gap"])
                        else res["gap"]),
                    status=res["status"],
                    n_zips=len(zips),
                    dropped_reps=res["dropped_reps"],
                    pieces=res["pieces"],
                    contiguous=res["contiguous"],
                )
                split_labels[dist] = dict(zip(zips, res["labels"]))
                split_ok.add(dist)
                claimed.update(set(roster) - set(res["dropped_reps"]))

        with T.phase("assign"):
            bucket = [dist for dist in D if dist not in split_ok]
            bucket_cands = {dist: [r for r in cands[dist] if r not in claimed]
                            for dist in bucket}
            staffable = [dist for dist in bucket if bucket_cands[dist]]
            sub = g[:, [jd[dist] for dist in staffable]] if staffable else np.zeros((len(R), 0))
            ok = np.zeros(sub.shape, bool)
            for j, dist in enumerate(staffable):
                for r in bucket_cands[dist]:
                    ok[ir[r], j] = sub[ir[r], j] > 0
            pairs = staff.assign(sub, ok)

            assignment = {staffable[j]: R[i] for i, j in pairs}
            gains = {staffable[j]: float(sub[i, j]) for i, j in pairs}
            value = float(sum(math.log(v) for v in gains.values()))

        with T.phase("write"):
            unstaffed_districts = [dist for dist in D
                                   if dist not in assignment and dist not in split_ok]
            taken = set(assignment.values()) | held | claimed

            contest = {}
            for dist in D:
                total = sum(book.get(dist, {}).values()) + free.get(dist, 0.0)
                contest[dist] = dict(
                    candidates=cands[dist],
                    share={r: (book[dist][r] / total if total > 0 else 0.0)
                          for r in cands[dist]},
                    free_share=(free.get(dist, 0.0) / total if total > 0 else 0.0),
                    g={r: float(g[ir[r], jd[dist]]) for r in cands[dist]},
                )

            requested_multi = {
                dist: dict(requested_n=entry["requested"], resolved_n=entry["resolved"],
                          **({"error": entry["error"]} if "error" in entry else {}))
                for dist, entry in rosters.items()}

            out = dict(
                kept=kept, released=released, k=k, districts=scope,
                assignment=assignment, gains=gains, value=value,
                unmatched_reps=[r for r in R if r not in taken],
                unstaffed_districts=unstaffed_districts,
                balance=ziptable.balance(rows, k),
                contest=contest,
                split_districts=split_districts_out,
                requested_multi=requested_multi,
            )
            with open(os.path.join(args.out, "staffing.json"), "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2, default=float)
                fh.write("\n")

            out_rows = []
            for r in rows:
                dist = r["district"]
                if dist in split_labels:
                    out_rows.append(dict(r, rep=split_labels[dist].get(r["zip"], "")))
                elif dist in scope:
                    out_rows.append(dict(r, rep=assignment.get(dist, "")))
                else:
                    out_rows.append(r)
            ziptable.write(os.path.join(args.out, "draw.csv"), out_rows)

        T.write(args.out)

        print(f"k={k} kept={len(kept)} released={len(released)} "
              f"staffed={len(assignment)} split={len(split_ok)} "
              f"unstaffed={len(unstaffed_districts)} value={value:.6f}", flush=True)
        return 0
    finally:
        T.close()


if __name__ == "__main__":
    sys.exit(telemetry.maybe_profile(main)())
