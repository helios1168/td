"""territory.py -- the territory pass after the realizer (`docs/MODEL.md` §7 step 6, #116).

Zero-opportunity ZIPs are territory (owner, 2026-10-04): every CONUS ZCTA gets a district in every
planning channel that holds it, and the ledger, not a display fill, assigns it.  A channel's
*footprint* (`footprint`) is every ZIP of the instance in a unit of its domain D_c, the units
dropped for zero opportunity included; the instance holds every CONUS ZCTA on the polygon graph
(#114), so the footprints of the channels that share a fine channel cover CONUS once.

`own_territory` runs on each channel's map after `td.realize.realize`, on the instance's ZIP graph:
1. The ZIPs with opportunity in the channel keep their owners; every zero-opportunity ZIP of the
   footprint is released.
2. **Grow**: breadth first from the owned ZIPs, each released ZIP taking the owner of the ZIP it
   is reached from, first only inside its unit, then inside its state, then across a state
   (`GROW_STAGES`).  A ZIP held across a state splits it (owner, 2026-10-05) and is listed.
3. A ZIP no edge reaches takes the owner of the nearest owned ZIP and stays a detached piece: M1
   fails on it, never patched.
4. **Join** (`join`): a district in pieces takes a shortest path of zero-opportunity ZIPs, inside
   the units where it holds opportunity, from one of its pieces to another of its ZIPs, whoever
   holds the path, when that lowers the total pieces of the district and of those it takes ZIPs
   from and leaves none of those in more pieces than before.  A path stays in units the district holds, so no mode is broken (C16), and no district
   is emptied.
Opportunity never moves, so masses, bands and shares are the realizer's.
"""
from __future__ import annotations

import collections

from td.realize import _d2, _parts, pieces
from td.spec import zip_components

GROW_STAGES = ("unit", "state", "across a state")


def footprint(inst, channel: str) -> set:
    """The ZIPs channel `channel` owns: every ZIP of the instance in a unit of its domain D_c."""
    units = inst.units
    return {z for u in inst.channels[channel].spec.domain for z in units.zips.get(u, ())}


def grow(owner: dict, free: set, adj: dict, same: dict | None = None) -> dict:
    """{zip: district} for the ZIPs of `free` reached breadth first from the ZIPs `owner` holds,
    each taking the owner of the ZIP it is reached from; with `same` ({zip: key}) only across an
    edge whose ends share a key.  `owner` and `free` are updated in place."""
    got, queue = {}, collections.deque(sorted(owner))
    while queue:
        z = queue.popleft()
        for y in sorted(adj.get(z, ())):
            if y in free and (same is None or same.get(y) == same.get(z)):
                free.discard(y)
                owner[y] = got[y] = owner[z]
                queue.append(y)
    return got


def _count(zs, adj: dict) -> int:
    return len(zip_components(zs, adj)) if zs else 0


def _path(part, j, owner: dict, zero: set, allowed: set, adj: dict, unit_of: dict) -> list:
    """The shortest path of `zero` ZIPs in the units `allowed`, from the piece `part` of district
    `j` to another ZIP of `j`, nearest first; empty when there is none."""
    prev, queue, hit, seen = {}, collections.deque(sorted(part)), None, set(part)
    while queue and hit is None:
        z = queue.popleft()
        for y in sorted(adj.get(z, ())):
            if y in seen:
                continue
            if owner.get(y) == j:
                hit = z
                break
            if y in zero and unit_of[y] in allowed:
                seen.add(y)
                prev[y] = z
                queue.append(y)
    path = []
    while hit is not None and hit not in part:
        path.append(hit)
        hit = prev[hit]
    return path


def join(owner: dict, zero: set, adj: dict, unit_of: dict, holds: dict, m: dict) -> list:
    """Step 4 of the module docstring, on `owner` in place: [(zips, district)] for each path
    claimed.  `holds` is {district: units where it holds opportunity}.  Each claim lowers the total
    pieces, so the passes end."""
    region = collections.defaultdict(set)
    for z, j in owner.items():
        region[j].add(z)
    claimed, changed = [], True
    while changed:
        changed = False
        for j in sorted(region):
            for part in _parts(region[j], adj, m)[1:]:
                path = _path(part, j, owner, zero, holds[j], adj, unit_of)
                if not path:
                    continue
                donors = sorted({owner[z] for z in path} - {j})
                after = {k: region[k] - set(path) for k in donors}
                if not all(after.values()):
                    continue                        # a district is never emptied
                was = {k: _count(region[k], adj) for k in donors}
                now = {k: _count(after[k], adj) for k in donors}
                if any(now[k] > was[k] for k in donors):
                    continue                        # no donor is cut into more pieces
                if _count(region[j] | set(path), adj) + sum(now.values()) \
                        >= _count(region[j], adj) + sum(was.values()):
                    continue
                for z in path:
                    owner[z] = j
                region[j] |= set(path)
                region.update(after)
                claimed.append((tuple(sorted(path)), j))
                changed = True
    return claimed


def own_territory(inst, plan, d, xy: dict, state: dict) -> dict:
    """The pass (module docstring) on the channel's map `d` (`td.realize.Drawing`) in place: every
    ZIP of the channel's `footprint` gets an owner and `d.pieces` is taken again.  `xy` is {zip:
    (x, y)} and `state` {zip: state} over the footprint.  Returns what it did: the zero ZIPs it
    released, how many each stage owned, the ZIPs claimed to join pieces, the zero ZIPs whose
    district holds no opportunity in their state, each a split, and those no edge reached."""
    ch, units = inst.channels[d.channel], inst.units
    adj, unit_of, m = units.zip_adj, units.unit_of, ch.m
    owner = {z: j for z, j in d.owner.items() if m.get(z, 0.0) > 0}
    zero = footprint(inst, d.channel) - set(owner)
    free = set(zero)
    holds = collections.defaultdict(set)
    for z, j in owner.items():
        holds[j].add(unit_of[z])
    by_stage = {stage: len(grow(owner, free, adj, same))
                for stage, same in zip(GROW_STAGES, (unit_of, state, None))}
    unreached = sorted(free)
    if owner:
        for z in unreached:
            owner[z] = owner[min(owner, key=lambda y: (_d2(xy[z], xy[y]), y))]
    by_stage["nearest, detached"] = len(unreached)
    claimed = join(owner, zero, adj, unit_of, holds, m)
    d.owner.clear()
    d.owner.update(owner)
    d.pieces = pieces(inst, d.channel, d.owner, {c.name: c.support for c in plan.copies}, d.planned)
    states = collections.defaultdict(set)
    for z, j in owner.items():
        if m.get(z, 0.0) > 0:
            states[j].add(state.get(z))
    return {"zero": len(zero), "by_stage": by_stage,
            "joined": sorted(z for path, _ in claimed for z in path),
            "cross_state": sorted((z, j) for z, j in owner.items()
                                  if z in zero and state.get(z) not in states[j]),
            "unreached": unreached}
