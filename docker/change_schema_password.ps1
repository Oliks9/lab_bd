$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:DOCKER_CONFIG = Join-Path $ProjectRoot ".docker-config"
New-Item -ItemType Directory -Force -Path $env:DOCKER_CONFIG | Out-Null

Push-Location $ProjectRoot
try {
    docker compose exec -T oracle sqlplus -s "/ as sysdba" "@/opt/quiz-project/docker/change_schema_password.sql"
    if ($LASTEXITCODE -ne 0) {
        throw "Schema password change failed (exit code $LASTEXITCODE)."
    }
}
finally {
    Pop-Location
}
