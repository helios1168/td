"""tools/exp/bnc (td#142 phase 0): the four arms on small grids, the separator rows, the round trip
of an exported instance, the lazy-callback probe and the merge of a drawing into a ledger.

Every arm must return the same optimum on three small instances (6 × 6 to 8 × 5 cells, 2-3
districts) on which the model without any connectivity row beyond draw.py's up-front neighbour rows
has a *disconnected* optimum, and every drawing an arm returns must be connected, checked by a
breadth-first search that shares no code with the cut generator (`synth.connected`).  The exported
instances of the real groups are checked too when they are on disk (a SKIP line says when not).
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BNC = os.path.join(HERE, "..", "tools", "exp", "bnc")
if BNC not in sys.path:
    sys.path.insert(0, BNC)

import capture  # noqa: E402
import inst_io  # noqa: E402
import sepcuts  # noqa: E402
import synth  # noqa: E402


def _mod(name: str, file: str):
    return capture.sibling(name, file)


arms = _mod("bnc_arms", "arms.py")
export = _mod("bnc_export", "export.py")
bnc_run = _mod("bnc_run", "run.py")
bnc_report = _mod("bnc_report", "report.py")

TOL = 1e-6


def _instances():
    return [(name, synth.grid(name, **kw)) for name, kw in synth.cases()]


def _no_cut_optimum(inst):
    """x of the MILP with nothing but draw.py's up-front rows."""
    import highspy
    h = inst.highs()
    h.run()
    assert h.getModelStatus() == highspy.HighsModelStatus.kOptimal
    return np.array(h.getSolution().col_value)


def test_each_grid_needs_cuts():
    """The premise of the other tests: without connectivity cuts the optimum is disconnected."""
    for name, inst in _instances():
        x = _no_cut_optimum(inst)
        det = sepcuts.Graphs(inst).detached(x)
        assert det, f"{name}: the model's optimum is already connected"
        assert not synth.connected(inst, inst.owner_of(x)), name


def test_arms_return_the_same_optimum_and_connected_drawings():
    for name, inst in _instances():
        got = {}
        for label, arm, kw in (("a", "a", {}), ("b", "b", {}), ("c", "c", {}),
                               ("c+frac", "c", {"frac_root": True})):
            r = arms.solve(arm, inst, 120.0, None, lambda *_: None, **kw)
            assert r["status"] == "optimal", (name, label, r["status"], r["note"])
            assert r["owner"] is not None and synth.connected(inst, r["owner"]), (name, label)
            obj, why = inst.evaluate(r["owner"])
            assert obj is not None and abs(obj - r["objective"]) <= TOL * max(1.0, abs(obj)), (name, label, obj, r["objective"], why)
            assert set(r["owner"]) == set(inst.zs), (name, label)
            got[label] = r["objective"]
        ref = got["a"]
        assert all(abs(v - ref) <= TOL * max(1.0, abs(ref)) for v in got.values()), (name, got)


def test_the_cut_loop_found_cuts_and_the_relaxation_is_a_lower_bound():
    """Arm b needed cuts on every grid; the connectivity-free optimum is at most the optimum."""
    for name, inst in _instances():
        b = arms.solve("b", inst, 120.0, None, lambda *_: None)
        assert b["cuts"] > 0 and b["rounds"] > 1, name
        h = inst.highs()
        h.run()
        free = h.getInfo().objective_function_value
        assert free <= b["objective"] + TOL * max(1.0, abs(b["objective"])), (name, free, b["objective"])


def test_separator_rows_are_valid_and_minimal():
    """Every row `integer_cuts` makes for the disconnected optimum is violated by it, held by the
    connected optimum, and its separator is minimal; the fractional rows from the LP relaxation are
    held by the connected optimum too."""
    import highspy
    for name, inst in _instances():
        x = _no_cut_optimum(inst)
        opt = arms.solve("a", inst, 120.0, None, lambda *_: None)["owner"]
        xo = inst.vector_of(opt)
        G = sepcuts.Graphs(inst)
        rows = G.integer_cuts(x)
        assert rows
        for r in rows:
            assert sepcuts.violated(r, x), (name, r)
            assert not sepcuts.violated(r, xo), (name, r)
        # minimality: for each detached component C of the optimum, each vertex of S has a neighbour
        # in the component of a and one in the component of b in G_j - S
        for j, comps in G.detached(x).items():
            main = G.components(j, G.selected(j, x))[0]
            b = inst.root.get(j) or max(main, key=lambda v: (inst.mass.get(v, 0.0), v))
            for comp in comps:
                sep = G.minimal_separator(j, comp, b)
                assert sep and not (sep & comp) and b not in sep
                ca = G._reach(j, comp, sep)
                cb = G._reach(j, [b], sep)
                assert not (ca & cb), "S does not separate"
                for s in sep:
                    assert any(w in ca for w in inst.adj[j][s]) and any(w in cb for w in inst.adj[j][s]), \
                        (name, j, s, "not minimal")
        # fractional rows from the LP relaxation
        h = inst.highs()
        h.changeColsIntegrality(inst.n, np.arange(inst.n, dtype=np.int32),
                                np.array([highspy.HighsVarType.kContinuous] * inst.n))
        h.run()
        xf = np.array(h.getSolution().col_value)
        for r in G.fractional_cuts(xf):
            assert sepcuts.violated(r, xf, 1e-5), (name, "not violated by the LP point")
            assert not sepcuts.violated(r, xo), (name, "cuts off the connected optimum", r)


def test_flow_formulation_confirms_the_optimum():
    """verify.py's SCIP model with flow rows and no cuts reaches the arms' optimum (rooted, two
    bodies and rootless districts)."""
    verify = _mod("bnc_verify", "verify.py")
    for name, inst in _instances():
        r = verify.run(inst, 120.0, lambda *_: None)
        ref = arms.solve("a", inst, 120.0, None, lambda *_: None)["objective"]
        assert r["scip_status"] == "optimal" and r["connected"], (name, r)
        assert abs(r["objective"] - ref) <= TOL * max(1.0, abs(ref)), (name, r["objective"], ref)


def test_round_trip_detects_a_difference():
    draw = capture.load_draw()
    name, inst = _instances()[0]
    doc = json.loads(json.dumps(inst.doc, default=float))
    rt = export.roundtrip(doc, draw)
    assert rt["ok"] and rt["columns"][0] == rt["columns"][1] == inst.n and rt["rows"][0] == inst.n_rows, rt
    doc["model"]["cost"][0] += 1e-3
    assert not export.roundtrip(doc, draw)["ok"]
    doc = json.loads(json.dumps(inst.doc, default=float))
    doc["draw"]["lo"] *= 0.9
    assert not export.roundtrip(doc, draw)["ok"]


def test_instance_survives_save_and_load():
    name, inst = _instances()[0]
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "x.json.gz")
        doc = json.loads(json.dumps(inst.doc, default=float))
        inst_io.save(doc, path)
        back = inst_io.load(path)
    assert back.n == inst.n and back.n_rows == inst.n_rows and back.js == inst.js
    assert np.array_equal(back.cost, inst.cost) and np.array_equal(back.row_idx, inst.row_idx)
    r = arms.solve("b", back, 60.0, None, lambda *_: None)
    assert r["status"] == "optimal"


def test_arm_d_records_the_lazy_callback_probe():
    """highspy 1.15.1 never invokes kCallbackMipDefineLazyConstraints and its callback input has no
    way to hand a row back (draw.py's docstring says the same).  If a later highspy makes it usable
    this fails, on purpose: arm d would need its loop."""
    name, inst = _instances()[0]
    r = arms.solve("d", inst, 30.0, None, lambda *_: None)
    p = r["probe"]
    assert len(p["attempts"]) == 2 and "input_fields" in p
    assert not p["usable"], "the callback became usable: write arm d's loop (arms.arm_d)"
    assert r["status"] == "not usable" and "invoked 0 times" in r["note"], r["note"]
    assert r["owner"] is None


def test_merge_replaces_the_groups_rows_and_flags_a_changed_body():
    name, inst = _instances()[0]
    owner = arms.solve("b", inst, 60.0, None, lambda *_: None)["owner"]
    with tempfile.TemporaryDirectory() as d:
        base, out = os.path.join(d, "base"), os.path.join(d, "out")
        os.makedirs(base)
        os.makedirs(out)
        fields = ["scenario", "zip_code", "current_channel", "state", "model_channel", "district",
                  "district_name", "m_rel", "reason"]
        ids = {"A": "X_01", "B": "X_02", "C": "X_03"}
        body = {z: j for j, bs in inst.doc["draw"]["bodies"].items() for b in bs for z in b}
        rows = []
        moved = min(z for z, j in body.items() if j == "B")      # one body cell the source map gave to A
        for z in sorted(set(inst.zs) | set(body)):
            j = "A" if z == moved else body.get(z, "A")         # every group ZCTA starts with district A
            for fine in ("fi", "wh"):
                rows.append({"scenario": "s", "zip_code": z, "current_channel": fine, "state": "ST",
                             "model_channel": "X", "district": ids[j], "district_name": "n",
                             "m_rel": "1", "reason": ""})
        rows.append({"scenario": "s", "zip_code": "other", "current_channel": "fi", "state": "ST",
                     "model_channel": "Y", "district": "Y_01", "district_name": "m", "m_rel": "1", "reason": ""})
        bnc_run.write_rows(os.path.join(base, "ledger.csv"), fields, rows)
        bnc_run.write_rows(os.path.join(base, "districts.csv"), ["channel", "district", "district_name", "copy"],
                           [{"channel": "X", "district": v, "district_name": f"n{v}", "copy": k} for k, v in ids.items()]
                           + [{"channel": "Y", "district": "Y_01", "district_name": "m", "copy": "A"}])
        with open(os.path.join(base, "run.json"), "w") as fh:
            json.dump({"fine_channels": ["fi", "wh"]}, fh)
        info = bnc_run.merge(inst, owner, base, {"channel": "X"}, out)
        assert info["replaced_rows"] == 2 * len(inst.zs)
        assert info["consistency"]["body_zctas_not_owned_as_modelled"] == 1
        assert info["consistency"]["examples"] == [moved]
        with open(os.path.join(out, "merged", "ledger.csv"), newline="") as fh:
            merged = list(csv.DictReader(fh))
        assert len(merged) == len(rows)
        got = {(r["zip_code"], r["current_channel"]): r["district"] for r in merged if r["model_channel"] == "X"}
        assert all(got[z, f] == ids[owner[z]] for z in inst.zs for f in ("fi", "wh"))
        assert [r for r in merged if r["model_channel"] == "Y"][0]["district"] == "Y_01"
        with open(os.path.join(out, "ledger.csv"), newline="") as fh:
            assert len(list(csv.DictReader(fh))) == 2 * len(inst.zs)


def test_exported_instances_reproduce_the_runs_groups():
    """The four exported groups (when exported): each is faithful to its run's contig.json record
    and rebuilds to the same MILP from the instance alone."""
    root = os.path.join(os.environ.get("TD_REPO", os.path.join(HERE, "..")), "runs", "exp",
                        "bnc_2026-10-15", "instances")
    names = [n for n in ("FI_PA", "FI_FL", "FI_NY", "WIFI_MD") if os.path.exists(os.path.join(root, f"{n}.json.gz"))]
    if not names:
        print("      SKIP: no exported instances under", root)
        return
    draw = capture.load_draw()
    for n in names:
        inst = inst_io.load(os.path.join(root, f"{n}.json.gz"))
        m = inst.doc["meta"]
        assert m["faithful"]["ok"] and m["roundtrip"]["ok"], (n, m["faithful"], m["roundtrip"])
        assert m["faithful"]["columns"][0] == m["faithful"]["columns"][1]
        again = export.roundtrip(inst.doc, draw)
        assert again["ok"], (n, again["problems"])
        assert set(inst.js) == set(m["districts"]) and len(inst.zs) == m["free_zctas"]


# ------------------------------------------------------------------------------ report, widths, runner
def _res(arm, status, objective, gate, seconds=10.0):
    return {"instance": "S", "arm": arm, "status": status, "objective": objective, "gate": gate,
            "seconds": seconds, "gap": 0.0, "nodes": 1, "note": "", "time_limit": 60.0, "threads": 1,
            "code_commit": "x", "source_sha256": SRC}


SRC = "f" * 64


def _gate(m1="pass", in_window=True):
    return {"m1": m1, "m1_items": ["i"] if m1 != "pass" else [], "m1_excluded": [], "map_m1": m1, "in_window": in_window,
            "other_districts_outside_window": []}


def test_report_winner_needs_the_m1_and_window_gates():
    """A cheaper feasible drawing that fails M1 or the window, or has no gate result, is never
    announced as the best connected drawing; it is listed as a failure / UNGATED."""
    rs = [_res("a", "feasible", 1.0, _gate("fail")), _res("b", "feasible", 2.0, _gate(in_window=False)),
          _res("c", "feasible", 3.0, None), _res("d", "feasible", 4.0, _gate())]
    text = "\n".join(bnc_report.winners(rs))
    assert "arm d's (objective 4" in text and "best connected drawing" in text, text
    assert "arm a (feasible" in text and "arm b (feasible" in text and "UNGATED" in text, text
    # no feasible drawing passes: nobody wins
    lines = bnc_report.winners(rs[:3])
    assert lines[0].startswith("- **S**: no arm finished") and "best connected" not in lines[0], lines
    # an optimum with no gate result or a failing gate is not a winner either
    for g in (None, _gate("fail")):
        lines = bnc_report.winners([_res("a", "optimal", 1.0, g)])
        assert "proved an optimum" not in lines[0], lines
    table = bnc_report.table(rs)
    assert table.count("**UNGATED**") == 2 and "no drawing" not in table, table
    assert "| S | e |" not in table
    none = bnc_report.table([_res("e", "not usable", None, None)])
    assert "UNGATED" not in none and "no drawing" not in none


def test_width_data_keeps_the_gates_inputs_of_the_group():
    """The exported widths hold polygon borders, connectors, gap widths, land and relays of the
    group's ZCTAs, bodies and neighbours, apart from the objective's border coefficients."""
    name, inst = _instances()[0]
    snap = json.loads(json.dumps(inst.doc["draw"]))
    zs = snap["zs"]
    zero = zs[0]
    snap["m"][zero] = 0.0
    a, b = zs[0], snap["adj"][zs[0]][0]
    polygon = {"border": {tuple(sorted((a, b))): 1500.0, ("far1", "far2"): 9.0},
               "connectors": [(zs[1], zs[2]), ("far1", zs[3])],
               "gaps": {(a, zs[-1]): 250.0, ("far1", "far2"): 5.0},
               "aland": {**{z: 1e6 for z in zs}, "far1": 2.0}, "state": {z: "ST" for z in zs}}
    w = capture.width_data(polygon, snap)
    assert w["border"] == [[*sorted((a, b)), 1500.0]], w["border"]
    assert w["connectors"] == [sorted((zs[1], zs[2]))] and w["gaps"] == [[*sorted((a, zs[-1])), 250.0]], w
    assert zero in w["relays"] and "far1" not in w["aland"] and w["aland"][zs[0]] == 1e6, w
    assert snap["border"] is None, "the widths do not come from the objective's border"


def _run_args(d, **kw):
    """`threads` None as in the other tests: HiGHS's pool is sized by the first value a process uses (trap 18)."""
    return types.SimpleNamespace(m2_dir=d, out=os.path.join(d, "runs", "exp", "bnc"),
                                 instances=os.path.join(d, "inst"), frac_root=False, no_flow=False,
                                 time_limit=60.0, threads=None, insts=["S"], arms=["a"], jobs=1, **kw)


def test_runner_always_gates_writes_manifests_and_has_no_bypass():
    name, inst = _instances()[0]
    called = []

    def fake_gate(inst_, owner, cfg, folder, log=print):
        called.append(folder)
        merged = os.path.join(folder, "merged")
        os.makedirs(merged, exist_ok=True)
        for d in (folder, merged):
            with open(os.path.join(d, "ledger.csv"), "w") as fh:
                fh.write("zip_code\n")
        if len(called) == 2:
            raise RuntimeError("gate broke")
        return _gate()
    with tempfile.TemporaryDirectory() as d:
        a = _run_args(d)
        os.makedirs(a.instances)
        with open(os.path.join(d, "spec.toml"), "w") as fh:
            fh.write("x")
        with open(os.path.join(d, "extract.json"), "w") as fh:
            fh.write("y")
        with open(os.path.join(a.instances, "S.json.gz"), "wb") as fh:
            fh.write(b"z")
        cfg = {"spec": os.path.join(d, "spec.toml"), "extract": os.path.join(d, "extract.json"), "channel": "X"}
        saved = (bnc_run.export.instances, bnc_run.inst_io.loads, bnc_run.gate)
        bnc_run.export.instances = lambda _d: {"S": cfg}
        bnc_run.inst_io.loads = lambda _b, _p="": inst
        bnc_run.gate = fake_gate
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert bnc_run.one("S", "b", a) == 0
                folder = os.path.join(a.out, "S", "b")
                assert called == [folder], called
                with open(os.path.join(folder, "result.json")) as fh:
                    res = json.load(fh)
                assert res["gate"]["m1"] == "pass"
                assert res["instance_sha256"] == hashlib.sha256(b"z").hexdigest(), res
                assert res["instance_path"] == os.path.join(os.path.abspath(a.instances), "S.json.gz"), res
                for f in (folder, os.path.join(folder, "merged")):
                    with open(os.path.join(f, "manifest.json")) as fh:
                        assert json.load(fh)["status"] == "done", f
                tracking = bnc_run.mandates().tracking(d, gate=lambda _d: "pass")
                assert [t for t in tracking if t.startswith("run folder with a ledger")] == [], tracking
                # a run whose gate raises leaves failed manifests, never a ledger without one
                try:
                    bnc_run.one("S", "b", a)
                    raise AssertionError("the gate error was swallowed")
                except RuntimeError as e:
                    assert "gate broke" in str(e)
                for f in (folder, os.path.join(folder, "merged")):
                    with open(os.path.join(f, "manifest.json")) as fh:
                        assert json.load(fh)["status"] == "failed", f
                # the first run's result.json was archived before the failed attempt: nothing to reuse
                assert not os.path.exists(os.path.join(folder, "result.json"))
                with open(os.path.join(folder, "result.previous.json")) as fh:
                    assert json.load(fh)["gate"]["m1"] == "pass"
                assert bnc_report.rows(a.out) == []
        finally:
            bnc_run.export.instances, bnc_run.inst_io.loads, bnc_run.gate = saved
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        try:
            bnc_run.main(["one", "FI_PA", "a", "--no-gate"])
            raise AssertionError("--no-gate still parses")
        except SystemExit as e:
            assert e.code == 2


def test_runner_records_the_instance_and_code_it_started_from_not_what_the_solve_left():
    """The instance file is replaced during the solve (a re-export, say): the result keeps the hash of
    the bytes that were solved, and the report then calls it stale instead of taking it for current."""
    name, inst = _instances()[0]
    with tempfile.TemporaryDirectory() as d:
        a = _run_args(d)
        os.makedirs(a.instances)
        path = os.path.join(a.instances, "S.json.gz")
        inst_io.save(json.loads(json.dumps(inst.doc, default=float)), path)
        with open(path, "rb") as fh:
            before = hashlib.sha256(fh.read()).hexdigest()
        for f, text in (("spec.toml", "x"), ("extract.json", "y")):
            with open(os.path.join(d, f), "w") as fh:
                fh.write(text)
        cfg = {"spec": os.path.join(d, "spec.toml"), "extract": os.path.join(d, "extract.json"), "channel": "X"}
        solved = []

        def fake_solve(arm, inst_, limit, threads, log, **kw):
            solved.append(inst_.n)
            with open(path, "wb") as fh:
                fh.write(b"re-exported during the solve")
            export.provenance = lambda: {"code_commit": "after", "code_dirty": True, "source_sha256": "after"}
            return {"arm": arm, "status": "infeasible", "objective": None, "bound": None, "gap": None, "nodes": 0,
                    "seconds": 0.1, "note": "", "owner": None, "rounds": 0, "cuts": 0}
        saved = (bnc_run.export.instances, arms.solve, export.provenance)
        bnc_run.export.instances = lambda _d: {"S": cfg}
        arms.solve = fake_solve
        export.provenance = lambda: {"code_commit": "before", "code_dirty": False, "source_sha256": "before"}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert bnc_run.one("S", "a", a) == 0
        finally:
            bnc_run.export.instances, arms.solve, export.provenance = saved
        with open(os.path.join(a.out, "S", "a", "result.json")) as fh:
            res = json.load(fh)
        assert solved == [inst.n], solved                   # the solve ran on the parsed original
        assert res["instance_sha256"] == before and res["instance_path"] == os.path.abspath(path), res
        assert res["code_commit"] == "before" and res["code_dirty"] is False and res["source_sha256"] == "before", res
        fresh, stale = bnc_report.split(a.out, a.instances)
        assert fresh == [] and "instance file changed" in stale[0][1], (fresh, stale)


def _verdict_world(bare=False):
    """Channel X, fine channel f, k = 3.  Chain r1 - p1 - p2 - r2 with q1 - q2 hanging off p2; every
    border 10 km (no neck).  D1 = p1 p2, D2 = q1 q2, D3 = r1 r2: D3 is in two pieces (a failure
    outside the group {D1, D2}) in the base map."""
    border = {("r1", "p1"): 1e4, ("p1", "p2"): 1e4, ("p2", "r2"): 1e4, ("p2", "q1"): 1e4, ("q1", "q2"): 1e4}
    vs = sorted({z for e in border for z in e})
    poly = {"vertices": vs, "edges": sorted(border), "state": dict.fromkeys(vs, "TX")}
    if not bare:
        poly.update(border=dict(border), connectors=[], aland=dict.fromkeys(vs, 1e8), voronoi_gaps={})
    owner = {"r1": "D3", "p1": "D1", "p2": "D1", "r2": "D3", "q1": "D2", "q2": "D2"}
    return poly, owner


def _verdict_check(poly, owner, mass=None, drop=()):
    from td import audit as td_audit
    mass = mass or {}
    cells = [td_audit.Cell(z, "f", "X", owner[z], mass.get(z, 1.0)) for z in poly["vertices"] if z not in drop]
    return td_audit.check_m1(td_audit.Run(cells, {"X": td_audit.Channel(3)}, polygon=poly, fine=("f",)))


MINE = {"X/D1", "X/D2"}


def test_m1_verdict_is_the_gates_less_only_proven_preexisting_outside_failures():
    poly, owner = _verdict_world()
    base = _verdict_check(poly, owner)
    assert base.status == "fail" and any("X/D3: detached piece" in i for i in base.items), base.items
    # a failure of D3 that the base map has with the same text is excluded and listed; the rest passes
    v = bnc_run.m1_verdict(base, MINE, lambda: base.items)
    assert v["m1"] == "pass" and v["m1_items"] == [] and len(v["m1_excluded"]) == 1, v
    assert v["m1_excluded"][0].startswith("X/D3: detached piece")
    # without a base to compare with, nothing is excluded
    assert bnc_run.m1_verdict(base, MINE)["m1"] == "fail"
    assert bnc_run.m1_verdict(base, MINE, lambda: [])["m1"] == "fail"
    # the same failure in a group district is never excluded, even when the base map has it too
    mine_d3 = bnc_run.m1_verdict(base, MINE | {"X/D3"}, lambda: base.items)
    assert mine_d3["m1"] == "fail" and mine_d3["m1_excluded"] == []
    # a piece of the group's own district fails beside the excluded one
    owner2 = dict(owner, q2="D1")
    bad = _verdict_check(poly, owner2)
    v = bnc_run.m1_verdict(bad, MINE, lambda: base.items)
    assert v["m1"] == "fail" and any(i.startswith("X/D1: detached piece") for i in v["m1_items"]), v
    assert len(v["m1_excluded"]) == 1
    # an outside item whose text changed (its mass moved) is a new failure, not the base's
    moved = _verdict_check(poly, owner, mass={"r2": 2.0})
    v = bnc_run.m1_verdict(moved, MINE, lambda: base.items)
    assert v["m1"] == "fail" and v["m1_excluded"] == [] and v["m1_items"], v


def test_m1_verdict_never_drops_coverage_ownership_or_unverified_results():
    poly, owner = _verdict_world()
    clean = dict(owner, r2="D1")                       # D3 = r1 alone, connected: the map is clean
    good = _verdict_check(poly, clean)
    assert good.status == "pass" and bnc_run.m1_verdict(good, MINE)["m1"] == "pass"
    # a missing zero-opportunity fine-channel row: no piece, no neck, and the gate fails
    miss = _verdict_check(poly, clean, mass={"r1": 0.0}, drop=("r1",))
    assert miss.status == "fail" and any("have no row" in i for i in miss.items), miss.items
    v = bnc_run.m1_verdict(miss, MINE, lambda: miss.items)      # even when the base map has the same hole
    assert v["m1"] == "fail" and v["m1_excluded"] == [] and any("have no row" in i for i in v["m1_items"]), v
    # a ZCTA owned twice
    from td import audit as td_audit
    cells = [td_audit.Cell(z, "f", "X", clean[z], 1.0) for z in poly["vertices"]] + [td_audit.Cell("q1", "f", "X", "D1", 1.0)]
    twice = td_audit.check_m1(td_audit.Run(cells, {"X": td_audit.Channel(3)}, polygon=poly, fine=("f",)))
    v = bnc_run.m1_verdict(twice, MINE, lambda: twice.items)
    assert twice.status == "fail" and v["m1"] == "fail" and any("owned by" in i for i in v["m1_items"]), v
    # a coverage hole beside an excluded outside piece still fails
    both = _verdict_check(poly, owner, mass={"q2": 0.0}, drop=("q2",))
    base = _verdict_check(poly, owner, mass={"q2": 0.0})
    v = bnc_run.m1_verdict(both, MINE, lambda: base.items)
    assert v["m1"] == "fail" and len(v["m1_excluded"]) == 1 and any("have no row" in i for i in v["m1_items"]), v
    # a gate that cannot check necks (no border lengths) is ungated, never a pass
    bare_poly, _ = _verdict_world(bare=True)
    unv = _verdict_check(bare_poly, clean)
    assert unv.status == "unverified"
    v = bnc_run.m1_verdict(unv, MINE, lambda: [])
    assert v["m1"] == "ungated" and v["m1_items"], v
    # an unverified polygon graph with a pre-existing outside piece: the gate fails on the piece, the
    # exclusion empties the list, and the unmeasured necks still keep the verdict off `pass`
    bare_base = _verdict_check(bare_poly, owner)
    assert bare_base.status == "fail" and bare_base.counts["necks"] is None, bare_base.items
    v = bnc_run.m1_verdict(bare_base, MINE, lambda: bare_base.items)
    assert v["m1"] == "ungated" and v["m1_items"] and len(v["m1_excluded"]) == 1, v
    assert not bnc_report.passes(_res("a", "optimal", 1.0, _gate(m1="ungated")))
    assert "**UNGATED**" in bnc_report.table([_res("a", "optimal", 1.0, _gate(m1="ungated"))])


def test_m1_verdict_keeps_an_unresolved_neck_search_even_when_the_base_map_has_it():
    unresolved = ("X/D3: neck unresolved (the search stopped at bound 1.5 km, under 5 km): listed as a neck")
    chk = types.SimpleNamespace(status="fail", items=[unresolved], summary="1 unresolved", counts={"necks": 1})
    v = bnc_run.m1_verdict(chk, MINE, lambda: [unresolved])
    assert v["m1"] == "fail" and v["m1_items"] == [unresolved] and v["m1_excluded"] == [], v
    proved = "X/D3: neck 1.00 km wide cuts off 2 ZIPs (a...), 5.0% of its land area and 1.0% of its mass; cut a-b 1.00 km"
    chk = types.SimpleNamespace(status="fail", items=[proved, unresolved], summary="2", counts={"necks": 2})
    v = bnc_run.m1_verdict(chk, MINE, lambda: [proved, unresolved])
    assert v["m1"] == "fail" and v["m1_items"] == [unresolved] and v["m1_excluded"] == [proved], v


def test_report_tables_only_the_campaign_of_the_newest_result():
    """After a subset rerun an older arm (other commit, limit, threads, settings or instance file) is
    listed as stale and neither tabled nor a winner."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "instances"))
        with open(os.path.join(d, "instances", "S.json.gz"), "wb") as fh:
            fh.write(b"inst")
        sha = hashlib.sha256(b"inst").hexdigest()

        def put(arm, finished, **kw):
            r = dict(_res(arm, "optimal", 1.0, _gate(), seconds=5.0 if arm == "a" else 50.0), finished=finished,
                     **{"instance_sha256": sha, **kw})
            os.makedirs(os.path.join(d, "S", arm), exist_ok=True)
            with open(os.path.join(d, "S", arm, "result.json"), "w") as fh:
                json.dump(r, fh)
        put("a", "2026-10-15T09:00:00", code_commit="old")      # fastest arm, but an older campaign
        put("b", "2026-10-15T10:00:00")
        put("c", "2026-10-15T10:01:00", settings={"frac_root": True})
        put("d", "2026-10-15T08:00:00", time_limit=7.0)
        fresh, stale = bnc_report.split(d)
        assert sorted(r["arm"] for r in fresh) == ["b", "c"], fresh
        assert sorted(r["arm"] for r, _ in stale) == ["a", "d"], stale
        with open(bnc_report.write(d)) as fh:
            text = fh.read()
        assert "## Stale results excluded" in text and "| S | a |" not in text and "| S | d |" not in text, text
        assert "arm a proved" not in text and "arm b proved" in text, text
        # the instance file is not the one arm b ran on
        put("b", "2026-10-15T10:00:00", instance_sha256="0" * 64)
        assert [r["arm"] for r in bnc_report.rows(d)] == ["c"]


def test_source_fingerprint_is_the_content_of_the_sources_not_git_state_or_times():
    def tree(d, a=b"x = 1\n", b=b"y = 2\n"):
        for rel, body in (("td/a.py", a), ("tools/exp/bnc/b.py", b), ("tools/exp/bnc/notes.txt", b"ignored")):
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            with open(os.path.join(d, rel), "wb") as fh:
                fh.write(body)
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2, tempfile.TemporaryDirectory() as d3:
        tree(d1)
        tree(d2)
        os.utime(os.path.join(d2, "td", "a.py"), (1, 1))                    # other times, same bytes
        with open(os.path.join(d2, "tools", "exp", "bnc", "notes.txt"), "wb") as fh:
            fh.write(b"other notes")                                         # not a source
        tree(d3, a=b"x = 2\n")                                              # one byte of one source
        f1, f2, f3 = (export.source_fingerprint(d) for d in (d1, d2, d3))
        assert f1 == f2 != f3 and len(f1) == 64
        os.rename(os.path.join(d1, "td", "a.py"), os.path.join(d1, "td", "c.py"))      # the same bytes under another name
        assert export.source_fingerprint(d1) != f1
    with tempfile.TemporaryDirectory() as empty:
        try:
            export.source_fingerprint(empty)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("fingerprinted a root with no sources")
    prov = export.provenance()
    assert prov["source_sha256"] == export.source_fingerprint() and {"code_commit", "code_dirty"} <= set(prov)


def test_report_tables_only_results_of_the_campaigns_source_fingerprint():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "instances"))
        with open(os.path.join(d, "instances", "S.json.gz"), "wb") as fh:
            fh.write(b"inst")
        sha = hashlib.sha256(b"inst").hexdigest()

        def put(arm, finished, **kw):
            r = dict(_res(arm, "optimal", 1.0, _gate()), finished=finished, **{"instance_sha256": sha, **kw})
            if kw.get("source_sha256", 1) is None:
                del r["source_sha256"]
            os.makedirs(os.path.join(d, "S", arm), exist_ok=True)
            with open(os.path.join(d, "S", arm, "result.json"), "w") as fh:
                json.dump(r, fh)
        put("a", "2026-10-15T09:00:00")
        put("b", "2026-10-15T10:00:00")
        put("d", "2026-10-15T10:02:00", source_sha256=None)           # the newest records no fingerprint at all
        fresh, stale = bnc_report.split(d)
        why = {r["arm"]: w for r, w in stale}
        assert fresh == [] and sorted(why) == ["a", "b", "d"], (fresh, why)
        assert "no source fingerprint recorded" in why["d"] and "source_sha256" in why["a"], why
    with tempfile.TemporaryDirectory() as d:                            # same commit and dirty flag, other file content:
        # the newest result (arm c) is the campaign, a and b are stale
        os.makedirs(os.path.join(d, "instances"))
        with open(os.path.join(d, "instances", "S.json.gz"), "wb") as fh:
            fh.write(b"inst")
        for arm, fin, src in (("a", "09", SRC), ("b", "10", SRC), ("c", "11", "e" * 64)):
            os.makedirs(os.path.join(d, "S", arm))
            with open(os.path.join(d, "S", arm, "result.json"), "w") as fh:
                json.dump(dict(_res(arm, "optimal", 1.0, _gate()), finished=f"2026-10-15T{fin}:00:00",
                               instance_sha256=hashlib.sha256(b"inst").hexdigest(), source_sha256=src), fh)
        fresh, stale = bnc_report.split(d)
        assert [r["arm"] for r in fresh] == ["c"] and sorted(r["arm"] for r, _ in stale) == ["a", "b"], (fresh, stale)
        assert all("source_sha256" in w for _, w in stale), stale


def test_report_admits_a_result_only_with_its_instance_file_and_hash():
    """No recorded hash, no file, or another file: stale.  The file is looked for where the run
    recorded it (a custom instance directory), unless the caller names a directory."""
    with tempfile.TemporaryDirectory() as d:
        custom = os.path.join(d, "elsewhere")
        os.makedirs(custom)
        path = os.path.join(custom, "S.json.gz")
        with open(path, "wb") as fh:
            fh.write(b"inst")
        sha = hashlib.sha256(b"inst").hexdigest()

        def put(arm, **kw):
            r = dict(_res(arm, "optimal", 1.0, _gate()), finished="2026-10-15T10:00:00", **kw)
            os.makedirs(os.path.join(d, "S", arm), exist_ok=True)
            with open(os.path.join(d, "S", arm, "result.json"), "w") as fh:
                json.dump(r, fh)

        def verdict(**kw):
            fresh, stale = bnc_report.split(d, **kw)
            return sorted(r["arm"] for r in fresh), {r["arm"]: why for r, why in stale}
        put("a", instance_sha256=sha, instance_path=path)       # run with --instances elsewhere
        put("b", instance_path=path)                            # no hash
        put("c", instance_sha256=sha)                           # no location: <out>/instances, which is empty
        put("d", instance_sha256=sha, instance_path=os.path.join(d, "gone", "S.json.gz"))
        fresh, stale = verdict()
        assert fresh == ["a"], (fresh, stale)
        assert "no instance sha256" in stale["b"] and "not available" in stale["c"] and "not available" in stale["d"], stale
        # the caller's directory wins over the recorded path
        assert verdict(instances=custom)[0] == ["a", "c", "d"]
        assert "not available" in verdict(instances=os.path.join(d, "none"))[1]["a"]
        with open(path, "wb") as fh:
            fh.write(b"replaced")
        assert "instance file changed" in verdict()[1]["a"]


def test_report_lists_an_independent_check_only_for_the_campaigns_instance():
    """A verification without a commit or hash, of a replaced or missing instance, or of another file
    than the one the tabled results ran on, is excluded and says why."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "instances"))
        path = os.path.join(d, "instances", "S.json.gz")
        with open(path, "wb") as fh:
            fh.write(b"inst")
        sha = hashlib.sha256(b"inst").hexdigest()
        os.makedirs(os.path.join(d, "S", "a"))
        with open(os.path.join(d, "S", "a", "result.json"), "w") as fh:
            json.dump(dict(_res("a", "optimal", 1.0, _gate()), finished="2026-10-15T10:00:00", instance_sha256=sha), fh)

        def put(name, **kw):
            v = {"instance": "S", "scip_status": "optimal", "seconds": 1.0, "nodes": 1, "objective": 1.0,
                 "connected": True, "time_limit": 60.0, **kw}
            with open(os.path.join(d, "S", name), "w") as fh:
                json.dump(v, fh)
        put("verify.json", instance_sha256=sha, instance_path=path, code_commit="x", source_sha256=SRC)
        put("verify_nohash.json", code_commit="x", source_sha256=SRC)
        put("verify_nocode.json", instance_sha256=sha, source_sha256=SRC)
        put("verify_other.json", instance_sha256="0" * 64, code_commit="x", source_sha256=SRC)
        put("verify_nosrc.json", instance_sha256=sha, code_commit="x")
        put("verify_othersrc.json", instance_sha256=sha, code_commit="x", source_sha256="e" * 64)
        ok, bad = bnc_report.checks(d)
        assert len(ok) == 1 and ok[0]["instance_sha256"] == sha, ok
        why = {os.path.basename(p): w for p, w in bad}
        assert set(why) == {"verify_nohash.json", "verify_nocode.json", "verify_other.json", "verify_nosrc.json",
                            "verify_othersrc.json"}, why
        assert "no source fingerprint" in why["verify_nosrc.json"], why
        assert "other source code" in why["verify_othersrc.json"], why
        assert "no instance sha256" in why["verify_nohash.json"] and "no code commit" in why["verify_nocode.json"], why
        assert "instance file changed" in why["verify_other.json"], why
        with open(bnc_report.write(d)) as fh:
            text = fh.read()
        assert "## Independent checks excluded" in text and "verify_other.json" in text, text
        # the instance is re-exported after the verification: the check no longer belongs to it
        with open(path, "wb") as fh:
            fh.write(b"re-exported")
        ok, bad = bnc_report.checks(d)
        assert ok == [] and len(bad) == 6 and all(w for _, w in bad), (ok, bad)
        # the file is gone
        os.remove(path)
        assert bnc_report.checks(d)[0] == []
        with open(bnc_report.write(d)) as fh:
            assert "not available" in fh.read()


def test_all_exits_nonzero_on_a_failed_child_and_drops_its_old_result():
    class Child:
        def __init__(self, cmd, **kw):
            arm, out = cmd[5], cmd[cmd.index("--out") + 1]
            self.returncode = {"a": 3, "b": 0, "c": 0}[arm]
            if arm == "c":
                inst = os.path.join(cmd[cmd.index("--instances") + 1], "S.json.gz")
                with open(os.path.join(out, "S", "c", "result.json"), "w") as fh:
                    json.dump(dict(_res("c", "optimal", 1.0, _gate()), instance_sha256=bnc_report._sha256(inst)), fh)

        def poll(self):
            return self.returncode
    saved = bnc_run.subprocess, bnc_run.time
    bnc_run.subprocess, bnc_run.time = types.SimpleNamespace(Popen=Child, DEVNULL=-3), types.SimpleNamespace(sleep=lambda s: None)
    try:
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            a = _run_args(d)
            a.arms = ["a", "b", "c"]
            os.makedirs(a.instances)
            with open(os.path.join(a.instances, "S.json.gz"), "wb") as fh:
                fh.write(b"inst")
            for arm in "abc":
                os.makedirs(os.path.join(a.out, "S", arm))
                with open(os.path.join(a.out, "S", arm, "result.json"), "w") as fh:
                    json.dump(_res(arm, "optimal", 0.5, _gate()), fh)
            assert bnc_run.all_runs(a) == 1
            for arm in "ab":      # rc 3, and rc 0 without a new result: the old measurement is not reported
                assert not os.path.exists(os.path.join(a.out, "S", arm, "result.json"))
                assert os.path.exists(os.path.join(a.out, "S", arm, "result.previous.json"))
            with open(os.path.join(a.out, "REPORT.md")) as fh:
                report = fh.read()
            assert "| S | c |" in report and "| S | a |" not in report and "| S | b |" not in report, report
            a.arms = ["c"]
            assert bnc_run.all_runs(a) == 0
    finally:
        bnc_run.subprocess, bnc_run.time = saved
