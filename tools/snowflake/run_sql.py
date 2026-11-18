"""Run one SQL file against Snowflake the way Snowsight's Run All does: every statement in one session, then a snapshot
of the last statement's result (its first rows) on screen and all of its rows in data/safe/last.csv (gitignored).

    .\\.venv\\Scripts\\python.exe tools\\snowflake\\run_sql.py [file.sql]

With no file it runs the .sql file saved last under tools/ or data/safe/: Helix before 25.07 has no %{buffer_name}, so
the F5 binding (tools/snowflake/README.md) is :write then this, and the popup's first line names the file it ran. The connection is [default] in
~/.snowflake/connections.toml. 03 with roster edits goes through run_03_04.ps1: this runs a file exactly as it is.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time

ROWS = 50
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "data", "safe", "last.csv")


def newest_sql(root=ROOT):
    """The .sql file under tools/ or data/safe/ saved last (the buffer F5 just wrote)."""
    found = [os.path.join(d, f) for top in ("tools", os.path.join("data", "safe"))
             for d, _, fs in os.walk(os.path.join(root, top)) for f in fs if f.lower().endswith(".sql")]
    if not found:
        raise SystemExit("no .sql file under tools/ or data/safe/")
    return max(found, key=os.path.getmtime)


def snapshot(cols, rows, n_stmt, secs):
    """The last result as Snowsight shows it: a table of its first ROWS rows, then its size."""
    import pandas as pd
    df = pd.DataFrame(rows, columns=cols)
    more = f", first {ROWS} shown" if len(df) > ROWS else ""
    return (df.head(ROWS).to_string(index=False, max_colwidth=40) +
            f"\n\n{len(df)} rows x {len(cols)} columns{more}. {n_stmt} statements in {secs:.0f} s. All rows: data/safe/last.csv")


def main(path):
    import snowflake.connector
    print(f"ran {os.path.relpath(path, ROOT)}")
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    t, n, last = time.time(), 0, None
    with snowflake.connector.connect(connection_name="default") as conn:
        try:
            for cur in conn.execute_stream(io.StringIO(sql)):
                n += 1
                if cur.description:
                    last = ([d[0] for d in cur.description], cur.fetchall())
        except snowflake.connector.errors.Error as e:
            print(f"ERROR in statement {n + 1} ({n} ran):\n{e}")
            return 1
    if last is None:
        print(f"{n} statements, none returned rows")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(last[0])
        w.writerows(last[1])
    print(snapshot(*last, n, time.time() - t))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else newest_sql()))
