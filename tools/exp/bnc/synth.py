"""synth.py -- small synthetic instances for the correctness tests (#142), in the instance schema.

`grid` lays out a w × h grid graph (4-neighbour, all edges equal), puts each district's fixed body
on given cells (a district with none is rootless), gives every cell a mass, and writes the snapshot
`capture.snapshot_args` would, so the model is built by draw.py's own `_solve_group`
(`capture.rebuild_model`), as for an exported group: the left half of the grid is unit `L`, the right
half `R`, so the split term has something to count.  A drawing is judged by `connected` below,
independently of `sepcuts` (breadth-first search on the grid).
"""
from __future__ import annotations

import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import capture  # noqa: E402
import inst_io  # noqa: E402


def cell(r: int, c: int) -> str:
    return f"r{r:02d}c{c:02d}"


def grid(name: str, w: int, h: int, bodies: dict, seed: int = 1, delta: float = 0.2,
         heavy: dict | None = None, rootless: tuple = (), k: int | None = None,
         band: tuple | None = None, extra: dict | None = None, sequential: bool = False) -> inst_io.Inst:
    """`bodies` {district: [(r, c), ...]} fixed cells (one body per connected run, listed as one
    body when adjacent, else one each); `rootless` districts with no body; `heavy` {(r, c): mass}.
    The band is τ(1 ± delta) for τ the total mass over the number of districts, or `band` (lo, hi);
    `extra` {district: mass} is the mass a district holds outside the group (draw.py's `extra`) and
    `sequential` draw.py's flag of that name."""
    rng = random.Random(seed)
    nodes = [(r, c) for r in range(h) for c in range(w)]
    mass = {cell(r, c): float(rng.randint(1, 4)) for r, c in nodes}
    for (r, c), x in (heavy or {}).items():
        mass[cell(r, c)] = float(x)
    owner = {cell(r, c): j for j, cs in bodies.items() for r, c in cs}
    js = sorted(set(bodies) | set(rootless))
    free = [cell(r, c) for r, c in nodes if cell(r, c) not in owner]
    adj = {cell(r, c): sorted(cell(r + dr, c + dc) for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))
                              if 0 <= r + dr < h and 0 <= c + dc < w) for r, c in nodes}
    unit = {cell(r, c): "L" if c < w // 2 else "R" for r, c in nodes}
    comps = {}
    for j, cs in bodies.items():
        left, out = {cell(r, c) for r, c in cs}, []
        while left:
            comp, stack = set(), [min(left)]
            while stack:
                a = stack.pop()
                if a in comp:
                    continue
                comp.add(a)
                stack += [b for b in adj[a] if b in left and b not in comp]
            out.append(sorted(comp))
            left -= comp
        comps[j] = sorted(out, key=lambda b: (-len(b), b[0]))
    tau = sum(mass.values()) / (k or len(js))
    lo, hi = band if band else (tau * (1 - delta), tau * (1 + delta))
    units = {"L": [z for z in unit if unit[z] == "L"], "R": [z for z in unit if unit[z] == "R"]}
    snap = {
        "c": "X", "zs": free, "allowed": {z: list(js) for z in free},
        "bodies": {j: comps.get(j, []) for j in js}, "fixed": dict(owner),
        "adj": {z: adj[z] for z in free}, "m": mass,
        "p": {cell(r, c): [float(c), float(r)] for r, c in nodes if cell(r, c) in set(free)},
        "unit_of": unit, "hold": {"L": list(js), "R": list(js)}, "planned": [],
        "support": {j: ["L", "R"] for j in js}, "targets": {j: tau for j in js}, "tau": tau,
        "M": [], "unit_zips": units, "lo": lo, "hi": hi, "arm": "arm1", "fixed_targets": False,
        "extra": extra, "sequential": sequential, "border": None, "land": None, "centres": []}
    draw = capture.load_draw()
    base = capture.rebuild_model(draw, snap)
    doc = {"schema": inst_io.SCHEMA, "id": name,
           "meta": {"note": "synthetic grid", "exported": time.strftime("%Y-%m-%dT%H:%M:%S")},
           "model": base["model"], "labels": base["labels"], "graph": base["graph"],
           "draw": snap, "start": base["start"]}
    return inst_io.Inst(doc, f"synthetic:{name}")


def connected(inst, owner: dict) -> bool:
    """Whether every district of `owner` (plus its body cells) is one piece on the grid graph,
    checked on the instance's own graph with no use of `sepcuts`."""
    g = inst.gadj
    for j in inst.js:
        cells = {z for z, k in owner.items() if k == j} | {b for b, k in inst.vert_of.items() if k == j}
        if not cells:
            continue
        start = next(iter(sorted(cells)))
        seen, stack = {start}, [start]
        while stack:
            for b in g[stack.pop()]:
                if b in cells and b not in seen:
                    seen.add(b)
                    stack.append(b)
        if seen != cells:
            return False
    return True


def cases() -> list:
    """The three test instances (name, kwargs of `grid`), found by search: the model without any
    connectivity row beyond draw.py's up-front neighbour rows has a disconnected optimum on each
    (a district's 18-cell piece, a second body of a district joined to nothing, a rootless
    district's 12-cell piece), so every arm has cuts to find."""
    return [
        ("g6x6_rooted", dict(w=6, h=6, bodies={"A": [(1, 0)], "B": [(3, 0)], "C": [(4, 0)]},
                             seed=4, delta=0.4, heavy={(0, 0): 8, (2, 1): 8, (5, 0): 12})),
        ("g6x6_two_bodies", dict(w=6, h=6, bodies={"A": [(2, 1), (2, 5)], "B": [(0, 1)], "C": [(0, 4)]},
                                 seed=13, delta=0.3, heavy={(2, 3): 8, (0, 2): 8})),
        ("g8x5_rootless", dict(w=8, h=5, bodies={"A": [(4, 7)], "B": [(1, 5)]}, rootless=("C",),
                               seed=36, delta=0.2, heavy={(2, 1): 20, (3, 7): 8, (3, 2): 20})),
    ]
