# Checks that this computer is ready to run SecureSearch AI (Windows PowerShell).
# Run from the repository root:   powershell -ExecutionPolicy Bypass -File scripts/check_prereqs.ps1
# It only looks: it installs nothing and changes nothing. It prints what is fine, what is missing and how to fix it.
# Nothing secret is printed (it never reads the contents of .env). Copy the whole output if you ask someone for help.
$ErrorActionPreference = "Continue"
$problems = 0
function Ok($text) { Write-Host ("  [ OK ]    " + $text) -ForegroundColor Green }
function Missing($text, $fix) { $script:problems++; Write-Host ("  [MISSING] " + $text) -ForegroundColor Red; Write-Host ("            -> " + $fix) }
function Warn($text) { Write-Host ("  [ NOTE ]  " + $text) -ForegroundColor Yellow }
function Have($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host ""
Write-Host "SecureSearch AI: is this computer ready?"
Write-Host "----------------------------------------"

# Docker
if (Have "docker") {
    Ok "Docker is installed"
    $info = & docker info 2>&1
    if ($LASTEXITCODE -eq 0) { Ok "Docker is running" } else { Missing "Docker is installed but not running" "Open Docker Desktop and wait until it says it is running, then run this check again." }
    $compose = & docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) { Ok ("Docker Compose: " + ($compose -join " ")) } else { Missing "Docker Compose v2 is missing" "Update Docker Desktop (it includes Compose)." }
} else {
    Missing "Docker is not installed" "Install Docker Desktop from https://www.docker.com/products/docker-desktop/ and start it."
}

# Git
if (Have "git") { Ok ((& git --version) -join " ") } else { Missing "Git is not installed" "Install Git from https://git-scm.com/download/win (it also gives you Git Bash, used by the backup scripts)." }

# Git Bash (for scripts/backup.sh and restore.sh)
$gitBash = @("C:\Program Files\Git\bin\bash.exe", "C:\Program Files (x86)\Git\bin\bash.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($gitBash) { Ok "Git Bash found (for the backup and restore scripts)" } else { Warn "Git Bash was not found. It is only needed for backup.sh and restore.sh." }

# Node.js
if (Have "node") {
    $v = (& node --version).TrimStart("v")
    $major = [int]($v.Split(".")[0]); $minor = [int]($v.Split(".")[1])
    if ($major -gt 20 -or ($major -eq 20 -and $minor -ge 9)) { Ok ("Node.js " + $v + " (needs 20.9 or newer; 24 is what the project is tested with)") } else { Missing ("Node.js " + $v + " is too old") "Install Node.js 24 LTS from https://nodejs.org/." }
    if (Have "npm") { Ok ("npm " + (& npm --version)) } else { Missing "npm is missing" "Reinstall Node.js from https://nodejs.org/." }
} else {
    Missing "Node.js is not installed" "Install Node.js 24 LTS from https://nodejs.org/."
}

# Ports
foreach ($p in @(@(3000, "the website"), @(8000, "the API"), @(8025, "the test mailbox"))) {
    $busy = Get-NetTCPConnection -LocalPort $p[0] -State Listen -ErrorAction SilentlyContinue
    if ($busy) { Warn ("Port " + $p[0] + " (" + $p[1] + ") is already in use. That is fine if it is this project already running; otherwise stop the other program.") } else { Ok ("Port " + $p[0] + " (" + $p[1] + ") is free") }
}

# Disk and memory
$drive = (Get-Location).Drive
if ($drive) {
    $freeGb = [math]::Round($drive.Free / 1GB)
    if ($freeGb -ge 15) { Ok ("Free disk space: " + $freeGb + " GB (needs about 15 GB for the first build)") } else { Missing ("Only " + $freeGb + " GB of disk space is free") "Free at least 15 GB (the first build downloads PyTorch and two AI models, about 5 GB)." }
}
$ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
if ($ramGb -ge 8) { Ok ("Memory: " + $ramGb + " GB (8 GB or more recommended)") } else { Warn ("Memory: " + $ramGb + " GB. 8 GB or more is recommended; searching may be slow.") }

# Internet (needed for the first build only)
foreach ($h in @("registry-1.docker.io", "huggingface.co", "download.pytorch.org", "registry.npmjs.org")) {
    $reach = $false
    try { $reach = (Test-NetConnection -ComputerName $h -Port 443 -WarningAction SilentlyContinue -InformationLevel Quiet) } catch { }
    if ($reach) { Ok ("Can reach " + $h) } else { Missing ("Cannot reach " + $h) "Check your internet connection or proxy. It is needed for the first build and for npm install." }
}

# Project files
$root = Split-Path -Parent $PSScriptRoot
if (Test-Path (Join-Path $root "docker-compose.yml")) { Ok "Project files found" } else { Missing "docker-compose.yml was not found" "Run this from inside the SecureSearch AI folder." }
if (Test-Path (Join-Path $root ".env")) { Ok ".env exists (settings and secrets for this computer)" } else { Warn ".env does not exist yet. Next step: powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1" }

Write-Host "----------------------------------------"
if ($problems -eq 0) {
    Write-Host "READY. Next: see the Quick start in README.md." -ForegroundColor Green
    exit 0
} else {
    Write-Host ("NOT READY: " + $problems + " thing(s) to fix (marked MISSING above). Fix them and run this check again.") -ForegroundColor Red
    exit 1
}
