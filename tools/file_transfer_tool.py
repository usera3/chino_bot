"""
文件传输工具
支持上传和下载群文件、私聊文件
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


# ==================== 上传群文件工具 ====================
class UploadGroupFileInput(BaseModel):
    """上传群文件输入"""
    file_path: str = Field(description="文件路径（本地文件路径）")
    name: str = Field(description="文件名称（上传后显示的名称）")
    group_id: Optional[int] = Field(default=None, description="群号，如果不提供则使用当前群")
    folder: Optional[str] = Field(default="/", description="上传到的文件夹路径，默认为根目录")


class UploadGroupFileTool(BaseTool):
    """上传文件到群文件"""
    name: str = "upload_group_file"
    description: str = """上传文件到 QQ 群文件。

使用场景：
- 用户说"上传xxx文件到群里"
- 用户说"把xxx文件发到群文件"
- 用户说"分享xxx文件"

参数说明：
- file_path: 本地文件路径（必需）
- name: 文件名称（必需）
- group_id: 群号（可选，不提供时使用当前群）
- folder: 上传到的文件夹路径（可选，默认为根目录）

注意：
- 文件必须存在于本地
- 文件大小限制取决于 QQ 群文件限制
- 只能在群聊中使用"""
    args_schema: type[BaseModel] = UploadGroupFileInput
    
    def _run(self, file_path: str, name: str, group_id: Optional[int] = None, folder: str = "/") -> str:
        """执行工具"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法上传文件"
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {file_path}"
        
        # 如果没有提供 group_id，从上下文获取
        if not group_id:
            from tools.qq_interaction_tools import get_current_context
            context = get_current_context()
            group_id = context.get("group_id")
            
            if not group_id:
                return "❌ 当前不在群聊中，无法上传群文件"
        
        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 调用 OneBot API
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                bot.call_api(
                    "upload_group_file",
                    group_id=int(group_id),
                    file=file_path,
                    name=name,
                    folder=folder
                )
            )
            
            return f"✅ 文件上传成功！\n📁 文件名：{name}\n📊 大小：{file_size_mb:.2f} MB\n📂 位置：群 {group_id} 的 {folder}"
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 上传失败：网络超时，请稍后重试"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 上传失败：没有权限上传文件到群 {group_id}"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 上传失败：群 {group_id} 不存在"
            elif "too large" in error_msg.lower() or "过大" in error_msg:
                return f"❌ 上传失败：文件过大（{file_size_mb:.2f} MB），超过群文件限制"
            else:
                return f"❌ 上传失败：{error_msg}"
    
    async def _arun(self, file_path: str, name: str, group_id: Optional[int] = None, folder: str = "/") -> str:
        """异步执行"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法上传文件"
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {file_path}"
        
        # 如果没有提供 group_id，从上下文获取
        if not group_id:
            from tools.qq_interaction_tools import get_current_context
            context = get_current_context()
            group_id = context.get("group_id")
            
            if not group_id:
                return "❌ 当前不在群聊中，无法上传群文件"
        
        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 调用 OneBot API
            await bot.call_api(
                "upload_group_file",
                group_id=int(group_id),
                file=file_path,
                name=name,
                folder=folder
            )
            
            return f"✅ 文件上传成功！\n📁 文件名：{name}\n📊 大小：{file_size_mb:.2f} MB\n📂 位置：群 {group_id} 的 {folder}"
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 上传失败：网络超时，请稍后重试"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 上传失败：没有权限上传文件到群 {group_id}"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 上传失败：群 {group_id} 不存在"
            elif "too large" in error_msg.lower() or "过大" in error_msg:
                return f"❌ 上传失败：文件过大（{file_size_mb:.2f} MB），超过群文件限制"
            else:
                return f"❌ 上传失败：{error_msg}"


# ==================== 获取群文件列表工具 ====================
class GetGroupFilesInput(BaseModel):
    """获取群文件列表输入"""
    group_id: Optional[int] = Field(default=None, description="群号，如果不提供则使用当前群")
    folder_id: Optional[str] = Field(default=None, description="文件夹 ID，不提供则获取根目录")


class GetGroupFilesTool(BaseTool):
    """获取群文件列表"""
    name: str = "get_group_files"
    description: str = """获取 QQ 群文件列表。

使用场景：
- 用户问"群里有什么文件"
- 用户说"查看群文件"
- 用户说"列出群文件"

参数说明：
- group_id: 群号（可选，不提供时使用当前群）
- folder_id: 文件夹 ID（可选，不提供则获取根目录）

注意：
- 只能在群聊中使用
- 返回文件名、大小、上传时间等信息"""
    args_schema: type[BaseModel] = GetGroupFilesInput
    
    def _run(self, group_id: Optional[int] = None, folder_id: Optional[str] = None) -> str:
        """执行工具"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法获取群文件"
        
        # 如果没有提供 group_id，从上下文获取
        if not group_id:
            from tools.qq_interaction_tools import get_current_context
            context = get_current_context()
            group_id = context.get("group_id")
            
            if not group_id:
                return "❌ 当前不在群聊中，无法获取群文件"
        
        try:
            # 调用 OneBot API
            loop = asyncio.get_event_loop()
            
            if folder_id:
                # 获取子目录文件
                result = loop.run_until_complete(
                    bot.call_api(
                        "get_group_files_by_folder",
                        group_id=int(group_id),
                        folder_id=folder_id
                    )
                )
            else:
                # 获取根目录文件
                result = loop.run_until_complete(
                    bot.call_api(
                        "get_group_root_files",
                        group_id=int(group_id)
                    )
                )
            
            # 解析结果
            files = result.get("files", [])
            folders = result.get("folders", [])
            
            if not files and not folders:
                return f"📂 群 {group_id} 的文件夹是空的"
            
            # 构建返回信息
            info = f"📂 群 {group_id} 的文件列表：\n\n"
            
            # 文件夹
            if folders:
                info += "📁 文件夹：\n"
                for folder in folders:
                    folder_name = folder.get("folder_name", "未知")
                    folder_id = folder.get("folder_id", "")
                    info += f"  - {folder_name} (ID: {folder_id})\n"
                info += "\n"
            
            # 文件
            if files:
                info += "📄 文件：\n"
                for file in files:
                    file_name = file.get("file_name", "未知")
                    file_size = file.get("file_size", 0)
                    file_size_mb = file_size / (1024 * 1024)
                    info += f"  - {file_name} ({file_size_mb:.2f} MB)\n"
            
            return info
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 获取失败：网络超时，请稍后重试"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 获取失败：没有权限查看群 {group_id} 的文件"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 获取失败：群 {group_id} 不存在"
            else:
                return f"❌ 获取失败：{error_msg}"
    
    async def _arun(self, group_id: Optional[int] = None, folder_id: Optional[str] = None) -> str:
        """异步执行"""
        bot = get_bot_instance()
        if not bot:
            return "❌ Bot 未初始化，无法获取群文件"
        
        # 如果没有提供 group_id，从上下文获取
        if not group_id:
            from tools.qq_interaction_tools import get_current_context
            context = get_current_context()
            group_id = context.get("group_id")
            
            if not group_id:
                return "❌ 当前不在群聊中，无法获取群文件"
        
        try:
            # 调用 OneBot API
            if folder_id:
                # 获取子目录文件
                result = await bot.call_api(
                    "get_group_files_by_folder",
                    group_id=int(group_id),
                    folder_id=folder_id
                )
            else:
                # 获取根目录文件
                result = await bot.call_api(
                    "get_group_root_files",
                    group_id=int(group_id)
                )
            
            # 解析结果
            files = result.get("files", [])
            folders = result.get("folders", [])
            
            if not files and not folders:
                return f"📂 群 {group_id} 的文件夹是空的"
            
            # 构建返回信息
            info = f"📂 群 {group_id} 的文件列表：\n\n"
            
            # 文件夹
            if folders:
                info += "📁 文件夹：\n"
                for folder in folders:
                    folder_name = folder.get("folder_name", "未知")
                    folder_id = folder.get("folder_id", "")
                    info += f"  - {folder_name} (ID: {folder_id})\n"
                info += "\n"
            
            # 文件
            if files:
                info += "📄 文件：\n"
                for file in files:
                    file_name = file.get("file_name", "未知")
                    file_size = file.get("file_size", 0)
                    file_size_mb = file_size / (1024 * 1024)
                    info += f"  - {file_name} ({file_size_mb:.2f} MB)\n"
            
            return info
            
        except Exception as e:
            error_msg = str(e)
            
            # 解析具体的错误原因
            if "timeout" in error_msg.lower():
                return f"❌ 获取失败：网络超时，请稍后重试"
            elif "permission" in error_msg.lower() or "权限" in error_msg:
                return f"❌ 获取失败：没有权限查看群 {group_id} 的文件"
            elif "not found" in error_msg.lower() or "不存在" in error_msg:
                return f"❌ 获取失败：群 {group_id} 不存在"
            else:
                return f"❌ 获取失败：{error_msg}"


# ==================== 工具列表 ====================
def get_all_file_transfer_tools():
    """获取所有文件传输工具"""
    return [
        UploadGroupFileTool(),
        GetGroupFilesTool(),
    ]
