"""Independent oracles for td/solvers/state_splits.py (docs/CODEVERIFY_state_splits.md).

Every oracle here is written against the *formulation in the plan*, not against the module:
brute-force enumeration of z-patterns with a hand-built dense LP for the shares, a hand-written
BFS, and a hand-built pair of dense LPs for the balance pass.  Deterministic (seeds pinned).

    /Users/ntlee/projects/td/.venv/bin/python3 docs/verify/codeverify_state_splits.py
"""
from __future__ import annotations

import itertools
import sys

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/vbl")
from td.solvers import state_splits as ss   # noqa: E402

FAIL: list[str] = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'} {name} {detail}")
    if not ok:
        FAIL.append(f"{name} {detail}")


# --------------------------------------------------------------- oracle helpers
def bfs_connected(sel, edges, n):
    """Hand-written BFS.  Empty set counts as connected (matches the module's convention)."""
    nodes = [s for s in range(n) if sel[s]]
    if not nodes:
        return True
    adj = {s: set() for s in nodes}
    for u, v in edges:
        if sel[u] and sel[v]:
            adj[u].add(v)
            adj[v].add(u)
    seen, queue = {nodes[0]}, [nodes[0]]
    while queue:
        s = queue.pop(0)
        for t in adj[s]:
            if t not in seen:
                seen.add(t)
                queue.append(t)
    return len(seen) == len(nodes)


def share_lp(z, M_s, D, tau, delta, eps, eta):
    """min eps * sum M_s D_sj y_sj over {sum_j y=1, eta z <= y <= z, band}.  Dense, hand-built.
    Returns None if infeasible."""
    S, k = z.shape
    n = S * k
    c = eps * (M_s[:, None] * D).ravel()
    A_eq = np.zeros((S, n))
    for s in range(S):
        A_eq[s, s * k:(s + 1) * k] = 1.0
    A_ub, b_ub = [], []
    for j in range(k):
        row = np.zeros(n)
        for s in range(S):
            row[s * k + j] = M_s[s]
        A_ub.append(row)
        b_ub.append(tau * (1 + delta))
        A_ub.append(-row)
        b_ub.append(-tau * (1 - delta))
    lo = (eta * z).ravel().astype(float)
    hi = z.ravel().astype(float)
    res = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub), A_eq=A_eq, b_eq=np.ones(S),
                  bounds=np.stack([lo, hi], axis=1), method="highs")
    if not res.success:
        return None
    return float(res.fun), res.x.reshape(S, k)


def brute_force(M_s, D, edges, tau, delta, eps, eta=0.01):
    """Enumerate every z in {0,1}^(S x k); objective = split count + share LP value."""
    S, k = D.shape
    best = None
    for bits in itertools.product([0, 1], repeat=S * k):
        z = np.array(bits, bool).reshape(S, k)
        if (z.sum(axis=1) == 0).any():
            continue
        ok = True
        for j in range(k):
            if z[:, j].sum() == 0 or not bfs_connected(z[:, j], edges, S):
                ok = False
                break
        if not ok:
            continue
        out = share_lp(z, M_s, D, tau, delta, eps, eta)
        if out is None:
            continue
        val = int(z.sum() - S) + out[0]
        if best is None or val < best[0] - 1e-12:
            best = (val, int(z.sum() - S), z, out[1])
    return best


# --------------------------------------------------------------- 1. build_milp vs brute force
def m1():
    print("\n== 1  build_milp / solve vs brute-force enumeration ==")
    cases = []
    # (a) 6-state path, equal masses, k=2, tight band -> 0 splits
    edges6 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    xy = np.arange(6, dtype=float)
    C = np.array([1.0, 4.0])
    D6 = (xy[:, None] - C[None, :]) ** 2
    cases.append(("6-path EVEN d=0.001", np.full(6, 10.0), D6, edges6, 0.001))
    cases.append(("6-path ODD   d=0.005",
                  np.array([10., 10., 10., 10., 10., 11.]), D6, edges6, 0.005))
    cases.append(("6-path COMB  d=0.03",
                  np.array([10., 3., 10., 3., 10., 3.]), D6, edges6, 0.03))
    # (d) eta case: path A-B-C, masses 1,2,1, tau=2, delta=0 (VERIFY 1b)
    cases.append(("3-path bridge d=0",
                  np.array([1.0, 2.0, 1.0]),
                  np.array([[1.0, 4.0], [2.0, 2.0], [4.0, 1.0]]), [(0, 1), (1, 2)], 0.0))
    # (e) 6-state cycle, random masses
    rng = np.random.default_rng(20260906)
    edgesC = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]
    cases.append(("6-cycle random d=0.05", rng.uniform(1, 5, 6), rng.uniform(0.5, 8, (6, 2)),
                  edgesC, 0.05))

    for name, M_s, D, edges, delta in cases:
        tau = float(M_s.sum()) / D.shape[1]
        eps = ss.eps_lexicographic(M_s, D)
        prob = ss.build_milp(M_s, D, edges, tau, delta, eps)
        res = ss.solve(prob)
        bf = brute_force(M_s, D, edges, tau, delta, eps)
        # the module's res.fun carries + S (c[z] = 1 with no -1 offset)
        obj_code = res["objective"] - D.shape[0]
        check(f"1 {name}: split count", res["splits"] == bf[1],
              f"code {res['splits']} brute {bf[1]}")
        check(f"1 {name}: objective", abs(obj_code - bf[0]) < 1e-7,
              f"code {obj_code:.9f} brute {bf[0]:.9f}")
        for j in range(prob.k):
            check(f"1 {name}: z col {j} connected",
                  bfs_connected(res["z"][:, j], edges, D.shape[0]) and res["z"][:, j].any())
            check(f"1 {name}: realised col {j} connected",
                  bfs_connected(res["y"][:, j] > 1e-9, edges, D.shape[0]))
        m = res["masses"]
        check(f"1 {name}: band", (m >= tau * (1 - delta) - 1e-7).all()
              and (m <= tau * (1 + delta) + 1e-7).all(), f"{m}")
        check(f"1 {name}: eta", (res["y"][res["z"]] >= prob.eta - 1e-7).all())
        check(f"1 {name}: sum_j y = 1", np.allclose(res["y"].sum(axis=1), 1.0))


# --------------------------------------------------------------- 1'. row-by-row structure
def m1_rows():
    print("\n== 1' build_milp rows read back symbolically ==")
    rng = np.random.default_rng(7)
    S, k = 5, 3
    M_s = rng.uniform(1, 4, S)
    D = rng.uniform(0.5, 6, (S, k))
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
    tau, delta, eps, eta = float(M_s.sum()) / k, 0.07, 0.001, 0.02
    p = ss.build_milp(M_s, D, edges, tau, delta, eps, eta=eta)
    A = p.A.toarray()
    N = S
    ok = True
    msgs = []

    def rowset(name):
        a, b = p.rows[name]
        return A[a:b], p.lb[a:b], p.ub[a:b]

    # objective
    cz = p.c[p.off_z:p.off_z + S * k]
    cy = p.c[p.off_y:p.off_y + S * k]
    ok &= np.allclose(cz, 1.0) and np.allclose(cy, eps * (M_s[:, None] * D).ravel())
    ok &= np.allclose(p.c[p.off_r:], 0.0)
    msgs.append(f"objective {'ok' if ok else 'BAD'}")
    # place
    Ap, lo, hi = rowset("place")
    E = np.zeros((S, p.n_var))
    for s in range(S):
        E[s, p.off_y + s * k:p.off_y + (s + 1) * k] = 1.0
    ok2 = np.allclose(Ap, E) and np.allclose(lo, 1) and np.allclose(hi, 1)
    msgs.append(f"place {'ok' if ok2 else 'BAD'}")
    ok &= ok2
    # yz and yz_lo
    Ay, _, hy = rowset("yz")
    Al, _, hl = rowset("yz_lo")
    Ey = np.zeros((S * k, p.n_var))
    El = np.zeros((S * k, p.n_var))
    for i in range(S * k):
        Ey[i, p.off_y + i], Ey[i, p.off_z + i] = 1.0, -1.0
        El[i, p.off_z + i], El[i, p.off_y + i] = eta, -1.0
    ok3 = np.allclose(Ay, Ey) and np.allclose(hy, 0) and np.allclose(Al, El) and np.allclose(hl, 0)
    msgs.append(f"y<=z, eta z<=y {'ok' if ok3 else 'BAD'}")
    ok &= ok3
    # band
    Ab, lob, hib = rowset("band")
    Eb = np.zeros((k, p.n_var))
    for j in range(k):
        for s in range(S):
            Eb[j, p.off_y + s * k + j] = M_s[s] / tau
    ok4 = (np.allclose(Ab, Eb) and np.allclose(lob, 1 - delta) and np.allclose(hib, 1 + delta))
    msgs.append(f"band {'ok' if ok4 else 'BAD'}")
    ok &= ok4
    # root / rz
    Ar, lor, hir = rowset("root")
    Er = np.zeros((k, p.n_var))
    for j in range(k):
        for s in range(S):
            Er[j, p.off_r + s * k + j] = 1.0
    ok5 = np.allclose(Ar, Er) and np.allclose(lor, 1) and np.allclose(hir, 1)
    Arz, _, hrz = rowset("rz")
    Erz = np.zeros((S * k, p.n_var))
    for i in range(S * k):
        Erz[i, p.off_r + i], Erz[i, p.off_z + i] = 1.0, -1.0
    ok5 &= np.allclose(Arz, Erz) and np.allclose(hrz, 0)
    msgs.append(f"root, r<=z {'ok' if ok5 else 'BAD'}")
    ok &= ok5
    # flow capacity: arc 2e is u->v, arc 2e+1 is v->u; both bounded by (N-1) z at each end
    n_arc = 2 * len(edges)
    Et = np.zeros((n_arc * k, p.n_var))
    Eh = np.zeros((n_arc * k, p.n_var))
    for e, (u, v) in enumerate(edges):
        for d, (tl, hd) in enumerate([(u, v), (v, u)]):
            a = 2 * e + d
            for j in range(k):
                i = a * k + j
                Et[i, p.off_f + i], Et[i, p.off_z + tl * k + j] = 1.0, -(N - 1.0)
                Eh[i, p.off_f + i], Eh[i, p.off_z + hd * k + j] = 1.0, -(N - 1.0)
    At, _, ht = rowset("flow_tail")
    Ah, _, hh = rowset("flow_head")
    ok6 = (np.allclose(At, Et) and np.allclose(Ah, Eh)
           and np.allclose(ht, 0) and np.allclose(hh, 0))
    msgs.append(f"arc capacity {'ok' if ok6 else 'BAD'}")
    ok &= ok6
    # net inflow: z_sj - N r_sj - (in - out) <= 0
    En = np.zeros((S * k, p.n_var))
    for s in range(S):
        for j in range(k):
            i = s * k + j
            En[i, p.off_z + i], En[i, p.off_r + i] = 1.0, -float(N)
    for e, (u, v) in enumerate(edges):
        for d, (tl, hd) in enumerate([(u, v), (v, u)]):
            a = 2 * e + d
            for j in range(k):
                En[hd * k + j, p.off_f + a * k + j] -= 1.0
                En[tl * k + j, p.off_f + a * k + j] += 1.0
    An, _, hn = rowset("net")
    ok7 = np.allclose(An, En) and np.allclose(hn, 0)
    msgs.append(f"net inflow {'ok' if ok7 else 'BAD'}")
    ok &= ok7
    # variable bounds / integrality
    ok8 = (np.allclose(p.var_lb, 0)
           and np.allclose(p.var_ub[:3 * S * k], 1)
           and np.allclose(p.var_ub[p.off_f:], N - 1.0)
           and p.integrality[p.off_z:p.off_z + S * k].all()
           and p.integrality[p.off_r:p.off_r + S * k].all()
           and not p.integrality[p.off_y:p.off_y + S * k].any()
           and not p.integrality[p.off_f:].any())
    msgs.append(f"bounds/integrality {'ok' if ok8 else 'BAD'}")
    ok &= ok8
    check("1' every row block matches the formulation", bool(ok), "; ".join(msgs))
    check("1' no rows beyond the eight blocks",
          A.shape[0] == sum(b - a for a, b in p.rows.values()), f"{A.shape[0]}")


# --------------------------------------------------------------- 1''. scf block, LP feasibility
def m1_scf():
    print("\n== 1'' scf block admits exactly the connected non-empty z-sets ==")
    graphs = {
        "path6": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
        "cycle6": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)],
        "grid2x3": [(0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)],
        "twotri": [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)],
        "star": [(0, 1), (0, 2), (0, 3), (0, 4), (4, 5)],
    }
    bad = 0
    tested = 0
    for gname, edges in graphs.items():
        S = 6
        M_s = np.ones(S)
        D = np.zeros((S, 1))
        # k = 1, fix z by bounds, ask HiGHS whether the flow block is feasible
        p = ss.build_milp(M_s, D, edges, 1.0, 10.0, 0.0)   # band made vacuous by huge delta
        for bits in itertools.product([0, 1], repeat=S):
            z = np.array(bits, float)
            lb = p.var_lb.copy()
            ub = p.var_ub.copy()
            lb[p.off_z:p.off_z + S] = z
            ub[p.off_z:p.off_z + S] = z
            from scipy.optimize import Bounds, LinearConstraint, milp
            r = milp(c=np.zeros(p.n_var),
                     constraints=LinearConstraint(p.A, p.lb, p.ub),
                     integrality=p.integrality, bounds=Bounds(lb, ub),
                     options={"mip_rel_gap": 0.0})
            lp_ok = r.status == 0
            want = bool(z.sum() > 0) and bfs_connected(z.astype(bool), edges, S)
            # with k = 1 the "place" row forces sum_j y = 1, so y_s0 = 1 and z_s0 = 1 for all s;
            # only the all-ones pattern is placeable.  Restrict the comparison to that pattern's
            # flow feasibility by dropping the place/eta rows: use z-only feasibility instead.
            tested += 1
            if z.sum() == S and lp_ok != want:
                bad += 1
    check("1'' scf (k=1, all-selected) agrees with BFS", bad == 0, f"{tested} patterns, {bad} bad")

    # the real test: an scf-only LP built from the module's own row blocks
    bad = 0
    n = 0
    for gname, edges in graphs.items():
        S = 6
        p = ss.build_milp(np.ones(S), np.zeros((S, 1)), edges, 1.0, 10.0, 0.0)
        A = p.A.tocsr()
        keep = [p.rows[b] for b in ("root", "rz", "flow_tail", "flow_head", "net")]
        idx = np.concatenate([np.arange(a, b) for a, b in keep])
        from scipy.optimize import Bounds, LinearConstraint, milp
        for bits in itertools.product([0, 1], repeat=S):
            z = np.array(bits, float)
            lb, ub = p.var_lb.copy(), p.var_ub.copy()
            lb[p.off_z:p.off_z + S] = z
            ub[p.off_z:p.off_z + S] = z
            r = milp(c=np.zeros(p.n_var),
                     constraints=LinearConstraint(A[idx], p.lb[idx], p.ub[idx]),
                     integrality=p.integrality, bounds=Bounds(lb, ub),
                     options={"mip_rel_gap": 0.0})
            want = bool(z.sum() > 0) and bfs_connected(z.astype(bool), edges, S)
            n += 1
            if (r.status == 0) != want:
                bad += 1
                print("   mismatch", gname, bits, r.status, want)
    check("1'' scf block alone == BFS-connected & non-empty", bad == 0, f"{n} subsets, {bad} bad")


# --------------------------------------------------------------- 2. connected vs BFS
def m2():
    print("\n== 2  connected() vs a hand-written BFS ==")
    rng = np.random.default_rng(11)
    graphs = [
        [], [(0, 1)], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
        [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)],
        [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
        [(1, 0), (2, 1), (5, 4)],                     # reversed / partial
    ]
    bad = 0
    n = 0
    for edges in graphs:
        for S in (1, 3, 6):
            if any(u >= S or v >= S for u, v in edges):
                continue
            for bits in itertools.product([0, 1], repeat=S):
                sel = np.array(bits, bool)
                n += 1
                if ss.connected(sel, edges) != bfs_connected(sel, edges, S):
                    bad += 1
                    print("   mismatch", edges, bits)
    # random graphs
    for trial in range(200):
        S = int(rng.integers(2, 8))
        pairs = [(u, v) for u in range(S) for v in range(u + 1, S)]
        m = int(rng.integers(0, len(pairs) + 1))
        edges = [pairs[i] for i in rng.choice(len(pairs), m, replace=False)]
        for bits in itertools.product([0, 1], repeat=S):
            sel = np.array(bits, bool)
            n += 1
            if ss.connected(sel, edges) != bfs_connected(sel, edges, S):
                bad += 1
    check("2 connected() == BFS on every subset", bad == 0, f"{n} subsets, {bad} mismatches")


# --------------------------------------------------------------- 3. eps
def m3():
    print("\n== 3  eps_lexicographic ==")
    rng = np.random.default_rng(2026)
    bad_formula = 0
    for _ in range(50):
        S, k = int(rng.integers(2, 9)), int(rng.integers(2, 5))
        M_s = rng.uniform(0.1, 10, S)
        D = rng.uniform(0.01, 50, (S, k))
        want = 0.5 / float((M_s * D.max(axis=1)).sum())
        if abs(ss.eps_lexicographic(M_s, D) - want) > 1e-15 * max(1.0, want):
            bad_formula += 1
    check("3 eps == 0.5 / sum_s M_s max_j D_sj", bad_formula == 0, f"{bad_formula}/50 off")

    # never trades a split for compactness: split count at eps == split count at eps = 0
    edges6 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    edgesC = edges6 + [(5, 0)]
    bad, feas, worse = 0, 0, 0
    for t in range(60):
        edges = edges6 if t % 2 else edgesC
        M_s = rng.uniform(0.5, 6.0, 6)
        D = rng.uniform(0.01, 60.0, (6, 2))
        tau = float(M_s.sum()) / 2
        delta = float(rng.choice([0.0, 0.02, 0.05, 0.10]))
        eps = ss.eps_lexicographic(M_s, D)
        try:
            r_eps = ss.solve(ss.build_milp(M_s, D, edges, tau, delta, eps))
            r_0 = ss.solve(ss.build_milp(M_s, D, edges, tau, delta, 0.0))
        except RuntimeError:
            continue
        feas += 1
        if r_eps["splits"] != r_0["splits"]:
            bad += 1
            print("   split traded:", M_s, D, delta, r_eps["splits"], r_0["splits"])
        # and the tie-break really is a tie-break: it must not be worse in compactness
        v_eps = float((M_s[:, None] * D * r_eps["y"]).sum())
        v_0 = float((M_s[:, None] * D * r_0["y"]).sum())
        if v_eps > v_0 + 1e-6:
            worse += 1
    check("3 eps never changes the split count", bad == 0, f"{feas} feasible trials, {bad} bad")
    check("3 eps solution is at least as compact as the eps=0 one", worse == 0,
          f"{worse} worse of {feas}")

    # the VERIFY section-2 counterexample: the plan's original eps buys 2 splits, this one 0
    M_s = np.full(4, 10.0)
    D = np.array([[1.0, 100.0], [100.0, 1.0], [1.0, 100.0], [100.0, 1.0]])
    e = [(0, 1), (1, 2), (2, 3)]
    r_new = ss.solve(ss.build_milp(M_s, D, e, 20.0, 0.0, ss.eps_lexicographic(M_s, D)))
    y0 = np.array([[1., 0.], [0., 1.], [1., 0.], [0., 1.]])
    eps_plan = 0.5 / float((M_s[:, None] * D * y0).sum())
    r_old = ss.solve(ss.build_milp(M_s, D, e, 20.0, 0.0, eps_plan))
    check("3 VERIFY-2 counterexample: new eps 0 splits, old eps 2",
          r_new["splits"] == 0 and r_old["splits"] == 2,
          f"new {r_new['splits']} old {r_old['splits']}")


# --------------------------------------------------------------- 4. balance pass
def oracle_balance(M_s, tau, z, eta):
    """Two dense LPs, hand-built: min t = max_j |mass_j/tau - 1|, then min spread at t*."""
    S, k = z.shape
    n = S * k
    A_eq = np.zeros((S, n + 1))
    for s in range(S):
        A_eq[s, s * k:(s + 1) * k] = 1.0
    mass = np.zeros((k, n + 1))
    for j in range(k):
        for s in range(S):
            mass[j, s * k + j] = M_s[s] / tau
    lo = (eta * z).ravel().astype(float)
    hi = z.ravel().astype(float)
    c = np.zeros(n + 1)
    c[n] = 1.0
    tcol = np.zeros((k, n + 1))
    tcol[:, n] = -1.0
    A_ub = np.vstack([mass + tcol, -mass + tcol])
    b_ub = np.concatenate([np.ones(k), -np.ones(k)])
    r1 = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=np.ones(S),
                 bounds=np.stack([np.append(lo, 0.0), np.append(hi, np.inf)], axis=1),
                 method="highs")
    if not r1.success:
        return None
    t = float(r1.x[n])
    # LP2 with u, l
    A_eq2 = np.zeros((S, n + 2))
    A_eq2[:, :n] = A_eq[:, :n]
    mass2 = np.zeros((k, n + 2))
    mass2[:, :n] = mass[:, :n]
    u = np.zeros((k, n + 2))
    u[:, n] = -1.0
    lcol = np.zeros((k, n + 2))
    lcol[:, n + 1] = 1.0
    c2 = np.zeros(n + 2)
    c2[n], c2[n + 1] = 1.0, -1.0
    A_ub2 = np.vstack([mass2 + u, -mass2 + lcol, mass2, -mass2])
    tt = t * (1 + 1e-9) + 1e-12
    b_ub2 = np.concatenate([np.zeros(2 * k), np.full(k, 1 + tt), np.full(k, -(1 - tt))])
    r2 = linprog(c2, A_ub=A_ub2, b_ub=b_ub2, A_eq=A_eq2, b_eq=np.ones(S),
                 bounds=np.stack([np.concatenate([lo, [0, 0]]),
                                  np.concatenate([hi, [np.inf, np.inf]])], axis=1),
                 method="highs")
    if not r2.success:
        return None
    y = np.clip(r2.x[:n].reshape(S, k), 0, 1)
    y = np.where(z, y, 0.0)
    y = y / y.sum(axis=1, keepdims=True)
    m = M_s @ y
    return dict(t=t, spread=float(r2.x[n] - r2.x[n + 1]), masses=m,
                max_dev_rel=float(np.abs(m - tau).max() / tau),
                spread_rel=float((m.max() - m.min()) / m.mean()))


def m4():
    print("\n== 4  balance_pass vs two hand-built LPs ==")
    rng = np.random.default_rng(4242)
    edges6 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    edgesC = edges6 + [(5, 0)]
    n, bad_z, bad_band, bad_eta, bad_t, bad_spread, wider = 0, 0, 0, 0, 0, 0, 0
    worst = None
    for t in range(80):
        S, k = 6, int(rng.choice([2, 3]))
        edges = edges6 if t % 2 else edgesC
        M_s = rng.uniform(0.5, 6.0, S)
        D = rng.uniform(0.01, 60.0, (S, k))
        tau = float(M_s.sum()) / k
        delta = float(rng.choice([0.02, 0.05, 0.10]))
        try:
            prob = ss.build_milp(M_s, D, edges, tau, delta, ss.eps_lexicographic(M_s, D))
            res = ss.solve(prob)
        except RuntimeError:
            continue
        pas = ss.balance_pass(prob, res["z"])
        orc = oracle_balance(M_s, tau, res["z"], prob.eta)
        n += 1
        if not (pas["y"][~res["z"]] == 0.0).all():
            bad_z += 1
        m = pas["masses"]
        if not ((m >= tau * (1 - delta) - 1e-7).all() and (m <= tau * (1 + delta) + 1e-7).all()):
            bad_band += 1
        if not (pas["y"][res["z"]] >= prob.eta - 1e-7).all():
            bad_eta += 1
        if abs(pas["max_dev_rel"] - orc["t"]) > 1e-6:
            bad_t += 1
            print("   maxdev differs", pas["max_dev_rel"], orc["t"])
        if pas["spread_rel"] * m.mean() / tau > orc["spread"] + 1e-6:
            bad_spread += 1
            print("   spread worse than oracle", pas["spread_rel"], orc["spread"])
        if pas["spread_rel"] > res["spread_rel"] + 1e-9:
            wider += 1
            if worst is None or pas["spread_rel"] - res["spread_rel"] > worst[0]:
                worst = (pas["spread_rel"] - res["spread_rel"], M_s, D, delta, edges, k)
    check("4 balance_pass leaves z alone", bad_z == 0, f"{n} trials")
    check("4 balance_pass keeps the band", bad_band == 0, f"{n} trials")
    check("4 balance_pass keeps eta z <= y", bad_eta == 0, f"{n} trials")
    check("4 max deviation matches the oracle LP1", bad_t == 0, f"{n} trials")
    check("4 spread matches the oracle LP2 (not worse)", bad_spread == 0, f"{n} trials")
    check("4 pass spread <= MILP spread", wider == 0,
          f"{n} trials, {wider} wider" + (f"  worst {worst[0]:.4g}" if worst else ""))
    if worst:
        print("   widest case:", worst)


# --------------------------------------------------------------- 5. realise
def m5():
    print("\n== 5  realise ==")
    rng = np.random.default_rng(5150)
    edges6 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    bad_whole = bad_target = bad_frac = bad_cost = bad_mass = 0
    n = 0
    for t in range(25):
        S, k, per = 6, int(rng.choice([2, 3])), int(rng.integers(3, 8))
        M_s = rng.uniform(1.0, 6.0, S)
        cx = rng.uniform(0, 5, (k, 2))
        off = rng.normal(0, 0.15, (S * per, 2))
        xy = np.repeat(np.stack([np.arange(S, dtype=float), np.zeros(S)], axis=1), per, axis=0) + off
        state_idx = np.repeat(np.arange(S), per)
        w = rng.uniform(0.5, 1.5, S * per)
        M = np.concatenate([w[state_idx == s] / w[state_idx == s].sum() * M_s[s]
                            for s in range(S)])
        D = np.zeros((S, k))
        for s in range(S):
            sel = state_idx == s
            d2 = ((xy[sel, None, :] - cx[None, :, :]) ** 2).sum(axis=2)
            D[s] = (M[sel, None] * d2).sum(axis=0) / M[sel].sum()
        tau = float(M_s.sum()) / k
        delta = float(rng.choice([0.05, 0.10]))
        try:
            prob = ss.build_milp(M_s, D, edges6, tau, delta, ss.eps_lexicographic(M_s, D))
            res = ss.solve(prob)
        except RuntimeError:
            continue
        pas = ss.balance_pass(prob, res["z"])
        out = ss.realise(xy, M, state_idx, res["z"], pas["y"], cx, rounds=5)
        n += 1
        lab = out["labels"]
        if (lab < 0).any():
            bad_whole += 1
        for s in range(S):
            sel = state_idx == s
            if s not in res["split_states"]:
                if len(set(lab[sel].tolist())) != 1 or lab[sel][0] != int(np.argmax(res["z"][s])):
                    bad_whole += 1
            else:
                got = np.array([M[sel][lab[sel] == j].sum() for j in range(k)])
                want = pas["y"][s] * M_s[s]
                one_zip = M[sel].max()
                if (np.abs(got - want) > one_zip + 1e-7).any():
                    bad_target += 1
                    print("   target miss", s, got, want, one_zip)
                touching = int(res["z"][s].sum())
                if out["states"][s]["n_fractional"] > touching - 1:
                    bad_frac += 1
                    print("   n_frac", out["states"][s]["n_fractional"], touching)
                cr = out["states"][s]["cost_rounds"]
                if any(b > a + 1e-9 for a, b in zip(cr, cr[1:])):
                    bad_cost += 1
                if len(cr) != out["states"][s]["rounds_used"] + 1:
                    bad_cost += 1
                if abs(got.sum() - M_s[s]) > 1e-7:
                    bad_mass += 1
    check("5 unsplit states go whole to their z district", bad_whole == 0, f"{n} trials")
    check("5 split-state masses within one zip of the target", bad_target == 0, f"{n} trials")
    check("5 n_fractional <= (districts touching - 1)", bad_frac == 0, f"{n} trials")
    check("5 cost_rounds non-increasing, length = rounds_used + 1", bad_cost == 0, f"{n} trials")
    check("5 each state's mass is conserved", bad_mass == 0, f"{n} trials")

    # a rejected round must leave labels and centres untouched -- force it with rounds=1 on a
    # geometry where recentroiding from FULL membership hurts the split state
    from tests.test_state_splits import COMB, FAR, path_toy
    toy = path_toy(COMB, centres=FAR)
    prob = ss.build_milp(toy["M_s"], toy["D"], edges6, float(toy["tau"]), 0.10,
                         ss.eps_lexicographic(toy["M_s"], toy["D"]))
    res = ss.solve(prob)
    pas = ss.balance_pass(prob, res["z"])
    outs = {r: ss.realise(toy["xy"], toy["M"], toy["state_idx"], res["z"], pas["y"], FAR, rounds=r)
            for r in range(0, 7)}
    mono = all(all(b <= a + 1e-12 for a, b in zip(outs[r]["states"][s]["cost_rounds"],
                                                  outs[r]["states"][s]["cost_rounds"][1:]))
               for r in outs for s in res["split_states"])
    # once rounds_used saturates below the cap, more rounds must change nothing
    used = {r: outs[r]["rounds_used"] for r in outs}
    sat = [r for r in range(1, 7) if used[r] == used[r - 1]]
    stable = all(np.array_equal(outs[r]["labels"], outs[r - 1]["labels"]) for r in sat)
    check("5 cost_rounds monotone for every round cap", mono, f"{used}")
    check("5 a stopped round leaves the labels unchanged", stable, f"saturated at {sat}")


# --------------------------------------------------------------- 6. scale
def m6():
    print("\n== 6  size at S = 49, k = 18, E = 107 ==")
    rng = np.random.default_rng(49)
    S, k, E = 49, 18, 107
    # a connected random rook-like graph with exactly 107 edges over 49 nodes
    edges = [(s, s + 1) for s in range(S - 1)]              # a spanning path: 48 edges
    pool = [(u, v) for u in range(S) for v in range(u + 2, S)]
    extra = rng.choice(len(pool), E - len(edges), replace=False)
    edges += [pool[i] for i in extra]
    M_s = rng.uniform(0.2, 12.0, S)
    D = rng.uniform(0.01, 100.0, (S, k))
    p = ss.build_milp(M_s, D, edges, float(M_s.sum()) / k, 0.05, ss.eps_lexicographic(M_s, D))
    counts = {name: b - a for name, (a, b) in p.rows.items()}
    print("   variables:", p.n_var, " (z", S * k, "y", S * k, "r", S * k, "flow", 2 * E * k, ")")
    print("   integral :", int(p.integrality.sum()))
    print("   rows     :", p.A.shape[0], counts)
    check("6 variables = 3*S*k + 2*E*k", p.n_var == 3 * S * k + 2 * E * k, f"{p.n_var}")
    check("6 integral = 2*S*k", int(p.integrality.sum()) == 2 * S * k)
    check("6 rows == the plan's 6,583", p.A.shape[0] == 6583, f"code {p.A.shape[0]}")
    plan_blocks = {"place": S, "yz": S * k, "rz": S * k, "band": k, "root": k,
                   "cap(pair)": 2 * E * k, "net": S * k}
    print("   plan's block table (no eta rows, capacity per arc *pair*):",
          plan_blocks, "total", sum(plan_blocks.values()))


if __name__ == "__main__":
    m1()
    m1_rows()
    m1_scf()
    m2()
    m3()
    m4()
    m5()
    m6()
    print("\n", "-" * 60)
    print(f"{len(FAIL)} failing checks")
    for f in FAIL:
        print("  FAIL", f)
