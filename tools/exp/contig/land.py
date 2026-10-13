"""land.py -- #133's land balance on run folders (the main-map overnight grid, 2026-10-13):
each folder's `land.csv`, one row per split group, a planning channel's districts owning ZCTAs in
one state when there are two or more, with the in-state land ratio, largest over smallest, over
the pieces holding at least `MIN_SHARE` of their district's mass, against R.

    "$TD_PY" tools/exp/contig/land.py <run_dir>... [--ratio R]

The ratio over every piece (`ratio_all`) is listed beside it: a sliver holding little of its
district's mass is no territory to balance (#133 step 1: NY national 870 over all pieces, 31 over
those of 20% or more).  Land is the gazetteer's (`geo.polygon_graph`'s `aland`, in km²), each
ZCTA counted once per channel however many fine channels it carries; mass is the ledger's, `m_rel`
or $M on a dollar run (a share is a ratio either way).  The draw holds the ratio softly
(`draw.py`'s land term, `run.py --land-ratio`); the repair keeps its own objective, so a
repaired folder's `land.csv` reports what it moved.
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import geo  # noqa: E402

RATIO = 10.0            # #133's R for the overnight grid (owner decision open, 2026-10-13)
MIN_SHARE = 0.20        # a piece counts when it holds this share of its district's mass
COLUMNS = ["channel", "state", "districts", "pieces", "ratio", "ratio_all", "largest", "largest_km2",
           "smallest", "smallest_km2", "over", "detail"]


def land_rows(ledger: list, aland: dict, ratio: float = RATIO, min_share: float = MIN_SHARE) -> list:
    """One row per split group of the ledger, sorted by (channel, state): `districts` and
    `pieces` (those of `min_share` or more) counted, `ratio` the largest piece's land over the
    smallest's among `pieces` (None below two), `ratio_all` over every piece, `largest` and
    `smallest` the two districts of `ratio` (else of `ratio_all`) with their km², `over` when
    `ratio` exceeds R, and `detail` [(district, km², share)] by land, largest first.  `aland` is
    {zip: km²}."""
    owned = set()                                   # (channel, district, state, zip)
    mass, total = collections.Counter(), collections.Counter()
    for r in ledger:
        d = r["district"]
        if not d:
            continue
        ch, s = r["model_channel"], r["state"]
        owned.add((ch, d, s, r["zip_code"]))
        m = float(r["m_rel"] or 0.0)
        mass[ch, d, s] += m
        total[ch, d] += m
    land = collections.Counter()
    groups = collections.defaultdict(set)
    for ch, d, s, z in owned:
        land[ch, d, s] += aland.get(z, 0.0)
        groups[ch, s].add(d)
    out = []
    for (ch, s), ds in sorted(groups.items()):
        if len(ds) < 2:
            continue
        detail = sorted(((d, land[ch, d, s], mass[ch, d, s] / total[ch, d] if total[ch, d] else 0.0)
                         for d in ds), key=lambda p: (-p[1], p[0]))
        big = [p for p in detail if p[2] >= min_share]
        use = big if len(big) > 1 else detail
        r_big = big[0][1] / max(big[-1][1], 1e-9) if len(big) > 1 else None
        out.append({"channel": ch, "state": s, "districts": len(ds), "pieces": len(big),
                    "ratio": r_big, "ratio_all": detail[0][1] / max(detail[-1][1], 1e-9),
                    "largest": use[0][0], "largest_km2": use[0][1],
                    "smallest": use[-1][0], "smallest_km2": use[-1][1],
                    "over": r_big is not None and r_big > ratio, "detail": detail})
    return out


def write_land(path: str, rows: list) -> None:
    """`land.csv`: the `land_rows`, km² to 0.1, ratios to 0.01, `detail` as district:km²:share%."""
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([r["channel"], r["state"], r["districts"], r["pieces"],
                        "" if r["ratio"] is None else f"{r['ratio']:.2f}", f"{r['ratio_all']:.2f}",
                        r["largest"], f"{r['largest_km2']:.1f}", r["smallest"], f"{r['smallest_km2']:.1f}",
                        int(r["over"]),
                        ";".join(f"{d}:{a:.1f}:{100 * x:.0f}%" for d, a, x in r["detail"])])


def summary(name: str, rows: list, ratio: float = RATIO) -> str:
    """One line per folder: split groups, those with two pieces or more, and those beyond R."""
    over = [r for r in rows if r["over"]]
    head = (f"{name}: {len(rows)} split groups, {sum(r['ratio'] is not None for r in rows)} with two "
            f"pieces of {100 * MIN_SHARE:.0f}% or more, {len(over)} beyond R = {ratio:g}")
    return head + "".join(f"; {r['channel']} {r['state']} {r['ratio']:.1f}" for r in over)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--ratio", type=float, default=RATIO, help="#133's R")
    a = ap.parse_args(argv)
    aland = {z: x / 1e6 for z, x in geo.polygon_graph()["aland"].items()}
    for d in a.run_dirs:
        with open(os.path.join(d, "ledger.csv"), newline="") as fh:
            rows = land_rows(list(csv.DictReader(fh)), aland, a.ratio)
        write_land(os.path.join(d, "land.csv"), rows)
        print(summary(os.path.basename(os.path.normpath(d)), rows, a.ratio))
    return 0


if __name__ == "__main__":
    sys.exit(main())
