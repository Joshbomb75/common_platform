#!/usr/bin/env bash
set -euo pipefail

API_DIR="$HOME/nine_scripts"
API_FILE="$API_DIR/nine_api.py"
LOG_FILE="/tmp/nine_api.log"
PID_FILE="/tmp/nine_api.pid"

mkdir -p "$API_DIR"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
    kill "${old_pid}" || true
    sleep 1
  fi
  rm -f "$PID_FILE"
fi

nohup bash -c "source ~/.profile && exec python3 \"$API_FILE\"" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "nine_api started pid=$(cat "$PID_FILE") log=$LOG_FILE"
