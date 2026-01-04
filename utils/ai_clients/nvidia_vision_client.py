"""
NVIDIA 视觉模型客户端 - Utils Layer  
职责：封装 NVIDIA 图像理解 API (替代千问VL)
代码量：~120 行（纯工具，无业务逻辑）
"""
from typing import Optional, Dict, List
from nonebot.log import logger
import httpx
import asyncio
import os


class NvidiaVisionClient:
    """通用视觉模型客户端 - 支持多种API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: str = "Gemini/gemini-2.5-flash",  # 默认使用Gemini 2.5 Flash
        model_name: str = "Gemini/gemini-2.5-flash",
        base_url: str = "https://gaozaiya.cloudns.org/"
    ):
        """
        初始化客户端
        
        Args:
            api_key: API密钥
            model_id: 模型ID
            model_name: 模型名称  
            base_url: API基础URL
        """
        self.api_key = api_key or os.getenv("VISION_API_KEY", "sk-6fW34zquoQ0Bk7ry65xcSU0INBFF8o91")
        self.model_id = model_id
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        
        # 根据不同的API构建URL
        if "gaozaiya.cloudns.org" in base_url:
            # Gemini API格式
            self.api_url = f"{self.base_url}/v1/chat/completions"
            self.api_type = "gemini"
        elif "nvcf.nvidia.com" in base_url:
            # NVIDIA API格式
            self.api_url = f"{base_url}/v2/nvcf/pexec/functions/{model_id}"
            self.api_type = "nvidia"
        else:
            # 标准OpenAI格式
            self.api_url = f"{self.base_url}/v1/chat/completions"
            self.api_type = "openai"
        
        logger.info(f"✅ 视觉模型初始化: {model_name} ({self.api_type})")
    
    async def understand_image(self, image_url: str, prompt: Optional[str] = None) -> Optional[str]:
        """
        理解图片内容 - 兼容千问VL接口
        
        Args:
            image_url: 图片 URL
            prompt: 提示词（可选）
        
        Returns:
            图片描述文本，失败返回 None
        """
        if not self.api_key:
            logger.error("❌ NVIDIA API Key 未配置")
            return None
        
        try:
            # 默认提示词（与千问VL保持一致）
            if not prompt:
                prompt = "请用1-2句话简单描述这张图片的内容，包括主要对象、场景和氛围。"
            
            logger.info("📡 调用NVIDIA视觉API...")
            
            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            # API 请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 根据API类型构建不同的请求体
            if self.api_type == "gemini":
                # Gemini API格式
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.3
                }
            elif self.api_type == "nvidia":
                # NVIDIA API格式
                payload = {
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.3,
                    "reasoning": False
                }
            else:
                # 标准OpenAI格式
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.3
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"📝 API原始响应: {data}")
                    
                    # 处理不同的API响应格式
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"📝 API返回内容: {content[:100]}...")
                        return content
                    elif "content" in data:
                        content = data["content"]
                        logger.info(f"📝 API返回内容: {content[:100]}...")
                        return content
                    else:
                        logger.error(f"❌ API响应格式异常: {data}")
                        return None
                else:
                    logger.error(f"❌ API错误: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ NVIDIA视觉模型调用异常: {e}")
            return None
    
    async def analyze_emoticon(self, image_url: str) -> Optional[Dict]:
        """
        专门分析表情包的接口
        
        Args:
            image_url: 表情包URL
            
        Returns:
            表情包分析结果字典
        """
        prompt = """分析这个表情包/图片，请用JSON格式回答：
{
  "description": "图片的简单描述",
  "emotion": "主要表达的情感(开心/难过/生气/惊讶/等)",
  "scene": "使用场景(聊天/道歉/庆祝/等)", 
  "tags": ["标签1", "标签2", "标签3"],
  "keywords": ["关键词1", "关键词2"]
}"""
        
        result = await self.understand_image(image_url, prompt)
        if result:
            try:
                # 尝试解析JSON
                import json
                # 清理可能的markdown格式
                json_text = result.strip()
                if json_text.startswith('```json'):
                    json_text = json_text.replace('```json', '').replace('```', '').strip()
                return json.loads(json_text)
            except Exception as e:
                logger.warning(f"解析表情包分析结果失败: {e}")
                # 如果不是JSON格式，返回基础描述
                return {
                    "description": result[:100],  # 截取前100字符
                    "emotion": "neutral",
                    "scene": "general", 
                    "tags": ["表情包"],
                    "keywords": ["表情"]
                }
        return None
    
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return bool(self.api_key)


# ==================== 全局实例 ====================

# 支持的视觉模型配置
VISION_MODELS = {
    "gemini-2.5-flash": {
        "name": "Gemini/gemini-2.5-flash",
        "base_url": "https://gaozaiya.cloudns.org/",
        "description": "Google Gemini 2.5 Flash视觉模型，速度快，质量高"
    },
    "llama-3.2-11b": {
        "id": "9fa6fd04-ba2c-4bb3-90b7-ede407a9290f", 
        "name": "ai-llama-3_2-11b-vision-instruct",
        "base_url": "https://api.nvcf.nvidia.com",
        "description": "NVIDIA Llama-3.2-11B视觉模型"
    },
    "nemotron-nano": {
        "id": "5756401f-7f6e-4a22-bb63-2afc1e1ced06",
        "name": "ai-llama-3_1-nemotron-nano-vl-8b-v1",
        "base_url": "https://api.nvcf.nvidia.com", 
        "description": "NVIDIA Nemotron Nano最快速度"
    }
}

# 全局单例（默认使用Llama-3.2-11B）
_nvidia_client: Optional[NvidiaVisionClient] = None

def get_nvidia_vision_client(model: str = None) -> NvidiaVisionClient:
    """获取NVIDIA视觉客户端实例"""
    global _nvidia_client
    if _nvidia_client is None:
        # 从配置文件读取模型配置
        try:
            from services.emoticon.emoticon_config import EmoticonConfig
            model_name = model or EmoticonConfig.VISION_MODEL
            api_key = EmoticonConfig.VISION_API_KEY
            base_url = EmoticonConfig.VISION_BASE_URL
        except ImportError:
            model_name = model or "llama-3.2-11b"
            api_key = "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"
            base_url = "https://api.nvcf.nvidia.com"
        
        # 获取NVIDIA模型配置
        model_config = VISION_MODELS.get(model_name, VISION_MODELS["llama-3.2-11b"])
        
        _nvidia_client = NvidiaVisionClient(
            api_key=api_key,
            model_id=model_config["id"],
            model_name=model_config["name"],
            base_url=base_url
        )
        logger.info(f"🔄 使用NVIDIA视觉模型: {model_config['name']} (质量更好)")
    return _nvidia_client


# ==================== 兼容性接口 ====================

def get_vision_client() -> NvidiaVisionClient:
    """获取视觉客户端（兼容旧的千问VL调用）"""
    return get_nvidia_vision_client()
