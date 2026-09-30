"""td.spec: the TOML scenario, the domain partition, units, modes and the connectivity stop (#67).

The toy instances name their units after states, since a scenario's units are the CONUS states
plus its pieces and metros.  The fixture tests need TIGER/Line 2025 state polygons
(`tl_2025_us_state.zip` in `data/public/`, or `$TD_REPO`'s); with neither they print SKIP and
return.  The rest read only the committed `reference/2025/`.
"""
from __future__ import annotations

import copy
import functools
import os
import sys
import tomllib
import types

from td import data, geo, spec

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCENARIOS = os.path.join(ROOT, "scenarios")
S51 = os.path.join(SCENARIOS, "51_total_13n_11wh_24fi_3wifi.toml")


def _raises(fn, *needles):
    try:
        fn()
    except spec.SpecError as e:
        for n in needles:
            assert n in str(e), (n, str(e))
        return str(e)
    raise AssertionError("no SpecError")


def _toy_raw(**channel):
    ch = {"k": 2, "domain": [{"units": "all", "fine": ["f", "g"]}], "eta": 0.1}
    ch.update(channel)
    return {"scenario": {"name": "toy", "fine_channels": ["f", "g"]}, "channels": {"X": ch}}


def _toy(unit_zips: dict, edges, cells: dict, **channel):
    """A one-channel toy over `unit_zips` {unit: [zip, ...]}, ZIPs on a line 1 km apart."""
    s = spec.parse(_toy_raw(**channel))
    unit_of = {z: u for u, zs in unit_zips.items() for z in zs}
    xy = {z: (1000.0 * i, 0.0) for i, z in enumerate(sorted(unit_of))}
    return s, spec.Units.from_graph(unit_of, edges, xy), cells


@functools.cache
def _reference():
    return geo.read_reference()


@functools.cache
def _state_file():
    for public in (geo.PUBLIC_DIR, os.path.join(os.environ.get("TD_REPO", ""), "data", "public")):
        path = os.path.join(public, "tl_2025_us_state.zip")
        if os.path.exists(path) and geo._valid_download(path):
            return public
    print("SKIP  test_spec.py: no tl_2025_us_state.zip in data/public or $TD_REPO/data/public; "
          "the fixture spec tests did not run", file=sys.stderr)
    return None


@functools.cache
def _fixture(channels):
    public = _state_file()
    if public is None:
        return None
    return data.fixture(0, channels=channels, reference=_reference(),
                        state_polys=data.state_polygons(public))


def _all_conus(s):
    """Every CONUS ZCTA with mass 1 in each of the scenario's fine channels."""
    zs, fs = list(_reference()["zcta"]), s.fine_channels
    n = len(zs) * len(fs)
    return data.Extract(tuple(fs), [z for z in zs for _ in fs], [f for _ in zs for f in fs],
                        [1.0] * n, [{}] * n, [0.0] * n)


# ------------------------------------------------------------------------------ the partition
def test_partition_rejects_a_gap():
    raw = _toy_raw(domain=[{"units": "all", "fine": ["f"]}, {"units": ["AL"], "fine": ["g"]}])
    msg = _raises(lambda: spec.parse(raw), "no channel", "(AR, g)")
    assert "(AL, g)" not in msg


def test_partition_rejects_an_overlap():
    raw = _toy_raw()
    raw["channels"]["Y"] = {"k": 1, "eta": 0.1, "domain": [{"units": ["TX"], "fine": ["g"]}]}
    _raises(lambda: spec.parse(raw), "two channels", "(TX, g) in X+Y")


def test_partition_rejects_a_fine_channel_outside_the_universe():
    raw = _toy_raw(domain=[{"units": "all", "fine": ["f", "g", "h"]}])
    _raises(lambda: spec.parse(raw), "outside [scenario] fine_channels", "h")


def test_the_51_scenario_partitions_its_cells_and_keeps_national_pure():
    s = spec.load(S51)
    assert list(s.channels) == ["national", "WH", "FI", "WIFI"]
    assert [c.k for c in s.channels.values()] == [13, 11, 24, 3]
    west = {"CO", "ID", "MT", "ND", "NE", "NM", "SD", "WY"}
    assert s.channels["WIFI"].units == west
    assert s.national.units == set(spec.CONUS_STATES) - west
    for u in s.units:
        for f in s.fine_channels:
            got = s.channel_of(u, f)
            if u in west:
                assert got == "WIFI"
            elif f in s.national.fine:
                assert got == "national"
            else:
                assert got == {"wh": "WH", "fi": "FI"}[f]
    assert s.channels["national"].modes["CA"] == "free"
    assert s.channels["national"].modes["AL"] == "whole"
    assert s.channels["WIFI"].delta == 1.0 and s.channels["FI"].delta == spec.DEFAULT_DELTA


def test_national_purity_and_fallback_are_checked():
    with open(S51, "rb") as fh:
        raw = tomllib.load(fh)
    bad = copy.deepcopy(raw)
    bad["national"]["units"] = "all"          # the west has no national cells
    _raises(lambda: spec.parse(bad), "purity/fallback", "(CO, national_chase) has national")
    bad = copy.deepcopy(raw)                   # wells FI in the west, but with WH, not FI
    bad["national"]["fallback"]["wells_fi"] = "wh"
    bad["channels"]["WIFI"]["domain"] = [
        {"units": "west", "fine": ["national_chase", "wells_wh", "wh", "wells_fi"]},
        {"units": "west", "fine": ["fi"]}]
    spec.parse(bad)                            # WH and FI are both WIFI there: still consistent
    bad = copy.deepcopy(raw)                   # a unit with national sends wells WH to WH
    bad["channels"]["national"]["domain"] = [
        {"units": "all - west", "fine": ["national_chase", "wells_fi"]}]
    bad["channels"]["WH"]["domain"] = [{"units": "all - west", "fine": ["wh", "wells_wh"]}]
    _raises(lambda: spec.parse(bad), "(AL, wells_wh) has national but is in WH")


def test_a_missing_fallback_does_not_skip_the_routing_check():
    with open(S51, "rb") as fh:
        raw = tomllib.load(fh)
    wrong = copy.deepcopy(raw)                 # CO sends national chase to WH, not with fi
    wrong["channels"]["WIFI"]["domain"] = [
        {"units": ["ID", "MT", "ND", "NE", "NM", "SD", "WY"], "fine": raw["scenario"]["fine_channels"]},
        {"units": ["CO"], "fine": ["wells_wh", "wells_fi", "fi"]}]
    wrong["channels"]["WH"]["domain"].append({"units": ["CO"], "fine": ["national_chase", "wh"]})
    _raises(lambda: spec.parse(wrong), "(CO, national_chase) is in WH, not with fi")
    omitted = copy.deepcopy(wrong)
    del omitted["national"]["fallback"]
    _raises(lambda: spec.parse(omitted), "need a fallback", "national_chase", "wells_fi")
    partial = copy.deepcopy(raw)
    del partial["national"]["fallback"]["national_chase"]
    _raises(lambda: spec.parse(partial), "need a fallback", "national_chase")
    circular = copy.deepcopy(raw)
    circular["national"]["fallback"]["wells_fi"] = "national_chase"
    _raises(lambda: spec.parse(circular), "not national", "national_chase")
    spec.parse(raw)                            # the scenario's complete fallback passes


def test_an_extract_with_a_fine_channel_outside_the_scenario_is_refused():
    s = spec.load(S51)
    ext = data.Extract(("fi", "priafs"), ["10001", "10001"], ["fi", "priafs"], [1.0, 1.0],
                       [{}, {}], [0.0, 0.0])
    _raises(lambda: spec.build(s, ext, _reference()), "priafs", "#76")


def test_overlapping_pieces_are_rejected():
    raw = _toy_raw()
    raw["geography"] = {"pieces": [{"name": "P1", "state": "TX", "counties": ["48201"]},
                                   {"name": "P2", "state": "TX", "counties": ["48201", "48141"]}]}
    _raises(lambda: spec.parse(raw), "P1 and P2 overlap in county 48201")
    raw["geography"] = {"pieces": [{"name": "P1", "state": "TX", "counties": ["06037"]}]}
    _raises(lambda: spec.parse(raw), "counties outside TX")


def test_two_metros_on_one_cbsa_are_rejected():
    raw = _toy_raw()
    raw["geography"] = {"metros": [{"name": "A", "cbsa": "35620"}, {"name": "B", "cbsa": "35620"}]}
    _raises(lambda: spec.parse(raw), "A", "B", "35620")
    raw["geography"] = {"metros": ["35620", {"name": "BIG", "cbsa": "35620"}]}
    _raises(lambda: spec.parse(raw), "M35620", "BIG", "35620")


def test_metros_must_be_2025_metropolitan_cbsas():
    """OD5 (#72 B4): a micropolitan CBSA, a CSA or metro-division code, or an unknown code is not
    a metro unit, and the spec is refused before any ZIP is carved."""
    raw = _toy_raw()
    raw["geography"] = {"metros": ["10100"]}                   # Aberdeen, SD Micro Area
    _raises(lambda: spec.parse(raw), "M10100", "10100", "Aberdeen, SD Micro Area",
            "not a metropolitan CBSA")
    raw["geography"] = {"metros": [{"name": "CSA", "cbsa": "408"}]}  # New York CSA
    _raises(lambda: spec.parse(raw), "CSA (408)", "csa code, not a CBSA")
    raw["geography"] = {"metros": ["1446014454"]}               # Boston, MA Metro Division
    _raises(lambda: spec.parse(raw), "1446014454", "metdiv code, not a CBSA")
    raw["geography"] = {"metros": ["99999"]}
    _raises(lambda: spec.parse(raw), "99999", "not a 2025 CBSA code")
    raw["geography"] = {"metros": ["35620", "10180"]}           # New York, Abilene: metros
    assert [m.name for m in spec.parse(raw).metros] == ["M35620", "M10180"]


def test_hooks_are_looked_up_by_name():
    s = spec.parse(_toy_raw(hook="shape_west"))
    assert spec.hook(spec.parse(_toy_raw()), "X") is None
    saved = sys.modules.get("td.hooks")
    try:
        mod = types.ModuleType("td.hooks")
        mod.shape_west = lambda *a: "ran"
        sys.modules["td.hooks"] = mod
        assert spec.hook(s, "X")() == "ran"
        del mod.shape_west
        _raises(lambda: spec.hook(s, "X"), "no hook 'shape_west'")
    finally:
        if saved is None:
            sys.modules.pop("td.hooks", None)
        else:
            sys.modules["td.hooks"] = saved


def test_unknown_keys_and_bad_values_are_rejected():
    _raises(lambda: spec.parse(_toy_raw(kk=1)), "unknown keys", "kk")
    _raises(lambda: spec.parse(_toy_raw(eta=0)), "eta")
    _raises(lambda: spec.parse(_toy_raw(delta=0.2, final_delta=0.1)), "final_delta")
    _raises(lambda: spec.parse(_toy_raw(free=["AL"], whole=["AL"])), "listed as")
    for cap in (0, -1, 2.5, True):
        _raises(lambda: spec.parse(_toy_raw(max_size=cap)), "max_size")


def test_a_boolean_is_neither_a_count_nor_a_number():
    """TOML's `true` is a Python int, so `k = true` read as K = 1 (#67 round 2 review)."""
    for k in (True, 0, 2.5, "2"):
        _raises(lambda: spec.parse(_toy_raw(k=k)), "channel X: k must be an integer >= 1")
    for caps in ({"AL": True}, {"AL": 2.5}, {"AL": 0}):
        _raises(lambda: spec.parse(_toy_raw(contact_caps=caps)), "contact_caps AL")
    for key in ("delta", "final_delta", "eta", "max_dist_km"):
        _raises(lambda: spec.parse(_toy_raw(**{key: True})), f"channel X: {key} must be a number")
    _raises(lambda: spec.parse(_toy_raw(dist_km={"AL": True})), "dist_km AL")
    raw = _toy_raw()
    raw["scenario"]["delta"] = True
    _raises(lambda: spec.parse(raw), "[scenario] delta")
    s = spec.parse(_toy_raw(k=3, contact_caps={"AL": 4}, dist_km={"AL": 1600}, max_dist_km=900))
    x = s.channels["X"]
    assert (x.k, x.contact_caps, x.dist_km, x.max_dist_km) == (3, {"AL": 4}, {"AL": 1600.0}, 900.0)


# ------------------------------------------------------------------------------ units and modes
def test_a_disconnected_whole_unit_stops_naming_its_components():
    s, units, cells = _toy({"AL": ["a1", "a2", "a3"], "AR": ["b1"]},
                           [("a1", "a2"), ("a2", "b1")],
                           {(z, "f"): 1.0 for z in ("a1", "a2", "a3", "b1")})
    assert units.components == {"AL": [("a1", "a2"), ("a3",)]}
    _raises(lambda: spec.assemble(s, units, cells), "AL: 2 components", "2 ZIPs a1, a2",
            "1 ZIPs a3")


def test_a_disconnected_splittable_unit_is_listed_not_stopped():
    s, units, cells = _toy({"AL": ["a1", "a2", "a3"], "AR": ["b1"]},
                           [("a1", "a2"), ("a2", "b1")],
                           {(z, "f"): 1.0 for z in ("a1", "a2", "a3", "b1")}, free=["AL"])
    inst = spec.assemble(s, units, cells)
    assert inst.report["disconnected"] == {"AL": [2, 1]}
    assert inst.channels["X"].mode["AL"] == "free"


def test_zero_opportunity_units_and_channels_are_dropped_and_reported():
    raw = _toy_raw(domain=[{"units": "all", "fine": ["f"]}])
    raw["channels"]["Y"] = {"k": 1, "eta": 0.1, "domain": [{"units": "all", "fine": ["g"]}]}
    s = spec.parse(raw)
    units = spec.Units.from_graph({"a": "AL", "b": "AR", "c": "AZ"}, [("a", "b"), ("b", "c")],
                                  {"a": (0, 0), "b": (1000, 0), "c": (2000, 0)})
    inst = spec.assemble(s, units, {("a", "f"): 2.0, ("b", "f"): 2.0, ("c", "f"): 0.0})
    x = inst.channels["X"]
    assert x.units == ("AL", "AR") and "AZ" in x.dropped_units
    assert x.tau == 2.0 and x.band == (2.0 * 0.9, 2.0 * 1.1)
    assert inst.dropped_channels == ("Y",) and "Y" not in inst.channels
    assert "AZ" in inst.report["dropped_units"]["X"]


def test_metros_are_classified_once_against_u_c():
    raw = _toy_raw(k=2, metro_mode="free")
    raw["geography"] = {"metros": ["35620", {"name": "BIG", "cbsa": "31080"}]}
    s = spec.parse(raw)
    assert [m.name for m in s.metros] == ["M35620", "BIG"]
    unit_of = spec.carve(s, {"z1": "NY", "z2": "NJ", "z3": "CA", "z4": "CA"},
                         {"z1": "36061", "z2": "34013", "z3": "06037", "z4": "06073"},
                         {"z1": "35620", "z2": "35620", "z3": "31080", "z4": "41740"})
    assert unit_of == {"z1": "M35620", "z2": "M35620", "z3": "BIG", "z4": "CA"}
    units = spec.Units.from_graph(unit_of, [("z1", "z2"), ("z2", "z3"), ("z3", "z4")],
                                  {z: (0, 0) for z in unit_of})
    cells = {("z1", "f"): 1.0, ("z2", "f"): 1.0, ("z3", "f"): 5.0, ("z4", "f"): 1.0}
    x = spec.assemble(s, units, cells).channels["X"]
    assert x.band[1] == 4.0 * 1.1
    assert x.mode == {"M35620": "whole", "BIG": "free", "CA": "whole"}


def test_the_national_report_moves_and_warns_per_unit():
    s = spec.load(S51)
    units = spec.Units.from_graph({"a": "AL", "c": "CO"}, [("a", "c")],
                                  {"a": (0, 0), "c": (1000, 0)})
    cells = {("a", "wh"): 1.0, ("a", "fi"): 1.0, ("c", "national_chase"): 2.0,
             ("c", "wells_wh"): 0.5, ("c", "fi"): 1.0}
    inst = spec.assemble(s, units, cells)
    assert inst.report["national_moved"] == {"CO": 2.5}
    assert inst.report["national_warnings"] == ["AL"]
    assert inst.channels["WIFI"].M == {"CO": 3.5}


# ------------------------------------------------------------------------------ on real geography
def test_the_51_scenario_lists_ca_as_disconnected_on_the_committed_graph():
    s = spec.load(S51)
    inst = spec.build(s, _all_conus(s), _reference())
    assert inst.report["disconnected"] == {"CA": [1801, 2]}
    assert inst.report["off_graph"] == [] and inst.dropped_channels == ()
    assert len(inst.units.zips) == 49
    assert set(inst.channels["WIFI"].units) == s.channels["WIFI"].units


def test_the_fixture_spec_with_a_disconnected_whole_piece_stops():
    s = spec.load(os.path.join(SCENARIOS, "fixture_disconnected_whole.toml"))
    fx = _fixture(tuple(s.fine_channels))
    if fx is None:
        return
    msg = _raises(lambda: spec.build(s, fx.extract, _reference(), fx.graph),
                  "not ZIP-connected", "TX_harris_el_paso: 2 components")
    assert msg.count("ZIPs") == 2


def test_a_sparse_extract_needs_its_own_graph():
    s = spec.load(S51)
    fx = _fixture(tuple(s.fine_channels))
    if fx is None:
        return
    _raises(lambda: spec.build(s, fx.extract, _reference()), "sparse", "geo.zip_graph")
    assert spec.build(s, fx.extract, _reference(), fx.graph).report["disconnected"] == {}


def test_the_51_scenario_builds_on_the_fixture():
    s = spec.load(S51)
    fx = _fixture(tuple(s.fine_channels))
    if fx is None:
        return
    inst = spec.build(s, fx.extract, _reference(), fx.graph)
    assert inst.report["disconnected"] == {} and inst.report["off_graph"] == []
    assert set(inst.report["national_moved"]) == s.channels["WIFI"].units
    for c in inst.channels.values():
        assert abs(sum(c.M.values()) - c.tau * c.k) < 1e-9 * c.tau * c.k
        assert set(c.m) == {z for u in c.units for z in inst.units.zips[u]}
