"""
c8_rho_sweep.py -- case C8: the compactness frontier (trap 7).

rho prices boundary edges in solve_contiguous_nash and competes directly with
the Nash objective log g_a + log g_b. Sweep rho on the largest overlap pair of
S1_aligned(n=200, seed=1) and report product and perimeter together, against
the unconstrained exact Nash product as reference.

Writes:
  battery/figures/C8_rho_frontier.png
  battery/figures/C8_rho_frontier.json
"""
from __future__ import annotations
import json, os, sys, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "code"))
import synth, territory as T, districting as D
from mapviz import draw_zip_map, zip_polygons, MAP_RC

plt.rcParams.update(MAP_RC)

OUTDIR = os.path.join(ROOT, "battery", "figures")
RHOS = [0.0, 1e-4, 5e-4, 2e-3, 8e-3, 3e-2]
MAP_RHOS = [1e-4, 2e-3, 3e-2]

COL_A = "#4878cf"
COL_B = "#d65f5f"
COL_OUT = (0.88, 0.88, 0.88, 1.0)


def main():
    G = synth.scenario("S1_aligned", n=200, seed=1)
    ra, rb, edata = T.largest_pair(G)
    zips = T.zips_for_pair(G, ra, rb)
    print(f"largest pair: A{ra}/B{rb}  n_zips={len(zips)}  shared M={edata['M']:.2f}")

    # ---- unconstrained exact Nash reference ------------------------------
    t0 = time.time()
    ref = T.solve(G, zips, "nash")
    ref_s = time.time() - t0
    frag = T.contiguity_report(G, zips, ref["to_a"])
    ref_prod = ref["product"]
    print(f"unconstrained Nash: product={ref_prod:.5f} k={ref['k']} "
          f"iters={ref.get('iters')} gap={ref.get('bound_gap'):.1e} "
          f"pieces A/B={frag['components_a']}/{frag['components_b']}  {ref_s:.2f}s")

    # ---- rho sweep -------------------------------------------------------
    # NB: the solver's reported `perimeter` reads the y_e variables; at rho=0
    # those are unpriced (objective coefficient 0), so MILP leaves them at
    # arbitrary feasible values >= |x_i - x_j| and the report is meaningless
    # slack. Recompute the TRUE boundary-edge count from the assignment.
    H = G.subgraph(zips)

    def true_perimeter(to_a):
        return sum(1 for u, v in H.edges() if (u in to_a) != (v in to_a))

    rows, maps = [], {}
    for rho in RHOS:
        t0 = time.time()
        c = D.solve_contiguous_nash(G, zips, rho=rho, max_iter=40,
                                    time_limit=20.0, verbose=False)
        secs = time.time() - t0
        row = dict(rho=rho, status=c.get("status"),
                   product=c.get("product"),
                   perimeter=true_perimeter(c["to_a"]) if "to_a" in c else None,
                   perimeter_reported=c.get("perimeter"),
                   g_a=c.get("g_a"), g_b=c.get("g_b"), k=c.get("k"),
                   iters=c.get("iters"), secs=round(secs, 2))
        if row["product"] is not None:
            row["pct_below_ref"] = 100.0 * (1.0 - row["product"] / ref_prod)
        rows.append(row)
        if rho in MAP_RHOS and c.get("status") == "optimal":
            maps[rho] = c["to_a"]
        p = f"{row['product']:.5f}" if row["product"] is not None else "   --  "
        per = f"{row['perimeter']}" if row["perimeter"] is not None else "--"
        print(f"rho={rho:<7g} status={row['status']:<16} product={p} "
              f"perim={per:>3} (reported {row['perimeter_reported']}) "
              f"iters={row['iters']} secs={secs:.1f}")

    # ---- verification ----------------------------------------------------
    checks = []
    for r in rows:
        if r["product"] is not None and r["product"] > ref_prod + 1e-9:
            checks.append(f"product at rho={r['rho']:g} EXCEEDS unconstrained "
                          f"({r['product']:.6f} > {ref_prod:.6f})")
    ok = [r for r in rows if r["perimeter"] is not None]
    for r0, r1 in zip(ok, ok[1:]):
        if r1["perimeter"] > r0["perimeter"]:
            checks.append(f"perimeter increases {r0['rho']:g}->{r1['rho']:g} "
                          f"({r0['perimeter']} -> {r1['perimeter']})")
    print("verify:", "; ".join(checks) if checks else "all checks pass "
          "(products <= unconstrained, perimeter monotone non-increasing)")

    # ---- figure ----------------------------------------------------------
    fig = plt.figure(figsize=(13, 4.2))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.9, 1, 1, 1], wspace=0.15)

    axF = fig.add_subplot(gs[0, 0])
    fr = [r for r in rows if r["product"] is not None]
    per = [r["perimeter"] for r in fr]
    pro = [r["product"] for r in fr]
    axF.axhline(ref_prod, color="0.4", lw=1.0, ls="--",
                label=f"unconstrained Nash product = {ref_prod:.3f} "
                      f"({frag['components_a']}/{frag['components_b']} pieces)")
    axF.plot(per, pro, "-", color="0.7", lw=1.0, zorder=1)
    axF.scatter(per, pro, c=COL_A, s=45, zorder=2)
    seen = {}
    for r in fr:
        key = (r["perimeter"], round(r["product"], 6))
        dup = seen.get(key, 0); seen[key] = dup + 1
        dx = -34 if r is fr[0] else 7           # rho=0 sits rightmost: keep inside
        axF.annotate(f"rho={r['rho']:g}", (r["perimeter"], r["product"]),
                     textcoords="offset points", xytext=(dx, -9 - 11 * dup),
                     fontsize=8)
    missing = [r for r in rows if r["product"] is None]
    if missing:
        axF.text(0.02, 0.03,
                 "not on frontier: " + ", ".join(
                     f"rho={r['rho']:g} ({r['status']}, {r['iters'] or 40} it)"
                     for r in missing),
                 transform=axF.transAxes, fontsize=8, color=COL_B)
    axF.set_xlabel("perimeter (boundary edges)", fontsize=9)
    axF.set_ylabel("Nash product $g_a g_b$", fontsize=9)
    axF.tick_params(labelsize=8)
    axF.legend(fontsize=8, frameon=False, loc="lower right")
    axF.set_title(f"C8: product vs perimeter frontier, pair A{ra}/B{rb} "
                  f"({len(zips)} zips)", fontsize=10)

    # map panels: filled Voronoi cells (mapviz.draw_zip_map) instead of a scatter +
    # adjacency-edge node-link plot, so the pair's territory reads as a colored
    # region carved out of the full instance, the way a real ZCTA map would show it.
    # Geometry is identical across the three rho panels -- built once and reused.
    zipset = set(zips)
    polys = zip_polygons(G)
    metro_pos = G.graph.get("metros")
    for j, rho in enumerate(MAP_RHOS):
        ax = fig.add_subplot(gs[0, 1 + j])
        if rho in maps:
            to_a = maps[rho]
            def color_of(z, to_a=to_a):
                if z not in zipset: return COL_OUT
                return COL_A if z in to_a else COL_B
            r = next(r for r in rows if r["rho"] == rho)
            title = (f"rho={rho:g}\nproduct={r['product']:.3f}  "
                     f"perim={r['perimeter']}")
        else:
            color_of = lambda z: COL_OUT
            title = f"rho={rho:g}\n(no optimal allocation)"
        legend = None
        if j == 0:
            legend = [
                Line2D([], [], marker="o", ls="", color=COL_A, label=f"A{ra}"),
                Line2D([], [], marker="o", ls="", color=COL_B, label=f"B{rb}"),
                Line2D([], [], marker="o", ls="", color=COL_OUT, label="out of pair")]
        draw_zip_map(ax, G, color_of, title, legend=legend, polys=polys, fontsize=8,
                    metro_pos=metro_pos)

    fig.suptitle("C8 -- compactness frontier: rho competes with the Nash objective "
                 "(trap 7)", fontsize=11, y=1.00)
    png = f"{OUTDIR}/C8_rho_frontier.png"
    fig.savefig(png, dpi=150, bbox_inches="tight")
    plt.close(fig)

    out = dict(case="C8", scenario="S1_aligned", n=200, seed=1,
               pair=dict(ra=ra, rb=rb, n_zips=len(zips)),
               unconstrained=dict(product=ref_prod, k=ref["k"],
                                  g_a=ref["g_a"], g_b=ref["g_b"],
                                  iters=ref.get("iters"),
                                  bound_gap=ref.get("bound_gap"), secs=round(ref_s, 2),
                                  components_a=frag["components_a"],
                                  components_b=frag["components_b"],
                                  sizes_a=frag["sizes_a"], sizes_b=frag["sizes_b"]),
               sweep=rows, checks=(checks or ["all pass"]))
    with open(f"{OUTDIR}/C8_rho_frontier.json", "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(f"wrote {png} and {OUTDIR}/C8_rho_frontier.json")


if __name__ == "__main__":
    main()
