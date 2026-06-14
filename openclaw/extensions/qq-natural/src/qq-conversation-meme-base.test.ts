import { describe, expect, it } from "vitest";
import { __testing } from "./service.js";

describe("qq conversation meme base image", () => {
  it("stores media records flat and picks the latest usable image", () => {
    __testing.resetQqConversationStateForTest();
    const conversationKey = "qq:default:group:673105016";

    __testing.rememberQqMediaRecords(conversationKey, [
      {
        id: "older-image",
        source: "inbound",
        message_id: "100",
        sender_id: "1",
        sender_name: "tester",
        type: "image",
        caption: "",
        quoted_text: "",
        image_count: 1,
        images: [
          {
            index: 1,
            ocr: "",
            alt: "旧图",
            vision_summary: "旧图",
            path: "/tmp/older.png",
          },
        ],
        summary: "旧图",
        created_at: 1000,
      },
    ]);

    __testing.rememberQqMediaRecords(conversationKey, [
      {
        id: "newer-image",
        source: "inbound",
        message_id: "101",
        sender_id: "1",
        sender_name: "tester",
        type: "image",
        caption: "",
        quoted_text: "",
        image_count: 1,
        images: [
          {
            index: 1,
            ocr: "",
            alt: "新图",
            vision_summary: "新图",
            path: "/tmp/newer.png",
          },
        ],
        summary: "新图",
        created_at: 2000,
      },
    ]);

    expect(
      __testing.resolveQqConversationMemeBaseImage({
        conversationKey,
        preferInbound: true,
      }),
    ).toMatchObject({
      imagePath: "/tmp/newer.png",
      mediaId: "newer-image",
      summary: "新图",
    });
  });
});
