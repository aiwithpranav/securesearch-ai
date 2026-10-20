# Creates or completes a local .env with freshly generated random secrets.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
# - No .env yet: creates it from .env.example.
# - .env exists: adds ONLY the keys that are missing (for example after a new phase adds settings).
#   Existing lines are never changed or removed.
# - Never prints secrets. .env is git-ignored. Do not paste its contents into chat or commit it.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$example = Join-Path $root ".env.example"
$target = Join-Path $root ".env"

function New-Secret([int]$bytes) {
    $buf = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buf)
    # base64url: safe inside URLs, JSON and .env files
    return [Convert]::ToBase64String($buf).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$pgPassword = New-Secret 24
$values = [ordered]@{
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
    "S3_ENDPOINT_URL"    = "http://storage:8333"
    "S3_ACCESS_KEY"      = New-Secret 12
    "S3_SECRET_KEY"      = New-Secret 32
    "S3_BUCKET"          = "securesearch-documents"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (Test-Path $target) {
    $existing = Get-Content $target | ForEach-Object { if ($_ -match '^([A-Z0-9_]+)=') { $Matches[1] } }
    $missing = @($values.Keys | Where-Object { $existing -notcontains $_ })
    if ($missing.Count -eq 0) {
        Write-Host ".env already has every key. Nothing changed."
        exit 0
    }
    $raw = [System.IO.File]::ReadAllText($target)
    $append = ""
    if (-not $raw.EndsWith("`n")) { $append += "`n" }
    foreach ($k in $missing) { $append += "$k=$($values[$k])`n" }
    [System.IO.File]::AppendAllText($target, $append, $utf8NoBom)
    Write-Host "Added missing keys to .env (values not shown): $($missing -join ', ')"
    exit 0
}

$lines = Get-Content $example | ForEach-Object {
    if ($_ -match '^([A-Z0-9_]+)=') {
        $key = $Matches[1]
        if ($values.Contains($key)) { return "$key=$($values[$key])" }
    }
    $_
}
# UTF-8 without BOM, LF endings (Docker reads this file)
[System.IO.File]::WriteAllText($target, (($lines -join "`n") + "`n"), $utf8NoBom)
Write-Host ".env created with generated secrets (values not shown)."
Write-Host "Demo-user password = SEED_USER_PASSWORD inside .env (open the file locally to read it)."
