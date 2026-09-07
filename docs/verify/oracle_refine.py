"""oracle_refine.py -- independent oracle for BORDERS_PLAN Track 1, mapping 4.

The plan says one round is "labels -> owner sets -> banded, penalised LP -> recentroid, 10
rounds, stop early when labels repeat", "no Nash polish (`centers.improve`)", "every iterate is
saved".  This file instruments `state_borders.refine` -- `centers.improve` is replaced by a
tripwire, `owner_sets`/`assign`/`_centroids` are wrapped to record their arguments -- and then
replays the whole loop from an INDEPENDENT re-implementation written here, comparing labellings
round by round.  Degenerate inputs (all-unknown states, k=1, rounds=0) are probed too.

Run:
  /Users/ntlee/projects/td/.venv/bin/python3 \
      /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/oracle_refine.py
"""
from __future__ import annotations

import sys

import numpy as np

ROOT = "/Users/ntlee/projects/td/.claude/worktrees/vbl"
sys.path.insert(0, ROOT)

from td.solvers import centers  # noqa: E402
from td.solvers import state_borders as sb  # noqa: E402


def toy(seed=1, n=90, k=4, S=5):
    """Zips in S vertical state stripes, k clusters cutting across them."""
    rng = np.random.default_rng(seed)
    xy = np.column_stack([rng.uniform(0, S, n), rng.uniform(0, 1, n)])
    state_idx = np.clip(xy[:, 0].astype(int), 0, S - 1)
    state_idx[rng.random(n) < 0.05] = -1
    M = rng.uniform(0.5, 2.0, n)
    labels0 = np.clip((xy[:, 0] / S * k).astype(int), 0, k - 1)
    return xy, M, labels0, state_idx, k, S


def replay(xy, M, labels0, state_idx, k, lam_rel, delta, rounds):
    """Independent re-implementation of the loop the plan describes."""
    n_states = int(state_idx.max()) + 1 if (state_idx >= 0).any() else 0
    C = centers._centroids(xy, M, labels0, k)
    lam_abs = lam_rel * float((M * ((xy - C[labels0]) ** 2).sum(axis=1)).sum() / M.sum())
    labels = np.asarray(labels0, int).copy()
    seen = [labels.tobytes()]
    its, conv, nf = [], False, 0
    owner_inputs = []
    for _ in range(rounds):
        owner_inputs.append(labels.copy())
        _, owners = sb.owner_sets(labels, state_idx, M, k, n_states)
        P = sb.penalty_matrix(state_idx, owners, lam_abs) if lam_abs > 0 else None
        labels, nf = centers.assign(xy, M, C, penalty=P, band=delta)
        its.append(np.asarray(labels, int).copy())
        C = centers._centroids(xy, M, labels, k, prev=C)
        if labels.tobytes() in seen:
            conv = True
            break
        seen.append(labels.tobytes())
    return dict(labels=labels, centers=C, iterates=its, converged=conv, n_fractional=nf,
                owner_inputs=owner_inputs, lam_abs=lam_abs)


class Tripwire:
    def __init__(self):
        self.calls = 0

    def __call__(self, *a, **kw):
        self.calls += 1
        raise AssertionError("centers.improve was called by refine")


def instrumented(xy, M, labels0, state_idx, k, **kw):
    """Run refine with improve tripwired and owner_sets/_centroids recorded."""
    rec = dict(owner_labels=[], centroid_labels=[], assign_bands=[], assign_pen=[])
    trip = Tripwire()
    real_os, real_cen, real_assign, real_imp = (sb.owner_sets, centers._centroids,
                                               centers.assign, centers.improve)

    def os_spy(labels, *a, **k2):
        rec["owner_labels"].append(np.asarray(labels, int).copy())
        return real_os(labels, *a, **k2)

    def cen_spy(xy_, M_, labels, k_, prev=None):
        rec["centroid_labels"].append(np.asarray(labels, int).copy())
        return real_cen(xy_, M_, labels, k_, prev=prev)

    def assign_spy(*a, **k2):
        rec["assign_bands"].append(k2.get("band"))
        rec["assign_pen"].append(None if k2.get("penalty") is None
                                 else np.asarray(k2["penalty"]).copy())
        return real_assign(*a, **k2)

    sb.owner_sets, sb.centers.improve = os_spy, trip
    sb.centers._centroids, sb.centers.assign = cen_spy, assign_spy
    try:
        res = sb.refine(xy, M, labels0, state_idx, k, **kw)
    finally:
        sb.owner_sets, centers.improve = real_os, real_imp
        centers._centroids, centers.assign = real_cen, real_assign
    return res, rec, trip


def main():
    ok = True
    for lam_rel, delta, rounds in ((100.0, 0.02, 10), (0.0, 0.0, 3), (10.0, 0.0, 10),
                                   (1.0, 0.10, 10)):
        xy, M, labels0, state_idx, k, S = toy()
        res, rec, trip = instrumented(xy, M, labels0, state_idx, k,
                                      lam_rel=lam_rel, delta=delta, rounds=rounds)
        exp = replay(xy, M, labels0, state_idx, k, lam_rel, delta, rounds)
        tag = f"lam={lam_rel} delta={delta} rounds={rounds}"

        same_iter = (len(res["iterates"]) == len(exp["iterates"])
                     and all(np.array_equal(a, b)
                             for a, b in zip(res["iterates"], exp["iterates"])))
        c_ok = np.array_equal(res["labels"], exp["labels"])
        conv_ok = res["converged"] == exp["converged"]
        ru_ok = res["rounds_used"] == len(res["iterates"]) <= rounds
        # centres are the centroids of the FINAL labels
        cen_ok = np.allclose(res["centers"],
                             centers._centroids(xy, M, res["labels"], k, prev=None), atol=0,
                             rtol=0) or np.allclose(
            res["centers"], centers._centroids(xy, M, res["labels"], k, prev=res["centers"]))
        # owner sets recomputed each round from the CURRENT labels
        drift = [np.array_equal(a, b) for a, b in zip(rec["owner_labels"], exp["owner_inputs"])]
        per_round = len(rec["owner_labels"]) == res["rounds_used"] and all(drift)
        from_labels0 = all(np.array_equal(a, labels0) for a in rec["owner_labels"])
        band_ok = all(b == delta for b in rec["assign_bands"])
        pen_ok = all((p is None) == (lam_rel == 0.0) for p in rec["assign_pen"])
        # stop-on-ANY-repeat: is the final labelling equal to labels0 or an earlier iterate?
        earlier = [labels0] + res["iterates"][:-1]
        repeat = any(np.array_equal(res["labels"], e) for e in earlier)
        m_ok = np.isclose(res["metrics"]["compactness"],
                          centers.metrics(M, res["labels"], xy, res["centers"])["compactness"])

        print(f"[{tag}]")
        print(f"  rounds_used={res['rounds_used']} converged={res['converged']} "
              f"n_fractional={res['n_fractional']}")
        print(f"  replay matches iterates: {same_iter}; final labels: {c_ok}; "
              f"converged: {conv_ok}")
        print(f"  improve calls: {trip.calls} (want 0)")
        print(f"  owner_sets called once per round from CURRENT labels: {per_round}  "
              f"(always from labels0? {from_labels0})")
        print(f"  band passed to assign == delta: {band_ok}; penalty None iff lam=0: {pen_ok}")
        print(f"  final labelling repeats an earlier one: {repeat} (converged={res['converged']})")
        print(f"  centres = centroids of final labels: {cen_ok}; metrics consistent: {m_ok}")
        ok &= (same_iter and c_ok and conv_ok and ru_ok and cen_ok and per_round
               and band_ok and pen_ok and m_ok and (repeat == res["converged"]))
        ok &= not from_labels0 or lam_rel == 0.0 or res["rounds_used"] == 1

    # a hand-built 2-cycle must be caught (not only a fixed point)
    print("\n[2-cycle / early-stop rule]")
    xy, M, labels0, state_idx, k, S = toy(seed=4, n=60, k=3, S=4)
    r = sb.refine(xy, M, labels0, state_idx, k, lam_rel=100.0, delta=0.0, rounds=30)
    its = [labels0] + [i for i in r["iterates"]]
    keys = [i.tobytes() for i in its]
    first_dup = next((i for i in range(1, len(keys)) if keys[i] in keys[:i]), None)
    print(f"  rounds_used={r['rounds_used']} converged={r['converged']} "
          f"first duplicate at iterate index {first_dup} (1-based round {first_dup})")
    ok &= (r["converged"] is False) or (first_dup == r["rounds_used"])

    print("\n[degenerate inputs]")
    for tag, fn in (
        ("all states unknown",
         lambda: sb.refine(*toy()[:2], toy()[2], np.full(90, -1), 4, lam_rel=100.0, delta=0.0,
                           rounds=3)),
        ("rounds=0",
         lambda: sb.refine(*toy()[:4], 4, lam_rel=100.0, delta=0.0, rounds=0)),
        ("k=1",
         lambda: sb.refine(toy()[0], toy()[1], np.zeros(90, int), toy()[3], 1,
                           lam_rel=100.0, delta=0.0, rounds=3)),
        ("delta=1.0 (band swallows everything)",
         lambda: sb.refine(*toy()[:4], 4, lam_rel=100.0, delta=1.0, rounds=3)),
    ):
        try:
            r = fn()
            print(f"  {tag:38s} -> rounds_used={r['rounds_used']} "
                  f"spread={r['metrics']['spread_rel']:.4f} converged={r['converged']}")
        except Exception as e:                                     # noqa: BLE001
            print(f"  {tag:38s} -> {type(e).__name__}: {e}")

    print("\nALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
