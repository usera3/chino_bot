#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zhinai-bot-v3 - NoneBot 主程序
基于 LangChain Agent 的智能管家机器人
"""
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 初始化 NoneBot
nonebot.init()

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 加载 APScheduler 插件（定时任务）
nonebot.load_plugin("nonebot_plugin_apscheduler")

# 加载自定义插件
nonebot.load_plugins("plugins")

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 zhinai-bot-v3 启动中...")
    print("=" * 60)
    print("📡 NoneBot 端口: 8080")
    print("🧠 使用 LangChain Agent (Butler)")
    print("💾 启用长期记忆 (VectorStore)")
    print("⏰ 启用定时任务 (APScheduler)")
    print("=" * 60)
    nonebot.run()
