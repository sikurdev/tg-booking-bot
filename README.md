# Telegram booking bot

Reusable long-polling booking bot for small local businesses (salons, barbers, car services, and similar). One YAML file per client.

Live demo: [t.me/s8kur_demo_booking_bot](https://t.me/s8kur_demo_booking_bot)

## Features

- Button-driven booking flow (service, day, time, name, phone)
- Owner notifications for new bookings and cancellations
- Admin view for today/tomorrow, cancel booking, block time
- Client "my bookings" with cancel
- Persistent FSM storage (survives restarts)
- Demo mode that mirrors owner notifications to the booker
- Ukrainian and Russian UI strings

## Stack

- Python 3.13+
- aiogram 3
- aiosqlite / SQLite
- Long polling (no webhook required)

## Quick start

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Get your numeric Telegram user id (for example via [@userinfobot](https://t.me/userinfobot)).
3. Configure environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# edit .env: BOT_TOKEN, OWNER_CHAT_ID (or OWNER_TELEGRAM_ID)
```

4. Run:

```bash
.venv/bin/python -m bot
```

Or use the helper scripts under `scripts/` (see `scripts/run_demo.sh` and `scripts/ensure_running.sh`).

## Config

| Variable | Required | Meaning |
| --- | --- | --- |
| `BOT_TOKEN` | yes | Telegram bot token from BotFather |
| `OWNER_CHAT_ID` or `OWNER_TELEGRAM_ID` | yes | Owner numeric Telegram user id |
| `BUSINESS_CONFIG` | no | Path to business YAML (default `config/demo_salon.yaml`) |
| `DATABASE_PATH` | no | SQLite path (default `data/bookings.db`) |
| `DEMO` | no | Set to `1` to mirror owner notifications to the booker |
| `TIMEZONE` | no | IANA timezone (default `Europe/Kyiv`) |

Business name, address, hours, services, and prices live in the YAML file. Swap the file to rebrand for another client.

## Tests

```bash
.venv/bin/python -m pytest -q
```

## License

MIT. Copyright (c) 2026 sikurdev.
