# Open-LLM-VTuber Adapter

## Purpose

This adapter makes OpenClaw look enough like an Open-LLM-VTuber backend for the frontend shell to connect.

It is a compatibility layer, not a full reimplementation.

## What it does

- exposes a WebSocket endpoint compatible with the frontend default:
  - `ws://127.0.0.1:12393/client-ws`
- exposes a matching HTTP base:
  - `http://127.0.0.1:12393`
- reads OpenClaw bridge state from `memory/bridge-state.json`
- mirrors bridge speech into:
  - `full-text` subtitle updates
  - `audio` messages without audio payload, so the frontend can still append AI chat lines and apply expressions
- maps frontend `text-input` into:
  - `openclaw agent --session-id <main-session-id> --message ...`
- relies on the `bridge-message-sent` hook so real main-session replies flow back into the shell

## Files

- Adapter script: `scripts/open-llm-vtuber-adapter.mjs`
- Adapter config: `companion/open-llm-vtuber-adapter.json`
- Companion bridge: `scripts/companion-bridge.mjs`
- Bridge state: `memory/bridge-state.json`
- Mirror hook: `hooks/bridge-message-sent/`

## Commands

```bash
node scripts/open-llm-vtuber-adapter.mjs ensure
node scripts/open-llm-vtuber-adapter.mjs serve
```

## Launch order

1. Start OpenClaw gateway
2. Start the companion bridge if you want a live HTTP/SSE bridge:
   - `node scripts/companion-bridge.mjs serve --port 18812`
3. Start the adapter:
   - `node scripts/open-llm-vtuber-adapter.mjs serve`
4. Point Open-LLM-VTuber frontend to:
   - WebSocket: `ws://127.0.0.1:12393/client-ws`
   - Base URL: `http://127.0.0.1:12393`

## Current limitations

- No TTS / audio generation yet
- No real chat-history sync from OpenClaw transcript files yet
- `create-new-history` is frontend-compatible but still tied to the single OpenClaw main session
- `interrupt-signal` stops the adapter-side CLI request and mirrors an interrupt event into the bridge, but it is not yet a perfect gateway-native cancel flow

## Model setup

The current repo is already wired to a sample model:

- `modelInfo.url`: `/live2d/shizuku/runtime/shizuku.model3.json`
- `static.live2dDir`: `/Users/mozi100/PycharmProjects/openclaw/companion-assets/live2d`
- `avatarFilename`: `shizuku.png`
- `static.avatarsDir`: `/Users/mozi100/PycharmProjects/openclaw/companion-assets/avatars`

This is a temporary local-only visual body.

OpenClaw's personality is still `智乃`; the model is just the current shell.

Typical future setup:

- `modelInfo.url`: `/live2d/<model-folder>/<model-file>.model3.json`
- `static.live2dDir`: absolute path to the folder containing the Live2D assets
- `avatarFilename`: optional avatar filename
- `static.avatarsDir`: absolute path to the avatar image directory

## Why this shape

OpenClaw remains the brain.

The adapter only:

- translates shell protocol
- forwards user text into the main session
- mirrors visible state back out

That keeps the shell replaceable.

## Convenience scripts

```bash
./scripts/start-companion-shell.sh
./scripts/stop-companion-shell.sh
./scripts/start-companion-web.sh
./scripts/stop-companion-web.sh
./scripts/start-companion-desktop.sh
./scripts/stop-companion-desktop.sh
```

`start-companion-desktop.sh` launches the Electron app in `pet` mode by default, so the character starts as a transparent always-on-top desktop pet rather than a normal app window.
