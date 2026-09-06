"""atom_draw.py -- stage 1 on an atom graph: k balanced districts, contiguity enforced.

The power-cell route (`centers.py`) abandons contiguity, because v2's zip adjacency has 862
components over 3,748 zips and no contiguous k-partition of it exists.  Pre-aggregating zips
into **state atoms** removes that obstacle: whole states, with only the oversized ones cut into
pieces, sit on the TIGER state rook graph, which is connected.  `td/atoms.py` builds the atoms;
this module draws on them.

The search is a multi-restart seeded growth plus a connectivity-checked local search, scoring
`sum_j log M_j` -- the same stage-1 objective `centers.metrics` reports.  It is a heuristic
with a bound, not an exact method: `draw` returns the argmax over `restarts` seeded runs and
`cert_draw.cert_balance_ceiling` supplies the valid upper bound.

What is a bound here and what is not
------------------------------------
`cert_draw.cert_balance_ceiling` is the bound: Jensen gives `sum_j log M_j <= k log(T/k)` for
**every** partition of the atoms, contiguous or not, so the draw's distance from it is a real
optimality gap.

`free_search` is **not** a bound, despite what the prototype this module replaces claimed.  It
is a local search over the contiguity-dropped problem, so it returns some feasible relaxed
value `F <= U*`, where `U*` is the relaxed optimum.  The contiguous optimum `C*` also satisfies
`C* <= U*`.  Those two facts order neither `F` nor `C*` against the other, so `F` is a lower
bound on the relaxation and says nothing about the draw.  The prototype's own docstring records
the symptom: a move-only version "was beaten by the contiguity-constrained draw itself on one
scenario, which is impossible for a true bound".  Adding swaps stopped the losses observed; it
did not make the quantity sound.  `free_search` is kept because it measures how much of the gap
to the ceiling is contiguity rather than search quality, and it is reported under that name.

Determinism
-----------
Set iteration over atom **names** decides tie-breaks in three places -- `_grow`'s
`min(frontier[i], ...)`, `_polish`'s destination set, and (via `td.atoms.atom_graph`'s edge
insertion order) `graph.neighbors` for the whole run.  String hashing is randomised per
process, so a run **requires `PYTHONHASHSEED=0`** to reproduce; without it the answer moves by
roughly 0.015 nats.  Every RNG is explicitly seeded, so that is the only source.  This is a
deliberate choice to keep the 2026-09-05 measurements reproducible rather than a defect to
route around; `tools/run_atoms.py` refuses to run without the variable set.

Scale
-----
`_polish` calls `nx.is_connected` inside its inner loop, which is fine at the ~56 atoms a
state model produces and quadratic nonsense at zip scale.  This module is for atom graphs.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

import networkx as nx
import numpy as np

from . import centers


def allocate(mass: dict, comps: list, k: int) -> list:
    """Seats per component, proportional to mass, at least one each.

    `comps` are the atom graph's connected components, heaviest first.  A component cannot be
    split across seats it does not have, and a seat cannot straddle components, so the split
    has to happen before the search.  Rounding is repaired by taking from the largest
    allocation when over and giving to the component with the worst mass-per-seat when under.
    """
    share = [sum(mass[a] for a in c) for c in comps]
    tot = sum(share)
    alloc = [max(1, int(round(k * s / tot))) for s in share]
    while sum(alloc) > k:
        i = max(range(len(alloc)), key=lambda i: alloc[i])
        if alloc[i] > 1:
            alloc[i] -= 1
        else:
            break
    while sum(alloc) < k:
        i = max(range(len(alloc)), key=lambda i: share[i] / alloc[i])
        alloc[i] += 1
    return alloc


def _grow(g, mass, kc, rng):
    """Seeded multi-source growth: kc connected districts covering a **connected** `g`.

    Each step gives the currently lightest district the lightest atom on its frontier, which is
    what keeps the districts near equal mass rather than near equal count.
    """
    nodes = list(g.nodes())
    seeds = rng.sample(nodes, kc)
    lab = {s: i for i, s in enumerate(seeds)}
    load = [mass[s] for s in seeds]
    frontier = {i: {w for w in g.neighbors(seeds[i]) if w not in lab} for i in range(kc)}
    remaining = len(nodes) - kc
    while remaining > 0:
        cands = [i for i in range(kc) if frontier[i]]
        # `g` is connected, so while any node is unlabelled some district's frontier is
        # non-empty: on a path from a labelled node to an unlabelled one, the first unlabelled
        # node is a neighbour of a labelled one and therefore on that district's frontier.
        assert cands, "grow called on a disconnected graph"
        i = min(cands, key=lambda i: load[i])
        v = min(frontier[i], key=lambda v: mass[v])
        if v in lab:
            frontier[i].discard(v)
            continue
        lab[v] = i
        load[i] += mass[v]
        remaining -= 1
        for j in range(kc):
            frontier[j].discard(v)
        frontier[i] |= {w for w in g.neighbors(v) if w not in lab}
    return lab


def _polish(g, mass, lab, kc, rounds=60):
    """Border **moves** that raise `sum_j log M_j` and keep every district connected.

    Moves only -- one atom at a time, to a district that already touches it.  Swaps exist in
    `free_search`, where there is no contiguity to preserve; here a swap would need two
    connectivity checks and a joint acceptance test for a gain that the move pass mostly
    finds anyway.

    The destination is drawn from `v`'s own neighbours, so the receiving district stays
    connected for free; only the source needs checking, and it is rejected if losing `v`
    would disconnect it or empty it.
    """
    members = defaultdict(set)
    for v, i in lab.items():
        members[i].add(v)
    load = [sum(mass[v] for v in members[i]) for i in range(kc)]

    def connected(sub):
        return len(sub) > 0 and nx.is_connected(g.subgraph(sub))

    improved = True
    r = 0
    while improved and r < rounds:
        improved = False
        r += 1
        for v in list(lab):
            i = lab[v]
            if len(members[i]) == 1:
                continue
            if not connected(members[i] - {v}):
                continue
            for j in {lab[w] for w in g.neighbors(v)} - {i}:
                ni, nj = load[i] - mass[v], load[j] + mass[v]
                if ni <= 0:
                    continue
                if (math.log(ni) + math.log(nj)) > (math.log(load[i]) + math.log(load[j])) + 1e-12:
                    members[i].discard(v)
                    members[j].add(v)
                    lab[v] = j
                    load[i], load[j] = ni, nj
                    improved = True
                    break
    return lab, load, r


def check_contiguous(graph, atom_district: dict, k: int) -> None:
    """Raise `ValueError` unless the draw is a partition into k non-empty connected districts.

    The whole claim of this route is contiguity, so it is verified rather than assumed.
    """
    missing = set(graph.nodes) - set(atom_district)
    if missing:
        raise ValueError(f"{len(missing)} atoms unassigned, e.g. {sorted(missing)[:5]}")
    members = defaultdict(set)
    for a, d in atom_district.items():
        members[d].add(a)
    if len(members) != k or set(members) != set(range(k)):
        raise ValueError(f"expected districts 0..{k - 1}, got {sorted(members)}")
    for d, part in sorted(members.items()):
        if not nx.is_connected(graph.subgraph(part)):
            comps = sorted(len(c) for c in nx.connected_components(graph.subgraph(part)))
            raise ValueError(f"district {d} is disconnected: component sizes {comps}")


def draw(graph, mass: dict, k: int, *, seed: int = 0, restarts: int = 250,
         polish_rounds: int = 60, stateless_mass: float = 0.0) -> dict:
    """`restarts` seeded grow-and-polish runs on `graph`; the best by `sum_j log M_j`.

    Returns the `centers.draw` shape -- everything `centers.metrics` reports, plus `seed`,
    `restarts` and `converged` -- with `atoms` (the atom order the labels index),
    `atom_district` (`{atom: district}`), `seats_per_component`, and `stateless_district`.
    There is no `centers` key and no `compactness`: atoms carry no coordinates.

    Districts are numbered by descending mass, so district 0 is the heaviest.  `stateless_mass`
    is the opportunity of zips the instance carries no state for; it belongs to no atom, so it
    is added to the lightest district after the draw and the districts are re-ordered.  That
    rule is a documented placeholder, not a decision -- see `td.atoms`.

    Raises `ValueError` if any atom mass is non-positive (`log M_j` would be `-inf`), if `k` is
    smaller than the number of components or larger than the number of atoms, or if the winning
    draw is not contiguous.
    """
    bad = sorted(a for a in mass if mass[a] <= 0)
    if bad:
        raise ValueError(f"every atom needs positive opportunity, {len(bad)} do not: {bad[:5]}")
    comps = sorted(nx.connected_components(graph), key=lambda c: -sum(mass[a] for a in c))
    if not 1 <= k <= len(mass):
        raise ValueError(f"k={k} with {len(mass)} atoms")
    if k < len(comps):
        raise ValueError(f"k={k} cannot cover {len(comps)} components")
    alloc = allocate(mass, comps, k)

    best = None
    for s in range(restarts):
        rng = random.Random(seed + s)
        parts, rounds_used, ok = [], 0, True
        for c, kc in zip(comps, alloc):
            sub = graph.subgraph(c).copy()
            if kc > sub.number_of_nodes():
                ok = False
                break
            lab = _grow(sub, mass, kc, rng)
            lab, _load, r = _polish(sub, mass, lab, kc, rounds=polish_rounds)
            rounds_used = max(rounds_used, r)
            mem = defaultdict(set)
            for v, i in lab.items():
                mem[i].add(v)
            parts += [mem[i] for i in range(kc) if mem[i]]
        if not ok or len(parts) != k:
            continue
        val = sum(math.log(sum(mass[a] for a in p)) for p in parts)
        if best is None or val > best[0]:
            best = (val, parts, s, rounds_used)
    if best is None:
        raise ValueError(f"no {k}-district draw found in {restarts} restarts")

    _val, parts, best_restart, rounds_used = best
    parts = sorted(parts, key=lambda p: -sum(mass[a] for a in p))
    masses = [sum(mass[a] for a in p) for p in parts]
    stateless_district = None
    if stateless_mass:
        masses[-1] += stateless_mass
        order = sorted(range(len(masses)), key=lambda i: -masses[i])
        stateless_district = order.index(len(masses) - 1)
        masses = [masses[i] for i in order]
        parts = [parts[i] for i in order]

    atom_district = {a: d for d, p in enumerate(parts) for a in p}
    check_contiguous(graph, atom_district, k)

    atoms = sorted(mass)
    labels = np.array([atom_district[a] for a in atoms], int)
    out = dict(atoms=atoms, atom_district=atom_district, labels=labels, seed=seed,
               restarts=restarts, best_restart=best_restart, rounds_used=rounds_used,
               converged=rounds_used < polish_rounds,
               n_components=len(comps), seats_per_component=alloc,
               stateless_mass=float(stateless_mass), stateless_district=stateless_district)
    # the stateless bucket enters `metrics` as one more unit, so `masses` and `nash` cover the
    # instance's whole mass; `sizes` then counts it as a single atom, which is what it is here
    M_arr, lab_arr = [mass[a] for a in atoms], list(labels)
    if stateless_mass:
        M_arr.append(float(stateless_mass))
        lab_arr.append(int(stateless_district))
    out.update(centers.metrics(np.array(M_arr, float), np.array(lab_arr, int)))
    return out


def free_search(mass: dict, k: int, *, init=None, seed: int = 100, restarts: int = 14,
                rounds: int = 500_000) -> float:
    """Best contiguity-dropped k-partition found by local search.  A reference, NOT a bound.

    Moves and swaps on random pairs of districts, accepting strict improvements in
    `sum_j log M_j`.  Restart 0 is warm-started from `init` (the contiguous draw's parts) when
    given, otherwise longest-processing-time greedy; later restarts are a shuffled round-robin.

    **This is not an upper bound on the draw**, and the module docstring says why: it is a
    local search over the relaxation, so it returns a feasible relaxed value that is itself
    below the relaxed optimum, which orders it against nothing.  Use
    `cert_draw.cert_balance_ceiling` for the bound.  What this measures is how much of the gap
    to that ceiling is contiguity rather than search quality -- with the same atoms and the
    constraint dropped, how far can a partition get?

    The warm start exists so the comparison is meaningful: dropping a constraint cannot lower
    the optimum, so a relaxed search that came in below a known-feasible contiguous draw would
    be reporting only its own weakness.
    """
    names = list(mass)
    w = [mass[a] for a in names]
    pos = {a: i for i, a in enumerate(names)}
    best = -math.inf
    for s in range(restarts):
        rng = random.Random(seed + s)
        groups = [[] for _ in range(k)]
        load = [0.0] * k
        if init is not None and s == 0:
            groups = [[pos[a] for a in p if a in pos] for p in init]
            groups += [[] for _ in range(k - len(groups))]
            load = [sum(w[i] for i in g) for g in groups]
        elif s == 0:
            for i in sorted(range(len(w)), key=lambda i: -w[i]):
                j = min(range(k), key=lambda j: load[j])
                groups[j].append(i)
                load[j] += w[i]
        else:
            idx = list(range(len(w)))
            rng.shuffle(idx)
            for t, i in enumerate(idx):
                groups[t % k].append(i)
            load = [sum(w[i] for i in g) for g in groups]
        if min(load) <= 0:
            continue
        cur = sum(math.log(x) for x in load)
        for _ in range(rounds):
            a, b = rng.randrange(k), rng.randrange(k)
            if a == b or not groups[a]:
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
                    groups[a].remove(i)
                    groups[b].append(i)
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
                    groups[a].remove(i)
                    groups[b].remove(j)
                    groups[a].append(j)
                    groups[b].append(i)
                    load[a], load[b], cur = na, nb, new
        best = max(best, cur)
    return best


def to_district(zips_of: dict, atom_district: dict, stateless: list = (),
                stateless_district: int = None) -> dict:
    """`{zip_id: district}` -- the atom analogue of `centers.to_district`.

    Every zip behind an atom takes that atom's district.  `stateless` zips belong to no atom
    and go to `stateless_district`, the one `draw` added their mass to; passing them without a
    district is an error, since silently dropping them would make the map disagree with the
    mass the draw was scored on.
    """
    out = {z: atom_district[a] for a, zs in zips_of.items() for z in zs}
    if stateless:
        if stateless_district is None:
            raise ValueError(f"{len(stateless)} stateless zips but no district for them")
        out.update({z: int(stateless_district) for z in stateless})
    return out
