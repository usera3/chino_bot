"""
组件定义模块
为所有功能模块提供标准化的组件接口
"""
from core.bootstrap import get_bootstrap
from core.component_registry import Component

# 导入各个组件定义
from .core_components import register_core_components
from .plugin_components import register_plugin_components
from .service_components import register_service_components


def register_all_components():
    """
    注册所有组件
    这是系统自我感知的核心 - 在这里声明所有功能模块
    """
    bootstrap = get_bootstrap()
    
    # 注册核心组件
    register_core_components(bootstrap)
    
    # 注册插件组件
    register_plugin_components(bootstrap)
    
    # 注册服务组件
    register_service_components(bootstrap)


__all__ = ['register_all_components']




