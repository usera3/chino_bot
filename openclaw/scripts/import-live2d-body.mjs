#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");
const assetsLive2dDir = path.join(workspaceRoot, "companion-assets", "live2d");
const assetsAvatarsDir = path.join(workspaceRoot, "companion-assets", "avatars");
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

function sanitizeSlug(input) {
  return String(input)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function copyDirectoryRecursive(srcDir, destDir) {
  fs.mkdirSync(destDir, { recursive: true });
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const srcPath = path.join(srcDir, entry.name);
    const destPath = path.join(destDir, entry.name);
    if (entry.isDirectory()) {
      copyDirectoryRecursive(srcPath, destPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function applyImportedProfile(profile) {
  const currentConfig = readJson(adapterConfigPath);
  const nextConfig = {
    ...currentConfig,
    avatarFilename: profile.avatarFilename,
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
  return nextConfig;
}

function usage() {
  process.stderr.write(
    [
      "Usage:",
      "  node scripts/import-live2d-body.mjs --name <name> --slug <slug> --model-dir <dir> --model-file <relative-model-file> [--avatar <path>] [--activate true]",
    ].join("\n") + "\n",
  );
  process.exit(1);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const required = ["name", "slug", "model-dir", "model-file"];
  for (const key of required) {
    if (!args[key]) {
      usage();
    }
  }

  const slug = sanitizeSlug(args.slug);
  if (!slug) {
    throw new Error("slug resolves to empty value");
  }

  const sourceModelDir = path.resolve(String(args["model-dir"]));
  const sourceModelFile = String(args["model-file"]);
  const resolvedSourceModelFile = path.resolve(sourceModelDir, sourceModelFile);
  if (!fs.existsSync(sourceModelDir) || !fs.statSync(sourceModelDir).isDirectory()) {
    throw new Error(`model dir not found: ${sourceModelDir}`);
  }
  if (!fs.existsSync(resolvedSourceModelFile) || !fs.statSync(resolvedSourceModelFile).isFile()) {
    throw new Error(`model file not found: ${resolvedSourceModelFile}`);
  }

  const targetModelDir = path.join(assetsLive2dDir, slug);
  copyDirectoryRecursive(sourceModelDir, targetModelDir);

  let avatarFilename = "";
  if (args.avatar) {
    const sourceAvatarPath = path.resolve(String(args.avatar));
    if (!fs.existsSync(sourceAvatarPath) || !fs.statSync(sourceAvatarPath).isFile()) {
      throw new Error(`avatar file not found: ${sourceAvatarPath}`);
    }
    const ext = path.extname(sourceAvatarPath);
    avatarFilename = `${slug}${ext}`;
    fs.mkdirSync(assetsAvatarsDir, { recursive: true });
    fs.copyFileSync(sourceAvatarPath, path.join(assetsAvatarsDir, avatarFilename));
  }

  const profile = {
    name: String(args.name),
    slug,
    description: String(args.description ?? `Imported Live2D body for ${args.name}`),
    visualRole: "imported-body",
    avatarFilename,
    modelInfo: {
      name: String(args.name),
      description: String(args.description ?? `Imported Live2D body for ${args.name}`),
      url: `/live2d/${slug}/${sourceModelFile.replaceAll(path.sep, "/")}`,
      kScale: Number(args["k-scale"] ?? 0.45),
      initialXshift: Number(args["x-shift"] ?? 0),
      initialYshift: Number(args["y-shift"] ?? 0),
      idleMotionGroupName: String(args["idle-motion-group"] ?? "Idle"),
      defaultEmotion: String(args["default-emotion"] ?? "neutral"),
      emotionMap: {
        calm: "neutral",
        curious: "surprised",
        focused: "serious",
        pleased: "happy",
        concerned: "sad",
        tired: "neutral",
      },
      pointerInteractive: true,
      scrollToResize: true,
      initialScale: Number(args["initial-scale"] ?? 0.9),
    },
    static: {
      live2dDir: assetsLive2dDir,
      avatarsDir: assetsAvatarsDir,
      backgroundsDir: "",
    },
  };

  const profilePath = path.join(profilesDir, `${slug}.json`);
  writeJson(profilePath, profile);

  const result = {
    ok: true,
    profilePath,
    profile,
    copiedModelDir: targetModelDir,
    copiedAvatarPath: avatarFilename
      ? path.join(assetsAvatarsDir, avatarFilename)
      : null,
    activated: false,
  };

  if (String(args.activate ?? "false") === "true") {
    result.activated = true;
    result.adapterConfig = applyImportedProfile(profile);
  }

  printJson(result);
}

main();
