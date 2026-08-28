import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt

A = np.load("/tmp/census_stress_alpha.npy")     # alpha, ship_m, ship_lo, ship_hi, eff_m, eff_lo, eff_hi
U = np.load("/tmp/census_stress_audit.npy")     # ms, ship, eff, trimmed

mpl.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 300,
    "xtick.direction": "out", "ytick.direction": "out"})
CA, CB, CM = "#2166ac", "#b2182b", "#4d4d4d"
fig, axes = plt.subplots(1, 3, figsize=(11, 3.7))

# panel a: alpha sweep
ax = axes[0]
ax.fill_between(A[:, 0], A[:, 2]*100, A[:, 3]*100, color=CB, alpha=.15, lw=0)
ax.plot(A[:, 0], A[:, 1]*100, "s-", color=CB, ms=3.5, label="original census (never splits)")
ax.fill_between(A[:, 0], A[:, 5]*100, A[:, 6]*100, color=CA, alpha=.15, lw=0)
ax.plot(A[:, 0], A[:, 4]*100, "o-", color=CA, ms=3.5, label="patched census (trim splits)")
ax.set_xlabel(r"rep-territory alignment  $\alpha$   (1 = B territories copy A's)")
ax.set_ylabel("opportunity in 1-1 pair components (%)")
ax.legend(frameon=False, loc="upper left")
ax.text(.03, .70, "band: min-max over 8 seeds", transform=ax.transAxes, fontsize=6.5)
ax.set_title("Any imperfection reads as fully dense\nunless trimming splits", loc="left")

# panel b: min_share audit on the sliver scenario
ax = axes[1]
ax.axhline(100, color="black", lw=.6, ls=":")
ax.text(.02, .955, "ground truth: 100% 1-1 by construction", transform=ax.transAxes,
        fontsize=6.5, va="top")
ax.plot(U[:, 0]*100, U[:, 1]*100, "s-", color=CB, ms=3.5, label="original: threshold is decorative")
ax.plot(U[:, 0]*100, U[:, 2]*100, "o-", color=CA, ms=3.5, label="patched: verdict recovered")
ax.plot(U[:, 0]*100, U[:, 3]*100, "^--", color=CM, ms=3.5, lw=1, label="opportunity orphaned by trim")
ax.axvline(2, color=CM, lw=.7, ls="--")
ax.text(2.2, 40, "shipped default 2%", fontsize=6.5, rotation=90, va="bottom", color=CM)
ax.set_xlabel("min_share threshold (% of component opportunity)")
ax.set_ylabel("opportunity in 1-1 pair components (%)")
ax.legend(frameon=False, loc="center right", fontsize=6.2)
ax.set_title("The 2% default did nothing;\nafter the patch it is a real dial", loc="left")

# panel c: rho dial -> realized corr
ax = axes[2]
rhos = np.array([-0.5, -0.25, 0.0, 0.25, 0.5, 0.7, 0.9, 1.0])
means = np.array([0.049, 0.210, 0.358, 0.503, 0.645, 0.755, 0.869, 0.926])
los = np.array([-0.428, -0.370, -0.230, -0.005, 0.312, 0.579, 0.783, 0.902])
his = np.array([0.389, 0.562, 0.675, 0.776, 0.847, 0.880, 0.919, 0.959])
ax.fill_between(rhos, los, his, color=CA, alpha=.15, lw=0)
ax.plot(rhos, means, "o-", color=CA, ms=3.5)
ax.axhline(0, color="black", lw=.6)
ax.axhline(0.685, color=CB, lw=.7, ls="--")
ax.text(-.48, 0.705, "zip50 instance (+0.685)", fontsize=6.5, color=CB)
ax.set_xlabel(r"book-correlation dial  rho_books")
ax.set_ylabel(r"realized corr$(A_z, B_z)$")
ax.text(.03, .05, "band: min-max over 8 seeds\nkill criterion 4 lives near zero",
        transform=ax.transAxes, fontsize=6.5, va="bottom")
ax.set_title("The dial spans separate to contested", loc="left")

for a, l in zip(axes, "abc"):
    a.text(-.14, 1.14, l, transform=a.transAxes, fontsize=11, fontweight="bold", va="top")
fig.tight_layout()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "census_stress.png")
fig.savefig(out, bbox_inches="tight")
r = fig.canvas.get_renderer()
ts = [(t, t.get_window_extent(r)) for t in fig.findobj(mpl.text.Text) if t.get_text().strip() and t.get_visible()]
ov = [(x.get_text(), y.get_text()) for i, (x, bx) in enumerate(ts) for y, by in ts[i+1:] if bx.overlaps(by)]
print("text overlaps:", len(ov))
for a, b in ov: print("  ", repr(a), "<->", repr(b))
