# Creates a local .env from .env.example with freshly generated random secrets.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
# - Never prints secrets. Never overwrites an existing .env.
# - .env is git-ignored. Do not paste its contents into chat or commit it.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$example = Join-Path $root ".env.example"
$target = Join-Path $root ".env"

if (Test-Path $target) {
    Write-Host ".env already exists. Nothing changed. Delete it first if you want a fresh one."
    exit 0
}

function New-Secret([int]$bytes) {
    $buf = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buf)
    # base64url: safe inside URLs and .env files
    return [Convert]::ToBase64String($buf).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$pgPassword = New-Secret 24
$values = @{
    "APP_ENV"            = "development"
    "APP_SECRET_KEY"     = New-Secret 48
    "JWT_SECRET_KEY"     = New-Secret 48
    "POSTGRES_USER"      = "securesearch"
    "POSTGRES_PASSWORD"  = $pgPassword
    "POSTGRES_DB"        = "securesearch"
    "DATABASE_URL"       = "postgresql://securesearch:$pgPassword@postgres:5432/securesearch"
    "REDIS_URL"          = "redis://redis:6379/0"
    "SMTP_HOST"          = "mailpit"
    "SMTP_PORT"          = "1025"
    "SEED_USER_PASSWORD" = New-Secret 15
}

$lines = Get-Content $example | ForEach-Object {
    if ($_ -match '^([A-Z_]+)=') {
        $key = $Matches[1]
        if ($values.ContainsKey($key)) { return "$key=$($values[$key])" }
    }
    $_
}
# UTF-8 without BOM, LF endings (Docker reads this file)
[System.IO.File]::WriteAllText($target, (($lines -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
Write-Host ".env created with generated secrets (values not shown)."
Write-Host "Demo-user password = SEED_USER_PASSWORD inside .env (open the file locally to read it)."
