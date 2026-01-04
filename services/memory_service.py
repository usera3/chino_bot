"""
记忆服务 - 管理对话历史和记忆检索
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from nonebot.log import logger
from sqlalchemy import desc, and_, or_
from models.memory_models import (
    ChatMessage, MemoryIndex, UserProfile, GroupProfile, RoleSettings,
    get_db_session, init_database
)


class MemoryService:
    """记忆管理服务"""
    
    def __init__(self):
        # 初始化数据库
        init_database()
        logger.success("✅ 记忆服务初始化完成")
    
    async def save_message(
        self,
        user_id: str,
        role: str,
        content: str,
        group_id: Optional[str] = None
    ) -> int:
        """
        保存对话消息
        
        Args:
            user_id: 用户QQ号
            role: 'user' 或 'assistant'
            content: 消息内容
            group_id: 群号（私聊为None）
        
        Returns:
            消息ID
        """
        session = get_db_session()
        try:
            context_type = 'group' if group_id else 'private'
            
            message = ChatMessage(
                user_id=user_id,
                group_id=group_id,
                role=role,
                content=content,
                context_type=context_type,
                timestamp=datetime.now()
            )
            
            session.add(message)
            session.commit()
            
            message_id = message.id
            
            # 更新用户/群组画像
            await self._update_profile(user_id, group_id, session)
            
            logger.debug(f"💾 保存消息: {context_type} | {role} | {content[:30]}...")
            
            return message_id
        finally:
            session.close()
    
    async def _update_profile(self, user_id: str, group_id: Optional[str], session):
        """更新用户/群组画像"""
        # 更新用户画像
        user_profile = session.query(UserProfile).filter_by(user_id=user_id).first()
        if not user_profile:
            user_profile = UserProfile(
                user_id=user_id,
                total_messages=0,
                intimacy_level=0.0
            )
            session.add(user_profile)
        
        # 确保字段不为None
        if user_profile.total_messages is None:
            user_profile.total_messages = 0
        if user_profile.intimacy_level is None:
            user_profile.intimacy_level = 0.0
        
        user_profile.last_chat = datetime.now()
        user_profile.total_messages += 1
        user_profile.intimacy_level = min(100, user_profile.intimacy_level + 0.1)
        
        # 更新群组画像
        if group_id:
            group_profile = session.query(GroupProfile).filter_by(group_id=group_id).first()
            if not group_profile:
                group_profile = GroupProfile(
                    group_id=group_id,
                    total_messages=0
                )
                session.add(group_profile)
            
            # 确保字段不为None
            if group_profile.total_messages is None:
                group_profile.total_messages = 0
            
            group_profile.last_active = datetime.now()
            group_profile.total_messages += 1
        
        session.commit()
    
    async def get_recent_history(
        self,
        user_id: str,
        group_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        获取最近的对话历史
        
        Args:
            user_id: 用户QQ号
            group_id: 群号
            limit: 返回数量
        
        Returns:
            对话历史列表
        """
        session = get_db_session()
        try:
            query = session.query(ChatMessage).filter_by(user_id=user_id)
            
            if group_id:
                # 群聊：只返回该群的历史
                query = query.filter_by(group_id=group_id)
            else:
                # 私聊：只返回私聊历史
                query = query.filter(ChatMessage.group_id.is_(None))
            
            messages = query.order_by(desc(ChatMessage.timestamp)).limit(limit).all()
            
            # 转换为字典列表（时间倒序改为正序）
            history = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp
                }
                for msg in reversed(messages)
            ]
            
            return history
        finally:
            session.close()
    
    async def get_cross_context_memory(
        self,
        user_id: str,
        current_group_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        获取跨场景记忆（私聊+群聊）
        
        当用户在群里聊天时，也会检索他的私聊记忆
        
        Args:
            user_id: 用户QQ号
            current_group_id: 当前群号
            limit: 返回数量
        
        Returns:
            跨场景记忆列表
        """
        session = get_db_session()
        try:
            # 如果在群里，检索私聊记忆
            if current_group_id:
                private_messages = session.query(ChatMessage).filter(
                    and_(
                        ChatMessage.user_id == user_id,
                        ChatMessage.group_id.is_(None)
                    )
                ).order_by(desc(ChatMessage.timestamp)).limit(limit).all()
                
                if private_messages:
                    logger.info(f"🔗 找到 {len(private_messages)} 条私聊记忆")
                    return [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.timestamp,
                            "source": "private_chat"
                        }
                        for msg in reversed(private_messages)
                    ]
            
            return []
        finally:
            session.close()
    
    async def search_relevant_memory(
        self,
        user_id: str,
        query: str,
        group_id: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        语义搜索相关记忆（简化版RAG）
        
        Args:
            user_id: 用户QQ号
            query: 查询文本
            group_id: 群号
            limit: 返回数量
        
        Returns:
            相关记忆列表
        """
        session = get_db_session()
        try:
            # 简单的关键词匹配（后续可以升级为向量检索）
            query_lower = query.lower()
            
            # 构建查询
            base_query = session.query(ChatMessage).filter_by(user_id=user_id)
            
            if group_id:
                base_query = base_query.filter_by(group_id=group_id)
            else:
                base_query = base_query.filter(ChatMessage.group_id.is_(None))
            
            # 关键词搜索
            messages = base_query.filter(
                ChatMessage.content.like(f'%{query}%')
            ).order_by(desc(ChatMessage.timestamp)).limit(limit).all()
            
            if messages:
                logger.info(f"🔍 找到 {len(messages)} 条相关记忆")
                return [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    }
                    for msg in messages
                ]
            
            return []
        finally:
            session.close()
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """获取用户画像"""
        session = get_db_session()
        try:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if profile:
                return {
                    "user_id": profile.user_id,
                    "nickname": profile.nickname,
                    "intimacy_level": profile.intimacy_level,
                    "total_messages": profile.total_messages,
                    "first_met": profile.first_met
                }
            return None
        finally:
            session.close()
    
    async def get_role_settings(self, role_name: str = "香风智乃") -> Optional[Dict]:
        """获取角色设定"""
        session = get_db_session()
        try:
            role = session.query(RoleSettings).filter_by(role_name=role_name, is_active=1).first()
            if role:
                return {
                    "role_name": role.role_name,
                    "role_description": role.role_description,
                    "personality": role.personality,
                    "speaking_style": role.speaking_style,
                    "background_story": role.background_story
                }
            return None
        finally:
            session.close()


# 全局单例
_memory_service: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    """获取记忆服务实例"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service

