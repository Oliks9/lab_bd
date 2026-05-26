$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:DOCKER_CONFIG = Join-Path $ProjectRoot ".docker-config"
New-Item -ItemType Directory -Force -Path $env:DOCKER_CONFIG | Out-Null

Push-Location $ProjectRoot
try {
    docker compose up -d
    docker compose ps
    Write-Host "Oracle is starting. Wait for status 'healthy', then run docker\check.ps1."
    Write-Host "DSN: localhost:1521/FREEPDB1 | schema: quiz_app | password: QuizSchema2026"
}
finally {
    Pop-Location
}
