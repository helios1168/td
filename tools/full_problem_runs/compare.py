"""Two realised cells side by side: the grid row, then per-bundle district masses, the districts
whose bundle and state set both runs share, and the districts in more than one piece.  A is the
reference (for the forced study, `grid_20260911_v4/full/X_n16w11f20_d100_d900n6_full`).

    compare.py A_CELL_DIR B_CELL_DIR [A_CELL_DIR B_CELL_DIR ...]
"""
import csv
import os
import sys
from collections import defaultdict

KEYS = ("cover_N", "cover_WH", "cover_FI", "cover_merged", "certified_passes", "districts",
        "districts_N", "districts_WH", "districts_FI", "splits_N", "splits_WH", "splits_FI",
        "states_three", "states_merged", "states_dropped", "states_other", "residual_mass",
        "max_extent_km", "pieces_total", "staffed", "staffing_value")


def grid_row(cell):
    path = os.path.join(os.path.dirname(cell), "grid.csv")
    if not os.path.exists(path):
        return {}
    for row in csv.DictReader(open(path)):
        if row["tag"] == os.path.basename(cell):
            return row
    return {}


def districts(cell):
    rows = list(csv.DictReader(open(os.path.join(cell, "districts.csv"))))
    for r in rows:
        r["mass"] = float(r["mass"])
        r["share"] = {kv.split(":")[0]: float(kv.split(":")[1]) for kv in r["states"].split(",")}
    return rows


def fmt(xs):
    return " ".join(f"{x:.0f}" for x in xs)


args = [a.rstrip("/") for a in sys.argv[1:]]
for a, b in zip(args[0::2], args[1::2]):
    print(f"\n=== {os.path.basename(b)}\n    A {a}\n    B {b}")
    ga, gb = grid_row(a), grid_row(b)
    for k in KEYS:
        va, vb = ga.get(k, "?"), gb.get(k, "?")
        mark = "" if va == vb else "   *"
        print(f"  {k:18s} {va:>12s} {vb:>12s}{mark}")
    da, db = districts(a), districts(b)
    by_a, by_b = defaultdict(list), defaultdict(list)
    for r in da:
        by_a[r["bundle"]].append(r)
    for r in db:
        by_b[r["bundle"]].append(r)
    print("  per bundle: count, total mass, sorted masses (A / B)")
    for bun in sorted(set(by_a) | set(by_b)):
        ma = sorted((r["mass"] for r in by_a[bun]), reverse=True)
        mb = sorted((r["mass"] for r in by_b[bun]), reverse=True)
        print(f"  {bun:10s} {len(ma):2d} {sum(ma):8.1f} | {len(mb):2d} {sum(mb):8.1f}")
        print(f"             A {fmt(ma)}\n             B {fmt(mb)}")
    # a district is the same when its bundle and its state set agree; report the rest
    key = lambda r: (r["bundle"], tuple(sorted(r["share"])))
    ka, kb = {key(r): r for r in da}, {key(r): r for r in db}
    same = set(ka) & set(kb)
    print(f"  districts with the same bundle and state set: {len(same)} of A {len(ka)} / B {len(kb)}")
    moved = [(k, ka[k]["mass"], kb[k]["mass"]) for k in same if abs(kb[k]["mass"] - ka[k]["mass"]) > 1]
    for k, x, y in sorted(moved, key=lambda t: -abs(t[2] - t[1]))[:10]:
        print(f"    {k[0]:10s} {','.join(k[1]):24s} {x:7.1f} {y:7.1f} {y - x:+6.1f}")
    for k in sorted(set(ka) - set(kb)):
        print(f"    only A: {k[0]:10s} {','.join(k[1])}  {ka[k]['mass']:.1f}")
    for k in sorted(set(kb) - set(ka)):
        print(f"    only B: {k[0]:10s} {','.join(k[1])}  {kb[k]['mass']:.1f}")
    multi = [r["district"] for r in db if int(r["pieces"]) > 1]
    print(f"  B districts in more than one piece: {len(multi)} {' '.join(multi)}")
