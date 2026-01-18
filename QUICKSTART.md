# 快速开始

## 🚀 5 分钟上手

### 1. 安装依赖

```bash
# 使用 pip
pip install langchain langchain-openai langchain-core python-dotenv

# 或使用 poetry（推荐）
poetry install
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# 方式 1: 使用 OpenAI
OPENAI_API_KEY=sk-xxx

# 方式 2: 使用 DeepSeek
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 方式 3: 使用通义千问（需要额外安装 langchain-dashscope）
# DASHSCOPE_API_KEY=sk-xxx
```

### 3. 运行测试

```bash
# 方式 1: 自动测试（推荐先运行这个）
python test_butler.py

# 方式 2: 交互式聊天
python chat.py
```

---

## 📝 测试示例

### 自动测试（test_butler.py）

运行后会自动测试以下场景：

1. **简单问候**: "你好！"
2. **查询时间**: "现在几点了？"
3. **查询天气**: "北京的天气怎么样？"
4. **复杂任务**: "查一下上海明天的天气，如果下雨就发邮件提醒我"
5. **情感互动**: "我对你的印象很好！"

### 交互式聊天（chat.py）

运行后可以自由对话：

```
👤 你: 你好
🤖 智乃: 你好呀！我是智乃，很高兴见到你~

👤 你: 现在几点了？
🤖 智乃: 现在是 2025年01月18日 14:30:00，星期六

👤 你: 北京的天气怎么样？
🤖 智乃: 北京今天的天气：晴，温度 5-15°C

👤 你: 查一下广州明天的天气，如果下雨就发邮件提醒我
🤖 智乃: 广州明天有雨，温度 18-25°C，我已经发邮件提醒你了~
```

---

## 🔧 当前功能

### 已实现的工具（伪代码）

1. **get_time**: 获取当前时间
2. **get_weather**: 查询天气（伪数据）
3. **get_emotion**: 获取用户情感值（伪数据）
4. **update_emotion**: 更新情感值（伪数据）
5. **send_email**: 发送邮件（伪代码）

### LangChain 功能

- ✅ **Agent**: ReAct 推理（自动思考和工具调用）
- ✅ **Memory**: 对话历史管理
- ✅ **Tools**: 标准化工具接口
- ⏳ **VectorStore**: 长期记忆（待实现）
- ⏳ **LangSmith**: 追踪调试（待配置）

---

## 🎯 测试重点

### 1. Agent 推理能力

测试 Agent 是否能自动推理和选择工具：

```
用户: "查北京天气，如果下雨就发邮件"

Agent 推理过程:
Thought: 需要先查天气
Action: get_weather
Observation: 晴天

Thought: 天气是晴天，不需要发邮件
Final Answer: 北京今天是晴天，不用担心下雨~
```

### 2. 工具调用

测试工具是否正确调用：

```
用户: "现在几点了？"
→ 调用 get_time 工具
→ 返回当前时间
```

### 3. 记忆功能

测试对话记忆：

```
用户: "我叫小明"
智乃: "你好小明！"

用户: "我叫什么名字？"
智乃: "你叫小明！"  ← 从 Memory 中检索
```

---

## 🐛 常见问题

### Q1: 提示 "No module named 'langchain'"

**A**: 需要安装依赖
```bash
pip install langchain langchain-openai langchain-core python-dotenv
```

### Q2: 提示 "API Key not found"

**A**: 需要配置 .env 文件
```bash
cp .env.example .env
# 编辑 .env，填入 API Key
```

### Q3: Agent 不调用工具

**A**: 可能是 Prompt 问题，或者 LLM 理解有误。可以：
1. 检查工具的 description 是否清晰
2. 尝试更明确的用户输入
3. 查看详细日志（verbose=True）

### Q4: 工具调用失败

**A**: 当前是伪代码版本，工具返回的是假数据。实际实现需要：
1. 天气工具：调用天气 API
2. 邮件工具：配置 SMTP
3. 情感工具：连接数据库

---

## 📚 下一步

1. ✅ **当前**: 基础 Agent + 伪代码工具
2. ⏳ **下一步**: 实现真实工具（天气 API、邮件 SMTP）
3. ⏳ **然后**: 集成 VectorStore（长期记忆）
4. ⏳ **最后**: 集成 NoneBot（QQ 机器人）

---

## 🎉 开始测试吧！

```bash
# 先运行自动测试，看看效果
python test_butler.py

# 然后试试交互式聊天
python chat.py
```

有问题随时问我！🚀
