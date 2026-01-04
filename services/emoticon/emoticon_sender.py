"""
表情发送服务 - Service Layer
职责：智能选择和发送表情包（核心新功能）
代码量：~300 行
"""
from typing import Optional, Dict, List, Tuple
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
import random
from datetime import datetime, timedelta

# 导入服务
from services.emoticon.emoticon_service import get_emoticon_service
from services.emoticon.emoticon_config import EmoticonConfig
from services.emotion import get_emotion_service

# 导入模型
from models.emoticon_models import LearnedEmoticon


class EmoticonSender:
    """
    表情发送服务
    
    核心功能：
    1. 判断是否应该发送表情
    2. 根据情感和内容智能选择表情
    3. 支持emoji、学习的表情包、文本表情
    4. 与情感系统联动
    """
    
    def __init__(self):
        self.emoticon_service = get_emoticon_service()
        self.emotion_service = get_emotion_service()
        
        # 使用记录（防止过度使用）
        self.recent_usage: Dict[str, List[datetime]] = {}  # user_id -> [timestamps]
        self.last_emoticon_hash: Dict[str, Tuple[str, datetime]] = {}  # user_id -> (hash, time)
    
    async def enhance_message(
        self,
        message: str,
        user_id: str,
        emotion_state: Optional[Dict] = None,
        context: str = "chat_response"
    ) -> str:
        """
        智能增强消息（添加表情）
        
        Args:
            message: 原始消息
            user_id: 用户ID
            emotion_state: 情感状态
            context: 上下文（chat_response/proactive等）
        
        Returns:
            增强后的消息（可能添加了表情）
        """
        # 1. 判断是否应该发送表情
        if not await self._should_send_emoticon(user_id, emotion_state, context):
            return message
        
        # 2. 选择合适的表情
        emoticon = await self._select_emoticon(message, emotion_state)
        
        if not emoticon:
            return message
        
        # 3. 添加表情到消息
        enhanced_message = self._add_emoticon_to_message(message, emoticon)
        
        logger.debug(f"💬 为用户 {user_id} 添加表情: {emoticon.get('type', 'unknown')}")
        return enhanced_message
    
    async def _should_send_emoticon(
        self,
        user_id: str,
        emotion_state: Optional[Dict],
        context: str
    ) -> bool:
        """
        判断是否应该发送表情
        
        考虑因素：
        1. 基础概率
        2. 情感状态影响
        3. 体力影响
        4. 连续使用控制
        """
        # 基础概率
        probability = EmoticonConfig.BASE_SEND_PROBABILITY
        
        # 情感影响
        if emotion_state:
            emotion = emotion_state.get('style', 'neutral').lower()
            happiness = emotion_state.get('happiness', 50)
            energy = emotion_state.get('energy', 50)
            
            # 根据风格调整概率
            emotion_map = {
                '毒舌': 'neutral',
                '腹黑': 'happy',
                '傲娇': 'shy',
                '病娇': 'sad',
                '慵懒': 'tired',
                '元气': 'excited',
                '友好': 'happy'
            }
            mapped_emotion = emotion_map.get(emotion, 'neutral')
            multiplier = EmoticonConfig.EMOTION_MULTIPLIERS.get(mapped_emotion, 1.0)
            probability *= multiplier
            
            # 体力影响
            if energy > 70:
                probability *= 1.2
            elif energy < 40:
                probability *= 0.6
        
        # 检查连续使用
        if self._is_continuous_usage(user_id):
            probability *= EmoticonConfig.CONTINUOUS_NO_EMOTICON_PROB
        
        # 随机判断
        should_send = random.random() < probability
        
        if should_send:
            # 记录使用
            self._record_usage_time(user_id)
        
        return should_send
    
    def _is_continuous_usage(self, user_id: str) -> bool:
        """检查是否连续使用"""
        if user_id not in self.recent_usage:
            return False
        
        recent_times = self.recent_usage[user_id]
        if not recent_times:
            return False
        
        # 检查最近5分钟内的使用次数
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        recent_count = sum(1 for t in recent_times if t > five_minutes_ago)
        
        return recent_count >= EmoticonConfig.MAX_CONTINUOUS_EMOTICONS
    
    def _record_usage_time(self, user_id: str):
        """记录使用时间"""
        if user_id not in self.recent_usage:
            self.recent_usage[user_id] = []
        
        self.recent_usage[user_id].append(datetime.now())
        
        # 只保留最近10次
        if len(self.recent_usage[user_id]) > 10:
            self.recent_usage[user_id] = self.recent_usage[user_id][-10:]
    
    async def _select_emoticon(
        self,
        message: str,
        emotion_state: Optional[Dict]
    ) -> Optional[Dict]:
        """
        选择合适的表情
        
        Returns:
            {'type': 'emoji'|'learned'|'text', 'content': ...}
        """
        # 提取情感
        emotion = self._extract_emotion_from_state(emotion_state)
        
        # 随机选择类型（根据权重）
        emoticon_type = self._choose_emoticon_type()
        
        if emoticon_type == 'emoji':
            return self._select_emoji(emotion, message)
        elif emoticon_type == 'learned':
            return await self._select_learned_emoticon(emotion, message)
        elif emoticon_type == 'text':
            return self._select_text_emoticon(emotion, message)
        
        return None
    
    def _extract_emotion_from_state(self, emotion_state: Optional[Dict]) -> str:
        """从情感状态提取情感类型"""
        if not emotion_state:
            return 'neutral'
        
        style = emotion_state.get('style', '友好')
        happiness = emotion_state.get('happiness', 50)
        energy = emotion_state.get('energy', 50)
        
        # 根据风格和参数映射情感
        if style == '元气' or happiness > 75:
            return 'excited'
        elif style == '友好' or style == '腹黑':
            return 'happy'
        elif style == '傲娇':
            return 'shy'
        elif style == '病娇' or happiness < 30:
            return 'sad'
        elif style == '毒舌':
            return 'cool'
        elif style == '慵懒' or energy < 40:
            return 'tired'
        else:
            return 'neutral'
    
    def _choose_emoticon_type(self) -> str:
        """根据权重随机选择表情类型"""
        weights = EmoticonConfig.EMOTICON_TYPE_WEIGHTS
        types = list(weights.keys())
        probabilities = list(weights.values())
        
        return random.choices(types, weights=probabilities)[0]
    
    def _select_emoji(self, emotion: str, message: str) -> Optional[Dict]:
        """选择emoji"""
        emoji_list = EmoticonConfig.EMOJI_LIBRARY.get(emotion, [])
        
        if not emoji_list:
            # 尝试其他相近的情感
            fallback_emotions = ['happy', 'neutral', 'thinking']
            for fallback in fallback_emotions:
                emoji_list = EmoticonConfig.EMOJI_LIBRARY.get(fallback, [])
                if emoji_list:
                    break
        
        if emoji_list:
            emoji = random.choice(emoji_list)
            return {'type': 'emoji', 'content': emoji}
        
        return None
    
    async def _select_learned_emoticon(
        self,
        emotion: str,
        message: str
    ) -> Optional[Dict]:
        """选择学习的表情包"""
        # 从消息中提取关键词
        keywords = self._extract_keywords(message)
        
        # 搜索表情包
        emoticons = await self.emoticon_service.search_emoticons(
            emotion=emotion,
            keywords=keywords,
            limit=5
        )
        
        if not emoticons:
            # 尝试不限情感搜索
            emoticons = await self.emoticon_service.search_emoticons(
                keywords=keywords,
                limit=5
            )
        
        if emoticons:
            # 随机选择一个（考虑质量分数）
            emoticon = self._weighted_random_choice(emoticons)
            return {
                'type': 'learned',
                'content': emoticon,
                'id': emoticon.id
            }
        
        return None
    
    def _select_text_emoticon(self, emotion: str, message: str) -> Optional[Dict]:
        """选择文本表情"""
        text_list = EmoticonConfig.TEXT_EMOTICONS.get(emotion, [])
        
        if not text_list:
            text_list = EmoticonConfig.TEXT_EMOTICONS.get('happy', [])
        
        if text_list:
            text = random.choice(text_list)
            return {'type': 'text', 'content': text}
        
        return None
    
    def _extract_keywords(self, message: str) -> List[str]:
        """从消息中提取关键词"""
        # 简单的关键词提取（可以后续优化）
        keywords = []
        
        # 检查常见词
        common_keywords = {
            '开心': ['开心', '高兴', '快乐', '哈哈'],
            '难过': ['难过', '伤心', '哭'],
            '生气': ['生气', '愤怒', '气'],
            '累': ['累', '困', '疲惫'],
            '吃': ['吃', '饿', '美食'],
            '睡': ['睡', '困'],
        }
        
        for key, words in common_keywords.items():
            if any(word in message for word in words):
                keywords.append(key)
        
        return keywords[:3]  # 最多3个关键词
    
    def _weighted_random_choice(self, emoticons: List[LearnedEmoticon]) -> LearnedEmoticon:
        """根据质量分数加权随机选择"""
        if not emoticons:
            return None
        
        if len(emoticons) == 1:
            return emoticons[0]
        
        # 计算权重（质量分数 + 使用次数）
        weights = []
        for emo in emoticons:
            weight = emo.quality_score * 0.7 + min(emo.use_count / 100, 0.3)
            weights.append(weight)
        
        return random.choices(emoticons, weights=weights)[0]
    
    def _add_emoticon_to_message(self, message: str, emoticon: Dict) -> str:
        """将表情添加到消息中"""
        emoticon_type = emoticon.get('type')
        content = emoticon.get('content')
        
        if emoticon_type == 'emoji':
            # emoji直接添加
            # 随机位置：前面、中间、后面
            positions = ['start', 'end']
            position = random.choice(positions)
            
            if position == 'start':
                return f"{content} {message}"
            else:
                return f"{message} {content}"
        
        elif emoticon_type == 'text':
            # 文本表情添加在后面
            return f"{message} {content}"
        
        elif emoticon_type == 'learned':
            # 学习的表情包作为图片
            # 注意：这里返回的是文本+图片的组合，需要在handler层处理
            # 暂时返回原消息，在handler层会单独发送图片
            return message
        
        return message
    
    def get_learned_emoticon_path(self, emoticon_content) -> Optional[str]:
        """获取学习的表情包路径（供handler使用）"""
        if isinstance(emoticon_content, LearnedEmoticon):
            return emoticon_content.file_path
        return None


# 全局单例
_emoticon_sender: Optional[EmoticonSender] = None

def get_emoticon_sender() -> EmoticonSender:
    """获取全局表情发送服务实例"""
    global _emoticon_sender
    if _emoticon_sender is None:
        _emoticon_sender = EmoticonSender()
    return _emoticon_sender

























