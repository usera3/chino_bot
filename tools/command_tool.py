"""
命令执行工具
提供安全的命令执行功能
"""
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import subprocess
import os
from core.security import validate_command, audit_log, get_project_root, is_admin


# ==================== 执行命令工具 ====================

class ExecuteCommandInput(BaseModel):
    """执行命令输入"""
    command: str = Field(description="要执行的命令，例如：ls -la, pytest test_butler.py, git status")
    working_dir: str = Field(default=".", description="工作目录（相对于项目根目录），默认为当前目录")
    timeout: int = Field(default=30, description="超时时间（秒），默认 30 秒")


class ExecuteCommandTool(BaseTool):
    """执行命令工具"""
    name: str = "execute_command"
    description: str = """执行系统命令。

⚠️ 重要安全说明：
- 只能执行白名单中的安全命令
- 所有操作会被审计记录
- 危险命令会被拦截

✅ 允许的命令类型：
1. **查看类**：ls, cat, head, tail, grep, find, tree, pwd
2. **Python 类**：python, python3, pip list, pip show
3. **测试类**：pytest, python -m pytest
4. **Git 类**：git status, git log, git diff, git show

使用场景：
- 用户说"运行测试" → execute_command("pytest test_butler.py")
- 用户说"查看 git 状态" → execute_command("git status")
- 用户说"列出文件" → execute_command("ls -la")
- 用户说"查看 Python 版本" → execute_command("python --version")

参数：
- command: 要执行的命令（必需）
- working_dir: 工作目录（可选，默认当前目录）
- timeout: 超时时间（可选，默认 30 秒）

返回：命令输出结果

⚠️ 注意：
- 命令必须在白名单中
- 危险命令会被拦截
- 超时会自动终止
- 所有操作会被记录"""
    args_schema: type[BaseModel] = ExecuteCommandInput
    
    def _run(self, command: str, working_dir: str = ".", timeout: int = 30) -> str:
        """执行工具"""
        try:
            # 1. 验证命令
            is_valid, error_msg = validate_command(command, user_id="butler")
            
            if not is_valid:
                audit_log(
                    user_id="butler",
                    operation="execute_command",
                    details={"command": command, "error": error_msg},
                    success=False
                )
                return f"❌ 命令验证失败: {error_msg}"
            
            # 2. 获取工作目录
            project_root = get_project_root()
            if working_dir == ".":
                work_dir = project_root
            else:
                work_dir = os.path.join(project_root, working_dir)
            
            # 验证工作目录
            if not os.path.exists(work_dir):
                return f"❌ 工作目录不存在: {working_dir}"
            
            if not os.path.isdir(work_dir):
                return f"❌ 工作目录不是目录: {working_dir}"
            
            # 3. 执行命令
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                # 4. 格式化输出
                output = ""
                
                if result.stdout:
                    output += result.stdout
                
                if result.stderr:
                    if output:
                        output += "\n"
                    output += f"[stderr]\n{result.stderr}"
                
                if not output:
                    output = "[命令执行完成，无输出]"
                
                # 5. 记录审计日志
                audit_log(
                    user_id="butler",
                    operation="execute_command",
                    details={
                        "command": command,
                        "working_dir": working_dir,
                        "return_code": result.returncode,
                        "output_length": len(output)
                    },
                    success=result.returncode == 0
                )
                
                # 6. 返回结果
                status_icon = "✅" if result.returncode == 0 else "⚠️"
                
                result_text = f"""{status_icon} 命令执行完成
📝 命令: {command}
📁 目录: {working_dir}
🔢 返回码: {result.returncode}

{'='*60}
{output}
{'='*60}"""
                
                # 限制输出长度
                if len(result_text) > 2000:
                    result_text = result_text[:2000] + "\n\n... (输出过长，已截断)"
                
                return result_text
            
            except subprocess.TimeoutExpired:
                audit_log(
                    user_id="butler",
                    operation="execute_command",
                    details={"command": command, "error": "超时"},
                    success=False
                )
                return f"❌ 命令执行超时（{timeout} 秒）: {command}"
            
            except Exception as e:
                audit_log(
                    user_id="butler",
                    operation="execute_command",
                    details={"command": command, "error": str(e)},
                    success=False
                )
                return f"❌ 命令执行失败: {str(e)}"
        
        except Exception as e:
            return f"❌ 执行命令时发生错误: {str(e)}"
    
    async def _arun(self, command: str, working_dir: str = ".", timeout: int = 30) -> str:
        """异步执行"""
        return self._run(command, working_dir, timeout)


# ==================== 工具列表 ====================

def get_command_tool():
    """获取命令执行工具"""
    return ExecuteCommandTool()
