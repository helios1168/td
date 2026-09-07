"""oracle_boundaries.py -- degenerate and boundary inputs to tools/measure/premium.py.

Each case prints what the implementation does; the report says which are inside the spec's
stated domain (a partition into k districts, a roster injective into R, k <= |R|) and which
are outside it.

    .venv/bin/python3 docs/artifacts/U7-meas/oracle_boundaries.py
"""
from __future__ import annotations

import importlib.util
import os
import sys

import networkx as nx

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))
sys.path.insert(0, ROOT)
THETA, LAM = 0.40, 0.30


def load_premium():
    path = os.path.join(ROOT, "tools", "measure", "premium.py")
    spec = importlib.util.spec_from_file_location("measure_premium", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def graph_from(books, M, free=None):
    G = nx.Graph()
    for z in sorted(books):
        G.add_node(z, cand=tuple(sorted(books[z])), S=dict(books[z]), M=float(M[z]),
                   S_free=float((free or {}).get(z, 0.0)), state="XX")
    nx.add_path(G, sorted(books))
    return G


def show(name, fn):
    try:
        out = fn()
    except Exception as e:                                        # noqa: BLE001
        print(f"{name:<42} raises {type(e).__name__}: {str(e)[:110]}")
        return None
    print(f"{name:<42} {out}")
    return out


def rungs(o):
    return [o["ladder"][n]["book"] for n in ("P0", "P_star_A", "P_S", "P13", "P_free")]


def main():
    p = load_premium()
    B = {"z1": {"A": 10.0}, "z2": {"A": 6.0, "B": 4.0},
         "z3": {"B": 8.0, "C": 3.0}, "z4": {"C": 9.0}}
    M = {"z1": 20.0, "z2": 15.0, "z3": 15.0, "z4": 20.0}
    G = graph_from(B, M)

    print("-- inside the spec's domain")
    show("k = 1 (one district, all zips)",
         lambda: (rungs(p.measure(G, {z: "D1" for z in B}, theta=THETA, lam=LAM)),
                  p.measure(G, {z: "D1" for z in B}, theta=THETA, lam=LAM)["staff"]))
    show("k = |R| = 3",
         lambda: rungs(p.measure(graph_from(B, M),
                                 {"z1": "D1", "z2": "D2", "z3": "D3", "z4": "D3"},
                                 theta=THETA, lam=LAM)))
    zero = {z: {} for z in B}
    show("all books zero (total_book = 0)",
         lambda: (rungs(p.measure(graph_from(zero, M), {"z1": "D1", "z2": "D1",
                                                        "z3": "D2", "z4": "D2"},
                                  reps_order=["A", "B", "C"], theta=THETA, lam=LAM)),
                  p.measure(graph_from(zero, M), {"z1": "D1", "z2": "D1", "z3": "D2",
                                                  "z4": "D2"}, reps_order=["A", "B", "C"],
                            theta=THETA, lam=LAM)["gaps"]["map"]))
    tie = {"z1": {"A": 5.0, "B": 5.0}, "z2": {"A": 5.0, "B": 5.0}}
    show("exact ties between two reps",
         lambda: (rungs(p.measure(graph_from(tie, {"z1": 20.0, "z2": 20.0}),
                                  {"z1": "D1", "z2": "D2"}, theta=THETA, lam=LAM)),
                  p.measure(graph_from(tie, {"z1": 20.0, "z2": 20.0}),
                            {"z1": "D1", "z2": "D2"}, theta=THETA, lam=LAM)["staff"]))
    show("filler book, filler_capture='full'",
         lambda: rungs(p.measure(graph_from(B, M, free={"z1": 3.0}),
                                 {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"},
                                 theta=THETA, lam=LAM, filler_capture="full")))

    print("\n-- the S13 tie found by the random search (5 reps, k = 3)")
    tb = {'z0': {'R1': 0.5439512430377764, 'R0': 1.42778488039438,
                 'R3': 1.266477547504812, 'R2': 0.8995035730749971},
          'z1': {'R0': 1.2048354196892825, 'R2': 13.713790056483344,
                 'R4': 14.08456177320108},
          'z2': {'R4': 1.2759982183563057},
          'z3': {'R4': 5.675002014102114, 'R3': 1.1818698877055982,
                 'R2': 21.323549182093757}}
    tM = {'z0': 18.968573927213612, 'z1': 36.62722782077348,
          'z2': 6.59620625266846, 'z3': 32.19862731784246}
    td = {'z0': 'D1', 'z1': 'D2', 'z2': 'D3', 'z3': 'D1'}
    o = p.measure(graph_from(tb, tM), td, theta=THETA, lam=LAM)
    print("  S13 =", o["staff"], " P_S =", o["ladder"]["P_S"]["book"])
    print("  (R0 in place of R1 on D3 is equally Nash-optimal: no rep holds book at z2 "
          "except R4, so every remaining rep values D3 identically; P_S would be 38.1119)")

    print("\n-- outside the spec's domain (k <= |R|, roster injective into R)")
    show("k = 4 > |R| = 3",
         lambda: rungs(p.measure(G, {"z1": "D1", "z2": "D2", "z3": "D3", "z4": "D4"},
                                 theta=THETA, lam=LAM)))
    show("k = 4 > |R| = 3, explicit roster",
         lambda: rungs(p.measure(G, {"z1": "D1", "z2": "D2", "z3": "D3", "z4": "D4"},
                                 sigma={"D1": "A", "D2": "B", "D3": "C", "D4": "A"},
                                 theta=THETA, lam=LAM)))
    show("roster not injective",
         lambda: p.measure(G, {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"},
                           sigma={"D1": "A", "D2": "A"}, theta=THETA, lam=LAM))
    show("roster misses a district",
         lambda: p.measure(G, {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"},
                           sigma={"D1": "A"}, theta=THETA, lam=LAM))
    show("roster names a rep outside R",
         lambda: p.measure(G, {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"},
                           sigma={"D1": "A", "D2": "Z"}, theta=THETA, lam=LAM))
    show("empty map",
         lambda: p.measure(G, {}, theta=THETA, lam=LAM)["ladder"])
    show("unknown filler_capture",
         lambda: p.measure(G, {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"},
                           theta=THETA, lam=LAM, filler_capture="nope"))

    print("\n-- trap 15: a MILP that does not stop optimal must report no bound")
    import numpy as np
    S = np.array([[1.0, 0.0], [0.0, 2.0]])
    show("max_k_coverage with k > n_reps (infeasible)",
         lambda: p.max_k_coverage(S, ["A", "B"], 3))
    show("max_k_coverage k = 0", lambda: p.max_k_coverage(S, ["A", "B"], 0))
    trap15_payload_probe()
    return 0


def trap15_payload_probe():
    """measure() with the MILP forced to a non-optimal stop: P13 and the roster gap must be
    null in the payload, and greedy must stay in its own field (trap 15)."""
    p = load_premium()
    B = {"z1": {"A": 10.0}, "z2": {"A": 6.0, "B": 4.0},
         "z3": {"B": 8.0, "C": 3.0}, "z4": {"C": 9.0}}
    M = {"z1": 20.0, "z2": 15.0, "z3": 15.0, "z4": 20.0}
    real = p.max_k_coverage
    p.max_k_coverage = lambda S, reps, k: p.Coverage(
        None, "limit", None, real(S, reps, k).greedy_value, real(S, reps, k).greedy_staff)
    out = p.measure(graph_from(B, M), {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"},
                    theta=THETA, lam=LAM)
    p.max_k_coverage = real
    print("\n-- trap 15 in the payload (MILP forced to status='limit')")
    print("  ladder.P13   =", out["ladder"]["P13"])
    print("  gaps.roster  =", out["gaps"]["roster"])
    print("  P13_solve    =", out["P13_solve"])


if __name__ == "__main__":
    sys.exit(main())
