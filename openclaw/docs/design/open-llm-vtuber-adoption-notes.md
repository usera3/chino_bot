# Open-LLM-VTuber Adoption Notes

## Why this shell

Open-LLM-VTuber remains the best first body for OpenClaw because it already provides:

- desktop pet mode
- Live2D presentation
- subtitles / bubbles
- input box and voice interaction
- proactive speaking controls
- a local desktop app path on macOS

## Official references

- Project home: https://docs.llmvtuber.com/en/
- Web mode UI and default WebSocket endpoint: https://docs.llmvtuber.com/docs/user-guide/frontend/web/
- Window / desktop pet mode: https://docs.llmvtuber.com/en/docs/user-guide/frontend/electron/
- LLM config and OpenAI-compatible backend support: https://docs.llmvtuber.com/en/docs/user-guide/backend/llm/
- Agent overview: https://docs.llmvtuber.com/en/docs/user-guide/backend/agent
- Backend repository: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber
- Release page (backend zip + macOS Electron app): https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/releases

## Practical notes from the official docs

- The frontend uses a WebSocket connection and the docs mention the default web mode endpoint as `ws://127.0.0.1:12393/client-ws`.
- Desktop pet mode is part of the Electron app and shares state with window mode.
- The project supports OpenAI-compatible LLM APIs, but OpenClaw itself is not a drop-in OpenAI-compatible LLM endpoint.

That means the clean integration path is:

1. Keep OpenClaw as the real brain
2. Keep the current bridge as the source of visible state
3. Later add an adapter that speaks the frontend/backend protocol expected by Open-LLM-VTuber

## What is already done locally

- OpenClaw inner state:
  - `memory/emotion-state.json`
  - `memory/goals.json`
  - `memory/heartbeat-state.json`
  - `memory/reflections/*.jsonl`
- Shell bridge:
  - `scripts/companion-bridge.mjs`
  - `memory/bridge-state.json`
- Main-session mirroring hook:
  - `hooks/bridge-message-sent/`

## Recommended next implementation step

Build a local adapter process that:

- reads `GET /state` or `GET /stream` from `companion-bridge`
- maps bridge fields to Open-LLM-VTuber frontend/backend state
- exposes interrupt / click / wake / sleep back into `companion-bridge`

## Minimal launch order for the future shell stack

1. Start OpenClaw gateway
2. Start `node scripts/companion-bridge.mjs serve --port 18812`
3. Start the Open-LLM-VTuber backend/frontend
4. Start the adapter that translates between them

## Guardrail

Do not move personality, memory, or initiative into the shell.

The shell should remain replaceable.
