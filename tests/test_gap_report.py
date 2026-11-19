"""tools/maps/gap_report.py (issue #148): hand-made CSVs in a tempdir with hand-worked numbers: the scenario max-min, the top pair
order, a failing TIE check flagged, dollars printed as $B, the load bands."""
import contextlib
import importlib.util
import io
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gap_report", ROOT / "tools" / "maps" / "gap_report.py")
gr = importlib.util.module_from_spec(_spec)
sys.modules["gap_report"] = gr
_spec.loader.exec_module(gr)

SUM = "SECTION,SCENARIO,EST_SOURCE,CHANNEL,ITEM,N_ZIPS,MM_OPP,PCT,MUST_BE_ZERO\n"
PAIR = "SCENARIO,EST_SOURCE,CHANNEL,HOLDER_A,HOLDER_B,N_ZIPS,MM_OPP\n"
LOAD = "SCENARIO,EST_SOURCE,HOLDER,ROLE,CHANNEL,AREA_KM2,ASSIGNED_USD,BASE_USD,MEDIAN_AREA_KM2,EXPECTED_USD,LOAD_RATIO\n"


def run(files):
    """files {name: text} -> the report text."""
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for n, t in files.items():
            p = os.path.join(d, n)
            with open(p, "w", encoding="utf-8-sig") as f:      # the BOM the owner's tools may add
                f.write(t)
            paths.append(p)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            gr.main(paths)
    return buf.getvalue()


def test_scenario_max_min_and_dollars_as_billions():
    out = run({"A_gap_summary.csv": SUM + "CLASS,A,CRBG,NATIONAL,GAP,10,3000000000,3.0,0\nCLASS,A,CRBG,NATIONAL,OVERLAP,2,500000000,0.5,0\n",
               "B_gap_summary.csv": SUM + "CLASS,B,CRBG,NATIONAL,GAP,8,1250000000,1.25,0\n"})
    assert "| NATIONAL | GAP | $3.00B (3.0%) | $1.25B (1.2%) | $1.75B |" in out, out     # 3.00 - 1.25
    assert "| NATIONAL | OVERLAP | $0.50B (0.5%) | - | $0.50B |" in out, out
    assert "3000000000" not in out


def test_a_shared_row_counts_for_every_scenario():
    out = run({"gap_summary.csv": SUM + "CLASS,A B C,CRBG,NATIONAL,GAP,10,3000000000,3.0,0\nCLASS,B,CRBG,NATIONAL,OVERLAP,2,500000000,0.5,0\n"
                                    "CLASS,A C,CRBG,NATIONAL,OVERLAP,1,250000000,0.2,0\n"})
    gap = next(l for l in out.splitlines() if l.startswith("| NATIONAL | GAP |"))
    over = next(l for l in out.splitlines() if l.startswith("| NATIONAL | OVERLAP |"))
    assert gap.count("$3.00B") == 3 and gap.endswith("$0.00B |"), gap        # shared by A, B and C
    assert over == "| NATIONAL | OVERLAP | $0.25B (0.2%) | $0.50B (0.5%) | $0.25B (0.2%) | $0.25B |", over   # A, B, C, max-min


def test_gaps_by_state_split_held_today_and_unheld():
    rows = ("STATE,A,CRBG,REGIONAL,CA | GAP (HELD TODAY),5,2000000000,1.9,0\nSTATE,A,CRBG,REGIONAL,CA | GAP (UNHELD),3,1000000000,0.9,0\n"
            "STATE,A,CRBG,REGIONAL,NY | GAP (UNHELD),4,2500000000,2.3,0\nSTATE,A,CRBG,REGIONAL,NY | COVERED,9,9000000000,8.0,0\n")
    out = run({"gap_summary.csv": SUM + rows})
    i = out.index("Top 15 states by GAP, REGIONAL")
    got = [l for l in out[i:].splitlines() if l.startswith("| CA ") or l.startswith("| NY ")][:2]
    assert got == ["| CA | 8 | $3.00B | $2.00B | $1.00B |", "| NY | 4 | $2.50B | $0.00B | $2.50B |"], got   # by total gap; COVERED not a gap


def test_top_pair_order():
    rows = "".join(f"A,CRBG,NATIONAL,R{a},R{b_},1,{v}\n" for a, b_, v in ((1, 2, 1e9), (3, 4, 5e9), (5, 6, 2e9)))
    out = run({"A_gap_pair.csv": PAIR + rows})
    assert out.index("R3 | R4") < out.index("R5 | R6") < out.index("R1 | R2"), out
    assert "not additive" in out


def test_failing_tie_check_flagged_and_passing_not():
    ok = SUM + "TIE,A,CRBG,NATIONAL,cells differ,0,0.4,,1\nTIE,A,CRBG,NATIONAL,info,5,9,,0\n"
    assert "CHECK FAILED" not in run({"A_gap_summary.csv": ok})                   # 0.4 dollars is under the 1 dollar tolerance
    out = run({"A_gap_summary.csv": ok + "TIE,A,CRBG,NATIONAL,rows differ,0,-2.5,,1\nTIE,A,CRBG,NATIONAL,zips differ,1,0,,1\n"})
    assert out.count("**CHECK FAILED") == 2 and "rows differ" in out and "zips differ" in out, out
    assert "cells differ" not in out


def test_load_bands():
    rows = "".join(f"A,CRBG,R{i},NATIONAL,NATIONAL,100,2000000000,0,50,1000000000,{r}\n" for i, r in enumerate(("1.30", "1.25", "0.79", "0.80", "1.00", "")))
    out = run({"A_gap_load.csv": LOAD + rows})
    assert "2 above 1.25" not in out and "1 above 1.25, 1 below 0.8 (of 5)" in out, out    # 1.25 and 0.80 are inside; empty ratio dropped
    assert out.index("R0 |") < out.index("R4 |")                                  # highest first
    assert "$2.00B | $1.00B | 1.30" in out, out
