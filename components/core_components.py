"""
核心组件定义
包括数据库、AI引擎等基础设施
"""
from core.component_registry import Component
from core.bootstrap import Bootstrap
import os


def check_database() -> bool:
    """检查数据库连接"""
    try:
        from services.database.database_service import get_database_service
        db_service = get_database_service()
        return db_service is not None
    except Exception as e:
        print(f"数据库检查失败: {e}")
        return False


def check_deepseek_api() -> bool:
    """检查 DeepSeek API"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ DEEPSEEK_API_KEY 未配置")
        return False
    return True


def check_qwen_api() -> bool:
    """检查通义千问 API"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️ DASHSCOPE_API_KEY 未配置")
        return False
    return True


async def init_database():
    """初始化数据库"""
    try:
        from services.database.database_service import get_database_service
        db_service = get_database_service()
        await db_service.initialize()
        print("  ✓ 数据库连接正常")
    except Exception as e:
        raise Exception(f"数据库初始化失败: {e}")


async def init_multimodal_ai():
    """初始化多模态AI"""
    try:
        from plugins.multimodal_ai import multimodal_ai
        print("  ✓ 多模态AI引擎就绪")
    except Exception as e:
        raise Exception(f"多模态AI初始化失败: {e}")


def register_core_components(bootstrap: Bootstrap):
    """注册核心组件"""
    
    # NoneBot 核心
    bootstrap.register_component(Component(
        name="nonebot_core",
        description="NoneBot2 核心框架",
        version="2.0.0",
        category="core",
        health_check=lambda: True  # NoneBot 运行中就是健康的
    ))
    
    # 数据库
    bootstrap.register_component(Component(
        name="database",
        description="SQLite 数据库",
        version="1.0.0",
        category="core",
        initialize=init_database,
        health_check=check_database
    ))
    
    # DeepSeek API
    bootstrap.register_component(Component(
        name="deepseek_api",
        description="DeepSeek AI 接口",
        version="1.0.0",
        category="core",
        health_check=check_deepseek_api,
        dependencies=[]
    ))
    
    # 通义千问 API
    bootstrap.register_component(Component(
        name="qwen_vl_api",
        description="通义千问-VL 图像理解接口",
        version="1.0.0",
        category="core",
        health_check=check_qwen_api,
        dependencies=[]
    ))
    
    # 多模态AI引擎
    bootstrap.register_component(Component(
        name="multimodal_ai",
        description="多模态AI引擎（图像+文本）",
        version="1.0.0",
        category="core",
        initialize=init_multimodal_ai,
        dependencies=["qwen_vl_api", "deepseek_api"]
    ))

