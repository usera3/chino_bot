"""测试长期记忆（VectorStore）"""
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
    print("🧠 zhinai-bot-v3 - 长期记忆测试")
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
    
    # 创建 Butler（启用长期记忆）
    print("🧠 创建 Butler（启用长期记忆）...")
    tools = get_all_tools()
    butler = Butler(
        llm=llm, 
        tools=tools, 
        verbose=True,
        use_vector_store=True,  # 启用长期记忆
        embedding_type="fake"  # 使用假 Embeddings（开发测试用）
    )
    print()
    
    # 测试场景
    print("=" * 60)
    print("📝 测试场景：长期记忆")
    print("=" * 60)
    print()
    
    # 第一轮对话：建立记忆
    print("=" * 60)
    print("第一轮对话：建立记忆")
    print("=" * 60)
    print()
    
    conversations_round1 = [
        "你好，我是小明，今年25岁",
        "我喜欢吃火锅和烧烤",
        "我的生日是3月15日",
        "我在北京工作，是一名程序员",
    ]
    
    for user_input in conversations_round1:
        print(f"👤 用户: {user_input}")
        response = butler.process(user_input, user_id="test_user")
        print(f"🤖 智乃: {response}")
        print()
    
    # 显示记忆统计
    stats = butler.get_memory_stats()
    print("=" * 60)
    print("📊 记忆统计")
    print("=" * 60)
    print(f"短期记忆消息数: {stats['short_term_messages']}")
    print(f"长期记忆已启用: {stats['long_term_enabled']}")
    if 'total_conversations' in stats:
        print(f"长期记忆对话数: {stats['total_conversations']}")
    print()
    
    # 清空短期记忆（模拟重启）
    print("=" * 60)
    print("🔄 清空短期记忆（模拟重启）")
    print("=" * 60)
    butler.clear_memory()
    print()
    
    # 第二轮对话：测试长期记忆检索
    print("=" * 60)
    print("第二轮对话：测试长期记忆检索")
    print("=" * 60)
    print()
    
    conversations_round2 = [
        "我叫什么名字？",
        "我喜欢吃什么？",
        "我的生日是什么时候？",
        "我在哪里工作？",
    ]
    
    for user_input in conversations_round2:
        print(f"👤 用户: {user_input}")
        response = butler.process(user_input, user_id="test_user")
        print(f"🤖 智乃: {response}")
        print()
    
    # 最终统计
    stats = butler.get_memory_stats()
    print("=" * 60)
    print("📊 最终统计")
    print("=" * 60)
    print(f"短期记忆消息数: {stats['short_term_messages']}")
    if 'total_conversations' in stats:
        print(f"长期记忆对话数: {stats['total_conversations']}")
    print()
    
    print("=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print()
    print("💡 观察要点:")
    print("   1. 第一轮对话后，信息被保存到长期记忆")
    print("   2. 清空短期记忆后，短期记忆丢失")
    print("   3. 第二轮对话时，从长期记忆中检索到相关信息")
    print("   4. Agent 能够基于长期记忆回答问题")
    print()


if __name__ == "__main__":
    main()
