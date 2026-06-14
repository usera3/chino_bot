import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");

const QQ_DIST_TARGETS = [
  "dist/reply-Bm8VrLQh.js",
  "dist/auth-profiles-DRjqKE3G.js",
  "dist/auth-profiles-DDVivXkv.js",
  "dist/model-selection-CU2b7bN6.js",
  "dist/model-selection-46xMp11W.js",
  "dist/discord-CcCLMjHw.js",
];

const DELIVERY_MODE_OLD =
  'const deliveryMode = resolveRequiredPlugin(channel, cfg).outbound?.deliveryMode ?? "direct";';
const DELIVERY_MODE_NEW = [
  "const deliveryMode = shouldForceGatewaySendForCli({",
  "\t\tchannel,",
  "\t\tgateway: params.gateway",
  '\t}) ? "gateway" : resolveRequiredPlugin(channel, cfg).outbound?.deliveryMode ?? "direct";',
].join("\n");

const PLUGIN_HANDLED_OLD = 'const pluginHandled = await tryHandleWithPluginAction({';
const PLUGIN_HANDLED_NEW = [
  "const pluginHandled = shouldForceGatewaySendForCli({",
  "\t\tchannel: params.ctx.channel,",
  "\t\tgateway: params.ctx.gateway",
  "\t}) ? null : await tryHandleWithPluginAction({",
].join("\n");

const HELPER_ANCHOR = "async function executePollAction(params) {";
const HELPER_BLOCK = [
  "function shouldForceGatewaySendForCli(params) {",
  '\treturn params.channel === "qq" && isGatewayCliClient(params.gateway);',
  "}",
].join("\n");

const NAPCAT_OB11_CONFIG = path.join(
  process.env.HOME || "",
  "Library",
  "Containers",
  "com.tencent.qq",
  "Data",
  "Library",
  "Application Support",
  "QQ",
  "NapCat",
  "config",
  "onebot11_2509109290.json",
);
const OPENCLAW_WS_URL = "ws://127.0.0.1:8080/onebot/v11/ws";

async function pathExists(pathname) {
  try {
    await fs.access(pathname);
    return true;
  } catch {
    return false;
  }
}

async function ensureBackup(pathname) {
  const backupPath = `${pathname}.bak-local-patches`;
  if (await pathExists(backupPath)) {
    return backupPath;
  }
  await fs.copyFile(pathname, backupPath);
  return backupPath;
}

async function readText(pathname) {
  return await fs.readFile(pathname, "utf8");
}

async function writeText(pathname, text) {
  const tmpPath = `${pathname}.${process.pid}.${Date.now()}.tmp`;
  await fs.writeFile(tmpPath, text, "utf8");
  await fs.rename(tmpPath, pathname);
}

function inspectDistPatch(text) {
  return {
    hasDeliveryModePatch: text.includes(DELIVERY_MODE_NEW),
    hasPluginHandledPatch: text.includes(PLUGIN_HANDLED_NEW),
    hasHelperPatch: text.includes(HELPER_BLOCK),
  };
}

function applyDistPatchText(text) {
  let next = text;
  if (!next.includes(DELIVERY_MODE_NEW)) {
    next = next.replace(DELIVERY_MODE_OLD, DELIVERY_MODE_NEW);
  }
  if (!next.includes(PLUGIN_HANDLED_NEW)) {
    next = next.replace(PLUGIN_HANDLED_OLD, PLUGIN_HANDLED_NEW);
  }
  if (!next.includes(HELPER_BLOCK)) {
    next = next.replace(HELPER_ANCHOR, `${HELPER_BLOCK}\n${HELPER_ANCHOR}`);
  }
  return next;
}

async function inspectDistTargets() {
  const results = [];
  for (const relativePath of QQ_DIST_TARGETS) {
    const absolutePath = path.join(workspaceRoot, relativePath);
    const text = await readText(absolutePath);
    const patchState = inspectDistPatch(text);
    results.push({
      path: absolutePath,
      ok:
        patchState.hasDeliveryModePatch &&
        patchState.hasPluginHandledPatch &&
        patchState.hasHelperPatch,
      ...patchState,
    });
  }
  return results;
}

async function applyDistTargets() {
  const results = [];
  for (const relativePath of QQ_DIST_TARGETS) {
    const absolutePath = path.join(workspaceRoot, relativePath);
    const original = await readText(absolutePath);
    const before = inspectDistPatch(original);
    const patched = applyDistPatchText(original);
    const after = inspectDistPatch(patched);
    const changed = patched !== original;
    if (changed) {
      await ensureBackup(absolutePath);
      await writeText(absolutePath, patched);
    }
    results.push({
      path: absolutePath,
      changed,
      before,
      after,
      ok:
        after.hasDeliveryModePatch &&
        after.hasPluginHandledPatch &&
        after.hasHelperPatch,
    });
  }
  return results;
}

async function inspectNapcatConfig() {
  if (!(await pathExists(NAPCAT_OB11_CONFIG))) {
    return {
      path: NAPCAT_OB11_CONFIG,
      exists: false,
      ok: false,
    };
  }
  const parsed = JSON.parse(await readText(NAPCAT_OB11_CONFIG));
  const clients = Array.isArray(parsed?.network?.websocketClients) ? parsed.network.websocketClients : [];
  const targetClient = clients.find((entry) => String(entry?.url || "").includes("127.0.0.1:8080"));
  return {
    path: NAPCAT_OB11_CONFIG,
    exists: true,
    targetClient,
    ok: String(targetClient?.url || "") === OPENCLAW_WS_URL,
  };
}

async function applyNapcatConfig() {
  const inspection = await inspectNapcatConfig();
  if (!inspection.exists) {
    return {
      ...inspection,
      changed: false,
    };
  }
  const parsed = JSON.parse(await readText(NAPCAT_OB11_CONFIG));
  const clients = Array.isArray(parsed?.network?.websocketClients) ? parsed.network.websocketClients : [];
  const targetIndex = clients.findIndex((entry) => String(entry?.url || "").includes("127.0.0.1:8080"));
  if (targetIndex < 0) {
    return {
      ...inspection,
      changed: false,
      ok: false,
      error: "No websocket client entry found for 127.0.0.1:8080",
    };
  }
  const targetClient = { ...clients[targetIndex] };
  targetClient.url = OPENCLAW_WS_URL;
  if (targetClient.name === "nonebot2") {
    targetClient.name = "openclaw";
  }
  clients[targetIndex] = targetClient;
  parsed.network.websocketClients = clients;
  const nextText = `${JSON.stringify(parsed, null, 2)}\n`;
  const currentText = await readText(NAPCAT_OB11_CONFIG);
  const changed = currentText !== nextText;
  if (changed) {
    await ensureBackup(NAPCAT_OB11_CONFIG);
    await writeText(NAPCAT_OB11_CONFIG, nextText);
  }
  return {
    path: NAPCAT_OB11_CONFIG,
    exists: true,
    changed,
    ok: true,
    targetClient,
  };
}

export async function inspectLocalPatches() {
  const [dist, napcat] = await Promise.all([inspectDistTargets(), inspectNapcatConfig()]);
  return {
    generatedAt: new Date().toISOString(),
    ok: dist.every((entry) => entry.ok) && napcat.ok,
    dist,
    napcat,
  };
}

export async function applyLocalPatches() {
  const [dist, napcat] = await Promise.all([applyDistTargets(), applyNapcatConfig()]);
  return {
    generatedAt: new Date().toISOString(),
    ok: dist.every((entry) => entry.ok) && napcat.ok,
    dist,
    napcat,
  };
}

async function main() {
  const command = process.argv[2] || "status";
  const result =
    command === "apply"
      ? await applyLocalPatches()
      : command === "status"
        ? await inspectLocalPatches()
        : null;
  if (!result) {
    throw new Error(`Unknown command: ${command}`);
  }
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    process.stderr.write(`${String(error instanceof Error ? error.stack || error.message : error)}\n`);
    process.exitCode = 1;
  });
}
