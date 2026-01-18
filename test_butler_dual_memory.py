"""测试 Butler 集成双向量库记忆系统"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from core.butler import Butler
from tools.basic_tools import get_all_tools

# 加载环境变量
load_dotenv()

def test_butler_dual_memory():
    """测试 Butler 的双向量库记忆功能"""
    print("\n" + "=" * 60)
    print("测试 Butler 双向量库记忆系统")
    print("=" * 60)
    
    # 初始化 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0.7,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    
    # 创建 Butler（启用双向量库）
    butler = Butler(
        llm=llm,
        tools=get_all_tools(),
        verbose=True,
        use_dual_memory=True,
        memory_path="./data",
        embedding_type="fake"
    )
    
    print("\n" + "=" * 60)
    print("📝 测试对话并提取知识")
    print("=" * 60)
    
    # 测试对话
    test_conversations = [
        "你好",
        "我叫李四",
        "我的邮箱是 lisi@gmail.com",
        "我喜欢喝咖啡",
        "我住在上海",
    ]
    
    user_id = "test_user_butler"
    
    for user_input in test_conversations:
        print(f"\n用户: {user_input}")
        response = butler.process(user_input, user_id=user_id)
        print(f"智乃: {response}")
    
    print("\n" + "=" * 60)
    print("🔍 测试记忆检索")
    print("=" * 60)
    
    # 测试记忆检索
    test_queries = [
        "我叫什么名字？",
        "我的邮箱是什么？",
        "我喜欢喝什么？",
    ]
    
    for query in test_queries:
        print(f"\n用户: {query}")
        response = butler.process(query, user_id=user_id)
        print(f"智乃: {response}")
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("📊 记忆统计信息:")
    stats = butler.get_memory_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print("=" * 60)

if __name__ == "__main__":
    test_butler_dual_memory()
