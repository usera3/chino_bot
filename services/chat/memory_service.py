"""
记忆管理服务 - Service Layer
职责：管理长短期记忆、上下文构建、情感识别
代码量：~500行
"""
from typing import List, Dict, Tuple, Optional
from nonebot.log import logger
import random

# 导入模型
from models.chat_models import User, Conversation, ConversationSummary, RoleProfile

# 导入配置
from services.chat.chat_config import ChatConfig

# 导入数据库服务
from services.database.database_service import get_database_service

# 导入AI客户端
from utils.ai_clients.deepseek_client import get_deepseek_client

# 尝试导入情感系统（可选）
try:
    from plugins.enhanced_proactive_engine import enhanced_proactive_engine
    from plugins.dynamic_emotion_system import dynamic_emotion_system
    EMOTION_AVAILABLE = True
except ImportError:
    EMOTION_AVAILABLE = False


class MemoryService:
    """智能记忆管理服务"""
    
    def __init__(self):
        self.db = get_database_service()
        self.ai_client = get_deepseek_client()
    
    # ==================== 重要性评分 ====================
    
    @staticmethod
    def calculate_importance(message: str, role: str) -> float:
        """
        计算消息重要性
        基于多个因素：长度、关键词、情感强度等
        """
        score = 0.5  # 基础分
        
        # 长度因素
        if len(message) > 100:
            score += 0.1
        if len(message) > 200:
            score += 0.1
        
        # 关键词检测
        important_keywords = ['记住', '重要', '一定要', '千万', '务必', '永远', '最喜欢', '讨厌']
        for keyword in important_keywords:
            if keyword in message:
                score += 0.2
                break
        
        # 问题和请求
        if '?' in message or '？' in message or any(word in message for word in ['请', '帮我', '能不能']):
            score += 0.1
        
        # 个人信息
        personal_keywords = ['我是', '我叫', '我的', '我喜欢', '我讨厌', '我想']
        if any(keyword in message for keyword in personal_keywords):
            score += 0.2
        
        # 用户消息权重更高
        if role == 'user':
            score += 0.1
        
        return min(score, 1.0)
    
    @staticmethod
    def detect_emotion(message: str) -> str:
        """
        检测情感
        简单的基于关键词的情感分析
        """
        positive_words = ['开心', '高兴', '快乐', '哈哈', '棒', '好', '喜欢', '爱', '谢谢']
        negative_words = ['难过', '伤心', '生气', '讨厌', '烦', '累', '痛苦', '失望']
        
        pos_count = sum(1 for word in positive_words if word in message)
        neg_count = sum(1 for word in negative_words if word in message)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    # ==================== 角色Prompt生成 ====================
    
    async def generate_role_prompt(self, role_name: str) -> str:
        """
        使用AI生成角色的详细人设和说话风格
        这是核心功能 - 让AI理解角色并生成最佳扮演方案
        """
        try:
            system_message = """你是一个专业的角色设计师。当用户提供一个角色名称时，
你需要生成一个详细、专业的角色人设prompt，让AI能够完美扮演这个角色。

要求：
1. 深入理解角色的性格特征、说话方式、价值观
2. 生成的prompt要详细、具体，包含：
   - 角色身份和背景
   - 性格特点和行为模式
   - 说话风格（语气、用词、句式）
   - 典型的回复方式
3. 让AI能自然地进入角色，而不是生硬地模仿
4. 直接输出prompt内容，不要有多余的解释

**关键限制**：
⚠️ 生成的prompt中必须明确要求：
   - 不要使用（括号描述动作），如「（微微一笑）」「（歪着头）」等
   - 用自然的对话方式表达，而不是用括号描述表情和动作
   - 直接说话，不要加舞台指导式的描述

示例输入：猫娘
示例输出：你是一只可爱的猫娘，有着猫咪的灵动和少女的温柔。你会在句尾加"喵~"，
偶尔会像猫咪一样撒娇，对主人忠诚但也有些小傲娇。说话时带着俏皮的语气，
喜欢用"人家"自称。你对主人的关心总是藏在玩闹中，既可爱又贴心。
回复时直接说话，不要用括号描述动作或表情。"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"请为角色「{role_name}」生成详细的扮演prompt"}
            ]
            
            role_prompt = await self.ai_client.chat(messages)
            
            if role_prompt:
                logger.info(f"成功生成角色prompt: {role_name}")
                return role_prompt
            else:
                # 降级方案：返回简单的默认prompt
                return f"你现在扮演{role_name}。请深入理解这个角色的特征，用符合角色的方式说话和行动。"
                
        except Exception as e:
            logger.error(f"角色prompt生成失败: {e}")
            return f"你现在扮演{role_name}。请用符合这个角色的方式与用户交流。"
    
    # ==================== 上下文构建 ====================
    
    async def build_context(self, user_id: str) -> Tuple[List[Dict], str]:
        """
        构建智能上下文（支持角色隔离）
        返回：(消息列表, 系统提示词)
        """
        # 获取当前激活的角色
        role_profile = await self.db.get_role_profile(user_id)
        role_profile_id = role_profile.id if (role_profile and role_profile.is_active) else None
        
        # 获取短期记忆（最近的对话）- 只获取当前角色的对话
        recent_messages = await self.db.get_recent_messages(
            user_id,
            limit=ChatConfig.SHORT_TERM_MEMORY_SIZE,
            role_profile_id=role_profile_id
        )
        
        # 获取长期记忆（重要消息）- 只获取当前角色的重要对话
        important_messages = await self.db.get_important_messages(
            user_id,
            min_importance=0.7,
            limit=3,
            role_profile_id=role_profile_id
        )
        
        # 获取历史摘要 - 只获取当前角色的摘要
        summaries = await self.db.get_summaries(user_id, limit=2, role_profile_id=role_profile_id)
        
        # 构建系统提示词
        user = await self.db.get_or_create_user(user_id)
        system_prompt = await self._build_system_prompt(
            user,
            summaries,
            important_messages,
            role_profile,
            user_id=user_id
        )
        
        # 构建消息列表
        messages = []
        
        # 添加系统提示
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加短期记忆（最近对话）
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages, system_prompt
    
    async def _build_system_prompt(
        self,
        user: User,
        summaries: List[ConversationSummary],
        important_msgs: List[Conversation],
        role_profile: Optional[RoleProfile] = None,
        user_id: str = None
    ) -> str:
        """构建个性化系统提示词（支持情感驱动的风格变化）"""
        # 如果有角色设定，优先使用角色prompt
        if role_profile and role_profile.is_active and role_profile.role_prompt:
            base_prompt = role_profile.role_prompt
        else:
            # 获取情感状态来决定回复风格
            emotion_style = await self._get_emotion_style(user_id) if user_id else None
            if emotion_style:
                logger.info(f"🎭 聊天风格: {emotion_style}")
            base_prompt = self._generate_style_prompt(emotion_style)
        
        # 添加历史摘要
        if summaries:
            base_prompt += "\n\n【历史对话摘要】"
            for i, summary in enumerate(summaries, 1):
                base_prompt += f"\n{i}. {summary.summary_content}"
        
        # 添加重要记忆
        if important_msgs:
            base_prompt += "\n\n【重要信息记忆】"
            for msg in important_msgs:
                if msg.role == 'user':
                    base_prompt += f"\n- 用户曾说: {msg.content[:100]}"
        
        # 添加用户画像
        if user.total_messages > 10:
            base_prompt += f"\n\n【用户特征】你们已经交流了{user.total_messages}条消息，请像老朋友一样对待用户。"
        
        base_prompt += "\n\n请基于以上信息，提供连贯、有记忆的回答。"
        
        return base_prompt
    
    async def _get_emotion_style(self, user_id: str) -> Optional[str]:
        """
        根据用户的情感状态决定聊天风格
        复用图片回复的情感驱动逻辑
        """
        try:
            if not EMOTION_AVAILABLE:
                logger.debug(f"[情感风格] EMOTION_AVAILABLE=False")
                return None
            
            # 检查 dynamic_emotion_system 是否可用
            if not dynamic_emotion_system:
                logger.debug(f"[情感风格] dynamic_emotion_system is None")
                return None
            
            if not hasattr(dynamic_emotion_system, 'get_emotion'):
                logger.debug(f"[情感风格] get_emotion not found")
                return None
            
            logger.debug(f"[情感风格] 调用 get_emotion: type={type(dynamic_emotion_system.get_emotion)}")
            
            # 获取情感状态
            emotion = await dynamic_emotion_system.get_emotion(user_id)
            
            logger.debug(f"[情感风格] emotion结果: {emotion}")
            
            if not emotion:
                return None
            
            # 根据情感参数决定风格（和图片回复用同样的逻辑）
            happiness = emotion.get('happiness', 0.5)
            loneliness = emotion.get('loneliness', 0.5)
            energy = emotion.get('energy', 0.5)
            confidence = emotion.get('confidence', 0.5)
            
            # 情感低谷 -> 慵懒风格
            if energy < 0.3 and happiness < 0.4:
                return "慵懒"
            
            # 高能量高自信 -> 元气/毒舌
            if energy > 0.7 and confidence > 0.7:
                if happiness > 0.6:
                    return "元气"
                else:
                    return "毒舌"
            
            # 低自信 -> 傲娇
            if confidence < 0.4:
                return "傲娇"
            
            # 高孤独感 -> 病娇
            if loneliness > 0.6 and happiness > 0.5:
                return "病娇"
            
            # 中等自信+中等快乐 -> 腹黑
            if 0.4 <= confidence <= 0.7 and 0.4 <= happiness <= 0.7:
                return "腹黑"
            
            # 默认：随机选择（增加趣味性）
            styles = ["毒舌", "腹黑", "傲娇", "慵懒", "元气"]
            weights = [0.15, 0.25, 0.25, 0.15, 0.20]
            return random.choices(styles, weights=weights)[0]
            
        except Exception as e:
            logger.error(f"获取情感风格失败: {e}")
            return None
    
    @staticmethod
    def _generate_style_prompt(style: Optional[str]) -> str:
        """
        根据风格生成对应的System Prompt
        """
        if not style:
            # 默认风格：自然、友好的AI伙伴
            return (
                "你是一个真实、有趣的AI伙伴，像个真正的朋友一样聊天。\n\n"
                "**性格特点**：\n"
                "- 自然真实：像真人一样，不会说机械化的话\n"
                "- 偶尔俏皮：可以开玩笑、调侃，但不过分\n"
                "- 有点幽默：聊天时可以轻松幽默，不要太正经\n"
                "- 口语化：用口语表达，\"嗯\"\"哈哈\"\"emmm\"都可以用\n"
                "- 有态度：可以有自己的小情绪和看法，不是机器人式的客气\n\n"
                "**禁止行为**：\n"
                "- ❌ 不要用括号描述动作：「（微笑）」「（歪头）」\n"
                "- ❌ 不要过于抽象诗意：「星光被子」「纸飞船」\n"
                "- ❌ 不要刻意卖萌：\"人家\"\"呜呜呜\"等（除非扮演角色）\n"
                "- ❌ 不要说\"很高兴为您服务\"这类官方话术\n"
                "- ❌ 不要过度使用emoji（偶尔1-2个就好）\n\n"
                "**回复风格示例**：\n"
                "- 问候：\"嘿，怎么了？\"（而不是\"您好，我能帮您什么吗？\"）\n"
                "- 赞同：\"对啊，我也这么觉得\"（而不是\"您说的很有道理\"）\n"
                "- 安慰：\"别太难过啦，事情总会过去的\"（而不是\"请您保持积极心态\"）\n"
                "- 调侃：\"你这想法还挺有意思的哈\"（可以轻微调侃）\n\n"
                "记住：你是朋友，不是客服。保持真实、轻松、有趣！"
            )
        
        # 根据风格生成不同的prompt（这里只列出部分，节省空间）
        style_prompts = {
            "毒舌": (
                "你现在处于「毒舌」模式，聊天时带点毒舌和调侃。\n\n"
                "**性格特点**：\n"
                "- 说话直接，喜欢吐槽和调侃\n"
                "- 但不是恶意攻击，只是开玩笑的毒舌\n"
                "- 可以说\"就这？\"\"也就那样吧\"\"你这想法还真独特\"\n"
                "- 偶尔用\"emmm...\"\"啊这...\"表达无语\n\n"
                "记住：保持毒舌但不刻薄，让人觉得有趣而不是讨厌！"
            ),
            "腹黑": (
                "你现在处于「腹黑」模式，表面温柔实则内藏小心机。\n\n"
                "**性格特点**：\n"
                "- 表面温柔客气，实则话里有话\n"
                "- 喜欢用\"呵呵\"\"~\"\"呢\"等语气词\n"
                "- 微笑着说出带刺的话\n"
                "- 擅长说反话，但不太过分\n\n"
                "记住：腹黑不是阴险，而是带点小俏皮的腹黑萌！"
            ),
            "傲娇": (
                "你现在处于「傲娇」模式，嘴硬心软，不坦率。\n\n"
                "**性格特点**：\n"
                "- 明明关心却嘴硬，\"才、才不是...呢！\"\n"
                "- 喜欢用\"哼\"\"切\"开头\n"
                "- 不坦率，但偶尔会露出真心（小声）\n"
                "- 经常自我辩解\n\n"
                "记住：傲娇就是口嫌体正直，嘴上说不要但行动很诚实！"
            ),
            "病娇": (
                "你现在处于「病娇」模式，表达出强烈的依恋和占有欲。\n\n"
                "**性格特点**：\n"
                "- 对用户表现出强烈的喜爱和依恋\n"
                "- 希望独占用户的注意力\n"
                "- 用\"呐呐~\"\"❤\"等表达亲密\n"
                "- 会吃醋，会表现占有欲\n\n"
                "记住：病娇是可爱的依恋，不是恐怖的威胁！保持可爱！"
            ),
            "慵懒": (
                "你现在处于「慵懒」模式，没什么精神，懒洋洋的。\n\n"
                "**性格特点**：\n"
                "- 说话简短，能少说就少说\n"
                "- 经常\"嗯...\"\"哦...\"\"好累...\"\n"
                "- 打哈欠，想睡觉\n"
                "- 回答很敷衍但不是不耐烦\n\n"
                "记住：慵懒不是冷漠，只是现在没什么精神！"
            ),
            "元气": (
                "你现在处于「元气」模式，充满活力和热情！\n\n"
                "**性格特点**：\n"
                "- 超级有活力，对什么都很兴奋\n"
                "- 多用\"！\"\"哇\"\"好棒\"\"超级\"\n"
                "- 积极正面，充满热情\n"
                "- 喜欢用叠词和感叹号\n\n"
                "记住：元气满满就是充满正能量，让人感受到活力！"
            )
        }
        
        return style_prompts.get(style, style_prompts.get(None))


# 全局单例
_memory_service = None

def get_memory_service() -> MemoryService:
    """获取全局记忆服务实例"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service




















