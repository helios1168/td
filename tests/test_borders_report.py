"""
test_borders_report.py -- tools/borders_report.py, Unit F of the borders build.

Two kinds of test.  The synthetic ones are pure functions on hand-built arrays/dicts and
always run.  `test_smoke_committed_map` exercises the real pipeline (`load_committed` +
`cell_row`) against the hub's confidential instance and the committed k=18 draw; it is guarded
by `os.path.exists` on the instance so it skips cleanly on a machine without that data
(CLAUDE.md: data lives in the hub only, gitignored).
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import borders_report as br                 # noqa: E402
import run_draw                              # noqa: E402
from td import geo                           # noqa: E402

# the descaled instance, the draw and the geo cache are gitignored and hub-only (CLAUDE.md); a
# worktree or a fresh clone carries none of them, so TD_DATA_ROOT points a run there at the
# hub's copy, and every test below skips on os.path.exists(INSTANCE_PATH) when there is none.
DATA_ROOT = os.environ.get("TD_DATA_ROOT", ROOT)
INSTANCE_PATH = os.path.join(DATA_ROOT, "instance_descaled_v2.json.gz")
DRAW_PATH = os.path.join(DATA_ROOT, "battery/results/draw_k18_v2_20260904/k18/draw.csv")
GEO_CACHE = os.path.join(DATA_ROOT, "data/geo")


# ------------------------------------------------------------------------------ owner sets
def test_home_and_owners_plurality_and_fallback():
    """Three states, two districts: a plain plurality home, and the no-home fallback (the
    orphan state's owner set falls to the single district holding most of its mass) --
    `docs/BORDERS_PLAN.md`'s own worked example (state 0 = "NY", 1 = "MA", 2 = "VT")."""
    labels = np.array([0, 0, 1, 1], int)
    state_idx = np.array([0, 1, 1, 2], int)
    M = np.array([10.0, 5.0, 3.0, 1.0], float)
    home, owners = br._home_and_owners(labels, state_idx, M, k=2, n_states=3)

    assert home.tolist() == [0, 1]                     # district 0 -> state 0, district 1 -> state 1
    assert owners[0].tolist() == [True, False]          # O(state 0) = {district 0}
    assert owners[1].tolist() == [False, True]          # O(state 1) = {district 1}
    # state 2 ("VT") has no home district; its whole mass (1.0) sits in district 1, so the
    # fallback hands it that single district rather than leaving it ownerless.
    assert owners[2].tolist() == [False, True]


def test_home_and_owners_unknown_state_excluded():
    """A `-1` (unknown) state contributes no mass to any district's plurality count."""
    labels = np.array([0, 0], int)
    state_idx = np.array([0, -1], int)
    M = np.array([1.0, 1000.0], float)
    home, owners = br._home_and_owners(labels, state_idx, M, k=1, n_states=1)
    assert home.tolist() == [0]                         # the unknown zip's mass never counts
    assert owners[0].tolist() == [True]


def test_owner_sets_falls_back_while_state_borders_is_a_stub():
    """`td.solvers.state_borders.owner_sets` exists but raises `NotImplementedError` (it is
    being written concurrently); `_owner_sets` must still return an answer."""
    labels = np.array([0, 1], int)
    state_idx = np.array([0, 1], int)
    M = np.array([1.0, 1.0], float)
    home, owners = br._owner_sets(labels, state_idx, M, k=2, n_states=2)
    assert home.tolist() == [0, 1]


# ------------------------------------------------------------------------------ naming
def test_label_of_is_district_id_inverse():
    for lab in (0, 1, 6, 17):
        assert br._label_of(run_draw.district_id(lab)) == lab


# ------------------------------------------------------------------------------ writing
def _toy_ctx():
    """The smallest `Ctx` `write_cell` reads: three zips, two states, two districts."""
    import networkx as nx
    from td import instance as descaled

    zips = ["00001", "00002", "00003"]
    states_by_zip = {"00001": "NY", "00002": "NY", "00003": "CA"}
    M_by_zip = {"00001": 1.0, "00002": 2.0, "00003": 3.0}
    G = nx.Graph()
    for z in zips:
        G.add_node(z, cand=(), S={}, M=M_by_zip[z], S_free=0.0, state=states_by_zip[z])
    return br.Ctx(d=descaled.Descaled(G=G), zips=zips, xy=np.zeros((3, 2)),
                 M=np.array([1.0, 2.0, 3.0]),
                 state_idx=np.array([0, 0, 1]), labels0=np.array([0, 0, 1]), k=2,
                 state_list=["CA", "NY"], states_by_zip=states_by_zip, M_by_zip=M_by_zip,
                 missing=[], committed_full={z: "D01" for z in zips[:2]} | {zips[2]: "D02"},
                 home=np.array([1, 0]), owners=np.array([[False, True], [True, False]]),
                 committed_rep_of=None)


def test_write_cell_and_grid_round_trip():
    """`write_cell`/`write_grid` write the files `tools/us_maps.py` and the grid table need,
    on a tiny synthetic instance with no gazetteer or network involved."""
    from td import ziptable

    ctx = _toy_ctx()
    labels = np.array([0, 0, 1])
    completed = run_draw.complete(labels, ctx.zips, ctx.states_by_zip, ctx.missing,
                                  ctx.M_by_zip)
    iterate0 = np.array([0, 1, 1])                       # a different intermediate round

    with tempfile.TemporaryDirectory() as tmp:
        cell_dir = br.write_cell(tmp, "committed", ctx, labels, completed,
                                 iterates=[iterate0])
        draw_csv = os.path.join(cell_dir, "draw.csv")
        assert os.path.exists(draw_csv)
        table = ziptable.read(draw_csv)
        assert ziptable.labels(table) == completed
        assert ziptable.masses(table) == ctx.M_by_zip
        assert [r["state"] for r in table] == ["NY", "NY", "CA"]

        it_csv = os.path.join(cell_dir, "iterates", "00.csv")
        assert os.path.exists(it_csv)

        row = dict(name="committed", spread_rel=0.0, nash=1.23, zips_changed=0)
        br.write_grid(tmp, [row])
        assert os.path.exists(os.path.join(tmp, "grid.csv"))
        with open(os.path.join(tmp, "grid.md"), encoding="utf-8") as fh:
            md = fh.read()
        assert "committed" in md and "nash" in md


def test_write_cell_steps_are_numbered_and_end_on_the_committed_labelling():
    """`steps=` writes one zip table per named step, `NN_completed.csv` last and equal to the
    cell's own `draw.csv` -- the contract `--maps-steps` and the motion page read."""
    from td import ziptable

    ctx = _toy_ctx()
    labels = np.array([0, 0, 1])
    completed = run_draw.complete(labels, ctx.zips, ctx.states_by_zip, ctx.missing,
                                  ctx.M_by_zip)

    with tempfile.TemporaryDirectory() as tmp:
        cell_dir = br.write_cell(tmp, "d0.05", ctx, labels, completed,
                                 steps=[("realise_CA_r0", np.array([0, 1, 1])),
                                        ("realise_CA_r1", np.array([0, 0, 1]))])
        names = sorted(os.listdir(os.path.join(cell_dir, "steps")))
        assert names == ["01_realise_CA_r0.csv", "02_realise_CA_r1.csv", "03_completed.csv"]
        last = ziptable.read(os.path.join(cell_dir, "steps", "03_completed.csv"))
        assert last == ziptable.read(os.path.join(cell_dir, "draw.csv"))
        first = ziptable.read(os.path.join(cell_dir, "steps", "01_realise_CA_r0.csv"))
        assert ziptable.labels(first)["00002"] == "D02"


# ------------------------------------------------------------------------------ the smoke test
def _committed_on(vintage):
    """`br.load_committed` with the gazetteer pinned to one vintage `(url, file name)` pair.

    `zcta_points` reads the module constants at call time, so swapping them around the call is
    enough; they are restored whatever happens.
    """
    saved = (geo.GAZ_URL, geo.GAZ_TXT)
    geo.GAZ_URL, geo.GAZ_TXT = vintage
    try:
        return br.load_committed(INSTANCE_PATH, DRAW_PATH, GEO_CACHE)
    finally:
        geo.GAZ_URL, geo.GAZ_TXT = saved


def test_smoke_committed_map():
    """`load_committed` + `cell_row` on the committed k=18 draw's own labelling must reproduce
    `metrics.json`'s numbers exactly (it is the same completed instance) and change no zip.

    `outside_owner_share` is a new measurement (nothing in `metrics.json` to check it against);
    `docs/BORDERS_PLAN.md` states 9.46% from the same owner-set rule this module implements
    verbatim, but the district-by-state table in that same file (its "district -> states by
    mass share" section) shows New Jersey's owner set holding only D12 -- one district, not the
    ">= 2" the plan's exclusion list later claims -- so the two figures in the plan disagree
    with each other by construction. This measures 9.1-9.2%; the bound below is loose on
    purpose, wide enough to pass either reading and tight enough to catch a broken rule.
    """
    if not os.path.exists(INSTANCE_PATH):
        return

    # The committed draw was solved on the 2020 gazetteer, so its numbers only reproduce against
    # that vintage.  Under the 2025 default the nine zips it has no coordinate for gain one and
    # stop being utility-assigned, which moves 31 zips and takes spread from 1.3684% to 1.2268%.
    ctx = _committed_on(geo.GAZ_VINTAGES["2020"])
    row = br.cell_row(ctx, ctx.labels0, "committed", {"n_fractional": 0})

    committed_nash = 110.88310108262327
    committed_spread = 0.013684389361686315
    committed_stage2 = 95.75519165924106

    assert abs(row["nash"] - committed_nash) <= 1e-6 * abs(committed_nash)
    assert abs(row["spread_rel"] - committed_spread) <= 1e-6 * abs(committed_spread)
    assert abs(row["stage2_value"] - committed_stage2) <= 1e-6 * abs(committed_stage2)
    assert row["zips_changed"] == 0
    assert 0.07 <= row["outside_owner_share"] <= 0.11


# ------------------------------------------------------------------------------ stage-2 weights
def test_cell_row_filler_capture_changes_stage2_value():
    """`filler_capture` scores fillers differently under `"full"` than under the default
    `"theta"` rule (`td.channel.stage2`), so the same labelling's `stage2_value` must move when
    it changes -- these keyword-only weights are not dead parameters."""
    if not os.path.exists(INSTANCE_PATH):
        return

    ctx = br.load_committed(INSTANCE_PATH, DRAW_PATH, GEO_CACHE)
    row_theta = br.cell_row(ctx, ctx.labels0, "committed", {"n_fractional": 0})
    row_full = br.cell_row(ctx, ctx.labels0, "committed", {"n_fractional": 0},
                           filler_capture="full")

    assert row_full["stage2_value"] != row_theta["stage2_value"]


def test_cell_row_echoes_the_weights_it_was_scored_under():
    """The row's `stage2_theta`/`stage2_lam`/`stage2_filler` are whatever was passed to
    `cell_row`, and fall back to the module's own `THETA`/`LAM`/`FILLER_CAPTURE` constants when
    nothing was passed -- the same constants `test_smoke_committed_map`'s regression number was
    computed under."""
    if not os.path.exists(INSTANCE_PATH):
        return

    ctx = br.load_committed(INSTANCE_PATH, DRAW_PATH, GEO_CACHE)

    row_default = br.cell_row(ctx, ctx.labels0, "committed", {"n_fractional": 0})
    assert row_default["stage2_theta"] == br.THETA
    assert row_default["stage2_lam"] == br.LAM
    assert row_default["stage2_filler"] == br.FILLER_CAPTURE

    row_custom = br.cell_row(ctx, ctx.labels0, "committed", {"n_fractional": 0},
                             theta=0.5, lam=0.2, filler_capture="opportunity")
    assert row_custom["stage2_theta"] == 0.5
    assert row_custom["stage2_lam"] == 0.2
    assert row_custom["stage2_filler"] == "opportunity"
