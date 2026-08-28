import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]; n=50

def asym_nash(A,B,M,th,lam,om,da=0.,db=0.,max_iter=60,tol=1e-9):
    """max om*log g_a + (1-om)*log g_b, outer approximation."""
    c1,c2=1-lam,th*(1-lam)
    ua,ub=c1*A+c2*B+lam*M, c2*A+c1*B+lam*M
    NV=n+2; IA,IB=n,n+1
    rows,rl,ru=[],[],[]
    def add(p,lo,hi): rows.append(p); rl.append(lo); ru.append(hi)
    def tan(side,gh):
        if gh<=1e-12: return
        if side=="a": add([(IA,1.)]+[(i,-ua[i]/gh) for i in range(n)],-np.inf,np.log(gh)-1.-da/gh)
        else:         add([(IB,1.)]+[(i, ub[i]/gh) for i in range(n)],-np.inf,np.log(gh)-1.+(ub.sum()-db)/gh)
    span=max(ua.sum()-da,ub.sum()-db)
    for g0 in np.geomspace(max(span*1e-3,1e-3),span,8): tan("a",g0); tan("b",g0)
    c=np.zeros(NV); c[IA]=-om; c[IB]=-(1-om)
    integ=np.zeros(NV); integ[:n]=1
    lo=np.zeros(NV); hi=np.ones(NV); lo[IA]=lo[IB]=-60; hi[IA]=hi[IB]=60
    def build():
        Am=lil_matrix((len(rows),NV))
        for k,pr in enumerate(rows):
            for cc,vv in pr: Am[k,cc]+=vv
        return LinearConstraint(csr_matrix(Am),np.array(rl),np.array(ru))
    best=(-np.inf,None)
    for it in range(max_iter):
        r=milp(c=c,constraints=build(),integrality=integ,bounds=Bounds(lo,hi),
               options=dict(time_limit=60,mip_rel_gap=0.0))
        if not r.success: return None
        x=np.round(r.x[:n]).astype(bool)
        ga,gb=ua[x].sum()-da, ub[~x].sum()-db
        LB=om*np.log(ga)+(1-om)*np.log(gb) if (ga>0 and gb>0) else -np.inf
        if LB>best[0]: best=(LB,x.copy())
        add_=0
        if ga>0 and r.x[IA]-np.log(ga)>tol: tan("a",ga); add_+=1
        if gb>0 and r.x[IB]-np.log(gb)>tol: tan("b",gb); add_+=1
        if add_==0: return best[1]
    return best[1]

from dzero import nash_exact_d
th,lam=.4,.3
x_book=nash_exact_d(Az,Bz,Mz,th,lam)["x"]                 # d=(Sa,Sb), omega=1/2
print("Which EXPLICIT seniority weight omega reproduces the pre-merger-baseline map?")
print("(asymmetric Nash at d=0: max g_a^omega * g_b^(1-omega))\n")
print(f"{'omega':>7} {'k':>4} {'zips differing from book-baseline map':>40}")
hits=[]
for om in np.arange(.40,.66,.01):
    x=asym_nash(Az,Bz,Mz,th,lam,float(om))
    dif=int((x!=x_book).sum())
    if dif<=3: print(f"{om:>7.2f} {int(x.sum()):>4} {dif:>40}")
    hits.append((round(float(om),2),dif))
best=[o for o,dd in hits if dd==min(h[1] for h in hits)]
print(f"\n  closest match at omega = {best}  (min divergence {min(h[1] for h in hits)} zips)")
np.save("/tmp/xbook.npy",x_book)
