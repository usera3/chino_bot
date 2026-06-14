import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq-natural decision stage", () => {
  it("maps gate modes to decision stages", () => {
    expect(__testing.inferQqDecisionStage({ mode: "overload_gate" })).toBe("overload");
    expect(__testing.inferQqDecisionStage({ mode: "fairness_gate" })).toBe("fairness");
    expect(__testing.inferQqDecisionStage({ mode: "stale_gate" })).toBe("stale");
    expect(__testing.inferQqDecisionStage({ mode: "mention_gate" })).toBe("mention");
  });

  it("treats immediate actions as immediate stage", () => {
    expect(__testing.inferQqDecisionStage({ mode: "explicit_image_search" })).toBe("immediate");
    expect(__testing.inferQqDecisionStage({ mode: "identity_question" })).toBe("immediate");
  });

  it("falls back to dispatch for normal routed replies", () => {
    expect(__testing.inferQqDecisionStage({ mode: "direct" })).toBe("dispatch");
    expect(__testing.inferQqDecisionStage({ mode: "ambient-passive" })).toBe("dispatch");
  });
});
