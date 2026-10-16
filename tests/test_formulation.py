"""#143: independently written F0/F4/F142 specifications on 30..300 ZCTAs.

Agent: modeler (openai-codex/gpt-6-astra).
"""
from __future__ import annotations

import gzip
import hashlib
import inspect
import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import highspy
import networkx as nx
import pyomo.environ as pyo

from td.formulation import f0, f4, f142
from tests.test_contig_realize import _draw

BNC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "exp", "bnc")
if BNC not in sys.path:
    sys.path.append(BNC)

import capture  # noqa: E402
import synth  # noqa: E402

bnc_arms = capture.sibling("bnc_arms", "arms.py")
bnc_verify = capture.sibling("bnc_verify", "verify.py")


def _solve(model, assignment=None):
    if assignment is not None:
        if any((z, j) not in model.X for z, j in assignment.items()):
            return "infeasible", None
        for (z, j), x in model.x.items():
            x.fix(int(assignment[z] == j))
    solver = pyo.SolverFactory("highs")
    solver.options.update({"mip_rel_gap": 0.0, "mip_abs_gap": 0.0, "time_limit": 90.0})
    for _ in range(1000):
        result = solver.solve(model, load_solutions=False)
        term = result.solver.termination_condition
        if term == pyo.TerminationCondition.infeasible:
            return "infeasible", None
        assert term == pyo.TerminationCondition.optimal, (model.name, term)
        model.solutions.load_from(result)
        if model.name != "F142" or f142.separate(model) == 0:
            return "optimal", pyo.value(model.objective)
    raise AssertionError("F142 integer-separation iteration limit")


def _production(call, centres, assignment=None):
    """Use draw's own build/solve/cut path; fixing actual x columns changes no input.

    Do not restrict allowed lists to fix a point: that changes normalized objective
    coefficients. Disable constructed starts for fixed-point feasibility checks.
    """
    draw = _draw()
    seen = []

    class Highs(highspy.Highs):
        def run(self):
            frame = inspect.currentframe().f_back
            assert frame.f_code.co_name == "_solve_group"
            col = frame.f_locals["col"]
            assert self.getOptionValue("mip_rel_gap")[1] == 0.0
            seen.append(dict(col))
            if assignment is not None:
                for (z, j), i in col.items():
                    x = float(assignment[z] == j)
                    self.changeColBounds(i, x, x)
            return super().run()

    shim = NS(**{k: getattr(highspy, k) for k in dir(highspy) if not k.startswith("__")})
    shim.Highs = Highs

    def center_input(inst, c, v, support, p):
        return {j: centres[v, j] for j in support}

    with patch.object(draw, "highspy", shim), patch.object(draw.tdrealize, "centres", center_input):
        if assignment is None:
            result = draw._solve_group(**call)
        else:
            with patch.object(draw, "construct", lambda *a, **kw: (None, "fixed-point test")):
                result = draw._solve_group(**call)
    assert result.status in ("optimal", "infeasible"), result.report()
    if seen:
        result.x_columns = set(seen[0])
    return result


def _call(G, pos, mass, *, fixed, known, land=False, targets=False, restricted=False):
    """One declared conditional group; geometry/centres are shared *inputs*."""
    js = ["A", "B"]
    zs = sorted(set(G) - set(fixed))
    unit_of = dict.fromkeys(G, "U")
    bodies = {j: sorted((frozenset(cc) for cc in nx.connected_components(
        G.subgraph([z for z in fixed if fixed[z] == j]))), key=lambda cc: (-len(cc), min(cc))) for j in js}
    body_of = {z: (j, i) for j, bs in bodies.items() for i, b in enumerate(bs) for z in b}
    allowed = {z: js[:] for z in zs}
    if restricted:
        # Preserve an eight-ZCTA choice window, fix the other ownership lists.
        for z in zs[:-8]:
            allowed[z] = [known[z]]
    total = math.fsum(mass.values())
    planned = {("U", j): math.fsum(mass[z] for z in G if known[z] == j) for j in js}
    inst = NS(channels={"X": NS(tau=total / 2, M={"U": total}, m=mass)},
              units=NS(zips={"U": sorted(G)}, unit_of=unit_of))
    plan = NS(copies=[NS(name=j, total=planned["U", j]) for j in js])
    centres = {("U", j): pos[min(z for z in G if known[z] == j)] for j in js}
    call = dict(c="X", zs=zs, allowed=allowed, bodies=bodies, body_of=body_of, fixed=fixed,
        adj={z: set(G[z]) for z in G}, m=mass, p=pos, unit_of=unit_of, hold={"U": js},
        plan=plan, planned=planned, support={j: frozenset({"U"}) for j in js}, inst=inst,
        lo=min(planned.values()) - 2, hi=max(planned.values()) + 2,
        arm="move" if targets else "arm1", fixed_targets=targets, time_limit=90.0,
        log=lambda *_: None, dag=False, flow=False,
        border={tuple(sorted(e)): 1 + (i % 7) / 10 for i, e in enumerate(sorted(G.edges()))},
        land={"aland": {z: 10.0 if known[z] == "A" else 1.0 for z in G}, "ratio": 1.5} if land else None)
    return call, centres, {z: known[z] for z in zs}


def _grid(width, height, *, bodies=True, land=False, targets=False, restricted=False):
    G = nx.grid_2d_graph(width, height)
    labels = {(x, y): f"z{x:02d}_{y:02d}" for x, y in G}
    pos = {labels[x, y]: (float(x), float(y)) for x, y in G}
    G = nx.relabel_nodes(G, labels)
    known = {z: "A" if p[0] < width / 2 else "B" for z, p in pos.items()}
    mass = {z: (0.0 if int(p[1]) == 0 else 1.0) for z, p in pos.items()}
    fixed = {}
    if bodies:
        for j, x, near in (("A", -1, 0), ("B", width, width - 1)):
            z = f"body{j}"
            pos[z] = (float(x), 1.0)
            G.add_edge(z, labels[near, 1])
            known[z], fixed[z], mass[z] = j, j, 2.0
    return _call(G, pos, mass, fixed=fixed, known=known, land=land, targets=targets, restricted=restricted)


def _bad_point(call, good):
    # Find an allowed ownership change creating a disconnected district, independently
    # of either formulation. It may additionally violate band/target rows.
    full = {**call["fixed"], **good}
    G = nx.Graph(call["adj"])
    for z in sorted(good):
        for j in call["allowed"][z]:
            if j == good[z]:
                continue
            candidate = {**full, z: j}
            if any(nx.number_connected_components(G.subgraph([w for w in G if candidate[w] == k])) > 1
                   for k in ("A", "B")):
                return {**good, z: j}
    raise AssertionError("fixture must have an allowed disconnected assignment")


def _conformance(name, fixture):
    call, centres, good = fixture
    n = len(set(call["zs"]) | set(call["fixed"]))
    assert 30 <= n <= 300
    data = f4.prepare(call, centres=centres)
    result = _production(call, centres)
    assert result.status == "optimal", (name, result.report())
    optima = []
    for build in (f4.build_model, f142.build_model):
        model = build(data)
        verdict, optimum = _solve(model)
        assert verdict == "optimal", (name, model.name, verdict)
        assert set(model.X) == result.x_columns, (name, "pruned columns differ")
        assert abs(optimum - result.objective) < 2e-6, (name, model.name, optimum, result.objective)
        optima.append(optimum)
    # Chosen point, production optimum, and a deliberately broken point all use
    # exactly the same original lists, objective normalization and fixed bodies.
    for point, expected in ((good, "optimal"), (result.owner, "optimal"), (_bad_point(call, good), "infeasible")):
        actual = _production(call, centres, point)
        assert actual.status == expected, (name, expected, actual.report())
        for build in (f4.build_model, f142.build_model):
            verdict, value = _solve(build(data), point)
            assert verdict == expected, (name, build.__module__, expected, verdict)
            if value is not None:
                assert abs(value - actual.objective) < 2e-6, (name, value, actual.objective)
    print(f"  FORMULATION {name}: {n} ZCTAs, F4=draw=F142 {optima[0]:.9f}; 3 point verdicts agree")


def test_formulation_grid_bodies_38():
    _conformance("grid-6x6-bodies", _grid(6, 6))


def test_formulation_grid_rootless_30():
    _conformance("grid-10x3-rootless", _grid(10, 3, bodies=False, restricted=True))


def test_formulation_grid_land_targets_move_50():
    _conformance("grid-8x6-land-targets-move", _grid(8, 6, land=True, targets=True, restricted=True))


def _slice_from_export(source):
    """Reproduce the committed real fixture from #142's captured input data.

    Retain induced geography, masses, coordinates, border and land. Two vertices
    become fixed seed bodies, lists admit A/B, and the band is slice-specific.
    Nothing from the bnc branch is imported or executed.
    """
    with gzip.open(source, "rt") as stream:
        snap = json.load(stream)["draw"]
    G = nx.Graph()
    G.add_nodes_from(snap["zs"])
    G.add_edges_from((z, w) for z in snap["zs"] for w in snap["adj"][z] if w in snap["zs"])
    nodes = list(nx.bfs_tree(G, min(G), sort_neighbors=sorted))[:30]
    assert len(nodes) == 30
    G = G.subgraph(nodes).copy()
    tree = nx.bfs_tree(G, nodes[0], sort_neighbors=sorted).to_undirected()
    # A tree-edge partition gives an explicit connected witness in the induced graph.
    choices = []
    for e in sorted(tree.edges()):
        trial = tree.copy()
        trial.remove_edge(*e)
        parts = list(nx.connected_components(trial))
        choices.append((abs(len(parts[0]) - len(parts[1])), e, parts))
    _, _, parts = min(choices, key=lambda x: (x[0], x[1]))
    known = {z: j for j, cc in zip(("A", "B"), parts) for z in cc}
    fixed = {min(cc): j for j, cc in zip(("A", "B"), parts)}
    pos = {z: tuple(snap["p"][z]) for z in G}
    mass = {z: snap["m"].get(z, 0) for z in G}
    call, centres, good = _call(G, pos, mass, fixed=fixed, known=known, land=True, restricted=True)
    call["border"] = {(a, b): w for a, b, w in snap["border"] if a in G and b in G}
    call["land"] = {"aland": {z: snap["land"]["aland"][z] for z in G}, "ratio": 10.0}
    return call, centres, good


def _real_slice():
    # The committed small fixture is always tested, including without hub inputs.
    path = Path(__file__).parent / "fixtures/formulation/fi_pa_30.json"
    doc = json.loads(path.read_text())
    G = nx.Graph()
    G.add_nodes_from(doc["p"])
    G.add_edges_from(doc["edges"])
    call, centres, good = _call(G, {z: tuple(p) for z, p in doc["p"].items()}, doc["m"],
        fixed=doc["fixed"], known=doc["known"], land=True, restricted=True)
    call["border"] = {(a, b): w for a, b, w in doc["border"]}
    call["land"] = doc["land"]
    root = Path(os.environ.get("TD_REPO", Path(__file__).resolve().parents[1]))
    source = root / doc["provenance"]["source"]
    if source.is_file():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == doc["provenance"]["source_sha256"]
        rebuilt, cs, owner = _slice_from_export(source)
        for key in ("zs", "allowed", "bodies", "fixed", "adj", "m", "p", "border", "land", "lo", "hi"):
            assert rebuilt[key] == call[key], ("real fixture differs from source", key)
        assert cs == centres and owner == good
    return call, centres, good


def test_formulation_real_pa_slice_30():
    _conformance("FI_PA-induced-slice", _real_slice())


def _f0_instance(forbidden=None, split_wifi=False):
    # 60 ZCTAs, 48 active districts. WH districts each have $1000M;
    # WIFI's first pair has $1300M, requiring exclusive ownership of its state.
    Z = [f"z{i:02d}" for i in range(60)]
    nwifi, kwh = (4, 46) if split_wifi else (2, 47)
    pairs = 60 - nwifi - kwh
    state = {z: ("S" if i < nwifi else f"S{i:02d}") for i, z in enumerate(Z)}
    rho = {(z, "fine"): "WIFI" if i < nwifi else "WH" for i, z in enumerate(Z)}
    own = {}
    for i, z in enumerate(Z):
        k = i - nwifi
        own[z] = i // 2 + 1 if i < nwifi else (k // 2 + 1 if k < 2 * pairs else k - pairs + 1)
    counts = {j: sum(i >= nwifi and own[z] == j for i, z in enumerate(Z)) for j in range(1, kwh + 1)}
    mass = {(z, "fine"): (650 if i < 2 else 425 if i < nwifi else 1000 / counts[own[z]]) for i, z in enumerate(Z)}
    model = f0.build_model(Z=Z, F=["fine"], rho=rho, m=mass, rates={"fine": 1}, state=state,
        E_P=list(zip(Z, Z[1:])), manhattan=(), forbidden={"WIFI": forbidden or [], "WH": []},
        shape=lambda t: sum(t.x["fixed", "WIFI", j, Z[0]] * j for j in t.J),
        balance=lambda t: sum(t.y.values()))
    for h, c, j, z in model.x:
        model.x[h, c, j, z].fix(int(j == own[z]))
    for h, c, j in model.y:
        model.y[h, c, j].fix(int((c == "WIFI" and j <= nwifi // 2) or (c == "WH" and j <= kwh)))
    return model


def _solve_f0(model):
    pyo.TransformationFactory("gdp.bigm").apply_to(model)
    solver = pyo.SolverFactory("highs")
    solver.options.update({"mip_rel_gap": 0.0, "mip_abs_gap": 0.0, "time_limit": 90.0})
    result = solver.solve(model, load_solutions=False)
    if result.solver.termination_condition == pyo.TerminationCondition.optimal:
        model.solutions.load_from(result)
        return True
    assert result.solver.termination_condition == pyo.TerminationCondition.infeasible
    return False


def test_formulation_f0_routing_windows_gdp_neck_and_flow():
    model = _f0_instance()
    assert _solve_f0(model)
    assert pyo.value(model.w["fixed", "WIFI", 1]) == 1
    assert pyo.value(model.D["fixed", "WIFI", 1]) == 1300
    assert pyo.value(sum(model.K.values())) == 48
    assert pyo.value(model.Phi_shape) == 1
    assert pyo.value(model.Phi_balance) == 48
    assert not _solve_f0(_f0_instance(forbidden=[{"z00", "z01"}]))
    broken = _f0_instance()
    # Swap equal-$500M vertices: all windows still hold, but district 1 detaches.
    for z, j in (("z03", 2), ("z05", 1)):
        for k in broken.J:
            broken.x["fixed", "WH", k, z].fix(int(k == j))
    assert not _solve_f0(broken)
    capped = _f0_instance()
    capped.w["fixed", "WIFI", 1].fix(0)
    assert not _solve_f0(capped)
    assert not _solve_f0(_f0_instance(split_wifi=True))
    # Isolate the cause: an intentionally invalid relaxation deleting only GDP's
    # owns-touched-state rows passes coverage, flow, counts and windows.
    relaxed_cap = _f0_instance(split_wifi=True)
    for d in relaxed_cap.whole.values():
        d.owns_touched_state.deactivate()
    assert _solve_f0(relaxed_cap)
    # Likewise, the equal-mass exchange fails connectivity alone.
    broken.flow_balance.deactivate()
    assert _solve_f0(broken)


def test_formulation_f0_manhattan_components_60():
    """Owner #140 exception over production's component decomposition, not a raw-gate pass."""
    from td.audit import _components

    Z = [f"z{i:02d}" for i in range(60)]
    own = {z: max(1, i - 11) for i, z in enumerate(Z)}
    X = {z for z in Z if own[z] == 1}  # 13 ZCTAs; the other 47 districts are singletons.
    cases = [
        ((), (), True),                         # original single-root domain
        ((), ("z00",), True),                   # connected Manhattan district
        ((5,), (), False),                      # no Manhattan in either component
        ((5,), ("z00",), True),                 # permitted detached Manhattan piece
        ((5,), ("z59",), False),                # Manhattan owned by another district
        ((2, 5), ("z00",), False),              # two extra pieces, only one Manhattan
        ((2, 5), ("z00", "z03"), False),       # even two Manhattan roots cannot be used
    ]
    for cuts, manhattan, expected in cases:
        edges = [(a, b) for i, (a, b) in enumerate(zip(Z, Z[1:])) if i not in cuts]
        graph = nx.Graph()
        graph.add_nodes_from(Z)
        graph.add_edges_from(edges)
        # Production has no exception path. Test its raw components against an
        # independent graph implementation, then explicitly apply the owner rule.
        parts = _components(X, {z: set(graph[z]) for z in Z})
        assert {frozenset(p) for p in parts} == {
            frozenset(p) for p in nx.connected_components(graph.subgraph(X))}
        accepted = len(parts) == 1 or (len(parts) == 2 and
                    any(set(p) & set(manhattan) for p in parts))
        assert accepted == expected
        def build(*, dollars=1000, forbidden=()):
            model = f0.build_model(Z=Z, F=["fine"], rho={(z, "fine"): "WH" for z in Z},
                m={(z, "fine"): dollars / len(X) if z in X else 1000 for z in Z},
                rates={"fine": 1}, state=dict.fromkeys(Z, "NY"), E_P=edges,
                manhattan=manhattan, forbidden={"WH": forbidden},
                shape=lambda t: sum(t.y.values()), balance=lambda t: sum(t.y.values()))
            for h, c, j, z in model.x:
                model.x[h, c, j, z].fix(int(j == own[z]))
            for h, c, j in model.y:
                model.y[h, c, j].fix(int(j <= 48))
            return model

        model = build()
        assert _solve_f0(model) == expected, (cuts, manhattan)
        if expected:
            assert pyo.value(model.Phi_shape) == 48
            assert abs(pyo.value(model.D["fixed", "WH", 1]) - 1000) < 1e-8
            # Manhattan never exempts a nonexempt neck or a dollar-window failure.
            assert not _solve_f0(build(forbidden=[X]))
            assert not _solve_f0(build(dollars=1200))
    print("  FORMULATION F0: 60 ZCTAs; ordinary/Manhattan flow matches 7 component verdicts")


def test_formulation_f0_authoritative_source():
    root = Path(__file__).resolve().parents[1]
    doc = (root / "docs/MODEL.md").read_text()
    section = doc.split("## 0. F0 — national reference program", 1)[1].split("## 1.", 1)[0]
    assert "[F0.tex](F0.tex)" in section and "[F0.pdf](F0.pdf)" in section
    assert "$$" not in section and "### 0." not in section
    assert "docs/F0.tex" in f0.__doc__
    tex = (root / "docs/F0.tex").read_text()
    assert r"\label{eq:flow}" in tex and r"\label{eq:neck}" in tex
    assert (root / "docs/F0.pdf").read_bytes().startswith(b"%PDF-")


def test_formulation_multiple_bodies_and_pruning_30():
    G = nx.path_graph([f"p{i:02d}" for i in range(30)])
    pos = {z: (float(i), 0.0) for i, z in enumerate(G)}
    known = {z: "A" if i <= 15 else "B" for i, z in enumerate(G)}
    call, centres, good = _call(G, pos, dict.fromkeys(G, 1.0),
        fixed={"p00": "A", "p15": "A", "p29": "B"}, known=known)
    data = f4.prepare(call, centres=centres)
    assert len(data.B["A"]) == 2
    assert sum(map(len, data.A_z.values())) < sum(map(len, call["allowed"].values()))
    _conformance("path-multiple-bodies-pruning", (call, centres, good))


def test_formulation_separators_reject_locally_valid_disconnected_point():
    call, centres, good = _grid(6, 6)
    bad = {**good, "z00_04": "B", "z00_05": "B", "z05_04": "A", "z05_05": "A"}
    data = f4.prepare(call, centres=centres)
    base = f4.build_model(data, connectivity=False)
    assert _solve(base, bad)[0] == "optimal"  # band, holders and neighbor rows hold
    sep = f142.build_model(data)
    assert _solve(sep, bad)[0] == "infeasible"
    assert len(sep.separator) >= 2
    assert _solve(f4.build_model(data), bad)[0] == "infeasible"
    result = _production(call, centres, bad)
    assert result.status == "infeasible" and result.cuts > 0


def _bnc_rootless_path(extra, sequential):
    """`test_formulation_rootless_empty_extra_and_sequential_domain`'s group as a bnc instance: a 30-ZCTA
    path of mass 1, districts A and B with no body, band [30, 35], B holding `extra` outside the group."""
    return synth.grid("rootless-path", w=30, h=1, bodies={}, rootless=("A", "B"), band=(30.0, 35.0),
                      extra={"B": extra}, sequential=sequential, heavy={(0, c): 1.0 for c in range(30)})


def test_formulation_rootless_empty_extra_and_sequential_domain():
    # F142 separators (and draw) allow an empty rootless district if `extra`
    # already meets its band. bnc verify.py's unconditional sum r=1 does not.
    G = nx.path_graph([f"p{i:02d}" for i in range(30)])
    pos = {z: (float(i), 0.0) for i, z in enumerate(G)}
    known = {z: "A" if i < 15 else "B" for i, z in enumerate(G)}
    call, centres, _ = _call(G, pos, dict.fromkeys(G, 1.0), fixed={}, known=known)
    call.update(lo=30.0, hi=35.0, extra={"B": 35.0})
    point = dict.fromkeys(G, "A")
    for sequential in (False, True):
        call.update(sequential=sequential, extra={"B": 40.0 if sequential else 35.0})
        data = f4.prepare(call, centres=centres)
        actual = _production(call, centres, point)
        assert actual.status == "optimal"
        for build in (f4.build_model, f142.build_model):
            verdict, value = _solve(build(data), point)
            assert verdict == "optimal" and abs(value - actual.objective) < 2e-6
        # The same group as a bnc instance (30 ZCTAs on a path, both districts rootless, B's `extra` as above):
        # draw.py's complete model, run through bnc's arm a, takes the empty B; the production flow verifier
        # (`verify.flow_model`, `verify.run`) roots every rootless district and so cannot.
        inst = _bnc_rootless_path(extra=call["extra"]["B"], sequential=sequential)
        arm = bnc_arms.solve("a", inst, 60.0, None, lambda *_: None)
        assert arm["status"] == "optimal" and set(arm["owner"].values()) == {"A"}, arm
        model, xs = bnc_verify.flow_model(inst)
        for (z, j), i in inst.xcol.items():
            value = float(j == "A")                       # the point: every ZCTA to A, as above
            model.chgVarLb(xs[i], value)
            model.chgVarUb(xs[i], value)
        model.optimize()
        assert model.getStatus() == "infeasible"
        assert bnc_verify.run(inst, 60.0, lambda *_: None)["scip_status"] == "infeasible"
    call["sequential"] = False
    assert _production(call, centres, point).status == "infeasible"
    assert _solve(f4.build_model(f4.prepare(call, centres=centres)), point)[0] == "infeasible"
