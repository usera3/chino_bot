# NoneBot 集成说明

## ✅ 已完成

zhinai-bot-v3 已成功集成 NoneBot，可以在 QQ 上运行！

---

## 📁 新增文件

```
zhinai-bot-v3/
├── bot.py                      # NoneBot 主程序
├── plugins/
│   ├── __init__.py
│   └── chat_plugin.py          # 聊天插件（集成 Butler）
├── start_bot.sh                # 启动脚本
├── stop_bot.sh                 # 停止脚本
├── test_nonebot.py             # NoneBot 集成测试
└── .env                        # 环境变量配置
```

---

## 🚀 快速开始

### 1. 确保依赖已安装

```bash
pip install nonebot2 nonebot-adapter-onebot
```

### 2. 配置环境变量

`.env` 文件已自动创建，包含：
- NoneBot 配置（端口 8081）
- DeepSeek API Key
- QQ 邮箱配置
- 其他 API Keys

### 3. 启动机器人

```bash
./start_bot.sh
```

**输出**:
```
================================
   启动 zhinai-bot-v3
================================

🚀 启动 NoneBot...

✅ NoneBot 已启动 (PID: xxxxx)

📝 日志文件: logs/bot.log
📡 监听端口: 8081

💡 提示:
   - 查看日志: tail -f logs/bot.log
   - 停止机器人: ./stop_bot.sh

================================
   启动完成！
================================
```

### 4. 配置 go-cqhttp

确保 go-cqhttp 配置中的反向 WebSocket 地址为：
```yaml
ws://127.0.0.1:8081/onebot/v11/ws
```

### 5. 测试

在 QQ 中：
- **私聊**: 直接发送消息
- **群聊**: @机器人 发送消息

---

## 💬 使用示例

### 私聊

```
你: 你好
智乃: 你好呀！我是智乃~

你: 现在几点了？
智乃: 现在是 2026年01月18日 15:45:00，星期日

你: 我叫小明
智乃: 你好小明！很高兴认识你~
```

### 群聊

```
你: @智乃 你好
智乃: 你好呀！我是智乃~

你: @智乃 现在几点了？
智乃: 现在是 2026年01月18日 15:45:00，星期日
```

---

## 🧠 功能特性

### 1. 智能对话
- 基于 LangChain Agent
- 自动工具选择
- 多步推理

### 2. 长期记忆
- 自动保存对话历史
- 跨会话记忆
- 语义检索

### 3. 工具调用
- 获取时间
- 查询天气（伪代码）
- 情感系统（伪代码）
- 发送邮件（伪代码）

---

## 📊 架构说明

### 消息流程

```
QQ 消息
  ↓
go-cqhttp
  ↓
NoneBot (bot.py)
  ↓
chat_plugin.py
  ↓
Butler.process()
  ↓
LangChain Agent
  ↓
工具调用 + 长期记忆
  ↓
生成回复
  ↓
返回 QQ
```

### 关键组件

1. **bot.py**: NoneBot 主程序
   - 初始化 NoneBot
   - 注册 OneBot 适配器
   - 加载插件

2. **chat_plugin.py**: 聊天插件
   - 启动时初始化 Butler
   - 处理 QQ 消息
   - 调用 Butler 生成回复
   - 发送回复到 QQ

3. **Butler**: 智能管家核心
   - LangChain Agent
   - 工具管理
   - 长期记忆

---

## 🔧 配置说明

### .env 配置

```bash
# NoneBot 配置
HOST=127.0.0.1
PORT=8081                    # 端口（避免与 new-bot 冲突）
LOG_LEVEL=INFO
SUPERUSERS=["1143242311"]    # 超级用户

# DeepSeek API
DEEPSEEK_API_KEY=sk-xxx      # API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# QQ 邮箱（用于邮件工具）
QQ_EMAIL_SENDER=xxx@qq.com
QQ_EMAIL_PASSWORD=xxx
```

### 插件配置

**chat_plugin.py** 中的关键配置：

```python
# Butler 配置
butler = Butler(
    llm=llm,
    tools=tools,
    verbose=True,              # 显示详细日志
    use_vector_store=True,     # 启用长期记忆
    embedding_type="fake"      # 使用 FakeEmbeddings
)

# 消息处理规则
chat = on_message(
    rule=to_me(),              # 只响应 @机器人 或私聊
    priority=10,               # 优先级
    block=True                 # 阻断后续处理
)
```

---

## 📝 日志查看

### 实时查看日志

```bash
tail -f logs/bot.log
```

### 日志内容

```
============================================================
🧠 初始化 Butler Agent...
============================================================
✅ DeepSeek LLM 初始化成功
✅ 已加载 5 个工具
📦 加载 Embeddings 模型 (fake)...
✅ Embeddings 模型加载成功
🗄️ 初始化 Chroma 向量数据库...
✅ Chroma 初始化成功
✅ Butler 初始化成功！
============================================================

============================================================
📨 收到消息 [私聊]
   用户: 1143242311
   内容: 你好
============================================================

📚 检索到相关历史记忆:
[历史对话 1]
...

🤖 Agent 推理过程:
...

✅ 回复成功: 你好呀！我是智乃~...
```

---

## 🛠️ 管理命令

### 启动机器人

```bash
./start_bot.sh
```

### 停止机器人

```bash
./stop_bot.sh
```

### 查看状态

```bash
# 检查进程
ps aux | grep bot.py

# 检查端口
lsof -i :8081
```

### 重启机器人

```bash
./stop_bot.sh && ./start_bot.sh
```

---

## 🐛 故障排查

### 1. 机器人无响应

**检查**:
- NoneBot 是否启动：`ps aux | grep bot.py`
- 端口是否监听：`lsof -i :8081`
- go-cqhttp 是否连接：查看日志

**解决**:
```bash
# 查看日志
tail -f logs/bot.log

# 重启机器人
./stop_bot.sh && ./start_bot.sh
```

### 2. Butler 初始化失败

**检查**:
- `.env` 文件是否存在
- `DEEPSEEK_API_KEY` 是否正确
- 依赖是否安装完整

**解决**:
```bash
# 检查环境变量
cat .env

# 重新安装依赖
pip install -r requirements.txt
```

### 3. 长期记忆错误

**检查**:
- `data/chroma` 目录是否可写
- Embeddings 是否初始化成功

**解决**:
```bash
# 清空长期记忆
rm -rf data/chroma

# 重启机器人
./stop_bot.sh && ./start_bot.sh
```

---

## 🎯 下一步

### 短期（1-2 天）

1. **测试和优化**
   - 在 QQ 上实际使用
   - 收集问题和反馈
   - 优化回复质量

2. **完善工具**
   - 实现真实的天气 API
   - 实现真实的邮件功能
   - 实现真实的情感系统

### 中期（3-5 天）

1. **添加更多功能**
   - 图片识别
   - 语音合成
   - 搜索功能

2. **优化长期记忆**
   - 使用 OpenAI Embeddings
   - 或修复 sentence-transformers

### 长期（1-2 周）

1. **生产环境部署**
   - 错误处理完善
   - 日志系统优化
   - 性能监控

2. **高级功能**
   - LangSmith 集成
   - 多 Agent 协作
   - 工作流系统

---

## 📚 相关文档

- `README.md` - 项目介绍
- `QUICKSTART.md` - 快速开始
- `已完成功能.md` - 已完成功能
- `下一步计划.md` - 后续计划
- `长期记忆实现总结.md` - 长期记忆说明

---

## 🎉 总结

✅ **NoneBot 集成完成！**

现在你可以：
1. 启动机器人：`./start_bot.sh`
2. 在 QQ 上测试
3. 查看日志：`tail -f logs/bot.log`
4. 停止机器人：`./stop_bot.sh`

**核心特性**:
- ✅ 智能对话（LangChain Agent）
- ✅ 长期记忆（VectorStore）
- ✅ 工具调用（5 个基础工具）
- ✅ QQ 集成（NoneBot）

**准备好了吗？开始使用吧！** 🚀
