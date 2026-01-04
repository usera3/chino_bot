"""
主动聊天Handler - Proactive Handler
处理主动聊天相关的命令
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg
from nonebot.log import logger
from datetime import datetime

from services.proactive import get_proactive_service
from services.emotion import get_emotion_service, EmotionConfig
from models.emotion_models import EmotionChangeLog, DynamicEmotionProfile
from sqlalchemy import select, desc


# 获取服务单例
proactive_service = get_proactive_service()
emotion_service = get_emotion_service()


# ==================== 命令定义 ====================

# 查看主动聊天状态
proactive_status = on_command("主动聊天状态", aliases={"主动状态", "聊天状态"}, priority=5)

@proactive_status.handle()
async def handle_proactive_status(event: MessageEvent):
    """查看主动聊天状态"""
    user_id = str(event.user_id)
    
    try:
        # 获取情感状态
        profile = await emotion_service.get_or_create_profile(user_id)
        emotion_style = await emotion_service.get_emotion_influenced_style(user_id)
        
        # 检查是否应该主动聊天
        should_chat, reason, emotion_state = await emotion_service.should_initiate_chat(user_id)
        
        # 获取亲密度排名
        intimacy_rankings = await emotion_service.get_intimacy_ranking()
        user_rank = next((i+1 for i, (uid, _) in enumerate(intimacy_rankings) if uid == user_id), "未知")
        
        status_msg = f"""🤖 主动聊天系统状态

【情感状态】
💝 快乐值: {profile.happiness:.1f}/100
😢 寂寞值: {profile.loneliness:.1f}/100
⚡ 体力值: {profile.energy:.1f}/100
💪 自信值: {profile.confidence:.1f}/100
😊 心情: {profile.mood}
📈 社交需求: {profile.social_need:.1f}/100
💕 亲密度: {profile.intimacy_level:.2f}/1.0

【系统状态】
🎯 是否应该主动聊天: {'是' if should_chat else '否'}
📝 原因: {reason}
🏆 亲密度排名: 第{user_rank}位

【回复风格】
🎨 心情影响: {emotion_style.get('mood', 'neutral')}
⚡ 体力状态: {emotion_style.get('energy_level', 'medium')}
💪 自信程度: {emotion_style.get('confidence_level', 'medium')}
💝 魅力程度: {emotion_style.get('charm_level', 'medium')}
🎭 创造力: {emotion_style.get('creativity_level', 'medium')}
❤️ 同理心: {emotion_style.get('empathy_level', 'medium')}

【特殊状态】
{'😴 正在休息' if emotion_style.get('be_resting') else '✅ 状态正常'}
{'😊 使用表情' if emotion_style.get('use_emojis') else '😐 少用表情'}
{'🎮 活泼模式' if emotion_style.get('be_playful') else '😌 安静模式'}
{'🤗 关怀模式' if emotion_style.get('be_caring') else '😐 普通模式'}
{'💪 自信模式' if emotion_style.get('be_confident') else '😌 温和模式'}
{'😌 温柔模式' if emotion_style.get('be_gentle') else '😐 普通模式'}
{'⚡ 活力模式' if emotion_style.get('be_energetic') else '😌 平静模式'}

【时间信息】
🕐 最后更新: {profile.last_update.strftime('%H:%M:%S')}
💬 最后聊天: {profile.last_chat_time.strftime('%H:%M:%S') if profile.last_chat_time else '从未'}
🎯 最后主动: {profile.last_proactive_time.strftime('%H:%M:%S') if profile.last_proactive_time else '从未'}
"""
        
        await proactive_status.send(status_msg)
        
    except Exception as e:
        logger.error(f"获取主动聊天状态失败: {e}")
        await proactive_status.send(f"❌ 获取状态失败: {str(e)}")


# 调整情感参数(管理员命令)
adjust_emotion = on_command("调整情感", priority=5)

@adjust_emotion.handle()
async def handle_adjust_emotion(event: MessageEvent, args: Message = CommandArg()):
    """调整情感参数(管理员命令)"""
    # 检查管理员权限
    if event.user_id not in [1446437177]:  # 管理员QQ号
        await adjust_emotion.send("❌ 权限不足,仅管理员可使用")
        return
    
    try:
        arg_text = args.extract_plain_text().strip()
        if not arg_text:
            await adjust_emotion.send(
                "💝 调整情感参数\n\n"
                "用法: /调整情感 参数=值\n\n"
                "可用参数:\n"
                "• happiness - 快乐值 (0-100)\n"
                "• loneliness - 寂寞值 (0-100)\n"
                "• energy - 体力值 (0-100)\n"
                "• confidence - 自信值 (0-100)\n"
                "• charm - 魅力值 (0-100)\n"
                "• intelligence - 智力值 (0-100)\n"
                "• creativity - 创造力 (0-100)\n"
                "• empathy - 同理心 (0-100)\n"
                "• stress_level - 压力值 (0-100)\n"
                "• intimacy_level - 亲密度 (0-1)\n\n"
                "示例: /调整情感 loneliness=80 happiness=20"
            )
            return
        
        # 解析参数
        changes = {}
        for part in arg_text.split():
            if '=' in part:
                key, value = part.split('=', 1)
                try:
                    val = float(value)
                    if key in ['intimacy_level']:
                        val = max(0, min(1, val))
                    else:
                        val = max(0, min(100, val))
                    changes[key] = val
                except ValueError:
                    await adjust_emotion.send(f"❌ 无效数值: {value}")
                    return
        
        if not changes:
            await adjust_emotion.send("❌ 没有有效的参数")
            return
        
        # 应用变化
        user_id = str(event.user_id)
        await emotion_service._apply_emotion_changes(
            user_id, changes, "admin_adjust", f"管理员调整: {changes}"
        )
        
        # 更新社交需求
        await emotion_service._update_social_need(user_id)
        
        await adjust_emotion.send(f"✅ 情感参数已调整: {changes}")
        
    except Exception as e:
        logger.error(f"调整情感参数失败: {e}")
        await adjust_emotion.send(f"❌ 调整失败: {str(e)}")


# 强制主动聊天
force_proactive = on_command("强制主动", priority=5)

@force_proactive.handle()
async def handle_force_proactive(event: MessageEvent):
    """强制触发主动聊天(管理员命令)"""
    # 检查管理员权限
    if event.user_id not in [1446437177]:  # 管理员QQ号
        await force_proactive.send("❌ 权限不足,仅管理员可使用")
        return
    
    try:
        user_id = str(event.user_id)
        
        # 获取当前情感状态
        profile = await emotion_service.get_or_create_profile(user_id)
        emotion_state = emotion_service._get_emotion_state(profile)
        
        # 强制触发主动聊天
        await proactive_service.execute_proactive_chat(
            user_id, emotion_state, "管理员强制触发"
        )
        
        await force_proactive.send("✅ 已强制触发主动聊天")
        
    except Exception as e:
        logger.error(f"强制主动聊天失败: {e}")
        await force_proactive.send(f"❌ 强制触发失败: {str(e)}")


# 查看亲密度排名
intimacy_ranking = on_command("亲密度排名", aliases={"排名", "亲密度"}, priority=5)

@intimacy_ranking.handle()
async def handle_intimacy_ranking(event: MessageEvent):
    """查看亲密度排名"""
    try:
        rankings = await emotion_service.get_intimacy_ranking()
        
        if not rankings:
            await intimacy_ranking.send("📊 暂无用户数据")
            return
        
        ranking_msg = "💕 亲密度排名\n\n"
        for i, (user_id, intimacy) in enumerate(rankings[:10]):  # 显示前10名
            rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
            ranking_msg += f"{rank_emoji} 用户 {user_id}: {intimacy:.3f}\n"
        
        await intimacy_ranking.send(ranking_msg)
        
    except Exception as e:
        logger.error(f"获取亲密度排名失败: {e}")
        await intimacy_ranking.send(f"❌ 获取排名失败: {str(e)}")


# 重置情感系统
reset_emotion = on_command("重置情感", priority=5)

@reset_emotion.handle()
async def handle_reset_emotion(event: MessageEvent):
    """重置情感系统(管理员命令)"""
    # 检查管理员权限
    if event.user_id not in [1446437177]:  # 管理员QQ号
        await reset_emotion.send("❌ 权限不足,仅管理员可使用")
        return
    
    try:
        user_id = str(event.user_id)
        
        # 重置为默认值
        reset_changes = {
            'happiness': 70.0,
            'loneliness': 30.0,
            'energy': 80.0,
            'confidence': 60.0,
            'charm': 50.0,
            'intelligence': 70.0,
            'creativity': 60.0,
            'empathy': 75.0,
            'stress_level': 20.0,
            'intimacy_level': 0.5
        }
        
        await emotion_service._apply_emotion_changes(
            user_id, reset_changes, "admin_reset", "管理员重置情感系统"
        )
        
        await reset_emotion.send("✅ 情感系统已重置为默认值")
        
    except Exception as e:
        logger.error(f"重置情感系统失败: {e}")
        await reset_emotion.send(f"❌ 重置失败: {str(e)}")


# 查看情感变化日志
emotion_logs = on_command("情感日志", aliases={"情感记录", "变化日志"}, priority=5)

@emotion_logs.handle()
async def handle_emotion_logs(event: MessageEvent):
    """查看情感变化日志"""
    try:
        user_id = str(event.user_id)
        
        # 获取最近的情感变化记录
        from services.database.database_service import get_database_service
        db_service = get_database_service()
        
        async with db_service.Session() as session:
            result = await session.execute(
                select(EmotionChangeLog)
                .where(EmotionChangeLog.user_id == user_id)
                .order_by(desc(EmotionChangeLog.created_at))
                .limit(10)
            )
            logs = result.scalars().all()
        
        if not logs:
            await emotion_logs.send("📝 暂无情感变化记录")
            return
        
        logs_msg = "📝 最近情感变化记录\n\n"
        for log in logs:
            logs_msg += f"🕐 {log.created_at.strftime('%H:%M:%S')}\n"
            logs_msg += f"📋 类型: {log.change_type}\n"
            logs_msg += f"📝 描述: {log.description}\n"
            if log.emotion_changes:
                import json
                changes = json.loads(log.emotion_changes)
                if changes:
                    changes_str = ", ".join([f"{k}: {v:+.1f}" for k, v in changes.items()])
                    logs_msg += f"📊 变化: {changes_str}\n"
            logs_msg += "\n"
        
        await emotion_logs.send(logs_msg)
        
    except Exception as e:
        logger.error(f"获取情感日志失败: {e}")
        await emotion_logs.send(f"❌ 获取日志失败: {str(e)}")


# 导出
__all__ = [
    'proactive_status', 'adjust_emotion', 'force_proactive',
    'intimacy_ranking', 'reset_emotion', 'emotion_logs'
]























