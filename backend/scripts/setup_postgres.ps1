<#
Creates RailVigil's local PostgreSQL + PostGIS databases on Windows and writes
DATABASE_URL / TEST_DATABASE_URL into backend/.env. Safe to run again.

  powershell -ExecutionPolicy Bypass -File backend\scripts\setup_postgres.ps1

What it does (details in docs/SETUP_POSTGRES.md):
  * asks for the PostgreSQL superuser ("postgres") password; it is used only by
    this script and never written anywhere
  * creates a tablespace folder (default E:\PostgresData\railvigil) so the
    project's data lives outside the PostgreSQL install directory
  * creates role "railvigil" with a freshly generated password, databases
    "railvigil" and "railvigil_test" in that tablespace, and enables PostGIS
  * writes the two connection URLs into backend/.env (git-ignored), keeping
    any other lines already there; passwords are never printed
#>
param(
    [string]$PgBin = 'C:\Program Files\PostgreSQL\17\bin',
    [string]$TablespaceDir = 'E:\PostgresData\railvigil',
    [string]$PgHost = 'localhost',
    [int]$Port = 5432,
    [string]$ServiceName = 'postgresql-x64-17'
)
$ErrorActionPreference = 'Stop'

$psql = Join-Path $PgBin 'psql.exe'
if (-not (Test-Path $psql)) { throw "psql.exe not found in '$PgBin'. Pass -PgBin <PostgreSQL bin folder>." }
$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'

function Invoke-Sql([string]$db, [string]$sql) {
    $out = & $psql -h $PgHost -p $Port -U postgres -d $db -w -v ON_ERROR_STOP=1 -tA -c $sql 2>&1
    if ($LASTEXITCODE -ne 0) { throw "psql failed on '$db': $out" }
    return ($out | Out-String).Trim()
}

# Superuser password: only in this process's environment, cleared at the end.
$secure = Read-Host -AsSecureString 'PostgreSQL superuser (postgres) password'
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

try {
    Write-Host "Connected to: $(Invoke-Sql 'postgres' 'SELECT version()')"

    # Tablespace folder: must exist, and the PostgreSQL service account must own the data in it.
    $tsExists = (Invoke-Sql 'postgres' "SELECT count(*) FROM pg_tablespace WHERE spcname = 'railvigil_ts'") -eq '1'
    if (-not $tsExists) {
        if (-not (Test-Path $TablespaceDir)) { New-Item -ItemType Directory -Path $TablespaceDir -Force | Out-Null }
        if (Get-ChildItem $TablespaceDir -Force) { throw "Tablespace folder '$TablespaceDir' is not empty." }
        $account = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").StartName
        if (-not $account) { throw "Service '$ServiceName' not found. Pass -ServiceName." }
        & icacls $TablespaceDir /grant "${account}:(OI)(CI)F" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not grant '$account' access to '$TablespaceDir'." }
        $location = $TablespaceDir -replace '\\', '/'
        Invoke-Sql 'postgres' "CREATE TABLESPACE railvigil_ts LOCATION '$location'" | Out-Null
        Write-Host "Created tablespace railvigil_ts at $TablespaceDir"
    } else {
        Write-Host 'Tablespace railvigil_ts already exists'
    }

    # Role with a new random password (letters and digits only, so it is URL- and SQL-safe).
    $chars = [char[]]'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 24
    $rng.GetBytes($bytes)
    $appPassword = -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
    $roleExists = (Invoke-Sql 'postgres' "SELECT count(*) FROM pg_roles WHERE rolname = 'railvigil'") -eq '1'
    if ($roleExists) {
        Invoke-Sql 'postgres' "ALTER ROLE railvigil WITH LOGIN PASSWORD '$appPassword'" | Out-Null
        Write-Host 'Role railvigil existed; password rotated'
    } else {
        Invoke-Sql 'postgres' "CREATE ROLE railvigil WITH LOGIN PASSWORD '$appPassword'" | Out-Null
        Write-Host 'Created role railvigil'
    }
    Invoke-Sql 'postgres' 'GRANT CREATE ON TABLESPACE railvigil_ts TO railvigil' | Out-Null

    foreach ($db in 'railvigil', 'railvigil_test') {
        $dbExists = (Invoke-Sql 'postgres' "SELECT count(*) FROM pg_database WHERE datname = '$db'") -eq '1'
        if (-not $dbExists) {
            Invoke-Sql 'postgres' "CREATE DATABASE $db OWNER railvigil TABLESPACE railvigil_ts" | Out-Null
            Write-Host "Created database $db"
        } else {
            Write-Host "Database $db already exists"
        }
        # Extensions need a superuser; the app role then just uses PostGIS.
        Invoke-Sql $db 'CREATE EXTENSION IF NOT EXISTS postgis' | Out-Null
        Write-Host "  PostGIS in ${db}: $(Invoke-Sql $db 'SELECT postgis_lib_version()')"
    }

    # Write the URLs into backend/.env, replacing only these two keys.
    $urls = [ordered]@{
        'DATABASE_URL'      = "postgresql+psycopg2://railvigil:$appPassword@${PgHost}:$Port/railvigil"
        'TEST_DATABASE_URL' = "postgresql+psycopg2://railvigil:$appPassword@${PgHost}:$Port/railvigil_test"
    }
    $lines = @()
    if (Test-Path $envFile) {
        $lines = Get-Content $envFile | Where-Object { $_ -notmatch '^(DATABASE_URL|TEST_DATABASE_URL)=' }
    }
    $lines += $urls.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
    [IO.File]::WriteAllLines($envFile, [string[]]$lines, (New-Object Text.UTF8Encoding($false)))
    Write-Host "Wrote DATABASE_URL and TEST_DATABASE_URL to $envFile (values not shown)"

    # Prove the app role can log in and see PostGIS.
    $env:PGPASSWORD = $appPassword
    $check = & $psql -h $PgHost -p $Port -U railvigil -d railvigil -w -tA -c 'SELECT current_user || '' / '' || postgis_version()' 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Login as railvigil failed: $check" }
    Write-Host "Login check OK: $check"
    Write-Host 'Done.'
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    $appPassword = $null
}
