"""
消息分段工具 - Utils Layer
职责：将长消息智能分段，模拟真人聊天
代码量：~150行
"""
from typing import List
import asyncio
import re
from nonebot.log import logger


class MessageSplitter:
    """消息分段发送工具 - 提升用户体验"""
    
    # 配置
    ENABLE_SPLIT_SEND = True  # 启用分段发送
    MIN_LENGTH_TO_SPLIT = 30  # 超过此长度才分段
    TYPING_DELAY_PER_CHAR = 0.03  # 每个字符的打字延迟（秒）
    MIN_TYPING_DELAY = 0.5  # 最小延迟
    MAX_TYPING_DELAY = 2.0  # 最大延迟
    
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
        if not text or len(text) < MessageSplitter.MIN_LENGTH_TO_SPLIT:
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
        计算模拟打字延迟
        根据文本长度动态调整，模拟真人打字速度
        """
        char_count = len(text)
        delay = char_count * MessageSplitter.TYPING_DELAY_PER_CHAR
        
        # 限制在合理范围
        delay = max(MessageSplitter.MIN_TYPING_DELAY, delay)
        delay = min(MessageSplitter.MAX_TYPING_DELAY, delay)
        
        return delay
    
    @staticmethod
    async def send_split_message(matcher, message: str):
        """
        分段发送消息，模拟真人聊天体验
        
        Args:
            matcher: NoneBot的matcher对象
            message: 要发送的完整消息
        """
        if not MessageSplitter.ENABLE_SPLIT_SEND:
            # 如果禁用分段发送，直接发送
            await matcher.send(message)
            return
        
        segments = MessageSplitter.split_message(message)
        
        if len(segments) <= 1:
            # 只有一段或消息很短，直接发送
            await matcher.send(message)
            return
        
        # 分段发送
        logger.info(f"💬 消息分为 {len(segments)} 段发送")
        
        for i, segment in enumerate(segments):
            if i > 0:
                # 计算并等待打字延迟
                delay = MessageSplitter.calculate_typing_delay(segment)
                await asyncio.sleep(delay)
            
            await matcher.send(segment)

























