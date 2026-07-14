#!/usr/bin/env bash
# PlayBot: установка одной командой на чистый Ubuntu 22.04+ (запускать от root).
#
#   bash <(curl -sL https://raw.githubusercontent.com/daniilrianov45-crypto/Playbot/main/scripts/install.sh)
#
# Скрипт спросит настройки, поставит всё сам и запустит бота.
set -euo pipefail

echo "=== PlayBot: установка ==="
read -rp "Домен (например playbot.site, уже направлен на этот сервер): " DOMAIN
read -rp "BOT_TOKEN от @BotFather: " BOT_TOKEN
read -rp "Юзернейм бота без @: " BOT_USERNAME
read -rp "Ваш Telegram ID (узнать: @userinfobot): " ADMIN_ID
read -rp "Юзернейм поддержки без @ (можно свой): " SUPPORT_USERNAME

echo "--- Пакеты..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip git curl debian-keyring \
  debian-archive-keyring apt-transport-https >/dev/null

echo "--- Caddy (HTTPS)..."
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq && apt-get install -y -qq caddy >/dev/null
fi

echo "--- Код проекта..."
mkdir -p /opt && cd /opt
if [ -d playbot ]; then
  cd playbot && git pull
else
  git clone https://github.com/daniilrianov45-crypto/Playbot.git playbot
  cd playbot
fi
pip3 install -q -r requirements.txt

echo "--- Настройки (.env)..."
cat > .env <<ENV
BOT_TOKEN=$BOT_TOKEN
BOT_USERNAME=$BOT_USERNAME
WEBAPP_URL=https://$DOMAIN
ADMIN_ID=$ADMIN_ID
SUPPORT_USERNAME=$SUPPORT_USERNAME
DEV_MODE=0
ENV
chmod 600 .env

echo "--- Картинки и анимации подарков..."
set -a; source .env; set +a
python3 -m scripts.sync_gifts || echo "(часть подарков не скачалась — можно доложить позже)"

echo "--- Автозапуск (systemd)..."
cat > /etc/systemd/system/playbot-api.service <<'UNIT'
[Unit]
Description=PlayBot API
After=network.target

[Service]
WorkingDirectory=/opt/playbot
EnvironmentFile=/opt/playbot/.env
ExecStart=/usr/bin/python3 -m uvicorn server.main:app --host 127.0.0.1 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/playbot-bot.service <<'UNIT'
[Unit]
Description=PlayBot Telegram bot
After=network.target

[Service]
WorkingDirectory=/opt/playbot
EnvironmentFile=/opt/playbot/.env
ExecStart=/usr/bin/python3 -m bot.main
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now playbot-api playbot-bot

echo "--- HTTPS (Caddy)..."
cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
    reverse_proxy 127.0.0.1:8080
}
CADDY
systemctl restart caddy

echo ""
echo "=== ГОТОВО! ==="
echo "1. Проверьте: https://$DOMAIN"
echo "2. В @BotFather: /mybots -> Bot Settings -> Menu Button -> https://$DOMAIN"
echo "3. Там же: Configure Mini App -> Enable -> https://$DOMAIN (для рефералки)"
echo "4. В боте: /start -> Играть"
