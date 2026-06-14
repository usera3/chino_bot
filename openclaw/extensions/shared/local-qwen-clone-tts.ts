import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export const DEFAULT_LOCAL_QWEN_CLONE_TTS = {
  enabled: false,
  projectRoot: "../voice/qwen3-tts-apple-silicon",
  pythonPath: "python3",
  scriptPath: "../voice/qwen3-tts-apple-silicon/openclaw_clone_tts.py",
  modelPath: "../voice/qwen3-tts-apple-silicon/models/Qwen3-TTS-12Hz-1.7B-Base-8bit",
  voiceName: "akari2",
  timeoutMs: 120_000,
  fallbackToSystemSay: true,
} as const;

export type LocalQwenCloneTtsConfig = {
  enabled: boolean;
  projectRoot: string;
  pythonPath: string;
  scriptPath: string;
  modelPath: string;
  voiceName: string;
  timeoutMs: number;
  fallbackToSystemSay: boolean;
};

function readString(value: unknown, fallback: string) {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function readBoolean(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

function readTimeout(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) && value >= 1_000 ? value : fallback;
}

export function resolveLocalQwenCloneTtsConfig(raw: unknown): LocalQwenCloneTtsConfig {
  const record = raw && typeof raw === "object" && !Array.isArray(raw)
    ? (raw as Record<string, unknown>)
    : {};
  return {
    enabled: readBoolean(record.enabled, DEFAULT_LOCAL_QWEN_CLONE_TTS.enabled),
    projectRoot: readString(record.projectRoot, DEFAULT_LOCAL_QWEN_CLONE_TTS.projectRoot),
    pythonPath: readString(record.pythonPath, DEFAULT_LOCAL_QWEN_CLONE_TTS.pythonPath),
    scriptPath: readString(record.scriptPath, DEFAULT_LOCAL_QWEN_CLONE_TTS.scriptPath),
    modelPath: readString(record.modelPath, DEFAULT_LOCAL_QWEN_CLONE_TTS.modelPath),
    voiceName: readString(record.voiceName, DEFAULT_LOCAL_QWEN_CLONE_TTS.voiceName),
    timeoutMs: readTimeout(record.timeoutMs, DEFAULT_LOCAL_QWEN_CLONE_TTS.timeoutMs),
    fallbackToSystemSay: readBoolean(
      record.fallbackToSystemSay,
      DEFAULT_LOCAL_QWEN_CLONE_TTS.fallbackToSystemSay,
    ),
  };
}

export function parseLocalQwenCloneTtsStdout(stdout: string, fallbackPath: string) {
  const lastNonEmptyLine =
    stdout
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .at(-1) ?? "";
  return path.resolve(lastNonEmptyLine || fallbackPath);
}

export async function synthesizeLocalQwenCloneTts(params: {
  text: string;
  outputPath: string;
  config: LocalQwenCloneTtsConfig;
}) {
  const trimmed = params.text.trim();
  if (!trimmed) {
    throw new Error("text 不能为空");
  }
  const resolvedOutputPath = path.resolve(params.outputPath);
  await fs.mkdir(path.dirname(resolvedOutputPath), { recursive: true });
  const { stdout } = await execFileAsync(
    params.config.pythonPath,
    [
      params.config.scriptPath,
      "--text",
      trimmed,
      "--output-path",
      resolvedOutputPath,
      "--voice-name",
      params.config.voiceName,
      "--model-path",
      params.config.modelPath,
    ],
    {
      cwd: params.config.projectRoot,
      timeout: params.config.timeoutMs,
      maxBuffer: 8 * 1024 * 1024,
    },
  );
  const finalPath = parseLocalQwenCloneTtsStdout(stdout, resolvedOutputPath);
  await fs.access(finalPath);
  return finalPath;
}
