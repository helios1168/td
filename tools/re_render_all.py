"""tools/re_render_all.py
Re-render all summary maps across all 18 scenarios with updated clean titles and full opportunity coverage.
"""
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
GEO_CACHE = "/Users/Shared/sv-ntlee/repos/td/data/geo"
ZCTA_SHP = "/Users/Shared/sv-ntlee/repos/td/data/tiger/2025/tl_2025_us_zcta520.shp"
PY = "/Users/Shared/sv-ntlee/repos/td/.venv/bin/python"
GROUPS_ARG = "G1=TX,NY,FL,NJ,IL,AZ,NC,PA,MI,OH,VA,GA,CO,MD;G2 adds=CT,IN,LA,MN,UT,WA"
BRAIN_DIR = Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07")

scenario_figures = [
    ("battery/results/option1_exact_merged", "figures/summary_option1.png"),
    ("battery/results/option2_exact_multichannel", "figures/summary_option2.png"),
    ("battery/results/scenario_A_51", "figures/summary_scenario_A.png"),
    ("battery/results/scenario_B_52", "figures/summary_scenario_B.png"),
    ("battery/results/scenario_C_51", "figures/summary_scenario_C.png"),
    ("battery/results/scenario_D_53", "figures/summary_scenario_D.png"),
    ("battery/results/scenario_E_52", "figures/summary_scenario_E.png"),
    ("battery/results/scenario_F_51", "figures/summary_scenario_F.png"),
    ("battery/results/scenario_G_52", "figures/summary_scenario_G.png"),
    ("battery/results/scenario_H_52", "figures/summary_scenario_H.png"),
    ("battery/results/scenario_I_53", "figures/summary_scenario_I.png"),
    ("battery/results/scenario_J_53", "figures/summary_scenario_J.png"),
    ("battery/results/scenario_K_52", "figures/summary_scenario_K.png"),
    ("battery/results/scenario_L_53", "figures/summary_scenario_L.png"),
    ("battery/results/grid_W3_A_51", "figures/summary_grid_W3_A.png"),
    ("battery/results/grid_W4_A_51", "figures/summary_grid_W4_A.png"),
    ("battery/results/grid_W4_B_52", "figures/summary_grid_W4_B.png"),
    ("battery/results/grid_W5_C_52", "figures/summary_grid_W5_C.png"),
]


def render_one(pair):
    run_d, fig_dest = pair
    run_path = REPO_ROOT / run_d
    dest_path = REPO_ROOT / fig_dest
    if not run_path.exists():
        return f"{run_d}: not found"
    env = os.environ.copy()
    env["TD_ZCTA_SHP"] = ZCTA_SHP
    cmd = [
        PY, str(REPO_ROOT / "tools/plan_summary.py"), str(run_path),
        "--geo-cache", GEO_CACHE,
        "--groups", GROUPS_ARG
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        return f"{run_d} error: {res.stderr}"
    src_png = run_path / "maps/summary.png"
    if src_png.exists():
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src_png, dest_path)
        if BRAIN_DIR.exists():
            shutil.copy(src_png, BRAIN_DIR / dest_path.name)
    return f"{run_d} -> {fig_dest} rendered successfully"


def main():
    print(f"Re-rendering all {len(scenario_figures)} scenario figures...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(render_one, scenario_figures))
    for r in results:
        print(r)
    print("All figures re-rendered!")


if __name__ == "__main__":
    main()
