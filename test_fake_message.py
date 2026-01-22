#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试伪造消息工具"""
import asyncio
import sys
sys.path.insert(0, '.')

from tools.fake_message_tool import fake_message_tool


async def test_fake_message():
    """测试伪造消息"""
    
    print("测试伪造消息工具")
    print("=" * 60)
    
    # 测试占位符替换
    messages = "{{USER_QQ}}说你好|{{BOT_QQ}}说你也好|{{USER_QQ}}说今天天气不错|{{BOT_QQ}}说是啊"
    user_qq = "1446437177"
    bot_qq = "2509109290"
    
    print(f"\n原始消息：")
    print(messages)
    print(f"\nuser_qq: {user_qq}")
    print(f"bot_qq: {bot_qq}")
    
    # 手动替换测试
    replaced = messages.replace("{{USER_QQ}}", user_qq).replace("{{BOT_QQ}}", bot_qq)
    print(f"\n替换后：")
    print(replaced)
    
    # 解析消息
    print(f"\n解析结果：")
    for msg in replaced.split("|"):
        if "说" in msg:
            qq, content = msg.split("说", 1)
            print(f"  QQ {qq}: {content}")


if __name__ == "__main__":
    asyncio.run(test_fake_message())
