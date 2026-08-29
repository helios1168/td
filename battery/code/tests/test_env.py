"""
test_env.py -- the contiguity programme's environment guard (PLAN.md U0c).

Fast (< 2 s).  Checks that every approved dependency imports and that each of the
three open-source MILP engines actually solves a two-variable knapsack in-process.
The CBC check is the one that catches the macOS code-signature SIGKILL documented in
requirements.txt (python-mip's cbcbox wheel).
"""
from __future__ import annotations
import subprocess, sys, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PINNED = dict(numpy="2.5.2", scipy="1.18.1", networkx="3.6.1", matplotlib="3.11.1")


def test_pinned_core_versions():
    import numpy, scipy, networkx, matplotlib
    got = dict(numpy=numpy.__version__, scipy=scipy.__version__,
               networkx=networkx.__version__, matplotlib=matplotlib.__version__)
    assert got == PINNED, f"core pins drifted (zip50 anchor depends on them): {got}"


def test_geo_stack_imports():
    import geopandas, shapely, pyogrio, pandas, pyproj  # noqa: F401


def test_highspy_solves():
    import highspy, numpy as np
    h = highspy.Highs(); h.silent()
    inf = highspy.kHighsInf
    h.addVars(2, np.zeros(2), np.ones(2))
    h.changeColsIntegrality(2, np.array([0, 1]), np.array([highspy.HighsVarType.kInteger] * 2))
    h.changeColsCost(2, np.array([0, 1]), np.array([-2.0, -3.0]))
    h.addRow(-inf, 1.0, 2, np.array([0, 1]), np.array([1.0, 1.0]))
    h.run()
    assert h.modelStatusToString(h.getModelStatus()) == "Optimal"
    assert abs(h.getInfo().objective_function_value + 3.0) < 1e-9


def test_pyscipopt_solves():
    import pyscipopt as scip
    m = scip.Model(); m.hideOutput()
    x = m.addVar(vtype="B"); y = m.addVar(vtype="B")
    m.addCons(x + y <= 1); m.setObjective(2 * x + 3 * y, "maximize")
    m.optimize()
    assert m.getStatus() == "optimal" and abs(m.getObjVal() - 3.0) < 1e-9


def test_python_mip_cbc_solves():
    # Run in a subprocess: a code-signature kill (SIGKILL) would otherwise take the
    # whole test runner down with it.
    code = ("import mip; m=mip.Model(solver_name='CBC'); m.verbose=0; "
            "x=m.add_var(var_type='B'); y=m.add_var(var_type='B'); m += x+y <= 1; "
            "m.objective=mip.maximize(2*x+3*y); s=m.optimize(); "
            "assert s == mip.OptimizationStatus.OPTIMAL and abs(m.objective_value-3) < 1e-9; print('ok')")
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    if p.returncode == -9 or p.returncode == 137:
        raise AssertionError("python-mip/CBC was SIGKILLed: invalid code signature in the "
                             "cbcbox wheel -- see the macOS note in requirements.txt")
    assert p.returncode == 0 and p.stdout.strip() == "ok", p.stderr[-2000:]
