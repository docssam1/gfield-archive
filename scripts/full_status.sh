#!/usr/bin/env bash
set -euo pipefail

echo "=============================="
echo "GFIELD FULL STATUS"
echo "=============================="
echo
bash scripts/server_info.sh || true
echo
echo "[6] GFIELD HQ GIT STATUS"
cd /home/gfield7265/gfield-hq
git remote -v || true
git status --short || true
git log -5 --oneline || true
echo
echo "[7] TELEGRAM BOT CMD MAP"
grep -n "ALLOWED_CMDS" -A40 bot_runner.py 2>/dev/null || echo "bot_runner.py not found"
grep -n "ALIASES" -A60 bot_runner.py 2>/dev/null || true
echo
bash scripts/folder_list.sh || true
echo
echo "=============================="
echo "END"
echo "=============================="
