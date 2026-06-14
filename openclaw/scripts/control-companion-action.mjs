#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const bridgeScript = path.join(workspaceRoot, "scripts", "companion-bridge.mjs");

const PRESETS = {
  calm: {
    expression: "calm",
    motionPreset: "idle-soft",
    status: "Returning to a calm idle stance.",
  },
  nod: {
    expression: "warm",
    motionPreset: "gentle-nod",
    status: "Giving a small nod.",
  },
  attentive: {
    expression: "focused",
    motionPreset: "still-attentive",
    status: "Becoming more attentive.",
  },
  curious: {
    expression: "curious",
    motionPreset: "lean-in-soft",
    status: "Leaning in with curiosity.",
  },
  concern: {
    expression: "concerned",
    motionPreset: "guarded-soft",
    status: "Reacting with quiet concern.",
  },
  sleepy: {
    expression: "sleepy",
    motionPreset: "slow-blink",
    status: "Settling into a sleepy blink.",
  },
  wave: {
    expression: "warm",
    motionPreset: "wave-soft",
    status: "Giving a small wave.",
  },
  wake: {
    expression: "curious",
    motionPreset: "wake-soft",
    status: "Waking into motion.",
  },
};

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

function usage() {
  process.stderr.write(
    [
      "Usage:",
      "  node scripts/control-companion-action.mjs list",
      "  node scripts/control-companion-action.mjs trigger --preset nod [--text \"...\"]",
    ].join("\n") + "\n",
  );
  process.exit(1);
}

function triggerPreset(name, text) {
  const preset = PRESETS[name];
  if (!preset) {
    throw new Error(`Unknown preset: ${name}`);
  }
  const args = [
    bridgeScript,
    "publish",
    "--expression",
    preset.expression,
    "--motion-preset",
    preset.motionPreset,
    "--status",
    preset.status,
  ];
  if (text) {
    args.push("--text", text);
  }
  const result = spawnSync(process.execPath, args, {
    cwd: workspaceRoot,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || `bridge publish failed with status ${result.status}`);
  }
  return {
    ok: true,
    preset: name,
    text: text ?? null,
    status: preset.status,
    expression: preset.expression,
    motionPreset: preset.motionPreset,
    bridgeResult: JSON.parse(result.stdout),
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0];
  if (!command) {
    usage();
  }

  if (command === "list") {
    printJson(Object.entries(PRESETS).map(([name, value]) => ({ name, ...value })));
    return;
  }

  if (command === "trigger") {
    if (!args.preset) {
      usage();
    }
    printJson(triggerPreset(String(args.preset), args.text ? String(args.text) : null));
    return;
  }

  usage();
}

main();
