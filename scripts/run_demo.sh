#!/usr/bin/env bash
# Launch the demo booking bot (long polling).
# Sources secrets at runtime — never copies the token into the repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SECRETS_FILE="${SECRETS_FILE:-/workspace/s8kur-forge/secrets/demo_bot.env}"
if [[ ! -f "$SECRETS_FILE" ]]; then
  echo "Secrets file not found: $SECRETS_FILE" >&2
  echo "Create it with BOT_TOKEN and OWNER_TELEGRAM_ID (or OWNER_CHAT_ID)." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$SECRETS_FILE"
set +a

export BUSINESS_CONFIG="${BUSINESS_CONFIG:-config/demo_salon.yaml}"
export DATABASE_PATH="${DATABASE_PATH:-data/bookings.db}"
export DEMO="${DEMO:-1}"
export TIMEZONE="${TIMEZONE:-Europe/Kyiv}"

# Map OWNER_TELEGRAM_ID → OWNER_CHAT_ID if only the former is set
if [[ -z "${OWNER_CHAT_ID:-}" && -n "${OWNER_TELEGRAM_ID:-}" ]]; then
  export OWNER_CHAT_ID="$OWNER_TELEGRAM_ID"
fi

if [[ -z "${BOT_TOKEN:-}" ]]; then
  echo "BOT_TOKEN missing after sourcing $SECRETS_FILE" >&2
  exit 1
fi
if [[ -z "${OWNER_CHAT_ID:-}" ]]; then
  echo "OWNER_CHAT_ID / OWNER_TELEGRAM_ID missing after sourcing $SECRETS_FILE" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Missing .venv — run: python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

mkdir -p data
echo "Starting demo bot (DEMO=$DEMO, config=$BUSINESS_CONFIG)…"
exec .venv/bin/python -m bot
