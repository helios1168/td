"""Run one SQL file against Snowflake the way Snowsight's Run All does: every statement in one session, then a snapshot
of the last statement's result (its first rows) on screen and all of its rows in data/safe/last.csv (gitignored).

    .\\.venv\\Scripts\\python.exe tools\\snowflake\\run_sql.py <file.sql>

A line `--then <path>` (repo-relative) runs that file next in the same session, so its result is the one shown:
data/safe/fix_names.sql ends with `--then tools/snowflake/explore/sheet_unmatched.sql`.  The file is always named: guessing it (the .sql saved last) ran the wrong script (owner, 2026-11-17). The popup's first
line names the file it ran. The connection is [default] in
~/.snowflake/connections.toml. With data/safe/snowsight_url.txt holding any Snowsight query-detail URL copied from the
browser, it also opens that page for the last result (Snowsight shows a query's results to the user who ran it). It
always exits 0 and writes only to stdout: Helix's :sh hides the output of a failing command, and shows stderr instead of
stdout when a command writes both. 03 with roster edits goes through run_03_04.ps1: this runs a file exactly as it is.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import time
import traceback
import webbrowser

ROWS = 50
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "data", "safe", "last.csv")
URL = os.path.join(ROOT, "data", "safe", "snowsight_url.txt")
QID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def snowsight_url(qid, path=URL):
    """The saved query-detail URL with its query ID swapped for qid, or None when no URL is saved."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        url = f.read().strip()
    if not QID.search(url):
        raise SystemExit(f"{path}: no query ID in it; paste a Snowsight query-detail URL from the browser")
    return QID.sub(qid, url, count=1)


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
    for then in re.findall(r"^--then\s+(\S+)\s*$", sql, re.M):
        print(f"then {then}")
        with open(os.path.join(ROOT, then), encoding="utf-8") as f:
            sql += "\n" + f.read()
    t, n, last, qid = time.time(), 0, None, None
    with snowflake.connector.connect(connection_name="default") as conn:
        try:
            for cur in conn.execute_stream(io.StringIO(sql)):
                n += 1
                if cur.description:
                    last, qid = ([d[0] for d in cur.description], cur.fetchall()), cur.sfqid
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
    url = snowsight_url(qid)
    if url:
        webbrowser.open(url)
        print(f"opened {url}")
    else:
        print(f"query ID {qid} (save a Snowsight query-detail URL in data/safe/snowsight_url.txt to open it in the browser)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr = sys.stdout  # Helix 25.07.1 shows stderr instead of stdout when there is any (the connector's login notes)
    try:
        if len(sys.argv) != 2:
            raise SystemExit("name the SQL file: run_sql.py <file.sql> (Helix: %{buffer_name})")
        main(sys.argv[1])
    except BaseException:  # ponytail: exit 0 with the traceback printed, or Helix's :sh shows only "status 1"
        traceback.print_exc(file=sys.stdout)
