#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/mozi100/PycharmProjects/openclaw"
FRONTEND_DIR="$ROOT/companion/vendor/open-llm-vtuber-web"

"$ROOT/scripts/stop-companion-web.sh" >/dev/null 2>&1 || true
"$ROOT/scripts/start-companion-shell.sh"

echo
echo "Starting Open-LLM-VTuber Electron desktop app..."
cd "$FRONTEND_DIR"
OPENCLAW_COMPANION_MODE=pet npm run dev
