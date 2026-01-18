"""
测试 NoneBot 集成
验证 Butler 能否正常工作
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from core.butler import Butler
from tools.basic_tools import get_all_tools

# 加载环境变量
load_dotenv()


def main():
    """主函数"""
    print("=" * 60)
    print("🧪 测试 NoneBot 集成")
    print("=" * 60)
    print()
    
    # 初始化 LLM
    print("📡 初始化 DeepSeek...")
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0.7,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    print("✅ DeepSeek 初始化成功")
    print()
    
    # 获取工具
    print("🔧 加载工具...")
    tools = get_all_tools()
    print(f"✅ 已加载 {len(tools)} 个工具")
    print()
    
    # 创建 Butler
    print("🧠 创建 Butler...")
    butler = Butler(
        llm=llm,
        tools=tools,
        verbose=True,
        use_vector_store=True,
        embedding_type="fake"
    )
    print()
    
    # 测试对话
    print("=" * 60)
    print("💬 测试对话")
    print("=" * 60)
    print()
    
    test_messages = [
        "你好！",
        "现在几点了？",
        "我叫小明",
    ]
    
    for msg in test_messages:
        print(f"👤 用户: {msg}")
        response = butler.process(msg, user_id="test_user")
        print(f"🤖 智乃: {response}")
        print()
    
    # 显示统计
    stats = butler.get_memory_stats()
    print("=" * 60)
    print("📊 记忆统计")
    print("=" * 60)
    print(f"短期记忆: {stats['short_term_messages']} 条消息")
    print(f"长期记忆: {'已启用' if stats['long_term_enabled'] else '未启用'}")
    if 'total_conversations' in stats:
        print(f"长期记忆对话数: {stats['total_conversations']}")
    print()
    
    print("=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print()
    print("💡 如果测试通过，可以启动 NoneBot:")
    print("   ./start_bot.sh")
    print()


if __name__ == "__main__":
    main()
