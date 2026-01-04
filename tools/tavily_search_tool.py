"""
Tavily 智能搜索工具 - 增强版网页搜索
提供更精准、更实时的搜索结果
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any, Optional
from nonebot.log import logger
import httpx


class TavilySearchTool(BaseTool):
    """
    Tavily 智能搜索工具
    比普通搜索更智能，能自动提取关键信息和摘要
    """
    
    def __init__(self):
        """初始化 Tavily 搜索工具"""
        super().__init__()
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.api_url = "https://api.tavily.com/search"
        
        if self.api_key:
            logger.success("✅ Tavily 搜索工具初始化完成")
        else:
            logger.warning("⚠️ TAVILY_API_KEY 未设置，搜索功能不可用")
            logger.info("💡 获取免费API密钥: https://tavily.com")
    
    def get_name(self) -> str:
        return "tavily_search"
    
    def get_description(self) -> str:
        return "智能网页搜索，获取实时信息。比普通搜索更精准，能自动总结关键内容。适用于：新闻、价格、数据、知识查询等"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回的最大结果数量（默认3）",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    
    async def execute(
        self, 
        query: str, 
        max_results: int = 3
    ) -> ToolResult:
        """
        执行智能搜索
        
        Args:
            query: 搜索查询
            max_results: 返回结果数量
        
        Returns:
            ToolResult: 搜索结果
        """
        if not self.is_available():
            return ToolResult(
                success=False,
                message="Tavily 搜索功能不可用（API密钥未配置）",
                error="API_NOT_CONFIGURED"
            )
        
        try:
            logger.info(f"🔍 Tavily 搜索: {query}")
            
            # 构建请求
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": min(max_results, 5),  # 限制最多5条
                "search_depth": "basic",  # basic/advanced
                "include_answer": True,  # 包含AI生成的答案总结
                "include_raw_content": False  # 不包含完整网页内容
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 解析结果
                    answer = data.get("answer", "")
                    results = data.get("results", [])
                    
                    if not results and not answer:
                        logger.warning("⚠️ Tavily 未返回任何结果")
                        return ToolResult(
                            success=True,
                            data={"query": query, "results": []},
                            message="未找到相关信息"
                        )
                    
                    # 格式化结果
                    formatted_results = []
                    for idx, item in enumerate(results[:max_results], 1):
                        formatted_results.append({
                            "title": item.get("title", "无标题"),
                            "url": item.get("url", ""),
                            "content": item.get("content", "")[:200],  # 限制长度
                            "score": item.get("score", 0.0)
                        })
                    
                    # 构建回复消息
                    message_parts = []
                    
                    if answer:
                        message_parts.append(f"💡 智能总结：{answer}")
                    
                    if formatted_results:
                        message_parts.append("\n📊 搜索结果：")
                        for idx, result in enumerate(formatted_results, 1):
                            message_parts.append(
                                f"{idx}. {result['title']}\n"
                                f"   {result['content'][:100]}...\n"
                                f"   🔗 {result['url']}"
                            )
                    
                    result_message = "\n".join(message_parts)
                    
                    logger.success(f"✅ Tavily 搜索成功，找到 {len(formatted_results)} 条结果")
                    
                    return ToolResult(
                        success=True,
                        data={
                            "query": query,
                            "answer": answer,
                            "results": formatted_results,
                            "count": len(formatted_results)
                        },
                        message=result_message
                    )
                
                elif response.status_code == 401:
                    logger.error("❌ Tavily API密钥无效")
                    return ToolResult(
                        success=False,
                        message="搜索失败（API密钥无效）",
                        error="INVALID_API_KEY"
                    )
                
                elif response.status_code == 429:
                    logger.error("❌ Tavily API调用次数超限")
                    return ToolResult(
                        success=False,
                        message="搜索失败（调用次数超限）",
                        error="RATE_LIMIT_EXCEEDED"
                    )
                
                else:
                    error_text = response.text
                    logger.error(f"❌ Tavily API错误: {response.status_code} - {error_text}")
                    return ToolResult(
                        success=False,
                        message="搜索失败（服务异常）",
                        error=f"API_ERROR_{response.status_code}"
                    )
        
        except httpx.TimeoutException:
            logger.error("❌ Tavily 搜索超时")
            return ToolResult(
                success=False,
                message="搜索超时，请稍后重试",
                error="TIMEOUT"
            )
        
        except Exception as e:
            logger.error(f"❌ Tavily 搜索失败: {e}")
            return ToolResult(
                success=False,
                message=f"搜索失败：{str(e)}",
                error="SEARCH_ERROR"
            )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return bool(self.api_key)


# 导出工具实例
tavily_search_tool = TavilySearchTool()

