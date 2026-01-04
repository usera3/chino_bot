"""
图像处理插件 - 已禁用
现在使用 Function Calling Agent 的 vision_understanding 工具代替
AI会根据用户意图决定是否调用图片识别功能
"""
from nonebot.log import logger

# ⚠️ 此插件已被禁用
# 图片识别功能已整合到 Function Calling Agent 中
# 当用户明确询问图片内容时，AI会自动调用 vision_understanding 工具

logger.info("🖼️ 图像识别已整合到 Function Calling Agent（基于用户意图触发）")
