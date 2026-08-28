import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle, matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from dzero import nash_exact_d
d=pickle.load(open("/tmp/z50.pkl","rb"))
Z,Az,Bz,Mz=d["Z"],d["Az"],d["Bz"],d["Mz"]; th,lam=.4,.3
c1,c2=1-lam,th*(1-lam)
ua,ub=c1*Az+c2*Bz+lam*Mz, c2*Az+c1*Bz+lam*Mz
x1=nash_exact_d(Az,Bz,Mz,th,lam)["x"]; x0=nash_exact_d(Az,Bz,Mz,th,lam,0.,0.)["x"]
moved=x1!=x0

mpl.rcParams.update({"font.size":8,"axes.titlesize":8,"axes.labelsize":8,
    "xtick.labelsize":6,"ytick.labelsize":6,"legend.fontsize":7,
    "axes.spines.top":False,"axes.spines.right":False,"figure.dpi":300,
    "xtick.direction":"out","ytick.direction":"out"})
CA,CB,CM="#2166ac","#b2182b","#4d4d4d"
fig,axes=plt.subplots(1,3,figsize=(11,3.7))

# panel a: map
ax=axes[0]
ax.scatter(Z[x1,0],Z[x1,1],s=26,c=CA,edgecolor="white",linewidth=.5,label="rep a",zorder=3)
ax.scatter(Z[~x1,0],Z[~x1,1],s=26,c=CB,edgecolor="white",linewidth=.5,label="rep b",zorder=3)
ax.scatter(Z[moved,0],Z[moved,1],s=150,facecolor="none",edgecolor="black",linewidth=1.4,zorder=4)
ax.text(.03,.97,"circled: moves to b when the\nbaseline is set to zero",transform=ax.transAxes,
        va="top",ha="left",fontsize=7)
ax.set_title("3 of 50 zips change hands",loc="left")
ax.set_xlabel("longitude (unit square)"); ax.set_ylabel("latitude")
ax.legend(frameon=False,loc="lower right"); ax.margins(.06)

# panel b: EF1 margin under noise
ax=axes[1]
rng=np.random.default_rng(11); m1=[];m0=[]
for _ in range(200):
    Ap=Az*rng.lognormal(0,.10,50);Bp=Bz*rng.lognormal(0,.10,50);Mp=Mz*rng.lognormal(0,.06,50)
    uap,ubp=c1*Ap+c2*Bp+lam*Mp, c2*Ap+c1*Bp+lam*Mp
    def mg(x):
        return max((uap[~x].sum()-uap[~x].max())-uap[x].sum(),
                   (ubp[x].sum()-ubp[x].max())-ubp[~x].sum())
    m1.append(mg(nash_exact_d(Ap,Bp,Mp,th,lam)["x"]))
    m0.append(mg(nash_exact_d(Ap,Bp,Mp,th,lam,0.,0.)["x"]))
m1,m0=np.array(m1),np.array(m0)
jit=rng.uniform(-.13,.13,200)
ax.axhline(0,color="black",lw=1)
ax.scatter(np.zeros(200)+jit,m1,s=9,c=np.where(m1>0,"#b2182b","#7f7f7f"),alpha=.65,linewidth=0)
ax.scatter(np.ones(200)+jit,m0,s=9,c="#7f7f7f",alpha=.65,linewidth=0)
for i,v in enumerate([m1,m0]):
    ax.plot([i-.28,i+.28],[np.median(v)]*2,color="black",lw=2,zorder=5)
ax.set_xticks([0,1]); ax.set_xticklabels(["pre-merger book\n$d=(S_a,S_b)$","zero\n$d=(0,0)$"])
ax.set_ylabel("EF1 residual envy")
ax.text(.02,.97,f"above the line = EF1 violated:  {(m1>0).sum()}/200  vs  {(m0>0).sum()}/200",
        transform=ax.transAxes,va="top",fontsize=7)
ax.set_ylim(min(m0.min(),m1.min())-.10, max(m1.max(),0)+.42)
ax.set_title("Only the pre-merger baseline breaks EF1",loc="left")
ax.margins(y=.08)

# panel c: zips moved across parameter box
ax=axes[2]
lams=np.linspace(.1,.5,5); thetas=np.linspace(.2,.6,5)
Mv=np.zeros((5,5))
for i,t in enumerate(thetas):
    for j,l in enumerate(lams):
        Mv[i,j]=(nash_exact_d(Az,Bz,Mz,t,l)["x"]!=nash_exact_d(Az,Bz,Mz,t,l,0.,0.)["x"]).sum()
im=ax.imshow(Mv,cmap="viridis",origin="lower",aspect="auto",vmin=0)
for i in range(5):
    for j in range(5):
        ax.text(j,i,f"{int(Mv[i,j])}",ha="center",va="center",
                color="white" if Mv[i,j]<Mv.max()*.6 else "black",fontsize=7)
ax.set_xticks(range(5)); ax.set_xticklabels([f"{v:.1f}" for v in lams])
ax.set_yticks(range(5)); ax.set_yticklabels([f"{v:.1f}" for v in thetas])
ax.set_xlabel("headroom credit  $\\lambda$"); ax.set_ylabel("transfer capture  $\\theta$")
ax.set_title("Never $\\leq$ 1 zip anywhere in the box",loc="left")
cb=fig.colorbar(im,ax=ax,fraction=.046,pad=.03); cb.set_label("zips moved (of 50)",fontsize=7)
cb.ax.tick_params(labelsize=6)
for i,(a,l) in enumerate(zip(axes,"abc")):
    a.text(-.10,1.10,l,transform=a.transAxes,fontsize=11,fontweight="bold",va="top")
fig.tight_layout()
fig.savefig("disagreement_point_test.png",bbox_inches="tight")
r=fig.canvas.get_renderer()
ts=[(t,t.get_window_extent(r)) for t in fig.findobj(mpl.text.Text) if t.get_text().strip() and t.get_visible()]
ov=[(a.get_text(),b.get_text()) for i,(a,ba) in enumerate(ts) for b,bb in ts[i+1:] if ba.overlaps(bb)]
print("text overlaps:",len(ov))
print(f"panel b: d=(Sa,Sb) violates {(m1>0).sum()}/200, d=0 violates {(m0>0).sum()}/200")
print(f"panel c: min {int(Mv.min())} max {int(Mv.max())}")
