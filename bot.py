#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新机器人主程序入口
完全独立于旧机器人，使用同一虚拟环境
"""
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 初始化 NoneBot
nonebot.init()

# 注册适配器
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 加载插件
nonebot.load_plugins("plugins")

if __name__ == "__main__":
    nonebot.run()












