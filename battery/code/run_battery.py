"""Re-run the full C1-C8 battery under the final code (d=0 + HiGHS tolerances)."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = ROOT / "battery" / "code"
OUT = str(ROOT / "battery" / "figures")
os.makedirs(OUT, exist_ok=True)

CASES = [
 dict(name="C1_aligned_seed1", scenario="S1_aligned", seed=1,
      title="C1: S1_aligned seed 1 (alpha=1, 4x4 reps)"),
 dict(name="C1_aligned_seed2", scenario="S1_aligned", seed=2,
      title="C1: S1_aligned seed 2 (alpha=1, 4x4 reps)"),
 dict(name="C2_entangled_a0", scenario="S2_entangled", seed=1,
      title="C2: S2_entangled alpha=0 (4A x 5B, dense)"),
 dict(name="C2_entangled_a05", scenario="S2_entangled", seed=1,
      overrides=dict(alpha=0.5), title="C2: entangled alpha=0.5 (4A x 5B)"),
 dict(name="C3_slivers_ms005", scenario="S3_slivers", seed=1, min_share=0.005,
      title="C3: S3_slivers min_share=0.5%"),
 dict(name="C3_slivers_ms02", scenario="S3_slivers", seed=1, min_share=0.02,
      title="C3: S3_slivers min_share=2%"),
 dict(name="C3_slivers_ms08", scenario="S3_slivers", seed=1, min_share=0.08,
      title="C3: S3_slivers min_share=8%"),
 dict(name="C4_separate", scenario="S4_separate", seed=1,
      title="C4: S4_separate rho_books=-0.5 (books separate)"),
 dict(name="C4_contested", scenario="S4_separate", seed=1,
      overrides=dict(rho_books=1.0), title="C4: rho_books=+1.0 (books heavily contested)"),
 dict(name="C5_states_free", scenario="S5_states", seed=1, respect_state=False,
      title="C5: S5_states, contiguity ignoring state lines"),
 dict(name="C5_states_resp", scenario="S5_states", seed=1, respect_state=True,
      title="C5: S5_states, contiguity respecting state lines"),
 dict(name="C6_tight", scenario="S6_tight", seed=1,
      title="C6: S6_tight sat=0.55, M near headroom bound"),
 dict(name="C6_loose", seed=1,
      overrides=dict(alpha=1.0, n_rep_a=4, n_rep_b=4, saturation=0.12),
      title="C6 contrast: same geometry, sat=0.12"),
 dict(name="C7_scale_n400", scenario="S1_aligned", seed=1, n=400,
      title="C7: S1_aligned at n=400 (4x4 reps)"),
 dict(name="C9_heavytail_seed1", scenario="S7_heavytail", seed=1,
      title="C9: S7_heavytail seed 1 (alpha=1, sales_tail_alpha=1.0/beta=3.5) vs C1 baseline"),
 dict(name="C9_heavytail_seed2", scenario="S7_heavytail", seed=2,
      title="C9: S7_heavytail seed 2 (alpha=1, sales_tail_alpha=1.0/beta=3.5) vs C1 baseline"),
]

def run_case(c):
    cfg = dict(n=200, rho=2e-3, outdir=OUT); cfg.update(c)
    p = f"/tmp/cfg_{c['name']}.json"
    with open(p, "w") as f: json.dump(cfg, f)
    t0 = time.time()
    r = subprocess.run([sys.executable, "case_pipeline.py", p], cwd=PIPELINE_DIR,
                       capture_output=True, text=True, timeout=1800)
    return c["name"], r.returncode, time.time() - t0, r.stdout[-400:], r.stderr[-400:]

def run_c8():
    t0 = time.time()
    r = subprocess.run([sys.executable, "c8_rho_sweep.py"], cwd=PIPELINE_DIR,
                       capture_output=True, text=True, timeout=1800)
    return "C8_rho_frontier", r.returncode, time.time() - t0, r.stdout[-400:], r.stderr[-400:]

jobs = [lambda c=c: run_case(c) for c in CASES] + [run_c8]
results = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for res in ex.map(lambda f: f(), jobs):
        results.append(res)
        print(f"[done {len(results)}/{len(jobs)}] {res[0]} rc={res[1]} {res[2]:.0f}s",
              flush=True)
        if res[1] != 0:
            print("  STDERR:", res[4], flush=True)

with open(f"{OUT}/battery_run_log.json", "w") as f:
    json.dump([dict(name=n, rc=rc, secs=s, tail=o, err=e)
               for n, rc, s, o, e in results], f, indent=1)
print("ALL DONE")
