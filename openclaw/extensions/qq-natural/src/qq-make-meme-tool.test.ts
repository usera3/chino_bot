import { beforeEach, describe, expect, it, vi } from "vitest";

const resolveQqConversationMemeBaseImage = vi.fn(() => ({
  imagePath: "/tmp/current-chat-image.jpg",
  imageUrl: undefined,
  source: "inbound",
  mediaId: "media-1",
  summary: "当前聊天图片",
}));

const runQqMakeMeme = vi.fn(async (params: Record<string, unknown>) => ({
  ok: true,
  mediaUrl: "http://127.0.0.1:18789/__openclaw__/canvas/qq-media/meme-test.png",
  primaryMediaUrl: "http://127.0.0.1:18789/__openclaw__/canvas/qq-media/meme-test.png",
  file_path: "/tmp/meme-test.png",
  echoed: params,
}));

vi.mock("./service.js", () => ({
  buildRecallTrackingKey: vi.fn(),
  debugInjectQqInboundMessage: vi.fn(),
  debugInjectQqInboundSequence: vi.fn(),
  getQqFile: vi.fn(),
  getQqGroupFileUrl: vi.fn(),
  getQqGroupFilesByFolder: vi.fn(),
  getQqGroupInfo: vi.fn(),
  getQqGroupMembers: vi.fn(),
  getQqGroupRootFiles: vi.fn(),
  getQqLoginInfo: vi.fn(),
  getQqPacketStatus: vi.fn(),
  getQqUserInfo: vi.fn(),
  rememberSentQqMedia: vi.fn(),
  recallRecentQqMessages: vi.fn(),
  resolveQqConversationMemeBaseImage,
  sendQqMedia: vi.fn(),
  sendQqSegments: vi.fn(),
  sendQqVoice: vi.fn(),
  sendQqLike: vi.fn(),
  uploadQqGroupFile: vi.fn(),
}));

vi.mock("./meme.js", () => ({
  runQqMakeMeme,
}));

describe("qq_make_meme tool", () => {
  beforeEach(() => {
    resolveQqConversationMemeBaseImage.mockClear();
    runQqMakeMeme.mockClear();
  });

  it("reuses the current conversation image when no explicit base image is provided", async () => {
    const { registerQqNativeTools } = await import("./tools.js");
    const tools = new Map<string, Record<string, unknown>>();
    const api = {
      config: {
        agents: {
          defaults: {
            workspace: "/Users/mozi100/PycharmProjects/openclaw",
          },
        },
        gateway: {
          port: 18789,
        },
      },
      resolvePath(input: string) {
        return input;
      },
      runtime: {
        channel: {
          session: {
            resolveStorePath() {
              return "/tmp/openclaw-test-session-store.json";
            },
          },
        },
      },
      registerTool(toolOrFactory: unknown) {
        const ctx = {
          agentId: "fusion-main",
          sessionKey: "agent:fusion-main:qq:group:673105016",
          messageChannel: "qq",
          agentAccountId: "default",
          requesterSenderId: "1446437177",
        };
        const tool =
          typeof toolOrFactory === "function" ? toolOrFactory(ctx) : (toolOrFactory as Record<string, unknown>);
        tools.set(String(tool.name), tool);
      },
    };

    const sessionStore = {
      "agent:fusion-main:qq:group:673105016": {
        deliveryContext: {
          channel: "qq",
          to: "qq:group:673105016",
          accountId: "default",
        },
        lastChannel: "qq",
        lastTo: "qq:group:673105016",
        lastAccountId: "default",
      },
    };
    const fs = await import("node:fs/promises");
    await fs.writeFile("/tmp/openclaw-test-session-store.json", JSON.stringify(sessionStore), "utf8");

    registerQqNativeTools(api as never);
    const tool = tools.get("qq_make_meme");
    expect(tool).toBeTruthy();

    const result = await (tool?.execute as (...args: unknown[]) => Promise<{ details: Record<string, unknown> }>)(
      "tool-call",
      {
        text: "今天周五还得上班",
      },
    );

    expect(resolveQqConversationMemeBaseImage).toHaveBeenCalledWith(
      expect.objectContaining({
        conversationKey: "qq:default:group:673105016",
      }),
    );
    expect(runQqMakeMeme).toHaveBeenCalledWith(
      expect.objectContaining({
        image_path: "/tmp/current-chat-image.jpg",
        text: "今天周五还得上班",
      }),
      expect.any(Object),
    );
    expect(result.details).toMatchObject({
      ok: true,
      meme_source: {
        conversation_key: "qq:default:group:673105016",
        source: "inbound",
        summary: "当前聊天图片",
      },
    });
  });
});
