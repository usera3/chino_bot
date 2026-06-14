import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { __testing } from "./service.js";

const tempDirs: string[] = [];

function createLogger() {
  return {
    debug() {},
    info() {},
    warn() {},
    error() {},
  };
}

describe("qq session rollover guard", () => {
  afterEach(() => {
    for (const dir of tempDirs.splice(0)) {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("marks deep group sessions stale so the next turn rolls over cleanly", () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "qq-rollover-"));
    tempDirs.push(tempDir);
    const storePath = path.join(tempDir, "sessions.json");
    const sessionFile = path.join(tempDir, "session-a.jsonl");
    const sessionKey = "agent:main:qq:group:673105016";

    fs.writeFileSync(
      sessionFile,
      Array.from({ length: 430 }, (_, index) =>
        JSON.stringify({
          type: "message",
          id: `m-${index}`,
          parentId: index > 0 ? `m-${index - 1}` : undefined,
        }),
      ).join("\n") + "\n",
      "utf8",
    );
    fs.writeFileSync(
      storePath,
      JSON.stringify(
        {
          [sessionKey]: {
            sessionId: "session-a",
            sessionFile,
            updatedAt: Date.now(),
          },
        },
        null,
        2,
      ) + "\n",
      "utf8",
    );

    const result = __testing.maybeMarkQqSessionForRollover({
      api: {
        logger: createLogger(),
      },
      storePath,
      sessionKey,
      conversationKey: "qq:default:group:673105016",
    });

    expect(result.rolledOver).toBe(true);
    expect(result.lineCount).toBe(430);

    const stored = JSON.parse(fs.readFileSync(storePath, "utf8")) as Record<
      string,
      { updatedAt?: number }
    >;
    expect(stored[sessionKey]?.updatedAt).toBe(0);
  });
});
