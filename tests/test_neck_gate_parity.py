"""The neck checks that run before the gate (window repair, plan check, whole-unit plans, glue) judge
a district as `td.audit.check_m1` does (#142; `notes/2026-10-14_national-approaches-review.md` §2
C14, C15, §3.1): zero-opportunity ZCTAs of the channel are relays whoever owns them (R3), and the
width graph is the gate's (polygon borders, gap edges, connectors under the #140 rule).

C14's counterexample: X = {a, b}, equal land, a 1 km polygon edge between them; r, of zero
opportunity and owned elsewhere, touches both across 20 km.  The gate accepts X (separating a from
b costs 21 km); a check without r finds a 1 km neck.  A true neck (no relay, or a relay with
opportunity) fails all of them.  A `draw.NeckCut` row is valid under the gate's model: no drawing
the gate accepts breaks it (`necks_gate.cut_terms`)."""
from __future__ import annotations

import importlib.util
import itertools
import os
import random
import sys

from td import audit
from td.audit import Cell, Channel, Run

from tests import test_realize as tr

HERE = os.path.dirname(os.path.abspath(__file__))
QUIET = dict(log=lambda *_: None)


def _module(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(HERE, "..", "tools", "exp", "contig", file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def _mods():
    gate = _module("contig_necks_gate", "necks_gate.py")
    repair = _module("contig_repair", "repair.py")
    plancheck = _module("contig_plancheck", "plancheck.py")
    wholeplan = _module("contig_wholeplan", "wholeplan.py")
    glue = _module("contig_glue", "glue.py")
    return gate, repair, plancheck, wholeplan, glue


def _c14(r_mass: float, relay: bool = True):
    """(instance, polygon): unit PA = {a, b} (mass 1 each, 1e8 m² each, a 1 km edge a-b), and with
    `relay` unit NY = {r} of mass `r_mass` touching a and b across 20 km each.  The channel has
    τ = 2: K 1 when r has no opportunity (its unit is dropped), K 2 when it has 2."""
    zips = {"PA": ["a", "b"]}
    edges, km = [("a", "b")], {("a", "b"): 1.0}
    mass, xy = {"a": 1.0, "b": 1.0}, {"a": (0.0, 0.0), "b": (1.0, 0.0)}
    if relay:
        zips["NY"] = ["r"]
        edges += [("a", "r"), ("b", "r")]
        km.update({("a", "r"): 20.0, ("b", "r"): 20.0})
        mass["r"], xy["r"] = r_mass, (0.5, 1.0)
    inst, _ = tr._toy(zips, edges, mass, xy, k=2 if r_mass > 0 and relay else 1, delta=0.1, eta=0.05)
    polygon = {"vertices": sorted(mass), "edges": sorted(edges), "state": dict(inst.units.unit_of),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": dict.fromkeys(mass, 1e8), "voronoi_gaps": {}}
    return inst, polygon


def _gate_necks(polygon: dict, owner: dict, mass: dict) -> list:
    """The neck items `check_m1` lists for a one-channel map: `owner` {zip: district}, `mass`."""
    cells = [Cell(z, "f", "X", owner[z], mass[z]) for z in polygon["vertices"]]
    check = audit.check_m1(Run(cells, {"X": Channel(2)}, polygon=polygon, fine=("f",)))
    return [i for i in check.items if " neck " in i and audit.MASS_NECK not in i]


def _verdicts(inst, polygon: dict, owner: dict) -> dict:
    """Each pre-gate check's neck count for the district D1 = {a, b}, and the gate's."""
    gate, repair, plancheck, wholeplan, glue = _mods()
    mass = {z: inst.channels["X"].m.get(z, 0.0) for z in polygon["vertices"]}
    ng = gate.gate_graph(polygon)
    m = gate.channel_mass(inst, "X")
    d1 = {z for z, j in owner.items() if j == "D1"}
    ch = inst.channels["X"]
    v = plancheck.drawable(inst, "X", frozenset({"PA"}), ch.spec.delta, ng, 60.0, **QUIET)
    wp = wholeplan.m1_verdict(d1, m, audit.adjacency(polygon), ng)
    necks_of, _ = glue.neck_counter(polygon, m)
    return {"gate": len(_gate_necks(polygon, owner, mass)),
            "repair": len(repair.district_necks(d1, m, ng)),
            "repair.necks": len(repair.necks(owner, m, ng, ["D1"])),
            "plancheck": 0 if v["status"] == "drawable" else v,
            "wholeplan": 0 if wp["status"] == "pass" else wp,
            "glue": len(necks_of(d1))}


def test_a_zero_opportunity_relay_owned_elsewhere_is_accepted_by_every_check_c14():
    """The review's C14: the gate, repair's and plancheck's checks, whole-unit plans and glue all
    accept X = {a, b} with the 20 km relay r owned by D2, and none finds a neck."""
    inst, polygon = _c14(0.0)
    assert "NY" in inst.channels["X"].dropped_units       # r's unit has no opportunity: dropped
    owner = {"a": "D1", "b": "D1", "r": "D2"}
    got = _verdicts(inst, polygon, owner)
    assert got == {"gate": 0, "repair": 0, "repair.necks": 0, "plancheck": 0, "wholeplan": 0,
                   "glue": 0}, got
    # without the relay's zero-opportunity masses (the old calls: `ch.m` alone) the 1 km edge is a neck
    gate, repair, *_ = _mods()
    ng = gate.gate_graph(polygon)
    assert len(audit.district_necks({"a", "b"}, inst.channels["X"].m, ng)) == 1
    assert repair.neck_cuts("X", owner, {"a"}, gate.channel_mass(inst, "X"), ng, {"a": "D1"}, {"D1"}) \
        == ([], [])


def test_a_true_neck_is_rejected_by_every_check():
    """The same X with no relay at all, and with r holding opportunity (never a relay): a 1 km neck
    cuts a (50% of the land) off, and the gate, repair, plancheck, wholeplan and glue all find it."""
    for inst, polygon in (_c14(0.0, relay=False), _c14(2.0)):
        owner = {"a": "D1", "b": "D1", "r": "D2"} if "r" in polygon["vertices"] else \
            {"a": "D1", "b": "D1"}
        got = _verdicts(inst, polygon, owner)
        assert got["gate"] == got["repair"] == got["repair.necks"] == got["glue"] == 1, got
        assert got["plancheck"]["status"] == "infeasible" and got["plancheck"]["why"].startswith("neck"), got
        assert got["wholeplan"]["status"] == "fail" and got["wholeplan"]["why"].startswith("neck"), got


def test_a_relay_narrower_than_the_limit_leaves_the_neck():
    """r touches a and b across 3 km each: the cheapest cut costs 1 + 3 = 4 km, still a neck."""
    inst, polygon = _c14(0.0)
    polygon["border"] = {**polygon["border"], ("a", "r"): 3000.0, ("b", "r"): 3000.0}
    got = _verdicts(inst, polygon, {"a": "D1", "b": "D1", "r": "D2"})
    assert got["gate"] == got["repair"] == got["glue"] == 1, got
    assert got["plancheck"]["status"] == "infeasible", got


# ------------------------------------------------------------------------------ NeckCut rows
def _random_world(rng: random.Random, p_zero: float = 0.35):
    """A small polygon graph in one state: 9 ZCTAs, random borders of 0.3 to 14 km, a few
    connectors and Voronoi gap edges, random land, a third of them of zero opportunity."""
    zs = [f"z{i}" for i in range(9)]
    pairs = [e for e in itertools.combinations(zs, 2) if rng.random() < 0.4]
    border = {e: 1000.0 * rng.choice([0.3, 1.0, 2.5, 4.0, 7.0, 14.0, 20.0]) for e in pairs}
    conn = [e for e in pairs if rng.random() < 0.12]
    gaps = {e: 1000.0 * rng.choice([1.0, 5.0, 12.0]) for e in itertools.combinations(zs, 2)
            if e not in border and rng.random() < 0.1}
    polygon = {"vertices": zs, "edges": sorted(pairs), "state": dict.fromkeys(zs, "TX"),
               "border": border, "connectors": conn,
               "aland": {z: rng.choice([1e6, 1e7, 5e7, 1e8, 3e8]) for z in zs}, "voronoi_gaps": gaps}
    m = {z: (0.0 if rng.random() < p_zero else 1.0) for z in zs}
    return polygon, m


def _own_connected(zs: set, ng) -> bool:
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


def test_a_neck_cut_row_is_broken_by_no_drawing_the_gate_accepts():
    """On random small graphs with relays, width-only (gap) edges and connectors: the rows
    `repair.neck_cuts` builds from one drawing of a window hold for every other own-connected
    drawing of the window in which district D1 has no gate neck (`necks_gate.cut_terms`)."""
    gate, repair, *_ = _mods()
    rng = random.Random(142)
    built = checked = 0
    for _ in range(260):
        polygon, m = _random_world(rng)
        ng = gate.gate_graph(polygon)
        zs = polygon["vertices"]
        W = set(rng.sample(zs, rng.randint(2, 5)))
        base = {z: rng.choice(["D1", "D2"]) for z in zs if z not in W}
        draws = [{z: rng.choice(["D1", "D2"]) for z in sorted(W)} for _ in range(14)]
        for first in draws[:3]:
            cuts, _ = repair.neck_cuts("X", base, W, m, ng, first, {"D1"})
            built += len(cuts)
            for other in draws:
                d1 = {z for z, j in {**base, **other}.items() if j == "D1"}
                if not _own_connected(d1, ng) or repair.district_necks(d1, m, ng):
                    continue
                checked += 1
                bad = [c.label for c in cuts if not c.holds(other)]
                assert not bad, (bad, sorted(d1), polygon, m)
    assert built >= 20 and checked >= 200, (built, checked)


def test_a_neck_cut_counts_the_relay_the_old_row_missed():
    """a (10 km²) hangs off b by a 1 km edge, and c (50 km²) joins b across 20 km; r, of zero
    opportunity and owned by D2, touches a and b across 3 km each.  The gate's cheapest cut of a
    costs 1 + 3 = 4 km, a neck.  The row for the window {r} counts that 4 km (the old row 1 km),
    and the drawing that leaves r to D2, with the neck, does not meet it."""
    gate, repair, *_ = _mods()
    km = {("a", "b"): 1.0, ("a", "r"): 3.0, ("b", "r"): 3.0, ("b", "c"): 20.0}
    polygon = {"vertices": list("abcr"), "edges": sorted(km), "state": dict.fromkeys("abcr", "TX"),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"a": 1e7, "b": 1e8, "c": 5e7, "r": 1e8}, "voronoi_gaps": {}}
    m = {"a": 1.0, "b": 1.0, "c": 1.0, "r": 0.0}
    ng = gate.gate_graph(polygon)
    owner = {"a": "D1", "b": "D1", "c": "D1", "r": "D2"}
    [nk] = repair.district_necks({"a", "b", "c"}, m, ng)
    assert nk.zips == ("a",) and abs(nk.width_km - 4.0) < 1e-6, nk
    cuts, labels = repair.neck_cuts("X", owner, {"r"}, m, ng, {"r": "D2"}, {"D1"})
    assert len(labels) == 1 and len(cuts) == 1
    cut = cuts[0]
    assert abs(cut.const + sum(w for _, w in cut.single) - 4.0) < 1e-3, cut     # a-b 1 + a-r 3
    assert not cut.holds({"r": "D2"})
    # a side holding more than half the land outside the window (here a alone is fixed) also counts
    # the edges among the rest (`cut_terms`): a weaker row, still broken by the neck drawing
    cuts, labels = repair.neck_cuts("X", {"a": "D1", "r": "D2"}, {"b", "c"}, m, ng,
                                    {"b": "D1", "c": "D1"}, {"D1"})
    assert len(labels) == 1 and len(cuts) == 1
    assert cuts[0].const + sum(w for _, w in cuts[0].single) + sum(w for *_, w in cuts[0].pair) > 4.0


def test_a_neck_cut_counts_the_relay_edge_an_owned_window_relay_cuts():
    """Five ZCTAs, D1 = {a, b, c} (a, r1 the window): a hangs off b by 1.5 km and joins c across
    12 km; r2 (D2's, outside the window) and r1 (window) have no opportunity, r2 touching b and c
    across 3 and 12 km and r1 across 12, r1 touching b across 3.  With r1 D2's the gate finds a neck;
    if D1 owns r1 it accepts D1 (r2 is then a relay of the fixed part, with r1 cut off from it by
    12 km).  The row built on the first map must hold on the second, which needs the r1-r2 edge that
    owning r1 cuts, and must still break the first."""
    gate, repair, *_ = _mods()
    km = {("a", "b"): 1.5, ("a", "c"): 12.0, ("b", "r1"): 3.0, ("b", "r2"): 3.0, ("c", "r2"): 12.0,
          ("r1", "r2"): 12.0}
    zs = ["a", "b", "c", "r1", "r2"]
    polygon = {"vertices": zs, "edges": sorted(km), "state": dict.fromkeys(zs, "TX"),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"a": 1e7, "b": 1e8, "c": 5e7, "r1": 1e6, "r2": 1e6}, "voronoi_gaps": {}}
    m = {"a": 1.0, "b": 1.0, "c": 1.0, "r1": 0.0, "r2": 0.0}
    ng = gate.gate_graph(polygon)
    base = {"b": "D1", "c": "D1", "r2": "D2"}
    first, other = {"a": "D1", "r1": "D2"}, {"a": "D1", "r1": "D1"}
    assert repair.district_necks({"a", "b", "c"}, m, ng)               # the first map has a neck
    assert not repair.district_necks({"a", "b", "c", "r1"}, m, ng)      # the drawing the gate accepts
    cuts, labels = repair.neck_cuts("X", base, {"a", "r1"}, m, ng, first, {"D1"})
    assert len(labels) == 1 and len(cuts) == 1
    assert not cuts[0].holds(first)                         # the neck drawing is still cut
    assert cuts[0].holds(other), cuts[0]                    # the accepted drawing is not


def test_a_widened_neck_cut_counts_an_optional_zero_opportunity_window_zip_as_a_relay():
    """Five ZCTAs, D1 = {c, r1} plus a and b (the window is {a, b, r2}; r1 and r2 have no
    opportunity).  The first map gives D1 a, b and leaves r2 to D2: the gate cuts r1 off (4 km).
    The map that leaves b to D2 is connected and the gate accepts it, with r2 a relay of D1 that the
    widened row must count: the optional zero ZCTA r2 is a possible relay (`bridged`'s candidates)."""
    gate, repair, *_ = _mods()
    zs = ["a", "b", "c", "r1", "r2"]
    km = {("a", "r1"): 2.0, ("a", "r2"): 9.0, ("b", "c"): 12.0, ("b", "r2"): 12.0, ("c", "r1"): 2.0,
          ("c", "r2"): 9.0}
    polygon = {"vertices": zs, "edges": sorted(km), "state": dict.fromkeys(zs, "TX"),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"a": 1e7, "b": 1e8, "c": 5e7, "r1": 1e8, "r2": 1e8}, "voronoi_gaps": {}}
    m = {"a": 1.0, "b": 1.0, "c": 1.0, "r1": 0.0, "r2": 0.0}
    ng = gate.gate_graph(polygon)
    base = {"c": "D1", "r1": "D1"}
    first = {"a": "D1", "b": "D1", "r2": "D2"}
    other = {"a": "D1", "b": "D2", "r2": "D2"}
    assert _own_connected(set(base) | {"a", "b"}, ng) and _own_connected(set(base) | {"a"}, ng)
    cuts, _ = repair.neck_cuts("X", base, {"a", "b", "r2"}, m, ng, first, {"D1"})
    assert len(cuts) == 1
    cells = [Cell(z, "f", "X", {**base, **other}[z], m[z]) for z in zs]
    check = audit.check_m1(Run(cells, {"X": Channel(2)}, polygon=polygon, fine=("f",)))
    assert check.status == "pass", check
    assert all(cut.holds(other) for cut in cuts), cuts


def test_replan_plans_with_the_gates_neck_graph_under_both_switches(tmp_path=None):
    """`replan.main` with `drawable_alone` hands `plancheck.plan_checked` the gate's graph
    (`necks_gate.gate_graph`), at the declared δ and again after a channel moved to its smallest δ:
    `TD_NECK_GAP_WIDTH` = "0" drops the width-only gap edge, `TD_NECK_PRE_2026_10_14_LAND_RULE` = "1"
    turns the pre-2026-10-14 land rule on, as `audit.check_m1` reads them (the old `audit.NeckGraph`
    call ignored both)."""
    import tempfile
    import types
    gate, *_ = _mods()
    replan = _module("contig_replan", "replan.py")
    plancheck = replan._plancheck()
    zs = ["a", "b", "r"]
    polygon = {"vertices": zs, "edges": [("a", "b")], "state": dict.fromkeys(zs, "TX"),
               "border": {("a", "b"): 5000.0}, "connectors": [], "aland": dict.fromkeys(zs, 1e8),
               "voronoi_gaps": {("a", "r"): 7000.0}}
    spec = types.SimpleNamespace(drawable_alone=True, window=False, delta=0.05, final_delta=0.1)
    inst = types.SimpleNamespace(channels={"X": types.SimpleNamespace(spec=spec)}, polygon=polygon)
    plan = types.SimpleNamespace(objective=0.0, copies=[])
    out = {}

    def run(env: dict) -> list:
        """The `ng` of each `plan_checked` call of one `replan.main`, under `env`."""
        seen, calls = [], []
        saved = {k: os.environ.pop(k, None) for k in (audit.GAP_WIDTH_ENV, audit.LAND_RULE_ENV)}
        os.environ.update(env)
        orig = (replan.build, plancheck.plan_checked, plancheck.checked_delta, replan.master.smallest_delta)

        def plan_checked(inst, c, checks=None, ng=None, **kw):
            seen.append(ng)
            calls.append(len(calls))
            return (None, {"status": "infeasible"}, {}) if len(calls) == 1 else \
                (plan, {"status": "optimal"}, {})
        try:
            replan.build = lambda spec_path, extract: (None, inst)
            plancheck.plan_checked = plan_checked
            plancheck.checked_delta = lambda *a, **k: {"steps": [], "delta": 0.07, "status": "optimal",
                                                       "lower": 0.06}
            replan.master.smallest_delta = lambda *a, **k: replan.master.Delta(
                "X", "bisection", "optimal", 0.07, 0.06, replan.master.DELTA_TOL)
            with tempfile.TemporaryDirectory() as d:
                src = os.path.join(d, "in.toml")
                with open(src, "w", encoding="utf-8") as fh:
                    fh.write("[channels.X]\ndelta = 0.05\n")
                rc = replan.main([src, "--out-spec", os.path.join(d, "out.toml"), "--plans",
                                  os.path.join(d, "plans"), "--keep", "--extract", src])
            assert rc == 0
        finally:
            replan.build, plancheck.plan_checked, plancheck.checked_delta, \
                replan.master.smallest_delta = orig
            for k in (audit.GAP_WIDTH_ENV, audit.LAND_RULE_ENV):
                os.environ.pop(k, None)
                if saved[k] is not None:
                    os.environ[k] = saved[k]
        return seen
    for name, env in (("default", {}), ("no gap width", {audit.GAP_WIDTH_ENV: "0"}),
                      ("old land rule", {audit.LAND_RULE_ENV: "1"})):
        ngs = run(env)
        assert len(ngs) == 2, (name, ngs)           # at the declared δ and after the move
        for ng in ngs:
            want = gate.gate_graph(polygon, gap_width=env.get(audit.GAP_WIDTH_ENV) != "0",
                                   land_rule=env.get(audit.LAND_RULE_ENV) == "1")
            assert ng.land_rule == (env.get(audit.LAND_RULE_ENV) == "1"), (name, ng.land_rule)
            assert ("r" in ng.border_cm.get("a", {})) == (env.get(audit.GAP_WIDTH_ENV) != "0"), name
            assert {k: dict(v) for k, v in ng.border_cm.items()} == \
                {k: dict(v) for k, v in want.border_cm.items()}, name
        out[name] = ngs[0]
    assert out["default"].border_cm["a"].get("r") and "r" not in out["no gap width"].border_cm.get("a", {})
    assert out["old land rule"].land_rule and not out["default"].land_rule


def test_bridged_flags_a_relay_touching_two_nodes_and_a_width_only_edge():
    gate, *_ = _mods()
    inst, polygon = _c14(0.0)
    ng, m = gate.gate_graph(polygon), gate.channel_mass(inst, "X")
    zero = gate.zero_opportunity(m)
    assert zero == {"r"}
    assert gate.bridged({"a", "b"}, set(), ng, zero)            # r touches a and b: a path round the edge
    assert not gate.bridged({"a", "b"}, set(), ng, frozenset())  # nothing zero: a plain graph
    assert not gate.bridged({"a", "b"}, set(), ng, zero, node_of=lambda z: "body")
    gappy = dict(polygon, border={("a", "b"): 1000.0}, edges=[("a", "b")], state=dict.fromkeys("abr", "PA"),
                 voronoi_gaps={("a", "r"): 5000.0})
    ng2 = gate.gate_graph(gappy)
    assert gate.bridged({"a"}, {"r"}, ng2, frozenset())          # a-r is a width edge and no own edge


# ------------------------------------------------------------------------------ a real district
def test_a_real_district_repairs_check_and_the_gate_agree():
    """On the national main map ne-50-bal (FI-WH-national, draw), every district of the national
    channel: the necks `repair.necks` lists are the ones `check_m1` lists, the same sides and
    widths.  SKIP without the run and the 2025 geography."""
    import csv
    repo = os.environ.get("TD_REPO") or os.path.join(HERE, "..")
    run_dir = os.path.join(repo, "runs", "exp", "national_2026-10-14", "main", "ne-50-bal",
                           "rest-FI-WH-national", "draw")
    from td import geo
    try:
        polygon = geo.polygon_graph()
        with open(os.path.join(run_dir, "ledger.csv"), newline="", encoding="utf-8") as fh:
            ledger = [r for r in csv.DictReader(fh) if r["model_channel"] == "national"]
    except (OSError, FileNotFoundError, ValueError) as e:
        print(f"SKIP  test_neck_gate_parity.py: no run {run_dir} or geography ({type(e).__name__})",
              flush=True)
        return
    gate, repair, *_ = _mods()
    cells = [Cell(r["zip_code"], r["current_channel"], r["model_channel"], r["district"],
                  float(r["m_rel"]), reason=r.get("reason", "")) for r in ledger]
    ks = len({r["district"] for r in ledger if r["district"]})
    check = audit.check_m1(Run(cells, {"national": Channel(ks)}, polygon=polygon, fine=None))
    theirs = sorted(i for i in check.items if " neck " in i and audit.MASS_NECK not in i)
    m, owner = {}, {}
    for r in ledger:
        m[r["zip_code"]] = m.get(r["zip_code"], 0.0) + float(r["m_rel"])
        if r["district"]:
            owner[r["zip_code"]] = r["district"]
    ng = gate.gate_graph(polygon)
    ours = sorted(audit.neck_item("national", j, nk) for j, _, nk in repair.necks(owner, m, ng))
    assert ours == theirs, (ours, theirs)
    assert gate.zero_opportunity(m), "the channel has zero-opportunity ZCTAs"


def test_a_wide_passage_flow_reaches_the_limit_in_every_district_the_gate_accepts_unless_bridged():
    """The plan check's wide-passage rows (`plancheck.wide_rows`, `necks_gate.bridged`): on random
    small graphs, a district the gate accepts, with two own-connected bodies each holding the share
    of its land, carries a flow of `NECK_KM` between them over the gate's widths, whenever
    `bridged` is False.  (Bridged districts are not claimed: it takes a cut through a relay to
    break the flow.)"""
    import networkx as nx
    gate, repair, *_ = _mods()
    rng = random.Random(1424)
    share = audit.NECK_SHARE * (1 - audit.NECK_TOL)
    tried = unbridged = bridged_broken = 0
    for _ in range(1500):
        polygon, m = _random_world(rng, rng.choice([0.0, 0.15, 0.35]))
        ng = gate.gate_graph(polygon)
        zero = gate.zero_opportunity(m)
        zs = polygon["vertices"]
        d = set(rng.sample(zs, rng.randint(4, 8)))
        if not _own_connected(d, ng) or repair.district_necks(d, m, ng):
            continue
        bodies = []
        for _b in range(2):                 # two own-connected bodies, disjoint, grown at random
            free = sorted(d - set().union(*bodies)) if bodies else sorted(d)
            if not free:
                break
            body, front = {rng.choice(free)}, []
            for _s in range(rng.randint(0, 3)):
                front = [y for z in body for y in free if y not in body and ng.own_edge(z, y)]
                if front:
                    body.add(rng.choice(sorted(front)))
            bodies.append(body)
        if len(bodies) < 2:
            continue
        land = lambda zz: sum(polygon["aland"][z] for z in zz)
        if min(land(b) for b in bodies) < share * land(d):
            continue
        fixed = set().union(*bodies)
        node = lambda z: f"@{0 if z in bodies[0] else 1}" if z in fixed else z
        flow = nx.DiGraph()
        states = frozenset({"TX"})
        for z in d:
            for y in gate.width_nbrs(ng, z):
                if y in d and node(z) != node(y):
                    w = gate.edge_km(ng, z, y, states)
                    cur = flow.get_edge_data(node(z), node(y), {"capacity": 0.0})["capacity"]
                    flow.add_edge(node(z), node(y), capacity=min(cur + w, gate.NECK_KM))
        flow.add_nodes_from(["@0", "@1"])
        tried += 1
        value = nx.maximum_flow_value(flow, "@0", "@1")
        is_bridged = gate.bridged(fixed, d - fixed, ng, zero, node)
        if not is_bridged:
            unbridged += 1
            assert value >= gate.NECK_KM - 1e-9, (value, sorted(d), bodies, polygon, m)
        elif value < gate.NECK_KM - 1e-9:
            bridged_broken += 1
    assert tried >= 40 and unbridged >= 10, (tried, unbridged)
    assert bridged_broken >= 1, "bridged districts never broke the flow: the test does not reach the case"
