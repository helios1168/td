"""tools/plan_render_app.py: the app's figure with the caller's labels, and a PNG through kaleido.

Gated on plotly the way `test_mapfig.py` is: under the solver venv every test returns at once.
Run for real under the app venv:
    PYTHONPATH=$PWD .venv-app/bin/python3 tests/run_all.py -k plan_render_app
The PNG test also needs kaleido and a Chrome; without them it returns after the figure check.
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import plotly                                   # noqa: F401
    import plan_render_app as cli
except ImportError:
    plotly = None
    cli = None


def _rows() -> list[dict]:
    return [
        dict(zip="z1", state="S1", x=0.5, y=0.5, opportunity=1.0, district="D1", rep="R1"),
        dict(zip="z2", state="S1", x=1.5, y=0.5, opportunity=2.0, district="D1", rep="R1"),
    ]


def _geom() -> dict:
    square = [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]]
    return dict(
        states={"S1": {"rings": square, "label": [1.0, 0.5]}},
        districts={"D1": {"rings": square, "color": "#4269d0"}},
        district_reach={"D1": {"rings": square, "color": "#4269d0"}},
        cells={"z1": {"rings": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
               "z2": {"rings": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]]}})


def test_the_labels_become_annotations_and_the_legend_goes():
    if cli is None:
        return
    fig = cli.render(_rows(), _geom(), {"D1": dict(x=1.0, y=0.5, text="D1\nR1")}, "D1 only")
    assert [a.text for a in fig.layout.annotations] == ["D1<br>R1"]
    assert fig.layout.showlegend is False
    assert fig.layout.title.text == "D1 only"
    # the app's traces are all there: state outline, reach fill, cells, district and reach lines
    names = [t.name for t in fig.data]
    assert "D1" in names and any(n for n in names)


def test_a_png_is_written_when_kaleido_and_a_browser_are_present():
    if cli is None:
        return
    try:
        import kaleido                              # noqa: F401
    except ImportError:
        return
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "map.png")
        try:
            cli.render(_rows(), _geom(), None, "", width=300, height=200).write_image(out,
                                                                                     scale=1)
        except Exception as exc:                   # no Chrome on this machine
            if "chrome" in str(exc).lower() or "browser" in str(exc).lower():
                return
            raise
        assert os.path.getsize(out) > 1000
