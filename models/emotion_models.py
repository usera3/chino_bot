"""
情感系统数据模型
用于定义动态情感档案和情感变化记录的数据结构
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime
from models.chat_models import Base  # 使用统一的Base


class DynamicEmotionProfile(Base):
    """动态情感档案表"""
    __tablename__ = 'dynamic_emotion_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, index=True)
    
    # 基础情感参数
    happiness = Column(Float, default=70.0)  # 快乐值 (0-100)
    loneliness = Column(Float, default=30.0)  # 寂寞值 (0-100)
    energy = Column(Float, default=80.0)  # 体力值 (0-100)
    confidence = Column(Float, default=60.0)  # 自信值 (0-100)
    charm = Column(Float, default=50.0)  # 魅力值 (0-100)
    intelligence = Column(Float, default=70.0)  # 智力值 (0-100)
    creativity = Column(Float, default=60.0)  # 创造力 (0-100)
    empathy = Column(Float, default=75.0)  # 同理心 (0-100)
    
    # 状态参数
    mood = Column(String(20), default='neutral')  # 当前心情
    stress_level = Column(Float, default=20.0)  # 压力值 (0-100)
    social_need = Column(Float, default=50.0)  # 社交需求 (0-100)
    
    # 关系参数
    intimacy_level = Column(Float, default=0.5)  # 亲密度 (0-1)
    
    # 时间戳
    last_update = Column(DateTime, default=datetime.now)
    last_chat_time = Column(DateTime, nullable=True)
    last_proactive_time = Column(DateTime, nullable=True)
    last_night_drain = Column(DateTime, nullable=True)  # 上次夜晚体力扣除时间
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class EmotionChangeLog(Base):
    """情感变化记录表"""
    __tablename__ = 'emotion_change_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    change_type = Column(String(50))  # chat_start, chat_response, time_update, etc.
    emotion_changes = Column(Text)  # JSON格式的变化数据（保持与旧版本兼容）
    description = Column(Text)  # 变化描述
    created_at = Column(DateTime, default=datetime.now, index=True)  # 保持与旧版本兼容

