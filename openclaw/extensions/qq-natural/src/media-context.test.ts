import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural media context", () => {
  it("keeps only current-turn media in the agent body", () => {
    const agentBody = __testing.buildQqAgentBody({
      focusEntry: {
        rawBody: "你看这张图怎么样",
        parsed: {
          text: "你看这张图怎么样",
          isReply: false,
          replyToMessageId: undefined,
          wasMentioned: true,
          mentionIds: [],
          imageUrls: ["file:///tmp/current.png"],
          mediaSegments: [],
          hasOnlyMediaLike: false,
        },
      },
      burstContext: "1. tester: 你看这张图怎么样",
      currentMedia: [
        {
          id: "current-1",
          source: "inbound",
          message_id: "1",
          sender_id: "123",
          sender_name: "tester",
          type: "image",
          caption: "你看这张图怎么样",
          quoted_text: "",
          image_count: 1,
          images: [
            {
              index: 1,
              ocr: "",
              alt: "当前图片",
              vision_summary: "当前回合图片",
            },
          ],
          summary: "当前图片",
          created_at: Date.now(),
        },
      ],
      boundMedia: null,
      replyTarget: {
        messageId: "reply-1",
        senderId: "456",
        senderName: "quoted-user",
        text: "上一条文字回复",
      },
      conversationKey: "qq:default:group:673105016",
    } as never);

    expect(agentBody).toContain("[QQCurrentTurnMedia]");
    expect(agentBody).toContain("当前图片");
    expect(agentBody).toContain("[QQReplyTarget]");
    expect(agentBody).not.toContain("[QQBoundMedia]");
    expect(agentBody).not.toContain("[QQRecentMediaBuffer]");
    expect(agentBody).not.toContain('"has_media"');
  });
});
