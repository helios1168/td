"""tools/dev/setup_ty.ps1 (owner, 2026-11-19): ty for Helix on the Windows work machine.  PowerShell does not run here, so the
script's contract is pinned by its text: the user config Helix reads on Windows, the repo's .venv ty.exe, no BOM, and an existing
languages.toml backed up, never overwritten."""
import pathlib

PS1 = pathlib.Path(__file__).resolve().parents[1] / "tools" / "dev" / "setup_ty.ps1"


def test_setup_ty_writes_the_windows_user_config_once_with_the_venv_ty_and_no_bom():
    t = PS1.read_text(encoding="utf-8")
    assert 'Join-Path $env:APPDATA "helix"' in t and '"languages.toml"' in t          # %APPDATA%\helix\languages.toml
    assert '".venv\\Scripts\\python.exe"' in t and '".venv\\Scripts\\ty.exe"' in t and "pip install --upgrade ty" in t
    assert "[language-server.ty]" in t and 'args = [`"server`"]' in t and "command = '$ty'" in t   # TOML literal string: backslashes kept
    assert "UTF8Encoding $false" in t and "Set-Content" not in t and "Out-File" not in t       # no BOM anywhere
    assert "Copy-Item $cfg $bak" in t and "AppendAllText" in t and "WriteAllText($cfg, $block.TrimStart()" in t
    assert t.count("WriteAllText") == 1 and "if (Test-Path $cfg)" in t                         # writes a new file only when there is none
