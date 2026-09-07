"""state_borders.py -- snapping a committed draw's district borders onto state lines.

Track 1 of the borders build (docs/BORDERS_PLAN.md).  The committed k=18 draw is balanced and
compact but its borders only nearly follow state lines: ~9.5% of mass sits in a district whose
*owner set* belongs to another state.  This module moves those borders without redrawing the
map, by re-running `centers.assign` with two changes -- a penalty on crossing a state line and
a band around the equal-mass target -- and re-centroiding, from the committed labels.

Owner sets
----------
`home(j)` is the state holding the plurality of district j's mass; `O(s) = {j : home(j) = s}`,
and when that is empty `O(s)` is the single district holding the most of state s's mass.  A
state with districts of its own is split only among them; a state without one lies wholly
inside one district.  Home-per-district alone is not enough: it would leave VT splittable
between a NY district and a MA district, and the owner set is what closes that.

States enter as an int array, one per zip, with -1 for unknown.  An unknown-state zip has no
owner set, pays no penalty and is never snapped.

Same contract as `centers.py`: pure functions on arrays, no adjacency, no instance file.  The
only Nash step deliberately *not* used here is `centers.improve` -- at lambda > 0 it would pull
zips back across the borders this module just moved, for balance.
"""
from __future__ import annotations

import numpy as np

from td.solvers import centers


def owner_sets(labels: np.ndarray, state_idx: np.ndarray, M: np.ndarray, k: int,
               n_states: int) -> tuple[np.ndarray, np.ndarray]:
    """`(home, owners)`: home state per district `(k,)`, owner districts per state `(n_states, k)`.

    `home[j]` is the state holding the plurality of district j's mass, `-1` when the district
    holds mass only in zips of unknown state (or no mass at all).  `owners[s, j]` is
    `home[j] == s`, except that a state with no home district of its own is given the single
    district holding the most of its mass -- so every state carrying mass has a nonempty owner
    set.  A state with no mass anywhere keeps an all-`False` row: nothing refers to it.

    Ties (two states level in a district, or two districts level in a homeless state) go to the
    lower index, so the result is deterministic.
    """
    labels = np.asarray(labels, int)
    state_idx = np.asarray(state_idx, int)
    M = np.asarray(M, float)
    known = state_idx >= 0

    W = np.zeros((n_states, k), float)                   # mass by state and district
    np.add.at(W, (state_idx[known], labels[known]), M[known])

    home = np.where(W.sum(axis=0) > 0, W.argmax(axis=0), -1).astype(int)
    owners = home[None, :] == np.arange(n_states)[:, None]
    for s in range(n_states):
        if not owners[s].any() and W[s].sum() > 0:       # homeless state: one whole district
            owners[s, int(W[s].argmax())] = True
    return home, owners


def penalty_matrix(state_idx: np.ndarray, owners: np.ndarray,
                   lam_abs: float) -> np.ndarray:
    """`(n, k)` cost added per zip and district: `lam_abs` off the owner set, 0 on it.

    In the units of `d^2`, so `assign` sees `d^2(z, c_j) + lam_abs * 1[j not in O(state(z))]`.
    An unknown-state zip (`state_idx == -1`) has no owner set and its whole row is 0.
    """
    state_idx = np.asarray(state_idx, int)
    owners = np.asarray(owners, bool)
    P = np.zeros((state_idx.size, owners.shape[1]), float)
    known = state_idx >= 0
    P[known] = float(lam_abs) * ~owners[state_idx[known]]
    return P


def pure_snap(xy: np.ndarray, M: np.ndarray, labels: np.ndarray, state_idx: np.ndarray,
              k: int) -> np.ndarray:
    """Move every zip outside its state's owner set to the nearest owner district.

    Owner sets are read off `labels` itself, distances are `d^2` to the M-weighted centroids of
    `labels`, and nothing else moves: unknown-state zips and zips already inside their owner
    set keep their district.  Zero parameters -- this is the baseline that shows what snapping
    alone costs in spread, before any LP.  Returns a copy.
    """
    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    labels = np.asarray(labels, int).copy()
    state_idx = np.asarray(state_idx, int)
    known = state_idx >= 0
    if not known.any():
        return labels

    _, owners = owner_sets(labels, state_idx, M, k, int(state_idx.max()) + 1)
    own = owners[np.where(known, state_idx, 0)]          # (n, k), row meaningless where unknown
    stray = known & ~own[np.arange(labels.size), labels]
    if stray.any():
        d2 = centers._dist2(xy, centers._centroids(xy, M, labels, k))
        labels[stray] = np.where(own[stray], d2[stray], np.inf).argmin(axis=1)
    return labels


def refine(xy: np.ndarray, M: np.ndarray, labels0: np.ndarray, state_idx: np.ndarray, k: int,
           *, lam_rel: float, delta: float, rounds: int = 10) -> dict:
    """Alternate penalised, banded assignment and recentroiding from `labels0`.

    One round is: owner sets from the current labels -> `centers.assign` with the penalty and
    the band `delta` against the current centers -> M-weighted centroids.  Centers start at the
    centroids of `labels0`.  The loop stops early when a labelling repeats any earlier one
    (including `labels0`), which is a 2-cycle or a fixed point; `converged` says whether it did.

    `lam_rel` is a multiple of the *starting* draw's mass-weighted mean `d^2`
    (`compactness(labels0) / sum M`), computed once, so it is scale-free; `lam_rel = 100` is
    effectively hard and crosses a state line only where the band forces it.  At `lam_rel = 0`
    no penalty is passed at all, so a round is exactly `assign`'s Lloyd step.

    `centers.improve` is deliberately never called: at `lam_rel > 0` its Nash-greedy moves would
    pull zips back across the borders this is moving, to buy balance.  Keys: `labels`,
    `centers`, `iterates` (every round's labelling, in order), `rounds_used`, `converged`,
    `n_fractional` (of the last LP) and `metrics` from `centers.metrics`.
    """
    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    labels = np.asarray(labels0, int).copy()
    state_idx = np.asarray(state_idx, int)
    n_states = int(state_idx.max()) + 1 if (state_idx >= 0).any() else 0

    C = centers._centroids(xy, M, labels, k)
    lam_abs = float(lam_rel) * float((M * ((xy - C[labels]) ** 2).sum(axis=1)).sum() / M.sum())

    seen = {labels.tobytes()}
    iterates: list[np.ndarray] = []
    converged, n_fractional = False, 0
    for _ in range(int(rounds)):
        _, owners = owner_sets(labels, state_idx, M, k, n_states)
        pen = penalty_matrix(state_idx, owners, lam_abs) if lam_abs > 0 else None
        labels, n_fractional = centers.assign(xy, M, C, penalty=pen, band=delta)
        labels = np.asarray(labels, int)
        iterates.append(labels.copy())
        C = centers._centroids(xy, M, labels, k, prev=C)
        key = labels.tobytes()
        if key in seen:
            converged = True
            break
        seen.add(key)

    return dict(labels=labels, centers=C, iterates=iterates, rounds_used=len(iterates),
                converged=converged, n_fractional=int(n_fractional),
                metrics=centers.metrics(M, labels, xy, C))
