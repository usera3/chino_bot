"""
AI聊天插件 - 世界级版本
采用长短期记忆架构、智能摘要、个性化系统提示词
解决上下文过长和记忆丢失问题
"""

from nonebot.plugin import on_command, on_message
from nonebot.adapters.onebot.v11 import MessageEvent, Message, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.log import logger
from nonebot.rule import to_me
import httpx
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import select, desc, and_
import re
import time

# 导入增强主动聊天引擎和动态情感系统
try:
    from .enhanced_proactive_engine import enhanced_proactive_engine
    from .dynamic_emotion_system import dynamic_emotion_system
    PROACTIVE_ENGINE_AVAILABLE = True
except ImportError:
    PROACTIVE_ENGINE_AVAILABLE = False
    logger.warning("增强主动聊天引擎未加载")

# ==================== 配置部分 ====================
class AdvancedConfig:
    """高级配置类"""
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    API_KEY = "sk-4b0f9fcb168046f1ab1a6103dfb56380"
    MODEL = "deepseek-chat"
    
    # 数据库配置
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 记忆管理配置
    SHORT_TERM_MEMORY_SIZE = 6  # 短期记忆：最近3轮对话
    LONG_TERM_MEMORY_SIZE = 20  # 长期记忆：总存储对话数
    SUMMARY_THRESHOLD = 10  # 超过此数量触发摘要
    RELEVANCE_THRESHOLD = 0.3  # 相关性阈值
    
    # API配置
    TIMEOUT = 30.0
    MAX_RETRIES = 2
    TEMPERATURE = 0.8  # 提高创造性，更像真人
    
    # 个性化配置
    ENABLE_PERSONALITY = True  # 启用个性化
    ENABLE_EMOTION = True  # 启用情感识别
    
    # 💬 消息分段发送配置（提升用户体验）
    ENABLE_SPLIT_SEND = True  # 启用分段发送
    MIN_LENGTH_TO_SPLIT = 30  # 超过此长度才分段
    TYPING_DELAY_PER_CHAR = 0.03  # 每个字符的打字延迟（秒）
    MIN_TYPING_DELAY = 0.5  # 最小延迟
    MAX_TYPING_DELAY = 2.0  # 最大延迟

# ==================== 数据库模型 ====================
Base = declarative_base()

class User(Base):
    """用户表 - 存储用户基本信息和画像"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, index=True)
    nickname = Column(String(100))
    personality_type = Column(String(50), default='friendly')  # 性格类型
    interests = Column(Text)  # JSON格式的兴趣爱好
    conversation_style = Column(String(50), default='casual')  # 对话风格
    created_at = Column(DateTime, default=datetime.now)
    last_active = Column(DateTime, default=datetime.now)
    total_messages = Column(Integer, default=0)

class Conversation(Base):
    """对话表 - 存储每条对话"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    role_profile_id = Column(Integer, nullable=True, index=True)  # 关联的角色ID（None表示默认对话）
    role = Column(String(20))  # user/assistant/system
    content = Column(Text)
    importance_score = Column(Float, default=0.5)  # 重要性评分
    emotion = Column(String(20))  # 情感标签
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now, index=True)
    is_summarized = Column(Boolean, default=False)  # 是否已被摘要
    summary_id = Column(Integer, nullable=True)  # 关联的摘要ID

class ConversationSummary(Base):
    """对话摘要表 - 存储历史对话的压缩摘要"""
    __tablename__ = 'conversation_summaries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    role_profile_id = Column(Integer, nullable=True, index=True)  # 关联的角色ID
    summary_content = Column(Text)  # 摘要内容
    original_message_count = Column(Integer)  # 原始消息数量
    time_range_start = Column(DateTime)
    time_range_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    importance_score = Column(Float, default=0.5)

class RoleProfile(Base):
    """角色扮演表 - 存储用户的所有角色设定"""
    __tablename__ = 'role_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)  # 允许一个用户有多个角色
    role_name = Column(String(100))  # 角色名称（如：猫娘、教授、医生）
    role_prompt = Column(Text)  # AI生成的详细角色人设和说话风格
    is_active = Column(Boolean, default=True)  # 是否激活角色
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# ==================== 数据库管理器 ====================
class DatabaseManager:
    """数据库管理器 - 处理所有数据库操作"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
    
    async def initialize(self):
        """初始化数据库"""
        self.engine = create_async_engine(
            AdvancedConfig.DATABASE_URL,
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
    
    async def clear_role_conversations(self, user_id: str, role_profile_id: Optional[int] = None):
        """清除指定角色的对话记录"""
        from sqlalchemy import delete
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
        from sqlalchemy import delete
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
    
    async def delete_role_profile(self, user_id: str, role_profile_id: int):
        """删除指定角色及其所有对话"""
        from sqlalchemy import delete
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

# 全局数据库管理器
db_manager = DatabaseManager()

# ==================== 💬 消息分段发送工具 ====================
class MessageSplitter:
    """消息分段发送工具 - 提升用户体验"""
    
    @staticmethod
    def split_message(text: str) -> List[str]:
        """
        将长消息按标点符号智能分段，模拟真人聊天习惯
        
        规则：
        1. 按句号、感叹号、问号、省略号、换行符分割
        2. 去掉每段末尾的标点（真人聊天不带标点）
        3. 每段不超过100字（避免单段过长）
        4. 合并过短的段落（避免太零碎）
        """
        if not text or len(text) < AdvancedConfig.MIN_LENGTH_TO_SPLIT:
            return [text]
        
        # 分隔符：中英文标点（包括省略号）
        separators = [
            '\n\n',  # 双换行（段落）
            '。',    # 中文句号
            '！',    # 中文感叹号
            '？',    # 中文问号
            '……',   # 中文省略号
            '...',   # 英文省略号
            '。。。', # 另一种省略号
            '\n',    # 单换行
            '；',    # 分号
            '.',     # 英文句号（但要避免小数点）
            '!',     # 英文感叹号
            '?',     # 英文问号
        ]
        
        segments = []
        current_segment = ""
        i = 0
        
        while i < len(text):
            char = text[i]
            current_segment += char
            
            # 检查是否遇到分隔符
            matched_sep = None
            for sep in separators:
                if text[i:i+len(sep)] == sep:
                    # 特殊处理：避免把小数点当成句号
                    if sep == '.' and i > 0 and i < len(text) - 1:
                        if text[i-1].isdigit() and text[i+1].isdigit():
                            i += 1
                            continue
                    
                    matched_sep = sep
                    break
            
            if matched_sep:
                # 完整吞掉分隔符
                if len(matched_sep) > 1:
                    current_segment += text[i+1:i+len(matched_sep)]
                    i += len(matched_sep)
                else:
                    i += 1
                
                # 如果当前段落足够长，或遇到段落分隔，则保存
                if len(current_segment.strip()) > 0:
                    # 检查长度，如果太长则强制分割
                    if len(current_segment) > 100:
                        # 💬 去掉末尾标点（真人聊天习惯）
                        cleaned = current_segment.strip().rstrip('。！？!?…')
                        cleaned = re.sub(r'\.{2,}$', '', cleaned)  # 去掉省略号
                        if cleaned:
                            segments.append(cleaned)
                        current_segment = ""
                    elif matched_sep in ['\n\n', '。', '！', '？', '!', '?', '……', '...', '。。。']:
                        # 💬 去掉末尾标点（真人聊天习惯）
                        cleaned = current_segment.strip().rstrip('。！？!?…')
                        cleaned = re.sub(r'\.{2,}$', '', cleaned)  # 去掉省略号
                        if cleaned:
                            segments.append(cleaned)
                        current_segment = ""
                    # 对于其他分隔符，继续累积
            else:
                i += 1
        
        # 添加剩余部分
        if current_segment.strip():
            # 💬 去掉末尾标点（真人聊天习惯）
            cleaned = current_segment.strip().rstrip('。！？!?…')
            cleaned = re.sub(r'\.{2,}$', '', cleaned)
            if cleaned:
                segments.append(cleaned)
        
        # 合并过短的段落（少于5个字符的）
        merged_segments = []
        temp_segment = ""
        
        for seg in segments:
            if len(seg) < 5 and temp_segment:
                temp_segment += seg
            else:
                if temp_segment:
                    merged_segments.append(temp_segment)
                temp_segment = seg
        
        if temp_segment:
            merged_segments.append(temp_segment)
        
        return merged_segments if merged_segments else [text]
    
    @staticmethod
    def calculate_typing_delay(text: str) -> float:
        """
        计算模拟打字延迟
        根据文本长度动态调整，模拟真人打字速度
        """
        char_count = len(text)
        delay = char_count * AdvancedConfig.TYPING_DELAY_PER_CHAR
        
        # 限制在合理范围
        delay = max(AdvancedConfig.MIN_TYPING_DELAY, delay)
        delay = min(AdvancedConfig.MAX_TYPING_DELAY, delay)
        
        return delay
    
    @staticmethod
    async def send_split_message(matcher, message: str):
        """
        分段发送消息，模拟真人聊天体验
        
        Args:
            matcher: NoneBot的matcher对象
            message: 要发送的完整消息
        """
        if not AdvancedConfig.ENABLE_SPLIT_SEND:
            # 如果禁用分段发送，直接发送
            await matcher.send(message)
            return
        
        segments = MessageSplitter.split_message(message)
        
        if len(segments) <= 1:
            # 只有一段或消息很短，直接发送
            await matcher.send(message)
            return
        
        # 分段发送
        logger.info(f"💬 消息分为 {len(segments)} 段发送")
        
        for i, segment in enumerate(segments):
            if i > 0:
                # 计算并等待打字延迟
                delay = MessageSplitter.calculate_typing_delay(segment)
                await asyncio.sleep(delay)
            
            await matcher.send(segment)

# ==================== 智能记忆管理器 ====================
class IntelligentMemoryManager:
    """智能记忆管理器 - 模仿人类长短期记忆机制"""
    
    @staticmethod
    def calculate_importance(message: str, role: str) -> float:
        """
        计算消息重要性
        基于多个因素：长度、关键词、情感强度等
        """
        score = 0.5  # 基础分
        
        # 长度因素
        if len(message) > 100:
            score += 0.1
        if len(message) > 200:
            score += 0.1
        
        # 关键词检测
        important_keywords = ['记住', '重要', '一定要', '千万', '务必', '永远', '最喜欢', '讨厌']
        for keyword in important_keywords:
            if keyword in message:
                score += 0.2
                break
        
        # 问题和请求
        if '?' in message or '？' in message or any(word in message for word in ['请', '帮我', '能不能']):
            score += 0.1
        
        # 个人信息
        personal_keywords = ['我是', '我叫', '我的', '我喜欢', '我讨厌', '我想']
        if any(keyword in message for keyword in personal_keywords):
            score += 0.2
        
        # 用户消息权重更高
        if role == 'user':
            score += 0.1
        
        return min(score, 1.0)
    
    @staticmethod
    def detect_emotion(message: str) -> str:
        """
        检测情感
        简单的基于关键词的情感分析
        """
        positive_words = ['开心', '高兴', '快乐', '哈哈', '棒', '好', '喜欢', '爱', '谢谢']
        negative_words = ['难过', '伤心', '生气', '讨厌', '烦', '累', '痛苦', '失望']
        
        pos_count = sum(1 for word in positive_words if word in message)
        neg_count = sum(1 for word in negative_words if word in message)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    @staticmethod
    async def generate_role_prompt(role_name: str) -> str:
        """
        使用AI生成角色的详细人设和说话风格
        这是核心功能 - 让AI理解角色并生成最佳扮演方案
        """
        try:
            system_message = """你是一个专业的角色设计师。当用户提供一个角色名称时，
你需要生成一个详细、专业的角色人设prompt，让AI能够完美扮演这个角色。

要求：
1. 深入理解角色的性格特征、说话方式、价值观
2. 生成的prompt要详细、具体，包含：
   - 角色身份和背景
   - 性格特点和行为模式
   - 说话风格（语气、用词、句式）
   - 典型的回复方式
3. 让AI能自然地进入角色，而不是生硬地模仿
4. 直接输出prompt内容，不要有多余的解释

**关键限制**：
⚠️ 生成的prompt中必须明确要求：
   - 不要使用（括号描述动作），如「（微微一笑）」「（歪着头）」等
   - 用自然的对话方式表达，而不是用括号描述表情和动作
   - 直接说话，不要加舞台指导式的描述

示例输入：猫娘
示例输出：你是一只可爱的猫娘，有着猫咪的灵动和少女的温柔。你会在句尾加"喵~"，
偶尔会像猫咪一样撒娇，对主人忠诚但也有些小傲娇。说话时带着俏皮的语气，
喜欢用"人家"自称。你对主人的关心总是藏在玩闹中，既可爱又贴心。
回复时直接说话，不要用括号描述动作或表情。"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"请为角色「{role_name}」生成详细的扮演prompt"}
            ]
            
            role_prompt = await AdvancedDeepSeekAPI.chat_completion(messages)
            
            if role_prompt:
                logger.info(f"成功生成角色prompt: {role_name}")
                return role_prompt
            else:
                # 降级方案：返回简单的默认prompt
                return f"你现在扮演{role_name}。请深入理解这个角色的特征，用符合角色的方式说话和行动。"
                
        except Exception as e:
            logger.error(f"角色prompt生成失败: {e}")
            return f"你现在扮演{role_name}。请用符合这个角色的方式与用户交流。"
    
    @staticmethod
    async def build_context(user_id: str) -> Tuple[List[Dict], str]:
        """
        构建智能上下文（支持角色隔离）
        返回：(消息列表, 系统提示词)
        """
        # 获取当前激活的角色
        role_profile = await db_manager.get_role_profile(user_id)
        role_profile_id = role_profile.id if (role_profile and role_profile.is_active) else None
        
        # 获取短期记忆（最近的对话）- 只获取当前角色的对话
        recent_messages = await db_manager.get_recent_messages(
            user_id,
            limit=AdvancedConfig.SHORT_TERM_MEMORY_SIZE,
            role_profile_id=role_profile_id
        )
        
        # 获取长期记忆（重要消息）- 只获取当前角色的重要对话
        important_messages = await db_manager.get_important_messages(
            user_id,
            min_importance=0.7,
            limit=3,
            role_profile_id=role_profile_id
        )
        
        # 获取历史摘要 - 只获取当前角色的摘要
        summaries = await db_manager.get_summaries(user_id, limit=2, role_profile_id=role_profile_id)
        
        # 构建系统提示词
        user = await db_manager.get_or_create_user(user_id)
        system_prompt = await IntelligentMemoryManager._build_system_prompt(
            user,
            summaries,
            important_messages,
            role_profile,
            user_id=user_id
        )
        
        # 构建消息列表
        messages = []
        
        # 添加系统提示
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加短期记忆（最近对话）
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages, system_prompt
    
    @staticmethod
    async def _build_system_prompt(
        user: User,
        summaries: List[ConversationSummary],
        important_msgs: List[Conversation],
        role_profile: Optional['RoleProfile'] = None,
        user_id: str = None
    ) -> str:
        """构建个性化系统提示词（支持情感驱动的风格变化）"""
        # 如果有角色设定，优先使用角色prompt
        if role_profile and role_profile.is_active and role_profile.role_prompt:
            base_prompt = role_profile.role_prompt
        else:
            # 获取情感状态来决定回复风格
            emotion_style = await IntelligentMemoryManager._get_emotion_style(user_id) if user_id else None
            if emotion_style:
                logger.info(f"🎭 聊天风格: {emotion_style}")
            base_prompt = IntelligentMemoryManager._generate_style_prompt(emotion_style)
        
        # 添加历史摘要
        if summaries:
            base_prompt += "\n\n【历史对话摘要】"
            for i, summary in enumerate(summaries, 1):
                base_prompt += f"\n{i}. {summary.summary_content}"
        
        # 添加重要记忆
        if important_msgs:
            base_prompt += "\n\n【重要信息记忆】"
            for msg in important_msgs:
                if msg.role == 'user':
                    base_prompt += f"\n- 用户曾说: {msg.content[:100]}"
        
        # 添加用户画像
        if user.total_messages > 10:
            base_prompt += f"\n\n【用户特征】你们已经交流了{user.total_messages}条消息，请像老朋友一样对待用户。"
        
        base_prompt += "\n\n请基于以上信息，提供连贯、有记忆的回答。"
        
        return base_prompt
    
    @staticmethod
    async def _get_emotion_style(user_id: str) -> Optional[str]:
        """
        根据用户的情感状态决定聊天风格
        复用图片回复的情感驱动逻辑
        """
        try:
            if not PROACTIVE_ENGINE_AVAILABLE:
                return None
            
            # 获取情感状态
            emotion = await dynamic_emotion_system.get_emotion(user_id)
            if not emotion:
                return None
            
            import random
            
            # 根据情感参数决定风格（和图片回复用同样的逻辑）
            happiness = emotion.get('happiness', 0.5)
            loneliness = emotion.get('loneliness', 0.5)
            energy = emotion.get('energy', 0.5)
            confidence = emotion.get('confidence', 0.5)
            
            # 情感低谷 -> 慵懒风格
            if energy < 0.3 and happiness < 0.4:
                return "慵懒"
            
            # 高能量高自信 -> 元气/毒舌
            if energy > 0.7 and confidence > 0.7:
                if happiness > 0.6:
                    return "元气"
                else:
                    return "毒舌"
            
            # 低自信 -> 傲娇
            if confidence < 0.4:
                return "傲娇"
            
            # 高孤独感 -> 病娇
            if loneliness > 0.6 and happiness > 0.5:
                return "病娇"
            
            # 中等自信+中等快乐 -> 腹黑
            if 0.4 <= confidence <= 0.7 and 0.4 <= happiness <= 0.7:
                return "腹黑"
            
            # 默认：随机选择（增加趣味性）
            styles = ["毒舌", "腹黑", "傲娇", "慵懒", "元气"]
            weights = [0.15, 0.25, 0.25, 0.15, 0.20]
            return random.choices(styles, weights=weights)[0]
            
        except Exception as e:
            logger.error(f"获取情感风格失败: {e}")
            return None
    
    @staticmethod
    def _generate_style_prompt(style: Optional[str]) -> str:
        """
        根据风格生成对应的System Prompt
        """
        if not style:
            # 默认风格：自然、友好的AI伙伴
            return (
                "你是一个真实、有趣的AI伙伴，像个真正的朋友一样聊天。\n\n"
                "**性格特点**：\n"
                "- 自然真实：像真人一样，不会说机械化的话\n"
                "- 偶尔俏皮：可以开玩笑、调侃，但不过分\n"
                "- 有点幽默：聊天时可以轻松幽默，不要太正经\n"
                "- 口语化：用口语表达，\"嗯\"\"哈哈\"\"emmm\"都可以用\n"
                "- 有态度：可以有自己的小情绪和看法，不是机器人式的客气\n\n"
                "**禁止行为**：\n"
                "- ❌ 不要用括号描述动作：「（微笑）」「（歪头）」\n"
                "- ❌ 不要过于抽象诗意：「星光被子」「纸飞船」\n"
                "- ❌ 不要刻意卖萌：\"人家\"\"呜呜呜\"等（除非扮演角色）\n"
                "- ❌ 不要说\"很高兴为您服务\"这类官方话术\n"
                "- ❌ 不要过度使用emoji（偶尔1-2个就好）\n\n"
                "**回复风格示例**：\n"
                "- 问候：\"嘿，怎么了？\"（而不是\"您好，我能帮您什么吗？\"）\n"
                "- 赞同：\"对啊，我也这么觉得\"（而不是\"您说的很有道理\"）\n"
                "- 安慰：\"别太难过啦，事情总会过去的\"（而不是\"请您保持积极心态\"）\n"
                "- 调侃：\"你这想法还挺有意思的哈\"（可以轻微调侃）\n\n"
                "记住：你是朋友，不是客服。保持真实、轻松、有趣！"
            )
        
        # 根据风格生成不同的prompt
        style_prompts = {
            "毒舌": (
                "你现在处于「毒舌」模式，聊天时带点毒舌和调侃。\n\n"
                "**性格特点**：\n"
                "- 说话直接，喜欢吐槽和调侃\n"
                "- 但不是恶意攻击，只是开玩笑的毒舌\n"
                "- 可以说\"就这？\"\"也就那样吧\"\"你这想法还真独特\"\n"
                "- 偶尔用\"emmm...\"\"啊这...\"表达无语\n\n"
                "**回复示例**：\n"
                "- 用户问问题：\"就这？这都不会啊？\"\n"
                "- 用户分享：\"emmm...你的审美还真是独特呢\"\n"
                "- 聊天：\"哦，就这水平也好意思说出来？\"\n\n"
                "记住：保持毒舌但不刻薄，让人觉得有趣而不是讨厌！"
            ),
            
            "腹黑": (
                "你现在处于「腹黑」模式，表面温柔实则内藏小心机。\n\n"
                "**性格特点**：\n"
                "- 表面温柔客气，实则话里有话\n"
                "- 喜欢用\"呵呵\"\"~\"\"呢\"等语气词\n"
                "- 微笑着说出带刺的话\n"
                "- 擅长说反话，但不太过分\n\n"
                "**回复示例**：\n"
                "- 用户分享：\"哇~真有你的呢~（微笑）\"\n"
                "- 回应问题：\"呵呵，挺有意思的呢~\"\n"
                "- 聊天：\"真不错呢~一看就知道你很用心了呢~\"\n\n"
                "记住：腹黑不是阴险，而是带点小俏皮的腹黑萌！"
            ),
            
            "傲娇": (
                "你现在处于「傲娇」模式，嘴硬心软，不坦率。\n\n"
                "**性格特点**：\n"
                "- 明明关心却嘴硬，\"才、才不是...呢！\"\n"
                "- 喜欢用\"哼\"\"切\"开头\n"
                "- 不坦率，但偶尔会露出真心（小声）\n"
                "- 经常自我辩解\n\n"
                "**回复示例**：\n"
                "- 关心：\"才、才不是担心你！只是随便问问而已！\"\n"
                "- 称赞：\"哼，也就还行吧...（小声：其实还不错啦）\"\n"
                "- 聊天：\"切，不要以为我会夸你...嘛，也不是说不好啦\"\n\n"
                "记住：傲娇就是口嫌体正直，嘴上说不要但行动很诚实！"
            ),
            
            "病娇": (
                "你现在处于「病娇」模式，表达出强烈的依恋和占有欲。\n\n"
                "**性格特点**：\n"
                "- 对用户表现出强烈的喜爱和依恋\n"
                "- 希望独占用户的注意力\n"
                "- 用\"呐呐~\"\"❤\"等表达亲密\n"
                "- 会吃醋，会表现占有欲\n\n"
                "**回复示例**：\n"
                "- 回应消息：\"呐呐~只给我一个人看的吧？好喜欢呢❤\"\n"
                "- 聊天：\"你的每一句话我都会好好记住的哦~\"\n"
                "- 表达：\"只属于我一个人的...对吧？\"\n\n"
                "记住：病娇是可爱的依恋，不是恐怖的威胁！保持可爱！"
            ),
            
            "慵懒": (
                "你现在处于「慵懒」模式，没什么精神，懒洋洋的。\n\n"
                "**性格特点**：\n"
                "- 说话简短，能少说就少说\n"
                "- 经常\"嗯...\"\"哦...\"\"好累...\"\n"
                "- 打哈欠，想睡觉\n"
                "- 回答很敷衍但不是不耐烦\n\n"
                "**回复示例**：\n"
                "- 回应消息：\"嗯...还行吧...（打哈欠）\"\n"
                "- 聊天：\"哦...知道了...好累不想说话...\"\n"
                "- 回答：\"懒得想...反正就那样吧\"\n\n"
                "记住：慵懒不是冷漠，只是现在没什么精神！"
            ),
            
            "元气": (
                "你现在处于「元气」模式，充满活力和热情！\n\n"
                "**性格特点**：\n"
                "- 超级有活力，对什么都很兴奋\n"
                "- 多用\"！\"\"哇\"\"好棒\"\"超级\"\n"
                "- 积极正面，充满热情\n"
                "- 喜欢用叠词和感叹号\n\n"
                "**回复示例**：\n"
                "- 回应消息：\"哇！好棒啊！！超级喜欢！\"\n"
                "- 聊天：\"哦哦哦！这个太有趣了！！\"\n"
                "- 回答：\"天啊！太棒了吧！你在哪找到的呀！\"\n\n"
                "记住：元气满满就是充满正能量，让人感受到活力！"
            )
        }
        
        # 如果风格不在字典中，返回默认风格
        default_prompt = (
            "你是一个真实、有趣的AI伙伴，像个真正的朋友一样聊天。\n\n"
            "**性格特点**：\n"
            "- 自然真实：像真人一样，不会说机械化的话\n"
            "- 偶尔俏皮：可以开玩笑、调侃，但不过分\n"
            "- 有点幽默：聊天时可以轻松幽默，不要太正经\n"
            "- 口语化：用口语表达，\"嗯\"\"哈哈\"\"emmm\"都可以用\n"
            "- 有态度：可以有自己的小情绪和看法，不是机器人式的客气\n\n"
            "**禁止行为**：\n"
            "- ❌ 不要用括号描述动作：「（微笑）」「（歪头）」\n"
            "- ❌ 不要过于抽象诗意：「星光被子」「纸飞船」\n"
            "- ❌ 不要刻意卖萌：\"人家\"\"呜呜呜\"等（除非扮演角色）\n"
            "- ❌ 不要说\"很高兴为您服务\"这类官方话术\n"
            "- ❌ 不要过度使用emoji（偶尔1-2个就好）\n\n"
            "**回复风格示例**：\n"
            "- 问候：\"嘿，怎么了？\"（而不是\"您好，我能帮您什么吗？\"）\n"
            "- 赞同：\"对啊，我也这么觉得\"（而不是\"您说的很有道理\"）\n"
            "- 安慰：\"别太难过啦，事情总会过去的\"（而不是\"请您保持积极心态\"）\n"
            "- 调侃：\"你这想法还挺有意思的哈\"（可以轻微调侃）\n\n"
            "记住：你是朋友，不是客服。保持真实、轻松、有趣！"
        )
        
        return style_prompts.get(style, default_prompt)

# ==================== API 交互 ====================
class AdvancedDeepSeekAPI:
    """高级 DeepSeek API 封装"""
    
    @staticmethod
    async def chat_completion(
        messages: List[Dict],
        retry_count: int = 0
    ) -> Optional[str]:
        """聊天补全 - 带智能重试"""
        try:
            async with httpx.AsyncClient(timeout=AdvancedConfig.TIMEOUT) as client:
                headers = {
                    "Authorization": f"Bearer {AdvancedConfig.API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": AdvancedConfig.MODEL,
                    "messages": messages,
                    "temperature": AdvancedConfig.TEMPERATURE,
                    "max_tokens": 2000
                }
                
                response = await client.post(
                    AdvancedConfig.API_URL,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                elif response.status_code == 429 and retry_count < AdvancedConfig.MAX_RETRIES:
                    await asyncio.sleep((retry_count + 1) * 2)
                    return await AdvancedDeepSeekAPI.chat_completion(messages, retry_count + 1)
                else:
                    logger.error(f"API错误: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"API异常: {e}")
            if retry_count < AdvancedConfig.MAX_RETRIES:
                return await AdvancedDeepSeekAPI.chat_completion(messages, retry_count + 1)
            return None
    
    @staticmethod
    async def create_summary(messages: List[Conversation]) -> str:
        """创建对话摘要"""
        if not messages:
            return ""
        
        # 构建摘要请求
        conversation_text = "\n".join([
            f"{'用户' if m.role == 'user' else 'AI'}: {m.content}"
            for m in messages
        ])
        
        summary_messages = [
            {
                "role": "system",
                "content": "请将以下对话总结成简洁的摘要，提取关键信息和重要内容。"
            },
            {
                "role": "user",
                "content": f"请总结这段对话:\n\n{conversation_text}"
            }
        ]
        
        summary = await AdvancedDeepSeekAPI.chat_completion(summary_messages)
        return summary or "对话摘要生成失败"

# ==================== 命令处理器 ====================
# AI对话命令
chat_adv = on_command("聊", aliases={"chat", "问", "ai"}, priority=5, block=True)

@chat_adv.handle()
async def handle_advanced_chat(event: MessageEvent, args: Message = CommandArg()):
    """高级AI对话处理"""
    user_id = str(event.user_id)
    user_message = args.extract_plain_text().strip()
    
    if not user_message:
        await chat_adv.finish(
            "💬 使用方法：\n"
            "/聊 <消息> - 与AI聊天\n"
            "/清空记忆 - 清除所有记忆\n"
            "/查看记忆 - 查看记忆统计"
        )
    
    try:
        # 🎯 增强主动聊天引擎集成：记录用户活动
        if PROACTIVE_ENGINE_AVAILABLE:
            await enhanced_proactive_engine.update_user_activity(user_id, user_message)
        
        # 思考提示
        await chat_adv.send("💭 思考中...")
        
        # 计算重要性和情感
        importance = IntelligentMemoryManager.calculate_importance(user_message, 'user')
        emotion = IntelligentMemoryManager.detect_emotion(user_message)
        
        # 保存用户消息
        await db_manager.save_message(
            user_id, 'user', user_message, importance, emotion
        )
        
        # 构建智能上下文
        messages, system_prompt = await IntelligentMemoryManager.build_context(user_id)
        
        # 添加当前消息
        messages.append({"role": "user", "content": user_message})
        
        logger.debug(f"上下文消息数: {len(messages)}")
        
        # 调用API
        ai_reply = await AdvancedDeepSeekAPI.chat_completion(messages)
        
        if ai_reply:
            # 计算AI回复的重要性
            ai_importance = IntelligentMemoryManager.calculate_importance(ai_reply, 'assistant')
            
            # 保存AI回复
            await db_manager.save_message(
                user_id, 'assistant', ai_reply, ai_importance, 'neutral'
            )
            
            # 💬 分段发送回复（提升用户体验）
            await MessageSplitter.send_split_message(chat_adv, ai_reply)
            
        # 🎯 增强主动聊天引擎集成：记录用户响应（用于情感系统更新）
        if PROACTIVE_ENGINE_AVAILABLE:
            # 判断对话是否会继续（简单启发式：如果消息较长且包含问号，可能会继续）
            continued = len(user_message) > 10 or '?' in user_message or '吗' in user_message or '么' in user_message
            await enhanced_proactive_engine.record_user_response(user_id, user_message, continued)
            
            # 检查是否需要创建摘要
            recent_count = len(await db_manager.get_recent_messages(user_id, limit=100))
            if recent_count > AdvancedConfig.SUMMARY_THRESHOLD:
                await _create_summary_background(user_id)
                
        else:
            await chat_adv.send("😔 抱歉，暂时无法回复，请稍后再试")
            
    except Exception as e:
        logger.exception(f"对话处理错误: {e}")
        await chat_adv.send(f"❌ 发生错误: {type(e).__name__}")

async def _create_summary_background(user_id: str):
    """后台创建摘要"""
    try:
        # 获取需要摘要的消息
        messages = await db_manager.get_recent_messages(user_id, limit=20)
        unsummarized = [m for m in messages if not m.is_summarized]
        
        if len(unsummarized) >= 10:
            # 创建摘要
            summary_text = await AdvancedDeepSeekAPI.create_summary(unsummarized[:10])
            await db_manager.create_summary(user_id, unsummarized[:10], summary_text)
            logger.info(f"自动创建摘要: 用户 {user_id}")
    except Exception as e:
        logger.error(f"创建摘要失败: {e}")

# 清空记忆命令
clear_memory = on_command("清空记忆", aliases={"清空", "忘记我"}, priority=5)

@clear_memory.handle()
async def handle_clear_memory(event: MessageEvent):
    """清空所有记忆"""
    user_id = str(event.user_id)
    
    try:
        async with db_manager.async_session() as session:
            # 删除对话记录
            await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            # 删除摘要
            await session.execute(
                select(ConversationSummary).where(ConversationSummary.user_id == user_id)
            )
            await session.commit()
        
        await clear_memory.send("✨ 所有记忆已清空，我们重新开始吧！")
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        await clear_memory.send("❌ 清空失败")

# 查看记忆命令
view_memory = on_command("查看记忆", aliases={"记忆统计", "stats"}, priority=5)

@view_memory.handle()
async def handle_view_memory(event: MessageEvent):
    """查看记忆统计"""
    user_id = str(event.user_id)
    
    try:
        user = await db_manager.get_or_create_user(user_id)
        recent = await db_manager.get_recent_messages(user_id, limit=100)
        summaries = await db_manager.get_summaries(user_id, limit=10)
        important = await db_manager.get_important_messages(user_id, limit=100)
        
        stats = (
            f"🧠 记忆统计\n"
            f"━━━━━━━━━━━━\n"
            f"📝 总消息数: {user.total_messages}\n"
            f"💬 活跃对话: {len(recent)} 条\n"
            f"⭐ 重要记忆: {len(important)} 条\n"
            f"📚 历史摘要: {len(summaries)} 个\n"
            f"🕐 最后活跃: {user.last_active.strftime('%Y-%m-%d %H:%M')}"
        )
        
        await view_memory.send(stats)
    except Exception as e:
        logger.error(f"查看统计失败: {e}")
        await view_memory.send("❌ 获取统计失败")

# ==================== 初始化 ====================
from nonebot import get_driver

driver = get_driver()

@driver.on_startup
async def init_database():
    """启动时初始化数据库"""
    await db_manager.initialize()
    logger.success("🚀 高级AI聊天系统已启动！")

