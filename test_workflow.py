"""测试工作流系统"""
import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from core.butler import Butler
from tools.basic_tools import get_all_tools

# 加载环境变量
load_dotenv()


async def test_workflow():
    """测试工作流系统"""
    print("\n" + "=" * 60)
    print("🧪 测试工作流系统")
    print("=" * 60 + "\n")
    
    # 1. 初始化 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0.7,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    print("✅ LLM 初始化成功")
    
    # 2. 获取工具
    tools = get_all_tools()
    print(f"✅ 已加载 {len(tools)} 个工具")
    
    # 3. 创建 Butler
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_vector_store=False  # 测试时不使用向量数据库
    )
    print("✅ Butler 初始化成功\n")
    
    # 4. 设置工作流工具的用户上下文
    for tool in butler.tools:
        if hasattr(tool, 'name') and tool.name == 'create_workflow':
            tool.current_user_id = "123456"
            tool.current_group_id = None
            print("✅ 已设置工作流工具的用户上下文\n")
            break
    
    # 测试用例
    test_cases = [
        {
            "name": "测试1：单步骤工作流 - 定时发邮件",
            "input": "10秒后给我发邮件提醒吃饭",
            "expected": "应该创建一个单步骤工作流，10秒后发送邮件"
        },
        {
            "name": "测试2：多步骤工作流 - 先查天气再发邮件",
            "input": "15秒后查深圳天气然后发邮件告诉我",
            "expected": "应该创建一个两步骤工作流，先查天气，再用天气结果发邮件"
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"📝 {test_case['name']}")
        print(f"{'=' * 60}")
        print(f"输入: {test_case['input']}")
        print(f"期望: {test_case['expected']}")
        print()
        
        try:
            # 执行测试
            response = await butler.aprocess(test_case['input'], user_id="123456")
            
            print(f"\n✅ 测试 {i} 完成")
            print(f"回复: {response}")
            
        except Exception as e:
            print(f"\n❌ 测试 {i} 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 等待一下，避免请求过快
        if i < len(test_cases):
            print("\n⏳ 等待 3 秒...")
            await asyncio.sleep(3)
    
    print(f"\n{'=' * 60}")
    print("🎉 所有测试完成！")
    print(f"{'=' * 60}\n")
    
    # 等待工作流执行
    print("⏳ 等待 20 秒，观察工作流执行...")
    await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(test_workflow())
