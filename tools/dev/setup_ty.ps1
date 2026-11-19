# Sets up ty (Astral's Python language server) for Helix on this machine.  From the repo root:  .\tools\dev\setup_ty.ps1
#  1. installs ty into this repo's .venv (pip, as snowflake-cli was);
#  2. points Helix at that ty.exe in your user config, %APPDATA%\helix\languages.toml, the folder Helix reads on Windows.
# Helix 25.07.1 already lists ty first among Python's language servers (its languages.toml: ty = { command = "ty", args = ["server"] },
# python language-servers = ["ty", "ruff", "jedi", "pylsp"]), so only the path to ty.exe is set here.  ty finds the repo's .venv itself.
# An existing languages.toml is backed up first and kept; the ty lines are added once (rerunning changes nothing).  Restart Helix after.
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "no $py : create the .venv first (README)" }
& $py -m pip install --upgrade ty
if ($LASTEXITCODE -ne 0) { throw "pip install ty failed (exit $LASTEXITCODE)" }
$ty = Join-Path $repo ".venv\Scripts\ty.exe"
if (-not (Test-Path $ty)) { throw "ty.exe is not at $ty after the install" }
& $ty --version

$dir = Join-Path $env:APPDATA "helix"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$cfg = Join-Path $dir "languages.toml"
$noBom = New-Object System.Text.UTF8Encoding $false            # Windows PowerShell's -Encoding UTF8 writes a BOM; TOML wants none
$block = "`n# ty, the Python language server, from $repo\.venv (tools\dev\setup_ty.ps1)`n[language-server.ty]`ncommand = '$ty'`nargs = [`"server`"]`n"
if (Test-Path $cfg) {
    $text = [System.IO.File]::ReadAllText($cfg)
    # ty already defined either way TOML allows: its own table, or `ty = ...` inside a [language-server] table
    if ($text -match '(?m)^\s*\[language-server\.ty\]' -or $text -match '(?ms)^\s*\[language-server\]\s*$(?:(?!^\s*\[).)*?^\s*ty\s*=') {
        Write-Output "$cfg already has [language-server.ty], left as it is:"
        Select-String -Path $cfg -Pattern 'language-server\.ty' -Context 0, 3 | ForEach-Object { $_.ToString() }
    } else {
        $bak = "$cfg.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")
        Copy-Item $cfg $bak
        [System.IO.File]::AppendAllText($cfg, $block, $noBom)
        Write-Output "added ty to $cfg (the old file is $bak)"
    }
} else {
    [System.IO.File]::WriteAllText($cfg, $block.TrimStart(), $noBom)
    Write-Output "wrote $cfg"
}
if (Get-Command hx -ErrorAction SilentlyContinue) { hx --health python } else { Write-Output "hx is not on PATH: check with  hx --health python  in a new terminal" }
