"""
无指令化集成模块 - AI驱动的复杂功能
专注于需要AI解析的复杂自然语言交互

目前支持：
- 🤖 AI智能点赞：支持复杂的目标识别和次数解析

已移除：
- 表情包系统（已废弃）
- 主动聊天（已有独立的handlers实现）
"""

from nonebot.log import logger
from typing import Dict, Any, Optional
import re
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
import asyncio

# 无指令化集成模块定位：专注于AI解析的复杂功能

# ==================== 点赞功能 ====================

async def _parse_like_target_with_ai(user_message: str, event) -> int:
    """使用AI解析点赞目标"""
    try:
        from utils.ai_clients.deepseek_client import get_deepseek_client
        
        # 构建AI提示词
        prompt = f"""请分析以下消息，识别用户想要给谁点赞。

消息内容：{user_message}

请从消息中提取目标用户的QQ号。如果消息中没有明确的QQ号，请返回"self"表示给自己点赞。

要求：
1. 如果消息包含QQ号（如"给12345678点赞"），返回该QQ号
2. 如果消息包含"给我点赞"、"点赞"等，返回"self"
3. 如果消息包含"给所有人点赞"等，返回"all"
4. 只返回数字QQ号、"self"或"all"，不要其他解释

示例：
- "给12345678点赞" → 12345678
- "给我点赞" → self
- "点赞" → self
- "给所有人点赞" → all
- "给qq号为1422903954的人点赞" → 1422903954

请直接返回结果："""
        
        client = get_deepseek_client()
        messages = [{"role": "user", "content": prompt}]
        response = await client.chat(messages)
        
        if response:
            response = response.strip()
            logger.info(f"🤖 AI解析点赞目标: {response}")
            
            if response == "self":
                return event.user_id
            elif response == "all":
                return "all"  # 特殊标记，表示批量点赞
            elif response.isdigit():
                return int(response)
        
        # 如果AI解析失败，默认给自己点赞
        logger.warning("AI解析点赞目标失败，默认给自己点赞")
        return event.user_id
        
    except Exception as e:
        logger.error(f"AI解析点赞目标失败: {e}")
        return event.user_id

async def handle_like_request(user_message: str, event) -> str:
    """
    处理点赞请求 - 支持多种目标格式
    - "给我点赞" / "点赞" → 给自己点赞
    - "给xxx点赞" / "给@某人点赞" → 给指定用户点赞
    - "给12345678点赞" → 给指定QQ号点赞
    - "给所有人点赞" / "给群里所有人点赞" → 给群内所有成员点赞（每人1次）
    """
    try:
        from nonebot import get_bot
        bot = get_bot()
        
        # 检查是否是给所有人点赞
        if any(keyword in user_message for keyword in ["给所有人点赞", "给群里所有人点赞", "给群内所有人点赞", "给全部人点赞", "全体点赞", "给大家点赞"]):
            return await handle_batch_like_request(event)
        
        # 使用AI识别点赞目标
        target_user_id = await _parse_like_target_with_ai(user_message, event)
        
        # 如果AI识别为批量点赞，调用批量点赞处理
        if target_user_id == "all":
            return await handle_batch_like_request(event)
        
        # 解析点赞次数 - 只匹配明确的次数表达，避免将QQ号误识别为次数
        times = 3  # 默认3次，避免触发限制
        
        # 更精确的次数匹配：匹配"点X次"、"X个赞"、"赞X次"等格式
        times_patterns = [
            r'点\s*(\d+)\s*[次个]',  # "点3次"、"点5个"
            r'(\d+)\s*[次个]\s*赞',  # "3次赞"、"5个赞"  
            r'赞\s*(\d+)\s*[次个]',  # "赞3次"、"赞5个"
            r'(\d+)\s*[次个]\s*点赞', # "3次点赞"、"5个点赞"
        ]
        
        for pattern in times_patterns:
            times_match = re.search(pattern, user_message)
            if times_match:
                times = int(times_match.group(1))
                if times < 1:
                    times = 1
                elif times > 10:  # 适当提高限制但仍要控制
                    times = 10
                break
        
        # 执行点赞
        logger.info(f"🎯 准备点赞: target_user_id={target_user_id}, times={times}")
        await bot.send_like(user_id=target_user_id, times=times)
        
        logger.info(f"👍 已给用户 {target_user_id} 点赞 {times} 次")
        
        # 根据次数返回不同的回复
        if times >= 10:
            return f"👍 已经给你狂点了 {times} 个赞啦！"
        elif times >= 5:
            return f"👍 给你点了 {times} 个赞~"
        else:
            return f"👍 点了 {times} 个赞"
            
    except Exception as e:
        logger.error(f"点赞失败: {e}")
        return "❌ 点赞失败了，可能今天已经点过很多次了"

async def handle_batch_like_request(event) -> str:
    """
    处理批量点赞请求 - 给群内所有成员点赞（每人1次）
    """
    try:
        from nonebot import get_bot
        bot = get_bot()
        
        # 只在群聊中支持批量点赞
        if not isinstance(event, GroupMessageEvent):
            return "❌ 批量点赞功能只能在群聊中使用哦~"
        
        group_id = event.group_id
        logger.info(f"🎯 开始批量点赞群 {group_id} 的所有成员")
        
        # 获取群成员列表
        try:
            member_list = await bot.get_group_member_list(group_id=group_id)
        except Exception as e:
            logger.error(f"获取群成员列表失败: {e}")
            return "❌ 无法获取群成员列表"
        
        if not member_list:
            return "❌ 没有可点赞的群成员"
        
        # 过滤掉机器人自己
        bot_info = await bot.get_login_info()
        bot_id = bot_info["user_id"]
        valid_members = [m for m in member_list if m["user_id"] != bot_id]
        
        if not valid_members:
            return "❌ 没有可点赞的群成员"
        
        logger.info(f"🎯 准备给 {len(valid_members)} 个群成员点赞（每人10次）")
        
        # 执行批量点赞
        success_count = 0
        failed_count = 0
        failed_members = []
        consecutive_failures = 0
        
        for member in valid_members:
            user_id = member["user_id"]
            nickname = member.get("nickname", str(user_id))
            
            try:
                # 给每个成员点赞10次
                await bot.send_like(user_id=user_id, times=10)
                success_count += 1
                consecutive_failures = 0
                logger.info(f"✅ 已给 {nickname}({user_id}) 点赞")
                
                # 适当延时避免频率限制
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_count += 1
                failed_members.append(nickname)
                consecutive_failures += 1
                logger.warning(f"❌ 给 {nickname} 点赞失败: {e}")
                
                # 如果连续失败太多次，提前退出
                if consecutive_failures >= 5:
                    logger.warning("⚠️ 连续失败次数过多，停止批量点赞")
                    break
        
        # 返回结果
        if success_count == 0:
            return "❌ 批量点赞失败，可能已达到今日点赞限制"
        elif failed_count == 0:
            return f"🎉 批量点赞完成！成功给 {success_count} 个群成员点赞"
        else:
            return f"📊 批量点赞完成！成功 {success_count} 人，失败 {failed_count} 人\n失败成员: {', '.join(failed_members[:5])}{'...' if len(failed_members) > 5 else ''}"
        
    except Exception as e:
        logger.error(f"批量点赞失败: {e}")
        return "❌ 批量点赞失败，请稍后重试"

# ==================== 功能注册信息 ====================

# 这个字典将被intelligent_dispatcher导入并注册
# 专注于需要AI解析的复杂无指令化功能
COMMANDLESS_FUNCTIONS = {
    # AI驱动的智能点赞功能
    "like_user": {
        "handler": handle_like_request,
        "description": "给用户QQ资料卡点赞，支持AI解析复杂的自然语言表达，包括指定目标用户、次数等",
        "keywords": ["点赞", "赞我", "给我点赞", "like", "赞", "点个赞", "给", "点", "所有人", "群里所有人", "全部人", "给大家点赞", "全体点赞"],
        "examples": [
            "给我点赞",
            "点赞",
            "赞我",
            "给张三点赞", 
            "给12345678点赞",
            "给我点5个赞",
            "点3次赞",
            "给所有人点赞",
            "给群里所有人点赞",
            "给大家点个赞",
            "全体点赞",
            "给QQ号为1234567890的人点赞"
        ]
    }
    
    # 说明：
    # - 表情包功能已废弃，不再支持
    # - 主动聊天功能已有独立的handlers实现（proactive_handler.py）
    # - 只保留需要AI解析的点赞功能，因为它支持复杂的自然语言表达
}

logger.info(f"✅ 无指令化功能集成完成，共注册 {len(COMMANDLESS_FUNCTIONS)} 个功能（专注AI驱动的复杂功能）")


