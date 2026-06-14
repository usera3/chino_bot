import type { ChannelPlugin, OpenClawPluginApi } from "../../dist/plugin-sdk/index.js";
import { DEFAULT_LOCAL_QWEN_CLONE_TTS } from "../shared/local-qwen-clone-tts.js";
import { qqPlugin } from "./src/channel.js";
import { createQqService } from "./src/service.js";
import { setQqRuntime } from "./src/runtime.js";
import { registerQqNativeTools } from "./src/tools.js";

const qqNaturalConfigSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    voiceSynthesis: {
      type: "object",
      additionalProperties: false,
      properties: {
        enabled: { type: "boolean", default: false },
        projectRoot: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.projectRoot,
        },
        pythonPath: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.pythonPath,
        },
        scriptPath: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.scriptPath,
        },
        modelPath: {
          type: "string",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.modelPath,
        },
        voiceName: { type: "string", default: DEFAULT_LOCAL_QWEN_CLONE_TTS.voiceName },
        timeoutMs: { type: "number", default: 120000, minimum: 1000, maximum: 300000 },
        fallbackToSystemSay: {
          type: "boolean",
          default: DEFAULT_LOCAL_QWEN_CLONE_TTS.fallbackToSystemSay,
        },
      },
    },
  },
} as const;

const plugin = {
  id: "qq-natural",
  name: "QQ Natural",
  description: "Natural-chat QQ channel plugin via NapCat / OneBot V11 reverse WebSocket",
  configSchema: qqNaturalConfigSchema,
  register(api: OpenClawPluginApi) {
    setQqRuntime(api.runtime);
    api.registerChannel({ plugin: qqPlugin as ChannelPlugin });
    api.registerService(createQqService(api));
    registerQqNativeTools(api);
  },
};

export default plugin;
