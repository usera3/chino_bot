"""
图像识别工具 - 基于通义千问 VL
"""
import os
import base64
import requests
from io import BytesIO
from langchain_core.tools import BaseTool
from pydantic import Field
import dashscope
from dashscope import MultiModalConversation


class ImageAnalysisTool(BaseTool):
    """图像分析工具 - 使用通义千问-VL"""
    
    name: str = "analyze_image"
    description: str = """分析图片内容并提供详细描述。

使用场景：
- 用户发送图片时自动调用
- 识别图片中的物体、场景、文字
- 理解图片的含义和情感

输入：图片URL或base64编码的图片
输出：图片的详细描述"""
    
    api_key: str = Field(default="")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if self.api_key:
            dashscope.api_key = self.api_key
    
    def _run(self, image_url: str, question: str = "请详细描述这张图片的内容") -> str:
        """
        分析图片
        
        Args:
            image_url: 图片URL或base64编码
            question: 对图片的提问
            
        Returns:
            图片分析结果
        """
        if not self.api_key:
            return "❌ 图像识别功能未配置（需要 DASHSCOPE_API_KEY）"
        
        try:
            # 构建消息
            messages = [{
                'role': 'user',
                'content': [
                    {'image': image_url},
                    {'text': question}
                ]
            }]
            
            # 调用 Qwen-VL API
            response = MultiModalConversation.call(
                model='qwen-vl-max',
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            if response.status_code == 200:
                result = response.output.choices[0].message.content[0]['text']
                return f"📸 图片分析结果：\n{result}"
            else:
                return f"❌ 图像识别失败: {response.code} - {response.message}"
                
        except Exception as e:
            return f"❌ 图像识别异常: {str(e)}"
    
    async def _arun(self, image_url: str, question: str = "请详细描述这张图片的内容") -> str:
        """异步版本"""
        return self._run(image_url, question)


def get_vision_tool():
    """获取图像识别工具"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    
    if not api_key:
        print("⚠️ DASHSCOPE_API_KEY 未配置，图像识别功能将不可用")
        return None
    
    try:
        tool = ImageAnalysisTool()
        return tool
    except Exception as e:
        print(f"⚠️ 图像识别工具初始化失败: {e}")
        return None
