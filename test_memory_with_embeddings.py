"""测试长期记忆（使用真实的 Embeddings）"""
import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from core.butler import Butler
from tools.basic_tools import get_all_tools

# 加载环境变量
load_dotenv()


async def test_memory():
    """测试长期记忆"""
    print("\n" + "=" * 60)
    print("🧪 测试长期记忆（HuggingFace Embeddings）")
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
    
    # 3. 创建 Butler（使用 HuggingFace Embeddings）
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_vector_store=True,
        embedding_type="huggingface"  # 使用真实的 embeddings
    )
    print("✅ Butler 初始化成功\n")
    
    # 测试用例
    test_cases = [
        {
            "name": "第1轮：告诉 AI 邮箱地址",
            "input": "我的邮箱是 test@example.com",
            "expected": "AI 应该记住邮箱地址"
        },
        {
            "name": "第2轮：询问邮箱地址",
            "input": "我的邮箱是什么？",
            "expected": "AI 应该能从长期记忆中检索到 test@example.com"
        },
        {
            "name": "第3轮：要求发邮件（不提供邮箱）",
            "input": "给我发个邮件，主题是测试，内容是你好",
            "expected": "AI 应该使用记忆中的邮箱地址，不再询问"
        },
    ]
    
    user_id = "test_user_123"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"📝 {test_case['name']}")
        print(f"{'=' * 60}")
        print(f"输入: {test_case['input']}")
        print(f"期望: {test_case['expected']}")
        print()
        
        try:
            # 执行测试
            response = await butler.aprocess(test_case['input'], user_id=user_id)
            
            print(f"\n✅ 测试 {i} 完成")
            print(f"回复: {response}")
            
        except Exception as e:
            print(f"\n❌ 测试 {i} 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 等待一下
        if i < len(test_cases):
            print("\n⏳ 等待 2 秒...")
            await asyncio.sleep(2)
    
    print(f"\n{'=' * 60}")
    print("🎉 所有测试完成！")
    print(f"{'=' * 60}\n")
    
    # 显示记忆统计
    stats = butler.get_memory_stats()
    print("📊 记忆统计:")
    print(f"   短期记忆消息数: {stats['short_term_messages']}")
    print(f"   长期记忆已启用: {stats['long_term_enabled']}")
    if 'total_documents' in stats:
        print(f"   长期记忆文档数: {stats['total_documents']}")


if __name__ == "__main__":
    asyncio.run(test_memory())
