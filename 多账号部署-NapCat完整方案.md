# 多账号部署方案 - NapCat Shell 完整指南

## 📋 当前架构分析

### 现有配置
你当前使用的是 **NapCat Shell** 模式：
- **NapCat 版本**: 4.8.122
- **集成方式**: NapCat 作为 QQ.app 的 Shell 插件运行
- **配置目录**: `~/Library/Containers/com.tencent.qq/Data/Library/Application Support/QQ/NapCat/`
- **连接方式**: WebSocket 反向连接 (ws://127.0.0.1:8080/onebot/v11/)
- **当前账号**: 1000000000

### 架构图
```
┌─────────────────────────────────────────┐
│         QQ.app (macOS)                  │
│  ┌───────────────────────────────────┐  │
│  │   NapCat Shell (插件模式)         │  │
│  │   - 账号: 1000000000              │  │
│  │   - WebUI: http://127.0.0.1:6099  │  │
│  │   - 反向WS: ws://127.0.0.1:8080   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    ↓ (WebSocket)
┌─────────────────────────────────────────┐
│   NoneBot2 (zhinai-bot-v3)              │
│   - 端口: 8080                          │
│   - 路径: /onebot/v11/                  │
└─────────────────────────────────────────┘
```

## 🎯 多账号部署方案

### 方案一：多 QQ 实例 + 多 NoneBot 实例（推荐）

每个 QQ 账号独立运行，每个 Bot 独立端口。

#### 架构设计
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  QQ.app #1   │  │  QQ.app #2   │  │  QQ.app #3   │
│  NapCat      │  │  NapCat      │  │  NapCat      │
│  2509xxx     │  │  3456xxx     │  │  7890xxx     │
│  WS反向连接  │  │  WS反向连接  │  │  WS反向连接  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ↓                 ↓                 ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  NoneBot #1  │  │  NoneBot #2  │  │  NoneBot #3  │
│  Port: 8080  │  │  Port: 8081  │  │  Port: 8082  │
└──────────────┘  └──────────────┘  └──────────────┘
       │                 │                 │
       └─────────────────┴─────────────────┘
                         ↓
              ┌──────────────────┐
              │  共享 SQLite DB   │
              │  (user_id 隔离)  │
              └──────────────────┘
```

#### 实施步骤

##### 1. 准备多个 QQ 账号
由于 macOS 的 QQ.app 一次只能登录一个账号，你需要：

**选项 A: 使用多个 macOS 用户（推荐）**
```bash
# 为每个 QQ 账号创建独立的 macOS 用户
# 每个用户运行独立的 QQ.app + NapCat
```

**选项 B: 使用 Docker 容器（推荐）**
```bash
# 使用 NapCat Docker 版本，可以在同一台机器运行多个实例
# 参考: https://github.com/NapNeko/NapCatQQ
```

**选项 C: 使用多台机器/虚拟机**
```bash
# 每台机器运行一个 QQ 账号
# 所有 Bot 连接到同一个数据库
```

##### 2. 配置多个 NoneBot 实例

创建 Bot 配置目录结构：
```bash
cd zhinai-bot-v3

# 创建多 Bot 配置目录
mkdir -p bots/bot1 bots/bot2 bots/bot3
```

为每个 Bot 创建独立的 `.env` 文件：

**bots/bot1/.env** (现有账号 1000000000)
```env
# NoneBot 配置
HOST=127.0.0.1
PORT=8080
LOG_LEVEL=INFO
SUPERUSERS=["123456789"]
NICKNAME=["智乃", "chino"]
COMMAND_START=["/", ""]
COMMAND_SEP=["."]

# OneBot 配置
ONEBOT_ACCESS_TOKEN=""

# Bot 标识
BOT_NAME=bot1
BOT_QQ=1000000000

# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# QQ 邮箱 SMTP 配置
QQ_EMAIL_SENDER=1000000000@qq.com
QQ_EMAIL_PASSWORD=your_qq_smtp_authorization_code

# 其他 API
TAVILY_API_KEY=tvly-your-tavily-api-key
AMAP_API_KEY=amap-your-api-key
DASHSCOPE_API_KEY=sk-your-dashscope-api-key
```

**bots/bot2/.env** (新账号)
```env
HOST=127.0.0.1
PORT=8081
LOG_LEVEL=INFO
SUPERUSERS=["123456789"]
NICKNAME=["智乃2", "chino2"]
COMMAND_START=["/", ""]
COMMAND_SEP=["."]

ONEBOT_ACCESS_TOKEN=""

BOT_NAME=bot2
BOT_QQ=3456789012

# 使用相同的 API 配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

QQ_EMAIL_SENDER=3456789012@qq.com
QQ_EMAIL_PASSWORD=your_qq_smtp_authorization_code

TAVILY_API_KEY=tvly-your-tavily-api-key
AMAP_API_KEY=amap-your-api-key
DASHSCOPE_API_KEY=sk-your-dashscope-api-key
```

**bots/bot3/.env** (新账号)
```env
HOST=127.0.0.1
PORT=8082
# ... 类似配置
BOT_NAME=bot3
BOT_QQ=7890123456
```

##### 3. 配置 NapCat 反向连接

对于每个 QQ 账号，需要配置 NapCat 的 OneBot11 配置文件。

**账号 1 (1000000000) - 已配置**
配置文件位置: `~/Library/Containers/com.tencent.qq/Data/Library/Application Support/QQ/NapCat/config/onebot11_1000000000.json`

当前配置（已正确）：
```json
{
  "network": {
    "websocketClients": [
      {
        "enable": true,
        "name": "nonebot2",
        "url": "ws://127.0.0.1:8080/onebot/v11/",
        "reportSelfMessage": false,
        "messagePostFormat": "array",
        "token": "abc123456",
        "debug": true,
        "heartInterval": 30000,
        "reconnectInterval": 1000
      }
    ]
  }
}
```

**账号 2 (3456789012) - 新配置**
如果使用不同的 macOS 用户或机器，配置文件路径相同，但修改连接端口：
```json
{
  "network": {
    "websocketClients": [
      {
        "enable": true,
        "name": "nonebot2",
        "url": "ws://127.0.0.1:8081/onebot/v11/",  // 注意端口改为 8081
        "reportSelfMessage": false,
        "messagePostFormat": "array",
        "token": "abc123456",
        "debug": true,
        "heartInterval": 30000,
        "reconnectInterval": 1000
      }
    ]
  }
}
```

**账号 3 (7890123456) - 新配置**
```json
{
  "network": {
    "websocketClients": [
      {
        "enable": true,
        "name": "nonebot2",
        "url": "ws://127.0.0.1:8082/onebot/v11/",  // 端口 8082
        "reportSelfMessage": false,
        "messagePostFormat": "array",
        "token": "abc123456",
        "debug": true,
        "heartInterval": 30000,
        "reconnectInterval": 1000
      }
    ]
  }
}
```

##### 4. 创建启动脚本

**start_multi_bots.sh**
```bash
#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/path/to/chino_bot"
BOT_BASE_DIR="${PROJECT_DIR}/zhinai-bot-v3"
VENV_DIR="${PROJECT_DIR}/.venv"
LOG_DIR="${PROJECT_DIR}/logs"
PYTHON_BIN="${VENV_DIR}/bin/python"

mkdir -p "${LOG_DIR}"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   启动多账号机器人系统${NC}"
echo -e "${GREEN}================================${NC}"

# Bot 配置数组 (bot_name:port:qq_number)
declare -A BOTS=(
    ["bot1"]="8080:1000000000"
    ["bot2"]="8081:3456789012"
    ["bot3"]="8082:7890123456"
)

# 启动每个 Bot
for bot_name in "${!BOTS[@]}"; do
    IFS=':' read -r port qq <<< "${BOTS[$bot_name]}"
    
    echo -e "${GREEN}启动 ${bot_name} (QQ:${qq}, Port:${port})...${NC}"
    
    # 检查配置文件
    if [ ! -f "${BOT_BASE_DIR}/bots/${bot_name}/.env" ]; then
        echo -e "${YELLOW}⚠️  ${bot_name} 配置文件不存在，跳过${NC}"
        continue
    fi
    
    # 复制配置文件到主目录
    cp "${BOT_BASE_DIR}/bots/${bot_name}/.env" "${BOT_BASE_DIR}/.env.${bot_name}"
    
    # 启动 NoneBot
    cd "${BOT_BASE_DIR}"
    nohup arch -arm64 caffeinate -i "${PYTHON_BIN}" bot.py \
        --env-file ".env.${bot_name}" \
        > "${LOG_DIR}/${bot_name}.log" 2>&1 &
    
    BOT_PID=$!
    echo "BOT_${bot_name}_PID=${BOT_PID}" >> "${PROJECT_DIR}/.bot_pids"
    
    echo -e "${GREEN}✓ ${bot_name} 启动成功 (PID: ${BOT_PID})${NC}"
    sleep 2
done

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   所有 Bot 启动完成${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "📝 查看日志："
echo -e "   ${YELLOW}tail -f ${LOG_DIR}/bot1.log${NC}"
echo -e "   ${YELLOW}tail -f ${LOG_DIR}/bot2.log${NC}"
echo -e "   ${YELLOW}tail -f ${LOG_DIR}/bot3.log${NC}"
echo ""
echo -e "🛑 停止所有 Bot："
echo -e "   ${YELLOW}bash stop_multi_bots.sh${NC}"
echo ""
```

**stop_multi_bots.sh**
```bash
#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PROJECT_DIR="/path/to/chino_bot"
PID_FILE="${PROJECT_DIR}/.bot_pids"

echo -e "${GREEN}停止所有机器人...${NC}"

if [ -f "${PID_FILE}" ]; then
    while IFS='=' read -r key value; do
        if [[ $key == BOT_* ]]; then
            if ps -p $value > /dev/null 2>&1; then
                kill $value
                echo -e "${GREEN}✓ 已停止 $key (PID: $value)${NC}"
            fi
        fi
    done < "${PID_FILE}"
    
    rm "${PID_FILE}"
    echo -e "${GREEN}所有 Bot 已停止${NC}"
else
    echo -e "${RED}未找到运行中的 Bot${NC}"
fi
```

**status_multi_bots.sh**
```bash
#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="/path/to/chino_bot"
PID_FILE="${PROJECT_DIR}/.bot_pids"

echo "多账号机器人状态："
echo "================================"

if [ -f "${PID_FILE}" ]; then
    while IFS='=' read -r key value; do
        if [[ $key == BOT_* ]]; then
            if ps -p $value > /dev/null 2>&1; then
                echo -e "${GREEN}✓ $key (PID: $value) - 运行中${NC}"
            else
                echo -e "${RED}✗ $key (PID: $value) - 已停止${NC}"
            fi
        fi
    done < "${PID_FILE}"
else
    echo "没有运行中的 Bot"
fi

echo ""
echo "端口监听状态："
for port in 8080 8081 8082; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 端口 $port - 监听中${NC}"
    else
        echo -e "${RED}✗ 端口 $port - 未监听${NC}"
    fi
done
```

##### 5. 数据库隔离

当前使用的 SQLite 数据库已经通过 `user_id` 字段实现了数据隔离，无需额外配置。

检查数据库表结构：
```sql
-- conversations 表
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,  -- QQ 号，自动隔离
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- knowledge 表
CREATE TABLE knowledge (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,  -- QQ 号，自动隔离
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

所有 Bot 共享同一个数据库文件，但通过 `user_id` 自动隔离数据。

## 🚀 启动流程

### 单机多用户方案（推荐用于测试）

1. **启动主账号 (1000000000)**
```bash
# 当前用户
cd /path/to/chino_bot
bash zhinai-bot-v3/start_bot.sh
```

2. **启动其他账号（需要其他 macOS 用户或机器）**
```bash
# 在其他用户/机器上
cd /path/to/project
bash zhinai-bot-v3/start_bot.sh
```

### Docker 方案（推荐用于生产）

使用 NapCat Docker 版本可以在同一台机器运行多个 QQ 实例：

```bash
# Bot 1
docker run -d --name napcat-bot1 \
  -p 8080:8080 \
  -e QQ_ACCOUNT=1000000000 \
  napneko/napcat:latest

# Bot 2
docker run -d --name napcat-bot2 \
  -p 8081:8081 \
  -e QQ_ACCOUNT=3456789012 \
  napneko/napcat:latest

# Bot 3
docker run -d --name napcat-bot3 \
  -p 8082:8082 \
  -e QQ_ACCOUNT=7890123456 \
  napneko/napcat:latest

# 启动所有 NoneBot 实例
bash start_multi_bots.sh
```

## 📊 监控和管理

### 查看 NapCat WebUI
每个 NapCat 实例都有独立的 WebUI：
- Bot1: http://127.0.0.1:6099/webui?token=your-napcat-webui-token
- Bot2: http://127.0.0.1:6100/webui?token=xxx (需要配置不同端口)
- Bot3: http://127.0.0.1:6101/webui?token=xxx

### 查看日志
```bash
# 实时查看所有 Bot 日志
tail -f logs/bot1.log logs/bot2.log logs/bot3.log

# 查看 NapCat 日志
tail -f logs/qq.log
```

### 查看状态
```bash
bash status_multi_bots.sh
```

## ⚠️ 注意事项

1. **macOS QQ.app 限制**
   - 一个 macOS 用户只能登录一个 QQ 账号
   - 需要多个 macOS 用户或使用 Docker

2. **端口分配**
   - 确保每个 Bot 使用不同的端口
   - 检查端口是否被占用：`lsof -ti:8080`

3. **NapCat 配置**
   - 每个 QQ 账号的 NapCat 配置文件独立
   - 配置文件路径：`~/Library/Containers/com.tencent.qq/Data/Library/Application Support/QQ/NapCat/config/onebot11_<QQ号>.json`

4. **数据隔离**
   - 数据库通过 `user_id` 自动隔离
   - 无需担心数据混淆

5. **资源消耗**
   - 每个 QQ + NoneBot 实例约占用 200-300MB 内存
   - 建议至少 2GB 可用内存

## 🔧 故障排查

### Bot 无法连接到 NapCat
```bash
# 检查 NapCat 是否启动
ps aux | grep QQ

# 检查 WebSocket 连接
tail -f logs/qq.log | grep "WebSocket"

# 检查 NoneBot 日志
tail -f logs/bot1.log | grep "WebSocket"
```

### 端口冲突
```bash
# 查看端口占用
lsof -ti:8080
lsof -ti:8081
lsof -ti:8082

# 杀死占用端口的进程
kill $(lsof -ti:8080)
```

### NapCat 配置未生效
```bash
# 重启 QQ.app
killall QQ
open /Applications/QQ.app

# 等待 NapCat 加载
tail -f logs/qq.log
```

## 📚 参考资料

- NapCat 官方文档: https://napneko.github.io/
- NapCat GitHub: https://github.com/NapNeko/NapCatQQ
- NoneBot2 文档: https://nonebot.dev/
- OneBot 标准: https://onebot.dev/

## 🎉 下一步

1. 准备多个 QQ 账号
2. 选择部署方案（多用户/Docker/多机器）
3. 配置 NapCat 和 NoneBot
4. 测试连接和功能
5. 监控运行状态

如有问题，查看日志文件或访问 NapCat WebUI 进行调试。
