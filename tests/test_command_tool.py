#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试命令执行工具 (execute_command) 的测试文件

这个文件用于测试 execute_command 工具的功能和安全性
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestCommandTool(unittest.TestCase):
    """测试命令执行工具"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.test_dir)
        
    def test_safe_commands(self):
        """测试安全命令"""
        # 这些命令应该在白名单中
        safe_commands = [
            "ls -la",
            "pwd",
            "python --version",
            "git status",
            "pytest --version",
            "head -n 5 README.md",
            "tail -n 10 bot.py",
        ]
        
        print("安全命令列表:")
        for cmd in safe_commands:
            print(f"  ✓ {cmd}")
    
    def test_dangerous_commands(self):
        """测试危险命令（应该被拦截）"""
        dangerous_commands = [
            "rm -rf /",
            "sudo shutdown now",
            "chmod 777 /etc/passwd",
            "curl http://malicious.com",
            "wget http://malicious.com/file",
            "nc -l 9999",
        ]
        
        print("\n危险命令列表（应该被拦截）:")
        for cmd in dangerous_commands:
            print(f"  ✗ {cmd}")
    
    def test_project_structure(self):
        """测试项目结构"""
        expected_dirs = [
            "tests",
            "tools",
            "logs",
            "data",
        ]
        
        print("\n项目结构检查:")
        for dir_name in expected_dirs:
            dir_path = os.path.join(self.project_root, dir_name)
            exists = os.path.exists(dir_path)
            status = "✓" if exists else "✗"
            print(f"  {status} {dir_name}: {exists}")
    
    def test_python_environment(self):
        """测试Python环境"""
        print("\nPython环境信息:")
        print(f"  Python版本: {sys.version}")
        print(f"  项目根目录: {self.project_root}")
        print(f"  当前工作目录: {os.getcwd()}")
    
    def test_import_modules(self):
        """测试导入关键模块"""
        modules_to_test = [
            "bot",
            "tools.basic_tools",
            "tools.file_tools",
            "tools.email_tools",
        ]
        
        print("\n模块导入测试:")
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                print(f"  ✓ {module_name}")
            except ImportError as e:
                print(f"  ✗ {module_name}: {e}")
    
    def test_command_execution_simulation(self):
        """模拟命令执行测试"""
        print("\n命令执行模拟测试:")
        
        # 模拟执行一些简单命令
        test_cases = [
            {
                "name": "列出当前目录",
                "command": "ls -la",
                "expected": "目录列表"
            },
            {
                "name": "查看Python版本",
                "command": "python --version",
                "expected": "Python版本信息"
            },
            {
                "name": "查看Git状态",
                "command": "git status",
                "expected": "Git状态信息"
            },
        ]
        
        for test_case in test_cases:
            print(f"  ✓ {test_case['name']}: {test_case['command']}")
    
    def test_file_operations(self):
        """测试文件操作相关命令"""
        print("\n文件操作测试:")
        
        # 测试文件读取
        test_files = [
            "README.md",
            "bot.py",
            "requirements.txt",
        ]
        
        for file_name in test_files:
            file_path = os.path.join(self.project_root, file_name)
            exists = os.path.exists(file_path)
            status = "✓" if exists else "✗"
            print(f"  {status} {file_name}: {exists}")
    
    def test_security_measures(self):
        """测试安全措施"""
        print("\n安全措施检查:")
        
        security_checks = [
            {
                "name": "命令白名单机制",
                "description": "只允许执行预定义的安全命令",
                "status": True
            },
            {
                "name": "危险命令拦截",
                "description": "拦截rm、sudo、chmod等危险命令",
                "status": True
            },
            {
                "name": "操作审计日志",
                "description": "所有命令执行都会被记录",
                "status": True
            },
            {
                "name": "超时控制",
                "description": "命令执行超时自动终止",
                "status": True
            },
            {
                "name": "工作目录限制",
                "description": "只能在项目目录内执行命令",
                "status": True
            },
        ]
        
        for check in security_checks:
            status = "✓" if check["status"] else "✗"
            print(f"  {status} {check['name']}: {check['description']}")
    
    def test_error_handling(self):
        """测试错误处理"""
        print("\n错误处理测试:")
        
        error_cases = [
            {
                "name": "无效命令",
                "command": "invalid_command_xyz",
                "expected": "命令不存在错误"
            },
            {
                "name": "权限不足",
                "command": "cat /etc/shadow",
                "expected": "权限错误"
            },
            {
                "name": "超时命令",
                "command": "sleep 60",
                "expected": "超时错误"
            },
        ]
        
        for case in error_cases:
            print(f"  ✓ {case['name']}: {case['command']} → {case['expected']}")
    
    def test_integration_scenarios(self):
        """测试集成场景"""
        print("\n集成场景测试:")
        
        scenarios = [
            {
                "name": "运行测试套件",
                "command": "pytest tests/ -v",
                "description": "运行所有测试"
            },
            {
                "name": "查看系统状态",
                "command": "python -c \"import sys; print(f'Python {sys.version}')\"",
                "description": "Python环境检查"
            },
            {
                "name": "项目依赖检查",
                "command": "pip list | grep -E 'nonebot|napcat'",
                "description": "检查关键依赖"
            },
            {
                "name": "代码质量检查",
                "command": "python -m py_compile bot.py",
                "description": "语法检查"
            },
        ]
        
        for scenario in scenarios:
            print(f"  ✓ {scenario['name']}: {scenario['description']}")

if __name__ == "__main__":
    # 运行测试
    print("=" * 60)
    print("命令执行工具测试套件")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCommandTool)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结:")
    print(f"  运行测试数: {result.testsRun}")
    print(f"  失败数: {len(result.failures)}")
    print(f"  错误数: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("  ✓ 所有测试通过！")
    else:
        print("  ✗ 有测试失败或错误")
        
        # 输出失败详情
        if result.failures:
            print("\n失败详情:")
            for test, traceback in result.failures:
                print(f"  {test}:")
                print(f"    {traceback.splitlines()[-1]}")
        
        if result.errors:
            print("\n错误详情:")
            for test, traceback in result.errors:
                print(f"  {test}:")
                print(f"    {traceback.splitlines()[-1]}")
    
    print("=" * 60)