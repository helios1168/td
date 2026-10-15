"""neckcut_search.py -- brute-force validity search for `draw.NeckCut` rows (#142 phase 1).

    "$TD_PY" -u tools/exp/contig/neckcut_search.py --seed 11 --graphs 40000 [--rows nogood|strong]
        [--jobs 4] [--show 3]

A `draw.NeckCut` row (`repair.neck_cuts`: the no-good rows of `necks_gate.nogood_terms` by default, `--rows strong` for
`necks_gate.cut_terms`) must be valid for the gate's
model: no drawing of the window in which the district is own-connected and has no gate neck
(`necks_gate.gate_necks`) may break it.  An invalid row excludes maps the gate accepts, the bug #142
fixes.  This script tests that on random 5-ZIP graphs (graph i of seed s is drawn from
`random.Random(s * 1_000_003 + i)`, so a run is reproducible and splits over `--jobs`; `--p-edge`,
`--p-zero`, `--window` and `--every-first` widen it): random
borders, connectors, width-only gap edges, land, and zero-opportunity ZCTAs; a window of 2 or 3
ZCTAs; a random owner of the others and a random first drawing of the window.  The rows built on
the first drawing's necks of D1 are tested against every drawing of the window.  It prints the
number of graphs with a row built, the drawings checked and the (graph, first drawing, row,
drawing) cases that break, and the `--show` smallest as Python literals to paste into a test.
Exit status 1 if any row breaks."""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import multiprocessing
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DISTRICTS = ("D1", "D2")
CHECK = {"D1"}


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


gate = _load("contig_necks_gate", "necks_gate.py")
repair = _load("contig_repair", "repair.py")


def world(rng: random.Random, p_edge: float = 0.5, p_zero: float = 0.35):
    """(polygon, m): five ZCTAs in one state, borders of 0.3 to 20 km on `p_edge` of the pairs, a
    connector on a tenth of them, gap edges on some of the rest, land from 1e6 to 3e8 m², and
    `p_zero` of the ZCTAs of zero opportunity."""
    zs = [f"z{i}" for i in range(5)]
    pairs = [e for e in itertools.combinations(zs, 2) if rng.random() < p_edge]
    border = {e: 1000.0 * rng.choice([0.3, 1.0, 2.5, 4.0, 7.0, 12.0, 20.0]) for e in pairs}
    conn = [e for e in pairs if rng.random() < 0.1]
    gaps = {e: 1000.0 * rng.choice([1.0, 5.0, 12.0]) for e in itertools.combinations(zs, 2)
            if e not in border and rng.random() < 0.15}
    polygon = {"vertices": zs, "edges": sorted(pairs), "state": dict.fromkeys(zs, "TX"),
               "border": border, "connectors": conn,
               "aland": {z: rng.choice([1e6, 1e7, 5e7, 1e8, 3e8]) for z in zs}, "voronoi_gaps": gaps}
    m = {z: (0.0 if rng.random() < p_zero else 1.0) for z in zs}
    return polygon, m


def own_connected(zs: set, ng) -> bool:
    zs = set(zs)
    if not zs:
        return False
    seen, stack = set(), [min(zs)]
    while stack:
        z = stack.pop()
        if z in seen:
            continue
        seen.add(z)
        stack += [y for y in zs - seen if ng.own_edge(z, y)]
    return seen == zs


def drawings(W: set):
    """Every assignment of the window's ZCTAs to D1 and D2."""
    zs = sorted(W)
    for pick in itertools.product(DISTRICTS, repeat=len(zs)):
        yield dict(zip(zs, pick))


def broken_rows(polygon: dict, m: dict, W: set, base: dict, first: dict, rows: str = "nogood"):
    """(rows built, drawings checked, [(label, drawing)] of rows broken by a drawing the gate
    accepts) for the rows `repair.neck_cuts` builds on the map `base` + `first`.  A drawing counts
    when D1 is own-connected in it with no gate neck."""
    ng = gate.gate_graph(polygon)
    cuts, _ = repair.neck_cuts("X", base, set(W), m, ng, first, CHECK, rows)
    checked, bad = 0, []
    for other in drawings(W):
        d1 = {z for z, j in {**base, **other}.items() if j == "D1"}
        if not own_connected(d1, ng) or repair.district_necks(d1, m, ng):
            continue
        checked += 1
        bad += [(c.label, other) for c in cuts if not c.holds(other)]
    return len(cuts), checked, bad


def one(args):
    """(index, rows, checked, [case]) of graph `i` of `seed`."""
    seed, i, p_edge, p_zero, sizes, every, kind = args
    rng = random.Random(seed * 1_000_003 + i)
    polygon, m = world(rng, p_edge, p_zero)
    zs = polygon["vertices"]
    W = set(rng.sample(zs, rng.choice(sizes)))
    base = {z: rng.choice(DISTRICTS) for z in zs if z not in W}
    rows = checked = 0
    cases = []
    for first in (drawings(W) if every else [{z: rng.choice(DISTRICTS) for z in sorted(W)}]):
        r, c, bad = broken_rows(polygon, m, W, base, first, kind)
        rows, checked = rows + r, checked + c
        cases += [dict(polygon=polygon, m=m, W=sorted(W), base=base, first=first, label=label,
                       drawing=d) for label, d in bad]
    return i, rows, checked, cases


def size(case: dict) -> tuple:
    p = case["polygon"]
    return (len(p["edges"]) + len(p["voronoi_gaps"]) + len(p["connectors"]), len(case["W"]),
            case["label"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--graphs", type=int, default=40000)
    ap.add_argument("--p-edge", type=float, default=0.5, help="share of the pairs with a border")
    ap.add_argument("--p-zero", type=float, default=0.35, help="share of ZCTAs of zero opportunity")
    ap.add_argument("--window", type=int, nargs="+", default=[2, 3], help="window sizes drawn from")
    ap.add_argument("--every-first", action="store_true",
                    help="build rows on every drawing of the window, not one at random")
    ap.add_argument("--rows", choices=repair.NECK_ROWS, default="nogood",
                    help="the row type tested (`repair.neck_cuts`)")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--show", type=int, default=3, help="print this many smallest broken cases")
    a = ap.parse_args(argv)
    work = [(a.seed, i, a.p_edge, a.p_zero, tuple(a.window), a.every_first, a.rows)
            for i in range(a.graphs)]
    if a.jobs > 1:
        with multiprocessing.Pool(a.jobs) as pool:
            results = pool.map(one, work, chunksize=200)
    else:
        results = map(one, work)
    rows = checked = graphs_with_rows = 0
    cases, bad_graphs = [], set()
    for i, r, c, bad in results:
        rows += r
        checked += c
        graphs_with_rows += r > 0
        if bad:
            bad_graphs.add(i)
            cases += bad
    print(f"seed {a.seed}, {a.rows} rows: {a.graphs} graphs, {graphs_with_rows} with a row built, {rows} rows, "
          f"{checked} drawings checked; {len(cases)} (row, drawing) cases break in "
          f"{len(bad_graphs)} graphs", flush=True)
    for case in sorted(cases, key=size)[:a.show]:
        print(repr(case))
    return 1 if cases else 0


if __name__ == "__main__":
    sys.exit(main())
