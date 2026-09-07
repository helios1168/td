"""Row 10 / P4.2 (EFM strictly stronger than 'no unmatched-rep blocking pair') and
P4.3 (EFM and full staffing are incompatible under H1).

Explicit small instances with a stated outside-option vector d; exhaustive truth table over
ALL partial matchings (districts may be unstaffed), independent of stab.py.
"""
import sys, itertools, random
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import blocking_pairs, maxweight, greedy
from fractions import Fraction

FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

def partial_matchings(n, k):
    for r in range(k + 1):
        for staffed in itertools.combinations(range(k), r):
            for assign in itertools.permutations(range(n), r):
                s = [None]*k
                for t, j in enumerate(staffed): s[j] = assign[t]
                yield tuple(s)

def acceptable(g, d, i, j):        # P4.1's instantiation
    return g[i][j] > d[i]

def is_efm(g, d, sigma):
    """aignerhorev2022: no UNMATCHED agent envies a MATCHED one.
    Here: no unmatched rep i has an acceptable district j that is staffed."""
    matched = {i for i in sigma if i is not None}
    for i in range(len(g)):
        if i in matched: continue
        for j in range(len(g[0])):
            if sigma[j] is not None and acceptable(g, d, i, j):
                return False
    return True

def unmatched_blocking(g, d, sigma):
    """Blocking pairs whose rep is unmatched, with H1 read through d:
    an unmatched rep blocks only where the district is acceptable to it."""
    matched = {i for i in sigma if i is not None}
    out = []
    for i in range(len(g)):
        if i in matched: continue
        for j in range(len(g[0])):
            if sigma[j] is None: continue
            if acceptable(g, d, i, j) and g[i][j] > g[sigma[j]][j]:
                out.append((i, j))
    return out

rng = random.Random(20260902)

# ---------- P4.2 direction 1: EFM => no unmatched-rep blocking pair (exhaustive)
bad, tot = [], 0
for _ in range(400):
    n = rng.randint(2, 5); k = rng.randint(1, min(3, n))
    g = [[rng.randint(1, 12) for _ in range(k)] for _ in range(n)]
    d = [rng.randint(0, 13) for _ in range(n)]
    for s in partial_matchings(n, k):
        tot += 1
        if is_efm(g, d, s) and unmatched_blocking(g, d, s):
            bad.append((g, d, s))
chk(f"P4.2 EFM => no blocking pair with an unmatched rep ({tot} (instance, matching) pairs)",
    not bad, bad[:1])

# ---------- P4.2 direction 2: the converse FAILS -- explicit witness of the stated form
#   pick d_i < g_ij <= g_{sigma(j),j}: envy without blocking
g = [[5, 1], [9, 1]]; d = [0, 0]; s = (1, None)
chk("P4.2 converse fails: explicit witness g=[[5,1],[9,1]], d=(0,0), sigma=(rep1, unstaffed)",
    (not is_efm(g, d, s)) and unmatched_blocking(g, d, s) == [],
    f"EFM={is_efm(g,d,s)}  unmatched-blocking={unmatched_blocking(g,d,s)}  "
    f"(rep0 finds district0 acceptable, 5 > d_0=0, but 5 <= g_10=9: envy, no block)")
found = 0
for _ in range(400):
    n = rng.randint(2, 5); k = rng.randint(1, min(3, n))
    g = [[rng.randint(1, 12) for _ in range(k)] for _ in range(n)]
    d = [rng.randint(0, 3) for _ in range(n)]
    for s in partial_matchings(n, k):
        if (not is_efm(g, d, s)) and not unmatched_blocking(g, d, s): found += 1
chk("P4.2 converse fails generically too", found > 0, f"{found} envy-without-block cases")

# ---------- P4.3: under H1 (d_i < min_j g_ij) with n > k, the only EFM is the empty matching
bad43 = []
for _ in range(300):
    n = rng.randint(2, 5); k = rng.randint(1, n - 1)          # n > k, so some rep is unmatched
    g = [[rng.randint(1, 12) for _ in range(k)] for _ in range(n)]
    d = [min(g[i]) - 1 for i in range(n)]                      # H1: strictly below every g_ij
    efms = [s for s in partial_matchings(n, k) if is_efm(g, d, s)]
    if efms != [tuple([None]*k)]:
        bad43.append((g, d, efms))
chk("P4.3 under H1 and n>k the ONLY envy-free matching is the empty one", not bad43, bad43[:1])
chk("P4.3 the empty matching is vacuously EFM (aignerhorev2022's 'possibly empty')",
    is_efm([[3, 4], [5, 6]], [0, 0], (None, None)))

# attack: H1 is load-bearing -- with d_i above some g_ij, a nonempty EFM can exist
g = [[10, 1], [2, 2], [1, 1]]
d = [0, 100, 100]              # reps 1,2 find nothing acceptable
efms = [s for s in partial_matchings(3, 2) if is_efm(g, d, s)]
chk("P4.3 attack: drop H1 and a nonempty (even fully staffing) EFM exists",
    any(all(x is not None for x in s) for s in efms),
    f"{len(efms)} EFMs, e.g. {[s for s in efms if all(x is not None for x in s)][:2]}")

# ---------- P4.2's punchline: N3 = 0 carries ZERO information about EFM
#   (a) P3.3 already gives no-unmatched-blocking for any max-weight roster, and
#   (b) N3 = 0 and N3 > 0 both coexist with EFM false.
n3zero_efmfalse = n3pos_efmfalse = n3zero_efmtrue = 0
for _ in range(3000):
    n = rng.randint(3, 6); k = rng.randint(1, min(3, n - 1))
    g = [[rng.randint(1, 20) for _ in range(k)] for _ in range(n)]
    d = [min(g[i]) - 1 for i in range(n)]                       # H1
    R, _ = maxweight(g, lambda x: Fraction(x))
    s = R[0]
    n3 = len(blocking_pairs(g, s))
    e = is_efm(g, d, s)
    if n3 == 0 and not e: n3zero_efmfalse += 1
    if n3 > 0 and not e: n3pos_efmfalse += 1
    if n3 == 0 and e: n3zero_efmtrue += 1
chk("P4.2 punchline: N3=0 does not imply EFM (both N3=0/EFM-false and N3>0/EFM-false occur)",
    n3zero_efmfalse > 0 and n3pos_efmfalse > 0 and n3zero_efmtrue == 0,
    f"N3=0 & !EFM: {n3zero_efmfalse}; N3>0 & !EFM: {n3pos_efmfalse}; N3=0 & EFM: {n3zero_efmtrue}")

# ---------- P4.1: with d == 0 every pair is acceptable, so every unmatched cell is envy
n, k = 111, 13
chk("P4.1 arithmetic: with d==0 all 98*13 = 1,274 unmatched cells are envy instances",
    (n - k)*k == 1274, (n-k)*k)

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
