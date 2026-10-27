#!/usr/bin/env bash
# Idempotent: start the demo supervisor if it is not already running, print status.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATA_DIR="${DATA_DIR:-$ROOT/data}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
mkdir -p "$DATA_DIR" "$LOG_DIR"

SUPERVISOR_PID_FILE="${SUPERVISOR_PID_FILE:-$DATA_DIR/supervisor.pid}"
BOT_PID_FILE="${BOT_PID_FILE:-$DATA_DIR/bot.pid}"
LOCK_FILE="${LOCK_FILE:-$DATA_DIR/demo.lock}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/demo.log}"

is_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

supervisor_pid=""
if [[ -f "$SUPERVISOR_PID_FILE" ]]; then
  supervisor_pid="$(tr -d '[:space:]' <"$SUPERVISOR_PID_FILE" || true)"
fi

if is_alive "$supervisor_pid"; then
  # Confirm it looks like our supervise.sh (best-effort).
  cmd="$(ps -p "$supervisor_pid" -o args= 2>/dev/null || true)"
  bot_pid=""
  if [[ -f "$BOT_PID_FILE" ]]; then
    bot_pid="$(tr -d '[:space:]' <"$BOT_PID_FILE" || true)"
  fi
  echo "status=running supervisor_pid=$supervisor_pid bot_pid=${bot_pid:-unknown} lock=$LOCK_FILE log=$LOG_FILE"
  echo "cmd=$cmd"
  exit 0
fi

# Stale pidfile
rm -f "$SUPERVISOR_PID_FILE"

# If lock is held by a live process we didn't track, report and exit.
if [[ -f "$LOCK_FILE" ]]; then
  # flock holders aren't always discoverable; try starting — supervise.sh exits 0 if locked.
  :
fi

nohup "$ROOT/scripts/supervise.sh" >/dev/null 2>&1 &
# supervise.sh writes its own pidfile after acquiring the lock
for _ in 1 2 3 4 5 6 7 8 9 10; do
  sleep 0.2
  if [[ -f "$SUPERVISOR_PID_FILE" ]]; then
    supervisor_pid="$(tr -d '[:space:]' <"$SUPERVISOR_PID_FILE" || true)"
    if is_alive "$supervisor_pid"; then
      bot_pid=""
      if [[ -f "$BOT_PID_FILE" ]]; then
        bot_pid="$(tr -d '[:space:]' <"$BOT_PID_FILE" || true)"
      fi
      echo "status=started supervisor_pid=$supervisor_pid bot_pid=${bot_pid:-starting} lock=$LOCK_FILE log=$LOG_FILE"
      exit 0
    fi
  fi
done

echo "status=error failed to start supervisor; see $LOG_FILE" >&2
exit 1
