"""Drive every tab of the Streamlit app once, headlessly, through `streamlit.testing.v1`.

Runs only under the app venv (`.venv-app`), which has streamlit; the solver venv has none, so
under `tests/run_all.py` from `.venv` every test here returns at once. Run it by hand:

    PYTHONPATH=$PWD .venv-app/bin/python3 tests/run_all.py -k app_smoke

`AppTest` executes the whole script the way a browser session would, so a traceback in any
tab, on whatever runs sit under `battery/results/app`, fails this test. It reads the hub's
results and never launches a driver: nothing here clicks a button.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

try:
    from streamlit.testing.v1 import AppTest
except ImportError:                              # the solver venv
    AppTest = None

TABS = ["Scenarios", "Map", "Reps", "Overrides", "Compare", "Timings"]


def test_every_tab_renders_without_an_exception():
    if AppTest is None:
        return
    at = AppTest.from_file(os.path.join(ROOT, "app", "main.py"), default_timeout=180).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert [t.label for t in at.tabs] == TABS
    assert [s.label for s in at.sidebar.selectbox] in ([], ["Scenario"], ["Scenario", "Instance"])
