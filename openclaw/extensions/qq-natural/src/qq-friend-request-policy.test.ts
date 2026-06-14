import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq friend request policy", () => {
  it("extracts qq level from stranger info payloads", () => {
    expect(
      __testing.extractQqUserLevel({
        qqLevel: 59,
      }),
    ).toBe(59);
    expect(
      __testing.extractQqUserLevel({
        level: 16,
      }),
    ).toBe(16);
    expect(__testing.extractQqUserLevel({})).toBeNull();
  });

  it("treats one sun as level 16 or above", () => {
    expect(__testing.hasAtLeastOneSunQqLevel(15)).toBe(false);
    expect(__testing.hasAtLeastOneSunQqLevel(16)).toBe(true);
    expect(__testing.hasAtLeastOneSunQqLevel(59)).toBe(true);
  });

  it("recognizes friend request events", () => {
    expect(
      __testing.isFriendRequestEvent({
        post_type: "request",
        request_type: "friend",
        self_id: 2509109290,
        user_id: 1446437177,
        flag: "friend-request-flag",
      } as never),
    ).toBe(true);
    expect(
      __testing.isFriendRequestEvent({
        post_type: "notice",
        notice_type: "notify",
        sub_type: "poke",
      } as never),
    ).toBe(false);
  });
});
