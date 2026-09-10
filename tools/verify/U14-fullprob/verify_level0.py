"""verify_level0.py -- adversarial verification of td/solvers/level0.py against
docs/FULL_PROBLEM.md section 5 and section 6, and against PLAN.md's level-0 mapping table.

Run from the worktree root with the hub's interpreter::

    /Users/ntlee/projects/td/.venv/bin/python3 tools/verify/U14-fullprob/verify_level0.py

Every check is an oracle the implementation does not share: constraint rows are read back
symbolically from the assembled sparse matrix and compared with rows written out by hand from
the spec, contiguity and coverage claims are checked by enumeration or by a second solve on a
hand-built instance with a known answer, and the flow block is compared byte for byte with
`state_splits.build_milp`'s own flow block on the same graph.  Nothing here is discovered by
`tests/run_all.py`; it never gates the suite.
"""
from __future__ import annotations

import itertools
import math
import sys
import time
from types import SimpleNamespace

import numpy as np
from scipy import sparse

from td.solvers import level0
from td.solvers import milp_engines as me
from td.solvers import state_splits as ss

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


# --------------------------------------------------------------------------- fixtures
EDGES6 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]      # the path used by tests/test_level0.py


def cells(M: np.ndarray, channels: tuple[str, ...]) -> SimpleNamespace:
    M = np.asarray(M, float)
    return SimpleNamespace(M=M, channels=channels,
                           state_list=[f"S{s}" for s in range(M.shape[0])])


def rowmap(problem, name: str) -> list[dict[int, float]]:
    """The named row block as a list of {column: coefficient}, read back from `A`."""
    lo, hi = problem.rows[name]
    A = problem.A.tocsr()[lo:hi]
    out = []
    for r in range(A.shape[0]):
        s, e = A.indptr[r], A.indptr[r + 1]
        out.append({int(c): float(v) for c, v in zip(A.indices[s:e], A.data[s:e]) if v != 0.0})
    return out


def bounds(problem, name: str) -> tuple[np.ndarray, np.ndarray]:
    lo, hi = problem.rows[name]
    return problem.lb[lo:hi], problem.ub[lo:hi]


# ------------------------------------------------------- 1. row by row against section 5
def rows_against_spec() -> None:
    """Every row block written out by hand from section 5 and compared with the matrix."""
    rng = np.random.default_rng(7)
    S, C = 6, 3
    M = rng.random((S, C)) * 0.4
    prior = np.zeros((S, C))
    prior[2, 1] = 0.4
    prior[5, 0] = 1.0
    bundles = {"A": ("c0",), "AB": ("c0", "c1"), "C": ("c2",)}
    chans = ("c0", "c1", "c2")
    L, U, eta = 0.8, 1.2, 0.05
    xy = np.array([[float(s), 0.0] for s in range(S)])
    p = level0.build_level0(cells(M, chans), bundles, edges=EDGES6, L=L, U=U, eta=eta,
                            prior=prior, n_max=3, dist_max=2.5, state_xy=xy, order_mass=True)
    K, tau = p.k, p.tau
    off_z, off_y, off_r, off_u = p.off_z, p.off_y, p.off_r, p.off_u

    # tau = (L + U) / 2 and the 1 -/+ delta rewrite reproduces L and U exactly
    check("tau = (L+U)/2", tau == (L + U) / 2.0)
    check("(1 - delta) * tau == L exactly", (1.0 - p.delta) * tau == L,
          f"{(1.0 - p.delta) * tau!r} vs {L!r}")
    check("(1 + delta) * tau == U exactly", (1.0 + p.delta) * tau == U,
          f"{(1.0 + p.delta) * tau!r} vs {U!r}")

    # cover: sum over exactly the slots whose bundle carries c, ub = 1 - prior
    cov = rowmap(p, "cover")
    lo_c, hi_c = bounds(p, "cover")
    ok, why = True, ""
    for s in range(S):
        for ci, cname in enumerate(chans):
            want = {off_y + s * K + j: 1.0 for j in range(K)
                    if cname in p.bundles[p.bundle_of[j]]}
            got = cov[s * C + ci]
            if got != want:
                ok, why = False, f"(s={s}, c={cname}): {got} != {want}"
            if abs(hi_c[s * C + ci] - (1.0 - prior[s, ci])) > 0 or lo_c[s * C + ci] != -np.inf:
                ok, why = False, f"(s={s}, c={cname}) bound {hi_c[s * C + ci]}"
    check("cover rows sum exactly the slots whose bundle contains c, ub = 1 - prior", ok, why)

    # eta z <= y <= z <= u
    yz, yzl, zu = rowmap(p, "yz"), rowmap(p, "yz_lo"), rowmap(p, "zu")
    ok = all(
        yz[s * K + j] == {off_y + s * K + j: 1.0, off_z + s * K + j: -1.0}
        and yzl[s * K + j] == {off_z + s * K + j: eta, off_y + s * K + j: -1.0}
        and zu[s * K + j] == {off_z + s * K + j: 1.0, off_u + j: -1.0}
        for s in range(S) for j in range(K))
    ok = ok and (bounds(p, "yz")[1] == 0).all() and (bounds(p, "yz_lo")[1] == 0).all() \
        and (bounds(p, "zu")[1] == 0).all()
    check("eta z <= y <= z <= u, one row each per (s, j)", ok)

    # band: L u_j <= sum_s W_sj y_sj <= U u_j, scaled by tau
    band_ok, why = True, ""
    for nm, bound, want_lo, want_hi in (("band_lo", L, 0.0, np.inf),
                                        ("band_hi", U, -np.inf, 0.0)):
        rm, (blo, bhi) = rowmap(p, nm), bounds(p, nm)
        for j in range(K):
            want = {off_y + s * K + j: p.W[s, j] / tau for s in range(S) if p.W[s, j] != 0}
            want[off_u + j] = -bound / tau
            if set(rm[j]) != set(want) or any(abs(rm[j][c] - v) > 1e-15 for c, v in want.items()):
                band_ok, why = False, f"{nm} row {j}"
            if blo[j] != want_lo or bhi[j] != want_hi:
                band_ok, why = False, f"{nm} bounds {blo[j]}, {bhi[j]}"
    check("band rows are (W/tau) y - (L or U)/tau * u, one per slot", band_ok, why)
    # the same rows in unscaled form recover L and U
    check("band rewrite is exact: (L/tau) = 1 - delta, (U/tau) = 1 + delta",
          abs(L / tau - (1 - p.delta)) == 0.0 and abs(U / tau - (1 + p.delta)) == 0.0)

    # root: sum_s r_sj = u_j;  rz: r <= z
    rt, (rlo, rhi) = rowmap(p, "root"), bounds(p, "root")
    ok = all(rt[j] == {**{off_r + s * K + j: 1.0 for s in range(S)}, off_u + j: -1.0}
             for j in range(K)) and (rlo == 0).all() and (rhi == 0).all()
    check("root row is sum_s r_sj - u_j = 0", ok)
    rz = rowmap(p, "rz")
    check("rz row is r_sj - z_sj <= 0",
          all(rz[s * K + j] == {off_r + s * K + j: 1.0, off_z + s * K + j: -1.0}
              for s in range(S) for j in range(K)))

    # caps
    cn, (nlo, nhi) = rowmap(p, "cap_n"), bounds(p, "cap_n")
    check("cap_n row is sum_s z_sj <= n_max, one per slot",
          all(cn[j] == {off_z + s * K + j: 1.0 for s in range(S)} for j in range(K))
          and (nhi == 3.0).all())

    a, b = np.nonzero(np.triu(np.abs(xy[:, None, 0] - xy[None, :, 0]) > 2.5, k=1))
    P = len(a)
    cd, (dlo, dhi) = rowmap(p, "cap_dist"), bounds(p, "cap_dist")
    want_rows = [{off_z + int(a[i]) * K + j: 1.0, off_z + int(b[i]) * K + j: 1.0}
                 for i in range(P) for j in range(K)]
    check("cap_dist is one row per (far pair, slot): z_sj + z_s'j <= 1",
          len(cd) == P * K and cd == want_rows and (dhi == 1.0).all(),
          f"P={P} K={K}; empty rows in the block: {sum(1 for r in cd if not r)}")

    # ordering
    ou = rowmap(p, "order_u")
    want_u = [{off_u + j + 1: 1.0, off_u + j: -1.0}
              for lo_j, hi_j in p.slots.values() for j in range(lo_j, hi_j - 1)]
    check("order_u is u_{j+1} - u_j <= 0 inside each bundle only",
          ou == want_u and (bounds(p, "order_u")[1] == 0).all())
    om = rowmap(p, "order_mass")
    ok, why = True, ""
    q = 0
    for lo_j, hi_j in p.slots.values():
        for j in range(lo_j, hi_j - 1):
            want = {}
            for s in range(S):
                if p.W[s, j + 1]:
                    want[off_y + s * K + j + 1] = p.W[s, j + 1] / tau
                if p.W[s, j]:
                    want[off_y + s * K + j] = -p.W[s, j] / tau
            if set(om[q]) != set(want) or any(abs(om[q][c] - v) > 1e-15
                                              for c, v in want.items()):
                ok, why = False, f"order_mass row {q}"
            q += 1
    check("order_mass is mass_{j+1} - mass_j <= 0 inside each bundle", ok and q == len(om), why)

    # anchors and forbid_bundle
    p2 = level0.build_level0(cells(M, chans), bundles, edges=EDGES6, L=L, U=U, eta=eta,
                             anchors=[(1, 0)])
    check("anchors are var_lb = 1 on z and add no row",
          p2.var_lb[p2.off_z + 1 * p2.k + 0] == 1.0
          and set(p2.rows) == set(level0.build_level0(cells(M, chans), bundles, edges=EDGES6,
                                                      L=L, U=U, eta=eta,
                                                      order_mass=False).rows))
    check("order_mass defaults off with anchors, off with D, on otherwise",
          "order_mass" not in p2.rows
          and "order_mass" not in level0.build_level0(
              cells(M, chans), bundles, edges=EDGES6, L=L, U=U, eta=eta,
              D=np.ones((S, p2.k))).rows
          and "order_mass" in level0.build_level0(
              cells(M, chans), bundles, edges=EDGES6, L=L, U=U, eta=eta).rows)
    f = level0.forbid_bundle(p, 3, "AB")
    lo_j, hi_j = p.slots["AB"]
    ok = all(f.var_lb[o + 3 * K + j] == 0.0 and f.var_ub[o + 3 * K + j] == 0.0
             for j in range(lo_j, hi_j) for o in (f.off_z, f.off_y))
    other = [j for j in range(K) if not (lo_j <= j < hi_j)]
    ok = ok and all(f.var_ub[f.off_z + 3 * K + j] == 1.0 for j in other)
    ok = ok and (p.var_ub[p.off_z + 3 * K + lo_j] == 1.0)          # the original is untouched
    check("forbid_bundle zeroes both bounds on z and y for every slot of the bundle only", ok)


# --------------------------------------------- 2. the flow block is level 1's, byte for byte
def flow_block_identical_to_level1() -> None:
    S = 6
    M = np.arange(1, S * 2 + 1, dtype=float).reshape(S, 2) / 10.0
    p = level0.build_level0(cells(M, ("c0", "c1")), {"AB": ("c0", "c1")}, edges=EDGES6,
                            L=0.8, U=1.2, eta=0.05)
    K = p.k
    q = ss.build_milp(np.ones(S), np.zeros((S, K)), EDGES6, tau=1.0, delta=0.2, eps=0.0,
                      eta=0.05)
    ok = True
    for name in ("yz", "yz_lo", "rz", "flow_tail", "flow_head", "net"):
        lo0, hi0 = p.rows[name]
        lo1, hi1 = q.rows[name]
        A0 = p.A.tocsr()[lo0:hi0, :p.off_u].toarray()
        A1 = q.A.tocsr()[lo1:hi1, :q.n_var].toarray()
        same = A0.shape == A1.shape and np.array_equal(A0, A1)
        same = same and np.array_equal(p.lb[lo0:hi0], q.lb[lo1:hi1])
        same = same and np.array_equal(p.ub[lo0:hi0], q.ub[lo1:hi1])
        if not same:
            ok = False
            print(f"      block {name} differs")
    check("flow, yz, yz_lo and rz blocks equal build_milp's at k = K (columns before u)", ok)
    check("variable layout: z, y, r, f then u, n_var = off_u + K",
          (p.off_z, p.off_y, p.off_r, p.off_f) == (0, S * K, 2 * S * K, 3 * S * K)
          and p.off_u == p.off_f + 2 * len(EDGES6) * K and p.n_var == p.off_u + K
          and (p.var_ub[p.off_f:p.off_u] == S - 1.0).all()
          and (p.var_ub[p.off_u:] == 1.0).all()
          and p.integrality[p.off_u:].all()
          and not p.integrality[p.off_y:p.off_r].any())


# ------------------------------------------------- 3. the engine seam reads the subclass back
def engine_seam_on_the_subclass() -> None:
    S = 6
    M = np.full((S, 1), 0.5)
    p = level0.build_level0(cells(M, ("c0",)), {"A": ("c0",)}, edges=EDGES6,
                            L=0.8, U=1.2, eta=0.05)
    K = p.k
    x = np.zeros(p.n_var)
    z = np.zeros((S, K), bool)
    z[0:3, 0] = True
    z[3:6, 1] = True
    y = np.where(z, 2.0 / 3.0, 0.0)
    x[p.off_z:p.off_z + S * K] = z.ravel().astype(float)
    x[p.off_y:p.off_y + S * K] = y.ravel()
    dec = me._decode_x(p, x)
    check("_decode_x slices z and y in the subclass layout",
          np.array_equal(dec["z"], z) and np.allclose(dec["y"], y)
          and np.allclose(dec["masses"][:2], 1.0) and dec["contacts"] == 6
          and dec["splits"] == 0 and list(dec["used"][:2]) == [True, True])
    cut = me.with_cutoff(p, 1)
    lo, hi = cut.rows["cutoff"]
    row = cut.A.tocsr()[lo:hi]
    check("with_cutoff on Level0Problem bounds sum z at n_state + s* - 1 (fewer contacts)",
          type(cut) is level0.Level0Problem
          and set(row.indices.tolist()) == set(range(p.off_z, p.off_z + S * K))
          and cut.ub[lo] == float(S + 1 - 1))
    fx = me.fix_roots(p, [(2, 0)])
    check("fix_roots keeps the subclass and touches only the r block of that slot",
          type(fx) is level0.Level0Problem and fx.var_lb[fx.off_r + 2 * K + 0] == 1.0
          and all(fx.var_ub[fx.off_r + s * K] == 0.0 for s in range(S) if s != 2)
          and np.array_equal(fx.var_ub[fx.off_u:], p.var_ub[p.off_u:])
          and p.var_ub[p.off_r + 0 * K] == 1.0)
    cl = me._clone(p)
    check("_clone keeps the level-0 fields", type(cl) is level0.Level0Problem
          and cl.off_u == p.off_u and np.array_equal(cl.W, p.W) and cl.slots == p.slots)


def parent_decode_regression() -> None:
    """`SplitProblem.decode_zy` must reproduce the pre-refactor body of `_solve_scipy`
    (`git show main:td/solvers/state_splits.py`, lines 735-747) on a level-1 problem."""
    S, k = 6, 2
    M_s = np.array([0.5, 0.4, 0.6, 0.5, 0.5, 0.5])
    D = np.abs(np.random.default_rng(3).normal(size=(S, k)))
    p = ss.build_milp(M_s, D, EDGES6, tau=1.5, delta=0.1, eps=1e-6, eta=0.01)
    res = ss.solve(p)
    z, y = res["z"], res["y"]
    z0 = np.asarray(z, bool).reshape(S, k)
    y0 = np.clip(np.asarray(y, float).reshape(S, k), 0.0, 1.0)
    y0 = np.where(z0, y0, 0.0)
    y0 = y0 / y0.sum(axis=1, keepdims=True)                    # the old bare division
    masses = p.M_s @ y0
    old = dict(z=z0, y=y0, masses=masses, splits=int(z0.sum() - S),
               split_states=[s for s in range(S) if int(z0[s].sum()) >= 2],
               spread_rel=float((masses.max() - masses.min()) / masses.mean()),
               max_dev_rel=float(np.abs(masses - p.tau).max() / p.tau))
    new = p.decode_zy(z, y)
    ok = set(new) == set(old) and all(np.allclose(new[key], old[key]) for key in old
                                      if key != "split_states")
    ok = ok and new["split_states"] == old["split_states"]
    check("parent decode_zy reproduces the pre-refactor _solve_scipy body on level 1", ok)
    # the one behaviour difference is unreachable at level 1: `place` forces sum_j y_sj = 1,
    # so no row of `np.where(z, y, 0)` sums to zero and the guarded division never differs.
    lo, hi = p.rows["place"]
    check("level 1's place row makes the guarded division equivalent to the old one",
          (p.lb[lo:hi] == 1.0).all() and (p.ub[lo:hi] == 1.0).all())


# ------------------------------------------------------------------ 4. K_B is enough slots
def k_b_is_enough() -> None:
    """A slot carries mass in [L, U] when used, so a plan covering total mass T uses at most
    floor(T / L) slots, and T is at most `avail`; K_B = ceil(avail / L) >= floor(avail / L).
    Checked numerically over random instances, and against a solve with three extra slots."""
    rng = np.random.default_rng(11)
    ok_arith = True
    for _ in range(2000):
        avail = float(rng.random() * 50)
        L = float(rng.random() * 2 + 0.1)
        K = int(math.ceil(avail / L - 1e-9)) if avail > 0 else 0
        if K < math.floor(avail / L + 1e-12):
            ok_arith = False
    check("K_B = ceil(avail/L) is at least floor(avail/L), the most slots any cover can use",
          ok_arith)

    # a direct solve: adding three slots to the bundle cannot raise the covered mass
    M = np.array([[0.5], [0.5], [0.4], [0.3], [0.5], [0.5]])
    base = level0.build_level0(cells(M, ("c0",)), {"A": ("c0",)}, edges=EDGES6,
                               L=0.8, U=1.2, eta=0.05)
    v0 = level0.solve_passes(base, [level0.cover_pass(base, ["A"])])["passes"][0]["value"]
    wide = _with_extra_slots(M, ("c0",), {"A": ("c0",)}, extra=3)
    v1 = level0.solve_passes(wide, [level0.cover_pass(wide, ["A"])])["passes"][0]["value"]
    check("three extra slots buy no coverage over K_B",
          wide.k == base.k + 3 and abs(v0 - v1) < 1e-6,
          f"K_B={base.k} covers {v0:.6f}; K={wide.k} covers {v1:.6f}")
    # the same on a merged bundle under a partial prior, where `avail` over-counts
    M2 = np.array([[0.5, 0.5]] * 6)
    prior = np.zeros((6, 2))
    prior[0, 1] = 1.0
    prior[3, 0] = 1.0
    b2 = {"AB": ("c0", "c1")}
    p2 = level0.build_level0(cells(M2, ("c0", "c1")), b2, edges=EDGES6, L=0.8, U=1.2,
                             eta=0.05, prior=prior)
    w2 = _with_extra_slots(M2, ("c0", "c1"), b2, extra=3, prior=prior)
    v2 = level0.solve_passes(p2, [level0.cover_pass(p2, ["AB"])])["passes"][0]["value"]
    v3 = level0.solve_passes(w2, [level0.cover_pass(w2, ["AB"])])["passes"][0]["value"]
    reach = float((M2 * (1.0 - prior)).sum())
    check("merged bundle under a partial prior: K_B still covers everything reachable",
          w2.k == p2.k + 3 and abs(v2 - v3) < 1e-6,
          f"K_B={p2.k} covers {v2:.4f}, K={w2.k} covers {v3:.4f}, "
          f"avail counted {reach:.4f}")


def _with_extra_slots(M, chans, bundles, *, extra: int, prior=None):
    """The same model with exactly `extra` more slots per bundle and no more reachable mass.

    `extra` padding states of mass `L` each are appended with no prior (so `slot_counts` sees
    `avail + extra * L` and `ceil((X + extra*L)/L) = ceil(X/L) + extra`), with no edge to the
    real graph, and are then closed off with `forbid_bundle`, which runs after the slot count
    is fixed.  So the extra slots exist and nothing new can go into them.
    """
    M = np.asarray(M, float)
    S, C = M.shape
    pad = np.zeros((extra, C))
    pad[:, 0] = 0.8                                   # exactly L, so K grows by `extra`
    Mx = np.vstack([M, pad])
    pr = np.vstack([np.asarray(prior, float) if prior is not None else np.zeros((S, C)),
                    np.zeros((extra, C))])
    p = level0.build_level0(cells(Mx, chans), bundles, edges=EDGES6, L=0.8, U=1.2, eta=0.05,
                            prior=pr)
    for s in range(S, S + extra):
        for name in list(p.slots):
            p = level0.forbid_bundle(p, s, name)
    return p


# --------------------------------------------------- 5. contiguity at the channel level
def contiguity_through_a_committed_state() -> None:
    edges3 = [(0, 1), (1, 2)]
    M = np.array([[0.5, 0.5], [0.0, 0.0], [0.5, 0.5]])
    b = {"A": ("c0",)}
    free = level0.build_level0(cells(M, ("c0", "c1")), b, edges=edges3, L=0.8, U=1.2, eta=0.05)
    out = level0.solve_passes(free, [level0.cover_pass(free, ["A"])])
    check("free: the zero-mass middle state bridges 0 and 2, cover 1.0",
          abs(out["passes"][0]["value"] - 1.0) < 1e-6 and bool(out["z"][1].any()),
          f"value {out['passes'][0]['value']:.6f}")

    prior = np.zeros((3, 2))
    prior[1, 0] = 1.0                                    # channel c0 of state 1 committed
    p = level0.build_level0(cells(M, ("c0", "c1")), b, edges=edges3, L=0.8, U=1.2, eta=0.05,
                            prior=prior)
    out = level0.solve_passes(p, [level0.cover_pass(p, ["A"])])
    check("a committed middle state cannot bridge: cover falls to 0 and z_1 stays off",
          abs(out["passes"][0]["value"]) < 1e-9 and not out["z"][1].any()
          and not out["z"].any(),
          f"value {out['passes'][0]['value']:.6f}")

    # the merged-bundle variant: committing *one* channel of the bundle is enough, because
    # every cover row of the bundle bounds the same y_1j
    b2 = {"AB": ("c0", "c1")}
    prior2 = np.zeros((3, 2))
    prior2[1, 1] = 1.0                                   # only channel c1 committed
    M2 = np.array([[0.25, 0.25], [0.0, 0.0], [0.25, 0.25]])   # neither end reaches L alone
    p2 = level0.build_level0(cells(M2, ("c0", "c1")), b2, edges=edges3, L=0.8, U=1.2,
                             eta=0.05, prior=prior2)
    out2 = level0.solve_passes(p2, [level0.cover_pass(p2, ["AB"])])
    free2 = level0.build_level0(cells(M2, ("c0", "c1")), b2, edges=edges3, L=0.8, U=1.2,
                                eta=0.05)
    outf = level0.solve_passes(free2, [level0.cover_pass(free2, ["AB"])])
    check("one committed channel of a merged bundle is enough to refuse the bridge",
          abs(outf["passes"][0]["value"] - 1.0) < 1e-6
          and abs(out2["passes"][0]["value"]) < 1e-9,
          f"free {outf['passes'][0]['value']:.4f}, committed {out2['passes'][0]['value']:.4f}")


# ---------------------------------------------------------------- 6. the caps, discriminating
def dist_max_row_semantics() -> None:
    """`z_sj + z_s'j <= 1` is per (pair, slot).  A 3-state path of 1.0 each with
    dist_max = 1.5 admits three singleton slots, cover 3.0: no slot holds both state 0 and
    state 2.  A row block that summed z over all slots would forbid states 0 and 2 from
    being contacted anywhere and cap the cover at 2.0."""
    edges3 = [(0, 1), (1, 2)]
    M = np.array([[1.0], [1.0], [1.0]])
    xy = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    p = level0.build_level0(cells(M, ("c0",)), {"A": ("c0",)}, edges=edges3, L=0.8, U=1.2,
                            eta=0.05, dist_max=1.5, state_xy=xy)
    out = level0.solve_passes(p, [level0.cover_pass(p, ["A"])])
    v = out["passes"][0]["value"]
    check("dist_max forbids one slot holding two far states, not the whole map",
          abs(v - 3.0) < 1e-6,
          f"cover {v:.6f} with K={p.k} slots; z per slot {out['z'].sum(axis=0).tolist()}")

    # the same cap written one row per (far pair, slot), appended with `append_row` (which
    # does not share the block builder under test): the cover comes back to 3.0, which is
    # what the fix `rows = np.arange(P * K)` instead of `np.repeat(np.arange(P), K)` gives.
    fixed = level0.build_level0(cells(M, ("c0",)), {"A": ("c0",)}, edges=edges3, L=0.8,
                                U=1.2, eta=0.05)
    Kf = fixed.k
    a, b = np.nonzero(np.triu(np.abs(xy[:, None, 0] - xy[None, :, 0]) > 1.5, k=1))
    for i in range(len(a)):
        for j in range(Kf):
            fixed = level0.append_row(
                fixed, f"cap_dist_{i}_{j}",
                [fixed.off_z + int(a[i]) * Kf + j, fixed.off_z + int(b[i]) * Kf + j],
                [1.0, 1.0], -np.inf, 1.0)
    of = level0.solve_passes(fixed, [level0.cover_pass(fixed, ["A"])])
    check("the per (pair, slot) cap covers 3.0 and still keeps far states out of one slot",
          abs(of["passes"][0]["value"] - 3.0) < 1e-6
          and not any(of["z"][0, j] and of["z"][2, j] for j in range(Kf)),
          f"cover {of['passes'][0]['value']:.6f}")

    # n_max, the same shape of check: at n_max = 2 three slots of two states still cover 3.0
    q = level0.build_level0(cells(np.full((6, 1), 0.5), ("c0",)), {"A": ("c0",)},
                            edges=EDGES6, L=0.8, U=1.2, eta=0.05, n_max=2)
    o2 = level0.solve_passes(q, [level0.cover_pass(q, ["A"])])
    check("n_max = 2 leaves three two-state slots feasible, cover 3.0",
          abs(o2["passes"][0]["value"] - 3.0) < 1e-6,
          f"cover {o2['passes'][0]['value']:.6f}")


# ------------------------------------------------------------------- 7. solve_passes
def passes_pin_and_certify() -> None:
    contig = [0.5, 0.1, 0.5, 0.1, 0.5, 0.1]
    scale = 8000.0
    M = (np.array(contig) * scale).reshape(6, 1)
    p = level0.build_level0(cells(M, ("c0",)), {"A": ("c0",)}, edges=EDGES6,
                            L=0.8 * scale, U=1.2 * scale, eta=0.05)
    out = level0.solve_passes(p, [level0.cover_pass(p, ["A"]), level0.contacts_pass(p)])
    cov, con = out["passes"]
    check("max pass then min pass at cover mass 14400: both certified",
          cov["certified"] and con["certified"] and abs(cov["value"] - 1.8 * scale) < 1e-3
          and con["value"] == 7,
          f"cover {cov['value']:.3f}, contacts {con['value']}")
    # the pin row itself, read back: on the minimised objective, ub = v + |v| 1e-9 + 1e-12
    pinned = out["problem"]
    lo, hi = pinned.rows["pin_cover_A"]
    v_min = -1.8 * scale
    check("the cover pin is a <= row on the minimised objective at v + |v|1e-9 + 1e-12",
          pinned.lb[lo] == -np.inf
          and abs(pinned.ub[lo] - (v_min + abs(v_min) * 1e-9 + 1e-12)) < 1e-3,
          f"ub {pinned.ub[lo]:.6f} against {v_min + abs(v_min) * 1e-9 + 1e-12:.6f}")
    # and it is a relaxation of the true optimum, never tighter
    check("the pin never cuts off the pass's own optimum",
          pinned.ub[lo] >= v_min - 1e-9)

    # the min-sense pin (v = 7 contacts) must not cut the cover optimum out either: a third
    # pass, maximising cover again, must recover 1.8 * scale under both pins
    p2 = level0.build_level0(cells(M, ("c0",)), {"A": ("c0",)}, edges=EDGES6,
                             L=0.8 * scale, U=1.2 * scale, eta=0.05)
    o2 = level0.solve_passes(p2, [level0.cover_pass(p2, ["A"]), level0.contacts_pass(p2),
                                  level0.cover_pass(p2, ["A"], name="cover_again")])
    check("a min-sense pin at v = 7 leaves the pinned cover optimum reachable",
          all(q["certified"] for q in o2["passes"])
          and abs(o2["passes"][2]["value"] - 1.8 * scale) < 1e-3,
          f"{[(q['name'], round(q['value'], 3)) for q in o2['passes']]}")

    # a zero objective is recorded, not solved, and adds no pin
    p3 = level0.build_level0(cells(np.full((6, 2), 0.5), ("c0", "c1")),
                             {"A": ("c0",), "B": ("c1",)}, edges=EDGES6, L=0.8, U=1.2,
                             eta=0.05)
    forb = p3
    empty = level0.build_level0(cells(np.hstack([np.full((6, 1), 0.5), np.zeros((6, 1))]),
                                      ("c0", "c1")), {"A": ("c0",), "B": ("c1",)},
                                edges=EDGES6, L=0.8, U=1.2, eta=0.05)
    o3 = level0.solve_passes(empty, [level0.cover_pass(empty, ["B"]),
                                     level0.cover_pass(empty, ["A"])])
    check("a zero-objective pass is recorded at 0 and never solved, and pins nothing",
          o3["passes"][0] == dict(name="cover_B", value=0.0, certified=True, status=0,
                                  seconds=0.0)
          and "pin_cover_B" not in o3["problem"].rows
          and abs(o3["passes"][1]["value"] - 3.0) < 1e-6)
    del forb

    # the lexicographic guarantee: eps * (W D y) is worth under half a contact at level 0,
    # even though a state's sum_j y_sj can exceed 1 there (it cannot at level 1).
    rng = np.random.default_rng(5)
    Mx = rng.random((6, 3)) * 0.3
    bundles = {"A": ("c0",), "AB": ("c0", "c1"), "C": ("c2",)}
    K = sum(level0.slot_counts(cells(Mx, ("c0", "c1", "c2")), bundles, L=0.8).values())
    D = rng.random((6, K)) * 10
    px = level0.build_level0(cells(Mx, ("c0", "c1", "c2")), bundles, edges=EDGES6, L=0.8,
                             U=1.2, eta=0.05, D=D)
    worst = _max_tiebreak_term(px)
    check("the eps tie-break is worth under half a contact over the whole polytope",
          worst < 0.5 - 1e-9, f"max eps*W*D*y over the LP relaxation = {worst:.6f}")


def _max_tiebreak_term(p) -> float:
    """Maximise `eps * sum_sj W_sj D_sj y_sj` over the LP relaxation of `p` (an oracle for
    `eps_lexicographic`'s claim, independent of the formula)."""
    from scipy.optimize import linprog
    c = np.zeros(p.n_var)
    S, K = p.n_state, p.k
    c[p.off_y:p.off_y + S * K] = -p.eps * (p.W * p.D).ravel()
    A_ub, b_ub = me._to_ineq(p)
    res = linprog(c, A_ub=A_ub, b_ub=b_ub,
                  bounds=list(zip(p.var_lb.tolist(), p.var_ub.tolist())),
                  method="highs-ds")
    return -float(res.fun)


def timed_out_pass_pins_its_incumbent() -> None:
    """A pass stopped by the clock records certified = False and still pins its incumbent."""
    rng = np.random.default_rng(19)
    S = 12
    M = rng.random((S, 2)) * 0.4 + 0.05
    edges = [(i, i + 1) for i in range(S - 1)] + [(0, 5), (2, 9), (4, 11)]
    b = {"A": ("c0",), "AB": ("c0", "c1"), "B": ("c1",)}
    p = level0.build_level0(cells(M, ("c0", "c1")), b, edges=edges, L=0.8, U=1.2, eta=0.05)
    try:
        out = level0.solve_passes(p, [level0.cover_pass(p, ["A", "AB", "B"]),
                                      level0.contacts_pass(p)],
                                  engine="highs", threads=2, time_limit=0.35)
    except ss.SolveFailure as exc:
        check("a timed-out pass pins its incumbent", False,
              f"INCONCLUSIVE: no incumbent inside the limit ({exc.reason}); "
              "solve_passes propagates SolveFailure rather than recording it")
        return
    first = out["passes"][0]
    pinned = "pin_" + first["name"] in out["problem"].rows
    check("a timed-out pass records certified = False and still pins its incumbent",
          (first["certified"] is False and first["status"] == "time_limit" and pinned)
          or (first["certified"] is True and first["status"] == 0),
          f"status {first['status']}, certified {first['certified']}, pinned {pinned}")


def portfolio_dispatch() -> None:
    """`strategy='portfolio'` on the contacts pass: `certified` reads `certified_splits`, and
    `threads` other than 2 is refused (trap 18)."""
    contig = [0.5, 0.1, 0.5, 0.1, 0.5, 0.1]
    M = np.array(contig).reshape(6, 1)
    p = level0.build_level0(cells(M, ("c0",)), {"A": ("c0",)}, edges=EDGES6, L=0.8, U=1.2,
                            eta=0.05)
    bad = False
    try:
        level0.solve_passes(p, [level0.contacts_pass(p)], strategy="portfolio", threads=4)
    except ValueError:
        bad = True
    check("the portfolio refuses a thread count other than 2", bad)
    refused = False
    try:
        level0.solve_passes(p, [level0.contacts_pass(p)], engine="cpsat")
    except ValueError:
        refused = True
    check("solve_passes refuses the cpsat engine", refused)
    t0 = time.time()
    out = level0.solve_passes(p, [level0.cover_pass(p, ["A"]), level0.contacts_pass(p)],
                              engine="highs", strategy="portfolio", time_limit=60.0)
    con = out["passes"][1]
    check("the portfolio contacts pass returns the certified minimum contact count",
          con["value"] == 7 and con["certified"] and out["contacts"] == 7,
          f"{con} in {time.time() - t0:.1f}s")


# ----------------------------------------------------- 8. the optimum against a brute force
def cover_and_contacts_against_enumeration() -> None:
    """On the six-state path with whole-state shares, enumerate every assignment of states to
    at most K slots and compare the best cover and the minimum contact count at full cover."""
    contig = np.array([0.5, 0.1, 0.5, 0.1, 0.5, 0.1])
    p = level0.build_level0(cells(contig.reshape(6, 1), ("c0",)), {"A": ("c0",)},
                            edges=EDGES6, L=0.8, U=1.2, eta=0.05)
    best_cover = 0.0
    for labels in itertools.product(range(-1, p.k), repeat=6):
        cols = [np.array([lab == j for lab in labels]) for j in range(p.k)]
        masses = [contig[c].sum() for c in cols]
        if any(0 < m < 0.8 - 1e-9 or m > 1.2 + 1e-9 for m in masses):
            continue
        if any(m > 0 and not ss.connected(c, EDGES6) for m, c in zip(masses, cols)):
            continue
        best_cover = max(best_cover, sum(masses))
    out = level0.solve_passes(p, [level0.cover_pass(p, ["A"]), level0.contacts_pass(p)])
    check("whole-state enumeration bounds the fractional cover from below",
          out["passes"][0]["value"] >= best_cover - 1e-9,
          f"MILP {out['passes'][0]['value']:.4f} against the best whole-state plan "
          f"{best_cover:.4f}")
    # at full cover (1.8) the contact count is 7: six states plus one split, and no
    # whole-state plan reaches 1.8 at all (the enumeration above tops out below it)
    check("full cover needs one split, which whole states cannot give",
          abs(out["passes"][0]["value"] - 1.8) < 1e-6 and out["contacts"] == 7
          and best_cover < 1.8 - 1e-9,
          f"best whole-state cover {best_cover:.4f}")
    for j in range(p.k):
        if out["u"][j]:
            assert ss.connected(out["z"][:, j], EDGES6)


def main() -> int:
    rows_against_spec()
    flow_block_identical_to_level1()
    engine_seam_on_the_subclass()
    parent_decode_regression()
    k_b_is_enough()
    contiguity_through_a_committed_state()
    dist_max_row_semantics()
    cover_and_contacts_against_enumeration()
    passes_pin_and_certify()
    timed_out_pass_pins_its_incumbent()
    portfolio_dispatch()
    print(f"\n{len(PASS)} checks passed, {len(FAIL)} failed")
    for name in FAIL:
        print(f"  FAILED: {name}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
