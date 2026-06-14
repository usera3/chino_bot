"""OpenClaw-inspired QQ chat style helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


MEMORY_CUES = (
    "之前",
    "刚才",
    "上次",
    "还记得",
    "记得",
    "继续",
    "接着",
    "那个",
    "这个",
    "那件事",
    "我说过",
    "你说过",
    "我们聊过",
)

LONG_FORM_CUES = (
    "详细",
    "分析",
    "解释",
    "展开",
    "步骤",
    "方案",
    "总结",
    "对比",
    "为什么",
    "怎么做",
    "教程",
    "代码",
    "文档",
    "设计",
    "实现",
    "排查",
    "修复",
)

ASSISTANT_OPENERS = (
    "当然可以",
    "当然",
    "好的呀",
    "好的呢",
    "好的",
    "没问题",
    "您好",
    "亲",
)

ANTI_PATTERNS = (
    "如果你愿意，我还能",
    "如果你愿意，我可以继续",
    "简单来说",
    "简单记",
    "举个例子",
    "根据你的描述",
    "作为一个AI",
    "如果还需要的话",
)

FOLLOW_UP_CUES = (
    "如果你愿意",
    "需要的话",
    "如果还要",
    "我还能",
    "我也可以继续",
)

QUESTION_TAIL_RE = re.compile(r"(吗|么|嘛|呢|要不要|要不|好不好|行不行|能不能|可不可以)[？?]?$")
LIST_LINE_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+", re.M)
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


@dataclass(frozen=True)
class ConversationStyleContext:
    """Lightweight conversation metadata for style control."""

    chat_type: str = "direct"
    group_id: Optional[str] = None
    engaged_directly: bool = True
    is_reply: bool = False
    has_images: bool = False
    platform: str = "qq"
    bot_name: str = "智乃"
    sender_name: Optional[str] = None


def build_style_context(raw: Optional[dict] = None) -> ConversationStyleContext:
    """Normalize conversation metadata."""

    raw = raw or {}
    chat_type = str(raw.get("chat_type") or "direct").strip().lower()
    if chat_type in {"群聊", "group", "qq_group"}:
        chat_type = "group"
    else:
        chat_type = "direct"

    return ConversationStyleContext(
        chat_type=chat_type,
        group_id=str(raw.get("group_id")).strip() if raw.get("group_id") else None,
        engaged_directly=bool(raw.get("engaged_directly", True)),
        is_reply=bool(raw.get("is_reply", False)),
        has_images=bool(raw.get("has_images", False)),
        platform=str(raw.get("platform") or "qq").strip().lower() or "qq",
        bot_name=str(raw.get("bot_name") or "智乃").strip() or "智乃",
        sender_name=str(raw.get("sender_name")).strip() if raw.get("sender_name") else None,
    )


def strip_system_context(user_input: str) -> str:
    """Remove the injected system header added by the QQ plugin."""

    text = (user_input or "").strip()
    if text.startswith("[系统提示：") and "]\n\n" in text:
        return text.split("]\n\n", 1)[1].strip()
    return text


def should_lookup_memory(user_input: str, context: ConversationStyleContext) -> bool:
    """Only hit long-term memory when the message clearly depends on history."""

    text = strip_system_context(user_input)
    if not text:
        return False
    if _is_poke_message(text):
        return False
    if _is_simple_interaction(text, context) and not any(cue in text for cue in MEMORY_CUES):
        return False
    return any(cue in text for cue in MEMORY_CUES)


def inject_relevant_memory(user_input: str, relevant_context: str) -> str:
    """Inject memory as quiet internal context instead of a transcript dump."""

    text = (relevant_context or "").strip()
    if not text or "没有找到" in text:
        return user_input
    if len(text) > 1200:
        text = text[:1200].rstrip() + "..."
    return (
        "[内部参考记忆]\n"
        f"{text}\n\n"
        "[使用规则]\n"
        "只有在当前消息明显依赖过去上下文时才参考上面的内容，不要逐条复述，不要像背档案。\n\n"
        f"[当前消息]\n{user_input}"
    )


def history_message_limit(user_input: str, context: ConversationStyleContext) -> int:
    """Decide how much short-term history to keep in the prompt."""

    text = strip_system_context(user_input)
    if _is_poke_message(text):
        return 4
    if _is_simple_interaction(text, context):
        return 6 if context.chat_type == "direct" else 4
    if _wants_long_form(text):
        return 12 if context.chat_type == "direct" else 8
    return 8 if context.chat_type == "direct" else 6


def build_openclaw_runtime_system_prompt(
    base_prompt: str,
    user_input: str,
    context: ConversationStyleContext,
) -> str:
    """Append an OpenClaw-style QQ conversation overlay to the base prompt."""

    text = strip_system_context(user_input)
    is_simple = _is_simple_interaction(text, context)
    wants_long_form = _wants_long_form(text)
    scope = "QQ群聊" if context.chat_type == "group" else "QQ私聊"
    if context.group_id and context.chat_type == "group":
        scope += f"（群号 {context.group_id}）"

    lines = [
        base_prompt.strip(),
        "",
        "## OpenClaw QQ 管家风格",
        f"- 当前场景：{scope}",
        f"- 你现在要像 openclaw 在 QQ 里的自然聊天那样说话，但保留 {context.bot_name} 的人设和这个项目的工具能力。",
        "- 优先追求像真实聊天成员一样自然，而不是像客服、教程生成器或正式助手。",
        "- 先在心里快速草拟 2 到 3 个候选回复，选最短、最自然、最低助手味的那个。",
        "- 打分标准：短、口语化、低标点、少套话、少复述、先回应当下社交动作。",
        "- 涉及执行操作、实时信息、发送内容、搜索、文件处理时，优先调用工具，不要只口头承诺。",
        "- 不要自称真人，也不要刻意强调自己是 AI；自然回答就行。",
        "- 不要把普通闲聊写成分点、小作文或说明书。",
        "- 不要重复用户刚说的话，除非这是完成任务所必需的确认。",
        "- 不要频繁用“嗯”“好的”“当然可以”“您好”开头。",
        "- 不知道就直接说不知道，不要编造细节。",
        "- 少用颜文字和 emoji，除非当下真的很合适。",
        "- 反面模式：'如果你愿意，我还能继续帮你…'、'简单来说'、'举个例子'、'根据你的描述'。",
    ]

    if context.chat_type == "group":
        lines.extend(
            [
                "- 群聊里把自己当作群里一个会看气氛的成员；默认一句，必要时最多两句。",
                "- 群聊默认少标点，不要故意写得很完整很工整。",
                "- 群里先接住当下那一下，再决定要不要补解释。",
            ]
        )
    else:
        lines.extend(
            [
                "- 私聊可以比群里稍微暖一点，但依旧简短克制。",
                "- 私聊默认 1 到 2 句；只有用户明确要详细说明时再展开。",
            ]
        )

    if is_simple:
        lines.append("- 当前这条更像轻聊天或轻互动，优先一小句落地，不要顺手追加服务。")

    if wants_long_form:
        lines.append("- 当前这条是明确的详细请求，可以展开，但先给结论或动作，再补解释。")

    if _is_poke_message(text):
        lines.append("- 如果这是戳一戳、拍一拍、招呼类互动，只回一个轻短反应，不要解释机制。")

    return "\n".join(lines).strip()


def normalize_reply_text(
    text: str,
    user_input: str,
    context: ConversationStyleContext,
) -> str:
    """Apply a light OpenClaw-like post-processing pass to casual replies."""

    reply = (text or "").replace("\r", "").strip()
    if not reply:
        return reply

    plain_user_input = strip_system_context(user_input)
    if _should_preserve_structure(reply, plain_user_input):
        return reply

    is_simple = _is_simple_interaction(plain_user_input, context)
    max_segments = 1 if context.chat_type == "group" or is_simple else 2
    sparse_punctuation = context.chat_type == "group" or is_simple

    cleaned = _strip_assistant_opening(reply)
    segments = _split_reply_segments(cleaned)
    normalized_segments = []
    for index, segment in enumerate(segments):
        next_segment = _normalize_segment(segment, drop_followup=index > 0)
        if next_segment:
            normalized_segments.append(next_segment)

    if not normalized_segments:
        normalized_segments = [_normalize_segment(cleaned, drop_followup=False) or cleaned]

    limited = normalized_segments[:max_segments]
    if max_segments == 1:
        result = limited[0]
    else:
        result = "\n".join(limited)

    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    result = EMOJI_RE.sub("", result).strip()

    if sparse_punctuation:
        result = _sparsify_punctuation(result)

    if result and not _is_question_like(result):
        result = result.rstrip("。！!~～…")

    return result.strip() or reply


def _is_poke_message(text: str) -> bool:
    return "戳了戳你" in text or "拍了拍你" in text


def _is_simple_interaction(text: str, context: ConversationStyleContext) -> bool:
    plain = (text or "").strip()
    if not plain:
        return True
    if _is_poke_message(plain):
        return True
    if _wants_long_form(plain):
        return False
    if len(plain) <= 10:
        return True
    if len(plain) <= 18 and not context.has_images:
        simple_patterns = ("你好", "在吗", "早", "晚安", "哈哈", "hhh", "收到", "好耶", "干嘛", "怎么了")
        return any(pattern in plain for pattern in simple_patterns)
    return False


def _wants_long_form(text: str) -> bool:
    plain = (text or "").strip()
    if not plain:
        return False
    if "```" in plain:
        return True
    if "\n" in plain:
        return True
    if len(plain) >= 40:
        return True
    return any(cue in plain for cue in LONG_FORM_CUES)


def _should_preserve_structure(reply: str, user_input: str) -> bool:
    if "```" in reply:
        return True
    if LIST_LINE_RE.search(reply):
        return True
    if _wants_long_form(user_input):
        return True
    return len(reply) >= 140


def _strip_assistant_opening(text: str) -> str:
    stripped = text.strip()
    for opener in ASSISTANT_OPENERS:
        if stripped.startswith(opener) and len(stripped) > len(opener) + 2:
            remainder = stripped[len(opener):].lstrip("，,。！!~～ ")
            if remainder:
                return remainder
    return stripped


def _split_reply_segments(text: str) -> list[str]:
    normalized = text.replace("\r", "").strip()
    if not normalized:
        return []

    line_segments = [line.strip() for line in normalized.split("\n") if line.strip()]
    if not line_segments:
        return []

    sentence_segments = []
    for line in line_segments:
        parts = [part.strip() for part in re.split(r"(?<=[。！？!?])", line) if part.strip()]
        sentence_segments.extend(parts or [line])

    clause_segments = []
    for segment in sentence_segments:
        trimmed = segment.strip()
        if not trimmed:
            continue
        if len(trimmed) > 18 and re.search(r"[，,;；:：]", trimmed):
            pieces = [piece.strip() for piece in re.split(r"[，,;；:：]+", trimmed) if piece.strip()]
            if len(pieces) > 1:
                clause_segments.extend(pieces)
                continue
        clause_segments.append(trimmed)

    cleaned = [segment.rstrip("。！？!?").strip() for segment in clause_segments if segment.strip()]
    return cleaned


def _normalize_segment(segment: str, drop_followup: bool) -> str:
    cleaned = _strip_assistant_opening(segment).strip()
    if not cleaned:
        return ""

    for phrase in ANTI_PATTERNS:
        if phrase in cleaned:
            if drop_followup:
                return ""
            before, after = cleaned.split(phrase, 1)
            cleaned = before.strip() or after.strip()

    while True:
        matched_cue = next((cue for cue in FOLLOW_UP_CUES if cleaned.startswith(cue)), None)
        if not matched_cue:
            break
        if drop_followup:
            return ""
        cleaned = cleaned[len(matched_cue):].lstrip("，,。！!：:~～ ")
        if not cleaned:
            return ""

    return cleaned.strip(" \n")


def _sparsify_punctuation(text: str) -> str:
    next_text = re.sub(r"[，、；：]", "", text)
    next_text = re.sub(r"[~～]{2,}", "~", next_text)
    next_text = re.sub(r"([!?！？]){2,}", r"\1", next_text)
    next_text = re.sub(r"([。]){2,}", "。", next_text)
    return next_text.strip()


def _is_question_like(text: str) -> bool:
    trimmed = text.strip()
    if not trimmed:
        return False
    return trimmed.endswith(("？", "?")) or bool(QUESTION_TAIL_RE.search(trimmed))
