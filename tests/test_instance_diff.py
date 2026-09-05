"""tools/measure/instance_diff.py -- separating a divisor change from a real re-estimation.

The one that matters is `divisor_ratio`: `m_rel = M / median(positive M)`, so when the divisor
moves between exports every zip's ratio moves with it, and the zips that did NOT change land on
that constant.  Recovering it is what makes the rest of the comparison meaningful, so the tests
plant a known K and check it comes back.

No test here reads a gitignored input; every instance is built in-process.
"""
import importlib.util
import os
import sys

import networkx as nx
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _diff():
    """tools/ is not a package on the path; load the script the way run_all.py loads tests."""
    path = os.path.join(ROOT, "tools", "measure", "instance_diff.py")
    spec = importlib.util.spec_from_file_location("measure_instance_diff", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


diff = _diff()


# ------------------------------------------------------------------ fixtures
def graph_from(books, M, free=None):
    """The N-way schema `channel`/`model` read."""
    G = nx.Graph()
    zips = sorted(M)
    for z in zips:
        b = dict(books.get(z, {}))
        G.add_node(z, cand=tuple(sorted(b)), S=b, M=float(M[z]),
                   S_free=float((free or {}).get(z, 0.0)), state="XX")
    nx.add_path(G, zips)
    return G


# ------------------------------------------------------------------ divisor recovery
def test_divisor_ratio_recovers_a_planted_constant():
    rng = np.random.default_rng(11)
    K = 1.650015380
    ratios = np.concatenate([
        np.full(400, K),                       # unchanged in dollars
        K * rng.uniform(1.05, 12.0, size=300),  # genuinely re-estimated
    ])
    assert abs(diff.divisor_ratio(ratios) - K) < 1e-9


def test_divisor_ratio_survives_six_figure_export_rounding():
    """The export carries 6 significant figures, so the spike is a narrow band, not a point."""
    rng = np.random.default_rng(3)
    K = 1.650015380
    jitter = 1.0 + rng.uniform(-5e-6, 5e-6, size=440)
    ratios = np.concatenate([K * jitter, K * rng.uniform(1.2, 20.0, size=500)])
    assert abs(diff.divisor_ratio(ratios) / K - 1.0) < 1e-5


def test_divisor_ratio_is_one_when_nothing_rescaled():
    rng = np.random.default_rng(5)
    ratios = np.concatenate([np.ones(200), rng.uniform(1.1, 4.0, size=90)])
    assert abs(diff.divisor_ratio(ratios) - 1.0) < 1e-9


def test_divisor_ratio_rejects_no_overlap():
    try:
        diff.divisor_ratio(np.array([]))
    except ValueError:
        return
    raise AssertionError("expected ValueError on an empty ratio array")


# ------------------------------------------------------------------ classification
def test_composition_counts_the_four_classes():
    G = graph_from(
        books={"z1": {"A": 3.0, "B": 2.0}, "z2": {"A": 4.0}, "z3": {}, "z4": {}},
        M={"z1": 10.0, "z2": 10.0, "z3": 10.0, "z4": 10.0},
        free={"z3": 1.5},                      # real book, no incumbent -> vacant
    )
    assert diff.composition(G) == {"contested": 1, "uncontested": 1, "vacant": 1, "untapped": 1}


def test_untapped_mass_excludes_vacant():
    G = graph_from(books={"z1": {}, "z2": {}}, M={"z1": 7.0, "z2": 5.0}, free={"z1": 0.5})
    assert diff.untapped_mass(G) == 5.0        # z1 is vacant, not untapped


def test_saturation_is_book_over_opportunity():
    G = graph_from(books={"z1": {"A": 2.0}, "z2": {"B": 1.0, "C": 1.0}},
                   M={"z1": 10.0, "z2": 10.0})
    assert abs(diff.saturation(G) - 0.2) < 1e-12
    assert abs(diff.saturation(G, ["z1"]) - 0.2) < 1e-12


# ------------------------------------------------------------------ the row-format trap
def test_row_inflation_counts_one_row_per_zip_rep():
    """The source repeats a zip's opportunity on every rep row; summing it there double-counts."""
    G = graph_from(books={"z1": {"A": 1.0, "B": 1.0}, "z2": {"A": 1.0}},
                   M={"z1": 10.0, "z2": 10.0})
    # z1 occupies 2 rows at M=10, z2 occupies 1 -> 30 against a true 20
    assert abs(diff.row_inflation(G) - 1.5) < 1e-12


def test_row_inflation_gives_a_zip_with_no_reps_one_row():
    G = graph_from(books={"z1": {}}, M={"z1": 10.0})
    assert abs(diff.row_inflation(G) - 1.0) < 1e-12


def test_row_inflation_is_one_when_every_zip_has_a_single_rep():
    G = graph_from(books={"z1": {"A": 1.0}, "z2": {"B": 1.0}}, M={"z1": 3.0, "z2": 9.0})
    assert abs(diff.row_inflation(G) - 1.0) < 1e-12
