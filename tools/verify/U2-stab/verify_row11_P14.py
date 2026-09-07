"""Row 11 / P1.4: the tie identity, and H2 vs distinctness on the structured toy.

Tie identity: symbolic.  Toy counts: recounted by an INDEPENDENT grouping (all-pairs
comparison rather than a value->count dict), with the matching recomputed by brute-force
greedy from verify_core and by scipy's Hungarian (cross-checked against a networkx blossom
oracle).  E5 is then re-run at three other seeds.
"""
import sys, itertools
import numpy as np, sympy as sp, networkx as nx
from scipy.optimize import linear_sum_assignment
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import greedy, blocking_pairs

FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

# ---------------- the tie identity (symbolic)
lam, th = sp.symbols("lam theta")
Bj = sp.Symbol("B_j")
w = (1 - lam)*(1 - th)
chk("P1.4 tie identity: b_ij = b_i'j = 0 => g_ij = g_i'j = B_j",
    sp.simplify((Bj + w*0) - (Bj + w*0)) == 0 and sp.simplify(Bj + w*0 - Bj) == 0)
bi, bk = sp.symbols("b_i b_k")
chk("P1.4 converse: g_ij = g_i'j <=> b_ij = b_i'j whenever w != 0",
    sp.solve(sp.Eq(Bj + w*bi, Bj + w*bk), bi) == [bk])

# ---------------- rebuild E5's toy (same generator; the COUNTING is independent)
def toy(seed):
    rng = np.random.default_rng(seed)
    n, k, wv = 111, 13, 42
    B = (rng.integers(900, 1100, size=k) * 1000).tolist()
    b = np.zeros((n, k), dtype=np.int64)
    for i in range(n):
        for j in rng.choice(k, size=int(rng.integers(1, 4)), replace=False):
            b[i, j] = int(rng.integers(1, 12000))
    g = (np.array(B)[None, :] + wv * b).astype(np.int64).tolist()
    return g, b, n, k

def hung_log(g):
    a = np.log(np.asarray(g, float))
    r, c = linear_sum_assignment(a.T, maximize=True)     # rows = districts
    s = [None]*len(g[0])
    for rr, cc in zip(r, c): s[rr] = int(cc)
    return tuple(s)

def blossom_log(g):
    """Independent oracle: networkx general-graph max-weight matching (Blossom)."""
    n, k = len(g), len(g[0])
    H = nx.Graph()
    for i in range(n):
        for j in range(k):
            H.add_edge(("r", i), ("d", j), weight=float(np.log(g[i][j])))
    M = nx.max_weight_matching(H, maxcardinality=True)
    s = [None]*k
    for u, v in M:
        (i, j) = (u[1], v[1]) if u[0] == "r" else (v[1], u[1])
        s[j] = i
    return tuple(s)

g, b, n, k = toy(20260902)

# independent tie count: all-pairs comparison within each district column
ties = 0
for j in range(k):
    col = [g[i][j] for i in range(n)]
    ties += sum(1 for x, y in itertools.combinations(col, 2) if x == y)
chk("E5 exact ties within district columns = 56,872 (independent all-pairs recount)",
    ties == 56872, ties)
zero = int((b == 0).sum())
chk("E5 zero-book cells = 1,222 of 1,443", zero == 1222 and n*k == 1443, f"{zero} of {n*k}")
chk("E5 distinctness is FALSE (ties > 0), i.e. P1.4's premise", ties > 0)

sg, rounds, h2 = greedy(g)
chk("E5 per-round argmax unique at all 13 rounds (H2 holds despite 56,872 ties)",
    h2 and len(rounds) == 13, [r[2] for r in rounds])
sl = hung_log(g)
sb = blossom_log(g)
chk("E5 oracle agreement: scipy Hungarian == networkx Blossom on the toy", sl == sb, (sl, sb))
bp = blocking_pairs(g, sl)
chk("E5 blocking pairs of the log roster = 1", len(bp) == 1, bp)
r0 = next(t for t, (i, j, _u) in enumerate(rounds) if sl[j] != i)
ir, jr, _ = rounds[r0]
chk("E5 first deviation at round 6 of 13 (1-indexed)", r0 + 1 == 6, f"0-indexed r={r0}")
chk("E5 first-deviation pair is (rep 8, district 2)", (ir, jr) == (8, 2), (ir, jr))
chk("E5 the enumerated blocking set is exactly {(8,2)}", bp == [(8, 2)], bp)

# ---------------- re-run at three other seeds
print("\n  E5 re-run at three other seeds:")
allok = True
for sd in (11111, 20260903, 987654321):
    g2, b2, _, _ = toy(sd)
    t2 = 0
    for j in range(k):
        col = [g2[i][j] for i in range(n)]
        t2 += sum(1 for x, y in itertools.combinations(col, 2) if x == y)
    sg2, rd2, h22 = greedy(g2)
    sl2 = hung_log(g2)
    bp2 = blocking_pairs(g2, sl2)
    r2 = next((t for t, (i, j, _u) in enumerate(rd2) if sl2[j] != i), None)
    print(f"    seed {sd}: ties={t2}  zero-book={int((b2==0).sum())}/1443  H2={h22}  "
          f"greedy==logHung={sg2==sl2}  blocking={len(bp2)}  first-dev round={None if r2 is None else r2+1}")
    if not h22: allok = False
    if r2 is not None and (rd2[r2][0], rd2[r2][1]) not in bp2: allok = False
chk("E5 at three other seeds: H2 holds, and the first-deviation pair blocks whenever they differ",
    allok)

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
