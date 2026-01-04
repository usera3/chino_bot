"""调试工具匹配器"""
from core.tool_matcher import get_tool_matcher

matcher = get_tool_matcher()

# 检查关键词索引
print("🔍 检查关键词索引（前20个）:")
for i, (keyword, tools) in enumerate(list(matcher.keyword_to_tools.items())[:20]):
    print(f"{i+1}. 关键词: '{keyword}' -> 工具: {tools}")

print("\n" + "="*60)

# 测试一个简单的例子
user_input = "今天几点"
user_input_lower = user_input.lower()
print(f"\n用户输入: '{user_input}'")
print(f"小写后: '{user_input_lower}'")

print(f"\n检查关键词 '几点' 是否在索引中: {'几点' in matcher.keyword_to_tools}")
print(f"检查关键词 '时间' 是否在索引中: {'时间' in matcher.keyword_to_tools}")

# 手动检查匹配
print("\n手动检查匹配:")
for keyword, tool_list in matcher.keyword_to_tools.items():
    if keyword in user_input_lower:
        print(f"✅ 匹配到关键词: '{keyword}' -> 工具: {tool_list}")




