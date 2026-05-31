"""
QQ 互动工具
基于 OneBot V11 API 实现 QQ 特有的互动功能
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
from nonebot.adapters.onebot.v11 import Bot


# 全局 Bot 实例和上下文（由 chat_plugin 设置）
_bot_instance: Optional[Bot] = None
_current_context: dict = {}


def set_bot_instance(bot: Bot):
    """设置全局 Bot 实例"""
    global _bot_instance
    _bot_instance = bot


def get_bot_instance() -> Optional[Bot]:
    """获取全局 Bot 实例"""
    return _bot_instance


def set_current_context(user_id: str, group_id: Optional[int] = None, mentioned_users: list = None):
    """设置当前对话上下文"""
    global _current_context
    _current_context = {
        "user_id": user_id,
        "group_id": group_id,
        "mentioned_users": mentioned_users or []  # 被 @ 的用户列表
    }


def get_current_context() -> dict:
    """获取当前对话上下文"""
    return _current_context


# ==================== 点赞工具 ====================
class SendLikeInput(BaseModel):
    """点赞输入"""
    user_id: Optional[str] = Field(default=None, description="用户 QQ 号，如果不提供则使用当前对话用户")
    times: int = Field(default=10, description="点赞次数，范围 1-10，默认 10 次")


class SendLikeTool(BaseTool):
    """给用户点赞（QQ 名片点赞）"""
    name: str = "send_like"
    description: str = """【必须调用】给用户的 QQ 名片点赞。

⚠️ 重要：当用户说"给我点赞"、"点赞"、"给xxx点赞"等时，必须调用此工具！

使用方法：
- 用户说"给我点赞" → 调用 send_like()，不需要提供 user_id
- 用户说"给 @某人 点赞" → 调用 send_like()，不需要提供 user_id
- 用户说"给我点10个赞" → 调用 send_like(times=10)

参数说明：
- user_id: 可选，不提供时自动使用当前用户或被@的用户
- times: 点赞次数（1-10），默认10次"""
    args_schema: type[BaseModel] = SendLikeInput
    
    def _run(self, user_id: Optional[str] = None, times: int = 10) -> str:
        """执行工具"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法执行点赞操作"
        
        # 如果没有提供 user_id，使用当前上下文
        if not user_id:
            context = get_current_context()
            
            # 优先使用被 @ 的用户（排除机器人自己）
            mentioned_users = context.get("mentioned_users", [])
            bot_id = str(bot.self_id) if hasattr(bot, 'self_id') else "1000000000"
            
            # 过滤掉机器人自己
            target_users = [u for u in mentioned_users if u != bot_id]
            
            if target_users:
                user_id = target_users[0]  # 使用第一个被 @ 的用户（非机器人）
            else:
                # 否则使用当前用户
                user_id = context.get("user_id")
            
            if not user_id:
                return "❌ 无法获取目标用户 ID"
        
        try:
            # 限制次数范围
            times = max(1, min(10, times))
            
            # 调用 OneBot API（使用新的事件循环）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(bot.send_like(user_id=int(user_id), times=times))
            
            return f"✅ 已给用户 {user_id} 点赞 {times} 次！👍"
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "今日同一好友点赞数已达上限" in error_msg or "已达上限" in error_msg:
                return f"❌ 点赞失败：今天对用户 {user_id} 的点赞次数已达上限（QQ 每天对同一好友点赞有次数限制）"
            elif "timeout" in error_msg.lower():
                return f"❌ 点赞失败：网络超时，请稍后重试"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 点赞失败：用户 {user_id} 不存在或不是好友"
            else:
                return f"❌ 点赞失败：{error_msg}"
    
    async def _arun(self, user_id: Optional[str] = None, times: int = 10) -> str:
        """异步执行"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法执行点赞操作"
        
        # 如果没有提供 user_id，使用当前上下文
        if not user_id:
            context = get_current_context()
            
            # 优先使用被 @ 的用户（排除机器人自己）
            mentioned_users = context.get("mentioned_users", [])
            bot_id = str(bot.self_id) if hasattr(bot, 'self_id') else "1000000000"
            
            # 过滤掉机器人自己
            target_users = [u for u in mentioned_users if u != bot_id]
            
            if target_users:
                user_id = target_users[0]  # 使用第一个被 @ 的用户（非机器人）
            else:
                # 否则使用当前用户
                user_id = context.get("user_id")
            
            if not user_id:
                return "❌ 无法获取目标用户 ID"
        
        try:
            times = max(1, min(10, times))
            await bot.send_like(user_id=int(user_id), times=times)
            return f"✅ 已给用户 {user_id} 点赞 {times} 次！👍"
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "今日同一好友点赞数已达上限" in error_msg or "已达上限" in error_msg:
                return f"❌ 点赞失败：今天对用户 {user_id} 的点赞次数已达上限（QQ 每天对同一好友点赞有次数限制）"
            elif "timeout" in error_msg.lower():
                return f"❌ 点赞失败：网络超时，请稍后重试"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 点赞失败：用户 {user_id} 不存在或不是好友"
            else:
                return f"❌ 点赞失败：{error_msg}"


# ==================== 获取用户信息工具 ====================
class GetUserInfoInput(BaseModel):
    """获取用户信息输入"""
    user_id: Optional[str] = Field(default=None, description="用户 QQ 号，如果不提供则使用当前对话用户")
    no_cache: bool = Field(default=False, description="是否不使用缓存，默认 False")


class GetUserInfoTool(BaseTool):
    """获取用户信息（昵称、年龄、性别等）"""
    name: str = "get_user_info"
    description: str = """【必须调用】获取 QQ 用户的详细信息。

⚠️ 重要：当用户问"我叫什么"、"我的名字"、"我的信息"、"查看我的qq名片"等时，必须调用此工具！

可以获取：
- 用户昵称
- 年龄
- 性别

使用方法：
- 用户问"我叫什么名字" → 调用 get_user_info()，不需要提供 user_id
- 用户问"xxx叫什么" → 调用 get_user_info(user_id="xxx的QQ号")

参数说明：
- user_id: 可选，不提供时自动使用当前用户
- no_cache: 是否不使用缓存，默认 False"""
    args_schema: type[BaseModel] = GetUserInfoInput
    
    def _run(self, user_id: Optional[str] = None, no_cache: bool = False) -> str:
        """执行工具"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法获取用户信息"
        
        # 如果没有提供 user_id，使用当前上下文
        if not user_id:
            context = get_current_context()
            user_id = context.get("user_id")
            if not user_id:
                return "❌ 无法获取当前用户 ID"
        
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            info = loop.run_until_complete(
                bot.get_stranger_info(user_id=int(user_id), no_cache=no_cache)
            )
            
            result = f"""📇 用户信息
QQ 号：{info['user_id']}
昵称：{info['nickname']}
性别：{info.get('sex', '未知')}
年龄：{info.get('age', '未知')}"""
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 获取用户信息失败：网络超时，请稍后重试"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 获取用户信息失败：用户 {user_id} 不存在"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 获取用户信息失败：没有权限查看该用户信息"
            else:
                return f"❌ 获取用户信息失败：{error_msg}"
    
    async def _arun(self, user_id: Optional[str] = None, no_cache: bool = False) -> str:
        """异步执行"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法获取用户信息"
        
        # 如果没有提供 user_id，使用当前上下文
        if not user_id:
            context = get_current_context()
            user_id = context.get("user_id")
            if not user_id:
                return "❌ 无法获取当前用户 ID"
        
        try:
            info = await bot.get_stranger_info(user_id=int(user_id), no_cache=no_cache)
            
            result = f"""📇 用户信息
QQ 号：{info['user_id']}
昵称：{info['nickname']}
性别：{info.get('sex', '未知')}
年龄：{info.get('age', '未知')}"""
            
            return result
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 获取用户信息失败：网络超时，请稍后重试"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 获取用户信息失败：用户 {user_id} 不存在"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 获取用户信息失败：没有权限查看该用户信息"
            else:
                return f"❌ 获取用户信息失败：{error_msg}"


# ==================== 获取群成员信息工具 ====================
class GetGroupMemberInfoInput(BaseModel):
    """获取群成员信息输入"""
    group_id: Optional[str] = Field(default=None, description="群号，如果不提供则使用当前群")
    user_id: Optional[str] = Field(default=None, description="用户 QQ 号，如果不提供则使用当前用户")
    no_cache: bool = Field(default=False, description="是否不使用缓存，默认 False")


class GetGroupMemberInfoTool(BaseTool):
    """获取群成员信息（群昵称、群名片、权限等）"""
    name: str = "get_group_member_info"
    description: str = """【必须调用】获取群成员的详细信息。

⚠️ 重要：当用户问"我在群里是什么身份"、"我的群名片"等时，必须调用此工具！

可以获取：
- 群昵称/群名片
- 群内权限（群主、管理员、成员）

使用方法：
- 用户问"我在群里是什么身份" → 调用 get_group_member_info()，不需要提供参数
- 用户问"xxx在群里是什么身份" → 调用 get_group_member_info(user_id="xxx的QQ号")

参数说明：
- group_id: 可选，不提供时自动使用当前群
- user_id: 可选，不提供时自动使用当前用户
- no_cache: 是否不使用缓存，默认 False"""
    args_schema: type[BaseModel] = GetGroupMemberInfoInput
    
    def _run(self, group_id: Optional[str] = None, user_id: Optional[str] = None, no_cache: bool = False) -> str:
        """执行工具"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法获取群成员信息"
        
        # 如果没有提供参数，使用当前上下文
        context = get_current_context()
        
        if not group_id:
            group_id = context.get("group_id")
            if not group_id:
                return "❌ 当前不在群聊中，无法获取群成员信息"
        
        if not user_id:
            user_id = context.get("user_id")
            if not user_id:
                return "❌ 无法获取当前用户 ID"
        
        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            info = loop.run_until_complete(
                bot.get_group_member_info(
                    group_id=int(group_id),
                    user_id=int(user_id),
                    no_cache=no_cache
                )
            )
            
            role_map = {
                "owner": "群主",
                "admin": "管理员",
                "member": "成员"
            }
            
            result = f"""👥 群成员信息
群号：{info['group_id']}
QQ 号：{info['user_id']}
昵称：{info['nickname']}
群名片：{info.get('card', '未设置')}
权限：{role_map.get(info.get('role', 'member'), '成员')}"""
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 获取群成员信息失败：网络超时，请稍后重试"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 获取群成员信息失败：群 {group_id} 或用户 {user_id} 不存在"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 获取群成员信息失败：没有权限查看该群信息"
            else:
                return f"❌ 获取群成员信息失败：{error_msg}"
    
    async def _arun(self, group_id: Optional[str] = None, user_id: Optional[str] = None, no_cache: bool = False) -> str:
        """异步执行"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法获取群成员信息"
        
        # 如果没有提供参数，使用当前上下文
        context = get_current_context()
        
        if not group_id:
            group_id = context.get("group_id")
            if not group_id:
                return "❌ 当前不在群聊中，无法获取群成员信息"
        
        if not user_id:
            user_id = context.get("user_id")
            if not user_id:
                return "❌ 无法获取当前用户 ID"
        
        try:
            info = await bot.get_group_member_info(
                group_id=int(group_id),
                user_id=int(user_id),
                no_cache=no_cache
            )
            
            role_map = {
                "owner": "群主",
                "admin": "管理员",
                "member": "成员"
            }
            
            result = f"""👥 群成员信息
群号：{info['group_id']}
QQ 号：{info['user_id']}
昵称：{info['nickname']}
群名片：{info.get('card', '未设置')}
权限：{role_map.get(info.get('role', 'member'), '成员')}"""
            
            return result
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 获取群成员信息失败：网络超时，请稍后重试"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 获取群成员信息失败：群 {group_id} 或用户 {user_id} 不存在"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 获取群成员信息失败：没有权限查看该群信息"
            else:
                return f"❌ 获取群成员信息失败：{error_msg}"


# ==================== 工具列表 ====================
def get_all_qq_interaction_tools() -> list[BaseTool]:
    """获取所有 QQ 互动工具"""
    return [
        SendLikeTool(),
        GetUserInfoTool(),
        GetGroupMemberInfoTool(),
    ]
