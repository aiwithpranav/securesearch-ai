#!/usr/bin/env bash
# Checks that this computer is ready to run SecureSearch AI (Linux, macOS, Git Bash).
# Run from anywhere:   bash scripts/check_prereqs.sh
# It only looks: it installs nothing and changes nothing. It never reads the contents of .env. Nothing secret is printed.
problems=0
ok()      { printf '  [ OK ]    %s\n' "$1"; }
note()    { printf '  [ NOTE ]  %s\n' "$1"; }
missing() { problems=$((problems + 1)); printf '  [MISSING] %s\n            -> %s\n' "$1" "$2"; }
have()    { command -v "$1" > /dev/null 2>&1; }
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo
echo "SecureSearch AI: is this computer ready?"
echo "----------------------------------------"

if have docker; then
  ok "Docker is installed"
  if docker info > /dev/null 2>&1; then ok "Docker is running"; else missing "Docker is installed but not running" "Start Docker (Docker Desktop, or the docker service) and run this check again."; fi
  if v="$(docker compose version 2>&1)"; then ok "Docker Compose: $v"; else missing "Docker Compose v2 is missing" "Install the Docker Compose plugin (it is included in Docker Desktop)."; fi
else
  missing "Docker is not installed" "Install Docker from https://docs.docker.com/get-docker/ and start it."
fi

if have git; then ok "$(git --version)"; else missing "Git is not installed" "Install Git from https://git-scm.com/."; fi

if have node; then
  v="$(node --version | sed 's/^v//')"; major="${v%%.*}"; rest="${v#*.}"; minor="${rest%%.*}"
  if [ "$major" -gt 20 ] || { [ "$major" -eq 20 ] && [ "$minor" -ge 9 ]; }; then ok "Node.js $v (needs 20.9 or newer; 24 is what the project is tested with)"; else missing "Node.js $v is too old" "Install Node.js 24 LTS from https://nodejs.org/."; fi
  if have npm; then ok "npm $(npm --version)"; else missing "npm is missing" "Reinstall Node.js from https://nodejs.org/."; fi
else
  missing "Node.js is not installed" "Install Node.js 24 LTS from https://nodejs.org/."
fi

port_busy() {  # prints nothing; returns 0 when something listens on the port
  if have ss; then ss -ltn 2> /dev/null | grep -q ":$1 "
  elif have lsof; then lsof -iTCP:"$1" -sTCP:LISTEN > /dev/null 2>&1
  elif have netstat; then netstat -an 2> /dev/null | grep -E "[:.]$1 .*LISTEN" > /dev/null
  else return 1; fi
}
for entry in "3000:the website" "8000:the API" "8025:the test mailbox"; do
  p="${entry%%:*}"; what="${entry#*:}"
  if port_busy "$p"; then note "Port $p ($what) is already in use. Fine if it is this project already running; otherwise stop the other program."; else ok "Port $p ($what) is free"; fi
done

free_gb="$(df -Pk "$root" 2> /dev/null | awk 'NR==2 {printf "%d", $4/1024/1024}')"
if [ -n "$free_gb" ]; then
  if [ "$free_gb" -ge 15 ]; then ok "Free disk space: ${free_gb} GB (needs about 15 GB for the first build)"; else missing "Only ${free_gb} GB of disk space is free" "Free at least 15 GB (the first build downloads PyTorch and two AI models, about 5 GB)."; fi
fi
if [ -r /proc/meminfo ]; then ram_gb="$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)"
elif have sysctl; then ram_gb="$(sysctl -n hw.memsize 2> /dev/null | awk '{printf "%d", $1/1024/1024/1024}')"
else ram_gb=""; fi
if [ -n "$ram_gb" ]; then
  if [ "$ram_gb" -ge 8 ]; then ok "Memory: ${ram_gb} GB (8 GB or more recommended)"; else note "Memory: ${ram_gb} GB. 8 GB or more is recommended; searching may be slow."; fi
fi

if have curl; then
  for h in registry-1.docker.io huggingface.co download.pytorch.org registry.npmjs.org; do
    if curl -s -o /dev/null --max-time 8 "https://$h"; then ok "Can reach $h"; else missing "Cannot reach $h" "Check your internet connection or proxy. It is needed for the first build and for npm install."; fi
  done
else
  note "curl is not installed, so the internet check was skipped."
fi

if [ -f "$root/docker-compose.yml" ]; then ok "Project files found"; else missing "docker-compose.yml was not found" "Run this from inside the SecureSearch AI folder."; fi
if [ -f "$root/.env" ]; then ok ".env exists (settings and secrets for this computer)"; else note ".env does not exist yet. Next step: bash scripts/setup_env.sh"; fi

echo "----------------------------------------"
if [ "$problems" -eq 0 ]; then echo "READY. Next: see the Quick start in README.md."; exit 0; fi
echo "NOT READY: $problems thing(s) to fix (marked MISSING above). Fix them and run this check again."
exit 1
