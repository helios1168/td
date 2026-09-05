"""Read-only: v2 state-atom facts for the problem-statement artifact."""
import csv
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/ntlee/projects/td")
import networkx as nx

from td import instance

d = instance.load_descaled("/Users/ntlee/projects/td/instance_descaled_v2.json.gz")
G = d.G
K = 18

m = defaultdict(float)
n = defaultdict(int)
for z in G.nodes:
    st = G.nodes[z].get("state") or "??"
    m[st] += float(G.nodes[z].get("M") or 0.0)
    n[st] += 1
total = sum(m.values())
target = total / K

out = {"k": K, "total_M": total, "target": target, "n_state_codes": len(m)}
out["states"] = sorted(
    ({"st": s, "M": v, "ratio": v / target, "zips": n[s]} for s, v in m.items()),
    key=lambda r: -r["M"],
)

# zip-level adjacency health
comps = list(nx.connected_components(G))
comp_M = sorted((sum(float(G.nodes[z].get("M") or 0.0) for z in c) for c in comps), reverse=True)
out["zip_graph"] = {
    "nodes": G.number_of_nodes(),
    "edges": G.number_of_edges(),
    "components": len(comps),
    "largest_share": comp_M[0] / total,
    "share_in_sub1pct": sum(x for x in comp_M if x / total < 0.01) / total,
    "singletons": sum(1 for c in comps if len(c) == 1),
}

# state-contracted adjacency
S = nx.Graph()
S.add_nodes_from(m)
for u, v in G.edges:
    a = G.nodes[u].get("state") or "??"
    b = G.nodes[v].get("state") or "??"
    if a != b:
        S.add_edge(a, b)
scomps = list(nx.connected_components(S))
out["state_graph"] = {
    "nodes": S.number_of_nodes(),
    "edges": S.number_of_edges(),
    "components": len(scomps),
    "isolated": sorted(x for c in scomps if len(c) == 1 for x in c),
    "sizes": sorted((len(c) for c in scomps), reverse=True),
}

# how the delivered draw fragments states
draw = {}
with open("/Users/ntlee/projects/td/battery/results/draw_k18_v2_20260904/k18/draw.csv") as fh:
    for row in csv.DictReader(fh):
        draw[row["zip"]] = row["district"]
per_state = defaultdict(set)
per_dist_states = defaultdict(set)
for z, dist in draw.items():
    st = G.nodes[z].get("state") or "??" if z in G.nodes else "??"
    per_state[st].add(dist)
    per_dist_states[dist].add(st)
frag = sorted(((s, len(ds)) for s, ds in per_state.items()), key=lambda r: -r[1])
out["baseline_draw"] = {
    "rows": len(draw),
    "districts": len(per_dist_states),
    "states_split": sum(1 for _, c in frag if c >= 2),
    "states_whole": sum(1 for _, c in frag if c == 1),
    "worst": frag[:12],
    "states_per_district": sorted(len(v) for v in per_dist_states.values()),
}

print(json.dumps(out, indent=1))
