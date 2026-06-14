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

describe("qq-natural overload gate", () => {
  it("skips low-value media-only group messages when the conversation is busy", () => {
    expect(
      __testing.shouldSkipQqOverloadNoise({
        isGroup: true,
        busyLevel: "busy",
        pendingCount: 2,
        rawBody: "用户发送了1张图片",
        parsed: parsed({ hasOnlyMediaLike: true }),
      }),
    ).toEqual({
      skip: true,
      reason: "group-overload-media-only",
    });
  });

  it("does not skip direct engagement even when busy", () => {
    expect(
      __testing.shouldSkipQqOverloadNoise({
        isGroup: true,
        busyLevel: "overloaded",
        pendingCount: 5,
        rawBody: "[QQ:2509109290] 嗯",
        parsed: parsed({ wasMentioned: true }),
      }),
    ).toEqual({
      skip: false,
      reason: "direct-engagement",
    });
  });

  it("does not skip explicit questions", () => {
    expect(
      __testing.shouldSkipQqOverloadNoise({
        isGroup: true,
        busyLevel: "busy",
        pendingCount: 3,
        rawBody: "这怎么回事？",
        parsed: parsed({ text: "这怎么回事？" }),
      }),
    ).toEqual({
      skip: false,
      reason: "not-noise",
    });
  });

  it("skips direct-chat low-info ack only at higher pressure", () => {
    expect(
      __testing.shouldSkipQqOverloadNoise({
        isGroup: false,
        busyLevel: "overloaded",
        pendingCount: 4,
        rawBody: "嗯",
        parsed: parsed({ text: "嗯" }),
      }),
    ).toEqual({
      skip: true,
      reason: "direct-overload-low-info-ack",
    });
  });
});
