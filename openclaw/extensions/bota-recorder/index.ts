import { Type } from "@sinclair/typebox";
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type {
  AnyAgentTool,
  OpenClawPluginApi,
  OpenClawPluginServiceContext,
} from "../../dist/plugin-sdk/index.js";

const DEFAULT_PROJECT_ROOT = "/Users/mozi100/PycharmProjects/PythonProject6";
const DEFAULT_PYTHON_PATH =
  "/Users/mozi100/PycharmProjects/PythonProject6/firmware/host_tools/.venv-mac/bin/python";
const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 8008;
const DEFAULT_AUTO_START = true;
const DEFAULT_STARTUP_TIMEOUT_MS = 20_000;
const DEFAULT_NAME_CONTAINS = "Bota";
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;

type PluginConfig = {
  projectRoot: string;
  pythonPath: string;
  host: string;
  port: number;
  autoStart: boolean;
  startupTimeoutMs: number;
  defaultNameContains: string;
};

type GatewayState = {
  connected?: boolean;
  device?: {
    address?: string | null;
    name?: string | null;
  };
  device_status?: Record<string, unknown>;
  recording_status?: Record<string, unknown>;
  wifi_status?: number | null;
  pair_state?: number | null;
  prov_result?: number | null;
  local_upload_url?: string | null;
  download_dir?: string;
  wifi_upload_dir?: string;
};

type RecordingEntry = {
  file_id_hex: string;
  duration_sec: number;
  size_kb: number;
};

let managedGatewayProcess: ChildProcess | null = null;
let gatewayStartPromise: Promise<void> | null = null;
let serviceContext: OpenClawPluginServiceContext | null = null;

function resolveConfig(api: OpenClawPluginApi): PluginConfig {
  const raw = (api.pluginConfig ?? {}) as Record<string, unknown>;
  return {
    projectRoot:
      typeof raw.projectRoot === "string" && raw.projectRoot.trim()
        ? raw.projectRoot.trim()
        : DEFAULT_PROJECT_ROOT,
    pythonPath:
      typeof raw.pythonPath === "string" && raw.pythonPath.trim()
        ? raw.pythonPath.trim()
        : DEFAULT_PYTHON_PATH,
    host:
      typeof raw.host === "string" && raw.host.trim() ? raw.host.trim() : DEFAULT_HOST,
    port:
      typeof raw.port === "number" && Number.isFinite(raw.port) ? raw.port : DEFAULT_PORT,
    autoStart:
      typeof raw.autoStart === "boolean" ? raw.autoStart : DEFAULT_AUTO_START,
    startupTimeoutMs:
      typeof raw.startupTimeoutMs === "number" && Number.isFinite(raw.startupTimeoutMs)
        ? raw.startupTimeoutMs
        : DEFAULT_STARTUP_TIMEOUT_MS,
    defaultNameContains:
      typeof raw.defaultNameContains === "string" && raw.defaultNameContains.trim()
        ? raw.defaultNameContains.trim()
        : DEFAULT_NAME_CONTAINS,
  };
}

function createBaseUrl(cfg: PluginConfig): string {
  return `http://${cfg.host}:${cfg.port}`;
}

function textResult(text: string, details?: unknown) {
  return {
    content: [{ type: "text" as const, text }],
    details,
  };
}

function jsonResult(label: string, details: unknown) {
  return textResult(`${label}\n${JSON.stringify(details, null, 2)}`, details);
}

function isProcessAlive(child: ChildProcess | null): boolean {
  return Boolean(child && child.exitCode === null && !child.killed);
}

function requestTimeoutSignal(timeoutMs: number): AbortSignal {
  return AbortSignal.timeout(timeoutMs);
}

async function fetchJson<T>(params: {
  cfg: PluginConfig;
  method: string;
  pathname: string;
  body?: unknown;
  timeoutMs?: number;
}): Promise<T> {
  const url = `${createBaseUrl(params.cfg)}${params.pathname}`;
  const res = await fetch(url, {
    method: params.method,
    headers: params.body ? { "content-type": "application/json" } : undefined,
    body: params.body ? JSON.stringify(params.body) : undefined,
    signal: requestTimeoutSignal(params.timeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS),
  });

  const contentType = res.headers.get("content-type") ?? "";
  const parsed = contentType.includes("application/json")
    ? await res.json()
    : await res.text();
  if (!res.ok) {
    const detail =
      typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2);
    throw new Error(`HTTP ${res.status} ${res.statusText}: ${detail}`);
  }
  return parsed as T;
}

async function getState(cfg: PluginConfig): Promise<GatewayState> {
  return await fetchJson<GatewayState>({
    cfg,
    method: "GET",
    pathname: "/api/state",
    timeoutMs: 2_500,
  });
}

async function isGatewayHealthy(cfg: PluginConfig): Promise<boolean> {
  try {
    await getState(cfg);
    return true;
  } catch {
    return false;
  }
}

function resolveLogPaths(ctx: OpenClawPluginServiceContext | null) {
  const baseDir = ctx?.stateDir ?? path.join(DEFAULT_PROJECT_ROOT, ".openclaw", "bota-recorder");
  fs.mkdirSync(baseDir, { recursive: true });
  return {
    stdout: path.join(baseDir, "bota-gateway.stdout.log"),
    stderr: path.join(baseDir, "bota-gateway.stderr.log"),
  };
}

function spawnGatewayProcess(api: OpenClawPluginApi, cfg: PluginConfig): ChildProcess {
  const logs = resolveLogPaths(serviceContext);
  const stdoutFd = fs.openSync(logs.stdout, "a");
  const stderrFd = fs.openSync(logs.stderr, "a");

  const child = spawn(
    cfg.pythonPath,
    [
      "-m",
      "uvicorn",
      "firmware.host_tools.bota_web.server:app",
      "--host",
      cfg.host,
      "--port",
      String(cfg.port),
    ],
    {
      cwd: cfg.projectRoot,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
      stdio: ["ignore", stdoutFd, stderrFd],
    },
  );

  child.on("exit", (code, signal) => {
    if (managedGatewayProcess?.pid === child.pid) {
      api.logger.info(
        `[bota-recorder] local gateway exited (pid=${child.pid}, code=${code}, signal=${signal ?? "none"})`,
      );
      managedGatewayProcess = null;
    }
  });

  child.unref();
  api.logger.info(
    `[bota-recorder] spawned local gateway pid=${child.pid ?? "unknown"} at ${createBaseUrl(cfg)}`,
  );
  return child;
}

async function waitForGatewayHealthy(cfg: PluginConfig, timeoutMs: number): Promise<void> {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await isGatewayHealthy(cfg)) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error(`Timed out waiting for local Bota gateway at ${createBaseUrl(cfg)}`);
}

async function ensureGateway(api: OpenClawPluginApi): Promise<{ started: boolean; state: GatewayState }> {
  const cfg = resolveConfig(api);
  if (await isGatewayHealthy(cfg)) {
    return { started: false, state: await getState(cfg) };
  }

  if (!cfg.autoStart) {
    throw new Error(
      `Local Bota gateway is not reachable at ${createBaseUrl(cfg)} and autoStart is disabled.`,
    );
  }

  if (!gatewayStartPromise) {
    gatewayStartPromise = (async () => {
      if (!fs.existsSync(cfg.projectRoot)) {
        throw new Error(`projectRoot does not exist: ${cfg.projectRoot}`);
      }
      if (!fs.existsSync(cfg.pythonPath)) {
        throw new Error(`pythonPath does not exist: ${cfg.pythonPath}`);
      }
      if (!isProcessAlive(managedGatewayProcess)) {
        managedGatewayProcess = spawnGatewayProcess(api, cfg);
      }
      await waitForGatewayHealthy(cfg, cfg.startupTimeoutMs);
    })().finally(() => {
      gatewayStartPromise = null;
    });
  }

  await gatewayStartPromise;
  return { started: true, state: await getState(cfg) };
}

async function ensureConnected(
  api: OpenClawPluginApi,
  params: {
    address?: string;
    nameContains?: string;
    scanTimeout?: number;
    autoConnect?: boolean;
  },
): Promise<GatewayState> {
  const cfg = resolveConfig(api);
  const { state } = await ensureGateway(api);
  if (state.connected) {
    return state;
  }
  if (params.autoConnect === false) {
    throw new Error("Bota BLE gateway is not connected. Use action=connect first.");
  }

  await fetchJson<GatewayState>({
    cfg,
    method: "POST",
    pathname: "/api/connect",
    body: {
      address: params.address,
      name_contains: params.nameContains || cfg.defaultNameContains,
      scan_timeout: params.scanTimeout ?? 8.0,
    },
    timeoutMs: Math.max(
      DEFAULT_REQUEST_TIMEOUT_MS,
      Math.round((params.scanTimeout ?? 8.0) * 1000) + 5000,
    ),
  });
  return await getState(cfg);
}

function normalizeFileIdHex(raw: unknown): string | null {
  if (typeof raw !== "string") {
    return null;
  }
  const value = raw.trim().toUpperCase();
  if (!/^[0-9A-F]{8}$/.test(value)) {
    return null;
  }
  return value;
}

function pickRecording(entries: RecordingEntry[], pick: "first" | "last" | "largest"): RecordingEntry {
  if (entries.length === 0) {
    throw new Error("No recordings found on the device.");
  }
  if (pick === "first") {
    return entries[0]!;
  }
  if (pick === "last") {
    return entries[entries.length - 1]!;
  }
  return [...entries].sort((a, b) => b.size_kb - a.size_kb)[0]!;
}

async function stopManagedGateway(api: OpenClawPluginApi): Promise<void> {
  if (!managedGatewayProcess || !isProcessAlive(managedGatewayProcess)) {
    managedGatewayProcess = null;
    return;
  }
  const pid = managedGatewayProcess.pid;
  managedGatewayProcess.kill("SIGTERM");
  const startedAt = Date.now();
  while (isProcessAlive(managedGatewayProcess) && Date.now() - startedAt < 5000) {
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  if (isProcessAlive(managedGatewayProcess)) {
    managedGatewayProcess.kill("SIGKILL");
  }
  api.logger.info(`[bota-recorder] stopped managed local gateway pid=${pid ?? "unknown"}`);
  managedGatewayProcess = null;
}

const BotaRecorderSchema = Type.Object({
  action: Type.Union([
    Type.Literal("state"),
    Type.Literal("scan"),
    Type.Literal("connect"),
    Type.Literal("disconnect"),
    Type.Literal("start"),
    Type.Literal("stop"),
    Type.Literal("list"),
    Type.Literal("download"),
  ]),
  address: Type.Optional(Type.String({ description: "Explicit BLE address to connect to." })),
  name_contains: Type.Optional(
    Type.String({ description: "BLE device-name substring used when scanning. Defaults to the plugin config." }),
  ),
  scan_timeout: Type.Optional(
    Type.Number({ minimum: 1, maximum: 60, description: "BLE scan timeout in seconds." }),
  ),
  auto_connect: Type.Optional(
    Type.Boolean({ description: "For start/stop/list/download: connect automatically if needed. Default true." }),
  ),
  file_id_hex: Type.Optional(
    Type.String({ description: "Eight-character recording ID, for example A1B2C3D4." }),
  ),
  pick: Type.Optional(
    Type.Union([Type.Literal("first"), Type.Literal("last"), Type.Literal("largest")]),
  ),
  timeout: Type.Optional(
    Type.Number({ minimum: 1, maximum: 600, description: "Download timeout in seconds." }),
  ),
});

const plugin = {
  id: "bota-recorder",
  name: "Bota Recorder",
  description: "Control a local Bota recording pen over BLE via the existing Python gateway.",
  configSchema: {
    type: "object",
    additionalProperties: false,
    properties: {
      projectRoot: { type: "string", default: DEFAULT_PROJECT_ROOT },
      pythonPath: { type: "string", default: DEFAULT_PYTHON_PATH },
      host: { type: "string", default: DEFAULT_HOST },
      port: { type: "number", default: DEFAULT_PORT, minimum: 1, maximum: 65535 },
      autoStart: { type: "boolean", default: DEFAULT_AUTO_START },
      startupTimeoutMs: {
        type: "number",
        default: DEFAULT_STARTUP_TIMEOUT_MS,
        minimum: 1000,
        maximum: 120000,
      },
      defaultNameContains: { type: "string", default: DEFAULT_NAME_CONTAINS },
    },
  },
  register(api: OpenClawPluginApi) {
    api.registerService({
      id: "bota-recorder",
      start: async (ctx) => {
        serviceContext = ctx;
        api.logger.info(
          `[bota-recorder] ready (gateway ${createBaseUrl(resolveConfig(api))})`,
        );
      },
      stop: async () => {
        await stopManagedGateway(api);
        serviceContext = null;
      },
    });

    api.registerTool(
      {
        name: "bota_recorder",
        description:
          "Control a local Bota recording pen over BLE. Supports scanning, connecting, starting/stopping recording, listing recordings, and downloading a recording file to the local machine.",
        parameters: BotaRecorderSchema,
        async execute(_toolCallId, rawParams) {
          const params = rawParams as {
            action: "state" | "scan" | "connect" | "disconnect" | "start" | "stop" | "list" | "download";
            address?: string;
            name_contains?: string;
            scan_timeout?: number;
            auto_connect?: boolean;
            file_id_hex?: string;
            pick?: "first" | "last" | "largest";
            timeout?: number;
          };

          const cfg = resolveConfig(api);

          try {
            if (params.action === "state") {
              const { started, state } = await ensureGateway(api);
              return jsonResult(
                started
                  ? "Bota gateway started and state fetched."
                  : "Bota gateway state fetched.",
                state,
              );
            }

            if (params.action === "scan") {
              await ensureGateway(api);
              const devices = await fetchJson<{ devices: unknown[] }>({
                cfg,
                method: "GET",
                pathname: `/api/scan?timeout=${encodeURIComponent(String(params.scan_timeout ?? 6))}`,
                timeoutMs: Math.max(
                  DEFAULT_REQUEST_TIMEOUT_MS,
                  Math.round((params.scan_timeout ?? 6) * 1000) + 5000,
                ),
              });
              return jsonResult("Bota BLE scan completed.", devices);
            }

            if (params.action === "connect") {
              await ensureGateway(api);
              const state = await fetchJson<GatewayState>({
                cfg,
                method: "POST",
                pathname: "/api/connect",
                body: {
                  address: params.address,
                  name_contains: params.name_contains || cfg.defaultNameContains,
                  scan_timeout: params.scan_timeout ?? 8.0,
                },
                timeoutMs: Math.max(
                  DEFAULT_REQUEST_TIMEOUT_MS,
                  Math.round((params.scan_timeout ?? 8.0) * 1000) + 5000,
                ),
              });
              return jsonResult("Bota BLE connected.", state);
            }

            if (params.action === "disconnect") {
              await ensureGateway(api);
              const state = await fetchJson<GatewayState>({
                cfg,
                method: "POST",
                pathname: "/api/disconnect",
              });
              return jsonResult("Bota BLE disconnected.", state);
            }

            if (params.action === "start") {
              const state = await ensureConnected(api, {
                address: params.address,
                nameContains: params.name_contains,
                scanTimeout: params.scan_timeout,
                autoConnect: params.auto_connect,
              });
              await fetchJson<{ ok: boolean }>({
                cfg,
                method: "POST",
                pathname: "/api/record/start",
              });
              return jsonResult("Bota recording start command sent.", state);
            }

            if (params.action === "stop") {
              const state = await ensureConnected(api, {
                address: params.address,
                nameContains: params.name_contains,
                scanTimeout: params.scan_timeout,
                autoConnect: params.auto_connect,
              });
              await fetchJson<{ ok: boolean }>({
                cfg,
                method: "POST",
                pathname: "/api/record/stop",
              });
              return jsonResult("Bota recording stop command sent.", state);
            }

            if (params.action === "list") {
              await ensureConnected(api, {
                address: params.address,
                nameContains: params.name_contains,
                scanTimeout: params.scan_timeout,
                autoConnect: params.auto_connect,
              });
              const result = await fetchJson<{ entries: RecordingEntry[] }>({
                cfg,
                method: "GET",
                pathname: "/api/recordings",
              });
              return jsonResult("Bota recordings listed.", result);
            }

            if (params.action === "download") {
              await ensureConnected(api, {
                address: params.address,
                nameContains: params.name_contains,
                scanTimeout: params.scan_timeout,
                autoConnect: params.auto_connect,
              });
              const listResult = await fetchJson<{ entries: RecordingEntry[] }>({
                cfg,
                method: "GET",
                pathname: "/api/recordings",
              });
              const entries = listResult.entries ?? [];
              const fileId =
                normalizeFileIdHex(params.file_id_hex) ??
                pickRecording(entries, params.pick ?? "largest").file_id_hex;
              const downloadResult = await fetchJson<{ ok: boolean; path: string; url: string }>({
                cfg,
                method: "POST",
                pathname: `/api/recordings/${fileId}/download`,
                body: { timeout: params.timeout ?? 120.0 },
                timeoutMs: Math.max(
                  DEFAULT_REQUEST_TIMEOUT_MS,
                  Math.round((params.timeout ?? 120.0) * 1000) + 5000,
                ),
              });
              return jsonResult("Bota recording downloaded.", {
                file_id_hex: fileId,
                ...downloadResult,
              });
            }

            return textResult(`Unsupported action: ${(params as { action?: string }).action ?? "unknown"}`);
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            return textResult(`Bota recorder action failed: ${message}`);
          }
        },
      } as AnyAgentTool,
      { optional: true },
    );
  },
};

export default plugin;
