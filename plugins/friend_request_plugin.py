#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
好友申请自动处理插件
支持自动同意、黑白名单、关键词过滤等功能
"""
import asyncio
from nonebot import on_request, get_driver
from nonebot.adapters.onebot.v11 import Bot, FriendRequestEvent
from nonebot.log import logger
from pathlib import Path
import sys

# 添加 config 目录到路径
config_path = Path(__file__).parent.parent / "config"
sys.path.insert(0, str(config_path))

try:
    from friend_request_config import (
        AUTO_APPROVE,
        SEND_WELCOME,
        WELCOME_MESSAGE,
        AUTO_REMARK,
        BLACKLIST,
        WHITELIST_MODE,
        WHITELIST,
        REJECT_KEYWORDS,
        REQUIRED_KEYWORDS,
        LOG_REQUESTS,
        NOTIFY_SUPERUSER
    )
except ImportError:
    # 使用默认配置
    logger.warning("未找到好友申请配置文件，使用默认配置")
    AUTO_APPROVE = True
    SEND_WELCOME = True
    WELCOME_MESSAGE = "你好呀！我是智乃，很高兴认识你~"
    AUTO_REMARK = ""
    BLACKLIST = []
    WHITELIST_MODE = False
    WHITELIST = []
    REJECT_KEYWORDS = []
    REQUIRED_KEYWORDS = []
    LOG_REQUESTS = True
    NOTIFY_SUPERUSER = False

# 获取超级用户列表
driver = get_driver()
superusers = driver.config.superusers

# 监听好友申请事件
friend_request = on_request(priority=5, block=False)


def should_approve(user_id: int, comment: str) -> tuple[bool, str]:
    """
    判断是否应该同意好友申请
    
    Args:
        user_id: 申请者 QQ 号
        comment: 申请备注
        
    Returns:
        (是否同意, 原因)
    """
    # 检查黑名单
    if user_id in BLACKLIST:
        return False, "用户在黑名单中"
    
    # 检查白名单模式
    if WHITELIST_MODE:
        if user_id not in WHITELIST:
            return False, "白名单模式：用户不在白名单中"
    
    # 检查拒绝关键词
    if REJECT_KEYWORDS and comment:
        for keyword in REJECT_KEYWORDS:
            if keyword in comment:
                return False, f"备注包含拒绝关键词: {keyword}"
    
    # 检查必须关键词
    if REQUIRED_KEYWORDS:
        if not comment:
            return False, "未填写备注，且设置了必须关键词"
        
        has_required = False
        for keyword in REQUIRED_KEYWORDS:
            if keyword in comment:
                has_required = True
                break
        
        if not has_required:
            return False, f"备注未包含必须关键词: {REQUIRED_KEYWORDS}"
    
    return True, "通过所有检查"


@friend_request.handle()
async def handle_friend_request(bot: Bot, event: FriendRequestEvent):
    """
    处理好友申请
    
    Args:
        bot: Bot 实例
        event: 好友申请事件
    """
    try:
        # 获取申请者信息
        user_id = event.user_id
        comment = event.comment or ""  # 申请备注
        flag = event.flag  # 请求标识
        
        # 记录日志
        if LOG_REQUESTS:
            logger.info(f"收到好友申请: 用户 {user_id}, 备注: {comment}")
        
        # 判断是否应该同意
        should_approve_result, reason = should_approve(user_id, comment)
        
        if not AUTO_APPROVE:
            logger.info(f"自动同意已禁用，跳过处理")
            return
        
        if should_approve_result:
            # 同意好友申请
            await bot.set_friend_add_request(
                flag=flag,
                approve=True,
                remark=AUTO_REMARK
            )
            
            logger.success(f"✓ 已自动同意用户 {user_id} 的好友申请 (原因: {reason})")
            
            # 通知超级用户
            if NOTIFY_SUPERUSER and superusers:
                notify_msg = f"[好友申请] 已自动同意\n用户: {user_id}\n备注: {comment}"
                for su in superusers:
                    try:
                        await bot.send_private_msg(user_id=int(su), message=notify_msg)
                    except:
                        pass
            
            # 等待好友添加成功
            await asyncio.sleep(2)
            
            # 发送欢迎消息
            if SEND_WELCOME:
                try:
                    await bot.send_private_msg(
                        user_id=user_id,
                        message=WELCOME_MESSAGE
                    )
                    logger.success(f"✓ 已向用户 {user_id} 发送欢迎消息")
                except Exception as e:
                    logger.warning(f"发送欢迎消息失败: {e}")
        else:
            # 拒绝好友申请
            await bot.set_friend_add_request(
                flag=flag,
                approve=False,
                remark=""
            )
            
            logger.warning(f"✗ 已拒绝用户 {user_id} 的好友申请 (原因: {reason})")
            
            # 通知超级用户
            if NOTIFY_SUPERUSER and superusers:
                notify_msg = f"[好友申请] 已自动拒绝\n用户: {user_id}\n备注: {comment}\n原因: {reason}"
                for su in superusers:
                    try:
                        await bot.send_private_msg(user_id=int(su), message=notify_msg)
                    except:
                        pass
            
    except Exception as e:
        logger.error(f"处理好友申请失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
