import { createPluginRuntimeStore } from "../../../dist/plugin-sdk/index.js";
import type { PluginRuntime } from "../../../dist/plugin-sdk/index.js";

const { setRuntime: setQqRuntime, getRuntime: getQqRuntime } =
  createPluginRuntimeStore<PluginRuntime>("QQ runtime not initialized - plugin not registered");

export { getQqRuntime, setQqRuntime };
