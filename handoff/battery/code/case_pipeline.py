"""
case_pipeline.py -- one synthetic case end-to-end, with the 3-stage figure.

Stages, per instance:
  1. pre-merger  : rep_a / rep_b territory maps + book distributions
  2. nash        : census -> per-pair exact Nash (territory.nash_exact via solve)
  3. contiguous  : districting.solve_contiguous_nash per pair (hard contiguity + rho)

Dense components: solved pair-by-pair over each pair's overlap zips (the two-player
theory does NOT compose there -- the figure labels this caveat) so the maps stay
informative; zips whose pair was not solved keep status quo (rep_a keeps its zip? --
no: unsolved zips are marked 'unresolved' and drawn grey).

Usage:
  python3 case_pipeline.py <case.json>
  case.json: {"name": ..., "scenario": "S1_aligned" | null, "overrides": {...},
              "n": 200, "seed": 1, "rho": 2e-3, "respect_state": false,
              "min_share": 0.02, "outdir": "..."}
Writes <outdir>/<name>.png and <outdir>/<name>.json (metrics).
"""
from __future__ import annotations
import json, sys, time, itertools
import numpy as np, networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import synth, territory as T, districting as D
from mapviz import draw_zip_map, draw_zip_heatmap, zip_polygons, MAP_RC

# same clean-figure conventions as mkfig_census.py, so every battery figure and
# the census-stress figure read as one family (spines off, small print, no chartjunk)
plt.rcParams.update(MAP_RC)

CA = plt.cm.tab10  # A-rep colors: tab10 indices 0..
CB = plt.cm.Set2   # B-rep colors


def pair_solves(G, min_share=0.02, theta=0.40, lam=0.30):
    """Census, then exact Nash per (rep_a, rep_b) overlap pair worth solving.

    Returns census rows, and per-pair dicts with zips, solve result, dense flag.
    For a 1-1 component the pair IS the component. For a dense component we solve
    every strong pair inside it on that pair's own overlap zips -- an illustration,
    not a fair division (two-player fairness does not compose across a dense blob).
    """
    cen = T.census(G, min_share=min_share)
    O = T.overlap_graph(G)
    out = []
    for row in cen:
        dense = not row["shape"].startswith("1-1")
        if not dense:
            pairs = [(row["reps_a"][0][1], row["reps_b"][0][1])]
        else:
            Mc = row["M"]
            pairs = []
            for u in row["reps_a"]:
                for v in row["reps_b"]:
                    if O.has_edge(u, v) and O[u][v]["M"] >= min_share * Mc:
                        pairs.append((u[1], v[1]))
        for ra, rb in pairs:
            zips = T.zips_for_pair(G, ra, rb)
            if len(zips) < 4:
                continue
            t0 = time.time()
            res = T.solve(G, zips, "nash", theta=theta, lam=lam)
            res["solve_s"] = time.time() - t0
            # prefix-fallback results (exact solver hit iteration limit) lack
            # 'product'; fill it in so plots/metrics stay uniform, and keep the
            # exact flag so the fallback is reported honestly.
            res.setdefault("product", res["g_a"] * res["g_b"])
            out.append(dict(ra=ra, rb=rb, zips=zips, res=res, dense=dense,
                            comp_share=row["share"]))
    return cen, out


def contiguous_solves(G, pairs, rho=2e-3, respect_state=False,
                      theta=0.40, lam=0.30):
    for p in pairs:
        t0 = time.time()
        c = D.solve_contiguous_nash(G, p["zips"], theta=theta, lam=lam, rho=rho,
                                    respect_state=respect_state, verbose=False)
        c["solve_s"] = time.time() - t0
        p["cont"] = c
    return pairs


# ------------------------------------------------------------------- plotting
# _draw_map used to scatter a dot per zip and join Delaunay neighbours with grey
# lines -- a node-link graph. draw_zip_map (mapviz.py) instead fills each zip's
# Voronoi cell, so a battery figure reads like an actual ZCTA choropleth: solid
# colored parcels with thin white seams. Geometry (`polys`) is computed once per
# instance and reused across all four map panels in a figure.
def _draw_map(ax, G, color_of, title, legend=None, polys=None, metro_pos=None):
    return draw_zip_map(ax, G, color_of, title, legend=legend, polys=polys,
                        fontsize=9, metro_pos=metro_pos)


def make_figure(G, cen, pairs, meta, path):
    na = G.graph["params"]["n_rep_a"]; nb = G.graph["params"]["n_rep_b"]
    ca = {r: CA(r % 10) for r in range(na)}
    cb = {r: CB(r % 8) for r in range(nb)}
    solved = {}          # zip -> (firm, rep) after nash
    solved_c = {}        # after contiguity
    for p in pairs:
        for z in p["zips"]:
            solved[z] = ("A", p["ra"]) if z in p["res"]["to_a"] else ("B", p["rb"])
            ok = p.get("cont", {}).get("status") == "optimal"
            if ok:
                solved_c[z] = ("A", p["ra"]) if z in p["cont"]["to_a"] else ("B", p["rb"])

    def col_nash(book):
        def f(z):
            if z not in book: return (0.9, 0.9, 0.9, 1.0)
            firm, r = book[z]
            return ca[r] if firm == "A" else cb[r]
        return f

    fig = plt.figure(figsize=(13, 16.6))
    gs = fig.add_gridspec(4, 3, hspace=0.32, wspace=0.12,
                          width_ratios=[1, 1, 0.95],
                          top=0.965, bottom=0.02, left=0.035, right=0.98)

    # geometry is identical across all map panels (same instance) -- build the
    # Voronoi cells once and reuse them, rather than recomputing per panel
    polys = zip_polygons(G)
    # synth.py's Gaussian-mixture density centers -- the closest analogue this
    # synthetic geography has to real metropolitan cores. Absent on graphs built
    # before this was added to G.graph (backward compat: draw fns treat None/[]
    # as "no markers").
    metro_pos = G.graph.get("metros")

    # -- row 1: pre-merger --------------------------------------------------
    axA = fig.add_subplot(gs[0, 0]); axB = fig.add_subplot(gs[0, 1])
    _draw_map(axA, G, lambda z: ca[G.nodes[z]["rep_a"]],
              f"pre-merger: firm A territories ({na} reps)",
              legend=[Line2D([], [], marker="o", ls="", color=ca[r], label=f"A{r}")
                      for r in range(na)], polys=polys, metro_pos=metro_pos)
    _draw_map(axB, G, lambda z: cb[G.nodes[z]["rep_b"]],
              f"pre-merger: firm B territories ({nb} reps)",
              legend=[Line2D([], [], marker="o", ls="", color=cb[r], label=f"B{r}")
                      for r in range(nb)], polys=polys, metro_pos=metro_pos)
    axD = fig.add_subplot(gs[0, 2])
    A = np.array([G.nodes[z]["A"] for z in G]); B = np.array([G.nodes[z]["B"] for z in G])
    Mv = np.array([G.nodes[z]["M"] for z in G])
    axD.scatter(A, B, s=8 + 50 * Mv / Mv.max(), alpha=0.55, c="#4878cf",
                edgecolors="none")
    axD.set_xlabel("$A_z$", fontsize=8); axD.set_ylabel("$B_z$", fontsize=8)
    axD.tick_params(labelsize=7)
    axD.set_title(f"books: corr(A,B)={G.graph['corr_AB']:+.2f}   "
                  f"$S_a$={G.graph['Sa']:.1f} $S_b$={G.graph['Sb']:.1f}\n"
                  f"size $\\propto M_z$;  sat={G.graph['params']['saturation']}",
                  fontsize=8)

    # -- row 2: nash --------------------------------------------------------
    axN = fig.add_subplot(gs[1, 0])
    n11 = sum(1 for r in cen if r["shape"].startswith("1-1"))
    share11 = sum(r["share"] for r in cen if r["shape"].startswith("1-1"))
    _draw_map(axN, G, col_nash(solved),
              f"exact Nash per overlap pair  ({len(pairs)} pairs solved)\n"
              f"census: {len(cen)} components, 1-1 opp share {share11:.0%}",
              polys=polys, metro_pos=metro_pos)
    axG = fig.add_subplot(gs[1, 1])
    labels = [f"A{p['ra']}/B{p['rb']}" + ("*" if p["dense"] else "") for p in pairs]
    gav = [p["res"]["g_a"] for p in pairs]; gbv = [p["res"]["g_b"] for p in pairs]
    xpos = np.arange(len(pairs))
    axG.bar(xpos - 0.18, gav, 0.36, color="#4878cf", label="$g_a$")
    axG.bar(xpos + 0.18, gbv, 0.36, color="#6acc65", label="$g_b$")
    axG.set_xticks(xpos, labels, fontsize=7, rotation=30)
    axG.tick_params(labelsize=7); axG.legend(fontsize=7, frameon=False)
    axG.set_title("gains per pair (vs $d=(0,0)$: $g$ = bundle utility)"
                  + ("   * = inside dense comp" if any(p["dense"] for p in pairs) else ""),
                  fontsize=8)
    axT = fig.add_subplot(gs[1, 2]); axT.axis("off")
    lines = ["pair      k   product  gap      it  s", "-" * 40]
    for p, lb in zip(pairs, labels):
        r = p["res"]
        lines.append(f"{lb:<9} {r['k']:>2}  {r['product']:>7.3f}  "
                     f"{r.get('bound_gap', float('nan')):.1e}  {r.get('iters', 0):>2}  "
                     f"{r['solve_s']:.2f}")
    axT.text(0, 1, "\n".join(lines), family="monospace", fontsize=7, va="top")
    axT.set_title("Nash certificates", fontsize=8)

    # -- row 3: contiguous --------------------------------------------------
    axC = fig.add_subplot(gs[2, 0])
    rs = " (state borders respected)" if meta.get("respect_state") else ""
    _draw_map(axC, G, col_nash(solved_c),
              f"contiguous MINLP, rho={meta['rho']:g}{rs}", polys=polys,
              metro_pos=metro_pos)
    axP = fig.add_subplot(gs[2, 1])
    prod_n = [p["res"]["product"] for p in pairs]
    prod_c = [p["cont"].get("product", np.nan) for p in pairs]
    axP.bar(xpos - 0.18, prod_n, 0.36, color="#4878cf", label="Nash (free)")
    axP.bar(xpos + 0.18, prod_c, 0.36, color="#d65f5f", label="Nash + contiguity")
    axP.set_xticks(xpos, labels, fontsize=7, rotation=30)
    axP.tick_params(labelsize=7); axP.legend(fontsize=7, frameon=False)
    axP.set_title("bargaining product: cost of contiguity", fontsize=8)
    axR = fig.add_subplot(gs[2, 2]); axR.axis("off")
    lines = ["pair      pieces A/B->  per  cost%   s", "-" * 42]
    for p, lb in zip(pairs, labels):
        rep0 = T.contiguity_report(G, p["zips"], p["res"]["to_a"],
                                   respect_state=meta.get("respect_state", False))
        c = p["cont"]
        if c.get("status") == "optimal":
            cost = 100 * (1 - c["product"] / p["res"]["product"]) if p["res"]["product"] else np.nan
            lines.append(f"{lb:<9} {rep0['components_a']}/{rep0['components_b']}->1/1  "
                         f"{c['perimeter']:>3}  {cost:>5.2f}  {c['solve_s']:.1f}")
        else:
            lines.append(f"{lb:<9} {rep0['components_a']}/{rep0['components_b']}  "
                         f"{c.get('status', '?')}")
    axR.text(0, 1, "\n".join(lines), family="monospace", fontsize=7, va="top")
    axR.set_title("fragmentation before -> after; product cost", fontsize=8)

    # -- row 4: pointwise gains fields (heatmap) -----------------------------
    # u_a(z), u_b(z) are the summands g_a, g_b are built from (territory.py
    # _fields): the "value of this one zip" under the model, independent of any
    # particular assignment. Shading a zip by this value -- rather than by which
    # wholesaler it ended up with -- shows WHY the solves above put boundaries
    # where they did: g_a/g_b's constituent field, not just its outcome.
    theta_, lam_ = meta.get("theta", 0.40), meta.get("lam", 0.30)
    Az_ = np.array([G.nodes[z]["A"] for z in G]); Bz_ = np.array([G.nodes[z]["B"] for z in G])
    Mz_ = np.array([G.nodes[z]["M"] for z in G])
    c1_, c2_ = 1 - lam_, theta_ * (1 - lam_)
    ua_all = c1_ * Az_ + c2_ * Bz_ + lam_ * Mz_
    ub_all = c2_ * Az_ + c1_ * Bz_ + lam_ * Mz_
    nodes_ = list(G)
    ua_map = dict(zip(nodes_, ua_all.tolist()))
    ub_map = dict(zip(nodes_, ub_all.tolist()))
    vmax_u = float(max(ua_all.max(), ub_all.max()))

    axHa = fig.add_subplot(gs[3, 0]); axHb = fig.add_subplot(gs[3, 1])
    draw_zip_heatmap(axHa, G, ua_map,
                     "gains field $u_a(z)$: value of z to wholesaler A",
                     cmap="Blues", polys=polys, metro_pos=metro_pos,
                     vmin=0, vmax=vmax_u, fontsize=9)
    draw_zip_heatmap(axHb, G, ub_map,
                     "gains field $u_b(z)$: value of z to wholesaler B",
                     cmap="Greens", polys=polys, metro_pos=metro_pos,
                     vmin=0, vmax=vmax_u, fontsize=9)
    axHt = fig.add_subplot(gs[3, 2]); axHt.axis("off")
    axHt.text(0, 1,
        "u_a(z) = c1*A_z + c2*B_z + lam*M_z\n"
        "u_b(z) = c2*A_z + c1*B_z + lam*M_z\n"
        f"c1 = 1-lam = {c1_:.2f}    c2 = theta*(1-lam) = {c2_:.2f}\n"
        f"theta = {theta_:.2f}    lam = {lam_:.2f}\n\n"
        f"u_a(z):  min {ua_all.min():.3f}  mean {ua_all.mean():.3f}  "
        f"max {ua_all.max():.3f}\n"
        f"u_b(z):  min {ub_all.min():.3f}  mean {ub_all.mean():.3f}  "
        f"max {ub_all.max():.3f}\n\n"
        "shade = g_a / g_b's pointwise summand at z -- what z is\n"
        "worth to that wholesaler if assigned, before any solve.\n"
        "Both panels share one 0..max scale, so intensity is\n"
        "directly comparable across the pair.\n\n"
        "* = metropolitan cluster centers (synth.py 'metros')",
        family="monospace", fontsize=7, va="top")
    axHt.set_title("gains field summary", fontsize=8)

    fig.suptitle(meta["title"], fontsize=11, y=0.998)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------- main
def run_case(cfg):
    name = cfg["name"]
    kw = dict(synth.SCENARIOS[cfg["scenario"]]) if cfg.get("scenario") else {}
    kw.update(cfg.get("overrides", {}))
    G = synth.make_instance(n=cfg.get("n", 200), seed=cfg.get("seed", 1), **kw)
    probs = T.validate(G)
    cen, pairs = pair_solves(G, min_share=cfg.get("min_share", 0.02))
    contiguous_solves(G, pairs, rho=cfg.get("rho", 2e-3),
                      respect_state=cfg.get("respect_state", False))
    meta = dict(title=cfg.get("title", name), rho=cfg.get("rho", 2e-3),
                respect_state=cfg.get("respect_state", False))
    outdir = cfg.get("outdir", ".")
    make_figure(G, cen, pairs, meta, f"{outdir}/{name}.png")

    metrics = dict(
        name=name, params=G.graph["params"], corr_AB=G.graph["corr_AB"],
        Sa=G.graph["Sa"], Sb=G.graph["Sb"], Mtot=G.graph["Mtot"],
        validate=probs,
        census=[dict(shape=r["shape"], share=r["share"], M=r["M"]) for r in cen],
        pairs=[dict(ra=p["ra"], rb=p["rb"], n_zips=len(p["zips"]), dense=p["dense"],
                    nash=dict(k=p["res"]["k"], exact=p["res"].get("exact"),
                              g_a=p["res"]["g_a"], g_b=p["res"]["g_b"],
                              product=p["res"]["product"],
                              bound_gap=p["res"].get("bound_gap"),
                              iters=p["res"].get("iters"), s=p["res"]["solve_s"]),
                    cont=({k: p["cont"][k] for k in
                           ("status", "k", "g_a", "g_b", "product", "perimeter",
                            "n_edges", "iters")
                           if k in p["cont"]} | {"s": p["cont"]["solve_s"]}))
               for p in pairs])
    with open(f"{outdir}/{name}.json", "w") as f:
        json.dump(metrics, f, indent=1, default=float)
    return metrics


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    m = run_case(cfg)
    print(json.dumps({k: m[k] for k in ("name", "corr_AB", "validate")}, default=float))
    for p in m["pairs"]:
        print(f"  A{p['ra']}/B{p['rb']} n={p['n_zips']:>3} dense={p['dense']} "
              f"nash prod={p['nash']['product']:.3f} gap={p['nash']['bound_gap']} "
              f"cont={p['cont'].get('status')} cont_prod={p['cont'].get('product')}")
