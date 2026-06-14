# QQ Natural Channel

QQ natural-chat channel plugin for OpenClaw via NapCat / OneBot V11 reverse WebSocket.

This plugin now includes an optional `naturalChat` mode for QQ group chats and QQ direct chats.
The goal is natural, lightweight, colloquial chat behavior:

- short replies
- sparse punctuation
- multi-sentence replies split into multiple sends
- gradual clarification instead of one big block

It is designed to feel more like ordinary chat, while still remaining an AI assistant.

Plugin id:

- `qq-natural`

Important:

- This plugin is intended to replace the stock `qq` plugin at runtime.
- Keep `channels.qq` config, but enable `qq-natural` and disable the stock `qq` plugin to avoid channel conflicts.

## What ships in this plugin

- OneBot reverse WebSocket listener for QQ / NapCat
- QQ voice sending with PTT-first fallback to audio/file delivery
- proactive reaction-image / meme sends for strong short-form chat cues (with cooldown)
- QQ mention / reply / image parsing
- follow-up tracking after someone mentions the bot
- optional semantic follow-up judging for same-speaker continuation
- optional macOS idle-sleep prevention via `caffeinate -i`
- optional `naturalChat` mode for QQ conversations
- queue sanitation for QQ delivery recovery
- post-reconnect QQ delivery recovery
- recent-delivery fingerprint dedupe to reduce duplicate replays
- QQ group file system tools (list/upload/download/url/info)

## Native tools

QQ file system tools (backed by OneBot V11 group file APIs):

- `qq_group_files_list`: list group folder (root or `folder_id`)
- `qq_group_file_info`: find a file entry in a folder by `file_id`
- `qq_group_file_url`: get a file download url (requires `busid`)
- `qq_group_file_download`: download file to a local path (via url)
- `qq_group_file_upload`: upload a local file into group file storage
- `qq_packet_status`: check NapCat packetBackend status (required for `qq_group_file_url` / download on NapCat)
- `qq_send_file`: send a local file into the current QQ conversation (tries `file://`, local path, then proxy URL)
- `qq_send_voice`: send spoken reply audio to the current QQ conversation; tries true QQ PTT/voice first, falls back to generic audio/file delivery, and finally sends explicit text if neither transport is available
- `qq_send_mention`: send an `@someone + text` QQ group reply, resolving the target by QQ id or current group nickname/card
- `qq_make_meme`: create a meme image with embedded text; by default preserves original image size and only auto-downscales oversized inputs. Optional sizing controls: `preserve_original_size`, `max_width`, `max_height`

Notes:

- On NapCat, `get_group_file_url` depends on `packetBackend`, so `qq_group_file_url` may fail when `packetBackend` is down.
- `qq_group_file_download` will try `get_group_file_url` first, and fall back to `get_file` (local download by modelId) when possible.
- QQ group-file `file_id` values should be treated as fresh session data. After a QQ/NapCat restart, list the folder again before trying to download.
- If you're unsure, run `qq_packet_status` to see the current `packetBackend` state.

## Recommended config

```json
{
  "channels": {
    "qq": {
      "enabled": true,
      "selfId": "YOUR_QQ_BOT_ID",
      "autoLaunch": true,
      "preventIdleSleep": true,
      "listenHost": "127.0.0.1",
      "listenPort": 8080,
      "websocketPath": "/onebot/v11/ws",
      "blockedUserIds": ["2136387285"],
      "naturalChat": {
        "enabled": true,
        "applyToGroups": true,
        "applyToDirect": true,
        "splitMessages": true,
        "removeDecorativeEmoji": true,
        "hardBannedSymbols": ["☕"]
      },
      "groups": {
        "*": {
          "requireMention": true
        }
      }
    }
  }
}
```

## `naturalChat` options

- `enabled`: master switch
- `applyToGroups`: apply natural chat behavior to QQ groups
- `applyToDirect`: apply natural chat behavior to QQ direct chats
- `splitMessages`: split multi-point replies into multiple sends
- `removeDecorativeEmoji`: strip decorative emoji before sending
- `hardBannedSymbols`: symbols that should never be sent

## Inbound blocking

- `blockedUserIds`: list of QQ user ids that should be ignored completely on inbound

Behavior:

- blocking applies to both QQ group chats and direct chats
- blocked messages are dropped before parse, queueing, follow-up tracking, social-join checks, or reply generation
- blocked users therefore cannot trigger mention-based replies, follow-up replies, or ambient group participation

Useful log line:

- `[qq] ignored inbound message from blocked user: user=... type=... group=...`

## Image handling

- current-turn images are still passed to the model together with the current text context
- recent-media tracking, reply-target image rebinding, and recent-media replay are intentionally disabled
- QQ image context now only comes from images present in the currently accepted inbound message burst

## Portability notes

- The plugin works without local `memory/group-social/...` files.
- If group-social memory exists, the plugin will use it as a higher-priority style reference.
- If it does not exist, the plugin falls back to a built-in QQ casual chat style reference.
- `preventIdleSleep` is macOS-only. On macOS it uses `/usr/bin/caffeinate -i`.

## Recovery and dedupe

This plugin includes extra protection for common QQ / NapCat reconnect problems.

### What it protects against

- NapCat / OneBot disconnecting briefly and reconnecting later
- QQ messages being queued on disk while the bridge is offline
- old queued replies replaying as one large block after reconnect
- duplicate replays of the same QQ reply after a reconnect

### How recovery works

On startup, the plugin sanitizes queued QQ deliveries before normal recovery runs:

- QQ queued text is split into safer single-burst payloads
- unsafe reply markers on old queued payloads are cleared
- QQ targets are normalized before replay

When NapCat / OneBot reconnects, the plugin also runs a QQ-specific post-connect recovery pass.
This helps recover pending QQ deliveries without waiting for a full gateway restart.

### How dedupe works

The plugin records recent outbound QQ delivery fingerprints:

- account id
- target kind
- target id
- text
- media url

If the same QQ delivery is about to be replayed again inside the dedupe window, it is skipped instead of being sent twice.

### What users should expect

- If QQ disconnects briefly, some pending replies may still be recovered later.
- Recovered replies should now replay as short bursts instead of one multi-line block.
- In reconnect scenarios, exact duplicate QQ sends should be reduced.
- The plugin does not guarantee perfect exactly-once delivery in every crash scenario, but it is designed to behave much better than naive replay.

### Useful log lines

These log lines are expected and helpful:

- `[qq] sanitized delivery recovery queue (...)`
- `[qq] post-connect recovery complete (...)`
- `[qq] started macOS idle sleep blocker via caffeinate -i`
- `[qq] media_resolve ...`
- `[qq] reply_target_resolve ...`
- `[qq] burst_compaction ...`
- `[qq] dispatch_gate ...`

If you see repeated `QQ channel is not connected to NapCat / OneBot`, the bridge is still offline and recovery is waiting for reconnect.

### Debug replay tool

The plugin also records QQ ingress debug events to:

- `~/.openclaw/logs/qq-ingress-debug.jsonl`

You can replay a recent QQ conversation with the native tool:

- `qq_debug_replay`
- `qq_debug_inject_message`

Useful parameters:

- `group_id`: inspect one QQ group
- `conversation_key`: inspect an exact QQ conversation
- `minutes`: replay a recent time window
- `around_message_id`: center replay around one message id

For synthetic ingress tests, `qq_debug_inject_message` can inject:

- plain text messages
- reply messages
- @bot messages
- local image files or image URLs

It defaults to dry-run mode so you can inspect media binding and gating without actually sending a QQ reply.

The replay output is meant to explain:

- which media got bound and why
- whether `reply_to` was resolved from buffer or `get_msg`
- whether burst compaction dropped similar image spam
- whether a message was skipped by mention/follow-up gating

## Operational notes

- `naturalChat` changes style, not identity. It should not claim to be human.
- For groups, `requireMention` is still recommended unless you explicitly want ambient participation.
- If you use `autoLaunch`, make sure `executablePath` points to a valid local QQ app.
