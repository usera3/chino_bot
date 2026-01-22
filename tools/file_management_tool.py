"""
文件管理工具
用于删除临时文件、清理空间等
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import os


# ==================== 删除文件工具 ====================
class DeleteFileInput(BaseModel):
    """删除文件输入"""
    file_path: str = Field(description="要删除的文件路径（完整路径）")


class DeleteFileTool(BaseTool):
    """删除文件工具"""
    name: str = "delete_file"
    description: str = """删除指定的文件。

使用场景：
- 发送图片/文件后删除临时文件
- 清理不需要的文件
- 节省磁盘空间

⚠️ 典型工作流：
1. 截图：web_screenshot → 返回文件路径
2. 发送：send_image 或 send_file → 发送给用户
3. 清理：delete_file → 删除临时文件

参数：
- file_path: 文件完整路径（必需）

返回：删除结果"""
    args_schema: type[BaseModel] = DeleteFileInput
    
    def _run(self, file_path: str) -> str:
        """执行工具"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return f"⚠️ 文件不存在：{file_path}"
            
            # 检查是否是文件（不是目录）
            if not os.path.isfile(file_path):
                return f"❌ 这不是一个文件：{file_path}"
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_size_kb = file_size / 1024
            
            # 删除文件
            os.remove(file_path)
            
            # 确认删除
            if os.path.exists(file_path):
                return f"❌ 删除失败：文件仍然存在"
            
            return f"""✅ 文件已删除
📁 文件名：{file_name}
📊 释放空间：{file_size_kb:.2f} KB
🗑️ 路径：{file_path}"""
            
        except PermissionError:
            return f"❌ 删除失败：没有权限删除此文件"
        except Exception as e:
            return f"❌ 删除失败：{str(e)}"
    
    async def _arun(self, file_path: str) -> str:
        """异步执行"""
        return self._run(file_path)


# ==================== 清理临时文件工具 ====================
class CleanTempFilesInput(BaseModel):
    """清理临时文件输入"""
    pattern: str = Field(default="screenshot_*.png", description="文件匹配模式，例如：screenshot_*.png")
    directory: Optional[str] = Field(default=None, description="目录路径，默认为 Downloads")


class CleanTempFilesTool(BaseTool):
    """清理临时文件工具"""
    name: str = "clean_temp_files"
    description: str = """批量清理临时文件。

使用场景：
- 清理所有截图文件
- 清理特定类型的临时文件
- 定期清理空间

参数：
- pattern: 文件匹配模式（可选，默认 screenshot_*.png）
- directory: 目录路径（可选，默认 Downloads）

返回：清理结果"""
    args_schema: type[BaseModel] = CleanTempFilesInput
    
    def _run(self, pattern: str = "screenshot_*.png", directory: Optional[str] = None) -> str:
        """执行工具"""
        try:
            import glob
            
            # 确定目录
            if directory is None:
                directory = os.path.expanduser("~/Downloads")
            
            # 构建匹配路径
            search_path = os.path.join(directory, pattern)
            
            # 查找匹配的文件
            files = glob.glob(search_path)
            
            if not files:
                return f"📭 没有找到匹配的文件：{pattern}"
            
            # 删除文件
            deleted_count = 0
            total_size = 0
            failed_files = []
            
            for file_path in files:
                try:
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        total_size += file_size
                except Exception as e:
                    failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
            
            # 格式化结果
            total_size_mb = total_size / (1024 * 1024)
            
            result = f"""✅ 清理完成
📁 目录：{directory}
🔍 模式：{pattern}
🗑️ 删除：{deleted_count} 个文件
📊 释放空间：{total_size_mb:.2f} MB"""
            
            if failed_files:
                result += f"\n\n⚠️ 失败的文件：\n" + "\n".join(failed_files)
            
            return result
            
        except Exception as e:
            return f"❌ 清理失败：{str(e)}"
    
    async def _arun(self, pattern: str = "screenshot_*.png", directory: Optional[str] = None) -> str:
        """异步执行"""
        return self._run(pattern, directory)


# ==================== 工具列表 ====================
def get_file_management_tools():
    """获取文件管理工具"""
    return [
        DeleteFileTool(),
        CleanTempFilesTool(),
    ]
