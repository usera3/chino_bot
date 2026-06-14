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

describe("qq-natural fairness gate", () => {
  it("skips low-value group noise when other conversations are pending", () => {
    expect(
      __testing.shouldSkipQqFairnessNoise({
        conversationKey: "qq:default:group:current",
        isGroup: true,
        rawBody: "用户发送了1张图片",
        parsed: parsed({ hasOnlyMediaLike: true }),
        globalLoadOverride: {
          competingConversationCount: 1,
          totalPendingCount: 2,
        },
      }),
    ).toEqual({
      skip: true,
      reason: "fairness-group-noise",
      fairnessClass: "group-noise",
      competingConversationCount: 1,
      totalPendingCount: 2,
    });
  });

  it("skips low-value direct noise only under higher global pressure", () => {
    expect(
      __testing.shouldSkipQqFairnessNoise({
        conversationKey: "qq:default:direct:current",
        isGroup: false,
        rawBody: "嗯",
        parsed: parsed({ text: "嗯" }),
        globalLoadOverride: {
          competingConversationCount: 2,
          totalPendingCount: 3,
        },
      }),
    ).toEqual({
      skip: false,
      reason: "direct-noise",
      fairnessClass: "direct-noise",
      competingConversationCount: 2,
      totalPendingCount: 3,
    });
  });

  it("skips low-value direct noise only at higher fairness pressure", () => {
    expect(
      __testing.shouldSkipQqFairnessNoise({
        conversationKey: "qq:default:direct:current",
        isGroup: false,
        rawBody: "嗯",
        parsed: parsed({ text: "嗯" }),
        globalLoadOverride: {
          competingConversationCount: 3,
          totalPendingCount: 5,
        },
      }),
    ).toEqual({
      skip: true,
      reason: "fairness-direct-noise",
      fairnessClass: "direct-noise",
      competingConversationCount: 3,
      totalPendingCount: 5,
    });
  });

  it("does not skip explicit questions", () => {
    expect(
      __testing.shouldSkipQqFairnessNoise({
        conversationKey: "qq:default:group:current",
        isGroup: true,
        rawBody: "这怎么回事？",
        parsed: parsed({ text: "这怎么回事？" }),
        globalLoadOverride: {
          competingConversationCount: 3,
          totalPendingCount: 6,
        },
      }),
    ).toEqual({
      skip: false,
      reason: "priority-protected",
      fairnessClass: "group-question",
      competingConversationCount: 3,
      totalPendingCount: 6,
    });
  });

  it("keeps direct engagement exempt from fairness gating", () => {
    expect(
      __testing.shouldSkipQqFairnessNoise({
        conversationKey: "qq:default:group:current",
        isGroup: true,
        rawBody: "[QQ:2509109290] 嗯",
        parsed: parsed({ wasMentioned: true }),
      }),
    ).toEqual({
      skip: false,
      reason: "direct-engagement",
      fairnessClass: "mention",
      competingConversationCount: 0,
      totalPendingCount: 0,
    });
  });
});
