"""
意图识别服务 - Intent Recognizer Service
使用AI分析用户意图
"""

from typing import Dict, Any, Optional
import json
import re
import httpx
import asyncio
from nonebot.log import logger

from services.dispatcher.dispatcher_config import DispatcherConfig
from services.dispatcher.function_registry import get_function_registry


class IntentRecognizer:
    """
    意图识别引擎 - 核心AI组件
    使用DeepSeek分析用户意图
    """
    
    def __init__(self):
        self.function_registry = get_function_registry()
    
    async def analyze_intent(self, user_message: str, user_id: str) -> Dict[str, Any]:
        """
        分析用户意图
        
        Args:
            user_message: 用户消息
            user_id: 用户ID
        
        Returns:
            {
                "intent_type": "chat|function_call",
                "function_name": "功能名称（如果是function_call）",
                "confidence": 0.0-1.0,
                "reasoning": "推理过程",
                "response": "AI的回复或空"
            }
        """
        # 获取功能列表
        functions_desc = self.function_registry.get_all_functions_desc()
        function_names = self.function_registry.get_function_names()
        
        # 构建意图分析提示词
        system_prompt = f"""你是一个智能助手的意图识别系统。

你的任务是分析用户的消息，判断用户是想：
1. 普通聊天 (intent_type: "chat")
2. 调用特定功能 (intent_type: "function_call")

{functions_desc}

⚠️ 重要：如果判断为function_call，function_name字段必须从以下列表中选择：
{json.dumps(function_names, ensure_ascii=False)}

请分析用户意图并以JSON格式回复：
{{
    "intent_type": "chat" 或 "function_call",
    "function_name": "功能名称（必须从上面列表中选择，chat时为空字符串）",
    "confidence": 0.0-1.0,
    "reasoning": "简短的推理说明"
}}

判断原则：
- 如果用户明确要求某个功能（查询、统计、清理、点赞、角色扮演等），选择function_call
- function_name必须严格从上面的功能列表中选择，不能自己创造
- "给我点赞"、"点赞"、"赞我"等明确表达必须识别为like功能调用
- 如果用户只是打招呼、闲聊、询问一般问题，选择chat
- 不确定时优先选择chat，给用户更自然的体验
- confidence低于0.6时，选择chat

注意：不要生成response字段，聊天回复将由专门的聊天系统处理。
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 英伟达API请求格式
                response = await client.post(
                    DispatcherConfig.API_URL,
                    headers={
                        "Authorization": f"Bearer {DispatcherConfig.API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": messages,
                        "temperature": 0.3,  # 降低温度，更准确
                        "max_tokens": 500,
                        # 英伟达API通常不需要单独指定model参数，已在URL中包含
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 处理英伟达API响应格式
                    if "choices" in result and result["choices"] and "message" in result["choices"][0]:
                        ai_reply = result["choices"][0]["message"]["content"]
                    else:
                        # 英伟达API可能使用不同的响应结构
                        ai_reply = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # 提取JSON
                    intent_data = self._extract_json(ai_reply)
                    
                    if DispatcherConfig.ENABLE_INTENT_LOG:
                        logger.info(f"🎯 意图识别: {intent_data}")
                    
                    return intent_data
                else:
                    logger.error(f"意图识别失败: {response.status_code}, 响应内容: {response.text}")
                    return self._default_intent(user_message)
                    
        except Exception as e:
            logger.exception(f"意图识别异常: {e}")
            logger.error(f"异常类型: {type(e).__name__}, 详细信息: {str(e)}")
            # 增加重试逻辑
            try:
                await asyncio.sleep(2)  # 等待2秒后重试
                logger.info("🔄 尝试重新连接英伟达API...")
                async with httpx.AsyncClient(timeout=20.0) as retry_client:
                    response = await retry_client.post(
                        DispatcherConfig.API_URL,
                        headers={
                            "Authorization": f"Bearer {DispatcherConfig.API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "messages": messages,
                            "temperature": 0.3,
                            "max_tokens": 500
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        # 兼容处理
                        if "choices" in result and result["choices"] and "message" in result["choices"][0]:
                            ai_reply = result["choices"][0]["message"]["content"]
                        else:
                            ai_reply = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        intent_data = self._extract_json(ai_reply)
                        if DispatcherConfig.ENABLE_INTENT_LOG:
                            logger.info(f"🎯 重试成功 - 意图识别: {intent_data}")
                        return intent_data
            except Exception as retry_e:
                logger.error(f"重试失败: {retry_e}")
                return self._default_intent(user_message)
            return self._default_intent(user_message)
    
    def _extract_json(self, text: str) -> Dict:
        """从AI回复中提取JSON"""
        try:
            # 尝试找到JSON代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 尝试直接解析
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # 解析失败，返回默认
            return {
                "intent_type": "chat",
                "function_name": "",
                "confidence": 0.5,
                "reasoning": "无法解析AI回复"
            }
        except:
            return {
                "intent_type": "chat",
                "function_name": "",
                "confidence": 0.5,
                "reasoning": "JSON解析失败"
            }
    
    def _default_intent(self, message: str) -> Dict:
        """返回默认意图（聊天）"""
        return {
            "intent_type": "chat",
            "function_name": "",
            "confidence": 0.5,
            "reasoning": "API调用失败，默认为聊天"
        }


# ==================== 全局单例 ====================
_intent_recognizer: Optional[IntentRecognizer] = None

def get_intent_recognizer() -> IntentRecognizer:
    """获取意图识别器单例"""
    global _intent_recognizer
    if _intent_recognizer is None:
        _intent_recognizer = IntentRecognizer()
    return _intent_recognizer

