"""
DeepSeek 客户端 - Utils Layer
职责：封装 DeepSeek Chat API
代码量：~200 行（纯工具，无业务逻辑）
"""
from typing import List, Dict, Optional
from nonebot.log import logger
import httpx
import asyncio
import os


class DeepSeekClient:
    """DeepSeek AI 聊天客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "ai-deepseek-r1-0528",
        base_url: str = "https://api.nvcf.nvidia.com"
    ):
        """
        初始化客户端
        
        Args:
            api_key: API密钥
            model: 模型名称
            base_url: API基础URL
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url
        
        # 检测是否为NVIDIA API
        if "nvcf.nvidia.com" in base_url:
            # NVIDIA Cloud Functions格式 - 这个URL会通过get_deepseek_client重新设置
            self.api_url = f"{base_url}/v2/nvcf/pexec/functions/853b883c-b3ae-41bc-aa2d-b147389f6490"
            self.is_nvidia_api = True
        else:
            # 标准OpenAI格式
            self.api_url = f"{base_url}/v1/chat/completions"
            self.is_nvidia_api = False
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: int = 2000,
        timeout: float = 30.0,
        retry_count: int = 0,
        max_retries: int = 2,
        enable_reasoning: bool = False
    ) -> Optional[str]:
        """
        发送聊天请求（带智能重试）
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            enable_reasoning: 是否启用推理思考（默认False，禁用以提高速度）
        
        Returns:
            AI回复文本，失败返回 None
        """
        if not self.api_key:
            logger.error("DeepSeek API Key 未配置")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 根据API类型构建请求体
            if self.is_nvidia_api:
                # NVIDIA Cloud Functions格式 - 不需要model字段
                payload = {
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "reasoning": enable_reasoning  # 禁用推理思考以提高速度
                }
                # NVIDIA API需要更长的超时时间
                timeout = max(timeout, 60.0)
            else:
                # 标准OpenAI格式
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "reasoning": enable_reasoning  # 禁用推理思考以提高速度
                }
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    message = data["choices"][0]["message"]
                    
                    # 处理NVIDIA API的特殊响应格式
                    if self.is_nvidia_api:
                        # NVIDIA API可能使用reasoning_content或content
                        content = message.get("content") or message.get("reasoning_content", "")
                    else:
                        content = message["content"]
                    
                    return content if content else None
                elif response.status_code == 429 and retry_count < max_retries:
                    # 速率限制，等待后重试
                    await asyncio.sleep((retry_count + 1) * 2)
                    return await self.chat(
                        messages, temperature, max_tokens, timeout, 
                        retry_count + 1, max_retries, enable_reasoning
                    )
                else:
                    logger.error(f"DeepSeek API 错误: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"DeepSeek API 调用异常: {e}")
            if retry_count < max_retries:
                await asyncio.sleep((retry_count + 1) * 2)
                return await self.chat(
                    messages, temperature, max_tokens, timeout,
                    retry_count + 1, max_retries, enable_reasoning
                )
            return None
    
    async def chat_simple(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        enable_reasoning: bool = False
    ) -> Optional[str]:
        """
        简化的聊天接口
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            enable_reasoning: 是否启用推理思考（默认False，禁用以提高速度）
        
        Returns:
            AI回复
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_message})
        
        return await self.chat(messages, enable_reasoning=enable_reasoning)
    
    async def create_summary(self, conversation_messages: List[Dict[str, str]], enable_reasoning: bool = False) -> Optional[str]:
        """
        创建对话摘要
        
        Args:
            conversation_messages: 对话消息列表
            enable_reasoning: 是否启用推理思考（默认False，禁用以提高速度）
        
        Returns:
            摘要文本
        """
        if not conversation_messages:
            return ""
        
        # 构建摘要请求
        conversation_text = "\n".join([
            f"{'用户' if m['role'] == 'user' else 'AI'}: {m['content']}"
            for m in conversation_messages
        ])
        
        summary_messages = [
            {
                "role": "system",
                "content": "请将以下对话总结成简洁的摘要，提取关键信息和重要内容。"
            },
            {
                "role": "user",
                "content": f"请总结这段对话:\n\n{conversation_text}"
            }
        ]
        
        summary = await self.chat(summary_messages, enable_reasoning=enable_reasoning)
        return summary or "对话摘要生成失败"
    
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return bool(self.api_key)


# 全局单例
_deepseek_client: Optional[DeepSeekClient] = None

def get_deepseek_client() -> DeepSeekClient:
    """获取全局DeepSeek客户端实例"""
    global _deepseek_client
    if _deepseek_client is None:
        # 从配置文件读取API Key
        try:
            from services.chat.chat_config import ChatConfig
            
            # 从完整的API_URL提取base_url
            if "nvcf.nvidia.com" in ChatConfig.API_URL:
                base_url = "https://api.nvcf.nvidia.com"
            else:
                # 标准格式，提取base_url
                import urllib.parse
                parsed = urllib.parse.urlparse(ChatConfig.API_URL)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            _deepseek_client = DeepSeekClient(
                api_key=ChatConfig.API_KEY,
                model=ChatConfig.MODEL,
                base_url=base_url
            )
            # 如果是NVIDIA API，使用配置文件中的完整API URL
            if "nvcf.nvidia.com" in ChatConfig.API_URL:
                _deepseek_client.api_url = ChatConfig.API_URL
        except ImportError:
            # 如果配置文件不存在，使用环境变量
            _deepseek_client = DeepSeekClient()
    return _deepseek_client
