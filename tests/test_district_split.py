"""
test_district_split.py -- the within-district split engine and its driver.

No network and no real instance: the graph is a hand-built `td.instance.Descaled` over a few
fake CONUS zips (the `tests/test_ziptable.py` pattern), and the driver test writes a synthetic
instance file in the export format plus a zip table into a temp directory.

The oracle is brute force: 3^8 labellings of 8 zips over 3 reps, enumerated exhaustively.  It
bounds the greedy answer from above and, when pyscipopt is importable, must equal `exact`'s
objective to 1e-6.  Without pyscipopt the SCIP tests print a note and pass -- SCIP is in the
solver venv but a caller reading this file elsewhere should not see a hard failure.
"""
from __future__ import annotations

import gzip
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import instance as descaled, ziptable                               # noqa: E402
from td.solvers import district_split as ds                                 # noqa: E402


def _have_scip() -> bool:
    try:
        import pyscipopt                                                    # noqa: F401
    except Exception:
        print("      (pyscipopt not importable -- SCIP assertions skipped)")
        return False
    return True


def _brute(u: np.ndarray):
    """`(best_objective, best_labels)` over every labelling of the columns of `u`."""
    n_reps, n = u.shape
    best_v, best_l = -math.inf, None
    for combo in itertools.product(range(n_reps), repeat=n):
        labels = np.array(combo, int)
        v = ds.objective(u, labels)
        if v > best_v:
            best_v, best_l = v, labels
    return best_v, best_l


def _toy_u(seed: int = 7, n_reps: int = 3, n: int = 8) -> np.ndarray:
    """A reproducible utility matrix with no exact ties, so the optimum is unique."""
    rng = np.random.default_rng(seed)
    return np.round(1.0 + 9.0 * rng.random((n_reps, n)), 4)


def _toy_xy(n: int = 8) -> np.ndarray:
    return np.array([[float(j), float((j * j) % 5)] for j in range(n)], float)


# ------------------------------------------------------------------ (a) SCIP == brute force
def test_exact_matches_brute_force():
    u = _toy_u()
    best_v, _ = _brute(u)
    if not _have_scip():
        return
    warm = ds.greedy(u, np.ones(u.shape[1]), _toy_xy(), n_near=3)
    labels, value, gap, status = ds.exact(u, warm, time_limit=30.0)
    assert status == "optimal", status
    assert gap <= 1e-9, gap
    assert abs(value - best_v) <= 1e-6, (value, best_v)
    assert abs(ds.objective(u, labels) - best_v) <= 1e-6


# ------------------------------------------------------------------ (b) greedy is bounded
def test_greedy_bounded_by_brute_force_and_never_empties():
    for seed in (1, 2, 3, 7, 11):
        u = _toy_u(seed)
        best_v, _ = _brute(u)
        labels = ds.greedy(u, np.ones(u.shape[1]), _toy_xy(), n_near=3)
        v = ds.objective(u, labels)
        assert v <= best_v + 1e-9, (seed, v, best_v)
        assert set(labels.tolist()) == {0, 1, 2}, (seed, labels)
        assert (ds.gains(u, labels) > 0).all()


def test_greedy_beats_its_own_seed():
    """The passes may only improve: the answer is never worse than `argmax_i u`."""
    for seed in (1, 2, 3, 7, 11):
        u = _toy_u(seed)
        start = ds.seed_labels(u)
        labels = ds.greedy(u, np.ones(u.shape[1]), _toy_xy(), n_near=3)
        assert ds.objective(u, labels) >= ds.objective(u, start) - 1e-12


# ------------------------------------------------------------------ (c) the geographic split
def test_two_reps_with_separated_books_split_geographically():
    """Twelve zips on a line: rep 0's book on 0-3, rep 1's on 8-11, nobody's on the four between.

    On the middle four the two reps' utilities are identical, so the Nash objective alone is
    indifferent about which of them moves across.  Only the `M_z d^2` tie-break decides, and it
    has to hand rep 1 the middle zips *nearest to it* -- 7 then 6 -- for the answer to be two
    contiguous halves rather than an interleaving.
    """
    n = 12
    xy = np.array([[float(j), 0.0] for j in range(n)], float)
    M = np.ones(n)
    u = np.full((2, n), 1.0)
    u[0, :4] += 0.5
    u[1, 8:] += 0.5
    book = np.zeros((2, n), bool)
    book[0, :4] = True
    book[1, 8:] = True

    labels = ds.greedy(u, M, xy, n_near=2, centers0=ds.rep_centers(u, xy, book, M))
    assert labels.tolist() == [0] * 6 + [1] * 6, labels.tolist()


def test_unpositioned_zips_are_assigned_by_utility_only():
    """A zip with no coordinates still moves for a Nash gain; it just carries no distance."""
    u = _toy_u(5)
    xy = _toy_xy()
    xy[3] = np.nan
    labels = ds.greedy(u, np.ones(u.shape[1]), xy, n_near=1)
    assert (ds.gains(u, labels) > 0).all()
    assert set(labels.tolist()) == {0, 1, 2}


# ------------------------------------------------------------------ (e) a starved rep
def test_rep_with_no_positive_utility_is_dropped():
    u = _toy_u(3)
    u = np.vstack([u, np.zeros(u.shape[1])])
    res = ds.split(u, np.ones(u.shape[1]), _toy_xy(), ["R1", "R2", "R3", "R4"])
    assert res["dropped_reps"] == ["R4"]
    assert res["reps"] == ["R1", "R2", "R3"]
    assert set(res["gains"]) == {"R1", "R2", "R3"}
    assert math.isfinite(res["objective"])
    assert set(res["labels"]) <= {"R1", "R2", "R3"}


def test_split_reports_method_and_moves():
    u = _toy_u(9)
    res = ds.split(u, np.ones(u.shape[1]), _toy_xy(), ["R1", "R2", "R3"])
    assert res["method"] == "greedy" and res["status"] == "heuristic" and res["gap"] is None
    assert 0 <= res["moves"] <= u.shape[1]
    assert len(res["labels"]) == u.shape[1]
    assert abs(res["objective"] - sum(math.log(g) for g in res["gains"].values())) < 1e-12


def test_split_exact_is_at_least_as_good_as_greedy():
    if not _have_scip():
        return
    u = _toy_u(4)
    greedy = ds.split(u, np.ones(u.shape[1]), _toy_xy(), ["R1", "R2", "R3"])
    exact = ds.split(u, np.ones(u.shape[1]), _toy_xy(), ["R1", "R2", "R3"],
                     use_exact=True, time_limit=30.0)
    best_v, _ = _brute(u)
    assert exact["objective"] >= greedy["objective"] - 1e-12
    assert abs(exact["objective"] - best_v) <= 1e-6
    assert exact["method"] == "scip" and exact["status"] == "optimal"


# ------------------------------------------------------------------ utilities from the model
def _graph(books: dict, masses: dict, states: dict, free: dict | None = None):
    G = nx.Graph()
    for z, m in masses.items():
        S = dict(books.get(z, {}))
        G.add_node(z, cand=tuple(sorted(S)), S=S, M=float(m),
                   S_free=float((free or {}).get(z, 0.0)), state=states[z])
    return G


def test_unrestricted_utilities_match_the_gain_matrix_coefficients():
    """A rep with no book on a zip still values it: candidacy is ignored, as in staffing."""
    from td import channel

    masses = {"10001": 5.0, "10002": 3.0}
    books = {"10001": {"R1": 1.0}, "10002": {"R2": 2.0}}
    G = _graph(books, masses, {"10001": "NY", "10002": "NY"}, free={"10001": 0.5})
    zips = ["10001", "10002"]
    u = ds.unrestricted_utilities(G, zips, ["R1", "R2"], masses,
                                  theta=0.4, lam=0.3, filler_capture="full")
    assert (u > 0).all()                                   # R2 values 10001 though it has no book
    g, R, D = channel.gain_matrix(G, {z: "D01" for z in zips}, reps_order=["R1", "R2"],
                                  districts=["D01"], theta=0.4, lam=0.3, filler_capture="full")
    assert np.allclose(u.sum(axis=1), g[:, 0])             # same coefficients, same total


def test_book_matrix_is_the_footprint():
    masses = {"10001": 5.0, "10002": 3.0}
    books = {"10001": {"R1": 1.0}, "10002": {"R2": 2.0}}
    G = _graph(books, masses, {"10001": "NY", "10002": "NY"})
    B = ds.book_matrix(G, ["10001", "10002"], ["R1", "R2"])
    assert B.tolist() == [[True, False], [False, True]]


# ------------------------------------------------------------------ (d) the driver end to end
def _write_instance(path: str, masses: dict, states: dict, books: dict) -> None:
    """The `td_instance_descaled/1` export format: shares and a relative opportunity."""
    zips = sorted(masses)
    obj = dict(
        format=descaled.FORMAT,
        nodes=dict(
            z=zips,
            m_rel=[masses[z] for z in zips],
            share=[{r: s / masses[z] for r, s in books.get(z, {}).items()} for z in zips],
            state=[states[z] for z in zips],
            share_free=[0.0] * len(zips),
        ),
        edges=dict(u=[], v=[]),
        firm={},
        meta={},
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _driver_case(tmp: str, n_in: int = 10, n_out: int = 4):
    """A two-district table: `n_in` zips in D01 to be split, `n_out` in D02 to be left alone."""
    masses, states, books, xy, labels = {}, {}, {}, {}, {}
    for j in range(n_in):
        z = f"1{j:04d}"
        masses[z] = 1.0 + 0.1 * j
        states[z] = "NY"
        books[z] = {"R1": 0.4} if j < n_in // 2 else {"R2": 0.4}
        xy[z] = (float(j) * 1000.0, 0.0)
        labels[z] = "D01"
    for j in range(n_out):
        z = f"2{j:04d}"
        masses[z] = 2.0
        states[z] = "TX"
        books[z] = {"R3": 0.5}
        xy[z] = (0.0, float(j) * 1000.0)
        labels[z] = "D02"

    inst = os.path.join(tmp, "inst.json.gz")
    _write_instance(inst, masses, states, books)
    d = descaled.load_descaled(inst)
    table = os.path.join(tmp, "in", "draw.csv")
    ziptable.write(table, ziptable.build(d, xy, labels))
    return inst, table, labels


def test_driver_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        inst, table, labels = _driver_case(tmp)
        out = os.path.join(tmp, "out")
        rc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "split_district.py"), inst,
             "--table", table, "--district", "D01", "--reps", "R1,R2", "--out", out],
            capture_output=True, text=True)
        assert rc.returncode == 0, rc.stdout + rc.stderr
        assert os.path.exists(os.path.join(out, "timings.json"))

        rows = ziptable.read(os.path.join(out, "draw.csv"))
        assert len(rows) == len(labels)
        for r in rows:
            assert r["district"] == labels[r["zip"]]            # district untouched
            if r["district"] == "D01":
                assert r["rep"] in ("R1", "R2"), r
            else:
                assert r["rep"] == "", r                        # reps only inside the district

        with open(os.path.join(out, "split.json"), encoding="utf-8") as fh:
            rep = json.load(fh)
        assert rep["district"] == "D01" and rep["reps"] == ["R1", "R2"]
        assert rep["n_zips"] == sum(1 for v in labels.values() if v == "D01")
        assert rep["method"] == "greedy" and rep["dropped_reps"] == []
        assert abs(sum(rep["shares"].values()) - 1.0) < 1e-9
        assert all(g > 0 for g in rep["gains"].values())
        assert abs(rep["objective"] - sum(math.log(g) for g in rep["gains"].values())) < 1e-9
        assert rep["seconds"] >= 0.0

        # the books are cleanly separated left/right, so the split is the two halves
        by_zip = {r["zip"]: r["rep"] for r in rows if r["district"] == "D01"}
        assert sorted(by_zip)[:5] == [z for z in sorted(by_zip) if by_zip[z] == "R1"]


def test_driver_fails_on_an_unknown_district():
    with tempfile.TemporaryDirectory() as tmp:
        inst, table, _ = _driver_case(tmp)
        out = os.path.join(tmp, "out")
        rc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "split_district.py"), inst,
             "--table", table, "--district", "D99", "--reps", "R1,R2", "--out", out],
            capture_output=True, text=True)
        assert rc.returncode != 0
        with open(os.path.join(out, "failure.json"), encoding="utf-8") as fh:
            assert "D99" in json.load(fh)["reason"]
