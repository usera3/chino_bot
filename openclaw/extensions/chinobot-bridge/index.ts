import { Type } from "@sinclair/typebox";
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { promisify } from "node:util";
import type { AnyAgentTool, OpenClawPluginApi } from "../../dist/plugin-sdk/index.js";
import { resolveQqAccount } from "../qq-natural/src/accounts.js";
import {
  buildQqMentionSegments,
  findQqMentionMember,
  normalizeQqMentionLookup,
} from "../qq-natural/src/mention.js";
import { runQqMakeMeme } from "../qq-natural/src/meme.js";
import { resolveQqHttpMediaUrl } from "../shared/onebot-media-file.js";
import {
  DEFAULT_LOCAL_QWEN_CLONE_TTS,
  resolveLocalQwenCloneTtsConfig,
  synthesizeLocalQwenCloneTts,
} from "../shared/local-qwen-clone-tts.js";
import {
  buildRecallTrackingKey,
  describeQqImageWithModel,
  getQqGroupMembers,
  getQqGroupRootFiles,
  getQqGroupFilesByFolder,
  getQqGroupFileUrl,
  getQqFile,
  getQqGroupInfo,
  getQqLoginInfo,
  getQqPacketStatus,
  getQqUserInfo,
  isOneBotActionAccepted,
  recallRecentQqMessages,
  rememberSentQqMedia,
  resolveQqConversationMemeBaseImage,
  sendQqForwardMessages,
  sendQqMedia,
  sendQqPoke,
  sendQqText,
  sendQqSegments,
  sendQqVoice,
  sendQqLike,
  setQqGroupAdmin,
  setQqGroupBan,
  setQqGroupKick,
  setQqGroupSpecialTitle,
  setQqGroupWholeBan,
  uploadQqGroupFile,
} from "../qq-natural/src/service.js";
import { runQqSearchImage } from "../qq-natural/src/tools.js";
import type { CoreConfig } from "../qq-natural/src/types.js";

const execFileAsync = promisify(execFile);

const DEFAULT_PROJECT_ROOT = "..";
const DEFAULT_BRIDGE_SCRIPT = "../bridge/openclaw_tool_bridge.py";
const DEFAULT_PYTHON_PATH = "python3";
const DEFAULT_TIMEOUT_MS = 30_000;
const BRIDGE_MAX_BUFFER = 8 * 1024 * 1024;
const BRIDGE_ERROR_TAIL_CHARS = 1500;
const BRIDGE_RENDER_RETRY_TOOLS = new Set(["render_html", "web_screenshot"]);
const EXTERNAL_URL_RE = /^(?:[a-z][a-z0-9+.-]*:\/\/|data:)/i;
const QQ_AVATAR_OUTPUT_DIR = path.join(os.tmpdir(), "openclaw-qq-avatars");

const pluginConfigSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    projectRoot: { type: "string", default: DEFAULT_PROJECT_ROOT },
    bridgeScript: { type: "string", default: DEFAULT_BRIDGE_SCRIPT },
    pythonPath: { type: "string", default: DEFAULT_PYTHON_PATH },
    timeoutMs: { type: "number", default: DEFAULT_TIMEOUT_MS, minimum: 1_000, maximum: 120_000 },
    voiceSynthesis: {
      type: "object",
      additionalProperties: false,
      properties: {
        enabled: { type: "boolean", default: false },
        projectRoot: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.projectRoot,
        },
        pythonPath: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.pythonPath,
        },
        scriptPath: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.scriptPath,
        },
        modelPath: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.modelPath,
        },
        voiceName: { type: "string", default: DEFAULT_LOCAL_QWEN_CLONE_TTS.voiceName },
        timeoutMs: { type: "number", default: 120000, minimum: 1000, maximum: 300000 },
        fallbackToSystemSay: {
          type: "boolean",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.fallbackToSystemSay,
        },
      },
    },
  },
} as const;

function textResult(text: string, details?: unknown) {
  return {
    content: [{ type: "text" as const, text }],
    details,
  };
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function tailSnippet(value: unknown, limit = BRIDGE_ERROR_TAIL_CHARS) {
  const text = String(value ?? "").trim();
  if (!text) {
    return "";
  }
  return text.length > limit ? text.slice(-limit) : text;
}

function formatBridgeExecError(error: unknown) {
  const err = error as { message?: unknown; stderr?: unknown; stdout?: unknown } | null;
  const parts = [String(err?.message ?? error)];
  const stderr = tailSnippet(err?.stderr);
  const stdout = tailSnippet(err?.stdout);
  if (stderr) {
    parts.push(`stderr:\n${stderr}`);
  }
  if (stdout) {
    parts.push(`stdout:\n${stdout}`);
  }
  return parts.join("\n\n");
}

type BridgeInvokePayload = {
  ok?: boolean;
  result?: unknown;
  error?: string;
  details?: unknown;
};

function resolveBridgeConfig(api: OpenClawPluginApi) {
  const config = (api.pluginConfig ?? {}) as {
    projectRoot?: string;
    bridgeScript?: string;
    pythonPath?: string;
    timeoutMs?: number;
    voiceSynthesis?: unknown;
  };
  return {
    projectRoot: config.projectRoot || DEFAULT_PROJECT_ROOT,
    bridgeScript: config.bridgeScript || DEFAULT_BRIDGE_SCRIPT,
    pythonPath: config.pythonPath || DEFAULT_PYTHON_PATH,
    timeoutMs:
      typeof config.timeoutMs === "number" && Number.isFinite(config.timeoutMs)
        ? config.timeoutMs
        : DEFAULT_TIMEOUT_MS,
    voiceSynthesis: resolveLocalQwenCloneTtsConfig(config.voiceSynthesis),
  };
}

function bridgeSuccessResult(payload: BridgeInvokePayload) {
  if (typeof payload.result === "string") {
    return textResult(payload.result, payload.details);
  }
  if (payload.result && typeof payload.result === "object") {
    return textResult(JSON.stringify(payload.result, null, 2), payload.result);
  }
  if (payload.result === undefined || payload.result === null) {
    return textResult("", payload.details);
  }
  return textResult(String(payload.result), payload.details ?? payload.result);
}

async function invokeBridgeTool(
  api: OpenClawPluginApi,
  toolName: string,
  params: Record<string, unknown>,
): Promise<BridgeInvokePayload | ReturnType<typeof textResult>> {
  const bridge = resolveBridgeConfig(api);
  const attempts = BRIDGE_RENDER_RETRY_TOOLS.has(toolName) ? 2 : 1;
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const { stdout, stderr } = await execFileAsync(
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
          maxBuffer: BRIDGE_MAX_BUFFER,
        },
      );
      const raw = stdout.trim();
      if (!raw) {
        return textResult("❌ chino_bot bridge 没有返回内容", { stderr });
      }
      return JSON.parse(raw) as BridgeInvokePayload;
    } catch (error) {
      lastError = error;
      if (attempt < attempts) {
        api.logger?.warn?.(
          `[chinobot-bridge] ${toolName} attempt ${attempt} failed; retrying: ${formatBridgeExecError(error)}`,
        );
        await sleep(600 * attempt);
        continue;
      }
    }
  }
  return textResult(`❌ 调用 chino_bot bridge 失败：${formatBridgeExecError(lastError)}`);
}

async function runBridgeTool(
  api: OpenClawPluginApi,
  toolName: string,
  params: Record<string, unknown>,
) {
  const payload = await invokeBridgeTool(api, toolName, params);
  if ("content" in payload) {
    return payload;
  }
  if (payload.ok) {
    return bridgeSuccessResult(payload);
  }
  return textResult(`❌ chino_bot bridge 调用失败：${payload.error ?? "unknown error"}`, payload.details ?? payload);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function readFirstString(
  record: Record<string, unknown> | null,
  keys: string[],
): string | undefined {
  if (!record) {
    return undefined;
  }
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
}

function stripVisualTransportFields(record: Record<string, unknown>) {
  const clone = { ...record };
  delete clone.media;
  delete clone.mediaUrl;
  delete clone.media_url;
  delete clone.primaryMediaUrl;
  delete clone.primary_media_url;
  delete clone.mediaUrls;
  delete clone.media_urls;
  delete clone.path;
  delete clone.filePath;
  delete clone.file_path;
  return clone;
}

function resolveVisualTransport(record: Record<string, unknown> | null) {
  if (!record) {
    return null;
  }
  const localPath = readFirstString(record, ["file_path", "path", "filePath"]);
  const mediaUrl = readFirstString(record, [
    "media_url",
    "mediaUrl",
    "primary_media_url",
    "primaryMediaUrl",
  ]);
  const caption = readFirstString(record, ["caption"]);
  if (!localPath && !mediaUrl) {
    return null;
  }
  return {
    localPath,
    mediaUrl,
    caption,
  };
}

async function tryExplicitQqVisualDelivery(params: {
  api: OpenClawPluginApi;
  ctx: {
    agentId?: string;
    sessionKey?: string;
    messageChannel?: string;
    agentAccountId?: string;
  };
  resultRecord: Record<string, unknown> | null;
  explicitTarget?: string;
}) {
  if (params.ctx.messageChannel !== "qq") {
    return null;
  }
  const transport = resolveVisualTransport(params.resultRecord);
  if (!transport) {
    return null;
  }
  const target = await resolveQqMessageTarget({
    api: params.api,
    ctx: params.ctx,
    explicitTarget: params.explicitTarget,
  }).catch(() => null);
  if (!target) {
    return null;
  }
  const mediaRef = transport.localPath
    ? params.api.resolvePath(transport.localPath)
    : (transport.mediaUrl ?? "");
  if (!mediaRef.trim()) {
    return null;
  }
  try {
    const result = await sendQqMedia({
      cfg: params.api.config as CoreConfig,
      accountId: target.accountId,
      targetKind: target.targetKind,
      targetId: target.targetId,
      text: transport.caption ?? "",
      mediaUrl: mediaRef,
    });
    await rememberSentQqMedia({
      cfg: params.api.config as CoreConfig,
      accountId: target.accountId,
      targetKind: target.targetKind,
      targetId: target.targetId,
      mediaUrl: mediaRef,
      caption: transport.caption ?? "",
      result,
      agentId: params.ctx.agentId,
    });
    return jsonText({
      ...stripVisualTransportFields(params.resultRecord ?? {}),
      ok: isOneBotSuccess(result),
      delivery_mode: "explicit_qq_media_send",
      source: target.source,
      target_kind: target.targetKind,
      target_id: target.targetId,
      account_id: target.accountId ?? null,
      generated_local_path: transport.localPath ?? null,
      generated_media_proxy_url: transport.mediaUrl ?? null,
      sent_media_ref: mediaRef,
      caption: transport.caption ?? null,
      data: result.data ?? null,
      message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    params.api.logger.warn?.(
      `[chinobot-bridge] explicit QQ visual delivery failed, falling back to normal result: ${message}`,
    );
    return null;
  }
}

async function runBridgeVisualTool(
  api: OpenClawPluginApi,
  ctx: {
    agentId?: string;
    sessionKey?: string;
    messageChannel?: string;
    agentAccountId?: string;
  },
  toolName: string,
  params: Record<string, unknown>,
) {
  const payload = await invokeBridgeTool(api, toolName, params);
  if ("content" in payload) {
    return payload;
  }
  if (!payload.ok) {
    return textResult(
      `❌ chino_bot bridge 调用失败：${payload.error ?? "unknown error"}`,
      payload.details ?? payload,
    );
  }
  const explicitDelivered = await tryExplicitQqVisualDelivery({
    api,
    ctx,
    resultRecord: asRecord(payload.result),
    explicitTarget: typeof params.target === "string" ? params.target : undefined,
  });
  if (explicitDelivered) {
    return explicitDelivered;
  }
  return bridgeSuccessResult(payload);
}

const ReceiveEmailSchema = Type.Object({
  max_count: Type.Optional(Type.Number({ minimum: 1, maximum: 20, default: 5 })),
  unread_only: Type.Optional(Type.Boolean({ default: true })),
});

const SendEmailSchema = Type.Object({
  receiver_email: Type.String({ minLength: 3 }),
  subject: Type.String({ minLength: 1 }),
  content: Type.String({ minLength: 1 }),
  attachment_path: Type.Optional(Type.String()),
});

const ReadPdfSchema = Type.Object({
  file_path: Type.String({ minLength: 1 }),
  max_pages: Type.Optional(Type.Number({ minimum: 1 })),
});

const ReadWordSchema = Type.Object({
  file_path: Type.String({ minLength: 1 }),
});

const CreateWordSchema = Type.Object({
  file_path: Type.String({ minLength: 1 }),
  title: Type.String({ minLength: 1 }),
  content: Type.String({ minLength: 1 }),
});

const ReadExcelSchema = Type.Object({
  file_path: Type.String({ minLength: 1 }),
  sheet_name: Type.Optional(Type.String()),
  max_rows: Type.Optional(Type.Number({ minimum: 1, default: 100 })),
});

const CreateExcelSchema = Type.Object({
  file_path: Type.String({ minLength: 1 }),
  data: Type.String({ minLength: 2 }),
  sheet_name: Type.Optional(Type.String({ minLength: 1, default: "Sheet1" })),
});

const ConvertWordToPdfSchema = Type.Object({
  word_path: Type.String({ minLength: 1 }),
  pdf_path: Type.Optional(Type.String()),
});

const ConvertPdfToWordSchema = Type.Object({
  pdf_path: Type.String({ minLength: 1 }),
  word_path: Type.Optional(Type.String()),
});

const ParseLinkSchema = Type.Object({
  url: Type.String({ minLength: 1 }),
});

const TavilySearchSchema = Type.Object({
  query: Type.String({ minLength: 1 }),
  count: Type.Optional(Type.Number({ minimum: 1, maximum: 10, default: 5 })),
  max_results: Type.Optional(Type.Number({ minimum: 1, maximum: 10, default: 5 })),
  search_depth: Type.Optional(Type.String({ minLength: 1, default: "basic" })),
  topic: Type.Optional(Type.String({ minLength: 1, default: "general" })),
  days: Type.Optional(Type.Number({ minimum: 1, maximum: 365 })),
  include_answer: Type.Optional(Type.Boolean({ default: true })),
  include_images: Type.Optional(Type.Boolean({ default: false })),
  include_raw_content: Type.Optional(Type.Boolean({ default: false })),
  include_domains: Type.Optional(Type.Array(Type.String({ minLength: 1 }), { maxItems: 10 })),
  exclude_domains: Type.Optional(Type.Array(Type.String({ minLength: 1 }), { maxItems: 10 })),
  proxy_mode: Type.Optional(Type.String({ minLength: 1, default: "auto" })),
  timeout_seconds: Type.Optional(Type.Number({ minimum: 5, maximum: 60, default: 20 })),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const RenderHtmlSchema = Type.Object({
  html_code: Type.String({ minLength: 1 }),
  width: Type.Optional(Type.Number({ minimum: 64, maximum: 4096, default: 800 })),
  height: Type.Optional(Type.Number({ minimum: 64, maximum: 4096, default: 600 })),
  wait_ms: Type.Optional(Type.Number({ minimum: 0, maximum: 10_000, default: 500 })),
  device_scale_factor: Type.Optional(Type.Number({ minimum: 1, maximum: 4, default: 2 })),
  full_page: Type.Optional(Type.Boolean({ default: true })),
});

const WebScreenshotSchema = Type.Object({
  url: Type.String({ minLength: 8 }),
  full_page: Type.Optional(Type.Boolean({ default: true })),
  width: Type.Optional(Type.Number({ minimum: 320, maximum: 4096, default: 1920 })),
  height: Type.Optional(Type.Number({ minimum: 240, maximum: 4096, default: 1080 })),
  wait_ms: Type.Optional(Type.Number({ minimum: 0, maximum: 10_000, default: 2000 })),
});

const ListBridgeToolsSchema = Type.Object({});

const ChinoBotQqUserInfoSchema = Type.Object({
  user_id: Type.Optional(Type.String()),
});

const ChinoBotQqSelfInfoSchema = Type.Object({});

const ChinoBotQqGroupInfoSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
});

const ChinoBotQqSendLikeSchema = Type.Object({
  user_id: Type.Optional(Type.String()),
  times: Type.Optional(Type.Number({ minimum: 1, maximum: 10, default: 10 })),
});

const ChinoBotQqGroupBanSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
  duration_seconds: Type.Optional(Type.Number({ minimum: 0, maximum: 2592000, default: 60 })),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqGroupWholeBanSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  enable: Type.Optional(Type.Boolean({ default: true })),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqGroupKickSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
  reject_add_request: Type.Optional(Type.Boolean({ default: false })),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqGroupAdminSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
  enable: Type.Optional(Type.Boolean({ default: true })),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqGroupSpecialTitleSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
  special_title: Type.String(),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqSendPokeSchema = Type.Object({
  user_id: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotAnalyzeAvatarSchema = Type.Object({
  user_id: Type.Optional(Type.String()),
  self: Type.Optional(Type.Boolean({ default: false })),
  avatar_size: Type.Optional(Type.Number({ minimum: 40, maximum: 640, default: 640 })),
});

const ChinoBotQqGroupMemberInfoSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  user_id: Type.Optional(Type.String()),
});

const ChinoBotQqGroupMembersSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
});

const ChinoBotQqGroupFilesSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  folder_id: Type.Optional(Type.String()),
});

const ChinoBotQqUploadGroupFileSchema = Type.Object({
  file_path: Type.String({ minLength: 1 }),
  name: Type.Optional(Type.String()),
  group_id: Type.Optional(Type.String()),
  folder: Type.Optional(Type.String()),
  upload_file: Type.Optional(Type.Boolean()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqSendFileSchema = Type.Object({
  file_path: Type.String({ minLength: 1 }),
  name: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqFakeMessageSchema = Type.Object({
  messages: Type.String({ minLength: 1 }),
  user_qq: Type.Optional(Type.String()),
  bot_qq: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqFakeDialogueSchema = Type.Object({
  messages: Type.String({ minLength: 1 }),
  target: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqSendImageSchema = Type.Object({
  image_url: Type.Optional(Type.String()),
  image_path: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqSendVoiceSchema = Type.Object({
  text: Type.Optional(Type.String()),
  audio_url: Type.Optional(Type.String()),
  audio_path: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  prefer_ptt: Type.Optional(Type.Boolean({ default: true })),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqRecallSchema = Type.Object({
  count: Type.Optional(Type.Number({ minimum: 1, maximum: 5, default: 1 })),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqSendMentionSchema = Type.Object({
  text: Type.String({ minLength: 1 }),
  mention_user_id: Type.Optional(Type.String()),
  mention_name: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  reply_to_message_id: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqPacketStatusSchema = Type.Object({});

const ChinoBotQqGroupFileInfoSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  file_id: Type.String({ minLength: 1 }),
  folder_id: Type.Optional(Type.String()),
});

const ChinoBotQqGroupFileUrlSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  file_id: Type.String({ minLength: 1 }),
  busid: Type.Optional(Type.Union([Type.String(), Type.Number()])),
  folder_id: Type.Optional(Type.String()),
});

const ChinoBotQqGroupFileDownloadSchema = Type.Object({
  group_id: Type.Optional(Type.String()),
  file_id: Type.String({ minLength: 1 }),
  busid: Type.Optional(Type.Union([Type.String(), Type.Number()])),
  folder_id: Type.Optional(Type.String()),
  output_path: Type.Optional(Type.String()),
  dry_run: Type.Optional(Type.Boolean({ default: false })),
});

const ChinoBotQqSearchImageSchema = Type.Object({
  query: Type.String({ minLength: 1 }),
  count: Type.Optional(Type.Number({ minimum: 1, maximum: 8, default: 4 })),
});

const ChinoBotQqMakeMemeSchema = Type.Object({
  image_url: Type.Optional(Type.String()),
  image_path: Type.Optional(Type.String()),
  top_text: Type.Optional(Type.String()),
  bottom_text: Type.Optional(Type.String()),
  center_text: Type.Optional(Type.String()),
  text: Type.Optional(Type.String()),
  caption: Type.Optional(Type.String()),
  target: Type.Optional(Type.String()),
  use_current_image: Type.Optional(Type.Boolean({ default: true })),
  preserve_original_size: Type.Optional(Type.Boolean()),
  max_width: Type.Optional(Type.Number()),
  max_height: Type.Optional(Type.Number()),
});

function jsonText(data: unknown) {
  return textResult(JSON.stringify(data, null, 2), data);
}

function isOneBotSuccess(result: { status?: string | null; retcode?: number | null } | null | undefined) {
  return result?.status === "ok" || result?.retcode === 0;
}

function summarizeOneBotFailure(result: {
  message?: string | null;
  wording?: string | null;
} | null | undefined) {
  return result?.message ?? result?.wording ?? "unknown error";
}

type QqGroupFileUploadAttempt = {
  source: "local_path" | "proxy_url";
  upload_file: boolean | null;
  status: string | null;
  retcode: number | null;
  message: string | null;
  wording: string | null;
};

async function attemptQqGroupFileUploadWithFallback(params: {
  cfg: CoreConfig;
  accountId?: string;
  groupId: string;
  resolvedPath: string;
  name: string;
  folderId?: string;
  requestedUploadFile?: boolean;
}) {
  const attempts: QqGroupFileUploadAttempt[] = [];
  let lastResult: Awaited<ReturnType<typeof uploadQqGroupFile>> | null = null;
  const proxyUrl = await resolveQqHttpMediaUrl({
    mediaUrl: params.resolvedPath,
    gatewayPort: params.cfg.gateway?.port,
  });
  const normalizedProxyUrl =
    proxyUrl && proxyUrl !== params.resolvedPath ? proxyUrl : null;

  const attemptUpload = async (attempt: {
    file: string;
    source: "local_path" | "proxy_url";
    uploadFile?: boolean;
  }) => {
    const result = await uploadQqGroupFile({
      cfg: params.cfg,
      accountId: params.accountId,
      groupId: params.groupId,
      file: attempt.file,
      name: params.name,
      folderId: params.folderId,
      uploadFile: attempt.uploadFile,
    });
    lastResult = result;
    attempts.push({
      source: attempt.source,
      upload_file: typeof attempt.uploadFile === "boolean" ? attempt.uploadFile : null,
      status: result.status ?? null,
      retcode: result.retcode ?? null,
      message: result.message ?? null,
      wording: result.wording ?? null,
    });
    return {
      ok: isOneBotSuccess(result),
      result,
      source: attempt.source,
      upload_file: typeof attempt.uploadFile === "boolean" ? attempt.uploadFile : null,
    };
  };

  const trySequence = async (source: "local_path" | "proxy_url", file: string) => {
    const primary = await attemptUpload({
      file,
      source,
      uploadFile: params.requestedUploadFile,
    });
    if (primary.ok) {
      return primary;
    }
    if (params.requestedUploadFile === undefined) {
      const relaxed = await attemptUpload({
        file,
        source,
        uploadFile: false,
      });
      if (relaxed.ok) {
        return relaxed;
      }
    }
    return null;
  };

  const localSuccess = await trySequence("local_path", params.resolvedPath);
  if (localSuccess) {
    return {
      ok: true,
      attempts,
      proxy_url: normalizedProxyUrl,
      upload_source: localSuccess.source,
      upload_file: localSuccess.upload_file,
      result: localSuccess.result,
    };
  }

  if (normalizedProxyUrl) {
    const proxySuccess = await trySequence("proxy_url", normalizedProxyUrl);
    if (proxySuccess) {
      return {
        ok: true,
        attempts,
        proxy_url: normalizedProxyUrl,
        upload_source: proxySuccess.source,
        upload_file: proxySuccess.upload_file,
        result: proxySuccess.result,
      };
    }
  }

  return {
    ok: false,
    attempts,
    proxy_url: normalizedProxyUrl,
    upload_source: (attempts[attempts.length - 1]?.source ?? "local_path") as "local_path" | "proxy_url",
    upload_file:
      (attempts[attempts.length - 1]?.upload_file ??
        (typeof params.requestedUploadFile === "boolean" ? params.requestedUploadFile : null)) as boolean | null,
    result: lastResult,
  };
}

function containsCjk(text: string) {
  return /[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/u.test(text);
}

async function synthesizeBridgeQqVoiceFromTextWithConfig(
  text: string,
  rawVoiceSynthesisConfig: unknown,
): Promise<string> {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("text 不能为空");
  }
  const voiceSynthesisConfig = resolveLocalQwenCloneTtsConfig(rawVoiceSynthesisConfig);
  const outputDir = path.join("/tmp", "openclaw-bridge-qq-voice");
  await fs.mkdir(outputDir, { recursive: true });
  if (voiceSynthesisConfig.enabled) {
    const clonedOutputPath = path.join(outputDir, `qq-voice-${Date.now()}.wav`);
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
  const outputPath = path.join(outputDir, `qq-voice-${Date.now()}.aiff`);
  const args = containsCjk(trimmed)
    ? ["-v", "Ting-Ting", trimmed, "-o", outputPath]
    : [trimmed, "-o", outputPath];
  await execFileAsync("/usr/bin/say", args);
  return outputPath;
}

function maybePacketBackendHint(message: unknown, wording: unknown): string | null {
  const combined = `${typeof message === "string" ? message : String(message ?? "")} ${typeof wording === "string" ? wording : String(wording ?? "")}`.toLowerCase();
  if (
    !combined.includes("packetbackend") &&
    !combined.includes("packet backend") &&
    !combined.includes("nativepacketclient")
  ) {
    return null;
  }
  return [
    "NapCat packetBackend is unavailable.",
    "Use chinobot_packet_status for details.",
  ].join(" ");
}

function guessFilenameFromUrl(rawUrl: string): string | null {
  try {
    const parsed = new URL(rawUrl);
    const name = path.basename(parsed.pathname).trim();
    return name || null;
  } catch {
    return null;
  }
}

async function ensureUniqueFilePath(filePath: string): Promise<string> {
  try {
    const stat = await fs.stat(filePath);
    if (stat.isDirectory()) {
      throw new Error(`output_path is a directory: ${filePath}`);
    }
  } catch (error) {
    if ((error as { code?: string } | null)?.code === "ENOENT") {
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
  return `${base}-${Date.now()}${ext}`;
}

async function downloadToFile(params: { url: string; outputPath: string }) {
  const response = await fetch(params.url);
  if (!response.ok) {
    throw new Error(`download failed: HTTP ${response.status}`);
  }
  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.mkdir(path.dirname(params.outputPath), { recursive: true });
  await fs.writeFile(params.outputPath, buffer);
  return { bytes: buffer.length };
}

function parseQqTarget(target: string): { targetKind: "user" | "group"; targetId: string } | null {
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

async function resolveQqSessionTarget(params: {
  api: OpenClawPluginApi;
  ctx: {
    agentId?: string;
    sessionKey?: string;
    messageChannel?: string;
    agentAccountId?: string;
  };
}) {
  const sessionKey = params.ctx.sessionKey?.trim();
  if (!sessionKey) {
    throw new Error("当前上下文没有 sessionKey，无法推断 QQ 会话目标");
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
    throw new Error("当前会话不是 QQ 会话");
  }
  const toValue =
    (typeof deliveryContext.to === "string" ? deliveryContext.to : undefined) ??
    (typeof entry.lastTo === "string" ? entry.lastTo : undefined) ??
    "";
  const parsed = parseQqTarget(toValue);
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
  };
}

function resolveRequesterUserId(ctx: { requesterSenderId?: string }) {
  return ctx.requesterSenderId?.trim() || undefined;
}

function buildFakeSpeakerAliasSet(values: string[]) {
  return new Set(values.map((value) => normalizeQqMentionLookup(value)));
}

const REQUESTER_FAKE_SPEAKER_ALIASES = buildFakeSpeakerAliasSet([
  "我",
  "我自己",
  "触发者",
  "命令触发者",
  "当前触发者",
  "当前发言人",
  "当前用户",
  "请求者",
  "提问的人",
  "sender",
  "requester",
  "user",
]);

const BOT_FAKE_SPEAKER_ALIASES = buildFakeSpeakerAliasSet([
  "你",
  "你自己",
  "机器人",
  "当前机器人",
  "当前bot",
  "bot",
  "assistant",
  "miko",
  "智乃",
]);

function isFakeSpeakerUserId(value: string) {
  return /^\d{6,10}$/u.test(value.trim());
}

async function resolveRequesterUserIdFromContext(params: {
  api: OpenClawPluginApi;
  ctx: {
    agentId?: string;
    sessionKey?: string;
    requesterSenderId?: string;
  };
}) {
  const direct = resolveRequesterUserId(params.ctx);
  if (direct) {
    return direct;
  }
  const sessionKey = params.ctx.sessionKey?.trim();
  if (!sessionKey) {
    return undefined;
  }
  try {
    const agentId = params.ctx.agentId?.trim() || "main";
    const storePath = params.api.runtime.channel.session.resolveStorePath(
      (params.api.config as { session?: { store?: string } }).session?.store,
      { agentId },
    );
    const raw = await fs.readFile(storePath, "utf8");
    const store = JSON.parse(raw) as Record<string, Record<string, unknown>>;
    const entry = store[sessionKey] ?? {};
    const deliveryContext = (entry.deliveryContext ?? {}) as Record<string, unknown>;
    const explicitSender =
      (typeof entry.requesterSenderId === "string" ? entry.requesterSenderId : undefined) ??
      (typeof entry.lastSenderId === "string" ? entry.lastSenderId : undefined) ??
      (typeof deliveryContext.senderId === "string" ? deliveryContext.senderId : undefined);
    const sender = explicitSender?.trim();
    if (sender) {
      return sender;
    }
    const compositeGroupId = typeof entry.groupId === "string" ? entry.groupId : "";
    const match = /:user:(\d+)$/u.exec(compositeGroupId);
    return match?.[1];
  } catch {
    return undefined;
  }
}

async function resolveQqMessageTarget(params: {
  api: OpenClawPluginApi;
  ctx: {
    agentId?: string;
    sessionKey?: string;
    messageChannel?: string;
    agentAccountId?: string;
  };
  explicitTarget?: string;
}) {
  const explicitTarget = params.explicitTarget?.trim();
  if (explicitTarget) {
    const parsed = parseQqTarget(explicitTarget);
    if (!parsed) {
      throw new Error(`无法解析 QQ target: ${explicitTarget}`);
    }
    let accountId = params.ctx.agentAccountId?.trim() || undefined;
    try {
      const inferred = await resolveQqSessionTarget({ api: params.api, ctx: params.ctx });
      accountId = inferred.accountId ?? accountId;
    } catch {
      // Explicit targets can still work outside an existing QQ session.
    }
    return {
      ...parsed,
      accountId,
      source: "explicit" as const,
    };
  }
  const inferred = await resolveQqSessionTarget({ api: params.api, ctx: params.ctx });
  return {
    ...inferred,
    source: "session" as const,
  };
}

async function resolveCurrentBotQq(params: {
  api: OpenClawPluginApi;
  accountId?: string;
}) {
  const configured = resolveQqAccount({
    cfg: params.api.config as CoreConfig,
    accountId: params.accountId,
  }).selfId?.trim();
  if (configured) {
    return configured;
  }
  try {
    const result = await getQqLoginInfo({
      cfg: params.api.config as CoreConfig,
      accountId: params.accountId,
    });
    const data = (result.data ?? {}) as Record<string, unknown>;
    const userId = String(data.user_id ?? "").trim();
    return userId || undefined;
  } catch {
    return undefined;
  }
}

async function resolveCurrentBotProfile(params: {
  api: OpenClawPluginApi;
  accountId?: string;
}) {
  const configuredUserId = resolveQqAccount({
    cfg: params.api.config as CoreConfig,
    accountId: params.accountId,
  }).selfId?.trim();
  let nickname: string | undefined;
  let userId = configuredUserId || "";
  try {
    const result = await getQqLoginInfo({
      cfg: params.api.config as CoreConfig,
      accountId: params.accountId,
    });
    const data = (result.data ?? {}) as Record<string, unknown>;
    const loginUserId = String(data.user_id ?? "").trim();
    const loginNickname = String(data.nickname ?? "").trim();
    if (loginUserId) {
      userId = loginUserId;
    }
    if (loginNickname) {
      nickname = loginNickname;
    }
  } catch {
    // ignore login-info failures and fall back to configured account id.
  }
  return {
    userId: userId || undefined,
    displayName: nickname || (userId ? `机器人${userId}` : undefined),
  };
}

function normalizeQqAvatarSize(size: number | undefined) {
  if (!Number.isFinite(size ?? Number.NaN)) {
    return 640;
  }
  if ((size ?? 0) >= 640) {
    return 640;
  }
  if ((size ?? 0) >= 140) {
    return 140;
  }
  if ((size ?? 0) >= 100) {
    return 100;
  }
  return 40;
}

function buildQqUserAvatarUrl(userId: string, size: number | undefined) {
  const spec = normalizeQqAvatarSize(size);
  return `https://q.qlogo.cn/headimg_dl?dst_uin=${encodeURIComponent(userId)}&spec=${spec}&img_type=jpg`;
}

function guessAvatarExtension(contentType?: string | null) {
  const normalized = String(contentType ?? "").toLowerCase();
  if (normalized.includes("png")) {
    return ".png";
  }
  if (normalized.includes("webp")) {
    return ".webp";
  }
  if (normalized.includes("gif")) {
    return ".gif";
  }
  return ".jpg";
}

async function downloadQqAvatarImage(params: {
  avatarUrl: string;
  userId: string;
}) {
  const response = await fetch(params.avatarUrl);
  if (!response.ok) {
    throw new Error(`头像下载失败: HTTP ${response.status}`);
  }
  const contentType = response.headers.get("content-type");
  if (contentType && !contentType.toLowerCase().startsWith("image/")) {
    throw new Error(`头像下载失败: 返回的不是图片 (${contentType})`);
  }
  await fs.mkdir(QQ_AVATAR_OUTPUT_DIR, { recursive: true });
  const ext = guessAvatarExtension(contentType);
  const filePath = path.join(
    QQ_AVATAR_OUTPUT_DIR,
    `avatar-${params.userId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`,
  );
  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.writeFile(filePath, buffer);
  return {
    filePath,
    contentType: contentType ?? undefined,
  };
}

async function resolveQqDisplayName(params: {
  api: OpenClawPluginApi;
  accountId?: string;
  userId: string;
}) {
  try {
    const result = await getQqUserInfo({
      cfg: params.api.config as CoreConfig,
      accountId: params.accountId,
      userId: params.userId,
    });
    const data = (result.data ?? {}) as Record<string, unknown>;
    const nickname = String(data.nickname ?? "").trim();
    const card = String(data.card ?? data.remark ?? "").trim();
    return nickname || card || `用户${params.userId}`;
  } catch {
    return `用户${params.userId}`;
  }
}

async function createFakeSpeakerResolver(params: {
  api: OpenClawPluginApi;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  requesterQq?: string | null;
  botQq?: string | null;
}) {
  type FakeSpeaker = { userId: string; displayName: string };

  const speakerCache = new Map<string, FakeSpeaker>();
  let groupMembersPromise: Promise<Record<string, unknown>[]> | null = null;

  const loadGroupMembers = async () => {
    if (params.targetKind !== "group") {
      return [] as Record<string, unknown>[];
    }
    if (!groupMembersPromise) {
      groupMembersPromise = getQqGroupMembers({
        cfg: params.api.config as CoreConfig,
        accountId: params.accountId,
        groupId: params.targetId,
      })
        .then((result) => (Array.isArray(result.data) ? (result.data as Record<string, unknown>[]) : []))
        .catch(() => []);
    }
    return await groupMembersPromise;
  };

  const resolveByUserId = async (userId: string): Promise<FakeSpeaker> => {
    const cacheKey = `id:${userId}`;
    const cached = speakerCache.get(cacheKey);
    if (cached) {
      return cached;
    }
    const members = await loadGroupMembers();
    if (members.length > 0) {
      try {
        const member = findQqMentionMember({
          members,
          mentionUserId: userId,
        });
        const resolved = {
          userId: member.userId,
          displayName: member.displayName,
        };
        speakerCache.set(cacheKey, resolved);
        return resolved;
      } catch {
        // Fall through to generic user lookup.
      }
    }
    const resolved = {
      userId,
      displayName: await resolveQqDisplayName({
        api: params.api,
        accountId: params.accountId,
        userId,
      }),
    };
    speakerCache.set(cacheKey, resolved);
    return resolved;
  };

  return async (speakerToken: string): Promise<FakeSpeaker> => {
    const raw = speakerToken.trim();
    if (!raw) {
      throw new Error("消息格式错误：说话人不能为空");
    }

    if (isFakeSpeakerUserId(raw)) {
      return await resolveByUserId(raw);
    }

    const normalized = normalizeQqMentionLookup(raw);
    if (params.requesterQq?.trim() && REQUESTER_FAKE_SPEAKER_ALIASES.has(normalized)) {
      return await resolveByUserId(params.requesterQq.trim());
    }
    if (params.botQq?.trim() && BOT_FAKE_SPEAKER_ALIASES.has(normalized)) {
      return await resolveByUserId(params.botQq.trim());
    }

    if (params.requesterQq?.trim()) {
      const requester = await resolveByUserId(params.requesterQq.trim());
      if (normalizeQqMentionLookup(requester.displayName) === normalized) {
        return requester;
      }
    }
    if (params.botQq?.trim()) {
      const bot = await resolveByUserId(params.botQq.trim());
      if (normalizeQqMentionLookup(bot.displayName) === normalized) {
        return bot;
      }
    }

    const members = await loadGroupMembers();
    if (members.length > 0) {
      const member = findQqMentionMember({
        members,
        mentionName: raw,
      });
      return {
        userId: member.userId,
        displayName: member.displayName,
      };
    }

    throw new Error(
      `说话人无法解析: ${raw}（请用 QQ 号、触发者、机器人，或在群聊里使用群成员昵称/群名片）`,
    );
  };
}

async function buildFakeDialogueLines(params: {
  api: OpenClawPluginApi;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  messages: string;
  userQq?: string | null;
  botQq?: string | null;
}) {
  let resolved = params.messages;
  const requesterQq = params.userQq?.trim() || "";
  const botQq =
    params.botQq?.trim() ||
    (await resolveCurrentBotQq({
      api: params.api,
      accountId: params.accountId,
    })) ||
    "";
  if (requesterQq) {
    resolved = resolved.replaceAll("{{USER_QQ}}", requesterQq);
  }
  if (botQq) {
    resolved = resolved.replaceAll("{{BOT_QQ}}", botQq);
  }
  if (resolved.includes("{{USER_QQ}}")) {
    throw new Error("messages 中包含 {{USER_QQ}}，但当前上下文没有可用的用户 QQ");
  }
  if (resolved.includes("{{BOT_QQ}}")) {
    throw new Error("messages 中包含 {{BOT_QQ}}，但当前配置里没有可用的机器人 QQ");
  }

  const resolveSpeaker = await createFakeSpeakerResolver({
    api: params.api,
    accountId: params.accountId,
    targetKind: params.targetKind,
    targetId: params.targetId,
    requesterQq: requesterQq || null,
    botQq: botQq || null,
  });

  const lines: string[] = [];
  for (const rawChunk of resolved.split("|")) {
    const chunk = rawChunk.trim();
    if (!chunk) {
      continue;
    }
    const splitAt = chunk.indexOf("说");
    if (splitAt <= 0) {
      throw new Error(`消息格式错误: ${chunk}（应为：昵称说内容）`);
    }
    const speaker = chunk.slice(0, splitAt).trim();
    const content = chunk.slice(splitAt + 1).trim();
    if (!speaker || !content) {
      throw new Error(`消息格式错误: ${chunk}（应为：昵称说内容）`);
    }
    const resolvedSpeaker = await resolveSpeaker(speaker);
    lines.push(`${resolvedSpeaker.displayName}: ${content}`);
  }
  if (lines.length === 0) {
    throw new Error("没有有效的消息内容");
  }
  return {
    lines,
    resolvedMessages: resolved,
    requesterQq: requesterQq || null,
    botQq: botQq || null,
  };
}

async function buildFakeForwardMessages(params: {
  api: OpenClawPluginApi;
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
  messages: string;
  userQq?: string;
  botQq?: string;
}) {
  let resolved = params.messages;
  const requesterQq = params.userQq?.trim();
  const botQq = params.botQq?.trim() || (await resolveCurrentBotQq({
    api: params.api,
    accountId: params.accountId,
  }));
  if (requesterQq) {
    resolved = resolved.replaceAll("{{USER_QQ}}", requesterQq);
  }
  if (botQq) {
    resolved = resolved.replaceAll("{{BOT_QQ}}", botQq);
  }
  if (resolved.includes("{{USER_QQ}}")) {
    throw new Error("messages 中包含 {{USER_QQ}}，但当前上下文没有可用的用户 QQ");
  }
  if (resolved.includes("{{BOT_QQ}}")) {
    throw new Error("messages 中包含 {{BOT_QQ}}，但当前配置里没有可用的机器人 QQ");
  }

  const resolveSpeaker = await createFakeSpeakerResolver({
    api: params.api,
    accountId: params.accountId,
    targetKind: params.targetKind,
    targetId: params.targetId,
    requesterQq: requesterQq ?? null,
    botQq: botQq ?? null,
  });
  const forwardMessages: Array<{
    type: "node";
    data: { name: string; uin: string; content: string };
  }> = [];

  for (const rawChunk of resolved.split("|")) {
    const chunk = rawChunk.trim();
    if (!chunk) {
      continue;
    }
    const splitAt = chunk.indexOf("说");
    if (splitAt <= 0) {
      throw new Error(`消息格式错误: ${chunk}（应为：QQ号说内容）`);
    }
    const speaker = chunk.slice(0, splitAt).trim();
    const content = chunk.slice(splitAt + 1).trim();
    if (!content) {
      throw new Error(`消息内容不能为空: ${chunk}`);
    }
    const resolvedSpeaker = await resolveSpeaker(speaker);
    for (const part of content.split(/\s+/u)) {
      const text = part.trim();
      if (!text) {
        continue;
      }
      forwardMessages.push({
        type: "node",
        data: {
          name: resolvedSpeaker.displayName,
          uin: resolvedSpeaker.userId,
          content: text,
        },
      });
    }
  }

  if (forwardMessages.length === 0) {
    throw new Error("没有有效的消息内容");
  }

  return {
    forwardMessages,
    resolvedMessages: resolved,
    requesterQq: requesterQq ?? null,
    botQq: botQq ?? null,
  };
}

async function resolveRecallTrackingKey(params: {
  api: OpenClawPluginApi;
  ctx: {
    agentId?: string;
    sessionKey?: string;
    requesterSenderId?: string;
  };
}) {
  const senderId = await resolveRequesterUserIdFromContext({
    api: params.api,
    ctx: params.ctx,
  });
  return buildRecallTrackingKey({
    sessionKey: params.ctx.sessionKey,
    senderId,
  });
}

async function resolveQqGroupTarget(params: {
  api: OpenClawPluginApi;
  ctx: {
    agentId?: string;
    sessionKey?: string;
    messageChannel?: string;
    agentAccountId?: string;
  };
  explicitGroupId?: string;
}) {
  const explicitGroupId = params.explicitGroupId?.trim();
  if (explicitGroupId) {
    return await resolveQqMessageTarget({
      api: params.api,
      ctx: params.ctx,
      explicitTarget: `group:${explicitGroupId}`,
    });
  }
  const target = await resolveQqMessageTarget({
    api: params.api,
    ctx: params.ctx,
  });
  if (target.targetKind !== "group") {
    throw new Error("current context is not a QQ group");
  }
  return target;
}

function findListedGroupFileBridge(listResult: unknown, fileId: string): Record<string, unknown> | null {
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
  if (files.length === 1) {
    return files[0] as Record<string, unknown>;
  }
  return null;
}

async function resolveGroupFileRecord(params: {
  api: OpenClawPluginApi;
  accountId?: string;
  groupId: string;
  fileId: string;
  folderId?: string;
}) {
  const listResult = params.folderId
    ? await getQqGroupFilesByFolder({
        cfg: params.api.config as CoreConfig,
        accountId: params.accountId,
        groupId: params.groupId,
        folderId: params.folderId,
      })
    : await getQqGroupRootFiles({
        cfg: params.api.config as CoreConfig,
        accountId: params.accountId,
        groupId: params.groupId,
      });
  const file = findListedGroupFileBridge(listResult, params.fileId);
  return { listResult, file };
}

async function resolveGroupFileBusid(params: {
  api: OpenClawPluginApi;
  accountId?: string;
  groupId: string;
  fileId: string;
  folderId?: string;
  busid?: string | number;
}) {
  if (params.busid !== undefined && String(params.busid).trim() !== "") {
    return {
      busid: params.busid,
      file: null as Record<string, unknown> | null,
      resolvedFileId: params.fileId,
    };
  }
  const { file } = await resolveGroupFileRecord(params);
  if (!file) {
    throw new Error("file not found in the listed folder (try specifying folder_id)");
  }
  const busid = file.busid ?? file.busId ?? file.bus_id;
  if (busid === undefined || String(busid).trim() === "") {
    throw new Error("busid unavailable for this file; specify busid manually");
  }
  return {
    busid,
    file,
    resolvedFileId: String(file.file_id ?? file.fileId ?? file.id ?? params.fileId).trim() || params.fileId,
  };
}

async function resolveBridgeMentionRecipient(params: {
  api: OpenClawPluginApi;
  accountId?: string;
  groupId: string;
  mentionUserId?: string;
  mentionName?: string;
}) {
  const result = await getQqGroupMembers({
    cfg: params.api.config as CoreConfig,
    accountId: params.accountId,
    groupId: params.groupId,
  });
  const members = Array.isArray(result.data) ? result.data : [];
  return findQqMentionMember({
    members: members as Record<string, unknown>[],
    mentionUserId: params.mentionUserId,
    mentionName: params.mentionName,
  });
}

function buildBridgeConversationKey(params: {
  accountId?: string;
  targetKind: "user" | "group";
  targetId: string;
}) {
  return `qq:${params.accountId ?? "default"}:${params.targetKind === "group" ? "group" : "direct"}:${params.targetId}`;
}

const plugin = {
  id: "chinobot-bridge",
  name: "ChinoBot Bridge",
  description: "Expose selected chino_bot utility capabilities as OpenClaw agent tools.",
  configSchema: pluginConfigSchema,
  register(api: OpenClawPluginApi) {
    api.registerTool({
      name: "chinobot_list_tools",
      label: "ChinoBot List Tools",
      description: "List currently bridged chino_bot capabilities available to OpenClaw.",
      parameters: ListBridgeToolsSchema,
      async execute() {
        const bridge = resolveBridgeConfig(api);
        try {
          const { stdout, stderr } = await execFileAsync(
            bridge.pythonPath,
            [bridge.bridgeScript, "list-tools"],
            {
              cwd: bridge.projectRoot,
              timeout: bridge.timeoutMs,
              maxBuffer: BRIDGE_MAX_BUFFER,
            },
          );
          const raw = stdout.trim();
          if (!raw) {
            return textResult("❌ chino_bot bridge 没有返回工具清单", { stderr });
          }
          return textResult(raw, JSON.parse(raw));
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          return textResult(`❌ 获取 chino_bot 工具清单失败：${message}`);
        }
      },
    } as AnyAgentTool);

    api.registerTool(
      ({
        name: "chinobot_packet_status",
        label: "ChinoBot Packet Status",
        description: "Check NapCat packetBackend status through the chino-style QQ tool surface.",
        parameters: ChinoBotQqPacketStatusSchema,
        async execute() {
          try {
            const result = await getQqPacketStatus({ cfg: api.config as CoreConfig });
            const ok = result.status === "ok" || result.retcode === 0;
            return jsonText({
              ok,
              status: result.status ?? null,
              retcode: result.retcode ?? null,
              message: result.message ?? null,
              wording: result.wording ?? null,
              error: ok ? null : result.message ?? result.wording ?? "packetBackend unavailable",
              data: result.data ?? null,
            });
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            return jsonText({ ok: false, error: message });
          }
        },
      }) as AnyAgentTool,
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_set_group_ban",
          label: "ChinoBot Set Group Ban",
          description:
            "Mute or unmute a QQ group member using chino-style defaults. Defaults to the current group and current sender when context is available.",
          parameters: ChinoBotQqGroupBanSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              user_id?: string;
              duration_seconds?: number;
              dry_run?: boolean;
            };
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const userId =
                params.user_id?.trim() ||
                (await resolveRequesterUserIdFromContext({
                  api,
                  ctx,
                })) ||
                "";
              if (!userId) {
                return jsonText({ ok: false, error: "user_id required outside current QQ sender context" });
              }
              const durationSeconds = Math.max(0, Math.trunc(Number(params.duration_seconds ?? 60)));
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  group_id: target.targetId,
                  user_id: userId,
                  duration_seconds: durationSeconds,
                  action: durationSeconds > 0 ? "ban" : "lift_ban",
                });
              }
              const result = await setQqGroupBan({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
                userId,
                duration: durationSeconds,
              });
              return jsonText({
                ok: isOneBotSuccess(result),
                source: target.source,
                group_id: target.targetId,
                user_id: userId,
                duration_seconds: durationSeconds,
                action: durationSeconds > 0 ? "ban" : "lift_ban",
                status: result.status ?? null,
                retcode: result.retcode ?? null,
                message: result.message ?? result.wording ?? null,
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_set_group_ban" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_set_group_whole_ban",
          label: "ChinoBot Set Group Whole Ban",
          description:
            "Enable or disable QQ whole-group mute using chino-style defaults. Defaults to the current QQ group.",
          parameters: ChinoBotQqGroupWholeBanSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              enable?: boolean;
              dry_run?: boolean;
            };
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const enable = params.enable !== false;
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  group_id: target.targetId,
                  enable,
                });
              }
              const result = await setQqGroupWholeBan({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
                enable,
              });
              return jsonText({
                ok: isOneBotSuccess(result),
                source: target.source,
                group_id: target.targetId,
                enable,
                status: result.status ?? null,
                retcode: result.retcode ?? null,
                message: result.message ?? result.wording ?? null,
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_set_group_whole_ban" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_set_group_kick",
          label: "ChinoBot Set Group Kick",
          description:
            "Kick a QQ group member using chino-style defaults. Defaults to the current group and current sender when context is available.",
          parameters: ChinoBotQqGroupKickSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              user_id?: string;
              reject_add_request?: boolean;
              dry_run?: boolean;
            };
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const userId =
                params.user_id?.trim() ||
                (await resolveRequesterUserIdFromContext({
                  api,
                  ctx,
                })) ||
                "";
              if (!userId) {
                return jsonText({ ok: false, error: "user_id required outside current QQ sender context" });
              }
              const rejectAddRequest = params.reject_add_request === true;
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  group_id: target.targetId,
                  user_id: userId,
                  reject_add_request: rejectAddRequest,
                });
              }
              const result = await setQqGroupKick({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
                userId,
                rejectAddRequest,
              });
              return jsonText({
                ok: isOneBotSuccess(result),
                source: target.source,
                group_id: target.targetId,
                user_id: userId,
                reject_add_request: rejectAddRequest,
                status: result.status ?? null,
                retcode: result.retcode ?? null,
                message: result.message ?? result.wording ?? null,
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_set_group_kick" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_set_group_admin",
          label: "ChinoBot Set Group Admin",
          description:
            "Grant or revoke QQ group admin status using chino-style defaults. Defaults to the current group and current sender when context is available.",
          parameters: ChinoBotQqGroupAdminSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              user_id?: string;
              enable?: boolean;
              dry_run?: boolean;
            };
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const userId =
                params.user_id?.trim() ||
                (await resolveRequesterUserIdFromContext({
                  api,
                  ctx,
                })) ||
                "";
              if (!userId) {
                return jsonText({ ok: false, error: "user_id required outside current QQ sender context" });
              }
              const enable = params.enable !== false;
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  group_id: target.targetId,
                  user_id: userId,
                  enable,
                });
              }
              const result = await setQqGroupAdmin({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
                userId,
                enable,
              });
              return jsonText({
                ok: isOneBotSuccess(result),
                source: target.source,
                group_id: target.targetId,
                user_id: userId,
                enable,
                status: result.status ?? null,
                retcode: result.retcode ?? null,
                message: result.message ?? result.wording ?? null,
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_set_group_admin" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_set_group_special_title",
          label: "ChinoBot Set Group Special Title",
          description:
            "Set or clear a QQ group special title using chino-style defaults. Defaults to the current group and current sender when context is available.",
          parameters: ChinoBotQqGroupSpecialTitleSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              user_id?: string;
              special_title?: string;
              dry_run?: boolean;
            };
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const userId =
                params.user_id?.trim() ||
                (await resolveRequesterUserIdFromContext({
                  api,
                  ctx,
                })) ||
                "";
              if (!userId) {
                return jsonText({ ok: false, error: "user_id required outside current QQ sender context" });
              }
              const specialTitle = typeof params.special_title === "string" ? params.special_title : "";
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  group_id: target.targetId,
                  user_id: userId,
                  special_title: specialTitle,
                  action: specialTitle.trim() ? "set_special_title" : "clear_special_title",
                });
              }
              const result = await setQqGroupSpecialTitle({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
                userId,
                specialTitle,
              });
              return jsonText({
                ok: isOneBotSuccess(result),
                source: target.source,
                group_id: target.targetId,
                user_id: userId,
                special_title: specialTitle,
                action: specialTitle.trim() ? "set_special_title" : "clear_special_title",
                status: result.status ?? null,
                retcode: result.retcode ?? null,
                message: result.message ?? result.wording ?? null,
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_set_group_special_title" },
    );

    api.registerTool({
      name: "chinobot_send_email",
      label: "ChinoBot Send Email",
      description: "Send an email through chino_bot's mail workflow.",
      parameters: SendEmailSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "send_email", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_receive_email",
      label: "ChinoBot Receive Email",
      description: "Read inbox mail through chino_bot's mail workflow.",
      parameters: ReceiveEmailSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "receive_email", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_read_pdf",
      label: "ChinoBot Read PDF",
      description: "Read a PDF document through chino_bot's document workflow.",
      parameters: ReadPdfSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "read_pdf", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_read_word",
      label: "ChinoBot Read Word",
      description: "Read a Word document through chino_bot's document workflow.",
      parameters: ReadWordSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "read_word", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_create_word",
      label: "ChinoBot Create Word",
      description: "Create a Word document through chino_bot's document workflow.",
      parameters: CreateWordSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "create_word", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_read_excel",
      label: "ChinoBot Read Excel",
      description: "Read an Excel workbook through chino_bot's document workflow.",
      parameters: ReadExcelSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "read_excel", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_create_excel",
      label: "ChinoBot Create Excel",
      description: "Create an Excel workbook through chino_bot's document workflow.",
      parameters: CreateExcelSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "create_excel", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_convert_word_to_pdf",
      label: "ChinoBot Convert Word To PDF",
      description: "Convert a Word document into PDF through chino_bot's document workflow.",
      parameters: ConvertWordToPdfSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(
          api,
          "convert_word_to_pdf",
          (rawParams ?? {}) as Record<string, unknown>,
        );
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_convert_pdf_to_word",
      label: "ChinoBot Convert PDF To Word",
      description: "Convert a PDF into Word through chino_bot's document workflow.",
      parameters: ConvertPdfToWordSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(
          api,
          "convert_pdf_to_word",
          (rawParams ?? {}) as Record<string, unknown>,
        );
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_parse_link",
      label: "ChinoBot Parse Link",
      description: "Resolve selected links using chino_bot's link parsing workflow.",
      parameters: ParseLinkSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "parse_link", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool({
      name: "chinobot_tavily_search",
      label: "ChinoBot Tavily Search",
      description:
        "Search the live web through chino_bot's Tavily-backed workflow. Useful for current facts, news, or online lookup when you want the chino_bot-side search path.",
      parameters: TavilySearchSchema,
      async execute(_toolCallId, rawParams) {
        return runBridgeTool(api, "tavily_search", (rawParams ?? {}) as Record<string, unknown>);
      },
    } as AnyAgentTool);

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_render_html",
          label: "ChinoBot Render HTML",
          description:
            "Render HTML/CSS into a QQ-ready image through chino_bot's HTML drawing workflow. In QQ sessions it will explicitly send the generated image instead of only returning media metadata.",
          parameters: RenderHtmlSchema,
          async execute(_toolCallId, rawParams) {
            return runBridgeVisualTool(
              api,
              ctx,
              "render_html",
              (rawParams ?? {}) as Record<string, unknown>,
            );
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_render_html" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_web_screenshot",
          label: "ChinoBot Web Screenshot",
          description:
            "Capture a webpage screenshot through chino_bot's visual workflow. In QQ sessions it will explicitly send the generated image instead of only returning media metadata.",
          parameters: WebScreenshotSchema,
          async execute(_toolCallId, rawParams) {
            return runBridgeVisualTool(
              api,
              ctx,
              "web_screenshot",
              (rawParams ?? {}) as Record<string, unknown>,
            );
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_web_screenshot" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_get_group_file_info",
          label: "ChinoBot Get Group File Info",
          description:
            "Get QQ group file metadata using chino_bot-style defaults. If group_id is omitted, use the current QQ group conversation.",
          parameters: ChinoBotQqGroupFileInfoSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              file_id?: string;
              folder_id?: string;
            };
            const fileId = params.file_id?.trim();
            if (!fileId) {
              return jsonText({ ok: false, error: "file_id required" });
            }
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const folderId = params.folder_id?.trim();
              const { listResult, file } = await resolveGroupFileRecord({
                api,
                accountId: target.accountId,
                groupId: target.targetId,
                fileId,
                folderId,
              });
              if (!file) {
                const payload = (listResult.data ?? {}) as Record<string, unknown>;
                const files = Array.isArray(payload.files) ? payload.files : [];
                return jsonText({
                  ok: false,
                  group_id: target.targetId,
                  folder_id: folderId ?? null,
                  file_id: fileId,
                  error: "file not found in the listed folder (try specifying folder_id)",
                  file_count: files.length,
                });
              }
              const resolvedFileId = String(file.file_id ?? file.fileId ?? file.id ?? "").trim() || fileId;
              return jsonText({
                ok: true,
                group_id: target.targetId,
                folder_id: folderId ?? null,
                file_id: fileId,
                resolved_file_id: resolvedFileId,
                file,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_get_group_file_info" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_get_group_file_url",
          label: "ChinoBot Get Group File URL",
          description:
            "Get a QQ group file download URL using chino_bot-style defaults. If group_id is omitted, use the current QQ group conversation. If busid is omitted, try to infer it from the file listing.",
          parameters: ChinoBotQqGroupFileUrlSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              file_id?: string;
              busid?: string | number;
              folder_id?: string;
            };
            const fileId = params.file_id?.trim();
            if (!fileId) {
              return jsonText({ ok: false, error: "file_id required" });
            }
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const folderId = params.folder_id?.trim();
              const { busid, resolvedFileId } = await resolveGroupFileBusid({
                api,
                accountId: target.accountId,
                groupId: target.targetId,
                fileId,
                folderId,
                busid: params.busid,
              });
              const result = await getQqGroupFileUrl({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
                fileId: resolvedFileId,
                busid,
              });
              const ok = result.status === "ok" || result.retcode === 0;
              const url = String((result.data as Record<string, unknown> | undefined)?.url ?? "");
              return jsonText({
                ok,
                group_id: target.targetId,
                file_id: resolvedFileId,
                folder_id: folderId ?? null,
                busid,
                url: url || null,
                status: result.status ?? null,
                retcode: result.retcode ?? null,
                message: result.message ?? null,
                wording: result.wording ?? null,
                error: ok ? null : result.message ?? result.wording ?? "get_group_file_url failed",
                hint: ok ? null : maybePacketBackendHint(result.message, result.wording),
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_get_group_file_url" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_download_group_file",
          label: "ChinoBot Download Group File",
          description:
            "Download a QQ group file using chino_bot-style defaults. If group_id is omitted, use the current QQ group conversation. If busid is omitted, try to infer it from the file listing.",
          parameters: ChinoBotQqGroupFileDownloadSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              group_id?: string;
              file_id?: string;
              busid?: string | number;
              folder_id?: string;
              output_path?: string;
              dry_run?: boolean;
            };
            const fileId = params.file_id?.trim();
            if (!fileId) {
              return jsonText({ ok: false, error: "file_id required" });
            }
            try {
              const cfg = api.config as CoreConfig;
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const folderId = params.folder_id?.trim();
              const { busid, file, resolvedFileId } = await resolveGroupFileBusid({
                api,
                accountId: target.accountId,
                groupId: target.targetId,
                fileId,
                folderId,
                busid: params.busid,
              });
              const urlResult = await getQqGroupFileUrl({
                cfg,
                accountId: target.accountId,
                groupId: target.targetId,
                fileId: resolvedFileId,
                busid,
              });
              const urlOk = urlResult.status === "ok" || urlResult.retcode === 0;
              const remoteUrl = String((urlResult.data as Record<string, unknown> | undefined)?.url ?? "").trim();

              const outputDir = path.join(os.tmpdir(), "openclaw-qq-group-files");
              const preferredPath = (() => {
                const explicit = params.output_path?.trim();
                if (explicit) {
                  return api.resolvePath(explicit);
                }
                const guessedName = guessFilenameFromUrl(remoteUrl);
                const fallbackName =
                  String(file?.file_name ?? file?.fileName ?? "").trim() ||
                  guessedName ||
                  `${resolvedFileId}.bin`;
                return path.join(outputDir, `qq-${target.targetId}-${resolvedFileId}-${fallbackName}`);
              })();
              const outputPath = await ensureUniqueFilePath(preferredPath);

              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  group_id: target.targetId,
                  folder_id: folderId ?? null,
                  file_id: resolvedFileId,
                  busid,
                  url_status: {
                    ok: urlOk,
                    status: urlResult.status ?? null,
                    retcode: urlResult.retcode ?? null,
                    message: urlResult.message ?? null,
                    wording: urlResult.wording ?? null,
                    hint: maybePacketBackendHint(urlResult.message, urlResult.wording),
                  },
                  planned_download_source: urlOk && remoteUrl ? "group_file_url" : "get_file_fallback",
                  url: urlOk && remoteUrl ? remoteUrl : null,
                  output_path: outputPath,
                });
              }

              let downloadSource: "group_file_url" | "get_file" = "group_file_url";
              let sourcePath: string | null = null;
              if (!urlOk || !remoteUrl) {
                const fileResult = await getQqFile({
                  cfg,
                  accountId: target.accountId,
                  fileId,
                });
                const fileOk = fileResult.status === "ok" || fileResult.retcode === 0;
                const filePayload = (fileResult.data ?? {}) as Record<string, unknown>;
                const fileCandidate = String(filePayload.file ?? filePayload.url ?? "").trim();
                if (!fileOk || !fileCandidate) {
                  return jsonText({
                    ok: false,
                    group_id: target.targetId,
                    folder_id: folderId ?? null,
                    file_id: resolvedFileId,
                    busid,
                    error: urlResult.message ?? urlResult.wording ?? "failed to get file url",
                    hint: maybePacketBackendHint(urlResult.message, urlResult.wording),
                    status: urlResult.status ?? null,
                    retcode: urlResult.retcode ?? null,
                    message: urlResult.message ?? null,
                    wording: urlResult.wording ?? null,
                    data: urlResult.data ?? null,
                    fallback: {
                      ok: fileOk,
                      error: fileResult.message ?? fileResult.wording ?? "get_file failed",
                      status: fileResult.status ?? null,
                      retcode: fileResult.retcode ?? null,
                      message: fileResult.message ?? null,
                      wording: fileResult.wording ?? null,
                      data: fileResult.data ?? null,
                    },
                  });
                }
                downloadSource = "get_file";
                sourcePath = fileCandidate;
              }

              let bytes = 0;
              if (downloadSource === "group_file_url") {
                ({ bytes } = await downloadToFile({ url: remoteUrl, outputPath }));
              } else if (EXTERNAL_URL_RE.test(sourcePath ?? "")) {
                ({ bytes } = await downloadToFile({ url: sourcePath ?? "", outputPath }));
              } else {
                await fs.mkdir(path.dirname(outputPath), { recursive: true });
                await fs.copyFile(sourcePath ?? "", outputPath);
                const stat = await fs.stat(outputPath);
                bytes = stat.size;
              }
              return jsonText({
                ok: true,
                group_id: target.targetId,
                folder_id: folderId ?? null,
                file_id: resolvedFileId,
                busid,
                download_source: downloadSource,
                url: downloadSource === "group_file_url" ? remoteUrl : null,
                source_path: downloadSource === "get_file" ? sourcePath : null,
                output_path: outputPath,
                bytes,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_download_group_file" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_get_user_info",
          label: "ChinoBot Get User Info",
          description:
            "Get QQ user info using chino_bot-style defaults. If user_id is omitted, use the current sender in this QQ conversation.",
          parameters: ChinoBotQqUserInfoSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { user_id?: string };
            const userId =
              params.user_id?.trim() ||
              (await resolveRequesterUserIdFromContext({
                api,
                ctx,
              }));
            if (!userId) {
              return jsonText({ ok: false, error: "user_id required or current sender unavailable" });
            }
            try {
              const result = await getQqUserInfo({
                cfg: api.config as CoreConfig,
                accountId: ctx.agentAccountId?.trim() || undefined,
                userId,
              });
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                user_id: userId,
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message, user_id: userId });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_get_user_info" },
    );

    api.registerTool(
      ({
        name: "chinobot_get_self_info",
        label: "ChinoBot Get Self Info",
        description: "Get the current QQ bot account info through the chino-style QQ tool surface.",
        parameters: ChinoBotQqSelfInfoSchema,
        async execute() {
          try {
            const result = await getQqLoginInfo({
              cfg: api.config as CoreConfig,
            });
            return jsonText({
              ok: result.status === "ok" || result.retcode === 0,
              data: result.data ?? null,
            });
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            return jsonText({ ok: false, error: message });
          }
        },
      }) as AnyAgentTool,
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_get_group_info",
          label: "ChinoBot Get Group Info",
          description:
            "Get QQ group info using chino_bot-style defaults. If group_id is omitted, use the current QQ group conversation.",
          parameters: ChinoBotQqGroupInfoSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { group_id?: string };
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const result = await getQqGroupInfo({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
              });
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                group_id: target.targetId,
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_get_group_info" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_send_like",
          label: "ChinoBot Send Like",
          description:
            "Send QQ likes using chino_bot-style defaults. If user_id is omitted, use the current sender in this QQ conversation.",
          parameters: ChinoBotQqSendLikeSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { user_id?: string; times?: number };
            const userId =
              params.user_id?.trim() ||
              (await resolveRequesterUserIdFromContext({
                api,
                ctx,
              }));
            if (!userId) {
              return jsonText({ ok: false, error: "user_id required or current sender unavailable" });
            }
            try {
              const result = await sendQqLike({
                cfg: api.config as CoreConfig,
                accountId: ctx.agentAccountId?.trim() || undefined,
                userId,
                times: params.times,
              });
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                user_id: userId,
                times: Math.max(1, Math.min(10, Number(params.times ?? 10))),
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message, user_id: userId });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_send_like" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_send_poke",
          label: "ChinoBot Send Poke",
          description:
            "Send a QQ 戳一戳 using chino_bot-style defaults. In direct chats it defaults to the current peer; in groups it defaults to the current sender unless user_id is provided.",
          parameters: ChinoBotQqSendPokeSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              user_id?: string;
              target?: string;
              dry_run?: boolean;
            };
            try {
              const target = await resolveQqMessageTarget({
                api,
                ctx,
                explicitTarget: params.target,
              });
              const explicitUserId = params.user_id?.trim() || undefined;
              const requesterUserId =
                (await resolveRequesterUserIdFromContext({
                  api,
                  ctx,
                })) || undefined;
              const pokeUserId =
                target.targetKind === "user"
                  ? explicitUserId ?? target.targetId
                  : explicitUserId ?? requesterUserId;
              if (target.targetKind === "group" && !pokeUserId) {
                return jsonText({
                  ok: false,
                  error: "group poke requires user_id, or must be called from a QQ group session with a known current sender",
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                });
              }
              if (params.dry_run === true) {
                return jsonText({
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
              return jsonText({
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
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_send_poke" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_analyze_avatar",
          label: "ChinoBot Analyze Avatar",
          description:
            "Fetch and analyze a QQ avatar. By default it uses the current sender in the current QQ conversation; set self=true to inspect the bot's own avatar.",
          parameters: ChinoBotAnalyzeAvatarSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              user_id?: string;
              self?: boolean;
              avatar_size?: number;
            };
            try {
              const inferredTarget = await resolveQqMessageTarget({
                api,
                ctx,
              }).catch(() => null);
              const accountId =
                inferredTarget?.accountId ?? ctx.agentAccountId?.trim() ?? undefined;
              const isSelf = params.self === true;
              let userId: string | undefined;
              let displayName: string | undefined;
              let subject: "self" | "user" = isSelf ? "self" : "user";

              if (isSelf) {
                const profile = await resolveCurrentBotProfile({
                  api,
                  accountId,
                });
                userId = profile.userId;
                displayName = profile.displayName;
              } else {
                userId =
                  params.user_id?.trim() ||
                  (await resolveRequesterUserIdFromContext({
                    api,
                    ctx,
                  })) ||
                  (inferredTarget?.targetKind === "user" ? inferredTarget.targetId : undefined);
                if (userId) {
                  displayName = await resolveQqDisplayName({
                    api,
                    accountId,
                    userId,
                  });
                }
              }

              if (!userId) {
                return jsonText({
                  ok: false,
                  error: isSelf
                    ? "无法确定当前机器人的 QQ 号"
                    : "user_id required or current sender unavailable",
                });
              }

              const avatarSize = normalizeQqAvatarSize(params.avatar_size);
              const avatarUrl = buildQqUserAvatarUrl(userId, avatarSize);
              const downloaded = await downloadQqAvatarImage({
                avatarUrl,
                userId,
              });
              const insight = await describeQqImageWithModel({
                cfg: api.config as CoreConfig,
                agentId: ctx.agentId?.trim() || "main",
                filePath: downloaded.filePath,
                sourceUrl: avatarUrl,
                contentType: downloaded.contentType,
                index: 1,
                logger: api.logger,
              });

              return jsonText({
                ok: true,
                subject,
                user_id: userId,
                display_name: displayName ?? null,
                avatar_size: avatarSize,
                avatar_url: avatarUrl,
                avatar_source: "inferred_qq_avatar_cdn",
                analysis: {
                  alt: insight.alt,
                  vision_summary: insight.vision_summary,
                  ocr: insight.ocr,
                },
                next_step_hints: [
                  "Use avatar_url as image_url for chinobot_make_meme if you want to add text or make a reaction image.",
                  "Use avatar_url inside chinobot_render_html if you want a card, profile layout, quote image, or poster built around the avatar.",
                  "Use avatar_url with chinobot_send_image if you simply want to send the avatar back into QQ.",
                ],
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_analyze_avatar" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_get_group_member_info",
          label: "ChinoBot Get Group Member Info",
          description:
            "Get detailed info for one member in the current QQ group. If group_id or user_id is omitted, use the current group/current sender when available.",
          parameters: ChinoBotQqGroupMemberInfoSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { group_id?: string; user_id?: string };
            try {
              const target = await resolveQqSessionTarget({ api, ctx });
              const groupId =
                params.group_id?.trim() ||
                (target.targetKind === "group" ? target.targetId : undefined);
              const userId =
                params.user_id?.trim() ||
                (await resolveRequesterUserIdFromContext({
                  api,
                  ctx,
                }));
              if (!groupId) {
                return jsonText({ ok: false, error: "group_id required or current QQ group unavailable" });
              }
              if (!userId) {
                return jsonText({ ok: false, error: "user_id required or current sender unavailable" });
              }
              const result = await getQqGroupMembers({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId,
              });
              const members = Array.isArray(result.data) ? result.data : [];
              const member =
                members.find((entry) => {
                  const row = entry as Record<string, unknown>;
                  return String(row.user_id ?? row.userId ?? "").trim() === userId;
                }) ?? null;
              return jsonText({
                ok: (result.status === "ok" || result.retcode === 0) && Boolean(member),
                group_id: groupId,
                user_id: userId,
                member,
                member_count: members.length,
                error: member ? null : "member not found in current group list",
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_get_group_member_info" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_get_group_members",
          label: "ChinoBot Get Group Members",
          description:
            "List QQ group members using chino_bot-style defaults. If group_id is omitted, use the current QQ group conversation.",
          parameters: ChinoBotQqGroupMembersSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { group_id?: string };
            try {
              const target = await resolveQqGroupTarget({
                api,
                ctx,
                explicitGroupId: params.group_id,
              });
              const result = await getQqGroupMembers({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                groupId: target.targetId,
              });
              const members = Array.isArray(result.data) ? result.data : [];
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                group_id: target.targetId,
                count: members.length,
                members,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_get_group_members" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_get_group_files",
          label: "ChinoBot Get Group Files",
          description:
            "List QQ group files using chino_bot-style defaults. If group_id is omitted, use the current QQ group conversation.",
          parameters: ChinoBotQqGroupFilesSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { group_id?: string; folder_id?: string };
            try {
              const target = await resolveQqSessionTarget({ api, ctx });
              const groupId =
                params.group_id?.trim() ||
                (target.targetKind === "group" ? target.targetId : undefined);
              if (!groupId) {
                return jsonText({ ok: false, error: "group_id required or current QQ group unavailable" });
              }
              const folderId = params.folder_id?.trim();
              const result = folderId
                ? await getQqGroupFilesByFolder({
                    cfg: api.config as CoreConfig,
                    accountId: target.accountId,
                    groupId,
                    folderId,
                  })
                : await getQqGroupRootFiles({
                    cfg: api.config as CoreConfig,
                    accountId: target.accountId,
                    groupId,
                  });
              const payload = (result.data ?? {}) as Record<string, unknown>;
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                group_id: groupId,
                folder_id: folderId ?? null,
                files: Array.isArray(payload.files) ? payload.files : [],
                folders: Array.isArray(payload.folders) ? payload.folders : [],
                data: result.data ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_get_group_files" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_upload_group_file",
          label: "ChinoBot Upload Group File",
          description:
            "Upload a file to QQ group files using chino_bot-style defaults. If group_id is omitted, use the current QQ group conversation.",
          parameters: ChinoBotQqUploadGroupFileSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              file_path?: string;
              name?: string;
              group_id?: string;
              folder?: string;
              upload_file?: boolean;
              dry_run?: boolean;
            };
            const filePathInput = params.file_path?.trim();
            if (!filePathInput) {
              return jsonText({ ok: false, error: "file_path required" });
            }
            try {
              const explicitGroupId = params.group_id?.trim() || undefined;
              let accountId = ctx.agentAccountId?.trim() || undefined;
              let groupId = explicitGroupId;
              if (!groupId) {
                const target = await resolveQqSessionTarget({ api, ctx });
                groupId = target.targetKind === "group" ? target.targetId : undefined;
                accountId = target.accountId ?? accountId;
              } else {
                try {
                  const inferred = await resolveQqSessionTarget({ api, ctx });
                  accountId = inferred.accountId ?? accountId;
                } catch {
                  // Explicit group targets can still work outside an active QQ session.
                }
              }
              if (!groupId) {
                return jsonText({ ok: false, error: "group_id required or current QQ group unavailable" });
              }
              const resolvedPath = api.resolvePath(filePathInput);
              const stat = await fs.stat(resolvedPath);
              if (!stat.isFile()) {
                return jsonText({ ok: false, error: `not a file: ${resolvedPath}` });
              }
              const fileName = params.name?.trim() || path.basename(resolvedPath);
              const cfg = api.config as CoreConfig;
              const requestedUploadFile =
                typeof params.upload_file === "boolean" ? params.upload_file : undefined;
              const folderId = params.folder?.trim() || undefined;
              const proxyUrl = await resolveQqHttpMediaUrl({
                mediaUrl: resolvedPath,
                gatewayPort: cfg.gateway?.port,
              });
              const normalizedProxyUrl = proxyUrl && proxyUrl !== resolvedPath ? proxyUrl : null;
              const plannedAttempts = [
                {
                  source: "local_path",
                  upload_file: requestedUploadFile ?? null,
                  file_ref: resolvedPath,
                },
                ...(requestedUploadFile === undefined
                  ? [{ source: "local_path", upload_file: false, file_ref: resolvedPath }]
                  : []),
                ...(normalizedProxyUrl
                  ? [
                      {
                        source: "proxy_url",
                        upload_file: requestedUploadFile ?? null,
                        file_ref: normalizedProxyUrl,
                      },
                      ...(requestedUploadFile === undefined
                        ? [{ source: "proxy_url", upload_file: false, file_ref: normalizedProxyUrl }]
                        : []),
                    ]
                  : []),
              ];
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  group_id: groupId,
                  file_path: resolvedPath,
                  name: fileName,
                  folder: folderId ?? "/",
                  upload_file: requestedUploadFile ?? null,
                  proxy_url: normalizedProxyUrl,
                  attempts: plannedAttempts,
                });
              }
              const outcome = await attemptQqGroupFileUploadWithFallback({
                cfg,
                accountId,
                groupId,
                resolvedPath,
                name: fileName,
                folderId,
                requestedUploadFile,
              });
              return jsonText({
                ok: outcome.ok,
                group_id: groupId,
                file_path: resolvedPath,
                name: fileName,
                folder: folderId ?? "/",
                proxy_url: outcome.proxy_url,
                upload_source: outcome.upload_source,
                upload_file: outcome.upload_file,
                attempts: outcome.attempts,
                data: outcome.result?.data ?? null,
                error: outcome.ok ? null : summarizeOneBotFailure(outcome.result),
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_upload_group_file" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_send_mention",
          label: "ChinoBot Send Mention",
          description:
            "Send a QQ group message that @mentions a specific member using chino_bot-style defaults. If target is omitted, use the current QQ group conversation.",
          parameters: ChinoBotQqSendMentionSchema,
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
              return jsonText({ ok: false, error: "text required" });
            }
            if (!params.mention_user_id?.trim() && !params.mention_name?.trim()) {
              return jsonText({ ok: false, error: "mention_user_id or mention_name required" });
            }
            try {
              const explicitTarget = params.target?.trim();
              const target = await resolveQqMessageTarget({
                api,
                ctx,
                explicitTarget:
                  explicitTarget && /^\d+$/u.test(explicitTarget)
                    ? `group:${explicitTarget}`
                    : explicitTarget,
              });
              if (target.targetKind !== "group") {
                return jsonText({
                  ok: false,
                  error: "chinobot_send_mention only supports QQ group targets",
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                });
              }
              const member = await resolveBridgeMentionRecipient({
                api,
                accountId: target.accountId,
                groupId: target.targetId,
                mentionUserId: params.mention_user_id?.trim(),
                mentionName: params.mention_name?.trim(),
              });
              const message = buildQqMentionSegments({
                mentionUserId: member.userId,
                text,
                replyToMessageId: params.reply_to_message_id?.trim(),
              });
              if (params.dry_run === true) {
                return jsonText({
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
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                targetKind: "group",
                targetId: target.targetId,
                message: message as never,
              });
              return jsonText({
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
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_send_mention" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_search_image",
          label: "ChinoBot Search Image",
          description: "Search images online and return send-ready image URLs for QQ replies.",
          parameters: ChinoBotQqSearchImageSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { query?: string; count?: number };
            try {
              return jsonText(
                await runQqSearchImage(
                  {
                    query: params.query ?? "",
                    count: params.count,
                  },
                  api.config as CoreConfig,
                ),
              );
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_search_image" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_send_image",
          label: "ChinoBot Send Image",
          description:
            "Send an image to the current QQ conversation using chino_bot-style defaults. If target is omitted, use the current QQ conversation.",
          parameters: ChinoBotQqSendImageSchema,
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
              return jsonText({ ok: false, error: "image_url or image_path required" });
            }
            try {
              const target = await resolveQqMessageTarget({
                api,
                ctx,
                explicitTarget: params.target,
              });
              const mediaUrl = imagePath ? api.resolvePath(imagePath) : (imageUrl ?? "");
              if (params.dry_run === true) {
                return jsonText({
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
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                media_url: mediaUrl,
                caption: params.caption?.trim() ?? "",
                data: result.data ?? null,
                message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_send_image" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_send_voice",
          label: "ChinoBot Send Voice",
          description:
            "Send a spoken QQ reply using chino_bot-style defaults. If target is omitted, use the current QQ conversation.",
          parameters: ChinoBotQqSendVoiceSchema,
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
              return jsonText({ ok: false, error: "text, audio_url, or audio_path required" });
            }
            try {
              const target = await resolveQqMessageTarget({
                api,
                ctx,
                explicitTarget: params.target,
              });
              const preferPtt = params.prefer_ptt !== false;
              const resolvedAudio =
                audioPath ? api.resolvePath(audioPath) : audioUrl ? audioUrl : null;
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                  account_id: target.accountId ?? null,
                  text: text || null,
                  audio_url: resolvedAudio,
                  synthesize_on_send: !resolvedAudio && Boolean(text),
                  caption: params.caption?.trim() ?? "",
                  preferred_mode: preferPtt ? "ptt" : "audio",
                  fallback_mode: preferPtt ? "audio" : "ptt",
                  final_fallback: "text",
                  capabilities: ["qq-ptt", "qq-audio-file", "qq-text-only"],
                  synthesis_provider: resolvedAudio
                    ? "user-supplied-audio"
                    : resolveBridgeConfig(api).voiceSynthesis.enabled
                      ? "local-qwen-clone"
                      : "system-say",
                  synthesis_voice_name: resolvedAudio
                    ? null
                    : resolveBridgeConfig(api).voiceSynthesis.enabled
                      ? resolveBridgeConfig(api).voiceSynthesis.voiceName
                      : "Ting-Ting",
                });
              }
              const mediaUrl =
                resolvedAudio ??
                (await synthesizeBridgeQqVoiceFromTextWithConfig(
                  text,
                  resolveBridgeConfig(api).voiceSynthesis,
                ));
              const outcome = await sendQqVoice({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                targetKind: target.targetKind,
                targetId: target.targetId,
                audioUrl: mediaUrl,
                caption: params.caption?.trim() ?? "",
                preferPtt,
              });
              return jsonText({
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
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_send_voice" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_make_meme",
          label: "ChinoBot Make Meme",
          description:
            "Create a meme image with embedded text using chino_bot-style defaults. If no image is provided, it can reuse the current QQ conversation's recent image.",
          parameters: ChinoBotQqMakeMemeSchema,
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
                | null = null;
              if (!imageUrl && !imagePath && params.use_current_image !== false) {
                const target = await resolveQqMessageTarget({
                  api,
                  ctx,
                  explicitTarget: params.target,
                });
                const conversationKey = buildBridgeConversationKey({
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
              const explicitDelivered =
                result && result.ok
                  ? await tryExplicitQqVisualDelivery({
                      api,
                      ctx,
                      resultRecord: asRecord(result),
                      explicitTarget: params.target,
                    })
                  : null;
              if (explicitDelivered) {
                const payload =
                  asRecord((explicitDelivered as { details?: unknown }).details) ?? {};
                return jsonText({
                  ...payload,
                  meme_source: memeSource,
                });
              }
              return jsonText({
                ...result,
                meme_source: memeSource,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_make_meme" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_send_file",
          label: "ChinoBot Send File",
          description:
            "Send a local file to the current QQ conversation using chino_bot-style defaults. If target is omitted, use the current QQ conversation.",
          parameters: ChinoBotQqSendFileSchema,
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
              return jsonText({ ok: false, error: "file_path required" });
            }
            if (/^[a-z][a-z0-9+.-]*:\/\//iu.test(filePathInput)) {
              return jsonText({ ok: false, error: "file_path must be a local file path", file_path: filePathInput });
            }
            try {
              const target = await resolveQqMessageTarget({
                api,
                ctx,
                explicitTarget: params.target,
              });
              const resolvedPath = api.resolvePath(filePathInput);
              const stat = await fs.stat(resolvedPath);
              if (!stat.isFile()) {
                return jsonText({ ok: false, error: `not a file: ${resolvedPath}` });
              }
              const fileName = (params.name?.trim() || path.basename(resolvedPath)).trim();
              if (!fileName) {
                return jsonText({ ok: false, error: "name cannot be empty" });
              }
              const caption = params.caption?.trim() ?? "";
              const localFileUrl = pathToFileURL(resolvedPath).toString();
              const proxyUrl = await resolveQqHttpMediaUrl({
                mediaUrl: resolvedPath,
                gatewayPort: (api.config as CoreConfig).gateway?.port,
              });
              const candidates = [
                { source: "file_url", fileRef: localFileUrl },
                { source: "local_path", fileRef: resolvedPath },
                ...(proxyUrl && proxyUrl !== resolvedPath ? [{ source: "proxy_url", fileRef: proxyUrl }] : []),
              ] as const;
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                  account_id: target.accountId ?? null,
                  file_path: resolvedPath,
                  file_url: localFileUrl,
                  proxy_url: proxyUrl && proxyUrl !== resolvedPath ? proxyUrl : null,
                  name: fileName,
                  caption,
                  fallback_group_file_upload: target.targetKind === "group",
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
                  cfg: api.config as CoreConfig,
                  accountId: target.accountId,
                  targetKind: target.targetKind,
                  targetId: target.targetId,
                  message: [
                    ...(caption ? [{ type: "text", data: { text: caption } }] : []),
                    { type: "file", data: { file: candidate.fileRef, name: fileName } },
                  ] as never,
                });
                const ok = isOneBotSuccess(result);
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
                  return jsonText({
                    ok: true,
                    source: target.source,
                    target_kind: target.targetKind,
                    target_id: target.targetId,
                    account_id: target.accountId ?? null,
                    file_path: resolvedPath,
                    file_ref: candidate.fileRef,
                    file_ref_source: candidate.source,
                    name: fileName,
                    caption,
                    delivery_mode: "message_file",
                    attempts,
                    data: result.data ?? null,
                    message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
                  });
                }
              }
              const last = attempts[attempts.length - 1] ?? null;
              if (target.targetKind === "group") {
                const uploadOutcome = await attemptQqGroupFileUploadWithFallback({
                  cfg: api.config as CoreConfig,
                  accountId: target.accountId,
                  groupId: target.targetId,
                  resolvedPath,
                  name: fileName,
                });
                return jsonText({
                  ok: uploadOutcome.ok,
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                  account_id: target.accountId ?? null,
                  file_path: resolvedPath,
                  file_url: localFileUrl,
                  proxy_url: proxyUrl && proxyUrl !== resolvedPath ? proxyUrl : null,
                  name: fileName,
                  caption,
                  delivery_mode: uploadOutcome.ok ? "group_file_upload_fallback" : "message_file_failed",
                  attempts,
                  fallback: {
                    mode: "group_file_upload",
                    ok: uploadOutcome.ok,
                    upload_source: uploadOutcome.upload_source,
                    upload_file: uploadOutcome.upload_file,
                    proxy_url: uploadOutcome.proxy_url,
                    attempts: uploadOutcome.attempts,
                    retcode: uploadOutcome.result?.retcode ?? null,
                    status: uploadOutcome.result?.status ?? null,
                    message: uploadOutcome.result?.message ?? null,
                    wording: uploadOutcome.result?.wording ?? null,
                    data: uploadOutcome.result?.data ?? null,
                  },
                  error: uploadOutcome.ok
                    ? null
                    : `${summarizeOneBotFailure(last)}; fallback upload failed: ${summarizeOneBotFailure(uploadOutcome.result)}`,
                });
              }
              return jsonText({
                ok: false,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                file_path: resolvedPath,
                file_url: localFileUrl,
                proxy_url: proxyUrl && proxyUrl !== resolvedPath ? proxyUrl : null,
                name: fileName,
                caption,
                delivery_mode: "message_file_failed",
                attempts,
                error: summarizeOneBotFailure(last),
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_send_file" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_recall_message",
          label: "ChinoBot Recall Message",
          description:
            "Recall recent QQ messages sent by OpenClaw in the current conversation for the current sender.",
          parameters: ChinoBotQqRecallSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as { count?: number; dry_run?: boolean };
            try {
              const trackingKey = await resolveRecallTrackingKey({
                api,
                ctx,
              });
              if (!trackingKey) {
                return jsonText({
                  ok: false,
                  error: "current context is missing session or sender information",
                });
              }
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  tracking_key: trackingKey,
                  count: Math.max(1, Math.min(5, Number(params.count ?? 1))),
                });
              }
              const result = await recallRecentQqMessages({
                cfg: api.config as CoreConfig,
                trackingKey,
                count: params.count,
              });
              return jsonText(result);
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_recall_message" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_send_fake_message",
          label: "ChinoBot Send Fake Message",
          description:
            "Send chino_bot-style fake merged-forward QQ messages. Speakers can be QQ numbers, 触发者, 机器人, or current-group member nicknames/cards. If target is omitted, use the current QQ conversation.",
          parameters: ChinoBotQqFakeMessageSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              messages?: string;
              user_qq?: string;
              bot_qq?: string;
              target?: string;
              dry_run?: boolean;
            };
            const messages = params.messages?.trim();
            if (!messages) {
              return jsonText({ ok: false, error: "messages required" });
            }
            try {
              const target = await resolveQqMessageTarget({
                api,
                ctx,
                explicitTarget: params.target,
              });
              const built = await buildFakeForwardMessages({
                api,
                accountId: target.accountId,
                targetKind: target.targetKind,
                targetId: target.targetId,
                messages,
                userQq:
                  params.user_qq?.trim() ||
                  (await resolveRequesterUserIdFromContext({
                    api,
                    ctx,
                  })),
                botQq: params.bot_qq?.trim(),
              });
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                  account_id: target.accountId ?? null,
                  requester_qq: built.requesterQq,
                  bot_qq: built.botQq,
                  message_count: built.forwardMessages.length,
                  resolved_messages: built.resolvedMessages,
                  messages: built.forwardMessages,
                });
              }
              const result = await sendQqForwardMessages({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                targetKind: target.targetKind,
                targetId: target.targetId,
                messages: built.forwardMessages,
              });
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                requester_qq: built.requesterQq,
                bot_qq: built.botQq,
                message_count: built.forwardMessages.length,
                resolved_messages: built.resolvedMessages,
                data: result.data ?? null,
                message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_send_fake_message" },
    );

    api.registerTool(
      ((ctx) =>
        ({
          name: "chinobot_create_fake_dialogue",
          label: "ChinoBot Create Fake Dialogue",
          description:
            "Send chino_bot-style formatted fake dialogue text to the current QQ conversation. Speakers can be 触发者, 机器人, or current-group member nicknames/cards. If target is omitted, use the current QQ conversation.",
          parameters: ChinoBotQqFakeDialogueSchema,
          async execute(_toolCallId, rawParams) {
            const params = (rawParams ?? {}) as {
              messages?: string;
              target?: string;
              dry_run?: boolean;
            };
            const messages = params.messages?.trim();
            if (!messages) {
              return jsonText({ ok: false, error: "messages required" });
            }
            try {
              const target = await resolveQqMessageTarget({
                api,
                ctx,
                explicitTarget: params.target,
              });
              const built = await buildFakeDialogueLines({
                api,
                accountId: target.accountId,
                targetKind: target.targetKind,
                targetId: target.targetId,
                messages,
                userQq: await resolveRequesterUserIdFromContext({
                  api,
                  ctx,
                }),
              });
              const dialogueLines = built.lines;
              const dialogueText =
                "━━━━━━━━━━━━━━━━\n" +
                "📱 对话记录\n" +
                "━━━━━━━━━━━━━━━━\n\n" +
                dialogueLines.join("\n\n") +
                "\n\n━━━━━━━━━━━━━━━━";
              if (params.dry_run === true) {
                return jsonText({
                  ok: true,
                  dry_run: true,
                  source: target.source,
                  target_kind: target.targetKind,
                  target_id: target.targetId,
                  account_id: target.accountId ?? null,
                  requester_qq: built.requesterQq,
                  bot_qq: built.botQq,
                  line_count: dialogueLines.length,
                  text: dialogueText,
                });
              }
              const result = await sendQqText({
                cfg: api.config as CoreConfig,
                accountId: target.accountId,
                targetKind: target.targetKind,
                targetId: target.targetId,
                text: dialogueText,
              });
              return jsonText({
                ok: result.status === "ok" || result.retcode === 0,
                source: target.source,
                target_kind: target.targetKind,
                target_id: target.targetId,
                account_id: target.accountId ?? null,
                requester_qq: built.requesterQq,
                bot_qq: built.botQq,
                line_count: dialogueLines.length,
                text: dialogueText,
                data: result.data ?? null,
                message_id: (result.data as Record<string, unknown> | undefined)?.message_id ?? null,
              });
            } catch (error) {
              const message = error instanceof Error ? error.message : String(error);
              return jsonText({ ok: false, error: message });
            }
          },
        }) as AnyAgentTool) as never,
      { name: "chinobot_create_fake_dialogue" },
    );
  },
};

export default plugin;
