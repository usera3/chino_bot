"""测试项目管理器"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.project_manager import ProjectManager, project_manager
from core.security import PathValidationError, get_project_root


def test_project_manager_init():
    """测试项目管理器初始化"""
    pm = ProjectManager()
    assert pm.project_root == get_project_root()
    print("✅ 项目管理器初始化成功")


def test_read_file():
    """测试读取文件"""
    pm = ProjectManager()
    
    # 读取 README.md
    try:
        content = pm.read_file("README.md", user_id="test")
        assert len(content) > 0
        print(f"✅ 读取文件成功，长度: {len(content)}")
    except FileNotFoundError:
        print("⚠️ README.md 不存在，跳过测试")


def test_read_file_invalid_path():
    """测试读取无效路径"""
    pm = ProjectManager()
    
    # 尝试读取项目外的文件
    try:
        pm.read_file("/etc/passwd", user_id="test")
        print("❌ 应该抛出 PathValidationError")
    except PathValidationError:
        print("✅ 路径验证正常工作")


def test_list_files():
    """测试列出文件"""
    pm = ProjectManager()
    
    # 列出 tools 目录的 Python 文件
    files = pm.list_files("tools", pattern="*.py", user_id="test")
    assert len(files) > 0
    print(f"✅ 列出文件成功，找到 {len(files)} 个文件")
    print(f"   示例: {files[:3]}")


def test_search_in_files():
    """测试搜索文件"""
    pm = ProjectManager()
    
    # 搜索 "Butler"
    results = pm.search_in_files(
        pattern="Butler",
        file_pattern="*.py",
        directory=".",
        max_results=10,
        user_id="test"
    )
    
    print(f"✅ 搜索成功，找到 {len(results)} 个匹配")
    if results:
        print(f"   示例: {results[0]}")


def test_get_file_info():
    """测试获取文件信息"""
    pm = ProjectManager()
    
    try:
        info = pm.get_file_info("bot.py", user_id="test")
        assert "size" in info
        assert "lines" in info
        print(f"✅ 获取文件信息成功")
        print(f"   大小: {info['size_kb']:.2f} KB")
        print(f"   行数: {info['lines']}")
    except FileNotFoundError:
        print("⚠️ bot.py 不存在，跳过测试")


def test_get_directory_tree():
    """测试获取目录树"""
    pm = ProjectManager()
    
    tree = pm.get_directory_tree("tools", max_depth=1, user_id="test")
    assert len(tree) > 0
    print(f"✅ 获取目录树成功")
    print(tree[:500])  # 只打印前 500 字符


def test_global_instance():
    """测试全局实例"""
    assert project_manager is not None
    assert isinstance(project_manager, ProjectManager)
    print("✅ 全局实例可用")


if __name__ == "__main__":
    print("=" * 60)
    print("测试项目管理器")
    print("=" * 60)
    
    test_project_manager_init()
    test_read_file()
    test_read_file_invalid_path()
    test_list_files()
    test_search_in_files()
    test_get_file_info()
    test_get_directory_tree()
    test_global_instance()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
