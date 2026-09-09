"""state_splits.py -- Track 2 CLI: the state-level minimum-splits MILP driver
(docs/BORDERS_PLAN.md "Track 2 -- the state-level minimum-splits MILP").

    .venv/bin/python3 tools/state_splits.py instance_descaled_v2.json.gz \\
        --draw battery/results/draw_k18_v2_20260904/k18/draw.csv \\
        --geo-cache data/geo --out battery/results/splits_k18_v2_20260907 --maps

Loads the committed draw once (`borders_report.load_committed`), then builds the level-1 data
once: state masses `M_s` and moments `D_sj` about the committed centres over the lower 48 plus
DC (`ctx.state_idx`), and the rook graph over those same state indices (`td.geo.state_rook`).
Prints one sanity row -- is the committed map's own state composition band-feasible and
connected at delta = 1.3%, checked directly, not solved for -- then for every `--delta`:

    1. `td.solvers.state_splits.build_milp` / `solve` (time-limited, `strict=False`: an
       unclosed run reports its incumbent and gap instead of raising);
    2. `balance_pass`, fixing `z` and tightening `y`;
    3. `realise`, turning `(z, y)` into zip labels over the geometric zips (the instance must
       be CONUS+DC, `geo.assert_conus`: no AK, HI or blank-state zip enters the pipeline);
    4. `borders_report.cell_row` / `write_cell` (and maps, if `--maps`), plus a per-delta
       `splits.json` with the full `z`/`y` and the MILP's own objective, status and gap.

Per cell that writes `draw.csv` as a zip table (`td/ziptable.py`), `state_shares.csv` (level 1's
whole decision: `state,district,share,target_mass` from the balance pass), and `steps/` -- one
zip table per accepted level-2 round, the whole instance's labelling at that moment, with
`NN_completed.csv` last.  `--maps-steps` draws every one of them.

`grid.csv` / `grid.md` are rewritten after every cell, so a killed run keeps whatever finished.
A cell whose MILP returns nothing usable writes `<out>/failure.json` (reason, scipy status,
HiGHS message, seconds spent) and re-raises, so the run still exits nonzero and the reason
survives the traceback.  `reason` is `infeasible` (HiGHS proved no such map exists) or
`no_incumbent` (the time limit arrived before a feasible point), which are different answers.

`--bounds PATH` carries user overrides into both levels (`parse_bounds` for the schema): level-1
bounds on `z` through `state_splits.bound_z`, level-2 freezes and pulls around `realise`.  Each
cell's `splits.json` then also carries `bounds` (the document as given) and `bounds_honoured`,
since a pull is only a preference and a forced `z` can still be refused by the band.
"""
from __future__ import annotations

import argparse
import csv
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
from td.solvers import centers                                              # noqa: E402
from td.solvers import state_splits as ss                                   # noqa: E402
import borders_report                                                       # noqa: E402
import run_draw                                                             # noqa: E402

# the sanity-row delta: the committed k=18 draw's own spread_rel (docs/BORDERS_PLAN.md)
COMMITTED_SPREAD = 0.013

# the bench's winner (tools/verify/milp_root_fix/REPORT.md, battery/results/bench/); scipy is
# the fallback everything else was checked against, never the default any more.
DEFAULT_ENGINE = "highs"


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--draw", required=True, help="the committed draw.csv")
    ap.add_argument("--k", type=int, default=18, help="must match the committed draw's k")
    ap.add_argument("--delta", type=float, nargs="+", default=[0.0, 0.01, 0.02, 0.05, 0.10],
                    help="band(s) for the minimum-splits MILP (default 0 .01 .02 .05 .10)")
    ap.add_argument("--time-limit", type=float, default=300.0,
                    help="seconds per MILP; an unclosed run reports its incumbent and gap")
    ap.add_argument("--rounds", type=int, default=5,
                    help="max Lloyd rounds per split state at level 2")
    ap.add_argument("--eta", type=float, default=0.01,
                    help="minimum share a state flagged z_sj=1 must actually send")
    ap.add_argument("--theta", type=float, default=borders_report.THETA,
                    help="stage-2 rep utility weight; weights the stage-2 rep utility only, "
                         "changes no geometry")
    ap.add_argument("--lam", type=float, default=borders_report.LAM,
                    help="stage-2 rep utility weight; weights the stage-2 rep utility only, "
                         "changes no geometry")
    ap.add_argument("--filler-capture", choices=list(model.FILLER_CAPTURE),
                    default=borders_report.FILLER_CAPTURE,
                    help="stage-2 filler capture rule; weights the stage-2 rep utility only, "
                         "changes no geometry")
    ap.add_argument("--incumbency-tiebreak", action="store_true", default=False,
                    help="level-2 bonus toward the committed map's rep(j) book (off by default)")
    ap.add_argument("--anchor-homes", action="store_true", default=False,
                    help="force z=1 for each district in its committed home state; names the "
                         "districts so HiGHS can close the MILP (off by default)")
    ap.add_argument("--engine", choices=("scipy", "highs", "scip"), default=DEFAULT_ENGINE,
                    help=f"MILP engine (default {DEFAULT_ENGINE})")
    ap.add_argument("--strategy", choices=("direct", "descent"), default="descent",
                    help="direct: one solve to --time-limit. descent: a quick incumbent, then "
                         "cutoff proofs of the split count and the tie-break (default descent)")
    ap.add_argument("--primal-seconds", type=float, default=30.0,
                    help="descent strategy: time budget for the first incumbent (default 30)")
    ap.add_argument("--threads", type=int, default=os.cpu_count(),
                    help="solver threads (highs/scip only; default the machine's cpu_count)")
    ap.add_argument("--no-fix-roots", action="store_true", default=False,
                    help="skip the root-fix tightening (default: on when --anchor-homes is "
                         "given and --engine is not scipy; scipy keeps today's matrix so the "
                         "committed map reproduces bit for bit)")
    ap.add_argument("--cap", action="append", default=[], metavar="ST=N",
                    help="cap state ST's district count at N (repeatable)")
    ap.add_argument("--unanchor", action="append", default=[], metavar="ST",
                    help="drop --anchor-homes anchors in state ST before the solve (repeatable)")
    ap.add_argument("--bounds", metavar="PATH", default=None,
                    help="JSON overrides: force/forbid/fix on the level-1 z, freeze/pull on the "
                         "level-2 labels (see load_bounds)")
    ap.add_argument("--dump-state-shares", metavar="PATH", default=None,
                    help="write per-state mass ratios and anchored counts to PATH and exit, "
                         "before the delta loop and before any solve")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--maps", dest="maps", action="store_true", default=True,
                    help="render districts/regions-voronoi maps per cell (default on)")
    ap.add_argument("--no-maps", dest="maps", action="store_false")
    ap.add_argument("--maps-steps", action="store_true", default=False,
                    help="also render every d<delta>/steps/ table into steps/figures/<NN_name>/")
    return ap


def _state_index(code: str, state_list: list[str], flag: str) -> int:
    """Validate one state code against `state_list`, exiting with a clear message.  AK and HI
    are not in the 49-state list (`td/geo.py` excludes them) and are named explicitly rather
    than falling into the generic "unknown code" path."""
    code = code.strip().upper()
    if code in ("AK", "HI"):
        sys.exit(f"{flag}: {code} is not in the 49-state list (AK and HI are excluded)")
    idx_of = {s: i for i, s in enumerate(state_list)}
    if code not in idx_of:
        sys.exit(f"{flag}: unknown state code {code!r}")
    return idx_of[code]


def _parse_caps(tokens: list[str], state_list: list[str]) -> dict[int, int]:
    """`["CA=4", "TX=2"]` -> `{state_index: N}`, validated against `state_list`."""
    caps: dict[int, int] = {}
    for tok in tokens:
        code, sep, n = tok.partition("=")
        if not sep:
            sys.exit(f"--cap {tok}: expected ST=N")
        s = _state_index(code, state_list, "--cap")
        try:
            caps[s] = int(n)
        except ValueError:
            sys.exit(f"--cap {tok}: {n!r} is not an integer")
    return caps


def _release_anchors(anchors: list[tuple[int, int]], caps: dict[int, int],
                     unanchor_states: list[int], ctx) -> tuple[list, dict]:
    """`--unanchor ST` releases only as many of ST's anchors as its `--cap` forces.

    Dropping every anchor in a state reopens the k! relabelling symmetry the anchors exist to
    break (docs: HiGHS already struggled to close a one-split gap without any anchors), so a
    capped state keeps `min(cap, anchored)` of its anchors -- the districts holding the most
    of that state's committed mass, ties broken by ascending district index -- and releases
    only the surplus.  An uncapped state releases all of its anchors, as `--unanchor` always
    has.  Returns the filtered anchor list and `{state: (kept_districts, released_districts)}`
    for every named state that held an anchor, for logging and `params.json`."""
    info: dict[int, tuple[list[int], list[int]]] = {}
    kept_anchors = list(anchors)
    for s in unanchor_states:
        held = [j for s0, j in kept_anchors if s0 == s]
        if not held:
            continue
        n_keep = caps.get(s)
        if n_keep is None:
            keep_js, drop_js = [], held
        elif n_keep >= len(held):
            keep_js, drop_js = held, []
        else:
            sel = ctx.state_idx == s
            mass = np.bincount(ctx.labels0[sel], weights=ctx.M[sel], minlength=ctx.k)
            ranked = sorted(held, key=lambda j: (-mass[j], j))
            keep_js, drop_js = sorted(ranked[:n_keep]), sorted(ranked[n_keep:])
        info[s] = (keep_js, drop_js)
        if drop_js:
            drop_set = set(drop_js)
            kept_anchors = [(s0, j) for s0, j in kept_anchors if not (s0 == s and j in drop_set)]
    return kept_anchors, info


# ------------------------------------------------------------------------------- --bounds
BOUND_KEYS = ("force", "forbid", "fix", "freeze", "pull")


def _district_index(name, k: int, flag: str) -> int:
    """One `D01`-style district name (`run_draw.district_id`) -> its 0-based index."""
    ids = {run_draw.district_id(j): j for j in range(k)}
    key = str(name).strip().upper()
    if key not in ids:
        sys.exit(f"{flag}: unknown district {name!r} "
                 f"(expected D01..{run_draw.district_id(k - 1)})")
    return ids[key]


def _zip_index(code, zip_pos: dict, flag: str) -> int:
    """One zip code -> its position in `ctx.zips`, the order every level-2 array is in."""
    key = str(code).strip()
    if key not in zip_pos:
        sys.exit(f"{flag}: unknown zip {code!r}")
    return zip_pos[key]


def parse_bounds(spec, state_list: list[str], k: int, zips: list) -> dict:
    """Translate a `--bounds` document into solver indices, or exit before anything is solved.

    The document names states, districts and zips the way the rest of the pipeline does
    (`TX`, `D05`, `75201`); everything downstream of here is indices::

        {"force":  [["TX", "D05"], ...]     z_sj >= 1, state s must touch district j
         "forbid": [["TX", "D03"], ...]     z_sj <= 0, state s must not touch j
         "fix":    {"VT": ["D02"], ...}     z_sj = 1 for the listed j, 0 for every other
         "freeze": {"05401": "D02", ...}    that zip takes that label after level 2
         "pull":   {"75201": "D05", ...}}   a level-2 preference toward that district

    `force`, `forbid` and `fix` are bounds and are honoured exactly or the MILP is infeasible;
    `freeze` is applied after `realise` and so always holds; `pull` is only a tie-break and may
    not (`bounds_honoured` in `splits.json` reports which of each did).  A pair that both forces
    and forbids the same `(s, j)`, or a `fix` that contradicts a `force`, is a contradiction in
    the document rather than an infeasible map, and exits nonzero here.
    """
    if not isinstance(spec, dict):
        sys.exit("--bounds: the document must be a JSON object")
    unknown = sorted(set(spec) - set(BOUND_KEYS))
    if unknown:
        sys.exit(f"--bounds: unknown key(s) {unknown}; expected {list(BOUND_KEYS)}")
    zip_pos = {str(z): i for i, z in enumerate(zips)}

    lohi: dict[tuple[int, int], list[float]] = {}

    def clamp(s: int, j: int, lo: float, hi: float, what: str) -> None:
        cur = lohi.setdefault((s, j), [0.0, 1.0])
        cur[0], cur[1] = max(cur[0], lo), min(cur[1], hi)
        if cur[0] > cur[1]:
            sys.exit(f"--bounds {what}: {state_list[s]} and {run_draw.district_id(j)} are both "
                     f"required and refused")

    def pairs(key: str) -> list[tuple[int, int]]:
        out = []
        for item in spec.get(key, []) or []:
            if not (isinstance(item, (list, tuple)) and len(item) == 2):
                sys.exit(f"--bounds {key}: expected [state, district] pairs, got {item!r}")
            s = _state_index(str(item[0]), state_list, f"--bounds {key}")
            out.append((s, _district_index(item[1], k, f"--bounds {key}")))
        return out

    force, forbid = pairs("force"), pairs("forbid")
    for s, j in force:
        clamp(s, j, 1.0, 1.0, "force")
    for s, j in forbid:
        clamp(s, j, 0.0, 0.0, "forbid")

    fix: dict[int, list[int]] = {}
    for code, names in (spec.get("fix") or {}).items():
        s = _state_index(str(code), state_list, "--bounds fix")
        if isinstance(names, str) or not isinstance(names, (list, tuple)) or not names:
            sys.exit(f"--bounds fix {code}: expected a non-empty list of district names")
        js = sorted({_district_index(n, k, "--bounds fix") for n in names})
        fix[s] = js
        for j in range(k):
            clamp(s, j, *((1.0, 1.0) if j in js else (0.0, 0.0)), "fix")

    def labelled(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for code, name in (spec.get(key) or {}).items():
            _zip_index(code, zip_pos, f"--bounds {key}")
            out[str(code).strip()] = _district_index(name, k, f"--bounds {key}")
        return out

    triples = [(s, j, lo, hi) for (s, j), (lo, hi) in sorted(lohi.items())]
    return dict(raw=spec, triples=triples, force=force, forbid=forbid, fix=fix,
                freeze=labelled("freeze"), pull=labelled("pull"))


def load_bounds(path: str, state_list: list[str], k: int, zips: list) -> dict:
    """`parse_bounds` on the JSON at `path`; a malformed file exits before any solve."""
    try:
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
    except OSError as exc:
        sys.exit(f"--bounds {path}: {exc}")
    except json.JSONDecodeError as exc:
        sys.exit(f"--bounds {path}: {exc}")
    return parse_bounds(spec, state_list, k, zips)


def _release_bound_anchors(anchors: list[tuple[int, int]],
                           triples: list[tuple[int, int, float, float]]) -> tuple[list, list]:
    """Drop every `--anchor-homes` anchor a `forbid` or a `fix` refuses, the way `--unanchor`
    drops one.  Without this the bound would silently overwrite the anchor's own lower bound
    inside `bound_z`, and the log would still claim the district was held in that state."""
    refused = {(s, j) for s, j, _lo, hi in triples if hi < 0.5}
    kept = [(s, j) for s, j in anchors if (s, j) not in refused]
    dropped = [(s, j) for s, j in anchors if (s, j) in refused]
    return kept, dropped


def _pull_tiebreak(pull: dict, zips: list, xy: np.ndarray, state_idx: np.ndarray,
                   C: np.ndarray, base: np.ndarray | None = None) -> np.ndarray:
    """`(n, k)` level-2 bonus that makes each pulled district the cheapest one for its zip.

    `realise` hands the bonus to `centers.assign` as `penalty=-tiebreak`, and `assign` adds the
    penalty to `d^2` before the mass column multiplies it, so the scale to beat is a squared
    distance and not a mass moment: ten times the largest `d^2` over the zips of that zip's own
    state dominates every distance difference the state can offer.  It is still only a
    preference -- `assign`'s target masses can, and at a tight target will, put the zip
    elsewhere.  `base` (the incumbency tiebreak, when both are asked for) is added to, not
    replaced.
    """
    n, k = xy.shape[0], C.shape[0]
    tb = np.zeros((n, k)) if base is None else np.array(base, float)
    pos = {str(z): i for i, z in enumerate(zips)}
    bonus_of: dict[int, float] = {}
    for code, j in pull.items():
        i = pos[str(code)]
        s = int(state_idx[i])
        if s not in bonus_of:
            sel = state_idx == s
            d2 = ((xy[sel][:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
            top = float(d2.max()) if d2.size else 0.0
            bonus_of[s] = 10.0 * top if top > 0 else 1.0
        tb[i, j] += bonus_of[s]
    return tb


def _apply_freeze(labels: np.ndarray, zips: list, freeze: dict) -> int:
    """Overwrite the frozen zips' labels in place; returns how many actually moved.

    Level 2 cuts a split state by a balanced LP, so a frozen zip cannot be expressed as a
    bound there -- it is imposed afterwards, which is why `freeze` is honoured by construction
    and can push a district a zip's worth of mass outside the band."""
    pos = {str(z): i for i, z in enumerate(zips)}
    moved = 0
    for code, j in freeze.items():
        i = pos[str(code)]
        if int(labels[i]) != int(j):
            moved += 1
        labels[i] = int(j)
    return moved


def _bounds_honoured(parsed: dict, z: np.ndarray, labels: np.ndarray, zips: list,
                     state_list: list[str]) -> dict:
    """Did each override hold?  `force`/`forbid`/`fix` read the solved `z`, `pull` the final
    labels; `freeze` is true by construction and is listed so a reader need not know that."""
    pos = {str(c): i for i, c in enumerate(zips)}
    return dict(
        force=[[state_list[s], run_draw.district_id(j), bool(z[s, j])]
               for s, j in parsed["force"]],
        forbid=[[state_list[s], run_draw.district_id(j), bool(not z[s, j])]
                for s, j in parsed["forbid"]],
        fix={state_list[s]: [int(x) for x in np.flatnonzero(z[s])] == list(js)
             for s, js in parsed["fix"].items()},
        freeze={str(c): True for c in parsed["freeze"]},
        pull={str(c): bool(int(labels[pos[str(c)]]) == j) for c, j in parsed["pull"].items()},
    )


def write_state_shares(path: str, state_list: list[str], z: np.ndarray, y: np.ndarray,
                       M_s: np.ndarray) -> str:
    """`state,district,share,target_mass` for every state-district pair level 1 opened.

    `share` is the balance pass's own `y_sj`, the fraction of state `s`'s mass district `j` is
    asked for, and `target_mass` is `M_s * y_sj`, the mass that fraction stands for.  Level 1
    moves no zip, so this is the whole of what it decided; level 2 is what turns it into labels.
    """
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["state", "district", "share", "target_mass"])
        for s in range(len(state_list)):
            for j in np.flatnonzero(z[s]):
                w.writerow([state_list[s], run_draw.district_id(int(j)),
                            float(y[s, j]), float(M_s[s] * y[s, j])])
    return path


# ------------------------------------------------------------------------------ level-1 data
def _state_masses_and_moments(ctx, geo_cache: str):
    """`(M_s, D, edges, tau, C)` for the lower-48-plus-DC states in `ctx.state_idx`.

    `M_s` is each state's mass; `C` the committed draw's `k` centroids; `D[s, j]` the exact
    moment of state `s` about centre `j`; `edges` the rook graph (`td.geo.state_rook`) mapped
    onto `ctx.state_list`'s indices; `tau` the equal-split target over this state population.
    """
    known = ctx.state_idx >= 0
    n_state = len(ctx.state_list)
    M_s = np.bincount(ctx.state_idx[known], weights=ctx.M[known], minlength=n_state).astype(float)

    C = centers._centroids(ctx.xy, ctx.M, ctx.labels0, ctx.k)
    d2 = ((ctx.xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    num = np.zeros((n_state, ctx.k), float)
    np.add.at(num, ctx.state_idx[known], ctx.M[known, None] * d2[known])
    D = np.divide(num, M_s[:, None], out=np.zeros_like(num), where=M_s[:, None] > 0)

    adj, _ = geo.state_rook(geo_cache)
    code_to_idx = {c: i for i, c in enumerate(ctx.state_list)}
    stray = sorted(set(adj) - set(code_to_idx))
    if stray:
        raise ValueError(f"state_rook codes not in the state list: {stray}")
    edges = sorted({(min(code_to_idx[a], code_to_idx[b]), max(code_to_idx[a], code_to_idx[b]))
                    for a, nbrs in adj.items() for b in nbrs})

    tau = float(M_s.sum()) / ctx.k
    return M_s, D, edges, tau, C


def _sanity_row(ctx, M_s: np.ndarray, edges: list, tau: float, delta: float) -> None:
    """Is the committed map's own state composition `y0` feasible at `delta`?  Band and
    connectivity are checked directly on `y0`/`z0`; nothing is solved for."""
    known = ctx.state_idx >= 0
    n_state = len(ctx.state_list)
    mass_sj = np.zeros((n_state, ctx.k), float)
    np.add.at(mass_sj, (ctx.state_idx[known], ctx.labels0[known]), ctx.M[known])
    y0 = np.divide(mass_sj, M_s[:, None], out=np.zeros_like(mass_sj), where=M_s[:, None] > 0)
    z0 = mass_sj > 0

    masses = M_s @ y0
    spread_rel = float((masses.max() - masses.min()) / masses.mean())
    max_dev_rel = float(np.abs(masses - tau).max() / tau)
    band_ok = max_dev_rel <= delta + 1e-9
    conn_ok = all(ss.connected(z0[:, j], edges) for j in range(ctx.k))
    below_eta = int(np.sum(z0 & (y0 < 0.01)))
    print(f"sanity @ delta={delta:g}: committed y0 feasible={band_ok and conn_ok} "
          f"(band_ok={band_ok} max_dev_rel={max_dev_rel:.4f} spread_rel={spread_rel:.4f} "
          f"connectivity_ok={conn_ok} state-district contacts below eta={below_eta})",
          flush=True)


def _write_failure(out: str, name: str, delta: float, exc, solve_s: float) -> str:
    """Record what a failed cell established, in a file a reader can act on.

    A failed run writes no `<cell>/splits.json`, so without this the only trace is a traceback in
    the log and every failure reads alike.  `reason` separates the two that matter: `infeasible`
    is a proof that no map meets the overrides at this band, `no_incumbent` is a search that hit
    `--time-limit` without reaching a feasible point (docs/HEADLINE.md section 7).
    """
    path = os.path.join(out, "failure.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(cell=name, delta=delta, reason=getattr(exc, "reason", "other"),
                       status=getattr(exc, "status", None),
                       message=getattr(exc, "solver_message", str(exc)),
                       solve_seconds=round(solve_s, 1)), fh, indent=2)
        fh.write("\n")
    print(f"{name}: no solution, reason={getattr(exc, 'reason', 'other')} "
          f"({solve_s:.1f}s solve); wrote {path}", flush=True)
    return path


# ------------------------------------------------------------------------- incumbency tiebreak
def _raw_tiebreak(ctx, zips_known: list) -> np.ndarray:
    """`(len(zips_known), k)` book of district `j`'s committed rep at each known-state zip,
    unscaled (mu = 1).  `--incumbency-tiebreak` needs `ctx.committed_rep_of` (the committed
    map's `metrics.json`, `{"D0X": rep}`) and `model.books(G, z)`; both are reachable off `ctx`,
    so this is the real tiebreak, not the fallback `NotImplementedError`."""
    if ctx.committed_rep_of is None:
        raise NotImplementedError(
            "--incumbency-tiebreak needs the committed draw's metrics.json (rep(j) "
            "assignment) next to --draw; none was found")
    rep_of = [ctx.committed_rep_of.get(run_draw.district_id(j)) for j in range(ctx.k)]
    tb = np.zeros((len(zips_known), ctx.k), float)
    for i, z in enumerate(zips_known):
        S = model.books(ctx.d.G, z)
        for j, rep in enumerate(rep_of):
            if rep is not None:
                tb[i, j] = S.get(rep, 0.0)
    return tb


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    T = telemetry.Timings("clip")
    try:
        return _main(args, T)
    finally:
        T.write(args.out)


def _main(args, T: telemetry.Timings) -> int:
    with T.phase("load"):
        print(f"loading instance and committed draw ({args.draw})...", flush=True)
        ctx = borders_report.load_committed(args.instance, args.draw, args.geo_cache)
        geo.assert_conus(ctx.d)
        if ctx.k != args.k:
            raise ValueError(f"--k {args.k} does not match the committed draw's k={ctx.k}")
        print(f"loaded: {len(ctx.zips)} geometric zips, k={ctx.k}", flush=True)

        M_s, D, edges, tau, C = _state_masses_and_moments(ctx, args.geo_cache)
        n_state = M_s.shape[0]
        print(f"states: {n_state} (lower 48 + DC), edges={len(edges)}, "
              f"tau={tau:.6g}, total_state_mass={M_s.sum():.6g}", flush=True)

    if args.dump_state_shares:
        # ratios only, per the confidentiality rule: never write tau or a raw mass.
        anchored = np.bincount(ctx.home[ctx.home >= 0], minlength=n_state)
        states = {ctx.state_list[s]: {"ratio": float(M_s[s] / tau), "anchored": int(anchored[s])}
                 for s in range(n_state)}
        with open(args.dump_state_shares, "w", encoding="utf-8") as fh:
            json.dump({"k": ctx.k, "states": states}, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.dump_state_shares}", flush=True)
        return 0

    _sanity_row(ctx, M_s, edges, tau, COMMITTED_SPREAD)

    eps = ss.eps_lexicographic(M_s, D)

    caps = _parse_caps(args.cap, ctx.state_list)
    unanchor_states = [_state_index(code, ctx.state_list, "--unanchor") for code in args.unanchor]

    bounds = load_bounds(args.bounds, ctx.state_list, ctx.k, ctx.zips) if args.bounds else None
    if bounds is not None:
        print(f"bounds: {len(bounds['triples'])} z bound(s) from {args.bounds} "
              f"(force={len(bounds['force'])} forbid={len(bounds['forbid'])} "
              f"fix={len(bounds['fix'])} freeze={len(bounds['freeze'])} "
              f"pull={len(bounds['pull'])})", flush=True)

    anchors = None
    released_by_state: dict[int, tuple[list[int], list[int]]] = {}
    bound_released: list[tuple[int, int]] = []
    if args.anchor_homes:
        anchors = [(int(ctx.home[j]), j) for j in range(ctx.k) if ctx.home[j] >= 0]
        if unanchor_states:
            anchors, released_by_state = _release_anchors(anchors, caps, unanchor_states, ctx)
        if bounds is not None:
            anchors, bound_released = _release_bound_anchors(anchors, bounds["triples"])
            for s, j in bound_released:
                print(f"bounds release: {run_draw.district_id(j)} unanchored from "
                      f"{ctx.state_list[s]} (a forbid or fix refuses it)", flush=True)
        print(f"anchors: {len(anchors)} districts held in their committed home states "
              f"({', '.join(run_draw.district_id(j) + '=' + ctx.state_list[s] for s, j in anchors)})",
              flush=True)
        for s, (keep_js, drop_js) in released_by_state.items():
            print(f"unanchor {ctx.state_list[s]}: kept "
                  f"[{', '.join(run_draw.district_id(j) for j in keep_js)}], released "
                  f"[{', '.join(run_draw.district_id(j) for j in drop_js)}]", flush=True)

    known = ctx.state_idx >= 0
    if not known.all():                    # assert_conus passed, so this is a state-list bug
        raise ValueError(f"{int((~known).sum())} geometric zip(s) carry a state outside the "
                         f"49-state list")
    zips_known = list(ctx.zips)
    xy_k, M_k, state_idx_k = ctx.xy, ctx.M, ctx.state_idx

    tiebreak = None
    if args.incumbency_tiebreak:
        tb_raw = _raw_tiebreak(ctx, zips_known)
        compactness0 = centers.metrics(ctx.M, ctx.labels0, ctx.xy)["compactness"]
        bound = float((M_k * tb_raw.max(axis=1)).sum())
        mu = 0.01 * compactness0 / bound if bound > 0 else 0.0
        tiebreak = tb_raw * mu
        print(f"incumbency tiebreak: mu={mu:.6g} (bound={bound:.6g}, "
              f"committed compactness={compactness0:.6g})", flush=True)

    if bounds is not None and bounds["pull"]:
        tiebreak = _pull_tiebreak(bounds["pull"], zips_known, xy_k, state_idx_k, C,
                                  base=tiebreak)
        print(f"pull tiebreak: {len(bounds['pull'])} zip(s) pulled", flush=True)

    fix_roots = args.anchor_homes and args.engine != "scipy" and not args.no_fix_roots

    params = dict(
        instance=os.path.abspath(args.instance), draw=os.path.abspath(args.draw), k=args.k,
        delta=args.delta, time_limit=args.time_limit, rounds=args.rounds, eta=args.eta,
        incumbency_tiebreak=args.incumbency_tiebreak, anchor_homes=args.anchor_homes,
        engine=args.engine, strategy=args.strategy, primal_seconds=args.primal_seconds,
        threads=args.threads, fix_roots=fix_roots,
        cap=args.cap, unanchor=args.unanchor,
        unanchor_released={ctx.state_list[s]: [run_draw.district_id(j) for j in drop_js]
                           for s, (_, drop_js) in released_by_state.items()},
        bounds=os.path.abspath(args.bounds) if args.bounds else None,
        bounds_released=[[ctx.state_list[s], run_draw.district_id(j)]
                         for s, j in bound_released],
        out=os.path.abspath(args.out),
        geo_cache=os.path.abspath(args.geo_cache), maps=args.maps,
        maps_steps=args.maps_steps, eps=eps, tau=tau,
        n_state=n_state, n_edges=len(edges),
    )
    with open(os.path.join(args.out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2, default=float)
        fh.write("\n")

    rows: list[dict] = []
    basemap_gdf = None

    def basemap():
        """The state polygons, read from the shapefile once per run rather than once per cell."""
        nonlocal basemap_gdf
        if basemap_gdf is None:
            basemap_gdf = geo.states_outline(args.geo_cache)
        return basemap_gdf

    def run_cell(delta: float) -> dict:
        name = f"d{delta:g}"
        t0 = time.time()
        with T.phase("build_milp"):
            problem = ss.build_milp(M_s, D, edges, tau, delta, eps, eta=args.eta,
                                    anchors=anchors, caps=caps or None,
                                    bounds=bounds["triples"] if bounds else None,
                                    fix_roots=fix_roots)
        try:
            with T.phase("solve") as ph:
                result = ss.solve(problem, time_limit=args.time_limit, strict=False,
                                  engine=args.engine, strategy=args.strategy,
                                  primal_seconds=args.primal_seconds, threads=args.threads)
                ph.note(status=result["status"], nodes=result["nodes"], gap=result["mip_gap"],
                        dual_bound=result["dual_bound"], objective=result["objective"],
                        time_limit=args.time_limit, engine=result["engine"],
                        strategy=result["strategy"], certified_splits=result["certified_splits"],
                        phases=result["phases"])
        except ss.SolveFailure as exc:
            _write_failure(args.out, name, delta, exc, time.time() - t0)
            raise
        solve_s = time.time() - t0
        split_codes = ",".join(sorted(ctx.state_list[s] for s in result["split_states"]))
        y_shares = {ctx.state_list[s]: {run_draw.district_id(j): round(float(result["y"][s, j]), 4)
                                        for j in np.flatnonzero(result["z"][s])}
                   for s in result["split_states"]}
        print(f"{name}: status={result['status']} splits={result['splits']} "
              f"split_states=[{split_codes}] milp_spread_rel={result['spread_rel']:.5f} "
              f"mip_gap={result['mip_gap']:.4g} engine={result['engine']} "
              f"strategy={result['strategy']} certified={result['certified_splits']} "
              f"({solve_s:.1f}s solve)", flush=True)

        with T.phase("balance_pass"):
            pas = ss.balance_pass(problem, result["z"])
        print(f"{name}: balance pass spread_rel={pas['spread_rel']:.5f} "
              f"max_dev_rel={pas['max_dev_rel']:.5f}", flush=True)

        with T.phase("realise"):
            realised = ss.realise(xy_k, M_k, state_idx_k, result["z"], pas["y"], C,
                                  rounds=args.rounds, tiebreak=tiebreak)

        def full_labels(labels_known) -> np.ndarray:
            """Level-2 labels -> an int label per `ctx.zips` (every geometric zip has a state)."""
            return np.array([int(lab) for lab in labels_known], int)

        labels_full = full_labels(realised["labels"])
        steps = [(f"realise_{ctx.state_list[s]}_r{r}", full_labels(lab))
                 for s, r, lab in realised["trajectory"]]
        if bounds is not None and bounds["freeze"]:
            moved = _apply_freeze(labels_full, ctx.zips, bounds["freeze"])
            print(f"{name}: froze {len(bounds['freeze'])} zip(s), {moved} relabelled",
                  flush=True)

        rounds_vals = list(realised["rounds_used"].values())
        params_row = dict(
            delta=delta, splits=result["splits"], status=result["status"],
            mip_gap=result["mip_gap"], milp_spread=result["spread_rel"],
            pass_spread=pas["spread_rel"], pass_max_dev=pas["max_dev_rel"],
            n_fractional=realised["n_fractional"],
            rounds_used=max(rounds_vals) if rounds_vals else 0,
        )
        with T.phase("stage2"):
            row = borders_report.cell_row(ctx, labels_full, name, params_row, theta=args.theta,
                                          lam=args.lam, filler_capture=args.filler_capture)
            completed = run_draw.complete(labels_full, ctx.zips, ctx.states_by_zip, ctx.missing,
                                          ctx.M_by_zip)

        with T.phase("write"):
            cell_dir = borders_report.write_cell(args.out, name, ctx, labels_full, completed,
                                                 steps=steps)
            write_state_shares(os.path.join(cell_dir, "state_shares.csv"), ctx.state_list,
                               result["z"], pas["y"], M_s)
            rows.append(row)
            borders_report.write_grid(args.out, rows)

            record = dict(
                delta=delta, status=result["status"], mip_gap=result["mip_gap"],
                objective=result["objective"], splits=result["splits"],
                split_states=split_codes, y_shares=y_shares,
                z=result["z"].astype(bool).tolist(), y=pas["y"].tolist(),
                state_list=ctx.state_list,
                engine=result["engine"], strategy=result["strategy"],
                certified_splits=result["certified_splits"], phases=result["phases"],
                stage2_value=row["stage2_value"], stage2_theta=row["stage2_theta"],
                stage2_lam=row["stage2_lam"], stage2_filler=row["stage2_filler"],
            )
            if bounds is not None:
                record["bounds"] = bounds["raw"]
                record["bounds_honoured"] = _bounds_honoured(bounds, result["z"], labels_full,
                                                             ctx.zips, ctx.state_list)
            with open(os.path.join(cell_dir, "splits.json"), "w", encoding="utf-8") as fh:
                json.dump(record, fh, indent=2)
                fh.write("\n")

            if args.maps or args.maps_steps:
                borders_report.render_cell_maps(cell_dir, args.geo_cache, states=basemap(),
                                                steps=args.maps_steps, report=print)
        total_s = time.time() - t0
        print(f"{name}: spread_rel={row['spread_rel']:.5f} "
              f"outside_owner_share={row['outside_owner_share']:.4f} "
              f"n_states_split={row['n_states_split']} zips_changed={row['zips_changed']} "
              f"stage2={row['stage2_value']:.4f} "
              f"({solve_s:.1f}s solve, {total_s:.1f}s total)", flush=True)
        return row

    for delta in args.delta:
        run_cell(delta)

    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(telemetry.maybe_profile(main)())
