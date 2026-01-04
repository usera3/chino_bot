"""
TTS (Text-to-Speech) 服务模块
"""
from .gpt_sovits_service import (
    GPTSoVITSService,
    GPTSoVITSConfig,
    get_tts_service,
    initialize_tts_service
)

__all__ = [
    'GPTSoVITSService',
    'GPTSoVITSConfig',
    'get_tts_service',
    'initialize_tts_service'
]

