import fs from "node:fs";
import path from "node:path";
import type { ParsedQqMessage } from "./types.js";

export type QqAgencyMode =
  | "silent"
  | "social_reply"
  | "play_reply"
  | "light_surprise"
  | "staged_surprise";

export type QqOpportunityType =
  | "touch_tease_window"
  | "absurdity_window"
  | "visual_window"
  | "running_gag_window"
  | "silence_break_window";

export type QqSocialSignal =
  | "touch_tease"
  | "repeated_touch"
  | "touch_dogpile"
  | "touch_overload"
  | "absurdity"
  | "has_visual_material"
  | "playful_visual_cue"
  | "has_avatar_cue"
  | "running_gag"
  | "high_group_energy"
  | "cold_scene"
  | "direct_engagement"
  | "safe_to_play"
  | "target_familiarity"
  | "serious_topic";

export type QqSurpriseRecipeId =
  | "touch_reaction"
  | "touch_timeout"
  | "avatar_meme"
  | "current_image_meme";

export type QqRecentMessageSample = {
  senderId: string;
  text: string;
  createdAt: number;
  wasMentioned: boolean;
  isReply: boolean;
  explicitInstruction?: boolean;
  direction?: "inbound" | "outbound";
};

export type QqAgencyGroupProfile = {
  groupId: string;
  groupDir?: string | null;
  selfPosition?: {
    currentRole?: string;
    allowedPresence?: string;
    attentionBudget?: number;
    playfulnessLevel?: number;
    protectivenessLevel?: number;
  };
  appraisal?: {
    socialSafety?: number;
    dramaRisk?: number;
    groupNoise?: number;
    recentAcceptance?: number;
    recentRejection?: number;
    novelty?: number;
  };
};

export type QqAgencySenderProfile = {
  qqId: string;
  displayName?: string;
  relationshipWeight?: number;
  trust?: number;
  teasingTolerance?: number | null;
  messageCount?: number;
};

export type QqInitiativeState = {
  schemaVersion: 1;
  updatedAt: string;
  groupId: string;
  energy: number;
  playfulness: number;
  mischief: number;
  shyness: number;
  attentionHunger: number;
  boredom: number;
  protectiveness: number;
  noveltySeeking: number;
  recentSuccessStreak: number;
  recentMissStreak: number;
  lastSurpriseAt: string | null;
  lastRecipeId: QqSurpriseRecipeId | null;
  suppressionUntil: string | null;
};

export type QqRelationshipEntry = {
  displayName?: string;
  closeness: number;
  teaseTolerance: number;
  likesPlayfulResponse: number;
  riskLevel: number;
  sharedGags: string[];
  recentHeat: number;
  lastTargetedAt: string | null;
};

export type QqRelationshipState = {
  schemaVersion: 1;
  updatedAt: string;
  groupId: string;
  relationships: Record<string, QqRelationshipEntry>;
};

export type QqSurpriseRecipe = {
  id: QqSurpriseRecipeId;
  triggerTypes: QqOpportunityType[];
  requiredSignals: QqSocialSignal[];
  tools: string[];
  risk: number;
  cooldownMinutes: number;
  maxPerHour: number;
  targetScope: "group" | "person";
  goal: string;
  styleHint: string;
};

export type QqSocialOpportunity = {
  type: QqOpportunityType;
  strength: number;
  reasons: string[];
};

export type QqAgencyRecipeCandidate = {
  recipe: QqSurpriseRecipe;
  score: number;
  reasons: string[];
  blockedByCooldown: boolean;
};

export type QqSocialAgencyPlan = {
  mode: QqAgencyMode;
  allowAmbientJoin: boolean;
  signals: QqSocialSignal[];
  state: QqInitiativeState;
  relationship: QqRelationshipEntry;
  opportunity: QqSocialOpportunity | null;
  selectedRecipe: QqAgencyRecipeCandidate | null;
  candidates: QqAgencyRecipeCandidate[];
  reasons: string[];
};

export type QqSocialAgencyPlanParams = {
  groupProfile: QqAgencyGroupProfile;
  senderId: string;
  senderName?: string;
  senderProfile?: QqAgencySenderProfile | null;
  rawBody: string;
  parsed: ParsedQqMessage;
  recentMessages: QqRecentMessageSample[];
  nowMs: number;
};

type OpportunityLogEntry = {
  ts: string;
  type: QqOpportunityType;
  senderId: string;
  senderName?: string;
  strength: number;
  signals: QqSocialSignal[];
  mode: QqAgencyMode;
  acted: boolean;
  recipe?: QqSurpriseRecipeId;
  reasons: string[];
};

const TOUCH_RE =
  /(摸摸|摸一下|又摸一下|摸了你一下|偷偷摸了你一下|碰一下|又碰一下|碰了碰你|占我便宜|戳一戳|戳戳|poke)/iu;
const AVATAR_RE = /(头像|头图|profile picture|avatar|pfp)/iu;
const SERIOUS_RE =
  /(流鼻血|鼻血|怎么办|治疗|医院|药|出血|疼|难受|急|救命|求助|帮帮|医疗|危险|报警|自杀|昏倒)/u;
const PLAYFUL_ABSURD_RE =
  /(咕咕嘎嘎|嘎嘎|摸摸|喵+|喵喵|汪+|啾+|欸嘿|诶嘿|草|笑死|hhh|www|发病|抽象|怪东西)/iu;
const REACTION_IMAGE_RE = /(配图|表情包|reaction|反应图|来张图|整张图)/iu;
const VISUAL_BANTER_RE = /(这张|这图|这表情|这照片|这画面|这也太|有点怪|好怪|离谱|绷不住|什么图)/iu;

const DEFAULT_RECIPES: QqSurpriseRecipe[] = [
  {
    id: "touch_reaction",
    triggerTypes: ["touch_tease_window"],
    requiredSignals: ["touch_tease"],
    tools: [],
    risk: 0.12,
    cooldownMinutes: 8,
    maxPerHour: 3,
    targetScope: "person",
    goal: "Answer teasing touch interactions with a lively in-character reaction.",
    styleHint: "keep it to one playful line; shy, mock-complaining, or lightly flustered fits",
  },
  {
    id: "touch_timeout",
    triggerTypes: ["touch_tease_window"],
    requiredSignals: ["touch_tease", "touch_overload", "safe_to_play"],
    tools: ["chinobot_set_group_ban"],
    risk: 0.48,
    cooldownMinutes: 120,
    maxPerHour: 1,
    targetScope: "person",
    goal: "If one person keeps repeatedly touching the bot or joins an obvious short-span dogpile, give them a short cooldown mute.",
    styleHint: "use only as a short moderation-style timeout, not as a normal playful response",
  },
  {
    id: "avatar_meme",
    triggerTypes: ["visual_window"],
    requiredSignals: ["has_avatar_cue", "safe_to_play"],
    tools: ["chinobot_analyze_avatar", "chinobot_make_meme"],
    risk: 0.34,
    cooldownMinutes: 60,
    maxPerHour: 1,
    targetScope: "person",
    goal: "Use the sender's avatar as material for a light meme or playful reaction image.",
    styleHint: "stay affectionate or teasing, not mean; avoid targeting unfamiliar people too hard",
  },
  {
    id: "current_image_meme",
    triggerTypes: ["visual_window"],
    requiredSignals: ["has_visual_material", "playful_visual_cue", "safe_to_play"],
    tools: ["chinobot_make_meme"],
    risk: 0.28,
    cooldownMinutes: 55,
    maxPerHour: 1,
    targetScope: "person",
    goal: "Use the image someone just posted as instant meme material for a playful callback.",
    styleHint: "make the image feel like the punchline; keep the text short and easy to read",
  },
];

function clamp01(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  if (value <= 0) {
    return 0;
  }
  if (value >= 1) {
    return 1;
  }
  return value;
}

function readJsonFile<T>(filePath: string, fallback: T): T {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
  } catch {
    return fallback;
  }
}

function writeJsonFile(filePath: string, value: unknown) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function appendJsonl(filePath: string, value: unknown) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.appendFileSync(filePath, `${JSON.stringify(value)}\n`, "utf8");
}

function initiativeStatePath(groupDir: string) {
  return path.join(groupDir, "initiative-state.json");
}

function relationshipStatePath(groupDir: string) {
  return path.join(groupDir, "relationship-state.json");
}

function opportunityLogPath(groupDir: string) {
  return path.join(groupDir, "opportunity-log.jsonl");
}

function surpriseRecipesPath(groupDir: string) {
  return path.join(groupDir, "surprise-recipes.json");
}

function membersPath(groupDir: string) {
  return path.join(groupDir, "members.json");
}

function loadRecipes(groupDir?: string | null): QqSurpriseRecipe[] {
  if (!groupDir) {
    return DEFAULT_RECIPES;
  }
  const loaded = readJsonFile<{ recipes?: QqSurpriseRecipe[] }>(
    surpriseRecipesPath(groupDir),
    {},
  ).recipes;
  if (!Array.isArray(loaded) || loaded.length === 0) {
    return DEFAULT_RECIPES;
  }
  return loaded;
}

function defaultInitiativeState(groupId: string, profile: QqAgencyGroupProfile): QqInitiativeState {
  const playfulnessSeed = Number(profile.selfPosition?.playfulnessLevel ?? 0.26);
  const protectivenessSeed = Number(profile.selfPosition?.protectivenessLevel ?? 0.42);
  const acceptanceSeed = Number(profile.appraisal?.recentAcceptance ?? 0.1);
  const noveltySeed = Number(profile.appraisal?.novelty ?? 0.5);
  return {
    schemaVersion: 1,
    updatedAt: new Date().toISOString(),
    groupId,
    energy: 0.58,
    playfulness: clamp01(0.3 + playfulnessSeed * 0.8),
    mischief: clamp01(0.24 + playfulnessSeed * 0.7),
    shyness: 0.34,
    attentionHunger: clamp01(0.24 + acceptanceSeed * 0.4),
    boredom: 0.18,
    protectiveness: clamp01(0.2 + protectivenessSeed * 0.8),
    noveltySeeking: clamp01(0.35 + noveltySeed * 0.45),
    recentSuccessStreak: 0,
    recentMissStreak: 0,
    lastSurpriseAt: null,
    lastRecipeId: null,
    suppressionUntil: null,
  };
}

function loadInitiativeState(groupDir: string | null | undefined, profile: QqAgencyGroupProfile) {
  if (!groupDir) {
    return defaultInitiativeState(profile.groupId, profile);
  }
  return readJsonFile<QqInitiativeState>(
    initiativeStatePath(groupDir),
    defaultInitiativeState(profile.groupId, profile),
  );
}

function defaultRelationshipEntry(params: {
  senderId: string;
  senderName?: string;
  senderProfile?: QqAgencySenderProfile | null;
}): QqRelationshipEntry {
  const relationshipWeight = Number(params.senderProfile?.relationshipWeight ?? 0.1);
  const trust = Number(params.senderProfile?.trust ?? 0.1);
  const teasingTolerance = Number(params.senderProfile?.teasingTolerance ?? 0.45);
  const messageCount = Number(params.senderProfile?.messageCount ?? 0);
  return {
    displayName: params.senderName ?? params.senderProfile?.displayName,
    closeness: clamp01(relationshipWeight * 1.6 + Math.min(messageCount, 8) * 0.03),
    teaseTolerance: clamp01(Number.isFinite(teasingTolerance) ? teasingTolerance : 0.45),
    likesPlayfulResponse: clamp01(0.35 + relationshipWeight * 1.2),
    riskLevel: clamp01(0.22 - trust * 0.12),
    sharedGags: [],
    recentHeat: clamp01(Math.min(messageCount, 8) * 0.04),
    lastTargetedAt: null,
  };
}

function loadRelationshipState(params: {
  groupDir?: string | null;
  profile: QqAgencyGroupProfile;
  senderId: string;
  senderName?: string;
  senderProfile?: QqAgencySenderProfile | null;
}): QqRelationshipState {
  const fallback: QqRelationshipState = {
    schemaVersion: 1,
    updatedAt: new Date().toISOString(),
    groupId: params.profile.groupId,
    relationships: {
      [params.senderId]: defaultRelationshipEntry(params),
    },
  };
  if (!params.groupDir) {
    return fallback;
  }
  const loaded = readJsonFile<QqRelationshipState>(
    relationshipStatePath(params.groupDir),
    fallback,
  );
  if (!loaded.relationships[params.senderId]) {
    loaded.relationships[params.senderId] = defaultRelationshipEntry(params);
  }
  return loaded;
}

export function resolveQqAgencySenderProfile(
  groupDir: string | null | undefined,
  senderId: string,
): QqAgencySenderProfile | null {
  if (!groupDir) {
    return null;
  }
  const data = readJsonFile<{ members?: QqAgencySenderProfile[] }>(membersPath(groupDir), {});
  if (!Array.isArray(data.members)) {
    return null;
  }
  return data.members.find((entry) => String(entry.qqId ?? "") === senderId) ?? null;
}

function normalizeText(text: string): string {
  return text.trim().toLowerCase();
}

function countRecentMessages(
  recentMessages: QqRecentMessageSample[],
  nowMs: number,
  withinMs: number,
): QqRecentMessageSample[] {
  return recentMessages.filter((entry) => nowMs - entry.createdAt <= withinMs);
}

function detectTouchTease(rawBody: string) {
  return TOUCH_RE.test(rawBody);
}

function detectAbsurdity(rawBody: string, parsed: ParsedQqMessage): boolean {
  if (!rawBody || SERIOUS_RE.test(rawBody)) {
    return false;
  }
  if (PLAYFUL_ABSURD_RE.test(rawBody)) {
    return true;
  }
  const compact = rawBody.replace(/\s+/g, "");
  const shortAndOdd =
    compact.length > 0 &&
    compact.length <= 14 &&
    !/[?？]/u.test(compact) &&
    !parsed.wasMentioned &&
    !parsed.isReply &&
    /[a-zA-Z]{2,}|[~～]{1,}|[哈嘿啊呀喵嘎]{3,}/u.test(compact);
  return shortAndOdd;
}

function detectRunningGag(params: {
  rawBody: string;
  recentMessages: QqRecentMessageSample[];
  nowMs: number;
}) {
  const normalized = normalizeText(params.rawBody);
  if (!normalized) {
    return false;
  }
  const recent = countRecentMessages(params.recentMessages, params.nowMs, 8 * 60 * 1000);
  const repeatedSame = recent.filter((entry) => normalizeText(entry.text) === normalized).length >= 2;
  const repeatedTouch = recent.filter((entry) => detectTouchTease(entry.text)).length >= 2;
  return repeatedSame || repeatedTouch;
}

function detectHighGroupEnergy(recentMessages: QqRecentMessageSample[], nowMs: number) {
  const recent = countRecentMessages(recentMessages, nowMs, 3 * 60 * 1000);
  if (recent.length >= 6) {
    return true;
  }
  const uniqueSenders = new Set(recent.map((entry) => entry.senderId)).size;
  return recent.length >= 4 && uniqueSenders >= 3;
}

function detectColdScene(recentMessages: QqRecentMessageSample[], nowMs: number) {
  const latest = recentMessages[recentMessages.length - 1];
  if (!latest) {
    return true;
  }
  return nowMs - latest.createdAt >= 7 * 60 * 1000;
}

function resolveSignals(params: {
  senderId: string;
  rawBody: string;
  parsed: ParsedQqMessage;
  recentMessages: QqRecentMessageSample[];
  nowMs: number;
  initiative: QqInitiativeState;
  relationship: QqRelationshipEntry;
  profile: QqAgencyGroupProfile;
}) {
  const signals = new Set<QqSocialSignal>();
  const directEngagement = params.parsed.wasMentioned || params.parsed.isReply;
  const touchTease = detectTouchTease(params.rawBody);
  const absurdity = detectAbsurdity(params.rawBody, params.parsed);
  const hasVisualMaterial = params.parsed.mediaSegments.length > 0 || REACTION_IMAGE_RE.test(params.rawBody);
  const hasAvatarCue = AVATAR_RE.test(params.rawBody);
  const runningGag = detectRunningGag({
    rawBody: params.rawBody,
    recentMessages: params.recentMessages,
    nowMs: params.nowMs,
  });
  if (directEngagement) {
    signals.add("direct_engagement");
  }
  if (touchTease) {
    signals.add("touch_tease");
  }
  const recentTouchCount = countRecentMessages(params.recentMessages, params.nowMs, 10 * 60 * 1000)
    .filter((entry) => detectTouchTease(entry.text)).length;
  if (recentTouchCount >= 2) {
    signals.add("repeated_touch");
  }
  const touchWindowSamples = countRecentMessages(params.recentMessages, params.nowMs, 6 * 60 * 1000)
    .filter((entry) => detectTouchTease(entry.text));
  const sameSenderTouchCount = touchWindowSamples.filter((entry) => entry.senderId === params.senderId).length;
  const currentMessageAlreadyTracked = params.recentMessages.some(
    (entry) =>
      entry.senderId === params.senderId &&
      detectTouchTease(entry.text) &&
      normalizeText(entry.text) === normalizeText(params.rawBody) &&
      Math.abs(params.nowMs - entry.createdAt) <= 15_000,
  );
  const normalizedSenderTouchCount =
    sameSenderTouchCount + (touchTease && !currentMessageAlreadyTracked ? 1 : 0);
  const normalizedTouchSamples = currentMessageAlreadyTracked
    ? touchWindowSamples
    : touchTease
      ? touchWindowSamples.concat({
          senderId: params.senderId,
          text: params.rawBody,
          createdAt: params.nowMs,
          wasMentioned: params.parsed.wasMentioned,
          isReply: params.parsed.isReply,
        })
      : touchWindowSamples;
  const touchDogpile =
    normalizedTouchSamples.length >= 5 &&
    new Set(normalizedTouchSamples.map((entry) => entry.senderId)).size >= 3;
  if (touchDogpile) {
    signals.add("touch_dogpile");
  }
  if (normalizedSenderTouchCount >= 4) {
    signals.add("touch_overload");
  }
  if (touchDogpile) {
    signals.add("touch_overload");
  }
  if (absurdity) {
    signals.add("absurdity");
  }
  if (hasVisualMaterial) {
    signals.add("has_visual_material");
  }
  if (hasAvatarCue) {
    signals.add("has_avatar_cue");
  }
  if (runningGag) {
    signals.add("running_gag");
  }
  if (
    hasVisualMaterial &&
    (absurdity ||
      directEngagement ||
      runningGag ||
      touchTease ||
      VISUAL_BANTER_RE.test(params.rawBody) ||
      params.rawBody.trim().length <= 18)
  ) {
    signals.add("playful_visual_cue");
  }
  if (detectHighGroupEnergy(params.recentMessages, params.nowMs)) {
    signals.add("high_group_energy");
  }
  if (detectColdScene(params.recentMessages, params.nowMs)) {
    signals.add("cold_scene");
  }
  if (params.relationship.closeness >= 0.38 || params.relationship.recentHeat >= 0.45) {
    signals.add("target_familiarity");
  }
  const seriousTopic = SERIOUS_RE.test(params.rawBody);
  if (seriousTopic) {
    signals.add("serious_topic");
  }
  const safeToPlay =
    Number(params.profile.appraisal?.socialSafety ?? 0.75) >= 0.65 &&
    Number(params.profile.appraisal?.dramaRisk ?? 0) <= 0.3 &&
    params.relationship.riskLevel <= 0.5 &&
    !seriousTopic;
  if (safeToPlay) {
    signals.add("safe_to_play");
  }
  return [...signals];
}

function resolveOpportunity(params: {
  signals: QqSocialSignal[];
  initiative: QqInitiativeState;
}): QqSocialOpportunity | null {
  const signalSet = new Set(params.signals);
  if (signalSet.has("touch_tease")) {
    return {
      type: "touch_tease_window",
      strength: signalSet.has("touch_dogpile")
        ? 0.96
        : signalSet.has("touch_overload")
          ? 0.94
          : signalSet.has("repeated_touch")
            ? 0.86
            : 0.62,
      reasons: signalSet.has("touch_dogpile")
        ? ["multiple people are piling on the same touch bit", "the current sender is joining a short-span dogpile"]
        : signalSet.has("touch_overload")
        ? ["same sender keeps touching in a short span", "a short cooldown-style response is now reasonable"]
        : signalSet.has("repeated_touch")
          ? ["repeated_touch", "teasing the bot is clearly part of the current bit"]
          : ["single teasing touch interaction"],
    };
  }
  if (signalSet.has("has_avatar_cue") || signalSet.has("has_visual_material")) {
    return {
      type: "visual_window",
      strength: signalSet.has("has_avatar_cue")
        ? 0.68
        : signalSet.has("playful_visual_cue")
          ? 0.64
          : 0.56,
      reasons: ["there is clear visual or avatar material to build on"],
    };
  }
  if (signalSet.has("running_gag")) {
    return {
      type: "running_gag_window",
      strength: 0.7,
      reasons: ["the same bit appears to be rolling across multiple recent messages"],
    };
  }
  if (signalSet.has("absurdity")) {
    return {
      type: "absurdity_window",
      strength: signalSet.has("high_group_energy") ? 0.66 : 0.54,
      reasons: ["the line reads more like a bit than a request for an answer"],
    };
  }
  if (signalSet.has("cold_scene") && params.initiative.boredom >= 0.55) {
    return {
      type: "silence_break_window",
      strength: 0.44,
      reasons: ["the scene is quiet and a tiny playful beat may help"],
    };
  }
  return null;
}

function resolveMode(params: {
  signals: QqSocialSignal[];
  initiative: QqInitiativeState;
  relationship: QqRelationshipEntry;
  opportunity: QqSocialOpportunity | null;
  nowMs: number;
}) {
  const signalSet = new Set(params.signals);
  const suppressionUntil = params.initiative.suppressionUntil
    ? Date.parse(params.initiative.suppressionUntil)
    : NaN;
  const isSuppressed = Number.isFinite(suppressionUntil) && params.nowMs < suppressionUntil;
  if (!params.opportunity) {
    return signalSet.has("serious_topic") ? "social_reply" : "silent";
  }
  if (isSuppressed) {
    if (params.opportunity.type === "touch_tease_window") {
      if (signalSet.has("touch_overload")) {
        return "light_surprise";
      }
      return "play_reply";
    }
    return signalSet.has("serious_topic") ? "social_reply" : "silent";
  }
  if (!signalSet.has("safe_to_play")) {
    return "social_reply";
  }
  if (params.opportunity.type === "touch_tease_window") {
    if (signalSet.has("touch_overload")) {
      return "light_surprise";
    }
    if (signalSet.has("repeated_touch") && params.initiative.playfulness >= 0.45) {
      return params.relationship.teaseTolerance >= 0.52 ? "light_surprise" : "play_reply";
    }
    return "play_reply";
  }
  if (params.opportunity.type === "visual_window") {
    return params.initiative.noveltySeeking >= 0.52 ? "light_surprise" : "play_reply";
  }
  if (params.opportunity.type === "running_gag_window") {
    return params.initiative.mischief >= 0.45 || params.initiative.noveltySeeking >= 0.5
      ? "light_surprise"
      : "play_reply";
  }
  if (params.opportunity.type === "absurdity_window") {
    if (
      (signalSet.has("high_group_energy") || signalSet.has("direct_engagement")) &&
      params.initiative.playfulness >= 0.5 &&
      params.relationship.likesPlayfulResponse >= 0.45
    ) {
      return "light_surprise";
    }
    return "play_reply";
  }
  if (params.opportunity.type === "silence_break_window") {
    return "play_reply";
  }
  return "silent";
}

function recipeMatchesOpportunity(recipe: QqSurpriseRecipe, opportunity: QqSocialOpportunity) {
  return recipe.triggerTypes.includes(opportunity.type);
}

function hasRequiredSignals(recipe: QqSurpriseRecipe, signals: QqSocialSignal[]) {
  const signalSet = new Set(signals);
  return recipe.requiredSignals.every((signal) => signalSet.has(signal));
}

function isRecipeOnCooldown(params: {
  recipe: QqSurpriseRecipe;
  initiative: QqInitiativeState;
  relationship: QqRelationshipEntry;
  nowMs: number;
}) {
  const lastSurpriseAt = params.initiative.lastSurpriseAt
    ? Date.parse(params.initiative.lastSurpriseAt)
    : NaN;
  const targetedAt = params.relationship.lastTargetedAt
    ? Date.parse(params.relationship.lastTargetedAt)
    : NaN;
  if (
    Number.isFinite(lastSurpriseAt) &&
    params.initiative.lastRecipeId === params.recipe.id &&
    params.nowMs - lastSurpriseAt < params.recipe.cooldownMinutes * 60_000
  ) {
    return true;
  }
  if (
    params.recipe.targetScope === "person" &&
    Number.isFinite(targetedAt) &&
    params.nowMs - targetedAt < Math.max(params.recipe.cooldownMinutes, 25) * 60_000
  ) {
    return true;
  }
  return false;
}

function scoreRecipe(params: {
  recipe: QqSurpriseRecipe;
  opportunity: QqSocialOpportunity;
  signals: QqSocialSignal[];
  initiative: QqInitiativeState;
  relationship: QqRelationshipEntry;
  nowMs: number;
}): QqAgencyRecipeCandidate {
  const reasons: string[] = [];
  let score = params.opportunity.strength;
  score += params.initiative.playfulness * 0.24;
  score += params.initiative.mischief * 0.18;
  score += params.initiative.noveltySeeking * 0.12;
  score += params.relationship.likesPlayfulResponse * 0.14;
  score += params.relationship.teaseTolerance * 0.12;
  score -= params.recipe.risk * 0.38;
  if (params.recipe.targetScope === "person") {
    score += params.relationship.closeness * 0.12;
  }
  if (params.initiative.lastRecipeId === params.recipe.id) {
    score -= 0.24;
    reasons.push("same recipe was the latest surprise");
  }
  if (params.signals.includes("has_avatar_cue") && params.recipe.id === "avatar_meme") {
    score += 0.16;
    reasons.push("avatar cue explicitly unlocks avatar meme flow");
  }
  if (params.signals.includes("touch_overload") && params.recipe.id === "touch_timeout") {
    score += 0.28;
    reasons.push("same sender has crossed the repeated-touch threshold");
  }
  if (params.signals.includes("touch_dogpile") && params.recipe.id === "touch_timeout") {
    score += 0.24;
    reasons.push("the current sender is joining a short-span touch dogpile");
  }
  if (params.signals.includes("has_visual_material") && params.recipe.id === "current_image_meme") {
    score += 0.12;
    reasons.push("there is already a usable image in the scene");
  }
  if (params.signals.includes("playful_visual_cue") && params.recipe.id === "current_image_meme") {
    score += 0.14;
    reasons.push("the posted image already feels like meme material");
  }
  const blockedByCooldown = isRecipeOnCooldown(params);
  if (blockedByCooldown) {
    score -= 0.5;
    reasons.push("recipe is cooling down");
  }
  return {
    recipe: params.recipe,
    score,
    reasons,
    blockedByCooldown,
  };
}

function shouldAllowAmbientJoin(params: {
  mode: QqAgencyMode;
  signals: QqSocialSignal[];
  opportunity: QqSocialOpportunity | null;
}) {
  if (!params.opportunity) {
    return false;
  }
  if (!params.signals.includes("safe_to_play")) {
    return false;
  }
  return params.mode === "play_reply" || params.mode === "light_surprise" || params.mode === "staged_surprise";
}

export function buildQqSocialAgencyPlan(
  params: QqSocialAgencyPlanParams,
): QqSocialAgencyPlan {
  const initiative = loadInitiativeState(params.groupProfile.groupDir, params.groupProfile);
  const relationships = loadRelationshipState({
    groupDir: params.groupProfile.groupDir,
    profile: params.groupProfile,
    senderId: params.senderId,
    senderName: params.senderName,
    senderProfile: params.senderProfile,
  });
  const relationship = relationships.relationships[params.senderId];
  const signals = resolveSignals({
    senderId: params.senderId,
    rawBody: params.rawBody,
    parsed: params.parsed,
    recentMessages: params.recentMessages,
    nowMs: params.nowMs,
    initiative,
    relationship,
    profile: params.groupProfile,
  });
  const opportunity = resolveOpportunity({
    signals,
    initiative,
  });
  const mode = resolveMode({
    signals,
    initiative,
    relationship,
    opportunity,
    nowMs: params.nowMs,
  });
  const reasons: string[] = [];
  if (opportunity) {
    reasons.push(...opportunity.reasons);
  }
  const candidates =
    opportunity && (mode === "light_surprise" || mode === "staged_surprise" || mode === "play_reply")
      ? loadRecipes(params.groupProfile.groupDir)
          .filter((recipe) => recipeMatchesOpportunity(recipe, opportunity))
          .filter((recipe) => hasRequiredSignals(recipe, signals))
          .map((recipe) =>
            scoreRecipe({
              recipe,
              opportunity,
              signals,
              initiative,
              relationship,
              nowMs: params.nowMs,
            }),
          )
          .sort((left, right) => right.score - left.score)
      : [];
  const selectedRecipe =
    mode === "light_surprise" || mode === "staged_surprise"
      ? ((opportunity?.type === "touch_tease_window" && signals.includes("repeated_touch")
          ? candidates.find(
              (candidate) =>
                !candidate.blockedByCooldown &&
                candidate.recipe.tools.length > 0 &&
                candidate.score >= 0.55,
            )
          : null) ??
        candidates.find((candidate) => !candidate.blockedByCooldown && candidate.score >= 0.55) ??
        null)
      : mode === "play_reply"
        ? (candidates.find((candidate) => candidate.recipe.id === "touch_reaction") ??
          candidates.find((candidate) => !candidate.blockedByCooldown && candidate.score >= 0.62) ??
          null)
        : null;
  if (selectedRecipe) {
    reasons.push(`selected recipe ${selectedRecipe.recipe.id}`);
  }
  return {
    mode,
    allowAmbientJoin: shouldAllowAmbientJoin({ mode, signals, opportunity }),
    signals,
    state: initiative,
    relationship,
    opportunity,
    selectedRecipe,
    candidates,
    reasons,
  };
}

export function persistQqSocialAgencyPlan(params: {
  groupDir?: string | null;
  groupId: string;
  senderId: string;
  senderName?: string;
  plan: QqSocialAgencyPlan;
  nowMs: number;
}) {
  if (!params.groupDir || !params.plan.opportunity) {
    return;
  }
  const initiative = {
    ...params.plan.state,
    updatedAt: new Date(params.nowMs).toISOString(),
    boredom: clamp01(params.plan.state.boredom * 0.82),
    playfulness: clamp01(params.plan.state.playfulness + (params.plan.mode === "light_surprise" ? 0.03 : 0)),
    attentionHunger: clamp01(
      params.plan.state.attentionHunger + (params.plan.mode === "silent" ? 0.01 : -0.01),
    ),
    lastSurpriseAt:
      params.plan.selectedRecipe &&
      (params.plan.mode === "light_surprise" || params.plan.mode === "staged_surprise")
        ? new Date(params.nowMs).toISOString()
        : params.plan.state.lastSurpriseAt,
    lastRecipeId: params.plan.selectedRecipe?.recipe.id ?? params.plan.state.lastRecipeId,
  } satisfies QqInitiativeState;
  writeJsonFile(initiativeStatePath(params.groupDir), initiative);

  const relationshipState = loadRelationshipState({
    groupDir: params.groupDir,
    profile: { groupId: params.groupId, groupDir: params.groupDir },
    senderId: params.senderId,
    senderName: params.senderName,
    senderProfile: null,
  });
  relationshipState.updatedAt = new Date(params.nowMs).toISOString();
  const current =
    relationshipState.relationships[params.senderId] ?? defaultRelationshipEntry({
      senderId: params.senderId,
      senderName: params.senderName,
      senderProfile: null,
    });
  relationshipState.relationships[params.senderId] = {
    ...current,
    displayName: params.senderName ?? current.displayName,
    recentHeat: clamp01(current.recentHeat * 0.7 + 0.25),
    closeness: clamp01(
      current.closeness + (params.plan.mode === "light_surprise" || params.plan.mode === "play_reply" ? 0.015 : 0.005),
    ),
    lastTargetedAt:
      params.plan.selectedRecipe?.recipe.targetScope === "person"
        ? new Date(params.nowMs).toISOString()
        : current.lastTargetedAt,
  };
  writeJsonFile(relationshipStatePath(params.groupDir), relationshipState);

  const logEntry: OpportunityLogEntry = {
    ts: new Date(params.nowMs).toISOString(),
    type: params.plan.opportunity.type,
    senderId: params.senderId,
    senderName: params.senderName,
    strength: params.plan.opportunity.strength,
    signals: params.plan.signals,
    mode: params.plan.mode,
    acted: Boolean(params.plan.selectedRecipe),
    recipe: params.plan.selectedRecipe?.recipe.id,
    reasons: params.plan.reasons,
  };
  appendJsonl(opportunityLogPath(params.groupDir), logEntry);
}

export function recordQqSocialAgencyOutcome(params: {
  groupDir?: string | null;
  groupId: string;
  senderId: string;
  senderName?: string;
  plan: QqSocialAgencyPlan | null;
  success: boolean;
  note?: string;
  nowMs: number;
}) {
  if (!params.groupDir || !params.plan?.selectedRecipe) {
    return;
  }
  const initiative = readJsonFile<QqInitiativeState>(
    initiativeStatePath(params.groupDir),
    params.plan.state,
  );
  initiative.updatedAt = new Date(params.nowMs).toISOString();
  if (params.success) {
    initiative.recentSuccessStreak = Math.min(initiative.recentSuccessStreak + 1, 6);
    initiative.recentMissStreak = 0;
    initiative.playfulness = clamp01(initiative.playfulness + 0.025);
    initiative.mischief = clamp01(initiative.mischief + 0.015);
    initiative.boredom = clamp01(initiative.boredom - 0.08);
    initiative.lastSurpriseAt = new Date(params.nowMs).toISOString();
    initiative.lastRecipeId = params.plan.selectedRecipe.recipe.id;
    initiative.suppressionUntil = null;
  } else {
    initiative.recentMissStreak = Math.min(initiative.recentMissStreak + 1, 6);
    initiative.recentSuccessStreak = 0;
    initiative.playfulness = clamp01(initiative.playfulness - 0.03);
    initiative.mischief = clamp01(initiative.mischief - 0.02);
    if (initiative.recentMissStreak >= 2) {
      initiative.suppressionUntil = new Date(params.nowMs + 30 * 60 * 1000).toISOString();
    }
  }
  writeJsonFile(initiativeStatePath(params.groupDir), initiative);

  const relationshipState = loadRelationshipState({
    groupDir: params.groupDir,
    profile: { groupId: params.groupId, groupDir: params.groupDir },
    senderId: params.senderId,
    senderName: params.senderName,
    senderProfile: null,
  });
  relationshipState.updatedAt = new Date(params.nowMs).toISOString();
  const current = relationshipState.relationships[params.senderId];
  relationshipState.relationships[params.senderId] = {
    ...current,
    recentHeat: clamp01(current.recentHeat + (params.success ? 0.06 : -0.02)),
    closeness: clamp01(current.closeness + (params.success ? 0.02 : 0)),
    likesPlayfulResponse: clamp01(
      current.likesPlayfulResponse + (params.success ? 0.03 : -0.015),
    ),
  };
  writeJsonFile(relationshipStatePath(params.groupDir), relationshipState);

  appendJsonl(opportunityLogPath(params.groupDir), {
    ts: new Date(params.nowMs).toISOString(),
    type: params.plan.opportunity?.type ?? null,
    senderId: params.senderId,
    senderName: params.senderName,
    outcome: params.success ? "success" : "failure",
    recipe: params.plan.selectedRecipe.recipe.id,
    note: params.note ?? null,
  });
}

export function buildQqSocialAgencyPromptRecord(plan: QqSocialAgencyPlan) {
  return {
    mode: plan.mode,
    allow_ambient_join: plan.allowAmbientJoin,
    signals: plan.signals,
    opportunity: plan.opportunity
      ? {
          type: plan.opportunity.type,
          strength: plan.opportunity.strength,
          reasons: plan.opportunity.reasons,
        }
      : null,
    inner_state: {
      playfulness: Number(plan.state.playfulness.toFixed(2)),
      mischief: Number(plan.state.mischief.toFixed(2)),
      shyness: Number(plan.state.shyness.toFixed(2)),
      attention_hunger: Number(plan.state.attentionHunger.toFixed(2)),
      boredom: Number(plan.state.boredom.toFixed(2)),
      novelty_seeking: Number(plan.state.noveltySeeking.toFixed(2)),
    },
    relationship: {
      closeness: Number(plan.relationship.closeness.toFixed(2)),
      tease_tolerance: Number(plan.relationship.teaseTolerance.toFixed(2)),
      likes_playful_response: Number(plan.relationship.likesPlayfulResponse.toFixed(2)),
      risk_level: Number(plan.relationship.riskLevel.toFixed(2)),
    },
    selected_recipe: plan.selectedRecipe
      ? {
          id: plan.selectedRecipe.recipe.id,
          goal: plan.selectedRecipe.recipe.goal,
          style_hint: plan.selectedRecipe.recipe.styleHint,
          tools: plan.selectedRecipe.recipe.tools,
        }
      : null,
    candidate_recipes: plan.candidates.slice(0, 3).map((candidate) => ({
      id: candidate.recipe.id,
      score: Number(candidate.score.toFixed(2)),
      tools: candidate.recipe.tools,
      blocked_by_cooldown: candidate.blockedByCooldown,
    })),
  };
}

export function ensureDefaultQqSocialAgencyFiles(groupDir: string, groupId: string) {
  if (!groupDir) {
    return;
  }
  if (!fs.existsSync(initiativeStatePath(groupDir))) {
    writeJsonFile(
      initiativeStatePath(groupDir),
      defaultInitiativeState(groupId, {
        groupId,
        groupDir,
      }),
    );
  }
  if (!fs.existsSync(relationshipStatePath(groupDir))) {
    writeJsonFile(
      relationshipStatePath(groupDir),
      {
        schemaVersion: 1,
        updatedAt: new Date().toISOString(),
        groupId,
        relationships: {},
      } satisfies QqRelationshipState,
    );
  }
  if (!fs.existsSync(surpriseRecipesPath(groupDir))) {
    writeJsonFile(
      surpriseRecipesPath(groupDir),
      {
        schemaVersion: 1,
        updatedAt: new Date().toISOString(),
        recipes: DEFAULT_RECIPES,
      },
    );
  }
}
