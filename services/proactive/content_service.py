"""
主动聊天内容生成服务 - Content Service
负责生成自然的主动聊天开场白
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import random
from nonebot.log import logger

from utils.ai_clients.deepseek_client import get_deepseek_client
from services.emotion import get_emotion_service
from services.database.database_service import get_database_service
from services.proactive.proactive_config import ProactiveConfig


class ContentService:
    """主动聊天内容生成服务"""
    
    def __init__(self):
        self.ai_client = get_deepseek_client()
        self.emotion_service = get_emotion_service()
        self.db_service = get_database_service()
    
    async def generate_opening(
        self, 
        user_id: str, 
        emotion_state: Dict,
        reason: str
    ) -> Tuple[str, str]:
        """
        生成自然的开场白
        
        Args:
            user_id: 用户ID
            emotion_state: 情感状态
            reason: 主动聊天的原因
        
        Returns:
            (开场白文本, 策略类型)
        
        策略类型:
        - topic_continuation: 延续之前的话题
        - share_discovery: 分享有趣的发现
        - check_status: 关心用户状态
        - time_based: 基于时间的问候
        - casual_chat: 轻松闲聊
        """
        try:
            # 获取用户当前激活的角色
            role_profile = await self.db_service.get_role_profile(user_id)
            
            # 获取情感风格
            emotion_style = await self.emotion_service.get_emotion_influenced_style(user_id)
            
            # 检查是否体力不足(需要休息)
            if emotion_style.get('be_resting'):
                # 体力不足时,简短表示累了
                return await self._generate_rest_message(emotion_state), "rest"
            
            # 选择策略
            strategy = self._select_strategy()
            
            # 构建提示
            prompt = await self._build_opening_prompt(
                user_id, strategy, emotion_state, role_profile
            )
            
            # 调用AI生成
            opening = await self._call_ai_for_opening(prompt)
            
            return opening, strategy
            
        except Exception as e:
            logger.error(f"生成开场白失败: {e}")
            return self._get_fallback_opening(), "fallback"
    
    def _select_strategy(self) -> str:
        """选择开场白策略"""
        strategies = []
        
        # 30%概率延续话题
        if random.random() < 0.3:
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
        
        # 默认:轻松闲聊
        if not strategies:
            strategies.append("casual_chat")
        
        return random.choice(strategies)
    
    async def _build_opening_prompt(
        self,
        user_id: str,
        strategy: str,
        emotion_state: Dict,
        role_profile = None
    ) -> str:
        """构建开场白生成提示"""
        current_hour = datetime.now().hour
        
        # 获取情感档案
        profile = await self.emotion_service.get_or_create_profile(user_id)
        intimacy_level = profile.intimacy_level
        
        # 暂时注释掉历史记录功能，因为数据库服务没有相应方法
        recent_history = []
        
        # 如果有激活的角色,使用角色人设
        if role_profile and role_profile.is_active:
            base_prompt = f"""🎭 重要:你正在扮演一个角色,必须严格保持角色设定!

【角色设定】
角色名称:{role_profile.role_name}
角色人设:{role_profile.role_prompt}

【任务】
现在要以这个角色的身份主动找朋友聊天。

【场景信息】
当前时间:{current_hour}点
聊天对象:一位朋友(用户)
亲密度:{intimacy_level:.2f}(0到1,越高越亲密)

【当前情感状态】
心情:{emotion_state.get('mood', 'neutral')}
快乐值:{emotion_state.get('happiness', 50):.1f}
寂寞值:{emotion_state.get('loneliness', 50):.1f}
体力值:{emotion_state.get('energy', 50):.1f}
自信值:{emotion_state.get('confidence', 50):.1f}

⚠️ 关键要求:
1. 必须完全以角色的语气、性格、说话方式来生成开场白
2. 不要说"我在扮演"或提及角色设定本身
3. 就像这个角色真的想主动找朋友聊天一样自然
4. 根据情感状态调整语气和内容

"""
        else:
            # 没有角色时,使用正常人设
            base_prompt = f"""你是一个非常懂得社交的真人,现在要主动找朋友聊天。

【场景信息】
当前时间:{current_hour}点
聊天对象:一位朋友
亲密度:{intimacy_level:.2f}(0到1,越高越亲密)

【当前情感状态】
心情:{emotion_state.get('mood', 'neutral')}
快乐值:{emotion_state.get('happiness', 50):.1f}
寂寞值:{emotion_state.get('loneliness', 50):.1f}
体力值:{emotion_state.get('energy', 50):.1f}
自信值:{emotion_state.get('confidence', 50):.1f}

"""
        
        # 策略提示
        # 构建topic_continuation策略的提示，包含历史记录
        topic_continuation_prompt = """策略:延续之前聊过的话题

要求:
1. 自然地提起之前聊过的内容
2. 加入新的角度或想法
3. 语气轻松,不要太刻意
4. 字数控制在20-40字
"""
        
        # 如果有历史聊天记录，添加到提示中
        if recent_history:
            history_text = "\n【历史聊天记录】\n"
            for i, msg in enumerate(reversed(recent_history)):  # 倒序显示，最近的在前面
                sender = "你" if msg.get('role') == 'assistant' else "对方"
                content = msg.get('content', '').strip()
                if content:
                    history_text += f"{sender}: {content}\n"
            topic_continuation_prompt += history_text
        else:
            topic_continuation_prompt += "\n【注意】没有找到历史聊天记录，选择其他话题开场\n\n"
        
        strategy_prompts = {
            "topic_continuation": topic_continuation_prompt,
            "share_discovery": """策略:分享有趣的发现或想法

要求:
1. 分享一个有趣的观察、想法或最近看到的内容
2. 可以是生活小事、网上看到的、突然的想法
3. 语气兴奋但不夸张
4. 自然地邀请对方参与讨论
5. 字数控制在25-45字
""",
            "check_status": """策略:关心朋友近况

要求:
1. 真诚地询问对方最近怎么样
2. 可以提到一些具体方面(工作、生活、心情等)
3. 语气温暖但不过分热情
4. 避免"好久不见"这种生硬开场
5. 字数控制在15-30字
""",
            "time_based": f"""策略:基于时间的问候

当前时段:{current_hour}点

要求:
1. 根据时间自然地打招呼(早/中/晚)
2. 结合这个时段的场景(早餐、午休、晚上等)
3. 轻松随意,像日常聊天
4. 字数控制在15-30字
""",
            "casual_chat": """策略:轻松闲聊开场

要求:
1. 非常随意自然的开场
2. 可以是emoji、口语化表达
3. 不要问太严肃的问题
4. 营造轻松氛围
5. 字数控制在10-25字
"""
        }
        
        prompt = base_prompt + strategy_prompts.get(strategy, strategy_prompts["casual_chat"])
        
        # 对于time_based策略，添加时间检查避免重复早安
        if strategy == "time_based" and recent_history:
            prompt += "\n【特别注意】检查历史记录，避免重复发送类似的时间问候(如早安、午安等)\n\n"
        
        prompt += """

注意事项:
- 必须是中文
- 像真人聊天,口语化
- 可以用emoji,但不要太多(最多1-2个)
- 不要太正式,不要用"您"
- 不要说教或给建议(除非必要)
- 语气要自然,不做作

直接输出开场白,不要有任何前缀或解释:"""
        
        return prompt
    
    async def _call_ai_for_opening(self, prompt: str) -> str:
        """调用AI生成开场白"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = await self.ai_client.chat(
                messages,
                temperature=ProactiveConfig.TEMPERATURE,
                max_tokens=200,
                timeout=30
            )
            
            if response:
                # 移除可能的引号
                opening = response.strip().strip('"\'「」『』')
                return opening
            else:
                logger.warning("AI返回空响应,使用备用开场白")
                return self._get_fallback_opening()
                
        except Exception as e:
            logger.error(f"调用AI失败: {e}")
            return self._get_fallback_opening()
    
    async def _generate_rest_message(self, emotion_state: Dict) -> str:
        """生成休息消息(体力不足时)"""
        rest_messages = [
            f"有点累了...体力只剩{emotion_state.get('energy', 50):.0f}了",
            "今天好累啊,想休息一下",
            "感觉有点疲惫,需要歇会儿",
            "体力不足了,改天再聊吧",
            "累了,先休息一下"
        ]
        return random.choice(rest_messages)
    
    def _get_fallback_opening(self) -> str:
        """备用开场白库"""
        openings = [
            "在吗?好久没聊天了",
            "突然想起你,最近怎么样呀",
            "嗨~有空聊聊吗",
            "分享个有趣的事儿~",
            "最近在忙啥呢",
            "好久不见啦!",
            "突然想找你聊聊天",
            "有个想法想跟你说说"
        ]
        return random.choice(openings)


# ==================== 全局单例 ====================
_content_service: Optional[ContentService] = None

def get_content_service() -> ContentService:
    """获取内容生成服务单例"""
    global _content_service
    if _content_service is None:
        _content_service = ContentService()
    return _content_service























