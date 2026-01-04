#!/bin/bash
# 新机器人停止脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo -e "${GREEN}=== 新机器人停止脚本 ===${NC}"

# 检查PID文件
if [ ! -f "new-bot.pid" ]; then
    echo -e "${YELLOW}未找到PID文件，机器人可能没有运行${NC}"
    exit 0
fi

# 读取PID
PID=$(cat new-bot.pid)

# 检查进程是否存在
if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}进程不存在 (PID: $PID)${NC}"
    rm -f new-bot.pid
    exit 0
fi

# 停止进程
echo -e "${GREEN}正在停止新机器人 (PID: $PID)...${NC}"
kill $PID

# 等待进程结束
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}新机器人已停止${NC}"
        rm -f new-bot.pid
        exit 0
    fi
    sleep 1
done

# 如果还没停止，强制结束
echo -e "${YELLOW}进程未响应，强制结束...${NC}"
kill -9 $PID
rm -f new-bot.pid
echo -e "${GREEN}新机器人已强制停止${NC}"




