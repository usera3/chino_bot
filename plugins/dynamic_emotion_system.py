"""
动态情感系统 - Dynamic Emotion System
实现更真实的情感参数动态变化机制
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
class DynamicEmotionConfig:
    """动态情感系统配置"""
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 情感参数范围
    MIN_VALUE = 0.0
    MAX_VALUE = 100.0
    
    # 时间相关配置
    LONELINESS_INCREASE_RATE = 5.0  # 寂寞值每小时增加率（提高，让机器人更容易寂寞）
    ENERGY_RECOVERY_RATE = 6.0  # 体力每小时恢复率
    ENERGY_NIGHT_DRAIN = 30.0  # 夜晚体力扣除量
    NIGHT_START_HOUR = 23  # 夜晚开始时间
    NIGHT_END_HOUR = 6  # 夜晚结束时间
    
    # 聊天影响配置
    CHAT_LONELINESS_REDUCTION = 15.0  # 聊天减少的寂寞值
    CHAT_ENERGY_COST = 8.0  # 聊天消耗的体力
    CHAT_HAPPINESS_GAIN = 10.0  # 聊天获得的快乐值
    CHAT_CONFIDENCE_GAIN = 5.0  # 聊天获得的自信值
    
    # 心情影响社交需求的配置
    MOOD_EXTREME_THRESHOLD = 15.0  # 心情极端阈值（距离50的差值，降低让机器人更容易主动）
    MOOD_SOCIAL_IMPACT_FACTOR = 2.5  # 极端心情对社交需求的影响因子（提高）
    
    # 情感参数对社交需求的影响权重
    EMOTION_SOCIAL_WEIGHTS = {
        'happiness': 0.2,      # 快乐值影响
        'loneliness': 0.3,     # 寂寞值影响（主要）
        'confidence': 0.15,    # 自信值影响
        'stress_level': -0.1,  # 压力值影响（负相关）
        'mood_extreme': 0.25   # 心情极端影响
    }
    
    # 用户消息情感分析配置
    POSITIVE_KEYWORDS = ['开心', '高兴', '快乐', '兴奋', '棒', '好', '喜欢', '爱', '成功', '胜利']
    NEGATIVE_KEYWORDS = ['难过', '伤心', '痛苦', '糟糕', '坏', '讨厌', '失败', '失望', '生气', '愤怒']
    CONFIDENCE_KEYWORDS = ['自信', '厉害', '强', '牛', '优秀', '完美', '成功', '胜利']
    STRESS_KEYWORDS = ['压力', '累', '忙', '紧张', '焦虑', '担心', '害怕']

# ==================== 数据库模型 ====================
Base = declarative_base()

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
    change_type = Column(String(50))  # time_decay, chat_impact, night_drain, etc.
    emotion_changes = Column(Text)  # JSON格式的情感变化
    description = Column(Text)  # 变化描述
    created_at = Column(DateTime, default=datetime.now)

# ==================== 动态情感系统核心 ====================
class DynamicEmotionSystem:
    """动态情感系统核心类"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        
    async def initialize(self):
        """初始化动态情感系统"""
        self.engine = create_async_engine(
            DynamicEmotionConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("💝 动态情感系统初始化完成")
    
    async def get_or_create_profile(self, user_id: str) -> DynamicEmotionProfile:
        """获取或创建用户动态情感档案"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DynamicEmotionProfile).where(DynamicEmotionProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                profile = DynamicEmotionProfile(
                    user_id=user_id,
                    happiness=random.uniform(60, 80),
                    loneliness=random.uniform(60, 80),  # 提高初始寂寞值，让机器人更容易主动
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
                logger.info(f"💝 为用户 {user_id} 创建动态情感档案")
            
            return profile
    
    async def update_time_based_emotions(self, user_id: str):
        """更新基于时间的情感变化"""
        profile = await self.get_or_create_profile(user_id)
        now = datetime.now()
        hours_passed = (now - profile.last_update).total_seconds() / 3600
        
        if hours_passed < 0.1:  # 少于6分钟不更新
            return
        
        changes = {}
        
        # 1. 寂寞值随时间增加
        loneliness_increase = DynamicEmotionConfig.LONELINESS_INCREASE_RATE * hours_passed
        changes['loneliness'] = min(100, profile.loneliness + loneliness_increase)
        
        # 2. 体力值随时间恢复（除非在夜晚）
        if self._is_night_time(now):
            # 夜晚体力扣除
            if not profile.last_night_drain or (now - profile.last_night_drain).total_seconds() > 3600:
                changes['energy'] = max(0, profile.energy - DynamicEmotionConfig.ENERGY_NIGHT_DRAIN)
                changes['last_night_drain'] = now
                logger.info(f"🌙 用户 {user_id} 夜晚体力扣除: {DynamicEmotionConfig.ENERGY_NIGHT_DRAIN}")
        else:
            # 白天体力恢复
            energy_recovery = DynamicEmotionConfig.ENERGY_RECOVERY_RATE * hours_passed
            changes['energy'] = min(100, profile.energy + energy_recovery)
        
        # 3. 其他情感参数缓慢衰减
        decay_rate = 0.05 * hours_passed  # 每小时5%的衰减
        for emotion in ['happiness', 'confidence', 'charm', 'intelligence', 'creativity', 'empathy']:
            current_value = getattr(profile, emotion)
            changes[emotion] = max(0, current_value - decay_rate)
        
        # 4. 压力值缓慢增加
        stress_increase = 0.1 * hours_passed
        changes['stress_level'] = min(100, profile.stress_level + stress_increase)
        
        # 应用变化
        await self._apply_emotion_changes(user_id, changes, "time_decay", f"时间流逝 {hours_passed:.1f} 小时")
        
        # 更新社交需求
        await self._update_social_need(user_id)
    
    def _is_night_time(self, now: datetime) -> bool:
        """判断是否是夜晚时间"""
        hour = now.hour
        return hour >= DynamicEmotionConfig.NIGHT_START_HOUR or hour < DynamicEmotionConfig.NIGHT_END_HOUR
    
    async def _update_social_need(self, user_id: str):
        """更新社交需求（基于各种情感参数）"""
        profile = await self.get_or_create_profile(user_id)
        
        # 计算心情极端程度
        mood_score = self._calculate_mood_score(profile)
        mood_extreme = abs(mood_score - 50)  # 距离中性的距离
        
        # 计算社交需求
        social_need = 0.0
        weights = DynamicEmotionConfig.EMOTION_SOCIAL_WEIGHTS
        
        social_need += profile.loneliness * weights['loneliness']
        social_need += profile.happiness * weights['happiness']
        social_need += profile.confidence * weights['confidence']
        social_need += profile.stress_level * weights['stress_level']
        social_need += mood_extreme * weights['mood_extreme']
        
        # 归一化到0-100
        social_need = max(0, min(100, social_need))
        
        # 更新社交需求
        changes = {'social_need': social_need}
        await self._apply_emotion_changes(user_id, changes, "social_need_update", f"社交需求更新: {social_need:.1f}")
    
    def _calculate_mood_score(self, profile: DynamicEmotionProfile) -> float:
        """计算心情评分"""
        happiness_weight = 0.3
        loneliness_weight = -0.2
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
        
        return max(0, min(100, mood_score))
    
    async def on_chat_start(self, user_id: str, user_message: str = ""):
        """聊天开始时的情感更新"""
        # 分析用户消息的情感影响
        message_impact = self._analyze_message_emotion(user_message)
        
        # 基础聊天影响
        changes = {
            'happiness': DynamicEmotionConfig.CHAT_HAPPINESS_GAIN,
            'energy': -DynamicEmotionConfig.CHAT_ENERGY_COST,
            'confidence': DynamicEmotionConfig.CHAT_CONFIDENCE_GAIN,
            'loneliness': -DynamicEmotionConfig.CHAT_LONELINESS_REDUCTION
        }
        
        # 添加消息情感影响
        changes.update(message_impact)
        
        await self._apply_emotion_changes(
            user_id, 
            changes, 
            "chat_start", 
            f"开始聊天: {user_message[:50] if user_message else '系统触发'}"
        )
        
        # 更新最后聊天时间
        async with self.async_session() as session:
            result = await session.execute(
                select(DynamicEmotionProfile).where(DynamicEmotionProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if profile:
                profile.last_chat_time = datetime.now()
                await session.commit()
    
    def _analyze_message_emotion(self, message: str) -> Dict[str, float]:
        """分析用户消息的情感影响"""
        if not message:
            return {}
        
        message_lower = message.lower()
        changes = {}
        
        # 分析积极词汇
        positive_count = sum(1 for word in DynamicEmotionConfig.POSITIVE_KEYWORDS if word in message_lower)
        if positive_count > 0:
            changes['happiness'] = positive_count * 3.0
            changes['confidence'] = positive_count * 2.0
        
        # 分析消极词汇
        negative_count = sum(1 for word in DynamicEmotionConfig.NEGATIVE_KEYWORDS if word in message_lower)
        if negative_count > 0:
            changes['happiness'] = -negative_count * 2.0
            changes['stress_level'] = negative_count * 3.0
        
        # 分析自信词汇
        confidence_count = sum(1 for word in DynamicEmotionConfig.CONFIDENCE_KEYWORDS if word in message_lower)
        if confidence_count > 0:
            changes['confidence'] = confidence_count * 4.0
        
        # 分析压力词汇
        stress_count = sum(1 for word in DynamicEmotionConfig.STRESS_KEYWORDS if word in message_lower)
        if stress_count > 0:
            changes['stress_level'] = stress_count * 4.0
            changes['happiness'] = -stress_count * 1.0
        
        return changes
    
    async def on_chat_response(self, user_id: str, response_quality: str = "good"):
        """用户回复时的情感更新"""
        if response_quality == "good":
            changes = {
                'happiness': 8.0,
                'confidence': 5.0,
                'loneliness': -8.0,
                'charm': 2.0,
                'intimacy_level': 0.05  # 增加亲密度
            }
            description = "用户积极回复，关系更亲密"
        elif response_quality == "neutral":
            changes = {
                'happiness': 2.0,
                'confidence': 1.0,
                'loneliness': -3.0,
                'intimacy_level': 0.02
            }
            description = "用户中性回复"
        else:  # bad
            changes = {
                'happiness': -3.0,
                'confidence': -2.0,
                'stress_level': 5.0,
                'intimacy_level': -0.03  # 减少亲密度
            }
            description = "用户消极回复，关系疏远"
        
        await self._apply_emotion_changes(user_id, changes, "chat_response", description)
    
    async def on_no_response(self, user_id: str):
        """用户无回复时的情感更新"""
        changes = {
            'loneliness': 8.0,
            'confidence': -2.0,
            'happiness': -3.0,
            'stress_level': 3.0,
            'intimacy_level': -0.01  # 轻微减少亲密度
        }
        
        await self._apply_emotion_changes(user_id, changes, "no_response", "用户没有回复，感到寂寞")
    
    async def should_initiate_chat(self, user_id: str) -> Tuple[bool, str, Dict]:
        """判断是否应该主动聊天"""
        profile = await self.get_or_create_profile(user_id)
        
        # 检查体力是否充足
        if profile.energy < 20:
            return False, f"体力不足({profile.energy:.1f})，正在休息", {}
        
        # 检查社交需求（降低阈值）
        if profile.social_need < 20:
            return False, f"社交需求不足({profile.social_need:.1f})", {}
        
        # 检查寂寞值（降低阈值）
        if profile.loneliness < 15:
            return False, f"不寂寞({profile.loneliness:.1f})", {}
        
        # 检查心情极端程度
        mood_score = self._calculate_mood_score(profile)
        mood_extreme = abs(mood_score - 50)
        if mood_extreme > 20:  # 心情很极端（降低阈值）
            return True, f"心情极端({mood_score:.1f})，需要倾诉", self._get_emotion_state(profile)
        
        # 综合判断（降低阈值）
        should_chat = (
            profile.loneliness >= 20 or
            profile.social_need >= 40 or
            mood_extreme >= 15
        )
        
        if should_chat:
            reason = f"情感驱动(寂寞:{profile.loneliness:.1f}, 社交:{profile.social_need:.1f}, 心情:{mood_score:.1f})"
            return True, reason, self._get_emotion_state(profile)
        
        return False, "情感状态不适合主动聊天", {}
    
    def _get_emotion_state(self, profile: DynamicEmotionProfile) -> Dict:
        """获取情感状态"""
        return {
            'happiness': profile.happiness,
            'loneliness': profile.loneliness,
            'energy': profile.energy,
            'confidence': profile.confidence,
            'mood': profile.mood,
            'charm': profile.charm,
            'intelligence': profile.intelligence,
            'creativity': profile.creativity,
            'empathy': profile.empathy,
            'stress_level': profile.stress_level,
            'social_need': profile.social_need,
            'intimacy_level': profile.intimacy_level
        }
    
    async def get_emotion(self, user_id: str) -> Dict:
        """获取用户的情感状态（公开方法）"""
        profile = await self.get_or_create_profile(user_id)
        return self._get_emotion_state(profile)
    
    async def get_emotion_influenced_style(self, user_id: str) -> Dict[str, any]:
        """根据情感状态获取影响回复风格的信息"""
        profile = await self.get_or_create_profile(user_id)
        mood_score = self._calculate_mood_score(profile)
        
        # 根据心情评分确定心情状态
        if mood_score >= 70:
            mood = "excited"
        elif mood_score >= 50:
            mood = "happy"
        elif mood_score >= 30:
            mood = "neutral"
        elif mood_score >= 10:
            mood = "sad"
        else:
            mood = "depressed"
        
        # 更新心情状态
        if profile.mood != mood:
            await self._apply_emotion_changes(user_id, {'mood': mood}, "mood_update", f"心情变化: {mood}")
        
        # 根据情感参数调整回复风格
        style = {
            'mood': mood,
            'energy_level': 'high' if profile.energy > 70 else 'medium' if profile.energy > 40 else 'low',
            'confidence_level': 'high' if profile.confidence > 70 else 'medium' if profile.confidence > 40 else 'low',
            'charm_level': 'high' if profile.charm > 70 else 'medium' if profile.charm > 40 else 'low',
            'creativity_level': 'high' if profile.creativity > 70 else 'medium' if profile.creativity > 40 else 'low',
            'empathy_level': 'high' if profile.empathy > 70 else 'medium' if profile.empathy > 40 else 'low',
            'use_emojis': profile.happiness > 60,
            'be_playful': profile.creativity > 60 and profile.energy > 50,
            'be_caring': profile.empathy > 70,
            'be_confident': profile.confidence > 60,
            'be_gentle': profile.stress_level > 50 or mood in ['sad', 'depressed'],
            'be_energetic': profile.energy > 70 and mood in ['excited', 'happy'],
            'be_resting': profile.energy < 20
        }
        
        return style
    
    async def _apply_emotion_changes(self, user_id: str, changes: Dict[str, any], change_type: str, description: str):
        """应用情感变化"""
        async with self.async_session() as session:
            # 获取当前档案
            result = await session.execute(
                select(DynamicEmotionProfile).where(DynamicEmotionProfile.user_id == user_id)
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
                'empathy': profile.empathy,
                'stress_level': profile.stress_level,
                'social_need': profile.social_need,
                'intimacy_level': profile.intimacy_level
            }
            
            # 应用变化
            for emotion, change in changes.items():
                if hasattr(profile, emotion):
                    if emotion in ['intimacy_level']:
                        # 亲密度特殊处理
                        current_value = getattr(profile, emotion)
                        new_value = max(0, min(1, current_value + change))
                    else:
                        # 其他情感参数
                        current_value = getattr(profile, emotion)
                        new_value = max(0, min(100, current_value + change))
                    setattr(profile, emotion, new_value)
            
            # 更新时间戳
            profile.last_update = datetime.now()
            profile.updated_at = datetime.now()
            
            await session.commit()
            
            # 记录情感变化日志
            emotion_changes = {k: getattr(profile, k) - old_values[k] 
                             for k in changes.keys() 
                             if hasattr(profile, k)}
            
            log = EmotionChangeLog(
                user_id=user_id,
                change_type=change_type,
                emotion_changes=json.dumps(emotion_changes),
                description=description
            )
            session.add(log)
            await session.commit()
            
            logger.info(f"💝 用户 {user_id} 情感变化: {emotion_changes}")
    
    async def get_intimacy_ranking(self) -> List[Tuple[str, float]]:
        """获取亲密度排名（用于决定主动聊天对象）"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DynamicEmotionProfile.user_id, DynamicEmotionProfile.intimacy_level)
                .order_by(desc(DynamicEmotionProfile.intimacy_level))
            )
            rankings = result.all()
            return [(user_id, intimacy) for user_id, intimacy in rankings]

# ==================== 全局实例 ====================
dynamic_emotion_system = DynamicEmotionSystem()

# ==================== 导出 ====================
__all__ = ['dynamic_emotion_system', 'DynamicEmotionSystem', 'DynamicEmotionConfig']
