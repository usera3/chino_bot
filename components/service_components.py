"""
服务组件定义
包括外部服务、工具等
"""
from core.component_registry import Component
from core.bootstrap import Bootstrap
import os


def check_qq_connection() -> bool:
    """检查QQ连接"""
    # 这个在实际运行时才能检查
    # 暂时返回 True，实际应该检查 OneBot 连接状态
    return True


def check_file_storage() -> bool:
    """检查文件存储"""
    emoticon_dir = "emoticons"
    if not os.path.exists(emoticon_dir):
        try:
            os.makedirs(emoticon_dir)
        except Exception:
            return False
    return os.path.isdir(emoticon_dir) and os.access(emoticon_dir, os.W_OK)


def check_log_system() -> bool:
    """检查日志系统"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception:
            return False
    return os.path.isdir(log_dir) and os.access(log_dir, os.W_OK)


def register_service_components(bootstrap: Bootstrap):
    """注册服务组件"""
    
    # QQ 连接（OneBot）
    bootstrap.register_component(Component(
        name="qq_connection",
        description="QQ 机器人连接（OneBot V11）",
        version="1.0.0",
        category="service",
        health_check=check_qq_connection,
        dependencies=["nonebot_core"]
    ))
    
    # 文件存储
    bootstrap.register_component(Component(
        name="file_storage",
        description="文件存储系统（表情包等）",
        version="1.0.0",
        category="service",
        health_check=check_file_storage
    ))
    
    # 日志系统
    bootstrap.register_component(Component(
        name="log_system",
        description="日志记录系统",
        version="1.0.0",
        category="service",
        health_check=check_log_system
    ))




