"""
DeepSeek 客户端 - 英伟达API版本
"""
from typing import List, Dict, Optional
from nonebot.log import logger
import httpx
import asyncio
import os

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv 未安装，将只使用系统环境变量")


class DeepSeekClient:
    """DeepSeek AI 聊天客户端（英伟达API）"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "meta/llama-3.3-70b-instruct",
    ):
        """
        初始化客户端
        
        Args:
            api_key: API密钥
            model: 模型名称（默认使用 Llama 3.3 70B - 快速响应，配合关键词匹配系统）
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        # 英伟达 API 统一地址
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,  # 保持创造性（平衡点）
        max_tokens: int = 150,  # 降低最大token，避免过长（原2000 → 150）
        timeout: float = 15.0,
        retry_count: int = 0,
        max_retries: int = 1,
        presence_penalty: float = 0.6,  # 适度鼓励新词汇（平衡）
        frequency_penalty: float = 0.4,  # 适度减少重复（平衡）
        top_p: float = 0.95,  # 保持质量
    ) -> Optional[str]:
        """
        发送聊天请求（带智能重试）
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数（0-2，越高越随机）
            max_tokens: 最大token数
            timeout: 超时时间
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            presence_penalty: 存在惩罚（0-2，鼓励新词汇）
            frequency_penalty: 频率惩罚（0-2，减少重复）
            top_p: 核采样（0-1，控制输出多样性）
        
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
            
            # 英伟达 API 统一格式
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,  # 核采样
                "presence_penalty": presence_penalty,  # 鼓励新词汇
                "frequency_penalty": frequency_penalty,  # 减少重复
                "stream": False,  # 禁用流式响应，加快速度
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
                    content = message.get("content") or message.get("reasoning_content", "")
                    return content if content else None
                    
                elif response.status_code == 429 and retry_count < max_retries:
                    # 速率限制，等待后重试
                    await asyncio.sleep((retry_count + 1) * 2)
                    return await self.chat(
                        messages, temperature, max_tokens, timeout, 
                        retry_count + 1, max_retries,
                        presence_penalty, frequency_penalty, top_p
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
                    retry_count + 1, max_retries,
                    presence_penalty, frequency_penalty, top_p
                )
            return None
    
    async def chat_simple(
        self,
        user_message: str,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        简化的聊天接口
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
        
        Returns:
            AI回复
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_message})
        
        return await self.chat(messages)
    
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return bool(self.api_key)


# 全局单例
_deepseek_client: Optional[DeepSeekClient] = None

def get_deepseek_client() -> DeepSeekClient:
    """获取全局DeepSeek客户端实例"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client

