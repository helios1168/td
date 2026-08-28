"""
obj2_power.py -- the power-law ("elasticity") track of objection 2.

Claim to test: apply a concave power-law response f(y)=y**kappa to each rep's raw
pooled gain before maximising the product. Two questions:

  (1) If BOTH reps have the same capacity elasticity kappa_a=kappa_b=kappa, does the
      allocation ever move relative to plain maximum-Nash-welfare (kappa=1)?
  (2) If they differ, is that a new phenomenon, or does it collapse into ground the
      review already covered (asymmetric-Nash omega, omega.py)?
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle, sympy as sp
from capacity import nash_exact_capacity, power_response
from omega import asym_nash

d = pickle.load(open("/tmp/z50.pkl", "rb"))
Az, Bz, Mz, th, lam = d["Az"], d["Bz"], d["Mz"], d["th"], d["lam"]

print("=" * 78)
print("PART 1 -- symbolic: is symmetric kappa a no-op, exactly?")
print("=" * 78)
raw_a, raw_b, kap = sp.symbols("raw_a raw_b kappa", positive=True)
obj_plain = sp.log(raw_a) + sp.log(raw_b)
obj_power = sp.log(raw_a**kap) + sp.log(raw_b**kap)
diff = sp.simplify(obj_power - kap * obj_plain)
print(f"  log(raw_a^kappa) + log(raw_b^kappa) - kappa*(log(raw_a)+log(raw_b)) = {diff}")
print("  -> the power-response objective is EXACTLY kappa times the plain objective,")
print("     for every (raw_a, raw_b). A positive scalar multiple of an objective never")
print("     changes its argmax. This holds allocation-by-allocation, not just at the")
print("     optimum, so no search over x is needed to know the argmax is unchanged.")

print()
print("=" * 78)
print("PART 2 -- numeric: confirm on the 50-zip instance, several kappa")
print("=" * 78)
x_plain = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0.)["x"]
print(f"  kappa=1.0 (plain) baseline: k={int(x_plain.sum())}")
for kappa in (0.15, 0.30, 0.50, 0.70, 0.90, 1.0):
    resp = power_response(kappa)
    r = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0., resp, resp)
    dif = int((r["x"] != x_plain).sum())
    print(f"  kappa={kappa:.2f}  k={int(r['x'].sum()):>2}  zips differing from baseline: {dif}")

print()
print("=" * 78)
print("PART 3 -- asymmetric kappa: identical to omega.py's asymmetric-Nash weight?")
print("=" * 78)
print(f"  {'kappa_a':>8} {'kappa_b':>8} {'implied omega':>14} {'k (power)':>10} "
      f"{'k (asym_nash)':>14} {'zips differing':>15}")
for ka, kb in [(0.6, 0.6), (0.7, 0.4), (0.4, 0.7), (0.9, 0.3), (0.3, 0.9), (0.55, 0.45)]:
    om = ka / (ka + kb)
    r_pow = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0., power_response(ka), power_response(kb))
    x_om = asym_nash(Az, Bz, Mz, th, lam, om)
    dif = int((r_pow["x"] != x_om).sum())
    print(f"  {ka:>8.2f} {kb:>8.2f} {om:>14.4f} {int(r_pow['x'].sum()):>10} "
          f"{int(x_om.sum()):>14} {dif:>15}")

print()
print("=" * 78)
print("PART 4 -- how much kappa-asymmetry before the allocation moves >1 zip?")
print("(mirrors HANDOFF_REVIEW.md's omega sweep: 0.48-0.52 clears EF1, 0.54 does not)")
print("=" * 78)
for ratio in (1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.50, 2.00):
    ka, kb = ratio, 1.0
    om = ka / (ka + kb)
    r = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0., power_response(ka), power_response(kb))
    dif = int((r["x"] != x_plain).sum())
    print(f"  kappa_a/kappa_b={ratio:.2f}  (omega={om:.4f})  k={int(r['x'].sum()):>2}  "
          f"zips vs symmetric baseline: {dif}")
