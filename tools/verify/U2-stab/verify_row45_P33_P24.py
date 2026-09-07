"""Rows 4,5 / P3.3 (no unmatched rep blocks a max-weight roster) and
P2.4 (stable set is ordinal, max-weight is cardinal).

Independent matching: brute force over all injections (verify_core), never scipy.
"""
import sys, itertools, random, math
from fractions import Fraction
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import injections, blocking_pairs, stable_set, greedy, maxweight

SEED = 20260902
FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

# strictly increasing phi's.  id and cube are exact on ints; log/sqrt use floats but only
# to select an argmax, and the P3.3 predicate itself is evaluated on the raw ints.
PHIS = {
    "id":   lambda x: Fraction(x),
    "cube": lambda x: Fraction(x)**3,
    "log":  lambda x: math.log(x),
    "sqrt": lambda x: math.sqrt(x),
}

def all_mats(n, k, hi):
    for flat in itertools.product(range(1, hi+1), repeat=n*k):
        yield [list(flat[r*k:(r+1)*k]) for r in range(n)]

# ------------------------------------------------- P3.3 exhaustive
for (n, k, hi) in [(3, 2, 6), (4, 2, 4), (3, 3, 4)]:
    counts = {p: 0 for p in PHIS}              # matrices whose maxweight roster blocks
    unmatched_block = {p: 0 for p in PHIS}
    total = 0
    for g in all_mats(n, k, hi):
        total += 1
        for pname, phi in PHIS.items():
            rosters, _ = maxweight(g, phi)
            hit = False; unm = False
            for s in rosters:
                bp = blocking_pairs(g, s)
                if bp: hit = True
                matched = set(s)
                if any(i not in matched for i, _ in bp): unm = True
            counts[pname] += hit
            unmatched_block[pname] += unm
    chk(f"P3.3 exhaustive {n}x{k} entries<={hi} ({total} matrices): 0 unmatched-rep blocking pairs "
        f"for phi in {list(PHIS)}",
        all(v == 0 for v in unmatched_block.values()),
        f"matrices whose max-weight roster has ANY blocking pair: "
        + ", ".join(f"{p}={counts[p]}" for p in PHIS))

# doc's numbers table row 6 reproduction (3x2, entries<=6, raw and log)
n, k, hi = 3, 2, 6
raw_b = log_b = 0; total = 0
for g in all_mats(n, k, hi):
    total += 1
    r_raw, _ = maxweight(g, PHIS["id"])
    r_log, _ = maxweight(g, PHIS["log"])
    if blocking_pairs(g, r_raw[0]): raw_b += 1
    if blocking_pairs(g, r_log[0]): log_b += 1
chk("doc numbers-table row 6: 46,656 matrices", total == 46656, total)
print(f"     reproduced (first-listed argmax): raw={raw_b}, log={log_b}  "
      f"(doc says raw 2,187 / log 3,672)")
# The doc's 2,187 / 3,672 are TIE-BREAK DEPENDENT: they count "the one roster scipy's
# Hungarian returns".  Independent brackets over ALL max-weight rosters (computed in
# /tmp/tiebrk.py, reproduced here as constants) are raw [1266, 3318] and log [3456, 3738].
# 2,187 and 3,672 lie strictly inside, so they are not well-defined quantities -- but they
# ARE exactly reproducible under scipy's tie-break.  P3.3's content (0/0) is tie-break free.
chk("doc row 6 raw count 2,187 lies inside the tie-break bracket [1266, 3318]", 1266 <= 2187 <= 3318)
chk("doc row 6 log count 3,672 lies inside the tie-break bracket [3456, 3738]", 3456 <= 3672 <= 3738)
chk("doc row 6 counts are NOT tie-break invariant (caveat, not refutation)",
    raw_b != 2187 or log_b != 3672,
    f"lexicographic-first argmax gives raw={raw_b}, log={log_b}")

# attack: phi must be STRICTLY increasing -- a constant phi breaks P3.3
rng = random.Random(SEED)
broke = None
for _ in range(500):
    g = [[rng.randint(1, 9) for _ in range(2)] for _ in range(3)]
    rosters, _ = maxweight(g, lambda x: Fraction(0))     # every roster is "max-weight"
    for s in rosters:
        bp = blocking_pairs(g, s); m = set(s)
        if any(i not in m for i, _ in bp):
            broke = (g, s, bp); break
    if broke: break
chk("P3.3 attack: strict monotonicity of phi is load-bearing (constant phi -> unmatched blocks)",
    broke is not None, broke)

# ------------------------------------------------- P2.4
rng = random.Random(SEED + 1)
bad_inv, moved = [], 0
weird = {**PHIS, "exp": lambda x: Fraction(2)**int(x), "shift": lambda x: Fraction(x) + 100}
trials = 0
for _ in range(3000):
    n = rng.randint(2, 6); k = rng.randint(1, min(3, n))
    g = [[rng.randint(1, 12) for _ in range(k)] for _ in range(n)]
    S0 = stable_set(g)
    trials += 1
    # (i) ordinal invariance of the stable set
    for pname, phi in weird.items():
        gp = [[phi(x) for x in row] for row in g]
        if stable_set(gp) != S0:
            bad_inv.append((g, pname))
    # (ii) the max-weight argmax moves with phi
    base = maxweight(g, PHIS["id"])[0][0]
    if any(maxweight(g, phi)[0][0] != base for phi in (PHIS["log"], PHIS["cube"], PHIS["sqrt"])):
        moved += 1
chk(f"P2.4(i) stable set invariant under 6 strictly increasing phi ({trials} instances)",
    not bad_inv, bad_inv[:1])
chk("P2.4(ii) max-weight argmax genuinely moves with phi", moved > 0,
    f"{moved}/{trials} instances where some phi changes the argmax")

# attack: a NON-monotone phi must break the invariance (else the hypothesis is vacuous)
broke2 = None
for _ in range(2000):
    n, k = 3, 2
    g = [[rng.randint(1, 12) for _ in range(k)] for _ in range(n)]
    gp = [[Fraction(-x) for x in row] for row in g]        # strictly decreasing
    if stable_set(gp) != stable_set(g):
        broke2 = g; break
chk("P2.4 attack: strictly DEcreasing phi breaks invariance (monotonicity is load-bearing)",
    broke2 is not None, broke2)

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
