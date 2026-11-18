# One-time setup of the Snowflake CLI on the owner's Windows machine.
# Run from the repo root with the .venv activated:  .\tools\snowflake\setup_snow.ps1
$ErrorActionPreference = "Stop"
git pull --ff-only
if (-not (Get-Command snow -ErrorAction SilentlyContinue)) { python -m pip install snowflake-cli }
New-Item -ItemType Directory -Force "$env:USERPROFILE\.snowflake" | Out-Null
Copy-Item tools\snowflake\connections.toml "$env:USERPROFILE\.snowflake\connections.toml" -Force
snow --version
snow connection test
