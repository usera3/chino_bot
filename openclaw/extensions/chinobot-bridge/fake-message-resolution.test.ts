import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGetQqGroupMembers = vi.fn();

vi.mock("../qq-natural/src/service.js", () => ({
  buildRecallTrackingKey: vi.fn(),
  getQqGroupMembers: mockGetQqGroupMembers,
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
  sendQqSegments: vi.fn(),
  sendQqVoice: vi.fn(),
  sendQqLike: vi.fn(),
  uploadQqGroupFile: vi.fn(),
}));

describe("chinobot fake message speaker resolution", () => {
  beforeEach(() => {
    mockGetQqGroupMembers.mockReset();
    mockGetQqGroupMembers.mockResolvedValue({
      data: [
        { user_id: "1446437177", nickname: "空白", card: "" },
        { user_id: "2509109290", nickname: "Miko", card: "Miko" },
        { user_id: "1401852832", nickname: "阿白", card: "" },
      ],
    });
  });

  it("resolves requester, bot, and group nickname speakers into distinct participants", async () => {
    const { default: plugin } = await import("./index.js");
    const toolFactories = new Map<string, (ctx: unknown) => { execute: (...args: unknown[]) => Promise<unknown> }>();

    const api = {
      config: {},
      pluginConfig: {},
      registerTool(toolOrFactory: unknown, meta?: { name?: string }) {
        if (meta?.name && typeof toolOrFactory === "function") {
          toolFactories.set(meta.name, toolOrFactory as never);
        }
      },
    };

    plugin.register(api as never);

    const fakeMessageToolFactory = toolFactories.get("chinobot_send_fake_message");
    expect(fakeMessageToolFactory).toBeTypeOf("function");

    const tool = fakeMessageToolFactory?.({
      agentId: "main",
      sessionKey: "agent:main:test",
      messageChannel: "qq",
      agentAccountId: "default",
      requesterSenderId: "1446437177",
    });
    const result = await tool?.execute("call-1", {
      messages: "触发者说你好|机器人说收到啦|@阿白说围观一下",
      target: "group:673105016",
      bot_qq: "2509109290",
      dry_run: true,
    });

    const text = String(
      ((result as { content?: Array<{ text?: string }> }).content ?? [])[0]?.text ?? "",
    );
    const payload = JSON.parse(text) as {
      ok: boolean;
      message_count: number;
      messages: Array<{ data: { name: string; uin: string; content: string } }>;
    };

    expect(payload.ok).toBe(true);
    expect(payload.message_count).toBe(3);
    expect(payload.messages.map((entry) => entry.data.uin)).toEqual([
      "1446437177",
      "2509109290",
      "1401852832",
    ]);
    expect(payload.messages.map((entry) => entry.data.name)).toEqual(["空白", "Miko", "阿白"]);
  });
});
