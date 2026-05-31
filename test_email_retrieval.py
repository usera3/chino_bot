"""测试邮箱信息检索"""
from core.vector_store import VectorStoreManager

def main():
    print("="*60)
    print("测试：能否检索到邮箱信息")
    print("="*60)
    
    vector_store = VectorStoreManager(
        persist_directory="./data/chroma",
        embedding_type="fake"
    )
    
    # 模拟用户问"你还记得我的邮箱吗"
    query = "你还记得我的邮箱吗"
    user_id = "123456789"
    
    print(f"\n用户问题: {query}")
    print(f"用户ID: {user_id}")
    print(f"\n检索 k=5 条最相关的历史对话:\n")
    
    context = vector_store.get_relevant_context(
        query=query,
        user_id=user_id,
        k=5
    )
    
    print(context)
    print("\n" + "="*60)
    
    # 检查是否包含邮箱信息
    if "123456789@qq.com" in context or "qq号加" in context or "邮箱" in context:
        print("✅ 成功检索到邮箱相关信息")
    else:
        print("❌ 未检索到邮箱相关信息")
        print("\n让我们尝试直接搜索包含邮箱的对话:")
        
        # 直接搜索
        results = vector_store.search_similar_conversations(
            query="我的邮箱就是我qq号加qq邮箱后缀",
            user_id=user_id,
            k=3
        )
        
        if results:
            print(f"\n找到 {len(results)} 条包含邮箱信息的对话:")
            for i, doc in enumerate(results, 1):
                print(f"\n[{i}] {doc.metadata.get('timestamp', '未知')}")
                print(f"用户: {doc.metadata.get('user_input', 'N/A')[:100]}")
                print(f"智乃: {doc.metadata.get('bot_response', 'N/A')[:100]}")

if __name__ == "__main__":
    main()
