"""测试 Butler 使用 HTML 渲染工具"""
import asyncio
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化 NoneBot（HTML 渲染需要）
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)
nonebot.load_plugin("nonebot_plugin_htmlrender")

# 导入 Butler
from core.butler import Butler
from tools.basic_tools import get_all_tools
from langchain_openai import ChatOpenAI


async def test_butler_render():
    """测试 Butler 使用 HTML 渲染工具"""
    print("=" * 60)
    print("测试 Butler 使用 HTML 渲染工具")
    print("=" * 60)
    
    # 初始化 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com",
        temperature=0.7,
    )
    
    # 获取所有工具
    tools = get_all_tools()
    
    # 创建 Butler
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_dual_memory=False  # 测试时不使用记忆
    )
    
    # 测试用例
    test_cases = [
        "帮我画一个红色的爱心",
        "生成一个数据统计图表，显示1-4月的数据：60, 80, 45, 90",
        "做一张生日贺卡",
    ]
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"测试 {i}: {user_input}")
        print(f"{'=' * 60}\n")
        
        response = await butler.aprocess(user_input, user_id="test_user")
        
        print(f"\n🤖 Butler 回复:")
        print(response)
        print()
    
    print("=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_butler_render())
