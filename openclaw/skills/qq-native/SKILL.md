---
name: qq-native
description: Teach the agent when to use QQ-native OpenClaw tools for user info, group members, likes, QQ media sending, and QQ group-file workflows.
---

# QQ Native Actions

Use these tools when the user asks about QQ-specific actions or information.

## Fusion note

If `chinobot-capability-router` is also loaded, and especially in QQ group `673105016`, prefer the matching `chinobot_*` wrapper whenever one exists.

Common replacements:

- `qq_user_info` -> `chinobot_get_self_info`, `chinobot_get_group_info`, or `chinobot_get_user_info` depending on whether the user means the bot itself, the current QQ group, or another QQ user
- `qq_group_members` -> `chinobot_get_group_members` for the full member list, or `chinobot_get_group_member_info` for one specific member
- `qq_send_like` -> `chinobot_send_like`
- `qq_send_poke` -> `chinobot_send_poke`
- `qq_send_image` -> `chinobot_send_image`
- `qq_send_voice` -> `chinobot_send_voice`
- `qq_send_mention` -> `chinobot_send_mention`
- `qq_recall_message` -> `chinobot_recall_message`
- `qq_group_files_list` -> `chinobot_get_group_files`
- `qq_group_file_info` -> `chinobot_get_group_file_info`
- `qq_group_file_url` -> `chinobot_get_group_file_url`
- `qq_group_file_download` -> `chinobot_download_group_file`
- `qq_group_file_upload` -> `chinobot_upload_group_file`
- `qq_send_file` -> `chinobot_send_file`
- `qq_make_meme` -> `chinobot_make_meme`
- `qq_search_image` -> `chinobot_search_image`
- custom card / poster / chart / quote-image / simple generated visual -> `chinobot_render_html` (no legacy `qq_*` equivalent)
- webpage screenshot / link screenshot -> `chinobot_web_screenshot` (no legacy `qq_*` equivalent)
- `qq_packet_status` -> `chinobot_packet_status`
- `send_email` -> `chinobot_send_email`

## Available tools

- `qq_user_info`
  Use for:
  - "我的QQ号是多少"
  - "你是谁"
  - "查一下这个群的信息"
  - "查一下某个QQ的信息"

- `qq_group_members`
  Use for:
  - "看看这个群有谁"
  - "查一下群成员"
  - "这个群有多少人"

- `qq_send_like`
  Use for:
  - "给我点个赞"
  - "点赞"
  - "给这个QQ点10个赞"

- `qq_send_poke`
  Use for:
  - "戳他一下"
  - "戳一戳这个人"
  - "回戳一下"
  - "轻轻戳一下 ta"

- `qq_send_image`
  Use for:
  - "把这张图发出去"
  - "把这个图片发群里"
  - "把刚找到的图片发一下"
  - "把这个链接对应的图发给当前会话"

- `qq_send_voice`
  Use for:
  - "给我发一条语音"
  - "把这段话做成语音发出来"
  - "发个 QQ 语音"
  - "把刚生成的音频按语音/PTT发给当前会话"

- `qq_send_mention`
  Use for:
  - "艾特 Miko 说今晚来吗"
  - "@一下某个人然后回一句"
  - "在群里点名某个人"
  - "帮我 @ 这个群友回一句"

- `qq_recall_message`
  Use for:
  - "撤回刚才那条"
  - "把上一条消息删掉"
  - "收回刚刚发的内容"
  - "撤回最近两条"

- `qq_group_files_list`
  Use for:
  - "看看这个群有哪些群文件"
  - "先列一下群文件"
  - "找一个群文件"

- `qq_group_file_download`
  Use for:
  - "把这个群文件下载下来"
  - "下载群里的文件"
  - "先下一个群文件再处理"

- `qq_send_file`
  Use for:
  - "把这个文件发回群里"
  - "把本地文件发到当前 QQ 会话"
  - "把刚下载的文件发出去"

- `qq_make_meme`
  Use for:
  - "把这张图做成表情包"
  - "给这图配一句"
  - "上面写XXX下面写YYY"
  - "给当前这张图加字"

- `search_nearby`
  Use for:
  - "XXX附近有什么YYY"
  - "看看XXX附近的餐厅"
  - "YYY周边有什么咖啡店"
  - "上海大学附近的海底捞"

- `send_email`
  Use for:
  - "给xxx@qq.com发邮件"
  - "写封邮件给..."
  - "邮件通知..."
  - "把结果发到邮箱"

## Usage rules

- In QQ group `673105016`, overlapping legacy `qq_*` tools are group-denied once a `chinobot_*` wrapper exists, so use the `chinobot_*` form directly.
- If the user clearly asks for QQ account info, prefer `qq_user_info`, but switch to the matching `chinobot_*` replacement when available.
- If the user asks for a member list or who is in a group, prefer `qq_group_members`, but switch to `chinobot_get_group_members` when available.
- If the user asks for likes, prefer `qq_send_like`.
- If the user asks to 戳一戳 / poke someone in QQ, prefer `qq_send_poke`, but switch to `chinobot_send_poke` when available.
- If the user asks to send an image into the current QQ conversation and you already have an image URL or local path, prefer `qq_send_image`.
- If the user asks to search online for an image and send it into QQ, first use `qq_search_image` to get a usable image URL, then call `qq_send_image` with that URL for the current conversation.
- If the user asks for a QQ voice reply from text, prefer `qq_send_voice` directly and pass the text to it.
- If the user already has an audio URL or local audio path and wants it sent as a QQ voice/PTT, prefer `qq_send_voice`.
- If the user asks to @ a specific person in the current QQ group and say something to them, prefer `qq_send_mention`.
- If the user asks to retract or delete the bot's recent message in the current conversation, prefer `qq_recall_message`.
- If the user asks about QQ group files, start with `qq_group_files_list` unless they already gave you a fresh `file_id` from the current session.
- For QQ group-file download, prefer `qq_group_file_download` over `qq_packet_status`. `qq_packet_status` is diagnostic only; a download may still work even when packetBackend is unavailable.
- For QQ group-file workflows after a QQ/NapCat restart, do not trust an old `file_id`. Call `qq_group_files_list` first, then use the returned current `file_id` immediately.
- If the user asks to send a local file into QQ, prefer `qq_send_file`.
- If the user asks to turn the current/recent QQ image into a meme with overlaid text, prefer `qq_make_meme`. It can reuse the current conversation image even when no explicit image_url/image_path is given.
- `qq_make_meme` keeps the original image size by default. Only very large images are auto-downscaled; if a specific size is needed, pass `max_width` / `max_height`.
- If the user wants a brand-new visual layout generated from instructions rather than an existing image lookup or meme edit, prefer `chinobot_render_html` when available. There is no direct legacy `qq_*` equivalent for this.
- If the user wants a screenshot of a real webpage rather than a generated card, prefer `chinobot_web_screenshot` when available. There is no direct legacy `qq_*` equivalent for this.
- If a QQ file send fails, report the concrete failure reason from the tool result instead of guessing.
- If the user asks for nearby places around a location, prefer `search_nearby`.
- If the user asks to send an email, prefer `send_email`.
- When a matching `chinobot_*` wrapper exists, interpret every `qq_*` preference above as a compatibility fallback only.
- Do not answer these with guesswork or generic chat if a QQ-native tool can answer directly.
- When the user says "给我点个赞", use their current QQ as the target if the tool context already provides it; otherwise ask for the QQ number.
- When the user says "撤回刚才那条", use `qq_recall_message` directly instead of asking for a message ID.
- When the user asks for nearby places, do not guess addresses; use `search_nearby`.
- When the user asks to send an email, generate a concrete subject and body that match the intent, then call `send_email`.

## Response style

- After tool use, answer naturally and briefly.
- Do not mention internal tool names unless the user explicitly asks.
- When doing a multi-step QQ file task, keep the status short: list -> download -> send -> result.
