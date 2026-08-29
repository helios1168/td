"""
test_gfx_scale.py -- the n=30k map scale test (PLAN.md U7 acceptance: "n=30k map renders
in < 60s with no seam haze"). SLOW=True (`run_all.py` skips it unless `TD_SLOW=1`).

The 30k-cell instance is built on the fly here, never committed (PLAN.md U7 binding
detail #2: "synthesise a 30k-cell fixture on the fly ... for the <60s / no-haze check").
Reports timings on stdout so a run with `-k gfx_scale` shows them.
"""
from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("MPLBACKEND", "Agg")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from gfx import geom, maps, style  # noqa: E402
from gfx.producers import twin_map  # noqa: E402

SLOW = True
N = 30_000
BUDGET_S = 60.0


def _make_30k_twin(seed=0):
    rng = np.random.default_rng(seed)
    pos = rng.uniform(0, 1, size=(N, 2))
    zs = [f"z{i:06d}" for i in range(N)]
    M = rng.lognormal(mean=1.0, sigma=0.8, size=N)
    A = rng.lognormal(mean=0.6, sigma=0.7, size=N)
    B = rng.lognormal(mean=0.6, sigma=0.7, size=N)
    n_rep_a, n_rep_b = 90, 90
    rep_a = [f"A{int(x)}" for x in rng.integers(0, n_rep_a, N)]
    rep_b = [f"B{int(x)}" for x in rng.integers(0, n_rep_b, N)]
    return {
        "meta": {"seed": seed, "graph_hash": "scale_test_30k"},
        "nodes": {"z": zs, "state": [None] * N, "A": A.tolist(), "B": B.tolist(),
                 "M": M.tolist(), "rep_a": rep_a, "rep_b": rep_b, "pos": pos.tolist()},
        "edges": {"u": [], "v": []},  # adjacency isn't needed for the map/heatmap timing
    }


def test_gfx_scale_polys_and_heatmap_render_30k_under_budget():
    rng = np.random.default_rng(1)
    pos = rng.uniform(0, 1, size=(N, 2))
    nodes = list(range(N))

    t0 = time.perf_counter()
    polys, bounds = geom.polys_from_pos(nodes, pos)
    t_polys = time.perf_counter() - t0
    assert set(polys) == set(nodes)
    assert all(len(polys[z]) >= 3 for z in nodes)

    style.use_rc()
    fig, ax = plt.subplots(figsize=(8, 8))
    values = dict(zip(nodes, rng.lognormal(size=N).tolist()))
    t1 = time.perf_counter()
    maps.heatmap(ax, polys, values, bounds=bounds, cmap="YlOrBr", title="30k scale test")
    t_draw = time.perf_counter() - t1
    t2 = time.perf_counter()
    style.save(fig, os.path.join(os.environ.get("TMPDIR", "/tmp"), "td_gfx_scale_30k.png"),
              producer="test_gfx_scale")
    t_save = time.perf_counter() - t2

    total = t_polys + t_draw + t_save
    print(f"\n[gfx_scale] n={N}: polys_from_pos={t_polys:.2f}s draw={t_draw:.2f}s "
         f"save={t_save:.2f}s total={total:.2f}s seam_width={geom.seam_width(N)}")
    assert geom.seam_width(N) == 0.0, "no seam haze at n>=5000"
    assert total < BUDGET_S, f"{total:.1f}s >= {BUDGET_S}s budget"


def test_gfx_scale_twin_map_producer_30k_under_budget():
    twin = _make_30k_twin()
    t0 = time.perf_counter()
    fig = twin_map.build(twin)
    dt = time.perf_counter() - t0
    print(f"\n[gfx_scale] twin_map.build at n={N}: {dt:.2f}s")
    overlaps = style.lint_text_overlap(fig)
    plt.close(fig)
    assert overlaps == []
    assert dt < BUDGET_S, f"{dt:.1f}s >= {BUDGET_S}s budget"


if __name__ == "__main__":
    test_gfx_scale_polys_and_heatmap_render_30k_under_budget()
    test_gfx_scale_twin_map_producer_30k_under_budget()
