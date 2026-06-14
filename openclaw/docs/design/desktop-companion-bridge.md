# Desktop Companion Bridge

## Purpose

This bridge exposes a small local interface between OpenClaw's internal state and an external shell such as Open-LLM-VTuber.

It is intentionally simple:

- OpenClaw remains the brain
- the bridge exposes current visible state
- the shell can read state, react to updates, and push small interaction events back

## Files

- State source: `memory/emotion-state.json`
- Goal source: `memory/goals.json`
- Heartbeat source: `memory/heartbeat-state.json`
- Bridge state: `memory/bridge-state.json`
- CLI / server: `scripts/companion-bridge.mjs`

## Commands

```bash
node scripts/companion-bridge.mjs ensure
node scripts/companion-bridge.mjs snapshot
node scripts/companion-bridge.mjs sync
node scripts/companion-bridge.mjs publish --text "..." --source openclaw
node scripts/companion-bridge.mjs clear-speech
node scripts/companion-bridge.mjs event --type click --note "Desktop shell clicked"
node scripts/companion-bridge.mjs serve --port 18812
```

## HTTP API

Default bind:

- `http://127.0.0.1:18812`

Routes:

- `GET /health`
- `GET /state`
- `GET /snapshot`
- `GET /stream` (Server-Sent Events)
- `POST /sync`
- `POST /publish`
- `POST /clear-speech`
- `POST /event`

## Data shape

`GET /state` returns a merged snapshot containing:

- identity summary from `IDENTITY.md`
- current emotion state
- heartbeat state
- current goals
- recommendation from `companion-state`
- shell-facing bridge state

The bridge state includes:

- `mode`
- `scene`
- `expression`
- `motionPreset`
- `statusLine`
- `bubbleText`
- `focusTarget`
- `speaking`
- `lastEvent`

## Intended shell behavior

The shell should map bridge values like this:

- `expression` -> face preset
- `motionPreset` -> idle / gesture animation
- `scene` -> high-level body situation (desk-watch, task-flow, interaction, night-rest, etc.)
- `statusLine` -> small status text or hidden internal state
- `bubbleText` -> speech bubble or subtitle
- `speaking.active` -> mouth animation / TTS gate
- `mode` -> background / watchful / approaching / engaged pose

## Current automatic action bindings

The current bridge derives body behavior from:

- `emotion.mood`
- `heartbeat mode`
- `dayPhase`
- explicit interaction events

Examples:

- `morning` -> `wake-soft`
- `midday/afternoon observe` -> `still-attentive`
- `evening` -> `gentle-nod`
- `late-night` or `tired` -> `slow-blink`
- `click` event -> `gentle-nod`
- `drag` event -> `wake-soft`
- `interrupt` event -> `guarded-soft`

Manual trigger entrypoint:

```bash
node scripts/control-companion-action.mjs list
node scripts/control-companion-action.mjs trigger --preset nod --text "..."
```

## Notes

- The bridge is local-only and loopback-bound by default.
- It is safe to poll, but `GET /stream` is better for a live shell.
- `sync` derives fresh shell state from the current internal state without speaking.
- `publish` is the simplest way for OpenClaw to tell a shell what to say next.
