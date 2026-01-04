"""
工具管理器 - Tool Manager
管理所有工具的注册、发现和调用
"""
from typing import Dict, List, Optional, Any
from nonebot.log import logger
from .tool_base import BaseTool, ToolResult, ToolDefinition


class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        logger.info("[工具管理器] 初始化")
    
    def register(self, tool: BaseTool):
        """注册工具
        
        Args:
            tool: 工具实例
        """
        tool_name = tool.get_name()
        if tool_name in self._tools:
            logger.warning(f"[工具管理器] 工具 {tool_name} 已存在，将被覆盖")
        
        self._tools[tool_name] = tool
        logger.info(f"[工具管理器] 注册工具: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具实例，不存在返回 None
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具定义（用于 Function Calling）
        
        Returns:
            工具定义列表
        """
        definitions = []
        for tool in self._tools.values():
            definition = tool.get_definition()
            definitions.append({
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": definition.parameters
                }
            })
        return definitions
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                message=f"工具 {tool_name} 不存在",
                error="TOOL_NOT_FOUND"
            )
        
        try:
            logger.info(f"[工具管理器] 执行工具: {tool_name}, 参数: {kwargs}")
            result = await tool.execute(**kwargs)
            logger.info(f"[工具管理器] 工具执行完成: {tool_name}, 成功: {result.success}")
            return result
        except Exception as e:
            logger.error(f"[工具管理器] 工具执行异常: {tool_name}, {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"工具执行失败: {str(e)}",
                error="EXECUTION_ERROR"
            )


# 全局工具管理器实例
tool_manager = ToolManager()




