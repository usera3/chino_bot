import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, it } from "vitest";
import { normalizeOneBotMediaFile, resolveQqHttpMediaUrl } from "./onebot-media-file.js";

describe("normalizeOneBotMediaFile", () => {
  it("keeps remote media URLs unchanged", () => {
    expect(normalizeOneBotMediaFile("https://example.com/cat.png")).toBe(
      "https://example.com/cat.png",
    );
    expect(normalizeOneBotMediaFile("file:///tmp/cat.png")).toBe("/tmp/cat.png");
    expect(normalizeOneBotMediaFile("data:image/png;base64,abc")).toBe("data:image/png;base64,abc");
  });

  it("keeps absolute local paths as filesystem paths", () => {
    const filePath = path.join(os.tmpdir(), "openclaw image.png");
    expect(normalizeOneBotMediaFile(filePath)).toBe(filePath);
  });

  it("expands home-relative paths into absolute filesystem paths", () => {
    const homeRelative = "~/Pictures/openclaw-test.png";
    const expanded = path.join(os.homedir(), "Pictures", "openclaw-test.png");
    expect(normalizeOneBotMediaFile(homeRelative)).toBe(expanded);
  });
});

describe("resolveQqHttpMediaUrl", () => {
  it("keeps HTTP media URLs unchanged", async () => {
    await expect(
      resolveQqHttpMediaUrl({
        mediaUrl: "https://example.com/cat.png",
        gatewayPort: 18789,
      }),
    ).resolves.toBe("https://example.com/cat.png");
  });

  it("publishes local file URLs through the local HTTP proxy", async () => {
    const filePath = path.join(os.tmpdir(), `openclaw-qq-proxy-${Date.now()}.png`);
    await fs.writeFile(filePath, Buffer.from("png"));
    try {
      const proxied = await resolveQqHttpMediaUrl({
        mediaUrl: pathToFileURL(filePath).toString(),
        gatewayPort: 18789,
      });
      expect(proxied).toMatch(
        /^http:\/\/127\.0\.0\.1:18789\/__openclaw__\/canvas\/qq-media\/qq-media-/,
      );
    } finally {
      await fs.unlink(filePath).catch(() => {});
    }
  });
});
