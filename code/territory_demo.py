"""Smoke test on a synthetic ZCTA lattice that mimics the real structure."""
import numpy as np, networkx as nx, territory as T
rng=np.random.default_rng(7)

# 24x24 lattice of "ZCTAs" with Rook adjacency; 4 states as vertical bands
W=24; G=nx.grid_2d_graph(W,W)          # grid_2d_graph IS rook adjacency
for (i,j) in G: G.nodes[(i,j)]["state"]=["NE","IA","MO","KS"][i//6]

# two metros drive opportunity
met=[(6,17),(17,7)]
for (i,j) in G:
    d=min((i-m[0])**2+(j-m[1])**2 for m in met)
    G.nodes[(i,j)]["M"]=float(0.4+6.0*np.exp(-d/26)+rng.uniform(0,.3))

# firm A: 3 reps in vertical strips; firm B: 4 reps in horizontal strips (deliberate misalignment)
for (i,j) in G:
    G.nodes[(i,j)]["rep_a"]=f"A{i//8}"
    G.nodes[(i,j)]["rep_b"]=f"B{j//6}"

# sales: A anchored on metro 1, B on metro 2
for (i,j) in G:
    M=G.nodes[(i,j)]["M"]
    da=np.exp(-((i-met[0][0])**2+(j-met[0][1])**2)/60)
    db=np.exp(-((i-met[1][0])**2+(j-met[1][1])**2)/60)
    sa=0.06+0.26*da; sb=0.06+0.26*db
    A=M*sa*rng.lognormal(0,.20); B=M*sb*rng.lognormal(0,.20)
    sc=max(1.0,(A+B)/(0.90*M)); G.nodes[(i,j)]["A"]=A/sc; G.nodes[(i,j)]["B"]=B/sc

print("VALIDATE"); [print("  !",p) for p in T.validate(G)] or print("  clean")

print("\nCENSUS")
for c in T.census(G):
    print(f"  {c['shape']:<34} M={c['M']:8.1f} ({c['share']:.1%})  "
          f"reps: {sorted(x[1] for x in c['reps_a'])} vs {sorted(x[1] for x in c['reps_b'])}")

# pick the pair sharing the most opportunity and solve it
ra,rb,d=T.largest_pair(G)
pair=T.zips_for_pair(G,ra,rb)
print(f"\nLARGEST OVERLAP PAIR: {ra} x {rb}   {len(pair)} ZCTAs, M={d['M']:.1f}")
rows=T.compare_criteria(G,pair)
print("  criterion             k    g_a      g_b     min(g)   KS gap   M_a share")
for nm,r in rows.items():
    print(f"  {nm:<20}{r['k']:>3}  {r['g_a']:7.3f}  {r['g_b']:7.3f}  {r['min_g']:7.3f}  "
          f"{r['ks_gap']:.4f}   {r['M_a_share']:.3f}")

res=T.solve(G,pair,"ks")
rep=T.contiguity_report(G,pair,res["to_a"])
print(f"\nCONTIGUITY (rook): A has {rep['components_a']} piece(s) {rep['sizes_a']}, "
      f"B has {rep['components_b']} {rep['sizes_b']}")
fix=T.enforce_contiguity(G,pair,res)
print(f"  repair: {fix['moves']} island move(s), KS gap {fix['ks_gap_before']:.4f} -> {fix['ks_gap_after']:.4f}")
rep2=T.contiguity_report(G,pair,fix["to_a"])
print(f"  after : A {rep2['components_a']} piece(s), B {rep2['components_b']}")

st=T.contiguity_report(G,pair,res["to_a"],respect_state=True)
print(f"  if state borders are HARD: A {st['components_a']} piece(s), B {st['components_b']}")

con=T.contestability(G,pair,draws=200)
top=sorted(con.items(),key=lambda kv:-kv[1]["contestability"])[:5]
print("\nTOP CONTESTED ZCTAs")
for n,c in top:
    print(f"  {str(n):<10} stake={c['stake']:.4f} doubt={c['doubt']:.3f} "
          f"contest={c['contestability']:.4f}  now={c['assigned']}  state={G.nodes[n]['state']}")
T.write_back(G,pair,fix["to_a"],con)
print(f"\nwrote attributes back to graph: {[k for k in G.nodes[pair[0]]]}")
