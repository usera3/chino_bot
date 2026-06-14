# QQ Channel

QQ channel plugin for OpenClaw via NapCat / OneBot V11 reverse WebSocket.

This plugin now includes an optional `naturalChat` mode for QQ group chats and QQ direct chats.
The goal is natural, lightweight, colloquial chat behavior:

- short replies
- sparse punctuation
- multi-sentence replies split into multiple sends
- gradual clarification instead of one big block

It is designed to feel more like ordinary chat, while still remaining an AI assistant.

## What ships in this plugin

- OneBot reverse WebSocket listener for QQ / NapCat
- QQ text and image sending
- QQ mention / reply / image parsing
- follow-up tracking after someone mentions the bot
- optional semantic follow-up judging for same-speaker continuation
- optional macOS idle-sleep prevention via `caffeinate -i`
- optional `naturalChat` mode for QQ conversations
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

## Portability notes

- The plugin works without local `memory/group-social/...` files.
- If group-social memory exists, the plugin will use it as a higher-priority style reference.
- If it does not exist, the plugin falls back to a built-in QQ casual chat style reference.
- `preventIdleSleep` is macOS-only. On macOS it uses `/usr/bin/caffeinate -i`.

## Operational notes

- `naturalChat` changes style, not identity. It should not claim to be human.
- For groups, `requireMention` is still recommended unless you explicitly want ambient participation.
- If you use `autoLaunch`, make sure `executablePath` points to a valid local QQ app.
