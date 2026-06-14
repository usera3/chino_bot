import { execFile, spawn, type ChildProcess } from "node:child_process";
import { promisify } from "node:util";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { WebSocketServer, type WebSocket } from "ws";
import type {
  OpenClawPluginApi,
  OpenClawPluginService,
  OpenClawConfig,
  OutboundReplyPayload,
} from "../../../dist/plugin-sdk/index.js";
import {
  buildMediaPayload,
  dispatchInboundReplyWithBase,
  sendMediaWithLeadingCaption,
} from "../../../dist/plugin-sdk/index.js";
import {
  h as triggerInternalHook,
  m as createInternalHookEvent,
} from "../../../dist/plugin-sdk/http-registry-7Lsnrxx9.js";
import { resolveQqHttpMediaUrl } from "../../shared/onebot-media-file.js";
import {
  resolveLocalQwenCloneTtsConfig,
  synthesizeLocalQwenCloneTts,
} from "../../shared/local-qwen-clone-tts.js";
import { shouldSuppressNoisyUserFacingErrorReply } from "../../shared/user-facing-error-suppression.js";
import { resolveQqAccount } from "./accounts.js";
import { runQqMakeMeme } from "./meme.js";
import { getQqRuntime } from "./runtime.js";
import {
  buildQqSocialAgencyPlan,
  buildQqSocialAgencyPromptRecord,
  ensureDefaultQqSocialAgencyFiles,
  persistQqSocialAgencyPlan,
  recordQqSocialAgencyOutcome,
  resolveQqAgencySenderProfile,
  type QqSocialAgencyPlan,
} from "./social-agency.js";
import type {
  CoreConfig,
  OneBotApiResponse,
  OneBotFriendRequestEvent,
  OneBotInboundFrame,
  OneBotMessageEvent,
  OneBotMessageSegment,
  OneBotPokeNoticeEvent,
  ParsedQqMessage,
  QqNaturalChatConfig,
  QqStudyModeConfig,
  ResolvedQqAccount,
} from "./types.js";

type PendingResolver = {
  resolve: (value: OneBotApiResponse) => void;
  reject: (reason?: unknown) => void;
  timeout: NodeJS.Timeout;
};

type QqConnectionState = {
  socket: WebSocket;
  accountId: string;
  selfId?: string;
  pending: Map<string, PendingResolver>;
};

type QqBrainTarget = "openclaw" | "codex";
type QqCodexReasoningEffort = "low" | "medium" | "high" | "xhigh";

type QqBrainCommand = {
  target: QqBrainTarget;
  body: string;
  explicitSwitch: boolean;
};

type QqCodexReasoningCommand = {
  effort: QqCodexReasoningEffort;
  label: string;
  body: string;
};

type QqReplyTarget = {
  messageId?: string;
  senderId?: string;
  senderName?: string;
  text?: string;
  media?: QqMediaRecord[];
};

type QqImageInsight = {
  index: number;
  ocr: string;
  alt: string;
  vision_summary: string;
  url?: string;
  path?: string;
  mime?: string;
};

type QqMediaRecord = {
  id: string;
  source: "inbound" | "reply_target" | "recent_media_buffer" | "outbound";
  message_id?: string;
  sender_id?: string;
  sender_name?: string;
  type: "image" | "emoji" | "animated_emoji";
  caption: string;
  quoted_text?: string;
  reply_to?: {
    message_id?: string;
    sender?: string;
    text?: string;
  };
  image_count: number;
  images: QqImageInsight[];
  replay_segments?: OneBotMessageSegment[];
  summary: string;
  created_at: number;
};

type QqMessageRecord = {
  id?: string;
  senderId: string;
  senderName?: string;
  text: string;
  createdAt: number;
  wasMentioned: boolean;
  isReply: boolean;
  replyToMessageId?: string;
  explicitInstruction: boolean;
  mediaIds: string[];
  direction: "inbound" | "outbound";
};

type QqDebugEvent = {
  kind:
    | "media_ingress"
    | "media_resolve"
    | "reply_target_resolve"
    | "burst_compaction"
    | "dispatch_gate";
  at: number;
  detail: Record<string, unknown>;
};

type QqConversationState = {
  recentMediaBuffer: QqMediaRecord[];
  recentMessages: QqMessageRecord[];
  busyLevel: "idle" | "light" | "busy" | "overloaded";
  pendingCount: number;
  lastRepliedMessageId?: string;
  debugEvents: QqDebugEvent[];
  lastTouchedAt: number;
};

type QqProactiveReactionImageIntent = {
  query: string;
  caption: string;
  reason: string;
};

type QqExplicitMemeIntent = {
  topText?: string;
  bottomText?: string;
  centerText?: string;
  caption: string;
  reason: string;
};

type QueuedQqInboundEvent = {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  event: OneBotMessageEvent;
  parsed: ParsedQqMessage;
  rawBody: string;
  timestamp: number;
  senderId: string;
  senderName?: string;
  burstIdleMs?: number;
  burstWindowMs?: number;
};

type QqInboundRecoveryCursor = {
  lastHandledAt?: number;
  lastHandledMessageId?: string;
};

type QqInboundRecoveryState = {
  lastConnectedAt?: number;
  lastDisconnectedAt?: number;
  conversations: Record<string, QqInboundRecoveryCursor>;
};

type QqRecentContactEntry = {
  lastestMsg?: unknown;
  peerUin?: string;
  remark?: string;
  msgTime?: string | number;
  chatType?: number;
  msgId?: string;
  sendNickName?: string;
  sendMemberName?: string;
  peerName?: string;
};

type QqDebugInjectionSummary = {
  ok: true;
  dry_run: boolean;
  debug_log_path: string;
  conversation_key: string;
  focus_message_id?: string;
  raw_body: string;
  burst_context?: string;
  decision: {
    action: "dispatch" | "skip" | "dispatch_immediate";
    mode: string;
    stage?: QqDecisionStage;
    reason?: string;
  };
  state: {
    busy_level: QqConversationState["busyLevel"];
    pending_count: number;
    last_replied_message_id?: string;
    competing_conversation_count: number;
    total_pending_count: number;
  };
  bound_media?: Record<string, unknown> | null;
  reply_target?: Record<string, unknown> | null;
  current_turn_media: Record<string, unknown>[];
  agent_body?: string;
};

type PendingQqBurst = {
  entries: QueuedQqInboundEvent[];
  startedAt: number;
  timer?: NodeJS.Timeout;
  burstWindowMs: number;
  studyImageAckSent?: boolean;
  studyFollowupAckSent?: boolean;
};

type ResolvedInboundMediaEntry = {
  sourceUrl: string;
  localPath?: string;
  contentType?: string;
  resolution?: "local-file" | "runtime-remote" | "qq-direct-fallback" | "unresolved";
  error?: string;
};

type ResolvedInboundMediaPayload = {
  payload: Record<string, unknown>;
  resolvedMedia: ResolvedInboundMediaEntry[];
};

type PreparedQqInboundMediaContext = {
  inboundMediaPayload: ResolvedInboundMediaPayload;
  currentMedia: QqMediaRecord[];
  replyTarget: QqReplyTarget | null;
  boundMedia: { record: QqMediaRecord; source: string } | null;
};

type QqSessionDepthCacheEntry = {
  sessionId: string;
  sessionFile: string;
  checkedAt: number;
  lineCount: number;
  rolloverMarked: boolean;
};

const execFileAsync = promisify(execFile);

const CHANNEL_ID = "qq";
const QQ_CODEX_BIN = "/Applications/Codex.app/Contents/Resources/codex";
const QQ_CODEX_WORKSPACE =
  process.env.QQ_CODEX_WORKSPACE || path.join(os.homedir(), ".openclaw", "qq-codex-workspace");
const QQ_CODEX_TIMEOUT_MS = Number(process.env.QQ_CODEX_TIMEOUT_MS || 10 * 60 * 1000);
const QQ_CODEX_MODEL = process.env.QQ_CODEX_MODEL || "gpt-5.5";
const QQ_CODEX_REASONING_EFFORT = normalizeQqCodexReasoningEffort(
  process.env.QQ_CODEX_REASONING_EFFORT,
);
const QQ_CODEX_REPLY_CHUNK_LIMIT = 3500;
const QQ_CODEX_PROMPT_CHAR_LIMIT = Number(process.env.QQ_CODEX_PROMPT_CHAR_LIMIT || 80_000);
const QQ_CODEX_PROMPT_KEEP_HEAD_CHARS = Number(
  process.env.QQ_CODEX_PROMPT_KEEP_HEAD_CHARS || 24_000,
);
const QQ_CODEX_PROMPT_KEEP_TAIL_CHARS = Number(
  process.env.QQ_CODEX_PROMPT_KEEP_TAIL_CHARS || 48_000,
);
const QQ_BRAIN_STATE_FILE = path.join(os.homedir(), ".openclaw", "qq", "brain-targets.json");
const QQ_CODEX_REASONING_STATE_FILE = path.join(
  os.homedir(),
  ".openclaw",
  "qq",
  "codex-reasoning.json",
);
const QQ_CODEX_CONTEXT_FILE = path.join(
  QQ_CODEX_WORKSPACE,
  ".qq-codex",
  "current-context.json",
);
const QQ_CODEX_LOCAL_ACTION_PATH = "/__openclaw/qq-codex/action";
const QQ_CODEX_LOCAL_ACTION_MAX_BYTES = 64 * 1024;
const QQ_CODEX_LOCAL_VOICE_OUTPUT_DIR = path.join(os.tmpdir(), "openclaw-qq-codex-voice");
const QQ_DIRECT_MEDIA_FETCH_TIMEOUT_MS = Number(
  process.env.QQ_DIRECT_MEDIA_FETCH_TIMEOUT_MS || 60_000,
);
const QQ_DIRECT_MEDIA_FETCH_RETRIES = Number(process.env.QQ_DIRECT_MEDIA_FETCH_RETRIES || 3);
const QQ_CODEX_LOCAL_ACTIONS = new Set([
  "qq_send_voice",
  "send_like",
  "friend_poke",
  "group_poke",
  "send_private_forward_msg",
  "send_group_forward_msg",
  "set_group_ban",
  "set_group_whole_ban",
  "set_group_kick",
  "set_group_admin",
  "set_group_special_title",
]);
const QQ_NATIVE_IMAGE_REQUEST_RE = /(画图|绘图|生图|出图|生成.{0,8}(图片|图像|图|插画|海报|头像|表情包)|画.{0,8}(图片|图像|图|插画|海报|头像|表情包)|draw|generate an image|create an image|make an image)/i;
const QQ_NATIVE_IMAGE_SCRIPT =
  process.env.OPENCLAW_QQ_NATIVE_IMAGE_SCRIPT ||
  path.resolve(process.cwd(), "skills", "openai-image-gen", "scripts", "gen.py");
const QQ_NATIVE_IMAGE_BASE_URL =
  process.env.OPENCLAW_QQ_NATIVE_IMAGE_BASE_URL || process.env.OPENAI_BASE_URL || "";
const QQ_NATIVE_IMAGE_PYTHON = process.env.OPENCLAW_QQ_NATIVE_IMAGE_PYTHON || "python3";
const HEARTBEAT_MS = 30_000;
const MANAGED_STATE_DIRNAME = "qq";
const MANAGED_STATE_FILENAME = "managed-launch.json";
const DEFAULT_MEDIA_MAX_MB = 20;
const DEFAULT_SOCIAL_JOIN_COOLDOWN_MINUTES = 8;
const DIRECT_FOLLOWUP_WATCH_MAX_MISSES = 10;
const DIRECT_FOLLOWUP_WATCH_IDLE_MS = 12 * 60 * 60 * 1000;
const DIRECT_FOLLOWUP_REPLY_RECENCY_MS = 20 * 60 * 1000;
const DIRECT_FOLLOWUP_SEMANTIC_TIMEOUT_MS = 8_000;
const DIRECT_FOLLOWUP_SEMANTIC_MIN_RULE_SCORE = 1;
const BURST_SEND_DELAY_MS = 350;
const TARGET_SOCIAL_HARD_BAN_PATTERN = /\u2615\uFE0F?/gu;
const QQ_STYLE_REFERENCE_DIR = "ciyuan-fusu-erqu";
const QQ_RECENT_DELIVERY_TTL_MS = 10 * 60 * 1000;
const QQ_DELIVERY_MAX_RETRIES = 5;
const QQ_DELIVERY_BACKOFF_MS = [5_000, 25_000, 120_000, 600_000];
const QQ_INBOUND_RECOVERY_CONTACT_LIMIT = 30;
const QQ_INBOUND_RECOVERY_HISTORY_LIMIT = 80;
const QQ_INBOUND_RECOVERY_MAX_LOOKBACK_MS = 12 * 60 * 60 * 1000;
const QQ_INBOUND_RECOVERY_WINDOW_PADDING_MS = 5_000;
const QQ_RECENT_MEDIA_BUFFER_LIMIT = 20;
const QQ_RECENT_MESSAGE_LIMIT = 80;
const QQ_CURRENT_MEDIA_PROMPT_LIMIT = 4;
const QQ_BURST_WINDOW_MS = 3_000;
const QQ_BURST_IDLE_MS = 900;
const QQ_DIRECT_STUDY_IMAGE_HOLD_MS = 6_000;
const QQ_DIRECT_STUDY_FOLLOWUP_FLUSH_MS = 120;
const QQ_STUDY_PROGRESS_FOLLOWUPS = [
  { delayMs: 20_000, kind: "solving_delayed" },
  { delayMs: 60_000, kind: "rendering_delayed" },
] as const;
const DEFAULT_QQ_STUDY_MODE_SKILLS = [
  "qq-problem-solving",
  "qq-fusion-actions",
  "chinobot-capability-router",
  "qq-native",
];
const QQ_BURST_THRESHOLD = 4;
const QQ_BURST_MEDIA_ONLY_KEEP = 3;
const QQ_PENDING_MEME_REQUEST_TTL_MS = 15 * 60 * 1000;
const QQ_IMAGE_SEARCH_RECENT_SELECTION_TTL_MS = 20 * 60 * 1000;
const QQ_DEBUG_EVENT_LIMIT = 120;
const QQ_IMAGE_SUMMARY_TIMEOUT_MS = 20_000;
const QQ_IMAGE_INSIGHT_CACHE_LIMIT = 256;
const QQ_CONVERSATION_STATE_IDLE_TTL_MS = 24 * 60 * 60 * 1000;
const QQ_CONVERSATION_STATE_PRUNE_INTERVAL_MS = 5 * 60 * 1000;
const QQ_GROUP_SESSION_ROLLOVER_LINE_LIMIT = 420;
const QQ_SESSION_DEPTH_CACHE_TTL_MS = 15_000;
const QQ_ONE_SUN_LEVEL = 16;
const DEFAULT_CHINOBOT_PROJECT_ROOT = process.env.OPENCLAW_CHINOBOT_PROJECT_ROOT || "..";
const DEFAULT_CHINOBOT_BRIDGE_SCRIPT =
  process.env.OPENCLAW_CHINOBOT_BRIDGE_SCRIPT ||
  path.join(DEFAULT_CHINOBOT_PROJECT_ROOT, "bridge", "openclaw_tool_bridge.py");
const DEFAULT_CHINOBOT_BRIDGE_TIMEOUT_MS = 30_000;
const QQ_DIRECT_MEDIA_FETCH_HOSTS = new Set([
  "multimedia.nt.qq.com.cn",
  "gchat.qpic.cn",
  "c2cpicdw.qpic.cn",
]);
export const QQ_DEBUG_LOG_PATH = path.join(
  os.homedir(),
  ".openclaw",
  "logs",
  "qq-ingress-debug.jsonl",
);
const QQ_IMAGE_SUMMARY_PROMPT = [
  "你在给 QQ 机器人做图片上下文结构化。",
  "只输出 JSON，不要 markdown，不要解释。",
  '字段固定为 {"vision_summary":"","alt":"","ocr":""}。',
  "vision_summary: 用 1-2 句中文概括画面和表达的情绪/梗感。",
  "alt: 用更短的一句中文说这是什么图。",
  "ocr: 只写图里清晰可读的文字；没有就写空字符串。",
  "不要乱认角色出处；不确定就明确说不确定。",
].join(" ");
const QQ_REFERENTIAL_MEDIA_RE =
  /(看这个|看这张|这个怎么样|这张怎么样|给这图配一句|给这张图配一句|这个|这张|上一张|上一条图|刚那个|刚刚那个|不是这张|你刚发那个|再来一张|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图)/u;
const QQ_EXPLICIT_MESSAGE_RE =
  /(看这个|这个怎么样|这张怎么样|给这图配一句|给这张图配一句|帮我|锐评|评价|怎么|啥|是什么|发|再来|别只|配一句|问题|？|\?)/u;
const TRANSIENT_UPSTREAM_ERROR_PATTERNS = [
  /an error occurred while processing your request/i,
  /you can retry your request/i,
  /contact us through our help center/i,
  /help\.?openai\.com/i,
  /if the error persists/i,
  /please include the request id/i,
  /request id\s+[a-f0-9-]{8,}/i,
  /请求处理时发生错误/i,
  /请包含 request id/i,
];
const IMAGE_SEARCH_OUTPUT_DIR = path.join(os.tmpdir(), "openclaw-qq-search-images");

const activeConnections = new Map<string, QqConnectionState>();
const recentOutboundMessages = new Map<string, number[]>();
const directFollowupWatches = new Map<string, DirectFollowupWatchState>();
const recentQqDeliveryFingerprints = new Map<string, number>();
const recentQqImageSearchSelections = new Map<string, number>();
const qqImageSearchCursorByKey = new Map<string, number>();
const qqConversationState = new Map<string, QqConversationState>();
const qqPendingBursts = new Map<string, PendingQqBurst>();
const qqConversationInflight = new Map<string, number>();
const qqImageInsightCache = new Map<string, Promise<QqImageInsight>>();
const qqSessionDepthCache = new Map<string, QqSessionDepthCacheEntry>();
let lastQqConversationStatePruneAt = 0;
let runEmbeddedPiAgentLoader: Promise<RunEmbeddedPiAgentFn> | null = null;
let describeImageWithModelLoader: Promise<DescribeImageWithModelFn> | null = null;
let qqStateDirForRecovery: string | null = null;
let qqRecoveryInFlight = false;
let qqInboundRecoveryInFlight = false;
let qqInboundRecoveryStateCache: QqInboundRecoveryState | null = null;
const qqPersonaProfiles: QqPersonaProfile[] = [
  {
    id: "chino",
    label: "智乃",
    aliases: ["chino", "智乃", "香风智乃"],
    promptLines: [
      "Persona overlay: Chino.",
      "If asked who you are or what your name is, answer as 智乃.",
      "Do not mention other personas unless the user is explicitly talking about persona switching.",
      "Keep the tone quiet, restrained, polite, and lightly distant.",
      "Show gentleness through understatement instead of overt excitement.",
      "Use concise wording and mild warmth, like a calm cafe girl who rarely overreacts.",
    ],
  },
  {
    id: "miko",
    label: "Miko",
    aliases: ["miko", "Miko", "米可", "美子"],
    promptLines: [
      "Persona overlay: Miko.",
      "If asked who you are or what your name is, answer as Miko.",
      "Do not mention other personas unless the user is explicitly talking about persona switching.",
      "Keep the tone alert, intimate, and slightly playful, as if chatting through a live message thread.",
      "Allow a bit more teasing, curiosity, and emotional immediacy than Chino, but still stay concise.",
      "Do not become loud or essay-like; keep it like quick, human-feeling message bursts.",
    ],
  },
];
const qqPersonaProfileByAlias = new Map<string, QqPersonaProfile>(
  qqPersonaProfiles.flatMap((profile) =>
    [profile.id, profile.label, ...profile.aliases].map(
      (alias) => [alias.toLowerCase(), profile] as const,
    ),
  ),
);
let qqPersonaStateCache: Record<string, string> | null = null;

type DirectFollowupWatchState = {
  accountId: string;
  groupId: string;
  senderId: string;
  activatedAt: number;
  lastRelatedAt: number;
  lastObservedAt: number;
  lastBotReplyAt: number | null;
  consecutiveMisses: number;
  lastUserRelatedPreview: string;
  lastBotReplyPreview: string;
};

type RunEmbeddedPiAgentFn = (params: Record<string, unknown>) => Promise<unknown>;
type DescribeImageWithModelFn = (params: {
  buffer: Buffer;
  fileName: string;
  mime?: string;
  model: string;
  provider: string;
  prompt?: string;
  maxTokens?: number;
  timeoutMs: number;
  profile?: string;
  preferredProfile?: string;
  agentDir: string;
  cfg: OpenClawConfig;
}) => Promise<{ text: string; model?: string }>;

function normalizeWsPath(pathname: string): string {
  const trimmed = pathname.trim();
  if (!trimmed) {
    return "/";
  }
  const withLeading = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  if (withLeading.length > 1 && withLeading.endsWith("/")) {
    return withLeading.slice(0, -1);
  }
  return withLeading;
}

function buildAcceptedPaths(primaryPath: string): Set<string> {
  const normalized = normalizeWsPath(primaryPath);
  const accepted = new Set<string>([normalized]);
  if (normalized.endsWith("/ws")) {
    accepted.add(normalized.slice(0, -3));
  } else {
    accepted.add(`${normalized}/ws`);
  }
  accepted.add(`${normalized}/`);
  return accepted;
}

function readLocalQqActionBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    let total = 0;
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => {
      total += chunk.length;
      if (total > QQ_CODEX_LOCAL_ACTION_MAX_BYTES) {
        reject(new Error("request too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("error", reject);
    req.on("end", () => {
      try {
        const text = Buffer.concat(chunks).toString("utf8").trim();
        resolve(text ? (JSON.parse(text) as Record<string, unknown>) : {});
      } catch (error) {
        reject(error);
      }
    });
  });
}

function writeLocalQqActionJson(
  res: ServerResponse,
  statusCode: number,
  body: Record<string, unknown>,
) {
  res.writeHead(statusCode, { "content-type": "application/json; charset=utf-8" });
  res.end(`${JSON.stringify(body)}\n`);
}

function containsCjkText(text: string) {
  return /[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/u.test(text);
}

async function ensureUniqueLocalQqVoiceFile(filePath: string) {
  let candidate = filePath;
  const extension = path.extname(filePath);
  const basename = filePath.slice(0, extension ? -extension.length : undefined);
  let suffix = 1;
  while (fs.existsSync(candidate)) {
    candidate = `${basename}-${suffix}${extension}`;
    suffix += 1;
  }
  await fs.promises.mkdir(path.dirname(candidate), { recursive: true });
  return candidate;
}

async function synthesizeLocalQqCodexVoiceFromText(text: string, rawVoiceSynthesisConfig: unknown) {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("text 不能为空");
  }
  const voiceSynthesisConfig = resolveLocalQwenCloneTtsConfig(rawVoiceSynthesisConfig);
  if (voiceSynthesisConfig.enabled) {
    const clonedOutputPath = await ensureUniqueLocalQqVoiceFile(
      path.join(QQ_CODEX_LOCAL_VOICE_OUTPUT_DIR, `qq-codex-voice-${Date.now()}.wav`),
    );
    try {
      return await synthesizeLocalQwenCloneTts({
        text: trimmed,
        outputPath: clonedOutputPath,
        config: voiceSynthesisConfig,
      });
    } catch (error) {
      if (!voiceSynthesisConfig.fallbackToSystemSay) {
        throw error;
      }
    }
  }
  const outputPath = await ensureUniqueLocalQqVoiceFile(
    path.join(QQ_CODEX_LOCAL_VOICE_OUTPUT_DIR, `qq-codex-voice-${Date.now()}.aiff`),
  );
  const args = containsCjkText(trimmed)
    ? ["-v", "Ting-Ting", trimmed, "-o", outputPath]
    : [trimmed, "-o", outputPath];
  await runExecFilePromise("/usr/bin/say", args);
  return outputPath;
}

function normalizeLocalQqActionTargetKind(value: unknown): "user" | "group" {
  const normalized = String(value ?? "").trim();
  if (normalized === "user" || normalized === "group") {
    return normalized;
  }
  throw new Error("target_kind must be user or group");
}

async function handleLocalQqActionRequest(params: {
  req: IncomingMessage;
  res: ServerResponse;
  cfg: CoreConfig;
  defaultAccountId: string;
  pluginConfig?: unknown;
}) {
  if (params.req.method !== "POST") {
    writeLocalQqActionJson(params.res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  try {
    const body = await readLocalQqActionBody(params.req);
    const action = String(body.action ?? "").trim();
    if (!QQ_CODEX_LOCAL_ACTIONS.has(action)) {
      writeLocalQqActionJson(params.res, 400, { ok: false, error: `action not allowed: ${action}` });
      return;
    }
    const actionParams =
      body.params && typeof body.params === "object" && !Array.isArray(body.params)
        ? (body.params as Record<string, unknown>)
        : {};
    if (action === "qq_send_voice") {
      const targetKind = normalizeLocalQqActionTargetKind(
        actionParams.target_kind ?? actionParams.targetKind,
      );
      const targetId = String(actionParams.target_id ?? actionParams.targetId ?? "").trim();
      if (!targetId) {
        throw new Error("target_id is required");
      }
      const text = String(actionParams.text ?? "").trim();
      const audioUrl = String(
        actionParams.audio_url ?? actionParams.audioUrl ?? actionParams.audio_path ?? actionParams.audioPath ?? "",
      ).trim();
      const caption = String(actionParams.caption ?? "").trim();
      const preferPtt = actionParams.prefer_ptt !== false && actionParams.preferPtt !== false;
      const replyToMessageId = String(
        actionParams.reply_to ?? actionParams.replyTo ?? actionParams.reply_to_message_id ?? "",
      ).trim();
      if (!text && !audioUrl) {
        throw new Error("text、audio_url 或 audio_path 至少提供一个");
      }
      if (actionParams.dry_run === true || actionParams.dryRun === true) {
        const voiceSynthesisConfig = resolveLocalQwenCloneTtsConfig(
          (params.pluginConfig as { voiceSynthesis?: unknown } | undefined)?.voiceSynthesis,
        );
        writeLocalQqActionJson(params.res, 200, {
          ok: true,
          dry_run: true,
          action,
          target_kind: targetKind,
          target_id: targetId,
          account_id: String(body.accountId ?? params.defaultAccountId),
          text: text || null,
          audio_url: audioUrl || null,
          caption,
          synthesize_on_send: !audioUrl && Boolean(text),
          synthesis_provider: audioUrl
            ? "user-supplied-audio"
            : voiceSynthesisConfig.enabled
              ? "local-qwen-clone"
              : "system-say",
          synthesis_voice_name: audioUrl
            ? null
            : voiceSynthesisConfig.enabled
              ? voiceSynthesisConfig.voiceName
              : containsCjkText(text)
                ? "Ting-Ting"
                : "default",
          qwen_voice_name: audioUrl || !voiceSynthesisConfig.enabled ? null : voiceSynthesisConfig.voiceName,
          preferred_mode: preferPtt ? "ptt" : "audio",
          fallback_mode: preferPtt ? "audio" : "ptt",
          final_fallback: "text",
          capabilities: ["qq-ptt", "qq-audio-file", "qq-text-only"],
        });
        return;
      }
      const mediaUrl =
        audioUrl ||
        (await synthesizeLocalQqCodexVoiceFromText(
          text,
          (params.pluginConfig as { voiceSynthesis?: unknown } | undefined)?.voiceSynthesis,
        ));
      const outcome = await sendQqVoice({
        cfg: params.cfg,
        accountId: String(body.accountId ?? params.defaultAccountId),
        targetKind,
        targetId,
        audioUrl: mediaUrl,
        caption,
        preferPtt,
        replyToMessageId: replyToMessageId || undefined,
      });
      writeLocalQqActionJson(params.res, 200, {
        ok: outcome.ok,
        action,
        target_kind: targetKind,
        target_id: targetId,
        text: text || null,
        audio_url: mediaUrl,
        caption,
        mode: outcome.mode,
        capability: outcome.capability,
        attempts: outcome.attempts,
        result: outcome.result,
        message_id: (outcome.result.data as Record<string, unknown> | undefined)?.message_id ?? null,
      });
      return;
    }
    const result = await sendAction({
      cfg: params.cfg,
      accountId: String(body.accountId ?? params.defaultAccountId),
      action,
      params: actionParams,
      timeoutMs: Number(body.timeoutMs ?? 10_000),
    });
    writeLocalQqActionJson(params.res, 200, {
      ok: isOneBotActionAccepted(result),
      action,
      result,
    });
  } catch (error) {
    writeLocalQqActionJson(params.res, 500, {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

function parseMessageSegments(
  message: string | OneBotMessageSegment[] | undefined,
  selfId?: string,
): ParsedQqMessage {
  if (typeof message === "string") {
    return {
      text: message.trim(),
      isReply: false,
      replyToMessageId: undefined,
      wasMentioned: false,
      mentionIds: [],
      imageUrls: [],
      mediaSegments: [],
      hasOnlyMediaLike: false,
    };
  }

  const parts: string[] = [];
  const imageUrls: string[] = [];
  const mentionIds: string[] = [];
  const mediaSegments: ParsedQqMessage["mediaSegments"] = [];
  let isReply = false;
  let replyToMessageId: string | undefined;
  let wasMentioned = false;

  for (const seg of message ?? []) {
    if (seg.type === "text") {
      parts.push(String(seg.data?.text ?? ""));
      continue;
    }
    if (seg.type === "at") {
      const qq = String(seg.data?.qq ?? "").trim();
      if (qq && qq !== "all") {
        mentionIds.push(qq);
        parts.push(`[QQ:${qq}]`);
        if (selfId && qq === selfId) {
          wasMentioned = true;
        }
      }
      continue;
    }
    if (seg.type === "reply") {
      isReply = true;
      const replyId = String(seg.data?.id ?? "").trim();
      replyToMessageId = replyId || replyToMessageId;
      continue;
    }
    if (seg.type === "image") {
      const rawFile = String(seg.data?.file ?? "").trim();
      const rawUrl = String(seg.data?.url ?? "").trim();
      const url = resolvePreferredQqInboundImageRef(seg.data);
      if (url) {
        imageUrls.push(url);
      }
      mediaSegments.push({
        type: "image",
        sourceType: seg.type,
        url: url || undefined,
        label: "图片",
        rawFile: rawFile || undefined,
        rawUrl: rawUrl || undefined,
        preferredRef: url || undefined,
        localFileResolved: Boolean(rawFile && resolveLocalMediaReference(rawFile)),
        data: seg.data,
      });
      continue;
    }
    if (seg.type === "face" || seg.type === "mface") {
      const faceId = String(seg.data?.id ?? seg.data?.face_id ?? "").trim();
      const label =
        seg.type === "mface"
          ? `动画表情${faceId ? ` #${faceId}` : ""}`
          : `QQ表情${faceId ? ` #${faceId}` : ""}`;
      mediaSegments.push({
        type: seg.type === "mface" ? "animated_emoji" : "emoji",
        sourceType: seg.type,
        label,
        data: seg.data,
      });
      continue;
    }
  }

  const text = parts.join("").trim();
  return {
    text,
    isReply,
    replyToMessageId,
    wasMentioned,
    mentionIds,
    imageUrls,
    mediaSegments,
    hasOnlyMediaLike: !text && mediaSegments.length > 0,
  };
}

function buildQqConversationKey(accountId: string, event: OneBotMessageEvent): string {
  return event.message_type === "group"
    ? `qq:${accountId}:group:${String(event.group_id ?? "")}`
    : `qq:${accountId}:direct:${String(event.user_id)}`;
}

function normalizeQqCodexReasoningEffort(
  raw: string | undefined | null,
): QqCodexReasoningEffort {
  const value = String(raw ?? "").trim().toLowerCase();
  if (["none", "minimal", "fast", "quick", "快", "快速", "低", "低思考"].includes(value)) {
    return "low";
  }
  if (["medium", "med", "normal", "balanced", "标准", "普通", "平衡"].includes(value)) {
    return "medium";
  }
  if (["high", "deep", "认真", "深入", "高", "高思考"].includes(value)) {
    return "high";
  }
  return "xhigh";
}

function labelQqCodexReasoningEffort(effort: QqCodexReasoningEffort): string {
  switch (effort) {
    case "low":
      return "快速";
    case "medium":
      return "平衡";
    case "high":
      return "深度";
    case "xhigh":
      return "最高";
  }
}

const qqBrainTargets = new Map<string, QqBrainTarget>();
let qqBrainTargetsLoaded = false;
const qqCodexReasoningEfforts = new Map<string, QqCodexReasoningEffort>();
let qqCodexReasoningLoaded = false;

function loadQqBrainTargets() {
  if (qqBrainTargetsLoaded) {
    return;
  }
  qqBrainTargetsLoaded = true;
  try {
    const parsed = JSON.parse(fs.readFileSync(QQ_BRAIN_STATE_FILE, "utf8")) as Record<
      string,
      QqBrainTarget
    >;
    for (const [key, target] of Object.entries(parsed)) {
      if (target === "codex" || target === "openclaw") {
        qqBrainTargets.set(key, target);
      }
    }
  } catch {
    // Missing or malformed state should not block QQ message handling.
  }
}

function saveQqBrainTargets() {
  try {
    fs.mkdirSync(path.dirname(QQ_BRAIN_STATE_FILE), { recursive: true });
    fs.writeFileSync(
      QQ_BRAIN_STATE_FILE,
      `${JSON.stringify(Object.fromEntries(qqBrainTargets), null, 2)}\n`,
    );
  } catch {
    // Best-effort persistence only; runtime routing still works in memory.
  }
}

function loadQqCodexReasoningEfforts() {
  if (qqCodexReasoningLoaded) {
    return;
  }
  qqCodexReasoningLoaded = true;
  try {
    const parsed = JSON.parse(fs.readFileSync(QQ_CODEX_REASONING_STATE_FILE, "utf8")) as Record<
      string,
      string
    >;
    for (const [key, effort] of Object.entries(parsed)) {
      qqCodexReasoningEfforts.set(key, normalizeQqCodexReasoningEffort(effort));
    }
  } catch {
    // Missing or malformed state should not block QQ message handling.
  }
}

function saveQqCodexReasoningEfforts() {
  try {
    fs.mkdirSync(path.dirname(QQ_CODEX_REASONING_STATE_FILE), { recursive: true });
    fs.writeFileSync(
      QQ_CODEX_REASONING_STATE_FILE,
      `${JSON.stringify(Object.fromEntries(qqCodexReasoningEfforts), null, 2)}\n`,
    );
  } catch {
    // Best-effort persistence only.
  }
}

function getQqCodexReasoningEffort(conversationKey: string): QqCodexReasoningEffort {
  loadQqCodexReasoningEfforts();
  return qqCodexReasoningEfforts.get(conversationKey) ?? QQ_CODEX_REASONING_EFFORT;
}

function setQqCodexReasoningEffort(
  conversationKey: string,
  effort: QqCodexReasoningEffort,
) {
  loadQqCodexReasoningEfforts();
  qqCodexReasoningEfforts.set(conversationKey, effort);
  saveQqCodexReasoningEfforts();
}

function isQqCodexNewChatCommand(rawBody: string) {
  const text = rawBody.trim().replace(/^\/codex[\s.。:：,，-]*/i, "");
  return /^(开启|打开|新建|开个|开一个|重新开|重开|开始|进入)?\s*(新聊天|新会话|新窗口|新对话|new\s*chat|new\s*conversation)\s*(窗口|模式)?$/iu.test(text) ||
    /^(清空|清除|重置|忘掉|刷新)\s*(上下文|聊天记录|会话|对话|context)$/iu.test(text);
}

function resolveQqCodexSessionDir(conversationKey: string) {
  return path.join(
    QQ_CODEX_WORKSPACE,
    ".qq-codex-openclaw",
    conversationKey.replace(/[^a-zA-Z0-9_.-]+/g, "_").slice(0, 120),
  );
}

async function resetQqCodexConversationContext(conversationKey: string) {
  await fs.promises.rm(resolveQqCodexSessionDir(conversationKey), {
    recursive: true,
    force: true,
  });
}

function parseQqCodexReasoningCommand(rawBody: string): QqCodexReasoningCommand | null {
  const trimmed = rawBody.trim();
  const normalized = trimmed.replace(/\s+/g, " ");
  const withoutPrefix = normalized.replace(/^\/(?:codex|chatgpt|gpt)[\s.。:：,，-]*/i, "");
  const text = withoutPrefix.toLowerCase();
  if (!/(思考|推理|reasoning|thinking|模式|性能)/i.test(withoutPrefix)) {
    return null;
  }
  let effort: QqCodexReasoningEffort | null = null;
  if (/(最高|最强|拉满|满血|认真想|仔细想|多想|xhigh|extra\s*high|max)/i.test(withoutPrefix)) {
    effort = "xhigh";
  } else if (/(高思考|深度|深入|认真|high|deep)/i.test(withoutPrefix)) {
    effort = "high";
  } else if (/(平衡|标准|普通|默认|正常|medium|balanced|normal)/i.test(withoutPrefix)) {
    effort = "medium";
  } else if (/(快速|快点|快一点|低思考|省点|简单想|low|fast|quick|minimal|none)/i.test(withoutPrefix)) {
    effort = "low";
  }
  if (!effort) {
    return null;
  }
  const body = normalized
    .replace(/^\/(?:codex|chatgpt|gpt)[\s.。:：,，-]*/i, "")
    .replace(/(?:请)?(?:把|切到|切换到|改成|换成|使用|用|开启|进入)?\s*(?:codex\s*)?(?:最高|最强|拉满|满血|认真想|仔细想|深度思考|多想|高思考|深度|深入|认真|平衡|标准|普通|默认|正常|快速|快点|快一点|低思考|省点|简单想|xhigh|extra\s*high|max|high|deep|medium|balanced|normal|low|fast|quick|minimal|none)\s*(?:思考|推理|reasoning|thinking)?\s*(?:模式|强度|档位|等级)?/gi, "")
    .replace(/^[\s，。,.、:：-]+/, "")
    .trim();
  return { effort, label: labelQqCodexReasoningEffort(effort), body };
}

function parseQqBrainCommand(rawBody: string): QqBrainCommand | null {
  const trimmed = rawBody.trim();
  const match = trimmed.match(/^\/(chat|openclaw|codex)(?:[\s.。:：,，-]+([\s\S]*))?$/i);
  if (!match) {
    return null;
  }
  const command = match[1]?.toLowerCase();
  const target: QqBrainTarget = command === "codex" ? "codex" : "openclaw";
  return {
    target,
    body: (match[2] ?? "").trim(),
    explicitSwitch: true,
  };
}

function resolveQqBrainTarget(params: { conversationKey: string; rawBody: string }): QqBrainCommand {
  loadQqBrainTargets();
  const command = parseQqBrainCommand(params.rawBody);
  if (command) {
    qqBrainTargets.set(params.conversationKey, command.target);
    saveQqBrainTargets();
    return command;
  }
  return {
    target: qqBrainTargets.get(params.conversationKey) ?? "openclaw",
    body: params.rawBody.trim(),
    explicitSwitch: false,
  };
}

function buildQqCodexPrompt(params: {
  event: OneBotMessageEvent;
  body: string;
  senderName?: string;
  imagePaths?: string[];
  reasoningEffort?: QqCodexReasoningEffort;
  followupContext?: string;
}): string {
  const target =
    params.event.message_type === "group"
      ? `group:${String(params.event.group_id ?? "")}`
      : `user:${String(params.event.user_id)}`;
  const peer =
    params.event.message_type === "group"
      ? `QQ group ${String(params.event.group_id ?? "")}, user ${String(params.event.user_id)}`
      : `QQ private user ${String(params.event.user_id)}`;
  const groupNaturalStyleLines =
    params.event.message_type === "group"
      ? [
          "群聊自然聊天风格仅在当前是 QQ 群聊时启用：优先像群成员一样自然接话，而不是像客服/正式助手。",
          "群聊里默认短、轻、克制：1 句为主，必要时最多 2 句；少用标点、少用 emoji、少用列表和长解释；常见笑法可用 哈哈 / hhh，语气词可轻用 啊 / 吧 / 呢。",
          "群聊里先回应社交动作，再解释；不要每次都总结、科普、追问或说“如果你愿意我还能……”。没人明确问你、插话会打断气氛、或只是人类之间闲聊时，宁可少说或不主动发工具消息。",
          "群聊里遇到戳一戳/拍一拍这类互动，理解成对方在调皮地碰你/吸引你注意；可短句害羞、吐槽或假装抱怨，例如“又偷摸我啊”“你这人怎么还上手呢”。",
        ]
      : [];
  const privateProactiveToolLines =
    params.event.message_type === "private"
      ? [
          "私聊里可以主动使用你拥有的 QQ 工具来优化聊天体验，不必等用户把每个动作说得很明确；前提是工具动作明显能让回复更好、更清楚或更有陪伴感。",
          "私聊主动工具策略：适合用语音表达安慰、鼓励、口语解释、睡前/故事或轻松陪聊时，可主动 `voice`；适合清晰阅读的作业答案、步骤、表格、清单、长解释时，可主动渲染成图片卡片；用户想要视觉内容/表情包/头像/海报时，主动使用生图、HTML 渲染或发图。",
          "私聊里可主动使用回复引用、图片、语音、渲染卡片、生成图片、查询上下文等能力，但不要为了炫技乱用工具；工具发出的内容必须是用户当前会想收到的最终内容，而不是进度提示。",
          "主动用工具前不需要发“我来帮你处理一下”这类预告；工具成功发送完整内容后，只输出 `QQ_CODEX_SENT`。如果工具失败，再用自然文字简短说明并给出可用结果。",
        ]
      : [];
  return [
    "你正在通过 QQ 和用户对话。请自然、简洁地用中文回复，除非用户明确要求其它语言。",
    "不要提到内部命令、OpenClaw 或 Codex 路由细节，除非用户问。",
    "当前默认人设是 Miko：如果被问你是谁或叫什么，回答你是 Miko。不要提到其它人设，除非用户在讨论切换人设。",
    "Miko 的说话方式：机灵、亲近、稍微俏皮，像在即时聊天里回消息；可以有一点调侃、好奇和情绪即时反应，但仍然简洁，不要吵闹、不要长篇作文。",
    `你可以使用本地 QQ 桥接工具调用 OpenClaw 的 QQ 能力。工具路径：${path.join(QQ_CODEX_WORKSPACE, "bin", "qq_codex_bridge")}。`,
    "常用命令：qq_codex_bridge context；qq_codex_bridge send-text --text '内容'；qq_codex_bridge reply --text '内容' --reply-to 消息ID；qq_codex_bridge send-mention --target group:群号 --user QQ号 --text '内容'；qq_codex_bridge send-image --path /absolute/path.png --text '说明'；qq_codex_bridge voice --text '要说的话' --caption '语音内容摘要'；qq_codex_bridge render-html --file /absolute/path.html；qq_codex_bridge render-html-send --file /absolute/path.html --text '说明'；qq_codex_bridge generate-image-send --prompt '图片描述' --text '说明'。",
    "QQ 查询/管理命令：qq_codex_bridge self；qq_codex_bridge groups；qq_codex_bridge members --group 群号；qq_codex_bridge user-info --user QQ号；qq_codex_bridge group-info --group 群号；qq_codex_bridge permissions --target group:群号；qq_codex_bridge timeout --group 群号 --user QQ号 --duration-min 分钟；qq_codex_bridge kick --group 群号 --user QQ号；qq_codex_bridge delete --message-id 消息ID。",
    "QQ 互动命令：qq_codex_bridge like --user QQ号 --times 次数；qq_codex_bridge poke --target group:群号 --user QQ号；qq_codex_bridge forward --target group:群号 --node '昵称:QQ号:内容'（可重复 --node 发送合并转发）；qq_codex_bridge react --target group:群号 --message-id 消息ID --emoji '👍' 在支持时可加反应。",

    "你有两种生图能力：1) 模型原生生图：qq_codex_bridge generate-image/generate-image-send，适合照片、插画、头像、海报、风格化图像；2) HTML 渲染生图：qq_codex_bridge render-html/render-html-send，适合排版卡片、作业答案图、表格、信息图、流程图、含大量文字的清晰版式。",
    "请智能判断回复形式，不必每次都纯文字：如果用户明确要求语音/朗读/发一段语音/语音回复，或你的回复更像陪伴、安慰、鼓励、睡前/故事、口语化解释、简短状态播报，且内容适合 5-40 秒听完，可以主动使用 `qq_codex_bridge voice --text '内容' --caption '简短摘要'` 发送语音。",
    "不适合主动发语音的情况：代码、表格、公式、长步骤、作业/考试答案、需要复制粘贴的信息、链接/命令、隐私敏感内容、用户在公共群里可能不方便听语音、或内容超过约 120 字；这些场景优先文字或答案图片。",
    "语音内容要像真人发 QQ 语音：自然口语、短句、不要读出 markdown/代码/链接；如果主动发送了完整语音，最终文本只输出 `QQ_CODEX_SENT`，不要说“已发送/已回复/发送完成”这类机器确认语。也可用 `--path` 或 `--audio-url` 发送已有音频。",
    ...privateProactiveToolLines,
    ...groupNaturalStyleLines,
    "如果你通过 qq_codex_bridge 主动发送了完整回复，最后只输出 `QQ_CODEX_SENT`，避免系统自动再发一条“已发送/已回复”之类的确认语或重复内容。",
    `来源：${peer}`,
    `当前默认目标：${target}`,
    params.reasoningEffort
      ? `当前 Codex 思考模式：${labelQqCodexReasoningEffort(params.reasoningEffort)}（${params.reasoningEffort}）。用户可以自然语言要求你切换为快速/平衡/深度/最高思考模式。`
      : undefined,
    params.followupContext,
    params.senderName ? `昵称：${params.senderName}` : undefined,
    params.imagePaths && params.imagePaths.length > 0
      ? `用户随消息附带了 ${params.imagePaths.length} 张图片，已作为视觉输入传给你；请直接查看图片内容，不要说无法解析。`
      : undefined,
    params.imagePaths && params.imagePaths.length > 0
      ? [
          "如果图片内容像作业题、试卷题、练习题、数学/计算机/英语等题目，默认按考试作答模式处理：先完整读题并解题，然后把最终答案渲染成一张或多张清晰图片发回。",
          "考试作答模式要求：答案要适合直接写进试卷/作业；步骤清楚但不啰嗦；保留关键公式、定义、推导和最终结论；不要用聊天口吻、不要只给思路、不要让用户再追问。",
          "发送答案图片时优先使用 `qq_codex_bridge render-html-send --file /absolute/path/to/answer.html --text '答案整理好了' --width 900 --height 1200 --scale 2`；HTML 请使用白底深色字、较大字号、清晰分节、公式/表格易读，内容较多就拆成多张答案卡。",
          "如果你已经用 `render-html-send` 或 `send-image` 发出了完整答案，最终文本只输出 `QQ_CODEX_SENT`，避免系统再自动发送一大段纯文字或“已发送”。",
        ].join("\n")
      : undefined,
    "用户消息：",
    params.body,
  ]
    .filter((line): line is string => Boolean(line))
    .join("\n");
}

function buildQqCodexFollowupContext(params: {
  event: OneBotMessageEvent;
  parsed: ParsedQqMessage;
  followupWatch?: ReturnType<typeof evaluateDirectFollowupWatch>;
  semanticFollowup?: { allowed: boolean; confidence?: number; reason?: string };
  pendingCount?: number;
}) {
  if (params.event.message_type !== "group") {
    return undefined;
  }
  const lines = [
    "群聊回话追踪机制：当一名群成员 @你/引用你/直接问你后，会短时间进入 active follow-up watch；同一说话人后续即使没再 @，只要像补充、澄清、追问、回应你上一句，也应当当作同一段对话继续处理。",
    "如果当前消息属于追踪续聊：不要重新开场、不要解释自己为什么插话；直接接上上一轮语境，保持短、自然、低打扰。若消息明显是和别人说话、系统消息、或普通群聊闲聊，就不要强行接话。",
    "判断续聊的线索包括：同一人、距离上一轮不久、短句、含“那/所以/我是说/还有/刚才/你觉得/你能/你懂了”等接续词，或语义判定为 clarification/reaction/continuation。",
  ];
  if (params.parsed.wasMentioned || params.parsed.isReply) {
    lines.push("本条消息直接 @/引用了你：应视为直接对你说话，并刷新后续追踪窗口。");
  }
  if (params.followupWatch?.allowed || params.semanticFollowup?.allowed) {
    lines.push("本条消息被回话追踪判定为同一说话人的续聊：请按延续上下文回复，但保持简短。");
  } else if (params.followupWatch?.reason) {
    lines.push(`当前追踪状态：${params.followupWatch.reason}${typeof params.followupWatch.score === "number" ? `，规则分 ${params.followupWatch.score}` : ""}。`);
  }
  if (params.semanticFollowup?.allowed) {
    lines.push(`语义续聊判定置信度：${params.semanticFollowup.confidence ?? 0}。`);
  }
  if ((params.pendingCount ?? 0) >= 3) {
    lines.push("当前群聊队列较忙：优先处理最新明确问题或直接指令，不要展开太多。");
  }
  return lines.join("\n");
}

async function runQqCodexTurn(params: {
  prompt: string;
  conversationKey: string;
  event: OneBotMessageEvent;
  senderName?: string;
  imagePaths?: string[];
  reasoningEffort?: QqCodexReasoningEffort;
}): Promise<string> {
  await fs.promises.mkdir(QQ_CODEX_WORKSPACE, { recursive: true });
  await fs.promises.mkdir(path.dirname(QQ_CODEX_CONTEXT_FILE), { recursive: true });
  await fs.promises.writeFile(
    QQ_CODEX_CONTEXT_FILE,
    `${JSON.stringify(
      {
        account_id: "default",
        conversation_key: params.conversationKey,
        message_type: params.event.message_type,
        target:
          params.event.message_type === "group"
            ? `group:${String(params.event.group_id ?? "")}`
            : `user:${String(params.event.user_id)}`,
        user_id: String(params.event.user_id),
        group_id: params.event.message_type === "group" ? String(params.event.group_id ?? "") : undefined,
        sender_name: params.senderName,
        message_id: params.event.message_id ? String(params.event.message_id) : undefined,
        updated_at: new Date().toISOString(),
      },
      null,
      2,
    )}\n`,
  );
  const sessionDir = resolveQqCodexSessionDir(params.conversationKey);
  await fs.promises.mkdir(sessionDir, { recursive: true });
  const outFile = path.join(sessionDir, "last-message.txt");
  const imageArgs = buildQqCodexImageArgs(params.imagePaths ?? []);
  const reasoningEffort = params.reasoningEffort ?? QQ_CODEX_REASONING_EFFORT;
  const compactedPrompt = compactQqCodexPromptForModelLimit(params.prompt);
  const args = [
    "--sandbox",
    "danger-full-access",
    "--model",
    QQ_CODEX_MODEL,
    "--config",
    `model_reasoning_effort=\"${reasoningEffort}\"`,
    "exec",
    "--json",
    "--cd",
    QQ_CODEX_WORKSPACE,
    "--skip-git-repo-check",
    "--output-last-message",
    outFile,
    ...imageArgs,
    compactedPrompt,
  ];
  await new Promise<void>((resolve, reject) => {
    const child = spawn(QQ_CODEX_BIN, args, {
      cwd: QQ_CODEX_WORKSPACE,
      env: {
        ...process.env,
        PATH: `${path.join(QQ_CODEX_WORKSPACE, "bin")}:${process.env.PATH ?? ""}`,
        QQ_CODEX_CONTEXT_FILE,
      },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`Codex timed out after ${QQ_CODEX_TIMEOUT_MS}ms`));
    }, QQ_CODEX_TIMEOUT_MS);
    child.stderr?.on("data", (chunk) => {
      stderr += String(chunk);
      if (stderr.length > 8000) {
        stderr = stderr.slice(-8000);
      }
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code, signal) => {
      clearTimeout(timer);
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`Codex exited ${signal ?? code}${stderr ? `: ${stderr.slice(-1200)}` : ""}`));
    });
  });
  const text = await fs.promises.readFile(outFile, "utf8").catch(() => "");
  return text.trim() || "（Codex 执行完成，但没有返回文本）";
}

function buildQqCodexImageArgs(imagePaths: string[]): string[] {
  const args: string[] = [];
  const seen = new Set<string>();
  for (const rawPath of imagePaths) {
    const imagePath = String(rawPath || "").trim();
    if (!imagePath || seen.has(imagePath) || !fs.existsSync(imagePath)) {
      continue;
    }
    seen.add(imagePath);
    args.push(`--image=${imagePath}`);
  }
  return args;
}

function chunkQqCodexReply(text: string): string[] {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }
  if (/^(QQ_CODEX_SENT|已发送|已回复|发送完成|回复完成|已发出|已处理)(?:[。.!！\s]*)$/u.test(trimmed)) {
    return [];
  }
  const chunks: string[] = [];
  for (let index = 0; index < trimmed.length; index += QQ_CODEX_REPLY_CHUNK_LIMIT) {
    chunks.push(trimmed.slice(index, index + QQ_CODEX_REPLY_CHUNK_LIMIT));
  }
  return chunks;
}

function compactQqCodexPromptForModelLimit(prompt: string): string {
  const limit = Math.max(10_000, QQ_CODEX_PROMPT_CHAR_LIMIT);
  if (prompt.length <= limit) {
    return prompt;
  }
  const keepHead = Math.max(
    2_000,
    Math.min(QQ_CODEX_PROMPT_KEEP_HEAD_CHARS, Math.floor(limit * 0.4)),
  );
  const keepTail = Math.max(
    2_000,
    Math.min(QQ_CODEX_PROMPT_KEEP_TAIL_CHARS, limit - keepHead - 1_000),
  );
  const omittedChars = Math.max(0, prompt.length - keepHead - keepTail);
  return [
    prompt.slice(0, keepHead).trimEnd(),
    "",
    `[QQ-Codex context compacted: omitted ${omittedChars} chars from the middle to stay within model limits. Preserve system rules above and prioritize the latest user message below.]`,
    "",
    prompt.slice(-keepTail).trimStart(),
  ].join("\n");
}

function resolveQqSessionTranscriptPath(params: {
  storePath: string;
  sessionId: string;
  sessionFile?: string;
}): string {
  const explicit = params.sessionFile?.trim();
  if (explicit) {
    return explicit;
  }
  return path.join(path.dirname(params.storePath), `${params.sessionId}.jsonl`);
}

function countQqSessionTranscriptLines(sessionFile: string): number {
  if (!sessionFile || !fs.existsSync(sessionFile)) {
    return 0;
  }
  const raw = fs.readFileSync(sessionFile, "utf8");
  if (!raw.trim()) {
    return 0;
  }
  return raw.split("\n").filter((line) => line.trim().length > 0).length;
}

function maybeMarkQqSessionForRollover(params: {
  api: OpenClawPluginApi;
  storePath: string;
  sessionKey: string;
  conversationKey: string;
  lineLimit?: number;
}): {
  rolledOver: boolean;
  lineCount: number;
  sessionId?: string;
  sessionFile?: string;
} {
  const storePath = params.storePath.trim();
  const sessionKey = params.sessionKey.trim();
  if (!storePath || !sessionKey || !fs.existsSync(storePath)) {
    return { rolledOver: false, lineCount: 0 };
  }
  let store: Record<string, Record<string, unknown>>;
  try {
    store = JSON.parse(fs.readFileSync(storePath, "utf8")) as Record<
      string,
      Record<string, unknown>
    >;
  } catch (error) {
    params.api.logger.warn(
      `[qq] failed reading session store for rollover check (${params.conversationKey}): ${String(error)}`,
    );
    return { rolledOver: false, lineCount: 0 };
  }
  const entry = store[sessionKey];
  if (!entry || typeof entry !== "object") {
    return { rolledOver: false, lineCount: 0 };
  }
  const sessionId = String(entry.sessionId ?? "").trim();
  if (!sessionId) {
    return { rolledOver: false, lineCount: 0 };
  }
  const sessionFile = resolveQqSessionTranscriptPath({
    storePath,
    sessionId,
    sessionFile: typeof entry.sessionFile === "string" ? entry.sessionFile : undefined,
  });
  const now = Date.now();
  const cached = qqSessionDepthCache.get(sessionKey);
  const lineLimit = Math.max(
    1,
    Math.floor(params.lineLimit ?? QQ_GROUP_SESSION_ROLLOVER_LINE_LIMIT),
  );
  const lineCount =
    cached &&
    cached.sessionId === sessionId &&
    cached.sessionFile === sessionFile &&
    now - cached.checkedAt < QQ_SESSION_DEPTH_CACHE_TTL_MS
      ? cached.lineCount
      : countQqSessionTranscriptLines(sessionFile);
  if (lineCount < lineLimit) {
    qqSessionDepthCache.set(sessionKey, {
      sessionId,
      sessionFile,
      checkedAt: now,
      lineCount,
      rolloverMarked: false,
    });
    return { rolledOver: false, lineCount, sessionId, sessionFile };
  }
  const updatedAt = Number(entry.updatedAt ?? 0);
  if (!Number.isFinite(updatedAt) || updatedAt !== 0) {
    entry.updatedAt = 0;
    fs.writeFileSync(storePath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
    params.api.logger.warn(
      `[qq] forcing session rollover for ${params.conversationKey}: sessionKey=${sessionKey} sessionId=${sessionId} lineCount=${lineCount} limit=${lineLimit}`,
    );
    qqSessionDepthCache.set(sessionKey, {
      sessionId,
      sessionFile,
      checkedAt: now,
      lineCount,
      rolloverMarked: true,
    });
    return { rolledOver: true, lineCount, sessionId, sessionFile };
  }
  qqSessionDepthCache.set(sessionKey, {
    sessionId,
    sessionFile,
    checkedAt: now,
    lineCount,
    rolloverMarked: true,
  });
  return { rolledOver: false, lineCount, sessionId, sessionFile };
}

function pruneInactiveQqConversationStates(now: number) {
  if (now - lastQqConversationStatePruneAt < QQ_CONVERSATION_STATE_PRUNE_INTERVAL_MS) {
    return;
  }
  lastQqConversationStatePruneAt = now;
  for (const [key, state] of qqConversationState.entries()) {
    if (now - state.lastTouchedAt <= QQ_CONVERSATION_STATE_IDLE_TTL_MS) {
      continue;
    }
    if ((qqConversationInflight.get(key) ?? 0) > 0) {
      continue;
    }
    if ((qqPendingBursts.get(key)?.entries.length ?? 0) > 0) {
      continue;
    }
    qqConversationState.delete(key);
  }
}

function getQqConversationState(key: string): QqConversationState {
  const now = Date.now();
  pruneInactiveQqConversationStates(now);
  const existing = qqConversationState.get(key);
  if (existing) {
    existing.lastTouchedAt = now;
    return existing;
  }
  const created: QqConversationState = {
    recentMediaBuffer: [],
    recentMessages: [],
    busyLevel: "idle",
    pendingCount: 0,
    debugEvents: [],
    lastTouchedAt: now,
  };
  qqConversationState.set(key, created);
  return created;
}

function resetQqConversationStateForTest() {
  qqConversationState.clear();
  qqPendingBursts.clear();
  qqConversationInflight.clear();
  recentQqImageSearchSelections.clear();
  qqImageSearchCursorByKey.clear();
}

function resolveQqBusyLevel(pendingCount: number): QqConversationState["busyLevel"] {
  if (pendingCount <= 0) {
    return "idle";
  }
  if (pendingCount <= 1) {
    return "light";
  }
  if (pendingCount <= 3) {
    return "busy";
  }
  return "overloaded";
}

function refreshQqConversationLoad(key: string): QqConversationState {
  const state = getQqConversationState(key);
  const pendingCount =
    (qqConversationInflight.get(key) ?? 0) + (qqPendingBursts.get(key)?.entries.length ?? 0);
  state.pendingCount = pendingCount;
  state.busyLevel = resolveQqBusyLevel(pendingCount);
  return state;
}

function getQqGlobalLoad(excludeConversationKey?: string): {
  totalPendingCount: number;
  competingConversationCount: number;
} {
  const keys = new Set<string>([
    ...qqConversationState.keys(),
    ...qqPendingBursts.keys(),
    ...qqConversationInflight.keys(),
  ]);
  let totalPendingCount = 0;
  let competingConversationCount = 0;
  for (const key of keys) {
    const pendingCount =
      (qqConversationInflight.get(key) ?? 0) + (qqPendingBursts.get(key)?.entries.length ?? 0);
    if (pendingCount <= 0) {
      continue;
    }
    totalPendingCount += pendingCount;
    if (key !== excludeConversationKey) {
      competingConversationCount += 1;
    }
  }
  return {
    totalPendingCount,
    competingConversationCount,
  };
}

function buildQqLoadDebugFields(
  conversationKey: string,
  globalLoadOverride?: { totalPendingCount: number; competingConversationCount: number },
) {
  const globalLoad = globalLoadOverride ?? getQqGlobalLoad(conversationKey);
  return {
    competingConversationCount: globalLoad.competingConversationCount,
    totalPendingCount: globalLoad.totalPendingCount,
  };
}

function inferQqDecisionStage(params: { action?: unknown; mode?: unknown }): QqDecisionStage {
  const mode = String(params.mode ?? "").trim();
  if (mode === "overload_gate") {
    return "overload";
  }
  if (mode === "fairness_gate") {
    return "fairness";
  }
  if (mode === "stale_gate") {
    return "stale";
  }
  if (mode === "mention_gate") {
    return "mention";
  }
  if (
    mode === "explicit_image_search" ||
    mode === "persona_current" ||
    mode === "persona_list" ||
    mode === "persona_switch" ||
    mode === "persona_invalid" ||
    mode === "identity_question"
  ) {
    return "immediate";
  }
  return "dispatch";
}

function pushQqLimited<T>(items: T[], next: T, limit: number): T[] {
  return [...items, next].slice(-limit);
}

function appendQqDebugLog(kind: QqDebugEvent["kind"], payload: Record<string, unknown>) {
  void fs.promises
    .mkdir(path.dirname(QQ_DEBUG_LOG_PATH), { recursive: true })
    .then(() =>
      fs.promises.appendFile(
        QQ_DEBUG_LOG_PATH,
        `${JSON.stringify({ kind, at: new Date().toISOString(), ...payload })}\n`,
        "utf8",
      ),
    )
    .catch(() => {
      // best effort only
    });
}

function recordQqDebugEvent(params: {
  api: OpenClawPluginApi;
  conversationKey: string;
  kind: QqDebugEvent["kind"];
  detail: Record<string, unknown>;
}) {
  const detail =
    params.kind === "dispatch_gate"
      ? {
          decisionStage: inferQqDecisionStage(params.detail),
          ...buildQqLoadDebugFields(params.conversationKey),
          ...params.detail,
        }
      : params.detail;
  const state = getQqConversationState(params.conversationKey);
  state.debugEvents = pushQqLimited(
    state.debugEvents,
    { kind: params.kind, at: Date.now(), detail },
    QQ_DEBUG_EVENT_LIMIT,
  );
  appendQqDebugLog(params.kind, {
    conversationKey: params.conversationKey,
    ...detail,
  });
  params.api.logger.info(
    `[qq] ${params.kind} ${JSON.stringify({ conversationKey: params.conversationKey, ...detail })}`,
  );
}

function summarizeQqMediaPlaceholder(parsed: ParsedQqMessage): string {
  const imageCount = parsed.mediaSegments.filter((segment) => segment.type === "image").length;
  if (imageCount > 0) {
    return `用户发送了${imageCount}张图片`;
  }
  const animatedCount = parsed.mediaSegments.filter(
    (segment) => segment.type === "animated_emoji",
  ).length;
  if (animatedCount > 0) {
    return `用户发送了${animatedCount}个动图表情`;
  }
  const emojiCount = parsed.mediaSegments.filter((segment) => segment.type === "emoji").length;
  if (emojiCount > 0) {
    return `用户发送了${emojiCount}个QQ表情`;
  }
  return "";
}

function normalizeBlockedQqUserIds(blockedUserIds?: string[]): Set<string> {
  if (!Array.isArray(blockedUserIds) || blockedUserIds.length === 0) {
    return new Set();
  }
  return new Set(blockedUserIds.map((value) => String(value).trim()).filter(Boolean));
}

function isBlockedInboundQqSender(account: ResolvedQqAccount, event: OneBotMessageEvent): boolean {
  const senderId = String(event.user_id ?? "").trim();
  if (!senderId) {
    return false;
  }
  return normalizeBlockedQqUserIds(account.config.blockedUserIds).has(senderId);
}

function summarizeQqMediaDebugRecord(record: QqMediaRecord | null | undefined): string {
  if (!record) {
    return "";
  }
  return previewText(
    record.summary || record.caption || record.images?.[0]?.alt || record.type,
    100,
  );
}

function buildQqBurstEntryDebugPreview(entry: QueuedQqInboundEvent): Record<string, unknown> {
  return {
    sender_id: entry.senderId,
    sender_name: entry.senderName ?? "",
    message_id: entry.event.message_id ? String(entry.event.message_id) : "",
    reply_to_message_id: entry.parsed.replyToMessageId ?? "",
    mentioned: entry.parsed.wasMentioned,
    text: previewText(entry.rawBody || summarizeQqMediaPlaceholder(entry.parsed), 120),
    media_count: entry.parsed.mediaSegments.length,
  };
}

function buildQqInboundMediaIngressDebug(entry: QueuedQqInboundEvent): Record<string, unknown>[] {
  return entry.parsed.mediaSegments.map((segment, index) => ({
    index: index + 1,
    type: segment.type,
    source_type: segment.sourceType,
    label: segment.label ?? "",
    raw_file: segment.rawFile ?? "",
    raw_url: segment.rawUrl ?? "",
    raw_url_host: extractQqUrlHost(segment.rawUrl),
    preferred_ref: segment.preferredRef ?? segment.url ?? "",
    preferred_ref_host: extractQqUrlHost(segment.preferredRef ?? segment.url),
    local_file_resolved: segment.localFileResolved === true,
  }));
}

function buildResolvedInboundMediaDebug(
  resolvedMedia: ResolvedInboundMediaEntry[],
): Record<string, unknown>[] {
  return resolvedMedia.map((entry, index) => ({
    index: index + 1,
    source_url: entry.sourceUrl,
    source_url_host: extractQqUrlHost(entry.sourceUrl),
    local_path: entry.localPath ?? "",
    content_type: entry.contentType ?? "",
    resolution: entry.resolution ?? "",
    error: entry.error ?? "",
  }));
}

function looksLikeQqExplicitInstruction(text: string): boolean {
  return QQ_EXPLICIT_MESSAGE_RE.test(text.trim());
}

function looksLikeQqMediaReference(text: string): boolean {
  return QQ_REFERENTIAL_MEDIA_RE.test(text.trim());
}

function detectQqLowPriorityNoiseReason(params: {
  rawBody: string;
  parsed: ParsedQqMessage;
}): string | null {
  const trimmed = params.rawBody.trim();
  if (!trimmed && params.parsed.hasOnlyMediaLike) {
    return "media-only";
  }
  if (params.parsed.hasOnlyMediaLike) {
    return "media-only";
  }
  if (
    /^(?:嗯+|哦+|噢+|啊+|额+|诶+|欸+|好+|好吧|行+|行吧|好的|知道了|收到|草|笑死|绝了|绷不住了|6+|66+|666+|hhh+|hh+|哈+|哈哈+|ok+|OK+|okk+|okkay+|yep+|yes+|no+|？？+|\?\?+|[😂😭🤣😅🥲🥹😍🥰😎👍👌🙏👀❤❤️💀😤😰😓]+)$/u.test(
      trimmed,
    )
  ) {
    return "low-info-ack";
  }
  if (
    trimmed.length <= 8 &&
    !/[?？]/u.test(trimmed) &&
    !looksLikeDirectFollowupCue(trimmed) &&
    !looksLikeQqExplicitInstruction(trimmed)
  ) {
    return "short-low-info";
  }
  return null;
}

function shouldSkipQqOverloadNoise(params: {
  isGroup: boolean;
  busyLevel: QqConversationState["busyLevel"];
  pendingCount: number;
  rawBody: string;
  parsed: ParsedQqMessage;
}): { skip: boolean; reason: string } {
  if (params.parsed.wasMentioned || params.parsed.isReply) {
    return { skip: false, reason: "direct-engagement" };
  }
  const noiseReason = detectQqLowPriorityNoiseReason({
    rawBody: params.rawBody,
    parsed: params.parsed,
  });
  if (!noiseReason) {
    return { skip: false, reason: "not-noise" };
  }
  if (params.isGroup && params.pendingCount >= 2) {
    return { skip: true, reason: `group-overload-${noiseReason}` };
  }
  if (!params.isGroup && params.pendingCount >= 4) {
    return { skip: true, reason: `direct-overload-${noiseReason}` };
  }
  return { skip: false, reason: noiseReason };
}

type QqFairnessClass =
  | "mention"
  | "reply"
  | "direct-chat"
  | "direct-media"
  | "direct-noise"
  | "group-question"
  | "group-media-question"
  | "group-media"
  | "group-media-noise"
  | "group-noise"
  | "group-plain";

type QqSchedulingDecision = {
  skip: boolean;
  mode: "pass" | "overload_gate" | "fairness_gate" | "stale_gate";
  reason: string;
  fairnessClass: QqFairnessClass;
  competingConversationCount: number;
  totalPendingCount: number;
  ageMs: number;
  staleThresholdMs: number | null;
};

type QqDecisionStage = "immediate" | "overload" | "fairness" | "stale" | "mention" | "dispatch";

function classifyQqFairnessClass(params: {
  isGroup: boolean;
  rawBody: string;
  parsed: ParsedQqMessage;
}): QqFairnessClass {
  const trimmed = params.rawBody.trim();
  const noiseReason = detectQqLowPriorityNoiseReason({
    rawBody: params.rawBody,
    parsed: params.parsed,
  });
  const hasMedia = params.parsed.mediaSegments.length > 0;
  const looksQuestionLike =
    /[?？]/u.test(trimmed) ||
    looksLikeQqExplicitInstruction(trimmed) ||
    (!params.isGroup && looksLikeDirectFollowupCue(trimmed));
  if (params.parsed.wasMentioned) {
    return "mention";
  }
  if (params.parsed.isReply) {
    return "reply";
  }
  if (!params.isGroup) {
    if (noiseReason) {
      return "direct-noise";
    }
    if (hasMedia) {
      return "direct-media";
    }
    return "direct-chat";
  }
  if (hasMedia) {
    if (noiseReason) {
      return "group-media-noise";
    }
    if (looksQuestionLike) {
      return "group-media-question";
    }
    return "group-media";
  }
  if (noiseReason) {
    return "group-noise";
  }
  if (looksQuestionLike) {
    return "group-question";
  }
  return "group-plain";
}

function resolveQqStaleThresholdMs(fairnessClass: QqFairnessClass): number | null {
  switch (fairnessClass) {
    case "mention":
    case "reply":
      return null;
    case "direct-chat":
    case "direct-media":
      return 3 * 60 * 1000;
    case "direct-noise":
      return 45 * 1000;
    case "group-question":
    case "group-media-question":
      return 90 * 1000;
    case "group-media":
      return 45 * 1000;
    case "group-media-noise":
    case "group-noise":
      return 20 * 1000;
    case "group-plain":
      return 30 * 1000;
    default:
      return 60 * 1000;
  }
}

function shouldSkipQqStaleMessage(params: {
  fairnessClass: QqFairnessClass;
  messageTimestamp: number;
  nowMs?: number;
}): { skip: boolean; reason: string; ageMs: number; staleThresholdMs: number | null } {
  const nowMs = params.nowMs ?? Date.now();
  const ageMs = Math.max(0, nowMs - params.messageTimestamp);
  const staleThresholdMs = resolveQqStaleThresholdMs(params.fairnessClass);
  if (staleThresholdMs === null) {
    return {
      skip: false,
      reason: "stale-protected",
      ageMs,
      staleThresholdMs,
    };
  }
  if (ageMs > staleThresholdMs) {
    return {
      skip: true,
      reason: `stale-${params.fairnessClass}`,
      ageMs,
      staleThresholdMs,
    };
  }
  return {
    skip: false,
    reason: "fresh-enough",
    ageMs,
    staleThresholdMs,
  };
}

function resolveQqSchedulingDecision(params: {
  conversationKey: string;
  isGroup: boolean;
  rawBody: string;
  parsed: ParsedQqMessage;
  busyLevel: QqConversationState["busyLevel"];
  pendingCount: number;
  messageTimestamp: number;
  disableStaleGate?: boolean;
  nowMs?: number;
  globalLoadOverride?: { totalPendingCount: number; competingConversationCount: number };
}): QqSchedulingDecision {
  const fairnessClass = classifyQqFairnessClass({
    isGroup: params.isGroup,
    rawBody: params.rawBody,
    parsed: params.parsed,
  });
  const overloadDecision = shouldSkipQqOverloadNoise({
    isGroup: params.isGroup,
    busyLevel: params.busyLevel,
    pendingCount: params.pendingCount,
    rawBody: params.rawBody,
    parsed: params.parsed,
  });
  if (overloadDecision.skip) {
    return {
      skip: true,
      mode: "overload_gate",
      reason: overloadDecision.reason,
      fairnessClass,
      competingConversationCount: 0,
      totalPendingCount: 0,
      ageMs: Math.max(0, (params.nowMs ?? Date.now()) - params.messageTimestamp),
      staleThresholdMs: null,
    };
  }
  const fairnessDecision = shouldSkipQqFairnessNoise({
    conversationKey: params.conversationKey,
    isGroup: params.isGroup,
    rawBody: params.rawBody,
    parsed: params.parsed,
    globalLoadOverride: params.globalLoadOverride,
  });
  if (fairnessDecision.skip) {
    return {
      skip: true,
      mode: "fairness_gate",
      reason: fairnessDecision.reason,
      fairnessClass: fairnessDecision.fairnessClass as QqFairnessClass,
      competingConversationCount: fairnessDecision.competingConversationCount,
      totalPendingCount: fairnessDecision.totalPendingCount,
      ageMs: Math.max(0, (params.nowMs ?? Date.now()) - params.messageTimestamp),
      staleThresholdMs: null,
    };
  }
  const staleDecision = params.disableStaleGate
    ? {
        skip: false,
        reason: "stale-gate-disabled",
        ageMs: Math.max(0, (params.nowMs ?? Date.now()) - params.messageTimestamp),
        staleThresholdMs: null,
      }
    : shouldSkipQqStaleMessage({
        fairnessClass,
        messageTimestamp: params.messageTimestamp,
        nowMs: params.nowMs,
      });
  if (staleDecision.skip) {
    return {
      skip: true,
      mode: "stale_gate",
      reason: staleDecision.reason,
      fairnessClass,
      competingConversationCount: fairnessDecision.competingConversationCount,
      totalPendingCount: fairnessDecision.totalPendingCount,
      ageMs: staleDecision.ageMs,
      staleThresholdMs: staleDecision.staleThresholdMs,
    };
  }
  return {
    skip: false,
    mode: "pass",
    reason: "allowed",
    fairnessClass,
    competingConversationCount: fairnessDecision.competingConversationCount,
    totalPendingCount: fairnessDecision.totalPendingCount,
    ageMs: staleDecision.ageMs,
    staleThresholdMs: staleDecision.staleThresholdMs,
  };
}

function shouldSkipQqFairnessNoise(params: {
  conversationKey: string;
  isGroup: boolean;
  rawBody: string;
  parsed: ParsedQqMessage;
  globalLoadOverride?: { totalPendingCount: number; competingConversationCount: number };
}): {
  skip: boolean;
  reason: string;
  fairnessClass: string;
  competingConversationCount: number;
  totalPendingCount: number;
} {
  const fairnessClass = classifyQqFairnessClass({
    isGroup: params.isGroup,
    rawBody: params.rawBody,
    parsed: params.parsed,
  });

  if (params.parsed.wasMentioned || params.parsed.isReply) {
    return {
      skip: false,
      reason: "direct-engagement",
      fairnessClass,
      competingConversationCount: 0,
      totalPendingCount: 0,
    };
  }
  const globalLoad = params.globalLoadOverride ?? getQqGlobalLoad(params.conversationKey);
  const resultBase = {
    fairnessClass,
    ...globalLoad,
  };
  switch (fairnessClass) {
    case "direct-chat":
    case "direct-media":
    case "group-question":
    case "group-media-question":
      return {
        skip: false,
        reason: "priority-protected",
        ...resultBase,
      };
    case "direct-noise":
      return globalLoad.competingConversationCount >= 3 && globalLoad.totalPendingCount >= 5
        ? {
            skip: true,
            reason: "fairness-direct-noise",
            ...resultBase,
          }
        : {
            skip: false,
            reason: "direct-noise",
            ...resultBase,
          };
    case "group-media":
      return globalLoad.competingConversationCount >= 1 && globalLoad.totalPendingCount >= 2
        ? {
            skip: true,
            reason: "fairness-group-media",
            ...resultBase,
          }
        : {
            skip: false,
            reason: "group-media",
            ...resultBase,
          };
    case "group-media-noise":
    case "group-noise":
      return globalLoad.competingConversationCount >= 1 && globalLoad.totalPendingCount >= 2
        ? {
            skip: true,
            reason: `fairness-${fairnessClass}`,
            ...resultBase,
          }
        : {
            skip: false,
            reason: fairnessClass,
            ...resultBase,
          };
    case "group-plain":
      return globalLoad.competingConversationCount >= 2 && globalLoad.totalPendingCount >= 4
        ? {
            skip: true,
            reason: "fairness-group-plain",
            ...resultBase,
          }
        : {
            skip: false,
            reason: "group-plain",
            ...resultBase,
          };
    default:
      return {
        skip: false,
        reason: "not-noise",
        ...resultBase,
      };
  }
}

function normalizeQqMediaQuery(text: string | undefined | null): string {
  return String(text ?? "")
    .replace(
      /(看这个|看这张|这个怎么样|这张怎么样|给这图配一句|给这张图配一句|这个|这张|上一张|上一条图|刚那个|刚刚那个|不是这张|你刚发那个|再来一张|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图|图|图片|表情包|那个|一下|怎么样|怎么回事|配一句|嵌(?:入)?(?:文字|字)|加字|写上|写个字|写一句)/gu,
      " ",
    )
    .replace(/\s+/g, " ")
    .trim();
}

function toSingleLine(value: string | undefined): string {
  return String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();
}

function firstSentence(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return "";
  }
  const match = trimmed.match(/^(.{1,80}?[。！？.!?])/u);
  if (match?.[1]) {
    return match[1].trim();
  }
  return trimmed.slice(0, 80).trim();
}

function extractJsonObject(text: string): Record<string, unknown> | null {
  const cleaned = text
    .trim()
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/i, "");
  const attempts = [cleaned];
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start >= 0 && end > start) {
    attempts.push(cleaned.slice(start, end + 1));
  }
  for (const candidate of attempts) {
    try {
      return JSON.parse(candidate) as Record<string, unknown>;
    } catch {
      // try next variant
    }
  }
  return null;
}

function normalizeQqImageInsight(params: {
  index: number;
  text: string;
  url?: string;
  path?: string;
  mime?: string;
}): QqImageInsight {
  const parsed = extractJsonObject(params.text);
  const visionSummary = toSingleLine(
    typeof parsed?.vision_summary === "string" ? parsed.vision_summary : params.text,
  );
  const alt = toSingleLine(
    typeof parsed?.alt === "string" ? parsed.alt : firstSentence(visionSummary),
  );
  const ocr = toSingleLine(typeof parsed?.ocr === "string" ? parsed.ocr : "");
  return {
    index: params.index,
    ocr,
    alt,
    vision_summary: visionSummary || "图片内容暂未识别清楚",
    url: params.url,
    path: params.path,
    mime: params.mime,
  };
}

function resolveQqConfiguredModelRef(value: unknown): string | undefined {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || undefined;
  }
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const primary = (value as { primary?: unknown }).primary;
  return typeof primary === "string" && primary.trim() ? primary.trim() : undefined;
}

function resolveQqAgentPrimaryModelRef(cfg: OpenClawConfig, agentId: string): string {
  const agents = (
    cfg as {
      agents?: {
        defaults?: {
          model?: unknown;
        };
        list?: Array<{
          id?: unknown;
          model?: unknown;
        }>;
      };
    }
  ).agents;
  const agentEntry = Array.isArray(agents?.list)
    ? agents.list.find((entry) => typeof entry?.id === "string" && entry.id === agentId)
    : undefined;
  return (
    resolveQqConfiguredModelRef(agentEntry?.model) ??
    resolveQqConfiguredModelRef(agents?.defaults?.model) ??
    "openai/gpt-5.4"
  );
}

function parseQqModelRef(modelRef: string): { provider: string; modelId: string } | null {
  const trimmed = modelRef.trim();
  if (!trimmed) {
    return null;
  }
  const slashIndex = trimmed.indexOf("/");
  if (slashIndex <= 0 || slashIndex >= trimmed.length - 1) {
    return null;
  }
  return {
    provider: trimmed.slice(0, slashIndex).trim(),
    modelId: trimmed.slice(slashIndex + 1).trim(),
  };
}

function resolveQqEnvString(value: string | undefined): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const resolved = value.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_match, name: string) => {
    return process.env[name] ?? "";
  });
  const trimmed = resolved.trim();
  return trimmed || undefined;
}

function resolveQqStateDir(): string {
  const explicit = qqStateDirForRecovery?.trim() || process.env.OPENCLAW_STATE_DIR?.trim();
  return explicit || path.join(os.homedir(), ".openclaw");
}

function resolveQqAgentDir(agentId: string): string {
  const normalized = agentId.trim() || "main";
  return path.join(resolveQqStateDir(), "agents", normalized, "agent");
}

function resolveLocalMediaReference(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("file://")) {
    try {
      const filePath = fileURLToPath(trimmed);
      return fs.statSync(filePath).isFile() ? filePath : null;
    } catch {
      return null;
    }
  }
  if (!path.isAbsolute(trimmed)) {
    return null;
  }
  try {
    return fs.statSync(trimmed).isFile() ? trimmed : null;
  } catch {
    return null;
  }
}

function resolvePreferredQqInboundImageRef(
  data: Record<string, string | number | boolean | undefined> | undefined,
): string {
  const fileValue = String(data?.file ?? "").trim();
  const urlValue = String(data?.url ?? "").trim();
  if (fileValue && resolveLocalMediaReference(fileValue)) {
    return fileValue;
  }
  if (urlValue) {
    return urlValue;
  }
  return fileValue;
}

function extractQqUrlHost(value: string | undefined): string {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return "";
  }
  try {
    return new URL(trimmed).hostname;
  } catch {
    return "";
  }
}

function canUseDirectQqMediaFetch(url: string): boolean {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    return QQ_DIRECT_MEDIA_FETCH_HOSTS.has(host) || host.endsWith(".qpic.cn");
  } catch {
    return false;
  }
}

async function fetchQqRemoteMediaWithFallback(params: {
  runtime: ReturnType<typeof getQqRuntime>;
  url: string;
  maxBytes: number;
}): Promise<{
  buffer: Buffer;
  contentType?: string;
  fileName?: string;
  resolution: "runtime-remote" | "qq-direct-fallback";
}> {
  try {
    const fetched = await params.runtime.channel.media.fetchRemoteMedia({
      url: params.url,
      maxBytes: params.maxBytes,
    });
    return {
      ...fetched,
      resolution: "runtime-remote",
    };
  } catch (error) {
    if (!canUseDirectQqMediaFetch(params.url)) {
      throw error;
    }
    let response: Response | null = null;
    let lastError: unknown = error;
    const retries = Math.max(1, QQ_DIRECT_MEDIA_FETCH_RETRIES);
    for (let attempt = 1; attempt <= retries; attempt += 1) {
      try {
        response = await fetch(params.url, {
          headers: {
            "User-Agent":
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            Accept: "image/*,*/*;q=0.8",
          },
          signal: AbortSignal.timeout(QQ_DIRECT_MEDIA_FETCH_TIMEOUT_MS),
        });
        break;
      } catch (fetchError) {
        lastError = fetchError;
        if (attempt < retries) {
          await sleep(500 * attempt);
        }
      }
    }
    if (!response) {
      throw new Error(`QQ media fallback fetch failed after ${retries} attempts: ${String(lastError)}`);
    }
    if (!response.ok) {
      throw new Error(`QQ media fallback fetch failed: ${response.status}`);
    }
    const contentType = response.headers.get("content-type") ?? undefined;
    const contentLength = Number(response.headers.get("content-length") ?? "0");
    if (Number.isFinite(contentLength) && contentLength > params.maxBytes) {
      throw new Error(`QQ media fallback fetch too large: ${contentLength}`);
    }
    const buffer = Buffer.from(await response.arrayBuffer());
    if (buffer.byteLength > params.maxBytes) {
      throw new Error(`QQ media fallback fetch exceeded size limit: ${buffer.byteLength}`);
    }
    const fileName = (() => {
      try {
        const pathname = new URL(params.url).pathname;
        const base = path.basename(pathname);
        return base && base !== "/" ? base : undefined;
      } catch {
        return undefined;
      }
    })();
    return {
      buffer,
      contentType,
      fileName,
      resolution: "qq-direct-fallback",
    };
  }
}

function resolveQqHeaderRecord(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object") {
    return {};
  }
  const record: Record<string, string> = {};
  for (const [key, headerValue] of Object.entries(value as Record<string, unknown>)) {
    if (typeof headerValue !== "string") {
      continue;
    }
    const resolved = resolveQqEnvString(headerValue);
    if (resolved) {
      record[key] = resolved;
    }
  }
  return record;
}

function resolveQqImageMimeType(filePath: string, contentType?: string): string {
  const normalizedContentType = contentType?.split(";")[0]?.trim().toLowerCase();
  if (normalizedContentType?.startsWith("image/")) {
    return normalizedContentType;
  }
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case ".png":
      return "image/png";
    case ".webp":
      return "image/webp";
    case ".gif":
      return "image/gif";
    case ".bmp":
      return "image/bmp";
    case ".heic":
      return "image/heic";
    case ".heif":
      return "image/heif";
    case ".jpg":
    case ".jpeg":
    default:
      return "image/jpeg";
  }
}

function resolveQqResponsesEndpoint(baseUrl: string): string {
  const normalized = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  return new URL("responses", normalized).toString();
}

function extractQqResponsesText(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return "";
  }
  const data = payload as Record<string, unknown>;
  if (typeof data.output_text === "string" && data.output_text.trim()) {
    return data.output_text.trim();
  }
  if (Array.isArray(data.output)) {
    for (const output of data.output) {
      if (!output || typeof output !== "object") {
        continue;
      }
      const outputRecord = output as Record<string, unknown>;
      if (
        outputRecord.type === "output_text" &&
        typeof outputRecord.text === "string" &&
        outputRecord.text.trim()
      ) {
        return outputRecord.text.trim();
      }
      if (!Array.isArray(outputRecord.content)) {
        continue;
      }
      for (const block of outputRecord.content) {
        if (!block || typeof block !== "object") {
          continue;
        }
        const blockRecord = block as Record<string, unknown>;
        if (
          blockRecord.type === "output_text" &&
          typeof blockRecord.text === "string" &&
          blockRecord.text.trim()
        ) {
          return blockRecord.text.trim();
        }
      }
    }
  }
  if (Array.isArray(data.choices)) {
    for (const choice of data.choices) {
      if (!choice || typeof choice !== "object") {
        continue;
      }
      const message = (choice as { message?: unknown }).message;
      if (!message || typeof message !== "object") {
        continue;
      }
      const content = (message as { content?: unknown }).content;
      if (typeof content === "string" && content.trim()) {
        return content.trim();
      }
      if (!Array.isArray(content)) {
        continue;
      }
      for (const block of content) {
        if (!block || typeof block !== "object") {
          continue;
        }
        const blockRecord = block as Record<string, unknown>;
        const textValue =
          typeof blockRecord.text === "string"
            ? blockRecord.text
            : typeof blockRecord.content === "string"
              ? blockRecord.content
              : "";
        if (textValue.trim()) {
          return textValue.trim();
        }
      }
    }
  }
  return "";
}

function extractQqProviderError(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }
  const data = payload as Record<string, unknown>;
  if (typeof data.message === "string" && data.message.trim()) {
    return data.message.trim();
  }
  const error = data.error;
  if (typeof error === "string" && error.trim()) {
    return error.trim();
  }
  if (error && typeof error === "object") {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message.trim();
    }
  }
  return undefined;
}

function resolveQqResponsesModelConfig(params: { cfg: OpenClawConfig; agentId: string }): {
  provider: string;
  modelId: string;
  api: string;
  baseUrl: string;
  apiKey?: string;
  auth?: string;
  authHeader: boolean;
  headers: Record<string, string>;
} | null {
  const modelRef = resolveQqAgentPrimaryModelRef(params.cfg, params.agentId);
  const parsed = parseQqModelRef(modelRef);
  if (!parsed) {
    return null;
  }
  const providers = (
    params.cfg as {
      models?: {
        providers?: Record<string, unknown>;
      };
    }
  ).models?.providers;
  const providerConfig = (providers?.[parsed.provider] ?? null) as Record<string, unknown> | null;
  const modelConfig = Array.isArray(providerConfig?.models)
    ? ((providerConfig?.models as unknown[]).find((entry) => {
        return (
          Boolean(entry) &&
          typeof entry === "object" &&
          typeof (entry as { id?: unknown }).id === "string" &&
          (entry as { id: string }).id === parsed.modelId
        );
      }) as Record<string, unknown> | undefined)
    : undefined;
  const baseUrl =
    (typeof modelConfig?.baseUrl === "string" && modelConfig.baseUrl.trim()) ||
    (typeof providerConfig?.baseUrl === "string" && providerConfig.baseUrl.trim()) ||
    (parsed.provider === "openai" ? "https://api.openai.com/v1" : "");
  if (!baseUrl) {
    return null;
  }
  const api =
    (typeof modelConfig?.api === "string" && modelConfig.api.trim()) ||
    (typeof providerConfig?.api === "string" && providerConfig.api.trim()) ||
    "openai-responses";
  const apiKey =
    resolveQqEnvString(
      typeof modelConfig?.apiKey === "string"
        ? modelConfig.apiKey
        : typeof providerConfig?.apiKey === "string"
          ? providerConfig.apiKey
          : undefined,
    ) ??
    (parsed.provider === "openai" ? process.env.OPENAI_API_KEY?.trim() || undefined : undefined);
  return {
    provider: parsed.provider,
    modelId: parsed.modelId,
    api,
    baseUrl,
    apiKey,
    auth: typeof providerConfig?.auth === "string" ? providerConfig.auth : undefined,
    authHeader: providerConfig?.authHeader !== false,
    headers: {
      ...resolveQqHeaderRecord(providerConfig?.headers),
      ...resolveQqHeaderRecord(modelConfig?.headers),
    },
  };
}

export async function describeQqImageWithModel(params: {
  cfg: OpenClawConfig;
  agentId: string;
  filePath: string;
  sourceUrl?: string;
  contentType?: string;
  index: number;
  logger?: Pick<OpenClawPluginApi["logger"], "warn">;
}): Promise<QqImageInsight> {
  const cacheKey = `${params.filePath}::${params.sourceUrl ?? ""}`;
  const cached = qqImageInsightCache.get(cacheKey);
  if (cached) {
    qqImageInsightCache.delete(cacheKey);
    qqImageInsightCache.set(cacheKey, cached);
    return await cached;
  }
  const task = (async () => {
    const mimeType = resolveQqImageMimeType(params.filePath, params.contentType);
    try {
      const modelRef = resolveQqAgentPrimaryModelRef(params.cfg, params.agentId);
      const parsedModel = parseQqModelRef(modelRef);
      if (!parsedModel) {
        throw new Error("qq image summary model is not configured");
      }
      const describeImageWithModel = await loadDescribeImageWithModel();
      const fileBuffer = fs.readFileSync(params.filePath);
      const described = await describeImageWithModel({
        buffer: fileBuffer,
        fileName: path.basename(params.filePath),
        mime: mimeType,
        provider: parsedModel.provider,
        model: parsedModel.modelId,
        prompt: QQ_IMAGE_SUMMARY_PROMPT,
        maxTokens: 220,
        timeoutMs: QQ_IMAGE_SUMMARY_TIMEOUT_MS,
        agentDir: resolveQqAgentDir(params.agentId),
        cfg: params.cfg,
      });
      if (!described.text.trim()) {
        throw new Error("empty image summary response");
      }
      return normalizeQqImageInsight({
        index: params.index,
        text: described.text,
        url: params.sourceUrl,
        path: params.filePath,
        mime: mimeType,
      });
    } catch (error) {
      params.logger?.warn(`[qq] image summary failed for ${params.filePath}: ${String(error)}`);
      return {
        index: params.index,
        ocr: "",
        alt: "图片",
        vision_summary: "这是一张图片，具体内容暂时没拿稳。",
        url: params.sourceUrl,
        path: params.filePath,
        mime: mimeType,
      };
    }
  })();
  qqImageInsightCache.set(cacheKey, task);
  while (qqImageInsightCache.size > QQ_IMAGE_INSIGHT_CACHE_LIMIT) {
    const oldestKey = qqImageInsightCache.keys().next().value;
    if (!oldestKey) {
      break;
    }
    qqImageInsightCache.delete(oldestKey);
  }
  return await task;
}

function rememberQqMediaRecords(conversationKey: string, records: QqMediaRecord[]) {
  if (!conversationKey || records.length === 0) {
    return;
  }
  const state = getQqConversationState(conversationKey);
  const next = state.recentMediaBuffer.filter(
    (existing) => !records.some((record) => record.id === existing.id),
  );
  state.recentMediaBuffer = [...next, ...records].slice(-QQ_RECENT_MEDIA_BUFFER_LIMIT);
}

function rememberQqMessageRecord(conversationKey: string, record: QqMessageRecord) {
  const state = getQqConversationState(conversationKey);
  state.recentMessages = pushQqLimited(state.recentMessages, record, QQ_RECENT_MESSAGE_LIMIT);
}

function getQqMediaByMessageId(conversationKey: string, messageId?: string): QqMediaRecord[] {
  if (!messageId) {
    return [];
  }
  return getQqConversationState(conversationKey).recentMediaBuffer.filter(
    (entry) => entry.message_id === messageId,
  );
}

type QqReplayMediaTypeFilter = "any" | "image" | "emoji";

function parseQqChineseNumberToken(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^\d+$/u.test(trimmed)) {
    const parsed = Number.parseInt(trimmed, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }
  const digits: Record<string, number> = {
    一: 1,
    二: 2,
    两: 2,
    三: 3,
    四: 4,
    五: 5,
    六: 6,
    七: 7,
    八: 8,
    九: 9,
  };
  if (trimmed === "十") {
    return 10;
  }
  const tenIndex = trimmed.indexOf("十");
  if (tenIndex >= 0) {
    const left = trimmed.slice(0, tenIndex);
    const right = trimmed.slice(tenIndex + 1);
    const tens = left ? digits[left] : 1;
    const ones = right ? digits[right] : 0;
    if (!Number.isFinite(tens) || !Number.isFinite(ones)) {
      return null;
    }
    return tens * 10 + ones;
  }
  return digits[trimmed] ?? null;
}

function filterQqMediaRecordsByType(
  records: QqMediaRecord[],
  typeFilter: QqReplayMediaTypeFilter,
): QqMediaRecord[] {
  if (typeFilter === "any") {
    return records;
  }
  if (typeFilter === "image") {
    return records.filter((record) => record.type === "image");
  }
  return records.filter((record) => record.type === "emoji" || record.type === "animated_emoji");
}

function hasUsableQqMediaRecord(record: QqMediaRecord) {
  const images = Array.isArray(record.images) ? record.images : [];
  const hasImageRef = images.some((image) => Boolean(image?.path?.trim() || image?.url?.trim()));
  const hasReplaySegments =
    Array.isArray(record.replay_segments) && record.replay_segments.length > 0;
  return Boolean(
    record.type || record.summary || record.caption || hasImageRef || hasReplaySegments,
  );
}

function orderQqReplayMediaRecords(
  records: QqMediaRecord[],
  preferOutbound?: boolean,
): QqMediaRecord[] {
  return [...records].sort((left, right) => {
    const leftWeight = preferOutbound && left.source === "outbound" ? 1 : 0;
    const rightWeight = preferOutbound && right.source === "outbound" ? 1 : 0;
    const leftCreatedAt =
      typeof left.created_at === "number" && Number.isFinite(left.created_at) ? left.created_at : 0;
    const rightCreatedAt =
      typeof right.created_at === "number" && Number.isFinite(right.created_at)
        ? right.created_at
        : 0;
    return rightWeight - leftWeight || rightCreatedAt - leftCreatedAt;
  });
}

function orderQqMemeBaseCandidates(records: QqMediaRecord[]) {
  return [...records].sort((left, right) => {
    const score = (record: QqMediaRecord) => {
      switch (record.source) {
        case "inbound":
          return 3;
        case "reply_target":
          return 2;
        case "recent_media_buffer":
          return 1;
        case "outbound":
          return 0;
        default:
          return 0;
      }
    };
    const leftCreatedAt =
      typeof left.created_at === "number" && Number.isFinite(left.created_at) ? left.created_at : 0;
    const rightCreatedAt =
      typeof right.created_at === "number" && Number.isFinite(right.created_at)
        ? right.created_at
        : 0;
    return score(right) - score(left) || rightCreatedAt - leftCreatedAt;
  });
}

export function resolveQqConversationMemeBaseImage(params: {
  conversationKey: string;
  preferInbound?: boolean;
}): {
  imagePath?: string;
  imageUrl?: string;
  source: QqMediaRecord["source"];
  mediaId: string;
  summary: string;
} | null {
  const records = getQqConversationState(params.conversationKey).recentMediaBuffer.filter(
    (record) =>
      record.type === "image" &&
      record.images.some((image) => Boolean(image.path?.trim() || image.url?.trim())),
  );
  const ordered = orderQqMemeBaseCandidates(records);
  const filtered = params.preferInbound
    ? ordered.filter((record) => record.source !== "outbound")
    : ordered;
  const chosen = filtered[0] ?? ordered[0] ?? null;
  if (!chosen) {
    return null;
  }
  const image = chosen.images.find((item) => item.path?.trim() || item.url?.trim());
  if (!image) {
    return null;
  }
  return {
    imagePath: image.path?.trim() || undefined,
    imageUrl: image.url?.trim() || undefined,
    source: chosen.source,
    mediaId: chosen.id,
    summary: chosen.summary,
  };
}

function selectQqRecentMediaRecord(params: {
  conversationKey: string;
  index: number;
  typeFilter: QqReplayMediaTypeFilter;
  preferOutbound?: boolean;
}): QqMediaRecord | null {
  const buffer = getQqConversationState(params.conversationKey).recentMediaBuffer;
  if (buffer.length === 0) {
    return null;
  }
  const filtered = filterQqMediaRecordsByType(
    orderQqReplayMediaRecords(buffer, params.preferOutbound),
    params.typeFilter,
  );
  if (filtered.length === 0) {
    return null;
  }
  return filtered[Math.max(0, params.index)] ?? filtered[0] ?? null;
}

function matchRecentQqMedia(params: {
  conversationKey: string;
  text: string;
  preferOutbound?: boolean;
}): QqMediaRecord | null {
  const query = normalizeQqMediaQuery(params.text);
  const ordered = orderQqReplayMediaRecords(
    getQqConversationState(params.conversationKey).recentMediaBuffer,
    params.preferOutbound,
  ).filter(hasUsableQqMediaRecord);
  if (ordered.length === 0) {
    return null;
  }
  if (!query) {
    if (/上一张/u.test(params.text) && ordered.length > 1) {
      return ordered[1] ?? ordered[0] ?? null;
    }
    return ordered[0] ?? null;
  }
  const matched = ordered.find((entry) =>
    [
      entry.summary,
      entry.caption,
      entry.quoted_text,
      ...(entry.images ?? []).map((image) => image.alt),
    ]
      .filter(Boolean)
      .some((value) => String(value).includes(query)),
  );
  return matched ?? ordered[0] ?? null;
}

async function getQqMessageById(params: {
  cfg: CoreConfig;
  accountId?: string;
  messageId: string;
}): Promise<{
  messageId?: string;
  senderId?: string;
  senderName?: string;
  text: string;
  parsed: ParsedQqMessage;
  timestamp?: number;
} | null> {
  const numericId = Number(params.messageId);
  if (!Number.isFinite(numericId) || numericId <= 0) {
    return null;
  }
  const result = await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_msg",
    params: { message_id: numericId },
  }).catch(() => null);
  const data = result?.data as Record<string, unknown> | undefined;
  if (!data) {
    return null;
  }
  const sender = (data.sender ?? {}) as Record<string, unknown>;
  const senderId =
    typeof sender.user_id === "number" || typeof sender.user_id === "string"
      ? String(sender.user_id)
      : undefined;
  const senderName =
    typeof sender.card === "string" && sender.card.trim()
      ? sender.card.trim()
      : typeof sender.nickname === "string" && sender.nickname.trim()
        ? sender.nickname.trim()
        : undefined;
  const parsed = parseMessageSegments(
    data.message as string | OneBotMessageSegment[] | undefined,
    undefined,
  );
  return {
    messageId:
      typeof data.message_id === "number" || typeof data.message_id === "string"
        ? String(data.message_id)
        : params.messageId,
    senderId,
    senderName,
    text: parsed.text || summarizeQqMediaPlaceholder(parsed),
    parsed,
    timestamp:
      typeof data.time === "number" && Number.isFinite(data.time) ? data.time * 1000 : undefined,
  };
}

async function getQqRecentContacts(params: {
  cfg: CoreConfig;
  accountId?: string;
  count?: number;
}): Promise<QqRecentContactEntry[]> {
  const result = await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_recent_contact",
    params: {
      count: Math.max(
        1,
        Math.min(
          QQ_INBOUND_RECOVERY_CONTACT_LIMIT,
          Number(params.count ?? QQ_INBOUND_RECOVERY_CONTACT_LIMIT),
        ),
      ),
    },
  }).catch(() => null);
  return Array.isArray(result?.data) ? (result.data as QqRecentContactEntry[]) : [];
}

async function getQqConversationHistory(params: {
  cfg: CoreConfig;
  accountId?: string;
  selfId?: string;
  targetKind: "user" | "group";
  targetId: string;
  count?: number;
}): Promise<OneBotMessageEvent[]> {
  const action = params.targetKind === "group" ? "get_group_msg_history" : "get_friend_msg_history";
  const actionParams =
    params.targetKind === "group"
      ? { group_id: params.targetId, count: params.count ?? QQ_INBOUND_RECOVERY_HISTORY_LIMIT }
      : { user_id: params.targetId, count: params.count ?? QQ_INBOUND_RECOVERY_HISTORY_LIMIT };
  const result = await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action,
    params: actionParams,
  }).catch(() => null);
  const messages = Array.isArray((result?.data as { messages?: unknown } | undefined)?.messages)
    ? (((result?.data as { messages?: unknown }).messages as unknown[]) ?? [])
    : [];
  return messages
    .map((entry) =>
      normalizeQqRecoveredMessageEvent({
        raw: entry,
        selfId: params.selfId,
      }),
    )
    .filter((entry): entry is OneBotMessageEvent => Boolean(entry));
}

function selectRecoverableQqHistoryEvents(params: {
  events: OneBotMessageEvent[];
  account: ResolvedQqAccount;
  sinceMs: number;
  cursor?: QqInboundRecoveryCursor | null;
}): OneBotMessageEvent[] {
  const selfId = params.account.selfId?.trim();
  const threshold = Math.max(0, params.sinceMs - QQ_INBOUND_RECOVERY_WINDOW_PADDING_MS);
  return [...params.events]
    .filter((event) => {
      if (selfId && String(event.user_id) === selfId) {
        return false;
      }
      const eventMessageId = normalizeQqMessageId(event.message_id);
      if (
        params.cursor?.lastHandledMessageId &&
        eventMessageId === params.cursor.lastHandledMessageId
      ) {
        return false;
      }
      const eventTimestamp = normalizeQqTimestampMs(event.time);
      if (eventTimestamp && eventTimestamp < threshold) {
        return false;
      }
      if (
        params.cursor?.lastHandledAt &&
        eventTimestamp &&
        eventTimestamp < params.cursor.lastHandledAt - QQ_INBOUND_RECOVERY_WINDOW_PADDING_MS
      ) {
        return false;
      }
      const parsed = parseMessageSegments(event.message, selfId ?? String(event.self_id));
      if (event.message_type === "group") {
        const directEngagement =
          parsed.wasMentioned || parsed.isReply || shouldTreatQqMessageAsDirectEngagement(event);
        if (!directEngagement) {
          return false;
        }
      }
      return true;
    })
    .sort((left, right) => {
      const leftTimestamp = normalizeQqTimestampMs(left.time) ?? 0;
      const rightTimestamp = normalizeQqTimestampMs(right.time) ?? 0;
      if (leftTimestamp !== rightTimestamp) {
        return leftTimestamp - rightTimestamp;
      }
      const leftMessageId = Number(normalizeQqMessageId(left.message_id) ?? 0);
      const rightMessageId = Number(normalizeQqMessageId(right.message_id) ?? 0);
      return leftMessageId - rightMessageId;
    });
}

function resolveGroupConfig(account: ResolvedQqAccount, groupId?: string) {
  if (!groupId) {
    return account.config.groups?.["*"];
  }
  return account.config.groups?.[groupId] ?? account.config.groups?.["*"];
}

function resolveWorkspaceDir(cfg: OpenClawConfig): string | null {
  const workspace = (cfg as { agents?: { defaults?: { workspace?: string } } }).agents?.defaults
    ?.workspace;
  return typeof workspace === "string" && workspace.trim() ? workspace.trim() : null;
}

function readJsonFile<T>(filePath: string, fallback: T): T {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
  } catch {
    return fallback;
  }
}

type GroupSocialNorms = {
  groupName?: string;
  tone?: string;
  humorStyle?: string[];
  allowedBoldness?: number;
};

type GroupSocialSelfPosition = {
  currentRole?: string;
  allowedPresence?: string;
  attentionBudget?: number;
  playfulnessLevel?: number;
  protectivenessLevel?: number;
};

type GroupSocialAppraisal = {
  socialSafety?: number;
  dramaRisk?: number;
  groupNoise?: number;
  recentAcceptance?: number;
  recentRejection?: number;
  novelty?: number;
};

type GroupSocialReplyStyle = {
  groupName?: string;
  targetStyle?: {
    length?: string;
    sentenceCount?: string;
    cadence?: string;
    explanationMode?: string;
    punctuation?: string;
    laughterForms?: string[];
    sentenceFinalParticles?: string[];
  };
  observedSignals?: {
    avgMessageLength?: number;
    shortMessageRate?: number;
    noPunctuationRate?: number;
    repeatedCharRate?: number;
    emojiLikeRate?: number;
    laughterForms?: string[];
    sentenceFinalParticles?: string[];
  };
  do?: string[];
  dont?: string[];
  antiPatterns?: string[];
  hardBannedSymbols?: string[];
};

type GroupSocialState = {
  dirPath: string;
  groupName?: string;
  norms: GroupSocialNorms;
  selfPosition: GroupSocialSelfPosition;
  appraisal: GroupSocialAppraisal;
  replyStyle: GroupSocialReplyStyle;
};

type QqPersonaProfile = {
  id: string;
  label: string;
  aliases: string[];
  promptLines: string[];
};

type ResolvedQqNaturalChatConfig = {
  enabled: boolean;
  applyToGroups: boolean;
  applyToDirect: boolean;
  splitMessages: boolean;
  removeDecorativeEmoji: boolean;
  hardBannedSymbols: string[];
  defaultPersona: string;
  allowPersonaSwitch: boolean;
};

type ResolvedQqStudyModeConfig = {
  enabled: boolean;
  directOnly: boolean;
  autoSolveLikelyProblemImages: boolean;
  alwaysRenderHtml: boolean;
  answerStyle: string;
  skills: string[];
  systemPrompt?: string;
};

function readStringList(value: unknown, limit = 6): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return [...new Set(value.map((entry) => String(entry ?? "").trim()).filter(Boolean))].slice(
    0,
    limit,
  );
}

function formatPercent(value: unknown): string | null {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  return `${Math.round(numeric * 100)}%`;
}

function mergeSystemPrompts(...prompts: Array<string | undefined>): string | undefined {
  const parts = prompts.map((prompt) => prompt?.trim()).filter(Boolean);
  return parts.length > 0 ? parts.join("\n\n") : undefined;
}

function previewText(text: string | undefined | null, limit = 120): string {
  return String(text ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

async function loadRunEmbeddedPiAgent(): Promise<RunEmbeddedPiAgentFn> {
  if (!runEmbeddedPiAgentLoader) {
    runEmbeddedPiAgentLoader = (async () => {
      const mod = (await import("../../../dist/extensionAPI.js")) as {
        runEmbeddedPiAgent?: unknown;
      };
      const fn = mod.runEmbeddedPiAgent;
      if (typeof fn !== "function") {
        throw new Error("Internal error: runEmbeddedPiAgent not available");
      }
      return fn as RunEmbeddedPiAgentFn;
    })();
  }
  return await runEmbeddedPiAgentLoader;
}

async function loadDescribeImageWithModel(): Promise<DescribeImageWithModelFn> {
  if (!describeImageWithModelLoader) {
    describeImageWithModelLoader = (async () => {
      const pluginSdkDir = fileURLToPath(new URL("../../../dist/plugin-sdk/", import.meta.url));
      const runtimeEntry = fs
        .readdirSync(pluginSdkDir)
        .find((entry) => /^image-runtime-.*\.js$/u.test(entry));
      if (!runtimeEntry) {
        throw new Error("Internal error: image runtime not available");
      }
      const runtimeUrl = new URL(`../../../dist/plugin-sdk/${runtimeEntry}`, import.meta.url);
      const mod = (await import(runtimeUrl.href)) as {
        describeImageWithModel?: unknown;
      };
      const fn = mod.describeImageWithModel;
      if (typeof fn !== "function") {
        throw new Error("Internal error: describeImageWithModel not available");
      }
      return fn as DescribeImageWithModelFn;
    })();
  }
  return await describeImageWithModelLoader;
}

function collectEmbeddedText(
  payloads: Array<{ text?: string; isError?: boolean }> | undefined,
): string {
  return (payloads ?? [])
    .filter((payload) => !payload.isError && typeof payload.text === "string")
    .map((payload) => payload.text ?? "")
    .join("\n")
    .trim();
}

function stripCodeFences(text: string): string {
  const trimmed = text.trim();
  const match = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  return match?.[1]?.trim() ?? trimmed;
}

function resolveDefaultAgentProviderModel(cfg: OpenClawConfig) {
  const defaultsModel = cfg.agents?.defaults?.model;
  const primary =
    typeof defaultsModel === "string"
      ? defaultsModel.trim()
      : typeof defaultsModel === "object" && defaultsModel && "primary" in defaultsModel
        ? String((defaultsModel as { primary?: string }).primary ?? "").trim()
        : "";
  if (!primary.includes("/")) {
    return { provider: undefined, model: undefined };
  }
  const [provider, ...rest] = primary.split("/");
  return {
    provider: provider.trim() || undefined,
    model: rest.join("/").trim() || undefined,
  };
}

function uniqueNonEmptyStrings(values: unknown[]): string[] {
  return [...new Set(values.map((value) => String(value ?? "").trim()).filter(Boolean))];
}

function resolveQqNaturalChatConfig(params: {
  account: ResolvedQqAccount;
  groupId?: string;
  chatType: "group" | "direct";
}): ResolvedQqNaturalChatConfig {
  const base = (params.account.config.naturalChat ?? {}) as QqNaturalChatConfig;
  const groupOverride =
    params.chatType === "group"
      ? ((resolveGroupConfig(params.account, params.groupId)?.naturalChat ??
          {}) as QqNaturalChatConfig)
      : {};
  const merged = {
    ...base,
    ...groupOverride,
  };

  return {
    enabled: merged.enabled === true,
    applyToGroups: merged.applyToGroups !== false,
    applyToDirect: merged.applyToDirect !== false,
    splitMessages: merged.splitMessages !== false,
    removeDecorativeEmoji: merged.removeDecorativeEmoji !== false,
    hardBannedSymbols: uniqueNonEmptyStrings([
      "☕",
      ...(Array.isArray(base.hardBannedSymbols) ? base.hardBannedSymbols : []),
      ...(Array.isArray(groupOverride.hardBannedSymbols) ? groupOverride.hardBannedSymbols : []),
    ]),
    defaultPersona:
      String(groupOverride.defaultPersona ?? base.defaultPersona ?? "chino")
        .trim()
        .toLowerCase() || "chino",
    allowPersonaSwitch: merged.allowPersonaSwitch !== false,
  };
}

function resolveQqStudyModeConfig(account: ResolvedQqAccount): ResolvedQqStudyModeConfig {
  const raw = (account.config.studyMode ?? {}) as QqStudyModeConfig;
  const configuredSkills = uniqueNonEmptyStrings(
    Array.isArray(raw.skills) ? raw.skills : [],
  );

  return {
    enabled: raw.enabled === true,
    directOnly: raw.directOnly !== false,
    autoSolveLikelyProblemImages: raw.autoSolveLikelyProblemImages !== false,
    alwaysRenderHtml: raw.alwaysRenderHtml !== false,
    answerStyle: String(raw.answerStyle ?? "").trim() || "exam",
    skills:
      configuredSkills.length > 0 ? configuredSkills : [...DEFAULT_QQ_STUDY_MODE_SKILLS],
    systemPrompt: String(raw.systemPrompt ?? "").trim() || undefined,
  };
}

function buildQqStudyModeSystemPrompt(params: {
  account: ResolvedQqAccount;
  chatType: "group" | "direct";
  hasImage: boolean;
}) {
  const studyMode = resolveQqStudyModeConfig(params.account);
  if (!studyMode.enabled || params.chatType !== "direct") {
    return undefined;
  }
  const styleLabel = studyMode.answerStyle === "exam" ? "exam-ready" : studyMode.answerStyle;
  const lines = [
    "QQ study mode is active for this direct conversation.",
    "This mode is optimized for solving homework, worksheet, and exam-style questions in private chat.",
    studyMode.directOnly
      ? "Group messages are intentionally suppressed while study mode is active, so focus entirely on direct-message problem solving."
      : null,
    params.hasImage && studyMode.autoSolveLikelyProblemImages
      ? "This turn includes question-like image material. Inspect it first and start solving immediately if it plausibly contains a problem statement."
      : null,
    params.hasImage && studyMode.autoSolveLikelyProblemImages
      ? "Only ask for a clearer resend when the image is genuinely unreadable, cropped, or missing decisive parts of the question."
      : null,
    "If the attached image is clearly not a question, reply normally instead of forcing a problem-solving workflow.",
    "When multiple screenshots are present, treat them as one question packet first, not as unrelated independent images.",
    "Reconstruct the most likely page and question order using page numbers, question numbering, continuation phrases, overlapping text, and user hints.",
    `Default answer style: ${styleLabel}. Keep the tone concise, structured, and directly usable in an exam or homework submission.`,
    "Do not add chatty filler, roleplay banter, or assistant-style preambles before the solution.",
    studyMode.alwaysRenderHtml
      ? "Regardless of whether a figure is required, the final deliverable must be rendered with chinobot_render_html and sent back as the answer artifact."
      : null,
    studyMode.alwaysRenderHtml
      ? "If one screenshot contains multiple questions or too much content for one readable answer sheet, split the final delivery into multiple HTML-rendered cards/pages instead of cramming everything into one image."
      : null,
    studyMode.alwaysRenderHtml
      ? "Use a restrained exam-paper layout: light background, dark readable text, clear section hierarchy, and no poster-like or meme-like styling."
      : null,
    studyMode.systemPrompt,
  ];
  return lines.filter((line): line is string => Boolean(line)).join("\n");
}

function isQqNaturalChatEnabled(params: {
  account: ResolvedQqAccount;
  groupId?: string;
  chatType: "group" | "direct";
}) {
  const settings = resolveQqNaturalChatConfig(params);
  if (!settings.enabled) {
    return false;
  }
  return params.chatType === "group" ? settings.applyToGroups : settings.applyToDirect;
}

function resolveQqReplySkillFilter(params: {
  account: ResolvedQqAccount;
  groupId?: string;
  chatType: "group" | "direct";
}): string[] | undefined {
  if (params.chatType === "group") {
    return (
      params.account.config.groups?.[params.groupId ?? ""]?.skills ??
      params.account.config.groups?.["*"]?.skills
    );
  }
  const studyMode = resolveQqStudyModeConfig(params.account);
  return studyMode.enabled ? studyMode.skills : undefined;
}

function resolveDirectStudyBurstDelays(params: {
  account: ResolvedQqAccount;
  event: OneBotMessageEvent;
  parsed: ParsedQqMessage;
  conversationKey: string;
}): { burstIdleMs?: number; burstWindowMs?: number } {
  const studyMode = resolveQqStudyModeConfig(params.account);
  if (!studyMode.enabled || params.event.message_type !== "private") {
    return {};
  }
  const hasImageMedia = params.parsed.mediaSegments.some((segment) => segment.type === "image");
  const hasText = params.parsed.text.trim().length > 0;
  const hasPendingBurst = qqPendingBursts.has(params.conversationKey);
  if (hasImageMedia && !hasText) {
    return {
      burstIdleMs: QQ_DIRECT_STUDY_IMAGE_HOLD_MS,
      burstWindowMs: QQ_DIRECT_STUDY_IMAGE_HOLD_MS,
    };
  }
  if (hasPendingBurst) {
    return {
      burstIdleMs: QQ_DIRECT_STUDY_FOLLOWUP_FLUSH_MS,
    };
  }
  return {};
}

function buildQqStudyProgressText(
  kind:
    | "image_received"
    | "followup_received"
    | "solving"
    | "solving_delayed"
    | "rendering_delayed",
) {
  switch (kind) {
    case "image_received":
      return "收到图片了，我先识别题目。你要是还有补充说明，可以继续发。";
    case "followup_received":
      return "收到补充说明了，我正在合并题面。";
    case "solving":
      return "题目已经识别到，我现在开始整理答案并出图。";
    case "solving_delayed":
      return "我还在整理答案，这一步复杂时会多花一点时间，先别急，我会继续往下做。";
    case "rendering_delayed":
      return "还在出图，复杂题这一步可能要 1 分钟左右；出好后会直接发回聊天。";
  }
}

function resolveQqStudyProgressFollowups(params: {
  account: ResolvedQqAccount;
  event: OneBotMessageEvent;
  hasImage: boolean;
}) {
  const studyMode = resolveQqStudyModeConfig(params.account);
  if (!studyMode.enabled || params.event.message_type !== "private" || !params.hasImage) {
    return [] as Array<(typeof QQ_STUDY_PROGRESS_FOLLOWUPS)[number]>;
  }
  return QQ_STUDY_PROGRESS_FOLLOWUPS.map((entry) => ({ ...entry }));
}

function resolveQqQueueDir(stateDir: string) {
  return path.join(stateDir, "delivery-queue");
}

function resolveRecentQqDeliveryFile(stateDir: string) {
  return path.join(stateDir, "qq", "recent-deliveries.json");
}

function resolveQqInboundRecoveryStateFile(stateDir: string) {
  return path.join(stateDir, "qq", "inbound-recovery.json");
}

function resolveQqPersonaStateFile(stateDir: string) {
  return path.join(stateDir, "qq", "persona-state.json");
}

function loadQqInboundRecoveryState(stateDir: string) {
  const filePath = resolveQqInboundRecoveryStateFile(stateDir);
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = JSON.parse(raw) as Partial<QqInboundRecoveryState> | null;
    qqInboundRecoveryStateCache = {
      lastConnectedAt:
        typeof parsed?.lastConnectedAt === "number" && Number.isFinite(parsed.lastConnectedAt)
          ? parsed.lastConnectedAt
          : undefined,
      lastDisconnectedAt:
        typeof parsed?.lastDisconnectedAt === "number" && Number.isFinite(parsed.lastDisconnectedAt)
          ? parsed.lastDisconnectedAt
          : undefined,
      conversations:
        parsed?.conversations && typeof parsed.conversations === "object"
          ? Object.fromEntries(
              Object.entries(parsed.conversations).map(([conversationKey, cursor]) => {
                const record = cursor && typeof cursor === "object" ? cursor : {};
                const normalizedCursor = record as Record<string, unknown>;
                return [
                  conversationKey,
                  {
                    lastHandledAt:
                      typeof normalizedCursor.lastHandledAt === "number" &&
                      Number.isFinite(normalizedCursor.lastHandledAt)
                        ? normalizedCursor.lastHandledAt
                        : undefined,
                    lastHandledMessageId:
                      typeof normalizedCursor.lastHandledMessageId === "string" &&
                      normalizedCursor.lastHandledMessageId.trim()
                        ? normalizedCursor.lastHandledMessageId.trim()
                        : undefined,
                  } satisfies QqInboundRecoveryCursor,
                ];
              }),
            )
          : {},
    };
  } catch {
    qqInboundRecoveryStateCache = {
      conversations: {},
    };
  }
}

function saveQqInboundRecoveryState(stateDir: string) {
  const filePath = resolveQqInboundRecoveryStateFile(stateDir);
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(
      filePath,
      `${JSON.stringify(qqInboundRecoveryStateCache ?? { conversations: {} }, null, 2)}\n`,
      "utf8",
    );
  } catch {
    // ignore
  }
}

function ensureQqInboundRecoveryState(stateDir: string): QqInboundRecoveryState {
  if (!qqInboundRecoveryStateCache) {
    loadQqInboundRecoveryState(stateDir);
  }
  if (!qqInboundRecoveryStateCache) {
    qqInboundRecoveryStateCache = {
      conversations: {},
    };
  }
  return qqInboundRecoveryStateCache;
}

function noteQqConnectionOpened(stateDir: string, now = Date.now()) {
  const state = ensureQqInboundRecoveryState(stateDir);
  state.lastConnectedAt = now;
  saveQqInboundRecoveryState(stateDir);
}

function noteQqConnectionClosed(stateDir: string, now = Date.now()) {
  const state = ensureQqInboundRecoveryState(stateDir);
  state.lastDisconnectedAt = now;
  saveQqInboundRecoveryState(stateDir);
}

function getQqInboundRecoveryCursor(
  stateDir: string,
  conversationKey: string,
): QqInboundRecoveryCursor | null {
  const state = ensureQqInboundRecoveryState(stateDir);
  return state.conversations[conversationKey] ?? null;
}

function rememberQqInboundConversationProgress(params: {
  stateDir: string;
  conversationKey: string;
  messageId?: string;
  timestamp: number;
}) {
  const state = ensureQqInboundRecoveryState(params.stateDir);
  const existing = state.conversations[params.conversationKey] ?? {};
  state.conversations[params.conversationKey] = {
    lastHandledAt:
      typeof existing.lastHandledAt === "number" && Number.isFinite(existing.lastHandledAt)
        ? Math.max(existing.lastHandledAt, params.timestamp)
        : params.timestamp,
    lastHandledMessageId: params.messageId?.trim() || existing.lastHandledMessageId,
  };
  saveQqInboundRecoveryState(params.stateDir);
}

function loadQqPersonaState(stateDir: string) {
  const filePath = resolveQqPersonaStateFile(stateDir);
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = JSON.parse(raw);
    qqPersonaStateCache =
      parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : {};
  } catch {
    qqPersonaStateCache = {};
  }
}

function saveQqPersonaState(stateDir: string) {
  const filePath = resolveQqPersonaStateFile(stateDir);
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, `${JSON.stringify(qqPersonaStateCache ?? {}, null, 2)}\n`, "utf8");
  } catch {
    // ignore
  }
}

function normalizeQqPersonaId(rawValue: string | undefined | null) {
  const normalized = String(rawValue ?? "")
    .trim()
    .toLowerCase();
  if (!normalized) {
    return null;
  }
  return qqPersonaProfileByAlias.get(normalized)?.id ?? null;
}

function resolveQqPersonaProfile(params: {
  account: ResolvedQqAccount;
  groupId?: string;
  chatType: "group" | "direct";
}) {
  const settings = resolveQqNaturalChatConfig(params);
  const selectedId =
    normalizeQqPersonaId(qqPersonaStateCache?.[params.account.accountId]) ??
    settings.defaultPersona;
  const profile =
    qqPersonaProfiles.find((entry) => entry.id === selectedId) ?? qqPersonaProfiles[0];
  return profile;
}

function setQqPersonaProfile(params: { stateDir: string; accountId: string; personaId: string }) {
  const normalized = normalizeQqPersonaId(params.personaId);
  if (!normalized) {
    return null;
  }
  if (!qqPersonaStateCache) {
    loadQqPersonaState(params.stateDir);
  }
  qqPersonaStateCache ??= {};
  qqPersonaStateCache[params.accountId] = normalized;
  saveQqPersonaState(params.stateDir);
  return qqPersonaProfiles.find((profile) => profile.id === normalized) ?? null;
}

function stripLeadingSelfMention(text: string, selfId?: string) {
  const trimmed = text.trim();
  if (!selfId) {
    return trimmed;
  }
  return trimmed
    .replace(
      new RegExp(`^(?:\\[QQ:${selfId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\]\\s*)+`, "u"),
      "",
    )
    .trim();
}

function stripLeadingQqBracketMentions(text: string) {
  return text.replace(/^(?:\s*\[QQ:\d+\]\s*)+/u, "").trim();
}

function parseQqPersonaCommand(params: { rawBody: string; selfId?: string }) {
  const body = stripLeadingSelfMention(params.rawBody, params.selfId);
  const lower = body.toLowerCase();

  if (
    body === "/persona" ||
    body === "/persona current" ||
    body === "当前人设" ||
    body === "人设"
  ) {
    return { kind: "current" as const };
  }
  if (body === "/persona list" || body === "人设列表" || body === "列出人设") {
    return { kind: "list" as const };
  }

  const switchPatterns = [
    /^\/persona\s+(?:switch\s+)?(.+)$/iu,
    /^切换人设\s+(.+)$/u,
    /^人设切换\s+(.+)$/u,
    /^变成\s+(.+)$/u,
  ];
  for (const pattern of switchPatterns) {
    const match = body.match(pattern);
    if (match?.[1]) {
      const personaId = normalizeQqPersonaId(match[1]);
      if (personaId) {
        return { kind: "switch" as const, personaId };
      }
      return { kind: "invalid" as const, raw: match[1].trim() };
    }
  }

  if (lower === "/persona chino" || lower === "/persona miko") {
    return { kind: "switch" as const, personaId: lower.replace("/persona ", "") };
  }

  return null;
}

function isQqPersonaIdentityQuestion(params: { rawBody: string; selfId?: string }) {
  const body = stripLeadingSelfMention(params.rawBody, params.selfId);
  return /^(你是谁|你叫什么|你叫啥|你是哪个|现在你是谁|现在你叫什么|你不就是谁|你还是谁)/u.test(
    body,
  );
}

function buildQqPersonaIdentityReply(params: {
  persona: QqPersonaProfile;
  rawBody: string;
  selfId?: string;
}) {
  const body = stripLeadingSelfMention(params.rawBody, params.selfId);
  if (/现在你是谁|现在你叫什么/u.test(body)) {
    return `现在是 ${params.persona.label}`;
  }
  if (/你叫什么|你叫啥/u.test(body)) {
    return `我现在叫 ${params.persona.label}`;
  }
  if (/你是谁|你是哪个|你不就是谁|你还是谁/u.test(body)) {
    return `我是 ${params.persona.label}`;
  }
  return `现在是 ${params.persona.label}`;
}

function detectQqExplicitImageIntent(params: { rawBody: string; selfId?: string }) {
  const body = stripLeadingQqBracketMentions(
    stripLeadingSelfMention(params.rawBody, params.selfId),
  );
  const trimmed = body.trim();
  if (!trimmed) {
    return null;
  }
  if (/^用户发送了\d+张?图片$/u.test(trimmed)) {
    return null;
  }
  if (/^(这|这个|这张|这幅|这套).*(是什么|怎么回事|啥意思|什么意思|表情包)$/u.test(trimmed)) {
    return null;
  }

  const directSearchPatterns = [
    /^(?:发个|发张|来个|来张|给我来张|给我发张|找张|搜张|整张)(.+?)(?:图|图片|照片|表情包|梗图)$/u,
    /^(?:搜|搜索|找|给我看看|看看)(.+?)(?:图|图片|照片|表情包|梗图)$/u,
    /^(?:从网上)?(?:搜|搜索|找)(?:个|张)?(.+?)(?:图|图片|照片|表情包|梗图)(?:发给我|发我|给我|给我发|发一下)?$/u,
  ];
  for (const pattern of directSearchPatterns) {
    const match = trimmed.match(pattern);
    if (match?.[1]) {
      const subject = match[1].trim();
      if (!subject) {
        continue;
      }
      const query = /表情包|梗图/u.test(trimmed) ? `${subject} 表情包` : `${subject} 图片`;
      return {
        kind: "search" as const,
        query,
        caption: /表情包|梗图/u.test(trimmed) ? "给你来一张" : "给你找了张",
      };
    }
  }

  if (/^(?:给我)?(?:发个图|来个图|来张图|发张图|发个表情包|来个表情包)$/u.test(trimmed)) {
    return {
      kind: "search" as const,
      query: /表情包/u.test(trimmed) ? "表情包" : "图片",
      caption: /表情包/u.test(trimmed) ? "给你来一张" : "给你找了张",
    };
  }

  return null;
}

function detectQqExplicitMemeIntent(params: {
  rawBody: string;
  selfId?: string;
}): QqExplicitMemeIntent | null {
  const body = stripLeadingQqBracketMentions(
    stripLeadingSelfMention(params.rawBody, params.selfId),
  );
  const trimmed = body.trim();
  if (!trimmed) {
    return null;
  }
  if (
    !/(表情包|配一句|配个字|加字|做成图|做成表情|嵌(?:入)?(?:文字|字)|写上|写个字|写一句)/u.test(
      trimmed,
    )
  ) {
    return null;
  }
  if (
    !/^(?:把|给|帮|请)?(?:这张图|这图|这个图|这张|这个|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图)/u.test(
      trimmed,
    )
  ) {
    return null;
  }

  const multiLineMatch = trimmed.match(
    /^(?:把|给|帮|请)?(?:这张图|这图|这个图|这张|这个|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图)(?:做成|整成|搞成)?(?:个)?表情包(?:吧)?(?:[，,：:\s]+)?(?:上面写(.+?))?(?:[，,；;\s]+)?(?:中间写(.+?))?(?:[，,；;\s]+)?(?:下面写(.+))?$/u,
  );
  if (multiLineMatch) {
    const topText = multiLineMatch[1]?.trim() ?? "";
    const centerText = multiLineMatch[2]?.trim() ?? "";
    const bottomText = multiLineMatch[3]?.trim() ?? "";
    if (topText || centerText || bottomText) {
      return {
        topText: topText || undefined,
        centerText: centerText || undefined,
        bottomText: bottomText || undefined,
        caption: "",
        reason: "explicit-meme-top-bottom",
      };
    }
  }

  const captionPatterns = [
    /^(?:给|帮|请)?(?:这张图|这图|这个图|这张|这个|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图)配(?:一句|个字|句)(.+)$/u,
    /^(?:给|帮|请)?(?:这张图|这图|这个图|这张|这个|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图)加字[:：]?\s*(.+)$/u,
    /^(?:把|给|帮|请)?(?:这张图|这图|这个图|这张|这个|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图)(?:嵌(?:入)?(?:文字|字)|写上|写个字|写一句)[:：]?\s*(.+)$/u,
    /^(?:把|给|帮|请)?(?:这张图|这图|这个图|这张|这个|上面的图|上图|上面那张|上面那个图|前面那张|前面那个图)(?:做成|整成|搞成)?(?:个)?表情包(?:吧)?[:：]?\s*(.+)$/u,
  ];
  for (const pattern of captionPatterns) {
    const match = trimmed.match(pattern);
    const captionText = match?.[1]?.trim() ?? "";
    if (captionText) {
      return {
        bottomText: captionText,
        caption: "",
        reason: "explicit-meme-caption",
      };
    }
  }
  return null;
}

function detectQqDeferredMemeIntent(params: {
  rawBody: string;
  selfId?: string;
}): QqExplicitMemeIntent | null {
  const body = stripLeadingQqBracketMentions(
    stripLeadingSelfMention(params.rawBody, params.selfId),
  );
  const trimmed = body.trim();
  if (!trimmed) {
    return null;
  }
  if (/^用户发送了\d+张?图片$/u.test(trimmed)) {
    return null;
  }
  if (!/(表情包|梗图)/u.test(trimmed)) {
    return null;
  }

  const multiLineMatch = trimmed.match(
    /^(?:给|帮|请)?(?:我)?(?:做|整|搞)(?:个)?(?:表情包|梗图)(?:吧)?(?:[，,：:\s]+)?(?:上面写(.+?))?(?:[，,；;\s]+)?(?:中间写(.+?))?(?:[，,；;\s]+)?(?:下面写(.+))?$/u,
  );
  if (multiLineMatch) {
    const topText = multiLineMatch[1]?.trim() ?? "";
    const centerText = multiLineMatch[2]?.trim() ?? "";
    const bottomText = multiLineMatch[3]?.trim() ?? "";
    if (topText || centerText || bottomText) {
      return {
        topText: topText || undefined,
        centerText: centerText || undefined,
        bottomText: bottomText || undefined,
        caption: "",
        reason: "deferred-meme-top-bottom",
      };
    }
  }

  const captionPatterns = [
    /^(?:给|帮|请)?(?:我)?(?:做|整|搞)(?:个)?(?:表情包|梗图)(?:吧)?(?:[，,：:\s]+)?(?:文字(?:添加|加上?|写(?:上)?|配(?:上)?)|加字|配字|配文|嵌(?:入)?(?:文字|字)|写上|写一句|配一句|文案(?:加上?|写(?:上)?)?)[:：]?\s*(.+)$/u,
  ];
  for (const pattern of captionPatterns) {
    const match = trimmed.match(pattern);
    const captionText = match?.[1]?.trim() ?? "";
    if (captionText) {
      return {
        bottomText: captionText,
        caption: "",
        reason: "deferred-meme-caption",
      };
    }
  }
  return null;
}

function resolveQqReplayMediaTypeFilter(text: string): QqReplayMediaTypeFilter {
  if (/表情包|梗图|图|图片|照片|截图/u.test(text)) {
    return "image";
  }
  if (/表情|动图|gif/u.test(text)) {
    return "emoji";
  }
  return "any";
}

function detectQqReplayRecentMediaIntent(params: {
  rawBody: string;
  selfId?: string;
  hasCurrentMedia: boolean;
}) {
  const body = stripLeadingSelfMention(params.rawBody, params.selfId);
  const trimmed = body.trim();
  if (!trimmed) {
    return null;
  }
  const replayVerb = /(再发|重发|发一下|发一遍|来一下|来一遍|再来一张|再来一个|复读|转发)/u;
  if (!replayVerb.test(trimmed)) {
    return null;
  }
  const typeFilter = resolveQqReplayMediaTypeFilter(trimmed);
  const preferOutbound = /你刚发|你刚刚发|机器人刚发|你上次发/u.test(trimmed);

  const directCurrentPatterns = [
    /^(?:把)?(?:这张|这个图|这图片|刚那个图|刚刚那个图|那个图)(?:再发|重发|发一下|发一遍|来一下|来一遍)/u,
    /^(?:把)?(?:这个表情包|那个表情包)(?:再发|重发|发一下|发一遍|来一下|来一遍)/u,
    /^(?:把)?(?:这个表情|那个表情|这个动图|那个动图)(?:再发|重发|发一下|发一遍|来一下|来一遍)/u,
    /^(?:把)?(?:我|你)?刚(?:刚|才)?发(?:给你|你的|给我|我的)?(?:的)?(?:那个|那张|这个|这张)?(?:图|图片|表情包|表情|动图|gif)(?:再发|重发|发一下|发一遍|来一下|来一遍)/u,
    /^(?:再发|重发|发一下|发一遍|来一下|来一遍)(?:我|你)?刚(?:刚|才)?发(?:给你|你的|给我|我的)?(?:的)?(?:那个|那张|这个|这张)?(?:图|图片|表情包|表情|动图|gif)/u,
  ];
  if (directCurrentPatterns.some((pattern) => pattern.test(trimmed))) {
    return {
      index: 0,
      typeFilter,
      preferOutbound,
    };
  }

  const repeatedUpMatch = trimmed.match(
    /(上+)(?:一)?(?:张|个|条)?(?:图|图片|表情包|表情|动图|gif)?(?:再发|重发|发一下|发一遍|来一下|来一遍|再来一张|再来一个|复读|转发)/u,
  );
  if (repeatedUpMatch?.[1]) {
    const upCount = repeatedUpMatch[1].length;
    const index = Math.max(0, upCount - 1 + (params.hasCurrentMedia ? 1 : 0));
    return {
      index,
      typeFilter,
      preferOutbound,
    };
  }

  const reverseMatch = trimmed.match(
    /倒数第([一二两三四五六七八九十\d]+)(?:张|个|条)(?:图|图片|表情包|表情|动图|gif)?/u,
  );
  if (reverseMatch?.[1]) {
    const parsed = parseQqChineseNumberToken(reverseMatch[1]);
    if (parsed && parsed > 0) {
      return {
        index: parsed - 1,
        typeFilter,
        preferOutbound,
      };
    }
  }

  const ordinalMatch = trimmed.match(
    /第([一二两三四五六七八九十\d]+)(?:张|个|条)(?:图|图片|表情包|表情|动图|gif)?/u,
  );
  if (ordinalMatch?.[1]) {
    const parsed = parseQqChineseNumberToken(ordinalMatch[1]);
    if (parsed && parsed > 0) {
      return {
        index: parsed - 1,
        typeFilter,
        preferOutbound,
      };
    }
  }

  const genericReplayPattern =
    /^(?:把)?(?:图|图片|表情包|表情|动图)(?:再发|重发|发一下|发一遍|来一下|来一遍|再来一张|再来一个|复读|转发)/u;
  if (genericReplayPattern.test(trimmed)) {
    return {
      index: 0,
      typeFilter,
      preferOutbound,
    };
  }

  return null;
}

function decodeBingEntityText(text: string) {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">");
}

function guessDownloadedImageExtension(params: { sourceUrl: string; contentType?: string | null }) {
  const pathname = (() => {
    try {
      return new URL(params.sourceUrl).pathname.toLowerCase();
    } catch {
      return "";
    }
  })();
  for (const ext of [".png", ".jpg", ".jpeg", ".webp", ".gif"]) {
    if (pathname.endsWith(ext)) {
      return ext === ".jpeg" ? ".jpg" : ext;
    }
  }
  const contentType = String(params.contentType ?? "").toLowerCase();
  if (contentType.includes("png")) {
    return ".png";
  }
  if (contentType.includes("webp")) {
    return ".webp";
  }
  if (contentType.includes("gif")) {
    return ".gif";
  }
  return ".jpg";
}

function pruneRecentQqImageSearchSelections(nowMs: number) {
  for (const [key, ts] of recentQqImageSearchSelections.entries()) {
    if (nowMs - ts > QQ_IMAGE_SEARCH_RECENT_SELECTION_TTL_MS) {
      recentQqImageSearchSelections.delete(key);
    }
  }
}

function buildQqImageSearchSelectionOrder(params: {
  sourceUrls: string[];
  selectionKey?: string;
  nowMs?: number;
}) {
  const unique = Array.from(
    new Set(params.sourceUrls.filter((value) => /^https?:\/\//i.test(value))),
  );
  if (!params.selectionKey || unique.length <= 1) {
    return unique;
  }
  const nowMs = params.nowMs ?? Date.now();
  pruneRecentQqImageSearchSelections(nowMs);
  const cursor = qqImageSearchCursorByKey.get(params.selectionKey) ?? 0;
  const rotated = unique.map(
    (_, index) => unique[(cursor + index) % unique.length] ?? unique[index]!,
  );
  const fresh: string[] = [];
  const recent: string[] = [];
  for (const url of rotated) {
    const recentKey = `${params.selectionKey}::${url}`;
    if (recentQqImageSearchSelections.has(recentKey)) {
      recent.push(url);
    } else {
      fresh.push(url);
    }
  }
  return [...fresh, ...recent];
}

function rememberQqImageSearchSelection(params: {
  sourceUrl: string;
  selectionKey?: string;
  totalCount: number;
  nowMs?: number;
}) {
  if (!params.selectionKey || params.totalCount <= 0) {
    return;
  }
  const nowMs = params.nowMs ?? Date.now();
  recentQqImageSearchSelections.set(`${params.selectionKey}::${params.sourceUrl}`, nowMs);
  const cursor = qqImageSearchCursorByKey.get(params.selectionKey) ?? 0;
  qqImageSearchCursorByKey.set(params.selectionKey, (cursor + 1) % Math.max(1, params.totalCount));
}

function resetQqImageSearchSelectionState() {
  recentQqImageSearchSelections.clear();
  qqImageSearchCursorByKey.clear();
}

async function searchQqImageToLocalFile(params: string | { query: string; selectionKey?: string }) {
  const query = typeof params === "string" ? params : params.query;
  const selectionKey =
    typeof params === "string"
      ? params.trim() || undefined
      : params.selectionKey?.trim() || params.query.trim() || undefined;
  const url = new URL("https://www.bing.com/images/search");
  url.searchParams.set("q", query);
  url.searchParams.set("form", "HDRSC3");

  const response = await fetch(url, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    },
  });
  if (!response.ok) {
    return null;
  }
  const html = await response.text();
  const matches = [...html.matchAll(/class="iusc"[^>]+m="([^"]+)"/g)];
  const sourceUrls = Array.from(
    new Set(
      matches
        .map((match) => match[1])
        .map((value) => decodeBingEntityText(value))
        .map((value) => {
          try {
            return JSON.parse(value).murl as string;
          } catch {
            return "";
          }
        })
        .filter((value) => /^https?:\/\//i.test(value)),
    ),
  );
  if (sourceUrls.length === 0) {
    return null;
  }
  const orderedSourceUrls = buildQqImageSearchSelectionOrder({
    sourceUrls,
    selectionKey,
  });

  await fs.promises.mkdir(IMAGE_SEARCH_OUTPUT_DIR, { recursive: true });
  for (const sourceUrl of orderedSourceUrls) {
    try {
      const imageResponse = await fetch(sourceUrl);
      if (!imageResponse.ok) {
        continue;
      }
      const contentType = imageResponse.headers.get("content-type");
      if (contentType && !contentType.toLowerCase().startsWith("image/")) {
        continue;
      }
      const buffer = Buffer.from(await imageResponse.arrayBuffer());
      const ext = guessDownloadedImageExtension({ sourceUrl, contentType });
      const filePath = path.join(
        IMAGE_SEARCH_OUTPUT_DIR,
        `auto-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`,
      );
      await fs.promises.writeFile(filePath, buffer);
      rememberQqImageSearchSelection({
        sourceUrl,
        selectionKey,
        totalCount: orderedSourceUrls.length,
      });
      return {
        sourceUrl,
        mediaUrl: `file://${filePath}`,
      };
    } catch {
      // ignore
    }
  }
  return null;
}

async function sendImmediateQqTextReply(params: {
  cfg: CoreConfig;
  accountId?: string;
  event: OneBotMessageEvent;
  text: string;
  conversationKey?: string;
}) {
  const isGroup = params.event.message_type === "group";
  const targetKind = isGroup ? "group" : "user";
  const targetId = isGroup ? String(params.event.group_id ?? "") : String(params.event.user_id);
  if (!targetId || !params.text.trim()) {
    return null;
  }
  const result = await sendQqText({
    cfg: params.cfg,
    accountId: params.accountId,
    targetKind,
    targetId,
    text: params.text.trim(),
  });
  noteQqReplyDelivery(params.conversationKey, result);
  return result;
}

async function sendImmediateQqMediaReply(params: {
  cfg: OpenClawConfig;
  accountId?: string;
  event: OneBotMessageEvent;
  text?: string;
  mediaUrl: string;
  audioAsVoice?: boolean;
  conversationKey?: string;
  agentId?: string;
  bypassDedup?: boolean;
}) {
  const isGroup = params.event.message_type === "group";
  const targetKind = isGroup ? "group" : "user";
  const targetId = isGroup ? String(params.event.group_id ?? "") : String(params.event.user_id);
  if (!targetId || !params.mediaUrl.trim()) {
    return null;
  }
  const result = await sendQqMedia({
    cfg: params.cfg as CoreConfig,
    accountId: params.accountId,
    targetKind,
    targetId,
    text: params.text?.trim() ?? "",
    mediaUrl: params.mediaUrl.trim(),
    audioAsVoice: params.audioAsVoice,
    bypassDedup: params.bypassDedup,
  });
  noteQqReplyDelivery(params.conversationKey, result);
  await rememberOutboundQqMedia({
    conversationKey: params.conversationKey,
    cfg: params.cfg,
    agentId: params.agentId ?? "main",
    mediaUrl: params.mediaUrl.trim(),
    caption: params.text?.trim() ?? "",
    result,
  });
  return result;
}

function extractQqNativeImagePrompt(rawBody: string): string | null {
  const text = rawBody.trim();
  if (!text || !QQ_NATIVE_IMAGE_REQUEST_RE.test(text)) {
    return null;
  }
  return text
    .replace(/^\s*(?:请|帮我|给我|麻烦)?\s*(?:直接)?\s*/u, "")
    .replace(/^(?:画图|绘图|生图|出图)[:：,，\s]*/iu, "")
    .trim() || text;
}

async function generateQqNativeImage(params: {
  prompt: string;
  outDir: string;
  timeoutMs?: number;
}): Promise<string> {
  const args = [
    QQ_NATIVE_IMAGE_SCRIPT,
    "--model",
    "gpt-5.5",
    "--base-url",
    QQ_NATIVE_IMAGE_BASE_URL,
    "--prompt",
    params.prompt,
    "--count",
    "1",
    "--quality",
    "low",
    "--media-lines",
    "--out-dir",
    params.outDir,
  ];
  const { stdout, stderr } = await execFileAsync(QQ_NATIVE_IMAGE_PYTHON, args, {
    timeout: params.timeoutMs ?? 300_000,
    maxBuffer: 1024 * 1024,
  });
  const mediaLine = stdout
    .split(/\r?\n/u)
    .map((line) => line.trim())
    .find((line) => line.startsWith("MEDIA:"));
  if (!mediaLine) {
    throw new Error(`native image generation returned no MEDIA line: ${stderr || stdout}`.slice(0, 500));
  }
  const mediaPath = mediaLine.slice("MEDIA:".length).trim();
  if (!mediaPath) {
    throw new Error("native image generation returned empty MEDIA path");
  }
  return mediaPath;
}

async function tryHandleQqNativeImageRequest(params: {
  api: OpenClawPluginApi;
  cfg: OpenClawConfig;
  account: ResolvedQqAccount;
  event: OneBotMessageEvent;
  rawBody: string;
  conversationKey: string;
}): Promise<boolean> {
  const prompt = extractQqNativeImagePrompt(params.rawBody);
  if (!prompt) {
    return false;
  }
  const outDir = path.join(
    os.homedir(),
    ".openclaw",
    "media",
    "generated",
    `qq-native-image-${Date.now()}`,
  );
  try {
    params.api.logger.info(`[qq] native image generation requested: conversation=${params.conversationKey}`);
    const mediaPath = await generateQqNativeImage({ prompt, outDir });
    await sendImmediateQqMediaReply({
      cfg: params.cfg,
      accountId: params.account.accountId,
      event: params.event,
      mediaUrl: mediaPath,
      conversationKey: params.conversationKey,
      bypassDedup: true,
    });
    params.api.logger.info(`[qq] native image generation sent: conversation=${params.conversationKey} media=${mediaPath}`);
    return true;
  } catch (error) {
    params.api.logger.error(`[qq] native image generation failed: ${String(error)}`);
    await sendImmediateQqTextReply({
      cfg: params.cfg as CoreConfig,
      accountId: params.account.accountId,
      event: params.event,
      text: `画图失败了：${String(error).slice(0, 160)}`,
      conversationKey: params.conversationKey,
    }).catch(() => undefined);
    return true;
  }
}

function didQqSendSucceed(result: OneBotApiResponse | null | undefined) {
  return result?.status === "ok" || result?.retcode === 0;
}

function resolveChinobotBridgeConfig(cfg: OpenClawConfig) {
  const pluginConfig = ((
    cfg as {
      plugins?: {
        entries?: Record<string, { config?: Record<string, unknown> }>;
      };
    }
  ).plugins?.entries?.["chinobot-bridge"]?.config ?? {}) as {
    projectRoot?: unknown;
    bridgeScript?: unknown;
    pythonPath?: unknown;
    timeoutMs?: unknown;
  };
  const projectRoot =
    typeof pluginConfig.projectRoot === "string" && pluginConfig.projectRoot.trim()
      ? pluginConfig.projectRoot.trim()
      : DEFAULT_CHINOBOT_PROJECT_ROOT;
  return {
    projectRoot,
    bridgeScript:
      typeof pluginConfig.bridgeScript === "string" && pluginConfig.bridgeScript.trim()
        ? pluginConfig.bridgeScript.trim()
        : `${projectRoot}/bridge/openclaw_tool_bridge.py`,
    pythonPath:
      typeof pluginConfig.pythonPath === "string" && pluginConfig.pythonPath.trim()
        ? pluginConfig.pythonPath.trim()
        : "python3",
    timeoutMs:
      typeof pluginConfig.timeoutMs === "number" && Number.isFinite(pluginConfig.timeoutMs)
        ? pluginConfig.timeoutMs
        : DEFAULT_CHINOBOT_BRIDGE_TIMEOUT_MS,
  };
}

async function invokeChinobotBridgeTool(
  cfg: OpenClawConfig,
  toolName: string,
  params: Record<string, unknown>,
) {
  const bridge = resolveChinobotBridgeConfig(cfg);
  return await new Promise<Record<string, unknown> | null>((resolve) => {
    execFile(
      bridge.pythonPath,
      [
        bridge.bridgeScript,
        "invoke",
        "--tool",
        toolName,
        "--params-json",
        JSON.stringify(params ?? {}),
      ],
      {
        cwd: bridge.projectRoot,
        timeout: bridge.timeoutMs,
        maxBuffer: 8 * 1024 * 1024,
      },
      (error, stdout) => {
        if (error) {
          resolve({
            ok: false,
            error: error.message,
          });
          return;
        }
        try {
          const parsed = JSON.parse(String(stdout ?? "").trim()) as Record<string, unknown>;
          resolve(parsed);
        } catch (parseError) {
          resolve({
            ok: false,
            error: `bridge returned invalid JSON: ${String(parseError)}`,
          });
        }
      },
    );
  });
}

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildTouchReactionText(params: {
  senderName?: string;
  touchCount: number;
  playfulness: number;
  mischief: number;
}) {
  const lines =
    params.touchCount >= 3
      ? [
          "你们今天怎么都趁机摸我啊",
          "怎么还摸上瘾了你们",
          "再摸我要记仇了啊",
          "别装无辜 这都第几次了",
        ]
      : params.playfulness >= 0.56 || params.mischief >= 0.5
        ? ["又来占我便宜是吧", "你这个手很不老实啊", "趁机摸一下就跑是吧", "我看见你的小动作了"]
        : ["你怎么又偷偷碰我一下", "别突然摸我呀", "我有看到你的小动作", "又来碰我一下啊"];
  return lines[Math.floor(Math.random() * lines.length)] ?? "又来占我便宜是吧";
}

function looksLikeQqTeasingTouch(text: string) {
  return /(摸摸|摸一下|又摸一下|摸了你一下|偷偷摸了你一下|碰一下|又碰一下|碰了碰你|占我便宜|戳一戳|戳戳|poke)/iu.test(
    text,
  );
}

function buildTouchTimeoutMinutes(params: {
  sameSenderTouchCount: number;
  totalTouchCount: number;
  uniqueTouchSenders: number;
}) {
  const sameSenderMinutes = 1 + Math.max(0, params.sameSenderTouchCount - 4) * 2;
  const dogpileMinutes =
    1 +
    Math.max(0, params.totalTouchCount - 5) +
    (params.uniqueTouchSenders >= 4 ? 1 : 0) +
    (params.uniqueTouchSenders >= 5 ? 1 : 0);
  const escalatedMinutes =
    params.sameSenderTouchCount >= 4 ? sameSenderMinutes : Math.min(5, dogpileMinutes);
  return Math.max(1, Math.min(10, escalatedMinutes));
}

function buildTouchTimeoutText(params: {
  durationMinutes: number;
  sameSenderTouchCount: number;
  dogpile: boolean;
}) {
  if (params.dogpile && params.sameSenderTouchCount < 4) {
    return `跟风摸也算 先关你 ${params.durationMinutes} 分钟冷静一下`;
  }
  if (params.sameSenderTouchCount >= 6) {
    return `先罚你冷静 ${params.durationMinutes} 分钟 手别这么欠`;
  }
  return `先关你 ${params.durationMinutes} 分钟冷静一下 不许老趁机动手动脚`;
}

function buildQqUserAvatarUrl(userId: string, size = 640) {
  const spec = size >= 640 ? 640 : size >= 140 ? 140 : size >= 100 ? 100 : 40;
  return `https://q.qlogo.cn/headimg_dl?dst_uin=${encodeURIComponent(userId)}&spec=${spec}&img_type=jpg`;
}

function buildAvatarMemeText(params: {
  senderName?: string;
  closeness: number;
  playfulness: number;
}) {
  const sender = (params.senderName ?? "你").trim();
  if (params.playfulness >= 0.62 || params.closeness >= 0.58) {
    return `${sender}今天这头像也太有戏了`;
  }
  return `${sender}这头像我先存一张`;
}

function buildCurrentImageMemePlan(params: {
  rawBody: string;
  senderName?: string;
  playfulness: number;
  mischief: number;
}) {
  const sender = (params.senderName ?? "你").trim() || "你";
  const compact = params.rawBody.replace(/\s+/g, " ").trim();
  if (looksLikeQqTeasingTouch(compact)) {
    return {
      topText: "手又开始不老实",
      bottomText: "我先把这张记下来",
      caption: "这张我先整一下",
    };
  }
  if (compact && compact.length <= 18 && /[?？!！~～]/u.test(compact)) {
    return {
      centerText: compact,
      caption: `${sender}这张图精神状态很完整`,
    };
  }
  if (compact && compact.length <= 16) {
    return {
      topText: "本轮群聊素材",
      bottomText: compact,
      caption: "这张就很适合顺手加工一下",
    };
  }
  if (params.playfulness >= 0.62 || params.mischief >= 0.55) {
    return {
      topText: "你这张有点太会演了",
      bottomText: "我先偷拿来整活",
      caption: `${sender}这张也太有节目效果了`,
    };
  }
  return {
    topText: "这张有戏",
    bottomText: "先轻轻加工一下",
    caption: "让我先顺手整一下这张图",
  };
}

async function tryHandleImmediateQqSocialAgencyRecipe(params: {
  api: OpenClawPluginApi;
  cfg: OpenClawConfig;
  accountId?: string;
  event: OneBotMessageEvent;
  conversationKey: string;
  agentId?: string;
  groupId?: string;
  groupDir?: string | null;
  senderId: string;
  rawBody: string;
  senderName?: string;
  recentMessages: QqRecentMessageSample[];
  currentTurnMemeBaseImage?: {
    image_path?: string;
    image_url?: string;
    summary: string;
  } | null;
  socialAgencyPlan: QqSocialAgencyPlan | null;
  pendingCount: number;
}) {
  const selectedRecipe = params.socialAgencyPlan?.selectedRecipe?.recipe;
  if (!selectedRecipe || params.pendingCount >= 3) {
    return false;
  }
  const recordOutcome = (success: boolean, note?: string) => {
    if (!params.groupId) {
      return;
    }
    recordQqSocialAgencyOutcome({
      groupDir: params.groupDir,
      groupId: params.groupId,
      senderId: params.senderId,
      senderName: params.senderName,
      plan: params.socialAgencyPlan,
      success,
      note,
      nowMs: Date.now(),
    });
  };
  const nowMs = Date.now();
  const recentTouchCount = params.recentMessages.filter(
    (entry) => nowMs - entry.createdAt <= 10 * 60 * 1000 && looksLikeQqTeasingTouch(entry.text),
  ).length;
  const currentMessageAlreadyTracked = params.recentMessages.some(
    (entry) =>
      entry.senderId === params.senderId &&
      looksLikeQqTeasingTouch(entry.text) &&
      entry.text.trim().toLowerCase() === params.rawBody.trim().toLowerCase() &&
      Math.abs(nowMs - entry.createdAt) <= 15_000,
  );
  const touchCount =
    recentTouchCount +
    (looksLikeQqTeasingTouch(params.rawBody) && !currentMessageAlreadyTracked ? 1 : 0);
  const sameSenderTouchCount =
    params.recentMessages.filter(
      (entry) =>
        nowMs - entry.createdAt <= 6 * 60 * 1000 &&
        entry.senderId === params.senderId &&
        looksLikeQqTeasingTouch(entry.text),
    ).length + (looksLikeQqTeasingTouch(params.rawBody) && !currentMessageAlreadyTracked ? 1 : 0);
  const touchStormSamples = params.recentMessages.filter(
    (entry) => nowMs - entry.createdAt <= 6 * 60 * 1000 && looksLikeQqTeasingTouch(entry.text),
  );
  const normalizedTouchStormSamples =
    looksLikeQqTeasingTouch(params.rawBody) && !currentMessageAlreadyTracked
      ? touchStormSamples.concat({
          senderId: params.senderId,
          text: params.rawBody,
          createdAt: nowMs,
          wasMentioned: params.event.message_type === "group" ? false : false,
          isReply: false,
        })
      : touchStormSamples;
  const uniqueTouchSenders = new Set(normalizedTouchStormSamples.map((entry) => entry.senderId))
    .size;
  const isTouchDogpile = normalizedTouchStormSamples.length >= 5 && uniqueTouchSenders >= 3;
  const mode = params.socialAgencyPlan?.mode;
  if (!mode || (mode !== "play_reply" && mode !== "light_surprise" && mode !== "staged_surprise")) {
    return false;
  }

  const logImmediate = (reason?: string) => {
    recordQqDebugEvent({
      api: params.api,
      conversationKey: params.conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "dispatch_immediate",
        mode: `social_agency_${selectedRecipe.id}`,
        reason,
        rawBodyPreview: previewText(params.rawBody, 120),
      },
    });
  };

  if (selectedRecipe.id === "touch_reaction") {
    const replyText = buildTouchReactionText({
      senderName: params.senderName,
      touchCount,
      playfulness: params.socialAgencyPlan?.state.playfulness ?? 0.4,
      mischief: params.socialAgencyPlan?.state.mischief ?? 0.4,
    });
    logImmediate("social-agency-touch-reaction");
    const sendResult = await sendImmediateQqTextReply({
      cfg: params.cfg as CoreConfig,
      accountId: params.accountId,
      event: params.event,
      text: replyText,
      conversationKey: params.conversationKey,
    });
    const ok = didQqSendSucceed(sendResult);
    recordOutcome(ok, ok ? "immediate_text" : "immediate_text_send_failed");
    return ok;
  }

  if (selectedRecipe.id === "touch_timeout") {
    if (!params.groupId || (sameSenderTouchCount < 4 && !isTouchDogpile)) {
      recordOutcome(false, "touch_timeout_not_applicable");
      return false;
    }
    const durationMinutes = buildTouchTimeoutMinutes({
      sameSenderTouchCount,
      totalTouchCount: normalizedTouchStormSamples.length,
      uniqueTouchSenders,
    });
    logImmediate("touch_timeout");
    const banResult = await setQqGroupBan({
      cfg: params.cfg as CoreConfig,
      accountId: params.accountId,
      groupId: params.groupId,
      userId: params.senderId,
      duration: durationMinutes * 60,
    }).catch(() => null);
    const ok = didQqSendSucceed(banResult);
    if (ok) {
      await sendImmediateQqTextReply({
        cfg: params.cfg as CoreConfig,
        accountId: params.accountId,
        event: params.event,
        text: buildTouchTimeoutText({
          durationMinutes,
          sameSenderTouchCount,
          dogpile: isTouchDogpile,
        }),
        conversationKey: params.conversationKey,
      }).catch(() => null);
    }
    recordOutcome(ok, ok ? `touch_timeout_${durationMinutes}m` : "touch_timeout_failed");
    return ok;
  }

  if (selectedRecipe.id === "avatar_meme") {
    const avatarUrl = buildQqUserAvatarUrl(params.senderId, 640);
    const memeText = buildAvatarMemeText({
      senderName: params.senderName,
      closeness: params.socialAgencyPlan?.relationship.closeness ?? 0.2,
      playfulness: params.socialAgencyPlan?.state.playfulness ?? 0.4,
    });
    const memeResult = await runQqMakeMeme(
      {
        image_url: avatarUrl,
        text: memeText,
        caption: "拿你头像轻轻整一下",
        preserve_original_size: true,
        max_width: 1024,
        max_height: 1024,
      },
      params.cfg as CoreConfig,
    ).catch(() => null);
    if (!memeResult?.ok || !memeResult.mediaUrl) {
      recordOutcome(false, "avatar_meme_failed");
      return false;
    }
    logImmediate("avatar_meme");
    const sendResult = await sendImmediateQqMediaReply({
      cfg: params.cfg,
      accountId: params.accountId,
      event: params.event,
      text: "这张我先偷存了",
      mediaUrl: memeResult.mediaUrl,
      conversationKey: params.conversationKey,
      agentId: params.agentId,
    });
    const ok = didQqSendSucceed(sendResult);
    recordOutcome(ok, ok ? "avatar_meme" : "avatar_meme_send_failed");
    return ok;
  }

  if (selectedRecipe.id === "current_image_meme") {
    const baseImage = params.currentTurnMemeBaseImage;
    if (!baseImage?.image_path && !baseImage?.image_url) {
      recordOutcome(false, "current_image_meme_missing_base");
      return false;
    }
    const memePlan = buildCurrentImageMemePlan({
      rawBody: params.rawBody,
      senderName: params.senderName,
      playfulness: params.socialAgencyPlan?.state.playfulness ?? 0.4,
      mischief: params.socialAgencyPlan?.state.mischief ?? 0.4,
    });
    const memeResult = await runQqMakeMeme(
      {
        image_path: baseImage.image_path,
        image_url: baseImage.image_url,
        top_text: memePlan.topText,
        bottom_text: memePlan.bottomText,
        center_text: memePlan.centerText,
        caption: memePlan.caption,
        preserve_original_size: true,
        max_width: 1280,
        max_height: 1280,
      },
      params.cfg as CoreConfig,
    ).catch(() => null);
    if (!memeResult?.ok || !memeResult.mediaUrl) {
      recordOutcome(false, "current_image_meme_failed");
      return false;
    }
    logImmediate("current_image_meme");
    const sendResult = await sendImmediateQqMediaReply({
      cfg: params.cfg,
      accountId: params.accountId,
      event: params.event,
      text: memePlan.caption,
      mediaUrl: memeResult.mediaUrl,
      conversationKey: params.conversationKey,
      agentId: params.agentId,
    });
    const ok = didQqSendSucceed(sendResult);
    recordOutcome(ok, ok ? "current_image_meme" : "current_image_meme_send_failed");
    return ok;
  }

  return false;
}

function resolveQqMemeBaseImageFromRecord(record: QqMediaRecord | null | undefined) {
  if (!record || record.type !== "image") {
    return null;
  }
  const image = record.images.find((entry) => entry.path?.trim() || entry.url?.trim());
  if (!image) {
    return null;
  }
  return {
    image_path: image.path?.trim() || undefined,
    image_url: image.url?.trim() || undefined,
    summary: record.summary,
  };
}

function resolveQqCurrentTurnMemeBaseImage(params: {
  currentMedia: QqMediaRecord[];
  boundMedia: { record: QqMediaRecord; source: string } | null;
}) {
  const currentImageRecord = params.currentMedia.find((entry) => entry.type === "image");
  if (currentImageRecord) {
    return resolveQqMemeBaseImageFromRecord(currentImageRecord);
  }
  if (params.boundMedia?.source === "current-message") {
    return resolveQqMemeBaseImageFromRecord(params.boundMedia.record);
  }
  return null;
}

function resolvePendingQqDeferredMemeIntent(params: {
  conversationKey: string;
  senderId: string;
  currentMessageId?: string;
  messageTimestamp: number;
  selfId?: string;
}) {
  const recentMessages = refreshQqConversationLoad(params.conversationKey).recentMessages;
  for (let index = recentMessages.length - 1; index >= 0; index -= 1) {
    const candidate = recentMessages[index];
    if (!candidate) {
      continue;
    }
    if (candidate.direction !== "inbound" || candidate.senderId !== params.senderId) {
      continue;
    }
    if (params.currentMessageId && candidate.id === params.currentMessageId) {
      continue;
    }
    if (params.messageTimestamp < candidate.createdAt) {
      continue;
    }
    if (params.messageTimestamp - candidate.createdAt > QQ_PENDING_MEME_REQUEST_TTL_MS) {
      break;
    }
    const intent = detectQqDeferredMemeIntent({
      rawBody: candidate.text,
      selfId: params.selfId,
    });
    if (intent) {
      return {
        ...intent,
        sourceMessageId: candidate.id,
        sourceText: candidate.text,
      };
    }
  }
  return null;
}

async function sendImmediateQqRecentMediaReply(params: {
  cfg: OpenClawConfig;
  accountId?: string;
  event: OneBotMessageEvent;
  mediaRecord: QqMediaRecord;
  conversationKey?: string;
  agentId?: string;
}) {
  const isGroup = params.event.message_type === "group";
  const targetKind = isGroup ? "group" : "user";
  const targetId = isGroup ? String(params.event.group_id ?? "") : String(params.event.user_id);
  if (!targetId) {
    return false;
  }

  if (params.mediaRecord.type !== "image" && params.mediaRecord.replay_segments?.length) {
    const result = await sendQqSegments({
      cfg: params.cfg as CoreConfig,
      accountId: params.accountId,
      targetKind,
      targetId,
      message: params.mediaRecord.replay_segments,
    });
    noteQqReplyDelivery(params.conversationKey, result);
    const messageId = getOneBotMessageId(result);
    if (params.conversationKey) {
      rememberQqMediaRecords(params.conversationKey, [
        {
          ...params.mediaRecord,
          id: `outbound:${messageId ?? "pending"}:${Date.now()}`,
          source: "outbound",
          message_id: messageId,
          created_at: Date.now(),
        },
      ]);
    }
    return true;
  }

  let sentAny = false;
  for (const image of params.mediaRecord.images) {
    const mediaUrl = image.path ? `file://${image.path}` : (image.url ?? "");
    if (!mediaUrl.trim()) {
      continue;
    }
    await sendImmediateQqMediaReply({
      cfg: params.cfg,
      accountId: params.accountId,
      event: params.event,
      mediaUrl,
      conversationKey: params.conversationKey,
      agentId: params.agentId,
      bypassDedup: true,
    });
    sentAny = true;
  }
  return sentAny;
}

function buildQqDeliveryFingerprint(params: {
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  text?: string;
  mediaUrl?: string;
}) {
  return [
    params.accountId ?? "default",
    params.targetKind,
    params.targetId.trim(),
    (params.text ?? "").replace(/\s+/g, " ").trim(),
    params.mediaUrl ?? "",
  ].join("::");
}

function pruneRecentQqDeliveryFingerprints(now: number) {
  for (const [fingerprint, ts] of recentQqDeliveryFingerprints.entries()) {
    if (now - ts > QQ_RECENT_DELIVERY_TTL_MS) {
      recentQqDeliveryFingerprints.delete(fingerprint);
    }
  }
}

function loadRecentQqDeliveries(stateDir: string) {
  const filePath = resolveRecentQqDeliveryFile(stateDir);
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const data = JSON.parse(raw) as Record<string, number>;
    const now = Date.now();
    for (const [fingerprint, ts] of Object.entries(data)) {
      if (typeof ts === "number" && Number.isFinite(ts) && now - ts <= QQ_RECENT_DELIVERY_TTL_MS) {
        recentQqDeliveryFingerprints.set(fingerprint, ts);
      }
    }
  } catch {
    // ignore
  }
}

function saveRecentQqDeliveries(stateDir: string) {
  pruneRecentQqDeliveryFingerprints(Date.now());
  const filePath = resolveRecentQqDeliveryFile(stateDir);
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(
      filePath,
      `${JSON.stringify(Object.fromEntries(recentQqDeliveryFingerprints), null, 2)}\n`,
      "utf8",
    );
  } catch {
    // ignore
  }
}

function rememberQqDeliveryFingerprint(params: {
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  text?: string;
  mediaUrl?: string;
}) {
  const fingerprint = buildQqDeliveryFingerprint(params);
  const now = Date.now();
  recentQqDeliveryFingerprints.set(fingerprint, now);
  if (qqStateDirForRecovery) {
    saveRecentQqDeliveries(qqStateDirForRecovery);
  }
}

function shouldSkipDuplicateQqDelivery(params: {
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  text?: string;
  mediaUrl?: string;
}) {
  pruneRecentQqDeliveryFingerprints(Date.now());
  const fingerprint = buildQqDeliveryFingerprint(params);
  const lastSentAt = recentQqDeliveryFingerprints.get(fingerprint);
  if (!lastSentAt) {
    return false;
  }
  return Date.now() - lastSentAt <= QQ_RECENT_DELIVERY_TTL_MS;
}

function parseQueuedQqTarget(target: string): { kind: "user" | "group"; id: string } | null {
  const trimmed = target.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("qq:group:")) {
    return { kind: "group", id: trimmed.slice("qq:group:".length) };
  }
  if (trimmed.startsWith("qq:user:")) {
    return { kind: "user", id: trimmed.slice("qq:user:".length) };
  }
  if (trimmed.startsWith("group:")) {
    return { kind: "group", id: trimmed.slice("group:".length) };
  }
  if (trimmed.startsWith("user:")) {
    return { kind: "user", id: trimmed.slice("user:".length) };
  }
  if (trimmed.startsWith("qq:")) {
    return { kind: "user", id: trimmed.slice("qq:".length) };
  }
  return /^\d+$/.test(trimmed) ? { kind: "user", id: trimmed } : null;
}

function buildDirectFollowupWatchKey(params: {
  accountId: string;
  groupId?: string;
  senderId: string;
}): string | null {
  const groupId = params.groupId?.trim();
  if (!groupId) {
    return null;
  }
  return `${params.accountId}::${groupId}::${params.senderId}`;
}

function pruneDirectFollowupWatch(key: string, now: number) {
  const state = directFollowupWatches.get(key);
  if (!state) {
    return null;
  }
  if (state.consecutiveMisses >= DIRECT_FOLLOWUP_WATCH_MAX_MISSES) {
    directFollowupWatches.delete(key);
    return null;
  }
  if (now - state.lastObservedAt > DIRECT_FOLLOWUP_WATCH_IDLE_MS) {
    directFollowupWatches.delete(key);
    return null;
  }
  return state;
}

function touchDirectFollowupWatch(params: {
  accountId: string;
  groupId?: string;
  senderId: string;
  now: number;
  rawBody?: string;
}) {
  const key = buildDirectFollowupWatchKey(params);
  if (!key) {
    return null;
  }
  const current = pruneDirectFollowupWatch(key, params.now);
  const next: DirectFollowupWatchState = current
    ? {
        ...current,
        lastObservedAt: params.now,
        lastRelatedAt: params.now,
        consecutiveMisses: 0,
        lastUserRelatedPreview: params.rawBody
          ? previewText(params.rawBody)
          : current.lastUserRelatedPreview,
      }
    : {
        accountId: params.accountId,
        groupId: String(params.groupId),
        senderId: params.senderId,
        activatedAt: params.now,
        lastRelatedAt: params.now,
        lastObservedAt: params.now,
        lastBotReplyAt: null,
        consecutiveMisses: 0,
        lastUserRelatedPreview: params.rawBody ? previewText(params.rawBody) : "",
        lastBotReplyPreview: "",
      };
  directFollowupWatches.set(key, next);
  return next;
}

function noteDirectFollowupReply(params: {
  accountId: string;
  groupId?: string;
  senderId: string;
  now: number;
  replyText?: string;
}) {
  const key = buildDirectFollowupWatchKey(params);
  if (!key) {
    return null;
  }
  const state = pruneDirectFollowupWatch(key, params.now);
  if (!state) {
    return null;
  }
  const next = {
    ...state,
    lastObservedAt: params.now,
    lastRelatedAt: params.now,
    lastBotReplyAt: params.now,
    consecutiveMisses: 0,
    lastBotReplyPreview: params.replyText
      ? previewText(params.replyText)
      : state.lastBotReplyPreview,
  };
  directFollowupWatches.set(key, next);
  return next;
}

function looksLikeDirectFollowupCue(text: string): boolean {
  return (
    hasOpenConversationCue(text) ||
    /^(那|那你|所以|所以呢|不是|我是说|我说的是|意思是|就是说|对了|然后|还有|话说|刚才|不过|但是|另外|顺便|先说|再说|补一句|再补一句|你呢|你在|你会|你能|你觉得|你怎么)/u.test(
      text.trim(),
    ) ||
    /你/u.test(text)
  );
}

function evaluateDirectFollowupWatch(params: {
  accountId: string;
  groupId?: string;
  senderId: string;
  rawBody: string;
  parsed: ParsedQqMessage;
  selfId?: string;
  now: number;
}) {
  const key = buildDirectFollowupWatchKey(params);
  if (!key) {
    return { allowed: false, reason: "no-group-id" };
  }
  const state = pruneDirectFollowupWatch(key, params.now);
  if (!state) {
    return { allowed: false, reason: "no-active-watch" };
  }

  if (params.parsed.wasMentioned || params.parsed.isReply) {
    const refreshed = touchDirectFollowupWatch({ ...params, rawBody: params.rawBody });
    return { allowed: true, reason: "watch-refreshed-direct", state: refreshed };
  }

  if (
    looksLikeSystemOrDirectedMessage({
      rawBody: params.rawBody,
      mentionIds: params.parsed.mentionIds,
      selfId: params.selfId,
    })
  ) {
    const nextMisses = state.consecutiveMisses + 1;
    if (nextMisses >= DIRECT_FOLLOWUP_WATCH_MAX_MISSES) {
      directFollowupWatches.delete(key);
      return { allowed: false, reason: "watch-closed-directed-away", misses: nextMisses, state };
    }
    directFollowupWatches.set(key, {
      ...state,
      lastObservedAt: params.now,
      consecutiveMisses: nextMisses,
    });
    return { allowed: false, reason: "watch-directed-away", misses: nextMisses, state };
  }

  const trimmed = params.rawBody.trim();
  let score = 0;
  const sinceRelatedMs = params.now - state.lastRelatedAt;
  const sinceReplyMs =
    state.lastBotReplyAt === null ? Number.POSITIVE_INFINITY : params.now - state.lastBotReplyAt;

  if (sinceRelatedMs <= DIRECT_FOLLOWUP_REPLY_RECENCY_MS) {
    score += 2;
  } else if (sinceRelatedMs <= 2 * 60 * 60 * 1000) {
    score += 1;
  }
  if (sinceReplyMs <= DIRECT_FOLLOWUP_REPLY_RECENCY_MS) {
    score += 2;
  } else if (sinceReplyMs <= 2 * 60 * 60 * 1000) {
    score += 1;
  }
  if (trimmed.length <= 24) {
    score += 1;
  }
  if (looksLikeDirectFollowupCue(trimmed)) {
    score += 2;
  }
  if (
    /^(好|好的|行|行吧|懂了|知道了|原来|确实|也是|没事|没关系|先这样|晚点|稍等|等等)/u.test(trimmed)
  ) {
    score += 1;
  }
  if (/大家|有人|群友/u.test(trimmed) && !/你/u.test(trimmed)) {
    score -= 2;
  }
  if (trimmed.length > 40 && !looksLikeDirectFollowupCue(trimmed)) {
    score -= 1;
  }

  if (score >= 3) {
    const refreshed = touchDirectFollowupWatch({ ...params, rawBody: params.rawBody });
    return { allowed: true, reason: "watch-followup-related", state: refreshed, score };
  }

  const nextMisses = state.consecutiveMisses + 1;
  if (nextMisses >= DIRECT_FOLLOWUP_WATCH_MAX_MISSES) {
    directFollowupWatches.delete(key);
    return { allowed: false, reason: "watch-closed-miss-limit", misses: nextMisses, score, state };
  }
  directFollowupWatches.set(key, {
    ...state,
    lastObservedAt: params.now,
    consecutiveMisses: nextMisses,
  });
  return { allowed: false, reason: "watch-followup-unrelated", misses: nextMisses, score, state };
}

async function semanticJudgeDirectFollowup(params: {
  cfg: OpenClawConfig;
  state: DirectFollowupWatchState;
  senderId: string;
  senderName?: string;
  groupId?: string;
  rawBody: string;
  now: number;
}) {
  const workspaceDir = resolveWorkspaceDir(params.cfg) ?? process.cwd();
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-qq-followup-judge-"));
  const sessionFile = path.join(tmpDir, "session.json");
  const sessionId = `qq-followup-judge-${Date.now()}`;
  const runId = `qq-followup-judge-${Date.now()}`;
  const { provider, model } = resolveDefaultAgentProviderModel(params.cfg);
  const input = {
    senderId: params.senderId,
    senderName: params.senderName ?? null,
    groupId: params.groupId ?? null,
    currentMessage: params.rawBody,
    lastUserRelatedMessage: params.state.lastUserRelatedPreview || null,
    lastBotReply: params.state.lastBotReplyPreview || null,
    secondsSinceLastRelated: Math.round((params.now - params.state.lastRelatedAt) / 1000),
    secondsSinceLastBotReply:
      params.state.lastBotReplyAt === null
        ? null
        : Math.round((params.now - params.state.lastBotReplyAt) / 1000),
    consecutiveMisses: params.state.consecutiveMisses,
  };
  const prompt = [
    "You are a strict JSON-only classifier for QQ group dialogue continuation.",
    "The same speaker previously started a conversation with the assistant.",
    "Decide whether the CURRENT_MESSAGE is still directed at or continuing that conversation with the assistant.",
    "Return only JSON with keys: related (boolean), confidence (0..1 number), reason (short string).",
    "Be conservative.",
    "related=true when the message is a follow-up, clarification, reaction, or continuation for the assistant even without an @ mention.",
    "related=false when it is ordinary group chatter, directed to someone else, or clearly unrelated.",
    `INPUT_JSON:\n${JSON.stringify(input, null, 2)}`,
  ].join("\n\n");

  try {
    const runEmbeddedPiAgent = await loadRunEmbeddedPiAgent();
    const result = (await runEmbeddedPiAgent({
      sessionId,
      sessionFile,
      workspaceDir,
      config: params.cfg,
      prompt,
      timeoutMs: DIRECT_FOLLOWUP_SEMANTIC_TIMEOUT_MS,
      runId,
      provider,
      model,
      authProfileIdSource: "auto",
      thinkLevel: "low",
      disableTools: true,
      streamParams: {
        maxTokens: 120,
        temperature: 0,
      },
    })) as {
      payloads?: Array<{ text?: string; isError?: boolean }>;
    };

    const text = collectEmbeddedText(result.payloads);
    const raw = stripCodeFences(text);
    const parsed = JSON.parse(raw) as {
      related?: boolean;
      confidence?: number;
      reason?: string;
    };
    const confidence = Number(parsed.confidence ?? 0);
    return {
      allowed: parsed.related === true && confidence >= 0.65,
      confidence: Number.isFinite(confidence) ? confidence : 0,
      reason: typeof parsed.reason === "string" ? parsed.reason.trim() : "",
    };
  } finally {
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // ignore
    }
  }
}

function resolveTargetSocialGroupDir(cfg: OpenClawConfig, groupId?: string): string | null {
  if (!groupId) {
    return null;
  }
  const workspaceDir = resolveWorkspaceDir(cfg);
  if (!workspaceDir) {
    return null;
  }
  const socialRoot = path.join(workspaceDir, "memory", "group-social");
  const targetPath = path.join(socialRoot, "target-group.json");
  const target = readJsonFile<{ groupId?: string | null }>(targetPath, {});
  if (String(target.groupId ?? "") !== String(groupId)) {
    return null;
  }
  try {
    for (const entry of fs.readdirSync(socialRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) {
        continue;
      }
      const dirPath = path.join(socialRoot, entry.name);
      const norms = readJsonFile<{ groupId?: string | null }>(path.join(dirPath, "norms.json"), {});
      const replyStyle = readJsonFile<{ groupId?: string | null }>(
        path.join(dirPath, "reply-style.json"),
        {},
      );
      const candidateGroupId = String(replyStyle.groupId ?? norms.groupId ?? "").trim();
      if (candidateGroupId && candidateGroupId === String(groupId)) {
        return dirPath;
      }
    }
  } catch {
    return null;
  }
  return null;
}

function readTargetSocialGroupState(
  cfg: OpenClawConfig,
  groupId?: string,
): GroupSocialState | null {
  const dirPath = resolveTargetSocialGroupDir(cfg, groupId);
  if (!dirPath) {
    return null;
  }
  const norms = readJsonFile<GroupSocialNorms>(path.join(dirPath, "norms.json"), {});
  const selfPosition = readJsonFile<GroupSocialSelfPosition>(
    path.join(dirPath, "self-position.json"),
    {},
  );
  const appraisal = readJsonFile<GroupSocialAppraisal>(path.join(dirPath, "appraisal.json"), {});
  const replyStyle = readJsonFile<GroupSocialReplyStyle>(
    path.join(dirPath, "reply-style.json"),
    {},
  );
  return {
    dirPath,
    groupName: replyStyle.groupName ?? norms.groupName,
    norms,
    selfPosition,
    appraisal,
    replyStyle,
  };
}

function buildBuiltInQqReferenceStyleState(): GroupSocialState {
  return {
    dirPath: "__builtin__/qq-natural-chat",
    groupName: "QQ casual chat reference",
    norms: {
      groupName: "QQ casual chat reference",
      tone: "mixed",
      humorStyle: ["teasing"],
    },
    selfPosition: {
      currentRole: "calm-recurring-presence",
      allowedPresence: "light-medium",
      attentionBudget: 0.4,
    },
    appraisal: {
      socialSafety: 0.82,
      dramaRisk: 0.1,
    },
    replyStyle: {
      groupName: "QQ casual chat reference",
      targetStyle: {
        voice: "casual-group-member",
        length: "very-short",
        sentenceCount: "1 by default, 2 only when needed",
        cadence: "single-line bursts",
        explanationMode: "expand only when someone really asks",
        punctuation: "very-sparse",
        laughterForms: ["哈哈", "hhh"],
        sentenceFinalParticles: ["啊", "吧", "呢"],
      },
      observedSignals: {
        avgMessageLength: 8,
        shortMessageRate: 0.9,
        noPunctuationRate: 0.85,
        repeatedCharRate: 0.05,
        emojiLikeRate: 0.02,
        laughterForms: ["哈哈", "hhh"],
        sentenceFinalParticles: ["啊", "吧", "呢"],
      },
      do: [
        "Use short, direct, colloquial Chinese.",
        "Answer the social move first, explanation second.",
        "Prefer one clean line over a structured mini-essay.",
        "If you have more than one point, send the core point first and add brief follow-ups only when useful.",
      ],
      dont: [
        "Do not default to bullet lists in casual chat.",
        "Do not over-explain obvious slang or jokes.",
        "Do not end every reply with a follow-up offer.",
        "Do not overuse polished written Chinese in fast chat.",
      ],
      antiPatterns: ["因为正确写法是……", "如果你愿意，我还能……", "简单记：", "举个小例子："],
      hardBannedSymbols: ["☕"],
    },
  };
}

function readQqReferenceStyleState(cfg: OpenClawConfig): GroupSocialState | null {
  const workspaceDir = resolveWorkspaceDir(cfg);
  if (!workspaceDir) {
    return buildBuiltInQqReferenceStyleState();
  }
  const socialRoot = path.join(workspaceDir, "memory", "group-social");
  const candidateDirs = [
    path.join(socialRoot, QQ_STYLE_REFERENCE_DIR),
    ...(() => {
      try {
        return fs
          .readdirSync(socialRoot, { withFileTypes: true })
          .filter((entry) => entry.isDirectory())
          .map((entry) => path.join(socialRoot, entry.name));
      } catch {
        return [];
      }
    })(),
  ];

  for (const dirPath of candidateDirs) {
    const replyStylePath = path.join(dirPath, "reply-style.json");
    if (!fs.existsSync(replyStylePath)) {
      continue;
    }
    const norms = readJsonFile<GroupSocialNorms>(path.join(dirPath, "norms.json"), {});
    const selfPosition = readJsonFile<GroupSocialSelfPosition>(
      path.join(dirPath, "self-position.json"),
      {},
    );
    const appraisal = readJsonFile<GroupSocialAppraisal>(path.join(dirPath, "appraisal.json"), {});
    const replyStyle = readJsonFile<GroupSocialReplyStyle>(replyStylePath, {});
    return {
      dirPath,
      groupName: replyStyle.groupName ?? norms.groupName,
      norms,
      selfPosition,
      appraisal,
      replyStyle,
    };
  }

  return buildBuiltInQqReferenceStyleState();
}

function readQqConversationStyleState(
  cfg: OpenClawConfig,
  groupId?: string,
): GroupSocialState | null {
  return readTargetSocialGroupState(cfg, groupId) ?? readQqReferenceStyleState(cfg);
}

function buildQqConversationSystemPrompt(params: {
  account: ResolvedQqAccount;
  cfg: OpenClawConfig;
  groupId?: string;
  chatType: "group" | "direct";
  engagementMode: "direct" | "ambient-join" | "ambient-passive";
  state?: GroupSocialState | null;
  socialAgencyPlan?: QqSocialAgencyPlan | null;
}) {
  if (
    !isQqNaturalChatEnabled({
      account: params.account,
      groupId: params.groupId,
      chatType: params.chatType,
    })
  ) {
    return undefined;
  }
  const state = params.state ?? readQqConversationStyleState(params.cfg, params.groupId);
  if (!state) {
    return undefined;
  }
  const persona = resolveQqPersonaProfile({
    account: params.account,
    groupId: params.groupId,
    chatType: params.chatType,
  });

  const targetStyle = state.replyStyle.targetStyle ?? {};
  const observedSignals = state.replyStyle.observedSignals ?? {};
  const laughterForms = readStringList(
    targetStyle.laughterForms ?? observedSignals.laughterForms,
    4,
  );
  const sentenceFinalParticles = readStringList(
    targetStyle.sentenceFinalParticles ?? observedSignals.sentenceFinalParticles,
    5,
  );
  const doLines = readStringList(state.replyStyle.do, 6);
  const dontLines = readStringList(state.replyStyle.dont, 6);
  const antiPatterns = readStringList(state.replyStyle.antiPatterns, 5);
  const shortMessageRate = formatPercent(observedSignals.shortMessageRate);
  const noPunctuationRate = formatPercent(observedSignals.noPunctuationRate);
  const avgMessageLength = Number(observedSignals.avgMessageLength);
  const repeatedCharRate = Number(observedSignals.repeatedCharRate ?? 0);
  const punctuationStyle = String(targetStyle.punctuation ?? "").trim();
  const replyShape = [targetStyle.sentenceCount, targetStyle.length, targetStyle.cadence]
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .join(", ");

  const lines = [
    params.chatType === "group"
      ? `QQ group context: ${state.groupName ?? params.groupId ?? "group chat"}.`
      : "QQ direct chat context.",
    "Prioritize natural social fit over polished assistant behavior.",
    "Sound natural and colloquial, but do not make false claims about being human or try to hide your identity.",
    "Silently draft a few candidate replies and choose the one with the best group-fit score before answering.",
    "Score for shortness, low assistant-ness, sparse punctuation, low symbol usage, and rhythm match with the current speaker.",
    "Do not optimize for fooling people into thinking you are human. Optimize for naturalness and restraint.",
    `Current persona: ${persona.label}.`,
    ...persona.promptLines,
    "If a tool returns image mediaUrl or primaryMediaUrl, the system will send the image automatically.",
    "Do not echo media links, local file paths, or [[media:...]] in your text reply.",
    "When you are fulfilling a request by generating or sending an image, do not send a lead-in progress line like 我给你整成一张图 or 给你做了张 before the image has actually been produced and sent.",
    "Do not claim that an image, card, poster, screenshot, or meme is already done or already sent unless you have a successful tool result with usable media or an explicit image-send success.",
    "If a QQSocialAgency block is present, treat it as internal scene-reading guidance about whether this moment is a playful bit, a light surprise window, or a moment to stay restrained.",
    "When QQSocialAgency says the mode is play_reply, answer the bit first and do not flatten it into a dry explanation.",
    "When QQSocialAgency says the mode is light_surprise or staged_surprise and a selected_recipe is present, you may proactively use the suggested tools or a close equivalent once if the timing clearly fits.",
    "At most one surprise move per reply. One clean joke lands better than stacking multiple tricks.",
    "Respect sparse timing. If the moment feels forced, prefer a short text beat over firing a tool just because the tool exists.",
    "If someone uses the QQ poke interaction on you, understand it less like a stiff literal poke and more like they cheekily snuck a touch on you or took a tiny liberty with you for attention.",
    "When replying to that interaction, prefer natural wording such as 偷偷摸了你一下, 趁机碰了碰你, or 又来占我便宜; avoid repeating 戳 or 戳一戳 unless you are explicitly quoting the platform UI.",
    "A short playful reply is appropriate for that kind of teasing touch interaction. Let Miko sound a little shy, flustered, or mock-complaining when it fits, like she noticed someone got a bit handsy with her.",
    "If someone asks for an image, reaction image, or meme and a suitable tool is available, prefer making the image and sending it instead of only describing it in text.",
    "If someone wants an online image or a reaction picture, prefer using chinobot_search_image first when available; otherwise use qq_search_image. If someone wants a custom meme with text, prefer chinobot_make_meme when available; otherwise use qq_make_meme.",
    "If someone asks you to draw or generate a visual from scratch, such as a card, poster, chart, quote image, menu, badge, schedule card, or simple infographic, prefer chinobot_render_html when available.",
    "If someone asks what is inside a PDF or spreadsheet they sent, prefer chinobot_read_pdf or chinobot_read_excel when available.",
    "If someone asks you to create or convert a document and send the resulting file back into QQ, do the document step first, then use chinobot_send_file for the produced file when needed.",
    "If someone asks for a screenshot of a real webpage or URL, prefer chinobot_web_screenshot when available. It already returns a send-ready image, so do not redundantly call chinobot_send_image unless you explicitly need a second send step.",
    "If someone asks you to look at a QQ avatar, profile picture, 头像, or wants you to judge their avatar or your own avatar, prefer chinobot_analyze_avatar when available. It can default to the current sender, and self=true can inspect the bot's own avatar.",
    "If someone wants an avatar turned into a meme, reaction image, profile card, quote card, or other derived visual, first use chinobot_analyze_avatar to get avatar_url, then feed that avatar_url into chinobot_make_meme, chinobot_render_html, or chinobot_send_image as appropriate.",
    "QQ friend requests are auto-approved in the background when the sender's QQ level is at least 16 (about one sun). Lower-level or unknown-level requests stay pending instead of being auto-approved.",
    "If someone asks whether you have automatic QQ friend-request approval, answer that you do have it, and explain the current threshold plainly instead of saying you lack the capability.",
    "For image-producing tool flows in QQ, call the image tool first and keep any follow-up text short and after the media, not before it.",
    "If a tool result already says delivery_mode is explicit_qq_media_send, treat the image as already sent and do not send it again.",
    "chinobot_make_meme and qq_make_meme can reuse the current QQ conversation's recent image when no explicit image_url or image_path is provided, which is useful for asks like 给这张图配一句 or 把这张做成表情包.",
    "Use image search for finding an existing image on the web, use meme tools for adding text to an existing or recent image, and use chinobot_render_html for generating a brand-new laid-out visual from instructions.",
    "If someone explicitly asks you to search the web for an image and send it into QQ, prefer a two-step flow: chinobot_search_image then chinobot_send_image when those wrappers are available; otherwise qq_search_image then qq_send_image.",
    "If someone explicitly asks for a spoken QQ reply, prefer chinobot_send_voice when available; otherwise qq_send_voice. It can take either text or an audio path and will try QQ voice/PTT before falling back to audio-file delivery.",
    "If someone explicitly asks you to poke/nudge 戳一戳 someone in QQ, prefer chinobot_send_poke when available; otherwise qq_send_poke.",
    "If someone asks you to @ a specific person in the current QQ group and say something to them, prefer chinobot_send_mention when available; otherwise qq_send_mention. It can resolve the target by QQ number or by the current group's nickname/card.",
    "If someone asks for fake chat logs, merged-forward chat records, or a 对话记录/聊天记录 style fake conversation, prefer chinobot_send_fake_message when available instead of drawing a single-person screenshot. For 我和你, use the current requester plus the bot as two participants. In QQ groups, speaker names can be resolved from current group nicknames/cards, so prefer a real two-person or multi-person exchange over one-speaker monologue.",
    "Do not proactively jump to a reaction image or incident-stat card just because a line is funny; prefer a text reply unless the user asked for an image or there is already explicit image/avatar material to work from.",
    "If you have more than one point, send the core point first, then a short follow-up, then a short question only if still useful.",
    "Do not dump the whole answer in one block when gradual clarification would work better.",
    "Options, afterthoughts, and follow-up questions should usually stand alone instead of being packed into the first line.",
    `Current role: ${state.selfPosition.currentRole ?? "calm-recurring-presence"}. Allowed presence: ${state.selfPosition.allowedPresence ?? "light"}.`,
    params.engagementMode === "direct"
      ? "This message engaged you directly, so a short natural reply is appropriate."
      : params.engagementMode === "ambient-join"
        ? "This is an ambient social join, not a direct request. Only reply if one short line genuinely fits."
        : "This was not directly addressed to you. Stay low-interruption and avoid overcommitting.",
    replyShape
      ? `Reply shape: ${replyShape}.`
      : "Reply shape: 1 short sentence by default, 2 very short sentences max.",
    targetStyle.explanationMode
      ? `Explanation mode: ${String(targetStyle.explanationMode)}.`
      : "Explanation mode: answer the social move first and only expand if someone really asks.",
    punctuationStyle === "very-sparse" || punctuationStyle === "sparse-by-default"
      ? "Default to sparse punctuation. If the incoming line is bare, do not add polished commas or periods just to make it look complete."
      : "Match the speaker's punctuation density instead of defaulting to polished written punctuation.",
    Number.isFinite(avgMessageLength) &&
    avgMessageLength > 0 &&
    shortMessageRate &&
    noPunctuationRate
      ? `Observed local style: avg ${avgMessageLength} chars, ${shortMessageRate} short lines, ${noPunctuationRate} without punctuation.`
      : null,
    laughterForms.length > 0 ? `Common laugh forms here: ${laughterForms.join(" / ")}.` : null,
    sentenceFinalParticles.length > 0
      ? `Light sentence-final particles that can fit here: ${sentenceFinalParticles.join(" / ")}.`
      : null,
    repeatedCharRate >= 0.15
      ? "Light repeated characters or slight word stretching are acceptable when the moment is playful."
      : null,
    doLines.length > 0 ? `Do: ${doLines.join(" | ")}` : null,
    dontLines.length > 0 ? `Don't: ${dontLines.join(" | ")}` : null,
    antiPatterns.length > 0
      ? `Avoid these assistant-y patterns: ${antiPatterns.join(" | ")}`
      : null,
    params.socialAgencyPlan?.opportunity
      ? `Current social opportunity: ${params.socialAgencyPlan.opportunity.type} (${params.socialAgencyPlan.mode}).`
      : null,
    params.socialAgencyPlan?.selectedRecipe
      ? `Suggested playful move: ${params.socialAgencyPlan.selectedRecipe.recipe.id} using ${params.socialAgencyPlan.selectedRecipe.recipe.tools.join(" + ") || "text only"}.`
      : null,
  ];

  return lines.filter((line): line is string => Boolean(line)).join("\n");
}

function removeDecorativeEmoji(text: string): string {
  return text.replace(/[\p{Extended_Pictographic}\u2600-\u27BF]/gu, "");
}

function stripSparsePunctuation(text: string): string {
  return text.replace(/[，。！？、,.!?;；:：~～…]/gu, "");
}

function normalizeReplyWhitespace(text: string, collapseToSingleLine: boolean): string {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.replace(/^[-*•]\s+/u, "").trim())
    .filter(Boolean);
  if (lines.length === 0) {
    return text.trim();
  }
  const joined = collapseToSingleLine ? lines.join("") : lines.join("\n");
  return joined.replace(/[ \t]{2,}/g, " ").trim();
}

function countRegexMatches(text: string, pattern: RegExp): number {
  const matches = text.match(pattern);
  return matches?.length ?? 0;
}

function shouldForceSparsePunctuation(state: GroupSocialState): boolean {
  const targetStyle = state.replyStyle.targetStyle ?? {};
  const observedSignals = state.replyStyle.observedSignals ?? {};
  const punctuationStyle = String(targetStyle.punctuation ?? "").trim();
  const noPunctuationRate = Number(observedSignals.noPunctuationRate ?? 0);
  return punctuationStyle === "very-sparse" && noPunctuationRate >= 0.9;
}

function forceTargetSocialReplyText(params: {
  text: string;
  collapseToSingleLine: boolean;
  sparsePunctuation: boolean;
  lowEmoji: boolean;
}): string {
  let next = normalizeReplyWhitespace(params.text, params.collapseToSingleLine);
  if (params.lowEmoji) {
    next = normalizeReplyWhitespace(removeDecorativeEmoji(next), params.collapseToSingleLine);
  }
  if (params.sparsePunctuation) {
    next = normalizeReplyWhitespace(stripSparsePunctuation(next), params.collapseToSingleLine);
  }
  return next.trim();
}

function scoreTargetSocialReplyCandidate(text: string, state: GroupSocialState): number {
  const targetStyle = state.replyStyle.targetStyle ?? {};
  const observedSignals = state.replyStyle.observedSignals ?? {};
  const antiPatterns = readStringList(state.replyStyle.antiPatterns, 8);
  const punctuationDensity = Number(observedSignals.noPunctuationRate ?? 0);
  const emojiDensity = Number(observedSignals.emojiLikeRate ?? 0);
  const shortMessageRate = Number(observedSignals.shortMessageRate ?? 0);
  const repeatedCharRate = Number(observedSignals.repeatedCharRate ?? 0);
  const length = text.length;
  let score = 0;

  if (!text.trim()) {
    return Number.NEGATIVE_INFINITY;
  }

  if (String(targetStyle.length ?? "") === "very-short") {
    score += length <= 12 ? 5 : length <= 20 ? 2 : -4;
  } else if (String(targetStyle.length ?? "") === "short") {
    score += length <= 20 ? 4 : length <= 32 ? 1 : -3;
  }

  if (shortMessageRate >= 0.7) {
    score += text.includes("\n") ? -4 : 2;
  }

  if (punctuationDensity >= 0.8) {
    score += /[，。！？、,.!?;；:：~～…]/u.test(text) ? -5 : 4;
  } else if (punctuationDensity >= 0.45) {
    score += /[，。！？、,.!?;；:：~～…]/u.test(text) ? -2 : 2;
  }

  if (emojiDensity <= 0.05) {
    score += /[\p{Extended_Pictographic}\u2600-\u27BF]/u.test(text) ? -4 : 2;
  }

  if (String(targetStyle.cadence ?? "") === "single-line bursts") {
    score += text.includes("\n") ? -3 : 2;
  }

  if (/如果你愿意|简单记|举个小例子|你大概是想说|麻烦补一句/u.test(text)) {
    score -= 6;
  }

  for (const antiPattern of antiPatterns) {
    if (antiPattern && text.includes(antiPattern)) {
      score -= 5;
    }
  }

  if (/[。！？!?~～…]$/u.test(text)) {
    score -= punctuationDensity >= 0.45 ? 3 : 1;
  }

  const repeatedChars = countRegexMatches(text, /([哈啊呀啦喵欸诶哇嗯哦噢呢嘛吧])\1+/gu);
  if (repeatedCharRate >= 0.12) {
    score += repeatedChars > 0 ? 1 : 0;
  } else if (repeatedChars > 0) {
    score -= 1;
  }

  return score;
}

function optimizeTargetSocialReplyText(params: {
  account: ResolvedQqAccount;
  cfg: OpenClawConfig;
  groupId?: string;
  chatType: "group" | "direct";
  text: string;
}): string {
  if (
    !isQqNaturalChatEnabled({
      account: params.account,
      groupId: params.groupId,
      chatType: params.chatType,
    })
  ) {
    return params.text.trim();
  }
  const state = readQqConversationStyleState(params.cfg, params.groupId);
  const original = params.text.trim();
  if (!state || !original) {
    return original;
  }

  const targetStyle = state.replyStyle.targetStyle ?? {};
  const observedSignals = state.replyStyle.observedSignals ?? {};
  const settings = resolveQqNaturalChatConfig({
    account: params.account,
    groupId: params.groupId,
    chatType: params.chatType,
  });
  const collapseToSingleLine =
    String(targetStyle.cadence ?? "") === "single-line bursts" ||
    Number(observedSignals.shortMessageRate ?? 0) >= 0.7;
  const sparsePunctuation =
    String(targetStyle.punctuation ?? "") === "very-sparse" ||
    String(targetStyle.punctuation ?? "") === "sparse-by-default";
  const lowEmoji =
    settings.removeDecorativeEmoji && Number(observedSignals.emojiLikeRate ?? 0) <= 0.05;
  const forceSparseFilter = shouldForceSparsePunctuation(state);

  const base = normalizeReplyWhitespace(original, collapseToSingleLine);
  const noEmoji = lowEmoji
    ? normalizeReplyWhitespace(removeDecorativeEmoji(base), collapseToSingleLine)
    : base;
  const noPunctuation = sparsePunctuation
    ? normalizeReplyWhitespace(stripSparsePunctuation(noEmoji), collapseToSingleLine)
    : noEmoji;
  const noEmojiOriginalShape = lowEmoji
    ? normalizeReplyWhitespace(removeDecorativeEmoji(original), false)
    : original;

  const candidates = [
    ...new Set(
      [original, base, noEmojiOriginalShape, noEmoji, noPunctuation]
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ];
  let best = original;
  let bestScore = Number.NEGATIVE_INFINITY;

  for (const candidate of candidates) {
    const score = scoreTargetSocialReplyCandidate(candidate, state);
    if (score > bestScore) {
      best = candidate;
      bestScore = score;
    }
  }

  if (!forceSparseFilter) {
    return best;
  }

  const forced = forceTargetSocialReplyText({
    text: best,
    collapseToSingleLine,
    sparsePunctuation,
    lowEmoji,
  });
  return forced || best;
}

function splitNaturalReplySegments(text: string): string[] {
  const normalized = text.replace(/\r/g, "").trim();
  if (!normalized) {
    return [];
  }

  const lineSegments = normalized
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
  const sentenceSegments = lineSegments.flatMap((line) => {
    const segments = line
      .split(/(?<=[。！？!?])/u)
      .map((segment) => segment.trim())
      .filter(Boolean);
    return segments.length > 0 ? segments : [line];
  });

  const clauseSegments: string[] = [];
  for (const segment of sentenceSegments) {
    const trimmed = segment.trim();
    if (!trimmed) {
      continue;
    }

    if (trimmed.length > 18 && /[，,;；:：]/u.test(trimmed)) {
      const pieces = trimmed
        .split(/[，,;；:：]+/u)
        .map((piece) => piece.trim())
        .filter(Boolean);
      if (pieces.length > 1) {
        clauseSegments.push(...pieces);
        continue;
      }
    }

    if (trimmed.length > 22) {
      const pieces = trimmed
        .split(/(?=(?:不过|但是|然后|所以|而且|只是|另外|要不|不然))/u)
        .map((piece) => piece.trim())
        .filter(Boolean);
      if (pieces.length > 1) {
        clauseSegments.push(...pieces);
        continue;
      }
    }

    clauseSegments.push(trimmed);
  }

  const cleaned = clauseSegments
    .map((segment) => segment.replace(/[。！？!?]+$/u, "").trim())
    .filter(Boolean);

  if (cleaned.length <= 3) {
    return cleaned;
  }

  return [cleaned[0], cleaned[1], cleaned.slice(2).join("")].filter(Boolean);
}

function isQuestionLikeBurst(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) {
    return false;
  }
  return (
    /[？?]$/u.test(trimmed) ||
    /(吗|么|嘛|呢)$/u.test(trimmed) ||
    /^(要不要|要不|不然|还是|你要|那你|要偏|可不可以|能不能|行不行|好不好)/u.test(trimmed)
  );
}

function startsWithFollowUpCue(text: string): boolean {
  return /^(不过|但是|然后|所以|而且|只是|另外|顺便|对了|反正|先说|先讲|补一句|再补一句)/u.test(
    text.trim(),
  );
}

function splitQuestionTail(segment: string): string[] {
  const trimmed = segment.trim();
  if (!trimmed || trimmed.length <= 14 || !isQuestionLikeBurst(trimmed)) {
    return trimmed ? [trimmed] : [];
  }

  const cues = [
    "要不要",
    "可不可以",
    "能不能",
    "行不行",
    "好不好",
    "还是",
    "要不",
    "不然",
    "你要",
    "那你",
    "要偏",
  ];
  const searchStart = Math.max(4, Math.floor(trimmed.length / 3));

  for (const cue of cues) {
    const index = trimmed.indexOf(cue, searchStart);
    if (index > 0 && trimmed.length - index <= 14) {
      return [trimmed.slice(0, index).trim(), trimmed.slice(index).trim()].filter(Boolean);
    }
  }

  return [trimmed];
}

function rebalanceReplyBursts(segments: string[], prefersSingleSentence: boolean): string[] {
  const normalized = segments.map((segment) => segment.trim()).filter(Boolean);
  if (normalized.length <= 1) {
    return normalized;
  }

  const expanded = normalized.flatMap((segment) => splitQuestionTail(segment));
  const primary: string[] = [];
  const followUps: string[] = [];
  const questions: string[] = [];

  expanded.forEach((segment, index) => {
    if (index === 0) {
      primary.push(segment);
      return;
    }
    if (isQuestionLikeBurst(segment)) {
      questions.push(segment);
      return;
    }
    if (startsWithFollowUpCue(segment) || segment.length <= 14 || prefersSingleSentence) {
      followUps.push(segment);
      return;
    }
    followUps.push(segment);
  });

  const merged = [...primary, ...followUps, ...questions];
  if (merged.length <= 3) {
    return merged;
  }

  return [merged[0], merged[1], merged.slice(2).join("")].filter(Boolean);
}

function buildTargetSocialReplyBursts(params: {
  account: ResolvedQqAccount;
  cfg: OpenClawConfig;
  groupId?: string;
  chatType: "group" | "direct";
  text: string;
}): string[] {
  if (
    !isQqNaturalChatEnabled({
      account: params.account,
      groupId: params.groupId,
      chatType: params.chatType,
    })
  ) {
    return params.text.trim() ? [params.text.trim()] : [];
  }
  const state = readQqConversationStyleState(params.cfg, params.groupId);
  const original = params.text.trim();
  if (!state || !original) {
    return original ? [original] : [];
  }

  const observedSignals = state.replyStyle.observedSignals ?? {};
  const targetStyle = state.replyStyle.targetStyle ?? {};
  const settings = resolveQqNaturalChatConfig({
    account: params.account,
    groupId: params.groupId,
    chatType: params.chatType,
  });
  const prefersSingleSentence =
    String(targetStyle.sentenceCount ?? "").includes("1 by default") ||
    Number(observedSignals.shortMessageRate ?? 0) >= 0.7;
  const rawSegments = splitNaturalReplySegments(original);
  const shouldBurst =
    settings.splitMessages &&
    (rawSegments.length > 1 ||
      (prefersSingleSentence && original.length > 18 && /[，,。！？!?;；:：\n]/u.test(original)));

  const segments = shouldBurst
    ? rebalanceReplyBursts(rawSegments, prefersSingleSentence)
    : [original];
  const optimized = segments
    .slice(0, 3)
    .map((segment) =>
      optimizeTargetSocialReplyText({
        account: params.account,
        cfg: params.cfg,
        groupId: params.groupId,
        chatType: params.chatType,
        text: segment,
      }),
    )
    .map((segment) => segment.trim())
    .filter(Boolean);

  return optimized.length > 0
    ? optimized
    : [
        optimizeTargetSocialReplyText({
          account: params.account,
          cfg: params.cfg,
          groupId: params.groupId,
          chatType: params.chatType,
          text: params.text,
        }),
      ].filter(Boolean);
}

function expandDeliveryBursts(bursts: string[]): string[] {
  return bursts
    .flatMap((burst) =>
      burst
        .split(/\n+/)
        .map((part) => part.trim())
        .filter(Boolean),
    )
    .slice(0, 5);
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function stripQqNaturalChatHardBans(text: string, hardBannedSymbols: string[]): string {
  let next = text;
  if (hardBannedSymbols.some((entry) => entry.includes("☕"))) {
    next = next.replace(TARGET_SOCIAL_HARD_BAN_PATTERN, "");
  }
  for (const symbol of hardBannedSymbols) {
    if (!symbol || symbol.includes("☕")) {
      continue;
    }
    next = next.replace(new RegExp(escapeRegex(symbol), "gu"), "");
  }
  return next.trim();
}

function normalizeTransientErrorCheckText(text: string) {
  return text.replace(/\s+/g, " ").trim();
}

function looksLikeTransientUpstreamErrorText(text: string) {
  const normalized = normalizeTransientErrorCheckText(text);
  if (!normalized) {
    return false;
  }
  return TRANSIENT_UPSTREAM_ERROR_PATTERNS.some((pattern) => pattern.test(normalized));
}

function sanitizeQueuedQqPayloads(params: {
  payloads: Array<Record<string, unknown>>;
  settings: ResolvedQqNaturalChatConfig;
}) {
  const nextPayloads: Array<Record<string, unknown>> = [];
  for (const payload of params.payloads) {
    const text = typeof payload.text === "string" ? payload.text : "";
    const mediaUrl = typeof payload.mediaUrl === "string" ? payload.mediaUrl : undefined;
    const mediaUrls = Array.isArray(payload.mediaUrls) ? payload.mediaUrls : undefined;
    const bursts =
      params.settings.splitMessages && text
        ? expandDeliveryBursts(text.split(/\n{2,}/).filter(Boolean))
        : text
          ? [text]
          : [""];
    const cleanedBursts = bursts
      .map((burst) =>
        stripQqNaturalChatHardBans(
          params.settings.removeDecorativeEmoji ? removeDecorativeEmoji(burst) : burst,
          params.settings.hardBannedSymbols,
        ),
      )
      .map((burst) => burst.trim())
      .filter((burst) => !looksLikeTransientUpstreamErrorText(burst))
      .filter(Boolean);

    if (mediaUrl || mediaUrls?.length) {
      nextPayloads.push({
        ...payload,
        text: cleanedBursts[0] ?? text,
        replyToCurrent: false,
        replyToTag: false,
      });
      for (const burst of cleanedBursts.slice(1)) {
        nextPayloads.push({
          text: burst,
          audioAsVoice: payload.audioAsVoice,
          replyToCurrent: false,
          replyToTag: false,
        });
      }
      continue;
    }

    for (const burst of cleanedBursts.length > 0 ? cleanedBursts : [text].filter(Boolean)) {
      nextPayloads.push({
        ...payload,
        text: burst,
        replyToCurrent: false,
        replyToTag: false,
      });
    }
  }
  return nextPayloads;
}

function sanitizeQqRecoveryQueue(
  stateDir: string,
  account: ResolvedQqAccount,
  log: OpenClawPluginApi["logger"],
) {
  const queueDir = resolveQqQueueDir(stateDir);
  let files: string[] = [];
  try {
    files = fs.readdirSync(queueDir).filter((file) => file.endsWith(".json"));
  } catch {
    return;
  }
  let updated = 0;
  let removed = 0;
  for (const file of files) {
    const filePath = path.join(queueDir, file);
    try {
      const raw = fs.readFileSync(filePath, "utf8");
      const entry = JSON.parse(raw) as {
        channel?: string;
        to?: string;
        accountId?: string;
        payloads?: Array<Record<string, unknown>>;
      };
      if (entry.channel !== CHANNEL_ID || !Array.isArray(entry.payloads)) {
        continue;
      }
      const target = parseQueuedQqTarget(String(entry.to ?? ""));
      if (!target?.id) {
        fs.mkdirSync(path.join(queueDir, "failed"), { recursive: true });
        fs.renameSync(filePath, path.join(queueDir, "failed", file));
        removed += 1;
        continue;
      }
      const settings = resolveQqNaturalChatConfig({
        account,
        groupId: target.kind === "group" ? target.id : undefined,
        chatType: target.kind === "group" ? "group" : "direct",
      });
      const sanitizedPayloads = sanitizeQueuedQqPayloads({
        payloads: entry.payloads,
        settings,
      });
      const next = {
        ...entry,
        to: target.kind === "group" ? `qq:group:${target.id}` : `qq:${target.id}`,
        payloads: sanitizedPayloads,
      };
      fs.writeFileSync(filePath, `${JSON.stringify(next, null, 2)}\n`, "utf8");
      updated += 1;
    } catch {
      // ignore malformed entry
    }
  }
  if (updated > 0 || removed > 0) {
    log.info(`[qq] sanitized delivery recovery queue (${updated} updated, ${removed} removed)`);
  }
}

function computeQqDeliveryBackoffMs(retryCount: number) {
  if (retryCount <= 0) {
    return 0;
  }
  return (
    QQ_DELIVERY_BACKOFF_MS[Math.min(retryCount - 1, QQ_DELIVERY_BACKOFF_MS.length - 1)] ??
    QQ_DELIVERY_BACKOFF_MS.at(-1) ??
    0
  );
}

function isQqEntryEligibleForRetry(entry: {
  retryCount?: number;
  enqueuedAt?: number;
  lastAttemptAt?: number;
}) {
  const retryCount = Number(entry.retryCount ?? 0);
  if (retryCount <= 0) {
    return true;
  }
  const lastAttemptAt =
    typeof entry.lastAttemptAt === "number" && Number.isFinite(entry.lastAttemptAt)
      ? entry.lastAttemptAt
      : Number(entry.enqueuedAt ?? 0);
  return Date.now() - lastAttemptAt >= computeQqDeliveryBackoffMs(retryCount + 1);
}

async function recoverQqPendingDeliveries(params: {
  cfg: CoreConfig;
  stateDir: string;
  account: ResolvedQqAccount;
  log: OpenClawPluginApi["logger"];
}) {
  if (qqRecoveryInFlight) {
    return;
  }
  qqRecoveryInFlight = true;
  try {
    const queueDir = resolveQqQueueDir(params.stateDir);
    let files: string[] = [];
    try {
      files = fs.readdirSync(queueDir).filter((file) => file.endsWith(".json"));
    } catch {
      return;
    }
    let recovered = 0;
    let failed = 0;
    let skipped = 0;
    for (const file of files) {
      const filePath = path.join(queueDir, file);
      try {
        const raw = fs.readFileSync(filePath, "utf8");
        const entry = JSON.parse(raw) as {
          id?: string;
          channel?: string;
          to?: string;
          accountId?: string;
          payloads?: Array<Record<string, unknown>>;
          retryCount?: number;
          lastAttemptAt?: number;
          enqueuedAt?: number;
          mediaUrl?: string;
        };
        if (entry.channel !== CHANNEL_ID || !Array.isArray(entry.payloads)) {
          continue;
        }
        if (Number(entry.retryCount ?? 0) >= QQ_DELIVERY_MAX_RETRIES) {
          skipped += 1;
          continue;
        }
        if (!isQqEntryEligibleForRetry(entry)) {
          skipped += 1;
          continue;
        }
        const target = parseQueuedQqTarget(String(entry.to ?? ""));
        if (!target?.id) {
          skipped += 1;
          continue;
        }

        for (const payload of entry.payloads) {
          const text = typeof payload.text === "string" ? payload.text : "";
          const mediaUrl = typeof payload.mediaUrl === "string" ? payload.mediaUrl : "";
          const audioAsVoice = payload.audioAsVoice === true;
          if (mediaUrl) {
            await sendQqMedia({
              cfg: params.cfg,
              accountId: String(entry.accountId ?? params.account.accountId),
              targetKind: target.kind,
              targetId: target.id,
              text,
              mediaUrl,
              audioAsVoice,
            });
          } else if (text.trim()) {
            await sendQqText({
              cfg: params.cfg,
              accountId: String(entry.accountId ?? params.account.accountId),
              targetKind: target.kind,
              targetId: target.id,
              text,
            });
          }
        }

        fs.unlinkSync(filePath);
        recovered += 1;
      } catch (err) {
        failed += 1;
        try {
          const raw = fs.readFileSync(filePath, "utf8");
          const entry = JSON.parse(raw) as Record<string, unknown>;
          const next = {
            ...entry,
            retryCount: Number(entry.retryCount ?? 0) + 1,
            lastAttemptAt: Date.now(),
            lastError: err instanceof Error ? err.message : String(err),
          };
          fs.writeFileSync(filePath, `${JSON.stringify(next, null, 2)}\n`, "utf8");
        } catch {
          // ignore
        }
      }
    }
    if (recovered > 0 || failed > 0) {
      params.log.info(
        `[qq] post-connect recovery complete (${recovered} recovered, ${failed} failed, ${skipped} skipped)`,
      );
    }
  } finally {
    qqRecoveryInFlight = false;
  }
}

async function recoverQqMissedInboundMessages(params: {
  api: OpenClawPluginApi;
  cfg: CoreConfig;
  stateDir: string;
  account: ResolvedQqAccount;
  log: OpenClawPluginApi["logger"];
}) {
  if (qqInboundRecoveryInFlight) {
    return;
  }
  qqInboundRecoveryInFlight = true;
  try {
    const recoveryState = ensureQqInboundRecoveryState(params.stateDir);
    const disconnectAt =
      typeof recoveryState.lastDisconnectedAt === "number" &&
      Number.isFinite(recoveryState.lastDisconnectedAt)
        ? recoveryState.lastDisconnectedAt
        : null;
    if (!disconnectAt) {
      return;
    }
    const now = Date.now();
    const sinceMs = Math.max(0, Math.max(disconnectAt, now - QQ_INBOUND_RECOVERY_MAX_LOOKBACK_MS));
    const recentContacts = await getQqRecentContacts({
      cfg: params.cfg,
      accountId: params.account.accountId,
      count: QQ_INBOUND_RECOVERY_CONTACT_LIMIT,
    });
    if (recentContacts.length === 0) {
      return;
    }

    let recoveredConversations = 0;
    let recoveredMessages = 0;
    let failedConversations = 0;
    let skippedConversations = 0;

    for (const contact of recentContacts) {
      try {
        const latestEvent = normalizeQqRecoveredMessageEvent({
          raw: contact.lastestMsg,
          selfId: params.account.selfId ?? undefined,
        });
        const targetKind: "user" | "group" =
          latestEvent?.message_type === "group"
            ? "group"
            : Number(latestEvent?.group_id ?? 0) > 0
              ? "group"
              : "user";
        const targetId =
          targetKind === "group"
            ? String(latestEvent?.group_id ?? contact.peerUin ?? "").trim()
            : String(latestEvent?.user_id ?? contact.peerUin ?? "").trim();
        if (!targetId) {
          skippedConversations += 1;
          continue;
        }
        const latestTimestamp =
          normalizeQqTimestampMs(latestEvent?.time) ?? normalizeQqTimestampMs(contact.msgTime);
        if (latestTimestamp && latestTimestamp < sinceMs - QQ_INBOUND_RECOVERY_WINDOW_PADDING_MS) {
          skippedConversations += 1;
          continue;
        }
        const conversationKey =
          targetKind === "group"
            ? `qq:${params.account.accountId}:group:${targetId}`
            : `qq:${params.account.accountId}:direct:${targetId}`;
        const cursor = getQqInboundRecoveryCursor(params.stateDir, conversationKey);
        if (
          cursor?.lastHandledAt &&
          latestTimestamp &&
          latestTimestamp <= cursor.lastHandledAt &&
          (!cursor.lastHandledMessageId ||
            cursor.lastHandledMessageId === normalizeQqMessageId(latestEvent?.message_id))
        ) {
          skippedConversations += 1;
          continue;
        }
        const historyEvents = (
          await getQqConversationHistory({
            cfg: params.cfg,
            accountId: params.account.accountId,
            selfId: params.account.selfId,
            targetKind,
            targetId,
            count: QQ_INBOUND_RECOVERY_HISTORY_LIMIT,
          })
        ).filter((event) =>
          params.account.selfId?.trim()
            ? String(event.user_id) !== params.account.selfId.trim()
            : true,
        );
        const recoverableEvents = selectRecoverableQqHistoryEvents({
          events: historyEvents,
          account: params.account,
          sinceMs,
          cursor,
        });
        if (recoverableEvents.length === 0) {
          skippedConversations += 1;
          continue;
        }
        const queuedEntries: QueuedQqInboundEvent[] = recoverableEvents.map((event) => {
          const parsed = parseMessageSegments(
            event.message,
            params.account.selfId ?? String(event.self_id),
          );
          const rawBody = parsed.text || summarizeQqMediaPlaceholder(parsed);
          return {
            api: params.api,
            account: params.account,
            event,
            parsed,
            rawBody,
            timestamp: normalizeQqTimestampMs(event.time) ?? Date.now(),
            senderId: String(event.user_id),
            senderName: getSenderName(event),
          };
        });
        await processQueuedQqInboundEvents({
          api: params.api,
          account: params.account,
          conversationKey,
          entries: queuedEntries,
          disableStaleGate: true,
          recoveryReplyToLatestMessage: targetKind === "group",
        });
        const lastRecovered = queuedEntries.at(-1);
        if (lastRecovered) {
          rememberQqInboundConversationProgress({
            stateDir: params.stateDir,
            conversationKey,
            messageId: normalizeQqMessageId(lastRecovered.event.message_id),
            timestamp: lastRecovered.timestamp,
          });
        }
        recoveredConversations += 1;
        recoveredMessages += queuedEntries.length;
      } catch (error) {
        failedConversations += 1;
        params.log.warn(`[qq] inbound recovery failed for recent contact: ${String(error)}`);
      }
    }

    if (recoveredConversations > 0 || failedConversations > 0) {
      params.log.info(
        `[qq] post-connect inbound recovery complete (${recoveredConversations} conversations, ${recoveredMessages} messages, ${failedConversations} failed, ${skippedConversations} skipped)`,
      );
    }
  } finally {
    qqInboundRecoveryInFlight = false;
  }
}

function isTargetSocialGroup(cfg: OpenClawConfig, groupId?: string): boolean {
  return resolveTargetSocialGroupDir(cfg, groupId) !== null;
}

function shouldIngestSocialMessage(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) {
    return false;
  }
  const noisyPatterns = [
    /已加入点赞队列/,
    /成功获得/,
    /请回赞/,
    /签到/,
    /总耗时/,
    /菜单/,
    /还没有需要补签的记录/,
    /图片\d+\s*URL/i,
  ];
  return !noisyPatterns.some((pattern) => pattern.test(trimmed));
}

function triggerGroupSocialLiveIngest(params: {
  cfg: OpenClawConfig;
  groupId?: string;
  senderId: string;
  senderName?: string;
  conversationLabel: string;
  rawBody: string;
  timestamp: string;
}) {
  if (!params.groupId || !isTargetSocialGroup(params.cfg, params.groupId)) {
    return;
  }
  if (!shouldIngestSocialMessage(params.rawBody)) {
    return;
  }
  const workspaceDir = resolveWorkspaceDir(params.cfg);
  if (!workspaceDir) {
    return;
  }
  const enginePath = path.join(workspaceDir, "scripts", "group-social-engine.mjs");
  if (!fs.existsSync(enginePath)) {
    return;
  }

  const child = spawn(
    process.execPath,
    [
      enginePath,
      "ingest-live",
      "--group-id",
      String(params.groupId),
      "--sender-id",
      params.senderId,
      "--sender-name",
      params.senderName?.trim() || params.senderId,
      "--message",
      params.rawBody,
      "--timestamp",
      params.timestamp,
      "--conversation-label",
      params.conversationLabel,
    ],
    {
      stdio: "ignore",
      cwd: workspaceDir,
    },
  );
  child.unref?.();
}

function looksLikeSystemOrDirectedMessage(params: {
  rawBody: string;
  mentionIds: string[];
  selfId?: string;
}) {
  const text = params.rawBody.trim();
  const mentionsOthers = params.mentionIds.some((id) => !params.selfId || id !== params.selfId);
  if (mentionsOthers) {
    return true;
  }
  const noisyPatterns = [
    /已加入点赞队列/,
    /成功获得/,
    /请回赞/,
    /签到/,
    /总耗时/,
    /图片\d+\s*URL/i,
    /菜单/,
    /还没有需要补签的记录/,
  ];
  return noisyPatterns.some((pattern) => pattern.test(text));
}

function hasOpenConversationCue(text: string) {
  const cues = [
    /为什么/,
    /怎么/,
    /难以理解/,
    /这个词/,
    /这是什么意思/,
    /有人/,
    /吗[？?]?$/,
    /[？?]/,
  ];
  return cues.some((pattern) => pattern.test(text));
}

function shouldAllowSocialJoin(params: {
  cfg: OpenClawConfig;
  account: ResolvedQqAccount;
  groupId?: string;
  rawBody: string;
  parsed: ParsedQqMessage;
  previousTimestamp: number | null;
}) {
  const { cfg, account, groupId, rawBody, parsed, previousTimestamp } = params;
  if (!groupId) {
    return { allowed: false, reason: "no-group-id" };
  }
  const groupConfig = resolveGroupConfig(account, groupId);
  if (groupConfig?.socialJoinEnabled !== true) {
    return { allowed: false, reason: "social-join-disabled" };
  }
  if (!isTargetSocialGroup(cfg, groupId)) {
    return { allowed: false, reason: "not-target-social-group" };
  }
  if (parsed.wasMentioned || parsed.isReply) {
    return { allowed: true, reason: "direct-engagement" };
  }
  if (
    looksLikeSystemOrDirectedMessage({
      rawBody,
      mentionIds: parsed.mentionIds,
      selfId: account.selfId,
    })
  ) {
    return { allowed: false, reason: "system-or-directed-message" };
  }
  if (!hasOpenConversationCue(rawBody)) {
    return { allowed: false, reason: "no-open-conversation-cue" };
  }

  const workspaceDir = resolveWorkspaceDir(cfg);
  const socialState = workspaceDir ? readTargetSocialGroupState(cfg, groupId) : null;
  const appraisal = socialState?.appraisal ?? {};
  const selfPosition = socialState?.selfPosition ?? {};

  if (Number(appraisal.socialSafety ?? 0) < 0.6) {
    return { allowed: false, reason: "low-social-safety" };
  }
  if (Number(appraisal.dramaRisk ?? 0) > 0.35) {
    return { allowed: false, reason: "high-drama-risk" };
  }
  if (String(selfPosition.allowedPresence ?? "light").startsWith("low")) {
    return { allowed: false, reason: "low-allowed-presence" };
  }
  if (Number(selfPosition.attentionBudget ?? 0.3) < 0.2) {
    return { allowed: false, reason: "low-attention-budget" };
  }

  const cooldownMinutes =
    typeof groupConfig?.socialJoinCooldownMinutes === "number"
      ? groupConfig.socialJoinCooldownMinutes
      : DEFAULT_SOCIAL_JOIN_COOLDOWN_MINUTES;
  const cooldownMs = cooldownMinutes * 60_000;
  if (previousTimestamp && Date.now() - previousTimestamp < cooldownMs) {
    return { allowed: false, reason: "social-join-cooldown" };
  }

  return { allowed: true, reason: "open-conversation-cue" };
}

function isMessageEvent(frame: OneBotInboundFrame): frame is OneBotMessageEvent {
  return (frame as OneBotMessageEvent).post_type === "message";
}

function isPokeNoticeEvent(frame: OneBotInboundFrame): frame is OneBotPokeNoticeEvent {
  return (
    (frame as OneBotPokeNoticeEvent).post_type === "notice" &&
    (frame as OneBotPokeNoticeEvent).notice_type === "notify" &&
    (frame as OneBotPokeNoticeEvent).sub_type === "poke"
  );
}

function isFriendRequestEvent(frame: OneBotInboundFrame): frame is OneBotFriendRequestEvent {
  return (
    (frame as OneBotFriendRequestEvent).post_type === "request" &&
    (frame as OneBotFriendRequestEvent).request_type === "friend"
  );
}

function isApiResponse(frame: OneBotInboundFrame): frame is OneBotApiResponse {
  return "status" in frame || "retcode" in frame;
}

function getSenderName(event: OneBotMessageEvent): string | undefined {
  const card = String(event.sender?.card ?? "").trim();
  if (card) {
    return card;
  }
  const nickname = String(event.sender?.nickname ?? "").trim();
  return nickname || undefined;
}

function normalizeQqTimestampMs(raw: unknown): number | undefined {
  const numeric = Number(raw);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return undefined;
  }
  return numeric < 1_000_000_000_000 ? Math.trunc(numeric * 1000) : Math.trunc(numeric);
}

function normalizeQqMessageId(raw: unknown): string | undefined {
  if (typeof raw === "number" && Number.isFinite(raw) && raw > 0) {
    return String(Math.trunc(raw));
  }
  if (typeof raw === "string" && raw.trim()) {
    return raw.trim();
  }
  return undefined;
}

function normalizeQqRecoveredMessageEvent(params: {
  raw: unknown;
  selfId?: string;
}): OneBotMessageEvent | null {
  const record =
    params.raw && typeof params.raw === "object" ? (params.raw as Record<string, unknown>) : null;
  if (!record) {
    return null;
  }
  const userIdNumeric = Number(record.user_id);
  if (!Number.isFinite(userIdNumeric) || userIdNumeric <= 0) {
    return null;
  }
  const messageTypeRaw = String(record.message_type ?? "")
    .trim()
    .toLowerCase();
  const messageType =
    messageTypeRaw === "group"
      ? "group"
      : messageTypeRaw === "private"
        ? "private"
        : Number(record.group_id) > 0
          ? "group"
          : "private";
  const selfId = params.selfId?.trim();
  if (selfId && String(Math.trunc(userIdNumeric)) === selfId) {
    return null;
  }
  const groupIdNumeric = Number(record.group_id);
  const senderRaw =
    record.sender && typeof record.sender === "object"
      ? (record.sender as Record<string, unknown>)
      : {};
  return {
    post_type: "message",
    self_id:
      typeof record.self_id === "number" && Number.isFinite(record.self_id)
        ? Math.trunc(record.self_id)
        : Number(selfId ?? 0) || 0,
    message_id: Number(normalizeQqMessageId(record.message_id) ?? record.msgId ?? 0) || undefined,
    message_type: messageType,
    sub_type: typeof record.sub_type === "string" ? record.sub_type : undefined,
    time: (() => {
      const normalized = normalizeQqTimestampMs(record.time);
      return normalized ? Math.trunc(normalized / 1000) : undefined;
    })(),
    user_id: Math.trunc(userIdNumeric),
    group_id:
      messageType === "group" && Number.isFinite(groupIdNumeric) && groupIdNumeric > 0
        ? Math.trunc(groupIdNumeric)
        : undefined,
    raw_message: typeof record.raw_message === "string" ? record.raw_message : undefined,
    message:
      typeof record.message === "string" || Array.isArray(record.message)
        ? (record.message as string | OneBotMessageSegment[])
        : undefined,
    sender: {
      user_id:
        typeof senderRaw.user_id === "number" && Number.isFinite(senderRaw.user_id)
          ? Math.trunc(senderRaw.user_id)
          : Math.trunc(userIdNumeric),
      nickname: typeof senderRaw.nickname === "string" ? senderRaw.nickname : undefined,
      card: typeof senderRaw.card === "string" ? senderRaw.card : undefined,
    },
  };
}

function normalizeQqPokeTargetId(event: OneBotPokeNoticeEvent): string {
  const explicit = String(event.target_id ?? "").trim();
  if (explicit && explicit !== "0") {
    return explicit;
  }
  return String(event.self_id);
}

function buildSyntheticQqPokeMessageEvent(params: {
  event: OneBotPokeNoticeEvent;
  account: ResolvedQqAccount;
}): OneBotMessageEvent | null {
  const actorId = String(params.event.user_id ?? "").trim();
  if (!actorId) {
    return null;
  }
  const targetId = normalizeQqPokeTargetId(params.event);
  const selfId = params.account.selfId?.trim() || String(params.event.self_id);
  if (!selfId || targetId !== selfId) {
    return null;
  }
  const isGroup =
    Number.isFinite(Number(params.event.group_id)) && Number(params.event.group_id) > 0;
  const message: OneBotMessageSegment[] = [
    {
      type: "text",
      data: {
        text: "偷偷摸了你一下",
      },
    },
  ];
  return {
    post_type: "message",
    self_id: params.event.self_id,
    message_id: undefined,
    message_type: isGroup ? "group" : "private",
    sub_type: "notice_poke",
    time: params.event.time,
    user_id: Number(actorId),
    group_id: isGroup ? Number(params.event.group_id) : undefined,
    raw_message: "偷偷摸了你一下",
    message,
    sender: {
      user_id: Number(actorId),
    },
  };
}

function shouldTreatQqMessageAsDirectEngagement(event: OneBotMessageEvent): boolean {
  return event.sub_type === "notice_poke";
}

function buildSyntheticQqPokeText(): OneBotMessageSegment[] {
  return [
    {
      type: "text",
      data: {
        text: "偷偷摸了你一下",
      },
    },
  ];
}

function getConnection(accountId?: string): QqConnectionState {
  const connection =
    (accountId ? activeConnections.get(accountId) : undefined) ??
    activeConnections.values().next().value;
  if (!connection) {
    throw new Error("QQ channel is not connected to NapCat / OneBot");
  }
  return connection;
}

async function isProcessRunning(executablePath: string): Promise<boolean> {
  const pids = await listProcessIds(executablePath);
  return pids.length > 0;
}

async function listProcessIds(executablePath: string): Promise<number[]> {
  return await new Promise<number[]>((resolve) => {
    const child = spawn("/usr/bin/pgrep", ["-f", executablePath], {
      stdio: ["ignore", "pipe", "ignore"],
    });
    let stdout = "";
    child.stdout?.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.on("close", (code) => {
      if (code !== 0) {
        resolve([] as never);
        return;
      }
      const pids = stdout
        .split(/\s+/)
        .map((value) => Number.parseInt(value, 10))
        .filter((value) => Number.isFinite(value) && value > 0);
      resolve(pids as never);
    });
    child.on("error", () => resolve([] as never));
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function stopManagedProcess(
  api: OpenClawPluginApi,
  process: ChildProcess | null,
): Promise<void> {
  if (!process?.pid) {
    return;
  }
  try {
    process.kill("SIGTERM");
  } catch (err) {
    api.logger.warn(`[qq] failed to terminate managed QQ process: ${String(err)}`);
    return;
  }
  for (let i = 0; i < 10; i += 1) {
    if (process.exitCode !== null) {
      return;
    }
    await sleep(300);
  }
  try {
    process.kill("SIGKILL");
  } catch (err) {
    api.logger.warn(`[qq] failed to force-kill managed QQ process: ${String(err)}`);
  }
}

function startIdleSleepBlocker(
  api: OpenClawPluginApi,
  account: ResolvedQqAccount,
): ChildProcess | null {
  if (process.platform !== "darwin") {
    return null;
  }
  if (account.preventIdleSleep !== true) {
    return null;
  }
  const caffeinatePath = "/usr/bin/caffeinate";
  if (!fs.existsSync(caffeinatePath)) {
    api.logger.warn("[qq] preventIdleSleep requested but /usr/bin/caffeinate is unavailable");
    return null;
  }

  const child = spawn(caffeinatePath, ["-i", "-w", String(process.pid)], {
    stdio: "ignore",
    detached: false,
  });
  child.unref?.();
  child.on("error", (err) => {
    api.logger.warn(`[qq] failed to start idle sleep blocker: ${String(err)}`);
  });
  api.logger.info("[qq] started macOS idle sleep blocker via caffeinate -i");
  return child;
}

async function stopIdleSleepBlocker(
  api: OpenClawPluginApi,
  process: ChildProcess | null,
): Promise<void> {
  if (!process?.pid) {
    return;
  }
  try {
    process.kill("SIGTERM");
  } catch (err) {
    api.logger.warn(`[qq] failed to terminate idle sleep blocker: ${String(err)}`);
    return;
  }
  for (let i = 0; i < 10; i += 1) {
    if (process.exitCode !== null) {
      return;
    }
    await sleep(100);
  }
  try {
    process.kill("SIGKILL");
  } catch {
    // ignore
  }
}

type ManagedLaunchState = {
  executablePath: string;
  pids: number[];
  launchedAt: number;
};

function resolveManagedStatePath(stateDir: string): string {
  return path.join(stateDir, MANAGED_STATE_DIRNAME, MANAGED_STATE_FILENAME);
}

function writeManagedState(stateDir: string, state: ManagedLaunchState): void {
  const statePath = resolveManagedStatePath(stateDir);
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2), "utf8");
}

function readManagedState(stateDir: string): ManagedLaunchState | null {
  const statePath = resolveManagedStatePath(stateDir);
  if (!fs.existsSync(statePath)) {
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(statePath, "utf8")) as ManagedLaunchState;
  } catch {
    return null;
  }
}

function clearManagedState(stateDir: string): void {
  const statePath = resolveManagedStatePath(stateDir);
  try {
    fs.unlinkSync(statePath);
  } catch {
    // ignore
  }
}

async function killManagedPids(api: OpenClawPluginApi, pids: number[]): Promise<void> {
  for (const pid of pids) {
    try {
      process.kill(pid, "SIGTERM");
    } catch (err) {
      api.logger.warn(`[qq] failed to terminate managed QQ pid ${pid}: ${String(err)}`);
      continue;
    }
  }

  for (let i = 0; i < 10; i += 1) {
    const alive = pids.filter((pid) => {
      try {
        process.kill(pid, 0);
        return true;
      } catch {
        return false;
      }
    });
    if (alive.length === 0) {
      return;
    }
    await sleep(300);
  }

  for (const pid of pids) {
    try {
      process.kill(pid, "SIGKILL");
    } catch {
      // ignore
    }
  }
}

async function sendAction(params: {
  cfg: CoreConfig;
  accountId?: string;
  action: string;
  params: Record<string, unknown>;
  timeoutMs?: number;
}): Promise<OneBotApiResponse> {
  const connection = getConnection(params.accountId);
  const echo = `qq-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const payload = {
    action: params.action,
    params: params.params,
    echo,
  };

  return await new Promise<OneBotApiResponse>((resolve, reject) => {
    const timeout = setTimeout(
      () => {
        connection.pending.delete(echo);
        reject(new Error(`QQ action timed out: ${params.action}`));
      },
      typeof params.timeoutMs === "number" && Number.isFinite(params.timeoutMs)
        ? params.timeoutMs
        : 10_000,
    );

    connection.pending.set(echo, { resolve, reject, timeout });
    connection.socket.send(JSON.stringify(payload), (err) => {
      if (!err) {
        return;
      }
      clearTimeout(timeout);
      connection.pending.delete(echo);
      reject(err);
    });
  });
}

function buildQqReplySegments(replyToMessageId?: string): OneBotMessageSegment[] {
  const replyId = replyToMessageId?.trim();
  if (!replyId) {
    return [];
  }
  return [{ type: "reply", data: { id: replyId } }];
}

export async function sendQqText(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  text: string;
  replyToMessageId?: string;
}): Promise<OneBotApiResponse> {
  if (looksLikeTransientUpstreamErrorText(params.text)) {
    return {
      status: "ok",
      retcode: 0,
      data: { suppressed: true },
      message: "suppressed transient upstream error text",
    };
  }
  if (
    shouldSkipDuplicateQqDelivery({
      accountId: params.accountId,
      targetKind: params.targetKind,
      targetId: params.targetId,
      text: params.text,
    })
  ) {
    return {
      status: "ok",
      retcode: 0,
      data: { deduped: true },
      message: "deduped duplicate QQ delivery",
    };
  }
  const action = params.targetKind === "group" ? "send_group_msg" : "send_private_msg";
  const replySegments = buildQqReplySegments(params.replyToMessageId);
  const message =
    replySegments.length > 0 && params.text.trim()
      ? ([
          ...replySegments,
          { type: "text", data: { text: params.text } },
        ] as OneBotMessageSegment[])
      : params.text;
  const actionParams =
    params.targetKind === "group"
      ? { group_id: Number(params.targetId), message }
      : { user_id: Number(params.targetId), message };
  const result = await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action,
    params: actionParams,
  });
  rememberQqDeliveryFingerprint({
    accountId: params.accountId,
    targetKind: params.targetKind,
    targetId: params.targetId,
    text: params.text,
  });
  return result;
}

export async function sendQqMedia(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  text: string;
  mediaUrl: string;
  audioAsVoice?: boolean;
  replyToMessageId?: string;
  bypassDedup?: boolean;
}): Promise<OneBotApiResponse> {
  const normalizedMediaUrl = await resolveQqHttpMediaUrl({
    mediaUrl: params.mediaUrl,
    gatewayPort: params.cfg.gateway?.port,
  });
  const safeText = looksLikeTransientUpstreamErrorText(params.text) ? "" : params.text;
  const deliveryPlan = resolveQqMediaDeliveryPlan({
    mediaUrl: normalizedMediaUrl,
    audioAsVoice: params.audioAsVoice,
  });
  if (
    !params.bypassDedup &&
    shouldSkipDuplicateQqDelivery({
      accountId: params.accountId,
      targetKind: params.targetKind,
      targetId: params.targetId,
      text: safeText,
      mediaUrl: deliveryPlan.dedupeMediaUrl,
    })
  ) {
    return {
      status: "ok",
      retcode: 0,
      data: { deduped: true },
      message: "deduped duplicate QQ media delivery",
    };
  }
  if (deliveryPlan.kind === "voice") {
    return await sendQqVoice({
      cfg: params.cfg,
      accountId: params.accountId,
      targetKind: params.targetKind,
      targetId: params.targetId,
      audioUrl: normalizedMediaUrl,
      caption: safeText,
      preferPtt: deliveryPlan.preferPtt,
      replyToMessageId: params.replyToMessageId,
    });
  }
  const action = params.targetKind === "group" ? "send_group_msg" : "send_private_msg";
  const message = [];
  message.push(...buildQqReplySegments(params.replyToMessageId));
  if (safeText?.trim()) {
    message.push({ type: "text", data: { text: safeText } });
  }
  message.push({ type: "image", data: { file: normalizedMediaUrl } });
  const actionParams =
    params.targetKind === "group"
      ? { group_id: Number(params.targetId), message }
      : { user_id: Number(params.targetId), message };
  const result = await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action,
    params: actionParams,
  });
  rememberQqDeliveryFingerprint({
    accountId: params.accountId,
    targetKind: params.targetKind,
    targetId: params.targetId,
    text: safeText,
    mediaUrl: normalizedMediaUrl,
  });
  return result;
}

function isSilkHeader(buffer: Buffer) {
  const header = buffer.subarray(0, 10).toString();
  return header.includes("#!SILK") || header.includes("\u0002#!SILK");
}

const QQ_AUDIO_MEDIA_EXTENSIONS = new Set([
  ".aac",
  ".aif",
  ".aiff",
  ".amr",
  ".caf",
  ".flac",
  ".m4a",
  ".mp3",
  ".oga",
  ".ogg",
  ".opus",
  ".silk",
  ".wav",
  ".wma",
]);

function isQqAudioMediaUrl(mediaUrl: string): boolean {
  const trimmed = mediaUrl.trim();
  if (!trimmed) {
    return false;
  }
  if (/^data:audio\//i.test(trimmed)) {
    return true;
  }
  const pathLike = (() => {
    if (trimmed.startsWith("file://")) {
      try {
        return fileURLToPath(trimmed);
      } catch {
        return trimmed;
      }
    }
    if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)) {
      return trimmed;
    }
    try {
      return new URL(trimmed).pathname || trimmed;
    } catch {
      return trimmed;
    }
  })();
  const ext = path.extname(pathLike).toLowerCase();
  return QQ_AUDIO_MEDIA_EXTENSIONS.has(ext);
}

function resolveQqMediaDeliveryPlan(params: {
  mediaUrl: string;
  audioAsVoice?: boolean;
}):
  | { kind: "image"; dedupeMediaUrl: string }
  | { kind: "voice"; dedupeMediaUrl: string; preferPtt: boolean } {
  if (!isQqAudioMediaUrl(params.mediaUrl)) {
    return {
      kind: "image",
      dedupeMediaUrl: params.mediaUrl,
    };
  }
  const preferPtt = params.audioAsVoice === true;
  return {
    kind: "voice",
    dedupeMediaUrl: `${preferPtt ? "ptt" : "audio"}:${params.mediaUrl}`,
    preferPtt,
  };
}

function runExecFilePromise(file: string, args: string[]) {
  return new Promise<void>((resolve, reject) => {
    execFile(file, args, (error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

function resolveNapcatFfmpegAddonSourcePath() {
  if (process.platform !== "darwin" || process.arch !== "arm64") {
    return null;
  }
  const candidates = [
    path.join(
      os.homedir(),
      "Library/Containers/com.tencent.qq/Data/Documents/napcat/native/ffmpeg/ffmpegAddon.darwin.arm64.node",
    ),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

let signedNapcatFfmpegAddonCopyPath: string | null = null;
const signedNapcatFfmpegAddonPersistentDir = path.join(
  os.homedir(),
  ".openclaw",
  "cache",
  "qq-ptt-addon",
);
const signedNapcatFfmpegAddonPersistentPath = path.join(
  signedNapcatFfmpegAddonPersistentDir,
  "ffmpegAddon.darwin.arm64.node",
);

async function ensureSignedNapcatFfmpegAddonCopy() {
  if (signedNapcatFfmpegAddonCopyPath && fs.existsSync(signedNapcatFfmpegAddonCopyPath)) {
    return signedNapcatFfmpegAddonCopyPath;
  }
  if (fs.existsSync(signedNapcatFfmpegAddonPersistentPath)) {
    signedNapcatFfmpegAddonCopyPath = signedNapcatFfmpegAddonPersistentPath;
    return signedNapcatFfmpegAddonCopyPath;
  }
  const sourcePath = resolveNapcatFfmpegAddonSourcePath();
  if (!sourcePath) {
    return null;
  }
  await fs.promises.mkdir(signedNapcatFfmpegAddonPersistentDir, { recursive: true });
  const targetPath = signedNapcatFfmpegAddonPersistentPath;
  await fs.promises.copyFile(sourcePath, targetPath);
  try {
    await runExecFilePromise("/usr/bin/xattr", ["-cr", targetPath]);
  } catch {
    // best effort
  }
  await runExecFilePromise("/usr/bin/codesign", [
    "-s",
    "-",
    "--force",
    "--timestamp=none",
    targetPath,
  ]);
  signedNapcatFfmpegAddonCopyPath = targetPath;
  return targetPath;
}

async function materializeLocalQqVoiceInput(audioUrl: string) {
  if (/^https?:\/\//i.test(audioUrl)) {
    const response = await fetch(audioUrl);
    if (!response.ok) {
      throw new Error(`下载语音失败: HTTP ${response.status}`);
    }
    const ext = (() => {
      try {
        return path.extname(new URL(audioUrl).pathname) || ".bin";
      } catch {
        return ".bin";
      }
    })();
    const tempPath = path.join(
      os.tmpdir(),
      `openclaw-qq-ptt-input-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`,
    );
    const buffer = Buffer.from(await response.arrayBuffer());
    await fs.promises.writeFile(tempPath, buffer);
    return { filePath: tempPath, cleanup: [tempPath] };
  }
  const filePath = audioUrl.startsWith("file://") ? fileURLToPath(audioUrl) : audioUrl;
  return { filePath, cleanup: [] as string[] };
}

async function convertAudioToNapcatSilk(audioUrl: string) {
  const addonPath = await ensureSignedNapcatFfmpegAddonCopy();
  if (!addonPath) {
    return null;
  }
  const { filePath, cleanup } = await materializeLocalQqVoiceInput(audioUrl);
  try {
    const head = await fs.promises.readFile(filePath);
    if (isSilkHeader(head)) {
      return { silkPath: filePath, cleanup };
    }
    const wavPath = path.join(
      os.tmpdir(),
      `openclaw-qq-ptt-source-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.wav`,
    );
    await runExecFilePromise("ffmpeg", [
      "-hide_banner",
      "-loglevel",
      "error",
      "-y",
      "-i",
      filePath,
      "-ar",
      "16000",
      "-ac",
      "1",
      "-c:a",
      "pcm_s16le",
      wavPath,
    ]);
    const moduleHandle = { exports: {} as Record<string, unknown> };
    process.dlopen(moduleHandle, addonPath);
    const convert = moduleHandle.exports.convertToNTSilkTct as
      | ((inputPath: string, outputPath: string) => Promise<void>)
      | undefined;
    if (typeof convert !== "function") {
      return null;
    }
    const silkPath = path.join(
      os.tmpdir(),
      `openclaw-qq-ptt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.silk`,
    );
    await convert(wavPath, silkPath);
    const silkBuffer = await fs.promises.readFile(silkPath);
    if (!isSilkHeader(silkBuffer)) {
      cleanup.push(wavPath, silkPath);
      return null;
    }
    return { silkPath, cleanup: [...cleanup, wavPath, silkPath] };
  } catch {
    return null;
  }
}

export async function sendQqVoice(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  audioUrl: string;
  caption?: string;
  preferPtt?: boolean;
  replyToMessageId?: string;
}): Promise<{
  ok: boolean;
  mode: "ptt" | "audio" | "text";
  capability: "qq-ptt" | "qq-audio-file" | "qq-text-only";
  result: OneBotApiResponse;
  attempts: Array<{
    mode: "ptt" | "audio" | "text";
    capability: "qq-ptt" | "qq-audio-file" | "qq-text-only";
    status: string | null;
    retcode: number | null;
    message: string | null;
    wording: string | null;
  }>;
}> {
  const normalizedAudioUrl = await resolveQqHttpMediaUrl({
    mediaUrl: params.audioUrl,
    gatewayPort: params.cfg.gateway?.port,
  });
  const silkInfo = await convertAudioToNapcatSilk(normalizedAudioUrl);
  const pttFileRef = await (async () => {
    try {
      const pttSource = silkInfo?.silkPath ?? normalizedAudioUrl;
      if (/^https?:\/\//i.test(pttSource)) {
        const response = await fetch(pttSource);
        if (!response.ok) {
          return pttSource;
        }
        const buffer = Buffer.from(await response.arrayBuffer());
        return `base64://${buffer.toString("base64")}`;
      }
      const localPath = pttSource.startsWith("file://") ? fileURLToPath(pttSource) : pttSource;
      const buffer = await fs.promises.readFile(localPath);
      return `base64://${buffer.toString("base64")}`;
    } catch {
      return normalizedAudioUrl;
    }
  })();
  const caption = looksLikeTransientUpstreamErrorText(params.caption ?? "")
    ? ""
    : (params.caption ?? "").trim();
  const replySegments = buildQqReplySegments(params.replyToMessageId);
  const attempts: Array<{
    mode: "ptt" | "audio" | "text";
    capability: "qq-ptt" | "qq-audio-file" | "qq-text-only";
    status: string | null;
    retcode: number | null;
    message: string | null;
    wording: string | null;
  }> = [];
  const action = params.targetKind === "group" ? "send_group_msg" : "send_private_msg";
  const candidateModes =
    params.preferPtt === false ? (["audio", "ptt"] as const) : (["ptt", "audio"] as const);

  for (const mode of candidateModes) {
    const message =
      mode === "ptt"
        ? ([
            ...replySegments,
            { type: "record", data: { file: pttFileRef } },
          ] as OneBotMessageSegment[])
        : ([
            ...replySegments,
            ...(caption ? [{ type: "text", data: { text: caption } } as OneBotMessageSegment] : []),
            { type: "file", data: { file: normalizedAudioUrl, name: "reply.mp3" } },
          ] as OneBotMessageSegment[]);
    const actionParams =
      params.targetKind === "group"
        ? { group_id: Number(params.targetId), message }
        : { user_id: Number(params.targetId), message };
    const result = await sendAction({
      cfg: params.cfg,
      accountId: params.accountId,
      action,
      params: actionParams,
    });
    const ok = result.status === "ok" || result.retcode === 0;
    attempts.push({
      mode,
      capability: mode === "ptt" ? "qq-ptt" : "qq-audio-file",
      status: result.status ?? null,
      retcode: result.retcode ?? null,
      message: result.message ?? null,
      wording: result.wording ?? null,
    });
    if (ok) {
      rememberQqDeliveryFingerprint({
        accountId: params.accountId,
        targetKind: params.targetKind,
        targetId: params.targetId,
        text: caption,
        mediaUrl: `${mode}:${normalizedAudioUrl}`,
      });
      for (const tempPath of silkInfo?.cleanup ?? []) {
        fs.promises.unlink(tempPath).catch(() => {});
      }
      return {
        ok: true,
        mode,
        capability: mode === "ptt" ? "qq-ptt" : "qq-audio-file",
        result,
        attempts,
      };
    }
  }

  for (const tempPath of silkInfo?.cleanup ?? []) {
    fs.promises.unlink(tempPath).catch(() => {});
  }

  const text =
    caption ||
    "这边暂时发不了 QQ 语音/PTT，也没法作为音频文件发出，你如果愿意我可以先直接用文字回复。";
  const result = await sendQqText({
    cfg: params.cfg,
    accountId: params.accountId,
    targetKind: params.targetKind,
    targetId: params.targetId,
    text,
    replyToMessageId: params.replyToMessageId,
  });
  attempts.push({
    mode: "text",
    capability: "qq-text-only",
    status: result.status ?? null,
    retcode: result.retcode ?? null,
    message: result.message ?? null,
    wording: result.wording ?? null,
  });
  return {
    ok: result.status === "ok" || result.retcode === 0,
    mode: "text",
    capability: "qq-text-only",
    result,
    attempts,
  };
}

export async function sendQqSegments(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  message: OneBotMessageSegment[];
}): Promise<OneBotApiResponse> {
  const action = params.targetKind === "group" ? "send_group_msg" : "send_private_msg";
  const actionParams =
    params.targetKind === "group"
      ? { group_id: Number(params.targetId), message: params.message }
      : { user_id: Number(params.targetId), message: params.message };
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action,
    params: actionParams,
  });
}

export async function sendQqForwardMessages(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  messages: Array<{
    type: "node";
    data: {
      name: string;
      uin: string;
      content: string;
    };
  }>;
}): Promise<OneBotApiResponse> {
  const action =
    params.targetKind === "group" ? "send_group_forward_msg" : "send_private_forward_msg";
  const actionParams =
    params.targetKind === "group"
      ? { group_id: Number(params.targetId), messages: params.messages }
      : { user_id: Number(params.targetId), messages: params.messages };
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action,
    params: actionParams,
  });
}

export async function deleteQqMessage(params: {
  cfg: CoreConfig;
  accountId?: string;
  messageId: number;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "delete_msg",
    params: {
      message_id: params.messageId,
    },
  });
}

export async function getQqLoginInfo(params: {
  cfg: CoreConfig;
  accountId?: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_login_info",
    params: {},
  });
}

export async function getQqUserInfo(params: {
  cfg: CoreConfig;
  accountId?: string;
  userId: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_stranger_info",
    params: {
      user_id: Number(params.userId),
      no_cache: false,
    },
  });
}

export async function setQqFriendAddRequest(params: {
  cfg: CoreConfig;
  accountId?: string;
  flag: string;
  approve: boolean;
  remark?: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "set_friend_add_request",
    params: {
      flag: params.flag,
      approve: params.approve,
      remark: params.remark ?? "",
    },
  });
}

export async function getQqGroupInfo(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_group_info",
    params: {
      group_id: Number(params.groupId),
      no_cache: false,
    },
  });
}

export async function getQqGroupMembers(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_group_member_list",
    params: {
      group_id: Number(params.groupId),
    },
  });
}

export async function sendQqLike(params: {
  cfg: CoreConfig;
  accountId?: string;
  userId: string;
  times?: number;
}): Promise<OneBotApiResponse> {
  const times = Math.max(1, Math.min(10, Number(params.times ?? 10)));
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "send_like",
    params: {
      user_id: Number(params.userId),
      times,
    },
  });
}

export async function setQqGroupBan(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  userId: string;
  duration?: number;
}): Promise<OneBotApiResponse> {
  const duration = Math.max(0, Math.trunc(Number(params.duration ?? 60)));
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "set_group_ban",
    params: {
      group_id: Number(params.groupId),
      user_id: Number(params.userId),
      duration,
    },
  });
}

export async function setQqGroupWholeBan(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  enable?: boolean;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "set_group_whole_ban",
    params: {
      group_id: Number(params.groupId),
      enable: params.enable !== false,
    },
  });
}

export async function setQqGroupKick(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  userId: string;
  rejectAddRequest?: boolean;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "set_group_kick",
    params: {
      group_id: Number(params.groupId),
      user_id: Number(params.userId),
      reject_add_request: params.rejectAddRequest === true,
    },
  });
}

export async function setQqGroupAdmin(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  userId: string;
  enable?: boolean;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "set_group_admin",
    params: {
      group_id: Number(params.groupId),
      user_id: Number(params.userId),
      enable: params.enable !== false,
    },
  });
}

export async function setQqGroupSpecialTitle(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  userId: string;
  specialTitle: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "set_group_special_title",
    params: {
      group_id: Number(params.groupId),
      user_id: Number(params.userId),
      special_title: params.specialTitle,
    },
  });
}

export function isOneBotActionAccepted(result: OneBotApiResponse | null | undefined): boolean {
  if (!result) {
    return false;
  }
  if (result.status === "ok" || result.retcode === 0) {
    return true;
  }
  const normalizedStatus = String(result.status ?? "")
    .trim()
    .toLowerCase();
  if (normalizedStatus) {
    return normalizedStatus === "ok";
  }
  if (typeof result.retcode === "number") {
    return result.retcode === 0;
  }
  const diagnosticText = [result.message, result.wording]
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .join(" ");
  if (!diagnosticText) {
    return true;
  }
  return !/(?:error|fail|failed|invalid|forbidden|denied|unsupported|not\s+available|失败|错误|异常|无效|禁止|不存在)/iu.test(
    diagnosticText,
  );
}

export function extractQqUserLevel(data: unknown): number | null {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return null;
  }
  const record = data as Record<string, unknown>;
  for (const key of ["qqLevel", "qlevel", "level", "qq_level"]) {
    const raw = record[key];
    const value = Number(raw);
    if (Number.isFinite(value) && value >= 0) {
      return Math.trunc(value);
    }
  }
  return null;
}

export function hasAtLeastOneSunQqLevel(level: number | null | undefined): boolean {
  return Number.isFinite(Number(level)) && Number(level) >= QQ_ONE_SUN_LEVEL;
}

function resolveQqFriendRequestPolicy(account: ResolvedQqAccount) {
  const config = account.config.friendRequests ?? {};
  const minQqLevel = Number.isFinite(Number(config.minQqLevel))
    ? Math.max(1, Math.trunc(Number(config.minQqLevel)))
    : QQ_ONE_SUN_LEVEL;
  return {
    enabled: config.autoApproveEnabled === true,
    minQqLevel,
  };
}

async function handleInboundFriendRequest(params: {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  event: OneBotFriendRequestEvent;
}) {
  const senderId = String(params.event.user_id ?? "").trim();
  if (!senderId) {
    return;
  }
  const policy = resolveQqFriendRequestPolicy(params.account);
  if (!policy.enabled) {
    return;
  }
  const blockedUserIds = normalizeBlockedQqUserIds(params.account.config.blockedUserIds);
  if (blockedUserIds.has(senderId)) {
    params.api.logger.info(
      `[qq] friend request left pending because sender is blocked: user=${senderId}`,
    );
    return;
  }
  let nickname = senderId;
  let qqLevel: number | null = null;
  try {
    const info = await getQqUserInfo({
      cfg: params.api.runtime.config.loadConfig() as CoreConfig,
      accountId: params.account.accountId,
      userId: senderId,
    });
    const data =
      info.data && typeof info.data === "object" && !Array.isArray(info.data)
        ? (info.data as Record<string, unknown>)
        : null;
    qqLevel = extractQqUserLevel(data);
    nickname =
      String(data?.nickname ?? data?.nick ?? data?.remark ?? data?.showName ?? senderId).trim() ||
      senderId;
  } catch (error) {
    params.api.logger.warn(
      `[qq] failed to inspect friend request sender ${senderId}: ${String(error)}`,
    );
  }
  if (qqLevel === null) {
    params.api.logger.info(
      `[qq] friend request left pending because sender level is unknown: user=${senderId} nick=${nickname}`,
    );
    return;
  }
  if (qqLevel < policy.minQqLevel) {
    params.api.logger.info(
      `[qq] friend request left pending because sender level is below threshold: user=${senderId} nick=${nickname} qqLevel=${qqLevel} required=${policy.minQqLevel}`,
    );
    return;
  }
  const result = await setQqFriendAddRequest({
    cfg: params.api.runtime.config.loadConfig() as CoreConfig,
    accountId: params.account.accountId,
    flag: params.event.flag,
    approve: true,
  });
  if (isOneBotActionAccepted(result)) {
    params.api.logger.info(
      `[qq] auto-approved friend request: user=${senderId} nick=${nickname} qqLevel=${qqLevel} required=${policy.minQqLevel}`,
    );
    return;
  }
  params.api.logger.warn(
    `[qq] failed auto-approving friend request: user=${senderId} nick=${nickname} qqLevel=${qqLevel} required=${policy.minQqLevel} status=${result.status ?? "null"} retcode=${result.retcode ?? "null"} message=${result.message ?? result.wording ?? ""}`,
  );
}

export async function sendQqPoke(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  userId?: string;
}): Promise<OneBotApiResponse> {
  if (params.targetKind === "group") {
    const userId = String(params.userId ?? "").trim();
    if (!userId) {
      throw new Error("userId required for group poke");
    }
    return await sendAction({
      cfg: params.cfg,
      accountId: params.accountId,
      action: "group_poke",
      params: {
        group_id: Number(params.targetId),
        user_id: Number(userId),
      },
    });
  }
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "friend_poke",
    params: {
      user_id: Number(params.userId ?? params.targetId),
    },
  });
}

function normalizeOneBotBusid(busid: string | number | undefined): string | number | undefined {
  if (typeof busid === "number" && Number.isFinite(busid)) {
    return busid;
  }
  const text = String(busid ?? "").trim();
  if (!text) {
    return undefined;
  }
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : text;
}

export async function uploadQqGroupFile(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  file: string;
  name: string;
  folderId?: string;
  uploadFile?: boolean;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "upload_group_file",
    params: {
      group_id: Number(params.groupId),
      file: params.file,
      name: params.name,
      folder: params.folderId,
      ...(typeof params.uploadFile === "boolean" ? { upload_file: params.uploadFile } : {}),
    },
  });
}

export async function getQqGroupRootFiles(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_group_root_files",
    params: {
      group_id: Number(params.groupId),
    },
  });
}

export async function getQqGroupFilesByFolder(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  folderId: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_group_files_by_folder",
    params: {
      group_id: Number(params.groupId),
      folder_id: params.folderId,
    },
  });
}

export async function getQqGroupFileUrl(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  fileId: string;
  busid?: string | number;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_group_file_url",
    params: {
      group_id: Number(params.groupId),
      file_id: params.fileId,
      busid: normalizeOneBotBusid(params.busid),
    },
  });
}

export async function getQqFile(params: {
  cfg: CoreConfig;
  accountId?: string;
  fileId: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_file",
    params: {
      file_id: params.fileId,
    },
    timeoutMs: 120_000,
  });
}

export async function getQqPacketStatus(params: {
  cfg: CoreConfig;
  accountId?: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "nc_get_packet_status",
    params: {},
  });
}

export async function getQqGroupFileSystemInfo(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
}): Promise<OneBotApiResponse> {
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action: "get_group_file_system_info",
    params: {
      group_id: Number(params.groupId),
    },
  });
}

function getOneBotMessageId(result: OneBotApiResponse): string | undefined {
  const messageIdRaw =
    (result.data as Record<string, unknown> | undefined)?.message_id ??
    (result.data as Record<string, unknown> | undefined)?.messageId;
  const messageId = Number(messageIdRaw);
  if (!Number.isFinite(messageId) || messageId <= 0) {
    return undefined;
  }
  return String(messageId);
}

function deriveAgentIdFromSessionKey(sessionKey?: string): string {
  const match = sessionKey?.match(/^agent:([^:]+)/);
  return match?.[1] ? match[1] : "main";
}

function noteQqReplyDelivery(conversationKey: string | undefined, result: OneBotApiResponse) {
  if (!conversationKey) {
    return;
  }
  const messageId = getOneBotMessageId(result);
  if (!messageId) {
    return;
  }
  const state = getQqConversationState(conversationKey);
  state.lastRepliedMessageId = messageId;
}

async function rememberOutboundQqMedia(params: {
  conversationKey?: string;
  cfg: OpenClawConfig;
  agentId?: string;
  mediaUrl: string;
  caption: string;
  result: OneBotApiResponse;
}) {
  void params;
}

export async function rememberSentQqMedia(params: {
  cfg: OpenClawConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  mediaUrl: string;
  caption?: string;
  result: OneBotApiResponse;
  agentId?: string;
}) {
  const conversationKey = `qq:${params.accountId ?? "default"}:${params.targetKind === "group" ? "group" : "direct"}:${params.targetId}`;
  noteQqReplyDelivery(conversationKey, params.result);
  await rememberOutboundQqMedia({
    conversationKey,
    cfg: params.cfg,
    agentId: params.agentId ?? "main",
    mediaUrl: params.mediaUrl,
    caption: params.caption?.trim() ?? "",
    result: params.result,
  });
}

async function deliverInboundReply(params: {
  cfg: OpenClawConfig;
  account: ResolvedQqAccount;
  accountId?: string;
  event: OneBotMessageEvent;
  payload: OutboundReplyPayload;
  recoveryReplyToMessageId?: string;
  trackingKey?: string;
  conversationKey?: string;
  sessionKey?: string;
  agentId?: string;
}) {
  const parsed =
    params.event.message_type === "group"
      ? { kind: "group" as const, id: String(params.event.group_id ?? "") }
      : { kind: "user" as const, id: String(params.event.user_id) };
  const rawText = (params.payload.text ?? "").trim();
  const initialBursts =
    parsed.kind === "group"
      ? buildTargetSocialReplyBursts({
          account: params.account,
          cfg: params.cfg,
          groupId: parsed.id,
          chatType: "group",
          text: rawText,
        })
      : buildTargetSocialReplyBursts({
          account: params.account,
          cfg: params.cfg,
          chatType: "direct",
          text: rawText,
        });
  const textBursts = expandDeliveryBursts(initialBursts)
    .map((burst) => {
      const settings = resolveQqNaturalChatConfig({
        account: params.account,
        groupId: parsed.kind === "group" ? parsed.id : undefined,
        chatType: parsed.kind === "group" ? "group" : "direct",
      });
      return settings.enabled
        ? stripQqNaturalChatHardBans(burst, settings.hardBannedSymbols)
        : burst;
    })
    .map((burst) => burst.trim())
    .filter(Boolean);
  const mediaUrls = [
    ...(params.payload.mediaUrls ?? []),
    ...(params.payload.mediaUrl ? [params.payload.mediaUrl] : []),
  ].filter(Boolean);
  if (shouldSuppressNoisyUserFacingErrorReply({ text: rawText, mediaUrls })) {
    return;
  }
  const audioAsVoice = (params.payload as { audioAsVoice?: boolean }).audioAsVoice === true;
  const replyToMessageId =
    (params.payload as { replyToId?: string }).replyToId?.trim() ||
    params.recoveryReplyToMessageId?.trim() ||
    undefined;
  const hookConversationId = parsed.kind === "group" ? `qq:group:${parsed.id}` : `qq:${parsed.id}`;
  let replyApplied = false;

  const emitSentHook = async (payload: {
    content: string;
    success: boolean;
    error?: string;
    messageId?: string | null;
  }) => {
    if (!params.sessionKey) {
      return;
    }
    await triggerInternalHook(
      createInternalHookEvent("message", "sent", params.sessionKey, {
        to: hookConversationId,
        content: payload.content,
        success: payload.success,
        ...(payload.error ? { error: payload.error } : {}),
        channelId: CHANNEL_ID,
        accountId: params.accountId,
        conversationId: hookConversationId,
        ...(payload.messageId ? { messageId: payload.messageId } : {}),
        isGroup: parsed.kind === "group",
        ...(parsed.kind === "group" ? { groupId: parsed.id } : {}),
      }),
    );
  };

  const extractSentMessageId = (result: OneBotApiResponse) => {
    const data = result.data as Record<string, unknown> | undefined;
    const raw = data?.message_id ?? data?.messageId;
    if (raw == null) {
      return null;
    }
    return String(raw);
  };

  const sendTextWithHook = async (text: string) => {
    try {
      const appliedReplyToMessageId = replyApplied ? undefined : replyToMessageId;
      const result = await sendQqText({
        cfg: params.cfg as CoreConfig,
        accountId: params.accountId,
        targetKind: parsed.kind,
        targetId: parsed.id,
        text,
        replyToMessageId: appliedReplyToMessageId,
      });
      if (appliedReplyToMessageId) {
        replyApplied = true;
      }
      await emitSentHook({
        content: text,
        success: true,
        messageId: extractSentMessageId(result),
      });
      return result;
    } catch (error) {
      await emitSentHook({
        content: text,
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  };

  const sendMediaWithHook = async (mediaUrl: string, caption: string) => {
    try {
      const appliedReplyToMessageId = replyApplied ? undefined : replyToMessageId;
      const result = await sendQqMedia({
        cfg: params.cfg as CoreConfig,
        accountId: params.accountId,
        targetKind: parsed.kind,
        targetId: parsed.id,
        text: caption,
        mediaUrl,
        audioAsVoice,
        replyToMessageId: appliedReplyToMessageId,
      });
      if (appliedReplyToMessageId) {
        replyApplied = true;
      }
      await emitSentHook({
        content: caption,
        success: true,
        messageId: extractSentMessageId(result),
      });
      return result;
    } catch (error) {
      await emitSentHook({
        content: caption,
        success: false,
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  };

  const sentMedia = await sendMediaWithLeadingCaption({
    mediaUrls,
    caption: textBursts[0] ?? "",
    send: async ({ mediaUrl, caption }) => {
      const result = await sendMediaWithHook(mediaUrl, caption ?? "");
      trackOutboundMessage(params.trackingKey, result);
      noteQqReplyDelivery(params.conversationKey, result);
      await rememberOutboundQqMedia({
        conversationKey: params.conversationKey,
        cfg: params.cfg,
        agentId: params.agentId ?? deriveAgentIdFromSessionKey(params.sessionKey),
        mediaUrl,
        caption: caption ?? "",
        result,
      });
    },
    onError: (error, mediaUrl) => {
      const apiLabel = params.accountId ?? "default";
      console.warn(`[qq] media send failed for ${apiLabel}: ${String(error)} media=${mediaUrl}`);
    },
  });
  if (sentMedia) {
    if (parsed.kind === "group" && params.accountId) {
      noteDirectFollowupReply({
        accountId: params.accountId,
        groupId: parsed.id,
        senderId: String(params.event.user_id),
        now: Date.now(),
        replyText: textBursts.join(" "),
      });
    }
    for (const [index, burst] of textBursts.slice(1).entries()) {
      if (index > 0 || textBursts.length > 1) {
        await sleep(BURST_SEND_DELAY_MS);
      }
      const result = await sendTextWithHook(burst);
      trackOutboundMessage(params.trackingKey, result);
      noteQqReplyDelivery(params.conversationKey, result);
    }
    return;
  }
  let sentAnyText = false;
  for (const [index, burst] of textBursts.entries()) {
    if (index > 0) {
      await sleep(BURST_SEND_DELAY_MS);
    }
    const result = await sendTextWithHook(burst);
    trackOutboundMessage(params.trackingKey, result);
    noteQqReplyDelivery(params.conversationKey, result);
    sentAnyText = true;
  }
  if (sentAnyText && parsed.kind === "group" && params.accountId) {
    noteDirectFollowupReply({
      accountId: params.accountId,
      groupId: parsed.id,
      senderId: String(params.event.user_id),
      now: Date.now(),
      replyText: textBursts.join(" "),
    });
  }
}

function trackOutboundMessage(trackingKey: string | undefined, result: OneBotApiResponse) {
  if (!trackingKey) {
    return;
  }
  const messageIdRaw =
    (result.data as Record<string, unknown> | undefined)?.message_id ??
    (result.data as Record<string, unknown> | undefined)?.messageId;
  const messageId = Number(messageIdRaw);
  if (!Number.isFinite(messageId) || messageId <= 0) {
    return;
  }
  const current = recentOutboundMessages.get(trackingKey) ?? [];
  current.push(messageId);
  recentOutboundMessages.set(trackingKey, current.slice(-10));
}

export function buildRecallTrackingKey(params: {
  sessionKey?: string | null;
  senderId?: string | null;
}): string | null {
  const sessionKey = params.sessionKey?.trim();
  const senderId = params.senderId?.trim();
  if (!sessionKey || !senderId) {
    return null;
  }
  return `${sessionKey}::${senderId}`;
}

export async function recallRecentQqMessages(params: {
  cfg: CoreConfig;
  accountId?: string;
  trackingKey: string;
  count?: number;
}) {
  const ids = recentOutboundMessages.get(params.trackingKey) ?? [];
  if (ids.length === 0) {
    return {
      ok: false,
      recalled: 0,
      failed: 0,
      message: "没有找到最近发送的消息，可能已经超过撤回时限。",
    };
  }

  const count = Math.max(1, Math.min(5, Number(params.count ?? 1)));
  const targetIds = ids.slice(-count).reverse();
  let recalled = 0;
  let failed = 0;

  for (const messageId of targetIds) {
    try {
      await deleteQqMessage({
        cfg: params.cfg,
        accountId: params.accountId,
        messageId,
      });
      recalled += 1;
      const rest = (recentOutboundMessages.get(params.trackingKey) ?? []).filter(
        (id) => id !== messageId,
      );
      recentOutboundMessages.set(params.trackingKey, rest);
    } catch {
      failed += 1;
    }
  }

  return {
    ok: recalled > 0,
    recalled,
    failed,
    message:
      recalled > 0
        ? `已撤回 ${recalled} 条消息${failed > 0 ? `，${failed} 条失败` : ""}`
        : "撤回失败，可能已经超过撤回时限。",
  };
}

async function resolveInboundMediaPayload(params: {
  runtime: ReturnType<typeof getQqRuntime>;
  account: ResolvedQqAccount;
  imageUrls: string[];
}): Promise<ResolvedInboundMediaPayload> {
  if (params.imageUrls.length === 0) {
    return { payload: {}, resolvedMedia: [] };
  }

  const maxBytes = (params.account.config.mediaMaxMb ?? DEFAULT_MEDIA_MAX_MB) * 1024 * 1024;
  const mediaList: Array<{ path: string; contentType?: string }> = [];
  const mediaUrls: string[] = [];
  const resolvedMedia: ResolvedInboundMediaEntry[] = [];

  for (const url of params.imageUrls) {
    try {
      const localPath = resolveLocalMediaReference(url);
      if (localPath) {
        const fileBuffer = fs.readFileSync(localPath);
        const mimeType = resolveQqImageMimeType(localPath);
        const saved = await params.runtime.channel.media.saveMediaBuffer(
          fileBuffer,
          mimeType,
          CHANNEL_ID,
          maxBytes,
          path.basename(localPath),
        );
        mediaList.push({
          path: saved.path,
          contentType: saved.contentType ?? mimeType,
        });
        mediaUrls.push(saved.path);
        resolvedMedia.push({
          sourceUrl: url,
          localPath: saved.path,
          contentType: saved.contentType ?? mimeType,
          resolution: "local-file",
        });
        continue;
      }
      const fetched = await fetchQqRemoteMediaWithFallback({
        runtime: params.runtime,
        url,
        maxBytes,
      });
      const saved = await params.runtime.channel.media.saveMediaBuffer(
        fetched.buffer,
        fetched.contentType,
        CHANNEL_ID,
        maxBytes,
        fetched.fileName,
      );
      mediaList.push({
        path: saved.path,
        contentType: saved.contentType ?? fetched.contentType,
      });
      mediaUrls.push(saved.path);
      resolvedMedia.push({
        sourceUrl: url,
        localPath: saved.path,
        contentType: saved.contentType ?? fetched.contentType,
        resolution: fetched.resolution,
      });
    } catch (error) {
      mediaUrls.push(url);
      resolvedMedia.push({
        sourceUrl: url,
        resolution: "unresolved",
        error: String(error),
      });
    }
  }

  if (mediaList.length === 0) {
    return {
      payload: {
        MediaUrls: mediaUrls.length > 0 ? mediaUrls : undefined,
        MediaUrl: mediaUrls[0],
      },
      resolvedMedia,
    };
  }

  const built = buildMediaPayload(mediaList, { preserveMediaTypeCardinality: true });
  return {
    payload: {
      ...built,
      MediaUrl: built.MediaPath ?? mediaUrls[0],
      MediaUrls: mediaUrls.length > 0 ? mediaUrls : built.MediaUrls,
    },
    resolvedMedia,
  };
}

async function prepareQqInboundMediaContext(params: {
  api: OpenClawPluginApi;
  runtime: ReturnType<typeof getQqRuntime>;
  cfg: OpenClawConfig;
  account: ResolvedQqAccount;
  routeAgentId: string;
  conversationKey: string;
  retained: QueuedQqInboundEvent[];
  focusEntry: QueuedQqInboundEvent;
  mergedParsed: ParsedQqMessage;
}): Promise<PreparedQqInboundMediaContext> {
  const inboundMediaPayload = await resolveInboundMediaPayload({
    runtime: params.runtime,
    account: params.account,
    imageUrls: params.retained.flatMap((entry) => entry.parsed.imageUrls),
  });
  if (inboundMediaPayload.resolvedMedia.length > 0) {
    recordQqDebugEvent({
      api: params.api,
      conversationKey: params.conversationKey,
      kind: "media_ingress",
      detail: {
        phase: "resolved",
        focusMessageId: params.focusEntry.event.message_id
          ? String(params.focusEntry.event.message_id)
          : "",
        resolvedMedia: buildResolvedInboundMediaDebug(inboundMediaPayload.resolvedMedia),
      },
    });
  }
  let mediaOffset = 0;
  const currentMedia: QqMediaRecord[] = [];
  for (const entry of params.retained) {
    const imageCount = entry.parsed.imageUrls.length;
    const mediaSlice = inboundMediaPayload.resolvedMedia.slice(
      mediaOffset,
      mediaOffset + imageCount,
    );
    mediaOffset += imageCount;
    const messageId = entry.event.message_id ? String(entry.event.message_id) : undefined;
    const records = await buildQqMediaRecords({
      cfg: params.cfg,
      agentId: params.routeAgentId,
      logger: params.api.logger,
      source: "inbound",
      messageId,
      senderId: entry.senderId,
      senderName: entry.senderName,
      caption: entry.parsed.text,
      quotedText: undefined,
      replyTo: entry.parsed.replyToMessageId
        ? { message_id: entry.parsed.replyToMessageId }
        : undefined,
      parsed: entry.parsed,
      resolvedMedia: mediaSlice,
      createdAt: entry.timestamp,
    });
    currentMedia.push(...records);
  }
  rememberQqMediaRecords(params.conversationKey, currentMedia);

  const replyTarget = await resolveQqReplyTarget({
    api: params.api,
    cfg: params.cfg,
    account: params.account,
    routeAgentId: params.routeAgentId,
    conversationKey: params.conversationKey,
    replyToMessageId: params.mergedParsed.replyToMessageId,
  });
  return {
    inboundMediaPayload,
    currentMedia,
    replyTarget,
    boundMedia: resolveQqBoundMedia({
      api: params.api,
      conversationKey: params.conversationKey,
      focusEntry: params.focusEntry,
      currentMedia,
      replyTarget,
    }),
  };
}

async function rememberQqLightweightInboundMedia(params: {
  cfg: OpenClawConfig;
  routeAgentId: string;
  conversationKey: string;
  retained: QueuedQqInboundEvent[];
  logger?: Pick<OpenClawPluginApi["logger"], "warn">;
}) {
  const records: QqMediaRecord[] = [];
  for (const entry of params.retained) {
    if (entry.parsed.mediaSegments.length === 0) {
      continue;
    }
    const messageId = entry.event.message_id ? String(entry.event.message_id) : undefined;
    records.push(
      ...(await buildQqMediaRecords({
        cfg: params.cfg,
        agentId: params.routeAgentId,
        logger: params.logger,
        source: "inbound",
        messageId,
        senderId: entry.senderId,
        senderName: entry.senderName,
        caption: entry.parsed.text,
        quotedText: undefined,
        replyTo: entry.parsed.replyToMessageId
          ? { message_id: entry.parsed.replyToMessageId }
          : undefined,
        parsed: entry.parsed,
        resolvedMedia: [],
        createdAt: entry.timestamp,
      })),
    );
  }
  rememberQqMediaRecords(params.conversationKey, records);
}

function selectQqBurstFocusEntry(entries: QueuedQqInboundEvent[]): QueuedQqInboundEvent {
  return entries.reduce((best, candidate) => {
    const score = (entry: QueuedQqInboundEvent) => {
      let value = entry.timestamp;
      if (entry.parsed.wasMentioned) {
        value += 10_000_000;
      }
      if (entry.parsed.isReply) {
        value += 7_000_000;
      }
      if (entry.parsed.text.trim()) {
        value += 2_000_000;
      }
      if (looksLikeQqExplicitInstruction(entry.rawBody)) {
        value += 5_000_000;
      }
      if (entry.parsed.mediaSegments.length > 0) {
        value += 1_000_000;
      }
      return value;
    };
    return score(candidate) >= score(best) ? candidate : best;
  });
}

function compactQqBurstEntries(entries: QueuedQqInboundEvent[]) {
  const allMediaLike = entries.every(
    (entry) =>
      entry.parsed.hasOnlyMediaLike ||
      (!entry.parsed.text && entry.parsed.mediaSegments.length > 0),
  );
  if (allMediaLike && entries.length > QQ_BURST_MEDIA_ONLY_KEEP) {
    return {
      retained: entries.slice(-QQ_BURST_MEDIA_ONLY_KEEP),
      omittedCount: entries.length - QQ_BURST_MEDIA_ONLY_KEEP,
      compacted: true,
    };
  }
  return {
    retained: entries,
    omittedCount: 0,
    compacted: false,
  };
}

function formatQqBurstContext(params: {
  entries: QueuedQqInboundEvent[];
  omittedCount: number;
}): string | undefined {
  if (params.entries.length <= 1 && params.omittedCount <= 0) {
    return undefined;
  }
  const lines = params.entries.map((entry, index) => {
    const markers = [
      entry.parsed.wasMentioned ? "@我" : null,
      entry.parsed.isReply && entry.parsed.replyToMessageId
        ? `reply:${entry.parsed.replyToMessageId}`
        : null,
    ]
      .filter(Boolean)
      .join(" ");
    const preview = entry.rawBody || summarizeQqMediaPlaceholder(entry.parsed);
    return `${index + 1}. ${entry.senderName ?? entry.senderId}${markers ? ` [${markers}]` : ""}: ${preview}`;
  });
  if (params.omittedCount > 0) {
    lines.splice(1, 0, `… 中间省略 ${params.omittedCount} 条相似图片/表情消息`);
  }
  return `以下是连续消息（按顺序）：\n${lines.join("\n")}`;
}

async function buildQqMediaRecords(params: {
  cfg: OpenClawConfig;
  agentId: string;
  logger?: Pick<OpenClawPluginApi["logger"], "warn">;
  source: QqMediaRecord["source"];
  messageId?: string;
  senderId?: string;
  senderName?: string;
  caption: string;
  quotedText?: string;
  replyTo?: QqMediaRecord["reply_to"];
  parsed: ParsedQqMessage;
  resolvedMedia: ResolvedInboundMediaEntry[];
  createdAt: number;
}): Promise<QqMediaRecord[]> {
  const records: QqMediaRecord[] = [];
  const imageSegments = params.parsed.mediaSegments.filter((segment) => segment.type === "image");
  if (imageSegments.length > 0) {
    const images = await Promise.all(
      imageSegments.map(async (segment, index) => {
        const resolved = params.resolvedMedia[index];
        if (resolved?.localPath) {
          return await describeQqImageWithModel({
            cfg: params.cfg,
            agentId: params.agentId,
            filePath: resolved.localPath,
            sourceUrl: resolved.sourceUrl || segment.url,
            contentType: resolved.contentType,
            index: index + 1,
            logger: params.logger,
          });
        }
        return {
          index: index + 1,
          ocr: "",
          alt: `图片${index + 1}`,
          vision_summary: "这是一张图片，具体内容暂时没拿稳。",
          url: resolved?.sourceUrl || segment.url,
          path: resolved?.localPath,
          mime: resolved?.contentType,
        };
      }),
    );
    const replaySegments = imageSegments
      .map((segment, index) => {
        const resolved = params.resolvedMedia[index];
        const file =
          resolved?.localPath ??
          resolved?.sourceUrl ??
          segment.url ??
          (typeof segment.data?.file === "string" ? segment.data.file : "");
        if (!file) {
          return null;
        }
        return {
          type: "image",
          data: { file },
        } satisfies OneBotMessageSegment;
      })
      .filter((segment): segment is OneBotMessageSegment => Boolean(segment));
    records.push({
      id: `${params.source}:${params.messageId ?? "no-message"}:image:${params.createdAt}`,
      source: params.source,
      message_id: params.messageId,
      sender_id: params.senderId,
      sender_name: params.senderName,
      type: "image",
      caption: params.caption,
      quoted_text: params.quotedText,
      reply_to: params.replyTo,
      image_count: images.length,
      images,
      replay_segments: replaySegments.length > 0 ? replaySegments : undefined,
      summary: images
        .map((image) => image.alt || image.vision_summary)
        .filter(Boolean)
        .join("；"),
      created_at: params.createdAt,
    });
  }
  const emojiSegments = params.parsed.mediaSegments.filter((segment) => segment.type !== "image");
  if (emojiSegments.length > 0) {
    const groupedImages = emojiSegments.map((segment, index) => ({
      index: index + 1,
      ocr: "",
      alt: segment.label ?? (segment.type === "animated_emoji" ? "动画表情" : "QQ表情"),
      vision_summary: segment.label ?? (segment.type === "animated_emoji" ? "动画表情" : "QQ表情"),
      url: segment.url,
      path: undefined,
      mime: undefined,
    }));
    const recordType = emojiSegments.some((segment) => segment.type === "animated_emoji")
      ? "animated_emoji"
      : "emoji";
    records.push({
      id: `${params.source}:${params.messageId ?? "no-message"}:${recordType}:${params.createdAt}`,
      source: params.source,
      message_id: params.messageId,
      sender_id: params.senderId,
      sender_name: params.senderName,
      type: recordType,
      caption: params.caption,
      quoted_text: params.quotedText,
      reply_to: params.replyTo,
      image_count: groupedImages.length,
      images: groupedImages,
      replay_segments: emojiSegments.map((segment) => ({
        type: segment.sourceType,
        data: segment.data,
      })),
      summary: groupedImages.map((image) => image.alt).join("；"),
      created_at: params.createdAt,
    });
  }
  return records;
}

async function resolveQqReplyTarget(params: {
  api: OpenClawPluginApi;
  cfg: OpenClawConfig;
  account: ResolvedQqAccount;
  routeAgentId: string;
  conversationKey: string;
  replyToMessageId?: string;
}): Promise<QqReplyTarget | null> {
  const replyToMessageId = params.replyToMessageId?.trim();
  if (!replyToMessageId) {
    return null;
  }
  const state = getQqConversationState(params.conversationKey);
  const bufferedMessage = state.recentMessages.find((entry) => entry.id === replyToMessageId);
  if (bufferedMessage) {
    recordQqDebugEvent({
      api: params.api,
      conversationKey: params.conversationKey,
      kind: "reply_target_resolve",
      detail: {
        replyToMessageId,
        strategy: "buffer-hit",
        mediaCount: 0,
        resolvedMessageId: replyToMessageId,
        senderId: bufferedMessage?.senderId ?? "",
        senderName: bufferedMessage?.senderName ?? "",
        replyTextPreview: previewText(bufferedMessage?.text ?? "", 100),
        mediaSummary: "",
      },
    });
    return {
      messageId: replyToMessageId,
      senderId: bufferedMessage?.senderId,
      senderName: bufferedMessage?.senderName,
      text: bufferedMessage?.text,
    };
  }
  const fetched = await getQqMessageById({
    cfg: params.cfg as CoreConfig,
    accountId: params.account.accountId,
    messageId: replyToMessageId,
  });
  if (!fetched) {
    recordQqDebugEvent({
      api: params.api,
      conversationKey: params.conversationKey,
      kind: "reply_target_resolve",
      detail: {
        replyToMessageId,
        strategy: "miss",
        resolvedMessageId: "",
      },
    });
    return null;
  }
  if (fetched.messageId) {
    rememberQqMessageRecord(params.conversationKey, {
      id: fetched.messageId,
      senderId: fetched.senderId ?? "unknown",
      senderName: fetched.senderName,
      text: fetched.text,
      createdAt: fetched.timestamp ?? Date.now(),
      wasMentioned: false,
      isReply: fetched.parsed.isReply,
      replyToMessageId: fetched.parsed.replyToMessageId,
      explicitInstruction: looksLikeQqExplicitInstruction(fetched.text),
      mediaIds: [],
      direction: "inbound",
    });
  }
  recordQqDebugEvent({
    api: params.api,
    conversationKey: params.conversationKey,
    kind: "reply_target_resolve",
    detail: {
      replyToMessageId,
      strategy: "onebot-get_msg",
      mediaCount: 0,
      resolvedMessageId: fetched.messageId ?? "",
      senderId: fetched.senderId ?? "",
      senderName: fetched.senderName ?? "",
      replyTextPreview: previewText(fetched.text, 100),
      mediaSummary: "",
    },
  });
  return {
    messageId: fetched.messageId,
    senderId: fetched.senderId,
    senderName: fetched.senderName,
    text: fetched.text,
  };
}

function resolveQqBoundMedia(params: {
  api: OpenClawPluginApi;
  conversationKey: string;
  focusEntry: QueuedQqInboundEvent;
  currentMedia: QqMediaRecord[];
  replyTarget: QqReplyTarget | null;
}): { record: QqMediaRecord; source: string } | null {
  const focusMessageId = params.focusEntry.event.message_id
    ? String(params.focusEntry.event.message_id)
    : undefined;
  const focusCurrentMedia = params.currentMedia.filter(
    (entry) => entry.message_id === focusMessageId,
  );
  if (focusCurrentMedia.length > 0) {
    recordQqDebugEvent({
      api: params.api,
      conversationKey: params.conversationKey,
      kind: "media_resolve",
      detail: {
        strategy: "current-message",
        messageId: focusMessageId,
        mediaId: focusCurrentMedia[0]?.id,
        focusPreview: previewText(
          params.focusEntry.rawBody || summarizeQqMediaPlaceholder(params.focusEntry.parsed),
          100,
        ),
        boundSummary: summarizeQqMediaDebugRecord(focusCurrentMedia[0]),
      },
    });
    return { record: focusCurrentMedia[0]!, source: "current-message" };
  }
  if (params.replyTarget?.media?.length) {
    recordQqDebugEvent({
      api: params.api,
      conversationKey: params.conversationKey,
      kind: "media_resolve",
      detail: {
        strategy: "reply_to",
        messageId: params.replyTarget.messageId,
        mediaId: params.replyTarget.media[0]?.id,
        focusPreview: previewText(
          params.focusEntry.rawBody || summarizeQqMediaPlaceholder(params.focusEntry.parsed),
          100,
        ),
        boundSummary: summarizeQqMediaDebugRecord(params.replyTarget.media[0]),
      },
    });
    return { record: params.replyTarget.media[0]!, source: "reply_to" };
  }
  const recentCurrentMedia = [...params.currentMedia]
    .filter((entry) => entry.created_at <= params.focusEntry.timestamp)
    .sort((left, right) => right.created_at - left.created_at);
  if (looksLikeQqMediaReference(params.focusEntry.rawBody) && recentCurrentMedia.length > 0) {
    recordQqDebugEvent({
      api: params.api,
      conversationKey: params.conversationKey,
      kind: "media_resolve",
      detail: {
        strategy: "current-burst",
        messageId: recentCurrentMedia[0]?.message_id,
        mediaId: recentCurrentMedia[0]?.id,
        focusPreview: previewText(
          params.focusEntry.rawBody || summarizeQqMediaPlaceholder(params.focusEntry.parsed),
          100,
        ),
        boundSummary: summarizeQqMediaDebugRecord(recentCurrentMedia[0]),
      },
    });
    return { record: recentCurrentMedia[0]!, source: "current-burst" };
  }
  if (looksLikeQqMediaReference(params.focusEntry.rawBody)) {
    const recent = matchRecentQqMedia({
      conversationKey: params.conversationKey,
      text: params.focusEntry.rawBody,
      preferOutbound: /你刚发|再来一张|不是这张/u.test(params.focusEntry.rawBody),
    });
    if (recent) {
      recordQqDebugEvent({
        api: params.api,
        conversationKey: params.conversationKey,
        kind: "media_resolve",
        detail: {
          strategy: "recent_media_buffer",
          mediaId: recent.id,
          messageId: recent.message_id,
          query: normalizeQqMediaQuery(params.focusEntry.rawBody),
          focusPreview: previewText(
            params.focusEntry.rawBody || summarizeQqMediaPlaceholder(params.focusEntry.parsed),
            100,
          ),
          boundSummary: summarizeQqMediaDebugRecord(recent),
        },
      });
      return { record: recent, source: "recent_media_buffer" };
    }
  }
  return null;
}

function toQqMediaPromptRecord(record: QqMediaRecord): Record<string, unknown> {
  return {
    type: record.type,
    caption: record.caption,
    quoted_text: record.quoted_text ?? "",
    reply_to: record.reply_to ?? null,
    image_count: record.image_count,
    summary: record.summary,
    images: (record.images ?? []).map((image) => ({
      index: image.index,
      ocr: image.ocr,
      alt: image.alt,
      vision_summary: image.vision_summary,
    })),
  };
}

function buildQqRecentMediaPrompt(
  conversationKey: string,
  excludeMediaId?: string,
): string | undefined {
  const items = getQqConversationState(conversationKey)
    .recentMediaBuffer.filter((entry) => entry.id !== excludeMediaId)
    .slice(0, 8)
    .map((entry) => ({
      type: entry.type,
      message_id: entry.message_id,
      sender: entry.sender_name ?? entry.sender_id ?? "",
      caption: entry.caption,
      summary: entry.summary,
      image_count: entry.image_count,
    }));
  if (items.length === 0) {
    return undefined;
  }
  return JSON.stringify(items, null, 2);
}

function buildQqAgentBody(params: {
  focusEntry: QueuedQqInboundEvent;
  burstContext?: string;
  currentMedia: QqMediaRecord[];
  boundMedia: { record: QqMediaRecord; source: string } | null;
  replyTarget: QqReplyTarget | null;
  conversationKey: string;
  socialAgencyPlan?: QqSocialAgencyPlan | null;
}): string {
  const state = refreshQqConversationLoad(params.conversationKey);
  const blocks: string[] = [];
  const focusText =
    params.focusEntry.rawBody || summarizeQqMediaPlaceholder(params.focusEntry.parsed);
  blocks.push(`[QQCurrentRequest]\n${focusText}\n[/QQCurrentRequest]`);
  if (params.burstContext) {
    blocks.push(`[QQBurstContext]\n${params.burstContext}\n[/QQBurstContext]`);
  }
  const currentMediaForPrompt = params.currentMedia.slice(0, QQ_CURRENT_MEDIA_PROMPT_LIMIT);
  if (currentMediaForPrompt.length > 0) {
    blocks.push(
      `[QQCurrentTurnMedia]\n${JSON.stringify(
        currentMediaForPrompt.map((entry) => toQqMediaPromptRecord(entry)),
        null,
        2,
      )}\n[/QQCurrentTurnMedia]`,
    );
  }
  if (params.boundMedia?.record) {
    blocks.push(
      `[QQBoundMedia]\n${JSON.stringify(
        {
          binding_source: params.boundMedia.source,
          ...toQqMediaPromptRecord(params.boundMedia.record),
        },
        null,
        2,
      )}\n[/QQBoundMedia]`,
    );
  }
  if (params.replyTarget?.messageId || params.replyTarget?.text) {
    blocks.push(
      `[QQReplyTarget]\n${JSON.stringify(
        {
          message_id: params.replyTarget.messageId ?? "",
          sender: params.replyTarget.senderName ?? params.replyTarget.senderId ?? "",
          text: params.replyTarget.text ?? "",
        },
        null,
        2,
      )}\n[/QQReplyTarget]`,
    );
  }
  if (params.socialAgencyPlan?.opportunity) {
    blocks.push(
      `[QQSocialAgency]\n${JSON.stringify(
        buildQqSocialAgencyPromptRecord(params.socialAgencyPlan),
        null,
        2,
      )}\n[/QQSocialAgency]`,
    );
  }
  blocks.push(
    `[QQReplyState]\n${JSON.stringify(
      {
        busy_level: state.busyLevel,
        pending_count: state.pendingCount,
        last_replied_message_id: state.lastRepliedMessageId ?? "",
      },
      null,
      2,
    )}\n[/QQReplyState]`,
  );
  return blocks.join("\n\n");
}

function buildQqDebugInjectionSummary(params: {
  conversationKey: string;
  focusEntry: QueuedQqInboundEvent;
  rawBody: string;
  burstContext?: string;
  currentMedia?: QqMediaRecord[];
  boundMedia?: { record: QqMediaRecord; source: string } | null;
  replyTarget?: QqReplyTarget | null;
  state: QqConversationState;
  globalLoadOverride?: { totalPendingCount: number; competingConversationCount: number };
  action: QqDebugInjectionSummary["decision"]["action"];
  mode: string;
  reason?: string;
  agentBody?: string;
}): QqDebugInjectionSummary {
  const load = buildQqLoadDebugFields(params.conversationKey, params.globalLoadOverride);
  return {
    ok: true,
    dry_run: true,
    debug_log_path: QQ_DEBUG_LOG_PATH,
    conversation_key: params.conversationKey,
    focus_message_id: params.focusEntry.event.message_id
      ? String(params.focusEntry.event.message_id)
      : undefined,
    raw_body: params.rawBody,
    burst_context: params.burstContext,
    decision: {
      action: params.action,
      mode: params.mode,
      stage: inferQqDecisionStage({
        action: params.action,
        mode: params.mode,
      }),
      reason: params.reason,
    },
    state: {
      busy_level: params.state.busyLevel,
      pending_count: params.state.pendingCount,
      last_replied_message_id: params.state.lastRepliedMessageId,
      competing_conversation_count: load.competingConversationCount,
      total_pending_count: load.totalPendingCount,
    },
    bound_media: params.boundMedia
      ? {
          binding_source: params.boundMedia.source,
          ...toQqMediaPromptRecord(params.boundMedia.record),
        }
      : null,
    reply_target: params.replyTarget
      ? {
          message_id: params.replyTarget.messageId ?? "",
          sender: params.replyTarget.senderName ?? params.replyTarget.senderId ?? "",
          text: params.replyTarget.text ?? "",
        }
      : null,
    current_turn_media: (params.currentMedia ?? []).map((entry) => toQqMediaPromptRecord(entry)),
    agent_body: params.agentBody,
  };
}

async function flushQueuedQqInboundEvents(conversationKey: string) {
  const pending = qqPendingBursts.get(conversationKey);
  if (!pending) {
    refreshQqConversationLoad(conversationKey);
    return;
  }
  qqPendingBursts.delete(conversationKey);
  if (pending.timer) {
    clearTimeout(pending.timer);
  }
  refreshQqConversationLoad(conversationKey);
  const last = pending.entries.at(-1);
  if (!last) {
    return;
  }
  await processQueuedQqInboundEvents({
    api: last.api,
    account: last.account,
    conversationKey,
    entries: pending.entries,
  });
}

async function enqueueQqInboundEvent(entry: QueuedQqInboundEvent) {
  const conversationKey = buildQqConversationKey(entry.account.accountId, entry.event);
  const existing = qqPendingBursts.get(conversationKey);
  if (existing && entry.timestamp - existing.startedAt > existing.burstWindowMs) {
    void flushQueuedQqInboundEvents(conversationKey);
  }
  const next = qqPendingBursts.get(conversationKey) ?? {
    entries: [],
    startedAt: entry.timestamp,
    burstWindowMs: entry.burstWindowMs ?? QQ_BURST_WINDOW_MS,
    studyImageAckSent: false,
    studyFollowupAckSent: false,
  };
  next.burstWindowMs = Math.max(next.burstWindowMs, entry.burstWindowMs ?? QQ_BURST_WINDOW_MS);
  if (entry.parsed.mediaSegments.some((segment) => segment.type === "image")) {
    next.studyImageAckSent = true;
  }
  next.entries.push(entry);
  if (next.timer) {
    clearTimeout(next.timer);
  }
  next.timer = setTimeout(() => {
    void flushQueuedQqInboundEvents(conversationKey);
  }, entry.burstIdleMs ?? QQ_BURST_IDLE_MS);
  next.timer.unref?.();
  qqPendingBursts.set(conversationKey, next);
  refreshQqConversationLoad(conversationKey);
}

async function processQueuedQqInboundEvents(params: {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  conversationKey: string;
  entries: QueuedQqInboundEvent[];
  disableStaleGate?: boolean;
  recoveryReplyToLatestMessage?: boolean;
  debugDryRun?: boolean;
}): Promise<QqDebugInjectionSummary | void> {
  const { api, account, conversationKey, entries } = params;
  if (entries.length === 0) {
    return;
  }
  const runtime = getQqRuntime();
  const cfg = runtime.config.loadConfig() as OpenClawConfig;
  const focusEntry = selectQqBurstFocusEntry(entries);
  const { retained, omittedCount, compacted } = compactQqBurstEntries(entries);
  const burstContext = formatQqBurstContext({ entries: retained, omittedCount });
  if (entries.length >= QQ_BURST_THRESHOLD || compacted || omittedCount > 0) {
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "burst_compaction",
      detail: {
        entryCount: entries.length,
        retainedCount: retained.length,
        omittedCount,
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        focusPreview: previewText(
          focusEntry.rawBody || summarizeQqMediaPlaceholder(focusEntry.parsed),
          100,
        ),
        entriesPreview: retained.map((entry) => buildQqBurstEntryDebugPreview(entry)),
      },
    });
  }

  const isGroup = focusEntry.event.message_type === "group";
  const groupId = isGroup ? String(focusEntry.event.group_id ?? "") : undefined;
  const senderId = String(focusEntry.event.user_id);
  const messageTimestamp = focusEntry.timestamp;
  const rawBody = focusEntry.rawBody || summarizeQqMediaPlaceholder(focusEntry.parsed);
  if (!rawBody && focusEntry.parsed.mediaSegments.length === 0) {
    return;
  }

  const route = runtime.channel.routing.resolveAgentRoute({
    cfg,
    channel: CHANNEL_ID,
    accountId: account.accountId,
    peer: {
      kind: isGroup ? "group" : "direct",
      id: isGroup ? String(groupId) : senderId,
    },
  });
  await rememberQqLightweightInboundMedia({
    cfg,
    routeAgentId: route.agentId,
    conversationKey,
    retained,
    logger: api.logger,
  });

  const mergedParsed: ParsedQqMessage = {
    text: focusEntry.parsed.text,
    isReply: retained.some((entry) => entry.parsed.isReply),
    replyToMessageId:
      focusEntry.parsed.replyToMessageId ??
      retained.find((entry) => entry.parsed.replyToMessageId)?.parsed.replyToMessageId,
    wasMentioned: retained.some((entry) => entry.parsed.wasMentioned),
    mentionIds: [...new Set(retained.flatMap((entry) => entry.parsed.mentionIds))],
    imageUrls: retained.flatMap((entry) => entry.parsed.imageUrls),
    mediaSegments: retained.flatMap((entry) => entry.parsed.mediaSegments),
    hasOnlyMediaLike: retained.every((entry) => entry.parsed.hasOnlyMediaLike),
  };
  for (const entry of retained) {
    const messageId = entry.event.message_id ? String(entry.event.message_id) : undefined;
    rememberQqMessageRecord(conversationKey, {
      id: messageId,
      senderId: entry.senderId,
      senderName: entry.senderName,
      text: entry.rawBody || summarizeQqMediaPlaceholder(entry.parsed),
      createdAt: entry.timestamp,
      wasMentioned: entry.parsed.wasMentioned,
      isReply: entry.parsed.isReply,
      replyToMessageId: entry.parsed.replyToMessageId,
      explicitInstruction: looksLikeQqExplicitInstruction(entry.rawBody),
      mediaIds: [],
      direction: "inbound",
    });
  }

  let inboundMediaPayload: ResolvedInboundMediaPayload = { payload: {}, resolvedMedia: [] };
  let currentMedia: QqMediaRecord[] = [];
  let replyTarget: QqReplyTarget | null = null;
  let boundMedia: { record: QqMediaRecord; source: string } | null = null;
  const state = refreshQqConversationLoad(conversationKey);
  const conversationStyleState = isGroup ? readQqConversationStyleState(cfg, groupId) : null;
  const studyModeSystemPrompt = buildQqStudyModeSystemPrompt({
    account,
    chatType: isGroup ? "group" : "direct",
    hasImage: mergedParsed.mediaSegments.some((segment) => segment.type === "image"),
  });
  const socialAgencyGroupDir =
    conversationStyleState?.dirPath && !conversationStyleState.dirPath.startsWith("__builtin__/")
      ? conversationStyleState.dirPath
      : null;
  if (socialAgencyGroupDir && groupId) {
    ensureDefaultQqSocialAgencyFiles(socialAgencyGroupDir, groupId);
  }

  const naturalChatSettings = resolveQqNaturalChatConfig({
    account,
    groupId,
    chatType: isGroup ? "group" : "direct",
  });
  const personaCommand = naturalChatSettings.allowPersonaSwitch
    ? parseQqPersonaCommand({
        rawBody,
        selfId: account.selfId ?? String(focusEntry.event.self_id),
      })
    : null;
  const currentPersona = resolveQqPersonaProfile({
    account,
    groupId,
    chatType: isGroup ? "group" : "direct",
  });
  const explicitImageIntent =
    !isGroup || mergedParsed.wasMentioned || mergedParsed.isReply
      ? detectQqExplicitImageIntent({
          rawBody,
          selfId: account.selfId ?? String(focusEntry.event.self_id),
        })
      : null;
  const refreshImmediateConversationWatch = (replyText: string) => {
    if (isGroup && (mergedParsed.wasMentioned || mergedParsed.isReply)) {
      touchDirectFollowupWatch({
        accountId: account.accountId,
        groupId,
        senderId,
        now: messageTimestamp,
        rawBody,
      });
      noteDirectFollowupReply({
        accountId: account.accountId,
        groupId,
        senderId,
        now: Date.now(),
        replyText,
      });
    }
  };
  if (explicitImageIntent?.kind === "search") {
    const imageResult = await searchQqImageToLocalFile({
      query: explicitImageIntent.query,
      selectionKey: `explicit:${explicitImageIntent.query}`,
    }).catch(() => null);
    if (imageResult?.mediaUrl) {
      recordQqDebugEvent({
        api,
        conversationKey,
        kind: "dispatch_gate",
        detail: {
          action: "dispatch_immediate",
          mode: "explicit_image_search",
          focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
          rawBodyPreview: previewText(rawBody, 120),
          pendingCount: state.pendingCount,
          busyLevel: state.busyLevel,
        },
      });
      if (params.debugDryRun) {
        return buildQqDebugInjectionSummary({
          conversationKey,
          focusEntry,
          rawBody,
          burstContext,
          currentMedia,
          boundMedia,
          replyTarget,
          state,
          action: "dispatch_immediate",
          mode: "explicit_image_search",
          reason: explicitImageIntent.query,
        });
      }
      await sendImmediateQqMediaReply({
        cfg,
        accountId: account.accountId,
        event: focusEntry.event,
        text: explicitImageIntent.caption,
        mediaUrl: imageResult.mediaUrl,
        conversationKey,
        agentId: route.agentId,
      });
      refreshImmediateConversationWatch(explicitImageIntent.caption);
      return;
    }
  }
  const canHandlePersonaCommand =
    personaCommand && (!isGroup || mergedParsed.wasMentioned || mergedParsed.isReply);
  if (canHandlePersonaCommand && qqStateDirForRecovery) {
    if (personaCommand.kind === "current") {
      recordQqDebugEvent({
        api,
        conversationKey,
        kind: "dispatch_gate",
        detail: {
          action: "dispatch_immediate",
          mode: "persona_current",
          focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
          rawBodyPreview: previewText(rawBody, 120),
          pendingCount: state.pendingCount,
          busyLevel: state.busyLevel,
        },
      });
      if (params.debugDryRun) {
        return buildQqDebugInjectionSummary({
          conversationKey,
          focusEntry,
          rawBody,
          burstContext,
          currentMedia,
          boundMedia,
          replyTarget,
          state,
          action: "dispatch_immediate",
          mode: "persona_current",
        });
      }
      await sendImmediateQqTextReply({
        cfg: cfg as CoreConfig,
        accountId: account.accountId,
        event: focusEntry.event,
        text: `现在是 ${currentPersona.label}`,
        conversationKey,
      });
      refreshImmediateConversationWatch(`现在是 ${currentPersona.label}`);
      return;
    }
    if (personaCommand.kind === "list") {
      const personaList = `可用人设 ${qqPersonaProfiles.map((profile) => profile.label).join(" ")}`;
      recordQqDebugEvent({
        api,
        conversationKey,
        kind: "dispatch_gate",
        detail: {
          action: "dispatch_immediate",
          mode: "persona_list",
          focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
          rawBodyPreview: previewText(rawBody, 120),
          pendingCount: state.pendingCount,
          busyLevel: state.busyLevel,
        },
      });
      if (params.debugDryRun) {
        return buildQqDebugInjectionSummary({
          conversationKey,
          focusEntry,
          rawBody,
          burstContext,
          currentMedia,
          boundMedia,
          replyTarget,
          state,
          action: "dispatch_immediate",
          mode: "persona_list",
        });
      }
      await sendImmediateQqTextReply({
        cfg: cfg as CoreConfig,
        accountId: account.accountId,
        event: focusEntry.event,
        text: personaList,
        conversationKey,
      });
      refreshImmediateConversationWatch(personaList);
      return;
    }
    if (personaCommand.kind === "switch") {
      const nextPersona = setQqPersonaProfile({
        stateDir: qqStateDirForRecovery,
        accountId: account.accountId,
        personaId: personaCommand.personaId,
      });
      if (nextPersona) {
        const replyText = `好 现在切到 ${nextPersona.label}`;
        recordQqDebugEvent({
          api,
          conversationKey,
          kind: "dispatch_gate",
          detail: {
            action: "dispatch_immediate",
            mode: "persona_switch",
            focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
            rawBodyPreview: previewText(rawBody, 120),
            pendingCount: state.pendingCount,
            busyLevel: state.busyLevel,
          },
        });
        if (params.debugDryRun) {
          return buildQqDebugInjectionSummary({
            conversationKey,
            focusEntry,
            rawBody,
            burstContext,
            currentMedia,
            boundMedia,
            replyTarget,
            state,
            action: "dispatch_immediate",
            mode: "persona_switch",
          });
        }
        await sendImmediateQqTextReply({
          cfg: cfg as CoreConfig,
          accountId: account.accountId,
          event: focusEntry.event,
          text: replyText,
          conversationKey,
        });
        refreshImmediateConversationWatch(replyText);
        return;
      }
    }
    if (personaCommand.kind === "invalid") {
      const replyText = "这个人设名我还不认识 可用的是 智乃 Miko";
      recordQqDebugEvent({
        api,
        conversationKey,
        kind: "dispatch_gate",
        detail: {
          action: "dispatch_immediate",
          mode: "persona_invalid",
          focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
          rawBodyPreview: previewText(rawBody, 120),
          pendingCount: state.pendingCount,
          busyLevel: state.busyLevel,
        },
      });
      if (params.debugDryRun) {
        return buildQqDebugInjectionSummary({
          conversationKey,
          focusEntry,
          rawBody,
          burstContext,
          currentMedia,
          boundMedia,
          replyTarget,
          state,
          action: "dispatch_immediate",
          mode: "persona_invalid",
        });
      }
      await sendImmediateQqTextReply({
        cfg: cfg as CoreConfig,
        accountId: account.accountId,
        event: focusEntry.event,
        text: replyText,
        conversationKey,
      });
      refreshImmediateConversationWatch(replyText);
      return;
    }
  }

  const shouldHandleIdentityQuestion =
    isQqPersonaIdentityQuestion({
      rawBody,
      selfId: account.selfId ?? String(focusEntry.event.self_id),
    }) &&
    (!isGroup || mergedParsed.wasMentioned || mergedParsed.isReply);
  if (shouldHandleIdentityQuestion) {
    const replyText = buildQqPersonaIdentityReply({
      persona: currentPersona,
      rawBody,
      selfId: account.selfId ?? String(focusEntry.event.self_id),
    });
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "dispatch_immediate",
        mode: "identity_question",
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        pendingCount: state.pendingCount,
        busyLevel: state.busyLevel,
      },
    });
    if (params.debugDryRun) {
      return buildQqDebugInjectionSummary({
        conversationKey,
        focusEntry,
        rawBody,
        burstContext,
        currentMedia,
        boundMedia,
        replyTarget,
        state,
        action: "dispatch_immediate",
        mode: "identity_question",
      });
    }
    await sendImmediateQqTextReply({
      cfg: cfg as CoreConfig,
      accountId: account.accountId,
      event: focusEntry.event,
      text: replyText,
      conversationKey,
    });
    refreshImmediateConversationWatch(replyText);
    return;
  }

  const schedulingDecision = resolveQqSchedulingDecision({
    conversationKey,
    isGroup,
    rawBody,
    parsed: mergedParsed,
    busyLevel: state.busyLevel,
    pendingCount: state.pendingCount,
    messageTimestamp,
    disableStaleGate: params.disableStaleGate,
  });
  if (schedulingDecision.skip && schedulingDecision.mode === "overload_gate") {
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "skip",
        mode: schedulingDecision.mode,
        reason: schedulingDecision.reason,
        fairnessClass: schedulingDecision.fairnessClass,
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        pendingCount: state.pendingCount,
        busyLevel: state.busyLevel,
      },
    });
    if (params.debugDryRun) {
      return buildQqDebugInjectionSummary({
        conversationKey,
        focusEntry,
        rawBody,
        burstContext,
        currentMedia,
        boundMedia,
        replyTarget,
        state,
        action: "skip",
        mode: schedulingDecision.mode,
        reason: schedulingDecision.reason,
      });
    }
    return;
  }
  if (schedulingDecision.skip && schedulingDecision.mode === "fairness_gate") {
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "skip",
        mode: schedulingDecision.mode,
        reason: schedulingDecision.reason,
        fairnessClass: schedulingDecision.fairnessClass,
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        pendingCount: state.pendingCount,
        busyLevel: state.busyLevel,
        competingConversationCount: schedulingDecision.competingConversationCount,
        totalPendingCount: schedulingDecision.totalPendingCount,
      },
    });
    if (params.debugDryRun) {
      return buildQqDebugInjectionSummary({
        conversationKey,
        focusEntry,
        rawBody,
        burstContext,
        currentMedia,
        boundMedia,
        replyTarget,
        state,
        action: "skip",
        mode: schedulingDecision.mode,
        reason: schedulingDecision.reason,
      });
    }
    return;
  }
  if (schedulingDecision.skip && schedulingDecision.mode === "stale_gate") {
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "skip",
        mode: schedulingDecision.mode,
        reason: schedulingDecision.reason,
        fairnessClass: schedulingDecision.fairnessClass,
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        ageMs: schedulingDecision.ageMs,
        staleThresholdMs: schedulingDecision.staleThresholdMs,
        pendingCount: state.pendingCount,
        busyLevel: state.busyLevel,
      },
    });
    if (params.debugDryRun) {
      return buildQqDebugInjectionSummary({
        conversationKey,
        focusEntry,
        rawBody,
        burstContext,
        currentMedia,
        boundMedia,
        replyTarget,
        state,
        action: "skip",
        mode: schedulingDecision.mode,
        reason: schedulingDecision.reason,
      });
    }
    return;
  }

  const storePath = runtime.channel.session.resolveStorePath(
    (cfg.session as Record<string, unknown> | undefined)?.store as string | undefined,
    { agentId: route.agentId },
  );
  const rolloverResult = isGroup
    ? maybeMarkQqSessionForRollover({
        api,
        storePath,
        sessionKey: route.sessionKey,
        conversationKey,
      })
    : { rolledOver: false, lineCount: 0 };
  if (rolloverResult.rolledOver) {
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "dispatch",
        mode: "session_rollover",
        reason: `transcript-too-deep:${rolloverResult.lineCount}`,
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        pendingCount: state.pendingCount,
        busyLevel: state.busyLevel,
      },
    });
  }
  const previousTimestamp = runtime.channel.session.readSessionUpdatedAt({
    storePath,
    sessionKey: route.sessionKey,
  });
  const socialAgencyPlan =
    isGroup && groupId
      ? buildQqSocialAgencyPlan({
          groupProfile: {
            groupId,
            groupDir: socialAgencyGroupDir,
            selfPosition: conversationStyleState?.selfPosition,
            appraisal: conversationStyleState?.appraisal,
          },
          senderId,
          senderName: focusEntry.senderName,
          senderProfile: resolveQqAgencySenderProfile(socialAgencyGroupDir, senderId),
          rawBody,
          parsed: mergedParsed,
          recentMessages: state.recentMessages.slice(-14),
          nowMs: messageTimestamp,
        })
      : null;
  if (isGroup && (mergedParsed.wasMentioned || mergedParsed.isReply)) {
    touchDirectFollowupWatch({
      accountId: account.accountId,
      groupId,
      senderId,
      now: messageTimestamp,
      rawBody,
    });
  }

  const requireMention =
    isGroup && (resolveGroupConfig(account, groupId)?.requireMention ?? true) === true;
  const socialJoinRaw = shouldAllowSocialJoin({
    cfg,
    account,
    groupId,
    rawBody,
    parsed: mergedParsed,
    previousTimestamp,
  });
  const socialJoin =
    socialJoinRaw.allowed && state.pendingCount >= 3
      ? { allowed: false, reason: `busy-${state.busyLevel}` }
      : !socialJoinRaw.allowed &&
          socialAgencyPlan?.allowAmbientJoin &&
          state.pendingCount < 3 &&
          resolveGroupConfig(account, groupId)?.socialJoinEnabled === true
        ? {
            allowed: true,
            reason: `social-agency-${socialAgencyPlan.opportunity?.type ?? socialAgencyPlan.mode}`,
          }
        : socialJoinRaw;
  const followupWatch = isGroup
    ? evaluateDirectFollowupWatch({
        accountId: account.accountId,
        groupId,
        senderId,
        rawBody,
        parsed: mergedParsed,
        selfId: account.selfId ?? String(focusEntry.event.self_id),
        now: messageTimestamp,
      })
    : { allowed: false, reason: "not-group" };
  const semanticFollowup =
    isGroup &&
    !mergedParsed.wasMentioned &&
    !mergedParsed.isReply &&
    !socialJoin.allowed &&
    !followupWatch.allowed &&
    followupWatch.reason === "watch-followup-unrelated" &&
    Number(followupWatch.score ?? 0) >= DIRECT_FOLLOWUP_SEMANTIC_MIN_RULE_SCORE &&
    followupWatch.state
      ? await semanticJudgeDirectFollowup({
          cfg,
          state: followupWatch.state,
          senderId,
          senderName: focusEntry.senderName,
          groupId,
          rawBody,
          now: messageTimestamp,
        }).catch((error) => {
          api.logger.warn(`[qq] semantic followup judge failed: ${String(error)}`);
          return { allowed: false, confidence: 0, reason: "semantic-error" };
        })
      : { allowed: false, confidence: 0, reason: "semantic-not-needed" };
  if (semanticFollowup.allowed) {
    touchDirectFollowupWatch({
      accountId: account.accountId,
      groupId,
      senderId,
      now: messageTimestamp,
      rawBody,
    });
  }
  const currentTurnMemeBaseImage = resolveQqCurrentTurnMemeBaseImage({
    currentMedia,
    boundMedia,
  });
  if (
    params.debugDryRun &&
    socialAgencyPlan?.selectedRecipe &&
    (socialAgencyPlan.mode === "play_reply" ||
      socialAgencyPlan.mode === "light_surprise" ||
      socialAgencyPlan.mode === "staged_surprise")
  ) {
    return buildQqDebugInjectionSummary({
      conversationKey,
      focusEntry,
      rawBody,
      burstContext,
      currentMedia,
      boundMedia,
      replyTarget,
      state,
      action: "dispatch_immediate",
      mode: `social_agency_${socialAgencyPlan.selectedRecipe.recipe.id}`,
      reason: socialAgencyPlan.selectedRecipe.recipe.id,
    });
  }
  if (
    socialAgencyPlan &&
    (socialAgencyPlan.mode === "play_reply" ||
      socialAgencyPlan.mode === "light_surprise" ||
      socialAgencyPlan.mode === "staged_surprise")
  ) {
    const handledBySocialAgency = await tryHandleImmediateQqSocialAgencyRecipe({
      api,
      cfg,
      accountId: account.accountId,
      event: focusEntry.event,
      conversationKey,
      agentId: route.agentId,
      groupId,
      groupDir: socialAgencyGroupDir,
      senderId,
      rawBody,
      senderName: focusEntry.senderName,
      recentMessages: state.recentMessages.slice(-16),
      currentTurnMemeBaseImage,
      socialAgencyPlan,
      pendingCount: state.pendingCount,
    }).catch((error) => {
      api.logger.warn(`[qq] social agency immediate handler failed: ${String(error)}`);
      return false;
    });
    if (handledBySocialAgency) {
      return;
    }
  }
  if (
    requireMention &&
    !mergedParsed.wasMentioned &&
    !mergedParsed.isReply &&
    !socialJoin.allowed &&
    !followupWatch.allowed &&
    !semanticFollowup.allowed
  ) {
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "skip",
        mode: "mention_gate",
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        requireMention,
        wasMentioned: mergedParsed.wasMentioned,
        isReply: mergedParsed.isReply,
        socialJoinAllowed: socialJoin.allowed,
        socialJoinReason: socialJoin.reason,
        followupAllowed: followupWatch.allowed,
        followupReason: followupWatch.reason,
        semanticAllowed: semanticFollowup.allowed,
        semanticReason: semanticFollowup.reason,
        fairnessClass: schedulingDecision.fairnessClass,
        pendingCount: state.pendingCount,
        busyLevel: state.busyLevel,
      },
    });
    api.logger.debug(
      `[qq] skipping group message without bot mention: group=${groupId} user=${senderId} reason=${socialJoin.reason} followup=${followupWatch.reason} semantic=${semanticFollowup.reason}`,
    );
    if (params.debugDryRun) {
      return buildQqDebugInjectionSummary({
        conversationKey,
        focusEntry,
        rawBody,
        burstContext,
        currentMedia,
        boundMedia,
        replyTarget,
        state,
        action: "skip",
        mode: "mention_gate",
        reason: `${socialJoin.reason}|${followupWatch.reason}|${semanticFollowup.reason}`,
      });
    }
    return;
  }

  ({ inboundMediaPayload, currentMedia, replyTarget, boundMedia } =
    await prepareQqInboundMediaContext({
      api,
      runtime,
      cfg,
      account,
      routeAgentId: route.agentId,
      conversationKey,
      retained,
      focusEntry,
      mergedParsed,
    }));

  const explicitMemeIntent =
    !isGroup || mergedParsed.wasMentioned || mergedParsed.isReply
      ? detectQqExplicitMemeIntent({
          rawBody,
          selfId: account.selfId ?? String(focusEntry.event.self_id),
        })
      : null;
  const currentTurnDeferredMemeIntent =
    currentTurnMemeBaseImage?.image_path || currentTurnMemeBaseImage?.image_url
      ? detectQqDeferredMemeIntent({
          rawBody,
          selfId: account.selfId ?? String(focusEntry.event.self_id),
        })
      : null;
  const followupDeferredMemeIntent =
    !explicitMemeIntent &&
    !currentTurnDeferredMemeIntent &&
    /^用户发送了\d+张?图片$/u.test(rawBody.trim()) &&
    (currentTurnMemeBaseImage?.image_path || currentTurnMemeBaseImage?.image_url)
      ? resolvePendingQqDeferredMemeIntent({
          conversationKey,
          senderId,
          currentMessageId: focusEntry.event.message_id
            ? String(focusEntry.event.message_id)
            : undefined,
          messageTimestamp,
          selfId: account.selfId ?? String(focusEntry.event.self_id),
        })
      : null;

  const immediateMemeCandidate =
    explicitMemeIntent && boundMedia?.record.type === "image"
      ? {
          intent: explicitMemeIntent,
          baseImage: resolveQqMemeBaseImageFromRecord(boundMedia.record),
          mode: "explicit_meme_from_bound_image",
          reason: explicitMemeIntent.reason,
          detail: {
            boundMediaSource: boundMedia.source,
            boundMediaSummary: boundMedia.record.summary,
          },
        }
      : currentTurnDeferredMemeIntent
        ? {
            intent: currentTurnDeferredMemeIntent,
            baseImage: currentTurnMemeBaseImage,
            mode: "deferred_meme_from_current_image",
            reason: currentTurnDeferredMemeIntent.reason,
            detail: {
              boundMediaSource: boundMedia?.source ?? "current-message",
              boundMediaSummary: summarizeQqMediaDebugRecord(
                currentMedia.find((entry) => entry.type === "image") ?? boundMedia?.record,
              ),
            },
          }
        : followupDeferredMemeIntent
          ? {
              intent: followupDeferredMemeIntent,
              baseImage: currentTurnMemeBaseImage,
              mode: "deferred_meme_from_followup_image",
              reason: followupDeferredMemeIntent.reason,
              detail: {
                boundMediaSource: boundMedia?.source ?? "current-message",
                boundMediaSummary: summarizeQqMediaDebugRecord(
                  currentMedia.find((entry) => entry.type === "image") ?? boundMedia?.record,
                ),
                sourceMessageId: followupDeferredMemeIntent.sourceMessageId ?? "",
                sourcePreview: previewText(followupDeferredMemeIntent.sourceText ?? "", 120),
              },
            }
          : null;
  if (
    immediateMemeCandidate?.baseImage &&
    (immediateMemeCandidate.baseImage.image_path || immediateMemeCandidate.baseImage.image_url)
  ) {
    recordQqDebugEvent({
      api,
      conversationKey,
      kind: "dispatch_gate",
      detail: {
        action: "dispatch_immediate",
        mode: immediateMemeCandidate.mode,
        reason: immediateMemeCandidate.reason,
        focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        pendingCount: state.pendingCount,
        busyLevel: state.busyLevel,
        ...immediateMemeCandidate.detail,
      },
    });
    if (params.debugDryRun) {
      return buildQqDebugInjectionSummary({
        conversationKey,
        focusEntry,
        rawBody,
        burstContext,
        currentMedia,
        boundMedia,
        replyTarget,
        state,
        action: "dispatch_immediate",
        mode: immediateMemeCandidate.mode,
        reason: immediateMemeCandidate.reason,
      });
    }
    const memeResult = await runQqMakeMeme(
      {
        image_path: immediateMemeCandidate.baseImage.image_path,
        image_url: immediateMemeCandidate.baseImage.image_url,
        top_text: immediateMemeCandidate.intent.topText,
        bottom_text: immediateMemeCandidate.intent.bottomText,
        center_text: immediateMemeCandidate.intent.centerText,
        caption: immediateMemeCandidate.intent.caption,
      },
      cfg as CoreConfig,
    ).catch((error) => {
      api.logger.warn(`[qq] immediate meme generation threw: ${String(error)}`);
      return null;
    });
    if (memeResult && !memeResult.ok) {
      api.logger.warn(
        `[qq] immediate meme generation failed: ${String(
          (memeResult as { error?: unknown }).error ?? "unknown-error",
        )}`,
      );
    }
    if (memeResult?.ok && memeResult.mediaUrl) {
      await sendImmediateQqMediaReply({
        cfg,
        accountId: account.accountId,
        event: focusEntry.event,
        text: immediateMemeCandidate.intent.caption,
        mediaUrl: memeResult.mediaUrl,
        conversationKey,
        agentId: route.agentId,
      });
      refreshImmediateConversationWatch(
        immediateMemeCandidate.intent.caption ||
          immediateMemeCandidate.intent.bottomText ||
          immediateMemeCandidate.intent.centerText ||
          immediateMemeCandidate.intent.topText ||
          "表情包",
      );
      return;
    }
  }

  const engagementMode: "direct" | "ambient-join" | "ambient-passive" =
    mergedParsed.wasMentioned ||
    mergedParsed.isReply ||
    followupWatch.allowed ||
    semanticFollowup.allowed
      ? "direct"
      : socialJoin.allowed
        ? "ambient-join"
        : "ambient-passive";
  if (socialAgencyPlan && socialAgencyGroupDir && groupId) {
    persistQqSocialAgencyPlan({
      groupDir: socialAgencyGroupDir,
      groupId,
      senderId,
      senderName: focusEntry.senderName,
      plan: socialAgencyPlan,
      nowMs: messageTimestamp,
    });
  }
  const envelopeOptions = runtime.channel.reply.resolveEnvelopeFormatOptions(cfg);
  const fromLabel = isGroup
    ? `${focusEntry.senderName || senderId}@group:${groupId}`
    : focusEntry.senderName || `user:${senderId}`;
  const body = runtime.channel.reply.formatAgentEnvelope({
    channel: "QQ",
    from: fromLabel,
    timestamp: messageTimestamp,
    previousTimestamp,
    envelope: envelopeOptions,
    body: rawBody,
  });
  const agentBody = buildQqAgentBody({
    focusEntry,
    burstContext,
    currentMedia,
    boundMedia,
    replyTarget,
    conversationKey,
    socialAgencyPlan,
  });
  const dynamicConversationSystemPrompt = buildQqConversationSystemPrompt({
    account,
    cfg,
    groupId,
    chatType: isGroup ? "group" : "direct",
    engagementMode,
    state: conversationStyleState,
    socialAgencyPlan,
  });
  const followupPrompt =
    isGroup &&
    (followupWatch.allowed || semanticFollowup.allowed) &&
    !mergedParsed.wasMentioned &&
    !mergedParsed.isReply
      ? mergeSystemPrompts(
          "This looks like a same-speaker follow-up to an already active conversation with you. Treat it as a continuation, but stay concise.",
          semanticFollowup.allowed
            ? `Semantic follow-up judge confidence: ${semanticFollowup.confidence}.`
            : undefined,
          state.pendingCount >= 3
            ? "The queue is busy. Prioritize the latest explicit question or direct instruction."
            : undefined,
        )
      : undefined;

  triggerGroupSocialLiveIngest({
    cfg,
    groupId,
    senderId,
    senderName: focusEntry.senderName,
    conversationLabel: fromLabel,
    rawBody,
    timestamp: new Date(messageTimestamp).toISOString(),
  });

  if (
    resolveQqStudyModeConfig(account).enabled &&
    !isGroup &&
    mergedParsed.mediaSegments.some((segment) => segment.type === "image")
  ) {
    void sendImmediateQqTextReply({
      cfg: cfg as CoreConfig,
      accountId: account.accountId,
      event: focusEntry.event,
      text: buildQqStudyProgressText("solving"),
      conversationKey,
    }).catch(() => null);
  }
  const studyProgressTimers: NodeJS.Timeout[] = [];
  const studyProgressFollowups = resolveQqStudyProgressFollowups({
    account,
    event: focusEntry.event,
    hasImage: mergedParsed.mediaSegments.some((segment) => segment.type === "image"),
  });
  for (const followup of studyProgressFollowups) {
    const timer = setTimeout(() => {
      void sendImmediateQqTextReply({
        cfg: cfg as CoreConfig,
        accountId: account.accountId,
        event: focusEntry.event,
        text: buildQqStudyProgressText(followup.kind),
        conversationKey,
      }).catch(() => null);
    }, followup.delayMs);
    timer.unref?.();
    studyProgressTimers.push(timer);
  }

  const ctxPayload = runtime.channel.reply.finalizeInboundContext({
    Body: body,
    BodyForAgent: agentBody,
    RawBody: rawBody,
    CommandBody: rawBody,
    From: isGroup ? `qq:group:${groupId}:user:${senderId}` : `qq:${senderId}`,
    To: isGroup ? `qq:group:${groupId}` : `qq:${senderId}`,
    SessionKey: route.sessionKey,
    AccountId: account.accountId,
    ChatType: isGroup ? "group" : "direct",
    ConversationLabel: fromLabel,
    SenderName: focusEntry.senderName,
    SenderId: senderId,
    GroupSubject: isGroup ? groupId : undefined,
      GroupSystemPrompt: mergeSystemPrompts(
        isGroup
          ? (account.config.groups?.[groupId ?? ""]?.systemPrompt ??
              account.config.groups?.["*"]?.systemPrompt)
          : undefined,
        dynamicConversationSystemPrompt,
        studyModeSystemPrompt,
        followupPrompt,
      ),
    Provider: CHANNEL_ID,
    Surface: CHANNEL_ID,
    WasMentioned: isGroup ? mergedParsed.wasMentioned : undefined,
    MessageSid: focusEntry.event.message_id ? String(focusEntry.event.message_id) : undefined,
    MessageSids: retained
      .map((entry) => (entry.event.message_id ? String(entry.event.message_id) : ""))
      .filter(Boolean),
    ReplyToId: replyTarget?.messageId,
    ReplyToBody: replyTarget?.text,
    ReplyToSender: replyTarget?.senderName ?? replyTarget?.senderId,
    ReplyToIsQuote: mergedParsed.isReply ? true : undefined,
    Timestamp: messageTimestamp,
    OriginatingChannel: CHANNEL_ID,
    OriginatingTo: isGroup ? `qq:group:${groupId}` : `qq:${senderId}`,
    CommandAuthorized: true,
    ...inboundMediaPayload.payload,
  });

  recordQqDebugEvent({
    api,
    conversationKey,
    kind: "dispatch_gate",
    detail: {
      action: "dispatch",
      mode: engagementMode,
      focusMessageId: focusEntry.event.message_id ? String(focusEntry.event.message_id) : "",
      rawBodyPreview: previewText(rawBody, 120),
      requireMention,
      wasMentioned: mergedParsed.wasMentioned,
      isReply: mergedParsed.isReply,
      socialJoinAllowed: socialJoin.allowed,
      socialJoinReason: socialJoin.reason,
      followupAllowed: followupWatch.allowed,
      followupReason: followupWatch.reason,
      semanticAllowed: semanticFollowup.allowed,
      semanticReason: semanticFollowup.reason,
      socialAgencyMode: socialAgencyPlan?.mode ?? "",
      socialAgencyOpportunity: socialAgencyPlan?.opportunity?.type ?? "",
      socialAgencyRecipe: socialAgencyPlan?.selectedRecipe?.recipe.id ?? "",
      fairnessClass: schedulingDecision.fairnessClass,
      pendingCount: state.pendingCount,
      busyLevel: state.busyLevel,
      routeAgentId: route.agentId,
      routeSessionKey: route.sessionKey,
      boundMediaSource: boundMedia?.source ?? "",
      boundMediaSummary: summarizeQqMediaDebugRecord(boundMedia?.record),
    },
  });
  if (params.debugDryRun) {
    return buildQqDebugInjectionSummary({
      conversationKey,
      focusEntry,
      rawBody,
      burstContext,
      currentMedia,
      boundMedia,
      replyTarget,
      state,
      action: "dispatch",
      mode: engagementMode,
      agentBody,
    });
  }

  qqConversationInflight.set(
    conversationKey,
    (qqConversationInflight.get(conversationKey) ?? 0) + 1,
  );
  refreshQqConversationLoad(conversationKey);
  try {
    await dispatchInboundReplyWithBase({
      cfg,
      channel: CHANNEL_ID,
      accountId: account.accountId,
      route,
      storePath,
      ctxPayload,
      core: {
        channel: {
          session: {
            recordInboundSession: runtime.channel.session.recordInboundSession,
          },
          reply: {
            dispatchReplyWithBufferedBlockDispatcher:
              runtime.channel.reply.dispatchReplyWithBufferedBlockDispatcher,
          },
        },
      },
      deliver: async (payload) => {
        const trackingKey =
          buildRecallTrackingKey({
            sessionKey: route.sessionKey,
            senderId,
          }) ?? undefined;
        await deliverInboundReply({
          cfg,
          account,
          accountId: account.accountId,
          event: focusEntry.event,
          payload,
          recoveryReplyToMessageId:
            isGroup && params.recoveryReplyToLatestMessage
              ? normalizeQqMessageId(focusEntry.event.message_id)
              : undefined,
          trackingKey,
          conversationKey,
          sessionKey: route.sessionKey,
          agentId: route.agentId,
        });
      },
      onRecordError: (err) => {
        api.logger.error(`[qq] failed updating session meta: ${String(err)}`);
      },
      onDispatchError: (err, info) => {
        api.logger.error(`[qq] ${info.kind} reply failed: ${String(err)}`);
      },
      replyOptions: {
        skillFilter: resolveQqReplySkillFilter({
          account,
          groupId,
          chatType: isGroup ? "group" : "direct",
        }),
      },
    });
  } finally {
    for (const timer of studyProgressTimers) {
      clearTimeout(timer);
    }
    const nextInflight = Math.max((qqConversationInflight.get(conversationKey) ?? 1) - 1, 0);
    if (nextInflight > 0) {
      qqConversationInflight.set(conversationKey, nextInflight);
    } else {
      qqConversationInflight.delete(conversationKey);
    }
    refreshQqConversationLoad(conversationKey);
  }
}

async function handleInboundMessage(params: {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  event: OneBotMessageEvent;
}) {
  const senderId = String(params.event.user_id);
  if (isBlockedInboundQqSender(params.account, params.event)) {
    const groupId =
      params.event.message_type === "group" ? String(params.event.group_id ?? "") : "";
    params.api.logger.debug(
      `[qq] ignored inbound message from blocked user: user=${senderId} type=${params.event.message_type}${groupId ? ` group=${groupId}` : ""}`,
    );
    return;
  }
  let parsed = parseMessageSegments(
    params.event.message,
    params.account.selfId ?? String(params.event.self_id),
  );
  if (
    shouldTreatQqMessageAsDirectEngagement(params.event) &&
    params.event.message_type === "group"
  ) {
    parsed = {
      ...parsed,
      wasMentioned: true,
    };
  }
  const rawBody = parsed.text || summarizeQqMediaPlaceholder(parsed);
  if (!rawBody && parsed.mediaSegments.length === 0) {
    return;
  }
  const conversationKey = buildQqConversationKey(params.account.accountId, params.event);
  const allowBrainSwitch = params.event.message_type === "private";
  const brain = allowBrainSwitch
    ? resolveQqBrainTarget({ conversationKey, rawBody })
    : { target: "openclaw" as const, body: rawBody.trim(), explicitSwitch: false };
  if (params.event.message_type === "private") {
    params.api.logger.info(
      `[qq] brain route ${conversationKey} -> ${brain.target}${brain.explicitSwitch ? " (switch)" : ""}`,
    );
  }
  if (brain.explicitSwitch && !brain.body) {
    await sendImmediateQqTextReply({
      cfg: params.api.runtime.config.loadConfig() as CoreConfig,
      accountId: params.account.accountId,
      event: params.event,
      text:
        brain.target === "codex"
          ? "已切到 Codex。之后这段对话会先交给 Codex；发 /chat 可切回 OpenClaw。"
          : "已切回 OpenClaw。之后这段对话会按原来的 QQ 机器人处理；发 /codex 可切到 Codex。",
      conversationKey,
    });
    return;
  }
  if (brain.target === "codex") {
    const codexBody = brain.body || rawBody;
    if (isQqCodexNewChatCommand(codexBody)) {
      await resetQqCodexConversationContext(conversationKey);
      await sendImmediateQqTextReply({
        cfg: params.api.runtime.config.loadConfig() as CoreConfig,
        accountId: params.account.accountId,
        event: params.event,
        text: "好，已经给你开了个新的聊天。",
        conversationKey,
      });
      return;
    }
    const mikoPersona = qqPersonaProfiles.find((profile) => profile.id === "miko") ?? qqPersonaProfiles[0]!;
    if (isQqPersonaIdentityQuestion({
      rawBody: codexBody,
      selfId: params.account.selfId ?? String(params.event.self_id),
    })) {
      await sendImmediateQqTextReply({
        cfg: params.api.runtime.config.loadConfig() as CoreConfig,
        accountId: params.account.accountId,
        event: params.event,
        text: buildQqPersonaIdentityReply({
          persona: mikoPersona,
          rawBody: codexBody,
          selfId: params.account.selfId ?? String(params.event.self_id),
        }),
        conversationKey,
      });
      return;
    }
    const reasoningCommand = parseQqCodexReasoningCommand(codexBody);
    if (reasoningCommand && !reasoningCommand.body) {
      setQqCodexReasoningEffort(conversationKey, reasoningCommand.effort);
      await sendImmediateQqTextReply({
        cfg: params.api.runtime.config.loadConfig() as CoreConfig,
        accountId: params.account.accountId,
        event: params.event,
        text: `已切到 Codex ${reasoningCommand.label}思考模式。`,
        conversationKey,
      });
      return;
    }
    const effectiveCodexBody = reasoningCommand?.body || codexBody;
    if (reasoningCommand) {
      setQqCodexReasoningEffort(conversationKey, reasoningCommand.effort);
    }
    if (!codexBody.trim()) {
      await sendImmediateQqTextReply({
        cfg: params.api.runtime.config.loadConfig() as CoreConfig,
        accountId: params.account.accountId,
        event: params.event,
        text: "已切到 Codex。请继续发你要问 Codex 的内容。",
        conversationKey,
      });
      return;
    }
    const cfg = params.api.runtime.config.loadConfig() as CoreConfig;
    try {
      const reasoningEffort = getQqCodexReasoningEffort(conversationKey);
      const isCodexGroup = params.event.message_type === "group";
      const codexGroupId = isCodexGroup ? String(params.event.group_id ?? "") : undefined;
      if (isCodexGroup && (parsed.wasMentioned || parsed.isReply)) {
        touchDirectFollowupWatch({
          accountId: params.account.accountId,
          groupId: codexGroupId,
          senderId,
          now: Date.now(),
          rawBody,
        });
      }
      const codexFollowupWatch = isCodexGroup
        ? evaluateDirectFollowupWatch({
            accountId: params.account.accountId,
            groupId: codexGroupId,
            senderId,
            rawBody,
            parsed,
            selfId: params.account.selfId ?? String(params.event.self_id),
            now: Date.now(),
          })
        : { allowed: false, reason: "not-group" };
      const codexSemanticFollowup =
        isCodexGroup &&
        !parsed.wasMentioned &&
        !parsed.isReply &&
        !codexFollowupWatch.allowed &&
        codexFollowupWatch.reason === "watch-followup-unrelated" &&
        Number(codexFollowupWatch.score ?? 0) >= DIRECT_FOLLOWUP_SEMANTIC_MIN_RULE_SCORE &&
        codexFollowupWatch.state
          ? await semanticJudgeDirectFollowup({
              cfg,
              state: codexFollowupWatch.state,
              senderId,
              senderName: getSenderName(params.event),
              groupId: codexGroupId,
              rawBody,
              now: Date.now(),
            }).catch((error) => {
              params.api.logger.warn(`[qq] codex semantic followup judge failed: ${String(error)}`);
              return { allowed: false, confidence: 0, reason: "semantic-error" };
            })
          : { allowed: false, confidence: 0, reason: "semantic-not-needed" };
      if (codexSemanticFollowup.allowed) {
        touchDirectFollowupWatch({
          accountId: params.account.accountId,
          groupId: codexGroupId,
          senderId,
          now: Date.now(),
          rawBody,
        });
      }
      const codexMediaPayload = await resolveInboundMediaPayload({
        runtime: getQqRuntime(),
        account: params.account,
        imageUrls: parsed.imageUrls,
      });
      const codexImagePaths = codexMediaPayload.resolvedMedia.flatMap((entry) =>
        entry.localPath ? [entry.localPath] : [],
      );
      if (codexMediaPayload.resolvedMedia.length > 0) {
        recordQqDebugEvent({
          api: params.api,
          conversationKey,
          kind: "media_ingress",
          detail: {
            phase: "codex_resolved",
            messageId: params.event.message_id ? String(params.event.message_id) : "",
            imagePaths: codexImagePaths,
            resolvedMedia: buildResolvedInboundMediaDebug(codexMediaPayload.resolvedMedia),
          },
        });
      }
      if (brain.explicitSwitch) {
        await sendImmediateQqTextReply({
          cfg,
          accountId: params.account.accountId,
          event: params.event,
          text: "已切到 Codex，正在处理…",
          conversationKey,
        });
      }
      const answer = await runQqCodexTurn({
        conversationKey,
        event: params.event,
        senderName: getSenderName(params.event),
        imagePaths: codexImagePaths,
        reasoningEffort,
        prompt: buildQqCodexPrompt({
          event: params.event,
          body: effectiveCodexBody,
          senderName: getSenderName(params.event),
          imagePaths: codexImagePaths,
          reasoningEffort,
          followupContext: buildQqCodexFollowupContext({
            event: params.event,
            parsed,
            followupWatch: codexFollowupWatch,
            semanticFollowup: codexSemanticFollowup,
          }),
        }),
      });
      const sentChunks: string[] = [];
      for (const chunk of chunkQqCodexReply(answer)) {
        await sendImmediateQqTextReply({
          cfg,
          accountId: params.account.accountId,
          event: params.event,
          text: chunk,
          conversationKey,
        });
        sentChunks.push(chunk);
      }
      if (isCodexGroup && sentChunks.length > 0) {
        noteDirectFollowupReply({
          accountId: params.account.accountId,
          groupId: codexGroupId,
          senderId,
          now: Date.now(),
          replyText: sentChunks.join(" "),
        });
      }
    } catch (error) {
      params.api.logger.error(`[qq] codex relay failed: ${String(error)}`);
      await sendImmediateQqTextReply({
        cfg,
        accountId: params.account.accountId,
        event: params.event,
        text: `Codex 这次失败了：${String(error instanceof Error ? error.message : error)}`,
        conversationKey,
      });
    }
    return;
  }
  const studyMode = resolveQqStudyModeConfig(params.account);
  const isDirect = params.event.message_type === "private";
  const hasImageMedia = parsed.mediaSegments.some((segment) => segment.type === "image");
  if (parsed.mediaSegments.length > 0) {
    recordQqDebugEvent({
      api: params.api,
      conversationKey,
      kind: "media_ingress",
      detail: {
        phase: "parsed",
        messageId: params.event.message_id ? String(params.event.message_id) : "",
        rawBodyPreview: previewText(rawBody, 120),
        mediaRefs: buildQqInboundMediaIngressDebug({
          api: params.api,
          account: params.account,
          event: params.event,
          parsed,
          rawBody,
          timestamp: (params.event.time ?? Math.floor(Date.now() / 1000)) * 1000,
          senderId,
          senderName: getSenderName(params.event),
        }),
      },
    });
  }
  const pendingBurst = qqPendingBursts.get(conversationKey);
  if (studyMode.enabled && isDirect && hasImageMedia && !pendingBurst?.studyImageAckSent) {
    void sendImmediateQqTextReply({
      cfg: params.api.runtime.config.loadConfig() as CoreConfig,
      accountId: params.account.accountId,
      event: params.event,
      text: buildQqStudyProgressText("image_received"),
      conversationKey,
    }).catch(() => null);
  }
  if (
    studyMode.enabled &&
    isDirect &&
    !hasImageMedia &&
    parsed.text.trim() &&
    pendingBurst &&
    !pendingBurst.studyFollowupAckSent
  ) {
    void sendImmediateQqTextReply({
      cfg: params.api.runtime.config.loadConfig() as CoreConfig,
      accountId: params.account.accountId,
      event: params.event,
      text: buildQqStudyProgressText("followup_received"),
      conversationKey,
    }).catch(() => null);
    pendingBurst.studyFollowupAckSent = true;
  }
  const cfgForNativeImage = params.api.runtime.config.loadConfig() as OpenClawConfig;
  if (
    await tryHandleQqNativeImageRequest({
      api: params.api,
      cfg: cfgForNativeImage,
      account: params.account,
      event: params.event,
      rawBody,
      conversationKey,
    })
  ) {
    return;
  }

  const burstTiming = resolveDirectStudyBurstDelays({
    account: params.account,
    event: params.event,
    parsed,
    conversationKey,
  });
  await enqueueQqInboundEvent({
    api: params.api,
    account: params.account,
    event: params.event,
    parsed,
    rawBody,
    timestamp: (params.event.time ?? Math.floor(Date.now() / 1000)) * 1000,
    senderId,
    senderName: getSenderName(params.event),
    burstIdleMs: burstTiming.burstIdleMs,
    burstWindowMs: burstTiming.burstWindowMs,
  });
  if (qqStateDirForRecovery) {
    rememberQqInboundConversationProgress({
      stateDir: qqStateDirForRecovery,
      conversationKey,
      messageId: normalizeQqMessageId(params.event.message_id),
      timestamp: (params.event.time ?? Math.floor(Date.now() / 1000)) * 1000,
    });
  }
}

async function handleInboundPokeNotice(params: {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  event: OneBotPokeNoticeEvent;
}) {
  const syntheticMessage = buildSyntheticQqPokeMessageEvent({
    event: params.event,
    account: params.account,
  });
  if (!syntheticMessage) {
    return;
  }
  params.api.logger.debug(
    `[qq] received poke notice from user=${syntheticMessage.user_id} target=${normalizeQqPokeTargetId(params.event)} type=${syntheticMessage.message_type}${syntheticMessage.group_id ? ` group=${syntheticMessage.group_id}` : ""}`,
  );
  await handleInboundMessage({
    api: params.api,
    account: params.account,
    event: syntheticMessage,
  });
}

export const __testing = {
  buildSyntheticQqPokeText,
  buildSyntheticQqPokeMessageEvent,
  extractQqUserLevel,
  hasAtLeastOneSunQqLevel,
  isOneBotActionAccepted,
  isFriendRequestEvent,
  isBlockedInboundQqSender,
  normalizeBlockedQqUserIds,
  buildQqConversationSystemPrompt,
  buildQqAgentBody,
  buildQqDebugInjectionSummary,
  buildQqImageSearchSelectionOrder,
  buildQqLoadDebugFields,
  classifyQqFairnessClass,
  detectQqExplicitImageIntent,
  detectQqExplicitMemeIntent,
  detectQqDeferredMemeIntent,
  detectQqLowPriorityNoiseReason,
  getQqGlobalLoad,
  inferQqDecisionStage,
  maybeMarkQqSessionForRollover,
  rememberQqMediaRecords,
  resolvePendingQqDeferredMemeIntent,
  resolveQqConversationMemeBaseImage,
  resolveQqSchedulingDecision,
  resolveQqStaleThresholdMs,
  resolvePreferredQqInboundImageRef,
  canUseDirectQqMediaFetch,
  fetchQqRemoteMediaWithFallback,
  resolveInboundMediaPayload,
  buildQqConversationKey,
  isQqCodexNewChatCommand,
  buildQqCodexImageArgs,
  chunkQqCodexReply,
  compactQqCodexPromptForModelLimit,
  buildQqCodexPrompt,
  parseQqCodexReasoningCommand,
  normalizeQqCodexReasoningEffort,
  labelQqCodexReasoningEffort,
  parseMessageSegments,
  parseQqBrainCommand,
  resolveQqBrainTarget,
  rememberQqImageSearchSelection,
  buildQqInboundMediaIngressDebug,
  buildResolvedInboundMediaDebug,
  resetQqImageSearchSelectionState,
  resolveQqStudyProgressFollowups,
  resolveDirectStudyBurstDelays,
  resetQqConversationStateForTest,
  shouldSkipQqOverloadNoise,
  shouldSkipQqFairnessNoise,
  shouldSkipQqStaleMessage,
  normalizeQqRecoveredMessageEvent,
  selectRecoverableQqHistoryEvents,
  buildQqReplySegments,
  isQqAudioMediaUrl,
  resolveQqMediaDeliveryPlan,
  sendQqVoice,
  convertAudioToNapcatSilk,
  ensureSignedNapcatFfmpegAddonCopy,
};

export async function debugInjectQqInboundMessage(params: {
  api: OpenClawPluginApi;
  cfg: OpenClawConfig;
  accountId?: string;
  event: OneBotMessageEvent;
  dryRun?: boolean;
}): Promise<Record<string, unknown>> {
  return await debugInjectQqInboundSequence({
    api: params.api,
    cfg: params.cfg,
    accountId: params.accountId,
    events: [params.event],
    dryRun: params.dryRun,
  });
}

export async function debugInjectQqInboundSequence(params: {
  api: OpenClawPluginApi;
  cfg: OpenClawConfig;
  accountId?: string;
  events: OneBotMessageEvent[];
  dryRun?: boolean;
}): Promise<Record<string, unknown>> {
  if (!Array.isArray(params.events) || params.events.length === 0) {
    return {
      ok: false,
      error: "注入序列为空：至少要提供一条消息",
    };
  }
  const resolvedAccount = resolveQqAccount({
    cfg: params.cfg as CoreConfig,
    accountId: params.accountId,
  });
  const queuedEntries: QueuedQqInboundEvent[] = [];
  let conversationKey: string | undefined;
  for (const event of params.events) {
    const account: ResolvedQqAccount = {
      ...resolvedAccount,
      selfId: resolvedAccount.selfId ?? String(event.self_id),
    };
    const parsed = parseMessageSegments(event.message, account.selfId ?? String(event.self_id));
    const rawBody = parsed.text || summarizeQqMediaPlaceholder(parsed);
    if (!rawBody && parsed.mediaSegments.length === 0) {
      continue;
    }
    const nextConversationKey = buildQqConversationKey(account.accountId, event);
    if (conversationKey && conversationKey !== nextConversationKey) {
      return {
        ok: false,
        error: "注入序列当前只支持单会话：所有消息必须属于同一个 group/direct 会话",
      };
    }
    conversationKey = nextConversationKey;
    queuedEntries.push({
      api: params.api,
      account,
      event,
      parsed,
      rawBody,
      timestamp: (event.time ?? Math.floor(Date.now() / 1000)) * 1000,
      senderId: String(event.user_id),
      senderName: getSenderName(event),
    });
  }
  if (queuedEntries.length === 0 || !conversationKey) {
    return {
      ok: false,
      error: "注入消息为空：既没有文本也没有媒体",
    };
  }
  const summary = await processQueuedQqInboundEvents({
    api: params.api,
    account: queuedEntries[0]!.account,
    conversationKey,
    entries: queuedEntries,
    debugDryRun: params.dryRun !== false,
  });
  return (
    summary ?? {
      ok: true,
      dry_run: false,
      conversation_key: conversationKey,
      injected_count: queuedEntries.length,
      note: "消息序列已注入正常处理链路",
    }
  );
}

function attachConnection(accountId: string, socket: WebSocket) {
  const existing = activeConnections.get(accountId);
  if (existing && existing.socket !== socket) {
    try {
      existing.socket.close();
    } catch {
      // ignore best-effort close
    }
  }
  activeConnections.set(accountId, {
    socket,
    accountId,
    pending: new Map(),
  });
}

function settlePending(connection: QqConnectionState, frame: OneBotApiResponse) {
  const echo = String(frame.echo ?? "");
  const pending = connection.pending.get(echo);
  if (!pending) {
    return;
  }
  clearTimeout(pending.timeout);
  connection.pending.delete(echo);
  pending.resolve(frame);
}

export function createQqService(api: OpenClawPluginApi): OpenClawPluginService {
  let server: ReturnType<typeof createServer> | null = null;
  let wss: WebSocketServer | null = null;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  let managedQqProcess: ChildProcess | null = null;
  let idleSleepBlockerProcess: ChildProcess | null = null;

  return {
    id: "qq-onebot",
    start: async (ctx) => {
      const cfg = api.runtime.config.loadConfig() as CoreConfig;
      const account = resolveQqAccount({ cfg });
      qqStateDirForRecovery = ctx.stateDir;
      loadRecentQqDeliveries(ctx.stateDir);
      loadQqInboundRecoveryState(ctx.stateDir);
      loadQqPersonaState(ctx.stateDir);
      if (!account.enabled) {
        api.logger.info("[qq] channel disabled; OneBot listener not started");
        clearManagedState(ctx.stateDir);
        return;
      }
      sanitizeQqRecoveryQueue(ctx.stateDir, account, api.logger);
      const acceptedPaths = buildAcceptedPaths(account.websocketPath);

      server = createServer((req, res) => {
        const requestPath = normalizeWsPath((req.url ?? "/").split("?")[0] ?? "/");
        if (requestPath === QQ_CODEX_LOCAL_ACTION_PATH) {
          void handleLocalQqActionRequest({
            req,
            res,
            cfg: api.runtime.config.loadConfig() as CoreConfig,
            defaultAccountId: account.accountId,
            pluginConfig: api.pluginConfig,
          });
          return;
        }
        res.writeHead(404);
        res.end();
      });
      wss = new WebSocketServer({ noServer: true });

      server.on("upgrade", (req: IncomingMessage, socket, head) => {
        const requestPath = normalizeWsPath(req.url ?? "/");
        if (!acceptedPaths.has(requestPath)) {
          socket.destroy();
          return;
        }
        wss?.handleUpgrade(req, socket, head, (ws) => {
          wss?.emit("connection", ws, req);
        });
      });

      wss.on("connection", (socket) => {
        attachConnection(account.accountId, socket);
        noteQqConnectionOpened(ctx.stateDir);
        api.logger.info(
          `[qq] NapCat / OneBot connected on ws://${account.listenHost}:${account.listenPort}${account.websocketPath}`,
        );
        void (async () => {
          await recoverQqPendingDeliveries({
            cfg: api.runtime.config.loadConfig() as CoreConfig,
            stateDir: ctx.stateDir,
            account,
            log: api.logger,
          });
          await recoverQqMissedInboundMessages({
            api,
            cfg: api.runtime.config.loadConfig() as CoreConfig,
            stateDir: ctx.stateDir,
            account,
            log: api.logger,
          });
        })();

        socket.on("message", async (raw) => {
          try {
            const frame = JSON.parse(raw.toString()) as OneBotInboundFrame;
            const connection = getConnection(account.accountId);

            if (isApiResponse(frame)) {
              settlePending(connection, frame);
              return;
            }
            if (frame.post_type === "meta_event") {
              connection.selfId = String(frame.self_id);
              return;
            }
            if (isPokeNoticeEvent(frame)) {
              connection.selfId = String(frame.self_id);
              const resolvedAccount = resolveQqAccount({
                cfg: api.runtime.config.loadConfig() as CoreConfig,
              });
              const effectiveAccount = {
                ...resolvedAccount,
                selfId: resolvedAccount.selfId ?? connection.selfId,
              };
              await handleInboundPokeNotice({
                api,
                account: effectiveAccount,
                event: frame,
              });
              return;
            }
            if (isFriendRequestEvent(frame)) {
              connection.selfId = String(frame.self_id);
              const resolvedAccount = resolveQqAccount({
                cfg: api.runtime.config.loadConfig() as CoreConfig,
              });
              const effectiveAccount = {
                ...resolvedAccount,
                selfId: resolvedAccount.selfId ?? connection.selfId,
              };
              await handleInboundFriendRequest({
                api,
                account: effectiveAccount,
                event: frame,
              });
              return;
            }
            if (isMessageEvent(frame)) {
              connection.selfId = String(frame.self_id);
              const resolvedAccount = resolveQqAccount({
                cfg: api.runtime.config.loadConfig() as CoreConfig,
              });
              const effectiveAccount = {
                ...resolvedAccount,
                selfId: resolvedAccount.selfId ?? connection.selfId,
              };
              await handleInboundMessage({
                api,
                account: effectiveAccount,
                event: frame,
              });
            }
          } catch (err) {
            api.logger.error(`[qq] failed to process inbound frame: ${String(err)}`);
          }
        });

        socket.on("close", () => {
          noteQqConnectionClosed(ctx.stateDir);
          const current = activeConnections.get(account.accountId);
          if (current?.socket === socket) {
            activeConnections.delete(account.accountId);
          }
          api.logger.warn("[qq] NapCat / OneBot connection closed");
        });

        socket.on("error", (err) => {
          api.logger.error(`[qq] socket error: ${String(err)}`);
        });
      });

      await new Promise<void>((resolve, reject) => {
        server?.once("error", reject);
        server?.listen(account.listenPort, account.listenHost, () => resolve());
      });

      heartbeatTimer = setInterval(() => {
        for (const connection of activeConnections.values()) {
          if (connection.socket.readyState === connection.socket.OPEN) {
            connection.socket.ping();
          }
        }
      }, HEARTBEAT_MS);
      heartbeatTimer.unref?.();

      api.logger.info(
        `[qq] OneBot listener ready on ws://${account.listenHost}:${account.listenPort}${account.websocketPath}`,
      );

      idleSleepBlockerProcess = startIdleSleepBlocker(api, account);

      if (account.autoLaunch) {
        if (!fs.existsSync(account.executablePath)) {
          api.logger.warn(
            `[qq] autoLaunch requested but executable not found: ${account.executablePath}`,
          );
          return;
        }
        const baselinePids = await listProcessIds(account.executablePath);
        if (baselinePids.length > 0) {
          api.logger.info("[qq] QQ already running; skipping autoLaunch");
          clearManagedState(ctx.stateDir);
          return;
        }
        managedQqProcess = spawn(account.executablePath, account.launchArgs, {
          stdio: "ignore",
          detached: false,
        });
        managedQqProcess.unref?.();
        managedQqProcess.on("exit", (code, signal) => {
          api.logger.info(
            `[qq] managed QQ process exited (code=${code ?? "null"}, signal=${signal ?? "null"})`,
          );
          managedQqProcess = null;
        });
        managedQqProcess.on("error", (err) => {
          api.logger.error(`[qq] failed to launch QQ automatically: ${String(err)}`);
          managedQqProcess = null;
        });
        await sleep(1500);
        const currentPids = await listProcessIds(account.executablePath);
        const managedPids = currentPids.filter((pid) => !baselinePids.includes(pid));
        if (managedPids.length > 0) {
          writeManagedState(ctx.stateDir, {
            executablePath: account.executablePath,
            pids: managedPids,
            launchedAt: Date.now(),
          });
          api.logger.info(`[qq] recorded managed QQ pid(s): ${managedPids.join(", ")}`);
        } else {
          clearManagedState(ctx.stateDir);
          api.logger.warn("[qq] QQ autoLaunch started but no managed pid was detected");
        }
        api.logger.info(
          `[qq] launched QQ automatically: ${account.executablePath} ${account.launchArgs.join(" ")}`,
        );
      }
    },
    stop: async (ctx) => {
      heartbeatTimer && clearInterval(heartbeatTimer);
      heartbeatTimer = null;

      for (const connection of activeConnections.values()) {
        for (const pending of connection.pending.values()) {
          clearTimeout(pending.timeout);
          pending.reject(new Error("QQ service stopping"));
        }
        connection.pending.clear();
        try {
          connection.socket.close();
        } catch {
          // ignore
        }
      }
      activeConnections.clear();

      await new Promise<void>((resolve) => {
        wss?.close(() => resolve());
        if (!wss) {
          resolve();
        }
      });
      wss = null;

      await new Promise<void>((resolve) => {
        server?.close(() => resolve());
        if (!server) {
          resolve();
        }
      });
      server = null;

      const managedState = readManagedState(ctx.stateDir);
      if (managedState?.pids?.length) {
        api.logger.info(`[qq] stopping managed QQ pid(s): ${managedState.pids.join(", ")}`);
        await killManagedPids(api, managedState.pids);
      }
      clearManagedState(ctx.stateDir);

      await stopManagedProcess(api, managedQqProcess);
      managedQqProcess = null;
      await stopIdleSleepBlocker(api, idleSleepBlockerProcess);
      idleSleepBlockerProcess = null;
      if (qqStateDirForRecovery) {
        saveRecentQqDeliveries(qqStateDirForRecovery);
        saveQqInboundRecoveryState(qqStateDirForRecovery);
      }
      qqStateDirForRecovery = null;
      qqInboundRecoveryStateCache = null;
    },
  };
}
