"""
图像识别工具 - 使用视觉模型理解图片内容
符合 Function Calling Agent 标准
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any, Optional
from nonebot.log import logger
import httpx


class VisionTool(BaseTool):
    """图像识别工具 - 理解图片内容"""
    
    def __init__(self):
        """初始化视觉工具"""
        super().__init__()
        # 使用Gemini 2.5 Flash模型（速度快，质量高）
        self.api_key = os.getenv("VISION_API_KEY", "sk-6fW34zquoQ0Bk7ry65xcSU0INBFF8o91")
        self.base_url = "https://gaozaiya.cloudns.org"
        self.model = "Gemini/gemini-2.5-flash"
        logger.info(f"✅ 图像识别工具初始化完成 (模型: {self.model})")
    
    def get_name(self) -> str:
        return "vision_understanding"
    
    def get_description(self) -> str:
        return "理解图片内容，识别图片中的对象、场景、文字等。当用户询问图片相关问题时使用，如'这是什么'、'图片里有什么'、'帮我看看这张图'"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "图片的URL地址（从消息上下文中获取）"
                },
                "question": {
                    "type": "string",
                    "description": "用户对图片的具体问题（可选）",
                }
            },
            "required": ["image_url"]
        }
    
    async def execute(
        self, 
        image_url: str, 
        question: Optional[str] = None
    ) -> ToolResult:
        """
        执行图像理解
        
        Args:
            image_url: 图片URL
            question: 用户的具体问题
        
        Returns:
            ToolResult: 执行结果
        """
        try:
            if not self.api_key:
                return ToolResult(
                    success=False,
                    message="视觉API未配置",
                    error="API_NOT_CONFIGURED"
                )
            
            # 构建提示词
            if question:
                prompt = f"请回答用户的问题：{question}"
            else:
                prompt = "请用1-2句话简单描述这张图片的内容，包括主要对象、场景和氛围。"
            
            logger.info(f"🖼️ 开始理解图片: {image_url[:60]}...")
            logger.info(f"🖼️ 用户问题: {question or '无'}")
            
            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            # API请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.3
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        logger.success(f"✅ 图片理解成功: {content[:50]}...")
                        
                        return ToolResult(
                            success=True,
                            data={"description": content, "image_url": image_url},
                            message=f"图片内容：{content}"
                        )
                    else:
                        logger.error(f"❌ API响应格式异常: {data}")
                        return ToolResult(
                            success=False,
                            message="API响应格式异常",
                            error="INVALID_API_RESPONSE"
                        )
                else:
                    error_text = response.text
                    logger.error(f"❌ API错误: {response.status_code} - {error_text}")
                    return ToolResult(
                        success=False,
                        message=f"图片识别失败（API错误）",
                        error=f"API_ERROR_{response.status_code}"
                    )
        
        except Exception as e:
            logger.error(f"❌ 图像理解失败: {e}")
            return ToolResult(
                success=False,
                message=f"图片识别失败：{str(e)}",
                error="VISION_ERROR"
            )
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        if not self.api_key:
            return False
        
        # 尝试测试连接
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/v1/models")
                return response.status_code < 500
        except:
            return False


# 导出工具实例
vision_tool = VisionTool()


