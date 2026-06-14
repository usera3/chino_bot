import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { __testing } from "./service.js";

const tempFiles: string[] = [];

afterEach(() => {
  for (const file of tempFiles.splice(0)) {
    fs.rmSync(file, { force: true });
  }
});

describe("qq codex/openclaw brain switch commands", () => {
  it("parses /codex with dotted separator and inline body", () => {
    expect(__testing.parseQqBrainCommand("/codex. 帮我解释一下这个报错")).toEqual({
      target: "codex",
      body: "帮我解释一下这个报错",
      explicitSwitch: true,
    });
  });

  it("parses /chat as openclaw switch without body", () => {
    expect(__testing.parseQqBrainCommand("/chat.")).toEqual({
      target: "openclaw",
      body: "",
      explicitSwitch: true,
    });
  });

  it("keeps per-conversation target state", () => {
    const key = `test:${Date.now()}:${Math.random()}`;
    expect(
      __testing.resolveQqBrainTarget({ conversationKey: key, rawBody: "/codex" }),
    ).toMatchObject({ target: "codex", explicitSwitch: true });
    expect(
      __testing.resolveQqBrainTarget({ conversationKey: key, rawBody: "继续" }),
    ).toMatchObject({ target: "codex", body: "继续", explicitSwitch: false });
    expect(
      __testing.resolveQqBrainTarget({ conversationKey: key, rawBody: "/chat" }),
    ).toMatchObject({ target: "openclaw", explicitSwitch: true });
  });

  it("scopes /chat and /codex state to each private user conversation", () => {
    const accountId = "default";
    const userAEvent = {
      post_type: "message",
      message_type: "private",
      sub_type: "friend",
      time: 1,
      self_id: 2509109290,
      user_id: 111,
      message_id: 1,
      message: [],
      raw_message: "",
      font: 0,
      sender: { user_id: 111, nickname: "A" },
    } as const;
    const userBEvent = {
      ...userAEvent,
      user_id: 222,
      message_id: 2,
      sender: { user_id: 222, nickname: "B" },
    } as const;
    const groupEvent = {
      ...userAEvent,
      message_type: "group",
      sub_type: "normal",
      group_id: 333,
      message_id: 3,
    } as const;

    const userAKey = __testing.buildQqConversationKey(accountId, userAEvent);
    const userBKey = __testing.buildQqConversationKey(accountId, userBEvent);
    const groupKey = __testing.buildQqConversationKey(accountId, groupEvent);

    expect(userAKey).toBe("qq:default:direct:111");
    expect(userBKey).toBe("qq:default:direct:222");
    expect(groupKey).toBe("qq:default:group:333");
    expect(__testing.resolveQqBrainTarget({ conversationKey: userAKey, rawBody: "/codex" })).toMatchObject({
      target: "codex",
      explicitSwitch: true,
    });
    expect(__testing.resolveQqBrainTarget({ conversationKey: userBKey, rawBody: "继续" })).toMatchObject({
      target: "openclaw",
      explicitSwitch: false,
    });
    expect(__testing.resolveQqBrainTarget({ conversationKey: groupKey, rawBody: "继续" })).toMatchObject({
      target: "openclaw",
      explicitSwitch: false,
    });
  });

  it("parses natural codex reasoning mode switches", () => {
    expect(__testing.parseQqCodexReasoningCommand("切到最高思考模式")).toEqual({
      effort: "xhigh",
      label: "最高",
      body: "",
    });
    expect(__testing.parseQqCodexReasoningCommand("快一点思考，直接回答这个题")).toEqual({
      effort: "low",
      label: "快速",
      body: "直接回答这个题",
    });
    expect(__testing.parseQqCodexReasoningCommand("/codex 用深度思考模式证明一下")).toEqual({
      effort: "high",
      label: "深度",
      body: "证明一下",
    });
  });

  it("detects natural new-chat reset commands for codex", () => {
    expect(__testing.isQqCodexNewChatCommand("开启新聊天窗口")).toBe(true);
    expect(__testing.isQqCodexNewChatCommand("/codex new chat")).toBe(true);
    expect(__testing.isQqCodexNewChatCommand("清空上下文")).toBe(true);
    expect(__testing.isQqCodexNewChatCommand("新聊天里继续解释这个题")).toBe(false);
  });

  it("defaults codex reasoning effort to highest", () => {
    expect(__testing.normalizeQqCodexReasoningEffort(undefined)).toBe("xhigh");
    expect(__testing.labelQqCodexReasoningEffort("xhigh")).toBe("最高");
  });

  it("builds repeatable codex image arguments from existing files only", () => {
    const imagePath = path.join(os.tmpdir(), `qq-codex-image-${Date.now()}-${Math.random()}.png`);
    fs.writeFileSync(imagePath, "not really an image");
    tempFiles.push(imagePath);

    expect(
      __testing.buildQqCodexImageArgs([
        imagePath,
        imagePath,
        "/tmp/definitely-missing-qq-codex-image.png",
        "",
      ]),
    ).toEqual([`--image=${imagePath}`]);
  });

  it("filters codex sent placeholders instead of sending machine confirmations", () => {
    expect(__testing.chunkQqCodexReply("QQ_CODEX_SENT")).toEqual([]);
    expect(__testing.chunkQqCodexReply("已发送。")).toEqual([]);
    expect(__testing.chunkQqCodexReply("已回复。")).toEqual([]);
    expect(__testing.chunkQqCodexReply("我是 Miko")).toEqual(["我是 Miko"]);
  });

  it("compacts very large codex prompts by preserving head and tail", () => {
    const prompt = `SYSTEM-RULES\n${"A".repeat(90_000)}\nLATEST-USER-MESSAGE`;
    const compacted = __testing.compactQqCodexPromptForModelLimit(prompt);

    expect(compacted.length).toBeLessThan(prompt.length);
    expect(compacted).toContain("SYSTEM-RULES");
    expect(compacted).toContain("LATEST-USER-MESSAGE");
    expect(compacted).toContain("QQ-Codex context compacted");
  });

  it("asks codex to render image-question answers as exam-ready cards", () => {
    const prompt = __testing.buildQqCodexPrompt({
      event: {
        post_type: "message",
        message_type: "private",
        sub_type: "friend",
        time: 1,
        self_id: 2509109290,
        user_id: 1446437177,
        message_id: 123,
        message: [],
        raw_message: "",
        font: 0,
        sender: { user_id: 1446437177, nickname: "空白" },
      },
      body: "用户发送了1张图片",
      senderName: "空白",
      imagePaths: ["/tmp/question.jpg"],
      reasoningEffort: "xhigh",
    });

    expect(prompt).toContain("默认按考试作答模式处理");
    expect(prompt).toContain("适合直接写进试卷/作业");
    expect(prompt).toContain("qq_codex_bridge render-html-send --file");
    expect(prompt).toContain("qq_codex_bridge send-mention --target group:群号 --user QQ号");
    expect(prompt).toContain("qq_codex_bridge voice --text '要说的话'");
    expect(prompt).toContain("请智能判断回复形式，不必每次都纯文字");
    expect(prompt).toContain("私聊里可以主动使用你拥有的 QQ 工具来优化聊天体验");
    expect(prompt).toContain("私聊主动工具策略");
    expect(prompt).toContain("不适合主动发语音的情况");
    expect(prompt).toContain("qq_codex_bridge timeout --group 群号 --user QQ号");
    expect(prompt).toContain("qq_codex_bridge forward --target group:群号 --node");
    expect(prompt).toContain("qq_codex_bridge like --user QQ号");
    expect(prompt).toContain("最终文本只输出 `QQ_CODEX_SENT`");
    expect(prompt).toContain("当前 Codex 思考模式：最高（xhigh）");
    expect(prompt).toContain("当前默认人设是 Miko");
    expect(prompt).toContain("Miko 的说话方式");
    expect(prompt).not.toContain("群聊自然聊天风格仅在当前是 QQ 群聊时启用");
  });

  it("adds Miko persona and group-only natural chat style for group codex turns", () => {
    const prompt = __testing.buildQqCodexPrompt({
      event: {
        post_type: "message",
        message_type: "group",
        sub_type: "normal",
        time: 1,
        self_id: 2509109290,
        group_id: 987654321,
        user_id: 1446437177,
        message_id: 456,
        message: [],
        raw_message: "戳一戳",
        font: 0,
        sender: { user_id: 1446437177, nickname: "空白" },
      },
      body: "戳一戳",
      senderName: "空白",
      reasoningEffort: "xhigh",
      followupContext: "本条消息被回话追踪判定为同一说话人的续聊：请按延续上下文回复，但保持简短。",
    });

    expect(prompt).toContain("当前默认人设是 Miko");
    expect(prompt).toContain("Miko 的说话方式：机灵、亲近、稍微俏皮");
    expect(prompt).toContain("群聊自然聊天风格仅在当前是 QQ 群聊时启用");
    expect(prompt).not.toContain("私聊里可以主动使用你拥有的 QQ 工具来优化聊天体验");
    expect(prompt).toContain("1 句为主，必要时最多 2 句");
    expect(prompt).toContain("又偷摸我啊");
    expect(prompt).toContain("本条消息被回话追踪判定为同一说话人的续聊");
  });
});
