"""stage2_state.py -- stage 2 (Nash staffing) at state x channel grain.

The level-0 plan decides, per state, which bundles of channels are served: keep three
channels, merge WH and FI, or drop national.  A move like that changes what every rep can
be handed, so it has to be priced by the staffing it enables, not by mass alone.  Pricing it
at zip level would mean re-drawing the map for every candidate move; pricing it here does not,
because the utility is additive over cells:

    u_i(s, c) = c1*S_i(s,c) + c2*(T_{s,c} - S_i(s,c)) + c_free*S_free(s,c) + lam*M_{s,c}

summing the zips of a state gives exactly the state-level cell, and summing the cells a slot
holds gives that slot's gain.  So the state-level gain of a rep on a slot is
`sum_s y_j[s] * sum_{c in B_j} u_i(s,c)`, and the Nash match over slots is the same Hungarian
`channel.match` runs over districts.  On whole states the score is exact; on a state split
between slots it is the mass-proportional approximation, and level 2 decides which zips move.

`cells` is a `channels.CellTable`: `state_list`, `channels`, `reps`, `M (S,C)`,
`S (R,S,C)`, `S_free (S,C)`.  It is read by attribute, never imported, so this module stands
alone.  Rows of `S` follow `cells.reps`; columns follow `cells.channels`.

Candidacy (`candidacy=True`) restricts a rep to slots where it holds book by *masking the
match*, never by releasing anyone: a released rep's book moves into `S_free`, which every
other candidate then prices at `c_free`, and that distorts the valuation of the whole
neighbourhood (CLAUDE.md trap 20).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from td import channel, model


@dataclass
class Slot:
    """One level-0 slot: a bundle of channels and the share of each state it holds."""
    bundle: tuple[str, ...]
    y: dict = field(default_factory=dict)      # state -> share in [0, 1]
    used: bool = True


@dataclass
class Plan:
    """A channel plan: the slots and the state order the level-0 model used.

    `state_list` is informational here.  Every slot's `y` is keyed by state *name* and is
    looked up in `cells.state_list`, so the two orders need not agree.
    """
    slots: list
    state_list: list = field(default_factory=list)


# ------------------------------------------------------------------ index helpers
def _rep_rows(cells, reps) -> list:
    """Row indices into `cells.S` for `reps` (all of them, in table order, when None)."""
    if reps is None:
        return list(range(len(cells.reps)))
    idx = {r: i for i, r in enumerate(cells.reps)}
    missing = [r for r in reps if r not in idx]
    if missing:
        raise ValueError(f"rep(s) {missing} are not in the cell table")
    return [idx[r] for r in reps]


def _channel_cols(cells, bundle) -> list:
    """Column indices into the channel axis for the channels of `bundle`."""
    idx = {c: j for j, c in enumerate(cells.channels)}
    missing = [c for c in bundle if c not in idx]
    if missing:
        raise ValueError(f"channel(s) {missing} are not in the cell table {cells.channels}")
    return [idx[c] for c in bundle]


def _y_vector(cells, y) -> np.ndarray:
    """A slot's state shares as a dense vector over `cells.state_list`."""
    idx = {s: i for i, s in enumerate(cells.state_list)}
    vec = np.zeros(len(cells.state_list), float)
    for name, share in y.items():
        if name not in idx:
            raise ValueError(f"state {name!r} is not in the cell table")
        vec[idx[name]] = float(share)
    return vec


def _slot_sums(cells, plan, slot_ids, arr: np.ndarray) -> np.ndarray:
    """`(R, J)`: `arr` summed over each slot's bundle and weighted by its state shares."""
    out = np.zeros((arr.shape[0], len(slot_ids)), float)
    for col, j in enumerate(slot_ids):
        slot = plan.slots[j]
        cols = _channel_cols(cells, slot.bundle)
        out[:, col] = arr[:, :, cols].sum(2) @ _y_vector(cells, slot.y)
    return out


def _slot_mass(cells, plan, slot_ids) -> np.ndarray:
    """Opportunity held by each used slot."""
    M = np.asarray(cells.M, float)
    vals = [M[:, _channel_cols(cells, plan.slots[j].bundle)].sum(1)
            @ _y_vector(cells, plan.slots[j].y) for j in slot_ids]
    return np.array(vals, float)


# ------------------------------------------------------------------- the utility
def state_utilities(cells, reps=None, *, theta: float = 0.40, lam: float = 0.30,
                    filler_capture: str = "theta") -> np.ndarray:
    """`u[i, s, c]` for the reps of `reps` (all of them when None), in that order.

    `T_{s,c}` is a property of the cell, so it sums the book of *every* rep in the table even
    when `reps` selects a subset: a rep left out of this subproblem still holds its book.
    """
    c1, c2, c_free = model.coefficients(theta, lam, filler_capture)
    S_all = np.asarray(cells.S, float)
    T = S_all.sum(0)                                    # (S, C), over every rep
    common = (c2 * T + c_free * np.asarray(cells.S_free, float)
              + lam * np.asarray(cells.M, float))
    return common[None, :, :] + (c1 - c2) * S_all[_rep_rows(cells, reps)]


def state_gain_matrix(cells, plan, *, reps=None, theta: float = 0.40, lam: float = 0.30,
                      filler_capture: str = "theta"):
    """`(g, reps, slot_ids)` over the *used* slots: `g[i, j]` is rep i's gain from slot j.

    `slot_ids` are indices into `plan.slots`; an unused slot has no column and so can never
    be matched.  This is `channel.gain_matrix` aggregated: same coefficients, same "every rep
    is priced on every slot" convention (candidacy is a stage-2 restriction, not a stage-1 one).
    """
    R = list(cells.reps) if reps is None else list(reps)
    slot_ids = [j for j, slot in enumerate(plan.slots) if slot.used]
    u = state_utilities(cells, reps, theta=theta, lam=lam, filler_capture=filler_capture)
    return _slot_sums(cells, plan, slot_ids, u), R, slot_ids


# ---------------------------------------------------------------------- matching
def _match_masked(g: np.ndarray, ok: np.ndarray, criterion: str):
    """`channel.match` restricted to the pairs `ok` allows.

    `linear_sum_assignment` matches `min(rows, cols)` cells whatever the costs, so forbidden
    cells cannot simply be dropped: they are priced above anything a swap of allowed cells can
    recover, then filtered out of the result.  This is `tools/staff.py`'s `assign`.
    """
    if criterion == "nash":
        ok = ok & (g > 0.0)        # a zero gain is no staffing, as in `tools/staff.py`
    if g.size == 0 or not ok.any():
        return [], 0.0
    if criterion == "nash":
        with np.errstate(divide="ignore", invalid="ignore"):
            cost = -np.log(np.where(ok, g, 1.0))
    elif criterion == "utilitarian":
        cost = -np.where(ok, g, 0.0)
    else:
        raise ValueError(f"criterion {criterion!r} not in ('nash', 'utilitarian')")
    lo, hi = float(cost[ok].min()), float(cost[ok].max())
    pen = hi + (min(g.shape) + 1) * (hi - lo + 1.0)
    rows, cols = linear_sum_assignment(np.where(ok, cost, pen))
    pairs = [(int(i), int(j)) for i, j in zip(rows, cols) if ok[i, j]]
    value = float(sum(math.log(g[i, j]) if criterion == "nash" else g[i, j]
                      for i, j in pairs))
    return pairs, value


def _check_staffable(g: np.ndarray, ok: np.ndarray, plan, slot_ids) -> None:
    """Every used slot must have at least one candidate with a positive gain."""
    for col, j in enumerate(slot_ids):
        if not (ok[:, col] & (g[:, col] > 0.0)).any():
            raise ValueError(
                f"slot {j} (bundle {tuple(plan.slots[j].bundle)}) has no candidate rep with a "
                f"positive gain, so it cannot be staffed; drop the slot or widen candidacy")


def _balance(vals: np.ndarray, target=None) -> dict:
    """`channel.balance_report`'s fields from the slot masses."""
    if vals.size == 0:
        return dict(k=0)
    tgt = float(np.mean(vals)) if target is None else float(target)
    return dict(
        k=int(vals.size),
        total=float(vals.sum()),
        target=tgt,
        mean=float(vals.mean()),
        min=float(vals.min()),
        max=float(vals.max()),
        spread_rel=float((vals.max() - vals.min()) / vals.mean()) if vals.mean() else 0.0,
        max_dev_rel=float(np.abs(vals - tgt).max() / tgt) if tgt else 0.0,
        log_sum=float(np.log(vals).sum()) if (vals > 0).all() else -math.inf,
    )


def state_stage2(cells, plan, *, reps=None, theta: float = 0.40, lam: float = 0.30,
                 filler_capture: str = "theta", criterion: str = "nash",
                 candidacy: bool = False) -> dict:
    """Staff a channel plan at state grain.  Same keys as `channel.stage2`.

    `districts` holds the used slots' indices into `plan.slots`, so `assignment` and `gains`
    are keyed by slot id.  With `candidacy=False` this is `channel.match` verbatim, which
    refuses a non-positive gain anywhere; with `candidacy=True` a rep is only offered the
    slots where it holds book, and the match is masked rather than the instance changed.
    """
    g, R, slot_ids = state_gain_matrix(cells, plan, reps=reps, theta=theta, lam=lam,
                                       filler_capture=filler_capture)
    ok = np.ones(g.shape, bool)
    if candidacy:
        book = _slot_sums(cells, plan, slot_ids,
                          np.asarray(cells.S, float)[_rep_rows(cells, reps)])
        ok = book > 0.0
    _check_staffable(g, ok, plan, slot_ids)
    pairs, value = (_match_masked(g, ok, criterion) if candidacy
                    else channel.match(g, criterion))
    assign = {slot_ids[j]: R[i] for i, j in pairs}
    gains = {slot_ids[j]: float(g[i, j]) for i, j in pairs}
    matched = {R[i] for i, _ in pairs}
    return dict(
        assignment=assign,                       # slot id -> rep
        gains=gains,                             # slot id -> that rep's utility
        value=value,                             # sum log g (nash) or sum g (utilitarian)
        criterion=criterion,
        reps=R, districts=slot_ids,
        unmatched_reps=[r for r in R if r not in matched],
        unstaffed_districts=[j for j in slot_ids if j not in assign],
        balance=_balance(_slot_mass(cells, plan, slot_ids)),
    )
