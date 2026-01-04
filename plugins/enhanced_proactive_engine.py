"""
增强主动聊天引擎 - Enhanced Proactive Engine
集成动态情感系统的完整主动聊天解决方案
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

# 导入动态情感系统（新架构）
from services.emotion import get_emotion_service, EmotionConfig
from models.emotion_models import DynamicEmotionProfile

# 获取情感服务单例
emotion_service = get_emotion_service()

# ==================== 配置 ====================
class EnhancedProactiveConfig:
    """增强主动聊天配置"""
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 时间窗口配置
    ACTIVE_HOURS = [(9, 12), (14, 18), (19, 23)]  # 活跃时间段
    MIN_SILENCE_MINUTES = 5  # 最少沉默时间（5分钟，用于测试）
    MAX_SILENCE_HOURS = 24  # 最大沉默时间（1天）
    
    # 决策配置
    CHECK_INTERVAL_MINUTES = 5  # 检查间隔（5分钟，降低频率节省资源）
    MAX_DAILY_PROACTIVE = 10  # 每天最多主动聊天次数（提高用于测试）
    MIN_PROACTIVE_INTERVAL_MINUTES = 2  # 两次主动聊天的最小间隔（2分钟）
    
    # 好友检查配置
    ONLY_FRIENDS = True  # 只向好友发送主动消息
    MAX_FAIL_COUNT = 3  # 连续失败最大次数，超过后跳过该用户
    
    # 亲密度影响配置
    INTIMACY_WEIGHT = 0.6  # 亲密度权重
    EMOTION_WEIGHT = 0.3  # 情感权重
    RANDOM_WEIGHT = 0.1  # 随机权重

# ==================== 数据库模型 ====================
Base = declarative_base()

class ProactiveDecision(Base):
    """主动聊天决策记录"""
    __tablename__ = 'enhanced_proactive_decisions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    
    # 决策信息
    decision_reason = Column(Text)  # 决策原因
    emotion_state = Column(Text)  # JSON格式的情感状态
    intimacy_level = Column(Float)  # 亲密度
    priority_score = Column(Float)  # 优先级评分
    
    # 时间信息
    decided_at = Column(DateTime, default=datetime.now)
    executed_at = Column(DateTime, nullable=True)
    
    # 结果
    executed = Column(Boolean, default=False)
    success = Column(Boolean, nullable=True)
    fail_reason = Column(Text, nullable=True)  # 失败原因
    consecutive_fails = Column(Integer, default=0)  # 连续失败次数
    
    created_at = Column(DateTime, default=datetime.now)

# ==================== 增强主动聊天引擎 ====================
class EnhancedProactiveEngine:
    """增强主动聊天引擎核心类"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.running = False
        self.bot = None
        
    async def initialize(self):
        """初始化引擎"""
        # 初始化数据库
        self.engine = create_async_engine(
            EnhancedProactiveConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # 初始化动态情感系统
        await emotion_service.initialize()
        
        logger.info("🎯 增强主动聊天引擎初始化完成")
    
    async def start(self):
        """启动决策引擎"""
        self.running = True
        logger.info("✨ 增强主动聊天引擎已启动")
        
        # 启动主循环
        asyncio.create_task(self._main_loop())
        
        # 启动情感更新循环
        asyncio.create_task(self._emotion_update_loop())
    
    async def stop(self):
        """停止引擎"""
        self.running = False
        logger.info("增强主动聊天引擎已停止")
    
    async def _main_loop(self):
        """主循环：定期检查是否需要主动聊天"""
        while self.running:
            try:
                await asyncio.sleep(EnhancedProactiveConfig.CHECK_INTERVAL_MINUTES * 60)
                await self._check_and_decide()
            except Exception as e:
                logger.error(f"增强主动聊天决策循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _emotion_update_loop(self):
        """情感更新循环"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 每5分钟更新一次情感
                await self._update_all_emotions()
            except Exception as e:
                logger.error(f"情感更新循环错误: {e}")
    
    async def _update_all_emotions(self):
        """更新所有用户的情感状态"""
        try:
            # 获取所有用户
            async with self.async_session() as session:
                result = await session.execute(
                    select(DynamicEmotionProfile.user_id)
                )
                user_ids = [row[0] for row in result.all()]
            
            # 更新每个用户的情感
            for user_id in user_ids:
                await emotion_service.update_time_based_emotions(user_id)
            
            logger.debug("💝 情感状态更新完成")
        except Exception as e:
            logger.error(f"更新所有用户情感失败: {e}")
    
    async def _check_and_decide(self):
        """检查所有用户，决定是否主动聊天"""
        try:
            # 获取亲密度排名
            intimacy_rankings = await emotion_service.get_intimacy_ranking()
            
            if not intimacy_rankings:
                logger.debug("没有用户需要检查")
                return
            
            # 如果启用了好友检查，先过滤出好友列表
            friend_ids = set()
            if EnhancedProactiveConfig.ONLY_FRIENDS:
                try:
                    bot = get_bot()
                    friend_list = await bot.get_friend_list()
                    friend_ids = {str(friend['user_id']) for friend in friend_list}
                    logger.debug(f"📋 获取到 {len(friend_ids)} 个好友")
                except Exception as e:
                    logger.warning(f"获取好友列表失败: {e}，跳过好友检查")
                    # 如果获取好友列表失败，禁用好友检查
                    friend_ids = None
            
            # 按亲密度排序检查用户
            candidates = []
            for user_id, intimacy_level in intimacy_rankings:
                # 好友检查
                if EnhancedProactiveConfig.ONLY_FRIENDS and friend_ids is not None:
                    if user_id not in friend_ids:
                        logger.debug(f"⏭️ 跳过非好友用户: {user_id}")
                        continue
                
                # 检查历史失败次数
                consecutive_fails = await self._get_consecutive_fails(user_id)
                if consecutive_fails >= EnhancedProactiveConfig.MAX_FAIL_COUNT:
                    logger.debug(f"⏭️ 跳过连续失败{consecutive_fails}次的用户: {user_id}")
                    continue
                
                should_chat, reason, emotion_state = await emotion_service.should_initiate_chat(user_id)
                
                if should_chat:
                    # 检查时间条件
                    if not await self._check_time_conditions(user_id):
                        continue
                    
                    # 计算优先级评分
                    priority_score = await self._calculate_priority(user_id, intimacy_level, emotion_state)
                    
                    candidates.append({
                        'user_id': user_id,
                        'reason': reason,
                        'emotion_state': emotion_state,
                        'intimacy_level': intimacy_level,
                        'priority_score': priority_score
                    })
            
            if not candidates:
                logger.debug("没有用户需要主动聊天")
                return
            
            # 按优先级排序
            candidates.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # 选择最高优先级的用户
            selected = candidates[0]
            user_id = selected['user_id']
            
            logger.info(f"🎯 决定向用户 {user_id} 主动聊天：{selected['reason']}")
            
            # 记录决策
            await self._record_decision(
                user_id, 
                selected['reason'], 
                selected['emotion_state'], 
                selected['intimacy_level'],
                selected['priority_score']
            )
            
            # 执行主动聊天
            await self._execute_proactive_chat(user_id, selected['emotion_state'])
            
        except Exception as e:
            logger.error(f"增强主动聊天决策过程错误: {e}")
    
    async def _check_time_conditions(self, user_id: str) -> bool:
        """检查时间条件"""
        now = datetime.now()
        current_hour = now.hour
        
        # 1. 检查活跃时间段
        in_active_hours = any(start <= current_hour < end for start, end in EnhancedProactiveConfig.ACTIVE_HOURS)
        if not in_active_hours:
            return False
        
        # 2. 检查沉默时长
        profile = await emotion_service.get_or_create_profile(user_id)
        if profile.last_chat_time:
            silence_minutes = (now - profile.last_chat_time).total_seconds() / 60
        else:
            silence_minutes = 1440  # 新用户，假设沉默1天
        
        if silence_minutes < EnhancedProactiveConfig.MIN_SILENCE_MINUTES:
            return False
        
        # 3. 检查最近是否已主动过（使用最小间隔）
        if profile.last_proactive_time:
            since_last_proactive = (now - profile.last_proactive_time).total_seconds() / 60
            if since_last_proactive < EnhancedProactiveConfig.MIN_PROACTIVE_INTERVAL_MINUTES:
                return False
        
        # 4. 检查每日主动次数限制
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        async with self.async_session() as session:
            result = await session.execute(
                select(ProactiveDecision)
                .where(ProactiveDecision.user_id == user_id)
                .where(ProactiveDecision.decided_at >= today_start)
                .where(ProactiveDecision.executed == True)
            )
            today_count = len(result.scalars().all())
            
            if today_count >= EnhancedProactiveConfig.MAX_DAILY_PROACTIVE:
                return False
        
        return True
    
    async def _get_consecutive_fails(self, user_id: str) -> int:
        """获取用户最近的连续失败次数"""
        try:
            async with self.async_session() as session:
                # 获取最近的决策记录
                result = await session.execute(
                    select(ProactiveDecision)
                    .where(ProactiveDecision.user_id == user_id)
                    .where(ProactiveDecision.executed == True)
                    .order_by(desc(ProactiveDecision.executed_at))
                    .limit(10)
                )
                decisions = result.scalars().all()
                
                # 计算连续失败次数
                consecutive_fails = 0
                for decision in decisions:
                    if decision.success == False:
                        consecutive_fails += 1
                    elif decision.success == True:
                        # 遇到成功记录，重置计数
                        break
                
                return consecutive_fails
        except Exception as e:
            logger.error(f"获取连续失败次数失败: {e}")
            return 0
    
    async def _calculate_priority(self, user_id: str, intimacy_level: float, emotion_state: Dict) -> float:
        """计算用户优先级评分"""
        score = 0.0
        
        # 1. 亲密度评分
        intimacy_score = intimacy_level  # 0-1
        score += intimacy_score * EnhancedProactiveConfig.INTIMACY_WEIGHT
        
        # 2. 情感评分
        emotion_score = (
            emotion_state.get('loneliness', 0) / 100 * 0.4 +
            emotion_state.get('social_need', 0) / 100 * 0.3 +
            (100 - emotion_state.get('stress_level', 0)) / 100 * 0.3
        )
        score += emotion_score * EnhancedProactiveConfig.EMOTION_WEIGHT
        
        # 3. 随机因素
        random_score = random.random()
        score += random_score * EnhancedProactiveConfig.RANDOM_WEIGHT
        
        return score
    
    async def _record_decision(self, user_id: str, reason: str, emotion_state: Dict, intimacy_level: float, priority_score: float):
        """记录决策"""
        async with self.async_session() as session:
            decision = ProactiveDecision(
                user_id=user_id,
                decision_reason=reason,
                emotion_state=json.dumps(emotion_state),
                intimacy_level=intimacy_level,
                priority_score=priority_score
            )
            session.add(decision)
            await session.commit()
    
    async def _execute_proactive_chat(self, user_id: str, emotion_state: Dict):
        """执行主动聊天"""
        try:
            # 获取Bot实例
            bot = get_bot()
            
            # 更新情感系统（聊天开始）
            await emotion_service.on_chat_start(user_id, "主动聊天触发")
            
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
                
                # 更新情感档案
                profile = await emotion_service.get_or_create_profile(user_id)
                profile.last_proactive_time = datetime.now()
                await session.commit()
            
            # 调用聊天模块进行主动聊天
            success, fail_reason = await self._call_chat_module_for_proactive(user_id, emotion_state)
            
            # 更新决策记录的成功/失败状态
            if decision:
                async with self.async_session() as session:
                    decision.success = success
                    if not success:
                        decision.fail_reason = fail_reason
                        # 获取连续失败次数
                        consecutive_fails = await self._get_consecutive_fails(user_id)
                        decision.consecutive_fails = consecutive_fails + 1
                        
                        if consecutive_fails + 1 >= EnhancedProactiveConfig.MAX_FAIL_COUNT:
                            logger.warning(f"⚠️ 用户 {user_id} 连续失败 {consecutive_fails + 1} 次，将被暂时跳过")
                    await session.commit()
            
            if success:
                logger.info(f"✅ 已执行主动聊天：用户 {user_id}")
            else:
                logger.warning(f"⚠️ 主动聊天失败：用户 {user_id}, 原因：{fail_reason}")
            
        except Exception as e:
            logger.error(f"执行主动聊天失败: {e}")
    
    async def _call_chat_module_for_proactive(self, user_id: str, emotion_state: Dict) -> Tuple[bool, str]:
        """调用聊天模块进行主动聊天
        
        Returns:
            Tuple[bool, str]: (是否成功, 失败原因)
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
                return (True, "")
            else:
                logger.warning("AI生成主动聊天内容失败")
                return (False, "AI生成内容失败")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"调用聊天模块失败: {e}")
            
            # 检查是否是"非好友"错误
            if "添加对方为好友" in error_msg or "not a friend" in error_msg.lower():
                return (False, "非好友")
            else:
                return (False, f"发送失败: {error_msg[:50]}")
    
    async def _build_proactive_system_prompt(self, user_id: str, emotion_state: Dict) -> str:
        """构建主动聊天的系统提示"""
        # 获取用户当前角色
        from .chat_plugin_advanced import db_manager
        role_profile = await db_manager.get_role_profile(user_id)
        
        # 获取情感风格
        emotion_style = await emotion_service.get_emotion_influenced_style(user_id)
        
        # 检查是否体力不足
        if emotion_style.get('be_resting'):
            return f"""你是一个真诚、友善的AI助手，但现在很累了。

【当前状态】
体力值: {emotion_state.get('energy', 50):.1f}/100
心情: {emotion_state.get('mood', 'neutral')}

【任务】
由于体力不足，你需要礼貌地表示自己累了，正在休息，暂时无法聊天。

请生成一个简短的消息，表示自己累了需要休息，直接输出，不要任何前缀。"""
        
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
亲密度：{emotion_state.get('intimacy_level', 0.5):.2f}

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
亲密度：{emotion_state.get('intimacy_level', 0.5):.2f}

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
            await emotion_service.on_chat_response(user_id, "good")
        else:
            await emotion_service.on_chat_response(user_id, "neutral")
        
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
        await emotion_service.on_no_response(user_id)
        
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
    
    async def update_user_activity(self, user_id: str, user_message: str = ""):
        """更新用户活跃时间"""
        # 更新情感系统（包含消息情感分析）
        await emotion_service.on_chat_start(user_id, user_message)

# ==================== 全局实例 ====================
enhanced_proactive_engine = EnhancedProactiveEngine()

# ==================== NoneBot 集成 ====================
driver = get_driver()

@driver.on_startup
async def start_enhanced_proactive_engine():
    """Bot启动时初始化增强主动聊天引擎"""
    await enhanced_proactive_engine.initialize()
    await enhanced_proactive_engine.start()
    logger.info("🎉 增强主动聊天系统已启动！Bot现在会智能地决定何时主动聊天了~")

@driver.on_shutdown
async def stop_enhanced_proactive_engine():
    """Bot关闭时停止引擎"""
    await enhanced_proactive_engine.stop()

# 导出给其他插件使用
__all__ = ['enhanced_proactive_engine', 'EnhancedProactiveEngine']
