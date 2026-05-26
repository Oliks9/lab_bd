param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EntryPoint = Join-Path $ProjectRoot "app\quiz_app.py"
$DistPath = Join-Path $ProjectRoot "dist"
$WorkPath = Join-Path $ProjectRoot "build\pyinstaller"
$SpecPath = Join-Path $ProjectRoot "build"
$TclRuntime = Join-Path $ProjectRoot "build\tcl_runtime"

& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

# The Codex bundled Python in this workspace ships mismatched Tcl scripts.
# Use extracted compatible Tk resources when present; a normal Python install ignores this branch.
if (Test-Path (Join-Path $TclRuntime "tcl8.6\init.tcl")) {
    $env:PYTHONPATH = "$(Join-Path $TclRuntime 'bin');$env:PYTHONPATH"
    $env:TCL_LIBRARY = "build/tcl_runtime/tcl8.6"
    $env:TK_LIBRARY = "build/tcl_runtime/tk8.6"
}

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name "OracleQuizPlatform" `
        --distpath $DistPath `
        --workpath $WorkPath `
        --specpath $SpecPath `
        --collect-all oracledb `
        --collect-all cryptography `
        $EntryPoint
}
finally {
    Pop-Location
}

Write-Host "EXE created: $(Join-Path $DistPath 'OracleQuizPlatform.exe')"
