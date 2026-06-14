#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/mozi100/PycharmProjects/openclaw"
RUNTIME_DIR="$ROOT/tmp/companion"

stop_pid_file() {
  local pid_file="$1"
  local label="$2"
  if [[ ! -f "$pid_file" ]]; then
    echo "$label not running (no pid file)"
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "Stopped $label (pid $pid)"
  else
    echo "$label not running (stale pid $pid)"
  fi
  rm -f "$pid_file"
}

stop_pid_file "$RUNTIME_DIR/adapter.pid" "adapter"
stop_pid_file "$RUNTIME_DIR/bridge.pid" "bridge"

pkill -f '/Users/mozi100/PycharmProjects/openclaw/scripts/open-llm-vtuber-adapter.mjs serve' || true
pkill -f '/Users/mozi100/PycharmProjects/openclaw/scripts/companion-bridge.mjs serve --port 18812' || true
