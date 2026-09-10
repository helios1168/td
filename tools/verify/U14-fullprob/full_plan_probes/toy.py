"""Shared toy builder for the tools/full_plan.py probes.

Writes a format-2 (`td_instance_descaled/2`) instance whose per-state channel masses are
exactly what the caller asks for, so a level-0 band can be reasoned about by hand.
"""
from __future__ import annotations

import gzip
import json
import os
import sys

WT = "/Users/ntlee/projects/td/.claude/worktrees/full-problem"
for p in (WT, os.path.join(WT, "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

FILE_CHANNELS = ("national", "wh", "fi")
REPS = [f"rep{i}" for i in range(8)]


def write_v2_toy(path: str, spec: dict, *, zips_per_state: int = 2) -> dict:
    """`spec = {state: {"national": m, "wh": m, "fi": m}}`; mass split evenly over the state's
    zips.  Every zip carries two reps at 0.3/0.2 of the cell and 0.1 filler."""
    z_col, c_col, m_col, s_col, f_col, st_col = [], [], [], [], [], []
    zips_by_state = {}
    n = 0
    for st in sorted(spec):
        zs = []
        for i in range(zips_per_state):
            zid = f"{90000 + n:05d}"
            n += 1
            zs.append(zid)
            for c in FILE_CHANNELS:
                m = float(spec[st].get(c, 0.0)) / zips_per_state
                z_col.append(zid)
                c_col.append(c)
                m_col.append(m)
                s_col.append({REPS[n % len(REPS)]: 0.3, REPS[(n + 1) % len(REPS)]: 0.2})
                f_col.append(0.1)
                st_col.append(st)
        zips_by_state[st] = zs
    allz = [z for zs in zips_by_state.values() for z in zs]
    obj = dict(
        format="td_instance_descaled/2",
        nodes=dict(z=z_col, channel=c_col, m_rel=m_col, share=s_col, share_free=f_col,
                   state=st_col),
        edges=dict(u=allz[:-1], v=allz[1:]),
        firm={}, meta={},
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return zips_by_state


def patch_rook(adj: dict, polys: dict | None = None):
    """Monkeypatch `td.geo.state_rook`, as tests/test_full_plan_cli.py does."""
    from td import geo as td_geo
    orig = td_geo.state_rook
    td_geo.state_rook = lambda *a, **kw: (adj, polys or {})
    return orig, td_geo


def unpatch(orig, td_geo):
    td_geo.state_rook = orig
