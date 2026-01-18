#!/bin/bash

# 创建新 Bot 配置的辅助脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================"
echo "   创建新 Bot 配置"
echo "================================"
echo ""

# 输入 Bot 信息
read -p "Bot 名称 (如 bot1, bot2): " bot_name
read -p "QQ 号: " qq_number
read -p "NoneBot 端口 (默认 8080): " port
read -p "NapCat 端口 (默认 3000): " napcat_port

# 设置默认值
port=${port:-8080}
napcat_port=${napcat_port:-3000}

# 创建目录
bot_dir="bots/$bot_name"
mkdir -p "$bot_dir"
mkdir -p "$bot_dir/napcat"

echo ""
echo "正在创建配置..."

# 创建 .env 文件
cat > "$bot_dir/.env" << EOF
# Bot 基础配置
BOT_ID=$bot_name
BOT_QQ=$qq_number
HOST=127.0.0.1
PORT=$port
NAPCAT_PORT=$napcat_port

# NoneBot 配置
LOG_LEVEL=INFO
SUPERUSERS=["1143242311"]
NICKNAME=["智乃", "chino"]
COMMAND_START=["/", ""]
COMMAND_SEP=["."]

# OneBot 配置
ONEBOT_ACCESS_TOKEN=""

# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-88d32ba8d6b644da8b00647200eafa95
DEEPSEEK_BASE_URL=https://api.deepseek.com

# QQ 邮箱 SMTP 配置
QQ_EMAIL_SENDER=${qq_number}@qq.com
QQ_EMAIL_PASSWORD=请填写授权码

# 其他 API（可选）
TAVILY_API_KEY=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
AMAP_API_KEY=f295c899197cc6a1f8d02cde8a81cc7a
DASHSCOPE_API_KEY=sk-105724d3e4bb4f6ea354426dbecf3137
EOF

echo -e "${GREEN}✓ 配置文件已创建: $bot_dir/.env${NC}"
echo ""
echo "================================"
echo "   配置完成！"
echo "================================"
echo ""
echo "📝 下一步："
echo "1. 编辑 $bot_dir/.env 文件"
echo "2. 配置 QQ 邮箱授权码"
echo "3. 配置 NapCat (如需要)"
echo "4. 运行: bash start_multi_bots.sh"
echo ""
echo -e "${YELLOW}⚠️  注意：${NC}"
echo "- 确保端口 $port 未被占用"
echo "- 确保 QQ 号 $qq_number 已登录 NapCat"
echo ""
