#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/probate-bot}"
APP_USER="${APP_USER:-ubuntu}"
DB_PATH="${DB_PATH:-$APP_DIR/data/probate.sqlite}"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nginx git

cd "$APP_DIR"
chmod +x deploy/oracle/*.sh

sudo mkdir -p "$APP_DIR"/{data,logs,exports,backups}
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
.venv/bin/playwright install --with-deps chromium

sudo cp deploy/oracle/systemd/probate-bot.env /etc/default/probate-bot
sudo sed -i "s|__APP_DIR__|$APP_DIR|g" /etc/default/probate-bot
sudo sed -i "s|__DB_PATH__|$DB_PATH|g" /etc/default/probate-bot

sudo cp deploy/oracle/systemd/probate-bot-web.service /etc/systemd/system/
sudo cp deploy/oracle/systemd/probate-bot-sync.service /etc/systemd/system/
sudo cp deploy/oracle/systemd/probate-bot-sync.timer /etc/systemd/system/
sudo cp deploy/oracle/systemd/probate-bot-backup.service /etc/systemd/system/
sudo cp deploy/oracle/systemd/probate-bot-backup.timer /etc/systemd/system/

sudo sed -i "s|__APP_DIR__|$APP_DIR|g" /etc/systemd/system/probate-bot-web.service
sudo sed -i "s|__APP_DIR__|$APP_DIR|g" /etc/systemd/system/probate-bot-sync.service
sudo sed -i "s|__APP_DIR__|$APP_DIR|g" /etc/systemd/system/probate-bot-backup.service

sudo cp deploy/oracle/nginx-probate-bot.conf /etc/nginx/sites-available/probate-bot
sudo sed -i "s|__APP_DIR__|$APP_DIR|g" /etc/nginx/sites-available/probate-bot
sudo ln -sf /etc/nginx/sites-available/probate-bot /etc/nginx/sites-enabled/probate-bot
sudo rm -f /etc/nginx/sites-enabled/default

sudo systemctl daemon-reload
sudo systemctl enable --now probate-bot-web.service
sudo systemctl enable --now probate-bot-sync.timer
sudo systemctl enable --now probate-bot-backup.timer
sudo systemctl restart nginx

echo "Bootstrap complete."
echo "Run an immediate sync with: sudo systemctl start probate-bot-sync.service"
echo "Edit /etc/default/probate-bot to change counties, max results, or sync window."
