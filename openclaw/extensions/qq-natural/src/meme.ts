import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import type { CoreConfig } from "./types.js";

import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const sharp = require("sharp") as typeof import("sharp");

const MEME_OUTPUT_DIR = path.join(os.tmpdir(), "openclaw-qq-memes");
const QQ_MEDIA_PROXY_DIR = path.join(os.homedir(), ".openclaw", "canvas", "qq-media");
const QQ_MEDIA_PROXY_PATH = "/__openclaw__/canvas/qq-media";
const QQ_MEME_SMART_MAX_DIMENSION = 3072;
const QQ_MEME_SMART_MAX_PIXELS = 9_000_000;

function resolveWorkspaceDir(cfg: CoreConfig): string | null {
  const workspace = (cfg as { agents?: { defaults?: { workspace?: string } } }).agents?.defaults
    ?.workspace;
  return typeof workspace === "string" && workspace.trim() ? workspace.trim() : null;
}

function resolveLocalPath(input: string, cfg: CoreConfig): string {
  const trimmed = input.trim();
  if (!trimmed) {
    return trimmed;
  }
  if (path.isAbsolute(trimmed)) {
    return trimmed;
  }
  const workspaceDir = resolveWorkspaceDir(cfg);
  if (workspaceDir && path.isAbsolute(workspaceDir)) {
    return path.join(workspaceDir, trimmed);
  }
  return path.resolve(trimmed);
}

function resolveGatewayPort(cfg: CoreConfig): number {
  return typeof (cfg as { gateway?: { port?: number } }).gateway?.port === "number" &&
    Number.isFinite((cfg as { gateway?: { port?: number } }).gateway?.port)
    ? ((cfg as { gateway?: { port?: number } }).gateway?.port as number)
    : 18789;
}

async function publishQqMediaProxyUrl(params: {
  cfg: CoreConfig;
  sourceFilePath: string;
  prefix: string;
}) {
  const ext = path.extname(params.sourceFilePath) || ".png";
  const outputName = `${params.prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`;
  const targetPath = path.join(QQ_MEDIA_PROXY_DIR, outputName);
  await fs.mkdir(QQ_MEDIA_PROXY_DIR, { recursive: true });
  await fs.copyFile(params.sourceFilePath, targetPath);
  return `http://127.0.0.1:${resolveGatewayPort(params.cfg)}${QQ_MEDIA_PROXY_PATH}/${encodeURIComponent(outputName)}`;
}

function escapeXml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function measureTextUnits(text: string) {
  let total = 0;
  for (const char of text) {
    total += /[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/u.test(char) ? 1 : 0.55;
  }
  return total;
}

function wrapMemeText(text: string, maxUnits: number) {
  const raw = text.replace(/\s+/gu, " ").trim();
  if (!raw) {
    return [];
  }
  const tokens = raw.split(/(\s+)/u).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const token of tokens) {
    const next = `${current}${token}`;
    if (current && measureTextUnits(next) > maxUnits) {
      lines.push(current.trim());
      current = token.trimStart();
      continue;
    }
    current = next;
  }
  if (current.trim()) {
    lines.push(current.trim());
  }
  if (lines.length === 1 && measureTextUnits(lines[0] ?? "") > maxUnits) {
    const hardLines: string[] = [];
    let chunk = "";
    for (const char of raw) {
      const next = `${chunk}${char}`;
      if (chunk && measureTextUnits(next) > maxUnits) {
        hardLines.push(chunk.trim());
        chunk = char;
        continue;
      }
      chunk = next;
    }
    if (chunk.trim()) {
      hardLines.push(chunk.trim());
    }
    return hardLines;
  }
  return lines;
}

function renderTextBlock(params: {
  lines: string[];
  x: string;
  y: number;
  lineHeight: number;
  textStyle: string;
}) {
  if (params.lines.length === 0) {
    return "";
  }
  const tspans = params.lines
    .map((line, index) => {
      const dy = index === 0 ? 0 : params.lineHeight;
      return `<tspan x="${params.x}" dy="${dy}">${escapeXml(line)}</tspan>`;
    })
    .join("");
  return `<text x="${params.x}" y="${params.y}" style="${params.textStyle}">${tspans}</text>`;
}

function buildMemeOverlaySvg(params: {
  width: number;
  height: number;
  topText?: string;
  bottomText?: string;
  centerText?: string;
}) {
  const topText = params.topText?.trim() ?? "";
  const bottomText = params.bottomText?.trim() ?? "";
  const centerText = params.centerText?.trim() ?? "";
  const fontSize = Math.max(28, Math.round(params.width / 10));
  const strokeWidth = Math.max(3, Math.round(fontSize / 8));
  const lineHeight = Math.round(fontSize * 1.08);
  const maxUnits = Math.max(6, Math.floor(params.width / (fontSize * 0.62)));
  const textStyle = [
    "font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif",
    `font-size: ${fontSize}px`,
    "font-weight: 900",
    "fill: white",
    "stroke: black",
    `stroke-width: ${strokeWidth}px`,
    "paint-order: stroke",
    "text-anchor: middle",
  ].join("; ");
  const topLines = wrapMemeText(topText, maxUnits);
  const bottomLines = wrapMemeText(bottomText, maxUnits);
  const centerLines = wrapMemeText(centerText, maxUnits);
  const centerBlockHeight = centerLines.length > 0 ? (centerLines.length - 1) * lineHeight : 0;
  const centerY = Math.round(params.height / 2 - centerBlockHeight / 2);
  const blocks = [
    topLines.length > 0
      ? renderTextBlock({
          lines: topLines,
          x: "50%",
          y: fontSize + 20,
          lineHeight,
          textStyle,
        })
      : "",
    centerLines.length > 0
      ? renderTextBlock({
          lines: centerLines,
          x: "50%",
          y: centerY,
          lineHeight,
          textStyle,
        })
      : "",
    bottomLines.length > 0
      ? renderTextBlock({
          lines: bottomLines,
          x: "50%",
          y: params.height - 24 - (bottomLines.length - 1) * lineHeight,
          lineHeight,
          textStyle,
        })
      : "",
  ].filter(Boolean);
  return Buffer.from(
    [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${params.width}" height="${params.height}">`,
      ...blocks,
      "</svg>",
    ].join(""),
    "utf8",
  );
}

async function loadMemeBaseImage(params: {
  cfg: CoreConfig;
  image_url?: string;
  image_path?: string;
}) {
  if (params.image_path?.trim()) {
    return await fs.readFile(resolveLocalPath(params.image_path.trim(), params.cfg));
  }
  if (params.image_url?.trim()) {
    const response = await fetch(params.image_url.trim());
    if (!response.ok) {
      throw new Error(`下载表情包底图失败: HTTP ${response.status}`);
    }
    const arrayBuffer = await response.arrayBuffer();
    return Buffer.from(arrayBuffer);
  }
  return null;
}

function resolveMemeResizePlan(params: {
  width: number;
  height: number;
  preserveOriginalSize?: boolean;
  maxWidth?: number;
  maxHeight?: number;
}) {
  const width = Math.max(1, Math.round(params.width));
  const height = Math.max(1, Math.round(params.height));
  const maxWidth =
    typeof params.maxWidth === "number" && Number.isFinite(params.maxWidth) && params.maxWidth > 0
      ? Math.round(params.maxWidth)
      : undefined;
  const maxHeight =
    typeof params.maxHeight === "number" && Number.isFinite(params.maxHeight) && params.maxHeight > 0
      ? Math.round(params.maxHeight)
      : undefined;

  let scale = 1;
  let reason = "preserve-original";

  if (maxWidth || maxHeight) {
    const widthScale = maxWidth ? maxWidth / width : 1;
    const heightScale = maxHeight ? maxHeight / height : 1;
    scale = Math.min(1, widthScale, heightScale);
    reason = "explicit-max-bounds";
  } else if (params.preserveOriginalSize === false) {
    const widthScale = 768 / width;
    scale = Math.min(1, widthScale);
    reason = "legacy-default";
  } else {
    const dimensionScale = Math.min(
      1,
      QQ_MEME_SMART_MAX_DIMENSION / width,
      QQ_MEME_SMART_MAX_DIMENSION / height,
    );
    const pixelScale = Math.min(1, Math.sqrt(QQ_MEME_SMART_MAX_PIXELS / (width * height)));
    scale = Math.min(dimensionScale, pixelScale);
    reason = scale < 1 ? "smart-downscale" : "preserve-original";
  }

  if (!(scale < 1)) {
    return {
      shouldResize: false,
      width,
      height,
      reason,
    };
  }

  return {
    shouldResize: true,
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
    reason,
  };
}

export async function runQqMakeMeme(
  params: {
    image_url?: string;
    image_path?: string;
    top_text?: string;
    bottom_text?: string;
    center_text?: string;
    text?: string;
    caption?: string;
    preserve_original_size?: boolean;
    max_width?: number;
    max_height?: number;
  },
  cfg: CoreConfig,
) {
  const topText = params.top_text?.trim() ?? "";
  const bottomText = params.bottom_text?.trim() ?? "";
  const centerText = params.center_text?.trim() ?? "";
  const singleText = params.text?.trim() ?? "";
  const effectiveBottom = bottomText || (!topText && !centerText ? singleText : "");
  const effectiveCenter = centerText || (topText || bottomText ? singleText : "");
  if (!topText && !effectiveBottom && !effectiveCenter) {
    return { ok: false, error: "至少要提供 text、top_text、bottom_text 或 center_text" };
  }

  const baseBuffer = await loadMemeBaseImage({
    cfg,
    image_url: params.image_url,
    image_path: params.image_path,
  });
  const baseImage = baseBuffer
    ? sharp(baseBuffer)
    : sharp({
        create: {
          width: 768,
          height: 768,
          channels: 4,
          background: { r: 35, g: 35, b: 35, alpha: 1 },
        },
      });
  const baseMetadata = await baseImage.metadata();
  const originalWidth = baseMetadata.width ?? 768;
  const originalHeight = baseMetadata.height ?? 768;
  const resizePlan = resolveMemeResizePlan({
    width: originalWidth,
    height: originalHeight,
    preserveOriginalSize: params.preserve_original_size,
    maxWidth: params.max_width,
    maxHeight: params.max_height,
  });
  const preparedImage = resizePlan.shouldResize
    ? baseImage.resize({
        width: resizePlan.width,
        height: resizePlan.height,
        fit: "inside",
        withoutEnlargement: true,
      })
    : baseImage;
  const prepared = await preparedImage.png().toBuffer({ resolveWithObject: true });
  const width = prepared.info.width ?? 768;
  const height = prepared.info.height ?? 768;
  const overlay = buildMemeOverlaySvg({
    width,
    height,
    topText,
    bottomText: effectiveBottom,
    centerText: effectiveCenter,
  });

  await fs.mkdir(MEME_OUTPUT_DIR, { recursive: true });
  const filePath = path.join(
    MEME_OUTPUT_DIR,
    `meme-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.png`,
  );
  await sharp(prepared.data)
    .composite([{ input: overlay, top: 0, left: 0 }])
    .png()
    .toFile(filePath);
  const mediaUrl = await publishQqMediaProxyUrl({
    cfg,
    sourceFilePath: filePath,
    prefix: "meme",
  });

  return {
    ok: true,
    media_url: mediaUrl,
    mediaUrl,
    primary_media_url: mediaUrl,
    primaryMediaUrl: mediaUrl,
    file_path: filePath,
    image_size: {
      original_width: originalWidth,
      original_height: originalHeight,
      output_width: width,
      output_height: height,
      resized: resizePlan.shouldResize,
      resize_reason: resizePlan.reason,
    },
    caption: params.caption?.trim() ?? "",
    note: "图片会由系统自动发送，请不要重复输出链接、文件路径或 [[media:...]]",
  };
}
