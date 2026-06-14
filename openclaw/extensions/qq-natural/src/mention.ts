type QqGroupMemberLike = Record<string, unknown>;

function readTrimmedString(value: unknown): string | null {
  if (typeof value !== "string") {
    if (typeof value === "number" && Number.isFinite(value)) {
      return String(value);
    }
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function uniqueStrings(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.map((value) => value?.trim() ?? "").filter(Boolean))];
}

export function normalizeQqMentionLookup(value: string): string {
  return value.trim().replace(/^@+/u, "").replace(/\s+/gu, " ").toLowerCase();
}

export type QqMentionResolvedMember = {
  userId: string;
  nickname: string | null;
  card: string | null;
  displayName: string;
  match: "user-id" | "name-exact" | "name-fuzzy";
};

function toMentionCandidate(member: QqGroupMemberLike): (QqMentionResolvedMember & { aliases: string[] }) | null {
  const userId = readTrimmedString(member.user_id ?? member.userId ?? member.id);
  if (!userId) {
    return null;
  }
  const nickname = readTrimmedString(member.nickname);
  const card = readTrimmedString(member.card);
  const displayName = card || nickname || userId;
  return {
    userId,
    nickname,
    card,
    displayName,
    match: "name-exact",
    aliases: uniqueStrings([card, nickname, userId]),
  };
}

function distinctCandidates(
  candidates: Array<QqMentionResolvedMember & { aliases: string[] }>,
): Array<QqMentionResolvedMember & { aliases: string[] }> {
  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    if (seen.has(candidate.userId)) {
      return false;
    }
    seen.add(candidate.userId);
    return true;
  });
}

function formatAmbiguousCandidates(candidates: Array<QqMentionResolvedMember & { aliases: string[] }>): string {
  return candidates
    .slice(0, 5)
    .map((candidate) => `${candidate.displayName}(${candidate.userId})`)
    .join("、");
}

export function findQqMentionMember(params: {
  members: QqGroupMemberLike[];
  mentionUserId?: string;
  mentionName?: string;
}): QqMentionResolvedMember {
  const candidates = distinctCandidates(
    params.members.map((member) => toMentionCandidate(member)).filter(Boolean) as Array<
      QqMentionResolvedMember & { aliases: string[] }
    >,
  );
  const mentionUserId = readTrimmedString(params.mentionUserId);
  if (mentionUserId) {
    const exact = candidates.find((candidate) => candidate.userId === mentionUserId);
    if (exact) {
      return { ...exact, match: "user-id" };
    }
    return {
      userId: mentionUserId,
      nickname: null,
      card: null,
      displayName: mentionUserId,
      match: "user-id",
    };
  }

  const mentionName = normalizeQqMentionLookup(params.mentionName ?? "");
  if (!mentionName) {
    throw new Error("mention_name 或 mention_user_id 至少提供一个");
  }

  const exactMatches = distinctCandidates(
    candidates.filter((candidate) =>
      candidate.aliases.some((alias) => normalizeQqMentionLookup(alias) === mentionName),
    ),
  );
  if (exactMatches.length === 1) {
    return { ...exactMatches[0], match: "name-exact" };
  }
  if (exactMatches.length > 1) {
    throw new Error(`mention_name 匹配到多个群成员: ${formatAmbiguousCandidates(exactMatches)}`);
  }

  const fuzzyMatches = distinctCandidates(
    candidates.filter((candidate) =>
      candidate.aliases.some((alias) => {
        const normalized = normalizeQqMentionLookup(alias);
        return normalized.includes(mentionName) || mentionName.includes(normalized);
      }),
    ),
  );
  if (fuzzyMatches.length === 1) {
    return { ...fuzzyMatches[0], match: "name-fuzzy" };
  }
  if (fuzzyMatches.length > 1) {
    throw new Error(`mention_name 模糊匹配到多个群成员: ${formatAmbiguousCandidates(fuzzyMatches)}`);
  }

  const preview = candidates
    .slice(0, 8)
    .map((candidate) => candidate.displayName)
    .join("、");
  throw new Error(`群里没找到要艾特的人: ${params.mentionName}${preview ? `。可见成员示例: ${preview}` : ""}`);
}

export function buildQqMentionSegments(params: {
  mentionUserId: string;
  text: string;
  replyToMessageId?: string;
}) {
  const mentionUserId = readTrimmedString(params.mentionUserId);
  if (!mentionUserId) {
    throw new Error("mentionUserId required");
  }
  const text = params.text.trim();
  if (!text) {
    throw new Error("text required");
  }
  const message: Array<{ type: string; data: Record<string, string> }> = [];
  const replyToMessageId = readTrimmedString(params.replyToMessageId);
  if (replyToMessageId) {
    message.push({
      type: "reply",
      data: { id: replyToMessageId },
    });
  }
  message.push({
    type: "at",
    data: { qq: mentionUserId },
  });
  message.push({
    type: "text",
    data: { text: text.startsWith(" ") ? text : ` ${text}` },
  });
  return message;
}
