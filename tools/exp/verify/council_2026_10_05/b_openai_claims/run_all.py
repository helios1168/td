"""Run every b_openai_claims check: `"$TD_PY" -u tools/exp/verify/council_2026_10_05/b_openai_claims/run_all.py`.

Each script prints one `[ok]` or `[MISMATCH]` line per check and exits 1 on any mismatch. A line
marked ok means the brute force agrees with the verdict recorded in RESULTS.md, which may be that
a claim is refuted.
"""
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = ["check_t1_t3.py", "check_t2.py", "check_t4_t5.py", "check_m1.py", "check_extra.py"]

t_all = time.time()
failed = []
for name in SCRIPTS:
    t = time.time()
    r = subprocess.run([sys.executable, "-u", str(HERE / name)], cwd=HERE, capture_output=True, text=True)
    print(f"== {name} ({time.time() - t:.1f} s, exit {r.returncode})")
    print(r.stdout, end="")
    if r.returncode:
        print(r.stderr, end="")
        failed.append(name)
print(f"== total {time.time() - t_all:.1f} s; {'ALL OK' if not failed else 'FAILED: ' + ', '.join(failed)}")
sys.exit(1 if failed else 0)
