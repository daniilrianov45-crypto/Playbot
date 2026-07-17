# MRKT-вотчер

Следит за новыми лотами на [MRKT](https://t.me/mrkt) (реверс-инжиниринг
API, официальной поддержки нет — при изменениях на стороне MRKT скрипт
может сломаться и потребовать правки). Присылает оповещение в отдельный
Telegram-бот, когда лот выставлен на `DISCOUNT_THRESHOLD`% и больше
дешевле floor-цены своей модели/фона.

Только оповещения — автопокупки нет, вы сами решаете, забирать лот или нет.

## Установка на сервере

```bash
cd /opt/playbot
python3 -m venv sniper/venv
source sniper/venv/bin/activate
pip install -r sniper/requirements.txt
```

## Настройка (.env)

Допишите в `/opt/playbot/.env`:

```
MRKT_API_ID=...          # с my.telegram.org -> API development tools
MRKT_API_HASH=...        # оттуда же
MRKT_SESSION_NAME=mrkt_session
ALERT_BOT_TOKEN=...      # токен нового бота от @BotFather (/newbot)
ALERT_CHAT_ID=...        # ваш Telegram id (тот же, что ADMIN_ID)
DISCOUNT_THRESHOLD=10    # % ниже floor — с этого порога шлём оповещение
HOT_THRESHOLD=20         # % ниже floor — помечаем 🔥 как особо выгодное
POLL_SECONDS=25          # как часто проверять
```

## Первый запуск — вход под своим Telegram-аккаунтом

Делается **один раз**, вручную, прямо в терминале (номер телефона и код
из Telegram вводите только здесь — я их не вижу и не запрашиваю):

```bash
cd /opt/playbot
source sniper/venv/bin/activate
set -a; source .env; set +a
python3 -m sniper.login
```

Спросит номер телефона, затем код из Telegram (придёт как обычное
сообщение от Telegram). После успешного входа появится файл
`sniper/mrkt_session.session` — повторно входить не нужно.

## Постоянная работа (systemd)

```bash
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
systemctl enable --now giftswap-sniper
journalctl -u giftswap-sniper -n 30 --no-pager
```

При старте бот пришлёт «👀 Вотчер MRKT запущен» — если это сообщение
пришло, всё поднялось корректно.

## Важно

- Это неофициальный, реверс-инжиниренный API — Тelegram/MRKT ничего не
  гарантируют, поведение может поменяться без предупреждения.
- Сортировка "по времени выставления" (свежие лоты) — предположение по
  документации сообщества, направление (новые сверху/снизу) не
  подтверждено официально. Проверьте по первым оповещениям — если
  постоянно приходят одни и те же старые лоты, напишите, поправим логику.
- Порог `DISCOUNT_THRESHOLD` и `HOT_THRESHOLD` можно менять в `.env` и
  перезапускать сервис — код трогать не нужно.
