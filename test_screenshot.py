"""测试网页截图功能"""
from tools.screenshot_tool import WebScreenshotTool

def test_screenshot():
    """测试截图功能"""
    print("=" * 60)
    print("📸 测试网页截图功能")
    print("=" * 60)
    
    tool = WebScreenshotTool()
    
    # 测试 1：截取百度首页
    print("\n【测试 1】截取百度首页")
    print("-" * 60)
    result = tool._run(
        url="https://www.baidu.com",
        full_page=True,
        width=1920,
        height=1080
    )
    print(result)
    
    # 测试 2：截取 GitHub 首页（仅可见区域）
    print("\n【测试 2】截取 GitHub 首页（仅可见区域）")
    print("-" * 60)
    result = tool._run(
        url="https://github.com",
        full_page=False,
        width=1920,
        height=1080
    )
    print(result)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_screenshot()
