import { spawn, execFile, type ChildProcess } from "node:child_process";
import { promisify } from "node:util";
import { createServer, type IncomingMessage } from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
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
import { resolveQqHttpMediaUrl } from "../../shared/onebot-media-file.js";
import { shouldSuppressNoisyUserFacingErrorReply } from "../../shared/user-facing-error-suppression.js";
import { resolveQqAccount } from "./accounts.js";
import { getQqRuntime } from "./runtime.js";
import type {
  CoreConfig,
  OneBotApiResponse,
  OneBotInboundFrame,
  OneBotMessageEvent,
  OneBotMessageSegment,
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

const execFileAsync = promisify(execFile);

const CHANNEL_ID = "qq";
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
const DIRECT_STUDY_BURST_INITIAL_WINDOW_MS = 900;
const DIRECT_STUDY_BURST_EXTEND_WINDOW_MS = 500;
const DIRECT_STUDY_BURST_TEXT_FLUSH_MS = 120;
const DIRECT_STUDY_BURST_MAX_WINDOW_MS = 2_200;
const DIRECT_STUDY_BURST_MAX_PARTS = 8;
const BURST_SEND_DELAY_MS = 350;
const TARGET_SOCIAL_HARD_BAN_PATTERN = /\u2615\uFE0F?/gu;
const QQ_STYLE_REFERENCE_DIR = "ciyuan-fusu-erqu";
const DEFAULT_QQ_STUDY_MODE_SKILLS = [
  "qq-problem-solving",
  "qq-fusion-actions",
  "chinobot-capability-router",
  "qq-native",
];
const QQ_NATIVE_IMAGE_REQUEST_RE = /(画图|绘图|生图|出图|生成.{0,8}(图片|图像|图|插画|海报|头像|表情包)|画.{0,8}(图片|图像|图|插画|海报|头像|表情包)|draw|generate an image|create an image|make an image)/i;
const QQ_CONTEXTUAL_STUDY_IMAGE_REQUEST_RE = /(题|题目|这题|那题|上题|刚刚|刚才|这张图|那张图|上一张|上面|前面|作业|试卷|答案|解析|解题|渲染|整理|html|HTML|OCR|截图|worksheet|homework|exam|question|answer|solution)/i;
const QQ_NATIVE_IMAGE_SCRIPT =
  process.env.OPENCLAW_QQ_NATIVE_IMAGE_SCRIPT ||
  path.resolve(process.cwd(), "skills", "openai-image-gen", "scripts", "gen.py");
const QQ_NATIVE_IMAGE_BASE_URL =
  process.env.OPENCLAW_QQ_NATIVE_IMAGE_BASE_URL || process.env.OPENAI_BASE_URL || "";
const QQ_NATIVE_IMAGE_PYTHON = process.env.OPENCLAW_QQ_NATIVE_IMAGE_PYTHON || "python3";

const activeConnections = new Map<string, QqConnectionState>();
const recentOutboundMessages = new Map<string, number[]>();
const directFollowupWatches = new Map<string, DirectFollowupWatchState>();
const pendingDirectStudyBursts = new Map<string, PendingDirectStudyBurst>();
let runEmbeddedPiAgentLoader: Promise<RunEmbeddedPiAgentFn> | null = null;

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

type PendingDirectStudyBurstPart = {
  event: OneBotMessageEvent;
  parsed: ParsedQqMessage;
};

type PendingDirectStudyBurst = {
  accountId: string;
  senderId: string;
  startedAt: number;
  parts: PendingDirectStudyBurstPart[];
  timer: NodeJS.Timeout;
};

type RunEmbeddedPiAgentFn = (params: Record<string, unknown>) => Promise<unknown>;

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

function parseMessageSegments(
  message: string | OneBotMessageSegment[] | undefined,
  selfId?: string,
): ParsedQqMessage {
  if (typeof message === "string") {
    return {
      text: message.trim(),
      isReply: false,
      wasMentioned: false,
      mentionIds: [],
      imageUrls: [],
    };
  }

  const parts: string[] = [];
  const imageUrls: string[] = [];
  const mentionIds: string[] = [];
  let isReply = false;
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
      continue;
    }
    if (seg.type === "image") {
      const url = String(seg.data?.url ?? seg.data?.file ?? "").trim();
      if (url) {
        imageUrls.push(url);
      }
      continue;
    }
  }

  return {
    text: parts.join("").trim(),
    isReply,
    wasMentioned,
    mentionIds,
    imageUrls,
  };
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
};

type GroupSocialSelfPosition = {
  currentRole?: string;
  allowedPresence?: string;
  attentionBudget?: number;
};

type GroupSocialAppraisal = {
  socialSafety?: number;
  dramaRisk?: number;
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

type ResolvedQqNaturalChatConfig = {
  enabled: boolean;
  applyToGroups: boolean;
  applyToDirect: boolean;
  splitMessages: boolean;
  removeDecorativeEmoji: boolean;
  hardBannedSymbols: string[];
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

function previewText(text: string, limit = 120): string {
  return text.replace(/\s+/g, " ").trim().slice(0, limit);
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
  };
}

export function resolveQqStudyModeConfig(
  account: ResolvedQqAccount,
): ResolvedQqStudyModeConfig {
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

export function shouldSkipInboundQqMessageForStudyMode(params: {
  account: ResolvedQqAccount;
  chatType: "group" | "direct";
}) {
  const studyMode = resolveQqStudyModeConfig(params.account);
  return studyMode.enabled && studyMode.directOnly && params.chatType === "group";
}

export function buildQqStudyModeSystemPrompt(params: {
  account: ResolvedQqAccount;
  chatType: "group" | "direct";
  hasImage: boolean;
}): string | undefined {
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
      ? "This turn includes an image. Inspect the image first; if it plausibly contains a problem statement, start solving immediately instead of asking whether the user wants help."
      : null,
    params.hasImage && studyMode.autoSolveLikelyProblemImages
      ? "Only ask for a clearer resend when the image is genuinely unreadable, cropped, or missing decisive parts of the question."
      : null,
    "If the attached image is clearly not a question (for example a selfie, meme, scenery, or casual photo), reply normally instead of forcing a problem-solving workflow.",
    params.hasImage
      ? "When multiple screenshots are present, treat them as one question packet first, not as unrelated independent images."
      : null,
    params.hasImage
      ? "Reconstruct the most likely page and question order using explicit page numbers, question numbering, continuation phrases, overlapping text, headers/footers, and answer flow."
      : null,
    params.hasImage
      ? "If the received order looks wrong, reorder the screenshots mentally before solving. User text hints about page order should override simple receive order."
      : null,
    `Default answer style: ${styleLabel}. Keep the tone concise, structured, and directly usable in an exam or homework submission.`,
    "Match the language of the question unless the user explicitly asks for another language.",
    "Do not add chatty filler, roleplay banter, or assistant-style preambles before the solution.",
    "If the problem needs or clearly benefits from a figure, graph, geometry sketch, table, flowchart, circuit, or coordinate diagram, include it in the final output.",
    studyMode.alwaysRenderHtml
      ? "Regardless of whether a figure is required, the final deliverable must be rendered with chinobot_render_html and sent back as the answer artifact."
      : null,
    studyMode.alwaysRenderHtml
      ? "If one screenshot contains multiple questions or too much content for one readable answer sheet, split the final delivery into multiple HTML-rendered cards/pages instead of cramming everything into one image."
      : null,
    studyMode.alwaysRenderHtml
      ? "Prefer one top-level question per rendered card, or one logical chunk per card when a single question is large."
      : null,
    studyMode.alwaysRenderHtml
      ? "Do not stop at plain text once you have solved the problem. The last-mile answer should be the rendered HTML visual."
      : null,
    studyMode.alwaysRenderHtml
      ? "Use a restrained exam-paper layout: light background, dark readable text, clear section hierarchy, and no poster-like or meme-like styling."
      : null,
    studyMode.alwaysRenderHtml
      ? "If only some questions are legible, solve the legible parts first and explicitly label any missing blurry or cropped parts."
      : null,
    studyMode.systemPrompt,
  ];

  return lines.filter((line): line is string => Boolean(line)).join("\n");
}

export function resolveQqReplySkillFilter(params: {
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

function buildDirectStudyBurstKey(accountId: string, senderId: string): string {
  return `${accountId}::${senderId}`;
}

export function shouldBufferInboundQqStudyBurst(params: {
  account: ResolvedQqAccount;
  chatType: "group" | "direct";
  senderId: string;
  parsed: ParsedQqMessage;
}) {
  const studyMode = resolveQqStudyModeConfig(params.account);
  if (!studyMode.enabled || params.chatType !== "direct") {
    return false;
  }
  const burstKey = buildDirectStudyBurstKey(params.account.accountId, params.senderId);
  if (pendingDirectStudyBursts.has(burstKey)) {
    return true;
  }
  return params.parsed.imageUrls.length > 0;
}

export function buildSyntheticDirectStudyBurstEvent(
  parts: PendingDirectStudyBurstPart[],
): OneBotMessageEvent {
  const latest = parts[parts.length - 1]!.event;
  const message: OneBotMessageSegment[] = [];

  parts.forEach((part, index) => {
    const text = part.parsed.text.trim();
    if (text) {
      message.push({
        type: "text",
        data: {
          text:
            parts.length > 1
              ? `[连续消息${index + 1}/${parts.length}] ${text}\n`
              : `${text}\n`,
        },
      });
    }
    part.parsed.imageUrls.forEach((url) => {
      message.push({
        type: "image",
        data: {
          file: url,
          url,
        },
      });
    });
  });

  return {
    ...latest,
    message,
    raw_message: "",
  };
}

async function flushPendingDirectStudyBurst(params: {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  burstKey: string;
}) {
  const pending = pendingDirectStudyBursts.get(params.burstKey);
  if (!pending) {
    return;
  }
  pendingDirectStudyBursts.delete(params.burstKey);
  clearTimeout(pending.timer);
  try {
    await handleInboundMessage({
      api: params.api,
      account: params.account,
      event: buildSyntheticDirectStudyBurstEvent(pending.parts),
      bypassStudyBurst: true,
    });
  } catch (error) {
    params.api.logger.error(`[qq] failed flushing direct study burst: ${String(error)}`);
  }
}

function schedulePendingDirectStudyBurstFlush(params: {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  burstKey: string;
  pending: PendingDirectStudyBurst;
  delayMs: number;
}) {
  clearTimeout(params.pending.timer);
  params.pending.timer = setTimeout(() => {
    void flushPendingDirectStudyBurst({
      api: params.api,
      account: params.account,
      burstKey: params.burstKey,
    });
  }, Math.max(0, params.delayMs));
  params.pending.timer.unref?.();
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
  const state = readQqConversationStyleState(params.cfg, params.groupId);
  if (!state) {
    return undefined;
  }

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
    const timeout = setTimeout(() => {
      connection.pending.delete(echo);
      reject(new Error(`QQ action timed out: ${params.action}`));
    }, typeof params.timeoutMs === "number" && Number.isFinite(params.timeoutMs) ? params.timeoutMs : 10_000);

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

export async function sendQqText(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  text: string;
}): Promise<OneBotApiResponse> {
  const action = params.targetKind === "group" ? "send_group_msg" : "send_private_msg";
  const actionParams =
    params.targetKind === "group"
      ? { group_id: Number(params.targetId), message: params.text }
      : { user_id: Number(params.targetId), message: params.text };
  return await sendAction({
    cfg: params.cfg,
    accountId: params.accountId,
    action,
    params: actionParams,
  });
}

export async function sendQqMedia(params: {
  cfg: CoreConfig;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  text: string;
  mediaUrl: string;
}): Promise<OneBotApiResponse> {
  const normalizedMediaUrl = await resolveQqHttpMediaUrl({
    mediaUrl: params.mediaUrl,
    gatewayPort: params.cfg.gateway?.port,
  });
  const action = params.targetKind === "group" ? "send_group_msg" : "send_private_msg";
  const message = [];
  if (params.text?.trim()) {
    message.push({ type: "text", data: { text: params.text } });
  }
  message.push({ type: "image", data: { file: normalizedMediaUrl } });
  const actionParams =
    params.targetKind === "group"
      ? { group_id: Number(params.targetId), message }
      : { user_id: Number(params.targetId), message };
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

function extractQqNativeImagePrompt(rawBody: string): string | null {
  const text = rawBody.trim();
  if (!text || !QQ_NATIVE_IMAGE_REQUEST_RE.test(text)) {
    return null;
  }
  if (QQ_CONTEXTUAL_STUDY_IMAGE_REQUEST_RE.test(text)) {
    return null;
  }
  return text
    .replace(/^\s*(?:请|帮我|给我|麻烦)?\s*(?:直接)?\s*/u, "")
    .replace(/^(?:画图|绘图|生图|出图)[:：,，\s]*/iu, "")
    .trim() || text;
}

export function shouldPassNativeImageRequestToAgent(rawBody: string): boolean {
  const text = rawBody.trim();
  return QQ_NATIVE_IMAGE_REQUEST_RE.test(text) && QQ_CONTEXTUAL_STUDY_IMAGE_REQUEST_RE.test(text);
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
  isGroup: boolean;
  groupId?: string;
  senderId: string;
}): Promise<boolean> {
  const prompt = extractQqNativeImagePrompt(params.rawBody);
  if (!prompt) {
    return false;
  }
  const targetKind = params.isGroup ? "group" : "user";
  const targetId = params.isGroup ? params.groupId : params.senderId;
  if (!targetId) {
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
    params.api.logger.info(`[qq] native image generation requested: target=${targetKind}:${targetId}`);
    const mediaPath = await generateQqNativeImage({ prompt, outDir });
    await sendQqMedia({
      cfg: params.cfg as CoreConfig,
      accountId: params.account.accountId,
      targetKind,
      targetId,
      text: "",
      mediaUrl: mediaPath,
    });
    return true;
  } catch (error) {
    params.api.logger.error(`[qq] native image generation failed: ${String(error)}`);
    await sendQqText({
      cfg: params.cfg as CoreConfig,
      accountId: params.account.accountId,
      targetKind,
      targetId,
      text: `画图失败了：${String(error).slice(0, 160)}`,
    }).catch(() => undefined);
    return true;
  }
}

async function deliverInboundReply(params: {
  cfg: OpenClawConfig;
  account: ResolvedQqAccount;
  accountId?: string;
  event: OneBotMessageEvent;
  payload: OutboundReplyPayload;
  trackingKey?: string;
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

  const sentMedia = await sendMediaWithLeadingCaption({
    mediaUrls,
    caption: textBursts[0] ?? "",
    send: async ({ mediaUrl, caption }) => {
      const result = await sendQqMedia({
        cfg: params.cfg as CoreConfig,
        accountId: params.accountId,
        targetKind: parsed.kind,
        targetId: parsed.id,
        text: caption ?? "",
        mediaUrl,
      });
      trackOutboundMessage(params.trackingKey, result);
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
      const result = await sendQqText({
        cfg: params.cfg as CoreConfig,
        accountId: params.accountId,
        targetKind: parsed.kind,
        targetId: parsed.id,
        text: burst,
      });
      trackOutboundMessage(params.trackingKey, result);
    }
    return;
  }
  let sentAnyText = false;
  for (const [index, burst] of textBursts.entries()) {
    if (index > 0) {
      await sleep(BURST_SEND_DELAY_MS);
    }
    const result = await sendQqText({
      cfg: params.cfg as CoreConfig,
      accountId: params.accountId,
      targetKind: parsed.kind,
      targetId: parsed.id,
      text: burst,
    });
    trackOutboundMessage(params.trackingKey, result);
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
}) {
  if (params.imageUrls.length === 0) {
    return {};
  }

  const maxBytes = (params.account.config.mediaMaxMb ?? DEFAULT_MEDIA_MAX_MB) * 1024 * 1024;
  const mediaList: Array<{ path: string; contentType?: string }> = [];
  const mediaUrls: string[] = [];

  for (const url of params.imageUrls) {
    try {
      const fetched = await params.runtime.channel.media.fetchRemoteMedia({
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
    } catch {
      mediaUrls.push(url);
    }
  }

  if (mediaList.length === 0) {
    return {
      MediaUrls: mediaUrls.length > 0 ? mediaUrls : undefined,
      MediaUrl: mediaUrls[0],
    };
  }

  const built = buildMediaPayload(mediaList, { preserveMediaTypeCardinality: true });
  return {
    ...built,
    MediaUrl: built.MediaPath ?? mediaUrls[0],
    MediaUrls: mediaUrls.length > 0 ? mediaUrls : built.MediaUrls,
  };
}

async function handleInboundMessage(params: {
  api: OpenClawPluginApi;
  account: ResolvedQqAccount;
  event: OneBotMessageEvent;
  bypassStudyBurst?: boolean;
}) {
  const { api, account, event } = params;
  const runtime = getQqRuntime();
  const cfg = runtime.config.loadConfig() as OpenClawConfig;
  const parsed = parseMessageSegments(event.message, account.selfId ?? String(event.self_id));

  const isGroup = event.message_type === "group";
  const groupId = isGroup ? String(event.group_id ?? "") : undefined;
  const senderId = String(event.user_id);
  const messageTimestamp = (event.time ?? Math.floor(Date.now() / 1000)) * 1000;
  const rawBody = parsed.text || (parsed.imageUrls.length > 0 ? "用户发送了图片" : "");
  if (!rawBody) {
    return;
  }

  if (
    !params.bypassStudyBurst &&
    shouldBufferInboundQqStudyBurst({
      account,
      chatType: isGroup ? "group" : "direct",
      senderId,
      parsed,
    })
  ) {
    const burstKey = buildDirectStudyBurstKey(account.accountId, senderId);
    const current = pendingDirectStudyBursts.get(burstKey);
    if (current) {
      current.parts.push({
        event,
        parsed,
      });
      const hasInstructionText = current.parts.some((part) => part.parsed.text.trim().length > 0);
      const maxRemaining = Math.max(
        0,
        DIRECT_STUDY_BURST_MAX_WINDOW_MS - (Date.now() - current.startedAt),
      );
      if (current.parts.length >= DIRECT_STUDY_BURST_MAX_PARTS || maxRemaining === 0) {
        void flushPendingDirectStudyBurst({
          api,
          account,
          burstKey,
        });
      } else {
        schedulePendingDirectStudyBurstFlush({
          api,
          account,
          burstKey,
          pending: current,
          delayMs: Math.min(
            hasInstructionText ? DIRECT_STUDY_BURST_TEXT_FLUSH_MS : DIRECT_STUDY_BURST_EXTEND_WINDOW_MS,
            maxRemaining,
          ),
        });
      }
    } else {
      const pending: PendingDirectStudyBurst = {
        accountId: account.accountId,
        senderId,
        startedAt: Date.now(),
        parts: [
          {
            event,
            parsed,
          },
        ],
        timer: setTimeout(() => {}, DIRECT_STUDY_BURST_INITIAL_WINDOW_MS),
      };
      pending.timer.unref?.();
      pendingDirectStudyBursts.set(burstKey, pending);
      schedulePendingDirectStudyBurstFlush({
        api,
        account,
        burstKey,
        pending,
        delayMs: parsed.text.trim()
          ? DIRECT_STUDY_BURST_TEXT_FLUSH_MS
          : DIRECT_STUDY_BURST_INITIAL_WINDOW_MS,
      });
    }
    return;
  }

  if (
    shouldSkipInboundQqMessageForStudyMode({
      account,
      chatType: isGroup ? "group" : "direct",
    })
  ) {
    api.logger.debug(
      `[qq] study mode active; skipping group message: group=${groupId ?? "-"} user=${senderId}`,
    );
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

  const storePath = runtime.channel.session.resolveStorePath(
    (cfg.session as Record<string, unknown> | undefined)?.store as string | undefined,
    { agentId: route.agentId },
  );
  const previousTimestamp = runtime.channel.session.readSessionUpdatedAt({
    storePath,
    sessionKey: route.sessionKey,
  });
  if (isGroup && (parsed.wasMentioned || parsed.isReply)) {
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
  const socialJoin = shouldAllowSocialJoin({
    cfg,
    account,
    groupId,
    rawBody,
    parsed,
    previousTimestamp,
  });
  const followupWatch = isGroup
    ? evaluateDirectFollowupWatch({
        accountId: account.accountId,
        groupId,
        senderId,
        rawBody,
        parsed,
        selfId: account.selfId ?? String(event.self_id),
        now: messageTimestamp,
      })
    : { allowed: false, reason: "not-group" };
  const semanticFollowup =
    isGroup &&
    !parsed.wasMentioned &&
    !parsed.isReply &&
    !socialJoin.allowed &&
    !followupWatch.allowed &&
    followupWatch.reason === "watch-followup-unrelated" &&
    Number(followupWatch.score ?? 0) >= DIRECT_FOLLOWUP_SEMANTIC_MIN_RULE_SCORE &&
    followupWatch.state
      ? await semanticJudgeDirectFollowup({
          cfg,
          state: followupWatch.state,
          senderId,
          senderName: getSenderName(event),
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
  if (
    requireMention &&
    !parsed.wasMentioned &&
    !parsed.isReply &&
    !socialJoin.allowed &&
    !followupWatch.allowed &&
    !semanticFollowup.allowed
  ) {
    api.logger.debug(
      `[qq] skipping group message without bot mention: group=${groupId} user=${senderId} reason=${socialJoin.reason} followup=${followupWatch.reason} semantic=${semanticFollowup.reason}`,
    );
    return;
  }
  if (
    await tryHandleQqNativeImageRequest({
      api,
      cfg,
      account,
      event,
      rawBody,
      isGroup,
      groupId,
      senderId,
    })
  ) {
    return;
  }

  const engagementMode: "direct" | "ambient-join" | "ambient-passive" =
    parsed.wasMentioned || parsed.isReply || followupWatch.allowed || semanticFollowup.allowed
      ? "direct"
      : socialJoin.allowed
        ? "ambient-join"
        : "ambient-passive";
  const envelopeOptions = runtime.channel.reply.resolveEnvelopeFormatOptions(cfg);
  const fromLabel = isGroup
    ? `${getSenderName(event) || senderId}@group:${groupId}`
    : getSenderName(event) || `user:${senderId}`;
  const agentBody = parsed.imageUrls.length
    ? `${rawBody}${parsed.imageUrls.map((url, index) => `\n[图片${index + 1} URL: ${url}]`).join("")}`
    : rawBody;
  const body = runtime.channel.reply.formatAgentEnvelope({
    channel: "QQ",
    from: fromLabel,
    timestamp: (event.time ?? Math.floor(Date.now() / 1000)) * 1000,
    previousTimestamp,
    envelope: envelopeOptions,
    body: rawBody,
  });
  const mediaPayload = await resolveInboundMediaPayload({
    runtime,
    account,
    imageUrls: parsed.imageUrls,
  });
  const dynamicConversationSystemPrompt = buildQqConversationSystemPrompt({
    account,
    cfg,
    groupId,
    chatType: isGroup ? "group" : "direct",
    engagementMode,
  });
  const studyModeSystemPrompt = buildQqStudyModeSystemPrompt({
    account,
    chatType: isGroup ? "group" : "direct",
    hasImage: parsed.imageUrls.length > 0,
  });
  const followupPrompt =
    isGroup &&
    (followupWatch.allowed || semanticFollowup.allowed) &&
    !parsed.wasMentioned &&
    !parsed.isReply
      ? mergeSystemPrompts(
          "This looks like a same-speaker follow-up to an already active conversation with you. Treat it as a continuation, but stay concise.",
          semanticFollowup.allowed
            ? `Semantic follow-up judge confidence: ${semanticFollowup.confidence}.`
            : undefined,
        )
      : undefined;

  triggerGroupSocialLiveIngest({
    cfg,
    groupId,
    senderId,
    senderName: getSenderName(event),
    conversationLabel: fromLabel,
    rawBody,
    timestamp: new Date(messageTimestamp).toISOString(),
  });

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
    SenderName: getSenderName(event),
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
    WasMentioned: isGroup ? parsed.wasMentioned : undefined,
    MessageSid: event.message_id ? String(event.message_id) : undefined,
    Timestamp: messageTimestamp,
    OriginatingChannel: CHANNEL_ID,
    OriginatingTo: isGroup ? `qq:group:${groupId}` : `qq:${senderId}`,
    CommandAuthorized: true,
    ...mediaPayload,
  });

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
        event,
        payload,
        trackingKey,
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
      if (!account.enabled) {
        api.logger.info("[qq] channel disabled; OneBot listener not started");
        clearManagedState(ctx.stateDir);
        return;
      }
      const acceptedPaths = buildAcceptedPaths(account.websocketPath);

      server = createServer((_req, res) => {
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
        api.logger.info(
          `[qq] NapCat / OneBot connected on ws://${account.listenHost}:${account.listenPort}${account.websocketPath}`,
        );

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
    },
  };
}
