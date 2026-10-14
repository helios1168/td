"""tests/test_division_scope.py -- `run.py --states`'s planning graph (`induced_graph`).

Induced on New Jersey, the committed polygon graph keeps exactly NJ's 598 shipped vertices, so a
ZCTA with no IFA opportunity is still a vertex (checked against the NJ extract when a worktree has
it), no vertex outside NJ, and every edge, border and connector has both ends inside.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
NJ_EXTRACT = os.path.join(ROOT, "runs", "exp", "contig", "nj", "_inst", "ifa_nj.json.gz")


def _run():
    if "contig_run" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "contig_run", os.path.join(ROOT, "tools", "exp", "contig", "run.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_run"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_run"]


def test_nj_induced_graph():
    from td import data, geo
    full = geo.polygon_graph()
    g = _run().induced_graph(full, ("NJ",))
    ref = geo.read_reference()
    nj = set(ref.loc[(ref["graph_vertex"] == "1") & (ref["state"] == "NJ"), "zcta"])
    assert len(g["vertices"]) == 598 and set(g["vertices"]) == nj
    assert all(g["state"][z] == "NJ" for z in g["vertices"])
    assert set(g["aland"]) == nj
    for e in g["edges"] + list(g["border"]) + g["connectors"]:
        assert e[0] in nj and e[1] in nj, e
    if os.path.exists(NJ_EXTRACT):
        ext = data.load(NJ_EXTRACT)
        opp = {z for z, f, m in zip(ext.z, ext.channel, ext.m_rel) if m > 0}
        zero = nj - opp
        assert zero and zero <= set(g["vertices"])
