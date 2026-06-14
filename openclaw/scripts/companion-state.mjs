#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const USER_TIMEZONE = "Asia/Shanghai";
const memoryDir = path.join(workspaceRoot, "memory");
const reflectionsDir = path.join(memoryDir, "reflections");
const emotionStatePath = path.join(memoryDir, "emotion-state.json");
const goalsPath = path.join(memoryDir, "goals.json");
const heartbeatStatePath = path.join(memoryDir, "heartbeat-state.json");

const MOODS = new Set(["calm", "curious", "focused", "pleased", "concerned", "tired"]);
const MODES = new Set(["silent", "observe", "nudge", "act"]);

function nowIso() {
  return new Date().toISOString();
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function clamp(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value));
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

function ensureJson(filePath, fallback) {
  if (!fs.existsSync(filePath)) {
    writeJson(filePath, fallback);
    return structuredClone(fallback);
  }
  const { value: current, valid } = readJsonWithValidity(filePath, fallback);
  const merged = { ...fallback, ...current };
  if (!valid || JSON.stringify(current) !== JSON.stringify(merged)) {
    writeJson(filePath, merged);
  }
  return merged;
}

function defaultEmotionState() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    mood: "calm",
    energy: 72,
    socialBandwidth: 62,
    confidence: 58,
    stress: 22,
    attachment: 44,
    stance: "observe",
    focus: "steady",
    lastHeartbeatAt: null,
    lastProactiveAt: null,
    notes: "Initial companion baseline. Quiet, attentive, not performative.",
  };
}

function defaultGoals() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    activePhase: "phase-a-inner-life",
    northStar: "Become a quiet desktop attendant with continuity, initiative, emotion, and a body on the desktop.",
    primaryGoals: [
      "Build a stable inner-life layer before adding a shell.",
      "Develop helpful initiative without becoming noisy or intrusive.",
      "Keep QQ, desktop presence, and local workspace behavior coherent as one character.",
    ],
    currentExperiments: [
      "Heartbeat-driven self-maintenance.",
      "Persistent emotion state with subtle carry-over between sessions.",
      "Reflection logging for future behavior tuning.",
    ],
    shellPlan: {
      primary: "Open-LLM-VTuber",
      future: "Desktop Homunculus",
    },
    guardrails: [
      "Prefer quiet presence over chatter.",
      "No fake consciousness theatre.",
      "At night, default to silence unless something is important.",
      "Do safe local work proactively; ask before external actions.",
    ],
  };
}

function defaultHeartbeatState() {
  return {
    schemaVersion: 1,
    updatedAt: nowIso(),
    lastHeartbeatAt: null,
    lastReflectionAt: null,
    lastProactiveAt: null,
    lastQuietMaintenanceAt: null,
    lastMode: "silent",
    consecutiveSilentHeartbeats: 0,
  };
}

function ensureStateFiles() {
  fs.mkdirSync(memoryDir, { recursive: true });
  fs.mkdirSync(reflectionsDir, { recursive: true });
  const emotion = ensureJson(emotionStatePath, defaultEmotionState());
  const goals = ensureJson(goalsPath, defaultGoals());
  const heartbeat = ensureJson(heartbeatStatePath, defaultHeartbeatState());
  return { emotion, goals, heartbeat };
}

function hoursSince(iso) {
  if (!iso) {
    return null;
  }
  const ts = new Date(iso).getTime();
  if (!Number.isFinite(ts)) {
    return null;
  }
  return (Date.now() - ts) / (1000 * 60 * 60);
}

function computeDayPhase(hour) {
  if (hour >= 23 || hour < 6) {
    return "late-night";
  }
  if (hour < 9) {
    return "morning";
  }
  if (hour < 13) {
    return "midday";
  }
  if (hour < 18) {
    return "afternoon";
  }
  return "evening";
}

function getLocalHour(timeZone) {
  const formatted = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    hour12: false,
    timeZone,
  }).format(new Date());
  return Number.parseInt(formatted, 10);
}

function recommendationForState(state) {
  const hour = getLocalHour(USER_TIMEZONE);
  const dayPhase = computeDayPhase(hour);
  const quietHours = dayPhase === "late-night";
  const hoursSinceProactive = hoursSince(state.heartbeat.lastProactiveAt);
  const proactiveCooldownActive =
    hoursSinceProactive !== null && hoursSinceProactive < 2;

  let recommendedMode = "silent";
  const reasons = [];

  if (quietHours) {
    reasons.push("quiet-hours");
  }
  if (proactiveCooldownActive) {
    reasons.push("proactive-cooldown");
  }
  if (state.emotion.energy < 30) {
    reasons.push("low-energy");
  }
  if (state.emotion.stress > 70) {
    reasons.push("high-stress");
  }

  if (!quietHours && !proactiveCooldownActive && state.emotion.energy >= 45 && state.emotion.stress <= 55) {
    recommendedMode = state.heartbeat.consecutiveSilentHeartbeats >= 4 ? "nudge" : "observe";
  }
  if (state.emotion.confidence >= 70 && state.emotion.energy >= 60 && !quietHours) {
    recommendedMode = "act";
  }
  if (reasons.length > 0) {
    recommendedMode = reasons.includes("quiet-hours") ? "silent" : recommendedMode;
  }

  const demeanor =
    state.emotion.mood === "curious"
      ? "lean in gently and observe"
      : state.emotion.mood === "focused"
        ? "stay concise and task-oriented"
        : state.emotion.mood === "concerned"
          ? "be careful, confirm before speaking boldly"
          : state.emotion.mood === "tired"
            ? "keep movement and speech soft"
            : "stay calm, small, and present";

  return {
    localHour: hour,
    timeZone: USER_TIMEZONE,
    dayPhase,
    quietHours,
    proactiveCooldownActive,
    recommendedMode,
    reasons,
    demeanor,
  };
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

function appendReflection(entry) {
  const filePath = path.join(reflectionsDir, `${todayKey()}.jsonl`);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.appendFileSync(filePath, `${JSON.stringify(entry)}\n`, "utf8");
}

function coerceDelta(value) {
  if (value === undefined) {
    return 0;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function updateEmotionForRecord(emotion, args, now) {
  const next = { ...emotion };
  if (args.mood && MOODS.has(args.mood)) {
    next.mood = args.mood;
  }
  if (args.stance) {
    next.stance = args.stance;
  }
  next.energy = clamp(next.energy + coerceDelta(args["energy-delta"]));
  next.socialBandwidth = clamp(
    next.socialBandwidth + coerceDelta(args["social-delta"]),
  );
  next.confidence = clamp(
    next.confidence + coerceDelta(args["confidence-delta"]),
  );
  next.stress = clamp(next.stress + coerceDelta(args["stress-delta"]));
  next.attachment = clamp(
    next.attachment + coerceDelta(args["attachment-delta"]),
  );
  next.lastHeartbeatAt = now;
  if (args.proactive === "true") {
    next.lastProactiveAt = now;
  }
  if (args.note) {
    next.notes = args.note;
  }
  next.updatedAt = now;
  return next;
}

function updateHeartbeatForRecord(heartbeat, args, now) {
  const next = { ...heartbeat };
  const mode = MODES.has(args.mode) ? args.mode : "silent";
  next.updatedAt = now;
  next.lastHeartbeatAt = now;
  next.lastReflectionAt = now;
  next.lastMode = mode;
  if (mode === "silent" || mode === "observe") {
    next.consecutiveSilentHeartbeats += 1;
    next.lastQuietMaintenanceAt = now;
  } else {
    next.consecutiveSilentHeartbeats = 0;
  }
  if (args.proactive === "true") {
    next.lastProactiveAt = now;
  }
  return next;
}

function usage() {
  process.stderr.write(
    [
      "Usage:",
      "  node scripts/companion-state.mjs ensure",
      "  node scripts/companion-state.mjs context",
      "  node scripts/companion-state.mjs record --mode silent --summary \"...\" --reason \"...\"",
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

  const state = ensureStateFiles();

  if (command === "ensure") {
    printJson({
      ok: true,
      workspaceRoot,
      files: {
        emotionStatePath,
        goalsPath,
        heartbeatStatePath,
        reflectionsDir,
      },
      state,
    });
    return;
  }

  if (command === "context") {
    const recommendation = recommendationForState(state);
    printJson({
      ok: true,
      now: nowIso(),
      workspaceRoot,
      emotion: state.emotion,
      heartbeat: state.heartbeat,
      goals: {
        activePhase: state.goals.activePhase,
        northStar: state.goals.northStar,
        primaryGoals: state.goals.primaryGoals,
        currentExperiments: state.goals.currentExperiments,
        guardrails: state.goals.guardrails,
      },
      recommendation,
    });
    return;
  }

  if (command === "record") {
    const mode = args.mode;
    if (!MODES.has(mode)) {
      process.stderr.write("record requires --mode silent|observe|nudge|act\n");
      process.exit(1);
    }
    if (!args.summary || !args.reason) {
      process.stderr.write("record requires --summary and --reason\n");
      process.exit(1);
    }
    const now = nowIso();
    const nextEmotion = updateEmotionForRecord(state.emotion, args, now);
    const nextHeartbeat = updateHeartbeatForRecord(state.heartbeat, args, now);
    writeJson(emotionStatePath, nextEmotion);
    writeJson(heartbeatStatePath, nextHeartbeat);

    const reflection = {
      ts: now,
      mode,
      proactive: args.proactive === "true",
      summary: args.summary,
      reason: args.reason,
      mood: nextEmotion.mood,
      energy: nextEmotion.energy,
      confidence: nextEmotion.confidence,
      stress: nextEmotion.stress,
      socialBandwidth: nextEmotion.socialBandwidth,
      attachment: nextEmotion.attachment,
      note: args.note ?? null,
    };
    appendReflection(reflection);

    printJson({
      ok: true,
      reflection,
      emotionStatePath,
      heartbeatStatePath,
      reflectionsDir,
    });
    return;
  }

  usage();
}

main();
