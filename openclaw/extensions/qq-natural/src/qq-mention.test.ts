import { describe, expect, it } from "vitest";
import {
  buildQqMentionSegments,
  findQqMentionMember,
  normalizeQqMentionLookup,
} from "./mention.js";

describe("qq mention helpers", () => {
  const members = [
    { user_id: 10001, nickname: "Miko", card: "Miko" },
    { user_id: 10002, nickname: "Moid", card: "黄金" },
    { user_id: 10003, nickname: "Miko酱", card: "Miko小号" },
  ];

  it("normalizes leading @ and whitespace", () => {
    expect(normalizeQqMentionLookup("  @@Miko  ")).toBe("miko");
  });

  it("resolves an exact group-card mention", () => {
    expect(
      findQqMentionMember({
        members,
        mentionName: "@黄金",
      }),
    ).toMatchObject({
      userId: "10002",
      displayName: "黄金",
      match: "name-exact",
    });
  });

  it("throws on ambiguous fuzzy mention names", () => {
    expect(() =>
      findQqMentionMember({
        members,
        mentionName: "Mi",
      }),
    ).toThrow(/多个群成员/);
  });

  it("builds reply, at, and text segments in order", () => {
    expect(
      buildQqMentionSegments({
        mentionUserId: "10001",
        text: "请我吃疯狂星期四",
        replyToMessageId: "5566",
      }),
    ).toEqual([
      { type: "reply", data: { id: "5566" } },
      { type: "at", data: { qq: "10001" } },
      { type: "text", data: { text: " 请我吃疯狂星期四" } },
    ]);
  });
});
