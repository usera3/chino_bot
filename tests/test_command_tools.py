"""
命令执行工具综合测试
测试 execute_command 工具的各种功能
"""
import os
import sys
import json

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.command_tool import ExecuteCommandTool


def test_basic_ls():
    """测试基本的 ls 命令"""
    print("\n" + "="*60)
    print("测试 1: 基本 ls 命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 执行 ls 命令
    result = tool._run("ls")
    print(f"结果: {result[:200]}...")
    
    assert "✅" in result or "⚠️" in result
    assert "bot.py" in result or "tools" in result or "tests" in result
    print("✅ 基本 ls 命令测试通过")


def test_ls_with_options():
    """测试带选项的 ls 命令"""
    print("\n" + "="*60)
    print("测试 2: ls -la 命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 执行 ls -la 命令
    result = tool._run("ls -la")
    print(f"结果长度: {len(result)} 字符")
    
    assert "✅" in result or "⚠️" in result
    assert "total" in result or "drwx" in result or "-rw" in result
    print("✅ ls -la 命令测试通过")


def test_cat_file():
    """测试 cat 命令读取文件"""
    print("\n" + "="*60)
    print("测试 3: cat README.md")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 执行 cat README.md
    result = tool._run("cat README.md")
    print(f"结果长度: {len(result)} 字符")
    
    assert "✅" in result or "⚠️" in result
    assert "智乃" in result or "Chino" in result or "README" in result
    print("✅ cat 命令测试通过")


def test_grep_search():
    """测试 grep 搜索"""
    print("\n" + "="*60)
    print("测试 4: grep 搜索")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 执行 grep 搜索
    result = tool._run("grep -r 'def test' tests/")
    print(f"结果: {result[:300]}...")
    
    assert "✅" in result or "⚠️" in result
    print("✅ grep 搜索测试通过")


def test_find_files():
    """测试 find 命令"""
    print("\n" + "="*60)
    print("测试 5: find 查找文件")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 执行 find 命令
    result = tool._run("find . -name '*.py' -maxdepth 2")
    print(f"结果: {result[:300]}...")
    
    assert "✅" in result or "⚠️" in result
    assert ".py" in result
    print("✅ find 命令测试通过")


def test_pwd_command():
    """测试 pwd 命令"""
    print("\n" + "="*60)
    print("测试 6: pwd 命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 执行 pwd 命令
    result = tool._run("pwd")
    print(f"结果: {result}")
    
    assert "✅" in result or "⚠️" in result
    assert "/" in result
    print("✅ pwd 命令测试通过")


def test_python_commands():
    """测试 Python 相关命令"""
    print("\n" + "="*60)
    print("测试 7: Python 命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试 python --version
    result1 = tool._run("python --version")
    print(f"Python 版本: {result1}")
    
    # 测试 python -c 执行简单代码
    result2 = tool._run("python -c \"print('Hello from Python test')\"")
    print(f"Python 代码执行: {result2}")
    
    assert "✅" in result1 or "⚠️" in result1 or "Python" in result1
    assert "Hello from Python test" in result2 or "✅" in result2 or "⚠️" in result2
    print("✅ Python 命令测试通过")


def test_pip_commands():
    """测试 pip 命令"""
    print("\n" + "="*60)
    print("测试 8: pip 命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试 pip list
    result = tool._run("pip list")
    print(f"pip list 结果长度: {len(result)} 字符")
    
    assert "✅" in result or "⚠️" in result
    print("✅ pip 命令测试通过")


def test_git_commands():
    """测试 Git 命令"""
    print("\n" + "="*60)
    print("测试 9: Git 命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试 git status
    result1 = tool._run("git status")
    print(f"git status 结果长度: {len(result1)} 字符")
    
    # 测试 git log --oneline -5
    result2 = tool._run("git log --oneline -5")
    print(f"git log 结果: {result2[:200]}...")
    
    assert "✅" in result1 or "⚠️" in result1
    assert "✅" in result2 or "⚠️" in result2
    print("✅ Git 命令测试通过")


def test_pytest_commands():
    """测试 pytest 命令"""
    print("\n" + "="*60)
    print("测试 10: pytest 命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试 pytest --help
    result = tool._run("pytest --help")
    print(f"pytest --help 结果长度: {len(result)} 字符")
    
    assert "✅" in result or "⚠️" in result or "pytest" in result
    print("✅ pytest 命令测试通过")


def test_dangerous_commands():
    """测试危险命令拦截"""
    print("\n" + "="*60)
    print("测试 11: 危险命令拦截")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试 rm 命令
    result1 = tool._run("rm -rf /tmp/test")
    print(f"rm 命令结果: {result1}")
    
    # 测试 sudo 命令
    result2 = tool._run("sudo ls")
    print(f"sudo 命令结果: {result2}")
    
    # 测试 curl 命令
    result3 = tool._run("curl https://example.com")
    print(f"curl 命令结果: {result3}")
    
    # 测试 wget 命令
    result4 = tool._run("wget https://example.com")
    print(f"wget 命令结果: {result4}")
    
    assert "❌" in result1
    assert "危险命令" in result1 or "不在白名单" in result1
    assert "❌" in result2
    assert "❌" in result3
    assert "❌" in result4
    print("✅ 危险命令拦截测试通过")


def test_working_directory_param():
    """测试工作目录参数"""
    print("\n" + "="*60)
    print("测试 12: 工作目录参数")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 在 tools 目录执行 ls
    result = tool._run("ls", working_dir="tools")
    print(f"tools 目录内容: {result[:200]}...")
    
    assert "✅" in result or "⚠️" in result
    assert "basic_tools.py" in result or "code_tools.py" in result
    print("✅ 工作目录参数测试通过")


def test_timeout_param():
    """测试超时参数"""
    print("\n" + "="*60)
    print("测试 13: 超时参数")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 执行一个快速命令，设置超时
    result = tool._run("echo 'test timeout'", timeout=5)
    print(f"超时测试结果: {result}")
    
    assert "✅" in result or "⚠️" in result
    assert "test timeout" in result
    print("✅ 超时参数测试通过")


def test_execute_command_tool_integration():
    """测试 execute_command 工具集成"""
    print("\n" + "="*60)
    print("测试 14: execute_command 工具集成")
    print("="*60)
    
    # 模拟 execute_command 工具调用
    from tools.command_tool import execute_command
    
    # 创建参数
    params = {
        "command": "ls -la",
        "working_dir": ".",
        "timeout": 30
    }
    
    # 执行命令
    result = execute_command(**params)
    print(f"execute_command 结果类型: {type(result)}")
    print(f"结果长度: {len(str(result))} 字符")
    
    assert isinstance(result, str)
    assert len(result) > 0
    print("✅ execute_command 工具集成测试通过")


def test_command_with_spaces():
    """测试带空格的命令"""
    print("\n" + "="*60)
    print("测试 15: 带空格的命令")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试带引号的命令
    result = tool._run("echo 'Hello World with spaces'")
    print(f"带空格命令结果: {result}")
    
    assert "✅" in result or "⚠️" in result
    assert "Hello World with spaces" in result
    print("✅ 带空格命令测试通过")


def test_multiple_commands():
    """测试多个命令组合"""
    print("\n" + "="*60)
    print("测试 16: 多个命令组合")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试多个命令用分号分隔
    result = tool._run("pwd; ls -la | head -5")
    print(f"多个命令结果: {result[:300]}...")
    
    assert "✅" in result or "⚠️" in result
    print("✅ 多个命令组合测试通过")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("测试 17: 错误处理")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试不存在的命令
    result = tool._run("nonexistentcommand12345")
    print(f"不存在的命令结果: {result}")
    
    assert "❌" in result or "错误" in result or "失败" in result
    print("✅ 错误处理测试通过")


def test_whitelist_validation():
    """测试白名单验证"""
    print("\n" + "="*60)
    print("测试 18: 白名单验证")
    print("="*60)
    
    tool = ExecuteCommandTool()
    
    # 测试白名单中的命令
    whitelist_commands = ["ls", "cat", "grep", "find", "pwd", "python", "pip", "git", "pytest"]
    
    for cmd in whitelist_commands[:3]:  # 只测试前3个，避免太多输出
        result = tool._run(f"{cmd} --help" if cmd != "pwd" else cmd)
        print(f"{cmd} 命令结果: {result[:100]}...")
        assert "❌" not in result or "危险命令" not in result
    
    print("✅ 白名单验证测试通过")


if __name__ == "__main__":
    print("🚀 开始综合测试命令执行工具...")
    
    tests = [
        test_basic_ls,
        test_ls_with_options,
        test_cat_file,
        test_grep_search,
        test_find_files,
        test_pwd_command,
        test_python_commands,
        test_pip_commands,
        test_git_commands,
        test_pytest_commands,
        test_dangerous_commands,
        test_working_directory_param,
        test_timeout_param,
        test_execute_command_tool_integration,
        test_command_with_spaces,
        test_multiple_commands,
        test_error_handling,
        test_whitelist_validation,
    ]
    
    passed = 0
    failed = 0
    
    for i, test_func in enumerate(tests, 1):
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ 测试 {i} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"📊 测试结果: 通过 {passed}/{len(tests)}，失败 {failed}/{len(tests)}")
    print("="*60)
    
    if failed == 0:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  有 {failed} 个测试失败")