"""
数据库服务 - Service Layer
职责：所有数据库操作
代码量：~400行
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, desc, and_, delete
from nonebot.log import logger
from datetime import datetime

# 导入模型
from models.chat_models import Base, User, Conversation, ConversationSummary, RoleProfile
from models.proactive_models import ProactiveDecision, ProactiveChatLog, UserBehaviorProfile
from models.emotion_models import DynamicEmotionProfile, EmotionChangeLog
import models.proactive_models  # 确保proactive_models的Base被注册
import models.emotion_models   # 确保emotion_models的Base被注册

# 导入配置
from services.chat.chat_config import ChatConfig


class DatabaseService:
    """数据库服务 - 处理所有数据库操作"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
    
    async def initialize(self):
        """初始化数据库"""
        self.engine = create_async_engine(
            ChatConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("数据库初始化完成")
    
    # ==================== 用户管理 ====================
    
    async def get_or_create_user(self, user_id: str) -> User:
        """获取或创建用户"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    user_id=user_id,
                    personality_type='friendly',
                    conversation_style='casual'
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"创建新用户: {user_id}")
            
            return user
    
    # ==================== 消息管理 ====================
    
    async def save_message(
        self,
        user_id: str,
        role: str,
        content: str,
        importance_score: float = 0.5,
        emotion: str = "neutral",
        role_profile_id: Optional[int] = None
    ):
        """保存消息到数据库（支持角色隔离）"""
        async with self.async_session() as session:
            msg = Conversation(
                user_id=user_id,
                role_profile_id=role_profile_id,
                role=role,
                content=content,
                importance_score=importance_score,
                emotion=emotion,
                tokens=len(content)
            )
            session.add(msg)
            
            # 更新用户统计
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.total_messages += 1
                user.last_active = datetime.now()
            
            await session.commit()
    
    async def get_recent_messages(
        self,
        user_id: str,
        limit: int = 10,
        role_profile_id: Optional[int] = None
    ) -> List[Conversation]:
        """获取最近的消息（支持按角色过滤）"""
        async with self.async_session() as session:
            query = select(Conversation).where(Conversation.user_id == user_id)
            
            # 如果指定了role_profile_id，只获取该角色的对话
            # None表示获取默认对话（无角色）
            query = query.where(Conversation.role_profile_id == role_profile_id)
            
            result = await session.execute(
                query.order_by(desc(Conversation.created_at)).limit(limit)
            )
            messages = result.scalars().all()
            return list(reversed(messages))
    
    async def get_important_messages(
        self,
        user_id: str,
        min_importance: float = 0.7,
        limit: int = 5,
        role_profile_id: Optional[int] = None
    ) -> List[Conversation]:
        """获取重要消息（支持按角色过滤）"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(
                    and_(
                        Conversation.user_id == user_id,
                        Conversation.role_profile_id == role_profile_id,
                        Conversation.importance_score >= min_importance
                    )
                )
                .order_by(desc(Conversation.importance_score))
                .limit(limit)
            )
            return result.scalars().all()
    
    # ==================== 摘要管理 ====================
    
    async def create_summary(
        self,
        user_id: str,
        messages: List[Conversation],
        summary_content: str
    ):
        """创建对话摘要"""
        async with self.async_session() as session:
            if not messages:
                return
            
            summary = ConversationSummary(
                user_id=user_id,
                summary_content=summary_content,
                original_message_count=len(messages),
                time_range_start=messages[0].created_at,
                time_range_end=messages[-1].created_at,
                importance_score=sum(m.importance_score for m in messages) / len(messages)
            )
            session.add(summary)
            
            # 标记消息为已摘要
            for msg in messages:
                result = await session.execute(
                    select(Conversation).where(Conversation.id == msg.id)
                )
                db_msg = result.scalar_one_or_none()
                if db_msg:
                    db_msg.is_summarized = True
                    db_msg.summary_id = summary.id
            
            await session.commit()
            logger.info(f"创建摘要: {len(messages)} 条消息")
    
    async def get_summaries(
        self,
        user_id: str,
        limit: int = 3,
        role_profile_id: Optional[int] = None
    ) -> List[ConversationSummary]:
        """获取历史摘要（支持按角色过滤）"""
        async with self.async_session() as session:
            result = await session.execute(
                select(ConversationSummary)
                .where(
                    and_(
                        ConversationSummary.user_id == user_id,
                        ConversationSummary.role_profile_id == role_profile_id
                    )
                )
                .order_by(desc(ConversationSummary.created_at))
                .limit(limit)
            )
            return result.scalars().all()
    
    # ==================== 角色管理 ====================
    
    async def get_role_profile(self, user_id: str) -> Optional[RoleProfile]:
        """获取用户当前激活的角色设定"""
        async with self.async_session() as session:
            result = await session.execute(
                select(RoleProfile).where(
                    and_(
                        RoleProfile.user_id == user_id,
                        RoleProfile.is_active == True
                    )
                )
            )
            return result.scalar_one_or_none()
    
    async def set_role_profile(self, user_id: str, role_name: str, role_prompt: str):
        """设置用户的角色（智能切换）"""
        async with self.async_session() as session:
            # 先停用所有当前用户的角色
            result = await session.execute(
                select(RoleProfile).where(RoleProfile.user_id == user_id)
            )
            all_roles = result.scalars().all()
            for r in all_roles:
                r.is_active = False
            
            # 查找是否已存在同名角色
            result = await session.execute(
                select(RoleProfile).where(
                    and_(
                        RoleProfile.user_id == user_id,
                        RoleProfile.role_name == role_name
                    )
                )
            )
            existing_role = result.scalar_one_or_none()
            
            if existing_role:
                # 角色已存在，激活它并更新prompt
                existing_role.is_active = True
                existing_role.role_prompt = role_prompt
                existing_role.updated_at = datetime.now()
                logger.info(f"用户 {user_id} 切换到已有角色: {role_name}")
            else:
                # 角色不存在，创建新角色
                new_role = RoleProfile(
                    user_id=user_id,
                    role_name=role_name,
                    role_prompt=role_prompt,
                    is_active=True
                )
                session.add(new_role)
                logger.info(f"用户 {user_id} 创建新角色: {role_name}")
            
            await session.commit()
    
    async def deactivate_role(self, user_id: str):
        """退出角色扮演（停用所有角色）"""
        async with self.async_session() as session:
            result = await session.execute(
                select(RoleProfile).where(RoleProfile.user_id == user_id)
            )
            roles = result.scalars().all()
            
            for role in roles:
                role.is_active = False
                role.updated_at = datetime.now()
            
            await session.commit()
            logger.info(f"用户 {user_id} 退出角色扮演")
    
    async def list_user_roles(self, user_id: str) -> List[RoleProfile]:
        """列出用户的所有角色"""
        async with self.async_session() as session:
            result = await session.execute(
                select(RoleProfile)
                .where(RoleProfile.user_id == user_id)
                .order_by(desc(RoleProfile.updated_at))
            )
            return result.scalars().all()
    
    async def switch_role(self, user_id: str, role_profile_id: int):
        """切换到指定角色"""
        async with self.async_session() as session:
            # 先取消所有角色的激活状态
            result = await session.execute(
                select(RoleProfile).where(RoleProfile.user_id == user_id)
            )
            roles = result.scalars().all()
            for role in roles:
                role.is_active = False
            
            # 激活指定角色
            result = await session.execute(
                select(RoleProfile).where(RoleProfile.id == role_profile_id)
            )
            target_role = result.scalar_one_or_none()
            if target_role:
                target_role.is_active = True
                target_role.updated_at = datetime.now()
                await session.commit()
                logger.info(f"用户 {user_id} 切换到角色 {target_role.role_name}")
                return target_role
            return None
    
    async def delete_role_profile(self, user_id: str, role_profile_id: int):
        """删除指定角色及其所有对话"""
        async with self.async_session() as session:
            # 先删除该角色的所有对话
            await session.execute(
                delete(Conversation).where(
                    and_(
                        Conversation.user_id == user_id,
                        Conversation.role_profile_id == role_profile_id
                    )
                )
            )
            # 删除摘要
            await session.execute(
                delete(ConversationSummary).where(
                    and_(
                        ConversationSummary.user_id == user_id,
                        ConversationSummary.role_profile_id == role_profile_id
                    )
                )
            )
            # 删除角色本身
            await session.execute(
                delete(RoleProfile).where(RoleProfile.id == role_profile_id)
            )
            await session.commit()
            logger.info(f"用户 {user_id} 删除角色 {role_profile_id}")
    
    # ==================== 清理操作 ====================
    
    async def clear_role_conversations(self, user_id: str, role_profile_id: Optional[int] = None):
        """清除指定角色的对话记录"""
        async with self.async_session() as session:
            # 删除对话
            await session.execute(
                delete(Conversation).where(
                    and_(
                        Conversation.user_id == user_id,
                        Conversation.role_profile_id == role_profile_id
                    )
                )
            )
            # 删除摘要
            await session.execute(
                delete(ConversationSummary).where(
                    and_(
                        ConversationSummary.user_id == user_id,
                        ConversationSummary.role_profile_id == role_profile_id
                    )
                )
            )
            await session.commit()
            logger.info(f"用户 {user_id} 清除角色 {role_profile_id} 的对话记录")
    
    async def clear_all_conversations(self, user_id: str):
        """清除用户的所有对话记录（所有角色）"""
        async with self.async_session() as session:
            # 删除所有对话
            await session.execute(
                delete(Conversation).where(Conversation.user_id == user_id)
            )
            # 删除所有摘要
            await session.execute(
                delete(ConversationSummary).where(ConversationSummary.user_id == user_id)
            )
            # 重置消息计数
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.total_messages = 0
            
            await session.commit()
            logger.info(f"用户 {user_id} 清除所有对话记录")


# 全局单例
_database_service = None

def get_database_service() -> DatabaseService:
    """获取全局数据库服务实例"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service






