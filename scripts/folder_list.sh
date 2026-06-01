#!/usr/bin/env bash
set -euo pipefail

echo "=============================="
echo "GFIELD FOLDER LIST"
echo "=============================="
echo
echo "[1] HQ REPO TREE"
find /home/gfield7265/gfield-hq -maxdepth 3 -type d \
  \( -name ".git" -o -name ".ssh" -o -name "__pycache__" \) -prune -o \
  -type d -print | sort | sed -n '1,160p'
echo
echo "[2] SCRIPTS"
find /home/gfield7265/gfield-hq/scripts -maxdepth 1 -type f -printf "%f\n" 2>/dev/null | sort
echo
echo "[3] PROJECT FOLDERS"
find /home/gfield7265/gfield-projects -maxdepth 3 \
  \( -name ".git" -o -name "__pycache__" \) -prune -o \
  -print 2>/dev/null | sort | sed -n '1,220p'
echo
echo "=============================="
echo "END"
echo "=============================="
