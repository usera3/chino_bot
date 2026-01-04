"""
智能表情包索要系统
功能：用户可以直接向Bot索要特定类型的表情包
"""

from nonebot import on_message, get_driver
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Message
from nonebot.log import logger
from nonebot.rule import to_me
from typing import Dict, List, Optional, Tuple
import json
import re
from pathlib import Path

# 导入表情包学习器和状态管理器
try:
    from .emoticon_learner import emoticon_learner
    from .emoticon_request_state import state_manager
    EMOTICON_LEARNER_AVAILABLE = True
except ImportError:
    EMOTICON_LEARNER_AVAILABLE = False
    logger.warning("表情包学习器不可用")

# ==================== 配置 ====================
class RequestConfig:
    """表情包索要配置"""
    MAX_RESULTS = 5  # 最多返回5个表情包
    MIN_CONFIDENCE = 0.3  # 最小匹配置信度
    ENABLE_SMART_MATCH = True  # 启用智能匹配

# ==================== 表情包索要处理器 ====================

class EmoticonRequestHandler:
    """表情包索要处理器"""
    
    def __init__(self):
        self.request_patterns = {
            # 情感类
            "happy": ["开心", "高兴", "快乐", "笑", "哈哈", "开心", "happy", "laugh"],
            "sad": ["哭", "难过", "伤心", "悲伤", "cry", "sad", "难过"],
            "angry": ["生气", "愤怒", "angry", "mad", "气"],
            "excited": ["兴奋", "激动", "excited", "激动"],
            "thinking": ["思考", "想", "thinking", "考虑"],
            "surprise": ["惊讶", "震惊", "surprise", "惊讶"],
            "love": ["爱", "喜欢", "love", "喜欢"],
            "thanks": ["感谢", "谢谢", "thanks", "thank"],
            "bye": ["再见", "拜拜", "bye", "goodbye"],
            "greeting": ["你好", "嗨", "hello", "hi", "问候"],
            
            # 场景类
            "chat": ["聊天", "对话", "chat", "聊天"],
            "comfort": ["安慰", "安慰", "comfort", "安慰"],
            "congratulation": ["恭喜", "祝贺", "congratulation", "恭喜"],
            "joke": ["搞笑", "笑话", "joke", "搞笑"],
            "celebration": ["庆祝", "庆祝", "celebration", "庆祝"],
        }
        
        # 反向映射：从中文到英文标签
        self.chinese_to_english = {}
        for eng_tag, chinese_list in self.request_patterns.items():
            for chinese in chinese_list:
                if chinese not in self.chinese_to_english:
                    self.chinese_to_english[chinese] = []
                self.chinese_to_english[chinese].append(eng_tag)
    
    def detect_emoticon_request(self, message: str) -> Optional[Dict]:
        """
        检测用户是否在索要表情包
        
        Returns:
            {
                "is_request": True,
                "requested_tags": ["happy", "laugh"],
                "confidence": 0.8,
                "original_message": "给我一个开心的表情包"
            }
        """
        message_lower = message.lower()
        
        # 索要表情包的关键词
        request_keywords = [
            "给我", "要一个", "发一个", "来一个", "表情包", "表情",
            "给我一个", "要个", "发个", "来个", "想要", "需要"
        ]
        
        # 检查是否包含索要关键词
        has_request_keyword = any(keyword in message for keyword in request_keywords)
        
        if not has_request_keyword:
            return None
        
        # 提取请求的情感/场景标签
        requested_tags = []
        confidence = 0.5  # 基础置信度
        
        # 匹配情感标签
        for chinese, english_tags in self.chinese_to_english.items():
            if chinese in message:
                requested_tags.extend(english_tags)
                confidence += 0.2
        
        # 如果没有找到具体标签，尝试从上下文推断
        if not requested_tags:
            # 检查是否有情感词汇
            emotion_words = ["开心", "难过", "生气", "兴奋", "惊讶", "爱", "感谢", "再见", "你好"]
            for word in emotion_words:
                if word in message:
                    if word in self.chinese_to_english:
                        requested_tags.extend(self.chinese_to_english[word])
                        confidence += 0.1
        
        # 如果还是没有找到，使用通用标签
        if not requested_tags:
            requested_tags = ["chat", "greeting"]
            confidence = 0.3
        
        return {
            "is_request": True,
            "requested_tags": list(set(requested_tags)),  # 去重
            "confidence": min(confidence, 1.0),
            "original_message": message
        }
    
    async def search_emoticons(self, tags: List[str], user_id: str) -> List[Dict]:
        """
        搜索匹配的表情包
        
        Returns:
            [
                {
                    "id": 1,
                    "file_path": "./emoticons/xxx.jpg",
                    "emotion_tags": ["happy", "laugh"],
                    "scene_tags": ["chat"],
                    "keywords": ["开心", "笑"],
                    "description": "一个开心的表情包",
                    "match_score": 0.9
                }
            ]
        """
        if not EMOTICON_LEARNER_AVAILABLE:
            logger.warning("表情包学习器不可用，无法搜索表情包")
            return []
        
        try:
            # 获取所有表情包
            all_emoticons = await emoticon_learner.get_emoticons_list()
            
            if not all_emoticons:
                logger.info("没有找到任何表情包")
                return []
            
            # 计算匹配分数
            matched_emoticons = []
            
            for emoticon in all_emoticons:
                if not emoticon.get('is_active', True):
                    continue
                
                # 解析标签
                emotion_tags = json.loads(emoticon.get('emotion_tags', '[]'))
                scene_tags = json.loads(emoticon.get('scene_tags', '[]'))
                keywords = json.loads(emoticon.get('keywords', '[]'))
                
                # 计算匹配分数
                match_score = 0.0
                
                # 情感标签匹配
                for tag in tags:
                    if tag in emotion_tags:
                        match_score += 0.4
                    if tag in scene_tags:
                        match_score += 0.3
                
                # 关键词匹配
                for tag in tags:
                    for keyword in keywords:
                        if tag in keyword or keyword in tag:
                            match_score += 0.2
                
                # 如果匹配分数足够高，添加到结果
                if match_score >= RequestConfig.MIN_CONFIDENCE:
                    matched_emoticons.append({
                        "id": emoticon['id'],
                        "file_path": emoticon['file_path'],
                        "emotion_tags": emotion_tags,
                        "scene_tags": scene_tags,
                        "keywords": keywords,
                        "description": emoticon.get('description', '表情包'),
                        "match_score": match_score
                    })
            
            # 按匹配分数排序
            matched_emoticons.sort(key=lambda x: x['match_score'], reverse=True)
            
            # 返回前N个结果
            return matched_emoticons[:RequestConfig.MAX_RESULTS]
            
        except Exception as e:
            logger.error(f"搜索表情包失败: {e}")
            return []
    
    def format_emoticon_list(self, emoticons: List[Dict], requested_tags: List[str]) -> str:
        """
        格式化表情包列表为可选择的格式
        """
        if not emoticons:
            return "😔 抱歉，没有找到匹配的表情包。你可以尝试其他关键词，比如：开心、难过、生气、感谢等。"
        
        # 构建回复消息
        message_parts = []
        
        # 标题
        tag_names = {
            "happy": "开心", "sad": "难过", "angry": "生气", "excited": "兴奋",
            "thinking": "思考", "surprise": "惊讶", "love": "爱", "thanks": "感谢",
            "bye": "再见", "greeting": "问候", "chat": "聊天", "comfort": "安慰",
            "congratulation": "恭喜", "joke": "搞笑", "celebration": "庆祝"
        }
        
        requested_names = [tag_names.get(tag, tag) for tag in requested_tags]
        message_parts.append(f"🎨 找到 {len(emoticons)} 个{'+'.join(requested_names)}表情包：")
        message_parts.append("")
        
        # 表情包列表
        for i, emoticon in enumerate(emoticons, 1):
            # 表情包信息
            info_parts = []
            
            # 情感标签
            if emoticon['emotion_tags']:
                emotion_names = [tag_names.get(tag, tag) for tag in emoticon['emotion_tags']]
                info_parts.append(f"情感: {', '.join(emotion_names)}")
            
            # 关键词
            if emoticon['keywords']:
                info_parts.append(f"关键词: {', '.join(emoticon['keywords'][:3])}")
            
            # 描述
            description = emoticon['description'][:50] + "..." if len(emoticon['description']) > 50 else emoticon['description']
            
            message_parts.append(f"{i}. {description}")
            if info_parts:
                message_parts.append(f"   ({'; '.join(info_parts)})")
            message_parts.append("")
        
        # 选择提示
        message_parts.append("💡 请回复数字选择表情包（如：1、2、3...）")
        
        return "\n".join(message_parts)
    
    async def send_selected_emoticon(self, emoticon: Dict, user_id: str) -> str:
        """
        发送选中的表情包
        """
        try:
            file_path = Path(emoticon['file_path'])
            
            if not file_path.exists():
                return f"❌ 表情包文件不存在: {file_path.name}"
            
            # 构建消息
            message_parts = []
            message_parts.append(f"🎨 为你发送表情包：{emoticon['description']}")
            
            # 尝试使用Base64编码发送（解决权限问题）
            try:
                import base64
                
                # 读取文件内容并转换为base64
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                
                # 转换为base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                logger.info(f"📁 使用Base64编码发送表情包 ({len(image_base64)} 字符)")
                
                # 使用base64发送
                image_segment = MessageSegment.image(f"base64://{image_base64}")
                message_parts.append(image_segment)
                
            except Exception as e:
                logger.error(f"Base64编码失败: {e}")
                # 如果Base64失败，尝试直接发送
                try:
                    image_segment = MessageSegment.image(str(file_path.absolute()))
                    message_parts.append(image_segment)
                except Exception as e2:
                    logger.error(f"直接发送图片失败: {e2}")
                    # 如果都失败了，返回文件信息
                    message_parts.append(f"📁 表情包文件: {file_path.name}")
                    message_parts.append(f"📂 路径: {file_path}")
                    message_parts.append(f"💡 提示: 文件存在但无法发送，可能是权限问题")
            
            return message_parts
            
        except Exception as e:
            logger.error(f"发送表情包失败: {e}")
            return f"❌ 发送表情包失败: {str(e)}"

# 全局处理器实例
emoticon_request_handler = EmoticonRequestHandler()

# ==================== 消息监听 ====================

# ==================== 注意 ====================
# 表情包索要功能已集成到智能调度器的AI意图识别系统
# 以下独立处理器已禁用，所有请求统一由AI识别处理
# 如需启用独立关键词匹配，请取消注释
# ==========================================

# # 监听所有消息（优先级高，用于检测索要请求）
# # block=False: 不自动阻断，在处理完成后手动决定是否继续传递
# # 优先级3: 高于选择处理器(5)，优先判断是否是索要请求
# request_listener = on_message(priority=3, block=False)

# @request_listener.handle()
async def handle_emoticon_request_legacy(bot, event: MessageEvent):
    """
    处理表情包索要请求
    """
    if not EMOTICON_LEARNER_AVAILABLE:
        return  # 直接return，消息继续传递
    
    # 只处理私聊
    if hasattr(event, 'group_id') and event.group_id:
        return  # 直接return，消息继续传递
    
    # 获取消息内容
    message_text = event.get_plaintext().strip()
    if not message_text:
        return  # 直接return，消息继续传递
    
    # 检测是否是索要请求
    request_info = emoticon_request_handler.detect_emoticon_request(message_text)
    if not request_info:
        return  # 不是索要请求，消息继续传递
    
    logger.info(f"🎨 检测到表情包索要请求: {message_text}")
    logger.info(f"🎯 请求标签: {request_info['requested_tags']}")
    
    # 搜索表情包
    emoticons = await emoticon_request_handler.search_emoticons(
        request_info['requested_tags'], 
        str(event.user_id)
    )
    
    # 设置用户状态
    state_manager.set_user_state(
        str(event.user_id),
        emoticons,
        request_info['requested_tags']
    )
    
    # 格式化并发送结果
    response = emoticon_request_handler.format_emoticon_list(
        emoticons, 
        request_info['requested_tags']
    )
    
    await request_listener.finish(response)  # 使用finish阻断后续处理器
    logger.info(f"🎨 已发送表情包列表，共 {len(emoticons)} 个")

# ==================== 选择处理 ====================

# ❌ 选择处理器已禁用，改为在智能调度器中统一处理
# 原因：任何priority < 10的处理器，无论如何都会阻断智能调度器
# 解决方案：让所有消息都直接到智能调度器(priority=10)处理

# # 监听数字选择（优先级高）
# selection_listener = on_message(priority=5, block=False)

# @selection_listener.handle()
async def handle_emoticon_selection_disabled(bot, event: MessageEvent):
    """
    处理表情包选择
    """
    # 快速检查：是否应该处理这条消息
    should_handle = False
    
    if EMOTICON_LEARNER_AVAILABLE:
        # 只处理私聊
        if not (hasattr(event, 'group_id') and event.group_id):
            # 获取消息内容
            message_text = event.get_plaintext().strip()
            
            # 检查是否是数字选择
            if re.match(r'^\d+$', message_text):
                # 获取用户状态
                user_state = state_manager.get_user_state(str(event.user_id))
                if user_state:
                    should_handle = True
    
    # 如果不应该处理，立即skip
    if not should_handle:
        await selection_listener.skip()
        return
    
    # 以下是真正的处理逻辑
    message_text = event.get_plaintext().strip()
    selection = int(message_text)
    user_state = state_manager.get_user_state(str(event.user_id))
    
    # 检查选择是否有效
    if selection < 1 or selection > len(user_state.emoticons):
        await selection_listener.finish(f"❌ 请选择 1-{len(user_state.emoticons)} 之间的数字")
        return
    
    # 获取选中的表情包
    selected_emoticon = user_state.emoticons[selection - 1]
    
    logger.info(f"🎨 用户 {event.user_id} 选择了表情包: {selected_emoticon['description']}")
    
    # 发送选中的表情包
    response = await emoticon_request_handler.send_selected_emoticon(
        selected_emoticon, 
        str(event.user_id)
    )
    
    # 清除用户状态
    state_manager.clear_user_state(str(event.user_id))
    
    logger.info(f"🎨 成功发送表情包给用户 {event.user_id}")
    
    # 发送响应（block=True会自动阻断）
    if isinstance(response, list):
        # 发送所有部分
        for part in response:
            await selection_listener.send(part)
    else:
        await selection_listener.send(response)
    
    # block=True + 正常完成 = 自动阻断后续处理器

# ==================== 初始化 ====================

@get_driver().on_startup
async def init_emoticon_request():
    """初始化表情包索要系统"""
    logger.info("🎨 表情包索要系统初始化完成")
    logger.info("💡 用户可以说：给我一个开心的表情包、要一个难过的表情等")
