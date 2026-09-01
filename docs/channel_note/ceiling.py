"""ceiling.py -- computed numbers and the figure for `channel_note.tex`.

Rewritten 2026-09-01, when the real export landed and rewrote the instance.  What it emits:

1. **The instance**, as the export reports it: 1,229 zips, 111 reps, ~$13B of opportunity,
   national footprint with the regional shares, and the shattered sold-zip adjacency
   (547 components) that retired the contiguity formulation.
2. **The real run** -- the k=13 portfolio of `battery/results/draw_k13_20260901` and the
   certification run of the same day.  The winner's district masses are frozen here as
   literals (`battery/results/` is gitignored, so the note must build without it), and every
   *derived* quantity -- Nash value, spread, max-deviation, the balance-ceiling gap -- is
   recomputed from them rather than transcribed.  When `metrics.json` is present the frozen
   masses are cross-checked against it, so the note cannot drift from the run.
3. **The saturation arithmetic** (MODEL.md) -- how much of a zip's utility is opportunity and
   how much is the incumbency premium, at theta = 0.40, lam = 0.30, 5% saturation.
4. **A 2x2 staffing example** where the Nash and utilitarian matchings disagree.
5. **The withdrawn illustrative ceiling** of the superseded four-component story, computed by
   calling `td.channel.allocate_districts` itself.  The note quotes only its range, in the
   demoted section, labelled as withdrawn -- the $6.2B total and the four-island footprint it
   rests on were both refuted by the export.

Everything lands in `ceiling_numbers.tex` as LaTeX macros and in `figures/draw_k13.png`.
Run from anywhere; paths resolve relative to this file.
"""
from __future__ import annotations

import itertools
import json
import math
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent                      # docs/channel_note -> docs -> repo root
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from td import channel  # noqa: E402

# The house figure style lived in `code/gfx/style.py`, which did not survive the 2026-08-31
# prune.  Only these four values were used, so they are inlined and the note stays
# self-contained -- it builds with nothing but the package and matplotlib.
PALETTE = {"A": "#2166ac", "B": "#b2182b", "neutral": "#4d4d4d"}
RC = {"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
      "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 7,
      "axes.spines.top": False, "axes.spines.right": False,
      "xtick.direction": "out", "ytick.direction": "out",
      "figure.titlesize": 10, "savefig.dpi": 200}

# ------------------------------------------------------- the instance, as exported
TOTAL_B = 13.0         # $B of opportunity across the footprint (user, 2026-09-01)
N_ZIPS = 1229          # zips carrying sales (the 2026-08-31 figure of 2,232 double-counted)
N_GEO = 1223           # of those, carrying a gazetteer internal point
N_REPS = 111           # distinct reps
TARGET_B = 1.0         # the ~$1B territory target
K = 13                 # districts drawn: round(TOTAL_B / TARGET_B)

# node classes from the export's `check_descaled` report
CLASSES = {"contested": 675, "uncontested": 477, "vacant": 2, "untapped": 75}

# regional shares of total opportunity (%), and the sold-zip Rook adjacency
SHARES = {"W": 33.2, "E": 31.0, "TX": 11.5, "FL": 6.7}
COMPONENTS_SOLD = 547        # components of the sold-zip Rook graph
LARGEST_COMP_SHARE = 5.1     # % of total M in the largest component
CRUMB_SHARE = 68             # % of total M in components below 1% each
MAX_ZIP_SHARE = 1.07         # % of total M in the largest single zip (10017)

THETA, LAM = 0.40, 0.30
SATURATION = 0.05      # t_z = T_z / M_z, "~5%"

# ------------------------------------------- the run: battery/results/draw_k13_20260901
RUN_ID = "draw_k13_20260901"
SEEDS = 5
WINNER_SEED = 3
# stage-2 Nash staffing value of every draw in the portfolio, by seed
STAGE2 = {0: 59.86626165934159, 4: 59.86626165934159, 1: 59.87558830522069,
          2: 59.93542665723935, 3: 59.93746979843285}
# the winner's 13 district masses (descaled units), as drawn -- i.e. over the 1,223 zips that
# carry coordinates, which is the object the certificates were computed on
WINNER_MASSES = [210.64551820000003, 211.66564659999997, 211.56884100000002,
                 210.31245955000006, 210.3842305000001, 210.3393512999999,
                 211.65920369999992, 210.33143139999996, 211.62670380000003,
                 210.70410439999998, 210.36013900000006, 210.37717310000002,
                 210.7028748]
# and after the 6 coordinate-less zips are placed by the state-plurality rule
WINNER_MASSES_COMPLETED = [210.64551820000003, 211.66564659999997, 211.56884100000002,
                           211.65055955000005, 210.3842305000001, 210.8654092999999,
                           211.65920369999992, 212.03426139999996, 211.62670380000003,
                           210.70410439999998, 210.98142000000007, 211.12241410000001,
                           210.7028748]
BEST_STAGE1_NASH = 69.56314348299892      # seed 2 -- the stage-1-best draw, which did not win
N_FRACTIONAL = 12                          # split zips in the winner's final transportation LP

# certification run, 2026-09-01 (cert_draw.certify on the winner's labels and centers).
# These are engine-reported and cannot be recomputed here; they are transcribed and cited.
FLOOR_T_REL_UPPER = 2.028e-6      # constructive primal: LPT + move/swap polish, as a fraction
FLOOR_MILP_SECONDS = 300          # dual side: HiGHS, mip_rel_gap = 0
FLOOR_MILP_NODES = 0
FLOOR_MILP_INCUMBENT = 1.69e-2    # HiGHS' own best max-deviation before the cap was imposed
PIN_SECONDS = 168                 # pinned-centers assignment MILP, gap closed to 0
PIN_NODES = 62659
PIN_GAIN_PCT = 8.53               # compactness improvement available at the same balance band
PIN_RELABELLED = 152
PIN_NASH_DELTA = -4.66e-5         # nats of stage-1 Nash paid for it

# ---------------------------------- the withdrawn illustrative ceiling (superseded premise)
OLD_TOTAL_B = 6.2
OLD_SPLITS = {"even-ish": {"W": 2.0, "E": 2.2, "TX": 1.1, "FL": 0.9},
              "east-heavy": {"W": 1.6, "E": 3.0, "TX": 0.9, "FL": 0.7},
              "coast-heavy": {"W": 2.6, "E": 2.6, "TX": 0.6, "FL": 0.4}}
OLD_K = 6


def sci(x: float, digits: int = 3) -> str:
    """`4.510\\times10^{-5}` -- a macro body meant for math mode."""
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    e = int(math.floor(math.log10(abs(x))))
    m = abs(x) / 10.0 ** e
    return f"{sign}{m:.{digits}f}\\times10^{{{e}}}"


def thousands(n) -> str:
    return f"{n:,}".replace(",", "{,}")


def check_against_run() -> None:
    """If the run's metrics.json is on disk, assert the frozen numbers still match it."""
    path = REPO / "battery" / "results" / RUN_ID / "metrics.json"
    if not path.exists():
        print(f"ceiling: {path} absent -- frozen run numbers not cross-checked")
        return
    d = json.loads(path.read_text())
    w = [x for x in d["draws"] if x["seed"] == WINNER_SEED][0]
    assert d["k"] == K and d["n_zips"] == N_ZIPS and d["n_with_coordinates"] == N_GEO
    assert len(d["seeds"]) == SEEDS
    assert d["winner"]["seed"] == WINNER_SEED
    assert np.allclose(sorted(w["before"]["masses"]), sorted(WINNER_MASSES))
    assert np.allclose(sorted(w["after"]["masses"].values()),
                       sorted(WINNER_MASSES_COMPLETED))
    assert w["before"]["n_fractional"] == N_FRACTIONAL
    assert math.isclose(max(x["before"]["nash"] for x in d["draws"]), BEST_STAGE1_NASH)
    for x in d["draws"]:
        assert math.isclose(STAGE2[x["seed"]], x["stage2_value"])
    print(f"ceiling: frozen run numbers agree with {path.relative_to(REPO)}")


def balance(masses) -> dict:
    """Nash value, spread, max-deviation and the analytic ceiling gap of one mass vector."""
    m = np.asarray(masses, float)
    k = m.size
    total = float(m.sum())
    target = total / k
    nash = float(np.log(m).sum())
    ceiling = k * math.log(target)
    return dict(k=k, total=total, target=target, nash=nash, ceiling=ceiling,
                gap=ceiling - nash, gap_rel=1.0 - math.exp(-(ceiling - nash)),
                spread=float((m.max() - m.min()) / target),
                max_dev=float(np.abs(m - target).max() / target),
                dev=(m - target) / target)


def old_ceiling_spreads() -> dict:
    """The superseded illustrative table's k=6 ceiling spreads, from the implementation."""
    out = {}
    for label, comps in OLD_SPLITS.items():
        r = channel.allocate_districts({c: v * 1e9 for c, v in comps.items()}, OLD_K)
        assert r["feasible"], label
        out[label] = 100.0 * r["ceiling_spread_rel"]
    return out


def old_min_spread_budget(comps: dict, k: int):
    """The budget minimising the ceiling spread -- not always the objective-optimal one."""
    names = sorted(comps)
    mean = sum(comps.values()) / k
    best = None
    for alloc in itertools.product(range(1, k + 1), repeat=len(names)):
        if sum(alloc) != k:
            continue
        sizes = [comps[n] / kc for n, kc in zip(names, alloc) for _ in range(kc)]
        sp = (max(sizes) - min(sizes)) / mean
        if best is None or sp < best[0]:
            best = (sp, dict(zip(names, alloc)))
    return best


def main() -> None:
    check_against_run()
    macros: list[str] = ["% generated by ceiling.py -- do not edit"]

    def mac(name: str, value) -> None:
        macros.append(f"\\newcommand{{\\{name}}}{{{value}}}")

    # ------------------------------------------------------------------- the instance
    mac("chTotalB", f"{TOTAL_B:g}")
    mac("chZips", thousands(N_ZIPS))
    mac("chZipsGeo", thousands(N_GEO))
    mac("chNoGeo", N_ZIPS - N_GEO)
    mac("chReps", N_REPS)
    mac("chTargetB", f"{TARGET_B:g}")
    mac("chKAtTarget", K)
    mac("chBinaries", thousands(N_ZIPS * K))
    mac("chRepRatio", f"{N_REPS / K:.1f}")
    mac("chDistrictB", f"{TOTAL_B / K:.2f}")
    for name, n in CLASSES.items():
        mac("chN" + name.capitalize(), n)
    for region, s in SHARES.items():
        mac("chShare" + region, f"{s:.1f}")
    mac("chShareRest", f"{100.0 - sum(SHARES.values()):.1f}")
    mac("chComponentsSold", thousands(COMPONENTS_SOLD))
    mac("chLargestCompShare", f"{LARGEST_COMP_SHARE:g}")
    mac("chCrumbShare", f"{CRUMB_SHARE:g}")
    mac("chMaxZipShare", f"{MAX_ZIP_SHARE:g}")
    mac("chMaxZipOfDistrict", f"{MAX_ZIP_SHARE * K:.0f}")

    # ------------------------------------------------------------------------ the run
    mac("chRunSeeds", SEEDS)
    mac("chWinnerSeed", WINNER_SEED)
    mac("chStageTwoWin", f"{max(STAGE2.values()):.4f}")
    mac("chStageTwoWorst", f"{min(STAGE2.values()):.4f}")
    mac("chStageTwoSpread", sci(max(STAGE2.values()) - min(STAGE2.values()), 2))

    b = balance(WINNER_MASSES)
    c = balance(WINNER_MASSES_COMPLETED)
    mac("chNashWin", f"{b['nash']:.6f}")
    mac("chNashBest", f"{BEST_STAGE1_NASH:.6f}")
    mac("chNashLoss", sci(BEST_STAGE1_NASH - b["nash"], 2))
    mac("chSpreadWin", f"{100 * b['spread']:.3f}")
    mac("chMaxDevWin", f"{100 * b['max_dev']:.4f}")
    mac("chSpreadCompleted", f"{100 * c['spread']:.3f}")
    mac("chCeilingWin", f"{b['ceiling']:.6f}")
    mac("chCeilGap", sci(b["gap"], 3))
    mac("chCeilGapPct", f"{100 * b['gap_rel']:.4f}")
    mac("chNFractional", N_FRACTIONAL)
    mac("chKminusOne", K - 1)

    mac("chFloorUpper", sci(FLOOR_T_REL_UPPER, 3))
    mac("chFloorUpperPct", f"{100 * FLOOR_T_REL_UPPER:.5f}")
    mac("chFloorRatio", thousands(int(round(b["max_dev"] / FLOOR_T_REL_UPPER))))
    mac("chFloorSeconds", FLOOR_MILP_SECONDS)
    mac("chFloorNodes", FLOOR_MILP_NODES)
    mac("chFloorIncumbentPct", f"{100 * FLOOR_MILP_INCUMBENT:.2f}")
    mac("chPinSeconds", PIN_SECONDS)
    mac("chPinNodes", thousands(PIN_NODES))
    mac("chPinGain", f"{PIN_GAIN_PCT:g}")
    mac("chPinRelabelled", PIN_RELABELLED)
    mac("chPinNash", sci(PIN_NASH_DELTA, 2))

    # ------------------------------------------------------- saturation arithmetic
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    t = SATURATION
    u_own = c1 * t + LAM                    # incumbent holds the whole book at z
    u_other = c2 * t + LAM                  # a candidate with no book at z
    mac("chCone", f"{c1:.2f}")
    mac("chCtwo", f"{c2:.2f}")
    mac("chCgap", f"{c1 - c2:.2f}")
    mac("chSat", f"{100 * t:g}")
    mac("chUown", f"{u_own:.3f}")
    mac("chUother", f"{u_other:.3f}")
    mac("chOppShare", f"{100 * LAM / u_own:.1f}")
    mac("chPremShare", f"{100 * (c1 - c2) * t / u_own:.1f}")
    mac("chUswing", f"{100 * (u_own / u_other - 1):.1f}")

    # ------------------------------------------------- nash vs utilitarian matching
    g = np.array([[100.0, 10.0], [90.0, 1.0]])
    mac("chMatchUtilDiag", f"{g[0, 0] + g[1, 1]:.0f}")
    mac("chMatchUtilAnti", f"{g[0, 1] + g[1, 0]:.0f}")
    mac("chMatchNashDiag", f"{math.log(g[0, 0]) + math.log(g[1, 1]):.3f}")
    mac("chMatchNashAnti", f"{math.log(g[0, 1]) + math.log(g[1, 0]):.3f}")

    # ------------------------------------------- the withdrawn illustrative ceiling
    old = old_ceiling_spreads()
    mac("chOldTotalB", f"{OLD_TOTAL_B:g}")
    mac("chOldK", OLD_K)
    mac("chOldSpreadLo", f"{min(old.values()):.1f}")
    mac("chOldSpreadHi", f"{max(old.values()):.1f}")
    sp, _ = old_min_spread_budget(OLD_SPLITS["east-heavy"], OLD_K)
    mac("chOldEastMinSpread", f"{100 * sp:.1f}")

    (HERE / "ceiling_numbers.tex").write_text("\n".join(macros) + "\n")

    # ------------------------------------------------------------------------ figure
    matplotlib.rcParams.update(RC)
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.6))

    ax = axes[0]
    dev = 100 * b["dev"]
    order = np.argsort(dev)
    ax.bar(np.arange(K), dev[order], width=0.72, color=PALETTE["A"])
    ax.axhline(0.0, color="0.35", lw=1.0)
    for s in (+1, -1):
        ax.axhline(s * 100 * b["max_dev"], color=PALETTE["B"], lw=0.9, ls="--")
    ax.annotate(f"max deviation {100 * b['max_dev']:.3f}%",
                xy=(K - 1, 100 * b["max_dev"]), xytext=(0, 3), textcoords="offset points",
                ha="right", fontsize=7, color=PALETTE["B"])
    ax.set_xticks(np.arange(K))
    ax.set_xticklabels([str(i + 1) for i in range(K)])
    ax.set_xlabel("district, sorted by deviation")
    ax.set_ylabel("deviation from target  [%]")
    ax.set_title(f"the $k={K}$ draw ({RUN_ID}, seed {WINNER_SEED}):\n"
                 f"every district within {100 * b['max_dev']:.2f}% of the "
                 f"\\${TOTAL_B / K:.2f}B target")

    ax = axes[1]
    bars = [("HiGHS incumbent,\n300 s, geometry-free", 100 * FLOOR_MILP_INCUMBENT,
             PALETTE["neutral"]),
            ("the draw", 100 * b["max_dev"], PALETTE["A"]),
            ("constructed partition\n(LPT + polish)", 100 * FLOOR_T_REL_UPPER,
             PALETTE["B"])]
    ys = np.arange(len(bars))[::-1]
    ax.barh(ys, [v for _, v, _ in bars], height=0.55,
            color=[col for _, _, col in bars])
    for y, (_, v, _) in zip(ys, bars):
        ax.annotate(f"{v:.3g}%", xy=(v, y), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7)
    ax.set_xscale("log")
    ax.set_yticks(ys)
    ax.set_yticklabels([lab for lab, _, _ in bars])
    ax.set_xlabel("max deviation from target  [%, log scale]")
    ax.set_title("the imbalance is geometry, not indivisibility:\n"
                 f"the draw sits {int(round(b['max_dev'] / FLOOR_T_REL_UPPER)):,}$\\times$ "
                 "above a reachable partition")
    ax.set_xlim(0.5 * 100 * FLOOR_T_REL_UPPER, 40)

    fig.tight_layout(w_pad=3.5)
    figdir = HERE / "figures"
    figdir.mkdir(exist_ok=True)
    fig.savefig(figdir / "draw_k13.png")
    plt.close(fig)

    print(f"ceiling: k={K} winner nash {b['nash']:.6f} vs ceiling {b['ceiling']:.6f} "
          f"(gap {b['gap']:.3e} nats), spread {100 * b['spread']:.3f}%, "
          f"max_dev {100 * b['max_dev']:.4f}%; withdrawn illustrative ceiling k={OLD_K}: "
          + ", ".join(f"{lab} {v:.1f}%" for lab, v in old.items()))


if __name__ == "__main__":
    main()
