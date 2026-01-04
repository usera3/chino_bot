"""
图像生成工具 - 文本生成图片
支持通义万相（Tongyi Wanxiang）和其他图像生成服务
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_base import BaseTool, ToolResult
from typing import Dict, Any, Optional
from nonebot.log import logger
import httpx
import asyncio


class TongyiImageGenTool(BaseTool):
    """
    通义万相图像生成工具
    根据文本描述生成图片
    """
    
    def __init__(self):
        """初始化通义万相图像生成工具"""
        super().__init__()
        # 使用阿里云 DashScope API
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        
        if self.api_key:
            logger.success("✅ 通义万相图像生成工具初始化完成")
        else:
            logger.warning("⚠️ DASHSCOPE_API_KEY 未设置，图像生成功能不可用")
            logger.info("💡 获取API密钥: https://dashscope.aliyun.com")
    
    def get_name(self) -> str:
        return "generate_image"
    
    def get_description(self) -> str:
        return "根据文本描述生成图片。用户说'画一个XXX'、'生成XXX图片'、'帮我画XXX'等时使用。支持各种风格：二次元、写实、水墨画、油画等"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "图片描述（中文或英文），越详细越好。例如：'一只可爱的橘猫在花园里玩耍，阳光明媚，二次元风格'"
                },
                "style": {
                    "type": "string",
                    "description": "画风（可选）：'anime'(二次元)、'realistic'(写实)、'watercolor'(水彩)、'ink'(水墨)、'oil'(油画)",
                    "enum": ["anime", "realistic", "watercolor", "ink", "oil", "auto"],
                    "default": "auto"
                },
                "size": {
                    "type": "string",
                    "description": "图片尺寸：'512x512'、'768x768'、'1024x1024'",
                    "enum": ["512x512", "768x768", "1024x1024"],
                    "default": "1024x1024"
                }
            },
            "required": ["prompt"]
        }
    
    async def execute(
        self, 
        prompt: str,
        style: str = "auto",
        size: str = "1024x1024"
    ) -> ToolResult:
        """
        执行图像生成
        
        Args:
            prompt: 图片描述
            style: 画风
            size: 图片尺寸
        
        Returns:
            ToolResult: 生成结果（包含图片URL）
        """
        if not self.is_available():
            return ToolResult(
                success=False,
                message="图像生成功能不可用（API密钥未配置）",
                error="API_NOT_CONFIGURED"
            )
        
        try:
            logger.info(f"🎨 开始生成图片: {prompt[:50]}...")
            logger.info(f"🎨 风格: {style}, 尺寸: {size}")
            
            # 构建请求参数
            # 通义万相使用 wanx-v1 模型
            payload = {
                "model": "wanx-v1",
                "input": {
                    "prompt": prompt
                },
                "parameters": {
                    "size": size,
                    "n": 1  # 生成1张图
                }
            }
            
            # 如果指定了风格，添加到prompt中
            if style != "auto":
                style_map = {
                    "anime": "二次元风格，动漫插画",
                    "realistic": "写实风格，超高清摄影",
                    "watercolor": "水彩画风格，柔和色彩",
                    "ink": "中国水墨画风格，意境优美",
                    "oil": "油画风格，质感厚重"
                }
                style_suffix = style_map.get(style, "")
                if style_suffix:
                    payload["input"]["prompt"] = f"{prompt}, {style_suffix}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable"  # 启用异步模式
            }
            
            # 发送生成请求
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 通义万相使用异步模式，需要轮询结果
                    task_id = data.get("output", {}).get("task_id")
                    
                    if task_id:
                        logger.info(f"🎨 图像生成任务已提交，任务ID: {task_id}")
                        
                        # 轮询任务状态
                        image_url = await self._poll_task_status(task_id)
                        
                        if image_url:
                            logger.success(f"✅ 图片生成成功: {image_url}")
                            
                            return ToolResult(
                                success=True,
                                data={
                                    "image_url": image_url,
                                    "prompt": prompt,
                                    "style": style,
                                    "size": size
                                },
                                message=f"🎨 图片已生成！\n描述：{prompt}\n[图片URL: {image_url}]"
                            )
                        else:
                            logger.error("❌ 图片生成超时或失败")
                            return ToolResult(
                                success=False,
                                message="图片生成超时，请稍后重试",
                                error="GENERATION_TIMEOUT"
                            )
                    else:
                        # 同步模式直接返回结果
                        output = data.get("output", {})
                        results = output.get("results", [])
                        
                        if results and len(results) > 0:
                            image_url = results[0].get("url", "")
                            
                            if image_url:
                                logger.success(f"✅ 图片生成成功: {image_url}")
                                
                                return ToolResult(
                                    success=True,
                                    data={
                                        "image_url": image_url,
                                        "prompt": prompt,
                                        "style": style,
                                        "size": size
                                    },
                                    message=f"🎨 图片已生成！\n描述：{prompt}\n[图片URL: {image_url}]"
                                )
                        
                        logger.error(f"❌ API响应格式异常: {data}")
                        return ToolResult(
                            success=False,
                            message="图片生成失败（响应异常）",
                            error="INVALID_RESPONSE"
                        )
                
                elif response.status_code == 401:
                    logger.error("❌ 通义万相 API密钥无效")
                    return ToolResult(
                        success=False,
                        message="图片生成失败（API密钥无效）",
                        error="INVALID_API_KEY"
                    )
                
                elif response.status_code == 429:
                    logger.error("❌ 通义万相 API调用次数超限")
                    return ToolResult(
                        success=False,
                        message="图片生成失败（调用次数超限）",
                        error="RATE_LIMIT_EXCEEDED"
                    )
                
                else:
                    error_text = response.text
                    logger.error(f"❌ 通义万相 API错误: {response.status_code} - {error_text}")
                    return ToolResult(
                        success=False,
                        message="图片生成失败（服务异常）",
                        error=f"API_ERROR_{response.status_code}"
                    )
        
        except httpx.TimeoutException:
            logger.error("❌ 图片生成超时")
            return ToolResult(
                success=False,
                message="图片生成超时，请稍后重试",
                error="TIMEOUT"
            )
        
        except Exception as e:
            logger.error(f"❌ 图片生成失败: {e}")
            return ToolResult(
                success=False,
                message=f"图片生成失败：{str(e)}",
                error="GENERATION_ERROR"
            )
    
    async def _poll_task_status(self, task_id: str, max_wait: int = 60) -> Optional[str]:
        """
        轮询任务状态，获取生成的图片URL
        
        Args:
            task_id: 任务ID
            max_wait: 最大等待时间（秒）
        
        Returns:
            图片URL，失败返回None
        """
        query_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        start_time = asyncio.get_event_loop().time()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                try:
                    response = await client.get(query_url, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        output = data.get("output", {})
                        task_status = output.get("task_status", "")
                        
                        if task_status == "SUCCEEDED":
                            results = output.get("results", [])
                            if results and len(results) > 0:
                                return results[0].get("url", "")
                        
                        elif task_status == "FAILED":
                            logger.error(f"❌ 任务失败: {output.get('message', '未知错误')}")
                            return None
                        
                        # 任务还在进行中，继续等待
                        logger.info(f"🎨 图片生成中... 状态: {task_status}")
                    
                    # 检查是否超时
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > max_wait:
                        logger.error("❌ 轮询超时")
                        return None
                    
                    # 等待2秒后再次查询
                    await asyncio.sleep(2)
                
                except Exception as e:
                    logger.error(f"❌ 轮询任务状态失败: {e}")
                    return None
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return bool(self.api_key)


# 导出工具实例
tongyi_image_gen_tool = TongyiImageGenTool()

