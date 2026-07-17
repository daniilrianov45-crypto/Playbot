# MRKT-вотчер

Следит за новыми лотами на [MRKT](https://t.me/mrkt) (реверс-инжиниринг
API, официальной поддержки нет — при изменениях на стороне MRKT скрипт
может сломаться и потребовать правки). Присылает оповещение в отдельный
Telegram-бот, когда лот выставлен на `DISCOUNT_THRESHOLD`% и больше
дешевле floor-цены своей модели/фона.

Только оповещения — автопокупки нет, вы сами решаете, забирать лот или нет.

## Установка на сервере (одной командой)

Требует, чтобы основной GiftSwap (`/opt/playbot`) уже был развёрнут и
обновлён до версии с папкой `sniper/` (`git pull`). Скрипт спросит
`MRKT_API_ID`/`MRKT_API_HASH` (с my.telegram.org), токен бота-оповещателя
(от @BotFather) и ваш Telegram id, поставит venv и зависимости, допишет
`.env` и подготовит systemd-сервис:

```bash
cd /opt/playbot && bash scripts/install-sniper.sh
```

В конце скрипт подскажет два последних ручных шага: вход под своим
Telegram-аккаунтом (`sniper/login.py`, см. ниже) и запуск сервиса.

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
