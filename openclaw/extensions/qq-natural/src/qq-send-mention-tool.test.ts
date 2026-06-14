import { beforeEach, describe, expect, it, vi } from "vitest";

const sendQqSegments = vi.fn(async (params: Record<string, unknown>) => ({
  status: "ok",
  retcode: 0,
  data: {
    message_id: 778899,
    echoed: params,
  },
}));

const getQqGroupMembers = vi.fn(async () => ({
  status: "ok",
  retcode: 0,
  data: [{ user_id: 3772118212, nickname: "Miko", card: "" }],
}));

vi.mock("./service.js", () => ({
  buildRecallTrackingKey: vi.fn(),
  debugInjectQqInboundMessage: vi.fn(),
  debugInjectQqInboundSequence: vi.fn(),
  getQqFile: vi.fn(),
  getQqGroupFileUrl: vi.fn(),
  getQqGroupFilesByFolder: vi.fn(),
  getQqGroupInfo: vi.fn(),
  getQqGroupMembers,
  getQqGroupRootFiles: vi.fn(),
  getQqLoginInfo: vi.fn(),
  getQqPacketStatus: vi.fn(),
  getQqUserInfo: vi.fn(),
  rememberSentQqMedia: vi.fn(),
  recallRecentQqMessages: vi.fn(),
  sendQqMedia: vi.fn(),
  sendQqSegments,
  sendQqVoice: vi.fn(),
  sendQqLike: vi.fn(),
  uploadQqGroupFile: vi.fn(),
}));

describe("qq_send_mention tool", () => {
  beforeEach(() => {
    getQqGroupMembers.mockClear();
    sendQqSegments.mockClear();
  });

  it("treats a bare numeric target as a QQ group for mention sends", async () => {
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
          sessionKey: "agent:fusion-main:main",
          messageChannel: "qq",
          agentAccountId: "default",
          requesterSenderId: "1446437177",
        };
        const tool =
          typeof toolOrFactory === "function" ? toolOrFactory(ctx) : (toolOrFactory as Record<string, unknown>);
        tools.set(String(tool.name), tool);
      },
    };

    registerQqNativeTools(api as never);
    const tool = tools.get("qq_send_mention");
    expect(tool).toBeTruthy();

    const result = await (tool?.execute as (...args: unknown[]) => Promise<{ details: Record<string, unknown> }>)(
      "tool-call",
      {
        target: "673105016",
        mention_name: "Miko",
        text: "请我吃疯狂星期四",
      },
    );

    expect(getQqGroupMembers).toHaveBeenCalledWith(
      expect.objectContaining({
        groupId: "673105016",
      }),
    );
    expect(sendQqSegments).toHaveBeenCalledWith(
      expect.objectContaining({
        targetKind: "group",
        targetId: "673105016",
        message: [
          { type: "at", data: { qq: "3772118212" } },
          { type: "text", data: { text: " 请我吃疯狂星期四" } },
        ],
      }),
    );
    expect(result.details).toMatchObject({
      ok: true,
      target_kind: "group",
      target_id: "673105016",
      mention_user_id: "3772118212",
      mention_name: "Miko",
      message_id: 778899,
    });
  });
});
