"""Assemble the "Borders in Motion" page: the template beside this file plus steps.json.

    .venv/bin/python3 tools/motion_page/steps_data.py     # writes battery/results/motion_page/steps.json
    .venv/bin/python3 tools/motion_page/build_steps.py    # writes battery/results/motion_page/borders_in_motion.html
    node tools/motion_page/dom_stub_run.js battery/results/motion_page/borders_in_motion.html
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
# battery/results is gitignored and hub-only (CLAUDE.md); a worktree carries none, so
# TD_DATA_ROOT points a run there at the hub's copy.
DATA_ROOT = Path(os.environ.get("TD_DATA_ROOT", REPO))
DATA = DATA_ROOT / "battery" / "results" / "motion_page"
html = (HERE / "steps_template.html").read_text().replace("__DATA__", (DATA / "steps.json").read_text())
out = DATA / "borders_in_motion.html"
out.write_text(html)
print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
