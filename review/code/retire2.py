import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from dzero import nash_exact_d
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]

def pair(A,B,M,th,lam):
    r1=nash_exact_d(A,B,M,th,lam); r0=nash_exact_d(A,B,M,th,lam,0.,0.)
    return r1["x"],r0["x"]

print("=== is '3 zips' stable across the defensible parameter box? ===")
mv=[]
for th in np.linspace(.2,.6,5):
    row=[]
    for lam in np.linspace(.1,.5,5):
        x1,x0=pair(Az,Bz,Mz,th,lam); row.append(int((x1!=x0).sum()))
    mv.append(row)
    print(f"  theta={th:.2f}  zips moved by lam=[.1 .2 .3 .4 .5]: {row}")
mv=np.array(mv)
print(f"  min {mv.min()}  median {int(np.median(mv))}  max {mv.max()}  of 50   -- never <= 1: {(mv<=1).sum()==0}")

print("\n=== EF1 safety margin: how close is each baseline to violating? ===")
th,lam=.4,.3; c1,c2=1-lam,th*(1-lam)
ua,ub=c1*Az+c2*Bz+lam*Mz, c2*Az+c1*Bz+lam*Mz
def margin(x):
    ga=(ua[~x].sum()-ua[~x].max())-ua[x].sum()
    gb=(ub[x].sum()-ub[x].max())-ub[~x].sum()
    return max(ga,gb)
x1,x0=pair(Az,Bz,Mz,th,lam)
m1,m0=margin(x1),margin(x0)
print(f"  d=(Sa,Sb): margin {m1:+.4f}   (negative = EF1 holds; closer to 0 = more fragile)")
print(f"  d=(0,0)  : margin {m0:+.4f}")
print(f"  -> the zero-baseline map sits {m0/m1:.0f}x further from violating EF1 on this instance")

print("\n=== under 10%/6% data noise, how often does each baseline violate EF1? ===")
rng=np.random.default_rng(11); v1=v0=0; N=200; mm1=[]; mm0=[]
for _ in range(N):
    Ap=Az*rng.lognormal(0,.10,50); Bp=Bz*rng.lognormal(0,.10,50); Mp=Mz*rng.lognormal(0,.06,50)
    uap,ubp=c1*Ap+c2*Bp+lam*Mp, c2*Ap+c1*Bp+lam*Mp
    def marg(x):
        ga=(uap[~x].sum()-uap[~x].max())-uap[x].sum()
        gb=(ubp[x].sum()-ubp[x].max())-ubp[~x].sum()
        return max(ga,gb)
    y1,y0=pair(Ap,Bp,Mp,th,lam)
    g1,g0=marg(y1),marg(y0); mm1.append(g1); mm0.append(g0)
    v1+= g1>1e-12; v0+= g0>1e-12
print(f"  d=(Sa,Sb): EF1 violated in {v1}/{N} draws   mean margin {np.mean(mm1):+.4f}  worst {max(mm1):+.4f}")
print(f"  d=(0,0)  : EF1 violated in {v0}/{N} draws   mean margin {np.mean(mm0):+.4f}  worst {max(mm0):+.4f}")
