# Runs 03 then 04 with the snow CLI and saves each output as CSV in data\safe\ (gitignored: the output carries names).
# Roster edits (wholesaler names) never go in the repo: write the INSERT rows in data\safe\03_edits.sql and this script
# puts them between 03's "--owner edits: begin" and "--owner edits: end" lines (the file in the repo stays unedited).
# From the repo root with .venv activated:  .\tools\snowflake\run_03_04.ps1
$ErrorActionPreference = "Stop"
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw "git pull failed" }
New-Item -ItemType Directory -Force data\safe | Out-Null
$t = Get-Date -Format "yyyy-MM-dd-HHmm"

$sql = Get-Content -Raw tools\snowflake\03_assignments.sql
if (Test-Path data\safe\03_edits.sql) {
    $edits = (Get-Content -Raw data\safe\03_edits.sql).TrimEnd()
    if ($edits -match '[^\x00-\x7F]') { throw "03_edits.sql has a non-ASCII character (an accent?): type the name as the data has it in plain ASCII, or ask" }
    $re = '(?s)(--owner edits: begin\r?\n).*?(--owner edits: end)'
    if ($sql -notmatch $re) { throw "03_assignments.sql has no owner edits block" }
    $sql = [regex]::Replace($sql, $re, { param($m) $m.Groups[1].Value + $edits + "`n" + $m.Groups[2].Value })
    Write-Host "03: edits from data\safe\03_edits.sql"
} else {
    Write-Host "03: no data\safe\03_edits.sql, so the default roster (every WH or FI holder kept, as WIFI)"
}
Set-Content -Encoding ascii data\safe\03_run.sql $sql

foreach ($f in @(@("03_assignments", "data\safe\03_run.sql"), @("04_assigned_coverage", "tools\snowflake\04_assigned_coverage.sql"))) {
    $out = "data\safe\$($f[0])_$t.csv"
    snow sql -f $f[1] --format CSV | Set-Content -Encoding utf8 $out
    if ($LASTEXITCODE -ne 0) { throw "$($f[0]).sql failed, see $out" }
    Write-Host "$($f[0]).sql -> $out"
}
