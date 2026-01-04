"""
主动聊天服务 - Proactive Service
协调决策和内容生成,管理主动聊天流程
"""

from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import json
from nonebot import get_bot
from nonebot.log import logger

from services.proactive.decision_service import get_decision_service
from services.proactive.content_service import get_content_service
from services.emotion import get_emotion_service
from services.database.database_service import get_database_service
from services.proactive.proactive_config import ProactiveConfig
from utils.text.message_splitter import MessageSplitter
from models.proactive_models import ProactiveDecision

# 聊天服务状态标志（延迟导入解决循环导入问题）
CHAT_SERVICE_AVAILABLE = False


class ProactiveService:
    """主动聊天服务 - 总协调器"""
    
    def __init__(self):
        self.decision_service = get_decision_service()
        self.content_service = get_content_service()
        self.emotion_service = get_emotion_service()
        self.db_service = get_database_service()
        self.message_splitter = MessageSplitter()
        self.running = False
    
    async def initialize(self):
        """初始化服务"""
        try:
            # 初始化情感系统
            await self.emotion_service.initialize()
            logger.info("✅ 主动聊天服务初始化完成")
        except Exception as e:
            logger.error(f"主动聊天服务初始化失败: {e}")
            raise
    
    async def start(self):
        """启动主动聊天引擎"""
        self.running = True
        logger.info("✨ 主动聊天引擎已启动")
        
        # 启动主循环
        asyncio.create_task(self._main_loop())
        
        # 启动情感更新循环
        asyncio.create_task(self._emotion_update_loop())
    
    async def stop(self):
        """停止引擎"""
        self.running = False
        logger.info("主动聊天引擎已停止")
    
    async def _main_loop(self):
        """主循环:定期检查是否需要主动聊天"""
        while self.running:
            try:
                await asyncio.sleep(ProactiveConfig.CHECK_INTERVAL_MINUTES * 60)
                await self._check_and_chat()
            except Exception as e:
                logger.error(f"主动聊天主循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _emotion_update_loop(self):
        """情感更新循环"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 每5分钟更新一次
                await self._update_all_emotions()
            except Exception as e:
                logger.error(f"情感更新循环错误: {e}")
    
    async def _update_all_emotions(self):
        """更新所有用户的情感状态"""
        try:
            from models.emotion_models import DynamicEmotionProfile
            from sqlalchemy import select
            
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(DynamicEmotionProfile.user_id)
                )
                user_ids = [row[0] for row in result.all()]
            
            # 更新每个用户的情感
            for user_id in user_ids:
                await self.emotion_service.update_time_based_emotions(user_id)
            
            logger.debug("💝 情感状态更新完成")
        except Exception as e:
            logger.error(f"更新所有用户情感失败: {e}")
    
    async def _check_and_chat(self):
        """
        检查所有用户,决定是否主动聊天
        """
        try:
            logger.debug("🔍 开始检查主动聊天条件")
            # 评估所有用户
            candidates = await self.decision_service.evaluate_all_users()
            
            logger.debug(f"👥 候选用户列表: {candidates}")
            
            if not candidates:
                logger.debug("❌ 没有用户需要主动聊天")
                return
            
            # 选择最佳候选人
            selected = self.decision_service.select_best_candidate(candidates)
            logger.debug(f"🏆 最佳候选人: {selected}")
            
            if not selected:
                logger.debug("❌ 没有合适的候选人")
                return
            
            user_id = selected['user_id']
            logger.info(f"🎯 决定向用户 {user_id} 主动聊天:{selected['reason']}")
            
            # 执行主动聊天
            await self.execute_proactive_chat(
                user_id,
                selected['emotion_state'],
                selected['reason'],
                selected['intimacy_level'],
                selected['priority_score']
            )
            logger.info(f"✅ 用户 {user_id} 主动聊天完成")
            
        except Exception as e:
            logger.error(f"主动聊天决策过程错误: {e}")
    
    async def execute_proactive_chat(
        self,
        user_id: str,
        emotion_state: Dict,
        reason: str = "",
        intimacy_level: float = 0.5,
        priority_score: float = 0.5
    ):
        """
        执行主动聊天
        
        Args:
            user_id: 用户ID
            emotion_state: 情感状态
            reason: 主动聊天的原因
            intimacy_level: 亲密度
            priority_score: 优先级评分
        """
        try:
            logger.debug(f"💬 开始执行用户 {user_id} 的主动聊天, 原因: {reason}")
            
            # 1. 记录决策
            await self._record_decision(
                user_id, reason, emotion_state, intimacy_level, priority_score
            )
            logger.debug(f"📝 已记录决策: 用户ID={user_id}, 优先级={priority_score}")
            
            # 2. 更新情感系统(聊天开始)
            await self.emotion_service.on_chat_start(user_id, "主动聊天触发")
            
            # 3. 生成开场白策略
            _, strategy = await self.content_service.generate_opening(
                user_id, emotion_state, reason
            )
            logger.debug(f"🎯 生成开场白策略: {strategy}")
            
            # 4. 尝试使用普通聊天服务处理主动聊天（延迟导入避免循环依赖）
            chat_response = None
            try:
                from services.chat.chat_service import get_chat_service
                chat_service = get_chat_service()
                logger.info(f"🎯 通过普通聊天服务处理主动聊天: {user_id}")
                
                # 构建情感状态描述
                emotion_description = self._build_emotion_description(emotion_state)
                logger.debug(f"😊 用户情感描述: {emotion_description}")
                
                # 构建AI描述词
                ai_description = f"现在你是主动聊天模式。用户当前情感状态：{emotion_description}。"
                
                # 构建特殊指令
                special_instructions = f"""
                1. 主动发起一个自然的对话，符合当前场景
                2. 开场白要简短、亲切，不要太长
                3. 根据用户的情感状态调整语气和内容
                4. 使用符合角色设定的语言风格
                5. 避免使用系统提示词或明显的模板痕迹
                """
                
                # 使用参数化接口调用聊天服务
                proactive_message = f"[主动聊天]开始对话: {reason}"
                logger.debug(f"🤖 调用参数化聊天接口, 消息: {proactive_message}")
                
                chat_response = await chat_service.process_parameterized_message(
                    user_id=user_id,
                    message=proactive_message,
                    emotion_state=emotion_state,
                    ai_description=ai_description,
                    special_instructions=special_instructions,
                    should_save=True,
                    is_proactive=True  # 标记为主动聊天消息
                )
                
                if chat_response:
                    logger.debug(f"📝 聊天服务响应: {chat_response[:50]}...")
                    logger.info(f"✅ 普通聊天服务生成主动聊天: {chat_response[:50]}")
                    # 添加发送消息逻辑
                    await self._send_message_to_user(user_id, chat_response)
                else:
                    raise Exception("聊天服务返回空响应")
            except Exception as e:
                logger.warning(f"聊天服务处理失败({str(e)}), 使用备用生成方法")
                
                # 备用模式：直接生成并发送消息
                opening_message, _ = await self.content_service.generate_opening(
                    user_id, emotion_state, reason
                )
                logger.debug(f"📝 备用模式生成消息: {opening_message[:50]}...")
                await self._send_message_to_user(user_id, opening_message)
            
            # 5. 更新用户画像
            profile = await self.emotion_service.get_or_create_profile(user_id)
            profile.last_proactive_time = datetime.now()
            
            async with self.db_service.async_session() as session:
                session.add(profile)
                await session.commit()
            logger.debug(f"👤 更新用户 {user_id} 最后主动聊天时间")
            
            # 6. 更新决策记录为已执行
            await self._mark_decision_executed(user_id)
            logger.debug(f"✅ 已标记用户 {user_id} 决策为已执行")
            
            logger.info(f"✅ 已向用户 {user_id} 发送主动消息(集成模式)")
            
        except Exception as e:
            logger.error(f"执行主动聊天失败: {e}")
            
    def _build_emotion_description(self, emotion_state: dict) -> str:
        """
        将情感状态字典转换为自然语言描述
        
        Args:
            emotion_state: 情感状态字典
            
        Returns:
            自然语言情感描述
        """
        descriptions = []
        
        if not emotion_state:
            return "未知"
            
        # 处理各种情感参数
        if 'happiness' in emotion_state:
            happiness = emotion_state['happiness']
            if happiness > 0.7:
                descriptions.append("心情很好")
            elif happiness > 0.4:
                descriptions.append("心情一般")
            else:
                descriptions.append("心情有些低落")
                
        if 'energy' in emotion_state:
            energy = emotion_state['energy']
            if energy > 0.7:
                descriptions.append("充满活力")
            elif energy > 0.4:
                descriptions.append("状态稳定")
            else:
                descriptions.append("有些疲惫")
                
        if 'loneliness' in emotion_state:
            loneliness = emotion_state['loneliness']
            if loneliness > 0.7:
                descriptions.append("感到孤独")
            elif loneliness < 0.3:
                descriptions.append("感到充实")
                
        if 'confidence' in emotion_state:
            confidence = emotion_state['confidence']
            if confidence > 0.7:
                descriptions.append("自信满满")
            elif confidence < 0.3:
                descriptions.append("有些缺乏自信")
                
        return "、".join(descriptions) if descriptions else "情绪稳定"
    
    async def _send_message_to_user(self, user_id: str, message: str):
        """
        分段发送消息到用户
        模拟真人聊天,按标点符号分段发送
        """
        try:
            logger.debug(f"📬 准备发送消息给用户 {user_id}, 消息长度: {len(message)}字符")
            
            # 分段
            segments = self.message_splitter.split_message(message)
            logger.debug(f"📝 消息分段结果: {len(segments)}段")
            
            # 获取Bot实例
            bot = get_bot()
            
            for i, segment in enumerate(segments):
                if i > 0:
                    # 计算打字延迟
                    delay = self.message_splitter.calculate_typing_delay(segment)
                    logger.debug(f"⏱️  第{i+1}段消息延迟: {delay:.2f}秒")
                    await asyncio.sleep(delay)
                
                logger.debug(f"📤 发送第{i+1}/{len(segments)}段消息到用户 {user_id}")
                await bot.send_private_msg(user_id=int(user_id), message=segment)
                logger.debug(f"💬 发送第 {i+1}/{len(segments)} 段:{segment[:30]}")
                
                # 注意：当使用普通聊天服务时，消息已经通过聊天服务的机制发送并记录
                # 这个方法主要用于备用模式下的消息发送
                
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def _record_decision(
        self,
        user_id: str,
        reason: str,
        emotion_state: Dict,
        intimacy_level: float,
        priority_score: float
    ):
        """记录主动聊天决策"""
        try:
            # 将情感状态合并到决策原因中
            decision_data = {
                'reason': reason,
                'emotion_state': emotion_state,
                'intimacy_level': intimacy_level,
                'priority_score': priority_score
            }
            
            async with self.db_service.async_session() as session:
                decision = ProactiveDecision(
                    user_id=user_id,
                    decision_score=priority_score,
                    decision_reason=json.dumps(decision_data, ensure_ascii=False),
                    should_proactive=True,
                    executed=False
                )
                session.add(decision)
                await session.commit()
        except Exception as e:
            logger.error(f"记录决策失败: {e}")
    
    async def _mark_decision_executed(self, user_id: str):
        """标记决策为已执行"""
        try:
            from sqlalchemy import select, desc
            
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(ProactiveDecision)
                    .where(ProactiveDecision.user_id == user_id)
                    .where(ProactiveDecision.executed == False)
                    .order_by(desc(ProactiveDecision.created_at))
                    .limit(1)
                )
                decision = result.scalar_one_or_none()
                
                if decision:
                    decision.executed = True
                    decision.execution_time = datetime.now()
                    await session.commit()
        except Exception as e:
            logger.error(f"标记决策执行失败: {e}")
    
    async def record_user_response(
        self,
        user_id: str,
        response_text: str,
        continued: bool = False
    ):
        """
        记录用户响应(用于情感系统更新)
        
        Args:
            user_id: 用户ID
            response_text: 响应文本
            continued: 是否继续对话
        """
        try:
            # 更新情感系统
            if continued:
                await self.emotion_service.on_chat_response(user_id, "good")
            else:
                await self.emotion_service.on_chat_response(user_id, "neutral")
            
            # 更新决策记录
            from sqlalchemy import select, desc
            
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(ProactiveDecision)
                    .where(ProactiveDecision.user_id == user_id)
                    .where(ProactiveDecision.executed == True)
                    .order_by(desc(ProactiveDecision.execution_time))
                    .limit(1)
                )
                decision = result.scalar_one_or_none()
                
                if decision:
                    decision.success = True
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"记录用户响应失败: {e}")
    
    async def record_no_response(self, user_id: str):
        """记录用户无响应"""
        try:
            # 更新情感系统
            await self.emotion_service.on_no_response(user_id)
            
            # 更新决策记录
            from sqlalchemy import select, desc
            
            async with self.db_service.async_session() as session:
                result = await session.execute(
                    select(ProactiveDecision)
                    .where(ProactiveDecision.user_id == user_id)
                    .where(ProactiveDecision.executed == True)
                    .order_by(desc(ProactiveDecision.execution_time))
                    .limit(1)
                )
                decision = result.scalar_one_or_none()
                
                if decision:
                    decision.success = False
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"记录无响应失败: {e}")
    
    async def update_user_activity(self, user_id: str, user_message: str = ""):
        """更新用户活跃时间"""
        try:
            # 更新情感系统(包含消息情感分析)
            await self.emotion_service.on_chat_start(user_id, user_message)
        except Exception as e:
            logger.error(f"更新用户活跃时间失败: {e}")


# ==================== 全局单例 ====================
_proactive_service: Optional[ProactiveService] = None

def get_proactive_service() -> ProactiveService:
    """获取主动聊天服务单例"""
    global _proactive_service
    if _proactive_service is None:
        _proactive_service = ProactiveService()
    return _proactive_service

