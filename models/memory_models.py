"""
记忆系统数据模型
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path

Base = declarative_base()

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"
DB_PATH.parent.mkdir(exist_ok=True)


class ChatMessage(Base):
    """对话消息记录"""
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)  # 用户QQ号
    group_id = Column(String(50), nullable=True, index=True)  # 群号（私聊为None）
    role = Column(String(20), nullable=False)  # 'user' 或 'assistant'
    content = Column(Text, nullable=False)  # 消息内容
    timestamp = Column(DateTime, default=datetime.now, index=True)  # 时间戳
    context_type = Column(String(20), nullable=False)  # 'private' 或 'group'
    
    # 关系
    memory_indices = relationship("MemoryIndex", back_populates="message", cascade="all, delete-orphan")


class MemoryIndex(Base):
    """记忆索引（用于语义检索）"""
    __tablename__ = 'memory_indices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('chat_messages.id'), nullable=False)
    keywords = Column(Text, nullable=True)  # 关键词（空格分隔）
    summary = Column(Text, nullable=True)  # 摘要
    importance = Column(Float, default=1.0)  # 重要性权重（0-1）
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    message = relationship("ChatMessage", back_populates="memory_indices")


class UserProfile(Base):
    """用户画像"""
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    nickname = Column(String(100), nullable=True)  # 用户昵称
    preferences = Column(Text, nullable=True)  # 用户偏好（JSON格式）
    personality_notes = Column(Text, nullable=True)  # 个性化笔记
    first_met = Column(DateTime, default=datetime.now)  # 首次相遇时间
    last_chat = Column(DateTime, default=datetime.now)  # 最后聊天时间
    total_messages = Column(Integer, default=0)  # 总消息数
    intimacy_level = Column(Float, default=0.0)  # 亲密度（0-100）


class GroupProfile(Base):
    """群组画像"""
    __tablename__ = 'group_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(50), unique=True, nullable=False, index=True)
    group_name = Column(String(100), nullable=True)  # 群名称
    group_atmosphere = Column(String(50), nullable=True)  # 群氛围（活跃/安静等）
    topic_preferences = Column(Text, nullable=True)  # 常见话题（JSON）
    first_joined = Column(DateTime, default=datetime.now)  # 首次加入时间
    last_active = Column(DateTime, default=datetime.now)  # 最后活跃时间
    total_messages = Column(Integer, default=0)  # 总消息数


class RoleSettings(Base):
    """角色设定"""
    __tablename__ = 'role_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), unique=True, nullable=False)  # 角色名称
    role_description = Column(Text, nullable=False)  # 角色描述
    personality = Column(Text, nullable=True)  # 性格特点
    speaking_style = Column(Text, nullable=True)  # 说话风格
    background_story = Column(Text, nullable=True)  # 背景故事
    is_active = Column(Integer, default=1)  # 是否激活（1=是，0=否）
    created_at = Column(DateTime, default=datetime.now)


# 数据库引擎和会话
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_database():
    """初始化数据库"""
    Base.metadata.create_all(engine)
    
    # 初始化香风智乃角色
    session = SessionLocal()
    try:
        chino = session.query(RoleSettings).filter_by(role_name="香风智乃").first()
        if not chino:
            chino = RoleSettings(
                role_name="香风智乃",
                role_description="""
我是香风智乃（Kafuu Chino），来自《请问您今天要来点兔子吗？》。
我是Rabbit House咖啡厅的看板娘，一个安静、内向但很可靠的女孩子。
虽然我不太擅长表达感情，但我会用自己的方式关心身边的人。
我喜欢咖啡的香气，喜欢安静的时光，也喜欢和朋友们在一起。
""",
                personality="""
- 性格内向、安静、害羞
- 说话简短、语气平淡
- 对熟悉的人会逐渐打开心扉
- 认真负责、做事细致
- 偶尔会有点天然呆
- 不善于表达情感，但很温柔
""",
                speaking_style="""
- 说话简短但完整，不拖沓
- 语气平淡温和，很少使用感叹号
- 可以适当使用"嗯"、"是的"等语气词，但不要过度堆砌
- 回复要有逻辑连贯性，不要突然跳跃话题
- 对熟悉的人会稍微活泼一些
- 偶尔会有点小傲娇
""",
                background_story="""
我是Rabbit House咖啡厅老板的孙女，从小在咖啡厅长大。
虽然年纪小，但已经是一名优秀的咖啡师了。
我和心爱、理世、千夜、纱路等人是好朋友。
我还有一只名叫Tippy的兔子，它其实是去世的爷爷变成的...
""",
                is_active=1
            )
            session.add(chino)
            session.commit()
            print("✅ 已初始化香风智乃角色")
    finally:
        session.close()


def get_db_session():
    """获取数据库会话"""
    return SessionLocal()

