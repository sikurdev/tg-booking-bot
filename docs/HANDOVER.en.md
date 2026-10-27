# Booking bot handover — client template

**Business:** _______________________
**Telegram bot:** @_______________
**Handover date:** _______________
**Support contact:** _______________

## What you get

1. A Telegram bot for online booking (Ukrainian UI; Russian optional).
2. Instant owner notifications for every new booking and cancellation.
3. `/admin` — today’s and tomorrow’s bookings, cancel (client is notified), block a day or time range.
4. One business YAML config and an SQLite bookings database on the server.

## How clients book

`/start` → service → working date → free slot → name → phone → confirm.
`/my` lists upcoming bookings and allows cancel.

## Changing hours and services

Edit the client YAML (e.g. `config/your_business.yaml`): `working_hours`, `days_off`, `services` (name, duration minutes, price or «Ціна за запитом»). Restart the bot. No code changes required.

## Owner admin

`/admin` (your account only) → today/tomorrow lists → cancel buttons → block via `YYYY-MM-DD` or `YYYY-MM-DD HH:MM — YYYY-MM-DD HH:MM`.

## Keep safe

Never share the bot token or `.env`. Back up `data/bookings.db` and the YAML.
