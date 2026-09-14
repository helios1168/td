"""test_fefx.py -- A2: adversarial and regression tests for the FEFx audit core.

Synthetic only: deterministic NetworkX fixtures, no instance file, no network, no confidential
rows.  The audit module is `tools/measure/fefx.py` (unit A1), loaded the way
`tests/test_measure.py` loads `tools/measure/premium.py`: `tools/` is not a package on the path,
so it comes in through an importlib spec and `sys.modules`.

The file is plain-`assert` pytest-layout so the repository's own runner (`tests/run_all.py`,
which imports every `test_*.py` in this directory) can execute it without pytest installed,
which is the state of the frozen `.venv`.  `raises` below is a local stand-in for
`pytest.raises`.

Load-bearing tests:

* the C0 toys (contract sections 1 and 13): EF1 removes the single *most* valuable zip (`TOP`),
  FEFx removes the least (`BOT`), and FEFx can fail while EF1 passes;
* the Q0 zero-valued-ZIP divergence between the `gain_matrix` and legacy `masked` valuation
  conventions, with the convention recorded on every result;
* the `td/model.py::fairness` regression anchor -- masked valuation, `1e-12` slack, the total
  roster divisor `n = |R|`, and the legacy output keys -- on a square and a rectangular roster,
  including a genuine EF1 failure;
* the `PairVerdict` reason enum, counted separately;
* band-only and band-plus-book-overlap feasibility as two separate masks the caller composes,
  never combined inside the module;
* non-finite input rejection and the empty-retained-roster branch.
"""
from __future__ import annotations

import contextlib
import importlib.util
import math
import os
import re
import sys

import networkx as nx
import numpy as np

from td import channel, model                                     # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
THETA, LAM = 0.40, 0.30
SLACK = 1e-12


def _fefx():
    """`tools/` is not a package on the path; load the script like test_measure.py does."""
    path = os.path.join(ROOT, "tools", "measure", "fefx.py")
    spec = importlib.util.spec_from_file_location("measure_fefx", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod                  # @dataclass resolves through sys.modules
    spec.loader.exec_module(mod)
    return mod


fefx = _fefx()


@contextlib.contextmanager
def raises(exc, match=None):
    """A local `pytest.raises` stand-in so the frozen runner needs no pytest."""
    try:
        yield
    except exc as err:
        if match is not None and re.search(match, str(err)) is None:
            raise AssertionError(f"{exc.__name__} message {str(err)!r} lacks {match!r}")
    else:
        raise AssertionError(f"{exc.__name__} was not raised")


def close(a, b, abs_tol=1e-9):
    return math.isclose(a, b, rel_tol=0.0, abs_tol=abs_tol)


# ------------------------------------------------------------------ fixtures
def graph_from(books, M, states=None):
    """The N-way schema `model`/`channel` read: `cand`, `S`, `M`, `S_free`, `state`."""
    G = nx.Graph()
    zips = sorted(books)
    for z in zips:
        G.add_node(z, cand=tuple(sorted(books[z])), S=dict(books[z]), M=float(M[z]),
                   S_free=0.0, state=(states or {}).get(z, "XX"))
    nx.add_path(G, zips)
    return G


def m_for(u):
    """A zip with no book values its ambient opportunity at `lam * M`; solve for `M` at `u`."""
    return u / LAM


def _verdict(out, i, j):
    for p in out["pairs"]:
        if p.i == i and p.j == j:
            return p
    raise AssertionError(f"no pair ({i!r}, {j!r}) in {out['pairs']}")


def _fairness_anchor(G, to_district, reps, districts, assignment, **kw):
    """`td/model.py::fairness` recomputed on the module's own masked utilities, then compared.

    `assignment` is district -> rep; the owner map handed to `fairness` is its inverse lifted
    onto zips.  This is the section 12 anchor: masked convention, `1e-12` slack, divisor `|R|`.
    """
    nodes = sorted(to_district)
    U, R = model.utilities(G, nodes, reps, theta=THETA, lam=LAM)
    assert R == list(reps)
    to_owner = {z: assignment[to_district[z]] for z in nodes}
    oi = model.owner_index(nodes, to_owner, reps)
    fair = model.fairness(U, oi)
    out = fefx.compute_envy_matrix(G, to_district, list(reps), list(districts),
                                   valuation="masked", quantifier="ef1", slack=SLACK,
                                   assignment=dict(assignment), theta=THETA, lam=LAM, **kw)
    assert out["valuation"] == "masked"
    assert out["quantifier"] == "ef1"
    assert out["slack"] == SLACK
    assert out["n"] == len(reps), "the legacy divisor is the total roster, |R|"
    assert out["ef1"] == fair["ef1"]
    assert out["n_ef1_failures"] == fair["n_ef1_failures"]
    assert close(out["envy_over_umax"], fair["envy_over_umax"], 1e-12)
    assert close(out["prop_shortfall"], fair["prop_shortfall"], 1e-12)
    return out, fair


# ------------------------------------------------------------------ the valuation convention
def test_district_extrema_matches_gain_matrix_and_per_zip_extrema():
    """`G` is `channel.gain_matrix`; `TOP`/`BOT` are the per-district max/min of `u_i`."""
    books = {"z0": {"A": 0.0}, "z1": {"A": 10.0, "B": 4.0}, "z2": {"B": 2.0}}
    M = {"z0": 5.0, "z1": 5.0, "z2": 7.0}
    to_d = {"z0": "D0", "z1": "D1", "z2": "D1"}
    G = graph_from(books, M)
    R, D = ["A", "B"], ["D0", "D1"]

    Gmat, TOP, BOT = fefx.district_extrema(G, to_d, R, D, theta=THETA, lam=LAM)
    g, Rg, Dg = channel.gain_matrix(G, to_d, R, D, theta=THETA, lam=LAM)
    assert (Rg, Dg) == (R, D)
    assert np.allclose(Gmat, g, rtol=0, atol=1e-12), (Gmat, g)

    nodes = sorted(to_d)
    c1, c2, c_free = model.coefficients(THETA, LAM, "theta")
    for j, d in enumerate(D):
        cols = [k for k, z in enumerate(nodes) if to_d[z] == d]
        for i, r in enumerate(R):
            expected = []
            for k in cols:
                z = nodes[k]
                S = model.books(G, z)
                common = c2 * sum(S.values()) + c_free * model.free_book(G, z) + LAM * M[z]
                expected.append(common + (c1 - c2) * float(S.get(r, 0.0)))
            assert close(TOP[i, j], max(expected), 1e-12)
            assert close(BOT[i, j], min(expected), 1e-12)
            assert close(Gmat[i, j], sum(expected), 1e-12)


# ------------------------------------------------------------------ the C0 toys
def test_c0_toy_a_ef1_uses_top_max_and_fefx_uses_bot_min():
    """Contract section 13(a): own 6, envied zips [5, 3, 2] summing to 10.

    EF1 residual `10 - max = 5` -> pass; FEFx residual `10 - min = 8` -> fail.
    """
    books = {"zk1": {}, "zk2": {}, "zk3": {}, "zi": {}}
    M = {"zk1": m_for(5.0), "zk2": m_for(3.0), "zk3": m_for(2.0), "zi": m_for(6.0)}
    to_d = {"zk1": "Ak", "zk2": "Ak", "zk3": "Ak", "zi": "Ai"}
    G = graph_from(books, M)
    R, D = ["i", "k"], ["Ai", "Ak"]

    Gmat, TOP, BOT = fefx.district_extrema(G, to_d, R, D, theta=THETA, lam=LAM)
    assert close(Gmat[0, 0], 6.0) and close(Gmat[0, 1], 10.0)
    assert close(TOP[0, 1], 5.0) and close(BOT[0, 1], 2.0)

    out = fefx.compute_envy_matrix(G, to_d, R, D, valuation="gain_matrix",
                                   assignment={"Ai": "i", "Ak": "k"},
                                   theta=THETA, lam=LAM)
    p = _verdict(out, "i", "Ak")
    assert p.applicable and p.reason is None
    assert p.ef1 is True and p.fefx is False
    assert close(Gmat[0, 1] - TOP[0, 1], 5.0)       # EF1 removes max
    assert close(Gmat[0, 1] - BOT[0, 1], 8.0)       # FEFx removes min
    assert out["n_ef1_failures"] == 0 and out["n_fefx_failures"] >= 1


def test_c0_toy_b_fefx_can_fail_when_ef1_passes():
    """Contract section 13(b): own 4, envied zips [7, 3] summing to 10.

    EF1: `4 >= 10 - 7 = 3` -> pass.  FEFx: `4 >= 10 - 3 = 7` -> fail.
    """
    books = {"zk1": {}, "zk2": {}, "zi": {}}
    M = {"zk1": m_for(7.0), "zk2": m_for(3.0), "zi": m_for(4.0)}
    to_d = {"zk1": "Ak", "zk2": "Ak", "zi": "Ai"}
    G = graph_from(books, M)
    R, D = ["i", "k"], ["Ai", "Ak"]

    out = fefx.compute_envy_matrix(G, to_d, R, D, valuation="gain_matrix",
                                   assignment={"Ai": "i", "Ak": "k"},
                                   theta=THETA, lam=LAM)
    p = _verdict(out, "i", "Ak")
    assert (p.ef1, p.fefx) == (True, False)
    assert out["ef1"] is True and out["fefx"] is False


# ------------------------------------------------------------------ the Q0 zero-valued ZIP
def test_q0_zero_valued_zip_diverges_between_masked_and_gain_matrix():
    """A non-candidate zip is 0 under `masked`, positive ambient under `gain_matrix`.

    The verdicts diverge (masked FEFx passes on a zero minimum; gain_matrix fails on a
    strictly positive minimum), each result names its convention, and only the masked run
    counts zero-valued bundle pairs.
    """
    books = {"zi": {"i": 0.0}, "zk1": {"k": 0.0}, "zk2": {"k": 0.0}}
    M = {"zi": m_for(4.0), "zk1": m_for(7.0), "zk2": m_for(3.0)}
    to_d = {"zi": "Ai", "zk1": "Ak", "zk2": "Ak"}
    G = graph_from(books, M)
    R, D = ["i", "k"], ["Ai", "Ak"]
    assignment = {"Ai": "i", "Ak": "k"}

    masked = fefx.compute_envy_matrix(G, to_d, R, D, valuation="masked",
                                      assignment=assignment, theta=THETA, lam=LAM)
    gained = fefx.compute_envy_matrix(G, to_d, R, D, valuation="gain_matrix",
                                      assignment=assignment, theta=THETA, lam=LAM)

    assert masked["valuation"] == "masked" and gained["valuation"] == "gain_matrix"
    pm, pg = _verdict(masked, "i", "Ak"), _verdict(gained, "i", "Ak")
    assert pm.fefx is True and pg.fefx is False          # the divergence
    assert pm.ef1 is True and pg.ef1 is True
    assert masked["n_zero_valued_bundle_pairs"] > 0
    assert gained["n_zero_valued_bundle_pairs"] == 0     # gain_matrix min is strictly positive


# ------------------------------------------------------------------ fairness regression anchor
SQUARE_BOOKS = {"z0": {"A": 0.0, "B": 0.0},
                "z1": {"A": 10.0, "B": 0.0},
                "z2": {"A": 10.0, "B": 0.0}}
SQUARE_TO_D = {"z0": "D0", "z1": "D1", "z2": "D1"}


def test_fairness_anchor_square_with_genuine_ef1_failure():
    """`|R| == |D|`: the masked call reproduces `fairness`, and the fixture really fails EF1."""
    G = graph_from(SQUARE_BOOKS, {z: 5.0 for z in SQUARE_BOOKS})
    out, fair = _fairness_anchor(G, SQUARE_TO_D, ["A", "B"], ["D0", "D1"],
                                 {"D0": "A", "D1": "B"})
    assert fair["ef1"] is False and fair["n_ef1_failures"] >= 1
    assert out["ef1"] is False and out["n_ef1_failures"] == fair["n_ef1_failures"]
    assert out["envy_over_umax"] > 0.0 and out["n"] == 2


RECT_BOOKS = {"z0": {"A": 0.0, "B": 0.0, "C": 0.0},
              "z1": {"A": 10.0, "B": 0.0, "C": 0.0},
              "z2": {"A": 10.0, "B": 0.0, "C": 0.0},
              "z3": {"B": 0.0, "C": 5.0}}
RECT_TO_D = {"z0": "D0", "z1": "D1", "z2": "D1", "z3": "D0"}


def test_fairness_anchor_rectangular_matches_td_model_fairness():
    """`|R| > |D|`: the extra rep is unmatched; its zero gain row still compares like fairness's."""
    G = graph_from(RECT_BOOKS, {z: 5.0 for z in RECT_BOOKS})
    out, fair = _fairness_anchor(G, RECT_TO_D, ["A", "B", "C"], ["D0", "D1"],
                                 {"D0": "A", "D1": "B"})
    assert out["n"] == 3 and out["n_unmatched"] == 0      # C is matched-layer unmatched, g=0
    assert out["n_retained"] == 2 and out["n_reps"] == 3
    assert out["ef1"] == fair["ef1"]
    assert out["n_ef1_failures"] == fair["n_ef1_failures"]


# ------------------------------------------------------------------ reason enum
def test_pair_verdict_reason_enum_counts_each_reason_separately():
    R = ["r0", "r1", "r2", "r3"]
    D = ["D0", "D1", "D2"]
    G = graph_from({"z0": {"r0": 1.0}, "z1": {"r1": 1.0}}, {"z0": 10.0, "z1": 10.0})
    feas = np.ones((4, 3), bool)
    feas[0, 1] = False
    out = fefx.compute_envy_matrix(
        G, {"z0": "D0", "z1": "D1"}, R, D, feasible=feas, valuation="gain_matrix",
        assignment={"D0": "r0", "D1": "r1", "D2": "r2"},
        district_mass={"D1": 20.0}, bands={"D1": (15.0, 25.0)}, theta=THETA, lam=LAM)

    assert out["n_applicable"] == 1
    assert out["n_self"] == 2
    assert out["n_empty_bundle"] == 2
    assert out["n_empty_own_bundle"] == 3
    assert out["n_unmatched"] == 3
    assert out["n_infeasible"] == 1
    assert (out["n_applicable"] + out["n_self"] + out["n_empty_bundle"]
            + out["n_empty_own_bundle"] + out["n_unmatched"] + out["n_infeasible"] == 12)

    for p in out["pairs"]:
        if p.applicable:
            assert p.reason is None
            assert p.ef1 is not None and p.fefx is not None
        else:
            assert p.reason in fefx.NOT_APPLICABLE_REASONS
            assert p.ef1 is None and p.fefx is None

    infeasible = _verdict(out, "r0", "D1")
    assert infeasible.reason == "infeasible_for_agent"
    assert infeasible.mass == 20.0 and infeasible.band == (15.0, 25.0)
    assert _verdict(out, "r0", "D0").reason == "self"
    assert _verdict(out, "r0", "D2").reason == "empty_bundle"
    assert _verdict(out, "r2", "D0").reason == "empty_own_bundle"
    assert _verdict(out, "r3", "D1").reason == "unmatched_rep"


# ------------------------------------------------------------------ separate masks
def test_band_only_and_overlap_masks_stay_separate_and_are_not_combined():
    """Two independent masks, one call each; the module neither ANDs them nor invents a rule.

    `band` marks (r0, D1) infeasible; `overlap` marks (r1, D0).  A combined (AND) audit would
    leave no applicable pair and count two infeasible pairs; each single-mask call must leave
    the other off-diagonal pair applicable.
    """
    G = graph_from({"z0": {"r0": 1.0}, "z1": {"r1": 1.0}}, {"z0": 10.0, "z1": 10.0})
    R, D = ["r0", "r1"], ["D0", "D1"]
    to_d = {"z0": "D0", "z1": "D1"}
    assignment = {"D0": "r0", "D1": "r1"}
    band = np.array([[True, False], [True, True]])
    overlap = np.array([[True, True], [False, True]])

    out_band = fefx.compute_envy_matrix(G, to_d, R, D, feasible=band,
                                        valuation="gain_matrix", assignment=assignment,
                                        theta=THETA, lam=LAM)
    out_overlap = fefx.compute_envy_matrix(G, to_d, R, D, feasible=overlap,
                                           valuation="gain_matrix", assignment=assignment,
                                           theta=THETA, lam=LAM)

    assert out_band["n_infeasible"] == 1 and out_band["n_applicable"] == 1
    assert out_overlap["n_infeasible"] == 1 and out_overlap["n_applicable"] == 1
    assert _verdict(out_band, "r0", "D1").reason == "infeasible_for_agent"
    assert _verdict(out_band, "r1", "D0").reason is None
    assert _verdict(out_overlap, "r1", "D0").reason == "infeasible_for_agent"
    assert _verdict(out_overlap, "r0", "D1").reason is None

    # `bands`/`district_mass` only annotate infeasible records; they never move a verdict.
    annotated = fefx.compute_envy_matrix(G, to_d, R, D, feasible=band,
                                         valuation="gain_matrix", assignment=assignment,
                                         district_mass={"D1": 99.0}, bands={"D1": (1.0, 2.0)},
                                         theta=THETA, lam=LAM)
    assert _verdict(annotated, "r1", "D0").ef1 == _verdict(out_band, "r1", "D0").ef1


# ------------------------------------------------------------------ rejection and empties
def test_non_finite_inputs_are_rejected():
    to_d = {"z0": "D0"}
    R, D = ["r0"], ["D0"]
    for bad in (float("nan"), float("inf"), float("-inf")):
        G = graph_from({"z0": {"r0": 1.0}}, {"z0": bad})
        with raises(ValueError, match="non-finite"):
            fefx.district_extrema(G, to_d, R, D, theta=THETA, lam=LAM)
        with raises(ValueError, match="non-finite"):
            fefx.compute_envy_matrix(G, to_d, R, D, valuation="gain_matrix",
                                     assignment={"D0": "r0"}, theta=THETA, lam=LAM)

    G = graph_from({"z0": {"r0": 1.0}}, {"z0": 10.0})
    for bad_slack in (float("nan"), float("inf"), -1.0):
        with raises(ValueError, match="slack"):
            fefx.compute_envy_matrix(G, to_d, R, D, slack=bad_slack,
                                     valuation="gain_matrix", assignment={"D0": "r0"},
                                     theta=THETA, lam=LAM)
    with raises(ValueError, match="valuation"):
        fefx.compute_envy_matrix(G, to_d, R, D, valuation="wishful",
                                 assignment={"D0": "r0"}, theta=THETA, lam=LAM)
    with raises(ValueError, match="quantifier"):
        fefx.compute_envy_matrix(G, to_d, R, D, quantifier="ef0",
                                 assignment={"D0": "r0"}, theta=THETA, lam=LAM)
    with raises(ValueError, match="feasible must be"):
        fefx.compute_envy_matrix(G, to_d, R, D, feasible=np.ones((3, 3), bool),
                                 valuation="gain_matrix", assignment={"D0": "r0"},
                                 theta=THETA, lam=LAM)


def test_empty_retained_roster_is_unmatched_not_a_crash():
    """`assignment={}` (gain_matrix): n=0, every pair unmatched, NaN gap, no ZeroDivisionError."""
    G = graph_from({"z0": {"r0": 1.0}}, {"z0": 10.0})
    R, D = ["r0", "r1"], ["D0", "D1"]
    out = fefx.compute_envy_matrix(G, {"z0": "D0"}, R, D, valuation="gain_matrix",
                                   assignment={}, theta=THETA, lam=LAM)
    assert out["n"] == 0 and out["n_retained"] == 0
    assert out["n_applicable"] == 0
    assert out["n_unmatched"] == len(R) * len(D)
    assert out["n_unstaffed_districts"] == len(D)
    assert math.isnan(out["prop_gap_min"])
    assert all((not p.applicable) and p.reason == "unmatched_rep" for p in out["pairs"])


def test_empty_bundle_extrema_are_zero():
    """A district with no zips yields `G = TOP = BOT = 0` and an `empty_bundle` reason."""
    G = graph_from({"z0": {"r0": 1.0}}, {"z0": 10.0})
    Gmat, TOP, BOT = fefx.district_extrema(G, {"z0": "D0"}, ["r0"], ["D0", "D1"],
                                           theta=THETA, lam=LAM)
    assert Gmat[0, 1] == 0.0 and TOP[0, 1] == 0.0 and BOT[0, 1] == 0.0
    out = fefx.compute_envy_matrix(G, {"z0": "D0"}, ["r0"], ["D0", "D1"],
                                   valuation="gain_matrix", assignment={"D0": "r0"},
                                   theta=THETA, lam=LAM)
    assert _verdict(out, "r0", "D1").reason == "empty_bundle"
