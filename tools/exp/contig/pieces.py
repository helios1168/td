"""pieces.py -- #127's county pieces: a state cut into connected groups of whole counties, each
piece and the state's remainder holding about one district's mass and passing M1 on its own.

A state of mass m τ (τ = the channel's total / K) gets n = round(m) parts, at least 2: n − 1
pieces named `<state>_p1`, `<state>_p2`, ... and the remainder, which keeps the state's name
(`td.spec` carves the pieces out of it).  A county's ZIPs are those whose 2025 reference county is
it, `td.spec.carve`'s rule; two counties touch when a ZIP of one borders a ZIP of the other on
the instance's ZIP graph (M1's polygon graph).  A county whose ZIPs fall apart on the graph is
first tied to the county its detached ZIPs touch most (`atoms`), so a part holding it can be one
piece.

A cut (`attempt`) seeds n parts at heavy atoms far apart (the heaviest, then each atom with the
largest √mass × distance to the seeds so far), grows them together, the lightest part taking the
untaken touching atom nearest its mass centroid, and then moves border atoms to a lighter part
while that brings both nearer the target m τ / n, keeps the giver connected and fails M1 in no
more of the two (`check` on the part's ZIP set, `wholeplan.m1_verdict`).  The part with the most
atoms is the remainder.  `cut_state` makes `ATTEMPTS` cuts, the first greedy and the others
randomised from `RNG_SEED`, and keeps the cut whose parts all pass M1 with the worst part nearest
the target.  A single county heavier than τ stays whole and is listed (`big_counties`).
"""
from __future__ import annotations

import collections
import math
import random

from td import spec as tdspec

ATTEMPTS = 100              # cuts tried per state
RNG_SEED = 127


def connected(nodes, adj: dict) -> bool:
    """True when `nodes` is one component on `adj` (or empty)."""
    nodes = set(nodes)
    if not nodes:
        return True
    start = next(iter(nodes))
    seen, stack = {start}, [start]
    while stack:
        for y in adj[stack.pop()]:
            if y in nodes and y not in seen:
                seen.add(y)
                stack.append(y)
    return len(seen) == len(nodes)


def county_zips(inst, ref, state: str) -> dict:
    """{county: set of ZIPs} of `state`'s counties: the instance's ZIPs whose reference county is
    one of them (`td.spec.carve`'s rule)."""
    fp = tdspec._STATEFP[state]
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    out = collections.defaultdict(set)
    for z, cty in zip(rows.index, rows["county"]):
        if str(cty).startswith(fp):
            out[str(cty)].add(z)
    return dict(out)


def atoms(zips: dict, zadj: dict) -> dict:
    """{atom id: set of counties}: each county, tied to the county its detached ZIPs (those off its
    largest component on `zadj`) touch most, transitively."""
    of = {z: cty for cty, zs in zips.items() for z in zs}
    parent = {cty: cty for cty in zips}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for cty, zs in sorted(zips.items()):
        comps = _components(zs, zadj)
        for comp in comps[1:]:
            touch = collections.Counter(of[y] for z in comp for y in zadj[z]
                                        if y in of and of[y] != cty)
            if touch:
                other = max(sorted(touch), key=lambda x: touch[x])
                parent[find(cty)] = find(other)
    out = collections.defaultdict(set)
    for cty in zips:
        out[find(cty)].add(cty)
    return dict(out)


def _components(zs, adj) -> list:
    left, out = set(zs), []
    while left:
        start = min(left)
        seen, stack = {start}, [start]
        while stack:
            for y in adj[stack.pop()]:
                if y in left and y not in seen:
                    seen.add(y)
                    stack.append(y)
        out.append(seen)
        left -= seen
    return sorted(out, key=lambda c: (-len(c), min(c)))


def attempt(n: int, adj: dict, mass: dict, xy: dict, target: float, passes,
            rng: random.Random | None) -> list:
    """One cut (module docstring) of the atoms of `adj` into n parts: [atom lists], the remainder
    last, or None when the parts cannot cover the atoms.  `passes(atoms)` is whether the part
    passes M1; a border atom moves to a lighter part when that brings both nearer the target and
    fails no more of the two.  `rng` None is the greedy cut."""
    every = sorted(adj)

    def d(a, b):
        return math.hypot(xy[a][0] - xy[b][0], xy[a][1] - xy[b][1])
    seeds = [max(every, key=lambda a: (mass[a], a))] if rng is None else \
        [rng.choice(sorted(every, key=lambda a: (-mass[a], a))[:4])]
    while len(seeds) < n:
        score = sorted((a for a in every if a not in seeds),
                       key=lambda a: (-math.sqrt(mass[a]) * min(d(a, s) for s in seeds), a))
        seeds.append(score[0] if rng is None else rng.choice(score[:4]))
    part = {a: i for i, a in enumerate(seeds)}
    tot = [mass[a] for a in seeds]
    members = [[a] for a in seeds]

    def centre(i):
        w = math.fsum(mass[a] for a in members[i]) or 1.0
        return (math.fsum(xy[a][0] * mass[a] for a in members[i]) / w,
                math.fsum(xy[a][1] * mass[a] for a in members[i]) / w)
    while len(part) < len(every):           # the lightest part with room takes its nearest atom
        grew = False
        for i in sorted(range(n), key=lambda i: (tot[i], i)):
            cand = sorted({y for a in members[i] for y in adj[a] if y not in part})
            if not cand:
                continue
            c = centre(i)
            cand.sort(key=lambda y: ((xy[y][0] - c[0]) ** 2 + (xy[y][1] - c[1]) ** 2, y))
            y = cand[1] if rng is not None and len(cand) > 1 and rng.random() < 0.3 else cand[0]
            part[y] = i
            members[i].append(y)
            tot[i] += mass[y]
            grew = True
            break
        if not grew:
            return None
    for _ in range(4 * len(every)):         # move a border atom to a lighter part while it helps
        moves = []
        for a in every:
            i = part[a]
            for j in sorted({part[y] for y in adj[a]} - {i}):
                old = max(abs(tot[i] - target), abs(tot[j] - target))
                new = max(abs(tot[i] - mass[a] - target), abs(tot[j] + mass[a] - target))
                if new < old - 1e-12:
                    moves.append((new - old, a, i, j))
        for _, a, i, j in sorted(moves):
            rest = [x for x in members[i] if x != a]
            if not rest or not connected(rest, adj):
                continue
            fails = (not passes(members[i])) + (not passes(members[j]))
            if (not passes(rest)) + (not passes(members[j] + [a])) <= fails:
                members[i], part[a] = rest, j
                members[j].append(a)
                tot[i] -= mass[a]
                tot[j] += mass[a]
                break
        else:
            break
    order = sorted(range(n), key=lambda i: (len(members[i]), i))     # the remainder: most atoms
    return [sorted(members[i]) for i in order]


def cut_state(inst, ref, c: str, state: str, tau: float, check, ng_adj: dict, ng) -> tuple:
    """([td.spec.Piece], record) for one state (module docstring)."""
    m, zadj = inst.channels[c].m, inst.units.zip_adj
    zips = county_zips(inst, ref, state)
    groups = atoms(zips, zadj)
    azips = {a: {z for cty in cs for z in zips[cty]} for a, cs in groups.items()}
    of = {z: a for a, zs in azips.items() for z in zs}
    adj = collections.defaultdict(set)
    for z, a in of.items():
        for y in zadj[z]:
            b = of.get(y)
            if b is not None and b != a:
                adj[a].add(b)
    mass = {a: math.fsum(m.get(z, 0.0) for z in zs) for a, zs in azips.items()}
    pts = ref.set_index("zcta")
    xy = {}
    for a, zs in azips.items():
        r = pts.loc[sorted(zs)]
        xy[a] = (float(r["x"].astype(float).mean()) / 1000.0,
                 float(r["y"].astype(float).mean()) / 1000.0)
    total = math.fsum(mass.values())
    n = max(2, round(total / tau))
    target = total / n
    county_mass = {cty: math.fsum(m.get(z, 0.0) for z in zs) for cty, zs in zips.items()}
    rec = {"state": state, "mass_tau": total / tau, "parts": n, "target_tau": target / tau,
           "attempts": ATTEMPTS, "tied_counties": sorted("+".join(sorted(cs))
                                                       for cs in groups.values() if len(cs) > 1),
           "big_counties": sorted(f"{cty} {x / tau:.2f} τ" for cty, x in county_mass.items()
                                  if x > tau)}

    def zset(xs):
        return {z for a in xs for z in azips[a]}

    verdicts, best, fails = {}, None, collections.Counter()

    def verdict(p):
        key = frozenset(p)
        if key not in verdicts:
            verdicts[key] = check(zset(p), m, ng_adj, ng)
        return verdicts[key]

    def passes(p):
        return verdict(p)["status"] == "pass"
    rng = random.Random(RNG_SEED)
    for t in range(ATTEMPTS):
        parts = attempt(n, {a: adj[a] for a in azips}, mass, xy, target, passes,
                        None if t == 0 else rng)
        if parts is None:
            fails["no cover"] += 1
            continue
        err = max(abs(math.fsum(mass[a] for a in p) - target) for p in parts) / tau
        if best is not None and err >= best[0]:
            continue
        bad = [verdict(p)["why"] for p in parts if not passes(p)]
        for why in bad[:1]:
            fails[why.split(" wide")[0][:60]] += 1
        if not bad:
            best = (err, parts)
    rec["rejections"] = dict(fails.most_common(8))
    if best is None:
        raise RuntimeError(f"{state}: no cut into {n} parts passes M1 in {ATTEMPTS} attempts: "
                           f"{dict(fails.most_common(5))}")
    out = []
    rec["pieces"] = []
    for i, p in enumerate(best[1][:-1], 1):
        counties = frozenset(cty for a in p for cty in groups[a])
        out.append(tdspec.Piece(f"{state}_p{i}", state, counties))
        rec["pieces"].append({"name": f"{state}_p{i}", "counties": len(counties),
                              "zips": len(zset(p)), "mass_tau": math.fsum(mass[a] for a in p) / tau})
    rest = best[1][-1]
    rec["remainder"] = {"name": state, "counties": sum(len(groups[a]) for a in rest),
                        "zips": len(zset(rest)), "mass_tau": math.fsum(mass[a] for a in rest) / tau}
    rec["worst_part_error_tau"] = best[0]
    return out, rec


def state_pieces(inst, ref, c: str, k: int, states, check) -> tuple:
    """([td.spec.Piece], {state: record}) for each of `states`, at τ = the channel's total / `k`;
    `check` judges a ZIP set (`wholeplan.m1_verdict`)."""
    from td import audit, geo
    polygon = geo.polygon_graph()
    ng_adj, ng = audit.adjacency(polygon), audit.NeckGraph(polygon)
    tau = math.fsum(inst.channels[c].M.values()) / k
    out, recs = [], {}
    for st in states:
        ps, recs[st] = cut_state(inst, ref, c, st, tau, check, ng_adj, ng)
        out += ps
    return out, recs
