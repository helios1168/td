# Creates data\safe\fix_names.sql (gitignored) from fix_names_template.sql, for the shortlist sheet's spelling fixes.
# Never overwrites an existing one.  From the repo root (Helix: :sh .\tools\snowflake\new_fix_names.ps1)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force data\safe | Out-Null
if (Test-Path data\safe\fix_names.sql) { Write-Output "data\safe\fix_names.sql already exists, left as it is"; exit 0 }
Copy-Item tools\snowflake\fix_names_template.sql data\safe\fix_names.sql
Write-Output "created data\safe\fix_names.sql: :open it, fill in the names, :w, F5"
