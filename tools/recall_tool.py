"""
消息撤回工具
"""
from typing import Optional
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot
from core.tool_base import BaseTool, ToolResult


class RecallTool(BaseTool):
    """消息撤回工具"""
    
    # 类变量：所有实例共享同一个消息记录
    recent_messages = {}  # {user_id: [message_id1, message_id2, ...]}
    
    def __init__(self, bot: Optional[Bot] = None):
        super().__init__()
        self.bot = bot
    
    def get_name(self) -> str:
        return "recall_message"
    
    def get_description(self) -> str:
        return """撤回机器人刚发送的消息。当用户要求"撤回"、"删除刚才的消息"、"收回"时使用。
注意：只能撤回最近发送的消息（2分钟内），且只能撤回自己发送的消息。"""
    
    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户QQ号，用于定位要撤回哪条消息"
                },
                "count": {
                    "type": "integer",
                    "description": "撤回最近的几条消息，默认1条，最多5条",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 5
                }
            },
            "required": ["user_id"]
        }
    
    async def execute(self, user_id: str, count: int = 1, **kwargs) -> ToolResult:
        """
        执行消息撤回
        
        Args:
            user_id: 用户QQ号
            count: 撤回最近几条消息
        """
        logger.info(f"🗑️ 执行消息撤回: 用户 {user_id}, 撤回 {count} 条")
        
        if not self.bot:
            return ToolResult(
                success=False,
                message="Bot 实例未设置，无法撤回消息。",
                error="Bot instance not set"
            )
        
        # 获取该用户的消息历史（使用类变量）
        if user_id not in RecallTool.recent_messages or not RecallTool.recent_messages[user_id]:
            return ToolResult(
                success=False,
                message="没有找到最近发送的消息，可能已经超过撤回时限（2分钟）。",
                error="No recent messages found"
            )
        
        # 限制撤回数量
        count = max(1, min(5, count))
        
        # 获取要撤回的消息ID列表
        message_ids = RecallTool.recent_messages[user_id][-count:]
        
        recalled_count = 0
        failed_count = 0
        
        for msg_id in reversed(message_ids):  # 从最新的开始撤回
            try:
                await self.bot.delete_msg(message_id=msg_id)
                recalled_count += 1
                logger.info(f"✅ 已撤回消息: {msg_id}")
                
                # 从记录中移除（使用类变量）
                RecallTool.recent_messages[user_id].remove(msg_id)
            except Exception as e:
                logger.error(f"❌ 撤回消息失败 {msg_id}: {e}")
                failed_count += 1
        
        if recalled_count > 0:
            return ToolResult(
                success=True,
                data={"recalled": recalled_count, "failed": failed_count},
                message=f"已撤回 {recalled_count} 条消息" + (f"，{failed_count} 条失败" if failed_count > 0 else "")
            )
        else:
            return ToolResult(
                success=False,
                error="所有消息撤回失败",
                message="撤回失败，可能已超过撤回时限（2分钟）。"
            )
    
    def track_message(self, user_id: str, message_id: int):
        """
        追踪发送的消息ID
        
        Args:
            user_id: 用户QQ号
            message_id: 消息ID
        """
        # 使用类变量存储
        if user_id not in RecallTool.recent_messages:
            RecallTool.recent_messages[user_id] = []
        
        RecallTool.recent_messages[user_id].append(message_id)
        
        # 只保留最近10条消息记录
        if len(RecallTool.recent_messages[user_id]) > 10:
            RecallTool.recent_messages[user_id] = RecallTool.recent_messages[user_id][-10:]
        
        logger.debug(f"📝 追踪消息ID: {message_id} (用户: {user_id})")
        logger.info(f"🔍 当前用户 {user_id} 的消息记录: {RecallTool.recent_messages[user_id]}")

