"""
AI表情包学习系统 - 第三步实现
自动学习群聊/私聊中的表情包，智能打标签并择机使用

功能：
1. 监听并识别图片消息中的表情包
2. 提取上下文，分析使用场景
3. 使用AI自动打标签（情感、主题、关键词）
4. 存储表情包和元数据
5. 智能匹配，择机使用学习到的表情包
"""

from nonebot import on_message, get_driver
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Message
from nonebot.log import logger
from nonebot.rule import to_me
from typing import Dict, List, Optional, Tuple
import httpx
import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
import asyncio
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, desc, and_, or_, func

# 导入通义千问SDK（延迟导入）
DASHSCOPE_AVAILABLE = False

# ==================== 配置 ====================
class LearnerConfig:
    """学习器配置"""
    # AI配置 - 通义千问-VL（支持图像识别）
    API_KEY = "sk-105724d3e4bb4f6ea354426dbecf3137"
    MODEL = "qwen-vl-max"  # 通义千问视觉模型
    USE_VISION = True  # 启用图像识别
    
    # 存储配置
    DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"
    EMOTICON_STORAGE_PATH = "./emoticons/"  # 表情包存储路径
    
    # 学习配置
    ENABLE_LEARNING = True  # 是否启用学习
    MIN_CONTEXT_LENGTH = 1  # 最小上下文长度（改为1条，方便测试）
    MAX_CONTEXT_MESSAGES = 10  # 上下文消息数量
    
    # 识别配置
    MIN_IMAGE_SIZE = 1024  # 最小图片大小（字节），过滤太小的图
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 最大5MB
    
    # 使用配置
    LEARNED_EMOTICON_PROBABILITY = 0.15  # 使用学习表情的概率（15%）
    MIN_USE_SCORE = 0.6  # 最低使用评分

# ==================== 数据库模型 ====================
Base = declarative_base()

class LearnedEmoticon(Base):
    """学习到的表情包"""
    __tablename__ = 'learned_emoticons'
    
    id = Column(Integer, primary_key=True)
    
    # 基础信息
    file_hash = Column(String(64), unique=True, index=True)  # 文件hash，去重
    file_path = Column(String(500))  # 存储路径
    file_size = Column(Integer)  # 文件大小
    
    # 学习信息
    source_user_id = Column(String(50))  # 来源用户
    source_group_id = Column(String(50), nullable=True)  # 来源群（如果有）
    learned_at = Column(DateTime, default=datetime.now)
    
    # AI分析结果
    emotion_tags = Column(Text)  # JSON格式的情感标签 ["happy", "funny", ...]
    scene_tags = Column(Text)  # JSON格式的场景标签 ["greeting", "goodbye", ...]
    keywords = Column(Text)  # JSON格式的关键词 ["你好", "再见", ...]
    ocr_text = Column(Text, nullable=True)  # OCR提取的文字（如果有）
    
    # 上下文信息
    context_before = Column(Text)  # 发送前的对话
    context_after = Column(Text, nullable=True)  # 发送后的反应
    
    # 使用统计
    use_count = Column(Integer, default=0)  # 使用次数
    success_count = Column(Integer, default=0)  # 成功次数（有正面反应）
    quality_score = Column(Float, default=0.5)  # 质量评分（0-1）
    
    # 其他
    is_active = Column(Boolean, default=True)  # 是否激活
    description = Column(Text, nullable=True)  # AI生成的描述

class EmoticonUsageLog(Base):
    """表情包使用日志"""
    __tablename__ = 'emoticon_usage_logs'
    
    id = Column(Integer, primary_key=True)
    emoticon_id = Column(Integer, index=True)  # 关联的表情包ID
    user_id = Column(String(50))
    
    used_at = Column(DateTime, default=datetime.now)
    context = Column(Text)  # 使用时的上下文
    user_reaction = Column(Text, nullable=True)  # 用户反应
    
    success = Column(Boolean, default=False)  # 是否成功
    feedback_score = Column(Float, nullable=True)  # 反馈评分

# ==================== AI表情包学习器 ====================
class EmoticonLearner:
    """AI表情包学习器核心类"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self.storage_path = Path(LearnerConfig.EMOTICON_STORAGE_PATH)
        self.context_buffer = {}  # 临时存储上下文
        
    async def initialize(self):
        """初始化学习器"""
        # 创建存储目录
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self.engine = create_async_engine(
            LearnerConfig.DATABASE_URL,
            echo=False
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # 检查DashScope状态（延迟导入）
        global DASHSCOPE_AVAILABLE
        try:
            import dashscope
            from dashscope import MultiModalConversation
            DASHSCOPE_AVAILABLE = True
            logger.info("🎨 通义千问-VL图像识别已启用")
            logger.info("✅ API Key已配置，图像识别功能就绪")
        except ImportError as e:
            DASHSCOPE_AVAILABLE = False
            logger.warning(f"⚠️ 图像识别不可用: {e}")
        except Exception as e:
            DASHSCOPE_AVAILABLE = False
            logger.warning(f"⚠️ 图像识别初始化失败: {e}")
        
        logger.info("🎓 AI表情包学习器初始化完成")
    
    async def process_image_message(
        self, 
        event: MessageEvent,
        image_url: str,
        context_messages: List[str]
    ) -> bool:
        """
        处理图片消息，判断是否为表情包并学习
        
        Args:
            event: 消息事件
            image_url: 图片URL
            context_messages: 上下文消息列表
        
        Returns:
            是否成功学习
        """
        try:
            # 1. 下载图片
            image_data = await self._download_image(image_url)
            if not image_data:
                return False
            
            # 2. 检查图片大小
            if len(image_data) < LearnerConfig.MIN_IMAGE_SIZE:
                logger.debug("图片太小，可能不是表情包")
                return False
            
            if len(image_data) > LearnerConfig.MAX_IMAGE_SIZE:
                logger.debug("图片太大，跳过")
                return False
            
            # 3. 计算hash，检查是否已存在
            file_hash = self._calculate_hash(image_data)
            
            async with self.async_session() as session:
                result = await session.execute(
                    select(LearnedEmoticon).where(LearnedEmoticon.file_hash == file_hash)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.debug(f"表情包已存在: {file_hash[:8]}")
                    # 更新上下文信息（丰富数据）
                    await self._update_context(existing, context_messages)
                    return False
            
            # 4. 保存图片文件
            file_path = await self._save_image(image_data, file_hash)
            
            # 5. AI分析表情包
            analysis = await self._analyze_emoticon_with_ai(
                image_data=image_data,
                context=context_messages,
                file_hash=file_hash
            )
            
            if not analysis:
                logger.warning("AI分析失败")
                return False
            
            # 6. 保存到数据库
            await self._save_learned_emoticon(
                file_hash=file_hash,
                file_path=str(file_path),
                file_size=len(image_data),
                source_user_id=str(event.user_id),
                source_group_id=str(getattr(event, 'group_id', None)),
                context=context_messages,
                analysis=analysis
            )
            
            logger.info(f"🎓 成功学习表情包: {analysis.get('description', 'unknown')[:30]}")
            return True
            
        except Exception as e:
            logger.exception(f"处理图片消息失败: {e}")
            return False
    
    async def _download_image(self, url: str) -> Optional[bytes]:
        """下载图片"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
        return None
    
    def _calculate_hash(self, data: bytes) -> str:
        """计算文件hash"""
        return hashlib.sha256(data).hexdigest()
    
    async def _save_image(self, data: bytes, file_hash: str) -> Path:
        """保存图片文件"""
        # 按hash前两位分子目录（避免单目录文件过多）
        subdir = self.storage_path / file_hash[:2]
        subdir.mkdir(parents=True, exist_ok=True)
        
        file_path = subdir / f"{file_hash}.jpg"
        
        # 异步写入
        await asyncio.to_thread(file_path.write_bytes, data)
        
        return file_path
    
    async def _analyze_emoticon_with_ai(
        self,
        image_data: bytes,
        context: List[str],
        file_hash: str
    ) -> Optional[Dict]:
        """
        使用通义千问-VL分析表情包（支持图像识别）
        
        Returns:
            {
                "emotion_tags": ["happy", "funny"],
                "scene_tags": ["greeting", "chat"],
                "keywords": ["你好", "开心"],
                "description": "一个开心的问候表情包",
                "ocr_text": "你好呀"  # 如果有文字
            }
        """
        try:
            # 检查DashScope是否可用
            if not DASHSCOPE_AVAILABLE:
                logger.warning("DashScope不可用，使用备用分析")
                return self._get_fallback_analysis(context)
            
            # 导入DashScope（确保在方法作用域内可用）
            import dashscope
            from dashscope import MultiModalConversation
            
            # 设置API Key
            dashscope.api_key = LearnerConfig.API_KEY
            
            # 构建上下文
            context_text = "\n".join(context[-5:]) if context else "无上下文"
            
            # 将图片数据转换为base64
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_base64}"
            
            # 构建多模态消息
            messages = [{
                'role': 'user',
                'content': [
                    # 1. 发送图片
                    {'image': image_url},
                    
                    # 2. 发送分析要求
                    {'text': f"""请分析这个表情包图片。

【对话上下文】
{context_text}

【分析要求】
1. 情感标签（英文）：happy, sad, funny, angry, excited, thinking, agree, laugh, cry, surprise, love, thanks, bye, greeting等
2. 使用场景（英文）：greeting, goodbye, thanks, congratulation, comfort, chat, joke, celebration等
3. 关键词（中文）：这个表情包适合在什么时候使用，3-5个关键词
4. OCR文字：如果图片上有文字，请提取出来
5. 简短描述（中文）：一句话描述这个表情包的内容和用途

【输出格式】
严格按JSON格式输出：
{{
  "emotion_tags": ["标签1", "标签2"],
  "scene_tags": ["场景1", "场景2"],
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "ocr_text": "提取的文字（如果没有则为空字符串）",
  "description": "描述文字"
}}

注意：
- 情感标签用英文（与系统统一）
- 关键词用中文
- 仔细观察图片内容，不要仅凭上下文猜测
- 如果图片上有文字，一定要提取出来
"""}
                ]
            }]
            
            # 调用通义千问-VL
            response = MultiModalConversation.call(
                model=LearnerConfig.MODEL,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            if response.status_code == 200:
                # 提取AI输出
                ai_output = response.output.choices[0].message.content[0]['text']
                logger.debug(f"通义千问-VL原始输出: {ai_output}")
                
                # 提取JSON
                import re
                json_match = re.search(r'\{.*\}', ai_output, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                    logger.info(f"🎨 图像识别分析成功: {analysis.get('description', 'unknown')[:30]}")
                    return analysis
                else:
                    logger.warning("通义千问输出不是有效JSON，使用备用分析")
                    return self._get_fallback_analysis_with_vision(context, ai_output)
            else:
                logger.error(f"通义千问调用失败: {response.code} - {response.message}")
                return self._get_fallback_analysis(context)
                    
        except Exception as e:
            logger.error(f"图像识别分析失败: {e}")
            return self._get_fallback_analysis(context)
    
    def _get_fallback_analysis(self, context: List[str]) -> Dict:
        """备用分析（基于简单规则）"""
        # 根据上下文简单判断
        context_text = " ".join(context).lower() if context else ""
        
        emotion_tags = ["neutral"]
        scene_tags = ["chat"]
        keywords = ["聊天"]
        
        if any(word in context_text for word in ["哈哈", "笑", "开心"]):
            emotion_tags = ["happy", "funny"]
            keywords = ["开心", "笑"]
        elif any(word in context_text for word in ["谢", "感谢"]):
            emotion_tags = ["thanks"]
            scene_tags = ["thanks"]
            keywords = ["感谢"]
        elif any(word in context_text for word in ["你好", "嗨", "hi"]):
            emotion_tags = ["happy"]
            scene_tags = ["greeting"]
            keywords = ["问候", "你好"]
        
        return {
            "emotion_tags": emotion_tags,
            "scene_tags": scene_tags,
            "keywords": keywords,
            "ocr_text": "",
            "description": "通用表情包"
        }
    
    def _get_fallback_analysis_with_vision(self, context: List[str], ai_output: str) -> Dict:
        """基于通义千问输出的备用分析"""
        # 尝试从AI输出中提取有用信息
        emotion_tags = ["neutral"]
        scene_tags = ["chat"]
        keywords = ["聊天"]
        ocr_text = ""
        description = "表情包"
        
        # 简单的关键词匹配
        ai_lower = ai_output.lower()
        
        if any(word in ai_lower for word in ["开心", "笑", "哈哈", "happy", "laugh"]):
            emotion_tags = ["happy", "laugh"]
            keywords = ["开心", "笑"]
        elif any(word in ai_lower for word in ["难过", "哭", "sad", "cry"]):
            emotion_tags = ["sad", "cry"]
            keywords = ["难过", "哭"]
        elif any(word in ai_lower for word in ["感谢", "谢谢", "thanks"]):
            emotion_tags = ["thanks"]
            scene_tags = ["thanks"]
            keywords = ["感谢", "谢谢"]
        
        # 尝试提取描述
        if "描述" in ai_output or "表情包" in ai_output:
            # 简单提取描述
            lines = ai_output.split('\n')
            for line in lines:
                if "表情包" in line and len(line) > 10:
                    description = line.strip()
                    break
        
        return {
            "emotion_tags": emotion_tags,
            "scene_tags": scene_tags,
            "keywords": keywords,
            "ocr_text": ocr_text,
            "description": description
        }
    
    async def _save_learned_emoticon(
        self,
        file_hash: str,
        file_path: str,
        file_size: int,
        source_user_id: str,
        source_group_id: Optional[str],
        context: List[str],
        analysis: Dict
    ):
        """保存学习到的表情包"""
        async with self.async_session() as session:
            emoticon = LearnedEmoticon(
                file_hash=file_hash,
                file_path=file_path,
                file_size=file_size,
                source_user_id=source_user_id,
                source_group_id=source_group_id,
                emotion_tags=json.dumps(analysis.get("emotion_tags", []), ensure_ascii=False),
                scene_tags=json.dumps(analysis.get("scene_tags", []), ensure_ascii=False),
                keywords=json.dumps(analysis.get("keywords", []), ensure_ascii=False),
                ocr_text=analysis.get("ocr_text", ""),  # 新增OCR文字支持
                context_before=json.dumps(context, ensure_ascii=False),
                description=analysis.get("description", "表情包"),
                quality_score=0.5  # 初始评分
            )
            
            session.add(emoticon)
            await session.commit()
    
    async def _update_context(self, emoticon: LearnedEmoticon, new_context: List[str]):
        """更新已存在表情包的上下文"""
        # TODO: 可以记录多次使用的不同上下文，进一步优化标签
        pass
    
    async def get_matching_emoticon(
        self,
        emotion: str,
        context: str,
        keywords: List[str] = None
    ) -> Optional[Tuple[str, int]]:
        """
        获取匹配的学习表情包
        
        Args:
            emotion: 情感类型
            context: 当前上下文
            keywords: 关键词列表
        
        Returns:
            (file_path, emoticon_id) 或 None
        """
        try:
            async with self.async_session() as session:
                # 查询活跃的表情包
                result = await session.execute(
                    select(LearnedEmoticon)
                    .where(LearnedEmoticon.is_active == True)
                    .where(LearnedEmoticon.quality_score >= LearnerConfig.MIN_USE_SCORE)
                    .order_by(desc(LearnedEmoticon.quality_score))
                    .limit(50)
                )
                candidates = result.scalars().all()
                
                if not candidates:
                    return None
                
                # 匹配评分
                best_match = None
                best_score = 0.0
                
                for emoticon in candidates:
                    score = self._calculate_match_score(
                        emoticon, emotion, context, keywords
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_match = emoticon
                
                # 如果评分足够高，返回
                if best_match and best_score >= 0.5:
                    logger.debug(f"找到匹配表情包: {best_match.description} (分数: {best_score:.2f})")
                    return (best_match.file_path, best_match.id)
                
                return None
                
        except Exception as e:
            logger.exception(f"获取匹配表情包失败: {e}")
            return None
    
    def _calculate_match_score(
        self,
        emoticon: LearnedEmoticon,
        emotion: str,
        context: str,
        keywords: List[str]
    ) -> float:
        """计算匹配评分"""
        score = 0.0
        
        # 1. 情感标签匹配（40%）
        emotion_tags = json.loads(emoticon.emotion_tags)
        if emotion in emotion_tags:
            score += 0.4
        
        # 2. 关键词匹配（30%）
        emoticon_keywords = json.loads(emoticon.keywords)
        if keywords:
            matched = sum(1 for kw in keywords if any(kw in ek for ek in emoticon_keywords))
            score += 0.3 * (matched / len(keywords))
        
        # 3. 上下文相似度（20%）
        # 简单实现：检查关键词是否在上下文中
        context_lower = context.lower()
        matched_kw = sum(1 for kw in emoticon_keywords if kw in context_lower)
        if emoticon_keywords:
            score += 0.2 * (matched_kw / len(emoticon_keywords))
        
        # 4. 质量评分（10%）
        score += 0.1 * emoticon.quality_score
        
        return score
    
    async def record_usage(
        self,
        emoticon_id: int,
        user_id: str,
        context: str,
        success: bool = False
    ):
        """记录表情包使用"""
        async with self.async_session() as session:
            # 记录日志
            log = EmoticonUsageLog(
                emoticon_id=emoticon_id,
                user_id=user_id,
                context=context,
                success=success
            )
            session.add(log)
            
            # 更新表情包统计
            result = await session.execute(
                select(LearnedEmoticon).where(LearnedEmoticon.id == emoticon_id)
            )
            emoticon = result.scalar_one_or_none()
            
            if emoticon:
                emoticon.use_count += 1
                if success:
                    emoticon.success_count += 1
                
                # 更新质量评分
                if emoticon.use_count > 0:
                    success_rate = emoticon.success_count / emoticon.use_count
                    # 结合历史评分和新数据
                    emoticon.quality_score = emoticon.quality_score * 0.7 + success_rate * 0.3
            
            await session.commit()
    
    async def get_statistics(self) -> Dict:
        """获取学习统计"""
        async with self.async_session() as session:
            # 总表情包数
            result = await session.execute(
                select(func.count(LearnedEmoticon.id))
            )
            total_count = result.scalar()
            
            # 活跃表情包数
            result = await session.execute(
                select(func.count(LearnedEmoticon.id))
                .where(LearnedEmoticon.is_active == True)
            )
            active_count = result.scalar()
            
            # 总使用次数
            result = await session.execute(
                select(func.sum(LearnedEmoticon.use_count))
            )
            total_uses = result.scalar() or 0
            
            return {
                "total_emoticons": total_count,
                "active_emoticons": active_count,
                "total_uses": total_uses,
                "storage_path": str(self.storage_path)
            }
    
    async def get_emoticons_list(self, limit: int = 50) -> List[Dict]:
        """获取表情包列表"""
        async with self.async_session() as session:
            result = await session.execute(
                select(LearnedEmoticon)
                .where(LearnedEmoticon.is_active == True)
                .order_by(desc(LearnedEmoticon.quality_score))
                .limit(limit)
            )
            emoticons = result.scalars().all()
            
            # 转换为字典格式
            emoticon_list = []
            for emo in emoticons:
                emoticon_list.append({
                    "id": emo.id,
                    "file_path": emo.file_path,
                    "emotion_tags": emo.emotion_tags,
                    "scene_tags": emo.scene_tags,
                    "keywords": emo.keywords,
                    "description": emo.description,
                    "quality_score": emo.quality_score,
                    "use_count": emo.use_count,
                    "is_active": emo.is_active,
                    "source_user_id": emo.source_user_id,
                    "created_at": emo.learned_at.isoformat() if emo.learned_at else None
                })
            
            return emoticon_list


# 全局实例
emoticon_learner = EmoticonLearner()

# 导出
__all__ = ['emoticon_learner', 'EmoticonLearner', 'LearnerConfig']

