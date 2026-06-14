import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural load debug", () => {
  it("includes global load metrics in debug summaries", () => {
    const summary = __testing.buildQqDebugInjectionSummary({
      conversationKey: "qq:default:group:673105016",
      focusEntry: {
        event: {
          message_id: 123,
        },
      },
      rawBody: "测试消息",
      state: {
        busyLevel: "busy",
        pendingCount: 2,
        recentMediaBuffer: [],
        recentMessages: [],
        debugEvents: [],
        lastTouchedAt: Date.now(),
      },
      action: "dispatch",
      mode: "direct",
      globalLoadOverride: {
        competingConversationCount: 3,
        totalPendingCount: 6,
      },
    } as never);

    expect(summary.state).toMatchObject({
      busy_level: "busy",
      pending_count: 2,
      competing_conversation_count: 3,
      total_pending_count: 6,
    });
  });
});
