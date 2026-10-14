"""M1's neck rule of 2026-10-14 (owner, answering "which water rule", #131): "(a) Any water crossing. A
neck or detached piece passes if its narrow passage is an approved water connector (bridge, tunnel or
ferry)... Narrow land necks (Cincinnati, El Paso, Utah) would still fail", amended: "(a) except we
should treat necks that are surrounded by empty or zero-opportunity zips the same way we treat water,
which i believe is what happened to el paso"; and "keep the manhattan exception and in general those
water split cases are ok".  R1: a connector is unlimited always (the pre-2026-10-14 land rule is the
opt-in `pre_2026_10_14_land_rule`); R2: land in no ZCTA counts towards a passage (`test_neck_gapwidth`);
R3: ZCTAs of zero opportunity in the district's planning channel do too, whoever owns them."""
import collections
import math
import random

from td import audit
from td.audit import Cell, Channel, Run


def _world(border: dict, state=None, connectors=(), aland=None) -> dict:
    """A polygon graph over the ZCTAs `border` ({(a, b): metres}) names, plus `connectors`."""
    vs = sorted({z for e in list(border) + list(connectors) for z in e})
    return {"vertices": vs, "edges": sorted(set(border) | set(connectors)),
            "state": state or dict.fromkeys(vs, "TX"), "border": dict(border),
            "connectors": list(connectors), "aland": aland or dict.fromkeys(vs, 1e8),
            "voronoi_gaps": {}}


def _m1(poly: dict, owner: dict, mass: dict, k: int = 2, **kw) -> audit.Check:
    """check_m1 of one channel X, one fine channel f: `owner` {zip: district or ""}, `mass` {zip: m}."""
    cells = [Cell(z, "f", "X", owner[z], mass[z]) for z in poly["vertices"]]
    return audit.check_m1(Run(cells, {"X": Channel(k)}, polygon=poly, fine=("f",)), **kw)


def _necks(check: audit.Check) -> list:
    return [i for i in check.items if " neck " in i and audit.MASS_NECK not in i]


# ------------------------------------------------------------ (i) a bridge beside a land route (R1)
def test_a_bridge_passes_though_a_wide_land_route_exists():
    """D1 = m1 + m2 joined only by a bridge; D2's y1 touches both across 20 km (land would do).
    Before 2026-10-14 the bridge counted 0 km there and D1 failed; now the bridge is unlimited."""
    poly = _world({("m1", "y1"): 2e4, ("m2", "y1"): 2e4}, connectors=[("m1", "m2")])
    owner = {"m1": "D1", "m2": "D1", "y1": "D2"}
    mass = dict.fromkeys(owner, 1.0)
    assert _necks(_m1(poly, owner, mass)) == [] and _m1(poly, owner, mass).status == "pass"
    legacy = _m1(poly, owner, mass, land_rule=True)
    assert legacy.status == "fail" and len(_necks(legacy)) == 1, legacy.items
    # a narrow land route (3 km) beside the bridge: it passed under both rules
    narrow = _world({("m1", "y1"): 3e3, ("m2", "y1"): 3e3}, connectors=[("m1", "m2")])
    assert _m1(narrow, owner, mass).status == "pass"
    assert _m1(narrow, owner, mass, land_rule=True).status == "pass"


def test_the_land_rule_is_read_from_the_environment_only_when_asked():
    import os
    poly = _world({("m1", "y1"): 2e4, ("m2", "y1"): 2e4}, connectors=[("m1", "m2")])
    owner = {"m1": "D1", "m2": "D1", "y1": "D2"}
    mass = dict.fromkeys(owner, 1.0)
    old = os.environ.pop(audit.LAND_RULE_ENV, None)
    try:
        assert _m1(poly, owner, mass).status == "pass"
        os.environ[audit.LAND_RULE_ENV] = "1"
        assert _m1(poly, owner, mass).status == "fail"
        assert _m1(poly, owner, mass, land_rule=False).status == "pass"
    finally:
        os.environ.pop(audit.LAND_RULE_ENV, None)
        if old is not None:
            os.environ[audit.LAND_RULE_ENV] = old


# ------------------------------------------- (ii), (iii) a neck across zero-opportunity ZCTAs (R3)
def _empty_land(km_a: float = 20.0, km_b: float = 20.0) -> tuple:
    """D1 = a + b joined by a 1 km polygon edge; z lies beside both, `km_a` and `km_b` wide, and
    touches w (20 km); D2 = z + w.  (poly, owner)"""
    poly = _world({("a", "b"): 1e3, ("a", "z"): km_a * 1e3, ("b", "z"): km_b * 1e3, ("w", "z"): 2e4})
    return poly, {"a": "D1", "b": "D1", "z": "D2", "w": "D2"}


def test_a_neck_across_zero_opportunity_zctas_of_another_district_passes():
    poly, owner = _empty_land()
    mass = {"a": 1.0, "b": 1.0, "z": 0.0, "w": 1.0}
    got = _m1(poly, owner, mass)
    assert got.status == "pass" and got.counts["necks"] == 0, got.items
    # z owned by no one passes the same way (a blank row of an owner-less zero-opportunity ZCTA)
    free = _m1(poly, dict(owner, z=""), mass)
    assert free.counts["necks"] == 0, free.items
    # the passage is as wide as its narrowest link through the empty land: 3 km on one side fails
    for km_a, km_b in ((3.0, 20.0), (20.0, 3.0), (6.0, 6.0)):
        thin, owner2 = _empty_land(km_a, km_b)
        assert len(_necks(_m1(thin, owner2, mass))) == 1, (km_a, km_b)


def test_the_same_neck_across_populated_zctas_still_fails():
    poly, owner = _empty_land()
    got = _m1(poly, owner, {"a": 1.0, "b": 1.0, "z": 0.5, "w": 1.0})
    assert got.status == "fail" and len(_necks(got)) == 1, got.items
    assert _necks(got)[0].startswith("X/D1: neck 1.00 km wide cuts off 1 ZIPs"), got.items


def test_zero_opportunity_is_judged_in_the_districts_own_channel():
    """z has opportunity in channel Y only: in X it is empty, so X's neck passes and Y's does not
    (a ZCTA's rows are summed per planning channel)."""
    poly, owner = _empty_land()
    cells = []
    for z in poly["vertices"]:
        cells.append(Cell(z, "f", "X", owner[z], 0.0 if z == "z" else 1.0))
        cells.append(Cell(z, "g", "Y", owner[z], 1.0 if z == "z" else 0.0))
    got = audit.check_m1(Run(cells, {"X": Channel(2), "Y": Channel(2)}, polygon=poly, fine=("f", "g")))
    necks = _necks(got)
    assert [n.split(":")[0] for n in necks] == ["Y/D1"], got.items


def test_a_relay_chain_and_a_connector_through_empty_land():
    """Two empty ZCTAs in series carry the passage (z1-z2 20 km wide); one 2 km link in the chain
    narrows it.  An approved connector to an empty ZCTA is unlimited."""
    mass = {"a": 1.0, "b": 1.0, "z1": 0.0, "z2": 0.0, "w": 1.0}
    owner = {"a": "D1", "b": "D1", "z1": "D2", "z2": "D2", "w": "D2"}
    for mid, want in ((2e4, 0), (2e3, 1)):
        poly = _world({("a", "b"): 1e3, ("a", "z1"): 2e4, ("z1", "z2"): mid, ("z2", "b"): 2e4,
                       ("w", "z2"): 2e4})
        assert len([n for n in _necks(_m1(poly, owner, mass)) if n.startswith("X/D1:")]) == want, mid
    poly = _world({("a", "b"): 1e3, ("a", "z1"): 2e4, ("z2", "w"): 2e4, ("z1", "z2"): 2e4},
                  connectors=[("b", "z1")])
    assert _necks(_m1(poly, owner, mass)) == []


def test_relays_add_width_only_and_leave_the_pieces_check_alone():
    """A district whose two parts touch only through empty land is still in two pieces; a relay is
    never in a neck's ZIP list or its shares."""
    poly = _world({("a", "z"): 2e4, ("z", "b"): 2e4, ("z", "w"): 2e4})
    owner = {"a": "D1", "b": "D1", "z": "D2", "w": "D2"}
    got = _m1(poly, owner, {"a": 1.0, "b": 1.0, "z": 0.0, "w": 1.0})
    assert got.status == "fail" and got.counts["pieces"] == 1 and got.counts["necks"] == 0, got.items
    # a neck's own ZCTAs: relay z is not listed among the cut-off ZIPs, and holds no share
    poly = _world({("a", "b"): 1e3, ("b", "c"): 2e4, ("z", "c"): 2e4, ("z", "b"): 2e3})
    [nk] = audit.district_necks({"a", "b", "c"}, {}, audit.NeckGraph(poly), free=frozenset({"z"}))
    assert "z" not in nk.zips and nk.zips == ("a",), nk


def test_without_opportunity_in_the_ledger_zero_opportunity_zctas_are_not_counted():
    poly, owner = _empty_land()
    cells = [Cell(z, "f", "X", owner[z], None) for z in poly["vertices"]]
    got = audit.check_m1(Run(cells, {"X": Channel(2)}, polygon=poly, fine=("f",)))
    assert got.counts["necks"] == 1 and "zero-opportunity ZCTAs not counted" in got.summary, got.summary


# ------------------------------------------------- exact against enumeration, with relays (R3)
def _world_with_relays(rng, n: int) -> tuple:
    """(poly, own, free): a path of `n` ZCTAs plus chords, borders around 10 km, a random subset free."""
    vs = [f"v{i}" for i in range(n)]
    edges = {tuple(sorted((vs[i], vs[i + 1]))) for i in range(n - 1)}
    for _ in range(rng.randint(0, n)):
        edges.add(tuple(sorted(rng.sample(vs, 2))))
    edges = sorted(edges)
    border = {e: 1000.0 * rng.choice([0.5, 2, 3, 4, 6, 9.5, 10, 12, 30]) for e in edges}
    conn = [e for e in [tuple(sorted(rng.sample(vs, 2)))] if e not in border and rng.random() < 0.5]
    poly = {"vertices": vs, "edges": edges + conn, "state": dict.fromkeys(vs, "TX"), "border": border,
            "connectors": conn, "aland": {v: rng.choice([1.0, 3.0, 20.0, 100.0]) for v in vs},
            "voronoi_gaps": {}}
    free = set(rng.sample(vs, rng.randint(0, n - 2)))
    return poly, set(vs) - free, free


def _near(poly: dict) -> dict:
    near = collections.defaultdict(set)
    for a, b, *_ in poly["edges"]:
        near[a].add(b)
        near[b].add(a)
    return near


def _narrowest_with_relays(poly: dict, own: set, free: set) -> float:
    """The narrowest neck of `own` in km (inf if none) by trying every vertex set of own + relays:
    a part holding 5% of the land area of `own`, no more than the rest, across a cut under 10 km in
    floored whole cm, whose own ZCTAs are connected among themselves, never through a relay (owner,
    2026-10-06, "One connected piece"); relays hold no land, and a connector is unlimited."""
    relay, stack = set(), list(own)
    near = _near(poly)
    while stack:
        z = stack.pop()
        for y in near[z]:
            if y in free and y not in own and y not in relay:
                relay.add(y)
                stack.append(y)
    vs = sorted(own | relay)
    width = {e: audit.border_cm(m) for e, m in poly["border"].items() if e[0] in vs and e[1] in vs}
    for e in poly["connectors"]:
        if e[0] in vs and e[1] in vs:
            width[e] = math.inf
    adj = _near({"edges": list(width)})
    own_adj = _near({"edges": [e for e in width if e[0] in own and e[1] in own]})
    if len(audit._components(set(vs), adj)) != 1:
        return None
    total = sum(poly["aland"][v] for v in own)
    best = math.inf
    for bits in range(1, 2 ** len(vs) - 1):
        side = {v for i, v in enumerate(vs) if bits >> i & 1}
        held = sum(poly["aland"][v] for v in side if v in own)
        if not (held / total >= audit.NECK_SHARE and held <= total - held):
            continue
        if len(audit._components(side & own, own_adj)) != 1:
            continue
        cut = sum(k for (a, b), k in width.items() if (a in side) != (b in side))
        if cut < audit.NECK_W_CM:
            best = min(best, cut / 1e5)
    return best


def test_the_neck_search_with_relays_is_exact_against_enumeration():
    rng = random.Random(20261014)
    tried = 0
    for _ in range(400):
        poly, own, free = _world_with_relays(rng, rng.randint(3, 9))
        want = _narrowest_with_relays(poly, own, free)
        if want is None or len(own) < 2:
            continue
        tried += 1
        got = audit.district_necks(own, {}, audit.NeckGraph(poly), free=frozenset(free))
        assert all(nk.status == "proved" for nk in got), got
        width = min((nk.width_km for nk in got), default=math.inf)
        assert width == want or abs(width - want) < 1e-9, (poly, own, free, got, want)
        assert all(set(nk.zips) <= own for nk in got), got
    assert tried > 100, tried


# ------------------------------------- R5: land-only gap edges join a district's pieces (#140)
def _gap_pieces_world(**extra) -> tuple:
    """D1 = a + b with no polygon edge between them, D2 = c touching both 20 km; `extra` goes into the
    polygon graph (`gaps`: land-only gap land, `voronoi_gaps`: Voronoi rows that may cross water)."""
    poly = dict(_world({("a", "c"): 2e4, ("b", "c"): 2e4}), **extra)
    if "gaps" in extra:
        del poly["voronoi_gaps"]            # the land-only widths stand in for the Voronoi rows
    return poly, {"a": "D1", "b": "D1", "c": "D2"}, dict.fromkeys("abc", 1.0)


def test_two_parts_separated_only_by_land_in_no_zcta_are_one_piece():
    """Owner, 2026-10-14, recorded on #140 ("yes"): in the pieces check two ZCTAs of one state that face
    each other across land in no ZCTA are adjacent, by the land-only gap edges of `zcta_gap_land.csv.gz`
    (`polygon["gaps"]`), behind the same default-on switch as G1."""
    poly, owner, mass = _gap_pieces_world(gaps={("a", "b"): 3e4})
    got = _m1(poly, owner, mass)
    assert got.status == "pass" and got.counts["pieces"] == 0 and got.counts["gap_edges"] == 1, got.items
    # the opt-out reads the polygon edges alone: the district is in two pieces
    off = _m1(poly, owner, mass, gap_width=False)
    assert off.status == "fail" and off.counts["pieces"] == 1 and off.counts["gap_edges"] == 0, off.items
    # across a state line the pair is no gap edge
    other = dict(poly, state={"a": "TX", "b": "NM", "c": "TX"})
    assert _m1(other, owner, mass).counts["pieces"] == 1


def test_the_same_parts_across_water_stay_two_pieces():
    """A pair only the Voronoi rows give (`voronoi_gaps`, which can cross water) widens a neck's passage
    (G1, owner 2026-10-08, #131) but never joins pieces (R5 reads the land-only rows alone): the
    district stays in two pieces, and a graph with no land-only gap file says R5 is inactive."""
    poly, owner, mass = _gap_pieces_world(voronoi_gaps={("a", "b"): 3e4}, gaps={})
    poly["voronoi_gaps"] = {("a", "b"): 3e4}
    got = _m1(poly, owner, mass)
    assert got.status == "fail" and got.counts["pieces"] == 1 and got.counts["gap_edges"] == 0, got.items
    assert "R5 inactive" in got.summary, got.summary
    assert audit.adjacency(poly, gaps=True)["a"] == {"c"}
    assert audit.adjacency(dict(poly, gaps={("a", "b"): 3e4}), gaps=True)["a"] == {"b", "c"}
    assert audit.adjacency(dict(poly, gaps={("a", "b"): 3e4}))["a"] == {"c"}      # off by default here


# ------------------------------- relays give width, never connect the cut-off part (owner, 2026-10-06)
def test_fringes_that_touch_only_through_a_relay_do_not_add_up_to_a_neck():
    """h holds 94% of the land; a, b and c (2% each) each touch h across 1 km and a relay z across 20
    km, and each other not at all.  With z free the three are one connected part only through z, a
    ZCTA the district does not own, so they are three 2% fringes, no part holding the 5% share:
    "One connected piece" (owner, 2026-10-06, #121).  Made one piece by a polygon edge among them, or
    by an owned z, the same 6% across the same 3 km is a neck."""
    border = {("h", v): 1000.0 for v in "abc"}
    border.update({(v, "z"): 20000.0 for v in "abc"})
    land = {"h": 94.0, "a": 2.0, "b": 2.0, "c": 2.0, "z": 50.0}
    g = audit.NeckGraph(_world(border, aland=land))
    assert audit.district_necks(set("habc"), {}, g) == []
    assert audit.district_necks(set("habc"), {}, g, free={"z"}) == []
    # owned: z joins the district (a, b, c, z then hold 56 of 150, a neck on a cut of 3 km only if z
    # is part of the district and the three still reach h through 1 km edges)
    [nk] = audit.district_necks(set("habcz"), {}, g)
    assert set(nk.zips) <= set("abcz") and nk.width_km == 3.0, nk
    # a polygon edge among the fringes makes them one part: 6% over 1 + 1 + 20 km... narrow via h
    joined = audit.NeckGraph(_world({**border, ("a", "b"): 3000.0, ("b", "c"): 3000.0}, aland=land))
    [nk] = audit.district_necks(set("habc"), {}, joined, free={"z"})
    assert nk.zips == ("a", "b", "c") and nk.width_km == 3.0, nk


def test_fringes_linked_only_by_a_voronoi_gap_are_two_fringes():
    """h holds 94% of the land, a and b 3% each, each touching h across 1 km and each other not at all
    on a polygon edge.  A Voronoi row a-b (`voronoi_gaps`, may cross water) widens passages (G1) but does
    not join the district's own ZCTAs into one part (owner, 2026-10-06, "One connected piece"; R5 reads
    the land-only rows alone): two 3% fringes, no neck.  The same pair as a land-only gap row (`gaps`,
    R5) is one 6% part on a 2 km cut: a neck."""
    border = {("h", "a"): 1000.0, ("h", "b"): 1000.0}
    land = {"h": 94.0, "a": 3.0, "b": 3.0}
    voronoi = dict(_world(border, aland=land), voronoi_gaps={("a", "b"): 2e4})
    assert audit.district_necks(set("hab"), {}, audit.NeckGraph(voronoi)) == []
    land_only = dict(_world(border, aland=land), gaps={("a", "b"): 2e4})
    del land_only["voronoi_gaps"]
    [nk] = audit.district_necks(set("hab"), {}, audit.NeckGraph(land_only))
    assert nk.zips == ("a", "b") and nk.width_km == 2.0, nk
    assert audit.district_necks(set("hab"), {}, audit.NeckGraph(land_only, gap_width=False)) == []
