$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:DOCKER_CONFIG = Join-Path $ProjectRoot ".docker-config"
New-Item -ItemType Directory -Force -Path $env:DOCKER_CONFIG | Out-Null

Push-Location $ProjectRoot
try {
    docker compose exec -T oracle sqlplus -s /nolog "@/opt/quiz-project/docker/reinstall_application.sql"
}
finally {
    Pop-Location
}
