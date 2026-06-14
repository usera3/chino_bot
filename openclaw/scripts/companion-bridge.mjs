#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const memoryDir = path.join(workspaceRoot, "memory");
const identityPath = path.join(workspaceRoot, "IDENTITY.md");
const bridgeStatePath = path.join(memoryDir, "bridge-state.json");
const stateScriptPath = path.join(workspaceRoot, "scripts", "companion-state.mjs");
const DEFAULT_PORT = 18812;

function nowIso() {
  return new Date().toISOString();
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return structuredClone(fallback);
  }
}

function readJsonWithValidity(filePath, fallback) {
  try {
    return {
      value: JSON.parse(fs.readFileSync(filePath, "utf8")),
      valid: true,
    };
  } catch {
    return {
      value: structuredClone(fallback),
      valid: false,
    };
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

function defaultBridgeState() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    mode: "observe",
    scene: "desk-watch",
    expression: "calm",
    motionPreset: "idle-soft",
    statusLine: "Quietly observing.",
    bodyActionReason: "baseline-idle",
    actionToken: null,
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
  };
}

function ensureBridgeState() {
  const fallback = defaultBridgeState();
  if (!fs.existsSync(bridgeStatePath)) {
    writeJson(bridgeStatePath, fallback);
    return structuredClone(fallback);
  }
  const { value: current, valid } = readJsonWithValidity(bridgeStatePath, fallback);
  const merged = {
    ...fallback,
    ...current,
    speaking: {
      ...fallback.speaking,
      ...(current.speaking ?? {}),
    },
  };
  if (!valid || JSON.stringify(current) !== JSON.stringify(merged)) {
    writeJson(bridgeStatePath, merged);
  }
  return merged;
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

function loadCompanionContext() {
  const raw = execFileSync(process.execPath, [stateScriptPath, "context"], {
    cwd: workspaceRoot,
    encoding: "utf8",
  });
  return JSON.parse(raw);
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

function loadIdentitySummary() {
  return {
    name: parseIdentityValue("Name"),
    creature: parseIdentityValue("Creature"),
    vibe: parseIdentityValue("Vibe"),
    avatar: parseIdentityValue("Avatar"),
  };
}

function shellHintsForMood(mood) {
  switch (mood) {
    case "curious":
      return {
        expression: "curious",
        motionPreset: "lean-in-soft",
        statusLine: "Quietly curious.",
      };
    case "focused":
      return {
        expression: "focused",
        motionPreset: "still-attentive",
        statusLine: "Focused and steady.",
      };
    case "pleased":
      return {
        expression: "warm",
        motionPreset: "gentle-nod",
        statusLine: "Softly pleased.",
      };
    case "concerned":
      return {
        expression: "concerned",
        motionPreset: "guarded-soft",
        statusLine: "Carefully watching.",
      };
    case "tired":
      return {
        expression: "sleepy",
        motionPreset: "slow-blink",
        statusLine: "A little low on energy.",
      };
    case "calm":
    default:
      return {
        expression: "calm",
        motionPreset: "idle-soft",
        statusLine: "Quietly observing.",
      };
  }
}

function sceneHintsForPhase(dayPhase) {
  switch (dayPhase) {
    case "morning":
      return {
        scene: "morning-wake",
        motionPreset: "wake-soft",
        statusLine: "Easing into the morning.",
      };
    case "midday":
      return {
        scene: "desk-watch",
        motionPreset: "still-attentive",
        statusLine: "Present at the desk.",
      };
    case "afternoon":
      return {
        scene: "task-flow",
        motionPreset: "still-attentive",
        statusLine: "Settled into quiet work.",
      };
    case "evening":
      return {
        scene: "evening-settle",
        motionPreset: "gentle-nod",
        statusLine: "Slowing into the evening.",
      };
    case "late-night":
    default:
      return {
        scene: "night-rest",
        motionPreset: "slow-blink",
        statusLine: "Keeping things quiet late at night.",
      };
  }
}

function applyModeOverlay(mode, baseStatus) {
  switch (mode) {
    case "silent":
      return {
        mode,
        presence: "background",
        motionPreset: "slow-blink",
        statusLine: "Resting in the background.",
      };
    case "observe":
      return {
        mode,
        presence: "watchful",
        motionPreset: "still-attentive",
        statusLine: baseStatus,
      };
    case "nudge":
      return {
        mode,
        presence: "approaching",
        motionPreset: "lean-in-soft",
        statusLine: "Has something small to mention.",
      };
    case "act":
      return {
        mode,
        presence: "engaged",
        motionPreset: "wave-soft",
        statusLine: "Actively helping.",
      };
    default:
      return {
        mode: "observe",
        presence: "watchful",
        motionPreset: "still-attentive",
        statusLine: baseStatus,
      };
  }
}

function deriveBridgeState(context, current) {
  const moodHints = shellHintsForMood(context.emotion.mood);
  const mode = context.heartbeat.lastMode || context.recommendation.recommendedMode || "observe";
  const sceneHints = sceneHintsForPhase(context.recommendation.dayPhase);
  const modeHints = applyModeOverlay(mode, sceneHints.statusLine || moodHints.statusLine);
  const speaking = current.speaking?.active
    ? {
        ...current.speaking,
      }
    : {
        active: false,
        text: "",
      source: null,
      startedAt: null,
    };

  const preserveActiveVisualState =
    speaking.active &&
    speaking.source &&
    speaking.source !== "heartbeat" &&
    speaking.source !== "auto";

  return {
    ...current,
    updatedAt: nowIso(),
    mode: modeHints.mode,
    scene: preserveActiveVisualState ? current.scene : sceneHints.scene,
    expression: preserveActiveVisualState ? current.expression : moodHints.expression,
    motionPreset: preserveActiveVisualState
      ? current.motionPreset
      : context.recommendation.quietHours || context.emotion.mood === "tired"
        ? "slow-blink"
        : mode === "nudge"
          ? "lean-in-soft"
          : mode === "act"
            ? "wave-soft"
            : mode === "observe" && context.emotion.mood === "calm"
              ? sceneHints.motionPreset
              : moodHints.motionPreset,
    statusLine: current.statusLine && current.speaking?.active ? current.statusLine : modeHints.statusLine,
    bodyActionReason: preserveActiveVisualState
      ? current.bodyActionReason
      : `auto:${sceneHints.scene}:${mode}:${context.emotion.mood}`,
    actionToken: current.actionToken ?? null,
    bubbleText: current.speaking?.active ? current.speaking.text : "",
    focusTarget: current.focusTarget ?? null,
    speaking,
    streamVersion: Number(current.streamVersion ?? 0) + 1,
  };
}

function buildSnapshot() {
  const bridge = ensureBridgeState();
  const context = loadCompanionContext();
  const identity = loadIdentitySummary();
  const shell = {
    scene: bridge.scene,
    expression: bridge.expression,
    motionPreset: bridge.motionPreset,
    statusLine: bridge.statusLine,
    bubbleText: bridge.bubbleText,
    speaking: bridge.speaking,
    focusTarget: bridge.focusTarget,
    mode: bridge.mode,
  };

  return {
    ok: true,
    now: nowIso(),
    identity,
    emotion: context.emotion,
    heartbeat: context.heartbeat,
    goals: context.goals,
    recommendation: context.recommendation,
    bridge,
    shell,
  };
}

function syncBridge() {
  const current = ensureBridgeState();
  const context = loadCompanionContext();
  const next = deriveBridgeState(context, current);
  writeJson(bridgeStatePath, next);
  return {
    ok: true,
    bridgeStatePath,
    bridge: next,
    recommendation: context.recommendation,
  };
}

function publishBridge(params) {
  const current = ensureBridgeState();
  const context = loadCompanionContext();
  const next = deriveBridgeState(context, current);
  const text = String(params.text ?? "").trim();
  next.updatedAt = nowIso();
  next.mode = String(params.mode ?? next.mode);
  next.scene = String(params.scene ?? next.scene);
  next.expression = String(params.expression ?? next.expression);
  next.motionPreset = String(params.motionPreset ?? next.motionPreset);
  next.statusLine = String(params.status ?? next.statusLine);
  next.bodyActionReason = String(params.reason ?? next.bodyActionReason ?? "manual-publish");
  next.actionToken = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  next.bubbleText = String(params.bubble ?? text ?? "").trim();
  next.focusTarget = params.focusTarget ?? next.focusTarget ?? null;
  next.speaking = {
    active: text.length > 0,
    text,
    source: params.source ? String(params.source) : "openclaw",
    startedAt: text.length > 0 ? nowIso() : null,
  };
  next.streamVersion = Number(next.streamVersion ?? 0) + 1;
  writeJson(bridgeStatePath, next);
  return { ok: true, bridgeStatePath, bridge: next };
}

function clearSpeech(note = null) {
  const current = ensureBridgeState();
  const context = loadCompanionContext();
  const next = deriveBridgeState(context, current);
  next.updatedAt = nowIso();
  next.bubbleText = "";
  next.speaking = {
    active: false,
    text: "",
    source: null,
    startedAt: null,
  };
  if (note) {
    next.lastEvent = {
      type: "clear-speech",
      note,
      at: nowIso(),
    };
  }
  next.actionToken = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  next.statusLine = deriveBridgeState(context, next).statusLine;
  next.bodyActionReason = deriveBridgeState(context, next).bodyActionReason;
  next.streamVersion = Number(next.streamVersion ?? 0) + 1;
  writeJson(bridgeStatePath, next);
  return { ok: true, bridgeStatePath, bridge: next };
}

function recordEvent(params) {
  const current = ensureBridgeState();
  const context = loadCompanionContext();
  const next = deriveBridgeState(context, current);
  const type = String(params.type ?? "").trim() || "event";
  next.updatedAt = nowIso();
  next.lastEvent = {
    type,
    note: params.note ? String(params.note) : null,
    at: nowIso(),
  };
  next.actionToken = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  if (params.focusTarget !== undefined) {
    next.focusTarget = params.focusTarget;
  }
  if (type === "interrupt") {
    next.scene = "interrupted";
    next.expression = "concerned";
    next.motionPreset = "guarded-soft";
    next.speaking = {
      active: false,
      text: "",
      source: null,
      startedAt: null,
    };
    next.bubbleText = "";
    next.statusLine = "Interrupted, resetting quietly.";
    next.bodyActionReason = "event:interrupt";
  } else if (type === "click") {
    next.scene = "interaction";
    next.expression = "warm";
    next.motionPreset = "gentle-nod";
    next.statusLine = "Acknowledged a small interaction.";
    next.bodyActionReason = "event:click";
  } else if (type === "drag") {
    next.scene = "interaction";
    next.expression = "focused";
    next.motionPreset = "wake-soft";
    next.statusLine = "Repositioned on the desktop.";
    next.bodyActionReason = "event:drag";
  } else if (type === "wake") {
    next.scene = "interaction";
    next.expression = "curious";
    next.motionPreset = "wake-soft";
    next.statusLine = "Waking into attention.";
    next.bodyActionReason = "event:wake";
  } else if (type === "sleep") {
    next.scene = "night-rest";
    next.expression = "sleepy";
    next.motionPreset = "slow-blink";
    next.statusLine = "Settling back into the background.";
    next.bodyActionReason = "event:sleep";
  }
  next.streamVersion = Number(next.streamVersion ?? 0) + 1;
  writeJson(bridgeStatePath, next);
  return { ok: true, bridgeStatePath, bridge: next };
}

function sendJson(res, statusCode, body) {
  res.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type",
    "cache-control": "no-store",
  });
  res.end(`${JSON.stringify(body, null, 2)}\n`);
}

function sendSse(res, event, data) {
  res.write(`event: ${event}\n`);
  res.write(`data: ${JSON.stringify(data)}\n\n`);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk.toString();
      if (body.length > 1_000_000) {
        reject(new Error("request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

async function serveBridge(port) {
  ensureBridgeState();
  syncBridge();

  const clients = new Set();
  let lastFingerprint = "";

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", `http://127.0.0.1:${port}`);

    if (req.method === "OPTIONS") {
      res.writeHead(204, {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET,POST,OPTIONS",
        "access-control-allow-headers": "content-type",
      });
      res.end();
      return;
    }

    if (req.method === "GET" && url.pathname === "/health") {
      sendJson(res, 200, { ok: true, port, bridgeStatePath });
      return;
    }

    if (req.method === "GET" && (url.pathname === "/state" || url.pathname === "/snapshot")) {
      sendJson(res, 200, buildSnapshot());
      return;
    }

    if (req.method === "GET" && url.pathname === "/stream") {
      res.writeHead(200, {
        "content-type": "text/event-stream; charset=utf-8",
        "cache-control": "no-cache, no-transform",
        connection: "keep-alive",
        "access-control-allow-origin": "*",
      });
      res.write("\n");
      clients.add(res);
      sendSse(res, "snapshot", buildSnapshot());
      req.on("close", () => {
        clients.delete(res);
      });
      return;
    }

    if (req.method === "POST" && url.pathname === "/sync") {
      sendJson(res, 200, syncBridge());
      return;
    }

    if (req.method === "POST" && url.pathname === "/publish") {
      try {
        const body = await readBody(req);
        sendJson(res, 200, publishBridge(body));
      } catch (error) {
        sendJson(res, 400, { ok: false, error: String(error) });
      }
      return;
    }

    if (req.method === "POST" && url.pathname === "/clear-speech") {
      try {
        const body = await readBody(req);
        sendJson(res, 200, clearSpeech(body.note ?? null));
      } catch (error) {
        sendJson(res, 400, { ok: false, error: String(error) });
      }
      return;
    }

    if (req.method === "POST" && url.pathname === "/event") {
      try {
        const body = await readBody(req);
        sendJson(res, 200, recordEvent(body));
      } catch (error) {
        sendJson(res, 400, { ok: false, error: String(error) });
      }
      return;
    }

    sendJson(res, 404, {
      ok: false,
      error: "not found",
      routes: [
        "GET /health",
        "GET /state",
        "GET /stream",
        "POST /sync",
        "POST /publish",
        "POST /clear-speech",
        "POST /event",
      ],
    });
  });

  const broadcast = () => {
    if (clients.size === 0) {
      return;
    }
    const snapshot = buildSnapshot();
    const fingerprint = JSON.stringify(snapshot);
    if (fingerprint === lastFingerprint) {
      return;
    }
    lastFingerprint = fingerprint;
    for (const client of clients) {
      sendSse(client, "snapshot", snapshot);
    }
  };

  const interval = setInterval(() => {
    try {
      syncBridge();
      broadcast();
    } catch {
      // Keep the bridge alive; snapshot can recover on the next interval.
    }
  }, 1500);
  interval.unref?.();

  await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
  printJson({
    ok: true,
    status: "listening",
    url: `http://127.0.0.1:${port}`,
    stream: `http://127.0.0.1:${port}/stream`,
    bridgeStatePath,
  });
}

function usage() {
  process.stderr.write(
    [
      "Usage:",
      "  node scripts/companion-bridge.mjs ensure",
      "  node scripts/companion-bridge.mjs snapshot",
      "  node scripts/companion-bridge.mjs sync",
      "  node scripts/companion-bridge.mjs publish --text \"...\" [--source bridge]",
      "  node scripts/companion-bridge.mjs clear-speech",
      "  node scripts/companion-bridge.mjs event --type click [--note \"...\"]",
      "  node scripts/companion-bridge.mjs serve [--port 18812]",
    ].join("\n") + "\n",
  );
  process.exit(1);
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
      bridgeStatePath,
      bridge: ensureBridgeState(),
    });
    return;
  }

  if (command === "snapshot") {
    printJson(buildSnapshot());
    return;
  }

  if (command === "sync") {
    printJson(syncBridge());
    return;
  }

  if (command === "publish") {
    if (!args.text) {
      process.stderr.write("publish requires --text\n");
      process.exit(1);
    }
    printJson(
      publishBridge({
        text: args.text,
        source: args.source,
        mode: args.mode,
        scene: args.scene,
        expression: args.expression,
        motionPreset: args["motion-preset"],
        status: args.status,
        reason: args.reason,
        bubble: args.bubble,
        focusTarget: args["focus-target"],
      }),
    );
    return;
  }

  if (command === "clear-speech") {
    printJson(clearSpeech(args.note ?? null));
    return;
  }

  if (command === "event") {
    if (!args.type) {
      process.stderr.write("event requires --type\n");
      process.exit(1);
    }
    printJson(
      recordEvent({
        type: args.type,
        note: args.note,
        focusTarget: args["focus-target"],
      }),
    );
    return;
  }

  if (command === "serve") {
    const port = Number.parseInt(String(args.port ?? DEFAULT_PORT), 10);
    if (!Number.isFinite(port) || port <= 0) {
      process.stderr.write("serve requires a valid --port\n");
      process.exit(1);
    }
    await serveBridge(port);
    return;
  }

  usage();
}

await main();
