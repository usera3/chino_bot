import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { afterEach, describe, expect, it } from "vitest";
import { runQqMakeMeme } from "./meme.js";

const require = createRequire(import.meta.url);
const sharp = require("sharp") as typeof import("sharp");
const createdFiles: string[] = [];

afterEach(() => {
  for (const filePath of createdFiles.splice(0)) {
    try {
      fs.unlinkSync(filePath);
    } catch {
      // ignore cleanup failures
    }
  }
});

describe("qq meme renderer", () => {
  it("creates a meme image from a base image with wrapped text", async () => {
    const basePath = path.join(os.tmpdir(), `openclaw-meme-base-${Date.now()}.png`);
    const pngBuffer = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0X8AAAAASUVORK5CYII=",
      "base64",
    );
    fs.writeFileSync(basePath, pngBuffer);
    createdFiles.push(basePath);

    const result = await runQqMakeMeme(
      {
        image_path: basePath,
        top_text: "今天周五",
        bottom_text: "还得上班真的绷不住了",
      },
      {
        agents: {
          defaults: {
            workspace: "/Users/mozi100/PycharmProjects/openclaw",
          },
        },
        gateway: {
          port: 18789,
        },
      },
    );

    expect(result).toMatchObject({
      ok: true,
    });
    const filePath = String(result.file_path ?? "");
    expect(filePath).toContain("openclaw-qq-memes");
    expect(fs.existsSync(filePath)).toBe(true);
    expect(result.image_size).toMatchObject({
      original_width: 1,
      original_height: 1,
      output_width: 1,
      output_height: 1,
      resized: false,
      resize_reason: "preserve-original",
    });
    createdFiles.push(filePath);
  });

  it("keeps the original size for ordinary tall images by default", async () => {
    const basePath = path.join(os.tmpdir(), `openclaw-meme-tall-${Date.now()}.jpg`);
    await sharp({
      create: {
        width: 1216,
        height: 2640,
        channels: 3,
        background: { r: 245, g: 245, b: 245 },
      },
    })
      .jpeg()
      .toFile(basePath);
    createdFiles.push(basePath);

    const result = await runQqMakeMeme(
      {
        image_path: basePath,
        text: "怒",
      },
      {
        agents: {
          defaults: {
            workspace: "/Users/mozi100/PycharmProjects/openclaw",
          },
        },
        gateway: {
          port: 18789,
        },
      },
    );

    expect(result).toMatchObject({
      ok: true,
    });
    expect(result.image_size).toMatchObject({
      original_width: 1216,
      original_height: 2640,
      output_width: 1216,
      output_height: 2640,
      resized: false,
      resize_reason: "preserve-original",
    });
    const filePath = String(result.file_path ?? "");
    expect(filePath).toContain("openclaw-qq-memes");
    expect(fs.existsSync(filePath)).toBe(true);
    createdFiles.push(filePath);
  });

  it("smart-resizes very large images when keeping the original would be excessive", async () => {
    const basePath = path.join(os.tmpdir(), `openclaw-meme-huge-${Date.now()}.jpg`);
    await sharp({
      create: {
        width: 4000,
        height: 3000,
        channels: 3,
        background: { r: 240, g: 240, b: 240 },
      },
    })
      .jpeg()
      .toFile(basePath);
    createdFiles.push(basePath);

    const result = await runQqMakeMeme(
      {
        image_path: basePath,
        text: "怒",
      },
      {
        agents: {
          defaults: {
            workspace: "/Users/mozi100/PycharmProjects/openclaw",
          },
        },
        gateway: {
          port: 18789,
        },
      },
    );

    expect(result).toMatchObject({
      ok: true,
    });
    expect(result.image_size).toMatchObject({
      original_width: 4000,
      original_height: 3000,
      resized: true,
      resize_reason: "smart-downscale",
    });
    expect(Number(result.image_size?.output_width ?? 0)).toBeLessThanOrEqual(3072);
    expect(Number(result.image_size?.output_height ?? 0)).toBeLessThanOrEqual(3072);
    expect(
      Number(result.image_size?.output_width ?? 0) * Number(result.image_size?.output_height ?? 0),
    ).toBeLessThanOrEqual(9_000_000);
    const filePath = String(result.file_path ?? "");
    expect(fs.existsSync(filePath)).toBe(true);
    createdFiles.push(filePath);
  });
});
