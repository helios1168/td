"""
toy_path.py -- the 1-D toy for the math note: n = 10 zips on a path graph.

Enumerates all 2^10 allocations, draws the gain cloud in (g_a, g_b) space with the Nash
hyperbola tangent at the free optimum, then the interval-only ("contiguous for a")
subcloud with its own tangency, and emits every number the note quotes as LaTeX macros
into figures/../toy_path_numbers.tex.

Deterministic: the seed is searched once, in a fixed order, for the smallest seed whose
free Nash optimum is NOT an interval of the path (the note's point), and the chosen seed
is itself emitted as a macro.  Run from anywhere; paths resolve relative to this file.

Model: u_a, u_b built from (A_z, B_z, M_z) with theta = 0.40, lam = 0.30, the NET
headroom convention (CLAUDE.md, "The Model in One Page").  A_z falls left-to-right,
B_z rises, M_z = 1.15 * pointwise headroom floor.
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "code"))

from gfx import style  # noqa: E402

N = 10
THETA, LAM = 0.40, 0.30
C1, C2 = 1.0 - LAM, THETA * (1.0 - LAM)


def build_instance(seed: int):
    """A_z falls, B_z rises, lognormal noise; M_z = 1.15 x headroom floor."""
    rng = np.random.default_rng(seed)
    t = np.arange(N) / (N - 1)                      # position along the path, 0..1
    A = 10.0 * (1.2 - t) * rng.lognormal(0.0, 0.55, N)
    B = 10.0 * (0.2 + t) * rng.lognormal(0.0, 0.55, N)
    M = 1.15 * np.maximum(A + THETA * B, B + THETA * A)
    ua = C1 * A + C2 * B + LAM * M
    ub = C2 * A + C1 * B + LAM * M
    return A, B, M, ua, ub


def gains_all_subsets(ua, ub):
    """(g_a, g_b) for every S in 2^[N], indexed by bitmask; bit z set => z on side a."""
    masks = np.arange(1 << N)
    bits = (masks[:, None] >> np.arange(N)) & 1     # (2^N, N)
    ga = bits @ ua
    gb = (1 - bits) @ ub
    return ga, gb, bits


def is_interval(members: np.ndarray) -> bool:
    """True iff the index set is empty or a run of consecutive integers."""
    idx = np.flatnonzero(members)
    return len(idx) == 0 or idx[-1] - idx[0] + 1 == len(idx)


def main():
    # ---- seed search: smallest seed whose free optimum is not an interval ----------
    for seed in range(1000):
        A, B, M, ua, ub = build_instance(seed)
        ga, gb, bits = gains_all_subsets(ua, ub)
        prod = ga * gb
        free_mask = int(np.argmax(prod))
        if not is_interval(bits[free_mask]):
            break
    else:
        raise SystemExit("no seed in 0..999 gives a non-interval free optimum")

    free_ga, free_gb = float(ga[free_mask]), float(gb[free_mask])
    free_prod = free_ga * free_gb
    free_set = sorted(np.flatnonzero(bits[free_mask]).tolist())

    # ---- interval-only ("contiguous for a") subcloud -------------------------------
    interval_rows = np.array([is_interval(bits[m]) for m in range(1 << N)])
    n_intervals = int(interval_rows.sum())
    expected = N * (N + 1) // 2 + 1
    assert n_intervals == expected, (n_intervals, expected)

    iv_masks = np.flatnonzero(interval_rows)
    iv_best = int(iv_masks[np.argmax(prod[iv_masks])])
    iv_ga, iv_gb = float(ga[iv_best]), float(gb[iv_best])
    iv_prod = iv_ga * iv_gb
    iv_set = sorted(np.flatnonzero(bits[iv_best]).tolist())
    iv_cost_pct = 100.0 * (1.0 - iv_prod / free_prod)

    # ---- both-sides-connected on a path = prefixes and suffixes --------------------
    # (the model's actual constraint: on a path, a's interval must touch an end,
    #  otherwise b is cut in two)
    both_rows = np.array(
        [is_interval(bits[m]) and is_interval(1 - bits[m]) for m in range(1 << N)]
    )
    n_both = int(both_rows.sum())
    both_masks = np.flatnonzero(both_rows)
    both_best = int(both_masks[np.argmax(prod[both_masks])])
    both_ga, both_gb = float(ga[both_best]), float(gb[both_best])
    both_prod = both_ga * both_gb
    both_set = sorted(np.flatnonzero(bits[both_best]).tolist())
    both_cost_pct = 100.0 * (1.0 - both_prod / free_prod)

    # Pareto frontier of the full cloud (for the plot): sort by ga desc, keep gb argmax
    order = np.argsort(-ga)
    frontier = []
    best_gb = -np.inf
    for m in order:
        if gb[m] > best_gb:
            frontier.append(m)
            best_gb = gb[m]
    frontier = np.array(frontier)

    # ---- macros --------------------------------------------------------------------
    def fmt(x, nd=2):
        return f"{x:.{nd}f}"

    def setname(s):
        return r"\{" + ",".join(str(z) for z in s) + r"\}"

    macros = {
        "pathSeed": str(seed),
        "pathN": str(N),
        "pathSubsets": str(1 << N),
        "pathIntervals": str(n_intervals),
        "pathBothConn": str(n_both),
        "pathFreeSet": setname(free_set),
        "pathFreeGa": fmt(free_ga),
        "pathFreeGb": fmt(free_gb),
        "pathFreeProd": fmt(free_prod, 1),
        "pathIvSet": setname(iv_set),
        "pathIvGa": fmt(iv_ga),
        "pathIvGb": fmt(iv_gb),
        "pathIvProd": fmt(iv_prod, 1),
        "pathIvCostPct": fmt(iv_cost_pct, 2),
        "pathBothSet": setname(both_set),
        "pathBothProd": fmt(both_prod, 1),
        "pathBothCostPct": fmt(both_cost_pct, 2),
    }
    out = HERE / "toy_path_numbers.tex"
    with open(out, "w") as fh:
        fh.write("% generated by toy_path.py -- do not edit\n")
        for k, v in macros.items():
            fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

    # ---- figure --------------------------------------------------------------------
    style.use_rc()
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), sharex=True, sharey=True)

    for ax in axes:
        ax.scatter(ga, gb, s=3, c="0.82", linewidths=0, rasterized=True, zorder=1)
        ax.plot(ga[frontier], gb[frontier], "-", color="0.55", lw=0.8, zorder=2)
        ax.set_xlabel(r"$g_a(S)$")
    axes[0].set_ylabel(r"$g_b(S)$")

    gr = np.linspace(0.5 * free_ga, 1.45 * free_ga, 300)
    ymax = 1.08 * float(gb.max())
    for ax in axes:
        ax.set_ylim(-4.0, ymax)

    ax = axes[0]
    ax.plot(gr, free_prod / gr, color=style.PALETTE["neutral"], lw=1.1, zorder=3)
    ax.scatter([free_ga], [free_gb], s=45, marker="*", color=style.PALETTE["A"],
               zorder=5, label="free Nash optimum")
    ax.set_title(f"all $2^{{{N}}}$ allocations; hyperbola "
                 r"$g_a g_b = $" + f"{free_prod:.1f}")
    ax.legend(loc="lower left", frameon=False)

    ax = axes[1]
    ax.scatter(ga[iv_masks], gb[iv_masks], s=16, c=style.PALETTE["B"], alpha=0.75,
               linewidths=0, zorder=3, label=f"{n_intervals} intervals")
    ax.plot(gr, iv_prod / gr, color=style.PALETTE["neutral"], lw=1.1, zorder=3)
    ax.scatter([free_ga], [free_gb], s=45, marker="*", color=style.PALETTE["A"], zorder=5)
    ax.scatter([iv_ga], [iv_gb], s=42, marker="D", color=style.PALETTE["B"],
               edgecolors="black", linewidths=0.5, zorder=6, label="interval optimum")
    ax.set_title(f"interval subcloud; cost of contiguity {iv_cost_pct:.2f}\\%"
                 if False else
                 f"interval subcloud; cost of contiguity {iv_cost_pct:.2f}%")
    ax.legend(loc="lower left", frameon=False)

    style.tight_layout(fig, w_pad=4.5)
    overlaps = style.lint_text_overlap(fig)
    assert not overlaps, overlaps
    figdir = HERE / "figures"
    figdir.mkdir(exist_ok=True)
    fig.savefig(figdir / "toy_path.png")
    plt.close(fig)

    print(f"toy_path: seed={seed} free={free_set} prod={free_prod:.2f} | "
          f"interval={iv_set} prod={iv_prod:.2f} cost={iv_cost_pct:.3f}% | "
          f"both-connected={both_set} prod={both_prod:.2f} cost={both_cost_pct:.3f}%")


if __name__ == "__main__":
    main()
