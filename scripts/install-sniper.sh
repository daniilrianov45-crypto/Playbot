#!/usr/bin/env bash
# MRKT-вотчер: установка поверх уже развёрнутого GiftSwap на том же сервере.
# Запускать от root, после того как /opt/playbot уже существует и обновлён
# (git pull) до версии с папкой sniper/.
#
#   cd /opt/playbot && bash scripts/install-sniper.sh
#
# Дописывает .env и поднимает systemd-сервис. Вход под личным Telegram-
# аккаунтом (sniper/login.py) скрипт НЕ делает — это отдельный ручной шаг
# с вводом номера телефона и кода, он описан в подсказке в конце.
set -euo pipefail

cd /opt/playbot

echo "=== MRKT-вотчер: установка ==="
read -rp "MRKT_API_ID (с my.telegram.org -> API development tools): " MRKT_API_ID
read -rp "MRKT_API_HASH (оттуда же): " MRKT_API_HASH
read -rp "Токен нового бота-оповещателя от @BotFather: " ALERT_BOT_TOKEN
read -rp "Ваш Telegram ID (тот же, что ADMIN_ID, узнать: @userinfobot): " ALERT_CHAT_ID
read -rp "Порог оповещения, % ниже floor [10]: " DISCOUNT_THRESHOLD
DISCOUNT_THRESHOLD=${DISCOUNT_THRESHOLD:-10}
read -rp "Порог 'горячего' лота, % ниже floor [20]: " HOT_THRESHOLD
HOT_THRESHOLD=${HOT_THRESHOLD:-20}

echo "--- Окружение вотчера (venv)..."
python3 -m venv sniper/venv
sniper/venv/bin/pip install -q --upgrade pip
sniper/venv/bin/pip install -q -r sniper/requirements.txt

echo "--- Настройки (.env)..."
cat >> .env <<ENV
MRKT_API_ID=$MRKT_API_ID
MRKT_API_HASH=$MRKT_API_HASH
MRKT_SESSION_NAME=mrkt_session
ALERT_BOT_TOKEN=$ALERT_BOT_TOKEN
ALERT_CHAT_ID=$ALERT_CHAT_ID
DISCOUNT_THRESHOLD=$DISCOUNT_THRESHOLD
HOT_THRESHOLD=$HOT_THRESHOLD
POLL_SECONDS=25
ENV

echo "--- Автозапуск (systemd)..."
cat > /etc/systemd/system/giftswap-sniper.service <<'UNIT'
[Unit]
Description=GiftSwap MRKT watcher
After=network.target

[Service]
WorkingDirectory=/opt/playbot
EnvironmentFile=/opt/playbot/.env
ExecStart=/opt/playbot/sniper/venv/bin/python3 -m sniper.watcher
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload

echo ""
echo "=== Пакеты и сервис готовы! Остался один ручной шаг ==="
echo "1. Войдите под своим Telegram-аккаунтом (номер и код вводите только тут):"
echo "     source sniper/venv/bin/activate"
echo "     set -a; source .env; set +a"
echo "     python3 -m sniper.login"
echo "2. После успешного входа запустите сервис:"
echo "     systemctl enable --now giftswap-sniper"
echo "     journalctl -u giftswap-sniper -n 20 --no-pager"
echo "   Должно прийти сообщение \"👀 Вотчер MRKT запущен\" в бот-оповещатель."
