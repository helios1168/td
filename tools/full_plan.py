"""full_plan.py: the level-0 channel-plan driver (docs/FULL_PROBLEM.md sections 5 and 6).

    .venv/bin/python3 tools/full_plan.py instance_descaled_v2_conus.json.gz \\
        --route joint --driver geo --geo-cache data/geo \\
        --out battery/results/full_plan_joint

Reads the instance (format 1 or 2), splits the file's channels into the fine four
(`td.channels.fine_split`), aggregates them to the state-by-channel cells
(`td.channels.aggregate`), then solves the level-0 plan: which slot of which bundle takes
which share of which state's channel mass.  A format-1 file carries one channel and needs
`--synthesize`, which expands it with `td.channels.synthesize_channels` first.

Two readings of the priority order, both over the same model:

    --route sequential   one level-0 model per priority group (N, then WH, then FI), each
                         one's coverage fixed as the next one's `prior`
    --route joint        one model over every bundle, lexicographic passes cover_N, cover_WH,
                         cover_FI, cover_merged, contacts, compactness in the `balance_pass`
                         pattern

and two drivers over the result:

    --driver geo         an extent cap on every slot (`--n-max` states, `--dist-max` km
                         between state centroids, `--radius-max` km from the slot's own
                         root), linear and centre-free
    --driver reps        after the solve, the per-state moves {keep, merge WH+FI, drop N},
                         each re-solved with `z` fixed away from the state and its rook
                         neighbours and scored by the state-level stage-2 Nash value, over
                         the heaviest `--move-budget` states

`--catch-all` adds a last model over whatever the plan left uncovered: one single-channel
bundle per residual channel (`--catch-all-bundle each`), or one bundle over all four
(`--catch-all-bundle all`), a rep covering every channel in the states where every channel is
residual.  "Four channels" then means that pass used at least one slot.

The band is `1 -/+ --delta` around a mean.  Which mean is `--band-mode`: one national `tau =
national mass / k` (global), or each bundle's own `tau_B = M^max_B / k_B` from `--k-fixed`
(per-bundle, the default as soon as a count is given).  The counts differ by bundle -- the grid
runs national 10-18, WH 9-12, FI 16-20 -- and one band around the national mean would hold a
WH district to a national district's size.

Writes `params.json` (every argument), `plan.json` (the slots with their centre state and
hull metrics, the per-state shares and the residual, the pass log, the move log, the anchors),
`staffing.json` (`td.stage2_state.state_stage2` on the
final plan), `timings.json`, and one `projections/<bundle>/` per used bundle holding a format-1
instance for that bundle and the `state_shares.csv` level 2 reads.  A solve that returns
nothing usable writes `failure.json` in the shape `tools/state_splits.py` writes it and
re-raises, so the run exits nonzero and the reason survives the traceback.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import geo, model, telemetry                                        # noqa: E402
from td.solvers import state_splits as ss                                   # noqa: E402
import borders_report                                                       # noqa: E402
import run_draw                                                             # noqa: E402

# tools/state_splits.py's own defaults, for the same reasons (the bench winner, and the
# portfolio rather than one engine's whole time budget).
DEFAULT_ENGINE = "highs"
DEFAULT_STRATEGY = "portfolio"

# The band floor, as a fraction of L, of the last all-channel stage under --serve-all-states:
# a state outside every channel at the end is allocated whatever its mass, so the floor only
# keeps the slot count finite.
ALL_LAST_FLOOR = 1e-3

# The priority groups of `--priority`: which bundles a group's stage opens slots for.  N is
# alone; WH takes the pure and the national-carrying WH bundles; FI takes its own two plus the
# merged bundles, which are the last thing the priority order reaches.
STAGE_BUNDLES = {
    "N": ("N",),
    "WH": ("WH", "WH_PLUS"),
    "FI": ("FI", "FI_PLUS", "WHFI", "WHFI_PLUS"),
}

# The merged bundles: a slot of one serves a state's WH and its FI together.  They carry their
# own coverage pass in both routes, after the pure ones, so a merged slot is opened for what
# the pure channels could not serve and never in place of a pure district that fits.
MERGED_BUNDLES = ("WHFI", "WHFI_PLUS")

# Route joint's coverage passes.  cover_N counts pure national slots only (decision 8);
# cover_merged is what makes a WHFI slot worth opening, and without it route joint never
# merged anything (code verify R3, row 2b).
JOINT_COVER = (
    ("cover_N", ("N",)),
    ("cover_WH", ("WH", "WH_PLUS")),
    ("cover_FI", ("FI", "FI_PLUS")),
    ("cover_merged", MERGED_BUNDLES),
)

# The per-state moves of `--driver reps`: which bundles the move forbids the state from.
MOVES = {
    "keep": (),
    "merge_whfi": ("WH", "FI", "WH_PLUS", "FI_PLUS"),
    "drop_n": ("N",),
}

# The bundles the catch-all pass runs: one per fine channel, over whatever the earlier stages
# left.  A product bundle cannot do this job.  A slot of `WHFI_PLUS` sits in all four cover
# rows, so its share is bounded by `min_c cover_ub[s, c]`; once any channel of a state is
# served the catch-all can never open a slot there, and decision 1 ("a fourth channel exists
# iff the catch-all used a slot") would always answer no for the wrong reason.
CATCH_ALL_BUNDLES = {"OTHER_N_WH": ("N_WH",), "OTHER_N_FI": ("N_FI",),
                     "OTHER_WH": ("WH",), "OTHER_FI": ("FI",)}


def _parse_k_fixed(text: str) -> dict[str, int]:
    """`"N=18,WH=11"` -> `{"N": 18, "WH": 11}`; the bundle names are checked in `_main`."""
    out = {}
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        name, _, count = item.partition("=")
        if not count.strip().isdigit():
            raise argparse.ArgumentTypeError(f"expected BUNDLE=COUNT, got {item!r}")
        out[name.strip()] = int(count)
    return out


def _parse_states(text: str) -> list[str]:
    """`"MT, WA,WY"` -> `["MT", "WA", "WY"]`, upper-cased; membership is checked in `_main`."""
    out = [item.strip().upper() for item in text.split(",") if item.strip()]
    if not out:
        raise argparse.ArgumentTypeError("expected at least one state code")
    return out


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz), format 1 or 2")
    ap.add_argument("--route", choices=("sequential", "joint"), default="sequential",
                    help="how the priority order is read (default sequential)")
    ap.add_argument("--driver", choices=("reps", "geo"), default="geo",
                    help="what merges bundles: an extent cap (geo) or the per-state moves "
                         "scored by state-level stage 2 (reps); default geo")
    ap.add_argument("--catch-all", action="store_true", default=False,
                    help="a last model over the residual with one bundle of all four channels")
    ap.add_argument("--catch-all-bundle", choices=("each", "all"), default="each",
                    help="what the catch-all districts: one single-channel bundle per residual "
                         "fine channel (each, the default), or one bundle over all four "
                         "(all, WHFI_PLUS), one rep covering every channel in the states where "
                         "every channel is still residual")
    ap.add_argument("--k", type=int, default=18,
                    help="tau = national mass / k (default 18, today's committed k)")
    ap.add_argument("--band-lo", type=float, default=0.8,
                    help="L = band_lo * tau (default 0.8, the $800MM floor)")
    ap.add_argument("--band-hi", type=float, default=1.2,
                    help="U = band_hi * tau (default 1.2, the $1.2B cap)")
    ap.add_argument("--delta", type=float, default=None, metavar="D",
                    help="band half-width: band_lo = 1 - D, band_hi = 1 + D. Overrides "
                         "--band-lo/--band-hi when given (the grid runs 0.05 to 0.10)")
    ap.add_argument("--band-mode", choices=("global", "per-bundle"), default=None,
                    help="one band over the national tau (global), or each bundle banded on "
                         "its own mean, tau_B = M^max_B / k_B from --k-fixed (per-bundle). "
                         "Default per-bundle when --k-fixed names a count, global otherwise")
    ap.add_argument("--bundles", default=None, metavar="B,B,...",
                    help="the bundles slots may carry (default td.channels.DEFAULT_BUNDLES)")
    ap.add_argument("--priority", default="N,WH,FI", metavar="G,G,...",
                    help="priority groups, in order (default N,WH,FI)")
    ap.add_argument("--eta", type=float, default=0.01,
                    help="minimum share a state flagged z_sj=1 must actually send")
    ap.add_argument("--move-budget", type=int, default=20, metavar="N",
                    help="driver reps: visit at most N states, heaviest first (default 20). "
                         "Each state costs one MILP per move, so 49 states is about 98 solves")
    ap.add_argument("--cover-slack", type=float, default=0.0, metavar="EPS",
                    help="driver reps: a move may give up this fraction of each coverage "
                         "pass's value, its pin widened to v*(1-EPS) for the move's re-solve "
                         "only. The plan the passes produce is the same at every EPS "
                         "(default 0.0, no room and no merge)")
    ap.add_argument("--n-max", type=int, default=None,
                    help="driver geo: at most this many states per slot")
    ap.add_argument("--dist-max", type=float, default=None, metavar="KM",
                    help="driver geo: two states more than KM apart by centroid may not share "
                         "a slot (needs the state polygons from --geo-cache)")
    ap.add_argument("--radius-max", type=float, default=None, metavar="KM",
                    help="driver geo: a slot reaches at most KM from its own root by state "
                         "centroid, as a bound on z; a slot whose root is free takes the "
                         "pairwise diameter bound 2*KM instead (needs --geo-cache polygons)")
    ap.add_argument("--prior", default=None, metavar="PLAN.json",
                    help="a previous plan.json whose coverage is held as already served")
    ap.add_argument("--centers", default=None, metavar="DRAW.csv|seeds",
                    help="where the compactness tie-break's moments come from: a committed "
                         "draw whose centres give them on the N slots, or `seeds`, every used "
                         "slot's own greedy seed (both together with --incumbency: the draw "
                         "keeps the N slots, the seeds carry the rest). Without it no "
                         "compactness pass runs")
    ap.add_argument("--incumbency", default=None, metavar="DRAW.csv",
                    help="a committed draw whose district home states anchor the N slots")
    ap.add_argument("--committed-instance", default=None, metavar="INSTANCE",
                    help="the instance --centers/--incumbency were drawn on, when it is not "
                         "the one being planned (the committed k=18 draw is on the v2 CONUS "
                         "file; the v3 file carries zips it never labelled)")
    ap.add_argument("--theta", type=float, default=borders_report.THETA,
                    help="stage-2 rep utility weight; scores the plan, changes no geometry")
    ap.add_argument("--lam", type=float, default=borders_report.LAM,
                    help="stage-2 rep utility weight; scores the plan, changes no geometry")
    ap.add_argument("--filler-capture", choices=list(model.FILLER_CAPTURE),
                    default=borders_report.FILLER_CAPTURE,
                    help="stage-2 filler capture rule; scores the plan, changes no geometry")
    ap.add_argument("--warm", choices=("greedy", "none"), default="greedy",
                    help="start every model's first pass from level0.greedy_plan's feasible "
                         "point (default greedy); the plan.json pass log opens with it")
    ap.add_argument("--anchor", choices=("greedy", "none"), default="none",
                    help="anchor every used slot at its greedy seed (z fixed there, root "
                         "fixed there); --incumbency keeps precedence on the N slots. "
                         "Refused with --driver reps (default none)")
    ap.add_argument("--k-fixed", type=_parse_k_fixed, default=None, metavar="B=N,B=N,...",
                    help="fix the first N slots of bundle B as used, e.g. N=18,WH=11,FI=19; "
                         "a bundle not named stays free (default none)")
    ap.add_argument("--k-mode", choices=("fixed", "cap"), default="fixed",
                    help="how --k-fixed binds: 'fixed' uses exactly N slots; 'cap' opens at "
                         "most N and lets a pass drop districts a cap makes infeasible. Both "
                         "band a bundle on its own mean M_B / N under --band-mode per-bundle "
                         "(default fixed)")
    ap.add_argument("--serve-all-states", action="store_true",
                    help="no state with mass ends outside every channel: rows sum_j z_sj >= 1 "
                         "on the joint model; on route S a last all-channel stage allocates "
                         "whatever the stages and the catch-all left, one district per state "
                         "at most, whatever its mass (default off)")
    ap.add_argument("--other-first", type=_parse_states, default=None, metavar="ST,ST,...",
                    help="before the channel stages, open all-channel (WHFI_PLUS) districts "
                         "that serve these states, as few contacts as the band allows, at "
                         "most one district per state named; the channel stages then run on "
                         "what is left. The route-S answer to a state no channel can serve "
                         "on its own under a cap (default none)")
    ap.add_argument("--other-floor", type=float, default=1.0, metavar="F",
                    help="the catch-all stage's band floor as a fraction of L: an 'other' "
                         "district, one person over every channel of a sparse region, may "
                         "hold F of a full book (default 1.0)")
    ap.add_argument("--engine", choices=("scipy", "highs", "scip"), default=DEFAULT_ENGINE,
                    help=f"MILP engine (default {DEFAULT_ENGINE})")
    ap.add_argument("--strategy", choices=("direct", "portfolio"), default=DEFAULT_STRATEGY,
                    help="strategy for the contacts pass, whose objective is unit cost on z; "
                         "the coverage and compactness passes always run direct (default "
                         f"{DEFAULT_STRATEGY})")
    ap.add_argument("--threads", type=int, default=None,
                    help="solver threads (highs/scip only; the portfolio parent solves with 2 "
                         "and HiGHS sizes its pool once per process, trap 18, so leave this "
                         "unset with --strategy portfolio)")
    ap.add_argument("--time-limit", type=float, default=300.0,
                    help="seconds per pass; an unclosed pass pins its incumbent and records "
                         "certified=false")
    ap.add_argument("--synthesize", action="store_true", default=False,
                    help="expand a one-channel instance with td.channels.synthesize_channels")
    ap.add_argument("--seed", type=int, default=0, help="--synthesize seed (default 0)")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--out", required=True, help="output directory")
    return ap


# ------------------------------------------------------------------------------- state geometry
def _state_list(d) -> list[str]:
    """The state codes the instance actually carries, sorted.

    Taken from the instance rather than `borders_report._STATE_LIST` so a toy runs: the real
    CONUS instance's states are that list, and `_state_edges` refuses any code the rook graph
    does not know.
    """
    codes = sorted({str(d.G.nodes[z].get("state") or "") for z in d.G})
    codes = [c for c in codes if c]
    if not codes:
        raise ValueError("the instance carries no state codes; level 0 has nothing to cut")
    return codes


def _state_edges(state_list: list[str], geo_cache: str) -> list[tuple[int, int]]:
    """The state rook graph (`td.geo.state_rook`) on `state_list`'s indices."""
    adj, _ = geo.state_rook(geo_cache)
    idx = {c: i for i, c in enumerate(state_list)}
    stray = sorted(set(state_list) - set(adj))
    if stray:
        raise ValueError(f"states not in the rook graph: {stray}")
    return sorted({(min(idx[a], idx[b]), max(idx[a], idx[b]))
                   for a, nbrs in adj.items() if a in idx
                   for b in nbrs if b in idx})


def _state_xy(state_list: list[str], geo_cache: str, *, required: bool = True):
    """State centroids in km: what `--dist-max`, `--radius-max` and `--centers seeds` measure
    between, and what the plan's `extent_km` and `radius_km` are reported in.

    `required=False` returns None when the cache has no polygon for some state, so a run that
    only wants the hull metrics does not die for want of geometry it can do without.
    """
    _, polys = geo.state_rook(geo_cache)
    missing = sorted(c for c in state_list if c not in polys)
    if missing:
        if not required:
            return None
        raise ValueError(f"--dist-max, --radius-max and --centers seeds need a polygon for "
                         f"every state; missing {missing}")
    return np.array([[polys[c].centroid.x / 1000.0, polys[c].centroid.y / 1000.0]
                     for c in state_list], float)


def _rook_neighbours(edges: list[tuple[int, int]], n_state: int) -> list[set[int]]:
    nbr: list[set[int]] = [set() for _ in range(n_state)]
    for a, b in edges:
        nbr[a].add(b)
        nbr[b].add(a)
    return nbr


# ------------------------------------------------------------------- the committed draw, if any
def _committed(args, cache: dict):
    """`borders_report.load_committed` for `--centers`/`--incumbency`, loaded at most once.

    `--centers seeds` names no draw, so it is the `--incumbency` path that carries one there.
    """
    path = (args.centers if args.centers not in (None, "seeds") else None) or args.incumbency
    if path is None:
        return None
    if "ctx" not in cache:
        inst = args.committed_instance or args.instance
        cache["ctx"] = borders_report.load_committed(inst, path, args.geo_cache)
    return cache["ctx"]


def _anchors_from_draw(ctx, state_list: list[str], start: int, stop: int):
    """`[(state index, slot)]` holding district j of the committed draw in its home state.

    Slot `start + j` of the N bundle is district `j`, so this is `tools/state_splits.py`'s
    `--anchor-homes` moved onto the level-0 slot numbering.
    """
    idx = {c: i for i, c in enumerate(state_list)}
    anchors = []
    for j in range(ctx.k):
        s = int(ctx.home[j])
        if s < 0 or start + j >= stop:
            continue
        code = ctx.state_list[s]
        if code in idx:
            anchors.append((idx[code], start + j))
    return anchors


def _moments_from_draw(ctx, state_list: list[str], n_state: int, n_slot: int,
                       start: int, stop: int) -> np.ndarray:
    """`D[s, j]`, state `s`'s exact moment about the committed centre of slot `j`.

    Only the N slots get a centre (they are the committed draw's own districts); every other
    slot's column is zero, which is what "contacts only" means for that bundle.
    """
    from td.solvers import centers

    C = centers._centroids(ctx.xy, ctx.M, ctx.labels0, ctx.k)
    known = ctx.state_idx >= 0
    d2 = ((ctx.xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    num = np.zeros((len(ctx.state_list), ctx.k), float)
    np.add.at(num, ctx.state_idx[known], ctx.M[known, None] * d2[known])
    M_s = np.bincount(ctx.state_idx[known], weights=ctx.M[known],
                      minlength=len(ctx.state_list)).astype(float)
    D_ctx = np.divide(num, M_s[:, None], out=np.zeros_like(num), where=M_s[:, None] > 0)

    idx = {c: i for i, c in enumerate(state_list)}
    D = np.zeros((n_state, n_slot), float)
    for s_ctx, code in enumerate(ctx.state_list):
        if code not in idx:
            continue
        for j in range(min(ctx.k, stop - start)):
            D[idx[code], start + j] = D_ctx[s_ctx, j]
    return D


# --------------------------------------------------------------------------------- plan records
def _bundle_name(b) -> str:
    """A slot's bundle as a name.  `Level0Problem.bundle_of` may hold either."""
    from td import channels

    if isinstance(b, str):
        return b
    want = tuple(b)
    for name, chans in channels.BUNDLES.items():
        if tuple(chans) == want:
            return name
    raise ValueError(f"bundle {b!r} is not one of {sorted(channels.BUNDLES)}")


def _bundle_table() -> dict:
    """`td.channels.BUNDLES` plus this driver's own catch-all bundles."""
    from td import channels

    return {**channels.BUNDLES, **CATCH_ALL_BUNDLES}


def _bundle_channels(b) -> tuple:
    return tuple(_bundle_table()[b]) if isinstance(b, str) else tuple(b)


def _coverage(y: np.ndarray, bundle_of, channel_idx: dict[str, int]) -> np.ndarray:
    """`(S, C)`: how much of each state-channel cell the slots of this solve cover."""
    S, K = y.shape
    cov = np.zeros((S, len(channel_idx)), float)
    for j in range(K):
        for c in _bundle_channels(bundle_of[j]):
            cov[:, channel_idx[c]] += y[:, j]
    return cov


def _slot_records(problem, result, state_list: list[str], next_id: int, *,
                  state_xy=None, roots=None) -> list[dict]:
    """One record per slot of this solve, with a plan-wide id.

    `L` and `U` are the band this slot was actually held to, its bundle's own under
    `--band-mode per-bundle` and the national one otherwise.  `center` is the state the slot is
    rooted or seeded at (`roots`, slot -> state index),
    `extent_km` the widest centroid distance between two states it contacts and `radius_km` the
    widest from that centre.  All three are reported and none is constrained: the grid's Plans
    tab ranks shapes off them without re-reading the geometry.  `extent_km` and `radius_km` are
    null without `state_xy` (a geo cache with no state polygons), and `center` and `radius_km`
    are null for a slot with no known centre -- under `--driver reps` a move re-solves the
    contacts and the stage's seed may no longer be one of them.
    """
    z = np.asarray(result["z"])
    y = np.asarray(result["y"], float)
    u = np.asarray(result["u"])
    masses = np.asarray(result["masses"], float)
    xy = None if state_xy is None else np.asarray(state_xy, float)
    roots = roots or {}
    out = []
    for j in range(problem.k):
        shares = {state_list[s]: round(float(y[s, j]), 6)
                  for s in np.flatnonzero(z[:, j]) if y[s, j] > 0.0}
        touched = np.flatnonzero(z[:, j])
        root = roots.get(j)
        extent = radius = None
        if xy is not None and len(touched):
            pts = xy[touched]
            extent = round(float(np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2)
                                         .sum(axis=2)).max()), 3)
            if root is not None:
                radius = round(float(np.sqrt(((pts - xy[root]) ** 2).sum(axis=1)).max()), 3)
        out.append(dict(id=f"P{next_id + j:03d}", bundle=_bundle_name(problem.bundle_of[j]),
                        used=bool(u[j]), mass=float(masses[j]),
                        contacts=int(z[:, j].sum()), y=shares,
                        L=float(problem.L_j[j]), U=float(problem.U_j[j]),
                        center=None if root is None else state_list[root],
                        extent_km=extent, radius_km=radius))
    return out


def _plan_object(slots: list[dict], state_list: list[str]):
    """The `td.stage2_state.Plan` the state-level stage 2 scores.

    `Slot.bundle` is the channel tuple, not the name, so the utility sums the right cells.
    """
    from td import stage2_state

    return stage2_state.Plan(
        slots=[stage2_state.Slot(bundle=_bundle_channels(r["bundle"]), y=dict(r["y"]),
                                 used=r["used"])
               for r in slots],
        state_list=list(state_list))


# ------------------------------------------------------------------------------------- failures
def _write_failure(out: str, stage: str, exc, solve_s: float) -> str:
    """The record `tools/state_splits.py::_write_failure` writes, for the same reader.

    `app/headline.py::failure` keys off `reason` (`infeasible` is a proof, `no_incumbent` is a
    search that ran out of time) and the seconds beside it, so the keys are the same here.
    `delta` is None: level 0 has a band, not a single delta.

    `td.solvers.level0.solve_passes` attaches `passes`, the log up to the pass that died, when
    it has one; the key is only written then, so a failure from anywhere else keeps exactly
    the record `tools/state_splits.py` writes.
    """
    path = os.path.join(out, "failure.json")
    rec = dict(cell=stage, delta=None, reason=getattr(exc, "reason", "other"),
               status=getattr(exc, "status", None),
               message=getattr(exc, "solver_message", str(exc)),
               solve_seconds=round(solve_s, 1))
    passes = getattr(exc, "passes", None)
    if passes:
        rec["passes"] = [dict(p, stage=stage) for p in passes]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, default=float)
        fh.write("\n")
    print(f"{stage}: no solution, reason={getattr(exc, 'reason', 'other')} "
          f"({solve_s:.1f}s solve); wrote {path}", flush=True)
    return path


# ---------------------------------------------------------------------------------- the passes
def _stage_cover(group: str, bundle_names) -> list:
    """Route sequential's cover groups for one priority stage: the pure bundles, then the
    merged ones.  Only the FI stage carries merged bundles (`STAGE_BUNDLES`), and splitting
    them off is what stops a WHFI slot standing in for a pure FI district that fits.
    """
    pure = [b for b in bundle_names if b not in MERGED_BUNDLES]
    merged = [b for b in bundle_names if b in MERGED_BUNDLES]
    groups = []
    if pure:
        groups.append((f"cover_{group}", pure))
    if merged:
        groups.append(("cover_merged", merged))
    return groups


def _pass_list(problem, cover_groups, *, cover_last: bool = False) -> list:
    """The lexicographic passes of one model: coverage, then contacts, then compactness.

    A cover group naming bundles this model has no slots for is dropped, so the catch-all
    model runs its own single cover pass and not route joint's four.  `solve_passes` is what
    applies `--strategy` to the contacts pass alone, so every pass goes in one call.

    `cover_last` puts the cover passes after the contacts pass: the `other_first` stage wants
    the fewest states that serve the named ones, and only then as much of their mass as the
    band holds, so a named state is not left 74% in its all-channel district and 26% in the
    next stage's.

    Every pass is pinned exactly (`Pass.slack` stays 0): `--cover-slack` is spent by a route-R
    move and by nothing else, so the plan a given instance produces does not depend on it.
    """
    from td.solvers import level0

    cover = []
    for name, bundles in cover_groups:
        bs = [b for b in bundles if b in problem.slots]
        if bs:
            cover.append(level0.cover_pass(problem, bs, name=name))
    contacts = [level0.contacts_pass(problem)]
    passes = contacts + cover if cover_last else cover + contacts
    # no centres, no moments, no tie-break: the plan is contacts only (section 6, route J).
    D = getattr(problem, "D", None)
    if D is not None and np.size(D) and float(np.abs(D).max()) > 0.0:
        passes.append(level0.compactness_pass(problem))
    return passes


def _run_passes(problem, passes, args, stage: str, T, *, warm=None,
                warm_seconds: float = 0.0) -> dict:
    """One `solve_passes` call; each pass pins its own value before the next.  `warm` is the
    greedy point the first pass starts from (`--warm greedy`), `warm_seconds` its build time."""
    from td.solvers import level0

    t0 = time.time()
    with T.phase("solve") as ph:
        try:
            result = level0.solve_passes(problem, passes, engine=args.engine,
                                         strategy=args.strategy, time_limit=args.time_limit,
                                         threads=args.threads, warm_start=warm,
                                         warm_seconds=warm_seconds)
        except ss.SolveFailure as exc:
            _write_failure(args.out, stage, exc, time.time() - t0)
            raise
        ph.note(stage=stage, strategy=args.strategy,
                passes=[p["name"] for p in result["passes"]])
    for rec in result["passes"]:
        v = rec["value"]
        shown = (", ".join(f"{b}={m:.6g}" for b, m in v.items()) if isinstance(v, dict)
                 else f"{v:.6g}")
        print(f"{stage}/{rec['name']}: value={shown} "
              f"certified={rec['certified']} status={rec['status']} "
              f"({rec['seconds']:.1f}s)", flush=True)
    result = dict(result)
    result["passes"] = [dict(rec, stage=stage) for rec in result["passes"]]
    return result


def _stage_bands(cells, bundle_names, args, *, band_lo, band_hi, tau, prior, mode):
    """`({bundle: (L_B, U_B)} or None, {bundle: {tau, L, U}})` for one stage.

    Under `global` every bundle takes the national band, and the band dict is None so the model
    is built exactly as it was before there were any others.  Under `per-bundle` a bundle
    `--k-fixed` names a count for takes its own mean, `tau_B = M^max_B / k_B` over the mass it
    could still hold under `prior`; a bundle with no count (WH+, FI+, WHFI, the catch-all
    bundles) takes the mass-weighted mean of the fixed bundles' `tau_B` in this stage, and the
    national `tau` when the stage fixes none.  The band is `(band_lo, band_hi) * tau_B`, so
    `--delta` is what sets its width in both modes.
    """
    from td.solvers import level0

    avail = level0.available_mass(cells, {b: _bundle_channels(b) for b in bundle_names},
                                  prior=prior)
    fixed = args.k_fixed or {}
    taus = {b: avail[b] / int(fixed[b]) for b in bundle_names
            if mode == "per-bundle" and int(fixed.get(b, 0)) > 0 and avail[b] > 0}
    weight = sum(avail[b] for b in taus)
    shared = (sum(avail[b] * taus[b] for b in taus) / weight) if weight > 0 else float(tau)
    record = {}
    for b in bundle_names:
        t = taus.get(b, shared) if mode == "per-bundle" else float(tau)
        record[b] = dict(tau=t, L=band_lo * t, U=band_hi * t)
    if mode != "per-bundle":
        return None, record
    return {b: (rec["L"], rec["U"]) for b, rec in record.items()}, record


def _build(cells, bundle_names, args, *, L, U, edges, prior, anchors, D, state_xy, band=None,
           serve=None, max_used=None):
    """`build_level0` with the driver's own switches applied.

    `order_mass` is off under `--driver reps`: a move's neighbourhood fixes `z` per slot, and
    the mass ordering inside a bundle is only valid while its slots are interchangeable.
    `--n-max`, `--dist-max` and `--radius-max` are honoured under both drivers; `params.json`
    records them either way, so dropping them under `reps` would make that record untrue.
    `--k-fixed`
    applies to the bundles this model carries; a named bundle in another stage's model is
    that stage's business.
    """
    from td.solvers import level0

    fixed = {b: n for b, n in (args.k_fixed or {}).items() if b in bundle_names}
    cap = getattr(args, "k_mode", "fixed") == "cap"
    problem = level0.build_level0(
        cells, {b: _bundle_channels(b) for b in bundle_names},
        edges=edges, L=L, U=U, band=band, eta=args.eta,
        n_max=args.n_max, dist_max=args.dist_max, radius_max=args.radius_max,
        state_xy=state_xy, prior=prior, anchors=anchors, D=D,
        order_mass=False if args.driver == "reps" else None,
        fixed_used=None if cap else (fixed or None),
        max_used=max_used or (fixed if cap and fixed else None))
    # `serve` names the states this stage must put into some district (`--serve-all-states`)
    return level0.serve_states(problem, serve) if serve else problem


def _print_slots(problem, stage: str) -> None:
    total = 0
    for name, (start, stop) in sorted(problem.slots.items()):
        band = (f" band=[{problem.L_j[start]:.6g}, {problem.U_j[start]:.6g}]"
                if stop > start else "")
        print(f"{stage}: slots[{name}] = {stop - start}{band}", flush=True)
        total += stop - start
    print(f"{stage}: {total} slots total, {problem.n_state} states", flush=True)


# ------------------------------------------------------------------------------- driver reps
def _relax_pins(problem, names, widen=(), slack: float = 0.0):
    """A copy of `problem` with the `names` pin rows opened to +inf and the `widen` ones
    moved out by `|bound| * slack`.

    `solve_passes` pins every pass's value with an appended row.  A move must keep the
    coverage pins -- they are what says the plan still serves what it served, and without them
    minimising contacts closes every slot and the "best" move is the empty plan -- but it must
    drop `pin_contacts`, which says "no more contacts than the unmerged plan used" and is what
    makes every merge infeasible.  Relaxing rather than deleting keeps the matrix shape, so
    every offset and every later `append_row` still lines up.

    `slack` is `--cover-slack`, applied here and not when the pin is written: the base plan is
    then the same at every EPS, and the coverage a move may give up is the only thing the flag
    changes.  The bound is the minimised value plus a margin of `|v| 1e-9 + 1e-12`, so
    `|bound| * slack` is `|v| * slack` to that margin.
    """
    ub = np.array(problem.ub, float)
    for name in names:
        lo, hi = problem.rows[name]
        ub[lo:hi] = np.inf
    if slack:
        for name in widen:
            lo, hi = problem.rows[name]
            ub[lo:hi] += np.abs(ub[lo:hi]) * float(slack)
    return dataclasses.replace(problem, ub=ub)


def _z_fix_away(problem, z: np.ndarray, keep: set[int]) -> None:
    """Fix `z` on every slot touching neither the moved state nor its rook neighbours.

    A move changes contacts, so the re-solve cannot fix `z` everywhere; fixing it away from the
    state's own neighbourhood is what makes the move a small MILP instead of the whole model
    again (docs/FULL_PROBLEM.md section 6, route R).
    """
    for j in range(problem.k):
        if any(z[s, j] for s in keep):
            continue
        for s in range(problem.n_state):
            v = float(z[s, j])
            ss.bound_z(problem, s, j, v, v)


def _rep_moves(problem, result, cells, state_list, edges, args, prefix, slots, next_id,
               T, state_xy=None) -> tuple[list[dict], dict]:
    """The per-state moves {keep, merge WH+FI, drop N}, scored by state-level stage 2.

    A move only re-solves the last model, but the score is the whole plan's: the rep
    constraint is the one thing that couples the bundles, so stage 2 runs over `prefix`, the
    slots the earlier stages fixed, plus the moved model's own.

    Kept deliberately simple: one neighbourhood re-solve of the contacts pass per move, the
    best move applied to the running problem, states visited in descending total mass and cut
    at `--move-budget`.  Wave 3 tunes the order and the neighbourhood.
    """
    from td import stage2_state
    from td.solvers import level0

    # a merge changes the contact count, so `pin_contacts` (and the compactness pin behind it)
    # would refuse every non-keep move; the coverage pins stay, or the empty plan wins.
    # `--cover-slack EPS` widens those coverage pins by |v| EPS, and that is the only room a
    # merge has: a merged slot's coverage counts in cover_merged, never in cover_WH or cover_FI,
    # so a merge gives up the whole of that state's share of the pure objectives.
    # TODO: comparing two plans with different district counts by the Nash sum is ★C territory.
    # A merge closes a district and frees a rep, and `sum log g` over the staffed districts has
    # one term fewer, so the two numbers are not like for like.  The move log's `value` is
    # comparable across moves that keep the district count and not across moves that change it.
    pins = [n for n in problem.rows if n.startswith("pin_")]
    problem = _relax_pins(problem, [n for n in pins if not n.startswith("pin_cover")],
                          widen=[n for n in pins if n.startswith("pin_cover")],
                          slack=args.cover_slack)
    nbr = _rook_neighbours(edges, problem.n_state)
    # The moves reach the last model only, so under --route sequential the N slots are in an
    # earlier model and "drop N" cannot be expressed; it is logged as not evaluable rather
    # than dropped.  Route joint has every bundle in one model and does evaluate it.
    enabled = set(problem.slots)
    order = sorted(range(problem.n_state), key=lambda s: (-float(cells.M[s].sum()),
                                                          state_list[s]))
    budget = max(int(args.move_budget), 0)
    if len(order) > budget:
        print(f"moves: {len(order)} states, visiting the {budget} heaviest "
              f"(--move-budget)", flush=True)
        order = order[:budget]
    log: list[dict] = []
    base_slots = slots

    def score(stage_slots) -> float:
        out = stage2_state.state_stage2(cells, _plan_object(prefix + stage_slots, state_list),
                                        theta=args.theta, lam=args.lam,
                                        filler_capture=args.filler_capture,
                                        criterion="nash", candidacy=False)
        return float(out["value"])

    try:
        base = stage2_state.state_stage2(cells, _plan_object(prefix + base_slots, state_list),
                                         theta=args.theta, lam=args.lam,
                                         filler_capture=args.filler_capture,
                                         criterion="nash", candidacy=False)
    except ValueError as exc:
        print(f"moves: the level-0 plan does not score at state grain ({exc}); no move run",
              flush=True)
        return log, dict(problem=problem, result=result, slots=base_slots)
    best_value = float(base["value"])

    # every accepted forbid, replayed onto the unpinned base for each new trial: `bound_z`
    # writes into the problem it is handed, so a trial must never be built on a previous
    # trial or the earlier state's z-fixes would still be binding
    applied: list[tuple[int, str]] = []

    for s in order:
        keep = {s} | nbr[s]
        candidates = []
        for move, forbidden in MOVES.items():
            forbidden = [b for b in forbidden if b in enabled]
            if move != "keep" and not forbidden:
                # under route sequential the N slots belong to an earlier model, so "drop N"
                # is not expressible here; say so rather than leaving it out of the log
                log.append(dict(state=state_list[s], move=move, value=None,
                                status="not_evaluable_under_sequential", accepted=False))
                continue
            if move == "keep":
                candidates.append((move, best_value, None, None, ()))
                continue
            trial = problem
            for s_i, b in [*applied, *((s, b) for b in forbidden)]:
                trial = level0.forbid_bundle(trial, s_i, b)   # copies var_lb/var_ub
            _z_fix_away(trial, np.asarray(result["z"]), keep)
            try:
                with T.phase("move_solve"):
                    out = level0.solve_passes(trial, [level0.contacts_pass(trial)],
                                              engine=args.engine, strategy="direct",
                                              time_limit=args.time_limit,
                                              threads=args.threads)
                trial_slots = _slot_records(trial, out, state_list, next_id,
                                            state_xy=state_xy)
                value = score(trial_slots)
            except (ss.SolveFailure, ValueError) as exc:
                # no map under the forbid, or a slot the move leaves unstaffable.  A pin
                # collision cannot happen any more: the trial is built on the unpinned model.
                log.append(dict(state=state_list[s], move=move, value=None,
                                status=getattr(exc, "reason", type(exc).__name__),
                                accepted=False))
                continue
            candidates.append((move, value, trial, out, tuple(forbidden)))

        move, value, trial, out, forbidden = max(candidates, key=lambda c: c[1])
        # a no-op move (nothing of the state's mass is in a forbidden bundle) re-solves to the
        # incumbent's own optimum, and the solver can report it a few ulps apart; without a
        # tolerance that tie is recorded as an acceptance the move did not earn
        accepted = move != "keep" and value > best_value + 1e-9 * max(1.0, abs(best_value))
        for name, val, *_ in candidates:
            log.append(dict(state=state_list[s], move=name, value=val,
                            accepted=bool(accepted and name == move)))
        print(f"move {state_list[s]}: best={move} value={value:.6g} "
              f"accepted={accepted}", flush=True)
        if accepted:
            applied.extend((s, b) for b in forbidden)
            result = out
            base_slots = _slot_records(trial, out, state_list, next_id, state_xy=state_xy)
            best_value = value

    return log, dict(problem=problem, result=result, slots=base_slots)


# ------------------------------------------------------------------------------- the projections
def _write_projections(out: str, d, cells, slots: list[dict], state_list: list[str],
                       T) -> list[str]:
    """One format-1 instance and one `state_shares.csv` per bundle the plan actually used.

    `target_mass` is `M^B_s * y_sj`, the state's own mass in that bundle times the share the
    slot asks for, which is what `tools/state_splits.py::write_state_shares` means by the
    column and what level 2 turns into zip labels.  Summed over a bundle's rows it is that
    bundle's total slot mass.
    """
    from td import channels

    cidx = {c: i for i, c in enumerate(cells.channels)}
    M = np.asarray(cells.M, float)
    s_idx = {code: s for s, code in enumerate(state_list)}

    written = []
    by_bundle: dict[str, list[dict]] = {}
    for rec in slots:
        if rec["used"] and rec["y"]:
            by_bundle.setdefault(rec["bundle"], []).append(rec)
    for bundle, recs in sorted(by_bundle.items()):
        states = sorted({st for rec in recs for st in rec["y"]})
        chans = _bundle_channels(bundle)
        M_B = M[:, [cidx[c] for c in chans]].sum(axis=1)
        cell = os.path.join(out, "projections", bundle)
        os.makedirs(cell, exist_ok=True)
        with T.phase("project"):
            # a catch-all bundle has no name in `td.channels`, so it projects by its channels
            proj = channels.project(d, bundle if bundle in channels.BUNDLES else chans,
                                    states=states)
            channels.write_v1(proj, os.path.join(cell, "instance_descaled.json.gz"))
        with open(os.path.join(cell, "state_shares.csv"), "w", encoding="utf-8",
                  newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["state", "district", "share", "target_mass"])
            for j, rec in enumerate(recs):
                for st, share in sorted(rec["y"].items()):
                    w.writerow([st, run_draw.district_id(j), float(share),
                                float(M_B[s_idx[st]]) * float(share)])
        written.append(cell)
        print(f"projection {bundle}: {len(recs)} district(s), {len(states)} state(s) "
              f"-> {cell}", flush=True)
    return written


# ------------------------------------------------------------------------------------- the run
def _prior_from_plan(path: str, state_list: list[str], channel_list) -> np.ndarray:
    """`(S, C)` already-served shares read off a previous run's `plan.json`."""
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    from td import channels

    idx = {c: i for i, c in enumerate(state_list)}
    cidx = {c: i for i, c in enumerate(channel_list)}
    prior = np.zeros((len(state_list), len(channel_list)), float)
    bundle_of = {rec["id"]: rec["bundle"] for rec in obj["slots"]}
    for st, row in obj["per_state"].items():
        if st not in idx:
            continue
        for slot_id, share in row.items():
            if slot_id == "residual_by_channel":
                continue
            for c in _bundle_channels(bundle_of[slot_id]):
                prior[idx[st], cidx[c]] += float(share)
    return np.clip(prior, 0.0, 1.0)


def _main(args, T: telemetry.Timings) -> int:
    from td import channels
    from td import instance as descaled
    from td import stage2_state
    from td.solvers import level0
    from td.solvers import milp_engines as me

    if args.anchor == "greedy" and args.driver == "reps":
        raise ValueError("--anchor greedy fixes each slot's root at its greedy seed, and a "
                         "route-R move that forbids that state from the bundle would leave "
                         "the root on a released contact; use --driver geo")
    with T.phase("load"):
        print(f"loading {args.instance}...", flush=True)
        d = descaled.load_descaled(args.instance)
        if args.synthesize:
            d = channels.synthesize_channels(d, seed=args.seed)
            channels.write_v2(d, os.path.join(args.out, "instance_v2.json.gz"))
            print(f"synthesized channels {d.channels} (seed {args.seed})", flush=True)
        if not d.channels:
            raise ValueError(f"{args.instance} carries one channel; pass --synthesize or "
                             f"give a format-2 file")
        if tuple(d.channels) != tuple(channels.CHANNELS):
            d = channels.fine_split(d)
        state_list = _state_list(d)
        cells = channels.aggregate(d, state_list)
        edges = _state_edges(state_list, args.geo_cache)
        channel_list = list(cells.channels)      # `covered`'s column order, so `cidx` aligns
        cidx = {c: i for i, c in enumerate(channel_list)}
        n_state = len(state_list)

    M = np.asarray(cells.M, float)
    national = float(M[:, [cidx["N_WH"], cidx["N_FI"]]].sum())
    tau = national / args.k
    # --delta is the band's half-width, and it is what the grid varies; it says the same thing
    # as the two multipliers and overrides them when both are given
    band_lo = 1.0 - args.delta if args.delta is not None else args.band_lo
    band_hi = 1.0 + args.delta if args.delta is not None else args.band_hi
    if not (0.0 < band_lo <= band_hi):
        raise ValueError(f"need 0 < band_lo <= band_hi, got {band_lo} and {band_hi}")
    L, U = band_lo * tau, band_hi * tau
    print(f"states={n_state} edges={len(edges)} channels={channel_list} "
          f"national_mass={national:.6g} tau={tau:.6g} L={L:.6g} U={U:.6g}", flush=True)

    enabled = (tuple(b.strip() for b in args.bundles.split(",") if b.strip()) if args.bundles
               else tuple(channels.DEFAULT_BUNDLES))
    unknown = [b for b in enabled if b not in channels.BUNDLES]
    if unknown:
        raise ValueError(f"--bundles: unknown bundle(s) {unknown}")
    priority = [g.strip() for g in args.priority.split(",") if g.strip()]
    unknown = [g for g in priority if g not in STAGE_BUNDLES]
    if unknown:
        raise ValueError(f"--priority: unknown group(s) {unknown}")
    unknown = [b for b in (args.k_fixed or {}) if b not in enabled]
    if unknown:
        raise ValueError(f"--k-fixed: bundle(s) {unknown} not among {list(enabled)}")
    # a per-bundle band needs a count to divide by, so it is the default exactly when there is
    # one.  Asked for without any it would leave every bundle on the national tau and record
    # `band_mode: per-bundle` over a run that is global, which a grid reader cannot see through
    if args.band_mode == "per-bundle" and not args.k_fixed:
        raise ValueError("--band-mode per-bundle needs --k-fixed: a bundle's own mean is its "
                         "own mass over its own count, and there is no count to divide by")
    band_mode = args.band_mode or ("per-bundle" if args.k_fixed else "global")
    print(f"band: mode={band_mode} lo={band_lo:.6g} hi={band_hi:.6g} "
          f"(delta={args.delta})", flush=True)

    prior = (_prior_from_plan(args.prior, state_list, channel_list) if args.prior
             else np.zeros((n_state, len(channel_list)), float))
    # a cap or the seed moments make the geometry compulsory; without one it is still read
    # when the cache has it, since the plan's hull metrics are measured in it
    need_xy = (args.dist_max is not None or args.radius_max is not None
               or args.centers == "seeds")
    state_xy = _state_xy(state_list, args.geo_cache, required=need_xy)
    ctx_cache: dict = {}

    params = dict(
        instance=os.path.abspath(args.instance), route=args.route, driver=args.driver,
        catch_all=args.catch_all, catch_all_bundle=args.catch_all_bundle, k=args.k,
        band_lo=band_lo, band_hi=band_hi, delta=args.delta, band_mode=band_mode, bands={},
        bundles=list(enabled), priority=priority, eta=args.eta, n_max=args.n_max,
        dist_max=args.dist_max, radius_max=args.radius_max, move_budget=args.move_budget,
        cover_slack=args.cover_slack,
        prior=os.path.abspath(args.prior) if args.prior else None,
        centers=(args.centers if args.centers in (None, "seeds")
                 else os.path.abspath(args.centers)),
        incumbency=os.path.abspath(args.incumbency) if args.incumbency else None,
        theta=args.theta, lam=args.lam, filler_capture=args.filler_capture,
        warm=args.warm, anchor=args.anchor, k_fixed=args.k_fixed, k_mode=args.k_mode,
        serve_all_states=args.serve_all_states, other_floor=args.other_floor,
        other_first=args.other_first,
        engine=args.engine, strategy=args.strategy, threads=args.threads,
        time_limit=args.time_limit, synthesize=args.synthesize, seed=args.seed,
        geo_cache=os.path.abspath(args.geo_cache), out=os.path.abspath(args.out),
        tau=tau, L=L, U=U, n_state=n_state, n_edges=len(edges),
        state_list=state_list, channels=channel_list,
    )
    with open(os.path.join(args.out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2, default=float)
        fh.write("\n")

    slots: list[dict] = []
    passes: list[dict] = []
    moves: list[dict] = []
    anchor_log: list[dict] = []
    band_records: dict[str, dict] = {}
    last = None

    def run_stage(stage: str, bundle_names, cover_groups) -> None:
        """Build one level-0 model, solve its passes, and fold its coverage into `prior`."""
        nonlocal prior, last
        # the band this stage holds each of its bundles to: the mass left is what a per-bundle
        # mean divides, so it is read here, off the prior the earlier stages folded in
        bands, band_rec = _stage_bands(cells, bundle_names, args, band_lo=band_lo,
                                       band_hi=band_hi, tau=tau, prior=prior, mode=band_mode)
        floor = (args.other_floor if stage in ("catch_all", "other_first")
                 else ALL_LAST_FLOOR if stage == "all_last" else 1.0)
        if floor != 1.0:
            # an "other" district is one person covering every channel of a sparse region,
            # and may hold less than a full book: its floor is `--other-floor` of L.  MT and
            # WY with every neighbour inside 900 km and six states reach 260 of a 424 floor.
            # The last all-channel stage has no floor to speak of: what is left is allocated
            # whatever its size, which is the rule "no state ends outside every channel".
            bands = {b: (rec["L"] * floor, rec["U"]) for b, rec in band_rec.items()}
            for rec in band_rec.values():
                rec["L"] *= floor
        band_records.update({b: dict(rec, stage=stage) for b, rec in band_rec.items()})
        # `--serve-all-states`: on the joint model every state with mass must enter some
        # district; on route S the states no stage served get the last all-channel stage
        serve, cap_used = None, None
        M_s = np.asarray(cells.M, float).sum(axis=1)
        if stage == "other_first":
            # `--other-first`: the named states, at most one all-channel district each, the
            # fewest contacts the band allows; no greedy, no anchors, so the seeds are not
            # the heaviest states of the country
            serve = [state_list.index(st) for st in args.other_first]
            cap_used = {"WHFI_PLUS": len(serve)}
            print(f"{stage}: {len(serve)} state(s) get an all-channel district: "
                  f"{' '.join(args.other_first)}", flush=True)
        elif stage == "all_last":
            serve = [s for s in range(n_state) if prior[s].max() <= 0.0 and M_s[s] > 0.0]
            cap_used = {"WHFI_PLUS": len(serve)}
            print(f"{stage}: {len(serve)} state(s) outside every channel get an all-channel "
                  f"district: {' '.join(state_list[s] for s in serve)}", flush=True)
        elif args.serve_all_states and stage == serve_stage:
            serve = [s for s in range(n_state) if prior[s].max() <= 0.0 and M_s[s] > 0.0]
            print(f"{stage}: {len(serve)} state(s) must be served here: "
                  f"{' '.join(state_list[s] for s in serve)}", flush=True)
        # A stage whose bundles have no mass left gets zero slots, and a zero-slot model has
        # no objective to build.  `--catch-all` after a sequential run that served everything
        # is exactly that case, so it is skipped and said so rather than raising.
        counts = level0.slot_counts(cells, {b: _bundle_channels(b) for b in bundle_names},
                                    L=L, prior=prior, band=bands)
        for b, n in (cap_used or {}).items():
            counts[b] = min(counts.get(b, 0), n)
        if not sum(counts.values()):
            if serve:
                raise ValueError(f"{stage}: {len(serve)} state(s) must be served here and "
                                 f"the stage has no slots")
            print(f"{stage}: 0 slots ({', '.join(sorted(bundle_names))} have no residual "
                  f"mass above L); skipped", flush=True)
            passes.append(dict(name=f"cover_{stage}", value=0.0, certified=True,
                               status="skipped", seconds=0.0, stage=stage, slots=0))
            last = None            # no model to move on, and no slots to report
            return
        with T.phase("build"):
            problem = _build(cells, bundle_names, args, L=L, U=U, band=bands, edges=edges, serve=serve, max_used=cap_used,
                             prior=prior.copy(), anchors=None, D=None, state_xy=state_xy)
        anchors, D = None, None
        seed_centres = args.centers == "seeds"
        if "N" in problem.slots and (args.incumbency or (args.centers and not seed_centres)):
            ctx = _committed(args, ctx_cache)
            start, stop = problem.slots["N"]
            if args.incumbency:
                anchors = _anchors_from_draw(ctx, state_list, start, stop)
                print(f"{stage}: {len(anchors)} anchor(s) from {args.incumbency}", flush=True)
            if args.centers:
                # under `--centers seeds` too: the N slots are the committed draw's own
                # districts, and their centres are known better than a greedy seed
                D = _moments_from_draw(ctx, state_list, n_state, problem.k, start, stop)
            with T.phase("build"):
                problem = _build(cells, bundle_names, args, L=L, U=U, band=bands, edges=edges, serve=serve, max_used=cap_used,
                                 prior=prior.copy(), anchors=anchors, D=D, state_xy=state_xy)
        _print_slots(problem, stage)
        anchor_log.extend(dict(stage=stage, bundle=problem.bundle_of[j], state=state_list[s],
                               slot=j, source="incumbency") for s, j in (anchors or ()))

        # The greedy point: the first pass's warm start (--warm greedy) and, under --anchor
        # greedy, the seeds every used slot is anchored and rooted at.  `--centers seeds` needs
        # the seeds too, whatever the other two flags say, or it would silently run no
        # compactness pass.  A build that fails is recorded and the stage solves cold: a
        # multi-hour run must not die on its start.
        warm, warm_s, seeds = None, 0.0, None
        if stage not in ("other_first", "all_last") and ("greedy" in (args.warm, args.anchor)
                                                          or seed_centres):
            t0 = time.time()
            try:
                # the cover groups' order, less the bundles this model has no slots for
                # (`_pass_list` drops those too)
                warm, seeds = level0.greedy_plan(
                    problem, priority=[b for _, bs in cover_groups for b in bs
                                       if b in problem.slots])
            except ValueError as exc:
                print(f"{stage}: greedy plan failed ({exc}); solving cold", flush=True)
                passes.append(dict(name="greedy", value=None, certified=False,
                                   status="warm_start_failed", seconds=time.time() - t0,
                                   stage=stage, message=str(exc)))
            warm_s = time.time() - t0
        # One rebuild carries both things the greedy settles: the anchors `--anchor greedy`
        # fixes, and the seed moments `--centers seeds` measures the tie-break about.  The
        # greedy point stays feasible for both -- neither changes a row it has to satisfy --
        # and one rebuild keeps the model `solve_passes` sees to a single build per stage.
        extra: list[tuple[int, int]] = []
        if seeds is not None and args.anchor == "greedy":
            # `z` fixed at the seed and the root fixed there (`fix_roots`); the incumbency's
            # own N anchors keep their slots
            taken = {j for _, j in (anchors or ())}
            extra = [(s, j) for lst in seeds.values() for s, j in lst if j not in taken]
        if seeds is not None and seed_centres:
            seed_D = level0.moments_from_seeds(problem, seeds, state_xy)
            if D is not None:
                keep = np.abs(D).max(axis=0) > 0.0       # a committed centre wins its slot
                seed_D[:, keep] = D[:, keep]
            D = seed_D
        if extra or (seeds is not None and seed_centres):
            anchors = list(anchors or ()) + extra
            with T.phase("build"):
                problem = _build(cells, bundle_names, args, L=L, U=U, band=bands, edges=edges, serve=serve, max_used=cap_used,
                                 prior=prior.copy(), anchors=anchors, D=D, state_xy=state_xy)
                if extra:
                    problem = me.fix_roots(problem, extra)
            anchor_log.extend(dict(stage=stage, bundle=problem.bundle_of[j],
                                   state=state_list[s], slot=j, source="greedy")
                              for s, j in extra)
            if extra:
                print(f"{stage}: {len(extra)} anchor(s) from the greedy plan", flush=True)
        if args.warm != "greedy":
            warm = None
        # what each slot is centred on: its anchor where it has one, else its greedy seed
        centre_of = {int(j): int(s) for s, j in (anchors or ())}
        for lst in (seeds or {}).values():
            for s, j in lst:
                centre_of.setdefault(int(j), int(s))

        unpinned = problem                            # before any pass pinned its value
        result = _run_passes(problem, _pass_list(problem, cover_groups,
                                                 cover_last=stage in ("other_first",
                                                                      "all_last")),
                             args, stage, T, warm=warm, warm_seconds=warm_s)
        problem = result.get("problem", problem)      # every pass's value pinned by a row
        recs = _slot_records(problem, result, state_list, len(slots) + 1,
                             state_xy=state_xy, roots=centre_of)
        slots.extend(recs)
        passes.extend(result["passes"])
        # `covered` is this solve's own coverage; `residual` is `(1 - prior) - covered`, so
        # folding `1 - residual` back into `prior` would count the prior twice.
        cov = result.get("covered")
        cov = (np.asarray(cov, float)
               if cov is not None and np.shape(cov) == (n_state, len(channel_list))
               else _coverage(np.asarray(result["y"], float), problem.bundle_of, cidx))
        prior = np.clip(prior + cov, 0.0, 1.0)
        last = dict(problem=problem, unpinned=unpinned, result=result, slots=recs)

    groups = [g for g in priority if any(b in enabled for b in STAGE_BUNDLES[g])]
    # the last stage that can still serve a state: the joint model, else the last channel
    # stage.  Never the catch-all: by then every neighbour is committed, so a small state
    # could neither join a district nor reach the band on its own; in the FI stage it can
    # still join an FI, FI+ or merged district next door, or an all-channel WHFI_PLUS one
    # when that bundle is enabled.
    serve_stage = "joint" if args.route == "joint" else ""
    if args.other_first:
        bad = [st for st in args.other_first if st not in state_list]
        if bad:
            raise ValueError(f"--other-first names states not in the instance: {bad}")
        run_stage("other_first", ["WHFI_PLUS"], [("cover_other_first", ["WHFI_PLUS"])])
    if args.route == "joint":
        run_stage("joint", list(enabled), [(name, list(bs)) for name, bs in JOINT_COVER])
    else:
        for group in groups:
            bundle_names = [b for b in STAGE_BUNDLES[group] if b in enabled]
            run_stage(f"seq_{group}", bundle_names, _stage_cover(group, bundle_names))

    if args.driver == "reps" and last is not None:
        head = len(slots) - len(last["slots"])
        with T.phase("moves"):
            moves, last = _rep_moves(last["problem"], last["result"], cells, state_list, edges,
                                     args, slots[:head], last["slots"], head + 1, T,
                                     state_xy=state_xy)
        slots = slots[:head] + last["slots"]

    if args.catch_all:
        if args.catch_all_bundle == "all":
            # one bundle over all four fine channels: one rep covering every channel of a
            # state.  A WHFI_PLUS slot sits in all four cover rows, so its share of a state is
            # bounded by `min_c cover_ub[s, c]` and it opens only where every channel is still
            # residual -- which is what this mode asks for, and why it is the wrong bundle for
            # `each`.  The residual it is measured against is that same minimum.
            share = np.min(np.clip(1.0 - prior, 0.0, 1.0), axis=1)
            residual = float((M.sum(axis=1) * share).sum())
            floor = L * args.other_floor
            live = ["WHFI_PLUS"] if residual >= floor else []
            print(f"catch-all: all-channel residual {residual:.6g} against L={floor:.6g}",
                  flush=True)
        else:
            # one single-channel bundle per fine channel that still has residual mass, over the
            # prior every earlier stage folded in.  Single-channel so the cover row of one
            # channel cannot bound a slot serving another (the WHFI_PLUS trap above).
            # residual mass below L can never fill a slot (`band_lo`), and rounding leaves a
            # served channel at ~1e-7 rather than 0, so the test is against L, not against zero
            live = [name for name, chans in CATCH_ALL_BUNDLES.items()
                    if float((M[:, [cidx[c] for c in chans]]
                              * (1.0 - prior[:, [cidx[c] for c in chans]])).sum()) >= L]
            print(f"catch-all: bundles with residual mass {live or '(none)'}", flush=True)
        if live:
            run_stage("catch_all", live, [("cover_other", live)])
            used = sum(1 for r in (last or {}).get("slots", []) if r["used"])
            print(f"catch-all: {used} slot(s) used", flush=True)
        else:
            # decision 1 reads "a fourth channel exists iff the catch-all used a slot", so the
            # stage is recorded even when there was nothing left for it to serve
            passes.append(dict(name="cover_other", value=0.0, certified=True,
                               status="skipped", seconds=0.0, stage="catch_all", slots=0))
            print("catch-all: 0 slot(s) used", flush=True)

    # No state ends outside every channel (the user's rule, 2026-09-11): on route S whatever
    # the stages and the catch-all left is allocated to all-channel districts, one per state
    # at most, the fewest contacts the caps allow, with no floor to speak of.  The joint model
    # carries the same rule as its `serve` rows.
    if args.serve_all_states and args.route != "joint":
        left = [s for s in range(n_state) if prior[s].max() <= 0.0 and M[s].sum() > 0.0]
        if left:
            run_stage("all_last", ["WHFI_PLUS"], [("cover_all_last", ["WHFI_PLUS"])])
        else:
            print("all-last: every state is in a channel already", flush=True)

    # params.json is written before the first solve so a run that dies still has its arguments;
    # the per-bundle bands are only known once each stage has read the mass left to it, so the
    # record is completed here
    params["bands"] = band_records
    with open(os.path.join(args.out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2, default=float)
        fh.write("\n")

    per_state: dict[str, dict] = {}
    for s, code in enumerate(state_list):
        row = {rec["id"]: rec["y"][code] for rec in slots if code in rec["y"]}
        row["residual_by_channel"] = {c: round(float(1.0 - prior[s, i]), 6)
                                      for c, i in cidx.items()}
        per_state[code] = row

    plan = dict(state_list=state_list, bundles=list(enabled), slots=slots,
                per_state=per_state, passes=passes, moves=moves, anchors=anchor_log)
    with open(os.path.join(args.out, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2, default=float)
        fh.write("\n")

    # projections first: they are the hand-off to level 2 and must survive a stage 2 that
    # refuses the plan (a used slot no rep can staff raises rather than scoring).
    _write_projections(args.out, d, cells, slots, state_list, T)

    with T.phase("stage2"):
        staffing = stage2_state.state_stage2(cells, _plan_object(slots, state_list),
                                             theta=args.theta, lam=args.lam,
                                             filler_capture=args.filler_capture,
                                             criterion="nash", candidacy=False)
    with open(os.path.join(args.out, "staffing.json"), "w", encoding="utf-8") as fh:
        json.dump(staffing, fh, indent=2, default=float)
        fh.write("\n")
    print(f"stage 2: value={staffing['value']:.6g} "
          f"unstaffed={len(staffing['unstaffed_districts'])}", flush=True)
    print(f"wrote {args.out}", flush=True)
    return 0


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    T = telemetry.Timings("full_plan")
    try:
        return _main(args, T)
    finally:
        T.write(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
