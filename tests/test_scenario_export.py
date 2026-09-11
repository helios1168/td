"""test_scenario_export.py: tools/scenario_export.py on a hand-built `assignment.csv`.

Three zips.  10000's national sits in a pure N district and its WH and FI in an all-channel
one; 10001 is wholly in that all-channel district; 10002's national is held by no district
(`other`) while its WH and FI are in a WH_PLUS and an FI_PLUS district.  What is pinned: the
five source rows per zip, the two national source rows sharing the `N_FI` cell's district and
rep, the drawn id and mix of a WHFI_PLUS district, empty mix and rep on `other`, the rep map
swap and its refusal of an unmapped id, and two scenarios stacking in one file.
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (HERE, os.path.join(ROOT, "tools"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import scenario_export as cli                        # noqa: E402

CELLS = [  # zip, state, channel, file_channel, district, bundle, wholesaler
    ("10000", "A", "N_WH", "national", "N_01", "N", "R0000"),
    ("10000", "A", "N_FI", "national", "N_01", "N", "R0000"),
    ("10000", "A", "WH", "wh", "WHFI_PLUS_02", "WHFI_PLUS", "R0005"),
    ("10000", "A", "FI", "fi", "WHFI_PLUS_02", "WHFI_PLUS", "R0005"),
    ("10001", "B", "N_WH", "national", "WHFI_PLUS_02", "WHFI_PLUS", "R0005"),
    ("10001", "B", "N_FI", "national", "WHFI_PLUS_02", "WHFI_PLUS", "R0005"),
    ("10001", "B", "WH", "wh", "WHFI_PLUS_02", "WHFI_PLUS", "R0005"),
    ("10001", "B", "FI", "fi", "WHFI_PLUS_02", "WHFI_PLUS", "R0005"),
    ("10002", "B", "N_WH", "national", "other", "", ""),
    ("10002", "B", "N_FI", "national", "other", "", ""),
    ("10002", "B", "WH", "wh", "WH_PLUS_01", "WH_PLUS", "R0003"),
    ("10002", "B", "FI", "fi", "FI_PLUS_01", "FI_PLUS", "R0004"),
]


def _run_dir(tmp: str, name: str, rows=CELLS) -> str:
    d = os.path.join(tmp, name)
    os.makedirs(d)
    with open(os.path.join(d, "assignment.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cli.ASSIGNMENT_COLUMNS)
        for row in rows:
            w.writerow([*row, 1.0])
    return d


def _rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_five_source_rows_per_zip_with_the_drawn_district_and_mix():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "scenarios.csv")
        assert cli.main(["--out", out, "--scenario", "S", _run_dir(tmp, "run")]) == 0
        rows = _rows(out)
    assert [r["scenario"] for r in rows] == ["S"] * 15
    assert list(rows[0]) == list(cli.COLUMNS)
    by_zip = {}
    for r in rows:
        by_zip.setdefault(r["zip_code"], []).append(r["current_channel"])
    assert by_zip == {z: list(cli.CHANNEL_ORDER) for z in ("10000", "10001", "10002")}
    # the N_FI cell's two source rows carry one district and one rep
    nat = {r["current_channel"]: r for r in rows if r["zip_code"] == "10000"}
    assert nat["National (Chase)"]["model_channel"] == nat["Wells FI"]["model_channel"] == "N_FI"
    assert nat["National (Chase)"]["district"] == nat["Wells FI"]["district"] == "N_01"
    assert nat["National (Chase)"]["rep"] == nat["Wells FI"]["rep"] == "R0000"
    assert nat["Wells WH"]["model_channel"] == "N_WH" and nat["Wells WH"]["district"] == "N_01"
    assert nat["National (Chase)"]["district_channels"] == "N"
    # the all-channel district is written as drawn
    assert nat["WH"]["district"] == "WIFI_02" and nat["WH"]["district_channels"] == "WIFI"
    assert nat["WH"]["state"] == "A"
    # `other` keeps its name and has no mix and no rep
    other = [r for r in rows if r["zip_code"] == "10002" and r["model_channel"] == "N_FI"]
    assert len(other) == 2
    assert all(r["district"] == "other" and r["district_channels"] == "" and r["rep"] == ""
               for r in other)
    plus = {r["current_channel"]: r for r in rows if r["zip_code"] == "10002"}
    assert plus["WH"]["district_channels"] == "WH+" and plus["FI"]["district_channels"] == "FI+"


def test_rep_map_swaps_ids_and_refuses_an_unmapped_one():
    with tempfile.TemporaryDirectory() as tmp:
        run = _run_dir(tmp, "run")
        rep_map = os.path.join(tmp, "rep_map.csv")
        with open(rep_map, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rep_surrogate", "rep_id", "firm_surrogate", "firm"])
            w.writerows([["R0000", "alice", "F0", "Acme"], ["R0003", "bob", "F1", "Bolt"],
                         ["R0004", "cy", "F1", "Bolt"], ["R0005", "dee", "F0", "Acme"]])
        out = os.path.join(tmp, "scenarios.csv")
        assert cli.main(["--out", out, "--rep-map", rep_map, "--scenario", "S", run]) == 0
        reps = {r["rep"] for r in _rows(out)}
        assert reps == {"alice", "bob", "cy", "dee", ""}

        with open(rep_map, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rep_surrogate", "rep_id"])
            w.writerow(["R0000", "alice"])
        out2 = os.path.join(tmp, "scenarios2.csv")
        assert cli.main(["--out", out2, "--rep-map", rep_map, "--scenario", "S", run]) == 1
        assert not os.path.exists(out2)


def test_two_scenarios_stack_in_name_order_and_names_must_differ():
    with tempfile.TemporaryDirectory() as tmp:
        a = _run_dir(tmp, "a")
        b = _run_dir(tmp, "b", rows=[row[:4] + ("N_02", "N", "R0007") for row in CELLS])
        out = os.path.join(tmp, "scenarios.csv")
        assert cli.main(["--out", out, "--scenario", "Z second", b,
                         "--scenario", "A first", a]) == 0
        rows = _rows(out)
        assert len(rows) == 30
        assert [r["scenario"] for r in rows] == ["A first"] * 15 + ["Z second"] * 15
        assert {r["district"] for r in rows if r["scenario"] == "Z second"} == {"N_02"}
        assert cli.main(["--out", out, "--scenario", "S", a, "--scenario", "S", b]) == 1


def test_an_assignment_with_other_columns_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "run")
        os.makedirs(d)
        with open(os.path.join(d, "assignment.csv"), "w", encoding="utf-8", newline="") as fh:
            fh.write("zip,state,channel,district\n10000,A,WH,WH_01\n")
        out = os.path.join(tmp, "scenarios.csv")
        assert cli.main(["--out", out, "--scenario", "S", d]) == 1
        assert not os.path.exists(out)
