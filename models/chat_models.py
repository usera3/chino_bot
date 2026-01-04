"""
聊天数据模型 - Models Layer
职责：定义数据库表结构
代码量：~100行
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

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




