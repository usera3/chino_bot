"""
LangChain Agent - 基于 LangChain 1.0+ 的智能代理
使用 DeepSeek API + MCP 标准工具系统
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Optional
from nonebot.log import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool as langchain_tool

from utils.deepseek_client import get_deepseek_client
from core.tool_matcher import get_tool_matcher


class SimpleLangChainAgent:
    """
    简化版 LangChain Agent，直接使用 DeepSeek Client
    实现 MCP 标准的工具调用
    """
    def __init__(self, system_prompt: str = None, verbose: bool = True, bot=None):
        """
        初始化 Agent
        
        Args:
            system_prompt: 系统提示词
            verbose: 是否输出详细日志
            bot: NoneBot bot 实例（用于某些需要bot的工具）
        """
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.verbose = verbose
        self.bot = bot
        self.deepseek_client = get_deepseek_client()
        self.tool_matcher = get_tool_matcher()  # 🆕 初始化工具匹配器
        self.tools = {}
        self._register_tools()
        
        if not self.deepseek_client.is_available():
            logger.warning("[LangChain Agent] DeepSeek API 未配置")
        else:
            logger.info("[LangChain Agent] 初始化完成，已注册工具")
    
    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        return """你是一个运行在QQ平台上的AI助手机器人，拥有工具能力。

# 🤖 重要：你的身份和能力

- 你是一个**QQ机器人**，运行在QQ平台上
- 每条消息会附带**上下文信息**：[上下文: 当前用户QQ号: xxx | 当前群号: xxx]
- 你可以通过工具**访问QQ用户信息**（用户QQ号、昵称、群信息等）
- 当用户问"我的QQ号"、"我是谁"、"这个群叫什么"时，你**有能力**通过工具查询
- **不要说**"我无法访问个人信息" —— 你有 get_user_info 工具，并且上下文中有用户ID！
- 使用工具时，从**上下文**中提取用户QQ号或群号作为参数

# 📋 每次回复前的思考流程（心理活动，不要输出）

收到用户消息后，按以下步骤思考：

**步骤1：意图判断**
- 这是【指令/查询】（需要工具）还是【闲聊/情感交流】（直接回复）？
- 关键词检测：
  * "查询/搜索/今日/最新/价格/指数" → 指令
  * "你好/谢谢/怎么样" → 闲聊

**步骤2：能力检查**
如果是指令，检查我的工具箱：
- 涉及【时间/日期/星期】→ 有 get_datetime 工具 ✅
- 涉及【实时信息/新闻/价格】→ 有 web_search 工具 ✅
- 涉及【计算】→ 有 calculator 工具 ✅
- 涉及【天气】→ 有 get_weather 工具 ✅
- 涉及【"我的QQ号"/"我是谁"/"用户信息"】→ 有 get_user_info 工具 ✅（我是QQ机器人，能查！）
- 涉及【"这个群"/"群名"/"群成员"】→ 有 get_user_info/get_group_members 工具 ✅

**步骤3：决策**
- ✅ 有工具能解决 → **必须**调用工具！（否则会编造错误信息）
- ❌ 没有工具能解决 → 坦诚告知用户，不要编造
- 💬 普通闲聊 → 直接友好回复

# 🚨 严格规则（必须遵守）

1. 你的知识截止到2023年，你**不知道**现在的时间、日期、星期
2. 你**不知道**任何实时信息：股票、价格、指数、汇率等
3. 当判断需要工具时，你**必须**调用工具，**绝不能**自己编造或猜测

# 🛠️ 可用工具详解

1. **get_datetime** - 获取当前时间/日期/星期
   - 能解决：所有关于"现在时间"的问题
   - 你自己不知道：现在几点、今天星期几、今天日期
   - 参数: "now"(时间), "date"(日期), "weekday"(星期)

2. **web_search** - 搜索互联网最新信息
   - 能解决：
     * 任何实时数据（价格、指数、汇率、比分）
     * 最新新闻、热点事件
     * 你不确定或不知道的事实
     * 2024年之后的信息（你的知识截止2023年）
   - 你自己不知道：
     * 股票、比特币、道琼斯等任何价格
     * 今天的新闻、热搜、头条
     * 最新研究、最新产品、最新政策
   - 参数: 搜索关键词

3. **calculator** - 精确数学计算
   - 能解决：复杂运算、大数字计算
   - 参数: 数学表达式

4. **get_weather** - 实时天气查询
   - 能解决：城市的当前天气
   - 参数: 城市名

5. **get_user_info** - 获取用户/群聊信息
   - 能解决：查询用户昵称、群名称、成员数等
   - 你自己不知道：当前用户是谁、当前群叫什么名字
   - 参数: query_type("self"机器人信息/"user"用户/"group"群), target_id(QQ号/群号)

6. **get_group_members** - 获取群成员列表
   - 能解决：查看群里有谁、群成员昵称
   - 你自己不知道：群里有哪些人
   - 参数: group_id(群号)

# 📝 工具调用方法

当你需要调用工具时，**只返回**这个格式，不要加任何其他文字：

[TOOL:工具名]参数[/TOOL]

# ✅ 正确示例（带思考过程）

**例1：时间查询**
用户："现在几点"
思考：涉及"时间" → 指令 → 有 get_datetime 工具 → 调用！
你：[TOOL:get_datetime]now[/TOOL]

**例2：实时信息**
用户："今日道琼斯指数"
思考：涉及"今日+指数" → 指令 → 有 web_search 工具 → 调用！
你：[TOOL:web_search]今日道琼斯指数[/TOOL]

**例3：最新信息**
用户："比特币价格"
思考：涉及"价格" → 实时信息 → 有 web_search 工具 → 调用！
你：[TOOL:web_search]比特币价格[/TOOL]

**例4：计算**
用户："帮我算 123+456"
思考：涉及"计算" → 指令 → 有 calculator 工具 → 调用！
你：[TOOL:calculator]123+456[/TOOL]

**例5：天气**
用户："北京天气"
思考：涉及"天气" → 指令 → 有 get_weather 工具 → 调用！
你：[TOOL:get_weather]北京[/TOOL]

**例6：用户信息**
[上下文: 当前用户QQ号: 1446437177]
用户消息："我的QQ号是多少"
思考：涉及"用户信息" → 指令 → 上下文中有当前用户QQ号 → 调用工具查询详细信息！
你：[TOOL:get_user_info]user:1446437177[/TOOL]

注意：当有上下文信息时，使用上下文中的ID作为参数！

# ❌ 不需要工具的例子

**例1：问候**
用户："你好"
思考：普通问候 → 闲聊 → 不需要工具 → 直接回复
你：你好！很高兴见到你~ 😊

**例2：通用知识**
用户："Python是什么"
思考：通用知识，我知道 → 不需要工具 → 直接回复
你：Python是一种编程语言...

# ⚠️ 核心原则

- 涉及"时间/日期/星期" → 必须调用 get_datetime
- 涉及"价格/指数/汇率/股票/最新" → 必须调用 web_search
- **绝不编造数据！不知道就调用工具！**

# 🎯 记住：每次回复前都要走思考流程！

1. 先判断：指令 or 闲聊？
2. 再检查：我的工具箱能解决吗？
3. 最后决策：调用工具 or 直接回复？

**这个思考过程是你的心理活动，不要输出给用户！**
"""
    
    def set_bot(self, bot):
        """设置 bot 实例并重新注册需要 bot 的工具"""
        self.bot = bot
        # 重新初始化需要 bot 的工具
        from tools.user_info_tool import UserInfoTool, GroupMemberTool
        self.tools["get_user_info"] = UserInfoTool(bot=bot)
        self.tools["get_group_members"] = GroupMemberTool(bot=bot)
    
    def _register_tools(self):
        """注册工具"""
        from tools.calculator_tool import CalculatorTool
        from tools.weather_tool import WeatherTool
        from tools.datetime_tool import DateTimeTool
        from tools.search_tool import SearchTool
        from tools.user_info_tool import UserInfoTool, GroupMemberTool
        
        self.tools = {
            "calculator": CalculatorTool(),
            "get_weather": WeatherTool(),
            "get_datetime": DateTimeTool(),
            "web_search": SearchTool(),
            "get_user_info": UserInfoTool(bot=self.bot),
            "get_group_members": GroupMemberTool(bot=self.bot)
        }
        
        if self.verbose:
            logger.info(f"[LangChain Agent] 已注册工具：{list(self.tools.keys())}")
    
    async def chat(self, user_message: str, chat_history: List = None, user_id: str = None, group_id: str = None) -> str:
        """
        处理用户消息
        
        Args:
            user_message: 用户消息
            chat_history: 聊天历史（暂未使用）
            user_id: 当前用户的QQ号
            group_id: 当前群号（如果是群聊）
            
        Returns:
            AI回复
        """
        if not self.deepseek_client.is_available():
            return "AI Agent 未初始化，请检查 API Key 配置。"
        
        try:
            if self.verbose:
                logger.info(f"[LangChain Agent] 处理消息: {user_message} (用户:{user_id}, 群:{group_id})")
            
            # 🎯 Step 1: 使用关键词树进行快速工具匹配
            tool_match = self.tool_matcher.get_best_match(user_message, threshold=0.3)
            
            if tool_match:
                logger.info(
                    f"[LangChain Agent] 🎯 关键词匹配到工具: {tool_match.tool_name} "
                    f"(置信度: {tool_match.confidence:.2%})"
                )
                
                # 根据工具类型执行相应的调用
                tool_result = await self._execute_matched_tool(
                    tool_match, user_message, user_id, group_id
                )
                
                if tool_result:
                    # 工具调用成功，让AI基于结果生成自然语言回复
                    return await self._generate_response_from_tool_result(
                        user_message, tool_match.tool_name, tool_result
                    )
            
            # 🧠 Step 2: 如果没有匹配到工具，让 AI 判断用户意图并决定是否使用工具
            
            # 构建上下文信息
            context_info = []
            if user_id:
                context_info.append(f"当前用户QQ号: {user_id}")
            if group_id:
                context_info.append(f"当前群号: {group_id}")
            
            # 构建完整的用户消息（包含上下文）
            full_user_message = user_message
            if context_info:
                context_str = " | ".join(context_info)
                full_user_message = f"[上下文: {context_str}]\n用户消息: {user_message}"
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": full_user_message}
            ]
            
            ai_response = await self.deepseek_client.chat(messages, max_tokens=500)
            
            if not ai_response:
                return "抱歉，AI暂时无法回复。"
            
            # 详细日志：显示 AI 原始回复
            logger.info(f"[LangChain Agent] AI 原始回复: {ai_response}")
            
            # 🛡️ 安全检测1：防止AI编造时间信息
            time_keywords = ["几点", "时间", "星期", "几号", "日期"]
            needs_time_info = any(kw in user_message for kw in time_keywords)
            
            if needs_time_info and "[TOOL:" not in ai_response:
                logger.warning(f"[LangChain Agent] ⚠️ 检测到时间查询但AI未调用工具，强制调用")
                
                # 判断查询类型
                if "星期" in user_message:
                    query_type = "weekday"
                elif "几号" in user_message or "日期" in user_message:
                    query_type = "date"
                else:
                    query_type = "now"
                
                tool = self.tools["get_datetime"]
                tool_result = await tool.execute(query_type=query_type)
                
                messages.append({"role": "assistant", "content": ai_response})
                messages.append({
                    "role": "user",
                    "content": f"⚠️ 你不知道当前时间！真实时间是：{tool_result}\n\n请根据真实时间重新回答。"
                })
                
                final_response = await self.deepseek_client.chat(messages, max_tokens=200)
                return final_response or tool_result
            
            # 🛡️ 安全检测2：防止AI编造实时数据
            realtime_keywords = [
                "价格", "指数", "汇率", "股票", "行情", "多少钱", "值多少",
                "最新", "新闻", "头条", "热点", "热搜", "今日", "今天发生"
            ]
            needs_realtime_data = any(kw in user_message for kw in realtime_keywords)
            
            if needs_realtime_data and "[TOOL:" not in ai_response:
                logger.warning(f"[LangChain Agent] ⚠️ 检测到AI可能在编造实时数据，强制触发搜索")
                
                tool = self.tools["web_search"]
                tool_result = await tool.execute(query=user_message, max_results=3)
                
                messages.append({"role": "assistant", "content": ai_response})
                messages.append({
                    "role": "user", 
                    "content": f"⚠️ 警告：你刚才的回复可能包含不准确的信息。\n\n这是真实的搜索结果：\n{tool_result}\n\n请【只】根据搜索结果回答，不要编造数据。"
                })
                
                final_response = await self.deepseek_client.chat(messages, max_tokens=500)
                return final_response or tool_result
            
            # 检查是否需要调用工具
            if "[TOOL:" in ai_response and "[/TOOL]" in ai_response:
                # 解析工具调用
                tool_call = self._parse_tool_call(ai_response)
                
                if tool_call:
                    tool_name, tool_arg = tool_call
                    
                    if self.verbose:
                        logger.info(f"[LangChain Agent] 调用工具: {tool_name}, 参数: {tool_arg}")
                    
                    # 执行工具
                    if tool_name in self.tools:
                        tool = self.tools[tool_name]
                        
                        try:
                            if tool_name == "calculator":
                                tool_result = await tool.execute(expression=tool_arg)
                            elif tool_name == "get_weather":
                                tool_result = await tool.execute(city=tool_arg)
                            elif tool_name == "get_datetime":
                                # 时间工具，参数可以是查询类型
                                tool_result = await tool.execute(query_type=tool_arg if tool_arg else "now")
                            elif tool_name == "web_search":
                                # 网络搜索工具
                                tool_result = await tool.execute(query=tool_arg, max_results=3)
                            elif tool_name == "get_user_info":
                                # 用户信息工具，格式：self 或 user:123456 或 group:789
                                if ":" in tool_arg:
                                    query_type, target_id = tool_arg.split(":", 1)
                                    tool_result = await tool.execute(query_type=query_type, target_id=target_id)
                                else:
                                    tool_result = await tool.execute(query_type=tool_arg)
                            elif tool_name == "get_group_members":
                                # 群成员列表工具
                                tool_result = await tool.execute(group_id=tool_arg)
                            else:
                                tool_result = "未知工具"
                            
                            if self.verbose:
                                logger.info(f"[LangChain Agent] 工具 {tool_name} 执行成功")
                            
                            # 第二次调用：让 AI 根据工具结果生成最终回复
                            messages.append({"role": "assistant", "content": ai_response})
                            messages.append({"role": "user", "content": f"工具执行结果：{tool_result}\n\n请根据这个结果自然地回答用户的问题。"})
                            
                            final_response = await self.deepseek_client.chat(messages, max_tokens=500)
                            return final_response or tool_result
                            
                        except Exception as e:
                            logger.error(f"[LangChain Agent] 工具执行失败: {e}")
                            return f"工具执行失败：{str(e)}"
                    else:
                        return f"未找到工具: {tool_name}"
            
            # 如果没有工具调用，直接返回 AI 回复
            return ai_response
            
        except Exception as e:
            logger.error(f"[LangChain Agent] 处理消息异常: {e}", exc_info=True)
            return "抱歉，AI在处理你的请求时遇到了问题。"
    
    def _parse_tool_call(self, response: str) -> Optional[tuple]:
        """
        解析工具调用
        
        Returns:
            (tool_name, tool_arg) 或 None
        """
        try:
            import re
            match = re.search(r'\[TOOL:(\w+)\](.+?)\[/TOOL\]', response)
            if match:
                tool_name = match.group(1)
                tool_arg = match.group(2).strip()
                return (tool_name, tool_arg)
        except Exception as e:
            logger.error(f"[LangChain Agent] 解析工具调用失败: {e}")
        
        return None
    
    async def _execute_matched_tool(
        self, tool_match, user_message: str, user_id: str = None, group_id: str = None
    ) -> Optional[str]:
        """
        执行匹配到的工具
        
        Args:
            tool_match: ToolMatch 对象
            user_message: 用户消息
            user_id: 用户QQ号
            group_id: 群号
            
        Returns:
            工具执行结果（message），失败返回 None
        """
        tool_name = tool_match.tool_name
        tool = self.tools.get(tool_name)
        
        if not tool:
            logger.error(f"[LangChain Agent] 工具 {tool_name} 不存在")
            return None
        
        try:
            # 根据工具类型准备参数
            if tool_name == "get_datetime":
                # 判断查询类型
                if "星期" in user_message or "周" in user_message:
                    query_type = "weekday"
                elif "几号" in user_message or "日期" in user_message:
                    query_type = "date"
                else:
                    query_type = "now"
                result = await tool.execute(query_type=query_type)
            
            elif tool_name == "web_search":
                # 提取搜索关键词
                query = user_message
                # 移除常见的搜索动词
                for word in ["搜索", "查询", "查找", "查一下", "找一下", "帮我", "一下"]:
                    query = query.replace(word, "")
                query = query.strip()
                result = await tool.execute(query=query, max_results=3)
            
            elif tool_name == "get_user_info":
                # 判断查询类型
                if "我的" in user_message or "我是" in user_message:
                    # 查询用户自己的信息
                    if user_id:
                        result = await tool.execute(query_type="user", target_id=user_id)
                    else:
                        result = await tool.execute(query_type="self")
                elif "群" in user_message:
                    # 查询群信息
                    if group_id:
                        result = await tool.execute(query_type="group", target_id=group_id)
                    else:
                        return "当前不在群聊中，无法查询群信息。"
                else:
                    result = await tool.execute(query_type="self")
            
            elif tool_name == "get_group_members":
                # 查询群成员列表
                if group_id:
                    result = await tool.execute(group_id=group_id)
                else:
                    return "当前不在群聊中，无法查询群成员。"
            
            elif tool_name == "calculator":
                # 直接传递用户消息作为表达式
                result = await tool.execute(expression=user_message)
            
            elif tool_name == "get_weather":
                # 提取城市名
                import re
                city_match = re.search(r'[\u4e00-\u9fa5]+(?=天气|气温|温度)', user_message)
                if city_match:
                    city = city_match.group()
                else:
                    city = "北京"  # 默认城市
                result = await tool.execute(city=city)
            
            else:
                logger.warning(f"[LangChain Agent] 未知工具类型: {tool_name}")
                return None
            
            # 兼容处理：result 可能是 ToolResult 对象或直接是字符串
            if result:
                if isinstance(result, str):
                    # 直接返回字符串结果
                    logger.info(f"[LangChain Agent] ✅ 工具 {tool_name} 执行成功（返回字符串）")
                    return result
                elif hasattr(result, 'success'):
                    # ToolResult 对象
                    if result.success:
                        logger.info(f"[LangChain Agent] ✅ 工具 {tool_name} 执行成功")
                        return result.message
                    else:
                        logger.error(f"[LangChain Agent] ❌ 工具 {tool_name} 执行失败: {result.error}")
                        return None
                else:
                    logger.warning(f"[LangChain Agent] 工具返回了未知类型: {type(result)}")
                    return str(result)
            else:
                logger.error(f"[LangChain Agent] ❌ 工具 {tool_name} 返回 None")
                return None
                
        except Exception as e:
            logger.error(f"[LangChain Agent] 工具 {tool_name} 执行异常: {e}", exc_info=True)
            return None
    
    async def _generate_response_from_tool_result(
        self, user_message: str, tool_name: str, tool_result: str
    ) -> str:
        """
        基于工具执行结果生成自然语言回复
        
        Args:
            user_message: 用户原始消息
            tool_name: 工具名称
            tool_result: 工具执行结果
            
        Returns:
            AI生成的自然语言回复
        """
        try:
            messages = [
                {"role": "system", "content": "你是一个友好的AI助手。根据提供的工具结果，自然地回答用户的问题。不要提及'工具'或'系统'等技术术语。"},
                {"role": "user", "content": f"用户问题：{user_message}\n\n查询结果：{tool_result}\n\n请自然地回答用户的问题。"}
            ]
            
            response = await self.deepseek_client.chat(messages, max_tokens=300)
            
            if response:
                return response
            else:
                # 如果AI生成失败，直接返回工具结果
                return tool_result
                
        except Exception as e:
            logger.error(f"[LangChain Agent] 生成回复失败: {e}")
            return tool_result
    
    def is_available(self) -> bool:
        """检查 Agent 是否可用"""
        return self.deepseek_client.is_available()


# 全局单例
_agent: Optional[SimpleLangChainAgent] = None

def get_langchain_agent(system_prompt: str = None) -> SimpleLangChainAgent:
    """获取 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = SimpleLangChainAgent(system_prompt=system_prompt)
    return _agent
