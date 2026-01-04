"""
图像处理入口 - Handler Layer
职责：监听图像消息，调用服务处理
代码量：~60 行（保持简洁！）
"""
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
from nonebot.log import logger
from typing import List
import random

# 导入服务层
from services.image.image_service import get_image_service


# ==================== 配置 ====================
REPLY_PROBABILITY = 0.95  # 回复概率


# ==================== 事件监听 ====================
image_matcher = on_message(priority=10, block=False)


@image_matcher.handle()
async def handle_image_messages(bot: Bot, event: MessageEvent):
    """
    处理图像消息
    职责：
    1. 检测消息中的图片
    2. 调用服务处理
    3. 发送回复
    
    ★ 代码简洁，一眼看懂功能
    """
    
    # 1. 提取图片 URL
    image_urls = _extract_image_urls(event.message)
    if not image_urls:
        return  # 不是图片消息，直接返回
    
    # 2. 决定是否回复（概率控制）
    if random.random() > REPLY_PROBABILITY:
        logger.debug("根据概率设置，跳过本次图片回复")
        return
    
    # 3. 调用服务处理图像
    user_id = str(event.user_id)
    image_url = image_urls[0]  # 目前只处理第一张图
    
    try:
        image_service = get_image_service()
        reply = await image_service.process_image(user_id, image_url)
        
        # 4. 发送回复
        if reply:
            await bot.send(event, reply)
            logger.info(f"✅ 已回复图片消息")
        
    except Exception as e:
        logger.error(f"处理图片消息失败: {e}")


# ==================== 辅助函数 ====================
def _extract_image_urls(message: Message) -> List[str]:
    """从消息中提取图片 URL"""
    urls = []
    for seg in message:
        if seg.type == "image":
            url = seg.data.get("url") or seg.data.get("file")
            if url:
                urls.append(url)
    return urls


# ==================== 系统初始化 ====================
logger.success("🖼️ 图像理解 Handler 已加载")
logger.info(f"  - 回复概率: {int(REPLY_PROBABILITY * 100)}%")
logger.info(f"  - 保存到记忆: ✅")

