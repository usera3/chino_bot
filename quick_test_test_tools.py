"""
快速测试测试工具集成
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.basic_tools import get_all_tools


def test_tools_loading():
    """测试工具加载"""
    print("🧪 测试工具加载...\n")
    
    tools = get_all_tools()
    
    # 查找测试工具
    test_tool_names = [
        'run_tests',
        'get_error_context',
        'analyze_test_coverage',
    ]
    
    found_tools = []
    for tool in tools:
        if tool.name in test_tool_names:
            found_tools.append(tool.name)
    
    print(f"\n📊 工具统计:")
    print(f"  - 总工具数: {len(tools)}")
    print(f"  - 测试工具: {len(found_tools)}/3")
    
    if len(found_tools) == 3:
        print("\n✅ 所有测试工具已成功加载！")
        return True
    else:
        print(f"\n❌ 缺少工具: {set(test_tool_names) - set(found_tools)}")
        return False


def test_run_tests():
    """测试运行测试"""
    print("\n" + "="*50)
    print("测试 1: 运行测试")
    print("="*50)
    
    from tools.test_tools import RunTestsTool
    
    tool = RunTestsTool()
    result = tool._run("tests/test_code_analyzer.py")
    
    print(result)
    
    if "🧪 测试执行结果" in result:
        print("\n✅ 测试通过")
        return True
    else:
        print("\n❌ 测试失败")
        return False


def test_get_error_context():
    """测试获取错误上下文"""
    print("\n" + "="*50)
    print("测试 2: 获取错误上下文")
    print("="*50)
    
    from tools.test_tools import GetErrorContextTool
    
    tool = GetErrorContextTool()
    result = tool._run("core/butler.py", 100, 5)
    
    print(result)
    
    if "🔍 错误上下文" in result:
        print("\n✅ 测试通过")
        return True
    else:
        print("\n❌ 测试失败")
        return False


def test_analyze_test_coverage():
    """测试分析测试覆盖率"""
    print("\n" + "="*50)
    print("测试 3: 分析测试覆盖率")
    print("="*50)
    
    from tools.test_tools import AnalyzeTestCoverageTool
    
    tool = AnalyzeTestCoverageTool()
    result = tool._run()
    
    print(result)
    
    if "📊 测试覆盖率分析" in result:
        print("\n✅ 测试通过")
        return True
    else:
        print("\n❌ 测试失败")
        return False


if __name__ == '__main__':
    print("🚀 开始测试测试工具集成\n")
    print("="*50)
    
    results = []
    
    # 测试 1：工具加载
    results.append(test_tools_loading())
    
    # 测试 2：运行测试
    results.append(test_run_tests())
    
    # 测试 3：获取错误上下文
    results.append(test_get_error_context())
    
    # 测试 4：分析测试覆盖率
    results.append(test_analyze_test_coverage())
    
    # 总结
    print("\n" + "="*50)
    print("📊 测试总结")
    print("="*50)
    print(f"通过: {sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 所有测试通过！测试工具已成功集成！")
    else:
        print("\n⚠️ 部分测试失败，请检查")
