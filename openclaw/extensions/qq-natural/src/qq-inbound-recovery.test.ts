import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq inbound recovery helpers", () => {
  it("normalizes recovered NapCat history messages into OneBot events", () => {
    const event = __testing.normalizeQqRecoveredMessageEvent({
      raw: {
        message_type: "group",
        message_id: "7788",
        user_id: "1446437177",
        group_id: "673105016",
        time: 1775702400,
        message: [
          { type: "at", data: { qq: "2509109290" } },
          { type: "text", data: { text: " 你还活着吗" } },
        ],
        sender: {
          user_id: "1446437177",
          nickname: "mozi100",
          card: "空白",
        },
      },
      selfId: "2509109290",
    });

    expect(event).toMatchObject({
      post_type: "message",
      message_type: "group",
      message_id: 7788,
      user_id: 1446437177,
      group_id: 673105016,
      sender: {
        user_id: 1446437177,
        nickname: "mozi100",
        card: "空白",
      },
    });
  });

  it("keeps direct chats but filters group history down to direct engagements after the checkpoint", () => {
    const recovered = __testing.selectRecoverableQqHistoryEvents({
      account: {
        accountId: "default",
        enabled: true,
        selfId: "2509109290",
        autoLaunch: false,
        preventIdleSleep: false,
        executablePath: "",
        launchArgs: [],
        config: {},
        listenHost: "127.0.0.1",
        listenPort: 8080,
        websocketPath: "/onebot/v11/ws",
      },
      sinceMs: 1_000_000,
      cursor: {
        lastHandledAt: 1_050_000,
        lastHandledMessageId: "1001",
      },
      events: [
        {
          post_type: "message",
          self_id: 2509109290,
          message_id: 1001,
          message_type: "group",
          time: 1050,
          user_id: 1446437177,
          group_id: 673105016,
          message: [{ type: "text", data: { text: "老消息" } }],
          sender: { user_id: 1446437177, nickname: "mozi100" },
        },
        {
          post_type: "message",
          self_id: 2509109290,
          message_id: 1002,
          message_type: "group",
          time: 1060,
          user_id: 1446437177,
          group_id: 673105016,
          message: [{ type: "text", data: { text: "普通群聊，不该补发" } }],
          sender: { user_id: 1446437177, nickname: "mozi100" },
        },
        {
          post_type: "message",
          self_id: 2509109290,
          message_id: 1003,
          message_type: "group",
          time: 1070,
          user_id: 1446437177,
          group_id: 673105016,
          message: [
            { type: "at", data: { qq: "2509109290" } },
            { type: "text", data: { text: "最新艾特消息" } },
          ],
          sender: { user_id: 1446437177, nickname: "mozi100" },
        },
        {
          post_type: "message",
          self_id: 2509109290,
          message_id: 1004,
          message_type: "private",
          time: 1080,
          user_id: 3772118212,
          message: [{ type: "text", data: { text: "私聊最新一条" } }],
          sender: { user_id: 3772118212, nickname: "Miko" },
        },
      ],
    });

    expect(recovered.map((entry: { message_id?: number }) => entry.message_id)).toEqual([
      1003, 1004,
    ]);
  });

  it("builds a reply segment for recovery follow-up quoting", () => {
    expect(__testing.buildQqReplySegments("1775132584")).toEqual([
      {
        type: "reply",
        data: { id: "1775132584" },
      },
    ]);
  });
});
