"""Read-only: does the delivered v2 draw already fuse NY/NJ/CT into shared districts?"""
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# battery/results and the descaled instance are gitignored and hub-only (CLAUDE.md); a
# worktree carries neither, so TD_DATA_ROOT points a run there at the hub's copy.
DATA_ROOT = Path(os.environ.get("TD_DATA_ROOT", REPO))

sys.path.insert(0, str(REPO))
from td import instance

d = instance.load_descaled(str(DATA_ROOT / "instance_descaled_v2.json.gz"))
G = d.G
TARGET = 473.5134742761501

draw = {}
with open(DATA_ROOT / "battery/results/draw_k18_v2_20260904/k18/draw.csv") as fh:
    for row in csv.DictReader(fh):
        draw[row["zip"]] = row["district"]

# district -> state -> mass
grid = defaultdict(lambda: defaultdict(float))
dist_M = defaultdict(float)
for z, dist in draw.items():
    st = (G.nodes[z].get("state") or "??") if z in G.nodes else "??"
    m = float(G.nodes[z].get("M") or 0.0) if z in G.nodes else 0.0
    grid[dist][st] += m
    dist_M[dist] += m

print("districts holding NY and/or NJ mass (>0.5 M), sorted by district mass:")
print(f"{'dist':<10}{'total M':>10}{'x tgt':>8}{'NY':>9}{'NJ':>9}{'CT':>9}{'PA':>9}  other states")
for dist in sorted(dist_M, key=lambda x: -dist_M[x]):
    g = grid[dist]
    if g.get("NY", 0) + g.get("NJ", 0) < 0.5:
        continue
    other = sorted(((s, v) for s, v in g.items() if s not in ("NY", "NJ", "CT", "PA") and v > 0.5),
                   key=lambda r: -r[1])
    otxt = ", ".join(f"{s} {v:.0f}" for s, v in other[:6])
    print(f"{dist:<10}{dist_M[dist]:>10.1f}{dist_M[dist]/TARGET:>8.2f}"
          f"{g.get('NY',0):>9.1f}{g.get('NJ',0):>9.1f}{g.get('CT',0):>9.1f}{g.get('PA',0):>9.1f}  {otxt}")

groups = {
    "NY+NJ": ["NY", "NJ"],
    "NY+NJ+CT": ["NY", "NJ", "CT"],
    "NY+NJ+CT+PA": ["NY", "NJ", "CT", "PA"],
}
sm = defaultdict(float)
for z in G.nodes:
    sm[G.nodes[z].get("state") or "??"] += float(G.nodes[z].get("M") or 0.0)
print()
for name, sts in groups.items():
    tot = sum(sm[s] for s in sts)
    print(f"{name:<14} M {tot:9.1f}   {tot/TARGET:5.3f} x target   ceil -> {-(-tot//TARGET):.0f} pieces")

print()
print("mass of every district, x target (baseline draw):")
print("  " + "  ".join(f"{dist_M[x]/TARGET:.3f}" for x in sorted(dist_M, key=lambda x: -dist_M[x])))
