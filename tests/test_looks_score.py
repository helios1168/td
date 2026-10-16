"""tools/looks/score.py (td#93) on toy channels with hand-computed values."""
from __future__ import annotations

import csv
import importlib.util
import json
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
               "state": state, "border": {(a, b): 1000.0 * km for a in edge for b, km in edge[a].items()
                                          if a < b},
               "connectors": [], "aland": dict.fromkeys(state, 1e8)}
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
    # pieces are on the ledger, not the fill (#116): b3 and a2 are cut off from b1
    assert c["pieces"] == [("X_02", 1, 0.25, "B"), ("X_02", 1, 0.15, "A")]
    assert c["max_states"] == 2
    assert math.isclose(c["extent_km"], 9.0)            # a2 to b3, the ledger's ZIPs only


def test_a_zero_opportunity_zcta_held_across_a_state_line_splits_that_state():
    """Council decision 1 (owner, 2026-10-05): a district owning any ZCTA of a state, a zero-
    opportunity one included, splits it.  X_01 holds b2 at zero mass, so B, X_02's, is split; a
    run whose ledger owns every ZCTA (#116) has nothing for the display fill to add."""
    g = _geo()
    cells = (("a1", "X_01", 1.0), ("a2", "X_01", 0.0), ("a3", "X_01", 0.0), ("b1", "X_02", 0.6),
             ("b2", "X_01", 0.0), ("b3", "X_02", 0.4))
    led = _rows("X", cells)
    c = score.channel_looks("X", led, _districts("X", (1.0, 1.0)), g)
    assert c["split"] == ["B"] and c["small"] == [("X_01", "B", 0.0)]
    own = {z: j for z, j, _ in cells}
    assert score.display_fill(own, g) == own
    without = score.channel_looks("X", _rows("X", [r for r in cells if r[0] != "b2"]),
                                  _districts("X", (1.0, 1.0)), g)
    assert without["split"] == []
    # states_per_district counts owned ZCTAs too (council decision 1): X_01 holds A and B's b2
    assert (c["max_states"], without["max_states"]) == (2, 1)


def test_a_piece_only_a_multipart_zcta_makes_is_listed_and_not_an_m1_piece():
    """Owner, 2026-10-05 (#108): m is one vertex with two parts; X_01 holds m and n, n touching
    m's part 0 only, so m's part 1 is a separate drawn piece, listed as a visual defect, while
    the district is one M1 piece."""
    state = dict.fromkeys(("m", "n"), "A")
    polygon = {"vertices": ["m", "n"], "edges": [("m", "n")], "state": state}
    parts = {"area": {"m": [4e6, 1e6], "n": [2e6]}, "edges": [("m", 0, "n", 0, "rook")]}
    g = score.Geography(state, {"m": (0.0, 0.0), "n": (1.0, 0.0)}, {"m": {"n": 1.0}, "n": {"m": 1.0}},
                        polygon, parts)
    c = score.channel_looks("X", _rows("X", (("m", "X_01", 1.0), ("n", "X_01", 1.0))),
                            _districts("X", (2.0,)), g)
    assert c["pieces"] == [] and c["multipart"] == [("X_01", "m", 1.0)]
    parts["edges"].append(("m", 1, "n", 0, "rook"))     # n now meets both parts: one drawn piece
    g = score.Geography(state, g.xy, g.edge, polygon, parts)
    assert score.channel_looks("X", _rows("X", (("m", "X_01", 1.0), ("n", "X_01", 1.0))),
                               _districts("X", (2.0,)), g)["multipart"] == []


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
| M1 polygon contiguity | fail | 1 districts in pieces, 2 detached pieces (largest 0.25 τ), 0 channel ZCTAs with no owner, 2 (ZCTA, fine channel) cells with no row, 0 owned twice |
"""


def test_scorecard_parse():
    assert score.scorecard_checks(SCORECARD) == {
        "one owner per cell": "pass", "final bands on drawn mass": "fail",
        "planned against drawn owners": "listed", "ZIP contiguity": "listed",
        audit.M1_CHECK: "fail"}
    assert score.audit_pieces(SCORECARD) == 2          # M1's count, the one piece count (#116)
    assert score.audit_pieces("") is None


M1_PASS = audit.Check(audit.M1_CHECK, "pass", "0 districts in pieces")


def test_eligibility_rules():
    led = _rows("X", X_CELLS)
    ok = score.bands_at(led, {"X": 2}, 0.15)
    assert ok.status == "pass"
    assert score.bands_at(_rows("X", (("a1", "X_01", 1.2), ("b1", "X_02", 0.8))),
                          {"X": 2}, 0.15).status == "fail"           # 1.2 > 1.15
    checks = {**score.scorecard_checks(SCORECARD), audit.M1_CHECK: "pass"}   # ±10% band: ±15%
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
        f"audit: {audit.M1_CHECK} fails", "M1: fail, 1 districts in pieces"]
    # the run's own M1 also checks each cell's planning channel, which a run folder cannot (#116)
    assert score.eligibility({**checks, audit.M1_CHECK: "fail"}, ok, main, good, M1_PASS) == [
        f"audit: {audit.M1_CHECK} fails"]
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


def _gate_rows(ch: str, cells) -> list:
    """Ledger rows of channel `ch` from (ZIP, district, $) cells at a rate of 1 per $; the state is
    the ZIP's first letter."""
    return [{"zip_code": z, "current_channel": "x", "state": z[0].upper(), "model_channel": ch,
             "district": d, "m_rel": repr(float(m))} for z, d, m in cells]


def _gate(ch: str, cells, names) -> list:
    return score.dollar_gate(_gate_rows(ch, cells), [{"channel": ch, "district": d} for d in names],
                             {"x": 1.0})


def test_dollar_gate_window_edges_inclusive():
    """Every main-map window in whole dollars, edges included (precedent 2d189e9); a district
    sharing its state with another takes no allowance."""
    for ch, (lo, hi) in score.WINDOWS.items():
        for x, ok in ((lo, True), (hi, True), (lo - 1, False), (hi + 1, False)):
            rows = _gate(ch, (("a1", "D_01", x), ("a2", "D_02", lo)), ("D_02", "D_01"))
            assert [r["district"] for r in rows] == ["D_01", "D_02"]
            r = rows[0]
            assert (r["ok"], r["allowance"], r["whole_states"], r["cap"]) == (ok, False, False, None), (ch, x, r)
            assert (r["usd"], r["lo"], r["hi"], r["states"]) == (x, lo, hi, ["A"])


def test_whole_state_allowance_is_wifi_only_and_whole_states_only():
    """Owner, 2026-10-13: a WIFI district owning alone, in WIFI, every state it owns a ZCTA in may
    reach $1.6B; a zero-mass ZCTA of a shared state ends that, and no other channel has it."""
    names = ("W_01", "W_02", "W_03")
    cells = (("a1", "W_01", 1.0e9), ("a2", "W_01", 0.6e9), ("c1", "W_01", 0.0),   # A and C whole
             ("b1", "W_02", 1.2e9), ("b2", "W_03", 1.0e9))                          # B shared
    w1, w2, w3 = _gate("WIFI", cells, names)
    assert (w1["ok"], w1["allowance"], w1["whole_states"], w1["cap"], w1["states"]) == (
        True, True, True, 1.6e9, ["A", "C"])
    assert (w2["ok"], w2["allowance"], w2["whole_states"], w2["cap"]) == (False, False, False, None)
    assert (w3["ok"], w3["allowance"]) == (True, False)
    assert score.gate_reason(w2) == "$ W_02 1,200.0M outside 850.0-1,150.0M"
    edge = _gate("WIFI", (("a1", "W_01", 1.6e9),), names[:1])[0]
    over = _gate("WIFI", (("a1", "W_01", 1.6e9 + 1),), names[:1])[0]
    assert (edge["ok"], edge["allowance"]) == (True, True) and (over["ok"], over["allowance"]) == (False, False)
    assert score.gate_reason(over) == "$ W_01 1,600.0M outside 850.0-1,150.0M (whole states: up to 1,600.0M)"
    w1 = _gate("WIFI", cells + (("b3", "W_01", 0.0),), names)[0]
    assert (w1["ok"], w1["whole_states"], w1["states"]) == (False, False, ["A", "B", "C"])
    nat = _gate("national", (("a1", "N_01", 1.5e9),), ("N_01",))[0]
    assert (nat["ok"], nat["whole_states"], nat["cap"]) == (False, True, None)
    ne = _gate("NE", (("a1", "NE_01", 1.0e9),), ("NE_01",))[0]
    assert ne["lo"] is None and not ne["ok"]
    assert score.gate_reason(ne) == "$ NE_01: no dollar window for NE"


def test_eligibility_with_a_gate():
    """A main-map run: the gate's failing districts replace the ±15% band and the channel
    averages; an IFA-only run ignores a gate, and a call without one keeps the old rules."""
    checks = {**score.scorecard_checks(SCORECARD), audit.M1_CHECK: "pass"}
    off = audit.Check(score.BAND_CHECK, "fail", "1 outside")
    main = {"national": 15, "WH": 12, "FI": 20, "WIFI": 3}
    far = {"national": 2.0e9, "WH": 0.5e9, "FI": 0.9e9, "WIFI": 1.0e9}      # averages the gate never reads
    good = {"channel": "WH", "district": "WH_01", "usd": 1.0e9, "lo": 0.85e9, "hi": 1.15e9,
            "states": ["A"], "whole_states": False, "cap": None, "allowance": False, "ok": True}
    bad = dict(good, district="WH_02", usd=1.2e9, ok=False)
    assert score.eligibility(checks, off, main, far, M1_PASS, [good]) == []
    assert score.eligibility(checks, off, main, far, M1_PASS, [good, bad]) == [
        "$ WH_02 1,200.0M outside 850.0-1,150.0M"]
    # an IFA-only run keeps its band and average and adds the gate's failing districts (#105)
    ifa_bad = dict(bad, channel="IFA", district="IFA_02", lo=1.0e9, hi=1.4375e9, usd=0.9e9)
    assert score.eligibility({}, off, {"IFA": 49}, {"IFA": 1.227e9}, M1_PASS, [good]) == [
        "audit: no scorecard", "audit at ±15%: 1 outside"]
    assert score.eligibility({}, off, {"IFA": 49}, {"IFA": 1.227e9}, M1_PASS, [good, ifa_bad]) == [
        "audit: no scorecard", "audit at ±15%: 1 outside", "$ IFA_02 900.0M outside 1,000.0-1,437.5M"]
    assert score.eligibility(checks, off, main, far, M1_PASS) == [
        "audit at ±15%: 1 outside", "$ WH 500M is -50.0% of 1,000M", "$ national 2,000M is +60.0% of 1,250M"]


def test_write_dollars():
    rows = _gate("WIFI", (("a1", "W_01", 1.5e9), ("b1", "W_02", 0.9e9), ("b2", "W_03", 0.9e9)),
                 ("W_01", "W_02", "W_03"))
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "dollars.csv")
        score.write_dollars(path, rows)
        with open(path, newline="") as fh:
            got = list(csv.reader(fh))
    assert got[0] == score.DOLLAR_COLUMNS and len(got) == 4
    assert got[1] == ["WIFI", "W_01", "1500.000000", "850.000000", "1150.000000", "1600.000000", "A", "1", "1", "1"]
    assert got[2] == ["WIFI", "W_02", "900.000000", "850.000000", "1150.000000", "", "B", "0", "0", "1"]


def _score_toy(ch: str, rates: dict, fine=None, run_json=None) -> dict:
    """`score.score` on a run folder holding channel `ch` laid out as X; with `fine`, its
    `run.json` names the scenario's fine channels; `run_json` adds to that file."""
    with tempfile.TemporaryDirectory() as d:
        if fine is not None or run_json:
            with open(os.path.join(d, "run.json"), "w") as fh:
                json.dump({**({"fine_channels": fine} if fine is not None else {}), **(run_json or {})}, fh)
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
    # M1 on the ledger, strict: WH_02's a2 and b3 are cut off from b1, and a3, b2 have no row
    m1 = ("M1: fail, 1 districts in pieces, 2 detached pieces (largest 0.25 τ), 0 necks, 0 channel "
          "ZCTAs with no owner, 2 (ZCTA, fine channel) cells with no row, 0 owned twice, 0 mass "
          "necks listed beside M1 (fine channels from the ledger)")
    sc = f"audit: {audit.M1_CHECK} fails"           # SCORECARD's own M1 row
    assert not s["eligible"] and s["why"] == [sc, m1, "main K 2 outside 48-54"]
    assert s["m1"]["status"] == "fail" and s["m1"]["no_row"] == 2 and s["m1"]["pieces"] == 2
    assert (s["splits"], s["split_list"], s["distinct"]) == (1, ["WH:A"], ["A"])
    # the scorer's pieces are M1's, on the ledger with no display fill (#116): b3 (0.25 τ) and a2
    # (0.15 τ), weighing 1 + mass/τ each (owner, 2026-10-05)
    assert (s["thin_links"], s["small_pieces"], s["crowded_states"], s["contiguity_pieces"]) == (2, 1, 0, 2)
    assert s["contiguity_weight"] == 2.4 and s["largest_piece_tau"] == 0.25
    assert s["defects"] == 5.4 and s["audit_pieces"] == s["m1"]["pieces"] == 2
    assert math.isclose(s["largest_extent_km"], 9.0) and s["states_per_district"] == 2
    assert s["worst_dev"] == 0.0 and s["mean_dev"] == 0.0
    assert f"INELIGIBLE ({sc}; {m1}; main K 2 outside 48-54) | 1 splits (1 states) | 5.4 defects" in score.verdict(s)
    assert "largest detached piece WH_02: 1 ZIPs in B, 0.250 tau" in score.report(s)
    # the main map's dollar gate checks every district (2026-10-13): $1,000M each, in WH's window
    assert [(r["district"], round(r["usd"]), r["ok"]) for r in s["dollar_gate"]] == [
        ("WH_01", 1000000000, True), ("WH_02", 1000000000, True)]
    hot = _score_toy("WH", {"wh": 1.2e9})
    assert hot["why"] == [sc, m1, "$ WH_01 1,200.0M outside 850.0-1,150.0M",
                          "$ WH_02 1,200.0M outside 850.0-1,150.0M", "main K 2 outside 48-54"]
    assert "$ gate: 2 districts, 2 outside their window, 0 on the whole-state allowance" in score.report(hot)
    # An IFA-only run: no main K rule, and $ is the owner's whole-extract IFA total over K.
    ifa = _score_toy("IFA", {})
    # and each district is held to the IFA window, at the IFA rate on the ledger's own m_rel (#105)
    assert ifa["dollars"] == {"IFA": 62.14e9 / 2} and len(ifa["dollar_gate"]) == 2
    assert ifa["why"] == [sc, m1, "$ IFA_01 1.3M outside 1,000.0-1,437.5M",
                          "$ IFA_02 1.3M outside 1,000.0-1,437.5M", "$ IFA 31,070M is +2385.6% of 1,250M"]
    # the scenario's fine channels come from run.json (#116): fi has no row at all
    both = _score_toy("WH", {"wh": 1.0e9}, fine=["wh", "fi"])
    assert both["m1"]["no_row"] == 2 + 6 and "from the ledger" not in both["m1"]["summary"]


def _s(run, splits, defects, eligible=True, extent=100.0, worst=0.05):
    return {"run": run, "eligible": eligible, "splits": splits, "defects": defects,
            "largest_extent_km": extent, "states_per_district": 3, "worst_dev": worst,
            "mean_dev": 0.01, "review": None}


def test_a_diagnostic_folder_is_never_eligible():
    """Sol's review of #121 (P1): a folder marked diagnostic (a `--diag-final-delta` repair, its
    children, or a backfilled one) is INELIGIBLE with the reason "diagnostic band", first."""
    plain = _score_toy("WH", {"wh": 1.0e9})
    diag = _score_toy("WH", {"wh": 1.0e9}, run_json={"diagnostic": True, "diagnostic_band": 0.15,
                                                     "diagnostic_label": "backfilled"})
    assert not plain["diagnostic"] and diag["diagnostic"] and not diag["eligible"]
    assert diag["why"] == ["diagnostic band (backfilled)"] + plain["why"], diag["why"]
    assert "INELIGIBLE (diagnostic band (backfilled); " in score.verdict(diag)


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


def _score_ifa(masses):
    """`score.score` on an IFA-only run folder whose IFA_01.. hold one ZIP each of the given m_rel;
    `csv` is the `dollars.csv` `write_dollars` writes for its gate."""
    with tempfile.TemporaryDirectory() as d:
        ids = [f"IFA_{i:02d}" for i in range(1, len(masses) + 1)]
        led = _rows("IFA", ((f"a{i}", j, m) for i, (j, m) in enumerate(zip(ids, masses), 1)))
        with open(os.path.join(d, "ledger.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, list(led[0]))
            w.writeheader()
            w.writerows(led)
        with open(os.path.join(d, "districts.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, ["channel", "district", "drawn_mass"])
            w.writeheader()
            w.writerows(_districts("IFA", masses))
        with open(os.path.join(d, "scorecard.md"), "w") as fh:
            fh.write(SCORECARD)
        s = score.score(d, _geo(), {})
        path = os.path.join(d, "dollars.csv")
        score.write_dollars(path, s["dollar_gate"])
        with open(path, newline="") as fh:
            s["csv"] = list(csv.reader(fh))
        return s


def test_ifa_only_run_has_a_per_district_dollar_gate():
    """#105 (owner, 2026-10-15): an IFA-only run's districts are held to $1,000M-$1,437.5M, $ being
    the ledger's unrounded m_rel times the IFA rate; the reported `dollars` stays the whole-extract
    IFA total over K (owner, 2026-10-04)."""
    rate = score.tdspec.IFA_USD_PER_M_REL
    assert score.IFA_RATES == {"ifa": rate * 1e6} and score.IFA_WINDOW == {"IFA": (1.0e9, 1.4375e9)}
    lo_mass = 1000.0 / rate                            # 798.74236..., exactly $1,000M
    under = _score_ifa([lo_mass - 1e-6, 900.0])         # IFA_01 is $1.25 below the window
    gate = {r["district"]: r for r in under["dollar_gate"]}
    assert not gate["IFA_01"]["ok"] and gate["IFA_02"]["ok"]
    assert math.isclose(gate["IFA_01"]["usd"], (lo_mass - 1e-6) * rate * 1e6)
    reason = "$ IFA_01 1,000.0M outside 1,000.0-1,437.5M"
    assert reason in under["why"] and not under["eligible"]
    assert under["dollars"] == {"IFA": 62.14e9 / 2}      # the reported average, unchanged
    assert "$ gate: 2 districts, 1 outside their window" in score.report(under)
    # one row per IFA district, unrounded to the whole dollar, the failing one flagged
    assert under["csv"][0] == score.DOLLAR_COLUMNS and len(under["csv"]) == 3
    row = under["csv"][1]
    assert row[:2] == ["IFA", "IFA_01"] and row[3:5] == ["1000.000000", "1437.500000"] and row[-1] == "0"
    assert float(row[2]) == round((lo_mass - 1e-6) * rate, 6) and row[2] == "999.999999"
    assert under["csv"][2][:2] == ["IFA", "IFA_02"] and under["csv"][2][-1] == "1"
    # all in the window, the edges included: no gate reason
    inside = _score_ifa([lo_mass, 1437.5 / rate])
    assert all(r["ok"] for r in inside["dollar_gate"])
    assert not [w for w in inside["why"] if w.startswith("$ IFA_")]
    # eligible: with the audit, bands, M1 and the gate all passing, nothing is left to fail
    checks = {**score.scorecard_checks(SCORECARD), audit.M1_CHECK: "pass"}
    ok = audit.Check(score.BAND_CHECK, "pass", "")
    assert score.eligibility(checks, ok, {"IFA": 2}, {"IFA": 1.25e9}, M1_PASS, inside["dollar_gate"]) == []
    assert score.eligibility(checks, ok, {"IFA": 2}, {"IFA": 1.25e9}, M1_PASS, under["dollar_gate"]) == [reason]
    over = _score_ifa([1437.5 / rate + 1e-3, 900.0])
    assert [r["ok"] for r in over["dollar_gate"]] == [False, True]
