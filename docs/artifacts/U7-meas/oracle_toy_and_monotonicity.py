"""oracle_toy_and_monotonicity.py -- two attacks on MODEL_U7-meas.md.

(1) The §4 worked example, recomputed by brute force with no call into
    tools/measure/premium.py: every roster, every 2-subset, the gain matrix from the
    definition, and the stage-2 Nash value.  Then the same numbers *through* premium.measure,
    compared.

(2) A falsification search on the ladder `P0 <= P*(A) <= P_S <= P13 <= P_free` as §3 states
    it, under the implementation's convention `S13 = im(sigma_nash)`.  §3 justifies each
    inequality as "a restriction", but `P*(A)` is a Hungarian over *all* reps while `P_S` is
    a ceiling over the 13 selected ones, so the second inequality is not a restriction chain
    unless the premium-optimal roster happens to be inside S13.  Random small instances are
    searched for a violation, in both the sigma=None (Nash) and sigma=hand-roster modes.

    .venv/bin/python3 docs/artifacts/U7-meas/oracle_toy_and_monotonicity.py
"""
from __future__ import annotations

import importlib.util
import itertools
import math
import os
import sys

import networkx as nx
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))
sys.path.insert(0, ROOT)
THETA, LAM = 0.40, 0.30
C1, C2 = 1.0 - LAM, THETA * (1.0 - LAM)
W = C1 - C2


def load_premium():
    path = os.path.join(ROOT, "tools", "measure", "premium.py")
    spec = importlib.util.spec_from_file_location("measure_premium", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def graph_from(books, M):
    G = nx.Graph()
    for z in sorted(books):
        G.add_node(z, cand=tuple(sorted(books[z])), S=dict(books[z]), M=float(M[z]),
                   S_free=0.0, state="XX")
    nx.add_path(G, sorted(books))
    return G


# ------------------------------------------------------------------ brute-force reference
def reference(books, M, to_d, reps, hand=None):
    """Every rung by exhaustive enumeration, from the definitions."""
    zips = sorted(books)
    D = sorted(set(to_d.values()))
    S = np.array([[books[z].get(r, 0.0) for z in zips] for r in reps], float)
    b = np.array([[sum(books[z].get(r, 0.0) for z in zips if to_d[z] == d) for d in D]
                  for r in reps], float)
    Mz = np.array([M[z] for z in zips], float)
    T = S.sum(axis=0)
    common = C2 * T + LAM * Mz
    g = np.array([[common[[i for i, z in enumerate(zips) if to_d[z] == d]].sum()
                   + W * b[ri, dj] for dj, d in enumerate(D)]
                  for ri, r in enumerate(reps)], float)

    best_V, nash = -math.inf, None
    best_P, star = -math.inf, None
    for perm in itertools.permutations(range(len(reps)), len(D)):
        V = sum(math.log(g[i, j]) for j, i in enumerate(perm))
        P = sum(b[i, j] for j, i in enumerate(perm))
        if V > best_V:
            best_V, nash = V, perm
        if P > best_P:
            best_P, star = P, perm
    S13 = sorted({reps[i] for i in nash})
    sigma0 = ({D[j]: reps[i] for j, i in enumerate(nash)} if hand is None else dict(hand))
    P0 = sum(b[reps.index(sigma0[d]), j] for j, d in enumerate(D))
    P_S = float(S[[reps.index(r) for r in S13]].max(axis=0).sum())
    P13 = max(float(S[list(sub)].max(axis=0).sum())
              for sub in itertools.combinations(range(len(reps)), len(D)))
    P_free = float(S.max(axis=0).sum())
    return dict(g=g, b=b, P0=P0, P_star=best_P, P_S=P_S, P13=P13, P_free=P_free,
                V_nash=best_V, nash={D[j]: reps[i] for j, i in enumerate(nash)},
                star={D[j]: reps[i] for j, i in enumerate(star)}, S13=S13,
                total_book=float(S.sum()))


# ------------------------------------------------------------------ (1) the §4 toy
TOY_BOOKS = {"z1": {"A": 10.0}, "z2": {"A": 6.0, "B": 4.0},
             "z3": {"B": 8.0, "C": 3.0}, "z4": {"C": 9.0}}
TOY_M = {"z1": 20.0, "z2": 15.0, "z3": 15.0, "z4": 20.0}
TOY_D = {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"}


def toy_check(premium):
    ref = reference(TOY_BOOKS, TOY_M, TOY_D, ["A", "B", "C"], hand={"D1": "A", "D2": "B"})
    print("§4 brute force, hand roster (D1->A, D2->B):")
    print("  b            =", ref["b"].tolist())
    print("  g            =", np.round(ref["g"], 6).tolist(), " (spec: [[22.82,16.10],"
          "[17.78,19.46],[16.10,21.14]])")
    print("  g - w*b rows =", np.round(ref["g"] - W * ref["b"], 12).tolist())
    print("  ladder       =", [ref["P0"], ref["P_star"], ref["P_S"], ref["P13"],
                               ref["P_free"]], " (spec: 24, 28, 28, 28, 33)")
    print("  P*(A) roster =", ref["star"], " (spec: (A, C))")
    print("  Nash roster  =", ref["nash"], "V =", round(ref["V_nash"], 4),
          " (spec: D1->A, D2->C, V = 6.1788)")
    print("  shares       =", ref["P0"] / 40.0, ref["P_free"] / 40.0,
          " (spec: 60%, 82.5%)")
    got = premium.measure(graph_from(TOY_BOOKS, TOY_M), TOY_D,
                          sigma={"D1": "A", "D2": "B"}, theta=THETA, lam=LAM)
    rungs = [got["ladder"][n]["book"] for n in ("P0", "P_star_A", "P_S", "P13", "P_free")]
    ok = (rungs == [ref["P0"], ref["P_star"], ref["P_S"], ref["P13"], ref["P_free"]]
          and got["P_star_A_roster"] == ref["star"] and got["staff"] == ref["S13"]
          and abs(got["V"]["sigma0"] - (math.log(ref["g"][0, 0]) +
                                        math.log(ref["g"][1, 1]))) < 1e-12)
    print("  premium.measure agrees with brute force:", ok, rungs)
    return ok


# ------------------------------------------------------------------ (2) the ladder search
def search(premium, n_trials=4000, seed=11):
    rng = np.random.default_rng(seed)
    worst = []
    tied_total = [0]
    for t in range(n_trials):
        n_reps = int(rng.integers(3, 6))
        n_zips = int(rng.integers(3, 8))
        k = int(rng.integers(2, min(4, n_reps) + 1))
        reps = [f"R{i}" for i in range(n_reps)]
        books, M = {}, {}
        for i in range(n_zips):
            z = f"z{i}"
            M[z] = float(rng.uniform(1.0, 40.0))
            hold = rng.choice(n_reps, size=int(rng.integers(1, n_reps + 1)), replace=False)
            raw = rng.uniform(0.02, 1.0, size=len(hold))
            raw = raw / raw.sum() * float(rng.uniform(0.05, 0.95))
            books[z] = {reps[int(h)]: M[z] * float(s) for h, s in zip(hold, raw)}
        to_d = {z: f"D{i % k + 1}" for i, z in enumerate(sorted(books))}
        if len(set(to_d.values())) != k:
            continue
        if len({r for d in books.values() for r in d}) != n_reps:
            continue          # every rep must hold book somewhere: model.reps() drops the rest
        D = sorted(set(to_d.values()))
        hands = [None]
        # a hand roster: any injective map, as the U10 baseline path would supply
        perm = rng.permutation(n_reps)[:k]
        hands.append({d: reps[int(i)] for d, i in zip(D, perm)})
        ties = 0
        for hand in hands:
            ref = reference(books, M, to_d, reps, hand=hand)
            got = premium.measure(graph_from(books, M), to_d, sigma=hand,
                                  theta=THETA, lam=LAM)
            rungs = [got["ladder"][n]["book"]
                     for n in ("P0", "P_star_A", "P_S", "P13", "P_free")]
            # P0 and P_S are evaluated at the roster / staff set the *code* chose, so a
            # tie-broken Nash roster is not counted as a disagreement here; ties are
            # counted separately below.
            b = ref["b"]
            P0_ref = sum(b[reps.index(got["sigma0"][d]), j]
                         for j, d in enumerate(sorted(set(to_d.values()))))
            Sm = np.array([[books[z].get(r, 0.0) for z in sorted(books)] for r in reps])
            P_S_ref = float(Sm[[reps.index(r) for r in got["staff"]]].max(axis=0).sum())
            exp = [P0_ref, ref["P_star"], P_S_ref, ref["P13"], ref["P_free"]]
            if not np.allclose(rungs, exp, rtol=0, atol=1e-9):
                print("MISMATCH vs brute force", t, rungs, exp)
                print("  books =", books, "\n  M =", M)
                print("  to_d =", to_d, "hand =", hand)
                print("  code S13 =", got["staff"], " brute S13 =", ref["S13"])
                print("  code sigma0 =", got["sigma0"], " brute Nash =", ref["nash"])
                return False, None
            if sorted(got["sigma_nash"].values()) != ref["S13"]:
                ties += 1                      # a tied Nash optimum: S13 is not unique
            viol = [(a, b_) for a, b_ in zip(rungs, rungs[1:]) if a > b_ + 1e-9]
            if viol:
                worst.append((t, hand is not None, rungs, books, M, to_d, hand,
                              got["staff"], got["P_star_A_roster"], got["sigma0"],
                              ref["S13"], ref["nash"]))
        tied_total[0] += ties
    print(f"\nladder search: {n_trials} random instances x 2 roster modes, "
          f"brute-force agreement on P*(A), P13, P_free and on P0/P_S at the code's own "
          f"roster/staff")
    print(f"instances where the Nash optimum is tied (S13 not unique): {tied_total[0]}")
    print(f"monotonicity violations: {len(worst)}")
    for w in worst[:6]:
        print("  trial", w[0], "hand roster:", w[1], "rungs", [round(x, 4) for x in w[2]])
        print("    books =", {z: {r: round(v, 4) for r, v in d.items()}
                              for z, d in w[3].items()})
        print("    M =", {z: round(v, 4) for z, v in w[4].items()})
        print("    map", w[5], "sigma0", w[9], "S13", w[7], "P*(A) roster", w[8],
              "brute S13", w[10])
    return True, worst


if __name__ == "__main__":
    premium = load_premium()
    ok = toy_check(premium)
    agree, worst = search(premium)
    sys.exit(0 if (ok and agree) else 1)
