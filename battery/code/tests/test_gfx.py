"""
test_gfx.py -- fast tests for the gfx graphics library (PLAN.md U7, Part D).

Renders every producer from the small fixtures under `tests/fixtures/gfx/` (built by
`code/gfx/fixtures_make.py`) and checks: the text-overlap lint passes, each render is
under 10s, `A` is always blue / `B` is always red, the instance-JSON schema validator
catches the documented violations, and the library never imports a solver module
(`territory`, `districting`, `contig_methods`) or `networkx` (dependency policy: gfx is
matplotlib + numpy + scipy only, with shapely/geopandas lazy inside
`geom.polys_from_shapes` and the `twin_map` CLI's `--shapes` branch).

The n=30k scale render lives in `test_gfx_scale.py` (SLOW=True) instead of here.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import tempfile
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

from gfx import charts, geom, schemas, style  # noqa: E402
from gfx.producers import (  # noqa: E402
    _common, calib_compare, instance_card, method_trace, run_summary, twin_audit, twin_map,
)

FX = os.path.join(HERE, "fixtures", "gfx")
GFX_DIR = os.path.join(ROOT, "code", "gfx")
RENDER_BUDGET_S = 10.0


def _tmp(name):
    return os.path.join(tempfile.mkdtemp(prefix="td_gfx_"), name)


def _timed(fn, *a, **kw):
    t0 = time.perf_counter()
    out = fn(*a, **kw)
    return out, time.perf_counter() - t0


# ------------------------------------------------------------------------- style
def test_palette_A_is_blue_B_is_red():
    assert style.PALETTE["A"] == "#2166ac"
    assert style.PALETTE["B"] == "#b2182b"


def test_rep_color_cycle_warns_past_20():
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        style.rep_color(3)
        assert not w
        style.rep_color(25)
        assert any("20-colour cycle" in str(x.message) for x in w)


def test_method_colors_are_tab10_by_order():
    colors = style.method_colors(["current", "brute", "scip"])
    assert len(set(colors.values())) == 3
    # same order -> same colours (tab10 cycled by REGISTRY order, not by name)
    assert style.method_colors(["a", "b"])["a"] != style.method_colors(["b", "a"])["a"]


def test_lint_text_overlap_detects_and_clears():
    fig, ax = plt.subplots()
    t1 = ax.text(0.5, 0.5, "hello", transform=ax.transAxes)
    t2 = ax.text(0.5, 0.5, "world", transform=ax.transAxes)
    assert style.lint_text_overlap(fig)  # same spot: must overlap
    t2.set_position((0.9, 0.9))
    assert style.lint_text_overlap(fig) == []
    plt.close(fig)


def test_check_text_overlap_raises_by_default_and_can_warn():
    import warnings
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, "a", transform=ax.transAxes)
    ax.text(0.5, 0.5, "b", transform=ax.transAxes)
    try:
        raised = False
        try:
            style.check_text_overlap(fig)
        except RuntimeError:
            raised = True
        assert raised
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            style.check_text_overlap(fig, warn=True)
            assert w
    finally:
        plt.close(fig)


def test_save_writes_png_and_sidecar_json():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    out = _tmp("smoke.png")
    style.save(fig, out, producer="test_gfx")
    assert os.path.exists(out)
    assert os.path.exists(out + ".json")
    import json
    sidecar = json.load(open(out + ".json"))
    assert sidecar["producer"] == "test_gfx"
    assert sidecar["dpi"] == style.RC["savefig.dpi"]


def test_tight_layout_reserves_suptitle_room():
    fig, axes = plt.subplots(1, 2)
    fig.suptitle("title")
    style.tight_layout(fig)  # must not raise; smoke test for the rect logic
    plt.close(fig)


# ------------------------------------------------------------------------- geom
def test_polys_from_pos_basic_shapes():
    rng = np.random.default_rng(0)
    pos = rng.uniform(0, 1, size=(30, 2))
    nodes = list(range(30))
    polys, bounds = geom.polys_from_pos(nodes, pos, pad_frac=0.035)
    assert set(polys) == set(nodes)
    assert all(len(polys[z]) >= 3 for z in nodes)
    xmin, xmax, ymin, ymax = bounds
    assert xmin < pos[:, 0].min() < pos[:, 0].max() < xmax
    assert ymin < pos[:, 1].min() < pos[:, 1].max() < ymax


def test_polys_from_pos_pad_is_relative_to_bbox():
    rng = np.random.default_rng(1)
    small = rng.uniform(0, 1, size=(20, 2))
    big = small * 100  # same shape, 100x the extent
    _, b_small = geom.polys_from_pos(list(range(20)), small, pad_frac=0.1)
    _, b_big = geom.polys_from_pos(list(range(20)), big, pad_frac=0.1)
    pad_small = b_small[0] - (small[:, 0].min() - 0)  # xmin_padded - 0 offset trick unusable;
    # simpler: recompute pad directly from bounds vs raw extents
    pad_small = small[:, 0].min() - b_small[0]
    pad_big = big[:, 0].min() - b_big[0]
    assert pad_big / pad_small > 50  # scales with bbox, not an absolute constant


def test_seam_width_thresholds():
    assert geom.seam_width(10) == 0.25
    assert geom.seam_width(500) == 0.25
    assert geom.seam_width(5000) == 0.0
    assert geom.seam_width(30000) == 0.0
    assert 0.0 < geom.seam_width(2000) < 0.25


def test_assert_equal_area_raises_on_lonlat():
    lonlat = [(-73.9, 40.7), (-118.2, 34.0), (-87.6, 41.8)]
    try:
        geom.assert_equal_area(lonlat)
        raised = False
    except ValueError:
        raised = True
    assert raised
    # a small-extent equal-area-like layout in [0, 1]^2 must not raise
    geom.assert_equal_area([(0.1, 0.2), (0.8, 0.9), (0.5, 0.5)])


def test_edge_segments_and_partition_boundary():
    pos = {0: (0, 0), 1: (1, 0), 2: (1, 1)}
    edges = [(0, 1), (1, 2)]
    segs = geom.edge_segments(edges, pos)
    assert segs.shape == (2, 2, 2)
    side = {0: "A", 1: "A", 2: "B"}
    boundary = geom.partition_boundary(edges, pos, lambda z: side[z])
    assert boundary.shape == (1, 2, 2)  # only edge (1, 2) crosses sides


def test_polys_from_shapes_with_shapely():
    from shapely.geometry import Polygon
    import geopandas as gpd

    gdf = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                      Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])]},
        index=["z1", "z2"],
    )
    polys, bounds = geom.polys_from_shapes(gdf)
    assert set(polys) == {"z1", "z2"}
    assert len(polys["z1"]) >= 4
    assert bounds[0] == 0.0 and bounds[1] == 2.0


# ------------------------------------------------------------------------- charts
def test_dodge_texts_resolves_overlap():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    t1 = ax.text(0.5, 0.5, "aaaa")
    t2 = ax.text(0.5, 0.5, "bbbb")
    charts.dodge_texts(ax, [t1, t2])
    assert style.lint_text_overlap(fig) == []
    plt.close(fig)


# ------------------------------------------------------------------------- schemas
def test_make_fixture_instance_is_valid_and_deterministic():
    d1 = schemas.make_fixture_instance(seed=5, n=20)
    d2 = schemas.make_fixture_instance(seed=5, n=20)
    assert schemas.validate_instance_json(d1) == []
    assert d1["nodes"] == d2["nodes"]
    assert d1["free_to_a"] == d2["free_to_a"]
    assert d1["A"] == d2["A"]


def test_validate_instance_json_catches_violations():
    d = schemas.make_fixture_instance(seed=1, n=15)
    assert schemas.validate_instance_json(d) == []

    missing = dict(d); del missing["edges"]
    assert schemas.validate_instance_json(missing)

    bad_len = dict(d); bad_len["A"] = d["A"][:-1]
    assert schemas.validate_instance_json(bad_len)

    bad_edge = dict(d); bad_edge["edges"] = d["edges"] + [[0, 999]]
    assert schemas.validate_instance_json(bad_edge)

    bad_free = dict(d); bad_free["free_to_a"] = list(d["free_to_a"]) + ["not_a_node"]
    assert schemas.validate_instance_json(bad_free)

    bad_row = dict(d)
    bad_row["rows"] = [dict(method="x", to_a=["not_a_node"])]
    assert schemas.validate_instance_json(bad_row)


# ------------------------------------------------------------------------- producers
def test_producer_instance_card():
    d = _common.load_json(os.path.join(FX, "instance_t0.json"))
    (fig,), dt = _timed(lambda: (instance_card.build(d),))
    assert style.lint_text_overlap(fig) == []
    assert dt < RENDER_BUDGET_S
    style.save(fig, _tmp("instance_card.png"), producer="test")


def test_producer_method_trace():
    rows = _common.load_jsonl(os.path.join(FX, "rows.jsonl"))
    instances = sorted({r["instance"] for r in rows})
    for inst in instances:
        (fig,), dt = _timed(lambda inst=inst: (method_trace.build(rows, inst),))
        assert style.lint_text_overlap(fig) == [], inst
        assert dt < RENDER_BUDGET_S
        plt_close(fig)


def plt_close(fig):
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_producer_run_summary_default_and_rho():
    rows = _common.load_jsonl(os.path.join(FX, "rows.jsonl"))
    instances = _common.load_csv(os.path.join(FX, "instances.csv"))
    summary = _common.load_csv(os.path.join(FX, "summary.csv"))
    (fig1,), dt1 = _timed(lambda: (run_summary.build_summary(rows, instances, summary),))
    assert style.lint_text_overlap(fig1) == []
    assert dt1 < RENDER_BUDGET_S
    plt_close(fig1)
    (fig2,), dt2 = _timed(lambda: (run_summary.build_rho_frontier(rows),))
    assert style.lint_text_overlap(fig2) == []
    assert dt2 < RENDER_BUDGET_S
    plt_close(fig2)


def test_producer_run_summary_tolerates_missing_columns():
    rows = [dict(method="current", instance="x", status="optimal", status_eff="optimal")]
    fig = run_summary.build_summary(rows, [], [])
    assert style.lint_text_overlap(fig) == []
    plt_close(fig)


def test_producer_twin_audit():
    stats = _common.load_json(os.path.join(FX, "twin_stats.json"))
    (fig,), dt = _timed(lambda: (twin_audit.build(stats),))
    assert style.lint_text_overlap(fig) == []
    assert dt < RENDER_BUDGET_S
    plt_close(fig)


def test_producer_twin_audit_tolerates_empty_stats():
    fig = twin_audit.build({})
    assert style.lint_text_overlap(fig) == []
    plt_close(fig)


def test_producer_twin_map():
    twin = _common.load_json(os.path.join(FX, "twin_instance.json.gz"))
    (fig,), dt = _timed(lambda: (twin_map.build(twin),))
    assert style.lint_text_overlap(fig) == []
    assert dt < RENDER_BUDGET_S
    plt_close(fig)


def test_producer_calib_compare():
    calib = _common.load_json(os.path.join(FX, "calib.json"))
    (fig,), dt = _timed(lambda: (calib_compare.build(calib),))
    assert style.lint_text_overlap(fig) == []
    assert dt < RENDER_BUDGET_S
    plt_close(fig)


def test_producer_calib_compare_tolerates_missing_scenarios():
    fig = calib_compare.build({"scenarios": {"S1_aligned": {}}})
    assert style.lint_text_overlap(fig) == []
    plt_close(fig)


# ------------------------------------------------------------------------- CLI form
def test_producer_cli_instance_card_end_to_end():
    out = _tmp("cli_instance_card.png")
    rc = instance_card.main([os.path.join(FX, "instance_t0.json"), "--out", out])
    assert rc == 0
    assert os.path.exists(out) and os.path.exists(out + ".json")


def test_producer_cli_run_summary_end_to_end():
    out = _tmp("cli_run_summary.png")
    rc = run_summary.main([os.path.join(FX, "rows.jsonl"), os.path.join(FX, "instances.csv"),
                           os.path.join(FX, "summary.csv"), "--out", out])
    assert rc == 0
    assert os.path.exists(out)


# ------------------------------------------------------------------------- dependency policy
_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+(networkx|geopandas|shapely)\b")
_SOLVER_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+(territory|districting|contig_methods)\b")


def _gfx_source_files():
    return sorted(glob.glob(os.path.join(GFX_DIR, "**", "*.py"), recursive=True))


def test_no_solver_imports_anywhere_in_gfx():
    offenders = []
    for path in _gfx_source_files():
        for lineno, line in enumerate(open(path), 1):
            if _SOLVER_IMPORT_RE.match(line):
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, offenders


def test_networkx_geopandas_shapely_only_indented_lazy_imports():
    """networkx: never. geopandas/shapely: only indented (inside a function body), per
    Part D's dependency rule -- a module-level (column-0) import would run even when the
    caller never touches TIGER geometry."""
    offenders = []
    for path in _gfx_source_files():
        for lineno, line in enumerate(open(path), 1):
            m = re.match(r"^(\s*)(?:import|from)\s+(networkx|geopandas|shapely)\b", line)
            if not m:
                continue
            indent, mod = m.group(1), m.group(2)
            if mod == "networkx" or indent == "":
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, offenders


def test_producers_have_no_live_solve_import():
    """Producers read files, never call a solver: no `nash_exact`, `solve_contiguous*`,
    or `T.solve` style call anywhere in gfx/producers."""
    banned = ("nash_exact", "solve_contiguous", "census(")
    offenders = []
    for path in glob.glob(os.path.join(GFX_DIR, "producers", "*.py")):
        text = open(path).read()
        for token in banned:
            if token in text:
                offenders.append(f"{path}: {token}")
    assert not offenders, offenders


def test_old_figure_scripts_are_untouched():
    """The frozen byte-identity anchor (PLAN.md Part D): this unit must not modify these
    files. A clean `git diff` against them (relative to the tree this worktree branched
    from) is the actual guarantee; here we just assert they still exist unmodified in the
    working tree (no staged/unstaged diff) as a fast sanity check."""
    frozen = [
        os.path.join(ROOT, "battery", "code", "mapviz.py"),
        os.path.join(ROOT, "battery", "code", "case_pipeline.py"),
        os.path.join(ROOT, "battery", "code", "c8_rho_sweep.py"),
        os.path.join(ROOT, "code", "mkfig_zip50.py"),
        os.path.join(ROOT, "code", "mkfig_census.py"),
    ]
    for f in frozen:
        assert os.path.exists(f), f
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", *frozen],
                             capture_output=True, text=True, cwd=ROOT, timeout=10)
    except Exception:
        return  # git unavailable in this environment; existence check above still ran
    assert out.returncode == 0 and out.stdout.strip() == "", out.stdout


def test_fixtures_directory_is_small():
    total = sum(os.path.getsize(os.path.join(FX, f)) for f in os.listdir(FX))
    assert total < 500 * 1024, f"{total} bytes"
