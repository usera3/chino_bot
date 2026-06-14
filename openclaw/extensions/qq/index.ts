import type { ChannelPlugin, OpenClawPluginApi } from "../../dist/plugin-sdk/index.js";
import { emptyPluginConfigSchema } from "../../dist/plugin-sdk/index.js";
import { qqPlugin } from "./src/channel.js";
import { createQqService } from "./src/service.js";
import { setQqRuntime } from "./src/runtime.js";
import { registerQqNativeTools } from "./src/tools.js";

const plugin = {
  id: "qq",
  name: "QQ",
  description: "QQ channel plugin via NapCat / OneBot V11 reverse WebSocket",
  configSchema: emptyPluginConfigSchema(),
  register(api: OpenClawPluginApi) {
    setQqRuntime(api.runtime);
    api.registerChannel({ plugin: qqPlugin as ChannelPlugin });
    api.registerService(createQqService(api));
    registerQqNativeTools(api);
  },
};

export default plugin;
