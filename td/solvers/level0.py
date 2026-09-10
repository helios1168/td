"""level0.py -- the channel-plan MILP at state x channel grain (docs/FULL_PROBLEM.md section 5).

Cells are `(s, c)`, S states by C fine channels.  A bundle `B` is a set of channels served
together; each bundle gets `K_B = ceil(M^max_B / L)` slots, `M^max_B` being every unit of mass
the bundle could hold, so the bundle of a slot is fixed and there are no bundle binaries.
`W_sj = sum_{c in B_j} M_sc` is the mass state `s` puts into slot `j` per unit share::

    y_sj in [0, 1]    share of state s in slot j (every channel of B_j alike)
    z_sj in {0, 1}    contact,  eta z_sj <= y_sj <= z_sj <= u_j
    u_j  in {0, 1}    slot used
    cover:   sum_{j : c in B_j} y_sj <= cover_ub_sc = 1 - prior_sc        for every (s, c)
    band:    (L/tau) u_j <= sum_s (W_sj/tau) y_sj <= (U/tau) u_j          for every j
    flow:    single-commodity flow per slot as level 1, root  sum_s r_sj = u_j
    caps:    sum_s z_sj <= n_max;  z_sj + z_s'j <= 1 when |xy_s - xy_s'| > dist_max
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
    """

    off_u: int = 0
    W: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    bundle_of: tuple[str, ...] = ()
    slots: dict[str, tuple[int, int]] = field(default_factory=dict)
    slot_has: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))
    L: float = 0.0
    U: float = 0.0
    cover_ub: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    prior: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))
    channels: tuple[str, ...] = ()
    bundles: dict[str, tuple[str, ...]] = field(default_factory=dict)

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


def slot_counts(cells, bundles: dict, *, L: float, prior=None) -> dict[str, int]:
    """`K_B = ceil(M^max_B / L)` per bundle, `M^max_B = sum_s sum_{c in B} M_sc cover_ub_sc`,
    all the mass the bundle could ever hold once `prior` is committed.  Zero when there is
    none.  The driver prints these before building: the slot count is the size lever."""
    M = np.asarray(cells.M, float)
    channels = tuple(cells.channels)
    cover_ub = _cover_ub(M.shape, prior)
    idx = _channel_index(channels, bundles)
    counts = {}
    for name, cols in idx.items():
        avail = float((M[:, cols] * cover_ub[:, cols]).sum())
        counts[name] = int(math.ceil(avail / float(L) - 1e-9)) if avail > 0 else 0
    return counts


def build_level0(cells, bundles: dict, *, edges: list[tuple[int, int]], L: float, U: float | None,
                 eta: float, tau: float | None = None, n_max: int | None = None,
                 dist_max: float | None = None, state_xy=None, prior=None, anchors=None,
                 D=None, eps: float | None = None,
                 order_mass: bool | None = None) -> Level0Problem:
    """Assemble the level-0 MILP.  `cells` carries `M (S, C)`, `channels` and `state_list`
    (`td.channels.CellTable`, duck-typed); `bundles` maps a name to a tuple of channels;
    `edges` is the state rook graph over indices `0..S-1`, undirected, once per pair.

    `U` is required: without an upper band the coverage passes build one giant district per
    bundle and balance is undefined.  `tau` defaults to `(L + U) / 2`.  `prior (S, C)` is the
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
    per-slot fix (`bound_z`, `fix_roots`, a neighbourhood z-fix) needs it off as well.
    `forbid_bundle` is uniform across a bundle's slots and is compatible with both orderings.
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
    counts = slot_counts(cells, bundles, L=L, prior=prior)

    # slots: contiguous ranges per bundle, in the order `bundles` lists them
    slots, bundle_of, start = {}, [], 0
    for name in bundles:
        slots[name] = (start, start + counts[name])
        bundle_of.extend([name] * counts[name])
        start += counts[name]
    K = start
    bundle_of = tuple(bundle_of)
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
    # sum_s (W_sj/tau) y_sj - (L/tau) u_j >= 0   and   ... - (U/tau) u_j <= 0
    for name, bound, lo, hi in (("band_lo", L, 0.0, np.inf), ("band_hi", U, -np.inf, 0.0)):
        add(name, _block(np.concatenate([j_of, jk]),
                         np.concatenate([off_y + sk, off_u + jk]),
                         np.concatenate([W.ravel() / tau, np.full(K, -bound / tau)]),
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
    if dist_max is not None:
        xy = np.asarray(state_xy, float).reshape(S, -1)
        dist = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
        a, b = np.nonzero(np.triu(dist > float(dist_max), k=1))
        P = len(a)
        # z_sj + z_s'j <= 1 for every far pair (s, s') and every slot j.  One row per
        # (pair, slot): a pair index here would let `_block` sum the slots into a single row
        # and forbid the two states from being contacted anywhere on the map.
        pk = np.arange(P * K)
        add("cap_dist", _block(np.concatenate([pk, pk]),
                               np.concatenate([off_z + np.repeat(a, K) * K + np.tile(jk, P),
                                               off_z + np.repeat(b, K) * K + np.tile(jk, P)]),
                               np.ones(2 * P * K), P * K, n_var),
            np.full(P * K, -np.inf), np.ones(P * K))

    pairs = np.array([(j, j + 1) for lo_j, hi_j in slots.values() for j in range(lo_j, hi_j - 1)],
                     int).reshape(-1, 2)
    Q = len(pairs)
    if Q:
        q = np.arange(Q)
        # u_{j+1} - u_j <= 0
        add("order_u", _block(np.concatenate([q, q]),
                              np.concatenate([off_u + pairs[:, 1], off_u + pairs[:, 0]]),
                              np.concatenate([np.ones(Q), -np.ones(Q)]), Q, n_var),
            np.full(Q, -np.inf), np.zeros(Q))
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
    pairs_a = anchors.items() if isinstance(anchors, dict) else (anchors or ())
    for s, j in pairs_a:
        if not (0 <= s < S and 0 <= j < K):
            raise ValueError(f"anchor ({s}, {j}) out of range")
        var_lb[off_z + s * K + j] = 1.0
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
        cover_ub=cover_ub, prior=prior_arr, channels=channels,
        bundles={name: tuple(chans) for name, chans in bundles.items()},
    )


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
                 threads: int | None = None) -> dict:
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
