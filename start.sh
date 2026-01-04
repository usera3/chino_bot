#!/bin/bash
# 新机器人启动脚本
# 使用旧机器人的虚拟环境

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 虚拟环境路径（使用旧机器人的）
VENV_PATH="/Users/mozi100/PycharmProjects/chino_bot/.venv"

echo -e "${GREEN}=== 新机器人启动脚本 ===${NC}"

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}错误: 虚拟环境不存在: $VENV_PATH${NC}"
    exit 1
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: .env 文件不存在，从模板复制...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}已创建 .env 文件，请编辑配置后重新启动${NC}"
        exit 0
    else
        echo -e "${RED}错误: .env.example 也不存在${NC}"
        exit 1
    fi
fi

# 创建日志目录
mkdir -p logs

# 检查是否已经在运行
if [ -f "new-bot.pid" ]; then
    PID=$(cat new-bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${YELLOW}新机器人已经在运行 (PID: $PID)${NC}"
        exit 0
    else
        echo -e "${YELLOW}清理过期的PID文件${NC}"
        rm -f new-bot.pid
    fi
fi

# 激活虚拟环境并启动
echo -e "${GREEN}使用虚拟环境: $VENV_PATH${NC}"
echo -e "${GREEN}正在启动新机器人...${NC}"

# 启动机器人（后台运行）
source "$VENV_PATH/bin/activate"
nohup python3 bot.py > logs/bot.log 2>&1 &
BOT_PID=$!

# 保存PID
echo $BOT_PID > new-bot.pid

echo -e "${GREEN}新机器人已启动 (PID: $BOT_PID)${NC}"
echo -e "${GREEN}日志文件: $SCRIPT_DIR/logs/bot.log${NC}"
echo ""
echo -e "${YELLOW}提示:${NC}"
echo "  - 查看日志: tail -f logs/bot.log"
echo "  - 停止机器人: ./stop.sh"
echo "  - 查看状态: ./status.sh"




