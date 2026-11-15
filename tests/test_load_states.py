"""tools/snowflake/load_states.py against a stand-in connection: the statements it sends, in order, and that a
table with rows is never touched.  Snowflake itself is not reached."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("load_states", ROOT / "tools" / "snowflake" / "load_states.py")
ls = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ls)


class Conn:
    def __init__(self, rows_before):
        self.sent, self.rows_before, self.last = [], rows_before, None

    def cursor(self):
        return self

    def execute(self, sql):
        self.sent.append(sql)
        self.last = sql
        return self

    def fetchone(self):
        return (56, 0) if "ST_ISVALID" in self.last else (self.rows_before,)

    def fetchall(self):
        return [("ok",)]


def test_an_empty_table_is_created_staged_copied_and_counted():
    c = Conn(0)
    assert ls.load(c, "CB_2025_US_STATE", "/tmp/x y/states.csv") == (56, 0)
    assert [s.split()[0] for s in c.sent] == ["CREATE", "SELECT", "PUT", "COPY", "SELECT"]
    assert "CREATE TABLE IF NOT EXISTS" in c.sent[0] and "REPLACE" not in " ".join(c.sent)
    assert c.sent[2].startswith("PUT 'file:///") and c.sent[2].endswith("x y/states.csv' @%CB_2025_US_STATE OVERWRITE = TRUE")


def test_a_table_with_rows_is_left_alone():
    c = Conn(56)
    assert ls.load(c, "CB_2025_US_STATE", "/tmp/states.csv") is None
    assert [s.split()[0] for s in c.sent] == ["CREATE", "SELECT"]


def test_a_table_name_that_is_not_plain_is_refused():
    try:
        ls.load(Conn(0), "t; DROP TABLE x", "/tmp/states.csv")
    except ValueError:
        return
    raise AssertionError("accepted")


def test_the_csv_it_loads_is_the_56_states():
    with open(ls.CSV, encoding="utf-8") as fh:
        assert sum(1 for _ in fh) == ls.N_STATES + 1
