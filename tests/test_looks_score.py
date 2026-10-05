"""tools/looks/score.py (td#93) on toy channels with hand-computed values."""
from __future__ import annotations

import csv
import importlib.util
import math
import os
import tempfile

from td import audit, data

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "looks_score", os.path.join(HERE, "..", "tools", "looks", "score.py"))
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)


def _geo():
    """States A (a1, a2, a3) and B (b1, b2, b3) on a line at x = 0, 1, 2, 3, 4, 10 km.  Borders:
    a1-a2 30, a2-a3 30, a3-b1 8, b1-b2 30 km, and b3 touches only a1 (5 km), across the state line.
    The M1 polygon graph has the same edges."""
    state = {"a1": "A", "a2": "A", "a3": "A", "b1": "B", "b2": "B", "b3": "B"}
    xy = {z: (x, 0.0) for z, x in zip(state, (0.0, 1.0, 2.0, 3.0, 4.0, 10.0))}
    edge = {z: {} for z in state}
    for a, b, km in (("a1", "a2", 30.0), ("a2", "a3", 30.0), ("a3", "b1", 8.0),
                     ("b1", "b2", 30.0), ("a1", "b3", 5.0)):
        edge[a][b] = edge[b][a] = km
    polygon = {"vertices": sorted(state), "edges": [(a, b) for a in edge for b in edge[a] if a < b],
               "state": state}
    return score.Geography(state, xy, edge, polygon)


def _rows(ch: str, cells) -> list:
    return [{"zip_code": z, "current_channel": ch.lower(), "state": z[0].upper(),
             "model_channel": ch, "district": j, "m_rel": str(m)} for z, j, m in cells]


# X_01 holds a1 (1.0); X_02 holds a2 (0.15), b1 (0.6) and b3 (0.25).  a3 and b2 have no cell in X.
X_CELLS = (("a1", "X_01", 1.0), ("a2", "X_02", 0.15), ("b1", "X_02", 0.6), ("b3", "X_02", 0.25))


def _districts(ch: str, masses) -> list:
    return [{"channel": ch, "district": f"{ch}_{i:02d}", "drawn_mass": str(m)}
            for i, m in enumerate(masses, 1)]


def test_display_fill_and_looks():
    g = _geo()
    led = _rows("X", X_CELLS)
    own = {"a1": "X_01", "a2": "X_02", "b1": "X_02", "b3": "X_02"}
    # a3 joins X_02 from a2, b2 joins X_02 from b1; b3 does not spread into A
    assert score.display_fill(own, g) == {**own, "a3": "X_02", "b2": "X_02"}
    c = score.channel_looks("X", led, _districts("X", (1.0, 1.0)), g)
    assert c["k"] == 2 and c["tau"] == 1.0 and c["deviation"] == {"X_01": 0.0, "X_02": 0.0}
    assert c["split"] == ["A"]
    assert c["small"] == [("X_02", "A", 0.15)]          # under 0.20 τ
    assert c["crowded"] == []                           # 2 districts, ceil(1.15) + 1 = 3
    # X_02's A piece {a2, a3} meets its B piece {b1, b2, b3} over a3-b1 only: 8 km, both ways
    assert c["thin"] == [("X_02", "A", 8.0), ("X_02", "B", 8.0)]
    assert c["pieces"] == [("X_02", 1, 0.25, "B")]      # b3 is cut off from X_02's other ZIPs
    assert c["max_states"] == 2
    assert math.isclose(c["extent_km"], 9.0)            # a2 to b3, the ledger's ZIPs only


def test_crowded_and_balance():
    # No edges: every two-state district is a thin link at 0 km and in two pieces.
    state = {z: z[0].upper() for z in ("c1", "c2", "c3", "d1", "d2", "d3")}
    g = score.Geography(state, {}, {}, {"vertices": sorted(state), "edges": [], "state": state})
    led = _rows("Y", (("c1", "Y_01", 0.25), ("d1", "Y_01", 0.75), ("c2", "Y_02", 0.25),
                      ("d2", "Y_02", 1.0), ("c3", "Y_03", 0.125), ("d3", "Y_03", 0.625)))
    c = score.channel_looks("Y", led, _districts("Y", (1.0, 1.25, 0.75)), g)
    assert c["deviation"] == {"Y_01": 0.0, "Y_02": 0.25, "Y_03": -0.25}
    assert c["split"] == ["C", "D"]
    assert c["crowded"] == ["C"]                        # 3 districts > ceil(0.625) + 1 = 2
    assert c["small"] == [("Y_03", "C", 0.125)]
    assert len(c["thin"]) == 6 and c["pieces"] == [("Y_01", 1, 0.25, "C"), ("Y_02", 1, 0.25, "C"),
                                                   ("Y_03", 1, 0.125, "C")]


def test_dollars():
    e = data.Extract(("wh", "fi", "career"), ["z1", "z2", "z3", "z4"], ["wh", "wh", "fi", "career"],
                     [1.0, 3.0, 2.0, 5.0], [0.0] * 4, [0.0] * 4)
    rates = score.dollar_rates(e)
    assert set(rates) == {"wh", "fi"}
    assert math.isclose(rates["wh"], 11.36e9 / 4.0) and math.isclose(rates["fi"], 20.69e9 / 2.0)
    led = [{"model_channel": "M", "district": "M_01", "current_channel": "wh", "m_rel": "1"},
           {"model_channel": "M", "district": "M_02", "current_channel": "fi", "m_rel": "1"},
           {"model_channel": "M", "district": "", "current_channel": "fi", "m_rel": "7"}]
    assert math.isclose(score.dollars_per_district("M", 2, led, rates),
                        (rates["wh"] + rates["fi"]) / 2)
    try:
        score.dollars_per_district("M", 2, led, {"wh": 1.0})
    except ValueError as err:
        assert "fi" in str(err)
    else:
        raise AssertionError("a fine channel without a dollar total must stop")


SCORECARD = """# Scorecard: toy

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 4 cells, 0 with other than one owner |
| final bands on drawn mass | fail | 2 districts, 1 outside the final tolerance |
| planned against drawn owners | listed | 1 listed |
| ZIP contiguity | listed | 1 districts in pieces, 3 pieces, 0 ZIPs not in the graph |
"""


def test_scorecard_parse():
    assert score.scorecard_checks(SCORECARD) == {
        "one owner per cell": "pass", "final bands on drawn mass": "fail",
        "planned against drawn owners": "listed", "ZIP contiguity": "listed"}
    assert score.audit_pieces(SCORECARD) == 3
    assert score.audit_pieces("") is None


M1_PASS = audit.Check(audit.M1_CHECK, "pass", "0 districts in pieces")


def test_eligibility_rules():
    led = _rows("X", X_CELLS)
    ok = score.bands_at(led, {"X": 2}, 0.15)
    assert ok.status == "pass"
    assert score.bands_at(_rows("X", (("a1", "X_01", 1.2), ("b1", "X_02", 0.8))),
                          {"X": 2}, 0.15).status == "fail"           # 1.2 > 1.15
    checks = score.scorecard_checks(SCORECARD)       # its ±10% band fail is replaced by ±15%
    main = {"national": 15, "WH": 12, "FI": 20, "NE": 3}
    good = {"national": 1.25e9, "WH": 1.09e9, "FI": 0.82e9, "NE": 2.0e9}   # NE: no target
    assert score.eligibility(checks, ok, main, good, M1_PASS) == []
    bad = score.eligibility({**checks, "phantom shares": "fail"}, ok, {**main, "NE": 10},
                            {**good, "WH": 0.845e9}, M1_PASS)
    assert bad == ["audit: phantom shares fails", "$ WH 845M is -15.5% of 1,000M",
                   "main K 57 outside 48-54"]
    assert score.eligibility(checks, ok, {"IFA": 49}, {"IFA": 1.227e9}, M1_PASS) == []   # no main K rule
    assert score.eligibility({}, audit.Check("b", "fail", "1 outside"), {"IFA": 49},
                             {"IFA": 1.227e9}, M1_PASS) == ["audit: no scorecard", "audit at ±15%: 1 outside"]
    # M1 (#108): a failing or missing M1 check makes the run ineligible, whatever else holds
    m1 = audit.Check(audit.M1_CHECK, "fail", "1 districts in pieces")
    assert score.eligibility(checks, ok, main, good, m1) == ["M1: fail, 1 districts in pieces"]
    assert score.eligibility({**checks, audit.M1_CHECK: "fail"}, ok, main, good, m1) == [
        "M1: fail, 1 districts in pieces"]
    assert score.eligibility(checks, ok, main, good) == ["M1: not checked"]
    unverified = audit.Check(audit.M1_CHECK, "unverified", "no polygon graph: M1 is not checked")
    assert score.eligibility(checks, ok, main, good, unverified) == [
        "M1: unverified, no polygon graph: M1 is not checked"]


def test_dollar_band_inclusive():
    ok = audit.Check(score.BAND_CHECK, "pass", "")
    for ch, t in (("national", 1.25e9), ("WH", 1.0e9), ("FI", 0.9e9)):
        for d in (t * 1.1, t * 0.9):                     # exactly ±10%: eligible
            assert score.eligibility({}, ok, {"IFA": 1}, {ch: d}, M1_PASS) == ["audit: no scorecard"], (ch, d)
        for d in (t * 1.1 + 1, t * 0.9 - 1):             # a dollar past either edge: not
            why = score.eligibility({}, ok, {"IFA": 1}, {ch: d}, M1_PASS)
            assert len(why) == 2 and why[1].startswith(f"$ {ch} "), (ch, d, why)


def _score_toy(ch: str, rates: dict) -> dict:
    """`score.score` on a run folder holding channel `ch` laid out as X."""
    with tempfile.TemporaryDirectory() as d:
        led = _rows(ch, ((z, j.replace("X", ch), m) for z, j, m in X_CELLS))
        with open(os.path.join(d, "ledger.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, list(led[0]))
            w.writeheader()
            w.writerows(led)
        with open(os.path.join(d, "districts.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, ["channel", "district", "drawn_mass"])
            w.writeheader()
            w.writerows(_districts(ch, (1.0, 1.0)))
        with open(os.path.join(d, "scorecard.md"), "w") as fh:
            fh.write(SCORECARD)
        return score.score(d, _geo(), rates)


def test_score_run_folder():
    s = _score_toy("WH", {"wh": 1.0e9})
    assert s["dollars"] == {"WH": 1.0e9}                # Σ m_rel × rate / K = 2 × 1e9 / 2
    # M1 on the ledger, strict: WH_02's a2 and b3 are cut off from b1, and a3, b2 have no owner
    m1 = "M1: fail, 1 districts in pieces, 2 detached pieces (largest 0.25 τ), 2 channel ZCTAs with no owner"
    assert not s["eligible"] and s["why"] == [m1, "main K 2 outside 48-54"]
    assert s["m1"]["status"] == "fail" and s["m1"]["no_owner"] == 2 and s["m1"]["pieces"] == 2
    assert (s["splits"], s["split_list"], s["distinct"]) == (1, ["WH:A"], ["A"])
    # after the display fill only b3 (0.25 τ) is detached, weighing 1 + 0.25 (owner, 2026-10-05)
    assert (s["thin_links"], s["small_pieces"], s["crowded_states"], s["contiguity_pieces"]) == (2, 1, 0, 1)
    assert s["contiguity_weight"] == 1.25 and s["largest_piece_tau"] == 0.25
    assert s["defects"] == 4.25 and s["audit_pieces"] == 3
    assert math.isclose(s["largest_extent_km"], 9.0) and s["states_per_district"] == 2
    assert s["worst_dev"] == 0.0 and s["mean_dev"] == 0.0
    assert f"INELIGIBLE ({m1}; main K 2 outside 48-54) | 1 splits (1 states) | 4.25 defects" in score.verdict(s)
    assert "largest detached piece WH_02: 1 ZIPs in B, 0.250 tau (after display fill)" in score.report(s)
    # An IFA-only run: no main K rule, and $ is the owner's whole-extract IFA total over K.
    ifa = _score_toy("IFA", {})
    assert ifa["dollars"] == {"IFA": 62.14e9 / 2}
    assert ifa["why"] == [m1, "$ IFA 31,070M is +2385.6% of 1,250M"]


def _s(run, splits, defects, eligible=True, extent=100.0, worst=0.05):
    return {"run": run, "eligible": eligible, "splits": splits, "defects": defects,
            "largest_extent_km": extent, "states_per_district": 3, "worst_dev": worst,
            "mean_dev": 0.01, "review": None}


def test_rank_and_review():
    runs = [_s("best_a", 10, 6), _s("best_b", 10, 4, extent=50.0), _s("plus1_fewer", 11, 2),
            _s("plus1_same", 11, 4), _s("plus2", 12, 0), _s("off", 5, 0, eligible=False)]
    out = score.rank(runs)
    assert [s["run"] for s in out] == ["best_b", "best_a", "plus1_fewer", "plus1_same", "plus2", "off"]
    flags = {s["run"]: s["review"] for s in out}
    # one split more and strictly fewer defects than every run at 10 splits (min 4): flagged
    assert flags == {"best_a": None, "best_b": None, "plus1_fewer": "REVIEW: +1 split for -2 defects",
                     "plus1_same": None, "plus2": None, "off": None}
    # a repeated call recomputes the flag from the runs it is given
    a, b, stale = _s("a", 10, 4), _s("b", 11, 2), _s("stale", 9, 0, eligible=False)
    assert score.rank([a, b])[1]["review"] == "REVIEW: +1 split for -2 defects"
    stale["review"] = "REVIEW: +1 split for -9 defects"
    out = score.rank([b, stale])
    assert [s["run"] for s in out] == ["b", "stale"] and b["review"] is None and stale["review"] is None
    ties = score.rank([_s("x", 3, 1, worst=0.09), _s("y", 3, 1, worst=0.08)])
    assert [s["run"] for s in ties] == ["y", "x"]
