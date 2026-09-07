"""test_state_splits_cli.py -- tools/state_splits.py: the driver's `--unanchor` release rule.

Pure-function test on synthetic state/district/mass arrays; no instance file, no solve.  The
six-state path toy in test_state_splits.py has no anchors-per-state notion worth exercising here
(k=2, at most one anchor per state), so this builds the smallest `ctx`-shaped stand-in that
`_release_anchors` actually reads: `state_idx`, `labels0`, `M`, `k`.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import state_splits as cli                    # noqa: E402


class _Ctx:
    """The fields `_release_anchors` reads off a real `borders_report.Ctx`, built by hand."""
    def __init__(self, state_idx, labels0, M, k):
        self.state_idx = np.asarray(state_idx)
        self.labels0 = np.asarray(labels0)
        self.M = np.asarray(M, float)
        self.k = k


def test_unanchor_with_a_cap_keeps_the_highest_mass_districts_and_releases_the_rest():
    """State 0 is anchored in three districts (2, 4, 5) with committed masses 10, 6, 6.  A
    cap of 2 keeps the top two by mass -- district 2, then district 4 over the tied district 5
    by ascending index -- and releases only district 5, the minimum surplus."""
    ctx = _Ctx(state_idx=[0, 0, 0, 0, 0, 0, 1],
              labels0=[2, 2, 4, 4, 5, 5, 3],
              M=[5.0, 5.0, 3.0, 3.0, 3.0, 3.0, 1.0], k=6)
    anchors = [(0, 2), (0, 4), (0, 5)]
    kept, info = cli._release_anchors(anchors, {0: 2}, [0], ctx)

    assert kept == [(0, 2), (0, 4)]
    assert info[0] == ([2, 4], [5])


def test_unanchor_without_a_cap_releases_every_anchor():
    """No `--cap` on the state: `--unanchor` keeps its original behaviour and releases all of
    it, the same as before this state's cap-aware release existed."""
    ctx = _Ctx(state_idx=[0, 0], labels0=[2, 4], M=[5.0, 5.0], k=6)
    kept, info = cli._release_anchors([(0, 2), (0, 4)], {}, [0], ctx)

    assert kept == []
    assert info[0] == ([], [2, 4])


def test_unanchor_never_releases_more_than_the_cap_forces():
    """A cap at or above the anchored count needs no release at all."""
    ctx = _Ctx(state_idx=[0, 0], labels0=[2, 4], M=[5.0, 5.0], k=6)
    kept, info = cli._release_anchors([(0, 2), (0, 4)], {0: 2}, [0], ctx)

    assert kept == [(0, 2), (0, 4)]
    assert info[0] == ([2, 4], [])
