import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from omega import asym_nash
from dzero import nash_exact_d
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]

def implied_omega(A,B,M,th,lam):
    xb=nash_exact_d(A,B,M,th,lam)["x"]
    best=(99,None)
    for om in np.arange(.40,.70,.01):
        x=asym_nash(A,B,M,th,lam,float(om))
        dd=int((x!=xb).sum())
        if dd<best[0]: best=(dd,round(float(om),2))
    return best[1],best[0]

print("Is the entitlement weight the book-baseline implies STABLE across parameters?")
print(f"{'theta':>6}{'lam':>7}{'implied omega':>15}{'exact?':>9}")
oms=[]
for th in (.3,.4,.5):
    for lam in (.15,.30,.45):
        om,dd=implied_omega(Az,Bz,Mz,th,lam)
        oms.append(om); print(f"{th:>6.2f}{lam:>7.2f}{om:>15.2f}{('yes' if dd==0 else f'{dd} zips'):>9}")
print(f"\n  implied omega ranges {min(oms):.2f} - {max(oms):.2f}")
print(f"  book share S_a/(S_a+S_b) = {Az.sum()/(Az.sum()+Bz.sum()):.3f}  (what a naive entitlement rule would use)")

print("\nUnder 10%/6% data noise, how much does the implied weight wander?")
rng=np.random.default_rng(5); w=[]
for _ in range(20):
    Ap=Az*rng.lognormal(0,.10,50);Bp=Bz*rng.lognormal(0,.10,50);Mp=Mz*rng.lognormal(0,.06,50)
    om,_=implied_omega(Ap,Bp,Mp,.4,.3); w.append(om)
w=np.array(w)
print(f"  implied omega across 20 noise draws: mean {w.mean():.3f}  sd {w.std():.3f}  range [{w.min():.2f}, {w.max():.2f}]")

print("\nDoes EF1 survive the explicit-weight route at d=0?")
th,lam=.4,.3; c1,c2=1-lam,th*(1-lam)
rng=np.random.default_rng(11); v={.50:0,.54:0,.60:0}; N=60
for _ in range(N):
    Ap=Az*rng.lognormal(0,.10,50);Bp=Bz*rng.lognormal(0,.10,50);Mp=Mz*rng.lognormal(0,.06,50)
    uap,ubp=c1*Ap+c2*Bp+lam*Mp, c2*Ap+c1*Bp+lam*Mp
    for om in v:
        x=asym_nash(Ap,Bp,Mp,th,lam,om)
        g=max((uap[~x].sum()-uap[~x].max())-uap[x].sum(),(ubp[x].sum()-ubp[x].max())-ubp[~x].sum())
        v[om]+= g>1e-12
for om in v: print(f"  omega={om:.2f} at d=0 : EF1 violated {v[om]}/{N} draws")
print(f"  (for reference, d=(S_a,S_b) violated 74/200 = 37% under the same noise)")
