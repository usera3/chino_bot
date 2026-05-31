#!/bin/bash

# ===========================================
# Chino Bot 一键启动脚本
# 功能：同时启动 NoneBot 和 NapCat(QQ)
# 支持黑屏后继续运行
# ===========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="${CHINO_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
BOT_DIR="${PROJECT_DIR}"
VENV_DIR="${PROJECT_DIR}/.venv"
LOG_DIR="${CHINO_LOG_DIR:-${PROJECT_DIR}/logs}"
PID_FILE="${PROJECT_DIR}/.bot_pids"

# 创建日志目录
mkdir -p "${LOG_DIR}"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   Chino Bot 启动中...${NC}"
echo -e "${GREEN}================================${NC}"

# 检查是否已经在运行
if [ -f "${PID_FILE}" ]; then
    echo -e "${YELLOW}检测到可能有正在运行的实例...${NC}"
    echo -e "${YELLOW}正在清理...${NC}"
    bash "${PROJECT_DIR}/stop_bot.sh" 2>/dev/null
    sleep 2
fi

# 1. 启动 NoneBot
echo -e "${GREEN}[1/3] 启动 NoneBot 机器人...${NC}"

# 使用虚拟环境的 Python（完整路径）
PYTHON_BIN="${VENV_DIR}/bin/python"

# 切换到 bot 目录
cd "${BOT_DIR}"

if [ ! -x "${PYTHON_BIN}" ]; then
    PYTHON_BIN="${PYTHON_BIN:-python}"
fi

if command -v caffeinate >/dev/null 2>&1; then
    nohup caffeinate -i "${PYTHON_BIN}" bot.py > "${LOG_DIR}/bot.log" 2>&1 &
else
    nohup "${PYTHON_BIN}" bot.py > "${LOG_DIR}/bot.log" 2>&1 &
fi
BOT_PID=$!

# 等待 bot 启动
sleep 3

# 检查 bot 是否成功启动
if ps -p ${BOT_PID} > /dev/null 2>&1; then
    echo -e "${GREEN}✓ NoneBot 启动成功 (PID: ${BOT_PID})${NC}"
    echo "BOT_PID=${BOT_PID}" > "${PID_FILE}"
else
    echo -e "${RED}✗ NoneBot 启动失败，请查看日志: ${LOG_DIR}/bot.log${NC}"
    exit 1
fi

# 2. 启动 NapCat (QQ)
echo -e "${GREEN}[2/3] 启动 NapCat (QQ)...${NC}"

# 检查 QQ 是否已经在运行
QQ_RUNNING=$(ps aux | grep "[Q]Q.app/Contents/MacOS/QQ" | grep -v grep | awk '{print $2}')
if [ -n "${QQ_RUNNING}" ]; then
    echo -e "${YELLOW}QQ 已在运行 (PID: ${QQ_RUNNING})${NC}"
    echo "QQ_PID=${QQ_RUNNING}" >> "${PID_FILE}"
else
    # 使用 caffeinate 启动 QQ，防止休眠
    nohup caffeinate -i /Applications/QQ.app/Contents/MacOS/QQ --no-sandbox > "${LOG_DIR}/qq.log" 2>&1 &
    QQ_PID=$!
    
    sleep 3
    
    # 验证 QQ 是否启动
    if ps -p ${QQ_PID} > /dev/null 2>&1; then
        echo -e "${GREEN}✓ QQ 启动成功 (PID: ${QQ_PID})${NC}"
        echo "QQ_PID=${QQ_PID}" >> "${PID_FILE}"
    else
        echo -e "${YELLOW}⚠ QQ 启动状态未知，请手动确认${NC}"
    fi
fi

# 3. 验证系统状态
echo -e "${GREEN}[3/3] 验证系统状态...${NC}"
sleep 2

# 检查端口 8080 是否被占用
if lsof -ti:8080 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 端口 8080 正常监听${NC}"
else
    echo -e "${RED}✗ 端口 8080 未监听，请检查日志${NC}"
fi

# 完成
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   启动完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "🤖 Chino Bot 特性："
echo -e "   ✅ LangChain Agent (Butler)"
echo -e "   ✅ 长期记忆 (VectorStore)"
echo -e "   ✅ 智能工具调用"
echo ""
echo -e "📝 日志文件位置："
echo -e "   Bot 日志: ${LOG_DIR}/bot.log"
echo -e "   QQ 日志:  ${LOG_DIR}/qq.log"
echo ""
echo -e "📊 查看实时日志："
echo -e "   ${YELLOW}tail -f ${LOG_DIR}/bot.log${NC}"
echo ""
echo -e "🛑 停止机器人："
echo -e "   ${YELLOW}bash ${PROJECT_DIR}/stop_bot.sh${NC}"
echo ""
echo -e "💡 提示：已启用防休眠模式，黑屏后机器人将继续运行"
echo ""
