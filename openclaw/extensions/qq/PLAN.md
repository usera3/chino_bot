# QQ Channel Migration Plan

Goal:

- make QQ a first-class OpenClaw channel
- reuse the already-proven NapCat / OneBot V11 transport and message parsing ideas from `new-bot`
- do **not** copy `new-bot`'s model brain into OpenClaw

## What to reuse from `new-bot`

Transport / channel-facing logic worth porting:

- `plugins/langchain_chat.py`
  - message segment parsing
  - `@mention` to `[QQ:<id>]`
  - image URL extraction
  - group reply gating (`to_me` / reply-like behavior)
- QQ native action patterns from:
  - `tools/user_info_tool.py`
  - `tools/like_tool.py`
  - later: recall / media helpers

## What not to port

Do not port these into the QQ channel:

- `utils/deepseek_client.py`
- `core/function_calling_agent.py`
- `core/role_agent.py`

Reason:

- once QQ becomes an OpenClaw channel, the "brain" should be OpenClaw itself
- the QQ plugin should stay transport-focused

## Phase 1

Minimal useful channel:

- dedicated QQ extension under `extensions/qq`
- OneBot / NapCat reverse WebSocket listener
- parse inbound text / at / reply / image-url context
- convert inbound QQ message into OpenClaw inbound context
- dispatch through OpenClaw's standard inbound reply pipeline
- send outbound text replies back via OneBot actions

## Phase 2

Improve fidelity:

- richer media sending
- directory lookups
- group policy / allowlist / pairing
- command authz and mention policy parity

## Phase 3

Lift QQ-native powers from `new-bot` into OpenClaw tools:

- user info
- group member listing
- likes
- recalls
- optional TTS / image helpers

## First implementation target

Keep config shape intentionally small:

```json5
{
  channels: {
    qq: {
      enabled: true,
      selfId: "2509109290",
      listenHost: "127.0.0.1",
      listenPort: 8080,
      websocketPath: "/onebot/v11/ws",
      groups: {
        "*": { requireMention: true }
      }
    }
  }
}
```

This mirrors the `new-bot` deployment shape closely enough that migration can stay small.
