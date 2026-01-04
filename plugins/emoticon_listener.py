"""
表情包监听插件
监听群聊和私聊中的图片消息，自动学习表情包
"""

from nonebot import on_message, get_driver, require
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, PrivateMessageEvent, MessageSegment
from nonebot.log import logger
from nonebot.rule import to_me
from typing import List, Dict
from collections import deque
import random

# 导入学习器
from .emoticon_learner import emoticon_learner, LearnerConfig

# ==================== 上下文管理 ====================
class ContextManager:
    """上下文管理器 - 记录最近的对话"""
    
    def __init__(self, max_messages: int = 10):
        self.contexts: Dict[str, deque] = {}  # key: user_id 或 group_id
        self.max_messages = max_messages
    
    def add_message(self, key: str, message: str):
        """添加消息到上下文"""
        if key not in self.contexts:
            self.contexts[key] = deque(maxlen=self.max_messages)
        
        self.contexts[key].append(message)
    
    def get_context(self, key: str) -> List[str]:
        """获取上下文"""
        if key in self.contexts:
            return list(self.contexts[key])
        return []
    
    def clear_context(self, key: str):
        """清除上下文"""
        if key in self.contexts:
            del self.contexts[key]

# 全局上下文管理器
context_manager = ContextManager(max_messages=LearnerConfig.MAX_CONTEXT_MESSAGES)

# ==================== 消息监听 ====================

# 监听所有消息（优先级低，不阻断）
message_listener = on_message(priority=99, block=False)

@message_listener.handle()
async def handle_all_messages(bot: Bot, event: MessageEvent):
    """
    监听所有消息，完成两件事：
    1. 记录上下文
    2. 检测图片并学习表情包
    """
    
    # 生成上下文key
    if isinstance(event, GroupMessageEvent):
        context_key = f"group_{event.group_id}"
    else:
        context_key = f"user_{event.user_id}"
    
    # 1. 记录文本消息到上下文
    message_text = event.get_plaintext().strip()
    if message_text:
        context_manager.add_message(context_key, f"{event.user_id}: {message_text}")
    
    # 2. 检测图片消息
    if not LearnerConfig.ENABLE_LEARNING:
        return
    
    message = event.get_message()
    
    for segment in message:
        if segment.type == "image":
            # 获取图片URL
            image_url = segment.data.get("url")
            if not image_url:
                continue
            
            # 获取上下文
            context = context_manager.get_context(context_key)
            
            if len(context) < LearnerConfig.MIN_CONTEXT_LENGTH:
                logger.debug("上下文太短，跳过学习")
                continue
            
            # 异步学习（不阻塞）
            try:
                learned = await emoticon_learner.process_image_message(
                    event=event,
                    image_url=image_url,
                    context_messages=context
                )
                
                if learned:
                    logger.info(f"🎓 学习了一个新表情包！来源: {context_key}")
                    
            except Exception as e:
                logger.exception(f"学习表情包失败: {e}")

# ==================== 启动初始化 ====================
driver = get_driver()

@driver.on_startup
async def init_emoticon_learner():
    """启动时初始化学习器"""
    try:
        await emoticon_learner.initialize()
        logger.success("🎓 表情包学习器启动成功")
    except Exception as e:
        logger.exception(f"表情包学习器启动失败: {e}")

@driver.on_shutdown
async def shutdown_emoticon_learner():
    """关闭时清理"""
    # 关闭数据库连接
    if emoticon_learner.engine:
        await emoticon_learner.engine.dispose()
    logger.info("🎓 表情包学习器已关闭")


