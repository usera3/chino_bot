import { describe, expect, it } from "vitest";
import plugin from "./index.js";

describe("chinobot bridge registration", () => {
  it("registers the new document and screenshot bridge tools", () => {
    const registered = new Set<string>();
    const api = {
      config: {},
      pluginConfig: {},
      registerTool(
        toolOrFactory: unknown,
        meta?: {
          name?: string;
        },
      ) {
        if (typeof meta?.name === "string" && meta.name.trim()) {
          registered.add(meta.name.trim());
          return;
        }
        if (typeof toolOrFactory === "function") {
          const tool = toolOrFactory({
            agentId: "main",
            sessionKey: "agent:main:test",
            messageChannel: "qq",
            agentAccountId: "default",
            requesterSenderId: "1446437177",
          });
          registered.add(String((tool as { name?: string }).name ?? ""));
          return;
        }
        registered.add(String((toolOrFactory as { name?: string }).name ?? ""));
      },
    };

    plugin.register(api as never);

    expect(registered.has("chinobot_read_pdf")).toBe(true);
    expect(registered.has("chinobot_read_excel")).toBe(true);
    expect(registered.has("chinobot_create_excel")).toBe(true);
    expect(registered.has("chinobot_convert_word_to_pdf")).toBe(true);
    expect(registered.has("chinobot_convert_pdf_to_word")).toBe(true);
    expect(registered.has("chinobot_tavily_search")).toBe(true);
    expect(registered.has("chinobot_web_screenshot")).toBe(true);
    expect(registered.has("chinobot_send_poke")).toBe(true);
    expect(registered.has("chinobot_analyze_avatar")).toBe(true);
    expect(registered.has("chinobot_set_group_ban")).toBe(true);
    expect(registered.has("chinobot_set_group_whole_ban")).toBe(true);
    expect(registered.has("chinobot_set_group_kick")).toBe(true);
    expect(registered.has("chinobot_set_group_admin")).toBe(true);
    expect(registered.has("chinobot_set_group_special_title")).toBe(true);
  });
});
