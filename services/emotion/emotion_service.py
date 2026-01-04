"""
动态情感服务 - Service Layer
职责：管理用户情感状态、情感变化、社交需求判断
整合原 dynamic_emotion_system.py 的所有功能
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from nonebot.log import logger
import json
import random
import math

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, desc

from models.emotion_models import DynamicEmotionProfile, EmotionChangeLog, Base
from services.emotion.emotion_config import EmotionConfig


class EmotionService:
    """动态情感服务"""
    
    def __init__(self):
        """初始化情感服务"""
        self.config = EmotionConfig
        self.engine = None
        self.Session = None
    
    async def initialize(self):
        """初始化数据库连接"""
        try:
            self.engine = create_async_engine(
                self.config.DATABASE_URL,
                echo=False
            )
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self.Session = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            
            logger.info("动态情感系统初始化完成")
        except Exception as e:
            logger.error(f"动态情感系统初始化失败: {e}")
            raise
    
    # ==================== 档案管理 ====================
    
    async def get_or_create_profile(self, user_id: str) -> DynamicEmotionProfile:
        """
        获取或创建用户情感档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户情感档案
        """
        async with self.Session() as session:
            # 尝试获取现有档案
            result = await session.execute(
                select(DynamicEmotionProfile).where(
                    DynamicEmotionProfile.user_id == user_id
                )
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                # 更新时间相关的情感参数
                await self._update_time_based_emotions_internal(session, profile)
                return profile
            
            # 创建新档案
            profile = DynamicEmotionProfile(user_id=user_id)
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
            
            logger.info(f"💝 为用户 {user_id} 创建动态情感档案")
            return profile
    
    async def update_time_based_emotions(self, user_id: str):
        """
        更新用户的基于时间的情感参数
        
        Args:
            user_id: 用户ID
        """
        async with self.Session() as session:
            # 获取用户档案
            result = await session.execute(
                select(DynamicEmotionProfile).where(
                    DynamicEmotionProfile.user_id == user_id
                )
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                # 更新时间相关的情感参数
                await self._update_time_based_emotions_internal(session, profile)
                await session.commit()
                logger.debug(f"💝 为用户 {user_id} 更新了时间相关情感参数")
            else:
                logger.warning(f"💝 用户 {user_id} 的情感档案不存在")
    
    async def _update_time_based_emotions_internal(
        self, 
        session: AsyncSession, 
        profile: DynamicEmotionProfile
    ):
        """内部方法：更新基于时间的情感参数"""
        now = datetime.now()
        last_update = profile.last_update or now
        time_passed = (now - last_update).total_seconds() / 3600  # 转换为小时
        
        if time_passed < 0.1:  # 小于6分钟，不更新
            return
        
        changes = {}
        
        # 1. 寂寞值增加（随时间流逝）
        loneliness_increase = self.config.LONELINESS_INCREASE_RATE * time_passed
        new_loneliness = min(self.config.MAX_VALUE, profile.loneliness + loneliness_increase)
        if abs(new_loneliness - profile.loneliness) > 0.5:
            changes['loneliness'] = new_loneliness - profile.loneliness
            profile.loneliness = new_loneliness
        
        # 2. 体力恢复（白天）或消耗（夜晚）
        if not self._is_night_time(now):
            # 白天：体力恢复
            energy_recovery = self.config.ENERGY_RECOVERY_RATE * time_passed
            new_energy = min(self.config.MAX_VALUE, profile.energy + energy_recovery)
            if abs(new_energy - profile.energy) > 0.5:
                changes['energy'] = new_energy - profile.energy
                profile.energy = new_energy
        else:
            # 夜晚：检查是否需要扣除体力
            last_drain = profile.last_night_drain
            if not last_drain or (now.date() > last_drain.date()):
                # 今天还没有扣除过夜晚体力
                energy_drain = -self.config.ENERGY_NIGHT_DRAIN
                new_energy = max(self.config.MIN_VALUE, profile.energy + energy_drain)
                changes['energy'] = new_energy - profile.energy
                profile.energy = new_energy
                profile.last_night_drain = now
                logger.debug(f"用户 {profile.user_id} 夜晚体力消耗: {energy_drain}")
        
        # 3. 更新社交需求
        await self._update_social_need_internal(session, profile)
        
        # 4. 保存变化
        if changes:
            profile.last_update = now
            await self._log_emotion_change(
                session, profile.user_id, 'time_update',
                f"时间流逝 {time_passed:.1f}小时", changes
            )
    
    def _is_night_time(self, now: datetime) -> bool:
        """判断是否是夜晚"""
        hour = now.hour
        return hour >= self.config.NIGHT_START_HOUR or hour < self.config.NIGHT_END_HOUR
    
    async def _update_social_need_internal(
        self,
        session: AsyncSession,
        profile: DynamicEmotionProfile
    ):
        """内部方法：更新社交需求"""
        # 1. 基础社交需求（基于寂寞值）
        base_need = profile.loneliness * 0.8
        
        # 2. 计算心情分数（-50到+50，0为中性）
        mood_score = self._calculate_mood_score(profile)
        
        # 3. 心情极端程度（距离中性状态的距离）
        mood_extremity = abs(mood_score)
        
        # 4. 如果心情极端，增加社交需求
        mood_impact = 0
        if mood_extremity > self.config.MOOD_EXTREME_THRESHOLD:
            mood_impact = (mood_extremity - self.config.MOOD_EXTREME_THRESHOLD) * self.config.MOOD_SOCIAL_IMPACT_FACTOR
        
        # 5. 综合计算社交需求
        weights = self.config.EMOTION_SOCIAL_WEIGHTS
        social_need = (
            base_need +
            profile.happiness * weights['happiness'] +
            profile.loneliness * weights['loneliness'] +
            profile.confidence * weights['confidence'] +
            profile.stress_level * weights['stress_level'] +
            mood_impact * weights['mood_extreme']
        )
        
        # 限制在0-100范围内
        profile.social_need = max(0, min(100, social_need))
    
    def _calculate_mood_score(self, profile: DynamicEmotionProfile) -> float:
        """
        计算心情分数
        
        Returns:
            心情分数 (-50 到 +50)
            正值表示正面情绪，负值表示负面情绪
        """
        happiness_contribution = (profile.happiness - 50) * 0.6
        confidence_contribution = (profile.confidence - 50) * 0.2
        energy_contribution = (profile.energy - 50) * 0.1
        stress_contribution = -(profile.stress_level - 20) * 0.1
        
        mood_score = (
            happiness_contribution +
            confidence_contribution +
            energy_contribution +
            stress_contribution
        )
        
        return max(-50, min(50, mood_score))
    
    # ==================== 聊天事件处理 ====================
    
    async def on_chat_start(self, user_id: str, user_message: str = ""):
        """
        聊天开始时的情感变化
        
        Args:
            user_id: 用户ID
            user_message: 用户消息内容（用于情感分析）
        """
        async with self.Session() as session:
            profile = await self.get_or_create_profile(user_id)
            
            # 分析用户消息的情感
            message_emotions = self._analyze_message_emotion(user_message) if user_message else {}
            
            changes = {
                'loneliness': -self.config.CHAT_LONELINESS_REDUCTION,
                'energy': -self.config.CHAT_ENERGY_COST,
                'happiness': self.config.CHAT_HAPPINESS_GAIN,
                'confidence': self.config.CHAT_CONFIDENCE_GAIN,
            }
            
            # 根据用户消息调整变化
            if message_emotions:
                for key, value in message_emotions.items():
                    if key in changes:
                        changes[key] += value
            
            # 应用变化
            result = await session.execute(
                select(DynamicEmotionProfile).where(
                    DynamicEmotionProfile.user_id == user_id
                )
            )
            profile = result.scalar_one()
            
            for key, value in changes.items():
                current_value = getattr(profile, key)
                new_value = max(
                    self.config.MIN_VALUE,
                    min(self.config.MAX_VALUE, current_value + value)
                )
                setattr(profile, key, new_value)
            
            # 更新时间戳
            profile.last_chat_time = datetime.now()
            profile.last_update = datetime.now()
            
            # 更新社交需求
            await self._update_social_need_internal(session, profile)
            
            # 记录变化
            await self._log_emotion_change(
                session, user_id, 'chat_start',
                f"开始聊天", changes
            )
            
            await session.commit()
            
            logger.info(f"💝 用户 {user_id} 情感变化: {changes}")
    
    def _analyze_message_emotion(self, message: str) -> Dict[str, float]:
        """
        分析用户消息的情感倾向
        
        Args:
            message: 用户消息
            
        Returns:
            情感变化字典
        """
        emotions = {}
        
        # 快乐/悲伤
        positive_count = sum(1 for kw in self.config.POSITIVE_KEYWORDS if kw in message)
        negative_count = sum(1 for kw in self.config.NEGATIVE_KEYWORDS if kw in message)
        
        if positive_count > negative_count:
            emotions['happiness'] = positive_count * 5
        elif negative_count > positive_count:
            emotions['happiness'] = -negative_count * 3
        
        # 自信
        confidence_count = sum(1 for kw in self.config.CONFIDENCE_KEYWORDS if kw in message)
        if confidence_count > 0:
            emotions['confidence'] = confidence_count * 3
        
        # 压力
        stress_count = sum(1 for kw in self.config.STRESS_KEYWORDS if kw in message)
        if stress_count > 0:
            emotions['stress_level'] = stress_count * 5
        
        return emotions
    
    async def on_chat_response(self, user_id: str, response_quality: str = "good"):
        """
        聊天响应后的情感变化
        
        Args:
            user_id: 用户ID
            response_quality: 回复质量 (good/normal/bad)
        """
        async with self.Session() as session:
            result = await session.execute(
                select(DynamicEmotionProfile).where(
                    DynamicEmotionProfile.user_id == user_id
                )
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                return
            
            changes = {}
            
            if response_quality == "good":
                changes = {'happiness': 3.0, 'confidence': 2.0}
            elif response_quality == "bad":
                changes = {'happiness': -2.0, 'confidence': -1.0}
            
            if changes:
                for key, value in changes.items():
                    current_value = getattr(profile, key)
                    new_value = max(
                        self.config.MIN_VALUE,
                        min(self.config.MAX_VALUE, current_value + value)
                    )
                    setattr(profile, key, new_value)
                
                await self._log_emotion_change(
                    session, user_id, 'chat_response',
                    f"聊天响应（{response_quality}）", changes
                )
                
                await session.commit()
    
    async def on_no_response(self, user_id: str):
        """
        无法响应时的情感变化
        
        Args:
            user_id: 用户ID
        """
        async with self.Session() as session:
            result = await session.execute(
                select(DynamicEmotionProfile).where(
                    DynamicEmotionProfile.user_id == user_id
                )
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                return
            
            changes = {'confidence': -3.0, 'stress_level': 5.0}
            
            for key, value in changes.items():
                current_value = getattr(profile, key)
                new_value = max(
                    self.config.MIN_VALUE,
                    min(self.config.MAX_VALUE, current_value + value)
                )
                setattr(profile, key, new_value)
            
            await self._log_emotion_change(
                session, user_id, 'no_response',
                "无法响应用户", changes
            )
            
            await session.commit()
    
    # ==================== 主动聊天判断 ====================
    
    async def should_initiate_chat(self, user_id: str) -> Tuple[bool, str, Dict]:
        """
        判断是否应该主动发起聊天
        
        Args:
            user_id: 用户ID
            
        Returns:
            (是否主动聊天, 原因, 情感状态字典)
        """
        profile = await self.get_or_create_profile(user_id)
        
        # 获取情感状态
        emotion_state = self._get_emotion_state(profile)
        
        # 判断条件
        reasons = []
        score = 0
        
        # 1. 社交需求高
        if profile.social_need > 70:
            score += 30
            reasons.append(f"社交需求高({profile.social_need:.1f})")
        
        # 2. 寂寞值高
        if profile.loneliness > 60:
            score += 25
            reasons.append(f"感到寂寞({profile.loneliness:.1f})")
        
        # 3. 心情极端
        mood_score = self._calculate_mood_score(profile)
        if abs(mood_score) > 30:
            score += 20
            reasons.append(f"心情{'很好' if mood_score > 0 else '很差'}({mood_score:.1f})")
        
        # 4. 很久没聊天
        if profile.last_chat_time:
            hours_since_chat = (datetime.now() - profile.last_chat_time).total_seconds() / 3600
            if hours_since_chat > 4:
                score += 15
                reasons.append(f"很久没聊天({hours_since_chat:.1f}小时)")
        
        # 综合判断
        should_chat = score >= 20  # 进一步降低阈值，让当前用户能够触发主动聊天
        reason = " + ".join(reasons) if reasons else "无特殊原因"
        
        logger.debug(f"主动聊天判断 用户{user_id}: score={score}, should={should_chat}, reason={reason}")
        
        return should_chat, reason, emotion_state
    
    def _get_emotion_state(self, profile: DynamicEmotionProfile) -> Dict:
        """获取情感状态摘要"""
        return {
            'happiness': profile.happiness,
            'loneliness': profile.loneliness,
            'energy': profile.energy,
            'confidence': profile.confidence,
            'mood': profile.mood,
            'social_need': profile.social_need,
            'stress_level': profile.stress_level,
            'intimacy_level': profile.intimacy_level
        }
    
    # ==================== 情感风格获取 ====================
    
    async def get_emotion_influenced_style(self, user_id: str) -> Dict[str, any]:
        """
        获取受情感影响的回复风格
        
        Args:
            user_id: 用户ID
            
        Returns:
            风格字典
        """
        profile = await self.get_or_create_profile(user_id)
        
        # 基于情感参数决定风格
        style = self._calculate_personality_style(
            profile.happiness,
            profile.confidence,
            profile.energy,
            profile.mood
        )
        
        return {
            'style': style,
            'happiness': profile.happiness,
            'confidence': profile.confidence,
            'energy': profile.energy,
            'mood': profile.mood,
            'social_need': profile.social_need,
            'stress_level': profile.stress_level
        }
    
    def _calculate_personality_style(
        self,
        happiness: float,
        confidence: float,
        energy: float,
        mood: str
    ) -> str:
        """
        根据情感参数计算个性风格
        
        Args:
            happiness: 快乐值
            confidence: 自信值
            energy: 体力值
            mood: 心情
            
        Returns:
            风格类型
        """
        if confidence > 75 and happiness < 50:
            return "毒舌"
        elif confidence > 70 and happiness > 60:
            return "腹黑"
        elif confidence < 50 and happiness > 60:
            return "傲娇"
        elif mood == "excited" and confidence > 65:
            return "病娇"
        elif energy < 40:
            return "慵懒"
        elif happiness > 75:
            return "元气"
        else:
            return "随机"
    
    # ==================== 辅助方法 ====================
    
    async def _apply_emotion_changes(
        self,
        user_id: str,
        changes: Dict[str, any],
        change_type: str,
        description: str
    ):
        """应用情感变化（内部方法）"""
        async with self.Session() as session:
            result = await session.execute(
                select(DynamicEmotionProfile).where(
                    DynamicEmotionProfile.user_id == user_id
                )
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                return
            
            for key, value in changes.items():
                if hasattr(profile, key):
                    current_value = getattr(profile, key)
                    new_value = max(
                        self.config.MIN_VALUE,
                        min(self.config.MAX_VALUE, current_value + value)
                    )
                    setattr(profile, key, new_value)
            
            profile.last_update = datetime.now()
            
            await self._log_emotion_change(
                session, user_id, change_type, description, changes
            )
            
            await session.commit()
    
    async def _log_emotion_change(
        self,
        session: AsyncSession,
        user_id: str,
        change_type: str,
        description: str,
        changes: Dict[str, float]
    ):
        """记录情感变化日志"""
        log = EmotionChangeLog(
            user_id=user_id,
            change_type=change_type,
            description=description,
            emotion_changes=json.dumps(changes, ensure_ascii=False)  # 使用旧版本列名
        )
        session.add(log)
    
    async def get_intimacy_ranking(self) -> List[Tuple[str, float]]:
        """
        获取亲密度排行
        
        Returns:
            [(user_id, intimacy_level), ...] 按亲密度降序
        """
        async with self.Session() as session:
            result = await session.execute(
                select(
                    DynamicEmotionProfile.user_id,
                    DynamicEmotionProfile.intimacy_level
                ).order_by(desc(DynamicEmotionProfile.intimacy_level)).limit(10)
            )
            return [(row[0], row[1]) for row in result.all()]


# ==================== 全局单例 ====================

_emotion_service: Optional[EmotionService] = None

def get_emotion_service() -> EmotionService:
    """获取全局情感服务实例"""
    global _emotion_service
    if _emotion_service is None:
        _emotion_service = EmotionService()
    return _emotion_service
