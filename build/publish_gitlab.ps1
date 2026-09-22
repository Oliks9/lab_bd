param(
    [string]$RepositoryUrl = 'http://10.22.10.16/25-26-spring/discipline-pvsbd/group-ks-23-18/group-ks-23-18-pvsbd-kalinin_syu.git',
    [string]$SourceDirectory = $PSScriptRoot,
    [string]$Branch = 'main',
    [string]$CommitMessage = 'Upload Oracle Quiz Platform release [skip ci]',
    [switch]$AllowHttp,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$Repository = [Uri]$RepositoryUrl
if (-not $Repository.IsAbsoluteUri -or $Repository.Scheme -notin @('http', 'https') -or
    $Repository.UserInfo -or $Repository.Query -or $Repository.Fragment) {
    throw 'Use a full HTTP(S) repository URL without credentials, query or fragment.'
}
$ProjectPath = [Uri]::UnescapeDataString($Repository.AbsolutePath).Trim('/').Replace('\', '/') -replace '\.git$', ''
if (-not $ProjectPath -or $ProjectPath.Split('/') -contains '..') { throw 'Invalid project path.' }
if (-not $Branch.Trim() -or -not $CommitMessage.Trim()) { throw 'Branch and commit message must not be empty.' }
$Api = $Repository.GetLeftPart([UriPartial]::Authority) + '/api/v4/projects/' + [Uri]::EscapeDataString($ProjectPath)
$Root = (Resolve-Path -LiteralPath $SourceDirectory).Path.TrimEnd('\', '/')
if ((Get-Item -LiteralPath $Root).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'The release directory must not be a symbolic link or junction.'
}
foreach ($Required in @('README.md', 'OracleQuizPlatform.exe', 'app/quiz_app.py', 'sql/install.sql', 'rebuild.ps1', 'requirements.txt')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $Required) -PathType Leaf)) {
        throw "Select the complete release directory. Missing: $Required"
    }
}

function Get-ReleaseFiles([string]$Directory) {
    foreach ($Item in Get-ChildItem -LiteralPath $Directory -Force | Sort-Object Name) {
        if ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Symbolic links and junctions cannot be uploaded: $($Item.Name)"
        }
        $Relative = $Item.FullName.Substring($Root.Length + 1).Replace('\', '/')
        if ($Item.Name -match '^(\.git|\.venv.*|venv|__pycache__|tests|\.env.*|\.ssh|\.aws|node_modules)$' -or
            $Item.Extension -match '^\.(pyc|pyo|log|zip|pem|key|pfx|p12)$' -or
            $Item.Name -match '^(connection\.json|credentials.*|secrets?.*|tokens?.*)$') {
            Write-Host "Excluded: $Relative"
            continue
        }
        if ($Item.PSIsContainer) {
            Get-ReleaseFiles $Item.FullName
        } else {
            [PSCustomObject]@{ Path = $Relative; FullName = $Item.FullName; Size = $Item.Length }
        }
    }
}

$Files = @(Get-ReleaseFiles $Root)
$TotalBytes = ($Files | Measure-Object Size -Sum).Sum
if ($TotalBytes -gt 80MB) { throw 'Release exceeds 80 MiB. Check for unrelated files before uploading.' }
Write-Host "Source: $Root"
Write-Host "Destination: $RepositoryUrl"
Write-Host "Branch: $Branch; paths are relative to the repository ROOT."
Write-Host 'README.md and other matching paths will be replaced. Unrelated remote files will NOT be deleted.'
foreach ($File in $Files) { Write-Host ('{0} ({1} bytes)' -f $File.Path, $File.Size) }
Write-Host ('Total: {0} files, {1:N2} MiB' -f $Files.Count, ($TotalBytes / 1MB))
if ($DryRun) { Write-Host 'Dry run finished. No network requests or uploads were made.'; return }
if ($Repository.Scheme -eq 'http') {
    if (-not $AllowHttp) { throw 'HTTP sends the access token without encryption. Use HTTPS or explicitly add -AllowHttp on a trusted network.' }
    Write-Warning 'HTTP is not encrypted. Use a short-lived token on a trusted network and revoke it after uploading.'
}
if ((Read-Host 'Type UPLOAD to confirm replacing matching files in this repository') -cne 'UPLOAD') {
    Write-Host 'Cancelled. No network requests were made.'
    return
}

$Headers = @{}
function Invoke-GitLab([string]$Method, [string]$Url, [byte[]]$Body = $null, [switch]$AllowMissing) {
    $Parameters = @{
        Uri = $Url; Method = $Method; Headers = $Headers; UseBasicParsing = $true
        MaximumRedirection = 0; TimeoutSec = 300; ErrorAction = 'Stop'
    }
    if ($null -ne $Body) { $Parameters.Body = $Body; $Parameters.ContentType = 'application/json; charset=utf-8' }
    try {
        $Response = Invoke-WebRequest @Parameters
        if ([int]$Response.StatusCode -ge 300) { throw 'Unexpected redirect or error response.' }
        return $Response
    } catch {
        $Status = 0
        if ($_.Exception.Response) { $Status = [int]$_.Exception.Response.StatusCode }
        if ($AllowMissing -and $Status -eq 404) { return $null }
        $Hint = switch ($Status) {
            401 { 'Invalid or expired token.' }
            403 { 'No API/write permission, or the branch is protected. Ask the project maintainer.' }
            404 { 'Project or branch not found, or not accessible to this token.' }
            400 { 'GitLab rejected the commit: check branch protection, file conflicts and server limits.' }
            413 { 'Server upload-size limit exceeded. Ask the GitLab administrator to allow this release size.' }
            429 { 'GitLab rate limit reached. Wait before running the script again.' }
            default { 'Check network, server availability and HTTPS/HTTP address. Redirects are not followed.' }
        }
        $Suffix = if ($Method -eq 'POST') { ' The commit outcome may be unknown: check GitLab before retrying. No automatic retry was made.' } else { '' }
        throw "GitLab $Method failed (HTTP $Status). $Hint$Suffix"
    }
}

try {
    $SecureToken = Read-Host 'GitLab access token with api scope (hidden input)' -AsSecureString
    $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
    try { $Headers['PRIVATE-TOKEN'] = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer); $SecureToken.Dispose() }
    if ([string]::IsNullOrWhiteSpace($Headers['PRIVATE-TOKEN'])) { throw 'Token must not be empty.' }
    $Project = (Invoke-GitLab 'GET' $Api).Content | ConvertFrom-Json
    if (-not $Project.id -or $Project.path_with_namespace -cne $ProjectPath) { throw 'GitLab project identity does not match the requested destination.' }
    $BranchUrl = $Api + '/repository/branches/' + [Uri]::EscapeDataString($Branch)
    $Head = (Invoke-GitLab 'GET' $BranchUrl).Content | ConvertFrom-Json
    if ($Head.can_push -eq $false) { throw 'This token cannot write to the selected branch. Ask the project maintainer.' }
    $Revision = [string]$Head.commit.id
    if ($Revision -notmatch '^[0-9a-f]{40,64}$') { throw 'GitLab returned an invalid branch revision.' }
    $Actions = New-Object 'System.Collections.Generic.List[object]'
    $Expected = @{}
    foreach ($File in $Files) {
        $Content = [IO.File]::ReadAllBytes($File.FullName)
        $Sha = [Security.Cryptography.SHA256]::Create()
        try { $Hash = [BitConverter]::ToString($Sha.ComputeHash($Content)).Replace('-', '').ToLowerInvariant() }
        finally { $Sha.Dispose() }
        $Expected[$File.Path] = $Hash
        $FileUrl = $Api + '/repository/files/' + [Uri]::EscapeDataString($File.Path)
        $Remote = Invoke-GitLab 'HEAD' ($FileUrl + '?ref=' + $Revision) -AllowMissing
        if ($Remote -and $Remote.Headers['X-Gitlab-Content-Sha256'] -eq $Hash) { continue }
        $Action = @{ action = 'create'; file_path = $File.Path; content = [Convert]::ToBase64String($Content); encoding = 'base64' }
        if ($Remote) {
            $LastCommit = [string]$Remote.Headers['X-Gitlab-Last-Commit-Id']
            if (-not $LastCommit) { throw "GitLab did not provide a conflict-check revision for $($File.Path). Upload stopped." }
            $Action.action = 'update'
            $Action.last_commit_id = $LastCommit
        }
        $Actions.Add($Action)
        Write-Host ("{0}: {1}" -f $Action.action, $File.Path)
    }
    if ($Actions.Count -eq 0) { Write-Host 'All release files already match GitLab. No commit is needed.'; return }
    $CurrentHead = (Invoke-GitLab 'GET' $BranchUrl).Content | ConvertFrom-Json
    if ($CurrentHead.commit.id -ne $Revision) { throw 'The branch changed during preparation. Nothing was uploaded; run again to refresh the file list.' }
    $Payload = @{ branch = $Branch; commit_message = $CommitMessage; actions = $Actions.ToArray() } | ConvertTo-Json -Depth 8 -Compress
    $PayloadBytes = $Utf8.GetBytes($Payload)
    Write-Host ('Sending {0} files in one commit ({1:N2} MiB request)...' -f $Actions.Count, ($PayloadBytes.Length / 1MB))
    $Commit = (Invoke-GitLab 'POST' ($Api + '/repository/commits') $PayloadBytes).Content | ConvertFrom-Json
    if ($Commit.id -notmatch '^[0-9a-f]{40,64}$') { throw 'Commit response could not be verified. Check GitLab before retrying.' }
    Write-Host ('Commit created: {0}/-/commit/{1}' -f ($RepositoryUrl -replace '\.git$', ''), $Commit.id)
    foreach ($File in $Files) {
        $FileUrl = $Api + '/repository/files/' + [Uri]::EscapeDataString($File.Path) + '?ref=' + $Commit.id
        $Remote = Invoke-GitLab 'HEAD' $FileUrl
        if ($Remote.Headers['X-Gitlab-Content-Sha256'] -ne $Expected[$File.Path]) {
            throw "Commit created, but verification failed for $($File.Path). Inspect the commit; do not assume the upload is complete."
        }
    }
    Write-Host 'Upload verified: every release file matches the created commit. README.md is at the repository root.'
} finally {
    $Headers.Clear()
}
