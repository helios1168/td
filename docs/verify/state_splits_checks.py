"""Adversarial checks on Track 2 of docs/BORDERS_PLAN.md (lines 86-144).

Run:  /Users/ntlee/projects/td/.venv/bin/python3 \
        /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/state_splits_checks.py

Deterministic (seeds pinned).  Versions printed at the top.
Sections:
  C1   scf contiguity block: iff-connected-and-non-empty, brute force on small graphs
  C1b  soundness caveat: the block needs r integral
  C2   epsilon calibrated at y0 -- counterexample MILP
  C2b  contiguity is imposed on z, not on the realised y-support
  C3   balance pass: band preservation, tightening, and spread widening
  C5   variable and constraint counts, and the state rook graph's edge count
"""

from __future__ import annotations

import sys

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

print(f"python {sys.version.split()[0]}  numpy {np.__version__}  scipy {scipy.__version__}")


# ----------------------------------------------------------------- helpers
def connected(nodes, edges):
    """BFS on the induced subgraph; False for the empty set."""
    nodes = set(nodes)
    if not nodes:
        return False
    adj = {u: set() for u in nodes}
    for u, v in edges:
        if u in nodes and v in nodes:
            adj[u].add(v)
            adj[v].add(u)
    start = next(iter(nodes))
    seen, stack = {start}, [start]
    while stack:
        u = stack.pop()
        for w in adj[u]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return seen == nodes


def _lp_feasible(A, lo, hi, bounds):
    A, lo, hi = np.asarray(A), np.asarray(lo), np.asarray(hi)
    res = linprog(np.zeros(A.shape[1]),
                  A_ub=np.vstack([A[np.isfinite(hi)], -A[np.isfinite(lo)]]),
                  b_ub=np.concatenate([hi[np.isfinite(hi)], -lo[np.isfinite(lo)]]),
                  bounds=bounds, method="highs")
    return res.status == 0


def scf_feasible(z, edges, n_nodes, N, root_binary=True):
    """Feasibility of the plan's scf block for ONE district, z fixed.

    Variables: f_(u->v) >= 0 for both orientations of every edge, then r_s.
    Rows:  f_uv + f_vu <= (N-1) z_u  and  <= (N-1) z_v      (edge capacity)
           net inflow at s  >=  z_s - N r_s                 (consumption)
           sum_s r_s = 1,  r_s <= z_s                       (one root, inside the set)
    root_binary=True  -> r a unit vector (the MILP's integral r), enumerated.
    root_binary=False -> r continuous in [0, z_s] (what the LP relaxation sees).
    """
    arcs = [(u, v) for (u, v) in edges] + [(v, u) for (u, v) in edges]
    na = len(arcs)

    def caps(nv):
        A, lo, hi = [], [], []
        for (u, v) in edges:
            row = np.zeros(nv)
            row[arcs.index((u, v))] = 1.0
            row[arcs.index((v, u))] = 1.0
            for w in (u, v):
                A.append(row.copy()); lo.append(-np.inf); hi.append((N - 1) * z[w])
        return A, lo, hi

    def inflow_row(nv, s):
        row = np.zeros(nv)
        for i, (u, v) in enumerate(arcs):
            if v == s:
                row[i] += 1.0
            if u == s:
                row[i] -= 1.0
        return row

    if root_binary:
        for rt in range(n_nodes):
            if z[rt] < 0.5:
                continue
            A, lo, hi = caps(na)
            for s in range(n_nodes):
                A.append(inflow_row(na, s))
                lo.append(z[s] - N * (1.0 if s == rt else 0.0))
                hi.append(np.inf)
            if _lp_feasible(A, lo, hi, [(0, None)] * na):
                return True
        return False

    nv = na + n_nodes
    A, lo, hi = caps(nv)
    for s in range(n_nodes):
        row = inflow_row(nv, s)
        row[na + s] = N                                   # inflow + N r_s >= z_s
        A.append(row); lo.append(z[s]); hi.append(np.inf)
    row = np.zeros(nv); row[na:] = 1.0
    A.append(row); lo.append(1.0); hi.append(1.0)
    bounds = [(0, None)] * na + [(0.0, float(z[s])) for s in range(n_nodes)]
    return _lp_feasible(A, lo, hi, bounds)


# ------------------------------------------------------------------- C1
GRAPHS = {
    "path6": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
    "cycle6": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)],
    "grid2x3": [(0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)],
    "star+edge": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 2)],
    "two-triangles": [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)],
    "bridge": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 2), (3, 5)],
}


def c1():
    print("\n=== C1  scf admits exactly the connected non-empty z-sets (r integral) ===")
    bad = []
    for name, edges in GRAPHS.items():
        for mask in range(1 << 6):
            z = np.array([(mask >> i) & 1 for i in range(6)], float)
            S = [i for i in range(6) if z[i] > 0.5]
            want = connected(S, edges)          # non-empty AND connected
            got = scf_feasible(z, edges, 6, N=6)
            if want != got:
                bad.append((name, tuple(S), want, got))
    print(f"  {len(GRAPHS)} graphs x 64 subsets, N = #nodes = 6 : mismatches = {len(bad)}")
    for b in bad:
        print("   MISMATCH", b)
    print("  empty z-set admitted?", scf_feasible(np.zeros(6), GRAPHS["path6"], 6, N=6),
          " (sum_s r_sj = 1 with r <= z forces a root, so every district is non-empty)")
    print("  full path selected, capacity (N-1) = 5 :",
          scf_feasible(np.ones(6), GRAPHS["path6"], 6, N=6))
    print("  same with capacity cut to 4 (N too small) :",
          scf_feasible(np.ones(6), GRAPHS["path6"], 6, N=5),
          " -> N-1 = #nodes-1 is exactly enough; any N >= #states works")


def c1b():
    print("\n=== C1b  the block is sound only because r is integral ===")
    edges = GRAPHS["path6"]
    z = np.array([1, 1, 0, 0, 1, 1], float)   # {0,1} u {4,5}, disconnected
    print("  disconnected {0,1,4,5}: r integral   ->",
          scf_feasible(z, edges, 6, N=6, root_binary=True))
    print("  disconnected {0,1,4,5}: r continuous ->",
          scf_feasible(z, edges, 6, N=6, root_binary=False))
    print("  a continuous root splits 0.5/0.5 and admits any z-set whose components are")
    print("  smaller than N/2 -- fine for correctness (r is binary), weak as a relaxation.")


# ------------------------------------------------------------------- MILP
def build_and_solve(M, D, tau, delta, eps, edges, gap=0.0):
    """The plan's MILP.  Variables [z (S*K) | y (S*K) | r (S*K) | f (2E*K)]."""
    S, K = D.shape
    arcs = [(u, v) for u, v in edges] + [(v, u) for u, v in edges]
    na = len(arcs)
    nz = ny = nr = S * K
    n = nz + ny + nr + na * K
    iz = lambda s, j: s * K + j                                    # noqa: E731
    iy = lambda s, j: nz + s * K + j                               # noqa: E731
    ir = lambda s, j: nz + ny + s * K + j                          # noqa: E731
    iff = lambda a, j: nz + ny + nr + j * na + a                   # noqa: E731
    N = S

    c = np.zeros(n)
    for s in range(S):
        for j in range(K):
            c[iz(s, j)] = 1.0
            c[iy(s, j)] = eps * M[s] * D[s, j]
    const = -S                                     # the "-1" per state

    rows, lo, hi = [], [], []

    def add(row, l, h):
        rows.append(row); lo.append(l); hi.append(h)

    for s in range(S):                                              # sum_j y = 1
        r = np.zeros(n)
        for j in range(K):
            r[iy(s, j)] = 1.0
        add(r, 1.0, 1.0)
    for s in range(S):                                              # y <= z, r <= z
        for j in range(K):
            r = np.zeros(n); r[iy(s, j)] = 1.0; r[iz(s, j)] = -1.0; add(r, -np.inf, 0.0)
            r = np.zeros(n); r[ir(s, j)] = 1.0; r[iz(s, j)] = -1.0; add(r, -np.inf, 0.0)
    for j in range(K):                                              # band
        r = np.zeros(n)
        for s in range(S):
            r[iy(s, j)] = M[s]
        add(r, tau * (1 - delta), tau * (1 + delta))
    for j in range(K):                                              # one root
        r = np.zeros(n)
        for s in range(S):
            r[ir(s, j)] = 1.0
        add(r, 1.0, 1.0)
    for j in range(K):                                              # capacity
        for (u, v) in edges:
            a1, a2 = arcs.index((u, v)), arcs.index((v, u))
            for w in (u, v):
                r = np.zeros(n)
                r[iff(a1, j)] = 1.0; r[iff(a2, j)] = 1.0; r[iz(w, j)] = -(N - 1)
                add(r, -np.inf, 0.0)
    for j in range(K):                                              # consumption
        for s in range(S):
            r = np.zeros(n)
            for a, (u, v) in enumerate(arcs):
                if v == s:
                    r[iff(a, j)] += 1.0
                if u == s:
                    r[iff(a, j)] -= 1.0
            r[iz(s, j)] = -1.0
            r[ir(s, j)] = N
            add(r, 0.0, np.inf)

    integrality = np.zeros(n)
    integrality[:nz] = 1
    integrality[nz + ny:nz + ny + nr] = 1
    ub = np.full(n, np.inf)
    ub[:nz + ny + nr] = 1.0
    res = milp(c, constraints=LinearConstraint(np.array(rows), lo, hi),
               integrality=integrality, bounds=Bounds(np.zeros(n), ub),
               options={"mip_rel_gap": gap})
    assert res.status == 0, res.message
    zsol = np.round(res.x[:nz]).reshape(S, K)
    ysol = res.x[nz:nz + ny].reshape(S, K)
    return res.fun + const, int(round(zsol.sum() - S)), zsol, ysol


# ------------------------------------------------------------------- C2
def c2():
    print("\n=== C2  eps = 0.5 / (sum_s sum_j M_s D_sj y0_sj) ===")
    # (a) the literal claim: the term at an arbitrary feasible y is unbounded in eps units
    M = np.array([1.0, 1.0])
    D = np.array([[1e-3, 100.0], [1e-3, 100.0]])
    y0 = np.array([[1.0, 0.0], [1.0, 0.0]])
    yb = np.array([[0.0, 1.0], [0.0, 1.0]])
    V0 = float((M[:, None] * D * y0).sum())
    Vb = float((M[:, None] * D * yb).sum())
    print(f"  toy 2x2: V(y0) = {V0:g}, V(other feasible y) = {Vb:g}, "
          f"term at that y = {0.5 * Vb / V0:g} splits  (claim: < 0.5)")

    # (b) the operational claim -- does the tie-break BUY splits?  Smallest instance found.
    #     path A-B-C-D, masses 10 each, K = 2, tau = 20, delta = 0, crossed preferences.
    Ms = np.array([10.0, 10.0, 10.0, 10.0])
    edges = [(0, 1), (1, 2), (2, 3)]
    Dm = np.array([[1.0, 100.0],      # A prefers district 0
                   [100.0, 1.0],      # B prefers district 1
                   [1.0, 100.0],      # C prefers district 0
                   [100.0, 1.0]])     # D prefers district 1
    tau, delta = 20.0, 0.0
    y0b = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0]])   # "committed" y0
    V0b = float((Ms[:, None] * Dm * y0b).sum())
    eps_plan = 0.5 / V0b
    eps_safe = 0.5 / float((Ms * Dm.max(1)).sum())
    print(f"\n  (b) 4-state path, 2 districts, M = 10 each, tau = {tau}, delta = {delta}")
    print(f"      y0 = the crossed composition (2 splits), V(y0) = {V0b:g}")
    print(f"      eps_plan = {eps_plan:g}   eps_safe = 0.5/sum_s M_s max_j D_sj = {eps_safe:g}")
    for tag, e in (("eps = 0   (pure min-splits)", 0.0),
                   ("eps_plan = 0.5/V(y0)", eps_plan),
                   ("eps_safe", eps_safe)):
        obj, sp, z, y = build_and_solve(Ms, Dm, tau, delta, e, edges)
        print(f"      {tag:28s} -> splits = {sp}   objective = {obj: .5f}")
        if e == eps_plan:
            print(f"        z =\n{z.astype(int)}\n        y =\n{np.round(y, 4)}")
    print("      the minimum split count is 0 ({A,B}|{C,D}); eps_plan returns 2 splits.")

    # (c) size of the mis-scaling on a synthetic 50 x 18 geometry
    rng = np.random.default_rng(7)
    xy = rng.uniform(0, 10, size=(50, 2))
    cj = rng.uniform(0, 10, size=(18, 2))
    Dn = ((xy[:, None, :] - cj[None, :, :]) ** 2).sum(-1)
    Mn = rng.uniform(0.5, 3.0, size=50)
    nearest = Dn.argmin(1)
    V0n = float(sum(Mn[s] * Dn[s, nearest[s]] for s in range(50)))
    Vmax = float((Mn * Dn.max(1)).sum())
    print(f"\n  (c) synthetic 50x18 geometry: sum M D y0 = {V0n:.1f}, "
          f"sum_s M_s max_j D_sj = {Vmax:.1f}")
    print(f"      ratio {Vmax / V0n:.1f}x -> the tie-break term can reach "
          f"{0.5 * Vmax / V0n:.1f} splits under eps_plan")
    print(f"      eps_safe = {V0n / Vmax:.4f} x eps_plan on this instance")


def c2b():
    print("\n=== C2b  contiguity is imposed on z, not on the realised y-support ===")
    Ms = np.array([1.0, 2.0, 1.0])                 # path A-B-C, tau = 2, delta = 0
    edges = [(0, 1), (1, 2)]
    Dm = np.array([[0.0, 5.0], [5.0, 0.0], [0.0, 5.0]])
    obj, sp, z, y = build_and_solve(Ms, Dm, tau=2.0, delta=0.0, eps=1e-6, edges=edges)
    print(f"  splits = {sp}\n  z =\n{z.astype(int)}\n  y =\n{np.round(y, 6)}")
    for j in range(2):
        zset = [s for s in range(3) if z[s, j] > 0.5]
        supp = [s for s in range(3) if y[s, j] > 1e-7]
        print(f"  district {j}: z-set {zset} connected = {connected(zset, edges)} | "
              f"y-support {supp} connected = {connected(supp, edges)}")
    print("  a z_sj = 1 with y_sj = 0 is a paid bridge: 1 split buys a disconnected district.")


# ------------------------------------------------------------------- C3
def balance_pass(M, z, tau):
    """min t  s.t.  t >= |sum_s M_s y_sj - tau|,  sum_j y_sj = 1,  0 <= y <= z."""
    S, K = z.shape
    n = S * K + 1
    c = np.zeros(n); c[-1] = 1.0
    A, lo, hi = [], [], []
    for s in range(S):
        r = np.zeros(n); r[s * K:(s + 1) * K] = 1.0
        A.append(r); lo.append(1.0); hi.append(1.0)
    for j in range(K):
        base = np.zeros(n)
        for s in range(S):
            base[s * K + j] = M[s]
        r = base.copy(); r[-1] = -1.0
        A.append(r); lo.append(-np.inf); hi.append(tau)
        r = base.copy(); r[-1] = 1.0
        A.append(r); lo.append(tau); hi.append(np.inf)
    bounds = [(0.0, float(z[s, j])) for s in range(S) for j in range(K)] + [(0.0, None)]
    A, lo, hi = np.array(A), np.array(lo), np.array(hi)
    res = linprog(c, A_ub=np.vstack([A[np.isfinite(hi)], -A[np.isfinite(lo)]]),
                  b_ub=np.concatenate([hi[np.isfinite(hi)], -lo[np.isfinite(lo)]]),
                  bounds=bounds, method="highs")
    if res.status != 0:
        return None, None
    return res.x[-1], res.x[:-1].reshape(S, K)


def masses(M, y):
    return (M[:, None] * y).sum(0)


def c3():
    print("\n=== C3  the balance pass ===")
    print("  (i) the MILP's y is feasible for the pass LP (same z, same sum_j y = 1, same")
    print("      bounds), so t* <= maxdev(MILP y) <= delta*tau: every band row survives.")

    # (ii) MILP at the band edge, the pass strictly tighter.
    Ms = np.array([3.0, 3.0, 3.0])
    edges = [(0, 1), (1, 2)]
    Dm = np.array([[0.0, 10.0], [0.0, 1.0], [10.0, 0.0]])   # B leans to district 0
    tau, delta = 4.5, 0.2
    obj, sp, z, y = build_and_solve(Ms, Dm, tau, delta, 0.5 / 30.0, edges)
    vM = masses(Ms, y)
    t, y2 = balance_pass(Ms, z, tau)
    v2 = masses(Ms, y2)
    band = (tau * (1 - delta), tau * (1 + delta))
    print(f"\n  3 states on a path, M = 3 each, tau = {tau}, band {band}, min splits = {sp}")
    print(f"    MILP  y_B = {np.round(y[1], 4)}  masses {np.round(vM, 4)}  "
          f"maxdev {np.abs(vM - tau).max():.4f}  spread {vM.max() - vM.min():.4f}")
    print(f"    pass  y_B = {np.round(y2[1], 4)}  masses {np.round(v2, 4)}  "
          f"maxdev {np.abs(v2 - tau).max():.4f}  spread {v2.max() - v2.min():.4f}  t* = {t:.4f}")
    print(f"    z unchanged by construction; band still holds: "
          f"{bool(np.all(v2 >= band[0] - 1e-9) and np.all(v2 <= band[1] + 1e-9))}")

    # (iii) can min-max-deviation widen spread = max_j - min_j ?
    print("\n  (iii) random search: fixed z (all districts non-empty), a band-feasible")
    print("        'MILP y', pass vs MILP on spread = max_j mass - min_j mass")
    rng = np.random.default_rng(11)
    worst = None
    n_trials = 6000
    for _ in range(n_trials):
        S, K = 4, 3
        Mr = rng.uniform(0.2, 2.0, size=S)
        zr = (rng.random((S, K)) < 0.7).astype(float)
        for s in range(S):
            if zr[s].sum() == 0:
                zr[s, rng.integers(K)] = 1.0
        if not np.all(zr.sum(0) > 0):
            continue
        tau_r = Mr.sum() / K
        yr = np.zeros((S, K))
        for s in range(S):
            allowed = np.flatnonzero(zr[s])
            yr[s, allowed] = rng.dirichlet(np.ones(len(allowed)))
        vr = masses(Mr, yr)
        if vr.min() <= 1e-9:                       # a district with no mass: not band-feasible
            continue
        tr, yp = balance_pass(Mr, zr, tau_r)
        if tr is None:
            continue
        vp = masses(Mr, yp)
        sr, spd = vr.max() - vr.min(), vp.max() - vp.min()
        if spd > sr + 1e-7 and (worst is None or spd - sr > worst[0]):
            worst = (spd - sr, Mr, zr, yr, vr, vp, tau_r, np.abs(vr - tau_r).max(), tr)
    if worst is None:
        print(f"        none found in {n_trials} random (M, z, y) triples")
    else:
        g, Mr, zr, yr, vr, vp, tau_r, mdr, tr = worst
        print(f"        FOUND: spread widened by {g:.4f}")
        print(f"        M = {np.round(Mr, 4)}  tau = {tau_r:.4f}")
        print(f"        z =\n{zr.astype(int)}")
        print(f"        y_MILP =\n{np.round(yr, 4)}")
        print(f"        masses MILP {np.round(vr, 4)} spread {vr.max() - vr.min():.4f} "
              f"maxdev {mdr:.4f}")
        print(f"        masses pass {np.round(vp, 4)} spread {vp.max() - vp.min():.4f} "
              f"maxdev {tr:.4f}")
        print(f"        (this MILP y would need delta >= {mdr / tau_r:.3f}; the pass's y is"
              f" band-feasible at that delta too)")
    print("        identity: sum_j (mass_j - tau) = 0 => maxdev <= spread <= 2*maxdev,")
    print("        so minimising maxdev pins spread only within a factor 2.")


# ------------------------------------------------------------------- C5
ADJ = """AL:FL,GA,MS,TN
AZ:CA,NM,NV,UT
AR:LA,MS,MO,OK,TN,TX
CA:AZ,NV,OR
CO:KS,NE,NM,OK,UT,WY
CT:MA,NY,RI
DE:MD,NJ,PA
DC:MD,VA
FL:AL,GA
GA:AL,FL,NC,SC,TN
ID:MT,NV,OR,UT,WA,WY
IL:IN,IA,KY,MO,WI
IN:IL,KY,MI,OH
IA:IL,MN,MO,NE,SD,WI
KS:CO,MO,NE,OK
KY:IL,IN,MO,OH,TN,VA,WV
LA:AR,MS,TX
ME:NH
MD:DE,PA,VA,WV,DC
MA:CT,NH,NY,RI,VT
MI:IN,OH,WI
MN:IA,ND,SD,WI
MS:AL,AR,LA,TN
MO:AR,IL,IA,KS,KY,NE,OK,TN
MT:ID,ND,SD,WY
NE:CO,IA,KS,MO,SD,WY
NV:AZ,CA,ID,OR,UT
NH:ME,MA,VT
NJ:DE,NY,PA
NM:AZ,CO,OK,TX,UT
NY:CT,MA,NJ,PA,VT
NC:GA,SC,TN,VA
ND:MN,MT,SD
OH:IN,KY,MI,PA,WV
OK:AR,CO,KS,MO,NM,TX
OR:CA,ID,NV,WA
PA:DE,MD,NJ,NY,OH,WV
RI:CT,MA
SC:GA,NC
SD:IA,MN,MT,NE,ND,WY
TN:AL,AR,GA,KY,MS,MO,NC,VA
TX:AR,LA,NM,OK
UT:AZ,CO,ID,NM,NV,WY
VT:MA,NH,NY
VA:KY,MD,NC,TN,WV,DC
WA:ID,OR
WV:KY,MD,OH,PA,VA
WI:IA,IL,MI,MN
WY:CO,ID,MT,NE,SD,UT"""


def c5():
    print("\n=== C5  size of the model ===")
    d = {ln.split(":")[0]: set(ln.split(":")[1].split(",")) for ln in ADJ.strip().splitlines()}
    states, edges = set(d), set()
    for a, nb in d.items():
        states |= nb
        for b in nb:
            edges.add(tuple(sorted((a, b))))
    asym = sorted((a, b) for a in d for b in d[a] if b in d and a not in d[b])
    print(f"  nodes: {len(states)} (48 lower states + DC)   asymmetric pairs: {asym}")
    print(f"  edges with UT-NM (a Four-Corners point contact) counted: {len(edges)}")
    rook = edges - {("NM", "UT")}
    print(f"  edges under strict rook (drop UT-NM, AZ-CO already out): {len(rook)}"
          f"   <- the plan's 107")
    print(f"  without DC's two edges: {len(rook - {('DC','MD'), ('DC','VA')})}"
          f"   (the usual lower-48 figure is 105)")

    S, K, E = 50, 18, 107
    nz = ny = nr = S * K
    nf = 2 * E * K
    print(f"\n  with the plan's S = {S}, K = {K}, E = {E}:")
    print(f"  variables: z {nz} + r {nr} + y {ny} + flow {nf} = {nz + nr + ny + nf}"
          f"  ({nz + nr} integral)")
    rows = {
        "sum_j y_sj = 1": S,
        "y_sj <= z_sj": S * K,
        "r_sj <= z_sj": S * K,
        "band (two-sided rows)": K,
        "sum_s r_sj = 1": K,
        "edge capacity (2 rows/edge/district)": 2 * E * K,
        "net inflow >= z_sj - N r_sj": S * K,
    }
    for k, v in rows.items():
        print(f"    {k:40s} {v:7d}")
    tot = sum(rows.values())
    print(f"    {'TOTAL rows':40s} {tot:7d}")
    print(f"    variant (band as two one-sided rows, caps per directed arc): {tot + K + 2*E*K}")
    print("  0 <= y <= 1 and the binary ranges are variable bounds, not rows.")
    S2 = 49
    print(f"\n  with S = 49 (48 lower states + DC, which is what the prose describes):")
    print(f"    z = r = y = {S2*K} each, flow {2*E*K}, total vars {3*S2*K + 2*E*K}, "
          f"rows {S2 + 2*S2*K + 2*K + 2*E*K + S2*K}")


if __name__ == "__main__":
    c1()
    c1b()
    c2()
    c2b()
    c3()
    c5()
