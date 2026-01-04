"""
多模态AI接口
统一处理文本和图像的AI能力
"""

from nonebot.log import logger
from typing import Dict, List, Optional, Tuple
import httpx
import base64
from pathlib import Path

# 检查是否安装了dashscope
DASHSCOPE_AVAILABLE = False
try:
    import dashscope
    from dashscope import MultiModalConversation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ dashscope未安装，图像识别功能将不可用")

# ==================== 配置 ====================
class MultiModalConfig:
    """多模态AI配置"""
    # 通义千问-VL API配置
    API_KEY = "sk-105724d3e4bb4f6ea354426dbecf3137"
    MODEL = "qwen-vl-max"  # 通义千问视觉模型
    
    # 功能开关
    ENABLE_IMAGE_UNDERSTANDING = True  # 图像理解功能
    ENABLE_IMAGE_MEMORY = True  # 图像内容记忆功能
    
    # 图像处理配置
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 最大5MB
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# ==================== 多模态AI引擎 ====================
class MultiModalAI:
    """统一的多模态AI接口"""
    
    def __init__(self):
        self.api_key = MultiModalConfig.API_KEY
        self.model = MultiModalConfig.MODEL
        
        if DASHSCOPE_AVAILABLE:
            dashscope.api_key = self.api_key
            logger.info("✅ 多模态AI引擎初始化成功")
        else:
            logger.warning("⚠️ 多模态AI引擎不可用")
    
    async def understand_image(
        self, 
        image_url: str, 
        context: Optional[str] = None
    ) -> Optional[Dict]:
        """
        理解图片内容
        
        Args:
            image_url: 图片URL
            context: 对话上下文
        
        Returns:
            {
                "description": "图片描述",
                "objects": ["物体1", "物体2"],
                "scene": "场景",
                "emotion": "情感",
                "text": "识别的文字",
                "suggestion": "建议的回复"
            }
        """
        if not DASHSCOPE_AVAILABLE or not MultiModalConfig.ENABLE_IMAGE_UNDERSTANDING:
            return None
        
        try:
            logger.info(f"🖼️ 开始理解图片：{image_url[:50]}...")
            
            # 构建提示词
            prompt = """请仔细分析这张图片，并以JSON格式返回以下信息：
{
    "description": "详细描述图片内容（1-2句话）",
    "objects": ["识别到的主要物体"],
    "scene": "场景类型（如：室内、室外、自然风光、城市、美食、人物等）",
    "emotion": "图片传达的情感（如：开心、难过、平静、激动等）",
    "text": "图片中的文字（如果有）",
    "suggestion": "适合这张图片的回复建议（自然、友好的语气）"
}"""
            
            if context:
                prompt += f"\n\n对话上下文：{context}"
            
            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_url},
                        {"text": prompt}
                    ]
                }
            ]
            
            logger.info(f"📡 调用通义千问-VL API...")
            
            # 调用API（直接使用同步调用，在异步函数中）
            response = MultiModalConversation.call(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            logger.info(f"📡 API响应状态: {response.status_code}")
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content[0]["text"]
                logger.info(f"📝 API返回内容: {content[:100]}...")
                
                # 解析JSON
                import json
                import re
                
                # 尝试提取JSON
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    logger.info(f"✅ 图像理解成功：{result.get('description', '')[:50]}")
                    return result
                else:
                    # 如果没有JSON，返回原始文本作为描述
                    logger.warning("⚠️ 未找到JSON格式，使用原始回复")
                    return {
                        "description": content,
                        "suggestion": content
                    }
            else:
                logger.error(f"❌ 图像理解API调用失败: {response.status_code} - {getattr(response, 'message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.exception(f"💥 图像理解异常: {e}")
            return None
    
    async def generate_image_response(
        self, 
        image_analysis: Dict, 
        user_context: Optional[str] = None
    ) -> str:
        """
        基于图像分析生成自然的回复
        
        Args:
            image_analysis: 图像分析结果
            user_context: 用户上下文
        
        Returns:
            自然的回复文本
        """
        if not image_analysis:
            return "好有趣的图片！"
        
        # 如果有建议回复，优先使用
        if "suggestion" in image_analysis:
            return image_analysis["suggestion"]
        
        # 否则基于分析结果构建回复
        description = image_analysis.get("description", "")
        scene = image_analysis.get("scene", "")
        emotion = image_analysis.get("emotion", "")
        
        # 简单的模板回复
        templates = [
            f"{description}",
            f"看到了{scene}的场景，{description}",
            f"这张图片感觉很{emotion}！{description}"
        ]
        
        import random
        return random.choice(templates)
    
    def format_image_for_memory(self, image_analysis: Dict) -> str:
        """
        将图像分析结果格式化为可以存入记忆的文本
        
        Args:
            image_analysis: 图像分析结果
        
        Returns:
            格式化的文本
        """
        if not image_analysis:
            return "[用户发送了一张图片]"
        
        parts = []
        
        if "description" in image_analysis:
            parts.append(f"[图片: {image_analysis['description']}")
        
        if "scene" in image_analysis and image_analysis["scene"]:
            parts.append(f"场景:{image_analysis['scene']}")
        
        if "emotion" in image_analysis and image_analysis["emotion"]:
            parts.append(f"情感:{image_analysis['emotion']}")
        
        if "objects" in image_analysis and image_analysis["objects"]:
            objects_str = "、".join(image_analysis["objects"][:3])
            parts.append(f"包含:{objects_str}")
        
        if parts:
            return " ".join(parts) + "]"
        else:
            return "[用户发送了一张图片]"

# 全局实例
multimodal_ai = MultiModalAI()

# ==================== 辅助函数 ====================
async def download_image(image_url: str) -> Optional[bytes]:
    """下载图片"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"下载图片失败: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"下载图片异常: {e}")
        return None

