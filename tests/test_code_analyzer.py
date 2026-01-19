"""
测试代码分析器
"""
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.code_analyzer import CodeAnalyzer


def test_analyze_simple_file():
    """测试分析简单文件"""
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def hello():
    '''Say hello'''
    return "Hello"

class MyClass:
    '''My class'''
    def method1(self):
        pass
    
    def method2(self):
        pass
""")
        temp_file = f.name
    
    try:
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(temp_file)
        
        # 验证结果
        assert 'classes' in result
        assert 'functions' in result
        assert 'imports' in result
        
        # 验证类
        assert len(result['classes']) == 1
        assert result['classes'][0]['name'] == 'MyClass'
        assert len(result['classes'][0]['methods']) == 2
        
        # 验证函数
        assert len(result['functions']) == 1
        assert result['functions'][0]['name'] == 'hello'
        
        print("✅ 测试通过：分析简单文件")
    
    finally:
        os.unlink(temp_file)


def test_extract_imports():
    """测试提取导入"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import os
import sys
from pathlib import Path
from typing import Dict, List
""")
        temp_file = f.name
    
    try:
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(temp_file)
        
        # 验证导入
        imports = result['imports']
        assert len(imports) >= 4
        
        # 验证 import 语句
        import_modules = [imp['module'] for imp in imports if imp['type'] == 'import']
        assert 'os' in import_modules
        assert 'sys' in import_modules
        
        # 验证 from 语句
        from_modules = [imp['module'] for imp in imports if imp['type'] == 'from']
        assert 'pathlib' in from_modules
        assert 'typing' in from_modules
        
        print("✅ 测试通过：提取导入")
    
    finally:
        os.unlink(temp_file)


def test_calculate_complexity():
    """测试计算复杂度"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def complex_function(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                print(i)
    else:
        while x < 0:
            x += 1
    return x
""")
        temp_file = f.name
    
    try:
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(temp_file)
        
        # 验证复杂度
        assert 'complexity' in result
        assert result['complexity'] > 1  # 有多个分支
        
        print(f"✅ 测试通过：计算复杂度 = {result['complexity']}")
    
    finally:
        os.unlink(temp_file)


def test_find_definition():
    """测试查找定义"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def my_function():
    '''My function'''
    return 42

class MyClass:
    '''My class'''
    def my_method(self):
        pass
""")
        temp_file = f.name
    
    try:
        analyzer = CodeAnalyzer()
        
        # 查找函数
        func_def = analyzer.find_definition(temp_file, 'my_function', 'function')
        assert func_def is not None
        assert func_def['type'] == 'function'
        assert func_def['name'] == 'my_function'
        assert 'code' in func_def
        
        # 查找类
        class_def = analyzer.find_definition(temp_file, 'MyClass', 'class')
        assert class_def is not None
        assert class_def['type'] == 'class'
        assert class_def['name'] == 'MyClass'
        
        print("✅ 测试通过：查找定义")
    
    finally:
        os.unlink(temp_file)


def test_syntax_error_handling():
    """测试语法错误处理"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
def broken_function(
    # 缺少闭合括号
    return 42
""")
        temp_file = f.name
    
    try:
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(temp_file)
        
        # 验证错误处理
        assert 'error' in result
        assert '语法错误' in result['error']
        
        print("✅ 测试通过：语法错误处理")
    
    finally:
        os.unlink(temp_file)


def test_analyze_real_file():
    """测试分析真实文件"""
    # 分析 code_analyzer.py 自己
    analyzer_file = project_root / 'core' / 'code_analyzer.py'
    
    if analyzer_file.exists():
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(str(analyzer_file))
        
        # 验证结果
        assert 'classes' in result
        assert 'functions' in result
        
        # 应该有 CodeAnalyzer 类
        class_names = [c['name'] for c in result['classes']]
        assert 'CodeAnalyzer' in class_names
        
        # 打印结果
        print(f"\n📊 分析结果：{analyzer_file.name}")
        print(f"  - 类数量: {len(result['classes'])}")
        print(f"  - 函数数量: {len(result['functions'])}")
        print(f"  - 导入数量: {len(result['imports'])}")
        print(f"  - 代码行数: {result['lines']}")
        print(f"  - 复杂度: {result['complexity']}")
        
        print("✅ 测试通过：分析真实文件")


if __name__ == '__main__':
    print("🧪 开始测试代码分析器...\n")
    
    test_analyze_simple_file()
    test_extract_imports()
    test_calculate_complexity()
    test_find_definition()
    test_syntax_error_handling()
    test_analyze_real_file()
    
    print("\n✅ 所有测试通过！")
