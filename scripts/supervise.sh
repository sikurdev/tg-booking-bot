#!/usr/bin/env bash
# Restart the demo bot on exit with exponential backoff.
# Holds an exclusive flock so only one instance can poll the token.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATA_DIR="${DATA_DIR:-$ROOT/data}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
mkdir -p "$DATA_DIR" "$LOG_DIR"

LOCK_FILE="${LOCK_FILE:-$DATA_DIR/demo.lock}"
SUPERVISOR_PID_FILE="${SUPERVISOR_PID_FILE:-$DATA_DIR/supervisor.pid}"
BOT_PID_FILE="${BOT_PID_FILE:-$DATA_DIR/bot.pid}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/demo.log}"
LOG_MAX_BYTES="${LOG_MAX_BYTES:-5242880}"  # 5 MiB
BACKOFF_START="${BACKOFF_START:-1}"
BACKOFF_MAX="${BACKOFF_MAX:-60}"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date -Iseconds) supervise: another instance holds $LOCK_FILE — exiting" >&2
  exit 0
fi

echo $$ >"$SUPERVISOR_PID_FILE"
trap 'rm -f "$SUPERVISOR_PID_FILE" "$BOT_PID_FILE"; flock -u 9' EXIT

rotate_log() {
  if [[ -f "$LOG_FILE" ]]; then
    local size
    size="$(wc -c <"$LOG_FILE" | tr -d ' ')"
    if [[ "$size" -gt "$LOG_MAX_BYTES" ]]; then
      mv -f "$LOG_FILE" "${LOG_FILE}.1"
      : >"$LOG_FILE"
      echo "$(date -Iseconds) supervise: rotated log (was ${size} bytes)" >>"$LOG_FILE"
    fi
  fi
}

backoff="$BACKOFF_START"
echo "$(date -Iseconds) supervise: started pid=$$ lock=$LOCK_FILE log=$LOG_FILE" >>"$LOG_FILE"

while true; do
  rotate_log
  echo "$(date -Iseconds) supervise: launching bot…" >>"$LOG_FILE"
  # run_demo.sh execs python; as a background child of this shell it stays our child.
  "$ROOT/scripts/run_demo.sh" >>"$LOG_FILE" 2>&1 &
  bot_pid=$!
  echo "$bot_pid" >"$BOT_PID_FILE"
  set +e
  wait "$bot_pid"
  code=$?
  set -e
  rm -f "$BOT_PID_FILE"
  echo "$(date -Iseconds) supervise: bot exited code=$code; restart in ${backoff}s" >>"$LOG_FILE"
  sleep "$backoff"
  if (( backoff < BACKOFF_MAX )); then
    next=$((backoff * 2))
    if (( next > BACKOFF_MAX )); then
      backoff=$BACKOFF_MAX
    else
      backoff=$next
    fi
  fi
done
