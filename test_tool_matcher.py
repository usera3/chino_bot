"""测试工具匹配器"""
from core.tool_matcher import get_tool_matcher

def test_matcher():
    matcher = get_tool_matcher()
    
    test_cases = [
        # 时间相关
        "现在几点",
        "今天星期几",
        "今天几号",
        
        # 搜索相关
        "搜索今日新闻",
        "今日道琼斯指数",
        "比特币价格",
        "查一下最新AI研究",
        
        # 用户信息
        "我的QQ号是多少",
        "我叫什么",
        "这个群叫什么名字",
        
        # 计算
        "帮我算 123+456",
        "100乘以50等于多少",
        
        # 天气
        "北京天气怎么样",
        "上海今天冷不冷",
        
        # 闲聊（不应匹配）
        "你好",
        "我今天心情不好",
        "Python是什么语言"
    ]
    
    print("🔍 测试工具匹配器\n" + "="*60)
    
    for user_input in test_cases:
        print(f"\n用户输入: \"{user_input}\"")
        match = matcher.get_best_match(user_input, threshold=0.3)
        
        if match:
            print(f"✅ 匹配到: {match.tool_name}")
            print(f"   置信度: {match.confidence:.2%}")
            print(f"   关键词: {', '.join(match.matched_keywords)}")
        else:
            print("❌ 未匹配到任何工具（闲聊）")

if __name__ == "__main__":
    test_matcher()




