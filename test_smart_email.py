#!/usr/bin/env python3
"""
测试智能邮件推理功能
"""
import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from core.butler import Butler
from tools.basic_tools import get_all_tools

# 加载环境变量
load_dotenv()


async def test_smart_email():
    """测试智能邮件推理"""
    print("\n" + "=" * 60)
    print("🧪 测试智能邮件推理功能")
    print("=" * 60)
    
    # 初始化 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0.7,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    
    # 获取工具
    tools = get_all_tools()
    
    # 创建 Butler
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_dual_memory=False  # 测试时不使用记忆
    )
    
    # 模拟用户上下文（第一次和机器人说话的用户）
    from tools.qq_interaction_tools import set_current_context
    set_current_context(user_id="123456789", group_id=878812866)
    
    # 测试场景：用户说"给我发个邮件"
    print("\n📝 测试场景：用户说「给我发个邮件」")
    print("-" * 60)
    
    user_input = "[系统提示：发送此消息的用户是测试用户(QQ:123456789)，当前在群878812866中。你的 QQ 号是 1000000000，用户的 QQ 号是 123456789]\n\n给我发个邮件"
    
    response = await butler.aprocess(user_input, user_id="123456789")
    
    print("\n" + "=" * 60)
    print("🤖 AI 回复:")
    print(response)
    print("=" * 60)
    
    # 预期行为：
    # 1. AI 应该先调用 get_user_info 工具获取用户的 QQ 号
    # 2. 根据 QQ 号推理邮箱地址（123456789@qq.com）
    # 3. 调用 send_email 工具发送邮件
    # 4. 不应该询问用户邮箱是什么
    
    print("\n✅ 预期行为:")
    print("1. 调用 get_user_info 工具获取 QQ 号")
    print("2. 推理邮箱地址为 123456789@qq.com")
    print("3. 调用 send_email 工具发送邮件")
    print("4. 不询问用户邮箱")


if __name__ == "__main__":
    asyncio.run(test_smart_email())
