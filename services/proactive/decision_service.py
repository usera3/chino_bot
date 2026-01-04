"""
主动聊天决策服务 - Decision Service
负责判断何时应该主动聊天以及选择谁聊天
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import random
import math
from nonebot.log import logger

from services.emotion import get_emotion_service
from services.proactive.proactive_config import ProactiveConfig


class DecisionService:
    """主动聊天决策服务"""
    
    def __init__(self):
        self.emotion_service = get_emotion_service()
    
    async def evaluate_all_users(self) -> List[Dict]:
        """
        评估所有用户,返回候选列表
        返回: [{'user_id': str, 'reason': str, 'emotion_state': dict, 'priority_score': float}, ...]
        """
        try:
            # 获取亲密度排名
            intimacy_rankings = await self.emotion_service.get_intimacy_ranking()
            
            logger.debug(f"🎯 亲密度排名数据: {intimacy_rankings}")
            
            if not intimacy_rankings:
                logger.debug("没有用户需要检查")
                return []
            
            candidates = []
            for user_id, intimacy_level in intimacy_rankings:
                # 检查情感系统是否建议主动聊天
                should_chat, reason, emotion_state = await self.emotion_service.should_initiate_chat(user_id)
                
                logger.debug(f"⏳ 用户{user_id} 情感判断: should_chat={should_chat}, reason={reason}")
                
                if should_chat:
                    # 检查时间条件
                    time_ok = await self._check_time_conditions(user_id)
                    logger.debug(f"⏰ 用户{user_id} 时间条件检查: {time_ok}")
                    
                    if not time_ok:
                        continue
                    
                    # 计算优先级评分
                    priority_score = await self._calculate_priority(
                        user_id, intimacy_level, emotion_state
                    )
                    
                    candidate = {
                        'user_id': user_id,
                        'reason': reason,
                        'emotion_state': emotion_state,
                        'intimacy_level': intimacy_level,
                        'priority_score': priority_score
                    }
                    
                    candidates.append(candidate)
                    logger.debug(f"✅ 添加候选人: {candidate}")
                    
            logger.debug(f"📋 最终候选人数: {len(candidates)}")
            
            # 按优先级排序
            candidates.sort(key=lambda x: x['priority_score'], reverse=True)
            
            return candidates
            
        except Exception as e:
            logger.error(f"评估用户失败: {e}")
            return []
    
    async def _check_time_conditions(self, user_id: str) -> bool:
        """检查时间条件"""
        now = datetime.now()
        current_hour = now.hour
        
        # 1. 检查活跃时间段
        in_active_hours = any(
            start <= current_hour < end 
            for start, end in ProactiveConfig.ACTIVE_HOURS
        )
        logger.debug(f"⏰ 用户{user_id} 活跃时间检查: {current_hour}时, 结果={in_active_hours}")
        if not in_active_hours:
            return False
        
        # 2. 检查沉默时长
        profile = await self.emotion_service.get_or_create_profile(user_id)
        if profile.last_chat_time:
            silence_minutes = (now - profile.last_chat_time).total_seconds() / 60
        else:
            silence_minutes = 1440  # 新用户,假设沉默1天
        
        logger.debug(f"⏰ 用户{user_id} 沉默时长: {silence_minutes:.1f}分钟, 要求≥{ProactiveConfig.MIN_SILENCE_MINUTES}")
        if silence_minutes < ProactiveConfig.MIN_SILENCE_MINUTES:
            return False
        
        # 3. 检查最近是否已主动过
        if profile.last_proactive_time:
            since_last_proactive = (now - profile.last_proactive_time).total_seconds() / 60
            logger.debug(f"⏰ 用户{user_id} 距上次主动: {since_last_proactive:.1f}分钟, 要求≥{ProactiveConfig.MIN_PROACTIVE_INTERVAL_MINUTES}")
            if since_last_proactive < ProactiveConfig.MIN_PROACTIVE_INTERVAL_MINUTES:
                return False
        else:
            logger.debug(f"⏰ 用户{user_id} 从未主动过")
        
        # 4. 检查每日主动次数限制
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 导入数据库服务获取今日决策记录
        from services.database.database_service import get_database_service
        db_service = get_database_service()
        
        from models.proactive_models import ProactiveDecision
        from sqlalchemy import select
        
        async with db_service.async_session() as session:
            result = await session.execute(
                select(ProactiveDecision)
                .where(ProactiveDecision.user_id == user_id)
                .where(ProactiveDecision.created_at >= today_start)
                .where(ProactiveDecision.executed == True)
            )
            today_count = len(result.scalars().all())
            
            logger.debug(f"⏰ 用户{user_id} 今日主动次数: {today_count}, 限制={ProactiveConfig.MAX_DAILY_PROACTIVE}")
            # 临时修改，增加次数限制以测试
            temp_max_proactive = 20
            if today_count >= temp_max_proactive:
                return False
        
        logger.debug(f"✅ 用户{user_id} 通过所有时间条件检查")
        return True
    
    async def _calculate_priority(
        self, 
        user_id: str, 
        intimacy_level: float, 
        emotion_state: Dict
    ) -> float:
        """
        计算用户优先级评分
        返回: 0.0-1.0 之间的评分
        """
        score = 0.0
        
        # 1. 亲密度评分 (权重60%)
        intimacy_score = intimacy_level
        score += intimacy_score * ProactiveConfig.INTIMACY_WEIGHT
        
        # 2. 情感评分 (权重30%)
        # 基于寂寞值、社交需求、压力水平
        emotion_score = (
            emotion_state.get('loneliness', 0) / 100 * 0.4 +  # 寂寞越高,越需要主动
            emotion_state.get('social_need', 0) / 100 * 0.3 +  # 社交需求越高,越需要主动
            (100 - emotion_state.get('stress_level', 0)) / 100 * 0.3  # 压力越低,越适合主动
        )
        score += emotion_score * ProactiveConfig.EMOTION_WEIGHT
        
        # 3. 随机因素 (权重10%)
        random_score = random.random()
        score += random_score * ProactiveConfig.RANDOM_WEIGHT
        
        return min(1.0, max(0.0, score))
    
    def select_best_candidate(self, candidates: List[Dict]) -> Optional[Dict]:
        """
        从候选列表中选择最佳用户
        返回: {'user_id': str, 'reason': str, 'emotion_state': dict, 'priority_score': float}
        """
        if not candidates:
            return None
        
        # 已经按优先级排序,返回第一个
        return candidates[0]


# ==================== 全局单例 ====================
_decision_service: Optional[DecisionService] = None

def get_decision_service() -> DecisionService:
    """获取决策服务单例"""
    global _decision_service
    if _decision_service is None:
        _decision_service = DecisionService()
    return _decision_service




