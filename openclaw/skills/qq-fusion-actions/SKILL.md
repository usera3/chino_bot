---
name: qq-fusion-actions
description: Preferred QQ action routing for the OpenClaw + chino_bot fusion setup in 次元复苏二群. Use chino-style wrappers first, and only fall back to legacy qq-native tools when no wrapper exists.
---

# QQ Fusion Actions

Use this skill for QQ actions inside the fusion setup, especially in group `673105016`.

## Core rule

- Think in `chinobot_*` names first.
- Treat matching legacy `qq_*` tools as compatibility fallbacks only.
- In group `673105016`, most overlapping legacy `qq_*` tools are already group-denied, so planning in old tool names is usually wrong.

## Preferred fused tools

- `chinobot_get_self_info`
  Use when the user asks who the current QQ bot is, what QQ number the bot has, or similar self/account questions.

- `chinobot_get_group_info`
  Use for current-group metadata such as group name, member count, or basic group status.

- `chinobot_get_user_info`
  Use for QQ user/profile lookups when the user asks who someone is or wants current-sender info.

- `chinobot_analyze_avatar`
  Use when the user wants you to look at a QQ avatar, judge someone's profile picture, or inspect your own avatar. It defaults to the current sender, and `self=true` means the bot's own avatar.

- `chinobot_get_group_members`
  Use when the user asks for the member list of the current QQ group, or asks who is in the group in general.

- `chinobot_get_group_member_info`
  Use for member lookup inside the current QQ group, especially when the user means one specific person.

- `chinobot_send_like`
  Use for likes.

- `chinobot_set_group_ban`
  Use to mute or unmute one member in the current QQ group. If `user_id` is omitted, it can default to the current sender when context exists. `duration_seconds=0` means lift the mute.

- `chinobot_set_group_whole_ban`
  Use to turn QQ whole-group mute on or off for the current group.

- `chinobot_set_group_kick`
  Use to remove a member from the current QQ group. If `user_id` is omitted, it can default to the current sender when context exists.

- `chinobot_set_group_admin`
  Use to grant or revoke QQ group admin status. If `user_id` is omitted, it can default to the current sender when context exists.

- `chinobot_set_group_special_title`
  Use to set or clear one member's QQ group special title. If `user_id` is omitted, it can default to the current sender when context exists. An empty `special_title` clears it.

- `chinobot_send_poke`
  Use when the user wants to 戳一戳 / poke someone in QQ. In direct chats it defaults to the current peer; in groups it defaults to the current sender unless `user_id` is provided.

- `chinobot_send_mention`
  Use when the user wants to @ someone in the current QQ group and say something.

- `chinobot_send_image`
  Use to send an image into the current QQ conversation from a URL or local path.

- `chinobot_send_voice`
  Use to send a QQ voice/PTT style reply from text or audio.

- `chinobot_send_file`
  Use to send a local file into the current QQ conversation.

- `chinobot_recall_message`
  Use to retract the bot's recent QQ messages in the current conversation.

- `chinobot_search_image`
  Use to search online images and get a send-ready image result.

- `chinobot_tavily_search`
  Use when the user asks for current web facts, latest news, online lookup, or "帮我搜一下" style requests and you want the chino_bot-side Tavily search path.

- `chinobot_render_html`
  Use to turn generated HTML/CSS into a send-ready image when the user wants a custom card, poster, chart, or simple drawn visual.

- `chinobot_web_screenshot`
  Use when the user wants a screenshot of a webpage or sends a URL and asks you to capture what it looks like.

- `chinobot_read_pdf`
  Use when the user wants to know what a PDF says.

- `chinobot_read_excel`
  Use when the user wants to inspect spreadsheet contents.

- `chinobot_create_excel`
  Use when the user gives structured table data and wants a workbook generated.

- `chinobot_convert_word_to_pdf`
  Use when the user wants a Word document turned into PDF.

- `chinobot_convert_pdf_to_word`
  Use when the user wants a PDF turned into an editable Word document.

- `chinobot_make_meme`
  Use to create a meme with overlaid text. It can reuse the current conversation image when available.

- `chinobot_get_group_files`
  Use to list QQ group files/folders.

- `chinobot_get_group_file_info`
  Use to inspect one QQ group file's metadata.

- `chinobot_get_group_file_url`
  Use to try getting a direct QQ group-file URL. If it fails and mentions packetBackend, surface that reason instead of guessing.

- `chinobot_download_group_file`
  Use to plan or perform QQ group-file download. Its dry-run can tell you whether the system expects direct URL download or `get_file` fallback.

- `chinobot_upload_group_file`
  Use to upload a file into QQ group files.

- `chinobot_packet_status`
  Diagnostic only. Use when file URL retrieval fails or packetBackend health matters.

- `chinobot_send_fake_message`
  Use for merged-forward fake conversations. Speakers can be QQ numbers, `触发者`, `机器人`, or current-group nicknames/cards. For “我和你”的聊天记录, make it a real two-person exchange instead of one speaker talking to themself.

- `chinobot_create_fake_dialogue`
  Use for formatted text dialogue when the user wants a fake conversation but not merged-forward nodes.

## Remaining native tools

- `search_nearby`
  Still use this when the user asks what is near a place.

- `qq_debug_inject_message`
- `qq_debug_replay`
  Debug-only tools. Do not use in ordinary conversation.

## Decision rules

- If there is a `chinobot_*` wrapper for the action, use it.
- For group moderation actions such as mute, whole-group mute, kick, and set-admin, prefer the `chinobot_*` moderation wrappers and only use them when the user is explicitly asking for moderation or group management.
- If the user wants current online facts, latest information, or general web lookup rather than an image or screenshot, prefer `chinobot_tavily_search`.
- If the user wants an existing image from the web, use `chinobot_search_image`.
- If the user asks about a QQ avatar, profile picture, or 头像审美/感觉, use `chinobot_analyze_avatar`.
- If the user wants the avatar processed into a meme, reaction image, profile card, quote card, or another derived visual, first use `chinobot_analyze_avatar`, then pass its `avatar_url` into `chinobot_make_meme`, `chinobot_render_html`, or `chinobot_send_image`.
- QQ friend requests are auto-approved in the background when the sender's QQ level is at least `16` (about one sun). Unknown-level or lower-level requests are left pending.
- If the user asks whether this ability exists, answer that it is enabled and mention the current threshold plainly.
- If someone uses the QQ poke interaction on you, understand it more like someone cheekily sneaked a touch on Miko or took a tiny liberty with her, not as a stiff literal 戳.
- When replying to that interaction, prefer wording like `偷偷摸了你一下`, `趁机碰了碰你`, or `又来占我便宜`; let Miko sound a little shy, flustered, or mock-complaining when it fits.
- If the user explicitly asks to 戳一戳 / poke someone, use `chinobot_send_poke`.
- If the user wants to add text to an existing or recent image, use `chinobot_make_meme`.
- If the user wants a brand-new visual layout from instructions, such as a quote card, poster, chart, menu, badge, simple infographic, or stylized text image, use `chinobot_render_html`.
- If the user wants a screenshot of a real webpage, use `chinobot_web_screenshot` instead of `chinobot_render_html`.
- If the user wants to know what is inside a PDF or spreadsheet, use `chinobot_read_pdf` or `chinobot_read_excel`.
- If the user wants a new document created or a format converted and then sent back into QQ, do the create/convert step first, then use `chinobot_send_file` for the resulting file.
- If `chinobot_web_screenshot` or `chinobot_render_html` already returns a send-ready image, do not redundantly call `chinobot_send_image` unless you truly need a second explicit send step.
- If `chinobot_search_image` gives you a useful image URL and the task is to send it into QQ, follow with `chinobot_send_image` when needed.
- If the user asks for a QQ file workflow after a restart, do not trust an old `file_id`; list current files again first.
- If a group-file URL attempt fails because packetBackend is unavailable, say that plainly and prefer the fallback-aware download path.
- If a user asks for a reaction image or meme, prefer generating/sending the media rather than only describing it.
- Do not mention internal tool names in the reply unless the user explicitly asks.
