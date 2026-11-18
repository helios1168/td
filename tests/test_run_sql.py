"""
test_run_sql.py -- `tools/snowflake/run_sql.py`: a SQL file's last result, as Snowsight's Run All shows it.

A fake connector: the last statement with rows is what shows and what lands in last.csv, the snapshot stops at ROWS rows,
and a failing statement prints which one failed and returns 1.
"""
from __future__ import annotations

import contextlib
import csv
import io
import os
import sys
import tempfile
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "snowflake"))
import run_sql  # noqa: E402


class Err(Exception):
    pass


SEEN = []


def fake_connector(results):
    """Each item: rows (a cursor with one column X), None (a cursor with no description) or Err (raised)."""
    def stream(f):
        SEEN.append(f.getvalue())
        for r in results:
            if r is Err:
                raise Err("SQL compilation error: bad")
            yield types.SimpleNamespace(description=[("X",)] if r is not None else None, fetchall=lambda r=r: r,
                                        sfqid=f"0000000{len(r) if r else 0}-0000-0000-0000-000000000000")
    conn = types.SimpleNamespace(execute_stream=stream)
    return types.SimpleNamespace(connect=lambda **kw: contextlib.nullcontext(conn), errors=types.SimpleNamespace(Error=Err))


def run(results):
    mod = fake_connector(results)
    saved = {k: sys.modules.get(k) for k in ("snowflake", "snowflake.connector")}
    sys.modules.update({"snowflake": types.SimpleNamespace(connector=mod), "snowflake.connector": mod})
    try:
        return _run()
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def _run():
    with tempfile.TemporaryDirectory() as d:
        run_sql.OUT = os.path.join(d, "safe", "last.csv")
        run_sql.URL = os.path.join(d, "none.txt")
        sql = os.path.join(d, "q.sql")
        open(sql, "w").write("select 1")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_sql.main(sql)
        rows = list(csv.reader(open(run_sql.OUT))) if os.path.exists(run_sql.OUT) else None
    return code, buf.getvalue(), rows


def test_the_last_result_shows_and_is_saved_whole():
    code, out, rows = run([[(1,)], None, [(i,) for i in range(run_sql.ROWS + 5)]])
    assert code == 0
    assert rows == [["X"]] + [[str(i)] for i in range(run_sql.ROWS + 5)]
    assert f"{run_sql.ROWS + 5} rows x 1 columns, first {run_sql.ROWS} shown. 3 statements" in out
    assert str(run_sql.ROWS - 1) in out and f" {run_sql.ROWS + 4}\n" not in out


def test_a_failing_statement_says_which_and_returns_1():
    code, out, rows = run([[(1,)], Err])
    assert code == 1 and rows is None
    assert "\nERROR in statement 2 (1 ran):" in out and "bad" in out


def test_the_saved_snowsight_url_gets_the_new_query_id():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "u.txt")
        assert run_sql.snowsight_url("x", p) is None
        open(p, "w").write("https://app.example/#/compute/history/queries/01bc2d3e-0000-4a5b-0000-abcdefabcdef/detail\n")
        new = "01ffffff-1111-2222-3333-444444444444"
        assert run_sql.snowsight_url(new, p) == f"https://app.example/#/compute/history/queries/{new}/detail"
        open(p, "w").write("https://app.example/#/compute/history")
        try:
            run_sql.snowsight_url(new, p)
            raise AssertionError("a URL with no query ID must refuse")
        except SystemExit as e:
            assert "no query ID" in str(e)


def test_then_runs_the_named_file_after_in_one_session():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "tools"))
        open(os.path.join(d, "tools", "after.sql"), "w").write("select 'after'")
        root, run_sql.ROOT = run_sql.ROOT, d
        try:
            SEEN.clear()
            fake = fake_connector([[(1,)]])
            saved = {k: sys.modules.get(k) for k in ("snowflake", "snowflake.connector")}
            sys.modules.update({"snowflake": types.SimpleNamespace(connector=fake), "snowflake.connector": fake})
            run_sql.OUT, run_sql.URL = os.path.join(d, "last.csv"), os.path.join(d, "none.txt")
            sql = os.path.join(d, "fix.sql")
            open(sql, "w").write("update x\n--then tools/after.sql\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                run_sql.main(sql)
        finally:
            run_sql.ROOT = root
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        assert SEEN == ["update x\n--then tools/after.sql\n\nselect 'after'"], SEEN
        assert "then tools/after.sql" in buf.getvalue()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
