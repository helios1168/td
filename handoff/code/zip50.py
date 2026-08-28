import numpy as np, pickle
rng=np.random.default_rng(17)
n=50; th,lam=0.40,0.30
c1,c2=1-lam,th*(1-lam)

# ---- ground truth: two metros, each a stronghold but both reps present -------
metros=np.array([[.28,.62],[.72,.36]])
covs=[np.array([[.020,.006],[.006,.014]]), np.array([[.014,-.005],[-.005,.020]])]
def gpdf(P,mu,cov):
    d=P-mu; ic=np.linalg.inv(cov)
    return np.exp(-.5*np.einsum('ij,jk,ik->i',d,ic,d))/(2*np.pi*np.sqrt(np.linalg.det(cov)))

# zip centroids: clustered near metros + scattered rural
k1=18; k2=16; k3=n-k1-k2
Z=np.vstack([rng.multivariate_normal(metros[0],covs[0]*2.2,k1),
             rng.multivariate_normal(metros[1],covs[1]*2.2,k2),
             rng.random((k3,2))])
Z=np.clip(Z,.02,.98)

dm=gpdf(Z,metros[0],covs[0])+gpdf(Z,metros[1],covs[1])
Mz=(0.80*dm/dm.max()+0.20)*rng.uniform(.7,1.3,n)          # opportunity
# A strong in metro 1, present in metro 2;  B the mirror
wa=0.75*gpdf(Z,metros[0],covs[0])+0.25*gpdf(Z,metros[1],covs[1])
wb=0.25*gpdf(Z,metros[0],covs[0])+0.75*gpdf(Z,metros[1],covs[1])
shA=0.10+0.30*wa/wa.max(); shB=0.10+0.30*wb/wb.max()
Az=Mz*shA*rng.lognormal(0,.20,n); Bz=Mz*shB*rng.lognormal(0,.20,n)

# enforce headroom >= 0 pointwise, then scale to the note's totals
scale=np.maximum(1.0,(Az+Bz)/(0.92*Mz)); Az/=scale; Bz/=scale
Az*=3.0/Az.sum(); Bz*=1.8/Bz.sum(); Mz*=40.0/Mz.sum()
bad=(Mz-Az-Bz)<0
if bad.any(): Mz[bad]=(Az+Bz)[bad]*1.05; Mz*=40.0/Mz.sum()
Sa,Sb,M=Az.sum(),Bz.sum(),Mz.sum()

ua=c1*Az+c2*Bz+lam*Mz; ub=c2*Az+c1*Bz+lam*Mz
head_a=Mz-Az-th*Bz; head_b=Mz-Bz-th*Az
print(f"  n={n}   S_a={Sa:.4f}  S_b={Sb:.4f}  M={M:.4f}")
print(f"  headroom min (net, a / b) : {head_a.min():.4f} / {head_b.min():.4f}   (need >= 0)")
print(f"  zip opportunity range     : [{Mz.min():.4f}, {Mz.max():.4f}]")
print(f"  combined share of market  : {(Sa+Sb)/M:.4f}")
print(f"  corr(A_z, B_z) across zips: {np.corrcoef(Az,Bz)[0,1]:+.4f}")
r=ua/ub
print(f"  utility ratio range       : [{r.min():.4f}, {r.max():.4f}]")
pickle.dump(dict(Z=Z,Az=Az,Bz=Bz,Mz=Mz,ua=ua,ub=ub,r=r,th=th,lam=lam,
                 c1=c1,c2=c2,Sa=Sa,Sb=Sb,M=M,metros=metros),open("/tmp/z50.pkl","wb"))
