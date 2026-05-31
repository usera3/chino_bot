"""
安全控制模块
提供路径验证、权限检查、命令验证等安全功能
"""
import os
from typing import Tuple, List
from datetime import datetime
import json


# ==================== 配置 ====================

# 项目根目录
PROJECT_ROOT = os.path.realpath(
    os.getenv("CHINO_PROJECT_ROOT", os.getcwd())
)

# 允许访问的路径
ALLOWED_PATHS = [PROJECT_ROOT]

# 管理员用户（QQ 号）
ADMIN_USERS = [
    user_id.strip()
    for user_id in os.getenv("CHINO_ADMIN_USERS", "").split(",")
    if user_id.strip()
]

# 安全命令白名单
SAFE_COMMANDS = {
    # 查看类
    "ls", "cat", "head", "tail", "grep", "find", "tree", "pwd",
    
    # Python 类
    "python", "python3", "pip list", "pip show", "pip freeze",
    
    # 测试类
    "pytest", "python -m pytest",
    
    # Git 类（只读）
    "git status", "git log", "git diff", "git show", "git branch",
}

# 危险命令黑名单
DANGEROUS_COMMANDS = {
    "rm", "mv", "cp",           # 文件操作
    "sudo", "su",               # 权限提升
    "chmod", "chown",           # 权限修改
    "kill", "pkill", "killall", # 进程管理
    "shutdown", "reboot",       # 系统控制
    "dd", "mkfs",               # 磁盘操作
}

# 需要用户确认的操作
REQUIRE_CONFIRMATION = {
    "write_file",      # 写入文件
    "execute_command", # 执行命令
    "delete_file",     # 删除文件
}

# 审计日志路径
AUDIT_LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "audit.log")


# ==================== 异常类 ====================

class SecurityError(Exception):
    """安全错误"""
    pass


class PathValidationError(SecurityError):
    """路径验证错误"""
    pass


class PermissionDeniedError(SecurityError):
    """权限拒绝错误"""
    pass


class CommandValidationError(SecurityError):
    """命令验证错误"""
    pass


# ==================== 路径验证 ====================

def validate_path(path: str) -> Tuple[bool, str]:
    """
    验证路径是否在允许的范围内
    
    Args:
        path: 要验证的路径
        
    Returns:
        (是否有效, 错误信息)
    """
    try:
        # 转换为绝对路径
        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)
        
        real_path = os.path.realpath(path)
        
        # 检查是否在允许的路径内
        for allowed_path in ALLOWED_PATHS:
            if real_path.startswith(allowed_path):
                return True, "OK"
        
        return False, f"路径不在允许的范围内: {real_path}"
    
    except Exception as e:
        return False, f"路径验证失败: {str(e)}"


def get_safe_path(path: str) -> str:
    """
    获取安全的路径（相对于项目根目录）
    
    Args:
        path: 输入路径
        
    Returns:
        安全的绝对路径
        
    Raises:
        PathValidationError: 路径验证失败
    """
    is_valid, error_msg = validate_path(path)
    
    if not is_valid:
        raise PathValidationError(error_msg)
    
    # 转换为绝对路径
    if not os.path.isabs(path):
        path = os.path.join(PROJECT_ROOT, path)
    
    return os.path.realpath(path)


# ==================== 权限检查 ====================

def check_permission(user_id: str, operation: str) -> Tuple[bool, str]:
    """
    检查用户是否有权限执行操作
    
    Args:
        user_id: 用户 ID（QQ 号）
        operation: 操作名称
        
    Returns:
        (是否有权限, 错误信息)
    """
    # 检查是否是需要确认的操作
    if operation in REQUIRE_CONFIRMATION:
        # 只有管理员可以执行需要确认的操作
        if user_id not in ADMIN_USERS:
            return False, f"操作 '{operation}' 需要管理员权限"
    
    return True, "OK"


def is_admin(user_id: str) -> bool:
    """
    检查用户是否是管理员
    
    Args:
        user_id: 用户 ID（QQ 号）
        
    Returns:
        是否是管理员
    """
    return user_id in ADMIN_USERS


# ==================== 命令验证 ====================

def validate_command(command: str) -> Tuple[bool, str]:
    """
    验证命令是否安全
    
    Args:
        command: 要执行的命令
        
    Returns:
        (是否安全, 错误信息)
    """
    # 分割命令
    cmd_parts = command.strip().split()
    
    if not cmd_parts:
        return False, "命令为空"
    
    base_cmd = cmd_parts[0]
    
    # 检查是否在危险命令黑名单中
    if base_cmd in DANGEROUS_COMMANDS:
        return False, f"危险命令: {base_cmd}"
    
    # 检查是否在安全命令白名单中
    if base_cmd not in SAFE_COMMANDS:
        # 检查是否是 python -m 形式
        if base_cmd == "python" and len(cmd_parts) > 2 and cmd_parts[1] == "-m":
            module = cmd_parts[2]
            if module in ["pytest", "pip"]:
                return True, "OK"
        
        return False, f"命令不在白名单中: {base_cmd}"
    
    # 检查命令中是否包含危险字符
    dangerous_chars = [";", "&&", "||", "|", ">", "<", "`", "$"]
    for char in dangerous_chars:
        if char in command:
            return False, f"命令包含危险字符: {char}"
    
    return True, "OK"


def get_safe_command(command: str) -> str:
    """
    获取安全的命令
    
    Args:
        command: 输入命令
        
    Returns:
        安全的命令
        
    Raises:
        CommandValidationError: 命令验证失败
    """
    is_valid, error_msg = validate_command(command)
    
    if not is_valid:
        raise CommandValidationError(error_msg)
    
    return command.strip()


# ==================== 操作审计 ====================

def audit_log(user_id: str, operation: str, details: dict, success: bool = True):
    """
    记录操作审计日志
    
    Args:
        user_id: 用户 ID
        operation: 操作名称
        details: 操作详情
        success: 是否成功
    """
    try:
        # 确保日志目录存在
        log_dir = os.path.dirname(AUDIT_LOG_PATH)
        os.makedirs(log_dir, exist_ok=True)
        
        # 构建日志条目
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "operation": operation,
            "details": details,
            "success": success,
        }
        
        # 写入日志
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    except Exception as e:
        print(f"⚠️ 审计日志写入失败: {e}")


def get_audit_logs(limit: int = 100) -> List[dict]:
    """
    获取审计日志
    
    Args:
        limit: 最多返回的日志条数
        
    Returns:
        日志列表
    """
    try:
        if not os.path.exists(AUDIT_LOG_PATH):
            return []
        
        logs = []
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    logs.append(log_entry)
                except:
                    continue
        
        # 返回最新的 N 条
        return logs[-limit:]
    
    except Exception as e:
        print(f"⚠️ 读取审计日志失败: {e}")
        return []


# ==================== 工具函数 ====================

def get_project_root() -> str:
    """获取项目根目录"""
    return PROJECT_ROOT


def is_path_in_project(path: str) -> bool:
    """检查路径是否在项目内"""
    is_valid, _ = validate_path(path)
    return is_valid


def get_relative_path(path: str) -> str:
    """
    获取相对于项目根目录的路径
    
    Args:
        path: 绝对路径
        
    Returns:
        相对路径
    """
    try:
        return os.path.relpath(path, PROJECT_ROOT)
    except:
        return path



def validate_command(command: str, user_id: str = "unknown") -> tuple[bool, str]:
    """
    验证命令是否安全
    
    Args:
        command: 要执行的命令
        user_id: 用户ID
        
    Returns:
        (是否安全, 错误信息)
    """
    # 1. 检查是否为空
    if not command or not command.strip():
        return False, "命令不能为空"
    
    # 2. 分割命令
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return False, "命令格式不正确"
    
    base_cmd = cmd_parts[0]
    
    # 3. 检查危险命令
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in command:
            audit_log(
                user_id=user_id,
                operation="validate_command",
                details={"command": command, "reason": f"包含危险命令: {dangerous}"},
                success=False
            )
            return False, f"危险命令：包含 '{dangerous}'"
    
    # 4. 检查命令白名单
    # 先检查完整命令
    if command in SAFE_COMMANDS:
        return True, "OK"
    
    # 再检查基础命令
    if base_cmd in SAFE_COMMANDS:
        return True, "OK"
    
    # 5. 特殊处理：python -m xxx
    if base_cmd in ["python", "python3"] and len(cmd_parts) >= 3 and cmd_parts[1] == "-m":
        module = cmd_parts[2]
        if module in ["pytest", "pip", "venv"]:
            return True, "OK"
    
    # 6. 特殊处理：pip xxx
    if base_cmd == "pip" and len(cmd_parts) >= 2:
        subcommand = cmd_parts[1]
        if subcommand in ["list", "show", "freeze", "check"]:
            return True, "OK"
    
    # 7. 特殊处理：git xxx
    if base_cmd == "git" and len(cmd_parts) >= 2:
        subcommand = cmd_parts[1]
        if subcommand in ["status", "log", "diff", "show", "branch"]:
            return True, "OK"
    
    # 8. 不在白名单中
    audit_log(
        user_id=user_id,
        operation="validate_command",
        details={"command": command, "reason": "不在白名单中"},
        success=False
    )
    return False, f"命令不在白名单中: {base_cmd}"


def get_safe_commands_list() -> list[str]:
    """获取安全命令列表"""
    return sorted(list(SAFE_COMMANDS))
