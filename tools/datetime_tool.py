"""
时间工具 - 获取系统时间、日期等信息
"""
from core.tool_base import BaseTool, ToolResult
from nonebot.log import logger
from datetime import datetime, timezone, timedelta
from typing import Dict, Any


class DateTimeTool(BaseTool):
    """
    时间工具 - AI 无法自己获取当前时间，需要通过这个工具。
    """
    
    def get_name(self) -> str:
        return "get_datetime"
    
    def get_description(self) -> str:
        return "获取当前系统时间、日期、星期等信息。AI 无法自己知道现在几点，必须调用此工具。"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "description": "查询类型：'now'(当前时间), 'date'(日期), 'weekday'(星期), 'timestamp'(时间戳), 'timezone'(时区转换)",
                    "enum": ["now", "date", "weekday", "timestamp", "timezone"],
                    "default": "now"
                }
            }
        }

    async def execute(self, query_type: str = "now", **kwargs) -> str:
        """
        执行时间查询
        
        Args:
            query_type: 查询类型
        
        Returns:
            str: 时间信息（简化返回，不用 ToolResult）
        """
        logger.info(f"执行时间工具，类型: {query_type}")
        
        try:
            # 获取东八区（北京时间）的当前时间
            tz = timezone(timedelta(hours=8))
            now = datetime.now(tz)
            
            if query_type == "now":
                # 完整的当前时间
                result = now.strftime("%Y年%m月%d日 %H:%M:%S")
                weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
                return f"当前时间：{result} {weekday}"
            
            elif query_type == "date":
                # 仅日期
                return now.strftime("今天是 %Y年%m月%d日")
            
            elif query_type == "weekday":
                # 仅星期
                weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
                return f"今天是 {weekday}"
            
            elif query_type == "timestamp":
                # Unix 时间戳
                timestamp = int(now.timestamp())
                return f"当前时间戳：{timestamp}"
            
            elif query_type == "timezone":
                # 显示不同时区的时间
                result = f"北京时间(UTC+8): {datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M:%S')}\n"
                result += f"东京时间(UTC+9): {datetime.now(timezone(timedelta(hours=9))).strftime('%H:%M:%S')}\n"
                result += f"纽约时间(UTC-5): {datetime.now(timezone(timedelta(hours=-5))).strftime('%H:%M:%S')}\n"
                result += f"伦敦时间(UTC+0): {datetime.now(timezone.utc).strftime('%H:%M:%S')}"
                return result
            
            else:
                return f"未知的查询类型: {query_type}。支持的类型：now, date, weekday, timestamp, timezone"
        
        except Exception as e:
            logger.error(f"时间工具执行失败: {e}")
            return f"获取时间失败：{e}"
