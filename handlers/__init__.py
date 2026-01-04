"""
Handlers 入口层
功能入口点，简洁清晰
"""

# 导入所有 handler，让 NoneBot 能够识别
from . import image_handler
from . import chat_handler

__all__ = ['image_handler', 'chat_handler']

