"""warm_start_probe.py: does the greedy point get HiGHS past the empty incumbent?

The synthetic 95-slot joint model (`battery/results/full_problem/synthetic_v2.json.gz`, the
TIMINGS row: the default six bundles, k 18, band 0.8/1.2, n_max 6).  Prints `greedy_plan`'s
build time and coverage per bundle, then `cover_N` alone under HiGHS at 60 s and threads 2,
cold and warm.  The warm row should come back at least the greedy's N coverage.  If it does
not, a third row hands the whole vector to `highspy.Highs.setSolution` directly, to separate
"the point is not accepted" from "the z, y partial start is not completed".

    timeout 300 .venv/bin/python3 tools/verify/U14-fullprob/warm_start_probe.py [--anchors]

`--anchors` is the v3 shape that rejected the first greedy point: a state anchored on two N
slots (CA on the first two) plus `fixed_used={"N": 18}`, the greedy having to share CA
between its slots and fill all eighteen.

Never point this at the 161-slot v3 model: two CONUS solves may be running already.
"""
from __future__ import annotations

import dataclasses
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402

import full_plan as cli                                               # noqa: E402
from td import channels, instance as descaled                         # noqa: E402
from td.solvers import level0, milp_engines as me, state_splits as ss  # noqa: E402

SYN = os.path.join(ROOT, "battery", "results", "full_problem", "synthetic_v2.json.gz")
GEO = os.path.join(ROOT, "data", "geo")
TIME_LIMIT, THREADS = 60.0, 2


def build(anchored: bool = False):
    d = descaled.load_descaled(SYN)
    if tuple(d.channels) != tuple(channels.CHANNELS):
        d = channels.fine_split(d)
    state_list = cli._state_list(d)
    cells = channels.aggregate(d, state_list)
    edges = cli._state_edges(state_list, GEO)
    M = np.asarray(cells.M, float)
    cidx = {c: i for i, c in enumerate(cells.channels)}
    tau = float(M[:, [cidx["N_WH"], cidx["N_FI"]]].sum()) / 18.0
    bundles = {b: cli._bundle_channels(b) for b in channels.DEFAULT_BUNDLES}
    kw = dict(edges=edges, L=0.8 * tau, U=1.2 * tau, eta=0.01, n_max=6)
    problem = level0.build_level0(cells, bundles, **kw)
    if anchored:
        ca, lo = state_list.index("CA"), problem.slots["N"][0]
        problem = level0.build_level0(cells, bundles, anchors=[(ca, lo), (ca, lo + 1)],
                                      fixed_used={"N": 18}, **kw)
        print(f"anchors: CA on N slots {lo} and {lo + 1}; fixed_used N=18", flush=True)
    return problem


def coverage(problem, x):
    S, K = problem.n_state, problem.k
    y = x[problem.off_y:problem.off_y + S * K].reshape(S, K)
    return {b: float((problem.W[:, lo:hi] * y[:, lo:hi]).sum())
            for b, (lo, hi) in problem.slots.items()}


def direct_set_solution(problem, x):
    """The whole vector through `setSolution`, bypassing `milp_engines`' z, y partial start."""
    import highspy

    h = highspy.Highs()
    h.passModel(me._highs_lp(problem))
    h.setOptionValue("output_flag", False)
    h.setOptionValue("mip_rel_gap", 0.0)
    h.setOptionValue("time_limit", TIME_LIMIT)
    h.setOptionValue("threads", THREADS)
    sol = highspy.HighsSolution()
    sol.col_value = [float(v) for v in x]
    h.setSolution(sol)
    h.run()
    info = h.getInfo()
    ok = info.primal_solution_status == highspy.kSolutionStatusFeasible
    if not ok:
        return None, h.modelStatusToString(h.getModelStatus())
    return -float(info.objective_function_value), h.modelStatusToString(h.getModelStatus())


def main():
    t = time.time()
    problem = build(anchored="--anchors" in sys.argv[1:])
    print(f"model: {problem.k} slots, {problem.n_var} vars, {problem.A.shape[0]} rows, "
          f"built in {time.time() - t:.1f}s", flush=True)
    t = time.time()
    x, seeds = level0.greedy_plan(problem)
    g = time.time() - t
    cov = coverage(problem, x)
    used = int(x[problem.off_u:].sum())
    print(f"greedy: {g:.2f}s, {used} of {problem.k} slots used, coverage "
          + ", ".join(f"{b}={v:.6g}" for b, v in cov.items()), flush=True)

    cover_n = level0.cover_pass(problem, ["N"])
    rows = [("greedy", g, cov["N"], "warm_start")]
    for label, warm in (("cover_N cold", None), ("cover_N warm", x)):
        t = time.time()
        try:
            out = level0.solve_passes(problem, [cover_n], engine="highs",
                                      time_limit=TIME_LIMIT, threads=THREADS,
                                      warm_start=warm, warm_seconds=g)
            rec = out["passes"][-1]
            value, status = rec["value"], rec["status"]
        except ss.SolveFailure as exc:
            value, status = None, exc.reason
        rows.append((label, time.time() - t, value, status))
        print(f"{label}: value={value} status={status} ({rows[-1][1]:.1f}s)", flush=True)

    warm_value = rows[-1][2]
    if warm_value is None or warm_value < cov["N"] - 1e-6:
        current = dataclasses.replace(problem, c=-cover_n.c)
        t = time.time()
        value, status = direct_set_solution(current, x)
        rows.append(("cover_N setSolution(x)", time.time() - t, value, status))
        print(f"setSolution(x): value={value} status={status}", flush=True)

    print()
    print(f"| {'row':24} | {'seconds':>8} | {'cover_N value':>14} | status |")
    print(f"|{'-' * 26}|{'-' * 10}|{'-' * 16}|--------|")
    for name, secs, value, status in rows:
        v = "none" if value is None else f"{value:.6g}"
        print(f"| {name:24} | {secs:8.1f} | {v:>14} | {status} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
