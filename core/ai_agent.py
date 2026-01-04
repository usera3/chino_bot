"""
AI Agent - 智能代理
核心逻辑：AI决定是否需要调用工具，以及如何使用工具结果
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Optional
from nonebot.log import logger
import json

from utils.deepseek_client import get_deepseek_client
from .tool_manager import tool_manager


class AIAgent:
    """AI智能代理"""
    
    def __init__(self, system_prompt: Optional[str] = None):
        """初始化
        
        Args:
            system_prompt: 系统提示词
        """
        self.client = get_deepseek_client()
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.conversation_history: List[Dict[str, Any]] = []
        logger.info("[AI Agent] 初始化完成")
    
    def _get_default_system_prompt(self) -> str:
        """默认系统提示词"""
        return """你是一个智能助手，可以使用各种工具来帮助用户。

你的特点：
1. 友好、专业、高效
2. 善于理解用户意图
3. 会主动使用工具解决问题
4. 给出简洁清晰的回复

当用户需要某些功能时，你应该：
1. 分析用户需求
2. 选择合适的工具
3. 使用工具获取结果
4. 将结果以友好的方式呈现给用户

记住：你的目标是帮助用户，而不是炫耀技术。"""
    
    async def chat(
        self,
        user_message: str,
        enable_tools: bool = True,
        max_tool_calls: int = 5
    ) -> str:
        """处理用户消息
        
        Args:
            user_message: 用户消息
            enable_tools: 是否启用工具调用
            max_tool_calls: 最大工具调用次数（防止死循环）
            
        Returns:
            AI回复
        """
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        tool_call_count = 0
        
        while tool_call_count < max_tool_calls:
            # 构建消息列表
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history)
            
            # 准备工具定义
            tools = None
            if enable_tools:
                tools = tool_manager.get_all_definitions()
                if not tools:
                    logger.warning("[AI Agent] 没有可用的工具")
                    enable_tools = False
            
            # 调用 AI
            try:
                response_data = await self._call_ai_with_tools(messages, tools)
                
                if not response_data:
                    return "抱歉，我现在遇到了一些问题..."
                
                # 检查是否需要调用工具
                tool_calls = self._extract_tool_calls(response_data)
                
                if not tool_calls:
                    # 没有工具调用，直接返回回复
                    assistant_message = self._extract_content(response_data)
                    if assistant_message:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": assistant_message
                        })
                    return assistant_message or "..."
                
                # 有工具调用，执行工具
                logger.info(f"[AI Agent] 需要调用 {len(tool_calls)} 个工具")
                tool_call_count += 1
                
                # 记录 AI 的工具调用请求
                self.conversation_history.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
                
                # 执行所有工具
                for tool_call in tool_calls:
                    tool_name = tool_call.get("function", {}).get("name")
                    tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
                    
                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    logger.info(f"[AI Agent] 调用工具: {tool_name}, 参数: {tool_args}")
                    
                    # 执行工具
                    result = await tool_manager.execute_tool(tool_name, **tool_args)
                    
                    # 将工具结果添加到对话历史
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "name": tool_name,
                        "content": result.message
                    })
                
                # 继续循环，让 AI 根据工具结果生成最终回复
                continue
                
            except Exception as e:
                logger.error(f"[AI Agent] 处理消息异常: {e}", exc_info=True)
                return f"抱歉，处理你的请求时出错了：{str(e)}"
        
        # 达到最大工具调用次数
        logger.warning(f"[AI Agent] 达到最大工具调用次数: {max_tool_calls}")
        return "抱歉，处理你的请求时工具调用次数过多，请简化你的问题。"
    
    async def _call_ai_with_tools(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """调用 AI（支持工具）
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            
        Returns:
            AI 响应数据
        """
        # 注意：这里需要根据实际 API 支持情况调整
        # DeepSeek R1 可能不支持 Function Calling
        # 如果不支持，需要用 prompt engineering 模拟
        
        if tools:
            logger.warning("[AI Agent] 当前 API 可能不支持 Function Calling，将使用普通模式")
        
        # 简化版本：直接调用 AI（不使用 Function Calling）
        # 未来可以升级为支持 Function Calling 的版本
        response = await self.client.chat(messages)
        
        if response:
            return {"content": response}
        return None
    
    def _extract_tool_calls(self, response_data: Dict) -> List[Dict]:
        """从响应中提取工具调用
        
        Args:
            response_data: AI 响应数据
            
        Returns:
            工具调用列表
        """
        # 如果 API 支持 Function Calling，在这里解析
        # 当前版本返回空列表（不使用工具）
        return []
    
    def _extract_content(self, response_data: Dict) -> str:
        """从响应中提取文本内容
        
        Args:
            response_data: AI 响应数据
            
        Returns:
            文本内容
        """
        return response_data.get("content", "")
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        logger.info("[AI Agent] 已清空对话历史")
    
    def get_history_length(self) -> int:
        """获取历史消息数量"""
        return len(self.conversation_history)




