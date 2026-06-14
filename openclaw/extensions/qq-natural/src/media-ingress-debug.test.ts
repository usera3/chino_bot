import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural media ingress debug", () => {
  it("records raw image refs and local-file preference for inbound image segments", () => {
    const tempPath = path.join(
      os.tmpdir(),
      `openclaw-qq-media-debug-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.jpg`,
    );
    fs.writeFileSync(tempPath, "debug-image");
    try {
      const parsed = __testing.parseMessageSegments(
        [
          {
            type: "image",
            data: {
              file: tempPath,
              url: "https://multimedia.nt.qq.com.cn/download?appid=1407",
            },
          },
        ],
        "2509109290",
      );
      const rows = __testing.buildQqInboundMediaIngressDebug({
        parsed,
      } as never);

      expect(rows).toHaveLength(1);
      expect(rows[0]).toMatchObject({
        type: "image",
        raw_file: tempPath,
        raw_url_host: "multimedia.nt.qq.com.cn",
        preferred_ref: tempPath,
        local_file_resolved: true,
      });
    } finally {
      fs.unlinkSync(tempPath);
    }
  });

  it("records resolved media diagnostics including resolution mode", () => {
    const rows = __testing.buildResolvedInboundMediaDebug([
      {
        sourceUrl: "https://multimedia.nt.qq.com.cn/download?appid=1407",
        localPath: "/tmp/qq-fallback-image.jpg",
        contentType: "image/jpeg",
        resolution: "qq-direct-fallback",
        error: "",
      },
    ]);

    expect(rows).toEqual([
      expect.objectContaining({
        source_url_host: "multimedia.nt.qq.com.cn",
        local_path: "/tmp/qq-fallback-image.jpg",
        content_type: "image/jpeg",
        resolution: "qq-direct-fallback",
      }),
    ]);
  });
});
