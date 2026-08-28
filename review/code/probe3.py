import numpy as np, pickle, itertools
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz,th,lam=d["Az"],d["Bz"],d["Mz"],d["th"],d["lam"]
def gains(A,B,M,th,lam,x):
    c1,c2=1-lam,th*(1-lam)
    ua,ub=c1*A+c2*B+lam*M, c2*A+c1*B+lam*M
    return ua[x].sum()-A.sum(), ub[~x].sum()-B.sum()
def prefix_best(A,B,M,th,lam):
    c1,c2=1-lam,th*(1-lam)
    ua,ub=c1*A+c2*B+lam*M, c2*A+c1*B+lam*M
    o=np.argsort(-(ua/ub)); Sa,Sb=A.sum(),B.sum()
    ga=np.concatenate([[0.],np.cumsum(ua[o])])-Sa
    gb=np.concatenate([[ub.sum()],ub.sum()-np.cumsum(ub[o])])-Sb
    k=int(np.argmax(np.where((ga>0)&(gb>0),ga*gb,-np.inf)))
    x=np.zeros(len(A),bool); x[o[:k]]=True
    return ga[k]*gb[k], x

print("=== power of the Appendix B test (400k uniform random subsets, n=50) ===")
print(f"  search space 2^50            = {2**50:.3e}")
print(f"  fraction sampled by 400k     = {400_000/2**50:.2e}")
p0,x0=prefix_best(Az,Bz,Mz,th,lam)
rng=np.random.default_rng(1); best=0
for _ in range(400_000):
    x=rng.random(50)<0.5
    ga,gb=gains(Az,Bz,Mz,th,lam,x)
    if ga>0 and gb>0: best=max(best,ga*gb)
print(f"  best uniform-random product  = {best:.4f}   vs best prefix {p0:.4f}")
# LOCAL SEARCH: the test that actually has power
x=x0.copy(); cur=p0; improved=True; nsw=0
while improved:
    improved=False
    for i in range(50):
        y=x.copy(); y[i]=~y[i]
        ga,gb=gains(Az,Bz,Mz,th,lam,y)
        if ga>0 and gb>0 and ga*gb>cur+1e-12: x,cur,improved=y,ga*gb,True; nsw+=1
    for i,j in itertools.combinations(range(50),2):
        if x[i]==x[j]: continue
        y=x.copy(); y[i],y[j]=y[j],y[i]
        ga,gb=gains(Az,Bz,Mz,th,lam,y)
        if ga>0 and gb>0 and ga*gb>cur+1e-12: x,cur,improved=y,ga*gb,True; nsw+=1
print(f"  best by 1-flip/1-swap LOCAL  = {cur:.5f}   ({nsw} improving moves found from the prefix optimum)")
print(f"  -> prefix shortfall vs local = {100*(cur-p0)/p0:.4f}%")

print("\n=== sensitivity: parameter vs data uncertainty (paper's claim) ===")
_,xb=prefix_best(Az,Bz,Mz,0.40,0.30)
mv=[]
for t in np.linspace(.2,.6,9):
    for l in np.linspace(.1,.5,9):
        _,xx=prefix_best(Az,Bz,Mz,t,l); mv.append((xx!=xb).sum())
print(f"  theta x lam grid  : zips moved  mean {np.mean(mv):.1f}  max {max(mv)}  of 50")
rng=np.random.default_rng(7); mv2=[]
for _ in range(300):
    Ap=Az*rng.lognormal(0,.10,50); Bp=Bz*rng.lognormal(0,.10,50); Mp=Mz*rng.lognormal(0,.06,50)
    _,xx=prefix_best(Ap,Bp,Mp,.40,.30); mv2.append((xx!=xb).sum())
print(f"  10%/6% data noise : zips moved  mean {np.mean(mv2):.1f}  max {max(mv2)}  of 50")
print(f"  -> ratio of data to parameter sensitivity: {np.mean(mv2)/max(np.mean(mv),1e-9):.1f}x")

print("\n=== scale invariance check (Nash axiom) ===")
for s in [1.0, 10.0, 1000.0]:
    c1,c2=1-lam,th*(1-lam)
    ua,ub=(c1*Az+c2*Bz+lam*Mz)*s, c2*Az+c1*Bz+lam*Mz
    o=np.argsort(-(ua/ub)); ga=np.concatenate([[0.],np.cumsum(ua[o])])-Az.sum()*s
    gb=np.concatenate([[ub.sum()],ub.sum()-np.cumsum(ub[o])])-Bz.sum()
    k=int(np.argmax(np.where((ga>0)&(gb>0),ga*gb,-np.inf)))
    print(f"  a's utility scaled x{s:<7} -> k={k}")
