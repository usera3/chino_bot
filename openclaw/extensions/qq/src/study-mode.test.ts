import { describe, expect, it } from "vitest";
import type { ResolvedQqAccount } from "./types.js";
import {
  buildSyntheticDirectStudyBurstEvent,
  buildQqStudyModeSystemPrompt,
  resolveQqReplySkillFilter,
  resolveQqStudyModeConfig,
  shouldPassNativeImageRequestToAgent,
  shouldBufferInboundQqStudyBurst,
  shouldSkipInboundQqMessageForStudyMode,
} from "./service.js";
import type { OneBotMessageEvent, ParsedQqMessage } from "./types.js";

function createAccount(overrides?: Partial<ResolvedQqAccount>): ResolvedQqAccount {
  return {
    accountId: "default",
    enabled: true,
    name: "QQ",
    selfId: "123456",
    autoLaunch: false,
    preventIdleSleep: false,
    executablePath: "/Applications/QQ.app/Contents/MacOS/QQ",
    launchArgs: [],
    listenHost: "127.0.0.1",
    listenPort: 8080,
    websocketPath: "/onebot/v11/ws",
    config: {},
    ...overrides,
  };
}

describe("qq study mode", () => {
  it("resolves study mode defaults when enabled", () => {
    const account = createAccount({
      config: {
        studyMode: {
          enabled: true,
        },
      },
    });

    expect(resolveQqStudyModeConfig(account)).toEqual({
      enabled: true,
      directOnly: true,
      autoSolveLikelyProblemImages: true,
      alwaysRenderHtml: true,
      answerStyle: "exam",
      skills: [
        "qq-problem-solving",
        "qq-fusion-actions",
        "chinobot-capability-router",
        "qq-native",
      ],
      systemPrompt: undefined,
    });
  });

  it("skips group messages when study mode is direct-only", () => {
    const account = createAccount({
      config: {
        studyMode: {
          enabled: true,
        },
      },
    });

    expect(
      shouldSkipInboundQqMessageForStudyMode({
        account,
        chatType: "group",
      }),
    ).toBe(true);
    expect(
      shouldSkipInboundQqMessageForStudyMode({
        account,
        chatType: "direct",
      }),
    ).toBe(false);
  });

  it("builds a study-mode prompt that enforces html rendering", () => {
    const account = createAccount({
      config: {
        studyMode: {
          enabled: true,
          systemPrompt: "Use concise exam formatting.",
        },
      },
    });

    const prompt = buildQqStudyModeSystemPrompt({
      account,
      chatType: "direct",
      hasImage: true,
    });

    expect(prompt).toContain("QQ study mode is active");
    expect(prompt).toContain("chinobot_render_html");
    expect(prompt).toContain("Use concise exam formatting.");
    expect(prompt).toContain("Inspect the image first");
  });

  it("routes direct-chat skill filters through study mode", () => {
    const account = createAccount({
      config: {
        groups: {
          "673105016": {
            skills: ["group-skill"],
          },
        },
        studyMode: {
          enabled: true,
          skills: ["qq-problem-solving", "chinobot-capability-router"],
        },
      },
    });

    expect(
      resolveQqReplySkillFilter({
        account,
        chatType: "group",
        groupId: "673105016",
      }),
    ).toEqual(["group-skill"]);
    expect(
      resolveQqReplySkillFilter({
        account,
        chatType: "direct",
      }),
    ).toEqual(["qq-problem-solving", "chinobot-capability-router"]);
  });

  it("passes contextual study image-generation requests through to the agent", () => {
    expect(shouldPassNativeImageRequestToAgent("试试用大模型自带的生图能力做这题")).toBe(
      true,
    );
    expect(
      shouldPassNativeImageRequestToAgent("对，你就试试用大模型自带的生图能力去渲染那题的答案试试"),
    ).toBe(true);
    expect(shouldPassNativeImageRequestToAgent("画图西瓜，用大模型自带的生图功能")).toBe(
      false,
    );
    expect(shouldPassNativeImageRequestToAgent("生成图片：一只猫在月亮上睡觉")).toBe(false);
  });

  it("buffers direct image turns into study bursts", () => {
    const account = createAccount({
      config: {
        studyMode: {
          enabled: true,
        },
      },
    });

    expect(
      shouldBufferInboundQqStudyBurst({
        account,
        chatType: "direct",
        senderId: "10001",
        parsed: {
          text: "",
          isReply: false,
          wasMentioned: false,
          mentionIds: [],
          imageUrls: ["https://example.com/q1.jpg"],
        },
      }),
    ).toBe(true);
  });

  it("builds one synthetic event from a direct-study burst packet", () => {
    const firstEvent: OneBotMessageEvent = {
      post_type: "message",
      self_id: 123456,
      message_type: "private",
      user_id: 10001,
      message_id: 1,
      time: 100,
      message: [],
    };
    const secondEvent: OneBotMessageEvent = {
      post_type: "message",
      self_id: 123456,
      message_type: "private",
      user_id: 10001,
      message_id: 2,
      time: 101,
      message: [],
    };
    const firstParsed: ParsedQqMessage = {
      text: "",
      isReply: false,
      wasMentioned: false,
      mentionIds: [],
      imageUrls: ["https://example.com/page2.jpg"],
    };
    const secondParsed: ParsedQqMessage = {
      text: "第二张其实是第一页",
      isReply: false,
      wasMentioned: false,
      mentionIds: [],
      imageUrls: ["https://example.com/page1.jpg"],
    };

    const synthetic = buildSyntheticDirectStudyBurstEvent([
      { event: firstEvent, parsed: firstParsed },
      { event: secondEvent, parsed: secondParsed },
    ]);

    expect(synthetic.message_type).toBe("private");
    expect(Array.isArray(synthetic.message)).toBe(true);
    const segments = synthetic.message as Array<{ type: string; data?: Record<string, string> }>;
    expect(segments.filter((segment) => segment.type === "image")).toHaveLength(2);
    expect(
      segments.some(
        (segment) =>
          segment.type === "text" &&
          String(segment.data?.text ?? "").includes("第二张其实是第一页"),
      ),
    ).toBe(true);
  });
});
