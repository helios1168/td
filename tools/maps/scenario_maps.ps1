# The scenario maps (issue #147): runs 03, 04 and 07 per scenario in one Snowflake login, then draws data\safe\maps\<run>\maps.pdf.
# From the repo root:  .\tools\maps\scenario_maps.ps1 -List   |   -All   |   -Scenario CA1_R105N,CA2_R105N   (add -Divisions for the division pages)
# The draft assignment (issue #152): -Draft results\draft\2026-11-19 [-Scenario ...] draws data\safe\maps\<run>\draft.pdf with names (no 03, 04 or 07).
param([switch]$All, [switch]$List, [string[]]$Scenario, [switch]$Divisions, [string]$Draft)
$ErrorActionPreference = "Stop"
$py = ".\.venv\Scripts\python.exe"
if ($Draft) { $a = @("--draft", $Draft); if ($Scenario) { $a += $Scenario | ForEach-Object { "--scenario"; $_ } } }
elseif ($List) { $a = @("--list") }
elseif ($All) { $a = @("--all") }
elseif ($Scenario) { $a = $Scenario | ForEach-Object { "--scenario"; $_ } }
else { throw "name -All, -Scenario <name>[,<name>], -List or -Draft <folder>" }
if ($Divisions) { $a += "--divisions" }
& $py tools\maps\scenario_maps.py @a
exit $LASTEXITCODE
