import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  buildQqSocialAgencyPlan,
  ensureDefaultQqSocialAgencyFiles,
  recordQqSocialAgencyOutcome,
} from "./social-agency.js";

const tempDirs: string[] = [];

function createTempGroupDir() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "qq-social-agency-"));
  tempDirs.push(dir);
  return dir;
}

afterEach(() => {
  for (const dir of tempDirs.splice(0)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

describe("qq social agency", () => {
  it("treats repeated touching as a surprise-capable play window", () => {
    const groupDir = createTempGroupDir();
    ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");

    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        groupDir,
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.72,
          playfulnessLevel: 0.61,
        },
        appraisal: {
          socialSafety: 0.88,
          dramaRisk: 0.05,
          groupNoise: 0.8,
          recentAcceptance: 0.42,
          novelty: 0.82,
        },
      },
      senderId: "2324504172",
      senderName: "伊落",
      senderProfile: {
        qqId: "2324504172",
        displayName: "伊落",
        relationshipWeight: 0.45,
        trust: 0.82,
        teasingTolerance: 0.86,
        messageCount: 12,
      },
      rawBody: "摸摸",
      parsed: {
        text: "摸摸",
        isReply: false,
        replyToMessageId: undefined,
        wasMentioned: false,
        mentionIds: [],
        imageUrls: [],
        mediaSegments: [],
        hasOnlyMediaLike: false,
      },
      recentMessages: [
        {
          senderId: "2324504172",
          text: "摸摸",
          createdAt: Date.now() - 90_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "516507077",
          text: "又来占我便宜",
          createdAt: Date.now() - 50_000,
          wasMentioned: false,
          isReply: false,
        },
      ],
      nowMs: Date.now(),
    });

    expect(plan.opportunity?.type).toBe("touch_tease_window");
    expect(plan.mode).toBe("light_surprise");
    expect(plan.allowAmbientJoin).toBe(true);
    expect(plan.selectedRecipe?.recipe.id).toBe("touch_reaction");
  });

  it("escalates same-sender touch spam into a timeout recipe", () => {
    const groupDir = createTempGroupDir();
    ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");
    const nowMs = Date.now();

    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        groupDir,
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.78,
          playfulnessLevel: 0.64,
        },
        appraisal: {
          socialSafety: 0.9,
          dramaRisk: 0.04,
          groupNoise: 0.82,
          recentAcceptance: 0.46,
          novelty: 0.83,
        },
      },
      senderId: "2324504172",
      senderName: "伊落",
      senderProfile: {
        qqId: "2324504172",
        displayName: "伊落",
        relationshipWeight: 0.48,
        trust: 0.84,
        teasingTolerance: 0.88,
        messageCount: 18,
      },
      rawBody: "偷偷摸了你一下",
      parsed: {
        text: "偷偷摸了你一下",
        isReply: false,
        replyToMessageId: undefined,
        wasMentioned: false,
        mentionIds: [],
        imageUrls: [],
        mediaSegments: [],
        hasOnlyMediaLike: false,
      },
      recentMessages: [
        {
          senderId: "2324504172",
          text: "摸摸",
          createdAt: nowMs - 180_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "2324504172",
          text: "又摸一下",
          createdAt: nowMs - 120_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "2324504172",
          text: "戳戳",
          createdAt: nowMs - 60_000,
          wasMentioned: false,
          isReply: false,
        },
      ],
      nowMs,
    });

    expect(plan.signals).toContain("touch_overload");
    expect(plan.mode).toBe("light_surprise");
    expect(plan.selectedRecipe?.recipe.id).toBe("touch_timeout");
  });

  it("treats multi-sender touch dogpiles as overload too", () => {
    const groupDir = createTempGroupDir();
    ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");
    const nowMs = Date.now();

    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        groupDir,
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.79,
          playfulnessLevel: 0.63,
        },
        appraisal: {
          socialSafety: 0.9,
          dramaRisk: 0.04,
          groupNoise: 0.84,
          recentAcceptance: 0.45,
          novelty: 0.82,
        },
      },
      senderId: "1446437177",
      senderName: "空白",
      senderProfile: {
        qqId: "1446437177",
        displayName: "空白",
        relationshipWeight: 0.46,
        trust: 0.83,
        teasingTolerance: 0.84,
        messageCount: 15,
      },
      rawBody: "我也摸一下",
      parsed: {
        text: "我也摸一下",
        isReply: false,
        replyToMessageId: undefined,
        wasMentioned: false,
        mentionIds: [],
        imageUrls: [],
        mediaSegments: [],
        hasOnlyMediaLike: false,
      },
      recentMessages: [
        {
          senderId: "2324504172",
          text: "摸摸",
          createdAt: nowMs - 150_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "516507077",
          text: "又摸一下",
          createdAt: nowMs - 120_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "2275999791",
          text: "戳戳",
          createdAt: nowMs - 90_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "2324504172",
          text: "偷偷摸了你一下",
          createdAt: nowMs - 45_000,
          wasMentioned: false,
          isReply: false,
        },
      ],
      nowMs,
    });

    expect(plan.signals).toContain("touch_dogpile");
    expect(plan.signals).toContain("touch_overload");
    expect(plan.mode).toBe("light_surprise");
    expect(plan.selectedRecipe?.recipe.id).toBe("touch_timeout");
  });

  it("prefers image-based meme antics when a playful image arrives", () => {
    const groupDir = createTempGroupDir();
    ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");
    const nowMs = Date.now();

    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        groupDir,
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.74,
          playfulnessLevel: 0.66,
        },
        appraisal: {
          socialSafety: 0.9,
          dramaRisk: 0.05,
          groupNoise: 0.78,
          recentAcceptance: 0.4,
          novelty: 0.86,
        },
      },
      senderId: "1446437177",
      senderName: "空白",
      senderProfile: {
        qqId: "1446437177",
        displayName: "空白",
        relationshipWeight: 0.52,
        trust: 0.84,
        teasingTolerance: 0.82,
        messageCount: 14,
      },
      rawBody: "这张也太怪了吧",
      parsed: {
        text: "这张也太怪了吧",
        isReply: false,
        replyToMessageId: undefined,
        wasMentioned: false,
        mentionIds: [],
        imageUrls: ["/tmp/fake-image.png"],
        mediaSegments: [
          {
            type: "image",
            sourceType: "image",
            label: "图片",
            url: "/tmp/fake-image.png",
            preferredRef: "/tmp/fake-image.png",
            localFileResolved: true,
          },
        ],
        hasOnlyMediaLike: false,
      },
      recentMessages: [
        {
          senderId: "1446437177",
          text: "这张也太怪了吧",
          createdAt: nowMs - 70_000,
          wasMentioned: false,
          isReply: false,
        },
      ],
      nowMs,
    });

    expect(plan.opportunity?.type).toBe("visual_window");
    expect(plan.mode).toBe("light_surprise");
    expect(plan.selectedRecipe?.recipe.id).toBe("current_image_meme");
  });

  it("keeps serious help-seeking out of play mode", () => {
    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.7,
          playfulnessLevel: 0.5,
        },
        appraisal: {
          socialSafety: 0.9,
          dramaRisk: 0.02,
        },
      },
      senderId: "2275999791",
      senderName: "仓鼠姬",
      rawBody: "流鼻血该怎么办",
      parsed: {
        text: "流鼻血该怎么办",
        isReply: true,
        replyToMessageId: "1",
        wasMentioned: false,
        mentionIds: [],
        imageUrls: [],
        mediaSegments: [],
        hasOnlyMediaLike: false,
      },
      recentMessages: [],
      nowMs: Date.now(),
    });

    expect(plan.mode).toBe("social_reply");
    expect(plan.allowAmbientJoin).toBe(false);
    expect(plan.selectedRecipe).toBeNull();
    expect(plan.signals).toContain("serious_topic");
  });

  it("writes a positive outcome back into initiative state", () => {
    const groupDir = createTempGroupDir();
    ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");
    const nowMs = Date.now();
    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        groupDir,
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.72,
          playfulnessLevel: 0.61,
        },
        appraisal: {
          socialSafety: 0.88,
          dramaRisk: 0.05,
          groupNoise: 0.8,
          recentAcceptance: 0.42,
          novelty: 0.82,
        },
      },
      senderId: "2324504172",
      senderName: "伊落",
      rawBody: "摸摸",
      parsed: {
        text: "摸摸",
        isReply: false,
        replyToMessageId: undefined,
        wasMentioned: false,
        mentionIds: [],
        imageUrls: [],
        mediaSegments: [],
        hasOnlyMediaLike: false,
      },
      recentMessages: [
        {
          senderId: "2324504172",
          text: "摸摸",
          createdAt: nowMs - 120_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "516507077",
          text: "摸摸",
          createdAt: nowMs - 90_000,
          wasMentioned: false,
          isReply: false,
        },
      ],
      nowMs,
    });

    recordQqSocialAgencyOutcome({
      groupDir,
      groupId: "673105016",
      senderId: "2324504172",
      senderName: "伊落",
      plan,
      success: true,
      note: "unit-test",
      nowMs,
    });

    const initiative = JSON.parse(
      fs.readFileSync(path.join(groupDir, "initiative-state.json"), "utf8"),
    ) as { recentSuccessStreak?: number; recentMissStreak?: number; lastRecipeId?: string | null };
    expect(initiative.recentSuccessStreak).toBe(1);
    expect(initiative.recentMissStreak).toBe(0);
    expect(initiative.lastRecipeId).toBe(plan.selectedRecipe?.recipe.id ?? null);
  });

  it("keeps non-touch surprise modes suppressed while suppressionUntil is active", () => {
    const groupDir = createTempGroupDir();
    ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");
    const nowMs = Date.now();
    fs.writeFileSync(
      path.join(groupDir, "initiative-state.json"),
      JSON.stringify(
        {
          schemaVersion: 1,
          updatedAt: new Date(nowMs).toISOString(),
          groupId: "673105016",
          energy: 0.6,
          playfulness: 0.7,
          mischief: 0.6,
          shyness: 0.3,
          attentionHunger: 0.3,
          boredom: 0.2,
          protectiveness: 0.4,
          noveltySeeking: 0.7,
          recentSuccessStreak: 0,
          recentMissStreak: 2,
          lastSurpriseAt: null,
          lastRecipeId: null,
          suppressionUntil: new Date(nowMs + 20 * 60 * 1000).toISOString(),
        },
        null,
        2,
      ) + "\n",
      "utf8",
    );

    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        groupDir,
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.72,
          playfulnessLevel: 0.61,
        },
        appraisal: {
          socialSafety: 0.88,
          dramaRisk: 0.05,
          groupNoise: 0.8,
          recentAcceptance: 0.42,
          novelty: 0.82,
        },
      },
      senderId: "2324504172",
      senderName: "伊落",
      rawBody: "我这头像怎么样",
      parsed: {
        text: "我这头像怎么样",
        isReply: false,
        replyToMessageId: undefined,
        wasMentioned: false,
        mentionIds: [],
        imageUrls: [],
        mediaSegments: [],
        hasOnlyMediaLike: false,
      },
      recentMessages: [],
      nowMs,
    });

    expect(plan.opportunity?.type).toBe("visual_window");
    expect(plan.mode).toBe("silent");
    expect(plan.selectedRecipe).toBeNull();
  });

  it("does not surface merged-forward fake-log antics in high-energy absurd banter", () => {
    const groupDir = createTempGroupDir();
    ensureDefaultQqSocialAgencyFiles(groupDir, "673105016");
    const nowMs = Date.now();

    const plan = buildQqSocialAgencyPlan({
      groupProfile: {
        groupId: "673105016",
        groupDir,
        selfPosition: {
          allowedPresence: "medium",
          attentionBudget: 0.75,
          playfulnessLevel: 0.7,
        },
        appraisal: {
          socialSafety: 0.9,
          dramaRisk: 0.03,
          groupNoise: 0.86,
          recentAcceptance: 0.5,
          novelty: 0.88,
        },
      },
      senderId: "516507077",
      senderName: "月",
      senderProfile: {
        qqId: "516507077",
        displayName: "月",
        relationshipWeight: 0.52,
        trust: 0.84,
        teasingTolerance: 0.82,
        messageCount: 16,
      },
      rawBody: "咕咕嘎嘎这什么东西啊",
      parsed: {
        text: "咕咕嘎嘎这什么东西啊",
        isReply: false,
        replyToMessageId: undefined,
        wasMentioned: false,
        mentionIds: [],
        imageUrls: [],
        mediaSegments: [],
        hasOnlyMediaLike: false,
      },
      recentMessages: [
        {
          senderId: "516507077",
          text: "咕咕嘎嘎",
          createdAt: nowMs - 100_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "2324504172",
          text: "草",
          createdAt: nowMs - 80_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "1446437177",
          text: "笑死",
          createdAt: nowMs - 70_000,
          wasMentioned: false,
          isReply: false,
        },
        {
          senderId: "1114358696",
          text: "这都啥啊",
          createdAt: nowMs - 55_000,
          wasMentioned: false,
          isReply: false,
        },
      ],
      nowMs,
    });

    expect(plan.mode).toBe("light_surprise");
    expect(plan.candidates.length).toBe(0);
  });
});
