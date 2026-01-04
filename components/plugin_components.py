"""
插件组件定义
包括聊天、表情、图像理解等功能插件
"""
from core.component_registry import Component
from core.bootstrap import Bootstrap


def check_chat_system() -> bool:
    """检查聊天系统（新架构）"""
    try:
        import handlers.chat_handler
        from services.chat.chat_service import get_chat_service
        return True
    except Exception:
        return False


def check_emotion_system() -> bool:
    """检查情感系统（新架构）"""
    try:
        from services.emotion import get_emotion_service
        return True
    except Exception:
        return False


def check_image_understanding() -> bool:
    """检查图像理解（新架构）"""
    try:
        # 检查新架构的 handler
        import handlers.image_handler
        # 检查服务层
        from services.image.image_service import get_image_service
        return True
    except Exception:
        return False


def check_emoticon_system() -> bool:
    """检查表情包系统（新架构）"""
    try:
        # emoticon_handler 已被重命名为 .bak，暂时跳过
        from services.emoticon import get_emoticon_service
        return True
    except Exception:
        return False


async def init_emoticon_system():
    """初始化表情包系统（新架构）"""
    try:
        # emoticon_handler 已被重命名为 .bak，暂时跳过
        from services.emoticon import get_emoticon_service
        emoticon_service = get_emoticon_service()
        # 初始化会在bot.py中统一处理
        print("  ✓ 表情包系统就绪（新架构）")
    except Exception as e:
        raise Exception(f"表情包系统初始化失败: {e}")


def check_proactive_chat() -> bool:
    """检查主动聊天（新架构）"""
    try:
        import handlers.proactive_handler
        from services.proactive import get_proactive_service
        return True
    except Exception:
        return False


def check_intelligent_dispatcher() -> bool:
    """检查智能调度（新架构）"""
    try:
        from services.dispatcher import get_dispatcher_service
        return True
    except Exception:
        return False


async def init_chat_system():
    """初始化聊天系统（新架构）"""
    try:
        import handlers.chat_handler
        from services.chat.chat_service import get_chat_service
        print("  ✓ 高级聊天系统就绪（新架构）")
    except Exception as e:
        raise Exception(f"聊天系统初始化失败: {e}")


async def init_emotion_system():
    """初始化情感系统（新架构）"""
    try:
        from services.emotion import get_emotion_service
        emotion_service = get_emotion_service()
        await emotion_service.initialize()
        print("  ✓ 动态情感系统就绪（新架构）")
    except Exception as e:
        raise Exception(f"情感系统初始化失败: {e}")


async def init_image_understanding():
    """初始化图像理解（新架构）"""
    try:
        # 导入新架构的 handler
        import handlers.image_handler
        # 导入服务层
        from services.image.image_service import get_image_service
        print("  ✓ 图像理解系统就绪（新架构）")
    except Exception as e:
        raise Exception(f"图像理解初始化失败: {e}")


async def init_proactive_chat():
    """初始化主动聊天系统（新架构）"""
    try:
        import handlers.proactive_handler
        from services.proactive import get_proactive_service
        proactive_service = get_proactive_service()
        await proactive_service.initialize()
        await proactive_service.start()
        print("  ✓ 主动聊天系统就绪（新架构）")
    except Exception as e:
        raise Exception(f"主动聊天系统初始化失败: {e}")


def register_plugin_components(bootstrap: Bootstrap):
    """注册插件组件"""
    
    # 聊天系统（关键组件）
    bootstrap.register_component(Component(
        name="chat_system",
        description="高级AI聊天系统（记忆+总结+个性化）",
        version="3.0.0",
        category="plugin",
        initialize=init_chat_system,
        health_check=check_chat_system,
        dependencies=["database", "deepseek_api"]
    ))
    
    # 情感系统（新架构）
    bootstrap.register_component(Component(
        name="emotion_system",
        description="动态情感系统（Service三层架构）",
        version="3.0.0",  # 新架构版本
        category="plugin",
        initialize=init_emotion_system,
        health_check=check_emotion_system,
        dependencies=["database"]
    ))
    
    # 图像理解（新架构）
    bootstrap.register_component(Component(
        name="image_understanding",
        description="图像理解系统（Handler→Service→Utils三层架构）",
        version="3.0.0",  # 新架构版本
        category="plugin",
        initialize=init_image_understanding,
        health_check=check_image_understanding,
        dependencies=["multimodal_ai", "emotion_system"]
    ))
    
    # 主动聊天（新架构）
    bootstrap.register_component(Component(
        name="proactive_chat",
        description="主动聊天引擎（Service三层架构+情感驱动）",
        version="3.0.0",  # 新架构版本
        category="plugin",
        initialize=init_proactive_chat,
        health_check=check_proactive_chat,
        dependencies=["emotion_system", "chat_system", "database"]
    ))
    
    # 智能调度（新架构）
    bootstrap.register_component(Component(
        name="intelligent_dispatcher",
        description="智能调度系统（Service三层架构+意图识别）",
        version="3.0.0",  # 新架构版本
        category="plugin",
        health_check=check_intelligent_dispatcher,
        dependencies=["chat_system", "emotion_system"]
    ))
    
    # 情感历史
    bootstrap.register_component(Component(
        name="emotion_history",
        description="情感历史数据系统（可视化）",
        version="1.0.0",
        category="plugin",
        dependencies=["emotion_system", "database"]
    ))

