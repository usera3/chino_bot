"""
计算器工具 - 示例工具
演示如何创建一个简单的工具
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any


class CalculatorTool(BaseTool):
    """计算器工具"""
    
    def get_name(self) -> str:
        return "calculator"
    
    def get_description(self) -> str:
        return "执行基本的数学计算，支持加减乘除"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "运算类型",
                    "enum": ["add", "subtract", "multiply", "divide"]
                },
                "a": {
                    "type": "number",
                    "description": "第一个数"
                },
                "b": {
                    "type": "number",
                    "description": "第二个数"
                }
            },
            "required": ["operation", "a", "b"]
        }
    
    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        """执行计算"""
        try:
            if operation == "add":
                result = a + b
                message = f"{a} + {b} = {result}"
            elif operation == "subtract":
                result = a - b
                message = f"{a} - {b} = {result}"
            elif operation == "multiply":
                result = a * b
                message = f"{a} × {b} = {result}"
            elif operation == "divide":
                if b == 0:
                    return ToolResult(
                        success=False,
                        message="除数不能为0",
                        error="DIVISION_BY_ZERO"
                    )
                result = a / b
                message = f"{a} ÷ {b} = {result}"
            else:
                return ToolResult(
                    success=False,
                    message=f"不支持的运算: {operation}",
                    error="INVALID_OPERATION"
                )
            
            return ToolResult(
                success=True,
                data=result,
                message=message
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"计算失败: {str(e)}",
                error="CALCULATION_ERROR"
            )




