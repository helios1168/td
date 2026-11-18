# The scenario maps (issue #147): runs 03 and 04 per scenario in one Snowflake login, then draws data\safe\maps\<run>\<scenario>.pdf.
# From the repo root:  .\tools\maps\scenario_maps.ps1 -List   |   -All   |   -Scenario CA1_R105N,CA2_R105N
param([switch]$All, [switch]$List, [string[]]$Scenario)
$ErrorActionPreference = "Stop"
$py = ".\.venv\Scripts\python.exe"
if ($List) { $a = @("--list") }
elseif ($All) { $a = @("--all") }
elseif ($Scenario) { $a = $Scenario | ForEach-Object { "--scenario"; $_ } }
else { throw "name -All, -Scenario <name>[,<name>] or -List" }
& $py tools\maps\scenario_maps.py @a
exit $LASTEXITCODE
