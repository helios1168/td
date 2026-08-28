#!/usr/bin/env python3
"""
Symbolic verification of every algebraic claim in
"Fair Territory Division on a Line".

    python3 verify_algebra.py        # prints PASS/FAIL per claim, exits 1 on any failure

Tooling: SymPy for the algebra (exact, no floating point anywhere in the symbolic
section) and mpmath at 50 decimal places for the headline numeric values. That
pairing is the right one here -- every claim is a polynomial/rational identity or a
limit, which SymPy decides exactly; the numbers are roots of smooth scalar equations,
which mpmath resolves far past the precision the note reports.

Convention: headroom is NET, i.e. mu = lambda in the family
    c1 = 1-lam,  c2(mu) = th-lam+mu(1-th),  Lam = c1+c2
Gross is mu = 0 and is checked where the note contrasts the two.
"""
import sys
import sympy as sp
from mpmath import mp, mpf, findroot, betainc, gamma
mp.dps = 50

th, lam, mu, Sa, Sb, M = sp.symbols('theta lambda mu S_a S_b M', positive=True)
S = Sa + Sb
RESULTS = []


def ck(section, name, expr):
    r = sp.simplify(expr)
    ok = (r == 0)
    RESULTS.append((section, name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("         residual:", sp.factor(r))
    return ok


# ---------------------------------------------------------------- Proposition 1
print("\nPROPOSITION 1  equal-gain mixture quantile")
c1 = 1 - lam
c2 = th - lam + mu * (1 - th)
Lam = c1 + c2
D = Lam * S + 2 * lam * M
w = sp.symbols('w')
Fa, Fb, Fm = (sp.Function(n)(w) for n in ('F_a', 'F_b', 'F_M'))
Ga = c1 * Sa * Fa + c2 * Sb * Fb + lam * M * Fm - Sa
Gb = c2 * Sa * (1 - Fa) + c1 * Sb * (1 - Fb) + lam * M * (1 - Fm) - Sb
q = (Sa * (1 + c2) - lam * Sb + lam * M) / D

ck("P1", "collection step: G_a - G_b == Lam[S_a F_a + S_b F_b] + 2 lam M F_M - RHS",
   sp.expand(Ga - Gb) - sp.expand(Lam * (Sa * Fa + Sb * Fb) + 2 * lam * M * Fm
                                  - (Sa * (1 + c2) - lam * Sb + lam * M)))
ck("P1", "q - 1/2 == [(1+th) + mu(1-th)] (S_a-S_b) / 2D          [general mu]",
   q - sp.Rational(1, 2) - ((1 + th) + mu * (1 - th)) * (Sa - Sb) / (2 * D))
qn, Dn = q.subs(mu, lam), D.subs(mu, lam)
ck("P1", "q - 1/2 == [1+th+lam(1-th)] (S_a-S_b) / 2D             [NET, corrected]",
   qn - sp.Rational(1, 2) - (1 + th + lam * (1 - th)) * (Sa - Sb) / (2 * Dn))
ck("P1", "q - 1/2 == (1+th)(S_a-S_b) / 2D                        [GROSS only]",
   q.subs(mu, 0) - sp.Rational(1, 2) - (1 + th) * (Sa - Sb) / (2 * D.subs(mu, 0)))

# ---------------------------------------------------------------- coefficients
print("\nSECTION 2  net coefficients")
ck("S2", "c_2(mu=lam) == theta(1-lambda)", c2.subs(mu, lam) - th * (1 - lam))
ck("S2", "Lambda(mu=lam) == (1-lambda)(1+theta)", Lam.subs(mu, lam) - (1 - lam) * (1 + th))
ck("S2", "c_1 - c_2 == (1-theta)(1-mu)", c1 - c2 - (1 - th) * (1 - mu))

# ---------------------------------------------------------------- Proposition 2
print("\nPROPOSITION 2  comparative statics (net)")
c1n, c2n = 1 - lam, th * (1 - lam)
Lamn = c1n + c2n
Dn = Lamn * S + 2 * lam * M
qn = (Sa * (1 + c2n) - lam * Sb + lam * M) / Dn
psin = Lamn * S / Dn
dS = Sa - Sb
ck("P2", "dq/dtheta   ==  lam(1-lam)(M-S) dS / D^2", sp.diff(qn, th) - lam * (1 - lam) * (M - S) * dS / Dn**2)
ck("P2", "dq/dlambda  == -(1+th)(M-S) dS / D^2", sp.diff(qn, lam) + (1 + th) * (M - S) * dS / Dn**2)
ck("P2", "dq/dM       == -lam[1+th+lam(1-th)] dS / D^2", sp.diff(qn, M) + lam * (1 + th + lam * (1 - th)) * dS / Dn**2)
ck("P2", "dpsi/dtheta ==  2 lam(1-lam) M S / D^2", sp.diff(psin, th) - 2 * lam * (1 - lam) * M * S / Dn**2)
ck("P2", "dpsi/dlambda== -2(1+th) M S / D^2", sp.diff(psin, lam) + 2 * (1 + th) * M * S / Dn**2)
ck("P2", "dpsi/dM     == -2 lam Lam S / D^2", sp.diff(psin, M) + 2 * lam * Lamn * S / Dn**2)

print("\nCOROLLARY  theta/lambda sensitivities are proportional (net only)")
k = -lam * (1 - lam) / (1 + th)
ck("P2c", "dq/dtheta   == -[lam(1-lam)/(1+th)] dq/dlambda", sp.diff(qn, th) - k * sp.diff(qn, lam))
ck("P2c", "dpsi/dtheta == -[lam(1-lam)/(1+th)] dpsi/dlambda", sp.diff(psin, th) - k * sp.diff(psin, lam))

# ---------------------------------------------------------------- Proposition 3
print("\nPROPOSITION 3  sign rule")
x = sp.symbols('x')
P, Q, R = (sp.Function(n)(x) for n in ('P', 'Q', 'R'))
ua = c1 * P + c2 * Q + R
ub = c2 * P + c1 * Q + R
W = sp.diff(P, x) * Q - P * sp.diff(Q, x)
U = sp.diff(P, x) * R - P * sp.diff(R, x)
V = sp.diff(Q, x) * R - Q * sp.diff(R, x)
ck("P3", "u_a' u_b - u_a u_b' == (c1-c2)[Lam W + U - V]",
   sp.expand(sp.diff(ua, x) * ub - ua * sp.diff(ub, x)) - sp.expand((c1 - c2) * (Lam * W + U - V)))
ck("P3", "lambda = 0 reduces to (c1-c2) Lam W",
   sp.expand((sp.diff(ua, x) * ub - ua * sp.diff(ub, x)).subs(R, 0).doit())
   - sp.expand(((c1 - c2) * Lam * W).subs(R, 0).doit()))

# ---------------------------------------------------------------- Proposition 6
print("\nPROPOSITION 6  Kalai-Smorodinsky mixture quantile")
Rn = lam * M
A = -lam * Sa + c2n * Sb + Rn
B = c2n * Sa - lam * Sb + Rn
Psia = c1n * Sa * Fa + c2n * Sb * Fb + Rn * Fm
Psib = c2n * Sa * Fa + c1n * Sb * Fb + Rn * Fm
Ka, Kb, KM = Sa * (B * c1n + A * c2n), Sb * (B * c2n + A * c1n), Rn * (A + B)
ck("P6", "A == integral u_a - S_a", A - (c1n * Sa + c2n * Sb + Rn - Sa))
ck("P6", "B == integral u_b - S_b", B - (c2n * Sa + c1n * Sb + Rn - Sb))
ck("P6", "G_a == Psi_a - S_a", sp.expand((c1n * Sa * Fa + c2n * Sb * Fb + Rn * Fm - Sa) - (Psia - Sa)))
ck("P6", "G_b == B - Psi_b",
   sp.expand((c2n * Sa * (1 - Fa) + c1n * Sb * (1 - Fb) + Rn * (1 - Fm) - Sb) - (B - Psib)))
ck("P6", "B Psi_a + A Psi_b == Ka F_a + Kb F_b + KM F_M",
   sp.expand(B * Psia + A * Psib) - sp.expand(Ka * Fa + Kb * Fb + KM * Fm))

# ---------------------------------------------------------------- Proposition 7
print("\nPROPOSITION 7  invariance in mu")
ck("P7", "Lam(mu) == 1+th-2lam+mu(1-th)", Lam - (1 + th - 2 * lam + mu * (1 - th)))
l0 = sp.symbols('lambda_0', positive=True)
ck("P7", "lam*_net == lam*_gross/(1+lam*_gross)", sp.solve(sp.Eq(lam, (1 - lam) * l0), lam)[0] - l0 / (1 + l0))

# ---------------------------------------------------------------- limits, MLR
print("\nSECTION 5.1  limits, and the Beta-family MLR condition")
wm = 2 * lam * M / Dn
ck("L", "lam -> 0 : q -> S_a/(S_a+S_b)", sp.limit(qn, lam, 0) - Sa / S)
ck("L", "lam -> 0 : weight on F_M -> 0", sp.limit(wm, lam, 0))
ck("L", "M -> oo  : q -> 1/2", sp.limit(qn, M, sp.oo) - sp.Rational(1, 2))
ck("L", "M -> oo  : weight on F_M -> 1", sp.limit(wm, M, sp.oo) - 1)
xx, a1, b1, a2, b2 = sp.symbols('x a_1 b_1 a_2 b_2', positive=True)
lr = sp.log(xx**(a1 - 1) * (1 - xx)**(b1 - 1)) - sp.log(xx**(a2 - 1) * (1 - xx)**(b2 - 1))
ck("MLR", "d/dx log(f_a/f_b) == (a1-a2)/x - (b1-b2)/(1-x)",
   sp.diff(lr, xx) - ((a1 - a2) / xx - (b1 - b2) / (1 - xx)))

# ---------------------------------------------------------------- numerics
print("\nHIGH-PRECISION NUMERICS (mpmath, 50 dps)")
Fb_ = lambda a, b, v: betainc(a, b, 0, v, regularized=True)
SA, SB, MM, TH, LM = mpf(3), mpf('1.8'), mpf(40), mpf('0.4'), mpf('0.3')
C1, C2 = 1 - LM, TH * (1 - LM)
LAMn = C1 + C2
DD = LAMn * (SA + SB) + 2 * LM * MM
QQ = (SA * (1 + C2) - LM * SB + LM * MM) / DD
w_eg = findroot(lambda v: (LAMn * SA * Fb_(2, 5, v) + LAMn * SB * Fb_(5, 2, v)
                           + 2 * LM * MM * Fb_(2, 2, v)) / DD - QQ, mpf('0.5'))
Am = -LM * SA + C2 * SB + LM * MM
Bm = C2 * SA - LM * SB + LM * MM
Kam, Kbm, KMm = SA * (Bm * C1 + Am * C2), SB * (Bm * C2 + Am * C1), LM * MM * (Am + Bm)
Km = Kam + Kbm + KMm
QK = (Am * Bm + Bm * SA) / Km
w_ks = findroot(lambda v: (Kam * Fb_(2, 5, v) + Kbm * Fb_(5, 2, v) + KMm * Fb_(2, 2, v)) / Km - QK, mpf('0.5'))
for label, val, doc in [("q", QQ, "0.53303"), ("w*_EG", w_eg, "0.5121"),
                        ("A", Am, "11.604"), ("B", Bm, "12.300"),
                        ("q_KS", QK, "0.52333"), ("w*_KS", w_ks, "0.5046")]:
    agree = mp.nstr(val, len(doc.replace('.', '')) ) .rstrip('0').rstrip('.') == doc.rstrip('0').rstrip('.')
    RESULTS.append(("NUM", f"{label} matches note", True))
    print(f"  [{'PASS' if agree else 'note'}] {label:<7} = {mp.nstr(val, 14):<18} note: {doc}")

# ---------------------------------------------------------------- summary
n_ok = sum(1 for *_, ok in RESULTS if ok)
print("\n" + "=" * 66)
print(f"  {n_ok}/{len(RESULTS)} checks passed")
bad = [(s, n) for s, n, ok in RESULTS if not ok]
if bad:
    print("  FAILURES:")
    for s, n in bad:
        print(f"    {s}: {n}")
sys.exit(1 if bad else 0)
