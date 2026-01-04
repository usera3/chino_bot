"""
图片搜索工具 - 搜索网络上的图片
支持 Google Images (SerpAPI) 和 Unsplash 两种搜索方式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any, Optional
from nonebot.log import logger
import httpx


class ImageSearchTool(BaseTool):
    """
    图片搜索工具
    优先使用 Google Images (SerpAPI)，降级到 Unsplash
    """
    
    # 国内可能无法访问的域名黑名单
    BLOCKED_DOMAINS = [
        'aljazeera.net',
        'bbc.co.uk',
        'bbci.co.uk',
        'brookings.edu',
        'nytimes.com',
        'wsj.com',
        'reuters.com',
        'theguardian.com',
        'cnn.com',
        'facebook.com',
        'twitter.com',
        'instagram.com',
        'youtube.com',
        'google.com/images',  # Google自己的图片
        'gstatic.com',
        'wikipedia.org',
    ]
    
    def __init__(self):
        """初始化图片搜索工具"""
        super().__init__()
        
        # SerpAPI 配置（Google Images）
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        self.serpapi_url = "https://serpapi.com/search.json"
        
        # Unsplash API 配置（备用）
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        self.unsplash_url = "https://api.unsplash.com/search/photos"
        
        if self.serpapi_key:
            logger.success("✅ Google 图片搜索工具初始化完成 (SerpAPI)")
        elif self.unsplash_key:
            logger.success("✅ Unsplash 图片搜索工具初始化完成 (备用)")
        else:
            logger.warning("⚠️ 图片搜索API未配置")
            logger.info("💡 获取 SerpAPI: https://serpapi.com (推荐)")
            logger.info("💡 获取 Unsplash: https://unsplash.com/developers (备用)")
    
    def get_name(self) -> str:
        return "search_images"
    
    def get_description(self) -> str:
        return "搜索网络上的图片（使用Google Images）。当用户要求'搜索XXX图片'、'找一张XXX的照片'、'给我看看XXX的图'时使用。返回真实的网络图片URL"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "图片搜索关键词，支持中英文。如：'猫'、'日落'、'城市夜景'、'咖啡'"
                },
                "count": {
                    "type": "integer",
                    "description": "返回图片数量（1-5），默认3张",
                    "default": 3
                }
            },
            "required": ["keyword"]
        }
    
    def _is_url_accessible(self, url: str) -> bool:
        """检查URL是否可能在国内访问（基于域名黑名单）"""
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 检查是否在黑名单中
            for blocked_domain in self.BLOCKED_DOMAINS:
                if blocked_domain in domain:
                    logger.debug(f"⚠️ 过滤不可访问域名: {domain}")
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"URL解析失败: {url}, {e}")
            return True  # 解析失败时默认允许
    
    async def execute(
        self, 
        keyword: str = None,
        keywords: str = None,
        query: str = None,
        count: int = 3
    ) -> ToolResult:
        """
        执行图片搜索
        
        Args:
            keyword: 搜索关键词（兼容参数）
            keywords: 搜索关键词（兼容参数，复数形式）
            query: 搜索关键词（兼容参数）
            count: 返回图片数量
        
        Returns:
            ToolResult: 搜索结果（包含图片URL列表）
        """
        # 兼容三种参数名（keyword, keywords, query）
        search_query = keyword or keywords or query
        if not search_query:
            return ToolResult(
                success=False,
                message="缺少搜索关键词",
                error="MISSING_KEYWORD"
            )
        query = search_query
        if not self.is_available():
            return ToolResult(
                success=False,
                message="图片搜索功能不可用（API密钥未配置）",
                error="API_NOT_CONFIGURED"
            )
        
        # 限制数量
        count = min(max(count, 1), 5)
        
        # 优先使用 SerpAPI (Google Images)
        if self.serpapi_key:
            return await self._search_with_serpapi(query, count)
        # 降级到 Unsplash
        elif self.unsplash_key:
            return await self._search_with_unsplash(query, count)
        else:
            return ToolResult(
                success=False,
                message="图片搜索功能不可用",
                error="NO_API_KEY"
            )
    
    async def _search_with_serpapi(self, query: str, count: int) -> ToolResult:
        """使用 SerpAPI 搜索 Google Images"""
        try:
            import random
            
            logger.info(f"🔍 Google 图片搜索: {query} (数量: {count})")
            
            # 🎲 添加随机偏移量，让每次搜索返回不同的图片
            # Google Images 每页最多100张，我们随机选择起始位置
            random_start = random.randint(0, 10) * 10  # 0, 10, 20, ..., 100
            
            # 多获取一些图片（count * 3），然后随机选择
            fetch_count = min(count * 3, 30)  # 最多获取30张
            
            params = {
                "engine": "google_images",
                "q": query,
                "api_key": self.serpapi_key,
                "num": fetch_count,
                "ijn": str(random_start // 100)  # 页数（每页100张）
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.serpapi_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    images_results = data.get("images_results", [])
                    
                    if not images_results:
                        logger.warning(f"⚠️ 未找到'{query}'相关的图片")
                        return ToolResult(
                            success=True,
                            data={"query": query, "images": []},
                            message=f"未找到'{query}'相关的图片"
                        )
                    
                    # 🎲 随机打乱并选择指定数量的图片
                    import random
                    
                    # 🔒 先过滤掉不可访问的域名
                    accessible_results = [
                        img for img in images_results 
                        if self._is_url_accessible(img.get("original", ""))
                    ]
                    
                    if not accessible_results:
                        logger.warning(f"⚠️ 所有图片均被过滤（不可访问域名），使用原始结果")
                        accessible_results = images_results
                    else:
                        logger.info(f"🔒 过滤后剩余 {len(accessible_results)}/{len(images_results)} 张可访问图片")
                    
                    # 随机选择
                    shuffled_results = random.sample(accessible_results, min(len(accessible_results), fetch_count))
                    selected_results = shuffled_results[:count]
                    
                    logger.info(f"🎲 从 {len(accessible_results)} 张图片中随机选择 {len(selected_results)} 张")
                    
                    # 格式化结果
                    images = []
                    for idx, img in enumerate(selected_results, 1):
                        original_url = img.get("original", "")
                        thumbnail_url = img.get("thumbnail", "")
                        title = img.get("title", "")
                        source = img.get("source", "")
                        
                        images.append({
                            "url": original_url,
                            "thumb_url": thumbnail_url,
                            "title": title,
                            "source": source,
                            "index": idx
                        })
                    
                    # 构建回复
                    message_parts = [f"🔍 找到 {len(images)} 张'{query}'相关图片（Google Images）：\n"]
                    for img in images:
                        title_text = f"：{img['title'][:30]}..." if img['title'] else ""
                        message_parts.append(f"{img['index']}. 图片{title_text}")
                        if img['source']:
                            message_parts.append(f"   来源：{img['source']}")
                        message_parts.append(f"   🔗 {img['url']}")
                    
                    result_message = "\n".join(message_parts)
                    
                    logger.success(f"✅ Google 图片搜索成功，找到 {len(images)} 张图片")
                    
                    return ToolResult(
                        success=True,
                        data={
                            "query": query,
                            "images": images,
                            "count": len(images),
                            "source": "google"
                        },
                        message=result_message
                    )
                
                else:
                    logger.error(f"❌ SerpAPI错误: {response.status_code}")
                    # 降级到 Unsplash
                    if self.unsplash_key:
                        logger.info("⚠️ 降级使用 Unsplash 搜索")
                        return await self._search_with_unsplash(query, count)
                    return ToolResult(
                        success=False,
                        message="图片搜索失败",
                        error=f"SERPAPI_ERROR_{response.status_code}"
                    )
        
        except Exception as e:
            logger.error(f"❌ SerpAPI 搜索失败: {e}")
            # 降级到 Unsplash
            if self.unsplash_key:
                logger.info("⚠️ 降级使用 Unsplash 搜索")
                return await self._search_with_unsplash(query, count)
            return ToolResult(
                success=False,
                message=f"图片搜索失败：{str(e)}",
                error="SEARCH_ERROR"
            )
    
    async def _search_with_unsplash(self, query: str, count: int) -> ToolResult:
        """使用 Unsplash 搜索（备用方案）"""
        try:
            import random
            
            logger.info(f"🖼️ Unsplash 图片搜索 (备用): {query} (数量: {count})")
            
            # 🎲 添加随机页数，让每次搜索返回不同的图片
            random_page = random.randint(1, 5)  # 随机选择第1-5页
            
            # 多获取一些图片，然后随机选择
            fetch_count = min(count * 2, 20)
            
            # 构建请求参数
            params = {
                "query": query,
                "page": random_page,
                "per_page": fetch_count,
                "orientation": "landscape",  # 横向图片
                "content_filter": "high"  # 高质量内容过滤
            }
            
            headers = {
                "Authorization": f"Client-ID {self.api_key}",
                "Accept-Version": "v1"
            }
            
            # 调用 Unsplash API
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.api_url,
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    if not results:
                        logger.warning(f"⚠️ 未找到'{query}'相关的图片")
                        return ToolResult(
                            success=True,
                            data={"query": query, "images": []},
                            message=f"未找到'{query}'相关的图片，换个关键词试试？"
                        )
                    
                    # 🔒 先过滤掉不可访问的域名
                    import random
                    accessible_results = [
                        photo for photo in results 
                        if self._is_url_accessible(photo.get("urls", {}).get("regular", ""))
                    ]
                    
                    if not accessible_results:
                        logger.warning(f"⚠️ 所有图片均被过滤，使用原始结果")
                        accessible_results = results
                    else:
                        logger.info(f"🔒 过滤后剩余 {len(accessible_results)}/{len(results)} 张可访问图片")
                    
                    # 🎲 随机选择指定数量的图片
                    selected_results = random.sample(accessible_results, min(len(accessible_results), count))
                    
                    logger.info(f"🎲 从 {len(accessible_results)} 张图片中随机选择 {len(selected_results)} 张")
                    
                    # 格式化结果
                    images = []
                    for idx, photo in enumerate(selected_results, 1):
                        # 获取不同尺寸的URL
                        urls = photo.get("urls", {})
                        image_url = urls.get("regular", "")  # 中等尺寸
                        thumb_url = urls.get("small", "")  # 缩略图
                        
                        # 图片信息
                        description = photo.get("description") or photo.get("alt_description", "")
                        photographer = photo.get("user", {}).get("name", "Unknown")
                        
                        images.append({
                            "url": image_url,
                            "thumb_url": thumb_url,
                            "description": description,
                            "photographer": photographer,
                            "index": idx
                        })
                    
                    # 构建回复消息
                    message_parts = [f"🖼️ 找到 {len(images)} 张'{query}'相关图片（Unsplash）：\n"]
                    
                    for img in images:
                        desc_text = f"：{img['description'][:30]}..." if img['description'] else ""
                        message_parts.append(f"{img['index']}. 图片{desc_text}")
                        message_parts.append(f"   📷 摄影师：{img['photographer']}")
                        message_parts.append(f"   🔗 {img['url']}")
                    
                    result_message = "\n".join(message_parts)
                    
                    logger.success(f"✅ 图片搜索成功，找到 {len(images)} 张图片")
                    
                    return ToolResult(
                        success=True,
                        data={
                            "query": query,
                            "images": images,
                            "count": len(images),
                            "source": "unsplash"
                        },
                        message=result_message
                    )
                
                elif response.status_code == 401:
                    logger.error("❌ Unsplash API密钥无效")
                    return ToolResult(
                        success=False,
                        message="图片搜索失败（API密钥无效）",
                        error="INVALID_API_KEY"
                    )
                
                elif response.status_code == 403:
                    logger.error("❌ Unsplash API 调用次数超限")
                    return ToolResult(
                        success=False,
                        message="图片搜索次数已达上限，请稍后重试",
                        error="RATE_LIMIT_EXCEEDED"
                    )
                
                else:
                    error_text = response.text
                    logger.error(f"❌ Unsplash API错误: {response.status_code} - {error_text}")
                    return ToolResult(
                        success=False,
                        message="图片搜索失败（服务异常）",
                        error=f"API_ERROR_{response.status_code}"
                    )
        
        except httpx.TimeoutException:
            logger.error("❌ 图片搜索超时")
            return ToolResult(
                success=False,
                message="图片搜索超时，请稍后重试",
                error="TIMEOUT"
            )
        
        except Exception as e:
            logger.error(f"❌ 图片搜索失败: {e}")
            return ToolResult(
                success=False,
                message=f"图片搜索失败：{str(e)}",
                error="SEARCH_ERROR"
            )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return bool(self.serpapi_key or self.unsplash_key)


# 导出工具实例
image_search_tool = ImageSearchTool()

