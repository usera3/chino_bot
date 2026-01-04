#!/bin/bash
# 新机器人状态检查脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo -e "${GREEN}=== 新机器人状态 ===${NC}"

# 检查PID文件
if [ ! -f "new-bot.pid" ]; then
    echo -e "${RED}状态: 未运行${NC}"
    exit 1
fi

# 读取PID
PID=$(cat new-bot.pid)

# 检查进程是否存在
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}状态: 运行中${NC}"
    echo -e "PID: $PID"
    echo -e "内存使用: $(ps -o rss= -p $PID | awk '{print $1/1024 " MB"}')"
    echo -e "运行时间: $(ps -o etime= -p $PID)"
    
    # 检查日志文件
    if [ -f "logs/bot.log" ]; then
        echo ""
        echo -e "${YELLOW}最近日志:${NC}"
        tail -n 10 logs/bot.log
    fi
else
    echo -e "${RED}状态: 未运行 (PID文件存在但进程不存在)${NC}"
    rm -f new-bot.pid
    exit 1
fi




