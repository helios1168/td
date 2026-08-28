import numpy as np, pickle, itertools
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix

def nash_exact_d(A,B,M,theta=.40,lam=.30,da=None,db=None,max_iter=60,tol=1e-9):
    """Outer approximation, mirroring territory.nash_exact but with an explicit
    disagreement point (da,db). da=db=0 gives maximum Nash welfare."""
    A,B,M=map(lambda v:np.asarray(v,float),(A,B,M)); n=len(A)
    c1,c2=1-lam,theta*(1-lam)
    ua,ub=c1*A+c2*B+lam*M, c2*A+c1*B+lam*M
    da=A.sum() if da is None else da; db=B.sum() if db is None else db
    NV=n+2; IA,IB=n,n+1
    rows,rl,ru=[],[],[]
    def add(pairs,lo,hi): rows.append(pairs); rl.append(lo); ru.append(hi)
    def tangent(side,gh):
        if gh<=1e-12: return
        if side=="a":
            add([(IA,1.)]+[(i,-ua[i]/gh) for i in range(n)], -np.inf, np.log(gh)-1.-da/gh)
        else:
            add([(IB,1.)]+[(i, ub[i]/gh) for i in range(n)], -np.inf, np.log(gh)-1.+(ub.sum()-db)/gh)
    span=max(ua.sum()-da, ub.sum()-db)
    for g0 in np.geomspace(max(span*1e-3,1e-3),span,8): tangent("a",g0); tangent("b",g0)
    c=np.zeros(NV); c[IA]=c[IB]=-1.
    integ=np.zeros(NV); integ[:n]=1
    lo=np.zeros(NV); hi=np.ones(NV); lo[IA]=lo[IB]=-60; hi[IA]=hi[IB]=60
    def build():
        Am=lil_matrix((len(rows),NV))
        for k,pr in enumerate(rows):
            for cc,vv in pr: Am[k,cc]+=vv
        return LinearConstraint(csr_matrix(Am),np.array(rl),np.array(ru))
    best=(-np.inf,None)
    for it in range(max_iter):
        res=milp(c=c,constraints=build(),integrality=integ,bounds=Bounds(lo,hi),
                 options=dict(time_limit=60,mip_rel_gap=0.0))
        if not res.success: return dict(status="fail",message=str(res.message))
        UB=res.x[IA]+res.x[IB]
        x=np.round(res.x[:n]).astype(bool)
        ga,gb=ua[x].sum()-da, ub[~x].sum()-db
        LB=np.log(ga)+np.log(gb) if (ga>0 and gb>0) else -np.inf
        if LB>best[0]: best=(LB,x.copy())
        added=0
        if ga>0 and res.x[IA]-np.log(ga)>tol: tangent("a",ga); added+=1
        if gb>0 and res.x[IB]-np.log(gb)>tol: tangent("b",gb); added+=1
        if added==0:
            xb=best[1]; ga,gb=ua[xb].sum()-da, ub[~xb].sum()-db
            return dict(status="optimal",x=xb,g_a=float(ga),g_b=float(gb),
                        product=float(ga*gb),iters=it+1,gap=float(UB-best[0]))
    xb=best[1]; ga,gb=ua[xb].sum()-da, ub[~xb].sum()-db
    return dict(status="iterlimit",x=xb,g_a=float(ga),g_b=float(gb),product=float(ga*gb))

def brute_d(ua,ub,da,db):
    n=len(ua); best=(-np.inf,None)
    for mask in range(1<<n):
        x=np.array([(mask>>i)&1 for i in range(n)],bool)
        ga,gb=ua[x].sum()-da, ub[~x].sum()-db
        if ga>0 and gb>0 and ga*gb>best[0]: best=(ga*gb,x.copy())
    return best

if __name__=="__main__":
    # validation 1: reproduce the paper's exact Nash number at d=(Sa,Sb)
    d=pickle.load(open("/tmp/z50.pkl","rb"))
    Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]
    r=nash_exact_d(Az,Bz,Mz)
    print(f"validation: d=(Sa,Sb) -> product {r['product']:.5f}  g_a={r['g_a']:.4f} g_b={r['g_b']:.4f} "
          f"k={int(r['x'].sum())} iters={r['iters']} gap={r['gap']:.2e}")
    print(f"            paper Section 7 reports 24.09117, g_a=4.9787, g_b=4.8388, k=25")
    # validation 2: solver vs brute force at n=12, both baselines
    rng=np.random.default_rng(3); ok=0; tot=0
    for _ in range(40):
        n=12; M=rng.uniform(1,10,n)
        A=M*rng.uniform(.02,.30,n); B=M*rng.uniform(.02,.30,n)
        th,lam=.4,.3
        if not (M>=np.maximum(A+th*B,B+th*A)).all(): continue
        ua,ub=(1-lam)*A+th*(1-lam)*B+lam*M, th*(1-lam)*A+(1-lam)*B+lam*M
        for (da,db) in [(A.sum(),B.sum()),(0.,0.)]:
            tot+=1
            s=nash_exact_d(A,B,M,th,lam,da,db); bp,_=brute_d(ua,ub,da,db)
            if abs(s["product"]-bp)<1e-7: ok+=1
    print(f"validation: solver matches brute force on {ok}/{tot} instances (n=12, both baselines)")
