import numpy as np, itertools
rng = np.random.default_rng(0)

def util(A,B,M,th,lam):
    c1,c2 = 1-lam, th*(1-lam)
    return c1*A+c2*B+lam*M, c2*A+c1*B+lam*M

def brute(ua,ub,Sa,Sb,dis=True):
    n=len(ua); best=(-np.inf,None)
    for mask in range(1<<n):
        x=np.array([(mask>>i)&1 for i in range(n)],bool)
        ga=ua[x].sum()-(Sa if dis else 0.0)
        gb=ub[~x].sum()-(Sb if dis else 0.0)
        if ga>0 and gb>0 and ga*gb>best[0]: best=(ga*gb,x.copy())
    return best

def ef1(ua,ub,x):
    # a's view: own bundle vs b's bundle minus best single item
    va_own, va_oth = ua[x].sum(), ua[~x].sum()
    ok_a = va_own >= va_oth - (ua[~x].max() if (~x).any() else 0) - 1e-12
    vb_own, vb_oth = ub[~x].sum(), ub[x].sum()
    ok_b = vb_own >= vb_oth - (ub[x].max() if x.any() else 0) - 1e-12
    return ok_a, ok_b

viol_dis=viol_mnw=trials=0; worst=None
for t in range(4000):
    n=rng.integers(4,9)
    th,lam = rng.uniform(.2,.6), rng.uniform(.1,.5)
    M=rng.uniform(1,10,n)
    A=M*rng.uniform(.02,.35,n); B=M*rng.uniform(.02,.35,n)
    keep=M>=np.maximum(A+th*B,B+th*A)
    if not keep.all(): continue
    ua,ub=util(A,B,M,th,lam); Sa,Sb=A.sum(),B.sum()
    p,x=brute(ua,ub,Sa,Sb,dis=True)
    if x is None: continue
    trials+=1
    a_ok,b_ok=ef1(ua,ub,x)
    if not(a_ok and b_ok):
        viol_dis+=1
        va_own,va_oth=ua[x].sum(),ua[~x].sum()
        gapa=(va_oth-(ua[~x].max() if (~x).any() else 0))-va_own
        vb_own,vb_oth=ub[~x].sum(),ub[x].sum()
        gapb=(vb_oth-(ub[x].max() if x.any() else 0))-vb_own
        g=max(gapa,gapb)
        if worst is None or g>worst[0]:
            worst=(g,n,th,lam,A.copy(),B.copy(),M.copy(),x.copy(),
                   g/max(va_own,vb_own))
    # zero-disagreement MNW on same data
    p0,x0=brute(ua,ub,0,0,dis=False)
    if x0 is not None:
        a0,b0=ef1(ua,ub,x0)
        if not(a0 and b0): viol_mnw+=1

print(f"instances tested                : {trials}")
print(f"EF1 violations, d=(Sa,Sb)       : {viol_dis}  ({100*viol_dis/trials:.1f}%)")
print(f"EF1 violations, d=(0,0) [MNW]   : {viol_mnw}  ({100*viol_mnw/trials:.1f}%)")
if worst:
    g,n,th,lam,A,B,M,x,rel=worst
    print(f"\nworst violation: residual envy {g:.4f}  ({100*rel:.1f}% of envier's own bundle)")
    print(f"  n={n} theta={th:.3f} lam={lam:.3f}")
    print("  A=",np.round(A,3)); print("  B=",np.round(B,3)); print("  M=",np.round(M,3))
    print("  x(to a)=",x.astype(int))
