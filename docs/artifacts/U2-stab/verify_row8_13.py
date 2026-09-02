"""Row 8 / P2.6 (P2.5 fails at n>=3) and Row 13 (w*tau/(c2*tau+lam) = 0.4217 vs FRAME 0.42).

Row 8: the recorded 3x3 witness re-checked over all 6 permutations by hand-checkable
integer arithmetic, independently of stab.py.  Row 13: exact rational recomputation in sympy.
"""
import sys, itertools, random
from fractions import Fraction
import sympy as sp
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import greedy, blocking_pairs, is_stable, maxweight, injections

FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

# =============================== ROW 8 / P2.6 ===============================
G = [[2638, 3920, 2123],
     [3750,  368, 6698],
     [ 406, 5843, 7243]]
print("all 6 injections of the recorded 3x3 witness (sigma[j] = rep for district j):")
rows = []
for s in injections(3, 3):
    tot = G[s[0]][0] + G[s[1]][1] + G[s[2]][2]
    pr = G[s[0]][0] * G[s[1]][1] * G[s[2]][2]
    rows.append((s, tot, pr, blocking_pairs(G, s)))
    print(f"  sigma={s}  sum={tot:6d}  product={pr:>16d}  blocking={blocking_pairs(G, s)}")
sg, rounds, h2 = greedy(G)
raw_arg = max(rows, key=lambda r: r[1])
log_arg = max(rows, key=lambda r: r[2])
chk("row8 H2 holds on the witness (unique argmax at each of 3 rounds)", h2, rounds)
chk("row8 greedy == (1,0,2)", sg == (1, 0, 2), sg)
chk("row8 log(product)-max roster == greedy", log_arg[0] == sg, log_arg[0])
chk("row8 raw(sum)-max roster == (0,2,1) != greedy", raw_arg[0] == (0, 2, 1) and raw_arg[0] != sg, raw_arg[0])
chk("row8 greedy sum 14913 = 3750+3920+7243", 3750+3920+7243 == 14913 and log_arg[1] == 14913, log_arg[1])
chk("row8 raw-optimal sum 15179 = 2638+5843+6698", 2638+5843+6698 == 15179 and raw_arg[1] == 15179, raw_arg[1])
chk("row8 sum strictly improves (15179 > 14913) while the product does NOT",
    raw_arg[1] > log_arg[1] and raw_arg[2] < log_arg[2], (raw_arg[2], log_arg[2]))
chk("row8 the LOG roster is stable", is_stable(G, log_arg[0]), blocking_pairs(G, log_arg[0]))
chk("row8 the RAW roster is unstable with blocking set {(2,2)}",
    blocking_pairs(G, raw_arg[0]) == [(2, 2)], blocking_pairs(G, raw_arg[0]))
chk("row8 uniqueness of both argmaxes (no ties)",
    sum(1 for r in rows if r[1] == raw_arg[1]) == 1 and sum(1 for r in rows if r[2] == log_arg[2]) == 1)
print("  => P2.5's contrapositive ('raw instability => log instability') FAILS here:"
      "\n     the raw roster is unstable, the log roster is stable.  P2.5 is a 2x2 artefact.")

# independent random search: P2.5 violations at n=3,4,5 with a different RNG family
def p25_violation(g):
    """greedy is the product-max roster but NOT a sum-max roster."""
    sg, _, h2 = greedy(g)
    if not h2: return False
    R, _ = maxweight(g, lambda x: Fraction(x))          # sum-max
    P, _ = maxweight(g, lambda x: Fraction(x))          # placeholder
    best_p = max(Fraction(1) if True else 0 for _ in [0])
    # exact: compare products and sums directly
    def sm(s): return sum(g[s[j]][j] for j in range(len(g[0])))
    def pm(s):
        v = 1
        for j in range(len(g[0])): v *= g[s[j]][j]
        return v
    allinj = list(injections(len(g), len(g[0])))
    if pm(sg) < max(pm(s) for s in allinj): return False   # greedy not product-max
    return sm(sg) < max(sm(s) for s in allinj)             # but not sum-max

rng = random.Random(1234567)          # different seed AND different draw shape than stab.py
counts = {}
for n in (3, 4, 5):
    v = 0
    for _ in range(20000):
        g = [[rng.randint(1, 10000) for _ in range(n)] for _ in range(n)]
        if p25_violation(g): v += 1
    counts[n] = v
chk("row8 independent search reproduces P2.5 violations at n=3,4,5 (rate ~1e-3)",
    all(counts[n] > 0 for n in counts), f"violations/20000: {counts}  "
    f"(stab.py: 151/191/140 per 133,333 -> rates "
    f"{151/133333:.2e}/{191/133333:.2e}/{140/133333:.2e}; here "
    + "/".join(f"{counts[n]/20000:.2e}" for n in (3,4,5)) + ")")
chk("row8 P2.5 has 0 violations at n=2 under the same generator (2x2 lemma still holds)",
    sum(p25_violation([[rng.randint(1,10000) for _ in range(2)] for _ in range(2)])
        for _ in range(20000)) == 0)

# =============================== ROW 13 ===============================
th, la, tau = sp.Rational(40, 100), sp.Rational(30, 100), sp.Rational(419, 1000)
c1 = 1 - la; c2 = th*(1 - la); w = c1 - c2
chk("row13 c1 = 0.70", c1 == sp.Rational(7, 10), c1)
chk("row13 c2 = 0.28", c2 == sp.Rational(28, 100), c2)
chk("row13 w = c1-c2 = (1-lam)(1-theta) = 0.42", w == sp.Rational(42, 100) and
    sp.simplify(w - (1-la)*(1-th)) == 0, w)
swing = w*tau/(c2*tau + la)
chk("row13 swing is the exact rational 8799/20866", sp.nsimplify(swing) == sp.Rational(8799, 20866),
    sp.nsimplify(swing))
chk("row13 swing rounds to 0.4217", round(float(swing), 4) == 0.4217, float(swing))
chk("row13 |swing - 0.42| = 0.0017 to 4 dp",
    round(abs(float(swing) - 0.42), 4) == 0.0017, abs(float(swing) - 0.42))
chk("row13 matches stab.py's recorded 0.4216907888430941 to 1e-15",
    abs(float(swing) - 0.4216907888430941) < 1e-15, float(swing))
# derivation check: swing = (u_hold - u_not)/u_not at t = T_z/M_z = tau
S_, M_ = sp.symbols("S M", positive=True)
u_hold = c1*tau + c2*0 + la          # rep holds the whole booked share tau
u_not  = c2*tau + la                 # rep holds none of it
chk("row13 swing == (u_hold - u_not)/u_not, the stated definition",
    sp.simplify((u_hold - u_not)/u_not - swing) == 0, sp.simplify((u_hold-u_not)/u_not))
# attack: does it survive the theta -> 1 degeneracy note?
chk("row13 attack: swing -> 0 as theta -> 1 (section 5 row 3's vacuity mode)",
    sp.limit(((1-la)*(1-sp.Symbol('t'))*tau)/(sp.Symbol('t')*(1-la)*tau + la), sp.Symbol('t'), 1) == 0)

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
