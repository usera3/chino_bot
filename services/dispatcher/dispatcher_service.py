"""
智能调度服务 - Dispatcher Service
协调意图识别和功能路由
"""

from typing import Dict, Optional
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.log import logger

from services.dispatcher.function_registry import get_function_registry
from services.dispatcher.intent_recognizer import get_intent_recognizer


class DispatcherService:
    """
    智能调度器 - 协调整个系统
    """
    
    def __init__(self):
        self.function_registry = get_function_registry()
        self.intent_recognizer = get_intent_recognizer()
    
    async def process(self, event: MessageEvent, user_message: str) -> Optional[str]:
        """
        处理用户消息的主流程
        
        Args:
            event: 消息事件
            user_message: 用户消息文本
        
        Returns:
            回复文本，或None（如果功能内部已处理）
        """
        user_id = str(event.user_id)
        
        # Step 1: 快速关键词匹配（优化性能）
        quick_match = self.function_registry.search_by_keywords(user_message)
        
        # Step 2: AI意图识别
        intent = await self.intent_recognizer.analyze_intent(user_message, user_id)
        
        # Step 3: 决策和路由
        if intent["intent_type"] == "function_call" and intent.get("function_name"):
            # 调用特定功能
            return await self._call_function(
                intent["function_name"],
                user_message,
                event,
                intent
            )
        else:
            # 普通聊天
            return await self._handle_chat(
                user_message,
                user_id,
                intent
            )
    
    async def _call_function(
        self,
        function_name: str,
        user_message: str,
        event: MessageEvent,
        intent: Dict
    ) -> Optional[str]:
        """
        调用指定功能
        
        Args:
            function_name: 功能名称
            user_message: 用户消息
            event: 消息事件
            intent: 意图数据
        
        Returns:
            功能执行结果
        """
        func_info = self.function_registry.get_function(function_name)
        
        if not func_info:
            return f"抱歉，我理解你想使用 {function_name} 功能，但我还没有学会这个。"
        
        try:
            # 调用功能处理器
            result = await func_info["handler"](user_message, event)
            
            # 如果功能返回None，说明功能内部已经发送了消息
            if result is None:
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"功能调用失败 [{function_name}]: {e}")
            return f"抱歉，执行 {function_name} 时出现了问题。"
    
    async def _handle_chat(
        self,
        user_message: str,
        user_id: str,
        intent: Dict
    ) -> Optional[str]:
        """
        处理普通聊天 - 调用高级聊天系统
        这样可以利用完整的记忆、摘要、重要性评分等功能
        
        Args:
            user_message: 用户消息
            user_id: 用户ID
            intent: 意图数据
        
        Returns:
            聊天回复
        """
        try:
            # 使用新的聊天服务
            from services.chat.chat_service import get_chat_service
            
            chat_service = get_chat_service()
            reply = await chat_service.process_message(user_id, user_message)
            
            if reply:
                logger.info(f"💬 用户 {user_id} 对话处理完成")
                return reply
            else:
                logger.warning("⚠️ AI API返回空回复")
                return "抱歉，我现在有点累了，等会再聊好吗？"
                
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            logger.exception(e)
            return "我们聊点别的吧？"


# ==================== 全局单例 ====================
_dispatcher_service: Optional[DispatcherService] = None

def get_dispatcher_service() -> DispatcherService:
    """获取调度服务单例"""
    global _dispatcher_service
    if _dispatcher_service is None:
        _dispatcher_service = DispatcherService()
    return _dispatcher_service























