"""premium.py -- U7-meas: the premium ladder and the numbers measured before formulating.

    .venv/bin/python3 tools/measure/premium.py instance_descaled.json.gz \\
        battery/results/draw_k13_20260901 --out battery/results/meas_20260903

Read-only over `td/`: two Hungarian calls, one small MILP and arithmetic (`docs/MODEL_U7-meas.md`).

Premium is the book that lands with its own holder, `P(pi, sigma) = sum_z S_{rep(z)}(z)`.  With
`u_i(z) = common(z) + w * S_i(z)` and `w = (1 - lam)(1 - theta)`, a district's gain separates as
`g_ij = B_j + w * b_ij`, so at a fixed map the roster moves the premium and nothing else.  The
ladder walks out from the committed draw, each rung relaxing one thing more::

    P0  <=  P*(A)  <=  P_S  <=  P13  <=  P_free
    |       |          |        |        `- every rep, no roster limit
    |       |          |        `- the best k (max-k-coverage MILP, no balance)
    |       |          `- these k, any map, no balance
    |       `- this map, best roster (Hungarian on the book matrix)
    `- this map, this roster

The gaps locate the unrealised premium: `P*(A) - P0` is the matching, `P_S - P0` the map,
`P13 - P_S` the roster.  Each is converted to nats through `w * dP / gbar` and flagged `small`
at 5e-3 (`td/solvers/base.py`'s tier-2 floor) -- a first-order reading, not a certificate.

Every ceiling above `P*(A)` ignores balance by construction, so `V` and the `M`-spread are
reported next to each roster that has a map.  The MILP runs at `mip_rel_gap = 0.0` (trap 12) and
a non-optimal stop is reported as no bound (trap 15), never as `P13`.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, linear_sum_assignment, milp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..")))

from td import channel, model                                              # noqa: E402
from td import instance as descaled                                        # noqa: E402

Rep = str
District = str
Zip = str
Roster = dict[District, Rep]

SMALL_NATS = 5e-3                    # base.EPS_CERT, the tier-2 floor (MODEL_U7-meas.md §6)
_K_DIR = re.compile(r"^k\d+$")
_MILP_STATUS = {0: "optimal", 1: "limit", 2: "infeasible", 3: "unbounded"}


# --------------------------------------------------------------------------- the book matrices
def book_by_zip(G: Any, reps_order: Sequence[Rep],
                nodes: Sequence[Zip]) -> np.ndarray:
    """`S[i, z]` -- rep `reps_order[i]`'s book at `nodes[z]`, zero where it holds none."""
    ir = {r: i for i, r in enumerate(reps_order)}
    S = np.zeros((len(reps_order), len(nodes)), float)
    for zi, z in enumerate(nodes):
        for r, s in model.books(G, z).items():
            i = ir.get(r)
            if i is not None:
                S[i, zi] = float(s)
    return S


def book_matrix(G: Any, to_district: dict[Zip, District],
                reps_order: Sequence[Rep] | None = None,
                districts: Sequence[District] | None = None,
                ) -> tuple[np.ndarray, list[Rep], list[District]]:
    """`(b, reps, districts)` with `b[i, j] = sum_{z in A_j} S_i(z)` -- the book term of `g`.

    Same accumulation as `channel.gain_matrix`, with `common(z)` dropped: `g = B_j + w * b`.
    """
    nodes = sorted(to_district)
    R = list(reps_order) if reps_order is not None else model.reps(G, nodes)
    D = list(districts) if districts is not None else channel.districts_from(to_district)
    b = np.zeros((len(R), len(D)), float)
    if not R or not D:
        return b, R, D
    S = book_by_zip(G, R, nodes)
    jd = {d: j for j, d in enumerate(D)}
    col = np.array([jd[to_district[z]] for z in nodes], int)
    for j in range(len(D)):
        b[:, j] = S[:, col == j].sum(axis=1)
    return b, R, D


# --------------------------------------------------------------------------- the rungs
def roster_premium(b: np.ndarray, reps: Sequence[Rep], districts: Sequence[District],
                   sigma: Roster) -> float:
    """`P0` at an arbitrary roster: `sum_j b_{sigma(j), j}`."""
    ir = {r: i for i, r in enumerate(reps)}
    return float(sum(b[ir[sigma[d]], j] for j, d in enumerate(districts) if d in sigma))


def best_roster(b: np.ndarray, reps: Sequence[Rep],
                districts: Sequence[District]) -> tuple[Roster, float]:
    """`P*(A)`: the premium-maximising roster at a fixed map, Hungarian on `-b` (Kuhn 1955).

    Rectangular (111 x 13) exactly as `channel.match`: the unmatched reps are the ones the
    premium would not retain.
    """
    if b.size == 0:
        return {}, 0.0
    rows, cols = linear_sum_assignment(-b)
    roster = {districts[int(j)]: reps[int(i)]
              for i, j in zip(rows.tolist(), cols.tolist())}
    return roster, float(b[rows, cols].sum())


def coverage_premium(S: np.ndarray, staff: Iterable[int]) -> float:
    """`sum_z max_{i in staff} S_i(z)` -- the best any map can do for a fixed staff set."""
    idx = list(staff)
    if not idx or S.size == 0:
        return 0.0
    return float(S[idx].max(axis=0).sum())


def greedy_staff(S: np.ndarray, k: int) -> tuple[list[int], float]:
    """The `(1 - 1/e)` greedy staff set for max-`k`-coverage, as row indices into `S`."""
    chosen: list[int] = []
    held = np.zeros(S.shape[1], float)
    for _ in range(min(k, S.shape[0])):
        marginal = np.maximum(S, held).sum(axis=1)
        marginal[chosen] = -np.inf
        chosen.append(int(np.argmax(marginal)))
        held = np.maximum(held, S[chosen[-1]])
    return chosen, float(held.sum())


@dataclass(frozen=True)
class Coverage:
    """The `P13` solve: `value` is `None` unless the solver stopped optimal (trap 15)."""

    value: float | None
    status: str
    staff: tuple[Rep, ...] | None
    greedy_value: float
    greedy_staff: tuple[Rep, ...]


def max_k_coverage(S: np.ndarray, reps: Sequence[Rep], k: int) -> Coverage:
    """`P13 = max_{|s| = k} sum_z max_{i in s} S_i(z)` as a MILP (MODEL_U7-meas.md §3.1).

    `y_i` binary, `w_zi in [0, 1]` on the pairs with `S_i(z) > 0` only; `w` is integral at an
    optimum for fixed `y`, so the relaxation loses nothing.  `mip_rel_gap = 0.0` (trap 12), and
    anything but an optimal stop returns `value=None` rather than a bound (trap 15).
    """
    n = len(reps)
    g_idx, g_val = greedy_staff(S, k)
    greedy = tuple(reps[i] for i in sorted(g_idx))
    if n == 0 or k <= 0:
        return Coverage(0.0, "optimal", (), g_val, greedy)

    pi, pz = np.nonzero(S > 0.0)                     # pairs (rep, zip) that can carry book
    p = int(pi.size)
    c = np.concatenate([np.zeros(n), -S[pi, pz]])
    integrality = np.concatenate([np.ones(n), np.zeros(p)])

    one_per_zip = sparse.coo_matrix(
        (np.ones(p), (pz, n + np.arange(p))), shape=(S.shape[1], n + p))
    open_only = sparse.coo_matrix(
        (np.concatenate([np.ones(p), -np.ones(p)]),
         (np.concatenate([np.arange(p), np.arange(p)]),
          np.concatenate([n + np.arange(p), pi]))), shape=(p, n + p))
    head_count = sparse.coo_matrix(
        (np.ones(n), (np.zeros(n, int), np.arange(n))), shape=(1, n + p))

    res = milp(c=c, integrality=integrality, bounds=Bounds(0.0, 1.0),
               constraints=[LinearConstraint(one_per_zip.tocsc(), -np.inf, 1.0),
                            LinearConstraint(open_only.tocsc(), -np.inf, 0.0),
                            LinearConstraint(head_count.tocsc(), float(k), float(k))],
               options=dict(mip_rel_gap=0.0))
    status = _MILP_STATUS.get(int(res.status), "other")
    if not res.success or int(res.status) != 0 or res.x is None:
        return Coverage(None, status, None, g_val, greedy)
    picked = [int(i) for i in np.nonzero(np.asarray(res.x)[:n] > 0.5)[0]]
    # evaluate the chosen staff directly rather than trusting `-res.fun`: `w` is free to be
    # fractional in the model, the evaluation is not.
    return Coverage(coverage_premium(S, picked), status,
                    tuple(reps[i] for i in picked), g_val, greedy)


# --------------------------------------------------------------------------- the other numbers
def pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    """Pearson correlation, or `None` when it is undefined (< 2 points, or no variance)."""
    if x.size < 2 or y.size != x.size:
        return None
    if float(x.std()) == 0.0 or float(y.std()) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def roster_value(g: np.ndarray, reps: Sequence[Rep], districts: Sequence[District],
                 sigma: Roster) -> float:
    """The stage-2 objective `V = sum_j log g_{sigma(j), j}` at an arbitrary roster."""
    ir = {r: i for i, r in enumerate(reps)}
    return float(sum(math.log(g[ir[sigma[d]], j])
                     for j, d in enumerate(districts) if d in sigma))


def spread(values: np.ndarray) -> dict[str, float]:
    """`min`/`max`/`mean`/`spread_rel` -- `balance_report`'s three numbers on any vector."""
    if values.size == 0:
        return dict(min=0.0, max=0.0, mean=0.0, spread_rel=0.0)
    mean = float(values.mean())
    return dict(min=float(values.min()), max=float(values.max()), mean=mean,
                spread_rel=float((values.max() - values.min()) / mean) if mean else 0.0)


def gap(delta: float, w: float, gbar: float, total_book: float) -> dict[str, Any]:
    """One rung-to-rung gap in book units, as a share, and as nats through `w * dP / gbar`."""
    nats = float(w * delta / gbar) if gbar else math.inf
    return dict(book=float(delta),
                share=float(delta / total_book) if total_book else 0.0,
                nats=nats, small=bool(nats <= SMALL_NATS))


def measure(G: Any, to_district: dict[Zip, District], *,
            reps_order: Sequence[Rep] | None = None,
            sigma: Roster | None = None,
            theta: float = 0.40, lam: float = 0.30,
            filler_capture: str = "theta") -> dict[str, Any]:
    """The whole of `docs/MODEL_U7-meas.md` §3 and §5 on one draw.

    `sigma=None` scores the roster `channel.stage2` picks (Nash); an explicit `{district: rep}`
    overrides it, which is how a hand-drawn baseline is scored (U10).  The override moves `P0`,
    `V` and the U1 gains only: the **selected staff** `S13`, which `P_S`, U4 and U8 are about,
    is the image of the model's own stage-2 roster either way -- who the model staffs is not a
    baseline's to change (MODEL_U7-meas.md §4, where `P_S = 28` at `S13 = {A, C}` while the
    hand roster `(A, B)` scores `P0 = 24`).
    """
    nodes = sorted(to_district)
    D = channel.districts_from(to_district)
    b, R, D = book_matrix(G, to_district, reps_order, D)
    S = book_by_zip(G, R, nodes)
    ir = {r: i for i, r in enumerate(R)}
    M = np.array([float(G.nodes[z]["M"]) for z in nodes], float)
    T = S.sum(axis=0)
    total_book, total_M = float(T.sum()), float(M.sum())
    w = (1.0 - lam) * (1.0 - theta)

    g, _, _ = channel.gain_matrix(G, to_district, R, D, theta=theta, lam=lam,
                                  filler_capture=filler_capture)
    nash: Roster = dict(channel.stage2(G, to_district, R, D, theta=theta, lam=lam,
                                       filler_capture=filler_capture)["assignment"])
    if sigma is None:
        sigma0: Roster = dict(nash)
    else:
        sigma0 = dict(sigma)
        missing = [d for d in D if d not in sigma0]
        unknown = [d for d in sigma0 if d not in set(D)]
        outside = [r for r in sigma0.values() if r not in ir]
        if missing or unknown or outside:
            raise ValueError(f"roster covers {sorted(sigma0)}: districts unstaffed {missing}, "
                             f"unknown {unknown}, reps outside the instance {outside}")
        if len(set(sigma0.values())) != len(sigma0):
            raise ValueError(f"roster is not injective: {sigma0}")

    # ---- the ladder
    staff = sorted(set(nash.values()))                            # S13, the selected staff
    P0 = roster_premium(b, R, D, sigma0)
    star, P_star = best_roster(b, R, D)
    P_S = coverage_premium(S, [ir[r] for r in staff])
    cov = max_k_coverage(S, R, len(D))
    P_free = coverage_premium(S, range(len(R)))

    def rung(value: float | None) -> dict[str, float | None]:
        if value is None:
            return dict(book=None, share=None)
        return dict(book=float(value),
                    share=float(value / total_book) if total_book else 0.0)

    # ---- U1: the realised gains beside the opportunity they were balanced on
    gains = np.array([g[ir[sigma0[d]], j] for j, d in enumerate(D)], float)
    gbar = float(gains.mean()) if gains.size else 0.0
    M_by_district = channel.district_opportunity(G, to_district, D)
    M_district = np.array([M_by_district[d] for d in D], float)

    # ---- U4: zips two or more of the selected staff both hold book in
    selected = set(staff)
    u4_zips = [z for z in nodes if len(selected.intersection(model.candidates(G, z))) >= 2]
    u4_M = float(sum(float(G.nodes[z]["M"]) for z in u4_zips))

    # ---- U8: does book sit where the opportunity is?
    per_rep: dict[Rep, float | None] = {}
    for r in staff:
        row = S[ir[r]]
        held = row > 0.0
        per_rep[r] = pearson(row[held], M[held])

    return dict(
        k=len(D), n_zips=len(nodes), n_reps=len(R), w=float(w),
        total_book=total_book, total_M=total_M,
        sigma_source="nash" if sigma is None else "given",
        sigma0=dict(sigma0), sigma_nash=dict(nash), staff=list(staff),
        ladder=dict(P0=rung(P0), P_star_A=rung(P_star), P_S=rung(P_S),
                    P13=rung(cov.value), P_free=rung(P_free)),
        P_star_A_roster=dict(star),
        P13_solve=dict(status=cov.status,
                       staff=list(cov.staff) if cov.staff is not None else None,
                       greedy_book=float(cov.greedy_value),
                       greedy_share=(float(cov.greedy_value / total_book)
                                     if total_book else 0.0),
                       greedy_staff=list(cov.greedy_staff)),
        gaps=dict(
            match=gap(P_star - P0, w, gbar, total_book),
            map=gap(P_S - P0, w, gbar, total_book),
            roster=(gap(cov.value - P_S, w, gbar, total_book)
                    if cov.value is not None else None),
        ),
        V=dict(sigma0=roster_value(g, R, D, sigma0),
               P_star_A=roster_value(g, R, D, star)),
        balance=channel.balance_report(G, to_district),
        U1=dict(gains=spread(gains), M=spread(M_district)),
        U4=dict(n_zips=len(u4_zips), M=u4_M,
                M_share=float(u4_M / total_M) if total_M else 0.0),
        U8=dict(pooled=pearson(T, M), per_rep=per_rep),
    )


# --------------------------------------------------------------------------- the CLI
def sha256(path: str) -> str:
    """Hex digest of a file, for provenance."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_draw_dir(path: str) -> tuple[str, str]:
    """`(dir, label)` for either layout: `<dir>/draw.csv` or a single `<dir>/k<kk>/draw.csv`."""
    d = os.path.normpath(path)
    if not os.path.isfile(os.path.join(d, "draw.csv")):
        subs = sorted(s for s in os.listdir(d) if _K_DIR.match(s)
                      and os.path.isfile(os.path.join(d, s, "draw.csv")))
        if len(subs) != 1:
            raise ValueError(f"{path}: expected draw.csv, or exactly one k*/draw.csv "
                             f"subdirectory; found {subs}")
        d = os.path.join(d, subs[0])
    base = os.path.basename(d)
    label = (os.path.basename(os.path.dirname(os.path.abspath(d)))
             if _K_DIR.match(base) else base)
    return d, label


def read_draw(path: str) -> dict[Zip, District]:
    """`zip,district` -- the CSV `tools/run_draw.py` writes."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = csv.DictReader(fh)
        if rows.fieldnames != ["zip", "district"]:
            raise ValueError(f"{path}: header {rows.fieldnames}, expected ['zip', 'district']")
        return {r["zip"]: r["district"] for r in rows}


def read_metrics(path: str) -> dict[str, Any]:
    """The draw's `metrics.json`."""
    with open(path, encoding="utf-8") as fh:
        return dict(json.load(fh))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("instance", help="instance_descaled.json.gz")
    ap.add_argument("draw", help="draw directory: <dir>/draw.csv or <dir>/k<kk>/draw.csv")
    ap.add_argument("--out", default=os.path.join(
        "battery", "results", f"meas_{_dt.date.today():%Y%m%d}"))
    ap.add_argument("--theta", type=float, default=0.40)
    ap.add_argument("--lam", type=float, default=0.30)
    ap.add_argument("--filler-capture", default="theta")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--sigma-from-metrics", dest="from_metrics", action="store_true",
                     default=True, help="score the draw's recorded roster (default)")
    src.add_argument("--sigma-nash", dest="from_metrics", action="store_false",
                     help="re-run stage 2 instead of reading winner.assignment")
    args = ap.parse_args(argv)

    draw_dir, label = resolve_draw_dir(args.draw)
    draw_csv = os.path.join(draw_dir, "draw.csv")
    to_district = read_draw(draw_csv)
    metrics = read_metrics(os.path.join(draw_dir, "metrics.json"))
    winner = dict(metrics.get("winner") or {})

    d = descaled.load_descaled(args.instance)
    print(f"instance: {d.summary()}")
    print(f"draw: {label} ({draw_dir}), {len(to_district):,} zips, "
          f"k={len(channel.districts_from(to_district))}")

    sigma: Roster | None = None
    if args.from_metrics:
        recorded = winner.get("assignment") or {}
        if not recorded:
            raise ValueError(f"{draw_dir}/metrics.json has no winner.assignment; "
                             f"pass --sigma-nash to re-run stage 2")
        sigma = {str(k): str(v) for k, v in recorded.items()}

    out = measure(d.G, to_district, reps_order=d.reps, sigma=sigma, theta=args.theta,
                  lam=args.lam, filler_capture=args.filler_capture)

    if args.from_metrics:
        recorded_V = float(winner["stage2_value"])
        if abs(out["V"]["sigma0"] - recorded_V) > 1e-9:
            raise ValueError(
                f"recomputed V {out['V']['sigma0']!r} != recorded winner.stage2_value "
                f"{recorded_V!r} (delta {out['V']['sigma0'] - recorded_V:.3e}); the roster, "
                f"the map or the parameters are not the ones that produced the draw")

    payload = dict(
        out,
        run_id=label,
        instance=os.path.abspath(args.instance),
        instance_sha256=sha256(args.instance),
        draw_dir=os.path.abspath(draw_dir),
        draw_sha256=sha256(draw_csv),
        theta=float(args.theta), lam=float(args.lam),
        filler_capture=str(args.filler_capture),
        sigma_from_metrics=bool(args.from_metrics),
        written=_dt.datetime.now().isoformat(timespec="seconds"),
    )

    lad = payload["ladder"]
    print(f"\nladder (book, share of {payload['total_book']:,.1f} total book)")
    for name in ("P0", "P_star_A", "P_S", "P13", "P_free"):
        book, share = lad[name]["book"], lad[name]["share"]
        print(f"  {name:>9}  " + ("no bound" if book is None
                                  else f"{book:>12,.2f}  {share:>7.2%}"))
    print(f"  P13 status {payload['P13_solve']['status']}, greedy "
          f"{payload['P13_solve']['greedy_book']:,.2f}")
    print(f"\ngaps (w = {payload['w']:.2f}, gbar = {payload['U1']['gains']['mean']:,.2f}, "
          f"small at {SMALL_NATS:g} nats)")
    for name in ("match", "map", "roster"):
        gp = payload["gaps"][name]
        print(f"  {name:>7}  " + ("no bound" if gp is None else
                                  f"{gp['book']:>12,.2f}  {gp['share']:>7.2%}  "
                                  f"{gp['nats']:>10.5f} nats  "
                                  f"{'small' if gp['small'] else 'LARGE'}"))
    print(f"\nV at sigma0 {payload['V']['sigma0']:.12f}, at the P*(A) roster "
          f"{payload['V']['P_star_A']:.12f}")
    print(f"U1: gains spread {payload['U1']['gains']['spread_rel']:.3%}, "
          f"M spread {payload['U1']['M']['spread_rel']:.3%}")
    print(f"U4: {payload['U4']['n_zips']} zips, {payload['U4']['M_share']:.2%} of M")
    pooled = payload["U8"]["pooled"]
    print(f"U8: corr(T, M) = " + ("undefined" if pooled is None else f"{pooled:.4f}"))

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{label}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=float)
        fh.write("\n")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
