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

describe("qq-natural fairness class", () => {
  it("classifies mentions and replies as direct engagement classes", () => {
    expect(
      __testing.classifyQqFairnessClass({
        isGroup: true,
        rawBody: "[QQ:2509109290] 嗯",
        parsed: parsed({ wasMentioned: true }),
      }),
    ).toBe("mention");
    expect(
      __testing.classifyQqFairnessClass({
        isGroup: true,
        rawBody: "好",
        parsed: parsed({ isReply: true }),
      }),
    ).toBe("reply");
  });

  it("classifies direct media separately from direct noise", () => {
    expect(
      __testing.classifyQqFairnessClass({
        isGroup: false,
        rawBody: "用户发送了1张图片",
        parsed: parsed({
          mediaSegments: [{ type: "image", sourceType: "image" }] as never,
          hasOnlyMediaLike: false,
        }),
      }),
    ).toBe("direct-media");
    expect(
      __testing.classifyQqFairnessClass({
        isGroup: false,
        rawBody: "嗯",
        parsed: parsed({ text: "嗯" }),
      }),
    ).toBe("direct-noise");
  });

  it("classifies group media questions separately from media noise", () => {
    expect(
      __testing.classifyQqFairnessClass({
        isGroup: true,
        rawBody: "这张图怎么回事？",
        parsed: parsed({
          text: "这张图怎么回事？",
          mediaSegments: [{ type: "image", sourceType: "image" }] as never,
        }),
      }),
    ).toBe("group-media-question");
    expect(
      __testing.classifyQqFairnessClass({
        isGroup: true,
        rawBody: "用户发送了1张图片",
        parsed: parsed({ hasOnlyMediaLike: true }),
      }),
    ).toBe("group-noise");
  });
});
