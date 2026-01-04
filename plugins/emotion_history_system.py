"""
情感历史数据系统 - Emotion History System
专门存储和管理情感参数的历史数据，用于绘制变化曲线
"""

from nonebot.log import logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, desc, and_, or_, func, text

# ==================== 配置 ====================
class EmotionHistoryConfig:
    """情感历史系统配置"""
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    
    # 记录频率配置
    RECORD_INTERVAL_MINUTES = 10  # 每10分钟记录一次
    BATCH_SIZE = 100  # 批量处理大小
    
    # 数据保留策略
    KEEP_DAILY_RECORDS_DAYS = 30  # 保留30天的详细记录
    KEEP_HOURLY_RECORDS_DAYS = 90  # 保留90天的小时记录
    KEEP_DAILY_SUMMARY_DAYS = 365  # 保留365天的日汇总
    
    # 自动清理配置
    MAX_DETAILED_RECORDS = 1000  # 详细记录最大条数，超过自动清理
    MAX_HOURLY_RECORDS = 500  # 小时汇总最大条数
    MAX_DAILY_RECORDS = 100  # 日汇总最大条数
    
    # 汇总配置
    DAILY_SUMMARY_HOUR = 23  # 每日汇总时间（23点）
    HOURLY_SUMMARY_MINUTE = 0  # 每小时汇总时间（0分）

# ==================== 数据库模型 ====================
Base = declarative_base()

class EmotionHistoryRecord(Base):
    """情感历史记录表（详细记录）"""
    __tablename__ = 'emotion_history_records'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    recorded_at = Column(DateTime, index=True)
    
    # 情感参数
    happiness = Column(Float)
    loneliness = Column(Float)
    energy = Column(Float)
    confidence = Column(Float)
    charm = Column(Float)
    intelligence = Column(Float)
    creativity = Column(Float)
    empathy = Column(Float)
    stress_level = Column(Float)
    social_need = Column(Float)
    intimacy_level = Column(Float)
    mood = Column(String(20))
    
    # 索引
    __table_args__ = (
        Index('idx_user_time', 'user_id', 'recorded_at'),
        Index('idx_recorded_at', 'recorded_at'),
    )

class EmotionHourlySummary(Base):
    """情感小时汇总表"""
    __tablename__ = 'emotion_hourly_summary'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    hour_start = Column(DateTime, index=True)  # 小时开始时间
    
    # 平均值
    avg_happiness = Column(Float)
    avg_loneliness = Column(Float)
    avg_energy = Column(Float)
    avg_confidence = Column(Float)
    avg_charm = Column(Float)
    avg_intelligence = Column(Float)
    avg_creativity = Column(Float)
    avg_empathy = Column(Float)
    avg_stress_level = Column(Float)
    avg_social_need = Column(Float)
    avg_intimacy_level = Column(Float)
    
    # 极值
    max_happiness = Column(Float)
    min_happiness = Column(Float)
    max_loneliness = Column(Float)
    min_loneliness = Column(Float)
    max_energy = Column(Float)
    min_energy = Column(Float)
    
    # 统计
    record_count = Column(Integer)  # 记录数量
    mood_distribution = Column(Text)  # 心情分布JSON
    
    # 索引
    __table_args__ = (
        Index('idx_user_hour', 'user_id', 'hour_start'),
        Index('idx_hour_start', 'hour_start'),
    )

class EmotionDailySummary(Base):
    """情感日汇总表"""
    __tablename__ = 'emotion_daily_summary'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    date = Column(DateTime, index=True)  # 日期
    
    # 平均值
    avg_happiness = Column(Float)
    avg_loneliness = Column(Float)
    avg_energy = Column(Float)
    avg_confidence = Column(Float)
    avg_charm = Column(Float)
    avg_intelligence = Column(Float)
    avg_creativity = Column(Float)
    avg_empathy = Column(Float)
    avg_stress_level = Column(Float)
    avg_social_need = Column(Float)
    avg_intimacy_level = Column(Float)
    
    # 极值
    max_happiness = Column(Float)
    min_happiness = Column(Float)
    max_loneliness = Column(Float)
    min_loneliness = Column(Float)
    max_energy = Column(Float)
    min_energy = Column(Float)
    
    # 统计
    record_count = Column(Integer)
    chat_count = Column(Integer)  # 聊天次数
    proactive_count = Column(Integer)  # 主动聊天次数
    mood_distribution = Column(Text)  # 心情分布JSON
    
    # 索引
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'date'),
        Index('idx_date', 'date'),
    )

# ==================== 情感历史系统核心 ====================
class EmotionHistorySystem:
    """情感历史系统核心类"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.running = False
        
    async def initialize(self):
        """初始化情感历史系统"""
        self.engine = create_async_engine(
            EmotionHistoryConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("📊 情感历史系统初始化完成")
    
    async def start(self):
        """启动历史记录系统"""
        self.running = True
        logger.info("📈 情感历史记录系统已启动")
        
        # 启动记录循环
        asyncio.create_task(self._record_loop())
        
        # 启动清理循环
        asyncio.create_task(self._cleanup_loop())
        
        # 启动汇总循环
        asyncio.create_task(self._summary_loop())
    
    async def stop(self):
        """停止系统"""
        self.running = False
        logger.info("情感历史记录系统已停止")
    
    async def _record_loop(self):
        """记录循环：每10秒记录一次情感数据"""
        while self.running:
            try:
                await asyncio.sleep(10)  # 每10秒记录一次
                await self._record_all_users_emotions()
            except Exception as e:
                logger.error(f"情感历史记录循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _record_all_users_emotions(self):
        """记录所有用户的情感数据"""
        try:
            # 导入动态情感系统（新架构）
            from services.emotion import get_emotion_service
            from models.emotion_models import DynamicEmotionProfile
            
            emotion_service = get_emotion_service()
            
            # 获取所有用户
            async with self.async_session() as session:
                result = await session.execute(
                    select(DynamicEmotionProfile.user_id)
                )
                user_ids = [row[0] for row in result.all()]
            
            # 记录每个用户的情感数据
            for user_id in user_ids:
                await self._record_user_emotion(user_id)
            
            # 检查并清理超量数据
            await self._cleanup_excess_records()
            
            logger.debug(f"📊 已记录 {len(user_ids)} 个用户的情感历史数据")
            
        except Exception as e:
            logger.error(f"记录用户情感数据失败: {e}")
    
    async def _record_user_emotion(self, user_id: str):
        """记录单个用户的情感数据"""
        try:
            # 导入动态情感系统（新架构）
            from services.emotion import get_emotion_service
            
            emotion_service = get_emotion_service()
            
            # 获取用户当前情感状态
            profile = await emotion_service.get_or_create_profile(user_id)
            
            # 创建历史记录
            record = EmotionHistoryRecord(
                user_id=user_id,
                recorded_at=datetime.now(),
                happiness=profile.happiness,
                loneliness=profile.loneliness,
                energy=profile.energy,
                confidence=profile.confidence,
                charm=profile.charm,
                intelligence=profile.intelligence,
                creativity=profile.creativity,
                empathy=profile.empathy,
                stress_level=profile.stress_level,
                social_need=profile.social_need,
                intimacy_level=profile.intimacy_level,
                mood=profile.mood
            )
            
            # 保存记录
            async with self.async_session() as session:
                session.add(record)
                await session.commit()
            
        except Exception as e:
            logger.error(f"记录用户 {user_id} 情感数据失败: {e}")
    
    async def _cleanup_excess_records(self):
        """清理超量数据"""
        from sqlalchemy import text
        try:
            async with self.async_session() as session:
                # 清理详细记录
                result = await session.execute(
                    select(func.count(EmotionHistoryRecord.id))
                )
                detailed_count = result.scalar()
                
                if detailed_count > EmotionHistoryConfig.MAX_DETAILED_RECORDS:
                    # 删除最旧的记录
                    excess_count = detailed_count - EmotionHistoryConfig.MAX_DETAILED_RECORDS
                    await session.execute(
                        text(f"""
                        DELETE FROM emotion_history_records 
                        WHERE id IN (
                            SELECT id FROM emotion_history_records 
                            ORDER BY recorded_at ASC 
                            LIMIT {excess_count}
                        )
                        """)
                    )
                    logger.info(f"🗑️ 清理了 {excess_count} 条超量详细记录")
                
                # 清理小时汇总
                result = await session.execute(
                    select(func.count(EmotionHourlySummary.id))
                )
                hourly_count = result.scalar()
                
                if hourly_count > EmotionHistoryConfig.MAX_HOURLY_RECORDS:
                    excess_count = hourly_count - EmotionHistoryConfig.MAX_HOURLY_RECORDS
                    await session.execute(
                        text(f"""
                        DELETE FROM emotion_hourly_summary 
                        WHERE id IN (
                            SELECT id FROM emotion_hourly_summary 
                            ORDER BY hour_start ASC 
                            LIMIT {excess_count}
                        )
                        """)
                    )
                    logger.info(f"🗑️ 清理了 {excess_count} 条超量小时汇总")
                
                # 清理日汇总
                result = await session.execute(
                    select(func.count(EmotionDailySummary.id))
                )
                daily_count = result.scalar()
                
                if daily_count > EmotionHistoryConfig.MAX_DAILY_RECORDS:
                    excess_count = daily_count - EmotionHistoryConfig.MAX_DAILY_RECORDS
                    await session.execute(
                        text(f"""
                        DELETE FROM emotion_daily_summary 
                        WHERE id IN (
                            SELECT id FROM emotion_daily_summary 
                            ORDER BY date ASC 
                            LIMIT {excess_count}
                        )
                        """)
                    )
                    logger.info(f"🗑️ 清理了 {excess_count} 条超量日汇总")
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"清理超量数据失败: {e}")
    
    async def _cleanup_loop(self):
        """清理循环：定期清理过期数据"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                await self._cleanup_old_data()
            except Exception as e:
                logger.error(f"数据清理循环错误: {e}")
    
    async def _cleanup_old_data(self):
        """清理过期数据"""
        try:
            now = datetime.now()
            
            # 清理30天前的详细记录
            cutoff_detailed = now - timedelta(days=EmotionHistoryConfig.KEEP_DAILY_RECORDS_DAYS)
            async with self.async_session() as session:
                result = await session.execute(
                    select(EmotionHistoryRecord)
                    .where(EmotionHistoryRecord.recorded_at < cutoff_detailed)
                )
                old_records = result.scalars().all()
                
                for record in old_records:
                    await session.delete(record)
                
                await session.commit()
                logger.info(f"🗑️ 清理了 {len(old_records)} 条过期详细记录")
            
            # 清理90天前的小时汇总
            cutoff_hourly = now - timedelta(days=EmotionHistoryConfig.KEEP_HOURLY_RECORDS_DAYS)
            async with self.async_session() as session:
                result = await session.execute(
                    select(EmotionHourlySummary)
                    .where(EmotionHourlySummary.hour_start < cutoff_hourly)
                )
                old_hourly = result.scalars().all()
                
                for record in old_hourly:
                    await session.delete(record)
                
                await session.commit()
                logger.info(f"🗑️ 清理了 {len(old_hourly)} 条过期小时汇总")
            
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
    
    async def _summary_loop(self):
        """汇总循环：定期生成汇总数据"""
        while self.running:
            try:
                # 每小时生成小时汇总
                await asyncio.sleep(3600)
                await self._generate_hourly_summary()
                
                # 每天23点生成日汇总
                now = datetime.now()
                if now.hour == EmotionHistoryConfig.DAILY_SUMMARY_HOUR:
                    await self._generate_daily_summary()
                    
            except Exception as e:
                logger.error(f"汇总循环错误: {e}")
    
    async def _generate_hourly_summary(self):
        """生成小时汇总"""
        try:
            now = datetime.now()
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            # 获取所有用户
            async with self.async_session() as session:
                result = await session.execute(
                    select(EmotionHistoryRecord.user_id)
                    .where(EmotionHistoryRecord.recorded_at >= hour_start)
                    .where(EmotionHistoryRecord.recorded_at < hour_end)
                    .distinct()
                )
                user_ids = [row[0] for row in result.all()]
            
            # 为每个用户生成小时汇总
            for user_id in user_ids:
                await self._create_hourly_summary(user_id, hour_start)
                
        except Exception as e:
            logger.error(f"生成小时汇总失败: {e}")
    
    async def _create_hourly_summary(self, user_id: str, hour_start: datetime):
        """创建单个用户的小时汇总"""
        try:
            hour_end = hour_start + timedelta(hours=1)
            
            async with self.async_session() as session:
                # 获取该小时的所有记录
                result = await session.execute(
                    select(EmotionHistoryRecord)
                    .where(EmotionHistoryRecord.user_id == user_id)
                    .where(EmotionHistoryRecord.recorded_at >= hour_start)
                    .where(EmotionHistoryRecord.recorded_at < hour_end)
                )
                records = result.scalars().all()
                
                if not records:
                    return
                
                # 计算统计数据
                emotions = ['happiness', 'loneliness', 'energy', 'confidence', 'charm', 
                          'intelligence', 'creativity', 'empathy', 'stress_level', 
                          'social_need', 'intimacy_level']
                
                summary_data = {}
                for emotion in emotions:
                    values = [getattr(record, emotion) for record in records if getattr(record, emotion) is not None]
                    if values:
                        summary_data[f'avg_{emotion}'] = sum(values) / len(values)
                        summary_data[f'max_{emotion}'] = max(values)
                        summary_data[f'min_{emotion}'] = min(values)
                
                # 计算心情分布
                mood_counts = {}
                for record in records:
                    mood = record.mood or 'unknown'
                    mood_counts[mood] = mood_counts.get(mood, 0) + 1
                
                # 创建汇总记录
                summary = EmotionHourlySummary(
                    user_id=user_id,
                    hour_start=hour_start,
                    record_count=len(records),
                    mood_distribution=json.dumps(mood_counts),
                    **summary_data
                )
                
                session.add(summary)
                await session.commit()
                
        except Exception as e:
            logger.error(f"创建用户 {user_id} 小时汇总失败: {e}")
    
    async def _generate_daily_summary(self):
        """生成日汇总"""
        try:
            now = datetime.now()
            date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 获取所有用户
            async with self.async_session() as session:
                result = await session.execute(
                    select(EmotionHistoryRecord.user_id)
                    .where(EmotionHistoryRecord.recorded_at >= date)
                    .where(EmotionHistoryRecord.recorded_at < date + timedelta(days=1))
                    .distinct()
                )
                user_ids = [row[0] for row in result.all()]
            
            # 为每个用户生成日汇总
            for user_id in user_ids:
                await self._create_daily_summary(user_id, date)
                
        except Exception as e:
            logger.error(f"生成日汇总失败: {e}")
    
    async def _create_daily_summary(self, user_id: str, date: datetime):
        """创建单个用户的日汇总"""
        try:
            next_date = date + timedelta(days=1)
            
            async with self.async_session() as session:
                # 获取该日的所有记录
                result = await session.execute(
                    select(EmotionHistoryRecord)
                    .where(EmotionHistoryRecord.user_id == user_id)
                    .where(EmotionHistoryRecord.recorded_at >= date)
                    .where(EmotionHistoryRecord.recorded_at < next_date)
                )
                records = result.scalars().all()
                
                if not records:
                    return
                
                # 计算统计数据
                emotions = ['happiness', 'loneliness', 'energy', 'confidence', 'charm', 
                          'intelligence', 'creativity', 'empathy', 'stress_level', 
                          'social_need', 'intimacy_level']
                
                summary_data = {}
                for emotion in emotions:
                    values = [getattr(record, emotion) for record in records if getattr(record, emotion) is not None]
                    if values:
                        summary_data[f'avg_{emotion}'] = sum(values) / len(values)
                        summary_data[f'max_{emotion}'] = max(values)
                        summary_data[f'min_{emotion}'] = min(values)
                
                # 计算心情分布
                mood_counts = {}
                for record in records:
                    mood = record.mood or 'unknown'
                    mood_counts[mood] = mood_counts.get(mood, 0) + 1
                
                # 统计聊天次数（这里需要从其他表获取，暂时设为0）
                chat_count = 0
                proactive_count = 0
                
                # 创建汇总记录
                summary = EmotionDailySummary(
                    user_id=user_id,
                    date=date,
                    record_count=len(records),
                    chat_count=chat_count,
                    proactive_count=proactive_count,
                    mood_distribution=json.dumps(mood_counts),
                    **summary_data
                )
                
                session.add(summary)
                await session.commit()
                
        except Exception as e:
            logger.error(f"创建用户 {user_id} 日汇总失败: {e}")
    
    async def get_emotion_history(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime,
        granularity: str = 'detailed'
    ) -> List[Dict]:
        """获取情感历史数据"""
        try:
            async with self.async_session() as session:
                if granularity == 'detailed':
                    # 获取详细记录
                    result = await session.execute(
                        select(EmotionHistoryRecord)
                        .where(EmotionHistoryRecord.user_id == user_id)
                        .where(EmotionHistoryRecord.recorded_at >= start_time)
                        .where(EmotionHistoryRecord.recorded_at <= end_time)
                        .order_by(EmotionHistoryRecord.recorded_at)
                    )
                    records = result.scalars().all()
                    
                    return [{
                        'timestamp': record.recorded_at.isoformat(),
                        'happiness': record.happiness,
                        'loneliness': record.loneliness,
                        'energy': record.energy,
                        'confidence': record.confidence,
                        'charm': record.charm,
                        'intelligence': record.intelligence,
                        'creativity': record.creativity,
                        'empathy': record.empathy,
                        'stress_level': record.stress_level,
                        'social_need': record.social_need,
                        'intimacy_level': record.intimacy_level,
                        'mood': record.mood
                    } for record in records]
                
                elif granularity == 'hourly':
                    # 获取小时汇总
                    result = await session.execute(
                        select(EmotionHourlySummary)
                        .where(EmotionHourlySummary.user_id == user_id)
                        .where(EmotionHourlySummary.hour_start >= start_time)
                        .where(EmotionHourlySummary.hour_start <= end_time)
                        .order_by(EmotionHourlySummary.hour_start)
                    )
                    records = result.scalars().all()
                    
                    return [{
                        'timestamp': record.hour_start.isoformat(),
                        'happiness': record.avg_happiness,
                        'loneliness': record.avg_loneliness,
                        'energy': record.avg_energy,
                        'confidence': record.avg_confidence,
                        'charm': record.avg_charm,
                        'intelligence': record.avg_intelligence,
                        'creativity': record.avg_creativity,
                        'empathy': record.avg_empathy,
                        'stress_level': record.avg_stress_level,
                        'social_need': record.avg_social_need,
                        'intimacy_level': record.avg_intimacy_level,
                        'record_count': record.record_count
                    } for record in records]
                
                elif granularity == 'daily':
                    # 获取日汇总
                    result = await session.execute(
                        select(EmotionDailySummary)
                        .where(EmotionDailySummary.user_id == user_id)
                        .where(EmotionDailySummary.date >= start_time)
                        .where(EmotionDailySummary.date <= end_time)
                        .order_by(EmotionDailySummary.date)
                    )
                    records = result.scalars().all()
                    
                    return [{
                        'timestamp': record.date.isoformat(),
                        'happiness': record.avg_happiness,
                        'loneliness': record.avg_loneliness,
                        'energy': record.avg_energy,
                        'confidence': record.avg_confidence,
                        'charm': record.avg_charm,
                        'intelligence': record.avg_intelligence,
                        'creativity': record.avg_creativity,
                        'empathy': record.avg_empathy,
                        'stress_level': record.avg_stress_level,
                        'social_need': record.avg_social_need,
                        'intimacy_level': record.avg_intimacy_level,
                        'record_count': record.record_count,
                        'chat_count': record.chat_count,
                        'proactive_count': record.proactive_count
                    } for record in records]
                
        except Exception as e:
            logger.error(f"获取情感历史数据失败: {e}")
            return []
    
    async def get_available_periods(self, user_id: str) -> Dict[str, Tuple[datetime, datetime]]:
        """获取可用的时间段"""
        try:
            async with self.async_session() as session:
                # 获取详细记录的时间范围
                result = await session.execute(
                    select(
                        func.min(EmotionHistoryRecord.recorded_at).label('min_time'),
                        func.max(EmotionHistoryRecord.recorded_at).label('max_time')
                    )
                    .where(EmotionHistoryRecord.user_id == user_id)
                )
                detailed_range = result.first()
                
                # 获取小时汇总的时间范围
                result = await session.execute(
                    select(
                        func.min(EmotionHourlySummary.hour_start).label('min_time'),
                        func.max(EmotionHourlySummary.hour_start).label('max_time')
                    )
                    .where(EmotionHourlySummary.user_id == user_id)
                )
                hourly_range = result.first()
                
                # 获取日汇总的时间范围
                result = await session.execute(
                    select(
                        func.min(EmotionDailySummary.date).label('min_time'),
                        func.max(EmotionDailySummary.date).label('max_time')
                    )
                    .where(EmotionDailySummary.user_id == user_id)
                )
                daily_range = result.first()
                
                return {
                    'detailed': (detailed_range.min_time, detailed_range.max_time) if detailed_range.min_time else None,
                    'hourly': (hourly_range.min_time, hourly_range.max_time) if hourly_range.min_time else None,
                    'daily': (daily_range.min_time, daily_range.max_time) if daily_range.min_time else None
                }
                
        except Exception as e:
            logger.error(f"获取可用时间段失败: {e}")
            return {}

# ==================== 全局实例 ====================
emotion_history_system = EmotionHistorySystem()

# ==================== NoneBot 集成 ====================
from nonebot import get_driver

driver = get_driver()

@driver.on_startup
async def start_emotion_history_system():
    """Bot启动时初始化情感历史系统"""
    await emotion_history_system.initialize()
    await emotion_history_system.start()
    logger.info("📊 情感历史记录系统已启动！开始记录情感变化历史")

@driver.on_shutdown
async def stop_emotion_history_system():
    """Bot关闭时停止系统"""
    await emotion_history_system.stop()

# 导出
__all__ = ['emotion_history_system', 'EmotionHistorySystem', 'EmotionHistoryConfig']
