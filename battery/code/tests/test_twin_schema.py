"""
test_twin_schema.py -- U9: the two consumers of twin_stats.json against U3's real schema.

`tools/twin_export` (U3) is the source of truth for what `twin_stats.json` looks like --
it is the user-audited artifact that actually leaves the confidential work machine.  This
test builds a real stand-in export (via `tools/twin_export/tests/fixtures.py`, the same
route U3's own tests use) and checks the two repo-side consumers against it:

    (a) `code/synth.py::calibrate` -- every `CALIB_MAP` key resolves except the two that
        have no real-data definition (`zipf_s`, `n_metros` -- generator-only concepts,
        correctly left on LITERATURE_DEFAULTS and reported in `calib_missing`)
    (b) `code/gfx/producers/twin_audit.py` -- renders from the export with no crash and no
        text-overlap
    (c) the committed gfx fixture (`tests/fixtures/gfx/twin_stats.json`, itself a real
        export -- see its own header note) renders the same way

n is kept small (~700 ZCTAs) so this runs in the fast tier: it launches the twin_export
CLI four times (validate / stats / twin / validate --twin) as a subprocess, same as U3's
own `test_tiny_end_to_end`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
FIXTURES_GFX = os.path.join(HERE, "fixtures", "gfx")
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code"), TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)

import synth                                                  # noqa: E402
from gfx import style                                         # noqa: E402
from gfx.producers import _common, twin_audit                 # noqa: E402
from twin_export.tests import fixtures as FX                  # noqa: E402

PY = sys.executable
EXPECTED_MISSING = {"zipf_s", "n_metros"}


def _build_standin(tmpdir, side=27, seed=2):
    """Run the real twin_export CLI (validate/stats/twin/validate --twin) on a small
    stand-in instance and return the path to the resulting `twin_stats.json`."""
    G = FX.lattice_instance(side=side, n_rep_a=8, n_rep_b=8, n_states=4, seed=seed)
    paths = FX.write_inputs(G, tmpdir)
    common = ["--graph", paths["graph_csv"], "--opportunity", paths["opportunity"],
              "--sales", paths["sales"], "--reps", paths["reps"], "--states",
              paths["states"], "--min-support", "5", "--min-state", "100",
              "--out", tmpdir, "--quiet"]
    env = dict(os.environ)
    env["PYTHONPATH"] = TOOLS + os.pathsep + env.get("PYTHONPATH", "")
    stats_path = os.path.join(tmpdir, "twin_stats.json")
    twin_path = os.path.join(tmpdir, "twin_instance.json.gz")
    for argv in (["validate"] + common, ["stats"] + common,
                 ["twin"] + common + ["--stats", stats_path, "--yes"],
                 ["validate", "--twin", twin_path, "--stats", stats_path, "--quiet"]):
        r = subprocess.run([PY, "-m", "twin_export"] + argv, cwd=tmpdir, env=env,
                           capture_output=True, text=True)
        # exit 3 ("twin_check did NOT pass") is a tolerance-table verdict on THIS
        # particular random draw, not a schema problem -- the file is still written
        # (see __main__.py::cmd_twin) and is what this test cares about; anything else
        # (2 = privacy guard, 4 = input error, or a crash) is a real failure.
        assert r.returncode in (0, 3), "`%s` exited %d\n%s%s" % (argv[0], r.returncode,
                                                                  r.stdout, r.stderr)
    assert os.path.exists(stats_path), "twin_export must still write twin_stats.json"
    return stats_path


# ------------------------------------------------------------- (a) synth.calibrate
def test_calibrate_resolves_all_but_generator_only_keys():
    d = tempfile.mkdtemp()
    stats_path = _build_standin(d)
    with open(stats_path) as f:
        stats = json.load(f)

    c = synth.calibrate(stats_path, n=2000, fit_rho=False)
    missing = set(c["calib_missing"])
    assert missing == EXPECTED_MISSING, (
        "CALIB_MAP resolution drifted from U3's real schema; missing=%r, expected=%r"
        % (missing, EXPECTED_MISSING))
    n_total = len(synth.CALIB_MAP)
    n_hit = n_total - len(missing)
    # calibrate()'s own convention: "twin" only if nothing is missing, "literature" only
    # if everything is, "partial" for exactly this in-between case (n_hit > 0, some
    # missing) -- asserted against the code's convention, not a fixed string chosen here.
    assert c["calib_source"] == "partial", c["calib_source"]
    assert c["calibrated"] is True
    print("synth.calibrate on the stand-in: resolved %d/%d (missing %s)"
         % (n_hit, n_total, sorted(missing)))

    # the resolved values must be the kind of thing calibrate() goes on to use -- not None,
    # not accidentally still a raw dict/path fragment
    v = c["resolved"]
    for k in synth.CALIB_MAP:
        if k in missing:
            continue
        assert v[k] is not None, "%s resolved to None from a real export" % k

    # exercising a calibrated scenario end to end must not raise
    import territory as T
    Gg = synth.scenario("S8_twin", n=300, seed=1, stats=stats_path)
    assert T.validate(Gg) == []
    del stats


# --------------------------------------------------------- (b) gfx twin_audit, stand-in
def test_twin_audit_renders_from_standin():
    d = tempfile.mkdtemp()
    stats_path = _build_standin(d)
    stats = _common.load_json(stats_path)
    fig = twin_audit.build(stats)
    try:
        assert style.lint_text_overlap(fig) == []
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


# ------------------------------------------------------- (c) gfx twin_audit, committed fixture
def test_twin_audit_renders_from_committed_gfx_fixture():
    """The committed `tests/fixtures/gfx/twin_stats.json` is itself a real twin_export
    stand-in output (regenerated 2026-08-29, U9) -- validate it against the same reader."""
    path = os.path.join(FIXTURES_GFX, "twin_stats.json")
    stats = _common.load_json(path)
    assert "scale" in stats and "gini_M" in stats["scale"], \
        "the committed gfx fixture must carry U9's scale.gini_M like a real export does"
    fig = twin_audit.build(stats)
    try:
        assert style.lint_text_overlap(fig) == []
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)
