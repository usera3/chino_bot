#!/bin/bash

echo "=================================="
echo "🤖 zhinai-bot-v3 安装脚本"
echo "=================================="
echo ""

# 检查 Python 版本
echo "📋 检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python 版本: $python_version"
echo ""

# 安装依赖
echo "📦 安装依赖..."
pip3 install -r requirements.txt
echo ""

# 创建 .env 文件
if [ ! -f .env ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请编辑并填入你的 API Key"
else
    echo "✅ .env 文件已存在"
fi
echo ""

echo "=================================="
echo "✅ 安装完成！"
echo "=================================="
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，填入你的 API Key"
echo "2. 运行测试: python3 test_butler.py"
echo "3. 交互聊天: python3 chat.py"
echo ""
