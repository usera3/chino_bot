"""
点赞工具 - QQ特色功能
"""
from core.tool_base import BaseTool, ToolResult
from nonebot.log import logger
from typing import Optional


class LikeTool(BaseTool):
    """
    点赞工具 - 给指定用户的QQ资料点赞
    """
    
    def __init__(self, bot=None):
        super().__init__()
        self.bot = bot
    
    def get_name(self) -> str:
        return "send_like"
    
    def get_description(self) -> str:
        return "给用户的QQ资料点赞。当用户要求点赞、给赞、点个赞等时使用。可以指定点赞次数（1-10次），默认点10次。"
    
    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "要点赞的用户QQ号。如果用户说'给我点赞'，使用当前用户的QQ号。"
                },
                "times": {
                    "type": "integer",
                    "description": "点赞次数，范围1-10，默认为10",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["user_id"]
        }
    
    async def execute(self, user_id: str, times: int = 10, **kwargs) -> ToolResult:
        """
        执行点赞
        
        Args:
            user_id: 用户QQ号
            times: 点赞次数（1-10，默认10）
        
        Returns:
            ToolResult
        """
        logger.info(f"执行点赞工具，目标用户: {user_id}, 次数: {times}")
        
        if not self.bot:
            return ToolResult(
                success=False,
                error="Bot 实例未设置",
                message="点赞功能暂时不可用。"
            )
        
        # 限制点赞次数
        times = max(1, min(10, times))
        
        try:
            # 调用 NoneBot 的点赞 API
            await self.bot.send_like(user_id=int(user_id), times=times)
            
            logger.info(f"点赞成功：用户 {user_id}，次数 {times}")
            
            return ToolResult(
                success=True,
                data={"user_id": user_id, "times": times},
                message=f"已成功给用户 {user_id} 点赞 {times} 次 👍"
            )
        
        except Exception as e:
            logger.error(f"点赞失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"点赞失败：{str(e)}"
            )

