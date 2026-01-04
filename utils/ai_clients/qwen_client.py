"""
通义千问 VL 客户端 - Utils Layer
职责：封装通义千问图像理解 API
代码量：~100 行（纯工具，无业务逻辑）
"""
from typing import Optional, Dict
from nonebot.log import logger
import os

# 检查是否安装了 dashscope
DASHSCOPE_AVAILABLE = False
try:
    import dashscope
    from dashscope import MultiModalConversation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ dashscope 未安装，图像识别功能将不可用")


class QwenVLClient:
    """通义千问-VL 图像理解客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-vl-max"):
        """
        初始化客户端
        
        Args:
            api_key: API密钥，如果不提供则从环境变量读取
            model: 模型名称
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "sk-105724d3e4bb4f6ea354426dbecf3137")
        self.model = model
        self.available = DASHSCOPE_AVAILABLE
        
        if self.available:
            dashscope.api_key = self.api_key
    
    async def understand_image(self, image_url: str, prompt: Optional[str] = None) -> Optional[str]:
        """
        理解图片内容
        
        Args:
            image_url: 图片 URL
            prompt: 提示词（可选）
        
        Returns:
            图片描述文本，失败返回 None
        """
        if not self.available:
            logger.error("dashscope 不可用")
            return None
        
        try:
            # 默认提示词
            if not prompt:
                prompt = "请用1-2句话简单描述这张图片的内容，包括主要对象、场景和氛围。"
            
            # 调用 API
            logger.info("📡 调用通义千问-VL API...")
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_url},
                        {"text": prompt}
                    ]
                }
            ]
            
            response = MultiModalConversation.call(
                model=self.model,
                messages=messages
            )
            
            # 处理响应
            status_code = response.status_code
            logger.info(f"📡 API响应状态: {status_code}")
            
            if status_code == 200:
                description = response.output.choices[0].message.content[0]["text"]
                logger.info(f"📝 API返回内容: {description[:100]}...")
                return description
            else:
                error_msg = response.message if hasattr(response, 'message') else '未知错误'
                logger.error(f"❌ API调用失败: {status_code} - {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 图像理解异常: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return self.available and bool(self.api_key)


# 全局单例
_qwen_client = QwenVLClient()

def get_qwen_client() -> QwenVLClient:
    """获取全局通义千问客户端"""
    return _qwen_client




