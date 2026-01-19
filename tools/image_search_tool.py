"""图片搜索工具 - 基于 Pexels API"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import os
import requests
import base64
from pathlib import Path


class ImageSearchInput(BaseModel):
    """图片搜索输入"""
    query: str = Field(
        description="搜索关键词，例如：猫、风景、美食、sunset、nature 等"
    )
    count: int = Field(
        default=1,
        description="返回图片数量，默认 1 张，最多 5 张"
    )


class ImageSearchTool(BaseTool):
    """图片搜索工具 - 从网上搜索并下载图片
    
    使用场景：
    - 用户说"帮我找一张猫的图片"
    - 用户说"搜索风景图片"
    - 用户说"给我看看美食图片"
    
    AI 的职责：
    1. 理解用户的搜索需求
    2. 提取搜索关键词
    3. 调用此工具搜索图片
    4. 图片会自动下载并发送给用户
    """
    
    name: str = "search_image"
    description: str = """从网上搜索图片并发送给用户。

⚠️ 使用规则：
1. 当用户要求搜索、查找、看图片时使用
2. 自动提取搜索关键词（支持中英文）
3. 图片会自动下载并发送到 QQ

✅ 适用场景：
- "帮我找一张猫的图片" → 搜索 "cat"
- "搜索风景图片" → 搜索 "landscape"
- "给我看看美食" → 搜索 "food"
- "找一张日落的照片" → 搜索 "sunset"

❌ 不适用场景：
- 用户要求画图 → 使用 render_html 工具
- 用户要求生成图片 → 使用 render_html 工具"""
    
    args_schema: type[BaseModel] = ImageSearchInput
    
    def _run(self, query: str, count: int = 1) -> str:
        """执行工具（同步版本，内部调用异步）"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            result = loop.run_until_complete(self._arun(query, count))
            return result
        except Exception as e:
            return f"❌ 图片搜索失败：{str(e)}"
    
    async def _arun(self, query: str, count: int = 1) -> str:
        """异步执行工具"""
        try:
            # 限制数量
            count = max(1, min(5, count))
            
            # 获取 API Key
            api_key = os.getenv("PEXELS_API_KEY")
            if not api_key:
                return """❌ 图片搜索功能未配置

请在 .env 文件中添加：
PEXELS_API_KEY=your_api_key

获取免费 API Key：
1. 访问 https://www.pexels.com/api/
2. 注册账号
3. 创建 API Key（完全免费）"""
            
            # 调用 Pexels API（添加随机页码，避免每次返回相同图片）
            import random
            random_page = random.randint(1, 10)  # 随机选择 1-10 页
            
            headers = {
                "Authorization": api_key
            }
            params = {
                "query": query,
                "per_page": count,
                "page": random_page  # 使用随机页码
            }
            
            response = requests.get(
                "https://api.pexels.com/v1/search",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return f"❌ 图片搜索失败：API 返回错误 {response.status_code}"
            
            data = response.json()
            photos = data.get("photos", [])
            
            if not photos:
                return f"❌ 没有找到关于 '{query}' 的图片，试试其他关键词吧"
            
            # 下载并发送图片
            from .qq_interaction_tools import get_bot_instance, get_current_context
            from nonebot.adapters.onebot.v11 import MessageSegment
            
            bot = get_bot_instance()
            context = get_current_context()
            
            if not bot or not context:
                # 没有 Bot 实例，只返回图片链接
                result = f"✅ 找到 {len(photos)} 张关于 '{query}' 的图片：\n\n"
                for i, photo in enumerate(photos, 1):
                    result += f"{i}. {photo['src']['large']}\n"
                    result += f"   摄影师：{photo['photographer']}\n\n"
                return result
            
            # 下载并发送图片
            sent_count = 0
            for photo in photos:
                try:
                    # 下载图片（使用中等尺寸）
                    image_url = photo['src']['large']
                    image_response = requests.get(image_url, timeout=10)
                    
                    if image_response.status_code == 200:
                        # 使用 base64 编码发送
                        image_base64 = base64.b64encode(image_response.content).decode()
                        image_msg = MessageSegment.image(f"base64://{image_base64}")
                        
                        # 判断是群聊还是私聊
                        if context.get("group_id"):
                            await bot.send_group_msg(
                                group_id=int(context["group_id"]),
                                message=image_msg
                            )
                        else:
                            await bot.send_private_msg(
                                user_id=int(context["user_id"]),
                                message=image_msg
                            )
                        
                        sent_count += 1
                
                except Exception as send_error:
                    continue  # 跳过失败的图片
            
            if sent_count > 0:
                return f"""✅ 已发送 {sent_count} 张关于 '{query}' 的图片！
📸 图片来源：Pexels（免费高质量图片库）"""
            else:
                return f"❌ 图片下载失败，请稍后重试"
            
        except requests.exceptions.Timeout:
            return "❌ 图片搜索超时，请检查网络连接"
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return f"❌ 图片搜索失败：{str(e)}\n\n详细错误：{error_detail[:200]}"


# 创建工具实例
image_search_tool = ImageSearchTool()
