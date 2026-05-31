#!/bin/bash

# 多 QQ 账号启动脚本
# 使用方法: bash start_multi_bots.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "   多账号机器人启动脚本"
echo "================================"

# 检查 bots 目录
if [ ! -d "bots" ]; then
    echo -e "${YELLOW}⚠️  bots 目录不存在，正在创建...${NC}"
    mkdir -p bots
    echo -e "${GREEN}✓ bots 目录已创建${NC}"
    echo ""
    echo "请按以下步骤配置："
    echo "1. 在 bots/ 目录下创建子目录（如 bot1, bot2）"
    echo "2. 在每个子目录中创建 .env 文件"
    echo "3. 配置不同的端口和 QQ 号"
    echo ""
    echo "示例："
    echo "  bots/bot1/.env  -> PORT=8080, BOT_QQ=1000000000"
    echo "  bots/bot2/.env  -> PORT=8081, BOT_QQ=3456789012"
    exit 0
fi

# 扫描所有 bot 配置
BOT_DIRS=($(find bots -maxdepth 1 -mindepth 1 -type d | sort))

if [ ${#BOT_DIRS[@]} -eq 0 ]; then
    echo -e "${RED}❌ 未找到任何 Bot 配置${NC}"
    echo "请在 bots/ 目录下创建 Bot 配置目录"
    exit 1
fi

echo "发现 ${#BOT_DIRS[@]} 个 Bot 配置："
for bot_dir in "${BOT_DIRS[@]}"; do
    bot_name=$(basename "$bot_dir")
    if [ -f "$bot_dir/.env" ]; then
        port=$(grep "^PORT=" "$bot_dir/.env" | cut -d'=' -f2)
        qq=$(grep "^BOT_QQ=" "$bot_dir/.env" | cut -d'=' -f2)
        echo "  - $bot_name (QQ:$qq, Port:$port)"
    else
        echo -e "  - $bot_name ${YELLOW}(缺少 .env 文件)${NC}"
    fi
done
echo ""

# 创建必要的目录
mkdir -p logs
mkdir -p data
mkdir -p pids

# 启动所有 Bot
for bot_dir in "${BOT_DIRS[@]}"; do
    bot_name=$(basename "$bot_dir")
    
    if [ ! -f "$bot_dir/.env" ]; then
        echo -e "${YELLOW}⚠️  跳过 $bot_name (缺少 .env 文件)${NC}"
        continue
    fi
    
    # 读取配置
    source "$bot_dir/.env"
    PORT=${PORT:-8080}
    BOT_QQ=${BOT_QQ:-unknown}
    NAPCAT_PORT=${NAPCAT_PORT:-3000}
    
    echo "================================"
    echo "启动 $bot_name"
    echo "================================"
    echo "QQ 号: $BOT_QQ"
    echo "NoneBot 端口: $PORT"
    echo "NapCat 端口: $NAPCAT_PORT"
    
    # 检查端口是否被占用
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $PORT 已被占用，跳过${NC}"
        continue
    fi
    
    # 启动 NoneBot
    echo "[1/2] 启动 NoneBot..."
    cd "$bot_dir"
    nohup python ../../bot.py > ../../logs/${bot_name}.log 2>&1 &
    NONEBOT_PID=$!
    echo $NONEBOT_PID > ../../pids/${bot_name}_nonebot.pid
    cd ../..
    
    # 等待启动
    sleep 2
    
    if ps -p $NONEBOT_PID > /dev/null; then
        echo -e "${GREEN}✓ NoneBot 启动成功 (PID: $NONEBOT_PID)${NC}"
    else
        echo -e "${RED}✗ NoneBot 启动失败${NC}"
        continue
    fi
    
    # 启动 NapCat (如果需要)
    if command -v napcat &> /dev/null; then
        echo "[2/2] 启动 NapCat..."
        nohup napcat --port $NAPCAT_PORT > logs/${bot_name}_napcat.log 2>&1 &
        NAPCAT_PID=$!
        echo $NAPCAT_PID > pids/${bot_name}_napcat.pid
        echo -e "${GREEN}✓ NapCat 启动成功 (PID: $NAPCAT_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  NapCat 未安装，跳过${NC}"
    fi
    
    echo ""
done

echo "================================"
echo "   启动完成！"
echo "================================"
echo ""
echo "📊 查看状态: bash status_multi_bots.sh"
echo "📝 查看日志: tail -f logs/bot1.log"
echo "🛑 停止所有: bash stop_multi_bots.sh"
echo ""
