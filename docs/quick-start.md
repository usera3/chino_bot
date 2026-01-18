# zhinai-bot-v3 快速开始指南

## 🎯 5 分钟上手

本指南将帮助你在 5 分钟内启动 zhinai-bot-v3 并进行第一次对话。

---

## 📋 前置条件

### 必需
- Python 3.10 或更高版本
- Poetry 1.5 或更高版本
- QQ 账号（用于机器人）

### 可选
- DashScope API Key（通义千问）
- DeepSeek API Key（备用 LLM）
- LangSmith API Key（可观测性）

---

## 🚀 安装步骤

### 1. 克隆项目

```bash
git clone <repo-url>
cd zhinai-bot-v3
```

### 2. 安装依赖

```bash
# 使用 Poetry 安装
poetry install

# 或使用 pip
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用你喜欢的编辑器
```

`.env` 文件示例：
```bash
# QQ 机器人配置
QQ_ACCOUNT=123456789
QQ_PASSWORD=your_password

# LLM 配置（至少配置一个）
DASHSCOPE_API_KEY=sk-xxx  # 通义千问
DEEPSEEK_API_KEY=sk-xxx   # DeepSeek（可选）

# LangSmith 配置（可选，用于调试）
LANGCHAIN_API_KEY=lsv2_xxx
LANGCHAIN_PROJECT=zhinai-bot-v3
LANGCHAIN_TRACING_V2=true

# 数据库配置（默认即可）
DATABASE_URL=sqlite:///data/bot.db
VECTOR_DB_PATH=data/vector_db
```

### 4. 初始化数据库

```bash
python scripts/init_db.py
```

### 5. 启动机器人

```bash
python bot.py
```

看到以下输出表示启动成功：
```
[INFO] NoneBot2 启动成功
[INFO] 已加载 5 个工具
[INFO] Agent 初始化完成
[INFO] 机器人已上线，开始监听消息...
```

---

## 💬 第一次对话

### 在 QQ 中测试

1. 添加机器人 QQ 为好友
2. 发送消息: `你好`
3. 机器人应该会回复: `你好！我是智乃，有什么可以帮你的吗？`

### 测试工具调用

```
你: 现在几点了？
机器人: 现在是 2025年1月18日 14:30:00

你: 北京的天气怎么样？
机器人: 北京今天晴，温度 5-15°C，空气质量良好
```

---

## 🛠️ 常见问题

### Q1: 启动失败，提示 "No module named 'xxx'"
**A**: 依赖未安装完整，重新运行 `poetry install`

### Q2: 机器人不回复消息
**A**: 检查以下几点：
1. QQ 账号是否正确登录
2. 是否添加了机器人为好友
3. 查看日志 `logs/bot.log` 是否有错误

### Q3: 工具调用失败
**A**: 检查 API Key 是否正确配置，查看 LangSmith 追踪详情

### Q4: 响应速度慢
**A**: 
1. 检查网络连接
2. 尝试切换 LLM 提供商
3. 启用缓存（见配置文档）

---

## 📚 下一步

### 学习核心概念
- [架构设计](./架构设计-v3-vs-newbot.md) - 了解双层 Agent 架构
- [工具系统](./tool-development.md) - 学习如何开发新工具
- [工作流](./workflow-guide.md) - 学习如何使用 LangGraph

### 自定义机器人
- 修改角色人设: 编辑 `config/prompts.py`
- 添加新工具: 参考 `tools/` 目录下的示例
- 集成插件: 参考 [插件集成指南](./plugin-integration.md)

### 监控和调试
- 查看日志: `tail -f logs/bot.log`
- LangSmith 面板: https://smith.langchain.com/
- 性能分析: `python scripts/analyze_performance.py`

---

## 🎉 成功！

恭喜！你已经成功启动了 zhinai-bot-v3。现在可以：

1. ✅ 与机器人对话
2. ✅ 测试工具调用
3. ✅ 查看调用链追踪
4. ✅ 开始自定义开发

有问题？查看 [完整文档](./requirements.md) 或提交 [Issue](<repo-url>/issues)。
