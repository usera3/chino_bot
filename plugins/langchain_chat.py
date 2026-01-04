"""
LangChain 聊天插件 - 使用 MCP 标准的工具系统
支持消息分段发送和自动语音合成
"""
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, MessageSegment
from nonebot.rule import to_me
from nonebot.log import logger
from nonebot.exception import FinishedException
import sys
import os
import httpx

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 🎯 使用角色扮演 Agent（带记忆系统）
from core.role_agent import get_role_agent

# 消息分段发送工具
from utils.message_splitter import MessageSplitter

# 初始化角色Agent（香风智乃）
langchain_agent = get_role_agent()

# 创建消息处理器 - 响应所有消息
langchain_chat_handler = on_message(priority=10, block=True)

@langchain_chat_handler.handle()
async def handle_langchain_chat(bot: Bot, event: MessageEvent):
    """处理聊天消息 - 使用 LangChain Agent + MCP 工具"""
    message_text = event.get_plaintext().strip()
    user_id = event.get_user_id()
    
    # 🖼️ 提取图片URL（如果有）
    image_urls = []
    for seg in event.message:
        if seg.type == "image":
            url = seg.data.get("url") or seg.data.get("file")
            if url:
                image_urls.append(url)
    
    if isinstance(event, GroupMessageEvent):
        source = f"群 {event.group_id}"
        
        # 群聊：只响应@机器人或回复机器人的消息
        if not event.to_me:
            # 检查是否是回复机器人的消息
            is_reply_to_bot = False
            for seg in event.message:
                if seg.type == "reply":
                    # 这是一条回复消息，可以处理
                    is_reply_to_bot = True
                    break
            
            if not is_reply_to_bot:
                # 既不是@也不是回复，忽略
                logger.debug(f"[LangChain Chat] 群消息未@机器人，忽略")
                return
    else:
        source = "私聊"
    
    # 构建日志消息（包含图片信息）
    log_msg = f"[LangChain Chat] 收到来自 {source} 的消息: {message_text}"
    if image_urls:
        log_msg += f" [包含 {len(image_urls)} 张图片]"
    logger.info(log_msg)
    
    if not message_text and not image_urls:
        await langchain_chat_handler.finish("你好呀！有什么可以帮你的吗？ 😊")
    
    # Function Calling Agent 不需要 is_available 检查
    
    # 传递 bot 实例给 agent（用于某些需要bot的工具）
    langchain_agent.set_bot(bot)
    
    try:
        logger.info(f"[LangChain Chat] 调用 LangChain Agent 处理消息...")
        
        # 获取上下文信息
        current_user_id = user_id
        current_group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
        
        # 🖼️ 如果有图片且识别功能可用，在消息中添加图片URL信息
        final_message = message_text
        if image_urls and vision_available:
            # 构建完整消息（包含图片URL）
            final_message = message_text or "用户发送了图片"
            # 将图片URL添加到上下文信息中
            for i, url in enumerate(image_urls, 1):
                final_message += f"\n[图片{i} URL: {url}]"
            logger.info(f"[LangChain Chat] 附带 {len(image_urls)} 张图片的URL")
        
        # 传递上下文给agent
        ai_reply = await langchain_agent.chat(
            user_message=final_message,
            user_id=current_user_id,
            group_id=current_group_id
        )
        
        if ai_reply is None:
            # 返回 None 表示不需要发送消息（例如撤回成功）
            logger.info(f"[LangChain Chat] Agent 返回 None，不发送消息")
            raise FinishedException
        
        if ai_reply:
            logger.info(f"[LangChain Chat] Agent 回复成功，长度: {len(ai_reply)}")
            
            # 🖼️ 检测是否是图片消息（AI调用了图片搜索工具）
            if ai_reply.startswith("[IMAGES:") and "|TEXT:" in ai_reply:
                import re
                
                match = re.match(r'\[IMAGES:(.+?)\|TEXT:(.+?)\]', ai_reply, re.DOTALL)
                if match:
                    urls_str = match.group(1)
                    text = match.group(2)
                    
                    logger.info(f"[LangChain Chat] 🖼️ 检测到图片消息: {text}")
                    
                    # 分割URL
                    image_urls = urls_str.split("|||")
                    
                    # 先发送文字
                    await langchain_chat_handler.send(text.strip())
                    
                    # 逐个下载并发送图片
                    for idx, url in enumerate(image_urls, 1):
                        try:
                            logger.info(f"[LangChain Chat] 📥 下载图片 {idx}/{len(image_urls)}: {url[:80]}...")
                            
                            # 使用 MessageSegment.image 直接发送URL
                            # OneBot 会自动下载并转换
                            image_msg = MessageSegment.image(url)
                            await langchain_chat_handler.send(image_msg)
                            
                            logger.success(f"✅ 图片 {idx} 发送成功")
                            
                        except Exception as e:
                            error_str = str(e)
                            logger.error(f"❌ 图片 {idx} 发送失败: {error_str}")
                            
                            # 分析失败原因并给出友好提示
                            if "Timeout" in error_str or "timeout" in error_str:
                                reason = "图片加载超时（可能是网络问题）"
                            elif "Connect" in error_str:
                                reason = "无法连接到图片服务器"
                            elif "404" in error_str:
                                reason = "图片不存在"
                            elif "403" in error_str:
                                reason = "图片访问被拒绝"
                            else:
                                reason = "图片加载失败"
                            
                            # 发送失败原因和链接
                            await langchain_chat_handler.send(f"⚠️ 图片 {idx} {reason}\n链接: {url}")
                    
                    raise FinishedException
            
            # 🎤 检测是否是语音消息（AI主动调用了TTS工具）
            if ai_reply.startswith("[VOICE:") and "|TEXT:" in ai_reply:
                # 解析语音消息
                import re
                from pathlib import Path
                import base64
                
                match = re.match(r'\[VOICE:(.+?)\|TEXT:(.+?)\]', ai_reply)
                if match:
                    voice_path = match.group(1)
                    text = match.group(2)
                    
                    logger.info(f"[LangChain Chat] 🎤 检测到语音消息: {text}")
                    
                    # 发送语音
                    if voice_path and Path(voice_path).exists():
                        try:
                            with open(voice_path, 'rb') as f:
                                voice_data = f.read()
                            voice_base64 = base64.b64encode(voice_data).decode('utf-8')
                            
                            voice_msg = MessageSegment.record(f"base64://{voice_base64}")
                            result = await langchain_chat_handler.send(voice_msg)
                            
                            # 追踪消息ID（用于撤回）
                            if result and hasattr(result, 'message_id'):
                                recall_tool = langchain_agent.tools.get("recall_message")
                                if recall_tool:
                                    recall_tool.track_message(user_id, result['message_id'])
                            
                            logger.success(f"🎤 已发送语音消息（不发送文字）")
                        except Exception as e:
                            logger.error(f"语音发送失败: {e}，发送文字")
                            await langchain_chat_handler.send(text)
                    else:
                        logger.warning(f"语音文件不存在: {voice_path}，发送文字")
                        await langchain_chat_handler.send(text)
                    
                    raise FinishedException
            
            # 🎤 正常消息：使用分段发送 + 自动语音
            # 获取TTS工具和撤回工具
            tts_tool = langchain_agent.tools.get("text_to_speech")
            recall_tool = langchain_agent.tools.get("recall_message")
            
            # 分段发送消息（带语音和消息ID追踪）
            await MessageSplitter.send_split_message(
                matcher=langchain_chat_handler,
                message=ai_reply,
                tts_tool=tts_tool,
                enable_tts=True,  # 启用最后一段语音
                recall_tool=recall_tool,  # 传递撤回工具用于追踪消息ID
                user_id=user_id  # 传递用户ID
            )
            
            # 使用finish()结束对话（不会再发送消息）
            raise FinishedException
        else:
            logger.error(f"[LangChain Chat] Agent 回复为空")
            await langchain_chat_handler.finish("抱歉，我现在有点累了，稍后再聊吧~ 😅")
    
    except FinishedException:
        raise  # Re-raise to properly end the matcher
    
    except Exception as e:
        logger.error(f"[LangChain Chat] 处理消息异常: {e}", exc_info=True)
        await langchain_chat_handler.finish("抱歉，我遇到了一些问题... 🙏")
