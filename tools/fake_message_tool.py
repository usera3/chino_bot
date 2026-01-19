#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伪造消息工具
基于 nonebot-plugin-fakemsg 的合并转发消息伪造功能
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type, List
import asyncio


class FakeMessageInput(BaseModel):
    """伪造消息输入"""
    messages: str = Field(
        description="""要伪造的消息内容，格式：QQ号1说内容1|QQ号2说内容2

⚠️ 特别说明：
- 如果用户说"帮我伪造我和你的对话"，使用 {{USER_QQ}} 代表用户，{{BOT_QQ}} 代表机器人
- 如果用户说"帮我伪造 A 和 B 的对话"，直接使用 A 和 B 的 QQ 号

示例：
- "{{USER_QQ}}说你好|{{BOT_QQ}}说你也好" → 会自动替换为实际的 QQ 号
- "123456说你好|654321说我也好" → 直接使用指定的 QQ 号

格式规则：
- 使用 | 分隔不同用户的消息
- 使用"说"连接 QQ 号和消息内容
- 同一用户的多条消息用空格分隔
- QQ 号必须是 6-10 位数字（或使用占位符）
"""
    )
    user_qq: Optional[str] = Field(
        default=None,
        description="用户的 QQ 号（用于替换 {{USER_QQ}} 占位符）"
    )
    bot_qq: Optional[str] = Field(
        default=None,
        description="机器人的 QQ 号（用于替换 {{BOT_QQ}} 占位符）"
    )


class FakeMessageTool(BaseTool):
    """伪造消息工具（合并转发）"""
    
    name: str = "send_fake_message"
    description: str = """发送伪造的合并转发消息，可以模拟多个用户的对话。

🎭 核心功能：AI 可以自动创作对话内容！

⚠️ 重要提示：
- 此功能在**群聊**中效果最好
- 私聊可能因为 OneBot 实现限制而无法正确显示多个发送者
- 如果遇到问题，建议在群聊中使用

当用户说"帮我伪造 XXX 和 YYY 谈恋爱的对话"时：
1. AI 需要自己创作符合场景的对话内容
2. 根据用户要求的句数生成相应数量的对话
3. 对话要自然、有趣、符合场景

使用场景：
- 制作有趣的对话截图（恋爱、吵架、搞笑等）
- 模拟多人对话场景
- 创建教程示例对话

⚠️ 重要限制：
1. 仅用于娱乐和教学目的
2. 不得用于欺骗、诈骗或其他违法行为
3. 伪造的 QQ 号必须是机器人好友或在群内
4. 超级用户不受白名单限制

输入格式：
messages: "QQ号1说内容1|QQ号2说内容2|QQ号3说内容3"

⚠️ 注意：工具会自动发送到当前对话（群聊或私聊），无需指定 target_id

示例 1 - 简单对话：
用户: "帮我伪造一个对话，123456说你好|654321说你也好"
→ 调用 send_fake_message(
    messages="123456说你好|654321说你也好"
)

示例 2 - AI 创作对话（重要！）：
用户: "帮我伪造 122344 和 244223 谈恋爱的 20 句对话"
→ AI 需要自己创作 20 句恋爱对话，然后调用：
send_fake_message(
    messages="122344说今天天气真好|244223说是啊，和你在一起的每一天都很好|122344说你真会说话|244223说因为是对你说的呀|..."
)

示例 3 - 多人对话：
用户: "伪造三个人讨论技术的对话"
→ AI 创作技术讨论内容：
send_fake_message(
    messages="111111说这个 bug 怎么解决|222222说我看看代码|333333说可能是异步问题|..."
)

🎨 AI 创作指南：
- 根据场景（恋爱、吵架、搞笑等）创作合适的对话
- 对话要自然流畅，有来有往
- 注意对话的情感和语气
- 可以加入表情、语气词让对话更生动
"""
    args_schema: Type[BaseModel] = FakeMessageInput
    
    def _run(self, messages: str, user_qq: Optional[str] = None, bot_qq: Optional[str] = None) -> str:
        """
        同步执行（LangChain 要求）
        
        Args:
            messages: 消息内容
            user_qq: 用户 QQ 号
            bot_qq: 机器人 QQ 号
            
        Returns:
            执行结果
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._arun(messages, user_qq, bot_qq))
            loop.close()
            return result
        except Exception as e:
            return f"伪造消息失败: {str(e)}"
    
    async def _arun(self, messages: str, user_qq: Optional[str] = None, bot_qq: Optional[str] = None) -> str:
        """
        异步执行伪造消息
        
        Args:
            messages: 消息内容，格式：QQ号1说内容1|QQ号2说内容2
            user_qq: 用户 QQ 号（用于替换占位符）
            bot_qq: 机器人 QQ 号（用于替换占位符）
            
        Returns:
            执行结果
        """
        try:
            from nonebot import get_bot
            from nonebot.adapters.onebot.v11 import Bot
            from tools.qq_interaction_tools import get_current_context
            
            # 获取 Bot 实例
            try:
                bot: Bot = get_bot()
                # 如果没有传入 bot_qq，从 bot 实例获取
                if not bot_qq:
                    bot_qq = str(bot.self_id)
            except Exception:
                return "❌ 无法获取 Bot 实例，请确保机器人正在运行"
            
            # 获取当前对话上下文
            context = get_current_context()
            target_user_id = context.get("user_id")
            target_group_id = context.get("group_id")
            
            print(f"[DEBUG] 当前上下文: {context}")
            print(f"[DEBUG] target_user_id: {target_user_id}")
            print(f"[DEBUG] target_group_id: {target_group_id}")
            print(f"[DEBUG] bot_qq: {bot_qq}")
            
            # 确定发送目标
            if target_group_id:
                # 群聊
                target_id = str(target_group_id)
                is_group = True
                target_desc = f"群 {target_id}"
            elif target_user_id:
                # 私聊
                target_id = target_user_id
                is_group = False
                target_desc = f"用户 {target_id}"
            else:
                return "❌ 无法确定发送目标，请在对话中使用此功能"
            
            print(f"[DEBUG] 最终发送目标: {target_desc} (is_group={is_group})")
            print(f"[DEBUG] target_id == bot_qq? {target_id == bot_qq}")
            
            # 替换占位符
            if user_qq:
                messages = messages.replace("{{USER_QQ}}", user_qq)
            if bot_qq:
                messages = messages.replace("{{BOT_QQ}}", bot_qq)
            
            # 解析消息
            fake_msg_list = []
            user_msgs = messages.split("|")
            
            print(f"[DEBUG] 开始解析消息，共 {len(user_msgs)} 条")
            print(f"[DEBUG] 替换后的完整消息: {messages[:200]}...")
            
            for user_msg in user_msgs:
                user_msg = user_msg.strip()
                if not user_msg or "说" not in user_msg:
                    continue
                
                try:
                    msg_qq, content = user_msg.split("说", 1)
                    msg_qq = msg_qq.strip()
                    content = content.strip()
                    
                    print(f"[DEBUG] 解析消息 - QQ: {msg_qq}, 内容: {content[:30]}...")
                    
                    # 验证 QQ 号格式
                    if not msg_qq.isdigit() or len(msg_qq) < 6 or len(msg_qq) > 10:
                        return f"❌ QQ 号格式错误: {msg_qq}（必须是 6-10 位数字）"
                    
                    # 获取用户信息
                    try:
                        user_info = await bot.get_stranger_info(user_id=int(msg_qq))
                        user_name = user_info["nickname"]
                        print(f"[DEBUG] 获取昵称成功 - QQ {msg_qq}: {user_name}")
                    except Exception as e:
                        user_name = f"用户{msg_qq}"
                        print(f"[DEBUG] 获取昵称失败 - QQ {msg_qq}: {e}")
                    
                    # 处理同一用户的多条消息（用空格分隔）
                    for msg in content.split(" "):
                        if msg.strip():
                            fake_msg_list.append((user_name, msg_qq, msg.strip()))
                            print(f"[DEBUG] 添加消息 - {user_name}({msg_qq}): {msg.strip()[:20]}...")
                
                except ValueError:
                    return f"❌ 消息格式错误: {user_msg}（应为：QQ号说内容）"
            
            print(f"[DEBUG] 解析完成，共 {len(fake_msg_list)} 条消息")
            print(f"[DEBUG] 消息列表前3条: {fake_msg_list[:3]}")
            
            if not fake_msg_list:
                return "❌ 没有有效的消息内容"
            
            # 构建合并转发消息
            def to_json(info: tuple[str, str, str]):
                return {
                    "type": "node",
                    "data": {
                        "name": info[0],
                        "uin": info[1],
                        "content": info[2]
                    }
                }
            
            forward_messages = [to_json(info) for info in fake_msg_list]
            
            print(f"[DEBUG] 准备发送到 {target_desc}")
            print(f"[DEBUG] 合并转发消息数量: {len(forward_messages)}")
            
            # 发送消息
            try:
                if is_group:
                    await bot.call_api(
                        "send_group_forward_msg",
                        group_id=int(target_id),
                        messages=forward_messages
                    )
                    return f"✅ 成功发送伪造消息到群 {target_id}（共 {len(fake_msg_list)} 条消息）"
                else:
                    await bot.call_api(
                        "send_private_forward_msg",
                        user_id=int(target_id),
                        messages=forward_messages
                    )
                    return f"✅ 成功发送伪造消息到用户 {target_id}（共 {len(fake_msg_list)} 条消息）"
            
            except Exception as e:
                print(f"[DEBUG] 发送失败: {e}")
                import traceback
                traceback.print_exc()
                return f"❌ 发送失败: {str(e)}"
        
        except Exception as e:
            print(f"[DEBUG] 伪造消息时出错: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ 伪造消息时出错: {str(e)}"


# 创建工具实例
fake_message_tool = FakeMessageTool()


if __name__ == "__main__":
    # 测试
    print("伪造消息工具")
    print("=" * 60)
    print("功能：创建合并转发的伪造消息")
    print("格式：QQ号1说内容1|QQ号2说内容2")
    print()
    print("示例：")
    print('  123456说你好|654321说我也好')
    print('  111111说今天天气不错|222222说是啊 真的很好')
