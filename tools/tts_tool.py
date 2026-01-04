"""
语音合成工具 - 将文本转换为语音
支持 GPT-SoVITS 本地服务
"""
from core.tool_base import BaseTool, ToolResult
from nonebot.log import logger
from typing import Optional
import os
from pathlib import Path
import re


class TTSConfig:
    """TTS 配置"""
    # GPT-SoVITS 服务地址
    API_BASE_URL = "http://localhost:9872"
    
    # 是否启用TTS
    ENABLED = True
    
    # 去除括号内容（动作/表情描述不适合语音）
    REMOVE_BRACKETS = True


class TTSTool(BaseTool):
    """
    文本转语音工具
    """
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.model_loaded = False
        
    def get_name(self) -> str:
        return "text_to_speech"
    
    def get_description(self) -> str:
        return "将文本转换为语音消息。当用户明确要求语音回复、或者需要更亲切的语音交流时使用。注意：普通文字回复不需要使用此工具。"
    
    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要转换为语音的文本内容"
                }
            },
            "required": ["text"]
        }
    
    def _remove_brackets_content(self, text: str) -> str:
        """去除括号及其内容"""
        # 去除各种括号
        patterns = [
            r'\([^)]*\)',  # 英文圆括号
            r'（[^）]*）',  # 中文圆括号
            r'\[[^\]]*\]',  # 方括号
            r'【[^】]*】',  # 中文方括号
        ]
        
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result)
        
        return result.strip()
    
    async def _initialize_gpt_sovits(self):
        """初始化 GPT-SoVITS 服务"""
        if self.model_loaded:
            return True
        
        try:
            from gradio_client import Client, handle_file
            
            logger.info("🎤 初始化 GPT-SoVITS TTS 服务...")
            
            # 连接到服务
            self.client = Client(TTSConfig.API_BASE_URL)
            logger.info(f"✅ 已连接到 {TTSConfig.API_BASE_URL}")
            
            # 这里可以添加模型加载逻辑（如果需要）
            # 暂时标记为已加载
            self.model_loaded = True
            logger.success("🎤 GPT-SoVITS TTS 服务初始化成功！")
            return True
            
        except Exception as e:
            logger.error(f"❌ GPT-SoVITS TTS 服务初始化失败: {e}")
            logger.warning("💡 提示：请确保 GPT-SoVITS 服务已启动在 http://localhost:9872")
            return False
    
    async def execute(self, text: str, **kwargs) -> ToolResult:
        """
        执行文本转语音
        
        Args:
            text: 要转换的文本
        
        Returns:
            ToolResult（包含语音文件路径）
        """
        if not TTSConfig.ENABLED:
            return ToolResult(
                success=False,
                error="TTS 服务未启用",
                message="语音功能暂时不可用。"
            )
        
        logger.info(f"🎤 执行语音合成: {text[:50]}...")
        
        try:
            # 初始化服务
            if not await self._initialize_gpt_sovits():
                return ToolResult(
                    success=False,
                    error="TTS 服务初始化失败",
                    message="语音服务暂时不可用，请稍后再试。"
                )
            
            # 去除括号内容
            if TTSConfig.REMOVE_BRACKETS:
                processed_text = self._remove_brackets_content(text)
            else:
                processed_text = text
            
            # 如果处理后为空
            if not processed_text or len(processed_text.strip()) == 0:
                return ToolResult(
                    success=False,
                    error="处理后的文本为空",
                    message="文本中没有可以转换为语音的内容。"
                )
            
            # 调用 GPT-SoVITS API
            from gradio_client import handle_file
            
            # 使用旧机器人的配置
            REF_WAV_PATH = "/Users/mozi100/PycharmProjects/chino_bot/zhinai-bot/ref_wav/vymql-azgz6.wav"
            
            logger.info(f"🎤 正在合成语音: {processed_text[:50]}...")
            
            result_path = self.client.predict(
                ref_wav_path=handle_file(REF_WAV_PATH),
                prompt_text="",  # 参考音频的文本内容（可选）
                prompt_language="中文",
                text=processed_text,
                text_language="中文",
                how_to_cut="凑四句一切",
                top_k=15,
                top_p=1,
                temperature=1,
                ref_free=False,
                speed=1.0,
                if_freeze=False,
                inp_refs=None,
                sample_steps="8",
                if_sr=False,
                pause_second=0.3,
                api_name="/get_tts_wav"
            )
            
            if result_path and os.path.exists(result_path):
                return ToolResult(
                    success=True,
                    data={"voice_path": result_path, "text": processed_text},
                    message=f"✅ 语音合成成功：{processed_text[:30]}..."
                )
            else:
                # 如果没有配置完整的TTS服务，返回文本
                return ToolResult(
                    success=False,
                    error="语音生成失败",
                    message=f"抱歉，语音功能暂时不可用。文本内容：{processed_text}"
                )
        
        except ImportError:
            return ToolResult(
                success=False,
                error="gradio_client 未安装",
                message="语音功能需要安装 gradio_client 库。"
            )
        except Exception as e:
            logger.error(f"❌ 语音合成失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"语音合成失败：{str(e)}"
            )

