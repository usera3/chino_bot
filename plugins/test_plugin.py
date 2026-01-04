from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import MessageEvent

# 创建一个监听 'test' 命令的处理器
test_handler = on_command("test", priority=5)

@test_handler.handle()
async def handle_test(event: MessageEvent):
    """处理 test 命令"""
    await test_handler.send("我在")
