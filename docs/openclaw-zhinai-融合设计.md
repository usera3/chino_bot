# OpenClaw + zhinai 融合设计

## 目标

让融合后的机器人以 `openclaw` 作为唯一的大脑和上下文/记忆真源，同时复用 `zhinai-bot-v3` 已经打磨好的 QQ 工具与执行体验。

核心思路不是简单换一段人设，而是做单脑分层：

- `openclaw` 负责前台聊天、上下文、记忆、skills、MCP 编排
- `zhinai` 负责 QQ 接入、QQ 工具执行、文档/工作流/代码等能力执行

---

## 两边各自的长处

### OpenClaw 擅长什么

- 场景感知强：群聊、私聊、轻互动、直接请求会区别对待
- 聊天自然：短句、少标点、少客服腔、少“如果你愿意我还能……”
- 会看气氛：先接住当下社交动作，再决定要不要解释
- 记忆更偏会话和工作区：谁在聊、最近发生了什么、这个群平时怎么说话

### zhinai-bot-v3 擅长什么

- 工具生态丰富：邮件、工作流、文件、代码、截图、文档、QQ 互动等
- 管家式调度：LLM + 工具链推理
- NoneBot/OneBot 集成完整，适合本地 QQ 机器人直接落地

---

## 融合后的职责分层

### 1. 对话层

由 `openclaw` 接管：

- 当前是群聊还是私聊
- 这条消息是轻聊天还是明确要详细回答
- 该不该少标点、该不该只回一句
- 该不该压掉“客服味”和“教程味”

### 2. 管家层

仍由 `openclaw` 接管：

- 理解意图
- 规划步骤
- 选择工具
- 整合结果

### 3. 执行层

由 `zhinai-bot-v3` 接管：

- QQ 消息收发
- QQ 相关原生工具
- 文档/工作流/代码/邮件等现成能力
- 执行结果返回

### 4. 记忆层

只保留 `openclaw` 作为唯一真源：

- 会话上下文：`openclaw` session
- 工作区记忆：`AGENTS.md` / `SOUL.md` / `USER.md` / `MEMORY.md` / `memory/*.md`
- 语义记忆：`openclaw` memory-core / memory search
- 群聊风格记忆：`memory/group-social/...`

`zhinai-bot-v3` 的 `DualVectorStore` 在融合态中不再作为主记忆使用。
如果要保留，也只能作为临时能力缓存，不能与 `openclaw` 并列成为第二套聊天记忆系统。

---

## 本次代码落点

- `core/openclaw_style.py`
  - 这是过渡层，用来把 `zhinai` 的聊天味道先往 `openclaw` 靠
  - 最终目标不是让它长期充当主脑，而是为后续彻底外接 `openclaw` 做风格对齐

- `core/butler.py`
  - 当前先减少它自己的“第二大脑”属性
  - 在过渡阶段只做风格和上下文收敛，不再鼓励它维护独立长期聊天记忆

- `plugins/chat_plugin.py`
  - 把 QQ 场景元信息传给 Butler
  - 修复“只有图片没有文本”时默认提示词注入过晚的问题

---

## 当前融合原则

一句话总结：

> 用 `openclaw` 思考和记忆，用 `zhinai` 执行和发消息。

也就是：

- 最终回复权只属于 `openclaw`
- `zhinai` 不再维护自己的主聊天上下文
- `zhinai` 的工具体验被保留，并作为 `openclaw` 可调用的能力面
- `openclaw` 现有 QQ 工具可以降级、替换或废除，只保留真正比 `zhinai` 更强的部分
