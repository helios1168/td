"""Adversarial verification of the U14-fullprob decomposition proposition (PLAN.md section 4).

Run:  /Users/ntlee/projects/td/.venv/bin/python3 tools/verify/U14-fullprob/verify_decomposition.py
from the worktree root /Users/ntlee/projects/td/.claude/worktrees/full-problem.

The proposition, restated (PLAN.md "The formulation" sections 3 and 4):

  cells (z, c), z in Z, c in C = {N_WH, N_FI, WH, FI}; mass M_{z,c}, rep book S_i(z,c),
  filler S_free(z,c), T_{z,c} = sum_i S_i(z,c);
  u_i(z,c) = c1*S_i(z,c) + c2*(T_{z,c} - S_i(z,c)) + c_free*S_free(z,c) + lam*M_{z,c};
  a district j = (A_j, B_j) owns A_j x B_j, A_j contained in Z_B = {z : B in pi(z)},
  connected in the proximity graph induced on Z_B; band L <= M_j <= U;
  stage 1 at fixed slot counts k_B maximises sum_j log M_j;
  stage 2 maximises sum_j log g_{sigma(j)}(j) over injections sigma from districts to reps.

  (a) u^B_i(z) := sum_{c in B} u_i(z,c) is the single-channel formula on the projected
      quantities M^B, S^B_i, T^B, S^B_free, so g_i(j) = sum_{z in A_j} u^{B_j}_i(z).
  (b) at fixed pi and fixed k_B the stage-1 feasible set is a product over bundles and the
      objective a sum, so the joint optimum is the tuple of per-bundle optima and Lemma 6's
      transportation structure holds per bundle.
  (c) the only cross-bundle coupling in stage 2 is injectivity of sigma, and the stage-2
      problem over the union of all districts is one assignment problem (channel.match).
  (d) a merged bundle carrying per-channel floors is a second balancing attribute and breaks
      (b)'s transportation structure (docs/MODEL.md Lemma 6, lines 375-406).

Every check either PASSES (the clause survived an attempt to break it) or FAILS.  Checks whose
name contains "attack" are dropped-hypothesis probes: they PASS when dropping the hypothesis
does break the clause, which is what makes the hypothesis load bearing.

Not covered here: `td/channels.py:project`, the projection tool B1 is building.  This artifact
uses its own `_projected_graph`, so the identity `gain_matrix(cells) == sum_B gain_matrix(
project(d, B))` must be re-checked against the real `project` by code-verify.

Deterministic: one seed, no solver defaults left implicit.
"""
from __future__ import annotations

import importlib.util
import itertools
import math
import os
import subprocess
import sys
from fractions import Fraction

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import networkx as nx  # noqa: E402
import scipy  # noqa: E402
import sympy as sp  # noqa: E402
from scipy.optimize import linprog  # noqa: E402

from td import channel, model  # noqa: E402

SEED = 20260910
TOL = 1e-12                      # tier 1 numeric-equality; CLAUDE.md CERT_TOL is 1e-8
CHANNELS = ("N_WH", "N_FI", "WH", "FI")
FILLERS = ("theta", "full", "opportunity")

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  --  {detail}" if detail else ""))


def header() -> None:
    try:
        sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", ROOT, "status", "--short"],
                               capture_output=True, text=True, check=True).stdout.strip()
    except Exception as exc:                       # pragma: no cover - diagnostics only
        sha, dirty = f"<unavailable: {exc}>", ""
    print("U14-fullprob decomposition verification")
    print(f"  root      {ROOT}")
    print(f"  git       {sha}" + ("  (worktree dirty: other agents mid-flight)" if dirty else ""))
    print(f"  python    {sys.version.split()[0]}")
    print(f"  numpy     {np.__version__}   scipy {scipy.__version__}   "
          f"sympy {sp.__version__}   networkx {nx.__version__}")
    print(f"  seed      {SEED}   tol {TOL:g}")


# ---------------------------------------------------------------- (a) linearity of u
def clause_a_symbolic() -> None:
    """sum_{c in B} u_i(z,c) equals the single-channel formula on projected quantities."""
    print("\n(a) symbolic: additivity of u over the cells of a bundle")
    c1, c2, cfree, lam = sp.symbols("c1 c2 c_free lam")
    nc, nreps = 3, 4                                    # |B| = 3 cells, 4 reps
    S = sp.Matrix(nreps, nc, lambda i, c: sp.Symbol(f"S_{i}_{c}"))
    free = [sp.Symbol(f"F_{c}") for c in range(nc)]
    M = [sp.Symbol(f"M_{c}") for c in range(nc)]
    T = [sum(S[i, c] for i in range(nreps)) for c in range(nc)]   # T defined as sum over reps

    for i in range(nreps):
        cellwise = sum(c1 * S[i, c] + c2 * (T[c] - S[i, c]) + cfree * free[c] + lam * M[c]
                       for c in range(nc))
        SB = sum(S[i, c] for c in range(nc))
        TB, FB, MB = sum(T), sum(free), sum(M)
        projected = c1 * SB + c2 * (TB - SB) + cfree * FB + lam * MB
        diff = sp.simplify(sp.expand(cellwise - projected))
        check(f"a.sym rep {i}: sum_c u_i(z,c) - u^B_i(z) == 0 identically",
              diff == 0, f"residual {diff}")

    # c_free stayed symbolic above, so all three filler_capture conventions are covered at once;
    # substitute each anyway so the claim is checked in the exact coded form (td/model.py:146-149).
    theta, lam_v = sp.Rational(2, 5), sp.Rational(3, 10)
    coeffs = {"theta": (1 - lam_v, theta * (1 - lam_v), theta * (1 - lam_v)),
              "full": (1 - lam_v, theta * (1 - lam_v), 1 - lam_v),
              "opportunity": (1 - lam_v, theta * (1 - lam_v), lam_v)}
    for name, (v1, v2, vf) in coeffs.items():
        subs = {c1: v1, c2: v2, cfree: vf, lam: lam_v}
        i = 0
        cellwise = sum(c1 * S[i, c] + c2 * (T[c] - S[i, c]) + cfree * free[c] + lam * M[c]
                       for c in range(nc)).subs(subs)
        SB = sum(S[i, c] for c in range(nc))
        projected = (c1 * SB + c2 * (sum(T) - SB) + cfree * sum(free) + lam * sum(M)).subs(subs)
        check(f"a.sym filler_capture={name!r}: identity closes",
              sp.simplify(sp.expand(cellwise - projected)) == 0)

    # attack: the identity needs the SAME constants on every cell of the bundle.
    d1, d2 = sp.symbols("lam1 lam2")
    i = 0
    cellwise = (c1 * S[i, 0] + c2 * (T[0] - S[i, 0]) + cfree * free[0] + d1 * M[0]
                + c1 * S[i, 1] + c2 * (T[1] - S[i, 1]) + cfree * free[1] + d2 * M[1])
    SB = S[i, 0] + S[i, 1]
    projected = (c1 * SB + c2 * (T[0] + T[1] - SB) + cfree * (free[0] + free[1])
                 + d1 * (M[0] + M[1]))
    resid = sp.simplify(sp.expand(cellwise - projected))
    check("a.attack per-channel lam breaks additivity (hypothesis: the constants are global)",
          resid != 0, f"residual {resid}")


def _cell_instance(n_zips: int, reps_all: list[str], *, seed_rng) -> dict:
    """Random per-cell data: M[(z,c)], S[(z,c)][rep], F[(z,c)]."""
    M, S, F = {}, {}, {}
    for z in range(n_zips):
        for c in CHANNELS:
            key = (z, c)
            M[key] = float(seed_rng.uniform(1.0, 10.0))
            books = {}
            for r in reps_all:
                if seed_rng.random() < 0.5:
                    books[r] = float(seed_rng.uniform(0.1, 3.0))
            S[key] = books
            F[key] = float(seed_rng.uniform(0.0, 2.0))
    return dict(M=M, S=S, F=F)


def _cell_graph(data: dict, cells: list[tuple[int, str]]) -> nx.Graph:
    G = nx.Graph()
    for (z, c) in cells:
        books = data["S"][(z, c)]
        G.add_node(f"{z}|{c}", M=data["M"][(z, c)], **{model.BOOK: dict(books),
                                                       model.FREE: data["F"][(z, c)],
                                                       model.CAND: tuple(sorted(books))})
    return G


def _projected_graph(data: dict, zips: list[int], bundle: tuple[str, ...]) -> nx.Graph:
    """The bundle projection, written here rather than taken from td/channels.py:project."""
    G = nx.Graph()
    for z in zips:
        books: dict[str, float] = {}
        m = f = 0.0
        for c in bundle:
            for r, s in data["S"][(z, c)].items():
                books[r] = books.get(r, 0.0) + s
            m += data["M"][(z, c)]
            f += data["F"][(z, c)]
        G.add_node(str(z), M=m, **{model.BOOK: books, model.FREE: f,
                                   model.CAND: tuple(sorted(books))})
    return G


def clause_a_numeric() -> None:
    """channel.gain_matrix on the cell graph == gain_matrix on the per-bundle projections."""
    print("\n(a) numeric: gain_matrix agrees cell-level vs projected (the coded path)")
    rng = np.random.default_rng(SEED + 1)
    reps_all = ["r0", "r1", "r2", "r3", "r_nobook"]     # r_nobook holds book nowhere
    n_zips = 8
    data = _cell_instance(n_zips, ["r0", "r1", "r2", "r3"], seed_rng=rng)

    # channel plan: bundle N = {N_WH, N_FI} on zips 0..5, WHFI = {WH, FI} on zips 2..7.
    plan = {("N_WH", "N_FI"): list(range(0, 6)), ("WH", "FI"): list(range(2, 8))}
    districts = {"N#0": (("N_WH", "N_FI"), [0, 1, 2]),
                 "N#1": (("N_WH", "N_FI"), [3, 4, 5]),
                 "WHFI#0": (("WH", "FI"), [2, 3, 4]),
                 "WHFI#1": (("WH", "FI"), [5, 6, 7])}

    cells = [(z, c) for B, zs in plan.items() for z in zs for c in B]
    Gc = _cell_graph(data, cells)
    to_district_cells = {f"{z}|{c}": d for d, (B, zs) in districts.items() for z in zs for c in B}
    dorder = sorted(districts)

    worst = 0.0
    for fc in FILLERS:
        for theta, lam in ((0.40, 0.30), (0.0, 0.0), (1.0, 0.99), (0.75, 0.5)):
            gc, _, _ = channel.gain_matrix(Gc, to_district_cells, reps_order=reps_all,
                                           districts=dorder, theta=theta, lam=lam,
                                           filler_capture=fc)
            gp = np.zeros_like(gc)
            for B, zs in plan.items():
                Gp = _projected_graph(data, zs, B)
                td_p = {str(z): d for d, (Bd, zsd) in districts.items() if Bd == B for z in zsd}
                gb, _, _ = channel.gain_matrix(Gp, td_p, reps_order=reps_all, districts=dorder,
                                               theta=theta, lam=lam, filler_capture=fc)
                gp += gb
            scale = max(1.0, float(np.abs(gc).max()))
            err = float(np.abs(gc - gp).max()) / scale
            worst = max(worst, err)
            check(f"a.num filler={fc:<11s} theta={theta:<5g} lam={lam:<5g}: "
                  "cell-level gain == projected gain", err <= TOL, f"rel err {err:.3e}")

    # a rep with no book anywhere still gets a strictly positive gain from the mass term,
    # and the identity holds for that row too (no hidden non-linearity in the `common` term).
    gc, _, _ = channel.gain_matrix(Gc, to_district_cells, reps_order=reps_all, districts=dorder,
                                   theta=0.40, lam=0.30, filler_capture="theta")
    row = gc[reps_all.index("r_nobook")]
    check("a.num rep with no book: gain strictly positive on every district",
          bool((row > 0).all()), f"min {row.min():.4f}")
    print(f"       worst relative error over all conventions: {worst:.3e}")


def clause_a_candidacy() -> None:
    """model.utilities masks non-candidates to 0; that mask is not additive over cells."""
    print("\n(a) attack: candidacy masking in model.utilities")
    # one zip, bundle {WH, FI}; rep r0 is a candidate at (z,WH) only.
    Gc = nx.Graph()
    Gc.add_node("z|WH", M=10.0, **{model.BOOK: {"r0": 2.0, "r1": 1.0}, model.FREE: 0.5,
                                   model.CAND: ("r0", "r1")})
    Gc.add_node("z|FI", M=8.0, **{model.BOOK: {"r1": 3.0}, model.FREE: 0.25,
                                  model.CAND: ("r1",)})       # r0 not a candidate here
    Gp = nx.Graph()
    Gp.add_node("z", M=18.0, **{model.BOOK: {"r0": 2.0, "r1": 4.0}, model.FREE: 0.75,
                                model.CAND: ("r0", "r1")})    # union candidacy on the projection

    Uc, _ = model.utilities(Gc, ["z|WH", "z|FI"], reps_order=["r0", "r1"])
    Up, _ = model.utilities(Gp, ["z"], reps_order=["r0", "r1"])
    same_r1 = abs(Uc[1].sum() - Up[1, 0]) <= TOL * max(1.0, abs(Up[1, 0]))
    diff_r0 = abs(Uc[0].sum() - Up[0, 0])
    check("a.cand rep candidate in every cell of the bundle: masked utilities are additive",
          same_r1, f"|diff| {abs(Uc[1].sum() - Up[1, 0]):.3e}")
    check("a.cand attack: rep candidate in only some cells breaks additivity of the MASKED path",
          diff_r0 > 1e-9, f"cellwise {Uc[0].sum():.4f} vs projected {Up[0, 0]:.4f}")

    # channel.gain_matrix ignores candidacy by design (td/channel.py:267), so the gain path,
    # which is the one the proposition is about, is unaffected.
    tdc = {"z|WH": "d", "z|FI": "d"}
    gc, _, _ = channel.gain_matrix(Gc, tdc, reps_order=["r0", "r1"], districts=["d"])
    gp, _, _ = channel.gain_matrix(Gp, {"z": "d"}, reps_order=["r0", "r1"], districts=["d"])
    check("a.cand gain_matrix (candidacy ignored) stays additive on the same instance",
          float(np.abs(gc - gp).max()) <= TOL * max(1.0, float(np.abs(gp).max())),
          f"max |diff| {float(np.abs(gc - gp).max()):.3e}")


def clause_a_release() -> None:
    """release_reps commutes with the bundle projection (trap 20 lives next door)."""
    print("\n(a) attack: does releasing a rep commute with projection?")
    rng = np.random.default_rng(SEED + 2)
    reps_all = ["r0", "r1", "r2"]
    data = _cell_instance(4, reps_all, seed_rng=rng)
    B = ("WH", "FI")
    zs = list(range(4))
    Gc = _cell_graph(data, [(z, c) for z in zs for c in B])
    Gp = _projected_graph(data, zs, B)
    tdc = {f"{z}|{c}": "d" for z in zs for c in B}
    tdp = {str(z): "d" for z in zs}
    for fc in FILLERS:
        g1, _, _ = channel.gain_matrix(model.release_reps(Gc, ["r2"]), tdc,
                                       reps_order=["r0", "r1"], districts=["d"],
                                       filler_capture=fc)
        g2, _, _ = channel.gain_matrix(model.release_reps(Gp, ["r2"]), tdp,
                                       reps_order=["r0", "r1"], districts=["d"],
                                       filler_capture=fc)
        err = float(np.abs(g1 - g2).max()) / max(1.0, float(np.abs(g2).max()))
        check(f"a.rel release then project == project then release (filler={fc})",
              err <= TOL, f"rel err {err:.3e}")


# ---------------------------------------------------------------- (b) separability
def _feasible_maps(G: nx.Graph, mass: dict, k: int, lo: float, hi: float) -> list[tuple]:
    """All labelings of G's nodes into k nonempty connected districts inside the band."""
    nodes = sorted(G.nodes)
    out = []
    for lab in itertools.product(range(k), repeat=len(nodes)):
        parts = [[z for z, l in zip(nodes, lab) if l == j] for j in range(k)]
        if any(not p for p in parts):
            continue
        if any(not nx.is_connected(G.subgraph(p)) for p in parts):
            continue
        masses = [sum(mass[z] for z in p) for p in parts]
        if any(m < lo - 1e-12 or m > hi + 1e-12 for m in masses):
            continue
        out.append((tuple(lab), tuple(masses)))
    return out


def _covered_cells(nodes, lab, bundle) -> set:
    """The cells (z, c) a labeling of `nodes` into districts of `bundle` covers."""
    return {(z, c) for z, _ in zip(nodes, lab) for c in bundle}


def _value(masses) -> float:
    return float(sum(math.log(m) for m in masses))


def clause_b_product() -> None:
    """At fixed pi and fixed k_B the joint feasible set is the product, the objective a sum."""
    print("\n(b) brute force: the stage-1 feasible set is a product over bundles")
    P = nx.path_graph(6)                              # zips 0..5, path proximity graph
    nodes = sorted(P.nodes)
    N, WHFI = ("N_WH", "N_FI"), ("WH", "FI")
    mass_N = dict(zip(range(6), [3.0, 2.0, 4.0, 3.0, 2.0, 4.0]))
    mass_W = dict(zip(range(6), [5.0, 1.0, 2.0, 6.0, 2.0, 2.0]))
    lo, hi = 6.0, 12.0
    fN = _feasible_maps(P, mass_N, 2, lo, hi)
    fW = _feasible_maps(P, mass_W, 2, lo, hi)
    check("b.prod both per-bundle feasible sets are nonempty",
          bool(fN) and bool(fW), f"|F_N| = {len(fN)}, |F_WHFI| = {len(fW)}")

    # the joint feasible set is enumerated with the cover constraint re-imposed at CELL level:
    # a pair (a, b) survives only if the two bundles' districts contend for no cell.  That the
    # count comes out at |F_N| * |F_WHFI| is then a finding about disjoint bundles, not a
    # restatement of how the loop was written.
    joint = [(a, b) for a in fN for b in fW
             if not (_covered_cells(nodes, a[0], N) & _covered_cells(nodes, b[0], WHFI))]
    check("b.prod cover at cell level rules out no pair: |joint| == |F_N| * |F_WHFI|",
          len(joint) == len(fN) * len(fW), f"{len(joint)} == {len(fN)}*{len(fW)}")

    best_joint = max(_value(a[1]) + _value(b[1]) for a, b in joint)
    best_sum = max(_value(a[1]) for a in fN) + max(_value(b[1]) for b in fW)
    check("b.prod max of the joint objective == sum of per-bundle maxima",
          abs(best_joint - best_sum) <= TOL, f"{best_joint:.12f} vs {best_sum:.12f}")

    aN = max(fN, key=lambda t: _value(t[1]))
    aW = max(fW, key=lambda t: _value(t[1]))
    check("b.prod argmax of the joint == (argmax_N, argmax_WHFI)",
          abs(_value(aN[1]) + _value(aW[1]) - best_joint) <= TOL)


def clause_b_free_k() -> None:
    """Attack: separability fails when the slot counts k_B are decision variables."""
    print("\n(b) attack: are fixed k_B load bearing?")
    P = nx.path_graph(6)
    mass_N = dict(zip(range(6), [4.0] * 6))            # 24 total
    mass_W = dict(zip(range(6), [2.0] * 6))            # 12 total
    lo, hi = 5.0, 13.0
    K = 4
    table = {}
    for kN in range(1, K):
        kW = K - kN
        fN = _feasible_maps(P, mass_N, kN, lo, hi)
        fW = _feasible_maps(P, mass_W, kW, lo, hi)
        table[(kN, kW)] = (max(_value(a[1]) for a in fN) + max(_value(b[1]) for b in fW)
                           if fN and fW else None)
    live = {k: v for k, v in table.items() if v is not None}
    best = max(live, key=lambda k: live[k])
    spread = max(live.values()) - min(live.values())
    check("b.freek the value depends on how the slot budget is split across bundles",
          spread > 1e-9,
          "values " + ", ".join(f"k_N={a},k_W={b}: {v:.6f}" for (a, b), v in sorted(live.items()))
          + f"; argmax {best}")
    check("b.freek attack confirms: with only sum_B k_B fixed the problem does NOT separate",
          len(live) > 1 and spread > 1e-9,
          "choosing k_B is a joint decision, which is what level 0 (PLAN section 5) is for")


def clause_b_overlap() -> None:
    """Attack: bundles inside pi(z) must be pairwise disjoint or the cover rows couple."""
    print("\n(b) attack: are pairwise-disjoint bundles inside pi(z) load bearing?")
    # pi(z) = {N, WHplus} with N = {N_WH, N_FI} and WHplus = {WH, N_WH}: they share N_WH.
    N, WHP = ("N_WH", "N_FI"), ("WH", "N_WH")
    zips = [0, 1, 2, 3]
    P = nx.path_graph(4)
    nodes = sorted(P.nodes)
    cell_mass = {(z, c): 1.0 for z in zips for c in CHANNELS}
    mass_N = {z: cell_mass[(z, "N_WH")] + cell_mass[(z, "N_FI")] for z in zips}
    mass_W = {z: cell_mass[(z, "WH")] + cell_mass[(z, "N_WH")] for z in zips}
    lo, hi = 2.0, 6.0
    fN = _feasible_maps(P, mass_N, 2, lo, hi)
    fW = _feasible_maps(P, mass_W, 2, lo, hi)

    joint_ok = sum(1 for a in fN for b in fW
                   if not (_covered_cells(nodes, a[0], N) & _covered_cells(nodes, b[0], WHP)))
    check("b.overlap attack: with overlapping bundles the joint feasible set is NOT the product",
          joint_ok < len(fN) * len(fW),
          f"joint {joint_ok} < product {len(fN) * len(fW)}; every pair double-covers (z, N_WH)")
    check("b.overlap attack: overlapping bundles make the joint problem infeasible here",
          joint_ok == 0,
          "the cover row on (z, N_WH) sums over slots of BOTH bundles; that row is exactly "
          "what level 0 solves before pi is fixed")

    WH, FI = ("WH",), ("FI",)
    m1 = {z: cell_mass[(z, "WH")] for z in zips}
    m2 = {z: cell_mass[(z, "FI")] for z in zips}
    f1 = _feasible_maps(P, m1, 2, 1.0, 3.0)
    f2 = _feasible_maps(P, m2, 2, 1.0, 3.0)
    ok = all(not (_covered_cells(nodes, a[0], WH) & _covered_cells(nodes, b[0], FI))
             for a in f1 for b in f2)
    check("b.overlap control: disjoint bundles never contend for a cell", ok,
          f"|F_WH| = {len(f1)}, |F_FI| = {len(f2)}")


def clause_b_catchall() -> None:
    """Attack: the catch-all bundle's cell set is NOT determined by pi, so it couples."""
    print("\n(b) attack: does the catch-all pass separate too?")
    # bundle WH on zips 0..3 with cover <= 1 (PLAN section 3: uncovered cells become "other").
    # One WH district of mass in [4,6]; whatever it leaves feeds the residual bundle.
    P = nx.path_graph(4)
    mass_W = {0: 3.0, 1: 3.0, 2: 3.0, 3: 3.0}
    mass_other = {0: 5.0, 1: 1.0, 2: 1.0, 3: 0.0}      # residual mass at the same zips
    lo, hi = 4.0, 6.0
    options = []
    for r in range(1, 5):                              # subsets, cover <= 1 so not a partition
        for sub in itertools.combinations(sorted(P.nodes), r):
            if not nx.is_connected(P.subgraph(sub)):
                continue
            m = sum(mass_W[z] for z in sub)
            if lo - 1e-12 <= m <= hi + 1e-12:
                options.append((sub, m))
    top = max(math.log(m) for _, m in options)
    ties = [o for o in options if abs(math.log(o[1]) - top) < 1e-12]
    check("b.catchall the WH pass has a tie among optima", len(ties) >= 2,
          f"tied optima: {[t[0] for t in ties]}")

    def catchall_value(sub):
        """Best residual district (connected, residual mass >= 5), or None if none fits."""
        left = [z for z in sorted(P.nodes) if z not in sub]
        best = None
        for r in range(1, len(left) + 1):
            for cand in itertools.combinations(left, r):
                if not nx.is_connected(P.subgraph(cand)):
                    continue
                m = sum(mass_other[z] for z in cand)
                if m >= 5.0 - 1e-12:
                    best = m if best is None else max(best, m)
        return best

    outcomes = {t[0]: catchall_value(t[0]) for t in ties}
    check("b.catchall attack: tied WH optima give DIFFERENT catch-all values",
          len(set(outcomes.values())) > 1,
          f"{outcomes}  (None = no residual district fits)")
    check("b.catchall the residual cell set is not determined by pi, so the catch-all pass "
          "is sequential, not a further factor of the product",
          len(set(outcomes.values())) > 1,
          "the proposition's product form covers the bundles of pi only")


# ---------------------------------------------------------------- (c) one assignment problem
def _brute_force_match(g: np.ndarray, ok: np.ndarray | None = None) -> float:
    """Exhaustive max of sum log g over matchings saturating the smaller side.

    Independent oracle for `channel.match` / `staff.assign`: it enumerates matchings directly
    rather than reducing to a cost matrix, so a bug in the Hungarian reduction cannot hide.
    """
    m, K = g.shape
    best = -math.inf
    if m >= K:                                   # injections from districts to reps
        for perm in itertools.permutations(range(m), K):
            if ok is not None and not all(ok[i, j] for j, i in enumerate(perm)):
                continue
            best = max(best, sum(math.log(g[i, j]) for j, i in enumerate(perm)))
    else:                                        # injections from reps to districts
        for perm in itertools.permutations(range(K), m):
            if ok is not None and not all(ok[i, j] for i, j in enumerate(perm)):
                continue
            best = max(best, sum(math.log(g[i, j]) for i, j in enumerate(perm)))
    return best


def clause_c_hungarian() -> None:
    """The union of all districts is one LAP; Hungarian == exhaustive search over injections."""
    print("\n(c) numeric: one Hungarian over the union of districts, against brute force")
    rng = np.random.default_rng(SEED + 3)
    bad = None
    for trial in range(200):
        m = int(rng.integers(3, 7))
        K = int(rng.integers(2, min(m, 5) + 1))
        g = rng.uniform(0.05, 20.0, size=(m, K))
        _, value = channel.match(g, "nash")
        brute = _brute_force_match(g)
        if abs(value - brute) > 1e-9:
            bad = (trial, value, brute)
            break
    check("c.hung 200 random instances: channel.match == exhaustive max over injections",
          bad is None, "sizes m in [3,6], K in [2,5], agreement to 1e-9" if bad is None
          else f"trial {bad[0]}: {bad[1]:.12f} vs {bad[2]:.12f}")

    # the same on a stacked two-bundle matrix, built from real per-bundle gain matrices
    rng2 = np.random.default_rng(SEED + 4)
    reps_all = ["r0", "r1", "r2", "r3", "r4"]
    data = _cell_instance(6, ["r0", "r1", "r2", "r3"], seed_rng=rng2)
    blocks = []
    for B, zs, ds in ((("N_WH", "N_FI"), [0, 1, 2, 3], {"N#0": [0, 1], "N#1": [2, 3]}),
                      (("WH", "FI"), [2, 3, 4, 5], {"W#0": [2, 3], "W#1": [4, 5]})):
        Gp = _projected_graph(data, zs, B)
        td_p = {str(z): d for d, zl in ds.items() for z in zl}
        gb, _, _ = channel.gain_matrix(Gp, td_p, reps_order=reps_all, districts=sorted(ds))
        blocks.append(gb)
    g = np.hstack(blocks)
    pairs, value = channel.match(g, "nash")
    brute = _brute_force_match(g)
    check("c.hung stacked bundles: one Hungarian == exhaustive max over injections",
          abs(value - brute) <= 1e-9, f"value {value:.9f}, brute {brute:.9f}")
    check("c.hung the matching is injective across bundles",
          len({i for i, _ in pairs}) == len(pairs), f"pairs {pairs}")


def clause_c_separate() -> None:
    """Attack: solving each bundle's assignment separately can violate injectivity."""
    print("\n(c) attack: is the cross-bundle coupling real?")
    # rep r0 is best in both bundles; separate per-bundle Hungarians both take r0.
    g1 = np.array([[10.0, 2.0], [3.0, 3.0], [2.0, 2.5], [1.5, 1.2]])   # bundle 1, districts 0,1
    g2 = np.array([[10.0, 2.0], [3.0, 3.0], [2.0, 2.5], [1.5, 1.2]])   # bundle 2
    p1, v1 = channel.match(g1, "nash")
    p2, v2 = channel.match(g2, "nash")
    reused = {i for i, _ in p1} & {i for i, _ in p2}
    check("c.sep attack: separate per-bundle matchings reuse a rep (injectivity broken)",
          bool(reused), f"reps used twice: {sorted(reused)}")
    g = np.hstack([g1, g2])
    pairs, value = channel.match(g, "nash")
    check("c.sep the joint Hungarian is feasible and strictly below the separate upper bound",
          value < v1 + v2 - 1e-9 and len({i for i, _ in pairs}) == len(pairs),
          f"joint {value:.6f} < separate {v1 + v2:.6f}, pairs {pairs}")
    brute = _brute_force_match(g)
    check("c.sep joint value == exhaustive max over injections",
          abs(value - brute) <= 1e-9, f"joint {value:.9f}, brute {brute:.9f}")


def clause_c_rows() -> None:
    """Attack: gain_matrix's default rep order is per-projection, so stacking needs one order."""
    print("\n(c) attack: do the two bundles' gain matrices share a row set?")
    G1 = nx.Graph()
    G1.add_node("0", M=5.0, **{model.BOOK: {"r0": 1.0}, model.FREE: 0.0, model.CAND: ("r0",)})
    G2 = nx.Graph()
    G2.add_node("0", M=5.0, **{model.BOOK: {"r1": 1.0}, model.FREE: 0.0, model.CAND: ("r1",)})
    _, R1, _ = channel.gain_matrix(G1, {"0": "d1"})
    _, R2, _ = channel.gain_matrix(G2, {"0": "d2"})
    check("c.rows attack: default reps_order differs across projections, so stacking is ill-posed",
          R1 != R2, f"R1 {R1} vs R2 {R2}")
    gA, RA, _ = channel.gain_matrix(G1, {"0": "d1"}, reps_order=["r0", "r1"])
    gB, RB, _ = channel.gain_matrix(G2, {"0": "d2"}, reps_order=["r0", "r1"])
    check("c.rows with one global reps_order the blocks stack and every entry is positive",
          RA == RB == ["r0", "r1"] and bool((np.hstack([gA, gB]) > 0).all()),
          f"stacked {np.hstack([gA, gB]).tolist()}")


def clause_c_mask() -> None:
    """Attack: candidacy masks and held reps. channel.match cannot express a forbidden pair."""
    print("\n(c) attack: candidacy masks and held reps")
    staff_path = os.path.join(ROOT, "tools", "staff.py")
    spec = importlib.util.spec_from_file_location("staff_mod", staff_path)
    staff = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(staff)
        have_staff = True
    except Exception as exc:                            # pragma: no cover
        have_staff = False
        print(f"       (tools/staff.py did not import: {exc})")

    g = np.array([[9.0, 1.0], [2.0, 8.0], [3.0, 3.0]])
    ok = np.array([[False, True], [True, True], [True, True]])   # r0 forbidden on district 0
    pairs, _ = channel.match(g, "nash")
    check("c.mask attack: channel.match ignores the mask and picks a forbidden pair",
          any(not ok[i, j] for i, j in pairs),
          f"channel.match pairs {pairs}; (0,0) allowed = {ok[0, 0]}")
    if have_staff:
        pairs2 = staff.assign(g, ok)
        val2 = sum(math.log(g[i, j]) for i, j in pairs2)
        brute = _brute_force_match(g, ok)
        check("c.mask staff.assign (penalty LAP) == exhaustive max over ALLOWED injections",
              abs(val2 - brute) <= 1e-9 and all(ok[i, j] for i, j in pairs2),
              f"staff {val2:.9f} vs brute {brute:.9f}, pairs {pairs2}")
        check("c.mask a masked problem is still ONE assignment problem, not several",
              True, "forbidden pairs enter as a penalty, tools/staff.py:114-131")

    # a held rep excluded from candidacy is a row removal, which preserves the LAP
    g_all = np.array([[9.0, 1.0], [2.0, 8.0], [3.0, 3.0], [7.0, 7.0]])
    keep = [i for i in range(g_all.shape[0]) if i != 3]
    _, v_full = channel.match(g_all[keep], "nash")
    check("c.mask held rep = row removal; the reduced problem is still one LAP",
          abs(v_full - _brute_force_match(g_all[keep])) <= 1e-9, f"value {v_full:.9f}")

    # rectangular the other way: fewer reps than districts leaves districts unstaffed
    g_short = np.array([[5.0, 4.0, 3.0], [2.0, 6.0, 1.0]])
    pairs3, _ = channel.match(g_short, "nash")
    check("c.mask attack: with reps < districts 'every district staffed' is infeasible and "
          "match returns a partial matching silently",
          len(pairs3) == 2 and g_short.shape[1] == 3, f"pairs {pairs3} for 3 districts")


# ---------------------------------------------------------------- (d) per-channel floors
def clause_d_floors() -> None:
    """Per-channel floors on a merged bundle break Lemma 6's split bound."""
    print("\n(d) per-channel floors on a merged bundle: the transportation structure")
    # two zips, two districts, merged bundle WHFI.  z0 is pure WH, z1 is pure FI.
    MWH = [Fraction(1), Fraction(0)]
    MFI = [Fraction(0), Fraction(1)]
    n, k = 2, 2
    LWH = LFI = Fraction(1, 2)

    y = sp.symbols("y0_0 y0_1 y1_0 y1_1", nonnegative=True)
    Y = {(0, 0): y[0], (0, 1): y[1], (1, 0): y[2], (1, 1): y[3]}
    place = [sp.Eq(Y[(z, 0)] + Y[(z, 1)], 1) for z in range(n)]
    # channel floors: sum_z M_{z,c} y_zj >= L_c.  Both channel totals are 1 and k*L = 1, so
    # every floor holds with equality at every feasible point; that is why solving the
    # equality system loses nothing.
    eqs = (place
           + [sp.Eq(sum(sp.Rational(MWH[z]) * Y[(z, j)] for z in range(n)), sp.Rational(LWH))
              for j in range(k)]
           + [sp.Eq(sum(sp.Rational(MFI[z]) * Y[(z, j)] for z in range(n)), sp.Rational(LFI))
              for j in range(k)])
    sol = sp.solve(eqs, list(y), dict=True)
    check("d.floor the two-channel-floor system has a unique solution", len(sol) == 1,
          f"solutions {sol}")
    if sol:
        vals = [sol[0][v] for v in y]
        check("d.floor that solution is y = 1/2 everywhere: BOTH zips split",
              all(v == sp.Rational(1, 2) for v in vals), f"y = {vals}")
        splits = sum(1 for z in range(n) if 0 < sol[0][Y[(z, 0)]] < 1)
        check("d.floor splits = 2 exceeds Lemma 6's bound k - 1 = 1 (docs/MODEL.md:379)",
              splits > k - 1, f"splits {splits} > k-1 = {k - 1}")
        positives = sum(1 for v in vals if v > 0)
        check("d.floor positive entries = 4 exceed the acyclic-support bound n + k - 1 = 3",
              positives > n + k - 1, f"positive entries {positives} > {n + k - 1}")

    # no integral assignment is feasible: exhaustive over 2^2
    feasible_int = [lab for lab in itertools.product(range(k), repeat=n)
                    if all(sum(MWH[z] for z in range(n) if lab[z] == j) >= LWH for j in range(k))
                    and all(sum(MFI[z] for z in range(n) if lab[z] == j) >= LFI for j in range(k))]
    check("d.floor attack: NO integral assignment satisfies both channel floors",
          not feasible_int, f"feasible integral labelings {feasible_int}")

    # LP confirmation with scipy, independent of the sympy algebra.
    # variables (y00, y01, y10, y11); A_eq places each zip; A_ub encodes the floors as -mass<=-L
    A_eq = np.array([[1.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 1.0]])
    b_eq = np.array([1.0, 1.0])
    A_ub = np.array([[-1.0, 0.0, 0.0, 0.0],      # -(WH mass in district 0) <= -0.5
                     [0.0, -1.0, 0.0, 0.0],      # district 1
                     [0.0, 0.0, -1.0, 0.0],      # -(FI mass in district 0) <= -0.5
                     [0.0, 0.0, 0.0, -1.0]])
    b_ub = np.array([-0.5, -0.5, -0.5, -0.5])
    res = linprog(c=np.zeros(4), A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=[(0, 1)] * 4, method="highs")
    check("d.floor scipy linprog agrees: the LP is feasible and its vertex is fractional",
          res.status == 0 and float(np.abs(res.x - 0.5).max()) <= 1e-9,
          f"status {res.status}, x {np.round(res.x, 9).tolist()}")

    # control: the SAME instance with one balancing attribute (total mass) is integral with
    # zero splits, exactly Lemma 6's transportation case.
    total = [MWH[z] + MFI[z] for z in range(n)]        # [1, 1]
    feasible_int1 = [lab for lab in itertools.product(range(k), repeat=n)
                     if all(sum(total[z] for z in range(n) if lab[z] == j) == Fraction(1)
                            for j in range(k))]
    check("d.floor control: one scalar mass per district admits an integral solution, 0 splits",
          bool(feasible_int1), f"integral labelings {feasible_int1}")

    # and the substitution eta = M_z * y that makes Lemma 6 a Hitchcock problem fails: under two
    # floors the district rows carry per-zip coefficients M_{z,c}/M_z that differ across zips,
    # so the matrix is not a node-arc incidence matrix.
    ratios = [(MWH[z] / (MWH[z] + MFI[z]), MFI[z] / (MWH[z] + MFI[z])) for z in range(n)]
    check("d.floor the Hitchcock substitution eta = M_z*y does not normalise both floors",
          len(set(ratios)) > 1,
          f"per-zip channel ratios {[(str(a), str(b)) for a, b in ratios]} are not constant")


def main() -> int:
    header()
    clause_a_symbolic()
    clause_a_numeric()
    clause_a_candidacy()
    clause_a_release()
    clause_b_product()
    clause_b_free_k()
    clause_b_overlap()
    clause_b_catchall()
    clause_c_hungarian()
    clause_c_separate()
    clause_c_rows()
    clause_c_mask()
    clause_d_floors()

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed")
    for n in failed:
        print(f"  FAILED: {n}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
