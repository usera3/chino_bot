from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.openclaw_style import (
    build_openclaw_runtime_system_prompt,
    build_style_context,
    history_message_limit,
    inject_relevant_memory,
    normalize_reply_text,
    should_lookup_memory,
    strip_system_context,
)


def test_strip_system_context():
    raw = "[系统提示：用户是小明(QQ:123)]\n\n你好"
    assert strip_system_context(raw) == "你好"


def test_memory_lookup_only_when_message_needs_history():
    context = build_style_context({"chat_type": "direct"})
    assert not should_lookup_memory("你好", context)
    assert should_lookup_memory("你还记得我上次说的邮箱吗", context)


def test_group_runtime_prompt_includes_openclaw_overlay():
    context = build_style_context({"chat_type": "group", "group_id": "123456"})
    prompt = build_openclaw_runtime_system_prompt("BASE", "哈哈", context)
    assert "OpenClaw QQ 管家风格" in prompt
    assert "QQ群聊（群号 123456）" in prompt
    assert "优先追求像真实聊天成员一样自然" in prompt


def test_history_window_stays_small_for_group_small_talk():
    context = build_style_context({"chat_type": "group"})
    assert history_message_limit("哈哈", context) == 4


def test_history_window_expands_for_direct_long_form_request():
    context = build_style_context({"chat_type": "direct"})
    assert history_message_limit("详细分析一下这个代码结构和修复方案", context) == 12


def test_inject_relevant_memory_uses_internal_reference_framing():
    merged = inject_relevant_memory("你还记得吗", "之前提到用户常用 QQ 邮箱")
    assert "[内部参考记忆]" in merged
    assert "不要逐条复述" in merged


def test_normalize_reply_text_makes_group_reply_less_assistant_like():
    context = build_style_context({"chat_type": "group"})
    reply = "当然可以，如果你愿意，我还能继续帮你看一下。"
    normalized = normalize_reply_text(reply, "哈哈", context)
    assert "如果你愿意" not in normalized
    assert "当然可以" not in normalized
    assert normalized == "继续帮你看一下"


def test_normalize_reply_text_preserves_long_form_structure():
    context = build_style_context({"chat_type": "direct"})
    reply = "1. 先看日志\n2. 再定位问题\n3. 最后补测试"
    normalized = normalize_reply_text(reply, "详细说说排查步骤", context)
    assert normalized == reply
