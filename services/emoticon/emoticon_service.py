"""
表情包核心服务 - Service Layer
职责：学习、搜索、管理表情包
代码量：~400 行
"""
from typing import Optional, List, Dict, Tuple
from nonebot.log import logger
from pathlib import Path
import httpx
import hashlib
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, desc, and_, or_, func

# 导入模型
from models.emoticon_models import LearnedEmoticon, EmoticonUsageLog, Base

# 导入配置
from services.emoticon.emoticon_config import EmoticonConfig

# 导入AI客户端
from utils.ai_clients.nvidia_vision_client import get_nvidia_vision_client


class EmoticonService:
    """表情包核心服务"""
    
    def __init__(self):
        self.async_session: Optional[async_sessionmaker[AsyncSession]] = None
        self.storage_path = Path(EmoticonConfig.EMOTICON_STORAGE_PATH)
        self.vision_client = None  # 延迟初始化NVIDIA视觉模型
    
    async def initialize(self, engine=None):
        """初始化表情包系统"""
        # 初始化数据库
        if engine:
            self.async_session = async_sessionmaker(engine, expire_on_commit=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.success("✅ 表情包数据库初始化成功")
        else:
            # 使用默认engine
            default_engine = create_async_engine(EmoticonConfig.DATABASE_URL)
            self.async_session = async_sessionmaker(default_engine, expire_on_commit=False)
            async with default_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.success("✅ 表情包数据库初始化成功（默认引擎）")
        
        # 创建存储目录
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 表情包存储路径: {self.storage_path}")
        
        # 初始化AI客户端（如果启用）
        if EmoticonConfig.USE_VISION_AI:
            try:
                self.vision_client = get_nvidia_vision_client()  # 使用NVIDIA视觉模型
                logger.success("✅ NVIDIA视觉模型客户端初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ NVIDIA视觉模型客户端初始化失败: {e}")
    
    async def learn_emoticon(
        self,
        image_url: str,
        user_id: str,
        group_id: Optional[str] = None,
        context_messages: Optional[List[str]] = None
    ) -> Optional[LearnedEmoticon]:
        """
        学习新表情包
        
        Args:
            image_url: 图片URL
            user_id: 用户ID
            group_id: 群组ID（可选）
            context_messages: 上下文消息列表
        
        Returns:
            学习后的表情包对象
        """
        if not self.async_session:
            logger.error("表情包服务未初始化")
            return None
        
        try:
            # 1. 下载图片
            file_path, file_hash = await self._download_image(image_url)
            if not file_path:
                return None
            
            # 2. 检查是否已存在
            async with self.async_session() as session:
                result = await session.execute(
                    select(LearnedEmoticon).filter_by(file_hash=file_hash)
                )
                existing = result.scalars().first()
                if existing:
                    logger.info(f"表情包已存在: {file_hash[:8]}")
                    return existing
            
            # 3. AI识别（如果启用）
            tags, emotion, scene, description, keywords = await self._analyze_image(
                file_path, context_messages
            )
            
            # 4. 保存到数据库
            emoticon = LearnedEmoticon(
                user_id=user_id,
                group_id=group_id,
                file_path=str(file_path),
                file_hash=file_hash,
                original_url=image_url,
                tags=json.dumps(tags, ensure_ascii=False),
                emotion=emotion,
                scene=scene,
                description=description,
                keywords=json.dumps(keywords, ensure_ascii=False),
                context=json.dumps(context_messages or [], ensure_ascii=False),
                confidence_score=0.7,  # 默认置信度
                quality_score=0.7
            )
            
            async with self.async_session() as session:
                session.add(emoticon)
                await session.commit()
                await session.refresh(emoticon)
            
            logger.success(f"✅ 学习新表情包: {emotion} | {scene}")
            return emoticon
            
        except Exception as e:
            logger.error(f"学习表情包失败: {e}", exc_info=True)
            return None
    
    async def _download_image(self, image_url: str) -> Tuple[Optional[Path], Optional[str]]:
        """下载图片并计算hash"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            
            # 检查大小
            if len(image_data) < EmoticonConfig.MIN_IMAGE_SIZE:
                logger.warning("图片太小，跳过")
                return None, None
            if len(image_data) > EmoticonConfig.MAX_IMAGE_SIZE:
                logger.warning("图片太大，跳过")
                return None, None
            
            # 计算hash
            file_hash = hashlib.sha256(image_data).hexdigest()
            
            # 保存文件
            file_path = self.storage_path / f"{file_hash}.jpg"
            file_path.write_bytes(image_data)
            
            return file_path, file_hash
            
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return None, None
    
    async def _analyze_image(
        self,
        file_path: Path,
        context_messages: Optional[List[str]] = None
    ) -> Tuple[List[str], str, str, str, List[str]]:
        """
        使用AI分析图片
        
        Returns:
            (tags, emotion, scene, description, keywords)
        """
        if not self.vision_client:
            # 如果没有AI，返回默认值
            return (
                ["表情包"],
                "neutral",
                "general",
                "一个表情包",
                ["表情"]
            )
        
        try:
            # 构建上下文
            context_text = ""
            if context_messages:
                context_text = "对话上下文：\n" + "\n".join(context_messages[-5:])
            
            # 调用通义千问-VL分析
            prompt = f"""请分析这张表情包图片，返回JSON格式：
{{
    "tags": ["标签1", "标签2"],
    "emotion": "主要情感(happy/sad/angry/excited等)",
    "scene": "使用场景(简短描述)",
    "description": "表情包描述(一句话)",
    "keywords": ["关键词1", "关键词2"]
}}

{context_text}"""
            
            result = await self.vision_client.analyze_emoticon(str(file_path))
            
            # 解析结果（NVIDIA客户端直接返回字典）
            if result and isinstance(result, dict):
                return (
                    result.get("tags", ["表情包"]),
                    result.get("emotion", "neutral"),
                    result.get("scene", "general"),  
                    result.get("description", "一个表情包"),
                    result.get("keywords", ["表情"])
                )
            elif result:
                logger.warning(f"AI返回格式异常: {type(result)} - {result}")
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
        
        # 返回默认值
        return (
            ["表情包"],
            "neutral",
            "general",
            "一个表情包",
            ["表情"]
        )
    
    async def search_emoticons(
        self,
        query: Optional[str] = None,
        emotion: Optional[str] = None,
        scene: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[LearnedEmoticon]:
        """
        搜索表情包
        
        Args:
            query: 搜索文本
            emotion: 情感筛选
            scene: 场景筛选
            keywords: 关键词筛选
            limit: 返回数量
        
        Returns:
            表情包列表
        """
        if not self.async_session:
            logger.error("表情包服务未初始化")
            return []
        
        try:
            async with self.async_session() as session:
                # 构建查询
                filters = [LearnedEmoticon.is_active == True]
                
                if emotion:
                    filters.append(LearnedEmoticon.emotion == emotion)
                
                if scene:
                    filters.append(LearnedEmoticon.scene.like(f"%{scene}%"))
                
                if query:
                    # 模糊搜索描述、标签、关键词
                    filters.append(
                        or_(
                            LearnedEmoticon.description.like(f"%{query}%"),
                            LearnedEmoticon.tags.like(f"%{query}%"),
                            LearnedEmoticon.keywords.like(f"%{query}%")
                        )
                    )
                
                if keywords:
                    for keyword in keywords:
                        filters.append(LearnedEmoticon.keywords.like(f"%{keyword}%"))
                
                # 执行查询（按质量和使用次数排序）
                result = await session.execute(
                    select(LearnedEmoticon)
                    .filter(and_(*filters))
                    .order_by(
                        desc(LearnedEmoticon.quality_score),
                        desc(LearnedEmoticon.use_count)
                    )
                    .limit(limit)
                )
                
                emoticons = result.scalars().all()
                return list(emoticons)
                
        except Exception as e:
            logger.error(f"搜索表情包失败: {e}", exc_info=True)
            return []
    
    async def record_usage(
        self,
        emoticon_id: int,
        user_id: str,
        group_id: Optional[str] = None,
        trigger_keywords: Optional[List[str]] = None,
        context_emotion: Optional[str] = None,
        match_score: float = 0.5,
        is_successful: bool = True
    ):
        """记录表情包使用"""
        if not self.async_session:
            return
        
        try:
            async with self.async_session() as session:
                # 创建使用记录
                log = EmoticonUsageLog(
                    emoticon_id=emoticon_id,
                    user_id=user_id,
                    group_id=group_id,
                    trigger_keywords=json.dumps(trigger_keywords or [], ensure_ascii=False),
                    context_emotion=context_emotion,
                    match_score=match_score,
                    is_successful=is_successful
                )
                session.add(log)
                
                # 更新表情包统计
                result = await session.execute(
                    select(LearnedEmoticon).filter_by(id=emoticon_id)
                )
                emoticon = result.scalars().first()
                if emoticon:
                    emoticon.use_count += 1
                    emoticon.last_used_at = datetime.now()
                    # 更新成功率
                    if is_successful:
                        emoticon.success_rate = (emoticon.success_rate * (emoticon.use_count - 1) + 1.0) / emoticon.use_count
                    else:
                        emoticon.success_rate = (emoticon.success_rate * (emoticon.use_count - 1)) / emoticon.use_count
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"记录表情包使用失败: {e}")
    
    async def get_emoticon_stats(self) -> Dict:
        """获取表情包统计信息"""
        if not self.async_session:
            return {"total": 0}
        
        try:
            async with self.async_session() as session:
                # 总数
                total_result = await session.execute(
                    select(func.count()).select_from(LearnedEmoticon).filter_by(is_active=True)
                )
                total = total_result.scalar()
                
                # 使用次数
                usage_result = await session.execute(
                    select(func.sum(LearnedEmoticon.use_count)).select_from(LearnedEmoticon)
                )
                total_usage = usage_result.scalar() or 0
                
                # 按情感分类统计
                emotion_result = await session.execute(
                    select(LearnedEmoticon.emotion, func.count())
                    .filter_by(is_active=True)
                    .group_by(LearnedEmoticon.emotion)
                )
                emotions = dict(emotion_result.all())
                
                return {
                    "total": total,
                    "total_usage": total_usage,
                    "by_emotion": emotions
                }
                
        except Exception as e:
            logger.error(f"获取表情包统计失败: {e}")
            return {"total": 0}


# 全局单例
_emoticon_service: Optional[EmoticonService] = None

def get_emoticon_service() -> EmoticonService:
    """获取全局表情包服务实例"""
    global _emoticon_service
    if _emoticon_service is None:
        _emoticon_service = EmoticonService()
    return _emoticon_service




