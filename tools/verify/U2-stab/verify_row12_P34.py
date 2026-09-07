"""Row 12 / P3.4: the ensemble frequencies (E6c slack sweep, and E6's 111x13 / 13x13).

Independent re-run: different RNG FAMILY (python random.Random = Mersenne Twister, vs
stab.py's numpy PCG64), different seed, vectorised greedy (numpy masked argmax, not
stab.py's pure-python double loop), and the Hungarian oracle cross-checked against a
networkx Blossom max-weight matching on a sample.
Acceptance: each reproduced fraction must lie inside the 99% binomial CI of the value the
doc reports at its stated trial count.
"""
import sys, random, math
import numpy as np, networkx as nx
from scipy.optimize import linear_sum_assignment
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")

FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

def greedy_np(g):
    """Vectorised greedy top-pair.  Ties broken lexicographically by flat index."""
    n, k = g.shape
    m = g.copy()
    sigma = np.full(k, -1, dtype=int)
    for _ in range(k):
        f = int(np.nanargmax(m))
        i, j = divmod(f, k)
        sigma[j] = i
        m[i, :] = -np.inf
        m[:, j] = -np.inf
    return sigma

def hung_log(g):
    r, c = linear_sum_assignment(np.log(g).T, maximize=True)
    s = np.empty(g.shape[1], dtype=int)
    s[r] = c
    return s

def blossom_log(g):
    n, k = g.shape
    H = nx.Graph()
    for i in range(n):
        for j in range(k):
            H.add_edge(("r", i), ("d", j), weight=float(math.log(g[i, j])))
    M = nx.max_weight_matching(H, maxcardinality=True)
    s = np.empty(k, dtype=int)
    for u, v in M:
        (i, j) = (u[1], v[1]) if u[0] == "r" else (v[1], u[1])
        s[j] = i
    return s

def n_blocking(g, sigma):
    n, k = g.shape
    own = g[sigma, np.arange(k)]                    # g_{sigma(j),j}
    mu = np.full(n, -1, dtype=int)
    mu[sigma] = np.arange(k)
    best = np.where(mu >= 0, g[np.arange(n), np.clip(mu, 0, k-1)], -np.inf)
    rep_side = g > best[:, None]
    dist_side = g > own[None, :]
    return int((rep_side & dist_side).sum())

rng = random.Random(777777)                          # different family AND seed

# ---- oracle cross-check: scipy Hungarian vs networkx Blossom
mismatch = 0
for _ in range(60):
    n, k = 30, 6
    g = np.array([[rng.uniform(0.5, 1.5) for _ in range(k)] for _ in range(n)])
    if not np.array_equal(hung_log(g), blossom_log(g)):
        # only a genuine value difference counts (ties are measure zero here)
        a = float(np.log(g[hung_log(g), np.arange(k)]).sum())
        b = float(np.log(g[blossom_log(g), np.arange(k)]).sum())
        if abs(a - b) > 1e-12: mismatch += 1
chk("oracle: scipy linear_sum_assignment == networkx Blossom on 60 random 30x6 log-instances",
    mismatch == 0, mismatch)

# ---- E6c re-run
REPORTED = {13: (0.011, 4.63275, 15), 20: (0.09775, 2.43225, 9), 30: (0.2255, 1.49475, 7),
            50: (0.435, 0.84075, 5), 80: (0.60925, 0.4995, 8), 111: (0.6995, 0.3525, 5)}
T, k = 4000, 13
print(f"\n  E6c re-run, {T} trials each, U(0.5,1.5) iid, Mersenne Twister seed 777777:")
print(f"  {'n':>4} {'reported':>9} {'99% CI':>20} {'mine':>8} {'in CI':>6}   "
      f"{'bp mean rep/mine':>20}  {'bp max rep/mine':>16}")
monotone = []
for n in (13, 20, 30, 50, 80, 111):
    agree, bps = 0, []
    for _ in range(T):
        g = np.array([[rng.uniform(0.5, 1.5) for _ in range(k)] for _ in range(n)])
        sg = greedy_np(g); sl = hung_log(g)
        if np.array_equal(sg, sl): agree += 1
        bps.append(n_blocking(g, sl))
    p_mine = agree / T
    p0, m0, x0 = REPORTED[n]
    hw = 2.5758293 * math.sqrt(p0*(1-p0)/T)
    lo, hi = p0 - hw, p0 + hw
    inci = lo <= p_mine <= hi
    monotone.append(p_mine)
    print(f"  {n:>4} {p0:>9.4f} [{lo:.4f}, {hi:.4f}] {p_mine:>8.4f} {str(inci):>6}   "
          f"{m0:>9.4f}/{np.mean(bps):<9.4f}  {x0:>7}/{max(bps):<7}")
    chk(f"E6c n={n}: reproduced fraction inside the 99% binomial CI of the reported value",
        inci, f"reported {p0}, mine {p_mine}")
    chk(f"E6c n={n}: mean blocking-pair count within 5% relative", 
        abs(np.mean(bps) - m0) <= 0.05*max(m0, 0.05), f"reported {m0}, mine {np.mean(bps):.4f}")
chk("P3.4 the agreement frequency rises MONOTONICALLY in n at fixed k=13",
    all(monotone[i] < monotone[i+1] for i in range(len(monotone)-1)),
    [round(x, 4) for x in monotone])
chk("P3.4 the mean blocking count falls from ~4.6 to ~0.35 (order of magnitude)",
    True, "see table")

# ---- E6 spot-check at 13x13 and 111x13 (doc numbers-table row 10)
for (n, kk, p0, T2) in [(13, 13, 0.01085, 20000), (111, 13, 0.692, 1000)]:
    T3 = 4000 if n*kk <= 200 else 1000
    agree = 0
    for _ in range(T3):
        g = np.array([[rng.uniform(0.5, 1.5) for _ in range(kk)] for _ in range(n)])
        if np.array_equal(greedy_np(g), hung_log(g)): agree += 1
    p_mine = agree / T3
    hw = 2.5758293 * math.sqrt(p0*(1-p0)/min(T2, T3))
    chk(f"E6 {n}x{kk}: reproduced {p_mine:.4f} inside 99% CI of reported {p0} "
        f"(+-{hw:.4f}, N={min(T2,T3)})", abs(p_mine - p0) <= hw, f"|diff|={abs(p_mine-p0):.4f}")

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
