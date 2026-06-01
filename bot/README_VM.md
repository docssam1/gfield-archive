# GFIELD VM Quick Start

## 1) Bootstrap
```bash
bash vm/bootstrap.sh https://github.com/<ORG>/<REPO>.git /opt/gfield
```

## 2) Configure env
```bash
cd /opt/gfield
cp bot/.env.example bot/.env
nano bot/.env
```

Required:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_CHAT_ID`
- `OPENAI_API_KEY`
- `GOOGLE_APPLICATION_CREDENTIALS` (optional for deferred mode, required for full Drive expansion)

## 3) Install systemd units
```bash
sudo cp vm/gfield-bot.service /etc/systemd/system/
sudo cp vm/gfield-preview.service /etc/systemd/system/
sudo cp vm/gfield-preview.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gfield-bot.service
sudo systemctl enable --now gfield-preview.timer
```

## 4) Check status
```bash
sudo systemctl status gfield-bot.service
sudo systemctl status gfield-preview.timer
```

## 5) Telegram commands
- `/status`
- `/run_preview`
- `/last_report`
- `/run 서버정보`
- `/run 폴더목록`
- `/run 전체상태`

Conversational aliases (without slash command):
- `서버정보`
- `폴더목록`
- `전체상태`

## 6) Enable run scripts
```bash
cd /opt/gfield
chmod +x scripts/*.sh
sudo systemctl restart gfield-bot.service
```

Bot policy:
- Preview-only mode
- DB update disabled
- Parent sending disabled
