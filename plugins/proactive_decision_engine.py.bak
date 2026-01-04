"""
主动聊天决策引擎 - Proactive Decision Engine
仅负责计算何时应该主动聊天以及和谁聊天
不负责内容生成，内容生成交给聊天模块处理
"""

from nonebot import get_driver, get_bot
from nonebot.log import logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
import json
import random
import math
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, desc, and_

# 导入情感系统
from .emotion_system import emotion_system, EmotionConfig

# ==================== 配置 ====================
class ProactiveDecisionConfig:
    """主动聊天决策配置"""
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 时间窗口配置
    ACTIVE_HOURS = [(9, 12), (14, 18), (19, 23)]  # 活跃时间段
    MIN_SILENCE_MINUTES = 120  # 最少沉默时间（2小时）
    MAX_SILENCE_HOURS = 24  # 最大沉默时间（1天）
    
    # 决策配置
    CHECK_INTERVAL_MINUTES = 15  # 检查间隔（15分钟）
    MAX_DAILY_PROACTIVE = 3  # 每天最多主动聊天次数
    
    # 用户优先级配置
    RELATIONSHIP_WEIGHT = 0.4  # 关系权重
    EMOTION_WEIGHT = 0.3  # 情感权重
    ACTIVITY_WEIGHT = 0.2  # 活跃度权重
    RANDOM_WEIGHT = 0.1  # 随机权重

# ==================== 数据库模型 ====================
Base = declarative_base()

class UserBehaviorProfile(Base):
    """用户行为画像表（简化版）"""
    __tablename__ = 'user_behavior_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, index=True)
    
    # 基础统计
    total_messages = Column(Integer, default=0)
    total_proactive_chats = Column(Integer, default=0)
    successful_proactive_chats = Column(Integer, default=0)
    
    # 时间偏好
    active_hours_json = Column(Text)  # JSON格式的活跃时间
    avg_response_time_seconds = Column(Float, default=300.0)
    
    # 关系程度
    relationship_score = Column(Float, default=0.0)  # -1到1，关系亲密度
    last_interaction_quality = Column(Float, default=0.5)  # 0-1，最近一次互动质量
    
    # 最近互动
    last_user_message_time = Column(DateTime)
    last_bot_proactive_time = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ProactiveDecision(Base):
    """主动聊天决策记录"""
    __tablename__ = 'proactive_decisions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    
    # 决策信息
    decision_reason = Column(Text)  # 决策原因
    emotion_state = Column(Text)  # JSON格式的情感状态
    priority_score = Column(Float)  # 优先级评分
    
    # 时间信息
    decided_at = Column(DateTime, default=datetime.now)
    executed_at = Column(DateTime, nullable=True)
    
    # 结果
    executed = Column(Boolean, default=False)
    success = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)

# ==================== 主动聊天决策引擎 ====================
class ProactiveDecisionEngine:
    """主动聊天决策引擎核心类"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.running = False
        self.bot = None
        self.chat_handler = None  # 聊天处理器引用
        
    async def initialize(self):
        """初始化引擎"""
        # 初始化数据库
        self.engine = create_async_engine(
            ProactiveDecisionConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # 初始化情感系统
        await emotion_system.initialize()
        
        logger.info("🎯 主动聊天决策引擎初始化完成")
    
    async def start(self):
        """启动决策引擎"""
        self.running = True
        logger.info("✨ 主动聊天决策引擎已启动")
        
        # 启动主循环
        asyncio.create_task(self._main_loop())
        
        # 启动情感衰减循环
        asyncio.create_task(self._emotion_decay_loop())
    
    async def stop(self):
        """停止引擎"""
        self.running = False
        logger.info("主动聊天决策引擎已停止")
    
    async def _main_loop(self):
        """主循环：定期检查是否需要主动聊天"""
        while self.running:
            try:
                await asyncio.sleep(ProactiveDecisionConfig.CHECK_INTERVAL_MINUTES * 60)
                await self._check_and_decide()
            except Exception as e:
                logger.error(f"主动聊天决策循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _emotion_decay_loop(self):
        """情感衰减循环"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # 每小时执行一次
                await emotion_system.decay_emotions()
            except Exception as e:
                logger.error(f"情感衰减循环错误: {e}")
    
    async def _check_and_decide(self):
        """检查所有用户，决定是否主动聊天"""
        try:
            # 获取所有用户行为画像
            async with self.async_session() as session:
                result = await session.execute(select(UserBehaviorProfile))
                profiles = result.scalars().all()
            
            if not profiles:
                return
            
            # 计算每个用户的优先级
            candidates = []
            for profile in profiles:
                should_chat, reason, emotion_state = await self._evaluate_user(profile)
                if should_chat:
                    priority_score = await self._calculate_priority(profile, emotion_state)
                    candidates.append({
                        'profile': profile,
                        'reason': reason,
                        'emotion_state': emotion_state,
                        'priority_score': priority_score
                    })
            
            if not candidates:
                logger.debug("没有用户需要主动聊天")
                return
            
            # 按优先级排序
            candidates.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # 选择最高优先级的用户
            selected = candidates[0]
            user_id = selected['profile'].user_id
            
            logger.info(f"🎯 决定向用户 {user_id} 主动聊天：{selected['reason']}")
            
            # 记录决策
            await self._record_decision(user_id, selected['reason'], selected['emotion_state'], selected['priority_score'])
            
            # 执行主动聊天（调用聊天模块）
            await self._execute_proactive_chat(user_id, selected['emotion_state'])
            
        except Exception as e:
            logger.error(f"主动聊天决策过程错误: {e}")
    
    async def _evaluate_user(self, profile: UserBehaviorProfile) -> Tuple[bool, str, Dict]:
        """
        评估用户是否需要主动聊天
        返回：(是否聊天, 原因, 情感状态)
        """
        now = datetime.now()
        current_hour = now.hour
        
        # 1. 检查时间窗口
        in_active_hours = any(start <= current_hour < end for start, end in ProactiveDecisionConfig.ACTIVE_HOURS)
        if not in_active_hours:
            return False, "不在活跃时间", {}
        
        # 2. 检查沉默时长
        if profile.last_user_message_time:
            silence_minutes = (now - profile.last_user_message_time).total_seconds() / 60
        else:
            silence_minutes = 1440  # 新用户，假设沉默1天
        
        if silence_minutes < ProactiveDecisionConfig.MIN_SILENCE_MINUTES:
            return False, f"沉默时间不足（{silence_minutes:.0f}分钟）", {}
        
        # 3. 检查最近是否已主动过
        if profile.last_bot_proactive_time:
            since_last_proactive = (now - profile.last_bot_proactive_time).total_seconds() / 60
            if since_last_proactive < ProactiveDecisionConfig.MIN_SILENCE_MINUTES:
                return False, "最近刚主动过", {}
        
        # 4. 检查每日主动次数限制
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        async with self.async_session() as session:
            result = await session.execute(
                select(ProactiveDecision)
                .where(ProactiveDecision.user_id == profile.user_id)
                .where(ProactiveDecision.decided_at >= today_start)
                .where(ProactiveDecision.executed == True)
            )
            today_count = len(result.scalars().all())
            
            if today_count >= ProactiveDecisionConfig.MAX_DAILY_PROACTIVE:
                return False, f"今日主动次数已达上限（{today_count}次）", {}
        
        # 5. 使用情感系统判断
        should_chat, emotion_reason, emotion_state = await emotion_system.should_initiate_chat(profile.user_id)
        
        if should_chat:
            return True, f"情感驱动：{emotion_reason}", emotion_state
        
        return False, "情感状态不适合主动聊天", {}
    
    async def _calculate_priority(self, profile: UserBehaviorProfile, emotion_state: Dict) -> float:
        """计算用户优先级评分"""
        score = 0.0
        
        # 1. 关系评分
        relationship_score = (profile.relationship_score + 1) / 2  # 归一化到0-1
        score += relationship_score * ProactiveDecisionConfig.RELATIONSHIP_WEIGHT
        
        # 2. 情感评分
        if emotion_state:
            emotion_score = (
                emotion_state.get('loneliness', 0) / 100 * 0.4 +
                emotion_state.get('social_need', 0) / 100 * 0.3 +
                (100 - emotion_state.get('stress_level', 0)) / 100 * 0.3
            )
            score += emotion_score * ProactiveDecisionConfig.EMOTION_WEIGHT
        
        # 3. 活跃度评分
        activity_score = min(1.0, profile.total_messages / 100)  # 消息越多越活跃
        score += activity_score * ProactiveDecisionConfig.ACTIVITY_WEIGHT
        
        # 4. 随机因素
        random_score = random.random()
        score += random_score * ProactiveDecisionConfig.RANDOM_WEIGHT
        
        return score
    
    async def _record_decision(self, user_id: str, reason: str, emotion_state: Dict, priority_score: float):
        """记录决策"""
        async with self.async_session() as session:
            decision = ProactiveDecision(
                user_id=user_id,
                decision_reason=reason,
                emotion_state=json.dumps(emotion_state),
                priority_score=priority_score
            )
            session.add(decision)
            await session.commit()
    
    async def _execute_proactive_chat(self, user_id: str, emotion_state: Dict):
        """
        执行主动聊天
        这里不直接生成内容，而是调用聊天模块
        """
        try:
            # 获取Bot实例
            bot = get_bot()
            
            # 构建主动聊天的触发消息
            # 这里我们发送一个特殊的系统消息来触发聊天模块
            trigger_message = f"主动聊天触发：用户{user_id}，情感状态：{emotion_state.get('mood', 'neutral')}"
            
            # 更新情感系统
            await emotion_system.on_chat_start(user_id)
            
            # 记录执行时间
            async with self.async_session() as session:
                # 更新决策记录
                result = await session.execute(
                    select(ProactiveDecision)
                    .where(ProactiveDecision.user_id == user_id)
                    .where(ProactiveDecision.executed == False)
                    .order_by(desc(ProactiveDecision.decided_at))
                    .limit(1)
                )
                decision = result.scalar_one_or_none()
                if decision:
                    decision.executed = True
                    decision.executed_at = datetime.now()
                
                # 更新用户画像
                result = await session.execute(
                    select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
                )
                profile = result.scalar_one_or_none()
                if profile:
                    profile.last_bot_proactive_time = datetime.now()
                    profile.total_proactive_chats += 1
                
                await session.commit()
            
            # 调用聊天模块进行主动聊天
            await self._call_chat_module_for_proactive(user_id, emotion_state)
            
            logger.info(f"✅ 已执行主动聊天：用户 {user_id}")
            
        except Exception as e:
            logger.error(f"执行主动聊天失败: {e}")
    
    async def _call_chat_module_for_proactive(self, user_id: str, emotion_state: Dict):
        """
        调用聊天模块进行主动聊天
        这里需要与聊天模块集成
        """
        try:
            # 导入聊天模块
            from .chat_plugin_advanced import db_manager, AdvancedDeepSeekAPI, IntelligentMemoryManager
            
            # 构建主动聊天的系统提示
            system_prompt = await self._build_proactive_system_prompt(user_id, emotion_state)
            
            # 构建消息上下文
            messages = [{"role": "system", "content": system_prompt}]
            
            # 添加主动聊天的触发消息
            messages.append({
                "role": "user", 
                "content": "请主动发起一个自然的聊天开场白，就像真人朋友主动找你聊天一样。"
            })
            
            # 调用AI生成回复
            ai_reply = await AdvancedDeepSeekAPI.chat_completion(messages)
            
            if ai_reply:
                # 获取Bot实例并发送消息
                bot = get_bot()
                await bot.send_private_msg(user_id=int(user_id), message=ai_reply)
                
                # 保存到聊天记录
                await db_manager.save_message(
                    user_id, 'assistant', ai_reply, 0.7, 'proactive'
                )
                
                logger.info(f"💬 主动聊天消息已发送：{ai_reply[:50]}")
            else:
                logger.warning("AI生成主动聊天内容失败")
                
        except Exception as e:
            logger.error(f"调用聊天模块失败: {e}")
    
    async def _build_proactive_system_prompt(self, user_id: str, emotion_state: Dict) -> str:
        """构建主动聊天的系统提示"""
        # 获取用户当前角色
        from .chat_plugin_advanced import db_manager
        role_profile = await db_manager.get_role_profile(user_id)
        
        # 获取情感风格
        emotion_style = await emotion_system.get_emotion_influenced_style(user_id)
        
        # 基础提示
        if role_profile and role_profile.is_active:
            base_prompt = f"""🎭 你正在扮演角色：{role_profile.role_name}
角色设定：{role_profile.role_prompt}

【主动聊天任务】
现在要以这个角色的身份主动找朋友聊天。

【当前情感状态】
心情：{emotion_state.get('mood', 'neutral')}
快乐值：{emotion_state.get('happiness', 50):.1f}
寂寞值：{emotion_state.get('loneliness', 50):.1f}
体力值：{emotion_state.get('energy', 50):.1f}
自信值：{emotion_state.get('confidence', 50):.1f}

【回复风格指导】
- 根据情感状态调整语气和内容
- 保持角色人设的一致性
- 像真人朋友主动聊天一样自然
- 不要提及"主动聊天"或"系统触发"等

请生成一个自然的开场白，直接输出，不要任何前缀。"""
        else:
            base_prompt = f"""你是一个真诚、友善的AI助手，现在要主动找朋友聊天。

【当前情感状态】
心情：{emotion_state.get('mood', 'neutral')}
快乐值：{emotion_state.get('happiness', 50):.1f}
寂寞值：{emotion_state.get('loneliness', 50):.1f}
体力值：{emotion_state.get('energy', 50):.1f}
自信值：{emotion_state.get('confidence', 50):.1f}

【回复风格指导】
- 根据情感状态调整语气和内容
- 像真人朋友主动聊天一样自然
- 不要提及"主动聊天"或"系统触发"等

请生成一个自然的开场白，直接输出，不要任何前缀。"""
        
        return base_prompt
    
    async def record_user_response(self, user_id: str, response_text: str, continued: bool = False):
        """记录用户响应（用于情感系统更新）"""
        # 更新情感系统
        if continued:
            await emotion_system.on_chat_response(user_id, "good")
        else:
            await emotion_system.on_chat_response(user_id, "neutral")
        
        # 更新决策记录
        async with self.async_session() as session:
            result = await session.execute(
                select(ProactiveDecision)
                .where(ProactiveDecision.user_id == user_id)
                .where(ProactiveDecision.executed == True)
                .order_by(desc(ProactiveDecision.executed_at))
                .limit(1)
            )
            decision = result.scalar_one_or_none()
            if decision:
                decision.success = True
                await session.commit()
    
    async def record_no_response(self, user_id: str):
        """记录用户无响应"""
        # 更新情感系统
        await emotion_system.on_no_response(user_id)
        
        # 更新决策记录
        async with self.async_session() as session:
            result = await session.execute(
                select(ProactiveDecision)
                .where(ProactiveDecision.user_id == user_id)
                .where(ProactiveDecision.executed == True)
                .order_by(desc(ProactiveDecision.executed_at))
                .limit(1)
            )
            decision = result.scalar_one_or_none()
            if decision:
                decision.success = False
                await session.commit()
    
    async def get_or_create_profile(self, user_id: str) -> UserBehaviorProfile:
        """获取或创建用户行为画像"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                profile = UserBehaviorProfile(
                    user_id=user_id,
                    relationship_score=0.0,
                    last_interaction_quality=0.5
                )
                session.add(profile)
                await session.commit()
                await session.refresh(profile)
            
            return profile
    
    async def update_user_activity(self, user_id: str):
        """更新用户活跃时间"""
        profile = await self.get_or_create_profile(user_id)
        
        async with self.async_session() as session:
            result = await session.execute(
                select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                profile.last_user_message_time = datetime.now()
                profile.total_messages += 1
                profile.updated_at = datetime.now()
                await session.commit()

# ==================== 全局实例 ====================
proactive_decision_engine = ProactiveDecisionEngine()

# ==================== NoneBot 集成 ====================
driver = get_driver()

@driver.on_startup
async def start_proactive_decision_engine():
    """Bot启动时初始化主动聊天决策引擎"""
    await proactive_decision_engine.initialize()
    await proactive_decision_engine.start()
    logger.info("🎉 主动聊天决策系统已启动！Bot现在会智能地决定何时主动聊天了~")

@driver.on_shutdown
async def stop_proactive_decision_engine():
    """Bot关闭时停止引擎"""
    await proactive_decision_engine.stop()

# 导出给其他插件使用
__all__ = ['proactive_decision_engine', 'ProactiveDecisionEngine']

