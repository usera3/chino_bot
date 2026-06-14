import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";
import type { ParsedQqMessage } from "./types.js";

function parsed(overrides: Partial<ParsedQqMessage> = {}): ParsedQqMessage {
  return {
    text: "",
    isReply: false,
    replyToMessageId: undefined,
    wasMentioned: false,
    mentionIds: [],
    imageUrls: [],
    mediaSegments: [],
    hasOnlyMediaLike: false,
    ...overrides,
  };
}

describe("qq-natural scheduling decision", () => {
  it("prefers overload gating before fairness gating", () => {
    expect(
      __testing.resolveQqSchedulingDecision({
        conversationKey: "qq:default:group:1",
        isGroup: true,
        rawBody: "嗯",
        parsed: parsed({ text: "嗯" }),
        busyLevel: "busy",
        pendingCount: 2,
        messageTimestamp: Date.now(),
        globalLoadOverride: {
          competingConversationCount: 5,
          totalPendingCount: 8,
        },
      }),
    ).toMatchObject({
      skip: true,
      mode: "overload_gate",
    });
  });

  it("prefers fairness gating before stale gating", () => {
    expect(
      __testing.resolveQqSchedulingDecision({
        conversationKey: "qq:default:group:1",
        isGroup: true,
        rawBody: "用户发送了1张图片",
        parsed: parsed({ hasOnlyMediaLike: true }),
        busyLevel: "light",
        pendingCount: 1,
        messageTimestamp: 0,
        nowMs: 60_000,
        globalLoadOverride: {
          competingConversationCount: 1,
          totalPendingCount: 2,
        },
      }),
    ).toMatchObject({
      skip: true,
      mode: "fairness_gate",
    });
  });

  it("uses stale gate when message is old but otherwise schedulable", () => {
    expect(
      __testing.resolveQqSchedulingDecision({
        conversationKey: "qq:default:group:1",
        isGroup: true,
        rawBody: "哈哈",
        parsed: parsed({ text: "哈哈" }),
        busyLevel: "idle",
        pendingCount: 0,
        messageTimestamp: 0,
        nowMs: 25_000,
        globalLoadOverride: {
          competingConversationCount: 0,
          totalPendingCount: 0,
        },
      }),
    ).toMatchObject({
      skip: true,
      mode: "stale_gate",
      fairnessClass: "group-noise",
    });
  });
});
