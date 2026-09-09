"""milp_worker.py -- runs OR-Tools CP-SAT on the minimum-splits MILP, out of process.

This file runs under `.venv-opt`, not `.venv`: it imports only numpy, ortools and the standard
library, never `td`, so the frozen `.venv` pins (docs/APP.md, the zip50 anchor) are untouched by
whatever `ortools` needs.  `milp_engines._cpsat_solve` runs it by file path (`.venv-opt/bin/
python3 <this file> <npz> <json>`), not `-m td.solvers.milp_worker`: that module form imports
`td.solvers`, whose `__init__.py` imports `networkx`, which `.venv-opt` deliberately lacks.

`<npz>` carries the semantic inputs `td.solvers.state_splits.build_milp` itself takes --
`M_s`, `D`, `edges`, `tau`, `delta`, `eta` -- plus `z_lb`/`z_ub`, the already-applied `z`-block
overrides (anchors, `fix_roots`, bounds) from the caller's `SplitProblem`.  `<json>` is read as
the request (`time_limit`, `num_workers`) and overwritten in place with the result.

CP-SAT has no continuous variables, so `y` and the flow `f` are represented as integers counting
units of `UNIT = 1e-4`: `Y_sj = round(y_sj / UNIT)` in `[0, 1/UNIT]`, and every row that mixes
`y`/`f` with the boolean `z`/`r` block is multiplied through by `1/UNIT` so every coefficient
lands on an integer exactly (`eta/UNIT`, `(N-1)/UNIT`, `N/UNIT` are all exact given `UNIT = 1e-4`
and integer `eta*100`, `N`).  The one row whose real coefficients are not already exact under
that scaling is the mass band, `sum_s (M_s/tau) Y_sj`: those coefficients are rounded to the
nearest integer at an extra `BAND_SCALE = 1e6` of precision (so the row's overall scale is
`BAND_SCALE / UNIT`), which is the "round `M_s/tau * 1e6`" the plan calls for.

Both roundings mean the CP-SAT model is a slightly tighter feasible set than the true MILP (a
`y` share that needed more than four decimal digits of precision is simply unavailable), so its
optimum is an upper bound on the true split count, never a certificate -- it is reported here as
a primal engine only.
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
from ortools.sat.python import cp_model

UNIT = 1e-4                 # y and flow are represented as integer multiples of this
BAND_SCALE = 1_000_000      # extra precision for the band row's M_s/tau coefficients


def build_and_solve(M_s: np.ndarray, D: np.ndarray, edges: np.ndarray, tau: float, delta: float,
                    eta: float, z_lb: np.ndarray, z_ub: np.ndarray, *,
                    time_limit: float, num_workers: int) -> dict:
    """Build the discretised CP-SAT model and solve it; see the module docstring for the scaling.

    `D` is accepted for symmetry with `build_milp` but unused: the split-count objective does
    not need the compactness tie-break, and CP-SAT's own tie-breaking is not being verified here.
    """
    del D
    S, k = int(M_s.shape[0]), int(z_lb.shape[1])
    N = S
    model = cp_model.CpModel()
    y_max = int(round(1.0 / UNIT))
    f_max = int(round(max(N - 1.0, 0.0) / UNIT))

    Z = [[model.NewIntVar(int(round(z_lb[s, j])), int(round(z_ub[s, j])), f"z_{s}_{j}")
         for j in range(k)] for s in range(S)]
    R = [[model.NewBoolVar(f"r_{s}_{j}") for j in range(k)] for s in range(S)]
    Y = [[model.NewIntVar(0, y_max, f"y_{s}_{j}") for j in range(k)] for s in range(S)]

    edge_list = [(int(u), int(v)) for u, v in np.asarray(edges, int).reshape(-1, 2)]
    arcs = edge_list + [(v, u) for u, v in edge_list]
    F = [[model.NewIntVar(0, f_max, f"f_{a}_{j}") for j in range(k)] for a in range(len(arcs))]
    out_arcs = [[a for a, (u, v) in enumerate(arcs) if u == s] for s in range(S)]
    in_arcs = [[a for a, (u, v) in enumerate(arcs) if v == s] for s in range(S)]

    for s in range(S):
        model.Add(sum(Y[s][j] for j in range(k)) == y_max)
    eta_units = int(round(eta / UNIT))
    for s in range(S):
        for j in range(k):
            model.Add(Y[s][j] <= y_max * Z[s][j])
            model.Add(Y[s][j] >= eta_units * Z[s][j])
            model.Add(R[s][j] <= Z[s][j])

    coef = np.round(np.asarray(M_s, float) / float(tau) * BAND_SCALE).astype(np.int64)
    lo_band = int(round((1.0 - delta) * BAND_SCALE / UNIT))
    hi_band = int(round((1.0 + delta) * BAND_SCALE / UNIT))
    for j in range(k):
        total = sum(int(coef[s]) * Y[s][j] for s in range(S))
        model.Add(total >= lo_band)
        model.Add(total <= hi_band)

    for j in range(k):
        model.Add(sum(R[s][j] for s in range(S)) == 1)
    for a, (_u, v) in enumerate(arcs):
        for j in range(k):
            model.Add(F[a][j] <= f_max * Z[v][j])
    for s in range(S):
        for j in range(k):
            inflow = sum(F[a][j] for a in in_arcs[s])
            outflow = sum(F[a][j] for a in out_arcs[s])
            model.Add(Z[s][j] - N * R[s][j] - (inflow - outflow) <= 0)

    model.Minimize(sum(Z[s][j] for s in range(S) for j in range(k)))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_workers = max(1, int(num_workers))
    solver.parameters.relative_gap_limit = 0.0

    trajectory: list[list[float]] = []
    t0 = time.time()

    class _Trajectory(cp_model.CpSolverSolutionCallback):
        def OnSolutionCallback(self) -> None:
            trajectory.append([time.time() - t0, self.ObjectiveValue(), self.BestObjectiveBound()])

    status = solver.Solve(model, _Trajectory())
    result = dict(status=solver.StatusName(status), nodes=int(solver.NumBranches()),
                 dual_bound=float(solver.BestObjectiveBound()), trajectory=trajectory)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        z_val = [[int(solver.Value(Z[s][j])) for j in range(k)] for s in range(S)]
        y_val = [[solver.Value(Y[s][j]) / y_max for j in range(k)] for s in range(S)]
        result.update(objective=float(solver.ObjectiveValue()), z=z_val, y=y_val)
    return result


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: milp_worker.py <npz> <json>", file=sys.stderr)
        return 2
    npz_path, json_path = argv
    data = np.load(npz_path)
    with open(json_path, encoding="utf-8") as fh:
        request = json.load(fh)
    result = build_and_solve(data["M_s"], data["D"], data["edges"], float(data["tau"]),
                             float(data["delta"]), float(data["eta"]), data["z_lb"], data["z_ub"],
                             time_limit=request.get("time_limit", 60.0),
                             num_workers=request.get("num_workers", 1))
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
