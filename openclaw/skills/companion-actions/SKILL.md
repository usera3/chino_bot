---
name: companion-actions
description: Trigger desktop companion body actions such as nod, wave, curious lean, concern, sleepy idle, and calm reset through the local companion bridge.
---

# Companion Actions

Use this skill when the user is clearly asking the desktop companion body to do a visible action.

## Use when the user says things like

- "点头"
- "挥手"
- "做个动作"
- "靠近一点"
- "做个好奇的动作"
- "表现得困一点"
- "恢复安静"
- "让桌宠动一下"

## Action mapping

- `nod`
  - 点头
  - 认可一下
  - 小点头

- `wave`
  - 挥手
  - 打招呼
  - 招招手

- `curious`
  - 好奇一点
  - 靠近一点
  - 探头看看

- `concern`
  - 紧张一点
  - 担心一点
  - 警觉一点

- `sleepy`
  - 困一点
  - 打瞌睡
  - 慢一点

- `attentive`
  - 认真一点
  - 专注一点
  - 站好一点

- `wake`
  - 醒一醒
  - 精神一点

- `calm`
  - 恢复安静
  - 回到待机
  - 正常一点

## How to execute

Run:

```bash
node scripts/control-companion-action.mjs trigger --preset <preset> [--text "可选台词"]
```

Examples:

```bash
node scripts/control-companion-action.mjs trigger --preset nod --text "老板。"
node scripts/control-companion-action.mjs trigger --preset wave --text "你好。"
node scripts/control-companion-action.mjs trigger --preset curious --text "我在看。"
node scripts/control-companion-action.mjs trigger --preset calm
```

## Rules

- Prefer a single clear visible action over multiple chained actions.
- If the user only wants the body to move, do not add extra speech unless it helps.
- If the request is ambiguous, choose the closest single preset.
- If the user asks for a body-only action, do not reply with a long explanation first; execute it.
- If the desktop companion stack is not running, say so briefly.

