import { beforeEach, describe, expect, it, vi } from "vitest";

const mockSendQqSegments = vi.fn();
const mockUploadQqGroupFile = vi.fn();
const mockResolveQqHttpMediaUrl = vi.fn();

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
  rememberSentQqMedia: vi.fn(),
  resolveQqConversationMemeBaseImage: vi.fn(),
  sendQqForwardMessages: vi.fn(),
  sendQqMedia: vi.fn(),
  sendQqText: vi.fn(),
  sendQqSegments: mockSendQqSegments,
  sendQqVoice: vi.fn(),
  sendQqLike: vi.fn(),
  uploadQqGroupFile: mockUploadQqGroupFile,
}));

vi.mock("../shared/onebot-media-file.js", () => ({
  resolveQqHttpMediaUrl: mockResolveQqHttpMediaUrl,
}));

describe("chinobot send file fallback", () => {
  beforeEach(() => {
    mockSendQqSegments.mockReset();
    mockUploadQqGroupFile.mockReset();
    mockResolveQqHttpMediaUrl.mockReset();
    mockResolveQqHttpMediaUrl.mockImplementation(async ({ mediaUrl }: { mediaUrl: string }) => {
      const encoded = encodeURIComponent(mediaUrl);
      return `http://127.0.0.1:18789/__openclaw__/canvas/qq-media/${encoded}`;
    });
  });

  it("falls back to QQ group file upload after rich media send failures", async () => {
    mockSendQqSegments.mockResolvedValue({
      status: "failed",
      retcode: 1200,
      message: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
      wording: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
      data: null,
    });
    mockUploadQqGroupFile.mockResolvedValue({
      status: "ok",
      retcode: 0,
      data: { file_id: "uploaded-1" },
    });

    const { default: plugin } = await import("./index.js");
    const toolFactories = new Map<string, (ctx: unknown) => { execute: (...args: unknown[]) => Promise<unknown> }>();

    const api = {
      config: {},
      pluginConfig: {},
      resolvePath(input: string) {
        return input;
      },
      registerTool(toolOrFactory: unknown, meta?: { name?: string }) {
        if (meta?.name && typeof toolOrFactory === "function") {
          toolFactories.set(meta.name, toolOrFactory as never);
        }
      },
    };

    plugin.register(api as never);

    const tool = toolFactories.get("chinobot_send_file")?.({
      agentId: "main",
      sessionKey: "agent:main:test",
      messageChannel: "qq",
      agentAccountId: "default",
    });

    const result = await tool?.execute("call-1", {
      file_path: "/Users/mozi100/PycharmProjects/openclaw/package.json",
      target: "group:673105016",
      name: "package.json",
    });

    const text = String(
      ((result as { content?: Array<{ text?: string }> }).content ?? [])[0]?.text ?? "",
    );
    const payload = JSON.parse(text) as {
      ok: boolean;
      delivery_mode: string;
      attempts: Array<{ source: string; retcode: number | null }>;
      fallback: {
        mode: string;
        ok: boolean;
        upload_source: string;
        attempts: Array<{ source: string; upload_file: boolean | null }>;
        data?: { file_id?: string };
      };
    };

    expect(mockSendQqSegments).toHaveBeenCalledTimes(3);
    expect(mockUploadQqGroupFile).toHaveBeenCalledTimes(1);
    expect(payload.ok).toBe(true);
    expect(payload.delivery_mode).toBe("group_file_upload_fallback");
    expect(payload.attempts.map((entry) => entry.source)).toEqual(["file_url", "local_path", "proxy_url"]);
    expect(payload.fallback.mode).toBe("group_file_upload");
    expect(payload.fallback.ok).toBe(true);
    expect(payload.fallback.upload_source).toBe("local_path");
    expect(payload.fallback.attempts.map((entry) => `${entry.source}:${String(entry.upload_file)}`)).toEqual([
      "local_path:null",
    ]);
    expect(payload.fallback.data?.file_id).toBe("uploaded-1");
  });

  it("uses proxy_url delivery before falling back to group upload", async () => {
    mockSendQqSegments
      .mockResolvedValueOnce({
        status: "failed",
        retcode: 1200,
        message: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        wording: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        data: null,
      })
      .mockResolvedValueOnce({
        status: "failed",
        retcode: 1200,
        message: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        wording: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        data: null,
      })
      .mockResolvedValueOnce({
        status: "ok",
        retcode: 0,
        data: { message_id: 42 },
      });

    const { default: plugin } = await import("./index.js");
    const toolFactories = new Map<string, (ctx: unknown) => { execute: (...args: unknown[]) => Promise<unknown> }>();

    const api = {
      config: {},
      pluginConfig: {},
      resolvePath(input: string) {
        return input;
      },
      registerTool(toolOrFactory: unknown, meta?: { name?: string }) {
        if (meta?.name && typeof toolOrFactory === "function") {
          toolFactories.set(meta.name, toolOrFactory as never);
        }
      },
    };

    plugin.register(api as never);

    const tool = toolFactories.get("chinobot_send_file")?.({
      agentId: "main",
      sessionKey: "agent:main:test",
      messageChannel: "qq",
      agentAccountId: "default",
    });

    const result = await tool?.execute("call-2", {
      file_path: "/Users/mozi100/PycharmProjects/openclaw/package.json",
      target: "group:673105016",
      name: "package.json",
    });

    const text = String(
      ((result as { content?: Array<{ text?: string }> }).content ?? [])[0]?.text ?? "",
    );
    const payload = JSON.parse(text) as {
      ok: boolean;
      delivery_mode: string;
      file_ref_source: string;
      attempts: Array<{ source: string }>;
      message_id: number | null;
    };

    expect(payload.ok).toBe(true);
    expect(payload.delivery_mode).toBe("message_file");
    expect(payload.file_ref_source).toBe("proxy_url");
    expect(payload.attempts.map((entry) => entry.source)).toEqual(["file_url", "local_path", "proxy_url"]);
    expect(payload.message_id).toBe(42);
    expect(mockUploadQqGroupFile).not.toHaveBeenCalled();
  });

  it("retries chinobot_upload_group_file with relaxed and proxy fallbacks", async () => {
    mockUploadQqGroupFile
      .mockResolvedValueOnce({
        status: "failed",
        retcode: 1200,
        message: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        wording: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        data: null,
      })
      .mockResolvedValueOnce({
        status: "failed",
        retcode: 1200,
        message: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        wording: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        data: null,
      })
      .mockResolvedValueOnce({
        status: "failed",
        retcode: 1200,
        message: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        wording: 'EventChecker Failed: {"result":-1,"errMsg":"rich media transfer failed"}',
        data: null,
      })
      .mockResolvedValueOnce({
        status: "ok",
        retcode: 0,
        data: { file_id: "proxy-uploaded" },
      });

    const { default: plugin } = await import("./index.js");
    const toolFactories = new Map<string, (ctx: unknown) => { execute: (...args: unknown[]) => Promise<unknown> }>();

    const api = {
      config: {},
      pluginConfig: {},
      resolvePath(input: string) {
        return input;
      },
      registerTool(toolOrFactory: unknown, meta?: { name?: string }) {
        if (meta?.name && typeof toolOrFactory === "function") {
          toolFactories.set(meta.name, toolOrFactory as never);
        }
      },
    };

    plugin.register(api as never);

    const tool = toolFactories.get("chinobot_upload_group_file")?.({
      agentId: "main",
      sessionKey: "agent:main:test",
      messageChannel: "qq",
      agentAccountId: "default",
    });

    const result = await tool?.execute("call-3", {
      file_path: "/Users/mozi100/PycharmProjects/openclaw/package.json",
      group_id: "673105016",
      name: "package.json",
    });

    const text = String(
      ((result as { content?: Array<{ text?: string }> }).content ?? [])[0]?.text ?? "",
    );
    const payload = JSON.parse(text) as {
      ok: boolean;
      upload_source: string;
      upload_file: boolean | null;
      attempts: Array<{ source: string; upload_file: boolean | null }>;
      data?: { file_id?: string };
    };

    expect(payload.ok).toBe(true);
    expect(payload.upload_source).toBe("proxy_url");
    expect(payload.upload_file).toBe(false);
    expect(payload.attempts.map((entry) => `${entry.source}:${String(entry.upload_file)}`)).toEqual([
      "local_path:null",
      "local_path:false",
      "proxy_url:null",
      "proxy_url:false",
    ]);
    expect(payload.data?.file_id).toBe("proxy-uploaded");
  });
});
