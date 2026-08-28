import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pickle, matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from capacity import nash_exact_capacity, saturating_response
from dzero import nash_exact_d

d = pickle.load(open("/tmp/z50.pkl", "rb"))
Az, Bz, Mz, th, lam = d["Az"], d["Bz"], d["Mz"], d["th"], d["lam"]
Sa, Sb = d["Sa"], d["Sb"]
c1, c2 = 1 - lam, th * (1 - lam)
ua, ub = c1*Az + c2*Bz + lam*Mz, c2*Az + c1*Bz + lam*Mz

x_d0 = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0.)["x"]           # settled baseline
x_book = nash_exact_d(Az, Bz, Mz, th, lam)["x"]                       # rejected baseline (d=Sa,Sb)
ya0, yb0 = ua[x_d0].sum(), ub[~x_d0].sum()

mpl.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 300,
    "xtick.direction": "out", "ytick.direction": "out"})
CA, CB, CM = "#2166ac", "#b2182b", "#4d4d4d"
fig, axes = plt.subplots(1, 3, figsize=(11, 3.7))

# panel a: symmetric ceiling K -- zips moved (bars) + objective gain from resolving (line)
ax = axes[0]
Ks = np.array([12, 10, 8, 6, 5, 4, 3.5, 3, 2.5, 2])
dif, gain = [], []
for K in Ks:
    fa, logfa, _ = saturating_response(K)
    r = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0., saturating_response(K), saturating_response(K))
    dif.append(int((r["x"] != x_d0).sum()))
    obj0 = logfa(ya0) + logfa(yb0)
    ya1, yb1 = ua[r["x"]].sum(), ub[~r["x"]].sum()
    gain.append(logfa(ya1) + logfa(yb1) - obj0)
dif, gain = np.array(dif), np.array(gain)
ax.bar(range(len(Ks)), dif, color=CM, alpha=.55, width=.6, label="zips moved (left)")
ax.set_xticks(range(len(Ks))); ax.set_xticklabels([f"{k:g}" for k in Ks], rotation=0)
ax.set_xlabel("symmetric ceiling  $K_a=K_b=K$  (baseline: $y_a^*{=}$"
              f"{ya0:.1f}, $y_b^*{{=}}${yb0:.1f})")
ax.set_ylabel("zips moved vs no-capacity baseline")
ax2 = ax.twinx()
ax2.plot(range(len(Ks)), np.maximum(gain, 1e-8), "o-", color=CA, ms=3, lw=1, label="log-Nash gain (right)")
ax2.set_yscale("log"); ax2.set_ylabel("objective gained by re-solving", color=CA, fontsize=7)
ax2.tick_params(axis="y", colors=CA, labelsize=6)
ax.text(.02, .97, "moves are knife-edge ties:\ngain $<10^{-4}$ throughout",
        transform=ax.transAxes, va="top", fontsize=6.5)
ax.set_title("Symmetric ceiling alone: cosmetic", loc="left")

# panel b: book-proportional asymmetric ceiling, both directions
ax = axes[1]
mults = np.array([10, 6, 5, 4, 3, 2, 1.5, 1.0])
dif_fwd, dif_rev = [], []
for m in mults:
    rf = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0.,
                             saturating_response(m*Sa), saturating_response(m*Sb))
    rr = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0.,
                             saturating_response(m*Sb), saturating_response(m*Sa))
    dif_fwd.append(int((rf["x"] != x_d0).sum()))
    dif_rev.append(int((rr["x"] != x_d0).sum()))
ax.plot(mults, dif_fwd, "o-", color=CA, ms=4, label=r"$K_a{=}m S_a,\ K_b{=}m S_b$ (a favored)")
ax.plot(mults, dif_rev, "s-", color=CB, ms=4, label=r"$K_a{=}m S_b,\ K_b{=}m S_a$ (b favored)")
ax.invert_xaxis()
ax.set_xlabel("capacity multiple on legacy book,  $m$")
ax.set_ylabel("zips moved vs no-capacity baseline")
ax.legend(frameon=False, loc="upper left", fontsize=6.5)
ax.set_title("Book-proportional ceiling: real, not cosmetic", loc="left")

# panel c: convergence to the REJECTED book-baseline as capacity tightens
ax = axes[2]
mults2 = np.array([10, 6, 5, 4.5, 4, 3.5, 3, 2.5])
dif_vs_book, dif_vs_d0 = [], []
for m in mults2:
    r = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0.,
                            saturating_response(m*Sa), saturating_response(m*Sb))
    dif_vs_book.append(int((r["x"] != x_book).sum()))
    dif_vs_d0.append(int((r["x"] != x_d0).sum()))
ax.plot(mults2, dif_vs_book, "o-", color="#e08214", ms=4, label="vs rejected $d=(S_a,S_b)$ map")
ax.plot(mults2, dif_vs_d0, "^-", color=CM, ms=4, label="vs settled $d=(0,0)$ map")
ax.invert_xaxis()
ax.axhline(1, color="black", lw=.6, ls=":")
ax.set_xlabel("capacity multiple on legacy book,  $m$")
ax.set_ylabel("zips differing")
ax.legend(frameon=False, loc="upper left", fontsize=6.5)
ax.text(.02, .05, "at m$\\approx$3.5 capacity alone\nreproduces the rejected map",
        transform=ax.transAxes, va="bottom", fontsize=6.5)
ax.set_title("Capacity can silently re-derive the\nrejected seniority tilt", loc="left")

for i, (a, l) in enumerate(zip(axes, "abc")):
    a.text(-.14, 1.14, l, transform=a.transAxes, fontsize=11, fontweight="bold", va="top")
fig.tight_layout()
fig.savefig("capacity_ceiling_test.png", bbox_inches="tight")

r = fig.canvas.get_renderer()
ts = [(t, t.get_window_extent(r)) for t in fig.findobj(mpl.text.Text) if t.get_text().strip() and t.get_visible()]
ov = [(a.get_text(), b.get_text()) for i, (a, ba) in enumerate(ts) for b, bb in ts[i+1:] if ba.overlaps(bb)]
print("text overlaps:", len(ov))
print("panel a dif:", dif.tolist())
print("panel b fwd:", dif_fwd, "rev:", dif_rev)
print("panel c vs_book:", dif_vs_book, "vs_d0:", dif_vs_d0)
