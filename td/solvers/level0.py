"""level0.py -- the channel-plan MILP at state x channel grain (docs/FULL_PROBLEM.md section 5).

Cells are `(s, c)`, S states by C fine channels.  A bundle `B` is a set of channels served
together; each bundle gets `K_B = ceil(M^max_B / L)` slots, `M^max_B` being every unit of mass
the bundle could hold, so the bundle of a slot is fixed and there are no bundle binaries.
`W_sj = sum_{c in B_j} M_sc` is the mass state `s` puts into slot `j` per unit share::

    y_sj in [0, 1]    share of state s in slot j (every channel of B_j alike)
    z_sj in {0, 1}    contact,  eta z_sj <= y_sj <= z_sj <= u_j
    u_j  in {0, 1}    slot used
    cover:   sum_{j : c in B_j} y_sj <= cover_ub_sc = 1 - prior_sc        for every (s, c)
    band:    (L_j/tau) u_j <= sum_s (W_sj/tau) y_sj <= (U_j/tau) u_j      for every j,
             `L_j`, `U_j` the slot's own bundle's band (`build_level0(band=...)`)
    flow:    single-commodity flow per slot as level 1, root  sum_s r_sj = u_j
    caps:    sum_s z_sj <= n_max;  z_sj + z_s'j <= 1 when |xy_s - xy_s'| > dist_max
    radius:  z_sj = 0 when |xy_s - xy_root(j)| > radius_max, or the pair rows at 2 radius_max
             on a slot whose root is not known
    order:   u_j >= u_{j+1}  and  mass_j >= mass_{j+1}  inside each J_B  (symmetry)

The residual per cell, `cover_ub - sum_j y_sj`, is what `decode_zy` reports as "other".
`Level0Problem` subclasses `state_splits.SplitProblem`: the `z`, `y`, `r`, `f` blocks keep
their layout with `k = K`, and a fifth block `u` of length `K` follows the flow, so every
engine in `milp_engines` (`_decode_x`, `fix_roots`, `with_cutoff`, the warm starts) reads a
`Level0Problem` unchanged.  `tau = (L + U) / 2`, so the band rows read `1 -/+ delta` exactly
as level 1's, with `delta = (U - L) / (L + U)`.

Objectives are passes (`Pass`), solved lexicographically by `solve_passes` in the
`balance_pass` pattern: solve, pin the value with one appended row, move to the next objective.
`cover_pass` maximises covered mass in a set of bundles, `contacts_pass` minimises `sum z` (the
level-1 objective), `compactness_pass` adds the `eps W D y` tie-break.

A cell with `cover_ub_sc < eta` cannot be contacted by any slot whose bundle contains `c`:
`eta z <= y <= cover_ub` forces `z = 0`.  This is intended.  A state fully committed by an
earlier route-S solve can neither be served again nor bridge two slots of that bundle.
"""
from __future__ import annotations

import dataclasses
import math
import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np
from scipy import sparse

from td.solvers import state_splits as ss
from td.solvers.state_splits import SplitProblem, _block


@dataclass
class Level0Problem(SplitProblem):
    """`SplitProblem` plus the slot block and the cell bookkeeping.

    `u_j` sits at `off_u + j`.  `W` is `(S, K)`, `bundle_of[j]` names slot `j`'s bundle,
    `slots[B] = (start, stop)` is its slot range, `slot_has[j, ci]` says whether slot `j`'s
    bundle contains channel `ci`, `cover_ub = 1 - prior` is `(S, C)`.  The inherited `M_s` is
    each state's mass summed over every channel and `D` is `(S, K)` (zeros without centres).

    `L` and `U` are the global band and `L_j`, `U_j` `(K,)` the band each slot is actually
    held to, which differs from it once a bundle is banded on its own mean.

    `state_xy (S, 2)` is the geometry the distance caps measure in (empty without one),
    `slot_root[j]` the state slot `j` is rooted at (`-1` when no single anchor names one) and
    `radius_max` the cap that geometry carries, so `greedy_plan` and `check_point` can read
    back what the bounds mean rather than re-deriving it.

    `state_list` is `cells.state_list`, in the same order as every state index here: what
    `max_splits` resolves a state code against.
    """

    off_u: int = 0
    W: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    bundle_of: tuple[str, ...] = ()
    slots: dict[str, tuple[int, int]] = field(default_factory=dict)
    slot_has: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))
    L: float = 0.0
    U: float = 0.0
    L_j: np.ndarray = field(default_factory=lambda: np.zeros(0))
    U_j: np.ndarray = field(default_factory=lambda: np.zeros(0))
    cover_ub: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    prior: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    channels: tuple[str, ...] = ()
    bundles: dict[str, tuple[str, ...]] = field(default_factory=dict)
    state_xy: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    slot_root: tuple[int, ...] = ()
    radius_max: float | None = None
    state_list: tuple[str, ...] = ()

    def decode_zy(self, z: np.ndarray, y: np.ndarray) -> dict:
        """`z`, `y` -> masses per slot `(W * y).sum(0)`, `used` (a used slot has a contact,
        since `L > 0`), `covered` and `residual` per cell, `contacts = sum z`, and
        `splits = contacts - n_state` so `milp_engines.with_cutoff`'s row reads "fewer
        contacts".  `y` is zeroed where `z` is 0 and clipped, never renormalised: the cover
        row is an inequality.  `spread_rel` and `max_dev_rel` are over used slots (nan when
        none is used) so a level-1 reader of the result does not break."""
        S, K = self.n_state, self.k
        z = np.asarray(z, bool).reshape(S, K)
        y = np.clip(np.asarray(y, float).reshape(S, K), 0.0, 1.0)
        y = np.where(z, y, 0.0)
        masses = (self.W * y).sum(axis=0)
        used = z.any(axis=0)
        covered = y @ self.slot_has.astype(float)
        residual = np.clip(self.cover_ub - covered, 0.0, None)
        contacts = int(z.sum())
        m = masses[used]
        return dict(
            z=z, y=y, masses=masses, used=used, covered=covered, residual=residual,
            contacts=contacts, splits=contacts - S,
            spread_rel=float((m.max() - m.min()) / m.mean()) if used.any() else float("nan"),
            max_dev_rel=(float(np.abs(m - self.tau).max() / self.tau) if used.any()
                         else float("nan")),
        )


@dataclass
class Pass:
    """One objective: `c` over `n_var`, `sense` `"min"` or `"max"`.

    `slack` widens the pin `solve_passes` writes after the pass by `|v| * slack`, so a later
    pass may give up that fraction of this one's value.  On a maximisation, whose minimised
    value is `-value`, that is exactly `v (1 - slack)`.  The default 0.0 pins the value.
    """

    name: str
    c: np.ndarray
    sense: str = "min"
    slack: float = 0.0


def _cover_ub(shape: tuple[int, int], prior) -> np.ndarray:
    if prior is None:
        return np.ones(shape)
    prior = np.asarray(prior, float)
    if prior.shape != shape:
        raise ValueError(f"prior must be {shape}, got {prior.shape}")
    return np.clip(1.0 - prior, 0.0, 1.0)


def _channel_index(channels: tuple[str, ...], bundles: dict) -> dict[str, list[int]]:
    out = {}
    for name, chans in bundles.items():
        if not chans:
            raise ValueError(f"bundle {name!r} is empty")
        missing = [c for c in chans if c not in channels]
        if missing:
            raise ValueError(f"bundle {name!r} names channels {missing} not in {channels}")
        out[name] = [channels.index(c) for c in chans]
    return out


def available_mass(cells, bundles: dict, *, prior=None) -> dict[str, float]:
    """`M^max_B = sum_s sum_{c in B} M_sc cover_ub_sc` per bundle: all the mass the bundle
    could ever hold once `prior` is committed.  The driver divides it by a fixed slot count to
    get that bundle's own band centre."""
    M = np.asarray(cells.M, float)
    cover_ub = _cover_ub(M.shape, prior)
    idx = _channel_index(tuple(cells.channels), bundles)
    return {name: float((M[:, cols] * cover_ub[:, cols]).sum()) for name, cols in idx.items()}


def _band_of(bundles: dict, L: float, U: float, band) -> dict[str, tuple[float, float]]:
    """`{bundle: (L_B, U_B)}`: the global pair everywhere, then whatever `band` overrides.

    `band` is None, a `(L, U)` pair (the same thing as the `L` and `U` arguments), or a dict
    naming some or all of the bundles; a bundle it does not name keeps the global pair.
    """
    out = {name: (float(L), float(U)) for name in bundles}
    if band is not None and not isinstance(band, dict):
        lo, hi = band
        out = {name: (float(lo), float(hi)) for name in bundles}
    elif band:
        unknown = [b for b in band if b not in out]
        if unknown:
            raise ValueError(f"band names bundle(s) {unknown} not in {list(bundles)}")
        out.update({name: (float(lo), float(hi)) for name, (lo, hi) in band.items()})
    for name, (lo, hi) in out.items():
        if not (0.0 < lo <= hi):
            raise ValueError(f"bundle {name!r} needs 0 < L <= U, got L={lo}, U={hi}")
    return out


def slot_counts(cells, bundles: dict, *, L: float, prior=None, band=None) -> dict[str, int]:
    """`K_B = ceil(M^max_B / L_B)` per bundle, `M^max_B` the mass it could hold once `prior` is
    committed (`available_mass`).  Zero when there is none.  `band` gives a bundle its own
    `(L_B, U_B)`; without one every bundle divides by the global `L`.  The driver prints these
    before building: the slot count is the size lever."""
    pairs = _band_of(bundles, L, float("inf"), band)      # no upper bound counts slots
    counts = {}
    for name, avail in available_mass(cells, bundles, prior=prior).items():
        counts[name] = (int(math.ceil(avail / pairs[name][0] - 1e-9)) if avail > 0 else 0)
    return counts


def build_level0(cells, bundles: dict, *, edges: list[tuple[int, int]], L: float, U: float | None,
                 eta: float, band=None, tau: float | None = None, n_max: int | None = None,
                 dist_max: float | None = None, radius_max: float | None = None,
                 state_xy=None, prior=None, anchors=None,
                 D=None, eps: float | None = None,
                 order_mass: bool | None = None,
                 fixed_used: dict[str, int] | None = None,
                 max_used: dict[str, int] | None = None,
                 dist_max_state: dict[int, float] | None = None) -> Level0Problem:
    """Assemble the level-0 MILP.  `cells` carries `M (S, C)`, `channels` and `state_list`
    (`td.channels.CellTable`, duck-typed); `bundles` maps a name to a tuple of channels;
    `edges` is the state rook graph over indices `0..S-1`, undirected, once per pair.

    `U` is required: without an upper band the coverage passes build one giant district per
    bundle and balance is undefined.  `tau` defaults to `(L + U) / 2`.

    `band` gives a bundle its own band: `None` (every bundle takes `(L, U)`), a `(L, U)` pair,
    or a dict `bundle -> (L_B, U_B)` for some or all of them.  The band rows are per slot
    already, so each slot takes its bundle's pair, and `L_j`, `U_j` `(K,)` carry them; `L` and
    `U` stay the global pair.  A bundle's mean district is its own mass over its own count once
    the counts differ across bundles (national 10-18, WH 9-12, FI 16-20), and one global `tau`
    would band them all at the national mean.  `tau` itself stays global: it scales the band
    rows and nothing else.

    `prior (S, C)` is the
    share already committed by an earlier solve; `cover_ub = 1 - prior`.  `anchors` is a list
    of `(s, j)` pairs (or a dict `s -> j`) forced to `z_sj = 1`, as `build_milp`.  `D (S, K)`
    are per-slot moments; `eps` defaults to `eps_lexicographic` on the state totals and `D`.
    The default objective `c` is the contacts pass plus the `eps W D y` tie-break.

    Ordering rows are valid only while the slots inside a `J_B` are interchangeable.
    `u_j >= u_{j+1}` always holds up under a relabelling and is always added.  The mass
    ordering `mass_j >= mass_{j+1}` is not: an anchor names a slot, and an anchored slot
    heavier than a lower-indexed one makes the row infeasible (the route-S regression carries
    committed homes), and a `D` that differs across a bundle's slots names them too.  So
    `order_mass` defaults to on only when neither `anchors` nor `D` is given; any later
    per-slot fix (`bound_z`, `fix_roots`, a neighbourhood z-fix) needs it off as well.  A
    `radius_max` bound is per-slot too, and it only ever appears with an anchor, so it is off
    by the same rule.
    `forbid_bundle` is uniform across a bundle's slots and is compatible with both orderings.

    `radius_max` caps how far a slot reaches from its own root, in `state_xy`'s units.  A slot
    named by exactly one anchor is rooted there, and every state farther than `radius_max` from
    that root gets `z_sj` (and `y_sj`) bounded to zero: a bound, not a row, so presolve drops
    the variable outright.  A slot with no anchor, or with several, has no known root, and a
    free root allows a diameter rather than a radius: those slots take the `cap_dist` pair rows
    at `2 radius_max` instead.  `dist_max` still applies to every slot, so a slot's pair
    threshold is the tighter of the two.

    `dist_max_state` maps a state index to its own km and relaxes `dist_max` pair by pair: a
    pair `(a, b)` may share a slot up to `max(dist_max, dist_max_state[a], dist_max_state[b])`
    apart, so one sparse state can reach further without loosening the cap between every
    other pair.  It never tightens `dist_max` and needs it; the radius rule above still takes
    the tighter of the pair's threshold and `2 radius_max` on a rootless slot.  Unset, every
    row is what it was.

    `fixed_used` maps a bundle name to a count: the first `count` slots of that bundle get
    `u_j` fixed at 1, so the passes must use them (a count above the bundle's slot count is
    refused).  The `u` ordering row between a fixed slot and the next is dropped, since
    `u_{j+1} <= 1` says nothing; a bundle not named stays free.  `max_used` maps a bundle
    name to a ceiling: every slot of that bundle past the first `count` gets `u_j` bounded to
    zero, so the passes use at most `count` of them and drop districts where a cap binds
    rather than fail; a bundle may carry both a floor and a ceiling.
    """
    if U is None:
        raise ValueError("build_level0 needs an upper band U: without one the coverage passes "
                         "build one giant district per bundle")
    L, U = float(L), float(U)
    if not (0.0 < L <= U):
        raise ValueError(f"need 0 < L <= U, got L={L}, U={U}")
    tau = (L + U) / 2.0 if tau is None else float(tau)
    if tau <= 0:
        raise ValueError("tau must be positive")
    M = np.asarray(cells.M, float)
    if M.ndim != 2:
        raise ValueError(f"cells.M must be (S, C), got {M.shape}")
    S, C = M.shape
    channels = tuple(cells.channels)
    if len(channels) != C:
        raise ValueError(f"cells.channels has {len(channels)} names for {C} columns")
    N = S
    E = [(int(u), int(v)) for u, v in edges]
    if any(u == v or not (0 <= u < S) or not (0 <= v < S) for u, v in E):
        raise ValueError("edges must be distinct state indices in range")
    n_arc = 2 * len(E)
    cover_ub = _cover_ub((S, C), prior)
    prior_arr = np.zeros((S, C)) if prior is None else np.asarray(prior, float)
    idx = _channel_index(channels, bundles)
    pairs_b = _band_of(bundles, L, U, band)
    counts = slot_counts(cells, bundles, L=L, prior=prior, band=pairs_b)
    # a ceiling below the count trims the bundle's slots at build time rather than closing
    # them afterwards, so a tiny floor (the all-channel stage over what is left) does not
    # build thousands of slots it can never use
    for name, count in (max_used or {}).items():
        if name in counts and int(count) >= 0:
            counts[name] = min(counts[name], int(count))

    # slots: contiguous ranges per bundle, in the order `bundles` lists them
    slots, bundle_of, start = {}, [], 0
    for name in bundles:
        slots[name] = (start, start + counts[name])
        bundle_of.extend([name] * counts[name])
        start += counts[name]
    K = start
    bundle_of = tuple(bundle_of)
    L_j = np.array([pairs_b[name][0] for name in bundle_of], float)
    U_j = np.array([pairs_b[name][1] for name in bundle_of], float)
    slot_has = np.zeros((K, C), bool)
    for j, name in enumerate(bundle_of):
        slot_has[j, idx[name]] = True
    W = M @ slot_has.T.astype(float)                       # (S, K)

    if D is None:
        D = np.zeros((S, K))
    D = np.asarray(D, float)
    if D.shape != (S, K):
        raise ValueError(f"D must be {(S, K)}, got {D.shape}")
    M_tot = M.sum(axis=1)
    if K == 0:
        raise ValueError("no slots: every bundle's available mass is below L, so there is "
                         "nothing to plan; skip the stage rather than building it")
    if eps is None:
        eps = ss.eps_lexicographic(M_tot, D) if (M_tot * D.max(axis=1)).sum() > 0 else 0.0
    if order_mass is None:
        order_mass = anchors is None and not D.any()
    if n_max is not None and int(n_max) < 1:
        raise ValueError(f"n_max must be at least 1, got {n_max}")
    if dist_max is not None and state_xy is None:
        raise ValueError("dist_max needs state_xy")
    if radius_max is not None and state_xy is None:
        raise ValueError("radius_max needs state_xy")
    if dist_max_state and dist_max is None:
        raise ValueError("dist_max_state relaxes dist_max per state and needs it")
    for s in (dist_max_state or {}):
        if not 0 <= int(s) < S:
            raise ValueError(f"dist_max_state names state {s}, out of range")
    pairs_a = list(anchors.items()) if isinstance(anchors, dict) else list(anchors or ())
    for s, j in pairs_a:
        if not (0 <= s < S and 0 <= j < K):
            raise ValueError(f"anchor ({s}, {j}) out of range")
    # a slot named by exactly one anchor is rooted there; several anchors name a contact set,
    # not a root, so that slot is treated as rootless
    anchored_on: dict[int, list[int]] = {}
    for s, j in pairs_a:
        anchored_on.setdefault(int(j), []).append(int(s))
    root_of = np.full(K, -1, int)
    for j, states in anchored_on.items():
        if len(states) == 1:
            root_of[j] = states[0]
    fixed_slots: list[int] = []
    for name, count in (fixed_used or {}).items():
        if name not in slots:
            raise ValueError(f"fixed_used names bundle {name!r} not in {list(slots)}")
        lo_j, hi_j = slots[name]
        if not (0 <= int(count) <= hi_j - lo_j):
            raise ValueError(f"fixed_used[{name!r}] = {count} exceeds the bundle's "
                             f"{hi_j - lo_j} slot(s)")
        fixed_slots.extend(range(lo_j, lo_j + int(count)))
    closed_slots: list[int] = []
    for name, count in (max_used or {}).items():
        if name not in slots:
            raise ValueError(f"max_used names bundle {name!r} not in {list(slots)}")
        lo_j, hi_j = slots[name]
        if int(count) < 0:
            raise ValueError(f"max_used[{name!r}] = {count} is negative")
        closed_slots.extend(range(lo_j + int(count), hi_j))
    if set(closed_slots) & set(fixed_slots):
        raise ValueError("a slot is both fixed used and closed: max_used below fixed_used")

    off_z, off_y, off_r = 0, S * K, 2 * S * K
    off_f = 3 * S * K
    off_u = off_f + n_arc * K
    n_var = off_u + K

    c = np.zeros(n_var)
    c[off_z:off_z + S * K] = 1.0
    c[off_y:off_y + S * K] = float(eps) * (W * D).ravel()

    sk = np.arange(S * K)
    j_of = np.tile(np.arange(K), S)                      # slot of flat (s, j)
    jk = np.arange(K)

    blocks, lb, ub, rows = [], [], [], {}

    def add(name, mat, lo, hi):
        start = sum(b.shape[0] for b in blocks)
        blocks.append(mat)
        lb.append(np.asarray(lo, float))
        ub.append(np.asarray(hi, float))
        rows[name] = (start, start + mat.shape[0])

    # sum_{j : c in B_j} y_sj <= cover_ub_sc
    jj, cc = np.nonzero(slot_has)
    add("cover", _block((np.arange(S)[:, None] * C + cc[None, :]).ravel(),
                        (off_y + np.arange(S)[:, None] * K + jj[None, :]).ravel(),
                        np.ones(S * len(jj)), S * C, n_var),
        np.full(S * C, -np.inf), cover_ub.ravel())
    # y_sj - z_sj <= 0
    add("yz", _block(np.concatenate([sk, sk]),
                     np.concatenate([off_y + sk, off_z + sk]),
                     np.concatenate([np.ones(S * K), -np.ones(S * K)]), S * K, n_var),
        np.full(S * K, -np.inf), np.zeros(S * K))
    # eta z_sj - y_sj <= 0
    add("yz_lo", _block(np.concatenate([sk, sk]),
                        np.concatenate([off_z + sk, off_y + sk]),
                        np.concatenate([np.full(S * K, float(eta)), -np.ones(S * K)]),
                        S * K, n_var),
        np.full(S * K, -np.inf), np.zeros(S * K))
    # z_sj - u_j <= 0
    add("zu", _block(np.concatenate([sk, sk]),
                     np.concatenate([off_z + sk, off_u + j_of]),
                     np.concatenate([np.ones(S * K), -np.ones(S * K)]), S * K, n_var),
        np.full(S * K, -np.inf), np.zeros(S * K))
    # sum_s (W_sj/tau) y_sj - (L_j/tau) u_j >= 0   and   ... - (U_j/tau) u_j <= 0
    for name, bound, lo, hi in (("band_lo", L_j, 0.0, np.inf), ("band_hi", U_j, -np.inf, 0.0)):
        add(name, _block(np.concatenate([j_of, jk]),
                         np.concatenate([off_y + sk, off_u + jk]),
                         np.concatenate([W.ravel() / tau, -bound / tau]),
                         K, n_var),
            np.full(K, lo), np.full(K, hi))
    # sum_s r_sj - u_j = 0
    add("root", _block(np.concatenate([j_of, jk]),
                       np.concatenate([off_r + sk, off_u + jk]),
                       np.concatenate([np.ones(S * K), -np.ones(K)]), K, n_var),
        np.zeros(K), np.zeros(K))
    # r_sj - z_sj <= 0
    add("rz", _block(np.concatenate([sk, sk]),
                     np.concatenate([off_r + sk, off_z + sk]),
                     np.concatenate([np.ones(S * K), -np.ones(S * K)]), S * K, n_var),
        np.full(S * K, -np.inf), np.zeros(S * K))

    tails = np.array([e[i] for e in E for i in (0, 1)], int) if E else np.zeros(0, int)
    heads = np.array([e[1 - i] for e in E for i in (0, 1)], int) if E else np.zeros(0, int)
    arc_flat = np.arange(n_arc * K)
    arc_of = np.repeat(np.arange(n_arc), K)
    j_arc = np.tile(np.arange(K), n_arc)
    for name, ends in (("flow_tail", tails), ("flow_head", heads)):
        # f_aj - (N-1) z_{end(a), j} <= 0
        add(name, _block(np.concatenate([arc_flat, arc_flat]),
                         np.concatenate([off_f + arc_flat, off_z + ends[arc_of] * K + j_arc]),
                         np.concatenate([np.ones(n_arc * K), np.full(n_arc * K, -(N - 1.0))]),
                         n_arc * K, n_var),
            np.full(n_arc * K, -np.inf), np.zeros(n_arc * K))
    # z_sj - N r_sj - (inflow - outflow)_sj <= 0
    add("net", _block(np.concatenate([sk, sk, heads[arc_of] * K + j_arc, tails[arc_of] * K + j_arc]),
                      np.concatenate([off_z + sk, off_r + sk,
                                      off_f + arc_flat, off_f + arc_flat]),
                      np.concatenate([np.ones(S * K), np.full(S * K, -float(N)),
                                      -np.ones(n_arc * K), np.ones(n_arc * K)]),
                      S * K, n_var),
        np.full(S * K, -np.inf), np.zeros(S * K))

    if n_max is not None:
        # sum_s z_sj <= n_max
        add("cap_n", _block(j_of, off_z + sk, np.ones(S * K), K, n_var),
            np.full(K, -np.inf), np.full(K, float(n_max)))
    xy = dist = None
    if dist_max is not None or radius_max is not None:
        xy = np.asarray(state_xy, float).reshape(S, -1)
        dist = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
        # the threshold per (pair, slot): the pair's own `dist_max` (the larger of its two
        # states' `dist_max_state` overrides where one is given) everywhere, and `2 radius_max`
        # on a slot whose root is free, since a free root allows a diameter and not a radius
        thresh = np.full(K, np.inf)
        if radius_max is not None:
            thresh[root_of < 0] = 2.0 * float(radius_max)
        ai, bi = np.triu_indices(S, k=1)
        pair_t = np.full(len(ai), np.inf)
        if dist_max is not None:
            own = np.full(S, float(dist_max))
            for s, km in (dist_max_state or {}).items():
                own[int(s)] = max(own[int(s)], float(km))
            pair_t = np.maximum(own[ai], own[bi])
        pi, ji = np.nonzero(dist[ai, bi][:, None] > np.minimum(pair_t[:, None], thresh[None, :]))
        P = len(pi)
        # z_sj + z_s'j <= 1 for every far pair (s, s') and every slot j it is far on.  One row
        # per (pair, slot): a pair index here would let `_block` sum the slots into a single row
        # and forbid the two states from being contacted anywhere on the map.
        pk = np.arange(P)
        add("cap_dist", _block(np.concatenate([pk, pk]),
                               np.concatenate([off_z + ai[pi] * K + ji,
                                               off_z + bi[pi] * K + ji]),
                               np.ones(2 * P), P, n_var),
            np.full(P, -np.inf), np.ones(P))

    pairs = np.array([(j, j + 1) for lo_j, hi_j in slots.values() for j in range(lo_j, hi_j - 1)],
                     int).reshape(-1, 2)
    Q = len(pairs)
    free = pairs[~np.isin(pairs[:, 0], fixed_slots)] if Q else pairs   # u_j = 1 says nothing
    if len(free):
        q = np.arange(len(free))
        # u_{j+1} - u_j <= 0
        add("order_u", _block(np.concatenate([q, q]),
                              np.concatenate([off_u + free[:, 1], off_u + free[:, 0]]),
                              np.concatenate([np.ones(len(free)), -np.ones(len(free))]),
                              len(free), n_var),
            np.full(len(free), -np.inf), np.zeros(len(free)))
    if Q and order_mass:
        # sum_s (W_{s,j+1}/tau) y_{s,j+1} - sum_s (W_sj/tau) y_sj <= 0
        qs = np.repeat(np.arange(Q), S)
        ss_ = np.tile(np.arange(S), Q)
        add("order_mass", _block(np.concatenate([qs, qs]),
                                 np.concatenate([off_y + ss_ * K + np.repeat(pairs[:, 1], S),
                                                 off_y + ss_ * K + np.repeat(pairs[:, 0], S)]),
                                 np.concatenate([W[ss_, np.repeat(pairs[:, 1], S)] / tau,
                                                 -W[ss_, np.repeat(pairs[:, 0], S)] / tau]),
                                 Q, n_var),
            np.full(Q, -np.inf), np.zeros(Q))

    var_lb = np.zeros(n_var)
    var_ub = np.ones(n_var)
    var_ub[off_f:off_u] = max(N - 1.0, 0.0)
    if radius_max is not None:
        for j in np.flatnonzero(root_of >= 0):
            beyond = np.flatnonzero(dist[:, root_of[j]] > float(radius_max))
            for off in (off_z, off_y):
                var_ub[off + beyond * K + j] = 0.0
    for s, j in pairs_a:
        var_lb[off_z + s * K + j] = 1.0
    for j in fixed_slots:
        var_lb[off_u + j] = 1.0
    for j in closed_slots:
        var_ub[off_u + j] = 0.0
        var_ub[off_z + np.arange(S) * K + j] = 0.0
        var_ub[off_y + np.arange(S) * K + j] = 0.0
    integrality = np.zeros(n_var)
    integrality[off_z:off_z + S * K] = 1
    integrality[off_r:off_r + S * K] = 1
    integrality[off_u:off_u + K] = 1

    return Level0Problem(
        c=c, A=sparse.csc_matrix(sparse.vstack(blocks)),
        lb=np.concatenate(lb), ub=np.concatenate(ub),
        integrality=integrality, var_lb=var_lb, var_ub=var_ub,
        M_s=M_tot, D=D, edges=E, tau=tau, delta=(U - L) / (L + U), eps=float(eps),
        eta=float(eta), n_state=S, k=K, off_z=off_z, off_y=off_y, off_r=off_r, off_f=off_f,
        n_var=n_var, rows=rows,
        off_u=off_u, W=W, bundle_of=bundle_of, slots=slots, slot_has=slot_has, L=L, U=U,
        L_j=L_j, U_j=U_j,
        cover_ub=cover_ub, prior=prior_arr, channels=channels,
        bundles={name: tuple(chans) for name, chans in bundles.items()},
        state_xy=np.zeros((0, 0)) if xy is None else xy,
        slot_root=tuple(int(v) for v in root_of),
        radius_max=None if radius_max is None else float(radius_max),
        state_list=tuple(cells.state_list),
    )


def moments_from_seeds(problem: Level0Problem, seeds, state_xy) -> np.ndarray:
    """`D (S, K)`: `D[s, j]` is the squared centroid distance from state `s` to the state slot
    `j` is seeded at, in whatever units `state_xy` carries (km after the driver's conversion).
    A slot with no seed keeps a zero column, which is what "contacts only" means for it.

    `seeds` is `greedy_plan`'s own second return, `{bundle: [(state, slot), ...]}`, so every
    slot the greedy used gets a centre and not just the ones a committed draw names.  Level 1's
    `D` is a state's second moment about a district centre; this is centroid to centroid, so
    the state a slot is seeded at scores exactly zero and a state's own internal spread never
    enters.  `eps_lexicographic` bounds the tie-break over the polytope either way.
    """
    S, K = problem.n_state, problem.k
    xy = np.asarray(state_xy, float).reshape(S, -1)
    D = np.zeros((S, K))
    for lst in seeds.values():
        for s, j in lst:
            if not (0 <= s < S and 0 <= j < K):
                raise ValueError(f"seed ({s}, {j}) out of range")
            D[:, j] = ((xy - xy[s]) ** 2).sum(axis=1)
    return D


def forbid_bundle(problem: Level0Problem, s: int, bundle: str) -> Level0Problem:
    """A copy of `problem` where state `s` cannot enter any slot of `bundle`: `z_sj` and
    `y_sj` get `var_ub = 0` (and `var_lb = 0`, so a standing anchor there is released, the
    override-wins rule of `bound_z`).  Route R's per-state move; a copy rather than an
    in-place edit so the incumbent problem stays intact across moves."""
    if not (0 <= s < problem.n_state):
        raise ValueError(f"state {s} out of range")
    if bundle not in problem.slots:
        raise ValueError(f"unknown bundle {bundle!r}; expected one of {list(problem.slots)}")
    new = dataclasses.replace(problem, var_lb=problem.var_lb.copy(),
                              var_ub=problem.var_ub.copy())
    lo, hi = new.slots[bundle]
    for j in range(lo, hi):
        for off in (new.off_z, new.off_y):
            new.var_lb[off + s * new.k + j] = 0.0
            new.var_ub[off + s * new.k + j] = 0.0
    return new


def require_cover(problem: Level0Problem, s: int, channels) -> Level0Problem:
    """A copy of `problem` where state `s` must be served in full on `channels`: the cover
    row of each `(s, c)` gets its lower bound raised to `cover_ub[s, c]`, the whole share the
    earlier stages left.  A channel the model does not carry is skipped.  Paired with
    `forbid_bundle` on every other bundle carrying the channel it says which bundle must take
    all of it (`--force-national`: pure `N` holds the state's national).  Uniform across a
    bundle's slots like `forbid_bundle`, so both orderings stay valid.  The bound is on a row,
    and `greedy_plan` does not aim for it: a greedy point that falls short is refused by
    `check_point`, and the driver then solves cold.  A copy for the same reason as
    `forbid_bundle`."""
    if not (0 <= s < problem.n_state):
        raise ValueError(f"state {s} out of range")
    new = dataclasses.replace(problem, lb=problem.lb.copy())
    lo, _ = new.rows["cover"]
    C = len(new.channels)
    for c in channels:
        if c in new.channels:
            ci = new.channels.index(c)
            new.lb[lo + s * C + ci] = new.cover_ub[s, ci]
    return new


def append_row(problem: SplitProblem, name: str, cols, vals, lo: float, hi: float) -> SplitProblem:
    """A copy of `problem` with one row `lo <= sum vals[i] x[cols[i]] <= hi` appended under
    `rows[name]` (`with_cutoff`'s pattern, any row)."""
    cols = np.asarray(cols, int)
    vals = np.asarray(vals, float)
    row = sparse.coo_matrix((vals, (np.zeros(len(cols), int), cols)),
                            shape=(1, problem.n_var)).tocsc()
    start = problem.A.shape[0]
    rows = dict(problem.rows)
    rows[name] = (start, start + 1)
    return dataclasses.replace(
        problem, A=sparse.vstack([problem.A, row]).tocsc(),
        lb=np.concatenate([problem.lb, [float(lo)]]),
        ub=np.concatenate([problem.ub, [float(hi)]]), rows=rows)


def serve_states(problem: Level0Problem, states) -> Level0Problem:
    """A copy of `problem` with one row per state in `states`, `sum_j z_sj >= 1` over every
    slot of the model: the state must be in at least one district of some bundle.  The
    business rule that no state is left out of every channel grouping; the driver applies it
    to the states no earlier stage served, in the last stage that can serve them.  Rows are
    named `serve` (one block)."""
    states = sorted({int(s) for s in states})
    if not states:
        return problem
    for s in states:
        if not (0 <= s < problem.n_state):
            raise ValueError(f"state {s} out of range")
    K = problem.k
    rows = np.repeat(np.arange(len(states)), K)
    cols = np.concatenate([problem.off_z + s * K + np.arange(K) for s in states])
    block = sparse.coo_matrix((np.ones(len(cols)), (rows, cols)),
                              shape=(len(states), problem.n_var)).tocsc()
    start = problem.A.shape[0]
    names = dict(problem.rows)
    names["serve"] = (start, start + len(states))
    return dataclasses.replace(
        problem, A=sparse.vstack([problem.A, block]).tocsc(),
        lb=np.concatenate([problem.lb, np.ones(len(states))]),
        ub=np.concatenate([problem.ub, np.full(len(states), np.inf)]), rows=names)


def max_splits(problem: Level0Problem, caps: dict[str, int]) -> Level0Problem:
    """A copy of `problem` with one row per state named in `caps` and present in the
    problem's `state_list`, `sum_j z_sj <= caps[state]` over every slot of the model: the
    state may be cut between at most `caps[state]` districts of this stage (route S) or of
    the whole model (route J).  The level-2 cut can still leave fragments the realiser's
    repair mends, so this caps the plan's own splits, not the drawn map's pieces.

    A cap below 1 is refused, for every entry of `caps` regardless of presence (the same
    dict is applied to every stage, and a typo should not wait for the one stage that
    happens to carry the state).  A state named in `caps` but not in `problem.state_list` (a
    stage that does not carry it) is ignored.  Rows are named `max_splits` (one block,
    `serve_states`'s pattern).
    """
    for code, cap in caps.items():
        if int(cap) < 1:
            raise ValueError(f"max_splits[{code!r}] = {cap} must be at least 1")
    idx = {code: i for i, code in enumerate(problem.state_list)}
    states = sorted(idx[code] for code in caps if code in idx)
    if not states:
        return problem
    code_of = {i: code for code, i in idx.items()}
    K = problem.k
    rows = np.repeat(np.arange(len(states)), K)
    cols = np.concatenate([problem.off_z + s * K + np.arange(K) for s in states])
    block = sparse.coo_matrix((np.ones(len(cols)), (rows, cols)),
                              shape=(len(states), problem.n_var)).tocsc()
    start = problem.A.shape[0]
    names = dict(problem.rows)
    names["max_splits"] = (start, start + len(states))
    ub = np.array([float(caps[code_of[s]]) for s in states])
    return dataclasses.replace(
        problem, A=sparse.vstack([problem.A, block]).tocsc(),
        lb=np.concatenate([problem.lb, np.full(len(states), -np.inf)]),
        ub=np.concatenate([problem.ub, ub]), rows=names)


def band_break(problem: Level0Problem, allowance: dict[str, float]) -> Level0Problem:
    """A copy of `problem` where, for each state `s` named in `allowance` and present in
    `problem.state_list` with a positive allowance `a_s`, the upper band row (`band_hi`)
    gains the term `- a_s z_sj` on every slot `j`: with `z_sj = 1` the row reads
    `sum_s W_sj y_sj <= U_j + a_s`, so a slot in contact with `s` may carry `a_s` past `U_j`
    (and `a_s + a_t` when it also contacts a second such state; the two allowances simply add).
    `band_lo` is untouched. A non-positive allowance, or a state `problem.state_list` does not
    carry, is ignored, the same rule `max_splits` uses.

    `band_hi` already exists as its own row block (`build_level0` bands each slot with a
    `band_lo` and a `band_hi` row rather than one ranged row), so this edits that block's data
    in place rather than adding a row; every row name in `problem.rows` is unchanged.  The
    edit only relaxes the bound a feasible point already satisfies (`z_sj` can only add
    non-positive terms to the row's value at `z_sj = 1` and none at `z_sj = 0`), so a point
    that passes `check_point` against `problem` still passes it against the result.
    """
    idx = {code: i for i, code in enumerate(problem.state_list)}
    states = [(idx[code], float(a)) for code, a in allowance.items()
             if code in idx and float(a) > 0.0]
    if not states:
        return problem
    lo, hi = problem.rows["band_hi"]
    K = problem.k
    if hi - lo != K:
        raise ValueError(f"band_hi has {hi - lo} rows, expected {K}")
    rows = np.concatenate([np.arange(K) for _ in states])
    cols = np.concatenate([problem.off_z + s * K + np.arange(K) for s, _ in states])
    data = np.concatenate([np.full(K, -a / problem.tau) for _, a in states])
    delta = sparse.coo_matrix((data, (lo + rows, cols)),
                              shape=problem.A.shape).tocsc()
    return dataclasses.replace(problem, A=(problem.A + delta).tocsc())


def plus_pair(problem: Level0Problem, target: dict[str, float] | None = None) -> Level0Problem:
    """A state's `WH_PLUS` share must equal its `FI_PLUS` share (docs/FULL_PROBLEM.md, the
    2026-09-11 decision): `WH_PLUS` folds only national's Wells WH half (`N_WH`) and `FI_PLUS`
    only Chase and Wells FI (`N_FI`), so a state on one without an equal share of the other
    leaves that other national half unserved, and no bundle can pick it up alone.

    With both bundles among `problem.slots`, one equality row per state:
    `sum_{j in WH_PLUS} y_sj - sum_{j in FI_PLUS} y_sj = 0`.  With `FI_PLUS` alone and a
    `target` (a dict `state -> share`, typically the `WH_PLUS` fold an earlier stage already
    solved), one row per state named in `target`: `sum_{j in FI_PLUS} y_sj = max(0, target[s])`
    (0 for a state with no positive target, still pinned there so the FI stage cannot serve
    it some other way instead.  With `WH_PLUS` alone and no `target`, or with neither bundle
    present, `problem` is returned unchanged: the WH stage is free and the FI stage inherits.
    Rows are named `plus_pair` (one block).
    """
    have_wh = "WH_PLUS" in problem.slots
    have_fi = "FI_PLUS" in problem.slots
    K = problem.k

    if have_wh and have_fi:
        wh_lo, wh_hi = problem.slots["WH_PLUS"]
        fi_lo, fi_hi = problem.slots["FI_PLUS"]
        n = problem.n_state
        wh_cols = np.arange(wh_lo, wh_hi)
        fi_cols = np.arange(fi_lo, fi_hi)
        per_state = np.concatenate([wh_cols, fi_cols])
        rows = np.repeat(np.arange(n), len(per_state))
        cols = np.concatenate([problem.off_y + s * K + per_state for s in range(n)])
        data = np.tile(np.concatenate([np.ones(len(wh_cols)), -np.ones(len(fi_cols))]), n)
        block = sparse.coo_matrix((data, (rows, cols)), shape=(n, problem.n_var)).tocsc()
        start = problem.A.shape[0]
        names = dict(problem.rows)
        names["plus_pair"] = (start, start + n)
        return dataclasses.replace(
            problem, A=sparse.vstack([problem.A, block]).tocsc(),
            lb=np.concatenate([problem.lb, np.zeros(n)]),
            ub=np.concatenate([problem.ub, np.zeros(n)]), rows=names)

    if have_fi and target is not None:
        idx = {code: i for i, code in enumerate(problem.state_list)}
        states = sorted((s for s in target if s in idx), key=lambda s: idx[s])
        if not states:
            return problem
        fi_lo, fi_hi = problem.slots["FI_PLUS"]
        cols_per = np.arange(fi_lo, fi_hi)
        rows = np.repeat(np.arange(len(states)), len(cols_per))
        cols = np.concatenate([problem.off_y + idx[st] * K + cols_per for st in states])
        block = sparse.coo_matrix((np.ones(len(cols)), (rows, cols)),
                                  shape=(len(states), problem.n_var)).tocsc()
        vals = np.array([max(0.0, float(target[st])) for st in states])
        start = problem.A.shape[0]
        names = dict(problem.rows)
        names["plus_pair"] = (start, start + len(states))
        new = dataclasses.replace(
            problem, A=sparse.vstack([problem.A, block]).tocsc(),
            lb=np.concatenate([problem.lb, vals]),
            ub=np.concatenate([problem.ub, vals]), rows=names)
        # a zero target is also a variable bound, so `greedy_plan` (which reads bounds, not
        # this row) never enters the state; otherwise its point fails the row and the FI
        # stage solves cold, which at FI 21 ran out of time on the empty plan
        for st, v in zip(states, vals):
            if v <= 0.0:
                new = forbid_bundle(new, idx[st], "FI_PLUS")
        return new

    return problem


def _var_name(problem: Level0Problem, i: int) -> str:
    S, K = problem.n_state, problem.k
    for name, off in (("z", problem.off_z), ("y", problem.off_y), ("r", problem.off_r)):
        if off <= i < off + S * K:
            return f"{name}[{(i - off) // K}, {(i - off) % K}]"
    if problem.off_f <= i < problem.off_u:
        return f"f[arc {(i - problem.off_f) // K}, {(i - problem.off_f) % K}]"
    return f"u[{i - problem.off_u}]" if i >= problem.off_u else f"x[{i}]"


def check_point(problem: Level0Problem, x: np.ndarray, *, tol: float = 1e-6) -> None:
    """Raise `ValueError` naming the first bound, row or integrality `x` violates; return
    quietly when `x` sits inside its bounds, `lb - tol <= A x <= ub + tol` on every row, and
    the integer blocks are integral.

    Bounds are read first: an anchor, a `forbid_bundle` and a radius cap are all bounds, and
    each says exactly which state and slot went wrong, where the row a broken bound also breaks
    (`yz_lo`, `net`) says only that some row does not hold.
    """
    x = np.asarray(x, float)
    if x.shape != (problem.n_var,):
        raise ValueError(f"x must have {problem.n_var} entries, got {x.shape}")
    S, K = problem.n_state, problem.k
    bad = np.flatnonzero((x < problem.var_lb - tol) | (x > problem.var_ub + tol))
    if bad.size:
        i = int(bad[0])
        if problem.off_z <= i < problem.off_z + S * K and problem.var_lb[i] >= 1.0 - 1e-9:
            raise ValueError(f"infeasible point: anchored contact {_var_name(problem, i)} "
                             f"(state {(i - problem.off_z) // K}, slot "
                             f"{(i - problem.off_z) % K}) is not placed")
        if (problem.off_z <= i < problem.off_z + S * K and problem.radius_max is not None
                and problem.var_ub[i] <= 1e-9):
            s, j = (i - problem.off_z) // K, (i - problem.off_z) % K
            root = problem.slot_root[j] if j < len(problem.slot_root) else -1
            if root >= 0:
                km = float(np.sqrt(((problem.state_xy[s] - problem.state_xy[root]) ** 2).sum()))
                raise ValueError(f"infeasible point: {_var_name(problem, i)} puts state {s} "
                                 f"{km:.6g} from slot {j}'s root {root}, beyond radius_max "
                                 f"{problem.radius_max:.6g}")
        raise ValueError(f"infeasible point: {_var_name(problem, i)} = {x[i]:.6g} outside "
                         f"[{problem.var_lb[i]:.6g}, {problem.var_ub[i]:.6g}]")
    Ax = problem.A @ x
    bad = np.flatnonzero((Ax < problem.lb - tol) | (Ax > problem.ub + tol))
    if bad.size:
        i = int(bad[0])
        block_of = next(((n, a) for n, (a, b) in problem.rows.items() if a <= i < b), None)
        name = f"{block_of[0]}[{i - block_of[1]}]" if block_of else f"row {i}"
        if block_of and block_of[0] in ("band_lo", "band_hi"):
            # the band bound lives in the matrix, not in `lb`/`ub`, and it is the slot's own
            j = i - block_of[1]
            y_j = x[problem.off_y + np.arange(S) * K + j]
            raise ValueError(f"infeasible point: slot {j} ({problem.bundle_of[j]}) holds "
                             f"{float(problem.W[:, j] @ y_j):.6g}, outside its band "
                             f"[{problem.L_j[j]:.6g}, {problem.U_j[j]:.6g}]")
        raise ValueError(f"infeasible point: row {name} needs {problem.lb[i]:.6g} <= "
                         f"{Ax[i]:.6g} <= {problem.ub[i]:.6g}")
    ints = np.flatnonzero(problem.integrality)
    frac = ints[np.abs(x[ints] - np.round(x[ints])) > tol]
    if frac.size:
        i = int(frac[0])
        raise ValueError(f"infeasible point: {_var_name(problem, i)} = {x[i]:.6g} is not integral")


def greedy_plan(problem: Level0Problem, *, priority=None
                ) -> tuple[np.ndarray, dict[str, list[tuple[int, int]]]]:
    """A feasible point of `problem` for the warm start, and the seeds its slots are rooted at
    (`{bundle: [(state, slot), ...]}`, one per used slot).

    Bundles go in `priority` order (default: `problem.slots`'s order, unnamed bundles after
    the named ones), slots in index order.  A slot seeds at the state with the most remaining
    mass `W_sj * avail_s`, `avail_s` the smallest remaining `cover_ub` over the bundle's
    channels after the earlier slots, and grows breadth-first on the rook graph over states
    with `avail >= eta`, taking whole shares until the mass reaches the slot's target.  When
    the next whole state would pass `U_B` it takes the fraction that lands the slot on the band
    midpoint `(L_B + U_B) / 2` (never below `eta`) and leaves the rest of that state to the next
    slot of the bundle, which seeds from it so the two stay contiguous.  The target is `L_B`.
    Every bound here is the bundle's own (`L_j`, `U_j`), which is the global band only while
    every bundle shares it.  For a
    bundle with `n` slots fixed used (`build_level0(fixed_used=...)`) the target is
    `clip(0.98 available mass / n, L_B, U_B)` and every slot is filled to exactly that, the state
    that would pass it cut to land there: whole states overshooting a target spend the mass
    budget before the count is reached (the 2% is for pockets the BFS cannot reach).  When no
    target fills every fixed slot, the slots the fullest fill left take the free rule.  A slot
    that reaches its target from no seed stays unused, and so does the rest of its bundle
    (the `u` ordering).

    Honoured along the way: `cap_n`, `cap_dist` and `max_splits`, read back from the rows, and
    every `z`, `y` and `r` bound (anchors, `forbid_bundle`, `fix_roots`, `bound_z`; a `z` with
    `var_ub = 0` is never entered).  A state named in `max_splits` may not enter a slot once
    it already touches its cap's worth of committed slots (only slots already in `plan`
    count; growing that same slot further is never a new entry, so the count only rises when
    the slot itself is finished).  The same rule applies in the `serve` pass below.  The
    greedy leaves a capped state's excess mass unfilled: `max_splits`'s own row still holds it
    in the MILP, and a relaxed band (`band_break`) is what gives that excess somewhere to go.
    `radius_max` is honoured from the slot's root, or from the
    seed when the slot has none: the model only carries a diameter bound there, so the greedy
    is the stricter of the two and its point stays feasible.  A state outside the radius is not
    a bridge either -- it cannot be in the slot at all, so the BFS stops rather than passing
    through it.  Anchors (`var_lb = 1` on `z`) are pre-committed
    contacts: a bundle's anchored slots go first, each seeded at an anchored state with the
    others forced in during growth, and a state anchored on `m` slots gives each of them
    `avail / (slots of its still pending)`, so a state the committed map splits (FL on two
    N slots, CA on five) is shared rather than eaten by the first.  Until its own slots have
    taken it an anchored state enters no other slot; what they leave is free afterwards.  An
    anchored slot that cannot reach its target, or connect its anchored states, raises.
    When `order_mass` rows exist a bundle's slots are relabelled by mass, descending, which
    those rows allow.

    `r` sits at the seed (or at a fixed root) and `f` carries each subtree's size down a BFS
    tree from it, so every `net` row holds with `inflow - outflow = 1` at each non-root
    contact.  The point is checked against every row, bound and integrality (`check_point`)
    before it is returned: a silently infeasible warm start is worse than none.
    """
    S, K = problem.n_state, problem.k
    W, eta = problem.W, problem.eta
    L_j, U_j = problem.L_j, problem.U_j              # each slot is held to its bundle's band
    off_z, off_y, off_r, off_f, off_u = (problem.off_z, problem.off_y, problem.off_r,
                                         problem.off_f, problem.off_u)
    order = list(priority or ())
    unknown = [b for b in order if b not in problem.slots]
    if unknown:
        raise ValueError(f"unknown bundle(s) {unknown}; expected some of {list(problem.slots)}")
    order += [b for b in problem.slots if b not in order]

    adj: list[list[int]] = [[] for _ in range(S)]
    arc: dict[tuple[int, int], int] = {}
    for e, (a, b) in enumerate(problem.edges):
        adj[a].append(b)
        adj[b].append(a)
        arc[(a, b)] = 2 * e
        arc[(b, a)] = 2 * e + 1

    def block(off):
        return (problem.var_lb[off:off + S * K].reshape(S, K),
                problem.var_ub[off:off + S * K].reshape(S, K))

    one = 1.0 - 1e-9
    z_lb, z_ub = block(off_z)
    _, y_ub = block(off_y)
    r_lb, r_ub = block(off_r)
    u_lb = problem.var_lb[off_u:off_u + K]
    anchored = (z_lb >= one).any(axis=1)
    pending = (z_lb >= one).sum(axis=1)          # anchored slots of s not yet processed
    n_max = (int(round(problem.ub[problem.rows["cap_n"][0]])) if "cap_n" in problem.rows
             else None)
    # (state, state, slot): a cap_dist row now names the slot it applies to, since a radius
    # cap puts the pair rows on the rootless slots only
    far: set[tuple[int, int, int]] = set()
    if "cap_dist" in problem.rows:
        a, b = problem.rows["cap_dist"]
        cap = problem.A.tocsr()[a:b]
        for i in range(b - a):
            cols = cap.indices[cap.indptr[i]:cap.indptr[i + 1]]
            pair = tuple(sorted(set(((cols - off_z) // K).tolist())))
            if len(pair) == 2:
                far.add((*pair, int((cols[0] - off_z) % K)))
    radius = problem.radius_max
    xy = np.asarray(problem.state_xy, float).reshape(S, -1) if radius is not None else None

    # `max_splits`: one row per capped state, its non-zero columns that state's own `z`
    # column over every slot (`max_splits`'s own layout).  Read the state index and its cap
    # back the way `cap_n` and `cap_dist` are, above.
    splits_cap: dict[int, int] = {}
    if "max_splits" in problem.rows:
        lo_m, hi_m = problem.rows["max_splits"]
        cap_rows = problem.A.tocsr()[lo_m:hi_m]
        for i in range(hi_m - lo_m):
            cols = cap_rows.indices[cap_rows.indptr[i]:cap_rows.indptr[i + 1]]
            splits_cap[int((cols[0] - off_z) // K)] = int(round(problem.ub[lo_m + i]))

    rem = problem.cover_ub.copy()
    has = problem.slot_has

    def avail(s, j):
        return float(min(rem[s, has[j]].min(), y_ub[s, j]))

    def touches(s):
        """How many slots already committed to `plan` contact state `s`; a slot still being
        grown for a trial is not yet in `plan`, so re-entering it is never counted as new."""
        return sum(1 for chosen, _, _ in plan.values() if s in chosen)

    def allowed(s, j):
        if not (z_ub[s, j] >= one and (not anchored[s] or z_lb[s, j] >= one
                                       or pending[s] == 0)):
            return False
        cap = splits_cap.get(s)
        return cap is None or touches(s) < cap

    def grow(j, seed, stop, land, cap):
        """BFS from `seed`: `(ok, {s: y}, mass, split state or None)`.  Whole shares until
        `stop`; a state that would pass `cap` is cut to land on `land`."""
        must = {int(s) for s in np.flatnonzero(z_lb[:, j] >= one)}
        chosen: dict[int, float] = {}
        mass, split = 0.0, None
        beyond = None
        if radius is not None:
            centre = problem.slot_root[j] if j < len(problem.slot_root) else -1
            centre = seed if centre < 0 else int(centre)
            beyond = ((xy - xy[centre]) ** 2).sum(axis=1) > float(radius) ** 2 + 1e-9
        queue, seen = deque([seed]), {seed}
        while queue:
            if mass >= stop - 1e-9 and must <= chosen.keys():
                break
            if n_max is not None and len(chosen) >= n_max:
                break
            s = queue.popleft()
            if beyond is not None and beyond[s]:
                continue                     # outside the slot's radius, and no bridge either
            if any((min(s, t), max(s, t), j) in far for t in chosen):
                continue
            a = avail(s, j)
            if s in must:
                a /= pending[s]              # an equal share for each of its pending slots
            if a < eta - 1e-12:
                continue
            w = W[s, j]
            if mass + w * a > cap + 1e-9:
                y = min(a, max(eta, (land - mass) / w))
                if mass + w * y > U_j[j] + 1e-9:
                    continue
                if y < a - 1e-12:
                    split = s
            else:
                y = a
            chosen[s] = y
            mass += w * y
            nb = [t for t in adj[s] if t not in seen and allowed(t, j)]
            nb.sort(key=lambda t: (t not in must, -W[t, j] * avail(t, j), t))
            seen.update(nb)
            queue.extend(nb)
        return mass >= stop - 1e-9 and must <= chosen.keys(), chosen, mass, split

    plan: dict[int, tuple[dict[int, float], float, int]] = {}

    def fill(bname, stop, land, cap):
        """Fill `bname`'s slots into `plan`: `(slots used, anchored-slot error or None)`."""
        lo, hi = problem.slots[bname]
        hint, n_used = None, 0
        # anchored slots first: their contacts are committed, and an unanchored slot that
        # grew first could take what an anchored one needs
        for j in sorted(range(lo, hi), key=lambda j: (not (z_lb[:, j] >= one).any(), j)):
            if j in plan:
                continue                    # filled by an earlier try
            must = [int(s) for s in np.flatnonzero(z_lb[:, j] >= one)]
            if must:
                seeds = sorted(must, key=lambda s: (-W[s, j] * avail(s, j), s))
            else:
                seeds = sorted((s for s in range(S)
                                if allowed(s, j) and avail(s, j) >= eta and W[s, j] > 0),
                               key=lambda s: (-W[s, j] * avail(s, j), s))
                if hint in seeds:
                    seeds.remove(hint)
                    seeds.insert(0, hint)
            found = None
            for seed in seeds:
                ok, chosen, mass, split = grow(j, seed, stop, land, cap)
                if ok:
                    found = (chosen, mass, seed, split)
                    break
            if found is None and must:
                missing = sorted(set(must) - set(chosen))
                return n_used, (
                    f"anchored slot {j} ({bname}) cannot connect its anchored states "
                    f"{missing} from {seed}" if missing else
                    f"anchored slot {j} ({bname}) reaches {mass:.6g} of its target "
                    f"{stop:.6g} from anchored state(s) {must} with the contacts left")
            if found is None:
                break                       # the rest of the bundle stays unused (order_u)
            chosen, mass, seed, split = found
            for s, y in chosen.items():
                rem[s, has[j]] -= y
            for s in must:
                pending[s] -= 1
            plan[j] = (chosen, mass, seed)
            hint = split
            n_used += 1
        return n_used, None

    for bname in order:
        lo, hi = problem.slots[bname]
        if hi <= lo:
            continue                                 # a bundle with no slots has no band
        L_b, U_b = float(L_j[lo]), float(U_j[lo])
        tau_b = (L_b + U_b) / 2.0
        n_fixed = int((u_lb[lo:hi] >= one).sum())
        if not n_fixed:
            _, err = fill(bname, L_b, tau_b, U_b)
            if err:
                raise ValueError(err)
            continue
        # A fixed count: the largest target in [L, U] at which the fill reaches it, tried
        # from `total / n` down in 3% steps to L, every slot filled to exactly the target.
        # Whole states overshooting a target spend the budget before the count is reached,
        # and pockets the BFS cannot reach are lost, so no single margin is right.
        total = sum(W[s, lo] * avail(s, lo) for s in range(S) if allowed(s, lo))
        targets = sorted({float(np.clip(f * total / n_fixed, L_b, U_b))
                          for f in np.arange(1.0, 0.0, -0.03)}, reverse=True)
        best = None                          # the fullest partial fill, for `strict=False`
        for target in targets:
            snap = (rem.copy(), pending.copy(), dict(plan))
            n_used, err = fill(bname, target, target, target)
            if err is None and n_used >= n_fixed:
                break
            if err is None and (best is None or n_used > best[0]):
                best = (n_used, rem.copy(), pending.copy(), dict(plan))
            rem[:], pending[:] = snap[0], snap[1]
            plan.clear()
            plan.update(snap[2])
        else:
            # No target fills every slot exactly.  Second try from the fullest partial fill:
            # the slots it left take the free rule (reach L_B, land on the midpoint, cap at
            # U_B), which tolerates the uneven pockets an exact target cannot.
            if best is not None:
                rem[:], pending[:] = best[1], best[2]
                plan.clear()
                plan.update(best[3])
                n_more, err2 = fill(bname, L_b, tau_b, U_b)
                if err2 is None and best[0] + n_more >= n_fixed:
                    continue
                err = err or err2
            raise ValueError(err or f"bundle {bname!r}: {n_used} of {n_fixed} fixed slots "
                             f"filled at every target in [{L_b:.6g}, {U_b:.6g}]")

    if "serve" in problem.rows:
        # `serve_states` rows: each named state joins a used slot next to it that has room
        # for a share of at least `eta` under its band and caps, the slot with the most room
        # first.  Read back from the rows, as the caps are.
        lo_r, hi_r = problem.rows["serve"]
        A_csr = problem.A.tocsr()
        need = sorted({int((A_csr[r].indices[0] - off_z) // K) for r in range(lo_r, hi_r)})
        served = {s for chosen, _, _ in plan.values() for s in chosen}
        for s in need:
            if s in served:
                continue
            options = []
            for j, (chosen, mass, seed) in plan.items():
                if not any(t in chosen for t in adj[s]) or not allowed(s, j):
                    continue
                if n_max is not None and len(chosen) >= n_max:
                    continue
                if any((min(s, t), max(s, t), j) in far for t in chosen):
                    continue
                if radius is not None:
                    centre = problem.slot_root[j] if j < len(problem.slot_root) else -1
                    centre = seed if centre < 0 else int(centre)
                    if ((xy[s] - xy[centre]) ** 2).sum() > float(radius) ** 2 + 1e-9:
                        continue
                room = U_j[j] - mass
                y = min(avail(s, j), room / W[s, j]) if W[s, j] > 0 else avail(s, j)
                if y < eta - 1e-12:
                    continue
                options.append((-room, j, y))
            if not options:
                raise ValueError(f"state {s} must be served and no used slot next to it "
                                 f"has room for it")
            _, j, y = min(options)
            chosen, mass, seed = plan[j]
            chosen[s] = y
            plan[j] = (chosen, mass + W[s, j] * y, seed)
            rem[s, has[j]] -= y
            served.add(s)

    if "order_mass" in problem.rows:
        relabelled = {}
        for lo, hi in problem.slots.values():
            used = sorted((j for j in range(lo, hi) if j in plan), key=lambda j: -plan[j][1])
            relabelled.update(zip(range(lo, lo + len(used)), (plan[j] for j in used)))
        plan = relabelled

    x = np.zeros(problem.n_var)
    seeds_out: dict[str, list[tuple[int, int]]] = {b: [] for b in problem.slots}
    for j, (chosen, mass, seed) in plan.items():
        x[off_u + j] = 1.0
        for s, y in chosen.items():
            x[off_z + s * K + j] = 1.0
            x[off_y + s * K + j] = y
        fixed = [s for s in chosen if r_lb[s, j] >= one]
        root = (fixed[0] if fixed else seed if r_ub[seed, j] >= one
                else next((s for s in chosen if r_ub[s, j] >= one), seed))
        x[off_r + root * K + j] = 1.0
        seeds_out[problem.bundle_of[j]].append((int(root), int(j)))
        parent: dict[int, int | None] = {root: None}
        walk, queue = [root], deque([root])
        while queue:
            s = queue.popleft()
            for t in adj[s]:
                if t in chosen and t not in parent:
                    parent[t] = s
                    walk.append(t)
                    queue.append(t)
        size = dict.fromkeys(chosen, 1)
        for t in reversed(walk):
            if parent[t] is not None:
                size[parent[t]] += size[t]
        for t in walk[1:]:
            x[off_f + arc[(parent[t], t)] * K + j] = float(size[t])
    check_point(problem, x)
    return x, seeds_out


def cover_pass(problem: Level0Problem, bundle_names, name: str | None = None) -> Pass:
    """Maximise `sum_{j in those bundles} sum_s W_sj y_sj`, the mass those slots cover.  Route
    J's `cover_N` names `["N"]` only (pure national slots), `cover_WH` names `WH` and
    `WH_PLUS`, `cover_FI` names `FI` and `FI_PLUS`."""
    names = [bundle_names] if isinstance(bundle_names, str) else list(bundle_names)
    c = np.zeros(problem.n_var)
    S, K = problem.n_state, problem.k
    for b in names:
        if b not in problem.slots:
            raise ValueError(f"unknown bundle {b!r}; expected one of {list(problem.slots)}")
        lo, hi = problem.slots[b]
        for j in range(lo, hi):
            c[problem.off_y + np.arange(S) * K + j] = problem.W[:, j]
    return Pass(name or "cover_" + "+".join(names), c, "max")


def contacts_pass(problem: Level0Problem) -> Pass:
    """Minimise `sum z`, unit cost on every contact (the level-1 objective)."""
    c = np.zeros(problem.n_var)
    c[problem.off_z:problem.off_z + problem.n_state * problem.k] = 1.0
    return Pass("contacts", c, "min")


def compactness_pass(problem: Level0Problem) -> Pass:
    """Contacts plus the `eps W D y` tie-break, `eps` from `eps_lexicographic` on the state
    totals and `D`; with `D` all zero this is the contacts pass again."""
    p = contacts_pass(problem)
    S, K = problem.n_state, problem.k
    p.c[problem.off_y:problem.off_y + S * K] = problem.eps * (problem.W * problem.D).ravel()
    return Pass("compactness", p.c, "min")


def _objective(problem: Level0Problem, c: np.ndarray, res: dict) -> float:
    """`c . x` on the decoded `z`, `y`, `u` (the `r` and flow blocks carry no cost in any
    pass built here, and a caller's `c` on them is not recoverable from a decode)."""
    S, K = problem.n_state, problem.k
    x = np.zeros(problem.n_var)
    x[problem.off_z:problem.off_z + S * K] = res["z"].ravel()
    x[problem.off_y:problem.off_y + S * K] = res["y"].ravel()
    x[problem.off_u:problem.off_u + K] = res["used"]
    return float(c @ x)


def solve_passes(problem: Level0Problem, passes: list[Pass], *, engine: str = "scipy",
                 strategy: str = "direct", time_limit: float | None = None,
                 threads: int | None = None, warm_start=None,
                 warm_seconds: float = 0.0) -> dict:
    """Solve `passes` lexicographically.  For each pass `problem.c` is set (negated for a
    `"max"` pass, every engine minimises), solved through `milp_engines.solve_problem`, and
    its value pinned by one appended row before the next pass.  The pinned bound is
    `v + |v| slack + |v| 1e-9 + 1e-12` on the minimised objective: `balance_pass`'s
    `v (1 + 1e-9)` widens only for `v >= 0`, and a maximisation's minimised value is negative.
    `Pass.slack` is what lets a later pass give up a fraction of this one's value; at the
    default 0.0 the bound is the exact pin.

    A pass that times out pins its incumbent and records `certified = False`.  A pass that
    returns nothing at all raises `SolveFailure` carrying `passes`, the log up to and
    including that pass, whose record is `value = None` and `status` the failure reason.
    A pass whose
    objective is identically zero (a cover pass over bundles with no slots) is recorded at
    `value = 0` and not solved (trap 19: a zero objective is not a feasibility shortcut).

    `strategy="portfolio"` applies to the contacts pass only (unit cost on `z`, the
    level-1 objective the portfolio's cutoff rounds certify); the other passes run direct.
    The portfolio parent's own HiGHS calls use `threads=2`, and HiGHS's thread pool is sized
    once per process (trap 18), so `threads` must be 2 (or None, read as 2 so a direct
    `highs` pass does not size the pool first) with it.  `highs` and `scip`
    are warm-started from the previous pass; `scipy` has no such hook.  `cpsat` is refused: its
    worker rebuilds a level-1 model from `M_s` and `delta`.

    `warm_start`, a feasible point over `n_var` (`greedy_plan`), is handed to the first solved
    pass the same way, as its `z` and `y`; `warm_seconds` is the time the caller spent
    building it.  The pass log then opens with a pseudo-entry `{name: "greedy", value: {bundle:
    covered mass}, certified: False, status: "warm_start", seconds: warm_seconds}` so the run
    record shows what the solver started from.  A first pass routed through the portfolio
    (`strategy="portfolio"` with a contacts pass first) does not receive it.

    Returns `passes` (`[{name, value, certified, status, seconds}]`), the last solved pass's
    `z (S, K)`, `y`, `u`, `residual (S, C)`, `covered`, `masses (K,)`, `contacts`, and
    `problem`, the pinned problem after every pass (route R's neighbourhood moves start there).
    """
    from td.solvers import milp_engines as _me

    if engine == "cpsat":
        raise ValueError("the cpsat engine cannot solve a Level0Problem")
    if strategy not in ("direct", "portfolio"):
        raise ValueError(f"unknown strategy {strategy!r}; expected 'direct' or 'portfolio'")
    if strategy == "portfolio":
        if threads not in (None, 2):
            raise ValueError("the portfolio parent solves with threads=2; one thread count "
                             f"per process (trap 18), got threads={threads}")
        threads = 2         # a direct highs pass at None would size the pool first
    log: list[dict] = []
    warm: dict | None = None
    last: dict | None = None
    if warm_start is not None:
        S, K = problem.n_state, problem.k
        x0 = np.asarray(warm_start, float)
        if x0.shape != (problem.n_var,):
            raise ValueError(f"warm_start must have {problem.n_var} entries, got {x0.shape}")
        z0 = x0[problem.off_z:problem.off_z + S * K].reshape(S, K) > 0.5
        y0 = x0[problem.off_y:problem.off_y + S * K].reshape(S, K)
        warm = dict(z=z0, y=y0)
        cov = {b: float((problem.W[:, lo:hi] * y0[:, lo:hi]).sum())
               for b, (lo, hi) in problem.slots.items()}
        log.append(dict(name="greedy", value=cov, certified=False, status="warm_start",
                        seconds=float(warm_seconds)))
    for p in passes:
        c = np.asarray(p.c, float) if p.sense == "min" else -np.asarray(p.c, float)
        if not np.any(c):
            log.append(dict(name=p.name, value=0.0, certified=True, status=0, seconds=0.0))
            continue
        current = dataclasses.replace(problem, c=c)
        t0 = time.time()
        try:
            if strategy == "portfolio" and p.name == "contacts":
                res = ss.solve(current, time_limit=time_limit, strict=False,
                               strategy="portfolio", threads=2)
                certified = bool(res["certified_splits"])
            else:
                kw = (dict(warm=warm) if (warm is not None and engine in ("highs", "scip"))
                      else {})
                res = _me.solve_problem(current, engine, time_limit=time_limit,
                                        threads=threads, **kw)
                certified = res["status"] == 0
        except ss.SolveFailure as exc:
            # A pass that returns nothing usable -- infeasible, or a time limit with no
            # incumbent -- would otherwise take the whole pass log with it.  Record it and
            # hand the log to the caller on the exception, so `failure.json` can name the
            # pass that died and the passes already pinned before it.
            log.append(dict(name=p.name, value=None, certified=False, status=exc.reason,
                            seconds=time.time() - t0))
            exc.passes = log
            raise
        # The pinned bound is the looser of the solver's own objective and the objective of
        # the decoded solution (exact on the contacts pass, where a portfolio member reports
        # 6.99999998 for 7); `value` is what the decoded plan realises.
        v_dec = _objective(problem, c, res)
        v = max(float(res["objective"]), v_dec)
        cols = np.flatnonzero(c)
        problem = append_row(problem, "pin_" + p.name, cols, c[cols], -np.inf,
                             v + abs(v) * p.slack + abs(v) * 1e-9 + 1e-12)
        warm = dict(z=res["z"], y=res["y"])
        last = res
        log.append(dict(name=p.name, value=(v_dec if p.sense == "min" else -v_dec + 0.0),
                        certified=certified, status=res["status"], seconds=time.time() - t0))

    if last is None:
        S, K, C = problem.n_state, problem.k, problem.cover_ub.shape[1]
        last = problem.decode_zy(np.zeros((S, K), bool), np.zeros((S, K)))
    return dict(passes=log, z=last["z"], y=last["y"], u=last["used"],
                residual=last["residual"], covered=last["covered"], masses=last["masses"],
                contacts=last["contacts"], problem=problem)
