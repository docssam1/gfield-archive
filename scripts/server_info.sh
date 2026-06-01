#!/usr/bin/env bash
set -euo pipefail

cd /home/gfield7265

echo "=============================="
echo "GFIELD HQ SERVER INFO"
echo "=============================="
echo
echo "[1] HOST / USER"
hostname
whoami
pwd
echo
echo "[2] OS"
sed -n '1,8p' /etc/os-release
echo
echo "[3] CPU / MEMORY / DISK"
nproc
free -h
df -h /
echo
echo "[4] INTERNAL / EXTERNAL IP"
hostname -I || true
curl -s ifconfig.me || true
echo
echo
echo "[5] SYSTEMD BOT STATUS"
systemctl is-active gfield-bot.service || true
systemctl status gfield-bot.service --no-pager -l | sed -n '1,15p' || true
echo
echo "=============================="
echo "END"
echo "=============================="
