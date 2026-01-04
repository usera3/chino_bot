"""
情感服务 - 核心情感引擎（PAD三维模型 + 昼夜节律 + 随机事件）
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random
from nonebot.log import logger

from models.emotion_models import (
    EmotionState, DailyEvent, ActivityLog,
    get_emotion_session, init_emotion_database
)
from config.activity_config import ACTIVITIES, ActivityConfig
from config.event_config import POSITIVE_EVENTS, NEUTRAL_EVENTS, NEGATIVE_EVENTS, DEFAULT_EVENT_WEIGHTS
from utils.emotion_utils import EmotionUtils


class EmotionService:
    """情感与行为服务"""
    
    def __init__(self):
        """初始化情感服务"""
        # 确保数据库已初始化
        init_emotion_database()
        
        # 智乃的人格配置（OCEAN五大人格）
        self.personality = {
            "openness": 0.6,           # 中等开放性
            "conscientiousness": 0.8,   # 高责任心
            "extraversion": 0.3,        # 低外向性（内向）
            "agreeableness": 0.7,       # 高宜人性（温柔）
            "neuroticism": 0.4          # 中低神经质（相对稳定）
        }
        
        # 状态缓存（避免频繁数据库访问）
        self._state_cache: Dict[str, Tuple[EmotionState, datetime]] = {}
        self._cache_ttl = 60  # 缓存60秒
        
        logger.success("✅ 情感服务初始化完成（PAD三维模型）")
    
    # ==================== 核心API ====================
    
    async def get_emotion_state(self, user_id: str) -> EmotionState:
        """
        获取用户的情感状态
        优先从缓存读取，缓存过期则从数据库读取
        """
        # 检查缓存
        if user_id in self._state_cache:
            cached_state, cache_time = self._state_cache[user_id]
            if (datetime.now() - cache_time).total_seconds() < self._cache_ttl:
                return cached_state
        
        # 从数据库获取
        session = get_emotion_session()
        try:
            state = session.query(EmotionState).filter_by(user_id=user_id).first()
            
            if not state:
                # 首次创建默认状态
                state = self._create_default_state(user_id)
                session.add(state)
                session.commit()
                session.refresh(state)
            
            # 更新缓存
            self._state_cache[user_id] = (state, datetime.now())
            
            return state
        finally:
            session.close()
    
    async def update_emotion_state(
        self,
        user_id: str,
        updates: Dict[str, float]
    ) -> EmotionState:
        """
        更新情感状态
        
        Args:
            user_id: 用户ID
            updates: 要更新的字段和增量值 {"pleasure": +0.2, "energy": -10, ...}
        
        Returns:
            更新后的情感状态
        """
        session = get_emotion_session()
        try:
            state = session.query(EmotionState).filter_by(user_id=user_id).first()
            
            if not state:
                state = self._create_default_state(user_id)
                session.add(state)
            
            # 应用更新
            for field, delta in updates.items():
                if hasattr(state, field):
                    current_value = getattr(state, field) or 0
                    new_value = current_value + delta
                    
                    # 限制范围
                    if field in ['pleasure', 'arousal', 'dominance']:
                        new_value = EmotionUtils.clamp(new_value, -1.0, 1.0)
                    elif field in ['energy', 'hunger', 'sleepiness', 'loneliness', 'stress', 'interest']:
                        new_value = EmotionUtils.clamp(new_value, 0, 100)
                    elif field == 'intimacy_level':
                        new_value = EmotionUtils.clamp(new_value, 0.0, 1.0)
                    
                    setattr(state, field, new_value)
            
            # 更新派生状态
            state.mood_label = EmotionUtils.derive_mood_label(
                state.pleasure, state.arousal, state.dominance
            )
            state.last_update = datetime.now()
            
            session.commit()
            session.refresh(state)
            
            # 更新缓存
            self._state_cache[user_id] = (state, datetime.now())
            
            logger.debug(f"[Emotion] 更新状态 {user_id}: {updates} → {state.mood_label}")
            
            return state
        finally:
            session.close()
    
    async def apply_circadian_rhythm(self, user_id: str):
        """
        应用昼夜节律影响
        根据当前时间自动调整生理状态
        """
        current_hour = datetime.now().hour
        state = await self.get_emotion_state(user_id)
        
        updates = {}
        
        # 根据时间段调整状态
        if 6 <= current_hour < 9:
            # 早晨：逐渐清醒
            updates['arousal'] = 0.05
            updates['sleepiness'] = -2
        elif 9 <= current_hour < 12:
            # 上午：精力充沛
            updates['arousal'] = 0.03
            updates['energy'] = -1
        elif 12 <= current_hour < 14:
            # 午后：困倦
            updates['sleepiness'] = 3
            updates['arousal'] = -0.05
        elif 14 <= current_hour < 18:
            # 下午：恢复
            updates['sleepiness'] = -1
            updates['energy'] = -2
        elif 18 <= current_hour < 21:
            # 傍晚：逐渐疲惫
            updates['energy'] = -2
            updates['arousal'] = -0.02
        elif 21 <= current_hour < 23:
            # 晚上：准备休息
            updates['sleepiness'] = 2
            updates['arousal'] = -0.05
        else:
            # 深夜：应该睡觉
            updates['sleepiness'] = 5
            updates['energy'] = -3
        
        # 饥饿感随时间增加
        if state.last_update:
            hours_since_update = (datetime.now() - state.last_update).total_seconds() / 3600
            updates['hunger'] = hours_since_update * 5  # 每小时+5饥饿感
        
        # 孤独感随时间增加
        if state.last_chat_time:
            hours_since_chat = (datetime.now() - state.last_chat_time).total_seconds() / 3600
            if hours_since_chat > 3:
                updates['loneliness'] = (hours_since_chat - 3) * 2  # 3小时后开始增加
        
        if updates:
            await self.update_emotion_state(user_id, updates)
            logger.debug(f"[Circadian] {current_hour}点 应用昼夜节律: {updates}")
    
    async def trigger_random_event(self, user_id: str) -> Optional[Dict]:
        """
        触发随机事件
        
        Returns:
            事件信息字典，如果没有触发则返回None
        """
        # 30%概率触发事件
        if random.random() > 0.3:
            return None
        
        # 获取当前情感状态（影响事件类型概率）
        state = await self.get_emotion_state(user_id)
        
        # 根据当前情感调整事件概率
        if state.pleasure > 0.3:
            # 心情好时，更容易遇到正面事件
            event_weights = [0.5, 0.3, 0.2]  # [positive, neutral, negative]
        elif state.pleasure < -0.3:
            # 心情差时，更容易遇到负面事件
            event_weights = [0.2, 0.3, 0.5]
        else:
            event_weights = [0.35, 0.35, 0.3]
        
        event_type = random.choices(
            ['positive', 'neutral', 'negative'],
            weights=event_weights
        )[0]
        
        # 选择事件
        event = self._get_random_event(event_type)
        
        if event:
            # 保存事件
            await self._save_event(user_id, event_type, event)
            
            # 应用情感影响
            if 'impact' in event:
                await self.update_emotion_state(user_id, event['impact'])
            
            logger.info(f"[Event] {user_id} 触发事件: {event['desc']}")
            
            return event
        
        return None
    
    async def get_emotion_context(self, user_id: str) -> str:
        """
        生成情感上下文文本（供AI使用）
        
        Returns:
            格式化的情感状态描述
        """
        state = await self.get_emotion_state(user_id)
        
        # 获取最近的事件
        recent_events = await self._get_recent_events(user_id, hours=2)
        
        # 构建上下文
        context_parts = []
        
        # 1. 当前时间
        current_time = datetime.now().strftime('%H:%M')
        context_parts.append(f"当前时间: {current_time}")
        
        # 2. 当前活动
        if state.current_activity:
            context_parts.append(f"正在: {state.current_activity}")
        
        # 3. 情感状态描述
        mood_desc = EmotionUtils.describe_emotion(state.pleasure, state.arousal)
        context_parts.append(f"心情: {mood_desc}")
        
        # 4. 生理状态
        physical_desc = []
        if state.energy < 30:
            physical_desc.append("有点累")
        elif state.energy > 80:
            physical_desc.append("精力充沛")
        
        if state.sleepiness > 60:
            physical_desc.append("困")
        
        if state.hunger > 70:
            physical_desc.append("有点饿")
        
        if physical_desc:
            context_parts.append(f"状态: {', '.join(physical_desc)}")
        
        # 5. 最近事件（30%概率提及）
        if recent_events and random.random() < 0.3:
            event_desc = recent_events[-1]['event_desc']
            context_parts.append(f"最近: {event_desc}")
        
        # 6. 社交状态
        if state.loneliness > 60:
            context_parts.append("有点寂寞")
        
        return " | ".join(context_parts)
    
    async def on_chat(self, user_id: str):
        """
        聊天时的情感更新（减少孤独感、消耗体力、增加亲密度）
        """
        updates = {
            "loneliness": -5,
            "energy": -2,
            "intimacy_level": 0.01
        }
        
        await self.update_emotion_state(user_id, updates)
        
        # 更新最后聊天时间
        session = get_emotion_session()
        try:
            state = session.query(EmotionState).filter_by(user_id=user_id).first()
            if state:
                state.last_chat_time = datetime.now()
                session.commit()
        finally:
            session.close()
    
    # ==================== 内部方法 ====================
    
    def _create_default_state(self, user_id: str) -> EmotionState:
        """创建默认情感状态"""
        return EmotionState(
            user_id=user_id,
            pleasure=0.3,
            arousal=0.0,
            dominance=0.0,
            energy=80.0,
            hunger=30.0,
            sleepiness=20.0,
            loneliness=40.0,
            intimacy_level=0.5,
            stress=20.0,
            interest=50.0,
            mood_label='平静'
        )
    
    def _get_random_event(self, event_type: str) -> Optional[Dict]:
        """获取随机事件"""
        events_map = {
            'positive': POSITIVE_EVENTS,
            'neutral': NEUTRAL_EVENTS,
            'negative': NEGATIVE_EVENTS
        }
        
        event_list = events_map.get(event_type, [])
        if not event_list:
            return None
        
        # 根据概率选择事件
        events = []
        probs = []
        for event in event_list:
            events.append(event)
            probs.append(event.get('prob', 0.1))
        
        selected = random.choices(events, weights=probs)[0]
        return selected
    
    async def _save_event(self, user_id: str, event_type: str, event: Dict):
        """保存事件到数据库"""
        session = get_emotion_session()
        try:
            db_event = DailyEvent(
                user_id=user_id,
                event_type=event_type,
                event_desc=event['desc'],
                emotion_impact=event.get('impact', {})
            )
            session.add(db_event)
            session.commit()
        finally:
            session.close()
    
    async def _get_recent_events(self, user_id: str, hours: int = 2) -> List[Dict]:
        """获取最近的事件"""
        session = get_emotion_session()
        try:
            from sqlalchemy import desc
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            events = session.query(DailyEvent).filter(
                DailyEvent.user_id == user_id,
                DailyEvent.event_date >= cutoff_time
            ).order_by(desc(DailyEvent.event_date)).limit(5).all()
            
            return [
                {
                    "event_desc": e.event_desc,
                    "event_type": e.event_type,
                    "event_date": e.event_date
                }
                for e in events
            ]
        finally:
            session.close()


# ============ 全局单例 ============

_emotion_service = None


def get_emotion_service() -> EmotionService:
    """获取情感服务单例"""
    global _emotion_service
    if _emotion_service is None:
        _emotion_service = EmotionService()
    return _emotion_service


