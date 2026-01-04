"""
功能注册表服务 - Function Registry Service
管理所有可用的功能模块
"""

from typing import Dict, List, Optional, Callable, Any
from nonebot.log import logger


class FunctionRegistry:
    """
    功能注册表 - 管理所有可用功能
    每个功能模块可以注册自己的能力
    """
    
    def __init__(self):
        self._functions: Dict[str, Dict] = {}
    
    def register(
        self,
        name: str,
        description: str,
        keywords: List[str],
        handler: Callable,
        examples: List[str] = None
    ):
        """
        注册一个功能
        
        Args:
            name: 功能名称
            description: 功能描述
            keywords: 触发关键词列表
            handler: 处理函数
            examples: 使用示例
        """
        self._functions[name] = {
            "name": name,
            "description": description,
            "keywords": keywords,
            "handler": handler,
            "examples": examples or []
        }
        logger.info(f"📝 注册功能: {name}")
    
    def get_all_functions_desc(self) -> str:
        """获取所有功能的描述（用于AI理解）"""
        if not self._functions:
            return "当前没有可用的特殊功能，我只能进行普通对话。"
        
        desc = "我具有以下功能：\n"
        for func_name, func_info in self._functions.items():
            desc += f"\n{func_name}: {func_info['description']}"
            if func_info['examples']:
                desc += f"\n  示例: {', '.join(func_info['examples'][:2])}"
        
        return desc
    
    def get_function_names(self) -> list:
        """获取所有已注册的功能名称列表"""
        return list(self._functions.keys())
    
    def get_function(self, name: str) -> Optional[Dict]:
        """获取指定功能"""
        return self._functions.get(name)
    
    def search_by_keywords(self, text: str) -> List[str]:
        """通过关键词搜索可能的功能"""
        matched = []
        text_lower = text.lower()
        
        for func_name, func_info in self._functions.items():
            for keyword in func_info['keywords']:
                if keyword.lower() in text_lower:
                    matched.append(func_name)
                    break
        
        return matched
    
    def get_all_functions(self) -> Dict[str, Dict]:
        """获取所有注册的功能"""
        return self._functions.copy()
    
    def count(self) -> int:
        """获取注册的功能数量"""
        return len(self._functions)


# ==================== 全局单例 ====================
_function_registry: Optional[FunctionRegistry] = None

def get_function_registry() -> FunctionRegistry:
    """获取功能注册表单例"""
    global _function_registry
    if _function_registry is None:
        _function_registry = FunctionRegistry()
    return _function_registry

