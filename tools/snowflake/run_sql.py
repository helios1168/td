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

Output into the buffer: `run_sql.py --stdin` (Helix F6, :pipe on the selection, any buffer, a scratch one too) runs the SQL
it reads and prints it back unchanged with the output after it as `-- ` comment lines, so the result lands under the
query and does not run next time, and opens no browser tab (F5 does).  It goes through data/safe/_pipe.sql, so the
session can run it.

One login a day: `run_sql.py --serve` (tools/snowflake/sql_session.ps1, in its own terminal pane) logs in once, keeps that
session alive and runs each file F5 sends it on 127.0.0.1:PORT, guarded by a token in data/safe/sql_session.token.  With
no session running, F5 logs in itself (a browser login each time: the account's ALLOW_ID_TOKEN is false, owner
2026-11-18).  The session keeps SET variables and temporary tables between runs, as a Snowsight worksheet does.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import re
import secrets
import socket
import sys
import time
import traceback
import webbrowser

ROWS = 50
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "data", "safe", "last.csv")
URL = os.path.join(ROOT, "data", "safe", "snowsight_url.txt")
TOKEN = os.path.join(ROOT, "data", "safe", "sql_session.token")
PORT = 47821
QID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def snowsight_url(qid, path=None):
    """The saved query-detail URL with its query ID swapped for qid, or None when no URL is saved."""
    path = path or URL
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


def main(path, conn=None, browser=True):
    import snowflake.connector
    print(f"ran {os.path.relpath(path, ROOT)}")
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    for then in re.findall(r"^--then\s+(\S+)\s*$", sql, re.M):
        print(f"then {then}")
        with open(os.path.join(ROOT, then), encoding="utf-8") as f:
            sql += "\n" + f.read()
    t, n, last, qid = time.time(), 0, None, None
    with (contextlib.nullcontext(conn) if conn else snowflake.connector.connect(connection_name="default")) as conn:
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
    url = snowsight_url(qid) if browser else None
    if url:
        webbrowser.open(url)
        print(f"opened {url}")
    else:
        print(f"query ID {qid}" + ("" if not browser else " (save a Snowsight query-detail URL in data/safe/snowsight_url.txt to open it in the browser)"))
    return 0


def serve(port=PORT, connect=None):
    """Log in once and run each file a client sends, in that one session, until stopped (Ctrl+C)."""
    import snowflake.connector
    connect = connect or (lambda: snowflake.connector.connect(connection_name="default", client_session_keep_alive=True))
    conn, token = connect(), secrets.token_hex(16)
    os.makedirs(os.path.dirname(TOKEN), exist_ok=True)
    with open(TOKEN, "w") as f:
        f.write(token)
    with socket.create_server(("127.0.0.1", port)) as srv:
        print(f"logged in; F5 now runs in this session (port {port}). Ctrl+C stops it.", flush=True)
        while True:
            c, _ = srv.accept()
            with c, c.makefile("rw", encoding="utf-8", newline="\n") as f:
                req = json.loads(f.readline() or "{}")
                if req.get("token") != token:
                    f.write("refused: wrong session token (restart sql_session.ps1)\n")
                    continue
                if conn.is_closed():
                    conn = connect()
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    try:
                        main(req["path"], conn, req.get("browser", True))
                    except BaseException:
                        traceback.print_exc(file=buf)
                f.write(buf.getvalue())
            print(f"ran {os.path.relpath(req['path'], ROOT)}", flush=True)


def piped(data, runner=None):
    """The selection back unchanged, then the output of running it as `-- ` comments, in the selection's line ending."""
    text = data.decode("utf-8")
    path = os.path.join(ROOT, "data", "safe", "_pipe.sql")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    out = (runner or run)(path, browser=False)  # F6: no browser tab, F5 opens it
    nl = "\r\n" if "\r\n" in text else "\n"
    sep = "" if text.endswith("\n") else nl
    return (text + sep + "".join(f"-- {line}{nl}" for line in out.splitlines())).encode("utf-8")


def run(path, browser=True):
    """The output of running path: by the session when one is running, else after logging in."""
    out = send(path, browser=browser)
    if out is None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print("no SQL session running (start .\\tools\\snowflake\\sql_session.ps1 to log in once): logging in")
            try:
                main(path, browser=browser)
            except BaseException:
                traceback.print_exc(file=buf)
        out = buf.getvalue()
    return out


def send(path, port=PORT, browser=True):
    """The output of path run by the session, or None when no session is running."""
    try:
        with open(TOKEN) as f:
            token = f.read().strip()
        c = socket.create_connection(("127.0.0.1", port), timeout=2)
    except OSError:
        return None
    with c, c.makefile("rw", encoding="utf-8", newline="\n") as f:
        c.settimeout(None)
        f.write(json.dumps({"token": token, "path": os.path.abspath(path), "browser": browser}) + "\n")
        f.flush()
        return f.read()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr = sys.stdout  # Helix 25.07.1 shows stderr instead of stdout when there is any (the connector's login notes)
    try:
        args = sys.argv[1:]
        if args == ["--serve"]:
            serve()
        elif args == ["--stdin"]:
            sys.stdout.flush()
            sys.stdout.buffer.write(piped(sys.stdin.buffer.read()))  # bytes: no CRLF translation of the echoed SQL
        elif len(args) != 1:
            raise SystemExit("name the SQL file: run_sql.py <file.sql> (Helix: %{buffer_name}), or --stdin, or --serve")
        else:
            print(run(args[0]), end="")
    except BaseException:  # ponytail: exit 0 with the traceback printed, or Helix's :sh shows only "status 1"
        traceback.print_exc(file=sys.stdout)
