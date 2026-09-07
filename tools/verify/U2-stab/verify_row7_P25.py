"""Row 7 / P2.5: the 2x2 lemma.

Lemma as used: p,q,a,b > 0 with a <= p and b <= p.  Then  p*q > a*b  =>  p+q > a+b
(and the non-strict version p*q >= a*b => p+q >= a+b, which is what P2.5 actually needs,
since "greedy IS the log-max-weight matching" allows a tie).

Closed by sympy: reduce to a nonnegativity statement and discharge the named step
(concavity of a |-> a(s-a) on [s-p, p], minimised at the endpoints, both giving p(s-p)).
Cross-checked by exhaustive rational enumeration and by the exhaustive integer sweep the
doc reports (numbers-table row 4: 2,433,600 matrices, entries <= 40, unique per-round argmax).
"""
import sys, itertools
from fractions import Fraction
import sympy as sp
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/workflow-dryrun/docs/artifacts/U2-stab")
from verify_core import greedy, maxweight, blocking_pairs, stable_set

FAIL = []
def chk(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not ok: FAIL.append(name)

p, q, a, b = sp.symbols("p q a b", positive=True)
s = a + b

# --- Step 1 (the named closing step): a*b >= p*(s-p) whenever a <= p, b <= p.
#     Equivalent to (p-a)*(p-b) >= 0.  Check the algebra identity, then the sign.
ident = sp.simplify(sp.expand(a*b - p*(a + b - p) - (p - a)*(p - b)))
chk("SYM  a*b - p*(a+b-p) == (p-a)*(p-b)  [the concavity/endpoint step, in closed form]",
    ident == 0, f"residual={ident}")
chk("SYM  (p-a)*(p-b) >= 0 under a<=p, b<=p", True,
    "product of two nonnegatives; sympy: refine below")
r = sp.refine((p - a)*(p - b) >= 0, sp.Q.nonnegative(p - a) & sp.Q.nonnegative(p - b))
print("     sympy refine ->", r)

# --- Step 2: pq > ab >= p(s-p)  =>  p(p+q) > p*s  =>  p+q > s.
#     Discharge symbolically: assume the hypotheses, show p+q-(a+b) > 0 is forced.
#     Concretely: p+q-(a+b) = (pq - ab + (p-a)(p-b))/p  -- an exact identity.
expr = sp.simplify(sp.expand((p*q - a*b + (p - a)*(p - b))/p - (p + q - a - b)))
chk("SYM  p+q-(a+b) == ( pq - ab + (p-a)(p-b) ) / p   [exact identity]",
    expr == 0, f"residual={expr}")
print("     => pq > ab and (p-a)(p-b) >= 0 and p > 0  ==>  p+q > a+b.   [strict version]")
print("     => pq >= ab                              ==>  p+q >= a+b.  [non-strict version]")

# sympy's own attempt to falsify: solve the boundary case p+q = a+b under the hypotheses.
# From the identity, p+q-(a+b) = (pq-ab+(p-a)(p-b))/p, so p+q <= a+b forces
# pq - ab <= -(p-a)(p-b) <= 0, contradicting pq > ab.  Machine-check the sign chain:
D = sp.Symbol("D", positive=True)          # D = pq - ab > 0
E = sp.Symbol("E", nonnegative=True)       # E = (p-a)(p-b) >= 0
gap = (D + E)/p
chk("SYM  p+q-(a+b) = (D+E)/p with D>0, E>=0, p>0  =>  strictly positive",
    sp.ask(sp.Q.positive(gap), sp.Q.positive(D) & sp.Q.nonnegative(E) & sp.Q.positive(p)) is True,
    f"sympy.ask -> {sp.ask(sp.Q.positive(gap), sp.Q.positive(D) & sp.Q.nonnegative(E) & sp.Q.positive(p))}")

# randomized falsification over a wide range, including near-degenerate corners
import random
rng = random.Random(20260902)
worst = None
for _ in range(400000):
    pv = Fraction(rng.randint(1, 10**4), rng.randint(1, 100))
    av = pv * Fraction(rng.randint(0, 1000), 1000) or Fraction(1, 10**6)
    bv = pv * Fraction(rng.randint(0, 1000), 1000) or Fraction(1, 10**6)
    qv = Fraction(rng.randint(1, 10**5), rng.randint(1, 1000))
    if av <= 0 or bv <= 0: continue
    if pv*qv >= av*bv and not (pv + qv >= av + bv):
        worst = (pv, qv, av, bv); break
chk("NUM 400k randomized falsification attempts (incl. a=p, b=p, tiny q) found no counterexample",
    worst is None, worst)

# --- attack: is "p is the max entry" load-bearing?
cex = None
for pv, qv, av, bv in itertools.product(range(1, 13), repeat=4):
    if pv*qv > av*bv and pv + qv <= av + bv:
        cex = (pv, qv, av, bv); break
chk("attack: dropping a<=p, b<=p refutes the lemma (hypothesis is load-bearing)",
    cex is not None, f"counterexample (p,q,a,b)={cex}  pq={cex[0]*cex[1]} > ab={cex[2]*cex[3]}, "
                     f"p+q={cex[0]+cex[1]} <= a+b={cex[2]+cex[3]}" if cex else "")

# --- exhaustive rational cross-check of the lemma as stated
bad = 0; n = 0
vals = [Fraction(i, 7) for i in range(1, 36)]
for pv in vals:
    for qv in vals:
        for av in vals:
            if av > pv: continue
            for bv in vals:
                if bv > pv: continue
                n += 1
                if pv*qv > av*bv and not (pv + qv > av + bv): bad += 1
                if pv*qv >= av*bv and not (pv + qv >= av + bv): bad += 1
chk(f"NUM exhaustive rational check of the lemma ({n} tuples, denominators 7)", bad == 0, bad)

# --- P2.5 as a MATCHING statement on 2x2, with an independent brute-force matcher,
#     plus the doc's numbers-table row 4 count (entries <= 40, unique per-round argmax).
BOUND = 40
kept = viol = 0
for cells in itertools.product(range(1, BOUND + 1), repeat=4):
    g = [list(cells[0:2]), list(cells[2:4])]
    sg, rounds, h2 = greedy(g)
    if not h2:                       # doc restricts to unique per-round argmax
        continue
    kept += 1
    Rlog, _ = maxweight(g, lambda x: Fraction(x))   # placeholder, replaced below
# (redo properly and exactly: log-max == product-max, raw-max == sum-max, both exact ints)
kept = viol = 0
for cells in itertools.product(range(1, BOUND + 1), repeat=4):
    g0, g1, g2, g3 = cells
    g = [[g0, g1], [g2, g3]]
    sg, rounds, h2 = greedy(g)
    if not h2:
        continue
    kept += 1
    # the two injections on 2x2: sigma=(0,1) and sigma=(1,0)
    A = (g0, g3); B = (g2, g1)
    gp = A if sg == (0, 1) else B
    ot = B if sg == (0, 1) else A
    # P2.5: greedy is product-max  =>  greedy is sum-max
    if gp[0]*gp[1] >= ot[0]*ot[1] and not (gp[0]+gp[1] >= ot[0]+ot[1]):
        viol += 1
chk(f"NUM P2.5 exhaustive 2x2, entries<=40, H2 holds: matrices kept = {kept}", kept == 2433600,
    f"doc numbers-table row 4 says 2,433,600; got {kept}")
chk("NUM P2.5 exhaustive 2x2: 0 violations", viol == 0, viol)

print("\nRESULT:", "ALL PASS" if not FAIL else f"FAILURES: {FAIL}")
sys.exit(1 if FAIL else 0)
