"""tools/maps/seat_optimize.py: the open seats chosen by optimisation, hand-worked on made-up td_seat_fit rows (no Snowflake).
Neighbours are kept people (KIND NEIGHBOUR, KEPT Y, with G); holders are not kept (KIND HOLDER, KEPT N)."""
import collections
import importlib.util
import math
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "maps"))
import seat_optimize as so  # noqa: E402

_spec = importlib.util.spec_from_file_location("scenario_maps", ROOT / "tools" / "maps" / "scenario_maps.py")
sm = importlib.util.module_from_spec(_spec)
sys.modules["scenario_maps"] = sm
_spec.loader.exec_module(sm)

ADJ = {("MD", "DC"), ("MD", "VA"), ("DC", "VA"), ("NE", "IA")}      # MD-DC allowed together, MD-NE never next to each other


def nb(seat, key, u, g):
    return {"SEAT": seat, "KIND": "NEIGHBOUR", "HOLDER": key, "KEPT": "Y", "U": u, "G": g, "SEAT_MM_OPP": 1e8}


def ho(seat, key, u):
    return {"SEAT": seat, "KIND": "HOLDER", "HOLDER": key, "KEPT": "N", "U": u, "G": None, "SEAT_MM_OPP": 1e8}


def best(rows, p=5, adj=ADJ, top=4):
    return so.optimize(rows, adj, p, top)


def choice(plan):
    return {c["seat"]: (c["choice"], c["holder"]) for c in plan["choices"]}


def test_a_holder_who_outsells_the_neighbour_gets_the_seat_and_the_neighbour_is_the_runner_up():
    rows = [nb("MD", "R1", 10, 100), ho("MD", "R5", 50)]
    plans = best(rows)
    assert choice(plans[0]) == {"MD": ("READD", "R5")} and plans[0]["readds"] == 1
    assert choice(plans[1]) == {"MD": ("NEIGHBOUR", "R1")} and plans[0]["F"] == 50 and plans[1]["F"] == 10
    assert abs(plans[1]["gap"] - 0.8) < 1e-12 and plans[0]["gap"] == 0 and len(plans) == 2          # two distinct plans exist
    assert choice(best([nb("MD", "R1", 90, 100), ho("MD", "R5", 50)])[0]) == {"MD": ("NEIGHBOUR", "R1")}   # the neighbour outsells the holder


def test_with_one_slot_and_two_candidates_the_bigger_gain_wins():
    rows = [nb("MD", "R1", 10, 100), nb("NE", "R1", 5, 100), ho("MD", "R5", 30), ho("NE", "R6", 20)]
    plan = best(rows, p=1)[0]
    assert choice(plan) == {"MD": ("READD", "R5"), "NE": ("NEIGHBOUR", "R1")} and plan["F"] == 35      # 30 + 5 against 20 + 10
    assert best(rows, p=2)[0]["F"] == 50 and best(rows, p=0)[0]["F"] == 15 and best(rows, p=0)[0]["readds"] == 0


def test_a_bundle_must_be_connected_md_dc_allowed_md_ne_refused():
    rows = [ho(s, "R5", 100) for s in ("MD", "DC", "NE")]
    plans = best(rows)
    top = plans[0]
    assert choice(top) == {"DC": ("READD", "R5"), "MD": ("READD", "R5"), "NE": ("VACANT", "")} and top["F"] == 200
    assert {c["bundle"] for c in top["choices"] if c["choice"] == "READD"} == {("DC", "MD")}
    for plan in plans:                                   # MD and NE (or all three) never in one holder's bundle
        for c in plan["choices"]:
            assert not {"MD", "NE"} <= set(c["bundle"])
    one = so.connected(0b011, [0b010, 0b001, 0])         # seats 0 and 1 next to each other; seat 2 alone
    assert one and not so.connected(0b101, [0b010, 0b001, 0]) and so.connected(0b100, [0b010, 0b001, 0])
    # one holder per seat set: R6 takes NE, so both are re-added when a second holder exists
    plan = best(rows + [ho("NE", "R6", 10)])[0]
    assert choice(plan) == {"DC": ("READD", "R5"), "MD": ("READD", "R5"), "NE": ("READD", "R6")} and plan["readds"] == 2


def test_a_neighbour_takes_two_seats_only_within_its_borders_and_the_nash_picks_the_lighter_book():
    # R1 borders MD and DC (heavy book), R2 borders MD only (light book): DC can only go to R1; MD to R2 (ln 2 + ln 1.1 > ln 1.2)
    rows = [nb("MD", "R1", 100, 1000), nb("DC", "R1", 100, 1000), nb("MD", "R2", 100, 100)]
    plan = best(rows)[0]
    assert choice(plan) == {"MD": ("NEIGHBOUR", "R2"), "DC": ("NEIGHBOUR", "R1")}
    assert abs(plan["nash"] - (math.log(2) + math.log(1.1))) < 1e-12
    assert {c["holder"] for c in plan["choices"] if c["seat"] == "DC"} == {"R1"}           # R2 never gets DC: not in N_k
    # the same book weights: R1 alone borders both, so it takes both
    plan = best([nb("MD", "R1", 100, 1000), nb("DC", "R1", 100, 1000)])[0]
    assert choice(plan) == {"MD": ("NEIGHBOUR", "R1"), "DC": ("NEIGHBOUR", "R1")} and abs(plan["nash"] - math.log(1.2)) < 1e-12
    # g NULL or 0: term 0, the seat still goes to someone (no vacancy with a neighbour)
    plan = best([nb("MD", "R1", 100, None), nb("MD", "R2", 50, 0)])[0]
    assert choice(plan) == {"MD": ("NEIGHBOUR", "R1")} and plan["nash"] == 0.0


def test_vacancy_only_when_no_neighbour_borders_and_no_slot_or_holder_is_left():
    rows = [nb("MD", "R1", 0, 100), ho("DC", "R5", 40), ho("NE", "R6", 30)]
    got = choice(best(rows, p=1)[0])
    assert got == {"MD": ("NEIGHBOUR", "R1"), "DC": ("READD", "R5"), "NE": ("VACANT", "")}      # no neighbour at NE, one slot, DC the bigger
    assert choice(best(rows, p=2)[0]) == {"MD": ("NEIGHBOUR", "R1"), "DC": ("READD", "R5"), "NE": ("READD", "R6")}
    assert choice(best(rows, p=0)[0])["DC"] == ("VACANT", "") and choice(best(rows, p=0)[0])["MD"] == ("NEIGHBOUR", "R1")   # U 0 still goes whole to a neighbour
    for plan in best(rows, p=2):                          # a seat with a neighbour is never vacant
        assert choice(plan)["MD"][0] != "VACANT"
    assert choice(best([nb("MD", "R1", 5, 100)] + [ho("MD", "R5", 0)])[0]) == {"MD": ("NEIGHBOUR", "R1")}   # a holder worth 0 is not re-added


def test_ties_are_deterministic_higher_nash_then_fewer_readds_then_lower_keys():
    rows = [nb("MD", "R7", 10, 100), nb("MD", "R2", 10, 100), nb("MD", "R30", 10, 100)]
    for order in (rows, rows[::-1], rows[1:] + rows[:1]):
        plans = best(order)
        assert len(plans) == 1 and choice(plans[0]) == {"MD": ("NEIGHBOUR", "R2")}      # equal Nash: the lower key number, 2 before 7 and 30
    rows = [nb("MD", "R20", 10, 100), nb("MD", "R3", 10, 100), nb("MD", "R100", 10, 100)]
    assert choice(best(rows)[0]) == {"MD": ("NEIGHBOUR", "R3")}                          # numbers, not text ('R100' < 'R20' as text)
    # the same F and the same Nash (the neighbour's book is NULL, term 0): the plan with fewer re-adds first
    plans = best([nb("MD", "R1", 10, None), ho("MD", "R5", 10)])
    assert [p["readds"] for p in plans] == [0, 1] and [p["F"] for p in plans] == [10, 10]
    # holders with equal U: lower key numbers first, whatever the row order; then the vacancy (no neighbour)
    rows = [ho("MD", "R9", 10), ho("MD", "R3", 10), ho("MD", "R12", 10)]
    want = [("READD", "R3"), ("READD", "R9"), ("READD", "R12"), ("VACANT", "")]
    assert [choice(p)["MD"] for p in best(rows)] == want and best(rows) == best(rows[::-1])


def test_the_inner_choice_compares_exact_scores_not_nine_decimals():
    # reviewer's P = 0 case: R3's term beats R2's by 3e-10, below the old 9-decimal key, which then fell to the higher U (R2)
    rows = [nb("DC", "R1", 221402758.40, 1e9), nb("MD", "R2", 210341836.37, 2e9), nb("MD", "R3", 105170918.52, 1e9)]
    want = brute(rows, ADJ, 0)[0]
    plan = best(rows, p=0)[0]
    assert choice(plan) == {"DC": ("NEIGHBOUR", "R1"), "MD": ("NEIGHBOUR", "R3")}, plan
    assert plan["nash"] == want[1] and plan["F"] == want[0]
    # an exact tie still goes to the higher sum U, then the lower key: R2 and R3 with the same term, R3 with more U
    rows = [nb("MD", "R2", 10, 100), nb("MD", "R3", 10, 100)]
    assert choice(best(rows)[0]) == {"MD": ("NEIGHBOUR", "R2")}


def test_trimming_and_ranking_use_the_same_exact_order_whatever_top_is():
    rows = [ho("MD", f"R{i}", 100 + 0.0002 * (i - 1)) for i in range(1, 6)]
    for top in (4, 5):
        plans = best(rows, p=1, top=top)
        assert choice(plans[0]) == {"MD": ("READD", "R5")}, (top, choice(plans[0]))        # the most U, not the lowest key at the same cent
        assert [choice(p)["MD"][1] for p in plans[:4]] == ["R5", "R4", "R3", "R2"], top


def test_the_cap_comes_from_the_sheet_count():
    person = [{"EST_SOURCE": "E", "HOLDER": f"R{i}", "ROLE": r} for i, r in enumerate(["NATIONAL", "WH", "WIFI", "WIFI"], 1)]
    person += [{"EST_SOURCE": "E", "HOLDER": "R1", "ROLE": "NATIONAL"}, {"EST_SOURCE": "E", "HOLDER": "R20", "ROLE": "OTHER"},
               {"EST_SOURCE": "F", "HOLDER": "R1", "ROLE": "NATIONAL"}]
    assert so.ROSTER_CAP == 49 and so.sheet_count(person, "E") == 4 and so.roster_room(person, "E") == 45 and so.roster_room(person, "F") == 48
    full = [{"EST_SOURCE": "E", "HOLDER": f"R{i}", "ROLE": "WH"} for i in range(60)]
    assert so.roster_room(full, "E") == -11                 # not clamped to 0: the caller refuses a roster over the cap
    try:
        best([nb("MD", "R1", 1, 100)], p=-11)
        raise AssertionError("a negative P was optimised")
    except ValueError:
        pass
    try:
        so.roster_room(person, "NOPE")
        raise AssertionError("an estimate with no person was accepted")
    except ValueError:
        pass
    # the cap bites: 49 - 48 on the sheet = 1 re-add left, 49 - 49 = none
    rows = [nb("MD", "R1", 1, 100), nb("NE", "R1", 1, 100), ho("MD", "R5", 30), ho("NE", "R6", 20)]
    sheet = lambda n: [{"EST_SOURCE": "E", "HOLDER": f"R{i}", "ROLE": "WH"} for i in range(n)]
    assert best(rows, so.roster_room(sheet(48), "E"))[0]["readds"] == 1 and best(rows, so.roster_room(sheet(47), "E"))[0]["readds"] == 2
    assert best(rows, so.roster_room(sheet(49), "E"))[0]["readds"] == 0


FIT_COLS = ["SCENARIO", "EST_SOURCE", "SEAT", "SEAT_MM_OPP", "KIND", "HOLDER", "SOURCE", "KEPT", "ROLE", "BORDERS", "U", "G", "DNASH", "RANK"]


def test_no_u_g_or_name_in_seat_plan_csv_and_the_names_file_has_them():
    def row(est, seat, kind, key, kept, u, g):
        return ("S", est, seat, 3e8 if seat == "MD" else 7e8, kind, key, "CRBG", kept, "WIFI", 1, u, g, None, 1)
    fit = [row("E", "MD", "NEIGHBOUR", "R1", "Y", 123456.78, 7777.5), row("E", "MD", "HOLDER", "R5", "N", 987654.32, None),
           row("E", "DC", "NEIGHBOUR", "R1", "Y", 55555.55, 7777.5), row("E", "NE", "HOLDER", "R6", "N", 4242.42, None)]
    person = (["SCENARIO", "EST_SOURCE", "HOLDER", "SOURCE", "ROLE", "ASSIGNED_STATES"], [("S", "E", "R1", "CRBG", "WIFI", "VA")])
    load = [dict(zip(sm.LOAD_COLS, ("S", "E", "R1", "WIFI", "REGIONAL", 100.0, 1e9, 1e9, 200.0, None, None)))]
    names = {"R1": "Ann Zed", "R5": "Bob Yoo", "R6": "Cy Xu"}
    got = sm.plan_prepare("S", (FIT_COLS, fit), person, sorted(ADJ), names, load, {"MD": 100.0, "DC": 50.0, "NE": 400.0})
    plan = got.plans["E"][0]
    assert choice(plan) == {"DC": ("NEIGHBOUR", "R1"), "MD": ("READD", "R5"), "NE": ("READD", "R6")} and len(got.plans["E"]) == 4
    assert got.lines == ["E: re-adds 2 of 48, vacancies 0, plan DC=R1 MD=R5* NE=R6* (* re-added)"], got.lines
    with tempfile.TemporaryDirectory() as d:
        masked, names_csv = sm.write_plan_csvs(d, {"S": got})
        text, ntext = open(masked, encoding="utf-8").read(), open(names_csv, encoding="utf-8").read()
        m = list(sm.csv.DictReader(open(masked, encoding="utf-8")))
        n = list(sm.csv.DictReader(open(names_csv, encoding="utf-8")))
    assert list(m[0]) == sm.PLAN_COLS == ["SCENARIO", "EST_SOURCE", "PLAN", "SEAT", "CHOICE", "HOLDER", "BUNDLE", "LOAD_BAND"]   # keys, choices, rank, band only
    assert not {"U", "G", "F", "NAME", "DNASH", "F_RANK_GAP"} & set(m[0]) and not [c for c in m[0] if "GAP" in c or c.startswith(("U", "F", "G"))] and len(m) == 4 * 3
    for secret in ("Ann", "Zed", "Bob", "Cy Xu", "123456", "987654", "7777", "55555", "4242"):
        assert secret not in text, secret
    assert collections.Counter(r["PLAN"] for r in m) == {"1": 3, "2": 3, "3": 3, "4": 3} and {r["SCENARIO"] for r in m} == {"S"}
    top = {r["SEAT"]: r for r in m if r["PLAN"] == "1"}
    assert top["MD"]["CHOICE"] == "READD" and top["MD"]["HOLDER"] == "R5" and top["MD"]["BUNDLE"] == "MD"
    assert top["DC"]["CHOICE"] == "NEIGHBOUR" and top["DC"]["BUNDLE"] == "" and top["DC"]["LOAD_BAND"] in ("under 0.8", "0.8 to 1.25", "over 1.25")
    assert top["MD"]["LOAD_BAND"] == ""                                                          # a re-added holder has no load row
    assert {"NAME", "U", "F", "F_RANK_GAP"} <= set(n[0]) and next(r for r in n if r["PLAN"] == "1" and r["SEAT"] == "MD")["NAME"] == "Bob Yoo" and "Ann Zed" in ntext
    assert next(r for r in n if r["PLAN"] == "1" and r["SEAT"] == "MD")["F_RANK_GAP"] == "0.0"                  # the gaps stay on the screen-only file


def brute(rows, adj, p, top=4):
    """The same optimum by trying every assignment of every seat (holder or none, then neighbour or none), exact (unrounded) scores:
    [(F, nash, readds)] best first."""
    import itertools
    seats = sorted({r["SEAT"] for r in rows})
    neigh = collections.defaultdict(dict)
    hold = collections.defaultdict(dict)
    g = {}
    for r in rows:
        if r["KIND"] == "NEIGHBOUR":
            neigh[r["HOLDER"]][r["SEAT"]], g[r["HOLDER"]] = r["U"], r["G"]
        elif r["KEPT"] == "N":
            hold[r["HOLDER"]][r["SEAT"]] = r["U"]

    def conn(ss):
        ss, seen, todo = set(ss), set(), [min(ss)]
        while todo:
            x = todo.pop()
            if x not in seen:
                seen.add(x)
                todo += [y for y in ss if (x, y) in adj or (y, x) in adj]
        return seen == ss
    out = {}
    for pick in itertools.product(*[[None] + [h for h in hold if s in hold[h]] for s in seats]):
        by = collections.defaultdict(list)
        for s, h in zip(seats, pick):
            if h:
                by[h].append(s)
        if len(by) > p or not all(conn(v) for v in by.values()):
            continue
        left = [s for s, h in zip(seats, pick) if not h]
        best = None
        for take in itertools.product(*[[k for k in neigh if s in neigh[k]] or [None] for s in left]):
            per = collections.defaultdict(float)
            for s, k in zip(left, take):
                if k:
                    per[k] += neigh[k][s]
            nash = sum(math.log1p(u / g[k]) for k, u in per.items() if g[k] and g[k] > 0)
            f_n = sum(per.values())
            if best is None or (nash, f_n) > best:           # exact scores, no rounding
                best = (nash, f_n)
        f = sum(hold[h][s] for h, v in by.items() for s in v) + best[1]
        out[pick] = (f, best[0], len(by))
    return sorted(out.values(), key=lambda t: (-t[0], -t[1], t[2]))[:top]


def test_the_search_agrees_with_trying_every_assignment():
    import random
    rng = random.Random(7)
    states = ["MD", "DC", "VA", "NE", "IA"]
    for trial in range(60):
        seats = rng.sample(states, rng.randint(2, 4))
        rows = []
        for k in range(rng.randint(1, 3)):
            g = rng.choice([None, 0, 50, 400])
            for s in seats:
                if rng.random() < 0.6:
                    rows.append(nb(s, f"R{k + 1}", float(rng.randint(1, 90)), g))
        for h in range(rng.randint(0, len(seats) + 5)):      # more holders than a seat's bundle can use: the trimming is exercised
            for s in seats:
                if rng.random() < 0.9:
                    rows.append(ho(s, f"R{h + 10}", float(rng.randint(1, 90))))
        if not rows:
            continue
        p = rng.randint(0, 3)
        got = [(x["F"], x["nash"], x["readds"]) for x in best(rows, p)]
        want = brute(rows, ADJ, p)
        # the brute force lists plans by F, Nash, re-adds: the same list, ties in F and Nash aside (U are whole dollars: F is exact)
        assert len(got) == min(4, len(want)) and all(g[0] == w[0] and abs(g[1] - w[1]) < 1e-12 for g, w in zip(got, want)), (trial, got, want)


def test_the_seat_page_has_an_optimal_plan_block_with_keys_names_and_the_gaps_but_no_dollars():
    from types import SimpleNamespace
    fit = [("S", "E", "MD", 3e8, "NEIGHBOUR", "R1", "CRBG", "Y", "WIFI", 1, 100.0, 1000.0, None, 1),
           ("S", "E", "MD", 3e8, "HOLDER", "R5", "CRBG", "N", "WIFI", 0, 150.0, None, None, 1),
           ("S", "E", "NE", 7e8, "HOLDER", "R6", "CRBG", "N", "WIFI", 0, 90.0, None, None, 1)]
    person = (["EST_SOURCE", "HOLDER", "ROLE"], [("E", "R1", "WIFI")])
    plan = sm.plan_prepare("S", (FIT_COLS, fit), person, [], {"R1": "Ann Zed", "R5": "Bob Yoo", "R6": "Cy Xu"}, [], {})
    cand = [{"EST_SOURCE": "E", "SEAT": r[2], "SEAT_MM_OPP": r[3], "KIND": r[4], "HOLDER": r[5], "RANK": 1, "BORDERS": r[9], "LOAD_BAND": ""} for r in fit]
    gd = SimpleNamespace(seat=SimpleNamespace(cand=cand, plan=plan), names={"R1": "Ann Zed", "R5": "Bob Yoo", "R6": "Cy Xu"})
    text = [t.get_text() for t in sm.draw_seat_page(gd, "t", "E").texts]
    block = next(t for t in text if t.startswith("Optimal plan"))
    both = "\n".join(text[text.index(block):])
    assert "F gap of plans 2 to" in block and "MD" in both and "READD" in both and "R5 Bob Yoo" in both and "NE" in both and "R6 Cy Xu" in both
    assert "100.0" not in both and "150.0" not in both and "e+" not in both          # no U, no F
    gd.seat.plan = None
    assert not [t for t in sm.draw_seat_page(gd, "t", "E").texts if t.get_text().startswith("Optimal plan")]


def test_a_plan_over_the_limits_is_refused_with_a_line_and_the_page_says_so():
    from types import SimpleNamespace
    def row(est, seat, kind, key, kept, u, g):
        return ("S", est, seat, 1e8, kind, key, "CRBG", kept, "WIFI", 1, u, g, None, 1)
    states = [f"X{i:02d}" for i in range(15)]
    fit = [row("BIG", s, "NEIGHBOUR", "R1", "Y", 1.0, 10.0) for s in states] + [row("OK", "MD", "NEIGHBOUR", "R1", "Y", 1.0, 10.0)]
    person = (["EST_SOURCE", "HOLDER", "ROLE"], [("BIG", "R1", "WIFI"), ("OK", "R1", "WIFI")])
    got = sm.plan_prepare("S", (FIT_COLS, fit), person, [], {}, [], {})
    assert got.notmade == {"BIG": "SEAT PLAN NOT MADE: S BIG: 15 open seats > 14"} and "BIG" not in got.plans and len(got.plans["OK"]) == 1
    assert len(got.masked[1]) == 1 and [l for l in got.lines if l.startswith("BIG")] == []
    over = (["EST_SOURCE", "HOLDER", "ROLE"], [(est, f"R{i}", "WH") for est in ("BIG", "OK") for i in range(50)])
    got = sm.plan_prepare("S", (FIT_COLS, fit), over, [], {}, [], {})
    assert got.notmade == {e: "SEAT PLAN NOT MADE: S: 50 people on the sheet > 49" for e in ("BIG", "OK")} and not got.plans and not got.masked[1] and not got.lines
    cand = [{"EST_SOURCE": "OK", "SEAT": "MD", "SEAT_MM_OPP": 1e8, "KIND": "NEIGHBOUR", "HOLDER": "R1", "RANK": 1, "BORDERS": 1, "LOAD_BAND": ""}]
    gd = SimpleNamespace(seat=SimpleNamespace(cand=cand, plan=got), names={})
    texts = [t.get_text() for t in sm.draw_seat_page(gd, "t", "OK").texts]
    assert any(t.startswith("Optimal plan") and "SEAT PLAN NOT MADE: S: 50 people on the sheet > 49" in t for t in texts), texts
