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

# Resolve relative interpreter paths before changing the working directory.
$ResolvedPython = & $Python -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0 -or -not $ResolvedPython) {
    throw "Cannot run the selected Python interpreter: $Python"
}
$Python = [string]($ResolvedPython | Select-Object -Last 1)
Write-Host "Build interpreter: $Python"
& $Python -c "import sys; print(sys.version); sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10 or newer is required. Python 3.12 x64 is tested for this project."
}

$SavedPythonPath = $env:PYTHONPATH
$SavedTclLibrary = $env:TCL_LIBRARY
$SavedTkLibrary = $env:TK_LIBRARY
$RunId = [guid]::NewGuid().ToString("N")
$SourceReport = Join-Path $WorkPath "source-check-$RunId.json"
$ExeReport = Join-Path $WorkPath "exe-check-$RunId.json"
$ExePath = Join-Path $DistPath "OracleQuizPlatform.exe"

Push-Location $ProjectRoot
try {
    & $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed (exit code $LASTEXITCODE). No new EXE was built."
    }
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependency conflicts detected. No new EXE was built."
    }

    # This local workaround is only needed by the bundled Codex Python runtime.
    if (Test-Path (Join-Path $TclRuntime "tcl8.6\init.tcl")) {
        $env:PYTHONPATH = "$(Join-Path $TclRuntime 'bin');$env:PYTHONPATH"
        $env:TCL_LIBRARY = "build/tcl_runtime/tcl8.6"
        $env:TK_LIBRARY = "build/tcl_runtime/tk8.6"
    }
    New-Item -ItemType Directory -Path $WorkPath -Force | Out-Null
    & $Python $EntryPoint --self-check $SourceReport
    if ($LASTEXITCODE -ne 0) {
        throw "Source dependency check failed. See $SourceReport. No new EXE was built."
    }

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name "OracleQuizPlatform" `
        --distpath $DistPath `
        --workpath $WorkPath `
        --specpath $SpecPath `
        --paths (Join-Path $ProjectRoot "app") `
        --hidden-import oracledb `
        --collect-all oracledb `
        --collect-all cryptography `
        $EntryPoint
    if ($LASTEXITCODE -ne 0) {
        throw "EXE build failed (exit code $LASTEXITCODE)."
    }

    # Unique report names prevent a stale report from passing a failed build.
    $Check = Start-Process -FilePath $ExePath `
        -ArgumentList @('--self-check', ('"{0}"' -f $ExeReport)) `
        -WindowStyle Hidden -PassThru
    try {
        if (-not $Check.WaitForExit(60000)) {
            $Check.Kill()
            throw "EXE self-check timed out. Do not distribute this build."
        }
        $Check.Refresh()
        if (-not (Test-Path -LiteralPath $ExeReport)) {
            throw "EXE self-check produced no report (exit code $($Check.ExitCode)). Check Windows compatibility and security logs."
        }
        $Report = Get-Content -LiteralPath $ExeReport -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Check.ExitCode -ne 0 -or $Report.ok -ne $true -or $Report.frozen -ne $true) {
            Get-Content -LiteralPath $ExeReport -Raw -Encoding UTF8 | Write-Host
            throw "EXE dependency check failed. See $ExeReport. Do not distribute this build."
        }
    }
    finally {
        $Check.Dispose()
    }

    Write-Host "EXE verified: $ExePath"
    Write-Host "Dependency report: $ExeReport"
}
finally {
    $env:PYTHONPATH = $SavedPythonPath
    $env:TCL_LIBRARY = $SavedTclLibrary
    $env:TK_LIBRARY = $SavedTkLibrary
    Pop-Location
}
