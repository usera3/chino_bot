"""
LangChain 工具集 - 符合 MCP 标准
"""
from langchain.tools import BaseTool, StructuredTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Optional, Type
from nonebot.log import logger


# ==================== 计算器工具 ====================
class CalculatorInput(BaseModel):
    """计算器输入参数"""
    operation: str = Field(description="运算类型：add(加), subtract(减), multiply(乘), divide(除)")
    a: float = Field(description="第一个数")
    b: float = Field(description="第二个数")


def calculator_func(operation: str, a: float, b: float) -> str:
    """执行计算"""
    try:
        if operation == "add":
            result = a + b
            return f"{a} + {b} = {result}"
        elif operation == "subtract":
            result = a - b
            return f"{a} - {b} = {result}"
        elif operation == "multiply":
            result = a * b
            return f"{a} × {b} = {result}"
        elif operation == "divide":
            if b == 0:
                return "错误：除数不能为0"
            result = a / b
            return f"{a} ÷ {b} = {result}"
        else:
            return f"不支持的运算：{operation}"
    except Exception as e:
        return f"计算失败：{str(e)}"


class CalculatorTool(BaseTool):
    """计算器工具 - LangChain 版本"""
    name: str = "calculator"
    description: str = "执行基本的数学计算，支持加减乘除。当用户要求计算数学表达式时使用。"
    args_schema: Type[BaseModel] = CalculatorInput
    
    def _run(self, operation: str, a: float, b: float) -> str:
        """同步执行"""
        logger.info(f"[Calculator Tool] 执行计算: {operation}({a}, {b})")
        return calculator_func(operation, a, b)
    
    async def _arun(self, operation: str, a: float, b: float) -> str:
        """异步执行"""
        return self._run(operation, a, b)


# ==================== 天气查询工具 ====================
class WeatherInput(BaseModel):
    """天气查询输入参数"""
    city: str = Field(description="城市名称，如：北京、上海、广州")


def weather_func(city: str) -> str:
    """查询天气"""
    # 模拟天气数据
    weather_data = {
        "北京": "晴天，温度 15°C，湿度 45%",
        "上海": "多云，温度 18°C，湿度 60%",
        "广州": "小雨，温度 25°C，湿度 75%",
        "深圳": "晴天，温度 26°C，湿度 70%",
        "杭州": "阴天，温度 16°C，湿度 55%",
    }
    
    if city in weather_data:
        return f"{city}天气：{weather_data[city]}"
    else:
        return f"{city}的天气信息暂时无法获取（演示数据）"


class WeatherTool(BaseTool):
    """天气查询工具 - LangChain 版本"""
    name: str = "get_weather"
    description: str = "查询指定城市的天气信息。当用户询问天气时使用。"
    args_schema: Type[BaseModel] = WeatherInput
    
    def _run(self, city: str) -> str:
        """同步执行"""
        logger.info(f"[Weather Tool] 查询天气: {city}")
        return weather_func(city)
    
    async def _arun(self, city: str) -> str:
        """异步执行"""
        return self._run(city)


# ==================== 搜索工具（示例） ====================
class SearchInput(BaseModel):
    """搜索输入参数"""
    query: str = Field(description="搜索关键词")


def search_func(query: str) -> str:
    """执行搜索（演示版）"""
    # TODO: 接入真实搜索API
    return f"关于「{query}」的搜索结果：\n1. 相关信息A\n2. 相关信息B\n（演示数据）"


class SearchTool(BaseTool):
    """搜索工具 - LangChain 版本"""
    name: str = "search"
    description: str = "搜索互联网上的信息。当用户询问你不知道的实时信息时使用。"
    args_schema: Type[BaseModel] = SearchInput
    
    def _run(self, query: str) -> str:
        """同步执行"""
        logger.info(f"[Search Tool] 搜索: {query}")
        return search_func(query)
    
    async def _arun(self, query: str) -> str:
        """异步执行"""
        return self._run(query)


# ==================== 工具注册函数 ====================
def get_all_tools() -> list:
    """获取所有可用工具
    
    Returns:
        工具列表
    """
    return [
        CalculatorTool(),
        WeatherTool(),
        SearchTool(),
    ]


def get_tool_names() -> list[str]:
    """获取所有工具名称"""
    return [tool.name for tool in get_all_tools()]




