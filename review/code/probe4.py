import numpy as np, pickle
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]
def best(A,B,M,th=.4,lam=.3):
    c1,c2=1-lam,th*(1-lam)
    ua,ub=c1*A+c2*B+lam*M, c2*A+c1*B+lam*M
    o=np.argsort(-(ua/ub))
    ga=np.concatenate([[0.],np.cumsum(ua[o])])-A.sum()
    gb=np.concatenate([[ub.sum()],ub.sum()-np.cumsum(ub[o])])-B.sum()
    k=int(np.argmax(np.where((ga>0)&(gb>0),ga*gb,-np.inf)))
    x=np.zeros(len(A),bool); x[o[:k]]=True; return x
xb=best(Az,Bz,Mz)
rng=np.random.default_rng(7); N=500
flip=np.zeros(50)
for _ in range(N):
    x=best(Az*rng.lognormal(0,.10,50),Bz*rng.lognormal(0,.10,50),Mz*rng.lognormal(0,.06,50))
    flip+=(x!=xb)
p=flip/N
print(f"zips that EVER flip in {N} draws          : {(p>0).sum()} of 50")
print(f"zips flipping in >5% of draws            : {(p>0.05).sum()}")
print(f"zips flipping in >25% of draws           : {(p>0.25).sum()}")
print(f"mean zips moved per draw                 : {p.sum():.1f}")
print(f"\n-> 'moves 34 of 50' is the UNION across draws, not per-draw displacement.")
print(f"   Per-draw the map is stable ({p.sum():.1f} zips); the union counts any zip")
print(f"   that is ever marginal. These support opposite operational conclusions.")
