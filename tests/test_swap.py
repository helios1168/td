"""td.swap: the swap pass toward τ inside split units, and repair's exchange-component guard (#85).

The pass is checked against #85's acceptance on toys: each exchange component's worst deviation
does not grow, every move keeps both districts' piece counts, no ZIP leaves its exchange
component, and repair crosses components only when the worse district of the pair improves.
"""
from __future__ import annotations

import collections
import random

from td import realize, swap

from tests import test_realize as tr


def _parts(owner, adj, m) -> dict:
    return {j: len(realize._parts(zs, adj, m)) for j, zs in realize._districts(owner).items()}


def _worst(mass: dict, tau: float, comp: dict) -> dict:
    out = collections.defaultdict(float)
    for j, x in mass.items():
        out[comp[j]] = max(out[comp[j]], abs(x - tau))
    return out


def _masses(owner, m) -> dict:
    out = collections.Counter()
    for z, j in owner.items():
        out[j] += m[z]
    return out


# ------------------------------------------------------------------------------ components
def test_components_link_districts_through_shared_units_only():
    planned = {("AL", "a"): 1.0, ("AL", "b"): 2.0, ("AR", "b"): 1.0, ("AR", "c"): 0.5,
               ("AZ", "c"): 3.0, ("AZ", "d"): 0.0, ("CA", "d"): 4.0, ("CO", "e"): 2.0}
    assert swap.sharing(planned) == {"AL": {"a", "b"}, "AR": {"b", "c"}}
    assert swap.components(planned) == {"a": "a", "b": "a", "c": "a", "d": "d", "e": "e"}


def test_stays_joined_refuses_a_cut_vertex_and_allows_a_cycle():
    adj = {"s": {"l1", "l2", "l3"}, "l1": {"s"}, "l2": {"s"}, "l3": {"s"}}
    assert not swap.stays_joined("s", {"s", "l1", "l2"}, adj)
    assert swap.stays_joined("l1", {"s", "l1", "l2"}, adj)
    ring = {f"r{i}": {f"r{(i - 1) % 4}", f"r{(i + 1) % 4}"} for i in range(4)}
    assert swap.stays_joined("r0", set(ring), ring)


# ------------------------------------------------------------------------------ the pass
def _shared_grid():
    """AL, a 4 × 2 grid of unit ZIPs, shared by AL#1 (columns 0–2) and AL#2 (column 3); AR, one
    unit ZIP beside column 0, held whole by AR#1.  K = 3, τ = 3."""
    al, edges, mass, xy = tr._grid("v", 4, 2)
    edges.append((al[0, 0], "u0"))
    inst, _ = tr._toy({"AL": list(al.values()), "AR": ["u0"]}, edges, {**mass, "u0": 1.0},
                      {**xy, "u0": (-1.0, 0.0)}, {"AL": "free"}, k=3, delta=0.5)
    owner = {z: ("AL#2" if i == 3 else "AL#1") for (i, _), z in al.items()}
    owner["u0"] = "AR#1"
    planned = {("AL", "AL#1"): 4.0, ("AL", "AL#2"): 4.0, ("AR", "AR#1"): 1.0}
    return inst, owner, planned


def test_the_pass_balances_a_shared_unit_and_never_crosses_a_component():
    """AL#1 6, AL#2 2: two moves give 4 and 4, the component's worst falling from 3 to 1.  AR#1
    at 1 would gain from AL#1's ZIP beside it, but shares no unit with it and gets nothing."""
    inst, owner, planned = _shared_grid()
    ch = inst.channels["X"]
    assert abs(ch.tau - 3.0) < 1e-12
    before = _parts(owner, inst.units.zip_adj, ch.m)
    moves = swap.swap(inst, "X", owner, planned)
    assert len(moves) == 2 and all((j, k) == ("AL#1", "AL#2") for _, j, k in moves)
    mass = _masses(owner, ch.m)
    assert mass == {"AL#1": 4.0, "AL#2": 4.0, "AR#1": 1.0}
    assert owner["u0"] == "AR#1"
    assert _parts(owner, inst.units.zip_adj, ch.m) == before == {"AL#1": 1, "AL#2": 1, "AR#1": 1}


def test_the_pass_refuses_a_move_that_cuts_the_donor():
    """A star: centre s and leaves l1, l2 in AL#1, leaf l3 in AL#2.  Giving s to AL#2 would
    balance 3 / 1 at 2 / 2 but leave l1 and l2 apart, so the pass makes no move."""
    zs = ["s", "l1", "l2", "l3"]
    inst, _ = tr._toy({"AL": zs}, [("s", "l1"), ("s", "l2"), ("s", "l3")], dict.fromkeys(zs, 1.0),
                      {"s": (0.0, 0.0), "l1": (-1.0, 0.0), "l2": (0.0, 1.0), "l3": (1.0, 0.0)},
                      {"AL": "free"}, k=2, delta=0.5)
    owner = {"s": "AL#1", "l1": "AL#1", "l2": "AL#1", "l3": "AL#2"}
    assert swap.swap(inst, "X", owner, {("AL", "AL#1"): 2.0, ("AL", "AL#2"): 2.0}) == []
    assert owner["s"] == "AL#1"


def test_the_pass_never_grows_a_detached_piece():
    """AL = p0–…–p5 of unit ZIPs; AL#1 holds p0–p4 (5), AL+AR#1 holds AR's r0–r1 (2) and p5 (1),
    a detached piece.  τ = 4: giving p4 to AL+AR#1 would balance 5 / 3 at 4 / 4, but p4 touches
    only its piece, not its main component, so the pass makes no move."""
    ps = [f"p{i}" for i in range(6)]
    inst, _ = tr._toy({"AL": ps, "AR": ["r0", "r1"]}, [*zip(ps, ps[1:]), ("r0", "r1")],
                      dict.fromkeys([*ps, "r0", "r1"], 1.0),
                      {**{z: (float(i), 0.0) for i, z in enumerate(ps)}, "r0": (0.0, 5.0),
                       "r1": (1.0, 5.0)}, {"AL": "free"}, k=2, delta=0.5)
    owner = {**dict.fromkeys(ps[:5], "AL#1"), "p5": "AL+AR#1", "r0": "AL+AR#1", "r1": "AL+AR#1"}
    planned = {("AL", "AL#1"): 4.0, ("AL", "AL+AR#1"): 2.0, ("AR", "AL+AR#1"): 2.0}
    assert abs(inst.channels["X"].tau - 4.0) < 1e-12
    assert swap.swap(inst, "X", owner, planned) == [] and owner["p4"] == "AL#1"


def test_the_pass_keeps_every_planned_share_drawn():
    """AL#1 holds unit B (mass 5) and z1 of AL; AL+B#1 would come within 0.5 of τ = 4.5 by
    giving z1 to AL#2, but z1 is its last ZIP in AL, so the share would vanish (C8): no move."""
    inst, _ = tr._toy({"AL": ["z1", "z2"], "AR": ["b0"]}, [("z1", "z2"), ("z1", "b0")],
                      {"z1": 1.0, "z2": 3.0, "b0": 5.0},
                      {"z1": (0.0, 0.0), "z2": (1.0, 0.0), "b0": (-1.0, 0.0)},
                      {"AL": "free"}, k=2, delta=0.5)
    owner = {"z1": "AL+B#1", "b0": "AL+B#1", "z2": "AL#1"}
    planned = {("AL", "AL+B#1"): 1.0, ("AR", "AL+B#1"): 5.0, ("AL", "AL#1"): 3.0}
    assert swap.swap(inst, "X", owner, planned) == []


def test_the_realizer_s_swaps_meet_the_acceptance_on_random_units():
    """#69's three-unit layout (AR + AL, AL, AZ + AL, AL free) with random masses and shares.
    Undo the realizer's swaps to get the map before the pass, then replay them: every move goes
    between districts planned in the ZIP's unit, keeps both districts' piece counts, and lowers
    the worse of the pair; each exchange component's worst deviation does not grow."""
    rng, swaps = random.Random(85), 0
    for _ in range(40):
        v, ve, vm, vp = tr._grid("v", rng.randint(6, 12), rng.randint(2, 5))
        u, ue, um, up = tr._grid("u", 3, 3, x0=-3.0)
        w, we, wm, wp = tr._grid("w", 3, 3, x0=20.0)
        mass = {z: (0.0 if rng.random() < 0.15 else rng.lognormvariate(0.0, 1.0))
                for z in [*v.values(), *u.values(), *w.values()]}
        nx = max(i for i, _ in v) + 1
        edges = ve + ue + we + [(u[2, 0], v[0, 0]), (v[nx - 1, 0], w[0, 0])]
        inst, xy = tr._toy({"AL": list(v.values()), "AR": list(u.values()), "AZ": list(w.values())},
                           edges, mass, {**vp, **up, **wp}, {"AL": "free"}, k=3, delta=0.9)
        ch, adj = inst.channels["X"], inst.units.zip_adj
        if min(ch.M.values()) <= 0:
            continue
        y = [rng.uniform(0.1, 1.0) for _ in range(3)]
        y = [x / sum(y) for x in y]
        plan = tr._plan(inst, [({"AR", "AL"}, {"AR": 1.0, "AL": y[0]}), ({"AL"}, {"AL": y[1]}),
                               ({"AZ", "AL"}, {"AZ": 1.0, "AL": y[2]})])
        d = realize.realize(inst, plan, xy)
        comp, share = swap.components(d.planned), swap.sharing(d.planned)
        owner = dict(d.owner)
        for z, j, k in reversed(d.swapped):
            assert owner[z] == k
            owner[z] = j
        start = _masses(owner, ch.m)
        for z, j, k in d.swapped:
            assert {j, k} <= share[inst.units.unit_of[z]] and comp[j] == comp[k]
            parts, now = _parts(owner, adj, ch.m), _masses(owner, ch.m)
            mj, mk = now[j], now[k]
            main_k = realize._parts([y for y, o in owner.items() if o == k], adj, ch.m)[0]
            assert set(adj[z]) & set(main_k), (z, k)                # no piece grows
            owner[z] = k
            after = _parts(owner, adj, ch.m)
            assert after[j] <= parts[j] and after[k] <= parts[k], (z, j, k)
            wz = ch.m[z]
            assert swap.worse(ch.tau, mj - wz, mk + wz) < swap.worse(ch.tau, mj, mk)
        assert owner == d.owner
        swaps += len(d.swapped)
        old, new = _worst(start, ch.tau, comp), _worst(d.mass, ch.tau, comp)
        assert all(new[c] <= old[c] + 1e-9 for c in old), (old, new)
    assert swaps > 40, swaps


# ------------------------------------------------------------------------------ repair's guard
def _cross_toy(u_mass):
    """`tests.test_realize._guard_toy("free")` with AR's two ZIPs at `u_mass` each: AL#1 holds
    v0 and v3 of AL, so {v3} is detached; AR#1, alone in its exchange component, is the only
    neighbour the band lets take it."""
    zs = ["v0", "v1", "v2", "v3", "u0", "u1"]
    mass = {"v0": 1.5, "v1": 1.5, "v2": 1.5, "v3": 1.0, "u0": u_mass, "u1": u_mass}
    edges = [("v0", "v1"), ("v1", "v2"), ("v2", "v3"), ("v3", "u0"), ("u0", "u1")]
    inst, _ = tr._toy({"AL": zs[:4], "AR": zs[4:]}, edges, mass,
                      {z: (float(i), 0.0) for i, z in enumerate(zs)}, {"AL": "free"}, k=3,
                      delta=0.4)
    owner = {"v0": "AL#1", "v3": "AL#1", "v1": "AL#2", "v2": "AL#2", "u0": "AR#1", "u1": "AR#1"}
    support = {"AL#1": frozenset({"AL"}), "AL#2": frozenset({"AL"}), "AR#1": frozenset({"AR"})}
    planned = {("AL", "AL#1"): 2.5, ("AL", "AL#2"): 3.0, ("AR", "AR#1"): 2.0 * u_mass}
    return inst, owner, support, swap.components(planned)


def test_repair_crosses_exchange_components_only_when_the_worse_district_improves():
    """AR mass 2 (τ 2.5): moving {v3} takes AL#1 2.5 → 1.5 and AR#1 2 → 3, worse 0.5 → 1, so it
    stays.  AR mass 1 (τ 13/6): AL#1 2.5 → 1.5 and AR#1 1 → 2, worse 7/6 → 2/3, so it moves."""
    inst, owner, support, comp = _cross_toy(1.0)
    assert comp == {"AL#1": "AL#1", "AL#2": "AL#1", "AR#1": "AR#1"}
    lo, hi = inst.channels["X"].final_band
    assert lo <= 1.5 <= hi and lo <= 3.0 <= hi                      # the band would allow it
    assert realize.repair(inst, "X", owner, support, comp) == []
    assert owner["v3"] == "AL#1"
    inst, owner, support, comp = _cross_toy(0.5)
    assert realize.repair(inst, "X", owner, support, comp) == [(("v3",), "AL#1", "AR#1")]
    assert owner["v3"] == "AR#1"
