"""staff.py -- staff a drawn map: which kept rep runs which district, and who contests it.

    .venv/bin/python3 -u tools/staff.py instance_descaled_v2_conus.json.gz \\
        --table battery/results/app/clip_.../d0.1/draw.csv --release R12,R31 \\
        --filler-capture full --out battery/results/app/staff_...

Stage 2 of the channel problem (`td/channel.py`) with two additions the review asked for.

Released reps.  A rep who leaves takes no book with them, so `model.release_reps` folds each
released rep's `S_i` into `S_free` at every zip and drops them from `cand`.  The reps who stay
then value that book at `c_free` rather than at `c2` -- at the default `--filler-capture full`,
at `c1`, the same rate as their own, because a vacancy has nobody left to pull business away.

Candidacy.  `channel.gain_matrix` evaluates every rep on every district by design (the map is
drawn first, so legacy candidacy does not restrict staffing).  The business rule here is
narrower: a rep may only be given a district they already sell in, i.e. `S_i(z) > 0` for some
zip `z` of it, books read *after* the fold.  A district no kept rep sells in is left unstaffed
rather than handed to the highest bidder, and the matching is Nash on the candidate pairs only.

The matching is the Hungarian algorithm on `-log g` (`channel.match`'s criterion), run here
directly because a non-candidate pair has to be excluded rather than scored.  Non-candidate
cells carry a penalty large enough that no optimal assignment uses one it could avoid, so the
result is a maximum-cardinality candidate matching that is Nash-optimal among those; any
penalised pair left over is dropped, and its district reads as unstaffed.

Writes `<out>/staffing.json` (the assignment, the per-district contest, balance) and
`<out>/draw.csv`, the input table with the `rep` column filled in on every row of a staffed
district.  Both carry the descaled masses the input table already carries; they live under
`battery/results/`, which is gitignored.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channel, geo, model, ziptable                                 # noqa: E402
from td import instance as descaled                                          # noqa: E402


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
                    help="restrict staffing to these districts; the rest keep the rep they "
                         "arrived with (default: every district of the table)")
    ap.add_argument("--out", required=True, help="output directory")
    return ap


def _names(spec: str | None) -> list[str]:
    """`"R1, R2"` -> `["R1", "R2"]`; an empty or absent spec is the empty list."""
    return [t.strip() for t in (spec or "").split(",") if t.strip()]


def split_reps(all_reps: list[str], keep: list[str], release: list[str]) -> tuple[list, list]:
    """`(kept, released)` from either flag, in `all_reps` order, unknown names refused.

    Neither flag means nobody leaves, which is the plain stage-2 run.
    """
    unknown = sorted((set(keep) | set(release)) - set(all_reps))
    if unknown:
        sys.exit(f"unknown rep(s) {unknown}; the instance has {len(all_reps)}")
    if keep:
        kept = set(keep)
    else:
        kept = set(all_reps) - set(release)
    return ([r for r in all_reps if r in kept], [r for r in all_reps if r not in kept])


def district_books(G, to_district, kept: list[str]) -> tuple[dict, dict]:
    """`({district: {rep: book}}, {district: free book})` over the table's zips.

    Books come off the released graph, so a released rep's production is already inside the
    free book and the shares below sum to 1 over the kept reps plus the filler.
    """
    book: dict = {}
    free: dict = {}
    for z, d in to_district.items():
        S = model.books(G, z)
        per = book.setdefault(d, {})
        for r in kept:
            s = float(S.get(r, 0.0))
            if s > 0:
                per[r] = per.get(r, 0.0) + s
        free[d] = free.get(d, 0.0) + model.free_book(G, z)
    return book, free


def assign(g: np.ndarray, ok: np.ndarray) -> list[tuple[int, int]]:
    """Nash matching on the pairs `ok` allows: `[(rep index, district index)]`.

    `linear_sum_assignment` matches `min(rows, cols)` cells whatever the costs, so forbidden
    cells cannot simply be dropped -- they are priced at `pen`, which is above anything a
    swap of allowed cells can recover.  The optimum therefore uses as few forbidden cells as
    possible, and those are filtered out here rather than reported as a staffing.
    """
    if g.size == 0 or not ok.any():
        return []
    with np.errstate(divide="ignore", invalid="ignore"):
        cost = -np.log(np.where(ok, g, 1.0))
    lo, hi = float(cost[ok].min()), float(cost[ok].max())
    n = min(g.shape)
    pen = hi + (n + 1) * (hi - lo + 1.0)
    cost = np.where(ok, cost, pen)
    rows, cols = linear_sum_assignment(cost)
    return [(int(i), int(j)) for i, j in zip(rows, cols) if ok[i, j]]


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

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

    scope = _names(args.districts)
    if scope:
        unknown = sorted(set(scope) - set(to_district.values()))
        if unknown:
            sys.exit(f"unknown district(s) {unknown}; the table has "
                     f"{sorted(set(to_district.values()))}")
        to_district = {z: dist for z, dist in to_district.items() if dist in scope}
    else:
        scope = sorted(set(to_district.values()))

    all_reps = sorted(model.reps(d.G, sorted(d.G)))
    kept, released = split_reps(all_reps, _names(args.keep), _names(args.release))
    if not kept:
        sys.exit("every rep is released; there is nobody left to staff the map")

    G = model.release_reps(d.G, released)
    book, free = district_books(G, to_district, kept)

    g, R, D = channel.gain_matrix(G, to_district, reps_order=kept, theta=args.theta,
                                  lam=args.lam, filler_capture=args.filler_capture)
    cands = {dist: [r for r in kept if book.get(dist, {}).get(r, 0.0) > 0] for dist in D}
    staffable = [dist for dist in D if cands[dist]]
    jd = {dist: j for j, dist in enumerate(D)}

    ir = {r: i for i, r in enumerate(R)}
    sub = g[:, [jd[dist] for dist in staffable]] if staffable else np.zeros((len(R), 0))
    ok = np.zeros(sub.shape, bool)
    for j, dist in enumerate(staffable):
        for r in cands[dist]:
            ok[ir[r], j] = sub[ir[r], j] > 0
    pairs = assign(sub, ok)

    assignment = {staffable[j]: R[i] for i, j in pairs}
    gains = {staffable[j]: float(sub[i, j]) for i, j in pairs}
    value = float(sum(math.log(v) for v in gains.values()))
    taken = set(assignment.values())

    contest = {}
    for dist in D:
        total = sum(book.get(dist, {}).values()) + free.get(dist, 0.0)
        contest[dist] = dict(
            candidates=cands[dist],
            share={r: (book[dist][r] / total if total > 0 else 0.0) for r in cands[dist]},
            free_share=(free.get(dist, 0.0) / total if total > 0 else 0.0),
            g={r: float(g[ir[r], jd[dist]]) for r in cands[dist]},
        )

    out = dict(
        kept=kept, released=released, k=k, districts=scope,
        assignment=assignment, gains=gains, value=value,
        unmatched_reps=[r for r in R if r not in taken],
        unstaffed_districts=[dist for dist in D if dist not in assignment],
        balance=ziptable.balance(rows, k),
        contest=contest,
    )
    with open(os.path.join(args.out, "staffing.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
        fh.write("\n")

    staffed = [dict(r, rep=(assignment.get(r["district"], "") if r["district"] in scope
                            else r["rep"]))
               for r in rows]
    ziptable.write(os.path.join(args.out, "draw.csv"), staffed)

    print(f"k={k} kept={len(kept)} released={len(released)} "
          f"staffed={len(assignment)} unstaffed={len(out['unstaffed_districts'])} "
          f"value={value:.6f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
