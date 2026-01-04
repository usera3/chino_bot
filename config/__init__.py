#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块
"""
from pydantic import BaseModel
from nonebot import get_driver


class Config(BaseModel):
    """机器人配置"""
    # API密钥
    deepseek_api_key: str = ""
    dashscope_api_key: str = ""
    
    class Config:
        extra = "ignore"


# 获取配置
global_config = get_driver().config
config = Config(**global_config.dict())




