#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/mozi100/PycharmProjects/openclaw"
RUNTIME_DIR="$ROOT/tmp/companion"
FRONTEND_PID="$RUNTIME_DIR/frontend.pid"

if [[ -f "$FRONTEND_PID" ]]; then
  pid="$(cat "$FRONTEND_PID")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "Stopped frontend (pid $pid)"
  else
    echo "Frontend not running (stale pid $pid)"
  fi
  rm -f "$FRONTEND_PID"
else
  echo "Frontend not running (no pid file)"
fi

"$ROOT/scripts/stop-companion-shell.sh"

