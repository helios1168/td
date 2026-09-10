"""merge_candidates.py: a cheap pre-screen of the three per-state channel options.

    .venv/bin/python3 tools/merge_candidates.py instance_descaled_v3_conus.json.gz \\
        --geo-cache data/geo --out battery/results/full_problem/candidates_v3

Every state faces the same three options (docs/FULL_PROBLEM.md section 1): keep three
channels, merge WH and FI into one, or drop national and let its mass fall back into WH and
FI.  Arizona is the worked example, $836MM of opportunity as $541MM national, $152MM WH and
$143MM FI.  Route R prices a move with one neighbourhood MILP per state per move, so a
49-state sweep is about 98 solves; this tool runs no solver at all.  It ranks the states by
what is at stake and says, in columns a reader can check, which option the geography and the
rep books already point at, so the move budget is spent where the answer is not obvious.

Four blocks of evidence per state, then a verdict.

**Mass.**  `M_s^N = M_{s,N_WH} + M_{s,N_FI}`, `M_s^WH`, `M_s^FI`, in descaled units, as a
share of the national CWIFI total, and in dollars.  The file's kappa is stripped
(`meta["scale_stripped"]`), so the dollar figures are *inferred*, not read: the settled
scale is tau = $1B at k = 18 (decision 12 and section 2 of the formulation), so one descaled
unit is `1e9 / (national mass / 18)` dollars.  The inference is pinned at k = 18 whatever
`--k` says, so the same state reports the same dollars in every run.  It reproduces the
Arizona example to about 1 per cent (846 against 836, national 553 against 541) and the
stated $48B CWIFI total to 48.3.

**Reach.**  A district needs `L` of mass, and it can only gather it from states its own
district can reach.  For a radius R, `reach_c(s, R)` is the mass of channel c over the
states BFS-reachable from s on the state rook graph restricted to states whose centroid is
within R km of s's centroid.  A pure district of c can exist at s only if `reach_c(s, R)`
is at least L *and* s carries some c itself, so both are tested.  The bundle forms are
additive: WHFI reaches when `reach_WH + reach_FI >= L`, WH+ when `reach_WH + reach_N_WH >=
L`, FI+ when `reach_FI + reach_N_FI >= L`.  Reach is an upper bound on feasibility, not a
certificate: the BFS crosses a state whatever its mass in c, while decision 6 says a state
with no c cannot bridge two c districts, and reach ignores the band's upper end, every other
state's claim on the same mass, and contiguity at zip level.

**Rep books.**  From `CellTable.S`: the reps holding book in both WH and FI at s (a merged
district hands one rep what two hold today), the reps holding national and either WH or FI
at s (they can absorb a dropped national), and the reps holding national alone there (they
are the ones who lose under a drop).  `overlap_share` is the WH-and-FI reps' share of the
state's whole WH plus FI book; `absorb_share` is the WH-or-FI reps' share of its national
book.

**Stage 2, at this state alone.**  The Nash value of staffing s's own cells under each
option: (a) three pure slots N, WH, FI; (b) N plus a merged WHFI slot; (c) WH+ plus FI+.
Each is a `Plan` whose slots hold only s at share 1, scored with `state_gain_matrix` and
`channel.match`; unmatched reps are ignored.  This is a per-state reading and it ignores the
other states the real districts would hold, so it is an ordering hint, not the route-R score.
Option (a) has three slots and (b) and (c) have two, and a sum of logs over three terms is
not comparable with one over two, so `value_per_slot` is reported beside `value` and neither
enters the verdict.  `d_merge_vs_drop_n` is the one difference that reads straight, two slots
against two over the same cells: positive means this state's books prefer the merged WHFI to
the dropped national.  A slot whose bundle carries no mass, no book and no filler at s cannot
be staffed and its option scores `None` (every other entry of a column is strictly positive,
since `c1 > c2`).

**The verdict.**  `R*` is the smallest radius at which pure national reaches L; `R_max` is
the largest radius asked for.  The branches are tried in this order and the one that fires is
named in the `rule` column:

    1. nothing reaches L at R_max                          -> other   nothing_reaches
    2. R* does not exist (national never reaches L):
         WH+ and FI+ both reach at R_max                   -> drop_n  national_unreachable
         otherwise                                         -> other   national_unreachable_no_fallback
    3. at R = R*:
         WH and FI each below L, WH + FI at or above L     -> merge   pure_pair_unreachable
         overlap_share >= 0.5                              -> merge   books_overlap
         absorb_share >= 0.5 and WH+ and FI+ both reach    -> drop_n  national_book_absorbed
         WH and FI both reach                              -> keep    pure_channels_reach
         otherwise                                         -> other   no_option_reaches

Feasibility is read before rep evidence, and rep evidence before `keep`: `keep` is the
do-nothing answer and only wins when the geography allows every pure channel and no book
argues otherwise.  The task's own wording lists `keep` first and leaves the precedence open;
this is the reading, stated so it can be argued with.  Rows are ranked by the mass at stake,
the state's whole CWIFI mass, which is what the decision governs.

Writes `candidates.csv` (one row per state, every column above), `candidates.md` (the top 15
plus Arizona) and a printed summary.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channel, channels, geo, model                                # noqa: E402
from td import instance as descaled                                         # noqa: E402
from td import stage2_state                                                 # noqa: E402
import borders_report                                                       # noqa: E402

# The dollar scale is inferred, and pinned here so `--k` cannot move it: tau = $1B at the
# committed k = 18 (docs/FULL_PROBLEM.md section 2, decision 12).
SCALE_K = 18
TAU_USD = 1.0e9

# "most of the book": the share at which the rep evidence decides the verdict on its own.
MOST = 0.5

# The three options of section 1, as the bundles a slot at this state would carry.
OPTIONS = {
    "keep": (("N_WH", "N_FI"), ("WH",), ("FI",)),
    "merge": (("N_WH", "N_FI"), ("WH", "FI")),
    "drop_n": (("WH", "N_WH"), ("FI", "N_FI")),
}

DEFAULT_RADII = "400,600,900"


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz), format 2")
    ap.add_argument("--k", type=int, default=18,
                    help="tau = national mass / k (default 18, today's committed k)")
    ap.add_argument("--band-lo", type=float, default=0.8,
                    help="L = band_lo * tau (default 0.8, the $800MM floor)")
    ap.add_argument("--radius", default=DEFAULT_RADII, metavar="KM,KM,...",
                    help=f"reach radii in km (default {DEFAULT_RADII})")
    ap.add_argument("--theta", type=float, default=borders_report.THETA,
                    help="stage-2 rep utility weight; scores the options, changes no geometry")
    ap.add_argument("--lam", type=float, default=borders_report.LAM,
                    help="stage-2 rep utility weight; scores the options, changes no geometry")
    ap.add_argument("--filler-capture", choices=list(model.FILLER_CAPTURE),
                    default=borders_report.FILLER_CAPTURE,
                    help="stage-2 filler capture rule; scores the options, changes no geometry")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--out", required=True, help="output directory")
    return ap


def _parse_radii(text: str) -> list[float]:
    out = sorted({float(v) for v in text.split(",") if v.strip()})
    if not out:
        raise ValueError(f"--radius: no radii in {text!r}")
    return out


# The next three helpers are copied from `tools/full_plan.py` (lines 206-239) rather than
# imported: that module is the level-0 driver and pulls a solver's worth of dependencies for
# three lines of geometry.  `geo.state_rook` is called through the module so a test can
# monkeypatch it, as `tests/test_full_plan_cli.py` does.
def _state_list(d) -> list[str]:
    """The state codes the instance actually carries, sorted."""
    codes = sorted({str(d.G.nodes[z].get("state") or "") for z in d.G})
    codes = [c for c in codes if c]
    if not codes:
        raise ValueError("the instance carries no state codes; there is nothing to screen")
    return codes


def _state_adjacency(state_list: list[str], geo_cache: str) -> dict[str, tuple]:
    """The state rook graph restricted to `state_list`."""
    adj, _ = geo.state_rook(geo_cache)
    stray = sorted(set(state_list) - set(adj))
    if stray:
        raise ValueError(f"states not in the rook graph: {stray}")
    keep = set(state_list)
    return {s: tuple(t for t in adj[s] if t in keep) for s in state_list}


def _state_xy(state_list: list[str], geo_cache: str) -> np.ndarray:
    """State centroids in km, the coordinates the radii measure in."""
    _, polys = geo.state_rook(geo_cache)
    missing = sorted(c for c in state_list if c not in polys)
    if missing:
        raise ValueError(f"the reach radii need a polygon for every state; missing {missing}")
    return np.array([[polys[c].centroid.x / 1000.0, polys[c].centroid.y / 1000.0]
                     for c in state_list], float)


# ----------------------------------------------------------------------------------- reach
def reach(cells, adj: dict, xy: np.ndarray, radius: float) -> np.ndarray:
    """`(S, C)`: the mass of each channel over the neighbourhood of each state at `radius`.

    The neighbourhood is what a BFS from s reaches on the rook graph induced on the states
    whose centroid lies within `radius` km of s's own.  s is always in it.
    """
    states = list(cells.state_list)
    idx = {s: i for i, s in enumerate(states)}
    M = np.asarray(cells.M, float)
    out = np.zeros_like(M)
    d = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)
    for i, s in enumerate(states):
        near = {t for t in states if d[i, idx[t]] <= radius}
        seen, stack = {s}, [s]
        while stack:
            cur = stack.pop()
            for t in adj.get(cur, ()):
                if t in near and t not in seen:
                    seen.add(t)
                    stack.append(t)
        out[i] = M[[idx[t] for t in sorted(seen)]].sum(0)
    return out


def bundle_reach(cells, reach_c: np.ndarray, s: int) -> dict[str, float]:
    """The reach of each bundle form at state `s`, summed from the fine channels."""
    j = {c: k for k, c in enumerate(cells.channels)}

    def tot(*cs):
        return float(sum(reach_c[s, j[c]] for c in cs if c in j))

    return dict(N=tot("N_WH", "N_FI"), WH=tot("WH"), FI=tot("FI"),
                WHFI=tot("WH", "FI"), WH_PLUS=tot("WH", "N_WH"), FI_PLUS=tot("FI", "N_FI"))


def _own(cells, s: int) -> dict[str, float]:
    """The state's own mass in each bundle form: reach alone cannot site a district here."""
    M = np.asarray(cells.M, float)
    j = {c: k for k, c in enumerate(cells.channels)}

    def tot(*cs):
        return float(sum(M[s, j[c]] for c in cs if c in j))

    return dict(N=tot("N_WH", "N_FI"), WH=tot("WH"), FI=tot("FI"),
                WHFI=tot("WH", "FI"), WH_PLUS=tot("WH", "N_WH"), FI_PLUS=tot("FI", "N_FI"))


def reachable(cells, reach_c: np.ndarray, s: int, L: float) -> dict[str, bool]:
    """Which bundle forms could hold a district at `s`: L of reach, and mass of its own."""
    r, own = bundle_reach(cells, reach_c, s), _own(cells, s)
    return {b: bool(r[b] >= L and own[b] > 0.0) for b in r}


# ----------------------------------------------------------------------------- rep overlap
def rep_overlap(cells, s: int) -> dict:
    """Who holds what at `s`: the WH-and-FI reps, the absorbers, and the national-only reps."""
    S = np.asarray(cells.S, float)
    j = {c: k for k, c in enumerate(cells.channels)}
    wh = S[:, s, j["WH"]] if "WH" in j else np.zeros(S.shape[0])
    fi = S[:, s, j["FI"]] if "FI" in j else np.zeros(S.shape[0])
    nat = sum(S[:, s, j[c]] for c in ("N_WH", "N_FI") if c in j)

    both = (wh > 0.0) & (fi > 0.0)
    absorb = (nat > 0.0) & ((wh > 0.0) | (fi > 0.0))
    only_n = (nat > 0.0) & (wh <= 0.0) & (fi <= 0.0)

    book_whfi = float((wh + fi).sum())
    book_nat = float(nat.sum())
    return dict(
        reps_both=int(both.sum()), book_both=float((wh + fi)[both].sum()),
        overlap_share=float((wh + fi)[both].sum() / book_whfi) if book_whfi > 0 else 0.0,
        reps_absorb=int(absorb.sum()), book_absorb=float(nat[absorb].sum()),
        absorb_share=float(nat[absorb].sum() / book_nat) if book_nat > 0 else 0.0,
        reps_only_n=int(only_n.sum()), book_only_n=float(nat[only_n].sum()),
        book_whfi=book_whfi, book_n=book_nat,
    )


# ---------------------------------------------------------------------- stage 2 at a state
def option_value(cells, state: str, bundles, *, theta: float, lam: float,
                 filler_capture: str):
    """The Nash value of staffing `state`'s cells as these slots, or None if it cannot be.

    A slot whose bundle carries no mass, no book and no filler at the state has an all-zero
    gain column, which no rep can be matched to; every other column is strictly positive
    because `c1 > c2`, so `channel.match` is safe once that case is out.
    """
    s = list(cells.state_list).index(state)
    M, S, F = (np.asarray(cells.M, float), np.asarray(cells.S, float),
               np.asarray(cells.S_free, float))
    j = {c: k for k, c in enumerate(cells.channels)}
    for bundle in bundles:
        cols = [j[c] for c in bundle if c in j]
        live = M[s, cols].sum() + S[:, s, cols].sum() + F[s, cols].sum()
        if live <= 0.0:
            return None
    plan = stage2_state.Plan(
        slots=[stage2_state.Slot(bundle=tuple(b), y={state: 1.0}, used=True) for b in bundles],
        state_list=list(cells.state_list))
    g, _, _ = stage2_state.state_gain_matrix(cells, plan, theta=theta, lam=lam,
                                             filler_capture=filler_capture)
    _, value = channel.match(g, "nash")
    return float(value)


# ---------------------------------------------------------------------------- the verdict
def verdict(flags_at: dict, r_star, r_max: float, overlap: dict) -> tuple[str, str]:
    """`(verdict, rule)` from the reach flags per radius and the rep books.

    `flags_at` maps a radius to `reachable(...)`'s dict; `r_star` is the smallest radius at
    which pure N reaches, or None.  The branch order is the docstring's.
    """
    top = flags_at[r_max]
    if not any(top.values()):
        return "other", "nothing_reaches"
    if r_star is None:
        if top["WH_PLUS"] and top["FI_PLUS"]:
            return "drop_n", "national_unreachable"
        return "other", "national_unreachable_no_fallback"

    at = flags_at[r_star]
    if not at["WH"] and not at["FI"] and at["WHFI"]:
        return "merge", "pure_pair_unreachable"
    if overlap["overlap_share"] >= MOST:
        return "merge", "books_overlap"
    if overlap["absorb_share"] >= MOST and at["WH_PLUS"] and at["FI_PLUS"]:
        return "drop_n", "national_book_absorbed"
    if at["WH"] and at["FI"]:
        return "keep", "pure_channels_reach"
    return "other", "no_option_reaches"


def screen(cells, adj: dict, xy: np.ndarray, *, L: float, radii, usd_per_unit: float,
           theta: float = borders_report.THETA, lam: float = borders_report.LAM,
           filler_capture: str = borders_report.FILLER_CAPTURE) -> list[dict]:
    """One row per state, ranked by the mass at stake.  No solver runs here."""
    radii = list(radii)
    reaches = {R: reach(cells, adj, xy, R) for R in radii}
    r_max = radii[-1]
    M = np.asarray(cells.M, float)
    j = {c: k for k, c in enumerate(cells.channels)}
    grand = float(M.sum())

    rows = []
    for s, state in enumerate(cells.state_list):
        m = dict(N=float(M[s, [j["N_WH"], j["N_FI"]]].sum()),
                 WH=float(M[s, j["WH"]]), FI=float(M[s, j["FI"]]))
        total = m["N"] + m["WH"] + m["FI"]
        flags_at = {R: reachable(cells, reaches[R], s, L) for R in radii}
        r_star = next((R for R in radii if flags_at[R]["N"]), None)
        overlap = rep_overlap(cells, s)
        values = {name: option_value(cells, state, bundles, theta=theta, lam=lam,
                                     filler_capture=filler_capture)
                  for name, bundles in OPTIONS.items()}
        call, rule = verdict(flags_at, r_star, r_max, overlap)

        row = dict(state=state, verdict=call, rule=rule,
                   mass_total=total, mass_n=m["N"], mass_wh=m["WH"], mass_fi=m["FI"],
                   usd_mm_total=total * usd_per_unit / 1e6,
                   usd_mm_n=m["N"] * usd_per_unit / 1e6,
                   usd_mm_wh=m["WH"] * usd_per_unit / 1e6,
                   usd_mm_fi=m["FI"] * usd_per_unit / 1e6,
                   share_of_total=total / grand if grand > 0 else 0.0,
                   r_star=r_star)
        for R in radii:
            tag = f"{R:g}"
            r = bundle_reach(cells, reaches[R], s)
            for b in ("N", "WH", "FI"):
                row[f"reach_{b.lower()}_{tag}"] = r[b]
            for b, flag in flags_at[R].items():
                row[f"can_{b.lower()}_{tag}"] = int(flag)
        row.update(overlap)
        for name, value in values.items():
            n_slot = len(OPTIONS[name])
            row[f"v_{name}"] = value
            row[f"v_{name}_per_slot"] = None if value is None else value / n_slot
        for name in ("merge", "drop_n"):
            row[f"d_{name}"] = (None if values[name] is None or values["keep"] is None
                                else values[name] - values["keep"])
        # merge against drop is the one comparable difference: two slots against two over the
        # same cells, so it says which of them the books at this state prefer.  Both
        # differences against `keep` carry its extra slot and cannot be read that way.
        row["d_merge_vs_drop_n"] = (None if values["merge"] is None or values["drop_n"] is None
                                    else values["merge"] - values["drop_n"])
        rows.append(row)

    rows.sort(key=lambda r: -r["mass_total"])
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


# ---------------------------------------------------------------------------------- output
def write_csv(rows: list[dict], path: str) -> None:
    head = ["rank", "state", "verdict", "rule"]
    rest = [c for c in rows[0] if c not in head]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=head + rest)
        w.writeheader()
        for row in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v)
                        for k, v in row.items()})


def _fmt(v, nd=1):
    return "" if v is None else f"{v:.{nd}f}"


def write_md(rows: list[dict], path: str, *, L: float, radii, usd_per_unit: float,
             top: int = 15) -> None:
    shown = rows[:top] + [r for r in rows[top:] if r["state"] == "AZ"]
    r_hi = f"{radii[-1]:g}"
    lines = [
        "# Merge candidates: the three per-state options before any MILP",
        "",
        f"Ranked by the mass at stake.  L = {L:.6g} descaled "
        f"(${L * usd_per_unit / 1e6:.0f}MM), radii {', '.join(f'{R:g}' for R in radii)} km.  "
        f"Dollars are inferred from tau = $1B at k = {SCALE_K}, not read from the file.  "
        "`can_*` is read at the radius the verdict was read at: R*, the smallest radius at "
        f"which pure national reaches L, or the largest asked for ({r_hi} km) when national "
        "never reaches it.",
        "",
        "| # | state | $MM | N | WH | FI | R* | pure N/WH/FI | WHFI | WH+/FI+ | overlap | "
        "absorb | v keep | v merge | v drop | merge-drop | verdict | rule |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in shown:
        tag = f"{r['r_star']:g}" if r["r_star"] is not None else r_hi
        pure = "/".join(str(r[f"can_{b}_{tag}"]) for b in ("n", "wh", "fi"))
        plus = "/".join(str(r[f"can_{b}_{tag}"]) for b in ("wh_plus", "fi_plus"))
        lines.append(
            f"| {r['rank']} | {r['state']} | {r['usd_mm_total']:.0f} | "
            f"{r['usd_mm_n']:.0f} | {r['usd_mm_wh']:.0f} | {r['usd_mm_fi']:.0f} | "
            f"{tag if r['r_star'] is not None else '-'} | {pure} | "
            f"{r[f'can_whfi_{tag}']} | {plus} | "
            f"{r['overlap_share']:.2f} | {r['absorb_share']:.2f} | "
            f"{_fmt(r['v_keep'], 2)} | {_fmt(r['v_merge'], 2)} | {_fmt(r['v_drop_n'], 2)} | "
            f"{_fmt(r['d_merge_vs_drop_n'], 3)} | `{r['verdict']}` | {r['rule']} |")
    lines += ["", "Columns: `pure N/WH/FI` and `WH+/FI+` are 1 when that bundle both reaches "
                  "L and has mass of its own at the state; `overlap` is the share of the "
                  "state's WH plus FI book held by reps who hold both; `absorb` is the share "
                  "of its national book held by reps who also hold WH or FI there.  The "
                  "stage-2 values are the state's own cells only, and `v keep` has three "
                  "slots against two, so the columns order options, they do not price them.",
              ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _summary(rows: list[dict]) -> str:
    by = collections.Counter(r["verdict"] for r in rows)
    mass = collections.Counter()
    for r in rows:
        mass[r["verdict"]] += r["usd_mm_total"]
    out = ["verdict counts and the mass they carry:"]
    for name in ("keep", "merge", "drop_n", "other"):
        out.append(f"  {name:7s} {by.get(name, 0):3d} states  ${mass.get(name, 0.0):,.0f}MM")
    rules = collections.Counter(r["rule"] for r in rows)
    out.append("rules that fired: " + ", ".join(f"{k}={v}" for k, v in rules.most_common()))
    out.append("top 10 by mass at stake:")
    for r in rows[:10]:
        out.append(f"  {r['rank']:3d} {r['state']}  ${r['usd_mm_total']:7.0f}MM  "
                   f"{r['verdict']:6s} {r['rule']}")
    return "\n".join(out)


def _main(args) -> int:
    radii = _parse_radii(args.radius)
    print(f"loading {args.instance}...", flush=True)
    d = descaled.load_descaled(args.instance)
    if not d.channels:
        raise ValueError(f"{args.instance} carries one channel; this screen needs a format-2 "
                         f"file with national, wh and fi")
    if tuple(d.channels) != tuple(channels.CHANNELS):
        d = channels.fine_split(d)
    state_list = _state_list(d)
    cells = channels.aggregate(d, state_list)
    adj = _state_adjacency(state_list, args.geo_cache)
    xy = _state_xy(state_list, args.geo_cache)

    M = np.asarray(cells.M, float)
    j = {c: k for k, c in enumerate(cells.channels)}
    national = float(M[:, [j["N_WH"], j["N_FI"]]].sum())
    tau = national / args.k
    L = args.band_lo * tau
    usd_per_unit = TAU_USD / (national / SCALE_K)
    print(f"states={len(state_list)} channels={list(cells.channels)} reps={len(cells.reps)} "
          f"national={national:.6g} tau={tau:.6g} L={L:.6g} "
          f"radii={[f'{R:g}' for R in radii]}", flush=True)
    print(f"inferred scale: 1 descaled unit = ${usd_per_unit / 1e6:.3f}MM "
          f"(tau = $1B at k = {SCALE_K}); CWIFI total ${M.sum() * usd_per_unit / 1e9:.2f}B",
          flush=True)

    rows = screen(cells, adj, xy, L=L, radii=radii, usd_per_unit=usd_per_unit,
                  theta=args.theta, lam=args.lam, filler_capture=args.filler_capture)

    params = dict(instance=os.path.abspath(args.instance), k=args.k, band_lo=args.band_lo,
                  radius=radii, theta=args.theta, lam=args.lam,
                  filler_capture=args.filler_capture, most=MOST, scale_k=SCALE_K,
                  tau=tau, L=L, usd_per_unit=usd_per_unit, n_state=len(state_list),
                  geo_cache=os.path.abspath(args.geo_cache), out=os.path.abspath(args.out))
    with open(os.path.join(args.out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2, default=float)
        fh.write("\n")
    write_csv(rows, os.path.join(args.out, "candidates.csv"))
    write_md(rows, os.path.join(args.out, "candidates.md"), L=L, radii=radii,
             usd_per_unit=usd_per_unit)
    print(_summary(rows), flush=True)
    print(f"wrote {args.out}", flush=True)
    return 0


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    return _main(args)


if __name__ == "__main__":
    raise SystemExit(main())
