import { Type } from "@sinclair/typebox";
import { execFile } from "node:child_process";
import { createWriteStream } from "node:fs";
import fs from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { pathToFileURL } from "node:url";
import type { AnyAgentTool, OpenClawPluginApi } from "../../../dist/plugin-sdk/index.js";
import {
  buildRecallTrackingKey,
  debugInjectQqInboundMessage,
  debugInjectQqInboundSequence,
  getQqFile,
  getQqGroupFileUrl,
  getQqGroupFilesByFolder,
  getQqGroupInfo,
  getQqGroupMembers,
  getQqGroupRootFiles,
  getQqLoginInfo,
  getQqPacketStatus,
  getQqUserInfo,
  rememberSentQqMedia,
  recallRecentQqMessages,
  isOneBotActionAccepted,
  resolveQqConversationMemeBaseImage,
  sendQqMedia,
  sendQqPoke,
  sendQqSegments,
  sendQqVoice,
  sendQqLike,
  uploadQqGroupFile,
} from "./service.js";
import { resolveQqAccount } from "./accounts.js";
import { replayQqIngressDebugLog } from "./debug-replay.js";
import { buildQqMentionSegments, findQqMentionMember } from "./mention.js";
import { runQqMakeMeme } from "./meme.js";
import type { CoreConfig } from "./types.js";
import { normalizeOneBotMediaFile } from "../../shared/onebot-media-file.js";
import {
  resolveLocalQwenCloneTtsConfig,
  synthesizeLocalQwenCloneTts,
} from "../../shared/local-qwen-clone-tts.js";

const require = createRequire(import.meta.url);
const nodemailer = require("nodemailer") as typeof import("nodemailer");

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

const EXTERNAL_URL_RE = /^(?:[a-z][a-z0-9+.-]*:\/\/|data:)/i;

function toText(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function maybePacketBackendHint(message: unknown, wording: unknown): string | null {
  const combined = `${toText(message)} ${toText(wording)}`.toLowerCase();
  if (
    !combined.includes("packetbackend") &&
    !combined.includes("packet backend") &&
    !combined.includes("nativepacketclient")
  ) {
    return null;
  }
  return [
    "NapCat packetBackend is unavailable.",
    "Run qq_packet_status for details.",
    "(On macOS, packetBackend typically requires a supported QQ build; NapCat offsets start around build 40824.)",
  ].join(" ");
}

function findListedGroupFile(
  listResult: unknown,
  fileId: string,
): Record<string, unknown> | null {
  const payload = (listResult as { data?: unknown } | null)?.data;
  const files = Array.isArray((payload as Record<string, unknown> | undefined)?.files)
    ? (((payload as Record<string, unknown>).files as unknown[]) ?? [])
    : [];
  for (const entry of files) {
    const row = entry as Record<string, unknown>;
    const id = String(row.file_id ?? row.fileId ?? row.id ?? "").trim();
    if (id && id === fileId) {
      return row;
    }
  }
  return null;
}

async function findQqCachedGroupFile(params: {
  fileName?: string | null;
  expectedSize?: number | null;
}): Promise<string | null> {
  const fileName = String(params.fileName ?? "").trim();
  if (!fileName) {
    return null;
  }
  const candidates = [
    path.join(
      os.homedir(),
      "Library/Containers/com.tencent.qq/Data/Library/Application Support/QQ/NapCat/temp",
      fileName,
    ),
    path.join(os.homedir(), "Library/Containers/com.tencent.qq/Data/Documents/napcat/temp", fileName),
  ];
  for (const candidate of candidates) {
    try {
      const stat = await fs.stat(candidate);
      if (!stat.isFile()) {
        continue;
      }
      if (typeof params.expectedSize === "number" && Number.isFinite(params.expectedSize) && params.expectedSize > 0) {
        if (stat.size !== params.expectedSize) {
          continue;
        }
      }
      return candidate;
    } catch {
      // try next
    }
  }
  return null;
}

function resolveWorkspaceDir(cfg: CoreConfig): string | null {
  const workspace = (cfg as { agents?: { defaults?: { workspace?: string } } }).agents?.defaults
    ?.workspace;
  return typeof workspace === "string" && workspace.trim() ? workspace.trim() : null;
}

function resolveLocalPath(input: string, cfg: CoreConfig): string {
  const normalized = normalizeOneBotMediaFile(input).trim();
  if (!normalized) {
    return normalized;
  }
  if (EXTERNAL_URL_RE.test(normalized)) {
    return normalized;
  }
  if (path.isAbsolute(normalized)) {
    return normalized;
  }
  const workspaceDir = resolveWorkspaceDir(cfg);
  if (workspaceDir && path.isAbsolute(workspaceDir)) {
    return path.join(workspaceDir, normalized);
  }
  return path.resolve(normalized);
}

async function ensureUniqueFilePath(filePath: string): Promise<string> {
  try {
    const stat = await fs.stat(filePath);
    if (stat.isDirectory()) {
      throw new Error(`output_path is a directory: ${filePath}`);
    }
  } catch (err) {
    if ((err as { code?: string } | null)?.code === "ENOENT") {
      return filePath;
    }
  }

  const ext = path.extname(filePath);
  const base = ext ? filePath.slice(0, -ext.length) : filePath;
  for (let i = 1; i <= 50; i += 1) {
    const candidate = `${base}-${i}${ext}`;
    try {
      await fs.access(candidate);
    } catch {
      return candidate;
    }
  }
  const candidate = `${base}-${Date.now()}${ext}`;
  try {
    await fs.access(candidate);
  } catch {
    return candidate;
  }
  throw new Error(`output_path already exists: ${filePath}`);
}

function containsCjk(text: string) {
  return /[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/u.test(text);
}

function runExecFile(file: string, args: string[]): Promise<void> {
  return new Promise((resolve, reject) => {
    execFile(file, args, (error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

async function synthesizeQqVoiceFromTextWithConfig(
  text: string,
  rawVoiceSynthesisConfig: unknown,
): Promise<string> {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("text 不能为空");
  }
  const voiceSynthesisConfig = resolveLocalQwenCloneTtsConfig(rawVoiceSynthesisConfig);
  if (voiceSynthesisConfig.enabled) {
    const clonedOutputPath = await ensureUniqueFilePath(
      path.join(QQ_VOICE_OUTPUT_DIR, `qq-voice-${Date.now()}.wav`),
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
  const outputPath = await ensureUniqueFilePath(
    path.join(QQ_VOICE_OUTPUT_DIR, `qq-voice-${Date.now()}.aiff`),
  );
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const args = containsCjk(trimmed)
    ? ["-v", "Ting-Ting", trimmed, "-o", outputPath]
    : [trimmed, "-o", outputPath];
  await runExecFile("/usr/bin/say", args);
  return outputPath;
}

function guessFilenameFromUrl(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl);
    const basename = path.basename(url.pathname);
    const decoded = decodeURIComponent(basename);
    const trimmed = decoded.trim();
    return trimmed ? trimmed : null;
  } catch {
    return null;
  }
}

async function downloadToFile(params: { url: string; outputPath: string }): Promise<{ bytes: number }> {
  const response = await fetch(params.url, { method: "GET" });
  if (!response.ok) {
    throw new Error(`download failed: HTTP ${response.status}`);
  }
  if (!response.body) {
    throw new Error("download failed: empty response body");
  }
  await fs.mkdir(path.dirname(params.outputPath), { recursive: true });
  await pipeline(Readable.fromWeb(response.body as never), createWriteStream(params.outputPath));
  const stat = await fs.stat(params.outputPath);
  return { bytes: stat.size };
}

function decodeHtmlEntityText(text: string) {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">");
}

function guessImageExtension(params: { sourceUrl: string; contentType?: string | null }) {
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

const QqUserInfoSchema = Type.Object({
  query_type: Type.Union([Type.Literal("self"), Type.Literal("user"), Type.Literal("group")]),
  target_id: Type.Optional(Type.String()),
});

const QqGroupMembersSchema = Type.Object({
  group_id: Type.String(),
});

const QqSendLikeSchema = Type.Object({
  user_id: Type.String(),
  times: Type.Optional(Type.Number({ minimum: 1, maximum: 10 })),
});

const QqSendPokeSchema = Type.Object({
  target: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean()),
});

const QqSendImageSchema = Type.Object({
  image_url: Type.Optional(Type.String()),
  image_path: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean()),
});

const QqSendVoiceSchema = Type.Object({
  text: Type.Optional(Type.String()),
  audio_url: Type.Optional(Type.String()),
  audio_path: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  prefer_ptt: Type.Optional(Type.Boolean()),
  dry_run: Type.Optional(Type.Boolean()),
});

const QqSendMentionSchema = Type.Object({
  text: Type.String(),
  mention_user_id: Type.Optional(Type.String()),
  mention_name: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  reply_to_message_id: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean()),
});

const QqSendFileSchema = Type.Object({
  file_path: Type.String(),
  name: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean()),
});

const QqRecallSchema = Type.Object({
  count: Type.Optional(Type.Number({ minimum: 1, maximum: 5 })),
});

const QqPacketStatusSchema = Type.Object({});

const QqGroupFileListSchema = Type.Object({
  group_id: Type.String(),
  folder_id: Type.Optional(Type.String()),
});

const QqGroupFileUploadSchema = Type.Object({
  group_id: Type.String(),
  file_path: Type.String(),
  name: Type.Optional(Type.String()),
  folder_id: Type.Optional(Type.String()),
  upload_file: Type.Optional(Type.Boolean({ description: "Whether to stage/prepare rich-media upload (NapCat extension)." })),
});

const QqGroupFileUrlSchema = Type.Object({
  group_id: Type.String(),
  file_id: Type.String(),
  busid: Type.Union([Type.String(), Type.Number()]),
});

const QqGroupFileDownloadSchema = Type.Object({
  group_id: Type.String(),
  file_id: Type.String(),
  busid: Type.Union([Type.String(), Type.Number()]),
  folder_id: Type.Optional(Type.String()),
  output_path: Type.Optional(Type.String()),
});

const QqGroupFileInfoSchema = Type.Object({
  group_id: Type.String(),
  file_id: Type.String(),
  folder_id: Type.Optional(Type.String()),
});

const SearchNearbySchema = Type.Object({
  location: Type.String(),
  keyword: Type.String(),
  city: Type.Optional(Type.String()),
  type: Type.Optional(Type.String()),
});

const SendEmailSchema = Type.Object({
  receiver_email: Type.String(),
  subject: Type.String(),
  content: Type.String(),
  content_type: Type.Optional(Type.Union([Type.Literal("plain"), Type.Literal("html")])),
});

const QqMakeMemeSchema = Type.Object({
  image_url: Type.Optional(Type.String()),
  image_path: Type.Optional(Type.String()),
  top_text: Type.Optional(Type.String()),
  bottom_text: Type.Optional(Type.String()),
  center_text: Type.Optional(Type.String()),
  text: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  use_current_image: Type.Optional(Type.Boolean()),
  preserve_original_size: Type.Optional(Type.Boolean()),
  max_width: Type.Optional(Type.Number({ minimum: 64, maximum: 8192 })),
  max_height: Type.Optional(Type.Number({ minimum: 64, maximum: 8192 })),
});

const QqSearchImageSchema = Type.Object({
  query: Type.String(),
  count: Type.Optional(Type.Number({ minimum: 1, maximum: 8 })),
});

const QqDebugReplaySchema = Type.Object({
  conversation_key: Type.Optional(Type.String()),
  group_id: Type.Optional(Type.String()),
  account_id: Type.Optional(Type.String()),
  minutes: Type.Optional(Type.Number({ minimum: 1, maximum: 1440 })),
  limit: Type.Optional(Type.Number({ minimum: 5, maximum: 200 })),
  around_message_id: Type.Optional(Type.String()),
  keyword: Type.Optional(Type.String()),
  kinds: Type.Optional(Type.Array(Type.String())),
  log_path: Type.Optional(Type.String()),
});

const QqDebugInjectSchema = Type.Object({
  account_id: Type.Optional(Type.String()),
  chat_type: Type.Union([Type.Literal("group"), Type.Literal("direct")]),
  group_id: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
  sender_name: Type.Optional(Type.String()),
  text: Type.Optional(Type.String()),
  mention_self: Type.Optional(Type.Boolean()),
  reply_to_message_id: Type.Optional(Type.String()),
  image_path: Type.Optional(Type.String()),
  image_url: Type.Optional(Type.String()),
  image_paths: Type.Optional(Type.Array(Type.String())),
  image_urls: Type.Optional(Type.Array(Type.String())),
  message_id: Type.Optional(Type.Number()),
  dry_run: Type.Optional(Type.Boolean()),
});

const QqDebugInjectSequenceEntrySchema = Type.Object({
  user_id: Type.Optional(Type.String()),
  sender_name: Type.Optional(Type.String()),
  text: Type.Optional(Type.String()),
  mention_self: Type.Optional(Type.Boolean()),
  reply_to_message_id: Type.Optional(Type.String()),
  image_path: Type.Optional(Type.String()),
  image_url: Type.Optional(Type.String()),
  image_paths: Type.Optional(Type.Array(Type.String())),
  image_urls: Type.Optional(Type.Array(Type.String())),
  message_id: Type.Optional(Type.Number()),
  delay_ms: Type.Optional(Type.Number({ minimum: 0, maximum: 60_000 })),
});

const QqDebugInjectSequenceSchema = Type.Object({
  account_id: Type.Optional(Type.String()),
  chat_type: Type.Union([Type.Literal("group"), Type.Literal("direct")]),
  group_id: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
  sender_name: Type.Optional(Type.String()),
  start_message_id: Type.Optional(Type.Number()),
  start_time_ms: Type.Optional(Type.Number()),
  default_gap_ms: Type.Optional(Type.Number({ minimum: 0, maximum: 10_000 })),
  dry_run: Type.Optional(Type.Boolean()),
  entries: Type.Array(QqDebugInjectSequenceEntrySchema, { minItems: 1, maxItems: 50 }),
});

const AMAP_BASE_URL = "https://restapi.amap.com/v3";
const IMAGE_SEARCH_OUTPUT_DIR = path.join(os.tmpdir(), "openclaw-qq-search-images");
const QQ_MEDIA_PROXY_DIR = path.join(os.homedir(), ".openclaw", "canvas", "qq-media");
const QQ_MEDIA_PROXY_PATH = "/__openclaw__/canvas/qq-media";
const QQ_VOICE_OUTPUT_DIR = path.join(os.tmpdir(), "openclaw-qq-voice");

const CITY_KEYWORDS: Record<string, string[]> = {
  北京: ["北京", "beijing"],
  上海: ["上海", "shanghai"],
  广州: ["广州", "guangzhou"],
  深圳: ["深圳", "shenzhen"],
  杭州: ["杭州", "hangzhou"],
  成都: ["成都", "chengdu"],
  武汉: ["武汉", "wuhan"],
  西安: ["西安", "xian"],
  南京: ["南京", "nanjing"],
  天津: ["天津", "tianjin"],
  重庆: ["重庆", "chongqing"],
  苏州: ["苏州", "suzhou"],
};

function extractCityFromLocation(location: string): string {
  const lower = location.toLowerCase();
  for (const [city, keywords] of Object.entries(CITY_KEYWORDS)) {
    if (keywords.some((keyword) => lower.includes(keyword) || location.includes(keyword))) {
      return city;
    }
  }
  return "";
}

function resolveGatewayPort(cfg: CoreConfig): number {
  return typeof cfg.gateway?.port === "number" && Number.isFinite(cfg.gateway.port)
    ? cfg.gateway.port
    : 18789;
}

async function publishQqMediaProxyUrl(params: {
  cfg: CoreConfig;
  sourceFilePath: string;
  prefix: string;
}) {
  const ext = path.extname(params.sourceFilePath) || ".jpg";
  const outputName = `${params.prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`;
  const targetPath = path.join(QQ_MEDIA_PROXY_DIR, outputName);
  await fs.mkdir(QQ_MEDIA_PROXY_DIR, { recursive: true });
  await fs.copyFile(params.sourceFilePath, targetPath);
  return `http://127.0.0.1:${resolveGatewayPort(params.cfg)}${QQ_MEDIA_PROXY_PATH}/${encodeURIComponent(outputName)}`;
}

function normalizeStringArray(value: string | string[] | undefined): string[] {
  if (typeof value === "string") {
    return value.trim() ? [value.trim()] : [];
  }
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item).trim()).filter(Boolean);
}

type InjectedDebugImageReference = {
  field: "file" | "url";
  value: string;
};

async function resolveInjectedDebugImageReferences(params: {
  image_path?: string;
  image_url?: string;
  image_paths?: string[];
  image_urls?: string[];
}): Promise<InjectedDebugImageReference[]> {
  const refs: InjectedDebugImageReference[] = normalizeStringArray(params.image_url)
    .concat(normalizeStringArray(params.image_urls))
    .map((value) => ({ field: "url", value }));
  const paths = normalizeStringArray(params.image_path).concat(normalizeStringArray(params.image_paths));
  for (const imagePath of paths) {
    const resolvedPath = path.resolve(imagePath);
    const stat = await fs.stat(resolvedPath).catch(() => null);
    if (!stat?.isFile()) {
      throw new Error(`图片文件不存在或不可读: ${resolvedPath}`);
    }
    refs.push({
      field: "file",
      value: resolvedPath,
    });
  }
  return refs;
}

async function buildInjectedQqEvent(params: {
  account: ReturnType<typeof resolveQqAccount>;
  chatType: "group" | "direct";
  groupId?: string;
  defaultUserId?: string;
  defaultSenderName?: string;
  text?: string;
  mentionSelf?: boolean;
  replyToMessageId?: string;
  imagePath?: string;
  imageUrl?: string;
  imagePaths?: string[];
  imageUrls?: string[];
  userId?: string;
  senderName?: string;
  messageId: number;
  timeSeconds: number;
}) {
  const imageRefs = await resolveInjectedDebugImageReferences({
    image_path: params.imagePath,
    image_url: params.imageUrl,
    image_paths: params.imagePaths,
    image_urls: params.imageUrls,
  });
  const message: Array<{ type: string; data?: Record<string, string> }> = [];
  if (params.replyToMessageId?.trim()) {
    message.push({
      type: "reply",
      data: { id: params.replyToMessageId.trim() },
    });
  }
  if (params.mentionSelf && params.account.selfId?.trim()) {
    message.push({
      type: "at",
      data: { qq: params.account.selfId.trim() },
    });
  }
  if (params.text?.trim()) {
    message.push({
      type: "text",
      data: { text: params.text.trim() },
    });
  }
  for (const imageRef of imageRefs) {
    message.push({
      type: "image",
      data: imageRef.field === "file" ? { file: imageRef.value } : { url: imageRef.value },
    });
  }
  const userId = params.userId?.trim() || params.defaultUserId?.trim() || "10001";
  const senderName = params.senderName?.trim() || params.defaultSenderName?.trim() || "DebugUser";
  const groupId = params.groupId?.trim() || "673105016";
  return {
    event: {
      post_type: "message" as const,
      self_id: Number(params.account.selfId ?? 2509109290),
      message_id: params.messageId,
      message_type: params.chatType === "group" ? ("group" as const) : ("private" as const),
      sub_type: "normal",
      time: params.timeSeconds,
      user_id: Number(userId),
      group_id: params.chatType === "group" ? Number(groupId) : undefined,
      message,
      raw_message: params.text?.trim() ?? "",
      sender: {
        user_id: Number(userId),
        nickname: senderName,
        card: senderName,
      },
    },
    groupId,
    imageCount: imageRefs.length,
    userId,
  };
}

async function runSearchNearby(params: {
  location: string;
  keyword?: string;
  type?: string;
  city?: string;
}) {
  const searchKeyword = params.keyword?.trim() || params.type?.trim() || "";
  if (!searchKeyword) {
    return { ok: false, error: "缺少搜索关键词" };
  }
  const location = params.location?.trim();
  if (!location) {
    return { ok: false, error: "请提供地点名称" };
  }
  const apiKey = (process.env.AMAP_API_KEY || "").trim();
  if (!apiKey) {
    return { ok: false, error: "地图搜索功能不可用（AMAP_API_KEY 未配置）" };
  }

  const city = params.city?.trim() || extractCityFromLocation(location);
  const query = `${location} ${searchKeyword}`.trim();
  const requestUrl = new URL(`${AMAP_BASE_URL}/place/text`);
  requestUrl.searchParams.set("key", apiKey);
  requestUrl.searchParams.set("keywords", query);
  requestUrl.searchParams.set("types", "");
  requestUrl.searchParams.set("offset", "5");
  requestUrl.searchParams.set("extensions", "base");
  if (city) {
    requestUrl.searchParams.set("city", city);
  }

  const response = await fetch(requestUrl, { method: "GET" });
  if (!response.ok) {
    return { ok: false, error: `地图搜索失败: HTTP ${response.status}` };
  }
  const data = (await response.json()) as Record<string, unknown>;
  if (String(data.status ?? "") !== "1") {
    return { ok: false, error: `地图搜索失败: ${String(data.info ?? "未知错误")}` };
  }
  const pois = Array.isArray(data.pois) ? data.pois : [];
  const results = pois.slice(0, 5).map((poi) => {
    const row = poi as Record<string, unknown>;
    return {
      name: String(row.name ?? "未知"),
      address: String(row.address ?? "地址未知"),
      distance: String(row.distance ?? ""),
      type: String(row.type ?? ""),
    };
  });
  return {
    ok: true,
    location,
    keyword: searchKeyword,
    city,
    count: results.length,
    results,
  };
}

async function runSendEmail(params: {
  receiver_email: string;
  subject: string;
  content: string;
  content_type?: "plain" | "html";
}) {
  const sender = (process.env.QQ_EMAIL_SENDER || "").trim();
  const password = (process.env.QQ_EMAIL_PASSWORD || "").trim();
  if (!sender || !password) {
    return { ok: false, error: "邮件功能未配置（缺少 QQ_EMAIL_SENDER 或 QQ_EMAIL_PASSWORD）" };
  }

  const receiver = params.receiver_email?.trim();
  if (!receiver || !receiver.includes("@")) {
    return { ok: false, error: `邮箱地址格式不正确: ${params.receiver_email}` };
  }
  const subject = params.subject?.trim();
  const content = params.content?.trim();
  if (!subject || !content) {
    return { ok: false, error: "邮件主题和内容不能为空" };
  }

  const transporter = nodemailer.createTransport({
    host: "smtp.qq.com",
    port: 587,
    secure: false,
    auth: {
      user: sender,
      pass: password,
    },
  });

  await transporter.sendMail({
    from: sender,
    to: receiver,
    subject,
    [params.content_type === "html" ? "html" : "text"]: content,
  });

  return {
    ok: true,
    receiver_email: receiver,
    subject,
    sender_email: sender,
  };
}

export async function runQqSearchImage(params: { query: string; count?: number }, cfg: CoreConfig) {
  const query = params.query.trim();
  if (!query) {
    return { ok: false, error: "query 不能为空" };
  }

  const count = Math.max(1, Math.min(8, Number(params.count ?? 4)));
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
    throw new Error(`搜图失败: HTTP ${response.status}`);
  }

  const html = await response.text();
  const matches = [...html.matchAll(/class="iusc"[^>]+m="([^"]+)"/g)];
  const imageUrls = Array.from(
    new Set(
      matches
        .map((match) => match[1])
        .map((value) => decodeHtmlEntityText(value))
        .map((value) => {
          try {
            return JSON.parse(value).murl as string;
          } catch {
            return "";
          }
        })
        .filter((value) => /^https?:\/\//i.test(value)),
    ),
  ).slice(0, count);

  if (imageUrls.length === 0) {
    return { ok: false, error: "没有搜到可用图片" };
  }

  await fs.mkdir(IMAGE_SEARCH_OUTPUT_DIR, { recursive: true });
  const localFilePaths: string[] = [];
  for (const imageUrl of imageUrls) {
    try {
      const imageResponse = await fetch(imageUrl);
      if (!imageResponse.ok) {
        continue;
      }
      const contentType = imageResponse.headers.get("content-type");
      if (contentType && !contentType.toLowerCase().startsWith("image/")) {
        continue;
      }
      const buffer = Buffer.from(await imageResponse.arrayBuffer());
      const ext = guessImageExtension({ sourceUrl: imageUrl, contentType });
      const filePath = path.join(
        IMAGE_SEARCH_OUTPUT_DIR,
        `search-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`,
      );
      await fs.writeFile(filePath, buffer);
      localFilePaths.push(filePath);
    } catch {
      // ignore individual image failures
    }
  }

  if (localFilePaths.length === 0) {
    return { ok: false, error: "搜到图片了 但下载失败" };
  }

  const primaryMediaUrl = await publishQqMediaProxyUrl({
    cfg,
    sourceFilePath: localFilePaths[0],
    prefix: "search",
  });

  return {
    ok: true,
    query,
    count: localFilePaths.length,
    media_url: primaryMediaUrl,
    mediaUrl: primaryMediaUrl,
    primary_media_url: primaryMediaUrl,
    primaryMediaUrl: primaryMediaUrl,
    note: "图片会由系统自动发送，请不要重复输出链接、文件路径或 [[media:...]]",
  };
}

function parseQqSendTarget(target: string): {
  targetKind: "user" | "group";
  targetId: string;
} | null {
  const trimmed = target.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("qq:group:")) {
    const targetId = trimmed.slice("qq:group:".length).trim();
    return targetId ? { targetKind: "group", targetId } : null;
  }
  if (trimmed.startsWith("group:")) {
    const targetId = trimmed.slice("group:".length).trim();
    return targetId ? { targetKind: "group", targetId } : null;
  }
  if (trimmed.startsWith("qq:user:")) {
    const targetId = trimmed.slice("qq:user:".length).trim();
    return targetId ? { targetKind: "user", targetId } : null;
  }
  if (trimmed.startsWith("user:")) {
    const targetId = trimmed.slice("user:".length).trim();
    return targetId ? { targetKind: "user", targetId } : null;
  }
  if (/^qq:\d+$/u.test(trimmed)) {
    return { targetKind: "user", targetId: trimmed.slice("qq:".length) };
  }
  if (/^\d+$/u.test(trimmed)) {
    return { targetKind: "user", targetId: trimmed };
  }
  return null;
}

async function resolveQqSendImageTarget(params: {
  api: OpenClawPluginApi;
  ctx: {
    agentId?: string;
    sessionKey?: string;
    messageChannel?: string;
    agentAccountId?: string;
  };
  explicitTarget?: string;
}) {
  const explicit = params.explicitTarget?.trim();
  if (explicit) {
    const parsed = parseQqSendTarget(explicit);
    if (!parsed) {
      throw new Error(`target 格式不对: ${explicit}`);
    }
    return {
      ...parsed,
      accountId: params.ctx.agentAccountId?.trim() || undefined,
      source: "explicit" as const,
    };
  }

  const sessionKey = params.ctx.sessionKey?.trim();
  if (!sessionKey) {
    throw new Error("当前上下文没有 sessionKey，无法推断 QQ 目标");
  }
  const agentId = params.ctx.agentId?.trim() || "main";
  const storePath = params.api.runtime.channel.session.resolveStorePath(
    (params.api.config as { session?: { store?: string } }).session?.store,
    { agentId },
  );
  const raw = await fs.readFile(storePath, "utf8");
  const store = JSON.parse(raw) as Record<string, Record<string, unknown>>;
  const entry = store[sessionKey];
  if (!entry) {
    throw new Error(`当前 session 未找到: ${sessionKey}`);
  }
  const deliveryContext = (entry.deliveryContext ?? {}) as Record<string, unknown>;
  const channel =
    (typeof deliveryContext.channel === "string" ? deliveryContext.channel : undefined) ??
    (typeof entry.lastChannel === "string" ? entry.lastChannel : undefined) ??
    params.ctx.messageChannel;
  if (channel !== "qq") {
    throw new Error("当前会话不是 QQ 会话，且没有显式 target");
  }
  const toValue =
    (typeof deliveryContext.to === "string" ? deliveryContext.to : undefined) ??
    (typeof entry.lastTo === "string" ? entry.lastTo : undefined) ??
    "";
  const parsed = parseQqSendTarget(toValue);
  if (!parsed) {
    throw new Error(`当前会话缺少可用的 QQ 目标: ${toValue || "(empty)"}`);
  }
  return {
    ...parsed,
    accountId:
      (typeof deliveryContext.accountId === "string" ? deliveryContext.accountId : undefined) ??
      (typeof entry.lastAccountId === "string" ? entry.lastAccountId : undefined) ??
      params.ctx.agentAccountId?.trim() ??
      undefined,
    source: "session" as const,
  };
}

async function resolveQqMentionRecipient(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  mentionUserId?: string;
  mentionName?: string;
}) {
  const mentionUserId = params.mentionUserId?.trim();
  if (mentionUserId) {
    const result = await getQqGroupMembers({
      cfg: params.cfg,
      accountId: params.accountId,
      groupId: params.groupId,
    }).catch(() => null);
    const members = Array.isArray(result?.data) ? result.data : [];
    return findQqMentionMember({
      members,
      mentionUserId,
      mentionName: params.mentionName,
    });
  }

  const result = await getQqGroupMembers({
    cfg: params.cfg,
    accountId: params.accountId,
    groupId: params.groupId,
  });
  const ok = result.status === "ok" || result.retcode === 0;
  if (!ok) {
    throw new Error(result.message ?? result.wording ?? "获取群成员列表失败");
  }
  const members = Array.isArray(result.data) ? result.data : [];
  return findQqMentionMember({
    members,
    mentionName: params.mentionName,
  });
}

function buildQqConversationKeyForTarget(params: {
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
}) {
  return `qq:${params.accountId ?? "default"}:${params.targetKind === "group" ? "group" : "direct"}:${params.targetId}`;
}

export function registerQqNativeTools(api: OpenClawPluginApi) {
  api.registerTool({
    name: "qq_group_files_list",
    label: "QQ Group Files List",
    description: "List files/folders in a QQ group folder through the active QQ / NapCat connection.",
    parameters: QqGroupFileListSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as { group_id?: string; folder_id?: string };
      const groupId = params.group_id?.trim();
      const folderId = params.folder_id?.trim();
      if (!groupId) {
        return json({ ok: false, error: "group_id required" });
      }
      try {
        const cfg = api.config as CoreConfig;
        const result = folderId
          ? await getQqGroupFilesByFolder({ cfg, groupId, folderId })
          : await getQqGroupRootFiles({ cfg, groupId });
        const ok = result.status === "ok" || result.retcode === 0;
        const payload = (result.data ?? {}) as Record<string, unknown>;
        const files = Array.isArray(payload.files) ? payload.files : [];
        const folders = Array.isArray(payload.folders) ? payload.folders : [];
        return json({
          ok,
          group_id: groupId,
          folder_id: folderId ?? null,
          file_count: files.length,
          folder_count: folders.length,
          files,
          folders,
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_group_file_info",
    label: "QQ Group File Info",
    description:
      "Get a QQ group file's metadata by listing its containing folder through the active QQ / NapCat connection.",
    parameters: QqGroupFileInfoSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as { group_id?: string; file_id?: string; folder_id?: string };
      const groupId = params.group_id?.trim();
      const fileId = params.file_id?.trim();
      const folderId = params.folder_id?.trim();
      if (!groupId) {
        return json({ ok: false, error: "group_id required" });
      }
      if (!fileId) {
        return json({ ok: false, error: "file_id required" });
      }
      try {
        const cfg = api.config as CoreConfig;
        const result = folderId
          ? await getQqGroupFilesByFolder({ cfg, groupId, folderId })
          : await getQqGroupRootFiles({ cfg, groupId });
        const ok = result.status === "ok" || result.retcode === 0;
        if (!ok) {
          return json({
            ok: false,
            group_id: groupId,
            folder_id: folderId ?? null,
            error: result.message ?? result.wording ?? "get_group_files failed",
            data: result.data ?? null,
          });
        }
        const payload = (result.data ?? {}) as Record<string, unknown>;
        const files = Array.isArray(payload.files) ? payload.files : [];
        const file =
          files.find((entry) => {
            const row = entry as Record<string, unknown>;
            const id = String(row.file_id ?? row.fileId ?? row.id ?? "").trim();
            return id && id === fileId;
          }) ?? null;
        if (!file) {
          return json({
            ok: false,
            group_id: groupId,
            folder_id: folderId ?? null,
            file_id: fileId,
            error: "file not found in the listed folder (try specifying folder_id)",
            file_count: files.length,
          });
        }
        return json({
          ok: true,
          group_id: groupId,
          folder_id: folderId ?? null,
          file_id: fileId,
          file,
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_group_file_url",
    label: "QQ Group File URL",
    description: "Get a QQ group file download URL through the active QQ / NapCat connection.",
    parameters: QqGroupFileUrlSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as { group_id?: string; file_id?: string; busid?: string | number };
      const groupId = params.group_id?.trim();
      const fileId = params.file_id?.trim();
      if (!groupId) {
        return json({ ok: false, error: "group_id required" });
      }
      if (!fileId) {
        return json({ ok: false, error: "file_id required" });
      }
      if (params.busid === undefined || String(params.busid).trim() === "") {
        return json({ ok: false, error: "busid required" });
      }
      try {
        const result = await getQqGroupFileUrl({
          cfg: api.config as CoreConfig,
          groupId,
          fileId,
          busid: params.busid,
        });
        const ok = result.status === "ok" || result.retcode === 0;
        const url = String((result.data as Record<string, unknown> | undefined)?.url ?? "");
        return json({
          ok,
          group_id: groupId,
          file_id: fileId,
          busid: params.busid,
          url: url || null,
          status: result.status ?? null,
          retcode: result.retcode ?? null,
          message: result.message ?? null,
          wording: result.wording ?? null,
          error: ok ? null : result.message ?? result.wording ?? "get_group_file_url failed",
          hint: ok ? null : maybePacketBackendHint(result.message, result.wording),
          data: result.data ?? null,
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_group_file_download",
    label: "QQ Group File Download",
    description:
      "Download a QQ group file to a local path. It tries get_group_file_url first, then falls back to NapCat get_file, so it may still work even when packetBackend is unavailable.",
    parameters: QqGroupFileDownloadSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        group_id?: string;
        file_id?: string;
        busid?: string | number;
        folder_id?: string;
        output_path?: string;
      };
      const groupId = params.group_id?.trim();
      const fileId = params.file_id?.trim();
      const folderId = params.folder_id?.trim();
      if (!groupId) {
        return json({ ok: false, error: "group_id required" });
      }
      if (!fileId) {
        return json({ ok: false, error: "file_id required" });
      }
      if (params.busid === undefined || String(params.busid).trim() === "") {
        return json({ ok: false, error: "busid required" });
      }
      try {
        const cfg = api.config as CoreConfig;
        const urlResult = await getQqGroupFileUrl({ cfg, groupId, fileId, busid: params.busid });
        const urlOk = urlResult.status === "ok" || urlResult.retcode === 0;
        const url = String((urlResult.data as Record<string, unknown> | undefined)?.url ?? "").trim();
        const urlHint = maybePacketBackendHint(urlResult.message, urlResult.wording);

        let downloadSource: "group_file_url" | "get_file" | "napcat_temp_cache" = "group_file_url";
        let remoteUrl = url;
        let localSourcePath: string | null = null;
        let listedFile: Record<string, unknown> | null = null;

        if (!urlOk || !url) {
          let listResult: unknown = null;
          try {
            if (folderId) {
              listResult = await getQqGroupFilesByFolder({ cfg, groupId, folderId });
            } else {
              listResult = await getQqGroupRootFiles({ cfg, groupId });
            }
          } catch {
            // Best-effort hydration for NapCat's in-memory file_id -> modelId cache.
          }
          listedFile = findListedGroupFile(listResult, fileId);

          let fileResult:
            | {
                status?: string | null;
                retcode?: number | null;
                message?: string | null;
                wording?: string | null;
                data?: unknown;
              }
            | null = null;
          let fileOk = false;
          let fileCandidate = "";

          const cachedFile = listedFile
            ? await findQqCachedGroupFile({
                fileName: String(listedFile.file_name ?? listedFile.fileName ?? "").trim(),
                expectedSize: Number(listedFile.file_size ?? listedFile.size ?? 0) || null,
              })
            : null;
          if (cachedFile) {
            fileOk = true;
            fileCandidate = cachedFile;
            downloadSource = "napcat_temp_cache";
          }
          if (!fileOk || !fileCandidate) {
            try {
              fileResult = await getQqFile({ cfg, fileId });
              fileOk = fileResult.status === "ok" || fileResult.retcode === 0;
              const filePayload = (fileResult.data ?? {}) as Record<string, unknown>;
              fileCandidate = normalizeOneBotMediaFile(
                String(filePayload.file ?? filePayload.url ?? "").trim(),
              ).trim();
            } catch (error) {
              fileResult = {
                status: "failed",
                retcode: null,
                message: error instanceof Error ? error.message : String(error),
                wording: error instanceof Error ? error.message : String(error),
                data: null,
              };
            }
          }
          if (!fileOk || !fileCandidate) {
            return json({
              ok: false,
              group_id: groupId,
              folder_id: folderId ?? null,
              file_id: fileId,
              busid: params.busid,
              error: urlResult.message ?? urlResult.wording ?? "failed to get file url",
              hint: urlHint,
              status: urlResult.status ?? null,
              retcode: urlResult.retcode ?? null,
              message: urlResult.message ?? null,
              wording: urlResult.wording ?? null,
              data: urlResult.data ?? null,
              fallback: {
                ok: fileOk,
                error: fileResult?.message ?? fileResult?.wording ?? "get_file failed",
                status: fileResult?.status ?? null,
                retcode: fileResult?.retcode ?? null,
                message: fileResult?.message ?? null,
                wording: fileResult?.wording ?? null,
                data: fileResult?.data ?? null,
              },
            });
          }
          if (downloadSource !== "napcat_temp_cache") {
            downloadSource = "get_file";
          }
          localSourcePath = fileCandidate;
          remoteUrl = "";
        }

        const outputDir = path.join(os.tmpdir(), "openclaw-qq-group-files");
        const preferredPath = (() => {
          const explicit = params.output_path?.trim();
          if (explicit) {
            return resolveLocalPath(explicit, cfg);
          }
          if (downloadSource === "group_file_url") {
            const guessedName = guessFilenameFromUrl(remoteUrl);
            const safeName = guessedName ? `qq-${groupId}-${fileId}-${guessedName}` : `qq-${groupId}-${fileId}.bin`;
            return path.join(outputDir, safeName);
          }
          const basename = localSourcePath ? path.basename(localSourcePath).trim() : "";
          const safeName = basename ? `qq-${groupId}-${fileId}-${basename}` : `qq-${groupId}-${fileId}.bin`;
          return path.join(outputDir, safeName);
        })();
        const outputPath = await ensureUniqueFilePath(preferredPath);

        let bytes = 0;
        if (downloadSource === "group_file_url") {
          ({ bytes } = await downloadToFile({ url: remoteUrl, outputPath }));
        } else if (EXTERNAL_URL_RE.test(localSourcePath ?? "")) {
          ({ bytes } = await downloadToFile({ url: localSourcePath ?? "", outputPath }));
        } else {
          await fs.mkdir(path.dirname(outputPath), { recursive: true });
          await fs.copyFile(localSourcePath ?? "", outputPath);
          const stat = await fs.stat(outputPath);
          bytes = stat.size;
        }
        return json({
          ok: true,
          group_id: groupId,
          folder_id: folderId ?? null,
          file_id: fileId,
          busid: params.busid,
          url: remoteUrl || null,
          download_source: downloadSource,
          source_path: downloadSource === "get_file" ? localSourcePath : null,
          output_path: outputPath,
          bytes,
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_group_file_upload",
    label: "QQ Group File Upload",
    description: "Upload a local file into a QQ group folder through the active QQ / NapCat connection.",
    parameters: QqGroupFileUploadSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        group_id?: string;
        file_path?: string;
        name?: string;
        folder_id?: string;
        upload_file?: boolean;
      };
      const groupId = params.group_id?.trim();
      const filePathInput = params.file_path?.trim();
      const folderId = params.folder_id?.trim();
      const requestedUploadFile = typeof params.upload_file === "boolean" ? params.upload_file : undefined;
      if (!groupId) {
        return json({ ok: false, error: "group_id required" });
      }
      if (!filePathInput) {
        return json({ ok: false, error: "file_path required" });
      }
      try {
        const cfg = api.config as CoreConfig;
        const resolvedPath = resolveLocalPath(filePathInput, cfg);
        if (!resolvedPath || EXTERNAL_URL_RE.test(resolvedPath)) {
          return json({
            ok: false,
            error: "file_path must be a local file path (not a URL)",
            file_path: filePathInput,
          });
        }
        const stat = await fs.stat(resolvedPath);
        if (!stat.isFile()) {
          return json({ ok: false, error: `not a file: ${resolvedPath}` });
        }
        const name = (params.name?.trim() || path.basename(resolvedPath)).trim();
        if (!name) {
          return json({ ok: false, error: "name cannot be empty" });
        }

        const attempts: Array<{
          source: "local_path" | "proxy_url";
          upload_file: boolean | null;
          status: string | null;
          retcode: number | null;
          message: string | null;
          wording: string | null;
        }> = [];

        const attemptUpload = async (params: {
          file: string;
          source: "local_path" | "proxy_url";
          uploadFile?: boolean;
        }) => {
          const result = await uploadQqGroupFile({
            cfg,
            groupId,
            file: params.file,
            name,
            folderId,
            uploadFile: params.uploadFile,
          });
          attempts.push({
            source: params.source,
            upload_file: typeof params.uploadFile === "boolean" ? params.uploadFile : null,
            status: result.status ?? null,
            retcode: result.retcode ?? null,
            message: result.message ?? null,
            wording: result.wording ?? null,
          });
          return { result, ok: result.status === "ok" || result.retcode === 0 };
        };

        const primary = await attemptUpload({
          file: resolvedPath,
          source: "local_path",
          uploadFile: requestedUploadFile,
        });
        if (primary.ok) {
          return json({
            ok: true,
            group_id: groupId,
            folder_id: folderId ?? null,
            file_path: resolvedPath,
            name,
            upload_source: "local_path",
            upload_file: typeof requestedUploadFile === "boolean" ? requestedUploadFile : null,
            attempts,
            data: primary.result.data ?? null,
          });
        }

        if (requestedUploadFile === undefined) {
          const relaxed = await attemptUpload({
            file: resolvedPath,
            source: "local_path",
            uploadFile: false,
          });
          if (relaxed.ok) {
            return json({
              ok: true,
              group_id: groupId,
              folder_id: folderId ?? null,
              file_path: resolvedPath,
              name,
              upload_source: "local_path",
              upload_file: false,
              attempts,
              data: relaxed.result.data ?? null,
            });
          }
        }

        const proxyUrl = await publishQqMediaProxyUrl({
          cfg,
          sourceFilePath: resolvedPath,
          prefix: "qq-file",
        });

        const fallback = await attemptUpload({
          file: proxyUrl,
          source: "proxy_url",
          uploadFile: requestedUploadFile,
        });
        if (fallback.ok) {
          return json({
            ok: true,
            group_id: groupId,
            folder_id: folderId ?? null,
            file_path: resolvedPath,
            upload_source: "proxy_url",
            proxy_url: proxyUrl,
            name,
            upload_file: typeof requestedUploadFile === "boolean" ? requestedUploadFile : null,
            attempts,
            data: fallback.result.data ?? null,
          });
        }

        if (requestedUploadFile === undefined) {
          const relaxedFallback = await attemptUpload({
            file: proxyUrl,
            source: "proxy_url",
            uploadFile: false,
          });
          if (relaxedFallback.ok) {
            return json({
              ok: true,
              group_id: groupId,
              folder_id: folderId ?? null,
              file_path: resolvedPath,
              upload_source: "proxy_url",
              proxy_url: proxyUrl,
              name,
              upload_file: false,
              attempts,
              data: relaxedFallback.result.data ?? null,
            });
          }
        }

        const last = attempts[attempts.length - 1] ?? null;
        return json({
          ok: false,
          group_id: groupId,
          folder_id: folderId ?? null,
          file_path: resolvedPath,
          upload_source: last?.source ?? "local_path",
          proxy_url: proxyUrl,
          name,
          upload_file: typeof requestedUploadFile === "boolean" ? requestedUploadFile : null,
          attempts,
          error: primary.result.message ?? primary.result.wording ?? "upload failed",
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_packet_status",
    label: "QQ Packet Status",
    description:
      "Check NapCat packetBackend status. Useful for diagnosing get_group_file_url and other packet-dependent APIs, but qq_group_file_download may still work via its get_file fallback.",
    parameters: QqPacketStatusSchema,
    async execute() {
      try {
        const result = await getQqPacketStatus({ cfg: api.config as CoreConfig });
        const ok = result.status === "ok" || result.retcode === 0;
        return json({
          ok,
          status: result.status ?? null,
          retcode: result.retcode ?? null,
          message: result.message ?? null,
          wording: result.wording ?? null,
          error: ok ? null : result.message ?? result.wording ?? "packetBackend unavailable",
          data: result.data ?? null,
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_user_info",
    label: "QQ User Info",
    description:
      "Get QQ self info, user info, or group info through the active QQ / NapCat connection.",
    parameters: QqUserInfoSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        query_type?: "self" | "user" | "group";
        target_id?: string;
      };
      const cfg = api.config as CoreConfig;
      try {
        switch (params.query_type) {
          case "self": {
            const result = await getQqLoginInfo({ cfg });
            return json({
              ok: result.status === "ok" || result.retcode === 0,
              query_type: "self",
              data: result.data ?? null,
            });
          }
          case "user": {
            const targetId = params.target_id?.trim();
            if (!targetId) {
              return json({ ok: false, error: "target_id required for query_type=user" });
            }
            const result = await getQqUserInfo({ cfg, userId: targetId });
            return json({
              ok: result.status === "ok" || result.retcode === 0,
              query_type: "user",
              target_id: targetId,
              data: result.data ?? null,
            });
          }
          case "group": {
            const targetId = params.target_id?.trim();
            if (!targetId) {
              return json({ ok: false, error: "target_id required for query_type=group" });
            }
            const result = await getQqGroupInfo({ cfg, groupId: targetId });
            return json({
              ok: result.status === "ok" || result.retcode === 0,
              query_type: "group",
              target_id: targetId,
              data: result.data ?? null,
            });
          }
          default:
            return json({ ok: false, error: "query_type must be one of: self, user, group" });
        }
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_group_members",
    label: "QQ Group Members",
    description: "Get the member list for a QQ group through the active QQ / NapCat connection.",
    parameters: QqGroupMembersSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as { group_id?: string };
      const groupId = params.group_id?.trim();
      if (!groupId) {
        return json({ ok: false, error: "group_id required" });
      }
      try {
        const result = await getQqGroupMembers({
          cfg: api.config as CoreConfig,
          groupId,
        });
        const list = Array.isArray(result.data) ? result.data : [];
        return json({
          ok: result.status === "ok" || result.retcode === 0,
          group_id: groupId,
          count: list.length,
          members: list,
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_send_like",
    label: "QQ Send Like",
    description: "Send profile likes to a QQ user through the active QQ / NapCat connection.",
    parameters: QqSendLikeSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as { user_id?: string; times?: number };
      const userId = params.user_id?.trim();
      if (!userId) {
        return json({ ok: false, error: "user_id required" });
      }
      try {
        const result = await sendQqLike({
          cfg: api.config as CoreConfig,
          userId,
          times: params.times,
        });
        return json({
          ok: result.status === "ok" || result.retcode === 0,
          user_id: userId,
          times: Math.max(1, Math.min(10, Number(params.times ?? 10))),
          data: result.data ?? null,
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_send_poke",
        label: "QQ Send Poke",
        description:
          "Send a QQ 戳一戳 / poke to the current conversation target. In direct chats it defaults to the current peer; in group chats it defaults to the current sender unless user_id is provided.",
        parameters: QqSendPokeSchema,
        async execute(_toolCallId, rawParams) {
          const params = (rawParams ?? {}) as {
            target?: string;
            user_id?: string;
            dry_run?: boolean;
          };
          try {
            const target = await resolveQqSendImageTarget({
              api,
              ctx,
              explicitTarget: params.target,
            });
            const explicitUserId = params.user_id?.trim() || undefined;
            const requesterUserId = ctx.requesterSenderId?.trim() || undefined;
            const pokeUserId =
              target.targetKind === "user"
                ? explicitUserId ?? target.targetId
                : explicitUserId ?? requesterUserId;
            if (target.targetKind === "group" && !pokeUserId) {
              return json({
                ok: false,
                error: "group poke requires user_id, or must be called from a QQ group session with a known current sender",
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
              });
            }
            if (params.dry_run === true) {
              return json({
                ok: true,
                dry_run: true,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                user_id: pokeUserId ?? null,
              });
            }
            const result = await sendQqPoke({
              cfg: api.config as CoreConfig,
              accountId: target.accountId,
              targetKind: target.targetKind,
              targetId: target.targetId,
              userId: pokeUserId,
            });
            return json({
              ok: isOneBotActionAccepted(result),
              source: target.source,
              target_kind: target.targetKind,
              target_id: target.targetId,
              account_id: target.accountId ?? null,
              user_id: pokeUserId ?? null,
              status: result.status ?? null,
              retcode: result.retcode ?? null,
              message: result.message ?? null,
              wording: result.wording ?? null,
              data: result.data ?? null,
            });
          } catch (err) {
            return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
          }
        },
      }) as AnyAgentTool) as never,
    { name: "qq_send_poke" },
  );

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_send_mention",
        label: "QQ Send Mention",
        description:
          "Send a QQ group message that @mentions a specific member, resolving by QQ id or current group nickname/card.",
        parameters: QqSendMentionSchema,
        async execute(_toolCallId, rawParams) {
          const params = (rawParams ?? {}) as {
            text?: string;
            mention_user_id?: string;
            mention_name?: string;
            target?: string;
            reply_to_message_id?: string;
            dry_run?: boolean;
          };
          const text = params.text?.trim() ?? "";
          if (!text) {
            return json({ ok: false, error: "text required" });
          }
          if (!params.mention_user_id?.trim() && !params.mention_name?.trim()) {
            return json({ ok: false, error: "mention_user_id 或 mention_name 至少提供一个" });
          }
          try {
            const cfg = api.config as CoreConfig;
            const explicitTarget = params.target?.trim();
            const target = await resolveQqSendImageTarget({
              api,
              ctx,
              explicitTarget:
                explicitTarget && /^\d+$/u.test(explicitTarget)
                  ? `group:${explicitTarget}`
                  : explicitTarget,
            });
            if (target.targetKind !== "group") {
              return json({
                ok: false,
                error: "qq_send_mention 只支持 QQ 群聊目标，请提供群 target 或在群会话里调用",
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
              });
            }
            const member = await resolveQqMentionRecipient({
              cfg,
              accountId: target.accountId,
              groupId: target.targetId,
              mentionUserId: params.mention_user_id,
              mentionName: params.mention_name,
            });
            const message = buildQqMentionSegments({
              mentionUserId: member.userId,
              text,
              replyToMessageId: params.reply_to_message_id,
            });
            if (params.dry_run === true) {
              return json({
                ok: true,
                dry_run: true,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                mention_user_id: member.userId,
                mention_name: member.displayName,
                mention_card: member.card,
                mention_nickname: member.nickname,
                mention_match: member.match,
                text,
                reply_to_message_id: params.reply_to_message_id?.trim() ?? null,
                message,
              });
            }
            const result = await sendQqSegments({
              cfg,
              accountId: target.accountId,
              targetKind: "group",
              targetId: target.targetId,
              message: message as never,
            });
            return json({
              ok: result.status === "ok" || result.retcode === 0,
              source: target.source,
              target_kind: target.targetKind,
              target_id: target.targetId,
              account_id: target.accountId ?? null,
              mention_user_id: member.userId,
              mention_name: member.displayName,
              mention_card: member.card,
              mention_nickname: member.nickname,
              mention_match: member.match,
              text,
              reply_to_message_id: params.reply_to_message_id?.trim() ?? null,
              data: result.data ?? null,
              message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
              message,
            });
          } catch (err) {
            return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
          }
        },
      }) as AnyAgentTool) as never,
    { name: "qq_send_mention" },
  );

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_send_image",
        label: "QQ Send Image",
        description:
          "Send an image to the current QQ conversation, or to an explicit QQ target, from an image URL or local path.",
        parameters: QqSendImageSchema,
        async execute(_toolCallId, rawParams) {
          const params = (rawParams ?? {}) as {
            image_url?: string;
            image_path?: string;
            caption?: string;
            target?: string;
            dry_run?: boolean;
          };
          const imageUrl = params.image_url?.trim();
          const imagePath = params.image_path?.trim();
          if (!imageUrl && !imagePath) {
            return json({ ok: false, error: "image_url 或 image_path 至少提供一个" });
          }
          try {
            const target = await resolveQqSendImageTarget({
              api,
              ctx,
              explicitTarget: params.target,
            });
            const mediaUrl = imagePath ? api.resolvePath(imagePath) : (imageUrl ?? "");
            if (params.dry_run === true) {
              return json({
                ok: true,
                dry_run: true,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                media_url: mediaUrl,
                caption: params.caption?.trim() ?? "",
              });
            }
            const result = await sendQqMedia({
              cfg: api.config as CoreConfig,
              accountId: target.accountId,
              targetKind: target.targetKind,
              targetId: target.targetId,
              text: params.caption?.trim() ?? "",
              mediaUrl,
            });
            await rememberSentQqMedia({
              cfg: api.config as CoreConfig,
              accountId: target.accountId,
              targetKind: target.targetKind,
              targetId: target.targetId,
              mediaUrl,
              caption: params.caption?.trim() ?? "",
              result,
              agentId: ctx.agentId,
            });
            return json({
              ok: result.status === "ok" || result.retcode === 0,
              source: target.source,
              target_kind: target.targetKind,
              target_id: target.targetId,
              account_id: target.accountId ?? null,
              media_url: mediaUrl,
              caption: params.caption?.trim() ?? "",
              data: result.data ?? null,
            });
          } catch (err) {
            return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
          }
        },
      }) as AnyAgentTool) as never,
    { name: "qq_send_image" },
  );

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_send_voice",
        label: "QQ Send Voice",
        description:
          "Send a spoken QQ reply to the current conversation, or to an explicit QQ target, preferring PTT/voice and falling back to audio-file delivery when needed.",
        parameters: QqSendVoiceSchema,
        async execute(_toolCallId, rawParams) {
          const params = (rawParams ?? {}) as {
            text?: string;
            audio_url?: string;
            audio_path?: string;
            caption?: string;
            target?: string;
            prefer_ptt?: boolean;
            dry_run?: boolean;
          };
          const text = params.text?.trim() ?? "";
          const audioUrl = params.audio_url?.trim();
          const audioPath = params.audio_path?.trim();
          if (!text && !audioUrl && !audioPath) {
            return json({ ok: false, error: "text、audio_url 或 audio_path 至少提供一个" });
          }
          try {
            const cfg = api.config as CoreConfig;
            const target = await resolveQqSendImageTarget({
              api,
              ctx,
              explicitTarget: params.target,
            });
            const resolvedAudio = audioPath
              ? api.resolvePath(audioPath)
              : audioUrl
                ? audioUrl
                : null;
            const preferPtt = params.prefer_ptt !== false;
            if (params.dry_run === true) {
              const voiceSynthesisConfig = resolveLocalQwenCloneTtsConfig(
                (api.pluginConfig as { voiceSynthesis?: unknown } | undefined)?.voiceSynthesis,
              );
              return json({
                ok: true,
                dry_run: true,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                text: text || null,
                audio_url: resolvedAudio,
                caption: params.caption?.trim() ?? "",
                synthesize_on_send: !resolvedAudio && Boolean(text),
                synthesis_provider: resolvedAudio
                  ? "user-supplied-audio"
                  : voiceSynthesisConfig.enabled
                    ? "local-qwen-clone"
                    : "system-say",
                synthesis_voice_name: resolvedAudio
                  ? null
                  : voiceSynthesisConfig.enabled
                    ? voiceSynthesisConfig.voiceName
                    : "Ting-Ting",
                preferred_mode: preferPtt ? "ptt" : "audio",
                fallback_mode: preferPtt ? "audio" : "ptt",
                final_fallback: "text",
                capabilities: ["qq-ptt", "qq-audio-file", "qq-text-only"],
              });
            }
            const mediaUrl =
              resolvedAudio ??
              (await synthesizeQqVoiceFromTextWithConfig(
                text,
                (api.pluginConfig as { voiceSynthesis?: unknown } | undefined)?.voiceSynthesis,
              ));
            const outcome = await sendQqVoice({
              cfg,
              accountId: target.accountId,
              targetKind: target.targetKind,
              targetId: target.targetId,
              audioUrl: mediaUrl,
              caption: params.caption?.trim() ?? "",
              preferPtt,
            });
            return json({
              ok: outcome.ok,
              source: target.source,
              target_kind: target.targetKind,
              target_id: target.targetId,
              account_id: target.accountId ?? null,
              text: text || null,
              audio_url: mediaUrl,
              caption: params.caption?.trim() ?? "",
              mode: outcome.mode,
              capability: outcome.capability,
              attempts: outcome.attempts,
              data: outcome.result.data ?? null,
              message_id: (outcome.result.data as Record<string, unknown> | undefined)?.message_id ?? null,
              error:
                outcome.ok || outcome.mode !== "text"
                  ? null
                  : "QQ PTT and audio-file delivery are unavailable; sent explanatory text fallback instead.",
            });
          } catch (err) {
            return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
          }
        },
      }) as AnyAgentTool) as never,
    { name: "qq_send_voice" },
  );

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_send_file",
        label: "QQ Send File",
        description:
          "Send a file to the current QQ conversation, or to an explicit QQ target, from a local file path. Tries local file:// first, then falls back to proxy URLs.",
        parameters: QqSendFileSchema,
        async execute(_toolCallId, rawParams) {
          const params = (rawParams ?? {}) as {
            file_path?: string;
            name?: string;
            caption?: string;
            target?: string;
            dry_run?: boolean;
          };
          const filePathInput = params.file_path?.trim();
          if (!filePathInput) {
            return json({ ok: false, error: "file_path required" });
          }
          try {
            const cfg = api.config as CoreConfig;
            const target = await resolveQqSendImageTarget({
              api,
              ctx,
              explicitTarget: params.target,
            });
            const resolvedPath = resolveLocalPath(filePathInput, cfg);
            if (!resolvedPath || EXTERNAL_URL_RE.test(resolvedPath)) {
              return json({
                ok: false,
                error: "file_path must be a local file path (not a URL)",
                file_path: filePathInput,
              });
            }
            const stat = await fs.stat(resolvedPath);
            if (!stat.isFile()) {
              return json({ ok: false, error: `not a file: ${resolvedPath}` });
            }
            const fileName = (params.name?.trim() || path.basename(resolvedPath)).trim();
            if (!fileName) {
              return json({ ok: false, error: "name cannot be empty" });
            }
            const caption = params.caption?.trim() ?? "";
            const localFileUrl = pathToFileURL(resolvedPath).toString();
            const proxyUrl = await publishQqMediaProxyUrl({
              cfg,
              sourceFilePath: resolvedPath,
              prefix: "qq-send-file",
            });
            const candidates = [
              { source: "file_url", fileRef: localFileUrl },
              { source: "local_path", fileRef: resolvedPath },
              { source: "proxy_url", fileRef: proxyUrl },
            ] as const;
            if (params.dry_run === true) {
              return json({
                ok: true,
                dry_run: true,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                file_path: resolvedPath,
                file_url: localFileUrl,
                proxy_url: proxyUrl,
                name: fileName,
                caption,
                attempts: candidates,
              });
            }
            const attempts: Array<{
              source: string;
              file_ref: string;
              status: string | null;
              retcode: number | null;
              message: string | null;
              wording: string | null;
              message_id: unknown;
            }> = [];
            for (const candidate of candidates) {
              const result = await sendQqSegments({
                cfg,
                accountId: target.accountId,
                targetKind: target.targetKind,
                targetId: target.targetId,
                message: [
                  ...(caption ? [{ type: "text", data: { text: caption } }] : []),
                  { type: "file", data: { file: candidate.fileRef, name: fileName } },
                ] as never,
              });
              const ok = result.status === "ok" || result.retcode === 0;
              attempts.push({
                source: candidate.source,
                file_ref: candidate.fileRef,
                status: result.status ?? null,
                retcode: result.retcode ?? null,
                message: result.message ?? null,
                wording: result.wording ?? null,
                message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
              });
              if (ok) {
                return json({
                  ok: true,
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                  account_id: target.accountId ?? null,
                  file_path: resolvedPath,
                  file_url: localFileUrl,
                  proxy_url: proxyUrl,
                  file_ref: candidate.fileRef,
                  file_ref_source: candidate.source,
                  name: fileName,
                  caption,
                  attempts,
                  data: result.data ?? null,
                  message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
                });
              }
            }
            const last = attempts[attempts.length - 1] ?? null;
            return json({
              ok: false,
              source: target.source,
              target_kind: target.targetKind,
              target_id: target.targetId,
              account_id: target.accountId ?? null,
              file_path: resolvedPath,
              file_url: localFileUrl,
              proxy_url: proxyUrl,
              name: fileName,
              caption,
              attempts,
              error: last?.message ?? last?.wording ?? "send file failed",
            });
          } catch (err) {
            return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
          }
        },
      }) as AnyAgentTool) as never,
    { name: "qq_send_file" },
  );

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_recall_message",
        label: "QQ Recall Message",
        description:
          "Recall the most recent QQ messages sent by OpenClaw in the current conversation for the current sender.",
        parameters: QqRecallSchema,
        async execute(_toolCallId, rawParams) {
          const params = (rawParams ?? {}) as { count?: number };
          const trackingKey = buildRecallTrackingKey({
            sessionKey: ctx.sessionKey,
            senderId: ctx.requesterSenderId,
          });
          if (!trackingKey) {
            return json({
              ok: false,
              error: "当前上下文缺少会话或发送者信息，无法撤回消息",
            });
          }
          try {
            const result = await recallRecentQqMessages({
              cfg: api.config as CoreConfig,
              trackingKey,
              count: params.count,
            });
            return json(result);
          } catch (err) {
            return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
          }
        },
      }) as AnyAgentTool) as never,
    { name: "qq_recall_message" },
  );

  api.registerTool({
    name: "search_nearby",
    label: "Search Nearby",
    description: "Search nearby places around a location using Amap (Gaode) map data.",
    parameters: SearchNearbySchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        location?: string;
        keyword?: string;
        type?: string;
        city?: string;
      };
      try {
        return json(
          await runSearchNearby({
            location: params.location ?? "",
            keyword: params.keyword,
            type: params.type,
            city: params.city,
          }),
        );
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "send_email",
    label: "Send Email",
    description: "Send email through QQ Mail SMTP with a concrete subject and body.",
    parameters: SendEmailSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        receiver_email?: string;
        subject?: string;
        content?: string;
        content_type?: "plain" | "html";
      };
      try {
        return json(
          await runSendEmail({
            receiver_email: params.receiver_email ?? "",
            subject: params.subject ?? "",
            content: params.content ?? "",
            content_type: params.content_type,
          }),
        );
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_make_meme",
        label: "QQ Make Meme",
        description:
          "Create a meme image with embedded text. If no image_url/image_path is provided, it can reuse the current QQ conversation's recent image.",
        parameters: QqMakeMemeSchema,
        async execute(_toolCallId, rawParams) {
          const params = (rawParams ?? {}) as {
            image_url?: string;
            image_path?: string;
            top_text?: string;
            bottom_text?: string;
            center_text?: string;
            text?: string;
            caption?: string;
            target?: string;
            use_current_image?: boolean;
            preserve_original_size?: boolean;
            max_width?: number;
            max_height?: number;
          };
          try {
            let imageUrl = params.image_url?.trim() || undefined;
            let imagePath = params.image_path?.trim() || undefined;
            let memeSource:
              | {
                  conversation_key: string;
                  source: string;
                  summary: string;
                }
              | undefined;
            if (!imageUrl && !imagePath && params.use_current_image !== false) {
              const target = await resolveQqSendImageTarget({
                api,
                ctx,
                explicitTarget: params.target,
              });
              const conversationKey = buildQqConversationKeyForTarget({
                accountId: target.accountId,
                targetKind: target.targetKind,
                targetId: target.targetId,
              });
              const currentImage = resolveQqConversationMemeBaseImage({
                conversationKey,
                preferInbound: true,
              });
              if (currentImage) {
                imageUrl = currentImage.imageUrl;
                imagePath = currentImage.imagePath;
                memeSource = {
                  conversation_key: conversationKey,
                  source: currentImage.source,
                  summary: currentImage.summary,
                };
              }
            }
            const result = await runQqMakeMeme(
              {
                image_url: imageUrl,
                image_path: imagePath,
                top_text: params.top_text,
                bottom_text: params.bottom_text,
                center_text: params.center_text,
                text: params.text,
                caption: params.caption,
                preserve_original_size: params.preserve_original_size,
                max_width: params.max_width,
                max_height: params.max_height,
              },
              api.config as CoreConfig,
            );
            return json({
              ...result,
              meme_source: memeSource ?? null,
            });
          } catch (err) {
            return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
          }
        },
      }) as AnyAgentTool) as never,
    { name: "qq_make_meme" },
  );

  api.registerTool({
    name: "qq_search_image",
    label: "QQ Search Image",
    description: "Search images online and return send-ready image URLs for QQ replies.",
    parameters: QqSearchImageSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        query?: string;
        count?: number;
      };
      try {
        return json(
          await runQqSearchImage({
            query: params.query ?? "",
            count: params.count,
          }, api.config as CoreConfig),
        );
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_debug_inject_message",
    label: "QQ Debug Inject Message",
    description:
      "Inject a synthetic QQ inbound text/image message into qq-natural for dry-run or live pipeline testing.",
    parameters: QqDebugInjectSchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        account_id?: string;
        chat_type?: "group" | "direct";
        group_id?: string;
        user_id?: string;
        sender_name?: string;
        text?: string;
        mention_self?: boolean;
        reply_to_message_id?: string;
        image_path?: string;
        image_url?: string;
        image_paths?: string[];
        image_urls?: string[];
        message_id?: number;
        dry_run?: boolean;
      };
      try {
        const cfg = api.config as CoreConfig;
        const account = resolveQqAccount({
          cfg,
          accountId: params.account_id,
        });
        const isGroup = params.chat_type === "group";
        const nowSeconds = Math.floor(Date.now() / 1000);
        const built = await buildInjectedQqEvent({
          account,
          chatType: isGroup ? "group" : "direct",
          groupId: params.group_id,
          text: params.text,
          mentionSelf: params.mention_self,
          replyToMessageId: params.reply_to_message_id,
          imagePath: params.image_path,
          imageUrl: params.image_url,
          imagePaths: params.image_paths,
          imageUrls: params.image_urls,
          userId: params.user_id,
          senderName: params.sender_name,
          messageId:
            typeof params.message_id === "number" && Number.isFinite(params.message_id)
              ? Math.floor(params.message_id)
              : nowSeconds,
          timeSeconds: nowSeconds,
        });
        const result = await debugInjectQqInboundMessage({
          api,
          cfg,
          accountId: params.account_id,
          event: built.event,
          dryRun: params.dry_run !== false,
        });
        return json({
          ...result,
          injected_event: {
            message_id: String(built.event.message_id),
            message_type: built.event.message_type,
            group_id: isGroup ? built.groupId : undefined,
            user_id: built.userId,
            image_count: built.imageCount,
          },
        });
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);

  api.registerTool({
    name: "qq_debug_replay",
    label: "QQ Debug Replay",
    description:
      "Replay recent QQ ingress debug events to inspect media binding, reply target resolution, burst compaction, and silence reasons.",
    parameters: QqDebugReplaySchema,
    async execute(_toolCallId, rawParams) {
      const params = (rawParams ?? {}) as {
        conversation_key?: string;
        group_id?: string;
        account_id?: string;
        minutes?: number;
        limit?: number;
        around_message_id?: string;
        keyword?: string;
        kinds?: string[];
        log_path?: string;
      };
      try {
        return json(
          await replayQqIngressDebugLog({
            conversationKey: params.conversation_key,
            groupId: params.group_id,
            accountId: params.account_id,
            minutes: params.minutes,
            limit: params.limit,
            aroundMessageId: params.around_message_id,
            keyword: params.keyword,
            kinds: params.kinds,
            logPath: params.log_path,
          }),
        );
      } catch (err) {
        return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    },
  } as AnyAgentTool);
}
