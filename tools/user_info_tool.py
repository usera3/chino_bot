"""
用户信息工具 - 获取用户、群聊和成员信息
"""
from core.tool_base import BaseTool, ToolResult
from nonebot.log import logger
from typing import Dict, Any


class UserInfoTool(BaseTool):
    """
    获取用户信息工具 - 查询用户昵称、群名称等
    """
    
    def __init__(self, bot=None):
        super().__init__()
        self.bot = bot
    
    def get_name(self) -> str:
        return "get_user_info"
    
    def get_description(self) -> str:
        return "获取用户或群聊的基本信息，包括用户昵称、群名称等"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "description": "查询类型：'user'(用户信息), 'group'(群信息), 'self'(机器人自己的信息)",
                    "enum": ["user", "group", "self"]
                },
                "target_id": {
                    "type": "string",
                    "description": "目标ID（QQ号或群号），查询self时不需要"
                }
            },
            "required": ["query_type"]
        }
    
    async def execute(self, query_type: str = "self", target_id: str = None, **kwargs) -> ToolResult:
        """
        执行用户信息查询
        
        Args:
            query_type: 查询类型
            target_id: 目标ID
        
        Returns:
            ToolResult: 查询结果
        """
        logger.info(f"执行用户信息查询，类型: {query_type}, 目标: {target_id}")
        
        try:
            if not self.bot:
                return ToolResult(
                    success=False,
                    message="机器人未初始化，无法查询信息"
                )
            
            if query_type == "self":
                # 获取机器人自己的信息
                self_info = await self.bot.get_login_info()
                nickname = self_info.get('nickname', '未知')
                user_id = self_info.get('user_id', '未知')
                return ToolResult(
                    success=True,
                    data=self_info,
                    message=f"机器人信息：昵称 {nickname}，QQ号 {user_id}"
                )
            
            elif query_type == "user" and target_id:
                # 获取用户信息
                try:
                    user_info = await self.bot.get_stranger_info(user_id=int(target_id))
                    nickname = user_info.get('nickname', '未知')
                    return ToolResult(
                        success=True,
                        data=user_info,
                        message=f"用户信息：QQ {target_id}，昵称 {nickname}"
                    )
                except Exception as e:
                    return ToolResult(
                        success=False,
                        message=f"无法获取用户 {target_id} 的信息"
                    )
            
            elif query_type == "group" and target_id:
                # 获取群信息
                try:
                    group_info = await self.bot.get_group_info(group_id=int(target_id))
                    group_name = group_info.get('group_name', '未知')
                    member_count = group_info.get('member_count', 0)
                    return ToolResult(
                        success=True,
                        data=group_info,
                        message=f"群聊信息：群号 {target_id}，群名 {group_name}，成员数 {member_count}"
                    )
                except Exception as e:
                    return ToolResult(
                        success=False,
                        message=f"无法获取群 {target_id} 的信息"
                    )
            
            else:
                return ToolResult(
                    success=False,
                    message="参数错误：需要提供查询类型和目标ID"
                )
        
        except Exception as e:
            logger.error(f"用户信息查询失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"查询失败：{e}"
            )


class GroupMemberTool(BaseTool):
    """
    获取群成员列表工具
    """
    
    def __init__(self, bot=None):
        super().__init__()
        self.bot = bot
    
    def get_name(self) -> str:
        return "get_group_members"
    
    def get_description(self) -> str:
        return "获取指定群聊的成员列表"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_id": {
                    "type": "string",
                    "description": "群号"
                }
            },
            "required": ["group_id"]
        }
    
    async def execute(self, group_id: str, **kwargs) -> ToolResult:
        """
        获取群成员列表
        
        Args:
            group_id: 群号
        
        Returns:
            ToolResult: 成员列表
        """
        logger.info(f"执行群成员查询，群号: {group_id}")
        
        try:
            if not self.bot:
                return ToolResult(
                    success=False,
                    message="机器人未初始化，无法查询成员"
                )
            
            # 获取群成员列表
            member_list = await self.bot.get_group_member_list(group_id=int(group_id))
            
            if not member_list:
                return ToolResult(
                    success=False,
                    message=f"群 {group_id} 没有成员或无权查看"
                )
            
            # 格式化成员信息
            member_info = []
            for member in member_list[:20]:  # 最多显示20个成员
                nickname = member.get('nickname', '未知')
                card = member.get('card', '')
                user_id = member.get('user_id', '')
                role = member.get('role', 'member')
                
                display_name = card if card else nickname
                member_info.append(f"{display_name}(QQ:{user_id}, 身份:{role})")
            
            total = len(member_list)
            summary = f"群 {group_id} 共有 {total} 名成员"
            if total > 20:
                summary += f"（显示前20名）"
            
            return ToolResult(
                success=True,
                data=member_list,
                message=f"{summary}：\n" + "\n".join(member_info)
            )
        
        except Exception as e:
            logger.error(f"群成员查询失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"查询失败：{e}"
            )




