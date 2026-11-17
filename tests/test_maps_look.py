"""tests/test_maps_look.py -- `tools/maps/look.py`, the td-free look of the territory maps that a
Snowflake notebook (Python 3.12) imports: it parses as Python 3.9 (the stricter lower bound), imports nothing
from `td` (or any of the repo's tools), and its colouring and label placement work on made-up shapes.
"""
from __future__ import annotations

import ast
import importlib.util
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LOOK = os.path.join(ROOT, "tools", "maps", "look.py")
ALLOWED = {"collections", "csv", "gzip", "os", "matplotlib", "numpy", "shapely", "pyproj", "__future__"}


def _tree() -> ast.Module:
    with open(LOOK, encoding="utf-8") as fh:
        return ast.parse(fh.read(), feature_version=(3, 9))     # fails on match, `with (a, b):` ...


def _load():
    spec = importlib.util.spec_from_file_location("maps_look_test", LOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_look_parses_as_python_39():
    # the lower bound: the runtime is 3.12, the 3.9 grammar is the stricter parse
    _tree()


def test_look_imports_nothing_from_td():
    roots = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import"
            roots.add(node.module.split(".")[0])
    assert roots <= ALLOWED, sorted(roots - ALLOWED)
    assert "td" not in roots and "tools" not in roots


def test_colouring_far_and_place_labels_on_made_up_shapes():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    look = _load()
    row = {f"d_{i}": shapely.box(i * 10_000, 0, i * 10_000 + 10_000, 10_000) for i in range(2)}   # side by side
    row["d_far"] = shapely.box(2_000_000, 0, 2_010_000, 10_000)
    near = look.neighbours(row)
    assert near["d_1"] == {"d_0"} and near["d_far"] == set()
    pal = ["#e6194b", "#3cb44b", "#4363d8", "#f58231"]
    c = look.colouring_far(row, near, palette=pal)
    assert set(c) == set(row) and set(c.values()) <= set(pal)
    assert all(c[a] != c[b] for a in near for b in near[a])        # side-by-side districts differ
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    placed = look.place_labels(ax, [(50, 50, "Alpha"), (50.2, 50.1, "Beta"), (500, 50, "Outside")],
                               near=look.NEAR[:1], leader=[])
    assert [t.get_text() for t in placed] == ["Alpha"]
    plt.close(fig)
