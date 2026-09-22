param([string]$Python = "")

$ErrorActionPreference = "Stop"
if (-not $Python) {
    $ResolvedPython = & py -3.12 -c "import sys; print(sys.executable)"
    if ($LASTEXITCODE -ne 0 -or -not $ResolvedPython) {
        throw "Install Python 3.12 x64 with pip and Tcl/Tk, or specify -Python with the interpreter path."
    }
    $Python = [string]($ResolvedPython | Select-Object -Last 1)
}
& (Join-Path $PSScriptRoot 'build/build_exe.ps1') -Python $Python -DistDirectory $PSScriptRoot -TemporaryBuild
if ($LASTEXITCODE -ne 0) { throw 'Release rebuild failed.' }
