# Upgrades an existing data\safe\fix_names.sql: drops the copy of sheet_unmatched.sql appended to it (from its
# "--THE RESULT HOLDS WHOLESALER NAMES" line on) and ends it with the --then line, so F5 runs the current
# sheet_unmatched.sql from the repo.  Keeps a copy as fix_names.sql.bak.  From the repo root, once:
#   .\tools\snowflake\upgrade_fix_names.ps1     (Helix: :sh .\tools\snowflake\upgrade_fix_names.ps1, then :reload)
$ErrorActionPreference = "Stop"
$f = "data\safe\fix_names.sql"
if (-not (Test-Path $f)) { throw "$f does not exist: run .\tools\snowflake\new_fix_names.ps1" }
$lines = Get-Content $f
if ($lines -match '^--then ') { Write-Output "$f already ends with a --then line, left as it is"; exit 0 }
Copy-Item $f "$f.bak" -Force
$cut = [array]::IndexOf($lines, ($lines | Where-Object { $_ -like '--THE RESULT HOLDS WHOLESALER NAMES*' } | Select-Object -First 1))
if ($cut -gt 0) { $lines = $lines[0..($cut - 1)] }
# the three use lines the old copy started with sit just above that line: drop them too
while ($lines.Count -gt 0 -and ($lines[-1] -match '^\s*$' -or $lines[-1] -like 'use *')) { $lines = $lines[0..($lines.Count - 2)] }
$lines + @("", "--then tools/snowflake/explore/sheet_unmatched.sql") | Set-Content -Encoding ascii $f
Write-Output "upgraded $f (old copy in $f.bak): :reload, then F5"
