"""Rows 2,3 / P1.2 (greedy is stable) and P1.3 (under H1+H2+H3 stable set = {greedy}).

Oracle: exhaustive enumeration of every injection J -> I (and, separately, every PARTIAL
matching, to test P1.3's 'any stable sigma staffs all k' step).  Independent of stab.py.
"""
import sys, random, itertools
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import (injections, blocking_pairs, is_stable, stable_set, greedy)

SEED = 20260902
FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

# ---- partial matchings: sigma[j] in {0..n-1} or None, injective on the matched part
def partial_matchings(n, k):
    for staffed in itertools.chain.from_iterable(
            itertools.combinations(range(k), r) for r in range(k+1)):
        for assign in itertools.permutations(range(n), len(staffed)):
            s = [None]*k
            for t, j in enumerate(staffed):
                s[j] = assign[t]
            yield tuple(s)

def blocking_partial(g, sigma):
    n, k = len(g), len(g[0])
    mu = {i: j for j, i in enumerate(sigma) if i is not None}
    out = []
    for i in range(n):
        for j in range(k):
            rep_side = (i not in mu) or (g[i][j] > g[i][mu[i]])
            # H1: an unstaffed district prefers any rep to nobody
            dist_side = (sigma[j] is None) or (g[i][j] > g[sigma[j]][j])
            if rep_side and dist_side:
                out.append((i, j))
    return out

rng = random.Random(SEED)

# ---------------- P1.2: greedy is stable, ties and all, no strictness used
tot = ties_seen = 0
bad12 = []
for trial in range(4000):
    n = rng.randint(1, 7); k = rng.randint(1, min(3, n))
    hi = rng.choice([2, 3, 5, 40])          # small hi => many ties
    g = [[rng.randint(1, hi) for _ in range(k)] for _ in range(n)]
    for tb in (lambda a: a[0], lambda a: a[-1], lambda a: rng.choice(a)):
        s, rounds, h2 = greedy(g, tb)
        tot += 1
        if not h2: ties_seen += 1
        if not is_stable(g, s):
            bad12.append((g, s))
chk("P1.2 greedy stable on 12,000 (matrix, tie-break) pairs, n<=7 k<=3", not bad12,
    f"instances with a tied round argmax: {ties_seen}/{tot}")

# adversarial: all-equal matrix (maximal ties)
for n, k in [(3,3),(5,3),(2,2),(1,1)]:
    g = [[7]*k for _ in range(n)]
    ok = all(is_stable(g, s) for s in injections(n, k))   # everything is stable
    sg, _, h2 = greedy(g)
    chk(f"P1.2 all-ties {n}x{k}: greedy stable (and H2 fails as expected)", is_stable(g, sg) and ok and (not h2 or (n==k==1)))

# ---------------- P1.3: H2 => |stable set| == 1 == {greedy}
n_h2, bad13 = 0, []
h2fail_multi, h2fail_tot = 0, 0
for trial in range(4000):
    n = rng.randint(1, 7); k = rng.randint(1, min(3, n))
    hi = rng.choice([3, 6, 40])
    g = [[rng.randint(1, hi) for _ in range(k)] for _ in range(n)]
    s, rounds, h2 = greedy(g)
    S = stable_set(g)
    if h2:
        n_h2 += 1
        if S != [s]:
            bad13.append((g, s, S))
    else:
        h2fail_tot += 1
        if len(S) > 1: h2fail_multi += 1
chk(f"P1.3 H2 holds => stable set == {{greedy}} ({n_h2} instances)", not bad13,
    bad13[:1])
chk("P1.3 attack: H2 violated => multiplicity is possible (hypothesis is load-bearing)",
    h2fail_multi > 0, f"{h2fail_multi}/{h2fail_tot} H2-failing instances have |stable set|>1")

# explicit constructed H2 violation
g = [[5, 5], [5, 3], [1, 1]]     # round-1 argmax tied at 3 cells
S = stable_set(g)
chk("P1.3 constructed tie instance has |stable set| > 1", len(S) > 1, f"|S|={len(S)}: {S}")

# ---------------- P1.3 step: no stable matching leaves a district unstaffed (uses H1)
bad_partial = []
for trial in range(600):
    n = rng.randint(1, 5); k = rng.randint(1, min(3, n))
    g = [[rng.randint(1, 9) for _ in range(k)] for _ in range(n)]
    s, rounds, h2 = greedy(g)
    if not h2: continue
    St = [m for m in partial_matchings(n, k) if not blocking_partial(g, m)]
    if St != [s]:
        bad_partial.append((g, s, St))
chk("P1.3 over PARTIAL matchings (H1 on): stable set is still exactly {greedy}",
    not bad_partial, bad_partial[:1])

# attack: drop H1 (unmatched rep does NOT block; unstaffed district accepts nobody)
def blocking_noH1(g, sigma):
    mu = {i: j for j, i in enumerate(sigma) if i is not None}
    out = []
    for i in range(len(g)):
        for j in range(len(g[0])):
            if i not in mu: continue            # H1 dropped: unmatched reps never block
            if sigma[j] is None: continue
            if g[i][j] > g[i][mu[i]] and g[i][j] > g[sigma[j]][j]:
                out.append((i, j))
    return out
counter = None
for trial in range(400):
    n, k = 3, 2
    g = [[rng.randint(1, 9) for _ in range(k)] for _ in range(n)]
    s, rounds, h2 = greedy(g)
    if not h2: continue
    St = [m for m in partial_matchings(n, k) if not blocking_noH1(g, m)]
    if len(St) > 1:
        counter = (g, s, len(St)); break
chk("P1.3 attack: dropping H1 breaks uniqueness (empty matching becomes stable)",
    counter is not None, counter)

# ---------------- k > n is outside the claim (no injection exists)
chk("scope: k>n has no injection J->I, claim correctly restricted to k<=n",
    list(injections(2, 3)) == [])

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
