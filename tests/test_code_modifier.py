"""
测试代码修改器
"""
import pytest
from core.code_modifier import CodeModifier


@pytest.fixture
def modifier():
    """创建代码修改器实例"""
    return CodeModifier()


class TestDiffGeneration:
    """测试 diff 生成"""
    
    def test_generate_unified_diff(self, modifier):
        """测试生成 unified diff"""
        original = """def hello():
    print("Hello")
"""
        
        modified = """def hello():
    print("Hello, World!")
"""
        
        diff = modifier.generate_diff(original, modified, "test.py")
        
        assert "---" in diff
        assert "+++" in diff
        assert "@@" in diff
        assert "-    print(\"Hello\")" in diff
        assert "+    print(\"Hello, World!\")" in diff
    
    def test_no_changes(self, modifier):
        """测试没有变化时"""
        code = """def hello():
    print("Hello")
"""
        
        diff = modifier.generate_diff(code, code, "test.py")
        
        assert diff == ""
    
    def test_multiple_changes(self, modifier):
        """测试多处变化"""
        original = """def func1():
    pass

def func2():
    pass
"""
        
        modified = """def func1():
    print("Changed")

def func2():
    print("Also changed")
"""
        
        diff = modifier.generate_diff(original, modified, "test.py")
        
        assert diff != ""
        assert "func1" in diff
        assert "func2" in diff


class TestCodeFormatting:
    """测试代码格式化"""
    
    def test_format_python_basic(self, modifier):
        """测试基本 Python 格式化"""
        code = """def hello(  ):
\tprint( "Hello" )
"""
        
        success, formatted, error = modifier.format_code(code, "python")
        
        assert success
        assert error == ""
        # 检查缩进被转换为空格
        assert '\t' not in formatted
    
    def test_format_invalid_language(self, modifier):
        """测试不支持的语言"""
        code = "some code"
        
        success, formatted, error = modifier.format_code(code, "unknown")
        
        assert not success
        assert "不支持的语言" in error
    
    def test_simple_format_removes_trailing_spaces(self, modifier):
        """测试移除行尾空格"""
        code = "def hello():   \n    pass   \n"
        
        success, formatted, error = modifier._simple_format_python(code)
        
        assert success
        # 检查行尾空格被移除
        lines = formatted.splitlines()
        for line in lines:
            assert line == line.rstrip()


class TestSyntaxValidation:
    """测试语法验证"""
    
    def test_valid_python_syntax(self, modifier):
        """测试有效的 Python 语法"""
        code = """def hello():
    print("Hello")
"""
        
        is_valid, error = modifier.validate_syntax(code, "python")
        
        assert is_valid
        assert error == ""
    
    def test_invalid_python_syntax(self, modifier):
        """测试无效的 Python 语法"""
        code = """def hello()
    print("Hello")
"""
        
        is_valid, error = modifier.validate_syntax(code, "python")
        
        assert not is_valid
        assert "语法错误" in error
    
    def test_invalid_language(self, modifier):
        """测试不支持的语言"""
        code = "some code"
        
        is_valid, error = modifier.validate_syntax(code, "unknown")
        
        assert not is_valid
        assert "不支持的语言" in error


class TestChangeExtraction:
    """测试更改提取"""
    
    def test_extract_changes(self, modifier):
        """测试提取更改信息"""
        original = """line 1
line 2
line 3
"""
        
        modified = """line 1
line 2 modified
line 3
line 4
"""
        
        diff = modifier.generate_diff(original, modified, "test.txt")
        changes = modifier.extract_changes(diff)
        
        assert changes["additions"] > 0
        assert changes["deletions"] > 0
        assert len(changes["hunks"]) > 0
    
    def test_extract_no_changes(self, modifier):
        """测试没有变化时"""
        code = "line 1\nline 2\n"
        
        diff = modifier.generate_diff(code, code, "test.txt")
        changes = modifier.extract_changes(diff)
        
        assert changes["additions"] == 0
        assert changes["deletions"] == 0
        assert len(changes["hunks"]) == 0


class TestBackup:
    """测试备份功能"""
    
    def test_create_backup_nonexistent_file(self, modifier):
        """测试备份不存在的文件"""
        success, backup_path, error = modifier.create_backup("nonexistent.txt")
        
        assert not success
        assert "文件不存在" in error


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
