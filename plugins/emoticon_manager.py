"""
智能表情管理系统
- 第一步：基于规则的emoji智能使用
- 第三步：集成AI学习表情包系统
"""

from typing import Optional, List, Dict, Tuple
import random
import re
from datetime import datetime
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from pathlib import Path

class EmoticonConfig:
    """表情配置"""
    # 基础使用概率（会根据用户画像动态调整）
    BASE_EMOTICON_PROBABILITY = 0.25  # 25%的消息带表情
    
    # 情感强度阈值（超过此值更容易使用表情）
    EMOTION_THRESHOLD = 0.6
    
    # 连续消息不使用表情的概率（避免每句都有）
    CONTINUOUS_NO_EMOTICON_PROB = 0.7  # 连续消息70%不带表情
    
    # 用户类型调整系数
    USER_TYPE_MULTIPLIER = {
        "active": 1.5,      # 活跃用户：更多表情
        "normal": 1.0,      # 普通用户：正常
        "reserved": 0.6     # 内向用户：更少表情
    }


class EmoticonManager:
    """
    智能表情管理器
    
    功能：
    1. 根据情感智能选择emoji
    2. 判断是否应该使用表情
    3. 避免过度使用
    4. 为AI学习预留接口
    """
    
    # Emoji表情库（按情感分类）
    EMOJI_LIBRARY = {
        # 积极情感
        "happy": ["😊", "😄", "🥰", "😆", "🤗"],
        "excited": ["😍", "🤩", "✨", "🎉"],
        "love": ["❤️", "💕", "💖", "🥰"],
        
        # 消极情感
        "sad": ["😢", "😔", "🥺", "😞"],
        "angry": ["😠", "💢", "😤"],
        "worried": ["😰", "😟", "😥"],
        
        # 中性/反应
        "laugh": ["😂", "🤣", "哈哈", "嘿嘿"],
        "thinking": ["🤔", "💭", "嗯"],
        "confused": ["😕", "❓", "😵"],
        "surprise": ["😮", "😯", "哇"],
        
        # 赞同/否定
        "agree": ["👍", "✅", "对的", "没错"],
        "disagree": ["👎", "❌"],
        
        # 其他常用
        "shy": ["😳", "🙈", "害羞"],
        "cool": ["😎", "👌", "🆒"],
        "greeting": ["👋", "嗨", "哈喽"],
        "bye": ["👋", "拜拜", "再见"],
        "thanks": ["🙏", "谢谢", "感谢"],
    }
    
    # 文本表情（更自然）
    TEXT_EMOTICONS = {
        "happy": ["哈哈", "嘿嘿", "嘻嘻"],
        "agree": ["对的", "没错", "确实"],
        "thinking": ["嗯", "唔"],
        "shy": ["害羞", "不好意思"],
    }
    
    def __init__(self):
        self.last_emoticon_time = {}  # 记录上次使用表情的时间
        self.user_emoticon_stats = {}  # 用户使用统计（为AI学习准备）
        self.learned_emoticons = {}    # AI学习到的表情包（第三步）
        self._learner = None           # 延迟加载学习器（避免循环导入）
    
    def should_use_emoticon(
        self, 
        user_id: str,
        emotion: str,
        emotion_intensity: float,
        is_continuous: bool = False
    ) -> bool:
        """
        智能判断是否应该使用表情
        
        考虑因素：
        1. 情感强度
        2. 用户类型
        3. 是否连续消息
        4. 随机性（模拟真人的不确定性）
        """
        # 基础概率
        base_prob = EmoticonConfig.BASE_EMOTICON_PROBABILITY
        
        # 1. 情感强度调整
        if emotion_intensity > EmoticonConfig.EMOTION_THRESHOLD:
            base_prob *= 1.8  # 强烈情感时更容易使用表情
        
        # 2. 特定情感更容易用表情
        high_emoticon_emotions = ["happy", "excited", "laugh", "love", "surprise"]
        if emotion in high_emoticon_emotions:
            base_prob *= 1.5
        
        # 3. 连续消息降低概率
        if is_continuous:
            base_prob *= (1 - EmoticonConfig.CONTINUOUS_NO_EMOTICON_PROB)
        
        # 4. 用户类型调整（简单版，后续可以从用户画像获取）
        user_type = self._get_user_type(user_id)
        base_prob *= EmoticonConfig.USER_TYPE_MULTIPLIER.get(user_type, 1.0)
        
        # 5. 限制最大概率
        base_prob = min(0.7, base_prob)  # 最多70%
        
        # 6. 随机决策
        return random.random() < base_prob
    
    def _get_user_type(self, user_id: str) -> str:
        """
        获取用户类型
        后续可以从用户画像系统获取
        """
        # 简单实现：随机分配（实际应该从数据库读取）
        if user_id not in self.user_emoticon_stats:
            self.user_emoticon_stats[user_id] = {
                "type": random.choice(["normal", "normal", "active", "reserved"]),
                "total_messages": 0,
                "emoticon_count": 0
            }
        
        return self.user_emoticon_stats[user_id]["type"]
    
    def select_emoticon(
        self,
        emotion: str,
        text: str,
        user_id: str,
        prefer_text: bool = True
    ) -> Optional[str]:
        """
        智能选择表情
        
        Args:
            emotion: 情感类型
            text: 消息文本
            user_id: 用户ID
            prefer_text: 是否优先使用文本表情（更自然）
        """
        # 优先使用文本表情（更像真人）
        if prefer_text and emotion in self.TEXT_EMOTICONS:
            if random.random() < 0.6:  # 60%概率用文本表情
                return random.choice(self.TEXT_EMOTICONS[emotion])
        
        # 使用emoji
        if emotion in self.EMOJI_LIBRARY:
            return random.choice(self.EMOJI_LIBRARY[emotion])
        
        # 默认情况：根据文本内容智能选择
        return self._smart_select_by_text(text)
    
    def _smart_select_by_text(self, text: str) -> Optional[str]:
        """根据文本内容智能选择表情"""
        text_lower = text.lower()
        
        # 关键词匹配
        keyword_emotions = {
            "哈哈": "laugh",
            "嘿嘿": "happy",
            "嗯": "thinking",
            "好的": "agree",
            "对": "agree",
            "谢": "thanks",
            "拜": "bye",
            "？": "confused",
            "！": "excited",
        }
        
        for keyword, emotion in keyword_emotions.items():
            if keyword in text:
                if emotion in self.EMOJI_LIBRARY:
                    return random.choice(self.EMOJI_LIBRARY[emotion])
        
        return None
    
    def add_emoticon_to_message(
        self,
        message: str,
        user_id: str,
        emotion: str = "neutral",
        emotion_intensity: float = 0.5,
        is_continuous: bool = False
    ) -> str:
        """
        智能地在消息中添加表情
        
        返回带表情的消息或原消息
        
        第三步新增：会尝试使用学习到的表情包
        """
        # 1. 判断是否应该使用表情
        if not self.should_use_emoticon(user_id, emotion, emotion_intensity, is_continuous):
            return message
        
        # 2. 第三步：尝试使用学习到的表情包（15%概率）
        if random.random() < 0.15:  # 15%使用学习表情
            learned_emoticon = self._try_get_learned_emoticon(emotion, message)
            if learned_emoticon:
                return learned_emoticon  # 直接返回表情图片segment
        
        # 3. 选择emoji表情
        emoticon = self.select_emoticon(emotion, message, user_id)
        
        if not emoticon:
            return message
        
        # 4. 智能添加位置
        if len(message) < 15:
            result = f"{message} {emoticon}"
        else:
            if random.random() < 0.7:
                result = f"{message} {emoticon}"
            else:
                result = self._insert_emoticon_smart(message, emoticon)
        
        # 5. 记录统计
        self._record_emoticon_usage(user_id)
        
        logger.debug(f"💬 为消息添加表情：{emotion} -> {emoticon}")
        
        return result
    
    def _insert_emoticon_smart(self, message: str, emoticon: str) -> str:
        """智能地在消息中间插入表情"""
        # 查找合适的插入点（句子中间的标点）
        punctuation = ['，', ',', '、']
        for p in punctuation:
            if p in message:
                parts = message.split(p, 1)
                if len(parts) == 2 and len(parts[0]) > 10:
                    return f"{parts[0]}{p}{emoticon} {parts[1]}"
        
        # 找不到合适位置，还是加末尾
        return f"{message} {emoticon}"
    
    def _record_emoticon_usage(self, user_id: str):
        """记录表情使用情况（为AI学习准备）"""
        if user_id not in self.user_emoticon_stats:
            self.user_emoticon_stats[user_id] = {
                "type": "normal",
                "total_messages": 0,
                "emoticon_count": 0
            }
        
        self.user_emoticon_stats[user_id]["emoticon_count"] += 1
        self.last_emoticon_time[user_id] = datetime.now()
    
    def update_message_count(self, user_id: str):
        """更新消息计数"""
        if user_id not in self.user_emoticon_stats:
            self.user_emoticon_stats[user_id] = {
                "type": "normal",
                "total_messages": 0,
                "emoticon_count": 0
            }
        
        self.user_emoticon_stats[user_id]["total_messages"] += 1
    
    def get_emoticon_stats(self, user_id: str) -> Dict:
        """获取用户的表情使用统计"""
        if user_id not in self.user_emoticon_stats:
            return {"usage_rate": 0.0, "total": 0}
        
        stats = self.user_emoticon_stats[user_id]
        total = stats["total_messages"]
        count = stats["emoticon_count"]
        
        return {
            "usage_rate": count / total if total > 0 else 0.0,
            "total": total,
            "emoticon_count": count,
            "user_type": stats["type"]
        }
    
    # ==================== 第三步：AI学习表情包集成 ====================
    
    def _get_learner(self):
        """延迟加载学习器（避免循环导入）"""
        if self._learner is None:
            try:
                from .emoticon_learner import emoticon_learner
                self._learner = emoticon_learner
                logger.debug("✅ 成功加载表情学习器")
            except ImportError as e:
                logger.warning(f"⚠️ 无法加载表情学习器: {e}")
                self._learner = False  # 标记为不可用
        
        return self._learner if self._learner is not False else None
    
    def _try_get_learned_emoticon(
        self,
        emotion: str,
        message: str
    ) -> Optional[str]:
        """
        尝试获取学习到的表情包
        
        Returns:
            表情包的MessageSegment（如果找到）或None
        """
        try:
            learner = self._get_learner()
            if not learner:
                return None
            
            # 从学习器获取匹配的表情包
            # 这是一个异步方法，需要在同步上下文中使用
            # 我们返回一个特殊的标记，让调用方异步处理
            # 或者我们可以返回一个包装对象
            
            # 简单实现：返回None，让其使用普通emoji
            # 真正的集成需要重构send_split_message
            return None
            
        except Exception as e:
            logger.debug(f"获取学习表情包失败: {e}")
            return None
    
    async def try_get_learned_emoticon_async(
        self,
        emotion: str,
        message: str,
        keywords: List[str] = None
    ) -> Optional[Tuple[str, int]]:
        """
        异步版本：尝试获取学习到的表情包
        
        Returns:
            (file_path, emoticon_id) 或 None
        """
        try:
            learner = self._get_learner()
            if not learner:
                return None
            
            result = await learner.get_matching_emoticon(
                emotion=emotion,
                context=message,
                keywords=keywords
            )
            
            if result:
                logger.info(f"🎨 使用学习到的表情包")
            
            return result
            
        except Exception as e:
            logger.debug(f"获取学习表情包失败: {e}")
            return None
    
    async def record_learned_emoticon_usage(
        self,
        emoticon_id: int,
        user_id: str,
        context: str,
        success: bool = False
    ):
        """记录学习表情包的使用情况"""
        try:
            learner = self._get_learner()
            if learner:
                await learner.record_usage(emoticon_id, user_id, context, success)
        except Exception as e:
            logger.debug(f"记录表情使用失败: {e}")
    
    def learn_emoticon_from_context(
        self,
        emoticon_data: bytes,
        context: str,
        user_reaction: str
    ):
        """
        从上下文学习表情包（第三步接口）
        
        现在由emoticon_learner.py实现
        """
        logger.info("🎓 使用emoticon_learner进行学习")
        pass
    
    def get_learned_emoticon(self, emotion: str, context: str) -> Optional[bytes]:
        """
        获取AI学习到的表情包（第三步接口）
        
        现在由emoticon_learner.py实现
        """
        return None


# 全局实例
emoticon_manager = EmoticonManager()

# 导出
__all__ = ['emoticon_manager', 'EmoticonManager', 'EmoticonConfig']

