"""
发送文件工具
支持在聊天中直接发送文件给用户
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import os
import asyncio


# 全局 Bot 实例（由 chat_plugin 设置）
_bot_instance = None


def set_bot_instance(bot):
    """设置全局 Bot 实例"""
    global _bot_instance
    _bot_instance = bot


def get_bot_instance():
    """获取全局 Bot 实例"""
    return _bot_instance


# ==================== 发送文件工具 ====================
class SendFileInput(BaseModel):
    """发送文件输入"""
    file_path: str = Field(description="文件路径（本地文件路径）")
    user_id: Optional[str] = Field(default=None, description="用户 QQ 号，如果不提供则使用当前用户")
    group_id: Optional[int] = Field(default=None, description="群号，如果提供则发送到群聊，否则发送私聊")


class SendFileTool(BaseTool):
    """在聊天中发送文件给用户"""
    name: str = "send_file"
    description: str = """在聊天中直接发送文件给用户。

使用场景：
- 用户说"把这个文件发给我"
- 用户说"发送这个文档"
- 创建文档后需要发送给用户

参数说明：
- file_path: 本地文件路径（必需）
- user_id: 用户 QQ 号（可选，不提供时使用当前用户）
- group_id: 群号（可选，提供则发送到群聊，否则发送私聊）

注意：
- 文件必须存在于本地
- 文件会直接在聊天中显示，用户可以点击下载
- 与 upload_group_file 不同，这个是发送到聊天，不是群文件"""
    args_schema: type[BaseModel] = SendFileInput
    
    def _run(self, file_path: str, user_id: Optional[str] = None, group_id: Optional[int] = None) -> str:
        """执行工具"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法发送文件"
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {file_path}"
        
        # 如果没有提供参数，从上下文获取
        if not user_id and not group_id:
            from tools.qq_interaction_tools import get_current_context
            context = get_current_context()
            user_id = context.get("user_id")
            group_id = context.get("group_id")
        
        try:
            from nonebot.adapters.onebot.v11 import Message, MessageSegment
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 构建文件消息段
            # 使用 file:// 协议指定本地文件
            file_url = f"file:///{os.path.abspath(file_path)}"
            
            # 创建消息
            message = Message([
                MessageSegment.text(f"📁 {file_name} ({file_size_mb:.2f} MB)"),
                MessageSegment("file", {"file": file_url, "name": file_name})
            ])
            
            # 发送消息
            loop = asyncio.get_event_loop()
            
            if group_id:
                # 发送到群聊
                loop.run_until_complete(
                    bot.send_group_msg(group_id=int(group_id), message=message)
                )
                return f"✅ 文件已发送到群聊！\n📁 文件名：{file_name}\n📊 大小：{file_size_mb:.2f} MB\n📂 群号：{group_id}"
            elif user_id:
                # 发送私聊
                loop.run_until_complete(
                    bot.send_private_msg(user_id=int(user_id), message=message)
                )
                return f"✅ 文件已发送给用户！\n📁 文件名：{file_name}\n📊 大小：{file_size_mb:.2f} MB\n👤 用户：{user_id}"
            else:
                return "❌ 无法确定发送目标（需要 user_id 或 group_id）"
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 发送失败：网络超时，请稍后重试"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 发送失败：没有权限发送文件"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 发送失败：用户或群不存在"
            elif "too large" in error_msg.lower() or "过大" in error_msg:
                return f"❌ 发送失败：文件过大（{file_size_mb:.2f} MB）"
            else:
                return f"❌ 发送失败：{error_msg}\n💡 提示：可以尝试使用 upload_group_file 上传到群文件"
    
    async def _arun(self, file_path: str, user_id: Optional[str] = None, group_id: Optional[int] = None) -> str:
        """异步执行"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法发送文件"
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {file_path}"
        
        # 如果没有提供参数，从上下文获取
        if not user_id and not group_id:
            from tools.qq_interaction_tools import get_current_context
            context = get_current_context()
            user_id = context.get("user_id")
            group_id = context.get("group_id")
        
        try:
            from nonebot.adapters.onebot.v11 import Message, MessageSegment
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 构建文件消息段
            file_url = f"file:///{os.path.abspath(file_path)}"
            
            # 创建消息
            message = Message([
                MessageSegment.text(f"📁 {file_name} ({file_size_mb:.2f} MB)"),
                MessageSegment("file", {"file": file_url, "name": file_name})
            ])
            
            # 发送消息
            if group_id:
                # 发送到群聊
                await bot.send_group_msg(group_id=int(group_id), message=message)
                return f"✅ 文件已发送到群聊！\n📁 文件名：{file_name}\n📊 大小：{file_size_mb:.2f} MB\n📂 群号：{group_id}"
            elif user_id:
                # 发送私聊
                await bot.send_private_msg(user_id=int(user_id), message=message)
                return f"✅ 文件已发送给用户！\n📁 文件名：{file_name}\n📊 大小：{file_size_mb:.2f} MB\n👤 用户：{user_id}"
            else:
                return "❌ 无法确定发送目标（需要 user_id 或 group_id）"
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 发送失败：网络超时，请稍后重试"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 发送失败：没有权限发送文件"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 发送失败：用户或群不存在"
            elif "too large" in error_msg.lower() or "过大" in error_msg:
                return f"❌ 发送失败：文件过大（{file_size_mb:.2f} MB）"
            else:
                return f"❌ 发送失败：{error_msg}\n💡 提示：可以尝试使用 upload_group_file 上传到群文件"


# ==================== 工具列表 ====================
def get_send_file_tool():
    """获取发送文件工具"""
    return SendFileTool()
