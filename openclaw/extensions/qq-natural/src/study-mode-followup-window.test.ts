import { describe, expect, it } from "vitest";
import type { OneBotMessageEvent, ParsedQqMessage, ResolvedQqAccount } from "./types.js";
import { __testing } from "./service.js";

function createAccount(overrides?: Partial<ResolvedQqAccount>): ResolvedQqAccount {
  return {
    accountId: "default",
    enabled: true,
    name: "QQ",
    selfId: "123456",
    autoLaunch: false,
    preventIdleSleep: false,
    executablePath: "/Applications/QQ.app/Contents/MacOS/QQ",
    launchArgs: [],
    listenHost: "127.0.0.1",
    listenPort: 8080,
    websocketPath: "/onebot/v11/ws",
    config: {
      studyMode: {
        enabled: true,
      },
    },
    ...overrides,
  };
}

function createEvent(messageType: "private" | "group"): OneBotMessageEvent {
  return {
    post_type: "message",
    self_id: 123456,
    message_type: messageType,
    user_id: 10001,
    message_id: 1,
    time: 100,
    message: [],
  };
}

describe("qq-natural study mode follow-up window", () => {
  it("holds direct image-only study turns for a longer merge window", () => {
    const account = createAccount();
    const parsed: ParsedQqMessage = {
      text: "",
      isReply: false,
      replyToMessageId: undefined,
      wasMentioned: false,
      mentionIds: [],
      imageUrls: ["https://example.com/q1.jpg"],
      mediaSegments: [
        {
          type: "image",
          sourceType: "image",
          url: "https://example.com/q1.jpg",
        },
      ],
      hasOnlyMediaLike: true,
    };

    const result = __testing.resolveDirectStudyBurstDelays({
      account,
      event: createEvent("private"),
      parsed,
      conversationKey: "qq:default:direct:10001",
    });

    expect(result.burstIdleMs).toBe(6000);
    expect(result.burstWindowMs).toBe(6000);
  });
});
