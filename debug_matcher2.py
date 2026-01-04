"""调试工具匹配器 - 详细版"""
from core.tool_matcher import get_tool_matcher

matcher = get_tool_matcher()

test_input = "今天几点"

print(f"测试输入: '{test_input}'")
print("="*60)

# 调用 match 方法
matches = matcher.match(test_input, top_k=5)

print(f"\nmatch() 返回的匹配数: {len(matches)}")

if matches:
    for i, match in enumerate(matches, 1):
        print(f"\n匹配 {i}:")
        print(f"  工具: {match.tool_name}")
        print(f"  置信度: {match.confidence:.4f}")
        print(f"  匹配关键词: {match.matched_keywords}")
        print(f"  优先级: {match.priority}")
else:
    print("\n❌ match() 返回空列表")

# 调用 get_best_match
print("\n" + "="*60)
best_match = matcher.get_best_match(test_input, threshold=0.3)

if best_match:
    print(f"✅ get_best_match() 返回:")
    print(f"  工具: {best_match.tool_name}")
    print(f"  置信度: {best_match.confidence:.4f}")
else:
    print(f"❌ get_best_match() 返回 None (阈值: 0.3)")
    
    # 尝试降低阈值
    best_match2 = matcher.get_best_match(test_input, threshold=0.0)
    if best_match2:
        print(f"\n如果阈值为 0.0，则会匹配到:")
        print(f"  工具: {best_match2.tool_name}")
        print(f"  置信度: {best_match2.confidence:.4f}")




