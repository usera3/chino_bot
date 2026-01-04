"""
天气查询工具 - 示例工具
演示如何创建一个需要外部API的工具
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any


class WeatherTool(BaseTool):
    """天气查询工具"""
    
    def get_name(self) -> str:
        return "get_weather"
    
    def get_description(self) -> str:
        return "查询指定城市的天气信息"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如：北京、上海、广州"
                }
            },
            "required": ["city"]
        }
    
    async def execute(self, city: str) -> ToolResult:
        """查询天气（演示版本，返回模拟数据）"""
        # TODO: 接入真实天气API
        # 这里用模拟数据演示
        
        weather_data = {
            "北京": {"temperature": "15°C", "condition": "晴", "humidity": "45%"},
            "上海": {"temperature": "18°C", "condition": "多云", "humidity": "60%"},
            "广州": {"temperature": "25°C", "condition": "小雨", "humidity": "75%"},
        }
        
        if city in weather_data:
            data = weather_data[city]
            message = f"{city}天气：{data['condition']}，温度{data['temperature']}，湿度{data['humidity']}"
            return ToolResult(
                success=True,
                data=data,
                message=message
            )
        else:
            return ToolResult(
                success=True,
                data={"temperature": "20°C", "condition": "未知", "humidity": "50%"},
                message=f"{city}的天气信息暂时无法获取（演示数据）"
            )




