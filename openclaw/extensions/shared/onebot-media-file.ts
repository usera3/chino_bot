import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const FILE_URL_RE = /^file:\/\//i;
const EXTERNAL_MEDIA_RE = /^(?:[a-z][a-z0-9+.-]*:\/\/|data:)/i;
const WINDOWS_DRIVE_RE = /^[a-zA-Z]:[\\/]/;
const HAS_FILE_EXT_RE = /\.\w{1,10}$/;
const QQ_MEDIA_PROXY_DIR = path.join(os.homedir(), ".openclaw", "canvas", "qq-media");
const QQ_MEDIA_PROXY_PATH = "/__openclaw__/canvas/qq-media";

function expandHomePath(input: string): string {
  if (input === "~") {
    return os.homedir();
  }
  if (input.startsWith("~/") || input.startsWith("~\\")) {
    return path.join(os.homedir(), input.slice(2));
  }
  return input;
}

export function normalizeOneBotMediaFile(mediaUrl: string): string {
  const trimmed = mediaUrl.trim();
  if (!trimmed) {
    return trimmed;
  }

  if (FILE_URL_RE.test(trimmed)) {
    try {
      return fileURLToPath(trimmed);
    } catch {
      return trimmed;
    }
  }

  if (EXTERNAL_MEDIA_RE.test(trimmed)) {
    return trimmed;
  }

  const expanded = expandHomePath(trimmed);
  if (!path.isAbsolute(expanded)) {
    return trimmed;
  }

  return expanded;
}

function looksLikeLocalMediaPath(input: string): boolean {
  return (
    FILE_URL_RE.test(input) ||
    path.isAbsolute(input) ||
    input.startsWith("./") ||
    input.startsWith("../") ||
    input.startsWith("~") ||
    WINDOWS_DRIVE_RE.test(input) ||
    input.startsWith("\\\\") ||
    (!EXTERNAL_MEDIA_RE.test(input) && (input.includes("/") || input.includes("\\") || HAS_FILE_EXT_RE.test(input)))
  );
}

function resolveGatewayPort(gatewayPort?: number): number {
  return typeof gatewayPort === "number" && Number.isFinite(gatewayPort) ? gatewayPort : 18789;
}

export async function resolveQqHttpMediaUrl(params: {
  mediaUrl: string;
  gatewayPort?: number;
}): Promise<string> {
  const normalized = normalizeOneBotMediaFile(params.mediaUrl);
  const trimmed = normalized.trim();
  if (!trimmed || (EXTERNAL_MEDIA_RE.test(trimmed) && !FILE_URL_RE.test(trimmed))) {
    return trimmed;
  }

  if (!looksLikeLocalMediaPath(trimmed)) {
    return trimmed;
  }

  const expanded = expandHomePath(trimmed);
  const filePath = FILE_URL_RE.test(expanded) ? normalizeOneBotMediaFile(expanded) : expanded;
  if (!path.isAbsolute(filePath)) {
    return trimmed;
  }

  try {
    const stat = await fs.stat(filePath);
    if (!stat.isFile()) {
      return trimmed;
    }
    await fs.mkdir(QQ_MEDIA_PROXY_DIR, { recursive: true });
    const ext = path.extname(filePath) || ".bin";
    const outputName = `qq-media-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`;
    const targetPath = path.join(QQ_MEDIA_PROXY_DIR, outputName);
    await fs.copyFile(filePath, targetPath);
    return `http://127.0.0.1:${resolveGatewayPort(params.gatewayPort)}${QQ_MEDIA_PROXY_PATH}/${encodeURIComponent(outputName)}`;
  } catch {
    return trimmed;
  }
}
