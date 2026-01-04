"""
GPT-SoVITS 语音合成服务
职责：封装 GPT-SoVITS API 调用，提供语音合成功能
"""
from gradio_client import Client, handle_file
from pathlib import Path
import tempfile
import shutil
import os
import re
from typing import Optional
import logging

# 使用标准 logging（兼容独立测试和 NoneBot 环境）
try:
    from nonebot.log import logger
except ImportError:
    logger = logging.getLogger(__name__)


class GPTSoVITSConfig:
    """GPT-SoVITS 配置"""
    API_BASE_URL = "http://localhost:9872"
    
    # 模型权重（使用 Chino 自定义模型）
    SOVITS_MODEL = "SoVITS_weights/chino_e8_s72.pth"
    GPT_MODEL = "GPT_weights/chino-e15.ckpt"
    
    # 参考音频
    REF_WAV_PATH = "/Users/mozi100/PycharmProjects/chino_bot/zhinai-bot/ref_wav/vymql-azgz6.wav"
    REF_TEXT = ""  # 参考音频的文本内容（可选）
    REF_LANGUAGE = "中文"
    
    # 合成参数
    TEXT_LANGUAGE = "中文"
    HOW_TO_CUT = "凑四句一切"
    TOP_K = 15
    TOP_P = 1
    TEMPERATURE = 1
    REF_FREE = False
    SPEED = 1.0
    IF_FREEZE = False
    SAMPLE_STEPS = "8"
    IF_SR = False
    PAUSE_SECOND = 0.3
    
    # 启用状态
    ENABLED = True


class GPTSoVITSService:
    """GPT-SoVITS TTS 服务"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.model_loaded = False
        self.enabled = GPTSoVITSConfig.ENABLED
        
    async def initialize(self):
        """初始化服务并加载模型"""
        if not self.enabled:
            logger.warning("🔇 GPT-SoVITS TTS 服务已禁用")
            return False
            
        try:
            logger.info("🎤 初始化 GPT-SoVITS TTS 服务...")
            
            # 连接到 GPT-SoVITS 服务
            self.client = Client(GPTSoVITSConfig.API_BASE_URL)
            logger.info(f"✅ 已连接到 {GPTSoVITSConfig.API_BASE_URL}")
            
            # 加载 SoVITS 模型
            logger.info(f"📦 加载 SoVITS 模型: {GPTSoVITSConfig.SOVITS_MODEL}")
            self.client.predict(
                sovits_path=GPTSoVITSConfig.SOVITS_MODEL,
                prompt_language=GPTSoVITSConfig.REF_LANGUAGE,
                text_language=GPTSoVITSConfig.TEXT_LANGUAGE,
                api_name="/change_sovits_weights"
            )
            
            # 加载 GPT 模型
            logger.info(f"📦 加载 GPT 模型: {GPTSoVITSConfig.GPT_MODEL}")
            self.client.predict(
                gpt_path=GPTSoVITSConfig.GPT_MODEL,
                api_name="/change_gpt_weights"
            )
            
            self.model_loaded = True
            if hasattr(logger, 'success'):
                logger.success("🎤 GPT-SoVITS TTS 服务初始化成功！")
            else:
                logger.info("🎤 GPT-SoVITS TTS 服务初始化成功！")
            return True
            
        except Exception as e:
            logger.error(f"❌ GPT-SoVITS TTS 服务初始化失败: {e}")
            self.enabled = False
            return False
    
    def remove_brackets_content(self, text: str) -> str:
        """
        去除文本中括号及其内容
        支持：() [] {} 《》 「」 【】 （）全角括号
        """
        # 匹配各种括号及其内容
        patterns = [
            r'\([^)]*\)',      # 半角圆括号 ()
            r'（[^）]*）',      # 全角圆括号 （）
            r'\[[^\]]*\]',     # 半角方括号 []
            r'【[^】]*】',      # 全角方括号 【】
            r'\{[^}]*\}',      # 花括号 {}
            r'《[^》]*》',      # 书名号 《》
            r'「[^」]*」',      # 日文引号 「」
        ]
        
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result)
        
        # 清理多余的空格
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    async def text_to_speech(self, text: str, remove_brackets: bool = True) -> Optional[str]:
        """
        将文本转换为语音
        
        Args:
            text: 要转换的文本
            remove_brackets: 是否去除括号内容
            
        Returns:
            生成的音频文件路径，失败返回 None
        """
        if not self.enabled or not self.model_loaded:
            logger.warning("🔇 TTS 服务未启用或模型未加载")
            return None
        
        try:
            # 处理文本：去除括号
            processed_text = self.remove_brackets_content(text) if remove_brackets else text
            
            # 如果去除括号后为空，直接跳过（括号内通常是动作/表情描述，不适合语音）
            if not processed_text or len(processed_text.strip()) == 0:
                logger.warning("⚠️ 处理后的文本为空，跳过语音合成")
                return None
            
            logger.info(f"🎤 正在合成语音: {processed_text[:50]}...")
            
            # 调用 GPT-SoVITS API
            result = self.client.predict(
                ref_wav_path=handle_file(GPTSoVITSConfig.REF_WAV_PATH),
                prompt_text=GPTSoVITSConfig.REF_TEXT,
                prompt_language=GPTSoVITSConfig.REF_LANGUAGE,
                text=processed_text,
                text_language=GPTSoVITSConfig.TEXT_LANGUAGE,
                how_to_cut=GPTSoVITSConfig.HOW_TO_CUT,
                top_k=GPTSoVITSConfig.TOP_K,
                top_p=GPTSoVITSConfig.TOP_P,
                temperature=GPTSoVITSConfig.TEMPERATURE,
                ref_free=GPTSoVITSConfig.REF_FREE,
                speed=GPTSoVITSConfig.SPEED,
                if_freeze=GPTSoVITSConfig.IF_FREEZE,
                inp_refs=None,
                sample_steps=GPTSoVITSConfig.SAMPLE_STEPS,
                if_sr=GPTSoVITSConfig.IF_SR,
                pause_second=GPTSoVITSConfig.PAUSE_SECOND,
                api_name="/get_tts_wav"
            )
            
            if result and os.path.exists(result):
                file_size = os.path.getsize(result)
                log_msg = f"✅ 语音合成成功！文件: {result}, 大小: {file_size} 字节"
                if hasattr(logger, 'success'):
                    logger.success(log_msg)
                else:
                    logger.info(log_msg)
                return result
            else:
                logger.error(f"❌ 语音合成失败：返回的文件路径无效 {result}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 语音合成失败: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查 TTS 服务是否可用"""
        return self.enabled and self.model_loaded


# 全局单例
_tts_service: Optional[GPTSoVITSService] = None


def get_tts_service() -> GPTSoVITSService:
    """获取 TTS 服务单例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = GPTSoVITSService()
    return _tts_service


async def initialize_tts_service():
    """初始化 TTS 服务（在启动时调用）"""
    service = get_tts_service()
    await service.initialize()

