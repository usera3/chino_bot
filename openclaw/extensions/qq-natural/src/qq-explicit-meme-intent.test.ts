import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq explicit meme intent", () => {
  it("parses current-image caption meme asks", () => {
    expect(
      __testing.detectQqExplicitMemeIntent({
        rawBody: "[QQ:2509109290] 给这张图配一句 今天周五还得上班",
        selfId: "2509109290",
      }),
    ).toMatchObject({
      bottomText: "今天周五还得上班",
      reason: "explicit-meme-caption",
    });
  });

  it("parses upper-image embed-text asks", () => {
    expect(
      __testing.detectQqExplicitMemeIntent({
        rawBody: "[QQ:2509109290] 把上面的图嵌入文字 呆…",
        selfId: "2509109290",
      }),
    ).toMatchObject({
      bottomText: "呆…",
      reason: "explicit-meme-caption",
    });
  });

  it("parses top and bottom text meme asks", () => {
    expect(
      __testing.detectQqExplicitMemeIntent({
        rawBody: "[QQ:2509109290] 把这张图做成表情包 上面写今天周五 下面写还得上班",
        selfId: "2509109290",
      }),
    ).toMatchObject({
      topText: "今天周五",
      bottomText: "还得上班",
      reason: "explicit-meme-top-bottom",
    });
  });

  it("does not mistake generic image questions for meme creation", () => {
    expect(
      __testing.detectQqExplicitMemeIntent({
        rawBody: "[QQ:2509109290] 这是什么表情包",
        selfId: "2509109290",
      }),
    ).toBeNull();
  });

  it("parses image-less meme requests that are waiting for a base image", () => {
    expect(
      __testing.detectQqDeferredMemeIntent({
        rawBody: "[QQ:2509109290] 给我做个表情包 文字添加 怒",
        selfId: "2509109290",
      }),
    ).toMatchObject({
      bottomText: "怒",
      reason: "deferred-meme-caption",
    });
  });
});
