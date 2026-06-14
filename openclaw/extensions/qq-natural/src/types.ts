export type QqNaturalChatConfig = {
  enabled?: boolean;
  applyToGroups?: boolean;
  applyToDirect?: boolean;
  splitMessages?: boolean;
  removeDecorativeEmoji?: boolean;
  hardBannedSymbols?: string[];
  defaultPersona?: string;
  allowPersonaSwitch?: boolean;
};

export type QqStudyModeConfig = {
  enabled?: boolean;
  directOnly?: boolean;
  autoSolveLikelyProblemImages?: boolean;
  alwaysRenderHtml?: boolean;
  answerStyle?: string;
  skills?: string[];
  systemPrompt?: string;
};

export type QqFriendRequestConfig = {
  autoApproveEnabled?: boolean;
  minQqLevel?: number;
};

export type QqGroupConfig = {
  requireMention?: boolean;
  enabled?: boolean;
  skills?: string[];
  systemPrompt?: string;
  socialJoinEnabled?: boolean;
  socialJoinCooldownMinutes?: number;
  naturalChat?: QqNaturalChatConfig;
};

export type QqAccountConfig = {
  name?: string;
  enabled?: boolean;
  selfId?: string;
  autoLaunch?: boolean;
  preventIdleSleep?: boolean;
  executablePath?: string;
  launchArgs?: string[];
  blockedUserIds?: string[];
  friendRequests?: QqFriendRequestConfig;
  allowFrom?: string[];
  groupAllowFrom?: string[];
  groups?: Record<string, QqGroupConfig>;
  mediaMaxMb?: number;
  textChunkLimit?: number;
  responsePrefix?: string;
  naturalChat?: QqNaturalChatConfig;
  studyMode?: QqStudyModeConfig;
};

export type QqConfig = QqAccountConfig & {
  accounts?: Record<string, QqAccountConfig>;
  defaultAccount?: string;
  listenHost?: string;
  listenPort?: number;
  websocketPath?: string;
};

export type CoreConfig = {
  channels?: {
    qq?: QqConfig;
  };
  session?: {
    store?: string;
  };
  [key: string]: unknown;
};

export type ResolvedQqAccount = {
  accountId: string;
  enabled: boolean;
  name?: string;
  selfId?: string;
  autoLaunch: boolean;
  preventIdleSleep: boolean;
  executablePath: string;
  launchArgs: string[];
  config: QqAccountConfig;
  listenHost: string;
  listenPort: number;
  websocketPath: string;
};

export type OneBotMessageSegment = {
  type: string;
  data?: Record<string, string | number | boolean | undefined>;
};

export type ParsedQqMediaSegment = {
  type: "image" | "emoji" | "animated_emoji";
  sourceType: string;
  url?: string;
  label?: string;
  rawFile?: string;
  rawUrl?: string;
  preferredRef?: string;
  localFileResolved?: boolean;
  data?: Record<string, string | number | boolean | undefined>;
};

export type OneBotSender = {
  user_id?: number;
  nickname?: string;
  card?: string;
};

export type OneBotMessageEvent = {
  post_type: "message";
  self_id: number;
  message_id?: number;
  message_type: "private" | "group";
  sub_type?: string;
  time?: number;
  user_id: number;
  group_id?: number;
  raw_message?: string;
  message?: string | OneBotMessageSegment[];
  sender?: OneBotSender;
};

export type OneBotMetaEvent = {
  post_type: "meta_event";
  self_id: number;
  meta_event_type?: string;
  sub_type?: string;
  time?: number;
};

export type OneBotPokeNoticeEvent = {
  post_type: "notice";
  self_id: number;
  notice_type: "notify";
  sub_type: "poke";
  time?: number;
  user_id: number;
  target_id?: number;
  group_id?: number;
  sender_id?: number;
  raw_info?: unknown;
};

export type OneBotFriendRequestEvent = {
  post_type: "request";
  self_id: number;
  request_type: "friend";
  time?: number;
  user_id: number;
  comment?: string;
  flag: string;
};

export type OneBotApiResponse = {
  status?: string;
  retcode?: number;
  data?: unknown;
  message?: string;
  wording?: string;
  echo?: string;
};

export type OneBotInboundFrame =
  | OneBotMessageEvent
  | OneBotMetaEvent
  | OneBotPokeNoticeEvent
  | OneBotFriendRequestEvent
  | OneBotApiResponse;

export type ParsedQqMessage = {
  text: string;
  isReply: boolean;
  replyToMessageId?: string;
  wasMentioned: boolean;
  mentionIds: string[];
  imageUrls: string[];
  mediaSegments: ParsedQqMediaSegment[];
  hasOnlyMediaLike: boolean;
};
