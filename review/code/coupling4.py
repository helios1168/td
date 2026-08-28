import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from dzero import nash_exact_d
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]; th,lam=.4,.3
c1,c2=1-lam,th*(1-lam)
ua_t,ub_t=c1*Az+c2*Bz+lam*Mz, c2*Az+c1*Bz+lam*Mz   # TRUE utilities

print("Which decision creates the anti-sandbagging incentive?")
print(f"  marginal effect of a's reported A_z on a's OBJECTIVE value:")
print(f"    d=(S_a,S_b), zip WON  : c1 - 1 = {c1-1:+.3f}   (reporting more HURTS)")
print(f"    d=(S_a,S_b), zip CEDED:   0 - 1 = {-1:+.3f}   (reporting more HURTS)")
print(f"    d=(0,0),     zip WON  : c1     = {c1:+.3f}   (reporting more HELPS)")
print(f"    d=(0,0),     zip CEDED:   0     = { 0:+.3f}")
print("  -> the disincentive comes from the SUBTRACTED BASELINE, not the headroom convention.\n")

def run(da,db,label):
    print(f"  {label}")
    base_x=nash_exact_d(Az,Bz,Mz,th,lam,da,db)["x"]
    base_u=ua_t[base_x].sum()
    for s in (1.0,0.8,0.5,1.25,2.0):
        Ap=Az*s
        dda = Ap.sum() if da!=0. else 0.
        x=nash_exact_d(Ap,Bz,Mz,th,lam,dda,db)["x"]
        print(f"    report A x{s:<5} -> a wins {int(x.sum()):>3} zips, TRUE utility {ua_t[x].sum():.4f}  ({100*(ua_t[x].sum()-base_u)/base_u:+.2f}%)")
run(Az.sum(),Bz.sum(),"baseline = pre-merger book:")
run(0.,0.,"baseline = zero (MNW):")
print("\n  CORRECTION to my review: I attributed the anti-sandbagging property to the")
print("  net-headroom convention. It is the NONZERO BASELINE that produces it.")
print("  Moving to d=0 fixes EF1 but GIVES UP this incentive property.")
