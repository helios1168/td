"""Row 6 / P3.1 (zero blocking <=> sigma^H = sigma^G) and P3.2 (the first-deviation greedy
pair blocks).  Brute force on toys; the first-deviation round is recomputed independently
and checked for membership in the enumerated blocking set."""
import sys, random, math
from fractions import Fraction
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import greedy, maxweight, blocking_pairs, is_stable, stable_set

FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

rng = random.Random(20260902)
PHI = {"log": lambda x: math.log(x), "raw": lambda x: Fraction(x),
       "sqrt": lambda x: math.sqrt(x), "cube": lambda x: Fraction(x)**3}

n31 = n32 = 0
bad31, bad32, bad32b = [], [], []
differ = 0
for _ in range(6000):
    n = rng.randint(1, 7); k = rng.randint(1, min(4, n))
    g = [[rng.randint(1, rng.choice([6, 20, 200])) for _ in range(k)] for _ in range(n)]
    sg, rounds, h2 = greedy(g)
    if not h2:
        continue          # H2 required by P3.1/P3.2
    n31 += 1
    for pname, phi in PHI.items():
        rosters, _ = maxweight(g, phi)
        for sh in rosters:
            # P3.1 (both directions)
            zero = not blocking_pairs(g, sh)
            if zero != (sh == sg):
                bad31.append((g, pname, sh, sg, zero))
            # P3.2
            if sh != sg:
                differ += 1
                # independently recompute the first greedy round where sigma^H deviates
                r = next(t for t, (i, j, _u) in enumerate(rounds) if sh[j] != i)
                ir, jr, _u = rounds[r]
                bp = blocking_pairs(g, sh)
                if (ir, jr) not in bp:
                    bad32.append((g, pname, sh, sg, r, (ir, jr), bp))
                # and check the doc's proof step: sigma^H agrees with greedy before r
                if any(sh[rounds[t][1]] != rounds[t][0] for t in range(r)):
                    bad32b.append((g, r))
chk(f"P3.1 zero blocking <=> sigma^H == sigma^G, over 4 phi, {n31} H2-instances",
    not bad31, bad31[:1])
chk(f"P3.2 first-deviation greedy pair is in the enumerated blocking set "
    f"({differ} deviating rosters)", not bad32, bad32[:1])
chk("P3.2 proof step: sigma^H agrees with greedy on rounds before the first deviation",
    not bad32b, bad32b[:1])
chk("P3.2 is non-vacuous (deviating rosters actually occur)", differ > 0, differ)

# P3.2 generalisation: the claim only needs sigma to agree with greedy on rounds < r,
# not that sigma is max-weight.  Test on ARBITRARY injections.
bad_gen = []
tested = 0
for _ in range(3000):
    n = rng.randint(2, 6); k = rng.randint(1, min(3, n))
    g = [[rng.randint(1, 30) for _ in range(k)] for _ in range(n)]
    sg, rounds, h2 = greedy(g)
    if not h2: continue
    from verify_core import injections
    for s in injections(n, k):
        if s == sg: continue
        r = next(t for t, (i, j, _u) in enumerate(rounds) if s[j] != i)
        if any(s[rounds[t][1]] != rounds[t][0] for t in range(r)):
            continue      # only meaningful when it agrees before r (it does, by construction of r)
        ir, jr, _ = rounds[r]
        tested += 1
        if (ir, jr) not in blocking_pairs(g, s):
            bad_gen.append((g, s, r, (ir, jr)))
chk(f"P3.2 holds for ANY injection deviating first at round r ({tested} cases)",
    not bad_gen, bad_gen[:1])

# attack: drop H2 -> P3.1 must be breakable
broke = None
for _ in range(20000):
    n = rng.randint(2, 5); k = rng.randint(2, min(3, n))
    g = [[rng.randint(1, 3) for _ in range(k)] for _ in range(n)]
    sg, rounds, h2 = greedy(g)
    if h2: continue
    for sh, _ in [maxweight(g, PHI["log"])]:
        for r in sh:
            if (not blocking_pairs(g, r)) != (r == sg):
                broke = (g, r, sg); break
        if broke: break
    if broke: break
chk("P3.1 attack: H2 is load-bearing (drop it and zero-blocking != greedy)",
    broke is not None, broke)

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
