"""
表情包数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class LearnedEmoticon(Base):
    """学习的表情包表"""
    __tablename__ = 'learned_emoticons'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)  # 从哪个用户学到的
    group_id = Column(String(50), nullable=True, index=True)  # 来自哪个群
    
    # 表情包信息
    file_path = Column(String(500))  # 本地存储路径
    file_hash = Column(String(64), unique=True, index=True)  # 文件hash（去重）
    original_url = Column(Text, nullable=True)  # 原始URL
    
    # AI分析结果
    tags = Column(Text)  # JSON格式标签列表
    emotion = Column(String(50), index=True)  # 主要情感
    scene = Column(String(100), index=True)  # 使用场景
    description = Column(Text)  # AI生成的描述
    keywords = Column(Text)  # 关键词（JSON列表）
    
    # 使用统计
    use_count = Column(Integer, default=0)  # 使用次数
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间
    success_rate = Column(Float, default=0.0)  # 成功率（用户反馈）
    
    # 质量评分
    confidence_score = Column(Float, default=0.5)  # AI置信度
    quality_score = Column(Float, default=0.5)  # 综合质量评分
    
    # 元数据
    context = Column(Text, nullable=True)  # 学习时的上下文（JSON）
    learned_at = Column(DateTime, default=datetime.now, index=True)
    is_active = Column(Boolean, default=True)  # 是否可用
    
    # 来源标记
    source_type = Column(String(20), default='learned')  # learned/imported/system


class EmoticonUsageLog(Base):
    """表情包使用记录表"""
    __tablename__ = 'emoticon_usage_logs'
    
    id = Column(Integer, primary_key=True)
    emoticon_id = Column(Integer, index=True)  # 关联learned_emoticons.id
    user_id = Column(String(50), index=True)  # 使用对象
    group_id = Column(String(50), nullable=True, index=True)  # 使用群组
    
    # 使用上下文
    trigger_keywords = Column(Text)  # 触发关键词（JSON）
    context_emotion = Column(String(50))  # 当时的情感状态
    match_score = Column(Float)  # 匹配分数
    
    # 反馈
    user_response = Column(Text, nullable=True)  # 用户响应
    is_successful = Column(Boolean, default=True)  # 是否成功
    
    used_at = Column(DateTime, default=datetime.now, index=True)

























