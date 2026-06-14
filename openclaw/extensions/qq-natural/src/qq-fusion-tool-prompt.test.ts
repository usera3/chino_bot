import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq fusion tool prompt", () => {
  it("includes coordinated document and screenshot tool guidance", () => {
    const prompt = __testing.buildQqConversationSystemPrompt({
      account: {
        accountId: "default",
        config: {
          naturalChat: {
            enabled: true,
            applyToGroups: true,
            applyToDirect: true,
            defaultPersona: "chino",
          },
        },
      } as never,
      cfg: {} as never,
      chatType: "direct",
      engagementMode: "direct",
    });

    expect(prompt).toContain("prefer chinobot_read_pdf or chinobot_read_excel");
    expect(prompt).toContain(
      "do the document step first, then use chinobot_send_file for the produced file",
    );
    expect(prompt).toContain("prefer chinobot_web_screenshot when available");
    expect(prompt).toContain("do not redundantly call chinobot_send_image");
    expect(prompt).toContain("prefer chinobot_analyze_avatar when available");
    expect(prompt).toContain("first use chinobot_analyze_avatar to get avatar_url");
    expect(prompt).toContain("QQ friend requests are auto-approved in the background");
    expect(prompt).toContain("instead of saying you lack the capability");
    expect(prompt).toContain("do not send a lead-in progress line");
    expect(prompt).toContain(
      "Do not claim that an image, card, poster, screenshot, or meme is already done",
    );
    expect(prompt).toContain("delivery_mode is explicit_qq_media_send");
    expect(prompt).toContain("If a QQSocialAgency block is present");
    expect(prompt).toContain("mode is light_surprise or staged_surprise");
    expect(prompt).toContain("At most one surprise move per reply");
    expect(prompt).toContain("they cheekily snuck a touch on you");
    expect(prompt).toContain("又来占我便宜");
    expect(prompt).toContain("prefer chinobot_send_poke when available");
    expect(prompt).toContain("prefer chinobot_send_fake_message when available");
    expect(prompt).toContain("use the current requester plus the bot as two participants");
  });
});
