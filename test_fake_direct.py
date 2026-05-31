#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试合并转发消息 API
"""
import asyncio
import nonebot
from nonebot import get_driver, get_bot
from nonebot.adapters.onebot.v11 import Bot


async def test_forward_msg():
    """测试合并转发消息"""
    print("=" * 60)
    print("测试合并转发消息 API")
    print("=" * 60)
    
    try:
        # 等待 bot 连接
        await asyncio.sleep(2)
        
        bot: Bot = get_bot()
        print(f"✓ 获取到 Bot 实例")
        print(f"  机器人 QQ: {bot.self_id}")
        
        # 测试数据
        user_qq = "123456789"  # 用户 QQ
        bot_qq = str(bot.self_id)  # 机器人 QQ
        
        print(f"\n构建测试消息:")
        print(f"  用户 QQ: {user_qq}")
        print(f"  机器人 QQ: {bot_qq}")
        
        # 构建合并转发消息
        messages = [
            {
                "type": "node",
                "data": {
                    "name": "空白",
                    "uin": user_qq,
                    "content": "你好呀"
                }
            },
            {
                "type": "node",
                "data": {
                    "name": "智乃",
                    "uin": bot_qq,
                    "content": "你也好~"
                }
            },
            {
                "type": "node",
                "data": {
                    "name": "空白",
                    "uin": user_qq,
                    "content": "今天天气不错"
                }
            },
            {
                "type": "node",
                "data": {
                    "name": "智乃",
                    "uin": bot_qq,
                    "content": "是啊，很适合出去玩"
                }
            }
        ]
        
        print(f"\n消息内容:")
        for i, msg in enumerate(messages, 1):
            print(f"  [{i}] {msg['data']['name']}({msg['data']['uin']}): {msg['data']['content']}")
        
        # 测试 1: 发送到用户私聊
        print(f"\n{'=' * 60}")
        print(f"测试 1: 发送到用户私聊 (user_id={user_qq})")
        print(f"{'=' * 60}")
        
        try:
            result = await bot.call_api(
                "send_private_forward_msg",
                user_id=int(user_qq),
                messages=messages
            )
            print(f"✓ 发送成功!")
            print(f"  返回结果: {result}")
        except Exception as e:
            print(f"✗ 发送失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 等待一下
        await asyncio.sleep(2)
        
        # 测试 2: 尝试发送到机器人自己（看看会不会出现"机器人对自己"的情况）
        print(f"\n{'=' * 60}")
        print(f"测试 2: 发送到机器人自己 (user_id={bot_qq})")
        print(f"{'=' * 60}")
        
        try:
            result = await bot.call_api(
                "send_private_forward_msg",
                user_id=int(bot_qq),
                messages=messages
            )
            print(f"✓ 发送成功!")
            print(f"  返回结果: {result}")
        except Exception as e:
            print(f"✗ 发送失败: {e}")
        
        print(f"\n{'=' * 60}")
        print(f"测试完成")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 初始化 NoneBot
    nonebot.init()
    
    # 加载适配器
    driver = get_driver()
    driver.register_adapter(nonebot.adapters.onebot.v11.Adapter)
    
    # 在 bot 连接后运行测试
    @driver.on_bot_connect
    async def on_connect(bot: Bot):
        print(f"\n✓ Bot 已连接: {bot.self_id}")
        await test_forward_msg()
    
    # 运行
    nonebot.run()
