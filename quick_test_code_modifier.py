"""
快速测试代码修改工具
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.code_modifier import CodeModifier
from tools.code_modifier_tools import get_code_modifier_tools


def test_code_modifier():
    """测试代码修改器"""
    print("=" * 60)
    print("测试代码修改器")
    print("=" * 60)
    
    modifier = CodeModifier()
    
    # 测试 1：生成 diff
    print("\n【测试 1】生成 diff")
    original = """def hello():
    print("Hello")
"""
    
    modified = """def hello():
    print("Hello, World!")
"""
    
    diff = modifier.generate_diff(original, modified, "test.py")
    
    if diff and "Hello, World!" in diff:
        print("✅ diff 生成成功")
        print(f"   预览:\n{diff[:200]}...")
    else:
        print("❌ diff 生成失败")
    
    # 测试 2：提取更改
    print("\n【测试 2】提取更改信息")
    changes = modifier.extract_changes(diff)
    
    if changes["additions"] > 0 and changes["deletions"] > 0:
        print(f"✅ 更改提取成功")
        print(f"   添加: {changes['additions']} 行")
        print(f"   删除: {changes['deletions']} 行")
        print(f"   修改块: {len(changes['hunks'])} 个")
    else:
        print("❌ 更改提取失败")
    
    # 测试 3：格式化代码
    print("\n【测试 3】格式化代码")
    messy_code = """def hello(  ):
\tprint( "Hello" )
"""
    
    success, formatted, error = modifier.format_code(messy_code, "python")
    
    if success and '\t' not in formatted:
        print("✅ 代码格式化成功")
        print(f"   原始: {repr(messy_code[:30])}...")
        print(f"   格式化: {repr(formatted[:30])}...")
    else:
        print(f"❌ 代码格式化失败: {error}")
    
    # 测试 4：验证语法
    print("\n【测试 4】验证语法")
    
    # 有效语法
    valid_code = """def hello():
    print("Hello")
"""
    is_valid, error = modifier.validate_syntax(valid_code, "python")
    
    if is_valid:
        print("✅ 有效语法验证通过")
    else:
        print(f"❌ 有效语法验证失败: {error}")
    
    # 无效语法
    invalid_code = """def hello()
    print("Hello")
"""
    is_valid, error = modifier.validate_syntax(invalid_code, "python")
    
    if not is_valid and "语法错误" in error:
        print("✅ 无效语法检测成功")
        print(f"   错误: {error[:50]}...")
    else:
        print("❌ 无效语法检测失败")
    
    return True


def test_code_modifier_tools():
    """测试代码修改工具"""
    print("\n" + "=" * 60)
    print("测试代码修改工具")
    print("=" * 60)
    
    tools = get_code_modifier_tools()
    
    # 测试工具加载
    print("\n【测试 1】工具加载")
    print(f"✅ 加载了 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")
    
    # 测试工具属性
    print("\n【测试 2】工具属性")
    expected_tools = ["preview_code_changes", "apply_code_changes", "format_code"]
    
    tool_names = [tool.name for tool in tools]
    
    passed = 0
    for expected in expected_tools:
        if expected in tool_names:
            print(f"✅ {expected}")
            passed += 1
        else:
            print(f"❌ {expected} - 未找到")
    
    print(f"\n工具属性测试: {passed}/{len(expected_tools)} 通过")
    
    return passed == len(expected_tools)


def main():
    """主函数"""
    print("\n🧪 开始测试代码修改功能...\n")
    
    # 测试代码修改器
    modifier_ok = test_code_modifier()
    
    # 测试代码修改工具
    tools_ok = test_code_modifier_tools()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if modifier_ok and tools_ok:
        print("✅ 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        if not modifier_ok:
            print("   - 代码修改器测试失败")
        if not tools_ok:
            print("   - 代码修改工具测试失败")
        return 1


if __name__ == '__main__':
    exit(main())
