<#
Runs the backend test suite against the local PostgreSQL test database.
Reads TEST_DATABASE_URL from backend/.env (written by setup_postgres.ps1)
for this process only. Extra arguments go to pytest.

  powershell -ExecutionPolicy Bypass -File backend\scripts\test_postgres.ps1 -q
#>
$ErrorActionPreference = 'Stop'
$backend = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $backend '.env'
$line = if (Test-Path $envFile) { Get-Content $envFile | Where-Object { $_ -match '^TEST_DATABASE_URL=' } | Select-Object -First 1 }
if (-not $line) { throw "TEST_DATABASE_URL not found in $envFile. Run backend\scripts\setup_postgres.ps1 first." }
$env:TEST_DATABASE_URL = $line.Substring('TEST_DATABASE_URL='.Length)
try {
    Push-Location $backend
    & (Join-Path $backend '.venv\Scripts\python.exe') -m pytest @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
}
