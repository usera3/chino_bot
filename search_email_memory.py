"""搜索包含邮箱地址的记忆"""
from core.vector_store import VectorStoreManager

def main():
    vector_store = VectorStoreManager(
        persist_directory="./data/chroma",
        embedding_type="fake"
    )
    
    # 搜索包含邮箱关键词的记忆
    queries = [
        "123456789@qq.com",
        "qq号加qq邮箱后缀",
        "我的邮箱就是我qq号",
        "地址就是我qq号加上qq邮箱的后缀"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"搜索: {query}")
        print('='*60)
        
        results = vector_store.search_similar_conversations(
            query=query,
            user_id="123456789",
            k=5
        )
        
        if results:
            for i, doc in enumerate(results, 1):
                print(f"\n[{i}] {doc.metadata.get('timestamp', '未知时间')}")
                print(f"用户输入: {doc.metadata.get('user_input', 'N/A')}")
                print(f"机器人回复: {doc.metadata.get('bot_response', 'N/A')}")
        else:
            print("没有找到")

if __name__ == "__main__":
    main()
