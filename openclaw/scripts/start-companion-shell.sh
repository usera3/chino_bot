#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/mozi100/PycharmProjects/openclaw"
RUNTIME_DIR="$ROOT/tmp/companion"
BRIDGE_PID="$RUNTIME_DIR/bridge.pid"
ADAPTER_PID="$RUNTIME_DIR/adapter.pid"
BRIDGE_LOG="$RUNTIME_DIR/bridge.log"
ADAPTER_LOG="$RUNTIME_DIR/adapter.log"

mkdir -p "$RUNTIME_DIR"

if [[ -f "$BRIDGE_PID" ]] && kill -0 "$(cat "$BRIDGE_PID")" 2>/dev/null; then
  echo "Bridge already running (pid $(cat "$BRIDGE_PID"))"
else
  nohup node "$ROOT/scripts/companion-bridge.mjs" serve --port 18812 >"$BRIDGE_LOG" 2>&1 &
  echo $! >"$BRIDGE_PID"
  echo "Started bridge (pid $(cat "$BRIDGE_PID"))"
fi

if [[ -f "$ADAPTER_PID" ]] && kill -0 "$(cat "$ADAPTER_PID")" 2>/dev/null; then
  echo "Adapter already running (pid $(cat "$ADAPTER_PID"))"
else
  nohup node "$ROOT/scripts/open-llm-vtuber-adapter.mjs" serve >"$ADAPTER_LOG" 2>&1 &
  echo $! >"$ADAPTER_PID"
  echo "Started adapter (pid $(cat "$ADAPTER_PID"))"
fi

echo
echo "Bridge:  http://127.0.0.1:18812/state"
echo "Adapter: ws://127.0.0.1:12393/client-ws"
echo "Adapter: http://127.0.0.1:12393"
echo "Logs:    $BRIDGE_LOG"
echo "Logs:    $ADAPTER_LOG"

