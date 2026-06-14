import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural media delivery plan", () => {
  it("routes audio media through voice delivery and prefers ptt when requested", () => {
    expect(__testing.isQqAudioMediaUrl("/tmp/reply.mp3")).toBe(true);
    expect(
      __testing.resolveQqMediaDeliveryPlan({
        mediaUrl: "/tmp/reply.mp3",
        audioAsVoice: true,
      }),
    ).toEqual({
      kind: "voice",
      dedupeMediaUrl: "ptt:/tmp/reply.mp3",
      preferPtt: true,
    });
  });

  it("keeps regular images on the image delivery path", () => {
    expect(__testing.isQqAudioMediaUrl("https://example.com/image.png")).toBe(false);
    expect(
      __testing.resolveQqMediaDeliveryPlan({
        mediaUrl: "https://example.com/image.png",
        audioAsVoice: true,
      }),
    ).toEqual({
      kind: "image",
      dedupeMediaUrl: "https://example.com/image.png",
    });
  });
});
