"""查看长期记忆数据库中的内容"""
from core.vector_store import VectorStoreManager

def main():
    # 初始化向量数据库
    print("📚 正在加载长期记忆数据库...")
    vector_store = VectorStoreManager(
        persist_directory="./data/chroma",
        embedding_type="fake"
    )
    
    # 获取统计信息
    stats = vector_store.get_stats()
    print(f"\n📊 统计信息:")
    print(f"   总对话数: {stats['total_conversations']}")
    print(f"   存储路径: {stats['persist_directory']}")
    
    # 获取所有记忆（通过搜索空字符串）
    print(f"\n🔍 查询用户 1446437177 的所有记忆...")
    
    # 尝试搜索一些常见关键词
    keywords = ["邮箱", "email", "吃饭", "提醒", ""]
    
    for keyword in keywords:
        print(f"\n{'='*60}")
        print(f"关键词: '{keyword}'")
        print('='*60)
        
        results = vector_store.search_similar_conversations(
            query=keyword if keyword else "用户",
            user_id="1446437177",
            k=10  # 获取最多10条
        )
        
        if results:
            print(f"找到 {len(results)} 条相关记忆:\n")
            for i, doc in enumerate(results, 1):
                print(f"[{i}] {doc.metadata.get('timestamp', '未知时间')}")
                print(f"    {doc.page_content}")
                print()
        else:
            print("没有找到相关记忆")
        
        if keyword == "":
            break  # 空关键词已经返回所有结果，不需要继续

if __name__ == "__main__":
    main()
