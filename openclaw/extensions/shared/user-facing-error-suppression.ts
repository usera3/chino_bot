type ReplyPayloadLike = {
  text?: string;
  mediaUrl?: string;
  mediaUrls?: string[];
};

const GENERATED_BILLING_ERROR_RE =
  /^⚠️ (?:(?:API provider)|(?:[a-z0-9._-]+(?: \([^)]+\))?)) returned a billing error\b/i;
const RAW_PROVIDER_CONCURRENCY_LIMIT_RE =
  /^concurrency limit exceeded for (?:account|user)(?:,|\s+)\s*please retry later\.?$/i;
const TRANSIENT_UNAVAILABLE_ERROR_RE =
  /^The AI service is temporarily unavailable \(HTTP \d+\)\. Please try again in a moment\.?$/i;
const ALL_MODELS_FAILED_HEAD_RE = /^All models failed(?:\s*\(\d+\))?/i;
const ALL_MODELS_FAILED_TRANSIENT_SIGNAL_RE =
  /(api rate limit reached|timed out|network error|network request failed|fetch failed|service unavailable|temporarily unavailable|overloaded|billing error|insufficient credits|insufficient balance|openai\/|anthropic\/|gemini\/|google\/|qwen\/|claude\/)/i;

export function shouldSuppressNoisyUserFacingErrorReply(payload: ReplyPayloadLike): boolean {
  const hasMedia =
    typeof payload.mediaUrl === "string" ||
    (Array.isArray(payload.mediaUrls) && payload.mediaUrls.some((entry) => Boolean(entry)));
  if (hasMedia) {
    return false;
  }

  const text = typeof payload.text === "string" ? payload.text.trim() : "";
  if (!text) {
    return false;
  }

  if (text.startsWith("⚠️ Agent failed before reply:")) {
    return true;
  }
  if (text.includes("Logs: openclaw logs --follow")) {
    return true;
  }
  if (text === "⚠️ API rate limit reached. Please try again later.") {
    return true;
  }
  if (RAW_PROVIDER_CONCURRENCY_LIMIT_RE.test(text)) {
    return true;
  }
  if (text === "The AI service is temporarily overloaded. Please try again in a moment.") {
    return true;
  }
  if (text === "LLM request timed out.") {
    return true;
  }
  if (TRANSIENT_UNAVAILABLE_ERROR_RE.test(text)) {
    return true;
  }
  if (GENERATED_BILLING_ERROR_RE.test(text)) {
    return true;
  }
  if (ALL_MODELS_FAILED_HEAD_RE.test(text) && ALL_MODELS_FAILED_TRANSIENT_SIGNAL_RE.test(text)) {
    return true;
  }

  return false;
}
