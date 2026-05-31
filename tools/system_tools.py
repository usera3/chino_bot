"""
系统工具 - 用于机器人自我诊断和监控
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import os


def _log_file_path(log_type: str) -> tuple[str, str] | None:
    """Resolve a log file path from environment-driven configuration."""
    log_dir = os.getenv(
        "CHINO_LOG_DIR",
        os.path.join(os.getenv("CHINO_PROJECT_ROOT", os.getcwd()), "logs"),
    )
    if log_type == "qq":
        return os.path.join(log_dir, "qq.log"), "NapCat"
    if log_type == "bot":
        return os.path.join(log_dir, "bot.log"), "机器人"
    return None


# ==================== 查看日志工具 ====================
class ViewLogsInput(BaseModel):
    """查看日志输入"""
    log_type: str = Field(
        default="qq",
        description="日志类型：'qq' 查看 NapCat 日志，'bot' 查看机器人日志"
    )
    lines: int = Field(
        default=5,
        description="读取的行数，默认 5 行（最新的）"
    )


class ViewLogsTool(BaseTool):
    """查看系统日志工具"""
    name: str = "view_logs"
    description: str = """查看系统日志，用于诊断问题。

⚠️ 使用场景（仅在以下情况使用）：
1. 工具调用失败后，需要查看错误原因
2. 发送消息/文件失败，需要查看 NapCat 日志
3. 用户报告功能异常，需要排查问题
4. 自我诊断系统状态

参数：
- log_type: 日志类型
  * "qq" - NapCat 日志（查看消息发送、文件上传等问题）
  * "bot" - 机器人日志（查看工具调用、错误堆栈等）
- lines: 读取行数（默认 5，建议 5-20）

返回：最新的日志内容

💡 典型使用流程：
1. 工具调用失败（如 send_file 失败）
2. 调用 view_logs(log_type="qq", lines=10)
3. 分析日志中的错误信息
4. 根据错误信息调整策略或告知用户

⚠️ 注意：
- 不要在正常情况下频繁调用
- 只在出错时使用
- 日志可能包含敏感信息，不要直接发送给用户"""
    args_schema: type[BaseModel] = ViewLogsInput
    
    def _run(self, log_type: str = "qq", lines: int = 5) -> str:
        """执行工具"""
        try:
            # 确定日志文件路径
            resolved = _log_file_path(log_type)
            if not resolved:
                return f"❌ 不支持的日志类型：{log_type}（支持：qq, bot）"
            log_file, log_name = resolved
            
            # 检查文件是否存在
            if not os.path.exists(log_file):
                return f"❌ 日志文件不存在：{log_file}"
            
            # 读取最后 N 行
            import subprocess
            result = subprocess.run(
                ["tail", f"-{lines}", log_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return f"❌ 读取日志失败：{result.stderr}"
            
            log_content = result.stdout.strip()
            
            if not log_content:
                return f"📭 {log_name}日志为空"
            
            # 格式化输出
            return f"""📋 {log_name}日志（最新 {lines} 行）
{'='*60}
{log_content}
{'='*60}

💡 提示：如果需要更多日志，可以增加 lines 参数"""
            
        except subprocess.TimeoutExpired:
            return f"❌ 读取日志超时"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ 读取日志失败：{str(e)}"
    
    async def _arun(self, log_type: str = "qq", lines: int = 5) -> str:
        """异步执行"""
        return self._run(log_type, lines)


# ==================== 系统状态工具 ====================
class CheckSystemStatusTool(BaseTool):
    """检查系统状态工具"""
    name: str = "check_system_status"
    description: str = """检查系统运行状态。

使用场景：
- 用户询问"机器人状态如何"
- 诊断系统问题
- 检查服务是否正常运行

返回：系统状态信息（进程、端口、内存等）"""
    
    def _run(self) -> str:
        """执行工具"""
        try:
            import subprocess
            import psutil
            
            status_info = []
            
            # 1. 检查进程
            status_info.append("🔍 进程状态")
            status_info.append("=" * 60)
            
            # 检查 bot.py 进程
            bot_running = False
            qq_running = False
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'bot.py' in cmdline:
                        bot_running = True
                        status_info.append(f"✅ 机器人进程: PID {proc.info['pid']}")
                    elif 'qq' in cmdline.lower() or 'napcat' in cmdline.lower():
                        qq_running = True
                        status_info.append(f"✅ QQ 进程: PID {proc.info['pid']}")
                except:
                    pass
            
            if not bot_running:
                status_info.append("❌ 机器人进程未运行")
            if not qq_running:
                status_info.append("⚠️ QQ 进程未检测到")
            
            # 2. 检查端口
            status_info.append("\n🌐 端口状态")
            status_info.append("=" * 60)
            
            # 检查 8080 端口
            result = subprocess.run(
                ["lsof", "-i", ":8080"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                status_info.append("✅ 端口 8080 正在监听")
            else:
                status_info.append("❌ 端口 8080 未监听")
            
            # 3. 内存使用
            status_info.append("\n💾 内存使用")
            status_info.append("=" * 60)
            
            memory = psutil.virtual_memory()
            status_info.append(f"总内存: {memory.total / (1024**3):.2f} GB")
            status_info.append(f"已使用: {memory.used / (1024**3):.2f} GB ({memory.percent}%)")
            status_info.append(f"可用: {memory.available / (1024**3):.2f} GB")
            
            # 4. 磁盘使用
            status_info.append("\n💿 磁盘使用")
            status_info.append("=" * 60)
            
            disk = psutil.disk_usage('/')
            status_info.append(f"总空间: {disk.total / (1024**3):.2f} GB")
            status_info.append(f"已使用: {disk.used / (1024**3):.2f} GB ({disk.percent}%)")
            status_info.append(f"可用: {disk.free / (1024**3):.2f} GB")
            
            return "\n".join(status_info)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ 检查系统状态失败：{str(e)}"
    
    async def _arun(self) -> str:
        """异步执行"""
        return self._run()


# ==================== 工具列表 ====================
def get_system_tools():
    """获取系统工具"""
    return [
        ViewLogsTool(),
        CheckSystemStatusTool(),
    ]
