"""tools/exp/bnc (td#142 phase 0): the four arms on small grids, the separator rows, the round trip
of an exported instance, the lazy-callback probe and the merge of a drawing into a ledger.

Every arm must return the same optimum on three small instances (6 × 6 to 8 × 5 cells, 2-3
districts) on which the model without any connectivity row beyond draw.py's up-front neighbour rows
has a *disconnected* optimum, and every drawing an arm returns must be connected, checked by a
breadth-first search that shares no code with the cut generator (`synth.connected`).  The exported
instances of the real groups are checked too when they are on disk (a SKIP line says when not).
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
import tempfile

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
