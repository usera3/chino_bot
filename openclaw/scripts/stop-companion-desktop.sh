#!/usr/bin/env bash
set -euo pipefail

pkill -f '/Users/mozi100/PycharmProjects/openclaw/companion/vendor/open-llm-vtuber-web/node_modules/.bin/electron-vite dev' || true
pkill -f '/Users/mozi100/PycharmProjects/openclaw/companion/vendor/open-llm-vtuber-web/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron' || true
pkill -f 'vite serve src/renderer --config vite.config.ts --host 127.0.0.1' || true
pkill -f '/Users/mozi100/PycharmProjects/openclaw/companion/vendor/open-llm-vtuber-web/node_modules/electron/dist/Electron.app/Contents/Frameworks/Electron Helper' || true

"/Users/mozi100/PycharmProjects/openclaw/scripts/stop-companion-shell.sh"
