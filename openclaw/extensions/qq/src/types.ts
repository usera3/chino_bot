export type QqNaturalChatConfig = {
  enabled?: boolean;
  applyToGroups?: boolean;
  applyToDirect?: boolean;
  splitMessages?: boolean;
  removeDecorativeEmoji?: boolean;
  hardBannedSymbols?: string[];
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

export type OneBotApiResponse = {
  status?: string;
  retcode?: number;
  data?: unknown;
  message?: string;
  wording?: string;
  echo?: string;
};

export type OneBotInboundFrame = OneBotMessageEvent | OneBotMetaEvent | OneBotApiResponse;

export type ParsedQqMessage = {
  text: string;
  isReply: boolean;
  wasMentioned: boolean;
  mentionIds: string[];
  imageUrls: string[];
};
