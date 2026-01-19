"""HTML 渲染工具 - 将 HTML/CSS 代码渲染成图片"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import os
from pathlib import Path


class HtmlRenderInput(BaseModel):
    """HTML 渲染输入"""
    html_code: str = Field(
        description="""完整的 HTML 代码，必须包含 <html>、<head>、<body> 标签。
        
示例：
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .heart {
            width: 100px;
            height: 100px;
            background: red;
            position: relative;
            transform: rotate(-45deg);
        }
        .heart::before,
        .heart::after {
            content: "";
            width: 100px;
            height: 100px;
            background: red;
            border-radius: 50%;
            position: absolute;
        }
        .heart::before {
            top: -50px;
            left: 0;
        }
        .heart::after {
            left: 50px;
            top: 0;
        }
    </style>
</head>
<body>
    <div class="heart"></div>
</body>
</html>
```"""
    )
    width: int = Field(
        default=800,
        description="图片宽度（像素），默认 800"
    )
    height: int = Field(
        default=600,
        description="图片高度（像素），默认 600"
    )


class HtmlRenderTool(BaseTool):
    """HTML 渲染工具 - 将 HTML/CSS 代码渲染成图片
    
    使用场景：
    - 用户说"帮我画一个红色的爱心"
    - 用户说"生成一个数据统计图表"
    - 用户说"做一张生日贺卡"
    - 用户说"画一个笑脸"
    
    AI 的职责：
    1. 理解用户的描述
    2. 生成完整的 HTML/CSS 代码（必须包含 <html>、<head>、<body> 标签）
    3. 调用此工具渲染成图片
    4. 图片会自动发送给用户
    """
    
    name: str = "render_html"
    description: str = """将 HTML/CSS 代码渲染成图片并发送给用户。

⚠️ 使用规则：
1. 必须生成完整的 HTML 代码（包含 <!DOCTYPE html>、<html>、<head>、<body>）
2. CSS 样式写在 <style> 标签内
3. 适合绘制：图形、图表、卡片、装饰图等
4. 图片会自动保存并返回文件路径

✅ 适用场景：
- "帮我画一个红色的爱心" → 生成爱心形状的 HTML/CSS
- "生成一个数据统计图表" → 生成图表的 HTML/CSS
- "做一张生日贺卡" → 生成贺卡的 HTML/CSS
- "画一个笑脸" → 生成笑脸的 HTML/CSS

❌ 不适用场景：
- 复杂的数据可视化（建议使用专业图表库）
- 需要交互的内容（这是静态图片）"""
    
    args_schema: type[BaseModel] = HtmlRenderInput
    
    def _run(self, html_code: str, width: int = 800, height: int = 600) -> str:
        """执行工具（同步版本，内部调用异步）"""
        try:
            # 在同步环境中运行异步代码
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建新的任务
                import nest_asyncio
                nest_asyncio.apply()
            
            result = loop.run_until_complete(self._arun(html_code, width, height))
            return result
        except Exception as e:
            return f"❌ HTML 渲染失败：{str(e)}"
    
    async def _arun(self, html_code: str, width: int = 800, height: int = 600) -> str:
        """异步执行工具"""
        try:
            from nonebot_plugin_htmlrender import html_to_pic
            from nonebot.adapters.onebot.v11 import MessageSegment
            from .qq_interaction_tools import get_bot_instance, get_current_context
            
            # 渲染 HTML 为图片
            image_bytes = await html_to_pic(
                html=html_code,
                viewport={"width": width, "height": height},
                type="png",
                device_scale_factor=2,  # 2倍清晰度
                wait=500,  # 等待 500ms 确保渲染完成
            )
            
            # 保存图片到临时目录
            temp_dir = Path("./data/temp_images")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            import time
            filename = f"render_{int(time.time() * 1000)}.png"
            image_path = temp_dir / filename
            
            # 保存图片
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            # 尝试发送图片到 QQ
            bot = get_bot_instance()
            context = get_current_context()
            
            if bot and context:
                try:
                    # 使用 base64 编码发送图片（更可靠）
                    import base64
                    with open(image_path, "rb") as f:
                        image_base64 = base64.b64encode(f.read()).decode()
                    
                    image_msg = MessageSegment.image(f"base64://{image_base64}")
                    
                    # 判断是群聊还是私聊
                    if context.get("group_id"):
                        # 群聊
                        await bot.send_group_msg(
                            group_id=int(context["group_id"]),
                            message=image_msg
                        )
                    else:
                        # 私聊
                        await bot.send_private_msg(
                            user_id=int(context["user_id"]),
                            message=image_msg
                        )
                    
                    # 发送成功后删除图片，节省磁盘空间
                    try:
                        import os
                        os.remove(image_path)
                    except Exception as del_error:
                        pass  # 删除失败不影响主流程
                    
                    return f"""✅ HTML 渲染成功并已发送！
📏 尺寸：{width}x{height}
💾 大小：{len(image_bytes) / 1024:.2f} KB"""
                    
                except Exception as send_error:
                    import traceback
                    error_detail = traceback.format_exc()
                    # 发送失败，保留图片
                    return f"""✅ HTML 渲染成功！
📏 尺寸：{width}x{height}
💾 大小：{len(image_bytes) / 1024:.2f} KB
📁 图片路径：{image_path}

⚠️ 图片发送失败：{str(send_error)}
详细错误：{error_detail[:200]}"""
            else:
                # 没有 Bot 实例，只保存图片
                return f"""✅ HTML 渲染成功！
📁 图片路径：{image_path}
📏 尺寸：{width}x{height}
💾 大小：{len(image_bytes) / 1024:.2f} KB

图片已保存，可以发送给用户了！"""
            
        except ImportError:
            return "❌ HTML 渲染功能未安装，请先安装 nonebot-plugin-htmlrender"
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return f"❌ HTML 渲染失败：{str(e)}\n\n详细错误：\n{error_detail}"


# 创建工具实例
html_render_tool = HtmlRenderTool()
