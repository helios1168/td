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
    ("battery/results/option1_exact_merged", "47_total_14n_11wh_21fi_1wifi", "47_14_11_21_1", "47_districts_14_national_districts_11_WH_districts_21_FI_districts_1_WIFI_districts", "summary_option1"),
    ("battery/results/option2_exact_multichannel", "46_total_14n_11wh_21fi_0wifi", "46_14_11_21_0", "46_districts_14_national_districts_11_WH_districts_21_FI_districts_0_WIFI_districts", "summary_option2"),
    ("battery/results/scenario_A_51", "51_total_13n_13wh_24fi_1wifi", "51_13_13_24_1", "51_districts_13_national_districts_13_WH_districts_24_FI_districts_1_WIFI_districts", "summary_scenario_A"),
    ("battery/results/scenario_B_52", "52_total_13n_14wh_24fi_1wifi", "52_13_14_24_1", "52_districts_13_national_districts_14_WH_districts_24_FI_districts_1_WIFI_districts", "summary_scenario_B"),
    ("battery/results/scenario_C_51", "51_total_12n_13wh_25fi_1wifi", "51_12_13_25_1", "51_districts_12_national_districts_13_WH_districts_25_FI_districts_1_WIFI_districts", "summary_scenario_C"),
    ("battery/results/scenario_D_53", "53_total_13n_14wh_25fi_1wifi", "53_13_14_25_1", "53_districts_13_national_districts_14_WH_districts_25_FI_districts_1_WIFI_districts", "summary_scenario_D"),
    ("battery/results/scenario_E_52", "52_total_12n_14wh_25fi_1wifi", "52_12_14_25_1", "52_districts_12_national_districts_14_WH_districts_25_FI_districts_1_WIFI_districts", "summary_scenario_E"),
    ("battery/results/scenario_F_51", "51_total_12n_13wh_24fi_2wifi", "51_12_13_24_2", "51_districts_12_national_districts_13_WH_districts_24_FI_districts_2_WIFI_districts", "summary_scenario_F"),
    ("battery/results/scenario_G_52", "52_total_12n_13wh_25fi_2wifi", "52_12_13_25_2", "52_districts_12_national_districts_13_WH_districts_25_FI_districts_2_WIFI_districts", "summary_scenario_G"),
    ("battery/results/scenario_H_52", "52_total_13n_13wh_24fi_2wifi", "52_13_13_24_2", "52_districts_13_national_districts_13_WH_districts_24_FI_districts_2_WIFI_districts", "summary_scenario_H"),
    ("battery/results/scenario_I_53", "53_total_13n_14wh_24fi_2wifi", "53_13_14_24_2", "53_districts_13_national_districts_14_WH_districts_24_FI_districts_2_WIFI_districts", "summary_scenario_I"),
    ("battery/results/scenario_J_53", "53_total_12n_14wh_25fi_2wifi", "53_12_14_25_2", "53_districts_12_national_districts_14_WH_districts_25_FI_districts_2_WIFI_districts", "summary_scenario_J"),
    ("battery/results/scenario_K_52", "52_total_14n_13wh_24fi_1wifi", "52_14_13_24_1", "52_districts_14_national_districts_13_WH_districts_24_FI_districts_1_WIFI_districts", "summary_scenario_K"),
    ("battery/results/scenario_L_53", "53_total_14n_14wh_24fi_1wifi", "53_14_14_24_1", "53_districts_14_national_districts_14_WH_districts_24_FI_districts_1_WIFI_districts", "summary_scenario_L"),
    ("battery/results/grid_W3_A_51", "51_total_13n_11wh_24fi_3wifi", "51_13_11_24_3", "51_districts_13_national_districts_11_WH_districts_24_FI_districts_3_WIFI_districts", "summary_grid_W3_A"),
    ("battery/results/grid_W4_A_51", "51_total_13n_11wh_23fi_4wifi", "51_13_11_23_4", "51_districts_13_national_districts_11_WH_districts_23_FI_districts_4_WIFI_districts", "summary_grid_W4_A"),
    ("battery/results/grid_W4_B_52", "52_total_12n_11wh_25fi_4wifi", "52_12_11_25_4", "52_districts_12_national_districts_11_WH_districts_25_FI_districts_4_WIFI_districts", "summary_grid_W4_B"),
    ("battery/results/grid_W5_C_52", "52_total_12n_10wh_25fi_5wifi", "52_12_10_25_5", "52_districts_12_national_districts_10_WH_districts_25_FI_districts_5_WIFI_districts", "summary_grid_W5_C"),
]


def render_one(entry):
    run_d, new_id, compact_id, verbose_name, legacy_stem = entry
    run_path = REPO_ROOT / run_d
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
        figures_dir = REPO_ROOT / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            figures_dir / f"{new_id}.png",
            figures_dir / f"{compact_id}.png",
            figures_dir / f"{verbose_name}.png",
            figures_dir / f"{legacy_stem}.png",
        ]
        for p in paths:
            shutil.copy(src_png, p)
            if BRAIN_DIR.exists():
                shutil.copy(src_png, BRAIN_DIR / p.name)
    return f"{run_d} -> {new_id} rendered successfully"


def main():
    print(f"Re-rendering all {len(scenario_figures)} scenario figures...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(render_one, scenario_figures))
    for r in results:
        print(r)
    print("All figures re-rendered!")


if __name__ == "__main__":
    main()
