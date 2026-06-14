import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq image search selection", () => {
  it("rotates candidates for the same selection key and avoids immediate repeats", () => {
    __testing.resetQqImageSearchSelectionState();
    const urls = ["https://example.com/a.jpg", "https://example.com/b.jpg", "https://example.com/c.jpg"];

    expect(
      __testing.buildQqImageSearchSelectionOrder({
        sourceUrls: urls,
        selectionKey: "reaction:laugh-shock",
        nowMs: 1000,
      }),
    ).toEqual(urls);

    __testing.rememberQqImageSearchSelection({
      sourceUrl: "https://example.com/a.jpg",
      selectionKey: "reaction:laugh-shock",
      totalCount: 3,
      nowMs: 1000,
    });

    expect(
      __testing.buildQqImageSearchSelectionOrder({
        sourceUrls: urls,
        selectionKey: "reaction:laugh-shock",
        nowMs: 2000,
      }),
    ).toEqual(["https://example.com/b.jpg", "https://example.com/c.jpg", "https://example.com/a.jpg"]);
  });
});
