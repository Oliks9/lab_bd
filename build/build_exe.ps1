param(
    [string]$Python = "python",
    [string]$SqlDirectory = "",
    [string]$DistDirectory = "",
    [switch]$TemporaryBuild
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EntryPoint = Join-Path $ProjectRoot "app\quiz_app.py"
$DistPath = if ($DistDirectory) { [IO.Path]::GetFullPath($DistDirectory) } else { Join-Path $ProjectRoot "dist" }
$SqlPath = if ($SqlDirectory) { (Resolve-Path -LiteralPath $SqlDirectory).Path } else { Join-Path $ProjectRoot "sql" }
if (-not (Test-Path -LiteralPath (Join-Path $SqlPath "install.sql"))) {
    throw "SQL directory must contain install.sql."
}
$WorkPath = Join-Path $ProjectRoot "build\pyinstaller"
$SpecPath = Join-Path $ProjectRoot "build"
$TclRuntime = Join-Path $ProjectRoot "build\tcl_runtime"
$RunId = [guid]::NewGuid().ToString("N")
$BuildDistPath = $DistPath
if ($TemporaryBuild) {
    $TemporaryRoot = Join-Path ([IO.Path]::GetTempPath()) "OracleQuizPlatform-build-$RunId"
    $WorkPath = Join-Path $TemporaryRoot "work"
    $SpecPath = $TemporaryRoot
    $BuildDistPath = Join-Path $TemporaryRoot "dist"
    Write-Host "Temporary build files: $TemporaryRoot"
}

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
$SavedNoBytecode = $env:PYTHONDONTWRITEBYTECODE
$SourceReport = Join-Path $WorkPath "source-check-$RunId.json"
$ExeReport = Join-Path $WorkPath "exe-check-$RunId.json"
$ExePath = Join-Path $BuildDistPath "OracleQuizPlatform.exe"

Push-Location $ProjectRoot
try {
    $env:PYTHONDONTWRITEBYTECODE = "1"
    & $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed (exit code $LASTEXITCODE). No new EXE was built."
    }
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependency conflicts detected. No new EXE was built."
    }

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
        --distpath $BuildDistPath `
        --workpath $WorkPath `
        --specpath $SpecPath `
        --paths (Join-Path $ProjectRoot "app") `
        --add-data "${SqlPath};sql" `
        --hidden-import oracledb `
        --collect-all oracledb `
        --collect-all cryptography `
        $EntryPoint
    if ($LASTEXITCODE -ne 0) {
        throw "EXE build failed (exit code $LASTEXITCODE)."
    }

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

    if ($TemporaryBuild) {
        New-Item -ItemType Directory -Path $DistPath -Force | Out-Null
        $DestinationExe = Join-Path $DistPath "OracleQuizPlatform.exe"
        Copy-Item -LiteralPath $ExePath -Destination $DestinationExe -Force
        $ExePath = $DestinationExe
    }
    Write-Host "EXE verified: $ExePath"
    Write-Host "Dependency report: $ExeReport"
}
finally {
    $env:PYTHONPATH = $SavedPythonPath
    $env:TCL_LIBRARY = $SavedTclLibrary
    $env:TK_LIBRARY = $SavedTkLibrary
    $env:PYTHONDONTWRITEBYTECODE = $SavedNoBytecode
    Pop-Location
}
