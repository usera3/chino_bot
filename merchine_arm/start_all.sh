#!/bin/bash

# 机械臂小车完整启动脚本
# 包括服务器和移动 APP 开发环境

set -e

PROJECT_ROOT="/Users/mozi100/PycharmProjects/chino_bot"
VENV_PATH="$PROJECT_ROOT/.venv"
SERVER_PATH="$PROJECT_ROOT/new-bot/merchine_arm"
APP_PATH="$PROJECT_ROOT/new-bot/merchine_arm/robotic-arm-controller"

echo "🤖 机械臂小车系统启动"
echo "===================================="
echo ""

# 获取本机 IP
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "未找到")

if [ "$IP" = "未找到" ]; then
    echo "⚠️  警告：无法获取本机 IP 地址"
    echo "请手动检查网络连接"
    echo ""
else
    echo "📡 本机 IP: $IP"
    echo ""
fi

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 错误：未找到 Python 虚拟环境"
    echo "路径：$VENV_PATH"
    exit 1
fi

# 1. 启动机械臂服务器
echo "1️⃣  启动机械臂服务器（端口 7070）..."
echo ""

cd "$SERVER_PATH"
source "$VENV_PATH/bin/activate"

# 停止旧进程
pkill -f "server_v2.py" 2>/dev/null && echo "   已停止旧服务器" || echo "   无旧服务器进程"

# 启动服务器（后台运行）
python server_v2.py > /tmp/robotic_arm_server.log 2>&1 &
SERVER_PID=$!

echo "   服务器 PID: $SERVER_PID"
echo "   日志文件: /tmp/robotic_arm_server.log"

# 等待服务器启动
sleep 3

# 检查服务器是否成功启动
if curl -s http://localhost:7070/api/status > /dev/null 2>&1; then
    echo "   ✅ 服务器启动成功"
else
    echo "   ❌ 服务器启动失败"
    echo "   查看日志: tail -f /tmp/robotic_arm_server.log"
    exit 1
fi

echo ""

# 2. 启动移动 APP 开发服务器
echo "2️⃣  启动移动 APP 开发服务器..."
echo ""

cd "$APP_PATH"

echo "   📱 使用说明："
echo "   ------------"
echo "   1. 在手机上安装 Expo Go APP"
echo "      - iOS: App Store 搜索 'Expo Go'"
echo "      - Android: Google Play 搜索 'Expo Go'"
echo ""
echo "   2. 确保手机和电脑在同一 WiFi"
echo ""
echo "   3. 扫描即将显示的二维码"
echo ""
echo "   4. 在 APP 中配置服务器地址："
echo "      http://$IP:7070"
echo ""
echo "   5. 网页可视化界面："
echo "      http://localhost:7070/test_step1"
echo ""
echo "===================================="
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 捕获退出信号，清理进程
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    pkill -f "server_v2.py" 2>/dev/null && echo "   ✅ 机械臂服务器已停止" || true
    echo "   ✅ APP 开发服务器已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 启动 Expo（前台运行）
npx expo start

# 脚本正常结束时也清理
cleanup





