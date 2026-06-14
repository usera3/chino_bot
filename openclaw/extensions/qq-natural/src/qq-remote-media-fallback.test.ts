import { describe, expect, it, vi } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural remote media fallback", () => {
  it("recognizes qq media hosts for direct fallback fetch", () => {
    expect(
      __testing.canUseDirectQqMediaFetch("https://multimedia.nt.qq.com.cn/download?id=1"),
    ).toBe(true);
    expect(__testing.canUseDirectQqMediaFetch("https://gchat.qpic.cn/gchatpic_new/1/2-3-4/0")).toBe(
      true,
    );
    expect(__testing.canUseDirectQqMediaFetch("https://example.com/image.jpg")).toBe(false);
  });

  it("falls back to direct fetch when runtime media fetch is blocked", async () => {
    const saveMediaBuffer = vi.fn(async () => ({
      path: "/tmp/qq-fallback-image.jpg",
      contentType: "image/jpeg",
    }));
    const runtime = {
      channel: {
        media: {
          fetchRemoteMedia: vi.fn(async () => {
            throw new Error("Blocked: resolves to private/internal/special-use IP address");
          }),
          saveMediaBuffer,
        },
      },
    } as never;

    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn(async () => {
      return new Response(Buffer.from("fake-image"), {
        status: 200,
        headers: {
          "content-type": "image/jpeg",
          "content-length": "10",
        },
      });
    }) as typeof fetch;

    try {
      const result = await __testing.resolveInboundMediaPayload({
        runtime,
        account: {
          config: { mediaMaxMb: 20 },
        } as never,
        imageUrls: ["https://multimedia.nt.qq.com.cn/download?appid=1407"],
      });

      expect(result.resolvedMedia[0]).toMatchObject({
        sourceUrl: "https://multimedia.nt.qq.com.cn/download?appid=1407",
        localPath: "/tmp/qq-fallback-image.jpg",
        contentType: "image/jpeg",
      });
      expect(saveMediaBuffer).toHaveBeenCalled();
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
