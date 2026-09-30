"""
test_export_instance.py -- `export/export_instance.py`, the work-machine exporter.

Format 3 (td#61): the node table is long by (zip, channel) cell for any channel values, one
descaling divisor (the median positive cell M) serves every channel, `channels.json` lists
the channels for the owner to review, and there is no graph and no state column. The
fixture is a synthetic seven-channel extract; every guard is checked against bad input.
"""
from __future__ import annotations

import ast
import contextlib
import csv
import gzip
import importlib.util
import io
import json
import os
import statistics
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
EXPORTER = os.path.join(ROOT, "export", "export_instance.py")


def _exporter():
    spec = importlib.util.spec_from_file_location("export_instance", EXPORTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------ fixtures
# 3 zips x 7 channels. The opportunity table spells each channel one way and the sales table
# another; both must normalise to the same name. (10002, wifi) has zero M and no book, so it
# is no cell; (10003, bank_direct) has no row at all.
ZIPS = ("10001", "10002", "10003")
OPP_SPELLING = ("National", "Wells (WH)", "Wells (FI)", "WH", "FI", "WIFI", "Bank/Direct")
CHANNELS = ["national", "wells_wh", "wells_fi", "wh", "fi", "wifi", "bank_direct"]


def _m(i, j):
    return 10.0 * (j + 1) * (i + 1)


OPP = [(z, OPP_SPELLING[j], 0.0 if (z, j) == ("10002", 5) else _m(i, j))
       for i, z in enumerate(ZIPS) for j in range(7) if (z, j) != ("10003", 6)]
M_OF = {(z, channel): m for z, spelled, m in OPP
        for channel in [CHANNELS[OPP_SPELLING.index(spelled)]] if m > 0}
KAPPA = statistics.median(M_OF.values())    # one divisor: the median positive cell M

NAT_SALES = [                               # (zip, rep, firm, sales), national only
    ("10001", "r_a", "FA", 4.0),
    ("10001", "r_b", "FB", 2.0),
    ("10002", "r_b", "FB", 6.0),
    ("10002", "r_c", "FA", 4.0),
    ("10002", "FILLER", "FB", 2.0),
    ("10003", "r_a", "FA", 12.0),
]
OTHER_SALES = [                             # (zip, channel as the sales table spells it, ...)
    ("10001", "WELLS-WH", "r_d", "FC", 5.0),
    ("10002", "wells fi", "r_a", "FA", 9.0),
    ("10003", "wh", "r_e", "FD", 24.0),
    ("10001", "fi", "r_d", "FC", 10.0),
    ("10003", "wifi", "r_c", "FA", 45.0),
    ("10002", "bank direct", "r_e", "FD", 28.0),
    ("10001", "Bank/Direct", "FILLER", "FB", 7.0),
]
SALES = [(z, r, f, "NATIONAL", v) for z, r, f, v in NAT_SALES]
SALES += [(z, r, f, c, v) for z, c, r, f, v in OTHER_SALES]
SALES_HEADER = ["zip_code", "rep_id", "firm", "current_channel", "sales"]


def _csv(tmp, name, header, rows):
    path = os.path.join(tmp, name)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def _inputs(tmp, sales=None, opp=None, chan_col="current_channel"):
    header = ["zip_code", "rep_id", "firm", chan_col, "sales"]
    return (_csv(tmp, "sales.csv", header, SALES if sales is None else sales),
            _csv(tmp, "opp.csv", ["zip_code", chan_col, "M"], OPP if opp is None else opp))


def _nat_inputs(tmp):
    """The national rows only, with no channel column."""
    return (_csv(tmp, "sales1.csv", ["zip_code", "rep_id", "firm", "sales"], NAT_SALES),
            _csv(tmp, "opp1.csv", ["zip_code", "M"],
                 [(z, m) for (z, c), m in M_OF.items() if c == "national"]))


def _run(mod, tmp, sales, opp, out="out", cmd="export", extra=()):
    """Run the CLI end to end.  Returns (exit code, payload, channels doc, output, out dir)."""
    out_dir = os.path.join(tmp, out)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = mod.main([cmd, "--sales", sales, "--opportunity", opp, "--out", out_dir,
                       "--filler-key", "FILLER", "--yes", *extra])
    payload = chans = None
    path = os.path.join(out_dir, "instance_descaled.json.gz")
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
    if os.path.exists(os.path.join(out_dir, "channels.json")):
        with open(os.path.join(out_dir, "channels.json"), encoding="utf-8") as fh:
            chans = json.load(fh)
    return rc, payload, chans, buf.getvalue(), out_dir


def _cells(payload):
    n = payload["nodes"]
    return {(z, c): dict(m_rel=m, share=s, share_free=f)
            for z, c, m, s, f in zip(n["z"], n["channel"], n["m_rel"], n["share"],
                                     n["share_free"])}


def _refused(fn, exc, *words):
    try:
        fn()
    except exc as e:
        for w in words:
            assert w in str(e), (w, str(e))
        return
    raise AssertionError(f"expected {exc.__name__}")


# ------------------------------------------------------------------- the v3 output
def test_seven_channel_extract_writes_format_3_nodes_and_meta():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, chans, txt, _ = _run(mod, tmp, *_inputs(tmp))
    assert rc == 0, txt
    assert payload["format"] == "td_instance_descaled/3"
    assert set(payload) == {"format", "nodes", "firm", "meta"}, "no edges leave any more"
    assert set(payload["nodes"]) == {"z", "channel", "m_rel", "share", "share_free"}
    meta = payload["meta"]
    assert meta["channels"] == CHANNELS, "channels in the order the opportunity table names them"
    assert meta["n_cells"] == 19 and meta["n_zips"] == 3
    assert not {"graph_hash", "n_edges", "kappa_channel", "channel_groups"} & set(meta)
    assert set(_cells(payload)) == set(M_OF)
    assert "10002:wifi" not in txt and chans is not None


def test_one_divisor_is_the_median_positive_cell_m_over_all_channels():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp))
    assert rc == 0, txt
    cells = _cells(payload)
    for cell, M in M_OF.items():
        assert abs(cells[cell]["m_rel"] - M / KAPPA) <= 1e-5 * M / KAPPA, cell
    assert "kappa" not in json.dumps(payload["meta"])
    assert "all channels" in payload["meta"]["scale"]


def test_share_is_the_cell_fraction_and_filler_book_is_free_share():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, chans, _, _ = _run(mod, tmp, *_inputs(tmp))
    cells = _cells(payload)
    assert cells[("10001", "national")]["share"] == {"R0002": 0.4, "R0004": 0.2}
    assert cells[("10001", "wells_wh")]["share"] == {"R0003": 5.0 / 20.0}
    assert cells[("10003", "wifi")]["share"] == {"R0001": 45.0 / 180.0}
    assert cells[("10002", "wh")]["share"] == {}, "opportunity, no book: an untapped cell"
    assert cells[("10002", "national")]["share_free"] == 2.0 / 20.0
    assert cells[("10001", "bank_direct")]["share_free"] == 7.0 / 70.0
    assert "FILLER" not in json.dumps(payload) and "FILLER" not in json.dumps(chans)


def test_channels_json_lists_every_channel_with_spellings_and_counts():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, _, chans, _, _ = _run(mod, tmp, *_inputs(tmp))
    assert rc == 0
    rows = {c["channel"]: c for c in chans["channels"]}
    assert [c["channel"] for c in chans["channels"]] == CHANNELS
    assert rows["national"]["spellings"] == ["NATIONAL", "National"]
    assert rows["wells_wh"]["spellings"] == ["WELLS-WH", "Wells (WH)"]
    assert rows["bank_direct"]["spellings"] == ["Bank/Direct", "bank direct"]
    assert rows["national"]["sales_rows"] == 6 and rows["bank_direct"]["sales_rows"] == 2
    assert rows["wifi"]["cells"] == 2 and rows["wifi"]["zips"] == 2
    assert rows["bank_direct"]["cells"] == 2
    total = sum(M_OF.values())
    for name, row in rows.items():
        want = sum(m for (z, c), m in M_OF.items() if c == name) / total
        assert abs(row["opportunity_share"] - want) <= 1e-5 * want, name
    assert "kappa" not in json.dumps(chans)


def test_rep_books_stay_with_surrogate_ids_ranked_by_total_book():
    """With no reference channel the ids rank by total book across channels:
    r_e 52 > r_c 49 > r_a 25 > r_d 15 > r_b 8 (sales units; m_rel*share is S/kappa)."""
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, _, _, _ = _run(mod, tmp, *_inputs(tmp))
    assert rc == 0
    assert payload["firm"] == {"R0000": "F3", "R0001": "F0", "R0002": "F0", "R0003": "F2",
                               "R0004": "F1"}
    book = {}
    for (z, c), row in _cells(payload).items():
        for rep, s in row["share"].items():
            book[rep] = book.get(rep, 0.0) + s * M_OF[(z, c)]
    want = {"R0000": 52.0, "R0001": 49.0, "R0002": 25.0, "R0003": 15.0, "R0004": 8.0}
    for rep, v in want.items():
        assert abs(book[rep] - v) < 1e-6, rep


def test_channelless_extract_is_one_national_channel():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, chans, txt, _ = _run(mod, tmp, *_nat_inputs(tmp))
    assert rc == 0, txt
    assert payload["format"] == "td_instance_descaled/3"
    assert payload["meta"]["channels"] == ["national"]
    assert set(payload["nodes"]["channel"]) == {"national"}
    assert payload["nodes"]["m_rel"] == [0.5, 1.0, 1.5], "kappa is the national median, 20"
    assert chans["channels"][0]["spellings"] == []


def test_validate_prints_the_channel_table_and_writes_nothing():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        rc, payload, chans, txt, out_dir = _run(mod, tmp, *_inputs(tmp), cmd="validate")
        assert not os.path.exists(out_dir)
    assert rc == 0 and payload is None and chans is None
    assert "validation: clean" in txt
    for name in CHANNELS:
        assert name in txt, name


def test_graph_and_states_flags_are_gone():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sp, op = _inputs(tmp)
        edges = _csv(tmp, "edges.csv", ["u", "v"], [("10001", "10002")])
        for flag in ("--graph", "--states"):
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    mod.main(["validate", "--sales", sp, "--opportunity", op, flag, edges])
            except SystemExit as e:
                assert e.code == 2 and "unrecognized arguments" in buf.getvalue(), flag
            else:
                raise AssertionError(f"{flag} is still accepted")


def test_exporter_imports_only_the_standard_library():
    with open(EXPORTER, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    names = set()
    for node in ast.walk(tree):                         # nested imports count too
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "no relative imports: the exporter is one file"
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__":
            raise AssertionError("no dynamic imports")
    assert names, "the walk found no imports at all"
    assert names <= set(sys.stdlib_module_names), sorted(names - set(sys.stdlib_module_names))


def test_rep_map_writes_the_surrogate_to_raw_id_map_only_when_asked():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "rep_map.csv")
        rc, _, _, _, _ = _run(mod, tmp, *_inputs(tmp), out="one")
        assert rc == 0 and not os.path.exists(path)
        rc2, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp), out="two",
                                       extra=["--rep-map", path])
        assert rc2 == 0 and "5 rep(s)" in txt
        with open(path, newline="") as fh:
            rows = list(csv.DictReader(fh))
    assert [r["rep_surrogate"] for r in rows] == ["R0000", "R0001", "R0002", "R0003", "R0004"]
    assert [r["rep_id"] for r in rows] == ["r_e", "r_c", "r_a", "r_d", "r_b"]
    for r in rows:
        assert payload["firm"][r["rep_surrogate"]] == r["firm_surrogate"]


# ------------------------------------------------------------------------ --rep-ids
def _prior_single_channel(tmp):
    """An earlier single-channel export: the national rows, nodes without a channel column."""
    mod = _exporter()
    rc, payload, _, txt, _ = _run(mod, tmp, *_nat_inputs(tmp), out="prior")
    assert rc == 0, txt
    del payload["nodes"]["channel"]
    payload["format"] = "td_instance_descaled/1"
    path = os.path.join(tmp, "prior.json.gz")
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)
    return path


def test_rep_ids_ranks_the_named_channel_first_and_accepts_the_same_book():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        prior = _prior_single_channel(tmp)
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp), extra=[
            "--rep-ids", prior, "--rep-ids-channel", "National"])
    assert rc == 0, txt
    assert "3 checked" in txt and "2 new rep" in txt
    # national reps keep their ids (r_a, r_b, r_c); r_e and r_d follow by total book
    assert _cells(payload)[("10001", "national")]["share"] == {"R0000": 0.4, "R0001": 0.2}
    assert _cells(payload)[("10003", "wh")]["share"] == {"R0003": 0.2}


def test_rep_ids_refuses_a_moved_book_and_writes_nothing():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        prior = _prior_single_channel(tmp)
        moved = [(z, r, f, c, v + 1.0 if (r, c) == ("r_b", "NATIONAL") else v)
                 for z, r, f, c, v in SALES]
        rc, payload, chans, txt, _ = _run(mod, tmp, *_inputs(tmp, sales=moved), extra=[
            "--rep-ids", prior, "--rep-ids-channel", "national"])
    assert rc == 2 and payload is None and chans is None
    assert "R0001" in txt and "nothing written" in txt


def test_rep_ids_needs_a_known_channel_and_a_single_channel_prior():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        prior = _prior_single_channel(tmp)
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp), extra=["--rep-ids", prior])
        assert rc == 4 and payload is None and "--rep-ids-channel" in txt
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp), extra=[
            "--rep-ids", prior, "--rep-ids-channel", "mystery"])
        assert rc == 4 and payload is None and "not a channel" in txt
        channelled = os.path.join(tmp, "prior", "instance_descaled.json.gz")
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp), out="three", extra=[
            "--rep-ids", channelled, "--rep-ids-channel", "national"])
        assert rc == 4 and payload is None and "single-channel" in txt


# ------------------------------------------------------------------------ guards
def test_join_floor_refuses_unjoined_sales_until_lowered():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        stray = SALES + [("10003", "r_a", "FA", "bank direct", 5.0)]   # no such cell
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp, sales=stray))
        assert rc == 4 and payload is None
        assert "joined to an opportunity cell" in txt and "10003:bank_direct" in txt
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp, sales=stray), out="low",
                                      extra=["--join-floor", "0.9"])
    assert rc == 0 and payload is not None, txt


def test_a_share_outside_0_1_is_refused():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        blown = [(z, r, f, c, 60.0 if (z, c) == ("10001", "WELLS-WH") else v)
                 for z, r, f, c, v in SALES]
        rc, payload, chans, txt, _ = _run(mod, tmp, *_inputs(tmp, sales=blown))
    assert rc == 3 and payload is None and chans is None
    assert "outside [0,1]" in txt and "10001:wells_wh" in txt

    mod.guard.filler_keys = ()
    payload = {"nodes": {"z": ["10001"], "channel": ["wh"], "m_rel": [1.0],
                         "share": [{"R0000": 1.5}], "share_free": [0.0]}, "meta": {}}
    _refused(lambda: mod.guard(payload), mod.GuardError, "not a share")
    payload["nodes"]["share"] = [{}]
    payload["nodes"]["share_free"] = [-0.1]
    _refused(lambda: mod.guard(payload), mod.GuardError, "not a share")


def test_pointwise_headroom_violation_is_refused():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        # fi at 10001 has M 50: shares 0.2, 0.9 and 0.8 are each in [0,1], but
        # 0.9 + 0.4 * (1.9 - 0.9) = 1.3 > 1
        crowded = SALES + [("10001", "r_a", "FA", "fi", 45.0),
                           ("10001", "r_c", "FA", "fi", 40.0)]
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp, sales=crowded))
    assert rc == 3 and payload is None
    assert "headroom" in txt


def test_guard_refuses_an_unstripped_scale_a_currency_amount_or_a_negative_mass():
    mod = _exporter()
    mod.guard.filler_keys = ()

    def payload(ms):
        return {"nodes": {"z": ["10001"] * len(ms), "channel": ["wh"] * len(ms),
                          "m_rel": ms, "share": [{}] * len(ms),
                          "share_free": [0.0] * len(ms)}, "meta": {}}

    mod.guard(payload([0.2, 1.0, 3.0]))
    _refused(lambda: mod.guard(payload([900.0, 1000.0, 1100.0])), mod.GuardError,
             "scale was not stripped")
    _refused(lambda: mod.guard(payload([0.5, 1.0, 2e4])), mod.GuardError, "currency amount")
    _refused(lambda: mod.guard(payload([0.5, 1.0, 1.5, -0.1])), mod.GuardError, "negative")
    _refused(lambda: mod.guard(payload([])), mod.GuardError, "no nodes")


def test_guard_refuses_the_divisor_in_meta_and_the_filler_name_anywhere():
    mod = _exporter()
    p = {"nodes": {"z": ["10001"], "channel": ["wh"], "m_rel": [1.0], "share": [{}],
                   "share_free": [0.0]}, "meta": {"kappa": 123.0}}
    mod.guard.filler_keys = ()
    _refused(lambda: mod.guard(p), mod.GuardError, "divisor")
    p["meta"] = {"counts": {"Kappa_value": 1.0}}
    _refused(lambda: mod.guard(p), mod.GuardError, "divisor")
    p["meta"] = {"channels": ["kappa"]}
    mod.guard(p)                            # a channel named kappa is a value, not the divisor
    p["meta"] = {"note": "FILLER"}
    mod.guard.filler_keys = ("FILLER",)
    _refused(lambda: mod.guard(p), mod.GuardError, "filler key")
    p["meta"] = {}
    doc = {"channels": [{"channel": "filler_wh", "spellings": ["FILLER WH"]}]}
    _refused(lambda: mod.guard(p, doc), mod.GuardError, "filler key", "channels.json")
    mod.guard.filler_keys = ()
    _refused(lambda: mod.guard(p, {"kappa": 1.0}), mod.GuardError, "divisor")


def test_the_filler_name_in_a_channel_spelling_is_refused_and_nothing_is_written():
    """#72 A1: the raw spellings go to channels.json, so the sentinel is checked there too."""
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sales = SALES + [("10001", "r_a", "FA", "FILLER WH", 1.0)]
        opp = OPP + [("10001", "FILLER WH", 10.0)]
        rc, payload, chans, txt, out_dir = _run(mod, tmp, *_inputs(tmp, sales=sales, opp=opp))
        assert not os.path.exists(out_dir), "the guard runs before the output directory exists"
    assert rc == 2 and payload is None and chans is None, txt
    assert "channels.json" in txt and "nothing written" in txt


def test_a_channel_named_kappa_exports():
    """#72 A4: the divisor guard looks for a kappa field, not the word in a channel name."""
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sales = [(z, r, f, "Kappa", v) for z, r, f, v in NAT_SALES]
        opp = [(z, "Kappa", m) for (z, c), m in M_OF.items() if c == "national"]
        rc, payload, chans, txt, _ = _run(mod, tmp, *_inputs(tmp, sales=sales, opp=opp))
    assert rc == 0, txt
    assert payload["meta"]["channels"] == ["kappa"]
    assert [c["channel"] for c in chans["channels"]] == ["kappa"]


def test_negative_or_non_finite_opportunity_is_refused_not_dropped():
    """#72 A3: an untapped cell with M -5, NaN or infinity used to vanish with exit 0."""
    mod = _exporter()
    for bad in ("-5", "NaN", "inf", "-inf"):
        with tempfile.TemporaryDirectory() as tmp:
            opp = OPP + [("10004", "National", bad)]
            rc, payload, chans, txt, _ = _run(mod, tmp, *_inputs(tmp, opp=opp))
        assert rc == 4 and payload is None and chans is None, (bad, txt)
        assert "10004:national" in txt, bad
        assert ("negative" if bad == "-5" else "not a finite number") in txt, bad


def test_impute_missing_m_still_replaces_a_negative_m_under_book():
    """The declared repair runs before the negative-total check: a cell with book and M -5
    gets M = its book, and only a negative cell left over stops the export."""
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        opp = [r for r in OPP if (r[0], r[1]) != ("10003", "WH")] + [("10003", "WH", -5.0)]
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp, opp=opp))
        assert rc == 4 and payload is None and "negative" in txt
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp, opp=opp), out="imputed",
                                      extra=["--impute-missing-m"])
    assert rc == 0, txt
    assert _cells(payload)[("10003", "wh")]["share"] == {"R0000": 1.0}
    assert payload["meta"]["zips_m_imputed"] == 1


def test_a_sales_only_channel_imputed_is_listed_and_loads():
    """#72 A2: CSV to export to td/data.py. A channel that --impute-missing-m brings in from
    sales alone joins the channel list after the opportunity table's, so the loader takes it."""
    from td import data
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sales = SALES + [("10002", "r_d", "FC", "Sales Only", 3.0),
                         ("10001", "r_d", "FC", "sales-only", 2.0)]
        rc, payload, chans, txt, out_dir = _run(mod, tmp, *_inputs(tmp, sales=sales),
                                                extra=["--impute-missing-m"])
        assert rc == 0, txt
        assert payload["meta"]["channels"] == CHANNELS + ["sales_only"]
        rows = {c["channel"]: c for c in chans["channels"]}
        assert [c["channel"] for c in chans["channels"]] == CHANNELS + ["sales_only"]
        assert rows["sales_only"]["spellings"] == ["Sales Only", "sales-only"]
        assert rows["sales_only"]["cells"] == 2 and rows["sales_only"]["sales_rows"] == 2
        ext = data.load(os.path.join(out_dir, "instance_descaled.json.gz"))
    assert list(ext.channels) == CHANNELS + ["sales_only"]
    assert "sales_only" in set(ext.channel)


# ------------------------------------------------------------------ input handling
def test_channel_column_spellings_are_all_accepted():
    mod = _exporter()
    for spelling in ("current_channel", "current channel", "channel"):
        with tempfile.TemporaryDirectory() as tmp:
            rc, payload, _, _, _ = _run(mod, tmp, *_inputs(tmp, chan_col=spelling))
        assert rc == 0, spelling
        assert payload["meta"]["channels"] == CHANNELS, spelling


def test_channel_name_normalises_any_value():
    c = _exporter().channel_name
    assert c("Wells (WH)") == c("WELLS-WH") == c("wells wh") == "wells_wh"
    assert c(" Bank/Direct ") == "bank_direct"
    assert c("wells.fi") == "wells_fi"
    assert c("Mystery Channel") == "mystery_channel"
    assert c("()") == ""


def test_a_channel_column_on_one_table_only_is_refused():
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        sp, _ = _inputs(tmp)
        _, op = _nat_inputs(tmp)
        rc, payload, _, txt, _ = _run(mod, tmp, sp, op)
    assert rc == 4 and payload is None
    assert "exactly one of the two tables" in txt


def test_a_blank_channel_value_is_refused():
    mod = _exporter()
    for blank in ("", "  ", "()"):
        with tempfile.TemporaryDirectory() as tmp:
            opp = OPP + [("10001", blank, 5.0)]
            rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp, opp=opp))
        assert rc == 4 and payload is None, repr(blank)
        assert "empty" in txt, repr(blank)


def test_channelled_opportunity_sums_across_the_rows_of_a_cell():
    """The channelled extract carries a cell's M once across its rows (parts, or one row with
    M and duplicates at 0); the cell's M is the sum. The channel-less extract repeats M on
    every row of a zip, so two different positive values there are a bad merge."""
    mod = _exporter()
    with tempfile.TemporaryDirectory() as tmp:
        split = [r for r in OPP if (r[0], r[1]) != ("10001", "National")]
        split += [("10001", "National", 6.0), ("10001", "national", 4.0),
                  ("10001", "WH", 0.0)]
        rc, payload, _, txt, _ = _run(mod, tmp, *_inputs(tmp, opp=split))
        assert rc == 0, txt
        cells = _cells(payload)
        assert abs(cells[("10001", "national")]["m_rel"] - 10.0 / KAPPA) < 1e-6
        assert abs(cells[("10001", "wh")]["m_rel"] - 40.0 / KAPPA) < 1e-6

        sp = _csv(tmp, "s1.csv", ["zip_code", "rep_id", "firm", "sales"], NAT_SALES)
        op = _csv(tmp, "o1.csv", ["zip_code", "M"],
                  [("10001", 6.0), ("10001", 4.0), ("10002", 20.0), ("10003", 30.0)])
        rc, payload, _, txt, _ = _run(mod, tmp, sp, op, out="one")
    assert rc == 4 and payload is None
    assert "two different opportunity values" in txt
