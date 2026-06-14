import { Type } from "@sinclair/typebox";
import { createRequire } from "node:module";
import { createWriteStream } from "node:fs";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import type { AnyAgentTool, OpenClawPluginApi } from "../../../dist/plugin-sdk/index.js";
import {
  buildRecallTrackingKey,
  getQqFile,
  getQqGroupFileUrl,
  getQqGroupFilesByFolder,
  getQqGroupInfo,
  getQqGroupMembers,
  getQqGroupRootFiles,
  getQqLoginInfo,
  getQqPacketStatus,
  getQqUserInfo,
  recallRecentQqMessages,
  sendQqLike,
  uploadQqGroupFile,
} from "./service.js";
import type { CoreConfig } from "./types.js";
import { resolveQqHttpMediaUrl, normalizeOneBotMediaFile } from "../../shared/onebot-media-file.js";

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

const QqUserInfoSchema = Type.Object({
  query_type: Type.Union([
    Type.Literal("self"),
    Type.Literal("user"),
    Type.Literal("group"),
  ]),
  target_id: Type.Optional(Type.String()),
});

const QqGroupMembersSchema = Type.Object({
  group_id: Type.String(),
});

const QqSendLikeSchema = Type.Object({
  user_id: Type.String(),
  times: Type.Optional(Type.Number({ minimum: 1, maximum: 10 })),
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
  content_type: Type.Optional(
    Type.Union([Type.Literal("plain"), Type.Literal("html")]),
  ),
});

const AMAP_BASE_URL = "https://restapi.amap.com/v3";

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

export function registerQqNativeTools(api: OpenClawPluginApi) {
  api.registerTool(
    {
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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
      name: "qq_group_file_info",
      label: "QQ Group File Info",
      description: "Get a QQ group file's metadata by listing its containing folder through the active QQ / NapCat connection.",
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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
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

          const proxyUrl = await resolveQqHttpMediaUrl({
            mediaUrl: resolvedPath,
            gatewayPort: cfg.gateway?.port,
          });
          if (!proxyUrl || proxyUrl === resolvedPath) {
            const last = attempts[attempts.length - 1] ?? null;
            return json({
              ok: false,
              group_id: groupId,
              folder_id: folderId ?? null,
              file_path: resolvedPath,
              upload_source: last?.source ?? "local_path",
              proxy_url: null,
              name,
              upload_file: typeof requestedUploadFile === "boolean" ? requestedUploadFile : null,
              attempts,
              error: primary.result.message ?? primary.result.wording ?? "upload failed",
            });
          }

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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
      name: "qq_user_info",
      label: "QQ User Info",
      description: "Get QQ self info, user info, or group info through the active QQ / NapCat connection.",
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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
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
    } as AnyAgentTool,
  );

  api.registerTool(
    {
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
    } as AnyAgentTool,
  );

  api.registerTool(
    ((ctx) =>
      ({
        name: "qq_recall_message",
        label: "QQ Recall Message",
        description: "Recall the most recent QQ messages sent by OpenClaw in the current conversation for the current sender.",
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

  api.registerTool(
    {
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
          return json(await runSearchNearby({
            location: params.location ?? "",
            keyword: params.keyword,
            type: params.type,
            city: params.city,
          }));
        } catch (err) {
          return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
        }
      },
    } as AnyAgentTool,
  );

  api.registerTool(
    {
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
          return json(await runSendEmail({
            receiver_email: params.receiver_email ?? "",
            subject: params.subject ?? "",
            content: params.content ?? "",
            content_type: params.content_type,
          }));
        } catch (err) {
          return json({ ok: false, error: err instanceof Error ? err.message : String(err) });
        }
      },
    } as AnyAgentTool,
  );
}
