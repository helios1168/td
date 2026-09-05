"""
toy_grid.py -- the 2-D toy for the math note: a 4x4 Rook grid, 65,536 allocations.

A bimodal value profile (two firm-A pockets in opposite corners, a firm-B band between)
makes the FREE Nash optimum give side a a disconnected territory.  The script verifies
the disconnection, brute-forces the contiguous optimum (both sides connected), builds the
root-free separator cut the solver would generate at the free point -- u and v chosen as
in `contig_methods/scip_tree.py`, C a minimal u,v-separator seeded at N(P) and greedily
minimalised -- verifies the free point violates it and the contiguous point satisfies it,
draws the three maps, and emits macros into toy_grid_numbers.tex.

Deterministic: the base profile is closed-form; a fixed-order seed search perturbs it
until the free optimum is disconnected (in practice the base profile already is at
seed 0, but the search is kept so the construction is honest).
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "code"))

from gfx import style  # noqa: E402

SIDE = 4
N = SIDE * SIDE
THETA, LAM = 0.40, 0.30
C1, C2 = 1.0 - LAM, THETA * (1.0 - LAM)

G = nx.grid_2d_graph(SIDE, SIDE)                       # nodes (row, col)
NODES = sorted(G.nodes())                              # row-major
IDX = {z: i for i, z in enumerate(NODES)}
ADJ = [[IDX[w] for w in G.neighbors(z)] for z in NODES]


def build_instance(seed: int):
    """Two A-pockets in the NW and SE corners, a B band on the anti-diagonal."""
    rng = np.random.default_rng(seed)
    A = np.zeros(N)
    B = np.zeros(N)
    for (r, c), i in IDX.items():
        d_nw = r + c                                   # graph distance to corner (0,0)
        d_se = (SIDE - 1 - r) + (SIDE - 1 - c)         # ... to corner (3,3)
        A[i] = 9.0 * (0.5 ** min(d_nw, d_se))          # bimodal: high at both corners
        band = abs(d_nw - d_se) <= 1                   # the anti-diagonal band
        B[i] = 7.0 if band else 1.5
    A = A * rng.lognormal(0.0, 0.15, N) + 0.3
    B = B * rng.lognormal(0.0, 0.15, N) + 0.3
    M = 1.15 * np.maximum(A + THETA * B, B + THETA * A)
    ua = C1 * A + C2 * B + LAM * M
    ub = C2 * A + C1 * B + LAM * M
    return A, B, M, ua, ub


def connected_or_empty(members: list[int]) -> bool:
    if not members:
        return True
    seen = {members[0]}
    stack = [members[0]]
    mset = set(members)
    while stack:
        i = stack.pop()
        for j in ADJ[i]:
            if j in mset and j not in seen:
                seen.add(j)
                stack.append(j)
    return len(seen) == len(members)


def pieces(members: list[int]) -> list[list[int]]:
    """Connected components of the induced subgraph on `members`."""
    out, todo = [], set(members)
    while todo:
        i = todo.pop()
        comp, stack = {i}, [i]
        while stack:
            k = stack.pop()
            for j in ADJ[k]:
                if j in todo:
                    todo.discard(j)
                    comp.add(j)
                    stack.append(j)
        out.append(sorted(comp))
    return sorted(out, key=len)


def main():
    # ---- seed search: free optimum must give side a a disconnected set -------------
    masks = np.arange(1 << N, dtype=np.uint32)
    bits = ((masks[:, None] >> np.arange(N)) & 1).astype(np.float64)
    for seed in range(1000):
        A, B, M, ua, ub = build_instance(seed)
        ga = bits @ ua
        gb = (1.0 - bits) @ ub
        prod = ga * gb
        free_m = int(np.argmax(prod))
        free_a = sorted(np.flatnonzero(bits[free_m]).astype(int).tolist())
        if not connected_or_empty(free_a):
            break
    else:
        raise SystemExit("no seed in 0..999 disconnects the free optimum")

    free_b = sorted(set(range(N)) - set(free_a))
    free_prod = float(prod[free_m])
    free_pieces = pieces(free_a)
    assert len(free_pieces) >= 2

    # ---- contiguous optimum: both sides connected (single pair component) ----------
    ok = np.fromiter(
        (connected_or_empty(sorted(np.flatnonzero(bits[m]).astype(int).tolist()))
         and connected_or_empty(sorted(np.flatnonzero(1 - bits[m]).astype(int).tolist()))
         for m in range(1 << N)),
        dtype=bool, count=1 << N)
    ok_masks = np.flatnonzero(ok)
    cont_m = int(ok_masks[np.argmax(prod[ok_masks])])
    cont_a = sorted(np.flatnonzero(bits[cont_m]).astype(int).tolist())
    cont_prod = float(prod[cont_m])
    assert connected_or_empty(cont_a) and connected_or_empty(
        sorted(set(range(N)) - set(cont_a)))
    cost_pct = 100.0 * (1.0 - cont_prod / free_prod)

    # ---- the separator cut at the free point (scip_tree's construction) ------------
    # violating piece P = a non-largest piece of side a; u = argmax_{P} u_a,
    # v = argmax_{largest piece} u_a; C = minimal u,v-separator seeded at N(P).
    P = free_pieces[0]
    big = free_pieces[-1]
    u = max(P, key=lambda i: ua[i])
    v = max(big, key=lambda i: ua[i])
    C = {j for i in P for j in ADJ[i]} - set(P)        # N(P): separates P from the rest
    Gm = nx.Graph((IDX[a], IDX[b]) for a, b in ((x, y) for x, y in G.edges()))
    for w in sorted(C, key=lambda i: ua[i]):           # greedy minimalisation
        trial = C - {w}
        H = Gm.subgraph(set(range(N)) - trial)
        if not (u in H and v in H and nx.has_path(H, u, v)):
            C = trial
    H = Gm.subgraph(set(range(N)) - C)
    assert not nx.has_path(H, u, v)                    # C is a u,v-separator
    for w in sorted(C):                                # and a minimal one
        H = Gm.subgraph(set(range(N)) - (C - {w}))
        assert nx.has_path(H, u, v)

    def cut_lhs(a_set):
        x = np.zeros(N)
        x[list(a_set)] = 1.0
        return float(sum(x[w] for w in C)), float(x[u] + x[v] - 1.0)

    lhs_free, rhs_free = cut_lhs(free_a)
    lhs_cont, rhs_cont = cut_lhs(cont_a)
    assert lhs_free < rhs_free, "free point must violate the cut"
    assert lhs_cont >= rhs_cont, "contiguous point must satisfy the cut"

    # ---- macros --------------------------------------------------------------------
    def fmt(x, nd=2):
        return f"{x:.{nd}f}"

    def setname(s):
        return r"\{" + ",".join(str(z) for z in sorted(s)) + r"\}"

    macros = {
        "gridSeed": str(seed),
        "gridN": str(N),
        "gridSubsets": str(1 << N),
        "gridFeasible": str(int(ok.sum())),
        "gridFreeProd": fmt(free_prod, 1),
        "gridFreePieces": str(len(free_pieces)),
        "gridFreeASet": setname(free_a),
        "gridContProd": fmt(cont_prod, 1),
        "gridContASet": setname(cont_a),
        "gridCostPct": fmt(cost_pct, 2),
        "gridPieceP": setname(P),
        "gridCutU": str(u),
        "gridCutV": str(v),
        "gridCutC": setname(C),
        "gridCutLhsFree": fmt(lhs_free, 0),
        "gridCutRhsFree": fmt(rhs_free, 0),
    }
    with open(HERE / "toy_grid_numbers.tex", "w") as fh:
        fh.write("% generated by toy_grid.py -- do not edit\n")
        for k, v_ in macros.items():
            fh.write(f"\\newcommand{{\\{k}}}{{{v_}}}\n")

    # ---- figure: three map panels --------------------------------------------------
    style.use_rc()
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.5))

    def draw(ax, a_set, title, sep=None, mark=None):
        a_set = set(a_set)
        for (r, c), i in IDX.items():
            col = style.PALETTE["A"] if i in a_set else style.PALETTE["B"]
            ax.add_patch(plt.Rectangle((c, SIDE - 1 - r), 1, 1, facecolor=col,
                                       alpha=0.55, edgecolor="white", lw=1.5))
            ax.text(c + 0.06, SIDE - 1 - r + 0.72, str(i), fontsize=6, color="0.25")
            ax.text(c + 0.5, SIDE - 1 - r + 0.40,
                    f"$u_a$={ua[i]:.0f}\n$u_b$={ub[i]:.0f}",
                    fontsize=5.4, ha="center", va="center", color="black")
        if sep:
            for w in sep:
                r, c = NODES[w]
                ax.add_patch(plt.Rectangle((c, SIDE - 1 - r), 1, 1, fill=False,
                                           edgecolor="black", lw=1.8, zorder=5))
        if mark:
            for w, lab in mark:
                r, c = NODES[w]
                ax.text(c + 0.88, SIDE - 1 - r + 0.12, lab, fontsize=8,
                        ha="right", va="bottom", fontweight="bold", color="black")
        ax.set_xlim(-0.05, SIDE + 0.05)
        ax.set_ylim(-0.05, SIDE + 0.05)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title)

    draw(axes[0], free_a,
         f"free Nash optimum: $g_ag_b$ = {free_prod:.1f}\n"
         f"side $a$ in {len(free_pieces)} pieces")
    draw(axes[1], free_a,
         f"violated cut: $\\sum_{{w\\in C}} x_w \\geq x_{{{u}}}+x_{{{v}}}-1$\n"
         f"$C$ outlined; LHS {lhs_free:.0f} $<$ {rhs_free:.0f} RHS",
         sep=C, mark=[(u, "u"), (v, "v")])
    draw(axes[2], cont_a,
         f"contiguous optimum: $g_ag_b$ = {cont_prod:.1f}\n"
         f"cost of contiguity {cost_pct:.2f}%")

    style.tight_layout(fig, w_pad=3.2)
    overlaps = style.lint_text_overlap(fig)
    assert not overlaps, overlaps
    figdir = HERE / "figures"
    figdir.mkdir(exist_ok=True)
    fig.savefig(figdir / "toy_grid.png")
    plt.close(fig)

    print(f"toy_grid: seed={seed} free_a={free_a} pieces={len(free_pieces)} "
          f"prod={free_prod:.2f} | cont_a={cont_a} prod={cont_prod:.2f} "
          f"cost={cost_pct:.3f}% | P={P} u={u} v={v} C={sorted(C)} "
          f"feasible={int(ok.sum())}")


if __name__ == "__main__":
    main()
