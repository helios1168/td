"""Same bound as partition.py, under three split rules, to separate granularity from circularity.

  inherit  pieces are the cuts the delivered v2 draw already makes inside each oversized group
           (favourable: those pieces came out of a balanced draw, so they are near-target already)
  equal    each oversized group is cut into ceil(M/target) pieces of EQUAL mass
           (neutral on mass; assumes such a cut is geographically drawable)
  whole    no splitting at all, every state is one atom (the pessimistic bracket)

Contiguity is ignored throughout, so every value here is an upper bound on what a contiguous
state-atom draw of that kind could reach.
"""
import csv
import math
import random
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/ntlee/projects/td")
from td import instance

K = 18
GROUPS = {"CA": ("CA",), "NYNJ": ("NY", "NJ"), "TX": ("TX",), "FL": ("FL",)}

d = instance.load_descaled("/Users/ntlee/projects/td/instance_descaled_v2.json.gz")
G = d.G
draw = {}
with open("/Users/ntlee/projects/td/battery/results/draw_k18_v2_20260904/k18/draw.csv") as fh:
    for row in csv.DictReader(fh):
        draw[row["zip"]] = row["district"]

state_M = defaultdict(float)
for z in G.nodes:
    state_M[G.nodes[z].get("state") or "??"] += float(G.nodes[z].get("M") or 0.0)
TOTAL = sum(state_M.values())
TARGET = TOTAL / K
CEIL = K * math.log(TARGET)
big = {s for sts in GROUPS.values() for s in sts}


def build(mode):
    atoms = defaultdict(float)
    if mode == "whole":
        atoms.update(state_M)
        return atoms
    for st, m in state_M.items():
        if st not in big:
            atoms[st] += m
    if mode == "inherit":
        for z in G.nodes:
            st = G.nodes[z].get("state") or "??"
            if st in big:
                g = next(k for k, v in GROUPS.items() if st in v)
                atoms[f"{g}/{draw.get(z, 'NA')}"] += float(G.nodes[z].get("M") or 0.0)
    else:
        for g, sts in GROUPS.items():
            m = sum(state_M[s] for s in sts)
            n = math.ceil(m / TARGET - 1e-9)
            for i in range(n):
                atoms[f"{g}/p{i + 1}"] = m / n
    return atoms


def solve(w, seeds=12, rounds=400_000):
    best, bestv = None, -math.inf
    n = len(w)
    for s in range(seeds):
        groups = [[] for _ in range(K)]
        if s == 0:
            load = [0.0] * K
            for i in sorted(range(n), key=lambda i: -w[i]):
                j = min(range(K), key=lambda j: load[j])
                groups[j].append(i)
                load[j] += w[i]
        else:
            rng0 = random.Random(s)
            idx = list(range(n))
            rng0.shuffle(idx)
            for t, i in enumerate(idx):
                groups[t % K].append(i)
        load = [sum(w[i] for i in g) for g in groups]
        if min(load) <= 0:
            continue
        cur = sum(math.log(x) for x in load)
        rng = random.Random(1000 + s)
        for _ in range(rounds):
            a, b = rng.randrange(K), rng.randrange(K)
            if a == b or len(groups[a]) == 0:
                continue
            if rng.random() < 0.5:
                if len(groups[a]) == 1:
                    continue
                i = groups[a][rng.randrange(len(groups[a]))]
                na, nb = load[a] - w[i], load[b] + w[i]
                if na <= 0:
                    continue
                new = cur - math.log(load[a]) - math.log(load[b]) + math.log(na) + math.log(nb)
                if new > cur:
                    groups[a].remove(i); groups[b].append(i)
                    load[a], load[b], cur = na, nb, new
            else:
                if not groups[b]:
                    continue
                i = groups[a][rng.randrange(len(groups[a]))]
                j = groups[b][rng.randrange(len(groups[b]))]
                na, nb = load[a] - w[i] + w[j], load[b] - w[j] + w[i]
                if na <= 0 or nb <= 0:
                    continue
                new = cur - math.log(load[a]) - math.log(load[b]) + math.log(na) + math.log(nb)
                if new > cur:
                    groups[a].remove(i); groups[b].remove(j)
                    groups[a].append(j); groups[b].append(i)
                    load[a], load[b], cur = na, nb, new
        if cur > bestv:
            best, bestv = groups, cur
    return best, bestv


print(f"total {TOTAL:.1f}   k {K}   target {TARGET:.4f}")
print(f"balanced ceiling            {CEIL:.6f}")
print(f"zip-level baseline (seed 2) 110.883101   gap {CEIL - 110.88310108262327:.6f}\n")

for mode in ("inherit", "equal", "whole"):
    atoms = build(mode)
    names = sorted(atoms, key=lambda a: -atoms[a])
    w = [atoms[n] for n in names]
    best, v = solve(w)
    load = sorted((sum(w[i] for i in g) for g in best), reverse=True)
    print(f"[{mode}]  atoms {len(names):3d}   Sigma log M {v:.6f}   "
          f"gap to ceiling {CEIL - v:.6f} nats")
    print(f"          mass x target: max {load[0]/TARGET:.4f}  min {load[-1]/TARGET:.4f}  "
          f"spread {(load[0]-load[-1])/TARGET:.3%}")
