#!/bin/bash

echo "================================"
echo "   停止 Chino Bot"
echo "================================"

PROJECT_DIR="${CHINO_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
PID_FILE="${PROJECT_DIR}/.bot_pids"

# 检查 PID 文件
if [ ! -f "${PID_FILE}" ]; then
    echo "⚠️  未找到运行中的机器人"
    exit 0
fi

# 读取 PID
PID=$(grep "^BOT_PID=" "${PID_FILE}" | cut -d'=' -f2)
if [ -z "${PID}" ]; then
    echo "⚠️  PID 文件中未找到 BOT_PID"
    exit 0
fi

# 检查进程是否存在
if ! ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  进程不存在 (PID: $PID)"
    rm "${PID_FILE}"
    exit 0
fi

# 停止进程
echo "正在停止 NoneBot (PID: $PID)..."
kill $PID

# 等待进程结束
sleep 2

# 检查是否成功停止
if ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  进程未响应，强制停止..."
    kill -9 $PID
    sleep 1
fi

# 删除 PID 文件
rm "${PID_FILE}"

echo "✅ NoneBot 已停止"
echo ""
echo "================================"
echo "   停止完成！"
echo "================================"
