import path from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { setQqRuntime } from "./runtime.js";
import { __testing, debugInjectQqInboundMessage } from "./service.js";

const TEST_IMAGE_PATH = path.resolve(process.cwd(), "README-header.png");
const TEST_SESSION_STORE = "/tmp/openclaw-qq-deferred-meme-followup-session-store.json";
const TEST_CFG = {
  channels: {
    qq: {
      enabled: true,
      selfId: "2509109290",
    },
  },
  session: {
    store: TEST_SESSION_STORE,
  },
  gateway: {
    port: 18789,
  },
};

const TEST_API = {
  logger: {
    info() {},
    debug() {},
    warn() {},
    error() {},
  },
};

function buildPrivateEvent(params: {
  messageId: number;
  time: number;
  userId: number;
  text?: string;
  imagePath?: string;
}) {
  const message: Array<{ type: string; data?: Record<string, string> }> = [];
  if (params.text?.trim()) {
    message.push({
      type: "text",
      data: { text: params.text.trim() },
    });
  }
  if (params.imagePath?.trim()) {
    message.push({
      type: "image",
      data: { file: params.imagePath.trim() },
    });
  }
  return {
    post_type: "message" as const,
    self_id: 2509109290,
    message_id: params.messageId,
    message_type: "private" as const,
    sub_type: "friend",
    time: params.time,
    user_id: params.userId,
    raw_message: params.text?.trim() ?? "",
    message,
    sender: {
      user_id: params.userId,
      nickname: "tester",
      card: "tester",
    },
  };
}

function buildGroupMentionEvent(params: {
  messageId: number;
  time: number;
  userId: number;
  groupId: number;
  text: string;
}) {
  return {
    post_type: "message" as const,
    self_id: 2509109290,
    message_id: params.messageId,
    message_type: "group" as const,
    sub_type: "normal",
    time: params.time,
    group_id: params.groupId,
    user_id: params.userId,
    raw_message: params.text,
    message: [
      { type: "at", data: { qq: "2509109290" } },
      { type: "text", data: { text: params.text } },
    ],
    sender: {
      user_id: params.userId,
      nickname: "tester",
      card: "tester",
    },
  };
}

describe("qq deferred meme followup", () => {
  beforeEach(() => {
    __testing.resetQqConversationStateForTest();
    setQqRuntime({
      config: {
        loadConfig() {
          return TEST_CFG;
        },
      },
      channel: {
        routing: {
          resolveAgentRoute() {
            return {
              sessionKey: "agent:fusion-main:test",
              agentId: "fusion-main",
            };
          },
        },
        session: {
          resolveStorePath() {
            return TEST_SESSION_STORE;
          },
          readSessionUpdatedAt() {
            return Date.now() - 1_000;
          },
          recordInboundSession() {},
        },
        reply: {
          resolveEnvelopeFormatOptions() {
            return {};
          },
          formatAgentEnvelope({ body }: { body: string }) {
            return body;
          },
          finalizeInboundContext(payload: Record<string, unknown>) {
            return payload;
          },
          dispatchReplyWithBufferedBlockDispatcher() {
            throw new Error("should not dispatch in dry run");
          },
        },
      },
    } as never);
  });

  it("turns a prior text-only meme request plus a later image upload into an immediate meme path", async () => {
    const userId = 1446437177;
    const nowSeconds = Math.floor(Date.now() / 1000);

    const first = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildPrivateEvent({
        messageId: 1001,
        time: nowSeconds,
        userId,
        text: "给我做个表情包 文字添加 怒",
      }),
    });

    expect(first).toMatchObject({
      ok: true,
      decision: {
        action: "dispatch",
      },
    });

    const second = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildPrivateEvent({
        messageId: 1002,
        time: nowSeconds + 60,
        userId,
        imagePath: TEST_IMAGE_PATH,
      }),
    });

    expect(second).toMatchObject({
      ok: true,
      raw_body: "用户发送了1张图片",
      decision: {
        action: "dispatch_immediate",
        mode: "deferred_meme_from_followup_image",
        reason: "deferred-meme-caption",
      },
      bound_media: {
        binding_source: "current-message",
        type: "image",
      },
    });
  });

  it("does not let direct-only study mode suppress mentioned group chat", async () => {
    const cfg = {
      ...TEST_CFG,
      channels: {
        qq: {
          ...TEST_CFG.channels.qq,
          studyMode: {
            enabled: true,
            directOnly: true,
          },
          groups: {
            "123456": {
              requireMention: true,
            },
          },
        },
      },
    };
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: cfg as never,
      dryRun: true,
      event: buildGroupMentionEvent({
        messageId: 2001,
        time: Math.floor(Date.now() / 1000),
        userId: 1446437177,
        groupId: 123456,
        text: " 在吗",
      }),
    });

    expect(result).toMatchObject({
      ok: true,
      conversation_key: "qq:default:group:123456",
      decision: {
        action: "dispatch",
      },
    });
  });
});
