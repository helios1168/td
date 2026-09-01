"""
test_descaled.py -- the descaled real-instance export and its loader.

Round-trips a synthetic "confidential" instance through tools/instance_export and back via
battery/code/descaled.py, and pins the property the whole route rests on: the loaded graph
is the real instance divided by one constant, so at rho = 0 it has the same optimum.
"""
from __future__ import annotations

import csv
import importlib.util
import math
import os
import sys
import tempfile

import networkx as nx
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


from td import instance as descaled                              # noqa: E402
from td import model              # noqa: E402

THETA, LAM = 0.40, 0.30
KAPPA = 91_000.0                             # the "dollar" scale the export must strip


def _exporter():
    path = os.path.join(ROOT, "tools", "instance_export", "export_instance.py")
    spec = importlib.util.spec_from_file_location("export_instance", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ a fake "real" instance
def fake_real(n=12, seed=3):
    """A path of ZCTAs with per-(zip, rep) dollar sales: contested, uncontested, untapped."""
    rng = np.random.default_rng(seed)
    zips = [f"{10000 + 7 * i:05d}" for i in range(n)]
    reps = ["alice@x", "bob@x", "carol@x"]
    M, sales = {}, []
    for i, z in enumerate(zips):
        M[z] = KAPPA * float(rng.uniform(0.4, 2.5))
        if i % 5 == 4:
            continue                                   # untapped: opportunity, no book
        k = 1 if i % 4 == 3 else (3 if i % 3 == 0 else 2)
        for rep in reps[:k]:
            sales.append((z, rep, "F_A" if rep != "carol@x" else "F_B",
                          M[z] * float(rng.uniform(0.02, 0.12))))
    edges = [(zips[i], zips[i + 1]) for i in range(n - 1)]
    return zips, reps, M, sales, edges


def _write_inputs(tmp, zips, M, sales, edges):
    sp = os.path.join(tmp, "sales.csv")
    with open(sp, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["zip_code", "rep_id", "firm", "sales"])
        w.writerows(sales)
    op = os.path.join(tmp, "opp.csv")
    with open(op, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["zip_code", "M"])
        w.writerows([(z, M[z]) for z in zips])
    gp = os.path.join(tmp, "edges.csv")
    with open(gp, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["u", "v"]); w.writerows(edges)
    return sp, op, gp


def _round_trip(tmp):
    ex = _exporter()
    zips, reps, M, sales, edges = fake_real()
    sp, op, gp = _write_inputs(tmp, zips, M, sales, edges)
    rc = ex.main(["export", "--sales", sp, "--opportunity", op, "--graph", gp,
                  "--out", tmp, "--yes"])
    assert rc == 0, f"exporter returned {rc}"
    d = descaled.load_descaled(os.path.join(tmp, "instance_descaled.json.gz"))
    return ex, d, (zips, reps, M, sales, edges)


# ------------------------------------------------------------------------------ tests
def test_round_trip_and_classes():
    with tempfile.TemporaryDirectory() as tmp:
        _, d, (zips, reps, M, sales, edges) = _round_trip(tmp)
        assert d.G.number_of_nodes() == len(zips)
        assert d.G.number_of_edges() == len(edges)
        assert len(d.contested) + len(d.uncontested) + len(d.untapped) == len(zips)
        assert d.untapped, "fixture should produce untapped zips"
        assert d.uncontested, "fixture should produce uncontested zips"
        assert d.contested, "fixture should produce contested zips"
        for z in d.contested:
            assert len(d.G.nodes[z]["cand"]) >= 2
        for z, owner in d.uncontested.items():
            assert d.G.nodes[z]["cand"] == (owner,)
        for z in d.untapped:
            assert d.G.nodes[z]["cand"] == ()


def test_no_real_identifier_or_dollar_leaves():
    """Rep ids are surrogates and no emitted magnitude is a currency amount."""
    import gzip, json
    with tempfile.TemporaryDirectory() as tmp:
        _, d, (zips, reps, M, sales, edges) = _round_trip(tmp)
        blob = gzip.open(os.path.join(tmp, "instance_descaled.json.gz"), "rt").read()
        for rep in reps:
            assert rep not in blob, f"{rep} leaked into the export"
        assert "@" not in blob
        obj = json.loads(blob)
        for row in obj["nodes"]["share"]:
            for s in row.values():
                assert 0.0 <= s <= 1.0
        ms = obj["nodes"]["m_rel"]
        assert max(ms) < 1e4 and 0.5 <= sorted(ms)[len(ms) // 2] <= 2.0
        assert "kappa" not in blob


def test_descaling_is_division_by_one_constant():
    """S_i and M come back as the real values over one common divisor.

    Exact up to the exporter's 6-significant-figure rounding: `share` and `m_rel` are each
    rounded before writing and the loader multiplies them, so the recovered ratio carries
    about two roundings' worth of relative error (~1e-6).  Far below anything the model
    resolves -- CERT_TOL is 1e-8 on log-objective *nats*, and the data is far noisier -- but
    it is a bound, not zero, so the test states the bound it actually has.
    """
    with tempfile.TemporaryDirectory() as tmp:
        _, d, (zips, reps, M, sales, edges) = _round_trip(tmp)
        real_S = {}
        for z, rep, _firm, v in sales:
            real_S.setdefault(z, {})[rep] = real_S.setdefault(z, {}).get(rep, 0.0) + v
        ratios = []
        for z in d.G:
            ratios.append(d.G.nodes[z]["M"] / M[z])
            got = sorted(d.G.nodes[z]["S"].values())
            want = sorted(real_S.get(z, {}).values())
            assert len(got) == len(want)
            for a, b in zip(got, want):
                if b > 0:
                    ratios.append(a / b)
        assert ratios
        spread = (max(ratios) - min(ratios)) / max(ratios)
        assert spread < 1e-5, f"not a single common divisor (relative spread {spread:.2e})"


def test_objective_is_scale_invariant_at_rho_zero():
    """The property the whole route rests on: descaling cannot move the argmax at rho=0."""
    with tempfile.TemporaryDirectory() as tmp:
        _, d, _ = _round_trip(tmp)
        nodes = d.contested
        if len(nodes) < 2:
            return
        U, R = model.utilities(d.G, nodes, theta=THETA, lam=LAM)
        H = d.G.copy()                                   # a 10x-rescaled copy of the same graph
        for z in H:
            H.nodes[z]["M"] *= 10.0
            H.nodes[z]["S"] = {r: v * 10.0 for r, v in H.nodes[z]["S"].items()}
        U10, R10 = model.utilities(H, nodes, theta=THETA, lam=LAM)
        assert R == R10
        rng = np.random.default_rng(0)
        best, best10 = None, None
        for _ in range(60):
            alloc = {z: d.G.nodes[z]["cand"][rng.integers(len(d.G.nodes[z]["cand"]))]
                     for z in nodes}
            oi = model.owner_index(nodes, alloc, R)
            o1 = model.objective(U, oi)
            o2 = model.objective(U10, oi)
            if not math.isfinite(o1):
                assert not math.isfinite(o2)
                continue
            # every objective shifts by exactly n*log(10)
            assert math.isclose(o2 - o1, len(R) * math.log(10.0), abs_tol=1e-9)
            if best is None or o1 > best[0]:
                best, best10 = (o1, tuple(oi)), (o2, tuple(oi))
        assert best is not None and best[1] == best10[1], "argmax moved under rescaling"


def test_check_descaled_clean_and_dirty():
    with tempfile.TemporaryDirectory() as tmp:
        _, d, _ = _round_trip(tmp)
        assert descaled.check_descaled(d, theta=THETA) == []
        z = d.contested[0]
        d.G.nodes[z]["M"] = 1e-9                          # book now exceeds opportunity
        assert any("headroom" in s for s in descaled.check_descaled(d, theta=THETA))


def test_validate_rejects_headroom_violation():
    """The exporter refuses to write when sales exceed what opportunity can contain."""
    ex = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        zips, reps, M, sales, edges = fake_real()
        sales = list(sales)
        z0 = sales[0][0]
        sales.append((z0, "greedy@x", "F_A", M[z0] * 5.0))       # share > 1
        sp, op, gp = _write_inputs(tmp, zips, M, sales, edges)
        rc = ex.main(["export", "--sales", sp, "--opportunity", op, "--graph", gp,
                      "--out", tmp, "--yes"])
        assert rc == 3, rc
        assert not os.path.exists(os.path.join(tmp, "instance_descaled.json.gz"))


def test_join_floor_fires_on_id_mismatch():
    """A leading-zero / vintage mismatch must hard-fail rather than silently drop rows."""
    ex = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        zips, reps, M, sales, edges = fake_real()
        bad = [(f"9{z}", rep, firm, v) for z, rep, firm, v in sales]   # 6-char ids
        sp, op, gp = _write_inputs(tmp, zips, M, bad, edges)
        rc = ex.main(["validate", "--sales", sp, "--opportunity", op, "--graph", gp])
        assert rc == 4, rc


def test_untapped_zips_are_kept_for_adjacency():
    """Dropping them would change connectivity -- regime (d) glue."""
    with tempfile.TemporaryDirectory() as tmp:
        _, d, _ = _round_trip(tmp)
        assert d.untapped
        assert all(z in d.G for z in d.untapped)
        n_before = d.G.number_of_nodes()
        d2 = descaled.load_descaled(os.path.join(tmp, "instance_descaled.json.gz"),
                                    keep_untapped=False)
        assert d2.G.number_of_nodes() == n_before - len(d.untapped)


def test_nway_primitives_accept_the_loaded_graph():
    """The loader's output is directly consumable by the N-way primitives."""
    with tempfile.TemporaryDirectory() as tmp:
        _, d, _ = _round_trip(tmp)
        nodes = d.contested
        U, R = model.utilities(d.G, nodes, theta=THETA, lam=LAM)
        assert U.shape == (len(R), len(nodes))
        C = model.candidate_matrix(d.G, nodes, R)
        assert (U[~C] == 0).all()
        alloc = {z: d.G.nodes[z]["cand"][0] for z in nodes}
        assert isinstance(model.pieces(d.G, nodes, alloc)["excess_pieces"], int)


def test_summary_and_meta():
    with tempfile.TemporaryDirectory() as tmp:
        _, d, _ = _round_trip(tmp)
        assert "contested" in d.summary()
        assert d.meta.get("graph_hash")
        assert d.meta.get("scale_stripped") is True
        assert set(d.firm) == set(d.reps) | set(d.firm)      # firms keyed by surrogate ids
        assert all(r.startswith("R") for r in d.reps)


# ------------------------------------------------------------- vacancy filler keys
FILLER = "VACANT_TERRITORY"


def fake_real_with_filler(n=12, seed=5):
    """As `fake_real`, plus zips whose only book sits under a vacancy filler key."""
    zips, reps, M, sales, edges = fake_real(n, seed)
    sales = list(sales)
    vacant_zips = [z for i, z in enumerate(zips) if i % 5 == 4]     # the untapped ones
    for z in vacant_zips:
        sales.append((z, FILLER, "F_A", M[z] * 0.05))               # now vacant, not untapped
    sales.append((zips[0], FILLER, "F_A", M[zips[0]] * 0.03))       # filler beside real reps
    return zips, reps, M, sales, edges, vacant_zips


def _round_trip_filler(tmp):
    ex = _exporter()
    zips, reps, M, sales, edges, vacant_zips = fake_real_with_filler()
    sp, op, gp = _write_inputs(tmp, zips, M, sales, edges)
    rc = ex.main(["export", "--sales", sp, "--opportunity", op, "--graph", gp,
                  "--filler-key", FILLER, "--out", tmp, "--yes"])
    assert rc == 0, f"exporter returned {rc}"
    d = descaled.load_descaled(os.path.join(tmp, "instance_descaled.json.gz"))
    return d, vacant_zips


def test_filler_never_becomes_a_candidate():
    """The vacancy key must not appear as a rep -- an objective term for an empty chair."""
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = _round_trip_filler(tmp)
        assert FILLER not in d.reps
        assert FILLER not in d.firm
        for z in d.G:
            assert FILLER not in d.G.nodes[z]["cand"]
            assert FILLER not in d.G.nodes[z]["S"]
        import gzip
        assert FILLER not in gzip.open(
            os.path.join(tmp, "instance_descaled.json.gz"), "rt").read()


def test_filler_only_zips_become_vacant_not_untapped():
    """Sales under a filler key make a zip vacant: real book, no incumbent, no candidate."""
    with tempfile.TemporaryDirectory() as tmp:
        d, vacant_zips = _round_trip_filler(tmp)
        assert set(d.vacant) == set(vacant_zips), (d.vacant, vacant_zips)
        assert not d.untapped, "these zips have sales, so nothing should be untapped now"
        for z in d.vacant:
            assert d.G.nodes[z]["cand"] == ()
            assert d.G.nodes[z]["S_free"] > 0
        assert set(d.undecided) == set(d.vacant)


def test_filler_book_reaches_candidates_as_free_book():
    """Where a filler sits beside real reps, its book raises their utility via S_free."""
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = _round_trip_filler(tmp)
        withfree = [z for z in d.contested if d.G.nodes[z]["S_free"] > 0]
        assert withfree, "fixture should put filler book on a contested zip"
        nodes = d.contested
        U, R = model.utilities(d.G, nodes, theta=THETA, lam=LAM)
        H = d.G.copy()
        for z in H:
            H.nodes[z]["S_free"] = 0.0
        U0, _ = model.utilities(H, nodes, reps_order=R, theta=THETA, lam=LAM)
        j = nodes.index(withfree[0])
        assert (U[:, j] >= U0[:, j]).all() and (U[:, j] > U0[:, j]).any()


def test_check_descaled_accepts_a_filler_instance():
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = _round_trip_filler(tmp)
        assert descaled.check_descaled(d, theta=THETA) == []


def test_footprint_report_components_and_ceiling():
    """The exporter's footprint section: components in shares, ceiling == td.channel's."""
    from td import channel
    ex = _exporter()

    # two path components with known opportunity, plus a crumb far below CRUMB_SHARE
    inst = ex.Instance()
    west = [f"9{i:04d}" for i in range(4)]           # m_rel 10 each -> share ~0.615
    east = [f"1{i:04d}" for i in range(3)]           # m_rel  8 each -> share ~0.369
    crumb = ["50000"]                                # m_rel  1      -> share ~0.015? keep < 1%
    for z in west:
        inst.m_rel[z] = 10.0
        inst.state[z] = "CA"
    for z in east:
        inst.m_rel[z] = 8.0
        inst.state[z] = "NY"
    inst.m_rel[crumb[0]] = 0.5                       # 0.5/64.5 ~ 0.8% < CRUMB_SHARE
    inst.edges = ([(west[i], west[i + 1]) for i in range(3)] +
                  [(east[i], east[i + 1]) for i in range(2)])

    comps = ex.components(inst)
    assert [set(c) for c in comps] == [set(west), set(east), set(crumb)]

    total = sum(inst.m_rel.values())
    shares = [40.0 / total, 24.0 / total]            # crumb excluded by the report
    for k in range(2, 8):
        mine = ex.alloc_ceiling(shares, k)
        ref = channel.allocate_districts({"W": 40.0, "E": 24.0}, k=k)
        assert ref["feasible"]
        assert mine["alloc"] == [ref["districts_per_component"]["W"],
                                 ref["districts_per_component"]["E"]]
        assert math.isclose(mine["spread"], ref["ceiling_spread_rel"], rel_tol=1e-12)
        assert math.isclose(mine["min_spread"], ref["min_spread_rel"], rel_tol=1e-12)
    assert ex.alloc_ceiling(shares, 1) is None       # k < number of components

    txt = ex.footprint_text(inst)
    assert "62.0%" in txt and "37.2%" in txt         # 40/64.5, 24/64.5
    assert "CA" in txt and "NY" in txt
    assert "crumb" in txt
    for tok in ("$", "40.0", "24.0"):                # shares only, no raw magnitudes
        assert tok not in txt


def test_build_adjacency_rook_rule_and_states():
    """build_adjacency: corner-touch pairs excluded, island disconnects, states by point."""
    import geopandas as gpd
    from shapely.geometry import box

    path = os.path.join(ROOT, "tools", "instance_export", "build_adjacency.py")
    spec = importlib.util.spec_from_file_location("build_adjacency", path)
    ba = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ba)

    # 2x2 grid (diagonals touch only at a corner point) plus a far island
    cells = {"10001": (0, 0), "10002": (1, 0), "10003": (0, 1), "10004": (1, 1),
             "99999": (5, 5)}
    gdf = gpd.GeoDataFrame(
        {"ZCTA5CE20": list(cells),
         "INTPTLAT20": [y + 0.5 for _, y in cells.values()],
         "INTPTLON20": [x + 0.5 for x, _ in cells.values()]},
        geometry=[box(x, y, x + 1, y + 1) for x, y in cells.values()], crs="EPSG:4269")

    edges = ba.rook_edges(gdf, "ZCTA5CE20", verbose=False)
    assert edges == [("10001", "10002"), ("10001", "10003"),
                     ("10002", "10004"), ("10003", "10004")], \
        "rook must drop the corner-touch diagonals and the island"
    assert ba.n_components(list(cells), edges) == 2

    with tempfile.TemporaryDirectory() as tmp:
        sp = os.path.join(tmp, "states.geojson")
        gpd.GeoDataFrame({"STUSPS": ["CA", "NY"]},
                         geometry=[box(-1, -1, 1, 3), box(1, -1, 7, 7)],
                         crs="EPSG:4269").to_file(sp, driver="GeoJSON")
        st = ba.state_membership(gdf, "ZCTA5CE20", sp, verbose=False)
    assert st == {"10001": "CA", "10002": "NY", "10003": "CA",
                  "10004": "NY", "99999": "NY"}
