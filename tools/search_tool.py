"""
网络搜索工具 - 使用 DuckDuckGo 搜索引擎
"""
from core.tool_base import BaseTool
from nonebot.log import logger
from typing import Dict, Any


class SearchTool(BaseTool):
    """
    网络搜索工具 - AI 无法获取最新信息，需要通过搜索引擎。
    使用 DuckDuckGo，免费且无需 API key。
    """
    
    def get_name(self) -> str:
        return "web_search"
    
    def get_description(self) -> str:
        return "在互联网上搜索最新信息。AI的知识截止到2023年，对于最新新闻、实时信息、不确定的事实，必须使用此工具。"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题，例如：'今天的新闻'、'比特币价格'、'最新科技新闻'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量，默认3条",
                    "default": 3
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str, max_results: int = 3, **kwargs) -> str:
        """
        执行网络搜索
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
        
        Returns:
            str: 搜索结果摘要
        """
        logger.info(f"执行网络搜索，关键词: {query}, 结果数: {max_results}")
        
        try:
            from ddgs import DDGS
            
            # 使用 DuckDuckGo 搜索（支持代理）
            # 如果需要代理，可以设置 proxy 参数，例如：
            # ddgs = DDGS(proxy="socks5://127.0.0.1:1086")
            ddgs = DDGS()
            
            results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return f"没有找到关于 '{query}' 的搜索结果。"
            
            # 格式化搜索结果
            formatted_results = []
            for i, result in enumerate(results, 1):
                title = result.get('title', '无标题')
                snippet = result.get('body', '无摘要')
                url = result.get('href', '')
                
                formatted_results.append(
                    f"{i}. {title}\n   {snippet}\n   来源: {url}"
                )
            
            return "搜索结果：\n\n" + "\n\n".join(formatted_results)
        
        except ImportError:
            logger.error("ddgs 库未安装")
            return "搜索功能不可用：缺少必要的库。请运行: pip install ddgs"
        
        except Exception as e:
            logger.error(f"网络搜索失败: {e}")
            return f"搜索失败：{str(e)}"

