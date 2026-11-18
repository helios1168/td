# Logs in to Snowflake once (one browser login) and keeps that session for F5 in Helix: run it in its own terminal pane
# (Alt+Shift+D, then .venv\Scripts\Activate.ps1 is not needed) and leave it open.  Ctrl+C stops it.
# From the repo root:  .\tools\snowflake\sql_session.ps1
.\.venv\Scripts\python.exe tools\snowflake\run_sql.py --serve
