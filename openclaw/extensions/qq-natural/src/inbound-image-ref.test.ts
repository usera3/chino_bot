import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural inbound image reference", () => {
  it("prefers a local file path over a remote qq media url", () => {
    const tempPath = path.join(
      os.tmpdir(),
      `openclaw-qq-inbound-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.jpg`,
    );
    fs.writeFileSync(tempPath, "test-image");
    try {
      expect(
        __testing.resolvePreferredQqInboundImageRef({
          file: tempPath,
          url: "https://multimedia.nt.qq.com.cn/download?appid=1407",
        }),
      ).toBe(tempPath);
    } finally {
      fs.unlinkSync(tempPath);
    }
  });

  it("falls back to url when no local file path exists", () => {
    expect(
      __testing.resolvePreferredQqInboundImageRef({
        file: "/tmp/definitely-missing-image-file.jpg",
        url: "https://example.com/image.jpg",
      }),
    ).toBe("https://example.com/image.jpg");
  });
});
