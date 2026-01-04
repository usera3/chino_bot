"""
点赞处理器 - Like Handler
处理用户点赞请求
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message
import asyncio


# ==================== 点赞命令 ====================
like_matcher = on_command("点赞", aliases={"赞我", "给我点赞", "like"}, priority=5, block=True)

# 群内批量点赞命令
like_all_matcher = on_command("给所有人点赞", aliases={"全体点赞", "群体点赞", "给大家点赞", "like all"}, priority=5, block=True)

@like_matcher.handle()
async def handle_like(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """处理点赞请求"""
    user_id = event.user_id
    arg_text = args.extract_plain_text().strip()
    
    # 解析点赞次数，默认3次，避免触发限制
    times = 10
    if arg_text:
        try:
            times = int(arg_text)
            if times < 1:
                times = 1
            elif times >=10:  # 降低限制，避免触发QQ限制
                times = 10
        except ValueError:
            times = 3
    
    try:
        # 调用OneBot API点赞
        await bot.send_like(user_id=user_id, times=times)
        
        logger.info(f"👍 已给用户 {user_id} 点赞 {times} 次")
        
        # 根据次数返回不同的回复
        if times >= 10:
            await like_matcher.send(f"👍 已经给你狂点了 {times} 个赞啦！")
        elif times >= 5:
            await like_matcher.send(f"👍 给你点了 {times} 个赞~")
        else:
            await like_matcher.send(f"👍 点了 {times} 个赞")
            
    except Exception as e:
        logger.error(f"点赞失败: {e}")
        await like_matcher.send("❌ 点赞失败了，可能今天已经点过很多次了")


# ==================== 批量点赞命令 ====================

@like_all_matcher.handle()
async def handle_like_all(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """处理群内批量点赞请求"""
    
    # 只在群聊中支持批量点赞
    if not isinstance(event, GroupMessageEvent):
        await like_all_matcher.finish("❌ 批量点赞功能只能在群聊中使用哦~")
    
    group_id = event.group_id
    user_id = event.user_id
    arg_text = args.extract_plain_text().strip()
    
    # 解析点赞次数，默认1次（批量点赞时建议少一些）
    times = 10
    if arg_text:
        try:
            times = int(arg_text)
            if times < 1:
                times = 1
            elif times >= 10:  # 批量点赞时限制更低，避免被限制
                times = 10
        except ValueError:
            times = 1
    
    try:
        # 获取群成员列表
        await like_all_matcher.send("📋 正在获取群成员列表...")
        member_list = await bot.get_group_member_list(group_id=group_id)
        
        if not member_list:
            await like_all_matcher.finish("❌ 无法获取群成员列表")
        
        # 过滤掉机器人自己
        bot_info = await bot.get_login_info()
        bot_id = bot_info["user_id"]
        members_to_like = [member for member in member_list if member["user_id"] != bot_id]
        
        total_members = len(members_to_like)
        await like_all_matcher.send(f"👥 准备给 {total_members} 位群友点赞，每人 {times} 次...")
        
        # 批量点赞
        success_count = 0
        failed_count = 0
        
        for i, member in enumerate(members_to_like, 1):
            try:
                member_id = member["user_id"]
                await bot.send_like(user_id=member_id, times=times)
                success_count += 1
                
                # 进度提示（每10个或最后一个）
                if i % 10 == 0 or i == total_members:
                    await like_all_matcher.send(f"⏳ 进度: {i}/{total_members} ({success_count} 成功, {failed_count} 失败)")
                
                # 适当延时避免频率限制
                if i < total_members:  # 不是最后一个才延时
                    await asyncio.sleep(0.5)  # 500ms延时
                    
            except Exception as e:
                failed_count += 1
                logger.warning(f"给用户 {member['user_id']} 点赞失败: {e}")
                continue
        
        # 最终统计
        success_rate = (success_count / total_members * 100) if total_members > 0 else 0
        result_msg = (
            f"🎉 批量点赞完成！\n"
            f"📊 统计结果：\n"
            f"✅ 成功: {success_count} 人\n"
            f"❌ 失败: {failed_count} 人\n"
            f"📈 成功率: {success_rate:.1f}%\n"
            f"👍 每人点赞: {times} 次"
        )
        
        await like_all_matcher.send(result_msg)
        logger.info(f"群 {group_id} 批量点赞完成: {success_count}/{total_members} 成功")
        
    except Exception as e:
        logger.error(f"批量点赞失败: {e}")
        await like_all_matcher.send(f"❌ 批量点赞失败: {str(e)}")


