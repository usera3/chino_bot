import { beforeEach, describe, expect, it, vi } from "vitest";

const { sendQqMedia, sendQqText } = vi.hoisted(() => ({
  sendQqMedia: vi.fn(async () => ({
    status: "ok",
    retcode: 0,
    data: { message_id: 13579 },
  })),
  sendQqText: vi.fn(async () => ({
    status: "ok",
    retcode: 0,
    data: { message_id: 24680 },
  })),
}));

vi.mock("./service.js", () => ({
  sendQqMedia,
  sendQqText,
}));

vi.mock("./accounts.js", () => ({
  listQqAccountIds: vi.fn(() => []),
  resolveDefaultQqAccountId: vi.fn(() => "default"),
  resolveQqAccount: vi.fn(() => ({
    accountId: "default",
    name: "QQ",
    enabled: true,
    selfId: "2509109290",
    autoLaunch: false,
    preventIdleSleep: false,
    config: {},
    executablePath: "",
    listenHost: "127.0.0.1",
    listenPort: 8080,
    websocketPath: "/onebot/v11/ws",
  })),
}));

vi.mock("./runtime.js", () => ({
  getQqRuntime: vi.fn(() => ({
    channel: {
      text: {
        chunkMarkdownText: (text: string) => [text],
      },
    },
  })),
}));

import { qqPlugin } from "./channel.js";

describe("qq-natural outbound audio payloads", () => {
  beforeEach(() => {
    sendQqMedia.mockClear();
    sendQqText.mockClear();
  });

  it("preserves audioAsVoice when outbound payload media is audio", async () => {
    const outbound = qqPlugin.outbound;
    if (!outbound?.sendPayload) {
      throw new Error("qq outbound sendPayload is unavailable");
    }

    const result = await outbound.sendPayload({
      cfg: {} as never,
      to: "group:673105016",
      text: "",
      payload: {
        text: "今天也要继续推进 openclaw",
        mediaUrl: "/tmp/reply.mp3",
        audioAsVoice: true,
      } as never,
      accountId: "default",
    });

    expect(sendQqMedia).toHaveBeenCalledWith(
      expect.objectContaining({
        targetKind: "group",
        targetId: "673105016",
        text: "今天也要继续推进 openclaw",
        mediaUrl: "/tmp/reply.mp3",
        audioAsVoice: true,
      }),
    );
    expect(result).toMatchObject({
      channel: "qq",
      chatId: "group:673105016",
    });
  });
});
