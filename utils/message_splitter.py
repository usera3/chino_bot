"""
消息分段发送工具 - 模拟真人打字效果
"""
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
import asyncio
import re
from typing import List, Optional
from pathlib import Path
import base64


class MessageSplitterConfig:
    """消息分段配置"""
    ENABLE_SPLIT_SEND = True  # 启用分段发送
    MIN_LENGTH_TO_SPLIT = 30  # 超过此长度才分段
    TYPING_DELAY_PER_CHAR = 0.03  # 每个字符的打字延迟（秒）
    MIN_TYPING_DELAY = 0.5  # 最小延迟
    MAX_TYPING_DELAY = 2.0  # 最大延迟
    
    # TTS 配置
    ENABLE_TTS = True  # 启用最后一段语音合成
    TTS_REMOVE_BRACKETS = True  # 去除括号内容


class MessageSplitter:
    """消息分段发送工具"""
    
    @staticmethod
    def split_message(text: str) -> List[str]:
        """
        将长消息按标点符号智能分段，模拟真人聊天习惯
        
        规则：
        1. 按句号、感叹号、问号、省略号、换行符分割
        2. 去掉每段末尾的标点（真人聊天不带标点）
        3. 每段不超过100字（避免单段过长）
        4. 合并过短的段落（避免太零碎）
        """
        if not text or len(text) < MessageSplitterConfig.MIN_LENGTH_TO_SPLIT:
            return [text]
        
        # 分隔符：中英文标点（包括省略号）
        separators = [
            '\n\n',  # 双换行（段落）
            '。',    # 中文句号
            '！',    # 中文感叹号
            '？',    # 中文问号
            '……',   # 中文省略号
            '...',   # 英文省略号
            '。。。', # 另一种省略号
            '\n',    # 单换行
            '；',    # 分号
            '.',     # 英文句号（但要避免小数点）
            '!',     # 英文感叹号
            '?',     # 英文问号
        ]
        
        segments = []
        current_segment = ""
        i = 0
        
        while i < len(text):
            char = text[i]
            current_segment += char
            
            # 检查是否遇到分隔符
            matched_sep = None
            for sep in separators:
                if text[i:i+len(sep)] == sep:
                    # 特殊处理：避免把小数点当成句号
                    if sep == '.' and i > 0 and i < len(text) - 1:
                        if text[i-1].isdigit() and text[i+1].isdigit():
                            i += 1
                            continue
                    
                    matched_sep = sep
                    break
            
            if matched_sep:
                # 完整吞掉分隔符
                if len(matched_sep) > 1:
                    current_segment += text[i+1:i+len(matched_sep)]
                    i += len(matched_sep)
                else:
                    i += 1
                
                # 如果当前段落足够长，或遇到段落分隔，则保存
                if len(current_segment.strip()) > 0:
                    # 检查长度，如果太长则强制分割
                    if len(current_segment) > 100:
                        # 💬 去掉末尾标点（真人聊天习惯）
                        cleaned = current_segment.strip().rstrip('。！？!?…')
                        cleaned = re.sub(r'\.{2,}$', '', cleaned)  # 去掉省略号
                        if cleaned:
                            segments.append(cleaned)
                        current_segment = ""
                    elif matched_sep in ['\n\n', '。', '！', '？', '!', '?', '……', '...', '。。。']:
                        # 💬 去掉末尾标点（真人聊天习惯）
                        cleaned = current_segment.strip().rstrip('。！？!?…')
                        cleaned = re.sub(r'\.{2,}$', '', cleaned)  # 去掉省略号
                        if cleaned:
                            segments.append(cleaned)
                        current_segment = ""
                    # 对于其他分隔符，继续累积
            else:
                i += 1
        
        # 添加剩余部分
        if current_segment.strip():
            # 💬 去掉末尾标点（真人聊天习惯）
            cleaned = current_segment.strip().rstrip('。！？!?…')
            cleaned = re.sub(r'\.{2,}$', '', cleaned)
            if cleaned:
                segments.append(cleaned)
        
        # 合并过短的段落（少于5个字符的）
        merged_segments = []
        temp_segment = ""
        
        for seg in segments:
            if len(seg) < 5 and temp_segment:
                temp_segment += seg
            else:
                if temp_segment:
                    merged_segments.append(temp_segment)
                temp_segment = seg
        
        if temp_segment:
            merged_segments.append(temp_segment)
        
        return merged_segments if merged_segments else [text]
    
    @staticmethod
    def calculate_typing_delay(text: str) -> float:
        """
        根据文本长度计算打字延迟
        """
        delay = len(text) * MessageSplitterConfig.TYPING_DELAY_PER_CHAR
        return min(
            max(delay, MessageSplitterConfig.MIN_TYPING_DELAY),
            MessageSplitterConfig.MAX_TYPING_DELAY
        )
    
    @staticmethod
    def remove_brackets_content(text: str) -> str:
        """去除括号及其内容"""
        patterns = [
            r'\([^)]*\)',  # 英文圆括号
            r'（[^）]*）',  # 中文圆括号
            r'\[[^\]]*\]',  # 方括号
            r'【[^】]*】',  # 中文方括号
        ]
        
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result)
        
        return result.strip()
    
    @staticmethod
    async def send_with_tts(text: str, matcher, tts_tool=None, recall_tool=None, user_id: str = None) -> bool:
        """
        发送带语音的消息
        
        Args:
            text: 要转换的文本
            matcher: NoneBot matcher
            tts_tool: TTS工具实例（可选）
            recall_tool: 撤回工具实例（用于追踪消息ID）
            user_id: 用户QQ号（用于追踪消息ID）
        
        Returns:
            是否成功发送语音
        """
        if not MessageSplitterConfig.ENABLE_TTS or not tts_tool:
            return False
        
        try:
            # 去除括号内容
            if MessageSplitterConfig.TTS_REMOVE_BRACKETS:
                processed_text = MessageSplitter.remove_brackets_content(text)
            else:
                processed_text = text
            
            # 如果处理后为空，跳过
            if not processed_text or len(processed_text.strip()) == 0:
                logger.debug("处理后的文本为空，跳过语音合成")
                return False
            
            # 调用TTS工具
            result = await tts_tool.execute(text=processed_text)
            
            if result and result.success and result.data:
                voice_path = result.data.get("voice_path")
                
                if voice_path and Path(voice_path).exists():
                    # 使用 base64 编码发送语音
                    with open(voice_path, 'rb') as f:
                        voice_data = f.read()
                    voice_base64 = base64.b64encode(voice_data).decode('utf-8')
                    
                    logger.info(f"🎤 语音文件大小: {len(voice_data)} 字节")
                    
                    # 发送语音消息
                    voice_msg = MessageSegment.record(f"base64://{voice_base64}")
                    send_result = await matcher.send(voice_msg)
                    
                    # 追踪语音消息ID
                    if recall_tool and user_id and send_result:
                        try:
                            msg_id = None
                            if isinstance(send_result, dict):
                                msg_id = send_result.get('message_id')
                            elif hasattr(send_result, 'message_id'):
                                msg_id = send_result.message_id
                            elif hasattr(send_result, '__getitem__'):
                                msg_id = send_result['message_id']
                            
                            if msg_id:
                                recall_tool.track_message(user_id, msg_id)
                                logger.info(f"📝 已追踪语音消息ID: {msg_id}")
                        except Exception as e:
                            logger.error(f"❌ 追踪语音消息ID失败: {e}")
                    
                    logger.success(f"🎤 语音消息已发送: {processed_text[:30]}...")
                    return True
            
            return False
        
        except Exception as e:
            logger.error(f"语音发送失败: {e}")
            return False
    
    @staticmethod
    async def send_split_message(
        matcher, 
        message: str, 
        tts_tool=None,
        enable_tts: bool = True,
        recall_tool=None,
        user_id: str = None
    ):
        """
        分段发送消息，最后一段可选语音
        
        Args:
            matcher: NoneBot matcher
            message: 完整消息
            tts_tool: TTS工具实例
            enable_tts: 是否启用最后一段的语音
            recall_tool: 撤回工具实例（用于追踪消息ID）
            user_id: 用户QQ号（用于追踪消息ID）
        """
        if not MessageSplitterConfig.ENABLE_SPLIT_SEND or len(message) < MessageSplitterConfig.MIN_LENGTH_TO_SPLIT:
            # 不分段，尝试发送语音
            if enable_tts and tts_tool:
                voice_sent = await MessageSplitter.send_with_tts(message, matcher, tts_tool, recall_tool, user_id)
                if voice_sent:
                    logger.success(f"🎤 已发送语音（不发文字）")
                    return  # 语音发送成功，不发送文字
            
            # 语音失败或未启用，发送文字
            result = await matcher.send(message)
            
            # 追踪消息ID
            logger.info(f"🔍 发送结果类型: {type(result)}, 内容: {result}")
            if recall_tool and user_id:
                if result:
                    try:
                        # 尝试不同的访问方式
                        msg_id = None
                        if isinstance(result, dict):
                            msg_id = result.get('message_id')
                        elif hasattr(result, 'message_id'):
                            msg_id = result.message_id
                        elif hasattr(result, '__getitem__'):
                            msg_id = result['message_id']
                        
                        if msg_id:
                            recall_tool.track_message(user_id, msg_id)
                            logger.info(f"📝 追踪消息ID: {msg_id}")
                        else:
                            logger.warning(f"⚠️ 无法从结果中提取消息ID")
                    except Exception as e:
                        logger.error(f"❌ 追踪消息ID失败: {e}")
                else:
                    logger.warning(f"⚠️ 发送结果为空")
            
            return
        
        # 分段发送
        segments = MessageSplitter.split_message(message)
        
        logger.info(f"📝 消息分为 {len(segments)} 段发送")
        
        for i, segment in enumerate(segments):
            is_last = (i == len(segments) - 1)
            
            # 计算打字延迟
            if i > 0:
                delay = MessageSplitter.calculate_typing_delay(segments[i-1])
                await asyncio.sleep(delay)
            
            # 最后一段：尝试发送语音，如果成功就不发文字
            if is_last and enable_tts and tts_tool:
                await asyncio.sleep(0.5)  # 语音前稍微延迟
                voice_sent = await MessageSplitter.send_with_tts(segment, matcher, tts_tool, recall_tool, user_id)
                if voice_sent:
                    logger.success(f"🎤 最后一段已发送语音（不发文字）")
                    continue  # 跳过文字发送
                else:
                    logger.info(f"📝 语音发送失败，发送文字")
            
            # 发送文本
            result = await matcher.send(segment)
            logger.debug(f"📤 已发送第 {i+1}/{len(segments)} 段")
            
            # 追踪消息ID
            if recall_tool and user_id and result and hasattr(result, 'message_id'):
                recall_tool.track_message(user_id, result['message_id'])
                logger.debug(f"📝 追踪消息ID: {result['message_id']}")

