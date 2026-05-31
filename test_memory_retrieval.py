"""测试长期记忆检索功能"""
from core.vector_store import VectorStoreManager

def main():
    print("="*60)
    print("测试长期记忆检索功能")
    print("="*60)
    
    # 初始化向量数据库
    vector_store = VectorStoreManager(
        persist_directory="./data/chroma",
        embedding_type="fake"
    )
    
    # 测试查询
    test_queries = [
        "我的邮箱是什么",
        "邮箱地址",
        "发邮件",
        "123456789",
        "qq邮箱"
    ]
    
    user_id = "123456789"
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"查询: {query}")
        print('='*60)
        
        # 使用 get_relevant_context 方法（这是 butler.py 中使用的方法）
        context = vector_store.get_relevant_context(
            query=query,
            user_id=user_id,
            k=3
        )
        
        print(f"\n检索结果:")
        print(context)
        print()

if __name__ == "__main__":
    main()
