# 🚀 Запуск PlayBot: пошаговая инструкция

От нуля до работающего бота в Telegram — примерно 1 час.

## Что понадобится

| Что | Где взять | Цена |
|---|---|---|
| VPS-сервер (Ubuntu 22.04+, 1 CPU / 1 ГБ RAM) | Timeweb, Beget, reg.ru, Aeza и т.п. | ~300–500 ₽/мес |
| Домен (любой, например `playbot.site`) | там же или на reg.ru | ~200–400 ₽/год |
| Токен бота | @BotFather в Telegram | бесплатно |
| Свой Telegram ID | напишите боту @userinfobot | бесплатно |

Telegram открывает мини-аппы **только по HTTPS с настоящим доменом** —
поэтому VPS и домен обязательны. HTTPS-сертификат получим бесплатно
и автоматически (Caddy сделает это сам).

## Шаг 1. Создать бота у @BotFather

1. Откройте @BotFather → `/newbot`
2. Придумайте имя (PlayBot) и юзернейм (например, `playbot_games_bot`)
3. Сохраните **токен** — он понадобится в `.env`

## Шаг 2. Домен → сервер

В панели, где купили домен, создайте **A-запись**: имя `@`, значение —
IP-адрес вашего VPS. Подождите 10–30 минут, пока запись разъедется.

## Шаг 3. Установка на сервере

Подключитесь к VPS по SSH (хостинг даёт логин/пароль) и выполните:

```bash
# базовые пакеты
apt update && apt install -y python3 python3-pip git

# Caddy — веб-сервер с автоматическим HTTPS
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy

# код проекта
cd /opt
git clone https://github.com/daniilrianov45-crypto/Playbot.git playbot
cd playbot
pip3 install -r requirements.txt
```

## Шаг 4. Настройки (.env)

```bash
cp .env.example .env
nano .env
```

Заполните:

```
BOT_TOKEN=токен_от_BotFather
BOT_USERNAME=юзернейм_бота_без_@
WEBAPP_URL=https://ваш-домен
ADMIN_ID=ваш_числовой_id_от_userinfobot
SUPPORT_USERNAME=юзернейм_аккаунта_поддержки_без_@
DEV_MODE=0
```

## Шаг 5. Скачать картинки и анимации подарков

```bash
cd /opt/playbot
export $(grep -v '^#' .env | xargs)
python3 -m scripts.sync_gifts
```

Скрипт скачает арты и Lottie-анимации подарков из каталога.
Если какой-то не скачался — сохраните подарок из Telegram как `.tgs`
в `webapp/gifts/tgs/Название.tgs` и запустите скрипт ещё раз.

## Шаг 6. Автозапуск (systemd)

```bash
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
```

## Шаг 7. HTTPS (Caddy)

```bash
cat > /etc/caddy/Caddyfile <<'CADDY'
ваш-домен {
    reverse_proxy 127.0.0.1:8080
}
CADDY
systemctl restart caddy
```

Замените `ваш-домен` на настоящий (без https://). Caddy сам получит
и будет продлевать сертификат. Через минуту откройте `https://ваш-домен`
в браузере — должен открыться мини-апп.

## Шаг 8. Привязать мини-апп к боту

В @BotFather:

1. `/mybots` → ваш бот → **Bot Settings → Menu Button** →
   указать `https://ваш-домен` — кнопка мини-аппа рядом с полем ввода.
2. `/mybots` → ваш бот → **Bot Settings → Configure Mini App** →
   **Enable Mini App** → указать тот же URL — это включает прямые ссылки
   `t.me/ваш_бот?startapp=ref_123`, на которых работает **рефералка**.

## Шаг 9. Проверка

1. Откройте своего бота → `/start` → «Играть» — должен открыться
   мини-апп со сплэшем, вашим именем и фото в профиле
2. `/addpromo TEST 10 5` → в профиле мини-аппа введите TEST — +10⭐
3. `/inv ваш_id` — бот покажет ваш баланс и инвентарь
4. Откройте бесплатный кейс, сыграйте раунд краша

## Обновление кода

```bash
cd /opt/playbot && git pull && systemctl restart playbot-api playbot-bot
```

## Бэкап

Вся база — один файл `/opt/playbot/playbot.db` (балансы, инвентари,
промокоды). Копируйте его регулярно:

```bash
cp /opt/playbot/playbot.db /root/backup-$(date +%F).db
```

## ⚠️ Перед подключением реальных денег

Приём платежей и вывод ценностей = азартные игры в глазах закона.
До подключения оплаты решите вопрос с юрисдикцией/лицензией и правилами
Telegram — иначе рискуете баном бота и юридическими последствиями.
Пока платежи не подключены, бот полностью безопасен: только виртуальные
звёзды и выдача призов вручную через поддержку.
