# notification_bot

Telegram bot that posts every **newly-created application** to the operators'
group with two inline buttons:

- ✅ **HEMISga qo'shildi**
- ❌ **Qo'shilmadi**

Pressing a button asks for confirmation ("Rostdan amalni tasdiqlaysizmi?"),
then writes the decision back to the admission system
(`hemis_status` on the application), and edits the message to show who/when.

Runs **outside docker** as a host `systemd` service. It talks to the backend
over the REST API and receives new-application pushes over a small HTTP
ingest endpoint.

```
backend (docker) ──push /ingest──▶ notification_bot (host) ──▶ Telegram group
        ▲                                    │
        └──────── POST /applications/{id}/hemis ◀── ✅/❌
```

## Architecture

- `main.py` — starts python-telegram-bot (polling) **and** an aiohttp ingest
  server in one asyncio loop.
- `bot/ingest.py` — `POST /ingest` (secret-protected): formats + posts the
  application to the group.
- `bot/handlers.py` — ✅/❌ callbacks + confirm step; calls the API on confirm.
- `bot/api_client.py` — service-account login + `set_hemis_status`.
- `bot/formatting.py` — message text + keyboards.

## Setup (server)

```bash
cd /home/ubuntu/xiu/qabul_fastapi/notification_bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # then fill it in
```

### Fill `.env`
- `BOT_TOKEN` — from @BotFather.
- `GROUP_CHAT_ID` — add the bot to the group as an admin, run `/id` in the
  group, copy the value (negative number).
- `API_BASE_URL` — `https://qabul.xiuedu.uz/api/v1`.
- `SERVICE_PHONE` / `SERVICE_PASSWORD` — a dedicated **admin** account in the
  system (not an operator — operators only see their own data).
- `INGEST_SECRET` — a long random string; **must equal** the backend's
  `NOTIFY_BOT_SECRET`.

### Backend side (docker `.env`)
```
NOTIFY_BOT_URL=http://host.docker.internal:8090/ingest
NOTIFY_BOT_SECRET=<same as INGEST_SECRET>
```
`docker-compose.yml` already maps `host.docker.internal` for the backend.
Apply with `docker compose up -d --force-recreate backend`.

### Run via systemd
```bash
sudo cp notification_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now notification_bot
journalctl -u notification_bot -f
```

## Local run
```bash
.venv/bin/python main.py
```

## Notes
- Buttons are open to **anyone in the group**; the presser's Telegram name is
  recorded as `marked_by`.
- New applications default to `qoshilmadi` (not in HEMIS) until someone
  presses ✅.
