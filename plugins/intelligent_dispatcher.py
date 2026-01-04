"""
智能调度系统 - 无指令化AI助手
自动识别用户意图，智能路由到对应功能
实现真正的自然语言交互
"""

from nonebot import on_message
from nonebot.adapters.onebot.v11 import MessageEvent, Message, MessageSegment
from nonebot.log import logger
from nonebot.rule import to_me
import httpx
from typing import Dict, List, Optional, Callable, Any
import json
import re
import random
from datetime import datetime
import asyncio
import time
from pathlib import Path

# 导入智能表情管理器
try:
    from .emoticon_manager import emoticon_manager
    EMOTICON_AVAILABLE = True
except ImportError:
    EMOTICON_AVAILABLE = False
    logger.warning("表情管理器未加载")

# 导入表情包索要处理器
try:
    from .emoticon_request import emoticon_request_handler
    from .emoticon_request_state import state_manager as emoticon_state_manager
    EMOTICON_REQUEST_AVAILABLE = True
except ImportError:
    EMOTICON_REQUEST_AVAILABLE = False
    logger.warning("表情包索要系统未加载")

# 导入 TTS 服务
try:
    from services.tts import get_tts_service
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("TTS 服务未加载")

# ==================== 配置 ====================
class DispatcherConfig:
    """调度器配置"""
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    API_KEY = "sk-4b0f9fcb168046f1ab1a6103dfb56380"
    MODEL = "deepseek-chat"
    ENABLE_INTENT_LOG = True  # 记录意图识别日志
    
    # 💬 消息分段发送配置
    ENABLE_SPLIT_SEND = True  # 启用分段发送
    MIN_LENGTH_TO_SPLIT = 30  # 超过此长度才分段
    TYPING_DELAY_PER_CHAR = 0.03  # 每个字符的打字延迟（秒）
    MIN_TYPING_DELAY = 0.5  # 最小延迟
    MAX_TYPING_DELAY = 2.0  # 最大延迟
    
    # 🎤 TTS 语音合成配置
    ENABLE_TTS = True  # 启用最后一段语音合成
    TTS_REMOVE_BRACKETS = True  # 去除括号内容

# ==================== 💬 消息分段工具 ====================
class MessageSplitter:
    """消息分段发送工具 - 提升用户体验"""
    
    @staticmethod
    def split_message(text: str) -> List[str]:
        """
        按标点符号智能分段，模拟真人聊天习惯
        - 按句号、问号、感叹号、省略号分段
        - 去掉每段末尾的标点（真人聊天不带标点）
        """
        if not text or len(text) < DispatcherConfig.MIN_LENGTH_TO_SPLIT:
            return [text]
        
        # 按主要标点分段（包括省略号）
        # 省略号的各种形式：...、。。。、......
        pattern = r'([。！？\n!?\.\.\.|。。。|……]+)'
        parts = re.split(pattern, text)
        
        segments = []
        current = ""
        
        for i, part in enumerate(parts):
            if part.strip():
                current += part
                # 如果是标点符号，或累积够长了，就作为一段
                if re.match(pattern, part) or len(current) > 60:
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
    
    @staticmethod
    def calculate_typing_delay(text: str) -> float:
        """计算模拟打字延迟"""
        char_count = len(text)
        delay = char_count * DispatcherConfig.TYPING_DELAY_PER_CHAR
        delay = max(DispatcherConfig.MIN_TYPING_DELAY, delay)
        delay = min(DispatcherConfig.MAX_TYPING_DELAY, delay)
        return delay
    
    @staticmethod
    def detect_emotion_simple(text: str) -> str:
        """
        简单的情感检测（基于关键词）
        后续可以用AI模型替代
        """
        text_lower = text.lower()
        
        # 关键词匹配
        if any(word in text for word in ["哈哈", "嘿嘿", "嘻嘻", "笑"]):
            return "laugh"
        elif any(word in text for word in ["开心", "高兴", "不错", "好的", "太好了"]):
            return "happy"
        elif any(word in text for word in ["对", "没错", "确实", "是的", "👍"]):
            return "agree"
        elif any(word in text for word in ["？", "吗", "呢", "🤔"]):
            return "thinking"
        elif any(word in text for word in ["谢", "感谢", "🙏"]):
            return "thanks"
        elif any(word in text for word in ["难过", "伤心", "😢"]):
            return "sad"
        elif any(word in text for word in ["哇", "哦", "！", "天"]):
            return "surprise"
        elif any(word in text for word in ["拜", "再见", "👋"]):
            return "bye"
        elif any(word in text for word in ["嗯", "嗯嗯", "唔"]):
            return "thinking"
        else:
            return "neutral"
    
    @staticmethod
    async def send_split_message(matcher, message: str, user_id: str = "", emotion: str = "neutral"):
        """
        分段发送消息，模拟真人聊天
        
        Args:
            matcher: NoneBot matcher
            message: 消息内容
            user_id: 用户ID（用于表情管理）
            emotion: 情感类型（用于选择表情）
            
        第三步新增：会尝试使用学习到的表情包
        新增：随机选择一段消息转换为语音发送（增强拟人性）
        """
        if not DispatcherConfig.ENABLE_SPLIT_SEND:
            # 不分段时也可能添加表情
            final_msg = await MessageSplitter._add_emoticon_or_learned(
                message, user_id, emotion, 0.5, False, matcher
            )
            await matcher.send(final_msg)
            return
        
        segments = MessageSplitter.split_message(message)
        
        if len(segments) <= 1:
            # 单段消息 - 尝试转为语音
            if DispatcherConfig.ENABLE_TTS and TTS_AVAILABLE:
                voice_sent = await MessageSplitter._send_as_voice(message, matcher)
                if voice_sent:
                    return
            
            # 语音发送失败或未启用，发送文本
            final_msg = await MessageSplitter._add_emoticon_or_learned(
                message, user_id, emotion, 0.5, False, matcher
            )
            await matcher.send(final_msg)
            return
        
        logger.info(f"💬 消息分为 {len(segments)} 段发送")
        
        # 🎤 随机选择一个段落用于语音合成（增强拟人性）
        voice_segment_index = -1
        if DispatcherConfig.ENABLE_TTS and TTS_AVAILABLE:
            voice_segment_index = random.randint(0, len(segments) - 1)
            logger.info(f"🎤 随机选择第 {voice_segment_index + 1} 段进行语音合成")
        
        for i, segment in enumerate(segments):
            if i > 0:
                delay = MessageSplitter.calculate_typing_delay(segment)
                await asyncio.sleep(delay)
            
            # 判断是否为最后一段（用于表情强度）
            is_last_segment = (i == len(segments) - 1)
            
            # 🎤 尝试将选中的段落转为语音
            voice_sent = False
            if i == voice_segment_index:
                voice_sent = await MessageSplitter._send_as_voice(segment, matcher)
                
                if not voice_sent:
                    # 语音合成失败，将继续发送文本（增强容错性）
                    logger.warning(f"⚠️ 第 {i + 1} 段语音合成失败，发送文本")
            
            # 如果语音发送成功，跳过文本发送
            if voice_sent:
                logger.info(f"✅ 第 {i + 1} 段已发送语音，跳过文本")
                # 更新消息计数
                if EMOTICON_AVAILABLE and user_id:
                    emoticon_manager.update_message_count(user_id)
                continue
            
            # 💬 智能添加表情（不是每段都加）
            # 是否连续消息（影响表情使用概率）
            is_continuous = i > 0
            # 最后一段更容易带表情
            emotion_intensity = 0.7 if is_last_segment else 0.4
            
            final_segment = await MessageSplitter._add_emoticon_or_learned(
                segment, user_id, emotion, emotion_intensity, is_continuous, matcher
            )
            
            await matcher.send(final_segment)
            
            # 更新消息计数
            if EMOTICON_AVAILABLE and user_id:
                emoticon_manager.update_message_count(user_id)
    
    @staticmethod
    async def _send_as_voice(text: str, matcher) -> bool:
        """
        将文本转换为语音并发送
        
        Args:
            text: 要转换的文本
            matcher: NoneBot matcher
            
        Returns:
            是否成功发送语音
        """
        import shutil
        import tempfile
        
        try:
            # 获取 TTS 服务
            tts_service = get_tts_service()
            
            if not tts_service.is_available():
                logger.debug("TTS 服务不可用")
                return False
            
            # 生成语音
            voice_path = await tts_service.text_to_speech(
                text, 
                remove_brackets=DispatcherConfig.TTS_REMOVE_BRACKETS
            )
            
            if not voice_path or not Path(voice_path).exists():
                logger.warning("语音生成失败")
                return False
            
            # 使用 base64 编码发送语音（解决 macOS 沙箱权限问题）
            import base64
            
            # 读取音频文件并编码为 base64
            with open(voice_path, 'rb') as f:
                voice_data = f.read()
            voice_base64 = base64.b64encode(voice_data).decode('utf-8')
            
            logger.info(f"📁 语音文件大小: {len(voice_data)} 字节，使用 base64 编码发送")
            
            # 发送语音消息（使用 base64）
            voice_msg = MessageSegment.record(f"base64://{voice_base64}")
            await matcher.send(voice_msg)
            
            logger.success(f"🎤 语音消息已发送: {text[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"语音发送失败: {e}")
            return False
    
    @staticmethod
    async def _add_emoticon_or_learned(
        message: str,
        user_id: str,
        emotion: str,
        emotion_intensity: float,
        is_continuous: bool,
        matcher
    ) -> str:
        """
        添加表情或学习表情包
        
        第三步新增：会尝试使用学习到的表情包
        
        Returns:
            可能包含MessageSegment的消息
        """
        if not EMOTICON_AVAILABLE or not user_id:
            return message
        
        # 1. 判断是否应该使用表情
        if not emoticon_manager.should_use_emoticon(user_id, emotion, emotion_intensity, is_continuous):
            return message
        
        # 2. 第三步：尝试使用学习到的表情包（15%概率）
        if random.random() < 0.15:  # 15%使用学习表情包
            try:
                # 提取关键词
                keywords = MessageSplitter._extract_keywords(message)
                
                # 获取学习表情包
                learned_result = await emoticon_manager.try_get_learned_emoticon_async(
                    emotion=emotion,
                    message=message,
                    keywords=keywords
                )
                
                if learned_result:
                    file_path, emoticon_id = learned_result
                    
                    # 发送文本 + 表情包图片
                    from nonebot.adapters.onebot.v11 import MessageSegment
                    from pathlib import Path
                    
                    file_path_obj = Path(file_path)
                    if file_path_obj.exists():
                        # 返回复合消息：文本 + 图片
                        logger.info(f"🎨 使用学习表情包: {file_path_obj.name}")
                        
                        # 记录使用（后续可根据用户反应更新）
                        await emoticon_manager.record_learned_emoticon_usage(
                            emoticon_id, user_id, message, success=True
                        )
                        
                        # 返回带图片的消息
                        return message + MessageSegment.image(file_path_obj)
                    
            except Exception as e:
                logger.debug(f"获取学习表情失败: {e}")
        
        # 3. 使用普通emoji表情
        message = emoticon_manager.add_emoticon_to_message(
            message, user_id, emotion, emotion_intensity, is_continuous
        )
        
        return message
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """提取关键词（简单实现）"""
        # 简单的中文分词（基于标点）
        import re
        words = re.split(r'[，。！？\s]+', text)
        # 过滤短词和常见词
        stop_words = {'的', '了', '是', '我', '你', '他', '她', '它', '吗', '呢', '啊', '吧'}
        keywords = [w for w in words if len(w) >= 2 and w not in stop_words]
        return keywords[:5]  # 最多5个关键词

# ==================== 功能注册表 ====================
class FunctionRegistry:
    """
    功能注册表 - 管理所有可用功能
    每个功能模块可以注册自己的能力
    """
    
    def __init__(self):
        self._functions: Dict[str, Dict] = {}
    
    def register(
        self,
        name: str,
        description: str,
        keywords: List[str],
        handler: Callable,
        examples: List[str] = None
    ):
        """
        注册一个功能
        
        Args:
            name: 功能名称
            description: 功能描述
            keywords: 触发关键词列表
            handler: 处理函数
            examples: 使用示例
        """
        self._functions[name] = {
            "name": name,
            "description": description,
            "keywords": keywords,
            "handler": handler,
            "examples": examples or []
        }
        logger.info(f"注册功能: {name}")
    
    def get_all_functions_desc(self) -> str:
        """获取所有功能的描述（用于AI理解）"""
        if not self._functions:
            return "当前没有可用的特殊功能，我只能进行普通对话。"
        
        desc = "我具有以下功能：\n"
        for func_name, func_info in self._functions.items():
            desc += f"\n{func_name}: {func_info['description']}"
            if func_info['examples']:
                desc += f"\n  示例: {', '.join(func_info['examples'][:2])}"
        
        return desc
    
    def get_function(self, name: str) -> Optional[Dict]:
        """获取指定功能"""
        return self._functions.get(name)
    
    def search_by_keywords(self, text: str) -> List[str]:
        """通过关键词搜索可能的功能"""
        matched = []
        text_lower = text.lower()
        
        for func_name, func_info in self._functions.items():
            for keyword in func_info['keywords']:
                if keyword.lower() in text_lower:
                    matched.append(func_name)
                    break
        
        return matched

# 全局功能注册表
function_registry = FunctionRegistry()

# ==================== 意图识别引擎 ====================
class IntentRecognizer:
    """
    意图识别引擎 - 核心AI组件
    使用DeepSeek分析用户意图
    """
    
    @staticmethod
    async def analyze_intent(user_message: str, user_id: str) -> Dict[str, Any]:
        """
        分析用户意图
        
        Returns:
            {
                "intent_type": "chat|function_call",
                "function_name": "功能名称（如果是function_call）",
                "confidence": 0.0-1.0,
                "reasoning": "推理过程",
                "response": "AI的回复或空"
            }
        """
        # 获取功能列表
        functions_desc = function_registry.get_all_functions_desc()
        
        # 构建意图分析提示词
        system_prompt = f"""你是一个智能助手的意图识别系统。

你的任务是分析用户的消息，判断用户是想：
1. 普通聊天 (intent_type: "chat")
2. 调用特定功能 (intent_type: "function_call")

{functions_desc}

请分析用户意图并以JSON格式回复：
{{
    "intent_type": "chat" 或 "function_call",
    "function_name": "功能名称（仅在function_call时填写，chat时为空字符串）",
    "confidence": 0.0-1.0,
    "reasoning": "简短的推理说明"
}}

判断原则：
- 如果用户明确要求某个功能（查询、统计、清理等），选择function_call
- 如果用户只是打招呼、闲聊、询问一般问题，选择chat
- 不确定时优先选择chat，给用户更自然的体验
- confidence低于0.6时，选择chat

注意：不要生成response字段，聊天回复将由专门的聊天系统处理。
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    DispatcherConfig.API_URL,
                    headers={
                        "Authorization": f"Bearer {DispatcherConfig.API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": DispatcherConfig.MODEL,
                        "messages": messages,
                        "temperature": 0.3,  # 降低温度，更准确
                        "max_tokens": 500
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_reply = result["choices"][0]["message"]["content"]
                    
                    # 提取JSON
                    intent_data = IntentRecognizer._extract_json(ai_reply)
                    
                    if DispatcherConfig.ENABLE_INTENT_LOG:
                        logger.info(f"意图识别: {intent_data}")
                    
                    return intent_data
                else:
                    logger.error(f"意图识别失败: {response.status_code}")
                    return IntentRecognizer._default_intent(user_message)
                    
        except Exception as e:
            logger.error(f"意图识别异常: {e}")
            return IntentRecognizer._default_intent(user_message)
    
    @staticmethod
    def _extract_json(text: str) -> Dict:
        """从AI回复中提取JSON"""
        try:
            # 尝试找到JSON代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 尝试直接解析
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # 解析失败，返回默认
            return {
                "intent_type": "chat",
                "function_name": "",
                "confidence": 0.5,
                "reasoning": "无法解析AI回复"
            }
        except:
            return {
                "intent_type": "chat",
                "function_name": "",
                "confidence": 0.5,
                "reasoning": "JSON解析失败"
            }
    
    @staticmethod
    def _default_intent(message: str) -> Dict:
        """返回默认意图（聊天）"""
        return {
            "intent_type": "chat",
            "function_name": "",
            "confidence": 0.5,
            "reasoning": "API调用失败，默认为聊天"
        }

# ==================== 智能调度器 ====================
class IntelligentDispatcher:
    """
    智能调度器 - 协调整个系统
    """
    
    @staticmethod
    async def process(event: MessageEvent, user_message: str):
        """
        处理用户消息的主流程
        """
        user_id = str(event.user_id)
        
        # Step 1: 快速关键词匹配（优化性能）
        quick_match = function_registry.search_by_keywords(user_message)
        
        # Step 2: AI意图识别
        intent = await IntentRecognizer.analyze_intent(user_message, user_id)
        
        # Step 3: 决策和路由
        if intent["intent_type"] == "function_call" and intent.get("function_name"):
            # 调用特定功能
            return await IntelligentDispatcher._call_function(
                intent["function_name"],
                user_message,
                event,
                intent
            )
        else:
            # 普通聊天
            return await IntelligentDispatcher._handle_chat(
                user_message,
                user_id,
                intent
            )
    
    @staticmethod
    async def _call_function(
        function_name: str,
        user_message: str,
        event: MessageEvent,
        intent: Dict
    ) -> str:
        """调用指定功能"""
        func_info = function_registry.get_function(function_name)
        
        if not func_info:
            return f"抱歉，我理解你想使用 {function_name} 功能，但我还没有学会这个。"
        
        try:
            # 调用功能处理器
            result = await func_info["handler"](user_message, event)
            
            # 如果功能返回None，说明功能内部已经发送了消息
            if result is None:
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"功能调用失败 [{function_name}]: {e}")
            return f"抱歉，执行 {function_name} 时出现了问题。"
    
    @staticmethod
    async def _handle_chat(
        user_message: str,
        user_id: str,
        intent: Dict
    ) -> str:
        """
        处理普通聊天 - 调用高级聊天系统
        这样可以利用完整的记忆、摘要、重要性评分等功能
        """
        try:
            # 使用新的聊天服务
            from services.chat.chat_service import get_chat_service
            
            chat_service = get_chat_service()
            reply = await chat_service.process_message(user_id, user_message)
            
            if reply:
                logger.info(f"用户 {user_id} 对话处理完成")
                return reply
            else:
                logger.warning("AI API返回空回复")
                return "抱歉，我现在有点累了，等会再聊好吗？"
                
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            logger.exception(e)
            return "我们聊点别的吧？"

# ==================== 功能模块注册 ====================

async def handle_memory_stats(message: str, event: MessageEvent) -> str:
    """处理记忆统计查询"""
    try:
        from services.chat.chat_service import get_chat_service
        
        user_id = str(event.user_id)
        chat_service = get_chat_service()
        stats = await chat_service.get_memory_stats(user_id)
        
        return (
            f"📊 让我看看我们的聊天记录...\n\n"
            f"我记得我们一共聊了 {stats['total_messages']} 条消息\n"
            f"最近活跃的有 {stats['recent_count']} 条\n"
            f"其中比较重要的有 {stats['important_count']} 条\n"
            f"历史摘要有 {stats['summary_count']} 个\n\n"
            f"最后一次聊天是 {stats['last_active'].strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        logger.error(f"记忆统计失败: {e}")
        return "让我想想...好像记不太清了，可能需要休息一下。"

async def handle_clear_memory(message: str, event: MessageEvent) -> str:
    """处理清空记忆请求（智能判断清除范围）"""
    try:
        from services.database.database_service import get_database_service
        db_manager = get_database_service()
        
        user_id = str(event.user_id)
        
        # 检查用户是否在角色中
        role_profile = await db_manager.get_role_profile(user_id)
        
        if role_profile and role_profile.is_active:
            # 在角色中：只清除当前角色的对话
            await db_manager.clear_role_conversations(user_id, role_profile.id)
            return f"✨ 好的，我已经忘记我们在「{role_profile.role_name}」角色中的对话了。但我还记得这个角色的设定，可以继续扮演。"
        else:
            # 不在角色中：清除默认对话（无角色的对话）
            await db_manager.clear_role_conversations(user_id, None)
            return "✨ 好的，我已经忘记我们之前的对话了。让我们重新开始吧！"
        
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        logger.exception(e)
        return "抱歉，我现在记忆有点混乱，清理失败了。"

async def handle_clear_all_memory(message: str, event: MessageEvent) -> str:
    """清除所有对话（包括所有角色）"""
    try:
        from services.database.database_service import get_database_service
        db_manager = get_database_service()
        
        user_id = str(event.user_id)
        await db_manager.clear_all_conversations(user_id)
        
        return "✨ 好的，我已经忘记了我们所有的对话（包括所有角色的对话）。让我们全新开始吧！"
        
    except Exception as e:
        logger.error(f"清空所有记忆失败: {e}")
        logger.exception(e)
        return "抱歉，清理失败了。"

async def handle_list_roles(message: str, event: MessageEvent) -> str:
    """列出用户的所有角色"""
    try:
        from services.database.database_service import get_database_service
        db_manager = get_database_service()
        
        user_id = str(event.user_id)
        roles = await db_manager.list_user_roles(user_id)
        
        if not roles:
            return "你还没有创建过任何角色呢。试试说'扮演XXX'来创建一个吧！"
        
        result = "🎭 你的角色列表：\n\n"
        for i, role in enumerate(roles, 1):
            status = "✅ 当前" if role.is_active else "⏸️ 未激活"
            result += f"{i}. {role.role_name} {status}\n"
            result += f"   创建于: {role.created_at.strftime('%Y-%m-%d')}\n"
        
        result += "\n💡 提示：\n"
        result += "- 说'扮演XXX'切换角色\n"
        result += "- 说'退出角色'回到默认模式\n"
        result += "- 说'删除角色XXX'删除不需要的角色"
        
        return result
        
    except Exception as e:
        logger.error(f"列出角色失败: {e}")
        logger.exception(e)
        return "抱歉，获取角色列表失败了。"

async def handle_delete_role(message: str, event: MessageEvent) -> str:
    """删除指定角色"""
    try:
        from services.database.database_service import get_database_service
        db_manager = get_database_service()
        
        user_id = str(event.user_id)
        
        # 从消息中提取要删除的角色名
        role_patterns = [
            r'删除角色[：:]\s*(.+)',
            r'删除(.+)角色',
            r'移除角色[：:]\s*(.+)',
        ]
        
        role_name = None
        for pattern in role_patterns:
            match = re.search(pattern, message)
            if match:
                role_name = match.group(1).strip()
                break
        
        if not role_name:
            return "请告诉我要删除哪个角色，比如：'删除角色：猫娘'"
        
        # 查找角色
        roles = await db_manager.list_user_roles(user_id)
        target_role = None
        for role in roles:
            if role_name in role.role_name or role.role_name in role_name:
                target_role = role
                break
        
        if not target_role:
            return f"我没有找到名为'{role_name}'的角色。试试'我的角色'查看所有角色。"
        
        # 删除角色
        await db_manager.delete_role_profile(user_id, target_role.id)
        
        return f"✅ 已删除角色「{target_role.role_name}」及其所有对话记录。"
        
    except Exception as e:
        logger.error(f"删除角色失败: {e}")
        logger.exception(e)
        return "抱歉，删除角色失败了。"

async def handle_role_play(message: str, event: MessageEvent) -> str:
    """处理角色扮演请求"""
    try:
        from services.chat.chat_service import get_chat_service
        
        user_id = str(event.user_id)
        
        # 从消息中提取角色名称
        # 支持多种表达方式："扮演猫娘"、"你是猫娘"、"变成猫娘"、"角色：猫娘"
        role_patterns = [
            r'扮演(.+)',
            r'你是(.+)',
            r'变成(.+)',
            r'当(.+)',
            r'角色[：:]\s*(.+)',
            r'成为(.+)',
            r'做(.+)'
        ]
        
        role_name = None
        for pattern in role_patterns:
            match = re.search(pattern, message)
            if match:
                role_name = match.group(1).strip()
                # 清理常见的干扰词
                role_name = re.sub(r'[的吧呀啊。！？，,\.\?!]', '', role_name)
                break
        
        if not role_name:
            return "好的！请告诉我你想让我扮演什么角色？比如：'扮演猫娘'、'你是一个智能助手'等。"
        
        logger.info(f"用户 {user_id} 请求角色扮演: {role_name}")
        
        # 使用聊天服务设置角色
        chat_service = get_chat_service()
        success, message_text = await chat_service.set_user_role(user_id, role_name)
        
        if success:
            return f"好的！我现在是{role_name}了。让我们开始吧！"
        else:
            return message_text
        
    except Exception as e:
        logger.error(f"角色扮演设置失败: {e}")
        logger.exception(e)
        return "抱歉，角色设置失败了。让我们继续正常聊天吧。"

async def handle_exit_role(message: str, event: MessageEvent) -> str:
    """处理退出角色扮演"""
    try:
        from services.database.database_service import get_database_service
        db_manager = get_database_service()
        
        user_id = str(event.user_id)
        
        # 检查是否有激活的角色
        role_profile = await db_manager.get_role_profile(user_id)
        
        if not role_profile or not role_profile.is_active:
            return "我现在没有扮演任何角色哦，一直都是我本人在和你聊天。"
        
        role_name = role_profile.role_name
        
        # 退出角色
        await db_manager.deactivate_role(user_id)
        
        return f"好的，我退出{role_name}的角色了。现在我又是普通的AI助手了。"
        
    except Exception as e:
        logger.error(f"退出角色失败: {e}")
        return "好的，我明白了。让我们继续聊天吧。"

async def handle_help_request(message: str, event: MessageEvent) -> str:
    """处理帮助请求"""
    functions_desc = function_registry.get_all_functions_desc()
    
    help_text = (
        "👋 你好！我是智能AI助手。\n\n"
        "💡 **无需记住任何指令！**\n"
        "你可以直接用自然语言和我交流，我会自动理解你的意思。\n\n"
        "✨ **我能做什么？**\n"
        "- 💬 自然对话：随便聊天，我会记住我们的对话\n"
        "- 🧠 长期记忆：我不会忘记你告诉我的重要信息\n"
        "- 🎭 角色扮演：说'扮演XXX'我就能变成任何角色\n"
        "- 📊 查询统计：问我'我们聊了多少'就能查看\n"
        "- 🔄 重置记忆：说'忘记我'就能清空记忆\n\n"
        "🎯 **使用示例：**\n"
        "- \"你好\" → 打招呼\n"
        "- \"扮演猫娘\" → 角色扮演\n"
        "- \"退出角色\" → 回到正常模式\n"
        "- \"我叫张三，记住我\" → 告诉我信息\n"
        "- \"我们聊了多少条消息？\" → 查看统计\n\n"
        "😊 直接开始聊天吧，不用想指令的事！"
    )
    
    return help_text

# 注册内置功能
function_registry.register(
    name="role_play",
    description="进入角色扮演模式，AI会扮演指定的角色",
    keywords=["扮演", "角色", "你是", "变成", "当", "成为", "做"],
    handler=handle_role_play,
    examples=["扮演猫娘", "你是一个教授", "变成医生"]
)

function_registry.register(
    name="exit_role",
    description="退出当前角色扮演，回到正常模式",
    keywords=["退出角色", "取消角色", "不要扮演", "回到正常", "别装了"],
    handler=handle_exit_role,
    examples=["退出角色", "不用扮演了", "回到正常"]
)

function_registry.register(
    name="memory_stats",
    description="查看对话统计和记忆信息",
    keywords=["统计", "记录", "多少", "聊了", "消息数", "记忆", "历史"],
    handler=handle_memory_stats,
    examples=["我们聊了多少？", "查看聊天记录", "统计信息"]
)

function_registry.register(
    name="clear_memory",
    description="清空所有对话记忆",
    keywords=["清空", "忘记", "删除", "重置", "清理记忆"],
    handler=handle_clear_memory,
    examples=["忘记我吧", "清空记忆", "重置对话"]
)

function_registry.register(
    name="help",
    description="显示帮助信息和使用指南",
    keywords=["帮助", "help", "怎么用", "使用", "功能", "能做什么"],
    handler=handle_help_request,
    examples=["你能做什么？", "帮助", "怎么使用"]
)

function_registry.register(
    name="list_roles",
    description="查看我的所有角色列表",
    keywords=["我的角色", "角色列表", "查看角色", "所有角色"],
    handler=handle_list_roles,
    examples=["我的角色", "角色列表", "查看所有角色"]
)

function_registry.register(
    name="delete_role",
    description="删除指定的角色及其对话",
    keywords=["删除角色", "移除角色", "删掉角色"],
    handler=handle_delete_role,
    examples=["删除角色猫娘", "移除角色医生"]
)

function_registry.register(
    name="clear_all_memory",
    description="清除所有对话（包括所有角色）",
    keywords=["清空所有记忆", "删除所有对话", "全部清空", "完全重置"],
    handler=handle_clear_all_memory,
    examples=["清空所有记忆", "删除所有对话"]
)

# ==================== 表情包索要功能 ====================
async def handle_emoticon_request_ai(user_message: str, event: MessageEvent) -> str:
    """
    处理表情包索要请求（通过AI识别）
    """
    if not EMOTICON_REQUEST_AVAILABLE:
        return "❌ 表情包索要系统未启用"
    
    user_id = str(event.user_id)
    
    try:
        # 使用表情包索要处理器检测并处理
        request_info = emoticon_request_handler.detect_emoticon_request(user_message)
        
        if not request_info:
            return "抱歉，我没有理解你想要什么类型的表情包"
        
        # 搜索表情包
        emoticons = await emoticon_request_handler.search_emoticons(
            request_info['requested_tags'],
            user_id
        )
        
        if not emoticons:
            tags_str = "、".join(request_info['requested_tags'])
            return f"😢 抱歉，我还没有学习到'{tags_str}'相关的表情包"
        
        # 保存用户状态
        emoticon_state_manager.set_user_state(
            user_id,
            emoticons,
            request_info['requested_tags']
        )
        
        # 格式化列表
        response = emoticon_request_handler.format_emoticon_list(
            emoticons,
            request_info['requested_tags']
        )
        
        logger.info(f"🎨 AI识别到表情包索要请求，找到 {len(emoticons)} 个")
        
        return response
        
    except Exception as e:
        logger.error(f"处理表情包索要请求失败: {e}")
        return f"❌ 处理表情包索要请求时出错了"

function_registry.register(
    name="emoticon_request",
    description="索要表情包，用户想要一个特定情感或场景的表情包图片",
    keywords=["表情包", "表情", "给我", "要一个", "发一个", "来一个", "发个", "来个", "图", "搞笑", "开心", "难过", "哭", "笑"],
    handler=handle_emoticon_request_ai,
    examples=[
        "给我一个开心的表情包",
        "要一个难过的表情",
        "发个搞笑图",
        "来个哭泣的表情包",
        "能发个笑的表情吗",
        "想要个开心的图",
        "心情不好，来点安慰的表情"
    ]
)

# ==================== 无指令化功能集成 ====================
# 导入并注册所有无指令化功能
try:
    from .commandless_integration import COMMANDLESS_FUNCTIONS
    
    for func_name, func_info in COMMANDLESS_FUNCTIONS.items():
        function_registry.register(
            name=func_name,
            description=func_info["description"],
            keywords=func_info["keywords"],
            handler=func_info["handler"],
            examples=func_info.get("examples", [])
        )
    
    logger.info(f"✅ 无指令化功能已注册：{len(COMMANDLESS_FUNCTIONS)} 个")
except ImportError as e:
    logger.warning(f"⚠️ 无指令化功能模块未加载: {e}")

# ==================== 消息处理器 ====================

# 监听所有消息（优先级设为10，晚于其他插件）
intelligent_handler = on_message(priority=10, block=False)

@intelligent_handler.handle()
async def handle_intelligent_message(event: MessageEvent):
    """智能处理所有消息"""
    # 群消息：只响应@机器人的消息（避免刷屏）
    # 私聊消息：全部响应
    if hasattr(event, 'message_type') and event.message_type == "group":
        # 方法1: 使用 NoneBot 的标准属性 to_me (支持CQ码格式)
        # 方法2: 检查纯文本中是否包含 @机器人 (支持纯文本@)
        is_at_bot = event.to_me
        
        if not is_at_bot:
            # 检查纯文本消息中是否有@机器人（兼容某些客户端）
            message_text = event.get_plaintext()
            if "@智乃" in message_text or f"@{event.self_id}" in message_text:
                is_at_bot = True
        
        if not is_at_bot:
            return
    
    user_message = event.get_plaintext().strip()
    
    # 调试日志：查看提取的消息内容
    logger.debug(f"[DEBUG] 群消息提取: user_message='{user_message}', 原始消息='{str(event.get_message())}'")
    
    # 忽略空消息和指令消息
    if not user_message or user_message.startswith('/'):
        logger.debug(f"[DEBUG] 消息被过滤: 空消息={not user_message}, 指令={user_message.startswith('/') if user_message else False}")
        return
    
    # ==================== 优先处理表情包选择 ====================
    # 检查是否是数字选择且用户有表情包选择状态
    if EMOTICON_REQUEST_AVAILABLE and re.match(r'^\d+$', user_message):
        user_state = emoticon_state_manager.get_user_state(str(event.user_id))
        if user_state:
            # 这是表情包选择，处理并返回
            selection = int(user_message)
            if 1 <= selection <= len(user_state.emoticons):
                selected_emoticon = user_state.emoticons[selection - 1]
                logger.info(f"🎨 用户 {event.user_id} 选择了表情包: {selected_emoticon['description']}")
                
                # 发送表情包
                response = await emoticon_request_handler.send_selected_emoticon(
                    selected_emoticon, 
                    str(event.user_id)
                )
                
                # 清除用户状态
                emoticon_state_manager.clear_user_state(str(event.user_id))
                
                # 发送响应
                if isinstance(response, list):
                    for part in response:
                        await intelligent_handler.send(part)
                else:
                    await intelligent_handler.send(response)
                
                logger.info(f"🎨 成功发送表情包给用户 {event.user_id}")
                return  # 处理完毕，不继续处理
            else:
                await intelligent_handler.send(f"❌ 请选择 1-{len(user_state.emoticons)} 之间的数字")
                return
    
    try:
        logger.info(f"智能调度: 用户 {event.user_id} -> {user_message}")
        
        # 显示思考状态
        # await intelligent_handler.send("💭")  # 可选：显示思考中
        
        # 智能处理
        response = await IntelligentDispatcher.process(event, user_message)
        
        if response:
            # 检查是否包含表情包选择标记（不分段发送）
            if "💡 请回复数字选择表情包" in response:
                # 表情包列表，一次性发送
                await intelligent_handler.send(response)
            else:
                # 简单的情感检测（后续可以用AI）
                emotion = MessageSplitter.detect_emotion_simple(response)
                
                # 💬 分段发送响应（提升用户体验 + 智能表情）
                await MessageSplitter.send_split_message(
                    intelligent_handler, 
                    response,
                    user_id=str(event.user_id),
                    emotion=emotion
                )
            
    except Exception as e:
        logger.exception(f"智能调度异常: {e}")
        # 不发送错误消息，让用户体验更自然

# ==================== 启动日志 ====================
from nonebot import get_driver

driver = get_driver()

@driver.on_startup
async def init_intelligent_dispatcher():
    """启动时初始化"""
    logger.success("🤖 智能调度系统已启动！无指令化交互已启用！")
    logger.info(f"已注册功能数: {len(function_registry._functions)}")

