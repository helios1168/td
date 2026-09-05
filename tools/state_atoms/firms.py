"""Read-only: what firm labels does v2 carry, and how is book split between them?"""
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/ntlee/projects/td")
from td import instance

d = instance.load_descaled("/Users/ntlee/projects/td/instance_descaled_v2.json.gz")
G = d.G

print("firm dict size:", len(d.firm))
labels = sorted(set(d.firm.values()))
print("distinct labels:", labels)
per = defaultdict(list)
for rep, f in d.firm.items():
    per[f].append(rep)
for f in labels:
    print(f"  {f!r}: {len(per[f])} reps, sample {sorted(per[f])[:6]}")

print("\nreps total:", len(d.reps), " with firm label:", len(set(d.reps) & set(d.firm)))
print("reps missing a firm label:", sorted(set(d.reps) - set(d.firm))[:10])

# book by firm
book = defaultdict(float)
for z in G.nodes:
    S = G.nodes[z].get("S") or {}
    for rep, v in S.items():
        book[d.firm.get(rep, "?")] += float(v)
tot = sum(book.values())
print("\nbooked production by firm:")
for f, v in sorted(book.items(), key=lambda r: -r[1]):
    print(f"  {f!r}: {v:12.1f}  {v/tot:6.1%}")

# zip-level dominance
dom = defaultdict(int)
domM = defaultdict(float)
for z in G.nodes:
    S = G.nodes[z].get("S") or {}
    M = float(G.nodes[z].get("M") or 0.0)
    byf = defaultdict(float)
    for rep, v in S.items():
        byf[d.firm.get(rep, "?")] += float(v)
    if not byf or max(byf.values()) <= 0:
        dom["none"] += 1
        domM["none"] += M
        continue
    top = max(byf, key=lambda k: byf[k])
    contested = sum(1 for v in byf.values() if v > 0) > 1
    key = top + ("/shared" if contested else "")
    dom[key] += 1
    domM[key] += M
print("\nzip dominance (count, M):")
for k in sorted(dom, key=lambda k: -domM[k]):
    print(f"  {k:<14} {dom[k]:5d} zips  M {domM[k]:9.1f}")

print("\nmeta keys:", sorted((d.meta or {}).keys()))
