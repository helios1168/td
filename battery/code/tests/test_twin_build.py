"""
test_twin_build.py -- full national TIGER build (PLAN.md C.5, U4 "reproducible
adjacency build").  SLOW: downloads/extracts TIGER2020 if not already under
`data/tiger/` (~528 MB, gitignored) and rebuilds the Rook adjacency from scratch
(~65s on the machine this was authored on), then checks it reproduces the committed
`data/zcta_adjacency.npz` exactly.

    TD_SLOW=1 .venv/bin/python3 battery/code/tests/run_all.py -k twin_build
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import networkx as nx

SLOW = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import twin  # noqa: E402

ADJ = os.path.join(ROOT, "data", "zcta_adjacency.npz")


def test_build_reproduces_committed_adjacency():
    assert os.path.exists(ADJ), f"{ADJ} must be committed before this test can compare against it"
    cached = twin.load_adjacency(ADJ)

    t0 = time.time()
    shp = twin.fetch_tiger(verbose=True)
    fresh = twin.build_rook_adjacency(shp, verbose=True)
    dt = time.time() - t0

    n, m = len(fresh["zcta"]), len(fresh["edges"])
    G = nx.Graph(); G.add_nodes_from(range(n)); G.add_edges_from(map(tuple, fresh["edges"]))
    ncc = nx.number_connected_components(G)
    print(f"twin_build: n={n} m={m} components={ncc} "
          f"npz_size={os.path.getsize(ADJ)} build_seconds={dt:.1f}")

    assert np.array_equal(fresh["zcta"], cached["zcta"]), "zcta ordering must be reproducible"
    assert np.array_equal(fresh["edges"], cached["edges"]), "rook edges must be reproducible"
    assert n == cached["meta"]["n"] and m == cached["meta"]["m"]
    assert n > 30000 and m > 50000
