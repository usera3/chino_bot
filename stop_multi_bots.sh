#!/bin/bash

# 多 QQ 账号停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
NC='\033[0m'

echo "================================"
echo "   停止所有机器人"
echo "================================"

if [ ! -d "pids" ]; then
    echo "没有运行中的 Bot"
    exit 0
fi

# 停止所有进程
for pid_file in pids/*.pid; do
    if [ -f "$pid_file" ]; then
        bot_name=$(basename "$pid_file" .pid)
        pid=$(cat "$pid_file")
        
        if ps -p $pid > /dev/null 2>&1; then
            echo "正在停止 $bot_name (PID: $pid)..."
            kill $pid 2>/dev/null
            sleep 1
            
            # 强制杀死
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null
            fi
            
            echo -e "${GREEN}✓ $bot_name 已停止${NC}"
        fi
        
        rm "$pid_file"
    fi
done

# 清理残留进程
echo ""
echo "清理残留进程..."
pkill -f "python.*bot.py" 2>/dev/null || true
pkill -f "napcat" 2>/dev/null || true

echo ""
echo "================================"
echo "   所有机器人已停止"
echo "================================"
