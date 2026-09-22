param(
    [string]$Python = "python",
    [ValidatePattern('^OracleQuizPlatform_Release[A-Za-z0-9_-]*$')]
    [string]$ReleaseName = "OracleQuizPlatform_Release"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReleaseRoot = Join-Path $ProjectRoot $ReleaseName
if (Test-Path -LiteralPath $ReleaseRoot) {
    throw "Release directory already exists; use another ReleaseName or move it first. No files were replaced."
}
$SqlRoot = (Resolve-Path -LiteralPath (Join-Path $ProjectRoot "sql")).Path
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$Scripts = @{}
$Visiting = @{}

function Read-ReleaseSql([string]$Relative) {
    $Source = [IO.Path]::GetFullPath((Join-Path $SqlRoot $Relative))
    if (-not $Source.StartsWith($SqlRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "SQL include escapes source directory: $Relative"
    }
    if ($Visiting.ContainsKey($Source)) { throw "Cyclic SQL include: $Relative" }
    if ($Scripts.ContainsKey($Source)) { return }
    $Visiting[$Source] = $true
    $Text = [IO.File]::ReadAllText($Source, $Utf8)
    $Target = $Source.Substring($SqlRoot.Length + 1)
    if ($Target.Replace('\', '/') -eq 'tests/check_invalid_objects.sql') {
        $Target = 'check_installation.sql'
    } elseif ($Target.Replace('\', '/').StartsWith('tests/')) {
        throw "A test script is not a release dependency: $Relative"
    }
    foreach ($Match in [regex]::Matches($Text, '(?m)^\s*@@([^\r\n]+)')) {
        $Include = $Match.Groups[1].Value.Trim()
        $Parent = Split-Path -Parent $Source
        $IncludedPath = [IO.Path]::GetFullPath((Join-Path $Parent $Include))
        if (-not $IncludedPath.StartsWith($SqlRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw "SQL include escapes source directory: $Include"
        }
        Read-ReleaseSql $IncludedPath.Substring($SqlRoot.Length + 1)
    }
    $Text = $Text.Replace('@@tests/check_invalid_objects.sql', '@@check_installation.sql')
    $Scripts[$Source] = @{ Target = $Target; Text = $Text }
    $Visiting.Remove($Source)
}

foreach ($Entry in @('install.sql', 'upgrade_no_views.sql', 'upgrade_quiz_invitations.sql')) {
    Read-ReleaseSql $Entry
}

New-Item -ItemType Directory -Path (Join-Path $ReleaseRoot 'app/quiz_client') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'app/quiz_app.py') -Destination (Join-Path $ReleaseRoot 'app/quiz_app.py')
Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'app/quiz_client') -File -Filter '*.py' | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $ReleaseRoot 'app/quiz_client')
}
foreach ($Script in $Scripts.Values) {
    $Destination = Join-Path (Join-Path $ReleaseRoot 'sql') $Script.Target
    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    [IO.File]::WriteAllText($Destination, $Script.Text, $Utf8)
}
$Requirements = Get-Content -LiteralPath (Join-Path $ProjectRoot 'requirements.txt') | Where-Object { $_ -notmatch '^pyinstaller' }
[IO.File]::WriteAllText((Join-Path $ReleaseRoot 'requirements.txt'), ($Requirements -join "`r`n") + "`r`n", $Utf8)
$Commit = (& git -C $ProjectRoot rev-parse --short HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine source revision.' }
$Readme = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'release_README.md'), $Utf8)
$Readme = $Readme.Replace('{{COMMIT}}', $Commit).Replace('{{DATE}}', (Get-Date -Format 'yyyy-MM-dd'))
[IO.File]::WriteAllText((Join-Path $ReleaseRoot 'README.md'), $Readme, $Utf8)

& (Join-Path $PSScriptRoot 'build_exe.ps1') -Python $Python -SqlDirectory (Join-Path $ReleaseRoot 'sql') -DistDirectory $ReleaseRoot
if ($LASTEXITCODE -ne 0) { throw 'Release executable build failed.' }
if (-not (Test-Path -LiteralPath (Join-Path $ReleaseRoot 'OracleQuizPlatform.exe'))) { throw 'Release executable is missing.' }
$Unwanted = Get-ChildItem -LiteralPath $ReleaseRoot -Recurse -Force | Where-Object {
    $_.Name -in @('tests', '__pycache__', '.git', '.venv', 'docker', '.env') -or
    $_.Extension -in @('.pyc', '.pyo', '.log') -or
    ($_.Extension -eq '.md' -and $_.FullName -ne (Join-Path $ReleaseRoot 'README.md'))
}
if ($Unwanted) { throw 'Unexpected development files in the release directory.' }
Write-Host "Release ready: $ReleaseRoot"
