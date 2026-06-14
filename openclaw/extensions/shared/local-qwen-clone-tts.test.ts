import { describe, expect, it } from "vitest";
import {
  DEFAULT_LOCAL_QWEN_CLONE_TTS,
  parseLocalQwenCloneTtsStdout,
  resolveLocalQwenCloneTtsConfig,
} from "./local-qwen-clone-tts.js";

describe("local qwen clone tts config", () => {
  it("uses defaults when config is missing", () => {
    expect(resolveLocalQwenCloneTtsConfig(undefined)).toEqual(DEFAULT_LOCAL_QWEN_CLONE_TTS);
  });

  it("merges provided fields", () => {
    const cfg = resolveLocalQwenCloneTtsConfig({
      enabled: true,
      voiceName: "line4",
      timeoutMs: 30_000,
      fallbackToSystemSay: false,
    });
    expect(cfg.enabled).toBe(true);
    expect(cfg.voiceName).toBe("line4");
    expect(cfg.timeoutMs).toBe(30_000);
    expect(cfg.fallbackToSystemSay).toBe(false);
    expect(cfg.projectRoot).toBe(DEFAULT_LOCAL_QWEN_CLONE_TTS.projectRoot);
  });

  it("extracts the last non-empty line from helper stdout as the final path", () => {
    const parsed = parseLocalQwenCloneTtsStdout(
      "Loaded speech tokenizer\nSegment 1/1: 100%\n/private/tmp/final-voice.wav\n",
      "/tmp/fallback.wav",
    );
    expect(parsed).toBe("/private/tmp/final-voice.wav");
  });
});
