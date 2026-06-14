#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const profilesDir = path.join(workspaceRoot, "companion", "body-profiles");
const adapterConfigPath = path.join(
  workspaceRoot,
  "companion",
  "open-llm-vtuber-adapter.json",
);

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

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function listProfiles() {
  if (!fs.existsSync(profilesDir)) {
    return [];
  }
  return fs
    .readdirSync(profilesDir)
    .filter((name) => name.endsWith(".json"))
    .map((name) => ({
      fileName: name,
      filePath: path.join(profilesDir, name),
      profile: readJson(path.join(profilesDir, name)),
    }));
}

function findProfile(profileName) {
  const profiles = listProfiles();
  const match = profiles.find(
    (entry) =>
      entry.fileName === `${profileName}.json` ||
      entry.profile.slug === profileName ||
      entry.profile.name === profileName,
  );
  if (!match) {
    throw new Error(`Body profile not found: ${profileName}`);
  }
  return match;
}

function current() {
  return {
    adapterConfigPath,
    adapterConfig: readJson(adapterConfigPath),
    availableProfiles: listProfiles().map((entry) => ({
      fileName: entry.fileName,
      name: entry.profile.name,
      slug: entry.profile.slug,
      visualRole: entry.profile.visualRole ?? null,
    })),
  };
}

function applyProfile(profileName) {
  const selected = findProfile(profileName);
  const profile = selected.profile;
  const currentConfig = readJson(adapterConfigPath);

  if (!profile.modelInfo || !profile.static) {
    throw new Error(
      `Profile "${profileName}" is not an importable shell body profile.`,
    );
  }

  const nextConfig = {
    ...currentConfig,
    avatarFilename:
      typeof profile.avatarFilename === "string"
        ? profile.avatarFilename
        : currentConfig.avatarFilename,
    modelInfo: {
      ...currentConfig.modelInfo,
      ...profile.modelInfo,
    },
    static: {
      ...currentConfig.static,
      ...profile.static,
    },
  };

  writeJson(adapterConfigPath, nextConfig);
  return {
    ok: true,
    appliedProfile: {
      fileName: selected.fileName,
      name: profile.name,
      slug: profile.slug,
    },
    adapterConfigPath,
    adapterConfig: nextConfig,
  };
}

function usage() {
  process.stderr.write(
    [
      "Usage:",
      "  node scripts/select-companion-body.mjs current",
      "  node scripts/select-companion-body.mjs list",
      "  node scripts/select-companion-body.mjs apply --profile <slug>",
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

  if (command === "current") {
    printJson(current());
    return;
  }

  if (command === "list") {
    printJson(
      listProfiles().map((entry) => ({
        fileName: entry.fileName,
        name: entry.profile.name,
        slug: entry.profile.slug,
        visualRole: entry.profile.visualRole ?? null,
      })),
    );
    return;
  }

  if (command === "apply") {
    if (!args.profile) {
      process.stderr.write("apply requires --profile\n");
      process.exit(1);
    }
    printJson(applyProfile(args.profile));
    return;
  }

  usage();
}

main();
