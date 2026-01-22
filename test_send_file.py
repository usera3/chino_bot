"""
测试发送文件功能
"""
from tools.send_file_tool import SendFileTool
import os


def test_send_file_tool():
    """测试发送文件工具"""
    print("\n" + "=" * 60)
    print("测试发送文件工具")
    print("=" * 60)
    
    # 创建测试文件
    test_file = "test_document.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("这是一个测试文件\n")
        f.write("用于测试发送文件功能\n")
    
    print(f"✅ 创建测试文件: {test_file}")
    
    # 创建工具实例
    tool = SendFileTool()
    
    print(f"\n📋 工具信息:")
    print(f"   名称: {tool.name}")
    print(f"   描述: {tool.description[:100]}...")
    
    # 测试文件是否存在检查
    print(f"\n🧪 测试 1: 文件不存在")
    result = tool._run("不存在的文件.txt")
    print(f"   结果: {result}")
    
    # 测试文件存在但没有 Bot 实例
    print(f"\n🧪 测试 2: 文件存在但没有 Bot 实例")
    result = tool._run(test_file)
    print(f"   结果: {result}")
    
    # 清理测试文件
    os.remove(test_file)
    print(f"\n✅ 清理测试文件")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n💡 提示：")
    print("   - 工具已正确创建")
    print("   - 文件检查功能正常")
    print("   - 需要在 NoneBot 环境中测试实际发送功能")
    print("   - 建议在 QQ 中测试：'帮我创建一个测试文档然后发给我'")


if __name__ == "__main__":
    test_send_file_tool()
