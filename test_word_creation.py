"""
测试 Word 文档创建功能
"""
from tools.document_tools import CreateWordTool
import os


def test_word_creation():
    """测试 Word 文档创建"""
    print("\n" + "=" * 60)
    print("测试 Word 文档创建功能")
    print("=" * 60)
    
    # 创建工具实例
    tool = CreateWordTool()
    
    print(f"\n📋 工具信息:")
    print(f"   名称: {tool.name}")
    print(f"   描述: {tool.description[:80]}...")
    
    # 测试创建 Word 文档
    print(f"\n🧪 测试: 创建 Word 文档")
    
    test_file = "测试文档.docx"
    test_title = "测试文档标题"
    test_content = """这是一个测试文档。

第一段：测试段落内容。

第二段：验证 Word 文档创建功能。

第三段：检查 lxml 依赖是否正常。

结束。"""
    
    result = tool._run(
        file_path=test_file,
        title=test_title,
        content=test_content
    )
    
    print(f"\n📤 结果:")
    print(result)
    
    # 检查文件是否创建
    if os.path.exists(test_file):
        file_size = os.path.getsize(test_file)
        print(f"\n✅ 文件已创建:")
        print(f"   路径: {test_file}")
        print(f"   大小: {file_size / 1024:.2f} KB")
        
        # 清理测试文件
        os.remove(test_file)
        print(f"\n🧹 已清理测试文件")
    else:
        print(f"\n❌ 文件未创建")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_word_creation()
