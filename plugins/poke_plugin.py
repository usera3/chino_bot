"""
戳一戳插件 - 让智乃对戳一戳做出智能反应（由 Butler Agent 处理）
"""
from nonebot import on_notice, get_driver
from nonebot.adapters.onebot.v11 import Bot, PokeNotifyEvent, GroupMessageEvent


# 全局 Butler 实例（从 chat_plugin 导入）
butler = None


@get_driver().on_startup
async def init_butler_ref():
    """获取 Butler 实例的引用"""
    global butler
    from plugins.chat_plugin import butler as chat_butler
    butler = chat_butler


# 创建戳一戳事件处理器
poke = on_notice(priority=10, block=True)


@poke.handle()
async def handle_poke(bot: Bot, event: PokeNotifyEvent):
    """处理戳一戳事件 - 交给 Butler Agent 处理"""
    global butler
    
    # 只响应戳机器人的事件
    if event.target_id != event.self_id:
        return
    
    # 设置 Bot 实例到 QQ 互动工具
    from tools.qq_interaction_tools import set_bot_instance, set_current_context
    set_bot_instance(bot)
    
    # 检查 Butler 是否初始化
    if butler is None:
        # 如果 Butler 未初始化，使用简单回复
        await bot.send(event, "呀！不要戳我啦~ (｡>﹏<｡)")
        return
    
    # 获取用户 ID
    user_id = str(event.user_id)
    
    # 判断是群聊还是私聊
    chat_type = "群聊" if event.group_id else "私聊"
    group_id = event.group_id
    
    # 设置当前上下文
    set_current_context(user_id=user_id, group_id=group_id)
    
    # 获取用户昵称
    try:
        if event.group_id:
            user_info = await bot.get_group_member_info(group_id=event.group_id, user_id=int(user_id), no_cache=False)
            user_nickname = user_info.get('card') or user_info.get('nickname', user_id)
        else:
            user_info = await bot.get_stranger_info(user_id=int(user_id), no_cache=False)
            user_nickname = user_info.get('nickname', user_id)
    except:
        user_nickname = user_id
    
    # 构建戳一戳事件的描述消息 - 简洁自然
    poke_message = f"[{user_nickname} 戳了戳你]"
    
    # 日志
    print(f"\n{'=' * 60}")
    print(f"🔔 收到戳一戳事件 [{chat_type}]")
    if group_id:
        print(f"   群号: {group_id}")
    print(f"   用户: {user_nickname}({user_id})")
    print(f"{'=' * 60}\n")
    
    try:
        # 使用 Butler 处理戳一戳事件
        response = await butler.aprocess(poke_message, user_id=user_id)
        
        # 发送回复
        if event.group_id:
            await bot.send_group_msg(group_id=event.group_id, message=response)
        else:
            await bot.send_private_msg(user_id=event.user_id, message=response)
        
        print(f"\n✅ 回复成功: {response[:50]}...\n")
        
    except Exception as e:
        error_msg = f"呀！被戳到了呢~ (´･ω･`)"
        if event.group_id:
            await bot.send_group_msg(group_id=event.group_id, message=error_msg)
        else:
            await bot.send_private_msg(user_id=event.user_id, message=error_msg)
        
        print(f"\n❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
