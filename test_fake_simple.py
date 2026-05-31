#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试合并转发消息
需要机器人已经在运行
"""
import asyncio
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot


async def test_forward():
    """测试合并转发"""
    print("=" * 60)
    print("测试合并转发消息")
    print("=" * 60)
    
    try:
        bot: Bot = get_bot()
        print(f"✓ 获取到 Bot: {bot.self_id}")
        
        user_qq = "123456789"
        bot_qq = str(bot.self_id)
        
        # 构建消息
        messages = [
            {
                "type": "node",
                "data": {
                    "name": "空白",
                    "uin": user_qq,
                    "content": "测试消息1"
                }
            },
            {
                "type": "node",
                "data": {
                    "name": "智乃",
                    "uin": bot_qq,
                    "content": "测试消息2"
                }
            }
        ]
        
        print(f"\n发送到用户 {user_qq}...")
        result = await bot.call_api(
            "send_private_forward_msg",
            user_id=int(user_qq),
            messages=messages
        )
        print(f"✓ 成功: {result}")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_forward())
