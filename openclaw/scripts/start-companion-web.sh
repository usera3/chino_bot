#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/mozi100/PycharmProjects/openclaw"
FRONTEND_DIR="$ROOT/companion/vendor/open-llm-vtuber-web"
RUNTIME_DIR="$ROOT/tmp/companion"
FRONTEND_PID="$RUNTIME_DIR/frontend.pid"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"

mkdir -p "$RUNTIME_DIR"

"$ROOT/scripts/start-companion-shell.sh"

if [[ -f "$FRONTEND_PID" ]] && kill -0 "$(cat "$FRONTEND_PID")" 2>/dev/null; then
  echo "Frontend already running (pid $(cat "$FRONTEND_PID"))"
else
  nohup npm run dev:web -- --host 127.0.0.1 >"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID"
  echo "Started frontend (pid $(cat "$FRONTEND_PID"))"
fi

echo
echo "Web UI:  http://127.0.0.1:3000"
echo "WS URL:  ws://127.0.0.1:12393/client-ws"
echo "Base:    http://127.0.0.1:12393"
echo "Log:     $FRONTEND_LOG"

