"""
真正的 Function Calling Agent
让 AI 自己决定要不要用工具、用哪个工具
"""
from typing import List, Dict, Optional
from nonebot.log import logger
from utils.deepseek_client import get_deepseek_client
import json
import re


class FunctionCallingAgent:
    """
    基于标准 Function Calling 的 Agent
    """
    def __init__(self, bot=None):
        self.bot = bot
        self.deepseek_client = get_deepseek_client()
        self.tools = {}
        self._register_tools()
        logger.info("[Function Calling Agent] 初始化完成")
    
    def _register_tools(self):
        """注册所有工具"""
        from tools.calculator_tool import CalculatorTool
        from tools.weather_tool import WeatherTool
        from tools.datetime_tool import DateTimeTool
        from tools.search_tool import SearchTool
        from tools.user_info_tool import UserInfoTool, GroupMemberTool
        from tools.like_tool import LikeTool
        from tools.tts_tool import TTSTool
        from tools.recall_tool import RecallTool
        from tools.vision_tool import VisionTool
        from tools.tavily_search_tool import TavilySearchTool
        from tools.image_gen_tool import TongyiImageGenTool
        from tools.fetch_tool import FetchTool
        from tools.image_search_tool import ImageSearchTool
        from tools.amap_tool import AmapTool
        from tools.robotic_arm_tool import RoboticArmTool
        
        self.tools = {
            "calculator": CalculatorTool(),
            "get_weather": WeatherTool(),
            "get_datetime": DateTimeTool(),
            "web_search": SearchTool(),
            "get_user_info": UserInfoTool(bot=self.bot),
            "get_group_members": GroupMemberTool(bot=self.bot),
            "send_like": LikeTool(bot=self.bot),
            "text_to_speech": TTSTool(),
            "recall_message": RecallTool(bot=self.bot),
            "vision_understanding": VisionTool(),
            "tavily_search": TavilySearchTool(),
            "generate_image": TongyiImageGenTool(),
            "fetch_webpage": FetchTool(),
            "search_images": ImageSearchTool(),
            "search_nearby": AmapTool(),
            "control_robotic_arm": RoboticArmTool()
        }
        
        # 检查并禁用不可用的工具
        tools_to_remove = []
        for tool_name, tool_instance in self.tools.items():
            if hasattr(tool_instance, 'is_available') and not tool_instance.is_available():
                logger.warning(f"⚠️ 工具 '{tool_name}' 不可用，已禁用")
                tools_to_remove.append(tool_name)
        
        for tool_name in tools_to_remove:
            del self.tools[tool_name]
        
        logger.info(f"[Function Calling Agent] 已注册工具：{list(self.tools.keys())}")
        logger.info(f"[Function Calling Agent] 初始化完成")
    
    def set_bot(self, bot):
        """设置 bot 实例"""
        self.bot = bot
        from tools.user_info_tool import UserInfoTool, GroupMemberTool
        from tools.like_tool import LikeTool
        from tools.recall_tool import RecallTool
        self.tools["get_user_info"] = UserInfoTool(bot=bot)
        self.tools["get_group_members"] = GroupMemberTool(bot=bot)
        self.tools["send_like"] = LikeTool(bot=bot)
        self.tools["recall_message"] = RecallTool(bot=bot)
    
    def _get_tools_schema(self) -> List[Dict]:
        """
        获取工具的 JSON Schema（OpenAI 格式）
        """
        tools_schema = []
        
        for tool_name, tool in self.tools.items():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.get_name(),
                    "description": tool.get_description(),
                    "parameters": tool.get_parameters()
                }
            }
            tools_schema.append(schema)
        
        return tools_schema
    
    def _build_system_prompt(self) -> str:
        """构建包含工具信息的系统提示词"""
        tools_schema = self._get_tools_schema()
        
        # 格式化工具列表
        tools_desc = []
        for schema in tools_schema:
            func = schema["function"]
            tools_desc.append(f"- **{func['name']}**: {func['description']}")
        
        tools_list_str = "\n".join(tools_desc)
        
        return f"""你是一个运行在QQ平台上的AI助手机器人。

## 🛠️ 可用工具

你可以调用以下工具来帮助用户：

{tools_list_str}

## 📝 工具调用格式

当你需要使用工具时，请严格按照以下格式回复：

```
[CALL_TOOL]
tool_name: 工具名称
arguments: {{参数的JSON格式}}
[/CALL_TOOL]
```

**示例1：查询时间**
```
[CALL_TOOL]
tool_name: get_datetime
arguments: {{"query_type": "now"}}
[/CALL_TOOL]
```

**示例2：搜索信息**
```
[CALL_TOOL]
tool_name: web_search
arguments: {{"query": "今日新闻", "max_results": 3}}
[/CALL_TOOL]
```

**示例3：给用户点赞**
```
[CALL_TOOL]
tool_name: send_like
arguments: {{"user_id": "1446437177", "times": 10}}
[/CALL_TOOL]
```
注意：如果用户没有指定点赞次数，默认为10次。

**示例4：撤回消息**
```
[CALL_TOOL]
tool_name: recall_message
arguments: {{"user_id": "1446437177", "count": 1}}
[/CALL_TOOL]
```
注意：只能撤回最近2分钟内发送的消息，默认撤回1条。

## 🎯 决策原则

**何时调用工具：**
1. 用户询问**时间/日期/星期** → 必须调用 get_datetime
2. 用户询问**实时信息/新闻/价格/指数** → 必须调用 web_search  
3. 用户询问**自己的QQ号/昵称** → 调用 get_user_info
4. 用户要做**数学计算** → 调用 calculator
5. 用户询问**天气** → 调用 get_weather
6. 用户要求**点赞/给赞** → 调用 send_like（使用当前用户的QQ号）
7. 用户要求**撤回/删除消息/收回** → 调用 recall_message
8. 用户询问**图片内容**（"这是什么"、"图片里有什么"、"帮我看看这张图"等） → 调用 vision_understanding（image_url从消息上下文获取）

**何时不调用工具：**
- 闲聊（你好、再见等）
- 通用知识问答（Python是什么等）
- 情感交流

## ⚠️ 重要

- 你**不知道**当前时间、日期、星期 → 必须用工具
- 你**没有**实时信息、新闻、价格数据 → 必须用工具
- **绝不能编造**这些信息！

## 💬 回复风格

调用工具后，用自然、友好的语言回答用户，不要提及"工具"、"系统"等技术术语。

## 📌 上下文使用

每条消息会包含 `[上下文: 当前用户QQ号: xxx]`：
- 当用户说"给我点赞"时，使用上下文中的用户QQ号作为 send_like 的 user_id 参数
- 当用户说"我的QQ号"时，使用上下文中的用户QQ号作为 get_user_info 的 target_id 参数
"""
    
    async def chat(self, user_message: str, user_id: str = None, group_id: str = None) -> str:
        """
        处理用户消息
        
        Args:
            user_message: 用户消息
            user_id: 用户QQ号
            group_id: 群号
            
        Returns:
            AI回复
        """
        try:
            logger.info(f"[Function Calling Agent] 处理消息: {user_message}")
            
            # 构建消息
            system_prompt = self._build_system_prompt()
            
            # 添加上下文信息
            context_info = []
            if user_id:
                context_info.append(f"当前用户QQ号: {user_id}")
            if group_id:
                context_info.append(f"当前群号: {group_id}")
            
            full_user_message = user_message
            if context_info:
                context_str = " | ".join(context_info)
                full_user_message = f"[上下文: {context_str}]\n{user_message}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user_message}
            ]
            
            # 第一次调用：让AI决定
            ai_response = await self.deepseek_client.chat(messages, max_tokens=500)
            
            if not ai_response:
                return "抱歉，AI暂时无法回复。"
            
            logger.info(f"[Function Calling Agent] AI 原始回复: {ai_response[:200]}...")
            
            # 解析工具调用
            tool_call = self._parse_tool_call(ai_response)
            
            if tool_call:
                # AI决定调用工具
                tool_name = tool_call["tool_name"]
                arguments = tool_call["arguments"]
                
                logger.info(f"[Function Calling Agent] 🎯 AI决定调用工具: {tool_name}")
                logger.info(f"[Function Calling Agent] 参数: {arguments}")
                
                # 特殊处理：TTS工具 - 标记为语音消息，不需要AI再生成回复
                if tool_name == "text_to_speech":
                    tool_result_obj = await self._execute_tool_raw(tool_name, arguments, user_id, group_id)
                    
                    if tool_result_obj and tool_result_obj.success and tool_result_obj.data:
                        # 返回特殊格式：[VOICE:path]
                        voice_path = tool_result_obj.data.get("voice_path")
                        text = tool_result_obj.data.get("text", arguments.get("text", ""))
                        return f"[VOICE:{voice_path}|TEXT:{text}]"
                    else:
                        # 语音失败，返回文本
                        return arguments.get("text", "语音合成失败")
                
                # 其他工具：正常处理
                tool_result = await self._execute_tool(tool_name, arguments, user_id, group_id)
                
                if tool_result:
                    # 将工具结果返回给AI
                    messages.append({"role": "assistant", "content": ai_response})
                    messages.append({
                        "role": "user",
                        "content": f"工具执行结果：{tool_result}\n\n请根据这个结果自然地回答用户的问题。"
                    })
                    
                    final_response = await self.deepseek_client.chat(messages, max_tokens=300)
                    return final_response or tool_result
                else:
                    return "工具执行失败，抱歉无法回答。"
            else:
                # AI决定直接回复
                return ai_response
        
        except Exception as e:
            logger.error(f"[Function Calling Agent] 处理消息异常: {e}", exc_info=True)
            return "抱歉，AI在处理你的请求时遇到了问题。"
    
    def _parse_tool_call(self, response: str) -> Optional[Dict]:
        """
        解析AI的工具调用
        
        格式：
        [CALL_TOOL]
        tool_name: xxx
        arguments: {...}
        [/CALL_TOOL]
        """
        try:
            match = re.search(
                r'\[CALL_TOOL\]\s*tool_name:\s*(\w+)\s*arguments:\s*(\{[^\}]*\})\s*\[/CALL_TOOL\]',
                response,
                re.DOTALL
            )
            
            if match:
                tool_name = match.group(1).strip()
                arguments_str = match.group(2).strip()
                arguments = json.loads(arguments_str)
                
                return {
                    "tool_name": tool_name,
                    "arguments": arguments
                }
        except Exception as e:
            logger.error(f"[Function Calling Agent] 解析工具调用失败: {e}")
        
        return None
    
    async def _execute_tool_raw(
        self, tool_name: str, arguments: Dict, user_id: str = None, group_id: str = None
    ):
        """执行工具并返回原始结果对象"""
        tool = self.tools.get(tool_name)
        
        if not tool:
            logger.error(f"[Function Calling Agent] 工具不存在: {tool_name}")
            return None
        
        try:
            result = await tool.execute(**arguments)
            return result
        except Exception as e:
            logger.error(f"[Function Calling Agent] 工具 {tool_name} 执行异常: {e}", exc_info=True)
            return None
    
    async def _execute_tool(
        self, tool_name: str, arguments: Dict, user_id: str = None, group_id: str = None
    ) -> Optional[str]:
        """执行工具并返回字符串结果"""
        result = await self._execute_tool_raw(tool_name, arguments, user_id, group_id)
        
        if not result:
            return None
        
        # 兼容不同返回类型
        if isinstance(result, str):
            logger.info(f"[Function Calling Agent] ✅ 工具 {tool_name} 执行成功")
            return result
        elif hasattr(result, 'success') and result.success:
            logger.info(f"[Function Calling Agent] ✅ 工具 {tool_name} 执行成功")
            return result.message
        else:
            logger.error(f"[Function Calling Agent] ❌ 工具 {tool_name} 执行失败")
            return None


# 全局单例
_agent: Optional[FunctionCallingAgent] = None

def get_function_calling_agent() -> FunctionCallingAgent:
    """获取全局Agent实例"""
    global _agent
    if _agent is None:
        _agent = FunctionCallingAgent()
    return _agent

