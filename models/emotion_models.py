"""
情感系统数据模型 - PAD三维情感模型 + 生理状态
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from pathlib import Path
from nonebot.log import logger

Base = declarative_base()

# 数据库路径
EMOTION_DB_PATH = Path(__file__).parent.parent / "data" / "emotion.db"
EMOTION_DB_PATH.parent.mkdir(exist_ok=True)


class EmotionState(Base):
    """情感状态表 - 记录用户的情感和行为状态（PAD三维模型）"""
    __tablename__ = 'emotion_states'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, unique=True, index=True)
    
    # === PAD三维情感模型 ===
    pleasure = Column(Float, default=0.3)      # 愉悦度 (-1.0 ~ 1.0)
    arousal = Column(Float, default=0.0)       # 唤醒度 (-1.0 ~ 1.0)
    dominance = Column(Float, default=0.0)     # 支配度 (-1.0 ~ 1.0)
    
    # === 生理状态 ===
    energy = Column(Float, default=80.0)       # 体力 (0 ~ 100)
    hunger = Column(Float, default=30.0)       # 饥饿感 (0 ~ 100)
    sleepiness = Column(Float, default=20.0)   # 困倦度 (0 ~ 100)
    
    # === 社交状态 ===
    loneliness = Column(Float, default=40.0)   # 孤独感 (0 ~ 100)
    intimacy_level = Column(Float, default=0.5) # 亲密度 (0.0 ~ 1.0)
    
    # === 认知状态 ===
    stress = Column(Float, default=20.0)       # 压力 (0 ~ 100)
    interest = Column(Float, default=50.0)     # 兴趣度 (0 ~ 100)
    
    # === 派生状态 ===
    mood_label = Column(String(20), default='平静')  # 当前心情标签
    current_activity = Column(String(50), nullable=True)  # 当前活动
    current_activity_start = Column(DateTime, nullable=True)  # 活动开始时间
    
    # === 时间戳 ===
    last_update = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_chat_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "pad": {
                "pleasure": round(self.pleasure, 2),
                "arousal": round(self.arousal, 2),
                "dominance": round(self.dominance, 2)
            },
            "physical": {
                "energy": round(self.energy, 1),
                "hunger": round(self.hunger, 1),
                "sleepiness": round(self.sleepiness, 1)
            },
            "social": {
                "loneliness": round(self.loneliness, 1),
                "intimacy_level": round(self.intimacy_level, 2)
            },
            "cognitive": {
                "stress": round(self.stress, 1),
                "interest": round(self.interest, 1)
            },
            "mood_label": self.mood_label,
            "current_activity": self.current_activity,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }


class DailyEvent(Base):
    """日常事件表 - 记录发生的随机事件"""
    __tablename__ = 'daily_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    event_date = Column(DateTime, default=datetime.now, index=True)
    
    event_type = Column(String(20), nullable=False)  # 'positive', 'neutral', 'negative'
    event_desc = Column(Text, nullable=False)  # 事件描述
    
    # 情感影响（JSON格式存储）
    emotion_impact = Column(JSON, nullable=True)  # {"pleasure": +0.2, "stress": -10, ...}
    
    # 是否已在对话中提及
    mentioned = Column(Integer, default=0)  # 0=未提及, 1=已提及
    
    created_at = Column(DateTime, default=datetime.now)


class ActivityLog(Base):
    """活动日志表 - 记录每天的活动"""
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    
    activity_name = Column(String(50), nullable=False)  # 活动名称
    activity_type = Column(String(20), nullable=False)  # 活动类型
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # 活动效果（JSON）
    effects = Column(JSON, nullable=True)  # {"energy": -10, "pleasure": +0.2, ...}
    
    created_at = Column(DateTime, default=datetime.now)


# ============ 数据库连接管理 ============

# 创建引擎
_emotion_engine = None
_EmotionSession = None


def get_emotion_engine():
    """获取数据库引擎（单例）"""
    global _emotion_engine
    if _emotion_engine is None:
        _emotion_engine = create_engine(
            f'sqlite:///{EMOTION_DB_PATH}',
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        logger.info(f"✅ 情感数据库引擎初始化完成: {EMOTION_DB_PATH}")
    return _emotion_engine


def get_emotion_session():
    """获取数据库会话"""
    global _EmotionSession
    if _EmotionSession is None:
        engine = get_emotion_engine()
        _EmotionSession = sessionmaker(bind=engine)
    return _EmotionSession()


def init_emotion_database():
    """初始化情感数据库（创建所有表）"""
    engine = get_emotion_engine()
    Base.metadata.create_all(engine)
    logger.success("✅ 情感数据库表创建完成")


# 自动初始化
try:
    init_emotion_database()
except Exception as e:
    logger.error(f"❌ 情感数据库初始化失败: {e}")


