import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from dzero import nash_exact_d
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]; th,lam=.4,.3
c1,c2=1-lam,th*(1-lam)
ua_t=c1*Az+c2*Bz+lam*Mz

def sweep(zero_base):
    da,db=(0.,0.) if zero_base else (Az.sum(),Bz.sum())
    x0=nash_exact_d(Az,Bz,Mz,th,lam,da,db)["x"]; u0=ua_t[x0].sum()
    rows=[]
    for s in np.concatenate([np.linspace(.3,.95,14),np.linspace(1.05,3.0,20)]):
        Ap=Az*s; dda=0. if zero_base else Ap.sum()
        x=nash_exact_d(Ap,Bz,Mz,th,lam,dda,db)["x"]
        rows.append((s, 100*(ua_t[x].sum()-u0)/u0))
    rows=np.array(rows)
    best=rows[np.argmax(rows[:,1])]
    return u0, best, rows

print("WORST-CASE unilateral misreport of own book by wholesaler a")
print("(scaling reported A by a constant s; gain measured in TRUE utility of the bundle won)\n")
for zb,nm in [(False,"d=(S_a,S_b)  pre-merger book"),(True,"d=(0,0)      zero / MNW    ")]:
    u0,best,rows=sweep(zb)
    under=rows[rows[:,0]<1]; over=rows[rows[:,0]>1]
    print(f"  {nm}")
    print(f"    truthful true utility          : {u0:.4f}")
    print(f"    best gain by UNDER-reporting   : {under[:,1].max():+6.2f}%  at s={under[np.argmax(under[:,1]),0]:.2f}")
    print(f"    best gain by OVER-reporting    : {over[:,1].max():+6.2f}%  at s={over[np.argmax(over[:,1]),0]:.2f}")
    print(f"    WORST CASE overall             : {best[1]:+6.2f}%  at s={best[0]:.2f}")
    print()
print("Reading:")
print("  The nonzero baseline does NOT make reporting incentive-compatible. It flips")
print("  the PROFITABLE DIRECTION from sandbagging to inflation, and the inflation")
print("  channel is the larger of the two exposures.")
