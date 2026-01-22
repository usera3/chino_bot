"""
测试测试工具
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.test_tools import RunTestsTool, GetErrorContextTool, AnalyzeTestCoverageTool


def test_run_tests_tool():
    """测试运行测试工具"""
    print("🧪 测试运行测试工具...")
    
    tool = RunTestsTool()
    
    # 测试运行单个测试文件
    result = tool._run("tests/test_code_analyzer.py")
    
    # 验证结果
    assert "🧪 测试执行结果" in result
    assert "测试路径" in result
    assert "测试统计" in result
    
    print("✅ 测试通过：运行测试工具")


def test_get_error_context_tool():
    """测试获取错误上下文工具"""
    print("🧪 测试获取错误上下文工具...")
    
    tool = GetErrorContextTool()
    
    # 测试获取错误上下文
    result = tool._run("core/code_analyzer.py", 50, 3)
    
    # 验证结果
    assert "🔍 错误上下文" in result
    assert "错误位置" in result
    assert "代码:" in result
    assert "50" in result
    
    print("✅ 测试通过：获取错误上下文工具")


def test_get_error_context_invalid_file():
    """测试获取错误上下文工具 - 无效文件"""
    print("🧪 测试获取错误上下文工具 - 无效文件...")
    
    tool = GetErrorContextTool()
    
    # 测试不存在的文件
    result = tool._run("nonexistent.py", 50)
    
    # 验证结果
    assert "❌" in result
    assert "不存在" in result
    
    print("✅ 测试通过：无效文件处理")


def test_get_error_context_invalid_line():
    """测试获取错误上下文工具 - 无效行号"""
    print("🧪 测试获取错误上下文工具 - 无效行号...")
    
    tool = GetErrorContextTool()
    
    # 测试无效行号
    result = tool._run("core/code_analyzer.py", 99999)
    
    # 验证结果
    assert "❌" in result
    assert "行号无效" in result
    
    print("✅ 测试通过：无效行号处理")


def test_analyze_test_coverage_tool():
    """测试分析测试覆盖率工具"""
    print("🧪 测试分析测试覆盖率工具...")
    
    tool = AnalyzeTestCoverageTool()
    
    # 测试分析测试覆盖率
    result = tool._run()
    
    # 验证结果
    assert "📊 测试覆盖率分析" in result
    assert "统计:" in result
    assert "代码文件:" in result
    assert "测试文件:" in result
    assert "覆盖率:" in result
    
    print("✅ 测试通过：分析测试覆盖率工具")


def test_tools_integration():
    """测试工具集成"""
    print("🧪 测试工具集成...")
    
    from tools.test_tools import get_test_tools
    
    tools = get_test_tools()
    
    # 验证工具数量
    assert len(tools) == 3
    
    # 验证工具名称
    tool_names = [tool.name for tool in tools]
    assert "run_tests" in tool_names
    assert "get_error_context" in tool_names
    assert "analyze_test_coverage" in tool_names
    
    print("✅ 测试通过：工具集成")


if __name__ == '__main__':
    print("🚀 开始测试测试工具\n")
    print("="*50)
    
    test_run_tests_tool()
    test_get_error_context_tool()
    test_get_error_context_invalid_file()
    test_get_error_context_invalid_line()
    test_analyze_test_coverage_tool()
    test_tools_integration()
    
    print("\n" + "="*50)
    print("✅ 所有测试通过！")
