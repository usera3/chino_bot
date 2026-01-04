"""
情感服务包
提供动态情感管理、情感风格计算等功能
"""

from .emotion_service import EmotionService, get_emotion_service
from .emotion_config import EmotionConfig

__all__ = ['EmotionService', 'get_emotion_service', 'EmotionConfig']




