"""The window band (owner, #112 comment, 2026-10-14): a channel's `band_lo`, `band_hi` make its band
the dollar window [τ·band_lo, τ·band_hi].  `td.spec` validates the keys, `td.master` plans in the
window whatever δ is asked, `draw.py`, `plancheck.drawable` and `repair.py` hold the same band and
never retry wider, `overnight.py` and `sealed.py` write the keys, and a channel without them is
built exactly as before."""
from __future__ import annotations

import math
import os
import tempfile
import tomllib

from td import audit, master, spec
from td import spec as tdspec

from tests import test_contig_realize as tc
from tests import test_master as tm
from tests import test_overnight as to
from tests import test_realize as tr
from tests import test_sealed as ts_
from tests import test_spec as tsp

LO, HI, TAU = 850.0, 1150.0, 870.0
BAND = (LO / TAU, HI / TAU)


def _three(masses=(850.0, 850.0, 910.0), **channel):
    """Three isolated whole units, K = 3: τ = 870 for the default masses."""
    names = ("AL", "AR", "AZ")
    unit_zips = {u: [u.lower()] for u in names}
    mass = {u.lower(): x for u, x in zip(names, masses)}
    xy = {u.lower(): (float(i), 0.0) for i, u in enumerate(names)}
    return tm._toy(unit_zips, [], mass, xy, k=3, **channel)


def _window(**over):
    return {"band_lo": BAND[0], "band_hi": BAND[1], **over}


def _rows(model):
    return [(r.kind, r.key, sorted(r.coef.items()), r.lo, r.hi) for r in model.rows]


# ------------------------------------------------------------------------------ td.spec
def test_spec_validates_the_band_keys():
    ok = spec.parse(tsp._toy_raw(**_window()))
    cs = ok.channels["X"]
    assert cs.window == BAND and cs.band_lo == BAND[0] and cs.band_hi == BAND[1]
    assert cs.window_delta == max(1 - BAND[0], BAND[1] - 1)
    assert cs.rel_band(0.01) == BAND            # δ is ignored under a window
    plain = spec.parse(tsp._toy_raw(delta=0.05)).channels["X"]
    assert plain.window is None and plain.window_delta is None and plain.rel_band(0.05) == (0.95, 1.05)
    bad = [{"band_lo": 0.9},                                # one key alone
           {"band_hi": 1.1},
           {"band_lo": 1.0, "band_hi": 1.1},                # the window must hold τ strictly
           {"band_lo": 0.9, "band_hi": 1.0},
           {"band_lo": 0.0, "band_hi": 1.1},
           {"band_lo": 1.2, "band_hi": 1.3},
           {"band_lo": 0.7, "band_hi": 0.8},
           {"band_lo": -0.1, "band_hi": 1.1},
           {"band_lo": 0.9, "band_hi": math.inf},
           {"band_lo": 0.9, "band_hi": math.nan},
           {"band_lo": True, "band_hi": 1.1},
           {"band_lo": "0.9", "band_hi": 1.1}]
    for keys in bad:
        try:
            spec.parse(tsp._toy_raw(**keys))
        except spec.SpecError as e:
            assert "band_lo" in str(e) or "band_hi" in str(e), (keys, str(e))
        else:
            raise AssertionError(f"accepted {keys}")


def test_the_instance_band_and_final_band_are_the_window_not_delta():
    """A symmetric final δ of 0.5 would accept 1.3 τ; the window's final band does not."""
    inst = _three(delta=0.02, final_delta=0.5, **_window())
    ch = inst.channels["X"]
    assert math.isclose(ch.tau, TAU)
    assert ch.band == ch.final_band
    assert math.isclose(ch.final_band[0], LO) and math.isclose(ch.final_band[1], HI)
    plain = _three(delta=0.02, final_delta=0.5).channels["X"]
    assert math.isclose(plain.final_band[1], TAU * 1.5) and math.isclose(plain.band[1], TAU * 1.02)


def test_a_district_outside_the_window_is_never_accepted():
    """The final band the audit and `repair.map_figures` judge is the window: 910 against a
    window of [850, 900] is outside it though a symmetric final δ of 0.5 would hold it."""
    repair = tc._repair_module()
    hi = 900.0 / TAU
    state = {"al": "AL", "ar": "AR", "az": "AZ"}
    owner = {"al": "AL#1", "ar": "AR#1", "az": "AZ#1"}
    win = _three(delta=0.02, final_delta=0.5, band_lo=LO / TAU, band_hi=hi)
    assert repair.map_figures(win, "X", owner, state)["outside_band"] == ["AZ#1"]
    wide = _three(delta=0.02, final_delta=0.5)
    assert repair.map_figures(wide, "X", owner, state)["outside_band"] == []
    ch = win.channels["X"]
    assert audit.Channel(ch.k, *ch.final_band).hi < 910.0       # what `td.output` and `td.realize` audit with


# ------------------------------------------------------------------------------ td.master
def test_absent_keys_reproduce_todays_rows_and_equal_keys_reproduce_the_delta_rows():
    plain = _three(delta=0.4)
    base = _rows(master.build(plain, "X"))
    assert base == _rows(master.build(plain, "X", 0.4))
    sym = _three(delta=0.4, band_lo=0.6, band_hi=1.4)
    assert _rows(master.build(sym, "X")) == base
    assert _rows(master.build(sym, "X", 0.01)) == base      # δ is ignored under a window
    model = master.build(plain, "X")
    s = frozenset(["AL"])
    mu = tm.supports.margin(plain, "X", s) / plain.channels["X"].tau
    assert math.isclose(-model.rows_of("band_lo")[(s,)].coef[model.n_col[s]], 0.6 + mu)
    assert math.isclose(-model.rows_of("band_hi")[(s,)].coef[model.n_col[s]], 1.4 - mu)


def test_a_window_plans_where_the_symmetric_delta_of_fit_delta_is_infeasible():
    """Districts of 850, 850 and 910 against τ = 870: the window [850, 1150] holds all three, the
    symmetric δ the fit gives (0.0229 = 20 / 870) holds only [850, 890]."""
    d = to.overnight.fit_delta(TAU, 3, LO, HI)
    assert d == 0.0229
    sym = _three(delta=d, final_delta=d)
    p, rep = master.plan(sym, "X")
    assert p is None and rep["status"] == "infeasible"
    win = _three(delta=d, final_delta=d, **_window())
    p, rep = master.plan(win, "X")
    assert p is not None and rep["status"] == "optimal"
    ch = win.channels["X"]
    assert math.isclose(p.delta, ch.spec.window_delta)
    totals = sorted(cp.total for cp in p.copies)
    assert all(LO - 1e-6 <= x <= HI + 1e-6 for x in totals), totals
    assert math.isclose(totals[-1], 910.0)
    other, _ = master.plan(win, "X", 0.001)         # a δ asked for is ignored, never narrower or wider
    assert other is not None and math.isclose(other.delta, p.delta)


def test_the_smallest_delta_searches_report_feasibility_in_the_window():
    win = _three(delta=0.0229, final_delta=0.0229, **_window())
    wd = win.channels["X"].spec.window_delta
    for found in (master.smallest_delta(win, "X"), master.exact_delta(win, "X"),
                  master.bisect_delta(win, "X")):
        assert (found.method, found.status, found.lower) == ("window", "converged", None), found
        assert math.isclose(found.delta, wd)
        assert [v for _, v, _ in found.steps] == ["feasible"] and math.isclose(found.steps[0][0], wd)
    # a plain channel is untouched: the symmetric search finds the δ the window does not need
    plain = master.exact_delta(_three(delta=0.0229), "X")
    assert plain.method == "exact" and math.isclose(plain.delta, 40.0 / TAU)
    # no window holds a 910 against [850, 900]: infeasible, and nothing is widened
    tight = _three(delta=0.0229, final_delta=0.5, band_lo=LO / TAU, band_hi=900.0 / TAU)
    for found in (master.smallest_delta(tight, "X"), master.bisect_delta(tight, "X")):
        assert (found.method, found.status, found.delta) == ("window", "infeasible", None), found
        assert len(found.steps) == 1
    p, rep = master.plan(tight, "X")
    assert p is None and rep["status"] == "infeasible"
    with tempfile.TemporaryDirectory() as tmp:      # the report writer takes a window Delta as any other
        path = master.write_report(os.path.join(tmp, "solver.json"), {"X": master.plan(win, "X")[1]},
                                   {"X": master.smallest_delta(win, "X")})
        assert os.path.getsize(path) > 0


# ------------------------------------------------------------------------------ draw, drawable
def _thin(**channel):
    """tests.test_realize._ct_ny_nj with channel keys: the thin-share plan is infeasible at
    δ = 0.3 and drawable at 0.4."""
    ny, ne, nm, npt = tr._grid("ny", 20, 2)
    ct, ce, cm, cp = tr._grid("ct", 5, 1, x0=20.0, mass=2.0)
    nj, je, jm, jp = tr._grid("nj", 6, 1, x0=-6.0, mass=2.0)
    edges = ne + ce + je + [(ny[19, 0], ct[0, 0]), (ny[19, 1], ct[0, 0]),
                            (ny[0, 0], nj[5, 0]), (ny[0, 1], nj[5, 0])]
    return tr._toy({"NY": list(ny.values()), "CT": list(ct.values()), "NJ": list(nj.values())},
                   edges, {**nm, **cm, **jm}, {**npt, **cp, **jp}, {"NY": "free"}, k=2, **channel)


def test_draw_holds_the_window_and_never_retries_wider():
    draw = tc._draw()
    plan_of = lambda inst: tr._plan(inst, [({"CT", "NY", "NJ"}, {"CT": 1.0, "NJ": 1.0, "NY": 0.05}),
                                           ({"NY"}, {"NY": 0.95})])
    inst, xy = _thin(delta=0.3, band_lo=0.7, band_hi=1.3)
    res = draw.draw(inst, plan_of(inst), xy, wider=(0.4, 0.5), delta=0.35, log=lambda *_: None)
    tried = res.groups[0].tried
    assert res.status == "infeasible" and not res.connected
    assert {t["delta"] for t in tried} == {inst.channels["X"].spec.window_delta}, tried
    assert math.isclose(res.delta, 0.3)
    # the same plan in a window of ±0.4 draws, and its masses sit inside it
    inst, xy = _thin(delta=0.3, band_lo=0.6, band_hi=1.4)
    res = draw.draw(inst, plan_of(inst), xy, wider=(0.5,), log=lambda *_: None)
    assert res.connected, [g.tried for g in res.groups]
    d = draw.drawing(inst, plan_of(inst), res)
    lo, hi = inst.channels["X"].final_band
    assert all(lo - 1e-9 <= x <= hi + 1e-9 for x in d.mass.values()), d.mass
    # without keys the wider band is still tried
    inst, xy = _thin(delta=0.3)
    res = draw.draw(inst, plan_of(inst), xy, wider=(0.4,), log=lambda *_: None)
    assert res.connected and any(t["delta"] == 0.4 for t in res.groups[0].tried)


def _corridor(**channel):
    """tests.test_contig_realize._corridor_toy(2) with channel keys: {PA, NY} weighs 1.03 against
    τ = 1.015."""
    edges = [("p0", "n1"), ("n1", "n2"), ("n2", "n3"), ("n3", "q0")]
    km = {("n1", "p0"): 20.0, ("n1", "n2"): 1.0, ("n2", "n3"): 1.0, ("n3", "q0"): 20.0}
    xy = {"p0": (0.0, 0.0), "n1": (1.0, 0.0), "n2": (2.0, 0.0), "n3": (3.0, 0.0), "q0": (4.0, 0.0)}
    mass = {"p0": 1.0, "q0": 1.0, "n1": 0.01, "n2": 0.01, "n3": 0.01}
    inst, _ = tr._toy({"PA": ["p0"], "NY": ["n1", "n2", "n3"], "NJ": ["q0"]}, edges, mass, xy,
                      {"NY": "free"}, k=2, eta=0.05, **channel)
    polygon = {"vertices": sorted(xy), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"p0": 1e8, "q0": 1e8, "n1": 1e6, "n2": 1e6, "n3": 1e6}}
    inst.polygon = polygon
    return inst, audit.NeckGraph(polygon)


def test_drawable_tests_in_the_window_whatever_delta_it_is_asked():
    pc = tc._plancheck_module()
    s = frozenset({"PA"})           # one whole ZIP of 1.0 against τ = 1.015: 0.985 τ
    inst, ng = _corridor(delta=0.1)
    assert pc.drawable(inst, "X", s, 0.1, ng, 60.0, log=lambda *_: None)["status"] == "drawable"
    inst, ng = _corridor(delta=0.1, band_lo=0.99, band_hi=1.02)     # 0.985 τ is below the window
    for asked in (0.1, 0.5):        # a wider δ would hold it; the window does not
        v = pc.drawable(inst, "X", s, asked, ng, 60.0, log=lambda *_: None)
        assert v["status"] == "infeasible" and "outside the band" in v["why"], v
        assert math.isclose(v["delta"], inst.channels["X"].spec.window_delta)
    inst, ng = _corridor(delta=0.001, band_lo=0.98, band_hi=1.02)   # a window that holds it, a δ that would not
    assert pc.drawable(inst, "X", s, 0.001, ng, 60.0, log=lambda *_: None)["status"] == "drawable"
    # B's loop and cache use the one δ, so a verdict in the window serves every asked δ
    wd = inst.channels["X"].spec.window_delta
    p, rep, rec = pc.plan_checked(inst, "X", 0.5, ng=ng, check_time=60.0, log=lambda *_: None)
    assert rec["delta"] == wd and all(t["delta"] == wd for t in rec["tested"])
    assert p is not None and math.isclose(p.delta, wd)
    found = pc.checked_delta(inst, "X", 0.0, None, pc.Checks(), ng, 60.0, 60.0, log=lambda *_: None)
    assert found["status"] == "converged" and math.isclose(found["delta"], wd) and len(found["steps"]) == 1


def test_repair_caps_a_diagnostic_band_at_the_window():
    """`--diag-final-delta` replaces a channel's final band; a window channel keeps the window."""
    repair = tc._repair_module()
    win = _three(delta=0.02, final_delta=0.02, **_window()).channels["X"]
    lo, hi = repair.diag_band(win, 0.5)
    assert math.isclose(lo, LO) and math.isclose(hi, HI)           # not 435 .. 1305
    lo, hi = repair.diag_band(win, 0.05)                           # a narrower side stays narrower
    assert math.isclose(lo, LO) and math.isclose(hi, TAU * 1.05)
    plain = _three(delta=0.02).channels["X"]
    assert repair.diag_band(plain, 0.5) == (TAU * 0.5, TAU * 1.5)


# ------------------------------------------------------------------------------ the drivers
def _window_plan(ov, window_band, ks=None):
    return ov.plan_point(ks or {"national": 2, "WIFI": 2}, to._toy(), to.CELLS, "rule", window_band=window_band)


def test_overnight_writes_the_band_only_behind_the_flag():
    ov = to.overnight
    off = _window_plan(ov, False)
    assert all("band_lo" not in v for v in off["channels"].values())
    on = _window_plan(ov, True)
    for c, v in on["channels"].items():
        assert math.isclose(v["band_lo"], v["lo_m"] / v["tau_m"]) and math.isclose(v["band_hi"], v["hi_m"] / v["tau_m"])
        assert v["final_delta"] == max(1 - v["band_lo"], v["band_hi"] - 1)
        assert off["channels"][c]["final_delta"] <= v["final_delta"] and off["channels"][c]["k"] == v["k"]
    assert on["infeasible"] == off["infeasible"] == {}
    # a whole-state channel's U is the cap, not the window's top
    base = ov.plan_point({"national": 2, "WIFI": 1}, to._toy(), {("CA", "wh"): 1000.0, ("CA", "national_chase"): 2000.0,
                                                                  ("TX", "national_chase"): 200.0}, "base", window_band=True)
    wifi = base["channels"]["WIFI"]
    assert wifi["whole_state_cap"] and math.isclose(wifi["band_hi"], wifi["hi_m"] / wifi["tau_m"])
    text = ov.point_spec_text(to.TOY, "pt-1", on)
    raw = tomllib.loads(text)
    for c, v in on["channels"].items():
        assert raw["channels"][c]["band_lo"] == v["band_lo"] and raw["channels"][c]["band_hi"] == v["band_hi"]
        assert raw["channels"][c]["final_delta"] == float(f"{v['final_delta']:g}")
    sp = tdspec.parse(raw)
    assert all(cs.window is not None for cs in sp.channels.values())
    off_text = ov.point_spec_text(to.TOY, "pt-1", off)
    assert "band_lo" not in off_text and "band_hi" not in off_text
    assert all(cs.window is None for cs in tdspec.parse(tomllib.loads(off_text)).channels.values())


def test_overnight_makes_no_wider_draw_retry_under_a_window_band():
    """A drawing ending "infeasible" earns one retry from a wider start; a window band cannot
    widen, so with `--window-band` the retry is not run (and without it, it is)."""
    import json
    ov = to.overnight

    class Fake(ov.Runner):
        def __init__(self, window_band):
            self.window_band, self.plans, self.extract, self.stages = window_band, "p", "e", []

        def stage(self, pid, name, cmd, log, cap, env=None):
            self.stages.append(name)
            return {"stop": None, "rc": 0}
    for window_band, expect in ((True, []), (False, ["draw_retry"])):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "draw")
            os.makedirs(out)
            with open(os.path.join(out, "manifest.json"), "w") as fh:
                json.dump({"status": "done"}, fh)
            open(os.path.join(out, "ledger.csv"), "w").close()
            with open(os.path.join(out, "contig.json"), "w") as fh:
                json.dump({"channels": {"WH": {"status": "infeasible", "plan_delta": 0.07}}}, fh)
            r = Fake(window_band)
            assert r._draw("pt", tmp, os.path.join(tmp, "spec.toml"), 2) == out
            assert r.stages == expect, (window_band, r.stages)


def test_the_overnight_flag_and_its_default():
    ov = to.overnight
    assert ov.parser().parse_args(["run", "--host", "m5"]).window_band is False
    assert ov.parser().parse_args(["run", "--host", "m5", "--window-band"]).window_band is True
    r = ov.Runner.__init__.__defaults__
    assert r == (False,)


def test_sealed_writes_the_band_for_every_present_channel_by_default():
    sealed = ts_.sealed
    with tempfile.TemporaryDirectory() as tmp:
        sp = tdspec.load(ts_._toy_file(tmp))
    off = sealed.region_plan(sp, ("CA", "TX"), {"national": 2, "WIFI": 2}, ts_.CELLS, "base")
    assert all("band_lo" not in v for v in off["channels"].values())          # the function's default is today's
    on = sealed.region_plan(sp, ("CA", "TX"), {"national": 2, "WIFI": 2}, ts_.CELLS, "base", True)
    nat = on["channels"]["national"]
    assert math.isclose(nat["band_lo"], 1000.0 / 1100.0) and math.isclose(nat["band_hi"], nat["hi_m"] / 1100.0)
    assert math.isclose(on["channels"]["WIFI"]["band_lo"], 850.0 / 950.0)
    text = sealed.run_spec_text(ts_.TOY, "toy-pt", "south", ("CA", "TX"), on, forbid=set(), max_size=None)
    raw = tomllib.loads(text)
    n, w = raw["channels"]["national"], raw["channels"]["WIFI"]
    assert (n["band_lo"], n["band_hi"]) == (nat["band_lo"], nat["band_hi"])
    assert (w["band_lo"], w["band_hi"]) == (on["channels"]["WIFI"]["band_lo"], on["channels"]["WIFI"]["band_hi"])
    assert n["delta"] == 0.02 and n["final_delta"] == float(f"{nat['final_delta']:g}")        # kept for reporting
    assert "band_lo" not in sealed.run_spec_text(ts_.TOY, "toy-pt", "south", ("CA", "TX"), off, forbid=set())
    a = sealed.parser().parse_args(["run", "--partition", "p.json", "--root", "r", "--host", "m5"])
    assert a.window_band is True and a.drawable_alone is True
    assert sealed.parser().parse_args(["run", "--partition", "p.json", "--root", "r", "--host", "m5",
                                       "--no-window-band"]).window_band is False


REPLAN_SRC = """[scenario]
name = "toy"
fine_channels = ["f", "g"]

[channels.X]
k = 3
delta = 0.0229
final_delta = 0.5
eta = 0.1
band_lo = {lo!r}
band_hi = {hi!r}
domain = [{{ units = "all", fine = ["f", "g"] }}]
"""


def _replan_main(hi, *extra):
    """(exit code or SystemExit message, stdout, report) of replan.py on the 850 / 850 / 910 toy
    whose window is [850, hi] and whose symmetric final δ is 0.5."""
    import contextlib
    import io
    import json
    replan = tc._replan_module()
    names = ("AL", "AR", "AZ")
    unit_zips = {u: [u.lower()] for u in names}
    mass = dict(zip(("al", "ar", "az"), (850.0, 850.0, 910.0)))
    xy = {z: (float(i), 0.0) for i, z in enumerate(mass)}

    def build(path, extract):
        with open(path, "rb") as fh:
            sp = spec.parse(tomllib.load(fh))
        unit_of = {z: u for u, zs in unit_zips.items() for z in zs}
        units = spec.Units.from_graph(unit_of, [], {z: (1000.0 * x, 1000.0 * y) for z, (x, y) in xy.items()})
        return sp, spec.assemble(sp, units, {(z, "f"): m for z, m in mass.items()})
    replan.build = build
    with tempfile.TemporaryDirectory() as tmp:
        src, out, rep = (os.path.join(tmp, x) for x in ("src.toml", "copy.toml", "replan.json"))
        with open(src, "w") as fh:
            fh.write(REPLAN_SRC.format(lo=LO / TAU, hi=hi / TAU))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                rc = replan.main([src, "--out-spec", out, "--plans", tmp, "--keep", "--report", rep,
                                  "--extract", "/nowhere", *extra])
            except SystemExit as e:
                rc = str(e)
        report = json.load(open(rep)) if os.path.exists(rep) else None
    return rc, buf.getvalue(), report


def test_replan_stops_on_a_window_channel_with_no_plan_and_never_widens_it():
    """The window [850, 900] holds no plan for a 910; a symmetric final δ of 0.5 would, but the
    driver stops: no δ is written into the copy and the report says so."""
    rc, out, report = _replan_main(900.0)
    assert rc == 1 and "no plan in the window band" in out, (rc, out)
    ch = report["channels"]["X"]
    assert ch["smallest_delta"]["status"] == "infeasible" and ch["smallest_delta"]["delta"] is None
    assert "delta" not in ch                                    # nothing was moved
    rc, out, report = _replan_main(1150.0, "--widen", "X")
    assert isinstance(rc, str) and "never widened" in rc, rc


def test_replan_writes_the_band_keys_through_banned_text():
    replan = tc._replan_module()
    text = replan.banned_text("[channels.X]\nk = 2\n", [], keys={"X": {"band_lo": repr(0.8), "band_hi": repr(1.2)}})
    assert text.split() == "[channels.X] k = 2 band_hi = 1.2 band_lo = 0.8".split()
