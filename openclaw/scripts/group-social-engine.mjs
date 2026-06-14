#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const memoryRoot = path.join(workspaceRoot, "memory", "group-social");
const targetGroupPath = path.join(memoryRoot, "target-group.json");
const targetSlug = "ciyuan-fusu-erqu";
const targetDir = path.join(memoryRoot, targetSlug);
const normsPath = path.join(targetDir, "norms.json");
const membersPath = path.join(targetDir, "members.json");
const selfPositionPath = path.join(targetDir, "self-position.json");
const appraisalPath = path.join(targetDir, "appraisal.json");
const replyStylePath = path.join(targetDir, "reply-style.json");
const episodesPath = path.join(targetDir, "episodes.jsonl");
const sessionsStorePath = path.join(
  os.homedir(),
  ".openclaw",
  "agents",
  "main",
  "sessions",
  "sessions.json",
);

function nowIso() {
  return new Date().toISOString();
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      args._.push(token);
      continue;
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = "true";
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
}

function printJson(value) {
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return structuredClone(fallback);
  }
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.${Math.random()
    .toString(36)
    .slice(2, 8)}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, filePath);
}

function appendJsonl(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.appendFileSync(filePath, `${JSON.stringify(value)}\n`, "utf8");
}

function defaultTargetGroup() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    groupName: "次元复苏 二群",
    groupId: null,
    channel: "qq",
    status: "active-target",
    notes: [
      "This is the primary social environment for the next selfhood phase.",
      "Do not bind a numeric group id until it is explicitly confirmed.",
    ],
  };
}

function defaultNorms() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    groupName: "次元复苏 二群",
    groupId: null,
    tone: "unknown-yet",
    humorStyle: [],
    taboos: [],
    allowedBoldness: 0.4,
    replyFrequencyExpectation: "low-until-confirmed",
    mentionSensitivity: "high",
    topicClusters: [],
    conflictTriggers: [],
    observedStats: {
      totalMessages: 0,
      uniqueSpeakers: 0,
      avgMessageLength: 0,
      exclamationRate: 0,
      questionRate: 0,
      roleplayRate: 0,
    },
    notes: [
      "This file should be filled from real observation, not assumptions.",
    ],
  };
}

function defaultMembers() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    groupName: "次元复苏 二群",
    groupId: null,
    members: [],
    notes: [
      "Populate with recurring members once group id is confirmed and observation starts.",
    ],
  };
}

function defaultSelfPosition() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    groupName: "次元复苏 二群",
    groupId: null,
    currentRole: "silent-observer",
    desiredRole: "calm-recurring-presence",
    allowedPresence: "light",
    socialRankEstimate: 0.0,
    playfulnessLevel: 0.3,
    protectivenessLevel: 0.5,
    attentionBudget: 0.35,
    notes: [
      "Stay conservative until the actual group culture is observed.",
    ],
  };
}

function defaultAppraisal() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    groupName: "次元复苏 二群",
    groupId: null,
    groupMood: "unknown",
    groupNoise: 0.0,
    dramaRisk: 0.0,
    novelty: 0.0,
    myBelonging: 0.0,
    recentAcceptance: 0.0,
    recentRejection: 0.0,
    socialSafety: 0.5,
  };
}

function defaultReplyStyle() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    groupName: "次元复苏 二群",
    groupId: null,
    targetStyle: {
      voice: "casual-group-member",
      length: "short",
      sentenceCount: "1-2 by default",
      cadence: "fast and natural",
      explanationMode: "only when explicitly useful",
      bodyFirstWhenPossible: true,
      punctuation: "sparse-by-default",
      punctuationMimicry: "follow-current-speaker",
      laughterForms: [],
      sentenceFinalParticles: [],
      stretchiness: "rare",
    },
    observedSignals: {
      sampleSize: 0,
      avgMessageLength: 0,
      shortMessageRate: 0,
      noPunctuationRate: 0,
      terminalPunctuationRate: 0,
      multiLineRate: 0,
      ellipsisRate: 0,
      repeatedCharRate: 0,
      emojiLikeRate: 0,
      laughterForms: [],
      sentenceFinalParticles: [],
    },
    do: [
      "Sound like a natural group participant, not documentation or customer support.",
      "Use short, direct, colloquial Chinese.",
      "Match the emotional temperature of the current speaker.",
      "Answer the actual social move first, explanation second.",
      "Prefer one clean line over a structured mini-essay.",
      "Use mild playfulness when the group energy supports it.",
    ],
    dont: [
      "Do not default to bullet lists in casual chat.",
      "Do not over-explain obvious slang or jokes.",
      "Do not start with assistant-y framing like '你大概是想说'.",
      "Do not end every reply with a follow-up offer.",
      "Do not sound like a teacher unless someone clearly asked for teaching.",
      "Do not overuse polished written Chinese in fast group banter.",
    ],
    antiPatterns: [
      "因为正确写法是……",
      "如果你愿意，我还能……",
      "你把具体对象发出来，我直接……",
      "简单记：",
      "举个小例子：",
    ],
    preferredPatterns: [
      "短句直接回",
      "顺着对方的话头接",
      "像群友，不像客服",
      "能用一句就别用三句",
    ],
  };
}

function ensureFiles() {
  const target = readJson(targetGroupPath, defaultTargetGroup());
  const norms = readJson(normsPath, defaultNorms());
  const members = readJson(membersPath, defaultMembers());
  const selfPosition = readJson(selfPositionPath, defaultSelfPosition());
  const appraisal = readJson(appraisalPath, defaultAppraisal());
  const replyStyle = readJson(replyStylePath, defaultReplyStyle());

  writeJson(targetGroupPath, target);
  writeJson(normsPath, norms);
  writeJson(membersPath, members);
  writeJson(selfPositionPath, selfPosition);
  writeJson(appraisalPath, appraisal);
  writeJson(replyStylePath, replyStyle);

  return { target, norms, members, selfPosition, appraisal, replyStyle };
}

function listCandidateSessions() {
  const store = readJson(sessionsStorePath, {});
  return Object.entries(store)
    .filter(([key]) => key.startsWith("agent:main:qq:group:"))
    .map(([key, value]) => ({
      key,
      groupId: key.split(":").at(-1),
      sessionId: value.sessionId ?? null,
      sessionFile: value.sessionFile ?? null,
      updatedAt: value.updatedAt ?? null,
    }))
    .sort((a, b) => Number(b.updatedAt ?? 0) - Number(a.updatedAt ?? 0));
}

function bindTargetGroup(groupId, groupName) {
  const files = ensureFiles();
  const nextTarget = {
    ...files.target,
    updatedAt: nowIso(),
    groupId: String(groupId),
    ...(groupName ? { groupName: String(groupName) } : {}),
  };
  const nextNorms = {
    ...files.norms,
    updatedAt: nowIso(),
    groupId: String(groupId),
    groupName: nextTarget.groupName,
  };
  const nextMembers = {
    ...files.members,
    updatedAt: nowIso(),
    groupId: String(groupId),
    groupName: nextTarget.groupName,
  };
  const nextSelfPosition = {
    ...files.selfPosition,
    updatedAt: nowIso(),
    groupId: String(groupId),
    groupName: nextTarget.groupName,
  };
  const nextAppraisal = {
    ...files.appraisal,
    updatedAt: nowIso(),
    groupId: String(groupId),
    groupName: nextTarget.groupName,
  };

  writeJson(targetGroupPath, nextTarget);
  writeJson(normsPath, nextNorms);
  writeJson(membersPath, nextMembers);
  writeJson(selfPositionPath, nextSelfPosition);
  writeJson(appraisalPath, nextAppraisal);

  return {
    ok: true,
    target: nextTarget,
  };
}

function extractJsonBlock(text, label) {
  const pattern = new RegExp(
    `${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}:\\n\`\`\`json\\n([\\s\\S]*?)\\n\`\`\``,
  );
  const match = text.match(pattern);
  if (!match) {
    return null;
  }
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

function normalizeMessageBody(text) {
  return text
    .replace(/\[Queued messages while agent was busy\][\s\S]*?(?=---\nQueued #|$)/g, "")
    .replace(/Conversation info \(untrusted metadata\):\n```json[\s\S]*?```/g, "")
    .replace(/Sender \(untrusted metadata\):\n```json[\s\S]*?```/g, "")
    .replace(/^\[media attached:[^\n]+\n?/gm, "")
    .replace(/^To send an image back,[^\n]+\n?/gm, "")
    .replace(/^\[图片\d+ URL:[^\n]+\n?/gm, "")
    .replace(/^\[QQ:\d+\]\s*/gm, "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .join("\n")
    .trim();
}

function splitQueuedSections(text) {
  if (!text.includes("[Queued messages while agent was busy]")) {
    return [text];
  }
  const sections = text.split(/\n---\nQueued #\d+\n/g).map((entry) => entry.trim()).filter(Boolean);
  return sections.length > 0 ? sections : [text];
}

function parseUserEntry(entry) {
  const sections = splitQueuedSections(entry);
  return sections
    .map((section) => {
      const conversationInfo = extractJsonBlock(section, "Conversation info (untrusted metadata)");
      const senderInfo = extractJsonBlock(section, "Sender (untrusted metadata)");
      const body = normalizeMessageBody(section);
      if (!conversationInfo?.group_subject || !senderInfo?.id || !body) {
        return null;
      }
      return {
        groupId: String(conversationInfo.group_subject),
        senderId: String(senderInfo.id),
        senderName:
          String(senderInfo.name ?? conversationInfo.sender ?? senderInfo.label ?? "").trim() ||
          String(senderInfo.id),
        conversationLabel: String(conversationInfo.conversation_label ?? "").trim(),
        timestamp: String(conversationInfo.timestamp ?? "").trim(),
        message: body,
      };
    })
    .filter(Boolean);
}

function loadTranscriptEntries(sessionFile) {
  const source = fs.readFileSync(sessionFile, "utf8");
  return source
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function detectHumorStyle(messages) {
  const humor = new Set();
  const joined = messages.join("\n");
  if (/喵|狐|猫娘|尾巴|主银/.test(joined)) {
    humor.add("roleplay-like");
  }
  if (/哈哈|hhh|www|233|笑/.test(joined)) {
    humor.add("light-meme");
  }
  if (/坏蛋|笨蛋|坏家伙|大憨憨|摸|抱/.test(joined)) {
    humor.add("teasing");
  }
  if (/QAQ|>\/<\/|>\/\/<\/|！{2,}|\?{2,}/.test(joined)) {
    humor.add("high-emotion");
  }
  return [...humor];
}

function deriveTopicClusters(messages) {
  const buckets = new Map();
  const keywords = [
    "签到",
    "点赞",
    "猫",
    "狐",
    "主银",
    "晚风",
    "抱",
    "尾巴",
    "喵",
    "图片",
  ];
  for (const keyword of keywords) {
    const hits = messages.filter((message) => message.includes(keyword)).length;
    if (hits > 0) {
      buckets.set(keyword, hits);
    }
  }
  return [...buckets.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([keyword, hits]) => ({ keyword, hits }));
}

function uniqueStrings(values) {
  return [...new Set(values.map((value) => String(value ?? "").trim()).filter(Boolean))];
}

function roundRate(value) {
  return Number(value.toFixed(2));
}

function countMatchingMessages(messages, pattern) {
  return messages.filter((message) => pattern.test(message)).length;
}

function topLabels(entries, limit = 4) {
  return [...entries.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([label]) => label);
}

function detectLaughterForms(messages) {
  const counts = new Map();
  for (const message of messages) {
    if (/(哈){2,}/u.test(message)) {
      counts.set("哈哈", (counts.get("哈哈") ?? 0) + 1);
    }
    if (/\b[hH]{2,}\b/.test(message)) {
      counts.set("hhh", (counts.get("hhh") ?? 0) + 1);
    }
    if (/\b[wW]{2,}\b|ｗ{2,}/u.test(message)) {
      counts.set("www", (counts.get("www") ?? 0) + 1);
    }
    if (/233+/.test(message)) {
      counts.set("233", (counts.get("233") ?? 0) + 1);
    }
    if (/笑死|笑死我|绷不住/u.test(message)) {
      counts.set("笑死", (counts.get("笑死") ?? 0) + 1);
    }
  }
  return topLabels(counts, 4);
}

function detectSentenceFinalParticles(messages) {
  const counts = new Map();
  const particles = ["啊", "呀", "吧", "嘛", "啦", "呢", "呐", "哦", "噢", "欸", "诶", "喵", "哇"];
  for (const message of messages) {
    const trimmed = message.trim();
    for (const particle of particles) {
      if (new RegExp(`${particle}[!！?？~～…]*$`, "u").test(trimmed)) {
        counts.set(particle, (counts.get(particle) ?? 0) + 1);
      }
    }
  }
  return topLabels(counts, 5);
}

function analyzeMessageStyle(messages) {
  const punctuationPattern = /[，。！？、,.!?;；:：~～…]/u;
  const terminalPunctuationPattern = /[。！？!?~～…]$/u;
  const repeatedCharPattern = /([哈啊呀啦喵欸诶哇嗯哦噢呢嘛吧])\1{1,}/u;
  const emojiLikePattern = /[\p{Extended_Pictographic}~～^><=_/\\|()[\]{}]/u;
  const total = Math.max(1, messages.length);
  const shortMessages = messages.filter((message) => message.length <= 12).length;
  const noPunctuation = messages.filter((message) => !punctuationPattern.test(message)).length;
  const terminalPunctuation = messages.filter((message) => terminalPunctuationPattern.test(message.trim())).length;
  const multiLine = messages.filter((message) => message.includes("\n")).length;
  const ellipsis = countMatchingMessages(messages, /…|\.\.\./u);
  const repeatedChar = countMatchingMessages(messages, repeatedCharPattern);
  const emojiLike = countMatchingMessages(messages, emojiLikePattern);
  const laughterForms = detectLaughterForms(messages);
  const sentenceFinalParticles = detectSentenceFinalParticles(messages);

  return {
    sampleSize: messages.length,
    shortMessageRate: roundRate(shortMessages / total),
    noPunctuationRate: roundRate(noPunctuation / total),
    terminalPunctuationRate: roundRate(terminalPunctuation / total),
    multiLineRate: roundRate(multiLine / total),
    ellipsisRate: roundRate(ellipsis / total),
    repeatedCharRate: roundRate(repeatedChar / total),
    emojiLikeRate: roundRate(emojiLike / total),
    laughterForms,
    sentenceFinalParticles,
  };
}

function inferPunctuationStyle(styleSignals) {
  if (styleSignals.noPunctuationRate >= 0.6) {
    return "very-sparse";
  }
  if (styleSignals.noPunctuationRate >= 0.4) {
    return "sparse-by-default";
  }
  if (styleSignals.terminalPunctuationRate >= 0.55) {
    return "explicit-end-punctuation";
  }
  return "mixed";
}

function buildReplyStyle(files, analysis) {
  const base = defaultReplyStyle();
  const existing = files.replyStyle ?? base;
  const styleSignals = analyzeMessageStyle(analysis.messageBodies);
  const punctuationStyle = inferPunctuationStyle(styleSignals);
  const targetLength =
    analysis.avgLength <= 10 ? "very-short" : analysis.avgLength <= 18 ? "short" : "mixed";
  const sentenceCount =
    styleSignals.shortMessageRate >= 0.65 ? "1 by default, 2 only when needed" : "1-2 short sentences";
  const cadence =
    styleSignals.multiLineRate <= 0.15 ? "single-line bursts" : "fast and natural";
  const explanationMode =
    styleSignals.shortMessageRate >= 0.55 ? "expand only when someone really asks" : "only when explicitly useful";
  const stretchiness =
    styleSignals.repeatedCharRate >= 0.15 ? "light-allowed" : "rare";
  const observedSignals = {
    sampleSize: styleSignals.sampleSize,
    avgMessageLength: roundRate(analysis.avgLength),
    shortMessageRate: styleSignals.shortMessageRate,
    noPunctuationRate: styleSignals.noPunctuationRate,
    terminalPunctuationRate: styleSignals.terminalPunctuationRate,
    multiLineRate: styleSignals.multiLineRate,
    ellipsisRate: styleSignals.ellipsisRate,
    repeatedCharRate: styleSignals.repeatedCharRate,
    emojiLikeRate: styleSignals.emojiLikeRate,
    laughterForms: styleSignals.laughterForms,
    sentenceFinalParticles: styleSignals.sentenceFinalParticles,
  };

  const dynamicDo = [
    styleSignals.noPunctuationRate >= 0.45
      ? "Default to bare short lines; do not add punctuation just to make the sentence look complete."
      : null,
    styleSignals.shortMessageRate >= 0.55
      ? "Keep replies short enough to feel like live banter, not a composed paragraph."
      : null,
    styleSignals.laughterForms.length > 0
      ? `If a laugh cue fits, prefer the group's own forms like ${styleSignals.laughterForms.join(" / ")}.`
      : null,
    styleSignals.sentenceFinalParticles.length > 0
      ? `Use light sentence-final particles only if they fit, such as ${styleSignals.sentenceFinalParticles.join(" / ")}.`
      : null,
    styleSignals.repeatedCharRate >= 0.15
      ? "Playful repeated characters are acceptable in the right moment, but keep it light."
      : null,
  ].filter(Boolean);

  const dynamicDont = [
    styleSignals.noPunctuationRate >= 0.45
      ? "Do not automatically end every line with commas or periods."
      : null,
    styleSignals.shortMessageRate >= 0.55
      ? "Do not answer one-line teasing with a full explanatory paragraph."
      : null,
    styleSignals.multiLineRate <= 0.15
      ? "Do not split casual replies into stacked mini paragraphs unless someone explicitly asked for detail."
      : null,
  ].filter(Boolean);

  const dynamicPreferred = [
    punctuationStyle === "very-sparse" || punctuationStyle === "sparse-by-default"
      ? "默认不补句号"
      : null,
    styleSignals.shortMessageRate >= 0.55 ? "短句裸回" : null,
    styleSignals.laughterForms.length > 0 ? "笑法跟群里走" : null,
    styleSignals.sentenceFinalParticles.length > 0 ? "轻一点语气词收尾" : null,
    styleSignals.repeatedCharRate >= 0.15 ? "偶尔顺着语气拖一点字" : null,
  ].filter(Boolean);

  return {
    ...base,
    ...existing,
    updatedAt: nowIso(),
    groupName: files.target.groupName ?? existing.groupName ?? base.groupName,
    groupId: files.target.groupId ?? existing.groupId ?? base.groupId,
    targetStyle: {
      ...base.targetStyle,
      ...(existing.targetStyle ?? {}),
      voice: "casual-group-member",
      length: targetLength,
      sentenceCount,
      cadence,
      explanationMode,
      bodyFirstWhenPossible: existing.targetStyle?.bodyFirstWhenPossible ?? true,
      punctuation: punctuationStyle,
      punctuationMimicry: "follow-current-speaker",
      laughterForms: styleSignals.laughterForms,
      sentenceFinalParticles: styleSignals.sentenceFinalParticles,
      stretchiness,
    },
    observedSignals,
    do: uniqueStrings([...base.do, ...(existing.do ?? []), ...dynamicDo]),
    dont: uniqueStrings([...base.dont, ...(existing.dont ?? []), ...dynamicDont]),
    antiPatterns: uniqueStrings([...(existing.antiPatterns ?? []), ...base.antiPatterns]),
    preferredPatterns: uniqueStrings([...base.preferredPatterns, ...(existing.preferredPatterns ?? []), ...dynamicPreferred]),
  };
}

function analyzeMessages(messageEntries) {
  const membersMap = new Map();

  for (const message of messageEntries) {
    const existing = membersMap.get(message.senderId) ?? {
      qqId: message.senderId,
      displayName: message.senderName,
      roleInGroup: "unknown",
      interactionStyle: [],
      relationshipWeight: 0.1,
      trust: 0.1,
      teasingTolerance: null,
      sensitivityFlags: [],
      runningTopics: [],
      knownPatterns: [],
      messageCount: 0,
      lastSeenAt: null,
      recentSamples: [],
    };

    existing.displayName = message.senderName;
    existing.messageCount = Number(existing.messageCount ?? 0) + 1;
    existing.lastSeenAt = message.timestamp;
    existing.recentSamples = [...(existing.recentSamples ?? []), message.message].slice(-3);
    if (/喵|主银|尾巴|抱/.test(message.message)) {
      existing.interactionStyle = [...new Set([...(existing.interactionStyle ?? []), "playful-roleplay"])];
      existing.teasingTolerance ??= 0.7;
    }
    if (/签到|点赞/.test(message.message)) {
      existing.knownPatterns = [...new Set([...(existing.knownPatterns ?? []), "system-ritual-participant"])];
    }

    membersMap.set(message.senderId, existing);
  }

  const messageBodies = messageEntries.map((entry) => entry.message);
  const avgLength =
    messageBodies.reduce((sum, message) => sum + message.length, 0) / Math.max(1, messageBodies.length);
  const exclamations = messageBodies.filter((message) => /!|！/.test(message)).length;
  const questions = messageBodies.filter((message) => /\?|？/.test(message)).length;
  const roleplay = messageBodies.filter((message) => /喵|主银|狐|猫娘|尾巴/.test(message)).length;

  return {
    membersMap,
    messageBodies,
    avgLength,
    exclamations,
    questions,
    roleplay,
  };
}

function applyAnalysisToState(files, groupId, analysis, sourceLabel) {
  const { membersMap, messageBodies, avgLength, exclamations, questions, roleplay } = analysis;

  const nextNorms = {
    ...files.norms,
    updatedAt: nowIso(),
    groupId: String(groupId),
    tone: roleplay / Math.max(1, messageBodies.length) > 0.35 ? "playful-roleplay" : "mixed",
    humorStyle: detectHumorStyle(messageBodies),
    allowedBoldness: Math.min(0.9, 0.25 + roleplay / Math.max(1, messageBodies.length)),
    replyFrequencyExpectation:
      messageBodies.length >= 20 ? "medium" : messageBodies.length >= 8 ? "light-medium" : "light",
    mentionSensitivity: "high",
    topicClusters: deriveTopicClusters(messageBodies),
    conflictTriggers: files.norms.conflictTriggers ?? [],
    observedStats: {
      totalMessages: messageBodies.length,
      uniqueSpeakers: membersMap.size,
      avgMessageLength: Number(avgLength.toFixed(2)),
      exclamationRate: Number((exclamations / Math.max(1, messageBodies.length)).toFixed(2)),
      questionRate: Number((questions / Math.max(1, messageBodies.length)).toFixed(2)),
      roleplayRate: Number((roleplay / Math.max(1, messageBodies.length)).toFixed(2)),
    },
  };

  const nextMembers = {
    ...files.members,
    updatedAt: nowIso(),
    groupId: String(groupId),
    members: [...membersMap.values()].sort(
      (a, b) => Number(b.messageCount ?? 0) - Number(a.messageCount ?? 0),
    ),
  };

  const nextAppraisal = {
    ...files.appraisal,
    updatedAt: nowIso(),
    groupId: String(groupId),
    groupMood:
      roleplay / Math.max(1, messageBodies.length) > 0.35
        ? "playful"
        : exclamations / Math.max(1, messageBodies.length) > 0.4
          ? "excited"
          : "mixed",
    groupNoise: Number(Math.min(1, messageBodies.length / 40).toFixed(2)),
    dramaRisk: Number(
      Math.min(
        1,
        messageBodies.filter((message) => /吵|闭嘴|坏蛋|滚|烦/.test(message)).length / 10,
      ).toFixed(2),
    ),
    novelty: Number(Math.min(1, membersMap.size / 12).toFixed(2)),
    myBelonging: files.target.groupId ? 0.4 : 0.15,
    recentAcceptance: Number((roleplay / Math.max(1, messageBodies.length)).toFixed(2)),
    recentRejection: 0,
    socialSafety: Number(
      Math.max(
        0,
        0.82 -
          Math.min(
            0.6,
            messageBodies.filter((message) => /滚|闭嘴|烦|吵/.test(message)).length / 10,
          ),
      ).toFixed(2),
    ),
  };

  const nextSelfPosition = {
    ...files.selfPosition,
    updatedAt: nowIso(),
    groupId: String(groupId),
    currentRole:
      nextNorms.tone === "playful-roleplay" ? "light-amused" : "calm-recurring-presence",
    desiredRole:
      nextNorms.tone === "playful-roleplay"
        ? "calm-recurring-presence-with-humor"
        : "calm-recurring-presence",
    allowedPresence: nextNorms.replyFrequencyExpectation,
    socialRankEstimate: Number(Math.min(1, membersMap.size / 20).toFixed(2)),
    playfulnessLevel: Number(Math.min(0.8, 0.2 + roleplay / Math.max(1, messageBodies.length)).toFixed(2)),
    attentionBudget: Number(
      Math.max(0.2, Math.min(0.65, 0.2 + messageBodies.length / 60)).toFixed(2),
    ),
  };
  const nextReplyStyle = buildReplyStyle(files, analysis);

  writeJson(normsPath, nextNorms);
  writeJson(membersPath, nextMembers);
  writeJson(appraisalPath, nextAppraisal);
  writeJson(selfPositionPath, nextSelfPosition);
  writeJson(replyStylePath, nextReplyStyle);

  appendJsonl(episodesPath, {
    ts: nowIso(),
    source: sourceLabel,
    groupId: String(groupId),
    observedMessages: messageBodies.length,
    uniqueSpeakers: membersMap.size,
    inferredTone: nextNorms.tone,
    humorStyle: nextNorms.humorStyle,
    topicClusters: nextNorms.topicClusters,
    punctuationStyle: nextReplyStyle.targetStyle?.punctuation,
    laughterForms: nextReplyStyle.observedSignals?.laughterForms ?? [],
  });

  return {
    ok: true,
    groupId: String(groupId),
    observedMessages: messageBodies.length,
    uniqueSpeakers: membersMap.size,
    tone: nextNorms.tone,
    humorStyle: nextNorms.humorStyle,
    punctuationStyle: nextReplyStyle.targetStyle?.punctuation,
    laughterForms: nextReplyStyle.observedSignals?.laughterForms ?? [],
    topMembers: nextMembers.members.slice(0, 5).map((member) => ({
      qqId: member.qqId,
      displayName: member.displayName,
      messageCount: member.messageCount,
    })),
  };
}

function updateFromTranscript(sessionFile, explicitGroupId = null) {
  const files = ensureFiles();
  const entries = loadTranscriptEntries(sessionFile);
  const parsedMessages = [];

  for (const entry of entries) {
    if (entry?.type !== "message" || entry?.message?.role !== "user") {
      continue;
    }
    const textBlocks = Array.isArray(entry.message.content)
      ? entry.message.content
          .filter((item) => item?.type === "text" && typeof item.text === "string")
          .map((item) => item.text)
      : [];
    if (textBlocks.length === 0) {
      continue;
    }
    for (const block of textBlocks) {
      for (const parsed of parseUserEntry(block)) {
        if (explicitGroupId && parsed.groupId !== String(explicitGroupId)) {
          continue;
        }
        if (files.target.groupId && parsed.groupId !== String(files.target.groupId)) {
          continue;
        }
        parsedMessages.push(parsed);
      }
    }
  }

  if (parsedMessages.length === 0) {
    return {
      ok: false,
      reason: "no-matching-group-messages",
      sessionFile,
    };
  }

  const groupId = explicitGroupId || files.target.groupId || parsedMessages[0].groupId;
  const messages = parsedMessages.filter((entry) => entry.groupId === String(groupId));
  return {
    sessionFile,
    ...applyAnalysisToState(files, groupId, analyzeMessages(messages), sessionFile),
  };
}

function ingestLiveMessage(payload) {
  const files = ensureFiles();
  const groupId = String(payload.groupId ?? "");
  if (!groupId) {
    return { ok: false, reason: "missing-group-id" };
  }
  if (files.target.groupId && String(files.target.groupId) !== groupId) {
    return { ok: false, reason: "not-target-group", targetGroupId: files.target.groupId };
  }
  const text = String(payload.message ?? "").trim();
  const senderId = String(payload.senderId ?? "").trim();
  if (!senderId || !text) {
    return { ok: false, reason: "missing-sender-or-message" };
  }

  const existingMembers = readJson(membersPath, defaultMembers()).members ?? [];
  const membersMap = new Map(existingMembers.map((member) => [String(member.qqId), member]));
  const currentMessageCount = existingMembers.reduce(
    (sum, member) => sum + Number(member.messageCount ?? 0),
    0,
  );

  const messageEntry = {
    groupId,
    senderId,
    senderName: String(payload.senderName ?? senderId).trim() || senderId,
    conversationLabel: String(payload.conversationLabel ?? "").trim(),
    timestamp: String(payload.timestamp ?? nowIso()).trim(),
    message: text,
  };

  const baselineMessages = [];
  for (const member of existingMembers) {
    const samples = Array.isArray(member.recentSamples) ? member.recentSamples : [];
    for (const sample of samples.slice(-2)) {
      baselineMessages.push({
        groupId,
        senderId: String(member.qqId),
        senderName: String(member.displayName ?? member.qqId),
        conversationLabel: "",
        timestamp: String(member.lastSeenAt ?? ""),
        message: String(sample),
      });
    }
  }
  const workingMessages = [...baselineMessages, messageEntry].slice(-30);
  const result = applyAnalysisToState(files, groupId, analyzeMessages(workingMessages), "live-message");

  appendJsonl(episodesPath, {
    ts: nowIso(),
    source: "live-message-detail",
    groupId,
    senderId,
    senderName: messageEntry.senderName,
    messagePreview: text.slice(0, 200),
    messageCountBefore: currentMessageCount,
    messageCountAfter: currentMessageCount + 1,
  });

  return result;
}

function usage() {
  process.stderr.write(
    [
      "Usage:",
      "  node scripts/group-social-engine.mjs status",
      "  node scripts/group-social-engine.mjs bind --group-id <id> [--group-name <name>]",
      "  node scripts/group-social-engine.mjs ingest --session-file <path> [--group-id <id>]",
      "  node scripts/group-social-engine.mjs ingest-live --group-id <id> --sender-id <id> --sender-name <name> --message <text> [--timestamp <text>] [--conversation-label <text>]",
      "  node scripts/group-social-engine.mjs ingest-target",
    ].join("\n") + "\n",
  );
  process.exit(1);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0];
  if (!command) {
    usage();
  }

  if (command === "status") {
    const files = ensureFiles();
    printJson({
      target: files.target,
      norms: files.norms,
      selfPosition: files.selfPosition,
      appraisal: files.appraisal,
      replyStyle: files.replyStyle,
      candidates: listCandidateSessions(),
    });
    return;
  }

  if (command === "bind") {
    if (!args["group-id"]) {
      usage();
    }
    printJson(bindTargetGroup(String(args["group-id"]), args["group-name"] ? String(args["group-name"]) : null));
    return;
  }

  if (command === "ingest") {
    if (!args["session-file"]) {
      usage();
    }
    printJson(
      updateFromTranscript(
        path.resolve(String(args["session-file"])),
        args["group-id"] ? String(args["group-id"]) : null,
      ),
    );
    return;
  }

  if (command === "ingest-target") {
    const files = ensureFiles();
    if (!files.target.groupId) {
      printJson({
        ok: false,
        reason: "target-group-id-not-bound",
        target: files.target,
        candidates: listCandidateSessions(),
      });
      return;
    }
    const candidate = listCandidateSessions().find(
      (entry) => String(entry.groupId) === String(files.target.groupId),
    );
    if (!candidate?.sessionFile) {
      printJson({
        ok: false,
        reason: "target-session-file-not-found",
        target: files.target,
        candidates: listCandidateSessions(),
      });
      return;
    }
    printJson(updateFromTranscript(candidate.sessionFile, String(files.target.groupId)));
    return;
  }

  if (command === "ingest-live") {
    printJson(
      ingestLiveMessage({
        groupId: args["group-id"],
        senderId: args["sender-id"],
        senderName: args["sender-name"],
        message: args.message,
        timestamp: args.timestamp,
        conversationLabel: args["conversation-label"],
      }),
    );
    return;
  }

  usage();
}

main();
