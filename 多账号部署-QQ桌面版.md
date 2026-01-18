# 多账号部署方案 - QQ 桌面应用版

## 当前架构说明

你现在使用的是：
- **QQ 桌面应用** (`/Applications/QQ.app`)
- **OneBot 协议** 连接到 NoneBot
- **单个 QQ 账号** (2509109290)

## 多账号部署方案

### 方案 1：多个 NoneBot 实例 + 单个 QQ（推荐）⭐⭐⭐⭐⭐

**适用场景**：一个 QQ 号管理多个群/好友

```
┌─────────────────┐
│   QQ 桌面应用    │
│  (2509109290)   │
│   Port: 8080    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│Bot1  │  │Bot2  │
│群A   │  │群B   │
└──────┘  └──────┘
```

**优点**：
- 不需要多个 QQ 账号
- 配置简单
- 资源占用少

**缺点**：
- 所有群/好友共享一个 QQ 号
- 无法实现真正的多账号隔离

### 方案 2：Docker 多容器（适合 3+ 账号）⭐⭐⭐⭐

每个容器运行一个完整的 QQ + NoneBot

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Container 1 │  │  Container 2 │  │  Container 3 │
│  QQ: 250xxx  │  │  QQ: 345xxx  │  │  QQ: 789xxx  │
│  Port: 8080  │  │  Port: 8081  │  │  Port: 8082  │
└──────────────┘  └──────────────┘  └──────────────┘
```

**优点**：
- 完全隔离
- 易于管理
- 可扩展

**缺点**：
- 需要 Docker
- 配置稍复杂

### 方案 3：多台机器（适合大规模）⭐⭐⭐

每台机器运行一个 QQ + NoneBot

## 推荐实现：方案 1（单 QQ 多 Bot）

### 步骤 1：修改当前架构

当前你的 QQ 已经在 8080 端口监听，我们可以让多个 NoneBot 实例连接到同一个 QQ。

### 步骤 2：创建多个 Bot 配置

```bash
# 创建 Bot 配置目录
mkdir -p bots/bot1 bots/bot2

# Bot1 配置（处理群 A）
cat > bots/bot1/.env << EOF
BOT_ID=bot1
HOST=127.0.0.1
PORT=8080
GROUP_FILTER=["704917458"]  # 只处理这个群
EOF

# Bot2 配置（处理群 B）
cat > bots/bot2/.env << EOF
BOT_ID=bot2
HOST=127.0.0.1
PORT=8080
GROUP_FILTER=["123456789"]  # 只处理这个群
EOF
```

### 步骤 3：修改插件支持群过滤

需要在 `chat_plugin.py` 中添加群过滤逻辑。

## 如果你想要真正的多 QQ 账号

### 选项 A：使用 NapCat（推荐）

1. **安装 NapCat**
```bash
# macOS 安装
brew install napcat

# 或者使用 npm
npm install -g napcat
```

2. **配置多个 NapCat 实例**
```bash
# 启动 NapCat 1 (QQ: 2509109290)
napcat --port 3000 --qq 2509109290

# 启动 NapCat 2 (QQ: 3456789012)
napcat --port 3001 --qq 3456789012
```

3. **配置 NoneBot 连接**
```env
# Bot1 连接到 NapCat 1
ONEBOT_WS_URL=ws://127.0.0.1:3000

# Bot2 连接到 NapCat 2
ONEBOT_WS_URL=ws://127.0.0.1:3001
```

### 选项 B：使用 Docker

我可以为你创建一个 Docker Compose 配置，一键启动多个 QQ + NoneBot。

## 你的选择

请告诉我你想要哪种方案：

1. **方案 1**：继续用当前的 QQ 桌面应用，多个 Bot 实例处理不同的群
2. **方案 2**：安装 NapCat，实现真正的多 QQ 账号
3. **方案 3**：使用 Docker，完全容器化部署

我会根据你的选择提供详细的实现步骤！

## 当前状态检查

让我帮你检查一下当前的配置：

```bash
# 查看 QQ 进程
ps aux | grep QQ.app

# 查看 NoneBot 进程
ps aux | grep bot.py

# 查看端口占用
lsof -i :8080
```

你的 QQ 现在应该是通过某种方式（可能是 go-cqhttp 或其他 OneBot 实现）连接到 NoneBot 的。

需要我帮你检查具体的连接方式吗？
