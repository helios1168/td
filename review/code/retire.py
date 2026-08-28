import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from dzero import nash_exact_d
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz,th,lam=d["Az"],d["Bz"],d["Mz"],d["th"],d["lam"]
c1,c2=1-lam,th*(1-lam)
ua,ub=c1*Az+c2*Bz+lam*Mz, c2*Az+c1*Bz+lam*Mz
Sa,Sb=Az.sum(),Bz.sum()

r1=nash_exact_d(Az,Bz,Mz,th,lam)            # d=(Sa,Sb)
r0=nash_exact_d(Az,Bz,Mz,th,lam,0.,0.)      # d=(0,0)  -> MNW
x1,x0=r1["x"],r0["x"]
moved=(x1!=x0)
print("="*74)
print("RETIREMENT CONDITION: re-solve with d=(0,0), count zips that move")
print("="*74)
print(f"  d=(Sa,Sb): k={x1.sum():>3}  g_a={r1['g_a']:.4f}  g_b={r1['g_b']:.4f}  prod={r1['product']:.5f}")
print(f"  d=(0,0)  : k={x0.sum():>3}  U_a={ua[x0].sum():.4f}  U_b={ub[~x0].sum():.4f}  prod={ua[x0].sum()*ub[~x0].sum():.5f}")
print(f"\n  ZIPS MOVED: {moved.sum()} of 50   ({100*moved.sum()/50:.0f}%)")
print(f"  threshold in the retirement condition was <= 1 zip -> {'COSMETIC' if moved.sum()<=1 else 'NOT COSMETIC'}")
print(f"  direction: {(x0&~x1).sum()} zips move TO a,  {(x1&~x0).sum()} move TO b")

# who wins/loses, in true utility
print(f"\n  a's true bundle utility: d=(Sa,Sb) {ua[x1].sum():.4f}  ->  d=0 {ua[x0].sum():.4f}  ({100*(ua[x0].sum()-ua[x1].sum())/ua[x1].sum():+.2f}%)")
print(f"  b's true bundle utility: d=(Sa,Sb) {ub[~x1].sum():.4f}  ->  d=0 {ub[~x0].sum():.4f}  ({100*(ub[~x0].sum()-ub[~x1].sum())/ub[~x1].sum():+.2f}%)")
print(f"  opportunity share to a : d=(Sa,Sb) {100*Mz[x1].sum()/Mz.sum():.1f}%  ->  d=0 {100*Mz[x0].sum()/Mz.sum():.1f}%")

# EF1 on both
def ef1(x):
    oa,ta=ua[x].sum(),ua[~x].sum()
    ob,tb=ub[~x].sum(),ub[x].sum()
    ga=ta-(ua[~x].max() if (~x).any() else 0)-oa
    gb=tb-(ub[x].max() if x.any() else 0)-ob
    return ga<=1e-12 and gb<=1e-12, max(ga,gb)
for nm,x in [("d=(Sa,Sb)",x1),("d=(0,0)  ",x0)]:
    ok,g=ef1(x); print(f"  EF1 {nm}: {'HOLDS' if ok else 'FAILS'}   (residual envy {g:+.4f})")

# is the d=0 allocation still good under the d=(Sa,Sb) objective, and vice versa?
p_cross=(ua[x0].sum()-Sa)*(ub[~x0].sum()-Sb)
print(f"\n  cost of using the d=0 map, scored on the d=(Sa,Sb) objective:")
print(f"    {p_cross:.5f} vs optimum {r1['product']:.5f}  ({100*(p_cross-r1['product'])/r1['product']:+.3f}%)")
np.save("/tmp/x1.npy",x1); np.save("/tmp/x0.npy",x0)
