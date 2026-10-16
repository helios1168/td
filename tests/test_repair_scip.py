"""repair.py --engine scip and window growth (td#142 phase 2, P1 and P2).

The engine: `scip_engine.ScipHighs` stands in for HiGHS inside `draw._solve_group`, so a window is
solved on draw.py's own model by PySCIPOpt with arm c's constraint handler.  On three small groups
(the bnc grids), the U toy's windows around the power diagram's detached piece at three sizes, and
a window that is infeasible, both engines must return the same status and the same optimum, and the
drawing must be connected.

The growth: a window proved infeasible is followed by larger ones (`grow_windows`, the adjacent
districts' free ZCTAs first, then the ball widened); an unknown window never grows.  The windows are
a stub's, so that a verdict is the test's to set.
"""
from __future__ import annotations

import contextlib
import os
import sys
import types

import numpy as np

from tests import test_contig_realize as tcr
from tests import test_realize as tr

HERE = os.path.dirname(os.path.abspath(__file__))
BNC = os.path.join(HERE, "..", "tools", "exp", "bnc")
if BNC not in sys.path:
    sys.path.append(BNC)

import arms  # noqa: E402
import capture  # noqa: E402
import synth  # noqa: E402

TOL = 1e-6
quiet = lambda *_: None     # noqa: E731


def _repair():
    return tcr._repair_module()


# ------------------------------------------------------------------------------ the engine
def _group(draw, repair, snap, engine, seconds=120.0):
    """`draw._solve_group` on a bnc snapshot (the complete model, flow rows off), by `engine`."""
    args, kw = capture.rebuild_args(snap)
    kw.update(dag=False, flow=False, layers=True, log=quiet)
    ctx = repair.scip_engine().installed(draw) if engine == "scip" else contextlib.nullcontext()
    with capture.centres_patch(draw, snap), ctx:
        return draw._solve_group(*args[:19], seconds, **kw)


def test_both_engines_return_the_same_optimum_on_three_groups():
    repair, draw = _repair(), tcr._draw()
    for name, kw in synth.cases():
        inst = synth.grid(name, **kw)
        snap = inst.doc["draw"]
        got = {e: _group(draw, repair, snap, e) for e in ("highs", "scip")}
        h, s = got["highs"], got["scip"]
        assert h.status == s.status == "optimal", (name, h.status, s.status, s.note)
        assert abs(h.objective - s.objective) <= TOL * max(1.0, abs(h.objective)), (name, h.objective, s.objective)
        assert synth.connected(inst, s.owner) and synth.connected(inst, h.owner), name
        assert set(s.owner) == set(inst.zs), name


def test_both_engines_prove_the_same_group_infeasible():
    """A band too narrow for the masses: no drawing at all, in either engine's terms."""
    repair, draw = _repair(), tcr._draw()
    name, kw = synth.cases()[0]
    inst = synth.grid(name, **{**kw, "delta": 0.001})
    snap = inst.doc["draw"]
    got = {e: _group(draw, repair, snap, e) for e in ("highs", "scip")}
    assert got["highs"].status == got["scip"].status == "infeasible", {e: g.status for e, g in got.items()}


def test_scip_takes_a_start_solution():
    """A full-column start (what draw.py gives HiGHS through `setSolution`) is accepted by SCIP."""
    name, kw = synth.cases()[0]
    inst = synth.grid(name, **kw)
    res, full = arms.scip_solve(inst, 120.0, quiet)
    assert res["status"] == "optimal" and full is not None
    again, _ = arms.scip_solve(inst, 120.0, quiet, start=full)
    assert "start accepted" in again["note"], again["note"]
    assert again["status"] == "optimal" and abs(again["objective"] - res["objective"]) <= TOL * max(1.0, abs(res["objective"]))


def _u_windows():
    repair = _repair()
    inst, xy, plan = tcr._u_toy()
    from td import realize
    power = realize.realize(inst, plan, xy)
    adj, m = inst.units.zip_adj, inst.channels["X"].m
    pieces = repair.detached(power.owner, adj, m)
    assert pieces
    free = repair.draw.split_fixed(inst, plan)[1]
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    return repair, inst, plan, power.owner, p, [repair.ball(pieces, free, adj, h, 50) for h in (1, 2, 3)]


def test_repair_windows_agree_between_engines():
    """`solve_window` on the U toy's detached piece at h = 1, 2, 3: the same status and optimum, a
    connected drawing, the same objective."""
    repair, inst, plan, owner, p, windows = _u_windows()
    assert len({len(W) for W in windows}) == 3, [len(W) for W in windows]
    for W in windows:
        lines = {"highs": [], "scip": []}
        got = {e: repair.solve_window(inst, plan, owner, W, p, 60.0, True, log=lines[e].append, engine=e)
               for e in ("highs", "scip")}
        assert any("[scip]" in x for x in lines["scip"]) and not any("[scip]" in x for x in lines["highs"])
        h, s = got["highs"], got["scip"]
        assert h.status == s.status, (len(W), h.status, s.status, s.note)
        if h.status in ("optimal", "connected"):
            assert abs(h.objective - s.objective) <= TOL * max(1.0, abs(h.objective)), (len(W), h.objective, s.objective)
            assert set(s.owner) == set(h.owner) == set(W), len(W)


def test_repair_channel_with_the_scip_engine_reconnects_the_piece():
    """`repair_channel` as `--engine scip` runs it: the environment names the engine (the worker
    processes inherit it), every attempt records it, and the piece is reconnected as with HiGHS."""
    repair = _repair()
    inst, xy, plan = tcr._u_toy()
    from td import realize
    power = realize.realize(inst, plan, xy)
    adj, m = inst.units.zip_adj, inst.channels["X"].m
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    state = dict(inst.units.unit_of)
    got = {}
    old = os.environ.get(repair.ENGINE_ENV)
    try:
        for e in ("highs", "scip"):
            os.environ[repair.ENGINE_ENV] = e
            got[e] = repair.repair_channel(inst, plan, power.owner, p, state, h0=1, max_zctas=100,
                                           time_limit=60.0, log=quiet)
    finally:
        if old is None:
            os.environ.pop(repair.ENGINE_ENV, None)
        else:
            os.environ[repair.ENGINE_ENV] = old
    for e, (owner, attempts) in got.items():
        assert repair.detached(owner, adj, m) == [], e
        assert attempts and {a["engine"] for a in attempts} == {e}, e
    assert [a["status"] for a in got["scip"][1]] == [a["status"] for a in got["highs"][1]]


def test_neck_aware_windows_agree_between_engines():
    """The bridge toy's neck-aware window: the neck cut adds rows and columns draw.py's maps do not
    list, a necked incumbent is cut and the solve repeated; SCIP ends at HiGHS's drawing."""
    from td import audit
    repair = _repair()
    inst, xy, plan, owner, polygon, ct, nj = tcr._bridge_toy()
    ng = audit.NeckGraph(polygon)
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    border = repair.draw.border_km(polygon)
    got = {e: repair.solve_window(inst, plan, owner, {"f", "g"}, p, 30.0, True, log=quiet,
                                  keep_support=True, repairing={ct}, border=border, ng=ng, engine=e)
           for e in ("highs", "scip")}
    h, s = got["highs"], got["scip"]
    assert h.status == s.status == "optimal", (h.status, s.status, s.note)
    assert s.owner == h.owner == {"f": nj, "g": ct}
    assert s.neck_cuts == h.neck_cuts >= 1
    assert abs(s.objective - h.objective) <= TOL * max(1.0, abs(h.objective))


def test_a_window_infeasible_by_the_band_is_infeasible_in_both_engines():
    repair = _repair()
    inst, plan, owner, p = tcr._over_band_toy()
    got = {e: repair.solve_window(inst, plan, owner, {"w"}, p, 30.0, True, log=quiet, engine=e)
           for e in ("highs", "scip")}
    assert got["highs"].status == got["scip"].status == "infeasible", {e: g.status for e, g in got.items()}


def test_the_engine_is_chosen_by_name_and_environment():
    repair = _repair()
    old = os.environ.pop(repair.ENGINE_ENV, None)
    try:
        assert repair.engine_mode() == "highs"
        os.environ[repair.ENGINE_ENV] = "scip"
        assert repair.engine_mode() == "scip"
        os.environ[repair.ENGINE_ENV] = "gurobi"
        try:
            repair.engine_mode()
        except SystemExit:
            pass
        else:
            raise AssertionError("an unknown engine was accepted")
    finally:
        os.environ.pop(repair.ENGINE_ENV, None)
        if old is not None:
            os.environ[repair.ENGINE_ENV] = old


# ------------------------------------------------------------------------------ growth
N = 60
NAMES = [f"z{i:02d}" for i in range(N)]
OWNER = {z: "A" for z in NAMES[:10] + NAMES[11:20]} | {"z10": "B"} \
    | {z: "C" for z in NAMES[20:30]} | {z: "D" for z in NAMES[30:45]} | {z: "E" for z in NAMES[45:]}


def _line():
    """z00..z59 on a path: A holds z00-z09 and z11-z19 with B's z10 between, then C, D, E; every
    ZCTA free.  The detached piece is A's z00-z09."""
    adj = {z: {NAMES[i + d] for d in (-1, 1) if 0 <= i + d < N} for i, z in enumerate(NAMES)}
    m = dict.fromkeys(NAMES, 1.0)
    ch = types.SimpleNamespace(m=m, tau=10.0, final_band=(0.0, 100.0))
    inst = types.SimpleNamespace(units=types.SimpleNamespace(zip_adj=adj), channels={"X": ch})
    plan = types.SimpleNamespace(channel="X")
    piece = [("A", frozenset(NAMES[:10]))]
    return inst, plan, dict(OWNER), set(NAMES), dict(zip(NAMES, NAMES)), piece


def _stub(repair, verdict):
    """`solve_window` replaced by a function giving `verdict(W)` ("infeasible", "unknown" or
    "connected") as the window's status; the windows it was asked for are in `.asked`."""
    asked = []

    def solve_window(inst, plan, owner, W, p, time_limit, cap, log=print, *a, **k):
        asked.append((len(W), cap))
        st = verdict(W)
        g = repair.draw.Group(sorted({owner[z] for z in W}), [], len(W), 1, 1, st)
        if st == "connected":
            g.owner = {z: owner[z] for z in W}
        return g
    solve_window.asked = asked
    return solve_window


@contextlib.contextmanager
def _patched(repair, fn):
    old = repair.solve_window
    repair.solve_window = fn
    try:
        yield
    finally:
        repair.solve_window = old


def _run(repair, verdict, grow, pool=None, max_zctas=14):
    inst, plan, owner, free, state, piece = _line()
    attempts, lines = [], []
    fn = _stub(repair, verdict)
    with _patched(repair, fn):
        repair._repair_cluster(inst, plan, owner, piece, free, {}, state, 3, max_zctas, 60.0,
                               attempts, lines.append, pool=pool, grow=grow)
    return attempts, lines


def _shapes(attempts):
    return [(a["shape"], a["status"], a["cap"]) for a in attempts]


def test_the_adjacent_districts_are_added_first():
    repair = _repair()
    attempts, lines = _run(repair, lambda W: "connected" if "z25" in W else "infeasible", (3, 60))
    grow = [a for a in attempts if a["shape"].startswith("grow")]
    assert grow and grow[0]["shape"] == "grow-adjacent" and grow[0]["status"] == "connected", _shapes(attempts)
    std = [a for a in attempts if not a["shape"].startswith("grow")]
    assert std and all(a["status"] == "infeasible" for a in std)
    assert not std[-1]["cap"], "the last standard window runs without the cap before growth"
    # C's free ZCTAs joined the window: A and B's districts plus the ring of C
    assert grow[0]["window_zctas"] > std[-1]["window_zctas"]
    assert "C" in grow[0]["districts"]
    # each growth step is logged with its ZCTAs, districts, verdict and seconds
    line = next(x for x in lines if "grow-adjacent step 1" in x)
    assert f"|W| = {grow[0]['window_zctas']} ZCTAs" in line and "districts" in line \
        and "connected" in line and line.rstrip().endswith("s"), line
    assert any("proved infeasible" in x and "growing by" in x for x in lines)


def test_a_proved_infeasible_window_grows_until_a_later_step_solves():
    """z32 is D's, which no district next to A and B touches: the adjacent step is infeasible, a
    wider ball reaches it.  Each step is a union that strictly grows the window, and each uses one
    of grow_max, so the adjacent step (21) and three wider ones (26, 30, 34) take four before z32 is in."""
    repair = _repair()
    attempts, _ = _run(repair, lambda W: "connected" if "z32" in W else "infeasible", (5, 60))
    grow = [a for a in attempts if a["shape"].startswith("grow")]
    assert [a["shape"] for a in grow][0] == "grow-adjacent" and grow[0]["status"] == "infeasible", _shapes(attempts)
    assert grow[-1]["shape"] == "grow-wider" and grow[-1]["status"] == "connected", _shapes(attempts)
    sizes = [a["window_zctas"] for a in grow]
    assert sizes == sorted(sizes) and len(set(sizes)) > 1, sizes
    assert max(sizes) <= 60
    assert len({a["grow"] for a in grow}) >= 2 and max(a["grow"] for a in grow) == 4
    wider = sorted({(a["grow"], a["window_zctas"]) for a in grow if a["shape"] == "grow-wider"})
    assert wider == [(2, 26), (3, 30), (4, 34)], wider
    # three steps stop short of z32 (at 30) and the log names the step cap
    short, lines = _run(repair, lambda W: "connected" if "z32" in W else "infeasible", (3, 60))
    grow = [a for a in short if a["shape"].startswith("grow")]
    assert max(a["window_zctas"] for a in grow) == 30 and all(a["status"] == "infeasible" for a in grow), _shapes(short)
    assert any("growing by 3 step(s) to 21, 26, 30 ZCTAs (at most 3 steps, 60 ZCTAs)" in x for x in lines), lines


def test_growth_stops_at_the_step_and_size_caps():
    repair = _repair()
    never = lambda W: "infeasible"      # noqa: E731
    attempts, _ = _run(repair, never, (1, 60))
    grow = {a["grow"] for a in attempts if a["shape"].startswith("grow")}
    assert grow == {1}, grow
    attempts, _ = _run(repair, never, (3, 60))
    grow = [a for a in attempts if a["shape"].startswith("grow")]
    assert 1 < len({a["grow"] for a in grow}) <= 3 and all(a["status"] == "infeasible" for a in grow)
    small, lines = _run(repair, never, (3, 11))
    assert not [a for a in small if a["shape"].startswith("grow")], "a cap at the window's own size grows nothing"
    assert any("no larger window within 11 ZCTAs" in x for x in lines)
    # a cap that holds only part of the ring takes its nearest ZCTAs (C's z20-z22), no more
    part, _ = _run(repair, never, (1, 14))
    grow = [a for a in part if a["shape"].startswith("grow")]
    assert {a["window_zctas"] for a in grow} == {14}, [a["window_zctas"] for a in grow]
    assert max(a["window_zctas"] for a in attempts) <= 60


def test_a_window_over_the_cap_does_not_end_growth_and_a_union_is_judged_not_its_part():
    """With a 25-ZCTA cap the adjacent step holds 21: a later window is wider than that only as a
    union with it, and a step over the cap is skipped, not the end of the steps."""
    repair = _repair()
    inst, plan, owner, free, state, pieces = _line()
    W = {f"z{i:02d}" for i in range(11)}
    got = repair.grow_windows(pieces, owner, W, free, inst.units.zip_adj, 3, 3, 25)
    assert got[0][0] == "grow-adjacent" and len(got[0][2]) == 21, [(s, len(V)) for s, _, V in got]
    assert any(shape == "grow-wider" and len(V) > 21 for shape, _, V in got), [(s, len(V)) for s, _, V in got]
    sizes = [len(V) for _, _, V in got]
    assert sizes == sorted(set(sizes)) and max(sizes) <= 25, sizes


def test_growth_is_off_with_grow_max_zero():
    repair = _repair()
    attempts, lines = _run(repair, lambda W: "infeasible", (0, 60))
    assert attempts and not [a for a in attempts if a["shape"].startswith("grow")]
    assert not any("growing" in x for x in lines)


def test_an_unknown_window_does_not_grow():
    """Unknown is no proof: the standard windows end unknown, nothing is grown; a growth window that
    ends unknown stops the growth."""
    repair = _repair()
    attempts, lines = _run(repair, lambda W: "unknown", (3, 60))
    assert attempts and not [a for a in attempts if a["shape"].startswith("grow")], _shapes(attempts)
    assert not any("growing" in x for x in lines)
    # infeasible until the growth, where the first window is unknown
    attempts, _ = _run(repair, lambda W: "unknown" if len(W) > 14 else "infeasible", (3, 60))
    grow = [a for a in attempts if a["shape"].startswith("grow")]
    assert [a["status"] for a in grow] == ["unknown"], _shapes(attempts)
    # a capped window that is unknown is not followed by its uncapped repeat or by a larger one
    assert grow[0]["cap"]


def test_a_solved_standard_window_does_not_grow():
    repair = _repair()
    attempts, _ = _run(repair, lambda W: "connected", (3, 60))
    assert len(attempts) == 1 and attempts[0]["status"] == "connected"


class _Pool:
    """Stands in for `WindowPool`: a task is solved when it is started."""

    def __init__(self, fn):
        self.fn, self.done, self.n, self.killed = fn, {}, 0, []

    def reserve(self):
        return True

    def unreserve(self):
        pass

    def start(self, task):
        self.n += 1
        self.done[self.n] = (self.fn(task), 0.1)
        return self.n

    def wait(self, handles, timeout):
        return [(h, self.done.pop(h)) for h in handles if h in self.done]

    def kill(self, handle):
        self.killed.append(handle)
        self.done.pop(handle, None)


def _race_run(repair, verdict, grow):
    inst, plan, owner, free, state, piece = _line()
    fn = _stub(repair, verdict)

    def task(t):
        c, own, W, *_rest, cap, flow, keep, repairing, opened = t
        return fn(inst, plan, own, W, {}, 1.0, cap)
    attempts = []
    with _patched(repair, fn):
        repair._repair_cluster(inst, plan, owner, piece, free, {}, state, 3, 14, 60.0, attempts,
                               quiet, pool=_Pool(task), grow=grow)
    return attempts


def test_growth_in_a_race_settles_as_the_loop_does():
    repair = _repair()
    verdict = lambda W: "connected" if "z32" in W else "infeasible"     # noqa: E731
    seq, _ = _run(repair, verdict, (3, 60))
    par = _race_run(repair, verdict, (3, 60))
    key = lambda xs: [(a["shape"], a["status"], a["cap"], a["window_zctas"]) for a in xs]   # noqa: E731
    assert key(par) == key(seq), (key(par), key(seq))
    unknown = lambda W: "unknown" if len(W) > 14 else "infeasible"      # noqa: E731
    seq, _ = _run(repair, unknown, (3, 60))
    assert key(_race_run(repair, unknown, (3, 60))) == key(seq)


# ------------------------------------------------------------------------------ growth, unstubbed
def _grow_toy():
    """A path p - b - a1 - a2 - c1 - c2 - c3 - c4 of three districts, K 3, τ 3, band (2.7, 3.3),
    every ZCTA of mass 1 but p (2).  NY (p, b) and NJ (c1-c4) are split units, so free; CT (a1, a2) is
    held whole.  The map has CT+NJ+NY#1 = {p, a1, a2} (4), p detached behind NY#1's b (1), and
    NJ#1 = {c1-c4} (4).  The ball around p is {p, b}: NY#1 takes both (3) but CT+NJ+NY#1 keeps 2, so
    no drawing exists.  With NJ's c1-c4 in the window (the adjacent districts' free ZCTAs), CT+NJ+NY#1
    takes c1 and the map is {p, b} | {a1, a2, c1} | {c2, c3, c4}, each connected, each 3."""
    path = ["p", "b", "a1", "a2", "c1", "c2", "c3", "c4"]
    mass = dict.fromkeys(path, 1.0) | {"p": 2.0}
    xy = {z: (float(i), 0.0) for i, z in enumerate(path)}
    inst, xym = tr._toy({"NY": ["p", "b"], "CT": ["a1", "a2"], "NJ": path[4:]}, list(zip(path, path[1:])),
                        mass, xy, {"NY": "free", "NJ": "free"}, k=3, delta=0.1, final_delta=0.1)
    plan = tr._plan(inst, [({"CT", "NJ", "NY"}, {"CT": 1.0, "NJ": 0.25, "NY": 0.0001}),
                           ({"NY"}, {"NY": 0.9999}), ({"NJ"}, {"NJ": 0.75})])
    a, b, c = (cp.name for cp in plan.copies)
    owner = {"p": a, "b": b, "a1": a, "a2": a} | dict.fromkeys(path[4:], c)
    return inst, xym, plan, owner, (a, b, c)


def test_a_window_scip_proves_infeasible_grows_and_the_grown_window_is_solved_by_scip():
    """No stub: `repair_channel` with `--engine scip`.  SCIP proves the ball around the detached
    piece infeasible (a solve, not the model's pre-check), with and without the cap; the adjacent
    districts' free ZCTAs are added; SCIP solves that window, and the piece is gone."""
    repair = _repair()
    solve_window = repair.solve_window
    inst, xy, plan, owner, (a, b, c) = _grow_toy()
    adj, m = inst.units.zip_adj, inst.channels["X"].m
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    assert repair.detached(owner, adj, m) == [(a, frozenset({"p"}))]
    lines, old = [], os.environ.get(repair.ENGINE_ENV)
    try:
        os.environ[repair.ENGINE_ENV] = "scip"
        done, attempts = repair.repair_channel(inst, plan, owner, p, dict(inst.units.unit_of), h0=1,
                                               max_zctas=100, time_limit=60.0, log=lines.append, grow_max=3)
    finally:
        if old is None:
            os.environ.pop(repair.ENGINE_ENV, None)
        else:
            os.environ[repair.ENGINE_ENV] = old
    assert repair.solve_window is solve_window
    shapes = [(x["shape"], x["status"], x["cap"], x["window_zctas"]) for x in attempts]
    assert shapes == [("ball", "infeasible", True, 2), ("ball", "infeasible", False, 2),
                      ("grow-adjacent", "optimal", True, 6)], shapes
    assert {x["engine"] for x in attempts} == {"scip"}
    for x in attempts[:2]:      # a solve of the engine's own, not the pre-check's "reachable by no district"
        assert x["note"] == "proved at solve 1" and x["group"]["iterations"] == 1 and x["group"]["columns"] > 0, x["group"]
    assert any("window of 2 ZCTAs (no cap) [scip]" in x and "-> infeasible" in x and "1 solves" in x
               for x in lines), lines
    assert any("proved infeasible; growing by 1 step(s) to 6 ZCTAs" in x for x in lines), lines
    assert any("window of 6 ZCTAs [scip]" in x and "-> optimal" in x for x in lines), lines
    grown = attempts[2]
    assert grown["districts"] == sorted((a, b, c)) and grown["pieces_before"] == 1 and grown["pieces_after"] == 0
    assert repair.detached(done, adj, m) == []
    assert done == {"p": b, "b": b, "a1": a, "a2": a, "c1": a, "c2": c, "c3": c, "c4": c}, done


# ------------------------------------------------------------------------------ a native crash
# A solver the child runs in place of `arms.scip_solve`: it kills itself with SIGSEGV as SCIP did on
# nw49-48, in the default setting (`TD_TEST_CRASH_ALWAYS`: in both), and otherwise solves for real.
CRASHY = '''
import os, signal
import arms

def solve(inst, time_limit, log=print, start=None, heuristics=True):
    if heuristics or os.environ.get("TD_TEST_CRASH_ALWAYS"):
        log("  c: about to fault")
        os.kill(os.getpid(), signal.SIGSEGV)
    return arms.scip_solve(inst, time_limit, log, start=start, heuristics=heuristics)
'''


@contextlib.contextmanager
def _crashing(always=False):
    import tempfile
    engine = _repair().scip_engine()
    old, old_env = engine.CHILD_SOLVER, os.environ.get("TD_TEST_CRASH_ALWAYS")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "crashy.py")
        with open(path, "w") as fh:
            fh.write(CRASHY)
        engine.CHILD_SOLVER = f"{path}:solve"
        if always:
            os.environ["TD_TEST_CRASH_ALWAYS"] = "1"
        try:
            yield engine
        finally:
            engine.CHILD_SOLVER = old
            if old_env is None:
                os.environ.pop("TD_TEST_CRASH_ALWAYS", None)
            else:
                os.environ["TD_TEST_CRASH_ALWAYS"] = old_env


def _crash_group(always):
    repair, draw = _repair(), tcr._draw()
    name, kw = synth.cases()[0]
    inst = synth.grid(name, **kw)
    lines = []
    args, skw = capture.rebuild_args(inst.doc["draw"])
    skw.update(dag=False, flow=False, layers=True, log=lines.append)
    with _crashing(always), repair.scip_engine().installed(draw) as runs, \
            capture.centres_patch(draw, inst.doc["draw"]):
        g = draw._solve_group(*args[:19], 120.0, **skw)
    return g, runs, lines


def test_a_crash_is_retried_once_with_heuristics_off_and_the_window_is_solved():
    g, runs, lines = _crash_group(always=False)
    assert g.status == "optimal", (g.status, g.note, lines)
    first = runs[0]
    assert (first["heuristics"], first["status"], first["signal"]) == (True, "crash", "SIGSEGV"), runs
    assert (runs[1]["heuristics"], runs[1]["status"]) == (False, "optimal"), runs
    assert sum(1 for r in runs if r["status"] == "crash") == 1, runs
    assert any("SCIP crashed" in x and "SIGSEGV" in x and "retrying once with primal heuristics off" in x
               for x in lines), lines
    assert any("primal heuristics off" in x for x in lines)


def test_a_crash_on_the_retry_leaves_the_window_unknown_not_infeasible():
    """At the group level the crash is `kSolveError`, no incumbent; `solve_window` then files the
    window `unknown` and takes no drawing, even one draw.py's construct heuristic holds."""
    g, runs, lines = _crash_group(always=True)
    assert g.status != "infeasible" and "SCIP crash" in g.note and "SIGSEGV" in g.note, (g.status, g.note)
    assert [(r["heuristics"], r["status"], r["signal"]) for r in runs] == \
        [(True, "crash", "SIGSEGV"), (False, "crash", "SIGSEGV")], runs
    repair = _repair()
    inst, xy, plan, owner, _ = _grow_toy()
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    with _crashing(always=True):
        w = repair.solve_window(inst, plan, owner, {"p", "b"}, p, 60.0, True, quiet, engine="scip")
    assert w.status == "unknown" and w.owner == {}, (w.status, w.owner)
    assert w.note.startswith("SCIP crashed (SIGSEGV) in both settings"), w.note
    assert [r["status"] for t in w.tried for r in t["engine_runs"]] == ["crash", "crash"] * len(w.tried)


def test_the_driver_survives_a_crashing_engine_and_does_not_grow_the_window():
    """`repair_channel` on the growth toy, whose ball window SCIP proves infeasible when it runs:
    with the solver faulting in both settings every window ends `unknown`, nothing grows, and the
    call returns the map unchanged with the crash recorded under each attempt."""
    repair = _repair()
    inst, xy, plan, owner, _ = _grow_toy()
    p = {z: (x / 1000.0, y / 1000.0) for z, (x, y) in xy.items()}
    lines, old = [], os.environ.get(repair.ENGINE_ENV)
    try:
        os.environ[repair.ENGINE_ENV] = "scip"
        with _crashing(always=True):
            done, attempts = repair.repair_channel(inst, plan, owner, p, dict(inst.units.unit_of), h0=1,
                                                   max_zctas=100, time_limit=60.0, log=lines.append,
                                                   grow_max=3)
    finally:
        if old is None:
            os.environ.pop(repair.ENGINE_ENV, None)
        else:
            os.environ[repair.ENGINE_ENV] = old
    assert attempts and {x["status"] for x in attempts} == {"unknown"}, [(x["shape"], x["status"]) for x in attempts]
    assert not any(x["shape"].startswith("grow") for x in attempts), [x["shape"] for x in attempts]
    assert not any("growing by" in x for x in lines), lines
    assert done == owner
    for x in attempts:
        runs = [r for t in x["tried"] for r in t.get("engine_runs", ())]
        assert runs and all(r["status"] == "crash" and r["signal"] == "SIGSEGV" for r in runs), x["tried"]
        assert {r["heuristics"] for r in runs} == {True, False}, runs
