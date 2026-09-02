"""Independent brute-force primitives for U2-stab verification.

Deliberately NOT importing docs/artifacts/U2-stab/stab.py: the claiming implementation
cannot be its own witness.  Matchings are enumerated over all injections J -> I with
itertools.permutations; no scipy, no Hungarian.
"""
import itertools
from fractions import Fraction


def injections(n, k):
    """All injections sigma: {0..k-1} -> {0..n-1}, as tuples sigma[j] = i."""
    return itertools.permutations(range(n), k)


def blocking_pairs(g, sigma):
    """(i,j) blocks sigma iff [i unmatched or g_ij > g_{i,mu(i)}] and g_ij > g_{sigma(j),j}.

    This is the predicate of MODEL_U2-stab.md section 1 verbatim, with H1 built in
    (an unmatched rep prefers any district)."""
    n, k = len(g), len(g[0])
    mu = {i: j for j, i in enumerate(sigma)}
    out = []
    for i in range(n):
        for j in range(k):
            rep_side = (i not in mu) or (g[i][j] > g[i][mu[i]])
            dist_side = g[i][j] > g[sigma[j]][j]
            if rep_side and dist_side:
                out.append((i, j))
    return out


def is_stable(g, sigma):
    return not blocking_pairs(g, sigma)


def stable_set(g):
    n, k = len(g), len(g[0])
    return [s for s in injections(n, k) if is_stable(g, s)]


def greedy(g, tiebreak=None):
    """Greedy top-pair.  Returns (sigma, rounds, h2_holds).

    rounds[r] = (i_r, j_r, unique_argmax).  `tiebreak` picks among argmax cells."""
    n, k = len(g), len(g[0])
    reps, dists = set(range(n)), set(range(k))
    sigma, rounds, h2 = [None]*k, [], True
    while dists:
        cells = [(i, j) for i in sorted(reps) for j in sorted(dists)]
        best = max(g[i][j] for i, j in cells)
        arg = [c for c in cells if g[c[0]][c[1]] == best]
        if len(arg) > 1:
            h2 = False
        i, j = arg[0] if tiebreak is None else tiebreak(arg)
        sigma[j] = i
        rounds.append((i, j, len(arg) == 1))
        reps.discard(i); dists.discard(j)
    return tuple(sigma), rounds, h2


def maxweight(g, phi):
    """All argmax injections for sum_j phi(g_{sigma(j),j}).  Exact when phi returns
    Fraction/int; float only if phi does."""
    best, out = None, []
    for s in injections(len(g), len(g[0])):
        v = sum(phi(g[s[j]][j]) for j in range(len(g[0])))
        if best is None or v > best:
            best, out = v, [s]
        elif v == best:
            out.append(s)
    return out, best


def prod(g, sigma):
    p = Fraction(1)
    for j in range(len(sigma)):
        p *= Fraction(g[sigma[j]][j])
    return p


def logmax(g):
    """Max-weight on logs == max product, done exactly with Fractions (no floats)."""
    best, out = None, []
    for s in injections(len(g), len(g[0])):
        v = prod(g, s)
        if best is None or v > best:
            best, out = v, [s]
        elif v == best:
            out.append(s)
    return out, best
