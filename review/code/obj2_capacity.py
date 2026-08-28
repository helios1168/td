"""
obj2_capacity.py -- the saturating-ceiling track of objection 2, the genuine new case.

f(y) = K*(1-exp(-y/K)) is NOT homogeneous, unlike the power-law track (obj2_power.py),
so a shared ceiling K does not obviously cancel out. Two tests:

  A. SYMMETRIC ceiling, Ka=Kb=K, swept from loose to tight. Does capacity alone --
     holding the ceiling equal between reps -- ever move the allocation?
  B. ASYMMETRIC ceiling tied to a defensible operational story: capacity scales with
     each rep's PRE-MERGER book (K_a = mult*S_a, K_b = mult*S_b), since a rep's existing
     book is the only real signal of their current servicing capacity in this data.
     Swept over `mult`, both directions checked because the review already learned
     (HANDOFF_REVIEW.md sec.4) that testing only one direction of an asymmetry produces
     an overstated or wrong conclusion.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from capacity import nash_exact_capacity, saturating_response

d = pickle.load(open("/tmp/z50.pkl", "rb"))
Az, Bz, Mz, th, lam = d["Az"], d["Bz"], d["Mz"], d["th"], d["lam"]
Sa, Sb = d["Sa"], d["Sb"]

base = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0.)
x_base = base["x"]; ya_base, yb_base = base["y_a"], base["y_b"]
print(f"no-capacity baseline (d=0): k={int(x_base.sum())}  y_a={ya_base:.4f}  y_b={yb_base:.4f}")
print(f"pre-merger books: S_a={Sa:.4f}  S_b={Sb:.4f}   "
      f"(y_a*/S_a = {ya_base/Sa:.3f}x,  y_b*/S_b = {yb_base/Sb:.3f}x)")

print()
print("=" * 82)
print("TEST A -- symmetric ceiling K_a = K_b = K, swept from loose to tight")
print("=" * 82)
print(f"  {'K':>8} {'K / y_a*':>10} {'K / y_b*':>10} {'k':>4} {'zips vs baseline':>18}")
for K in (100.0, 30.0, 15.0, 10.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0):
    resp = saturating_response(K)
    r = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0., resp, resp)
    if r["status"] != "optimal":
        print(f"  {K:>8.1f}  solver status={r['status']}"); continue
    dif = int((r["x"] != x_base).sum())
    print(f"  {K:>8.1f} {K/ya_base:>10.2f} {K/yb_base:>10.2f} {int(r['x'].sum()):>4} {dif:>18}")

print()
print("=" * 82)
print("TEST B -- asymmetric ceiling tied to pre-merger book: K_a=mult*S_a, K_b=mult*S_b")
print("(direction check: which rep's capacity binds first as mult shrinks?)")
print("=" * 82)
print(f"  mult needed for K_a to just clear y_a* (no bind): {ya_base/Sa:.3f}")
print(f"  mult needed for K_b to just clear y_b* (no bind): {yb_base/Sb:.3f}")
print()
print(f"  {'mult':>6} {'K_a':>7} {'K_b':>7} {'k':>4} {'y_a':>7} {'y_b':>7} "
      f"{'zips vs baseline':>18} {'binds harder on':>16}")
for mult in (10.0, 6.0, 5.0, 4.5, 4.0, 3.5, 3.0, 2.7, 2.5, 2.3, 2.0, 1.5, 1.0):
    Ka, Kb = mult * Sa, mult * Sb
    r = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0., saturating_response(Ka), saturating_response(Kb))
    if r["status"] != "optimal":
        print(f"  {mult:>6.2f}  solver status={r['status']}"); continue
    dif = int((r["x"] != x_base).sum())
    binds = "b" if Kb < yb_base and (Ka >= ya_base or (yb_base - Kb) > (ya_base - Ka)) else \
            ("a" if Ka < ya_base else "neither")
    print(f"  {mult:>6.2f} {Ka:>7.3f} {Kb:>7.3f} {int(r['x'].sum()):>4} {r['y_a']:>7.4f} {r['y_b']:>7.4f} "
          f"{dif:>18} {binds:>16}")

print()
print("=" * 82)
print("TEST B' -- reverse direction: capacity INVERSELY proportional to legacy book")
print("(the smaller pre-merger player already has slack; the larger one is stretched)")
print("=" * 82)
print(f"  {'mult':>6} {'K_a':>7} {'K_b':>7} {'k':>4} {'zips vs baseline':>18}")
for mult in (10.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.5, 1.0, 0.8):
    Ka, Kb = mult * Sb, mult * Sa     # swapped
    r = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0., saturating_response(Ka), saturating_response(Kb))
    if r["status"] != "optimal":
        print(f"  {mult:>6.2f}  solver status={r['status']}"); continue
    dif = int((r["x"] != x_base).sum())
    print(f"  {mult:>6.2f} {Ka:>7.3f} {Kb:>7.3f} {int(r['x'].sum()):>4} {dif:>18}")
