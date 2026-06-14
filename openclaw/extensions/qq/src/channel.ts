import type {
  ChannelPlugin,
  OpenClawConfig,
  OutboundReplyPayload,
} from "../../../dist/plugin-sdk/index.js";
import {
  buildChannelSendResult,
  sendPayloadWithChunkedTextAndMedia,
} from "../../../dist/plugin-sdk/index.js";
import { listQqAccountIds, resolveDefaultQqAccountId, resolveQqAccount } from "./accounts.js";
import { sendQqMedia, sendQqText } from "./service.js";
import { getQqRuntime } from "./runtime.js";
import type { CoreConfig, ResolvedQqAccount } from "./types.js";

const meta = {
  id: "qq",
  label: "QQ",
  selectionLabel: "QQ (NapCat / OneBot V11)",
  docsPath: "/channels/qq",
  docsLabel: "qq",
  blurb: "QQ channel via NapCat / OneBot V11 reverse WebSocket.",
  aliases: ["onebot-qq", "napcat-qq"],
  order: 85,
  quickstartAllowFrom: true,
};

function parseOutboundTarget(target: string): { kind: "user" | "group"; id: string } {
  const trimmed = target.trim();
  if (trimmed.startsWith("group:")) {
    return { kind: "group", id: trimmed.slice("group:".length) };
  }
  if (trimmed.startsWith("user:")) {
    return { kind: "user", id: trimmed.slice("user:".length) };
  }
  if (/^group:\d+$/.test(trimmed) || /^user:\d+$/.test(trimmed)) {
    const [kind, id] = trimmed.split(":", 2) as ["group" | "user", string];
    return { kind, id };
  }
  return { kind: "user", id: trimmed.replace(/^qq:/i, "") };
}

async function deliverQqPayload(params: {
  cfg: OpenClawConfig;
  accountId?: string;
  to: string;
  payload: OutboundReplyPayload;
}) {
  const { cfg, accountId, to } = params;
  const parsed = parseOutboundTarget(to);
  return {
    cfg: cfg as CoreConfig,
    accountId,
    targetKind: parsed.kind,
    targetId: parsed.id,
  };
}

export const qqPlugin: ChannelPlugin<ResolvedQqAccount> = {
  id: "qq",
  meta,
  capabilities: {
    chatTypes: ["direct", "group"],
    reactions: false,
    threads: false,
    media: true,
    nativeCommands: false,
    blockStreaming: true,
  },
  reload: { configPrefixes: ["channels.qq"] },
  configSchema: {
    schema: {
      type: "object",
      additionalProperties: false,
      properties: {
        enabled: { type: "boolean" },
        name: { type: "string" },
        selfId: { type: "string" },
        autoLaunch: { type: "boolean" },
        preventIdleSleep: { type: "boolean" },
        naturalChat: {
          type: "object",
          additionalProperties: false,
          properties: {
            enabled: { type: "boolean" },
            applyToGroups: { type: "boolean" },
            applyToDirect: { type: "boolean" },
            splitMessages: { type: "boolean" },
            removeDecorativeEmoji: { type: "boolean" },
            hardBannedSymbols: { type: "array", items: { type: "string" } },
          },
        },
        studyMode: {
          type: "object",
          additionalProperties: false,
          properties: {
            enabled: { type: "boolean" },
            directOnly: { type: "boolean" },
            autoSolveLikelyProblemImages: { type: "boolean" },
            alwaysRenderHtml: { type: "boolean" },
            answerStyle: { type: "string" },
            skills: { type: "array", items: { type: "string" } },
            systemPrompt: { type: "string" },
          },
        },
        executablePath: { type: "string" },
        launchArgs: { type: "array", items: { type: "string" } },
        listenHost: { type: "string" },
        listenPort: { type: "number" },
        websocketPath: { type: "string" },
        allowFrom: { type: "array", items: { type: "string" } },
        groupAllowFrom: { type: "array", items: { type: "string" } },
      },
    },
  },
  config: {
    listAccountIds: (cfg) => listQqAccountIds(cfg as CoreConfig),
    resolveAccount: (cfg, accountId) => resolveQqAccount({ cfg: cfg as CoreConfig, accountId }),
    defaultAccountId: (cfg) => resolveDefaultQqAccountId(cfg as CoreConfig),
    isConfigured: (account) => account.enabled,
    describeAccount: (account) => ({
      accountId: account.accountId,
      name: account.name,
      enabled: account.enabled,
      configured: account.enabled,
      selfId: account.selfId,
      autoLaunch: account.autoLaunch,
      preventIdleSleep: account.preventIdleSleep,
      naturalChat: account.config.naturalChat,
      studyMode: account.config.studyMode,
      executablePath: account.executablePath,
      listenHost: account.listenHost,
      listenPort: account.listenPort,
      websocketPath: account.websocketPath,
    }),
  },
  groups: {
    resolveRequireMention: ({ cfg, groupId, accountId }) => {
      const account = resolveQqAccount({ cfg: cfg as CoreConfig, accountId });
      const groups = account.config.groups;
      if (!groups || !groupId) {
        return true;
      }
      const groupConfig = groups[groupId] ?? groups["*"];
      return groupConfig?.requireMention ?? true;
    },
  },
  messaging: {
    normalizeTarget: (target) => target.trim().replace(/^qq:/i, ""),
    targetResolver: {
      looksLikeId: (id) => /^((group|user):)?\d+$/.test(id?.trim() ?? ""),
      hint: "<user:qq|group:groupId>",
    },
  },
  directory: {
    self: async () => null,
    listPeers: async () => [],
    listGroups: async () => [],
  },
  outbound: {
    deliveryMode: "direct",
    textChunkLimit: 1500,
    chunker: (text, limit) => getQqRuntime().channel.text.chunkMarkdownText(text, limit),
    sendPayload: async (ctx) =>
      await sendPayloadWithChunkedTextAndMedia({
        ctx,
        textChunkLimit: qqPlugin.outbound!.textChunkLimit,
        chunker: qqPlugin.outbound!.chunker,
        sendText: (nextCtx) => qqPlugin.outbound!.sendText!(nextCtx),
        sendMedia: (nextCtx) => qqPlugin.outbound!.sendMedia!(nextCtx),
        emptyResult: { channel: "qq", messageId: "", chatId: ctx.to },
      }),
    sendText: async ({ cfg, to, text, accountId }) => {
      const target = await deliverQqPayload({
        cfg,
        to,
        accountId,
        payload: { text },
      });
      await sendQqText({
        ...target,
        text,
      });
      return {
        ...buildChannelSendResult("qq", {
          ok: true,
          messageId: `qq:${Date.now()}`,
        }),
        chatId: to,
      };
    },
    sendMedia: async ({ cfg, to, text, mediaUrl, accountId }) => {
      const target = await deliverQqPayload({
        cfg,
        to,
        accountId,
        payload: { text, mediaUrl },
      });
      await sendQqMedia({
        ...target,
        text,
        mediaUrl,
      });
      return {
        ...buildChannelSendResult("qq", {
          ok: true,
          messageId: `qq:${Date.now()}`,
        }),
        chatId: to,
      };
    },
  },
};
