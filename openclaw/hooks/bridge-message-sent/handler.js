import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..", "..");
const bridgeScriptPath = path.join(workspaceRoot, "scripts", "companion-bridge.mjs");
const MAIN_SESSION_KEY = "agent:main:main";
const HEARTBEAT_TOKEN = "HEARTBEAT_OK";

function shouldMirror(event) {
  if (event?.type !== "message" || event?.action !== "sent") {
    return false;
  }
  if (event.sessionKey !== MAIN_SESSION_KEY) {
    return false;
  }

  const content = String(event.context?.content ?? "").trim();
  if (!event.context?.success || !content || content === HEARTBEAT_TOKEN) {
    return false;
  }

  return true;
}

function publishToBridge(text) {
  return new Promise((resolve, reject) => {
    execFile(
      process.execPath,
      [
        bridgeScriptPath,
        "publish",
        "--text",
        text,
        "--source",
        "message-sent-hook",
        "--status",
        "Speaking from the main session.",
      ],
      { cwd: workspaceRoot },
      (error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      },
    );
  });
}

const mirrorMainSessionOutbound = async (event) => {
  if (!shouldMirror(event)) {
    return;
  }

  const text = String(event.context?.content ?? "").trim();
  await publishToBridge(text);
};

export default mirrorMainSessionOutbound;
