"""
主动聊天数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from datetime import datetime
from models.chat_models import Base  # 使用统一的Base


class UserBehaviorProfile(Base):
    """用户行为画像表"""
    __tablename__ = 'user_behavior_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, index=True)
    
    # 基础统计
    total_messages = Column(Integer, default=0)  # 总消息数
    total_proactive_chats = Column(Integer, default=0)  # 总主动聊天次数
    successful_proactive_chats = Column(Integer, default=0)  # 成功的主动聊天（用户有回应）
    
    # 时间偏好
    active_hours_json = Column(Text)  # JSON格式的活跃时间段 [9-12, 14-18, ...]
    avg_response_time_seconds = Column(Float, default=300.0)  # 平均响应时间（秒）
    
    # 关系程度
    relationship_score = Column(Float, default=0.0)  # -1到1，关系亲密度
    intimacy_level = Column(Float, default=0.0)  # 0-1，亲密度
    last_interaction_quality = Column(Float, default=0.5)  # 0-1，最近一次互动质量
    
    # 主动性评分
    proactivity_score = Column(Float, default=0.3)  # 0-1，当前对该用户的主动性评分
    
    # 兴趣标签（JSON格式）
    interest_tags_json = Column(Text)  # {"tag": weight, ...}
    
    # 最近互动时间
    last_user_message_time = Column(DateTime, nullable=True)  # 用户最后一次发消息时间
    last_bot_proactive_time = Column(DateTime, nullable=True)  # 机器人最后一次主动聊天时间
    last_bot_message_time = Column(DateTime, nullable=True)  # 机器人最后一次回复时间
    
    # 今日统计
    today_proactive_count = Column(Integer, default=0)  # 今日主动聊天次数
    last_reset_date = Column(DateTime, default=datetime.now)  # 上次重置日期
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ProactiveDecision(Base):
    """主动聊天决策记录"""
    __tablename__ = 'proactive_decisions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    
    # 决策信息
    decision_score = Column(Float)  # 决策分数
    decision_reason = Column(Text)  # 决策原因（JSON）
    should_proactive = Column(Boolean)  # 是否应该主动
    
    # 执行结果
    executed = Column(Boolean, default=False)  # 是否已执行
    execution_time = Column(DateTime, nullable=True)  # 执行时间
    
    # 用户响应
    user_responded = Column(Boolean, default=False)  # 用户是否回应
    response_time_seconds = Column(Float, nullable=True)  # 响应时间
    response_quality = Column(Float, nullable=True)  # 响应质量（0-1）
    
    created_at = Column(DateTime, default=datetime.now, index=True)


class ProactiveChatLog(Base):
    """主动聊天日志"""
    __tablename__ = 'proactive_chat_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    
    # 聊天内容
    opening_message = Column(Text)  # 开场白
    context_used = Column(Text)  # 使用的上下文（JSON）
    
    # 生成参数
    generation_strategy = Column(String(50))  # 生成策略
    temperature = Column(Float, default=0.9)  # 生成温度
    
    # 结果
    success = Column(Boolean, default=False)  # 是否成功
    user_response_message = Column(Text, nullable=True)  # 用户回复内容
    conversation_continued = Column(Boolean, default=False)  # 对话是否继续
    
    # 反馈
    reward_score = Column(Float, nullable=True)  # 奖励分数（强化学习）
    quality_score = Column(Float, nullable=True)  # 质量评分
    
    created_at = Column(DateTime, default=datetime.now, index=True)






