"""
test_measure.py -- the premium ladder (tools/measure/premium.py, unit U7-meas).

Synthetic only: no instance file, no network.  The load-bearing test is `test_toy_ladder`, the
worked example of `docs/MODEL_U7-meas.md` §4, which pins every rung of
`P0 <= P*(A) <= P_S <= P13 <= P_free` at once and, with it, the decomposition
`g = B_j + w * b` the whole unit rests on.  `test_seeded_*` check the two solved rungs against
brute force on a fixture at ~40% saturation, the measured saturation of the real instance.
"""
from __future__ import annotations

import gzip
import importlib.util
import itertools
import json
import math
import os
import sys
import tempfile

import networkx as nx
import numpy as np

from td import channel                                            # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
THETA, LAM = 0.40, 0.30
W = (1.0 - LAM) * (1.0 - THETA)


def _premium():
    """tools/ is not a package on the path; load the script the way run_all.py loads tests."""
    path = os.path.join(ROOT, "tools", "measure", "premium.py")
    spec = importlib.util.spec_from_file_location("measure_premium", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod                  # @dataclass resolves through sys.modules
    spec.loader.exec_module(mod)
    return mod


premium = _premium()


# ------------------------------------------------------------------ fixtures
def graph_from(books, M, states=None):
    """The N-way schema `channel`/`model` read: `cand`, `S`, `M`, `S_free`, `state` on a path."""
    G = nx.Graph()
    zips = sorted(books)
    for z in zips:
        G.add_node(z, cand=tuple(sorted(books[z])), S=dict(books[z]), M=float(M[z]),
                   S_free=0.0, state=(states or {}).get(z, "XX"))
    nx.add_path(G, zips)
    return G


TOY_BOOKS = {"z1": {"A": 10.0},
             "z2": {"A": 6.0, "B": 4.0},
             "z3": {"B": 8.0, "C": 3.0},
             "z4": {"C": 9.0}}
TOY_M = {"z1": 20.0, "z2": 15.0, "z3": 15.0, "z4": 20.0}
TOY_D = {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"}


def toy():
    return graph_from(TOY_BOOKS, TOY_M)


def seeded(n_reps=4, n_zips=10, seed=7):
    """~40% saturation: 1-3 holders per zip, each holding 8-32% of the zip's opportunity."""
    rng = np.random.default_rng(seed)
    reps = [f"R{i}" for i in range(n_reps)]
    books, M = {}, {}
    for i in range(n_zips):
        z = f"z{i:02d}"
        M[z] = float(rng.uniform(5.0, 20.0))
        holders = rng.choice(n_reps, size=int(rng.integers(1, 4)), replace=False)
        books[z] = {reps[int(h)]: M[z] * float(rng.uniform(0.08, 0.32)) for h in holders}
        assert sum(books[z].values()) <= M[z]                    # headroom: T_z <= M_z
    return graph_from(books, M), reps, sorted(books)


def rungs(out):
    return [out["ladder"][name]["book"]
            for name in ("P0", "P_star_A", "P_S", "P13", "P_free")]


# ------------------------------------------------------------------ the worked example, §4
def test_toy_ladder():
    """`24 <= 28 <= 28 <= 28 <= 33`, and the `P*(A)` roster is (A, C)."""
    out = premium.measure(toy(), TOY_D, sigma={"D1": "A", "D2": "B"},
                          theta=THETA, lam=LAM)
    assert rungs(out) == [24.0, 28.0, 28.0, 28.0, 33.0], rungs(out)
    assert out["P_star_A_roster"] == {"D1": "A", "D2": "C"}
    assert out["ladder"]["P0"]["share"] == 24.0 / 40.0
    assert out["ladder"]["P_free"]["share"] == 33.0 / 40.0
    assert out["total_book"] == 40.0 and out["w"] == W
    assert out["P13_solve"]["status"] == "optimal"
    assert out["P13_solve"]["staff"] == ["A", "C"]


def test_toy_nash_roster_closes_the_matching_gap():
    """Stage 2 picks (A, C) on its own, so `P0 = P*(A) = 28` and the gap vanishes."""
    out = premium.measure(toy(), TOY_D, theta=THETA, lam=LAM)
    assert out["sigma0"] == {"D1": "A", "D2": "C"}
    assert out["ladder"]["P0"]["book"] == 28.0
    assert out["gaps"]["match"]["book"] == 0.0
    assert out["gaps"]["match"]["small"] and out["gaps"]["map"]["small"]
    assert out["staff"] == ["A", "C"]


def test_toy_gain_decomposition():
    """`g = B_j + w * b`: `g - 0.42 * b` has one row repeated, the rep-independent part."""
    G = toy()
    g, R, D = channel.gain_matrix(G, TOY_D, theta=THETA, lam=LAM)
    b, Rb, Db = premium.book_matrix(G, TOY_D)
    assert (R, D) == (Rb, Db) == (["A", "B", "C"], ["D1", "D2"])
    expected = np.array([[22.82, 16.10], [17.78, 19.46], [16.10, 21.14]])
    assert np.allclose(g, expected, rtol=0, atol=1e-9), g
    common = g - W * b
    assert np.allclose(common, common[0], rtol=0, atol=1e-12), common


# ------------------------------------------------------------------ brute force at 40% saturation
def brute_best_roster(b, reps, districts):
    return max(sum(b[reps.index(r), j] for j, r in enumerate(perm))
               for perm in itertools.permutations(reps, len(districts)))


def brute_max_k_coverage(S, k):
    return max(float(S[list(sub)].max(axis=0).sum())
               for sub in itertools.combinations(range(S.shape[0]), k))


def _seeded_case(k):
    G, reps, zips = seeded()
    to_d = {z: f"D{i % k + 1}" for i, z in enumerate(zips)}
    out = premium.measure(G, to_d, theta=THETA, lam=LAM)
    b, R, D = premium.book_matrix(G, to_d)
    S = premium.book_by_zip(G, R, zips)
    return out, b, R, D, S


def test_seeded_best_roster_is_optimal():
    for k in (2, 3):
        out, b, R, D, _ = _seeded_case(k)
        assert math.isclose(out["ladder"]["P_star_A"]["book"], brute_best_roster(b, R, D),
                            rel_tol=0, abs_tol=1e-9)


def test_seeded_p13_is_optimal():
    for k in (2, 3):
        out, _, _, _, S = _seeded_case(k)
        assert out["P13_solve"]["status"] == "optimal"
        assert math.isclose(out["ladder"]["P13"]["book"], brute_max_k_coverage(S, k),
                            rel_tol=0, abs_tol=1e-9)
        assert out["P13_solve"]["greedy_book"] <= out["ladder"]["P13"]["book"] + 1e-9


def test_seeded_ladder_is_monotone():
    for k in (2, 3):
        out, _, _, _, _ = _seeded_case(k)
        got = rungs(out)
        assert all(a <= b + 1e-9 for a, b in zip(got, got[1:])), got


# ------------------------------------------------------------------ the degenerate map
def test_p_s_equals_p0_when_every_zip_sits_with_its_top_holder():
    books = {"z1": {"A": 10.0, "B": 2.0}, "z2": {"A": 7.0, "B": 1.0},
             "z3": {"B": 9.0, "A": 3.0}, "z4": {"B": 6.0, "A": 2.0}}
    M = {z: 20.0 for z in books}
    to_d = {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"}
    out = premium.measure(graph_from(books, M), to_d, sigma={"D1": "A", "D2": "B"},
                          theta=THETA, lam=LAM)
    assert out["ladder"]["P0"]["book"] == 32.0
    assert out["ladder"]["P_S"]["book"] == out["ladder"]["P0"]["book"]
    assert out["gaps"]["map"]["book"] == 0.0 and out["gaps"]["map"]["small"]


# ------------------------------------------------------------------ the CLI
def write_draw(dir_, to_district, sigma, value):
    os.makedirs(dir_, exist_ok=True)
    with open(os.path.join(dir_, "draw.csv"), "w", encoding="utf-8") as fh:
        fh.write("zip,district\n")
        for z in sorted(to_district):
            fh.write(f"{z},{to_district[z]}\n")
    with open(os.path.join(dir_, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(run_id=os.path.basename(dir_),
                       winner=dict(assignment=dict(sigma), stage2_value=float(value))),
                  fh, indent=2)
    return dir_


def write_instance(path, books, M):
    """The `td_instance_descaled/1` file `td.instance.load_descaled` reads."""
    zips = sorted(books)
    obj = dict(format="td_instance_descaled/1",
               nodes=dict(z=zips, m_rel=[M[z] for z in zips],
                          share=[{r: s / M[z] for r, s in books[z].items()} for z in zips],
                          state=["XX"] * len(zips), share_free=[0.0] * len(zips)),
               edges=dict(u=zips[:-1], v=zips[1:]), firm={}, meta={})
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return path


def test_both_draw_layouts_parse():
    with tempfile.TemporaryDirectory() as tmp:
        flat = write_draw(os.path.join(tmp, "draw_k02_20260903"), TOY_D,
                          {"D1": "A", "D2": "C"}, 6.1788)
        nested = os.path.join(tmp, "sweep_20260903_s10")
        write_draw(os.path.join(nested, "k02"), TOY_D, {"D1": "A", "D2": "C"}, 6.1788)

        d, label = premium.resolve_draw_dir(flat)
        assert (d, label) == (flat, "draw_k02_20260903")
        d, label = premium.resolve_draw_dir(nested)
        assert (d, label) == (os.path.join(nested, "k02"), "sweep_20260903_s10")
        d, label = premium.resolve_draw_dir(os.path.join(nested, "k02"))
        assert (d, label) == (os.path.join(nested, "k02"), "sweep_20260903_s10")
        assert premium.read_draw(os.path.join(d, "draw.csv")) == TOY_D


def test_measure_is_deterministic():
    G = toy()
    assert premium.measure(G, TOY_D, theta=THETA, lam=LAM) == \
        premium.measure(G, TOY_D, theta=THETA, lam=LAM)


def test_cli_output_is_byte_identical_apart_from_the_timestamp():
    with tempfile.TemporaryDirectory() as tmp:
        inst = write_instance(os.path.join(tmp, "instance_descaled.json.gz"), TOY_BOOKS, TOY_M)
        d = __import__("td.instance", fromlist=["instance"]).load_descaled(inst)
        st2 = channel.stage2(d.G, TOY_D, d.reps, theta=THETA, lam=LAM)
        draw = write_draw(os.path.join(tmp, "draw_k02_20260903"), TOY_D,
                          st2["assignment"], st2["value"])

        out_a, out_b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
        for out in (out_a, out_b):
            assert premium.main([inst, draw, "--out", out,
                                 "--theta", str(THETA), "--lam", str(LAM)]) == 0

        def read(out):
            with open(os.path.join(out, "draw_k02_20260903.json"), encoding="utf-8") as fh:
                return fh.read()

        a, b = read(out_a), read(out_b)
        drop = lambda s: "\n".join(l for l in s.splitlines() if '"written"' not in l)
        assert drop(a) == drop(b)
        payload = json.loads(a)
        assert payload["run_id"] == "draw_k02_20260903"
        assert len(payload["instance_sha256"]) == 64 and len(payload["draw_sha256"]) == 64
        assert math.isclose(payload["V"]["sigma0"], st2["value"], rel_tol=0, abs_tol=1e-9)
        assert payload["ladder"]["P_free"]["book"] == 33.0
