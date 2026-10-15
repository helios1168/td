"""verify.py -- an independent check of a connectivity verdict (#142): the instance's MILP with
single-commodity flow rows in SCIP, no constraint handler and no separator rows.

    "$TD_PY" -u tools/exp/bnc/verify.py <instance.json.gz> [--time-limit 1800]

The lazy-cut arms (b, c) rest on `sepcuts`' separator rows; this solves the same model with the
textbook flow formulation of connectivity instead, so an `infeasible` or `optimal` verdict of arm b
or c can be confirmed by a model that shares none of their cut code.  A district with a root body
sends one unit from it to every other vertex it owns and every other body; a district with none picks
a root r_v (Σ r = 1, r_v ≤ x_v) and every other owned vertex needs net inflow 1.  Prints a result
line (status, objective, seconds, and whether the drawing is connected by `sepcuts.Graphs`).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import capture  # noqa: E402
import inst_io  # noqa: E402
import sepcuts  # noqa: E402

arms = capture.sibling("bnc_arms", "arms.py")
export = capture.sibling("bnc_export", "export.py")


def flow_model(inst, log=print):
    """The instance's SCIP model with the flow rows added; (model, x variables)."""
    from pyscipopt import quicksum
    model, xs = arms.scip_model(inst)
    for j in inst.js:
        nodes = sorted(inst.nodes[j])
        fixed, root = inst.fixed[j], inst.root.get(j)
        n = len(nodes)
        x = {v: (1.0 if v in fixed else xs[inst.xcol[v, j]]) for v in nodes}
        arcs = {}
        for a in nodes:
            for b in inst.adj[j][a]:
                if b != root:
                    arcs[a, b] = model.addVar(name=f"f_{j}_{a}_{b}", lb=0.0, ub=float(n), vtype="C")
        rv = {}
        if root is None:
            rv = {v: model.addVar(name=f"r_{j}_{v}", vtype="B") for v in nodes}
            model.addCons(quicksum(rv.values()) == 1)
            for v in nodes:
                model.addCons(rv[v] <= x[v])
        for (a, b), f in arcs.items():
            if b not in fixed:
                model.addCons(f <= float(n) * x[b])
            if a not in fixed:
                model.addCons(f <= float(n) * x[a])
        inflow = {v: [] for v in nodes}
        outflow = {v: [] for v in nodes}
        for (a, b), f in arcs.items():
            inflow[b].append(f)
            outflow[a].append(f)
        for v in nodes:
            if v == root:
                continue
            net = quicksum(inflow[v]) - quicksum(outflow[v])
            if root is None:
                model.addCons(net >= x[v] - float(n) * rv[v])
            elif v in fixed:
                model.addCons(net == 1.0)
            else:
                model.addCons(net == x[v])
    return model, xs


def run(inst, time_limit: float, log=print) -> dict:
    t0 = time.time()
    model, xs = flow_model(inst, log)
    model.setRealParam("limits/gap", 0.0)
    model.setRealParam("limits/absgap", arms.ABS_GAP)
    model.setRealParam("limits/time", float(time_limit))
    log(f"verify {inst.id}: SCIP with flow rows, {model.getNVars()} variables, {model.getNConss()} rows")
    model.optimize()
    st = model.getStatus()
    out = {"instance": inst.id, "scip_status": st, "seconds": time.time() - t0,
           "nodes": int(model.getNNodes()), "objective": None, "connected": None}
    if model.getNSols() > 0:
        sol = model.getBestSol()
        x = np.zeros(inst.n)
        for i in sorted(inst.xcol.values()):
            x[i] = model.getSolVal(sol, xs[i])
        out["objective"] = float(model.getSolObjVal(sol))
        out["connected"] = not sepcuts.Graphs(inst).detached(np.round(x))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("instance")
    ap.add_argument("--time-limit", type=float, default=1800.0)
    ap.add_argument("--out", default=None, help="also write the result as JSON here")
    a = ap.parse_args(argv)
    path = os.path.abspath(a.instance)
    data, digest = inst_io.read(path)
    prov = export.provenance()
    res = run(inst_io.loads(data, path), a.time_limit)
    res.update(time_limit=a.time_limit, instance_sha256=digest, instance_path=path, **prov)
    print(res)
    if a.out:
        import json
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
