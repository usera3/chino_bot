import fs from "node:fs/promises";
import { QQ_DEBUG_LOG_PATH } from "./service.js";

export type QqDebugReplayParams = {
  conversationKey?: string;
  groupId?: string;
  accountId?: string;
  minutes?: number;
  limit?: number;
  aroundMessageId?: string;
  keyword?: string;
  kinds?: string[];
  logPath?: string;
};

type QqDebugLogRow = {
  kind: string;
  at: string;
  atMs: number;
  conversationKey: string;
  accountId?: string;
  chatType?: "group" | "direct";
  peerId?: string;
  detail: Record<string, unknown>;
  messageIds: string[];
};

function shortText(value: unknown, limit = 120): string {
  return String(value ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

function parseConversationKey(conversationKey: string): {
  accountId?: string;
  chatType?: "group" | "direct";
  peerId?: string;
} {
  const match = conversationKey.match(/^qq:([^:]+):(group|direct):(.+)$/);
  if (!match) {
    return {};
  }
  return {
    accountId: match[1],
    chatType: match[2] === "group" ? "group" : "direct",
    peerId: match[3],
  };
}

function toTimestamp(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return 0;
}

function extractMessageIds(detail: Record<string, unknown>): string[] {
  const ids = new Set<string>();
  for (const key of ["messageId", "replyToMessageId", "resolvedMessageId", "focusMessageId"]) {
    const value = detail[key];
    if (typeof value === "string" && value.trim()) {
      ids.add(value.trim());
    }
  }
  const entriesPreview = detail.entriesPreview;
  if (Array.isArray(entriesPreview)) {
    for (const entry of entriesPreview) {
      if (!entry || typeof entry !== "object") {
        continue;
      }
      const messageId = (entry as { message_id?: unknown }).message_id;
      if (typeof messageId === "string" && messageId.trim()) {
        ids.add(messageId.trim());
      }
      const replyToMessageId = (entry as { reply_to_message_id?: unknown }).reply_to_message_id;
      if (typeof replyToMessageId === "string" && replyToMessageId.trim()) {
        ids.add(replyToMessageId.trim());
      }
    }
  }
  return [...ids];
}

function parseLogLine(line: string): QqDebugLogRow | null {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(trimmed) as Record<string, unknown>;
  } catch {
    return null;
  }
  const kind = typeof parsed.kind === "string" ? parsed.kind.trim() : "";
  const conversationKey =
    typeof parsed.conversationKey === "string" ? parsed.conversationKey.trim() : "";
  if (!kind || !conversationKey) {
    return null;
  }
  const at = typeof parsed.at === "string" ? parsed.at : new Date().toISOString();
  const { kind: _kind, at: _at, conversationKey: _conversationKey, ...detail } = parsed;
  return {
    kind,
    at,
    atMs: toTimestamp(at),
    conversationKey,
    ...parseConversationKey(conversationKey),
    detail,
    messageIds: extractMessageIds(detail),
  };
}

async function readQqDebugRows(logPath: string): Promise<QqDebugLogRow[]> {
  const raw = await fs.readFile(logPath, "utf8");
  return raw
    .split(/\r?\n/g)
    .map((line) => parseLogLine(line))
    .filter((entry): entry is QqDebugLogRow => Boolean(entry))
    .sort((left, right) => left.atMs - right.atMs);
}

function matchesKeyword(entry: QqDebugLogRow, keyword?: string): boolean {
  const query = keyword?.trim().toLowerCase();
  if (!query) {
    return true;
  }
  const haystack = JSON.stringify({
    kind: entry.kind,
    conversationKey: entry.conversationKey,
    ...entry.detail,
  }).toLowerCase();
  return haystack.includes(query);
}

function matchesKinds(entry: QqDebugLogRow, kinds?: string[]): boolean {
  if (!Array.isArray(kinds) || kinds.length === 0) {
    return true;
  }
  return kinds.includes(entry.kind);
}

function summarizeEvent(entry: QqDebugLogRow): { summary: string; lines?: string[] } {
  switch (entry.kind) {
    case "media_ingress": {
      const preview = shortText(entry.detail.rawBodyPreview, 80);
      const phase = shortText(entry.detail.phase, 16);
      const refs = Array.isArray(entry.detail.mediaRefs)
        ? entry.detail.mediaRefs
            .map((item) => {
              if (!item || typeof item !== "object") {
                return "";
              }
              const type = shortText((item as { type?: unknown }).type, 16) || "unknown";
              const preferred = shortText((item as { preferred_ref?: unknown }).preferred_ref, 60);
              const rawFile = shortText((item as { raw_file?: unknown }).raw_file, 40);
              const rawUrlHost = shortText((item as { raw_url_host?: unknown }).raw_url_host, 40);
              const localResolved = Boolean(
                (item as { local_file_resolved?: unknown }).local_file_resolved,
              );
              return `${type}: preferred=${preferred || "-"} raw_file=${rawFile || "-"} raw_url_host=${rawUrlHost || "-"} local=${localResolved ? "yes" : "no"}`;
            })
            .filter(Boolean)
        : Array.isArray(entry.detail.resolvedMedia)
          ? entry.detail.resolvedMedia
              .map((item) => {
                if (!item || typeof item !== "object") {
                  return "";
                }
                const resolution = shortText((item as { resolution?: unknown }).resolution, 24);
                const sourceHost = shortText(
                  (item as { source_url_host?: unknown }).source_url_host,
                  40,
                );
                const localPath = shortText((item as { local_path?: unknown }).local_path, 40);
                const error = shortText((item as { error?: unknown }).error, 60);
                return `resolved: mode=${resolution || "-"} host=${sourceHost || "-"} local=${localPath || "-"}${error ? ` error=${error}` : ""}`;
              })
              .filter(Boolean)
          : [];
      return {
        summary: `media_ingress${phase ? `(${phase})` : ""}: ${preview || "无预览"}${refs.length > 0 ? ` | ${refs[0]}` : ""}`,
        lines: refs.length > 1 ? refs : undefined,
      };
    }
    case "burst_compaction": {
      const entryCount = Number(entry.detail.entryCount ?? 0);
      const retainedCount = Number(entry.detail.retainedCount ?? 0);
      const omittedCount = Number(entry.detail.omittedCount ?? 0);
      const focusPreview = shortText(entry.detail.focusPreview, 80);
      const lines = Array.isArray(entry.detail.entriesPreview)
        ? entry.detail.entriesPreview
            .map((item, index) => {
              if (!item || typeof item !== "object") {
                return "";
              }
              const sender =
                shortText((item as { sender_name?: unknown }).sender_name, 32) ||
                shortText((item as { sender_id?: unknown }).sender_id, 24);
              const text = shortText((item as { text?: unknown }).text, 80);
              return `${index + 1}. ${sender}: ${text}`;
            })
            .filter(Boolean)
        : undefined;
      return {
        summary: `burst: 连续 ${entryCount} 条，保留 ${retainedCount} 条，省略 ${omittedCount} 条；焦点=${focusPreview || "无"}`,
        lines,
      };
    }
    case "reply_target_resolve": {
      const strategy = shortText(entry.detail.strategy, 32);
      const replyToMessageId = shortText(entry.detail.replyToMessageId, 32);
      const preview = shortText(entry.detail.replyTextPreview, 80);
      const mediaSummary = shortText(entry.detail.mediaSummary, 80);
      return {
        summary:
          `reply_target: ${strategy || "unknown"} reply_to=${replyToMessageId || "-"} ` +
          `${preview ? `文本=${preview}` : ""}${mediaSummary ? ` 媒体=${mediaSummary}` : ""}`.trim(),
      };
    }
    case "media_resolve": {
      const strategy = shortText(entry.detail.strategy, 32);
      const query = shortText(entry.detail.query, 40);
      const focusPreview = shortText(entry.detail.focusPreview, 80);
      const boundSummary = shortText(entry.detail.boundSummary, 80);
      return {
        summary:
          `media_resolve: ${strategy || "unknown"} ` +
          `${boundSummary ? `=> ${boundSummary}` : ""}` +
          `${query ? ` query=${query}` : ""}` +
          `${focusPreview ? ` | 用户=${focusPreview}` : ""}`,
      };
    }
    case "dispatch_gate": {
      const action = shortText(entry.detail.action, 24);
      const mode = shortText(entry.detail.mode, 32);
      const rawBodyPreview = shortText(entry.detail.rawBodyPreview, 80);
      const busyLevel = shortText(entry.detail.busyLevel, 16);
      const pendingCount = Number(entry.detail.pendingCount ?? 0);
      const socialJoinReason = shortText(entry.detail.socialJoinReason, 32);
      const followupReason = shortText(entry.detail.followupReason, 32);
      const semanticReason = shortText(entry.detail.semanticReason, 32);
      return {
        summary:
          `dispatch: ${action || "unknown"} mode=${mode || "-"} busy=${busyLevel || "-"} pending=${pendingCount}` +
          `${socialJoinReason ? ` social=${socialJoinReason}` : ""}` +
          `${followupReason ? ` followup=${followupReason}` : ""}` +
          `${semanticReason ? ` semantic=${semanticReason}` : ""}` +
          `${rawBodyPreview ? ` | 用户=${rawBodyPreview}` : ""}`,
      };
    }
    default:
      return {
        summary: `${entry.kind}: ${shortText(JSON.stringify(entry.detail), 180)}`,
      };
  }
}

function buildDiagnosis(entries: QqDebugLogRow[]): string[] {
  if (entries.length === 0) {
    return ["当前窗口没有匹配到调试事件。"];
  }
  const notes: string[] = [];
  const latestSkip = [...entries]
    .reverse()
    .find((entry) => entry.kind === "dispatch_gate" && entry.detail.action === "skip");
  if (latestSkip) {
    notes.push(
      `最近一次沉默是被 ${shortText(latestSkip.detail.mode, 32) || "dispatch gate"} 挡住；social=${shortText(latestSkip.detail.socialJoinReason, 32) || "-"} / followup=${shortText(latestSkip.detail.followupReason, 32) || "-"} / semantic=${shortText(latestSkip.detail.semanticReason, 32) || "-"}`,
    );
  }
  const latestRecentBufferBind = [...entries]
    .reverse()
    .find(
      (entry) => entry.kind === "media_resolve" && entry.detail.strategy === "recent_media_buffer",
    );
  if (latestRecentBufferBind) {
    notes.push(
      `最近一次图绑定走了 recent_media_buffer，说明当轮/引用里没直接命中，靠最近媒体兜底：${shortText(latestRecentBufferBind.detail.boundSummary, 80)}`,
    );
  }
  const latestReplyMiss = [...entries]
    .reverse()
    .find((entry) => entry.kind === "reply_target_resolve" && entry.detail.strategy === "miss");
  if (latestReplyMiss) {
    notes.push("最近一次 reply_to 解析没命中，被回复消息没从 buffer 或 OneBot `get_msg` 拿到。");
  }
  const latestBurst = [...entries]
    .reverse()
    .find(
      (entry) => entry.kind === "burst_compaction" && Number(entry.detail.omittedCount ?? 0) > 0,
    );
  if (latestBurst) {
    notes.push(
      `最近一次 burst mode 省略了 ${Number(latestBurst.detail.omittedCount ?? 0)} 条相似媒体消息，避免图片海把上下文塞满。`,
    );
  }
  if (notes.length === 0) {
    notes.push("当前窗口内没有明显异常；可以结合更长时间窗口再看一轮。");
  }
  return notes;
}

function buildConversationList(entries: QqDebugLogRow[]) {
  const grouped = new Map<
    string,
    {
      conversation_key: string;
      account_id?: string;
      chat_type?: "group" | "direct";
      peer_id?: string;
      event_count: number;
      last_at: string;
      kinds: string[];
    }
  >();
  for (const entry of entries) {
    const current = grouped.get(entry.conversationKey) ?? {
      conversation_key: entry.conversationKey,
      account_id: entry.accountId,
      chat_type: entry.chatType,
      peer_id: entry.peerId,
      event_count: 0,
      last_at: entry.at,
      kinds: [],
    };
    current.event_count += 1;
    current.last_at = entry.at;
    if (!current.kinds.includes(entry.kind)) {
      current.kinds.push(entry.kind);
    }
    grouped.set(entry.conversationKey, current);
  }
  return [...grouped.values()]
    .sort((left, right) => Date.parse(right.last_at) - Date.parse(left.last_at))
    .slice(0, 12);
}

function selectConversation(
  entries: QqDebugLogRow[],
  params: QqDebugReplayParams,
): string | undefined {
  if (params.conversationKey?.trim()) {
    return params.conversationKey.trim();
  }
  const filtered = entries.filter((entry) => {
    if (params.accountId?.trim() && entry.accountId !== params.accountId.trim()) {
      return false;
    }
    if (params.groupId?.trim()) {
      return entry.chatType === "group" && entry.peerId === params.groupId.trim();
    }
    return true;
  });
  return filtered.at(-1)?.conversationKey;
}

function buildReplayText(entries: QqDebugLogRow[]): string {
  return entries
    .map((entry) => {
      const timestamp = new Date(entry.atMs || Date.parse(entry.at)).toLocaleString("zh-CN", {
        hour12: false,
      });
      const summary = summarizeEvent(entry);
      const lines = summary.lines?.length ? `\n  ${summary.lines.join("\n  ")}` : "";
      return `[${timestamp}] ${summary.summary}${lines}`;
    })
    .join("\n");
}

export async function replayQqIngressDebugLog(params: QqDebugReplayParams = {}) {
  const logPath = params.logPath?.trim() || QQ_DEBUG_LOG_PATH;
  let rows: QqDebugLogRow[] = [];
  try {
    rows = await readQqDebugRows(logPath);
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
      log_path: logPath,
      available_conversations: [],
    };
  }

  const selectedConversation = selectConversation(rows, params);
  const availableConversations = buildConversationList(rows);
  if (!selectedConversation) {
    return {
      ok: false,
      error: "没有找到匹配的 conversation，可先看 available_conversations。",
      log_path: logPath,
      available_conversations: availableConversations,
    };
  }

  const now = Date.now();
  const minutes = Math.max(1, Math.min(24 * 60, Number(params.minutes ?? 30)));
  const limit = Math.max(5, Math.min(200, Number(params.limit ?? 40)));
  const timeFloor = now - minutes * 60_000;
  let filtered = rows.filter(
    (entry) =>
      entry.conversationKey === selectedConversation &&
      matchesKeyword(entry, params.keyword) &&
      matchesKinds(entry, params.kinds),
  );
  const totalConversationEvents = filtered.length;
  if (params.aroundMessageId?.trim()) {
    const target = params.aroundMessageId.trim();
    const index = filtered.findIndex((entry) => entry.messageIds.includes(target));
    if (index >= 0) {
      const radius = Math.max(2, Math.floor(limit / 2));
      filtered = filtered.slice(Math.max(0, index - radius), index + radius + 1);
    } else {
      filtered = filtered.slice(-limit);
    }
  } else {
    const windowed = filtered.filter((entry) => entry.atMs >= timeFloor);
    filtered = (windowed.length > 0 ? windowed : filtered).slice(-limit);
  }

  const replay = filtered.map((entry) => {
    const summary = summarizeEvent(entry);
    return {
      at: entry.at,
      kind: entry.kind,
      summary: summary.summary,
      lines: summary.lines ?? [],
      message_ids: entry.messageIds,
      details: entry.detail,
    };
  });

  return {
    ok: true,
    log_path: logPath,
    selected_conversation_key: selectedConversation,
    selected_conversation: parseConversationKey(selectedConversation),
    window: {
      minutes,
      limit,
      returned_events: replay.length,
      total_conversation_events: totalConversationEvents,
    },
    diagnosis: buildDiagnosis(filtered),
    replay_text: buildReplayText(filtered),
    replay,
    available_conversations: availableConversations,
  };
}
