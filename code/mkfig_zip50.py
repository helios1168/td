"""
mkfig_zip50.py -- regenerates the paper's Section 5 worked instance results and the
three d-dependent figures (nash_solution.png, zip50_nash_milp.png,
nash_contestability.png), all at the current d=(0,0) disagreement point.

zip50_distributions.png is NOT regenerated here: every one of its panels (M_z, A_z,
B_z, net headroom, sales share, utility ratio) is a function of the raw instance data
only, not of the disagreement point, so it is unaffected by the d=0 migration.

Adjacency: Delaunay triangulation on the zip centroids Z. This reproduces the paper's
stated "50 zips and 132 adjacency edges" exactly, and is the natural graph for a
Voronoi-cell map (Delaunay is the Voronoi neighbor dual).

Run from the repo root: .venv/bin/python3 code/mkfig_zip50.py
Prints every number the paper's Section 5, Section 6, Contestability, Exact parameter
breakpoints, Opportunity balance, and Appendix A/B sections need, then writes the three
PNGs into figures/.
"""
import sys, os, pickle, time
import numpy as np
import networkx as nx
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.spatial import Delaunay

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "battery", "code"))
import territory as T
import districting as D
from mapviz import draw_zip_map, draw_zip_heatmap, zip_polygons, MAP_RC

FIGDIR = os.path.join(ROOT, "figures")

import zip50  # noqa: E402  (executes and writes /tmp/z50.pkl, seed=17, deterministic)

d = pickle.load(open("/tmp/z50.pkl", "rb"))
Z, Az, Bz, Mz = d["Z"], d["Az"], d["Bz"], d["Mz"]
th, lam = d["th"], d["lam"]
c1, c2 = 1 - lam, th * (1 - lam)
ua, ub = c1 * Az + c2 * Bz + lam * Mz, c2 * Az + c1 * Bz + lam * Mz
Amax, Bmax = ua.sum(), ub.sum()
n = 50

G = nx.Graph()
for i in range(n):
    G.add_node(i, rep_a=0, rep_b=0, A=float(Az[i]), B=float(Bz[i]), M=float(Mz[i]),
              pos=tuple(Z[i]))
tri = Delaunay(Z)
edges = set()
for simplex in tri.simplices:
    for a in range(3):
        for b in range(a + 1, 3):
            edges.add(tuple(sorted((int(simplex[a]), int(simplex[b])))))
G.add_edges_from(edges)
nodes = list(G.nodes())
nE = G.number_of_edges()
polys = zip_polygons(G)

print("=" * 70)
print(f"instance: n={n}  Sa={Az.sum():.4f}  Sb={Bz.sum():.4f}  M={Mz.sum():.4f}  "
      f"graph: {nE} edges")
print(f"Amax={Amax:.4f}  Bmax={Bmax:.4f}")

# ---------------------------------------------------------------- Section 5: solution
r_exact = T.nash_exact(Az, Bz, Mz, th, lam)
to_a_exact = {nodes[i] for i in range(n) if r_exact["x"][i]}
k_exact = int(r_exact["x"].sum())

t = T.prefix_table(G, nodes, th, lam)
prod_pre = t["ga"] * t["gb"]
k_pref = int(np.argmax(np.where((t["ga"] > 0) & (t["gb"] > 0), prod_pre, -np.inf)))
to_a_pref = {t["nodes"][i] for i in t["order"][:k_pref]}
shortfall = (r_exact["product"] - prod_pre[k_pref]) / r_exact["product"]

M_a = sum(Mz[i] for i in to_a_exact)
M_b = Mz.sum() - M_a

print("\n--- Section 5: fifty-zip instance ---")
print(f"exact:  k={k_exact}  g_a={r_exact['g_a']:.4f}  g_b={r_exact['g_b']:.4f}  "
      f"product={r_exact['product']:.5f}")
print(f"prefix: k={k_pref}  g_a={t['ga'][k_pref]:.4f}  g_b={t['gb'][k_pref]:.4f}  "
      f"product={prod_pre[k_pref]:.5f}  shortfall={shortfall:.2e}  "
      f"different_allocation={to_a_exact != to_a_pref}")
print(f"a receives {k_exact} zips, {M_a/Mz.sum()*100:.1f}% of opportunity  "
      f"(M_a={M_a:.2f} M_b={M_b:.2f} imbalance={abs(M_a-M_b)/Mz.sum()*100:.1f}%)")

# ---------------------------------------------------------------- Appendix A: criteria
rows = T.compare_criteria(G, nodes, th, lam)
print("\n--- Appendix A: other solution concepts ---")
for name, row in rows.items():
    print(f"  {name:20s} k={row['k']:3d}  g_a={row['g_a']:.4f}  g_b={row['g_b']:.4f}  "
          f"prod={row['product']:.3f}  min_g={row['min_g']:.4f}  ks_gap={row['ks_gap']:.4f}  "
          f"M_a_share={row['M_a_share']*100:.1f}%")

# ---------------------------------------------------------------- Section 6: contiguity
rep_unc = T.contiguity_report(G, nodes, to_a_exact)
print("\n--- Section 6: contiguity ---")
print(f"unconstrained pieces a/b: {rep_unc['components_a']}/{rep_unc['components_b']}  "
      f"sizes_a={rep_unc['sizes_a']} sizes_b={rep_unc['sizes_b']}")

contig_rows = []
for rho in (2e-3, 2e-4, 1e-5):
    t0 = time.time()
    res = D.solve_contiguous_nash(G, nodes, th, lam, rho=rho, verbose=False)
    dt = time.time() - t0
    res["dt"] = dt
    res["rho"] = rho
    rep = T.contiguity_report(G, nodes, res["to_a"])
    res["pieces_a"], res["pieces_b"] = rep["components_a"], rep["components_b"]
    contig_rows.append(res)
    print(f"  rho={rho:.0e}: product={res['product']:.4f}  perimeter={res['perimeter']}  "
          f"({res['perimeter']/nE*100:.1f}% of {nE})  iters={res['iters']}  "
          f"time={dt:.2f}s  pieces={res['pieces_a']}/{res['pieces_b']}  "
          f"zips_to_a={res['k']}")
ref_contig = contig_rows[0]  # rho=2e-3, the reference compactness weight used throughout
best_contig = max(contig_rows, key=lambda r: r["product"])
worst_contig = min(contig_rows, key=lambda r: r["product"])
price_lo = (r_exact["product"] - best_contig["product"]) / r_exact["product"] * 100
price_hi = (r_exact["product"] - worst_contig["product"]) / r_exact["product"] * 100
print(f"  price of contiguity: {price_lo:.2f}% -- {price_hi:.2f}% of the bargaining product")

# ---------------------------------------------------------------- Contestability
print("\n--- Contestability ---")
t0 = time.time()
contest = T.contestability(G, nodes, th, lam, criterion="nash")
print(f"  computed in {time.time()-t0:.0f}s")
stakes = np.array([contest[nd]["stake"] for nd in nodes])
doubts = np.array([contest[nd]["doubt"] for nd in nodes])
cons = np.array([contest[nd]["contestability"] for nd in nodes])
order_c = np.argsort(-cons)
print(f"  stake range: [{stakes.min():.4f}, {stakes.max():.4f}]")
for rank, i in enumerate(order_c[:5], 1):
    nd = nodes[i]
    print(f"  {rank}. zip {nd}: stake={contest[nd]['stake']:.4f} doubt={contest[nd]['doubt']:.4f} "
          f"contestability={contest[nd]['contestability']:.4f}")
top5_share = cons[order_c[:5]].sum() / cons.sum()
print(f"  top 5 share of total contestability: {top5_share*100:.0f}%")

# ---------------------------------------------------------------- breakpoints & balance
def k_at(lam_, th_=th):
    c1_, c2_ = 1 - lam_, th_ * (1 - lam_)
    ua_, ub_ = c1_ * Az + c2_ * Bz + lam_ * Mz, c2_ * Az + c1_ * Bz + lam_ * Mz
    order_ = np.argsort(-(ua_ / ub_))
    ga_ = np.concatenate([[0.0], np.cumsum(ua_[order_])])
    gb_ = np.concatenate([[ub_.sum()], ub_.sum() - np.cumsum(ub_[order_])])
    prod_ = ga_ * gb_
    kk = int(np.argmax(np.where((ga_ > 0) & (gb_ > 0), prod_, -np.inf)))
    return kk, Mz[order_[:kk]].sum()

lams_grid = np.linspace(0.001, 0.999, 8000)
ks_grid = np.array([k_at(l)[0] for l in lams_grid])
distinct = sorted(set(ks_grid.tolist()))
changes = np.where(np.diff(ks_grid) != 0)[0]
bpoints = lams_grid[changes]
k30, _ = k_at(0.30)
i30 = int(np.searchsorted(lams_grid, 0.30))
lo_idx = i30
while lo_idx > 0 and ks_grid[lo_idx - 1] == k30:
    lo_idx -= 1
hi_idx = i30
while hi_idx < len(ks_grid) - 1 and ks_grid[hi_idx + 1] == k30:
    hi_idx += 1
flat_lo, flat_hi = lams_grid[lo_idx], lams_grid[hi_idx]
distinct_in_range = sorted(set(ks_grid[(lams_grid >= 0.02) & (lams_grid <= 0.90)].tolist()))
bpoints_in_range = bpoints[(bpoints >= 0.02) & (bpoints <= 0.90)]
print("\n--- Exact parameter breakpoints ---")
print(f"  distinct k over lambda in [0.02,0.90]: {distinct_in_range}  "
      f"breakpoints at {bpoints_in_range}")
print(f"  distinct k over full [0.001,0.999]: {distinct}  all breakpoints at {bpoints}")
print(f"  k at lambda=0.30: {k30}  contiguous flat interval containing it: "
      f"[{flat_lo:.4f}, {flat_hi:.4f}]")

print("\n--- Opportunity balance ---")
for l in (0.02, 0.21, 0.30, 0.70, 0.90):
    kk, Ma_ = k_at(l)
    Mb_ = Mz.sum() - Ma_
    print(f"  lambda={l:.2f}: k={kk}  M_a={Ma_:.2f}  imbalance={abs(Ma_-Mb_)/Mz.sum()*100:.1f}%")

# ---------------------------------------------------------------- Appendix B: 400k check
print("\n--- Appendix B: prefix property on 400k random subsets ---")
order_full = np.argsort(-(ua / ub))
ga_pre = np.concatenate([[0.0], np.cumsum(ua[order_full])])
gb_pre = np.concatenate([[ub.sum()], ub.sum() - np.cumsum(ub[order_full])])
rng = np.random.default_rng(0)
N = 400_000
best = dict(util=-np.inf, nash=-np.inf, egal=-np.inf, eqgain=np.inf, ks=np.inf)
for _ in range(N):
    mask = rng.random(n) < 0.5
    ga_ = ua[mask].sum(); gb_ = ub[~mask].sum()
    if ga_ <= 0 or gb_ <= 0:
        continue
    best["util"] = max(best["util"], ga_ + gb_)
    best["nash"] = max(best["nash"], ga_ * gb_)
    best["egal"] = max(best["egal"], min(ga_, gb_))
    best["eqgain"] = min(best["eqgain"], abs(ga_ - gb_))
    best["ks"] = min(best["ks"], abs(ga_ / Amax - gb_ / Bmax))
bp_util = max(ga_pre[k] + gb_pre[k] for k in range(n + 1))
bp_nash = max((ga_pre[k] * gb_pre[k]) for k in range(n + 1) if ga_pre[k] > 0 and gb_pre[k] > 0)
bp_egal = max(min(ga_pre[k], gb_pre[k]) for k in range(n + 1))
bp_eqgain = min(abs(ga_pre[k] - gb_pre[k]) for k in range(n + 1))
bp_ks = min(abs(ga_pre[k] / Amax - gb_pre[k] / Bmax) for k in range(n + 1))
for name, bp, br, hilo in (("utilitarian", bp_util, best["util"], "max"),
                          ("nash", bp_nash, best["nash"], "max"),
                          ("egalitarian", bp_egal, best["egal"], "max"),
                          ("equal gain", bp_eqgain, best["eqgain"], "min"),
                          ("KS", bp_ks, best["ks"], "min")):
    holds = (bp >= br) if hilo == "max" else (bp <= br)
    print(f"  {name:12s} best prefix {bp:.5f}  best random {br:.5f}  "
          f"{'prefix holds' if holds else 'VIOLATED'}")

# ================================================================== FIGURES
mpl.rcParams.update(MAP_RC)
CA, CB = "#2166ac", "#b2182b"

# ---------------------------------------------------- Figure: nash_solution.png
fig, axes = plt.subplots(1, 3, figsize=(11, 3.7))
fig.suptitle(f"Nash bargaining solution -- 50 ZCTAs, $d=(0,0)$, "
            f"$\\theta$={th}, $\\lambda$={lam}, net headroom")

ax = axes[0]
draw_zip_map(ax, G, lambda z: CA if z in to_a_exact else CB,
            f"Nash allocation -- {k_exact} zips to A, {M_a/Mz.sum()*100:.0f}% of opportunity",
            legend=[Line2D([], [], marker="s", ls="", color=CA, label="to A"),
                    Line2D([], [], marker="s", ls="", color=CB, label="to B")],
            polys=polys, metro_pos=d["metros"])

ax = axes[1]
ks_axis = np.arange(n + 1)
ax.plot(ks_axis, prod_pre, "-o", ms=3, color="#2166ac")
ax.axvline(k_exact, color="#b2182b", ls="--", label=f"Nash optimum k={k_exact}")
ax.set_xlabel("prefix size $k$ (zips to A, in utility-ratio order)")
ax.set_ylabel("bargaining product $g_ag_b$")
ax.set_title("the whole optimisation: max product over prefixes", loc="left")
ax.legend(frameon=False, loc="lower center")

ax = axes[2]
lams_fine = np.linspace(0.001, 0.5, 600)
ks_fine = np.array([k_at(l)[0] for l in lams_fine])
ax.step(lams_fine, ks_fine, where="post", color="#2166ac")
ax.axvspan(flat_lo, min(flat_hi, 0.5), color="orange", alpha=0.25,
          label=f"flat: [{flat_lo:.3f}, {flat_hi:.3f}]")
ax.axvline(lam, color="black", ls=":", label=f"$\\lambda$={lam:.2f}")
ax.set_xlabel("$\\lambda$ (headroom credit)")
ax.set_ylabel("zips to A")
ax.set_title("Nash allocation is piecewise constant in $\\lambda$", loc="left")
ax.legend(frameon=False, fontsize=6)

fig.tight_layout()
fig.savefig(os.path.join(FIGDIR, "nash_solution.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------- Figure: zip50_nash_milp.png
fig, axes = plt.subplots(1, 3, figsize=(11, 3.7))
fig.suptitle("Nash bargaining on 50 ZCTAs -- unconstrained, contiguous, and the bargaining set")

ax = axes[0]
draw_zip_map(ax, G, lambda z: CA if z in to_a_exact else CB,
            f"Nash, unconstrained -- pieces A/B = {rep_unc['components_a']}/{rep_unc['components_b']}\n"
            f"product {r_exact['product']:.4f}",
            polys=polys)
for u, v in G.edges():
    pu, pv = G.nodes[u]["pos"], G.nodes[v]["pos"]
    ax.plot([pu[0], pv[0]], [pu[1], pv[1]], color="black", lw=0.3, alpha=0.4, zorder=3)

ax = axes[1]
draw_zip_map(ax, G, lambda z: CA if z in ref_contig["to_a"] else CB,
            f"Nash + contiguity (MILP) -- pieces {ref_contig['pieces_a']}/{ref_contig['pieces_b']}\n"
            f"product {ref_contig['product']:.4f}, perimeter {ref_contig['perimeter']} "
            f"($\\rho$={ref_contig['rho']:.0e})",
            polys=polys)

ax = axes[2]
ax.plot(ga_pre, gb_pre, "-o", ms=3, color="gray", label="prefix frontier")
gg = np.linspace(0.5, max(ga_pre.max(), gb_pre.max()), 200)
for lvl in (r_exact["product"] * 0.9, r_exact["product"], r_exact["product"] * 1.1):
    ax.plot(gg, lvl / gg, ":", color="#b2182b", lw=0.8)
ax.plot([], [], ":", color="#b2182b", lw=0.8, label="Nash product level curves")
ax.plot(r_exact["g_a"], r_exact["g_b"], "*", ms=16, color="#2166ac", label="Nash unconstrained")
ax.plot(ref_contig["g_a"], ref_contig["g_b"], "D", ms=10, color="orange",
       markeredgecolor="black", label="Nash + contiguity")
ks_row = rows["ks"]
ax.plot(ks_row["g_a"], ks_row["g_b"], "s", ms=9, color="purple", label="Kalai--Smorodinsky")
util_row = rows["utilitarian"]
ax.plot(util_row["g_a"], util_row["g_b"], "^", ms=9, color="black", label="utilitarian")
ax.set_xlabel("$g_a$"); ax.set_ylabel("$g_b$")
ax.set_title("Bargaining set and the Nash point", loc="left")
ax.legend(frameon=False, fontsize=6, loc="upper right")
ax.set_xlim(0, ga_pre.max() * 1.05); ax.set_ylim(0, gb_pre.max() * 1.05)

fig.tight_layout()
fig.savefig(os.path.join(FIGDIR, "zip50_nash_milp.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------- Figure: nash_contestability.png
fig, axes = plt.subplots(1, 3, figsize=(11, 3.7))
fig.suptitle("Contestability under the Nash solution")

ax = axes[0]
values = {nodes[i]: cons[i] for i in range(n)}
draw_zip_heatmap(ax, G, values, "Contestability = stake $\\times$ doubt\ncyan: Nash boundary",
                 cmap="YlOrBr", polys=polys)
from scipy.spatial import Voronoi as _Voronoi  # noqa: E402
_vor = _Voronoi(Z)
for (p1, p2), (v1, v2) in zip(_vor.ridge_points, _vor.ridge_vertices):
    if v1 < 0 or v2 < 0:
        continue
    if (int(p1) in to_a_exact) != (int(p2) in to_a_exact):
        a_, b_ = _vor.vertices[v1], _vor.vertices[v2]
        ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color="cyan", lw=1.8, zorder=3)
for i in order_c[:5]:
    nd = nodes[i]
    p = G.nodes[nd]["pos"]
    ax.plot(*p, "o", ms=12, mfc="none", mec="lime", mew=1.6, zorder=4)
    ax.annotate(str(nd), p, fontsize=6, ha="center", va="center", zorder=5)

ax = axes[1]
stake_med, doubt_med = np.median(stakes), np.median(doubts)
colors_q = np.where((stakes >= stake_med) & (doubts >= doubt_med), "#b2182b",
           np.where((stakes >= stake_med) & (doubts < doubt_med), "#2166ac",
           np.where((stakes < stake_med) & (doubts >= doubt_med), "orange", "lightgray")))
ax.scatter(doubts, stakes, s=cons / cons.max() * 300 + 15, c=colors_q,
          edgecolor="black", linewidth=0.3, alpha=0.85)
ax.axvline(doubt_med, color="black", ls="--", lw=0.8)
ax.axhline(stake_med, color="black", ls="--", lw=0.8)
for i in order_c[:5]:
    ax.annotate(str(nodes[i]), (doubts[i], stakes[i]), fontsize=7, fontweight="bold")
ax.set_xlabel("doubt -- flip rate under parameter + data uncertainty")
ax.set_ylabel("stake  $u_a(z)/g_a + u_b(z)/g_b$")
ax.set_title("what to argue about (median split)", loc="left")
handles = [Line2D([], [], marker="o", ls="", color="#b2182b", label="high stake, high doubt"),
          Line2D([], [], marker="o", ls="", color="#2166ac", label="high stake, low doubt"),
          Line2D([], [], marker="o", ls="", color="orange", label="low stake, high doubt"),
          Line2D([], [], marker="o", ls="", color="lightgray", label="low stake, low doubt")]
ax.legend(handles=handles, frameon=False, fontsize=6, loc="upper left")

ax = axes[2]
top16 = order_c[:16]
ylabels = [f"zip {nodes[i]}" for i in top16]
y = np.arange(len(top16))
ax.barh(y, -doubts[top16], color="#b2182b", label="doubt")
ax.barh(y, stakes[top16] / stakes[top16].max(), color="#2166ac", label="stake (scaled)")
ax.plot(cons[top16] / cons[top16].max(), y, "o-", color="black", ms=4, label="contestability")
ax.set_yticks(y); ax.set_yticklabels(ylabels, fontsize=6)
ax.invert_yaxis()
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("$\\leftarrow$ doubt          stake / contestability $\\rightarrow$")
ax.set_title("decomposition, top 16", loc="left")
ax.legend(frameon=False, fontsize=6, loc="lower right")

fig.tight_layout()
fig.savefig(os.path.join(FIGDIR, "nash_contestability.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

print("\nfigures written to", FIGDIR)
