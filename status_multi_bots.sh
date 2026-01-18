#!/bin/bash

# 多 QQ 账号状态查看脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================"
echo "   机器人状态"
echo "================================"
echo ""

if [ ! -d "pids" ] || [ -z "$(ls -A pids 2>/dev/null)" ]; then
    echo "没有运行中的 Bot"
    exit 0
fi

# 统计
total=0
running=0

# 检查每个 Bot
for bot_dir in bots/*/; do
    if [ ! -d "$bot_dir" ]; then
        continue
    fi
    
    bot_name=$(basename "$bot_dir")
    total=$((total + 1))
    
    # 读取配置
    if [ -f "$bot_dir/.env" ]; then
        source "$bot_dir/.env"
        PORT=${PORT:-unknown}
        BOT_QQ=${BOT_QQ:-unknown}
    else
        PORT="unknown"
        BOT_QQ="unknown"
    fi
    
    # 检查 NoneBot 状态
    nonebot_pid_file="pids/${bot_name}_nonebot.pid"
    napcat_pid_file="pids/${bot_name}_napcat.pid"
    
    echo "📱 $bot_name (QQ:$BOT_QQ)"
    echo "   端口: $PORT"
    
    # NoneBot 状态
    if [ -f "$nonebot_pid_file" ]; then
        pid=$(cat "$nonebot_pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "   NoneBot: ${GREEN}运行中${NC} (PID: $pid)"
            running=$((running + 1))
        else
            echo -e "   NoneBot: ${RED}已停止${NC}"
        fi
    else
        echo -e "   NoneBot: ${RED}未启动${NC}"
    fi
    
    # NapCat 状态
    if [ -f "$napcat_pid_file" ]; then
        pid=$(cat "$napcat_pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "   NapCat:  ${GREEN}运行中${NC} (PID: $pid)"
        else
            echo -e "   NapCat:  ${RED}已停止${NC}"
        fi
    else
        echo -e "   NapCat:  ${YELLOW}未配置${NC}"
    fi
    
    # 日志文件大小
    if [ -f "logs/${bot_name}.log" ]; then
        log_size=$(du -h "logs/${bot_name}.log" | cut -f1)
        echo "   日志: $log_size"
    fi
    
    echo ""
done

echo "================================"
echo "总计: $total 个 Bot, $running 个运行中"
echo "================================"
