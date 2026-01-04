"""
Fetch 工具 - 网页内容抓取和转换
将网页内容转换为干净的 Markdown 格式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any
from nonebot.log import logger
import httpx
from bs4 import BeautifulSoup
import re


class FetchTool(BaseTool):
    """
    网页内容抓取工具
    将网页HTML转换为结构化文本，方便AI处理
    """
    
    def __init__(self):
        """初始化 Fetch 工具"""
        super().__init__()
        logger.success("✅ Fetch 网页抓取工具初始化完成")
    
    def get_name(self) -> str:
        return "fetch_webpage"
    
    def get_description(self) -> str:
        return "抓取网页内容并转换为文本。当用户分享链接并要求总结、阅读、分析网页内容时使用。例如：'帮我看看这个网站'、'总结一下这篇文章'"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要抓取的网页URL地址"
                }
            },
            "required": ["url"]
        }
    
    async def execute(self, url: str) -> ToolResult:
        """
        执行网页抓取
        
        Args:
            url: 网页URL
        
        Returns:
            ToolResult: 抓取的网页内容
        """
        try:
            logger.info(f"🌐 开始抓取网页: {url[:60]}...")
            
            # 发送 HTTP 请求
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"❌ 网页请求失败: {response.status_code}")
                    return ToolResult(
                        success=False,
                        message=f"无法访问网页（错误码: {response.status_code}）",
                        error=f"HTTP_{response.status_code}"
                    )
                
                # 解析 HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 移除脚本和样式
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # 提取标题
                title = soup.find('title')
                title_text = title.get_text().strip() if title else "无标题"
                
                # 提取主要内容
                # 尝试查找常见的内容容器
                main_content = None
                for selector in ['article', 'main', '.content', '.post', '.article']:
                    if selector.startswith('.'):
                        main_content = soup.find(class_=selector[1:])
                    else:
                        main_content = soup.find(selector)
                    if main_content:
                        break
                
                # 如果没找到特定容器，使用 body
                if not main_content:
                    main_content = soup.find('body')
                
                if not main_content:
                    logger.error("❌ 无法提取网页内容")
                    return ToolResult(
                        success=False,
                        message="无法提取网页内容",
                        error="NO_CONTENT"
                    )
                
                # 提取文本
                text = main_content.get_text(separator='\n', strip=True)
                
                # 清理文本
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                # 去重连续的空行
                cleaned_lines = []
                prev_line = ""
                for line in lines:
                    if line != prev_line or len(line) > 20:  # 避免重复的短句
                        cleaned_lines.append(line)
                        prev_line = line
                
                content = '\n'.join(cleaned_lines)
                
                # 限制长度（避免过长）
                max_length = 3000
                if len(content) > max_length:
                    content = content[:max_length] + "\n\n...[内容过长，已截断]"
                
                logger.success(f"✅ 网页抓取成功，内容长度: {len(content)} 字符")
                
                result_message = f"📄 网页标题：{title_text}\n\n内容摘要：\n{content[:500]}..."
                
                return ToolResult(
                    success=True,
                    data={
                        "url": url,
                        "title": title_text,
                        "content": content,
                        "length": len(content)
                    },
                    message=result_message
                )
        
        except httpx.TimeoutException:
            logger.error("❌ 网页请求超时")
            return ToolResult(
                success=False,
                message="网页访问超时，请稍后重试",
                error="TIMEOUT"
            )
        
        except Exception as e:
            logger.error(f"❌ 网页抓取失败: {e}")
            return ToolResult(
                success=False,
                message=f"网页抓取失败：{str(e)}",
                error="FETCH_ERROR"
            )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return True  # Fetch 不需要 API 密钥


# 导出工具实例
fetch_tool = FetchTool()

