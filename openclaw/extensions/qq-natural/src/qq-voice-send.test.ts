import { describe, expect, it, vi } from "vitest";

vi.mock("node:child_process", () => ({
  execFile: (file: string, args: string[], cb: (error: Error | null) => void) => cb(null),
  spawn: vi.fn(),
}));

vi.mock("../../../dist/plugin-sdk/http-registry-7Lsnrxx9.js", () => ({
  h: vi.fn(async () => undefined),
  m: vi.fn((_type: string, _action: string, _sessionKey: string, context: Record<string, unknown>) => context),
}));

describe("qq voice send", () => {
  it("exports voice send testing helpers", async () => {
    const service = await import("./service.js");
    expect(typeof service.__testing.sendQqVoice).toBe("function");
    expect(typeof service.__testing.convertAudioToNapcatSilk).toBe("function");
  });
});
