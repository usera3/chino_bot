"""
网页截图工具
使用 Playwright 截取网页截图
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import os


# ==================== 网页截图工具 ====================
class WebScreenshotInput(BaseModel):
    """网页截图输入"""
    url: str = Field(description="要截图的网页 URL，必须包含 http:// 或 https://")
    full_page: bool = Field(default=True, description="是否截取整个页面（True）还是仅可见区域（False），默认 True")
    width: int = Field(default=1920, description="浏览器窗口宽度，默认 1920")
    height: int = Field(default=1080, description="浏览器窗口高度，默认 1080")


class WebScreenshotTool(BaseTool):
    """网页截图工具"""
    name: str = "web_screenshot"
    description: str = """截取指定网页的截图。

使用场景：
- 用户说"截图这个网页"
- 用户说"帮我看看这个网站长什么样"
- 用户发送链接并要求截图
- 用户说"给我截个图"

参数：
- url: 网页 URL（必需，必须包含 http:// 或 https://）
- full_page: 是否截取整个页面（可选，默认 True）
- width: 浏览器窗口宽度（可选，默认 1920）
- height: 浏览器窗口高度（可选，默认 1080）

返回：截图文件路径

⚠️ 重要提示：
- 截图会保存到 Downloads 目录
- 建议发送图片后使用 delete_file 工具删除，节省空间
- 工作流：web_screenshot → send_image/send_file → delete_file"""
    args_schema: type[BaseModel] = WebScreenshotInput

    def _run(self, url: str, full_page: bool = True, width: int = 1920, height: int = 1080) -> str:
        """执行工具"""
        try:
            from playwright.sync_api import sync_playwright
            import time

            # 验证 URL
            if not url.startswith(('http://', 'https://')):
                return f"❌ URL 格式错误：必须以 http:// 或 https:// 开头"

            # 生成文件名
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"

            # 保存到 Downloads 目录（NapCat 可访问）
            downloads_dir = os.path.expanduser("~/Downloads")
            filepath = os.path.join(downloads_dir, filename)

            print(f"📸 正在截图: {url}")
            print(f"💾 保存路径: {filepath}")

            # 使用 Playwright 截图
            with sync_playwright() as p:
                # 获取代理配置
                use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
                proxy_config = None
                if use_proxy:
                    http_proxy = os.getenv("HTTP_PROXY", "")
                    if http_proxy:
                        proxy_config = {
                            'server': http_proxy
                        }
                        print(f"🌐 使用代理: {http_proxy}")

                # 启动浏览器（使用 chromium）
                browser = p.chromium.launch(
                    headless=True,  # 无头模式
                    args=['--no-sandbox', '--disable-setuid-sandbox'],
                    proxy=proxy_config  # 添加代理配置
                )

                # 创建上下文和页面
                context = browser.new_context(
                    viewport={'width': width, 'height': height},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )

                page = context.new_page()

                # 访问网页
                try:
                    page.goto(url, wait_until='networkidle', timeout=30000)
                except Exception as e:
                    browser.close()
                    return f"❌ 无法访问网页：{str(e)}"

                # 等待页面加载
                page.wait_for_timeout(2000)  # 额外等待 2 秒确保内容加载

                # 截图
                page.screenshot(
                    path=filepath,
                    full_page=full_page
                )

                # 关闭浏览器
                browser.close()

            # 检查文件是否生成
            if not os.path.exists(filepath):
                return f"❌ 截图失败：文件未生成"

            # 获取文件大小
            file_size = os.path.getsize(filepath)
            file_size_kb = file_size / 1024

            return f"""✅ 网页截图成功！
🌐 URL：{url}
📁 文件：{filepath}
📊 大小：{file_size_kb:.2f} KB
📏 尺寸：{width}x{height}
📄 模式：{'整页' if full_page else '可见区域'}

💡 提示：截图已保存到 Downloads 目录，可以直接发送给用户"""

        except ImportError:
            return """❌ 缺少依赖库：playwright

请安装 playwright：
1. pip install playwright
2. playwright install chromium

或者运行：
poetry add playwright
poetry run playwright install chromium"""

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ 截图失败：{str(e)}"

    async def _arun(self, url: str, full_page: bool = True, width: int = 1920, height: int = 1080) -> str:
        """异步执行"""
        try:
            from playwright.async_api import async_playwright
            import time

            # 验证 URL
            if not url.startswith(('http://', 'https://')):
                return f"❌ URL 格式错误：必须以 http:// 或 https:// 开头"

            # 生成文件名
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"

            # 保存到 Downloads 目录（NapCat 可访问）
            downloads_dir = os.path.expanduser("~/Downloads")
            filepath = os.path.join(downloads_dir, filename)

            print(f"📸 正在截图: {url}")
            print(f"💾 保存路径: {filepath}")

            # 使用 Playwright 截图
            async with async_playwright() as p:
                # 获取代理配置
                use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
                proxy_config = None
                if use_proxy:
                    http_proxy = os.getenv("HTTP_PROXY", "")
                    if http_proxy:
                        proxy_config = {
                            'server': http_proxy
                        }
                        print(f"🌐 使用代理: {http_proxy}")

                # 启动浏览器（使用 chromium）
                browser = await p.chromium.launch(
                    headless=True,  # 无头模式
                    args=['--no-sandbox', '--disable-setuid-sandbox'],
                    proxy=proxy_config  # 添加代理配置
                )

                # 创建上下文和页面
                context = await browser.new_context(
                    viewport={'width': width, 'height': height},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )

                page = await context.new_page()

                # 访问网页
                try:
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                except Exception as e:
                    await browser.close()
                    return f"❌ 无法访问网页：{str(e)}"

                # 等待页面加载
                await page.wait_for_timeout(2000)  # 额外等待 2 秒确保内容加载

                # 截图
                await page.screenshot(
                    path=filepath,
                    full_page=full_page
                )

                # 关闭浏览器
                await browser.close()

            # 检查文件是否生成
            if not os.path.exists(filepath):
                return f"❌ 截图失败：文件未生成"

            # 获取文件大小
            file_size = os.path.getsize(filepath)
            file_size_kb = file_size / 1024

            return f"""✅ 网页截图成功！
🌐 URL：{url}
📁 文件：{filepath}
📊 大小：{file_size_kb:.2f} KB
📏 尺寸：{width}x{height}
📄 模式：{'整页' if full_page else '可见区域'}

💡 提示：截图已保存到 Downloads 目录，可以直接发送给用户"""

        except ImportError:
            return """❌ 缺少依赖库：playwright

请安装 playwright：
1. pip install playwright
2. playwright install chromium

或者运行：
poetry add playwright
poetry run playwright install chromium"""

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ 截图失败：{str(e)}"


# ==================== 工具列表 ====================
def get_screenshot_tool():
    """获取截图工具"""
    return WebScreenshotTool()
