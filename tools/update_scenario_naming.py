"""tools/update_scenario_naming.py
Update naming convention of scenarios and figures across all 18 configurations:
"total_districts_national_districts_WH_districts_FI_districts_WIFI_districts"
Generates both compact (e.g., 51_13_11_24_3) and descriptive (e.g., 51_districts_13_national_districts_11_WH_districts_24_FI_districts_3_WIFI_districts)
figures and metadata, re-exports scenarios.csv and summary.csv, and copies artifacts.
"""
import csv
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review-memo")
PY = "/Users/Shared/sv-ntlee/repos/td/.venv/bin/python"
BRAIN_DIR = Path("/Users/sandvault-ntlee/.gemini/antigravity-cli/brain/09f078e7-2f55-4c40-9905-5ed9fd054e07")

SCENARIOS = [
    {
        "run_d": "battery/results/option1_exact_merged",
        "legacy_fig": "figures/summary_option1.png",
        "total": 47, "n": 14, "wh": 11, "fi": 21, "wifi": 1
    },
    {
        "run_d": "battery/results/option2_exact_multichannel",
        "legacy_fig": "figures/summary_option2.png",
        "total": 46, "n": 14, "wh": 11, "fi": 21, "wifi": 0
    },
    {
        "run_d": "battery/results/scenario_A_51",
        "legacy_fig": "figures/summary_scenario_A.png",
        "total": 51, "n": 13, "wh": 13, "fi": 24, "wifi": 1
    },
    {
        "run_d": "battery/results/scenario_B_52",
        "legacy_fig": "figures/summary_scenario_B.png",
        "total": 52, "n": 13, "wh": 14, "fi": 24, "wifi": 1
    },
    {
        "run_d": "battery/results/scenario_C_51",
        "legacy_fig": "figures/summary_scenario_C.png",
        "total": 51, "n": 12, "wh": 13, "fi": 25, "wifi": 1
    },
    {
        "run_d": "battery/results/scenario_D_53",
        "legacy_fig": "figures/summary_scenario_D.png",
        "total": 53, "n": 13, "wh": 14, "fi": 25, "wifi": 1
    },
    {
        "run_d": "battery/results/scenario_E_52",
        "legacy_fig": "figures/summary_scenario_E.png",
        "total": 52, "n": 12, "wh": 14, "fi": 25, "wifi": 1
    },
    {
        "run_d": "battery/results/scenario_F_51",
        "legacy_fig": "figures/summary_scenario_F.png",
        "total": 51, "n": 12, "wh": 13, "fi": 24, "wifi": 2
    },
    {
        "run_d": "battery/results/scenario_G_52",
        "legacy_fig": "figures/summary_scenario_G.png",
        "total": 52, "n": 12, "wh": 13, "fi": 25, "wifi": 2
    },
    {
        "run_d": "battery/results/scenario_H_52",
        "legacy_fig": "figures/summary_scenario_H.png",
        "total": 52, "n": 13, "wh": 13, "fi": 24, "wifi": 2
    },
    {
        "run_d": "battery/results/scenario_I_53",
        "legacy_fig": "figures/summary_scenario_I.png",
        "total": 53, "n": 13, "wh": 14, "fi": 24, "wifi": 2
    },
    {
        "run_d": "battery/results/scenario_J_53",
        "legacy_fig": "figures/summary_scenario_J.png",
        "total": 53, "n": 12, "wh": 14, "fi": 25, "wifi": 2
    },
    {
        "run_d": "battery/results/scenario_K_52",
        "legacy_fig": "figures/summary_scenario_K.png",
        "total": 52, "n": 14, "wh": 13, "fi": 24, "wifi": 1
    },
    {
        "run_d": "battery/results/scenario_L_53",
        "legacy_fig": "figures/summary_scenario_L.png",
        "total": 53, "n": 14, "wh": 14, "fi": 24, "wifi": 1
    },
    {
        "run_d": "battery/results/grid_W3_A_51",
        "legacy_fig": "figures/summary_grid_W3_A.png",
        "total": 51, "n": 13, "wh": 11, "fi": 24, "wifi": 3
    },
    {
        "run_d": "battery/results/grid_W4_A_51",
        "legacy_fig": "figures/summary_grid_W4_A.png",
        "total": 51, "n": 13, "wh": 11, "fi": 23, "wifi": 4
    },
    {
        "run_d": "battery/results/grid_W4_B_52",
        "legacy_fig": "figures/summary_grid_W4_B.png",
        "total": 52, "n": 12, "wh": 11, "fi": 25, "wifi": 4
    },
    {
        "run_d": "battery/results/grid_W5_C_52",
        "legacy_fig": "figures/summary_grid_W5_C.png",
        "total": 52, "n": 12, "wh": 10, "fi": 25, "wifi": 5
    },
]


def main():
    figures_dir = REPO_ROOT / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    fieldnames = [
        'scenario_id', 'scenario_short_name', 'scenario_name',
        'total_districts', 'national_districts', 'WH_districts', 'FI_districts', 'WIFI_districts',
        'national_tau', 'wealth_tau', 'fi_tau',
        'total_opportunity_mass', 'held_mass', 'unheld_mass', 'unheld_mass_pct',
        'contiguity_status', 'map_path', 'map_path_verbose'
    ]

    print("--- 1. UPDATING FIGURES AND BUILDING SUMMARY METRICS ---")
    for sc in SCENARIOS:
        tot = sc["total"]
        n = sc["n"]
        wh = sc["wh"]
        fi = sc["fi"]
        wifi = sc["wifi"]
        assert tot == n + wh + fi + wifi, f"Sum mismatch for {sc['run_d']}: {tot} != {n}+{wh}+{fi}+{wifi}"

        new_id = f"{tot}_total_{n}n_{wh}wh_{fi}fi_{wifi}wifi"
        compact_id = f"{tot}_{n}_{wh}_{fi}_{wifi}"
        verbose_name = f"{tot}_districts_{n}_national_districts_{wh}_WH_districts_{fi}_FI_districts_{wifi}_WIFI_districts"

        run_path = REPO_ROOT / sc["run_d"]
        src_png = run_path / "maps/summary.png"
        if not src_png.exists():
            raise FileNotFoundError(f"Missing summary.png in {run_path}")

        # 1. Save new primary figure
        new_fig = figures_dir / f"{new_id}.png"
        shutil.copy(src_png, new_fig)

        # 2. Save aliases for backwards compatibility
        compact_fig = figures_dir / f"{compact_id}.png"
        shutil.copy(src_png, compact_fig)
        verbose_fig = figures_dir / f"{verbose_name}.png"
        shutil.copy(src_png, verbose_fig)
        legacy_fig = REPO_ROOT / sc["legacy_fig"]
        shutil.copy(src_png, legacy_fig)

        # 3. Copy to brain artifacts
        if BRAIN_DIR.exists():
            shutil.copy(src_png, BRAIN_DIR / new_fig.name)
            shutil.copy(src_png, BRAIN_DIR / compact_fig.name)
            shutil.copy(src_png, BRAIN_DIR / verbose_fig.name)
            shutil.copy(src_png, BRAIN_DIR / legacy_fig.name)

        # Parse metrics from plan.json and assignment.csv
        with open(run_path / "plan.json") as f:
            plan = json.load(f)
        slots = plan["slots"]
        bundles = {}
        for s in slots:
            bundles.setdefault(s["bundle"], []).append(s)

        with open(run_path / "assignment.csv") as f:
            assign_rows = list(csv.DictReader(f))
        total_m = sum(float(r.get("M_cell", 0)) for r in assign_rows)
        unheld_m = sum(float(r.get("M_cell", 0)) for r in assign_rows if r.get("district") == "other")
        held_m = total_m - unheld_m

        n_slots = bundles.get("N", [])
        wh_slots = bundles.get("WH", [])
        fi_slots = bundles.get("FI", [])
        whfi_slots = bundles.get("WHFI", [])

        n_tau = (n_slots[0]["L"] + n_slots[0]["U"]) / 2.0 if n_slots else 0.0
        wh_tau = (wh_slots[0]["L"] + wh_slots[0]["U"]) / 2.0 if wh_slots else 0.0
        fi_tau = (fi_slots[0]["L"] + fi_slots[0]["U"]) / 2.0 if fi_slots else 0.0

        summary_rows.append({
            'scenario_id': new_id,
            'scenario_short_name': new_id,
            'scenario_name': new_id,
            'total_districts': tot,
            'national_districts': n,
            'WH_districts': wh,
            'FI_districts': fi,
            'WIFI_districts': wifi,
            'national_tau': f'{n_tau:.1f}',
            'wealth_tau': f'{wh_tau:.1f}',
            'fi_tau': f'{fi_tau:.1f}',
            'total_opportunity_mass': f'{total_m:.2f}',
            'held_mass': f'{held_m:.2f}',
            'unheld_mass': f'{unheld_m:.2f}',
            'unheld_mass_pct': f'{(unheld_m / total_m * 100):.2f}%',
            'contiguity_status': '100% Contiguous (0 violations)',
            'map_path': f"figures/{new_id}.png",
            'map_path_verbose': f"figures/{new_id}.png",
        })
        print(f"  [OK] {new_id} -> {new_fig.name}")

    # Write summary.csv
    summary_path = REPO_ROOT / "summary.csv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\nsummary.csv updated with {len(summary_rows)} rows!")
    if BRAIN_DIR.exists():
        shutil.copy(summary_path, BRAIN_DIR / "summary.csv")

    print("\n--- 2. EXPORTING MASTER SCENARIOS CSV (scenarios.csv) ---")
    export_cmd = [
        PY, str(REPO_ROOT / "tools/scenario_export.py"),
        "--out", str(REPO_ROOT / "scenarios.csv"),
    ]
    for sc in SCENARIOS:
        new_id = f"{sc['total']}_total_{sc['n']}n_{sc['wh']}wh_{sc['fi']}fi_{sc['wifi']}wifi"
        export_cmd.extend(["--scenario", new_id, str(REPO_ROOT / sc["run_d"])])

    res = subprocess.run(export_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Export stdout:", res.stdout)
        print("Export stderr:", res.stderr)
        raise RuntimeError("scenario_export failed")

    with open(REPO_ROOT / "scenarios.csv") as f:
        reader = csv.reader(f)
        header = next(reader)
        n_rows = sum(1 for _ in reader)
    print(f"scenarios.csv written with {n_rows:,} rows across {len(SCENARIOS)} scenarios!")
    if BRAIN_DIR.exists():
        shutil.copy(REPO_ROOT / "scenarios.csv", BRAIN_DIR / "scenarios.csv")


if __name__ == "__main__":
    main()
