"""
census_stress.py -- exercise T.census() against the synthetic battery before real data.

Four experiments, each aimed at a named gate:

  1. ALPHA SWEEP (kill criterion 1): how much opportunity sits in 1-1 pair components
     as rep-territory alignment degrades from perfect (alpha=1) to independent
     (alpha=0)? Run under the ORIGINAL census behaviour (split=False: weak edges
     trimmed only when labelling a component, never to split it -- so a single sliver
     edge permanently glues two clean pairs into one "dense" component) AND the
     PATCHED default (split=True: trimming re-componentizes). The patch to
     territory.census() was made because of what this experiment found.

  2. MIN_SHARE AUDIT (implicit-parameter audit of the 2% default): on the sliver
     scenario, sweep min_share and ask whether the verdict (share of opportunity in
     1-1 components) depends on a threshold nobody chose.

  3. RHO DIAL CHECK (kill criterion 4): realized corr(A_z,B_z) across the dial,
     confirming the generator can instantiate the books-barely-overlap regime.

  4. STATE BINDING (kill criterion 3): fraction of adjacency edges deleted by
     respect_state, and how many pieces each rep-pair zone fragments into.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, networkx as nx
import territory as T
from synth import make_instance, scenario, SCENARIOS


def share11(rows):
    return sum(r["share"] for r in rows if r["shape"] == "1-1 pair")


if __name__ == "__main__":
    SEEDS = range(8)

    print("=" * 78)
    print("1. ALPHA SWEEP  (n=200, 4A x 4B reps, 8 seeds)")
    print("   share of opportunity in 1-1 pair components, mean [min,max] over seeds")
    print("=" * 78)
    print(f"  {'alpha':>6} {'census as shipped':>22} {'effective (re-split)':>22}")
    alpha_rows = []
    for alpha in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0):
        s_ship, s_eff = [], []
        for sd in SEEDS:
            G = make_instance(n=200, n_rep_a=4, n_rep_b=4, alpha=alpha, seed=sd)
            s_ship.append(share11(T.census(G, split=False)))
            s_eff.append(share11(T.census(G, split=True)))
        s_ship, s_eff = np.array(s_ship), np.array(s_eff)
        alpha_rows.append((alpha, s_ship, s_eff))
        print(f"  {alpha:>6.1f} {s_ship.mean():>8.0%} [{s_ship.min():>4.0%},{s_ship.max():>4.0%}] "
              f"{s_eff.mean():>8.0%} [{s_eff.min():>4.0%},{s_eff.max():>4.0%}]")

    print()
    print("=" * 78)
    print("2. MIN_SHARE AUDIT  (S3_slivers: alpha=1, sliver=3%, 8 seeds)")
    print("   the truth is 100% 1-1 by construction; slivers are pure map noise")
    print("=" * 78)
    print(f"  {'min_share':>10} {'as shipped':>12} {'effective':>12} {'opp trimmed':>12}")
    audit_rows = []
    for ms in (0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.15):
        s_ship, s_eff, s_trim = [], [], []
        for sd in SEEDS:
            G = scenario("S3_slivers", n=200, seed=sd)
            s_ship.append(share11(T.census(G, min_share=ms, split=False)))
            rows = T.census(G, min_share=ms, split=True)
            s_eff.append(share11(rows))
            s_trim.append(1.0 - sum(r["share"] for r in rows))
        audit_rows.append((ms, np.mean(s_ship), np.mean(s_eff), np.mean(s_trim)))
        print(f"  {ms:>10.3f} {np.mean(s_ship):>12.0%} {np.mean(s_eff):>12.0%} "
              f"{np.mean(s_trim):>12.1%}")

    print()
    print("=" * 78)
    print("3. RHO DIAL -> REALIZED corr(A_z, B_z)  (8 seeds each)")
    print("=" * 78)
    for rho in (-0.5, -0.25, 0.0, 0.25, 0.5, 0.7, 0.9, 1.0):
        cs = [make_instance(n=200, rho_books=rho, seed=sd).graph["corr_AB"]
              for sd in SEEDS]
        cs = np.array(cs)
        print(f"  rho={rho:+.2f}  corr mean {cs.mean():+.3f}  sd {cs.std():.3f}  "
              f"range [{cs.min():+.3f}, {cs.max():+.3f}]")

    print()
    print("=" * 78)
    print("4. STATE BINDING  (S5_states: 6 states, alpha=0.7, 8 seeds)")
    print("=" * 78)
    fr_edges, fr_pieces = [], []
    for sd in SEEDS:
        G = scenario("S5_states", n=200, seed=sd)
        cross = sum(1 for u, v in G.edges()
                    if G.nodes[u]["state"] != G.nodes[v]["state"])
        fr_edges.append(cross / G.number_of_edges())
        # fragmentation of each (rep_a, rep_b) overlap zone once cross-state edges go
        H = nx.Graph((u, v) for u, v in G.edges()
                     if G.nodes[u]["state"] == G.nodes[v]["state"])
        H.add_nodes_from(G.nodes())
        pieces = []
        zones = {}
        for z, d in G.nodes(data=True):
            zones.setdefault((d["rep_a"], d["rep_b"]), []).append(z)
        for zone_nodes in zones.values():
            if len(zone_nodes) < 3: continue
            pieces.append(nx.number_connected_components(H.subgraph(zone_nodes)))
        fr_pieces.append(np.mean(pieces))
    print(f"  cross-state adjacency edges: mean {np.mean(fr_edges):.0%} of all edges")
    print(f"  mean pieces per rep-pair overlap zone after respect_state: "
          f"{np.mean(fr_pieces):.1f} (1.0 = state lines cost nothing)")

    np.save("/tmp/census_stress_alpha.npy",
            np.array([(a, s1.mean(), s1.min(), s1.max(), s2.mean(), s2.min(), s2.max())
                      for a, s1, s2 in alpha_rows]))
    np.save("/tmp/census_stress_audit.npy", np.array(audit_rows))
