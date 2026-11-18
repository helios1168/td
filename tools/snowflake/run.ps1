# Runs one SQL file with the snow CLI and saves its output as CSV in data\safe\ (gitignored: output can carry names),
# as <name>_<time>.csv and as data\safe\last.csv (keep that open in Helix and :reload-all after each run).
# From the repo root with .venv activated:  .\tools\snowflake\run.ps1 <file.sql>
# For 03 with roster edits use run_03_04.ps1: this script runs the file as it is.
param([Parameter(Mandatory = $true)][string]$File)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force data\safe | Out-Null
$out = "data\safe\$([IO.Path]::GetFileNameWithoutExtension($File))_$(Get-Date -Format yyyy-MM-dd-HHmmss).csv"
snow sql -f $File --format CSV | Set-Content -Encoding utf8 $out
if ($LASTEXITCODE -ne 0) { throw "$File failed (snow's error is above), partial output in $out" }
Copy-Item $out data\safe\last.csv -Force
Get-Content $out -Tail 40
Write-Host "-> $out (and data\safe\last.csv)"
