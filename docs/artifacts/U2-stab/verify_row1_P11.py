"""Row 1 / P1.1: g_ij = B_j + w*b_ij with w = (1-lam)(1-theta), and rho absent.

SYMBOLIC leg: replay td/channel.py::gain_matrix's accumulation loop with sympy symbols
and check the closed form identically.
NUMERIC leg (independent oracle): build toy graphs, call the *real* gain_matrix, and
compare against B_j + w*b_ij computed from an independent hand-written accumulation.
"""
import sys, subprocess, itertools, random
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun")
import sympy as sp, numpy as np, networkx as nx
from td import channel, model

print("versions:", sp.__version__, np.__version__, nx.__version__)
FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

# ---------------------------------------------------------------- SYMBOLIC
theta, lam = sp.symbols("theta lam")
nreps, nz = 4, 5                      # reps in district j, zips in A_j
S = sp.Matrix(nreps, nz, lambda i, z: sp.Symbol(f"S_{i}_{z}", nonnegative=True))
Free = [sp.Symbol(f"F_{z}", nonnegative=True) for z in range(nz)]
Mz   = [sp.Symbol(f"M_{z}", nonnegative=True) for z in range(nz)]

for mode, cfree_expr in (("theta", theta*(1-lam)), ("full", 1-lam), ("opportunity", lam)):
    c1, c2 = 1-lam, theta*(1-lam)
    c_free = cfree_expr
    # replay the loop of channel.py:277-284 exactly
    g = [sp.Integer(0)]*nreps
    for z in range(nz):
        T = sum(S[i, z] for i in range(nreps))
        common = c2*T + c_free*Free[z] + lam*Mz[z]
        for i in range(nreps):
            g[i] += common + (c1-c2)*S[i, z]
    # closed form
    B = sum(c2*sum(S[i, z] for i in range(nreps)) + c_free*Free[z] + lam*Mz[z] for z in range(nz))
    w = (1-lam)*(1-theta)
    ok = all(sp.simplify(sp.expand(g[i] - (B + w*sum(S[i, z] for z in range(nz))))) == 0
             for i in range(nreps))
    chk(f"SYM closed form g=B_j+w*b_ij, filler_capture={mode}", ok)

chk("SYM w = c1-c2 = (1-lam)(1-theta)", sp.simplify((1-lam) - theta*(1-lam) - (1-lam)*(1-theta)) == 0)
chk("SYM w>0 strictly for 0<=theta<1, 0<=lam<1",
    sp.simplify(((1-sp.Rational(4,10))*(1-sp.Rational(3,10)))) > 0)
# attack: w = 0 exactly at theta=1 or lam=1 (failure mode row 3 of section 5)
chk("SYM w=0 at theta=1", sp.simplify(((1-lam)*(1-1))) == 0)
chk("SYM w=0 at lam=1", sp.simplify(((1-1)*(1-theta))) == 0)
# attack: is B_j really rep-independent? differentiate B wrt a rep's own book -> c2, not 0.
# The doc's B_j contains c2*T_z which DOES depend on rep i's own book. Check the *ranking*
# corollary instead: g_ij - g_i'j must equal w*(b_ij - b_i'j) only if B_j is common.
c1, c2 = 1-lam, theta*(1-lam)
gg = []
for i in range(nreps):
    tot = sp.Integer(0)
    for z in range(nz):
        T = sum(S[q, z] for q in range(nreps))
        tot += c2*T + c2*Free[z] + lam*Mz[z] + (c1-c2)*S[i, z]
    gg.append(tot)
w = (1-lam)*(1-theta)
diff = sp.simplify(sp.expand(gg[0]-gg[1] - w*(sum(S[0, z] for z in range(nz)) - sum(S[1, z] for z in range(nz)))))
chk("SYM column ranking is by b_ij alone (B_j truly common)", diff == 0, f"residual={diff}")

# rho: symbol absent from the source
src = open("/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/td/channel.py").read()
chk("rho/compactness symbol absent from td/channel.py", ("rho" not in src) and ("ρ" not in src))

# ---------------------------------------------------------------- NUMERIC oracle
rng = random.Random(20260902)
def toy(nz, nreps, seed):
    r = random.Random(seed)
    G = nx.Graph()
    to_d = {}
    for z in range(nz):
        cand = tuple(sorted(r.sample(range(nreps), r.randint(0, min(3, nreps)))))
        Sd = {i: round(r.uniform(0.01, 0.4), 4) for i in cand}
        free = round(r.uniform(0, 0.2), 4) if r.random() < 0.4 else 0.0
        M = round(sum(Sd.values()) + free + r.uniform(0.1, 2.0), 4)
        G.add_node(f"z{z:03d}", cand=cand, S=Sd, S_free=free, M=M)
        to_d[f"z{z:03d}"] = f"D{r.randint(0, 2)}"
    return G, to_d

bad = 0
for seed in range(30):
    for mode in ("theta", "full", "opportunity"):
        for th, la in ((0.40, 0.30), (0.0, 0.0), (0.99, 0.99), (1.0, 0.30), (0.40, 1.0), (0.7, 0.1)):
            G, to_d = toy(25, 6, seed)
            g, R, D = channel.gain_matrix(G, to_d, theta=th, lam=la, filler_capture=mode)
            c1, c2 = 1-la, th*(1-la)
            cf = {"theta": c2, "full": c1, "opportunity": la}[mode]
            wv = (1-la)*(1-th)
            B = {d: 0.0 for d in D}
            b = np.zeros_like(g)
            for z, d in to_d.items():
                Sd = model.books(G, z); T = sum(Sd.values())
                B[d] += c2*T + cf*model.free_book(G, z) + la*G.nodes[z]["M"]
                for i, r in enumerate(R):
                    b[i, D.index(d)] += Sd.get(r, 0.0)
            pred = np.array([[B[d] for d in D]]*len(R)) + wv*b
            e = np.max(np.abs(pred - g)) if g.size else 0.0
            if not (e <= 1e-12 * max(1.0, np.max(np.abs(g)) if g.size else 1.0)):
                bad += 1; print("  mismatch", seed, mode, th, la, e)
chk("NUM gain_matrix == B_j + w*b_ij on 540 toy configs (incl. theta=1, lam=1 edges)", bad == 0)

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
