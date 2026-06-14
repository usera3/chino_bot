# codex2openclaw

维修 OpenClaw 前，优先先读这份文件。

## QQ 桥联现状

- 当前生效的 QQ 插件是 `qq-natural`
- stock `extensions/qq` 处于未启用状态
- QQ 桥联链路是：
  - `QQ / NapCat`
  - `OneBot V11 reverse WebSocket`
  - `ws://127.0.0.1:8080/onebot/v11/ws`
  - `extensions/qq-natural/src/service.ts`
  - `OpenClaw gateway`
- Gateway 本地入口常见为 `127.0.0.1:18789`
- NapCat 真正生效的配置目录不是 `Documents/napcat/config/`，而是：
  - `/Users/mozi100/Library/Containers/com.tencent.qq/Data/Library/Application Support/QQ/NapCat/config/`
- 当前关键配置文件：
  - `onebot11_2509109290.json`
  - `napcat_2509109290.json`
  - `napcat_protocol_2509109290.json`
  - `webui.json`

## QQ 黑名单功能

- 配置键：`channels.qq.blockedUserIds`
- 类型：`string[]`
- 当前已加入黑名单：`2136387285`
- 作用范围：群聊 + 私聊
- 行为：命中后在入站最早阶段直接丢弃，不做 parse、排队、follow-up watch、social join、media 绑定，也不会回复

## QQ 图片处理现状

- 已移除 QQ 最近图片缓存/追踪的主运行路径
- 已禁用 reply target 旧图绑定、recent media replay、recent media buffer prompt 注入
- 现在只会把“当前允许接收的这次消息里的图片”和当前文字上下文一起给模型
- 已增加 `media_ingress` 调试事件，会记录入站图片的 `raw_file`、`raw_url`、`preferred_ref`、是否命中本地文件
- 已增加 `overload_gate`：当单会话积压时，低价值噪音消息会被明确跳过，避免挤占高价值回复
- 已增加 `fairness_gate`：当其他会话也在排队时，当前会话的低价值噪音消息会更早被压掉，减少单窗口独占
- 所有 `dispatch_gate` 现在自动记录全局负载指标：`competingConversationCount`、`totalPendingCount`
- 所有 `dispatch_gate` 现在自动记录 `decisionStage`：`immediate`、`overload`、`fairness`、`stale`、`mention`、`dispatch`
- `fairness_gate` 当前会区分：`mention`、`reply`、`direct-chat`、`direct-media`、`direct-noise`、`group-question`、`group-media-question`、`group-media`、`group-media-noise`、`group-noise`、`group-plain`
- 已增加 `stale_gate`：按 `fairnessClass` 分层超时，自动放弃已经错过时机的旧消息
- 已新增统一调度入口 `resolveQqSchedulingDecision`，按顺序协调 `overload_gate -> fairness_gate -> stale_gate`
- 如果排查图片理解异常，优先看 `extensions/qq-natural/src/service.ts` 里的 `prepareQqInboundMediaContext` 和 `buildQqAgentBody`

## 关键代码位置

- 配置类型：`extensions/qq-natural/src/types.ts`
- 配置 schema：`extensions/qq-natural/src/channel.ts`
- 账号配置落地：`extensions/qq-natural/src/accounts.ts`
- 入站黑名单拦截：`extensions/qq-natural/src/service.ts`
- 回归测试：`extensions/qq-natural/src/blocked-user.test.ts`
- 图片上下文测试：`extensions/qq-natural/src/media-context.test.ts`
- 图片入站引用测试：`extensions/qq-natural/src/inbound-image-ref.test.ts`
- 图片入站调试测试：`extensions/qq-natural/src/media-ingress-debug.test.ts`
- QQ 域名兜底下载测试：`extensions/qq-natural/src/qq-remote-media-fallback.test.ts`
- 过载降级测试：`extensions/qq-natural/src/overload-gate.test.ts`
- 公平门测试：`extensions/qq-natural/src/fairness-gate.test.ts`
- 全局负载摘要测试：`extensions/qq-natural/src/load-debug.test.ts`
- 过期门测试：`extensions/qq-natural/src/stale-gate.test.ts`
- 调度决策顺序测试：`extensions/qq-natural/src/scheduling-decision.test.ts`
- 决策阶段测试：`extensions/qq-natural/src/decision-stage.test.ts`

## 排障线索

- 命中黑名单时会出现日志：
  - `[qq] ignored inbound message from blocked user: user=... type=... group=...`
- 如果看到消息继续进入 `dispatch_gate`、`reply_target_resolve`、`media_resolve`，说明黑名单没有在入站早期命中
- 当前本机运行配置文件是 `~/.openclaw/openclaw.json`
- 如果 Gateway 正常、QQ 进程也在，但一直没有：
  - `[qq] NapCat / OneBot connected on ws://127.0.0.1:8080/onebot/v11/ws`
  - 优先检查 NapCat 实际生效文件 `onebot11_2509109290.json`
- 这台机器最近一次真故障根因就是：
  - NapCat 配置里 8080 那条 websocket client 写成了 `ws://127.0.0.1:8080/onebot/v11/`
  - 但 OpenClaw listener 实际监听的是 `ws://127.0.0.1:8080/onebot/v11/ws`
  - 修成 `/onebot/v11/ws` 并重启 gateway 后恢复

## 维护约定

- 以后如果要维修 OpenClaw，先检查这份文件是否已有相关资料
- 如果再新增 OpenClaw 的本地定制能力，也把入口、配置键、测试位置和排障线索补到这里
- 当前这份 checkout 的核心 CLI / gateway / outbound 主逻辑没有完整 `src/` 源码树，很多核心修改只能先落在 `dist/*.js` 运行时 chunk 上
- 因此如果以后升级或重装 OpenClaw，需要重点复核这类运行时补丁是否被新 build 覆盖
- 已新增本地补丁脚本：
  - `scripts/openclaw-local-patches.mjs`
- 用法：
  - `node scripts/openclaw-local-patches.mjs status`
  - `node scripts/openclaw-local-patches.mjs apply`
- 当前脚本会检查/修复两类本地定制：
  - OpenClaw `dist/*.js` 中的 QQ CLI send -> gateway send 补丁
  - NapCat 实际生效配置里 OpenClaw reverse WS URL 是否指向 `/onebot/v11/ws`
- 建议：
  - 每次升级 OpenClaw 后先跑一次 `apply`
  - 如果 QQ 桥又莫名掉线，也先跑一次 `status`
