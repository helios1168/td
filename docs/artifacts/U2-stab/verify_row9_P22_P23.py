"""Row 9 / P2.2 and P2.3: minimality of the 2x2 witnesses (max entry 4, 5, 5).

Independent exhaustive enumeration with a brute-force matcher (verify_core), never scipy.
Exact integer/Fraction arithmetic; log-max-weight == product-max, done on ints.
"""
import sys, itertools
from fractions import Fraction
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import greedy, blocking_pairs

FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

def analyse(g):
    """Return (sigma_greedy, h2, sum/prod of both injections)."""
    sg, rounds, h2 = greedy(g)
    d = (g[0][0], g[1][1])          # sigma = (0,1)
    o = (g[1][0], g[0][1])          # sigma = (1,0)
    return sg, h2, d, o

def sep_log(g):
    """greedy != the unique log(product)-max roster (strict separation)."""
    sg, h2, d, o = analyse(g)
    pg, po = (d if sg == (0, 1) else o), (o if sg == (0, 1) else d)
    return pg[0]*pg[1] < po[0]*po[1]

def sep_raw(g):
    sg, h2, d, o = analyse(g)
    pg, po = (d if sg == (0, 1) else o), (o if sg == (0, 1) else d)
    return pg[0]+pg[1] < po[0]+po[1]

def mats_distinct(bound):
    for cells in itertools.permutations(range(1, bound + 1), 4):
        if max(cells) != bound: continue
        yield [list(cells[0:2]), list(cells[2:4])]

def mats_all(bound):
    for cells in itertools.product(range(1, bound + 1), repeat=4):
        if max(cells) != bound: continue
        yield [list(cells[0:2]), list(cells[2:4])]

# ---------------- P2.2a: log separation, four DISTINCT positive integers
first = {}
for B in range(1, 8):
    hits = [g for g in mats_distinct(B) if sep_log(g)]
    if hits and 'log' not in first:
        first['log'] = (B, len(hits), hits[0],
                        len([g for g in itertools.permutations(range(1, B+1), 4)]))
    print(f"  distinct-int, max entry {B}: arrangements={len(list(mats_distinct(B)))}, log-separating={len(hits)}")
B, cnt, w, _ = first['log']
chk("P2.2a minimal max entry for log separation (distinct ints) is 4", B == 4, B)
chk("P2.2a count is 8 of 24 arrangements", cnt == 8 and len(list(mats_distinct(4))) == 24,
    f"{cnt} of {len(list(mats_distinct(4)))}")
chk("P2.2a first witness is [[1,2],[3,4]]", w == [[1, 2], [3, 4]], w)
g = [[1, 2], [3, 4]]
sg, h2, d, o = analyse(g)
pg = d if sg == (0, 1) else o; po = o if sg == (0, 1) else d
chk("P2.2a witness: greedy product 4, log-optimum 6", pg[0]*pg[1] == 4 and po[0]*po[1] == 6,
    f"{pg[0]*pg[1]} vs {po[0]*po[1]}")
sl = (1, 0) if sg == (0, 1) else (0, 1)
chk("P2.2a witness: blocking pair of the log roster is (1,1)",
    blocking_pairs(g, sl) == [(1, 1)], blocking_pairs(g, sl))
print("  NOTE: 4 distinct positive integers force max entry >= 4, so 'minimal max entry 4'"
      "\n        is true but carries no content beyond the distinctness hypothesis.")

# ---------------- P2.2b: STRICT raw separation
res = {}
for B in range(1, 9):
    hd = [g for g in mats_distinct(B) if sep_raw(g)]
    ha = [g for g in mats_all(B) if sep_raw(g) and greedy(g)[2]]     # H2 holds
    res[B] = (hd, ha)
    print(f"  max entry {B}: raw-separating distinct={len(hd)}  all-with-H2={len(ha)}")
Bd = min(b for b in res if res[b][0])
Ba = min(b for b in res if res[b][1])
chk("P2.2b minimal max entry for strict raw separation (distinct ints) is 5", Bd == 5, Bd)
chk("P2.2b 8 witnesses at max entry 5 (distinct ints)", len(res[5][0]) == 8, len(res[5][0]))
chk("P2.2b first witness [[1,3],[4,5]]", res[5][0][0] == [[1, 3], [4, 5]], res[5][0][0])
g = [[1, 3], [4, 5]]; sg, h2, d, o = analyse(g)
pg = d if sg == (0, 1) else o; po = o if sg == (0, 1) else d
chk("P2.2b witness: greedy sum 6, raw optimum 7", pg[0]+pg[1] == 6 and po[0]+po[1] == 7,
    f"{pg[0]+pg[1]} vs {po[0]+po[1]}")
# SCOPE PROBE (not part of P2.2): P2.2's "distinct positive integers" hypothesis is
# load-bearing for the raw claim.  Without it, strict raw separation already occurs at
# max entry 4 -- [[1,3],[3,4]] and its 3 symmetries, greedy sum 5 vs raw optimum 6, all
# with a repeated entry 3.  P2.2 states the claim under distinctness, so this is a scope
# note, not a counterexample.
chk("SCOPE probe: without distinctness the raw threshold drops to 4 (documented caveat)",
    Ba == 4, f"minimal max entry without distinctness = {Ba}; "
             f"witnesses = {[g for g in mats_all(4) if sep_raw(g) and greedy(g)[2]]}")

# ---------------- P2.3: raw roster stable, log roster unstable
def p23(g):
    sg, h2, d, o = analyse(g)
    if not h2: return False
    other = (1, 0) if sg == (0, 1) else (0, 1)
    pg = d if sg == (0, 1) else o; po = o if sg == (0, 1) else d
    raw_is_greedy = pg[0]+pg[1] > po[0]+po[1]
    log_is_other  = pg[0]*pg[1] < po[0]*po[1]
    if not (raw_is_greedy and log_is_other): return False
    return (not blocking_pairs(g, sg)) and bool(blocking_pairs(g, other))
out = {}
for B in range(1, 9):
    hd = [g for g in mats_distinct(B) if p23(g)]
    ha = [g for g in mats_all(B) if p23(g)]
    out[B] = (hd, ha)
    print(f"  max entry {B}: P2.3 witnesses distinct={len(hd)}  all={len(ha)}")
Bp = min(b for b in out if out[b][1])
chk("P2.3 minimal max entry is 5", Bp == 5, Bp)
chk("P2.3 8 witnesses at max entry 5", len(out[5][1]) == 8, len(out[5][1]))
chk("P2.3 first witness [[1,2],[3,5]]", out[5][1][0] == [[1, 2], [3, 5]], out[5][1][0])
g = [[1, 2], [3, 5]]; sg, h2, d, o = analyse(g)
pg = d if sg == (0, 1) else o; po = o if sg == (0, 1) else d
other = (1, 0) if sg == (0, 1) else (0, 1)
chk("P2.3 witness: raw sums 6 > 5", (pg[0]+pg[1], po[0]+po[1]) == (6, 5), (pg[0]+pg[1], po[0]+po[1]))
chk("P2.3 witness: products 5 < 6", (pg[0]*pg[1], po[0]*po[1]) == (5, 6), (pg[0]*pg[1], po[0]*po[1]))
chk("P2.3 witness: 0 blocking pairs raw, 1 log = [(1,1)]",
    blocking_pairs(g, sg) == [] and blocking_pairs(g, other) == [(1, 1)],
    (blocking_pairs(g, sg), blocking_pairs(g, other)))

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
