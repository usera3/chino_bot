"""
代码操作工具测试
"""
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.code_tools import (
    ReadProjectFileTool,
    WriteProjectFileTool,
    ListProjectFilesTool,
    SearchInFilesTool,
    GetDirectoryTreeTool,
)


def test_read_file():
    """测试读取文件"""
    print("\n" + "="*60)
    print("测试 1: 读取文件")
    print("="*60)
    
    tool = ReadProjectFileTool()
    
    # 读取 bot.py
    result = tool._run("bot.py")
    print(result)
    
    assert "bot.py" in result
    assert "📁 文件:" in result
    print("✅ 读取文件测试通过")


def test_list_files():
    """测试列出文件"""
    print("\n" + "="*60)
    print("测试 2: 列出文件")
    print("="*60)
    
    tool = ListProjectFilesTool()
    
    # 列出 tools 目录的 Python 文件
    result = tool._run(directory="tools", pattern="*.py", recursive=False)
    print(result)
    
    assert "tools" in result
    assert "basic_tools.py" in result
    print("✅ 列出文件测试通过")


def test_search_in_files():
    """测试搜索文件"""
    print("\n" + "="*60)
    print("测试 3: 搜索文件")
    print("="*60)
    
    tool = SearchInFilesTool()
    
    # 搜索 "Butler"
    result = tool._run(pattern="Butler", file_pattern="*.py", directory="core", max_results=5)
    print(result)
    
    assert "Butler" in result or "没有找到" in result
    print("✅ 搜索文件测试通过")


def test_get_directory_tree():
    """测试获取目录树"""
    print("\n" + "="*60)
    print("测试 4: 获取目录树")
    print("="*60)
    
    tool = GetDirectoryTreeTool()
    
    # 获取 tools 目录树
    result = tool._run(directory="tools", max_depth=1)
    print(result)
    
    assert "tools" in result
    print("✅ 获取目录树测试通过")


def test_write_file():
    """测试写入文件（需要管理员权限）"""
    print("\n" + "="*60)
    print("测试 5: 写入文件（需要管理员权限）")
    print("="*60)
    
    tool = WriteProjectFileTool()
    
    # 创建测试文件
    test_content = """# 测试文件
print("Hello, World!")
"""
    
    result = tool._run(file_path="test_code_tools_temp.py", content=test_content)
    print(result)
    
    # 验证文件是否创建
    if "✅" in result:
        # 读取文件验证
        read_tool = ReadProjectFileTool()
        read_result = read_tool._run("test_code_tools_temp.py")
        assert "Hello, World!" in read_result
        
        # 删除测试文件
        import os
        test_file = os.path.join(project_root, "test_code_tools_temp.py")
        if os.path.exists(test_file):
            os.remove(test_file)
            print("✅ 测试文件已删除")
        
        print("✅ 写入文件测试通过")
    else:
        print("⚠️ 写入文件需要管理员权限，跳过测试")


def test_security():
    """测试安全限制"""
    print("\n" + "="*60)
    print("测试 6: 安全限制")
    print("="*60)
    
    tool = ReadProjectFileTool()
    
    # 尝试读取项目外的文件
    result = tool._run("../../etc/passwd")
    print(result)
    
    assert "❌" in result
    assert "路径验证失败" in result or "不在项目内" in result
    print("✅ 安全限制测试通过")


if __name__ == "__main__":
    print("🚀 开始测试代码操作工具...")
    
    try:
        test_read_file()
        test_list_files()
        test_search_in_files()
        test_get_directory_tree()
        test_write_file()
        test_security()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
