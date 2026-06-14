import { describe, expect, it } from "vitest";
import { resolveQqAccount } from "./accounts.js";
import { __testing } from "./service.js";
import type { CoreConfig, OneBotMessageEvent } from "./types.js";

function buildEvent(overrides: Partial<OneBotMessageEvent> = {}): OneBotMessageEvent {
  return {
    post_type: "message",
    self_id: 2509109290,
    message_type: "group",
    user_id: 2136387285,
    group_id: 673105016,
    message: "hello",
    ...overrides,
  };
}

describe("qq-natural blocked inbound users", () => {
  it("preserves blockedUserIds in resolved account config", () => {
    const cfg: CoreConfig = {
      channels: {
        qq: {
          enabled: true,
          blockedUserIds: ["2136387285", " 1304086244 "],
        },
      },
    };

    const account = resolveQqAccount({ cfg });

    expect(account.config.blockedUserIds).toEqual(["2136387285", " 1304086244 "]);
  });

  it("matches blocked senders in group chats", () => {
    const account = resolveQqAccount({
      cfg: {
        channels: {
          qq: {
            enabled: true,
            blockedUserIds: ["2136387285"],
          },
        },
      } satisfies CoreConfig,
    });

    expect(__testing.isBlockedInboundQqSender(account, buildEvent())).toBe(true);
  });

  it("matches blocked senders in private chats", () => {
    const account = resolveQqAccount({
      cfg: {
        channels: {
          qq: {
            enabled: true,
            blockedUserIds: ["2136387285"],
          },
        },
      } satisfies CoreConfig,
    });

    expect(
      __testing.isBlockedInboundQqSender(
        account,
        buildEvent({
          message_type: "private",
          group_id: undefined,
        }),
      ),
    ).toBe(true);
  });

  it("normalizes string values before matching", () => {
    const account = resolveQqAccount({
      cfg: {
        channels: {
          qq: {
            enabled: true,
            blockedUserIds: [" 2136387285 "],
          },
        },
      } satisfies CoreConfig,
    });

    expect(__testing.isBlockedInboundQqSender(account, buildEvent())).toBe(true);
  });

  it("does not match non-blocked users", () => {
    const account = resolveQqAccount({
      cfg: {
        channels: {
          qq: {
            enabled: true,
            blockedUserIds: ["2136387285"],
          },
        },
      } satisfies CoreConfig,
    });

    expect(
      __testing.isBlockedInboundQqSender(
        account,
        buildEvent({
          user_id: 1304086244,
        }),
      ),
    ).toBe(false);
  });

  it("keeps behavior unchanged when blockedUserIds is missing", () => {
    const account = resolveQqAccount({
      cfg: {
        channels: {
          qq: {
            enabled: true,
          },
        },
      } satisfies CoreConfig,
    });

    expect(__testing.isBlockedInboundQqSender(account, buildEvent())).toBe(false);
  });
});
