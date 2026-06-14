#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { WebSocketServer } from "ws";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const companionDir = path.join(workspaceRoot, "companion");
const adapterConfigPath = path.join(companionDir, "open-llm-vtuber-adapter.json");
const bridgeStatePath = path.join(workspaceRoot, "memory", "bridge-state.json");
const sessionsStorePath = path.join(
  os.homedir(),
  ".openclaw",
  "agents",
  "main",
  "sessions",
  "sessions.json",
);
const bridgeScriptPath = path.join(workspaceRoot, "scripts", "companion-bridge.mjs");
const identityPath = path.join(workspaceRoot, "IDENTITY.md");
const FIXED_HISTORY_UID = "openclaw-main";
const MAIN_SESSION_KEY = "agent:main:main";

const MIME_TYPES = {
  ".json": "application/json; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".moc3": "application/octet-stream",
  ".model3": "application/json; charset=utf-8",
  ".exp3.json": "application/json; charset=utf-8",
  ".motion3.json": "application/json; charset=utf-8",
  ".wav": "audio/wav",
  ".mp3": "audio/mpeg",
  ".txt": "text/plain; charset=utf-8",
};

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

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.${Math.random()
    .toString(36)
    .slice(2, 8)}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, filePath);
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return structuredClone(fallback);
  }
}

function defaultAdapterConfig() {
  return {
    host: "127.0.0.1",
    port: 12393,
    wsPath: "/client-ws",
    confName: "OpenClaw Companion",
    confUid: "openclaw-companion",
    avatarFilename: "",
    speakerName: "智乃",
    modelInfo: {
      name: "OpenClaw Companion",
      description: "Bridge-driven local shell for OpenClaw",
      url: "",
      kScale: 0.45,
      initialXshift: 0,
      initialYshift: 0,
      idleMotionGroupName: "Idle",
      defaultEmotion: "neutral",
      emotionMap: {
        calm: "neutral",
        curious: "surprised",
        focused: "serious",
        pleased: "happy",
        concerned: "sad",
        tired: "neutral",
      },
      pointerInteractive: true,
      tapMotions: {
        default: {
          "": 1,
        },
      },
      scrollToResize: true,
      initialScale: 0.9,
    },
    static: {
      live2dDir: "",
      avatarsDir: "",
      backgroundsDir: "",
    },
    motionMap: {},
    agent: {
      timeoutSeconds: 600,
      thinking: "",
    },
  };
}

function mergeAdapterConfig(base, current) {
  return {
    ...base,
    ...current,
    modelInfo: {
      ...base.modelInfo,
      ...(current.modelInfo ?? {}),
      emotionMap: {
        ...base.modelInfo.emotionMap,
        ...(current.modelInfo?.emotionMap ?? {}),
      },
    },
    static: {
      ...base.static,
      ...(current.static ?? {}),
    },
    motionMap: {
      ...(base.motionMap ?? {}),
      ...(current.motionMap ?? {}),
    },
    agent: {
      ...base.agent,
      ...(current.agent ?? {}),
    },
  };
}

function ensureAdapterConfig() {
  const fallback = defaultAdapterConfig();
  if (!fs.existsSync(adapterConfigPath)) {
    writeJson(adapterConfigPath, fallback);
    return structuredClone(fallback);
  }
  const current = readJson(adapterConfigPath, fallback);
  const merged = mergeAdapterConfig(fallback, current);
  if (JSON.stringify(current) !== JSON.stringify(merged)) {
    writeJson(adapterConfigPath, merged);
  }
  return merged;
}

function parseIdentityValue(label) {
  if (!fs.existsSync(identityPath)) {
    return null;
  }
  const source = fs.readFileSync(identityPath, "utf8");
  const pattern = new RegExp(`- \\*\\*${label}:\\*\\*\\s*(.+)`);
  const match = source.match(pattern);
  return match?.[1]?.trim() || null;
}

function loadIdentity() {
  return {
    name: parseIdentityValue("Name") || "智乃",
    creature: parseIdentityValue("Creature"),
    vibe: parseIdentityValue("Vibe"),
    avatar: parseIdentityValue("Avatar"),
  };
}

function resolveMainSessionId() {
  const store = readJson(sessionsStorePath, {});
  return store[MAIN_SESSION_KEY]?.sessionId ?? null;
}

function resolveOpenClawBin() {
  const explicit = process.env.OPENCLAW_BIN?.trim();
  if (explicit) {
    return explicit;
  }
  const homeBin = path.join(os.homedir(), ".local", "bin", "openclaw");
  if (fs.existsSync(homeBin)) {
    return homeBin;
  }
  return "openclaw";
}

function readBridgeState() {
  return readJson(bridgeStatePath, {
    schemaVersion: 1,
    updatedAt: nowIso(),
    mode: "observe",
    expression: "calm",
    motionPreset: "idle-soft",
    statusLine: "Quietly observing.",
    bubbleText: "",
    focusTarget: null,
    speaking: {
      active: false,
      text: "",
      source: null,
      startedAt: null,
    },
    lastEvent: null,
    streamVersion: 0,
  });
}

function createHistoryStore() {
  return {
    histories: [
      {
        uid: FIXED_HISTORY_UID,
        latest_message: null,
        timestamp: null,
      },
    ],
    messagesByUid: new Map([[FIXED_HISTORY_UID, []]]),
  };
}

function appendHistoryMessage(store, message) {
  const current = store.messagesByUid.get(FIXED_HISTORY_UID) ?? [];
  const next = [...current, message];
  store.messagesByUid.set(FIXED_HISTORY_UID, next);
  store.histories = [
    {
      uid: FIXED_HISTORY_UID,
      latest_message: {
        role: message.role,
        timestamp: message.timestamp,
        content: message.content,
      },
      timestamp: message.timestamp,
    },
  ];
}

function safeResolveWithin(rootDir, requestPath) {
  if (!rootDir) {
    return null;
  }
  const absoluteRoot = path.resolve(rootDir);
  const candidate = path.resolve(absoluteRoot, `.${requestPath}`);
  if (!candidate.startsWith(absoluteRoot)) {
    return null;
  }
  return candidate;
}

function sendJson(res, statusCode, body) {
  res.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
    "cache-control": "no-store",
  });
  res.end(`${JSON.stringify(body, null, 2)}\n`);
}

function serveStaticFile(res, filePath) {
  if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    sendJson(res, 404, { ok: false, error: "not found" });
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    "content-type": MIME_TYPES[ext] ?? "application/octet-stream",
    "cache-control": "no-store",
    "access-control-allow-origin": "*",
  });
  res.end(fs.readFileSync(filePath));
}

function buildSetModelMessage(config, clientUid) {
  return {
    type: "set-model-and-conf",
    model_info: config.modelInfo,
    conf_name: config.confName,
    conf_uid: config.confUid,
    client_uid: clientUid,
  };
}

function buildDisplayText(text, config, identity) {
  return {
    text,
    name: config.speakerName || identity.name || config.confName,
    avatar: config.avatarFilename || "",
  };
}

function mapExpression(config, bridgeState) {
  const expression = String(bridgeState.expression ?? "").trim();
  if (!expression) {
    return [];
  }
  const mapped = config.modelInfo?.emotionMap?.[expression];
  return [mapped ?? expression];
}

function mapMotionPreset(config, bridgeState) {
  const preset = String(bridgeState.motionPreset ?? "").trim();
  if (!preset) {
    return [];
  }
  const motions = config.motionMap?.[preset];
  return Array.isArray(motions) ? motions : [];
}

function sendWs(ws, payload) {
  if (ws.readyState === ws.OPEN) {
    ws.send(JSON.stringify(payload));
  }
}

function broadcast(clients, payload) {
  for (const client of clients) {
    sendWs(client.ws, payload);
  }
}

function usage() {
  process.stderr.write(
    [
      "Usage:",
      "  node scripts/open-llm-vtuber-adapter.mjs ensure",
      "  node scripts/open-llm-vtuber-adapter.mjs serve",
    ].join("\n") + "\n",
  );
  process.exit(1);
}

async function publishBridgeInterrupt() {
  return await new Promise((resolve) => {
    const child = spawn(process.execPath, [bridgeScriptPath, "event", "--type", "interrupt", "--note", "frontend interrupt"], {
      cwd: workspaceRoot,
      stdio: "ignore",
    });
    child.on("close", () => resolve());
    child.on("error", () => resolve());
  });
}

async function publishTextToBridge(text, status = "Speaking from adapter result.") {
  const trimmed = String(text ?? "").trim();
  if (!trimmed) {
    return;
  }
  return await new Promise((resolve) => {
    const child = spawn(
      process.execPath,
      [
        bridgeScriptPath,
        "publish",
        "--text",
        trimmed,
        "--source",
        "open-llm-vtuber-adapter",
        "--status",
        status,
      ],
      {
        cwd: workspaceRoot,
        stdio: "ignore",
      },
    );
    child.on("close", () => resolve());
    child.on("error", () => resolve());
  });
}

function normalizeAgentStdoutToBridgeText(stdout) {
  const lines = String(stdout ?? "")
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0)
    .filter((line) => !line.startsWith("MEDIA:"));
  return lines.join("\n").trim();
}

async function runOpenClawMainTurn(params) {
  const openclawBin = resolveOpenClawBin();
  const sessionId = resolveMainSessionId();
  if (!sessionId) {
    throw new Error("Main session id not found. Start or restore the main session first.");
  }

  const args = [
    "agent",
    "--session-id",
    sessionId,
    "--message",
    params.message,
    "--timeout",
    String(params.timeoutSeconds),
  ];
  if (params.thinking) {
    args.push("--thinking", params.thinking);
  }

  return await new Promise((resolve, reject) => {
    const child = spawn(openclawBin, args, {
      cwd: workspaceRoot,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code, signal) => {
      if (code === 0) {
        resolve({ stdout, stderr, code, signal, child });
        return;
      }
      reject(
        new Error(
          `openclaw agent failed (code=${code ?? "null"}, signal=${signal ?? "null"}): ${stderr || stdout}`.trim(),
        ),
      );
    });
    params.onChild(child);
  });
}

async function serveAdapter() {
  const config = ensureAdapterConfig();
  const identity = loadIdentity();
  const historyStore = createHistoryStore();
  const clients = new Map();
  let bridgeState = readBridgeState();
  let lastBridgeVersion = Number(bridgeState.streamVersion ?? 0);
  let currentAgentChild = null;
  let currentAgentStartedAt = null;
  let suppressNextBridgeStart = false;

  const httpServer = http.createServer((req, res) => {
    const url = new URL(req.url ?? "/", `http://${config.host}:${config.port}`);

    if (req.method === "GET" && url.pathname === "/health") {
      sendJson(res, 200, {
        ok: true,
        port: config.port,
        wsUrl: `ws://${config.host}:${config.port}${config.wsPath}`,
        modelUrl: config.modelInfo.url,
      });
      return;
    }

    if (req.method === "GET" && url.pathname.startsWith("/avatars/")) {
      const relativePath = url.pathname.slice("/avatars".length);
      const filePath = safeResolveWithin(config.static.avatarsDir, relativePath);
      serveStaticFile(res, filePath);
      return;
    }

    if (req.method === "GET" && url.pathname.startsWith("/backgrounds/")) {
      const relativePath = url.pathname.slice("/backgrounds".length);
      const filePath = safeResolveWithin(config.static.backgroundsDir, relativePath);
      serveStaticFile(res, filePath);
      return;
    }

    if (req.method === "GET" && url.pathname.startsWith("/live2d/")) {
      const relativePath = url.pathname.slice("/live2d".length);
      const filePath = safeResolveWithin(config.static.live2dDir, relativePath);
      serveStaticFile(res, filePath);
      return;
    }

    sendJson(res, 404, { ok: false, error: "not found" });
  });

  const wss = new WebSocketServer({ noServer: true });

  function sendInitialState(ws, clientUid) {
    sendWs(ws, { type: "full-text", text: "Connection established" });
    sendWs(ws, buildSetModelMessage(config, clientUid));
    sendWs(ws, {
      type: "config-files",
      configs: [{ filename: `${config.confUid}.json`, name: config.confName }],
    });
    sendWs(ws, {
      type: "history-list",
      histories: historyStore.histories,
    });
  }

function emitBridgeSpeech(nextBridge) {
    const text = String(nextBridge.bubbleText ?? "").trim();
    if (!text) {
      return;
    }
    const displayText = buildDisplayText(text, config, identity);
    appendHistoryMessage(historyStore, {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      content: text,
      role: "ai",
      timestamp: nowIso(),
      name: displayText.name,
      avatar: displayText.avatar || undefined,
      type: "text",
    });
    broadcast(clients.values(), {
      type: "full-text",
      text,
    });
    broadcast(clients.values(), {
      type: "audio",
      audio: "",
      display_text: displayText,
      actions: {
        expressions: mapExpression(config, nextBridge),
        motions: mapMotionPreset(config, nextBridge),
      },
      forwarded: true,
    });
    broadcast(clients.values(), {
      type: "history-data",
      messages: historyStore.messagesByUid.get(FIXED_HISTORY_UID) ?? [],
    });
  }

  function handleBridgeStateChange(nextBridge) {
    const previous = bridgeState;
    bridgeState = nextBridge;

    const speakingWasActive = Boolean(previous?.speaking?.active);
    const speakingIsActive = Boolean(nextBridge?.speaking?.active);
    const bubbleChanged = String(previous?.bubbleText ?? "") !== String(nextBridge?.bubbleText ?? "");
    const eventChanged =
      String(previous?.lastEvent?.at ?? "") !== String(nextBridge?.lastEvent?.at ?? "");
    const motionChanged =
      String(previous?.motionPreset ?? "") !== String(nextBridge?.motionPreset ?? "") ||
      String(previous?.expression ?? "") !== String(nextBridge?.expression ?? "");
    const actionTokenChanged =
      String(previous?.actionToken ?? "") !== String(nextBridge?.actionToken ?? "");

    if (!speakingWasActive && speakingIsActive) {
      if (suppressNextBridgeStart) {
        suppressNextBridgeStart = false;
      } else {
        broadcast(clients.values(), {
          type: "control",
          text: "conversation-chain-start",
        });
      }
    }

    if (speakingIsActive && (bubbleChanged || actionTokenChanged)) {
      emitBridgeSpeech(nextBridge);
    }

    if (!speakingIsActive && (motionChanged || actionTokenChanged)) {
      broadcast(clients.values(), {
        type: "audio",
        audio: "",
        actions: {
          expressions: mapExpression(config, nextBridge),
          motions: mapMotionPreset(config, nextBridge),
        },
        forwarded: true,
      });
    }

    if (speakingWasActive && !speakingIsActive) {
      broadcast(clients.values(), {
        type: "conversation-chain-end",
      });
    }

    if (eventChanged && nextBridge?.lastEvent?.type === "interrupt") {
      broadcast(clients.values(), {
        type: "interrupt-signal",
      });
    }
  }

  async function handleTextInput(ws, data) {
    const text = String(data.text ?? "").trim();
    if (!text) {
      return;
    }
    if (currentAgentChild) {
      sendWs(ws, {
        type: "error",
        message: "OpenClaw is already handling another request.",
      });
      return;
    }

    appendHistoryMessage(historyStore, {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      content: text,
      role: "human",
      timestamp: nowIso(),
      type: "text",
    });

    broadcast(clients.values(), {
      type: "control",
      text: "conversation-chain-start",
    });

    try {
      const result = await runOpenClawMainTurn({
        message: text,
        timeoutSeconds: config.agent.timeoutSeconds,
        thinking: String(config.agent.thinking ?? "").trim(),
        onChild: (child) => {
          currentAgentChild = child;
          currentAgentStartedAt = Date.now();
        },
      });
      const replyText = normalizeAgentStdoutToBridgeText(result.stdout);
      if (replyText && replyText !== "HEARTBEAT_OK") {
        suppressNextBridgeStart = true;
        await publishTextToBridge(replyText, "Speaking from adapter text input.");
      }
      broadcast(clients.values(), {
        type: "conversation-chain-end",
      });
    } catch (error) {
      sendWs(ws, {
        type: "error",
        message: error instanceof Error ? error.message : String(error),
      });
      broadcast(clients.values(), {
        type: "conversation-chain-end",
      });
    } finally {
      currentAgentChild = null;
      currentAgentStartedAt = null;
    }
  }

  async function handleInterrupt() {
    if (currentAgentChild) {
      try {
        currentAgentChild.kill("SIGTERM");
      } catch {
        // ignore best effort stop
      }
      currentAgentChild = null;
      currentAgentStartedAt = null;
    }
    await publishBridgeInterrupt();
    broadcast(clients.values(), {
      type: "conversation-chain-end",
    });
  }

  wss.on("connection", (ws) => {
    const clientUid = randomUUID();
    clients.set(clientUid, { ws, clientUid });
    sendInitialState(ws, clientUid);

    ws.on("message", async (raw) => {
      let data;
      try {
        data = JSON.parse(raw.toString());
      } catch {
        sendWs(ws, { type: "error", message: "Invalid JSON payload" });
        return;
      }

      switch (data.type) {
        case "fetch-backgrounds":
          sendWs(ws, { type: "background-files", files: [] });
          break;
        case "fetch-configs":
          sendWs(ws, {
            type: "config-files",
            configs: [{ filename: `${config.confUid}.json`, name: config.confName }],
          });
          break;
        case "fetch-history-list":
          sendWs(ws, {
            type: "history-list",
            histories: historyStore.histories,
          });
          break;
        case "create-new-history":
          sendWs(ws, { type: "new-history-created", history_uid: FIXED_HISTORY_UID });
          sendWs(ws, {
            type: "history-data",
            messages: historyStore.messagesByUid.get(FIXED_HISTORY_UID) ?? [],
          });
          break;
        case "fetch-and-set-history":
          sendWs(ws, {
            type: "history-data",
            messages: historyStore.messagesByUid.get(FIXED_HISTORY_UID) ?? [],
          });
          break;
        case "delete-history":
          sendWs(ws, {
            type: "history-deleted",
            success: false,
            message: "History deletion is not supported by the OpenClaw adapter.",
          });
          break;
        case "request-init-config":
          sendWs(ws, buildSetModelMessage(config, clientUid));
          break;
        case "switch-config":
          sendWs(ws, { type: "config-switched" });
          sendWs(ws, buildSetModelMessage(config, clientUid));
          break;
        case "text-input":
          await handleTextInput(ws, data);
          break;
        case "interrupt-signal":
          await handleInterrupt();
          break;
        case "heartbeat":
          sendWs(ws, { type: "heartbeat-ack" });
          break;
        case "audio-play-start":
        case "request-group-info":
        case "add-client-to-group":
        case "remove-client-from-group":
        case "mic-audio-data":
        case "mic-audio-end":
        case "raw-audio-data":
        case "ai-speak-signal":
          break;
        default:
          sendWs(ws, { type: "error", message: `Unsupported message type: ${data.type}` });
          break;
      }
    });

    ws.on("close", () => {
      clients.delete(clientUid);
    });
  });

  httpServer.on("upgrade", (req, socket, head) => {
    const requestUrl = new URL(req.url ?? "/", `http://${config.host}:${config.port}`);
    if (requestUrl.pathname !== config.wsPath) {
      socket.destroy();
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws, req);
    });
  });

  const bridgePoll = setInterval(() => {
    const nextBridge = readBridgeState();
    const nextVersion = Number(nextBridge.streamVersion ?? 0);
    if (nextVersion !== lastBridgeVersion) {
      lastBridgeVersion = nextVersion;
      handleBridgeStateChange(nextBridge);
    }
  }, 500);
  bridgePoll.unref?.();

  await new Promise((resolve) => httpServer.listen(config.port, config.host, resolve));
  printJson({
    ok: true,
    status: "listening",
    host: config.host,
    port: config.port,
    wsUrl: `ws://${config.host}:${config.port}${config.wsPath}`,
    baseUrl: `http://${config.host}:${config.port}`,
    configPath: adapterConfigPath,
    currentMainSessionId: resolveMainSessionId(),
    currentBridgeVersion: lastBridgeVersion,
    agentBusy: currentAgentStartedAt !== null,
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0];
  if (!command) {
    usage();
  }

  if (command === "ensure") {
    printJson({
      ok: true,
      configPath: adapterConfigPath,
      config: ensureAdapterConfig(),
      identity: loadIdentity(),
      mainSessionId: resolveMainSessionId(),
    });
    return;
  }

  if (command === "serve") {
    await serveAdapter();
    return;
  }

  usage();
}

await main();
