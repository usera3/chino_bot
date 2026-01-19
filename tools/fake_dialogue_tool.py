#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伪造对话工具 - 文本格式版本
不使用合并转发，而是生成格式化的文本对话
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type
import asyncio


class FakeDialogueInput(BaseModel):
    """伪造对话输入"""
    messages: str = Field(
        description="""要伪造的对话内容，格式：昵称1说内容1|昵称2说内容2

示例：
- "小明说你好|小红说你也好|小明说今天天气不错|小红说是啊"

格式规则：
- 使用 | 分隔不同的消息
- 使用"说"连接昵称和消息内容
"""
    )


class FakeDialogueTool(BaseTool):
    """伪造对话工具（文本格式）"""
    
    name: str = "create_fake_dialogue"
    description: str = """创建伪造的对话文本，可以模拟多个用户的对话。

🎭 核心功能：AI 可以自动创作对话内容！

当用户说"帮我伪造 XXX 和 YYY 谈恋爱的对话"时：
1. AI 需要自己创作符合场景的对话内容
2. 根据用户要求的句数生成相应数量的对话
3. 对话要自然、有趣、符合场景

使用场景：
- 制作有趣的对话文本（恋爱、吵架、搞笑等）
- 模拟多人对话场景
- 创建教程示例对话

输入格式：
messages: "昵称1说内容1|昵称2说内容2|昵称3说内容3"

示例 1 - 简单对话：
用户: "帮我伪造一个对话，小明说你好|小红说你也好"
→ 调用 create_fake_dialogue(
    messages="小明说你好|小红说你也好"
)

示例 2 - AI 创作对话（重要！）：
用户: "帮我伪造小明和小红谈恋爱的 10 句对话"
→ AI 需要自己创作 10 句恋爱对话，然后调用：
create_fake_dialogue(
    messages="小明说今天天气真好|小红说是啊，和你在一起的每一天都很好|小明说你真会说话|小红说因为是对你说的呀|..."
)

🎨 AI 创作指南：
- 根据场景（恋爱、吵架、搞笑等）创作合适的对话
- 对话要自然流畅，有来有往
- 注意对话的情感和语气
- 可以加入表情、语气词让对话更生动
"""
    args_schema: Type[BaseModel] = FakeDialogueInput
    
    def _run(self, messages: str) -> str:
        """
        同步执行（LangChain 要求）
        
        Args:
            messages: 消息内容
            
        Returns:
            执行结果
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._arun(messages))
            loop.close()
            return result
        except Exception as e:
            return f"创建对话失败: {str(e)}"
    
    async def _arun(self, messages: str) -> str:
        """
        异步执行创建对话
        
        Args:
            messages: 消息内容，格式：昵称1说内容1|昵称2说内容2
            
        Returns:
            格式化的对话文本
        """
        try:
            from nonebot import get_bot
            from nonebot.adapters.onebot.v11 import Bot
            from tools.qq_interaction_tools import get_current_context
            
            # 获取 Bot 实例
            try:
                bot: Bot = get_bot()
            except Exception:
                return "❌ 无法获取 Bot 实例，请确保机器人正在运行"
            
            # 获取当前对话上下文
            context = get_current_context()
            target_user_id = context.get("user_id")
            target_group_id = context.get("group_id")
            
            # 确定发送目标
            if target_group_id:
                target_id = str(target_group_id)
                is_group = True
            elif target_user_id:
                target_id = target_user_id
                is_group = False
            else:
                return "❌ 无法确定发送目标，请在对话中使用此功能"
            
            # 解析消息
            dialogue_lines = []
            user_msgs = messages.split("|")
            
            for user_msg in user_msgs:
                user_msg = user_msg.strip()
                if not user_msg or "说" not in user_msg:
                    continue
                
                try:
                    name, content = user_msg.split("说", 1)
                    name = name.strip()
                    content = content.strip()
                    
                    dialogue_lines.append(f"{name}: {content}")
                
                except ValueError:
                    return f"❌ 消息格式错误: {user_msg}（应为：昵称说内容）"
            
            if not dialogue_lines:
                return "❌ 没有有效的消息内容"
            
            # 构建对话文本
            dialogue_text = "━━━━━━━━━━━━━━━━\n"
            dialogue_text += "📱 对话记录\n"
            dialogue_text += "━━━━━━━━━━━━━━━━\n\n"
            dialogue_text += "\n\n".join(dialogue_lines)
            dialogue_text += "\n\n━━━━━━━━━━━━━━━━"
            
            # 发送消息
            try:
                if is_group:
                    await bot.send_group_msg(
                        group_id=int(target_id),
                        message=dialogue_text
                    )
                    return f"✅ 成功发送对话到群 {target_id}（共 {len(dialogue_lines)} 条消息）"
                else:
                    await bot.send_private_msg(
                        user_id=int(target_id),
                        message=dialogue_text
                    )
                    return f"✅ 成功发送对话到用户 {target_id}（共 {len(dialogue_lines)} 条消息）"
            
            except Exception as e:
                return f"❌ 发送失败: {str(e)}"
        
        except Exception as e:
            return f"❌ 创建对话时出错: {str(e)}"


# 创建工具实例
fake_dialogue_tool = FakeDialogueTool()


if __name__ == "__main__":
    # 测试
    print("伪造对话工具（文本格式）")
    print("=" * 60)
    print("功能：创建格式化的对话文本")
    print("格式：昵称1说内容1|昵称2说内容2")
    print()
    print("示例：")
    print('  小明说你好|小红说我也好')
    print('  张三说今天天气不错|李四说是啊 真的很好')
