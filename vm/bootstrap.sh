#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash vm/bootstrap.sh https://github.com/<org>/<repo>.git /opt/gfield

REPO_URL="${1:-}"
APP_DIR="${2:-/opt/gfield}"

if [[ -z "${REPO_URL}" ]]; then
  echo "ERROR: missing repo url"
  echo "Usage: bash vm/bootstrap.sh <repo_url> [app_dir]"
  exit 1
fi

sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl

if [[ ! -d "${APP_DIR}/.git" ]]; then
  sudo mkdir -p "${APP_DIR}"
  sudo chown -R "$USER:$USER" "${APP_DIR}"
  git clone "${REPO_URL}" "${APP_DIR}"
else
  echo "Repo already exists: ${APP_DIR}"
fi

cd "${APP_DIR}"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r bot/requirements.txt

mkdir -p gfield_output/logs
echo "Bootstrap complete: ${APP_DIR}"
