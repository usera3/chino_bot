"""测试双向量库记忆系统"""
import os
os.environ['DASHSCOPE_API_KEY'] = open('.env').read().split('DASHSCOPE_API_KEY=')[1].split('\n')[0]

from langchain_community.chat_models import ChatTongyi
from core.dual_vector_store import DualVectorStore
from core.knowledge_extractor import KnowledgeExtractor


def test_dual_memory():
    """测试双向量库"""
    print("="*60)
    print("测试双向量库记忆系统")
    print("="*60)
    
    # 初始化
    llm = ChatTongyi(model="qwen-plus")
    vector_store = DualVectorStore(
        persist_directory="./data/dual_test",
        embedding_type="fake"
    )
    extractor = KnowledgeExtractor(llm)
    
    user_id = "test_user_001"
    
    # 模拟对话
    conversations = [
        ("你好", "你好呀~ (｡･ω･｡)ﾉ♡"),
        ("我叫张三", "你好张三！很高兴认识你"),
        ("我的邮箱是 zhangsan@qq.com", "好的，记住你的邮箱了"),
        ("我喜欢吃火锅", "火锅啊...听起来很好吃呢"),
        ("我住在北京", "北京是个好地方呢"),
        ("今天天气怎么样", "我不太清楚呢，要不要我帮你查查？"),
        ("不用了", "好的~"),
    ]
    
    print("\n📝 添加对话并提取知识...")
    for user_input, bot_response in conversations:
        print(f"\n用户: {user_input}")
        print(f"智乃: {bot_response}")
        
        # 1. 添加到对话库
        vector_store.add_conversation(user_input, bot_response, user_id)
        
        # 2. 提取知识
        knowledge = extractor.extract_knowledge(user_input, bot_response, user_id)
        if knowledge:
            print(f"✅ 提取到知识: {knowledge}")
            vector_store.add_knowledge(knowledge, user_id)
    
    # 测试检索
    print("\n" + "="*60)
    print("测试检索")
    print("="*60)
    
    # 测试1：检索邮箱
    print("\n【测试1】用户问：你还记得我的邮箱吗？")
    context = vector_store.get_relevant_context(
        query="邮箱 email",
        user_id=user_id,
        k_conversations=3,
        k_knowledge=2
    )
    print(f"\n检索结果:\n{context}")
    
    # 测试2：检索偏好
    print("\n【测试2】用户问：我喜欢吃什么？")
    context = vector_store.get_relevant_context(
        query="喜欢吃 食物",
        user_id=user_id,
        k_conversations=3,
        k_knowledge=2
    )
    print(f"\n检索结果:\n{context}")
    
    # 测试3：检索个人信息
    print("\n【测试3】用户问：我是谁？")
    context = vector_store.get_relevant_context(
        query="我是谁 姓名",
        user_id=user_id,
        k_conversations=3,
        k_knowledge=2
    )
    print(f"\n检索结果:\n{context}")
    
    # 统计信息
    print("\n" + "="*60)
    stats = vector_store.get_stats()
    print(f"📊 统计信息:")
    print(f"   对话数: {stats['conversations']}")
    print(f"   知识数: {stats['knowledge']}")
    print("="*60)


if __name__ == "__main__":
    test_dual_memory()
