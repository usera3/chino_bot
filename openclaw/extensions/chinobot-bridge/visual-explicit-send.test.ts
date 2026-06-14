import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockExecFile = vi.fn();
const mockExecFileAsync = vi.fn();
const mockSendQqMedia = vi.fn();
const mockRememberSentQqMedia = vi.fn();

vi.mock("node:child_process", () => ({
  execFile: mockExecFile,
}));

vi.mock("node:util", async () => {
  const actual = await vi.importActual<typeof import("node:util")>("node:util");
  return {
    ...actual,
    promisify(fn: unknown) {
      if (fn === mockExecFile) {
        return mockExecFileAsync;
      }
      return actual.promisify(fn as never);
    },
  };
});

vi.mock("../qq-natural/src/service.js", () => ({
  buildRecallTrackingKey: vi.fn(),
  getQqGroupMembers: vi.fn(),
  getQqGroupRootFiles: vi.fn(),
  getQqGroupFilesByFolder: vi.fn(),
  getQqGroupFileUrl: vi.fn(),
  getQqFile: vi.fn(),
  getQqGroupInfo: vi.fn(),
  getQqLoginInfo: vi.fn(),
  getQqPacketStatus: vi.fn(),
  getQqUserInfo: vi.fn(),
  recallRecentQqMessages: vi.fn(),
  rememberSentQqMedia: mockRememberSentQqMedia,
  resolveQqConversationMemeBaseImage: vi.fn(),
  sendQqForwardMessages: vi.fn(),
  sendQqMedia: mockSendQqMedia,
  sendQqText: vi.fn(),
  sendQqSegments: vi.fn(),
  sendQqVoice: vi.fn(),
  sendQqLike: vi.fn(),
  uploadQqGroupFile: vi.fn(),
}));

vi.mock("../qq-natural/src/meme.js", () => ({
  runQqMakeMeme: vi.fn(),
}));

describe("chinobot visual explicit send", () => {
  beforeEach(() => {
    mockExecFile.mockReset();
    mockExecFileAsync.mockReset();
    mockSendQqMedia.mockReset();
    mockRememberSentQqMedia.mockReset();
  });

  it("explicitly sends render_html output into the current QQ session", async () => {
    const sessionStorePath = path.join(
      os.tmpdir(),
      `chinobot-bridge-session-${Date.now()}-${Math.random().toString(36).slice(2)}.json`,
    );
    await fs.writeFile(
      sessionStorePath,
      JSON.stringify(
        {
          "agent:main:qq:group:673105016": {
            deliveryContext: {
              channel: "qq",
              to: "qq:group:673105016",
              accountId: "default",
            },
          },
        },
        null,
        2,
      ),
      "utf8",
    );

    mockExecFileAsync.mockResolvedValue({
      stdout: JSON.stringify({
        ok: true,
        result: {
          ok: true,
          file_path: "/tmp/render-test.png",
          media_url: "http://127.0.0.1:18789/__openclaw__/canvas/qq-media/render-test.png",
          width: 900,
          height: 520,
        },
      }),
      stderr: "",
    });
    mockSendQqMedia.mockResolvedValue({
      status: "ok",
      retcode: 0,
      data: { message_id: 24680 },
    });

    const { default: plugin } = await import("./index.js");
    const toolFactories = new Map<
      string,
      (ctx: unknown) => { execute: (...args: unknown[]) => Promise<unknown> }
    >();

    const api = {
      config: {},
      pluginConfig: {},
      logger: { warn: vi.fn() },
      resolvePath(input: string) {
        return input;
      },
      runtime: {
        channel: {
          session: {
            resolveStorePath() {
              return sessionStorePath;
            },
          },
        },
      },
      registerTool(toolOrFactory: unknown, meta?: { name?: string }) {
        if (meta?.name && typeof toolOrFactory === "function") {
          toolFactories.set(meta.name, toolOrFactory as never);
        }
      },
    };

    plugin.register(api as never);

    const tool = toolFactories.get("chinobot_render_html")?.({
      agentId: "main",
      sessionKey: "agent:main:qq:group:673105016",
      messageChannel: "qq",
      agentAccountId: "default",
    });

    const result = await tool?.execute("call-render", {
      html_code: "<div>hi</div>",
      width: 900,
      height: 520,
    });

    const text = String(
      ((result as { content?: Array<{ text?: string }> }).content ?? [])[0]?.text ?? "",
    );
    const payload = JSON.parse(text) as {
      ok: boolean;
      delivery_mode: string;
      target_kind: string;
      target_id: string;
      generated_local_path: string | null;
      generated_media_proxy_url: string | null;
      sent_media_ref: string;
      message_id: number | null;
      media_url?: unknown;
      file_path?: unknown;
    };

    expect(mockSendQqMedia).toHaveBeenCalledTimes(1);
    expect(mockSendQqMedia.mock.calls[0]?.[0]).toMatchObject({
      targetKind: "group",
      targetId: "673105016",
      mediaUrl: "/tmp/render-test.png",
    });
    expect(mockRememberSentQqMedia).toHaveBeenCalledTimes(1);
    expect(payload.ok).toBe(true);
    expect(payload.delivery_mode).toBe("explicit_qq_media_send");
    expect(payload.target_kind).toBe("group");
    expect(payload.target_id).toBe("673105016");
    expect(payload.generated_local_path).toBe("/tmp/render-test.png");
    expect(payload.generated_media_proxy_url).toBe(
      "http://127.0.0.1:18789/__openclaw__/canvas/qq-media/render-test.png",
    );
    expect(payload.sent_media_ref).toBe("/tmp/render-test.png");
    expect(payload.message_id).toBe(24680);
    expect(payload.media_url).toBeUndefined();
    expect(payload.file_path).toBeUndefined();
  });

  it("retries render_html once before failing the tool", async () => {
    const sessionStorePath = path.join(
      os.tmpdir(),
      `chinobot-bridge-session-${Date.now()}-${Math.random().toString(36).slice(2)}.json`,
    );
    await fs.writeFile(
      sessionStorePath,
      JSON.stringify(
        {
          "agent:main:qq:group:673105016": {
            deliveryContext: {
              channel: "qq",
              to: "qq:group:673105016",
              accountId: "default",
            },
          },
        },
        null,
        2,
      ),
      "utf8",
    );

    mockExecFileAsync
      .mockRejectedValueOnce(
        Object.assign(new Error("bridge failed"), {
          stderr: "Traceback: renderer busy",
          stdout: "",
        }),
      )
      .mockResolvedValueOnce({
        stdout: JSON.stringify({
          ok: true,
          result: {
            ok: true,
            file_path: "/tmp/render-retry-test.png",
            media_url: "http://127.0.0.1:18789/__openclaw__/canvas/qq-media/render-retry-test.png",
          },
        }),
        stderr: "",
      });
    mockSendQqMedia.mockResolvedValue({
      status: "ok",
      retcode: 0,
      data: { message_id: 24681 },
    });

    const { default: plugin } = await import("./index.js");
    const toolFactories = new Map<
      string,
      (ctx: unknown) => { execute: (...args: unknown[]) => Promise<unknown> }
    >();
    const warn = vi.fn();
    const api = {
      config: {},
      pluginConfig: {},
      logger: { warn },
      resolvePath(input: string) {
        return input;
      },
      runtime: {
        channel: {
          session: {
            resolveStorePath() {
              return sessionStorePath;
            },
          },
        },
      },
      registerTool(toolOrFactory: unknown, meta?: { name?: string }) {
        if (meta?.name && typeof toolOrFactory === "function") {
          toolFactories.set(meta.name, toolOrFactory as never);
        }
      },
    };

    plugin.register(api as never);

    const tool = toolFactories.get("chinobot_render_html")?.({
      agentId: "main",
      sessionKey: "agent:main:qq:group:673105016",
      messageChannel: "qq",
      agentAccountId: "default",
    });

    const result = await tool?.execute("call-render-retry", {
      html_code: "<div>retry</div>",
      width: 900,
      height: 520,
    });

    const text = String(
      ((result as { content?: Array<{ text?: string }> }).content ?? [])[0]?.text ?? "",
    );

    expect(mockExecFileAsync).toHaveBeenCalledTimes(2);
    expect(mockSendQqMedia).toHaveBeenCalledTimes(1);
    expect(text).toContain("\"ok\": true");
    expect(warn).toHaveBeenCalledTimes(1);
  });

  it("includes stderr details when render_html fails", async () => {
    mockExecFileAsync.mockRejectedValue(
      Object.assign(new Error("bridge failed"), {
        stderr: "Traceback: chromium target closed",
        stdout: "partial stdout",
      }),
    );

    const { default: plugin } = await import("./index.js");
    const toolFactories = new Map<
      string,
      (ctx: unknown) => { execute: (...args: unknown[]) => Promise<unknown> }
    >();
    const warn = vi.fn();
    const api = {
      config: {},
      pluginConfig: {},
      logger: { warn },
      resolvePath(input: string) {
        return input;
      },
      runtime: {
        channel: {
          session: {
            resolveStorePath() {
              return "/tmp/chinobot-bridge-render-error.json";
            },
          },
        },
      },
      registerTool(toolOrFactory: unknown, meta?: { name?: string }) {
        if (meta?.name && typeof toolOrFactory === "function") {
          toolFactories.set(meta.name, toolOrFactory as never);
        }
      },
    };

    plugin.register(api as never);

    const tool = toolFactories.get("chinobot_render_html")?.({
      agentId: "main",
      sessionKey: "agent:main:qq:group:673105016",
      messageChannel: "qq",
      agentAccountId: "default",
    });

    const result = await tool?.execute("call-render-error", {
      html_code: "<div>fail</div>",
      width: 900,
      height: 520,
    });

    const text = String(
      ((result as { content?: Array<{ text?: string }> }).content ?? [])[0]?.text ?? "",
    );

    expect(mockExecFileAsync).toHaveBeenCalledTimes(2);
    expect(text).toContain("stderr:");
    expect(text).toContain("chromium target closed");
    expect(text).toContain("stdout:");
    expect(warn).toHaveBeenCalledTimes(1);
  });
});
