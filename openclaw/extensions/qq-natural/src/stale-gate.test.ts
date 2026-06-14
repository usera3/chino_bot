import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural stale gate", () => {
  it("protects direct engagement classes from stale dropping", () => {
    expect(
      __testing.shouldSkipQqStaleMessage({
        fairnessClass: "mention",
        messageTimestamp: 0,
        nowMs: 10 * 60 * 1000,
      }),
    ).toEqual({
      skip: false,
      reason: "stale-protected",
      ageMs: 10 * 60 * 1000,
      staleThresholdMs: null,
    });
  });

  it("drops stale group noise quickly", () => {
    expect(
      __testing.shouldSkipQqStaleMessage({
        fairnessClass: "group-noise",
        messageTimestamp: 0,
        nowMs: 25 * 1000,
      }),
    ).toEqual({
      skip: true,
      reason: "stale-group-noise",
      ageMs: 25 * 1000,
      staleThresholdMs: 20 * 1000,
    });
  });

  it("keeps recent group questions", () => {
    expect(
      __testing.shouldSkipQqStaleMessage({
        fairnessClass: "group-question",
        messageTimestamp: 0,
        nowMs: 30 * 1000,
      }),
    ).toEqual({
      skip: false,
      reason: "fresh-enough",
      ageMs: 30 * 1000,
      staleThresholdMs: 90 * 1000,
    });
  });

  it("drops stale direct noise after a shorter threshold", () => {
    expect(
      __testing.shouldSkipQqStaleMessage({
        fairnessClass: "direct-noise",
        messageTimestamp: 0,
        nowMs: 60 * 1000,
      }),
    ).toEqual({
      skip: true,
      reason: "stale-direct-noise",
      ageMs: 60 * 1000,
      staleThresholdMs: 45 * 1000,
    });
  });
});
