"""
智脑AI机器人 - 主程序入口
采用组件化架构，支持自我感知和健康检查
"""
import nonebot 
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
import asyncio
import sys

# 导入核心系统
from core.bootstrap import get_bootstrap
from core.component_registry import Component, ComponentStatus

# 导入组件定义
from components import register_all_components


async def startup_system():
    """启动系统"""
    bootstrap = get_bootstrap()
    
    # 注册所有组件
    register_all_components()
    
    # 标记关键组件（这些组件失败会导致系统无法启动）
    bootstrap.mark_as_critical("nonebot_core")
    bootstrap.mark_as_critical("database")
    bootstrap.mark_as_critical("chat_system")
    
    # 执行启动
    success = await bootstrap.startup()
    
    if not success:
        print("❌ 系统启动失败，请检查日志")
        sys.exit(1)
    
    # 初始化聊天数据库
    try:
        from services.database.database_service import get_database_service
        db_service = get_database_service()
        await db_service.initialize()
        print("✅ 聊天数据库初始化成功")
    except Exception as e:
        print(f"⚠️ 聊天数据库初始化失败: {e}")
    
    # 初始化 TTS 服务
    try:
        from services.tts import initialize_tts_service
        await initialize_tts_service()
        print("✅ TTS 语音合成服务初始化成功")
    except Exception as e:
        print(f"⚠️ TTS 服务初始化失败: {e}")
    
    return success


def main():
    """主函数"""
    # 初始化 NoneBot
    nonebot.init()
    
    # 获取驱动器并注册适配器
    driver = nonebot.get_driver()
    driver.register_adapter(ONEBOT_V11Adapter)
    
    # 注册启动钩子
    @driver.on_startup
    async def on_startup():
        """系统启动时执行"""
        await startup_system()
    
    # 注册关闭钩子
    @driver.on_shutdown
    async def on_shutdown():
        """系统关闭时执行"""
        bootstrap = get_bootstrap()
        await bootstrap.shutdown()
    
    # 加载内置插件
    nonebot.load_builtin_plugins('echo')
    
    # 从配置文件加载插件
    nonebot.load_from_toml("pyproject.toml")
    
    # 显式加载新架构的 handlers
    # 这样 NoneBot 就能识别它们
    import handlers.image_handler
    import handlers.chat_handler
    import handlers.proactive_handler
    import handlers.like_handler
    
    # 运行
    nonebot.run()


if __name__ == "__main__":
    main()