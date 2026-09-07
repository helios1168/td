"""oracle_owner_sets.py -- independent oracle for BORDERS_PLAN Track 1, mapping 3.

Brute-forces the owner-set rule in plain Python dicts (no numpy, no vectorisation) on random
200-zip toys and on hand-built degenerate cases, and compares with
`td.solvers.state_borders.owner_sets`.  Also checks the tie rule is deterministic and is the
documented "lower index wins", and checks the same rule against the inline fallback in
`tools/borders_report._home_and_owners`.

Run:
  /Users/ntlee/projects/td/.venv/bin/python3 \
      /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/oracle_owner_sets.py
"""
from __future__ import annotations

import sys

import numpy as np

ROOT = "/Users/ntlee/projects/td/.claude/worktrees/vbl"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + "/tools")

from td.solvers.state_borders import owner_sets  # noqa: E402
import borders_report  # noqa: E402


def brute(labels, state_idx, M, k, n_states):
    """Plain-Python plurality home + homeless fallback.  Ties -> lower index."""
    W = [[0.0] * k for _ in range(n_states)]
    for z in range(len(labels)):
        s = int(state_idx[z])
        if s >= 0:
            W[s][int(labels[z])] += float(M[z])
    home = []
    for j in range(k):
        col = [W[s][j] for s in range(n_states)]
        if sum(col) > 0:
            best, bs = -1.0, -1
            for s in range(n_states):          # strict > keeps the FIRST (lowest) index
                if col[s] > best:
                    best, bs = col[s], s
            home.append(bs)
        else:
            home.append(-1)
    owners = [[home[j] == s for j in range(k)] for s in range(n_states)]
    for s in range(n_states):
        if not any(owners[s]) and sum(W[s]) > 0:
            best, bj = -1.0, -1
            for j in range(k):
                if W[s][j] > best:
                    best, bj = W[s][j], j
            owners[s][bj] = True
    return home, owners


def compare(labels, state_idx, M, k, n_states, tag):
    h, o = owner_sets(labels, state_idx, M, k, n_states)
    bh, bo = brute(labels, state_idx, M, k, n_states)
    ok_h = h.tolist() == bh
    ok_o = o.tolist() == [[bool(v) for v in row] for row in bo]
    hb, ob = borders_report._home_and_owners(np.asarray(labels, int), np.asarray(state_idx, int),
                                             np.asarray(M, float), k, n_states)
    ok_rep = hb.tolist() == bh and ob.tolist() == [[bool(v) for v in r] for r in bo]
    print(f"  {tag:38s} home={'OK' if ok_h else 'DIFF'} owners={'OK' if ok_o else 'DIFF'} "
          f"report-fallback={'OK' if ok_rep else 'DIFF'}")
    if not ok_h:
        print("    impl ", h.tolist())
        print("    brute", bh)
    return ok_h and ok_o and ok_rep


def main():
    ok = True
    print("random 200-zip toys (k=6, 9 states, ~10% unknown):")
    for seed in range(12):
        rng = np.random.default_rng(seed)
        n, k, S = 200, 6, 9
        labels = rng.integers(0, k, size=n)
        state_idx = rng.integers(0, S, size=n)
        state_idx[rng.random(n) < 0.10] = -1
        M = rng.uniform(0.1, 10.0, size=n)
        ok &= compare(labels, state_idx, M, k, S, f"seed {seed}")

    print("ties and degenerates:")
    # exact tie in a district between states 0 and 2 -> lower index (0) must win
    ok &= compare([0, 0], [0, 2], [1.0, 1.0], 1, 3, "district tie: states 0 vs 2")
    h, _ = owner_sets(np.array([0, 0]), np.array([0, 2]), np.array([1.0, 1.0]), 1, 3)
    print(f"    -> home = {h.tolist()} (lower index wins: {h.tolist() == [0]})")
    ok &= h.tolist() == [0]

    # exact tie for a homeless state between districts 0 and 1 -> lower index
    lab = [0, 1, 0, 1]
    st = [0, 1, 2, 2]
    M = [10.0, 10.0, 1.0, 1.0]
    ok &= compare(lab, st, M, 2, 3, "homeless-state tie: D0 vs D1")
    _, o = owner_sets(np.array(lab), np.array(st), np.array(M), 2, 3)
    print(f"    -> owners[2] = {o[2].tolist()} (lower index wins: {o[2].tolist() == [True, False]})")
    ok &= o[2].tolist() == [True, False]

    ok &= compare([0, 1], [-1, -1], [1.0, 1.0], 2, 3, "every zip unknown state")
    ok &= compare([0, 0, 0], [0, 0, 0], [1.0, 1.0, 1.0], 3, 1, "two empty districts")
    ok &= compare([0], [0], [1.0], 1, 1, "singleton")
    ok &= compare([], [], [], 2, 3, "empty input")
    ok &= compare([0, 0], [1, 1], [1.0, 1.0], 2, 4, "states 0,2,3 carry no mass")
    ok &= compare([0, 1], [0, 0], [1.0, 1.0], 2, 1, "one state, two districts (both home 0)")
    ok &= compare([0, 0], [0, 0], [0.0, 0.0], 2, 1, "zero masses")

    # determinism: same input, 50 calls
    rng = np.random.default_rng(99)
    labels, state_idx = rng.integers(0, 5, 200), rng.integers(-1, 8, 200)
    M = rng.uniform(0.1, 5.0, 200)
    outs = {owner_sets(labels, state_idx, M, 5, 8)[1].tobytes() for _ in range(50)}
    print(f"  determinism over 50 calls: {len(outs)} distinct results (want 1)")
    ok &= len(outs) == 1

    print("\nALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
