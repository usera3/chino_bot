---
name: bridge-message-sent
description: "Mirror successful main-session outbound text into the desktop companion bridge"
homepage: https://docs.openclaw.ai/automation/hooks
metadata:
  {
    "openclaw":
      {
        "emoji": "🪞",
        "events": ["message:sent"],
        "requires": { "bins": ["node"] },
      },
  }
---

# Bridge Message Sent Hook

Mirrors successful outbound text from the main session into the local desktop companion bridge.

## What It Does

When OpenClaw successfully sends a text reply from the primary main session:

1. Checks that the session is `agent:main:main`
2. Ignores empty output and `HEARTBEAT_OK`
3. Calls `scripts/companion-bridge.mjs publish`
4. Updates the bridge so a desktop shell can show the same line as a speech bubble / subtitle

## Why It Exists

This keeps the future desktop shell in sync with what OpenClaw actually says, without changing the core reply pipeline.

## Guardrails

- Only mirrors the main session
- Does not mirror silent heartbeat acknowledgements
- Does not send anything externally

