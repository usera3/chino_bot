"""
聊天服务 - Service Layer
职责：协调完整的聊天流程
代码量：~200行
"""
from typing import Optional
from nonebot.log import logger

# 导入配置
from services.chat.chat_config import ChatConfig

# 导入数据库服务
from services.database.database_service import get_database_service

# 导入记忆服务
from services.chat.memory_service import get_memory_service

# 导入AI客户端
from utils.ai_clients.deepseek_client import get_deepseek_client

# 尝试导入主动聊天引擎（可选）
try:
    from services.proactive import get_proactive_service
    proactive_service = get_proactive_service()
    PROACTIVE_AVAILABLE = True
except ImportError:
    PROACTIVE_AVAILABLE = False


class ChatService:
    """聊天服务 - 协调完整流程"""
    
    def __init__(self):
        self.db = get_database_service()
        self.memory = get_memory_service()
        self.ai_client = get_deepseek_client()
    
    async def process_parameterized_message(self, 
                                        user_id: str, 
                                        message: str, 
                                        emotion_state: dict = None,
                                        ai_description: str = "",
                                        special_instructions: str = "",
                                        should_save: bool = True,
                                        is_proactive: bool = False) -> Optional[str]:
        """
        参数化处理消息，支持传入各种控制参数
        
        Args:
            user_id: 用户ID
            message: 消息内容
            emotion_state: 用户情感状态字典 (可选)
            ai_description: 给AI的特殊描述词 (可选)
            special_instructions: 特殊指令 (可选)
            should_save: 是否保存到历史记录 (默认True)
            is_proactive: 是否为主动聊天消息 (默认False)
        
        Returns:
            AI回复文本，失败返回 None
        """
        try:
            # 1. 计算重要性和情感
            importance = self.memory.calculate_importance(message, 'user')
            emotion = emotion_state if emotion_state else self.memory.detect_emotion(message)
            
            # 2. 获取当前角色ID（用于角色隔离）
            role_profile = await self.db.get_role_profile(user_id)
            role_profile_id = role_profile.id if (role_profile and role_profile.is_active) else None
            
            # 3. 保存用户消息（如果需要）
            if should_save:
                await self.db.save_message(
                    user_id, 'user', message, 
                    importance, emotion, role_profile_id
                )
            
            # 4. 构建智能上下文
            messages, system_prompt = await self.memory.build_context(user_id)
            
            # 5. 添加特殊描述和指令（如果有）
            if ai_description or special_instructions:
                special_context = ""
                if ai_description:
                    special_context += f"[AI描述]: {ai_description}\n"
                if special_instructions:
                    special_context += f"[特殊指令]: {special_instructions}\n"
                
                # 将特殊上下文添加到系统提示中
                system_prompt += f"\n\n{special_context}"
                # 重建系统消息
                messages = [m for m in messages if m["role"] != "system"]
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            # 6. 添加当前消息
            messages.append({"role": "user", "content": message})
            
            logger.debug(f"上下文消息数: {len(messages)}")
            logger.debug(f"使用参数化处理: emotion={emotion_state}, description={ai_description}")
            
            # 7. 调用AI
            ai_reply = await self.ai_client.chat(
                messages,
                temperature=ChatConfig.TEMPERATURE,
                max_tokens=2000,
                timeout=ChatConfig.TIMEOUT
            )
            
            if not ai_reply:
                return None
            
            # 8. 计算AI回复的重要性
            ai_importance = self.memory.calculate_importance(ai_reply, 'assistant')
            
            # 9. 保存AI回复（如果需要）
            if should_save:
                await self.db.save_message(
                    user_id, 'assistant', ai_reply,
                    ai_importance, 'neutral', role_profile_id
                )
            
            # 10. 记录用户响应（主动聊天引擎）- 仅当不是主动聊天时
            if PROACTIVE_AVAILABLE and not is_proactive:
                # 判断对话是否会继续
                continued = len(message) > 10 or '?' in message or '吗' in message
                await proactive_service.record_user_response(user_id, message, continued)
            
            # 11. 检查是否需要创建摘要
            if should_save:
                await self._auto_create_summary(user_id, role_profile_id)
            
            return ai_reply
            
        except Exception as e:
            logger.error(f"参数化处理消息失败: {e}")
            return None
    
    async def process_message(self, user_id: str, user_message: str) -> Optional[str]:
        """
        处理用户消息的完整流程（兼容原接口）
        
        Args:
            user_id: 用户ID
            user_message: 用户消息
        
        Returns:
            AI回复文本，失败返回 None
        """
        try:
            # 1. 记录用户活动（主动聊天引擎）
            if PROACTIVE_AVAILABLE:
                await proactive_service.update_user_activity(user_id, user_message)
            
            # 2. 调用新的参数化处理方法，保持原有行为
            result = await self.process_parameterized_message(
                user_id=user_id,
                message=user_message,
                should_save=True,
                is_proactive=False
            )
            
            return result
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return None
    
    async def _auto_create_summary(self, user_id: str, role_profile_id: Optional[int] = None):
        """自动创建摘要（后台）"""
        try:
            # 获取最近的消息
            recent = await self.db.get_recent_messages(
                user_id, limit=100, role_profile_id=role_profile_id
            )
            
            if len(recent) < ChatConfig.SUMMARY_THRESHOLD:
                return
            
            # 获取未摘要的消息
            unsummarized = [m for m in recent if not m.is_summarized]
            
            if len(unsummarized) >= 10:
                # 只摘要前10条
                to_summarize = unsummarized[:10]
                
                # 转换为消息格式
                messages = [
                    {"role": m.role, "content": m.content}
                    for m in to_summarize
                ]
                
                # 创建摘要
                summary_text = await self.ai_client.create_summary(messages)
                
                # 保存摘要
                await self.db.create_summary(user_id, to_summarize, summary_text)
                
                logger.info(f"✅ 自动创建摘要: 用户 {user_id}")
                
        except Exception as e:
            logger.error(f"创建摘要失败: {e}")
    
    async def clear_memory(self, user_id: str, clear_all: bool = False):
        """
        清除记忆
        
        Args:
            user_id: 用户ID
            clear_all: 是否清除所有角色的记忆
        """
        if clear_all:
            await self.db.clear_all_conversations(user_id)
        else:
            # 只清除当前角色的记忆
            role_profile = await self.db.get_role_profile(user_id)
            role_profile_id = role_profile.id if (role_profile and role_profile.is_active) else None
            await self.db.clear_role_conversations(user_id, role_profile_id)
    
    async def get_memory_stats(self, user_id: str) -> dict:
        """
        获取记忆统计
        
        Returns:
            统计信息字典
        """
        user = await self.db.get_or_create_user(user_id)
        recent = await self.db.get_recent_messages(user_id, limit=100)
        summaries = await self.db.get_summaries(user_id, limit=10)
        important = await self.db.get_important_messages(user_id, limit=100)
        
        return {
            'total_messages': user.total_messages,
            'recent_count': len(recent),
            'important_count': len(important),
            'summary_count': len(summaries),
            'last_active': user.last_active
        }
    
    async def set_role(self, user_id: str, role_name: str) -> str:
        """
        设置角色
        
        Returns:
            生成的角色prompt
        """
        # 生成角色prompt
        role_prompt = await self.memory.generate_role_prompt(role_name)
        
        # 保存到数据库
        await self.db.set_role_profile(user_id, role_name, role_prompt)
        
        return role_prompt
    
    async def exit_role(self, user_id: str):
        """退出角色扮演"""
        await self.db.deactivate_role(user_id)


# 全局单例
_chat_service = None

def get_chat_service() -> ChatService:
    """获取全局聊天服务实例"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service

