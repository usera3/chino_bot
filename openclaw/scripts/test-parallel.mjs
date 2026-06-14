import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..");

function resolveVitestBin() {
  const executable = process.platform === "win32" ? "vitest.cmd" : "vitest";
  return path.join(workspaceRoot, "node_modules", ".bin", executable);
}

async function pathExists(pathname) {
  try {
    await fs.access(pathname);
    return true;
  } catch {
    return false;
  }
}

function buildTasks() {
  const tasks = [];
  const unitConfigPath = path.join(workspaceRoot, "vitest.unit.config.ts");
  tasks.push({
    name: "unit",
    kind: "vitest",
    configPath: unitConfigPath,
    args: ["run", "--config", "vitest.unit.config.ts"],
  });
  return tasks;
}

async function runVitestTask(vitestBin, task) {
  return await new Promise((resolve) => {
    const child = spawn(vitestBin, task.args, {
      cwd: workspaceRoot,
      env: process.env,
      stdio: "inherit",
    });
    child.on("close", (code, signal) => {
      resolve({
        name: task.name,
        ok: code === 0,
        code,
        signal,
      });
    });
    child.on("error", (error) => {
      resolve({
        name: task.name,
        ok: false,
        code: null,
        signal: null,
        error: String(error?.message || error),
      });
    });
  });
}

async function main() {
  const vitestBin = resolveVitestBin();
  if (!(await pathExists(vitestBin))) {
    throw new Error(`vitest executable not found: ${vitestBin}`);
  }

  const availableTasks = [];
  for (const task of buildTasks()) {
    if (task.configPath && !(await pathExists(task.configPath))) {
      continue;
    }
    availableTasks.push(task);
  }

  if (availableTasks.length === 0) {
    process.stdout.write("\n[test-parallel] no configured test tasks are available in this checkout; skipping.\n");
    return;
  }

  const results = [];
  for (const task of availableTasks) {
    process.stdout.write(`\n[test-parallel] running ${task.name}\n`);
    results.push(await runVitestTask(vitestBin, task));
  }

  const failed = results.filter((entry) => !entry.ok);
  if (failed.length > 0) {
    const summary = failed
      .map((entry) => `${entry.name} failed${entry.code != null ? ` (exit ${entry.code})` : ""}`)
      .join(", ");
    throw new Error(summary);
  }

  process.stdout.write(
    `\n[test-parallel] completed ${results.map((entry) => entry.name).join(", ")}\n`,
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    process.stderr.write(`${String(error instanceof Error ? error.stack || error.message : error)}\n`);
    process.exitCode = 1;
  });
}
