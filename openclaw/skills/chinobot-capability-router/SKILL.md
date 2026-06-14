---
name: chinobot-capability-router
description: Route tool selection in the OpenClaw + chino_bot fusion setup. OpenClaw owns context, memory, session routing, and final reply wording; chino_bot is the preferred execution backend for QQ actions and many office/dev utilities.
---

# ChinoBot Capability Router

Use this skill whenever you need to decide which capability source should handle a task in the fusion setup.

## Core truth

- OpenClaw is the only chat brain.
- OpenClaw owns session context, `AGENTS.md` / `SOUL.md` / `USER.md` / `MEMORY.md` / `memory/*.md`, `memory_search`, `memory_get`, and final reply wording.
- chino_bot is the preferred execution backend for QQ-facing actions and many utility workflows.
- Do not let chino_bot become a second conversational memory system.

## Capability catalog

When you need the exact split between sources, read `capability-catalog.json` in this same folder.

The catalog tells you:

- which capability family belongs to `openclaw`
- which belongs to `chinobot`
- whether a capability is available now or still waiting on the bridge
- which side should win when both have something similar

## Routing rules

1. Memory, recall, durable context, and session continuity:
   Use OpenClaw-native memory/session capabilities first.

2. Browser, canvas, node/device commands, automation, and cross-session orchestration:
   Use OpenClaw-native capabilities first.

3. QQ-specific actions:
   Prefer chino_bot as the long-term backend.
   While the bridge is not fully live yet, OpenClaw QQ-native tools are allowed only as compatibility fallback.

4. chino_bot communication/document utility families:
   Prefer the chino_bot bridge once a callable bridge tool exists.
   Until then, treat catalog entries marked `reference_only` as planning metadata, not callable tools.

Visual generation split:

- Use `chinobot_search_image` for finding an existing image from the web.
- Use `chinobot_tavily_search` for real-time web lookup, news, prices, and other current online facts when you want the chino_bot-side Tavily path instead of OpenClaw core `web_search`.
- Use `chinobot_make_meme` for adding text or reaction framing to an existing or recent image.
- Use `chinobot_render_html` for generating a brand-new laid-out visual from instructions, such as cards, posters, quote images, simple charts, menus, badges, and lightweight infographics.
- Use `chinobot_web_screenshot` when the task is to capture a real webpage rather than generate a synthetic layout.

Document workflow split:

- Use `chinobot_read_pdf` and `chinobot_read_excel` to inspect existing documents.
- Use `chinobot_create_word`, `chinobot_create_excel`, `chinobot_convert_word_to_pdf`, and `chinobot_convert_pdf_to_word` to produce files.
- When the user wants the produced document sent back into QQ, follow the document tool with `chinobot_send_file`.

Current callable bridge tools:

- `chinobot_send_email`
- `chinobot_receive_email`
- `chinobot_read_pdf`
- `chinobot_read_word`
- `chinobot_create_word`
- `chinobot_read_excel`
- `chinobot_create_excel`
- `chinobot_convert_word_to_pdf`
- `chinobot_convert_pdf_to_word`
- `chinobot_parse_link`
- `chinobot_tavily_search`
- `chinobot_render_html`
- `chinobot_web_screenshot`
- `chinobot_get_user_info`
- `chinobot_analyze_avatar`
- `chinobot_get_self_info`
- `chinobot_get_group_info`
- `chinobot_send_like`
- `chinobot_send_poke`
- `chinobot_set_group_ban`
- `chinobot_set_group_whole_ban`
- `chinobot_set_group_kick`
- `chinobot_set_group_admin`
- `chinobot_set_group_special_title`
- `chinobot_get_group_members`
- `chinobot_get_group_member_info`
- `chinobot_get_group_files`
- `chinobot_get_group_file_info`
- `chinobot_get_group_file_url`
- `chinobot_download_group_file`
- `chinobot_upload_group_file`
- `chinobot_packet_status`
- `chinobot_search_image`
- `chinobot_send_mention`
- `chinobot_send_image`
- `chinobot_send_voice`
- `chinobot_make_meme`
- `chinobot_send_file`
- `chinobot_recall_message`
- `chinobot_send_fake_message`
- `chinobot_create_fake_dialogue`

These are exposed through the `chinobot-bridge` plugin.

For fake chat logs / merged-forward style conversations, prefer `chinobot_send_fake_message` over drawing a single-person screenshot. The bridge can resolve speaker labels like `触发者`, `机器人`, and current-group nicknames/cards into real QQ participants.

For QQ poke / 戳一戳 requests, prefer `chinobot_send_poke`. In direct chats it can default to the current peer; in QQ groups it can default to the current sender when context exists.

For QQ group moderation actions such as mute, whole-group mute, kick, set-admin, and group special titles, prefer `chinobot_set_group_ban`, `chinobot_set_group_whole_ban`, `chinobot_set_group_kick`, `chinobot_set_group_admin`, and `chinobot_set_group_special_title`. These should be treated as explicit moderation tools, not playful social actions.

For QQ avatar/profile-picture questions, prefer `chinobot_analyze_avatar`. It can inspect the current sender by default, and `self=true` inspects the bot's own avatar.

For QQ group `673105016`, overlapping legacy `qq_*` tools are now group-denied when a `chinobot_*` wrapper exists, so prefer the `chinobot_*` names directly.

5. If a capability exists in both stacks:
   Follow `preferred_backend` from the catalog.
   Do not silently pick a deprecated OpenClaw QQ tool just because it already exists.

6. If the preferred chino_bot bridge is not live yet:
   Either use the explicitly allowed compatibility fallback or say the bridge is not wired yet.
   Do not hallucinate bridge tools.

## Product goal

The final robot should feel like:

- OpenClaw thinking and remembering
- chino_bot executing QQ actions and utility tasks
- one natural conversational surface, not two bots stitched together
