"""Which forced state makes a cell's national stage infeasible?  Re-runs one cell of a cell file
with each forced state left out in turn (and once as is), each run stopped as soon as the seq_N
stage either proves infeasibility or finishes its first coverage pass.  A feasible branch runs
the full pass time limit (180 s); an infeasible one usually proves in seconds.

    probe_force.py CELLS.json TAG OUT_DIR [--pairs]

PY defaults to $TD_ROOT/.venv/bin/python3, TD_ROOT to the repo root.
"""
import itertools
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import full_grid  # noqa: E402

PY = os.environ.get("PY") or os.path.join(os.environ.get("TD_ROOT", ROOT), ".venv", "bin", "python3")
cells_path, tag, out = sys.argv[1:4]
pairs = "--pairs" in sys.argv
cell = {c["tag"]: c for c in full_grid.load_cells(cells_path)}[tag]
forced = cell["flags"]["force_national"].split(",")


def probe(drop) -> str:
    flags = dict(cell["flags"], force_national=",".join(s for s in forced if s not in drop))
    d = os.path.join(out, "drop_" + ("_".join(drop) or "none"))
    os.makedirs(d, exist_ok=True)
    argv = full_grid.plan_argv(PY, flags, d)
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    verdict = "ended without a seq_N verdict"
    for line in p.stdout:
        if line.startswith("force-national:"):
            print("   ", line.rstrip())
        if line.startswith("seq_N/cover_N:"):
            verdict = "feasible (" + line.split(":", 1)[1].strip() + ")"
            break
        if line.startswith("seq_N: no solution"):
            verdict = "INFEASIBLE"
            break
    p.kill()
    p.wait()
    return verdict


print(f"{tag}: forced {forced}")
print(f"  as is: {probe(())}")
for s in forced:
    print(f"  without {s}: {probe((s,))}", flush=True)
if pairs:
    for a, b in itertools.combinations(forced, 2):
        print(f"  without {a},{b}: {probe((a, b))}", flush=True)
