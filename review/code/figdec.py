import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle, matplotlib as mpl
mpl.use("Agg"); import matplotlib.pyplot as plt
from dzero import nash_exact_d
from omega import asym_nash
d=pickle.load(open("/tmp/z50.pkl","rb"))
Az,Bz,Mz=d["Az"],d["Bz"],d["Mz"]; th,lam=.4,.3
c1,c2=1-lam,th*(1-lam)
ua,ub=c1*Az+c2*Bz+lam*Mz, c2*Az+c1*Bz+lam*Mz
Sa,Sb=Az.sum(),Bz.sum()
mpl.rcParams.update({"font.size":8,"axes.titlesize":8,"axes.labelsize":8,
 "xtick.labelsize":6,"ytick.labelsize":6,"legend.fontsize":7,
 "axes.spines.top":False,"axes.spines.right":False,"figure.dpi":300})
CA,CB="#2166ac","#b2182b"

oms=np.round(np.arange(.44,.645,.02),2)
rng=np.random.default_rng(11); N=40
viol=[]; shareA=[]
draws=[(Az*rng.lognormal(0,.10,50),Bz*rng.lognormal(0,.10,50),Mz*rng.lognormal(0,.06,50)) for _ in range(N)]
for om in oms:
    v=0
    for Ap,Bp,Mp in draws:
        uap,ubp=c1*Ap+c2*Bp+lam*Mp, c2*Ap+c1*Bp+lam*Mp
        x=asym_nash(Ap,Bp,Mp,th,lam,float(om))
        g=max((uap[~x].sum()-uap[~x].max())-uap[x].sum(),(ubp[x].sum()-ubp[x].max())-ubp[~x].sum())
        v+= g>1e-12
    viol.append(100*v/N)
    x=asym_nash(Az,Bz,Mz,th,lam,float(om)); shareA.append(100*Mz[x].sum()/Mz.sum())

fig,axes=plt.subplots(1,2,figsize=(8.4,3.5))
ax=axes[0]
ax.plot(oms,viol,"-o",ms=3.5,color="#333333",zorder=3)
ax.axvline(.5,color=CA,lw=1.2,ls="--"); ax.axvline(.54,color=CB,lw=1.2,ls="--")
ax.text(.503,96,"symmetric\n$d=(0,0)$",color=CA,fontsize=7,va="top")
ax.text(.545,58,"implied by\npre-merger\nbaseline",color=CB,fontsize=7,va="top")
ax.set_xlabel("seniority weight  $\\omega$  (asymmetric Nash at $d=0$)")
ax.set_ylabel("EF1 violated (% of noise draws)")
ax.set_title("EF1 is a knife-edge property of $\\omega=0.5$",loc="left")
ax.set_ylim(-4,104); ax.margins(x=.04)

ax=axes[1]
opts=[("$d=(S_a,S_b)$\npre-merger book",nash_exact_d(Az,Bz,Mz,th,lam)["x"]),
      ("$d=(0,0)$\nsymmetric MNW",nash_exact_d(Az,Bz,Mz,th,lam,0.,0.)["x"])]
xs=np.arange(2); w=.36
va=[ua[x].sum() for _,x in opts]; vb=[ub[~x].sum() for _,x in opts]
ax.bar(xs-w/2,va,w,color=CA,label="rep a (larger book)")
ax.bar(xs+w/2,vb,w,color=CB,label="rep b (smaller book)")
for i,(p,q) in enumerate(zip(va,vb)):
    ax.text(i-w/2,p+.09,f"{p:.2f}",ha="center",fontsize=7)
    ax.text(i+w/2,q+.09,f"{q:.2f}",ha="center",fontsize=7)
ax.annotate("",xy=(1-w/2,va[1]+.42),xytext=(0-w/2,va[0]+.42),
            arrowprops=dict(arrowstyle="->",color="#555555",lw=1,
                            connectionstyle="arc3,rad=-.28"))
ax.text(.5,9.15,"$-7.6\\%$ to a,  $+8.9\\%$ to b",ha="center",fontsize=7,color="#555555")
ax.set_xticks(xs); ax.set_xticklabels([o[0] for o in opts])
ax.set_ylabel("post-merger book value")
ax.set_title("What the choice costs each rep",loc="left")
ax.legend(frameon=False,loc="upper left",ncol=1,bbox_to_anchor=(.02,.99)); ax.set_ylim(0,11.4)
for a,l in zip(axes,"ab"):
    a.text(-.13,1.10,l,transform=a.transAxes,fontsize=11,fontweight="bold",va="top")
fig.tight_layout(); fig.savefig("baseline_decision.png",bbox_inches="tight")
r=fig.canvas.get_renderer()
ts=[(t,t.get_window_extent(r)) for t in fig.findobj(mpl.text.Text) if t.get_text().strip() and t.get_visible()]
print("overlaps:",sum(1 for i,(a,ba) in enumerate(ts) for b,bb in ts[i+1:] if ba.overlaps(bb)))
print("EF1 viol% by omega:",dict(zip(oms,viol)))
