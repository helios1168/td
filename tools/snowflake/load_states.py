"""load_states.py -- geo/cb_2025_us_state_500k.csv into a Snowflake table, GEO_BOUNDARY as GEOGRAPHY.

Run it on the machine that reaches Snowflake (pip install snowflake-connector-python):

    python load_states.py --account <account> --user <user>          # signs in through the browser
    python load_states.py --connection <name in connections.toml>

The role, database and schema are the session header's.  The table (default CB_2025_US_STATE) is created if it is
not there, the CSV goes to the table's own stage (PUT, no named stage needed) and COPY INTO loads it.  A table that
already has rows is left alone: drop it yourself to load again.  Exits 1 unless 56 valid shapes are in.
Snowflake pages read 2026-11-15: .../sql-reference/sql/put (table stage, quoted file URI, Windows forward slashes),
.../python-connector/python-connector-example (PUT then COPY INTO), .../python-connector-api (authenticator).
"""
import argparse
import pathlib
import re
import sys

ROLE, DATABASE, SCHEMA = "rl_ssdb_Integration_Lr_Strategy_Rw", "ssdb_Integration", "lr_strategy"
CSV = pathlib.Path(__file__).resolve().parent / "geo" / "cb_2025_us_state_500k.csv"
N_STATES = 56


def load(conn, table, csv_path):
    """Create, stage, copy and count.  Returns (rows, invalid or missing shapes), or None when the table has rows."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", table):
        raise ValueError(f"not a plain table name: {table!r}")
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table} (GEO_ID VARCHAR, FULLY_QUALIFIED_ID VARCHAR, GEO_NAME VARCHAR, "
                "STUSPS VARCHAR, GEO_BOUNDARY GEOGRAPHY)")
    if cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
        return None
    uri = "file://" + pathlib.Path(csv_path).resolve().as_posix()  # /x/y.csv -> file:///x/y.csv, C:/x/y.csv -> file://C:/x/y.csv
    print("PUT ", cur.execute(f"PUT '{uri}' @%{table} OVERWRITE = TRUE").fetchall())
    print("COPY", cur.execute(f"COPY INTO {table} FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 "
                              "FIELD_OPTIONALLY_ENCLOSED_BY = '\"') PURGE = TRUE").fetchall())
    return tuple(cur.execute(f"SELECT COUNT(*), COUNT_IF(GEO_BOUNDARY IS NULL OR NOT ST_ISVALID(GEO_BOUNDARY)) "
                             f"FROM {table}").fetchone())


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--account")
    p.add_argument("--user")
    p.add_argument("--connection", help="a connection in connections.toml, instead of --account and --user")
    p.add_argument("--authenticator", default="externalbrowser")
    p.add_argument("--warehouse", help="default: the user's own")
    p.add_argument("--table", default="CB_2025_US_STATE")
    p.add_argument("--csv", default=str(CSV))
    a = p.parse_args(argv)
    if not a.connection and not (a.account and a.user):
        p.error("give --connection, or --account and --user")
    import snowflake.connector
    kw = dict(connection_name=a.connection) if a.connection else dict(
        account=a.account, user=a.user, authenticator=a.authenticator)
    if a.warehouse:
        kw["warehouse"] = a.warehouse
    with snowflake.connector.connect(role=ROLE, database=DATABASE, schema=SCHEMA, **kw) as conn:
        got = load(conn, a.table, a.csv)
    where = f"{DATABASE}.{SCHEMA}.{a.table}"
    if got is None:
        sys.exit(f"{where} already has rows: left alone (DROP TABLE it to load again)")
    if got != (N_STATES, 0):
        sys.exit(f"{where}: {got[0]} rows, {got[1]} invalid or missing shapes, expected {N_STATES} and 0")
    print(f"{where}: {got[0]} states, every shape valid")


if __name__ == "__main__":
    main()
