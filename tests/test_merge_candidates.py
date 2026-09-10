"""test_merge_candidates.py: tools/merge_candidates.py, the pre-screen of the three options.

A six-state toy carries one state per rule, so the branches of the rule in the tool's
docstring are exercised on numbers small enough to check by hand.  The states sit on a line,
`td.geo.state_rook` is monkeypatched to that path the way `tests/test_full_plan_cli.py`
patches it, and the spacing is chosen so the smallest radius leaves every state alone, the
middle one reaches a neighbour, and the largest reaches two hops.  S0, S1 and S2 are the
cluster; S3, S4 and S5 are parked far apart, so no radius reaches them and their verdicts are
properties of their own cells alone, which is what a bundle that never reaches L needs.

Every bundle is read at its own R*, so a state whose WH is short of L on its own but reaches
over a neighbour is not a merge candidate: S1 is that state, and the two degenerate branches
no toy state carries (`national_unreachable` and `national_unreachable_no_fallback`) are
checked against `verdict` itself, which is a pure function of the R* map and the books.

The stage-2 values are checked against an independent Hungarian: the utility is rewritten from
`docs/FULL_PROBLEM.md` section 3 and the best assignment found by brute force over the
permutations, so the test does not restate the code it is checking.
"""
from __future__ import annotations

import gzip
import itertools
import json
import math
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import numpy as np                              # noqa: E402

from td import channels                         # noqa: E402
from td import geo as td_geo                    # noqa: E402
from td import instance as td_instance          # noqa: E402
import borders_report                           # noqa: E402
import merge_candidates as mc                   # noqa: E402

STATES = [f"S{i}" for i in range(6)]
REPS = [f"r{i}" for i in range(5)]

# the path S0 - S1 - ... - S5; S3, S4 and S5 are in the graph but out of every radius
PATH_ADJ = {f"S{i}": tuple(f"S{j}" for j in (i - 1, i + 1) if 0 <= j < 6) for i in range(6)}

# centroids in km along a line: the cluster 300 apart, then 2,400, 3,000 and 3,000 away
KM = [0.0, 300.0, 600.0, 3000.0, 6000.0, 9000.0]
RADII = [200.0, 400.0, 700.0]
L = 10.0

# (N_WH, N_FI, WH, FI) per state, in the fine-label order of `channels.CHANNELS`
MASS = {
    "S0": (6.0, 6.0, 11.0, 11.0),        # every pure channel fits on its own
    "S1": (6.0, 6.0, 6.0, 6.0),          # WH and FI short alone, reached over S0 and S2
    "S2": (6.0, 6.0, 11.0, 11.0),        # like S0; its books are what differ
    "S3": (6.0, 6.0, 6.0, 6.0),          # alone: WH and FI each short, the pair in band
    "S4": (1.0, 1.0, 6.0, 6.0),          # alone: national, WH+ and FI+ all short, WHFI fits
    "S5": (0.5, 0.5, 0.5, 0.5),          # alone: nothing reaches L
}

# {state: {rep: {channel: book}}}; every entry stays under the state's own mass
BOOKS = {
    "S0": {"r0": {"WH": 5.0}, "r1": {"FI": 5.0},
           "r2": {"WH": 1.0, "FI": 1.0, "N_WH": 1.0},
           "r3": {"N_WH": 4.0, "N_FI": 4.0}},
    "S1": {"r0": {"WH": 3.0, "FI": 3.0}, "r1": {"WH": 1.0},
           "r3": {"N_WH": 3.0, "N_FI": 3.0}},
    "S2": {"r0": {"WH": 5.0, "N_WH": 4.0}, "r1": {"FI": 5.0},
           "r2": {"WH": 1.0, "FI": 1.0}, "r3": {"N_FI": 0.5}},
    "S3": {"r0": {"WH": 3.0}, "r1": {"FI": 3.0}, "r3": {"N_WH": 3.0, "N_FI": 3.0}},
    "S4": {"r0": {"WH": 3.0}, "r1": {"FI": 3.0}, "r3": {"N_WH": 0.5, "N_FI": 0.5}},
    "S5": {"r0": {"WH": 0.2}},
}

FILLER = 0.1


def _cells():
    """The toy as a `channels.CellTable`, the shape `screen` reads."""
    C = channels.CHANNELS
    M = np.array([MASS[s] for s in STATES], float)
    S = np.zeros((len(REPS), len(STATES), len(C)), float)
    for si, state in enumerate(STATES):
        for rep, per in BOOKS[state].items():
            for c, v in per.items():
                S[REPS.index(rep), si, C.index(c)] = v
    return channels.CellTable(state_list=tuple(STATES), channels=C, reps=tuple(REPS),
                              M=M, S=S, S_free=np.full((len(STATES), len(C)), FILLER))


def _xy():
    return np.array([[km, 0.0] for km in KM], float)


def _polys():
    """`state_rook`'s second return: anything with `.centroid.x` in metres will do."""
    return {s: types.SimpleNamespace(centroid=types.SimpleNamespace(x=KM[i] * 1000.0, y=0.0))
            for i, s in enumerate(STATES)}


def _rows():
    return mc.screen(_cells(), PATH_ADJ, _xy(), L=L, radii=RADII, usd_per_unit=1.0e6)


def _row(rows, state):
    return next(r for r in rows if r["state"] == state)


# ------------------------------------------------------------------------------------ reach
def test_reach_is_the_bfs_over_the_states_inside_the_radius():
    """A district gathers mass from what its own district can reach: the rook graph induced
    on the states within R km of the centroid, BFS from the state itself."""
    cells = _cells()
    j = {c: i for i, c in enumerate(cells.channels)}

    at200 = mc.reach(cells, PATH_ADJ, _xy(), 200.0)
    assert np.allclose(at200, cells.M), "at 200 km every state is alone"

    at400 = mc.reach(cells, PATH_ADJ, _xy(), 400.0)
    assert at400[0, j["WH"]] == MASS["S0"][2] + MASS["S1"][2]          # S0 reaches S1
    assert at400[1, j["WH"]] == sum(MASS[s][2] for s in ("S0", "S1", "S2"))
    assert at400[3, j["WH"]] == MASS["S3"][2], "S3 is 2,400 km from its rook neighbour"
    assert at400[5, j["WH"]] == MASS["S5"][2]

    at700 = mc.reach(cells, PATH_ADJ, _xy(), 700.0)
    assert at700[0, j["FI"]] == sum(MASS[s][3] for s in ("S0", "S1", "S2"))
    assert at700[2, j["FI"]] == sum(MASS[s][3] for s in ("S0", "S1", "S2"))
    for far in (3, 4, 5):
        assert at700[far, j["FI"]] == MASS[STATES[far]][3], "no radius reaches the far states"

    # the bundle forms are sums of the fine channels, nothing more
    r = mc.bundle_reach(cells, at200, 0)
    assert r["N"] == 12.0 and r["WHFI"] == 22.0
    assert r["WH_PLUS"] == 11.0 + 6.0 and r["FI_PLUS"] == 11.0 + 6.0


def test_a_state_with_no_mass_of_its_own_cannot_host_that_pure_district():
    """Reach counts the neighbourhood, so a state with none of channel c would otherwise read
    as able to hold a pure c district it cannot be part of."""
    cells = _cells()
    M = np.array(cells.M, float)
    M[0, cells.channels.index("WH")] = 0.0
    stripped = channels.CellTable(state_list=cells.state_list, channels=cells.channels,
                                  reps=cells.reps, M=M, S=cells.S, S_free=cells.S_free)
    at700 = mc.reach(stripped, PATH_ADJ, _xy(), 700.0)
    assert mc.bundle_reach(stripped, at700, 0)["WH"] >= L, "the neighbourhood has the mass"
    assert mc.reachable(stripped, at700, 0, L)["WH"] is False
    assert mc.reachable(stripped, at700, 0, L)["FI"] is True


# ------------------------------------------------------------------------------ rep overlap
def test_rep_overlap_counts_the_books_a_merge_and_a_drop_turn_on():
    """Three counts per state: who holds WH and FI both, who holds national beside one of
    them, and who holds national alone and so loses under a drop."""
    cells = _cells()

    s0 = mc.rep_overlap(cells, STATES.index("S0"))
    assert s0["reps_both"] == 1 and s0["book_both"] == 2.0      # r2 holds WH 1 and FI 1
    assert s0["book_whfi"] == 12.0
    assert abs(s0["overlap_share"] - 2.0 / 12.0) < 1e-12
    assert s0["reps_absorb"] == 1 and s0["book_absorb"] == 1.0  # r2's national book
    assert s0["book_n"] == 9.0
    assert abs(s0["absorb_share"] - 1.0 / 9.0) < 1e-12
    assert s0["reps_only_n"] == 1 and s0["book_only_n"] == 8.0  # r3
    # what a drop costs: r3 holds 8 of the 9 national book and nothing else there
    assert abs(s0["only_n_share"] - 8.0 / 9.0) < 1e-12
    assert abs(s0["only_n_share"] + s0["absorb_share"] - 1.0) < 1e-12

    s1 = mc.rep_overlap(cells, STATES.index("S1"))
    assert s1["reps_both"] == 1 and s1["book_both"] == 6.0      # r0 holds WH 3 and FI 3
    assert abs(s1["overlap_share"] - 6.0 / 7.0) < 1e-12

    s2 = mc.rep_overlap(cells, STATES.index("S2"))
    assert s2["reps_absorb"] == 1 and s2["book_absorb"] == 4.0  # r0 holds WH and national
    assert abs(s2["overlap_share"] - 2.0 / 12.0) < 1e-12
    assert s2["reps_only_n"] == 1 and s2["book_only_n"] == 0.5
    assert abs(s2["only_n_share"] - 0.5 / 4.5) < 1e-12
    assert s2["only_n_share"] < mc.ONLY_N_MAX, "S2 is the state a drop costs almost nothing"

    s5 = mc.rep_overlap(cells, STATES.index("S5"))
    assert s5["book_n"] == 0.0 and s5["absorb_share"] == 0.0, "no book is a zero share"
    assert s5["only_n_share"] == 0.0


# --------------------------------------------------------------------------- stage 2 values
def _hand_value(cells, state, bundles, *, theta=0.40, lam=0.30):
    """The Nash value of these slots at this state, from the utility of section 3 by hand.

    `filler_capture="theta"` means `c_free = c2`.  Brute force over the injective assignments
    of reps to slots, so nothing here reuses the tool's matching.
    """
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    s = list(cells.state_list).index(state)
    j = {c: k for k, c in enumerate(cells.channels)}
    S, M, F = (np.asarray(cells.S, float), np.asarray(cells.M, float),
               np.asarray(cells.S_free, float))

    def u(i, c):
        col = j[c]
        T = S[:, s, col].sum()
        return (c1 * S[i, s, col] + c2 * (T - S[i, s, col]) + c2 * F[s, col]
                + lam * M[s, col])

    g = [[sum(u(i, c) for c in bundle) for bundle in bundles]
         for i in range(len(cells.reps))]
    best = -math.inf
    for pick in itertools.permutations(range(len(cells.reps)), len(bundles)):
        best = max(best, sum(math.log(g[i][k]) for k, i in enumerate(pick)))
    return best


def test_the_three_option_values_are_the_hungarian_on_the_state_s_own_cells():
    """Three pure slots, N plus a merged WHFI slot, and WH+ plus FI+, each staffed over this
    state's cells alone."""
    cells = _cells()
    for state in ("S0", "S3"):
        for name, bundles in mc.OPTIONS.items():
            got = mc.option_value(cells, state, bundles, theta=0.40, lam=0.30,
                                  filler_capture="theta")
            want = _hand_value(cells, state, bundles)
            assert abs(got - want) < 1e-9, (state, name, got, want)

    rows = _rows()
    r = _row(rows, "S0")
    assert abs(r["v_keep"] - _hand_value(cells, "S0", mc.OPTIONS["keep"])) < 1e-9
    # three slots against two: the per-slot column is the only comparable one
    assert abs(r["v_keep_per_slot"] - r["v_keep"] / 3.0) < 1e-12
    assert abs(r["v_merge_per_slot"] - r["v_merge"] / 2.0) < 1e-12
    assert abs(r["d_merge"] - (r["v_merge"] - r["v_keep"])) < 1e-12


def test_an_option_whose_slot_has_nothing_to_staff_scores_none():
    """A slot carrying no mass, no book and no filler cannot be staffed, and the option is
    reported as unpriced rather than raising out of the Hungarian."""
    cells = _cells()
    M = np.zeros_like(np.asarray(cells.M, float))
    empty = channels.CellTable(state_list=cells.state_list, channels=cells.channels,
                               reps=cells.reps, M=M,
                               S=np.zeros_like(np.asarray(cells.S, float)),
                               S_free=np.zeros_like(np.asarray(cells.S_free, float)))
    assert mc.option_value(empty, "S0", mc.OPTIONS["keep"], theta=0.4, lam=0.3,
                           filler_capture="theta") is None


# ----------------------------------------------------------------------------- the verdicts
def test_every_branch_of_the_rule_fires_on_the_toy():
    """One state per rule, and the rule column names which branch it was."""
    rows = _rows()
    got = {r["state"]: (r["verdict"], r["rule"]) for r in rows}
    assert got["S0"] == ("keep", "pure_channels_reach")
    assert got["S1"] == ("merge", "books_overlap")
    assert got["S2"] == ("drop_n", "national_book_absorbed")
    assert got["S3"] == ("merge", "pure_pair_unreachable")
    assert got["S4"] == ("merge", "national_unreachable_whfi_reaches")
    assert got["S5"] == ("other", "nothing_reaches")


def test_each_bundle_is_read_at_its_own_smallest_radius():
    """S1's WH is short of L on its own and reaches over S0 and S2, so its R* is 400 while its
    national's is 200.  Reading WH at national's radius made a merge candidate of it."""
    rows = _rows()
    r1 = _row(rows, "S1")
    assert r1["r_star_n"] == 200.0, "S1's own national mass is 12, above L"
    assert r1["r_star_wh"] == 400.0 and r1["r_star_fi"] == 400.0
    assert r1["r_star_whfi"] == 200.0, "the pair fits on S1 alone"
    assert r1["verdict"] == "merge" and r1["rule"] == "books_overlap", \
        "S1 merges on its books, not because a pure channel cannot reach"

    # the far states never reach past themselves, so a short bundle is short at every radius
    r3 = _row(rows, "S3")
    assert r3["r_star_n"] == 200.0 and r3["r_star_whfi"] == 200.0
    assert r3["r_star_wh"] is None and r3["r_star_fi"] is None
    r4 = _row(rows, "S4")
    assert r4["r_star_n"] is None and r4["r_star_whfi"] == 200.0
    assert r4["r_star_wh_plus"] is None and r4["r_star_fi_plus"] is None
    assert all(_row(rows, "S5")[f"r_star_{b.lower()}"] is None for b in mc.FORMS)


def test_feasibility_is_read_before_the_books_and_the_books_before_keep():
    """The branch order of the docstring, on the R* map directly: a pure pair that cannot
    reach merges whatever the books say, a state whose channels all reach still leaves `keep`
    when a book argues otherwise, and the two branches no toy state carries."""
    everywhere = {b: 200.0 for b in mc.FORMS}
    quiet = dict(overlap_share=0.0, only_n_share=1.0)
    assert mc.verdict(everywhere, quiet) == ("keep", "pure_channels_reach")
    assert mc.verdict(everywhere, dict(overlap_share=mc.MOST, only_n_share=1.0))[0] == "merge"
    assert mc.verdict(everywhere, dict(overlap_share=0.0, only_n_share=0.0))[0] == "drop_n"
    # the threshold is strict: a state whose national-only book is exactly the cap keeps it
    assert mc.verdict(everywhere,
                      dict(overlap_share=0.0, only_n_share=mc.ONLY_N_MAX))[0] == "keep"

    short = dict(everywhere, WH=None, FI=None)
    assert mc.verdict(short, dict(overlap_share=0.9, only_n_share=0.0)) == \
        ("merge", "pure_pair_unreachable")

    dead = {b: None for b in mc.FORMS}
    assert mc.verdict(dead, quiet) == ("other", "nothing_reaches")
    # national never reaches: the plus bundles first, then the merged one, then nothing
    plus = dict(dead, WH_PLUS=700.0, FI_PLUS=700.0, WHFI=700.0)
    assert mc.verdict(plus, quiet) == ("drop_n", "national_unreachable")
    assert mc.verdict(dict(dead, WHFI=700.0), quiet) == \
        ("merge", "national_unreachable_whfi_reaches")
    assert mc.verdict(dict(dead, WH_PLUS=700.0), quiet) == \
        ("other", "national_unreachable_no_fallback")


def test_rows_are_ranked_by_the_mass_at_stake_and_carry_the_dollar_columns():
    rows = _rows()
    masses = [r["mass_total"] for r in rows]
    assert masses == sorted(masses, reverse=True)
    assert [r["rank"] for r in rows] == list(range(1, len(STATES) + 1))
    top = rows[0]
    assert top["mass_total"] == sum(MASS[top["state"]])
    # `usd_per_unit` of 1e6 makes one descaled unit one $MM, so the columns are the masses
    assert abs(top["usd_mm_total"] - top["mass_total"]) < 1e-9
    assert abs(sum(r["share_of_total"] for r in rows) - 1.0) < 1e-9


# ------------------------------------------------------------------------------- end to end
def _write_v2(path: str) -> None:
    """The toy as a format-2 instance, one zip per (state, channel)."""
    z, chan, m_rel, share, share_free, state = [], [], [], [], [], []
    for si, st in enumerate(STATES):
        for ci, c in enumerate(channels.CHANNELS):
            z.append(f"{10000 + si:05d}")
            chan.append(c)
            m_rel.append(MASS[st][ci])
            share.append({rep: per[c] / MASS[st][ci]
                          for rep, per in BOOKS[st].items() if per.get(c)})
            share_free.append(FILLER / MASS[st][ci])
            state.append(st)
    obj = dict(
        format=td_instance.FORMAT_V2,
        nodes=dict(z=z, channel=chan, m_rel=m_rel, share=share, share_free=share_free,
                   state=state),
        edges=dict(u=[f"{10000 + i:05d}" for i in range(len(STATES) - 1)],
                   v=[f"{10001 + i:05d}" for i in range(len(STATES) - 1)]),
        meta=dict(channels=list(channels.CHANNELS)),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def test_the_cli_writes_the_csv_the_markdown_and_the_params():
    """`geo.state_rook` is monkeypatched to the toy path and its centroids, so the run needs
    no shapefile.  The national mass is 53, so `--k 53 --band-lo 10` puts L back at the 10 the
    hand cases use and every verdict has to survive the round trip through the file."""
    national = sum(MASS[s][0] + MASS[s][1] for s in STATES)
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        out = os.path.join(tmp, "out")
        _write_v2(inst)
        orig = td_geo.state_rook
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, _polys())
        try:
            rc = mc.main([inst, "--k", str(int(national)), "--band-lo", str(L),
                          "--radius", "200,400,700", "--geo-cache", "unused", "--out", out])
            assert rc == 0, rc
        finally:
            td_geo.state_rook = orig

        import csv
        with open(os.path.join(out, "candidates.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == len(STATES)
        assert {r["state"]: r["verdict"] for r in rows} == {
            "S0": "keep", "S1": "merge", "S2": "drop_n", "S3": "merge",
            "S4": "merge", "S5": "other"}
        # the per-bundle R* columns survive the round trip, empty where a bundle never reaches
        s3 = next(r for r in rows if r["state"] == "S3")
        assert s3["r_star_n"] == "200.0" and s3["r_star_whfi"] == "200.0"
        assert s3["r_star_wh"] == "" and s3["r_star_fi"] == ""
        with open(os.path.join(out, "params.json"), encoding="utf-8") as fh:
            params = json.load(fh)
        assert abs(params["L"] - L) < 1e-9, "tau = national / k = 1, so L is band_lo"
        assert params["radius"] == [200.0, 400.0, 700.0] and params["scale_k"] == mc.SCALE_K
        with open(os.path.join(out, "candidates.md"), encoding="utf-8") as fh:
            md = fh.read()
        assert md.startswith("# Merge candidates") and "| S0 |" in md
        for r in rows:
            assert r["rule"] in md or int(r["rank"]) > 15


def test_stage2_weight_flags_default_to_borders_report_s_own_constants():
    """A screen scored under other weights is not comparable with the committed map's number,
    the reason `tests/test_full_plan_cli.py` pins the same three."""
    args = mc.build_argparser().parse_args(["instance.json.gz", "--out", "out"])
    assert args.theta == borders_report.THETA
    assert args.lam == borders_report.LAM
    assert args.filler_capture == borders_report.FILLER_CAPTURE
    assert args.k == 18 and args.band_lo == 0.8
    assert mc._parse_radii(args.radius) == [400.0, 600.0, 900.0]
