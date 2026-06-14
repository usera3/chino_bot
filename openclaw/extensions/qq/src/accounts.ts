import type { CoreConfig, QqConfig, ResolvedQqAccount } from "./types.js";

export const DEFAULT_ACCOUNT_ID = "default";
const DEFAULT_LISTEN_HOST = "127.0.0.1";
const DEFAULT_LISTEN_PORT = 8080;
const DEFAULT_WS_PATH = "/onebot/v11/ws";
const DEFAULT_QQ_EXECUTABLE = "/Applications/QQ.app/Contents/MacOS/QQ";
const DEFAULT_QQ_ARGS = ["--no-sandbox"];

function normalizeAccountId(accountId?: string | null): string {
  const trimmed = accountId?.trim();
  return trimmed ? trimmed : DEFAULT_ACCOUNT_ID;
}

function getQqConfig(cfg: CoreConfig): QqConfig {
  return (cfg.channels?.qq ?? {}) as QqConfig;
}

export function listQqAccountIds(cfg: CoreConfig): string[] {
  if (!cfg.channels?.qq) {
    return [];
  }
  const qq = getQqConfig(cfg);
  const ids = Object.keys(qq.accounts ?? {});
  return ids.length > 0 ? ids : [DEFAULT_ACCOUNT_ID];
}

export function resolveDefaultQqAccountId(cfg: CoreConfig): string {
  const qq = getQqConfig(cfg);
  const explicit = normalizeAccountId(qq.defaultAccount);
  const ids = listQqAccountIds(cfg);
  return ids.includes(explicit) ? explicit : ids[0] ?? DEFAULT_ACCOUNT_ID;
}

export function resolveQqAccount(params: {
  cfg: CoreConfig;
  accountId?: string | null;
}): ResolvedQqAccount {
  const providerConfigPresent = params.cfg.channels?.qq !== undefined;
  const qq = getQqConfig(params.cfg);
  const resolvedAccountId = normalizeAccountId(params.accountId ?? resolveDefaultQqAccountId(params.cfg));
  const scoped = qq.accounts?.[resolvedAccountId] ?? {};
  const merged: QqConfig = {
    ...qq,
    ...scoped,
  };

  return {
    accountId: resolvedAccountId,
    enabled: providerConfigPresent && merged.enabled !== false,
    name: merged.name,
    selfId: merged.selfId,
    autoLaunch: merged.autoLaunch === true,
    preventIdleSleep:
      typeof merged.preventIdleSleep === "boolean"
        ? merged.preventIdleSleep
        : process.platform === "darwin" && merged.enabled !== false,
    executablePath: merged.executablePath?.trim() || DEFAULT_QQ_EXECUTABLE,
    launchArgs:
      Array.isArray(merged.launchArgs) && merged.launchArgs.length > 0
        ? merged.launchArgs.map((value) => String(value))
        : DEFAULT_QQ_ARGS,
    listenHost: merged.listenHost?.trim() || DEFAULT_LISTEN_HOST,
    listenPort:
      typeof merged.listenPort === "number" && Number.isFinite(merged.listenPort)
        ? merged.listenPort
        : DEFAULT_LISTEN_PORT,
    websocketPath: merged.websocketPath?.trim() || DEFAULT_WS_PATH,
    config: {
      name: merged.name,
      enabled: merged.enabled,
      selfId: merged.selfId,
      autoLaunch: merged.autoLaunch,
      preventIdleSleep: merged.preventIdleSleep,
      executablePath: merged.executablePath,
      launchArgs: merged.launchArgs,
      allowFrom: merged.allowFrom,
      groupAllowFrom: merged.groupAllowFrom,
      groups: merged.groups,
      mediaMaxMb: merged.mediaMaxMb,
      textChunkLimit: merged.textChunkLimit,
      responsePrefix: merged.responsePrefix,
      naturalChat: merged.naturalChat,
      studyMode: merged.studyMode,
    },
  };
}
