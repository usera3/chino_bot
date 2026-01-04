"""
主动聊天引擎 - Proactive Chat Engine
让AI像真人一样主动发起对话

核心设计理念：
1. 时机感知：基于用户行为模式和时间窗口
2. 上下文理解：深度学习用户兴趣和对话历史
3. 自然度优化：使用强化学习不断优化开场白质量
4. 情感智能：根据用户状态调整主动性
"""

from nonebot import require, get_driver, get_bot
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.log import logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
import json
import random
import math
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, desc, and_, or_, func
import httpx

# ==================== 配置 ====================
class ProactiveConfig:
    """主动聊天配置"""
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    API_KEY = "sk-4b0f9fcb168046f1ab1a6103dfb56380"
    MODEL = "deepseek-chat"
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 时间窗口配置（真人聊天习惯）
    ACTIVE_HOURS = [(9, 12), (14, 18), (19, 23)]  # 活跃时间段
    MIN_SILENCE_MINUTES = 120  # 最少沉默时间（2小时）
    MAX_SILENCE_HOURS = 24  # 最大沉默时间（1天）
    
    # 主动性配置
    BASE_PROACTIVITY = 0.3  # 基础主动性（30%）
    MAX_PROACTIVITY = 0.8  # 最大主动性（80%）
    MIN_PROACTIVITY = 0.05  # 最小主动性（5%）
    
    # 强化学习配置
    POSITIVE_REWARD = 1.0  # 用户积极回应
    NEUTRAL_REWARD = 0.0  # 用户中性回应
    NEGATIVE_REWARD = -1.0  # 用户消极回应
    NO_RESPONSE_PENALTY = -0.5  # 用户不回应
    LEARNING_RATE = 0.1  # 学习率
    
    # 内容生成配置
    TEMPERATURE = 0.9  # 高温度，更有创造性
    CHECK_INTERVAL_MINUTES = 15  # 检查间隔（15分钟）

# ==================== 数据库模型 ====================
Base = declarative_base()

class UserBehaviorProfile(Base):
    """用户行为画像表"""
    __tablename__ = 'user_behavior_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, index=True)
    
    # 时间偏好
    active_hours_json = Column(Text)  # JSON格式的活跃时间
    avg_response_time_seconds = Column(Float, default=300.0)  # 平均响应时间
    
    # 主动聊天统计
    total_proactive_chats = Column(Integer, default=0)
    successful_proactive_chats = Column(Integer, default=0)  # 用户有回应的
    proactivity_score = Column(Float, default=0.3)  # 当前主动性评分
    
    # 兴趣标签
    interest_tags_json = Column(Text)  # JSON格式的兴趣标签和权重
    
    # 最近互动
    last_user_message_time = Column(DateTime)
    last_bot_proactive_time = Column(DateTime)
    last_interaction_quality = Column(Float, default=0.5)  # 0-1，最近一次互动质量
    
    # 关系程度
    relationship_score = Column(Float, default=0.0)  # -1到1，关系亲密度
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ProactiveChatLog(Base):
    """主动聊天记录表"""
    __tablename__ = 'proactive_chat_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    
    # 聊天内容
    opening_message = Column(Text)  # 开场白
    opening_strategy = Column(String(50))  # 策略类型
    
    # 时机信息
    sent_at = Column(DateTime, default=datetime.now)
    silence_duration_minutes = Column(Float)  # 沉默时长
    time_of_day_hour = Column(Integer)  # 发送时刻
    
    # 响应信息
    user_responded = Column(Boolean, default=False)
    response_time_seconds = Column(Float, nullable=True)
    response_length = Column(Integer, nullable=True)
    conversation_continued = Column(Boolean, default=False)  # 是否继续聊天
    
    # 质量评分
    predicted_quality = Column(Float)  # 预测质量（发送前）
    actual_quality = Column(Float, nullable=True)  # 实际质量（收到回复后）
    reward = Column(Float, nullable=True)  # 强化学习奖励
    
    created_at = Column(DateTime, default=datetime.now)

class ConversationTopic(Base):
    """对话主题库"""
    __tablename__ = 'conversation_topics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    
    topic_name = Column(String(100))  # 主题名称
    topic_keywords = Column(Text)  # 关键词（JSON）
    success_rate = Column(Float, default=0.5)  # 成功率
    last_used = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.now)

# ==================== 主动聊天引擎 ====================
class ProactiveChatEngine:
    """主动聊天引擎核心类"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.running = False
        self.bot = None
        
    async def initialize(self):
        """初始化引擎"""
        # 初始化数据库
        self.engine = create_async_engine(
            ProactiveConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("🚀 主动聊天引擎初始化完成")
    
    async def start(self):
        """启动主动聊天引擎"""
        self.running = True
        logger.info("✨ 主动聊天引擎已启动")
        
        # 启动主循环
        asyncio.create_task(self._main_loop())
    
    async def stop(self):
        """停止引擎"""
        self.running = False
        logger.info("主动聊天引擎已停止")
    
    async def _main_loop(self):
        """主循环：定期检查是否需要主动聊天"""
        while self.running:
            try:
                await asyncio.sleep(ProactiveConfig.CHECK_INTERVAL_MINUTES * 60)
                await self._check_and_chat()
            except Exception as e:
                logger.error(f"主动聊天主循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_chat(self):
        """检查所有用户，决定是否主动聊天"""
        async with self.async_session() as session:
            # 获取所有用户行为画像
            result = await session.execute(select(UserBehaviorProfile))
            profiles = result.scalars().all()
            
            for profile in profiles:
                should_chat, reason = await self._should_initiate_chat(profile)
                
                if should_chat:
                    logger.info(f"准备向用户 {profile.user_id} 主动聊天：{reason}")
                    await self._initiate_proactive_chat(profile.user_id, reason)
    
    async def _should_initiate_chat(self, profile: UserBehaviorProfile) -> Tuple[bool, str]:
        """
        判断是否应该主动聊天
        返回：(是否聊天, 原因)
        
        决策因素：
        1. 时间窗口（是否在活跃时间）
        2. 沉默时长（是否足够久没联系）
        3. 主动性评分（强化学习得出的最优主动性）
        4. 关系程度（关系越好，越容易主动）
        5. 最近互动质量（如果上次聊得好，更愿意聊）
        """
        now = datetime.now()
        current_hour = now.hour
        
        # 1. 检查时间窗口
        in_active_hours = any(start <= current_hour < end for start, end in ProactiveConfig.ACTIVE_HOURS)
        if not in_active_hours:
            return False, "不在活跃时间"
        
        # 2. 检查沉默时长
        if profile.last_user_message_time:
            silence_minutes = (now - profile.last_user_message_time).total_seconds() / 60
        else:
            silence_minutes = 1440  # 新用户，假设沉默1天
        
        if silence_minutes < ProactiveConfig.MIN_SILENCE_MINUTES:
            return False, f"沉默时间不足（{silence_minutes:.0f}分钟）"
        
        # 3. 检查最近是否已主动过
        if profile.last_bot_proactive_time:
            since_last_proactive = (now - profile.last_bot_proactive_time).total_seconds() / 60
            if since_last_proactive < ProactiveConfig.MIN_SILENCE_MINUTES:
                return False, "最近刚主动过"
        
        # 4. 计算综合主动概率
        base_prob = profile.proactivity_score
        
        # 沉默时间越长，概率越高（使用对数函数，避免过快增长）
        silence_factor = min(1.0, math.log(silence_minutes / ProactiveConfig.MIN_SILENCE_MINUTES + 1) / 3)
        
        # 关系越好，概率越高
        relationship_factor = (profile.relationship_score + 1) / 2  # 归一化到0-1
        
        # 上次互动质量越高，概率越高
        quality_factor = profile.last_interaction_quality
        
        # 综合概率
        final_prob = base_prob * (1 + silence_factor + relationship_factor + quality_factor) / 4
        final_prob = max(ProactiveConfig.MIN_PROACTIVITY, 
                        min(ProactiveConfig.MAX_PROACTIVITY, final_prob))
        
        # 5. 随机决策
        if random.random() < final_prob:
            reason = f"沉默{silence_minutes:.0f}分钟，主动概率{final_prob:.2%}"
            return True, reason
        
        return False, f"主动概率不足（{final_prob:.2%}）"
    
    async def _initiate_proactive_chat(self, user_id: str, reason: str):
        """发起主动聊天"""
        try:
            # 1. 生成开场白
            opening_message, strategy = await self._generate_opening(user_id, reason)
            
            # 2. 💬 分段发送消息（提升用户体验）
            await self._send_split_message_to_user(user_id, opening_message)
            
            # 3. 记录
            await self._log_proactive_chat(user_id, opening_message, strategy, reason)
            
            # 4. 更新用户画像
            await self._update_profile_after_proactive(user_id)
            
            logger.info(f"✅ 已向用户 {user_id} 发送主动消息：{opening_message[:50]}")
            
        except Exception as e:
            logger.error(f"主动聊天失败: {e}")
    
    async def _generate_opening(self, user_id: str, reason: str) -> Tuple[str, str]:
        """
        生成自然的开场白
        
        策略：
        1. 基于历史话题的延续
        2. 分享有趣的发现/想法
        3. 关心用户状态
        4. 轻松的闲聊开场
        5. 基于时间的问候
        
        🎭 重要：会自动获取并保持用户当前的角色设定
        """
        # 获取用户画像和历史
        async with self.async_session() as session:
            result = await session.execute(
                select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                strategy = "first_contact"
                return "嗨~ 好久不见啦！最近怎么样呀？", strategy
            
            # 获取最近成功的主题
            result = await session.execute(
                select(ConversationTopic)
                .where(ConversationTopic.user_id == user_id)
                .order_by(desc(ConversationTopic.success_rate))
                .limit(5)
            )
            successful_topics = result.scalars().all()
        
        # 🎭 获取用户当前激活的角色（关键修复！）
        active_role = await self._get_active_role(user_id)
        
        # 选择策略
        strategies = []
        
        # 如果有成功的主题，30%概率延续
        if successful_topics and random.random() < 0.3:
            strategies.append("topic_continuation")
        
        # 20%概率分享发现
        if random.random() < 0.2:
            strategies.append("share_discovery")
        
        # 25%概率关心状态
        if random.random() < 0.25:
            strategies.append("check_status")
        
        # 25%概率时间相关
        if random.random() < 0.25:
            strategies.append("time_based")
        
        # 默认：轻松闲聊
        if not strategies:
            strategies.append("casual_chat")
        
        strategy = random.choice(strategies)
        
        # 使用AI生成自然的开场白（🎭 传入角色信息）
        prompt = await self._build_opening_prompt(user_id, strategy, profile, successful_topics, active_role)
        opening = await self._call_ai_for_opening(prompt)
        
        return opening, strategy
    
    async def _build_opening_prompt(
        self, 
        user_id: str, 
        strategy: str,
        profile: UserBehaviorProfile,
        topics: List[ConversationTopic],
        active_role = None  # 🎭 新增：角色信息
    ) -> str:
        """构建开场白生成提示（支持角色扮演）"""
        current_hour = datetime.now().hour
        
        # 🎭 如果有激活的角色，使用角色人设
        if active_role:
            base_prompt = f"""🎭 重要：你正在扮演一个角色，必须严格保持角色设定！

【角色设定】
角色名称：{active_role.role_name}
角色人设：{active_role.role_prompt}

【任务】
现在要以这个角色的身份主动找朋友聊天。

【场景信息】
当前时间：{current_hour}点
聊天对象：一位朋友（用户）
关系亲密度：{profile.relationship_score:.2f}（-1到1，越高越亲密）
最近互动质量：{profile.last_interaction_quality:.2f}（0到1，越高越好）

⚠️ 关键要求：
1. 必须完全以角色的语气、性格、说话方式来生成开场白
2. 不要说"我在扮演"或提及角色设定本身
3. 就像这个角色真的想主动找朋友聊天一样自然

"""
        else:
            # 没有角色时，使用正常人设
            base_prompt = f"""你是一个非常懂得社交的真人，现在要主动找朋友聊天。

当前时间：{current_hour}点
聊天对象：一位朋友
关系亲密度：{profile.relationship_score:.2f}（-1到1，越高越亲密）
最近互动质量：{profile.last_interaction_quality:.2f}（0到1，越高越好）

"""
        
        strategy_prompts = {
            "topic_continuation": f"""策略：延续之前聊过的话题
之前成功的话题：{topics[0].topic_name if topics else '无'}

要求：
1. 自然地提起之前聊过的内容
2. 加入新的角度或想法
3. 语气轻松，不要太刻意
4. 字数控制在20-40字
""",
            "share_discovery": """策略：分享有趣的发现或想法

要求：
1. 分享一个有趣的观察、想法或最近看到的内容
2. 可以是生活小事、网上看到的、突然的想法
3. 语气兴奋但不夸张
4. 自然地邀请对方参与讨论
5. 字数控制在25-45字
""",
            "check_status": """策略：关心朋友近况

要求：
1. 真诚地询问对方最近怎么样
2. 可以提到一些具体方面（工作、生活、心情等）
3. 语气温暖但不过分热情
4. 避免"好久不见"这种生硬开场
5. 字数控制在15-30字
""",
            "time_based": f"""策略：基于时间的问候

当前时段：{current_hour}点

要求：
1. 根据时间自然地打招呼（早/中/晚）
2. 结合这个时段的场景（早餐、午休、晚上等）
3. 轻松随意，像日常聊天
4. 字数控制在15-30字
""",
            "casual_chat": """策略：轻松闲聊开场

要求：
1. 非常随意自然的开场
2. 可以是emoji、口语化表达
3. 不要问太严肃的问题
4. 营造轻松氛围
5. 字数控制在10-25字
"""
        }
        
        prompt = base_prompt + strategy_prompts.get(strategy, strategy_prompts["casual_chat"])
        
        prompt += """

注意事项：
- 必须是中文
- 像真人聊天，口语化
- 可以用emoji，但不要太多（最多1-2个）
- 不要太正式，不要用"您"
- 不要说教或给建议（除非必要）
- 语气要自然，不做作

直接输出开场白，不要有任何前缀或解释："""
        
        return prompt
    
    async def _call_ai_for_opening(self, prompt: str) -> str:
        """调用AI生成开场白"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    ProactiveConfig.API_URL,
                    headers={
                        "Authorization": f"Bearer {ProactiveConfig.API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": ProactiveConfig.MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": ProactiveConfig.TEMPERATURE,
                        "max_tokens": 200
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    opening = result['choices'][0]['message']['content'].strip()
                    # 移除可能的引号
                    opening = opening.strip('"\'「」『』')
                    return opening
                else:
                    logger.error(f"AI生成失败: {response.status_code}")
                    return self._get_fallback_opening()
                    
        except Exception as e:
            logger.error(f"调用AI失败: {e}")
            return self._get_fallback_opening()
    
    def _get_fallback_opening(self) -> str:
        """备用开场白库"""
        openings = [
            "在吗？好久没聊天了",
            "突然想起你，最近怎么样呀",
            "嗨～有空聊聊吗",
            "分享个有趣的事儿～",
            "最近在忙啥呢",
            "好久不见啦！",
            "突然想找你聊聊天",
            "有个想法想跟你说说"
        ]
        return random.choice(openings)
    
    async def _send_split_message_to_user(self, user_id: str, message: str):
        """
        💬 分段发送消息到用户（提升用户体验）
        模拟真人聊天，按标点符号分段发送
        """
        # 简化的分段逻辑（参考chat_plugin_advanced中的实现）
        segments = self._split_message_simple(message)
        
        bot = get_bot()
        
        for i, segment in enumerate(segments):
            if i > 0:
                # 计算打字延迟
                delay = min(2.0, max(0.5, len(segment) * 0.03))
                await asyncio.sleep(delay)
            
            await bot.send_private_msg(user_id=int(user_id), message=segment)
            logger.info(f"💬 发送第 {i+1}/{len(segments)} 段：{segment[:30]}")
    
    def _split_message_simple(self, text: str) -> List[str]:
        """
        简单的消息分段逻辑，模拟真人聊天习惯
        - 按句号、问号、感叹号、省略号分段
        - 去掉每段末尾的标点
        """
        if not text or len(text) < 30:
            return [text]
        
        # 按主要标点分段（包括省略号）
        import re
        # 省略号的各种形式：...、。。。、……
        pattern = r'([。！？\n!?\.\.\.|。。。|……]+)'
        parts = re.split(pattern, text)
        
        segments = []
        current = ""
        
        for i, part in enumerate(parts):
            if part.strip():
                current += part
                # 如果是标点符号，或累积够长了，就作为一段
                if re.match(pattern, part) or len(current) > 50:
                    if current.strip():
                        # 💬 去掉末尾的标点符号（真人聊天习惯）
                        cleaned = current.strip().rstrip('。！？!?…')
                        # 处理省略号
                        cleaned = re.sub(r'\.{2,}$', '', cleaned)  # 去掉末尾的多个点
                        cleaned = re.sub(r'。{2,}$', '', cleaned)  # 去掉末尾的多个句号
                        if cleaned:
                            segments.append(cleaned)
                        current = ""
        
        if current.strip():
            # 最后一段也去掉标点
            cleaned = current.strip().rstrip('。！？!?…')
            cleaned = re.sub(r'\.{2,}$', '', cleaned)
            cleaned = re.sub(r'。{2,}$', '', cleaned)
            if cleaned:
                segments.append(cleaned)
        
        return segments if segments else [text]
    
    async def _log_proactive_chat(self, user_id: str, message: str, strategy: str, reason: str):
        """记录主动聊天"""
        async with self.async_session() as session:
            # 计算沉默时长
            result = await session.execute(
                select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            silence_minutes = 0
            if profile and profile.last_user_message_time:
                silence_minutes = (datetime.now() - profile.last_user_message_time).total_seconds() / 60
            
            log = ProactiveChatLog(
                user_id=user_id,
                opening_message=message,
                opening_strategy=strategy,
                silence_duration_minutes=silence_minutes,
                time_of_day_hour=datetime.now().hour,
                predicted_quality=0.5  # 初始预测
            )
            
            session.add(log)
            await session.commit()
    
    async def _update_profile_after_proactive(self, user_id: str):
        """更新用户画像（发送主动消息后）"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                profile.last_bot_proactive_time = datetime.now()
                profile.total_proactive_chats += 1
                await session.commit()
    
    async def record_user_response(
        self, 
        user_id: str, 
        response_text: str,
        continued_conversation: bool = False
    ):
        """
        记录用户响应（用于强化学习）
        
        这个函数应该在用户回复后被调用
        """
        async with self.async_session() as session:
            # 获取最近的主动聊天记录
            result = await session.execute(
                select(ProactiveChatLog)
                .where(ProactiveChatLog.user_id == user_id)
                .where(ProactiveChatLog.user_responded == False)
                .order_by(desc(ProactiveChatLog.created_at))
                .limit(1)
            )
            log = result.scalar_one_or_none()
            
            if not log:
                return
            
            # 计算响应时间
            response_time = (datetime.now() - log.sent_at).total_seconds()
            
            # 更新记录
            log.user_responded = True
            log.response_time_seconds = response_time
            log.response_length = len(response_text)
            log.conversation_continued = continued_conversation
            
            # 计算奖励
            reward = self._calculate_reward(response_time, len(response_text), continued_conversation)
            log.reward = reward
            log.actual_quality = (reward + 1) / 2  # 归一化到0-1
            
            await session.commit()
            
            # 更新用户画像（强化学习）
            await self._update_profile_with_reward(user_id, reward, log.actual_quality)
            
            logger.info(f"记录用户响应：{user_id}，奖励={reward:.2f}")
    
    def _calculate_reward(self, response_time: float, response_length: int, continued: bool) -> float:
        """
        计算强化学习奖励
        
        奖励因素：
        1. 响应时间（越快越好，但不能太快）
        2. 响应长度（越长越好，但不能太短）
        3. 是否继续对话（最重要）
        """
        reward = 0.0
        
        # 响应时间评分（30-300秒最佳）
        if response_time < 10:
            time_score = -0.2  # 太快可能是敷衍
        elif 30 <= response_time <= 300:
            time_score = 0.3
        elif 300 < response_time <= 1800:
            time_score = 0.1
        else:
            time_score = -0.3  # 太慢说明不太想聊
        
        # 响应长度评分
        if response_length < 3:
            length_score = -0.3  # 太短，敷衍
        elif 3 <= response_length <= 10:
            length_score = 0.2
        elif 10 < response_length <= 50:
            length_score = 0.4
        else:
            length_score = 0.3  # 很长的回复通常是积极的
        
        # 是否继续对话（最重要）
        conversation_score = 1.0 if continued else 0.0
        
        # 综合计算（加权）
        reward = time_score * 0.2 + length_score * 0.3 + conversation_score * 0.5
        
        # 归一化到-1到1
        reward = max(-1.0, min(1.0, reward))
        
        return reward
    
    async def _update_profile_with_reward(self, user_id: str, reward: float, quality: float):
        """使用强化学习更新用户画像"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserBehaviorProfile).where(UserBehaviorProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                # 创建新画像
                profile = UserBehaviorProfile(
                    user_id=user_id,
                    proactivity_score=ProactiveConfig.BASE_PROACTIVITY
                )
                session.add(profile)
            
            # 更新成功计数
            if reward > 0:
                profile.successful_proactive_chats += 1
            
            # 强化学习更新主动性评分
            # Q-learning风格的更新
            old_score = profile.proactivity_score
            new_score = old_score + ProactiveConfig.LEARNING_RATE * reward
            
            # 限制范围
            new_score = max(ProactiveConfig.MIN_PROACTIVITY, 
                          min(ProactiveConfig.MAX_PROACTIVITY, new_score))
            
            profile.proactivity_score = new_score
            profile.last_interaction_quality = quality
            
            # 更新关系评分
            relationship_delta = reward * 0.1  # 慢速更新关系
            profile.relationship_score = max(-1.0, min(1.0, 
                profile.relationship_score + relationship_delta))
            
            profile.updated_at = datetime.now()
            
            await session.commit()
            
            logger.info(f"用户 {user_id} 画像更新：主动性 {old_score:.3f} -> {new_score:.3f}")
    
    async def record_no_response(self, user_id: str):
        """记录用户未响应（惩罚）"""
        async with self.async_session() as session:
            # 获取最近的未响应主动聊天
            result = await session.execute(
                select(ProactiveChatLog)
                .where(ProactiveChatLog.user_id == user_id)
                .where(ProactiveChatLog.user_responded == False)
                .where(ProactiveChatLog.sent_at < datetime.now() - timedelta(hours=2))
                .order_by(desc(ProactiveChatLog.created_at))
            )
            logs = result.scalars().all()
            
            for log in logs:
                log.reward = ProactiveConfig.NO_RESPONSE_PENALTY
                log.actual_quality = 0.1
                
                # 更新画像（惩罚）
                await self._update_profile_with_reward(
                    user_id, 
                    ProactiveConfig.NO_RESPONSE_PENALTY,
                    0.1
                )
            
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
                    proactivity_score=ProactiveConfig.BASE_PROACTIVITY,
                    active_hours_json=json.dumps([[9,23]]),
                    interest_tags_json=json.dumps({})
                )
                session.add(profile)
                await session.commit()
                await session.refresh(profile)
            
            return profile
    
    async def _get_active_role(self, user_id: str):
        """
        🎭 获取用户当前激活的角色
        从chat_plugin_advanced的RoleProfile表中查询
        """
        try:
            # 使用原始SQL查询role_profiles表
            async with self.async_session() as session:
                query = text("""
                    SELECT role_name, role_prompt 
                    FROM role_profiles 
                    WHERE user_id = :user_id AND is_active = 1
                    LIMIT 1
                """)
                result = await session.execute(query, {"user_id": user_id})
                row = result.first()
                
                if row:
                    # 创建一个简单的对象来存储角色信息
                    class ActiveRole:
                        def __init__(self, role_name, role_prompt):
                            self.role_name = role_name
                            self.role_prompt = role_prompt
                    
                    return ActiveRole(row[0], row[1])
                
                return None
        except Exception as e:
            logger.warning(f"🎭 获取角色信息失败，将使用正常模式: {e}")
            return None
    
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
                profile.updated_at = datetime.now()
                await session.commit()

# ==================== 全局实例 ====================
proactive_engine = ProactiveChatEngine()

# ==================== NoneBot 集成 ====================
driver = get_driver()

@driver.on_startup
async def start_proactive_engine():
    """Bot启动时初始化主动聊天引擎"""
    await proactive_engine.initialize()
    await proactive_engine.start()
    logger.info("🎉 主动聊天系统已启动！Bot现在会像真人一样主动找人聊天了~")

@driver.on_shutdown
async def stop_proactive_engine():
    """Bot关闭时停止引擎"""
    await proactive_engine.stop()

# 导出给其他插件使用
__all__ = ['proactive_engine', 'ProactiveChatEngine']

