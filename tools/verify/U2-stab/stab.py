"""U2-stab: greedy top-pair vs Hungarian-on-logs.  All numbers in docs/MODEL_U2-stab.md.

Run from the repo root:
    .venv/bin/python3 docs/artifacts/U2-stab/stab.py

Everything that decides a claim is done in exact integer arithmetic (products and sums of
ints); floats appear only in the Monte-Carlo genericity study (E6) and the FRAME-consistency
arithmetic (E7), and never inside a minimality claim.
"""
import itertools, json, platform, sys
from fractions import Fraction

import numpy as np
import scipy
from scipy.optimize import linear_sum_assignment

SEED = 20260902
OUT = {}


# ---------------------------------------------------------------- primitives
def greedy(g):
    """Greedy top-pair matching on an (n x k) pair-value matrix.

    Returns (sigma, rounds) with sigma[j] = i, and rounds a list of
    (j, i, value, argmax_unique) in the order pairs were fixed.
    """
    n, k = len(g), len(g[0])
    reps, dists = set(range(n)), set(range(k))
    sigma, rounds = {}, []
    while dists:
        best, arg, ties = None, None, 0
        for i in sorted(reps):
            for j in sorted(dists):
                v = g[i][j]
                if best is None or v > best:
                    best, arg, ties = v, (i, j), 1
                elif v == best:
                    ties += 1
        i, j = arg
        sigma[j] = i
        rounds.append(dict(district=j, rep=i, value=str(best), argmax_unique=(ties == 1)))
        reps.discard(i)
        dists.discard(j)
    return sigma, rounds


def hungarian(g, weight):
    """Max-weight matching.  weight='raw' maximises sum g; 'log' maximises sum log g.

    Rectangular: scipy assigns every district (the smaller side) exactly one rep.
    """
    a = np.array(g, dtype=float)
    cost = -a if weight == "raw" else -np.log(a)
    rows, cols = linear_sum_assignment(cost)
    return {int(j): int(i) for i, j in zip(rows, cols)}


def value_exact(g, sigma, weight):
    """Exact objective value of a matching: an int sum, or a Fraction product."""
    if weight == "raw":
        return sum(g[i][j] for j, i in sigma.items())
    p = Fraction(1)
    for j, i in sigma.items():
        p *= Fraction(g[i][j])
    return p


def blocking_pairs(g, sigma):
    """(i, j) blocks sigma iff j is strictly better for i than i's assignment (or i is
    unmatched, individual rationality d_i = 0 < g_ij) and i is strictly better for j
    than j's incumbent."""
    n, k = len(g), len(g[0])
    mu = {i: j for j, i in sigma.items()}
    out = []
    for i in range(n):
        for j in range(k):
            if sigma.get(j) == i:
                continue
            better_for_i = (i not in mu) or g[i][j] > g[i][mu[i]]
            better_for_j = g[i][j] > g[sigma[j]][j]
            if better_for_i and better_for_j:
                out.append((i, j))
    return out


# ------------------------------------------------- E1: minimal log-separating 2x2
def e1():
    """Smallest 2x2 with distinct positive integer entries on which greedy differs from
    Hungarian-on-logs.  Minimised on (max entry, then entry multiset)."""
    for B in range(2, 13):
        found = []
        for cells in itertools.permutations(range(1, B + 1), 4):
            if max(cells) != B:
                continue
            g = [[cells[0], cells[1]], [cells[2], cells[3]]]
            sg, _ = greedy(g)
            sl = hungarian(g, "log")
            if sg != sl:
                found.append(g)
        if found:
            g = found[0]
            sg, _ = greedy(g)
            sl, sr = hungarian(g, "log"), hungarian(g, "raw")
            return dict(min_max_entry=B, n_witnesses_at_that_max=len(found), matrix=g,
                        greedy=sg, log_hungarian=sl, raw_hungarian=sr,
                        greedy_product=str(value_exact(g, sg, "log")),
                        log_hungarian_product=str(value_exact(g, sl, "log")),
                        greedy_sum=value_exact(g, sg, "raw"),
                        raw_hungarian_sum=value_exact(g, sr, "raw"),
                        blocking_pairs_of_log_hungarian=blocking_pairs(g, sl),
                        raw_agrees_with_greedy=(sr == sg))
    return None


# ------------------------------- E2: minimal instance where ONLY the log disagrees
def e2():
    """Smallest 2x2, distinct positive integers, with raw-Hungarian == greedy (a raw-weight
    roster would have been stable) but log-Hungarian != greedy (the delivered objective is
    the log one, and it is unstable)."""
    for B in range(2, 16):
        found = []
        for cells in itertools.permutations(range(1, B + 1), 4):
            if max(cells) != B:
                continue
            g = [[cells[0], cells[1]], [cells[2], cells[3]]]
            sg, _ = greedy(g)
            if hungarian(g, "raw") == sg and hungarian(g, "log") != sg:
                # require a strict raw win for greedy, not a tie
                other = {0: g[1][0] and 1, 1: 0}
                anti = {0: 1, 1: 0} if sg == {0: 0, 1: 1} else {0: 0, 1: 1}
                if value_exact(g, sg, "raw") > value_exact(g, anti, "raw"):
                    found.append(g)
        if found:
            g = found[0]
            sg, _ = greedy(g)
            sl = hungarian(g, "log")
            anti = {0: 1, 1: 0} if sg == {0: 0, 1: 1} else {0: 0, 1: 1}
            return dict(min_max_entry=B, n_witnesses_at_that_max=len(found), matrix=g,
                        greedy=sg, log_hungarian=sl, raw_hungarian=hungarian(g, "raw"),
                        greedy_sum=value_exact(g, sg, "raw"),
                        alternative_sum=value_exact(g, anti, "raw"),
                        greedy_product=str(value_exact(g, sg, "log")),
                        log_hungarian_product=str(value_exact(g, sl, "log")),
                        blocking_pairs_of_log_hungarian=blocking_pairs(g, sl),
                        blocking_pairs_of_raw_hungarian=blocking_pairs(g, hungarian(g, "raw")))
    return None


# ------------------------------- E1b: minimal STRICT raw-weight separation
def e1b():
    """Smallest 2x2, distinct positive integers, on which greedy differs from
    Hungarian-on-raw-weights with a STRICT margin (no sum tie).  The raw-weight form of
    the counterexample."""
    for B in range(2, 16):
        found = []
        for cells in itertools.permutations(range(1, B + 1), 4):
            if max(cells) != B:
                continue
            g = [[cells[0], cells[1]], [cells[2], cells[3]]]
            sg, _ = greedy(g)
            anti = {0: 1, 1: 0} if sg == {0: 0, 1: 1} else {0: 0, 1: 1}
            if value_exact(g, anti, "raw") > value_exact(g, sg, "raw"):
                found.append(g)
        if found:
            g = found[0]
            sg, _ = greedy(g)
            sr, sl = hungarian(g, "raw"), hungarian(g, "log")
            return dict(min_max_entry=B, n_witnesses_at_that_max=len(found), matrix=g,
                        greedy=sg, raw_hungarian=sr, log_hungarian=sl,
                        greedy_sum=value_exact(g, sg, "raw"),
                        raw_hungarian_sum=value_exact(g, sr, "raw"),
                        greedy_product=str(value_exact(g, sg, "log")),
                        log_hungarian_product=str(value_exact(g, sl, "log")),
                        blocking_pairs_of_raw_hungarian=blocking_pairs(g, sr),
                        blocking_pairs_of_log_hungarian=blocking_pairs(g, sl),
                        log_also_separates=(sl != sg))
    return None


# ---------------------- E3: is the reverse separation possible?  (Proposition 5)
def e3(bound=40, trials=400000, dims=(3, 4, 5)):
    """Prop 5 says: on 2x2, log-Hungarian == greedy implies raw-Hungarian == greedy.
    (a) exhaustive check on all 2x2 positive-integer matrices with entries <= bound;
    (b) random search for an n x n counterexample at n = 3, 4, 5, keeping the first
        witness found at each n (Prop 5 is claimed for 2x2 only)."""
    exhaustive_violations, checked = 0, 0
    for cells in itertools.product(range(1, bound + 1), repeat=4):
        g = [[cells[0], cells[1]], [cells[2], cells[3]]]
        sg, rounds = greedy(g)
        if not all(r["argmax_unique"] for r in rounds):
            continue                      # uniqueness hypothesis fails; excluded by Prop 5
        checked += 1
        if hungarian(g, "log") == sg and hungarian(g, "raw") != sg:
            exhaustive_violations += 1
    rng = np.random.default_rng(SEED)
    rand = {}
    for n in dims:
        viol, witness = 0, None
        for _ in range(trials // len(dims)):
            g = rng.integers(1, 10 ** 4, size=(n, n)).tolist()
            sg, rounds = greedy(g)
            if not all(r["argmax_unique"] for r in rounds):
                continue
            if hungarian(g, "log") == sg and hungarian(g, "raw") != sg:
                viol += 1
                if witness is None:
                    witness = dict(matrix=g, greedy=sg, log_hungarian=hungarian(g, "log"),
                                   raw_hungarian=hungarian(g, "raw"),
                                   greedy_sum=value_exact(g, sg, "raw"),
                                   raw_hungarian_sum=value_exact(
                                       g, hungarian(g, "raw"), "raw"),
                                   blocking_pairs_of_raw_hungarian=blocking_pairs(
                                       g, hungarian(g, "raw")))
        rand[f"n={n}"] = dict(trials=trials // len(dims), violations=viol, witness=witness)
    return dict(exhaustive_bound=bound, exhaustive_matrices_checked=checked,
                exhaustive_violations=exhaustive_violations, random=rand)


# ------------- E4: can an UNMATCHED rep block a max-weight roster?  (Proposition 6)
def e4(bound=6, n=3, k=2):
    """Proposition 6: a max-weight matching (raw or log) admits no blocking pair whose rep
    is unmatched -- swapping the unmatched rep in would strictly raise the objective.
    Exhaustive over all n x k matrices with entries in 1..bound, for both weights.
    Also returns the minimal witness on which the LOG max-weight roster is unstable, to
    show that matched-matched blocking pairs do survive."""
    unmatched_block = {"raw": 0, "log": 0}
    any_block = {"raw": 0, "log": 0}
    total = 0
    witness = None
    for cells in itertools.product(range(1, bound + 1), repeat=n * k):
        g = [list(cells[r * k:(r + 1) * k]) for r in range(n)]
        total += 1
        sg, _ = greedy(g)
        for w in ("raw", "log"):
            s = hungarian(g, w)
            bp = blocking_pairs(g, s)
            matched = set(s.values())
            if bp:
                any_block[w] += 1
            if any(i not in matched for (i, j) in bp):
                unmatched_block[w] += 1
        sl = hungarian(g, "log")
        if witness is None and sl != sg and blocking_pairs(g, sl):
            witness = dict(matrix=g, greedy=sg, log_hungarian=sl,
                           raw_hungarian=hungarian(g, "raw"),
                           greedy_product=str(value_exact(g, sg, "log")),
                           log_hungarian_product=str(value_exact(g, sl, "log")),
                           blocking_pairs=blocking_pairs(g, sl),
                           unmatched_reps=sorted(set(range(n)) - set(sl.values())),
                           blocking_pairs_with_unmatched_rep=[
                               (i, j) for (i, j) in blocking_pairs(g, sl)
                               if i not in set(sl.values())])
    return dict(shape=[n, k], entry_bound=bound, matrices_checked=total,
                rosters_with_any_blocking_pair=any_block,
                rosters_with_an_unmatched_rep_blocking_pair=unmatched_block,
                minimal_unstable_log_witness=witness)


# -------------------------- E5: structured toy -- ties from the common baseline B_j
def e5():
    """g_ij = B_j + w * b_ij, the exact form of td/channel.py:gain_matrix (a district-wide
    constant plus (c1-c2) times rep i's book inside the district).  Integer arithmetic:
    B_j and b_ij integers, w = 42 (= 100*(c1-c2) at the reference theta=0.40, lam=0.30).

    Shows (i) exact ties are structural, not measure-zero, and (ii) the uniqueness
    hypothesis that actually matters is per-round argmax uniqueness, which can hold
    despite thousands of ties.
    """
    rng = np.random.default_rng(SEED)
    n, k, w = 111, 13, 42
    B = (rng.integers(900, 1100, size=k) * 1000).tolist()          # district baselines
    b = np.zeros((n, k), dtype=np.int64)
    for i in range(n):                       # each rep holds book in 1-3 districts
        for j in rng.choice(k, size=int(rng.integers(1, 4)), replace=False):
            b[i, j] = int(rng.integers(1, 12000))
    g = (np.array(B)[None, :] + w * b).astype(np.int64).tolist()

    zero_book_pairs = int((b == 0).sum())
    # count exact ties: pairs (i,i') tying on some district j
    ties = 0
    for j in range(k):
        col = [row[j] for row in g]
        seen = {}
        for v in col:
            seen[v] = seen.get(v, 0) + 1
        ties += sum(c * (c - 1) // 2 for c in seen.values() if c > 1)

    sg, rounds = greedy(g)
    sl, sr = hungarian(g, "log"), hungarian(g, "raw")
    bp = blocking_pairs(g, sl)
    return dict(n=n, k=k, w=w, exact_ties_within_a_district_column=ties,
                zero_book_rep_district_pairs=zero_book_pairs,
                all_g_distinct=(ties == 0),
                per_round_argmax_unique=all(r["argmax_unique"] for r in rounds),
                greedy_equals_log_hungarian=(sg == sl),
                greedy_equals_raw_hungarian=(sg == sr),
                blocking_pairs_of_log_hungarian=len(bp),
                first_deviation_round=next((r for r, rd in enumerate(rounds)
                                            if sl.get(rd["district"]) != rd["rep"]), None),
                first_deviation_pair=_dev_pair(rounds, sl),
                first_deviation_pair_blocks=(_dev_pair(rounds, sl) in
                                             [list(p) for p in bp] or
                                             tuple(_dev_pair(rounds, sl) or ()) in
                                             [tuple(p) for p in bp]),
                blocking_pair_list=bp,
                stable_matching_unique=all(r["argmax_unique"] for r in rounds))


def _dev_pair(rounds, s):
    """(rep, district) of the first greedy round at which matching s deviates."""
    for rd in rounds:
        if s.get(rd["district"]) != rd["rep"]:
            return [rd["rep"], rd["district"]]
    return None


def e5b(reps=200):
    """E5's structured generator over many seeds: how often does greedy coincide with
    Hungarian-on-logs under a common-baseline-plus-sparse-book pair value?  The sparsity
    and magnitudes are INVENTED -- this illustrates the mechanism, it does not forecast N3."""
    n, k, w = 111, 13, 42
    agree = uniq = 0
    bps = []
    for t in range(reps):
        rng = np.random.default_rng(SEED + 1000 + t)
        B = (rng.integers(900, 1100, size=k) * 1000).tolist()
        b = np.zeros((n, k), dtype=np.int64)
        for i in range(n):
            for j in rng.choice(k, size=int(rng.integers(1, 4)), replace=False):
                b[i, j] = int(rng.integers(1, 12000))
        g = (np.array(B)[None, :] + w * b).astype(np.int64).tolist()
        sg, rounds = greedy(g)
        sl = hungarian(g, "log")
        uniq += all(r["argmax_unique"] for r in rounds)
        if sg == sl:
            agree += 1
        bps.append(len(blocking_pairs(g, sl)))
    return dict(replicates=reps, greedy_eq_log_hungarian=agree,
                frac_greedy_eq_log=agree / reps,
                per_round_argmax_unique_all=uniq,
                blocking_pairs_mean=float(np.mean(bps)),
                blocking_pairs_max=int(max(bps)),
                blocking_pairs_zero_count=int(sum(1 for x in bps if x == 0)))


# ----------------------------------- E6: genericity of greedy != log max-weight
def e6(trials=20000):
    """Fraction of iid-random pair-value matrices on which greedy coincides with
    Hungarian-on-logs.  A statement about generic matrices, NOT a forecast of N3 -- the
    real g matrix is far from iid (see E5)."""
    rng = np.random.default_rng(SEED + 1)
    out = {}
    for (n, k) in [(2, 2), (4, 2), (13, 13), (111, 13)]:
        agree_log = agree_raw = 0
        t = trials if n * k <= 200 else trials // 20
        for _ in range(t):
            g = rng.uniform(0.5, 1.5, size=(n, k))
            gl = [list(map(float, r)) for r in g]
            sg, _ = greedy(gl)
            if sg == hungarian(gl, "log"):
                agree_log += 1
            if sg == hungarian(gl, "raw"):
                agree_raw += 1
        out[f"{n}x{k}"] = dict(trials=t, greedy_eq_log_hungarian=agree_log,
                               frac_greedy_eq_log=agree_log / t,
                               greedy_eq_raw_hungarian=agree_raw,
                               frac_greedy_eq_raw=agree_raw / t)
    return out


def e6c(trials=4000, k=13, ns=(13, 20, 30, 50, 80, 111)):
    """Agreement between greedy and Hungarian-on-logs as the rep:district ratio grows,
    iid U(0.5, 1.5) pair values, k = 13 fixed.  Isolates SLACK as the mechanism that makes
    the delivered roster more likely to be stable than the square-market intuition says."""
    rng = np.random.default_rng(SEED + 2)
    out = {}
    for n in ns:
        agree, bp = 0, []
        for _ in range(trials):
            g = [list(map(float, r)) for r in rng.uniform(0.5, 1.5, size=(n, k))]
            sg, _ = greedy(g)
            sl = hungarian(g, "log")
            if sg == sl:
                agree += 1
            bp.append(len(blocking_pairs(g, sl)))
        out[f"n={n}"] = dict(trials=trials, frac_greedy_eq_log=agree / trials,
                             blocking_pairs_mean=float(np.mean(bp)),
                             blocking_pairs_max=int(max(bp)))
    return out


# ------------------------- E7: FRAME §6 consistency -- the size of the rep-dependent term
def e7():
    """c1 - c2 at the FRAME §6 reference parameters, and the hold-vs-not swing it implies
    at the measured aggregate saturation.  Checks that the rep-dependent part of g is a
    first-order term, not a perturbation (which is what keeps P1 non-vacuous)."""
    theta, lam, tau = 0.40, 0.30, 0.419        # FRAME §6 / CLAUDE.md reference values
    c1, c2 = 1 - lam, theta * (1 - lam)
    swing = (c1 - c2) * tau / (c2 * tau + lam)
    return dict(theta=theta, lam=lam, saturation_tau=tau,
                c1=c1, c2=c2, c1_minus_c2=c1 - c2,
                hold_vs_not_swing=swing,
                frame_s6_reported_swing=0.42,
                abs_diff_vs_frame=abs(swing - 0.42),
                degenerate_at=dict(theta_eq_1=True, lam_eq_1=True))


if __name__ == "__main__":
    OUT["meta"] = dict(seed=SEED, python=sys.version.split()[0], numpy=np.__version__,
                       scipy=scipy.__version__, platform=platform.platform(),
                       command="/Users/ntlee/projects/td/.venv/bin/python3 "
                               "docs/artifacts/U2-stab/stab.py")
    OUT["E1_minimal_log_separating"] = e1()
    OUT["E1b_minimal_raw_separating"] = e1b()
    OUT["E2_minimal_log_only_separating"] = e2()
    OUT["E3_reverse_separation_search"] = e3()
    OUT["E4_unmatched_cannot_block"] = e4()
    OUT["E5_structured_toy"] = e5()
    OUT["E5b_structured_replicates"] = e5b()
    OUT["E6_genericity"] = e6()
    OUT["E6c_slack_sweep"] = e6c()
    OUT["E7_frame_consistency"] = e7()
    print(json.dumps(OUT, indent=2, default=str))
