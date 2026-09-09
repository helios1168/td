"""check_root_fix.py -- does `milp_engines.fix_roots` lose an optimum?

Claim under test (docstring of `td/solvers/milp_engines.py fix_roots`, lines 132-138): for an
instance built by `state_splits.build_milp(anchors=[(home(j), j) for every j])`, fixing
`r[home(j), j] = 1` and `r[s, j] = 0` elsewhere leaves the optimal objective unchanged and the
set of optimal `(z, y)` unchanged.

Six legs, run in order:

  A structure   the `r` and `f` columns carry zero objective and appear only in the `root`,
                `rz`, `flow_tail`, `flow_head` and `net` row blocks, so nothing outside the
                flow block can see a root.  Also: every flow row touches exactly one district,
                so the flow block separates over `j`.
  B exhaustive  for every subset Z of the states and every root choice, district j's flow rows
                (taken from the assembled matrix, not re-derived) are feasible exactly when Z
                is connected, nonempty and contains the root.  Oracle: BFS
                (`state_splits.connected`).
  C random      220 anchored instances solved twice, plain and root-fixed, with the `scipy`
                engine at `mip_rel_gap = 0`; objectives compared at 1e-9, `z` exactly, `y` at
                1e-9.  A quarter of the instances also carry a `cap` on an anchored home state.
  D bound gap   the anchor-contradicting bound: `bounds=[(home(0), 0, 0.0, 0.0)]` releases the
                anchor inside `build_milp`, but `fix_roots` still given that anchor forces
                `r[home(0), 0] = 1 <= z[home(0), 0] = 0`.
  E shared home two districts anchored to the same state (which `tools/state_splits.py` line
                516 permits: nothing makes `ctx.home` injective), plus a cap on that state.
  F released    the `--unanchor` shape: `build_milp` without the anchor, `fix_roots` with it.

Run: /Users/ntlee/projects/td/.venv/bin/python3 tools/verify/milp_root_fix/check_root_fix.py
"""
from __future__ import annotations

import sys
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from scipy.spatial import Delaunay

sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/app2")

from td.solvers import state_splits as ss          # noqa: E402
from td.solvers import milp_engines as me          # noqa: E402

SEED = 20260908
TOL = 1e-9
FLOW_BLOCKS = ("root", "rz", "flow_tail", "flow_head", "net")


# --------------------------------------------------------------------------- instance factory
def random_graph(rng, S):
    """A connected planar graph on S nodes: the Delaunay triangulation of S random points."""
    while True:
        P = rng.random((S, 2))
        try:
            tri = Delaunay(P)
        except Exception:
            continue
        E = set()
        for simplex in tri.simplices:
            for a in range(3):
                for b in range(a + 1, 3):
                    u, v = int(simplex[a]), int(simplex[b])
                    E.add((min(u, v), max(u, v)))
        E = sorted(E)
        if ss.connected(np.ones(S, bool), E):
            return P, E


def random_instance(rng, S, k, delta=0.1, eta=0.01, homes=None):
    P, E = random_graph(rng, S)
    M_s = rng.uniform(0.2, 3.0, S)
    C = rng.random((k, 2))
    D = ((P[:, None, :] - C[None, :, :]) ** 2).sum(axis=2) + rng.uniform(0.01, 0.2, (S, k))
    tau = M_s.sum() / k
    eps = ss.eps_lexicographic(M_s, D)
    if homes is None:
        homes = list(rng.permutation(S)[:k])
    anchors = [(int(homes[j]), j) for j in range(k)]
    return dict(M_s=M_s, D=D, edges=E, tau=tau, delta=delta, eps=eps, eta=eta,
                anchors=anchors)


def build(inst, anchors=None, **kw):
    return ss.build_milp(inst["M_s"], inst["D"], inst["edges"], inst["tau"], inst["delta"],
                         inst["eps"], eta=inst["eta"],
                         anchors=inst["anchors"] if anchors is None else anchors, **kw)


def district_cols(p, j):
    """The `z`, `r`, `f` column indices belonging to district `j`."""
    S, k = p.n_state, p.k
    n_arc = 2 * len(p.edges)
    zc = np.array([p.off_z + s * k + j for s in range(S)])
    rc = np.array([p.off_r + s * k + j for s in range(S)])
    fc = np.array([p.off_f + a * k + j for a in range(n_arc)], dtype=int)
    return zc, rc, fc


# --------------------------------------------------------------------------- leg A: structure
def leg_structure():
    rng = np.random.default_rng(SEED)
    bad = []
    for _ in range(20):
        S, k = int(rng.integers(4, 10)), int(rng.integers(2, 4))
        p = build(random_instance(rng, S, k))
        A = p.A.tocsr()
        r_cols = set(range(p.off_r, p.off_r + p.n_state * p.k))
        f_cols = set(range(p.off_f, p.n_var))
        rf = r_cols | f_cols
        if np.abs(p.c[p.off_r:]).max(initial=0.0) != 0.0:
            bad.append("objective touches r or f")
        for name, (lo, hi) in p.rows.items():
            cols = set(A[lo:hi].indices.tolist())
            if name not in FLOW_BLOCKS and cols & rf:
                bad.append(f"row block {name} touches r/f")
        used = set()
        for name in FLOW_BLOCKS:
            lo, hi = p.rows[name]
            used |= set(A[lo:hi].indices.tolist())
        if not rf <= used:
            bad.append("some r/f column appears in no flow row")
        # separability: every flow row's support lies inside a single district's columns
        own = [set(np.concatenate(district_cols(p, j)).tolist()) for j in range(k)]
        for name in FLOW_BLOCKS:
            lo, hi = p.rows[name]
            for r in range(lo, hi):
                sup = set(A[r].indices.tolist())
                if not sup:
                    continue
                if not any(sup <= own[j] for j in range(k)):
                    bad.append(f"flow row {r} in block {name} spans two districts")
    return bad


# --------------------------------------------------------------------------- leg B: exhaustive
def flow_rows_of(p, j):
    """Row indices of the flow blocks whose support lies in district `j`'s columns."""
    A = p.A.tocsr()
    own = set(np.concatenate(district_cols(p, j)).tolist())
    keep = []
    for name in FLOW_BLOCKS:
        lo, hi = p.rows[name]
        for r in range(lo, hi):
            sup = set(A[r].indices.tolist())
            if sup and sup <= own:
                keep.append(r)
    return np.array(keep, dtype=int)


def flow_feasible(p, j, z_col, r_col, keep, A):
    """Is district `j`'s flow block feasible at this `z` column and this fixed root?

    Rows and coefficients come straight out of the assembled `p.A`; only the `f` variables of
    district `j` are free.  `z` and `r` enter as constants moved to the right-hand side.
    """
    N = p.n_state
    zc, rc, fc = district_cols(p, j)
    Ak = A[keep]
    const = np.asarray(Ak[:, zc] @ z_col + Ak[:, rc] @ r_col).ravel()
    Af = Ak[:, fc]
    lo, hi = p.lb[keep] - const, p.ub[keep] - const
    parts_A, parts_b = [], []
    up = np.isfinite(hi)
    if up.any():
        parts_A.append(Af[up]); parts_b.append(hi[up])
    dn = np.isfinite(lo)
    if dn.any():
        parts_A.append(-Af[dn]); parts_b.append(-lo[dn])
    A_ub = sparse.vstack(parts_A).tocsc()
    b_ub = np.concatenate(parts_b)
    n_f = len(fc)
    res = linprog(np.zeros(n_f), A_ub=A_ub, b_ub=b_ub,
                  bounds=[(0.0, max(N - 1.0, 0.0))] * n_f, method="highs-ds")
    return bool(res.success)


def leg_exhaustive():
    rng = np.random.default_rng(SEED + 1)
    bad, n_case = [], 0
    for S in (4, 5, 6):
        for _ in range(3):
            inst = random_instance(rng, S, 2)
            p = build(inst)
            A = p.A.tocsr()
            keep = flow_rows_of(p, 0)
            for mask in range(1 << S):
                z_col = np.array([(mask >> s) & 1 for s in range(S)], float)
                conn = bool(z_col.any()) and ss.connected(z_col.astype(bool), p.edges)
                for root in range(S):
                    r_col = np.zeros(S)
                    r_col[root] = 1.0
                    want = bool(conn and z_col[root] > 0.5)
                    got = flow_feasible(p, 0, z_col, r_col, keep, A)
                    n_case += 1
                    if got != want:
                        bad.append((S, mask, root, want, got))
    return bad, n_case


# --------------------------------------------------------------------------- the paired solve
def new_stats():
    return dict(solved=0, infeasible=0, with_splits=0, capped=0, home_leaf=0, home_alone=0,
                shared_home=0, obj_max=0.0, y_max=0.0, z_mismatch=0, y_tie=0)


def compare(inst, anchors_build, anchors_fix, stats, bad, **kw):
    """Solve plain and root-fixed and score the pair.  Returns the plain result or None."""
    p_plain = build(inst, anchors=anchors_build, **kw)
    p_fixed = me.fix_roots(build(inst, anchors=anchors_build, **kw), anchors_fix)
    try:
        a = me.solve_problem(p_plain, "scipy", time_limit=60.0)
    except ss.SolveFailure:
        try:
            me.solve_problem(p_fixed, "scipy", time_limit=60.0)
        except ss.SolveFailure:
            stats["infeasible"] += 1
            return None
        bad.append("plain infeasible, root-fixed feasible")
        return None
    try:
        b = me.solve_problem(p_fixed, "scipy", time_limit=60.0)
    except ss.SolveFailure as exc:
        bad.append(("fixed infeasible where plain solved", exc.reason, anchors_fix))
        return None
    if a["status"] != 0 or b["status"] != 0:
        return None
    stats["solved"] += 1
    stats["with_splits"] += int(a["splits"] > 0)
    d_obj = abs(a["objective"] - b["objective"])
    stats["obj_max"] = max(stats["obj_max"], d_obj)
    if d_obj > TOL:
        bad.append(("objective differs", d_obj))
    if not np.array_equal(a["z"], b["z"]):
        stats["z_mismatch"] += 1
        if a["splits"] != b["splits"]:
            bad.append(("split count differs", a["splits"], b["splits"]))
    d_y = float(np.abs(a["y"] - b["y"]).max())
    stats["y_max"] = max(stats["y_max"], d_y)
    if d_y > TOL:
        stats["y_tie"] += 1                       # equal objective, different LP vertex
    return a


# --------------------------------------------------------------------------- leg C: random solves
def leg_random(n_target=220):
    rng = np.random.default_rng(SEED + 2)
    stats, bad, tries = new_stats(), [], 0
    while stats["solved"] < n_target and tries < 8 * n_target:
        tries += 1
        S = int(rng.integers(4, 10))
        k = int(rng.integers(2, 4))
        if k >= S:
            continue
        inst = random_instance(rng, S, k)
        caps = None
        if rng.random() < 0.25:                      # attack: a cap on an anchored home state
            s0 = inst["anchors"][0][0]
            need = sum(1 for s, _ in inst["anchors"] if s == s0)
            caps = {s0: int(rng.integers(need, k + 1))}
        a = compare(inst, inst["anchors"], inst["anchors"], stats, bad, caps=caps)
        if a is None:
            continue
        stats["capped"] += int(caps is not None)
        for s, j in inst["anchors"]:
            Zj = set(int(t) for t in np.flatnonzero(a["z"][:, j]))
            if s not in Zj:
                bad.append(("anchor not held", s, j))
            deg = sum(1 for u, v in inst["edges"]
                      if (u == s and v in Zj) or (v == s and u in Zj))
            if len(Zj) == 1:
                stats["home_alone"] += 1
            elif deg == 1:
                stats["home_leaf"] += 1
        homes = [s for s, _ in inst["anchors"]]
        if len(set(homes)) < len(homes):
            stats["shared_home"] += 1
    return stats, bad


# --------------------------------------------------------------------------- leg D: the gap
def leg_bound_gap():
    """A `bounds` entry that contradicts an anchor: `bound_z` releases it (lb and ub both 0),
    so the plain model can still be feasible while `fix_roots` on the *unreleased* anchor list
    forces `r = 1 <= z = 0` and is infeasible."""
    rng = np.random.default_rng(SEED + 3)
    for _ in range(60):
        inst = random_instance(rng, int(rng.integers(5, 9)), 3)
        s0, j0 = inst["anchors"][0]
        p_plain = build(inst, bounds=[(s0, j0, 0.0, 0.0)])
        p_fixed = me.fix_roots(build(inst, bounds=[(s0, j0, 0.0, 0.0)]), inst["anchors"])
        try:
            a = me.solve_problem(p_plain, "scipy", time_limit=60.0)
        except ss.SolveFailure:
            continue
        if a["status"] != 0:
            continue
        try:
            me.solve_problem(p_fixed, "scipy", time_limit=60.0)
        except ss.SolveFailure as exc:
            return dict(found=True, reason=exc.reason, S=int(inst["M_s"].shape[0]),
                        anchor=(int(s0), int(j0)), plain_objective=a["objective"])
        return dict(found=False, note="both solved; the released anchor was re-imposed")
    return dict(found=False, note="no feasible plain instance in 60 draws")


# --------------------------------------------------------------------------- leg E: shared home
def leg_shared_home(n_target=40):
    """Districts 0 and 1 anchored to the same state, with a cap on it.  `r` is per `(s, j)`, so
    both roots can sit on the same state."""
    rng = np.random.default_rng(SEED + 4)
    stats, bad, tries = new_stats(), [], 0
    while stats["solved"] < n_target and tries < 8 * n_target:
        tries += 1
        S, k = int(rng.integers(5, 10)), 3
        perm = list(rng.permutation(S))
        homes = [int(perm[0]), int(perm[0]), int(perm[1])]     # two districts share a home
        inst = random_instance(rng, S, k, homes=homes)
        caps = {homes[0]: int(rng.integers(2, k + 1))}
        compare(inst, inst["anchors"], inst["anchors"], stats, bad, caps=caps)
    return stats, bad


# --------------------------------------------------------------------------- leg F: released anchor
def leg_released_anchor():
    """The `--unanchor` shape: `build_milp` gets the reduced anchor list, `fix_roots` the full
    one.  `r[s, j] = 1` and the `rz` row `r <= z` then re-impose the released anchor."""
    rng = np.random.default_rng(SEED + 5)
    worse, checked = 0, 0
    for _ in range(60):
        S, k = int(rng.integers(5, 10)), 3
        inst = random_instance(rng, S, k)
        reduced = inst["anchors"][1:]                 # district 0 unanchored
        p_plain = build(inst, anchors=reduced)
        p_fixed = me.fix_roots(build(inst, anchors=reduced), inst["anchors"])
        try:
            a = me.solve_problem(p_plain, "scipy", time_limit=60.0)
            b = me.solve_problem(p_fixed, "scipy", time_limit=60.0)
        except ss.SolveFailure:
            continue
        if a["status"] != 0 or b["status"] != 0:
            continue
        checked += 1
        if b["objective"] > a["objective"] + TOL:
            worse += 1
    return dict(checked=checked, strictly_worse=worse)


# --------------------------------------------------------------------------- main
if __name__ == "__main__":
    import scipy
    print(f"numpy {np.__version__}  scipy {scipy.__version__}  seed {SEED}")

    bad = leg_structure()
    print(f"\nA structure  : {'OK' if not bad else bad[:5]} "
          f"(20 problems; zero cost on r/f, flow rows only, one district per flow row)")

    bad_b, n_case = leg_exhaustive()
    print(f"B exhaustive : {'OK' if not bad_b else bad_b[:5]} "
          f"({n_case} (subset, root) pairs vs the BFS oracle)")

    stats, bad_c = leg_random()
    print(f"C random     : {stats}")
    print(f"               failures: {bad_c[:5] if bad_c else 'none'}")

    gap = leg_bound_gap()
    print(f"D bound gap  : {gap}")

    stats_e, bad_e = leg_shared_home()
    print(f"E shared home: {stats_e}")
    print(f"               failures: {bad_e[:5] if bad_e else 'none'}")

    print(f"F released   : {leg_released_anchor()}")

    ok = not bad and not bad_b and not bad_c and not bad_e
    print(f"\nVERDICT: {'claim holds on every anchored check' if ok else 'BROKEN'}; "
          f"bound gap reproduced: {gap.get('found')}")
