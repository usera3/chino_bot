"""
图像理解服务 - Service Layer
职责：协调图像理解的完整业务流程
代码量：~150 行（核心业务逻辑）
"""
from typing import Optional, Dict
from nonebot.log import logger

# 导入工具层
from utils.ai_clients.nvidia_vision_client import get_nvidia_vision_client
from utils.image.element_extractor import extract_key_elements

# 导入服务层
from services.emotion.emotion_service import get_emotion_service
from services.image.image_reply_service import ImageReplyService


class ImageService:
    """图像理解服务"""
    
    def __init__(self):
        self.vision_client = get_nvidia_vision_client()  # 使用NVIDIA视觉模型替代千问VL
        self.emotion_service = get_emotion_service()
        self.reply_service = ImageReplyService()
    
    async def process_image(self, user_id: str, image_url: str) -> Optional[str]:
        """
        处理图像消息的完整流程
        
        Args:
            user_id: 用户ID
            image_url: 图片URL
        
        Returns:
            回复文本，失败返回 None
        """
        try:
            # 1. 理解图像内容
            logger.info(f"🖼️ 开始理解图片：{image_url[:60]}...")
            description = await self._understand_image(image_url)
            
            if not description:
                logger.warning("⚠️ 图片理解失败")
                return None
            
            logger.info(f"✅ 图片理解成功：{description[:50]}")
            
            # 2. 提取关键元素
            elements = extract_key_elements(description)
            
            # 3. 获取用户情感状态
            emotion_style = await self.emotion_service.get_emotion_influenced_style(user_id)
            
            # 4. 生成个性化回复（使用新的幽默回复系统）
            reply = await self.reply_service.generate_reply(
                description=description,
                elements=elements,
                emotion_style=emotion_style
            )
            
            logger.info(f"💬 生成图片回复：{reply[:30]}")
            
            # 5. 保存到记忆（如果需要）
            # await self._save_to_memory(user_id, description)
            
            return reply
            
        except Exception as e:
            logger.error(f"处理图像失败: {e}")
            return None
    
    async def _understand_image(self, image_url: str) -> Optional[str]:
        """
        理解图像内容
        
        Args:
            image_url: 图片URL
        
        Returns:
            图像描述文本
        """
        # 使用NVIDIA视觉模型进行图像理解（速度比千问VL更快）
        description = await self.vision_client.understand_image(image_url)
        return description
    
    def infer_scene(self, description: str) -> str:
        """
        根据描述推断场景类型
        
        Args:
            description: 图像描述
        
        Returns:
            场景类型（人物/动物/风景/物品/未知）
        """
        scene_keywords = {
            "人物": ["女孩", "男孩", "少女", "少年", "人物", "角色"],
            "动物": ["猫", "狗", "鸟", "动物", "宠物"],
            "风景": ["树", "花", "山", "海", "天空", "风景"],
            "物品": ["食物", "物品", "东西", "物体"]
        }
        
        for scene, keywords in scene_keywords.items():
            if any(kw in description for kw in keywords):
                return scene
        
        return "未知"
    
    def format_for_memory(self, description: str) -> str:
        """
        格式化图像描述用于保存到记忆
        
        Args:
            description: 图像描述
        
        Returns:
            格式化后的文本
        """
        scene = self.infer_scene(description)
        return f"[用户发送了一张{scene}图片: {description[:50]}...]"


# 全局单例
_image_service = None

def get_image_service() -> ImageService:
    """获取全局图像服务实例"""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service



