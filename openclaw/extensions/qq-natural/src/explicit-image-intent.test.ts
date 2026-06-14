import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural explicit image intent", () => {
  it("does not treat inbound image placeholders as search requests", () => {
    expect(
      __testing.detectQqExplicitImageIntent({
        rawBody: "用户发送了1张图片",
      }),
    ).toBeNull();
  });

  it("does not treat current-image questions as web image search", () => {
    expect(
      __testing.detectQqExplicitImageIntent({
        rawBody: "[QQ:2509109290] 这是什么表情包",
        selfId: "2509109290",
      }),
    ).toBeNull();
  });

  it("still keeps explicit image search requests working", () => {
    expect(
      __testing.detectQqExplicitImageIntent({
        rawBody: "[QQ:2509109290] 给我发张博丽灵梦的美图",
        selfId: "2509109290",
      }),
    ).toMatchObject({
      kind: "search",
      query: "博丽灵梦的美 图片",
    });
  });

  it("treats short meme asks with 给我 as image search intent", () => {
    expect(
      __testing.detectQqExplicitImageIntent({
        rawBody: "[QQ:2509109290] 给我发个表情包",
        selfId: "2509109290",
      }),
    ).toMatchObject({
      kind: "search",
      query: "表情包",
      caption: "给你来一张",
    });
  });

  it("treats short meme asks with 给我来个 as image search intent", () => {
    expect(
      __testing.detectQqExplicitImageIntent({
        rawBody: "[QQ:2509109290] 给我来个表情包",
        selfId: "2509109290",
      }),
    ).toMatchObject({
      kind: "search",
      query: "表情包",
      caption: "给你来一张",
    });
  });
});
