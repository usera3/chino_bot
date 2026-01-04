"""
聊天处理入口 - Handler Layer
职责：监听聊天命令，调用服务处理
代码量：~120行（保持简洁！）
"""
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg
from nonebot.log import logger

# 导入服务层
from services.chat.chat_service import get_chat_service

# 导入工具层
from utils.text.message_splitter import MessageSplitter


# ==================== 配置 ====================
ENABLE_SPLIT_SEND = True  # 启用分段发送


# ==================== 命令注册 ====================

# AI聊天命令
chat_matcher = on_command("聊", aliases={"chat", "问", "ai"}, priority=5, block=True)

# 清空记忆命令
clear_matcher = on_command("清空记忆", aliases={"清空", "忘记我"}, priority=5, block=True)

# 查看记忆命令
stats_matcher = on_command("查看记忆", aliases={"记忆统计", "stats"}, priority=5, block=True)


# ==================== 聊天处理 ====================

@chat_matcher.handle()
async def handle_chat(event: MessageEvent, args: Message = CommandArg()):
    """
    处理AI聊天
    职责：
    1. 提取用户消息
    2. 调用服务处理
    3. 分段发送回复
    """
    user_id = str(event.user_id)
    user_message = args.extract_plain_text().strip()
    
    # 检查消息是否为空
    if not user_message:
        await chat_matcher.finish(
            "💬 使用方法：\n"
            "/聊 <消息> - 与AI聊天\n"
            "/清空记忆 - 清除记忆\n"
            "/查看记忆 - 查看统计"
        )
    
    try:
        # 思考提示
        await chat_matcher.send("💭 思考中...")
        
        # 调用服务处理
        chat_service = get_chat_service()
        ai_reply = await chat_service.process_message(user_id, user_message)
        
        if ai_reply:
            # 分段发送回复（提升用户体验）
            await MessageSplitter.send_split_message(chat_matcher, ai_reply)
        else:
            await chat_matcher.send("😔 抱歉，暂时无法回复，请稍后再试")
            
    except Exception as e:
        logger.exception(f"对话处理错误: {e}")
        await chat_matcher.send(f"❌ 发生错误: {type(e).__name__}")


# ==================== 记忆管理 ====================

@clear_matcher.handle()
async def handle_clear_memory(event: MessageEvent):
    """
    清空记忆
    职责：调用服务清除用户记忆
    """
    user_id = str(event.user_id)
    
    try:
        chat_service = get_chat_service()
        await chat_service.clear_memory(user_id, clear_all=False)
        await clear_matcher.send("✨ 所有记忆已清空，我们重新开始吧！")
        
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        await clear_matcher.send("❌ 清空失败")


@stats_matcher.handle()
async def handle_view_memory(event: MessageEvent):
    """
    查看记忆统计
    职责：调用服务获取统计并展示
    """
    user_id = str(event.user_id)
    
    try:
        chat_service = get_chat_service()
        stats = await chat_service.get_memory_stats(user_id)
        
        message = (
            f"🧠 记忆统计\n"
            f"━━━━━━━━━━━━\n"
            f"📝 总消息数: {stats['total_messages']}\n"
            f"💬 活跃对话: {stats['recent_count']} 条\n"
            f"⭐ 重要记忆: {stats['important_count']} 条\n"
            f"📚 历史摘要: {stats['summary_count']} 个\n"
            f"🕐 最后活跃: {stats['last_active'].strftime('%Y-%m-%d %H:%M')}"
        )
        
        await stats_matcher.send(message)
        
    except Exception as e:
        logger.error(f"查看统计失败: {e}")
        await stats_matcher.send("❌ 获取统计失败")


# ==================== 系统初始化 ====================
logger.success("💬 聊天 Handler 已加载")
logger.info("  - 支持命令: /聊, /清空记忆, /查看记忆")
logger.info("  - 分段发送: ✅")
logger.info("  - 记忆管理: ✅")




