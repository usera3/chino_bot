import { describe, expect, it } from "vitest";
import type { OneBotMessageEvent, ResolvedQqAccount } from "./types.js";
import { __testing } from "./service.js";

function createAccount(overrides?: Partial<ResolvedQqAccount>): ResolvedQqAccount {
  return {
    accountId: "default",
    enabled: true,
    name: "QQ",
    selfId: "123456",
    autoLaunch: false,
    preventIdleSleep: false,
    executablePath: "/Applications/QQ.app/Contents/MacOS/QQ",
    launchArgs: [],
    listenHost: "127.0.0.1",
    listenPort: 8080,
    websocketPath: "/onebot/v11/ws",
    config: {
      studyMode: {
        enabled: true,
      },
    },
    ...overrides,
  };
}

function createEvent(messageType: "private" | "group"): OneBotMessageEvent {
  return {
    post_type: "message",
    self_id: 123456,
    message_type: messageType,
    user_id: 10001,
    message_id: 1,
    time: 100,
    message: [],
  };
}

describe("qq-natural study mode progress followups", () => {
  it("schedules delayed progress updates for direct image study turns", () => {
    const followups = __testing.resolveQqStudyProgressFollowups({
      account: createAccount(),
      event: createEvent("private"),
      hasImage: true,
    });

    expect(followups).toEqual([
      { delayMs: 20_000, kind: "solving_delayed" },
      { delayMs: 60_000, kind: "rendering_delayed" },
    ]);
  });

  it("skips delayed progress updates for direct text-only turns", () => {
    const followups = __testing.resolveQqStudyProgressFollowups({
      account: createAccount(),
      event: createEvent("private"),
      hasImage: false,
    });

    expect(followups).toEqual([]);
  });

  it("skips delayed progress updates for group image turns", () => {
    const followups = __testing.resolveQqStudyProgressFollowups({
      account: createAccount(),
      event: createEvent("group"),
      hasImage: true,
    });

    expect(followups).toEqual([]);
  });
});
