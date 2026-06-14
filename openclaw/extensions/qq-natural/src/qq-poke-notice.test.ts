import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq poke notice bridge", () => {
  it("treats empty-ish poke action responses as accepted", () => {
    expect(__testing.isOneBotActionAccepted({} as never)).toBe(true);
    expect(
      __testing.isOneBotActionAccepted({
        message: "accepted",
      } as never),
    ).toBe(true);
  });

  it("treats explicit poke action errors as failures", () => {
    expect(
      __testing.isOneBotActionAccepted({
        status: "failed",
      } as never),
    ).toBe(false);
    expect(
      __testing.isOneBotActionAccepted({
        wording: "rich media transfer failed",
      } as never),
    ).toBe(false);
  });

  it("turns a group poke notice targeting the bot into a direct-engagement synthetic message", () => {
    const event = __testing.buildSyntheticQqPokeMessageEvent({
      account: {
        accountId: "default",
        enabled: true,
        autoLaunch: false,
        preventIdleSleep: false,
        executablePath: "",
        launchArgs: [],
        config: {},
        listenHost: "127.0.0.1",
        listenPort: 8080,
        websocketPath: "/onebot/v11/ws",
        selfId: "2509109290",
      } as never,
      event: {
        post_type: "notice",
        notice_type: "notify",
        sub_type: "poke",
        self_id: 2509109290,
        user_id: 1446437177,
        target_id: 2509109290,
        group_id: 673105016,
        time: 1_775_247_400,
      },
    });

    expect(event).not.toBeNull();
    expect(event?.message_type).toBe("group");
    expect(event?.sub_type).toBe("notice_poke");
    expect(event?.user_id).toBe(1446437177);
    expect(event?.group_id).toBe(673105016);
    expect(event?.raw_message).toBe("偷偷摸了你一下");
    expect(event?.message).toEqual(__testing.buildSyntheticQqPokeText());
  });

  it("ignores poke notices that do not target the bot", () => {
    const event = __testing.buildSyntheticQqPokeMessageEvent({
      account: {
        accountId: "default",
        enabled: true,
        autoLaunch: false,
        preventIdleSleep: false,
        executablePath: "",
        launchArgs: [],
        config: {},
        listenHost: "127.0.0.1",
        listenPort: 8080,
        websocketPath: "/onebot/v11/ws",
        selfId: "2509109290",
      } as never,
      event: {
        post_type: "notice",
        notice_type: "notify",
        sub_type: "poke",
        self_id: 2509109290,
        user_id: 1446437177,
        target_id: 1300000000,
        group_id: 673105016,
        time: 1_775_247_400,
      },
    });

    expect(event).toBeNull();
  });
});
