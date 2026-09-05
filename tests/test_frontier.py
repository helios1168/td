"""
test_frontier.py -- the utility-convention gate (tools/measure/frontier.py, unit U8-band).

Synthetic only: no instance file, no network.  The gate is what stands between a frontier run and
a wrong-units "refutation" of P1-band, and it is the one part of `frontier.py` that was pinned to
v1 at `k = 13` by a hard-coded `EG_S13_REFERENCE`.  These tests pin its instance-agnostic form:
`EG_S >= V` always, the published number only when `--gate-reference` asks for it.

`EG_S` maximises `sum_i log g_i` over every coverage, and the delivered map is one coverage, so
`EG_S >= V` is a theorem, not a measurement -- it can only fail if `U` and `V` were built in
different utility conventions, which is exactly the `model.utilities` (masked) against
`channel.gain_matrix` (unmasked) mistake `CODEVERIFY_U8-band.md` row 2 records.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import os
import sys

import networkx as nx

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
THETA, LAM = 0.40, 0.30


def _frontier():
    """tools/ is not a package on the path; load the script the way run_all.py loads tests."""
    path = os.path.join(ROOT, "tools", "measure", "frontier.py")
    spec = importlib.util.spec_from_file_location("measure_frontier", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod                  # @dataclass resolves through sys.modules
    spec.loader.exec_module(mod)
    return mod


frontier = _frontier()

TOY_BOOKS = {"z1": {"A": 10.0},
             "z2": {"A": 6.0, "B": 4.0},
             "z3": {"B": 8.0, "C": 3.0},
             "z4": {"C": 9.0}}
TOY_M = {"z1": 20.0, "z2": 15.0, "z3": 15.0, "z4": 20.0}
TOY_DRAW = {"z1": "D1", "z2": "D2", "z3": "D2", "z4": "D2"}   # deliberately not EG-optimal
TOY_ROSTER = {"D1": "A", "D2": "C"}


def toy_setting():
    G = nx.Graph()
    for z in sorted(TOY_BOOKS):
        G.add_node(z, cand=tuple(sorted(TOY_BOOKS[z])), S=dict(TOY_BOOKS[z]),
                   M=float(TOY_M[z]), S_free=0.0, state="XX")
    nx.add_path(G, sorted(TOY_BOOKS))
    return frontier.build_setting(G, TOY_DRAW, TOY_ROSTER,
                                  theta=THETA, lam=LAM, filler_capture="theta")


def test_gate_passes_on_the_structural_invariant():
    """No reference: the gate checks `EG_S >= V` and reports the gap."""
    s = toy_setting()
    out = frontier.gate(s)
    assert out["passed"] and out["above_V"] and out["matches_reference"]
    assert out["reference"] is None and out["delta_upper"] is None
    assert out["EG_S_upper"] >= s.V
    assert abs(out["gap_to_V"] - (out["EG_S_upper"] - s.V)) < 1e-12
    assert out["gap_to_V"] > 0.0                 # the delivered map is not EG-optimal here


def test_gate_does_not_consult_the_v1_constant():
    """The toy's `EG_S` is ~6.2 nats, nowhere near v1's 60.697 -- and the gate still passes."""
    s = toy_setting()
    out = frontier.gate(s)
    assert abs(out["EG_S_upper"] - frontier.EG_S13_REFERENCE) > 50.0
    assert out["passed"]


def test_gate_raises_when_EG_is_below_V():
    """A `V` and a `U` from different utility conventions -- the masked/unmasked mistake."""
    s = toy_setting()
    broken = dataclasses.replace(s, V=s.V + 1.0)     # V now exceeds the true optimum
    try:
        frontier.gate(broken)
    except ValueError as e:
        assert "below the delivered V" in str(e) and "masked" in str(e)
    else:
        raise AssertionError("the gate accepted EG_S < V")


def test_gate_reference_matches_and_misses():
    """`--gate-reference` pins the exact number when one is published, and only then."""
    s = toy_setting()
    eg = frontier.gate(s)["EG_S_upper"]
    out = frontier.gate(s, reference=eg)
    assert out["passed"] and out["matches_reference"]
    assert abs(out["delta_upper"]) <= frontier.GATE_TOL
    try:
        frontier.gate(s, reference=eg + 1e-3)
    except ValueError as e:
        assert "gate reference MISSED" in str(e)
    else:
        raise AssertionError("the gate accepted a reference it does not reproduce")
