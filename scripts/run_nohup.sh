#!/usr/bin/env bash
# Background launch on the box via nohup. Logs to data/bot.log (no secrets).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data
LOG="${LOG_FILE:-data/bot.log}"
nohup "$ROOT/scripts/run_demo.sh" >>"$LOG" 2>&1 &
echo $! > data/bot.pid
echo "PID $(cat data/bot.pid) — log: $LOG"
