#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试伪造消息工具 - 调试版本
"""
import asyncio
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot


async def test_forward_message():
    """测试合并转发消息"""
    try:
        bot: Bot = get_bot()
        bot_qq = str(bot.self_id)
        print(f"机器人 QQ: {bot_qq}")
        
        # 测试数据
        user_qq = "1446437177"  # 用户 QQ
        
        # 构建消息
        messages = [
            {
                "type": "node",
                "data": {
                    "name": "空白",
                    "uin": user_qq,
                    "content": "你好"
                }
            },
            {
                "type": "node",
                "data": {
                    "name": "智乃",
                    "uin": bot_qq,
                    "content": "你也好"
                }
            }
        ]
        
        print(f"\n发送到用户 {user_qq} 的私聊")
        print(f"消息内容: {messages}")
        
        # 发送到用户私聊
        result = await bot.call_api(
            "send_private_forward_msg",
            user_id=int(user_qq),
            messages=messages
        )
        
        print(f"发送结果: {result}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_forward_message())
