import { describe, expect, it } from "vitest";
import { shouldSuppressNoisyUserFacingErrorReply } from "./user-facing-error-suppression.js";

describe("shouldSuppressNoisyUserFacingErrorReply", () => {
  it("suppresses embedded agent failure dumps", () => {
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "⚠️ Agent failed before reply: HTTP 502: Bad Gateway.\nLogs: openclaw logs --follow",
      }),
    ).toBe(true);
  });

  it("suppresses all-models-failed rate-limit dumps", () => {
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: [
          "All models failed (3)",
          "",
          "openai/gpt-5.4 ⚠️ API rate limit reached. Please try again later.",
          "google/gemini-3-flash-preview ⚠️ API rate limit reached. Please try again later.",
        ].join("\n"),
      }),
    ).toBe(true);
  });

  it("suppresses generic transient provider errors", () => {
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "The AI service is temporarily overloaded. Please try again in a moment.",
      }),
    ).toBe(true);
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "LLM request timed out.",
      }),
    ).toBe(true);
  });

  it("suppresses raw provider concurrency-limit errors", () => {
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "Concurrency limit exceeded for account, please retry later",
      }),
    ).toBe(true);
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "Concurrency limit exceeded for user, please retry later.",
      }),
    ).toBe(true);
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "Concurrency limit exceeded for account\nplease retry later",
      }),
    ).toBe(true);
  });

  it("suppresses generated billing copy", () => {
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text:
          "⚠️ API provider returned a billing error — your API key has run out of credits or has an insufficient balance.",
      }),
    ).toBe(true);
  });

  it("keeps actionable non-transient replies", () => {
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "⚠️ Context overflow — this conversation is too large for the model. Use /new to start a fresh session.",
      }),
    ).toBe(false);
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "我来解释一下 API rate limit reached 这句话是什么意思。",
      }),
    ).toBe(false);
  });

  it("does not suppress replies that include media", () => {
    expect(
      shouldSuppressNoisyUserFacingErrorReply({
        text: "⚠️ Agent failed before reply: HTTP 502: Bad Gateway.",
        mediaUrl: "https://example.com/cat.png",
      }),
    ).toBe(false);
  });
});
