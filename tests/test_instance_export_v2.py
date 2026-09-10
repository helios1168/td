"""
test_instance_export_v2.py -- the exporter's (zip, channel) output, format 2.

Two things are being pinned. First, that a channel-less extract still writes exactly the file
it wrote before channels existed: the committed instance was produced by that path and every
number downstream of it would move if the path did. The golden payload below was captured from
the exporter at `main` 7325737, before any of this was written.

Second, that the national cells of a channelled export are the single-channel export, cell for
cell and id for id. The expanded extract's national rows are the same data as today's whole
extract, so kappa (pinned to the national median), every national m_rel and share, and every
national rep's surrogate id have to come out unchanged. That is what lets tau = 471.21 at
k = 18 and every comparison against the existing instance survive the arrival of WH and FI.
"""
from __future__ import annotations

import contextlib
import csv
import gzip
import importlib.util
import io
import json
import os
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _exporter():
    path = os.path.join(ROOT, "tools", "instance_export", "export_instance.py")
    spec = importlib.util.spec_from_file_location("export_instance", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------ fixtures
# 3 zips x 3 channels, 4 reps.  30003 has no `fi` cell at all; 30002's `fi` cell has
# opportunity but no book (untapped); r_a sells in two channels; r_d sells in none of the
# national rows, so it is one of the reps whose id must be assigned after the national ones.
NAT_SALES = [
    ("30001", "r_a", "FA", 20.0),
    ("30001", "r_b", "FB", 10.0),
    ("30002", "r_b", "FB", 30.0),
    ("30002", "r_c", "FA", 20.0),
    ("30002", "FILLER", "FB", 10.0),
    ("30003", "r_a", "FA", 60.0),
]
OTHER_SALES = [
    ("30001", "wh", "r_a", "FA", 8.0),
    ("30001", "wh", "FILLER", "FB", 4.0),
    ("30001", "fi", "r_c", "FA", 6.0),
    ("30002", "wh", "r_d", "FC", 12.0),
    ("30003", "wh", "r_d", "FC", 4.0),
]
NAT_OPP = [("30001", 100.0), ("30002", 200.0), ("30003", 300.0)]
OTHER_OPP = [("30001", "wh", 40.0), ("30001", "fi", 30.0),
             ("30002", "wh", 60.0), ("30002", "fi", 50.0),
             ("30003", "wh", 20.0)]
EDGES = [("30001", "30002"), ("30002", "30003")]
STATES = [("30001", "GA"), ("30002", "GA"), ("30003", "AL")]

KAPPA = 200.0                       # median of the three national M values


def _csv(tmp, name, header, rows):
    path = os.path.join(tmp, name)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def _v1_inputs(tmp, sales=None):
    """The national rows only, with no channel column: today's extract."""
    return (_csv(tmp, "sales1.csv", ["zip_code", "rep_id", "firm", "sales"],
                 NAT_SALES if sales is None else sales),
            _csv(tmp, "opp1.csv", ["zip_code", "M"], NAT_OPP))


def _v2_inputs(tmp, chan_col="current_channel", sales=None, opp=None):
    """The same national rows plus wh and fi, both tables long by (zip, channel)."""
    rows = [(z, r, f, "national", v) for z, r, f, v in (sales or NAT_SALES)]
    rows += [(z, r, f, c, v) for z, c, r, f, v in OTHER_SALES]
    orows = [(z, "national", m) for z, m in NAT_OPP]
    orows += [(z, c, m) for z, c, m in (opp or OTHER_OPP)]
    return (_csv(tmp, "sales2.csv", ["zip_code", "rep_id", "firm", chan_col, "sales"], rows),
            _csv(tmp, "opp2.csv", ["zip_code", chan_col, "M"], orows))


def _sides(tmp):
    return (_csv(tmp, "edges.csv", ["u", "v"], EDGES),
            _csv(tmp, "states.csv", ["zip_code", "state"], STATES))


def _export(mod, tmp, sales, opp, out="out", extra=()):
    """Run the CLI end to end.  Returns (exit code, payload or None, stdout)."""
    gp, stp = _sides(tmp)
    out_dir = os.path.join(tmp, out)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = mod.main(["export", "--sales", sales, "--opportunity", opp, "--graph", gp,
                       "--states", stp, "--out", out_dir, "--filler-key", "FILLER",
                       "--yes", *extra])
    path = os.path.join(out_dir, "instance_descaled.json.gz")
    payload = None
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
    return rc, payload, buf.getvalue(), path


def _cells(payload):
    """{(zip, channel): row} from a format-2 payload, or {(zip, ""): row} from a format-1."""
    n = payload["nodes"]
    chan = n.get("channel") or [""] * len(n["z"])
    return {(z, c): dict(m_rel=m, share=s, share_free=f, state=st)
            for z, c, m, s, f, st in zip(n["z"], chan, n["m_rel"], n["share"],
                                         n["share_free"], n["state"])}


# ------------------------------------------------------------- the v1 regression
# Captured from tools/instance_export/export_instance.py at main 7325737, the commit the
# committed instance's lineage runs through, before channels were added.
V1_GOLDEN = {
    "edges": {"u": ["30001", "30002"], "v": ["30002", "30003"]},
    "firm": {"R0000": "F0", "R0001": "F1", "R0002": "F0"},
    "format": "td_instance_descaled/1",
    "meta": {"cand_histogram": {"1": 1, "2": 2}, "exporter": "export_instance",
             "graph_hash": "a2f47c99fe6c54aa321cb253d2613aeb7b390c4fa8507ed1a84e6ec1b47ac7db",
             "join_rate": 1.0, "lam": 0.3, "max_candidates": 2, "n_edges": 2,
             "n_filler_keys": 1, "n_filler_rows": 1, "n_reps": 3, "n_sales_rows": 6,
             "n_sales_rows_nonpositive": 0, "n_zips": 3, "repair_added_share": 0.0,
             "scale": "descaled: M/median(positive M); shares dimensionless",
             "scale_stripped": True, "theta": 0.4, "version": "0.1.0",
             "zips_contested": 2, "zips_headroom_repaired": 0, "zips_m_imputed": 0,
             "zips_uncontested": 1, "zips_untapped": 0, "zips_vacant": 0,
             "zips_with_filler": 1},
    "nodes": {"m_rel": [0.5, 1.0, 1.5],
              "share": [{"R0000": 0.2, "R0001": 0.1}, {"R0001": 0.15, "R0002": 0.1},
                        {"R0000": 0.2}],
              "share_free": [0.0, 0.05, 0.0],
              "state": ["GA", "GA", "AL"],
              "z": ["30001", "30002", "30003"]},
}


def test_channelless_extract_writes_the_v1_file_byte_for_byte():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sp, op = _v1_inputs(tmp)
        rc, payload, _, path = _export(mod, tmp, sp, op)
        assert rc == 0
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            text = fh.read()
    expected = json.dumps(V1_GOLDEN, separators=(",", ":"), sort_keys=True)
    assert text == expected, "the channel-less path is no longer what produced the instance"


# ------------------------------------------------------------------ the v2 output
def test_v2_format_string_and_channels_in_file_order():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, _, _ = _export(mod, tmp, *_v2_inputs(tmp))
    assert rc == 0
    assert payload["format"] == "td_instance_descaled/2"
    assert payload["meta"]["channels"] == ["national", "wh", "fi"]
    assert payload["meta"]["kappa_channel"] == "national"
    assert "national" in payload["meta"]["scale"]


def test_v2_nodes_are_long_by_zip_and_channel():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, _, _ = _export(mod, tmp, *_v2_inputs(tmp))
    n = payload["nodes"]
    assert set(n) == {"z", "channel", "m_rel", "share", "share_free", "state"}
    cells = _cells(payload)
    assert set(cells) == {("30001", "national"), ("30001", "wh"), ("30001", "fi"),
                          ("30002", "national"), ("30002", "wh"), ("30002", "fi"),
                          ("30003", "national"), ("30003", "wh")}, \
        "30003 carries no fi row, so it must have no fi cell"
    assert payload["meta"]["n_cells"] == 8
    assert payload["meta"]["n_zips"] == 3
    # the state column repeats with the zip; the graph stays on zips
    assert {c: r["state"] for c, r in cells.items()}[("30003", "wh")] == "AL"
    assert payload["edges"] == {"u": ["30001", "30002"], "v": ["30002", "30003"]}
    assert payload["meta"]["graph_hash"] == V1_GOLDEN["meta"]["graph_hash"], \
        "the graph is over zips and must hash the same as the single-channel export"


def test_v2_share_is_the_cell_fraction_and_kappa_is_the_national_median():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, _, _ = _export(mod, tmp, *_v2_inputs(tmp))
    cells = _cells(payload)
    m_of = {("30001", "national"): 100.0, ("30001", "wh"): 40.0, ("30001", "fi"): 30.0,
            ("30002", "national"): 200.0, ("30002", "wh"): 60.0, ("30002", "fi"): 50.0,
            ("30003", "national"): 300.0, ("30003", "wh"): 20.0}
    for cell, M in m_of.items():
        assert abs(cells[cell]["m_rel"] - M / KAPPA) < 1e-12, cell

    # share is sales / M of that cell, not of the zip
    assert cells[("30001", "national")]["share"] == {"R0000": 0.2, "R0001": 0.1}
    assert cells[("30001", "wh")]["share"] == {"R0000": 8.0 / 40.0}
    assert cells[("30001", "fi")]["share"] == {"R0002": 6.0 / 30.0}
    assert cells[("30002", "wh")]["share"] == {"R0003": 12.0 / 60.0}
    assert cells[("30002", "fi")]["share"] == {}, "opportunity, no book: an untapped cell"
    # the filler's book is free share of its own cell
    assert cells[("30001", "wh")]["share_free"] == 4.0 / 40.0
    assert cells[("30002", "national")]["share_free"] == 10.0 / 200.0
    assert "FILLER" not in json.dumps(payload)


def test_national_cells_reproduce_the_single_channel_export():
    """The invariant the whole track pins on: adding WH and FI moves no national number."""
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc1, v1, _, _ = _export(mod, tmp, *_v1_inputs(tmp), out="one")
        rc2, v2, _, _ = _export(mod, tmp, *_v2_inputs(tmp), out="two")
    assert (rc1, rc2) == (0, 0)
    nat = {z: r for (z, c), r in _cells(v2).items() if c == "national"}
    for (z, _), row in _cells(v1).items():
        assert nat[z]["m_rel"] == row["m_rel"], z
        assert nat[z]["share"] == row["share"], z
        assert nat[z]["share_free"] == row["share_free"], z


def test_surrogate_ids_of_national_reps_are_unchanged_by_the_new_channels():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc1, v1, _, _ = _export(mod, tmp, *_v1_inputs(tmp), out="one")
        rc2, v2, _, _ = _export(mod, tmp, *_v2_inputs(tmp), out="two")
    # every id the single-channel export handed out means the same rep, with the same firm
    for rep, firm in v1["firm"].items():
        assert v2["firm"][rep] == firm, rep
    assert set(v2["firm"]) - set(v1["firm"]) == {"R0003"}, \
        "the WH-only rep must be numbered after the national ones, not among them"
    assert v2["firm"]["R0003"] == "F2"


def test_rep_ids_flag_accepts_the_earlier_export_and_refuses_a_changed_book():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc1, _, _, prior = _export(mod, tmp, *_v1_inputs(tmp), out="one")
        assert rc1 == 0

        rc2, payload, txt, _ = _export(mod, tmp, *_v2_inputs(tmp), out="two",
                                       extra=["--rep-ids", prior])
        assert rc2 == 0 and payload is not None
        assert "3 checked" in txt and "1 new rep" in txt

        # a national row that moved: an id would silently stand for a different book
        moved = [(z, r, f, (v + 5.0 if r == "r_b" else v)) for z, r, f, v in NAT_SALES]
        sp, op = _v2_inputs(tmp, sales=moved)
        rc3, payload3, txt3, path3 = _export(mod, tmp, sp, op, out="three",
                                             extra=["--rep-ids", prior])
        assert rc3 == 2, "a moved national book must stop the export"
        assert payload3 is None and not os.path.exists(path3)
        assert "R0001" in txt3


# ------------------------------------------------------------------------ guards
def test_guard_rejects_a_cell_whose_book_exceeds_its_opportunity():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        # the wh cell at 30001 has M = 40 and one rep selling 8; give it 60 instead
        blown = [(z, c, r, f, (60.0 if (z, c, r) == ("30001", "wh", "r_a") else v))
                 for z, c, r, f, v in OTHER_SALES]
        rows = [(z, r, f, "national", v) for z, r, f, v in NAT_SALES]
        rows += [(z, r, f, c, v) for z, c, r, f, v in blown]
        sp = _csv(tmp, "sales_bad.csv",
                  ["zip_code", "rep_id", "firm", "current_channel", "sales"], rows)
        _, op = _v2_inputs(tmp)
        rc, payload, txt, path = _export(mod, tmp, sp, op)
    assert rc == 3, "validation must catch it before anything is written"
    assert payload is None and not os.path.exists(path)
    assert "30001:wh" in txt

    # and the guard itself, the last line before the bytes go out
    payload = {"nodes": {"z": ["30001"], "channel": ["national"], "m_rel": [1.0],
                         "share": [{"R0000": 1.5}], "share_free": [0.0]},
               "meta": {"kappa_channel": "national"}}
    mod.guard.filler_keys = ()
    try:
        mod.guard(payload)
        raise AssertionError("expected GuardError")
    except mod.GuardError as e:
        assert "not a share" in str(e)


def test_guard_takes_the_median_over_the_kappa_channel_only():
    """A channel a fifth the size of national must not read as an unstripped scale."""
    mod = _exporter()
    payload = {"nodes": {"z": ["30001"] * 5, "channel": ["national"] + ["wh"] * 4,
                         "m_rel": [1.0, 0.2, 0.2, 0.2, 0.2],
                         "share": [{}] * 5, "share_free": [0.0] * 5},
               "meta": {"kappa_channel": "national"}}
    mod.guard.filler_keys = ()
    mod.guard(payload)                       # median over all five rows would be 0.2

    payload["nodes"]["m_rel"][0] = 9000.0     # national itself unstripped: still caught
    try:
        mod.guard(payload)
        raise AssertionError("expected GuardError")
    except mod.GuardError as e:
        assert "scale was not stripped" in str(e) or "currency amount" in str(e)


def test_kappa_channel_in_meta_does_not_trip_the_divisor_guard():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, _, _ = _export(mod, tmp, *_v2_inputs(tmp))
    assert rc == 0
    assert payload["meta"]["kappa_channel"] == "national"
    assert "kappa" not in {k for k in payload["meta"] if k != "kappa_channel"}


# ------------------------------------------------------------------ input handling
def test_channel_column_spellings_are_all_accepted():
    mod = _exporter()
    for spelling in ("current_channel", "current channel", "channel"):
        with tempfile.TemporaryDirectory() as tmp:
            rc, payload, _, _ = _export(mod, tmp, *_v2_inputs(tmp, chan_col=spelling))
        assert rc == 0, spelling
        assert payload["meta"]["channels"] == ["national", "wh", "fi"], spelling


def test_a_channel_column_on_one_table_only_is_refused():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sp, _ = _v2_inputs(tmp)
        _, op = _v1_inputs(tmp)
        rc, payload, txt, _ = _export(mod, tmp, sp, op)
    assert rc == 4 and payload is None
    assert "exactly one of the two tables" in txt


def test_a_blank_channel_value_is_refused():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        orows = [(z, "", m) for z, m in NAT_OPP]
        op = _csv(tmp, "opp_blank.csv", ["zip_code", "current_channel", "M"], orows)
        sp, _ = _v2_inputs(tmp)
        rc, payload, txt, _ = _export(mod, tmp, sp, op)
    assert rc == 4 and payload is None
    assert "empty" in txt


def test_no_national_rows_is_refused_because_kappa_is_pinned_to_them():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rows = [(z, r, f, "wh", v) for z, r, f, v in NAT_SALES]
        orows = [(z, "wh", m) for z, m in NAT_OPP]
        sp = _csv(tmp, "sales_wh.csv",
                  ["zip_code", "rep_id", "firm", "current_channel", "sales"], rows)
        op = _csv(tmp, "opp_wh.csv", ["zip_code", "current_channel", "M"], orows)
        rc, payload, txt, _ = _export(mod, tmp, sp, op)
    assert rc == 4 and payload is None
    assert "national" in txt


# ------------------------------------------------------------------- the loader
def test_v2_round_trips_through_the_loader():
    """Skips until A1's format-2 loader lands."""
    from td import instance as descaled
    if not hasattr(descaled, "FORMAT_V2"):
        return
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, _, path = _export(mod, tmp, *_v2_inputs(tmp))
        assert rc == 0
        d = descaled.load_descaled(path)
    assert d.channels == ("national", "wh", "fi")
    assert set(d.G) == {"30001", "30002", "30003"}
    # totals are the sum over the zip's cells, in descaled units
    assert abs(d.G.nodes["30001"]["M"] - (100.0 + 40.0 + 30.0) / KAPPA) < 1e-9
    assert abs(d.G.nodes["30003"]["M"] - (300.0 + 20.0) / KAPPA) < 1e-9
    # S_i(z) = share * m_rel, summed over channels: r_a sells 20 national and 8 wh at 30001
    assert abs(d.G.nodes["30001"]["S"]["R0000"] - (20.0 + 8.0) / KAPPA) < 1e-9
    assert abs(d.G.nodes["30001"]["S_free"] - (0.0 + 4.0) / KAPPA) < 1e-9
    assert d.G.nodes["30002"]["cand"] == ("R0001", "R0002", "R0003")
