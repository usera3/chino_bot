"""
情感系统 - Emotion System
为机器人添加拟人化的情感、体力、自信等参数
影响机器人的主动聊天行为和回复风格
"""

from nonebot.log import logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import random
import math
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, desc, and_

# ==================== 配置 ====================
class EmotionConfig:
    """情感系统配置"""
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 情感参数范围
    MIN_VALUE = 0.0
    MAX_VALUE = 100.0
    
    # 情感衰减配置
    DECAY_RATE = 0.1  # 每小时衰减率
    DECAY_INTERVAL_HOURS = 1  # 衰减间隔
    
    # 情感影响配置
    LONELINESS_THRESHOLD = 30.0  # 寂寞阈值，低于此值会主动聊天
    ENERGY_THRESHOLD = 20.0  # 体力阈值，低于此值减少主动聊天
    CONFIDENCE_THRESHOLD = 40.0  # 自信阈值，影响回复风格
    
    # 情感变化配置
    CHAT_HAPPINESS_GAIN = 5.0  # 聊天获得的快乐值
    CHAT_ENERGY_COST = 2.0  # 聊天消耗的体力
    CHAT_CONFIDENCE_GAIN = 3.0  # 聊天获得的自信值
    NO_RESPONSE_LONELINESS_GAIN = 8.0  # 无回应增加的寂寞值
    NO_RESPONSE_CONFIDENCE_LOSS = 2.0  # 无回应损失的自信值

# ==================== 数据库模型 ====================
Base = declarative_base()

class EmotionProfile(Base):
    """情感档案表"""
    __tablename__ = 'emotion_profiles'
    
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
    
    # 时间戳
    last_update = Column(DateTime, default=datetime.now)
    last_chat_time = Column(DateTime, nullable=True)
    last_proactive_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class EmotionEvent(Base):
    """情感事件记录表"""
    __tablename__ = 'emotion_events'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    event_type = Column(String(50))  # chat, proactive, no_response, etc.
    emotion_changes = Column(Text)  # JSON格式的情感变化
    description = Column(Text)  # 事件描述
    created_at = Column(DateTime, default=datetime.now)

# ==================== 情感系统核心 ====================
class EmotionSystem:
    """情感系统核心类"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        
    async def initialize(self):
        """初始化情感系统"""
        self.engine = create_async_engine(
            EmotionConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("💝 情感系统初始化完成")
    
    async def get_or_create_profile(self, user_id: str) -> EmotionProfile:
        """获取或创建用户情感档案"""
        async with self.async_session() as session:
            result = await session.execute(
                select(EmotionProfile).where(EmotionProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                profile = EmotionProfile(
                    user_id=user_id,
                    happiness=random.uniform(60, 80),
                    loneliness=random.uniform(20, 40),
                    energy=random.uniform(70, 90),
                    confidence=random.uniform(50, 70),
                    charm=random.uniform(40, 60),
                    intelligence=random.uniform(60, 80),
                    creativity=random.uniform(50, 70),
                    empathy=random.uniform(70, 85)
                )
                session.add(profile)
                await session.commit()
                await session.refresh(profile)
                logger.info(f"💝 为用户 {user_id} 创建情感档案")
            
            return profile
    
    async def update_emotion(
        self, 
        user_id: str, 
        changes: Dict[str, float], 
        event_type: str = "manual",
        description: str = ""
    ):
        """更新用户情感参数"""
        async with self.async_session() as session:
            # 获取当前档案
            result = await session.execute(
                select(EmotionProfile).where(EmotionProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                profile = await self.get_or_create_profile(user_id)
            
            # 记录变化前的情感值
            old_values = {
                'happiness': profile.happiness,
                'loneliness': profile.loneliness,
                'energy': profile.energy,
                'confidence': profile.confidence,
                'charm': profile.charm,
                'intelligence': profile.intelligence,
                'creativity': profile.creativity,
                'empathy': profile.empathy
            }
            
            # 应用变化
            for emotion, change in changes.items():
                if hasattr(profile, emotion):
                    current_value = getattr(profile, emotion)
                    new_value = max(EmotionConfig.MIN_VALUE, 
                                  min(EmotionConfig.MAX_VALUE, 
                                      current_value + change))
                    setattr(profile, emotion, new_value)
            
            # 更新心情状态
            profile.mood = self._calculate_mood(profile)
            profile.last_update = datetime.now()
            
            await session.commit()
            
            # 记录情感事件
            emotion_changes = {k: getattr(profile, k) - old_values[k] 
                             for k in changes.keys() 
                             if hasattr(profile, k)}
            
            event = EmotionEvent(
                user_id=user_id,
                event_type=event_type,
                emotion_changes=json.dumps(emotion_changes),
                description=description
            )
            session.add(event)
            await session.commit()
            
            logger.info(f"💝 用户 {user_id} 情感更新: {emotion_changes}")
    
    def _calculate_mood(self, profile: EmotionProfile) -> str:
        """根据情感参数计算当前心情"""
        # 综合评分
        happiness_weight = 0.3
        loneliness_weight = -0.2  # 寂寞值越高，心情越差
        energy_weight = 0.2
        confidence_weight = 0.2
        stress_weight = -0.1
        
        mood_score = (
            profile.happiness * happiness_weight +
            profile.loneliness * loneliness_weight +
            profile.energy * energy_weight +
            profile.confidence * confidence_weight +
            profile.stress_level * stress_weight
        )
        
        if mood_score >= 70:
            return "excited"  # 兴奋
        elif mood_score >= 50:
            return "happy"  # 开心
        elif mood_score >= 30:
            return "neutral"  # 中性
        elif mood_score >= 10:
            return "sad"  # 难过
        else:
            return "depressed"  # 沮丧
    
    async def should_initiate_chat(self, user_id: str) -> Tuple[bool, str, Dict]:
        """
        判断是否应该主动聊天
        返回：(是否聊天, 原因, 情感状态)
        """
        profile = await self.get_or_create_profile(user_id)
        
        # 检查各种条件
        reasons = []
        should_chat = False
        
        # 1. 寂寞值过高
        if profile.loneliness >= EmotionConfig.LONELINESS_THRESHOLD:
            reasons.append(f"寂寞值过高({profile.loneliness:.1f})")
            should_chat = True
        
        # 2. 体力充足
        if profile.energy < EmotionConfig.ENERGY_THRESHOLD:
            reasons.append(f"体力不足({profile.energy:.1f})")
            should_chat = False
        
        # 3. 社交需求
        if profile.social_need >= 70:
            reasons.append(f"社交需求强烈({profile.social_need:.1f})")
            should_chat = True
        
        # 4. 心情影响
        if profile.mood in ["sad", "depressed"]:
            reasons.append(f"心情不好({profile.mood})")
            should_chat = True
        
        # 5. 时间因素（距离上次聊天的时间）
        if profile.last_chat_time:
            hours_since_chat = (datetime.now() - profile.last_chat_time).total_seconds() / 3600
            if hours_since_chat > 6:  # 6小时没聊天
                reasons.append(f"长时间未聊天({hours_since_chat:.1f}小时)")
                should_chat = True
        
        # 6. 随机因素（基于情感参数）
        random_factor = random.random()
        emotion_based_prob = (
            profile.loneliness / 100 * 0.4 +
            profile.social_need / 100 * 0.3 +
            (100 - profile.stress_level) / 100 * 0.3
        )
        
        if random_factor < emotion_based_prob:
            reasons.append(f"情感驱动({emotion_based_prob:.2%})")
            should_chat = True
        
        # 综合判断
        if should_chat and profile.energy >= EmotionConfig.ENERGY_THRESHOLD:
            reason = " + ".join(reasons) if reasons else "情感驱动"
            emotion_state = {
                'happiness': profile.happiness,
                'loneliness': profile.loneliness,
                'energy': profile.energy,
                'confidence': profile.confidence,
                'mood': profile.mood,
                'charm': profile.charm,
                'intelligence': profile.intelligence,
                'creativity': profile.creativity,
                'empathy': profile.empathy
            }
            return True, reason, emotion_state
        else:
            return False, "情感状态不适合主动聊天", {}
    
    async def on_chat_start(self, user_id: str):
        """聊天开始时更新情感"""
        changes = {
            'happiness': EmotionConfig.CHAT_HAPPINESS_GAIN,
            'energy': -EmotionConfig.CHAT_ENERGY_COST,
            'confidence': EmotionConfig.CHAT_CONFIDENCE_GAIN,
            'loneliness': -5.0,  # 减少寂寞
            'social_need': -10.0  # 满足社交需求
        }
        
        await self.update_emotion(
            user_id, 
            changes, 
            "chat_start", 
            "开始聊天，心情变好"
        )
        
        # 更新最后聊天时间
        async with self.async_session() as session:
            result = await session.execute(
                select(EmotionProfile).where(EmotionProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if profile:
                profile.last_chat_time = datetime.now()
                await session.commit()
    
    async def on_chat_response(self, user_id: str, response_quality: str = "good"):
        """用户回复时更新情感"""
        if response_quality == "good":
            changes = {
                'happiness': 8.0,
                'confidence': 5.0,
                'loneliness': -8.0,
                'charm': 2.0
            }
            description = "用户积极回复，心情很好"
        elif response_quality == "neutral":
            changes = {
                'happiness': 2.0,
                'confidence': 1.0,
                'loneliness': -3.0
            }
            description = "用户中性回复"
        else:  # bad
            changes = {
                'happiness': -3.0,
                'confidence': -2.0,
                'stress_level': 5.0
            }
            description = "用户消极回复，有点沮丧"
        
        await self.update_emotion(
            user_id, 
            changes, 
            "chat_response", 
            description
        )
    
    async def on_no_response(self, user_id: str):
        """用户无回复时更新情感"""
        changes = {
            'loneliness': EmotionConfig.NO_RESPONSE_LONELINESS_GAIN,
            'confidence': -EmotionConfig.NO_RESPONSE_CONFIDENCE_LOSS,
            'happiness': -3.0,
            'stress_level': 3.0
        }
        
        await self.update_emotion(
            user_id, 
            changes, 
            "no_response", 
            "用户没有回复，感到寂寞"
        )
    
    async def get_emotion_influenced_style(self, user_id: str) -> Dict[str, any]:
        """根据情感状态获取影响回复风格的信息"""
        profile = await self.get_or_create_profile(user_id)
        
        # 根据情感参数调整回复风格
        style = {
            'mood': profile.mood,
            'energy_level': 'high' if profile.energy > 70 else 'medium' if profile.energy > 40 else 'low',
            'confidence_level': 'high' if profile.confidence > 70 else 'medium' if profile.confidence > 40 else 'low',
            'charm_level': 'high' if profile.charm > 70 else 'medium' if profile.charm > 40 else 'low',
            'creativity_level': 'high' if profile.creativity > 70 else 'medium' if profile.creativity > 40 else 'low',
            'empathy_level': 'high' if profile.empathy > 70 else 'medium' if profile.empathy > 40 else 'low',
            'use_emojis': profile.happiness > 60,  # 快乐时多用emoji
            'be_playful': profile.creativity > 60 and profile.energy > 50,
            'be_caring': profile.empathy > 70,
            'be_confident': profile.confidence > 60,
            'be_gentle': profile.stress_level > 50 or profile.mood in ['sad', 'depressed']
        }
        
        return style
    
    async def decay_emotions(self):
        """情感衰减（定期调用）"""
        async with self.async_session() as session:
            # 获取所有档案
            result = await session.execute(select(EmotionProfile))
            profiles = result.scalars().all()
            
            for profile in profiles:
                # 计算衰减
                hours_passed = (datetime.now() - profile.last_update).total_seconds() / 3600
                if hours_passed >= EmotionConfig.DECAY_INTERVAL_HOURS:
                    # 基础衰减
                    decay_amount = EmotionConfig.DECAY_RATE * hours_passed
                    
                    # 不同情感的衰减速度不同
                    changes = {
                        'happiness': -decay_amount * 0.5,  # 快乐衰减较慢
                        'energy': -decay_amount * 0.3,  # 体力衰减最慢
                        'confidence': -decay_amount * 0.2,  # 自信衰减很慢
                        'loneliness': decay_amount * 0.8,  # 寂寞增加较快
                        'social_need': decay_amount * 0.6,  # 社交需求增加
                        'stress_level': decay_amount * 0.1  # 压力缓慢增加
                    }
                    
                    # 应用衰减
                    for emotion, change in changes.items():
                        if hasattr(profile, emotion):
                            current_value = getattr(profile, emotion)
                            new_value = max(EmotionConfig.MIN_VALUE, 
                                          min(EmotionConfig.MAX_VALUE, 
                                              current_value + change))
                            setattr(profile, emotion, new_value)
                    
                    profile.mood = self._calculate_mood(profile)
                    profile.last_update = datetime.now()
            
            await session.commit()
            logger.debug("💝 情感衰减完成")

# ==================== 全局实例 ====================
emotion_system = EmotionSystem()

# ==================== 导出 ====================
__all__ = ['emotion_system', 'EmotionSystem', 'EmotionConfig']

