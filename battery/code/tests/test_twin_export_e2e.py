"""test_twin_export_e2e.py -- U3's end-to-end acceptance on realistic stand-ins (SLOW).

Two instances, both driven through the real CLI in a subprocess:

  14  a 5000-ZCTA stand-in from code/synth.py with 90 reps per firm, heavy-tailed sales,
      12 states and fake 5-digit ids whose leading digits encode the state (including a
      "00" block).  This is the closest thing available to the confidential instance.
  15  a zero-inflated lattice: ~8% of ZCTAs are spatially clustered glue with A = B = M = 0,
      the fourth regime (sparse active zips) that real data adds.

`code/synth.py` is imported HERE, in the test -- never inside tools/twin_export, which has
to run on a work machine where this repo does not exist.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code"), TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)

import synth as S                                            # noqa: E402
from twin_export import _territory_vendored as V             # noqa: E402
from twin_export import io as IO                             # noqa: E402
from twin_export.tests import fixtures as FX                 # noqa: E402

SLOW = True
PY = sys.executable
ID_RE = re.compile(r"^[0-9]{5}$")


def _id_like(obj, path=""):
    """Every string value and dict key in the object that looks like a ZCTA id."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if ID_RE.match(str(k)):
                out.append("%s key %s" % (path, k))
            out.extend(_id_like(v, "%s.%s" % (path, k)))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_id_like(v, path))
    elif isinstance(obj, str) and ID_RE.match(obj):
        out.append("%s = %s" % (path, obj))
    return out


def _cli(argv, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = TOOLS + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([PY, "-m", "twin_export"] + argv, cwd=cwd, env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def _run_all(paths, d, min_support=20, extra=()):
    common = ["--graph", paths["graph_csv"], "--opportunity", paths["opportunity"],
              "--sales", paths["sales"], "--reps", paths["reps"], "--states", paths["states"],
              "--min-support", str(min_support), "--min-state", "100", "--out", d]
    common = list(common) + list(extra)
    times = {}
    for name, argv in (("validate", ["validate"] + common),
                       ("stats", ["stats"] + common + ["--explain"]),
                       ("twin", ["twin"] + common
                        + ["--stats", os.path.join(d, "twin_stats.json"), "--yes"]),
                       ("validate_twin", ["validate", "--twin",
                                          os.path.join(d, "twin_instance.json.gz"),
                                          "--stats", os.path.join(d, "twin_stats.json")])):
        t0 = time.time()
        code, out, err = _cli(argv + ["--quiet"], cwd=d)
        times[name] = time.time() - t0
        assert code == 0, "`%s` exited %d\n%s\n%s" % (name, code, out[-4000:], err[-4000:])
        if name == "twin":
            times["audit_table"] = out
        if name == "stats":
            times["stats_bytes"] = os.path.getsize(os.path.join(d, "twin_stats.json"))
    return times


# ------------------------------------------------------------------ 14. the stand-in
def test_standin_5000_end_to_end():
    d = tempfile.mkdtemp()
    G = S.make_instance(n=5000, n_rep_a=90, n_rep_b=90, alpha=0.7, rho_books=0.6,
                        n_states=12, sliver=0.02, saturation=0.25,
                        sales_tail_alpha=1.2, sales_tail_beta=3.5, seed=11)
    paths = FX.write_inputs(G, d, coords=True)
    zids = paths["zids"]
    assert len(set(zids)) == 5000 and all(len(z) == 5 for z in zids)
    assert any(z.startswith("00") for z in zids), "need a 00-prefixed state block"

    times = _run_all(paths, d)
    for k in ("graph.csv", "opportunity.csv", "sales.csv", "reps.csv"):
        assert os.path.exists(os.path.join(d, k))

    st = json.load(open(os.path.join(d, "twin_stats.json")))
    bad = [r["key"] for r in st["twin_check"]["rows"] if r["ok"] is False]
    assert st["twin_check"]["passed"], "twin_check failed on: %s" % bad

    # the twin must satisfy the model's own validity check, via the vendored function
    obj = IO.read_twin(os.path.join(d, "twin_instance.json.gz"))
    tinst = IO.twin_to_instance(obj)
    assert V.validate(tinst.to_schema_graph()) == []

    # --- what leaves, and how big it is -------------------------------------
    assert times["stats_bytes"] <= 120 * 1024, times["stats_bytes"]
    hits = _id_like(st)
    assert not hits, "twin_stats.json contains ZCTA-shaped strings: %s" % hits[:5]

    gz = os.path.getsize(os.path.join(d, "twin_instance.json.gz"))
    per_zip = gz / 5000.0
    print("\n  twin_instance.json.gz  %.1f KB at n=5000  (%.1f bytes/ZCTA)"
          % (gz / 1024.0, per_zip))
    print("  extrapolated to n=33000: %.2f MB" % (per_zip * 33000 / 1024.0 / 1024.0))
    print("  wall: validate %.1fs  stats %.1fs  twin %.1fs  validate --twin %.1fs"
          % (times["validate"], times["stats"], times["twin"], times["validate_twin"]))
    # PLAN.md C.2 budgets ~1 MB for the national instance; 10-120 bytes per ZCTA
    # brackets that comfortably at n = 33000
    assert 10.0 <= per_zip <= 120.0, per_zip

    # --- the privacy audit ---------------------------------------------------
    au = json.load(open(os.path.join(d, "twin_audit.json")))
    for f in ("M", "A", "B"):
        assert au["fields"][f]["exact_value_matches"] == 0, f
    sp = au["fields"]["M"]["spearman"]
    assert 0.90 <= sp <= 0.97, ("Spearman(M) = %.4f is outside [0.90, 0.97]; sigma=0.10 "
                                "predicts rho = 0.945" % sp)
    assert au["fields"]["M"]["corr_3hop_neighbourhood"] > 0.9
    assert au["verdict"].startswith("OK"), au["verdict"]
    assert "PRIVACY AUDIT" in times["audit_table"]
    assert os.path.getsize(os.path.join(d, "leaving.txt")) > 1000


# --------------------------------------------------------------- 15. glue regime
def test_zero_inflated_glue():
    d = tempfile.mkdtemp()
    G = FX.lattice_instance(side=30, n_rep_a=8, n_rep_b=8, n_states=4, seed=2, p_zero=0.08)
    dead = sum(1 for z in G.nodes if G.nodes[z]["M"] == 0.0)
    assert 0.05 <= dead / 900.0 <= 0.12, dead
    paths = FX.write_inputs(G, d)
    _run_all(paths, d, min_support=5)

    st = json.load(open(os.path.join(d, "twin_stats.json")))
    bad = [r["key"] for r in st["twin_check"]["rows"] if r["ok"] is False]
    assert st["twin_check"]["passed"], "twin_check failed on: %s" % bad
    assert abs(st["scale"]["p_glue"] - dead / 900.0) < 1e-6

    with gzip.open(os.path.join(d, "twin_instance.json.gz"), "rt") as f:
        tw = json.load(f)
    M = tw["nodes"]["M"]
    n_zero = sum(1 for m in M if m == 0.0)
    assert abs(n_zero - dead) <= 2, (n_zero, dead)
    for i, m in enumerate(M):
        if m == 0.0:
            assert tw["nodes"]["A"][i] == 0.0 and tw["nodes"]["B"][i] == 0.0
    obj = IO.read_twin(os.path.join(d, "twin_instance.json.gz"))
    assert V.validate(IO.twin_to_instance(obj).to_schema_graph()) == []
