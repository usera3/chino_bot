import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ensureDefaultQqSocialAgencyFiles } from "./social-agency.js";
import { setQqRuntime } from "./runtime.js";
import { __testing, debugInjectQqInboundMessage } from "./service.js";

const TEST_SESSION_STORE = "/tmp/openclaw-qq-social-agency-verification-session-store.json";
const TEST_IMAGE_FILE = "/Users/mozi100/PycharmProjects/openclaw/dist/control-ui/apple-touch-icon.png";
const DEFAULT_TEST_WORKSPACE = "/Users/mozi100/PycharmProjects/openclaw";
const tempWorkspaces: string[] = [];
const TEST_CFG = {
  agents: {
    defaults: {
      workspace: DEFAULT_TEST_WORKSPACE,
    },
  },
  channels: {
    qq: {
      enabled: true,
      selfId: "2509109290",
      naturalChat: {
        enabled: true,
        applyToGroups: true,
        applyToDirect: true,
        defaultPersona: "miko",
      },
      groups: {
        "673105016": {
          enabled: true,
          requireMention: true,
          socialJoinEnabled: true,
          socialJoinCooldownMinutes: 0,
        },
      },
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
  config: TEST_CFG,
  logger: {
    info() {},
    debug() {},
    warn() {},
    error() {},
  },
  resolvePath(input: string) {
    return input;
  },
};

function createIsolatedSocialWorkspace() {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-qq-social-workspace-"));
  tempWorkspaces.push(workspace);
  const socialRoot = path.join(workspace, "memory", "group-social");
  const groupDir = path.join(socialRoot, "ciyuan-fusu-erqu");
  fs.mkdirSync(groupDir, { recursive: true });
  fs.writeFileSync(
    path.join(socialRoot, "target-group.json"),
    `${JSON.stringify({ groupId: "673105016" }, null, 2)}\n`,
    "utf8",
  );
  fs.writeFileSync(
    path.join(groupDir, "norms.json"),
    `${JSON.stringify({ groupId: "673105016", groupName: "次元复苏 二群" }, null, 2)}\n`,
    "utf8",
  );
  fs.writeFileSync(
    path.join(groupDir, "reply-style.json"),
    `${JSON.stringify({ groupId: "673105016", groupName: "次元复苏 二群" }, null, 2)}\n`,
    "utf8",
  );
  fs.writeFileSync(
    path.join(groupDir, "self-position.json"),
    `${JSON.stringify(
      {
        currentRole: "playful-companion",
        allowedPresence: "medium",
        attentionBudget: 0.76,
        playfulnessLevel: 0.68,
        protectivenessLevel: 0.52,
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
  fs.writeFileSync(
    path.join(groupDir, "appraisal.json"),
    `${JSON.stringify(
      {
        socialSafety: 0.9,
        dramaRisk: 0.04,
        groupNoise: 0.8,
        recentAcceptance: 0.44,
        novelty: 0.85,
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
  ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");
  return workspace;
}

function buildGroupEvent(params: {
  messageId: number;
  time: number;
  userId: number;
  senderName?: string;
  text?: string;
  mentionSelf?: boolean;
  imageFile?: string;
}) {
  const message: Array<{ type: string; data?: Record<string, string> }> = [];
  if (params.mentionSelf) {
    message.push({
      type: "at",
      data: { qq: "2509109290" },
    });
  }
  if (params.text?.trim()) {
    message.push({
      type: "text",
      data: { text: params.mentionSelf ? ` ${params.text.trim()}` : params.text.trim() },
    });
  }
  if (params.imageFile?.trim()) {
    message.push({
      type: "image",
      data: { file: params.imageFile.trim() },
    });
  }
  return {
    post_type: "message" as const,
    self_id: 2509109290,
    message_id: params.messageId,
    message_type: "group" as const,
    sub_type: "normal",
    time: params.time,
    user_id: params.userId,
    group_id: 673105016,
    raw_message: params.text?.trim() ?? "",
    message,
    sender: {
      user_id: params.userId,
      nickname: params.senderName ?? `u${params.userId}`,
      card: params.senderName ?? `u${params.userId}`,
    },
  };
}

describe("qq social agency verification", () => {
  beforeEach(() => {
    __testing.resetQqConversationStateForTest();
    TEST_CFG.agents.defaults.workspace = DEFAULT_TEST_WORKSPACE;
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
              sessionKey: "agent:main:qq:group:673105016",
              agentId: "main",
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

  it("verifies repeated touch escalates into a social-agency card move", async () => {
    const now = Math.floor(Date.now() / 1000);
    await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1001,
        time: now,
        userId: 2324504172,
        senderName: "伊落",
        text: "摸摸",
      }),
    });
    await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1002,
        time: now + 5,
        userId: 2324504172,
        senderName: "伊落",
        text: "又摸一下",
      }),
    });
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1003,
        time: now + 10,
        userId: 2324504172,
        senderName: "伊落",
        text: "偷偷摸了你一下",
      }),
    });
    const decision = (result as { decision?: { mode?: string; action?: string } }).decision;
    expect(decision?.action).toBe("dispatch_immediate");
    expect(decision?.mode).toBe("social_agency_touch_reaction");
  });

  it("verifies repeated touching by the same sender can escalate to a timeout move", async () => {
    const now = Math.floor(Date.now() / 1000);
    await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1101,
        time: now,
        userId: 2324504172,
        senderName: "伊落",
        text: "摸摸",
      }),
    });
    await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1102,
        time: now + 5,
        userId: 2324504172,
        senderName: "伊落",
        text: "又摸一下",
      }),
    });
    await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1103,
        time: now + 10,
        userId: 2324504172,
        senderName: "伊落",
        text: "戳戳",
      }),
    });
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1104,
        time: now + 15,
        userId: 2324504172,
        senderName: "伊落",
        text: "偷偷摸了你一下",
      }),
    });
    const decision = (result as { decision?: { mode?: string; action?: string } }).decision;
    expect(decision?.action).toBe("dispatch_immediate");
    expect(decision?.mode).toBe("social_agency_touch_timeout");
  });

  it("verifies touch dogpiles across multiple senders can also escalate to a timeout move", async () => {
    const isolatedWorkspace = createIsolatedSocialWorkspace();
    TEST_CFG.agents.defaults.workspace = isolatedWorkspace;
    const now = Math.floor(Date.now() / 1000);
    for (const [messageId, offset, userId, senderName, text] of [
      [1201, 0, 2324504172, "伊落", "摸摸"],
      [1202, 4, 516507077, "月", "又摸一下"],
      [1203, 8, 2275999791, "仓鼠姬", "戳戳"],
      [1204, 12, 2324504172, "伊落", "偷偷摸了你一下"],
    ] as const) {
      await debugInjectQqInboundMessage({
        api: TEST_API as never,
        cfg: TEST_CFG as never,
        dryRun: true,
        event: buildGroupEvent({
          messageId,
          time: now + offset,
          userId,
          senderName,
          text,
        }),
      });
    }
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 1205,
        time: now + 16,
        userId: 1446437177,
        senderName: "空白",
        text: "我也摸一下",
      }),
    });
    const decision = (result as { decision?: { mode?: string; action?: string } }).decision;
    expect(decision?.action).toBe("dispatch_immediate");
    expect(decision?.mode).toBe("social_agency_touch_timeout");
  });

  it("verifies high-energy absurd banter becomes a social-agency surprise move", async () => {
    const now = Math.floor(Date.now() / 1000);
    for (const [offset, userId, senderName, text] of [
      [0, 516507077, "月", "咕咕嘎嘎"],
      [4, 2324504172, "伊落", "草"],
      [8, 1446437177, "空白", "笑死"],
    ] as const) {
      await debugInjectQqInboundMessage({
        api: TEST_API as never,
        cfg: TEST_CFG as never,
        dryRun: true,
        event: buildGroupEvent({
          messageId: 2000 + offset,
          time: now + offset,
          userId,
          senderName,
          text,
        }),
      });
    }
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 2009,
        time: now + 12,
        userId: 516507077,
        senderName: "月",
        text: "咕咕嘎嘎这什么东西啊",
      }),
    });
    const decision = (result as { decision?: { mode?: string; action?: string } }).decision;
    expect(decision?.action).toBe("dispatch");
    expect(decision?.mode?.startsWith("social_agency_")).not.toBe(true);
  });

  it("verifies avatar prompt opens a social-agency avatar surprise path", async () => {
    const now = Math.floor(Date.now() / 1000);
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 3001,
        time: now,
        userId: 516507077,
        senderName: "月",
        text: "我这头像怎么样",
      }),
    });
    const decision = (result as { decision?: { mode?: string; action?: string } }).decision;
    expect(decision?.action).toBe("dispatch_immediate");
    expect(decision?.mode).toBe("social_agency_avatar_meme");
  });

  it("verifies a playful current image can become a social-agency image meme", async () => {
    const isolatedWorkspace = createIsolatedSocialWorkspace();
    TEST_CFG.agents.defaults.workspace = isolatedWorkspace;
    const now = Math.floor(Date.now() / 1000);
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 3501,
        time: now,
        userId: 1446437177,
        senderName: "空白",
        text: "这张也太怪了吧",
        imageFile: TEST_IMAGE_FILE,
      }),
    });
    const decision = (result as { decision?: { mode?: string; action?: string } }).decision;
    expect(decision?.action).toBe("dispatch_immediate");
    expect(decision?.mode).toBe("social_agency_current_image_meme");
  });

  it("verifies serious help does not enter a social-agency immediate move", async () => {
    const now = Math.floor(Date.now() / 1000);
    const result = await debugInjectQqInboundMessage({
      api: TEST_API as never,
      cfg: TEST_CFG as never,
      dryRun: true,
      event: buildGroupEvent({
        messageId: 4001,
        time: now,
        userId: 2275999791,
        senderName: "仓鼠姬",
        text: "流鼻血该怎么办",
      }),
    });
    const decision = (result as { decision?: { mode?: string; action?: string } }).decision;
    expect(decision?.mode?.startsWith("social_agency_")).not.toBe(true);
  });

  afterEach(() => {
    TEST_CFG.agents.defaults.workspace = DEFAULT_TEST_WORKSPACE;
    for (const dir of tempWorkspaces.splice(0)) {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});
