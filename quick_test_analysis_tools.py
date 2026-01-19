"""
快速测试代码分析工具集成
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
    
    # 查找代码分析工具
    analysis_tool_names = [
        'analyze_code_structure',
        'get_function_definition',
        'analyze_dependencies',
    ]
    
    found_tools = []
    for tool in tools:
        if tool.name in analysis_tool_names:
            found_tools.append(tool.name)
    
    print(f"\n📊 工具统计:")
    print(f"  - 总工具数: {len(tools)}")
    print(f"  - 代码分析工具: {len(found_tools)}/3")
    
    if len(found_tools) == 3:
        print("\n✅ 所有代码分析工具已成功加载！")
        return True
    else:
        print(f"\n❌ 缺少工具: {set(analysis_tool_names) - set(found_tools)}")
        return False


def test_analyze_code_structure():
    """测试分析代码结构"""
    print("\n" + "="*50)
    print("测试 1: 分析代码结构")
    print("="*50)
    
    from tools.analysis_tools import AnalyzeCodeStructureTool
    
    tool = AnalyzeCodeStructureTool()
    result = tool._run("core/butler.py")
    
    print(result[:800] + "...")  # 只显示前 800 字符
    
    if "📊 代码结构分析" in result:
        print("\n✅ 测试通过")
        return True
    else:
        print("\n❌ 测试失败")
        return False


def test_get_function_definition():
    """测试获取函数定义"""
    print("\n" + "="*50)
    print("测试 2: 获取函数定义")
    print("="*50)
    
    from tools.analysis_tools import GetFunctionDefinitionTool
    
    tool = GetFunctionDefinitionTool()
    result = tool._run("core/butler.py", "Butler", "class")
    
    print(result[:500] + "...")  # 只显示前 500 字符
    
    if "🔍 定义查找" in result:
        print("\n✅ 测试通过")
        return True
    else:
        print("\n❌ 测试失败")
        return False


def test_analyze_dependencies():
    """测试分析依赖"""
    print("\n" + "="*50)
    print("测试 3: 分析依赖")
    print("="*50)
    
    from tools.analysis_tools import AnalyzeDependenciesTool
    
    tool = AnalyzeDependenciesTool()
    result = tool._run("bot.py")
    
    print(result)
    
    if "📦 依赖分析" in result:
        print("\n✅ 测试通过")
        return True
    else:
        print("\n❌ 测试失败")
        return False


if __name__ == '__main__':
    print("🚀 开始测试代码分析工具集成\n")
    print("="*50)
    
    results = []
    
    # 测试 1：工具加载
    results.append(test_tools_loading())
    
    # 测试 2：分析代码结构
    results.append(test_analyze_code_structure())
    
    # 测试 3：获取函数定义
    results.append(test_get_function_definition())
    
    # 测试 4：分析依赖
    results.append(test_analyze_dependencies())
    
    # 总结
    print("\n" + "="*50)
    print("📊 测试总结")
    print("="*50)
    print(f"通过: {sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 所有测试通过！代码分析工具已成功集成！")
    else:
        print("\n⚠️ 部分测试失败，请检查")
