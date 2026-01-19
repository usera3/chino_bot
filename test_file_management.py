"""测试文件管理功能"""
from tools.file_management_tool import DeleteFileTool, CleanTempFilesTool
from tools.screenshot_tool import WebScreenshotTool
import os

def test_file_management():
    """测试文件管理功能"""
    print("=" * 60)
    print("🗑️ 测试文件管理功能")
    print("=" * 60)
    
    # 先创建一个测试截图
    print("\n【步骤 1】创建测试截图")
    print("-" * 60)
    screenshot_tool = WebScreenshotTool()
    result = screenshot_tool._run(url="https://www.baidu.com", full_page=False)
    print(result)
    
    # 从结果中提取文件路径
    import re
    match = re.search(r'文件：(.+\.png)', result)
    if not match:
        print("❌ 无法提取文件路径")
        return
    
    file_path = match.group(1)
    print(f"\n📁 提取到文件路径：{file_path}")
    
    # 测试删除单个文件
    print("\n【步骤 2】删除单个文件")
    print("-" * 60)
    delete_tool = DeleteFileTool()
    result = delete_tool._run(file_path=file_path)
    print(result)
    
    # 验证文件是否被删除
    if os.path.exists(file_path):
        print("❌ 文件仍然存在")
    else:
        print("✅ 文件已成功删除")
    
    # 创建多个测试截图
    print("\n【步骤 3】创建多个测试截图")
    print("-" * 60)
    for i in range(3):
        result = screenshot_tool._run(url="https://www.baidu.com", full_page=False)
        print(f"截图 {i+1} 完成")
    
    # 测试批量清理
    print("\n【步骤 4】批量清理截图文件")
    print("-" * 60)
    clean_tool = CleanTempFilesTool()
    result = clean_tool._run(pattern="screenshot_*.png")
    print(result)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_file_management()
